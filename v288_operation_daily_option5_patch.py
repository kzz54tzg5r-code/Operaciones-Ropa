"""V288 · Opción 5 para Operación > Captura diaria.

Capa visual no destructiva:
- agrega 4 tarjetas de contexto (cobertura, pendiente, avance y estado);
- conserva los filtros, IDs, endpoints, permisos y eventos existentes;
- convierte los 4 campos de Origen en tarjetas compactas;
- sólo se activa en la pestaña Captura diaria del módulo Operación.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V288_OPERATION_DAILY_OPTION5", False):
        return

    css = r'''<style id="v288-operation-daily-option5-css">
:root{
  --v288-navy:#123f73;
  --v288-blue:#1689ff;
  --v288-line:#d7e3ef;
  --v288-muted:#667a90;
}

/* ===== Opción 5 · KPIs de Captura diaria ===== */
body.v288-daily-option5 #v288DailyKpis{
  display:grid!important;
  grid-template-columns:repeat(4,minmax(0,1fr))!important;
  gap:10px!important;
  width:100%!important;
  min-width:0!important;
  margin:8px 0 10px!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-kpi{
  min-width:0!important;
  min-height:92px!important;
  border:1px solid var(--v288-line)!important;
  border-radius:14px!important;
  padding:11px 12px!important;
  display:grid!important;
  grid-template-columns:42px minmax(0,1fr)!important;
  gap:10px!important;
  align-items:center!important;
  box-sizing:border-box!important;
  overflow:hidden!important;
  box-shadow:0 5px 14px rgba(18,63,115,.05)!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-kpi.blue{background:linear-gradient(135deg,#eef7ff 0%,#fff 100%)!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi.orange{background:linear-gradient(135deg,#fff7e9 0%,#fff 100%)!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi.green{background:linear-gradient(135deg,#eefbf4 0%,#fff 100%)!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi.purple{background:linear-gradient(135deg,#f6f1ff 0%,#fff 100%)!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi-icon{
  width:42px!important;height:42px!important;border-radius:11px!important;
  display:grid!important;place-items:center!important;
}
body.v288-daily-option5 #v288DailyKpis .blue .v288-kpi-icon{background:#dceeff!important;color:#1478dc!important}
body.v288-daily-option5 #v288DailyKpis .orange .v288-kpi-icon{background:#ffedcf!important;color:#e88b00!important}
body.v288-daily-option5 #v288DailyKpis .green .v288-kpi-icon{background:#daf6e5!important;color:#07934f!important}
body.v288-daily-option5 #v288DailyKpis .purple .v288-kpi-icon{background:#eadfff!important;color:#6c3bd2!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi-icon svg{width:22px!important;height:22px!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi-copy{min-width:0!important}
body.v288-daily-option5 #v288DailyKpis .v288-kpi-label{
  display:flex!important;align-items:center!important;gap:5px!important;
  color:#496681!important;font-size:8px!important;line-height:1.1!important;
  font-weight:950!important;white-space:normal!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-kpi-value{
  display:block!important;margin-top:5px!important;color:var(--v288-navy)!important;
  font-size:22px!important;line-height:1!important;font-weight:950!important;
  letter-spacing:-.02em!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-kpi-sub{
  display:block!important;margin-top:5px!important;color:#718398!important;
  font-size:7.2px!important;line-height:1.25!important;font-weight:700!important;
  white-space:normal!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-chip{
  display:inline-flex!important;align-items:center!important;gap:4px!important;
  margin-top:5px!important;padding:3px 7px!important;border-radius:999px!important;
  width:max-content!important;max-width:100%!important;font-size:6.7px!important;
  line-height:1!important;font-weight:950!important;white-space:nowrap!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-chip.good{background:#dff7e8!important;color:#13733b!important}
body.v288-daily-option5 #v288DailyKpis .v288-chip.warn{background:#fff0d3!important;color:#b66d00!important}
body.v288-daily-option5 #v288DailyKpis .v288-chip.closed{background:#ffe6e6!important;color:#b42318!important}
body.v288-daily-option5 #v288DailyKpis .v288-progress{
  height:6px!important;margin-top:7px!important;border-radius:999px!important;
  overflow:hidden!important;background:#dfe8ef!important;
}
body.v288-daily-option5 #v288DailyKpis .v288-progress i{
  display:block!important;height:100%!important;border-radius:inherit!important;background:#13a663!important;
}

/* ===== Filtros · versión clara y compacta de la Opción 5 ===== */
body.v288-daily-option5 #operativoPeriodBar{
  background:#fff!important;border:1px solid var(--v288-line)!important;
  border-radius:14px!important;box-shadow:0 5px 16px rgba(18,63,115,.05)!important;
  overflow:hidden!important;margin:0 0 10px!important;
}
body.v288-daily-option5 #operativoPeriodBar.v250-option9b{
  padding:0 12px 11px!important;
}
body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-brand{
  width:100%!important;min-height:48px!important;height:auto!important;
  margin:0 0 7px!important;padding:8px 2px 7px!important;
  color:var(--v288-navy)!important;background:#fff!important;
  border:0!important;border-bottom:1px solid #edf2f7!important;border-radius:0!important;
  box-shadow:none!important;gap:9px!important;
}
body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-brand b{
  color:var(--v288-navy)!important;font-size:13px!important;line-height:1.05!important;
}
body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-brand small{
  color:#6b7f93!important;font-size:7.5px!important;line-height:1.15!important;margin-top:2px!important;
}
body.v288-daily-option5 #operativoPeriodBar .or-report-filter-brand-icon{
  width:34px!important;height:34px!important;min-width:34px!important;border-radius:9px!important;
  color:#1478dc!important;background:#e7f3ff!important;border:0!important;
}
body.v288-daily-option5 #operativoPeriodBar .or-report-filter-brand-icon svg{width:19px!important;height:19px!important}
body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-grid{
  gap:10px!important;align-items:flex-end!important;overflow-x:hidden!important;
}
body.v288-daily-option5 #operativoPeriodBar select,
body.v288-daily-option5 #operativoPeriodBar input{
  border-color:#cad9e7!important;background:#fbfdff!important;border-radius:9px!important;
}

/* ===== Formulario Captura diaria · Origen ===== */
body.v288-daily-option5 .v288-capture-panel{
  border:1px solid var(--v288-line)!important;border-radius:15px!important;
  padding:13px!important;background:#fff!important;box-shadow:0 5px 16px rgba(18,63,115,.05)!important;
}
body.v288-daily-option5 .v288-capture-panel>div:first-child{
  align-items:center!important;gap:10px!important;
}
body.v288-daily-option5 .v288-capture-panel h3{
  display:flex!important;align-items:center!important;gap:8px!important;
  margin:0 0 3px!important;color:var(--v288-navy)!important;font-size:15px!important;font-weight:950!important;
}
body.v288-daily-option5 .v288-title-icon{
  width:30px!important;height:30px!important;min-width:30px!important;
  display:grid!important;place-items:center!important;border-radius:9px!important;
  background:#e7f3ff!important;color:#1478dc!important;
}
body.v288-daily-option5 .v288-title-icon svg{width:17px!important;height:17px!important}
body.v288-daily-option5 .v288-capture-panel>.v125-note,
body.v288-daily-option5 .v288-capture-panel>div:first-child .v125-note{
  color:#6c7f93!important;font-size:7.8px!important;line-height:1.35!important;
}
body.v288-daily-option5 .v288-capture-panel .v125-status{
  padding:5px 10px!important;border-radius:999px!important;font-size:7.5px!important;
}
body.v288-daily-option5 .v288-capture-panel .v288-capture-grid{
  display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;
  gap:9px!important;margin-top:11px!important;align-items:stretch!important;
}
body.v288-daily-option5 .v288-capture-panel .v288-field{
  position:relative!important;min-width:0!important;min-height:99px!important;
  border:1px solid #d7e3ef!important;border-radius:12px!important;
  padding:10px 10px 9px 48px!important;box-sizing:border-box!important;
}
body.v288-daily-option5 .v288-capture-panel .v288-field[data-v288-tone="arrival"]{background:linear-gradient(135deg,#eef7ff,#fff)!important}
body.v288-daily-option5 .v288-capture-panel .v288-field[data-v288-tone="released"]{background:linear-gradient(135deg,#f5f0ff,#fff)!important;border-color:#dfd2f8!important}
body.v288-daily-option5 .v288-capture-panel .v288-field[data-v288-tone="pending"]{background:linear-gradient(135deg,#fff7e9,#fff)!important;border-color:#f4dfb7!important}
body.v288-daily-option5 .v288-capture-panel .v288-field[data-v288-tone="excess"]{background:linear-gradient(135deg,#eefbf4,#fff)!important;border-color:#bee8d1!important}
body.v288-daily-option5 .v288-field-icon{
  position:absolute!important;left:10px!important;top:10px!important;
  width:30px!important;height:30px!important;border-radius:8px!important;
  display:grid!important;place-items:center!important;background:#dfefff!important;color:#1478dc!important;
}
body.v288-daily-option5 .v288-field[data-v288-tone="released"] .v288-field-icon{background:#eadfff!important;color:#6c3bd2!important}
body.v288-daily-option5 .v288-field[data-v288-tone="pending"] .v288-field-icon{background:#ffebc7!important;color:#df8200!important}
body.v288-daily-option5 .v288-field[data-v288-tone="excess"] .v288-field-icon{background:#d9f5e4!important;color:#088f50!important}
body.v288-daily-option5 .v288-field-icon svg{width:17px!important;height:17px!important}
body.v288-daily-option5 .v288-capture-panel .v288-field label{
  display:block!important;margin:2px 0 7px!important;color:var(--v288-navy)!important;
  font-size:8.3px!important;line-height:1.15!important;font-weight:950!important;
  text-transform:none!important;white-space:normal!important;
}
body.v288-daily-option5 .v288-capture-panel .v288-field input{
  width:100%!important;height:38px!important;min-height:38px!important;
  padding:6px 9px!important;border:1px solid #cbd9e7!important;border-radius:8px!important;
  background:#fff!important;color:#173f70!important;font-size:13px!important;font-weight:850!important;
  box-sizing:border-box!important;
}
body.v288-daily-option5 .v288-capture-panel .v288-field[data-v288-tone="excess"] input{
  border-color:#8bd0ac!important;background:#f8fffb!important;
}
body.v288-daily-option5 .v288-capture-panel .v288-field input:disabled{
  opacity:1!important;background:#f1f6fa!important;color:#47647f!important;
}
body.v288-daily-option5 .v288-capture-panel .v159-auto-note,
body.v288-daily-option5 .v288-capture-panel .v288-help{
  display:block!important;margin-top:5px!important;color:#708397!important;
  font-size:6.8px!important;line-height:1.25!important;font-weight:700!important;
}
body.v288-daily-option5 .v288-capture-panel .v125-actions{
  display:flex!important;justify-content:flex-start!important;align-items:center!important;
  gap:8px!important;margin-top:10px!important;
}
body.v288-daily-option5 .v288-capture-panel .v125-actions button{
  min-height:38px!important;border-radius:9px!important;padding:7px 13px!important;font-size:8px!important;font-weight:950!important;
}
body.v288-daily-option5 .v288-capture-panel #v125SaveOrigin{
  background:linear-gradient(135deg,#0d6fd5,#168cff)!important;border-color:#168cff!important;color:#fff!important;
  box-shadow:0 5px 12px rgba(22,137,255,.18)!important;
}
body.v288-daily-option5 .v288-capture-panel #v125CloseDay{
  background:#fff!important;border:1px solid #ef6b6b!important;color:#c82b2b!important;
}
body.v288-daily-option5 .v288-capture-panel #v125DailyMsg{font-size:7.5px!important;margin-top:6px!important}

/* ===== Responsive: conserva estructura tipo laptop, sólo compacta ===== */
@media(max-width:1100px){
  body.v288-daily-option5 #v288DailyKpis{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  body.v288-daily-option5 .v288-capture-panel .v288-capture-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:700px){
  body.v288-daily-option5 #v288DailyKpis{gap:5px!important;margin:5px 0 7px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-kpi{
    min-height:70px!important;padding:7px!important;grid-template-columns:30px minmax(0,1fr)!important;gap:6px!important;border-radius:9px!important;
  }
  body.v288-daily-option5 #v288DailyKpis .v288-kpi-icon{width:30px!important;height:30px!important;border-radius:8px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-kpi-icon svg{width:16px!important;height:16px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-kpi-label{font-size:6px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-kpi-value{font-size:15px!important;margin-top:3px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-kpi-sub{font-size:5.5px!important;margin-top:3px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-chip{font-size:5px!important;padding:2px 5px!important;margin-top:3px!important}
  body.v288-daily-option5 #v288DailyKpis .v288-progress{height:4px!important;margin-top:4px!important}
  body.v288-daily-option5 #operativoPeriodBar.v250-option9b{padding:0 5px 6px!important}
  body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-brand{min-height:36px!important;padding:5px 1px!important;margin-bottom:4px!important}
  body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-brand b{font-size:9px!important}
  body.v288-daily-option5 #operativoPeriodBar>.or-report-filter-brand small{font-size:5.5px!important}
  body.v288-daily-option5 #operativoPeriodBar .or-report-filter-brand-icon{width:25px!important;height:25px!important;min-width:25px!important}
  body.v288-daily-option5 .v288-capture-panel{padding:7px!important;border-radius:10px!important}
  body.v288-daily-option5 .v288-capture-panel h3{font-size:10px!important;gap:5px!important}
  body.v288-daily-option5 .v288-title-icon{width:23px!important;height:23px!important;min-width:23px!important;border-radius:6px!important}
  body.v288-daily-option5 .v288-capture-panel .v288-capture-grid{gap:5px!important;margin-top:6px!important}
  body.v288-daily-option5 .v288-capture-panel .v288-field{
    min-height:78px!important;padding:6px 6px 6px 32px!important;border-radius:8px!important;
  }
  body.v288-daily-option5 .v288-field-icon{left:5px!important;top:6px!important;width:22px!important;height:22px!important;border-radius:6px!important}
  body.v288-daily-option5 .v288-field-icon svg{width:12px!important;height:12px!important}
  body.v288-daily-option5 .v288-capture-panel .v288-field label{font-size:5.7px!important;margin:1px 0 4px!important}
  body.v288-daily-option5 .v288-capture-panel .v288-field input{height:30px!important;min-height:30px!important;font-size:8px!important;padding:3px 5px!important}
  body.v288-daily-option5 .v288-capture-panel .v159-auto-note,
  body.v288-daily-option5 .v288-capture-panel .v288-help{font-size:5px!important;margin-top:3px!important}
  body.v288-daily-option5 .v288-capture-panel .v125-actions{gap:5px!important;margin-top:6px!important}
  body.v288-daily-option5 .v288-capture-panel .v125-actions button{min-height:31px!important;padding:5px 8px!important;font-size:6px!important}
}
@media(max-width:340px){
  body.v288-daily-option5 #v288DailyKpis{grid-template-columns:1fr!important}
  body.v288-daily-option5 .v288-capture-panel .v288-capture-grid{grid-template-columns:1fr!important}
}
</style>'''

    js = r'''<script id="v288-operation-daily-option5-js">
(function(){
  if(window.__V288_OPERATION_DAILY_OPTION5)return;
  window.__V288_OPERATION_DAILY_OPTION5=true;

  const q=(s,r=document)=>r.querySelector(s);
  const num=v=>Number(v||0);
  const fmt=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:0});
  const pct=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1});
  let timer=0;

  const icons={
    calendar:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>',
    clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>',
    bars:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M5 19V12M10 19V8M15 19V4M20 19V10"/></svg>',
    pulse:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 12h4l2-6 4 12 2-6h6"/></svg>',
    truck:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 6h11v10H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
    cube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/></svg>',
    doc:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 12h6M9 16h6"/></svg>',
    plus:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M12 5v14M5 12h14"/></svg>'
  };

  function isOperation(){
    if(document.body.classList.contains('v238-module-operation'))return true;
    if(String(document.body.dataset.v163Module||'').toLowerCase()==='operation')return true;
    try{
      return String(window.MAIN||'').toLowerCase()==='operation' || String(window.OP_VIEW||'').toLowerCase()==='operación';
    }catch(_){return false}
  }

  function activeTab(){
    const top=q('#v200OperationTabs [data-v200-op].active') || q('#v200OperationTabs [data-v200-op][aria-selected="true"]');
    if(top && top.dataset.v200Op)return String(top.dataset.v200Op);
    const legacy=q('.v125-tabs .v125-tab.active');
    if(legacy){
      if(legacy.dataset.v149Tab)return String(legacy.dataset.v149Tab);
      if(legacy.dataset.v125Tab)return String(legacy.dataset.v125Tab);
    }
    try{
      if(String(window.V149_OPERATION_TAB||'')==='daily')return 'daily';
      if(String(window.V125_OPERATION_TAB||'')==='daily')return 'daily';
    }catch(_){}
    return '';
  }

  async function getJson(url){
    const r=await fetch(url,{credentials:'same-origin',cache:'no-store'});
    let d={};
    try{d=await r.json()}catch(_){}
    if(!r.ok)throw new Error(d.detail||d.message||('HTTP '+r.status));
    return d;
  }

  function fieldCard(input,tone,label,help){
    if(!input)return;
    const root=input.closest('.v125-field,.v159-pending-field,.v159-excess-field');
    if(!root)return;
    root.classList.add('v288-field');
    root.dataset.v288Tone=tone;
    let lab=q('label',root);
    if(lab){
      if(tone==='pending'){
        const note=q('.v159-auto-note',root);
        const auto=/autom/i.test(lab.textContent||'') || /calculad/i.test(note?.textContent||'');
        lab.textContent=auto?'Pendiente automático':'Piezas pendientes iniciales';
      }else{
        lab.textContent=label;
      }
    }
    if(!q('.v288-field-icon',root)){
      const span=document.createElement('span');
      span.className='v288-field-icon';
      span.setAttribute('aria-hidden','true');
      span.innerHTML=icons[tone==='arrival'?'truck':tone==='released'?'cube':tone==='pending'?'doc':'plus'];
      root.insertAdjacentElement('afterbegin',span);
    }
    if(help && !q('.v159-auto-note',root) && !q('.v288-help',root)){
      const small=document.createElement('small');
      small.className='v288-help';
      small.textContent=help;
      root.appendChild(small);
    }
  }

  function decorateCapture(){
    const arrival=q('#v125OriginArrival');
    const released=q('#v125OriginReleased');
    if(!arrival||!released)return;
    const panel=arrival.closest('.v125-panel');
    if(!panel)return;
    panel.classList.add('v288-capture-panel');
    const grid=arrival.closest('.v125-two');
    if(grid)grid.classList.add('v288-capture-grid');
    const title=q('h3',panel);
    if(title && !q('.v288-title-icon',title)){
      const span=document.createElement('span');
      span.className='v288-title-icon';
      span.setAttribute('aria-hidden','true');
      span.innerHTML=icons.cube;
      title.insertAdjacentElement('afterbegin',span);
    }
    fieldCard(arrival,'arrival','Llegada','Piezas recibidas en la tienda.');
    fieldCard(released,'released','Mercancía liberada','Piezas liberadas hacia piso.');
    fieldCard(q('#v159OriginPending'),'pending','Piezas pendientes iniciales','');
    fieldCard(q('#v159OriginExcess'),'excess','Excedente','');
  }

  function kpiCard(tone,icon,label,value,sub,extra){
    return '<article class="v288-kpi '+tone+'">'+
      '<span class="v288-kpi-icon" aria-hidden="true">'+icons[icon]+'</span>'+
      '<div class="v288-kpi-copy">'+
        '<span class="v288-kpi-label">'+label+'</span>'+
        '<b class="v288-kpi-value">'+value+'</b>'+
        (sub?'<span class="v288-kpi-sub">'+sub+'</span>':'')+
        (extra||'')+
      '</div>'+
    '</article>';
  }

  function renderKpis(coverage,daily,summary,hasContext){
    const bar=q('#operativoPeriodBar');
    if(!bar)return;
    let host=q('#v288DailyKpis');
    if(!host){
      host=document.createElement('section');
      host.id='v288DailyKpis';
      host.setAttribute('aria-label','Resumen de captura diaria');
      bar.insertAdjacentElement('beforebegin',host);
    }

    const s=(summary&&summary.summary)||{};
    const progress=num(s.progress_pieces);
    const compliance=num(s.compliance_pct);
    const target=compliance>0 ? progress/(compliance/100) : 0;
    const pending=hasContext ? num(daily?.pending ?? s.pending ?? 0) : null;
    const closed=String(daily?.status?.status||'open').toLowerCase()==='closed';
    const coverageDate=String(coverage?.max_date||coverage?.raw?.parsed_max||'').slice(0,10) || '—';
    const pendingValue=pending===null?'—':fmt(pending);
    const pendingSub=pending===null?'Selecciona una tienda':'piezas';
    const advanceValue=hasContext ? pct(compliance)+'%' : '—';
    let advanceSub='Selecciona una tienda';
    if(hasContext){
      advanceSub=target>0 ? (fmt(progress)+' / '+fmt(target)+' pzas') : (fmt(progress)+' pzas de avance');
    }
    const stateValue=!hasContext?'Sin tienda':(closed?'Cerrado':'En captura');
    const stateSub=!hasContext?'Selecciona tienda y fecha':(closed?'El día seleccionado está cerrado.':'Captura abierta para el día seleccionado.');
    const stateChip=hasContext
      ? '<span class="v288-chip '+(closed?'closed':'good')+'">'+(closed?'Cerrado':'● En captura')+'</span>'
      : '<span class="v288-chip warn">Por seleccionar</span>';
    const progressWidth=Math.max(0,Math.min(100,compliance));

    host.innerHTML=
      kpiCard('blue','calendar','Cobertura publicada',coverageDate,'Última cobertura operativa','<span class="v288-chip good">✓ Publicada</span>')+
      kpiCard('orange','clock','Pendiente estimado',pendingValue,pendingSub,hasContext?'<span class="v288-chip warn">Por capturar</span>':'')+
      kpiCard('green','bars','Avance productivo',advanceValue,advanceSub,hasContext?'<div class="v288-progress"><i style="width:'+progressWidth+'%"></i></div>':'')+
      kpiCard('purple','pulse','Estado',stateValue,stateSub,stateChip);
  }

  async function refresh(){
    const dailyMode=isOperation() && activeTab()==='daily';
    document.body.classList.toggle('v288-daily-option5',dailyMode);
    if(!dailyMode){
      q('#v288DailyKpis')?.remove();
      return;
    }

    decorateCapture();

    const day=String(q('#operPeriodSelect')?.value||'').trim();
    const store=String(q('#operStoreSelect')?.value||'').trim();
    const hasContext=Boolean(day && store && store!=='Compañía');
    const coverageP=getJson('/api/operations/coverage-v169').catch(()=>({}));
    const dailyP=hasContext
      ? getJson('/api/operation/origin-capture-v159?'+new URLSearchParams({date:day,store:store})).catch(()=>({}))
      : Promise.resolve({});
    const summaryP=hasContext
      ? getJson('/api/operation/summary-v149?'+new URLSearchParams({period_type:'day',period_value:day,store:store})).catch(()=>({}))
      : Promise.resolve({});

    const values=await Promise.all([coverageP,dailyP,summaryP]);
    renderKpis(values[0],values[1],values[2],hasContext);
    decorateCapture();
  }

  function schedule(ms){
    clearTimeout(timer);
    timer=setTimeout(function(){refresh().catch(function(e){console.warn('[V288]',e)})},ms||80);
  }

  function wrapRender(){
    const prev=window.renderOperativoView;
    if(typeof prev!=='function')return false;
    if(prev.__v288Option5)return true;
    const wrapped=async function(){
      const out=await prev.apply(this,arguments);
      schedule(25);
      setTimeout(function(){schedule(30)},260);
      return out;
    };
    wrapped.__v288Option5=true;
    wrapped.__v288Previous=prev;
    window.renderOperativoView=wrapped;
    return true;
  }

  document.addEventListener('click',function(e){
    if(e.target.closest?.('#v200OperationTabs>button,.v125-tabs>.v125-tab,[data-main="operation"],#v125SaveOrigin,#v125CloseDay,#v125ReopenDay')){
      schedule(180);
      setTimeout(function(){schedule(20)},520);
    }
  },true);

  document.addEventListener('change',function(e){
    if(e.target?.matches?.('#operStoreSelect,#operPeriodSelect,#operPeriodMode')){
      schedule(220);
    }
  },true);

  wrapRender();
  setTimeout(function(){wrapRender();schedule(20)},420);
  setTimeout(function(){schedule(20)},950);
  console.info('[V288] Opción 5 activa en Operación > Captura diaria.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v288_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            ctype = str(response.headers.get("content-type") or "").lower()
            if "text/html" not in ctype:
                return response
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v288-operation-daily-option5-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v288-operation-daily-option5-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in {"content-length", "content-encoding", "transfer-encoding"}
            }
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["Pragma"] = "no-cache"
            headers["Expires"] = "0"
            headers["X-Operations-UI-Version"] = "V288-OPTION5"
            return HTMLResponse(
                content=html,
                status_code=response.status_code,
                headers=headers,
            )
        except Exception as exc:
            print(f"[V288] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V288_OPERATION_DAILY_OPTION5 = True
    print("[V288] Opción 5 de Captura diaria instalada.", flush=True)
