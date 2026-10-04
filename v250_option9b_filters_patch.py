"""V250 · Tema global de filtros Opción 9B.

Aplica el diseño 9B (gradiente azul suave, ancho completo y controles compactos)
a los filtros de Cambios y Muertos, Operación y Análisis Comercial, sin cambiar
las reglas de negocio ni los valores que cada pestaña usa.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V250_OPTION9B_FILTERS", False):
        return

    css = r'''<style id="v250-option9b-filters-css">
:root{
  --v250-filter-bg-1:#f7fbff;
  --v250-filter-bg-2:#e6f3ff;
  --v250-filter-bg-3:#cfe9ff;
  --v250-filter-line:#bfd8f2;
  --v250-filter-blue:#0d6ee8;
  --v250-filter-blue-2:#1689ff;
  --v250-filter-navy:#123f73;
}

/* ===== Opción 9B · base ===== */
#operativoPeriodBar.v250-option9b,
#globalFilters.v250-option9b{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin:0 0 12px!important;
  padding:0 14px 14px!important;
  border:1px solid var(--v250-filter-line)!important;
  border-radius:16px!important;
  box-sizing:border-box!important;
  overflow:hidden!important;
  background:
    linear-gradient(115deg,var(--v250-filter-bg-1) 0%,var(--v250-filter-bg-2) 58%,var(--v250-filter-bg-3) 100%)!important;
  box-shadow:0 8px 24px rgba(18,63,115,.08)!important;
}

/* Anula el ancho reducido de V249: Opción 9B ocupa todo el reporte. */
body.v238-module-operativo #operativoPeriodBar.v249-compact.v250-option9b{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin-left:0!important;
  margin-right:0!important;
}

/* Header azul como el boceto 9B */
#operativoPeriodBar.v250-option9b > .or-report-filter-brand,
#globalFilters.v250-option9b > .v250-filter-brand{
  grid-column:1/-1!important;
  width:calc(100% + 28px)!important;
  min-height:66px!important;
  margin:0 -14px 14px!important;
  padding:12px 18px!important;
  display:flex!important;
  align-items:center!important;
  gap:12px!important;
  box-sizing:border-box!important;
  color:#fff!important;
  background:linear-gradient(100deg,#0a4b91 0%,#0b67c8 55%,#1187ff 100%)!important;
  border:0!important;
  border-radius:0!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-brand b,
#globalFilters.v250-option9b > .v250-filter-brand b{
  display:block!important;
  margin:0!important;
  color:#fff!important;
  font-size:16px!important;
  line-height:1.05!important;
  font-weight:950!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-brand small,
#globalFilters.v250-option9b > .v250-filter-brand small{
  display:block!important;
  margin-top:3px!important;
  color:rgba(255,255,255,.9)!important;
  font-size:10px!important;
  line-height:1.15!important;
  font-weight:650!important;
}
#operativoPeriodBar.v250-option9b .or-report-filter-brand-icon,
#globalFilters.v250-option9b .v250-filter-brand-icon{
  width:38px!important;
  height:38px!important;
  min-width:38px!important;
  display:grid!important;
  place-items:center!important;
  border-radius:11px!important;
  color:#fff!important;
  background:rgba(255,255,255,.14)!important;
  border:1px solid rgba(255,255,255,.16)!important;
}
#operativoPeriodBar.v250-option9b .or-report-filter-brand-icon svg,
#globalFilters.v250-option9b .v250-filter-brand-icon svg{
  width:22px!important;
  height:22px!important;
}

/* ===== Opción 9B real: TODO en una sola línea ===== */
#operativoPeriodBar.v250-option9b > .or-report-filter-grid{
  display:flex!important;
  flex-wrap:nowrap!important;
  align-items:flex-end!important;
  gap:10px!important;
  width:100%!important;
  min-width:0!important;
  margin:0!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  padding:0 0 2px!important;
  scrollbar-width:thin;
  -webkit-overflow-scrolling:touch;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid::-webkit-scrollbar{
  height:5px;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid::-webkit-scrollbar-thumb{
  background:#b9d3ee;
  border-radius:999px;
}

#operativoPeriodBar.v250-option9b .v250-quick-period{
  order:-2!important;
  display:flex!important;
  flex-direction:column!important;
  align-items:stretch!important;
  justify-content:flex-end!important;
  flex:1.65 1 330px!important;
  min-width:300px!important;
  width:auto!important;
  margin:0!important;
  padding:0!important;
  border:0!important;
  background:transparent!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-period.hidden{display:none!important}
#operativoPeriodBar.v250-option9b .v250-quick-title{
  flex:none!important;
  margin:0 0 5px!important;
  color:#294b70!important;
  font-size:9px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.025em!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-buttons{
  flex:none!important;
  min-width:0!important;
  height:48px!important;
  display:grid!important;
  grid-template-columns:repeat(var(--v250-quick-count,4),minmax(0,1fr))!important;
  border:1px solid #bcd0e5!important;
  border-radius:11px!important;
  overflow:hidden!important;
  background:rgba(255,255,255,.88)!important;
  box-shadow:0 1px 0 rgba(255,255,255,.72) inset!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-btn{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  min-width:0!important;
  min-height:48px!important;
  height:48px!important;
  padding:0 9px!important;
  border:0!important;
  border-right:1px solid #c9daeb!important;
  border-radius:0!important;
  background:transparent!important;
  color:#153f70!important;
  font-size:10.5px!important;
  line-height:1!important;
  font-weight:900!important;
  white-space:nowrap!important;
  cursor:pointer!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-btn:last-child{border-right:0!important}
#operativoPeriodBar.v250-option9b .v250-quick-btn.active{
  color:#fff!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.15)!important;
}
#operativoPeriodBar.v250-option9b #operPeriodModeWrap.v250-mode-source{
  display:none!important;
}

/* Los selects, filtros particulares y Consultar comparten ESA MISMA fila. */
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > .or-fcontrol:not(.hidden):not(.v249-hidden){
  flex:1 1 185px!important;
  min-width:155px!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodSelectWrap{
  flex:1 1 190px!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operStoreWrap{
  flex:1.15 1 205px!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operActivityWrap,
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operAreaWrap{
  flex:1 1 185px!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
  order:20!important;
  flex:.72 1 145px!important;
  min-width:130px!important;
}

/* Análisis Comercial: encabezado arriba y TODOS los filtros en una sola línea. */
#globalFilters.v250-option9b{
  display:grid!important;
  grid-template-columns:repeat(var(--v250-commercial-count,5),minmax(0,1fr))!important;
  align-items:end!important;
  gap:10px!important;
}
#globalFilters.v250-option9b.hidden{display:none!important}
#globalFilters.v250-option9b > .v250-filter-brand{
  grid-column:1/-1!important;
}
#globalFilters.v250-option9b > .filter,
#globalFilters.v250-option9b > #refresh{
  min-width:0!important;
}

#operativoPeriodBar.v250-option9b .or-fcontrol,
#globalFilters.v250-option9b .filter{
  min-width:0!important;
  width:100%!important;
  max-width:none!important;
  margin:0!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol label,
#globalFilters.v250-option9b .filter label{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
  margin:0 0 5px!important;
  color:#294b70!important;
  font-size:9px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.025em!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol-icon svg{
  width:15px!important;
  height:15px!important;
}
#operativoPeriodBar.v250-option9b .v254-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
#operativoPeriodBar.v250-option9b .v254-mode-icon svg{
  width:15px!important;
  height:15px!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-title{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:7px!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon{
  display:inline-grid!important;
  place-items:center!important;
  flex:0 0 18px!important;
}

#operativoPeriodBar.v250-option9b select,
#operativoPeriodBar.v250-option9b input,
#globalFilters.v250-option9b select,
#globalFilters.v250-option9b input{
  width:100%!important;
  min-width:0!important;
  max-width:none!important;
  min-height:48px!important;
  height:48px!important;
  padding:7px 38px 7px 13px!important;
  border:1px solid #bcd0e5!important;
  border-radius:11px!important;
  box-sizing:border-box!important;
  background:rgba(255,255,255,.88)!important;
  color:#123f73!important;
  font-size:12px!important;
  font-weight:850!important;
  outline:none!important;
  box-shadow:0 1px 0 rgba(255,255,255,.72) inset!important;
}
#operativoPeriodBar.v250-option9b select:focus,
#operativoPeriodBar.v250-option9b input:focus,
#globalFilters.v250-option9b select:focus,
#globalFilters.v250-option9b input:focus{
  border-color:#3f92ed!important;
  box-shadow:0 0 0 3px rgba(22,137,255,.12)!important;
}

/* Botón igual al boceto 9B */
#operativoPeriodBar.v250-option9b #operPeriodApply,
#globalFilters.v250-option9b #refresh{
  width:100%!important;
  min-width:0!important;
  max-width:none!important;
  min-height:48px!important;
  height:48px!important;
  margin:0!important;
  padding:8px 14px!important;
  border:0!important;
  border-radius:11px!important;
  color:#fff!important;
  font-size:13px!important;
  font-weight:950!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:0 7px 15px rgba(13,103,216,.18)!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply:hover,
#globalFilters.v250-option9b #refresh:hover{
  filter:brightness(1.035);
  transform:translateY(-1px);
}
#operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon{
  width:19px!important;
  height:19px!important;
}

/* Respeta ocultos definidos por cada pestaña. */
#operativoPeriodBar.v250-option9b .hidden,
#operativoPeriodBar.v250-option9b .v249-hidden{
  display:none!important;
}

/* ===== Tablet ===== */
@media(max-width:1050px){
  /* Se conserva en línea; si no cabe, se recorre horizontalmente. */
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid{
    flex-wrap:nowrap!important;
    overflow-x:auto!important;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-period{
    flex:0 0 310px!important;
    min-width:310px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > .or-fcontrol:not(.hidden):not(.v249-hidden){
    flex:0 0 175px!important;
    min-width:175px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
    flex:0 0 145px!important;
    min-width:145px!important;
  }
  #globalFilters.v250-option9b{
    display:flex!important;
    flex-wrap:nowrap!important;
    align-items:flex-end!important;
    overflow-x:auto!important;
    gap:8px!important;
    -webkit-overflow-scrolling:touch;
  }
  #globalFilters.v250-option9b > .v250-filter-brand{
    display:none!important;
  }
  #globalFilters.v250-option9b > .filter{
    flex:0 0 180px!important;
    min-width:180px!important;
  }
  #globalFilters.v250-option9b > #refresh{
    flex:0 0 145px!important;
    min-width:145px!important;
  }
}

/* ===== Móvil ===== */
@media(max-width:650px){
  #operativoPeriodBar.v250-option9b,
  #globalFilters.v250-option9b{
    padding:0 8px 9px!important;
    border-radius:12px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-brand,
  #globalFilters.v250-option9b > .v250-filter-brand{
    width:calc(100% + 16px)!important;
    min-height:50px!important;
    margin:0 -8px 8px!important;
    padding:8px 10px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid{
    display:flex!important;
    flex-wrap:nowrap!important;
    gap:7px!important;
    overflow-x:auto!important;
    padding-bottom:4px!important;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-period{
    flex:0 0 275px!important;
    min-width:275px!important;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-buttons{
    height:42px!important;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-btn{
    min-height:42px!important;
    height:42px!important;
    padding:0 7px!important;
    font-size:8.5px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > .or-fcontrol:not(.hidden):not(.v249-hidden){
    flex:0 0 155px!important;
    min-width:155px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
    flex:0 0 125px!important;
    min-width:125px!important;
  }
  #globalFilters.v250-option9b{
    display:flex!important;
    flex-wrap:nowrap!important;
    overflow-x:auto!important;
    gap:7px!important;
    padding:8px!important;
  }
  #globalFilters.v250-option9b > .v250-filter-brand{display:none!important}
  #globalFilters.v250-option9b > .filter{
    flex:0 0 155px!important;
    min-width:155px!important;
  }
  #globalFilters.v250-option9b > #refresh{
    flex:0 0 125px!important;
    min-width:125px!important;
  }
  #operativoPeriodBar.v250-option9b select,
  #operativoPeriodBar.v250-option9b input,
  #globalFilters.v250-option9b select,
  #globalFilters.v250-option9b input,
  #operativoPeriodBar.v250-option9b #operPeriodApply,
  #globalFilters.v250-option9b #refresh{
    min-height:42px!important;
    height:42px!important;
    font-size:10px!important;
  }
  #operativoPeriodBar.v250-option9b .or-fcontrol label,
  #globalFilters.v250-option9b .filter label,
  #operativoPeriodBar.v250-option9b .v250-quick-title{
    font-size:7.5px!important;
  }
}
</style>'''

    js = r'''<script id="v250-option9b-filters-js">
(function(){
  if(window.__V250_OPTION9B_FILTERS)return;
  window.__V250_OPTION9B_FILTERS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  const filterIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5Z"/></svg>';
  const FULL_KEYS=new Set(['operations.center','operations.conversion','operations.recovery','operations.recovery_store','operations.routes','operations.score']);
  const PRODUCTIVITY_KEY='operations.productivity';
  const ROUTES_KEY='operations.routes';

  function activeOpButton(){
    return q('#operativoNav>button.active[data-opview]')||
      q('#operativoNav>button[aria-selected="true"][data-opview]')||
      q('#operativoNav>button[data-opview="Centro Ejecutivo"]');
  }
  function showOp(el,on){
    if(!el)return;
    el.classList.toggle('hidden',!on);
    el.classList.toggle('v249-hidden',!on);
    if(on){
      el.removeAttribute('hidden');
      el.style.removeProperty('display');
    }
  }
  function setRouteTypes(){
    const sel=q('#operActivitySelect');
    const wrap=q('#operActivityWrap');
    if(!sel||!wrap)return;
    const current=['','Muertos','Cambios','Probador'].includes(sel.value)?sel.value:'';
    const values=[['','Todos'],['Muertos','Muertos'],['Cambios','Cambios'],['Probador','Probador']];
    const html=values.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    if(sel.innerHTML!==html)sel.innerHTML=html;
    sel.value=current;
    const label=q('label span:last-child',wrap);
    if(label)label.textContent='Tipo de recolección';
  }
  function applyOperationalProfile(){
    const bar=q('#operativoPeriodBar');
    const btn=activeOpButton();
    if(!bar||!btn)return;
    const key=String(btn.dataset.tabKey||'');
    const view=String(btn.dataset.opview||'');

    /* V255: cada pestaña define explícitamente sus controles.
       Antes las pestañas fuera de FULL_KEYS hacían return y heredaban
       hidden/v249-hidden de la pestaña anterior. */
    if(view==='Metas y tiendas'||view==='Carga de datos'){
      bar.classList.add('hidden');
      return;
    }

    bar.classList.remove('hidden','v249-compact');

    let fixed='flex';
    try{
      if(typeof fixedPeriodTypeForView==='function')fixed=fixedPeriodTypeForView(view);
    }catch(_){}
    const variablePeriod=['flex','fullperiod','productivityperiod'].includes(String(fixed||''));

    showOp(q('#operPeriodModeWrap'),variablePeriod);
    showOp(q('#operPeriodSelectWrap'),true);
    showOp(q('#operStoreWrap'),true);
    showOp(q('#operStartWrap'),false);
    showOp(q('#operEndWrap'),false);
    showOp(q('#operAreaWrap'),false);
    showOp(q('#operActivityWrap'),false);

    if(key===ROUTES_KEY){
      showOp(q('#operActivityWrap'),true);
      setRouteTypes();
    }
  }

  function ensureCommercialBrand(){
    const bar=q('#globalFilters');
    if(!bar)return;
    bar.classList.add('v250-option9b');
    let brand=q(':scope > .v250-filter-brand',bar);
    if(!brand){
      brand=document.createElement('div');
      brand.className='v250-filter-brand';
      brand.innerHTML='<span class="v250-filter-brand-icon">'+filterIcon+'</span><div><b>Filtros del reporte</b><small>Define la vista antes de consultar</small></div>';
      bar.prepend(brand);
    }
    const btn=q('#refresh',bar);
    if(btn && btn.textContent.trim()!=='Consultar')btn.textContent='Consultar';

    const visible=qa(':scope > .filter, :scope > button',bar).filter(el=>{
      if(el.classList.contains('hidden'))return false;
      if(el.style.display==='none')return false;
      return true;
    });
    bar.style.setProperty('--v250-commercial-count',String(Math.max(1,Math.min(visible.length,6))));
  }

  function modeWrapVisible(){
    const wrap=q('#operPeriodModeWrap');
    if(!wrap)return false;
    return !wrap.classList.contains('hidden') &&
      !wrap.classList.contains('v249-hidden') &&
      wrap.style.display!=='none';
  }

  function syncQuickActive(){
    const sel=q('#operPeriodMode');
    const quick=q('#operativoPeriodBar .v250-quick-period');
    if(!quick||!sel)return;
    qa('.v250-quick-btn',quick).forEach(btn=>btn.classList.toggle('active',btn.dataset.mode===sel.value));
  }

  function v254ModeIcon(v){
    const icons={
      day:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M8 14h3"/></svg>',
      week:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M7 14h2M11 14h2M15 14h2"/></svg>',
      month:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M7 14h3M12 14h3M7 17h3M12 17h3"/></svg>',
      year:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v4M17 2v4M3 9h18"/><path d="M8 13h8M8 17h5"/></svg>'
    };
    return '<span class="v254-mode-icon">'+(icons[v]||icons.month)+'</span>';
  }

  function ensureQuickMode(){
    /* V258 es el único controlador visual de Vista operativa.
       Cuando está activo, V250 conserva estilos/base pero deja de reconstruir
       su selector rápido heredado. */
    if(window.__V258_UNIVERSAL_FILTER){
      const legacy=q('#operativoPeriodBar .v250-quick-period');
      if(legacy)legacy.classList.add('hidden');
      return;
    }
    const bar=q('#operativoPeriodBar');
    const grid=q(':scope > .or-report-filter-grid',bar);
    const mode=q('#operPeriodMode');
    const wrap=q('#operPeriodModeWrap');
    if(!bar||!grid||!mode||!wrap)return;

    let quick=q('.v250-quick-period',bar);
    if(!quick){
      quick=document.createElement('div');
      quick.className='v250-quick-period hidden';
    }
    if(quick.parentElement!==grid){
      grid.insertBefore(quick,grid.firstElementChild||null);
    }

    const canShow=modeWrapVisible() && mode.options.length>1;
    if(!canShow){
      wrap.classList.remove('v250-mode-source');
      quick.classList.add('hidden');
      return;
    }

    wrap.classList.add('v250-mode-source');
    quick.classList.remove('hidden');

    const opts=[...mode.options].map(o=>({value:o.value,text:o.textContent.trim()}));
    quick.style.setProperty('--v250-quick-count',String(Math.max(1,opts.length)));
    const signature=opts.map(o=>o.value+'='+o.text).join('|');
    if(quick.dataset.signature!==signature){
      quick.dataset.signature=signature;
      quick.innerHTML='<div class="v250-quick-title"><span class="or-fcontrol-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z"/><circle cx="12" cy="12" r="2.5"/></svg></span>Vista operativa</div><div class="v250-quick-buttons">'+
        opts.map(o=>'<button type="button" class="v250-quick-btn" data-mode="'+o.value+'">'+v254ModeIcon(o.value)+'<span>'+o.text+'</span></button>').join('')+
        '</div>';
      qa('.v250-quick-btn',quick).forEach(btn=>btn.addEventListener('click',()=>{
        if(mode.value===btn.dataset.mode)return;
        mode.value=btn.dataset.mode;
        syncQuickActive();
        mode.dispatchEvent(new Event('change',{bubbles:true}));
      }));
    }
    syncQuickActive();
  }

  function ensureOperational(){
    const bar=q('#operativoPeriodBar');
    if(!bar)return;

    applyOperationalProfile();
    bar.classList.add('v250-option9b');
    bar.classList.remove('v249-compact');
    bar.style.setProperty('width','100%','important');
    bar.style.setProperty('max-width','100%','important');
    bar.style.setProperty('min-width','0','important');
    bar.style.setProperty('margin-left','0','important');
    bar.style.setProperty('margin-right','0','important');

    const brand=q(':scope > .or-report-filter-brand',bar);
    if(brand){
      const icon=q('.or-report-filter-brand-icon',brand);
      if(icon)icon.innerHTML=filterIcon;
      const small=q('small',brand);
      if(small)small.textContent='Define la vista antes de consultar';
    }

    ensureQuickMode();

    const grid=q(':scope > .or-report-filter-grid',bar);
    if(!grid)return;
    grid.style.setProperty('display','flex','important');
    grid.style.setProperty('flex-wrap','nowrap','important');
    grid.style.setProperty('align-items','flex-end','important');
    grid.style.setProperty('gap','10px','important');
    grid.style.setProperty('width','100%','important');
    grid.style.setProperty('max-width','100%','important');
    grid.style.setProperty('min-width','0','important');
    grid.style.setProperty('overflow-x','auto','important');
    grid.style.setProperty('overflow-y','hidden','important');
    grid.style.setProperty('grid-template-columns','none','important');
    grid.style.setProperty('grid-auto-flow','unset','important');

    const quick=q(':scope > .v250-quick-period',grid);
    if(quick&&!quick.classList.contains('hidden')){
      quick.style.setProperty('flex','1.6 1 340px','important');
      quick.style.setProperty('min-width','300px','important');
      quick.style.setProperty('width','auto','important');
    }

    const sizing={
      operPeriodSelectWrap:'1 1 190px',
      operStoreWrap:'1.15 1 210px',
      operAreaWrap:'1 1 180px',
      operActivityWrap:'1 1 190px'
    };
    qa(':scope > .or-fcontrol',grid).forEach(el=>{
      if(el.id==='operPeriodModeWrap'&&el.classList.contains('v250-mode-source'))return;
      if(el.classList.contains('hidden')||el.classList.contains('v249-hidden'))return;
      el.style.setProperty('flex',sizing[el.id]||'1 1 180px','important');
      el.style.setProperty('min-width','150px','important');
      el.style.setProperty('width','auto','important');
      el.style.setProperty('max-width','none','important');
    });
    const applyBtn=q('#operPeriodApply',grid);
    if(applyBtn){
      applyBtn.style.setProperty('flex','.72 1 150px','important');
      applyBtn.style.setProperty('min-width','135px','important');
      applyBtn.style.setProperty('width','auto','important');
      applyBtn.style.setProperty('grid-column','auto','important');
    }

    const controls=qa(':scope > .or-fcontrol, :scope > button, :scope > .v250-quick-period',grid).filter(el=>{
      if(el.id==='operPeriodModeWrap' && el.classList.contains('v250-mode-source'))return false;
      if(el.classList.contains('hidden')||el.classList.contains('v249-hidden'))return false;
      if(el.style.display==='none')return false;
      return true;
    });
    grid.style.setProperty('--v250-control-count',String(Math.max(1,Math.min(controls.length,7))));
  }

  function apply(){
    ensureOperational();
    ensureCommercialBrand();
  }

  document.addEventListener('click',async e=>{
    const goals=e.target.closest?.('#openGoalsBtn');
    if(goals){
      e.preventDefault();
      e.stopImmediatePropagation();
      try{
        window.OP_VIEW='Metas y tiendas';
      }catch(_e){}
      qa('#operativoNav>button').forEach(b=>{
        const on=b===goals;
        b.classList.toggle('active',on);
        b.setAttribute('aria-selected',on?'true':'false');
      });
      const bar=q('#operativoPeriodBar');
      if(bar)bar.classList.add('hidden');
      if(typeof renderGoalsConfig==='function'){
        await renderGoalsConfig();
      }
      return;
    }
    if(e.target.closest?.('#operativoNav>button,#analysisNav>button,[data-main]')){
      [0,40,140,400].forEach(ms=>setTimeout(apply,ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(['operPeriodMode','operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect','week','store','section','catalog'].includes(e.target?.id||'')){
      setTimeout(apply,0);
      setTimeout(apply,120);
    }
  },true);

  const observer=new MutationObserver(()=>setTimeout(apply,0));
  function start(){
    const op=q('#operativoPeriodBar'),commercial=q('#globalFilters'),nav=q('#operativoNav'),anav=q('#analysisNav');
    [op,commercial,nav,anav].filter(Boolean).forEach(el=>observer.observe(el,{subtree:true,childList:true}));
    apply();
    [120,400,900,1800].forEach(ms=>setTimeout(apply,ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V252] Opción 9B autoritativa: una sola línea horizontal y Metas reparada.');
})();
</script>'''

    @m.app.middleware("http")
    async def v250_option9b_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v250-option9b-filters-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v250-option9b-filters-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V250-OPTION9B-FILTERS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V250] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V250_OPTION9B_FILTERS = True
    print("[V252] Opción 9B horizontal autoritativa instalada.",flush=True)
