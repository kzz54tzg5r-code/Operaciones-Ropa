"""V199 · Acceso, menú, resumen comercial ligero y productividad Cambios/Muertos."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import threading
import time

import numpy as np
import pandas as pd
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V199_ACCESS_PERF_PRODUCTIVITY", False):
        return

    # ------------------------------------------------------------------
    # Configuración / DB de captura digital de productividad
    # ------------------------------------------------------------------
    m.REPORT_TABS.setdefault("operations.productivity_capture", "Cargar productividad")

    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS cm_productivity_capture(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            store TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            employee_no TEXT DEFAULT '',
            activity TEXT NOT NULL,
            muertos REAL NOT NULL DEFAULT 0,
            cajas REAL NOT NULL DEFAULT 0,
            probador REAL NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            ended_at TEXT DEFAULT '',
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_cm_prod_date_store ON cm_productivity_capture(date,store)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_cm_prod_created_by ON cm_productivity_capture(created_by,status)")

    def _scope_store(actor, requested):
        role=str(actor.get("role") or "")
        assigned=str(actor.get("store") or "").strip()
        if role in ("tienda","colaborador_operativo","colaborador_lenceria"):
            if not assigned:
                raise HTTPException(409,"El usuario no tiene tienda asignada")
            return assigned
        value=str(requested or "").strip()
        if not value or value=="Compañía":
            raise HTTPException(400,"Selecciona una tienda")
        active={m.login_key(x):x for x in m.store_names(True)}
        chosen=active.get(m.login_key(value))
        if not chosen:
            raise HTTPException(400,"Tienda inválida")
        return chosen

    def _dt(value):
        try:
            return datetime.fromisoformat(str(value or ""))
        except Exception:
            return None

    @m.app.get("/api/cm-productivity/meta")
    def cm_productivity_meta(request: Request):
        actor=m.require_user(request)
        return {
            "stores":m.store_names(True),
            "user":{
                "username":str(actor.get("username") or ""),
                "store":str(actor.get("store") or ""),
                "role":str(actor.get("role") or ""),
            },
            "activities":["Recolección","Acondicionado","Ubicado","Clasificado","Recorridos","Otro"],
        }

    @m.app.get("/api/cm-productivity/active")
    def cm_productivity_active(request: Request):
        actor=m.require_user(request)
        with m.db() as con:
            row=con.execute(
                "SELECT * FROM cm_productivity_capture WHERE status='active' AND created_by=? ORDER BY id DESC LIMIT 1",
                (str(actor.get("username") or ""),)
            ).fetchone()
        return {"item":dict(row) if row else None}

    @m.app.post("/api/cm-productivity/start")
    async def cm_productivity_start(request: Request):
        actor=m.require_user(request,("superadmin","admin","tienda","colaborador_operativo"))
        body=await request.json()
        day=str(body.get("date") or datetime.now(MX).date().isoformat())[:10]
        try:
            datetime.strptime(day,"%Y-%m-%d")
        except Exception:
            raise HTTPException(400,"Fecha inválida")
        store=_scope_store(actor,body.get("store"))
        employee_name=str(body.get("employee_name") or actor.get("username") or "").strip()
        employee_no=str(body.get("employee_no") or "").strip()[:40]
        activity=str(body.get("activity") or "").strip()
        if not employee_name:
            raise HTTPException(400,"Escribe el colaborador")
        if not activity:
            raise HTTPException(400,"Selecciona la actividad realizada")
        now=datetime.now(MX).isoformat(timespec="seconds")
        created_by=str(actor.get("username") or "")
        with m.db() as con:
            active=con.execute(
                "SELECT id FROM cm_productivity_capture WHERE status='active' AND created_by=? LIMIT 1",
                (created_by,)
            ).fetchone()
            if active:
                raise HTTPException(409,"Ya tienes un registro en curso. Finalízalo antes de iniciar otro.")
            cur=con.execute(
                """INSERT INTO cm_productivity_capture(
                    date,store,employee_name,employee_no,activity,
                    muertos,cajas,probador,started_at,status,created_by,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,'active',?,?)""",
                (day,store,employee_name,employee_no,activity,0,0,0,now,created_by,now)
            )
            rid=int(cur.lastrowid)
        return {"ok":True,"id":rid,"started_at":now,"message":"Tiempo iniciado"}

    @m.app.post("/api/cm-productivity/{record_id}/finish")
    async def cm_productivity_finish(record_id: int, request: Request):
        actor=m.require_user(request,("superadmin","admin","tienda","colaborador_operativo"))
        body=await request.json()
        def qty(name):
            try:return max(float(body.get(name) or 0),0)
            except Exception:raise HTTPException(400,f"{name.title()} debe ser un número válido")
        muertos,cajas,probador=qty("muertos"),qty("cajas"),qty("probador")
        now_dt=datetime.now(MX); now=now_dt.isoformat(timespec="seconds")
        with m.db() as con:
            row=con.execute("SELECT * FROM cm_productivity_capture WHERE id=?",(record_id,)).fetchone()
            if not row:
                raise HTTPException(404,"Registro no encontrado")
            role=str(actor.get("role") or "")
            if role not in ("superadmin","admin") and str(row["created_by"] or "")!=str(actor.get("username") or ""):
                raise HTTPException(403,"No puedes finalizar este registro")
            if str(row["status"] or "")!="active":
                raise HTTPException(409,"El registro ya fue finalizado")
            start=_dt(row["started_at"])
            duration=max(int((now_dt-start).total_seconds()),0) if start else 0
            con.execute(
                """UPDATE cm_productivity_capture SET
                   muertos=?,cajas=?,probador=?,ended_at=?,duration_seconds=?,
                   status='finished',updated_at=? WHERE id=?""",
                (muertos,cajas,probador,now,duration,now,record_id)
            )
        return {
            "ok":True,"message":"Tiempo finalizado y productividad guardada",
            "pieces":muertos+cajas+probador,"duration_seconds":duration
        }

    @m.app.get("/api/cm-productivity/history")
    def cm_productivity_history(request: Request, date: str="", store: str=""):
        actor=m.require_user(request)
        day=str(date or datetime.now(MX).date().isoformat())[:10]
        role=str(actor.get("role") or "")
        params=[day]; where=["date=?"]
        if role in ("tienda","colaborador_operativo","colaborador_lenceria"):
            scoped=str(actor.get("store") or "")
            where.append("store=?");params.append(scoped)
        elif store and store!="Compañía":
            where.append("store=?");params.append(store)
        if role=="colaborador_operativo":
            where.append("created_by=?");params.append(str(actor.get("username") or ""))
        with m.db() as con:
            rows=con.execute(
                "SELECT * FROM cm_productivity_capture WHERE "+" AND ".join(where)+" ORDER BY id DESC LIMIT 60",
                tuple(params)
            ).fetchall()
        return {"items":[dict(x) for x in rows]}

    def _period_bounds(period_type, period_value):
        today=datetime.now(MX).date()
        typ=str(period_type or "day"); value=str(period_value or "")
        try:
            if typ=="day" and value:
                d=datetime.strptime(value[:10],"%Y-%m-%d").date();return d,d
            if typ=="month" and re.fullmatch(r"\d{4}-\d{2}",value):
                first=datetime.strptime(value+"-01","%Y-%m-%d").date()
                nxt=(first.replace(day=28)+timedelta(days=4)).replace(day=1)
                return first,nxt-timedelta(days=1)
            if typ=="week" and re.fullmatch(r"\d{4}-W\d{2}",value):
                y,w=value.split("-W");start=datetime.fromisocalendar(int(y),int(w),1).date()
                return start,start+timedelta(days=6)
        except Exception:
            pass
        return today,today

    @m.app.get("/api/cm-productivity/report")
    def cm_productivity_report(
        request: Request, period_type: str="day", period_value: str="",
        store: str="Compañía",
    ):
        actor=m.require_user(request)
        start,end=_period_bounds(period_type,period_value)
        scoped=m.effective_store(actor,store)
        params=[start.isoformat(),end.isoformat()]
        where=["status='finished'","date>=?","date<=?"]
        if scoped and scoped!="Compañía":
            where.append("store=?");params.append(scoped)
        with m.db() as con:
            rows=con.execute(
                "SELECT * FROM cm_productivity_capture WHERE "+" AND ".join(where)+" ORDER BY date,id",
                tuple(params)
            ).fetchall()
        items=[dict(x) for x in rows]
        if not items:
            return {"use_digital":False,"items":[],"productivity":[]}

        goals=m.get_goals()
        target_daily=float(goals.get("productividad_diaria",784) or 784)
        people={}
        for r in items:
            key=(str(r.get("employee_name") or ""),str(r.get("store") or ""))
            p=people.setdefault(key,{
                "name":key[0],"store":key[1],"employee_no":str(r.get("employee_no") or ""),
                "muertos":0.0,"cajas":0.0,"probador":0.0,"pieces":0.0,
                "days":set(),"duration_seconds":0,"activities":set(),
            })
            for k in ("muertos","cajas","probador"):
                p[k]+=float(r.get(k) or 0)
            p["pieces"]+=float(r.get("muertos") or 0)+float(r.get("cajas") or 0)+float(r.get("probador") or 0)
            p["days"].add(str(r.get("date") or ""))
            p["duration_seconds"]+=int(r.get("duration_seconds") or 0)
            if r.get("activity"):p["activities"].add(str(r.get("activity")))
        out=[]
        for p in people.values():
            days=max(len(p["days"]),1); target=target_daily*days
            out.append({
                "name":p["name"],"store":p["store"],"employee_no":p["employee_no"],
                "muertos":p["muertos"],"cajas":p["cajas"],"probador":p["probador"],
                "pieces":p["pieces"],"days":days,"duration_seconds":p["duration_seconds"],
                "daily":p["pieces"]/days if days else 0,
                "target":target,"pct":p["pieces"]/target*100 if target else 0,
                "missing":max(target-p["pieces"],0),
                "activities":sorted(p["activities"]),
            })
        out.sort(key=lambda x:(-x["pct"],-x["pieces"],x["name"]))
        return {
            "use_digital":True,
            "source":"Captura digital Cambios y Muertos",
            "start":start.isoformat(),"end":end.isoformat(),
            "items":items,"productivity":out,
        }

    # ------------------------------------------------------------------
    # Resumen comercial ligero: una sola pasada, sin construir miles de
    # etiquetas ni recurrencias. Evita los 3 requests pesados/502.
    # ------------------------------------------------------------------
    summary_cache={}
    summary_lock=threading.RLock()
    offer_keys={
        m.login_key("Oferta"),m.login_key("Gran remate (por descontinuar)"),
        m.login_key("Oferta(por descontinuar)"),m.login_key("Outlet"),
        m.login_key("Outlet(por descontinuar)"),
    }
    areas=("Colgado","Doblado","Jeans","Lencería","Oferta")

    def _commercial_summary_payload(week,selected,section,catalog):
        try:
            entry=m._capacity_source_entry(week) or {}
            source_id=str(entry.get("id") or entry.get("uploaded_at") or "latest")
        except Exception:
            entry={};source_id="latest"
        key=(source_id,str(week),m.login_key(selected),m.login_key(section),m.login_key(catalog))
        now=time.monotonic()
        with summary_lock:
            hit=summary_cache.get(key)
            if hit and now-hit[0]<600:return hit[1]

        frame=m._capacity_frame_for_period(week)
        work=m._capacity_scope_v45(frame,selected,section,catalog,add_area=True)
        if work is None or work.empty or "ID_ART" not in work.columns:
            empty=[{"area":a,"models":0,"sales_pzas":0,"sales_value":0,"existence":0,"cedis":0,"suggested":0,"ddi":0,"capacity":0,"occupancy":None} for a in areas]
            return {"summaries":{"80_20":empty,"slow":empty,"suggested_zero":empty}}

        ids=work["ID_ART"].fillna("").astype(str).str.strip()
        valid=~ids.isin(["","nan","None"])
        w=work.loc[valid].copy()
        w["__id"]=ids.loc[valid]
        if w.empty:
            return {"summaries":{}}

        store_series=w.get("Tienda",pd.Series("",index=w.index)).fillna("").astype(str).map(m._canonical_capacity_store_key)
        nums=pd.DataFrame({"__id":w["__id"],"__store":store_series},index=w.index)
        srcs={
            "existence":"Existencia","suggested":"VPD","capacity":"Capacidad",
            "sales_pzas_7":"Venta pzas 7","sales_pzas_month":"Venta pzas",
            "sales_pzas_30":"Venta pzas 30","sales_value_7":"Venta $ 7","sales_value_month":"Venta $ mes",
        }
        for dest,src in srcs.items():
            nums[dest]=pd.to_numeric(w[src],errors="coerce").fillna(0.0) if src in w.columns else 0.0
        cols=list(srcs)
        per_store=nums.groupby(["__store","__id"],sort=False,observed=True)[cols].max()
        model=per_store.groupby(level="__id",sort=False).sum(numeric_only=True)

        if "Existencia CEDIS" in w.columns:
            cedis=pd.to_numeric(w["Existencia CEDIS"],errors="coerce").fillna(0).groupby(w["__id"]).max()
            model=model.join(cedis.rename("cedis"),how="left")
        else:model["cedis"]=0.0
        model["cedis"]=pd.to_numeric(model["cedis"],errors="coerce").fillna(0)

        if "DDI" in w.columns:
            dt=pd.DataFrame({
                "__store":store_series,"__id":w["__id"],
                "ddi":pd.to_numeric(w["DDI"],errors="coerce").replace([np.inf,-np.inf],np.nan),
                "suggested":pd.to_numeric(w.get("VPD",0),errors="coerce").fillna(0),
            })
            ds=dt.groupby(["__store","__id"],sort=False,observed=True).agg({"ddi":"max","suggested":"max"}).reset_index()
            weighted=(ds["ddi"].fillna(0)*ds["suggested"]).groupby(ds["__id"]).sum()
            weights=ds["suggested"].groupby(ds["__id"]).sum().replace(0,np.nan)
            fallback=ds.groupby("__id",sort=False)["ddi"].mean()
            model=model.join((weighted/weights).fillna(fallback).rename("ddi"),how="left")
        else:model["ddi"]=0.0
        model["ddi"]=pd.to_numeric(model["ddi"],errors="coerce").fillna(0)

        if "Última entrada CEDIS a tienda" in w.columns:
            last=pd.to_datetime(w["Última entrada CEDIS a tienda"],errors="coerce").groupby(w["__id"]).max()
            model=model.join(last.rename("last_entry"),how="left")
        else:model["last_entry"]=pd.NaT

        flags=pd.DataFrame(index=model.index)
        for area in ("Colgado","Doblado","Jeans","Lencería"):
            if "Área reporte" in w.columns:
                mask=w["Área reporte"].fillna("").astype(str).eq(area)
                aset=set(w.loc[mask,"__id"].astype(str))
                flags[area]=flags.index.to_series().astype(str).isin(aset).values
            else:flags[area]=False
        if "Estatus comercial" in w.columns:
            omask=w["Estatus comercial"].fillna("").astype(str).map(m.login_key).isin(offer_keys)
            oset=set(w.loc[omask,"__id"].astype(str))
            flags["Oferta"]=flags.index.to_series().astype(str).isin(oset).values
        else:flags["Oferta"]=False

        monthly=bool(re.fullmatch(r"\d{4}-\d{2}",str(week or "")))
        pcol="sales_pzas_month" if monthly else "sales_pzas_7"
        vcol="sales_value_month" if monthly else "sales_value_7"
        model["sales_pzas"]=pd.to_numeric(model.get(pcol,0),errors="coerce").fillna(0)
        model["sales_value"]=pd.to_numeric(model.get(vcol,0),errors="coerce").fillna(0)

        try:report_date=pd.Timestamp(m._capacity_report_date(entry))
        except Exception:report_date=pd.Timestamp.now().normalize()
        last=pd.to_datetime(model["last_entry"],errors="coerce")
        zero_eligible=(
            (pd.to_numeric(model["suggested"],errors="coerce").fillna(0)<=1)
            &(pd.to_numeric(model["sales_pzas_30"],errors="coerce").fillna(0)<=0)
            &last.notna()&(last>=report_date-pd.Timedelta(days=30))&(last<=report_date)
        )
        all_models=model.copy()
        slow=model[(model["suggested"]<=1)|(model["sales_pzas_30"]<=0)]
        slow=slow[~zero_eligible.reindex(slow.index,fill_value=False)].sort_values(["existence","suggested","sales_pzas_30"],ascending=[False,True,True]).head(50)
        zero=model[zero_eligible].sort_values(["existence","sales_pzas_30"],ascending=[False,True]).head(80)

        def summarize(selected_models):
            result=[]
            for area in areas:
                if selected_models.empty:
                    sub=selected_models
                else:
                    ids_idx=selected_models.index.intersection(flags.index[flags[area]])
                    sub=selected_models.loc[ids_idx]
                models_count=int(len(sub))
                suggested=float(pd.to_numeric(sub.get("suggested",0),errors="coerce").fillna(0).sum()) if models_count else 0
                capacity=float(pd.to_numeric(sub.get("capacity",0),errors="coerce").fillna(0).sum()) if models_count else 0
                existence=float(pd.to_numeric(sub.get("existence",0),errors="coerce").fillna(0).sum()) if models_count else 0
                if models_count and suggested>0:
                    ddi=float((pd.to_numeric(sub.get("ddi",0),errors="coerce").fillna(0)*pd.to_numeric(sub.get("suggested",0),errors="coerce").fillna(0)).sum()/suggested)
                elif models_count:
                    ddi=float(pd.to_numeric(sub.get("ddi",0),errors="coerce").fillna(0).mean())
                else:ddi=0.0
                result.append({
                    "area":area,"models":models_count,
                    "sales_pzas":float(pd.to_numeric(sub.get("sales_pzas",0),errors="coerce").fillna(0).sum()) if models_count else 0,
                    "sales_value":float(pd.to_numeric(sub.get("sales_value",0),errors="coerce").fillna(0).sum()) if models_count else 0,
                    "existence":existence,
                    "cedis":float(pd.to_numeric(sub.get("cedis",0),errors="coerce").fillna(0).sum()) if models_count else 0,
                    "suggested":suggested,"ddi":ddi,"capacity":capacity,
                    "occupancy":existence/capacity*100 if capacity else None,
                })
            return result

        payload={"summaries":{
            "80_20":summarize(all_models),
            "slow":summarize(slow),
            "suggested_zero":summarize(zero),
        }}
        with summary_lock:
            if len(summary_cache)>20:summary_cache.pop(next(iter(summary_cache)))
            summary_cache[key]=(now,payload)
        m._release_process_memory()
        return payload

    @m.app.get("/api/commercial-model-summaries-v199")
    def commercial_model_summaries_v199(
        request: Request, week: str="", store: str="Compañía",
        section: str="Todas", catalog: str="Todos",
    ):
        actor=m.require_user(request)
        selected=str(m.effective_store(actor,store) or "Compañía")
        with m._RESOURCE_HEAVY_LOCK:
            return _commercial_summary_payload(week,selected,section,catalog)

    # ------------------------------------------------------------------
    # HTML / UX final
    # ------------------------------------------------------------------
    css=r'''<style id="v199-access-menu-productivity-css">
/* LOGIN */
#loginView.login-v15{
  min-height:100vh!important;
  display:grid!important;
  place-items:center!important;
  padding:32px 18px!important;
  background:
    radial-gradient(circle at 12% 8%,rgba(23,105,232,.18),transparent 34%),
    radial-gradient(circle at 90% 90%,rgba(16,54,107,.14),transparent 35%),
    linear-gradient(145deg,#f7faff 0%,#eef5ff 52%,#f8fbff 100%)!important;
}
#loginView.login-v15 .login-v15-bg,#loginView.login-v15 .login-v15-shade{display:none!important}
#loginView .login-v15-card{
  width:min(440px,calc(100vw - 30px))!important;
  padding:30px 30px 26px!important;
  background:#fff!important;
  border:1px solid #d8e4f2!important;
  border-radius:22px!important;
  box-shadow:0 24px 70px rgba(16,54,107,.16)!important;
  color:#123b73!important;
  text-align:center!important;
}
#loginView .login-logo-v15{width:72px!important;height:72px!important;object-fit:contain!important;margin:0 auto 10px!important;display:block!important}
#loginView .login-brand-v15{font-size:22px!important;font-weight:950!important;color:#123b73!important;letter-spacing:-.02em!important}
#loginView .login-sub-v15{font-size:12px!important;color:#6b7c93!important;margin:5px 0 20px!important;font-weight:700!important}
#loginView .login-form-v15{display:grid!important;gap:11px!important}
#loginView .login-field-v15{position:relative!important;display:flex!important;align-items:center!important;min-height:52px!important;background:#fff!important;border:1px solid #cfdbea!important;border-radius:12px!important;overflow:hidden!important}
#loginView .login-field-v15:focus-within{border-color:#1769e8!important;box-shadow:0 0 0 3px rgba(23,105,232,.11)!important}
#loginView .login-icon-v15{width:48px!important;display:grid!important;place-items:center!important;font-size:17px!important}
#loginView .login-field-v15 input{flex:1!important;width:100%!important;border:0!important;outline:0!important;background:transparent!important;color:#123b73!important;font-size:15px!important;font-weight:700!important;padding:14px 45px 14px 0!important}
#loginView .login-field-v15 input::placeholder{color:#8798ad!important;font-weight:500!important;opacity:1!important}
#loginView .v199-pass-toggle{position:absolute!important;right:8px!important;top:50%!important;transform:translateY(-50%)!important;border:0!important;background:transparent!important;color:#52708f!important;font-size:16px!important;padding:8px!important;cursor:pointer!important}
#loginView .v199-remember{display:flex!important;align-items:center!important;gap:8px!important;text-align:left!important;color:#52677f!important;font-size:11px!important;font-weight:700!important;margin:0 2px 2px!important;cursor:pointer!important}
#loginView .v199-remember input{width:16px!important;height:16px!important;accent-color:#1769e8!important}
#loginView .login-btn-v15{min-height:52px!important;border-radius:12px!important;background:linear-gradient(135deg,#1769e8,#0d7ff0)!important;box-shadow:0 12px 28px rgba(23,105,232,.22)!important;font-size:14px!important}
#loginView .server-msg-v15{color:#778aa1!important;font-size:9px!important;margin-top:16px!important}
#loginView .login-msg-v15{font-size:10px!important;min-height:18px!important}
#loginView .login-link-v17{color:#1769e8!important;font-size:10px!important}

/* MENU LATERAL */
#sidebar.side{
  background:linear-gradient(180deg,#0e477f 0%,#0b5ca2 52%,#0d477d 100%)!important;
  color:#fff!important;border-right:0!important;padding:14px 10px!important;gap:4px!important;
}
#sidebar .sidebar-toggle{background:rgba(255,255,255,.10)!important;border:1px solid rgba(255,255,255,.2)!important;color:#fff!important}
#sidebar .sidebrand{padding:4px 8px 14px!important;gap:10px!important;border-bottom:1px solid rgba(255,255,255,.12)!important;margin-bottom:7px!important}
#sidebar .sidebrand img{width:44px!important;height:44px!important;object-fit:contain!important;flex:0 0 44px!important}
#sidebar .sidebrand-text b{color:#fff!important;font-size:13px!important;line-height:1.2!important}
#sidebar .sidebrand-text small{color:#dbeafe!important;font-size:8px!important;margin-top:3px!important}
#sidebar .group{color:#9fc6ec!important;font-size:7.5px!important;letter-spacing:.8px!important;padding:12px 10px 4px!important}
#sidebar .nav{color:#fff!important;background:transparent!important;border:1px solid transparent!important;padding:10px 9px!important;border-radius:10px!important}
#sidebar .nav small{color:#dbeafe!important;opacity:.78!important}
#sidebar .nav:hover{background:rgba(255,255,255,.08)!important}
#sidebar .nav.active{background:#1677e8!important;border-color:rgba(255,255,255,.16)!important;box-shadow:0 8px 20px rgba(0,0,0,.12)!important}
#sidebar .profile{
  margin-top:auto!important;
  background:rgba(255,255,255,.08)!important;
  border:1px solid rgba(255,255,255,.14)!important;
  border-radius:12px!important;
  padding:9px!important;
  min-height:0!important;height:auto!important;
  color:#fff!important;
}
#sidebar .profile b,#sidebar .profile small{color:#eaf4ff!important}
#sidebar .profile #viewRoleBox{background:transparent!important}
#sidebar .profile select{background:#fff!important;color:#123b73!important;border-radius:8px!important;border:0!important}
#sidebar .logout{width:100%!important;background:#fff!important;color:#0e4c86!important;border:0!important;border-radius:9px!important;font-weight:900!important;padding:9px!important;margin-top:7px!important}
#sidebar #profileMeta{opacity:.78!important;margin-top:5px!important;font-size:7px!important}
.shell.sidebar-collapsed #sidebar .profile{padding:6px!important}
.shell.sidebar-collapsed #sidebar .logout{font-size:0!important;padding:9px 4px!important}
.shell.sidebar-collapsed #sidebar .logout:before{content:'↪';font-size:17px!important}

/* CAPTURA PRODUCTIVIDAD CM */
.v199-prod-panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:11px}
.v199-prod-head{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.v199-prod-head h3{margin:0;color:#123b73;font-size:15px}
.v199-timer{font-variant-numeric:tabular-nums;font-size:28px;font-weight:950;color:#123b73;background:#eef5ff;border-radius:12px;padding:9px 14px;min-width:132px;text-align:center}
.v199-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:12px}
.v199-field label{display:block;font-size:8px;color:#667085;font-weight:950;text-transform:uppercase;margin-bottom:5px}
.v199-field input,.v199-field select{width:100%;min-height:43px;border:1px solid #ccd6e2;border-radius:9px;background:#fff;color:#123b73;padding:8px 10px;font-size:13px}
.v199-motives{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px}
.v199-motive{border:1px solid #dde6f0;border-radius:12px;padding:10px;background:#f9fbfe}
.v199-motive b{display:block;font-size:10px;color:#123b73;margin-bottom:6px}
.v199-motive input{width:100%;min-height:45px;border:1px solid #cdd9e7;border-radius:9px;padding:8px;font-size:18px;font-weight:900;color:#123b73}
.v199-prod-actions{display:flex;gap:8px;margin-top:12px}
.v199-start,.v199-finish{border:0;border-radius:10px;padding:11px 18px;font-weight:950;cursor:pointer}
.v199-start{background:#16a34a;color:#fff}.v199-finish{background:#dc2626;color:#fff}
.v199-start:disabled,.v199-finish:disabled{opacity:.45;cursor:not-allowed}
.v199-source-note{font-size:8.5px;color:#667085;margin-top:8px}
.v199-digital-badge{display:inline-flex;padding:4px 7px;border-radius:999px;background:#dcfce7;color:#166534;font-size:7.5px;font-weight:950}
@media(max-width:900px){
 #loginView .login-v15-card{padding:24px 18px 22px!important}
 .v199-form-grid{grid-template-columns:1fr}.v199-motives{grid-template-columns:repeat(3,minmax(0,1fr))}
 .v199-timer{font-size:22px}
}
</style>'''

    js=r'''<script id="v199-access-menu-productivity-js">
(function(){
if(window.__V199_ACCESS_PERF_PRODUCTIVITY)return;window.__V199_ACCESS_PERF_PRODUCTIVITY=true;
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>{const x=Number(v||0);return Number.isFinite(x)?x:0};
const fmt=v=>Math.round(num(v)).toLocaleString('es-MX');
const pct=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%';
const C='Cargar productividad';

function fixBrand(){
  const loginLogo=q('#loginView .login-logo-v15');
  if(loginLogo){loginLogo.src='/static/app-icon-192.svg';loginLogo.alt='Operaciones Ropa'}
  const side=q('#sidebar .sidebrand img');
  if(side){side.src='/static/app-icon-192.svg';side.alt='Operaciones Ropa'}
  const brand=q('#loginView .login-brand-v15');if(brand)brand.textContent='Operaciones Ropa';
  const sub=q('#loginView .login-sub-v15');if(sub)sub.textContent='Inicia sesión para continuar';
}

function setupLogin(){
  fixBrand();
  const user=q('#loginUser'),pass=q('#loginPass'),normal=q('#normalLogin');
  if(!user||!pass||!normal)return;
  user.name='username';pass.name='password';user.autocomplete='username';pass.autocomplete='current-password';
  let remember=q('#v199Remember');
  if(!remember){
    const label=document.createElement('label');label.className='v199-remember';
    label.innerHTML='<input id="v199Remember" type="checkbox"> <span>Recordarme en este equipo</span>';
    const btn=q('#loginBtn');normal.insertBefore(label,btn);
    remember=q('#v199Remember');
  }
  if(!q('#v199PassToggle')){
    const b=document.createElement('button');b.type='button';b.id='v199PassToggle';b.className='v199-pass-toggle';b.title='Mostrar / ocultar contraseña';b.textContent='👁';
    pass.parentElement.appendChild(b);
    b.onclick=()=>{pass.type=pass.type==='password'?'text':'password';b.textContent=pass.type==='password'?'👁':'🙈'};
  }
  const saved=localStorage.getItem('operacionesRopa.rememberUser')||'';
  if(saved&&!user.value){user.value=saved;remember.checked=true}
  if(saved&&remember.checked&&navigator.credentials&&window.PasswordCredential){
    navigator.credentials.get({password:true,mediation:'optional'}).then(cred=>{
      if(cred&&cred.id&&(!user.value||user.value===saved)){
        user.value=cred.id||saved;
        if(cred.password)pass.value=cred.password;
      }
    }).catch(()=>{});
  }
  if(!q('#v199LoginHook')){
    const marker=document.createElement('span');marker.id='v199LoginHook';marker.hidden=true;normal.appendChild(marker);
    q('#loginBtn')?.addEventListener('click',()=>{
      const keep=q('#v199Remember')?.checked;
      if(keep)localStorage.setItem('operacionesRopa.rememberUser',user.value.trim());
      else localStorage.removeItem('operacionesRopa.rememberUser');
      if(keep&&user.value&&pass.value&&navigator.credentials?.store&&window.PasswordCredential){
        try{navigator.credentials.store(new PasswordCredential({id:user.value,password:pass.value,name:user.value})).catch(()=>{})}catch(_){}
      }
    },true);
  }
}

let retryCount=0;
function setupServerRetry(){
  const msg=q('#serverMsg');if(!msg||msg.__v199)return;msg.__v199=true;
  const mo=new MutationObserver(()=>{
    const t=String(msg.textContent||'').toLowerCase();
    if((t.includes('reinició')||t.includes('iniciando')||t.includes('502')||t.includes('503'))&&retryCount<3){
      retryCount++;msg.textContent='Reconectando con el servidor…';
      setTimeout(()=>{try{if(typeof start==='function')start()}catch(_){}},1200*retryCount);
    }
  });
  mo.observe(msg,{childList:true,subtree:true,characterData:true});
}

function ensureCaptureTab(){
  const nav=q('#operativoNav');if(!nav)return;
  if(q('[data-opview="'+C+'"]',nav))return;
  const b=document.createElement('button');b.className='switch';b.dataset.opview=C;b.dataset.tabKey='operations.productivity_capture';b.textContent=C;
  const prod=q('[data-opview="Productividad por Colaborador"]',nav);
  if(prod)prod.after(b);else nav.appendChild(b);
  b.onclick=async()=>{
    try{OP_VIEW=C}catch(_){}
    qa('#operativoNav>button').forEach(x=>x.classList.toggle('active',x===b));
    await window.renderOperativoView(C,true);
  };
  document.dispatchEvent(new CustomEvent('report-tabs-visibility-changed'));
}

function currentStore(){return q('#operStoreSelect')?.value||''}
function currentPeriodType(){try{return OPER_PERIOD.type||'day'}catch(_){return 'day'}}
function currentPeriodValue(){try{return OPER_PERIOD.value||''}catch(_){return ''}}
function hms(sec){sec=Math.max(0,Math.floor(sec||0));const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60),s=sec%60;return [h,m,s].map(x=>String(x).padStart(2,'0')).join(':')}
let timerId=0,activeRecord=null;

async function capApi(url,opt){if(typeof api==='function')return api(url,opt);const r=await fetch(url,{credentials:'same-origin',...(opt||{})});const d=await r.json();if(!r.ok)throw Error(d.detail||('HTTP '+r.status));return d}

function updateTimer(){
 const el=q('#v199Timer');if(!el)return;
 if(!activeRecord||!activeRecord.started_at){el.textContent='00:00:00';return}
 const start=new Date(activeRecord.started_at).getTime(),now=Date.now();
 el.textContent=hms((now-start)/1000);
}
function startTimer(){clearInterval(timerId);updateTimer();timerId=setInterval(updateTimer,1000)}

async function renderCapture(){
  const centro=q('#operativoCentro'),dyn=q('#operativoDynamic');centro?.classList.add('hidden');dyn?.classList.remove('hidden');
  q('#operativoPeriodBar')?.classList.add('hidden');
  if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent='Cargar productividad';
  if(q('#operativoDynamicSub'))q('#operativoDynamicSub').textContent='Cambios y Muertos · actividad, motivos, piezas y tiempo real';
  const host=q('#operativoDynamicContent');if(!host)return;
  host.innerHTML='<div class="infoempty">Preparando captura…</div>';
  let meta,act,hist;
  try{
    [meta,act]=await Promise.all([capApi('/api/cm-productivity/meta'),capApi('/api/cm-productivity/active')]);
    activeRecord=act.item||null;
    const today=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    const selected=(meta.user?.store||currentStore()||meta.stores?.[0]||'');
    hist=await capApi('/api/cm-productivity/history?date='+encodeURIComponent(today)+'&store='+encodeURIComponent(selected));
    const restricted=['tienda','colaborador_operativo','colaborador_lenceria'].includes(meta.user?.role);
    const storeHtml=restricted
      ?'<input id="v199Store" value="'+esc(meta.user?.store||'')+'" disabled>'
      :'<select id="v199Store">'+(meta.stores||[]).map(s=>'<option'+(s===selected?' selected':'')+'>'+esc(s)+'</option>').join('')+'</select>';
    const a=activeRecord;
    host.innerHTML='<div class="v199-prod-panel">'+
      '<div class="v199-prod-head"><div><h3>Registro de productividad</h3><div class="v199-source-note">Inicio y Fin guardan el tiempo real. Las piezas se separan por motivo de ingreso.</div></div><div id="v199Timer" class="v199-timer">00:00:00</div></div>'+
      '<div class="v199-form-grid">'+
        '<div class="v199-field"><label>Fecha</label><input id="v199Date" type="date" value="'+esc(a?.date||today)+'" '+(a?'disabled':'')+'></div>'+
        '<div class="v199-field"><label>Tienda</label>'+storeHtml+'</div>'+
        '<div class="v199-field"><label>Colaborador</label><input id="v199Employee" value="'+esc(a?.employee_name||meta.user?.username||'')+'" '+(a?'disabled':'')+'></div>'+
        '<div class="v199-field"><label>Nómina (opcional)</label><input id="v199EmployeeNo" value="'+esc(a?.employee_no||'')+'" '+(a?'disabled':'')+'></div>'+
        '<div class="v199-field" style="grid-column:1/-1"><label>Actividad realizada</label><select id="v199Activity" '+(a?'disabled':'')+'>'+((meta.activities||[]).map(x=>'<option'+(a?.activity===x?' selected':'')+'>'+esc(x)+'</option>').join(''))+'</select></div>'+
      '</div>'+
      '<div class="v199-motives">'+
        '<div class="v199-motive"><b>Muertos · piezas</b><input id="v199Muertos" type="number" min="0" inputmode="numeric" value="'+num(a?.muertos)+'"></div>'+
        '<div class="v199-motive"><b>Cajas · piezas</b><input id="v199Cajas" type="number" min="0" inputmode="numeric" value="'+num(a?.cajas)+'"></div>'+
        '<div class="v199-motive"><b>Probador · piezas</b><input id="v199Probador" type="number" min="0" inputmode="numeric" value="'+num(a?.probador)+'"></div>'+
      '</div>'+
      '<div class="v199-prod-actions"><button id="v199Start" class="v199-start" '+(a?'disabled':'')+'>▶ Inicio</button><button id="v199Finish" class="v199-finish" '+(!a?'disabled':'')+'>■ Fin</button></div>'+
      '<div id="v199Msg" class="v199-source-note"></div></div>'+
      '<div class="v199-prod-panel"><h3 style="margin-top:0">Capturas de hoy</h3><div class="tablewrap"><table class="table"><thead><tr><th>Colaborador</th><th>Actividad</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Total</th><th>Tiempo</th><th>Estado</th></tr></thead><tbody>'+
      ((hist.items||[]).map(r=>'<tr><td><b>'+esc(r.employee_name)+'</b></td><td>'+esc(r.activity)+'</td><td>'+fmt(r.muertos)+'</td><td>'+fmt(r.cajas)+'</td><td>'+fmt(r.probador)+'</td><td><b>'+fmt(num(r.muertos)+num(r.cajas)+num(r.probador))+'</b></td><td>'+hms(r.duration_seconds)+'</td><td>'+esc(r.status==='active'?'En curso':'Finalizado')+'</td></tr>').join('')||'<tr><td colspan="8">Sin capturas de hoy.</td></tr>')+
      '</tbody></table></div></div>';
    if(a)startTimer();else{clearInterval(timerId);activeRecord=null;updateTimer()}
    q('#v199Start')?.addEventListener('click',async()=>{
      const msg=q('#v199Msg');msg.textContent='Iniciando…';
      try{
        const r=await capApi('/api/cm-productivity/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          date:q('#v199Date').value,store:q('#v199Store').value,employee_name:q('#v199Employee').value,
          employee_no:q('#v199EmployeeNo').value,activity:q('#v199Activity').value
        })});
        msg.textContent=r.message;await renderCapture();
      }catch(e){msg.textContent=e.message}
    });
    q('#v199Finish')?.addEventListener('click',async()=>{
      if(!activeRecord)return;
      const msg=q('#v199Msg');msg.textContent='Finalizando…';
      try{
        const r=await capApi('/api/cm-productivity/'+activeRecord.id+'/finish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          muertos:num(q('#v199Muertos').value),cajas:num(q('#v199Cajas').value),probador:num(q('#v199Probador').value)
        })});
        msg.textContent=r.message;activeRecord=null;clearInterval(timerId);await renderCapture();
      }catch(e){msg.textContent=e.message}
    });
  }catch(e){host.innerHTML='<div class="infoempty">No fue posible abrir Cargar productividad: '+esc(e.message||e)+'</div>'}
}

function digitalReportHtml(rep){
  const rows=rep.productivity||[],total=rows.reduce((a,r)=>a+num(r.pieces),0);
  const days=rows.reduce((a,r)=>a+num(r.days),0),daily=days?total/days:0;
  const target=rows.reduce((a,r)=>a+num(r.target),0),comp=target?total/target*100:0;
  const cards='<div class="report-kpis">'+
    '<div class="report-kpi" style="--rk:#1769e8"><div class="rk-label">Piezas procesadas</div><div class="rk-value">'+fmt(total)+'</div><div class="rk-sub">Captura digital</div></div>'+
    '<div class="report-kpi" style="--rk:#F59E0B"><div class="rk-label">Productividad</div><div class="rk-value">'+fmt(daily)+'</div><div class="rk-sub">Piezas / colaborador-día</div></div>'+
    '<div class="report-kpi" style="--rk:#10B981"><div class="rk-label">Cumplimiento</div><div class="rk-value">'+pct(comp)+'</div><div class="rk-sub">Meta configurada</div></div></div>';
  return '<div style="margin-bottom:8px"><span class="v199-digital-badge">Fuente digital desde captura</span></div>'+cards+
    '<div class="title">Ranking completo</div><div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Colaborador</th><th>Tienda</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Piezas</th><th>Tiempo</th><th>Días</th><th>Prod. diaria</th><th>Meta</th><th>Cumplimiento</th></tr></thead><tbody>'+
    (rows.map((r,i)=>'<tr><td>'+(i+1)+'</td><td><b>'+esc(r.name)+'</b></td><td>'+esc(r.store)+'</td><td>'+fmt(r.muertos)+'</td><td>'+fmt(r.cajas)+'</td><td>'+fmt(r.probador)+'</td><td><b>'+fmt(r.pieces)+'</b></td><td>'+hms(r.duration_seconds)+'</td><td>'+fmt(r.days)+'</td><td>'+fmt(r.daily)+'</td><td>'+fmt(r.target)+'</td><td>'+pct(r.pct)+'</td></tr>').join('')||'<tr><td colspan="12">Sin productividad digital en este periodo.</td></tr>')+
    '</tbody></table></div><div class="v199-source-note">Los periodos sin captura digital continúan mostrando la información histórica del Excel.</div>';
}

function installRenderer(){
  if(typeof window.renderOperativoView!=='function'||window.renderOperativoView.__v199)return;
  const prev=window.renderOperativoView;
  const wrapped=async function(name,force){
    if(name===C)return renderCapture();
    const result=await prev.call(this,name,force);
    if(name==='Productividad por Colaborador'||name==='Ranking de Colaboradores'){
      try{
        const qs=new URLSearchParams({period_type:currentPeriodType(),period_value:currentPeriodValue(),store:currentStore()||'Compañía'});
        const rep=await capApi('/api/cm-productivity/report?'+qs,{timeoutMs:30000});
        if(rep.use_digital&&q('#operativoDynamicContent'))q('#operativoDynamicContent').innerHTML=digitalReportHtml(rep);
      }catch(e){console.warn('[V199] productividad digital',e)}
    }
    return result;
  };
  wrapped.__v199=true;window.renderOperativoView=wrapped;
}

function setup(){
  setupLogin();setupServerRetry();fixBrand();ensureCaptureTab();installRenderer();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
[100,400,1000,2200].forEach(ms=>setTimeout(setup,ms));
window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});
console.info('[V199] acceso, menú, rendimiento comercial y productividad Cambios/Muertos activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v199_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            # Logo que sí forma parte del paquete PWA.
            html=html.replace("/static/price_shoes_logo.png","/static/app-icon-192.svg")
            # Nueva pestaña antes de ejecutar el JS base, para que herede sus eventos.
            if 'data-tab-key="operations.productivity_capture"' not in html:
                anchor='<button class="switch" data-opview="Productividad por Colaborador" data-tab-key="operations.productivity">Productividad</button>'
                insert=anchor+'\n  <button class="switch" data-opview="Cargar productividad" data-tab-key="operations.productivity_capture">Cargar productividad</button>'
                html=html.replace(anchor,insert,1)
            if "v199-access-menu-productivity-css" not in html:html=html.replace("</head>",css+"</head>",1)
            if "v199-access-menu-productivity-js" not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None)
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V199"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V199] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V199_ACCESS_PERF_PRODUCTIVITY=True
    print("[V199] Acceso/menu + resumen comercial ligero + productividad digital instalado.",flush=True)
