(() => {
  'use strict';

  /**
   * ReportTabCarousel
   * Navegación global para pestañas de reportes.
   * - NO se aplica a filtros internos.
   * - Conserva los botones y listeners originales.
   * - El contenido sigue cambiando con la lógica existente; aquí sólo cambia navegación/UX.
   *
   * Iconografía: subconjunto consistente de Lucide Icons (SVG outline).
   */

  const STYLE_ID = 'report-tab-carousel-style-v1';
  const ENHANCED = new WeakMap();
  let lastMainModule = null;
  let globalObserverScheduled = false;

  const LUCIDE = {
    dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>',
    week: '<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
    repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    dollar: '<circle cx="12" cy="12" r="9"/><path d="M16 8.5c-.8-.7-1.9-1-3.2-1-1.8 0-3.1.9-3.1 2.3 0 3.2 6.3 1.5 6.3 4.6 0 1.4-1.3 2.4-3.2 2.4-1.4 0-2.6-.4-3.5-1.2M12.8 5.5v13"/>',
    store: '<path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/><path d="M3 10c0 1.5 2.2 2 3 1 .8 1 2.2.5 3-1 .8 1.5 2.2 1.5 3 0 .8 1.5 2.2 1.5 3 0 .8 1.5 2.2 1.5 3 0 .8 1.5 2.2 1.5 3 0"/>',
    productivity: '<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/><path d="m5 7 4-3 4 4 6-5"/>',
    route: '<path d="M5 19c3-6 11-5 14-12"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="7" r="2"/><path d="M9 7h3M10.5 5.5v3"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    alert: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    upload: '<path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 20h14"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6.2L14.7 4h-4l-.3 2.2a8 8 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 1.5.9l.3 2.2h4l.3-2.2a8 8 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/>',
    macro: '<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
    accordion: '<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="4" rx="1.5"/><rect x="3" y="17" width="18" height="3" rx="1.5"/>',
    building: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h2M14 7h2M8 11h2M14 11h2M8 15h2M14 15h2M9 21v-3h6v3"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    pin: '<path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z"/><circle cx="12" cy="10" r="2"/>',
    checklist: '<path d="M9 5h10M9 12h10M9 19h10"/><path d="m3 5 1.2 1.2L6.5 4M3 12l1.2 1.2L6.5 11M3 19l1.2 1.2L6.5 18"/>',
    more: '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    percent: '<path d="m19 5-14 14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    clipboard: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5M9 9h6M9 13h6M9 17h4"/>',
    package: '<path d="m21 8-9 5-9-5 9-5 9 5Z"/><path d="m3 8 9 5 9-5v8l-9 5-9-5V8Z"/><path d="M12 13v8"/>',
    standards: '<path d="M4 6h16M4 12h10M4 18h13"/><circle cx="18" cy="12" r="2"/><circle cx="15" cy="18" r="2"/>',
    chevronLeft: '<path d="m15 18-6-6 6-6"/>',
    chevronRight: '<path d="m9 18 6-6-6-6"/>',
    file: '<path d="M6 2h8l4 4v16H6z"/><path d="M14 2v5h5M9 13h6M9 17h6"/>'
  };

  const TAB_META = {
    'operations.center': ['Centro Operativo', 'dashboard'],
    'operations.day': ['Día', 'calendar'],
    'operations.week': ['Semanal', 'week'],
    'operations.month': ['Mensual', 'calendar'],
    'operations.conversion': ['Conversión', 'repeat'],
    'operations.recovery': ['Recuperación $', 'dollar'],
    'operations.recovery_store': ['Recuperación por Tienda', 'store'],
    'operations.productivity': ['Productividad', 'productivity'],
    'operations.routes': ['Recorridos', 'route'],
    'operations.score': ['Score', 'target'],
    'operations.alerts': ['Alertas', 'alert'],
    'commercial.macro': ['Macro Compañía', 'macro'],
    'commercial.accordion': ['Acordeón Comercial', 'accordion'],
    'commercial.stores': ['Tiendas', 'building'],
    'commercial.sections': ['Sección / Rubro', 'grid'],
    'commercial.areas': ['Ubicación / Área', 'pin'],
    'commercial.lingerie_checklist': ['Checklist Lencería', 'checklist'],
    'commercial.sellthrough': ['Sell Through', 'percent'],
    'commercial.more': ['Más opciones', 'more'],
    'commercial.upload': ['Carga de datos', 'upload']
  };

  const V125_META = {
    daily: ['Captura diaria', 'calendar'],
    capture: ['Cargar productividad', 'upload'],
    productivity: ['Productividad', 'productivity'],
    standards: ['Estándares', 'standards']
  };

  // Día / Semanal / Mensual ya viven dentro del selector Vista de Centro Operativo.
  // Se conservan en DOM sólo por compatibilidad con los renderizadores históricos.
  const CONSOLIDATED_OPERATION_TABS = new Set([
    'operations.day',
    'operations.week',
    'operations.month'
  ]);

  const EXCLUDED_SELECTORS = [
    '#globalFilters',
    '#operativoPeriodBar',
    '#metricSwitch',
    '#macroAreaSectionSwitch',
    '#macroAreaGroupSwitch',
    '#paretoGroupSwitch',
    '#champSectionSwitch',
    '#rubroSectionSwitch',
    '#v176SlowSectionTabs',
    '#v176ZeroSectionTabs',
    '#v176SlowAreaTabs',
    '.compact-filter .switches',
    '.v176-select-tabs',
    '.v193-st-filters',
    '[data-filter-tabs]'
  ];

  const css = `
    .rt-carousel-shell{
      --rt-card-w:clamp(154px,16vw,190px);
      box-sizing:border-box!important;
      --rt-gap:10px;
      position:relative!important;
      width:100%!important;
      max-width:100%!important;
      margin:2px 0 9px!important;
      padding:0!important;
      background:transparent!important;
      border:0!important;
      box-shadow:none!important;
    }
    .rt-carousel-shell.rt-hidden{display:none!important}

    /* Prioridad final sobre V161/V163/V194: estas capas históricas usan IDs +
       !important y podían convertir el carrusel en cuadrícula. */
    body[data-v163-module="operativo"] #operativoNav.rt-carousel,
    body[data-v163-module="analysis"] #analysisNav.rt-carousel,
    body[data-v163-module="operation"] .v125-tabs.rt-carousel{
      display:flex!important;
      grid-template-columns:none!important;
      flex-wrap:nowrap!important;
      align-items:stretch!important;
      overflow-x:auto!important;
      overflow-y:visible!important;
      gap:var(--rt-gap)!important;
      width:100%!important;
      max-width:100%!important;
      min-height:0!important;
      padding:8px var(--rt-edge-pad) 12px!important;
      margin:0!important;
      border:0!important;
      border-radius:0!important;
      background:transparent!important;
      box-shadow:none!important;
      scroll-snap-type:x mandatory!important;
      scroll-padding-inline:var(--rt-edge-pad)!important;
    }

    body[data-v163-module="operativo"] #operativoNav.rt-carousel .switch,
    body[data-v163-module="analysis"] #analysisNav.rt-carousel .switch,
    body[data-v163-module="operation"] .v125-tabs.rt-carousel .v125-tab{
      flex:0 0 var(--rt-card-w)!important;
      width:var(--rt-card-w)!important;
      min-width:var(--rt-card-w)!important;
      max-width:var(--rt-card-w)!important;
      min-height:66px!important;
      height:66px!important;
      padding:8px 10px 9px!important;
      display:flex!important;
      flex-direction:column!important;
      align-items:center!important;
      justify-content:center!important;
      gap:5px!important;
      border-radius:15px!important;
      white-space:normal!important;
      scroll-snap-align:center!important;
      scroll-snap-stop:always!important;
    }

    body[data-v163-module="operativo"] #v161FilterBar{
      display:none!important;
    }
    .rt-carousel{
      --rt-edge-pad:14px;
      display:flex!important;
      flex-wrap:nowrap!important;
      align-items:stretch!important;
      gap:var(--rt-gap)!important;
      width:100%!important;
      max-width:100%!important;
      min-height:0!important;
      margin:0!important;
      padding:8px var(--rt-edge-pad) 12px!important;
      overflow-x:auto!important;
      overflow-y:visible!important;
      scroll-snap-type:x mandatory!important;
      scroll-padding-inline:var(--rt-edge-pad)!important;
      scroll-behavior:smooth!important;
      overscroll-behavior-x:contain!important;
      -webkit-overflow-scrolling:touch!important;
      scrollbar-width:none!important;
      touch-action:pan-y pinch-zoom!important;
      background:linear-gradient(90deg,rgba(244,247,251,.15),rgba(244,247,251,.75) 12%,rgba(244,247,251,.75) 88%,rgba(244,247,251,.15))!important;
      border:0!important;
      border-radius:0!important;
      box-shadow:none!important;
    }
    .rt-carousel::-webkit-scrollbar{display:none!important}
    .rt-carousel>div{display:contents!important}
    .rt-carousel .switch,
    .rt-carousel .v125-tab,
    .rt-carousel>button{
      position:relative!important;
      box-sizing:border-box!important;
      flex:0 0 var(--rt-card-w)!important;
      width:var(--rt-card-w)!important;
      min-width:var(--rt-card-w)!important;
      max-width:var(--rt-card-w)!important;
      min-height:66px!important;
      height:66px!important;
      margin:0!important;
      padding:8px 10px 9px!important;
      display:flex!important;
      flex-direction:column!important;
      align-items:center!important;
      justify-content:center!important;
      gap:5px!important;
      scroll-snap-align:center!important;
      scroll-snap-stop:always!important;
      white-space:normal!important;
      text-align:center!important;
      border:1px solid #d7e2ee!important;
      border-radius:15px!important;
      background:rgba(255,255,255,.94)!important;
      color:#536a82!important;
      opacity:.72!important;
      transform:scale(.965)!important;
      box-shadow:0 2px 8px rgba(19,54,90,.035)!important;
      transition:transform .18s ease,opacity .18s ease,background .18s ease,border-color .18s ease,box-shadow .18s ease,color .18s ease!important;
      font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;
      cursor:pointer!important;
      -webkit-tap-highlight-color:transparent!important;
    }
    .rt-carousel .switch:hover,
    .rt-carousel .v125-tab:hover,
    .rt-carousel>button:hover{
      opacity:.9!important;
      transform:scale(.985)!important;
      border-color:#b8cbe0!important;
      background:#fff!important;
    }
    .rt-carousel .switch.active,
    .rt-carousel .v125-tab.active,
    .rt-carousel>button.active,
    .rt-carousel [aria-selected="true"]{
      opacity:1!important;
      transform:scale(1.035)!important;
      z-index:2!important;
      border-color:#0b5fab!important;
      background:linear-gradient(145deg,#0b3a6e 0%,#0c579e 58%,#0d7ff4 100%)!important;
      color:#fff!important;
      box-shadow:0 8px 20px rgba(10,69,126,.18)!important;
    }
    .rt-carousel .switch.active::after,
    .rt-carousel .v125-tab.active::after,
    .rt-carousel>button.active::after,
    .rt-carousel [aria-selected="true"]::after{
      content:""!important;
      position:absolute!important;
      left:50%!important;
      bottom:5px!important;
      width:22px!important;
      height:3px!important;
      transform:translateX(-50%)!important;
      border-radius:999px!important;
      background:rgba(255,255,255,.96)!important;
      box-shadow:0 1px 3px rgba(0,0,0,.10)!important;
    }
    .rt-tab-icon{
      display:grid!important;
      place-items:center!important;
      width:20px!important;
      height:20px!important;
      min-width:20px!important;
      flex:0 0 20px!important;
      color:#0d72d4!important;
      transition:transform .18s ease,color .18s ease!important;
      pointer-events:none!important;
    }
    .rt-tab-icon svg{
      display:block!important;
      width:20px!important;
      height:20px!important;
      stroke:currentColor!important;
      fill:none!important;
    }
    .rt-tab-label{
      display:-webkit-box!important;
      -webkit-box-orient:vertical!important;
      -webkit-line-clamp:2!important;
      overflow:hidden!important;
      max-width:100%!important;
      color:inherit!important;
      font-size:10.5px!important;
      line-height:1.12!important;
      font-weight:760!important;
      letter-spacing:-.01em!important;
      pointer-events:none!important;
    }
    .rt-carousel .active .rt-tab-icon,
    .rt-carousel [aria-selected="true"] .rt-tab-icon{
      color:#fff!important;
      transform:scale(1.06)!important;
    }
    .rt-carousel .active .rt-tab-label,
    .rt-carousel [aria-selected="true"] .rt-tab-label{
      font-weight:900!important;
    }
    .rt-carousel .or-tab-icon,
    .rt-carousel .v164-tab-icon,
    .rt-carousel .v166-tab-icon,
    .rt-carousel .v167-tab-icon,
    .rt-carousel .v176-tab-icon,
    .rt-carousel .v177-nav-ico,
    .rt-carousel .rt-legacy-tab-deco{
      display:none!important;
    }
    .rt-carousel-arrow{
      position:absolute!important;
      top:50%!important;
      z-index:8!important;
      display:grid!important;
      place-items:center!important;
      width:38px!important;
      height:38px!important;
      padding:0!important;
      margin:0!important;
      transform:translateY(-50%)!important;
      border:1px solid #d6e2ee!important;
      border-radius:50%!important;
      background:rgba(255,255,255,.96)!important;
      color:#0b4f91!important;
      box-shadow:0 6px 16px rgba(15,56,97,.13)!important;
      cursor:pointer!important;
      opacity:1!important;
      transition:opacity .16s ease,transform .16s ease,box-shadow .16s ease!important;
      backdrop-filter:blur(8px)!important;
    }
    .rt-carousel-arrow:hover{
      transform:translateY(-50%) scale(1.05)!important;
      box-shadow:0 8px 20px rgba(15,56,97,.17)!important;
    }
    .rt-carousel-arrow:disabled{
      opacity:0!important;
      pointer-events:none!important;
    }
    .rt-carousel-arrow svg{width:19px!important;height:19px!important;stroke:currentColor!important}
    .rt-carousel-arrow.prev{left:2px!important}
    .rt-carousel-arrow.next{right:2px!important}
    .rt-carousel-shell::before,
    .rt-carousel-shell::after{
      content:""!important;
      position:absolute!important;
      top:4px!important;
      bottom:7px!important;
      z-index:4!important;
      width:30px!important;
      pointer-events:none!important;
      opacity:0!important;
      transition:opacity .16s ease!important;
    }
    .rt-carousel-shell::before{left:0!important;background:linear-gradient(90deg,#f4f7fb 10%,rgba(244,247,251,0))!important}
    .rt-carousel-shell::after{right:0!important;background:linear-gradient(270deg,#f4f7fb 10%,rgba(244,247,251,0))!important}
    .rt-carousel-shell.rt-can-prev::before,
    .rt-carousel-shell.rt-can-next::after{opacity:1!important}

    @media(max-width:900px){
      .rt-carousel-shell{
        --rt-card-w:clamp(148px,43vw,176px);
        --rt-gap:8px;
        margin:0 0 7px!important;
      }
      .rt-carousel{
        padding-top:7px!important;
        padding-bottom:11px!important;
        background:transparent!important;
      }
      .rt-carousel .switch,
      .rt-carousel .v125-tab,
      .rt-carousel>button{
        min-height:64px!important;
        height:64px!important;
        padding:7px 8px 9px!important;
        border-radius:14px!important;
      }
      .rt-tab-icon{width:19px!important;height:19px!important;min-width:19px!important}
      .rt-tab-icon svg{width:19px!important;height:19px!important}
      .rt-tab-label{font-size:10px!important;line-height:1.08!important}
      .rt-carousel-arrow{display:none!important}
      .rt-carousel-shell::before,.rt-carousel-shell::after{display:none!important}
    }

    @media(min-width:901px){
      .rt-carousel-shell{padding:0 44px!important}
      .rt-carousel{padding-left:var(--rt-edge-pad)!important;padding-right:var(--rt-edge-pad)!important}
    }

    /* Filtros inferiores de Cambios y Muertos:
       en Día/Semanal/Mensual no se repite el selector Vista. */
    #operativoPeriodBar.or-fixed-period>.or-report-filter-grid{
      grid-template-columns:repeat(4,minmax(0,1fr))!important;
    }
    #operativoPeriodBar.or-fixed-period #operPeriodSelectWrap,
    #operativoPeriodBar.or-fixed-period #operStoreWrap,
    #operativoPeriodBar.or-fixed-period #operAreaWrap,
    #operativoPeriodBar.or-fixed-period #operActivityWrap{
      grid-column:span 1!important;
    }
    #operativoPeriodBar.or-fixed-period #operPeriodApply{
      grid-column:1/-1!important;
    }

    @media(max-width:900px){
      body[data-v163-module="operativo"] #operativoNav.rt-carousel,
      body[data-v163-module="analysis"] #analysisNav.rt-carousel,
      body[data-v163-module="operation"] .v125-tabs.rt-carousel{
        padding:7px var(--rt-edge-pad) 11px!important;
      }
      body[data-v163-module="operativo"] #operativoNav.rt-carousel .switch,
      body[data-v163-module="analysis"] #analysisNav.rt-carousel .switch,
      body[data-v163-module="operation"] .v125-tabs.rt-carousel .v125-tab{
        min-height:64px!important;
        height:64px!important;
        border-radius:14px!important;
      }
      #operativoPeriodBar.or-fixed-period>.or-report-filter-grid{
        grid-template-columns:repeat(2,minmax(0,1fr))!important;
      }
    }

    @media(prefers-reduced-motion:reduce){
      .rt-carousel{scroll-behavior:auto!important}
      .rt-carousel .switch,.rt-carousel .v125-tab,.rt-carousel>button,.rt-carousel-arrow{transition:none!important}
    }
  `;

  function svg(name){
    const path=LUCIDE[name]||LUCIDE.file;
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+path+'</svg>';
  }

  function installStyle(){
    if(document.getElementById(STYLE_ID)) return;
    const style=document.createElement('style');
    style.id=STYLE_ID;
    style.textContent=css;
    document.head.appendChild(style);
  }

  function isExcluded(el){
    return EXCLUDED_SELECTORS.some(sel=>{
      try{return el.matches(sel)||Boolean(el.closest(sel));}catch(_){return false;}
    });
  }

  function directNavButtons(el){
    const buttons=[];
    [...el.children].forEach(child=>{
      if(child instanceof HTMLButtonElement){
        buttons.push(child);
        return;
      }
      if(child instanceof HTMLElement){
        [...child.children].forEach(grand=>{
          if(grand instanceof HTMLButtonElement) buttons.push(grand);
        });
      }
    });
    return buttons;
  }

  function isSemanticButton(btn){
    return Boolean(
      btn?.dataset?.tabKey ||
      btn?.dataset?.opview ||
      btn?.dataset?.sub ||
      btn?.dataset?.v125Tab ||
      btn?.dataset?.reportTab
    );
  }

  function semanticButtons(el){
    return directNavButtons(el).filter(isSemanticButton);
  }

  function directSemanticButtons(el){
    return [...el.children].filter(child=>child instanceof HTMLButtonElement && isSemanticButton(child));
  }

  function isReportTabContainer(el){
    if(!(el instanceof Element)||isExcluded(el)) return false;
    if(el.id==='operativoNav'||el.id==='analysisNav'||el.classList.contains('v125-tabs')||el.hasAttribute('data-report-tab-carousel')) return true;
    // Para detección genérica exigimos botones semánticos DIRECTOS.
    // Esto evita que main/page/shell se confundan con un carrusel por contener
    // navegaciones varios niveles más abajo.
    return directSemanticButtons(el).length>=2;
  }

  function visibleButton(btn){
    if(!btn||btn.disabled||btn.hidden||btn.classList.contains('hidden')) return false;
    if(btn.style?.display==='none') return false;
    const cs=getComputedStyle(btn);
    return cs.display!=='none'&&cs.visibility!=='hidden';
  }

  function buttonsOf(viewport){
    return directNavButtons(viewport);
  }

  function visibleButtons(viewport){
    return buttonsOf(viewport).filter(visibleButton);
  }

  function cleanText(btn){
    if(btn.dataset.rtOriginalLabel) return btn.dataset.rtOriginalLabel;
    const clone=btn.cloneNode(true);
    clone.querySelectorAll('svg,.or-tab-icon,.v164-tab-icon,.v166-tab-icon,.v167-tab-icon,.v176-tab-icon,.v177-nav-ico,.rt-tab-icon').forEach(x=>x.remove());
    let text=(clone.textContent||'').replace(/^%\s*/,'').replace(/\s+/g,' ').trim();
    if(!text) text='Pestaña';
    btn.dataset.rtOriginalLabel=text;
    return text;
  }

  function metaFor(btn){
    const key=btn.dataset.tabKey||'';
    if(TAB_META[key]) return {label:TAB_META[key][0],icon:TAB_META[key][1]};
    const v125=btn.dataset.v125Tab||'';
    if(V125_META[v125]) return {label:V125_META[v125][0],icon:V125_META[v125][1]};

    const label=cleanText(btn);
    const l=label.toLowerCase();
    let icon='file';
    if(btn.id==='openGoalsBtn'||/meta|config|estándar/.test(l)) icon='settings';
    else if(/carga|subir/.test(l)) icon='upload';
    else if(/sell/.test(l)) icon='percent';
    else if(/centro|resumen|ejecutivo/.test(l)) icon='dashboard';
    else if(/convers/.test(l)) icon='repeat';
    else if(/recuper.*tienda|por tienda|tienda/.test(l)) icon='store';
    else if(/recuper/.test(l)) icon='dollar';
    else if(/product/.test(l)) icon='productivity';
    else if(/recorrido|ruta/.test(l)) icon='route';
    else if(/score|índice|indice/.test(l)) icon='target';
    else if(/alert/.test(l)) icon='alert';
    else if(/macro/.test(l)) icon='macro';
    else if(/acorde/.test(l)) icon='accordion';
    else if(/sección|seccion|rubro/.test(l)) icon='grid';
    else if(/ubicación|ubicacion|área|area/.test(l)) icon='pin';
    else if(/check/.test(l)) icon='checklist';
    else if(/80\/20|campe|lento/.test(l)) icon='package';
    else if(/día|dia|mes|semana/.test(l)) icon='calendar';
    else if(/más|mas|opciones/.test(l)) icon='more';
    return {label,icon};
  }

  function decorateButton(btn){
    if(!(btn instanceof HTMLButtonElement)) return;
    const meta=metaFor(btn);
    const currentLabel=btn.querySelector('.rt-tab-label')?.textContent?.trim();
    const currentIcon=btn.dataset.rtIcon;
    if(currentLabel===meta.label&&currentIcon===meta.icon) return;

    btn.dataset.rtIcon=meta.icon;
    btn.dataset.rtLabel=meta.label;
    btn.setAttribute('role','tab');

    // Reemplazar sólo el contenido interno mantiene intactos listeners/onclick del botón.
    btn.innerHTML='<span class="rt-tab-icon">'+svg(meta.icon)+'</span><span class="rt-tab-label"></span>';
    btn.querySelector('.rt-tab-label').textContent=meta.label;
  }

  function activeButton(viewport){
    const buttons=visibleButtons(viewport);
    // La clase .active representa el estado real del reporte.
    // aria-selected es sólo accesibilidad y puede quedar momentáneamente desfasado.
    return buttons.find(b=>b.classList.contains('active'))
      || buttons.find(b=>b.getAttribute('aria-selected')==='true')
      || buttons[0]
      || null;
  }

  function updateAria(viewport){
    const current=activeButton(viewport);
    buttonsOf(viewport).forEach(btn=>{
      const active=btn===current;
      btn.setAttribute('aria-selected',active?'true':'false');
      btn.tabIndex=active?0:-1;
    });
  }

  function setEdgePadding(viewport){
    const first=visibleButtons(viewport)[0];
    if(!first||!viewport.clientWidth) return;
    const width=first.getBoundingClientRect().width;
    const edge=Math.max(10,(viewport.clientWidth-width)/2);
    viewport.style.setProperty('--rt-edge-pad',edge+'px');
  }

  function centerButton(viewport,btn,behavior='smooth'){
    if(!btn||!visibleButton(btn)||!viewport.clientWidth) return;
    const vr=viewport.getBoundingClientRect();
    const br=btn.getBoundingClientRect();
    const delta=(br.left+br.width/2)-(vr.left+vr.width/2);
    const target=viewport.scrollLeft+delta;
    const max=Math.max(0,viewport.scrollWidth-viewport.clientWidth);
    const left=Math.max(0,Math.min(max,target));
    try{viewport.scrollTo({left,behavior});}
    catch(_){viewport.scrollLeft=left;}
  }

  function containerShown(viewport){
    if(viewport.hidden||viewport.classList.contains('hidden')||viewport.style.display==='none') return false;
    return getComputedStyle(viewport).display!=='none';
  }

  function updateArrows(viewport){
    const state=ENHANCED.get(viewport);
    if(!state) return;
    const shown=containerShown(viewport);
    state.shell.classList.toggle('rt-hidden',!shown);
    if(!shown){
      state.prev.disabled=true;
      state.next.disabled=true;
      return;
    }
    const max=Math.max(0,viewport.scrollWidth-viewport.clientWidth);
    const canPrev=viewport.scrollLeft>8;
    const canNext=viewport.scrollLeft<max-8;
    state.shell.classList.toggle('rt-can-prev',canPrev);
    state.shell.classList.toggle('rt-can-next',canNext);
    state.prev.disabled=!canPrev;
    state.next.disabled=!canNext;
  }

  function syncActive(viewport,{center=true,behavior='smooth'}={}){
    const btn=activeButton(viewport);
    if(!btn) return;
    setEdgePadding(viewport);
    updateAria(viewport);
    if(center) centerButton(viewport,btn,behavior);
    requestAnimationFrame(()=>updateArrows(viewport));
  }

  function nearestButton(viewport){
    const buttons=visibleButtons(viewport);
    if(!buttons.length) return null;
    const rect=viewport.getBoundingClientRect();
    const cx=rect.left+rect.width/2;
    let best=null,bestDist=Infinity;
    buttons.forEach(btn=>{
      const r=btn.getBoundingClientRect();
      const d=Math.abs((r.left+r.width/2)-cx);
      if(d<bestDist){best=btn;bestDist=d;}
    });
    return best;
  }

  function clickAdjacent(viewport,delta){
    const buttons=visibleButtons(viewport);
    if(!buttons.length) return;
    const active=activeButton(viewport);
    let idx=Math.max(0,buttons.indexOf(active));
    idx=Math.max(0,Math.min(buttons.length-1,idx+delta));
    const next=buttons[idx];
    if(next&&next!==active) next.click();
    else centerButton(viewport,next||active,'smooth');
  }

  function commitSwipe(viewport){
    const state=ENHANCED.get(viewport);
    if(!state||!state.gesturePending) return;
    state.gesturePending=false;

    const nearest=nearestButton(viewport);
    if(!nearest) return;

    // La pestaña que quedó más cerca del centro pasa a ser la elegida
    // y se queda anclada ahí. No dependemos de que la lógica del reporte
    // actualice .active de forma síncrona.
    state.userCenteredButton=nearest;
    state.userAnchored=true;

    const active=activeButton(viewport);
    if(nearest!==active){
      nearest.click();
    }

    centerButton(viewport,nearest,'smooth');
    setTimeout(()=>centerButton(viewport,nearest,'smooth'),70);
    setTimeout(()=>centerButton(viewport,nearest,'auto'),190);
  }

  function enforceConsolidatedOperationTabs(viewport){
    if(viewport?.id!=='operativoNav') return;
    buttonsOf(viewport).forEach(btn=>{
      if(!CONSOLIDATED_OPERATION_TABS.has(btn.dataset.tabKey||'')) return;
      if(!btn.hidden) btn.hidden=true;
      if(!btn.classList.contains('hidden')) btn.classList.add('hidden');
      if(btn.getAttribute('aria-hidden')!=='true') btn.setAttribute('aria-hidden','true');
      if(btn.tabIndex!==-1) btn.tabIndex=-1;
    });
  }

  function refreshCards(viewport){
    enforceConsolidatedOperationTabs(viewport);
    viewport.style.setProperty('display','flex','important');
    viewport.style.setProperty('grid-template-columns','none','important');
    viewport.style.setProperty('flex-wrap','nowrap','important');
    viewport.style.setProperty('overflow-x','auto','important');
    viewport.style.setProperty('overflow-y','visible','important');
    buttonsOf(viewport).forEach(decorateButton);
    setEdgePadding(viewport);
    syncActive(viewport,{center:false});
    updateArrows(viewport);
  }

  function arrowButton(dir){
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='rt-carousel-arrow '+dir;
    btn.setAttribute('aria-label',dir==='prev'?'Pestaña anterior':'Pestaña siguiente');
    btn.innerHTML=svg(dir==='prev'?'chevronLeft':'chevronRight');
    return btn;
  }

  function enhance(viewport){
    if(!isReportTabContainer(viewport)) return;
    enforceConsolidatedOperationTabs(viewport);
    if(ENHANCED.has(viewport)){
      refreshCards(viewport);
      return;
    }

    installStyle();

    const shell=document.createElement('div');
    shell.className='rt-carousel-shell';
    const prev=arrowButton('prev');
    const next=arrowButton('next');

    viewport.parentNode.insertBefore(shell,viewport);
    shell.append(prev,viewport,next);

    viewport.classList.add('rt-carousel');
    viewport.setAttribute('role','tablist');
    viewport.setAttribute('aria-orientation','horizontal');

    // Blindaje contra capas CSS históricas que intentaban convertir la navegación
    // en grid. Inline !important gana sobre V161/V163/V194.
    const forceSingleRow = () => {
      viewport.style.setProperty('display','flex','important');
      viewport.style.setProperty('grid-template-columns','none','important');
      viewport.style.setProperty('flex-wrap','nowrap','important');
      viewport.style.setProperty('align-items','stretch','important');
      viewport.style.setProperty('overflow-x','auto','important');
      viewport.style.setProperty('overflow-y','visible','important');
      viewport.style.setProperty('white-space','nowrap','important');
      viewport.style.setProperty('width','100%','important');
      viewport.style.setProperty('max-width','100%','important');
    };
    forceSingleRow();

    const state={
      shell,prev,next,
      gesturePending:false,
      scrollTimer:null,
      mutationFrame:null,
      touchStartX:0,
      touchStartY:0,
      touchStartScroll:0,
      touchMode:'idle',
      dragged:false,
      suppressClickUntil:0,
      userAnchored:false,
      userCenteredButton:null
    };
    ENHANCED.set(viewport,state);

    prev.addEventListener('click',()=>clickAdjacent(viewport,-1));
    next.addEventListener('click',()=>clickAdjacent(viewport,1));

    viewport.addEventListener('click',event=>{
      const btn=event.target.closest('button');
      if(!btn||btn.closest('.rt-carousel')!==viewport) return;

      // Después de un swipe, iOS puede emitir click sobre la tarjeta bajo el dedo.
      // Lo anulamos para no abrir una pestaña distinta accidentalmente.
      if(Date.now()<state.suppressClickUntil){
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      state.gesturePending=false;
      state.userAnchored=true;
      state.userCenteredButton=btn;

      // Centrar el botón que el usuario tocó, no "la activa" calculada,
      // porque el reporte puede actualizar .active unas décimas después.
      requestAnimationFrame(()=>centerButton(viewport,btn,'smooth'));
      setTimeout(()=>centerButton(viewport,btn,'smooth'),80);
      setTimeout(()=>centerButton(viewport,btn,'auto'),180);
    });

    viewport.addEventListener('touchstart',event=>{
      // V196: cuando el rail final está activo, él es el único dueño del gesto.
      // Evita dos listeners compitiendo por el mismo dedo en Android.
      if(viewport.classList.contains('rt-icon-rail-v1')) return;
      if(!event.touches||event.touches.length!==1) return;
      const t=event.touches[0];
      state.touchStartX=t.clientX;
      state.touchStartY=t.clientY;
      state.touchStartScroll=viewport.scrollLeft;
      state.touchMode='pending';
      state.dragged=false;
      state.gesturePending=false;
      clearTimeout(state.scrollTimer);
    },{passive:true});

    viewport.addEventListener('touchmove',event=>{
      if(viewport.classList.contains('rt-icon-rail-v1')) return;
      if(!event.touches||event.touches.length!==1||state.touchMode==='idle') return;
      const t=event.touches[0];
      const dx=t.clientX-state.touchStartX;
      const dy=t.clientY-state.touchStartY;
      const ax=Math.abs(dx), ay=Math.abs(dy);

      if(state.touchMode==='pending'){
        if(ax<5&&ay<5) return;
        if(ax>ay*1.08){
          state.touchMode='horizontal';
          state.gesturePending=true;
          viewport.style.setProperty('scroll-snap-type','none','important');
          viewport.style.setProperty('scroll-behavior','auto','important');
        }else if(ay>ax){
          state.touchMode='vertical';
          state.gesturePending=false;
          return;
        }
      }

      if(state.touchMode==='horizontal'){
        if(ax>6) state.dragged=true;
        event.preventDefault();
        viewport.scrollLeft=state.touchStartScroll-dx;
        updateArrows(viewport);
      }
    },{passive:false});

    const finishTouch=()=>{
      if(state.touchMode==='horizontal'){
        viewport.style.setProperty('scroll-snap-type','x mandatory','important');
        viewport.style.setProperty('scroll-behavior','smooth','important');
        if(state.dragged) state.suppressClickUntil=Date.now()+320;
        state.gesturePending=true;
        clearTimeout(state.scrollTimer);
        state.scrollTimer=setTimeout(()=>commitSwipe(viewport),40);
      }
      state.touchMode='idle';
    };

    viewport.addEventListener('touchend',finishTouch,{passive:true});
    viewport.addEventListener('touchcancel',finishTouch,{passive:true});

    viewport.addEventListener('scroll',()=>{
      updateArrows(viewport);
      if(state.gesturePending){
        clearTimeout(state.scrollTimer);
        state.scrollTimer=setTimeout(()=>commitSwipe(viewport),150);
      }
    },{passive:true});

    if('onscrollend' in window){
      viewport.addEventListener('scrollend',()=>commitSwipe(viewport),{passive:true});
    }

    viewport.addEventListener('keydown',event=>{
      if(event.key==='ArrowRight'){
        event.preventDefault();
        clickAdjacent(viewport,1);
      }else if(event.key==='ArrowLeft'){
        event.preventDefault();
        clickAdjacent(viewport,-1);
      }else if(event.key==='Home'){
        event.preventDefault();
        visibleButtons(viewport)[0]?.click();
      }else if(event.key==='End'){
        event.preventDefault();
        visibleButtons(viewport).at(-1)?.click();
      }
    });

    const observer=new MutationObserver(mutations=>{
      const needsCards=mutations.some(m=>m.type==='childList');
      const needsActive=mutations.some(m=>m.type==='attributes');

      if(state.mutationFrame) cancelAnimationFrame(state.mutationFrame);
      state.mutationFrame=requestAnimationFrame(()=>{
        state.mutationFrame=null;

        if(needsCards) refreshCards(viewport);

        if(needsActive){
          // Actualizar accesibilidad/estado visual sin mover el carrusel.
          // Una carga de datos, cambio de filtros o render interno NO debe
          // reposicionar las pestañas.
          updateAria(viewport);
          updateArrows(viewport);

          // Si el usuario ya ancló una pestaña, mantener exactamente ese centro.
          if(state.userAnchored && state.userCenteredButton && visibleButton(state.userCenteredButton)){
            // Sólo corregimos desviaciones perceptibles, sin animaciones repetidas.
            const vr=viewport.getBoundingClientRect();
            const br=state.userCenteredButton.getBoundingClientRect();
            const delta=Math.abs((br.left+br.width/2)-(vr.left+vr.width/2));
            if(delta>4) centerButton(viewport,state.userCenteredButton,'auto');
          }
        }
      });
    });
    observer.observe(viewport,{
      subtree:true,
      childList:true,
      attributes:true,
      attributeFilter:['class','style','hidden','aria-selected']
    });
    state.observer=observer;

    refreshCards(viewport);
    requestAnimationFrame(()=>{
      setEdgePadding(viewport);
      state.userAnchored=false;
      state.userCenteredButton=null;
      syncActive(viewport,{center:true,behavior:'auto'});
    });
  }

  function scan(root=document){
    const candidates=new Set();
    if(root instanceof Element&&isReportTabContainer(root)) candidates.add(root);

    const selectors=[
      '#operativoNav',
      '#analysisNav',
      '.v125-tabs',
      '[data-report-tab-carousel]'
    ];

    selectors.forEach(sel=>{
      try{root.querySelectorAll?.(sel).forEach(el=>candidates.add(el));}catch(_){}
    });

    // Cualquier contenedor nuevo que tenga 2+ botones semánticos de navegación.
    root.querySelectorAll?.('div,nav,section').forEach(el=>{
      if(isReportTabContainer(el)) candidates.add(el);
    });

    candidates.forEach(enhance);
  }

  function activateFirst(viewport){
    const first=visibleButtons(viewport)[0];
    if(!first) return;
    const state=ENHANCED.get(viewport);
    if(state){
      state.userAnchored=false;
      state.userCenteredButton=null;
    }
    if(!first.classList.contains('active')) first.click();
    requestAnimationFrame(()=>centerButton(viewport,first,'smooth'));
  }

  function firstForMain(main){
    if(main==='operativo') return document.getElementById('operativoNav');
    if(main==='analysis') return document.getElementById('analysisNav');
    return null;
  }

  function syncOperativeFilterUI(viewName){
    const bar=document.getElementById('operativoPeriodBar');
    if(!bar||document.body.dataset.v163Module!=='operativo') return;

    const modeWrap=document.getElementById('operPeriodModeWrap');
    const periodLabel=document.getElementById('operPeriodLabel');
    const areaWrap=document.getElementById('operAreaWrap');
    const activityWrap=document.getElementById('operActivityWrap');
    const storeWrap=document.getElementById('operStoreWrap');

    if(viewName==='Carga de datos'){
      bar.classList.add('hidden');
      bar.classList.remove('or-fixed-period');
      return;
    }

    // Los filtros inferiores son la única fuente visible.
    bar.classList.remove('hidden');
    storeWrap?.classList.remove('hidden');
    areaWrap?.classList.remove('hidden');
    activityWrap?.classList.remove('hidden');

    const fixed={
      'Operación Diaria':'Fecha',
      'Reporte Semanal':'Semana ISO',
      'Reporte Mensual':'Mes',
      'Indicadores Diarios':'Fecha'
    };
    const fixedLabel=fixed[viewName];

    if(fixedLabel){
      modeWrap?.classList.add('hidden');
      bar.classList.add('or-fixed-period');
      if(periodLabel) periodLabel.textContent=fixedLabel;
    }else{
      bar.classList.remove('or-fixed-period');
      // Para vistas flexibles se conserva Vista + Periodo.
      if(modeWrap && modeWrap.querySelector('select')?.options?.length){
        modeWrap.classList.remove('hidden');
      }
    }
  }

  function bindOperativeFilterGuard(){
    document.addEventListener('click',event=>{
      const btn=event.target.closest?.('#operativoNav [data-opview]');
      if(!btn) return;
      const view=btn.dataset.opview||'';
      // La lógica original procesa la pestaña primero; luego sólo corregimos la UI.
      [40,140,360].forEach(ms=>setTimeout(()=>syncOperativeFilterUI(view),ms));
    },true);

    const initial=document.querySelector('#operativoNav [data-opview].active');
    if(initial) setTimeout(()=>syncOperativeFilterUI(initial.dataset.opview||''),180);
  }

  function bindMainReset(){
    lastMainModule=document.querySelector('.nav[data-main].active')?.dataset.main||null;
    document.addEventListener('click',event=>{
      const mainBtn=event.target.closest('[data-main]');
      if(!mainBtn) return;
      const main=mainBtn.dataset.main;
      if(!['operativo','analysis'].includes(main)) return;
      const changed=main!==lastMainModule;
      lastMainModule=main;
      if(!changed) return;
      setTimeout(()=>{
        const viewport=firstForMain(main);
        if(viewport){
          enhance(viewport);
          activateFirst(viewport);
        }
      },140);
    });
  }

  function refreshAll(){
    scan(document);
    document.querySelectorAll('.rt-carousel').forEach(viewport=>{
      setEdgePadding(viewport);
      refreshCards(viewport);
      syncActive(viewport,{center:false});
    });
  }

  function init(){
    installStyle();
    scan(document);
    bindMainReset();
    bindOperativeFilterGuard();

    const observer=new MutationObserver(mutations=>{
      if(globalObserverScheduled) return;
      if(!mutations.some(m=>m.addedNodes.length||m.removedNodes.length)) return;
      globalObserverScheduled=true;
      requestAnimationFrame(()=>{
        globalObserverScheduled=false;
        scan(document);
      });
    });
    observer.observe(document.body,{subtree:true,childList:true});

    window.addEventListener('resize',()=>{
      clearTimeout(window.__rtCarouselResizeTimer);
      window.__rtCarouselResizeTimer=setTimeout(refreshAll,100);
    },{passive:true});

    window.ReportTabCarousel={
      refresh:refreshAll,
      enhance,
      centerActive:(viewport)=>syncActive(viewport,{center:true}),
      activateFirst
    };
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
