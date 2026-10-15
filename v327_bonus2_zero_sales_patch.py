"""V328 · Bono 2 con cartera independiente en el corte INICIAL del mes.

- Tipo catálogo = VIGENTE y CATALOGO comercial oficial = Abrigador/Licencias/Básicos.
- Ventas en piezas de los últimos 30 días = cero en el corte inicial.
- Última entrada de CEDIS a tienda AL MENOS 7 días antes de ese mismo corte.
- No se incluyen productos recién ingresados (0-6 días al corte).
- Se valida cada ID con todas sus filas de tienda para no esconder ventas o
  ingresos recientes en otras variantes del mismo ID.
No altera Bono 1 ni sus cálculos, cortes históricos o los Bonos 3–6.
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
_CACHE_VERSION = "v328-initial-7days"  # Nueva cartera; nunca reutilizar caché de corte actual
_JOBS = set()
_JOB_LOCK = threading.Lock()
_SCAN_LIMIT = threading.BoundedSemaphore(1)


def fold(v):
    return "".join(c for c in unicodedata.normalize("NFKD", str(v or "")) if not unicodedata.combining(c)).upper().strip()


def read_bono2_rows(raw, cutoff: date, source_path):
    """Rows eligible by *catalog*, before sales/date qualification.

    Keep all variants for a store+ID so an unsold variant cannot hide another
    variant that sold merchandise or was replenished in the last seven days.
    Missing sales/dates stay unknown, never synthesized as zero or an old date.
    """
    import pandas as pd
    from commercial.parsers import _capacity_date_series, _normalize_capacity_source

    required = ("TIPO CATALOGO MAX VIG", "VTA EN PZAS 30", "ULTIMA ENTRADA CEDIS A TIENDA",
                "CATALOGO", "ID_ART", "TIENDA", "MODELO")
    absent = [k for k in required if k not in raw.columns]
    if absent:
        raise ValueError("Columnas de Capacidades no disponibles: " + ", ".join(absent))

    is_vigente = raw["TIPO CATALOGO MAX VIG"].astype(str).map(fold).eq("VIGENTE")
    catalogs = classify_bonus_catalogs_from_source(raw["CATALOGO"])
    eligible_catalog = catalogs.isin(CATALOGS)
    matched = is_vigente & eligible_catalog
    if not bool(matched.any()):
        return []

    selected = raw.loc[matched].copy()
    valid_source = (
        selected["TIENDA"].astype(str).str.strip().ne("")
        & ~selected["TIENDA"].astype(str).isin(["nan", "None"])
        & selected["MODELO"].astype(str).str.strip().ne("")
        & ~selected["MODELO"].astype(str).isin(["nan", "None"])
    )
    selected = selected.loc[valid_source]
    if selected.empty:
        return []

    # Preserve exact row alignment across parser normalization, which resets
    # indexes. ISO strings are parsed year-first; Excel serial dates still work.
    original_dates = selected["ULTIMA ENTRADA CEDIS A TIENDA"]
    dates = _capacity_date_series(original_dates)
    raw_iso = original_dates.astype(str).str.strip()
    explicit_iso = pd.to_datetime(
        raw_iso.where(raw_iso.str.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}")),
        format="%Y-%m-%d", errors="coerce",
    )
    dates = dates.where(explicit_iso.isna(), explicit_iso).reset_index(drop=True)
    sales = pd.to_numeric(selected["VTA EN PZAS 30"], errors="coerce").reset_index(drop=True)
    selected = selected.reset_index(drop=True)
    normalized = _normalize_capacity_source(selected, source_path)
    if len(normalized) != len(dates) or len(normalized) != len(sales):
        raise ValueError("No coinciden los datos de ventas, fecha e ID del corte inicial")
    normalized_catalogs = classify_bonus_catalogs_from_source(normalized["Catálogo comercial"])

    result = []
    for idx, row in normalized.iterrows():
        id_art = str(row.get("ID_ART") or "").strip()
        if not re.fullmatch(r"\d{1,15}", id_art):
            continue
        catalog = str(normalized_catalogs.loc[idx] or "")
        if catalog not in CATALOGS:
            continue
        arriving = dates.iloc[idx]
        age = (cutoff - arriving.date()).days if not pd.isna(arriving) else None
        pieces = sales.iloc[idx]
        sale_count = float(pieces) if not pd.isna(pieces) and math.isfinite(float(pieces)) else None

        def numeric(key):
            try:
                value = float(row.get(key) or 0)
                return value if math.isfinite(value) else 0.0
            except (ValueError, TypeError):
                return 0.0

        result.append({
            "store": str(row.get("Tienda") or "").strip(),
            "id_art": id_art,
            "model": str(row.get("Modelo") or id_art),
            "catalog": catalog,
            "sales_30": sale_count,
            "last_arrival": arriving.date().isoformat() if not pd.isna(arriving) else None,
            "arrival_age_days": age,
            "initial_ddi": numeric("DDI"),
            "initial_existence": numeric("Existencia"),
            "initial_investment": numeric("Inversión"),
            # Not comparable until a subsequent period cut is evaluated.
            "current_ddi": None,
            "current_existence": None,
            "current_investment": None,
            "ddi_reduction_pct": None,
            "investment_reduction_pct": None,
        })
    return result


def qualify_bono2_rows(raw, cutoff: date, source_path):
    """Per-row rule: >=7 elapsed days before initial cutoff and 0 sales/30d."""
    return [
        row for row in read_bono2_rows(raw, cutoff, source_path)
        if row["sales_30"] == 0
        and row["arrival_age_days"] is not None
        and row["arrival_age_days"] >= 7
    ]


def build_bono2_cohort(source, cutoff: date):
    """Read the assigned *initial* XLSX in chunks and qualify by store+article."""
    from commercial.parsers import _iter_fast_capacity_xlsx
    if source.suffix.lower() != ".xlsx":
        raise ValueError("El corte inicial debe cargarse en formato XLSX para Bonos 2")
    merged = {}
    with _SCAN_LIMIT:
        for chunk in _iter_fast_capacity_xlsx(source, chunk_rows=1000):
            for row in read_bono2_rows(chunk, cutoff, source):
                key = (fold(row["store"]), row["id_art"])
                old = merged.get(key)
                if old is None:
                    old = dict(row)
                    old["_arrival_missing"] = row["arrival_age_days"] is None
                    old["_catalog_mismatch"] = False
                    merged[key] = old
                    continue
                # Every variant of the same ID must have 0 sales. The newest
                # delivery is decisive; use the sum of sales across variants.
                if old["sales_30"] is None or row["sales_30"] is None:
                    old["sales_30"] = None
                else:
                    old["sales_30"] += row["sales_30"]
                old["_arrival_missing"] |= row["arrival_age_days"] is None
                old["_catalog_mismatch"] |= row["catalog"] != old["catalog"]
                if row["last_arrival"] and (
                    not old["last_arrival"] or row["last_arrival"] > old["last_arrival"]
                ):
                    old["last_arrival"] = row["last_arrival"]
                    old["arrival_age_days"] = row["arrival_age_days"]
                old["initial_ddi"] = max(old["initial_ddi"], row["initial_ddi"])
                old["initial_existence"] += row["initial_existence"]
                old["initial_investment"] += row["initial_investment"]
            del chunk

    records = []
    for row in merged.values():
        if row.pop("_arrival_missing") or row.pop("_catalog_mismatch"):
            continue
        if row["sales_30"] != 0 or row["arrival_age_days"] is None or row["arrival_age_days"] < 7:
            continue
        records.append(row)
    return sorted(records, key=lambda row:(fold(row["store"]), row["catalog"], row["id_art"]))


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

    def processed_entries():
        # Igual que Bono 1: sólo cortes validados; no recorrer ni rehacer hash
        # de todos los Excel en cada petición HTTP.
        manifest=Path(m.COMMERCIAL_DATA_ROOT)/"manifest.json"
        try:
            payload=json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
        except (OSError, ValueError):
            payload={}
        entries=list(payload.get("capacities") or [])+list(payload.get("bonus_initial_capacity_entries") or [])
        initial_ids={
            str(x.get("entry_id") if isinstance(x,dict) else x)
            for x in (payload.get("bonus_initial_cuts") or {}).values()
        }
        return [
            entry for entry in entries
            if str(entry.get("status") or "").strip().lower()=="procesado"
            and not bool(entry.get("bonus_initial_only"))
            and str(entry.get("id") or "") not in initial_ids
        ]

    def source_for_month(month):
        """Exactly the same initial cut chosen by Bono 1 (including explicit assignments)."""
        if not re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", month):
            raise HTTPException(400, "Periodo inválido")
        selector = getattr(m, "_sales_bonus_opening_capacity_v293", None)
        if not callable(selector):
            raise HTTPException(503, "No está disponible el corte inicial de Bonos")
        pick = selector(month)
        if not pick:
            return None
        # Do not substitute an unrelated current cut if the initial source is absent.
        path = m.resolve_entry_path(pick[2])
        if not path.is_file():
            raise HTTPException(503, "El archivo asignado al corte inicial no se encuentra")
        return pick


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
                       "criteria":{"sales_30":0,"arrival_min_days":7,"tipo_catalogo":"VIGENTE","source":"initial"}}
            # Write atomically; an interrupted build must not leave corrupt JSON.
            temp = dest.with_name(dest.name+".tmp")
            with gzip.open(temp, "wt", encoding="utf-8", compresslevel=4) as stream:
                json.dump(payload, stream, ensure_ascii=False, separators=(",",":"))
            os.replace(temp, dest)
            counts = {}
            for x in records:
                counts[x["catalog"]] = counts.get(x["catalog"],0)+1
            print(f"[V328-B2] Cartera de corte INICIAL lista corte={cutoff} registros={len(records)} rubros={counts}", flush=True)
        except Exception as exc:
            print(f"[V328-B2] Error preparando listado: {type(exc).__name__}: {str(exc)[:250]}", flush=True)
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
            average=(sum(x["initial_ddi"] for x in xs)/len(xs)) if xs else None
            ranking.append({"store":name,"models":len(xs),"avg_ddi":average,
                            "investment":sum(x["initial_investment"] for x in xs),
                            "classification":"En seguimiento" if result["status"]=="ready" else "Procesando"})
        ranking.sort(key=lambda x:(-x["models"],x["store"]))
        for rank,row in enumerate(ranking,1):
            row["rank"]=rank if row["models"] else None
        rows=by_store.get(selected,[]) if selected in by_store else []
        # En Compañía, tarjetas macro de todas las tiendas, no cero modelos.
        # El detalle requiere seleccionar una tienda concreta, como Bono 1.
        stat_rows=all_rows if selected=="Compañía" else rows
        pending=result["status"]=="pending"
        stats={"models":len(stat_rows),"sales_30":0 if result["status"]=="ready" else None,
               "avg_ddi":sum(x["initial_ddi"] for x in stat_rows)/len(stat_rows) if stat_rows else None,
               "existence":sum(x["initial_existence"] for x in stat_rows),
               "investment":sum(x["initial_investment"] for x in stat_rows),
               "catalog_counts":{c:sum(1 for x in stat_rows if x["catalog"]==c) for c in CATALOGS}}
        all_months=sorted({month,*[
            str(m._capacity_report_date(e))[:7]
            for e in processed_entries()
            if m.resolve_entry_path(e).is_file()
        ]},reverse=True)
        labels = {
          1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
          7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
        return {
            "version":"V328-BONUS2-INITIAL-ZERO-SALES-AGE-GTE7",
            "b2_cohort":True,
            "month":month,
            "months":[{"value":v,"label":labels[int(v[5:7])]+" "+v[:4]} for v in all_months if len(v)==7],
            "stores": ([allowed] if restricted else ["Compañía",*stores]),
            "selected_store":selected,
            "can_admin":str(actor.get("role") or "").lower() in ("superadmin","admin"),
            "source_dates":{"opening_capacity":report_date.isoformat() if report_date else "",
                            "current_capacity":""},
            "processing":{"capacity":pending,"sales":False},
            "source_error":result.get("error") or "",
            "summary":{"inventory":{},"sales_pct":None,"stores_total":len(stores)},
            "selected":{"formula":"Corte inicial · Abrigador, Licencias y Básicos · Tipo VIGENTE · 0 ventas en 30 días · última llegada de hace 7 días o más"},
            "ranking":ranking,
            "details":rows,
            "b2_stats":stats,
            "cutoff_date":report_date.isoformat() if report_date else "",
            "cutoff_source":"initial",
            "cutoff_name":str(entry.get("name") or "") if entry else "",
            "b2_status":result["status"],
        }

    @m.app.get("/api/bonuses-b2-v327")
    def get_bono2(request:Request,month:str="",store:str="Compañía"):
        return payload(request,month,store)

    m._v327_bonus2_payload=payload
    m._V327_BONUS2_MODELS=True
    print("[V328-B2] Corte inicial: 0 venta en 30 días y llegada de hace 7 días o más.",flush=True)
