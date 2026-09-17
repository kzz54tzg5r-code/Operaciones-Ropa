"""V165 · Ajustes solicitados 17-sep-2026.

Alcance:
- Cambios y Muertos: Vista estable, elimina tabs redundantes Operación/Día/Semana/Mes,
  integra Matriz de recolección dentro de Recorridos y alerta colaboradores sin registro.
- Matriz: lunes-domingo y bloques horarios completos, del primer al último horario real.
- Operación: resumen exclusivo de Origen (Colgado+Doblado), Mercancía liberada y navegación
  estable sin Resumen duplicado.
- Comercial: filtro Estatus, MARCA real (no Marca Price), iconos consistentes, reparación
  definitiva de /api/commercial-sales-summary 422, filtros internos con el lenguaje del
  filtro superior y todos los modelos que conforman el 80%.
"""
from __future__ import annotations

from collections import defaultdict
from contextvars import ContextVar
from datetime import date, datetime, timedelta
from pathlib import Path
import math
import re
import unicodedata

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse


_STATUS_CTX: ContextVar[str] = ContextVar("v165_commercial_status", default="Todos")


def install(m):
    if getattr(m, "_V165_REQUESTED_FIXES", False):
        return

    # ------------------------------------------------------------------
    # 1. Cambios y Muertos: Matriz ya no es pestaña independiente.
    # ------------------------------------------------------------------
    m.REPORT_TABS.pop("operations.collection", None)
    try:
        with m.db() as con:
            con.execute("DELETE FROM report_tab_visibility WHERE tab_key='operations.collection'")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 2. Comercial: MARCA debe ganar sobre MARCA PRICE.
    #    Se intercepta el lector sin reescribir el parser completo.
    # ------------------------------------------------------------------
    try:
        import commercial.parsers as cp
        if not getattr(cp, "_V165_BRAND_PRIORITY", False):
            _old_series = cp._series

            def _series_v165(df, candidates, default="", contains=False):
                values = list(candidates or [])
                normalized = [cp.norm_text(x) for x in values]
                if "MARCA" in normalized and "MARCA PRICE" in normalized:
                    rest = [x for x in values if cp.norm_text(x) not in ("MARCA", "MARCA PRICE")]
                    values = ["MARCA", "MARCA PRICE", *rest]
                return _old_series(df, values, default, contains=contains)

            cp._series = _series_v165
            cp._V165_BRAND_PRIORITY = True
        m.read_capacity_file = cp.read_capacity_file
    except Exception as exc:
        print(f"[V165] No fue posible priorizar MARCA: {type(exc).__name__}: {exc}", flush=True)

    # El cache normalizado guarda el valor de Marca, por lo que se invalida UNA sola
    # vez para reconstruirlo desde el Excel original con MARCA y Estatus correctos.
    try:
        marker = Path(m.DATA_ROOT) / ".v165_capacity_brand_status_rebuilt"
        if not marker.exists():
            manifest = m.load_manifest() or {}
            for entry in list(manifest.get("capacities") or []):
                cache_rel = str(entry.get("cache_file") or "").strip()
                if cache_rel:
                    cache_path = Path(m.DATA_ROOT) / cache_rel
                    try:
                        if cache_path.exists() and "capacity_normalized" in cache_path.parts:
                            cache_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    try:
                        m.update_entry("capacities", str(entry.get("id") or ""), cache_file="")
                    except Exception:
                        pass
            try:
                m._CAPACITY_FRAME_CACHE.update({"path":"", "mtime":None, "frame":None})
            except Exception:
                pass
            marker.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    except Exception as exc:
        print(f"[V165] Cache comercial: {type(exc).__name__}: {exc}", flush=True)

    # ------------------------------------------------------------------
    # 3. Filtro Estatus comercial autoritativo en todos los endpoints de capacidad.
    # ------------------------------------------------------------------
    def _norm(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.casefold().strip().split())

    def _apply_status(work):
        status = str(_STATUS_CTX.get() or "Todos").strip()
        if work is None or getattr(work, "empty", True) or status in ("", "Todos", "Todas"):
            return work
        if "Estatus comercial" not in work.columns:
            return work
        try:
            keys = work["Estatus comercial"].fillna("").astype(str).map(_norm)
            return work.loc[keys == _norm(status)].copy()
        except Exception:
            return work

    if hasattr(m, "_capacity_scope_v45") and not getattr(m, "_V165_SCOPE_STATUS", False):
        _old_scope45 = m._capacity_scope_v45

        def _scope45_v165(frame, store="Compañía", section="Todas", catalog="Todos", add_area=False):
            return _apply_status(_old_scope45(frame, store, section, catalog, add_area=add_area))

        m._capacity_scope_v45 = _scope45_v165
        if hasattr(m, "_scope_capacity"):
            _old_scope = m._scope_capacity

            def _scope_v165(frame, store="Compañía", section="Todas", catalog="Todos"):
                return _apply_status(_old_scope(frame, store, section, catalog))

            m._scope_capacity = _scope_v165
        m._V165_SCOPE_STATUS = True

    @m.app.middleware("http")
    async def _v165_status_context(request, call_next):
        token = _STATUS_CTX.set(str(request.query_params.get("status") or "Todos"))
        try:
            return await call_next(request)
        finally:
            _STATUS_CTX.reset(token)

    @m.app.get("/api/commercial/status-options-v165")
    def commercial_status_options_v165(request: Request, week: str = ""):
        m.require_user(request)
        frame = m._capacity_frame_for_period(week or "")
        if frame is None or frame.empty or "Estatus comercial" not in frame.columns:
            return {"values": []}
        values = []
        for value in frame["Estatus comercial"].fillna("").astype(str).tolist():
            value = " ".join(value.split()).strip()
            if value and value.lower() not in ("nan", "none") and value not in values:
                values.append(value)
        values.sort(key=lambda x: _norm(x))
        return {"values": values}

    # ------------------------------------------------------------------
    # 4. Modelos 80/20: devolver TODOS los modelos necesarios para llegar a 80%.
    # ------------------------------------------------------------------
    if hasattr(m, "_capacity_model_rows") and not getattr(m, "_V165_ALL_80", False):
        _old_model_rows = m._capacity_model_rows

        def _all_80_rows(store="Compañía", section="Todas", period="", catalog="Todos"):
            pd = m.pd
            np = m.np
            frame = m._capacity_frame_for_period(period)
            work = m._capacity_scope_v45(frame, store, section, catalog)
            if work is None or work.empty or "ID_ART" not in work.columns:
                return []
            work = work.copy()
            work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
            work = work[~work["__id"].isin(["", "nan", "None"])]
            if work.empty:
                return []
            pcol, vcol = m._capacity_period_columns(period)
            tmp = pd.DataFrame({"__id": work["__id"]})
            mapping = {
                "existence":"Existencia", "floor":"Existencia piso", "warehouse":"Existencia bodega",
                "suggested":"VPD", "capacity":"Capacidad", "sales_pzas":pcol,
                "sales_value":vcol, "sales_pzas_30":"Venta pzas 30", "pzas_ult_cedis":"Pzas última entrada",
            }
            for dst, src in mapping.items():
                tmp[dst] = pd.to_numeric(work[src], errors="coerce").fillna(0.0) if src in work.columns else 0.0
            agg = tmp.groupby("__id", sort=False).sum(numeric_only=True)
            if "DDI" in work.columns:
                ddi = pd.to_numeric(work["DDI"], errors="coerce").replace([np.inf, -np.inf], np.nan)
                agg = agg.join(ddi.groupby(work["__id"]).mean().rename("ddi"), how="left")
            else:
                agg["ddi"] = 0.0
            agg["ddi"] = pd.to_numeric(agg["ddi"], errors="coerce").fillna(0.0)
            meta_map = {"model":"Modelo", "brand":"Marca", "section":"Sección", "rubro":"Subcategoría"}
            for dst, src in meta_map.items():
                if src in work.columns:
                    s = work[src].fillna("").astype(str).str.strip().replace({"":"", "nan":"", "None":""})
                    first = pd.DataFrame({"__id":work["__id"], dst:s.replace("", pd.NA)}).groupby("__id", sort=False)[dst].first()
                    agg = agg.join(first, how="left")
                else:
                    agg[dst] = ""
            if "Última entrada CEDIS a tienda" in work.columns:
                dates = pd.to_datetime(work["Última entrada CEDIS a tienda"], errors="coerce")
                agg = agg.join(dates.groupby(work["__id"]).max().rename("ultima_cedis"), how="left")
            else:
                agg["ultima_cedis"] = pd.NaT
            models = agg.reset_index().sort_values(["sales_value", "sales_pzas", "existence"], ascending=[False, False, False]).reset_index(drop=True)
            total = float(models["sales_value"].sum())
            models["cum_share"] = models["sales_value"].cumsum() / total * 100 if total > 0 else 0.0
            if total > 0:
                hits = np.flatnonzero(models["cum_share"].to_numpy() >= 80.0)
                last = int(hits[0]) if len(hits) else len(models)-1
                models = models.iloc[:last+1].copy()
            else:
                models = models.head(50).copy()
            ids = set(models["__id"].astype(str))
            labels = work[work["__id"].isin(ids)].copy()

            def label_map(col, limit=3):
                if col not in labels.columns:
                    return {}
                z = labels[["__id", col]].copy()
                z[col] = z[col].fillna("").astype(str).str.strip()
                z = z[~z[col].isin(["", "nan", "None"])].drop_duplicates()
                if z.empty:
                    return {}
                return z.groupby("__id", sort=False)[col].agg(lambda s: m._combine_labels(s, limit)).to_dict()

            loc_col = "Ubicación detalle" if "Ubicación detalle" in labels.columns else ("Pasillo" if "Pasillo" in labels.columns else "")
            locations = label_map(loc_col) if loc_col else {}
            exhibitions = label_map("Exhibición", 5)
            stores = label_map("Tienda", 5)
            rows = []
            for idx, r in enumerate(models.to_dict("records"), 1):
                rid = str(r.get("__id") or "")
                cap = float(r.get("capacity") or 0); ex = float(r.get("existence") or 0)
                dt = r.get("ultima_cedis")
                try:
                    dt_txt = pd.Timestamp(dt).strftime("%Y-%m-%d") if pd.notna(dt) else ""
                except Exception:
                    dt_txt = ""
                rows.append({
                    "id_art":rid, "model":str(r.get("model") or rid), "brand":str(r.get("brand") or "Sin marca"),
                    "section":str(r.get("section") or "Sin sección"), "rubro":str(r.get("rubro") or "Sin rubro"),
                    "location":locations.get(rid, ""), "exhibition":exhibitions.get(rid, ""),
                    "store":stores.get(rid, store if store != "Compañía" else "Compañía"), "rank":idx,
                    "suggested":float(r.get("suggested") or 0), "existence":ex, "capacity":cap,
                    "occupancy":ex/cap*100 if cap else None, "sales_pzas_30":float(r.get("sales_pzas_30") or 0),
                    "sales_pzas":float(r.get("sales_pzas") or 0), "sales_value":float(r.get("sales_value") or 0),
                    "floor":float(r.get("floor") or 0), "warehouse":float(r.get("warehouse") or 0),
                    "ddi":float(r.get("ddi") or 0), "ultima_cedis":dt_txt,
                    "pzas_ult_cedis":float(r.get("pzas_ult_cedis") or 0), "cum_share":float(r.get("cum_share") or 0),
                    "recurrence_weeks":0,
                })
            return rows

        def _model_rows_v165(store="Compañía", section="Todas", mode="80_20", period="", catalog="Todos"):
            key = str(mode or "").lower()
            if key in ("80_20", "8020", "top", "champions"):
                return _all_80_rows(store, section, period, catalog)
            return _old_model_rows(store, section, mode, period, catalog)

        m._capacity_model_rows = _model_rows_v165
        m._V165_ALL_80 = True

    # ------------------------------------------------------------------
    # 5. Ventas: sustituye definitivamente la ruta que seguía respondiendo 422.
    # ------------------------------------------------------------------
    for route in list(m.app.router.routes):
        if getattr(route, "path", None) == "/api/commercial-sales-summary" and "GET" in (getattr(route, "methods", set()) or set()):
            try:
                m.app.router.routes.remove(route)
            except ValueError:
                pass

    @m.app.get("/api/commercial-sales-summary")
    async def commercial_sales_summary_v165(request: Request, year: int | None = None, through_month: int | None = None, store: str = "Compañía"):
        actor = m.require_user(request)
        now = datetime.now()
        yy = int(year or now.year)
        cut = max(1, min(12, int(through_month or now.month)))
        try:
            scope = m.effective_store(actor, store)
        except Exception:
            scope = store
        scope = str(scope or "Compañía").strip() or "Compañía"

        entries = []
        for raw in list((m.load_manifest() or {}).get("sales") or []):
            item = dict(raw)
            y = int(item.get("year") or 0); mo = int(item.get("month") or 0)
            if not y or mo not in range(1, 13):
                continue
            path = m.resolve_entry_path(item)
            if path.suffix.lower() != ".pdf" or not path.exists():
                continue
            # Releer cuando la carga histórica no produjo venta o quedó con parser viejo.
            if float(item.get("total_sales") or 0) <= 0 or int(item.get("parser_version") or 0) < 113:
                try:
                    parsed = dict(m.parse_sales_pdf(path, y, mo) or {})
                    changes = {k: parsed.get(k) for k in (
                        "status","store","rows","stores","pages","total_pieces","total_sales","parser_version",
                        "source_line","source_method","detected_stores","diagnostic","rejected_pdf_value"
                    ) if k in parsed}
                    m.update_entry("sales", str(item.get("id") or ""), **changes)
                    item.update(changes)
                    try:
                        m.save_sales_pdf_snapshot(str(item.get("id") or ""), parsed)
                    except Exception:
                        pass
                except Exception as exc:
                    print(f"[V165-SALES] reparo {path.name}: {type(exc).__name__}: {exc}", flush=True)
            entries.append(item)

        def month_values(target_year, wanted_scope):
            latest = {}
            for e in entries:
                if int(e.get("year") or 0) != int(target_year):
                    continue
                mo = int(e.get("month") or 0)
                st = str(e.get("store") or "Compañía").strip() or "Compañía"
                key = (mo, _norm(st))
                old = latest.get(key)
                if old is None or str(e.get("uploaded_at") or "") >= str(old.get("uploaded_at") or ""):
                    latest[key] = e
            out = {}
            for mo in range(1, 13):
                values = []
                if _norm(wanted_scope) != _norm("Compañía"):
                    found = latest.get((mo, _norm(wanted_scope)))
                    if found: values = [found]
                else:
                    company = latest.get((mo, _norm("Compañía")))
                    if company and float(company.get("total_sales") or 0) > 0:
                        values = [company]
                    else:
                        values = [e for (mno, st), e in latest.items() if mno == mo and st != _norm("Compañía")]
                valid = [e for e in values if float(e.get("total_sales") or 0) > 0]
                out[mo] = {
                    "sales":sum(max(float(e.get("total_sales") or 0), 0.0) for e in values),
                    "pieces":sum(max(float(e.get("total_pieces") or 0), 0.0) for e in values),
                    "sources":len(valid),
                    "last_upload":max([str(e.get("uploaded_at") or "") for e in valid] or [""]),
                }
            return out

        current = month_values(yy, scope); previous = month_values(yy-1, scope)
        goals = {}
        try:
            with m.db() as con:
                for row in con.execute("SELECT month,target FROM sales_goals WHERE year=? AND store=?", (yy, scope)).fetchall():
                    goals[int(row["month"])] = float(row["target"] or 0)
        except Exception:
            pass
        labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        months = []
        for mo in range(1, 13):
            cur = float(current[mo]["sales"] or 0); prev = float(previous[mo]["sales"] or 0); goal = float(goals.get(mo, 0))
            months.append({
                "month":mo, "label":labels[mo-1], "target":goal, "current":cur, "previous":prev,
                "pieces":float(current[mo]["pieces"] or 0), "previous_pieces":float(previous[mo]["pieces"] or 0),
                "compliance":cur/goal*100 if goal else None, "growth":(cur/prev-1)*100 if prev else None,
                "sources":int(current[mo]["sources"] or 0),
            })
        goal_ytd = sum(float(x["target"] or 0) for x in months[:cut])
        current_ytd = sum(float(x["current"] or 0) for x in months[:cut])
        previous_ytd = sum(float(x["previous"] or 0) for x in months[:cut])
        source_count = sum(int(current[x]["sources"] or 0) for x in range(1, cut+1))
        last_upload = max([str(current[x]["last_upload"] or "") for x in range(1, cut+1)] or [""])
        available_years = sorted({int(e.get("year") or 0) for e in entries if int(e.get("year") or 0) > 0} | {yy, yy-1}, reverse=True)
        return {
            "year":yy, "previous_year":yy-1, "through_month":cut, "store":scope,
            "available_years":available_years, "months":months,
            "totals":{
                "goal_ytd":goal_ytd, "current_ytd":current_ytd, "previous_ytd":previous_ytd,
                "compliance_pct":current_ytd/goal_ytd*100 if goal_ytd else None,
                "growth_pct":(current_ytd/previous_ytd-1)*100 if previous_ytd else None,
                "gap_to_goal":current_ytd-goal_ytd if goal_ytd else None,
            },
            "has_sales":any(float(x["current"] or 0)>0 or float(x["previous"] or 0)>0 for x in months[:cut]),
            "source_count":source_count, "last_upload":last_upload,
            "editable":str(actor.get("role") or "") in ("superadmin", "admin"),
            "parser_version":165, "source_label":"Fuente: PDF de ventas mensuales",
        }

    # ------------------------------------------------------------------
    # 6. Fechas / periodos compartidos para alertas y resumen Origen.
    # ------------------------------------------------------------------
    def _bounds(ptype, value):
        ptype = str(ptype or "week").lower().strip(); value = str(value or "").strip(); today = date.today()
        if ptype == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date(); return d, d
        if ptype == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt: y,w = int(mt.group(1)), int(mt.group(2))
            else: iso=today.isocalendar(); y,w=iso.year,iso.week
            d=date.fromisocalendar(y,w,1); return d,d+timedelta(days=6)
        if ptype == "month":
            mt=re.fullmatch(r"(\d{4})-(\d{1,2})",value)
            if mt: y,mo=int(mt.group(1)),int(mt.group(2))
            else: y,mo=today.year,today.month
            d=date(y,mo,1); nxt=date(y+(1 if mo==12 else 0),1 if mo==12 else mo+1,1); return d,nxt-timedelta(days=1)
        if ptype == "year":
            y=int(value or today.year); return date(y,1,1),date(y,12,31)
        return date(2000,1,1), today

    @m.app.get("/api/operations/missing-productivity-v165")
    def missing_productivity_v165(request: Request, period_type: str="week", period_value: str="", store: str="Compañía"):
        actor=m.require_user(request); start,end=_bounds(period_type,period_value); st=m.effective_store(actor,store)
        known={}; current=set()
        for r in list((m.load_ops() or {}).get("rows") or []):
            name=" ".join(str(r.get("name") or "").split()).strip(); rs=str(r.get("store") or "").strip(); ds=str(r.get("date") or "")[:10]
            if not name or not rs or not ds: continue
            if st and st!="Compañía" and rs!=st: continue
            productive=float(r.get("productividad") or 0)>0 or float(r.get("acondicionado") or 0)>0 or float(r.get("ubicado") or 0)>0 or float(r.get("recolectadas") or 0)>0
            if not productive: continue
            try: d=date.fromisoformat(ds)
            except Exception: continue
            key=(rs,_norm(name))
            if d < start:
                old=known.get(key)
                if old is None or ds>old["last_date"]:
                    known[key]={"store":rs,"name":name,"last_date":ds,"last_activity":str(r.get("activity") or r.get("activity_original") or "")}
            if start<=d<=end:
                current.add(key)
        missing=[v for k,v in known.items() if k not in current]
        missing.sort(key=lambda x:(x["store"],x["name"]))
        return {"count":len(missing),"rows":missing,"start_date":start.isoformat(),"end_date":end.isoformat(),"store":st}

    # ------------------------------------------------------------------
    # 7. Matriz horaria: L-D, horas completas, integrada en Recorridos.
    # ------------------------------------------------------------------
    DAY_NAMES=("Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo")

    def _hour(value):
        raw=str(value or "").strip()
        if not raw or raw.lower() in ("nan","nat","none"): return None
        mt=re.search(r"(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)",raw)
        if mt:return int(mt.group(1))
        try:
            x=float(raw)
            if 0<=x<1:return int((x*24)%24)
        except Exception:pass
        return None

    @m.app.get("/api/operations/collection-hour-matrix-v165")
    def collection_hour_matrix_v165(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor=m.require_user(request); start,end=_bounds(period_type,period_value); st=m.effective_store(actor,store)
        records=[]
        for r in list((m.load_ops() or {}).get("rows") or []):
            ds=str(r.get("date") or "")[:10]
            try:d=date.fromisoformat(ds)
            except Exception:continue
            if d<start or d>end:continue
            rs=str(r.get("store") or "").strip()
            if st and st!="Compañía" and rs!=st:continue
            if str(area or "") not in ("","Todas","Todos") and _norm(r.get("area"))!=_norm(area):continue
            if str(activity or "") not in ("","Todas","Todos"):
                act=r.get("activity") or r.get("activity_original") or ""
                if _norm(act)!=_norm(activity):continue
            muertos=float(r.get("muertos") or 0);cajas=float(r.get("cajas") or 0);prob=float(r.get("probador") or 0)
            if muertos<=0 and cajas<=0 and prob<=0:continue
            h=_hour(r.get("start_time"));hend=_hour(r.get("end_time"))
            if h is None:continue
            records.append({"day":d.weekday(),"hour":h,"end_hour":hend if hend is not None else h,"store":rs,"name":" ".join(str(r.get("name") or "").split()).strip(),"muertos":muertos,"cajas":cajas,"probador":prob})
        if not records:
            return {"summary":{"pieces":0,"slots":0,"stores":0,"first_hour":None,"last_hour":None},"matrix":[],"source_totals":{"muertos":0,"cajas":0,"probador":0},"days":[],"stores":[]}
        first=min(r["hour"] for r in records);last=max(max(r["hour"],r["end_hour"]) for r in records)
        grouped=defaultdict(lambda:{"muertos":0.0,"cajas":0.0,"probador":0.0,"names":set(),"stores":set()})
        byday=defaultdict(lambda:{"muertos":0.0,"cajas":0.0,"probador":0.0})
        bystore=defaultdict(lambda:{"muertos":0.0,"cajas":0.0,"probador":0.0})
        totals={"muertos":0.0,"cajas":0.0,"probador":0.0}
        for r in records:
            g=grouped[(r["day"],r["hour"])]
            for k in totals:
                g[k]+=r[k];byday[r["day"]][k]+=r[k];bystore[r["store"]][k]+=r[k];totals[k]+=r[k]
            if r["name"]:g["names"].add(r["name"])
            if r["store"]:g["stores"].add(r["store"])
        matrix=[]
        for dayno in range(7):
            for hour in range(first,last+1):
                g=grouped[(dayno,hour)];total=g["muertos"]+g["cajas"]+g["probador"]
                matrix.append({"day":DAY_NAMES[dayno],"day_no":dayno,"hour":hour,"schedule":f"{hour:02d}:00","muertos":g["muertos"],"cajas":g["cajas"],"probador":g["probador"],"total":total,"responsible":", ".join(sorted(g["names"])),"stores":len(g["stores"])})
        days=[]
        for dno in range(7):
            x=byday[dno];days.append({"day":DAY_NAMES[dno],**x,"total":x["muertos"]+x["cajas"]+x["probador"]})
        stores=[]
        for name,x in bystore.items():stores.append({"store":name,**x,"total":x["muertos"]+x["cajas"]+x["probador"]})
        stores.sort(key=lambda x:(-x["total"],x["store"]))
        return {"summary":{"pieces":sum(totals.values()),"slots":sum(1 for x in matrix if x["total"]>0),"stores":len(bystore),"first_hour":first,"last_hour":last},"matrix":matrix,"source_totals":totals,"days":days,"stores":stores}

    # ------------------------------------------------------------------
    # 8. Operación: resumen EXCLUSIVO de Origen, sin Cambios y Muertos.
    # ------------------------------------------------------------------
    @m.app.get("/api/operation/origin-summary-v165")
    def operation_origin_summary_v165(request: Request, period_type: str="day", period_value: str="", store: str="Compañía"):
        actor=m.require_user(request);start,end=_bounds(period_type,period_value);ss,es=start.isoformat(),end.isoformat()
        selected=m.effective_store(actor,store)
        stores=[selected] if selected!="Compañía" else list(m.store_names(True) or getattr(m,"PROJECT_STORES",[]))
        if not stores:return {"summary":{},"stores":[],"alerts":[]}
        ph=",".join("?" for _ in stores)
        with m.db() as con:
            caps=[dict(r) for r in con.execute(f"SELECT date,store,arrival,released,pending_manual FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ({ph})",(es,*stores)).fetchall()]
            prod=[dict(r) for r in con.execute(f"SELECT date,store,employee_no,employee_name,origin,pieces FROM operation_productivity WHERE origin IN ('Colgado','Doblado') AND date<=? AND store IN ({ph})",(es,*stores)).fetchall()]
            standards={str(r["origin"]):float(r["pieces_per_shift"] or 0) for r in con.execute("SELECT origin,pieces_per_shift FROM operation_standards").fetchall()}
        standards.setdefault("Colgado",1228.0);standards.setdefault("Doblado",906.0)
        period_caps=[r for r in caps if ss<=str(r["date"])<=es];period_prod=[r for r in prod if ss<=str(r["date"])<=es]
        arrival=sum(float(r.get("arrival") or 0) for r in period_caps);released=sum(float(r.get("released") or 0) for r in period_caps);processed=sum(float(r.get("pieces") or 0) for r in period_prod)
        previous_arrival=sum(float(r.get("arrival") or 0) for r in caps if str(r["date"])<ss);previous_processed=sum(float(r.get("pieces") or 0) for r in prod if str(r["date"])<ss);pending_start=max(previous_arrival-previous_processed,0.0)
        explicit=[r for r in period_caps if r.get("pending_manual") is not None];explicit.sort(key=lambda x:str(x["date"]))
        pending=float(explicit[-1]["pending_manual"] or 0) if explicit else max(pending_start+arrival-processed,0.0)
        people={};targets=0.0;target_keys=set()
        for r in period_prod:
            key=(str(r.get("employee_no") or r.get("employee_name") or ""),str(r["store"]));people.setdefault(key,{"pieces":0.0,"days":set()});people[key]["pieces"]+=float(r.get("pieces") or 0);people[key]["days"].add(str(r["date"]))
            tk=(str(r["date"]),str(r["store"]),str(r["origin"]))
            if tk not in target_keys:target_keys.add(tk);targets+=float(standards.get(str(r["origin"]),0) or 0)
        empdays=sum(max(len(v["days"]),1) for v in people.values());avg=sum(v["pieces"] for v in people.values())/empdays if empdays else 0.0
        efficiency=processed/(pending_start+arrival)*100 if pending_start+arrival>0 else 0.0;compliance=processed/targets*100 if targets else 0.0
        store_rows=[];required_total=0
        for st in stores:
            pc=sum(float(r.get("pieces") or 0) for r in period_prod if r["store"]==st and r["origin"]=="Colgado");pdbl=sum(float(r.get("pieces") or 0) for r in period_prod if r["store"]==st and r["origin"]=="Doblado");mix=pc+pdbl
            weighted=((pc*standards["Colgado"]+pdbl*standards["Doblado"])/mix) if mix>0 else (standards["Colgado"]+standards["Doblado"])/2
            st_caps=[r for r in caps if r["store"]==st];st_prod=[r for r in prod if r["store"]==st]
            sa=sum(float(r.get("arrival") or 0) for r in st_caps if ss<=str(r["date"])<=es);sr=sum(float(r.get("released") or 0) for r in st_caps if ss<=str(r["date"])<=es);sp=sum(float(r.get("pieces") or 0) for r in st_prod if ss<=str(r["date"])<=es)
            pre=max(sum(float(r.get("arrival") or 0) for r in st_caps if str(r["date"])<ss)-sum(float(r.get("pieces") or 0) for r in st_prod if str(r["date"])<ss),0.0)
            ex=[r for r in st_caps if ss<=str(r["date"])<=es and r.get("pending_manual") is not None];ex.sort(key=lambda x:str(x["date"]));pend=float(ex[-1]["pending_manual"] or 0) if ex else max(pre+sa-sp,0.0)
            req=int(math.ceil(pend/weighted)) if pend>0 and weighted>0 else 0;required_total+=req
            store_rows.append({"store":st,"arrival":sa,"processed":sp,"released":sr,"pending":pend,"required":req})
        alerts=[]
        if pending>0:alerts.append({"level":"warn","text":f"Pendiente de Origen: {pending:,.0f} piezas por procesar."})
        if not alerts:alerts=[{"level":"ok","text":"Sin alertas críticas de Origen para el periodo consultado."}]
        return {"summary":{"arrival_origin":arrival,"processed":processed,"released":released,"pending":pending,"efficiency_pct":efficiency,"productivity_avg":avg,"compliance_pct":compliance,"collaborators":len(people),"required":required_total},"stores":store_rows,"alerts":alerts}

    # ------------------------------------------------------------------
    # HTML / CSS / JS final de V165.
    # ------------------------------------------------------------------
    css = r'''<style id="v165-requested-fixes-css">
/* Cambios y Muertos: Vista sustituye Día/Semana/Mensual y Operación vive aparte. */
#operativoNav [data-tab-key="operations.day"],#operativoNav [data-tab-key="operations.week"],#operativoNav [data-tab-key="operations.month"],#operativoNav [data-tab-key="operations.operation"],#operativoNav [data-tab-key="operations.collection"],#operativoNav [data-opview="Operación"]{display:none!important}
body[data-v163-module="operativo"] #operativoNav:not(.hidden){grid-template-columns:repeat(7,minmax(0,1fr))!important}
/* Facadas de filtros internos Comercial: mismo lenguaje del filtro superior. */
.v165-inline-filters{display:flex;gap:9px;align-items:end;flex-wrap:wrap;background:#fff;border:1px solid #d6e3f1;border-radius:13px;padding:10px;margin:8px 0}
.v165-inline-field{min-width:180px;flex:0 1 260px;position:relative}.v165-inline-field label{display:block;font-size:8px;color:#60758f;font-weight:950;text-transform:uppercase;margin:0 0 5px 2px}.v165-inline-field select{width:100%;height:42px;border:1px solid #cbdcec;border-radius:10px;padding:7px 30px 7px 36px;color:#103f7d;font-weight:850;background:#fff}.v165-inline-field:before{content:'▦';position:absolute;left:12px;bottom:11px;color:#176fe8;font-size:16px}.v165-original-switches{display:none!important}
#champSection.v165-top-select,#slowSection.v165-top-select{display:block!important;width:100%;height:42px;border:1px solid #cbdcec;border-radius:10px;padding:7px 12px;color:#103f7d;font-weight:850;background:#fff}
.panel.compact-filter.v165-filter-panel{border:1px solid #d6e3f1!important;border-radius:13px!important;padding:10px!important;background:#fff!important}
/* Alerta productividad faltante */
#v165MissingProd{background:#fff;border:1px solid #f2d39a;border-radius:13px;padding:12px;margin:10px 0}#v165MissingProd h3{margin:0 0 6px;color:#103f7d;font-size:13px}#v165MissingProd .v165-miss-count{display:inline-block;background:#fff3cd;color:#8a5c00;border-radius:999px;padding:4px 8px;font-size:9px;font-weight:900}.v165-miss-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:8px}.v165-miss-item{background:#fff8e8;border:1px solid #f6dfb0;border-radius:9px;padding:8px;font-size:9px}.v165-miss-item b{display:block;color:#173f78}.v165-miss-item span{color:#7b6a49;font-size:8px}
/* Matriz dentro de Recorridos */
#v165MatrixRoutes{margin:0 0 14px}.v165-matrix-card{background:#fff;border:1px solid #d8e4f0;border-radius:13px;padding:12px;margin:8px 0}.v165-matrix-card h3{margin:0 0 8px;color:#103f7d;font-size:14px}.v165-matrix-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.v165-matrix-kpi{background:#fff;border:1px solid #d8e4f0;border-radius:12px;padding:10px;border-left:4px solid #176fe8}.v165-matrix-kpi small{display:block;color:#687b93;font-size:8px;font-weight:900;text-transform:uppercase}.v165-matrix-kpi b{display:block;font-size:20px;color:#103f7d;margin-top:5px}.v165-matrix-bars{display:grid;gap:5px}.v165-matrix-bar{display:grid;grid-template-columns:72px 1fr 54px;gap:7px;align-items:center;font-size:8px}.v165-matrix-track{height:13px;background:#edf2f7;border-radius:7px;overflow:hidden}.v165-matrix-fill{height:100%;background:#176fe8;border-radius:7px}.v165-matrix-donut{width:130px;height:130px;border-radius:50%;display:grid;place-items:center;margin:auto}.v165-matrix-donut:after{content:'Motivos';width:78px;height:78px;background:#fff;border-radius:50%;display:grid;place-items:center;color:#60758f;font-size:9px;font-weight:900}
/* Operación: 5 tabs exactas y sin duplicados. */
body[data-v163-module="operation"] .v125-tabs{grid-template-columns:repeat(5,minmax(0,1fr))!important}.v165-origin-flow{background:#fff;border:1px solid #d8e4f0;border-radius:12px;padding:11px}.v165-origin-flow-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.v165-origin-flow-grid div{background:#f6f9fd;border-radius:9px;padding:9px}.v165-origin-flow-grid small{display:block;color:#687b93;font-size:8px;text-transform:uppercase;font-weight:900}.v165-origin-flow-grid b{display:block;color:#103f7d;font-size:18px;margin-top:4px}
/* Comercial tabs: iconos homogéneos aprobados. */
#analysisNav .switch{gap:8px!important}.v165-tab-svg{width:18px;height:18px;display:inline-flex;flex:0 0 18px}.v165-tab-svg svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
@media(max-width:900px){.v165-matrix-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v165-miss-grid{grid-template-columns:1fr}.v165-origin-flow-grid{grid-template-columns:repeat(2,1fr)}.v165-inline-field{min-width:0;flex:1 1 45%}}
</style>'''

    js = r'''<script id="v165-requested-fixes-js">
(function(){
if(window.__V165_REQUESTED_FIXES)return;window.__V165_REQUESTED_FIXES=true;
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const n=v=>Number(v||0),fmt=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:0}),pct=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%';
function mod(){let x='';try{x=String(window.MAIN||'').toLowerCase()}catch(_){ }if(x==='operation')return'operation';if(x==='operativo')return'operativo';if(x==='analysis'||x==='commercial')return'analysis';return document.body.dataset.v163Module||''}
function tab(){if(mod()==='operativo')return ($('#operativoNav .active')?.textContent||'').trim();if(mod()==='operation')return ($('.v125-tabs .active')?.textContent||'').trim();if(mod()==='analysis')return ($('#analysisNav .active')?.textContent||'').trim();return''}
function svg(name){const p={grid:'<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',list:'<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',store:'<path d="M3 9h18l-2-5H5L3 9Z"/><path d="M5 9v11h14V9"/><path d="M9 20v-6h6v6"/>',pin:'<path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',more:'<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',upload:'<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 15v5h14v-5"/>',chart:'<line x1="5" y1="20" x2="5" y2="12"/><line x1="12" y1="20" x2="12" y2="5"/><line x1="19" y1="20" x2="19" y2="9"/>',settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2H10V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/>'};return`<span class="v165-tab-svg"><svg viewBox="0 0 24 24">${p[name]||p.grid}</svg></span>`}

/* ---------- Cambios y Muertos: limpiar tabs redundantes ---------- */
function cleanCmTabs(){
  const nav=$('#operativoNav');if(!nav)return;
  ['operations.day','operations.week','operations.month','operations.operation','operations.collection'].forEach(k=>nav.querySelector(`[data-tab-key="${k}"]`)?.remove());
  nav.querySelectorAll('[data-opview="Operación"]').forEach(x=>x.remove());
}

/* ---------- Vista: nunca volver a quedar vacía después de cambiar periodo ---------- */
function syncViewFacade(){
  const real=$('#operPeriodMode'),fac=$('#v161FilterBar select[data-source="operPeriodMode"]');if(!real||!fac)return;
  const base=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
  if(real.options.length<4){real.innerHTML=base.map(x=>`<option value="${x[0]}">${x[1]}</option>`).join('')}
  if(!real.value){const p=$('#operPeriodSelect')?.value||'';real.value=/^\d{4}-W/.test(p)?'week':/^\d{4}-\d{2}-\d{2}$/.test(p)?'day':/^\d{4}-\d{2}$/.test(p)?'month':/^\d{4}$/.test(p)?'year':'week'}
  const wanted=real.value;fac.innerHTML=[...real.options].map(o=>`<option value="${esc(o.value)}">${esc(o.textContent)}</option>`).join('');fac.value=wanted;
  if(!fac.dataset.v165Bound){fac.dataset.v165Bound='1';fac.addEventListener('change',()=>{real.value=fac.value;try{if(window.OPER_PERIOD)window.OPER_PERIOD.type=fac.value}catch(_){ }real.dispatchEvent(new Event('change',{bubbles:true}));setTimeout(schedule,120)})}
  const rp=$('#operPeriodSelect'),fp=$('#v161FilterBar select[data-source="operPeriodSelect"]');if(rp&&fp){const val=rp.value;fp.innerHTML=[...rp.options].map(o=>`<option value="${esc(o.value)}">${esc(o.textContent)}</option>`).join('');fp.value=val}
}

/* ---------- Operación: exactamente 5 pestañas, sin Resumen duplicado ---------- */
const opTabs=[['summary','Resumen','grid'],['daily','Captura diaria','list'],['capture','Cargar productividad','chart'],['productivity','Productividad','chart'],['standards','Estándares','settings']];
function opState(){let k='summary';try{k=String(window.V149_OPERATION_TAB||window.V125_OPERATION_TAB||'summary')}catch(_){ }return opTabs.some(x=>x[0]===k)?k:'summary'}
function repairOperationTabs(){
  if(mod()!=='operation')return;const host=$('.v125-tabs');if(!host)return;const active=opState();
  host.innerHTML=opTabs.map(x=>`<button class="v125-tab ${x[0]===active?'active':''}" data-v165-op="${x[0]}">${svg(x[2])}<span>${x[1]}</span></button>`).join('');
  host.querySelectorAll('[data-v165-op]').forEach(b=>b.onclick=async()=>{const k=b.dataset.v165Op;window.V149_OPERATION_TAB=k;window.V125_OPERATION_TAB=k;try{await window.renderOperativoView('Operación',true)}catch(e){console.warn('[V165 op tab]',e)}setTimeout(schedule,60)});
}

/* ---------- Comercial: iconos correctos ---------- */
function commercialIcons(){
 const map={macro:['Macro compañía','grid'],accordion:['Acordeón comercial','list'],stores:['Tiendas','store'],sections:['Sección / Rubro','grid'],areas:['Ubicación / Área','pin'],more:['Más opciones','more'],'analysis-upload':['Carga de datos','upload']};
 $$('#analysisNav [data-sub]').forEach(b=>{const key=b.dataset.sub,x=map[key];if(!x)return;b.innerHTML=svg(x[1])+`<span>${x[0]}</span>`});
}

/* ---------- Filtro Estatus ---------- */
window.V165_COMMERCIAL_STATUS=window.V165_COMMERCIAL_STATUS||'Todos';
let statusWeek='';
async function statusFilter(){
 if(mod()!=='analysis')return;const grid=$('#v161FilterGrid');if(!grid)return;let wrap=$('#v165StatusField');if(!wrap){wrap=document.createElement('div');wrap.className='v161-field';wrap.id='v165StatusField';wrap.innerHTML='<label>Estatus</label><select id="v165Status"><option value="Todos">Todos</option></select>';const go=grid.querySelector('.v161-apply');grid.insertBefore(wrap,go||null);wrap.querySelector('select').addEventListener('change',e=>window.V165_COMMERCIAL_STATUS=e.target.value||'Todos')}
 const week=$('#week')?.value||'';if(week===statusWeek&&wrap.querySelector('select').options.length>1){wrap.querySelector('select').value=window.V165_COMMERCIAL_STATUS;return}statusWeek=week;
 try{const r=await api('/api/commercial/status-options-v165?week='+encodeURIComponent(week),{timeoutMs:60000});const sel=wrap.querySelector('select'),old=window.V165_COMMERCIAL_STATUS;sel.innerHTML='<option value="Todos">Todos</option>'+((r.values||[]).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join(''));sel.value=[...sel.options].some(o=>o.value===old)?old:'Todos';window.V165_COMMERCIAL_STATUS=sel.value}catch(e){console.warn('[V165 status]',e)}
}
const originalFetch=window.fetch.bind(window);window.fetch=function(input,init){try{let raw=typeof input==='string'?input:input?.url||'';if(mod()==='analysis'&&raw&&raw.includes('/api/')&&!raw.includes('status-options-v165')&&!raw.includes('commercial-sales')&&!raw.includes('/upload/')){const u=new URL(raw,location.origin);const p=u.pathname;if(p.includes('commercial')||p.includes('dashboard')||p.includes('model-')||p.includes('capacity-')){u.searchParams.set('status',window.V165_COMMERCIAL_STATUS||'Todos');raw=u.pathname+u.search+u.hash;if(typeof input==='string')input=raw;else input=new Request(raw,input)}}}catch(_){ }return originalFetch(input,init)};

/* ---------- Filtros internos estilo filtro superior ---------- */
function selectFacade(id,label,options,onchange){let el=$('#'+id);if(el)return el;const host=document.createElement('div');host.className='v165-inline-filters';host.id=id+'Wrap';host.innerHTML=`<div class="v165-inline-field"><label>${esc(label)}</label><select id="${id}">${options.map(x=>`<option value="${esc(x[0])}">${esc(x[1])}</option>`).join('')}</select></div>`;const sel=host.querySelector('select');sel.addEventListener('change',()=>onchange(sel.value));return{host,sel}}
function internalFilters(){if(mod()!=='analysis')return;
 // Modelos 80/20
 const champ=$('#champSection');const cs=$('#champSectionSwitch');if(champ&&cs){cs.classList.add('v165-original-switches');champ.classList.remove('hidden');champ.classList.add('v165-top-select');const panel=champ.closest('.compact-filter');if(panel)panel.classList.add('v165-filter-panel')}
 // Lentos
 const slow=$('#slowSection');if(slow){slow.classList.add('v165-top-select');slow.closest('.compact-filter')?.classList.add('v165-filter-panel')}
 // Sugerido 0 a 1: fachada ligada al mismo alcance de sección de lentos.
 const zeroTitle=$('#zeroTitle');if(zeroTitle&&slow&&!$('#v165ZeroSectionWrap')){const f=selectFacade('v165ZeroSection','Sección · Sugerido 0 a 1',[['Todas','Todas'],['Dama','Dama'],['Caballero','Caballero'],['Infantil','Infantil']],v=>{slow.value=v;slow.dispatchEvent(new Event('change',{bubbles:true}))});zeroTitle.insertAdjacentElement('afterend',f.host);f.sel.value=slow.value||'Todas'}
 // Macro 80/20: convertir botones de agrupación en select superior.
 const pg=$('[data-pareto-group]');if(pg&&!$('#v165ParetoGroupWrap')){const group=pg.parentElement;group.classList.add('v165-original-switches');const opts=$$('[data-pareto-group]').map(b=>[b.dataset.paretoGroup,(b.textContent||b.dataset.paretoGroup).trim()]);const f=selectFacade('v165ParetoGroup','Desglose 80/20',opts,v=>$(`[data-pareto-group="${v}"]`)?.click());group.insertAdjacentElement('beforebegin',f.host);f.sel.value=$('[data-pareto-group].active')?.dataset.paretoGroup||opts[0]?.[0]||''}
 // Ubicación: sección y área como selects del mismo formato.
 const as=$('[data-area-section]');if(as&&!$('#v165AreaSectionWrap')){const g=as.parentElement;g.classList.add('v165-original-switches');const opts=$$('[data-area-section]').map(b=>[b.dataset.areaSection,(b.textContent||b.dataset.areaSection).trim()]);const f=selectFacade('v165AreaSection','Sección',opts,v=>$(`[data-area-section="${v}"]`)?.click());g.insertAdjacentElement('beforebegin',f.host);f.sel.value=$('[data-area-section].active')?.dataset.areaSection||opts[0]?.[0]||''}
 const ag=$('[data-area-group]');if(ag&&!$('#v165AreaGroupWrap')){const g=ag.parentElement;g.classList.add('v165-original-switches');const opts=$$('[data-area-group]').map(b=>[b.dataset.areaGroup,(b.textContent||b.dataset.areaGroup).trim()]);const f=selectFacade('v165AreaGroup','Área',opts,v=>$(`[data-area-group="${v}"]`)?.click());g.insertAdjacentElement('beforebegin',f.host);f.sel.value=$('[data-area-group].active')?.dataset.areaGroup||opts[0]?.[0]||''}
 // Título: ya no limitar visualmente a primeros 150.
 const ct=$('#champTitle');if(ct)ct.textContent=ct.textContent.replace(/\s*·\s*primeros\s*150/i,'');
}

/* ---------- Productividad: alerta colaboradores históricos sin captura actual ---------- */
async function missingProductivity(){
 if(mod()!=='operativo'||!tab().toLowerCase().includes('productividad')){$('#v165MissingProd')?.remove();return}
 const q=new URLSearchParams({period_type:$('#operPeriodMode')?.value||'week',period_value:$('#operPeriodSelect')?.value||'',store:$('#operStoreSelect')?.value||'Compañía'});let r;try{r=await api('/api/operations/missing-productivity-v165?'+q,{timeoutMs:60000})}catch(e){return}
 let box=$('#v165MissingProd');if(!box){box=document.createElement('div');box.id='v165MissingProd';const title=[...document.querySelectorAll('.title,h2')].find(x=>(x.textContent||'').toLowerCase().includes('ranking completo'));if(title)title.insertAdjacentElement('beforebegin',box);else $('#operativoNav')?.insertAdjacentElement('afterend',box)}
 if(!box)return;box.innerHTML=`<h3>Alerta · colaboradores sin productividad en el periodo</h3><span class="v165-miss-count">${fmt(r.count)} sin registro</span>${r.count?`<div class="v165-miss-grid">${(r.rows||[]).map(x=>`<div class="v165-miss-item"><b>${esc(x.name)}</b><span>${esc(x.store)} · último registro ${esc(x.last_date)}${x.last_activity?' · '+esc(x.last_activity):''}</span></div>`).join('')}</div>`:'<div style="margin-top:8px;font-size:9px;color:#15803d">Todos los colaboradores históricos tienen productividad en el periodo.</div>'}`;
}

/* ---------- Matriz integrada al inicio de Recorridos ---------- */
function matrixTable(rows){return `<div class="tablewrap" style="max-height:540px"><table class="table"><thead><tr><th>Día</th><th>Hora</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Total</th><th>Responsables</th></tr></thead><tbody>${rows.map(x=>`<tr><td><b>${esc(x.day)}</b></td><td>${esc(x.schedule)}</td><td>${fmt(x.muertos)}</td><td>${fmt(x.cajas)}</td><td>${fmt(x.probador)}</td><td><b>${fmt(x.total)}</b></td><td>${esc(x.responsible||'—')}</td></tr>`).join('')}</tbody></table></div>`}
async function matrixInRoutes(){
 if(mod()!=='operativo'||!tab().toLowerCase().includes('recorridos')){$('#v165MatrixRoutes')?.remove();return}
 const q=new URLSearchParams({period_type:$('#operPeriodMode')?.value||'week',period_value:$('#operPeriodSelect')?.value||'',store:$('#operStoreSelect')?.value||'Compañía',area:$('#operAreaSelect')?.value||'Todas',activity:$('#operActivitySelect')?.value||'Todas'});let r;try{r=await api('/api/operations/collection-hour-matrix-v165?'+q,{timeoutMs:120000})}catch(e){console.warn('[V165 matrix]',e);return}
 let root=$('#v165MatrixRoutes');if(!root){root=document.createElement('section');root.id='v165MatrixRoutes';$('#operativoNav')?.insertAdjacentElement('afterend',root)}if(!root)return;
 const max=Math.max(1,...(r.days||[]).map(x=>n(x.total))),t=r.source_totals||{},sum=Math.max(1,n(t.muertos)+n(t.cajas)+n(t.probador)),pm=n(t.muertos)/sum*100,pc=n(t.cajas)/sum*100;
 root.innerHTML=`<div class="title">Matriz de recolección de mercancía</div><div class="subtitle">Agrupada de lunes a domingo por hora completa, desde el primer hasta el último horario registrado.</div><div class="v165-matrix-kpis"><div class="v165-matrix-kpi"><small>Piezas recolectadas</small><b>${fmt(r.summary?.pieces)}</b></div><div class="v165-matrix-kpi"><small>Franjas con movimiento</small><b>${fmt(r.summary?.slots)}</b></div><div class="v165-matrix-kpi"><small>Tiendas</small><b>${fmt(r.summary?.stores)}</b></div><div class="v165-matrix-kpi"><small>Horario</small><b>${r.summary?.first_hour==null?'—':String(r.summary.first_hour).padStart(2,'0')+':00–'+String(r.summary.last_hour).padStart(2,'0')+':00'}</b></div></div><div class="v165-matrix-card"><h3>Matriz día × hora</h3>${matrixTable(r.matrix||[])}</div><div class="grid"><div class="v165-matrix-card"><h3>Tendencia por día</h3><div class="v165-matrix-bars">${(r.days||[]).map(x=>`<div class="v165-matrix-bar"><b>${esc(x.day)}</b><div class="v165-matrix-track"><div class="v165-matrix-fill" style="width:${Math.min(100,n(x.total)/max*100)}%"></div></div><span>${fmt(x.total)}</span></div>`).join('')}</div></div><div class="v165-matrix-card"><h3>Participación por motivo</h3><div class="v165-matrix-donut" style="background:conic-gradient(#e4007f 0 ${pm}%,#7047c8 ${pm}% ${pm+pc}%,#f59e0b ${pm+pc}% 100%)"></div><div style="font-size:9px;margin-top:8px">Muertos ${pct(n(t.muertos)/sum*100)} · Cajas ${pct(n(t.cajas)/sum*100)} · Probador ${pct(n(t.probador)/sum*100)}</div></div></div><div class="v165-matrix-card"><h3>Resumen por tienda</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Total</th></tr></thead><tbody>${(r.stores||[]).map(x=>`<tr><td><b>${esc(x.store)}</b></td><td>${fmt(x.muertos)}</td><td>${fmt(x.cajas)}</td><td>${fmt(x.probador)}</td><td><b>${fmt(x.total)}</b></td></tr>`).join('')}</tbody></table></div></div>`;
}

/* ---------- Operación: Origen únicamente ---------- */
async function originOnly(){
 if(mod()!=='operation'||opState()!=='summary')return;const q=new URLSearchParams({period_type:$('#operPeriodMode')?.value||'day',period_value:$('#operPeriodSelect')?.value||'',store:$('#operStoreSelect')?.value||'Compañía'});let r;try{r=await api('/api/operation/origin-summary-v165?'+q,{timeoutMs:60000})}catch(e){console.warn('[V165 origin]',e);return}const s=r.summary||{};
 const vals={'llegada origen':fmt(s.arrival_origin),'productividad registrada':fmt(s.processed),'mercancía liberada':fmt(s.released),'pendiente':fmt(s.pending),'eficiencia':pct(s.efficiency_pct),'prod. promedio':fmt(s.productivity_avg),'cumplimiento':pct(s.compliance_pct),'colaboradores':fmt(s.collaborators),'colaboradores necesarios':fmt(s.required),'colab. necesarios origen':fmt(s.required)};
 $$('.v149-kpi,.v125-kpi,.report-kpi,.kpi').forEach(card=>{const lab=(card.querySelector('small,.lab,.rk-label')?.textContent||'').trim().toLowerCase();if(vals[lab]!=null){const v=card.querySelector('b,.val,.rk-value');if(v)v.textContent=vals[lab];if(lab==='mercancía liberada'){const sub=card.querySelector('span,.note,.rk-sub');if(sub)sub.textContent='Origen'}}});
 // Reemplazar cualquier panel comparativo con C&M por flujo exclusivo de Origen.
 const h=$$('h3').find(x=>(x.textContent||'').toLowerCase().includes('origen vs cambios'));if(h){const p=h.closest('.v149-panel,.v126-panel,.panel')||h.parentElement;p.innerHTML=`<h3>Origen · Mercancía liberada</h3><div class="v165-origin-flow"><div class="v165-origin-flow-grid"><div><small>Llegada</small><b>${fmt(s.arrival_origin)}</b></div><div><small>Procesadas</small><b>${fmt(s.processed)}</b></div><div><small>Mercancía liberada</small><b>${fmt(s.released)}</b></div><div><small>Pendiente</small><b>${fmt(s.pending)}</b></div></div></div>`}
 // No dejar textos residuales de C&M dentro del Resumen de Operación.
 const walker=document.createTreeWalker($('#operativoDynamicContent')||document.body,NodeFilter.SHOW_TEXT);let node;while(node=walker.nextNode()){if(node.nodeValue?.includes('Origen + C&M'))node.nodeValue=node.nodeValue.replace(/Origen \+ C&M/g,'Origen')}
}

function schedule(){cleanCmTabs();syncViewFacade();repairOperationTabs();commercialIcons();internalFilters();setTimeout(statusFilter,20);setTimeout(missingProductivity,40);setTimeout(matrixInRoutes,50);setTimeout(originOnly,60)}
let timer=null;function later(){clearTimeout(timer);timer=setTimeout(schedule,80)}
document.addEventListener('click',e=>{if(e.target.closest?.('[data-main],#operativoNav,#analysisNav,.v125-tabs,#v161FilterBar,.v161-apply'))later()},true);document.addEventListener('change',e=>{if(e.target.matches?.('select,input'))later()},true);
const mo=new MutationObserver(()=>later());if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{mo.observe(document.body,{childList:true,subtree:true});schedule()});else{mo.observe(document.body,{childList:true,subtree:true});schedule()}
console.info('[V165] Cambios solicitados: filtros, alertas, matriz horaria, Origen, Estatus, Marca, ventas e internos Comercial.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v165_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8", errors="replace")
            if "v165-requested-fixes-css" not in html:
                html=html.replace("</head>", css+"</head>", 1)
            if "v165-requested-fixes-js" not in html:
                html=html.replace("</body>", js+"</body>", 1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None)
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V165"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V165] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V165_REQUESTED_FIXES=True
    print("[V165] Ajustes solicitados instalados: Vista estable, Recorridos+Matriz, Origen, Estatus, Marca, ventas y filtros internos.", flush=True)
