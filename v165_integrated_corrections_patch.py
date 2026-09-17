"""V165 · Correcciones funcionales solicitadas 2026-09-17.

- Cambios y Muertos: elimina pestañas redundantes Operación/Día/Semanal/Mensual,
  conserva Vista como selector de periodo y garantiza que nunca quede vacío.
- Productividad: alerta colaboradores con productividad histórica pero sin registro
  en el periodo consultado.
- Recorridos: integra al inicio la Matriz de recolección, agrupada por lunes-domingo
  y hora completa desde la primera hasta la última hora registrada.
- Operación: se enfoca sólo en Origen; mercancía liberada y personal requerido ya
  no mezclan Cambios y Muertos. Corrige duplicado de Resumen/navegación de tabs.
- Comercial: agrega filtro Estatus basado en ESTATUS del Excel, usa MARCA (no
  MARCA PRICE), corrige iconos, ventas 422 y da estilo de filtro superior a los
  filtros internos de ubicación/80-20/lentos/sugerido 0-1.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo
import inspect
import math
import re
import threading
import unicodedata

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V165_CORRECTIONS", False):
        return

    def norm(v):
        t = unicodedata.normalize("NFKD", str(v or ""))
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", t).strip().upper()

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def bounds(kind, value):
        kind = str(kind or "week").lower().strip()
        value = str(value or "").strip()
        today = datetime.now(MX).date()
        if kind == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date()
            return d, d
        if kind == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt:
                y, w = int(mt.group(1)), int(mt.group(2))
            else:
                iso = today.isocalendar()
                y, w = iso.year, iso.week
            start = date.fromisocalendar(y, w, 1)
            return start, start + timedelta(days=6)
        if kind == "month":
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            if mt:
                y, mo = int(mt.group(1)), int(mt.group(2))
            else:
                y, mo = today.year, today.month
            start = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return start, nxt - timedelta(days=1)
        if kind == "year":
            y = int(value or today.year)
            return date(y, 1, 1), date(y, 12, 31)
        raise HTTPException(400, "Vista inválida")

    def scoped_store(actor, requested):
        if str(actor.get("role") or "") in ("tienda", "colaborador"):
            return str(actor.get("store") or "").strip()
        return str(requested or "Compañía").strip() or "Compañía"

    try:
        m.REPORT_TABS.pop("operations.collection", None)
    except Exception:
        pass

    # Marca real del Excel: MARCA tiene prioridad sobre MARCA PRICE.
    try:
        import commercial.parsers as cp
        if not getattr(cp, "_V165_BRAND_PRIORITY", False):
            original_read_capacity = cp.read_capacity_file
            original_series = cp._series
            brand_lock = threading.RLock()

            def read_capacity_v165(path):
                with brand_lock:
                    prev = cp._series
                    def series_v165(df, candidates, default="", contains=False):
                        normalized = [cp.norm_text(x) for x in (candidates or [])]
                        if normalized == ["MARCA PRICE", "MARCA"]:
                            candidates = ["MARCA", "MARCA PRICE"]
                        return original_series(df, candidates, default, contains=contains)
                    cp._series = series_v165
                    try:
                        return original_read_capacity(path)
                    finally:
                        cp._series = prev

            cp.read_capacity_file = read_capacity_v165
            cp._V165_BRAND_PRIORITY = True
            if hasattr(m, "read_capacity_file"):
                m.read_capacity_file = read_capacity_v165
            cache = getattr(m, "_CAPACITY_FRAME_CACHE", None)
            if isinstance(cache, dict):
                cache.update({"path": "", "mtime": None, "frame": None})
            print("[V165] Capacidad: MARCA priorizada sobre MARCA PRICE.", flush=True)
    except Exception as exc:
        print(f"[V165] Marca warning: {type(exc).__name__}: {exc}", flush=True)

    # Fuerza una reconstrucción única del cache de capacidades para que el
    # cambio MARCA (columna N) se refleje aun si Render tenía un pickle previo.
    try:
        manifest = m.load_manifest() or {}
        for entry in list(manifest.get("capacities") or []):
            cache_rel = str(entry.get("cache_file") or "").strip()
            if cache_rel:
                try:
                    cache_path = m.DATA_ROOT / cache_rel
                    cache_path.unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    m.update_entry("capacities", str(entry.get("id") or ""), cache_file="")
                except Exception:
                    pass
        cache = getattr(m, "_CAPACITY_FRAME_CACHE", None)
        if isinstance(cache, dict):
            cache.update({"path":"","mtime":None,"frame":None})
    except Exception as exc:
        print(f"[V165] Cache capacidad warning: {type(exc).__name__}: {exc}", flush=True)

    # El reporte Modelos 80/20 debe traer TODOS los modelos que alcanzan el 80%,
    # no recortar a 150. Para ese modo se recalcula el detalle vectorizado; los
    # demás modos conservan exactamente la implementación existente.
    original_capacity_model_rows = getattr(m, "_capacity_model_rows", None)
    if callable(original_capacity_model_rows):
        def capacity_model_rows_v165(store="Compañía", section="Todas", mode="80_20", period="", catalog="Todos"):
            mode_key = str(mode or "80_20").lower()
            if mode_key not in ("80_20","8020","top","champions"):
                return original_capacity_model_rows(store, section, mode, period, catalog)
            try:
                import pandas as pd
                import numpy as np
                frame = m._capacity_frame_for_period(period)
                work = m._capacity_scope_v45(frame, store, section, catalog)
                if work is None or work.empty or "ID_ART" not in work.columns:
                    return []
                work = work.copy()
                work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
                work = work[~work["__id"].isin(["","nan","None"])]
                if work.empty:
                    return []
                pcol, vcol = m._capacity_period_columns(period)
                def nums(col):
                    return pd.to_numeric(work.get(col, 0), errors="coerce").fillna(0.0)
                tmp = pd.DataFrame({"__id": work["__id"]})
                mapping = {
                    "existence":"Existencia", "floor":"Existencia piso",
                    "warehouse":"Existencia bodega", "suggested":"VPD",
                    "capacity":"Capacidad", "sales_pzas":pcol, "sales_value":vcol,
                    "sales_pzas_30":"Venta pzas 30", "pzas_ult_cedis":"Pzas última entrada",
                }
                for dst, src in mapping.items(): tmp[dst] = nums(src)
                agg = tmp.groupby("__id", sort=False).sum(numeric_only=True)
                if "DDI" in work.columns:
                    ddi = pd.to_numeric(work["DDI"], errors="coerce").replace([np.inf,-np.inf], np.nan)
                    agg = agg.join(ddi.groupby(work["__id"]).mean().rename("ddi"), how="left")
                else: agg["ddi"] = 0.0
                meta_cols={"model":"Modelo","brand":"Marca","section":"Sección","rubro":"Subcategoría","catalog":"Tipo catálogo"}
                for dst,src in meta_cols.items():
                    if src in work.columns:
                        ser=work[src].fillna("").astype(str).str.strip().replace({"nan":"","None":""})
                        first=pd.DataFrame({"__id":work["__id"],dst:ser.replace("",pd.NA)}).groupby("__id",sort=False)[dst].first()
                        agg=agg.join(first,how="left")
                    else: agg[dst]=""
                if "Última entrada CEDIS a tienda" in work.columns:
                    dates=pd.to_datetime(work["Última entrada CEDIS a tienda"],errors="coerce")
                    agg=agg.join(dates.groupby(work["__id"]).max().rename("ultima_cedis"),how="left")
                else: agg["ultima_cedis"]=pd.NaT
                models=agg.reset_index().rename(columns={"__id":"id_art"})
                models=models.sort_values(["sales_value","sales_pzas","existence"],ascending=[False,False,False]).reset_index(drop=True)
                total=float(models["sales_value"].sum())
                models["cum_share"]=(models["sales_value"].cumsum()/total*100) if total>0 else 0.0
                if total>0:
                    hit=np.flatnonzero(models["cum_share"].to_numpy()>=80.0)
                    last=int(hit[0]) if len(hit) else len(models)-1
                    models=models.iloc[:last+1].copy()
                else:
                    models=models.head(50).copy()
                models=models.reset_index(drop=True);models["rank"]=np.arange(1,len(models)+1)
                models["occupancy"]=np.where(models["capacity"]>0,models["existence"]/models["capacity"]*100,np.nan)
                ids=set(models["id_art"].astype(str));labels=work[work["__id"].isin(ids)].copy()
                def labels_map(col, limit=3):
                    if col not in labels.columns:return {}
                    x=labels[["__id",col]].copy();x[col]=x[col].fillna("").astype(str).str.strip();x=x[~x[col].isin(["","nan","None","—"])].drop_duplicates()
                    if x.empty:return {}
                    return x.groupby("__id",sort=False)[col].agg(lambda q:" / ".join(list(dict.fromkeys(q.tolist()))[:limit])).to_dict()
                loc_col="Ubicación detalle" if "Ubicación detalle" in labels.columns else ("Pasillo" if "Pasillo" in labels.columns else "")
                loc=labels_map(loc_col,3) if loc_col else {}; exhib=labels_map("Exhibición",5); stores=labels_map("Tienda",3)
                out=[]
                for r in models.to_dict("records"):
                    rid=str(r.get("id_art") or "")
                    out.append({
                        "id_art":rid,"model":str(r.get("model") or rid),"brand":str(r.get("brand") or "Sin marca"),
                        "section":str(r.get("section") or "Sin sección"),"rubro":str(r.get("rubro") or "Sin rubro"),
                        "location":loc.get(rid,""),"exhibition":exhib.get(rid,""),"store":stores.get(rid,store),
                        "rank":int(r.get("rank") or 0),"suggested":num(r.get("suggested")),"existence":num(r.get("existence")),
                        "capacity":num(r.get("capacity")),"occupancy":None if pd.isna(r.get("occupancy")) else num(r.get("occupancy")),
                        "sales_pzas_30":num(r.get("sales_pzas_30")),"sales_pzas":num(r.get("sales_pzas")),
                        "sales_value":num(r.get("sales_value")),"floor":num(r.get("floor")),"warehouse":num(r.get("warehouse")),
                        "ddi":num(r.get("ddi")),"ultima_cedis":"" if pd.isna(r.get("ultima_cedis")) else pd.Timestamp(r.get("ultima_cedis")).strftime("%Y-%m-%d"),
                        "pzas_ult_cedis":num(r.get("pzas_ult_cedis")),"cum_share":num(r.get("cum_share")),"recurrence_weeks":0,
                    })
                return out
            except Exception as exc:
                print(f"[V165] Modelos 80 completo warning: {type(exc).__name__}: {exc}", flush=True)
                return original_capacity_model_rows(store, section, mode, period, catalog)
        m._capacity_model_rows = capacity_model_rows_v165

    original_capacity_frame = getattr(m, "_capacity_frame_for_period", None)
    status_lock = threading.RLock()

    def status_frame(period, status):
        frame = original_capacity_frame(period) if callable(original_capacity_frame) else None
        if frame is None or getattr(frame, "empty", True):
            return frame
        status = str(status or "Todos").strip()
        if status in ("", "Todos", "Todas"):
            return frame
        col = "Estatus comercial"
        if col not in frame.columns:
            return frame.iloc[0:0].copy()
        target = norm(status)
        mask = frame[col].fillna("").astype(str).map(norm).eq(target)
        return frame.loc[mask].copy()

    def find_route(path, method="GET"):
        for r in list(m.app.router.routes):
            if getattr(r, "path", None) == path and method in (getattr(r, "methods", set()) or set()):
                return r
        return None

    def install_status_wrapper(path, signature_kind):
        if not callable(original_capacity_frame):
            return
        route = find_route(path, "GET")
        if not route:
            return
        old = route.endpoint
        m.app.router.routes.remove(route)

        async def call_old(kwargs, status):
            if not status or status in ("Todos", "Todas"):
                result = old(**kwargs)
                return await result if inspect.isawaitable(result) else result
            with status_lock:
                previous = m._capacity_frame_for_period
                m._capacity_frame_for_period = lambda period="": status_frame(period, status)
                try:
                    result = old(**kwargs)
                    return await result if inspect.isawaitable(result) else result
                finally:
                    m._capacity_frame_for_period = previous

        if signature_kind == "dashboard":
            async def endpoint(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos", status: str="Todos"):
                return await call_old(dict(request=request, week=week, store=store, section=section, catalog=catalog), status)
        elif signature_kind == "detail":
            async def endpoint(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos", status: str="Todos"):
                return await call_old(dict(request=request, week=week, store=store, section=section, catalog=catalog), status)
        elif signature_kind == "accordion":
            async def endpoint(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos", status: str="Todos"):
                return await call_old(dict(request=request, week=week, store=store, section=section, catalog=catalog), status)
        elif signature_kind == "ranking":
            async def endpoint(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", slow: bool=False, mode: str|None=None, catalog: str="Todos", status: str="Todos"):
                return await call_old(dict(request=request, week=week, store=store, section=section, slow=slow, mode=mode, catalog=catalog), status)
        else:
            async def endpoint(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos", group_by: str="section", status: str="Todos"):
                return await call_old(dict(request=request, week=week, store=store, section=section, catalog=catalog, group_by=group_by), status)
        m.app.add_api_route(path, endpoint, methods=["GET"])

    for path, kind in (
        ("/api/dashboard", "dashboard"),
        ("/api/commercial-detail", "detail"),
        ("/api/commercial-accordion", "accordion"),
        ("/api/model-ranking", "ranking"),
        ("/api/model-8020-summary", "pareto"),
    ):
        try:
            install_status_wrapper(path, kind)
        except Exception as exc:
            print(f"[V165] status wrapper {path}: {type(exc).__name__}: {exc}", flush=True)

    @m.app.get("/api/commercial/status-values-v165")
    def commercial_status_values_v165(request: Request, week: str|None=None):
        m.require_user(request)
        if not callable(original_capacity_frame):
            return {"values": []}
        frame = original_capacity_frame(week or "")
        if frame is None or getattr(frame, "empty", True) or "Estatus comercial" not in frame.columns:
            return {"values": []}
        values = sorted({
            str(x).strip() for x in frame["Estatus comercial"].dropna().tolist()
            if str(x).strip() and str(x).strip().lower() not in ("nan", "none")
        })
        return {"values": values}

    try:
        sales_route = find_route("/api/commercial-sales-summary", "GET")
        if sales_route:
            m.app.router.routes.remove(sales_route)
    except Exception:
        pass

    def sales_scope_entries(year, scope):
        entries = []
        try:
            entries = list((m.load_manifest() or {}).get("sales") or [])
        except Exception:
            return {}
        grouped = {}
        for item0 in entries:
            item = dict(item0 or {})
            if int(item.get("year") or 0) != int(year):
                continue
            mo = int(item.get("month") or 0)
            if mo not in range(1, 13):
                continue
            st = str(item.get("store") or "Compañía").strip() or "Compañía"
            key = (mo, norm(st))
            prev = grouped.get(key)
            if prev is None or str(item.get("uploaded_at") or "") >= str(prev.get("uploaded_at") or ""):
                grouped[key] = item
        out = {}
        for mo in range(1, 13):
            if scope != "Compañía":
                candidates = [v for (mth, st), v in grouped.items() if mth == mo and st == norm(scope)]
            else:
                company = [v for (mth, st), v in grouped.items() if mth == mo and st in ("COMPAÑIA", "COMPANY")]
                candidates = company if company else [v for (mth, st), v in grouped.items() if mth == mo]
            out[mo] = {
                "sales": sum(max(num(x.get("total_sales")), 0) for x in candidates),
                "pieces": sum(max(num(x.get("total_pieces")), 0) for x in candidates),
                "sources": sum(1 for x in candidates if num(x.get("total_sales")) > 0),
                "last_upload": max([str(x.get("uploaded_at") or "") for x in candidates] or [""]),
            }
        return out

    @m.app.get("/api/commercial-sales-summary")
    def commercial_sales_summary_v165(request: Request, year: int|None=None, through_month: int|None=None, store: str="Compañía"):
        actor = m.require_user(request)
        now = datetime.now(MX)
        y = int(year or now.year)
        cut = max(1, min(12, int(through_month or now.month)))
        scope = scoped_store(actor, store)
        current = sales_scope_entries(y, scope)
        previous = sales_scope_entries(y - 1, scope)
        goals = {}
        try:
            with m.db() as con:
                for r in con.execute("SELECT month,target FROM sales_goals WHERE year=? AND store=?", (y, scope)).fetchall():
                    goals[int(r["month"])] = num(r["target"])
        except Exception:
            pass
        labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        months = []
        source_count = 0
        last_upload = ""
        for mo in range(1, 13):
            cur = num(current.get(mo, {}).get("sales")); prev = num(previous.get(mo, {}).get("sales")); goal = num(goals.get(mo)); src = int(current.get(mo, {}).get("sources") or 0)
            source_count += src if mo <= cut else 0
            if mo <= cut:
                last_upload = max(last_upload, str(current.get(mo, {}).get("last_upload") or ""))
            months.append({"month":mo,"label":labels[mo-1],"target":goal,"current":cur,"previous":prev,"pieces":num(current.get(mo,{}).get("pieces")),"previous_pieces":num(previous.get(mo,{}).get("pieces")),"sources":src,"compliance":cur/goal*100 if goal else None,"growth":(cur/prev-1)*100 if prev else None})
        goal_ytd=sum(x["target"] for x in months[:cut]); current_ytd=sum(x["current"] for x in months[:cut]); previous_ytd=sum(x["previous"] for x in months[:cut])
        available={y,y-1}
        try:
            for e in (m.load_manifest() or {}).get("sales",[]):
                if int(e.get("year") or 0)>0: available.add(int(e.get("year")))
        except Exception: pass
        return {"year":y,"previous_year":y-1,"through_month":cut,"store":scope,"available_years":sorted(available,reverse=True),"editable":str(actor.get("role") or "") in ("superadmin","admin"),"months":months,"totals":{"goal_ytd":goal_ytd,"current_ytd":current_ytd,"previous_ytd":previous_ytd,"compliance_pct":current_ytd/goal_ytd*100 if goal_ytd else None,"growth_pct":(current_ytd/previous_ytd-1)*100 if previous_ytd else None,"gap_to_goal":current_ytd-goal_ytd if goal_ytd else None},"has_sales":any(x["current"]>0 or x["previous"]>0 for x in months[:cut]),"source_count":source_count,"last_upload":last_upload,"source_label":"Fuente: PDF de ventas mensuales procesados","parser_version":165}

    @m.app.get("/api/operations/inactive-collaborators-v165")
    def inactive_collaborators_v165(request: Request, period_type: str="week", period_value: str="", store: str="Compañía"):
        actor=m.require_user(request); start,end=bounds(period_type,period_value); selected=scoped_store(actor,store); historical={};active=set()
        for r in list((m.load_ops() or {}).get("rows") or []):
            ds=str(r.get("date") or "")[:10];name=str(r.get("name") or "").strip();st=str(r.get("store") or "").strip();pieces=num(r.get("pieces"));activity=str(r.get("activity") or r.get("activity_original") or "")
            if not ds or not name or pieces<=0 or not activity:continue
            try:d=date.fromisoformat(ds)
            except Exception:continue
            if selected!="Compañía" and st!=selected:continue
            key=(norm(name),st)
            if d<start:
                prev=historical.get(key)
                if prev is None or ds>prev["last_date"]:historical[key]={"name":name,"store":st,"last_date":ds}
            elif start<=d<=end:active.add(key)
        missing=[v for k,v in historical.items() if k not in active];missing.sort(key=lambda x:(x["store"],x["name"]))
        return {"start_date":start.isoformat(),"end_date":end.isoformat(),"store":selected,"rows":missing,"count":len(missing)}

    def hour_from_value(raw):
        s=str(raw or "").strip();mt=re.search(r"(?:^|\s)([01]?\d|2[0-3]):[0-5]\d",s)
        if mt:return int(mt.group(1))
        try:
            x=float(s)
            if 0<=x<1:return int((x*24)%24)
        except Exception:pass
        return None

    @m.app.get("/api/operations/collection-hourly-v165")
    def collection_hourly_v165(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor=m.require_user(request);start,end=bounds(period_type,period_value);selected=scoped_store(actor,store);buckets=defaultdict(lambda:{"muertos":0.0,"cajas":0.0,"probador":0.0,"records":0});min_hour=max_hour=None
        for r in list((m.load_ops() or {}).get("rows") or []):
            ds=str(r.get("date") or "")[:10]
            if not ds:continue
            try:d=date.fromisoformat(ds)
            except Exception:continue
            if d<start or d>end:continue
            st=str(r.get("store") or "").strip()
            if selected!="Compañía" and st!=selected:continue
            if str(area or "") not in ("","Todos","Todas") and norm(r.get("area"))!=norm(area):continue
            if str(activity or "") not in ("","Todos","Todas") and norm(r.get("activity") or r.get("activity_original") or "")!=norm(activity):continue
            mu,ca,pr=num(r.get("muertos")),num(r.get("cajas")),num(r.get("probador"))
            if mu<=0 and ca<=0 and pr<=0:continue
            hour=hour_from_value(r.get("start_time"))
            if hour is None:continue
            b=buckets[(d.weekday(),hour)];b["muertos"]+=mu;b["cajas"]+=ca;b["probador"]+=pr;b["records"]+=1
            min_hour=hour if min_hour is None else min(min_hour,hour);max_hour=hour if max_hour is None else max(max_hour,hour)
        if min_hour is None:min_hour,max_hour=9,20
        days=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"];rows=[];totals={"muertos":0.0,"cajas":0.0,"probador":0.0}
        for hour in range(min_hour,max_hour+1):
            cells=[];row_total=0.0
            for wd in range(7):
                b=dict(buckets.get((wd,hour),{"muertos":0.0,"cajas":0.0,"probador":0.0,"records":0}));b["total"]=b["muertos"]+b["cajas"]+b["probador"];row_total+=b["total"];cells.append(b)
                totals["muertos"]+=b["muertos"];totals["cajas"]+=b["cajas"];totals["probador"]+=b["probador"]
            rows.append({"hour":hour,"label":f"{hour:02d}:00","cells":cells,"total":row_total})
        return {"start_date":start.isoformat(),"end_date":end.isoformat(),"store":selected,"days":days,"min_hour":min_hour,"max_hour":max_hour,"rows":rows,"totals":{**totals,"total":sum(totals.values())}}

    @m.app.get("/api/operation/origin-only-v165")
    def origin_only_v165(request: Request, period_type: str="day", period_value: str="", store: str="Compañía"):
        actor=m.require_user(request);start,end=bounds(period_type,period_value);selected=scoped_store(actor,store);stores=[selected] if selected!="Compañía" else list(m.store_names(True))
        if not stores:return {"summary":{},"rows":[],"alerts":[]}
        ph=",".join("?" for _ in stores);ss,es=start.isoformat(),end.isoformat()
        with m.db() as con:
            caps=[dict(r) for r in con.execute(f"SELECT date,store,arrival,released,pending_manual FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ({ph}) ORDER BY date",(es,*stores)).fetchall()]
            prod=[dict(r) for r in con.execute(f"SELECT date,store,employee_no,employee_name,origin,pieces FROM operation_productivity WHERE origin IN ('Colgado','Doblado') AND date<=? AND store IN ({ph}) ORDER BY date,id",(es,*stores)).fetchall()]
            std={"Colgado":1228.0,"Doblado":906.0}
            try:
                for r in con.execute("SELECT origin,pieces_per_shift FROM operation_standards WHERE origin IN ('Colgado','Doblado')").fetchall():std[str(r["origin"])]=num(r["pieces_per_shift"])
            except Exception:pass
        rows=[];all_people=set()
        for st in stores:
            in_caps=[r for r in caps if r["store"]==st and ss<=str(r["date"])<=es];in_prod=[r for r in prod if r["store"]==st and ss<=str(r["date"])<=es]
            arrival=sum(num(r.get("arrival")) for r in in_caps);released=sum(num(r.get("released")) for r in in_caps);processed=sum(num(r.get("pieces")) for r in in_prod)
            hist_arr=sum(num(r.get("arrival")) for r in caps if r["store"]==st and str(r["date"])<=es);hist_proc=sum(num(r.get("pieces")) for r in prod if r["store"]==st and str(r["date"])<=es)
            explicit=[r for r in in_caps if r.get("pending_manual") is not None];explicit.sort(key=lambda r:str(r["date"]));pending=num(explicit[-1].get("pending_manual")) if explicit else max(hist_arr-hist_proc,0)
            pc=sum(num(r.get("pieces")) for r in in_prod if str(r.get("origin"))=="Colgado");pd=sum(num(r.get("pieces")) for r in in_prod if str(r.get("origin"))=="Doblado");mix=pc+pd;weighted=((pc*std["Colgado"]+pd*std["Doblado"])/mix) if mix else ((std["Colgado"]+std["Doblado"])/2);needed=int(math.ceil(pending/weighted)) if pending>0 and weighted>0 else 0
            people={(str(r.get("employee_no") or ""),str(r.get("employee_name") or "")) for r in in_prod if str(r.get("employee_name") or "").strip()};all_people|={(st,a,b) for a,b in people};rows.append({"store":st,"arrival":arrival,"processed":processed,"released":released,"pending":pending,"required":needed,"collaborators":len(people)})
        summary={"arrival":sum(r["arrival"] for r in rows),"processed":sum(r["processed"] for r in rows),"released":sum(r["released"] for r in rows),"pending":sum(r["pending"] for r in rows),"required":sum(r["required"] for r in rows),"collaborators":len(all_people)};workload=summary["processed"]+summary["pending"];summary["efficiency_pct"]=summary["processed"]/workload*100 if workload else 0;summary["productivity_avg"]=summary["processed"]/max(summary["collaborators"],1)
        alerts=[]
        if summary["pending"]>0:alerts.append({"level":"warn","text":f"Origen tiene {summary['pending']:,.0f} piezas pendientes."})
        if summary["required"]>summary["collaborators"]:alerts.append({"level":"bad","text":f"Se requieren {summary['required']} colaboradores para Origen; hay {summary['collaborators']} con productividad en el periodo."})
        if not alerts:alerts.append({"level":"ok","text":"Sin alertas críticas de mercancía de Origen para el periodo."})
        return {"start_date":ss,"end_date":es,"store":selected,"summary":summary,"rows":rows,"alerts":alerts}

    css = r'''<style id="v165-corrections-css">
#operativoNav [data-opview="Operación"],#operativoNav [data-opview="Operación Diaria"],#operativoNav [data-opview="Reporte Semanal"],#operativoNav [data-opview="Reporte Mensual"],#operativoNav [data-opview="Matriz de recolección"]{display:none!important}
body[data-v163-module="operativo"] #v161FilterBar .v161-filter-grid{grid-template-columns:repeat(5,minmax(130px,1fr)) auto!important}
body[data-v163-module="operation"] #v161FilterBar .v161-filter-grid{grid-template-columns:repeat(3,minmax(150px,1fr)) auto!important}
body[data-v163-module="analysis"] .panel.compact-filter{border:1px solid #d6e3f1!important;border-radius:14px!important;background:#fff!important;padding:10px!important;box-shadow:0 3px 12px rgba(18,63,125,.04)!important;margin:8px 0 10px!important}
body[data-v163-module="analysis"] .panel.compact-filter .filter-caption,body[data-v163-module="analysis"] .panel.compact-filter .filter label{color:#60758f!important;font-size:8px!important;font-weight:950!important;text-transform:uppercase!important}
body[data-v163-module="analysis"] .panel.compact-filter .switches{gap:7px!important;margin:4px 0 8px!important}
body[data-v163-module="analysis"] .panel.compact-filter .switch{min-height:38px!important;border:1px solid #cbdcec!important;border-radius:9px!important;padding:8px 13px!important;background:#fff!important;color:#103f7d!important}
body[data-v163-module="analysis"] .panel.compact-filter .switch.active{background:#176fe8!important;color:#fff!important;border-color:#176fe8!important}
body[data-v163-module="analysis"] .panel.compact-filter select{min-height:40px!important;border:1px solid #cbdcec!important;border-radius:9px!important;color:#103f7d!important;font-weight:800!important;background:#fff!important}
#v165RouteMatrix{margin:0 0 14px}.v165-matrix-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin:0 0 8px}.v165-matrix-head h3{margin:0;color:#103f7d;font-size:15px}.v165-matrix-head small{color:#6b7d92;font-size:8px}.v165-hour-table{min-width:1120px}.v165-hour-table td{text-align:center;vertical-align:top}.v165-cell-total{font-weight:950;color:#103f7d}.v165-cell-note{display:block;font-size:7px;color:#71839a;margin-top:2px}.v165-empty{color:#a0aec0}
.v165-alert-panel{border:1px solid #ffd2d2;background:#fff7f7;border-radius:12px;padding:11px;margin:10px 0}.v165-alert-panel h3{margin:0 0 7px;color:#a31515;font-size:12px}.v165-alert-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.v165-alert-item{background:#fff;border:1px solid #f0d6d6;border-radius:8px;padding:8px;font-size:8px;color:#5f3540}
.v165-origin-flow{border:1px solid #d8e4f0;border-radius:12px;padding:12px;background:#fff;margin:9px 0}.v165-origin-flow h3{margin:0 0 8px;color:#103f7d;font-size:12px}.v165-origin-flow-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.v165-origin-mini{background:#f7faff;border:1px solid #e0e8f2;border-radius:9px;padding:9px}.v165-origin-mini small{display:block;color:#6b7d92;font-size:7px;text-transform:uppercase;font-weight:900}.v165-origin-mini b{display:block;color:#103f7d;font-size:18px;margin-top:4px}
#v165StatusField{position:relative}.v165-status-icon{position:absolute;left:11px;bottom:11px;color:#176fe8;width:18px;height:18px}.v165-status-icon svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.8}#v165StatusField select{padding-left:36px!important}
@media(max-width:900px){.v165-alert-list{grid-template-columns:1fr}.v165-origin-flow-grid{grid-template-columns:repeat(2,minmax(0,1fr))}body[data-v163-module="operativo"] #v161FilterBar .v161-filter-grid,body[data-v163-module="operation"] #v161FilterBar .v161-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
</style>'''

    js = r'''<script id="v165-corrections-js">
(function(){if(window.__V165_CORRECTIONS)return;window.__V165_CORRECTIONS=true;
const $=s=>document.querySelector(s),$$=s=>Array.from(document.querySelectorAll(s)),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])),nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0}),n1=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:1}),norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();window.V165_COMMERCIAL_STATUS=window.V165_COMMERCIAL_STATUS||'Todos';
const icons={dashboard:'<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',layers:'<svg viewBox="0 0 24 24"><path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/></svg>',store:'<svg viewBox="0 0 24 24"><path d="M4 10v10h16V10"/><path d="M3 10 5 4h14l2 6"/><path d="M8 20v-6h8v6"/><path d="M3 10c1 2 3 2 4 0 1 2 3 2 4 0 1 2 3 2 4 0 1 2 3 2 4 0"/></svg>',grid:'<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',pin:'<svg viewBox="0 0 24 24"><path d="M12 21s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12Z"/><circle cx="12" cy="9" r="2.5"/></svg>',sliders:'<svg viewBox="0 0 24 24"><path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h8M16 18h4"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="14" cy="18" r="2"/></svg>',upload:'<svg viewBox="0 0 24 24"><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 20h16"/></svg>',tag:'<svg viewBox="0 0 24 24"><path d="M20 13 11 22 2 13V4h9l9 9Z"/><circle cx="7" cy="9" r="1.5"/></svg>'};
function currentModule(){return document.body.dataset.v163Module||''}function buttonText(b){return norm((b?.textContent||'').replace(/\s+/g,' '))}
function cleanupOperativoNav(){const nav=$('#operativoNav');if(!nav)return;const remove=['operacion','operacion diaria','dia','reporte semanal','semanal','reporte mensual','mensual','matriz de recoleccion'];$$('#operativoNav .switch').forEach(b=>{if(remove.includes(buttonText(b)))b.remove()})}
function ensureViewOptions(){const src=$('#operPeriodMode');if(!src)return;const wanted=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']],current=src.value||window.OPER_PERIOD?.type||'week',existing=[...src.options].map(o=>o.value);if(wanted.some(x=>!existing.includes(x[0]))||src.options.length!==4){src.innerHTML='';wanted.forEach(([v,l])=>src.add(new Option(l,v)))}src.value=wanted.some(x=>x[0]===current)?current:'week';const proxy=$('#v161FilterBar [data-source="operPeriodMode"]');if(proxy){proxy.innerHTML='';wanted.forEach(([v,l])=>proxy.add(new Option(l,v)));proxy.value=src.value}if(currentModule()==='operativo')proxy?.closest('.v161-field')?.classList.remove('hidden')}
function cleanupOperationTabs(){const bar=$('.v125-tabs');if(!bar)return;const desired=['resumen','captura diaria','cargar productividad','productividad','estandares'],seen=new Set();[...bar.querySelectorAll('.v125-tab')].forEach(b=>{const t=buttonText(b),key=t.startsWith('resumen')?'resumen':t.startsWith('captura diaria')?'captura diaria':t.startsWith('cargar productividad')?'cargar productividad':t==='productividad'?'productividad':t.startsWith('estandar')?'estandares':'';if(!key||seen.has(key)){b.remove();return}seen.add(key);b.dataset.v165OpTab=key});desired.forEach(k=>{const b=bar.querySelector(`[data-v165-op-tab="${k}"]`);if(b)bar.appendChild(b)})}
document.addEventListener('click',async e=>{const b=e.target.closest?.('.v125-tabs [data-v165-op-tab]');if(!b||currentModule()!=='operation')return;e.preventDefault();e.stopImmediatePropagation();const key=b.dataset.v165OpTab;window.V149_OPERATION_TAB=key==='estandares'?'standards':key==='captura diaria'?'daily':key==='cargar productividad'?'capture':key;window.V125_OPERATION_TAB=window.V149_OPERATION_TAB;try{await window.renderOperativoView('Operación',true)}catch(err){console.warn('[V165] operación tab',err)}setTimeout(()=>{cleanupOperationTabs();decorateOperationOrigin()},60)},true);
async function injectInactiveCollaborators(){if(currentModule()!=='operativo')return;const active=$('#operativoNav .switch.active');if(!active||!buttonText(active).includes('productividad'))return;const cont=$('#operativoDynamicContent');if(!cont||cont.querySelector('#v165InactiveCollaborators'))return;const q=new URLSearchParams({period_type:$('#operPeriodMode')?.value||window.OPER_PERIOD?.type||'week',period_value:$('#operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',store:$('#operStoreSelect')?.value||'Compañía'});try{const d=await api('/api/operations/inactive-collaborators-v165?'+q,{timeoutMs:60000});if(!d.rows?.length)return;const html=`<div id="v165InactiveCollaborators" class="v165-alert-panel"><h3>⚠ Colaboradores sin productividad en el periodo · ${d.count}</h3><div class="v165-alert-list">${d.rows.map(x=>`<div class="v165-alert-item"><b>${esc(x.name)}</b><br>${esc(x.store)} · última productividad ${esc(x.last_date)}</div>`).join('')}</div></div>`;const first=cont.querySelector('.report-kpis');if(first)first.insertAdjacentHTML('afterend',html);else cont.insertAdjacentHTML('afterbegin',html)}catch(err){console.warn('[V165] alerta colaboradores',err)}}
function matrixCell(c){const t=Number(c.total||0);if(!t)return '<span class="v165-empty">—</span>';return `<span class="v165-cell-total">${nf(t)}</span><span class="v165-cell-note">M ${nf(c.muertos)} · C ${nf(c.cajas)} · P ${nf(c.probador)}</span>`}
async function injectRouteMatrix(){if(currentModule()!=='operativo')return;const active=$('#operativoNav .switch.active');if(!active||!buttonText(active).includes('recorridos'))return;const cont=$('#operativoDynamicContent');if(!cont)return;cont.querySelector('#v165RouteMatrix')?.remove();const q=new URLSearchParams({period_type:$('#operPeriodMode')?.value||window.OPER_PERIOD?.type||'week',period_value:$('#operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',store:$('#operStoreSelect')?.value||'Compañía',area:$('#operAreaSelect')?.value||'Todas',activity:$('#operActivitySelect')?.value||'Todas'});try{const d=await api('/api/operations/collection-hourly-v165?'+q,{timeoutMs:120000}),total=Number(d.totals?.total||0),html=`<div id="v165RouteMatrix"><div class="v165-matrix-head"><div><h3>Matriz de recolección de mercancía</h3><small>Lunes a domingo · hora completa · ${esc(d.start_date)} a ${esc(d.end_date)}</small></div><div><b>${nf(total)} pzas</b></div></div><div class="tablewrap"><table class="table v165-hour-table"><thead><tr><th>Hora</th>${d.days.map(x=>`<th>${esc(x)}</th>`).join('')}<th>Total</th></tr></thead><tbody>${d.rows.map(r=>`<tr><td><b>${esc(r.label)}</b></td>${r.cells.map(matrixCell).map(x=>`<td>${x}</td>`).join('')}<td><b>${nf(r.total)}</b></td></tr>`).join('')}</tbody></table></div><div class="note" style="margin-top:7px">Muertos ${nf(d.totals?.muertos)} · Cajas ${nf(d.totals?.cajas)} · Probador ${nf(d.totals?.probador)}</div></div>`;cont.insertAdjacentHTML('afterbegin',html)}catch(err){console.warn('[V165] matriz recorridos',err)}}
async function decorateOperationOrigin(){if(currentModule()!=='operation')return;cleanupOperationTabs();const active=$('.v125-tabs .active');if(active&&!buttonText(active).startsWith('resumen'))return;const cont=$('#operativoDynamicContent');if(!cont)return;const q=new URLSearchParams({period_type:$('#operPeriodMode')?.value||window.OPER_PERIOD?.type||'day',period_value:$('#operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',store:$('#operStoreSelect')?.value||'Compañía'});try{const d=await api('/api/operation/origin-only-v165?'+q,{timeoutMs:60000}),s=d.summary||{};$$('.v149-kpi,.v125-kpi,.report-kpi,.kpi').forEach(card=>{const label=norm(card.querySelector('small,.lab,.rk-label')?.textContent||''),val=card.querySelector('b,.val,.rk-value'),note=card.querySelector('span,.note,.rk-sub');if(!val)return;if(label.includes('llegada origen'))val.textContent=nf(s.arrival);if(label.includes('productividad registrada'))val.textContent=nf(s.processed);if(label.includes('mercancia liberada')){val.textContent=nf(s.released);if(note)note.textContent='Sólo mercancía de Origen'}if(label==='pendiente'||label.includes('piezas por procesar'))val.textContent=nf(s.pending);if(label.includes('eficiencia'))val.textContent=n1(s.efficiency_pct)+'%';if(label.includes('prod. promedio'))val.textContent=nf(s.productivity_avg);if(label.includes('colaboradores necesarios')){val.textContent=nf(s.required);if(note)note.textContent='Necesarios sólo para Origen'}if(label==='colaboradores'||label.includes('con productividad'))val.textContent=nf(s.collaborators)});const panels=[...cont.querySelectorAll('.v149-panel,.v126-panel,.panel')],target=panels.find(p=>norm(p.querySelector('h3')?.textContent||'').includes('origen vs cambios')),flow=`<div class="v165-origin-flow"><h3>Flujo de mercancía de Origen</h3><div class="v165-origin-flow-grid"><div class="v165-origin-mini"><small>Llegada</small><b>${nf(s.arrival)}</b></div><div class="v165-origin-mini"><small>Procesadas</small><b>${nf(s.processed)}</b></div><div class="v165-origin-mini"><small>Mercancía liberada</small><b>${nf(s.released)}</b></div><div class="v165-origin-mini"><small>Pendiente</small><b>${nf(s.pending)}</b></div></div></div>`;if(target)target.outerHTML=flow;else if(!cont.querySelector('.v165-origin-flow'))cont.insertAdjacentHTML('beforeend',flow);const alertPanel=[...cont.querySelectorAll('.v149-panel,.v126-panel,.panel')].find(p=>norm(p.querySelector('h3')?.textContent||'').includes('alertas operativas'));if(alertPanel)alertPanel.innerHTML='<h3>Alertas operativas · Origen</h3>'+d.alerts.map(a=>`<div class="v149-alert ${a.level||'warn'}">${esc(a.text)}</div>`).join('')}catch(err){console.warn('[V165] origen-only',err)}}
async function ensureStatusField(){if(currentModule()!=='analysis')return;const grid=$('#v161FilterGrid'),bar=$('#v161FilterBar');if(!grid||!bar?.classList.contains('on'))return;let field=$('#v165StatusField');if(!field){field=document.createElement('div');field.id='v165StatusField';field.className='v161-field';field.innerHTML='<label>Estatus</label><select id="v165StatusSelect"><option value="Todos">Todos</option></select><span class="v165-status-icon">'+icons.tag+'</span>';const apply=grid.querySelector('.v161-apply');grid.insertBefore(field,apply);field.querySelector('select').addEventListener('change',e=>{window.V165_COMMERCIAL_STATUS=e.target.value||'Todos'})}const sel=$('#v165StatusSelect');if(sel&&sel.dataset.week!==($('#week')?.value||'')){try{const d=await api('/api/commercial/status-values-v165?week='+encodeURIComponent($('#week')?.value||''),{timeoutMs:60000}),current=window.V165_COMMERCIAL_STATUS||'Todos';sel.innerHTML='<option value="Todos">Todos</option>'+(d.values||[]).map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');sel.value=[...sel.options].some(o=>o.value===current)?current:'Todos';window.V165_COMMERCIAL_STATUS=sel.value;sel.dataset.week=$('#week')?.value||''}catch(_){}}}
const rawFetch=window.fetch.bind(window);window.fetch=function(input,init){try{const url=typeof input==='string'?input:(input?.url||''),targets=['/api/dashboard','/api/commercial-detail','/api/commercial-accordion','/api/model-ranking','/api/model-8020-summary'];if(currentModule()==='analysis'&&targets.some(p=>url.startsWith(p))){const st=window.V165_COMMERCIAL_STATUS||'Todos';if(st!=='Todos'){const u=new URL(url,location.origin);u.searchParams.set('status',st);if(typeof input==='string')input=u.pathname+u.search;else input=new Request(u.toString(),input)}}}catch(_){}return rawFetch(input,init)};
function commercialIcons(){$$('#analysisNav .switch').forEach(b=>{let span=b.querySelector('.v164-tab-icon');if(!span){span=document.createElement('span');span.className='v164-tab-icon';b.prepend(span)}const t=buttonText(b);span.innerHTML=t.includes('macro')?icons.dashboard:t.includes('acordeon')?icons.layers:t==='tiendas'?icons.store:t.includes('seccion')?icons.grid:t.includes('ubicacion')?icons.pin:t.includes('mas opciones')?icons.sliders:t.includes('carga')?icons.upload:icons.dashboard})}
function styleCommercialSubfilters(){if(currentModule()!=='analysis')return;$$('.panel.compact-filter').forEach(p=>p.classList.add('v165-toplike-filter'));const title=$('#champTitle');if(title)title.textContent=title.textContent.replace(/\s*·\s*primeros 150\s*$/i,' · todos los modelos que integran el 80%')}
function schedule(){[0,80,220,600,1200].forEach(ms=>setTimeout(async()=>{cleanupOperativoNav();ensureViewOptions();cleanupOperationTabs();commercialIcons();styleCommercialSubfilters();await ensureStatusField();if(currentModule()==='operativo'){await injectInactiveCollaborators();await injectRouteMatrix()}if(currentModule()==='operation')await decorateOperationOrigin()},ms))}
const prevRender=window.renderOperativoView;if(typeof prevRender==='function'){window.renderOperativoView=async function(name,force=false){const out=await prevRender.apply(this,arguments);setTimeout(async()=>{cleanupOperativoNav();ensureViewOptions();cleanupOperationTabs();if(name==='Cumplimiento de Recorridos')await injectRouteMatrix();if(name==='Productividad por Colaborador')await injectInactiveCollaborators();if(name==='Operación')await decorateOperationOrigin()},40);return out}}
document.addEventListener('click',e=>{if(e.target.closest?.('[data-main],#operativoNav,#analysisNav,.v125-tabs,#v161FilterBar,.compact-filter'))schedule()},true);document.addEventListener('change',e=>{if(e.target?.matches?.('select,input')){if(e.target.id==='operPeriodMode'||e.target.dataset?.source==='operPeriodMode')setTimeout(ensureViewOptions,80);schedule()}},true);const mo=new MutationObserver(()=>{clearTimeout(window.__v165mo);window.__v165mo=setTimeout(schedule,90)});if(document.body)mo.observe(document.body,{childList:true,subtree:true});if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();console.info('[V165] Correcciones integrales instaladas.');})();
</script>'''

    @m.app.middleware("http")
    async def _v165_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v165-corrections-css" not in html:html=html.replace("</head>",css+"</head>",1)
            if "v165-corrections-js" not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V165"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V165] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V165_CORRECTIONS=True
    print("[V165] Filtros, Recorridos/Matriz, Operación Origen y Comercial corregidos.",flush=True)
