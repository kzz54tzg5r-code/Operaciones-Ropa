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
        provisional_attendance_stores=sum(1 for x in rows if x.get("attendance_provisional"))

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
            "attendance_provisional_stores":provisional_attendance_stores,
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
        final["version"]="V318-BONUS-CUTS-AND-DESIGN"
        final["cut_rule"]="Corte inicial = último corte procesado disponible al inicio del mes; corte actual = último corte procesado hasta hoy."
        return final

    css=r'''<style id="v313-css">
body[data-v313="1"] #analysisNav,body[data-v313="1"] #operativoNav,body[data-v313="1"] #globalFilters{display:none!important}
body[data-v313="1"] #v312Host{display:none!important}
.v313{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b3268;max-width:1600px;margin:0 auto;padding-bottom:14px}
.v313 *{box-sizing:border-box}.v313-head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-bottom:8px}.v313 h2{font-size:21px;margin:0}.v313-sub{font-size:10px;color:#69809b;margin-top:2px}
.v313-filters{display:flex;gap:7px}.v313-field label{display:block;font-size:8px;font-weight:900;color:#71849b;margin:0 0 2px}.v313-field select{height:30px;min-width:150px;border:1px solid #ccd9e8;border-radius:7px;background:white;color:#123968;font-size:10px;font-weight:800;padding:0 28px 0 8px}
.v313-bonus,.v313-tabs{display:grid;gap:5px;margin:6px 0}.v313-bonus{grid-template-columns:repeat(7,minmax(0,1fr))}.v313-tabs{grid-template-columns:repeat(4,1fr)}.v313-tabs.v313-tabs-b2{grid-template-columns:repeat(5,minmax(0,1fr))}.v313-tabs.v313-tabs-b3{grid-template-columns:repeat(7,minmax(0,1fr))}
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

.v313-head-right{display:flex;gap:9px;align-items:flex-end;flex-wrap:wrap;justify-content:flex-end}
#v313UpdateBtn{background:#fff;color:#0b417a;border:1px solid #bad1ea;border-radius:8px;padding:8px 12px;font-weight:850;font-size:10px;cursor:pointer;height:31px}
#v313UpdateBtn:hover,.v313-model-downloads button:hover{background:#eaf4ff}
.v313-return-btn{background:#eaf2ff;color:#124475;border:1px solid #b9d1ec;border-radius:7px;padding:8px 10px;font-weight:850;font-size:10px;cursor:pointer}.v313-return-btn:hover{background:#dceafd}.v313-export-notice{padding:8px 11px;background:#eef6ff;color:#114276;font-size:11px;border-radius:5px;margin:4px 10px}.v313-export-notice.error{background:#fff0ef;color:#922f34}.v313-export-notice[hidden]{display:none!important}.v313-model-downloads button:disabled{opacity:.5;cursor:not-allowed}
.v313-model-actions{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:6px 10px;background:#fafcff;font-size:9px;color:#49617f}
.v313-model-downloads{display:flex;gap:7px}.v313-model-downloads button{font-size:10px;font-weight:850;color:#115292;border:1px solid #bad1ea;border-radius:7px;padding:8px 12px;background:#fff;cursor:pointer}
.v313-model-scroll{display:block!important;height:min(66dvh,620px)!important;max-height:min(66dvh,620px)!important;min-height:280px!important;overflow-y:auto!important;overflow-x:auto!important;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;touch-action:pan-x pan-y;scrollbar-width:thin;scrollbar-color:#7b9cc1 #f1f5f9;contain:layout;position:relative}
.v313-model-table{min-width:880px;height:max-content!important;table-layout:auto}.v313-model-table thead th{position:sticky;top:0;z-index:2;background:#eaf3fb}
.v313-model-scroll::-webkit-scrollbar{width:14px;height:12px}.v313-model-scroll::-webkit-scrollbar-thumb{background:#86a9d3;border-radius:10px;border:2px solid #f1f5f9}.v313-model-table tbody tr{height:43px}.v313-model-table .v314-photo{width:32px;height:36px;object-fit:contain;cursor:zoom-in}
.v313-model-table .v314-photo-cell{width:46px;min-width:46px;padding:3px}
.v313-photo-missing{font-size:8px;color:#8293a9}.v313-photo-overlay{position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,.91);display:flex;align-items:center;justify-content:center;padding:65px 16px 20px}
.v313-photo-overlay img{max-height:100%;max-width:100%;object-fit:contain}.v313-photo-overlay button{position:absolute;top:14px;left:14px;border:0;border-radius:8px;padding:12px 16px;background:#fff;color:#12497e;font-weight:900;cursor:pointer}
@media(max-width:900px){.v313-head-right{width:100%;justify-content:space-between}.v313-model-scroll{height:min(62dvh,570px)!important;max-height:min(62dvh,570px)!important}}

.v329-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:8px}
.v329-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin:10px 0}
.v329-fields label{font-size:9.5px;font-weight:850;color:#436584}
.v329-fields input{display:block;width:100%;height:33px;margin-top:4px;padding:5px 7px;border:1px solid #c3d4e6;border-radius:7px;font-size:12px}
.v329-pair{display:flex;justify-content:space-between;gap:9px;align-items:center;border-bottom:1px solid #e3edf6;padding:10px 0;font-size:10.5px}
.v329-pair b{white-space:nowrap;text-align:right;color:#174d89}.v329-total{background:#edf6ff;border-radius:7px;padding:10px 6px;font-weight:850}
@media(max-width:900px){.v329-layout{grid-template-columns:1fr}.v329-fields{gap:4px}.v329-fields label{font-size:9px}}

.v330-source{display:flex;gap:8px;align-items:center;flex-wrap:wrap;border:1px solid #dce8f4;border-radius:9px;background:#f4f8fc;padding:8px 10px;margin:8px 0;font-size:10px;color:#496989}
.v330-source b{color:#104876}.v330-layout{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,.75fr);gap:8px;align-items:start;margin-top:8px}
.v330-list{display:grid;gap:5px;padding:8px}.v330-item{display:flex;gap:8px;align-items:center;min-height:58px;border:1px solid #e0eaf2;background:#fff;border-radius:9px;padding:8px 10px}
.v330-indicator{width:8px;height:30px;border-radius:99px;flex-shrink:0}.v330-indicator.blue{background:#2173e8}.v330-indicator.green{background:#20af77}.v330-indicator.violet{background:#8868e5}
.v330-item-main{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}.v330-item-main b{font-size:12px;color:#143e70}.v330-item-main small{font-size:10px;color:#6a8098}
.v330-weight{color:#144e92;font-size:12px}.v330-item strong{min-width:75px;text-align:right;color:#164b8d;font-size:15px}
.v330-compact .v330-item{min-height:49px;padding:6px 9px}.v330-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;padding:9px}
.v330-card{display:flex;flex-direction:column;gap:8px;border:1px solid #e1eaf4;border-radius:9px;padding:12px;min-width:0;background:#fff}.v330-card.blue{background:#f4f8ff}.v330-card.green{background:#f2fbf7}.v330-card.violet{background:#f7f4ff}
.v330-card span{font-size:11px;font-weight:800;color:#284f79}.v330-card b{font-size:20px;color:#0b4383}.v330-card strong{font-size:14px;color:#1a5ca2}.v330-card small{font-size:10px;color:#68829e}
.v330-bar{height:7px;border-radius:99px;background:#e8eef6;overflow:hidden}.v330-bar i{height:100%;display:block;border-radius:inherit;background:#2879eb}.v330-bar i.green{background:#1fb27a}.v330-bar i.violet{background:#8e6bea}
.v330-info-line{display:flex;gap:12px;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #edf2f7;font-size:10.5px}.v330-info-line b{color:#16487c;text-align:right}
.v330-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;padding:10px}.v330-stats>div{background:#f5f9fd;padding:9px;border:1px solid #e7eef5;border-radius:7px}.v330-stats span{display:block;color:#71869b;font-size:10px}.v330-stats b{display:block;margin-top:6px;font-size:15px;color:#164779}
.v330-ranking{min-width:880px}.v330-ranking td{text-align:center}.v330-ranking td.left{text-align:left}
@media(max-width:950px){.v330-layout{grid-template-columns:1fr}.v330-stats{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:640px){.v330-cards{gap:4px;padding:5px}.v330-card{padding:6px;gap:5px}.v330-card b{font-size:16px}.v330-card span{font-size:9px}.v330-card small{font-size:9px}.v330-item-main b{font-size:10px}.v330-item strong{font-size:12px}.v330-item-main small{font-size:9px}.v330-stats span{font-size:9px}.v330-stats b{font-size:12px}}

.v313-model-pagination{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;padding:9px 10px;background:#f5faff;border-top:1px solid #d8e5f4;font-weight:800;font-size:11px;color:#194877}
.v313-model-pagination button{font-size:11px;font-weight:800;border:1px solid #b9d1eb;background:#fff;border-radius:7px;padding:8px 12px;cursor:pointer;color:#124b85}
.v313-model-pagination button:disabled{opacity:.35;cursor:not-allowed}
.v313-model-scroll:focus-visible{outline:2px solid #3280e8;outline-offset:-2px}
</style>''';

    js=r'''<script id="v313-js">(function(){
if(window.__V313_BONUS_VISUAL_CUTS)return;window.__V313_BONUS_VISUAL_CUTS=true;
var S={bonus:1,section:"summary",store:"Compañía",month:"",catalog:"Abrigador",data:null,seq:0,refreshCount:0,refreshTimer:null,initialStatus:null,modelScroll:{},modelPage:{},controller:null,cache:new Map()};
function q(s,r){return(r||document).querySelector(s)}function qa(s,r){return Array.from((r||document).querySelectorAll(s))}
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c]})}
function n(v){var x=Number(v);return Number.isFinite(x)?x:0}function pc(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{maximumFractionDigits:1})+"%"}function nf(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{maximumFractionDigits:1})}
function money(v){return v==null?"N/D":n(v).toLocaleString("es-MX",{style:"currency",currency:"MXN",maximumFractionDigits:0})}
function dateMx(v){if(!v)return"Pendiente";var a=String(v).slice(0,10).split("-");return a.length===3?a[2]+"/"+a[1]+"/"+a[0]:v}
function api(u,opts){return fetch(u,{credentials:"same-origin",...(opts||{})}).then(function(r){if(!r.ok)return r.text().then(function(t){throw new Error(t||("HTTP "+r.status))});return r.json()})}
function ensure(){var p=q("#page-bonuses"),main=q("main.main");if(main&&!p){p=document.createElement("section");p.className="page";p.id="page-bonuses";main.appendChild(p)}if(p&&!q("#v313Host",p))p.insertAdjacentHTML("afterbegin","<div id=\"v313Host\"></div>");return p}
function activate(){ensure();try{MAIN="bonuses"}catch(_e){}document.body.dataset.v313="1";document.body.removeAttribute("data-v302");document.body.removeAttribute("data-v312");qa("[data-main]").forEach(function(x){x.classList.toggle("active",x.dataset.main==="bonuses")});qa(".page").forEach(function(x){x.classList.toggle("active",x.id==="page-bonuses")});var t=q("#heroTitle"),s=q("#heroSub");if(t)t.textContent="Bonos";if(s)s.textContent="Indicadores para habilitar el bono de colaboradores"}
function filters(d){return"<div class=\"v313-filters\"><div class=\"v313-field\"><label>Periodo</label><select id=\"v313Month\">"+(d.months||[]).map(function(x){return"<option value=\""+esc(x.value)+"\" "+(x.value===d.month?"selected":"")+">"+esc(x.label)+"</option>"}).join("")+"</select></div><div class=\"v313-field\"><label>Tienda</label><select id=\"v313Store\">"+(d.stores||[]).map(function(x){return"<option "+(x===d.selected_store?"selected":"")+">"+esc(x)+"</option>"}).join("")+"</select></div></div>"}
function bonusTabs(d){var h=[1,2,3,4,5,6].map(function(i){return"<button data-v313-bonus=\""+i+"\" class=\""+(S.bonus===i&&S.section!=="initial-upload"?"active":"")+"\">Bono "+i+"</button>"}).join("");if(d&&d.can_admin)h+="<button data-v313-initial=\"1\" class=\""+(S.section==="initial-upload"?"active":"")+"\">Corte inicial</button>";return"<div class=\"v313-bonus"+(d&&d.can_admin?" v313-bonus-admin":"")+"\">"+h+"</div>"}
function tabs(){
var xs,cls="";
if(S.bonus===2){
 // Replicar exactamente las cuatro vistas del Bono 1.
 xs=[["summary","Resumen General"],["ranking","Ranking de Tiendas"],["panorama","Panorama por Tienda"],["models","Modelos a Detalle"]];
}else{
 xs=[["summary","Resumen General"],["ranking","Ranking de Tiendas"],["panorama","Panorama por Tienda"],["models","Modelos a Detalle"]];
}
return"<div class=\"v313-tabs"+cls+"\">"+xs.map(function(x){return"<button data-v313-section=\""+x[0]+"\" class=\""+(S.section===x[0]?"active":"")+"\">"+x[1]+"</button>"}).join("")+"</div>"
}


function cutbar(d){
if(d.b2_cohort){
 var status=d.b2_status==="pending"?"Preparando cartera del corte inicial · actualización automática":d.b2_status==="error"?"Error al validar el corte":d.b2_status==="missing"?"Falta el corte inicial de Capacidades":"Cartera consultable";
 return "<div class=\"v313-cutbar\"><div class=\"v313-cut\"><span>Regla · Bono 2</span><b>VIGENTE · 0 ventas en 30 días</b></div><div class=\"v313-cut ok\"><span>Última llegada</span><b>Hace 7 días o más al corte inicial</b></div><div class=\"v313-cut current\"><span>Corte inicial evaluado</span><b>"+dateMx(d.cutoff_date)+"</b></div><div class=\"v313-cut\"><span>Estado</span><b>"+status+"</b></div></div>";
}
var sd=d.source_dates||{},opening=sd.opening_capacity,current=sd.current_capacity,processing=d.processing||{};
var hasOpening=!!opening,hasCurrent=!!current,same=hasOpening&&hasCurrent&&((sd.opening_capacity_id&&sd.current_capacity_id)?String(sd.opening_capacity_id)===String(sd.current_capacity_id):String(opening)===String(current));
var status=!hasOpening?"Falta corte inicial":!hasCurrent?"Falta corte actual":same?(processing.capacity?"Preparando cartera inicial":"Esperando segundo corte"):(processing.capacity?"Procesando comparación":"Comparación activa");
return"<div class=\"v313-cutbar\"><div class=\"v313-cut\"><span>Regla de comparación</span><b>Corte más cercano al inicio → corte actual</b></div><div class=\"v313-cut "+(hasOpening?"ok":"wait")+"\"><span>Corte inicial seleccionado</span><b>"+dateMx(opening)+"</b></div><div class=\"v313-cut current "+(!hasCurrent||same?"wait":"ok")+"\"><span>Corte actual</span><b>"+dateMx(current)+"</b></div><div class=\"v313-cut\"><span>Avance</span><b>"+status+"</b></div></div>"
}


function hero(d){if(d.is_v330)return '<div class="v313-hero"><div><b>Bono '+S.bonus+' · '+esc(d.model.name)+'</b><br><span>Seguimiento automático por corte inicial y último corte procesado de Capacidades · '+esc(d.model.design)+'</span></div><span class="tag">'+esc(d.selected_store)+'</span></div>';var names={1:"Modelo actual · 50/30/20",2:"Modelos sin venta · antigüedad ≥7 días",3:"Rubros críticos · 2 de 3",4:"Matriz integral · imagen 1",5:"Mejora contra sí misma · 3 de 4",6:"Cumplimiento sostenido · 4 semanas"};return"<div class=\"v313-hero\"><div><b>Bono "+S.bonus+" · "+names[S.bonus]+"</b><br><span>"+esc((d.selected&&d.selected.formula)||({1:"Bono 1 conserva exactamente su cálculo original.",2:"Venta ≥100% + reducción DDI mínima 50%.",3:"Venta ≥100% + mínimo 2 de 3 rubros con DDI reducido ≥50%.",4:"Venta ≥100% + matriz DDI / Existencia / Inversión / Modelos.",5:"Venta ≥100% + mejora en mínimo 3 de 4 indicadores.",6:"Venta ≥100% + cuatro cortes semanales consecutivos."})[S.bonus])+"</span></div><span class=\"tag\">"+esc(d.selected_store)+"</span></div>"}
function kpi(label,val,note,cls){return"<div class=\"v313-kpi\"><span>"+esc(label)+"</span><b class=\""+(cls||"")+"\">"+esc(val)+"</b><small>"+esc(note||"")+"</small></div>"}
function topKpis(d){var s=d.summary||{},inv=s.inventory||{},out=[];
 if(d.is_v330)return [
 kpi("Ventas vs Meta",pc(s.sales_pct),"Fuente de ventas y metas"),
 kpi("DDI reducido (modelos)",pc(s.ddi_models_pct),"Sobre la cartera inicial"),
 kpi("Reducción DDI promedio",pc(inv.ddi_reduction_pct),"DDI inicial vs actual"),
 kpi("Asistencia tienda",pc(s.attendance_reference),s.attendance_provisional?"20% · 100% provisional":"20% · pendiente individual"),
 kpi("Modelos con DDI reducido",s.ddi_improved_models==null?"Pendiente":nf(s.ddi_improved_models),"De "+(s.ddi_models==null?"N/D":nf(s.ddi_models))),
 kpi("Variación inversión",money(inv.capital_variation_mxn),"Informativa; no suma puntos")
 ].join("");
if(d.b2_cohort){
 var z=d.b2_stats||{},pending=!!(d.processing||{}).capacity;
 return [
  kpi("Modelos en cartera",pending?"Preparando":nf(z.models),"Vigentes · 3 catálogos"),
  kpi("Venta últimos 30 días",pending?"—":"0 piezas","Requisito obligatorio"),
  kpi("Última entrada","≥ 7 días","Antigüedad en el corte inicial"),
  kpi("DDI inicial promedio",z.avg_ddi==null?"N/D":nf(z.avg_ddi),"Valor del corte inicial"),
  kpi("Existencia inicial",nf(z.existence),"Piezas del corte inicial"),
  kpi("Inversión inicial",money(z.investment),"En modelos sin venta")
 ].join("");
}out.push(kpi("Venta vs Meta",pc(s.sales_pct),"Meta obligatoria 100%",s.sales_pct==null?"warn":n(s.sales_pct)>=100?"good":"bad"));if(S.bonus===1){var l=d.legacy_components||{};out.push(kpi("DDI por Cat",pc(l.ddi_pct),"Peso 30%"));out.push(kpi("Asistencia",pc(l.attendance_pct),l.attendance_provisional_stores?"20% · provisional":"Peso 20%"));out.push(kpi("Resultado promedio",pc(l.legacy_score_avg),"Sólo scores completos"));out.push(kpi("Tiendas con score",nf(l.stores_with_score)+" de "+nf(s.stores_total),"Bono 1"));out.push(kpi("Corte actual",dateMx((d.source_dates||{}).current_capacity),"Capacidades"));return out.join("")}out.push(kpi("DDI inicial",nf(inv.initial_ddi),"Corte inicial"));out.push(kpi("DDI actual",nf(inv.current_ddi),"Último corte"));out.push(kpi("Reducción DDI",pc(inv.ddi_reduction_pct),"Objetivo base ≥50%",inv.ddi_reduction_pct!=null&&n(inv.ddi_reduction_pct)>=50?"good":"bad"));out.push(kpi("Tiendas habilitadas",nf(s.stores_enabled)+" de "+nf(s.stores_total),"Según Bono "+S.bonus));out.push(kpi("Asistencia",pc(s.attendance_reference),"Referencia · no suma puntos","warn"));return out.join("")}
function componentsB1(d){var l=d.legacy_components||{},p=l.legacy_score_avg;return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Componentes originales del Bono 1</span><span>50 / 30 / 20</span></div><div class=\"v313-body\"><div class=\"v313-components\"><div class=\"v313-comp sales\"><div class=\"top\">50% · Venta vs Meta</div><div class=\"value\"><b>"+pc(l.sales_pct)+"</b><small>Base Muertos/Cambios + Meta</small></div></div><div class=\"v313-comp ddi\"><div class=\"top\">30% · DDI por Cat</div><div class=\"value\"><b>"+pc(l.ddi_pct)+"</b><small>Capacidades</small></div></div><div class=\"v313-comp att\"><div class=\"top\">20% · Asistencia</div><div class=\"value\"><b>"+pc(l.attendance_pct)+"</b><small>"+(l.attendance_provisional_stores?"100% provisional sin captura":"Captura autorizada")+"</small></div></div></div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Resultado Bono 1</span><span>Sin cambios</span></div><div class=\"v313-score\"><div class=\"v313-ring\" style=\"--p:"+Math.max(0,Math.min(100,n(p)))+"\"><div><b>"+pc(p)+"</b><small>Promedio compañía</small></div></div><div><b style=\"font-size:12px\">Cálculo original V293</b><div class=\"v313-note\">No se modificó fórmula, ponderaciones ni criterios.</div></div></div></section>"}
function levelsB2(d){var a=d.ranking||[],counts=[0,0,0,0,0];a.forEach(function(x){counts[Math.max(0,Math.min(4,Number(x.level)||0))]++});var labs=["<50%","50–59%","60–74%","75–89%","≥90%"];return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Escalones de reducción DDI</span><span>Mínimo 50%</span></div><div class=\"v313-body\"><div class=\"v313-levels\">"+counts.map(function(c,i){return"<div class=\"v313-level "+(i?"l"+i:"off")+"\"><b>"+c+"</b><span>"+labs[i]+"</span><small style=\"display:block\">"+(i?"Nivel "+i:"No habilita")+"</small></div>"}).join("")+"</div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Puerta del bono</span><span>Venta + DDI</span></div><div class=\"v313-gate\"><div><b>"+pc((d.summary||{}).inventory?.ddi_reduction_pct)+"</b><span>Reducción DDI compañía<br>Venta debe estar en 100% o más</span></div></div></section>"}
function rubrosB3(d){var r=(d.summary||{}).rubros||{};return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Rubros críticos</span><span>Se requieren 2 de 3</span></div><div class=\"v313-body\"><div class=\"v313-bars\">"+CAT().map(function(c){var v=r[c],ok=v!=null&&n(v)>=50;return"<div class=\"v313-barbox\"><div class=\"v313-bartrack\"><i style=\"height:"+Math.max(2,Math.min(100,n(v)))+"%\"></i></div><b class=\""+(ok?"good":"bad")+"\">"+pc(v)+"</b>"+c+"<small style=\"display:block\">"+(ok?"Cumple ≥50%":"Pendiente / <50%")+"</small></div>"}).join("")+"</div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Regla</span><span>Opción 4 elegida</span></div><div class=\"v313-gate\"><div><b>2 / 3</b><span>Abrigador · Licencias · Básicos<br>cada rubro debe reducir DDI al menos 50%</span></div></div></section>"}
function CAT(){return["Abrigador","Licencias","Básicos"]}
function matrixB4(d){var inv=(d.summary||{}).inventory||{},score=(d.summary||{}).score_avg,rows=[["DDI","ddi_reduction_pct",50,30],["Existencia","existence_reduction_pct",30,25],["Inversión","investment_reduction_pct",30,25],["Modelos","models_reduction_pct",20,20]];return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Matriz integral · diseño aprobado</span><span>Score mínimo 80</span></div><div class=\"v313-body\"><div class=\"v313-matrixcards\">"+rows.map(function(x){var v=inv[x[1]],ok=v!=null&&n(v)>=x[2];return"<div class=\"v313-mcard\"><span>"+x[0]+" · peso "+x[3]+"%</span><b class=\""+(ok?"good":"bad")+"\">"+pc(v)+"</b><small>Objetivo ≥"+x[2]+"% &nbsp; <span class=\"v313-check "+(ok?"":"no")+"\">"+(ok?"✓":"×")+"</span></small></div>"}).join("")+"</div><div class=\"v313-score\"><div class=\"v313-ring\" style=\"--p:"+Math.max(0,Math.min(100,n(score)))+"\"><div><b>"+pc(score)+"</b><small>Score integral</small></div></div><div><b style=\"font-size:12px\">"+(score!=null&&n(score)>=80?"Habilita por matriz":"Aún no habilita por matriz")+"</b><div class=\"v313-note\">DDI 30% · Existencia 25% · Inversión 25% · Modelos 20%</div></div></div></div></section>"}
function improveB5(d){var ch=(d.summary||{}).changes||{},rows=[["DDI","ddi_reduction_pct"],["Existencia","existence_reduction_pct"],["Inversión","investment_reduction_pct"],["Modelos","models_reduction_pct"]];return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Mejora contra sí misma</span><span>Se requieren 3 de 4</span></div><div class=\"v313-body\"><div class=\"v313-pairs\">"+rows.map(function(x){var z=ch[x[1]]||{},delta=z.current!=null&&z.previous!=null?n(z.current)-n(z.previous):null,ok=delta!=null&&delta>0;return"<div class=\"v313-pair\"><b>"+x[0]+"</b><div class=\"nums\"><span>Anterior "+pc(z.previous)+"</span><span>Actual "+pc(z.current)+"</span></div><div class=\"delta "+(ok?"good":"bad")+"\">"+(delta==null?"N/D":(delta>=0?"+":"")+delta.toLocaleString("es-MX",{maximumFractionDigits:1})+" pp")+"</div><small>"+(ok?"Mejoró":"No mejoró")+"</small></div>"}).join("")+"</div></div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Puerta</span><span>Periodo anterior vs actual</span></div><div class=\"v313-gate\"><div><b>"+nf((d.summary||{}).improved_avg)+" / 4</b><span>Promedio de indicadores mejorados</span></div></div></section>"}
function weeksB6(d){var sel=d.selected||{},weeks=((sel.extra||{}).weeks||[]).slice(-4),slots=[0,1,2,3].map(function(i){return weeks[i]||null});return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Cumplimiento sostenido</span><span>4 cortes semanales consecutivos</span></div><div class=\"v313-body\"><div class=\"v313-weeks\">"+slots.map(function(w,i){if(!w)return"<div class=\"v313-week\"><b>Semana "+(i+1)+"</b><div class=\"dot\">—</div><small>Sin corte</small></div>";return"<div class=\"v313-week "+(w.meets?"pass":"fail")+"\"><b>"+esc(w.week||("Semana "+(i+1)))+"</b><div class=\"dot\">"+(w.meets?"✓":"×")+"</div><small>"+dateMx(w.date)+"<br>"+(w.meets?"Cumple objetivos":"No cumple todos")+"</small></div>"}).join("")+"</div>"+(d.weekly_pending?"<div class=\"v313-note\">Procesando los cortes semanales de Capacidades…</div>":"")+"</div></section><section class=\"v313-panel\" style=\"margin-top:7px\"><div class=\"v313-ph\"><span>Racha actual</span><span>Se necesitan 4</span></div><div class=\"v313-gate\"><div><b>"+nf((sel.extra||{}).streak)+" / 4</b><span>semanas consecutivas</span></div></div></section>"}
function b2Visual(d){
 var z=d.b2_stats||{},counts=z.catalog_counts||{},pending=d.b2_status==="pending";
 var bars=CAT().map(function(c){
  var count=n(counts[c]),total=Math.max(1,n(z.models));
  return "<div class=\"v313-barbox\"><div class=\"v313-bartrack\"><i style=\"height:"+Math.max(2,Math.round(100*count/total))+"%\"></i></div><b>"+nf(count)+"</b>"+c+"<small style=\"display:block\">Venta 30 días = 0</small></div>";
 }).join("");
 return "<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Panorama de modelos sin venta · Bono 2</span><span>Vigente · última entrada hace ≥7 días</span></div><div class=\"v313-body\"><div class=\"v313-bars\">"+bars+"</div><div class=\"v313-note\">"+(pending?"Procesando archivo de Capacidades. Se actualizará el listado al terminar.":d.source_error?esc(d.source_error):"Los modelos se seleccionan desde el corte inicial, por tienda e ID. Se excluyen las últimas llegadas de 0 a 6 días y cualquier modelo con venta en 30 días.")+"</div></div></section>"
}


function v330Val(v,unit){return v==null?"Pendiente":(unit==="percent"?pc(v):unit==="money"?money(v):nf(v))}
function v330Bar(v,tone){return '<div class="v330-bar"><i class="'+(tone||'blue')+'" style="width:'+Math.max(0,Math.min(100,n(v)))+'%"></i></div>'}
function v330Metric(label,weight,value,caption,tone){
 return '<div class="v330-item"><span class="v330-indicator '+tone+'"></span><div class="v330-item-main"><b>'+esc(label)+'</b><small>'+esc(caption||'')+'</small></div><b class="v330-weight">'+(weight==null?"Indicador":weight+"%")+'</b><strong>'+v330Val(value,"percent")+'</strong></div>';
}
function v330Investment(d){
 var inv=(d.summary||{}).inventory||{};
 return '<section class="v313-panel v330-finance"><div class="v313-ph"><span>Inversión y DDI · cortes reales</span><span>Inversión informativa</span></div><div class="v313-body">'
 +'<div class="v330-info-line"><span>DDI inicial / último corte</span><b>'+v330Val(inv.initial_ddi)+' / '+v330Val(inv.current_ddi)+' días</b></div>'
 +'<div class="v330-info-line"><span>Reducción DDI promedio</span><b>'+v330Val(inv.ddi_reduction_pct,"percent")+'</b></div>'
 +'<div class="v330-info-line"><span>Inversión inicial</span><b>'+v330Val(inv.initial_investment,"money")+'</b></div>'
 +'<div class="v330-info-line"><span>Inversión último corte</span><b>'+v330Val(inv.current_investment,"money")+'</b></div>'
 +'<div class="v330-info-line"><span>Variación neta de inversión</span><b>'+v330Val(inv.capital_variation_mxn,"money")+'</b></div>'
 +'<div class="v313-note">La inversión es exclusivamente informativa y no genera puntos. Su variación neta no equivale necesariamente a capital vendido: pueden existir entradas, traspasos y ajustes.</div></div></section>';
}
function v330StoreData(d){
 var s=d.summary||{},inv=s.inventory||{};
 return {sale:s.sales_pct,ddi:s.ddi_models_pct,att:s.attendance_reference,models:s.ddi_models,improved:s.ddi_improved_models,inv:inv};
}
function v330Source(d){
 var p=d.processing||{},m=d.model||{},sd=d.source_dates||{};
 var status=p.capacity?"Procesando datos de Capacidades":!sd.opening_capacity?"Falta asignar corte inicial":!m.cut_comparable?"Esperando un nuevo corte de Capacidades":"Comparación entre cortes activa";
 return '<div class="v330-source"><b>'+esc(status)+'</b><span>Corte inicial: '+dateMx(sd.opening_capacity)+' · Último corte: '+dateMx(sd.current_capacity)+'</span><span>Los datos se toman automáticamente de Análisis Comercial; no existe captura manual de resultados.</span></div>';
}
function v330Content(d){
 var x=v330StoreData(d),note='<div class="v313-note">Asistencia: 20% de ponderación. Cuando no existe captura se muestra 100% provisional (no verificado), sin autorizar pagos; los datos reales de asistencia tienen prioridad.</div>';
 var s50=v330Metric("Ventas vs. Meta",50,x.sale,"Resultado real de la tienda","blue");
 var d30=v330Metric("Reducción de DDI",30,x.ddi,"Modelos con DDI menor al corte inicial","green");
 var a20=v330Metric("Asistencia",20,x.att,"Referencia de tienda, no individual","violet");
 var body="";
 if(S.bonus===3){
    // Boceto 3.2 · lista de tres indicadores con sus ponderaciones.
    body='<section class="v313-panel"><div class="v313-ph"><span>Indicadores de evaluación</span><span>Boceto 3.2 · Lista</span></div><div class="v330-list">'+s50+d30+a20+'</div><div class="v313-note">Puntos ponderados: 50% ventas, 30% reducción real de DDI y 20% asistencia. Inversión no puntúa.</div></section>';
 }else if(S.bonus===4){
    // Boceto 4.1 · tarjetas de detalle para cada criterio independiente.
    var cards=[["Ventas vs. Meta","50%",x.sale,"blue","Objetivo independiente; tramos de cumplimiento"],["Reducción de DDI","30%",x.ddi,"green","Objetivo independiente; modelos mejorados"],["Asistencia","20%",x.att,"violet","Participación proporcional; referencia de tienda"]];
    body='<section class="v313-panel"><div class="v313-ph"><span>Indicadores por objetivo independiente</span><span>Boceto 4.1 · Tarjetas</span></div><div class="v330-cards">'+cards.map(function(c){return '<div class="v330-card '+c[3]+'"><span>'+c[0]+'</span><b>'+c[1]+'</b><strong>'+v330Val(c[2],"percent")+'</strong>'+v330Bar(c[2],c[3])+'<small>'+c[4]+'</small></div>'}).join('')+'</div><div class="v313-note">Ventas y DDI se evalúan en tramos: &lt;80%=0%, 80–&lt;100%=50%, 100–&lt;110%=100%, ≥110%=120%. Asistencia conserva un peso fijo del 20% sin aceleradores.</div></section>';
 }else if(S.bonus===5){
    // Boceto 5.2 · lista compacta, con DDI condicionante no simulado.
    body='<section class="v313-panel"><div class="v313-ph"><span>Indicadores de evaluación</span><span>Boceto 5.2 · Lista compacta</span></div><div class="v330-list v330-compact">'+v330Metric("Ventas vs. Meta",80,x.sale,"Componente comercial de referencia","blue")+v330Metric("Reducción de DDI",null,x.ddi,"Condiciona multiplicador; no suma un peso adicional","green")+a20+'</div><div class="v313-note">Multiplicador por DDI: pendiente de un umbral autorizado de reducción. Se muestra el avance real, sin activación automática ni proyección de pagos.</div></section>';
 }else{
    // Boceto 6.1 · tarjetas de resultado de tienda + asistencia individual.
    body='<section class="v313-panel"><div class="v313-ph"><span>Indicadores colectivos por tienda</span><span>Boceto 6.1 · Tarjetas</span></div><div class="v330-cards v330-store-cards"><div class="v330-card blue"><span>Ventas vs. Meta</span><b>48%</b><strong>'+v330Val(x.sale,"percent")+'</strong>'+v330Bar(x.sale,"blue")+'<small>Resultado de tienda</small></div><div class="v330-card green"><span>Reducción de DDI</span><b>32%</b><strong>'+v330Val(x.ddi,"percent")+'</strong>'+v330Bar(x.ddi,"green")+'<small>Resultado de tienda</small></div><div class="v330-card violet"><span>Asistencia</span><b>20%</b><strong>'+v330Val(x.att,"percent")+'</strong>'+v330Bar(x.att,"violet")+'<small>Evaluación individual pendiente; referencia por tienda</small></div></div></section>';
 }
 var details='<div class="v330-stats"><div><span>Modelos del corte inicial</span><b>'+(x.models==null?"Pendiente":nf(x.models))+'</b></div><div><span>Modelos con reducción de DDI</span><b>'+(x.improved==null?"Pendiente":nf(x.improved))+'</b></div><div><span>Porcentaje de modelos mejorados</span><b>'+v330Val(x.ddi,"percent")+'</b></div></div>';
 return '<div class="v330-layout"><div>'+body+'<section class="v313-panel" style="margin-top:7px"><div class="v313-ph"><span>Avance de la cartera de modelos</span><span>Sin simulaciones</span></div>'+details+'</section></div>'+v330Investment(d)+'</div>'+note;
}
function v330Ranking(d,limit){
 var rows=(d.ranking||[]).slice();if(limit)rows=rows.slice(0,limit);
 var columns='<th>#</th><th class="left">Tienda</th><th>Venta vs. Meta</th><th>DDI mejorados</th><th>Reducción DDI</th><th>Asistencia tienda</th><th>Variación inversión</th><th>Estado</th>';
 var body=rows.map(function(r){
  var i=r.inventory||{};
  return '<tr data-v313-store="'+esc(r.store)+'" style="cursor:pointer"><td>'+(r.rank==null?"—":r.rank)+'</td><td class="left"><b>'+esc(r.store)+'</b></td><td>'+v330Val(r.sales_pct,"percent")+'</td><td>'+v330Val(r.ddi_models_pct,"percent")+'</td><td>'+v330Val(r.ddi_reduction_pct,"percent")+'</td><td>'+v330Val(r.attendance_reference,"percent")+'</td><td>'+v330Val(i.capital_variation_mxn,"money")+'</td><td>'+esc(r.classification||"")+'</td></tr>';
 }).join('');
 return '<section class="v313-panel"><div class="v313-ph"><span>Ranking de tiendas · indicadores reales</span><span>Sin importes de bono</span></div><div class="v313-scroll"><table class="v313-table v330-ranking"><thead><tr>'+columns+'</tr></thead><tbody>'+body+'</tbody></table></div><div class="v313-note">Orden por evaluación referencial de tienda cuando hay datos completos; de lo contrario, por modelos con DDI reducido. No representa incentivos pagaderos.</div></section>';
}
function v330Visual(d){return v330Source(d)+v330Content(d)}
function visual(d){if(d.is_v330)return v330Visual(d);if(d.b2_cohort)return b2Visual(d);if(S.bonus===1)return componentsB1(d);if(S.bonus===2)return levelsB2(d);if(S.bonus===3)return rubrosB3(d);if(S.bonus===4)return matrixB4(d);if(S.bonus===5)return improveB5(d);return weeksB6(d)}
function indicator(e){if(!e)return"N/D";if(S.bonus===1)return pc(e.indicator);if(S.bonus===2)return pc((e.extra||{}).ddi_reduction_pct)+" · N"+(e.level||0);if(S.bonus===3)return nf((e.extra||{}).rubros_met)+" de 3";if(S.bonus===4)return pc((e.extra||{}).score);if(S.bonus===5)return nf((e.extra||{}).improved)+" de 4";return nf((e.extra||{}).streak)+" de 4"}
function ranking(d,limit){if(d.is_v330)return v330Ranking(d,limit);if(d.b2_cohort){
 var arr=(d.ranking||[]).slice();if(limit)arr=arr.slice(0,limit);
 return "<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Ranking de tiendas · Bono 2</span><span>Modelos que cumplen criterios</span></div><div class=\"v313-scroll\"><table class=\"v313-table\"><thead><tr><th>#</th><th class=\"left\">Tienda</th><th>Modelos</th><th>Vta 30d</th><th>DDI prom.</th><th>Inversión inicial</th><th>Estado</th></tr></thead><tbody>"+arr.map(function(e){return "<tr data-v313-store=\""+esc(e.store)+"\" style=\"cursor:pointer\"><td>"+(e.rank||"—")+"</td><td class=\"left\"><b>"+esc(e.store)+"</b></td><td>"+nf(e.models)+"</td><td>0</td><td>"+nf(e.avg_ddi)+"</td><td>"+money(e.investment)+"</td><td>"+esc(e.classification)+"</td></tr>"}).join("")+"</tbody></table></div></section>"
}
var a=(d.ranking||[]).slice();if(limit)a=a.slice(0,limit);return"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Ranking de Tiendas · Bono "+S.bonus+"</span><span>Mejor a peor</span></div><div class=\"v313-scroll\"><table class=\"v313-table\"><thead><tr><th>#</th><th class=\"left\">Tienda</th><th>Venta</th><th>Indicador</th><th>Asistencia ref.</th><th>Estado</th></tr></thead><tbody>"+a.map(function(e){return"<tr data-v313-store=\""+esc(e.store)+"\" style=\"cursor:pointer\"><td>"+(e.rank==null?"—":e.rank)+"</td><td class=\"left\"><b>"+esc(e.store)+"</b></td><td>"+pc(e.sales_pct)+"</td><td>"+esc(indicator(e))+"</td><td>"+pc(e.attendance_reference)+"</td><td><span class=\"v313-status "+(!e.ready?"na":e.eligible?"":"no")+"\">"+esc(e.classification)+"</span></td></tr>"}).join("")+"</tbody></table></div></section>"}
function summary(d){if(d.is_v330)return cutbar(d)+hero(d)+'<div class="v313-kpis">'+topKpis(d)+'</div>'+v330Visual(d)+'<div style="margin-top:8px">'+v330Ranking(d,10)+'</div>';return cutbar(d)+hero(d)+"<div class=\"v313-kpis\">"+topKpis(d)+"</div>"+visual(d)+"<div style=\"margin-top:8px\">"+ranking(d,10)+"</div><div class=\"v313-note\">Cálculo estimado: 20% asistencia individual, inversión informativa. Sin datos completos no se genera pago.</div>";return cutbar(d)+hero(d)+"<div class=\"v313-kpis\">"+topKpis(d)+"</div><div class=\"v313-main\"><div>"+visual(d)+"</div><div>"+ranking(d,10)+(d.b2_cohort?"<div class=\"v313-note\">Seguimiento específico de modelos sin venta 30 días y llegada reciente. El diseño replica al Bono 1; la elegibilidad de un pago no se calcula sin una base de DDI comparable.</div>":d.is_v329?"<div class=\"v313-note\">El 20% de asistencia requiere validación individual. La inversión sólo se informa, no suma puntos. Los importes son simulaciones, no nómina.</div>":"<div class=\"v313-note\">Asistencia en Bonos 2–6 es sólo referencia; 1 falta descalifica al colaborador en la validación individual. El costo del bono no se calcula en esta pantalla.</div>")+"</div></div>"}
function panorama(d){if(d.selected_store==="Compañía")return cutbar(d)+hero(d)+"<div class=\"v313-note\">Selecciona una tienda para ver su panorama completo.</div>"+ranking(d,0);return summary(d)}
function modelTable(d,rows,title,showCatalog,subtabsHtml){
if(d.selected_store==="Compañía")return cutbar(d)+hero(d)+"<div class=\"v313-note\">Selecciona una tienda para consultar los modelos de su cartera.</div>"+ranking(d,0);
var all=d.details||[],processing=d.processing||{},sd=d.source_dates||{},emptyTitle="",emptyText="";
 var pageKey=[S.month,S.store,S.bonus,S.section,S.catalog].join("|");
 var pageSize=30,pageMax=Math.max(1,Math.ceil(rows.length/pageSize));
 var page=Math.max(0,Math.min(pageMax-1,S.modelPage[pageKey]||0));
 var visible=rows.slice(page*pageSize,(page+1)*pageSize);
if(!rows.length){
 if(processing.capacity){emptyTitle="Preparando la cartera inicial";emptyText="Capacidades está reconstruyendo el listado para el corte seleccionado. Esta pantalla se actualizará automáticamente cuando termine."}
 else if(!sd.opening_capacity){emptyTitle="Falta un corte inicial válido";emptyText="No se usará una Capacidades antigua de otro mes. Carga el corte más cercano al inicio de "+esc((d.period_label||d.month||"este periodo"))+" para construir la comparación."}
 else if(!all.length){emptyTitle="No hay modelos elegibles para esta tienda";emptyText="La cartera se forma con modelos de los rubros Abrigador, Licencias y Básicos que tienen DDI inicial >90 e inversión superior al promedio de su catálogo."}
 else{emptyTitle="Sin modelos en "+title;emptyText="No hay modelos de este rubro que cumplan los criterios de la cartera inicial. Revisa los demás rubros o la clasificación del archivo de Capacidades."}
}
var head="<th data-v314-photo-head=\"1\">Foto</th><th class=\"left\">ID</th><th class=\"left\">Modelo</th>"+(showCatalog?"<th>Rubro</th>":"")+"<th>DDI inicial</th><th>DDI actual</th><th>Red. DDI</th><th>Exist. inicial</th><th>Exist. actual</th><th>Inv. inicial</th><th>Inv. actual</th><th>Red. inversión</th>";
var bodyRows=visible.map(function(r){var id=String(r.id_art||"").trim(),valid=/^\d{1,15}$/.test(id),photo=valid?"<img class=\"v314-photo v313-photo\" alt=\"Foto ID "+esc(id)+"\" loading=\"lazy\" decoding=\"async\" src=\"/api/bonuses/product-photo/"+encodeURIComponent(id)+"\" onerror=\"this.style.display='none';this.nextElementSibling.style.display='inline'\"/><span class=\"v313-photo-missing\" style=\"display:none\">Sin foto</span>":"<span class=\"v313-photo-missing\">Sin foto</span>";return"<tr><td data-v314-photo-cell=\"1\" class=\"v314-photo-cell\">"+photo+"</td><td class=\"left\"><b>"+esc(id)+"</b></td><td class=\"left\">"+esc(r.model)+"</td>"+(showCatalog?"<td>"+esc(r.catalog)+"</td>":"")+"<td>"+nf(r.initial_ddi)+"</td><td>"+nf(r.current_ddi)+"</td><td>"+pc(r.ddi_reduction_pct)+"</td><td>"+nf(r.initial_existence)+"</td><td>"+nf(r.current_existence)+"</td><td>"+money(r.initial_investment)+"</td><td>"+money(r.current_investment)+"</td><td>"+pc(r.investment_reduction_pct)+"</td></tr>"}).join("");
if(d.b2_cohort){
 if(!rows.length){
  emptyTitle=d.b2_status==="pending"?"Preparando modelos sin venta":d.b2_status==="missing"?"No hay corte inicial de Capacidades":d.b2_status==="error"?"No se pudo validar el archivo":"No hay modelos que cumplan los criterios";
  emptyText=d.source_error||"Sólo Tipo catálogo VIGENTE, Abrigador/Licencias/Básicos, VTA EN PZAS 30 = 0 y última llegada de hace 7 días o más al corte inicial. Si falta alguna fecha de entrada, el modelo no entra.";
 }
 head="<th data-v314-photo-head=\"1\">Foto</th><th class=\"left\">ID</th><th class=\"left\">Modelo</th>"+(showCatalog?"<th>Rubro</th>":"")+"<th>Venta pzas 30</th><th>Última llegada</th><th>Días desde llegada</th><th>DDI inicial</th><th>Existencia inicial</th><th>Inversión inicial</th>";
 bodyRows=visible.map(function(r){
  var id=String(r.id_art||"").trim(),valid=/^\d{1,15}$/.test(id);
  var photo=valid?"<img class=\"v314-photo v313-photo\" alt=\"Foto ID "+esc(id)+"\" loading=\"lazy\" decoding=\"async\" src=\"/api/bonuses/product-photo/"+encodeURIComponent(id)+"\" onerror=\"this.style.display='none';this.nextElementSibling.style.display='inline'\"/><span class=\"v313-photo-missing\" style=\"display:none\">Sin foto</span>":"<span class=\"v313-photo-missing\">Sin foto</span>";
  return "<tr><td data-v314-photo-cell=\"1\" class=\"v314-photo-cell\">"+photo+"</td><td class=\"left\"><b>"+esc(id)+"</b></td><td class=\"left\">"+esc(r.model)+"</td>"+(showCatalog?"<td>"+esc(r.catalog)+"</td>":"")+"<td>0</td><td>"+dateMx(r.last_arrival)+"</td><td>"+nf(r.arrival_age_days)+"</td><td>"+nf(r.initial_ddi)+"</td><td>"+nf(r.initial_existence)+"</td><td>"+money(r.initial_investment)+"</td></tr>";
 }).join("");
}
var actions="<div class=\"v313-model-actions\" data-v314-export=\"1\"><button type=\"button\" class=\"v313-return-btn\" data-v313-return=\"1\">← Regresar al listado</button><span>"+nf(rows.length)+" modelos · Tipo catálogo: VIGENTE "+(d.b2_cohort?"· 0 ventas 30 días · última llegada ≥7 días ":"")+"· rueda/dedo o usa las páginas (30 modelos por página)</span><div class=\"v313-model-downloads\"><button type=\"button\" data-v313-scroll-up=\"1\" title=\"Subir dentro de la tabla\" "+(rows.length<2?"disabled":"")+">↑</button><button type=\"button\" data-v313-scroll-down=\"1\" title=\"Bajar dentro de la tabla\" "+(rows.length<2?"disabled":"")+">↓</button><button type=\"button\" data-v313-download=\"xlsx\" "+(rows.length?"":"disabled")+">↓ Descargar Excel</button><button type=\"button\" data-v313-download=\"pdf\" "+(rows.length?"":"disabled")+">↓ Descargar PDF</button></div></div><div id=\"v313ExportNotice\" role=\"status\" aria-live=\"polite\" class=\"v313-export-notice\" hidden></div>";
return cutbar(d)+hero(d)+(subtabsHtml||"")+"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Modelos a Detalle · "+esc(title)+"</span><span>"+esc(d.selected_store)+" · "+nf(rows.length)+" modelos</span></div>"+actions+"<div class=\"v313-scroll v313-model-scroll\" tabindex=\"0\" role=\"region\" aria-label=\"Listado de modelos, usa rueda o dedo para desplazar\"><table class=\"v313-table v313-model-table\"><thead><tr>"+head+"</tr></thead><tbody>"+bodyRows+"</tbody></table></div>"+(pageMax>1?"<div class=\"v313-model-pagination\" role=\"navigation\" aria-label=\"Páginas de modelos\"><button type=\"button\" data-v313-page=\"prev\" "+(page===0?"disabled":"")+">← Anteriores</button><span>Mostrando "+(page*pageSize+1)+"–"+Math.min((page+1)*pageSize,rows.length)+" de "+rows.length+" · Página "+(page+1)+" de "+pageMax+"</span><button type=\"button\" data-v313-page=\"next\" "+(page>=pageMax-1?"disabled":"")+">Siguientes →</button></div>":"")+(!rows.length?"<div class=\"v313-empty\"><b>"+emptyTitle+"</b><p>"+emptyText+"</p></div>":"")+"</section>"
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


function initialUpload(d){
if(!d.can_admin)return"<div class=\"v313-empty\"><b>Acceso restringido</b><p>La carga de cortes iniciales está disponible sólo para Administrador y Superadministrador.</p></div>";
var month=String(S.month||d.month||"");
var opts=(d.months||[]).map(function(x){return"<option value=\""+esc(x.value)+"\" "+(x.value===month?"selected":"")+">"+esc(x.label)+"</option>"}).join("");
return"<div class=\"v313-hero\"><div><b>Corte inicial mensual</b><br><span>Asigna un Excel de Capacidades al mes seleccionado. El archivo se conserva en el histórico y no reemplaza los cortes actuales.</span></div><span class=\"tag\">"+esc(month)+"</span></div>"+
"<section class=\"v313-panel\"><div class=\"v313-ph\"><span>Cargar corte inicial</span><span>Capacidades · Excel</span></div><div class=\"v313-body\">"+
"<div class=\"v313-note\">El corte inicial define el punto de partida para los Bonos 2–6. Elige el mes, selecciona el Excel más cercano al inicio de ese mes y guarda. Cada mes tiene su propia asignación; no se usará una base antigua de otro periodo automáticamente.</div>"+
"<div class=\"v313-upload-grid\" style=\"margin-top:12px\"><div><label for=\"v321InitialMonth\">Mes del bono</label><select id=\"v321InitialMonth\">"+opts+"</select></div><div><label for=\"v321InitialFile\">Archivo de Capacidades inicial (.xlsx / .xls)</label><input id=\"v321InitialFile\" type=\"file\" accept=\".xlsx,.xls,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\"></div><div><button type=\"button\" class=\"v321-upload-button\" id=\"v321UploadButton\">Procesar y guardar</button></div></div>"+
"<div id=\"v321UploadStatus\" class=\"v321-state "+esc((S.initialStatus||{}).kind||"")+"\" role=\"status\">"+esc((S.initialStatus||{}).text||"Selecciona el mes y el archivo inicial que deseas asociar.")+"</div>"+
"<div id=\"v321InitialHistory\"><div class=\"v313-empty\">Consultando los cortes iniciales guardados…</div></div></div></section>"+
"<section class=\"v313-panel\" style=\"margin-top:8px\"><div class=\"v313-ph\"><span>Reglas de resguardo</span><span>Histórico por mes</span></div><div class=\"v313-body\"><div class=\"v313-note\">• El corte inicial queda asociado sólo al mes seleccionado.<br>• Cargar un nuevo archivo para el mismo mes reemplaza su asignación, pero no borra el archivo anterior del histórico general.<br>• La carga no modifica la fórmula del Bono 1 ni los criterios de los Bonos 2–6.<br>• Para comparar resultados, también debe existir un corte actual procesado.</div></div></section>";
}
function loadInitialHistory(){
var host=q("#v321InitialHistory");if(!host)return;
var month=String(S.month||(S.data&&S.data.month)||"");
api("/api/bonuses/initial-capacity?month="+encodeURIComponent(month)).then(function(payload){
if(!q("#v321InitialHistory"))return;
var selected=payload.selected;
var current=selected?"<div class=\"v313-note\"><b>Asignación para "+esc(month)+":</b> "+esc(selected.name)+" · fecha de reporte "+esc(dateMx(selected.report_date))+" · "+esc(selected.status)+" · "+nf(selected.rows)+" filas · "+nf(selected.stores_count)+" tiendas</div>":"<div class=\"v313-empty\"><b>No hay corte inicial asignado para "+esc(month)+"</b><p>Selecciona el archivo que corresponda al inicio de este periodo. No se tomará como inicial un archivo antiguo de otro mes.</p></div>";
var rows=(payload.items||[]).map(function(x){return"<tr><td><b>"+esc(x.month)+"</b></td><td>"+esc(x.name)+"</td><td>"+esc(dateMx(x.report_date))+"</td><td>"+esc(x.status)+"</td><td>"+nf(x.rows)+"</td><td>"+nf(x.stores_count)+"</td></tr>"}).join("");
var history=rows?"<div class=\"v321-history-wrap\"><table class=\"v321-history\"><thead><tr><th>Mes</th><th>Archivo inicial</th><th>Fecha del corte</th><th>Estado</th><th>Filas</th><th>Tiendas</th></tr></thead><tbody>"+rows+"</tbody></table></div>":"<div class=\"v313-empty\">Aún no hay cortes iniciales asignados a ningún mes.</div>";
host.innerHTML=current+"<h3 style=\"margin:14px 0 5px;font-size:12px\">Histórico de cortes iniciales por mes</h3>"+history;
}).catch(function(err){if(q("#v321InitialHistory"))q("#v321InitialHistory").innerHTML="<div class=\"v321-state err\">No se pudo consultar el histórico: "+esc(err.message||err)+"</div>"});
}
function pollInitialCutJob(jobId,startedAt,status){
 return api("/api/upload/jobs/"+encodeURIComponent(jobId)).then(function(job){
  if(job.module!=="bonus_initial_capacity")throw new Error("El servidor devolvió un folio de carga no válido.");
  if(job.status==="complete")return job.result||{};
  if(job.status==="error")throw new Error(job.error||job.message||"No se pudo procesar el corte inicial.");
  var progress=Math.max(0,Math.min(99,Number(job.progress)||10));
  var message=(job.message||"Procesando el corte inicial.")+" ("+progress+"%)";
  S.initialStatus={kind:"",text:message};
  if(status){status.className="v321-state";status.textContent=message}
  if(Date.now()-startedAt>15*60*1000){
   throw new Error("La carga aún no confirmó su resultado. No vuelvas a subir el archivo todavía; revisa el histórico en unos minutos. Folio: "+jobId);
  }
  return new Promise(function(resolve){setTimeout(resolve,1800)}).then(function(){return pollInitialCutJob(jobId,startedAt,status)});
 });
}
function uploadInitialCut(){
var file=q("#v321InitialFile")&&q("#v321InitialFile").files[0];
var month=q("#v321InitialMonth")?q("#v321InitialMonth").value:String(S.month||"");
var status=q("#v321UploadStatus"),button=q("#v321UploadButton");
if(!file){if(status){status.className="v321-state err";status.textContent="Primero selecciona un Excel de Capacidades."}return}
if(!/\.xlsx?$/.test(file.name.toLowerCase())){if(status){status.className="v321-state err";status.textContent="El archivo debe ser .xlsx o .xls."}return}
var form=new FormData();form.append("month",month);form.append("file",file);
if(button){button.disabled=true;button.textContent="Procesando…"}
if(status){status.className="v321-state";status.textContent="Procesando el Excel y asignándolo al periodo seleccionado…"}
fetch("/api/bonuses/initial-capacity",{method:"POST",credentials:"same-origin",body:form}).then(function(response){return response.text().then(function(raw){var data={};try{data=JSON.parse(raw)}catch(_e){data={detail:raw}}if(!response.ok)throw new Error(data.detail||data.message||("HTTP "+response.status));if(data.job_id)return pollInitialCutJob(data.job_id,Date.now(),status);return data})}).then(function(data){
S.initialStatus={kind:"ok",text:data.message+" Archivo: "+data.file+" · Fecha: "+dateMx(data.report_date)+" · Filas: "+nf(data.rows)+" · Tiendas: "+nf(data.stores)};
if(status){status.className="v321-state ok";status.textContent=S.initialStatus.text}
S.month=month;S.refreshCount=0;
var period=q("#v313Month");if(period)period.value=month;
load();
}).catch(function(err){S.initialStatus={kind:"err",text:"No se pudo guardar el corte inicial: "+(err.message||err)};if(status){status.className="v321-state err";status.textContent=S.initialStatus.text}}).finally(function(){if(button){button.disabled=false;button.textContent="Procesar y guardar"}});
}
function body(d){
if(S.section==="initial-upload")return initialUpload(d);
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


function page(d){return"<div class=\"v313\"><div class=\"v313-head\"><div><h2>Bonos</h2><div class=\"v313-sub\">"+(d.is_v330?"Seguimiento automático con fuentes reales · sin simulaciones ni importes de pago":d.b2_cohort?"Bono 2 · corte inicial · 0 ventas en 30 días · excluir llegadas de los últimos 7 días · catálogo vigente":"Comparación real entre corte inicial y corte actual · sin gráficas de línea")+"</div></div><div class=\"v313-head-right\">"+filters(d)+"<button type=\"button\" id=\"v313UpdateBtn\" title=\"Consultar la última versión y actualizar\">↻ Actualizar</button></div></div>"+bonusTabs(d)+(S.section==="initial-upload"?"":tabs())+body(d)+"</div>"}
function bind(){
q("#v313UpdateBtn")?.addEventListener("click",async function(){
  var btn=this;btn.disabled=true;btn.textContent="Buscando versión…";
  try{
    if(window.OperacionesPWA&&window.OperacionesPWA.checkForUpdates){
      var versionResult=await window.OperacionesPWA.checkForUpdates({manual:true});
       if(versionResult&&versionResult.available&&window.OperacionesPWA.applyUpdate)await window.OperacionesPWA.applyUpdate();
    }else{
      var response=await fetch("/api/app-version?t="+Date.now(),{cache:"no-store",credentials:"same-origin"});
      if(!response.ok)throw new Error("Servicio de actualización no disponible");
      alert("Versión consultada. Si hay una actualización, abre el aviso superior.");
    }
  }catch(e){
    alert("No fue posible consultar las actualizaciones. Revisa la conexión e inténtalo de nuevo.");
  }finally{btn.disabled=false;btn.textContent="↻ Actualizar"}
});
function showExportNotice(message,isError){
  var el=q("#v313ExportNotice");if(!el)return;
  el.hidden=false;el.classList.toggle("error",!!isError);el.textContent=message;
}
function detailRows(){var a=((S.data||{}).details||[]);return S.section==="details"?a:a.filter(function(r){return r.catalog===S.catalog})}
qa("[data-v313-download]").forEach(function(b){b.addEventListener("click",async function(){
  var rows=detailRows(),fmt=b.dataset.v313Download,all= S.section==="details";
  if(!rows.length){showExportNotice("Sin modelos disponibles para descargar en este catálogo. Comprueba Tipo catálogo VIGENTE y los criterios del corte inicial.",true);return}
  var p=new URLSearchParams({month:S.month,store:S.store,bonus:String(S.bonus),catalog:all?"Todos":S.catalog,format:fmt});
  var buttons=qa("[data-v313-download]");buttons.forEach(function(x){x.disabled=true});
  showExportNotice("Preparando "+(fmt==="xlsx"?"Excel":"PDF")+" con "+rows.length+" modelos. Permanece en este listado mientras se genera el archivo…",false);
  try{
    var response=await fetch("/api/bonuses/models-export?"+p.toString(),{credentials:"same-origin",cache:"no-store"});
    if(!response.ok){
      var errorText=await response.text(),detail="";try{var parsed=JSON.parse(errorText);detail=String(parsed.detail||parsed.message||"")}catch(_e){detail=errorText.slice(0,200)}
      throw new Error(detail||"Error HTTP "+response.status);
    }
    var blob=await response.blob();
    if(!blob.size)throw new Error("El archivo de exportación llegó vacío");
    var disposition=response.headers.get("Content-Disposition")||"";
    var match=/filename="?([^";]+)"?/i.exec(disposition);
    var filename=match&&match[1]?match[1]:("Bonos_"+S.store+"_"+(all?"Todos":S.catalog)+"_"+S.month+"."+(fmt==="xlsx"?"xlsx":"pdf"));
    var url=URL.createObjectURL(blob),link=document.createElement("a");
    link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
    setTimeout(function(){URL.revokeObjectURL(url)},60000);
    var count=Number(response.headers.get("X-Photos-Included")||0),total=Number(response.headers.get("X-Photos-Requested")||0);
    var report=total?" Fotografías: "+count+" de "+total+".":" Fotografías no solicitadas.";
    showExportNotice("Descarga preparada: "+filename+"."+report+" El listado permanece abierto.",total>0&&count<total);
  }catch(e){showExportNotice("No se pudo descargar: "+(e.message||e)+". No se perdió tu consulta.",true)}
  finally{buttons.forEach(function(x){x.disabled=detailRows().length===0})}
})});
q("[data-v313-return]")?.addEventListener("click",function(){S.section="summary";render()});
qa("[data-v313-page]").forEach(function(b){b.addEventListener("click",function(){
 var list=detailRows(),key=[S.month,S.store,S.bonus,S.section,S.catalog].join("|");
 var total=Math.max(1,Math.ceil(list.length/30)),current=S.modelPage[key]||0;
 S.modelPage[key]=Math.max(0,Math.min(total-1,current+(b.dataset.v313Page==="next"?1:-1)));
 S.modelScroll[key]=0;render();
})});
function moveModelViewport(direction){
 var sc=q(".v313-model-scroll");if(!sc)return;
 var list=detailRows(),key=[S.month,S.store,S.bonus,S.section,S.catalog].join("|");
 var current=S.modelPage[key]||0,pages=Math.max(1,Math.ceil(list.length/30));
 var measurable=sc.scrollHeight>sc.clientHeight;
 var atEdge=measurable&&(direction>0?sc.scrollTop+sc.clientHeight>=sc.scrollHeight-12:sc.scrollTop<=2);
 if(atEdge&&((direction>0&&current<pages-1)||(direction<0&&current>0))){
  S.modelPage[key]=current+direction;S.modelScroll[key]=0;render();return;
 }
 sc.scrollBy({top:direction*1290,behavior:"smooth"});
}
q("[data-v313-scroll-up]")?.addEventListener("click",function(){moveModelViewport(-1)});
q("[data-v313-scroll-down]")?.addEventListener("click",function(){moveModelViewport(1)});
var scroller=q(".v313-model-scroll");if(scroller){
 var scrollKey=[S.month,S.store,S.bonus,S.section,S.catalog].join("|");
 scroller.scrollTop=S.modelScroll[scrollKey]||0;
 scroller.addEventListener("scroll",function(){S.modelScroll[scrollKey]=scroller.scrollTop},{passive:true});
  scroller.addEventListener("wheel",function(e){
    if(scroller.scrollHeight<=scroller.clientHeight&&scroller.scrollWidth<=scroller.clientWidth)return;
    if(e.cancelable)e.preventDefault();
    scroller.scrollTop+=e.deltaY;scroller.scrollLeft+=e.deltaX;
  },{passive:false,capture:true});
  var startY=0,startX=0;
  scroller.addEventListener("touchstart",function(e){
    if(e.touches.length===1){startY=e.touches[0].clientY;startX=e.touches[0].clientX}
  },{passive:true});
  scroller.addEventListener("touchmove",function(e){
    if(e.touches.length!==1)return;
    var y=e.touches[0].clientY,x=e.touches[0].clientX;
    if(scroller.scrollHeight>scroller.clientHeight||scroller.scrollWidth>scroller.clientWidth){
      if(e.cancelable)e.preventDefault();
      scroller.scrollTop+=(startY-y);scroller.scrollLeft+=(startX-x);
    }
    startY=y;startX=x;
  },{passive:false,capture:true});
}
qa(".v313-photo").forEach(function(im){im.addEventListener("click",function(){var bg=document.createElement("div");bg.className="v313-photo-overlay";var large=document.createElement("img");large.src=im.src;large.alt=im.alt;var close=document.createElement("button");close.type="button";close.textContent="← Regresar al listado";function done(){bg.remove();document.removeEventListener("keydown",escape)}function escape(e){if(e.key==="Escape")done()}close.onclick=done;bg.onclick=function(e){if(e.target===bg)done()};bg.append(close,large);document.body.append(bg);document.addEventListener("keydown",escape)})});
q("#v313Month")?.addEventListener("change",function(e){S.month=e.target.value;S.refreshCount=0;load()});
q("#v313Store")?.addEventListener("change",function(e){S.store=e.target.value;S.refreshCount=0;load()});
qa("[data-v313-bonus]").forEach(function(b){b.addEventListener("click",function(){
 var next=Number(b.dataset.v313Bonus);if(S.bonus===next&&S.section==="summary")return;
 S.bonus=next;S.section="summary";S.catalog="Abrigador";S.refreshCount=0;load();
})});
q("[data-v313-initial]")?.addEventListener("click",function(){S.section="initial-upload";render()});
q("#v321InitialMonth")?.addEventListener("change",function(e){S.month=e.target.value;S.initialStatus=null;var p=q("#v313Month");if(p)p.value=S.month;S.refreshCount=0;load()});
q("#v321UploadButton")?.addEventListener("click",uploadInitialCut);
qa("[data-v313-section]").forEach(function(b){b.addEventListener("click",function(){
 S.section=b.dataset.v313Section;
 if(S.section==="catalogLic")S.catalog="Licencias";if(S.section==="catalogBas")S.catalog="Básicos";
 if(S.bonus>=3&&S.section==="models"&&(!S.data||!S.data.details||!S.data.details.length)){load();return}
 render()
})});
qa("[data-v313-store]").forEach(function(r){r.addEventListener("click",function(){S.store=r.dataset.v313Store;S.section="panorama";S.refreshCount=0;load()})});
qa("[data-v313-cat]").forEach(function(b){b.addEventListener("click",function(){S.catalog=b.dataset.v313Cat;render()})})
}


function render(){activate();var h=q("#v313Host");if(h&&S.data){h.innerHTML=page(S.data);bind();if(S.section==="initial-upload")loadInitialHistory()}}
var v330Display={3:["Puntos ponderados","3.2",50,30],4:["Objetivos independientes","4.1",50,30],5:["Multiplicador por DDI","5.2",80,null],6:["Resultado colectivo por tienda","6.1",48,32]};
function displayKey(){return [S.bonus,S.month,S.store,S.section==="models"?"details":"brief"].join("|")}
function load(){
 if(S.refreshTimer){clearTimeout(S.refreshTimer);S.refreshTimer=null}
 if(S.controller){try{S.controller.abort()}catch(_){}S.controller=null}
 var seq=++S.seq,key=displayKey(),cached=S.cache.get(key),old=S.data;
 if(cached&&Date.now()-cached.at<20000){
  S.data=cached.data;render();
 }else if(S.bonus>=3&&old&&old.is_v330&&old.month===S.month&&old.selected_store===S.store&&S.section!=="models"){
  var next=v330Display[S.bonus];
  S.data=Object.assign({},old,{bonus_no:S.bonus,
   model:Object.assign({},old.model,{name:next[0],design:next[1],
    weights:{sales:next[2],ddi:next[3],attendance:20}}),
   ranking:[]});
  render();
 }else{
  S.data=null;activate();
  var h=q("#v313Host");
  if(h)h.innerHTML='<div class="v313"><div class="v313-head"><h2>Bonos · Bono '+S.bonus+'</h2></div><div class="v313-bonus">'+[1,2,3,4,5,6].map(function(i){return'<button data-v313-bonus="'+i+'" class="'+(i===S.bonus?'active':'')+'">Bono '+i+'</button>'}).join('')+'</div><div class="v313-note" role="status">Consultando indicadores reales del Bono '+S.bonus+'…</div></div>';
  qa("[data-v313-bonus]").forEach(function(b){b.addEventListener("click",function(){S.bonus=Number(b.dataset.v313Bonus);S.section="summary";load()})});
 }
 var controller=typeof AbortController!=="undefined"?new AbortController():null;S.controller=controller;
 var p=new URLSearchParams({bonus:String(S.bonus),store:S.store});
 if(S.month)p.set("month",S.month);
 if(S.bonus>=3&&S.section==="models")p.set("include_details","true");
 var url=(S.bonus===2?"/api/bonuses-b2-v327?":S.bonus>=3?"/api/bonuses-v330?":"/api/bonuses-v313?")+p.toString();
 api(url,controller?{signal:controller.signal}:{}).then(function(d){
  if(seq!==S.seq)return;
  S.data=d;S.month=d.month;S.store=d.selected_store;S.controller=null;
  S.cache.set(displayKey(),{data:d,at:Date.now()});
  if(S.cache.size>16)S.cache.delete(S.cache.keys().next().value);
  render();
  var processing=d.processing||{};
  var capacityRetries=!!processing.capacity&&S.refreshCount<60;
  var otherRetries=!!(processing.sales||d.weekly_pending)&&S.refreshCount<10;
  if(capacityRetries||otherRetries){
   S.refreshCount++;
   S.refreshTimer=setTimeout(function(){if(seq===S.seq)load()},capacityRetries?3000:1800);
  }else{S.refreshCount=0}
 }).catch(function(e){
  if(seq!==S.seq||e&&e.name==="AbortError")return;
  S.controller=null;
  var h=q("#v313Host");if(!h)return;
  var safe=esc(e.message||e);
  if(S.data){
   var box=q("#v313ErrorRetry");
   if(!box){box=document.createElement("div");box.id="v313ErrorRetry";box.className="v313-note";h.prepend(box)}
   box.innerHTML="No se pudieron actualizar los datos: "+safe+' <button type="button" id="v313Retry">Reintentar</button>';
  }else h.innerHTML='<div class="v313-note">No fue posible cargar Bono '+S.bonus+': '+safe+' <button type="button" id="v313Retry">Reintentar</button></div>';
  q("#v313Retry")?.addEventListener("click",function(){load()});
 })
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
            headers["X-Operations-Bonus-Version"]="V318-BONUS-CUTS-AND-DESIGN"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V313] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V313_BONUS_VISUAL_CUTS=True
    print("[V318] Bonos: corte inicial por cercanía, ID único por archivo, tabs aprobadas y estados de detalle.",flush=True)
