"""V165 · refinamiento operativo/comercial solicitado 2026-09-17.

- Cambios y Muertos: sólo Centro Operativo, Conversión, Recuperación $,
  Productividad y Recorridos (+ administración). Vista vuelve a ofrecer
  Día/Semanal/Mensual/Anual siempre.
- Productividad: alerta colaboradores históricos sin registro en el periodo.
- Matriz: se integra al inicio de Recorridos, agrupada L-D y por hora completa.
- Operación: elimina C&M del resumen de Origen, corrige tabs duplicados.
- Comercial: filtro Estatus real, Marca usa columna MARCA antes de MARCA PRICE,
  iconos consistentes y subfiltros para Ubicación/80-20/Lentos/Sugerido 0-1.
- Ventas: la corrección de Request de V112 se activa desde server_entry.
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import date, datetime, timedelta
import math
import threading
import time

from fastapi import Request
from fastapi.responses import HTMLResponse

_STATUS_CTX = ContextVar("v165_commercial_status", default="Todos")


def install(m):
    if getattr(m, "_V165_REFINEMENT", False):
        return

    # Ya no existe como pestaña independiente: la matriz vive dentro de Recorridos.
    m.REPORT_TABS.pop("operations.collection", None)
    for key in ("operations.operation", "operations.day", "operations.week", "operations.month", "operations.score", "operations.alerts"):
        m.REPORT_TABS.pop(key, None)

    # -------- Marca y Estatus exactos desde el Excel de capacidades --------
    try:
        import commercial.parsers as cp
        original_read_capacity = m.read_capacity_file

        def read_capacity_file_v165(path):
            base = original_read_capacity(path)
            try:
                p = cp.Path(path)
                source = cp._fast_capacity_xlsx(p) if p.suffix.lower() == ".xlsx" else cp._read_sheet(p, 0)
                if source is None or source.empty or base is None or base.empty:
                    return base
                store = cp._series(source, ["TIENDA", "SUCURSAL", "TIENDA/SUCURSAL"]).map(cp.canon_store)
                model = cp._series(source, ["MODELO", "ID_ART", "ID ART", "ID/Modelo"]).astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
                article = cp._series(source, ["ID_ART", "ID ART", "ID", "CODIGO"]).astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
                model = model.where(~model.isin(["", "nan", "None"]), article)
                valid = store.ne("") & ~model.isin(["", "nan", "None"])
                exact_brand = cp._series(source, ["MARCA"], "Sin marca").astype(str).str.strip().loc[valid].reset_index(drop=True)
                exact_status = cp._series(source, ["ESTATUS"], "").astype(str).str.strip().loc[valid].reset_index(drop=True)
                if len(base) == len(exact_brand):
                    base = base.copy()
                    base["Marca"] = exact_brand
                    base["Estatus comercial"] = exact_status
            except Exception as exc:
                print(f"[V165] Marca/Estatus exactos: {type(exc).__name__}: {exc}", flush=True)
            return base

        cp.read_capacity_file = read_capacity_file_v165
        m.read_capacity_file = read_capacity_file_v165
    except Exception as exc:
        print(f"[V165] No fue posible envolver read_capacity_file: {type(exc).__name__}: {exc}", flush=True)

    # -------- Filtro Estatus real sin duplicar endpoints --------
    old_scope = getattr(m, "_capacity_scope_v45", None)
    if callable(old_scope):
        def scope_v165(frame, store="Compañía", section="Todas", catalog="Todos", add_area=False):
            work = old_scope(frame, store, section, catalog, add_area=add_area)
            status = str(_STATUS_CTX.get() or "Todos").strip()
            if status not in ("", "Todos", "Todas") and work is not None and not work.empty and "Estatus comercial" in work.columns:
                key = m.login_key(status)
                work = work[work["Estatus comercial"].fillna("").astype(str).map(m.login_key) == key].copy()
            return work
        m._capacity_scope_v45 = scope_v165

    @m.app.middleware("http")
    async def _v165_status_context(request, call_next):
        token = _STATUS_CTX.set(str(request.query_params.get("status") or "Todos"))
        try:
            return await call_next(request)
        finally:
            _STATUS_CTX.reset(token)

    @m.app.get("/api/commercial/statuses-v165")
    def statuses_v165(request: Request, week: str = ""):
        m.require_user(request)
        try:
            frame = m._capacity_frame_for_period(week)
            if frame is None or frame.empty or "Estatus comercial" not in frame.columns:
                return {"statuses": []}
            vals = sorted({str(x).strip() for x in frame["Estatus comercial"].dropna().tolist() if str(x).strip() and str(x).strip().lower() not in ("nan","none")})
            return {"statuses": vals}
        except Exception:
            return {"statuses": []}

    # -------- Colaboradores históricos sin productividad en el periodo --------
    def _bounds(ptype, value):
        ptype = str(ptype or "week").lower(); value = str(value or "").strip(); today=date.today()
        if ptype == "day":
            d=datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date(); return d,d
        if ptype == "week":
            if value and "-W" in value:
                y,w=value.split("-W",1); s=date.fromisocalendar(int(y),int(w),1)
            else:
                iso=today.isocalendar(); s=date.fromisocalendar(iso.year,iso.week,1)
            return s,s+timedelta(days=6)
        if ptype == "month":
            if value and len(value)>=7: y,mo=map(int,value[:7].split("-"))
            else: y,mo=today.year,today.month
            s=date(y,mo,1); n=date(y+(mo==12),1 if mo==12 else mo+1,1); return s,n-timedelta(days=1)
        y=int(value or today.year); return date(y,1,1),date(y,12,31)

    def _productive_row(r):
        act=m.normalize_col(r.get("activity") or r.get("activity_original") or "")
        reason=m.normalize_col(r.get("reason") or "")
        return ("acondicion" in act or "habilit" in act or "ubic" in act or "recoleccion" in act or "caja" in reason or "probador" in reason)

    @m.app.get("/api/operations/nonreporting-v165")
    def nonreporting_v165(request: Request, period_type: str="week", period_value: str="", store: str="Compañía"):
        actor=m.require_user(request); start,end=_bounds(period_type,period_value); selected=m.effective_store(actor,store)
        known={}; current=set()
        rows=list((m.load_ops() or {}).get("rows") or [])
        for r in rows:
            st=str(r.get("store") or "").strip(); name=str(r.get("name") or "").strip(); ds=str(r.get("date") or "")[:10]
            if not name or not ds or (selected!="Compañía" and st!=selected) or not _productive_row(r): continue
            try:d=date.fromisoformat(ds)
            except Exception:continue
            key=(m.login_key(name),st)
            if d < start: known[key]={"name":name,"store":st,"last_date":ds}
            if start <= d <= end: current.add(key)
        try:
            with m.db() as con:
                manual=[dict(x) for x in con.execute("SELECT date,store,employee_name,pieces FROM operation_productivity ORDER BY date").fetchall()]
            for r in manual:
                st=str(r.get("store") or "").strip(); name=str(r.get("employee_name") or "").strip(); ds=str(r.get("date") or "")[:10]
                if not name or not ds or (selected!="Compañía" and st!=selected): continue
                try:d=date.fromisoformat(ds)
                except Exception:continue
                key=(m.login_key(name),st)
                if d < start: known[key]={"name":name,"store":st,"last_date":ds}
                if start <= d <= end and float(r.get("pieces") or 0)>0: current.add(key)
        except Exception: pass
        missing=[v for k,v in known.items() if k not in current]
        missing.sort(key=lambda x:(x["store"],x["name"]))
        return {"count":len(missing),"rows":missing,"start":start.isoformat(),"end":end.isoformat(),"store":selected}

    # Reprocesa el último catálogo en segundo plano para que Marca/Estatus exactos
    # queden también en el cache persistente actual, sin bloquear el arranque.
    def _refresh_capacity_cache():
        time.sleep(8)
        try:
            entries=list((m.load_manifest() or {}).get("capacities") or [])
            entries=[dict(e) for e in entries if str(e.get("status") or "").lower()=="procesado"]
            if not entries:return
            latest=max(entries,key=lambda e:str(e.get("uploaded_at") or ""))
            path=m.resolve_entry_path(latest)
            df=m._prepare_capacity_frame(m.read_capacity_file(path))
            if df is None or df.empty:return
            cache_path=m._capacity_cache_path(latest["id"]); df.to_pickle(cache_path)
            m._CAPACITY_FRAME_CACHE.update({"path":str(path),"mtime":path.stat().st_mtime if path.exists() else None,"frame":df})
            m.update_entry("capacities",latest["id"],cache_file=str(cache_path.relative_to(m.DATA_ROOT)),rows=int(len(df)),status="Procesado")
            print(f"[V165] Catálogo actual reparado: Marca=MARCA, Estatus=ESTATUS, filas={len(df)}",flush=True)
        except Exception as exc:
            print(f"[V165] Reproceso catálogo: {type(exc).__name__}: {exc}",flush=True)
    threading.Thread(target=_refresh_capacity_cache,daemon=True,name="v165-capacity-refresh").start()

    css=r'''<style id="v165-refinement-css">
/* Cambios y Muertos: sólo las vistas reales solicitadas */
#operativoNav [data-opview="Operación"],#operativoNav [data-opview="Operación Diaria"],
#operativoNav [data-opview="Reporte Semanal"],#operativoNav [data-opview="Reporte Mensual"],
#operativoNav [data-opview="Score"],#operativoNav [data-opview="Alertas"],
#operativoNav [data-opview="Matriz de recolección"]{display:none!important}
body[data-v163-module="operativo"] #operativoNav:not(.hidden){grid-template-columns:repeat(5,minmax(0,1fr))!important}
.v165-alert-panel{background:#fff8db;border:1px solid #f0d77a;border-radius:12px;padding:11px;margin:9px 0;color:#704c00}.v165-alert-panel h3{margin:0 0 5px;font-size:12px;color:#8a5c00}.v165-alert-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.v165-alert-chip{background:#fff;border:1px solid #efd887;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:800}
.v165-hour-grid{overflow:auto;border:1px solid #d8e4f0;border-radius:10px}.v165-hour-grid table{border-collapse:collapse;width:100%;min-width:900px;font-size:8px}.v165-hour-grid th{position:sticky;top:0;background:#173f78;color:#fff;padding:8px}.v165-hour-grid td{padding:7px;border-bottom:1px solid #e6edf5;border-right:1px solid #edf2f7;text-align:center}.v165-hour-grid td:first-child{font-weight:900;text-align:left;position:sticky;left:0;background:#fff}.v165-hour-cell b{display:block;color:#103f7d}.v165-hour-cell small{display:block;color:#748399;font-size:6.5px;margin-top:2px}.v165-rec-block{margin:0 0 12px}.v165-rec-head{display:flex;justify-content:space-between;align-items:end;margin:4px 0 8px}.v165-rec-head h2{font-size:17px;margin:0;color:#103f7d}.v165-rec-head p{font-size:8px;color:#71839a;margin:3px 0 0}.v165-mini-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-bottom:8px}.v165-mini-kpi{background:#fff;border:1px solid #d8e4f0;border-radius:12px;padding:10px;border-left:4px solid var(--c,#176fe8)}.v165-mini-kpi small{font-size:7px;color:#667a92;font-weight:900;text-transform:uppercase}.v165-mini-kpi b{display:block;font-size:19px;color:#103f7d;margin-top:5px}
.v165-commercial-status{position:relative}.v165-commercial-status select{padding-left:36px!important}.v165-subfilters{display:flex;gap:6px;flex-wrap:wrap;background:#fff;border:1px solid #d6e3f1;border-radius:12px;padding:6px;margin:8px 0}.v165-subfilters button{border:1px solid #d8e4f0;background:#fff;color:#214f82;border-radius:9px;padding:8px 11px;font-size:8px;font-weight:900;cursor:pointer}.v165-subfilters button:hover,.v165-subfilters button.active{background:#176fe8;color:#fff;border-color:#176fe8}
/* Iconos comerciales más cercanos al boceto */
body[data-v163-module="analysis"] #analysisNav .v164-tab-icon{width:16px;height:16px}
@media(max-width:900px){.v165-mini-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v165-subfilters{overflow-x:auto;flex-wrap:nowrap}.v165-subfilters button{white-space:nowrap}}
</style>'''

    js=r'''<script id="v165-refinement-js">
(function(){
 if(window.__V165_REFINEMENT)return;window.__V165_REFINEMENT=true;
 const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])),nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0});
 const ico={status:'<svg viewBox="0 0 24 24"><path d="M4 5h16M4 12h10M4 19h7"/><circle cx="18" cy="12" r="2"/></svg>'};
 let STATUS=localStorage.getItem('v165CommercialStatus')||'Todos';

 function cleanCyMNav(){
   const remove=['Operación','Día','Semanal','Mensual','Score','Alertas','Matriz de recolección'];
   $$('#operativoNav [data-opview]').forEach(b=>{const t=(b.textContent||'').trim();if(remove.includes(t)||remove.some(x=>t===x))b.style.display='none'});
 }
 function fixViewSelect(){
   if((document.body.dataset.v163Module||'')!=='operativo')return;
   const src=document.getElementById('operPeriodMode');const visible=$('#v161FilterGrid [data-v164-source="operPeriodMode"] select');
   const options=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
   [src,visible].filter(Boolean).forEach(sel=>{const old=sel.value||window.OPER_PERIOD?.type||'week';sel.innerHTML=options.map(o=>`<option value="${o[0]}">${o[1]}</option>`).join('');sel.value=options.some(o=>o[0]===old)?old:'week'});
   if(visible&&!visible.dataset.v165){visible.dataset.v165='1';visible.addEventListener('change',()=>{if(src){src.value=visible.value;src.dispatchEvent(new Event('change',{bubbles:true}))}if(window.OPER_PERIOD){window.OPER_PERIOD.type=visible.value;window.OPER_PERIOD.value=''}setTimeout(()=>window.renderOperativoView?.(window.OP_VIEW||'Centro Ejecutivo',true),60)})}
 }
 function normalizeOperationTabs(){
   if((document.body.dataset.v163Module||'')!=='operation')return;
   const root=$('.v125-tabs');if(!root)return;
   const map=new Map();$$('.v125-tabs .v125-tab').forEach(b=>{const t=(b.textContent||'').trim();if(map.has(t))b.remove();else map.set(t,b)});
   const allowed=[['Resumen','summary'],['Captura diaria','daily'],['Cargar productividad','capture'],['Productividad','productivity'],['Estándares','standards']];
   [...root.children].forEach(b=>{if(!allowed.some(x=>x[0]===(b.textContent||'').trim()))b.remove()});
   allowed.forEach(([label,key])=>{let b=[...root.children].find(x=>(x.textContent||'').trim()===label);if(!b){b=document.createElement('button');b.className='v125-tab';b.textContent=label;root.appendChild(b)}b.onclick=async e=>{e.preventDefault();window.V149_OPERATION_TAB=key;window.V125_OPERATION_TAB=key;if(window.OPER_PERIOD&&key!=='productivity'){window.OPER_PERIOD.type='day';window.OPER_PERIOD.value=''}await window.renderOperativoView?.('Operación',true);setTimeout(normalizeOperationTabs,80)}});
 }
 function focusOriginOnly(){
   if((document.body.dataset.v163Module||'')!=='operation')return;
   $$('h3').forEach(h=>{if((h.textContent||'').includes('Origen vs Cambios y Muertos'))h.textContent='Origen · Mercancía liberada'});
   $$('table tbody tr').forEach(tr=>{const first=(tr.cells?.[0]?.textContent||'').trim();if(first==='Cambios y Muertos')tr.remove();if(first==='Origen')tr.cells[0].textContent='Mercancía de origen'});
 }
 async function addNonReporting(){
   if((document.body.dataset.v163Module||'')!=='operativo')return;
   const active=($('#operativoNav .active')?.textContent||'').trim();if(active!=='Productividad')return;
   const cont=$('#operativoDynamicContent');if(!cont||cont.querySelector('#v165NonReporting'))return;
   const type=$('#operPeriodMode')?.value||window.OPER_PERIOD?.type||'week',value=$('#operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',store=$('#operStoreSelect')?.value||'Compañía';
   try{const d=await api(`/api/operations/nonreporting-v165?period_type=${encodeURIComponent(type)}&period_value=${encodeURIComponent(value)}&store=${encodeURIComponent(store)}`);if(!d.count)return;const box=document.createElement('div');box.id='v165NonReporting';box.className='v165-alert-panel';box.innerHTML=`<h3>⚠ Colaboradores sin productividad registrada · ${d.count}</h3><div>Ya habían reportado productividad anteriormente, pero no tienen registro en el periodo consultado.</div><div class="v165-alert-chips">${(d.rows||[]).slice(0,30).map(r=>`<span class="v165-alert-chip">${esc(r.name)} · ${esc(r.store)}</span>`).join('')}</div>`;const ranking=[...cont.querySelectorAll('h2,h3,.title')].find(x=>(x.textContent||'').includes('Ranking completo'));(ranking?.parentElement||cont).insertBefore(box,ranking||cont.firstChild)}catch(e){console.warn('[V165] alerta productividad',e)}
 }
 function hourLabel(h){const d=new Date(2000,0,1,h,0);return d.toLocaleTimeString('es-MX',{hour:'numeric',minute:'2-digit',hour12:true})}
 function groupHourly(matrix){
   const days=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'],map={},hours=[];
   (matrix||[]).forEach(r=>{const mt=String(r.schedule||'').match(/(\d{1,2}):/);if(!mt)return;const h=Number(mt[1]);hours.push(h);const key=r.day+'|'+h,g=map[key]||(map[key]={muertos:0,cajas:0,probador:0,total:0});['muertos','cajas','probador','total'].forEach(k=>g[k]+=Number(r[k]||0))});
   const min=hours.length?Math.min(...hours):9,max=hours.length?Math.max(...hours):19,cols=[];for(let h=min;h<=max;h++)cols.push(h);return{days,map,cols};
 }
 function hourGrid(data){const g=groupHourly(data.matrix||[]);return `<div class="v165-hour-grid"><table><thead><tr><th>Día</th>${g.cols.map(h=>`<th>${hourLabel(h)}</th>`).join('')}</tr></thead><tbody>${g.days.map(day=>`<tr><td>${day}</td>${g.cols.map(h=>{const x=g.map[day+'|'+h];return `<td>${x?`<span class="v165-hour-cell"><b>${nf(x.total)}</b><small>M ${nf(x.muertos)} · C ${nf(x.cajas)} · P ${nf(x.probador)}</small></span>`:'—'}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`}
 async function collectionBlock(){
   const type=$('#operPeriodMode')?.value||window.OPER_PERIOD?.type||'week',value=$('#operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',store=$('#operStoreSelect')?.value||'Compañía',area=$('#operAreaSelect')?.value||'Todas',activity=$('#operActivitySelect')?.value||'Todas';
   const q=new URLSearchParams({period_type:type,period_value:value,store,area,activity});const d=await api('/api/operations/collection-matrix-v164?'+q);const s=d.summary||{},src=d.source_totals||{},total=Number(src.muertos||0)+Number(src.cajas||0)+Number(src.probador||0);
   return `<section id="v165CollectionIntegrated" class="v165-rec-block"><div class="v165-rec-head"><div><h2>Matriz de recolección de mercancía</h2><p>Agrupada de lunes a domingo y por hora completa · Muertos, Cajas y Probador.</p></div></div><div class="v165-mini-kpis"><div class="v165-mini-kpi"><small>Piezas recolectadas</small><b>${nf(s.pieces)}</b></div><div class="v165-mini-kpi" style="--c:#e4007f"><small>Muertos</small><b>${nf(src.muertos)}</b></div><div class="v165-mini-kpi" style="--c:#7047c8"><small>Cajas</small><b>${nf(src.cajas)}</b></div><div class="v165-mini-kpi" style="--c:#f59e0b"><small>Probador</small><b>${nf(src.probador)}</b></div></div><div class="v164-panel"><h3>Día × hora</h3><div class="sub">Desde la primera hora registrada hasta la última, consolidado en horas completas.</div>${hourGrid(d)}</div><div class="v164-matrix-grid"><div class="v164-panel"><h3>Tendencia del periodo</h3>${typeof trendHtml==='function'?trendHtml(d.daily||[]):''}</div><div class="v164-panel"><h3>Participación</h3><div class="v164-donut-wrap"><div class="v164-donut" style="background:${typeof pieStyle==='function'?pieStyle(src):'conic-gradient(#1769e8 0 100%)'}"><div class="v164-donut-center"><b>${nf(total)}</b><span>piezas</span></div></div></div></div></div></section>`;
 }
 async function integrateCollection(){
   if((document.body.dataset.v163Module||'')!=='operativo'||($('#operativoNav .active')?.textContent||'').trim()!=='Recorridos')return;const c=$('#operativoDynamicContent');if(!c||c.querySelector('#v165CollectionIntegrated'))return;try{c.insertAdjacentHTML('afterbegin',await collectionBlock())}catch(e){console.warn('[V165] matriz integrada',e)}
 }
 async function ensureStatusFilter(){
   if((document.body.dataset.v163Module||'')!=='analysis')return;const grid=$('#v161FilterGrid'),apply=grid?.querySelector('.v161-apply');if(!grid||!apply)return;let wrap=$('#v165StatusWrap');if(!wrap){wrap=document.createElement('div');wrap.id='v165StatusWrap';wrap.className='v161-field v165-commercial-status';wrap.innerHTML=`<label>Estatus</label><select id="v165Status"><option>Todos</option></select><span class="v164-filter-icon">${ico.status}</span>`;grid.insertBefore(wrap,apply);$('#v165Status').onchange=e=>{STATUS=e.target.value;localStorage.setItem('v165CommercialStatus',STATUS)}}
   const sel=$('#v165Status');if(sel.dataset.loaded===$('#week')?.value)return;try{const d=await api('/api/commercial/statuses-v165?week='+encodeURIComponent($('#week')?.value||''));const old=STATUS;sel.innerHTML='<option>Todos</option>'+(d.statuses||[]).map(x=>`<option>${esc(x)}</option>`).join('');sel.value=[...sel.options].some(o=>o.value===old)?old:'Todos';STATUS=sel.value;sel.dataset.loaded=$('#week')?.value||''}catch(e){}
 }
 function apiStatus(){if(typeof window.api!=='function'||window.api.__v165)return;const old=window.api;const wrapped=function(url,opt){try{const u=String(url||'');if((document.body.dataset.v163Module||'')==='analysis'&&/^\/api\/(dashboard|commercial-detail|commercial-accordion|model-ranking)/.test(u)&&STATUS&&STATUS!=='Todos'){const sep=u.includes('?')?'&':'?';url=u+sep+'status='+encodeURIComponent(STATUS)}}catch(_){}return old(url,opt)};wrapped.__v165=true;window.api=wrapped}
 function commercialSubfilters(){
   if((document.body.dataset.v163Module||'')!=='analysis'||($('#analysisNav .active')?.textContent||'').trim()!=='Macro compañía')return;if($('#v165MacroSubfilters'))return;const cards=$('.kpis')||$('.report-kpis');if(!cards)return;const bar=document.createElement('div');bar.id='v165MacroSubfilters';bar.className='v165-subfilters';const defs=['Ubicación','Macro 80/20','Modelos 80/20','Modelos lentos','Sugerido 0 a 1'];defs.forEach(label=>{const b=document.createElement('button');b.textContent=label;b.onclick=()=>{const nodes=[...document.querySelectorAll('h2,h3,.title,.acc>button')];const q=label.toLowerCase().replace('modelos ','').replace('macro ','');let target=nodes.find(n=>(n.textContent||'').toLowerCase().includes(q))||nodes.find(n=>(n.textContent||'').toLowerCase().includes(label.toLowerCase().split(' ')[0]));if(target?.closest('.acc'))target.closest('.acc').classList.add('open');target?.scrollIntoView({behavior:'smooth',block:'start'});$$('#v165MacroSubfilters button').forEach(x=>x.classList.toggle('active',x===b))};bar.appendChild(b)});cards.insertAdjacentElement('afterend',bar)
 }
 function fixCommercialIcons(){
   const iconMap={'Macro compañía':'▦','Acordeón comercial':'☷','Tiendas':'▣','Sección / Rubro':'▦','Ubicación / Área':'⌖','Más opciones':'☰','Carga de datos':'⇧'};$$('#analysisNav [data-sub]').forEach(b=>{const t=(b.textContent||'').replace(/[▦☷▣⌖☰⇧]/g,'').trim();const i=b.querySelector('.v164-tab-icon');if(i&&iconMap[t])i.innerHTML=`<span style="font-size:16px;line-height:1">${iconMap[t]}</span>`})
 }
 function schedule(){[20,120,350,800].forEach(ms=>setTimeout(()=>{cleanCyMNav();fixViewSelect();normalizeOperationTabs();focusOriginOnly();ensureStatusFilter();commercialSubfilters();fixCommercialIcons();addNonReporting();integrateCollection()},ms))}
 const prevRender=window.renderOperativoView;if(typeof prevRender==='function'){window.renderOperativoView=async function(name,force=false){const out=await prevRender.apply(this,arguments);setTimeout(()=>{normalizeOperationTabs();focusOriginOnly();addNonReporting();if(name==='Recorridos')integrateCollection()},80);return out}}
 apiStatus();document.addEventListener('click',e=>{if(e.target.closest?.('[data-main],#operativoNav,#analysisNav,.v125-tabs,.v161-apply'))schedule()},true);document.addEventListener('change',e=>{if(e.target?.matches?.('select,input'))schedule()},true);const mo=new MutationObserver(()=>{clearTimeout(window.__v165mo);window.__v165mo=setTimeout(schedule,80)});if(document.body)mo.observe(document.body,{childList:true,subtree:true});if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();console.info('[V165] refinamiento operativo/comercial activo');
})();
</script>'''

    @m.app.middleware("http")
    async def _v165_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v165-refinement-css" not in html:html=html.replace("</head>",css+"</head>",1)
            if "v165-refinement-js" not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V165"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V165] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V165_REFINEMENT=True
    print("[V165] Filtros, Recorridos, Operación y Comercial refinados.",flush=True)
