"""V149 · Restaura Resumen como primera pestaña de Operación.

Se instala al final de la cadena para que no lo oculten los parches posteriores.
Resumen: Llegada Origen, productividad, mercancía liberada, pendiente,
eficiencia, productividad promedio, cumplimiento, colaboradores; además
Origen vs Cambios y Muertos, desempeño por tienda, Top 5 y alertas.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import math
import re

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V149_OPERATION_SUMMARY_RESTORE", False):
        return

    def n(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def bounds(kind, value):
        kind = str(kind or "day").lower(); value = str(value or "").strip(); today = datetime.now(MX).date()
        if kind == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date(); return d, d
        if kind == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt: y, w = int(mt.group(1)), int(mt.group(2))
            else: iso = today.isocalendar(); y, w = iso.year, iso.week
            d = date.fromisocalendar(y, w, 1); return d, d + timedelta(days=6)
        if kind == "month":
            if value:
                y, mo = [int(x) for x in value.split("-")[:2]]
            else: y, mo = today.year, today.month
            d = date(y, mo, 1); nxt = date(y + (mo == 12), 1 if mo == 12 else mo + 1, 1); return d, nxt - timedelta(days=1)
        if kind == "year":
            y = int(value or today.year); return date(y, 1, 1), date(y, 12, 31)
        raise HTTPException(400, "Vista inválida")

    def scoped_stores(actor, requested):
        role = str(actor.get("role") or ""); assigned = str(actor.get("store") or "").strip()
        if role in ("tienda", "colaborador"):
            if not assigned: raise HTTPException(409, "El usuario no tiene tienda asignada")
            return [assigned], assigned
        selected = str(requested or "Compañía").strip() or "Compañía"
        if selected != "Compañía": return [selected], selected
        try: return list(m.store_names(True)), "Compañía"
        except Exception: return list(getattr(m, "PROJECT_STORES", [])), "Compañía"

    def standards():
        out = {"Colgado": 1228.0, "Doblado": 906.0, "Cambios y Muertos": 670.0}
        try:
            with m.db() as con:
                for r in con.execute("SELECT origin,pieces_per_shift FROM operation_standards").fetchall():
                    out[str(r["origin"])] = n(r["pieces_per_shift"])
        except Exception: pass
        return out

    @m.app.get("/api/operation/summary-v149")
    def summary_v149(request: Request, period_type: str="day", period_value: str="", store: str="Compañía"):
        actor = m.require_user(request); start, end = bounds(period_type, period_value); stores, selected = scoped_stores(actor, store)
        if not stores:
            return {"summary":{},"comparison":[],"stores":[],"top":[],"alerts":[]}
        ss, es = start.isoformat(), end.isoformat(); ph = ",".join("?" for _ in stores); stset = set(stores); std = standards()
        with m.db() as con:
            caps = [dict(r) for r in con.execute(f"SELECT date,store,arrival,released FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ({ph})", (es,*stores)).fetchall()]
            prod = [dict(r) for r in con.execute(f"SELECT date,store,user_id,employee_no,employee_name,origin,pieces FROM operation_productivity WHERE origin IN ('Colgado','Doblado') AND date<=? AND store IN ({ph})", (es,*stores)).fetchall()]
        cm=[]
        try:
            for r in (m.load_ops() or {}).get("rows",[]):
                ds=str(r.get("date") or "")[:10]; st=str(r.get("store") or "").strip()
                if not ds or st not in stset: continue
                try: d=date.fromisoformat(ds)
                except Exception: continue
                if d>end: continue
                cm.append({"date":ds,"store":st,"arrival":n(r.get("recolectadas")),"processed":n(r.get("acondicionado")),"released":n(r.get("ubicado")),"pieces":n(r.get("pieces")),"name":str(r.get("name") or "").strip()})
        except Exception as exc:
            print(f"[V149] C&M: {type(exc).__name__}: {exc}", flush=True)

        prev_o_arr=sum(n(r["arrival"]) for r in caps if str(r["date"])<ss); prev_o_proc=sum(n(r["pieces"]) for r in prod if str(r["date"])<ss)
        prev_c_arr=sum(n(r["arrival"]) for r in cm if r["date"]<ss); prev_c_proc=sum(n(r["processed"]) for r in cm if r["date"]<ss)
        po=max(prev_o_arr-prev_o_proc,0); pc=max(prev_c_arr-prev_c_proc,0)
        cp=[r for r in caps if ss<=str(r["date"])<=es]; pp=[r for r in prod if ss<=str(r["date"])<=es]; cc=[r for r in cm if ss<=r["date"]<=es]
        oa=sum(n(r["arrival"]) for r in cp); op=sum(n(r["pieces"]) for r in pp); orl=sum(n(r["released"]) for r in cp); of=max(po+oa-op,0)
        ca=sum(n(r["arrival"]) for r in cc); cpr=sum(n(r["processed"]) for r in cc); cr=sum(n(r["released"]) for r in cc); cf=max(pc+ca-cpr,0)
        total_arr=oa+ca; total_proc=op+cpr; total_rel=orl+cr; total_pending=of+cf; workload=po+pc+total_arr

        # Productividad por colaborador.
        people={}; seen_target=set()
        for r in pp:
            name=str(r.get("employee_name") or "Sin nombre").strip(); eno=str(r.get("employee_no") or "").strip(); st=str(r["store"]); org=str(r.get("origin") or "")
            key=(eno or name.casefold(),st); g=people.setdefault(key,{"name":name,"store":st,"pieces":0.0,"days":set(),"target":0.0}); g["pieces"]+=n(r["pieces"]); g["days"].add(str(r["date"]))
            tk=(key,str(r["date"]),org)
            if tk not in seen_target: seen_target.add(tk); g["target"]+=n(std.get(org))
        for r in cc:
            name=str(r.get("name") or "").strip(); pcs=n(r.get("pieces"))
            if not name or pcs<=0: continue
            st=str(r["store"]); key=(name.casefold(),st); g=people.setdefault(key,{"name":name,"store":st,"pieces":0.0,"days":set(),"target":0.0}); g["pieces"]+=pcs; g["days"].add(r["date"])
            tk=(key,r["date"],"Cambios y Muertos")
            if tk not in seen_target: seen_target.add(tk); g["target"]+=n(std.get("Cambios y Muertos"))
        top=[]
        for g in people.values():
            d=max(len(g["days"]),1); comp=g["pieces"]/g["target"]*100 if g["target"] else 0
            top.append({"name":g["name"],"store":g["store"],"pieces":g["pieces"],"daily":g["pieces"]/d,"compliance_pct":comp})
        top.sort(key=lambda x:(-x["compliance_pct"],-x["pieces"],x["name"]))
        empdays=sum(max(len(g["days"]),1) for g in people.values()); avg=sum(g["pieces"] for g in people.values())/empdays if empdays else 0

        # Meta global y tienda.
        manual_keys={(str(r["date"]),str(r["store"]),str(r.get("origin") or "")) for r in pp}; target=sum(n(std.get(org)) for _,_,org in manual_keys)
        cm_keys={(r["date"],r["store"]) for r in cc if n(r["arrival"]) or n(r["processed"])}; target+=len(cm_keys)*n(std.get("Cambios y Muertos"))
        compliance=total_proc/target*100 if target else 0; efficiency=total_proc/workload*100 if workload else 0
        by=[]
        for st in stores:
            a=sum(n(r["arrival"]) for r in cp if r["store"]==st)+sum(n(r["arrival"]) for r in cc if r["store"]==st)
            p=sum(n(r["pieces"]) for r in pp if r["store"]==st)+sum(n(r["processed"]) for r in cc if r["store"]==st)
            rel=sum(n(r["released"]) for r in cp if r["store"]==st)+sum(n(r["released"]) for r in cc if r["store"]==st)
            mk={(str(r["date"]),str(r.get("origin") or "")) for r in pp if r["store"]==st}; tg=sum(n(std.get(org)) for _,org in mk)
            ck={r["date"] for r in cc if r["store"]==st and (n(r["arrival"]) or n(r["processed"]))}; tg+=len(ck)*n(std.get("Cambios y Muertos")); comp=p/tg*100 if tg else 0
            if a or p or rel or tg: by.append({"store":st,"arrival":a,"processed":p,"released":rel,"target":tg,"compliance_pct":comp})
        by.sort(key=lambda x:(-x["compliance_pct"],-x["processed"],x["store"]))
        alerts=[]
        if total_pending>0: alerts.append({"level":"warn","text":f"Pendiente operativo: {total_pending:,.0f} piezas por procesar."})
        if workload and efficiency<75: alerts.append({"level":"bad","text":f"Eficiencia operativa baja: {efficiency:.1f}%."})
        lows=[x for x in by if x["target"] and x["compliance_pct"]<75]
        if lows: alerts.append({"level":"bad","text":"Tiendas bajo 75% de cumplimiento: "+", ".join(x["store"] for x in lows[:5])+"."})
        if not alerts: alerts=[{"level":"ok","text":"Sin alertas críticas para el periodo consultado."}]
        return {"start_date":ss,"end_date":es,"store":selected,"summary":{"arrival_origin":oa,"processed":total_proc,"released":total_rel,"pending":total_pending,"efficiency_pct":efficiency,"productivity_avg":avg,"compliance_pct":compliance,"collaborators":len(people)},"comparison":[{"name":"Origen","arrival":oa,"processed":op,"released":orl,"pending":of},{"name":"Cambios y Muertos","arrival":ca,"processed":cpr,"released":cr,"pending":cf}],"stores":by,"top":top[:5],"alerts":alerts}

    css=r'''<style id="v149-operation-summary-css">
.v149-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.v149-kpi{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;position:relative;overflow:hidden}.v149-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--k,#246fe5)}.v149-kpi small{display:block;color:#667085;font-size:7px;font-weight:950;text-transform:uppercase}.v149-kpi b{display:block;color:var(--navy);font-size:22px;margin:6px 0 2px}.v149-kpi span{font-size:8px;color:#667085}.v149-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v149-panel{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;margin:9px 0}.v149-panel h3{font-size:12px;color:var(--navy);margin:0 0 9px}.v149-alert{padding:9px 10px;border-radius:9px;margin:6px 0;font-size:9px;font-weight:800}.v149-alert.ok{background:#ecfdf3;color:#166534}.v149-alert.warn{background:#fff8db;color:#8a5c00}.v149-alert.bad{background:#feecec;color:#a31515}@media(max-width:900px){.v149-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v149-grid{grid-template-columns:1fr}.v149-kpi b{font-size:20px}}</style>'''
    js=r'''<script id="v149-operation-summary-js">
(function(){
const OP='Operación',num=v=>Number(v||0),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])),fn=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:0}),f1=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1});
window.V149_OPERATION_TAB=window.V149_OPERATION_TAB||'summary';
function today(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()),g=t=>p.find(x=>x.type===t)?.value||'';return `${g('year')}-${g('month')}-${g('day')}`}
function week(ds){const d=new Date(ds+'T12:00:00'),t=new Date(d),n=(d.getDay()+6)%7;t.setDate(t.getDate()-n+3);const f=new Date(t.getFullYear(),0,4),w=1+Math.round(((t-f)/86400000-3+(f.getDay()+6)%7)/7);return `${t.getFullYear()}-W${String(w).padStart(2,'0')}`}
function vals(meta,type){return type==='day'?(meta.dates||[]):type==='week'?(meta.weeks||[]):type==='month'?(meta.months||[]):meta.years||[]}
function def(meta,type){const d=today(),a=vals(meta,type);if(type==='day')return d;if(a.length)return a[a.length-1];if(type==='week')return week(d);if(type==='month')return d.slice(0,7);return d.slice(0,4)}
function setSel(el,a,v){if(!el)return;el.innerHTML='';a.forEach(x=>el.add(new Option(x,x)));el.value=a.includes(v)?v:(a[a.length-1]||'')}
function tabs(active='summary'){return `<div class="v125-tabs" role="tablist"><button class="v125-tab ${active==='summary'?'active':''}" data-v149-tab="summary">Resumen</button><button class="v125-tab ${active==='daily'?'active':''}" data-v149-tab="daily">Captura diaria</button><button class="v125-tab ${active==='capture'?'active':''}" data-v149-tab="capture">Cargar productividad</button><button class="v125-tab ${active==='productivity'?'active':''}" data-v149-tab="productivity">Productividad</button><button class="v125-tab ${active==='standards'?'active':''}" data-v149-tab="standards">Estándares</button></div>`}
async function setup(meta){$('#operativoPeriodBar')?.classList.remove('hidden');$('#operPeriodModeWrap')?.classList.remove('hidden');$('#operAreaSelect')?.closest('.filter')?.classList.add('hidden');$('#operActivitySelect')?.closest('.filter')?.classList.add('hidden');if(!['day','week','month','year'].includes(OPER_PERIOD.type))OPER_PERIOD.type='day';const mode=$('#operPeriodMode');if(mode){mode.innerHTML='<option value="day">Día</option><option value="week">Semanal</option><option value="month">Mensual</option><option value="year">Anual</option>';mode.value=OPER_PERIOD.type}let a=vals(meta,OPER_PERIOD.type);if(OPER_PERIOD.type==='day')a=[...new Set([...(a||[]),today()])].sort();if(!OPER_PERIOD.value||!a.includes(OPER_PERIOD.value))OPER_PERIOD.value=def(meta,OPER_PERIOD.type);setSel($('#operPeriodSelect'),a.length?a:[OPER_PERIOD.value],OPER_PERIOD.value);$('#operPeriodModeLabel').textContent='Vista';$('#operPeriodLabel').textContent=OPER_PERIOD.type==='day'?'Fecha':OPER_PERIOD.type==='week'?'Semana ISO':OPER_PERIOD.type==='month'?'Mes':'Año';const s=$('#operStoreSelect');if(s){const old=s.value,restricted=USER?.role==='tienda'||USER?.role==='colaborador';s.innerHTML='';if(!restricted)s.add(new Option('Compañía','Compañía'));(meta.stores||[]).forEach(x=>s.add(new Option(x,x)));if(restricted){s.value=USER.store||meta.stores?.[0]||'';s.disabled=true}else{s.disabled=false;s.value=[...s.options].some(o=>o.value===old)?old:'Compañía'}s.closest('.filter')?.classList.remove('hidden');s.parentElement.querySelector('label').textContent='Tienda'}}
function cards(s){const d=[['Llegada Origen',s.arrival_origin,'Colgado + Doblado','#246fe5'],['Productividad registrada',s.processed,'Piezas procesadas','#7338ef'],['Mercancía liberada',s.released,'Origen + C&M','#ec007c'],['Pendiente',s.pending,'Piezas por procesar','#ef3434'],['Eficiencia',f1(s.efficiency_pct)+'%','Procesadas / carga','#10b981'],['Prod. promedio',f1(s.productivity_avg),'Pzas / colaborador / día','#f3a300'],['Cumplimiento',f1(s.compliance_pct)+'%','Vs estándar','#10b981'],['Colaboradores',s.collaborators,'Con productividad','#173f78']];return `<div class="v149-kpis">${d.map(x=>`<div class="v149-kpi" style="--k:${x[3]}"><small>${x[0]}</small><b>${typeof x[1]==='string'?x[1]:fn(x[1])}</b><span>${x[2]}</span></div>`).join('')}</div>`}
function comp(rows){return `<div class="v149-panel"><h3>Origen vs Cambios y Muertos</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tipo</th><th>Llegada</th><th>Procesadas</th><th>Liberadas</th><th>Pendiente</th></tr></thead><tbody>${rows.map(r=>`<tr><td><b>${esc(r.name)}</b></td><td>${fn(r.arrival)}</td><td>${fn(r.processed)}</td><td>${fn(r.released)}</td><td>${fn(r.pending)}</td></tr>`).join('')}</tbody></table></div></div>`}
function storeTable(rows){return `<div class="v149-panel"><h3>Desempeño por tienda</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Llegada</th><th>Procesadas</th><th>Liberadas</th><th>Meta</th><th>Cumplimiento</th></tr></thead><tbody>${rows.length?rows.map(r=>`<tr><td><b>${esc(r.store)}</b></td><td>${fn(r.arrival)}</td><td>${fn(r.processed)}</td><td>${fn(r.released)}</td><td>${fn(r.target)}</td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${f1(r.compliance_pct)}%</b></td></tr>`).join(''):'<tr><td colspan="6">Sin información para el periodo.</td></tr>'}</tbody></table></div></div>`}
function top(rows){return `<div class="v149-panel"><h3>Top 5 colaboradores</h3><div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Colaborador</th><th>Tienda</th><th>Piezas</th><th>Prod. diaria</th><th>Cumplimiento</th></tr></thead><tbody>${rows.length?rows.map((r,i)=>`<tr><td>#${i+1}</td><td><b>${esc(r.name)}</b></td><td>${esc(r.store)}</td><td>${fn(r.pieces)}</td><td>${fn(r.daily)}</td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${f1(r.compliance_pct)}%</b></td></tr>`).join(''):'<tr><td colspan="6">Sin productividad registrada.</td></tr>'}</tbody></table></div></div>`}
function alerts(rows){return `<div class="v149-panel"><h3>Alertas operativas</h3>${rows.map(a=>`<div class="v149-alert ${a.level||'warn'}">${esc(a.text)}</div>`).join('')}</div>`}
function bindTabs(){document.querySelectorAll('[data-v149-tab]').forEach(b=>b.onclick=async()=>{V149_OPERATION_TAB=b.dataset.v149Tab;if(V149_OPERATION_TAB==='summary'){await renderOperativoView(OP,true);return}V125_OPERATION_TAB=V149_OPERATION_TAB;OPER_PERIOD.value='';if(V149_OPERATION_TAB!=='productivity')OPER_PERIOD.type='day';await renderOperativoView(OP,true)})}
async function renderSummary(){const c=$('#operativoCentro'),d=$('#operativoDynamic');c?.classList.add('hidden');d?.classList.remove('hidden');$('#operativoDynamicTitle').textContent='Operación';$('#operativoDynamicSub').textContent='Resumen ejecutivo de operación y productividad';let meta;try{meta=await api('/api/operation/meta',{timeoutMs:60000})}catch(e){$('#operativoDynamicContent').innerHTML=`<div class="infoempty">No fue posible abrir el resumen: ${esc(e.message)}</div>`;return}await setup(meta);const q=new URLSearchParams({period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store:$('#operStoreSelect')?.value||'Compañía'});let r;try{r=await api('/api/operation/summary-v149?'+q,{timeoutMs:180000})}catch(e){$('#operativoDynamicContent').innerHTML=`${tabs()}<div class="infoempty">No fue posible consultar el resumen: ${esc(e.message)}</div>`;bindTabs();return}$('#operativoDynamicContent').innerHTML=`${tabs()}${cards(r.summary||{})}<div class="v149-grid">${comp(r.comparison||[])}${alerts(r.alerts||[])}</div>${storeTable(r.stores||[])}${top(r.top||[])}`;bindTabs()}
const previousRender=window.renderOperativoView;window.renderOperativoView=async function(name,force=false){if(name!==OP)return previousRender(name,force);if(V149_OPERATION_TAB==='summary')return renderSummary();V125_OPERATION_TAB=V149_OPERATION_TAB;const out=await previousRender(name,force);const old=document.querySelector('.v125-tabs');if(old){old.insertAdjacentHTML('afterbegin','<button class="v125-tab" data-v149-tab="summary">Resumen</button>');old.querySelector('[data-v149-tab="summary"]').onclick=async()=>{V149_OPERATION_TAB='summary';await renderOperativoView(OP,true)}}return out};
const mode=$('#operPeriodMode');mode?.addEventListener('change',async()=>{if(MAIN==='operation'&&V149_OPERATION_TAB==='summary'){OPER_PERIOD.type=mode.value;OPER_PERIOD.value='';await renderOperativoView(OP,true)}});const apply=$('#operPeriodApply');apply?.addEventListener('click',async()=>{if(MAIN==='operation'&&V149_OPERATION_TAB==='summary'){OPER_PERIOD.value=$('#operPeriodSelect')?.value||'';await renderOperativoView(OP,true)}});document.addEventListener('click',e=>{if(e.target.closest?.('[data-main="operation"]')){V149_OPERATION_TAB='summary';setTimeout(()=>renderOperativoView(OP,true),80)}},true);console.info('[V149] Resumen restaurado como primera pestaña de Operación.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v149_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v149-operation-summary-js" not in html:
                html=html.replace("</head>",css+"</head>",1).replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V149"})
        except Exception as exc:
            print(f"[V149] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V149_OPERATION_SUMMARY_RESTORE=True
    print("[V149] Resumen ejecutivo de Operación restaurado como primera pestaña.",flush=True)
