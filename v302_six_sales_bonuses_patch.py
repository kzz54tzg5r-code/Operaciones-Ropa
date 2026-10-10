"""V302 · Seis modelos seleccionables dentro del único módulo Bonos.

Bono 1 conserva exactamente el cálculo de V293 (Venta vs Meta 50% + DDI por Cat 30% + Asistencia 20%).
Bono 2..6 reutilizan los mismos datos/criterios sin tocar el Bono Operativo de V279.
Las configuraciones nuevas son versionadas por mes efectivo para no alterar históricos.
"""
from __future__ import annotations

import json, math
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX=ZoneInfo("America/Mexico_City")
ADMIN=("superadmin","admin")
BONUS_NOS=(1,2,3,4,5,6)
CRITERIA=(
    ("sales","Venta vs Meta",50.0),
    ("ddi","DDI por Cat",30.0),
    ("attendance","Asistencia",20.0),
)
METHODS={1:"existing",2:"proportional",3:"weighted",4:"bands",5:"accumulated",6:"integral"}

def install(m):
    if getattr(m,"_V302_SIX_SALES_BONUSES",False): return

    def now_iso(): return datetime.now(MX).isoformat(timespec="seconds")
    def num(v,default=0.0):
        try:
            x=float(v)
            return x if math.isfinite(x) else default
        except Exception:return default
    def clamp(v,lo=0.0,hi=100.0): return max(lo,min(hi,num(v)))
    def month_key(v):
        s=str(v or "").strip()
        if len(s)==7 and s[4]=="-":
            try:
                y=int(s[:4]); mm=int(s[5:7])
                if 1<=mm<=12:return f"{y:04d}-{mm:02d}"
            except Exception:pass
        n=datetime.now(MX);return f"{n.year:04d}-{n.month:02d}"

    base_weights={k:w for k,_label,w in CRITERIA}
    base_points={k:w for k,_label,w in CRITERIA}
    defaults={
        1:{"method":"existing","active":True,"locked":True,"weights":base_weights,"max_points":base_points},
        2:{"method":"proportional","active":True,"locked":False,"max_points":base_points,"compliance_cap_pct":100.0},
        3:{"method":"weighted","active":True,"locked":False,"weights":base_weights,"compliance_cap_pct":100.0},
        4:{"method":"bands","active":False,"locked":False,"bands":{k:[] for k,_,_ in CRITERIA}},
        5:{"method":"accumulated","active":True,"locked":False,"max_points":base_points,"compliance_cap_pct":100.0},
        6:{"method":"integral","active":False,"locked":False,"weights":base_weights,"minimums":{k:None for k,_,_ in CRITERIA},"penalty_pct":0.0},
    }

    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS sales_bonus_model_versions_v302(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bonus_no INTEGER NOT NULL,
            version INTEGER NOT NULL,
            effective_from TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            config_json TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            UNIQUE(bonus_no,version)
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_sales_bonus_model_v302_effective ON sales_bonus_model_versions_v302(bonus_no,effective_from,version)")
        con.execute("""CREATE TABLE IF NOT EXISTS sales_bonus_official_versions_v302(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            effective_from TEXT NOT NULL,
            bonus_no INTEGER NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL
        )""")
        for b in BONUS_NOS:
            exists=con.execute("SELECT 1 FROM sales_bonus_model_versions_v302 WHERE bonus_no=? LIMIT 1",(b,)).fetchone()
            if not exists:
                con.execute("INSERT INTO sales_bonus_model_versions_v302(bonus_no,version,effective_from,active,config_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",
                    (b,1,"0000-00",1 if defaults[b]["active"] else 0,json.dumps(defaults[b],ensure_ascii=False),now_iso(),"system"))
        if not con.execute("SELECT 1 FROM sales_bonus_official_versions_v302 LIMIT 1").fetchone():
            con.execute("INSERT INTO sales_bonus_official_versions_v302(effective_from,bonus_no,changed_at,changed_by) VALUES(?,?,?,?)",
                ("0000-00",1,now_iso(),"system"))

    def base_endpoint():
        for route in getattr(m.app,"routes",[]):
            if getattr(route,"path","")=="/api/operation/sales-bonus-v293":
                return getattr(route,"endpoint",None)
        return None

    def config_for(bonus_no,month):
        b=int(bonus_no)
        with m.db() as con:
            row=con.execute("""SELECT version,effective_from,active,config_json,changed_at,changed_by
                FROM sales_bonus_model_versions_v302
                WHERE bonus_no=? AND effective_from<=?
                ORDER BY effective_from DESC,version DESC LIMIT 1""",(b,month)).fetchone()
        if not row:
            cfg=dict(defaults[b]);return {**cfg,"version":0,"effective_from":"0000-00","active":bool(cfg.get("active"))}
        try: cfg=json.loads(row["config_json"] or "{}")
        except Exception: cfg={}
        merged={**defaults[b],**cfg}
        merged.update(version=int(row["version"]),effective_from=str(row["effective_from"]),active=bool(row["active"]),
                      changed_at=str(row["changed_at"]),changed_by=str(row["changed_by"]))
        return merged

    def official_for(month):
        with m.db() as con:
            row=con.execute("""SELECT bonus_no FROM sales_bonus_official_versions_v302
                WHERE effective_from<=? ORDER BY effective_from DESC,id DESC LIMIT 1""",(month,)).fetchone()
        b=int(row["bonus_no"]) if row else 1
        return b if b in BONUS_NOS else 1

    def pct_map_selected(base):
        s=base.get("selected") or {}
        return {
            "sales": (s.get("sales") or {}).get("pct"),
            "ddi": (s.get("ddi") or {}).get("pct"),
            "attendance": (s.get("attendance") or {}).get("pct"),
        }

    def classify(pct,ready=True):
        if not ready:return "Información incompleta"
        p=num(pct)
        return "Excelente" if p>=90 else "Bueno" if p>=70 else "En riesgo" if p>=50 else "Crítico"

    def config_ready(b,cfg):
        if not bool(cfg.get("active")): return False,"Bono desactivado"
        if b==4:
            bands=cfg.get("bands") or {}
            if any(not isinstance(bands.get(k),list) or not bands.get(k) for k,_,_ in CRITERIA):
                return False,"Faltan rangos autorizados"
        if b==6:
            mins=cfg.get("minimums") or {}
            if any(mins.get(k) is None for k,_,_ in CRITERIA):
                return False,"Faltan mínimos autorizados"
        return True,""

    def calc_model(bonus_no,pcts,cfg,b1_score=None,b1_ready=False):
        b=int(bonus_no); breakdown=[]; ok_cfg,cfg_reason=config_ready(b,cfg)
        missing=[k for k,_,_ in CRITERIA if pcts.get(k) is None]
        ready_data=not missing
        total=0.0; max_total=0.0; formula=""; meets_all=True
        if b==1:
            weights=base_weights
            for k,label,w in CRITERIA:
                p=pcts.get(k); pts=None if p is None else clamp(p)*w/100.0
                breakdown.append({"key":k,"indicator":label,"compliance_pct":p,"max_points":w,"points":pts,"weight":w,"status":"N/D" if p is None else ("Cumple" if num(p)>=100 else "Pendiente")})
            score=num(b1_score); total=score;max_total=100.0;ready=bool(b1_ready)
            return {"bonus_no":1,"name":"Bono 1","points":round(total,2),"max_points":100.0,"compliance_pct":round(score,2),
                    "ready":ready,"config_ready":True,"configuration_reason":"","classification":classify(score,ready),
                    "criteria_total":3,"criteria_met":sum(1 for x in breakdown if x["compliance_pct"] is not None and num(x["compliance_pct"])>=100),
                    "criteria_pending":sum(1 for x in breakdown if x["compliance_pct"] is None or num(x["compliance_pct"])<100),
                    "breakdown":breakdown,"formula":"Cálculo original conservado: 50% Venta vs Meta + 30% DDI por Cat + 20% Asistencia."}
        if not ok_cfg:
            return {"bonus_no":b,"name":f"Bono {b}","points":None,"max_points":None,"compliance_pct":None,"ready":False,
                    "config_ready":False,"configuration_reason":cfg_reason,"classification":"Pendiente de configuración",
                    "criteria_total":3,"criteria_met":0,"criteria_pending":3,"breakdown":[],"formula":""}
        cap=clamp(cfg.get("compliance_cap_pct",100),1,100)
        if b in (2,5):
            mps=cfg.get("max_points") or {}
            for k,label,_w in CRITERIA:
                mx=max(0.0,num(mps.get(k))); p=pcts.get(k); pts=None if p is None else mx*min(max(num(p),0.0),cap)/100.0
                max_total+=mx
                if pts is not None: total+=pts
                breakdown.append({"key":k,"indicator":label,"compliance_pct":p,"max_points":mx,"points":None if pts is None else round(pts,2),"weight":None,"status":"N/D" if p is None else ("Cumple" if num(p)>=100 else "Pendiente")})
            formula=("Puntos = Puntos máximos × Cumplimiento / 100; suma proporcional de criterios." if b==2
                     else "Cada criterio acumula puntos hasta su máximo; el total es la suma de puntos ganados.")
        elif b==3:
            ws=cfg.get("weights") or {}
            for k,label,_w in CRITERIA:
                w=max(0.0,num(ws.get(k)));p=pcts.get(k);pts=None if p is None else min(max(num(p),0.0),cap)*w/100.0
                max_total+=w
                if pts is not None:total+=pts
                breakdown.append({"key":k,"indicator":label,"compliance_pct":p,"max_points":w,"points":None if pts is None else round(pts,2),"weight":w,"status":"N/D" if p is None else ("Cumple" if num(p)>=100 else "Pendiente")})
            formula="Aporte = Cumplimiento × Ponderación / 100; total normalizado por la suma de ponderaciones."
        elif b==4:
            bands=cfg.get("bands") or {}
            for k,label,_w in CRITERIA:
                p=pcts.get(k);rows=bands.get(k) or [];mx=max([num(x.get("points")) for x in rows] or [0]);pts=None
                if p is not None:
                    pv=num(p);candidates=[]
                    for band in rows:
                        lo=num(band.get("min"),0); hi=band.get("max")
                        if pv>=lo and (hi is None or hi=="" or pv<num(hi)):
                            candidates.append(num(band.get("points")))
                    pts=max(candidates) if candidates else 0.0
                max_total+=mx
                if pts is not None:total+=pts
                breakdown.append({"key":k,"indicator":label,"compliance_pct":p,"max_points":mx,"points":None if pts is None else round(pts,2),"weight":None,"status":"N/D" if p is None else ("Nivel asignado" if pts else "Sin nivel")})
            formula="Cada cumplimiento cae en un rango autorizado y recibe los puntos definidos para ese nivel."
        else:
            ws=cfg.get("weights") or {}; mins=cfg.get("minimums") or {}
            for k,label,_w in CRITERIA:
                w=max(0.0,num(ws.get(k)));p=pcts.get(k);minimum=num(mins.get(k));pts=None if p is None else clamp(p)*w/100.0
                met=(p is not None and num(p)>=minimum);meets_all=meets_all and met
                max_total+=w
                if pts is not None:total+=pts
                breakdown.append({"key":k,"indicator":label,"compliance_pct":p,"max_points":w,"points":None if pts is None else round(pts,2),"weight":w,"minimum":minimum,"status":"N/D" if p is None else ("Cumple mínimo" if met else "No cumple mínimo")})
            penalty=clamp(cfg.get("penalty_pct",0),0,100)
            if ready_data and not meets_all and penalty>0: total*=1-penalty/100.0
            formula="Se calculan aportes ponderados y se validan mínimos autorizados; sólo se aplica penalización si fue configurada."
        final_pct=(total/max_total*100.0) if max_total>0 else 0.0
        ready=bool(ok_cfg and ready_data and max_total>0)
        classification=("No cumple mínimos" if b==6 and ready and not meets_all else classify(final_pct,ready))
        return {"bonus_no":b,"name":f"Bono {b}","points":round(total,2) if max_total>0 else None,"max_points":round(max_total,2) if max_total>0 else None,
                "compliance_pct":round(final_pct,2) if max_total>0 else None,"ready":ready,"config_ready":ok_cfg,"configuration_reason":cfg_reason,
                "classification":classification,"criteria_total":3,
                "criteria_met":sum(1 for x in breakdown if x.get("status") in ("Cumple","Nivel asignado","Cumple mínimo")),
                "criteria_pending":sum(1 for x in breakdown if x.get("status") not in ("Cumple","Nivel asignado","Cumple mínimo")),
                "breakdown":breakdown,"formula":formula}


    def enrich_breakdown(base,model):
        s=base.get("selected") or {}
        sales=s.get("sales") or {}; ddi=s.get("ddi") or {}; att=s.get("attendance") or {}
        values={
            "sales":{"meta":sales.get("goal"),"result":sales.get("actual"),"unit":"$","source":"Base Muertos/Cambios + METAS 2026"},
            "ddi":{"meta":100.0,"result":ddi.get("pct"),"unit":"%","source":"Capacidades"},
            "attendance":{"meta":100.0,"result":att.get("pct"),"unit":"%","source":"Captura de Asistencia"},
        }
        out=[]
        for row in model.get("breakdown") or []:
            out.append({**row,**values.get(row.get("key"),{})})
        model["breakdown"]=out
        return model

    def ranking_for(base,bonus_no,cfg):
        rows=[]
        for r in base.get("ranking") or []:
            pcts={"sales":r.get("sales_pct"),"ddi":r.get("ddi_pct"),"attendance":r.get("attendance_pct")}
            model=calc_model(bonus_no,pcts,cfg,r.get("score"),bool(r.get("score_ready")))
            rows.append({"store":r.get("store"),"model":model})
        ready=[x for x in rows if x["model"].get("ready") and x["model"].get("points") is not None]
        ready.sort(key=lambda x:(-num(x["model"].get("compliance_pct")),-num(x["model"].get("points")),str(x.get("store") or "")))
        pos={str(x["store"]):i for i,x in enumerate(ready,1)}
        rows.sort(key=lambda x:(pos.get(str(x["store"]),10**6),str(x.get("store") or "")))
        return [{"rank":pos.get(str(x["store"])),"store":x["store"],"points":x["model"].get("points"),
                 "max_points":x["model"].get("max_points"),"compliance_pct":x["model"].get("compliance_pct"),
                 "classification":x["model"].get("classification"),"ready":x["model"].get("ready"),
                 "configuration_reason":x["model"].get("configuration_reason","")} for x in rows]

    def glossary_for(bonus_no,cfg):
        b=int(bonus_no)
        common={
            "name":f"Bono {b}",
            "objective":"Evaluar el desempeño de la tienda utilizando exactamente los criterios y fuentes heredados de Bono 1.",
            "evaluated":"Tiendas. Este módulo no evalúa colaboradores ni clústeres porque Bono 1 pertenece al indicador comercial Bonos por Venta; Bonos Operativos permanece separado en Operación.",
            "period":"Mes seleccionado.",
            "sources":["Base Muertos/Cambios para venta real","METAS 2026 para meta mensual","Capacidades para Existencia, DDI e Inversión","Captura de Asistencia"],
            "criteria":[
                {"key":"sales","name":"Venta vs Meta","meaning":"Cumplimiento de la venta acumulada de la tienda frente a su meta mensual.","source":"Base Muertos/Cambios + METAS 2026","meta":"Meta mensual de la tienda","missing":"Se muestra N/D y no se interpreta como incumplimiento."},
                {"key":"ddi","name":"DDI por Cat","meaning":"Avance de los modelos objetivo de Abrigador, Licencias y Básicos fijados al inicio del mes, considerando reducción de DDI e inversión.","source":"Capacidades","meta":"100% de avance sobre la cartera objetivo","missing":"Se muestra N/D y no se interpreta como incumplimiento."},
                {"key":"attendance","name":"Asistencia","meaning":"Porcentaje de asistencia autorizado para la tienda en el mes.","source":"Captura de Asistencia","meta":"100%","missing":"Se muestra N/D y no se interpreta como incumplimiento."},
            ],
            "rules":[
                "Información faltante se reporta como N/D; no equivale a cero ni a incumplimiento.",
                "Si una meta matemática es cero, el cumplimiento de esa entrada no se calcula hasta contar con una meta válida.",
                "Los datos por encima de 100% respetan el límite configurado de la metodología cuando aplique.",
                "Los cambios de configuración se versionan por mes efectivo y no reescriben periodos anteriores.",
                "Origen, Resurtido, Mixto, circuitos y estándares operativos no se mezclan en este módulo comercial.",
            ],
        }
        if b==1:
            common.update(methodology="Cálculo original existente, sin cambios.",difference="Es el modelo original y fuente de criterios para los demás.",
                          formula="Puntaje = min(Venta%,100)×0.50 + min(DDI%,100)×0.30 + min(Asistencia%,100)×0.20.")
        elif b==2:
            common.update(methodology="Cumplimiento proporcional por criterio.",difference="Convierte el cumplimiento de cada criterio directamente en puntos proporcionales.",
                          formula="Puntos criterio = Puntos máximos × min(Cumplimiento, límite) / 100. Total = suma de puntos.")
        elif b==3:
            common.update(methodology="Puntuación ponderada configurable.",difference="Cada cumplimiento se multiplica por su ponderación autorizada.",
                          formula="Aporte = min(Cumplimiento,límite) × Peso / 100. % final = suma de aportes / suma de pesos × 100.")
        elif b==4:
            common.update(methodology="Niveles escalonados configurables.",difference="El cumplimiento se convierte en puntos mediante rangos autorizados.",
                          formula="Puntos criterio = puntos del rango donde cae el cumplimiento. Total = suma de puntos de los tres criterios.")
        elif b==5:
            common.update(methodology="Acumulación de puntos por criterio.",difference="El ranking prioriza la suma de puntos ganados frente a los puntos disponibles.",
                          formula="Puntos acumulados = Σ(Puntos máximos criterio × Cumplimiento limitado / 100).")
        else:
            common.update(methodology="Evaluación integral con mínimos configurables.",difference="Además del puntaje ponderado valida requisitos mínimos por indicador.",
                          formula="Puntaje base = suma ponderada. Se verifica cada mínimo; una penalización sólo se aplica si fue autorizada en configuración.")
        common["config"]=cfg
        return common

    def base_payload(request,month,store):
        endpoint=base_endpoint()
        if endpoint is None: raise HTTPException(503,"Bono 1 no está disponible")
        return endpoint(request=request,month=month,store=store)

    def full_payload(request,month,store,bonus_no):
        month=month_key(month);b=int(bonus_no or 1)
        if b not in BONUS_NOS:b=1
        base=base_payload(request,month,store)
        cfgs={i:config_for(i,month) for i in BONUS_NOS}
        selected=calc_model(b,pct_map_selected(base),cfgs[b],(base.get("selected") or {}).get("score"),bool((base.get("selected") or {}).get("score_ready")))
        selected=enrich_breakdown(base,selected)
        rankings={i:ranking_for(base,i,cfgs[i]) for i in BONUS_NOS}
        comparison=[]
        st=str(base.get("selected_store") or "")
        for i in BONUS_NOS:
            model=calc_model(i,pct_map_selected(base),cfgs[i],(base.get("selected") or {}).get("score"),bool((base.get("selected") or {}).get("score_ready")))
            rank=next((x.get("rank") for x in rankings[i] if str(x.get("store") or "")==st),None)
            comparison.append({"bonus_no":i,"name":f"Bono {i}","points":model.get("points"),"max_points":model.get("max_points"),
                               "compliance_pct":model.get("compliance_pct"),"rank":rank,"ready":model.get("ready"),
                               "classification":model.get("classification"),"configuration_reason":model.get("configuration_reason",""),
                               "active":bool(cfgs[i].get("active"))})
        actor=m.require_user(request);role=str(actor.get("role") or "").lower()
        return {"month":month,"bonus_no":b,"name":f"Bono {b}","official_bonus":official_for(month),"can_admin":role in ADMIN,
                "stores":base.get("stores") or [],"months":base.get("months") or [],"selected_store":base.get("selected_store"),
                "model":selected,"ranking":rankings[b],"comparison":comparison,"configs":{i:{"active":bool(cfgs[i].get("active")),"version":cfgs[i].get("version"),"effective_from":cfgs[i].get("effective_from")} for i in BONUS_NOS},
                "base":base,"glossary":glossary_for(b,cfgs[b])}

    @m.app.get("/api/bonuses-v302")
    def get_bonuses_v302(request:Request,month:str="",store:str="",bonus:int=1):
        m.require_user(request)
        return full_payload(request,month,store,bonus)

    @m.app.get("/api/bonuses-v302/config")
    def get_bonus_config_v302(request:Request,month:str=""):
        actor=m.require_user(request,ADMIN);month=month_key(month)
        configs={i:config_for(i,month) for i in BONUS_NOS}
        with m.db() as con:
            hist=[dict(r) for r in con.execute("""SELECT bonus_no,version,effective_from,active,changed_at,changed_by
                FROM sales_bonus_model_versions_v302 ORDER BY id DESC LIMIT 120""").fetchall()]
            official=[dict(r) for r in con.execute("""SELECT effective_from,bonus_no,changed_at,changed_by
                FROM sales_bonus_official_versions_v302 ORDER BY id DESC LIMIT 60""").fetchall()]
        return {"month":month,"configs":configs,"official_bonus":official_for(month),"history":hist,"official_history":official,
                "user":str(actor.get("username") or "")}

    def validate_config(b,cfg):
        if b==1: raise HTTPException(400,"Bono 1 conserva su configuración original y no puede modificarse")
        out={**defaults[b],**(cfg or {})};out["method"]=METHODS[b];out["locked"]=False
        out["active"]=bool(out.get("active"))
        if b in (2,5):
            pts=out.get("max_points") or {}
            if any(num(pts.get(k),-1)<0 for k,_,_ in CRITERIA):raise HTTPException(400,"Puntos máximos inválidos")
            out["max_points"]={k:round(num(pts.get(k)),4) for k,_,_ in CRITERIA}
            out["compliance_cap_pct"]=clamp(out.get("compliance_cap_pct",100),1,100)
        if b==3:
            ws=out.get("weights") or {}
            if sum(max(0,num(ws.get(k))) for k,_,_ in CRITERIA)<=0:raise HTTPException(400,"Las ponderaciones deben sumar más de cero")
            out["weights"]={k:round(max(0,num(ws.get(k))),4) for k,_,_ in CRITERIA}
            out["compliance_cap_pct"]=clamp(out.get("compliance_cap_pct",100),1,100)
        if b==4:
            bands=out.get("bands") or {}
            clean={}
            for k,_,_ in CRITERIA:
                rows=[]
                for x in bands.get(k) or []:
                    lo=num(x.get("min"));hi=x.get("max");pts=max(0,num(x.get("points")))
                    hi_val=None if hi in (None,"") else num(hi)
                    if hi_val is not None and hi_val<=lo:raise HTTPException(400,f"Rango inválido en {k}")
                    rows.append({"min":lo,"max":hi_val,"points":pts})
                clean[k]=rows
            out["bands"]=clean
        if b==6:
            mins=out.get("minimums") or {}
            out["minimums"]={k:(None if mins.get(k) in (None,"") else max(0,num(mins.get(k)))) for k,_,_ in CRITERIA}
            out["penalty_pct"]=clamp(out.get("penalty_pct",0),0,100)
            ws=out.get("weights") or base_weights
            out["weights"]={k:round(max(0,num(ws.get(k))),4) for k,_,_ in CRITERIA}
        return out

    @m.app.post("/api/bonuses-v302/config")
    async def save_bonus_config_v302(request:Request):
        actor=m.require_user(request,ADMIN);body=await request.json();b=int(body.get("bonus_no") or 0)
        if b not in BONUS_NOS:raise HTTPException(400,"Bono inválido")
        eff=month_key(body.get("effective_from"))
        cfg=validate_config(b,body.get("config") or {})
        with m.db() as con:
            ver=int(con.execute("SELECT COALESCE(MAX(version),0)+1 AS v FROM sales_bonus_model_versions_v302 WHERE bonus_no=?",(b,)).fetchone()["v"])
            con.execute("INSERT INTO sales_bonus_model_versions_v302(bonus_no,version,effective_from,active,config_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",
                (b,ver,eff,1 if cfg.get("active") else 0,json.dumps(cfg,ensure_ascii=False),now_iso(),str(actor.get("username") or "")))
            if bool(body.get("make_official")):
                ok,reason=config_ready(b,cfg)
                if not ok:raise HTTPException(400,f"No puede ser oficial: {reason}")
                con.execute("INSERT INTO sales_bonus_official_versions_v302(effective_from,bonus_no,changed_at,changed_by) VALUES(?,?,?,?)",
                    (eff,b,now_iso(),str(actor.get("username") or "")))
        return {"ok":True,"bonus_no":b,"version":ver,"effective_from":eff,"official_bonus":official_for(eff)}

    @m.app.post("/api/bonuses-v302/simulate")
    async def simulate_bonus_v302(request:Request):
        m.require_user(request);body=await request.json();b=int(body.get("bonus_no") or 1)
        if b not in BONUS_NOS:raise HTTPException(400,"Bono inválido")
        month=month_key(body.get("month"));cfg={**config_for(b,month),**(body.get("config") or {})}
        if b!=1:cfg=validate_config(b,cfg)
        inputs=body.get("inputs") or {};pcts={};steps=[]
        for k,label,_ in CRITERIA:
            item=inputs.get(k) or {};meta=num(item.get("meta"));real=num(item.get("result"))
            if meta<=0:
                pcts[k]=None;steps.append(f"{label}: meta cero/no válida → N/D")
            else:
                p=real/meta*100.0;pcts[k]=p;steps.append(f"{label}: ({real:g} / {meta:g}) × 100 = {p:.2f}%")
        b1=sum(clamp(pcts.get(k))*w/100 for k,_,w in CRITERIA if pcts.get(k) is not None)
        result=calc_model(b,pcts,cfg,b1,len([x for x in pcts.values() if x is not None])==3)
        return {"bonus_no":b,"result":result,"steps":steps+[result.get("formula") or ""],"simulation":True}

    # Prueba interna de aritmética sin datos reales.
    try:
        _t=calc_model(2,{"sales":100,"ddi":100,"attendance":100},defaults[2],100,True)
        assert abs(num(_t.get("points"))-100)<1e-6 and _t.get("ready")
        print("[V302-SELFTEST] engine=ok · Bono1 comercial identificado · Bono Operativo V279 intacto",flush=True)
    except Exception as exc:
        print(f"[V302-SELFTEST] failed: {type(exc).__name__}: {exc}",flush=True)
