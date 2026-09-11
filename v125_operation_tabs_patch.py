"""V125 · Operación por pestañas.

Estructura el módulo Operación en cuatro vistas claras:
- Captura diaria: un solo Origen (Colgado + Doblado) con Llegada y Mercancía liberada.
- Cargar productividad: captura individual para colaboradores.
- Productividad: consulta y ranking de productividad.
- Estándares: configuración separada de Colgado, Doblado y Cambios y Muertos.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V125_OPERATION_TABS", False):
        return

    def _actor(request, roles=None):
        return m.require_user(request, roles)

    def _scope_store(actor, requested):
        role = str(actor.get("role") or "")
        assigned = str(actor.get("store") or "").strip()
        if role in ("tienda", "colaborador"):
            if not assigned:
                raise HTTPException(409, "El usuario no tiene tienda asignada")
            return assigned
        return str(requested or "").strip()

    def _day_open(store, day):
        with m.db() as con:
            row = con.execute("SELECT status FROM operation_day_status WHERE date=? AND store=?", (day, store)).fetchone()
        return not row or str(row["status"] or "open") != "closed"

    @m.app.get("/api/operation/origin-capture")
    def operation_origin_capture(request: Request, date: str, store: str):
        actor = _actor(request)
        day = str(date or "")[:10]
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except Exception:
            raise HTTPException(400, "Fecha inválida")
        scoped = _scope_store(actor, store)
        if not scoped or scoped == "Compañía":
            raise HTTPException(400, "Selecciona una tienda")
        with m.db() as con:
            row = con.execute(
                "SELECT arrival,released,notes,updated_at,updated_by FROM operation_daily_capture WHERE date=? AND store=? AND origin='Origen'",
                (day, scoped),
            ).fetchone()
            legacy = None
            if not row:
                legacy = con.execute(
                    "SELECT COALESCE(SUM(arrival),0) arrival,COALESCE(SUM(released),0) released FROM operation_daily_capture WHERE date=? AND store=? AND origin IN ('Colgado','Doblado')",
                    (day, scoped),
                ).fetchone()
            status = con.execute("SELECT * FROM operation_day_status WHERE date=? AND store=?", (day, scoped)).fetchone()
        src = dict(row) if row else {"arrival": float(legacy["arrival"] or 0) if legacy else 0, "released": float(legacy["released"] or 0) if legacy else 0, "notes": "", "updated_at": "", "updated_by": ""}
        return {
            "date": day,
            "store": scoped,
            "origin": "Origen",
            "arrival": float(src.get("arrival") or 0),
            "released": float(src.get("released") or 0),
            "notes": str(src.get("notes") or ""),
            "status": dict(status) if status else {"date": day, "store": scoped, "status": "open"},
            "can_capture": str(actor.get("role") or "") in ("superadmin", "admin", "tienda"),
            "can_close": str(actor.get("role") or "") in ("superadmin", "admin", "tienda"),
            "can_reopen": str(actor.get("role") or "") in ("superadmin", "admin"),
        }

    @m.app.post("/api/operation/origin-capture")
    async def operation_origin_capture_save(request: Request):
        actor = _actor(request, ("superadmin", "admin", "tienda"))
        body = await request.json()
        day = str(body.get("date") or "")[:10]
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except Exception:
            raise HTTPException(400, "Fecha inválida")
        store = _scope_store(actor, body.get("store"))
        if not store or store == "Compañía":
            raise HTTPException(400, "Selecciona una tienda")
        if not _day_open(store, day):
            raise HTTPException(409, "El corte de ese día está cerrado")
        try:
            arrival = max(float(body.get("arrival") or 0), 0)
            released = max(float(body.get("released") or 0), 0)
        except Exception:
            raise HTTPException(400, "Llegada y mercancía liberada deben ser números válidos")
        notes = str(body.get("notes") or "").strip()[:500]
        now = datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            con.execute(
                """INSERT INTO operation_daily_capture(date,store,origin,arrival,released,notes,updated_at,updated_by)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(date,store,origin) DO UPDATE SET
                     arrival=excluded.arrival,released=excluded.released,notes=excluded.notes,
                     updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
                (day, store, "Origen", arrival, released, notes, now, str(actor.get("username") or "")),
            )
        return {"ok": True, "message": "Captura de Origen guardada", "arrival": arrival, "released": released}

    @m.app.get("/api/operation/collaborators")
    def operation_collaborators(request: Request, store: str = "Compañía"):
        actor = _actor(request)
        role = str(actor.get("role") or "")
        scoped = _scope_store(actor, store)
        with m.db() as con:
            if role == "colaborador":
                rows = con.execute(
                    "SELECT id,username,store,employee_no,full_name FROM users WHERE id=? AND active=1",
                    (actor.get("id"),),
                ).fetchall()
            elif scoped and scoped != "Compañía":
                rows = con.execute(
                    "SELECT id,username,store,employee_no,full_name FROM users WHERE role='colaborador' AND active=1 AND store=? ORDER BY full_name,username",
                    (scoped,),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT id,username,store,employee_no,full_name FROM users WHERE role='colaborador' AND active=1 ORDER BY store,full_name,username"
                ).fetchall()
        return {"items": [
            {"id": int(r["id"]), "username": str(r["username"] or ""), "store": str(r["store"] or ""), "employee_no": str(r["employee_no"] or ""), "name": str(r["full_name"] or r["username"] or "")}
            for r in rows
        ]}

    css = r'''<style id="v125-operation-tabs-css">
.v125-tabs{display:flex;gap:7px;overflow-x:auto;padding:2px 0 9px;scrollbar-width:none}.v125-tabs::-webkit-scrollbar{display:none}.v125-tab{border:1px solid var(--line);background:#fff;color:#64748b;border-radius:999px;padding:8px 13px;font-size:9px;font-weight:950;white-space:nowrap;cursor:pointer}.v125-tab.active{background:var(--blue);border-color:var(--blue);color:#fff}.v125-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v125-field label{display:block;font-size:8px;font-weight:950;color:#667085;text-transform:uppercase;margin-bottom:5px}.v125-field input,.v125-field select{width:100%;min-height:44px;border:1px solid #ccd6e2;border-radius:10px;background:#fff;color:var(--text);padding:9px 10px;font-size:16px}.v125-panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:11px}.v125-panel h3{font-size:14px;margin:0 0 4px;color:var(--navy)}.v125-note{font-size:9px;line-height:1.45;color:#667085}.v125-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.v125-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.v125-kpi{background:#fff;border:1px solid var(--line);border-radius:12px;padding:11px}.v125-kpi small{display:block;color:#667085;font-size:7px;font-weight:950;text-transform:uppercase}.v125-kpi b{display:block;font-size:21px;color:var(--navy);margin-top:5px}.v125-rank{display:grid;gap:7px}.v125-rank-row{display:grid;grid-template-columns:minmax(110px,1.1fr) minmax(120px,2fr) 62px;gap:8px;align-items:center;font-size:8px}.v125-rank-track{height:14px;background:#edf2f7;border-radius:6px;overflow:hidden}.v125-rank-fill{height:100%;background:#246fe5;border-radius:6px}.v125-msg{margin-top:8px;font-size:9px;color:#667085}.v125-msg.ok{color:#15803d}.v125-msg.err{color:#b42318}.v125-status{display:inline-flex;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:950}.v125-status.open{background:#dcfce7;color:#166534}.v125-status.closed{background:#fee2e2;color:#991b1b}.v125-grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.v125-standard{background:#f8fafc;border:1px solid var(--line);border-radius:11px;padding:10px}.v125-standard label{display:block;font-size:8px;color:#667085;font-weight:950;text-transform:uppercase;margin-bottom:5px}.v125-standard input{width:100%;min-height:44px;border:1px solid #ccd6e2;border-radius:9px;background:#fff;color:var(--text);padding:8px;font-size:16px}.v125-standard b{font-size:21px;color:var(--navy)}
@media(max-width:900px){.v125-two,.v125-grid3{grid-template-columns:1fr}.v125-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v125-tab{padding:9px 12px;font-size:9px}.v125-rank-row{grid-template-columns:94px minmax(90px,1fr) 56px}.v125-panel{padding:12px}.v125-field input,.v125-field select,.v125-standard input{font-size:16px}}
</style>'''

    js = r'''<script id="v125-operation-tabs-js">
(function(){
  const OP='Operación';
  const num=v=>Number(v||0);
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const fmt1=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1});
  window.V125_OPERATION_TAB=window.V125_OPERATION_TAB||'daily';

  function mxToday(){
    const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const get=t=>parts.find(p=>p.type===t)?.value||'';
    return `${get('year')}-${get('month')}-${get('day')}`;
  }
  function periodOptions(meta,type){if(type==='day')return meta.dates||[];if(type==='week')return meta.weeks||[];if(type==='month')return meta.months||[];return meta.years||[]}
  function weekOfDate(ds){const d=new Date(ds+'T12:00:00');const target=new Date(d.valueOf());const dayNr=(d.getDay()+6)%7;target.setDate(target.getDate()-dayNr+3);const firstThursday=new Date(target.getFullYear(),0,4);const week=1+Math.round(((target-firstThursday)/86400000-3+(firstThursday.getDay()+6)%7)/7);return `${target.getFullYear()}-W${String(week).padStart(2,'0')}`}
  function defaultPeriod(meta,type){const today=mxToday(),arr=periodOptions(meta,type);if(type==='day')return today;if(arr.length)return arr[arr.length-1];if(type==='month')return today.slice(0,7);if(type==='year')return today.slice(0,4);return weekOfDate(today)}
  function setSelect(el,values,current){if(!el)return;el.innerHTML='';values.forEach(v=>el.add(new Option(v,v)));if(current&&values.includes(current))el.value=current;else if(values.length)el.value=values[values.length-1]}
  function tabs(){return `<div class="v125-tabs" role="tablist"><button class="v125-tab ${V125_OPERATION_TAB==='daily'?'active':''}" data-v125-tab="daily">Captura diaria</button><button class="v125-tab ${V125_OPERATION_TAB==='capture'?'active':''}" data-v125-tab="capture">Cargar productividad</button><button class="v125-tab ${V125_OPERATION_TAB==='productivity'?'active':''}" data-v125-tab="productivity">Productividad</button><button class="v125-tab ${V125_OPERATION_TAB==='standards'?'active':''}" data-v125-tab="standards">Estándares</button></div>`}

  function setFilterVisibility(tab){
    const bar=$('#operativoPeriodBar'),mode=$('#operPeriodModeWrap'),store=$('#operStoreSelect')?.closest('.filter'),origin=$('#operAreaSelect')?.closest('.filter'),collab=$('#operActivitySelect')?.closest('.filter');
    bar?.classList.toggle('hidden',tab==='standards');
    mode?.classList.toggle('hidden',tab!=='productivity');
    if(store)store.classList.remove('hidden');
    if(origin)origin.classList.toggle('hidden',tab!=='productivity');
    if(collab)collab.classList.toggle('hidden',tab!=='productivity');
  }

  async function setupFilters(meta,tab){
    setFilterVisibility(tab);
    if(tab==='daily'||tab==='capture')OPER_PERIOD.type='day';
    if(!['day','week','month','year'].includes(OPER_PERIOD.type))OPER_PERIOD.type='day';
    const mode=$('#operPeriodMode');
    if(mode){mode.innerHTML='<option value="day">Día</option><option value="week">Semanal</option><option value="month">Mensual</option><option value="year">Anual</option>';mode.value=OPER_PERIOD.type}
    const period=$('#operPeriodSelect');
    let vals=periodOptions(meta,OPER_PERIOD.type);
    if(OPER_PERIOD.type==='day')vals=[...new Set([...(vals||[]),mxToday()])].sort();
    if(!OPER_PERIOD.value||!vals.includes(OPER_PERIOD.value)||tab==='daily'||tab==='capture')OPER_PERIOD.value=defaultPeriod(meta,OPER_PERIOD.type);
    setSelect(period,vals.length?vals:[OPER_PERIOD.value],OPER_PERIOD.value);
    $('#operPeriodModeLabel').textContent='Vista';
    $('#operPeriodLabel').textContent=OPER_PERIOD.type==='day'?'Fecha':OPER_PERIOD.type==='week'?'Semana ISO':OPER_PERIOD.type==='month'?'Mes':'Año';
    const ss=$('#operStoreSelect');
    if(ss){
      const old=ss.value,restricted=USER?.role==='tienda'||USER?.role==='colaborador';
      ss.innerHTML='';
      if(tab==='productivity'&&!restricted)ss.add(new Option('Compañía','Compañía'));
      else if(!restricted)ss.add(new Option('Selecciona tienda',''));
      (meta.stores||[]).forEach(s=>ss.add(new Option(s,s)));
      if(restricted){ss.value=USER.store||meta.stores?.[0]||'';ss.disabled=true}
      else{ss.disabled=false;if(Array.from(ss.options).some(o=>o.value===old))ss.value=old;else ss.value=tab==='productivity'?'Compañía':''}
      ss.parentElement.querySelector('label').textContent='Tienda';
    }
    const os=$('#operAreaSelect');
    if(os){const old=os.value;os.innerHTML='<option value="Todos">Todos</option><option value="Colgado">Colgado</option><option value="Doblado">Doblado</option><option value="Cambios y Muertos">Cambios y Muertos</option>';os.value=Array.from(os.options).some(o=>o.value===old)?old:'Todos';os.parentElement.querySelector('label').textContent='Actividad / origen'}
    const cs=$('#operActivitySelect');
    if(cs){const old=cs.value;cs.innerHTML='<option value="">Todos</option>';(meta.collaborators||[]).forEach(p=>cs.add(new Option(`${p.name}${p.employee_no?' · '+p.employee_no:''}`,p.employee_no||'')));cs.value=Array.from(cs.options).some(o=>o.value===old)?old:'';cs.parentElement.querySelector('label').textContent='Colaborador';cs.disabled=USER?.role==='colaborador'}
  }

  async function dailyView(){
    const store=$('#operStoreSelect')?.value||'';
    if(!store)return `<div class="v125-panel"><h3>Captura diaria</h3><div class="infoempty">Selecciona una tienda para capturar el Origen.</div></div>`;
    let d;try{d=await api(`/api/operation/origin-capture?date=${encodeURIComponent(OPER_PERIOD.value)}&store=${encodeURIComponent(store)}`)}catch(e){return `<div class="infoempty">${esc(e.message)}</div>`}
    const closed=d.status?.status==='closed';
    return `<div class="v125-panel"><div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><div><h3>Captura diaria · Origen</h3><div class="v125-note">Origen agrupa <b>Colgado + Doblado</b>. Sólo captura el total de llegada y mercancía liberada.</div></div><span class="v125-status ${closed?'closed':'open'}">${closed?'Cerrado':'En captura'}</span></div><div class="v125-two" style="margin-top:12px"><div class="v125-field"><label>Origen · Llegada</label><input id="v125OriginArrival" type="number" min="0" inputmode="numeric" value="${num(d.arrival)}" ${closed||!d.can_capture?'disabled':''}></div><div class="v125-field"><label>Origen · Mercancía liberada</label><input id="v125OriginReleased" type="number" min="0" inputmode="numeric" value="${num(d.released)}" ${closed||!d.can_capture?'disabled':''}></div></div>${d.can_capture?`<div class="v125-actions"><button class="primary" id="v125SaveOrigin" ${closed?'disabled':''}>Guardar captura</button>${!closed&&d.can_close?'<button class="v121-danger" id="v125CloseDay">Cerrar día</button>':''}${closed&&d.can_reopen?'<button class="v121-danger" id="v125ReopenDay">Reabrir corte</button>':''}</div>`:''}<div id="v125DailyMsg" class="v125-msg"></div><div class="v125-note" style="margin-top:9px">Cambios y Muertos continúa integrándose automáticamente desde el indicador existente; no se captura manualmente aquí.</div></div>`;
  }

  async function captureProductivityView(meta){
    const store=$('#operStoreSelect')?.value||'';
    if(!store)return `<div class="v125-panel"><h3>Cargar productividad</h3><div class="infoempty">Selecciona una tienda.</div></div>`;
    let people={items:[]};try{people=await api(`/api/operation/collaborators?store=${encodeURIComponent(store)}`)}catch(e){}
    const isCollab=USER?.role==='colaborador';
    let rep={my_entries:[]};
    try{const q=new URLSearchParams({period_type:'day',period_value:OPER_PERIOD.value,store:store,origin:'Todos',employee_no:''});rep=await api('/api/operation/report?'+q,{timeoutMs:120000})}catch(e){}
    const personField=isCollab?'':`<div class="v125-field"><label>Colaborador</label><select id="v125ProdPerson"><option value="">Selecciona colaborador</option>${(people.items||[]).map(p=>`<option value="${p.id}">${esc(p.name)}${p.employee_no?' · '+esc(p.employee_no):''}</option>`).join('')}</select></div>`;
    const ownEntries=(rep.my_entries||[]);
    return `<div class="v125-panel"><h3>Cargar productividad</h3><div class="v125-note">Cada colaborador registra sus piezas. Tienda, nómina y nombre se relacionan automáticamente con su usuario.</div><div class="v125-two" style="margin-top:12px"><div class="v125-field"><label>Fecha</label><input id="v125ProdDate" type="date" value="${OPER_PERIOD.value}"></div>${personField}<div class="v125-field"><label>Origen de productividad</label><select id="v125ProdOrigin"><option>Colgado</option><option>Doblado</option></select></div><div class="v125-field"><label>Actividad</label><select id="v125ProdActivity"><option>Acondicionado</option><option>Ubicado</option><option>Clasificado</option><option>Ingreso</option><option>Recolección</option><option>Otro</option></select></div><div class="v125-field"><label>Piezas</label><input id="v125ProdPieces" type="number" min="1" inputmode="numeric" placeholder="0"></div></div><div class="v125-actions"><button class="primary" id="v125SaveProd">Guardar productividad</button></div><div id="v125ProdMsg" class="v125-msg"></div>${isCollab&&ownEntries.length?`<div class="title">Mis capturas del día</div><div class="tablewrap"><table class="table"><thead><tr><th>Origen</th><th>Actividad</th><th>Piezas</th><th></th></tr></thead><tbody>${ownEntries.map(r=>`<tr><td>${esc(r.origin)}</td><td>${esc(r.activity)}</td><td>${fmt(r.pieces)}</td><td><button class="v121-danger v125DeleteProd" data-id="${r.id}">Eliminar</button></td></tr>`).join('')}</tbody></table></div>`:''}</div>`;
  }

  function productivityTable(rows){return `<div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Nómina</th><th>Colaborador</th><th>Tienda</th><th>Piezas</th><th>Días</th><th>Prod. diaria</th><th>Meta</th><th>Cumplimiento</th><th>Origen</th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td>#${i+1}</td><td>${esc(r.employee_no||'—')}</td><td><b>${esc(r.name)}</b></td><td>${esc(r.store)}</td><td>${fmt(r.pieces)}</td><td>${r.days}</td><td>${fmt(r.daily)}</td><td>${fmt(r.target)}</td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${fmt1(r.compliance_pct)}%</b></td><td>${esc((r.origins||[]).join(', '))}</td></tr>`).join('')||'<tr><td colspan="10">Sin productividad para el periodo seleccionado.</td></tr>'}</tbody></table></div>`}
  async function productivityView(){
    const q=new URLSearchParams({period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store:$('#operStoreSelect')?.value||'Compañía',origin:$('#operAreaSelect')?.value||'Todos',employee_no:$('#operActivitySelect')?.value||''});
    let rep;try{rep=await api('/api/operation/report?'+q,{timeoutMs:180000})}catch(e){return `<div class="infoempty">No fue posible consultar productividad: ${esc(e.message)}</div>`}
    const rows=rep.productivity||[],total=rows.reduce((a,r)=>a+num(r.pieces),0),avgDaily=rows.length?rows.reduce((a,r)=>a+num(r.daily),0)/rows.length:0,avgPct=rows.length?rows.reduce((a,r)=>a+num(r.compliance_pct),0)/rows.length:0,target=rows.reduce((a,r)=>a+num(r.target),0),max=Math.max(1,...rows.map(r=>num(r.compliance_pct)));
    const rank=rows.slice(0,25).map((r,i)=>`<div class="v125-rank-row"><b>#${i+1} ${esc(r.name)}</b><div class="v125-rank-track"><div class="v125-rank-fill" style="width:${Math.min(100,num(r.compliance_pct)/Math.max(100,max)*100)}%"></div></div><span>${fmt1(r.compliance_pct)}%</span></div>`).join('')||'<div class="infoempty">Sin registros para graficar.</div>';
    return `<div class="v125-kpis"><div class="v125-kpi"><small>Piezas</small><b>${fmt(total)}</b></div><div class="v125-kpi"><small>Colaboradores</small><b>${rows.length}</b></div><div class="v125-kpi"><small>Prod. diaria prom.</small><b>${fmt(avgDaily)}</b></div><div class="v125-kpi"><small>Cumplimiento prom.</small><b>${fmt1(avgPct)}%</b></div></div><div class="v125-panel"><h3>Ranking de productividad</h3><div class="v125-note">Ordenado por cumplimiento contra el estándar de la actividad.</div><div class="v125-rank" style="margin-top:10px">${rank}</div></div><div class="v125-panel"><h3>Detalle de productividad</h3><div class="v125-note">Meta acumulada del periodo: ${fmt(target)} piezas.</div><div style="margin-top:10px">${productivityTable(rows)}</div><div class="v125-actions"><button class="primary" id="v125ProdPdf">Descargar PDF</button><button class="primary" id="v125ProdXlsx">Descargar Excel</button></div></div>`;
  }

  async function standardsView(){
    let d;try{d=await api('/api/operation/standards')}catch(e){return `<div class="infoempty">${esc(e.message)}</div>`}
    const vals=d.values||{},origins=['Colgado','Doblado','Cambios y Muertos'];
    return `<div class="v125-panel"><h3>Productividad estándar por jornada</h3><div class="v125-note">Los estándares quedan separados de la captura diaria y se utilizan para calcular cumplimiento y productividad.</div><div class="v125-grid3" style="margin-top:12px">${origins.map(o=>d.editable?`<div class="v125-standard"><label>${o}</label><input class="v125-standard-input" data-origin="${o}" type="number" min="1" value="${num(vals[o])}"></div>`:`<div class="v125-standard"><label>${o}</label><b>${fmt(vals[o])}</b><div class="v125-note">pzas/jornada</div></div>`).join('')}</div>${d.editable?'<div class="v125-actions"><button class="primary" id="v125SaveStandards">Guardar estándares</button></div>':''}<div id="v125StdMsg" class="v125-msg"></div></div>`;
  }

  async function downloadProductivity(format){const q=new URLSearchParams({format,period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store:$('#operStoreSelect')?.value||'Compañía',origin:$('#operAreaSelect')?.value||'Todos',employee_no:$('#operActivitySelect')?.value||''});const res=await fetch('/api/operation/export?'+q,{credentials:'same-origin'});if(!res.ok)throw new Error(await res.text());const blob=await res.blob(),a=document.createElement('a');a.href=URL.createObjectURL(blob);const cd=res.headers.get('content-disposition')||'',mt=cd.match(/filename="?([^";]+)"?/i);a.download=mt?mt[1]:`Productividad.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1200)}

  function bindCommon(meta){
    document.querySelectorAll('[data-v125-tab]').forEach(b=>b.onclick=async()=>{V125_OPERATION_TAB=b.dataset.v125Tab;OPER_PERIOD.value='';if(V125_OPERATION_TAB!=='productivity')OPER_PERIOD.type='day';await renderOperativoView(OP,true)});
    $('#v125SaveOrigin')?.addEventListener('click',async()=>{const msg=$('#v125DailyMsg');try{const r=await api('/api/operation/origin-capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:OPER_PERIOD.value,store:$('#operStoreSelect').value,arrival:num($('#v125OriginArrival').value),released:num($('#v125OriginReleased').value)})});msg.className='v125-msg ok';msg.textContent=r.message}catch(e){msg.className='v125-msg err';msg.textContent=e.message}});
    $('#v125CloseDay')?.addEventListener('click',async()=>{if(!confirm('¿Cerrar el corte del día?'))return;try{await api('/api/operation/day-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:OPER_PERIOD.value,store:$('#operStoreSelect').value,action:'close'})});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});
    $('#v125ReopenDay')?.addEventListener('click',async()=>{try{await api('/api/operation/day-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:OPER_PERIOD.value,store:$('#operStoreSelect').value,action:'reopen'})});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});
    $('#v125SaveProd')?.addEventListener('click',async()=>{const msg=$('#v125ProdMsg');try{const body={date:$('#v125ProdDate').value,store:$('#operStoreSelect').value,origin:$('#v125ProdOrigin').value,activity:$('#v125ProdActivity').value,pieces:num($('#v125ProdPieces').value)};if(USER?.role!=='colaborador'){body.user_id=Number($('#v125ProdPerson')?.value||0);if(!body.user_id)throw new Error('Selecciona un colaborador')}const r=await api('/api/operation/productivity',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});msg.className='v125-msg ok';msg.textContent=r.message;$('#v125ProdPieces').value='';setTimeout(()=>renderOperativoView(OP,true),500)}catch(e){msg.className='v125-msg err';msg.textContent=e.message}});
    document.querySelectorAll('.v125DeleteProd').forEach(b=>b.onclick=async()=>{if(!confirm('¿Eliminar esta captura?'))return;try{await api(`/api/operation/productivity/${b.dataset.id}`,{method:'DELETE'});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});
    $('#v125SaveStandards')?.addEventListener('click',async()=>{const msg=$('#v125StdMsg');try{const values={};document.querySelectorAll('.v125-standard-input').forEach(i=>values[i.dataset.origin]=num(i.value));const r=await api('/api/operation/standards',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values})});msg.className='v125-msg ok';msg.textContent=r.message}catch(e){msg.className='v125-msg err';msg.textContent=e.message}});
    $('#v125ProdPdf')?.addEventListener('click',()=>downloadProductivity('pdf').catch(e=>alert(e.message)));$('#v125ProdXlsx')?.addEventListener('click',()=>downloadProductivity('xlsx').catch(e=>alert(e.message)));
  }

  const previousRender=window.renderOperativoView;
  window.renderOperativoView=async function(name,force=false){
    if(name!==OP)return previousRender(name,force);
    const centro=$('#operativoCentro'),dyn=$('#operativoDynamic');if(centro)centro.classList.add('hidden');if(dyn)dyn.classList.remove('hidden');
    $('#operativoDynamicTitle').textContent='Operación';$('#operativoDynamicSub').textContent='Control diario y productividad por colaborador';
    if(USER?.role==='colaborador'&&V125_OPERATION_TAB==='daily')V125_OPERATION_TAB='capture';
    let meta;try{meta=await api('/api/operation/meta',{timeoutMs:60000})}catch(e){$('#operativoDynamicContent').innerHTML=`<div class="infoempty">No fue posible abrir Operación: ${esc(e.message)}</div>`;return}
    await setupFilters(meta,V125_OPERATION_TAB);
    let body='';if(V125_OPERATION_TAB==='daily')body=await dailyView();else if(V125_OPERATION_TAB==='capture')body=await captureProductivityView(meta);else if(V125_OPERATION_TAB==='productivity')body=await productivityView();else body=await standardsView();
    $('#operativoDynamicContent').innerHTML=`${tabs()}${body}`;bindCommon(meta);
  };

  const mode=$('#operPeriodMode');if(mode)mode.addEventListener('change',async()=>{if(MAIN==='operation'&&V125_OPERATION_TAB==='productivity'){OPER_PERIOD.type=mode.value;OPER_PERIOD.value='';await renderOperativoView(OP,true)}});
  console.info('[V125] Operación: Origen agrupado + Captura productividad + Productividad + Estándares.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v125_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v125-operation-tabs-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V125",
            })
        except Exception as exc:
            print(f"[V125] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V125_OPERATION_TABS = True
    print("[V125] Operación reestructurada en 4 pestañas; Origen agrupa Colgado + Doblado.", flush=True)
