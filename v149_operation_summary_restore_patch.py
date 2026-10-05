"""V149.3 · Restaura Resumen como primera pestaña de Operación.

Se instala al final de la cadena para que no lo oculten los parches posteriores.
Resumen: Llegada Origen, productividad, mercancía liberada, pendiente,
eficiencia, productividad promedio, cumplimiento y colaboradores.
El módulo Operación es exclusivamente Origen; Cambios y Muertos se mantiene
separado en su propio módulo.
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
        """Resumen del módulo Operación: EXCLUSIVAMENTE flujo Origen.

        El pendiente usa la última captura manual disponible como cierre
        autoritativo. Si no existe captura, usa sólo el último día con movimiento. Para
        Semana/Mes/Año se toma saldo de apertura + movimientos del periodo;
        nunca se suman pendientes diarios.
        """
        actor = m.require_user(request)
        start, end = bounds(period_type, period_value)
        stores, selected = scoped_stores(actor, store)
        if not stores:
            return {"summary":{},"comparison":[],"stores":[],"top":[],"alerts":[]}

        ss, es = start.isoformat(), end.isoformat()
        day_before = (start - timedelta(days=1)).isoformat()
        ph = ",".join("?" for _ in stores)
        std = standards()

        with m.db() as con:
            caps = [dict(r) for r in con.execute(
                f"""SELECT date,store,arrival,released,pending_manual
                    FROM operation_daily_capture
                    WHERE origin='Origen' AND date<=? AND store IN ({ph})
                    ORDER BY date""",
                (es,*stores)
            ).fetchall()]
            prod = [dict(r) for r in con.execute(
                f"""SELECT date,store,user_id,employee_no,employee_name,origin,pieces
                    FROM operation_productivity
                    WHERE origin IN ('Colgado','Doblado','Jeans','Lencería')
                      AND date<=? AND store IN ({ph})
                    ORDER BY date,id""",
                (es,*stores)
            ).fetchall()]

        def family(origin):
            org = str(origin or "")
            if org in ("Colgado","Lencería"):
                return "Colgado"
            if org in ("Doblado","Jeans"):
                return "Doblado"
            return org

        def balance_to(st, cutoff):
            """Saldo Origen al corte sin acumular toda la historia.

            Prioridad:
            1) última captura manual de pendiente y movimientos posteriores;
            2) si no existe captura manual, usar sólo el último día con movimiento
               como saldo de cierre, nunca la suma histórica completa.
            """
            st_caps = [r for r in caps if str(r.get("store") or "")==st and str(r.get("date") or "")<=cutoff]
            st_prod = [r for r in prod if str(r.get("store") or "")==st and str(r.get("date") or "")<=cutoff]
            explicit = [r for r in st_caps if r.get("pending_manual") is not None]
            if explicit:
                anchor = max(explicit, key=lambda r:str(r.get("date") or ""))
                anchor_day = str(anchor.get("date") or "")
                bal = n(anchor.get("pending_manual"))
                bal += sum(n(r.get("arrival")) for r in st_caps if str(r.get("date") or "")>anchor_day)
                bal -= sum(n(r.get("pieces")) for r in st_prod if str(r.get("date") or "")>anchor_day)
                return max(bal,0.0), "capturado"

            days = sorted({
                str(r.get("date") or "") for r in (st_caps + st_prod)
                if str(r.get("date") or "")
            })
            if not days:
                return 0.0, "calculado"
            last_day = days[-1]
            arrivals = sum(n(r.get("arrival")) for r in st_caps if str(r.get("date") or "")==last_day)
            processed = sum(n(r.get("pieces")) for r in st_prod if str(r.get("date") or "")==last_day)
            return max(arrivals-processed,0.0), "calculado"

        cp=[r for r in caps if ss<=str(r.get("date") or "")<=es]
        pp=[r for r in prod if ss<=str(r.get("date") or "")<=es]

        opening_by={}
        closing_by={}
        pending_source={}
        for st in stores:
            opening_by[st], opening_source = balance_to(st,day_before)

            st_cp=[r for r in cp if str(r.get("store") or "")==st]
            st_pp=[r for r in pp if str(r.get("store") or "")==st]
            explicit_period=[r for r in st_cp if r.get("pending_manual") is not None]

            if explicit_period:
                anchor=max(explicit_period,key=lambda r:str(r.get("date") or ""))
                anchor_day=str(anchor.get("date") or "")
                bal=n(anchor.get("pending_manual"))
                bal+=sum(n(r.get("arrival")) for r in st_cp if str(r.get("date") or "")>anchor_day)
                bal-=sum(n(r.get("pieces")) for r in st_pp if str(r.get("date") or "")>anchor_day)
                closing_by[st]=max(bal,0.0)
                pending_source[st]="capturado"
            else:
                # Regla acordada: saldo inicial del periodo + movimientos acumulados,
                # sin sumar pendientes diarios ni arrastrar toda la historia.
                period_arrival=sum(n(r.get("arrival")) for r in st_cp)
                period_processed=sum(n(r.get("pieces")) for r in st_pp)
                closing_by[st]=max(opening_by[st]+period_arrival-period_processed,0.0)
                pending_source[st]=opening_source

        oa=sum(n(r.get("arrival")) for r in cp)
        op=sum(n(r.get("pieces")) for r in pp)
        orl=sum(n(r.get("released")) for r in cp)
        opening_total=sum(opening_by.values())
        total_pending=sum(closing_by.values())
        workload=opening_total+oa

        # Productividad sólo del flujo Origen (Colgado/Doblado/Jeans/Lencería).
        people={}
        seen_target=set()
        for r in pp:
            name=str(r.get("employee_name") or "Sin nombre").strip()
            eno=str(r.get("employee_no") or "").strip()
            st=str(r.get("store") or "")
            fam=family(r.get("origin"))
            key=(eno or name.casefold(),st)
            g=people.setdefault(key,{"name":name,"store":st,"pieces":0.0,"days":set(),"target":0.0})
            g["pieces"]+=n(r.get("pieces"))
            g["days"].add(str(r.get("date") or ""))
            tk=(key,str(r.get("date") or ""),fam)
            if tk not in seen_target:
                seen_target.add(tk)
                g["target"]+=n(std.get(fam))

        top=[]
        for g in people.values():
            days=max(len(g["days"]),1)
            comp=g["pieces"]/g["target"]*100 if g["target"] else 0
            top.append({
                "name":g["name"],"store":g["store"],"pieces":g["pieces"],
                "daily":g["pieces"]/days,"compliance_pct":comp
            })
        top.sort(key=lambda x:(-x["compliance_pct"],-x["pieces"],x["name"]))
        empdays=sum(max(len(g["days"]),1) for g in people.values())
        avg=sum(g["pieces"] for g in people.values())/empdays if empdays else 0

        # Meta global exclusivamente de Origen.
        target_keys={(str(r.get("date") or ""),str(r.get("store") or ""),family(r.get("origin"))) for r in pp}
        target=sum(n(std.get(fam)) for _,_,fam in target_keys)
        compliance=op/target*100 if target else 0
        efficiency=op/workload*100 if workload else 0

        by=[]
        for st in stores:
            a=sum(n(r.get("arrival")) for r in cp if str(r.get("store") or "")==st)
            p=sum(n(r.get("pieces")) for r in pp if str(r.get("store") or "")==st)
            rel=sum(n(r.get("released")) for r in cp if str(r.get("store") or "")==st)
            keys={(str(r.get("date") or ""),family(r.get("origin"))) for r in pp if str(r.get("store") or "")==st}
            tg=sum(n(std.get(fam)) for _,fam in keys)
            comp=p/tg*100 if tg else 0
            closing=closing_by.get(st,0.0)
            if a or p or rel or tg or opening_by.get(st,0) or closing:
                by.append({
                    "store":st,"arrival":a,"processed":p,"released":rel,
                    "target":tg,"compliance_pct":comp,
                    "pending_opening":opening_by.get(st,0.0),
                    "pending":closing,
                    "pending_source":pending_source.get(st,"calculado"),
                })
        by.sort(key=lambda x:(-x["compliance_pct"],-x["processed"],x["store"]))

        alerts=[]
        if total_pending>0:
            alerts.append({"level":"warn","text":f"Pendiente Origen: {total_pending:,.0f} piezas por procesar."})
        if workload and efficiency<75:
            alerts.append({"level":"bad","text":f"Eficiencia operativa baja: {efficiency:.1f}%."})
        lows=[x for x in by if x["target"] and x["compliance_pct"]<75]
        if lows:
            alerts.append({"level":"bad","text":"Tiendas bajo 75% de cumplimiento: "+", ".join(x["store"] for x in lows[:5])+"."})
        if not alerts:
            alerts=[{"level":"ok","text":"Sin alertas críticas para el periodo consultado."}]

        return {
            "start_date":ss,
            "end_date":es,
            "store":selected,
            "summary":{
                "arrival_origin":oa,
                "processed":op,
                "released":orl,
                "pending":total_pending,
                "pending_opening":opening_total,
                "efficiency_pct":efficiency,
                "productivity_avg":avg,
                "compliance_pct":compliance,
                "collaborators":len(people),
            },
            "comparison":[{
                "name":"Origen","arrival":oa,"processed":op,"released":orl,
                "pending":total_pending,"pending_opening":opening_total
            }],
            "stores":by,
            "top":top[:5],
            "alerts":alerts,
        }

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
function cards(s){const d=[['Llegada Origen',s.arrival_origin,'Colgado + Doblado','#246fe5'],['Productividad registrada',s.processed,'Piezas procesadas','#7338ef'],['Mercancía liberada',s.released,'Origen','#ec007c'],['Pendiente',s.pending,'Piezas por procesar','#ef3434'],['Eficiencia',f1(s.efficiency_pct)+'%','Procesadas / carga','#10b981'],['Prod. promedio',f1(s.productivity_avg),'Pzas / colaborador / día','#f3a300'],['Cumplimiento',f1(s.compliance_pct)+'%','Vs estándar','#10b981'],['Colaboradores',s.collaborators,'Con productividad','#173f78']];return `<div class="v149-kpis">${d.map(x=>`<div class="v149-kpi" style="--k:${x[3]}"><small>${x[0]}</small><b>${typeof x[1]==='string'?x[1]:fn(x[1])}</b><span>${x[2]}</span></div>`).join('')}</div>`}
function comp(rows){return ''}
function storeTable(rows){return `<div class="v149-panel"><h3>Desempeño por tienda</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Llegada</th><th>Procesadas</th><th>Liberadas</th><th>Meta</th><th>Cumplimiento</th></tr></thead><tbody>${rows.length?rows.map(r=>`<tr><td><b>${esc(r.store)}</b></td><td>${fn(r.arrival)}</td><td>${fn(r.processed)}</td><td>${fn(r.released)}</td><td>${fn(r.target)}</td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${f1(r.compliance_pct)}%</b></td></tr>`).join(''):'<tr><td colspan="6">Sin información para el periodo.</td></tr>'}</tbody></table></div></div>`}
function top(rows){return `<div class="v149-panel"><h3>Top 5 colaboradores</h3><div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Colaborador</th><th>Tienda</th><th>Piezas</th><th>Prod. diaria</th><th>Cumplimiento</th></tr></thead><tbody>${rows.length?rows.map((r,i)=>`<tr><td>#${i+1}</td><td><b>${esc(r.name)}</b></td><td>${esc(r.store)}</td><td>${fn(r.pieces)}</td><td>${fn(r.daily)}</td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${f1(r.compliance_pct)}%</b></td></tr>`).join(''):'<tr><td colspan="6">Sin productividad registrada.</td></tr>'}</tbody></table></div></div>`}
function alerts(rows){return `<div class="v149-panel"><h3>Alertas operativas</h3>${rows.map(a=>`<div class="v149-alert ${a.level||'warn'}">${esc(a.text)}</div>`).join('')}</div>`}
function bindTabs(){document.querySelectorAll('[data-v149-tab]').forEach(b=>b.onclick=async()=>{V149_OPERATION_TAB=b.dataset.v149Tab;if(V149_OPERATION_TAB==='summary'){await renderOperativoView(OP,true);return}V125_OPERATION_TAB=V149_OPERATION_TAB;OPER_PERIOD.value='';if(V149_OPERATION_TAB!=='productivity')OPER_PERIOD.type='day';await renderOperativoView(OP,true)})}
async function renderSummary(){const c=$('#operativoCentro'),d=$('#operativoDynamic');c?.classList.add('hidden');d?.classList.remove('hidden');$('#operativoDynamicTitle').textContent='Operación';$('#operativoDynamicSub').textContent='Resumen ejecutivo de operación y productividad';let meta;try{meta=await api('/api/operation/meta',{timeoutMs:60000})}catch(e){$('#operativoDynamicContent').innerHTML=`<div class="infoempty">No fue posible abrir el resumen: ${esc(e.message)}</div>`;return}await setup(meta);const _ml={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};if($('#operativoDynamicTitle'))$('#operativoDynamicTitle').textContent='Operación · '+(_ml[OPER_PERIOD.type]||'Día');if($('#operativoDynamicSub'))$('#operativoDynamicSub').textContent='Resumen ejecutivo de operación y productividad'+(OPER_PERIOD.value?' · '+OPER_PERIOD.value:'');const q=new URLSearchParams({period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store:$('#operStoreSelect')?.value||'Compañía'});let r;try{r=await api('/api/operation/summary-v149?'+q,{timeoutMs:180000})}catch(e){$('#operativoDynamicContent').innerHTML=`${tabs()}<div class="infoempty">No fue posible consultar el resumen: ${esc(e.message)}</div>`;bindTabs();return}$('#operativoDynamicContent').innerHTML=`${tabs()}${cards(r.summary||{})}${alerts(r.alerts||[])}${storeTable(r.stores||[])}${top(r.top||[])}`;bindTabs()}
const previousRender=window.renderOperativoView;window.renderOperativoView=async function(name,force=false){if(name!==OP)return previousRender(name,force);if(V149_OPERATION_TAB==='summary')return renderSummary();V125_OPERATION_TAB=V149_OPERATION_TAB;const out=await previousRender(name,force);const old=document.querySelector('.v125-tabs');if(old){old.insertAdjacentHTML('afterbegin','<button class="v125-tab" data-v149-tab="summary">Resumen</button>');old.querySelector('[data-v149-tab="summary"]').onclick=async()=>{V149_OPERATION_TAB='summary';await renderOperativoView(OP,true)}}return out};
const mode=$('#operPeriodMode');mode?.addEventListener('change',async()=>{if(MAIN==='operation'&&V149_OPERATION_TAB==='summary'){OPER_PERIOD.type=mode.value;OPER_PERIOD.value='';await renderOperativoView(OP,true)}});const apply=$('#operPeriodApply');apply?.addEventListener('click',async()=>{if(MAIN==='operation'&&V149_OPERATION_TAB==='summary'){OPER_PERIOD.value=$('#operPeriodSelect')?.value||'';await renderOperativoView(OP,true)}});document.addEventListener('click',e=>{if(e.target.closest?.('[data-main="operation"]')){V149_OPERATION_TAB='summary';setTimeout(()=>renderOperativoView(OP,true),80)}},true);console.info('[V149.2] Resumen Origen-only, pendiente capturado/arrastrado y título sincronizado.');
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
    print("[V149.2] Resumen ejecutivo Origen-only restaurado con pendiente autoritativo.",flush=True)
