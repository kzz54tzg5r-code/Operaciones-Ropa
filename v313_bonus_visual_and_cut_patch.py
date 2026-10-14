"""V313 · Bonos: diseño fiel por metodología + cortes de Capacidades visibles.

Mantiene cálculos V312. Sólo mejora:
- corte base/corte actual visibles;
- macro Compañía calculado con datos reales disponibles;
- diseño distinto para Bono 1..6, sin gráficas de línea;
- Bono 4 con matriz integral como boceto aprobado;
- Bono 2 escalones, Bono 3 rubros, Bono 5 comparación y Bono 6 semanas.
"""
from __future__ import annotations

import math
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX=ZoneInfo("America/Mexico_City")
CATALOGS=("Abrigador","Licencias","Básicos")

def install(m):
    if getattr(m,"_V313_BONUS_VISUAL_CUTS",False):
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

    def route_endpoint(path):
        for route in getattr(m.app,"routes",[]):
            if getattr(route,"path","")==path:
                return getattr(route,"endpoint",None)
        return None

    def base_endpoint():
        fn=route_endpoint("/api/operation/sales-bonus-v293")
        if fn is None: raise HTTPException(503,"La base de Bonos no está disponible")
        return fn

    def final_endpoint():
        fn=route_endpoint("/api/bonuses-v312")
        if fn is None: raise HTTPException(503,"Bonos V312 no está disponible")
        return fn

    def aggregate_base(base):
        rows=list(base.get("ranking") or [])
        valid_sales=[x for x in rows if maybe(x.get("sales_pct")) is not None]
        actual=sum(num(x.get("sales_actual")) for x in valid_sales)
        goal=sum(num(x.get("sales_goal")) for x in valid_sales)
        sales_pct=(actual/goal*100.0) if goal>0 and valid_sales else None

        ddi_vals=[maybe(x.get("ddi_pct")) for x in rows]; ddi_vals=[x for x in ddi_vals if x is not None]
        att_vals=[maybe(x.get("attendance_pct")) for x in rows]; att_vals=[x for x in att_vals if x is not None]
        score_vals=[maybe(x.get("score")) for x in rows if bool(x.get("score_ready"))]; score_vals=[x for x in score_vals if x is not None]

        invs=[dict(x.get("inventory") or {}) for x in rows]
        def vals(k):
            a=[maybe(x.get(k)) for x in invs]
            return [x for x in a if x is not None]
        def avg(k):
            a=vals(k); return round(sum(a)/len(a),1) if a else None
        def total(k):
            a=vals(k); return sum(a) if a else None
        def red(initial,current):
            return round((initial-current)/initial*100.0,1) if initial is not None and current is not None and initial>0 else None

        init_ddi=avg("initial_ddi"); cur_ddi=avg("current_ddi")
        init_exist=total("initial_existence"); cur_exist=total("current_existence")
        init_inv=total("initial_investment"); cur_inv=total("current_investment")
        init_models=total("initial_models"); cur_models=total("current_models")
        inventory={
            "initial_ddi":init_ddi,"current_ddi":cur_ddi,"ddi_reduction_pct":red(init_ddi,cur_ddi),
            "initial_existence":None if init_exist is None else round(init_exist,1),
            "current_existence":None if cur_exist is None else round(cur_exist,1),
            "existence_reduction_pct":red(init_exist,cur_exist),
            "initial_investment":None if init_inv is None else round(init_inv,2),
            "current_investment":None if cur_inv is None else round(cur_inv,2),
            "investment_reduction_pct":red(init_inv,cur_inv),
            "initial_models":None if init_models is None else int(init_models),
            "current_models":None if cur_models is None else int(cur_models),
            "models_reduction_pct":red(init_models,cur_models),
        }
        return {
            "sales_pct":None if sales_pct is None else round(sales_pct,1),
            "ddi_pct":round(sum(ddi_vals)/len(ddi_vals),1) if ddi_vals else None,
            "attendance_pct":round(sum(att_vals)/len(att_vals),1) if att_vals else None,
            "legacy_score_avg":round(sum(score_vals)/len(score_vals),1) if score_vals else None,
            "inventory":inventory,
            "stores_with_sales":len(valid_sales),
            "stores_with_score":len(score_vals),
        }

    @m.app.get("/api/bonuses-v313")
    def bonuses_v313(request:Request,month:str="",store:str="Compañía",bonus:int=1):
        actor=m.require_user(request)
        final=final_endpoint()(request=request,month=month,store=store,bonus=bonus)
        selected_store=str(final.get("selected_store") or "Compañía")
        base=base_endpoint()(request=request,month=str(final.get("month") or month),store="" if selected_store=="Compañía" else selected_store)
        agg=aggregate_base(base)

        # Macro real: no convertir "sin ventas cargadas" en 0%.
        if selected_store=="Compañía":
            final["summary"]["sales_pct"]=agg["sales_pct"]
            final["summary"]["inventory"]=agg["inventory"]
            final["summary"]["attendance_reference"]=agg["attendance_pct"]
        final["legacy_components"]=agg
        final["source_dates"]=dict(base.get("source_dates") or {})
        final["processing"]=dict(base.get("processing") or {})
        final["current_source_period"]=base.get("current_source_period")
        final["current_source_date"]=base.get("current_source_date")
        final["version"]="V316-BONUS-CUTS-AND-DESIGN"
        final["cut_rule"]="Corte inicial = último corte procesado disponible al inicio del mes; corte actual = último corte procesado hasta hoy."
        return final

    css=r'''<style id="v313-css">
body[data-v313="1"] #analysisNav,body[data-v313="1"] #operativoNav,body[data-v313="1"] #globalFilters{display:none!important}
body[data-v313="1"] #v312Host{display:none!important}
.v313{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b3268;max-width:1600px;margin:0 auto;padding-bottom:14px}
.v313 *{box-sizing:border-box}.v313-head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-bottom:8px}.v313 h2{font-size:21px;margin:0}.v313-sub{font-size:10px;color:#69809b;margin-top:2px}
.v313-filters{display:flex;gap:7px}.v313-field label{display:block;font-size:8px;font-weight:900;color:#71849b;margin:0 0 2px}.v313-field select{height:30px;min-width:150px;border:1px solid #ccd9e8;border-radius:7px;background:white;color:#123968;font-size:10px;font-weight:800;padding:0 28px 0 8px}
.v313-bonus,.v313-tabs{display:grid;gap:5px;margin:6px 0}.v313-bonus{grid-template-columns:repeat(6,1fr)}.v313-tabs{grid-template-columns:repeat(4,1fr)}.v313-tabs.v313-tabs-b2{grid-template-columns:repeat(5,minmax(0,1fr))}.v313-tabs.v313-tabs-b3{grid-template-columns:repeat(7,minmax(0,1fr))}
.v313-bonus button,.v313-tabs button,.v313-subtabs button{height:32px;border:1px solid #d3dfec;border-radius:7px;background:#fff;color:#0d3b73;font-size:10px;font-weight:900}.v313-bonus button.active,.v313-tabs button.active,.v313-subtabs button.active{background:#1475ee;color:#fff;border-color:#1475ee}
.v313-cutbar{display:grid;grid-template-columns:1.15fr 1fr 1fr 1.35fr;gap:6px;margin:7px 0}.v313-cut{border:1px solid #d5e2ef;background:#fff;border-radius:9px;padding:7px 9px;min-height:53px}.v313-cut span{display:block;font-size:8px;color:#68809b;font-weight:800}.v313-cut b{display:block;font-size:12px;margin-top:3px}.v313-cut.current{background:#eef7ff;border-color:#b8d8fb}.v313-cut.ok b{color:#15925b}.v313-cut.wait b{color:#d28a00}
.v313-hero{border-radius:10px;padding:10px 12px;color:#fff;background:linear-gradient(100deg,#074caa,#1480ef);display:flex;justify-content:space-between;align-items:center;gap:10px;margin:7px 0}.v313-hero b{font-size:13px}.v313-hero span{font-size:9px;opacity:.95}.v313-hero .tag{background:rgba(255,255,255,.18);padding:5px 8px;border-radius:99px;font-weight:900;white-space:nowrap}
.v313-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}.v313-kpi,.v313-panel{background:#fff;border:1px solid #d7e3ef;border-radius:9px;box-shadow:0 2px 7px rgba(15,62,117,.05)}.v313-kpi{padding:8px;min-height:76px}.v313-kpi span{display:block;font-size:8px;font-weight:900;color:#627b97}.v313-kpi b{display:block;font-size:18px;margin-top:4px;color:#0a376f}.v313-kpi small{display:block;font-size:8px;color:#7289a2;margin-top:3px}.good{color:#13925a!important}.bad{color:#dc3848!important}.warn{color:#d89500!important}
.v313-main{display:grid;grid-template-columns:1.25fr .85fr;gap:7px;margin-top:7px}.v313-panel{overflow:hidden}.v313-ph{padding:7px 9px;border-bottom:1px solid #e3ebf4;font-size:9px;font-weight:900;display:flex;justify-content:space-between;gap:8px}.v313-body{padding:9px}
.v313-components{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.v313-comp{border:1px solid #dbe6f1;border-radius:9px;overflow:hidden}.v313-comp .top{padding:6px 8px;color:#fff;font-size:9px;font-weight:900}.v313-comp.sales .top{background:#0d70e8}.v313-comp.ddi .top{background:#734ee8}.v313-comp.att .top{background:#138b65}.v313-comp .value{padding:10px;text-align:center}.v313-comp .value b{display:block;font-size:25px}.v313-comp .value small{font-size:8px;color:#71839a}
.v313-score{display:flex;align-items:center;justify-content:center;gap:14px;min-height:144px}.v313-ring{--p:0;width:112px;height:112px;border-radius:50%;background:conic-gradient(#1177ec calc(var(--p)*1%),#e7eef6 0);display:grid;place-items:center}.v313-ring:after{content:"";width:79px;height:79px;border-radius:50%;background:white;position:absolute}.v313-ring{position:relative}.v313-ring div{z-index:1;text-align:center}.v313-ring b{font-size:20px}.v313-ring small{display:block;font-size:8px;color:#71839a}
.v313-levels{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}.v313-level{border-radius:8px;padding:10px 5px;text-align:center;background:#eef3f8;font-size:8px}.v313-level b{display:block;font-size:18px}.v313-level.l1{background:#eaf9ef}.v313-level.l2{background:#e6f3ff}.v313-level.l3{background:#eee9ff}.v313-level.l4{background:#dfeaff}.v313-level.off b{color:#d94452}
.v313-bars{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;min-height:170px;align-items:end}.v313-barbox{text-align:center;font-size:9px}.v313-bartrack{height:118px;border-bottom:1px solid #d7e2ee;display:flex;align-items:flex-end;justify-content:center;gap:4px}.v313-bartrack i{width:34px;display:block;background:#1475ee;border-radius:5px 5px 0 0;min-height:2px}.v313-bartrack i.prev{background:#8760e6}.v313-barbox b{display:block;margin-top:5px;font-size:12px}
.v313-matrixcards{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.v313-mcard{border:1px solid #dbe6f1;border-radius:9px;padding:9px;text-align:center}.v313-mcard span{display:block;font-size:8px;color:#607995;font-weight:800}.v313-mcard b{font-size:20px;display:block;margin:4px 0}.v313-mcard small{font-size:8px}.v313-check{display:inline-flex;width:19px;height:19px;align-items:center;justify-content:center;border-radius:5px;background:#e8f8ee;color:#15945b;font-weight:900}.v313-check.no{background:#ffecef;color:#d93c4d}
.v313-weeks{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.v313-week{border:1px solid #dbe6f1;border-radius:9px;padding:8px;text-align:center}.v313-week b{display:block;font-size:11px}.v313-week .dot{margin:7px auto;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#edf2f7;color:#6c7d90;font-weight:900}.v313-week.pass .dot{background:#e6f8ed;color:#15945b}.v313-week.fail .dot{background:#ffecee;color:#d93a4a}.v313-week small{font-size:8px;color:#71839a}
.v313-scroll{overflow:auto;max-width:100%;-webkit-overflow-scrolling:touch}.v313-table{width:100%;border-collapse:collapse;font-size:9px;white-space:nowrap}.v313-table th{background:#f3f7fb;color:#315676}.v313-table th,.v313-table td{padding:5px 6px;border-bottom:1px solid #edf1f5;text-align:center}.v313-table .left{text-align:left}.v313-status{display:inline-block;padding:3px 7px;border-radius:99px;background:#e7f7ed;color:#138c51;font-weight:900}.v313-status.no{background:#ffedef;color:#d93647}.v313-status.na{background:#eef2f6;color:#748497}
.v313-subtabs{display:flex;gap:5px;margin:7px 0}.v313-note{font-size:9px;color:#466583;background:#eef6ff;border-radius:7px;padding:7px 9px;margin-top:7px}.v313-empty{margin:9px;padding:12px;border:1px dashed #b9cce0;border-radius:8px;background:#f7faff;color:#3b5b7c;font-size:10px;white-space:normal}.v313-empty b{display:block;color:#153f73;font-size:11px;margin-bottom:4px}.v313-empty p{margin:4px 0}.v313-gate{display:flex;align-items:center;justify-content:center;min-height:110px;text-align:center}.v313-gate b{font-size:34px;display:block}.v313-gate span{font-size:9px}.v313-pairs{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.v313-pair{border:1px solid #dbe6f1;border-radius:8px;padding:8px}.v313-pair b{display:block;font-size:11px}.v313-pair .nums{display:flex;justify-content:space-between;font-size:9px;margin-top:7px}.v313-pair .delta{font-size:15px;margin-top:5px;font-weight:900}
@media(max-width:900px){.v313{min-width:980px}.v313-kpis{grid-template-columns:repeat(6,minmax(120px,1fr))}.v313-main{grid-template-columns:1.2fr .8fr}}
</style>''';

    js=r'''<script id="v313-js">(function(){
if(window.__V313_BONUS_VISUAL_CUTS)return;window.__V313_BONUS_VISUAL_CUTS=true;
var S={bonus:1,section:"summary",store:"Compañía",month:"",catalog:"Abrigador",data:null,seq:0,refreshCount:0,refreshTimer:null};
function q(s,r){return(r||document).querySelector(s)}function qa(s,r){return Array.from((r||document).querySelectorAll(s))}
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c]})}
function n(v){var x=Number(v);return Number.isFinite(x)?x:0}function pc(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{maximumFractionDigits:1})+"%"}function nf(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{maximumFractionDigits:1})}
function money(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{style:"currency",currency:"MXN",maximumFractionDigits:0})}
function dateMx(v){if(!v)return"Pendiente";var a=String(v).slice(0,10).split("-");return a.length===3?a[2]+"/"+a[1]+"/"+a[0]:v}
function api(u){return fetch(u,{credentials:"same-origin"}).then(function(r){if(!r.ok)return r.text().then(function(t){throw new Error(t||("HTTP "+r.status))});return r.json()})}
function ensure(){var p=q("#page-bonuses"),main=q("main.main");if(main&&!p){p=document.createElement("section");p.className="page";p.id="page-bonuses";main.appendChild(p)}if(p&&!q("#v313Host",p))p.insertAdjacentHTML("afterbegin","<div id=\"v313Host\"></div>");return p}
function activate(){ensure();try{MAIN="bonuses"}catch(_e){}document.body.dataset.v313="1";document.body.removeAttribute("data-v302");document.body.removeAttribute("data-v312");qa("[data-main]").forEach(function(x){x.classList.toggle("active",x.dataset.main==="bonuses")});qa(".page").forEach(function(x){x.classList.toggle("active",x.id==="page-bonuses")});var t=q("#heroTitle"),s=q("#heroSub");if(t)t.textContent="Bonos";if(s)s.textContent="Indicadores para habilitar el bono de colaboradores"}
function filters(d){return"<div class=\"v313-filters\"><div class=\"v313-field\"><label>Periodo</label><select id=\"v313Month\">"+(d.months||[]).map(function(x){return"<option value=\""+esc(x.value)+"\" "+(x.value===d.month?"selected":"")+">"+esc(x.label)+"</option>"}).join("")+"</select></div><div class=\"v313-field\"><label>Tienda</label><select id=\"v313Store\">"+(d.stores||[]).map(function(x){return"<option "+(x===d.selected_store?"selected":"")+">"+esc(x)+"</option>"}).join("")+"</select></div></div>"}
function bonusTabs(){return"<div class=\"v313-bonus\">"+[1,2,3,4,5,6].map(function(i){return"<button data-v313-bonus=\""+i+"\" class=\""+(S.bonus===i?"active":"")+"\">Bono "+i+"</button>"}).join("")+"</div>"}
function tabs(){
var xs,cls="";
if(S.bonus===2){
 cls=" v313-tabs-b2";
 xs=[["summary","Resumen General"],["ranking","Ranking de Tiendas"],["panorama","Desempeño por Tienda"],["collaborators","Colaboradores"],["models","Modelos a Detalle"]];
}else if(S.bonus===3){
 cls=" v313-tabs-b3";
 xs=[["summary","Resumen General"],["ranking","Ranking de Tiendas"],["rubros","Rubros críticos"],["stores","Tiendas"],["catalogLic","Licencias"],["catalogBas","Básicos"],["details","Detalle por rubro"]];
}else{
 xs=[["summary","Resumen General"],["ranking","Ranking de Tiendas"],["panorama","Panorama por Tienda"],["models","Modelos a Detalle"]];
}
return"<div class=\"v313-tabs"+cls+"\">"+xs.map(function(x){return"<button data-v313-section=\""+x[0]+"\" class=\""+(S.section===x[0]?"active":"")+"\">"+x[1]+"</button>"}).join("")+"</div>"
}


function cutbar(d){
var sd=d.source_dates||{},opening=sd.opening_capacity,current=sd.current_capacity,processing=d.processing||{};
var hasOpening=!!opening,hasCurrent=!!current,same=hasOpening&&hasCurrent&&String(opening)===String(current);
var status=!hasOpening?"Falta corte inicial":!hasCurrent?"Falta corte actual":same?(processing.capacity?"Preparando cartera inicial":"Esperando segundo corte"):(processing.capacity?"Procesando comparación":"Comparación activa");
return"<div class=\"v313-cutbar\"><div class=\"v313-cut\"><span>Regla de comparación</span><b>Corte más cercano al inicio → corte actual</b></div><div class=\"v313-cut "+(hasOpening?"ok":"wait")+"\"><span>Corte inicial seleccionado</span><b>"+dateMx(opening)+"</b></div><div class=\"v313-cut current "+(!hasCurrent||same?"wait":"ok")+"\"><span>Corte actual</span><b>"+dateMx(current)+"</b></div><div class=\"v313-cut\"><span>Avance</span><b>"+status+"</b></div></div>"
}


function hero(d){var names={1:"Modelo actual · 50/30/20",2:"Reducción DDI · escalones",3:"Rubros críticos · 2 de 3",4:"Matriz integral · imagen 1",5:"Mejora contra sí misma · 3 de 4",6:"Cumplimiento sostenido · 4 semanas"};return"<div class=\"v313-hero\"><div><b>Bono "+S.bonus+" · "+names[S.bonus]+"</b><br><span>"+esc((d.selected&&d.selected.formula)||({1:"Bono 1 conserva exactamente su cálculo original.",2:"Venta ≥100% + reducción DDI mínima 50%.",3:"Venta ≥100% + mínimo 2 de 3 rubros con DDI reducido ≥50%.",4:"Venta ≥100% + matriz DDI / Existencia / Inversión / Modelos.",5:"Venta ≥100% + mejora en mínimo 3 de 4 indicadores.",6:"Venta ≥100% + cuatro cortes semanales consecutivos."})[S.bonus])+"</span></div><span class=\"tag\">"+esc(d.selected_store)+"</span></div>"}
function kpi(label,val,note,cls){return"<div class=\"v313-kpi\"><span>"+esc(label)+"</span><b class=\""+(cls||"")+"\">"+esc(val)+"</b><small>"+esc(note||"")+"</small></div>"}
function topKpis(d){var s=d.summary||{},inv=s.inventory||{},out=[];out.push(kpi("Venta vs Meta",pc(s.sales_pct),"Meta obligatoria 100%",s.sales_pct==null?"warn":n(s.sales_pct)>=100?"good":"bad"));if(S.bonus===1){var l=d.legacy_components||{};out.push(kpi("DDI por Cat",pc(l.ddi_pct),"Peso 30%"));out.push(kpi("Asistencia",pc(l.attendance_pct),"Peso 20%"));out.push(kpi("Resultado promedio",pc(l.legacy_score_avg),"Sólo scores completos"));out.push(kpi("Tiendas con score",nf(l.stores_with_score)+" de "+nf(s.stores_total),"Bono 1"));out.push(kpi("Corte actual",dateMx((d.source_dates||{}).current_capacity),"Capacidades"));return out.join("")}out.push(kpi("DDI inicial",nf(inv.initial_ddi),"Corte inicial"));out.push(kpi("DDI actual",nf(inv.current_ddi),"Último corte"));out.push(kpi("Reducción DDI",pc(inv.ddi_reduction_pct),"Objetivo base ≥50%",inv.ddi_reduction_pct!=null&&n(inv.ddi_reduction_pct)>=50?"good":"bad"));out.push(kpi("Tiendas habilitadas",nf(s.stores_enabled)+" de "+nf(s.stores_total),"Según Bono "+S.bonus));out.push(kpi("Asistencia",pc(s.attendance_reference),"Referencia · no suma puntos","warn"));return out.join("")}
function componentsB1(d){var l=d.legacy_components||{},p=l.legacy_score_avg;return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Componentes originales del Bono 1</span><span>50 / 30 / 20</span></div><div class=\"v313-body\"><div class=\"v313-components\"><div class=\"v313-comp sales\"><div class=\"top\">50% · Venta vs Meta</div><div class=\"value\"><b>"+pc(l.sales_pct)+"</b><small>Base Muertos/Cambios + Meta</small></div></div><div class=\"v313-comp ddi\"><div class=\"top\">30% · DDI por Cat</div><div class=\"value\"><b>"+pc(l.ddi_pct)+"</b><small>Capacidades</small></div></div><div class=\"v313-comp att\"><div class=\"top\">20% · Asistencia</div><div class=\"value\"><b>"+pc(l.attendance_pct)+"</b><small>Captura autorizada</small></div></div></div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Resultado Bono 1</span><span>Sin cambios</span></div><div class=\"v313-score\"><div class=\"v313-ring\" style=\"--p:"+Math.max(0,Math.min(100,n(p)))+"\"><div><b>"+pc(p)+"</b><small>Promedio compañía</small></div></div><div><b style=\"font-size:12px\">Cálculo original V293</b><div class=\"v313-note\">No se modificó fórmula, ponderaciones ni criterios.</div></div></div></section>"}
function levelsB2(d){var a=d.ranking||[],counts=[0,0,0,0,0];a.forEach(function(x){counts[Math.max(0,Math.min(4,Number(x.level)||0))]++});var labs=["<50%","50–59%","60–74%","75–89%","≥90%"];return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Escalones de reducción DDI</span><span>Mínimo 50%</span></div><div class=\"v313-body\"><div class=\"v313-levels\">"+counts.map(function(c,i){return"<div class=\"v313-level "+(i?"l"+i:"off")+"\"><b>"+c+"</b><span>"+labs[i]+"</span><small style=\"display:block\">"+(i?"Nivel "+i:"No habilita")+"</small></div>"}).join("")+"</div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Puerta del bono</span><span>Venta + DDI</span></div><div class=\"v313-gate\"><div><b>"+pc((d.summary||{}).inventory?.ddi_reduction_pct)+"</b><span>Reducción DDI compañía<br>Venta debe estar en 100% o más</span></div></div></section>"}
function rubrosB3(d){var r=(d.summary||{}).rubros||{};return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Rubros críticos</span><span>Se requieren 2 de 3</span></div><div class=\"v313-body\"><div class=\"v313-bars\">"+CAT().map(function(c){var v=r[c],ok=v!=null&&n(v)>=50;return"<div class=\"v313-barbox\"><div class=\"v313-bartrack\"><i style=\"height:"+Math.max(2,Math.min(100,n(v)))+"%\"></i></div><b class=\""+(ok?"good":"bad")+"\">"+pc(v)+"</b>"+c+"<small style=\"display:block\">"+(ok?"Cumple ≥50%":"Pendiente / <50%")+"</small></div>"}).join("")+"</div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Regla</span><span>Opción 4 elegida</span></div><div class=\"v313-gate\"><div><b>2 / 3</b><span>Abrigador · Licencias · Básicos<br>cada rubro debe reducir DDI al menos 50%</span></div></div></section>"}
function CAT(){return["Abrigador","Licencias","Básicos"]}
function matrixB4(d){var inv=(d.summary||{}).inventory||{},score=(d.summary||{}).score_avg,rows=[["DDI","ddi_reduction_pct",50,30],["Existencia","existence_reduction_pct",30,25],["Inversión","investment_reduction_pct",30,25],["Modelos","models_reduction_pct",20,20]];return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Matriz integral · diseño aprobado</span><span>Score mínimo 80</span></div><div class=\"v313-body\"><div class=\"v313-matrixcards\">"+rows.map(function(x){var v=inv[x[1]],ok=v!=null&&n(v)>=x[2];return"<div class=\"v313-mcard\"><span>"+x[0]+" · peso "+x[3]+"%</span><b class=\""+(ok?"good":"bad")+"\">"+pc(v)+"</b><small>Objetivo ≥"+x[2]+"% &nbsp; <span class=\"v313-check "+(ok?"":"no")+"\">"+(ok?"✓":"×")+"</span></small></div>"}).join("")+"</div><div class=\"v313-score\"><div class=\"v313-ring\" style=\"--p:"+Math.max(0,Math.min(100,n(score)))+"\"><div><b>"+pc(score)+"</b><small>Score integral</small></div></div><div><b style=\"font-size:12px\">"+(score!=null&&n(score)>=80?"Habilita por matriz":"Aún no habilita por matriz")+"</b><div class=\"v313-note\">DDI 30% · Existencia 25% · Inversión 25% · Modelos 20%</div></div></div></div></section>"}
function improveB5(d){var ch=(d.summary||{}).changes||{},rows=[["DDI","ddi_reduction_pct"],["Existencia","existence_reduction_pct"],["Inversión","investment_reduction_pct"],["Modelos","models_reduction_pct"]];return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Mejora contra sí misma</span><span>Se requieren 3 de 4</span></div><div class=\"v313-body\"><div class=\"v313-pairs\">"+rows.map(function(x){var z=ch[x[1]]||{},delta=z.current!=null&&z.previous!=null?n(z.current)-n(z.previous):null,ok=delta!=null&&delta>0;return"<div class=\"v313-pair\"><b>"+x[0]+"</b><div class=\"nums\"><span>Anterior "+pc(z.previous)+"</span><span>Actual "+pc(z.current)+"</span></div><div class=\"delta "+(ok?"good":"bad")+"\">"+(delta==null?"N/D":(delta>=0?"+":"")+delta.toLocaleString("es-MX",{maximumFractionDigits:1})+" pp")+"</div><small>"+(ok?"Mejoró":"No mejoró")+"</small></div>"}).join("")+"</div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Puerta</span><span>Periodo anterior vs actual</span></div><div class=\"v313-gate\"><div><b>"+nf((d.summary||{}).improved_avg)+" / 4</b><span>Promedio de indicadores mejorados</span></div></div></section>"}
function weeksB6(d){var sel=d.selected||{},weeks=((sel.extra||{}).weeks||[]).slice(-4),slots=[0,1,2,3].map(function(i){return weeks[i]||null});return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Cumplimiento sostenido</span><span>4 cortes semanales consecutivos</span></div><div class=\"v313-body\"><div class=\"v313-weeks\">"+slots.map(function(w,i){if(!w)return"<div class=\"v313-week\"><b>Semana "+(i+1)+"</b><div class=\"dot\">—</div><small>Sin corte</small></div>";return"<div class=\"v313-week "+(w.meets?"pass":"fail")+"\"><b>"+esc(w.week||("Semana "+(i+1)))+"</b><div class=\"dot\">"+(w.meets?"✓":"×")+"</div><small>"+dateMx(w.date)+"<br>"+(w.meets?"Cumple objetivos":"No cumple todos")+"</small></div>"}).join("")+"</div>"+(d.weekly_pending?"<div class=\"v313-note\">Procesando los cortes semanales de Capacidades…</div>":"")+"</div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Racha actual</span><span>Se necesitan 4</span></div><div class=\"v313-gate\"><div><b>"+nf((sel.extra||{}).streak)+" / 4</b><span>semanas consecutivas</span></div></div></section>"}
function visual(d){if(S.bonus===1)return componentsB1(d);if(S.bonus===2)return levelsB2(d);if(S.bonus===3)return rubrosB3(d);if(S.bonus===4)return matrixB4(d);if(S.bonus===5)return improveB5(d);return weeksB6(d)}
function indicator(e){if(!e)return"N/D";if(S.bonus===1)return pc(e.indicator);if(S.bonus===2)return pc((e.extra||{}).ddi_reduction_pct)+" · N"+(e.level||0);if(S.bonus===3)return nf((e.extra||{}).rubros_met)+" de 3";if(S.bonus===4)return pc((e.extra||{}).score);if(S.bonus===5)return nf((e.extra||{}).improved)+" de 4";return nf((e.extra||{}).streak)+" de 4"}
function ranking(d,limit){var a=(d.ranking||[]).slice();if(limit)a=a.slice(0,limit);return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Ranking de Tiendas · Bono "+S.bonus+"</span><span>Mejor a peor</span></div><div class=\"v313-scroll\"><table class=\"v313-table\"><thead><tr><th>#</th><th class=\"left\">Tienda</th><th>Venta</th><th>Indicador</th><th>Asistencia ref.</th><th>Estado</th></tr></thead><tbody>"+a.map(function(e){return"<tr data-v313-store=\""+esc(e.store)+"\" style=\"cursor:pointer\"><td>"+(e.rank==null?"—":e.rank)+"</td><td class=\"left\"><b>"+esc(e.store)+"</b></td><td>"+pc(e.sales_pct)+"</td><td>"+esc(indicator(e))+"</td><td>"+pc(e.attendance_reference)+"</td><td><span class=\"v313-status "+(!e.ready?"na":e.eligible?"":"no")+"\">"+esc(e.classification)+"</span></td></tr>"}).join("")+"</tbody></table></div></section>"}
function summary(d){return cutbar(d)+hero(d)+"<div class=\"v313-kpis\">"+topKpis(d)+"</div><div class=\"v313-main\"><div>"+visual(d)+"</div><div>"+ranking(d,10)+"<div class=\"v313-note\">Asistencia en Bonos 2–6 es sólo referencia; 1 falta descalifica al colaborador en la validación individual. El costo del bono no se calcula en esta pantalla.</div></div></div>"}
function panorama(d){if(d.selected_store==="Compañía")return cutbar(d)+hero(d)+"<div class=\"v313-note\">Selecciona una tienda para ver su panorama completo.</div>"+ranking(d,0);return summary(d)}
function modelTable(d,rows,title,showCatalog,subtabsHtml){
if(d.selected_store==="Compañía")return cutbar(d)+hero(d)+"<div class=\"v313-note\">Selecciona una tienda para consultar los modelos de su cartera.</div>"+ranking(d,0);
var all=d.details||[],processing=d.processing||{},sd=d.source_dates||{},emptyTitle="",emptyText="";
if(!rows.length){
 if(processing.capacity){emptyTitle="Preparando la cartera inicial";emptyText="Capacidades está reconstruyendo el listado para el corte seleccionado. Esta pantalla se actualizará automáticamente cuando termine."}
 else if(!sd.opening_capacity){emptyTitle="Falta un corte inicial válido";emptyText="No se usará una Capacidades antigua de otro mes. Carga el corte más cercano al inicio de "+esc((d.period_label||d.month||"este periodo"))+" para construir la comparación."}
 else if(!all.length){emptyTitle="No hay modelos elegibles para esta tienda";emptyText="La cartera se forma con modelos de los rubros Abrigador, Licencias y Básicos que tienen DDI inicial >90 e inversión superior al promedio de su catálogo."}
 else{emptyTitle="Sin modelos en "+title;emptyText="No hay modelos de este rubro que cumplan los criterios de la cartera inicial. Revisa los demás rubros o la clasificación del archivo de Capacidades."}
}
var head="<th class=\"left\">ID</th><th class=\"left\">Modelo</th>"+(showCatalog?"<th>Rubro</th>":"")+"<th>DDI inicial</th><th>DDI actual</th><th>Red. DDI</th><th>Exist. inicial</th><th>Exist. actual</th><th>Inv. inicial</th><th>Inv. actual</th><th>Red. inversión</th>";
var bodyRows=rows.map(function(r){return"<tr><td class=\"left\"><b>"+esc(r.id_art)+"</b></td><td class=\"left\">"+esc(r.model)+"</td>"+(showCatalog?"<td>"+esc(r.catalog)+"</td>":"")+"<td>"+nf(r.initial_ddi)+"</td><td>"+nf(r.current_ddi)+"</td><td>"+pc(r.ddi_reduction_pct)+"</td><td>"+nf(r.initial_existence)+"</td><td>"+nf(r.current_existence)+"</td><td>"+money(r.initial_investment)+"</td><td>"+money(r.current_investment)+"</td><td>"+pc(r.investment_reduction_pct)+"</td></tr>"}).join("");
return cutbar(d)+hero(d)+(subtabsHtml||"")+"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Modelos a Detalle · "+esc(title)+"</span><span>"+esc(d.selected_store)+" · "+nf(rows.length)+" modelos</span></div><div class=\"v313-scroll\"><table class=\"v313-table\"><thead><tr>"+head+"</tr></thead><tbody>"+bodyRows+"</tbody></table></div>"+(!rows.length?"<div class=\"v313-empty\"><b>"+emptyTitle+"</b><p>"+emptyText+"</p></div>":"")+"</section>"
}
function models(d,onlyCatalog){
if(onlyCatalog)S.catalog=onlyCatalog;
var all=d.details||[],rows=all.filter(function(x){return x.catalog===S.catalog});
var tabsHtml=onlyCatalog?"":"<div class=\"v313-subtabs\">"+CAT().map(function(c){return"<button data-v313-cat=\""+c+"\" class=\""+(S.catalog===c?"active":"")+"\">"+c+"</button>"}).join("")+"</div>";
return modelTable(d,rows,S.catalog,false,tabsHtml)
}
function allModels(d){
var rows=(d.details||[]).slice().sort(function(a,b){return String(a.catalog||"").localeCompare(String(b.catalog||""))||String(a.id_art||"").localeCompare(String(b.id_art||""))});
return modelTable(d,rows,"Todos los rubros",true,"")
}
function collaborators(d){
var rows=Array.isArray(d.collaborators)?d.collaborators:[];
var content=rows.length?rows.map(function(x){return"<div class=\"v313-note\">"+esc(x.name||x.colaborador||x.employee||"Colaborador")+" · "+esc(x.store||d.selected_store||"")+" · "+esc(x.status||"Pendiente de validación individual")+"</div>"}).join(""):"<div class=\"v313-empty\"><b>La elegibilidad individual aún no está disponible en esta consulta</b><p>El servicio de Bonos devuelve indicadores por tienda y modelos, pero no el padrón individual con ventas y faltas. No se inventarán colaboradores ni porcentajes.</p><p>Regla conservada: venta mínima del 100%; la asistencia sólo es referencia y una falta descalifica al colaborador. El costo se calcula aparte.</p></div>";
return cutbar(d)+hero(d)+"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Colaboradores · Bono 2</span><span>Validación individual</span></div>"+content+"</section>"
}
function rubrosPage(d){
return cutbar(d)+hero(d)+"<div class=\"v313-kpis\">"+topKpis(d)+"</div><div class=\"v313-main\"><div>"+rubrosB3(d)+"</div><div>"+ranking(d,10)+"</div></div>"
}


function body(d){
if(S.section==="ranking"||S.section==="stores")return cutbar(d)+hero(d)+ranking(d,0);
if(S.section==="panorama")return panorama(d);
if(S.section==="collaborators")return collaborators(d);
if(S.section==="rubros")return rubrosPage(d);
if(S.section==="catalogLic")return models(d,"Licencias");
if(S.section==="catalogBas")return models(d,"Básicos");
if(S.section==="details")return allModels(d);
if(S.section==="models")return models(d);
return summary(d)
}


function page(d){return"<div class=\"v313\"><div class=\"v313-head\"><div><h2>Bonos</h2><div class=\"v313-sub\">Comparación real entre corte inicial y corte actual · sin gráficas de línea</div></div>"+filters(d)+"</div>"+bonusTabs()+tabs()+body(d)+"</div>"}
function bind(){
q("#v313Month")?.addEventListener("change",function(e){S.month=e.target.value;S.refreshCount=0;load()});
q("#v313Store")?.addEventListener("change",function(e){S.store=e.target.value;S.refreshCount=0;load()});
qa("[data-v313-bonus]").forEach(function(b){b.addEventListener("click",function(){S.bonus=Number(b.dataset.v313Bonus);S.section="summary";S.catalog="Abrigador";S.refreshCount=0;load()})});
qa("[data-v313-section]").forEach(function(b){b.addEventListener("click",function(){S.section=b.dataset.v313Section;if(S.section==="catalogLic")S.catalog="Licencias";if(S.section==="catalogBas")S.catalog="Básicos";render()})});
qa("[data-v313-store]").forEach(function(r){r.addEventListener("click",function(){S.store=r.dataset.v313Store;S.section=S.bonus===3?"rubros":"panorama";S.refreshCount=0;load()})});
qa("[data-v313-cat]").forEach(function(b){b.addEventListener("click",function(){S.catalog=b.dataset.v313Cat;render()})})
}


function render(){activate();var h=q("#v313Host");if(h&&S.data){h.innerHTML=page(S.data);bind()}}
function load(){
if(S.refreshTimer){clearTimeout(S.refreshTimer);S.refreshTimer=null}
var seq=++S.seq;activate();var p=new URLSearchParams({bonus:String(S.bonus),store:S.store});if(S.month)p.set("month",S.month);
api("/api/bonuses-v313?"+p.toString()).then(function(d){
 if(seq!==S.seq)return;
 S.data=d;S.month=d.month;S.store=d.selected_store;render();
 var processing=d.processing||{};
 if((processing.capacity||processing.sales||d.weekly_pending)&&S.refreshCount<10){
  S.refreshCount++;
  S.refreshTimer=setTimeout(function(){if(seq===S.seq)load()},1800);
 }else{S.refreshCount=0}
}).catch(function(e){var h=q("#v313Host");if(h)h.innerHTML="<div class=\"v313-note\">No fue posible cargar Bonos: "+esc(e.message||e)+"</div>"})
}


function bindMenu(el){if(!el)return;var c=el.cloneNode(true);el.replaceWith(c);c.dataset.v313Bound="1";c.dataset.v312Bound="1";c.dataset.v302Bound="1";c.dataset.v293Bound="1";c.addEventListener("click",function(e){e.preventDefault();e.stopImmediatePropagation();activate();load()},true)}
function boot(){var s=q("#sidebar [data-main=\"bonuses\"]"),m=q("#mobileMainNav [data-main=\"bonuses\"]");if(s&&!s.dataset.v313Bound)bindMenu(s);if(m&&!m.dataset.v313Bound)bindMenu(m)}
document.addEventListener("DOMContentLoaded",function(){setTimeout(boot,850)},{once:true});[900,1800,3300].forEach(function(ms){setTimeout(boot,ms)});
document.addEventListener("click",function(e){var x=e.target.closest&&e.target.closest("[data-main]");if(x&&x.dataset.main!=="bonuses")document.body.removeAttribute("data-v313")},true);
})();</script>''';

    @m.app.middleware("http")
    async def v313_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator: body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v313-css"' not in html: html=html.replace("</head>",css+"</head>",1)
            if 'id="v313-js"' not in html: html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-Bonus-Version"]="V316-BONUS-CUTS-AND-DESIGN"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V313] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V313_BONUS_VISUAL_CUTS=True
    print("[V316] Bonos: corte inicial válido, estados de carga, tabs aprobadas y detalle con estado vacío.",flush=True)
