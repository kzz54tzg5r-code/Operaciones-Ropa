"""V126 · Resumen de Operación.

Restaura como primera pestaña el Resumen solicitado para el módulo Operación.
Conserva V125: Captura diaria, Cargar productividad, Productividad y Estándares.
El resumen usa Origen = Colgado + Doblado para llegada/liberación y cruza la
productividad individual con Cambios y Muertos automático.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V126_OPERATION_SUMMARY", False):
        return

    def _num(v):
        try:
            return float(v or 0)
        except Exception:
            return 0.0

    def _period_bounds(kind: str, value: str):
        kind = str(kind or "day").lower().strip()
        value = str(value or "").strip()
        today = datetime.now(MX).date()
        if kind == "day":
            d = datetime.strptime(value[:10], "%Y-%m-%d").date() if value else today
            return d, d
        if kind == "week":
            if value:
                import re
                mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, flags=re.I)
                if not mt:
                    raise HTTPException(400, "Semana ISO inválida")
                start = date.fromisocalendar(int(mt.group(1)), int(mt.group(2)), 1)
            else:
                iso = today.isocalendar(); start = date.fromisocalendar(iso.year, iso.week, 1)
            return start, start + timedelta(days=6)
        if kind == "month":
            if value:
                y, mo = (int(x) for x in value.split("-")[:2])
            else:
                y, mo = today.year, today.month
            start = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return start, nxt - timedelta(days=1)
        if kind == "year":
            y = int(value or today.year)
            return date(y, 1, 1), date(y, 12, 31)
        raise HTTPException(400, "Vista inválida")

    def _scope_stores(actor, requested):
        role = str(actor.get("role") or "")
        assigned = str(actor.get("store") or "").strip()
        if role in ("tienda", "colaborador"):
            if not assigned:
                raise HTTPException(409, "El usuario no tiene tienda asignada")
            return [assigned], assigned
        selected = str(requested or "Compañía").strip() or "Compañía"
        if selected != "Compañía":
            return [selected], selected
        try:
            return list(m.store_names(True)), "Compañía"
        except Exception:
            return list(getattr(m, "PROJECT_STORES", [])), "Compañía"

    @m.app.get("/api/operation/origin-summary")
    def operation_origin_summary(request: Request, period_type: str = "day", period_value: str = "", store: str = "Compañía"):
        actor = m.require_user(request)
        start, end = _period_bounds(period_type, period_value)
        stores, selected_store = _scope_stores(actor, store)
        if not stores:
            return {"start_date": start.isoformat(), "end_date": end.isoformat(), "store": selected_store, "summary": {}, "daily": [], "by_store": []}

        ph = ",".join("?" for _ in stores)
        with m.db() as con:
            caps = [dict(r) for r in con.execute(
                f"SELECT date,store,arrival,released FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ({ph}) ORDER BY date,store",
                (end.isoformat(), *stores),
            ).fetchall()]
            prod = [dict(r) for r in con.execute(
                f"SELECT date,store,user_id,employee_no,employee_name,origin,pieces FROM operation_productivity WHERE origin IN ('Colgado','Doblado') AND date<=? AND store IN ({ph}) ORDER BY date,id",
                (end.isoformat(), *stores),
            ).fetchall()]
            stdrows = con.execute("SELECT origin,pieces_per_shift FROM operation_standards WHERE origin IN ('Colgado','Doblado')").fetchall()

        standards = {str(r["origin"]): _num(r["pieces_per_shift"]) for r in stdrows}
        standards.setdefault("Colgado", 1228.0); standards.setdefault("Doblado", 906.0)

        capmap = {(str(r["date"]), str(r["store"])): r for r in caps}
        prod_daily = {}
        people_daily = {}
        target_keys = set()
        for r in prod:
            ds, st = str(r["date"]), str(r["store"])
            key = (ds, st)
            prod_daily[key] = prod_daily.get(key, 0.0) + _num(r.get("pieces"))
            person = str(r.get("employee_no") or r.get("user_id") or r.get("employee_name") or "").strip()
            if person:
                people_daily.setdefault(key, set()).add(person)
                target_keys.add((ds, st, person, str(r.get("origin") or "")))

        dates = [date.fromisoformat(str(r["date"])) for r in caps if r.get("date")] + [date.fromisoformat(str(r["date"])) for r in prod if r.get("date")]
        calc_start = min(dates) if dates else start
        if calc_start > start:
            calc_start = start

        pending_by_store = {st: 0.0 for st in stores}
        period_daily = []
        by_store_acc = {st: {"store": st, "arrival": 0.0, "processed": 0.0, "released": 0.0, "pending_start": None, "pending": 0.0, "employee_days": set(), "people": set(), "target": 0.0} for st in stores}
        cursor = calc_start
        while cursor <= end:
            ds = cursor.isoformat()
            day = {"date": ds, "arrival": 0.0, "processed": 0.0, "released": 0.0, "pending": 0.0}
            for st in stores:
                c = capmap.get((ds, st), {})
                arrival = _num(c.get("arrival")); released = _num(c.get("released")); processed = _num(prod_daily.get((ds, st)))
                prev = pending_by_store.get(st, 0.0)
                pending = max(prev + arrival - processed, 0.0)
                pending_by_store[st] = pending
                if start <= cursor <= end:
                    acc = by_store_acc[st]
                    if acc["pending_start"] is None:
                        acc["pending_start"] = prev
                    acc["arrival"] += arrival; acc["processed"] += processed; acc["released"] += released; acc["pending"] = pending
                    for p in people_daily.get((ds, st), set()):
                        acc["people"].add(p); acc["employee_days"].add((ds, p))
                    day["arrival"] += arrival; day["processed"] += processed; day["released"] += released; day["pending"] += pending
            if start <= cursor <= end:
                period_daily.append(day)
            cursor += timedelta(days=1)

        for ds, st, person, origin in target_keys:
            if start.isoformat() <= ds <= end.isoformat() and st in by_store_acc:
                by_store_acc[st]["target"] += _num(standards.get(origin))

        by_store = []
        for st, a in by_store_acc.items():
            a["pending_start"] = _num(a["pending_start"])
            workload = a["pending_start"] + a["arrival"]
            employee_days = len(a["employee_days"])
            people = len(a["people"])
            target = a["target"]
            by_store.append({
                "store": st, "arrival": a["arrival"], "processed": a["processed"], "released": a["released"],
                "pending_start": a["pending_start"], "pending": a["pending"],
                "efficiency_pct": a["processed"] / workload * 100 if workload else 0.0,
                "productivity_daily": a["processed"] / employee_days if employee_days else 0.0,
                "target": target, "compliance_pct": a["processed"] / target * 100 if target else 0.0,
                "collaborators": people,
            })
        by_store.sort(key=lambda x: (-x["compliance_pct"], -x["processed"], x["store"]))

        total_arrival = sum(x["arrival"] for x in by_store); total_processed = sum(x["processed"] for x in by_store); total_released = sum(x["released"] for x in by_store)
        total_pending_start = sum(x["pending_start"] for x in by_store); total_pending = sum(x["pending"] for x in by_store); total_target = sum(x["target"] for x in by_store)
        unique_people = set(); employee_days = set()
        for (ds, st), ps in people_daily.items():
            if start.isoformat() <= ds <= end.isoformat():
                for p in ps:
                    unique_people.add((st, p)); employee_days.add((ds, st, p))
        workload = total_pending_start + total_arrival
        summary = {
            "arrival": total_arrival, "processed": total_processed, "released": total_released,
            "pending_start": total_pending_start, "pending": total_pending,
            "efficiency_pct": total_processed / workload * 100 if workload else 0.0,
            "productivity_daily": total_processed / len(employee_days) if employee_days else 0.0,
            "target": total_target, "compliance_pct": total_processed / total_target * 100 if total_target else 0.0,
            "collaborators": len(unique_people),
        }
        return {"start_date": start.isoformat(), "end_date": end.isoformat(), "store": selected_store, "summary": summary, "daily": period_daily, "by_store": by_store}

    css = r'''<style id="v126-operation-summary-css">
.v126-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.v126-kpi{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;position:relative;overflow:hidden}.v126-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--vc,#246fe5)}.v126-kpi small{display:block;font-size:7px;font-weight:950;color:#667085;text-transform:uppercase}.v126-kpi b{display:block;font-size:22px;color:var(--navy);margin:6px 0 2px}.v126-kpi span{font-size:8px;color:#667085}.v126-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v126-panel{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;margin:10px 0}.v126-title{font-size:12px;font-weight:950;color:var(--navy);margin-bottom:8px}.v126-bar{display:grid;grid-template-columns:minmax(95px,1fr) minmax(100px,2fr) 64px;gap:7px;align-items:center;font-size:8px;margin:7px 0}.v126-track{height:15px;background:#edf2f7;border-radius:6px;overflow:hidden}.v126-fill{height:100%;background:#246fe5;border-radius:6px}.v126-alert{padding:9px;border-radius:9px;background:#f8fafc;border:1px solid var(--line);font-size:9px;color:#526277;margin:6px 0}.v126-alert b{color:var(--navy)}
@media(max-width:900px){.v126-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v126-grid{grid-template-columns:1fr}.v126-kpi b{font-size:20px}.v126-bar{grid-template-columns:90px minmax(80px,1fr) 56px}}
</style>'''

    js = r'''<script id="v126-operation-summary-js">
(function(){
  const OP='Operación',num=v=>Number(v||0),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const f1=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1}),pct=v=>`${f1(v)}%`;
  function mxToday(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()),g=t=>p.find(x=>x.type===t)?.value||'';return `${g('year')}-${g('month')}-${g('day')}`}
  function weekOfDate(ds){const d=new Date(ds+'T12:00:00'),t=new Date(d.valueOf()),n=(d.getDay()+6)%7;t.setDate(t.getDate()-n+3);const f=new Date(t.getFullYear(),0,4),w=1+Math.round(((t-f)/86400000-3+(f.getDay()+6)%7)/7);return `${t.getFullYear()}-W${String(w).padStart(2,'0')}`}
  function values(meta,type){if(type==='day')return meta.dates||[];if(type==='week')return meta.weeks||[];if(type==='month')return meta.months||[];return meta.years||[]}
  function defaultPeriod(meta,type){const d=mxToday(),arr=values(meta,type);if(type==='day')return d;if(arr.length)return arr[arr.length-1];if(type==='week')return weekOfDate(d);if(type==='month')return d.slice(0,7);return d.slice(0,4)}
  function setSel(el,vals,current){if(!el)return;el.innerHTML='';vals.forEach(v=>el.add(new Option(v,v)));if(vals.includes(current))el.value=current;else if(vals.length)el.value=vals[vals.length-1]}
  function summaryTabs(){return `<div class="v125-tabs" role="tablist"><button class="v125-tab active" data-v125-tab="summary">Resumen</button><button class="v125-tab" data-v125-tab="daily">Captura diaria</button><button class="v125-tab" data-v125-tab="capture">Cargar productividad</button><button class="v125-tab" data-v125-tab="productivity">Productividad</button><button class="v125-tab" data-v125-tab="standards">Estándares</button></div>`}
  function addSummaryButton(){const tabs=document.querySelector('.v125-tabs');if(!tabs||tabs.querySelector('[data-v125-tab="summary"]'))return;const b=document.createElement('button');b.className='v125-tab';b.dataset.v125Tab='summary';b.textContent='Resumen';tabs.prepend(b);b.onclick=async()=>{V125_OPERATION_TAB='summary';OPER_PERIOD.value='';await renderOperativoView(OP,true)}}
  function bindTabs(){document.querySelectorAll('[data-v125-tab]').forEach(b=>b.onclick=async()=>{V125_OPERATION_TAB=b.dataset.v125Tab;OPER_PERIOD.value='';if(V125_OPERATION_TAB==='daily'||V125_OPERATION_TAB==='capture')OPER_PERIOD.type='day';await renderOperativoView(OP,true)})}
  function setupSummaryFilters(meta){
    const bar=$('#operativoPeriodBar');bar?.classList.remove('hidden');$('#operPeriodModeWrap')?.classList.remove('hidden');
    const origin=$('#operAreaSelect')?.closest('.filter'),collab=$('#operActivitySelect')?.closest('.filter');origin?.classList.add('hidden');collab?.classList.add('hidden');
    if(!['day','week','month','year'].includes(OPER_PERIOD.type))OPER_PERIOD.type='day';
    const mode=$('#operPeriodMode');if(mode){mode.innerHTML='<option value="day">Día</option><option value="week">Semanal</option><option value="month">Mensual</option><option value="year">Anual</option>';mode.value=OPER_PERIOD.type}
    let vals=values(meta,OPER_PERIOD.type);if(OPER_PERIOD.type==='day')vals=[...new Set([...(vals||[]),mxToday()])].sort();if(!OPER_PERIOD.value||!vals.includes(OPER_PERIOD.value))OPER_PERIOD.value=defaultPeriod(meta,OPER_PERIOD.type);setSel($('#operPeriodSelect'),vals.length?vals:[OPER_PERIOD.value],OPER_PERIOD.value);
    $('#operPeriodModeLabel').textContent='Vista';$('#operPeriodLabel').textContent=OPER_PERIOD.type==='day'?'Fecha':OPER_PERIOD.type==='week'?'Semana ISO':OPER_PERIOD.type==='month'?'Mes':'Año';
    const ss=$('#operStoreSelect');if(ss){const old=ss.value,restricted=USER?.role==='tienda'||USER?.role==='colaborador';ss.innerHTML='';if(!restricted)ss.add(new Option('Compañía','Compañía'));(meta.stores||[]).forEach(s=>ss.add(new Option(s,s)));if(restricted){ss.value=USER.store||meta.stores?.[0]||'';ss.disabled=true}else{ss.disabled=false;ss.value=Array.from(ss.options).some(o=>o.value===old)?old:'Compañía'}ss.closest('.filter')?.classList.remove('hidden');ss.parentElement.querySelector('label').textContent='Tienda'}
  }
  function cards(s,cm){const c=[['Llegada Origen',s.arrival,'Colgado + Doblado','#246fe5'],['Productividad',s.processed,'Piezas registradas','#7338ef'],['Mercancía liberada',s.released,'Origen','#ec007c'],['Pendiente',s.pending,'Origen al cierre','#ef3434'],['Eficiencia',pct(s.efficiency_pct),'Procesadas / carga','#10b981'],['Prod. promedio',f1(s.productivity_daily),'Pzas / colaborador / día','#f3a300'],['Cumplimiento',pct(s.compliance_pct),'Vs estándar','#10b981'],['Colaboradores',s.collaborators,'Con captura en periodo','#173f78']];return `<div class="v126-kpis">${c.map(x=>`<div class="v126-kpi" style="--vc:${x[3]}"><small>${x[0]}</small><b>${typeof x[1]==='string'?x[1]:fmt(x[1])}</b><span>${x[2]}</span></div>`).join('')}</div>`}
  function originTable(s,cm){const rows=[{name:'Origen',arrival:s.arrival,processed:s.processed,released:s.released,pending:s.pending,eff:s.efficiency_pct,comp:s.compliance_pct},{name:'Cambios y Muertos',arrival:num(cm?.arrival),processed:num(cm?.processed),released:num(cm?.released),pending:num(cm?.pending),eff:num(cm?.efficiency_pct),comp:num(cm?.compliance_pct)}];return `<div class="tablewrap"><table class="table"><thead><tr><th>Origen operativo</th><th>Llegada</th><th>Procesadas</th><th>Liberadas / Ubicadas</th><th>Pendiente</th><th>Eficiencia</th><th>Cumplimiento</th></tr></thead><tbody>${rows.map(r=>`<tr><td><b>${r.name}</b></td><td>${fmt(r.arrival)}</td><td>${fmt(r.processed)}</td><td>${fmt(r.released)}</td><td>${fmt(r.pending)}</td><td>${pct(r.eff)}</td><td><b class="${r.comp>=100?'metric-good':r.comp>=75?'metric-warn':'metric-bad'}">${pct(r.comp)}</b></td></tr>`).join('')}</tbody></table></div>`}
  function bars(rows){const max=Math.max(1,...rows.map(r=>Math.max(num(r.processed),num(r.target))));return rows.map(r=>`<div class="v126-bar"><b>${esc(r.store)}</b><div><div class="v126-track"><div class="v126-fill" style="width:${Math.min(100,num(r.processed)/max*100)}%"></div></div></div><span>${pct(r.compliance_pct)}</span></div>`).join('')||'<div class="infoempty">Sin productividad en el periodo.</div>'}
  function topPeople(rows){const top=(rows||[]).slice(0,5),max=Math.max(1,...top.map(x=>num(x.pieces)));return top.map((r,i)=>`<div class="v126-bar"><b>#${i+1} ${esc(r.name)}</b><div class="v126-track"><div class="v126-fill" style="width:${Math.min(100,num(r.pieces)/max*100)}%"></div></div><span>${fmt(r.pieces)}</span></div>`).join('')||'<div class="infoempty">Sin colaboradores con productividad.</div>'}
  function alerts(s,cm){const out=[];if(num(s.pending)>0)out.push(`<div class="v126-alert"><b>Pendiente Origen:</b> ${fmt(s.pending)} piezas al cierre del periodo.</div>`);if(num(s.compliance_pct)<75&&num(s.target)>0)out.push(`<div class="v126-alert"><b>Cumplimiento bajo:</b> ${pct(s.compliance_pct)} contra el estándar de productividad.</div>`);if(cm&&num(cm.pending)>0)out.push(`<div class="v126-alert"><b>Cambios y Muertos:</b> ${fmt(cm.pending)} piezas pendientes.</div>`);return out.join('')||'<div class="v126-alert"><b>Sin alertas críticas</b> para el periodo consultado.</div>'}
  async function renderSummary(){
    const content=$('#operativoDynamicContent');if(content)content.innerHTML='<div class="infoempty">Cargando resumen de Operación...</div>';
    let meta;try{meta=await api('/api/operation/meta',{timeoutMs:60000})}catch(e){content.innerHTML=`<div class="infoempty">${esc(e.message)}</div>`;return}setupSummaryFilters(meta);
    const store=$('#operStoreSelect')?.value||'Compañía',q=new URLSearchParams({period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store});
    let origin,rep;try{[origin,rep]=await Promise.all([api('/api/operation/origin-summary?'+q,{timeoutMs:120000}),api('/api/operation/report?'+new URLSearchParams({period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store,origin:'Todos',employee_no:''}),{timeoutMs:180000})])}catch(e){content.innerHTML=`${summaryTabs()}<div class="infoempty">Error consultando resumen: ${esc(e.message)}</div>`;bindTabs();return}
    const s=origin.summary||{},cm=(rep.origin_summary||[]).find(x=>x.origin==='Cambios y Muertos')||{},storeRows=origin.by_store||[],people=rep.productivity||[];
    content.innerHTML=`${summaryTabs()}${cards(s,cm)}<div class="title">Resumen por origen</div>${originTable(s,cm)}<div class="v126-grid"><div class="v126-panel"><div class="v126-title">Desempeño vs estándar por tienda</div>${bars(storeRows.slice(0,17))}</div><div class="v126-panel"><div class="v126-title">Top 5 colaboradores</div>${topPeople(people)}</div><div class="v126-panel"><div class="v126-title">Alertas operativas</div>${alerts(s,cm)}</div><div class="v126-panel"><div class="v126-title">Lectura del periodo</div><div class="v126-alert"><b>${esc(origin.start_date||'')} → ${esc(origin.end_date||'')}</b><br>Origen agrupa Colgado + Doblado. Cambios y Muertos se integra automáticamente.</div></div></div><div class="v125-actions"><button class="primary" id="v126SummaryPdf">Descargar PDF</button><button class="primary" id="v126SummaryXlsx">Descargar Excel</button></div>`;
    bindTabs();$('#v126SummaryPdf')?.addEventListener('click',()=>download('pdf'));$('#v126SummaryXlsx')?.addEventListener('click',()=>download('xlsx'));
  }
  async function download(format){const q=new URLSearchParams({format,period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store:$('#operStoreSelect')?.value||'Compañía',origin:'Todos',employee_no:''}),r=await fetch('/api/operation/export?'+q,{credentials:'same-origin'});if(!r.ok)throw new Error(await r.text());const blob=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`Operacion_Resumen.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}

  const prev=window.renderOperativoView;
  window.renderOperativoView=async function(name,force=false){
    if(name!==OP)return prev(name,force);
    if(USER?.role!=='colaborador'&&V125_OPERATION_TAB==='summary'){
      const centro=$('#operativoCentro'),dyn=$('#operativoDynamic');centro?.classList.add('hidden');dyn?.classList.remove('hidden');$('#operativoDynamicTitle').textContent='Operación';$('#operativoDynamicSub').textContent='Resumen ejecutivo y operativo';await renderSummary();return;
    }
    const out=await prev(name,force);addSummaryButton();return out;
  };
  const mode=$('#operPeriodMode');if(mode)mode.addEventListener('change',async()=>{if(OP_VIEW===OP&&V125_OPERATION_TAB==='summary'){OPER_PERIOD.type=mode.value;OPER_PERIOD.value='';await renderOperativoView(OP,true)}});
  const apply=$('#operPeriodApply');if(apply)apply.addEventListener('click',async()=>{if(OP_VIEW===OP&&V125_OPERATION_TAB==='summary'){OPER_PERIOD.value=$('#operPeriodSelect')?.value||'';await renderOperativoView(OP,true)}});
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-main="operation"]');if(b&&USER?.role!=='colaborador')V125_OPERATION_TAB='summary'},true);
  if(USER?.role!=='colaborador'&&window.V125_OPERATION_TAB==='daily')window.V125_OPERATION_TAB='summary';
  console.info('[V126] Resumen de Operación restaurado como primera pestaña.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v126_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v126-operation-summary-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0", "X-Operations-UI-Version": "V126"
            })
        except Exception as exc:
            print(f"[V126] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V126_OPERATION_SUMMARY = True
    print("[V126] Resumen de Operación instalado y fijado como primera pestaña.", flush=True)
