"""V264 · Paridad responsive laptop → tablet/móvil.

Capa final exclusivamente visual:
- conserva la estructura y el orden de escritorio;
- elimina cortes/overflow globales;
- hace que pestañas, filtros, KPIs y tablas se adapten al viewport;
- corrige el subtítulo duplicado de Filtros del reporte;
- no modifica datos, cálculos, endpoints, permisos ni lógica de filtros.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V264_UNIFORM_RESPONSIVE", False):
        return

    css = r'''<style id="v264-uniform-responsive-css">
:root{
  --v264-page-x:clamp(5px,1.55vw,18px);
  --v264-gap:clamp(4px,.8vw,12px);
  --v264-radius:clamp(9px,1.1vw,15px);
}

html,body{
  width:100%!important;
  max-width:100%!important;
  margin-left:0!important;
  margin-right:0!important;
  overflow-x:hidden!important;
  -webkit-text-size-adjust:100%;
  text-size-adjust:100%;
}
*,*::before,*::after{box-sizing:border-box!important}
img,svg,canvas,video,iframe{max-width:100%}

#appView,.shell,.main,section.page,
#operativoCentro,#operativoDynamic,#operativoDynamicContent,
#analysisDynamic,#operativoPeriodBar,#v161FilterBar,#v161FilterGrid,
.panel,.card,.filters,.tablewrap,.chart-box,.chart-scroll{
  min-width:0!important;
  max-width:100%!important;
}

/* No esconder errores internos: el scroll horizontal sólo vive dentro de tablas. */
.tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow-x:auto!important;
  overscroll-behavior-x:contain!important;
  -webkit-overflow-scrolling:touch!important;
  touch-action:pan-x pan-y!important;
}

/* Tablas pequeñas (marcadas por JS) caben completas como en laptop. */
.tablewrap > table.v264-fit-table,
.model-sticky-table > table.v264-fit-table{
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  table-layout:auto!important;
}
table.v264-fit-table th,
table.v264-fit-table td{
  white-space:normal!important;
  overflow-wrap:anywhere!important;
}

/* Tablas grandes conservan la tabla real y desplazan sólo su contenedor. */
.tablewrap > table.v264-scroll-table,
.model-sticky-table > table.v264-scroll-table{
  width:max-content!important;
  min-width:max(100%,calc(var(--v264-cols,8) * 72px))!important;
  max-width:none!important;
}

/* Gráficas siempre responden al contenedor. */
.chart-box,.chart-scroll,
[data-testid="stPlotlyChart"],[data-testid="stVegaLiteChart"],
.js-plotly-plot,.plot-container,.svg-container{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
}
.chart-box svg,.chart-scroll svg,.combo-svg,.recovery-svg{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  height:auto!important;
}

/* ===== Tablet: misma composición, más compacta y sin carriles cortados ===== */
@media (min-width:768px) and (max-width:1023px){
  .main{
    width:100%!important;
    max-width:100%!important;
    padding-left:clamp(8px,1.4vw,14px)!important;
    padding-right:clamp(8px,1.4vw,14px)!important;
    overflow-x:hidden!important;
  }

  #operativoNav,#analysisNav,#v200OperationTabs{
    display:grid!important;
    grid-template-columns:repeat(var(--v264-tab-count,8),minmax(0,1fr))!important;
    gap:5px!important;
    width:100%!important;
    max-width:100%!important;
    overflow:visible!important;
    white-space:normal!important;
  }
  #operativoNav>button,#analysisNav>button,#v200OperationTabs>button,
  #operativoNav .switch,#analysisNav .switch,#v200OperationTabs .switch{
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
    min-height:54px!important;
    padding:6px 4px!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    text-align:center!important;
    font-size:clamp(8px,1.05vw,11px)!important;
    line-height:1.08!important;
  }

  html body #appView #operativoPeriodBar>.or-report-filter-grid{
    display:flex!important;
    flex-wrap:wrap!important;
    gap:8px!important;
    width:100%!important;
    max-width:100%!important;
    overflow:visible!important;
  }
  html body #appView #operativoPeriodBar .v259-period-view{
    flex:1.7 1 330px!important;
    min-width:280px!important;
    width:auto!important;
  }
  html body #appView #operativoPeriodBar>.or-report-filter-grid>.or-fcontrol:not(.hidden):not(.v249-hidden){
    flex:1 1 155px!important;
    min-width:145px!important;
    width:auto!important;
  }

  html body #appView #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
    gap:7px!important;
    overflow:visible!important;
  }
  html body #appView #v161FilterGrid .v161-field{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
  }

  .kpis,.report-kpis,.lingerie-kpis,.kpis.or-kpi-matrix{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
  }
}

/* ===== Móvil: la vista de laptop comprimida al ancho real ===== */
@media (max-width:767px){
  .main{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    padding:
      max(4px,env(safe-area-inset-top))
      max(var(--v264-page-x),env(safe-area-inset-left))
      calc(58px + env(safe-area-inset-bottom))
      max(var(--v264-page-x),env(safe-area-inset-right))!important;
    overflow-x:hidden!important;
  }

  /* Encabezado completo, sin elipsis ni texto cortado. */
  .hero{
    width:100%!important;
    max-width:100%!important;
    min-height:0!important;
    padding:clamp(8px,2.1vw,12px) clamp(9px,2.4vw,14px)!important;
    margin:0 0 5px!important;
    border-radius:clamp(11px,2.8vw,15px)!important;
    gap:7px!important;
  }
  .hero h1{
    margin:0!important;
    max-width:calc(100% - 52px)!important;
    font-size:clamp(18px,5.1vw,24px)!important;
    line-height:1.04!important;
    white-space:normal!important;
    overflow:visible!important;
    text-overflow:clip!important;
    overflow-wrap:anywhere!important;
  }
  .hero p{
    margin:3px 0 0!important;
    max-width:calc(100% - 52px)!important;
    font-size:clamp(9px,2.6vw,12px)!important;
    line-height:1.15!important;
    white-space:normal!important;
    overflow:visible!important;
    text-overflow:clip!important;
    overflow-wrap:anywhere!important;
  }

  /* Pestañas: todas caben en el ancho disponible; nada se encime ni se corte. */
  #operativoNav,#analysisNav,#v200OperationTabs{
    display:grid!important;
    grid-template-columns:repeat(var(--v264-tab-count,8),minmax(0,1fr))!important;
    grid-auto-flow:row!important;
    align-items:stretch!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    gap:3px!important;
    padding:4px!important;
    margin:0 0 6px!important;
    overflow:visible!important;
    white-space:normal!important;
    scroll-snap-type:none!important;
  }
  #operativoNav>div,#analysisNav>div,#v200OperationTabs>div{
    display:contents!important;
  }
  #operativoNav>button,#analysisNav>button,#v200OperationTabs>button,
  #operativoNav .switch,#analysisNav .switch,#v200OperationTabs .switch{
    width:100%!important;
    max-width:none!important;
    min-width:0!important;
    flex:none!important;
    min-height:58px!important;
    padding:5px 2px!important;
    margin:0!important;
    border-radius:10px!important;
    white-space:normal!important;
    overflow:hidden!important;
    overflow-wrap:anywhere!important;
    word-break:normal!important;
    text-align:center!important;
    font-size:clamp(7.4px,2.0vw,9.4px)!important;
    line-height:1.02!important;
  }
  #operativoNav svg,#analysisNav svg,#v200OperationTabs svg,
  #operativoNav .mnav-icon,#analysisNav .mnav-icon,#v200OperationTabs .mnav-icon{
    width:clamp(13px,3.5vw,17px)!important;
    height:clamp(13px,3.5vw,17px)!important;
    max-width:100%!important;
    margin:0 auto 3px!important;
  }

  .title{
    margin:7px 1px 3px!important;
    font-size:clamp(17px,4.7vw,22px)!important;
    line-height:1.08!important;
    overflow-wrap:anywhere!important;
  }
  .subtitle{
    margin:0 1px 6px!important;
    font-size:clamp(10px,2.85vw,13px)!important;
    line-height:1.2!important;
    overflow-wrap:anywhere!important;
  }

  /* Filtros Opción 9B: SIN scroll horizontal. La primera fila replica laptop:
     Vista operativa + Periodo; los filtros extra continúan compactos debajo. */
  html body #appView #operativoPeriodBar{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    padding:0 6px 7px!important;
    margin:5px 0 7px!important;
    border-radius:12px!important;
    overflow:hidden!important;
  }
  html body #appView #operativoPeriodBar>.or-report-filter-brand{
    width:calc(100% + 12px)!important;
    min-height:48px!important;
    margin:0 -6px 7px!important;
    padding:7px 9px!important;
    gap:8px!important;
    border-radius:0!important;
  }
  html body #appView #operativoPeriodBar .or-report-filter-brand-icon{
    width:35px!important;
    min-width:35px!important;
    height:35px!important;
    border-radius:10px!important;
  }
  html body #appView #operativoPeriodBar .or-report-filter-brand-icon svg{
    width:18px!important;
    height:18px!important;
  }
  html body[data-v163-module="operativo"] #appView #operativoPeriodBar>.or-report-filter-brand b{
    font-size:clamp(15px,4.2vw,19px)!important;
    line-height:1.02!important;
    white-space:normal!important;
  }
  html body[data-v163-module="operativo"] #appView #operativoPeriodBar>.or-report-filter-brand small{
    display:block!important;
    margin-top:2px!important;
    font-size:clamp(9px,2.55vw,11px)!important;
    line-height:1.08!important;
    white-space:normal!important;
  }
  html body[data-v163-module="operativo"] #appView #operativoPeriodBar>.or-report-filter-brand small::after{
    content:none!important;
    display:none!important;
  }

  html body #appView #operativoPeriodBar>.or-report-filter-grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.55fr) minmax(0,.85fr)!important;
    grid-auto-flow:row dense!important;
    align-items:end!important;
    gap:5px!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    padding:0!important;
    margin:0!important;
    overflow:visible!important;
  }
  html body #appView #operativoPeriodBar .v259-period-view{
    grid-column:1!important;
    display:flex!important;
    flex:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    margin:0!important;
    gap:3px!important;
  }
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operPeriodSelectWrap{
    grid-column:2!important;
  }
  html body #appView #operativoPeriodBar>.or-report-filter-grid>.or-fcontrol:not(.hidden):not(.v249-hidden),
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operPeriodSelectWrap,
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operStoreWrap,
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operAreaWrap,
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operActivityWrap,
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operStartWrap,
  html body #appView #operativoPeriodBar>.or-report-filter-grid>#operEndWrap{
    flex:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    margin:0!important;
  }

  html body #appView #operativoPeriodBar .v259-period-title{
    height:auto!important;
    min-height:13px!important;
    margin:0 0 2px!important;
    gap:4px!important;
    font-size:clamp(7px,2.1vw,9px)!important;
    line-height:1!important;
  }
  html body #appView #operativoPeriodBar .v259-period-title-icon,
  html body #appView #operativoPeriodBar .v259-period-title-icon svg{
    width:13px!important;
    height:13px!important;
    min-width:13px!important;
  }
  html body #appView #operativoPeriodBar .v259-period-buttons{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:38px!important;
    height:38px!important;
    border-radius:10px!important;
  }
  html body #appView #operativoPeriodBar .v259-period-btn{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:38px!important;
    height:38px!important;
    padding:0 2px!important;
    gap:2px!important;
    font-size:clamp(7px,1.95vw,9px)!important;
    line-height:1!important;
    white-space:nowrap!important;
  }
  html body #appView #operativoPeriodBar .v259-period-mode-icon,
  html body #appView #operativoPeriodBar .v259-period-mode-icon svg{
    width:12px!important;
    height:12px!important;
    min-width:12px!important;
  }

  html body #appView #operativoPeriodBar .or-fcontrol label{
    margin:0 0 3px!important;
    gap:4px!important;
    font-size:clamp(7px,2.05vw,9px)!important;
    line-height:1!important;
  }
  html body #appView #operativoPeriodBar .or-fcontrol-icon,
  html body #appView #operativoPeriodBar .or-fcontrol-icon svg{
    width:14px!important;
    height:14px!important;
    min-width:14px!important;
  }
  html body #appView #operativoPeriodBar select,
  html body #appView #operativoPeriodBar input{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:38px!important;
    height:38px!important;
    padding:5px 25px 5px 8px!important;
    border-radius:10px!important;
    font-size:clamp(9px,2.65vw,12px)!important;
    line-height:1!important;
    text-overflow:ellipsis!important;
  }

  /* Análisis Comercial: mismos filtros, adaptados al ancho y sin carril lateral. */
  html body #appView #v161FilterBar{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    padding:0 6px 7px!important;
    margin:5px 0 7px!important;
    overflow:hidden!important;
  }
  html body #appView #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    overflow:visible!important;
    padding:0!important;
  }
  html body #appView #v161FilterGrid .v161-field{
    flex:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    padding:4px 6px 5px 30px!important;
    border-right:0!important;
  }
  html body #appView #v161FilterGrid .v166-filter-icon{
    left:7px!important;
    width:18px!important;
    height:18px!important;
  }
  html body #appView #v161FilterGrid .v166-filter-icon svg{
    width:17px!important;
    height:17px!important;
  }
  html body #appView #v161FilterGrid .v161-field label{
    font-size:clamp(7px,2vw,9px)!important;
  }
  html body #appView #v161FilterGrid .v161-field select,
  html body #appView #v161FilterGrid .v161-field input{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    height:34px!important;
    min-height:34px!important;
    font-size:clamp(9px,2.5vw,11px)!important;
  }

  /* Filtros genéricos. */
  .filters{
    width:100%!important;
    max-width:100%!important;
    display:grid!important;
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;
    padding:6px!important;
    overflow:visible!important;
  }
  .filters .filter,.filter select,.filter input{
    min-width:0!important;
    max-width:100%!important;
    width:100%!important;
  }

  /* KPIs: exactamente dos por fila en móvil, como el reporte de laptop comprimido. */
  .kpis,.report-kpis,.lingerie-kpis,.kpis.or-kpi-matrix{
    display:grid!important;
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;
    width:100%!important;
    max-width:100%!important;
  }
  .kpi,.report-kpi{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:0!important;
    height:auto!important;
    padding:clamp(8px,2vw,11px)!important;
    border-radius:11px!important;
    overflow:hidden!important;
  }
  .lab,.report-kpi .rk-label{
    font-size:clamp(8px,2.25vw,10px)!important;
    line-height:1.08!important;
    overflow-wrap:anywhere!important;
  }
  .val,.report-kpi .rk-value{
    margin:5px 0 2px!important;
    font-size:clamp(20px,5.8vw,28px)!important;
    line-height:1!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
  }
  .note,.report-kpi .rk-note,.report-kpi .rk-sub{
    font-size:clamp(8px,2.2vw,10px)!important;
    line-height:1.14!important;
    overflow-wrap:anywhere!important;
  }

  .cards{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;
  }
  .card,.panel{
    min-width:0!important;
    max-width:100%!important;
    padding:clamp(8px,2vw,11px)!important;
  }

  /* Densidad de tablas: pequeñas visibles completas; grandes con scroll interno. */
  .table{
    font-size:clamp(9px,2.45vw,11px)!important;
    font-variant-numeric:tabular-nums!important;
  }
  .table th,.table td{
    padding:7px 7px!important;
    line-height:1.12!important;
  }
  table.v264-fit-table th,
  table.v264-fit-table td{
    padding:8px 8px!important;
    white-space:normal!important;
  }
  table.v264-fit-table th:last-child,
  table.v264-fit-table td:last-child{
    text-align:right;
  }
  .table th{
    position:sticky;
    top:0;
    z-index:10;
  }

  /* Controles y botones nunca exceden el viewport. */
  input,select,button,textarea{
    max-width:100%!important;
  }
}

/* iPhone / Android pequeños: comprimir antes de apilar. */
@media (max-width:430px){
  :root{--v264-page-x:4px}
  #operativoNav,#analysisNav,#v200OperationTabs{
    gap:2px!important;
    padding:3px!important;
  }
  #operativoNav>button,#analysisNav>button,#v200OperationTabs>button,
  #operativoNav .switch,#analysisNav .switch,#v200OperationTabs .switch{
    min-height:56px!important;
    padding:4px 1px!important;
    border-radius:9px!important;
    font-size:clamp(7px,1.92vw,8.4px)!important;
  }
  html body #appView #operativoPeriodBar>.or-report-filter-grid{
    grid-template-columns:minmax(0,1.58fr) minmax(0,.82fr)!important;
    gap:4px!important;
  }
  html body #appView #operativoPeriodBar .v259-period-btn{
    gap:1px!important;
    padding:0 1px!important;
    font-size:clamp(6.7px,1.82vw,8px)!important;
  }
}

/* 320–360 px: mantener dos KPI y la misma primera fila de filtros. */
@media (max-width:360px){
  .kpis,.report-kpis,.lingerie-kpis,.kpis.or-kpi-matrix,.cards{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:4px!important;
  }
  .kpi,.report-kpi,.card,.panel{padding:7px!important}
  .val,.report-kpi .rk-value{font-size:18px!important}
  html body #appView #operativoPeriodBar>.or-report-filter-grid{
    grid-template-columns:minmax(0,1.6fr) minmax(0,.8fr)!important;
  }
  html body #appView #operativoPeriodBar .v259-period-mode-icon,
  html body #appView #operativoPeriodBar .v259-period-mode-icon svg{
    width:10px!important;height:10px!important;min-width:10px!important;
  }
}

/* Landscape móvil = mini laptop. */
@media (max-width:900px) and (orientation:landscape){
  .kpis,.report-kpis,.lingerie-kpis,.kpis.or-kpi-matrix{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
  }
  .cards{grid-template-columns:repeat(3,minmax(0,1fr))!important}
  html body #appView #operativoPeriodBar>.or-report-filter-grid{
    display:flex!important;
    flex-wrap:wrap!important;
    overflow:visible!important;
  }
  html body #appView #operativoPeriodBar .v259-period-view{
    flex:1.55 1 300px!important;
    min-width:260px!important;
    width:auto!important;
  }
  html body #appView #operativoPeriodBar>.or-report-filter-grid>.or-fcontrol:not(.hidden):not(.v249-hidden){
    flex:1 1 145px!important;
    width:auto!important;
    min-width:130px!important;
  }
}
</style>'''

    js = r'''<script id="v264-uniform-responsive-js">
(function(){
  if(window.__V264_UNIFORM_RESPONSIVE)return;
  window.__V264_UNIFORM_RESPONSIVE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function visible(el){
    if(!el || el.hidden || el.classList.contains('hidden') || el.classList.contains('v249-hidden'))return false;
    const cs=getComputedStyle(el);
    return cs.display!=='none' && cs.visibility!=='hidden';
  }

  function syncNav(nav){
    if(!nav)return;
    const buttons=qa(':scope > button',nav).filter(visible);
    const count=Math.max(1,buttons.length);
    nav.style.setProperty('--v264-tab-count',String(count));
  }

  function fixFilterBrand(){
    const small=q('#operativoPeriodBar > .or-report-filter-brand small');
    if(small && small.textContent.trim()!=='Define la vista del reporte'){
      small.textContent='Define la vista del reporte';
    }
  }

  function classifyTable(table){
    if(!table)return;
    const head=table.querySelector('thead tr');
    const row=head||table.querySelector('tr');
    const cols=row ? row.querySelectorAll('th,td').length : 0;
    if(!cols)return;
    table.style.setProperty('--v264-cols',String(cols));
    const fit=cols<=4;
    table.classList.toggle('v264-fit-table',fit);
    table.classList.toggle('v264-scroll-table',!fit);
  }

  function sync(){
    syncNav(q('#operativoNav'));
    syncNav(q('#analysisNav'));
    syncNav(q('#v200OperationTabs'));
    fixFilterBrand();
    qa('.tablewrap > table,.model-sticky-table > table,.table-scroll-35 > table,.model-scroll-30 > table').forEach(classifyTable);
  }

  let timer=0;
  function queue(delay=45){
    clearTimeout(timer);
    timer=setTimeout(sync,delay);
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav,#analysisNav,#v200OperationTabs,[data-main]')){
      [0,60,180,420].forEach(ms=>setTimeout(sync,ms));
    }
  },false);

  document.addEventListener('change',e=>{
    if(e.target.closest?.('#operativoPeriodBar,#v161FilterBar,#globalFilters')){
      [0,70,220].forEach(ms=>setTimeout(sync,ms));
    }
  },false);

  window.addEventListener('resize',()=>queue(35),{passive:true});
  window.addEventListener('orientationchange',()=>[50,220,520].forEach(ms=>setTimeout(sync,ms)),{passive:true});

  const observer=new MutationObserver(()=>queue(70));
  function start(){
    const root=q('.main')||document.body;
    if(root)observer.observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','style']});
    sync();
    [120,350,800,1600].forEach(ms=>setTimeout(sync,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V264] paridad responsive laptop/tablet/móvil activa.');
})();
</script>'''

    @m.app.middleware("http")
    async def v264_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")

            if 'id="v264-uniform-responsive-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v264-uniform-responsive-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)

            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V264-UNIFORM-RESPONSIVE",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V264] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V264_UNIFORM_RESPONSIVE = True
    print("[V264] paridad responsive laptop/tablet/móvil instalada.",flush=True)
