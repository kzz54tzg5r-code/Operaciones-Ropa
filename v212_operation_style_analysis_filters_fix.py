"""V212 · Navegación tipo Operación + filtros comerciales debajo de pestañas.

- Cambios y Muertos y Análisis Comercial adoptan la misma tarjeta de navegación
  visual que Operación (icono + nombre + activo azul), sin cambiar listeners,
  permisos ni contenido de los reportes.
- Análisis Comercial usa un único bloque de filtros debajo de pestañas/título:
  Periodo, Tienda, Sección, Catálogo y Estatus.
- Neutraliza la fachada/carrusel visual antiguo, pero conserva las pestañas
  existentes y su configuración de visibilidad.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V212_OPERATION_STYLE_ANALYSIS_FILTERS", False):
        return

    css = r"""<style id="v212-operation-style-analysis-filters-css">
:root{
  --v212-blue:#0878df;
  --v212-navy:#0d4f8b;
  --v212-ink:#123f73;
  --v212-muted:#70849a;
  --v212-line:#d6e3f0;
}

/* ============================================================
   CAMBIOS Y MUERTOS + ANÁLISIS: MISMO PATRÓN VISUAL DE OPERACIÓN
   ============================================================ */
body[data-v163-module="operativo"] #operativoNav:not(.hidden),
body[data-v163-module="analysis"] #analysisNav:not(.hidden){
  display:flex!important;
  grid-template-columns:none!important;
  flex-wrap:nowrap!important;
  align-items:stretch!important;
  justify-content:flex-start!important;
  gap:9px!important;
  width:100%!important;
  max-width:100%!important;
  min-height:96px!important;
  height:auto!important;
  margin:3px 0 9px!important;
  padding:7px 3px 13px!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  background:transparent!important;
  border:0!important;
  border-radius:0!important;
  box-shadow:none!important;
  white-space:nowrap!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important;
  scroll-snap-type:x mandatory!important;
  overscroll-behavior-x:contain!important;
}
body[data-v163-module="operativo"] #operativoNav::-webkit-scrollbar,
body[data-v163-module="analysis"] #analysisNav::-webkit-scrollbar{display:none!important}

body[data-v163-module="operativo"] #operativoNav>button,
body[data-v163-module="analysis"] #analysisNav>button{
  position:relative!important;
  display:flex!important;
  flex:0 0 112px!important;
  width:112px!important;
  min-width:112px!important;
  max-width:112px!important;
  min-height:82px!important;
  height:82px!important;
  max-height:none!important;
  margin:0!important;
  padding:8px 7px 10px!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  border:1px solid var(--v212-line)!important;
  border-radius:18px!important;
  background:rgba(255,255,255,.96)!important;
  color:#55718d!important;
  box-shadow:0 5px 18px rgba(28,72,116,.06)!important;
  transform:none!important;
  opacity:1!important;
  font-size:9px!important;
  line-height:1.15!important;
  font-weight:850!important;
  white-space:normal!important;
  text-align:center!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
  overflow:visible!important;
}
body[data-v163-module="operativo"] #operativoNav>button:hover,
body[data-v163-module="analysis"] #analysisNav>button:hover{
  transform:translateY(-1px)!important;
  border-color:#b7cfe7!important;
  box-shadow:0 8px 22px rgba(28,72,116,.10)!important;
}

/* Sólo una iconografía canónica por pestaña. */
body[data-v163-module="operativo"] #operativoNav .v166-tab-icon,
body[data-v163-module="analysis"] #analysisNav .v166-tab-icon,
body[data-v163-module="operativo"] #operativoNav .rt-tab-icon,
body[data-v163-module="analysis"] #analysisNav .rt-tab-icon,
body[data-v163-module="operativo"] #operativoNav .rt-tab-label,
body[data-v163-module="analysis"] #analysisNav .rt-tab-label{
  display:none!important;
}

body[data-v163-module="operativo"] #operativoNav .v206-tab-icon,
body[data-v163-module="analysis"] #analysisNav .v206-tab-icon{
  display:grid!important;
  place-items:center!important;
  flex:0 0 38px!important;
  width:38px!important;
  min-width:38px!important;
  max-width:38px!important;
  height:38px!important;
  min-height:38px!important;
  max-height:38px!important;
  margin:0!important;
  padding:0!important;
  border:1px solid #dce8f4!important;
  border-radius:13px!important;
  background:#edf5fd!important;
  color:#567c9f!important;
  box-shadow:none!important;
}
body[data-v163-module="operativo"] #operativoNav .v206-tab-icon svg,
body[data-v163-module="analysis"] #analysisNav .v206-tab-icon svg{
  display:block!important;
  width:21px!important;
  height:21px!important;
  max-width:21px!important;
  max-height:21px!important;
  stroke:currentColor!important;
  fill:none!important;
}
body[data-v163-module="operativo"] #operativoNav .v206-tab-label,
body[data-v163-module="analysis"] #analysisNav .v206-tab-label{
  position:static!important;
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  height:auto!important;
  min-height:0!important;
  margin:0!important;
  padding:0!important;
  overflow:visible!important;
  clip:auto!important;
  clip-path:none!important;
  white-space:normal!important;
  text-overflow:clip!important;
  color:inherit!important;
  font-size:9px!important;
  line-height:1.12!important;
  font-weight:850!important;
  text-align:center!important;
  opacity:1!important;
}

/* Activo idéntico al lenguaje de Operación. */
body[data-v163-module="operativo"] #operativoNav>button.active,
body[data-v163-module="analysis"] #analysisNav>button.active,
body[data-v163-module="operativo"] #operativoNav>button[aria-selected="true"],
body[data-v163-module="analysis"] #analysisNav>button[aria-selected="true"]{
  color:#fff!important;
  border-color:#0a5da7!important;
  background:linear-gradient(145deg,var(--v212-navy) 0%,var(--v212-blue) 100%)!important;
  box-shadow:0 12px 28px rgba(13,79,139,.24)!important;
  transform:translateY(-2px)!important;
}
body[data-v163-module="operativo"] #operativoNav>button.active .v206-tab-icon,
body[data-v163-module="analysis"] #analysisNav>button.active .v206-tab-icon,
body[data-v163-module="operativo"] #operativoNav>button[aria-selected="true"] .v206-tab-icon,
body[data-v163-module="analysis"] #analysisNav>button[aria-selected="true"] .v206-tab-icon{
  background:rgba(255,255,255,.14)!important;
  border-color:rgba(255,255,255,.22)!important;
  color:#fff!important;
}
body[data-v163-module="operativo"] #operativoNav>button.active:after,
body[data-v163-module="analysis"] #analysisNav>button.active:after,
body[data-v163-module="operativo"] #operativoNav>button[aria-selected="true"]:after,
body[data-v163-module="analysis"] #analysisNav>button[aria-selected="true"]:after{
  content:""!important;
  display:block!important;
  position:absolute!important;
  left:50%!important;
  right:auto!important;
  top:auto!important;
  bottom:-7px!important;
  width:32px!important;
  height:4px!important;
  border-radius:999px!important;
  background:#1185ef!important;
  transform:translateX(-50%)!important;
  box-shadow:0 2px 7px rgba(17,133,239,.24)!important;
}

/* La configuración de Pestañas visibles sigue mandando. */
#operativoNav>button.hidden,#analysisNav>button.hidden,
#operativoNav>button[hidden],#analysisNav>button[hidden]{
  display:none!important;
}

/* Quitar restos visuales del carrusel anterior. */
.rt-icon-rail-v1-current,
.rt-icon-rail-v1-indicator{display:none!important}
.rt-icon-rail-v1-shell{width:100%!important;max-width:100%!important;margin:0!important;padding:0!important}
.rt-icon-rail-v1-shell:before,.rt-icon-rail-v1-shell:after{display:none!important;content:none!important}

/* Título contextual: pestañas -> título -> filtros -> contenido. */
body[data-v163-module="operativo"] #v207Context-cm,
body[data-v163-module="analysis"] #v207Context-analysis{
  margin:5px 0 10px!important;
}

/* ============================================================
   FILTRO ÚNICO DE ANÁLISIS, DEBAJO DE LAS PESTAÑAS
   ============================================================ */
body[data-v163-module="analysis"] #v161FilterBar,
body[data-v163-module="analysis"] #globalFilters{
  display:none!important;
}
#v212AnalysisFilterCard{
  display:none;
  width:100%;
  max-width:100%;
  margin:8px 0 12px;
  padding:0;
  border:1px solid var(--v212-line);
  border-radius:18px;
  background:#fff;
  box-shadow:0 8px 24px rgba(14,79,139,.08);
  overflow:hidden;
}
body[data-v163-module="analysis"] #v212AnalysisFilterCard.on{display:block}
#v212AnalysisFilterCard .v212-filter-head{
  min-height:56px;
  display:flex;
  align-items:center;
  gap:11px;
  padding:10px 14px;
  color:#fff;
  background:linear-gradient(135deg,#103f72,#0878df);
}
.v212-filter-head-icon{
  width:34px;height:34px;min-width:34px;border-radius:10px;
  display:grid;place-items:center;background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.12);
}
.v212-filter-head-icon svg{width:18px;height:18px;stroke:currentColor;fill:none}
.v212-filter-head b{display:block;font-size:12px;font-weight:950;line-height:1.1}
.v212-filter-head small{display:block;margin-top:3px;font-size:8px;font-weight:700;opacity:.84}
.v212-filter-grid{
  display:grid;
  grid-template-columns:repeat(5,minmax(120px,1fr)) auto;
  gap:8px;
  align-items:end;
  padding:12px 13px 13px;
}
.v212-field{position:relative;min-width:0}
.v212-field label{
  display:block;margin:0 0 5px 2px;color:#61758b;
  font-size:8px;font-weight:950;text-transform:uppercase;letter-spacing:.04em;
}
.v212-field select{
  width:100%;height:44px;min-width:0;
  border:1px solid #cbd9e8;border-radius:12px;background:#fbfdff;
  color:var(--v212-ink);padding:7px 30px 7px 10px;
  font-size:10px;font-weight:850;outline:none;
}
.v212-filter-apply{
  height:44px;min-width:126px;padding:0 18px;border:0;border-radius:12px;
  background:linear-gradient(135deg,#176fe8,#0a83ef);
  color:#fff;font-size:9px;font-weight:950;cursor:pointer;
  box-shadow:0 8px 18px rgba(23,111,232,.18);
}

/* ============================================================
   MÓVIL: MISMO TAMAÑO/PATRÓN DE OPERACIÓN
   ============================================================ */
@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav:not(.hidden),
  body[data-v163-module="analysis"] #analysisNav:not(.hidden){
    gap:8px!important;
    width:auto!important;
    max-width:none!important;
    min-height:92px!important;
    margin-left:-13px!important;
    margin-right:-13px!important;
    padding:7px max(14px,calc((100vw - 112px)/2)) 13px!important;
    scroll-padding-inline:calc((100vw - 112px)/2)!important;
  }
  body[data-v163-module="operativo"] #operativoNav>button,
  body[data-v163-module="analysis"] #analysisNav>button{
    flex:0 0 112px!important;
    width:112px!important;
    min-width:112px!important;
    max-width:112px!important;
    min-height:76px!important;
    height:76px!important;
    border-radius:17px!important;
    font-size:8.2px!important;
    padding:7px 6px 9px!important;
  }
  body[data-v163-module="operativo"] #operativoNav .v206-tab-icon,
  body[data-v163-module="analysis"] #analysisNav .v206-tab-icon{
    width:34px!important;min-width:34px!important;max-width:34px!important;
    height:34px!important;min-height:34px!important;max-height:34px!important;
    flex-basis:34px!important;border-radius:12px!important;
  }
  body[data-v163-module="operativo"] #operativoNav .v206-tab-icon svg,
  body[data-v163-module="analysis"] #analysisNav .v206-tab-icon svg{
    width:19px!important;height:19px!important;
  }
  body[data-v163-module="operativo"] #operativoNav .v206-tab-label,
  body[data-v163-module="analysis"] #analysisNav .v206-tab-label{
    font-size:8.2px!important;
  }

  #v212AnalysisFilterCard{border-radius:15px;margin:7px 0 11px}
  #v212AnalysisFilterCard .v212-filter-head{min-height:54px;padding:9px 11px}
  .v212-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:10px}
  .v212-field select{height:43px;font-size:12px}
  .v212-filter-apply{grid-column:1/-1;width:100%;height:44px;font-size:11px}
}
@media(max-width:390px){
  .v212-filter-grid{grid-template-columns:1fr 1fr}
}
</style>"""

    js = r"""<script id="v212-operation-style-analysis-filters-js">
(function(){
  if(window.__V212_OPERATION_STYLE_ANALYSIS_FILTERS)return;
  window.__V212_OPERATION_STYLE_ANALYSIS_FILTERS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const norm=v=>String(v||'').replace(/\s+/g,' ').trim().toLowerCase();

  const icons={
    center:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    conversion:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/></svg>',
    money:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M16 8.5c-.8-.7-1.9-1-3.2-1-1.8 0-3.1.9-3.1 2.3 0 3.2 6.3 1.5 6.3 4.6 0 1.4-1.3 2.4-3.2 2.4-1.4 0-2.6-.4-3.5-1.2M12.8 5.5v13"/></svg>',
    store:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/></svg>',
    chart:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="m4 8 6-5 6 8 5-4"/></svg>',
    route:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 19c3-6 11-5 14-12"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="7" r="2"/></svg>',
    target:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/></svg>',
    alert:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>',
    upload:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 20h14"/></svg>',
    settings:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6.2L14.7 4h-4l-.3 2.2a8 8 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 1.5.9l.3 2.2h4l.3-2.2a8 8 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/></svg>',
    accordion:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="4" rx="1.5"/><rect x="3" y="17" width="18" height="3" rx="1.5"/></svg>',
    grid:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    pin:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z"/><circle cx="12" cy="10" r="2"/></svg>',
    checklist:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 5h10M9 12h10M9 19h10"/><path d="m3 5 1.2 1.2L6.5 4M3 12l1.2 1.2L6.5 11M3 19l1.2 1.2L6.5 18"/></svg>',
    more:'<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>'
  };

  function moduleName(){return norm(document.body.dataset.v163Module||'')}

  function metaFor(btn,kind){
    if(kind==='cm'){
      const key=String(btn.dataset.tabKey||'');
      const op=norm(btn.dataset.opview||'');
      if(key==='operations.center'||op==='centro ejecutivo')return['Centro Operativo','center'];
      if(key==='operations.conversion')return['Conversión','conversion'];
      if(key==='operations.recovery')return['Recuperación $','money'];
      if(key==='operations.recovery_store')return['Recuperación por Tienda','store'];
      if(key==='operations.productivity')return['Productividad','chart'];
      if(key==='operations.routes')return['Recorridos','route'];
      if(key==='operations.score')return['Score','target'];
      if(key==='operations.alerts')return['Alertas','alert'];
      if(btn.id==='openGoalsBtn')return['Metas y tiendas','settings'];
      if(op==='carga de datos')return['Carga de datos','upload'];
      const label=btn.querySelector('.v206-tab-label')?.textContent||btn.textContent||'';
      return[label.trim(), 'chart'];
    }
    const sub=String(btn.dataset.sub||'');
    const map={
      'macro':['Macro Compañía','chart'],
      'accordion':['Acordeón Comercial','accordion'],
      'stores':['Tiendas','store'],
      'sections':['Sección / Rubro','grid'],
      'areas':['Ubicación / Área','pin'],
      'lingerie-checklist':['Checklist Lencería','checklist'],
      'more':['Más opciones','more'],
      'analysis-upload':['Carga de datos','upload']
    };
    const label=btn.querySelector('.v206-tab-label')?.textContent||btn.textContent||'';
    return map[sub]||[label.trim(),'grid'];
  }

  function neutralizeOldRail(host){
    if(!host)return;
    host.classList.remove('rt-icon-rail-v1','rt-icon-has-user-selection');
    qa(':scope > button',host).forEach(b=>b.classList.remove('rt-icon-user-active'));
    const shell=host.parentElement;
    if(shell?.classList?.contains('rt-icon-rail-v1-shell')){
      shell.parentNode?.insertBefore(host,shell);
      shell.remove();
    }
  }

  function decorateNav(host,kind){
    if(!host)return;
    neutralizeOldRail(host);
    qa(':scope > button',host).forEach(btn=>{
      if(kind==='cm' && (btn.dataset.tabKey==='operations.productivity_capture'||btn.dataset.opview==='Cargar productividad')){
        btn.hidden=true;btn.classList.add('hidden');btn.setAttribute('aria-hidden','true');return;
      }
      const [label,iconKey]=metaFor(btn,kind);
      let icon=q(':scope > .v206-tab-icon',btn);
      let text=q(':scope > .v206-tab-label',btn);
      if(!icon){icon=document.createElement('span');icon.className='v206-tab-icon';icon.setAttribute('aria-hidden','true');btn.prepend(icon)}
      if(!text){text=document.createElement('span');text.className='v206-tab-label';btn.append(text)}
      if(icon.dataset.v212Icon!==iconKey){icon.innerHTML=icons[iconKey]||icons.grid;icon.dataset.v212Icon=iconKey}
      if(text.textContent!==label)text.textContent=label;
      btn.title=label;
      btn.dataset.v212Decorated='1';
    });
  }

  function copyOptions(src,dst){
    if(!src||!dst)return;
    const sig=[...src.options].map(o=>o.value+'|'+o.text).join('¦');
    if(dst.dataset.v212sig!==sig){
      dst.innerHTML='';
      [...src.options].forEach(o=>dst.add(new Option(o.text,o.value)));
      dst.dataset.v212sig=sig;
    }
    if([...dst.options].some(o=>o.value===src.value))dst.value=src.value;
  }

  function ensureFilterCard(){
    let card=q('#v212AnalysisFilterCard');
    if(!card){
      card=document.createElement('section');
      card.id='v212AnalysisFilterCard';
      card.innerHTML=
        '<div class="v212-filter-head">'+
          '<span class="v212-filter-head-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h16M7 12h10m-7 7h4"/></svg></span>'+
          '<div><b>Filtros del reporte</b><small>Define la vista comercial antes de consultar</small></div>'+
        '</div>'+
        '<div class="v212-filter-grid" id="v212AnalysisFilterGrid">'+
          '<div class="v212-field"><label>Periodo</label><select id="v212AnalysisPeriod"></select></div>'+
          '<div class="v212-field"><label>Tienda</label><select id="v212AnalysisStore"></select></div>'+
          '<div class="v212-field"><label>Sección</label><select id="v212AnalysisSection"></select></div>'+
          '<div class="v212-field"><label>Catálogo</label><select id="v212AnalysisCatalog"></select></div>'+
          '<div class="v212-field" id="v166StatusField"><label>Estatus</label><select id="v166StatusSelect"><option>Todos</option></select></div>'+
          '<button type="button" class="v212-filter-apply" id="v212AnalysisApply">Consultar</button>'+
        '</div>';
    }
    const header=q('#v207Context-analysis');
    const nav=q('#analysisNav');
    const anchor=header||nav;
    if(anchor && card.previousElementSibling!==anchor)anchor.insertAdjacentElement('afterend',card);
    return card;
  }

  async function loadStatus(){
    const ss=q('#v166StatusSelect'),period=q('#week')?.value||'';
    if(!ss||ss.dataset.loadedFor===String(period))return;
    try{
      let d;
      if(typeof api==='function')d=await api('/api/commercial/status-options-v166?week='+encodeURIComponent(period),{timeoutMs:60000});
      else{
        const r=await fetch('/api/commercial/status-options-v166?week='+encodeURIComponent(period),{credentials:'same-origin'});
        d=await r.json();
      }
      const cur=ss.value||'Todos';
      ss.innerHTML='';
      ['Todos',...(d.values||[])].forEach(x=>ss.add(new Option(x,x)));
      if([...ss.options].some(o=>o.value===cur))ss.value=cur;
      ss.dataset.loadedFor=String(period);
    }catch(e){console.warn('[V212] estatus comercial',e)}
  }

  function syncNative(id,source){
    const dst=q(id),src=q(source);
    if(dst&&src&&[...dst.options].some(o=>o.value===src.value))dst.value=src.value;
  }

  function bindFilter(card){
    if(card.dataset.v212Bound==='1')return;
    card.dataset.v212Bound='1';
    q('#v212AnalysisPeriod')?.addEventListener('change',e=>{
      const native=q('#week');if(native){native.value=e.target.value;native.dispatchEvent(new Event('change',{bubbles:true}))}
      const ss=q('#v166StatusSelect');if(ss)ss.dataset.loadedFor='';
      setTimeout(loadStatus,40);
    });
    q('#v212AnalysisStore')?.addEventListener('change',e=>{const x=q('#store');if(x)x.value=e.target.value});
    q('#v212AnalysisSection')?.addEventListener('change',e=>{const x=q('#section');if(x)x.value=e.target.value});
    q('#v212AnalysisCatalog')?.addEventListener('change',e=>{const x=q('#catalog');if(x)x.value=e.target.value});
    q('#v212AnalysisApply')?.addEventListener('click',()=>{
      syncNative('#week','#v212AnalysisPeriod');
      syncNative('#store','#v212AnalysisStore');
      syncNative('#section','#v212AnalysisSection');
      syncNative('#catalog','#v212AnalysisCatalog');
      const b=q('#refresh');
      if(b)b.click();
      else if(typeof window.loadDash==='function')window.loadDash();
    });
  }

  async function refreshAnalysisFilter(){
    const card=ensureFilterCard();
    if(moduleName()!=='analysis'){card.classList.remove('on');return}
    const sub=String(q('#analysisNav>button.active')?.dataset.sub||'');
    if(sub==='analysis-upload'){card.classList.remove('on');return}
    copyOptions(q('#week'),q('#v212AnalysisPeriod'));
    copyOptions(q('#store'),q('#v212AnalysisStore'));
    copyOptions(q('#section'),q('#v212AnalysisSection'));
    copyOptions(q('#catalog'),q('#v212AnalysisCatalog'));
    bindFilter(card);
    card.classList.add('on');
    await loadStatus();
  }

  function refresh(){
    decorateNav(q('#operativoNav'),'cm');
    decorateNav(q('#analysisNav'),'analysis');
    refreshAnalysisFilter();
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button')){
      [20,100,300,700].forEach(ms=>setTimeout(refresh,ms));
    }
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(refresh,30));
  document.addEventListener('change',e=>{
    if(e.target?.matches?.('#week,#store,#section,#catalog'))setTimeout(refreshAnalysisFilter,70);
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});
  else refresh();
  [120,420,1000,2100].forEach(ms=>setTimeout(refresh,ms));
  window.addEventListener('pageshow',()=>setTimeout(refresh,60),{passive:true});
  window.addEventListener('resize',()=>setTimeout(refresh,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(refresh,120),{passive:true});

  console.info('[V212] pestañas tipo Operación + filtros comerciales debajo de pestañas activos.');
})();
</script>"""

    @m.app.middleware("http")
    async def v212_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v212-operation-style-analysis-filters-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v212-operation-style-analysis-filters-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V212",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V212] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V212_OPERATION_STYLE_ANALYSIS_FILTERS=True
    print("[V212] navegación tipo Operación + filtros comerciales debajo de pestañas.",flush=True)
