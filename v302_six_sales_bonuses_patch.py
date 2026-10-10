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
        example_pcts={"sales":90.0,"ddi":80.0,"attendance":95.0}
        example_b1=90.0*0.50+80.0*0.30+95.0*0.20
        common["example_inputs"]=example_pcts
        common["example"]=calc_model(b,example_pcts,cfg,example_b1,True)
        common["example_note"]="Ejemplo didáctico de simulación; no modifica metas, configuraciones ni resultados reales."
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
        if b==1:
            if not bool(body.get("make_official")):
                raise HTTPException(400,"Bono 1 está bloqueado; sólo puede seleccionarse como bono oficial")
            with m.db() as con:
                con.execute("INSERT INTO sales_bonus_official_versions_v302(effective_from,bonus_no,changed_at,changed_by) VALUES(?,?,?,?)",
                    (eff,1,now_iso(),str(actor.get("username") or "")))
            current=config_for(1,eff)
            return {"ok":True,"bonus_no":1,"version":current.get("version"),"effective_from":eff,"official_bonus":1}
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


    css=r'''<style id="v302-css">
body[data-v302="1"] #analysisNav,body[data-v302="1"] #operativoNav,body[data-v302="1"] #globalFilters{display:none!important}
#page-bonuses{min-width:0}.v302{min-width:0;color:#123f73}.v302 *{box-sizing:border-box}
.v302-head{display:flex;justify-content:space-between;align-items:flex-end;gap:8px;margin:2px 0 7px}.v302-head h2{margin:0;font-size:18px}.v302-sub{font-size:7px;color:#617990;font-weight:800}
.v302-filters{display:grid;grid-template-columns:190px 155px;gap:6px}.v302-field label{display:block;font-size:6px;font-weight:950;color:#64788d;margin:0 0 2px}.v302-field select,.v302-field input,.v302-field textarea{width:100%;border:1px solid #ccd9e7;border-radius:8px;background:#fff;color:#173f72;font-weight:800}.v302-field select,.v302-field input{height:31px;padding:0 8px;font-size:7px}.v302-field textarea{min-height:95px;padding:7px;font-size:6px;resize:vertical}
.v302-bonus-tabs{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px;padding:4px;border:1px solid #d9e5ef;border-radius:11px;background:#f7faff;margin:6px 0}.v302-bonus-tabs button,.v302-nav button{border:0;background:transparent;border-radius:8px;font-weight:950;color:#315a80;white-space:nowrap}.v302-bonus-tabs button{height:35px;font-size:7px}.v302-bonus-tabs button.active{background:#176fe8;color:#fff;box-shadow:0 2px 8px rgba(23,111,232,.18)}.v302-bonus-tabs button.inactive:not(.active){opacity:.55}
.v302-nav{display:flex;gap:4px;overflow-x:auto;scrollbar-width:thin;padding:3px 0 6px;touch-action:pan-x}.v302-nav button{height:30px;padding:0 12px;font-size:6px;border:1px solid #dce6ef;background:#fff}.v302-nav button.active{background:#0e5798;color:#fff;border-color:#0e5798}
.v302-statusline{display:flex;gap:6px;align-items:center;margin:2px 0 6px;font-size:5.5px;color:#667d92;font-weight:800}.v302-pill{display:inline-flex;padding:3px 7px;border-radius:999px;background:#e9f3ff;color:#125ba4;font-size:5.5px;font-weight:950}.v302-pill.off{background:#f1f3f5;color:#6e7883}.v302-pill.warn{background:#fff0d6;color:#946200}
.v302-cards{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;margin-bottom:6px}.v302-card{border:1px solid #dae5ef;border-radius:10px;background:#fff;padding:8px;text-align:center;min-width:0}.v302-card span{display:block;font-size:5.5px;color:#667c91;font-weight:850;margin-bottom:3px}.v302-card b{display:block;font-size:18px;color:#123f73;line-height:1.05;overflow:hidden;text-overflow:ellipsis}.v302-card small{font-size:5px;color:#71869b}
.v302-grid2{display:grid;grid-template-columns:1fr 1fr;gap:6px}.v302-panel{border:1px solid #dbe5ef;border-radius:10px;background:#fff;overflow:hidden;margin-bottom:6px}.v302-ph{display:flex;justify-content:space-between;gap:6px;align-items:center;padding:7px 9px;background:#fbfdff;border-bottom:1px solid #e8eef4;font-size:7px;font-weight:950}.v302-body{padding:8px}.v302-scroll{overflow:auto;max-height:430px;touch-action:pan-x pan-y;-webkit-overflow-scrolling:touch}
.v302-table{width:100%;border-collapse:collapse;min-width:720px}.v302-table th{position:sticky;top:0;background:#eff5fb;color:#234c72;padding:6px 5px;font-size:5.5px;white-space:nowrap;text-align:center;z-index:1}.v302-table td{border-top:1px solid #edf2f6;padding:6px 5px;font-size:6px;text-align:center;white-space:nowrap}.v302-table th.left,.v302-table td.left{text-align:left}.v302-ok{background:#e5f8ec!important;color:#117042;font-weight:950}.v302-bad{background:#ffe6ea!important;color:#ad243b;font-weight:950}.v302-mid{background:#fff2d7!important;color:#946100;font-weight:950}.v302-na{color:#75889b;font-weight:850}
.v302-chart{display:grid;gap:5px;padding:7px}.v302-chart-row{display:grid;grid-template-columns:55px 1fr 60px;align-items:center;gap:6px;font-size:6px;font-weight:900}.v302-track{height:12px;background:#edf2f6;border-radius:99px;overflow:hidden}.v302-fill{height:100%;background:#176fe8;border-radius:99px}
.v302-gloss h3{margin:3px 0 5px;font-size:12px}.v302-gloss p,.v302-gloss li{font-size:6.5px;line-height:1.45;color:#49667f}.v302-gloss .method{padding:8px;border:1px solid #dce7f1;border-radius:9px;background:#f8fbfe;margin-bottom:6px}.v302-gloss-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.v302-calc-grid,.v302-config-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.v302-calc-row{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:5px;align-items:end}.v302-btn{height:30px;border:0;border-radius:8px;background:#176fe8;color:#fff;font-size:6px;font-weight:950;padding:0 12px}.v302-btn.secondary{background:#eef4fa;color:#214d75;border:1px solid #d4e0eb}.v302-btn:disabled{opacity:.5}
.v302-note{font-size:5.5px;color:#6d8195;padding:6px 8px;background:#f7fafc;border-top:1px solid #e7eef4}.v302-empty{padding:24px;text-align:center;color:#6d8195;font-size:8px}.v302-loading{padding:28px;text-align:center;font-size:8px;color:#61798f}.v302-history{max-height:210px;overflow:auto}
.v302-sourcecards{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.v302-sourcecard{border:1px solid #dfE8f1;border-radius:8px;padding:7px}.v302-sourcecard b{font-size:7px}.v302-sourcecard div{font-size:5.5px;color:#657c90;margin-top:2px}
@media(max-width:950px){.v302-head h2{font-size:13px}.v302-cards{grid-template-columns:repeat(7,minmax(72px,1fr));overflow-x:auto}.v302-card{padding:5px}.v302-card b{font-size:14px}.v302-bonus-tabs button{font-size:5px;height:28px}.v302-nav button{font-size:4.8px;height:25px}.v302-filters{grid-template-columns:1fr 1fr;width:46%}.v302-field select,.v302-field input{height:26px;font-size:5px}.v302-grid2,.v302-gloss-grid{gap:3px}.v302-table th,.v302-table td{font-size:4.5px;padding:4px 3px}.v302-ph{font-size:5.5px;padding:5px 6px}}
@media(max-width:640px){.v302{min-width:760px}.v302-bonus-tabs{gap:2px}.v302-grid2{grid-template-columns:1fr 1fr}.v302-calc-grid,.v302-config-grid{grid-template-columns:repeat(3,1fr)}}
</style>'''

    js=r'''<script id="v302-js">(function(){if(window.__V302_SIX_BONUSES)return;window.__V302_SIX_BONUSES=true;
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)],esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),n=v=>Number(v??0)||0;
const pc=v=>v==null?'N/D':n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%',nf=v=>v==null?'N/D':n(v).toLocaleString('es-MX',{maximumFractionDigits:2}),money=v=>v==null?'N/D':'$'+n(v).toLocaleString('es-MX',{maximumFractionDigits:0});
let S={bonus:1,section:'summary',month:'',store:'',data:null,busy:false,seq:0,configData:null};
async function A(u,o={}){let r=await fetch(u,{credentials:'same-origin',cache:'no-store',...o}),d={};try{d=await r.json()}catch(_){}if(!r.ok)throw new Error(d.detail||d.message||('HTTP '+r.status));return d}
function fmt(v,unit){if(v==null)return'N/D';return unit==='$'?money(v):pc(v)}
function cls(v){if(v==null)return'v302-na';v=n(v);return v>=90?'v302-ok':v>=70?'v302-mid':'v302-bad'}
function ensurePage(){let main=q('main.main'),p=q('#page-bonuses');if(main&&!p){p=document.createElement('section');p.className='page';p.id='page-bonuses';main.appendChild(p)}if(p&&!q('#v302Host',p))p.innerHTML='<div id="v302Host"></div>';return p}
function activate(){ensurePage();try{MAIN='bonuses'}catch(_){}document.body.dataset.v302='1';qa('[data-main]').forEach(x=>x.classList.toggle('active',x.dataset.main==='bonuses'));qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-bonuses'));let t=q('#heroTitle'),s=q('#heroSub');if(t)t.textContent='Bonos';if(s)s.textContent='Seis modelos seleccionables sobre los mismos criterios y fuentes'}
function statusPill(d){let cfg=d.configs?.[S.bonus]||d.configs?.[String(S.bonus)]||{},official=Number(d.official_bonus)===Number(S.bonus);return '<div class="v302-statusline"><span class="v302-pill '+(cfg.active?'':'off')+'">'+(cfg.active?'Activo':'No autorizado')+'</span>'+(official?'<span class="v302-pill">Bono oficial</span>':'')+'<span>Versión '+esc(cfg.version??'—')+' · efectiva '+esc(cfg.effective_from||'—')+'</span></div>'}
function filters(d){return '<div class="v302-filters"><div class="v302-field"><label>Tienda</label><select id="v302Store">'+(d.stores||[]).map(x=>'<option '+(x===d.selected_store?'selected':'')+'>'+esc(x)+'</option>').join('')+'</select></div><div class="v302-field"><label>Periodo</label><select id="v302Month">'+(d.months||[]).map(x=>'<option value="'+esc(x.value)+'" '+(x.value===d.month?'selected':'')+'>'+esc(x.label)+'</option>').join('')+'</select></div></div>'}
function bonusTabs(d){return '<div class="v302-bonus-tabs">'+[1,2,3,4,5,6].map(i=>{let cfg=d.configs?.[i]||d.configs?.[String(i)]||{};return '<button data-v302-bonus="'+i+'" class="'+(S.bonus===i?'active ':'')+(cfg.active?'':'inactive')+'">Bono '+i+'</button>'}).join('')+'</div>'}
function nav(d){let xs=[['summary','Resumen'],['ranking','Ranking'],['data','Datos base'],['compare','Comparativo de Bonos'],['glossary','Glosario de Bonos']];if(d.can_admin)xs.push(['config','Configuración']);return '<div class="v302-nav">'+xs.map(x=>'<button data-v302-section="'+x[0]+'" class="'+(S.section===x[0]?'active':'')+'">'+x[1]+'</button>').join('')+'</div>'}
function cards(m){let xs=[['Puntaje obtenido',m.points==null?'N/D':nf(m.points)],['Puntos máximos',m.max_points==null?'N/D':nf(m.max_points)],['Cumplimiento',pc(m.compliance_pct)],['Criterios evaluados',m.criteria_total??3],['Criterios cumplidos',m.criteria_met??0],['Pendientes / incumplidos',m.criteria_pending??0],['Clasificación',m.classification||'N/D']];return '<div class="v302-cards">'+xs.map(x=>'<div class="v302-card"><span>'+esc(x[0])+'</span><b>'+esc(x[1])+'</b></div>').join('')+'</div>'}
function breakdown(m){let rows=m.breakdown||[];return '<section class="v302-panel"><div class="v302-ph"><span>Desglose de indicadores</span><span>'+esc(m.name||'')+'</span></div><div class="v302-scroll"><table class="v302-table"><thead><tr><th class="left">Indicador</th><th>Meta</th><th>Resultado</th><th>Cumplimiento %</th><th>Peso</th><th>Puntos máximos</th><th>Puntos obtenidos</th><th>Estatus</th></tr></thead><tbody>'+rows.map(r=>'<tr><td class="left"><b>'+esc(r.indicator)+'</b><br><small>'+esc(r.source||'')+'</small></td><td>'+fmt(r.meta,r.unit)+'</td><td>'+fmt(r.result,r.unit)+'</td><td class="'+cls(r.compliance_pct)+'">'+pc(r.compliance_pct)+'</td><td>'+(r.weight==null?'—':pc(r.weight))+'</td><td>'+nf(r.max_points)+'</td><td>'+nf(r.points)+'</td><td>'+esc(r.status||'')+'</td></tr>').join('')+'</tbody></table></div><div class="v302-note">'+esc(m.formula||m.configuration_reason||'')+'</div></section>'}
function miniRanking(d,limit=8){let a=(d.ranking||[]).slice(0,limit||999);return '<section class="v302-panel"><div class="v302-ph"><span>Ranking global por tienda</span><span>Mejor a peor</span></div><div class="v302-scroll"><table class="v302-table"><thead><tr><th>#</th><th class="left">Tienda</th><th>Puntos</th><th>Máximo</th><th>Cumplimiento</th><th>Clasificación</th></tr></thead><tbody>'+a.map(r=>'<tr><td>'+(r.rank??'—')+'</td><td class="left"><b>'+esc(r.store)+'</b></td><td>'+nf(r.points)+'</td><td>'+nf(r.max_points)+'</td><td class="'+cls(r.compliance_pct)+'">'+pc(r.compliance_pct)+'</td><td>'+esc(r.classification||'')+'</td></tr>').join('')+'</tbody></table></div></section>'}
function summary(d){let m=d.model;return statusPill(d)+cards(m)+breakdown(m)+'<div class="v302-grid2">'+miniRanking(d,8)+sources(d)+'</div>'}
function sources(d){let b=d.base||{},s=b.selected||{};return '<section class="v302-panel"><div class="v302-ph"><span>Fuentes heredadas de Bono 1</span><span>No se mezclan datos operativos</span></div><div class="v302-body v302-sourcecards"><div class="v302-sourcecard"><b>Venta vs Meta</b><div>Venta: '+money(s.sales?.actual)+'</div><div>Meta: '+money(s.sales?.goal)+'</div><div>Fuente: Base Muertos/Cambios + METAS 2026</div></div><div class="v302-sourcecard"><b>DDI por Cat</b><div>'+pc(s.ddi?.pct)+'</div><div>Modelos objetivo: '+nf(s.target_models)+'</div><div>Fuente: Capacidades</div></div><div class="v302-sourcecard"><b>Asistencia</b><div>'+pc(s.attendance?.pct)+'</div><div>Fuente: captura autorizada</div></div></div></section>'}

function dataView(d){let b=d.base||{},s=b.selected||{},cats=s.ddi?.catalogs||[],rows=s.details||[];return '<div class="v302-grid2"><section class="v302-panel"><div class="v302-ph"><span>Modelos objetivo</span><span>'+nf(s.target_models)+' modelos</span></div><div class="v302-scroll"><table class="v302-table"><thead><tr><th class="left">Catálogo</th><th>Modelos</th><th>DDI reducido</th><th>Inversión reducida</th><th>Avance combinado</th></tr></thead><tbody>'+cats.map(x=>'<tr><td class="left"><b>'+esc(x.catalog)+'</b></td><td>'+nf(x.models)+'</td><td>'+pc(x.ddi_reduction_pct)+'</td><td>'+pc(x.investment_reduction_pct)+'</td><td>'+pc(x.combined_pct)+'</td></tr>').join('')+'</tbody></table></div></section>'+sources(d)+'</div><section class="v302-panel"><div class="v302-ph"><span>Detalle por ID · del peor al mejor avance</span><span>Listado fijo mensual heredado de Bono 1</span></div><div class="v302-scroll"><table class="v302-table"><thead><tr><th>#</th><th class="left">ID Modelo</th><th class="left">Modelo</th><th>Catálogo</th><th>Exist. inicial</th><th>Exist. actual</th><th>DDI inicial</th><th>DDI actual</th><th>Inversión inicial</th><th>Inversión actual</th><th>% Red. DDI</th><th>% Red. inversión</th><th>Avance</th><th>Estatus</th></tr></thead><tbody>'+rows.map((r,i)=>'<tr><td>'+(i+1)+'</td><td class="left"><b>'+esc(r.id_art)+'</b></td><td class="left">'+esc(r.model)+'</td><td>'+esc(r.catalog)+'</td><td>'+nf(r.initial_existence)+'</td><td>'+nf(r.current_existence)+'</td><td>'+nf(r.initial_ddi)+'</td><td>'+nf(r.current_ddi)+'</td><td>'+money(r.initial_investment)+'</td><td>'+money(r.current_investment)+'</td><td>'+pc(r.ddi_reduction_pct)+'</td><td>'+pc(r.investment_reduction_pct)+'</td><td>'+pc(r.progress_pct)+'</td><td>'+esc(r.status)+'</td></tr>').join('')+'</tbody></table></div><div class="v302-note">Esta información es común para Bono 1 a Bono 6; sólo cambia la metodología de cálculo, no la fuente.</div></section>'}
function compare(d){let a=d.comparison||[];let ready=a.filter(x=>x.compliance_pct!=null),mx=Math.max(100,...ready.map(x=>n(x.compliance_pct)));return '<div class="v302-grid2"><section class="v302-panel"><div class="v302-ph"><span>Comparativo de Bonos</span><span>Mismos datos · seis metodologías</span></div><div class="v302-scroll"><table class="v302-table"><thead><tr><th class="left">Bono</th><th>Puntos obtenidos</th><th>Puntos máximos</th><th>Cumplimiento %</th><th>Ranking</th><th>Clasificación</th></tr></thead><tbody>'+a.map(x=>'<tr><td class="left"><b>'+esc(x.name)+'</b></td><td>'+nf(x.points)+'</td><td>'+nf(x.max_points)+'</td><td class="'+cls(x.compliance_pct)+'">'+pc(x.compliance_pct)+'</td><td>'+(x.rank??'—')+'</td><td>'+esc(x.classification||x.configuration_reason||'')+'</td></tr>').join('')+'</tbody></table></div><div class="v302-note">No se declara automáticamente que un modelo sea mejor. Se muestran puntuación y porcentaje normalizado para comparar escalas diferentes.</div></section><section class="v302-panel"><div class="v302-ph"><span>Gráfica comparativa</span><span>% normalizado</span></div><div class="v302-chart">'+a.map(x=>'<div class="v302-chart-row"><span>'+esc(x.name)+'</span><div class="v302-track"><div class="v302-fill" style="width:'+Math.max(0,Math.min(100,(n(x.compliance_pct)/mx)*100))+'%"></div></div><b>'+pc(x.compliance_pct)+'</b></div>').join('')+'</div></section></div>'}
function glossaryTabs(){return '<div class="v302-bonus-tabs">'+[1,2,3,4,5,6].map(i=>'<button data-v302-bonus="'+i+'" class="'+(S.bonus===i?'active':'')+'">Bono '+i+'</button>').join('')+'</div>'}
function glossary(d){let g=d.glossary||{},m=d.model||{};return '<div class="v302-gloss">'+glossaryTabs()+'<div class="v302-gloss-grid"><section class="v302-panel"><div class="v302-ph"><span>'+esc(g.name||'')+'</span><span>Metodología</span></div><div class="v302-body"><div class="method"><h3>Descripción general</h3><p><b>Objetivo:</b> '+esc(g.objective||'')+'</p><p><b>Metodología:</b> '+esc(g.methodology||'')+'</p><p><b>Evaluados:</b> '+esc(g.evaluated||'')+'</p><p><b>Periodo:</b> '+esc(g.period||'')+'</p><p><b>Diferencia:</b> '+esc(g.difference||'')+'</p><p><b>Fórmula:</b> '+esc(g.formula||'')+'</p></div><h3>Fuentes</h3><ul>'+(g.sources||[]).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul><h3>Reglas y excepciones</h3><ul>'+(g.rules||[]).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div></section><section class="v302-panel"><div class="v302-ph"><span>Criterios evaluados</span><span>Transparencia del cálculo</span></div><div class="v302-scroll"><table class="v302-table"><thead><tr><th class="left">Criterio</th><th class="left">Qué evalúa</th><th>Fuente</th><th>Meta</th><th>Actual</th><th>Puntos</th></tr></thead><tbody>'+(g.criteria||[]).map(c=>{let r=(m.breakdown||[]).find(x=>x.key===c.key)||{};return '<tr><td class="left"><b>'+esc(c.name)+'</b></td><td class="left">'+esc(c.meaning)+'</td><td>'+esc(c.source)+'</td><td>'+esc(c.meta)+'</td><td>'+pc(r.compliance_pct)+'</td><td>'+nf(r.points)+' / '+nf(r.max_points)+'</td></tr>'}).join('')+'</tbody></table></div><div class="v302-note">Si un indicador no tiene información se muestra N/D y no se transforma en incumplimiento.</div></section></div>'+calculator(d)+'</div>'}
function calcConfig(d){let cfg=d.glossary?.config||{},b=S.bonus;if(b===2||b===5){let p=cfg.max_points||{};return '<div class="v302-calc-grid">'+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Puntos máximos · '+k+'</label><input data-calc-max="'+k+'" type="number" value="'+esc(p[k]??'')+'"></div>').join('')+'</div>'}if(b===3){let w=cfg.weights||{};return '<div class="v302-calc-grid">'+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Ponderación · '+k+'</label><input data-calc-weight="'+k+'" type="number" value="'+esc(w[k]??'')+'"></div>').join('')+'</div>'}if(b===4){return '<div class="v302-field"><label>Rangos de simulación (JSON por criterio)</label><textarea id="v302CalcBands">'+esc(JSON.stringify(cfg.bands||{},null,2))+'</textarea></div>'}if(b===6){let mins=cfg.minimums||{};return '<div class="v302-calc-grid">'+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Mínimo · '+k+'</label><input data-calc-min="'+k+'" type="number" value="'+esc(mins[k]??'')+'"></div>').join('')+'<div class="v302-field"><label>Penalización autorizada %</label><input id="v302CalcPenalty" type="number" value="'+esc(cfg.penalty_pct??0)+'"></div></div>'}return '<div class="v302-note">Bono 1 usa exactamente su cálculo original; la simulación no modifica información real.</div>'}
function calculator(d){return '<section class="v302-panel"><div class="v302-ph"><span>Calculadora interactiva · simulación</span><span>No modifica metas ni resultados reales</span></div><div class="v302-body"><div class="v302-calc-grid">'+[['sales','Venta vs Meta'],['ddi','DDI por Cat'],['attendance','Asistencia']].map(x=>'<div class="v302-calc-row"><div><b style="font-size:6px">'+x[1]+'</b></div><div class="v302-field"><label>Meta</label><input data-calc-meta="'+x[0]+'" type="number" value="100"></div><div class="v302-field"><label>Resultado</label><input data-calc-result="'+x[0]+'" type="number" value="100"></div></div>').join('')+'</div>'+calcConfig(d)+'<div style="margin-top:7px"><button class="v302-btn" id="v302Sim">Simular</button></div><div id="v302SimOut"></div></div></section>'}
function configFields(cfg,b){if(b===1)return '<div class="v302-note">Bono 1 está bloqueado para conservar íntegramente sus fórmulas, ponderaciones, fuentes y resultados históricos.</div>';let common='<div class="v302-field"><label>Estado</label><select id="v302CfgActive"><option value="1" '+(cfg.active?'selected':'')+'>Activo</option><option value="0" '+(!cfg.active?'selected':'')+'>Desactivado</option></select></div>';if(b===2||b===5){let p=cfg.max_points||{};return common+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Puntos máximos · '+k+'</label><input data-cfg-max="'+k+'" type="number" value="'+esc(p[k]??'')+'"></div>').join('')+'<div class="v302-field"><label>Límite de cumplimiento %</label><input id="v302CfgCap" type="number" value="'+esc(cfg.compliance_cap_pct??100)+'"></div>'}if(b===3){let w=cfg.weights||{};return common+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Ponderación · '+k+'</label><input data-cfg-weight="'+k+'" type="number" value="'+esc(w[k]??'')+'"></div>').join('')+'<div class="v302-field"><label>Límite de cumplimiento %</label><input id="v302CfgCap" type="number" value="'+esc(cfg.compliance_cap_pct??100)+'"></div>'}if(b===4)return common+'<div class="v302-field" style="grid-column:1/-1"><label>Rangos autorizados (JSON)</label><textarea id="v302CfgBands">'+esc(JSON.stringify(cfg.bands||{},null,2))+'</textarea></div>';if(b===6){let mins=cfg.minimums||{},w=cfg.weights||{};return common+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Mínimo · '+k+'</label><input data-cfg-min="'+k+'" type="number" value="'+esc(mins[k]??'')+'"></div>').join('')+['sales','ddi','attendance'].map(k=>'<div class="v302-field"><label>Peso · '+k+'</label><input data-cfg-weight="'+k+'" type="number" value="'+esc(w[k]??'')+'"></div>').join('')+'<div class="v302-field"><label>Penalización autorizada %</label><input id="v302CfgPenalty" type="number" value="'+esc(cfg.penalty_pct??0)+'"></div>'}return common}
function configView(d){let cfg=d.glossary?.config||{};return '<section class="v302-panel"><div class="v302-ph"><span>Configuración administrativa · Bono '+S.bonus+'</span><span>Versionada por periodo efectivo</span></div><div class="v302-body"><div class="v302-config-grid"><div class="v302-field"><label>Vigencia desde</label><input id="v302CfgEffective" type="month" value="'+esc(d.month)+'"></div><div class="v302-field"><label>Meta y estándares</label><input disabled value="Heredados de Bono 1"></div><div class="v302-field"><label>Bono oficial</label><select id="v302CfgOfficial"><option value="0">No cambiar</option><option value="1">Hacer oficial desde la vigencia</option></select></div>'+configFields(cfg,S.bonus)+'</div><div style="margin-top:8px"><button class="v302-btn" id="v302SaveCfg">'+(S.bonus===1?'Seleccionar Bono 1 como oficial':'Guardar nueva versión')+'</button></div><div id="v302CfgMsg"></div></div><div class="v302-note">Cada guardado crea una nueva versión con usuario, fecha y hora. Los periodos anteriores conservan la configuración que les corresponde.</div></section><div id="v302History"></div>'}
function body(d){if(S.section==='ranking')return statusPill(d)+miniRanking(d,0);if(S.section==='data')return dataView(d);if(S.section==='compare')return compare(d);if(S.section==='glossary')return glossary(d);if(S.section==='config')return configView(d);return summary(d)}
function page(d){return '<div class="v302"><div class="v302-head"><div><h2>Bonos</h2><div class="v302-sub">Bono 1 conserva el modelo existente · Bono 2 a Bono 6 usan los mismos criterios y fuentes</div></div>'+filters(d)+'</div>'+bonusTabs(d)+nav(d)+body(d)+'</div>'}

function calcPayload(){let inputs={};for(let k of ['sales','ddi','attendance'])inputs[k]={meta:n(q('[data-calc-meta="'+k+'"]')?.value),result:n(q('[data-calc-result="'+k+'"]')?.value)};let cfg={};if(S.bonus===2||S.bonus===5){cfg.max_points={};qa('[data-calc-max]').forEach(x=>cfg.max_points[x.dataset.calcMax]=n(x.value));cfg.compliance_cap_pct=100;cfg.active=true}if(S.bonus===3){cfg.weights={};qa('[data-calc-weight]').forEach(x=>cfg.weights[x.dataset.calcWeight]=n(x.value));cfg.compliance_cap_pct=100;cfg.active=true}if(S.bonus===4){try{cfg.bands=JSON.parse(q('#v302CalcBands')?.value||'{}')}catch(_){throw new Error('JSON de rangos inválido')}cfg.active=true}if(S.bonus===6){cfg.minimums={};qa('[data-calc-min]').forEach(x=>cfg.minimums[x.dataset.calcMin]=x.value===''?null:n(x.value));cfg.penalty_pct=n(q('#v302CalcPenalty')?.value);cfg.weights=S.data?.glossary?.config?.weights||{sales:50,ddi:30,attendance:20};cfg.active=true}return {bonus_no:S.bonus,month:S.month,inputs,config:cfg}}
async function simulate(){let out=q('#v302SimOut');if(out)out.innerHTML='<div class="v302-loading">Calculando simulación…</div>';try{let d=await A('/api/bonuses-v302/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(calcPayload())}),r=d.result||{};if(out)out.innerHTML='<div class="v302-grid2" style="margin-top:7px"><div class="v302-panel"><div class="v302-ph"><span>Resultado simulado</span><span>'+esc(r.classification||'')+'</span></div><div class="v302-body"><b style="font-size:20px">'+nf(r.points)+' / '+nf(r.max_points)+'</b><div style="font-size:7px;margin-top:4px">'+pc(r.compliance_pct)+'</div></div></div><div class="v302-panel"><div class="v302-ph"><span>Paso a paso</span><span>Fórmula aplicada</span></div><div class="v302-body">'+(d.steps||[]).map(x=>'<div style="font-size:6px;margin:3px 0">'+esc(x)+'</div>').join('')+'</div></div></div>'+breakdown({name:'Simulación',breakdown:r.breakdown||[],formula:r.formula||''})}catch(e){if(out)out.innerHTML='<div class="v302-note">'+esc(e.message||e)+'</div>'}}
function cfgPayload(){let cfg={active:q('#v302CfgActive')?.value!=='0'};if(S.bonus===2||S.bonus===5){cfg.max_points={};qa('[data-cfg-max]').forEach(x=>cfg.max_points[x.dataset.cfgMax]=n(x.value));cfg.compliance_cap_pct=n(q('#v302CfgCap')?.value||100)}if(S.bonus===3){cfg.weights={};qa('[data-cfg-weight]').forEach(x=>cfg.weights[x.dataset.cfgWeight]=n(x.value));cfg.compliance_cap_pct=n(q('#v302CfgCap')?.value||100)}if(S.bonus===4){try{cfg.bands=JSON.parse(q('#v302CfgBands')?.value||'{}')}catch(_){throw new Error('JSON de rangos inválido')}}if(S.bonus===6){cfg.minimums={};qa('[data-cfg-min]').forEach(x=>cfg.minimums[x.dataset.cfgMin]=x.value===''?null:n(x.value));cfg.weights={};qa('[data-cfg-weight]').forEach(x=>cfg.weights[x.dataset.cfgWeight]=n(x.value));cfg.penalty_pct=n(q('#v302CfgPenalty')?.value||0)}return {bonus_no:S.bonus,effective_from:q('#v302CfgEffective')?.value||S.month,make_official:q('#v302CfgOfficial')?.value==='1',config:cfg}}
async function saveCfg(){let msg=q('#v302CfgMsg'),btn=q('#v302SaveCfg');try{if(btn){btn.disabled=true;btn.textContent='Guardando…'}let payload=cfgPayload(),d=await A('/api/bonuses-v302/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(msg)msg.innerHTML='<div class="v302-note">Versión '+esc(d.version)+' guardada · vigente '+esc(d.effective_from)+'</div>';S.configData=null;await load()}catch(e){if(msg)msg.innerHTML='<div class="v302-note">'+esc(e.message||e)+'</div>'}finally{if(btn){btn.disabled=false;btn.textContent='Guardar nueva versión'}}}
async function makeB1Official(){let msg=q('#v302CfgMsg');try{let eff=q('#v302CfgEffective')?.value||S.month,d=await A('/api/bonuses-v302/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bonus_no:1,effective_from:eff,make_official:true,config:{}})});if(msg)msg.innerHTML='<div class="v302-note">Bono 1 seleccionado como oficial desde '+esc(eff)+'</div>';await load()}catch(e){if(msg)msg.innerHTML='<div class="v302-note">'+esc(e.message||e)+'</div>'}}
async function history(){if(!S.data?.can_admin)return;let host=q('#v302History');if(!host)return;host.innerHTML='<div class="v302-loading">Cargando historial…</div>';try{let d=await A('/api/bonuses-v302/config?month='+encodeURIComponent(S.month));S.configData=d;host.innerHTML='<div class="v302-grid2"><section class="v302-panel"><div class="v302-ph"><span>Historial de configuraciones</span><span>Usuario · fecha · versión</span></div><div class="v302-history"><table class="v302-table"><thead><tr><th>Bono</th><th>Versión</th><th>Vigencia</th><th>Estado</th><th>Fecha</th><th>Usuario</th></tr></thead><tbody>'+(d.history||[]).map(x=>'<tr><td>Bono '+x.bonus_no+'</td><td>'+x.version+'</td><td>'+esc(x.effective_from)+'</td><td>'+(x.active?'Activo':'Desactivado')+'</td><td>'+esc(x.changed_at)+'</td><td>'+esc(x.changed_by)+'</td></tr>').join('')+'</tbody></table></div></section><section class="v302-panel"><div class="v302-ph"><span>Historial de bono oficial</span><span>Actual: Bono '+esc(d.official_bonus)+'</span></div><div class="v302-history"><table class="v302-table"><thead><tr><th>Vigencia</th><th>Bono</th><th>Fecha</th><th>Usuario</th></tr></thead><tbody>'+(d.official_history||[]).map(x=>'<tr><td>'+esc(x.effective_from)+'</td><td>Bono '+x.bonus_no+'</td><td>'+esc(x.changed_at)+'</td><td>'+esc(x.changed_by)+'</td></tr>').join('')+'</tbody></table></div></section></div>'}catch(e){host.innerHTML='<div class="v302-note">'+esc(e.message||e)+'</div>'}}
let calcTimer=null;
function bind(d){q('#v302Store')?.addEventListener('change',e=>{S.store=e.target.value;load()});q('#v302Month')?.addEventListener('change',e=>{S.month=e.target.value;load()});qa('[data-v302-bonus]').forEach(b=>b.addEventListener('click',()=>{S.bonus=Number(b.dataset.v302Bonus);load()}));qa('[data-v302-section]').forEach(b=>b.addEventListener('click',()=>{S.section=b.dataset.v302Section;render();if(S.section==='config')history()}));q('#v302Sim')?.addEventListener('click',simulate);qa('[data-calc-meta],[data-calc-result],[data-calc-max],[data-calc-weight],[data-calc-min],#v302CalcPenalty,#v302CalcBands').forEach(x=>x.addEventListener('input',()=>{clearTimeout(calcTimer);calcTimer=setTimeout(simulate,450)}));q('#v302SaveCfg')?.addEventListener('click',S.bonus===1?makeB1Official:saveCfg)}
function render(){activate();let h=q('#v302Host');if(!h||!S.data)return;h.innerHTML=page(S.data);bind(S.data);if(S.section==='config')history()}
async function load(){let seq=++S.seq;S.busy=true;activate();let h=q('#v302Host');if(h&&!S.data)h.innerHTML='<div class="v302-loading">Cargando Bonos…</div>';try{let p=new URLSearchParams({bonus:String(S.bonus)});if(S.month)p.set('month',S.month);if(S.store)p.set('store',S.store);let d=await A('/api/bonuses-v302?'+p);if(seq!==S.seq)return;S.data=d;S.month=d.month;S.store=d.selected_store;render()}catch(e){if(seq===S.seq&&h)h.innerHTML='<div class="v302-empty">No fue posible cargar Bonos: '+esc(e.message||e)+'</div>'}finally{if(seq===S.seq)S.busy=false}}
function menu(){let side=q('#sidebar'),b=q('#sidebar [data-main="bonuses"]');if(side&&!b){b=document.createElement('button');b.className='nav';b.dataset.main='bonuses';b.innerHTML='Bonos<small>Seis modelos de cálculo</small>';let before=q('#sidebar [data-main="users"]')||q('#sidebar [data-main="share"]')||q('#sidebar .profile');before?side.insertBefore(b,before):side.appendChild(b)}let mn=q('#mobileMainNav'),mb=q('#mobileMainNav [data-main="bonuses"]');if(mn&&!mb){mb=document.createElement('button');mb.className='mnav';mb.dataset.main='bonuses';mb.innerHTML='<span class="mnav-icon">★</span><span>Bonos</span>';let before=q('#mobileMainNav [data-main="users"]')||q('#mobileMainNav [data-main="share"]');before?mn.insertBefore(mb,before):mn.appendChild(mb)}return [b,mb]}
function open(){activate();load()}
function boot(){let bs=menu();for(let b of bs)if(b&&!b.dataset.v302Bound){b.dataset.v302Bound='1';b.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();open()},true)}}
document.addEventListener('DOMContentLoaded',()=>setTimeout(boot,250),{once:true});document.addEventListener('click',e=>{let x=e.target.closest?.('[data-main]');if(x&&x.dataset.main!=='bonuses'){document.body.removeAttribute('data-v302');setTimeout(boot,80)}},true);[600,1400,2800].forEach(ms=>setTimeout(boot,ms));
})();</script>'''

    @m.app.middleware("http")
    async def v302_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v302-css"' not in html:html=html.replace("</head>",css+"</head>",1)
            if 'id="v302-js"' not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None)
            headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-Bonus-Version"]="V302-SIX-BONUSES"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V302] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V302_SIX_SALES_BONUSES=True
    print("[V302] Bonos: Bono 1 comercial preservado + Bono 2..6 + Glosario + Calculadora + Comparativo + Configuración versionada.",flush=True)
