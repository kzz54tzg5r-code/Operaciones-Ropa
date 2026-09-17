"""V166 · Estabilización integral solicitada 17-sep-2026.

Objetivos:
- Un solo filtro operativo real con Vista Día/Semanal/Mensual/Anual y periodo válido.
- Colaboradores persistentes por tienda; baja/reactivación y alerta de quienes no registran productividad.
- Matriz horaria L-D integrada al inicio de Recorridos.
- Operación enfocada exclusivamente a mercancía de Origen, preservando Captura diaria/Cargar productividad.
- Comercial: filtro Estatus real, MARCA real, filtros internos uniformes, una sola tabla de Ubicación/Área.
- Modelos 80/20 completos (sin corte arbitrario de 150) con tablas de desplazamiento interno.
- Ventas: recuperar meta y año anterior desde PDF cuando existan; respetar metas manuales.
- UI estable: sin MutationObserver global ni escrituras repetitivas que provoquen brincos en Carga de datos.
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

PARSER_VERSION = 166
_STATUS_CTX: ContextVar[str] = ContextVar("v166_commercial_status", default="Todos")


def install(m):
    if getattr(m, "_V166_STABILITY_ROSTER_FILTERS", False):
        return

    def norm(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.casefold().strip().split())

    def num(value):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def bounds(ptype: str, value: str):
        ptype = str(ptype or "week").strip().lower()
        value = str(value or "").strip()
        today = date.today()
        if ptype == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date()
            return d, d
        if ptype == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt:
                y, w = int(mt.group(1)), int(mt.group(2))
            else:
                iso = today.isocalendar(); y, w = iso.year, iso.week
            d = date.fromisocalendar(y, w, 1)
            return d, d + timedelta(days=6)
        if ptype == "month":
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            if mt:
                y, mo = int(mt.group(1)), int(mt.group(2))
            else:
                y, mo = today.year, today.month
            d = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return d, nxt - timedelta(days=1)
        if ptype == "year":
            y = int(value or today.year)
            return date(y, 1, 1), date(y, 12, 31)
        return date(2000, 1, 1), today

    with m.db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS operation_collaborators(
                store TEXT NOT NULL,
                name_key TEXT NOT NULL,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                first_seen TEXT DEFAULT '',
                last_seen TEXT DEFAULT '',
                last_activity TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                PRIMARY KEY(store,name_key)
            )
        """)

    def is_productive_row(r):
        if num(r.get("productividad")) > 0:
            return True
        if num(r.get("acondicionado")) > 0 or num(r.get("ubicado")) > 0 or num(r.get("recolectadas")) > 0:
            return True
        act = norm(r.get("activity") or r.get("activity_original"))
        reason = norm(r.get("reason"))
        return any(x in act for x in ("acondicion", "habilit", "ubic", "recoleccion")) or "caja" in reason or "probador" in reason

    def sync_collaborators():
        found = {}
        for r in list((m.load_ops() or {}).get("rows") or []):
            if not is_productive_row(r):
                continue
            name = " ".join(str(r.get("name") or "").split()).strip()
            store = str(r.get("store") or "").strip()
            ds = str(r.get("date") or "")[:10]
            if not name or not store or norm(name) in ("nan", "none", "sin dato"):
                continue
            key = (store, norm(name))
            item = found.setdefault(key, {
                "store": store, "name_key": norm(name), "name": name,
                "first_seen": ds, "last_seen": ds,
                "last_activity": str(r.get("activity") or r.get("activity_original") or ""),
            })
            if ds and (not item["first_seen"] or ds < item["first_seen"]):
                item["first_seen"] = ds
            if ds and (not item["last_seen"] or ds > item["last_seen"]):
                item["last_seen"] = ds
                item["last_activity"] = str(r.get("activity") or r.get("activity_original") or "")
                item["name"] = name
        now = datetime.now().isoformat(timespec="seconds")
        if found:
            with m.db() as con:
                for item in found.values():
                    con.execute("""
                        INSERT INTO operation_collaborators(store,name_key,name,active,first_seen,last_seen,last_activity,updated_at,updated_by)
                        VALUES(?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(store,name_key) DO UPDATE SET
                            name=excluded.name,
                            first_seen=CASE WHEN operation_collaborators.first_seen='' OR excluded.first_seen<operation_collaborators.first_seen THEN excluded.first_seen ELSE operation_collaborators.first_seen END,
                            last_seen=CASE WHEN excluded.last_seen>operation_collaborators.last_seen THEN excluded.last_seen ELSE operation_collaborators.last_seen END,
                            last_activity=CASE WHEN excluded.last_seen>=operation_collaborators.last_seen THEN excluded.last_activity ELSE operation_collaborators.last_activity END
                    """, (
                        item["store"], item["name_key"], item["name"], 1,
                        item["first_seen"], item["last_seen"], item["last_activity"], now, "sync-v166"
                    ))

    try:
        sync_collaborators()
    except Exception as exc:
        print(f"[V166] roster sync warning: {type(exc).__name__}: {exc}", flush=True)

    @m.app.get("/api/operations/collaborators-v166")
    def operation_collaborators_v166(request: Request, store: str="Compañía", include_inactive: bool=True):
        actor = m.require_user(request)
        try:
            sync_collaborators()
        except Exception:
            pass
        selected = m.effective_store(actor, store)
        sql = "SELECT store,name_key,name,active,first_seen,last_seen,last_activity,updated_at,updated_by FROM operation_collaborators"
        params = []
        clauses = []
        if selected and selected != "Compañía":
            clauses.append("store=?"); params.append(selected)
        if not include_inactive:
            clauses.append("active=1")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY store,name"
        with m.db() as con:
            rows = [dict(r) for r in con.execute(sql, params).fetchall()]
        return {"store":selected, "rows":rows, "editable":str(actor.get("role") or "") in ("superadmin","admin")}

    @m.app.put("/api/operations/collaborators-v166/status")
    async def operation_collaborator_status_v166(request: Request):
        actor = m.require_user(request, ("superadmin","admin"))
        body = await request.json()
        store = " ".join(str(body.get("store") or "").split()).strip()
        name = " ".join(str(body.get("name") or "").split()).strip()
        active = 1 if bool(body.get("active")) else 0
        if not store or not name:
            raise HTTPException(400, "Falta colaborador o tienda")
        key = norm(name)
        now = datetime.now().isoformat(timespec="seconds")
        with m.db() as con:
            existing = con.execute("SELECT * FROM operation_collaborators WHERE store=? AND name_key=?", (store,key)).fetchone()
            if existing:
                con.execute("UPDATE operation_collaborators SET active=?,updated_at=?,updated_by=? WHERE store=? AND name_key=?", (active,now,actor["username"],store,key))
            else:
                con.execute("INSERT INTO operation_collaborators(store,name_key,name,active,first_seen,last_seen,last_activity,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?)", (store,key,name,active,"","","",now,actor["username"]))
        return {"ok":True, "store":store, "name":name, "active":bool(active), "message":"Colaborador reactivado" if active else "Colaborador dado de baja"}

    @m.app.get("/api/operations/missing-productivity-v166")
    def missing_productivity_v166(request: Request, period_type: str="week", period_value: str="", store: str="Compañía"):
        actor = m.require_user(request)
        start, end = bounds(period_type, period_value)
        selected = m.effective_store(actor, store)
        try:
            sync_collaborators()
        except Exception:
            pass
        with m.db() as con:
            sql = "SELECT store,name_key,name,first_seen,last_seen,last_activity FROM operation_collaborators WHERE active=1"
            params=[]
            if selected and selected != "Compañía":
                sql += " AND store=?"; params.append(selected)
            roster = [dict(r) for r in con.execute(sql, params).fetchall()]
        current=set()
        for r in list((m.load_ops() or {}).get("rows") or []):
            if not is_productive_row(r):
                continue
            rs=str(r.get("store") or "").strip(); name=" ".join(str(r.get("name") or "").split()).strip(); ds=str(r.get("date") or "")[:10]
            if not rs or not name or not ds: continue
            if selected and selected!="Compañía" and rs!=selected: continue
            try:d=date.fromisoformat(ds)
            except Exception:continue
            if start<=d<=end:current.add((rs,norm(name)))
        missing=[]
        for r in roster:
            first=str(r.get("first_seen") or "")[:10]
            if first:
                try:
                    if date.fromisoformat(first)>end:
                        continue
                except Exception:
                    pass
            if (r["store"],r["name_key"]) not in current:
                missing.append({"store":r["store"],"name":r["name"],"last_date":r.get("last_seen") or "","last_activity":r.get("last_activity") or ""})
        missing.sort(key=lambda x:(x["store"],x["name"]))
        return {"count":len(missing),"rows":missing,"start_date":start.isoformat(),"end_date":end.isoformat(),"store":selected}

    DAY_NAMES=("Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo")

    def hour_from(value):
        raw=str(value or "").strip()
        if not raw or raw.lower() in ("nan","nat","none"): return None
        mt=re.search(r"(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)", raw)
        if mt:return int(mt.group(1))
        try:
            x=float(raw)
            if 0<=x<1:return int((x*24)%24)
        except Exception:pass
        return None

    @m.app.get("/api/operations/collection-hour-matrix-v166")
    def collection_hour_matrix_v166(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor=m.require_user(request); start,end=bounds(period_type,period_value); selected=m.effective_store(actor,store)
        grouped=defaultdict(lambda:{"muertos":0.0,"cajas":0.0,"probador":0.0,"names":set(),"stores":set()})
        totals={"muertos":0.0,"cajas":0.0,"probador":0.0}; first=None; last=None; stores=set()
        for r in list((m.load_ops() or {}).get("rows") or []):
            ds=str(r.get("date") or "")[:10]
            try:d=date.fromisoformat(ds)
            except Exception:continue
            if d<start or d>end:continue
            rs=str(r.get("store") or "").strip()
            if selected and selected!="Compañía" and rs!=selected:continue
            if str(area or "") not in ("","Todas","Todos") and norm(r.get("area"))!=norm(area):continue
            if str(activity or "") not in ("","Todas","Todos"):
                act=r.get("activity") or r.get("activity_original") or ""
                if norm(act)!=norm(activity):continue
            muertos=num(r.get("muertos"));cajas=num(r.get("cajas"));prob=num(r.get("probador"))
            if muertos<=0 and cajas<=0 and prob<=0:continue
            h=hour_from(r.get("start_time"))
            if h is None:continue
            first=h if first is None else min(first,h); last=h if last is None else max(last,h)
            g=grouped[(h,d.weekday())];g["muertos"]+=muertos;g["cajas"]+=cajas;g["probador"]+=prob
            nm=" ".join(str(r.get("name") or "").split()).strip()
            if nm:g["names"].add(nm)
            if rs:g["stores"].add(rs);stores.add(rs)
            totals["muertos"]+=muertos;totals["cajas"]+=cajas;totals["probador"]+=prob
        if first is None or last is None:
            return {"days":list(DAY_NAMES),"hours":[],"summary":{"pieces":0,"stores":0,"first_hour":None,"last_hour":None},"source_totals":totals}
        hours=[]
        for h in range(first,last+1):
            cells=[]
            for dno in range(7):
                g=grouped[(h,dno)];total=g["muertos"]+g["cajas"]+g["probador"]
                cells.append({"day":DAY_NAMES[dno],"total":total,"muertos":g["muertos"],"cajas":g["cajas"],"probador":g["probador"],"responsible":", ".join(sorted(g["names"])),"stores":len(g["stores"])})
            hours.append({"hour":h,"label":f"{h:02d}:00","cells":cells,"total":sum(c["total"] for c in cells)})
        return {"days":list(DAY_NAMES),"hours":hours,"summary":{"pieces":sum(totals.values()),"stores":len(stores),"first_hour":first,"last_hour":last},"source_totals":totals}

    @m.app.get("/api/operation/origin-summary-v166")
    def operation_origin_summary_v166(request: Request, period_type: str="day", period_value: str="", store: str="Compañía"):
        actor=m.require_user(request);start,end=bounds(period_type,period_value);ss,es=start.isoformat(),end.isoformat();selected=m.effective_store(actor,store)
        stores=[selected] if selected!="Compañía" else list(m.store_names(True) or getattr(m,"PROJECT_STORES",[]))
        if not stores:return {"summary":{},"stores":[],"top":[],"alerts":[]}
        ph=",".join("?" for _ in stores)
        with m.db() as con:
            caps=[dict(r) for r in con.execute(f"SELECT date,store,arrival,released,pending_manual FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ({ph})",(es,*stores)).fetchall()]
            prod=[dict(r) for r in con.execute(f"SELECT date,store,employee_no,employee_name,origin,pieces FROM operation_productivity WHERE origin IN ('Colgado','Doblado') AND date<=? AND store IN ({ph})",(es,*stores)).fetchall()]
            standards={str(r["origin"]):num(r["pieces_per_shift"]) for r in con.execute("SELECT origin,pieces_per_shift FROM operation_standards").fetchall()}
        standards.setdefault("Colgado",1228.0);standards.setdefault("Doblado",906.0)
        period_caps=[r for r in caps if ss<=str(r["date"])<=es];period_prod=[r for r in prod if ss<=str(r["date"])<=es]
        arrival=sum(num(r.get("arrival")) for r in period_caps);released=sum(num(r.get("released")) for r in period_caps);processed=sum(num(r.get("pieces")) for r in period_prod)
        previous_arrival=sum(num(r.get("arrival")) for r in caps if str(r["date"])<ss);previous_processed=sum(num(r.get("pieces")) for r in prod if str(r["date"])<ss);pending_start=max(previous_arrival-previous_processed,0.0)
        explicit=[r for r in period_caps if r.get("pending_manual") is not None];explicit.sort(key=lambda x:str(x["date"]));pending=num(explicit[-1]["pending_manual"]) if explicit else max(pending_start+arrival-processed,0.0)
        people={};targets=0.0;seen=set()
        for r in period_prod:
            key=(str(r.get("employee_no") or r.get("employee_name") or ""),str(r.get("store") or ""));g=people.setdefault(key,{"name":str(r.get("employee_name") or "Sin nombre"),"store":str(r.get("store") or ""),"pieces":0.0,"days":set(),"target":0.0})
            g["pieces"]+=num(r.get("pieces"));g["days"].add(str(r.get("date")))
            sk=(key,str(r.get("date")),str(r.get("origin") or ""))
            if sk not in seen:seen.add(sk);t=num(standards.get(str(r.get("origin") or "")));g["target"]+=t;targets+=t
        top=[]
        for g in people.values():
            days=max(len(g["days"]),1);pct=g["pieces"]/g["target"]*100 if g["target"] else 0
            top.append({"name":g["name"],"store":g["store"],"pieces":g["pieces"],"daily":g["pieces"]/days,"compliance_pct":pct})
        top.sort(key=lambda x:(-x["compliance_pct"],-x["pieces"],x["name"]))
        empdays=sum(max(len(g["days"]),1) for g in people.values());avg=sum(g["pieces"] for g in people.values())/empdays if empdays else 0.0
        efficiency=processed/(pending_start+arrival)*100 if pending_start+arrival>0 else 0.0;compliance=processed/targets*100 if targets else 0.0
        store_rows=[];required_total=0
        for st in stores:
            pc=sum(num(r.get("pieces")) for r in period_prod if r.get("store")==st and r.get("origin")=="Colgado");pdbl=sum(num(r.get("pieces")) for r in period_prod if r.get("store")==st and r.get("origin")=="Doblado");mix=pc+pdbl
            weighted=((pc*standards["Colgado"]+pdbl*standards["Doblado"])/mix) if mix>0 else (standards["Colgado"]+standards["Doblado"])/2
            st_caps=[r for r in caps if r.get("store")==st];st_prod=[r for r in prod if r.get("store")==st]
            sa=sum(num(r.get("arrival")) for r in st_caps if ss<=str(r.get("date"))<=es);sr=sum(num(r.get("released")) for r in st_caps if ss<=str(r.get("date"))<=es);sp=sum(num(r.get("pieces")) for r in st_prod if ss<=str(r.get("date"))<=es)
            pre=max(sum(num(r.get("arrival")) for r in st_caps if str(r.get("date"))<ss)-sum(num(r.get("pieces")) for r in st_prod if str(r.get("date"))<ss),0.0)
            ex=[r for r in st_caps if ss<=str(r.get("date"))<=es and r.get("pending_manual") is not None];ex.sort(key=lambda x:str(x.get("date")));pend=num(ex[-1]["pending_manual"]) if ex else max(pre+sa-sp,0.0)
            req=int(math.ceil(pend/weighted)) if pend>0 and weighted>0 else 0;required_total+=req
            target_store=sum(num(standards.get(str(r.get("origin") or ""))) for r in st_prod if ss<=str(r.get("date"))<=es)
            store_rows.append({"store":st,"arrival":sa,"processed":sp,"released":sr,"pending":pend,"required":req,"target":target_store,"compliance_pct":sp/target_store*100 if target_store else 0.0})
        store_rows.sort(key=lambda x:(-x["compliance_pct"],-x["processed"],x["store"]))
        alerts=[]
        if pending>0:alerts.append({"level":"warn","text":f"Pendiente de Origen: {pending:,.0f} piezas por procesar."})
        if (pending_start+arrival)>0 and efficiency<75:alerts.append({"level":"bad","text":f"Eficiencia de Origen baja: {efficiency:.1f}%."})
        if not alerts:alerts=[{"level":"ok","text":"Sin alertas críticas de Origen para el periodo consultado."}]
        return {"start_date":ss,"end_date":es,"store":selected,"summary":{"arrival_origin":arrival,"processed":processed,"released":released,"pending":pending,"efficiency_pct":efficiency,"productivity_avg":avg,"compliance_pct":compliance,"collaborators":len(people),"required":required_total},"stores":store_rows,"top":top[:5],"alerts":alerts}

    try:
        import commercial.parsers as cp
        if not getattr(cp,"_V166_BRAND_PRIORITY",False):
            old_series=cp._series
            def series_v166(df,candidates,default="",contains=False):
                vals=list(candidates or []);keys=[cp.norm_text(x) for x in vals]
                if "MARCA" in keys and "MARCA PRICE" in keys:
                    rest=[x for x in vals if cp.norm_text(x) not in ("MARCA","MARCA PRICE")]
                    vals=["MARCA","MARCA PRICE",*rest]
                return old_series(df,vals,default,contains=contains)
            cp._series=series_v166;cp._V166_BRAND_PRIORITY=True
        m.read_capacity_file=cp.read_capacity_file
    except Exception as exc:
        print(f"[V166] brand priority warning: {type(exc).__name__}: {exc}",flush=True)

    def apply_status(work):
        status=str(_STATUS_CTX.get() or "Todos").strip()
        if work is None or getattr(work,"empty",True) or status in ("","Todos","Todas"):
            return work
        if "Estatus comercial" not in work.columns:return work
        keys=work["Estatus comercial"].fillna("").astype(str).map(norm)
        return work.loc[keys==norm(status)].copy()

    if hasattr(m,"_capacity_scope_v45") and not getattr(m,"_V166_SCOPE_STATUS",False):
        old_scope=m._capacity_scope_v45
        def scope_v166(frame,store="Compañía",section="Todas",catalog="Todos",add_area=False):
            return apply_status(old_scope(frame,store,section,catalog,add_area=add_area))
        m._capacity_scope_v45=scope_v166
        if hasattr(m,"_scope_capacity"):
            old_scope2=m._scope_capacity
            def scope2_v166(frame,store="Compañía",section="Todas",catalog="Todos"):
                return apply_status(old_scope2(frame,store,section,catalog))
            m._scope_capacity=scope2_v166
        m._V166_SCOPE_STATUS=True

    @m.app.middleware("http")
    async def v166_status_context(request,call_next):
        token=_STATUS_CTX.set(str(request.query_params.get("status") or "Todos"))
        try:return await call_next(request)
        finally:_STATUS_CTX.reset(token)

    @m.app.get("/api/commercial/status-options-v166")
    def status_options_v166(request: Request,week: str=""):
        m.require_user(request);frame=m._capacity_frame_for_period(week or "")
        if frame is None or frame.empty or "Estatus comercial" not in frame.columns:return {"values":[]}
        values=[];seen=set()
        for raw in frame["Estatus comercial"].fillna("").astype(str):
            value=" ".join(raw.split()).strip();key=norm(value)
            if value and key not in ("nan","none") and key not in seen:seen.add(key);values.append(value)
        values.sort(key=norm)
        return {"values":values}

    if hasattr(m,"_capacity_model_rows") and not getattr(m,"_V166_ALL_80",False):
        old_model_rows=m._capacity_model_rows
        def model_rows_v166(store="Compañía",section="Todas",mode="80_20",period="",catalog="Todos"):
            key=str(mode or "").lower()
            if key not in ("80_20","8020","top","champions"):
                return old_model_rows(store,section,mode,period,catalog)
            pd=m.pd;np=m.np;frame=m._capacity_frame_for_period(period);work=m._capacity_scope_v45(frame,store,section,catalog)
            if work is None or work.empty or "ID_ART" not in work.columns:return []
            work=work.copy();work["__id"]=work["ID_ART"].fillna("").astype(str).str.strip();work=work[~work["__id"].isin(["","nan","None"])]
            if work.empty:return []
            pcol,vcol=m._capacity_period_columns(period);tmp=pd.DataFrame({"__id":work["__id"]})
            sources={"existence":"Existencia","floor":"Existencia piso","warehouse":"Existencia bodega","suggested":"VPD","capacity":"Capacidad","sales_pzas":pcol,"sales_value":vcol,"sales_pzas_30":"Venta pzas 30","pzas_ult_cedis":"Pzas última entrada"}
            for dst,src in sources.items():tmp[dst]=pd.to_numeric(work[src],errors="coerce").fillna(0.0) if src in work.columns else 0.0
            agg=tmp.groupby("__id",sort=False).sum(numeric_only=True)
            ddi=pd.to_numeric(work.get("DDI",0),errors="coerce").replace([np.inf,-np.inf],np.nan) if "DDI" in work.columns else pd.Series(0,index=work.index)
            agg=agg.join(ddi.groupby(work["__id"]).mean().rename("ddi"),how="left");agg["ddi"]=pd.to_numeric(agg["ddi"],errors="coerce").fillna(0.0)
            for dst,src,default in (("model","Modelo",""),("brand","Marca","Sin marca"),("section","Sección","Sin sección"),("rubro","Subcategoría","Sin rubro")):
                if src in work.columns:
                    s=work[src].fillna("").astype(str).str.strip().replace({"":"", "nan":"", "None":""});first=pd.DataFrame({"__id":work["__id"],dst:s.replace("",pd.NA)}).groupby("__id",sort=False)[dst].first();agg=agg.join(first,how="left")
                else:agg[dst]=default
            if "Última entrada CEDIS a tienda" in work.columns:
                dates=pd.to_datetime(work["Última entrada CEDIS a tienda"],errors="coerce");agg=agg.join(dates.groupby(work["__id"]).max().rename("ultima_cedis"),how="left")
            else:agg["ultima_cedis"]=pd.NaT
            models=agg.reset_index().sort_values(["sales_value","sales_pzas","existence"],ascending=[False,False,False]).reset_index(drop=True);total=float(models["sales_value"].sum());models["cum_share"]=models["sales_value"].cumsum()/total*100 if total>0 else 0.0
            if total>0:
                hits=np.flatnonzero(models["cum_share"].to_numpy()>=80.0);last=int(hits[0]) if len(hits) else len(models)-1;models=models.iloc[:last+1].copy()
            else:models=models.head(50).copy()
            ids=set(models["__id"].astype(str));labels=work[work["__id"].isin(ids)].copy()
            def label_map(col,limit=3):
                if col not in labels.columns:return {}
                z=labels[["__id",col]].copy();z[col]=z[col].fillna("").astype(str).str.strip();z=z[~z[col].isin(["","nan","None"])].drop_duplicates()
                return {} if z.empty else z.groupby("__id",sort=False)[col].agg(lambda s:m._combine_labels(s,limit)).to_dict()
            loc_col="Ubicación detalle" if "Ubicación detalle" in labels.columns else ("Pasillo" if "Pasillo" in labels.columns else "")
            locations=label_map(loc_col) if loc_col else {};exhibitions=label_map("Exhibición",5);stores_map=label_map("Tienda",5);rows=[]
            for idx,r in enumerate(models.to_dict("records"),1):
                rid=str(r.get("__id") or "");cap=num(r.get("capacity"));ex=num(r.get("existence"));dt=r.get("ultima_cedis")
                try:dt_txt=pd.Timestamp(dt).strftime("%Y-%m-%d") if pd.notna(dt) else ""
                except Exception:dt_txt=""
                rows.append({"id_art":rid,"model":str(r.get("model") or rid),"brand":str(r.get("brand") or "Sin marca"),"section":str(r.get("section") or "Sin sección"),"rubro":str(r.get("rubro") or "Sin rubro"),"location":locations.get(rid,""),"exhibition":exhibitions.get(rid,""),"store":stores_map.get(rid,store if store!="Compañía" else "Compañía"),"rank":idx,"suggested":num(r.get("suggested")),"existence":ex,"capacity":cap,"occupancy":ex/cap*100 if cap else None,"sales_pzas_30":num(r.get("sales_pzas_30")),"sales_pzas":num(r.get("sales_pzas")),"sales_value":num(r.get("sales_value")),"floor":num(r.get("floor")),"warehouse":num(r.get("warehouse")),"ddi":num(r.get("ddi")),"ultima_cedis":dt_txt,"pzas_ult_cedis":num(r.get("pzas_ult_cedis")),"cum_share":num(r.get("cum_share")),"recurrence_weeks":0})
            return rows
        m._capacity_model_rows=model_rows_v166;m._V166_ALL_80=True

    def parse_money_token(text):
        raw=str(text or "").strip(); mt=re.search(r"-?\d[\d,]*(?:\.\d+)?",raw.replace("$",""))
        if not mt:return 0.0
        try:return float(mt.group(0).replace(",",""))
        except Exception:return 0.0

    def pdf_comparative(path: Path, year: int):
        result={"target_sales":0.0,"previous_sales":0.0,"pdf_current_sales":0.0,"diagnostic":""}
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages=pdf.pages[:min(3,len(pdf.pages))]
                all_candidates={"target":[],"previous":[],"current":[]}
                for pno,page in enumerate(pages,1):
                    text=page.extract_text(x_tolerance=2,y_tolerance=3) or ""
                    lines=[re.sub(r"\s+"," ",x).strip() for x in text.splitlines() if x.strip()]
                    for line in lines:
                        key=norm(line);vals=[parse_money_token(x) for x in re.findall(r"\$?\s*\d[\d,]*(?:\.\d+)?",line)];vals=[v for v in vals if v>=1000 and not (2020<=v<=2100)]
                        if not vals:continue
                        if any(t in key for t in ("meta","presupuesto","objetivo")):all_candidates["target"].append((30,max(vals),f"P{pno} {line[:120]}"))
                        if str(year-1) in key and any(t in key for t in ("venta","vta","real","acum")):all_candidates["previous"].append((40,max(vals),f"P{pno} {line[:120]}"))
                        if str(year) in key and any(t in key for t in ("venta","vta","real","acum")):all_candidates["current"].append((40,max(vals),f"P{pno} {line[:120]}"))
                    try:words=page.extract_words(x_tolerance=2,y_tolerance=3,use_text_flow=True) or []
                    except TypeError:words=page.extract_words() or []
                    anchors=[]
                    for w in words:
                        k=norm(w.get("text"));kind=None
                        if k in ("meta","presupuesto","objetivo") or "meta"==k:kind="target"
                        elif str(year-1)==k:kind="previous"
                        elif str(year)==k:kind="current"
                        if kind:anchors.append((kind,(float(w.get("x0",0))+float(w.get("x1",0)))/2,float(w.get("top",0))))
                    for kind,x,top in anchors:
                        row_anchors=sorted([a for a in anchors if abs(a[2]-top)<=8],key=lambda a:a[1]);xs=[a[1] for a in row_anchors]
                        left=-1e9;right=1e9
                        for xx in xs:
                            if xx<x:left=max(left,(xx+x)/2)
                            elif xx>x:right=min(right,(xx+x)/2)
                        vals=[]
                        for w in words:
                            wt=float(w.get("top",0));wx=(float(w.get("x0",0))+float(w.get("x1",0)))/2
                            if wt<=top+5 or wt>top+170 or not (left<=wx<=right):continue
                            token=str(w.get("text") or "");v=parse_money_token(token)
                            if v>=1000 and not (2020<=v<=2100) and "%" not in token:vals.append((v,wt,token))
                        if vals:
                            nearest=min(v[1] for v in vals);near=[v for v in vals if abs(v[1]-nearest)<=5];value=max(v[0] for v in near)
                            all_candidates[kind].append((55,value,f"P{pno} columna {kind}"))
                for kind,dst in (("target","target_sales"),("previous","previous_sales"),("current","pdf_current_sales")):
                    vals=all_candidates[kind]
                    if vals:
                        best=max(vals,key=lambda x:(x[0],x[1]));result[dst]=float(best[1]);result["diagnostic"]+=(" | " if result["diagnostic"] else "")+f"{kind}:{best[2]}"
        except Exception as exc:
            result["diagnostic"]=f"{type(exc).__name__}: {exc}"
        return result

    previous_parser=getattr(m,"parse_sales_pdf",None)
    if callable(previous_parser):
        def parse_sales_pdf_v166(path,year=None,month=None):
            result=dict(previous_parser(path,year,month) or {});y=int(year or 0);path=Path(path)
            if y>0 and path.exists() and path.suffix.lower()==".pdf":
                cmp=pdf_comparative(path,y);result.update(cmp)
                if num(result.get("total_sales"))<=0 and num(cmp.get("pdf_current_sales"))>=1000:
                    result["total_sales"]=num(cmp["pdf_current_sales"]);result["source_method"]="PDF · venta detectada";result["status"]="Procesado"
            result["parser_version"]=PARSER_VERSION
            return result
        m.parse_sales_pdf=parse_sales_pdf_v166

    for route in list(m.app.router.routes):
        if getattr(route,"path",None)=="/api/commercial-sales-summary" and "GET" in (getattr(route,"methods",set()) or set()):
            try:m.app.router.routes.remove(route)
            except ValueError:pass

    def sales_entries_repaired():
        out=[]
        for raw in list((m.load_manifest() or {}).get("sales") or []):
            item=dict(raw);y=int(item.get("year") or 0);mo=int(item.get("month") or 0)
            if not y or mo not in range(1,13):continue
            path=m.resolve_entry_path(item)
            if not path.exists() or path.suffix.lower()!=".pdf":continue
            if int(item.get("parser_version") or 0)<PARSER_VERSION or (num(item.get("previous_sales"))<=0 and num(item.get("target_sales"))<=0):
                try:
                    parsed=dict(m.parse_sales_pdf(path,y,mo) or {});changes={k:parsed.get(k) for k in ("status","store","rows","stores","pages","total_pieces","total_sales","parser_version","source_line","source_method","target_sales","previous_sales","pdf_current_sales","diagnostic") if k in parsed};m.update_entry("sales",str(item.get("id") or ""),**changes);item.update(changes)
                except Exception as exc:print(f"[V166-SALES] {path.name}: {type(exc).__name__}: {exc}",flush=True)
            out.append(item)
        return out

    @m.app.get("/api/commercial-sales-summary")
    async def sales_summary_v166(request: Request,year: int|None=None,through_month: int|None=None,store: str="Compañía"):
        actor=m.require_user(request);now=datetime.now();yy=int(year or now.year);cut=max(1,min(12,int(through_month or now.month)))
        try:scope=m.effective_store(actor,store)
        except Exception:scope=store
        scope=str(scope or "Compañía").strip() or "Compañía";entries=sales_entries_repaired()
        def scope_match(e):
            st=str(e.get("store") or "Compañía").strip() or "Compañía"
            return scope=="Compañía" or norm(st)==norm(scope) or norm(st)==norm("Compañía")
        current={mo:{"sales":0.0,"pieces":0.0,"sources":0,"last_upload":"","embedded_prev":0.0,"embedded_goal":0.0} for mo in range(1,13)}
        previous={mo:{"sales":0.0,"pieces":0.0,"sources":0} for mo in range(1,13)}
        latest={}
        for e in entries:
            if not scope_match(e):continue
            key=(int(e.get("year") or 0),int(e.get("month") or 0),str(e.get("store") or ""));old=latest.get(key)
            if old is None or str(e.get("uploaded_at") or "")>=str(old.get("uploaded_at") or ""):latest[key]=e
        def entries_for(y,mo):
            vals=[e for (ey,em,_),e in latest.items() if ey==y and em==mo]
            company=[e for e in vals if norm(e.get("store"))==norm("Compañía")]
            return company if company else vals
        for mo in range(1,13):
            vals=entries_for(yy,mo)
            current[mo]["sales"]=sum(num(e.get("total_sales")) for e in vals);current[mo]["pieces"]=sum(num(e.get("total_pieces")) for e in vals);current[mo]["sources"]=sum(1 for e in vals if num(e.get("total_sales"))>0);current[mo]["last_upload"]=max([str(e.get("uploaded_at") or "") for e in vals]+[""])
            current[mo]["embedded_prev"]=sum(num(e.get("previous_sales")) for e in vals);current[mo]["embedded_goal"]=sum(num(e.get("target_sales")) for e in vals)
            prevs=entries_for(yy-1,mo);previous[mo]["sales"]=sum(num(e.get("total_sales")) for e in prevs);previous[mo]["pieces"]=sum(num(e.get("total_pieces")) for e in prevs);previous[mo]["sources"]=sum(1 for e in prevs if num(e.get("total_sales"))>0)
            if previous[mo]["sales"]<=0 and current[mo]["embedded_prev"]>0:previous[mo]["sales"]=current[mo]["embedded_prev"];previous[mo]["sources"]=current[mo]["sources"]
            if current[mo]["sales"]<=0:
                try:
                    from v112_sales_pdf_repair import _capacity_month_fallback
                    cs,cp,_src=_capacity_month_fallback(m,yy,mo,scope)
                    if cs>=1000:current[mo]["sales"]=cs;current[mo]["pieces"]=cp;current[mo]["sources"]=max(1,current[mo]["sources"])
                except Exception:pass
            if previous[mo]["sales"]<=0:
                try:
                    from v112_sales_pdf_repair import _capacity_month_fallback
                    ps,pp,_src=_capacity_month_fallback(m,yy-1,mo,scope)
                    if ps>=1000:previous[mo]["sales"]=ps;previous[mo]["pieces"]=pp;previous[mo]["sources"]=max(1,previous[mo]["sources"])
                except Exception:pass
        with m.db() as con:
            goal_rows=con.execute("SELECT month,target FROM sales_goals WHERE year=? AND store=?",(yy,scope)).fetchall()
        manual={int(r["month"]):num(r["target"]) for r in goal_rows}
        labels=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];months=[]
        for mo in range(1,13):
            goal=manual.get(mo,0.0) or current[mo]["embedded_goal"];cur=current[mo]["sales"];prev=previous[mo]["sales"]
            months.append({"month":mo,"label":labels[mo-1],"target":goal,"current":cur,"previous":prev,"pieces":current[mo]["pieces"],"previous_pieces":previous[mo]["pieces"],"sources":current[mo]["sources"],"compliance":cur/goal*100 if goal else None,"growth":(cur/prev-1)*100 if prev else None})
        goal_ytd=sum(num(x["target"]) for x in months[:cut]);current_ytd=sum(num(x["current"]) for x in months[:cut]);previous_ytd=sum(num(x["previous"]) for x in months[:cut]);source_count=sum(int(current[x]["sources"] or 0) for x in range(1,cut+1));last_upload=max([str(current[x]["last_upload"] or "") for x in range(1,cut+1)]+[""])
        years=sorted({int(e.get("year") or 0) for e in entries if int(e.get("year") or 0)>0}|{yy,yy-1},reverse=True)
        return {"year":yy,"previous_year":yy-1,"through_month":cut,"store":scope,"available_years":years,"months":months,"totals":{"goal_ytd":goal_ytd,"current_ytd":current_ytd,"previous_ytd":previous_ytd,"compliance_pct":current_ytd/goal_ytd*100 if goal_ytd else None,"growth_pct":(current_ytd/previous_ytd-1)*100 if previous_ytd else None,"gap_to_goal":current_ytd-goal_ytd if goal_ytd else None},"has_sales":any(num(x["current"])>0 or num(x["previous"])>0 for x in months[:cut]),"source_count":source_count,"last_upload":last_upload,"editable":str(actor.get("role") or "") in ("superadmin","admin"),"parser_version":PARSER_VERSION,"source_label":"Fuente: PDF mensual · venta/meta/año anterior; capacidades sólo como respaldo del mismo mes"}

    css=r'''<style id="v166-stable-ui-css">
#operativoNav [data-opview="Operación"],#operativoNav [data-opview="Operación Diaria"],#operativoNav [data-opview="Indicadores Diarios"],#operativoNav [data-opview="Reporte Semanal"],#operativoNav [data-opview="Reporte Mensual"],#operativoNav [data-opview="Día"],#operativoNav [data-opview="Semanal"],#operativoNav [data-opview="Mensual"],#operativoNav [data-opview="Matriz de recolección"]{display:none!important}
.v166-tab-icon{display:inline-flex;width:18px;height:18px;flex:0 0 18px;align-items:center;justify-content:center}.v166-tab-icon svg,.v166-kpi-icon svg,.v166-filter-icon svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}.v166-kpi-icon{position:absolute;left:13px;top:16px;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#edf5ff;color:#176fe8;z-index:1}.kpi,.report-kpi,.v149-kpi,.v125-kpi{padding-left:50px!important}.v166-iconized-card:nth-child(4n+2) .v166-kpi-icon{background:#ecfbf4;color:#0ca96b}.v166-iconized-card:nth-child(4n+3) .v166-kpi-icon{background:#f4edff;color:#7135e8}.v166-iconized-card:nth-child(4n) .v166-kpi-icon{background:#fff0f3;color:#ef376c}.v166-filter-icon{position:absolute;left:11px;bottom:11px;width:18px;height:18px;color:#176fe8;display:grid;place-items:center;pointer-events:none}.v161-field{position:relative}.v161-field select,.v161-field input{padding-left:36px!important}
.v166-internal-filter{background:#fff;border:1px solid #d5e1ee;border-radius:14px;padding:10px;margin:8px 0 10px}.v166-internal-grid{display:grid;grid-template-columns:minmax(180px,310px) auto;gap:8px;align-items:end}.v166-internal-filter label{display:block;margin:0 0 5px 2px;color:#60758f;font-size:8px;font-weight:950;text-transform:uppercase}.v166-internal-filter select{width:100%;height:42px;border:1px solid #cad9e9;border-radius:10px;background:#fff;color:#173f78;padding:7px 32px 7px 36px;font-size:10px;font-weight:850}.v166-internal-filter .v166-select-wrap{position:relative}.v166-internal-filter button{height:42px;min-width:126px;border:0;border-radius:10px;background:#176fe8;color:#fff;font-size:9px;font-weight:950;padding:0 18px}.v166-scroll-table{max-height:1500px;overflow:auto!important}.v166-scroll-table .table th{position:sticky;top:0;z-index:4}
#v166RoutesMatrix{margin:0 0 12px}.v166-matrix-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-end;margin:0 0 7px}.v166-matrix-head h3{margin:0;color:#103f7d;font-size:15px}.v166-matrix-head p{margin:3px 0 0;color:#71839a;font-size:8px}.v166-matrix-table{min-width:1000px}.v166-matrix-table td{text-align:center;min-width:115px}.v166-matrix-cell{display:grid;gap:2px}.v166-matrix-cell b{font-size:10px;color:#103f7d}.v166-matrix-cell small{font-size:6.8px;color:#71839a}.v166-zero{color:#a4b0bf!important;font-weight:500!important}.v166-alert-panel{background:#fff;border:1px solid #d8e4f0;border-radius:13px;padding:11px;margin:10px 0}.v166-alert-row{display:grid;grid-template-columns:1fr 140px 140px;gap:8px;padding:8px;border-bottom:1px solid #e7edf5;font-size:8.5px}.v166-alert-row:last-child{border-bottom:0}.v166-alert-badge{display:inline-flex;align-items:center;gap:5px;color:#b42318;font-weight:900}.v166-alert-badge:before{content:"";width:7px;height:7px;border-radius:50%;background:#ef4444}.v166-roster .action-sm{border:1px solid #c8d6e7;background:#fff;color:#103f7d;border-radius:8px;padding:6px 9px;font-size:8px;font-weight:900;cursor:pointer}.v166-roster .action-sm.danger{border-color:#f3b0b0;color:#b42318}.v166-inactive-row td{opacity:.58;background:#f7f8fa!important}body.v166-area-single #areaTables>.area-block{display:none!important}#v166AreaSingleTable{display:block!important}.v166-native-internal-hidden{display:none!important}body[data-v163-module="analysis"] #page-analysis-upload,body[data-v163-module="analysis"] #analysisUploadLog{contain:layout paint}.uploadgrid,.drop,.panel{transform:none!important}.v166-no-transition *{transition:none!important;animation:none!important}@media(max-width:900px){.v166-internal-grid{grid-template-columns:1fr}.v166-internal-filter button{width:100%}.v166-alert-row{grid-template-columns:1fr}.v166-scroll-table{max-height:900px}.v166-matrix-table{min-width:850px}}
</style>'''

    js=r'''<script id="v166-stable-ui-js">
(function(){
if(window.__V166_STABLE_UI)return;window.__V166_STABLE_UI=true;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0}),f1=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:1});
const svg={calendar:'<svg viewBox="0 0 24 24"><path d="M4 5h16v15H4zM8 3v4M16 3v4M4 9h16"/></svg>',store:'<svg viewBox="0 0 24 24"><path d="M4 10h16l-2-5H6zM5 10v9h14v-9M9 19v-5h6v5"/></svg>',grid:'<svg viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/></svg>',list:'<svg viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11M4 6h1M4 12h1M4 18h1"/></svg>',chart:'<svg viewBox="0 0 24 24"><path d="M5 20V11M12 20V4M19 20v-7"/></svg>',money:'<svg viewBox="0 0 24 24"><path d="M12 3v18M16 7c-1-1-2-1.5-4-1.5-2.3 0-4 1.2-4 3s1.5 2.5 4.3 3.1c2.7.6 4.2 1.4 4.2 3.4 0 2.1-1.9 3.5-4.5 3.5-2 0-3.7-.7-4.8-2"/></svg>',pin:'<svg viewBox="0 0 24 24"><path d="M12 21s7-6.1 7-12a7 7 0 10-14 0c0 5.9 7 12 7 12z"/><circle cx="12" cy="9" r="2"/></svg>',table:'<svg viewBox="0 0 24 24"><path d="M4 5h16v14H4zM4 10h16M9 5v14M15 5v14"/></svg>',box:'<svg viewBox="0 0 24 24"><path d="M4 7l8-4 8 4-8 4zM4 7v10l8 4 8-4V7M12 11v10"/></svg>',target:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/></svg>',user:'<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/></svg>',settings:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 00-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0015 6l-.3-2.6H9.3L9 6a8 8 0 00-1.5 1.1l-2.4-1-2 3.4L5.1 11a7 7 0 000 2l-2 1.5 2 3.4 2.4-1A8 8 0 009 18l.3 2.6h5.4L15 18a8 8 0 001.5-1.1l2.4 1 2-3.4-2-1.5a7 7 0 00.1-1z"/></svg>',upload:'<svg viewBox="0 0 24 24"><path d="M12 16V4M7 9l5-5 5 5M5 20h14"/></svg>',search:'<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M16 16l5 5"/></svg>'};
function labelOf(field){return (field?.querySelector('label')?.textContent||'').trim().toLowerCase()}function filterField(label){const want=String(label).trim().toLowerCase();return $$('#v161FilterGrid .v161-field').find(x=>labelOf(x)===want)}function filterControl(label){return filterField(label)?.querySelector('select,input')||null}function setOptions(el,items,value){if(!el)return;const sig=items.map(x=>Array.isArray(x)?x.join('|'):String(x)).join('¦');if(el.dataset.v166sig!==sig){el.innerHTML='';items.forEach(x=>{const pair=Array.isArray(x)?x:[x,x];el.add(new Option(pair[1],pair[0]))});el.dataset.v166sig=sig}if([...el.options].some(o=>o.value===value))el.value=value;else if(el.options.length&&!el.value)el.selectedIndex=el.options.length-1}
function moduleName(){let main='';try{main=String(window.MAIN||'').toLowerCase()}catch(_){ }if(main==='analysis')return'analysis';if(main==='operation')return'operation';if(main==='operativo')return'operativo';const txt=$('.nav.active')?.textContent?.toLowerCase()||'';if(txt.includes('análisis comercial'))return'analysis';if(txt.trim().startsWith('operación'))return'operation';if(txt.includes('cambios y muertos'))return'operativo';return''}
function sourceIcon(label){const x=String(label||'').toLowerCase();if(x.includes('tienda'))return svg.store;if(x.includes('área')||x.includes('sección'))return svg.grid;if(x.includes('actividad')||x.includes('catálogo')||x.includes('estatus'))return svg.list;return svg.calendar}function decorateFilterIcons(){$$('#v161FilterGrid .v161-field').forEach(w=>{let i=w.querySelector(':scope>.v166-filter-icon');if(!i){i=document.createElement('span');i.className='v166-filter-icon';w.append(i)}const code=sourceIcon(w.querySelector('label')?.textContent);if(i.innerHTML!==code)i.innerHTML=code});const b=$('#v161FilterGrid .v161-apply');if(b&&!b.dataset.v166){b.dataset.v166='1';b.innerHTML=`<span style="display:inline-flex;width:17px">${svg.search}</span> Consultar`}}
window.V166_VIEW_TYPE=window.V166_VIEW_TYPE||'';function yearsFrom(meta){const out=new Set();[...(meta?.available_dates||[]),...(meta?.available_months||[]),...(meta?.available_weeks||[])].forEach(x=>{const m=String(x).match(/^(\d{4})/);if(m)out.add(m[1])});return [...out].sort()}function periodList(meta,type){if(type==='day')return meta?.available_dates||[];if(type==='week')return meta?.available_weeks||[];if(type==='month')return meta?.available_months||[];if(type==='year')return yearsFrom(meta);return[]}function periodLabel(type){return type==='day'?'Fecha':type==='week'?'Semana ISO':type==='month'?'Mes':'Año'}function currentMeta(){return window.OPSDATA&&typeof window.OPSDATA==='object'?window.OPSDATA:null}
async function ensureOperationalFilter(){if(moduleName()!=='operativo')return;let meta=currentMeta();if(!meta){try{meta=await api('/api/operations/meta',{timeoutMs:30000});window.OPSDATA=meta}catch(_){return}}const mode=$('#operPeriodMode'),period=$('#operPeriodSelect');let type=window.V166_VIEW_TYPE||window.OPER_PERIOD?.type||mode?.value||'month';if(!['day','week','month','year'].includes(type))type='month';window.V166_VIEW_TYPE=type;if(window.OPER_PERIOD)window.OPER_PERIOD.type=type;const opts=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];setOptions(mode,opts,type);const list=periodList(meta,type);let value=window.OPER_PERIOD?.value||period?.value||'';if(!list.includes(value))value=list.at(-1)||'';setOptions(period,list,value);if(period)period.value=value;if(window.OPER_PERIOD)window.OPER_PERIOD.value=value;const fmode=filterControl('Vista'),fp=filterControl('Periodo');setOptions(fmode,opts,type);if(fmode)fmode.value=type;setOptions(fp,list,value);if(fp)fp.value=value;const pl=filterField('Periodo')?.querySelector('label');if(pl)pl.textContent=periodLabel(type)}
function bindFacadePeriod(){const fm=filterControl('Vista');if(fm&&!fm.dataset.v166bind){fm.dataset.v166bind='1';fm.addEventListener('change',async()=>{window.V166_VIEW_TYPE=fm.value;if(window.OPER_PERIOD){window.OPER_PERIOD.type=fm.value;window.OPER_PERIOD.value=''}const real=$('#operPeriodMode');if(real){setOptions(real,[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']],fm.value);real.value=fm.value;real.dispatchEvent(new Event('change',{bubbles:true}))}await ensureOperationalFilter();schedule()})}const fp=filterControl('Periodo');if(fp&&!fp.dataset.v166bind){fp.dataset.v166bind='1';fp.addEventListener('change',()=>{const real=$('#operPeriodSelect');if(real){real.value=fp.value;real.dispatchEvent(new Event('change',{bubbles:true}))}if(window.OPER_PERIOD)window.OPER_PERIOD.value=fp.value})}}
if(typeof window.currentPeriodTypeForView==='function')window.currentPeriodTypeForView=function(name){if(name==='Carga de datos')return'all';return window.V166_VIEW_TYPE||window.OPER_PERIOD?.type||'month'};if(typeof window.fixedPeriodTypeForView==='function')window.fixedPeriodTypeForView=function(name){return name==='Carga de datos'?'all':'period'};if(typeof window.setPeriodSelector==='function')window.setPeriodSelector=function(name,d){const bar=$('#operativoPeriodBar'),sel=$('#operPeriodSelect'),lab=$('#operPeriodLabel'),mode=$('#operPeriodMode'),mw=$('#operPeriodModeWrap');if(name==='Carga de datos'){bar?.classList.add('hidden');return}bar?.classList.remove('hidden');mw?.classList.remove('hidden');let t=window.V166_VIEW_TYPE||window.OPER_PERIOD?.type||'month';if(!['day','week','month','year'].includes(t))t='month';window.V166_VIEW_TYPE=t;setOptions(mode,[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']],t);const list=periodList(d,t),cur=(window.OPER_PERIOD?.value&&list.includes(window.OPER_PERIOD.value))?window.OPER_PERIOD.value:(list.at(-1)||'');setOptions(sel,list,cur);if(window.OPER_PERIOD){window.OPER_PERIOD.type=t;window.OPER_PERIOD.value=cur}if(lab)lab.textContent=periodLabel(t)};
if(!window.__V166_FETCH_WRAP){window.__V166_FETCH_WRAP=true;const ofetch=window.fetch.bind(window);window.fetch=function(input,init){try{let raw=typeof input==='string'?input:input?.url;if(raw&&(/\/api\/operations(?:\?|$)/.test(raw)||/\/api\/export\/operations(?:\?|$)/.test(raw))){const u=new URL(raw,location.origin);if(u.searchParams.get('period_type')==='year'){const y=u.searchParams.get('period_value');if(/^\d{4}$/.test(y||'')){u.searchParams.set('period_type','all');u.searchParams.set('period_value','');u.searchParams.set('start_date',`${y}-01-01`);u.searchParams.set('end_date',`${y}-12-31`);raw=u.pathname+u.search;if(typeof input==='string')input=raw;else input=new Request(raw,input)}}}if(raw&&raw.includes('/api/commercial')&&!raw.includes('status-options-v166')){const st=$('#v166StatusSelect')?.value||'Todos';if(st&&st!=='Todos'){const u=new URL(typeof input==='string'?input:input.url,location.origin);u.searchParams.set('status',st);const nr=u.pathname+u.search;if(typeof input==='string')input=nr;else input=new Request(nr,input)}}}catch(_){ }return ofetch(input,init)}}
async function ensureCommercialFilter(){if(moduleName()!=='analysis')return;const grid=$('#v161FilterGrid');if(!grid)return;const period=filterControl('Periodo'),src=$('#week');if(period&&src&&src.options.length){const items=[...src.options].map(o=>[o.value,o.text]);setOptions(period,items,src.value);period.value=src.value}if(!$('#v166StatusField')){const wrap=document.createElement('div');wrap.className='v161-field';wrap.id='v166StatusField';wrap.innerHTML='<label>Estatus</label><select id="v166StatusSelect"><option>Todos</option></select><span class="v166-filter-icon">'+svg.list+'</span>';const apply=grid.querySelector('.v161-apply');grid.insertBefore(wrap,apply)}const ss=$('#v166StatusSelect');if((ss&&!ss.dataset.loadedFor)||ss?.dataset.loadedFor!==String(src?.value||'')){try{const d=await api('/api/commercial/status-options-v166?week='+encodeURIComponent(src?.value||''),{timeoutMs:60000});const cur=ss.value||'Todos';setOptions(ss,[['Todos','Todos'],...(d.values||[]).map(x=>[x,x])],cur);ss.dataset.loadedFor=String(src?.value||'')}catch(_){}}if(ss&&!ss.dataset.v166bind){ss.dataset.v166bind='1';ss.addEventListener('change',()=>{const b=$('#refresh');if(b)b.click();else if(window.loadDash)window.loadDash()})}}
function tabIcon(text){const x=String(text||'').toLowerCase();if(x.includes('recorrido'))return svg.pin;if(x.includes('productiv')||x.includes('convers'))return svg.chart;if(x.includes('recuper'))return svg.money;if(x.includes('carga'))return svg.upload;if(x.includes('meta')||x.includes('estándar')||x.includes('score'))return svg.target;if(x.includes('ubicación')||x.includes('sección')||x.includes('macro'))return svg.grid;if(x.includes('tienda'))return svg.store;return svg.table}function decorateTabs(){['#operativoNav','#analysisNav','.v125-tabs'].forEach(sel=>$$(sel+' button,'+sel+' .switch,'+sel+' .v125-tab').forEach(b=>{const text=(b.textContent||'').replace(/\s+/g,' ').trim();if(!text)return;b.querySelectorAll('.v164-tab-icon,.v166-tab-icon').forEach(x=>x.remove());const s=document.createElement('span');s.className='v166-tab-icon';s.innerHTML=tabIcon(text);b.prepend(s)}))}function cardLabel(card){return (card.querySelector('.lab,.rk-label,small')?.textContent||'').trim()}function decorateCards(){$$('.kpi,.report-kpi,.v149-kpi,.v125-kpi').forEach(c=>{c.querySelectorAll('.v164-kpi-icon,.v166-kpi-icon').forEach((x,i)=>{if(i>0)x.remove()});let icon=c.querySelector('.v166-kpi-icon,.v164-kpi-icon');if(!icon){icon=document.createElement('span');icon.className='v166-kpi-icon';c.prepend(icon)}else{icon.classList.add('v166-kpi-icon');icon.classList.remove('v164-kpi-icon')}const l=cardLabel(c).toLowerCase();const code=l.includes('$')||l.includes('venta')||l.includes('recuperación')?svg.money:l.includes('colaborador')?svg.user:l.includes('meta')||l.includes('cumpl')?svg.target:l.includes('tienda')?svg.store:l.includes('mercanc')||l.includes('pieza')||l.includes('existencia')||l.includes('capacidad')?svg.box:svg.chart;if(icon.innerHTML!==code)icon.innerHTML=code;c.classList.add('v166-iconized-card')})}
async function injectMissingProductivity(name){if(!String(name||'').toLowerCase().includes('productividad'))return;const cont=$('#operativoDynamicContent');if(!cont)return;let box=$('#v166MissingProductivity');if(!box){box=document.createElement('div');box.id='v166MissingProductivity';box.className='v166-alert-panel';const actions=cont.querySelector('.report-actions');if(actions)cont.insertBefore(box,actions);else cont.append(box)}const q=new URLSearchParams({period_type:window.V166_VIEW_TYPE||window.OPER_PERIOD?.type||'month',period_value:window.OPER_PERIOD?.value||$('#operPeriodSelect')?.value||'',store:$('#operStoreSelect')?.value||'Compañía'});try{const d=await api('/api/operations/missing-productivity-v166?'+q,{timeoutMs:60000});box.innerHTML=`<div style="display:flex;justify-content:space-between;gap:10px;align-items:center"><div><b style="font-size:13px;color:#103f7d">Alertas · colaboradores sin productividad</b><div style="font-size:8px;color:#71839a;margin-top:3px">Colaboradores activos que ya registraron productividad anteriormente y no tienen registro en el periodo.</div></div><span class="v166-alert-badge">${nf(d.count)} sin registro</span></div>${d.rows?.length?d.rows.map(r=>`<div class="v166-alert-row"><b>${esc(r.name)}</b><span>${esc(r.store)}</span><span>Último: ${esc(r.last_date||'Sin fecha')}</span></div>`).join(''):'<div class="infoempty" style="margin-top:9px">Todos los colaboradores activos tienen productividad registrada para el periodo.</div>'}`}catch(e){box.innerHTML='<div class="infoempty">No fue posible consultar alertas: '+esc(e.message||e)+'</div>'}}
async function injectRoster(name){if(!String(name||'').toLowerCase().includes('metas y tiendas'))return;const cont=$('#operativoDynamicContent');if(!cont)return;let box=$('#v166Roster');if(!box){box=document.createElement('div');box.id='v166Roster';box.className='panel v166-roster';cont.append(box)}const store=$('#operStoreSelect')?.value||'Compañía';try{const d=await api('/api/operations/collaborators-v166?store='+encodeURIComponent(store)+'&include_inactive=true',{timeoutMs:60000});box.innerHTML=`<div class="title" style="margin-top:0!important">Colaboradores de productividad</div><div class="subtitle">La baja excluye al colaborador de las alertas de productividad; su histórico se conserva.</div><div class="tablewrap v166-scroll-table"><table class="table"><thead><tr><th>Colaborador</th><th>Tienda</th><th>Primera actividad</th><th>Última actividad</th><th>Estatus</th><th>Acción</th></tr></thead><tbody>${(d.rows||[]).map(r=>`<tr class="${r.active?'':'v166-inactive-row'}"><td><b>${esc(r.name)}</b></td><td>${esc(r.store)}</td><td>${esc(r.first_seen||'')}</td><td>${esc(r.last_seen||'')}</td><td>${r.active?'<span class="status ok">Activo</span>':'<span class="status bad">Baja</span>'}</td><td>${d.editable?`<button class="action-sm ${r.active?'danger':''}" data-v166-person="${esc(r.name)}" data-v166-store="${esc(r.store)}" data-v166-active="${r.active?'0':'1'}">${r.active?'Dar de baja':'Reactivar'}</button>`:'—'}</td></tr>`).join('')||'<tr><td colspan="6">Aún no hay colaboradores históricos.</td></tr>'}</tbody></table></div>`;box.querySelectorAll('[data-v166-person]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/api/operations/collaborators-v166/status',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:b.dataset.v166Person,store:b.dataset.v166Store,active:b.dataset.v166Active==='1'})});await injectRoster(name)}catch(e){alert(e.message||e)}finally{b.disabled=false}})}catch(e){box.innerHTML='<div class="infoempty">No fue posible consultar colaboradores: '+esc(e.message||e)+'</div>'}}
async function injectRoutesMatrix(name){if(!String(name||'').toLowerCase().includes('recorridos'))return;const cont=$('#operativoDynamicContent');if(!cont)return;let root=$('#v166RoutesMatrix');if(!root){root=document.createElement('div');root.id='v166RoutesMatrix';cont.prepend(root)}const q=new URLSearchParams({period_type:window.V166_VIEW_TYPE||window.OPER_PERIOD?.type||'week',period_value:window.OPER_PERIOD?.value||$('#operPeriodSelect')?.value||'',store:$('#operStoreSelect')?.value||'Compañía',area:$('#operAreaSelect')?.value||'Todas',activity:$('#operActivitySelect')?.value||'Todas'});root.innerHTML='<div class="panel"><div class="infoempty">Cargando matriz de recolección…</div></div>';try{const d=await api('/api/operations/collection-hour-matrix-v166?'+q,{timeoutMs:120000});const body=(d.hours||[]).map(r=>`<tr><td><b>${esc(r.label)}</b></td>${(r.cells||[]).map(c=>`<td><div class="v166-matrix-cell"><b class="${Number(c.total||0)===0?'v166-zero':''}">${nf(c.total)}</b>${Number(c.total||0)>0?`<small>M ${nf(c.muertos)} · C ${nf(c.cajas)} · P ${nf(c.probador)}</small>`:'<small>—</small>'}</div></td>`).join('')}<td><b>${nf(r.total)}</b></td></tr>`).join('');root.innerHTML=`<div class="panel"><div class="v166-matrix-head"><div><h3>Matriz de recolección · día y hora</h3><p>Lunes a domingo · horas completas desde el primer hasta el último horario registrado.</p></div><b style="color:#103f7d">${nf(d.summary?.pieces)} pzas</b></div><div class="tablewrap"><table class="table v166-matrix-table"><thead><tr><th>Hora</th>${(d.days||[]).map(x=>`<th>${esc(x)}</th>`).join('')}<th>Total</th></tr></thead><tbody>${body||`<tr><td colspan="9">Sin recolecciones para los filtros seleccionados.</td></tr>`}</tbody></table></div></div>`}catch(e){root.innerHTML='<div class="panel"><div class="infoempty">No fue posible cargar la matriz: '+esc(e.message||e)+'</div></div>'}}
async function originSummaryAfterNative(name){if(name!=='Operación'||String(window.V149_OPERATION_TAB||'summary')!=='summary')return;const cont=$('#operativoDynamicContent');if(!cont)return;const tabs=cont.querySelector('.v125-tabs');if(!tabs)return;const q=new URLSearchParams({period_type:window.OPER_PERIOD?.type||'day',period_value:window.OPER_PERIOD?.value||$('#operPeriodSelect')?.value||'',store:$('#operStoreSelect')?.value||'Compañía'});let d;try{d=await api('/api/operation/origin-summary-v166?'+q,{timeoutMs:120000})}catch(e){return}[...cont.children].forEach(x=>{if(x!==tabs)x.remove()});const s=d.summary||{},cards=[['Llegada Origen',s.arrival_origin,'Colgado + Doblado','#246fe5'],['Productividad registrada',s.processed,'Piezas procesadas de Origen','#7338ef'],['Mercancía liberada',s.released,'Sólo mercancía de Origen','#ec007c'],['Pendiente',s.pending,'Origen por procesar','#ef3434'],['Eficiencia',f1(s.efficiency_pct)+'%','Procesadas / carga Origen','#10b981'],['Prod. promedio',f1(s.productivity_avg),'Pzas / colaborador / día','#f3a300'],['Cumplimiento',f1(s.compliance_pct)+'%','Vs estándar Origen','#10b981'],['Colaboradores',s.collaborators,'Con productividad Origen','#173f78'],['Colaboradores necesarios',s.required,'Para pendiente actual','#0f766e']];const html=`<div class="v149-kpis">${cards.map(x=>`<div class="v149-kpi" style="--k:${x[3]}"><small>${x[0]}</small><b>${typeof x[1]==='string'?x[1]:nf(x[1])}</b><span>${x[2]}</span></div>`).join('')}</div><div class="v149-panel"><h3>Alertas operativas · Origen</h3>${(d.alerts||[]).map(a=>`<div class="v149-alert ${a.level||'warn'}">${esc(a.text)}</div>`).join('')}</div><div class="v149-panel"><h3>Desempeño por tienda · Origen</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Llegada</th><th>Procesadas</th><th>Liberadas</th><th>Pendiente</th><th>Necesarios</th><th>Cumplimiento</th></tr></thead><tbody>${(d.stores||[]).map(r=>`<tr><td><b>${esc(r.store)}</b></td><td>${nf(r.arrival)}</td><td>${nf(r.processed)}</td><td>${nf(r.released)}</td><td>${nf(r.pending)}</td><td>${nf(r.required)}</td><td>${f1(r.compliance_pct)}%</td></tr>`).join('')||'<tr><td colspan="7">Sin información de Origen.</td></tr>'}</tbody></table></div></div><div class="v149-panel"><h3>Top 5 colaboradores · Origen</h3><div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Colaborador</th><th>Tienda</th><th>Piezas</th><th>Prod. diaria</th><th>Cumplimiento</th></tr></thead><tbody>${(d.top||[]).map((r,i)=>`<tr><td>#${i+1}</td><td><b>${esc(r.name)}</b></td><td>${esc(r.store)}</td><td>${nf(r.pieces)}</td><td>${nf(r.daily)}</td><td>${f1(r.compliance_pct)}%</td></tr>`).join('')||'<tr><td colspan="6">Sin productividad de Origen registrada.</td></tr>'}</tbody></table></div></div>`;tabs.insertAdjacentHTML('afterend',html);decorateCards()}
function internalFilter(id,label,options,value,onChange){let root=$('#'+id);if(root){const s=root.querySelector('select');setOptions(s,options,value);s.value=value;return root}root=document.createElement('div');root.id=id;root.className='v166-internal-filter';root.innerHTML=`<div class="v166-internal-grid"><div class="v166-select-wrap"><label>${esc(label)}</label><select></select><span class="v166-filter-icon">${svg.list}</span></div><button type="button"><span style="display:inline-flex;width:15px">${svg.search}</span> Consultar</button></div>`;const s=root.querySelector('select');setOptions(s,options,value);s.value=value;root.querySelector('button').onclick=()=>onChange(s.value);s.onchange=()=>onChange(s.value);return root}
window.V166_AREA_GROUP=window.V166_AREA_GROUP||'General';async function renderSingleAreaTable(){if(moduleName()!=='analysis')return;const active=$('#analysisNav .active')?.dataset.sub||'';if(active!=='areas'&&window.SUB!=='areas')return;const host=$('#areaTables');if(!host)return;const filter=internalFilter('v166AreaFilter','Área',[['General','General'],['Colgado','Colgado'],['Doblado','Doblado'],['Jeans','Jeans'],['Lencería','Lencería']],window.V166_AREA_GROUP,v=>{window.V166_AREA_GROUP=v;renderSingleAreaTable()});if(!filter.isConnected)host.before(filter);let table=$('#v166AreaSingleTable');if(!table){table=document.createElement('div');table.id='v166AreaSingleTable';host.before(table)}document.body.classList.add('v166-area-single');const store=$('#store')?.value||'Compañía',section=$('#section')?.value||'Todas',week=$('#week')?.value||'',catalog=$('#catalog')?.value||'Todos';try{const d=await api(`/api/commercial-detail?week=${encodeURIComponent(week)}&store=${encodeURIComponent(store)}&section=${encodeURIComponent(section)}&catalog=${encodeURIComponent(catalog)}`,{timeoutMs:120000});let rows=d.locations||[];if(window.V166_AREA_GROUP!=='General')rows=rows.filter(x=>x.group===window.V166_AREA_GROUP);rows=[...rows].sort((a,b)=>Number(b.suggested||0)-Number(a.suggested||0));const company=store==='Compañía';table.innerHTML=`<div class="title">${esc(window.V166_AREA_GROUP)} · ${esc(store)} · Sugerido mayor a menor</div><div class="tablewrap v166-scroll-table"><table class="table"><thead><tr>${company?'<th>Tienda</th>':''}<th>Ubicación</th><th>Pasillo / Mesa</th><th>Modelos</th><th>Curva</th><th>Piso</th><th>Bodega</th><th>Existencia</th><th>Sugerido 7</th><th>DDI 7</th><th>Vta pzas</th><th>Venta $</th><th>% Ocupación</th></tr></thead><tbody>${rows.map(r=>`<tr>${company?`<td><b>${esc(r.store)}</b></td>`:''}<td><b>${esc(r.group)}</b></td><td><b>${esc(r.location)}</b></td><td>${nf(r.ids)}</td><td>${nf(r.capacity)}</td><td>${nf(r.floor)}</td><td>${nf(r.warehouse)}</td><td>${nf(r.existence)}</td><td>${Number(r.suggested||0).toLocaleString('es-MX',{maximumFractionDigits:2})}</td><td>${nf(r.ddi)}</td><td>${nf(r.sales_pzas)}</td><td>$${nf(r.sales_value)}</td><td>${r.occupancy==null?'N/D':f1(r.occupancy)+'%'}</td></tr>`).join('')||`<tr><td colspan="13">Sin información para ${esc(window.V166_AREA_GROUP)}.</td></tr>`}</tbody></table></div>`}catch(e){table.innerHTML='<div class="infoempty">No fue posible consultar Ubicación / Área: '+esc(e.message||e)+'</div>'}}
function replaceNativePills(){const sectionBtns=$$('[data-area-section]'),areaBtns=$$('[data-area-group]');if(sectionBtns.length){const anchor=sectionBtns[0].closest('.switches')||sectionBtns[0].parentElement;if(anchor&&!$('#v166MacroSectionFilter')){const opts=sectionBtns.map(b=>[b.dataset.areaSection||b.textContent.trim(),b.textContent.trim()]);let val=sectionBtns.find(b=>b.classList.contains('active'))?.dataset.areaSection||opts[0]?.[0]||'Todas';const f=internalFilter('v166MacroSectionFilter','Sección',opts,val,v=>{sectionBtns.find(b=>(b.dataset.areaSection||'Todas')===v)?.click()});anchor.before(f);anchor.classList.add('v166-native-internal-hidden')}}if(areaBtns.length){const anchor=areaBtns[0].closest('.switches')||areaBtns[0].parentElement;if(anchor&&!$('#v166MacroAreaFilter')){const opts=[['Todas','General'],...areaBtns.filter(b=>(b.dataset.areaGroup||'Todas')!=='Todas').map(b=>[b.dataset.areaGroup,b.textContent.trim()])];let val=areaBtns.find(b=>b.classList.contains('active'))?.dataset.areaGroup||'Todas';const f=internalFilter('v166MacroAreaFilter','Área',opts,val,v=>{areaBtns.find(b=>(b.dataset.areaGroup||'Todas')===v)?.click()});anchor.before(f);anchor.classList.add('v166-native-internal-hidden')}}const pareto=$$('[data-pareto-group]');if(pareto.length){const a=pareto[0].closest('.switches')||pareto[0].parentElement;if(a&&!$('#v166ParetoFilter')){const opts=pareto.map(b=>[b.dataset.paretoGroup||'general',b.textContent.trim()]);const val=pareto.find(b=>b.classList.contains('active'))?.dataset.paretoGroup||opts[0]?.[0];const f=internalFilter('v166ParetoFilter','Desglose 80/20',opts,val,v=>pareto.find(b=>(b.dataset.paretoGroup||'general')===v)?.click());a.before(f);a.classList.add('v166-native-internal-hidden')}}[['champSection','v166ChampionFilter','Sección · Modelos 80/20'],['slowSection','v166SlowFilter','Sección · Modelos lentos'],['zeroSection','v166ZeroFilter','Sección · Sugerido 0 a 1']].forEach(([sid,fid,label])=>{const s=$('#'+sid);if(!s||$('#'+fid))return;const opts=[...s.options].map(o=>[o.value,o.text]);const f=internalFilter(fid,label,opts,s.value||opts[0]?.[0],v=>{s.value=v;s.dispatchEvent(new Event('change',{bubbles:true}))});const parent=s.closest('.switches,.field,.filter')||s.parentElement;parent.before(f);parent.classList.add('v166-native-internal-hidden')});['champTable','slowTable','zeroTable','modelTable','macroAreaTable'].forEach(id=>{const el=$('#'+id);el?.closest('.tablewrap')?.classList.add('v166-scroll-table')})}
function stabilizeUpload(){const active=$('#analysisNav .active')?.dataset.sub||'';document.body.classList.toggle('v166-no-transition',moduleName()==='analysis'&&(active==='analysis-upload'||window.SUB==='analysis-upload'))}async function afterOperational(name){await ensureOperationalFilter();bindFacadePeriod();decorateFilterIcons();decorateTabs();decorateCards();await injectMissingProductivity(name);await injectRoutesMatrix(name);await injectRoster(name);await originSummaryAfterNative(name);decorateCards()}async function afterAnalysis(){await ensureCommercialFilter();decorateFilterIcons();decorateTabs();decorateCards();replaceNativePills();await renderSingleAreaTable();stabilizeUpload()}function schedule(){[60,220,650,1150,1800].forEach(ms=>setTimeout(()=>{ensureOperationalFilter().then(bindFacadePeriod);ensureCommercialFilter();decorateFilterIcons();decorateTabs();decorateCards();replaceNativePills();renderSingleAreaTable();stabilizeUpload()},ms))}
if(typeof window.renderOperativoView==='function'&&!window.renderOperativoView.__v166){const prev=window.renderOperativoView;const wrapped=async function(name,force=false){const out=await prev.apply(this,arguments);await afterOperational(name);return out};wrapped.__v166=true;window.renderOperativoView=wrapped}if(typeof window.loadDash==='function'&&!window.loadDash.__v166){const prev=window.loadDash;const wrapped=async function(){const out=await prev.apply(this,arguments);await afterAnalysis();return out};wrapped.__v166=true;window.loadDash=wrapped}if(typeof window.goSub==='function'&&!window.goSub.__v166){const prev=window.goSub;const wrapped=function(){const out=prev.apply(this,arguments);Promise.resolve(out).then(()=>afterAnalysis());return out};wrapped.__v166=true;window.goSub=wrapped}
document.addEventListener('click',e=>{if(e.target.closest?.('[data-main],[data-sub],[data-opview],#operativoNav,#analysisNav,.v125-tabs,#refresh,#operPeriodApply,.v161-apply'))schedule()},true);document.addEventListener('change',e=>{if(e.target?.matches?.('select,input'))setTimeout(schedule,20)},true);if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();console.info('[V166] UI estable, roster, matriz, Vista 4 modos, Comercial y Ventas instalados.');
})();
</script>'''

    @m.app.middleware("http")
    async def v166_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v166-stable-ui-css" not in html:html=html.replace("</head>",css+"</head>",1)
            if "v166-stable-ui-js" not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V166-STABLE"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V166-HTML] {type(exc).__name__}: {exc}",flush=True);return response

    m._V166_STABILITY_ROSTER_FILTERS=True
    print("[V166] Vista/roster/matriz/Origen/Comercial/Ventas + estabilidad instalados.",flush=True)
