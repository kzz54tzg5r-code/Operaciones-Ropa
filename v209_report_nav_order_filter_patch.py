"""V209 · Orden definitivo de pestañas + filtros comerciales debajo del dock.

Deja fijas las navegaciones principales según el orden aprobado:
Cambios y Muertos:
  1 Centro Operativo
  2 Conversión
  3 Recuperación $
  4 Recuperación por Tienda
  5 Recorridos
  6 Productividad
  7 Metas y tiendas
  8 Cargar productividad
  9 Carga de datos

Análisis Comercial:
  1 Macro Compañía
  2 Sell Through
  3 Tiendas
  4 Checklist Lencería
  5 Carga de datos
  6 Acordeón Comercial

Además:
- oculta pestañas legacy/duplicadas que no pertenecen al dock;
- evita el reordenamiento circular en escritorio de estas dos barras;
- restaura nombre visible bajo cada icono;
- mueve los filtros comerciales debajo de pestañas + título contextual;
- sincroniza pestaña activa con la página real mostrada.
"""
from __future__ import annotations

from datetime import datetime
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V209_REPORT_NAV_ORDER_FILTERS", False):
        return

    desired_tabs = [
        ("operations.center", "Centro Operativo"),
        ("operations.conversion", "Conversión"),
        ("operations.recovery", "Recuperación $"),
        ("operations.recovery_store", "Recuperación por Tienda"),
        ("operations.routes", "Recorridos"),
        ("operations.productivity", "Productividad"),
        ("operations.goals", "Metas y tiendas"),
        ("operations.productivity_capture", "Cargar productividad"),
        ("operations.upload", "Carga de datos"),
        ("commercial.macro", "Macro Compañía"),
        ("commercial.sellthrough", "Sell Through"),
        ("commercial.stores", "Tiendas"),
        ("commercial.lingerie_checklist", "Checklist Lencería"),
        ("commercial.upload", "Carga de datos"),
        ("commercial.accordion", "Acordeón Comercial"),
    ]

    # La pantalla "Pestañas visibles" debe mostrar sólo el dock definitivo
    # y en el mismo orden visual.
    try:
        m.REPORT_TABS.clear()
        for key, label in desired_tabs:
            m.REPORT_TABS[key] = label
        now = datetime.now().isoformat(timespec="seconds")
        with m.db() as con:
            for key, _ in desired_tabs:
                con.execute(
                    "INSERT OR IGNORE INTO report_tab_visibility(tab_key,visible,updated_at,updated_by) VALUES(?,?,?,?)",
                    (key, 1, now, "system"),
                )
    except Exception as exc:
        print(f"[V209] tabs backend warning: {type(exc).__name__}: {exc}", flush=True)

    css = r'''<style id="v209-report-nav-order-css">
/* ===============================================================
   DOCK DEFINITIVO · CAMBIOS Y MUERTOS + ANÁLISIS COMERCIAL
   =============================================================== */
#operativoNav.v209-static-nav,
#analysisNav.v209-static-nav{
  display:flex!important;
  grid-template-columns:none!important;
  flex-wrap:nowrap!important;
  align-items:flex-start!important;
  justify-content:center!important;
  gap:7px!important;
  width:100%!important;
  max-width:100%!important;
  min-height:72px!important;
  height:auto!important;
  margin:3px 0 5px!important;
  padding:5px 8px 9px!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  border:0!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
  white-space:nowrap!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
  scroll-snap-type:x mandatory!important;
  scroll-behavior:smooth!important;
  touch-action:pan-x pan-y!important;
}
#operativoNav.v209-static-nav::-webkit-scrollbar,
#analysisNav.v209-static-nav::-webkit-scrollbar{display:none!important}

#operativoNav.v209-static-nav>button,
#analysisNav.v209-static-nav>button{
  position:relative!important;
  display:flex!important;
  flex:0 0 92px!important;
  width:92px!important;
  min-width:92px!important;
  max-width:92px!important;
  height:64px!important;
  min-height:64px!important;
  max-height:64px!important;
  margin:0!important;
  padding:3px 3px 4px!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:3px!important;
  border:0!important;
  border-radius:13px!important;
  background:transparent!important;
  box-shadow:none!important;
  color:#617890!important;
  opacity:1!important;
  transform:none!important;
  font-size:7.4px!important;
  line-height:1.06!important;
  font-weight:850!important;
  text-align:center!important;
  white-space:normal!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
  overflow:visible!important;
}
#operativoNav.v209-static-nav>button:hover,
#analysisNav.v209-static-nav>button:hover{
  background:#f7fbff!important;
}

#operativoNav.v209-static-nav .v209-tab-icon,
#analysisNav.v209-static-nav .v209-tab-icon{
  display:grid!important;
  place-items:center!important;
  width:35px!important;
  height:35px!important;
  min-width:35px!important;
  min-height:35px!important;
  flex:0 0 35px!important;
  border:1px solid #d7e4f0!important;
  border-radius:50%!important;
  background:#fff!important;
  color:#557a9e!important;
  box-shadow:0 2px 7px rgba(18,70,118,.06)!important;
}
#operativoNav.v209-static-nav .v209-tab-icon svg,
#analysisNav.v209-static-nav .v209-tab-icon svg{
  display:block!important;
  width:18px!important;
  height:18px!important;
  stroke:currentColor!important;
}
#operativoNav.v209-static-nav .v209-tab-label,
#analysisNav.v209-static-nav .v209-tab-label{
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  color:inherit!important;
  font-size:7.4px!important;
  line-height:1.06!important;
  font-weight:850!important;
  text-align:center!important;
  white-space:normal!important;
  overflow:visible!important;
  text-overflow:clip!important;
}

#operativoNav.v209-static-nav>button.active,
#analysisNav.v209-static-nav>button.active,
#operativoNav.v209-static-nav>button[aria-selected="true"],
#analysisNav.v209-static-nav>button[aria-selected="true"]{
  color:#0b5fae!important;
  background:transparent!important;
  border:0!important;
  box-shadow:none!important;
  transform:none!important;
}
#operativoNav.v209-static-nav>button.active .v209-tab-icon,
#analysisNav.v209-static-nav>button.active .v209-tab-icon,
#operativoNav.v209-static-nav>button[aria-selected="true"] .v209-tab-icon,
#analysisNav.v209-static-nav>button[aria-selected="true"] .v209-tab-icon{
  width:44px!important;
  height:44px!important;
  min-width:44px!important;
  min-height:44px!important;
  flex-basis:44px!important;
  border-color:#0d6fd1!important;
  background:linear-gradient(145deg,#0b3a6e 0%,#0c579e 58%,#0d7ff4 100%)!important;
  color:#fff!important;
  box-shadow:0 7px 17px rgba(10,69,126,.20)!important;
}
#operativoNav.v209-static-nav>button.active:after,
#analysisNav.v209-static-nav>button.active:after,
#operativoNav.v209-static-nav>button[aria-selected="true"]:after,
#analysisNav.v209-static-nav>button[aria-selected="true"]:after{
  content:""!important;
  display:block!important;
  position:absolute!important;
  left:50%!important;
  bottom:-5px!important;
  width:28px!important;
  height:3px!important;
  border-radius:999px!important;
  background:#1185ef!important;
  transform:translateX(-50%)!important;
}

/* Estructurales: nunca deben reaparecer por CSS legacy. */
#operativoNav>button.v209-structural-hidden,
#analysisNav>button.v209-structural-hidden{
  display:none!important;
  visibility:hidden!important;
  flex:0 0 0!important;
  width:0!important;
  min-width:0!important;
  max-width:0!important;
  height:0!important;
  min-height:0!important;
  max-height:0!important;
  margin:0!important;
  padding:0!important;
  opacity:0!important;
  pointer-events:none!important;
}

/* Ya existe título contextual debajo del dock; quitamos el "nombre activo"
   duplicado que agregaba el carrusel antiguo. */
.rt-icon-rail-v1-current,
.rt-icon-rail-v1-indicator,
.rt-carousel-arrow{
  display:none!important;
}

/* ===============================================================
   FILTRO COMERCIAL · MISMO PATRÓN QUE OPERACIÓN
   =============================================================== */
#globalFilters.v209-commercial-filter{
  position:relative!important;
  width:100%!important;
  max-width:100%!important;
  margin:5px 0 11px!important;
  padding:0 7px 7px!important;
  border:1px solid #cddbea!important;
  border-radius:15px!important;
  background:#fff!important;
  box-shadow:0 6px 18px rgba(13,58,104,.055)!important;
  overflow:hidden!important;
  grid-template-columns:repeat(5,minmax(0,1fr))!important;
  gap:6px!important;
  align-items:end!important;
}
#globalFilters.v209-commercial-filter:not(.hidden){
  display:grid!important;
}
#globalFilters.v209-commercial-filter.hidden{display:none!important}

#globalFilters .v209-commercial-filter-brand{
  grid-column:1/-1!important;
  display:flex!important;
  align-items:center!important;
  gap:8px!important;
  min-height:35px!important;
  margin:0 -7px 1px!important;
  padding:6px 9px!important;
  background:linear-gradient(100deg,#0b3a6e 0%,#0c579e 62%,#0d7ff4 100%)!important;
  color:#fff!important;
}
.v209-commercial-filter-brand .v209-filter-icon{
  display:grid!important;
  place-items:center!important;
  width:24px!important;
  height:24px!important;
  flex:0 0 24px!important;
  border-radius:7px!important;
  background:rgba(255,255,255,.14)!important;
}
.v209-commercial-filter-brand svg{
  width:14px!important;height:14px!important;stroke:#fff!important;
}
.v209-commercial-filter-brand b{
  display:block!important;
  color:#fff!important;
  font-size:9px!important;
  line-height:1!important;
  font-weight:900!important;
}
.v209-commercial-filter-brand small{
  display:block!important;
  margin-top:3px!important;
  color:rgba(255,255,255,.73)!important;
  font-size:6.8px!important;
  line-height:1!important;
  font-weight:650!important;
}

#globalFilters.v209-commercial-filter>.filter{
  min-width:0!important;
  width:100%!important;
  margin:0!important;
}
#globalFilters.v209-commercial-filter>.filter label{
  display:block!important;
  margin:0 0 3px!important;
  color:#58708b!important;
  font-size:7px!important;
  line-height:1!important;
  font-weight:900!important;
  letter-spacing:.045em!important;
  text-transform:uppercase!important;
}
#globalFilters.v209-commercial-filter>.filter select,
#globalFilters.v209-commercial-filter>.filter input{
  width:100%!important;
  height:34px!important;
  min-height:34px!important;
  max-height:34px!important;
  margin:0!important;
  padding:0 7px!important;
  border:1px solid #c9d7e5!important;
  border-radius:8px!important;
  background:#f8fbff!important;
  color:#173f70!important;
  font-size:10px!important;
  font-weight:800!important;
  box-shadow:none!important;
}
#globalFilters.v209-commercial-filter>.primary,
#globalFilters.v209-commercial-filter>.or-clear-filters{
  width:100%!important;
  height:34px!important;
  min-height:34px!important;
  border-radius:8px!important;
  font-size:9.5px!important;
}

/* Título contextual siempre inmediatamente bajo el dock. */
body[data-v163-module="analysis"] #v207Context-analysis,
body[data-v163-module="operativo"] #v207Context-cm{
  margin-top:3px!important;
  margin-bottom:7px!important;
}

/* Escritorio: el orden se lee de izquierda a derecha; no se recentra circularmente. */
@media(min-width:901px){
  #operativoNav.v209-static-nav,
  #analysisNav.v209-static-nav{
    scroll-snap-type:x proximity!important;
  }
}

/* Móvil: conserva carrusel horizontal, pero mantiene el orden lógico aprobado. */
@media(max-width:900px){
  #operativoNav.v209-static-nav,
  #analysisNav.v209-static-nav{
    justify-content:flex-start!important;
    gap:5px!important;
    min-height:68px!important;
    width:auto!important;
    max-width:none!important;
    margin-left:-6px!important;
    margin-right:-6px!important;
    padding:4px max(12px,calc((100vw - 78px)/2)) 9px!important;
    scroll-padding-inline:calc((100vw - 78px)/2)!important;
  }
  #operativoNav.v209-static-nav>button,
  #analysisNav.v209-static-nav>button{
    flex-basis:78px!important;
    width:78px!important;
    min-width:78px!important;
    max-width:78px!important;
    height:60px!important;
    min-height:60px!important;
    max-height:60px!important;
  }
  #globalFilters.v209-commercial-filter{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;
    padding-bottom:6px!important;
  }
  #globalFilters.v209-commercial-filter>.primary:last-of-type{
    grid-column:1/-1!important;
  }
}

@media(max-width:900px) and (orientation:landscape){
  #globalFilters.v209-commercial-filter{
    grid-template-columns:repeat(5,minmax(0,1fr))!important;
  }
  #globalFilters.v209-commercial-filter>.primary:last-of-type{
    grid-column:auto!important;
  }
}
</style>'''

    js = r'''<script id="v209-report-nav-order-js">
(function(){
  if(window.__V209_REPORT_NAV_ORDER)return;
  window.__V209_REPORT_NAV_ORDER=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const norm=s=>String(s||'').replace(/s+/g,' ').trim().toLowerCase();

  /* Marcador síncrono: los scripts defer del carrusel lo leen antes de iniciar. */
  function markStatic(){
    ['operativoNav','analysisNav'].forEach(id=>{
      const nav=document.getElementById(id);
      if(nav)nav.dataset.v209StaticOrder='1';
    });
  }
  markStatic();

  const icons={
    dashboard:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    repeat:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7h12l-3-3m3 3-3 3M17 17H5l3 3m-3-3 3-3"/></svg>',
    dollar:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M15 8.5c-.7-.7-1.7-1-3-1-1.7 0-3 .8-3 2s1.3 1.8 3 2 3 .8 3 2-1.3 2-3 2c-1.3 0-2.4-.4-3-1M12 5v14"/></svg>',
    store:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h16M6 10V7l2-3h8l2 3v3M6 10v9h12v-9M9 19v-5h6v5"/></svg>',
    route:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 17c3-1 2-5 5-6s3-3 3-3"/></svg>',
    productivity:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="m4 8 6-5 6 8 5-4"/></svg>',
    settings:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19 13.5v-3l-2-.6-.7-1.7 1-1.8-2.1-2.1-1.8 1-1.7-.7L11 2H8l-.6 2.6-1.7.7-1.8-1-2.1 2.1 1 1.8-.7 1.7-2 .6v3l2 .6.7 1.7-1 1.8 2.1 2.1 1.8-1 1.7.7L8 22h3l.6-2.6 1.7-.7 1.8 1 2.1-2.1-1-1.8.7-1.7 2-.6Z"/></svg>',
    upload:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 16V4m0 0L7 9m5-5 5 5M4 20h16"/></svg>',
    percent:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="17" r="3"/><path d="M19 5 5 19"/></svg>',
    checklist:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m5 7 2 2 4-4M5 14l2 2 4-4M13 8h6M13 15h6"/></svg>',
    accordion:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="4" rx="1"/><rect x="4" y="10" width="16" height="4" rx="1"/><rect x="4" y="16" width="16" height="4" rx="1"/></svg>'
  };

  const cmDefs=[
    {key:'operations.center',selector:'[data-opview="Centro Ejecutivo"]',label:'Centro Operativo',icon:'dashboard'},
    {key:'operations.conversion',selector:'[data-opview="Conversión"]',label:'Conversión',icon:'repeat'},
    {key:'operations.recovery',selector:'[data-opview="Recuperación Económica"]',label:'Recuperación $',icon:'dollar'},
    {key:'operations.recovery_store',selector:'[data-opview="Recuperación por Tienda"]',label:'Recuperación por Tienda',icon:'store'},
    {key:'operations.routes',selector:'[data-opview="Cumplimiento de Recorridos"]',label:'Recorridos',icon:'route'},
    {key:'operations.productivity',selector:'[data-opview="Productividad por Colaborador"]',label:'Productividad',icon:'productivity'},
    {key:'operations.goals',selector:'#openGoalsBtn',label:'Metas y tiendas',icon:'settings'},
    {key:'operations.productivity_capture',selector:'[data-opview="Cargar productividad"]',label:'Cargar productividad',icon:'upload'},
    {key:'operations.upload',selector:'[data-opview="Carga de datos"]',label:'Carga de datos',icon:'upload'}
  ];

  const analysisDefs=[
    {key:'commercial.macro',selector:'[data-sub="macro"]',label:'Macro Compañía',icon:'dashboard',sub:'macro'},
    {key:'commercial.sellthrough',selector:'#v193SellBtn,[data-sub="sellthrough-clean"]',label:'Sell Through',icon:'percent',sub:'sellthrough-clean'},
    {key:'commercial.stores',selector:'[data-sub="stores"]',label:'Tiendas',icon:'store',sub:'stores'},
    {key:'commercial.lingerie_checklist',selector:'[data-sub="lingerie-checklist"]',label:'Checklist Lencería',icon:'checklist',sub:'lingerie-checklist'},
    {key:'commercial.upload',selector:'[data-sub="analysis-upload"]',label:'Carga de datos',icon:'upload',sub:'analysis-upload'},
    {key:'commercial.accordion',selector:'[data-sub="accordion"]',label:'Acordeón Comercial',icon:'accordion',sub:'accordion'}
  ];

  const cmMeta={
    'operations.center':['Centro Operativo','Resumen de Cambios y Muertos y seguimiento operativo'],
    'operations.conversion':['Conversión','Conversión de devolución a venta por periodo'],
    'operations.recovery':['Recuperación económica','Recuperación en pesos derivada de la venta'],
    'operations.recovery_store':['Recuperación por tienda','Comparativo de recuperación por tienda'],
    'operations.routes':['Cumplimiento de recorridos','Avance de recorridos contra la meta definida'],
    'operations.productivity':['Productividad por colaborador','Desempeño operativo por colaborador y tienda'],
    'operations.goals':['Metas y tiendas','Configuración de metas y alcance por tienda'],
    'operations.productivity_capture':['Cargar productividad','Registro digital de piezas y tiempo real'],
    'operations.upload':['Carga de datos','Actualización de la base de Cambios y Muertos']
  };
  const analysisMeta={
    'commercial.macro':['Macro Compañía','Vista general del desempeño comercial a nivel compañía'],
    'commercial.sellthrough':['Sell Through','Rotación por modelo con venta e inventario disponible'],
    'commercial.stores':['Tiendas','Radiografía comercial y comparativo por tienda'],
    'commercial.lingerie_checklist':['Checklist Lencería','Seguimiento de campeones y ejecución por familia'],
    'commercial.upload':['Carga de datos','Actualización de ventas, capacidades y existencias'],
    'commercial.accordion':['Acordeón Comercial','Lectura integral para toma de decisiones']
  };

  function cleanLegacyShell(nav){
    if(!nav)return;
    nav.classList.remove('rt-carousel','rt-icon-rail-v1');
    nav.classList.add('v209-static-nav');
    nav.dataset.v209StaticOrder='1';
    nav.style.removeProperty('--rt-edge-pad');

    const shell=nav.parentElement?.classList?.contains('rt-carousel-shell')?nav.parentElement:null;
    if(shell){
      const context=shell.querySelector(':scope > .v207-context-header');
      shell.parentNode.insertBefore(nav,shell);
      if(context)nav.insertAdjacentElement('afterend',context);
      shell.remove();
    }
    nav.parentElement?.querySelectorAll?.(':scope > .rt-icon-rail-v1-current,:scope > .rt-icon-rail-v1-indicator')
      .forEach(x=>x.remove());
  }

  function decorate(btn,def){
    if(!btn)return;
    btn.dataset.tabKey=def.key;
    btn.dataset.v209Key=def.key;
    btn.dataset.v206Decorated='1';
    btn.dataset.rtOriginalLabel=def.label;
    btn.dataset.rtLabel=def.label;
    btn.title=def.label;
    btn.setAttribute('role','tab');
    const wanted='<span class="v209-tab-icon" aria-hidden="true">'+icons[def.icon]+'</span>'+
                 '<span class="v209-tab-label">'+def.label+'</span>';
    if(!btn.querySelector('.v209-tab-label') || btn.querySelector('.v209-tab-label')?.textContent!==def.label){
      btn.innerHTML=wanted;
    }
  }

  function structuralHide(btn){
    if(!btn)return;
    btn.classList.add('v209-structural-hidden');
    btn.setAttribute('hidden','');
    btn.setAttribute('aria-hidden','true');
    btn.setAttribute('aria-selected','false');
    btn.classList.remove('active','rt-icon-user-active');
  }

  function enforceOrder(nav,defs){
    if(!nav)return [];
    cleanLegacyShell(nav);
    const keep=[];
    defs.forEach(def=>{
      const btn=q(def.selector,nav);
      if(!btn)return;
      decorate(btn,def);
      keep.push(btn);
    });

    qa(':scope > button',nav).forEach(btn=>{
      if(!keep.includes(btn))structuralHide(btn);
    });

    const frag=document.createDocumentFragment();
    keep.forEach(btn=>frag.appendChild(btn));
    qa(':scope > button',nav).filter(btn=>!keep.includes(btn)).forEach(btn=>frag.appendChild(btn));
    nav.appendChild(frag);
    return keep;
  }

  function visible(btn){
    if(!btn)return false;
    return !btn.hidden &&
      !btn.classList.contains('hidden') &&
      !btn.classList.contains('v209-structural-hidden') &&
      btn.getAttribute('aria-hidden')!=='true' &&
      getComputedStyle(btn).display!=='none';
  }

  function center(btn){
    if(!btn||window.innerWidth>900)return;
    try{btn.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}catch(_){}
  }

  function setActive(nav,btn){
    if(!nav||!btn)return;
    qa(':scope > button',nav).forEach(x=>{
      const on=x===btn;
      x.classList.toggle('active',on);
      x.classList.remove('rt-icon-user-active');
      x.setAttribute('aria-selected',on?'true':'false');
      x.tabIndex=on?0:-1;
    });
    center(btn);
  }

  function currentCmKey(){
    let view='';
    try{view=String(OP_VIEW||'')}catch(_){}
    const map={
      'Centro Ejecutivo':'operations.center',
      'Conversión':'operations.conversion',
      'Recuperación Económica':'operations.recovery',
      'Recuperación por Tienda':'operations.recovery_store',
      'Cumplimiento de Recorridos':'operations.routes',
      'Productividad por Colaborador':'operations.productivity',
      'Cargar productividad':'operations.productivity_capture',
      'Carga de datos':'operations.upload'
    };
    if(map[view])return map[view];
    const title=norm(q('#operativoDynamicTitle')?.textContent);
    if(title.includes('cargar productividad'))return'operations.productivity_capture';
    if(!q('#operativoCentro')?.classList.contains('hidden'))return'operations.center';
    return'';
  }

  function currentAnalysisKey(){
    if(q('#page-sellthrough-clean.active'))return'commercial.sellthrough';
    const page=q('section.page.active');
    const id=page?.id||'';
    const map={
      'page-macro':'commercial.macro',
      'page-stores':'commercial.stores',
      'page-lingerie-checklist':'commercial.lingerie_checklist',
      'page-analysis-upload':'commercial.upload',
      'page-accordion':'commercial.accordion'
    };
    if(map[id])return map[id];
    let sub='';
    try{sub=String(SUB||'')}catch(_){}
    return {
      macro:'commercial.macro',
      stores:'commercial.stores',
      'lingerie-checklist':'commercial.lingerie_checklist',
      'analysis-upload':'commercial.upload',
      accordion:'commercial.accordion',
      'sellthrough-clean':'commercial.sellthrough'
    }[sub]||'';
  }

  function updateContext(kind,key){
    const meta=kind==='cm'?cmMeta[key]:analysisMeta[key];
    const wrap=document.getElementById(kind==='cm'?'v207Context-cm':'v207Context-analysis');
    if(!wrap||!meta)return;
    const t=q('.v207-context-title',wrap),s=q('.v207-context-sub',wrap);
    if(t)t.textContent=meta[0];
    if(s)s.textContent=meta[1];
  }

  function syncActive(){
    const mod=norm(document.body.dataset.v163Module);
    if(mod==='operativo'){
      const nav=q('#operativoNav'),key=currentCmKey();
      const btn=key?q('[data-v209-key="'+key+'"]',nav):null;
      if(btn&&visible(btn))setActive(nav,btn);
      if(key)updateContext('cm',key);
    }
    if(mod==='analysis'){
      const nav=q('#analysisNav'),key=currentAnalysisKey();
      const btn=key?q('[data-v209-key="'+key+'"]',nav):null;
      if(btn&&visible(btn))setActive(nav,btn);
      if(key)updateContext('analysis',key);
    }
  }

  function ensureFilterBrand(filters){
    if(!filters)return;
    filters.classList.add('v209-commercial-filter');
    if(!q(':scope > .v209-commercial-filter-brand',filters)){
      const brand=document.createElement('div');
      brand.className='v209-commercial-filter-brand';
      brand.innerHTML='<span class="v209-filter-icon"><svg viewBox="0 0 24 24" fill="none" stroke-width="1.8"><path d="M4 5h16M7 12h10m-7 7h4"/></svg></span>'+
        '<div><b>Filtros del reporte</b><small>Define el alcance de la consulta comercial</small></div>';
      filters.prepend(brand);
    }
  }

  function placeCommercialFilters(){
    const nav=q('#analysisNav'),filters=q('#globalFilters');
    if(!nav||!filters)return;
    ensureFilterBrand(filters);
    const context=q('#v207Context-analysis')||nav;
    if(filters.previousElementSibling!==context)context.insertAdjacentElement('afterend',filters);
  }

  function enforceAll(){
    markStatic();
    const cm=q('#operativoNav'),an=q('#analysisNav');
    enforceOrder(cm,cmDefs);
    enforceOrder(an,analysisDefs);
    placeCommercialFilters();
    syncActive();
  }

  function normalRole(){
    try{
      const u=(typeof USER!=='undefined'?USER:null)||window.USER||null;
      return String(u?.role||'');
    }catch(_){return''}
  }

  async function openDefault(main){
    const role=normalRole();
    if(main==='operativo' && !['colaborador_operativo','colaborador','colaborador_lenceria'].includes(role)){
      const btn=q('#operativoNav [data-v209-key="operations.center"]');
      if(btn&&visible(btn)){
        try{
          if(typeof OP_VIEW!=='undefined')OP_VIEW='Centro Ejecutivo';
          if(typeof window.renderOperativoView==='function')await window.renderOperativoView('Centro Ejecutivo',true);
          else btn.click();
        }catch(_){btn.click()}
      }
    }
    if(main==='analysis' && role!=='colaborador_lenceria'){
      const btn=q('#analysisNav [data-v209-key="commercial.macro"]');
      if(btn&&visible(btn)){
        try{
          if(typeof window.goSub==='function')await window.goSub('macro');
          else if(typeof goSub==='function')await goSub('macro');
          else btn.click();
        }catch(_){btn.click()}
      }
    }
    setTimeout(()=>{enforceAll();syncActive()},90);
  }

  document.addEventListener('click',e=>{
    const main=e.target.closest?.('[data-main]');
    if(main){
      const name=String(main.dataset.main||'');
      [40,120,300].forEach(ms=>setTimeout(enforceAll,ms));
      if(name==='operativo'||name==='analysis')setTimeout(()=>openDefault(name),150);
    }
    const tab=e.target.closest?.('#operativoNav>button,#analysisNav>button');
    if(tab)[30,120,320].forEach(ms=>setTimeout(()=>{enforceAll();syncActive()},ms));
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>{
    [20,100,260].forEach(ms=>setTimeout(enforceAll,ms));
  });

  const mo=new MutationObserver(mutations=>{
    if(!mutations.some(m=>m.type==='childList'||m.attributeName==='class'||m.attributeName==='hidden'||m.attributeName==='aria-selected'))return;
    clearTimeout(window.__v209NavSync);
    window.__v209NavSync=setTimeout(enforceAll,25);
  });

  function setup(){
    enforceAll();
    ['operativoNav','analysisNav'].forEach(id=>{
      const nav=document.getElementById(id);
      if(nav&&nav.dataset.v209Observed!=='1'){
        nav.dataset.v209Observed='1';
        mo.observe(nav,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-selected','style']});
      }
    });
    const pages=q('#appView');
    if(pages&&pages.dataset.v209Observed!=='1'){
      pages.dataset.v209Observed='1';
      mo.observe(pages,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
    }
  }

  setup();
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});
  [120,350,800,1500,2800].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('resize',()=>setTimeout(enforceAll,90),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});

  console.info('[V209] orden definitivo de pestañas y filtros comerciales inferiores activo.');
})();
</script>'''

    @m.app.middleware("http")
    async def v209_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v209-report-nav-order-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v209-report-nav-order-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V209",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V209] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V209_REPORT_NAV_ORDER_FILTERS = True
    print("[V209] orden final de tabs + filtros comerciales inferiores instalado.", flush=True)
