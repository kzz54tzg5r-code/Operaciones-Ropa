"""V327 · Bono 2, misma interfaz de Bono 1 con cartera independiente.

Criterios exclusivos de Bono 2, calculados al último corte de Capacidades:
- Tipo catálogo = VIGENTE;
- rubro oficial CATALOGO = Abrigador/Licencias/Básicos;
- VTA EN PZAS 30 = exactamente cero (nunca tratar dato faltante como cero);
- última entrada CEDIS a tienda entre fecha_corte-7 y fecha_corte, inclusive.

No altera Bono 1, los cortes históricos ni los puntajes de Bonos 3–6.
Cálculo pesado asíncrono, por lotes pequeños, con caché persistente y acotado.
"""
from __future__ import annotations
import gzip
import json
import math
import os
import re
import tempfile
import threading
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from v293_sales_bonus_patch import classify_bonus_catalogs_from_source

MX = ZoneInfo("America/Mexico_City")
CATALOGS = ("Abrigador", "Licencias", "Básicos")
RESTRICTED = ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria")
_CACHE_VERSION = "v327-2"
_JOBS = set()
_JOB_LOCK = threading.Lock()
_SCAN_LIMIT = threading.BoundedSemaphore(1)


def fold(v):
    return "".join(c for c in unicodedata.normalize("NFKD", str(v or "")) if not unicodedata.combining(c)).upper().strip()


def qualify_bono2_rows(raw, cutoff: date, source_path):
    """Pure chunk filter: never infer missing sales or dates."""
    import pandas as pd
    from commercial.parsers import _capacity_date_series, _normalize_capacity_source
    required = ("TIPO CATALOGO MAX VIG", "VTA EN PZAS 30", "ULTIMA ENTRADA CEDIS A TIENDA",
                "CATALOGO", "ID_ART", "TIENDA")
    absent = [k for k in required if k not in raw.columns]
    if absent:
        raise ValueError("Columnas de Capacidades no disponibles: " + ", ".join(absent))
    status = raw["TIPO CATALOGO MAX VIG"].astype(str).map(fold).eq("VIGENTE")
    sales = pd.to_numeric(raw["VTA EN PZAS 30"], errors="coerce")
    original_dates = raw["ULTIMA ENTRADA CEDIS A TIENDA"]
    dates = _capacity_date_series(original_dates)
    # ISO YYYY-MM-DD es inequívoco y no debe interpretarse como DD-MM-YYYY
    # con dayfirst=True; en Capacidades reales también puede llegar serial Excel.
    raw_iso = original_dates.astype(str).str.strip()
    explicit_iso = pd.to_datetime(
        raw_iso.where(raw_iso.str.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}")),
        format="%Y-%m-%d", errors="coerce"
    )
    dates = dates.where(explicit_iso.isna(), explicit_iso)
    lower = pd.Timestamp(cutoff - timedelta(days=7))
    upper = pd.Timestamp(cutoff)
    recent = dates.ge(lower) & dates.le(upper)
    matched = status & sales.eq(0) & recent
    if not bool(matched.any()):
        return []
    selected = raw.loc[matched].copy()
    normalized = _normalize_capacity_source(selected, source_path)
    catalogs = classify_bonus_catalogs_from_source(normalized["Catálogo comercial"])
    normalized = normalized.loc[catalogs.isin(CATALOGS)].copy()
    catalogs = catalogs.loc[normalized.index]
    if normalized.empty:
        return []
    result = []
    for idx in normalized.index:
        row = normalized.loc[idx]
        id_art = str(row.get("ID_ART") or "").strip()
        if not re.fullmatch(r"\d{1,15}", id_art):
            continue
        arriving = dates.loc[idx]
        store = str(row.get("Tienda") or "").strip()
        if not store:
            continue
        def numeric(key):
            try:
                value = float(row.get(key) or 0)
                return value if math.isfinite(value) else 0.0
            except (ValueError, TypeError):
                return 0.0
        result.append({
            "store": store,
            "id_art": id_art,
            "model": str(row.get("Modelo") or id_art),
            "catalog": str(catalogs.loc[idx]),
            "sales_30": 0,
            "last_arrival": arriving.date().isoformat(),
            "arrival_age_days": (cutoff - arriving.date()).days,
            "current_ddi": numeric("DDI"),
            "current_existence": numeric("Existencia"),
            "current_investment": numeric("Inversión"),
            "initial_ddi": None,
            "initial_existence": None,
            "initial_investment": None,
            "ddi_reduction_pct": None,
            "investment_reduction_pct": None,
        })
    return result


def build_bono2_cohort(source, cutoff: date):
    """Work from XLSX chunks; no global 200k-row DataFrame is materialized."""
    from commercial.parsers import _iter_fast_capacity_xlsx
    merged = {}
    with _SCAN_LIMIT:
        for index, chunk in enumerate(_iter_fast_capacity_xlsx(source, chunk_rows=1000)):
            for row in qualify_bono2_rows(chunk, cutoff, source):
                key = (fold(row["store"]), row["id_art"])
                old = merged.get(key)
                if old is None:
                    merged[key] = row
                else:
                    # One ID per store; retain newest shipment and larger stock.
                    if row["last_arrival"] > old["last_arrival"]:
                        old["last_arrival"] = row["last_arrival"]
                        old["arrival_age_days"] = row["arrival_age_days"]
                    old["current_ddi"] = max(old["current_ddi"], row["current_ddi"])
                    old["current_existence"] = max(old["current_existence"], row["current_existence"])
                    old["current_investment"] = max(old["current_investment"], row["current_investment"])
            del chunk
    return sorted(merged.values(), key=lambda r:(fold(r["store"]),r["catalog"],r["id_art"]))


def install(m):
    if getattr(m, "_V327_BONUS2_MODELS", False):
        return

    root = Path(m.DATA_ROOT) / "cache_bonus2"
    root.mkdir(parents=True, exist_ok=True)

    def canon(name):
        key = fold(name)
        for store in m.store_names(True):
            if fold(store) == key:
                return store
        return str(name or "")

    def source_for_month(month):
        if not re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", month):
            raise HTTPException(400, "Periodo inválido")
        yy, mm = [int(x) for x in month.split("-")]
        now = __import__("datetime").datetime.now(MX).date()
        if (yy,mm) > (now.year,now.month):
            return None
        sources = []
        for entry in m.load_manifest().get("capacities", []):
            path = m.resolve_entry_path(entry)
            if not path.is_file() or path.suffix.lower() != ".xlsx":
                continue
            report_day = m._capacity_report_date(entry)
            if (report_day.year,report_day.month) != (yy,mm) or report_day > now:
                continue
            sources.append((report_day, str(entry.get("uploaded_at") or ""), entry))
        return max(sources, default=None, key=lambda item:(item[0],item[1]))

    def cache_file(entry):
        key = str(entry.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key):
            raise ValueError("ID de corte inválido")
        return root / (key+"-"+_CACHE_VERSION+".json.gz")

    def scan(entry, cutoff, dest):
        try:
            path = m.resolve_entry_path(entry)
            records = build_bono2_cohort(path, cutoff)
            payload = {"status":"ready","records":records,"cutoff":cutoff.isoformat(),
                       "criteria":{"sales_30":0,"arrival_max_days":7,"tipo_catalogo":"VIGENTE"}}
            # Write atomically; an interrupted build must not leave corrupt JSON.
            temp = dest.with_name(dest.name+".tmp")
            with gzip.open(temp, "wt", encoding="utf-8", compresslevel=4) as stream:
                json.dump(payload, stream, ensure_ascii=False, separators=(",",":"))
            os.replace(temp, dest)
            counts = {}
            for x in records:
                counts[x["catalog"]] = counts.get(x["catalog"],0)+1
            print(f"[V327-B2] Listado listo corte={cutoff} registros={len(records)} rubros={counts}", flush=True)
        except Exception as exc:
            print(f"[V327-B2] Error preparando listado: {type(exc).__name__}: {str(exc)[:250]}", flush=True)
            # No fabricate a valid empty dataset on parser failures.
            payload={"status":"error","error":str(exc)[:250],"records":[]}
            temp=dest.with_name(dest.name+".tmp")
            with gzip.open(temp,"wt",encoding="utf-8") as stream:
                json.dump(payload,stream,ensure_ascii=False)
            os.replace(temp,dest)
        finally:
            with _JOB_LOCK:
                _JOBS.discard(str(dest))
            try:
                m._release_process_memory()
            except Exception:
                pass

    def get_dataset(entry, cutoff):
        path=cache_file(entry)
        if path.is_file():
            try:
                with gzip.open(path,"rt",encoding="utf-8") as stream:
                    return json.load(stream)
            except (OSError, ValueError):
                path.unlink(missing_ok=True)
        with _JOB_LOCK:
            if str(path) not in _JOBS:
                _JOBS.add(str(path))
                threading.Thread(target=scan,args=(dict(entry),cutoff,path),daemon=True,name="b2-v327-catalog").start()
        return {"status":"pending","records":[],"cutoff":cutoff.isoformat()}

    def payload(request, month="",store=""):
        actor = m.require_user(request)
        if not month:
            month = __import__("datetime").datetime.now(MX).strftime("%Y-%m")
        stores = m.store_names(True)
        restricted = str(actor.get("role") or "").lower() in RESTRICTED
        allowed = canon(actor.get("store")) if restricted else None
        if restricted and allowed not in stores:
            raise HTTPException(403,"No tienes tienda asignada")
        if restricted and store and canon(store) != allowed:
            raise HTTPException(403,"No puedes consultar otra tienda")
        selected = allowed if restricted else canon(store) if store else "Compañía"
        if selected not in stores and selected != "Compañía":
            selected = "Compañía"

        pick=source_for_month(month)
        report_date=pick[0] if pick else None
        entry=pick[2] if pick else None
        result=get_dataset(entry,report_date) if entry else {"status":"missing","records":[]}
        all_rows=result.get("records") or []
        by_store={name:[] for name in stores}
        for row in all_rows:
            name=canon(row.get("store"))
            if name in by_store:
                by_store[name].append(row)
        ranking=[]
        for name in stores:
            xs=by_store[name]
            average=(sum(x["current_ddi"] for x in xs)/len(xs)) if xs else None
            ranking.append({"store":name,"models":len(xs),"avg_ddi":average,
                            "investment":sum(x["current_investment"] for x in xs),
                            "classification":"En seguimiento" if result["status"]=="ready" else "Procesando"})
        ranking.sort(key=lambda x:(-x["models"],x["store"]))
        for rank,row in enumerate(ranking,1):
            row["rank"]=rank if row["models"] else None
        rows=by_store.get(selected,[]) if selected in by_store else []
        pending=result["status"]=="pending"
        stats={"models":len(rows),"sales_30":0 if result["status"]=="ready" else None,
               "avg_ddi":sum(x["current_ddi"] for x in rows)/len(rows) if rows else None,
               "existence":sum(x["current_existence"] for x in rows),
               "investment":sum(x["current_investment"] for x in rows),
               "catalog_counts":{c:sum(1 for x in rows if x["catalog"]==c) for c in CATALOGS}}
        all_months=sorted({month,*[
            str(m._capacity_report_date(e))[:7]
            for e in m.load_manifest().get("capacities",[])
            if m.resolve_entry_path(e).is_file()
        ]},reverse=True)
        labels = {
          1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
          7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
        return {
            "version":"V327-BONUS2-ZERO-SALES-RECENT-ARRIVALS",
            "b2_cohort":True,
            "month":month,
            "months":[{"value":v,"label":labels[int(v[5:7])]+" "+v[:4]} for v in all_months if len(v)==7],
            "stores": ([allowed] if restricted else ["Compañía",*stores]),
            "selected_store":selected,
            "can_admin":str(actor.get("role") or "").lower() in ("superadmin","admin"),
            "source_dates":{"opening_capacity":report_date.isoformat() if report_date else "",
                            "current_capacity":report_date.isoformat() if report_date else ""},
            "processing":{"capacity":pending,"sales":False},
            "source_error":result.get("error") or "",
            "summary":{"inventory":{},"sales_pct":None,"stores_total":len(stores)},
            "selected":{"formula":"Catálogos Abrigador, Licencias y Básicos · Tipo catálogo VIGENTE · 0 ventas en 30 días · última llegada de 0 a 7 días al corte"},
            "ranking":ranking,
            "details":rows,
            "b2_stats":stats,
            "cutoff_date":report_date.isoformat() if report_date else "",
            "b2_status":result["status"],
        }

    @m.app.get("/api/bonuses-b2-v327")
    def get_bono2(request:Request,month:str="",store:str="Compañía"):
        return payload(request,month,store)

    m._v327_bonus2_payload=payload
    m._V327_BONUS2_MODELS=True
    print("[V327-B2] Cartera aislada del Bono 2 habilitada (0 venta 30d, llegada <=7 días).",flush=True)
