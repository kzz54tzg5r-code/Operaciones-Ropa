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
