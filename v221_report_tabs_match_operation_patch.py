"""V221 · Cambios y Muertos + Análisis Comercial usan el dock de Operación.

Objetivo:
- reemplazar el carrusel/icon rail anterior por las mismas tarjetas de Operación;
- una sola línea siempre;
- tamaño automático según pestañas visibles y ancho real;
- mismo estado activo azul, icono + nombre;
- respeta orden, permisos, hidden y configuración de Pestañas visibles;
- no toca renderizadores, filtros, cálculos, carga de datos ni endpoints.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V221_REPORT_TABS_MATCH_OPERATION", False):
        return

    css = r"""<style id="v221-report-tabs-match-operation-css">
/* Retira restos visuales de los carruseles históricos si quedaron en DOM. */
.rt-carousel-shell.v221-report-shell{
  width:100%!important;
  max-width:100%!important;
  margin:0!important;
  padding:0!important;
  background:transparent!important;
  border:0!important;
  box-shadow:none!important;
}
.rt-carousel-shell.v221-report-shell>.rt-carousel-arrow,
.rt-carousel-shell.v221-report-shell>.rt-icon-rail-v1-current,
.rt-carousel-shell.v221-report-shell>.rt-icon-rail-v1-indicator,
.rt-carousel-shell.v221-report-shell>.rt-worldcup-current,
.rt-carousel-shell.v221-report-shell>.rt-worldcup-pedestal,
.rt-carousel-shell.v221-report-shell>.rt-mundial-current,
.rt-carousel-shell.v221-report-shell>.rt-m7-current{
  display:none!important;
}
.rt-carousel-shell.v221-report-shell::before,
.rt-carousel-shell.v221-report-shell::after{
  display:none!important;
  content:none!important;
}

/* Ocultamiento por módulo sigue siendo autoritativo. */
body[data-v163-module="operativo"] #analysisNav,
body[data-v163-module="analysis"] #operativoNav,
body[data-v163-module="operation"] :is(#operativoNav,#analysisNav),
body[data-v163-module="users"] :is(#operativoNav,#analysisNav),
body[data-v163-module="share"] :is(#operativoNav,#analysisNav),
#operativoNav.hidden,#analysisNav.hidden{
  display:none!important;
}

/* ==========================================================
   MISMO DOCK VISUAL DE OPERACIÓN
   ========================================================== */
body[data-v163-module="operativo"] #operativoNav:not(.hidden),
body[data-v163-module="analysis"] #analysisNav:not(.hidden){
  --v221-count:5;
  --v221-gap:4px;
  --v221-tab-h:64px;
  --v221-icon:27px;
  --v221-font:8px;
  --v221-radius:13px;
  display:grid!important;
  grid-template-columns:repeat(var(--v221-count),minmax(0,1fr))!important;
  grid-auto-flow:column!important;
  gap:var(--v221-gap)!important;
  align-items:stretch!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  min-height:0!important;
  height:auto!important;
  margin:3px 0 8px!important;
  padding:5px 0 9px!important;
  overflow:visible!important;
  overflow-x:visible!important;
  overflow-y:visible!important;
  white-space:normal!important;
  border:0!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
  scroll-snap-type:none!important;
  scroll-padding:0!important;
  touch-action:auto!important;
}

/* Todas las pestañas conservan exactamente el mismo tamaño, incluida la activa. */
body[data-v163-module="operativo"] #operativoNav>button,
body[data-v163-module="analysis"] #analysisNav>button,
body[data-v163-module="operativo"] #operativoNav>button.active,
body[data-v163-module="analysis"] #analysisNav>button.active,
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.rt-icon-user-active{
  position:relative!important;
  display:flex!important;
  flex:initial!important;
  flex-basis:auto!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:3px!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  min-height:var(--v221-tab-h)!important;
  height:var(--v221-tab-h)!important;
  max-height:var(--v221-tab-h)!important;
  margin:0!important;
  padding:4px 2px 6px!important;
  overflow:visible!important;
  border:1px solid #d6e3f0!important;
  border-radius:var(--v221-radius)!important;
  background:rgba(255,255,255,.96)!important;
  color:#55718d!important;
  opacity:1!important;
  box-shadow:0 5px 18px rgba(28,72,116,.06)!important;
  transform:none!important;
  white-space:normal!important;
  text-align:center!important;
  font-size:var(--v221-font)!important;
  line-height:1.02!important;
  scroll-snap-align:none!important;
}

/* Icono igual al de Operación. */
body[data-v163-module] :is(#operativoNav,#analysisNav) .rt-tab-icon{
  display:grid!important;
  place-items:center!important;
  flex:0 0 var(--v221-icon)!important;
  width:var(--v221-icon)!important;
  min-width:var(--v221-icon)!important;
  max-width:var(--v221-icon)!important;
  height:var(--v221-icon)!important;
  min-height:var(--v221-icon)!important;
  max-height:var(--v221-icon)!important;
  margin:0!important;
  padding:0!important;
  border:1px solid #dce8f4!important;
  border-radius:calc(var(--v221-radius) - 3px)!important;
  background:#edf5fd!important;
  color:#567c9f!important;
  box-shadow:none!important;
  transform:none!important;
  opacity:1!important;
  visibility:visible!important;
  pointer-events:none!important;
}
body[data-v163-module] :is(#operativoNav,#analysisNav) .rt-tab-icon svg{
  display:block!important;
  width:calc(var(--v221-icon) * .57)!important;
  height:calc(var(--v221-icon) * .57)!important;
  max-width:calc(var(--v221-icon) * .57)!important;
  max-height:calc(var(--v221-icon) * .57)!important;
  stroke:currentColor!important;
  fill:none!important;
}

/* Nombre dentro de cada tarjeta, nunca en una banda aparte. */
body[data-v163-module] :is(#operativoNav,#analysisNav) .rt-tab-label{
  position:static!important;
  display:-webkit-box!important;
  -webkit-box-orient:vertical!important;
  -webkit-line-clamp:var(--v221-lines,2)!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  height:auto!important;
  min-height:0!important;
  margin:0!important;
  padding:0!important;
  overflow:hidden!important;
  clip:auto!important;
  clip-path:none!important;
  color:inherit!important;
  font-size:var(--v221-font)!important;
  line-height:1.02!important;
  font-weight:850!important;
  letter-spacing:0!important;
  white-space:normal!important;
  text-align:center!important;
  text-overflow:ellipsis!important;
  overflow-wrap:anywhere!important;
  pointer-events:none!important;
}

/* Activa = mismo gradiente y subrayado que Operación, SIN crecer. */
body[data-v163-module="operativo"] #operativoNav>button.active,
body[data-v163-module="analysis"] #analysisNav>button.active,
body[data-v163-module="operativo"] #operativoNav>button[aria-selected="true"],
body[data-v163-module="analysis"] #analysisNav>button[aria-selected="true"],
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.rt-icon-user-active{
  color:#fff!important;
  border-color:#0a5da7!important;
  background:linear-gradient(145deg,#0d4f8b 0%,#0878df 100%)!important;
  box-shadow:0 10px 24px rgba(13,79,139,.22)!important;
  transform:translateY(-1px)!important;
}
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.active .rt-tab-icon,
body[data-v163-module] :is(#operativoNav,#analysisNav)>button[aria-selected="true"] .rt-tab-icon,
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.rt-icon-user-active .rt-tab-icon{
  background:rgba(255,255,255,.14)!important;
  border-color:rgba(255,255,255,.22)!important;
  color:#fff!important;
  width:var(--v221-icon)!important;
  height:var(--v221-icon)!important;
  min-width:var(--v221-icon)!important;
  max-width:var(--v221-icon)!important;
  transform:none!important;
}
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.active::after,
body[data-v163-module] :is(#operativoNav,#analysisNav)>button[aria-selected="true"]::after,
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.rt-icon-user-active::after{
  content:""!important;
  display:block!important;
  position:absolute!important;
  left:50%!important;
  bottom:-6px!important;
  width:min(28px,70%)!important;
  height:3px!important;
  transform:translateX(-50%)!important;
  border-radius:999px!important;
  background:#1185ef!important;
  box-shadow:0 2px 7px rgba(17,133,239,.24)!important;
}

/* Lo ocultado por permisos/configuración no ocupa columna ni cuenta. */
body[data-v163-module] :is(#operativoNav,#analysisNav)>button.hidden,
body[data-v163-module] :is(#operativoNav,#analysisNav)>button[hidden],
body[data-v163-module] :is(#operativoNav,#analysisNav)>button[aria-hidden="true"]{
  display:none!important;
}

/* Neutraliza por completo presentación del icon rail anterior. */
body[data-v163-module] :is(#operativoNav,#analysisNav).rt-icon-rail-v1{
  border:0!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
}

/* En cualquier orientación o dispositivo sigue siendo una sola línea. */
@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav:not(.hidden),
  body[data-v163-module="analysis"] #analysisNav:not(.hidden){
    display:grid!important;
    grid-template-columns:repeat(var(--v221-count),minmax(0,1fr))!important;
    grid-auto-flow:column!important;
    gap:var(--v221-gap)!important;
    width:100%!important;
    max-width:100%!important;
    margin-left:0!important;
    margin-right:0!important;
    padding-left:0!important;
    padding-right:0!important;
    overflow:visible!important;
    overflow-x:visible!important;
    overflow-y:visible!important;
    scroll-snap-type:none!important;
    scroll-padding-inline:0!important;
  }
}

/* Título/indicador que pertenecía al carrusel de iconos: ya no existe. */
.rt-icon-rail-v1-current,
.rt-icon-rail-v1-indicator{
  display:none!important;
}

/* V221.2 · ningún decorador anterior puede agregar un segundo icono. */
body[data-v163-module] :is(#operativoNav,#analysisNav) :is(.v164-tab-icon,.v166-tab-icon,.v206-tab-icon,.v217-tab-icon){
  display:none!important;
}

/* Cuando no caben con un tamaño legible, una sola fila desplazable con el dedo. */
body[data-v163-module] :is(#operativoNav,#analysisNav)[data-v221-scroll="1"]{
  display:flex!important;
  grid-template-columns:none!important;
  grid-auto-flow:unset!important;
  flex-wrap:nowrap!important;
  justify-content:flex-start!important;
  align-items:stretch!important;
  gap:var(--v221-gap,7px)!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  overscroll-behavior-x:contain!important;
  -webkit-overflow-scrolling:touch!important;
  scroll-snap-type:x proximity!important;
  scroll-padding-inline:8px!important;
  touch-action:pan-x pan-y!important;
  padding-left:2px!important;
  padding-right:2px!important;
  scrollbar-width:none!important;
}
body[data-v163-module] :is(#operativoNav,#analysisNav)[data-v221-scroll="1"]::-webkit-scrollbar{
  display:none!important;
}
body[data-v163-module] :is(#operativoNav,#analysisNav)[data-v221-scroll="1"]>button{
  flex:0 0 var(--v221-card-w,88px)!important;
  width:var(--v221-card-w,88px)!important;
  min-width:var(--v221-card-w,88px)!important;
  max-width:var(--v221-card-w,88px)!important;
  scroll-snap-align:center!important;
}

/* Nunca permitir que una tarjeta invada a la siguiente. */
body[data-v163-module] :is(#operativoNav,#analysisNav)>button{
  box-sizing:border-box!important;
  isolation:isolate!important;
}
body[data-v163-module] :is(#operativoNav,#analysisNav)>button>*{
  max-width:100%!important;
}
</style>"""

    js = r"""<script id="v221-report-tabs-match-operation-js">
(function(){
  if(window.__V221_REPORT_TABS_MATCH_OPERATION)return;
  window.__V221_REPORT_TABS_MATCH_OPERATION=true;

  const qs=(s,r=document)=>r.querySelector(s);
  const qsa=(s,r=document)=>[...r.querySelectorAll(s)];
  const clamp=(min,v,max)=>Math.max(min,Math.min(max,v));

  const META={
    'operations.center':['Centro Operativo','dashboard'],
    'operations.conversion':['Conversión','repeat'],
    'operations.recovery':['Recuperación $','dollar'],
    'operations.recovery_store':['Recuperación por Tienda','store'],
    'operations.productivity':['Productividad','chart'],
    'operations.routes':['Recorridos','route'],
    'operations.score':['Score','target'],
    'operations.alerts':['Alertas','bell'],
    'commercial.macro':['Macro Compañía','chart'],
    'commercial.accordion':['Acordeón Comercial','accordion'],
    'commercial.stores':['Tiendas','building'],
    'commercial.sections':['Sección / Rubro','grid'],
    'commercial.areas':['Ubicación / Área','pin'],
    'commercial.lingerie_checklist':['Checklist Lencería','checklist'],
    'commercial.sellthrough':['Sell Through','percent'],
    'commercial.more':['Más opciones','more'],
    'commercial.upload':['Carga de datos','upload']
  };

  const PATHS={
    dashboard:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    repeat:'<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h18"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    dollar:'<circle cx="12" cy="12" r="9"/><path d="M12 6v12M15.5 8.5c-.8-.7-1.8-1-3-1-1.8 0-3 .9-3 2.2 0 3 6 1.5 6 4.5 0 1.4-1.3 2.3-3.1 2.3-1.3 0-2.5-.4-3.4-1.2"/>',
    store:'<path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/>',
    chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="m4 8 6-5 6 8 5-4"/>',
    route:'<path d="M5 19c3-6 11-5 14-12"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="7" r="2"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    accordion:'<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="4" rx="1.5"/><rect x="3" y="17" width="18" height="3" rx="1.5"/>',
    building:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h2M14 7h2M8 11h2M14 11h2M8 15h2M14 15h2M9 21v-3h6v3"/>',
    grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    pin:'<path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z"/><circle cx="12" cy="10" r="2"/>',
    checklist:'<path d="M9 5h10M9 12h10M9 19h10"/><path d="m3 5 1.2 1.2L6.5 4M3 12l1.2 1.2L6.5 11M3 19l1.2 1.2L6.5 18"/>',
    percent:'<path d="m19 5-14 14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    more:'<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>',
    upload:'<path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 20h14"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6.2L14.7 4h-4l-.3 2.2a8 8 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 1.5.9l.3 2.2h4l.3-2.2a8 8 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/>'
  };

  function svg(name){
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(PATHS[name]||PATHS.chart)+'</svg>';
  }

  function meta(btn){
    const key=String(btn.dataset.tabKey||'');
    if(META[key])return META[key];

    const op=String(btn.dataset.opview||'').toLowerCase();
    const sub=String(btn.dataset.sub||'').toLowerCase();
    const txt=String(btn.dataset.rtLabel||btn.textContent||btn.title||'').replace(/\s+/g,' ').trim();

    if(btn.id==='openGoalsBtn'||op.includes('metas'))return['Metas y tiendas','settings'];
    if(op.includes('carga de datos'))return['Carga de datos','upload'];
    if(op.includes('convers'))return['Conversión','repeat'];
    if(op.includes('recuperación económica')||op.includes('recuperacion economica'))return['Recuperación $','dollar'];
    if(op.includes('recuperación por tienda')||op.includes('recuperacion por tienda'))return['Recuperación por Tienda','store'];
    if(op.includes('productividad'))return['Productividad','chart'];
    if(op.includes('recorridos'))return['Recorridos','route'];
    if(op.includes('índice')||op.includes('indice')||op.includes('score'))return['Score','target'];
    if(op.includes('alerta'))return['Alertas','bell'];

    if(sub==='macro')return['Macro Compañía','chart'];
    if(sub==='accordion')return['Acordeón Comercial','accordion'];
    if(sub==='stores')return['Tiendas','building'];
    if(sub==='sections')return['Sección / Rubro','grid'];
    if(sub==='areas')return['Ubicación / Área','pin'];
    if(sub==='lingerie-checklist')return['Checklist Lencería','checklist'];
    if(sub.includes('sell'))return[txt||'Sell Through','percent'];
    if(sub==='more')return['Más opciones','more'];
    if(sub==='analysis-upload')return['Carga de datos','upload'];

    if(/sell through/i.test(txt))return[txt,'percent'];
    return[txt||'Reporte','chart'];
  }

  function visible(btn){
    if(!btn||btn.hidden||btn.classList.contains('hidden')||btn.getAttribute('aria-hidden')==='true')return false;
    const cs=getComputedStyle(btn);
    return cs.display!=='none'&&cs.visibility!=='hidden';
  }

  function cleanLegacy(host){
    // El carrusel histórico podía envolver cada navegación en un shell.
    // Lo retiramos por completo: cada reporte conserva su barra original.
    const shell=host.closest('.rt-carousel-shell');
    if(shell&&shell.parentNode){
      shell.parentNode.insertBefore(host,shell);
      shell.remove();
    }

    host.classList.remove(
      'rt-carousel','rt-icon-rail-v1','rt-icon-has-user-selection',
      'rt-mundial-stage','rt-mundial-v6','rt-mundial-v7'
    );
    host.querySelectorAll(':scope > button.rt-icon-user-active').forEach(b=>b.classList.remove('rt-icon-user-active'));
    host.style.removeProperty('--rt-edge-pad');
    host.style.removeProperty('scroll-behavior');
    host.scrollLeft=0;
  }

  function currentModule(){
    const active=document.querySelector('.side [data-main].active') ||
      document.querySelector('#mobileMainNav [data-main].active');
    const dm=String(active?.dataset?.main||'').toLowerCase();
    if(['operativo','analysis','operation','users','share'].includes(dm))return dm;
    const tagged=String(document.body.dataset.v163Module||'').toLowerCase();
    if(tagged)return tagged;
    return '';
  }

  function hideForeignHost(host){
    if(!host)return;
    host.style.setProperty('display','none','important');
    const shell=host.closest('.rt-carousel-shell');
    if(shell)shell.style.setProperty('display','none','important');
  }

  function decorate(host){
    qsa(':scope > button',host).forEach(btn=>{
      if(btn.dataset.v221Decorating==='1')return;
      const [label,icon]=meta(btn);
      const currentLabel=btn.querySelector(':scope > .rt-tab-label')?.textContent?.trim();
      const currentIcon=btn.dataset.v221Icon;
      if(currentLabel===label&&currentIcon===icon)return;
      btn.dataset.v221Decorating='1';
      btn.querySelectorAll(':scope > .v164-tab-icon,:scope > .v166-tab-icon,:scope > .v206-tab-icon,:scope > .v217-tab-icon').forEach(x=>x.remove());
      btn.dataset.v221Icon=icon;
      btn.dataset.rtLabel=label;
      btn.title=label;
      btn.innerHTML='<span class="rt-tab-icon">'+svg(icon)+'</span><span class="rt-tab-label"></span>';
      const lab=btn.querySelector(':scope > .rt-tab-label');
      if(lab)lab.textContent=label;
      delete btn.dataset.v221Decorating;
    });
  }

  function fit(host){
    if(!host||!host.isConnected)return;
    const mod=currentModule();
    const owns=(host.id==='operativoNav'&&mod==='operativo') ||
      (host.id==='analysisNav'&&mod==='analysis');

    // CRÍTICO: V221 antes sólo hacía return. Como el host conservaba
    // display:grid!important de la vista previa, las pestañas terminaban
    // mezclándose entre C&M, Operación y Análisis.
    if(!owns){
      hideForeignHost(host);
      return;
    }

    cleanLegacy(host);
    host.classList.remove('hidden');
    host.removeAttribute('hidden');
    decorate(host);

    const tabs=qsa(':scope > button',host).filter(visible);
    const count=Math.max(1,tabs.length);
    const width=Math.max(280,host.clientWidth||host.getBoundingClientRect().width||window.innerWidth-24);
    const gap=count<=5?4:count<=7?6:7;
    const cell=Math.max(18,(width-gap*(count-1))/count);

    // No comprimir hasta volver ilegibles las tarjetas. Si no caben,
    // mantener una sola línea y habilitar swipe horizontal.
    const shouldScroll=count>5 && cell<78;
    const cardWidth=shouldScroll?clamp(82,width*.235,96):cell;
    const visualCell=shouldScroll?cardWidth:cell;

    const icon=clamp(22,visualCell*.36,30);
    const font=clamp(7.1,visualCell*.102,8.8);
    const height=clamp(58,visualCell*.78,68);
    const radius=clamp(11,visualCell*.16,14);
    const lines=2;

    host.dataset.v221Scroll=shouldScroll?'1':'0';
    host.style.setProperty('--v221-count',String(count));
    host.style.setProperty('--v221-gap',gap+'px');
    host.style.setProperty('--v221-card-w',cardWidth.toFixed(1)+'px');
    host.style.setProperty('--v221-icon',icon.toFixed(1)+'px');
    host.style.setProperty('--v221-font',font.toFixed(2)+'px');
    host.style.setProperty('--v221-tab-h',height.toFixed(1)+'px');
    host.style.setProperty('--v221-radius',radius.toFixed(1)+'px');
    host.style.setProperty('--v221-lines',String(lines));
    host.style.setProperty('width','100%','important');
    host.style.setProperty('max-width','100%','important');

    if(shouldScroll){
      host.style.setProperty('display','flex','important');
      host.style.removeProperty('grid-template-columns');
      host.style.removeProperty('grid-auto-flow');
      host.style.setProperty('flex-wrap','nowrap','important');
      host.style.setProperty('overflow-x','auto','important');
      host.style.setProperty('overflow-y','visible','important');
      host.style.setProperty('scroll-snap-type','x proximity','important');
      const active=tabs.find(b=>b.classList.contains('active')||b.getAttribute('aria-selected')==='true');
      if(active){
        requestAnimationFrame(()=>{
          try{active.scrollIntoView({behavior:'auto',block:'nearest',inline:'center'})}catch(_){}
        });
      }
    }else{
      host.style.setProperty('display','grid','important');
      host.style.setProperty('grid-template-columns','repeat('+count+',minmax(0,1fr))','important');
      host.style.setProperty('grid-auto-flow','column','important');
      host.style.setProperty('flex-wrap','nowrap','important');
      host.style.setProperty('overflow','visible','important');
      host.style.setProperty('overflow-x','visible','important');
      host.style.setProperty('overflow-y','visible','important');
      host.style.setProperty('scroll-snap-type','none','important');
      host.scrollLeft=0;
    }
  }

  let raf=0;
  function refresh(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      fit(qs('#operativoNav'));
      fit(qs('#analysisNav'));
    });
  }

  const ro=new ResizeObserver(refresh);
  const observers=[];

  function observe(host){
    if(!host||host.dataset.v221Observed==='1')return;
    host.dataset.v221Observed='1';
    ro.observe(host.parentElement||host);
    const mo=new MutationObserver(mutations=>{
      // Visibilidad, botón activo o cambios de lista => recalcular.
      if(mutations.some(m=>m.type==='childList'||m.type==='attributes'))refresh();
    });
    mo.observe(host,{
      childList:true,
      subtree:false,
      attributes:true,
      attributeFilter:['class','hidden','aria-hidden']
    });
    observers.push(mo);
  }

  function init(){
    const op=qs('#operativoNav'),an=qs('#analysisNav');
    observe(op);observe(an);
    refresh();
    [80,220,600,1400].forEach(ms=>setTimeout(refresh,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();

  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(refresh,20));
  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button')){
      refresh();
      [20,100,260,650].forEach(ms=>setTimeout(refresh,ms));
    }
  },true);
  window.addEventListener('resize',refresh,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(refresh,100),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,60),{passive:true});

  console.info('[V221] C&M + Análisis usan el mismo dock dinámico de Operación.');
})();
</script>"""

    @m.app.middleware("http")
    async def v221_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v221-report-tabs-match-operation-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v221-report-tabs-match-operation-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V221.2-REPORT-DOCK-SWIPE",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V221] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V221_REPORT_TABS_MATCH_OPERATION=True
    print("[V221.2] C&M + Análisis · tarjetas sin encimar y swipe horizontal cuando no caben.",flush=True)
