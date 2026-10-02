"""V239 · Cierre funcional de navegación, Centro Operativo y Operación.

- Día/Semanal/Mensual dejan de ser pestañas independientes: viven dentro de Centro Operativo.
- Centro Operativo conserva Día / Semanal / Mensual / Anual sin regresar a Mensual.
- Elimina la gráfica horizontal "Devolución y recuperación" de todas las vistas.
- Cargar productividad usa el flujo Origen/Resurtido V222 con actividades y piezas por área.
- Estándares: Colgado/Lencería -> estándar Colgado; Doblado/Jeans -> estándar Doblado.
- Administración de pestañas compacta por reporte, con ocultar y eliminar/restaurar.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V239_FUNCTIONAL_CLOSE", False):
        return

    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS report_tab_deleted_v239(
            tab_key TEXT PRIMARY KEY,
            label TEXT NOT NULL DEFAULT '',
            report_group TEXT NOT NULL DEFAULT '',
            deleted_at TEXT NOT NULL,
            deleted_by TEXT NOT NULL DEFAULT ''
        )""")

    def _owner(request):
        actor = m.require_user(request)
        role = str(actor.get("real_role") or actor.get("role") or "").strip().lower()
        if role != "superadmin":
            raise m.HTTPException(403, "Sólo Super Administrador puede eliminar o restaurar pestañas.")
        return actor

    @m.app.get("/api/settings/report-tabs-v239/deleted")
    def deleted_tabs_v239(request: m.Request):
        m.require_user(request)
        with m.db() as con:
            rows = con.execute(
                "SELECT tab_key,label,report_group,deleted_at,deleted_by "
                "FROM report_tab_deleted_v239 ORDER BY report_group,label,tab_key"
            ).fetchall()
        return {"items": [dict(r) for r in rows]}

    @m.app.post("/api/settings/report-tabs-v239/delete")
    def delete_tab_v239(request: m.Request, payload: dict):
        actor = _owner(request)
        key = str((payload or {}).get("key") or "").strip()
        label = str((payload or {}).get("label") or key).strip()
        group = str((payload or {}).get("group") or "").strip()
        if not key:
            raise m.HTTPException(400, "Pestaña inválida")
        with m.db() as con:
            con.execute(
                "INSERT INTO report_tab_deleted_v239(tab_key,label,report_group,deleted_at,deleted_by) "
                "VALUES(?,?,?,?,?) ON CONFLICT(tab_key) DO UPDATE SET "
                "label=excluded.label,report_group=excluded.report_group,"
                "deleted_at=excluded.deleted_at,deleted_by=excluded.deleted_by",
                (
                    key,
                    label,
                    group,
                    datetime.now(MX).isoformat(timespec="seconds"),
                    str(actor.get("username") or ""),
                ),
            )
        return {"ok": True, "key": key}

    @m.app.post("/api/settings/report-tabs-v239/restore")
    def restore_tab_v239(request: m.Request, payload: dict):
        _owner(request)
        key = str((payload or {}).get("key") or "").strip()
        if not key:
            raise m.HTTPException(400, "Pestaña inválida")
        with m.db() as con:
            con.execute("DELETE FROM report_tab_deleted_v239 WHERE tab_key=?", (key,))
        return {"ok": True, "key": key}

    css = r'''<style id="v239-functional-close-css">
/* Día/Semanal/Mensual ya no son pestañas: son vistas de Centro Operativo. */
#operativoNav [data-opview="Operación Diaria"],
#operativoNav [data-opview="Reporte Semanal"],
#operativoNav [data-opview="Reporte Mensual"],
#operativoNav [data-tab-key="operations.day"],
#operativoNav [data-tab-key="operations.week"],
#operativoNav [data-tab-key="operations.month"]{
  display:none!important;
}

/* Gráfica eliminada en todas las vistas. */
.recovery-svg,
.chart-box:has(> .recovery-svg){
  display:none!important;
}

/* Administración compacta por tipo de reporte. */
#page-users.v219-users #tabVisibilityPanel{
  padding:10px!important;
}
#page-users.v219-users .v219-tabs-head{
  margin-bottom:7px!important;
}
#page-users.v219-users .v219-tabs-head-icon{
  width:32px!important;height:32px!important;min-width:32px!important;border-radius:9px!important;
}
#page-users.v219-users .v219-tabs-head-icon svg{width:17px!important;height:17px!important}
#page-users.v219-users .v219-tabs-head h2{font-size:14px!important}
#page-users.v219-users .v219-tabs-head p{font-size:8.5px!important;margin-top:2px!important}

#page-users.v219-users #tabVisibilityOptions.v222-grouped{
  grid-template-columns:repeat(3,minmax(0,1fr))!important;
  gap:7px!important;
}
#page-users.v219-users .v222-vis-group{
  padding:6px!important;border-radius:11px!important;
}
#page-users.v219-users .v222-vis-title{
  font-size:10px!important;margin:0!important;padding:3px 3px 6px!important;
}
#page-users.v219-users .v222-vis-group label.field{
  min-height:34px!important;
  padding:4px 2px!important;
  gap:6px!important;
}
#page-users.v219-users .v219-tab-icon{
  width:24px!important;height:24px!important;min-width:24px!important;border-radius:7px!important;
}
#page-users.v219-users .v219-tab-icon svg{width:13px!important;height:13px!important}
#page-users.v219-users .v222-vis-group label.field>span:not(.v219-tab-icon){
  font-size:8.5px!important;line-height:1.08!important;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]{
  flex:0 0 30px!important;width:30px!important;min-width:30px!important;height:17px!important;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]::after{
  top:2px!important;left:2px!important;width:13px!important;height:13px!important;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]:checked::after{
  transform:translateX(13px)!important;
}
.v239-tab-delete{
  order:4;
  width:25px;height:25px;min-width:25px;
  border:1px solid #f3c7c7;border-radius:7px;
  background:#fff4f4;color:#b42318;
  display:grid;place-items:center;
  padding:0;font-size:13px;font-weight:900;cursor:pointer;
}
.v239-tab-delete:hover{background:#ffe8e8}
.v239-deleted{
  grid-column:1/-1;
  margin-top:2px;padding:7px;
  border:1px dashed #cfdbea;border-radius:10px;background:#fbfdff;
}
.v239-deleted-title{font-size:9px;font-weight:900;color:#375b80;margin-bottom:5px}
.v239-deleted-list{display:flex;flex-wrap:wrap;gap:5px}
.v239-restore{
  border:1px solid #cfdbea;border-radius:999px;background:#fff;color:#194b7c;
  padding:4px 7px;font-size:7.8px;font-weight:800;cursor:pointer;
}
#page-users.v219-users #saveTabVisibility{
  min-height:34px!important;margin-top:7px!important;font-size:9px!important;
}

/* Cargar productividad: selección tipo botón + tabla de áreas. */
body[data-v163-module="operation"] #v222CaptureCard .v222-choice button{
  min-height:38px!important;font-size:10px!important;
}
body[data-v163-module="operation"] #v222CaptureCard .v222-area-table th,
body[data-v163-module="operation"] #v222CaptureCard .v222-area-table td{
  font-size:10px!important;
}

/* Tablet/móvil: panel de pestañas por reporte apilado. */
@media(max-width:900px){
  #page-users.v219-users #tabVisibilityOptions.v222-grouped{
    grid-template-columns:1fr!important;
  }
}
</style>'''

    js = r'''<script id="v239-functional-close-js">
(function(){
  if(window.__V239_FUNCTIONAL_CLOSE)return;
  window.__V239_FUNCTIONAL_CLOSE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const CENTER='Centro Ejecutivo';
  const MODES=[
    ['day','Día','Operación Diaria'],
    ['week','Semanal','Reporte Semanal'],
    ['month','Mensual','Reporte Mensual'],
    ['year','Anual','Centro Ejecutivo']
  ];
  const MODE_LABEL={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
  const MODE_SUB={
    day:'Consulta por fecha · ingresos, pendientes y avance por tienda',
    week:'Semana ISO · operación, conversión, recuperación, productividad y recorridos',
    month:'Mes seleccionado · operación y desempeño consolidado',
    year:'Acumulado anual · operación, conversión, recuperación, productividad y recorridos'
  };
  const LEGACY_KEYS=new Set(['operations.day','operations.week','operations.month']);
  let DELETED=new Map();
  let centerRendering=false;
  let centerSeq=0;
  let centerMode='';
  const modeValues={};

  function norm(s){return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase()}
  function isLegacyRow(input){
    if(!input)return false;
    const key=String(input.dataset.tabSetting||'');
    const label=norm(input.closest('label')?.textContent||'');
    return LEGACY_KEYS.has(key)||label==='dia'||label==='semanal'||label==='mensual';
  }
  function groupForKey(key){
    key=String(key||'');
    if(key.startsWith('operations.'))return 'Cambios y Muertos';
    if(key.startsWith('operation.'))return 'Operación';
    if(key.startsWith('commercial.'))return 'Análisis Comercial';
    return 'Otro';
  }

  function removeLegacyCenterTabs(){
    qa('#operativoNav>button').forEach(btn=>{
      const key=String(btn.dataset.tabKey||'');
      const op=String(btn.dataset.opview||'');
      const txt=norm(btn.dataset.v232Original||btn.dataset.rtLabel||btn.title||btn.textContent);
      if(
        LEGACY_KEYS.has(key)||
        ['Operación Diaria','Reporte Semanal','Reporte Mensual'].includes(op)||
        ['dia','semanal','mensual'].includes(txt)
      ) btn.remove();
    });
  }

  function applyDeleted(){
    removeLegacyCenterTabs();
    DELETED.forEach((_v,key)=>{
      qa('[data-tab-key="'+CSS.escape(key)+'"]').forEach(el=>{
        el.hidden=true;
        el.classList.add('hidden');
        el.setAttribute('aria-hidden','true');
        el.style.setProperty('display','none','important');
      });
    });
  }

  async function fetchDeleted(){
    try{
      const r=await api('/api/settings/report-tabs-v239/deleted',{timeoutMs:15000});
      DELETED=new Map((r.items||[]).map(x=>[String(x.tab_key),x]));
      applyDeleted();
      decorateVisibilityAdmin();
    }catch(e){console.warn('[V239] eliminadas',e)}
  }

  function deletedFooter(box){
    let footer=q(':scope>.v239-deleted',box);
    if(!DELETED.size){
      footer?.remove();
      return;
    }
    if(!footer){
      footer=document.createElement('div');
      footer.className='v239-deleted';
      box.appendChild(footer);
    }
    footer.innerHTML='<div class="v239-deleted-title">Pestañas eliminadas · puedes restaurarlas</div><div class="v239-deleted-list">'+
      [...DELETED.entries()].map(([key,item])=>
        '<button type="button" class="v239-restore" data-v239-restore="'+key.replace(/"/g,'&quot;')+'">Restaurar · '+String(item.label||key).replace(/</g,'&lt;')+'</button>'
      ).join('')+'</div>';
    qa('[data-v239-restore]',footer).forEach(btn=>btn.onclick=async()=>{
      const key=btn.dataset.v239Restore;
      btn.disabled=true;
      try{
        await api('/api/settings/report-tabs-v239/restore',{
          method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})
        });
        DELETED.delete(key);
        if(typeof loadTabVisibility==='function')await loadTabVisibility();
        setTimeout(()=>{decorateVisibilityAdmin();if(typeof applyTabVisibility==='function')applyTabVisibility();},60);
      }catch(e){alert('No fue posible restaurar: '+(e.message||e));btn.disabled=false}
    });
  }

  function decorateVisibilityAdmin(){
    const box=q('#tabVisibilityOptions');
    if(!box)return;

    qa('input[data-tab-setting]',box).forEach(input=>{
      const row=input.closest('label.field')||input.closest('label');
      if(!row)return;
      const key=String(input.dataset.tabSetting||'');
      if(isLegacyRow(input)||DELETED.has(key)){
        row.remove();
        return;
      }
      if(!q('.v239-tab-delete',row)){
        const del=document.createElement('button');
        del.type='button';del.className='v239-tab-delete';del.title='Eliminar pestaña';del.setAttribute('aria-label','Eliminar pestaña');del.textContent='×';
        del.dataset.v239Delete=key;
        del.onclick=async e=>{
          e.preventDefault();e.stopPropagation();
          const label=String(row.querySelector('span:not(.v219-tab-icon)')?.textContent||key).trim();
          if(!confirm('¿Eliminar la pestaña “'+label+'”? Dejará de aparecer en el reporte y en esta lista.'))return;
          del.disabled=true;
          try{
            await api('/api/settings/report-tabs-v239/delete',{
              method:'POST',headers:{'Content-Type':'application/json'},
              body:JSON.stringify({key,label,group:groupForKey(key)})
            });
            DELETED.set(key,{tab_key:key,label,report_group:groupForKey(key)});
            row.remove();applyDeleted();deletedFooter(box);
            document.dispatchEvent(new CustomEvent('report-tabs-visibility-changed'));
          }catch(err){alert('No fue posible eliminar: '+(err.message||err));del.disabled=false}
        };
        row.appendChild(del);
      }
    });

    // Mantener únicamente los tres grupos de reporte y eliminar grupos vacíos.
    qa('.v222-vis-group',box).forEach(section=>{
      const title=norm(q('.v222-vis-title',section)?.textContent||'');
      if(title.includes('cambios')) q('.v222-vis-title',section).textContent='Cambios y Muertos';
      else if(title==='operacion') q('.v222-vis-title',section).textContent='Operación';
      else if(title.includes('analisis')) q('.v222-vis-title',section).textContent='Análisis Comercial';
      if(!q('input[data-tab-setting]',section))section.remove();
    });
    deletedFooter(box);
  }

  // Reaplicar eliminadas después de cualquier guardado de visibilidad.
  const baseApply=window.applyTabVisibility;
  if(typeof baseApply==='function'){
    window.applyTabVisibility=function(){
      const out=baseApply.apply(this,arguments);
      setTimeout(()=>{applyDeleted();decorateVisibilityAdmin();},0);
      return out;
    };
  }

  /* ---------- Centro Operativo: vista persistente ---------- */
  function yearsFrom(meta){
    return Array.from(new Set([...(meta?.available_dates||[]),...(meta?.available_months||[])]
      .map(v=>String(v||'').slice(0,4)).filter(v=>/^\d{4}$/.test(v)))).sort();
  }
  function listFor(mode,meta){
    if(mode==='day')return [...(meta?.available_dates||[])];
    if(mode==='week')return [...(meta?.available_weeks||[])];
    if(mode==='month')return [...(meta?.available_months||[])];
    return yearsFrom(meta||{});
  }
  function currentSavedMode(){
    const dom=q('#operPeriodMode')?.value;
    if(MODES.some(x=>x[0]===dom))return dom;
    if(MODES.some(x=>x[0]===centerMode))return centerMode;
    try{
      const s=localStorage.getItem('operacionesRopa.centerMode');
      if(MODES.some(x=>x[0]===s))return s;
    }catch(_e){}
    return 'month';
  }
  function setMode(mode){
    centerMode=MODES.some(x=>x[0]===mode)?mode:'month';
    try{localStorage.setItem('operacionesRopa.centerMode',centerMode)}catch(_e){}
    try{OPER_PERIOD.type=centerMode}catch(_e){}
  }
  function prepareCenterControls(mode,meta,forceLatest=false){
    const bar=q('#operativoPeriodBar'),wrap=q('#operPeriodModeWrap'),modeSel=q('#operPeriodMode'),sel=q('#operPeriodSelect'),lab=q('#operPeriodLabel');
    if(!bar||!wrap||!modeSel||!sel||!lab)return'';
    bar.classList.remove('hidden');bar.style.removeProperty('display');
    wrap.classList.remove('hidden');wrap.style.removeProperty('display');
    const sw=q('#operStartWrap'),ew=q('#operEndWrap');sw?.classList.add('hidden');ew?.classList.add('hidden');
    modeSel.innerHTML=MODES.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    modeSel.value=mode;
    const list=listFor(mode,meta).filter(Boolean);
    const before=forceLatest?'':String(modeValues[mode]||((OPER_PERIOD?.type===mode&&OPER_PERIOD?.value)||'')||'');
    const value=(before&&list.includes(before))?before:(list.at(-1)||'');
    lab.textContent=mode==='day'?'Fecha':mode==='week'?'Semana ISO':mode==='month'?'Mes':'Año';
    sel.innerHTML=list.map(v=>'<option value="'+v+'">'+v+'</option>').join('');
    if(value){
      sel.value=value;modeValues[mode]=value;
      try{OPER_PERIOD.type=mode;OPER_PERIOD.value=value}catch(_e){}
    }
    return value;
  }
  function keepCenterActive(mode){
    const center=q('#operativoNav [data-opview="Centro Ejecutivo"]');
    qa('#operativoNav>button').forEach(btn=>{
      const on=btn===center;
      btn.classList.toggle('active',on);
      if(on)btn.setAttribute('aria-selected','true');else btn.setAttribute('aria-selected','false');
    });
    try{OP_VIEW=CENTER}catch(_e){}
    const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub');
    if(title)title.textContent='Centro Operativo · '+MODE_LABEL[mode];
    if(sub){
      const existing=String(sub.textContent||'');
      const kpi=existing.match(/KPIs:\s*\d+\s+tiendas Proyecto/i)?.[0];
      sub.textContent=MODE_SUB[mode]+(kpi?' · '+kpi:'');
    }
    // El renderer específico puede ocultar el selector de vista: volver a mostrarlo.
    q('#operPeriodModeWrap')?.classList.remove('hidden');
    if(q('#operPeriodModeWrap'))q('#operPeriodModeWrap').style.removeProperty('display');
    const ms=q('#operPeriodMode');if(ms)ms.value=mode;
  }

  const baseRender=window.renderOperativoView;

  async function renderAnnual(meta,seq){
    const value=prepareCenterControls('year',meta,false);
    const host=q('#operativoDynamicContent');
    const dyn=q('#operativoDynamic'),centro=q('#operativoCentro');
    centro?.classList.add('hidden');dyn?.classList.remove('hidden');
    keepCenterActive('year');
    if(host)host.innerHTML='<div class="infoempty">Cargando reporte anual…</div>';
    const store=q('#operStoreSelect')?.value||'Compañía',area=q('#operAreaSelect')?.value||'',activity=q('#operActivitySelect')?.value||'';
    try{
      const d=await api('/api/operations/year?year='+encodeURIComponent(value)+'&store='+encodeURIComponent(store)+'&area='+encodeURIComponent(area)+'&activity='+encodeURIComponent(activity)+'&compact=true&project_only=false',{timeoutMs:180000});
      if(seq!==centerSeq)return;
      const mt=d.metrics||{},rec=d.recovery_by_store||[],stores=d.stores||[];
      const projects=typeof orderByConversion==='function'?orderByConversion(stores.filter(x=>x.is_project),rec):stores.filter(x=>x.is_project);
      let out=typeof monthlyCrossTable==='function'?monthlyCrossTable(mt):'';
      if(typeof recoveryTable==='function')out+='<div class="title">Recuperación por tienda</div>'+recoveryTable(rec);
      if(typeof operationalDetailTable==='function')out+='<div class="title">Detalle operativo · tiendas del proyecto</div>'+(projects.length?operationalDetailTable(projects,rec):'<div class="infoempty">No hay tiendas guardadas como Proyecto.</div>');
      if(projects.length&&typeof opsComboSvg==='function')out+=opsComboSvg(projects,value,store==='Compañía'?'Todas las tiendas':store,rec);
      if(typeof reportDownloadBar==='function')out+=reportDownloadBar(CENTER);
      if(host)host.innerHTML=out;
      keepCenterActive('year');
      prepareCenterControls('year',meta,false);
    }catch(e){
      if(seq!==centerSeq)return;
      if(host)host.innerHTML='<div class="infoempty">Error al cargar el reporte anual: '+String(e?.message||e)+'</div>';
    }
  }

  async function renderCenterV239(mode=currentSavedMode(),forceLatest=false){
    if(centerRendering)return;
    centerRendering=true;
    const seq=++centerSeq;
    try{
      setMode(mode);
      let meta=window.OPSDATA||null;
      if(!meta&&typeof refreshOperativoMeta==='function'){
        try{meta=await refreshOperativoMeta()}catch(_e){meta=window.OPSDATA||{}}
      }
      meta=meta||window.OPSDATA||{};
      const value=prepareCenterControls(mode,meta,forceLatest);
      modeValues[mode]=value;
      if(mode==='year'){
        await renderAnnual(meta,seq);
        return;
      }
      const target=MODES.find(x=>x[0]===mode)?.[2]||'Reporte Mensual';
      try{OPER_PERIOD.type=mode;OPER_PERIOD.value=value}catch(_e){}
      if(typeof baseRender==='function')await baseRender(target,true);
      if(seq!==centerSeq)return;
      // El renderer legado mantiene la vista específica pedida; sólo consolidamos la cabecera como Centro Operativo.
      keepCenterActive(mode);
      prepareCenterControls(mode,meta,false);
      removeRecoveryCharts();
    }finally{centerRendering=false}
  }

  if(typeof baseRender==='function'){
    window.renderOperativoView=async function(name,force=false){
      if(name===CENTER)return await renderCenterV239(currentSavedMode(),false);
      return await baseRender(name,force);
    };
  }
  window.V239_renderCenter=renderCenterV239;

  function bindCenterControls(){
    const mode=q('#operPeriodMode');
    if(mode&&!mode.dataset.v239Bound){
      mode.dataset.v239Bound='1';
      mode.addEventListener('change',e=>{
        if(!q('#operativoNav [data-opview="Centro Ejecutivo"]')?.classList.contains('active'))return;
        e.stopImmediatePropagation();
        const v=e.target.value;setMode(v);
        try{OPER_PERIOD.value=''}catch(_e){}
        modeValues[v]='';
        renderCenterV239(v,true);
      },true);
    }
    const period=q('#operPeriodSelect');
    if(period&&!period.dataset.v239Bound){
      period.dataset.v239Bound='1';
      period.addEventListener('change',e=>{
        const center=q('#operativoNav [data-opview="Centro Ejecutivo"]');
        if(!center?.classList.contains('active'))return;
        e.stopImmediatePropagation();
        const mode=currentSavedMode();
        modeValues[mode]=e.target.value;
        try{OPER_PERIOD.type=mode;OPER_PERIOD.value=e.target.value}catch(_e){}
        renderCenterV239(mode,false);
      },true);
    }
    const apply=q('#operPeriodApply')||q('#operativoPeriodBar .primary');
    if(apply&&!apply.dataset.v239Bound){
      apply.dataset.v239Bound='1';
      apply.addEventListener('click',e=>{
        const center=q('#operativoNav [data-opview="Centro Ejecutivo"]');
        if(!center?.classList.contains('active'))return;
        e.preventDefault();e.stopImmediatePropagation();
        const mode=currentSavedMode(),sel=q('#operPeriodSelect');
        if(sel)modeValues[mode]=sel.value;
        renderCenterV239(mode,false);
      },true);
    }
  }

  /* ---------- Eliminar gráfica Devolución y recuperación ---------- */
  function removeRecoveryCharts(){
    qa('.recovery-svg').forEach(svg=>{
      const box=svg.closest('.chart-box');if(box)box.remove();else svg.remove();
    });
  }
  try{window.recoveryHorizontalChart=function(){return''}}catch(_e){}

  /* ---------- Operación: nombres y Cargar productividad ---------- */
  const OP_LABELS={
    summary:'Resumen',
    daily:'Captura diaria',
    capture:'Cargar productividad',
    productivity:'Productividad',
    standards:'Estándares Operativos'
  };
  function fixOperationTabs(){
    qa('#v200OperationTabs>button[data-v200-op]').forEach(btn=>{
      const key=btn.dataset.v200Op,label=OP_LABELS[key]||btn.textContent.trim();
      btn.title=label;
      btn.dataset.v232Original=label;
      btn.dataset.rtLabel=label;
      const lab=q(':scope>.v232-tab-label,:scope>.v203-tab-label,:scope>.rt-tab-label',btn);
      if(lab&&lab.textContent!==label)lab.textContent=label;
      else if(!lab&&btn.textContent!==label)btn.textContent=label;
    });
  }
  function openCapture(){
    // V222 determina el módulo a partir del menú lateral antes que del body.
    // Sincronizar ambos evita que un estado heredado mande la captura al renderer viejo.
    qa('[data-main]').forEach(x=>{
      if(x.closest('#analysisNav,#operativoNav,#v200OperationTabs'))return;
      x.classList.toggle('active',String(x.dataset.main||'')==='operation');
    });
    document.body.dataset.v163Module='operation';
    document.body.classList.add('v238-module-operation');
    document.body.classList.remove('v238-module-operativo','v238-module-analysis');
    try{window.MAIN='operation'}catch(_e){}
    try{window.V149_OPERATION_TAB='capture';window.V125_OPERATION_TAB='capture'}catch(_e){}
    qa('#v200OperationTabs>button[data-v200-op]').forEach(btn=>{
      const on=btn.dataset.v200Op==='capture';btn.classList.toggle('active',on);btn.setAttribute('aria-selected',on?'true':'false');
    });
    if(typeof window.V222_renderOperationCapture==='function'){
      const out=window.V222_renderOperationCapture();
      // Algunas capas heredadas intentan repintar unos ms después: reafirmar la captura V222.
      setTimeout(()=>{if(typeof window.V222_renderOperationCapture==='function')window.V222_renderOperationCapture()},80);
      return out;
    }
  }
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#v200OperationTabs [data-v200-op="capture"]');
    if(!btn)return;
    const mod=String(document.body.dataset.v163Module||'').toLowerCase();
    if(mod!=='operation'&&!document.body.classList.contains('v238-module-operation'))return;
    e.preventDefault();e.stopImmediatePropagation();
    Promise.resolve(openCapture()).catch(err=>console.warn('[V239] Cargar productividad',err));
  },true);

  /* Estándares: reforzar denominaciones visibles por si aparece histórico Frontal. */
  function normalizeStandardsText(){
    const title=q('#operativoDynamicTitle');
    if(norm(title?.textContent)!=='estandares operativos')return;
    const root=q('#operativoDynamicContent');if(!root)return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    let node;
    while((node=walker.nextNode())){
      if(node.nodeValue&&node.nodeValue.includes('Frontal'))node.nodeValue=node.nodeValue.replaceAll('Frontal','Colgado');
    }
  }

  /* ---------- Observadores / arranque ---------- */
  let tidyTimer=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(tidyTimer);
    tidyTimer=setTimeout(()=>{
      removeLegacyCenterTabs();applyDeleted();decorateVisibilityAdmin();fixOperationTabs();
      bindCenterControls();removeRecoveryCharts();normalizeStandardsText();
    },25);
  });

  function init(){
    removeLegacyCenterTabs();
    fixOperationTabs();
    bindCenterControls();
    removeRecoveryCharts();
    fetchDeleted();
    const box=q('#tabVisibilityOptions');
    if(box)decorateVisibilityAdmin();
    observer.observe(document.body,{subtree:true,childList:true});
    [120,400,900,1800].forEach(ms=>setTimeout(()=>{
      removeLegacyCenterTabs();applyDeleted();decorateVisibilityAdmin();fixOperationTabs();
      bindCenterControls();removeRecoveryCharts();normalizeStandardsText();
    },ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(()=>{applyDeleted();decorateVisibilityAdmin();removeLegacyCenterTabs()},40));
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});

  console.info('[V239] cierre funcional: Centro Operativo, pestañas, gráfica y Cargar productividad.');
})();
</script>'''

    @m.app.middleware("http")
    async def v239_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v239-functional-close-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v239-functional-close-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V239-FUNCTIONAL-CLOSE",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V239] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V239_FUNCTIONAL_CLOSE = True
    print("[V239] cierre funcional instalado.", flush=True)
