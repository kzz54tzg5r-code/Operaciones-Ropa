"""V312 · Bonos por Venta finales seleccionados.

- Bono 1 permanece exactamente con su cálculo V293.
- Bono 2 conserva la opción elegida: Meta >=100% + reducción DDI mínima 50%, escalonada.
- Bono 3 conserva la opción elegida: rubros críticos Abrigador/Licencias/Básicos, 2 de 3.
- Bono 4: matriz integral de inventario.
- Bono 5: mejora contra sí misma vs periodo anterior.
- Bono 6: cumplimiento sostenido en cuatro cortes semanales.
- Asistencia es sólo referencia en Bono 2..6; 1 falta descalifica al colaborador en validación individual.
- El costo del bono se calcula fuera de este módulo.
"""
from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX=ZoneInfo("America/Mexico_City")
BONUS_NOS=(1,2,3,4,5,6)
CATALOGS=("Abrigador","Licencias","Básicos")
ADMIN=("superadmin","admin")
B4_TARGETS={"ddi_reduction_pct":50.0,"existence_reduction_pct":30.0,"investment_reduction_pct":30.0,"models_reduction_pct":20.0}
B4_WEIGHTS={"ddi_reduction_pct":30.0,"existence_reduction_pct":25.0,"investment_reduction_pct":25.0,"models_reduction_pct":20.0}
B4_SCORE_MIN=80.0
B3_RUBRO_MIN=50.0
B3_RUBROS_REQUIRED=2
B6_WEEKS_REQUIRED=4

def install(m):
    if getattr(m,"_V312_FINAL_SALES_BONUSES",False):
        return

    def num(v,default=0.0):
        try:
            x=float(v)
            return x if math.isfinite(x) else default
        except Exception:
            return default

    def maybe(v):
        try:
            if v is None:return None
            x=float(v)
            return x if math.isfinite(x) else None
        except Exception:
            return None

    def clamp(v,lo=0.0,hi=100.0):
        return max(lo,min(hi,num(v)))

    def month_key(v):
        s=str(v or "").strip()
        if len(s)==7 and s[4]=="-":
            try:
                y=int(s[:4]);mm=int(s[5:7])
                if 1<=mm<=12:return f"{y:04d}-{mm:02d}"
            except Exception:pass
        n=datetime.now(MX)
        return f"{n.year:04d}-{n.month:02d}"

    def prev_month(v):
        y,mm=(int(x) for x in month_key(v).split("-"))
        mm-=1
        if mm<1:y-=1;mm=12
        return f"{y:04d}-{mm:02d}"

    def base_endpoint():
        for route in getattr(m.app,"routes",[]):
            if getattr(route,"path","")=="/api/operation/sales-bonus-v293":
                return getattr(route,"endpoint",None)
        return None

    def base_payload(request,month,store=""):
        endpoint=base_endpoint()
        if endpoint is None:
            raise HTTPException(503,"La base de Bonos no está disponible")
        return endpoint(request=request,month=month,store=store)

    def row_map(base):
        return {str(x.get("store") or ""):dict(x) for x in (base.get("ranking") or [])}

    def inventory(row):
        return dict((row or {}).get("inventory") or {})

    def catalog_map(row):
        return {str(x.get("catalog") or ""):dict(x) for x in ((row or {}).get("catalogs") or [])}

    def sales_ok(row):
        p=maybe((row or {}).get("sales_pct"))
        return p is not None and p>=100.0

    def b2_level(ddi):
        if ddi is None or ddi<50:return 0
        if ddi<60:return 1
        if ddi<75:return 2
        if ddi<90:return 3
        return 4

    def evaluate(b,row,prior=None,weeks=None):
        sales=maybe((row or {}).get("sales_pct"))
        inv=inventory(row)
        att=maybe((row or {}).get("attendance_pct"))
        out={
            "bonus_no":b,"store":str((row or {}).get("store") or ""),"sales_pct":sales,
            "attendance_reference":att,"attendance_scored":False,
            "attendance_rule":"Sólo referencia. La validación es individual: 1 falta descalifica al colaborador.",
            "cost_included":False,"inventory":inv,"eligible":False,"ready":True,
            "classification":"No habilitada","indicator":None,"level":None,"extra":{}
        }
        if b==1:
            ready=bool((row or {}).get("score_ready"))
            score=maybe((row or {}).get("score"))
            out.update({
                "eligible":ready and score is not None,
                "ready":ready,"classification":"Resultado original" if ready else "Información incompleta",
                "indicator":score,"score":score,"formula":"Cálculo original V293 sin cambios: 50% Venta + 30% DDI por Cat + 20% Asistencia.",
                "attendance_scored":True
            })
            return out

        if sales is None:
            out.update(ready=False,classification="Información incompleta")
            return out

        if b==2:
            ddi=maybe(inv.get("ddi_reduction_pct"))
            level=b2_level(ddi)
            ok=sales>=100 and ddi is not None and ddi>=50
            out.update(
                ready=ddi is not None,eligible=ok,classification="Habilitada" if ok else ("No habilitada" if ddi is not None else "Información incompleta"),
                indicator=ddi,level=level,
                formula="Venta >=100% + reducción DDI mínima 50%. DDI define el escalón: 50–59, 60–74, 75–89, >=90%.",
                extra={"ddi_reduction_pct":ddi,"level":level}
            )
            return out

        if b==3:
            cats=catalog_map(row)
            rubros={}
            met=0
            available=0
            for c in CATALOGS:
                cr=cats.get(c) or {}
                val=maybe(cr.get("ddi_days_reduction_pct"))
                models=int(num(cr.get("models"),0))
                if models>0 and val is not None:
                    available+=1
                    if val>=B3_RUBRO_MIN:met+=1
                rubros[c]={"reduction_pct":val,"models":models,"meets":bool(models>0 and val is not None and val>=B3_RUBRO_MIN)}
            ready=available>=B3_RUBROS_REQUIRED
            ok=sales>=100 and ready and met>=B3_RUBROS_REQUIRED
            avg=(sum(x["reduction_pct"] for x in rubros.values() if x["reduction_pct"] is not None)/available) if available else None
            out.update(
                ready=ready,eligible=ok,classification="Habilitada" if ok else ("No habilitada" if ready else "Información incompleta"),
                indicator=avg,level=met,
                formula="Venta >=100% y al menos 2 de 3 rubros críticos con reducción DDI >=50%.",
                extra={"rubros":rubros,"rubros_met":met,"rubros_available":available}
            )
            return out

        if b==4:
            parts={}
            complete=True
            score=0.0
            for k,target in B4_TARGETS.items():
                val=maybe(inv.get(k))
                if val is None:
                    complete=False
                    comp=None
                    pts=None
                else:
                    comp=clamp(max(0.0,val)/target*100.0)
                    pts=comp*B4_WEIGHTS[k]/100.0
                    score+=pts
                parts[k]={"value":val,"target":target,"weight":B4_WEIGHTS[k],"compliance_pct":comp,"points":pts}
            ok=sales>=100 and complete and score>=B4_SCORE_MIN
            out.update(
                ready=complete,eligible=ok,classification="Habilitada" if ok else ("No habilitada" if complete else "Información incompleta"),
                indicator=round(score,1) if complete else None,level=(4 if score>=90 else 3 if score>=80 else 2 if score>=60 else 1),
                formula="Venta >=100% + matriz: DDI 30%, Existencia 25%, Inversión 25%, Modelos 20%. Score mínimo 80.",
                extra={"matrix":parts,"score":round(score,1) if complete else None}
            )
            return out

        if b==5:
            pinv=inventory(prior)
            keys=("ddi_reduction_pct","existence_reduction_pct","investment_reduction_pct","models_reduction_pct")
            changes={}
            improved=0
            complete=True
            for k in keys:
                cur=maybe(inv.get(k));old=maybe(pinv.get(k))
                if cur is None or old is None:
                    complete=False;delta=None;better=False
                else:
                    delta=cur-old;better=delta>0
                    if better:improved+=1
                changes[k]={"previous":old,"current":cur,"delta":delta,"improved":better}
            ok=sales>=100 and complete and improved>=3
            out.update(
                ready=complete,eligible=ok,classification="Habilitada" if ok else ("No habilitada" if complete else "Información incompleta"),
                indicator=(improved/4*100.0) if complete else None,level=improved,
                formula="Venta >=100% + mejora vs periodo anterior en al menos 3 de 4 indicadores: DDI, Existencia, Inversión y Modelos.",
                extra={"changes":changes,"improved":improved,"previous_month":prev_month((prior or {}).get("month") or "")}
            )
            return out

        series=list(weeks or [])[-B6_WEEKS_REQUIRED:]
        checks=[]
        for point in series:
            wi=dict(point.get("inventory") or {})
            pass_week=all(maybe(wi.get(k)) is not None and maybe(wi.get(k))>=target for k,target in B4_TARGETS.items())
            checks.append({"week":point.get("week"),"date":point.get("date"),"inventory":wi,"meets":pass_week})
        complete=len(checks)>=B6_WEEKS_REQUIRED
        streak=0
        for x in reversed(checks):
            if x["meets"]:streak+=1
            else:break
        ok=sales>=100 and complete and streak>=B6_WEEKS_REQUIRED
        out.update(
            ready=complete,eligible=ok,classification="Habilitada" if ok else ("No habilitada" if complete else "Información incompleta"),
            indicator=(streak/B6_WEEKS_REQUIRED*100.0) if complete else None,level=streak,
            formula="Venta >=100% + 4 cortes semanales consecutivos cumpliendo objetivos de DDI, Existencia, Inversión y Modelos.",
            extra={"weeks":checks,"streak":streak,"required_weeks":B6_WEEKS_REQUIRED}
        )
        return out

    def company_summary(base,evaluated,b):
        rows=list(base.get("ranking") or [])
        actual=sum(num(x.get("sales_actual")) for x in rows)
        goal=sum(num(x.get("sales_goal")) for x in rows)
        sales_pct=(actual/goal*100.0) if goal>0 else None
        invs=[inventory(x) for x in rows]
        def avg(k):
            vals=[maybe(x.get(k)) for x in invs]
            vals=[x for x in vals if x is not None]
            return round(sum(vals)/len(vals),1) if vals else None
        atts=[maybe(x.get("attendance_pct")) for x in rows]
        atts=[x for x in atts if x is not None]
        out={
            "sales_pct":None if sales_pct is None else round(sales_pct,1),
            "stores_total":len(rows),
            "stores_sales_100":sum(1 for x in rows if maybe(x.get("sales_pct")) is not None and num(x.get("sales_pct"))>=100),
            "stores_enabled":sum(1 for x in evaluated if x.get("eligible")),
            "attendance_reference":round(sum(atts)/len(atts),1) if atts else None,
            "inventory":{
                "initial_ddi":avg("initial_ddi"),"current_ddi":avg("current_ddi"),
                "ddi_reduction_pct":avg("ddi_reduction_pct"),"existence_reduction_pct":avg("existence_reduction_pct"),
                "investment_reduction_pct":avg("investment_reduction_pct"),"models_reduction_pct":avg("models_reduction_pct")
            }
        }
        if b==3:
            rubros={}
            for c in CATALOGS:
                vals=[]
                for e in evaluated:
                    v=((e.get("extra") or {}).get("rubros") or {}).get(c,{}).get("reduction_pct")
                    if v is not None:vals.append(num(v))
                rubros[c]=round(sum(vals)/len(vals),1) if vals else None
            out["rubros"]=rubros
        if b==4:
            vals=[maybe((e.get("extra") or {}).get("score")) for e in evaluated]
            vals=[x for x in vals if x is not None]
            out["score_avg"]=round(sum(vals)/len(vals),1) if vals else None
        if b==5:
            vals=[int((e.get("extra") or {}).get("improved") or 0) for e in evaluated if e.get("ready")]
            out["improved_avg"]=round(sum(vals)/len(vals),1) if vals else None
            ch={}
            for k in ("ddi_reduction_pct","existence_reduction_pct","investment_reduction_pct","models_reduction_pct"):
                cur=[];prev=[]
                for e in evaluated:
                    q=((e.get("extra") or {}).get("changes") or {}).get(k) or {}
                    if q.get("current") is not None:cur.append(num(q.get("current")))
                    if q.get("previous") is not None:prev.append(num(q.get("previous")))
                ch[k]={"current":round(sum(cur)/len(cur),1) if cur else None,"previous":round(sum(prev)/len(prev),1) if prev else None}
            out["changes"]=ch
        if b==6:
            dist={0:0,1:0,2:0,3:0,4:0}
            for e in evaluated:
                s=int((e.get("extra") or {}).get("streak") or 0)
                dist[max(0,min(4,s))]+=1
            out["streak_distribution"]=dist
        return out

    @m.app.get("/api/bonuses-v312")
    def bonuses_v312(request:Request,month:str="",store:str="Compañía",bonus:int=2):
        actor=m.require_user(request)
        month=month_key(month)
        b=int(bonus or 2)
        if b not in BONUS_NOS:b=2
        requested=str(store or "Compañía")
        base=base_payload(request,month,"" if requested=="Compañía" else requested)
        current=row_map(base)
        stores=list(base.get("stores") or [])
        prior={}
        if b==5:
            try:
                pbase=base_payload(request,prev_month(month),"")
                prior=row_map(pbase)
                for x in prior.values():x["month"]=prev_month(month)
            except Exception:
                prior={}
        weekly={}
        weekly_pending=False
        if b==6 and hasattr(m,"_sales_bonus_weekly_inventory_v293"):
            try:
                w=m._sales_bonus_weekly_inventory_v293(month,stores)
                weekly=dict(w.get("stores") or {})
                weekly_pending=bool(w.get("pending"))
            except Exception as exc:
                print(f"[V312] Weekly warning: {type(exc).__name__}: {exc}",flush=True)
        evaluated=[]
        for s in stores:
            row=current.get(s) or {"store":s}
            e=evaluate(b,row,prior.get(s),weekly.get(s))
            evaluated.append(e)
        evaluated.sort(key=lambda x:(not x.get("eligible"),not x.get("ready"),-(num(x.get("indicator"))),str(x.get("store") or "")))
        for i,e in enumerate(evaluated,1):
            e["rank"]=i if e.get("ready") else None
        selected_store=requested if requested in stores else "Compañía"
        selected_eval=next((x for x in evaluated if x.get("store")==selected_store),None)
        selected_base=(base.get("selected") if selected_store!="Compañía" else None)
        if selected_store!="Compañía" and str((base.get("selected") or {}).get("store") or "")!=selected_store:
            b2=base_payload(request,month,selected_store)
            selected_base=b2.get("selected")
        summary=company_summary(base,evaluated,b) if selected_store=="Compañía" else {
            "sales_pct":selected_eval.get("sales_pct") if selected_eval else None,
            "stores_total":1,"stores_sales_100":1 if selected_eval and num(selected_eval.get("sales_pct"))>=100 else 0,
            "stores_enabled":1 if selected_eval and selected_eval.get("eligible") else 0,
            "attendance_reference":selected_eval.get("attendance_reference") if selected_eval else None,
            "inventory":selected_eval.get("inventory") if selected_eval else {}
        }
        if selected_store!="Compañía" and selected_eval:
            if b==3:summary["rubros"]={c:((selected_eval.get("extra") or {}).get("rubros") or {}).get(c,{}).get("reduction_pct") for c in CATALOGS}
            if b==4:summary["score_avg"]=(selected_eval.get("extra") or {}).get("score")
            if b==5:summary["changes"]=(selected_eval.get("extra") or {}).get("changes")
            if b==6:
                dist={0:0,1:0,2:0,3:0,4:0};dist[int((selected_eval.get("extra") or {}).get("streak") or 0)]=1;summary["streak_distribution"]=dist
        state=getattr(request,"state",None)
        if state is not None:state.bonus_base_v312=base
        role=str(actor.get("role") or "").lower()
        return {
            "version":"V312-FINAL-BONUS-METHODS","month":month,"bonus_no":b,
            "selected_store":selected_store,"stores":["Compañía"]+stores,
            "months":base.get("months") or [],"can_admin":role in ADMIN,
            "summary":summary,"ranking":evaluated,"selected":selected_eval,
            "details":(selected_base or {}).get("details") or [],
            "catalogs":((selected_base or {}).get("ddi") or {}).get("catalogs") or [],
            "weekly_pending":weekly_pending,
            "rules":{
                "attendance":"Asistencia sólo de referencia en Bono 2–6. Validación individual posterior: 1 falta descalifica.",
                "cost":"El costo del bono se calcula aparte y no forma parte de estos indicadores.",
                "sales":"Meta de venta >=100% obligatoria en Bono 2–6.",
                "ddi":"Reducción DDI mínima 50% donde aplique."
            }
        }

    css=r'''<style id="v312-css">
body[data-v312="1"] #analysisNav,body[data-v312="1"] #operativoNav,body[data-v312="1"] #globalFilters{display:none!important}
.v312{font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:#0c2f66;max-width:1600px;margin:0 auto}
.v312 *{box-sizing:border-box}.v312-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-end;margin-bottom:8px}
.v312 h2{margin:0;font-size:22px}.v312-sub{font-size:11px;color:#6b7e95}.v312-filters{display:flex;gap:8px}
.v312-field label{display:block;font-size:9px;font-weight:800;color:#6b7e95;margin-bottom:2px}.v312-field select{height:30px;border:1px solid #cbd8e8;border-radius:7px;background:#fff;padding:0 28px 0 8px;color:#12335c;font-weight:700}
.v312-bonus,.v312-tabs{display:grid;grid-template-columns:repeat(6,1fr);gap:5px;margin:7px 0}.v312-tabs{grid-template-columns:repeat(4,1fr)}
.v312-bonus button,.v312-tabs button,.v312-subtabs button{border:1px solid #d7e3f1;background:#fff;border-radius:7px;height:31px;font-size:10px;font-weight:900;color:#1d4a80}
.v312-bonus button.active,.v312-tabs button.active,.v312-subtabs button.active{background:#0d6efd;color:#fff;border-color:#0d6efd}
.v312-method{background:linear-gradient(90deg,#0755b6,#0d74e8);color:white;border-radius:9px;padding:9px 12px;display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:8px}
.v312-method b{font-size:13px}.v312-method span{font-size:10px;opacity:.95}.v312-pill{background:#e7f6ed;color:#158447;border-radius:99px;padding:4px 8px;font-size:9px;font-weight:900;white-space:nowrap}
.v312-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.v312-card,.v312-panel{background:#fff;border:1px solid #d8e4f0;border-radius:9px;box-shadow:0 2px 7px rgba(13,69,127,.06)}
.v312-card{padding:8px;min-height:78px}.v312-card span{display:block;font-size:9px;font-weight:800;color:#516c8b}.v312-card b{display:block;font-size:19px;color:#0a3671;margin-top:5px}.v312-card small{display:block;font-size:8px;margin-top:4px;color:#7190ad}
.v312-good{color:#16a05d!important}.v312-bad{color:#e13a47!important}.v312-warn{color:#e6a21a!important}
.v312-layout{display:grid;grid-template-columns:1.35fr .85fr;gap:7px;margin-top:7px}.v312-panel{overflow:hidden}.v312-ph{padding:7px 9px;border-bottom:1px solid #e3ebf4;font-size:10px;font-weight:900;display:flex;justify-content:space-between;gap:10px}.v312-body{padding:9px}
.v312-rules{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.v312-rule{border:1px solid #dce7f3;border-radius:8px;padding:8px;font-size:9px;line-height:1.35}.v312-rule b{display:block;color:#095dc5;margin-bottom:3px}
.v312-bars{display:flex;align-items:flex-end;gap:10px;min-height:145px;padding:12px 8px 4px}.v312-barcol{flex:1;text-align:center;font-size:8px;color:#5c7290}.v312-bar{height:105px;display:flex;align-items:flex-end;justify-content:center;gap:3px;border-bottom:1px solid #d6e1ec}.v312-bar i{display:block;width:24px;min-height:2px;border-radius:4px 4px 0 0;background:#0d6efd}.v312-bar i.alt{background:#7b4be8}.v312-barcol b{display:block;font-size:10px;margin-top:4px}
.v312-levels{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}.v312-level{padding:9px 5px;border-radius:7px;text-align:center;background:#edf5ff;font-size:8px}.v312-level b{display:block;font-size:16px;color:#0756b5}.v312-level.off{background:#fff0f1}.v312-level.l1{background:#e8f8ed}.v312-level.l2{background:#e6f2ff}.v312-level.l3{background:#ece8ff}.v312-level.l4{background:#d9e8ff}
.v312-scroll{overflow:auto;max-width:100%;-webkit-overflow-scrolling:touch}.v312-table{width:100%;border-collapse:collapse;font-size:9px;white-space:nowrap}.v312-table th{background:#f3f7fb;color:#315575}.v312-table th,.v312-table td{padding:5px 6px;border-bottom:1px solid #edf1f5;text-align:center}.v312-table .left{text-align:left}.v312-status{display:inline-block;border-radius:99px;padding:3px 7px;font-weight:900;background:#e8f7ed;color:#14894d}.v312-status.no{background:#feecef;color:#d93949}.v312-status.na{background:#eef2f6;color:#758394}
.v312-progress{height:8px;background:#edf2f6;border-radius:99px;overflow:hidden}.v312-progress i{display:block;height:100%;background:#0d6efd;border-radius:99px}
.v312-matrix{display:grid;grid-template-columns:1.1fr repeat(4,1fr);font-size:9px}.v312-matrix div{padding:7px;border-bottom:1px solid #edf1f5}.v312-matrix .h{font-weight:900;background:#f3f7fb}.v312-check{width:18px;height:18px;border-radius:5px;margin:auto;display:flex;align-items:center;justify-content:center;background:#e9f8ee;color:#159558;font-weight:900}.v312-check.no{background:#ffedef;color:#d93647}
.v312-subtabs{display:flex;gap:5px;margin:7px 0}.v312-note{font-size:9px;padding:7px 9px;background:#eef6ff;border-radius:7px;color:#3d5e82;margin-top:7px}.v312-att{background:#fff9e7;color:#946a00}.v312-model-title{font-size:11px;font-weight:900;margin:8px 0}
@media(max-width:900px){.v312{min-width:980px;transform-origin:top left}.v312-grid{grid-template-columns:repeat(7,minmax(120px,1fr))}.v312-head{align-items:flex-start}.v312-layout{grid-template-columns:1.25fr .85fr}}
</style>'''

    js=r'''<script id="v312-js">(function(){
if(window.__V312_FINAL_BONUSES)return;window.__V312_FINAL_BONUSES=true;
var S={bonus:2,section:"summary",store:"Compañía",month:"",catalog:"Abrigador",data:null,seq:0};
function q(s,r){return(r||document).querySelector(s)}function qa(s,r){return Array.from((r||document).querySelectorAll(s))}
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c]})}
function n(v){var x=Number(v);return Number.isFinite(x)?x:0}function pc(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{maximumFractionDigits:1})+"%"}
function nf(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{maximumFractionDigits:1})}
function api(url){return fetch(url,{credentials:"same-origin"}).then(function(r){if(!r.ok)return r.text().then(function(t){throw new Error(t||("HTTP "+r.status))});return r.json()})}
function ensure(){var main=q("main.main"),p=q("#page-bonuses");if(main&&!p){p=document.createElement("section");p.className="page";p.id="page-bonuses";main.appendChild(p)}if(p&&!q("#v312Host",p))p.innerHTML="<div id=\"v312Host\"></div>";return p}
function activate(){ensure();try{MAIN="bonuses"}catch(_e){}document.body.dataset.v312="1";document.body.removeAttribute("data-v302");qa("[data-main]").forEach(function(x){x.classList.toggle("active",x.dataset.main==="bonuses")});qa(".page").forEach(function(x){x.classList.toggle("active",x.id==="page-bonuses")});var t=q("#heroTitle"),s=q("#heroSub");if(t)t.textContent="Bonos";if(s)s.textContent="Indicadores para habilitar el bono de colaboradores"}
function filters(d){return "<div class=\"v312-filters\"><div class=\"v312-field\"><label>Periodo</label><select id=\"v312Month\">"+(d.months||[]).map(function(x){return"<option value=\""+esc(x.value)+"\" "+(x.value===d.month?"selected":"")+">"+esc(x.label)+"</option>"}).join("")+"</select></div><div class=\"v312-field\"><label>Tienda</label><select id=\"v312Store\">"+(d.stores||[]).map(function(x){return"<option "+(x===d.selected_store?"selected":"")+">"+esc(x)+"</option>"}).join("")+"</select></div></div>"}
function bonusTabs(){return"<div class=\"v312-bonus\">"+[1,2,3,4,5,6].map(function(i){return"<button data-v312-bonus=\""+i+"\" class=\""+(S.bonus===i?"active":"")+"\">Bono "+i+"</button>"}).join("")+"</div>"}
function tabs(){var xs=[["summary","Resumen General"],["ranking","Ranking de Tiendas"],["panorama","Panorama por Tienda"],["models","Modelos a Detalle"]];return"<div class=\"v312-tabs\">"+xs.map(function(x){return"<button data-v312-section=\""+x[0]+"\" class=\""+(S.section===x[0]?"active":"")+"\">"+x[1]+"</button>"}).join("")+"</div>"}
function method(d){var names={1:"Modelo actual · sin cambios",2:"Reducción de DDI · escalonado",3:"Rubros críticos · opción elegida",4:"Matriz integral de indicadores",5:"Mejora contra sí misma",6:"Cumplimiento sostenido"};var f=(d.selected&&d.selected.formula)||({1:"Cálculo original V293.",2:"Venta >=100% y DDI baja al menos 50%.",3:"Venta >=100% y 2 de 3 rubros críticos.",4:"Venta >=100% y score integral >=80.",5:"Venta >=100% y mejora en 3 de 4 indicadores.",6:"Venta >=100% y 4 semanas consecutivas."})[S.bonus];return"<div class=\"v312-method\"><div><b>Bono "+S.bonus+" · "+esc(names[S.bonus])+"</b><br><span>"+esc(f)+"</span></div><span class=\"v312-pill\">Costo del bono: cálculo aparte</span></div>"}
function card(label,value,note,cls){return"<div class=\"v312-card\"><span>"+esc(label)+"</span><b class=\""+(cls||"")+"\">"+esc(value)+"</b><small>"+esc(note||"")+"</small></div>"}
function baseCards(d){var s=d.summary||{},inv=s.inventory||{},out=[];out.push(card("Venta vs Meta",pc(s.sales_pct),"Meta mínima 100%",n(s.sales_pct)>=100?"v312-good":"v312-bad"));out.push(card("Tiendas que cumplen 100%",nf(s.stores_sales_100)+" de "+nf(s.stores_total),"Puerta obligatoria"));if(S.bonus===1){out.push(card("DDI por Cat","Ver cálculo original","Sin cambios"));out.push(card("Tiendas evaluadas",nf(s.stores_total),"Bono 1"));out.push(card("Tiendas con resultado",nf((d.ranking||[]).filter(function(x){return x.ready}).length),"Cálculo V293"));out.push(card("Asistencia","Incluida","Sólo Bono 1"));out.push(card("Bono 1","Original","Sin cambios"));return out.join("")}out.push(card("DDI inicial",nf(inv.initial_ddi),"Promedio cartera"));out.push(card("DDI final",nf(inv.current_ddi),"Promedio cartera"));if(S.bonus===2)out.push(card("% reducción DDI",pc(inv.ddi_reduction_pct),"Mínimo 50%",n(inv.ddi_reduction_pct)>=50?"v312-good":"v312-bad"));else if(S.bonus===3)out.push(card("Tiendas habilitadas",nf(s.stores_enabled)+" de "+nf(s.stores_total),"Cumplen rubros"));else if(S.bonus===4)out.push(card("Score integral",pc(s.score_avg),"Mínimo 80 pts",n(s.score_avg)>=80?"v312-good":"v312-bad"));else if(S.bonus===5)out.push(card("Indicadores mejorados",nf(s.improved_avg)+" de 4","Promedio"));else out.push(card("Tiendas habilitadas",nf(s.stores_enabled)+" de "+nf(s.stores_total),"Racha requerida"));out.push(card("Colaboradores potenciales","Por validar","Asistencia individual posterior"));out.push(card("Asistencia (referencia)",pc(s.attendance_reference),"No suma puntos · 1 falta descalifica","v312-warn"));return out.join("")}
function rules(d){var r=d.rules||{};var two=S.bonus===2?"DDI debe bajar mínimo 50% desde el valor inicial.":S.bonus===3?"Abrigador, Licencias y Básicos: mínimo 50% de reducción DDI; cumplir 2 de 3.":S.bonus===4?"Matriz: DDI 30%, Existencia 25%, Inversión 25%, Modelos 20%; score >=80.":S.bonus===5?"Mejorar vs periodo anterior en al menos 3 de 4 indicadores.":S.bonus===6?"Mantener los objetivos de inventario durante 4 cortes semanales consecutivos.":"Se conserva el cálculo actual del Bono 1.";return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Cómo funciona este bono</span><span>Reglas de acreditación</span></div><div class=\"v312-body\"><div class=\"v312-rules\"><div class=\"v312-rule\"><b>1 · Venta</b>"+esc(S.bonus===1?"Regla original sin cambios.":r.sales)+"</div><div class=\"v312-rule\"><b>2 · Indicador principal</b>"+esc(two)+"</div><div class=\"v312-rule v312-att\"><b>3 · Asistencia</b>"+esc(S.bonus===1?"Se conserva exactamente como en Bono 1.":r.attendance)+"</div></div></div></section>"}
function levels(d){var a=d.ranking||[],counts=[0,0,0,0,0];a.forEach(function(x){var lv=Math.max(0,Math.min(4,Number(x.level)||0));counts[lv]++});var labs=["<50%","50–59%","60–74%","75–89%","≥90%"];return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Escalones por reducción DDI</span><span>Bono 2</span></div><div class=\"v312-body\"><div class=\"v312-levels\">"+counts.map(function(c,i){return"<div class=\"v312-level "+(i?"l"+i:"off")+"\"><b>"+c+"</b>"+labs[i]+"<small style=\"display:block\">"+(i?"Nivel "+i:"No habilita")+"</small></div>"}).join("")+"</div></div></section>"}
function rubros(d){var r=(d.summary||{}).rubros||{};return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Reducción DDI por rubro</span><span>Mínimo 50%</span></div><div class=\"v312-body\"><div class=\"v312-bars\">"+["Abrigador","Licencias","Básicos"].map(function(c){var v=r[c];return"<div class=\"v312-barcol\"><div class=\"v312-bar\"><i style=\"height:"+Math.max(2,Math.min(100,n(v)))+"%\"></i></div><b>"+pc(v)+"</b>"+c+"</div>"}).join("")+"</div></div></section>"}
function matrix(d){var inv=(d.summary||{}).inventory||{},score=(d.summary||{}).score_avg;var rows=[["Reducción DDI","ddi_reduction_pct",50,30],["Reducción Existencia","existence_reduction_pct",30,25],["Reducción Inversión","investment_reduction_pct",30,25],["Control de Modelos","models_reduction_pct",20,20]];return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Matriz integral de indicadores</span><span>Score "+pc(score)+"</span></div><div class=\"v312-body\"><div class=\"v312-matrix\"><div class=\"h\">Indicador</div><div class=\"h\">Peso</div><div class=\"h\">Objetivo</div><div class=\"h\">Resultado</div><div class=\"h\">Cumple</div>"+rows.map(function(x){var v=inv[x[1]],ok=v!=null&&n(v)>=x[2];return"<div><b>"+x[0]+"</b></div><div>"+x[3]+"%</div><div>≥ "+x[2]+"%</div><div>"+pc(v)+"</div><div><span class=\"v312-check "+(ok?"":"no")+"\">"+(ok?"✓":"×")+"</span></div>"}).join("")+"</div></div></section>"}
function improvement(d){var ch=(d.summary||{}).changes||{};var rows=[["DDI","ddi_reduction_pct"],["Existencia","existence_reduction_pct"],["Inversión","investment_reduction_pct"],["Modelos","models_reduction_pct"]];return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Comparativo contra periodo anterior</span><span>Bono 5</span></div><div class=\"v312-body\"><div class=\"v312-bars\">"+rows.map(function(x){var z=ch[x[1]]||{},mx=Math.max(100,n(z.previous),n(z.current));return"<div class=\"v312-barcol\"><div class=\"v312-bar\"><i class=\"alt\" style=\"height:"+Math.max(2,n(z.previous)/mx*100)+"%\"></i><i style=\"height:"+Math.max(2,n(z.current)/mx*100)+"%\"></i></div><b>"+pc(z.current)+"</b>"+x[0]+"<small style=\"display:block\">Ant. "+pc(z.previous)+"</small></div>"}).join("")+"</div></div></section>"}
function streaks(d){var dist=(d.summary||{}).streak_distribution||{};var total=n((d.summary||{}).stores_total)||1;return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Distribución por racha semanal</span><span>4 semanas requeridas</span></div><div class=\"v312-body\">"+[4,3,2,1,0].map(function(k){var c=n(dist[k]||dist[String(k)]),w=c/total*100;return"<div style=\"display:grid;grid-template-columns:70px 1fr 40px;gap:7px;align-items:center;font-size:9px;margin:7px 0\"><b>"+k+" semanas</b><div class=\"v312-progress\"><i style=\"width:"+w+"%\"></i></div><span>"+c+"</span></div>"}).join("")+"</div></section>"}
function visual(d){if(S.bonus===2)return levels(d);if(S.bonus===3)return rubros(d);if(S.bonus===4)return matrix(d);if(S.bonus===5)return improvement(d);if(S.bonus===6)return streaks(d);return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Bono 1</span><span>Sin cambios</span></div><div class=\"v312-body\"><div class=\"v312-note\">La fórmula, ponderaciones y resultados del Bono 1 se conservan tal cual.</div></div></section>"}
function indicator(e){if(!e)return"N/D";if(S.bonus===1)return pc(e.indicator);if(S.bonus===2)return pc((e.extra||{}).ddi_reduction_pct)+" · Nivel "+(e.level||0);if(S.bonus===3)return (e.extra||{}).rubros_met+" de 3 rubros";if(S.bonus===4)return pc((e.extra||{}).score);if(S.bonus===5)return (e.extra||{}).improved+" de 4";return (e.extra||{}).streak+" de 4 semanas"}
function ranking(d,limit){var a=(d.ranking||[]).slice();if(limit)a=a.slice(0,limit);return"<section class=\"v312-panel\"><div class=\"v312-ph\"><span>Ranking de Tiendas · Bono "+S.bonus+"</span><span>Mejor a peor</span></div><div class=\"v312-scroll\"><table class=\"v312-table\"><thead><tr><th>#</th><th class=\"left\">Tienda</th><th>Venta %</th><th>Indicador</th><th>Asistencia ref.</th><th>Estado</th></tr></thead><tbody>"+a.map(function(e){return"<tr data-v312-store=\""+esc(e.store)+"\" style=\"cursor:pointer\"><td>"+(e.rank==null?"—":e.rank)+"</td><td class=\"left\"><b>"+esc(e.store)+"</b></td><td class=\""+(n(e.sales_pct)>=100?"v312-good":"v312-bad")+"\">"+pc(e.sales_pct)+"</td><td>"+esc(indicator(e))+"</td><td>"+pc(e.attendance_reference)+"</td><td><span class=\"v312-status "+(!e.ready?"na":e.eligible?"":"no")+"\">"+esc(e.classification)+"</span></td></tr>"}).join("")+"</tbody></table></div></section>"}
function summary(d){return method(d)+"<div class=\"v312-grid\">"+baseCards(d)+"</div><div class=\"v312-layout\"><div>"+rules(d)+"<div style=\"margin-top:7px\">"+ranking(d,8)+"</div></div>"+visual(d)+"</div><div class=\"v312-note\">"+esc(d.rules.cost)+"</div>"}
function panorama(d){if(d.selected_store==="Compañía")return method(d)+"<div class=\"v312-note\">Selecciona una tienda desde el filtro o desde el ranking para abrir su panorama.</div>"+ranking(d,0);return summary(d)}
function models(d){if(d.selected_store==="Compañía")return method(d)+"<div class=\"v312-note\">Selecciona una tienda para consultar Modelos a Detalle.</div>"+ranking(d,0);var rows=(d.details||[]).filter(function(x){return x.catalog===S.catalog});return method(d)+"<div class=\"v312-subtabs\">"+["Abrigador","Licencias","Básicos"].map(function(c){return"<button data-v312-cat=\""+c+"\" class=\""+(S.catalog===c?"active":"")+"\">"+c+"</button>"}).join("")+"</div><div class=\"v312-model-title\">Modelos a detalle · "+esc(d.selected_store)+" · "+esc(S.catalog)+"</div><section class=\"v312-panel\"><div class=\"v312-scroll\"><table class=\"v312-table\"><thead><tr><th class=\"left\">ID</th><th class=\"left\">Modelo</th><th>DDI inicial</th><th>DDI actual</th><th>Red. DDI</th><th>Exist. inicial</th><th>Exist. actual</th><th>Red. inversión</th><th>Estatus</th></tr></thead><tbody>"+rows.map(function(r){return"<tr><td class=\"left\"><b>"+esc(r.id_art)+"</b></td><td class=\"left\">"+esc(r.model)+"</td><td>"+nf(r.initial_ddi)+"</td><td>"+nf(r.current_ddi)+"</td><td>"+pc(r.ddi_reduction_pct)+"</td><td>"+nf(r.initial_existence)+"</td><td>"+nf(r.current_existence)+"</td><td>"+pc(r.investment_reduction_pct)+"</td><td>"+esc(r.status)+"</td></tr>"}).join("")+"</tbody></table></div></section>"}
function body(d){if(S.section==="ranking")return method(d)+ranking(d,0);if(S.section==="panorama")return panorama(d);if(S.section==="models")return models(d);return summary(d)}
function page(d){return"<div class=\"v312\"><div class=\"v312-head\"><div><h2>Bonos</h2><div class=\"v312-sub\">Indicadores comerciales para habilitar el bono de colaboradores · el costo se calcula aparte</div></div>"+filters(d)+"</div>"+bonusTabs()+tabs()+body(d)+"</div>"}
function bind(){q("#v312Month")&&q("#v312Month").addEventListener("change",function(e){S.month=e.target.value;load()});q("#v312Store")&&q("#v312Store").addEventListener("change",function(e){S.store=e.target.value;load()});qa("[data-v312-bonus]").forEach(function(b){b.addEventListener("click",function(){S.bonus=Number(b.dataset.v312Bonus);S.section="summary";load()})});qa("[data-v312-section]").forEach(function(b){b.addEventListener("click",function(){S.section=b.dataset.v312Section;render()})});qa("[data-v312-store]").forEach(function(r){r.addEventListener("click",function(){S.store=r.dataset.v312Store;S.section="panorama";load()})});qa("[data-v312-cat]").forEach(function(b){b.addEventListener("click",function(){S.catalog=b.dataset.v312Cat;render()})})}
function render(){activate();var h=q("#v312Host");if(h&&S.data){h.innerHTML=page(S.data);bind()}}
function load(){var seq=++S.seq;activate();var p=new URLSearchParams({bonus:String(S.bonus),store:S.store});if(S.month)p.set("month",S.month);api("/api/bonuses-v312?"+p.toString()).then(function(d){if(seq!==S.seq)return;S.data=d;S.month=d.month;S.store=d.selected_store;render()}).catch(function(e){var h=q("#v312Host");if(h)h.innerHTML="<div class=\"v312-note\">No fue posible cargar Bonos: "+esc(e.message||e)+"</div>"})}
function replaceMenuOne(el){if(!el)return null;var c=el.cloneNode(true);el.replaceWith(c);c.dataset.v302Bound="1";c.dataset.v293Bound="1";c.dataset.v312Bound="1";c.addEventListener("click",function(e){e.preventDefault();e.stopImmediatePropagation();open()},true);return c}
function menu(){var side=q("#sidebar"),old=side&&q("[data-main=\"bonuses\"]",side);if(old&&!old.dataset.v312Bound)replaceMenuOne(old);var mn=q("#mobileMainNav"),mo=mn&&q("[data-main=\"bonuses\"]",mn);if(mo&&!mo.dataset.v312Bound)replaceMenuOne(mo)}
function open(){activate();load()}
function boot(){menu();setTimeout(menu,150)}
document.addEventListener("DOMContentLoaded",function(){setTimeout(boot,300)},{once:true});[700,1500,3000].forEach(function(ms){setTimeout(boot,ms)});
document.addEventListener("click",function(e){var x=e.target.closest&&e.target.closest("[data-main]");if(x&&x.dataset.main!=="bonuses"){document.body.removeAttribute("data-v312")}},true);
})();</script>'''

    @m.app.middleware("http")
    async def v312_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v312-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v312-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-Bonus-Version"]="V312-FINAL-BONUS-METHODS"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V312] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V312_FINAL_SALES_BONUSES=True
    print("[V312] Bonos finales: B1 intacto; B2/B3 opciones elegidas; B4-B6 metodologías aprobadas; sin gráficas de línea.",flush=True)
