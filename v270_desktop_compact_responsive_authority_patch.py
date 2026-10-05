"""V270 · Autoridad responsive global Desktop Compact.

Objetivo:
- Laptop/PC es la referencia visual.
- Móvil, tablet e iPad conservan la misma estructura y orden, compactados al ancho real.
- Sin scroll horizontal global; sólo tablas grandes pueden desplazar internamente.
- No altera datos, cálculos, endpoints, filtros, roles, permisos, login ni eventos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V270_DESKTOP_COMPACT_RESPONSIVE", False):
        return

    css = r'''<style id="v270-desktop-compact-responsive-css">
/* =========================================================
   V270 · AUTORIDAD RESPONSIVE GLOBAL
   Laptop/PC = referencia. Tablet/móvil = misma vista compacta.
   ========================================================= */

:root{
  --v270-page-x:clamp(4px,1vw,16px);
  --v270-gap:clamp(4px,.65vw,10px);
  --v270-radius:clamp(8px,.9vw,14px);
}

/* ---------- Base de ancho real ---------- */
html,body{
  width:100%!important;
  max-width:100%!important;
  margin:0!important;
  overflow-x:hidden!important;
  -webkit-text-size-adjust:100%!important;
  text-size-adjust:100%!important;
}
*,*::before,*::after{box-sizing:border-box!important}
img,svg,canvas,video,iframe{max-width:100%!important}

#appView,.shell,.main,section.page,
#operativoCentro,#operativoDynamic,#operativoDynamicContent,
#analysisDynamic,#operativoPeriodBar,#v161FilterBar,#v161FilterGrid,
.panel,.card,.filters,.chart-box,.chart-scroll,
.report-kpis,.kpis,.cards,.grid,.uploadgrid,.usergrid{
  min-width:0!important;
  max-width:100%!important;
}

.main{
  width:auto!important;
  max-width:100%!important;
  min-width:0!important;
  overflow-x:hidden!important;
}

/* ---------- Pestañas: misma matriz de desktop ---------- */
body.v238-module-operativo #operativoNav:not(.hidden),
body.v238-module-analysis #analysisNav:not(.hidden),
body.v238-module-operation #v200OperationTabs:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(var(--v270-tab-count,var(--v238-count,5)),minmax(0,1fr))!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow:hidden!important;
  white-space:normal!important;
  touch-action:pan-y!important;
}

body.v238-module-operativo #operativoNav>button,
body.v238-module-analysis #analysisNav>button,
body.v238-module-operation #v200OperationTabs>button{
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  overflow:hidden!important;
  white-space:normal!important;
  text-align:center!important;
}

/* ---------- Filtros ---------- */
#operativoPeriodBar,
#v161FilterBar{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow:hidden!important;
}
#operativoPeriodBar>.or-report-filter-grid,
#v161FilterGrid{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
}
#operativoPeriodBar .or-fcontrol,
#v161FilterGrid .v161-field{
  min-width:0!important;
  max-width:100%!important;
}
#operativoPeriodBar select,
#operativoPeriodBar input,
#v161FilterGrid select,
#v161FilterGrid input,
.filters select,.filters input{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  text-overflow:ellipsis!important;
}

/* ---------- KPIs / cards ---------- */
.kpis:not(.v149-kpis):not(.v204-kpis),
.report-kpis:not(.v149-kpis):not(.v204-kpis),
.lingerie-kpis{
  display:grid!important;
  grid-template-columns:repeat(var(--v270-kpi-cols,4),minmax(0,1fr))!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  gap:var(--v270-gap)!important;
}
.cards{
  display:grid!important;
  grid-template-columns:repeat(var(--v270-card-cols,3),minmax(0,1fr))!important;
  gap:var(--v270-gap)!important;
}
.kpi,.report-kpi,.card,.panel{
  min-width:0!important;
  max-width:100%!important;
  overflow:hidden!important;
}

/* ---------- Tablas: scroll interno solamente ---------- */
.tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30,
.monthly-cross-desktop,.lingerie-table-wrap{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
  touch-action:pan-x pan-y!important;
}
table.v270-fit-table{
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  table-layout:auto!important;
}
table.v270-scroll-table{
  width:max-content!important;
  min-width:max(100%,calc(var(--v270-cols,8) * 68px))!important;
  max-width:none!important;
}
.table th,.table td,
table th,table td{
  font-variant-numeric:tabular-nums;
}

/* ---------- Gráficas ---------- */
.chart-box,.chart-scroll,
[data-testid="stPlotlyChart"],[data-testid="stVegaLiteChart"],
.js-plotly-plot,.plot-container,.svg-container,
.combo-svg,.recovery-svg{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
}
.chart-box svg,.chart-scroll svg,.combo-svg,.recovery-svg,
.js-plotly-plot .plot-container,.js-plotly-plot .svg-container{
  max-width:100%!important;
}

/* =========================================================
   TABLET / IPAD LANDSCAPE 900–1024
   Misma vista de laptop, compactada al ancho disponible
   ========================================================= */
@media (min-width:900px) and (max-width:1024px){
  :root{--v270-page-x:8px;--v270-gap:6px}
  .main{
    width:100%!important;
    max-width:100%!important;
    padding-left:8px!important;
    padding-right:8px!important;
  }
  .hero{
    padding:12px 14px!important;
    margin-bottom:6px!important;
    border-radius:13px!important;
  }
  .hero h1{font-size:20px!important;line-height:1.04!important}
  .hero p{font-size:9px!important;margin-top:3px!important}
  .title{font-size:17px!important;margin:7px 0 4px!important}
  .subtitle{font-size:9px!important;margin:0 0 6px!important}

  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    height:54px!important;min-height:54px!important;max-height:54px!important;
    grid-template-rows:54px!important;
    column-gap:3px!important;
    margin:5px 0 7px!important;
    padding:0 1px!important;
  }
  body.v238-module-operativo #operativoNav>button,
  body.v238-module-analysis #analysisNav>button,
  body.v238-module-operation #v200OperationTabs>button{
    height:54px!important;min-height:54px!important;max-height:54px!important;
    padding:4px 2px!important;border-radius:9px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-icon,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-icon{
    width:15px!important;height:15px!important;min-width:15px!important;min-height:15px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-label,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-label{
    font-size:7.3px!important;line-height:1.02!important;height:24px!important;min-height:24px!important;
  }

  #operativoPeriodBar{padding:0 7px 7px!important;margin:5px 0 7px!important}
  #operativoPeriodBar>.or-report-filter-brand{
    min-height:48px!important;padding:7px 10px!important;margin-bottom:6px!important;
  }
  #operativoPeriodBar>.or-report-filter-grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.75fr) repeat(var(--v270-oper-filter-cols,2),minmax(0,1fr))!important;
    gap:6px!important;align-items:end!important;overflow:visible!important;
  }
  #operativoPeriodBar .v266-period-view{
    min-width:0!important;width:100%!important;max-width:100%!important;flex:none!important;
  }
  #operativoPeriodBar .v266-period-buttons,
  #operativoPeriodBar .v266-period-btn{
    height:42px!important;min-height:42px!important;
  }
  #operativoPeriodBar .v266-period-btn{font-size:8px!important;padding:0 4px!important;gap:3px!important}
  #operativoPeriodBar select,#operativoPeriodBar input{
    height:42px!important;min-height:42px!important;font-size:10px!important;
  }

  #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(var(--v270-analysis-cols,5),minmax(0,1fr))!important;
    gap:5px!important;overflow:visible!important;
  }

  .kpi,.report-kpi{min-height:68px!important;padding:8px!important}
  .lab,.report-kpi .rk-label{font-size:7px!important}
  .val,.report-kpi .rk-value{font-size:18px!important;margin:4px 0 2px!important}
  .note,.report-kpi .rk-sub,.report-kpi .rk-note{font-size:7px!important}
  .card,.panel{padding:8px!important}
}

/* =========================================================
   TABLET / IPAD PORTRAIT 768–899
   ========================================================= */
@media (min-width:768px) and (max-width:899px){
  :root{--v270-page-x:7px;--v270-gap:5px}
  .main{padding-left:7px!important;padding-right:7px!important}
  .hero{padding:10px 12px!important;margin-bottom:5px!important;border-radius:12px!important}
  .hero h1{font-size:18px!important}
  .hero p{font-size:8.5px!important}
  .title{font-size:16px!important;margin:6px 0 3px!important}
  .subtitle{font-size:8.5px!important;margin:0 0 5px!important}

  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    height:50px!important;min-height:50px!important;max-height:50px!important;
    grid-template-rows:50px!important;column-gap:2px!important;margin:4px 0 6px!important;
  }
  body.v238-module-operativo #operativoNav>button,
  body.v238-module-analysis #analysisNav>button,
  body.v238-module-operation #v200OperationTabs>button{
    height:50px!important;min-height:50px!important;max-height:50px!important;
    padding:3px 1px!important;border-radius:8px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-icon,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-icon{
    width:13px!important;height:13px!important;min-width:13px!important;min-height:13px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-label,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-label{
    font-size:6.5px!important;line-height:1!important;height:22px!important;min-height:22px!important;
  }

  #operativoPeriodBar{padding:0 6px 6px!important;margin:4px 0 6px!important}
  #operativoPeriodBar>.or-report-filter-brand{min-height:44px!important;padding:6px 8px!important;margin-bottom:5px!important}
  #operativoPeriodBar>.or-report-filter-grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.7fr) repeat(var(--v270-oper-filter-cols,2),minmax(0,1fr))!important;
    gap:5px!important;align-items:end!important;overflow:visible!important;
  }
  #operativoPeriodBar .v266-period-view{
    min-width:0!important;width:100%!important;max-width:100%!important;flex:none!important;
  }
  #operativoPeriodBar .v266-period-buttons,
  #operativoPeriodBar .v266-period-btn{
    height:38px!important;min-height:38px!important;
  }
  #operativoPeriodBar .v266-period-btn{font-size:7px!important;padding:0 2px!important;gap:2px!important}
  #operativoPeriodBar .v266-period-mode-icon,
  #operativoPeriodBar .v266-period-mode-icon svg{width:12px!important;height:12px!important;min-width:12px!important}
  #operativoPeriodBar select,#operativoPeriodBar input{height:38px!important;min-height:38px!important;font-size:9px!important}

  #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(var(--v270-analysis-cols,5),minmax(0,1fr))!important;
    gap:4px!important;overflow:visible!important;
  }
  #v161FilterGrid .v161-field{padding-top:3px!important;padding-bottom:3px!important}
  #v161FilterGrid .v161-field label{font-size:6.6px!important}
  #v161FilterGrid .v161-field select,#v161FilterGrid .v161-field input{height:34px!important;min-height:34px!important;font-size:8.5px!important}

  .kpi,.report-kpi{min-height:62px!important;padding:7px!important}
  .lab,.report-kpi .rk-label{font-size:6.5px!important}
  .val,.report-kpi .rk-value{font-size:17px!important;margin:4px 0 2px!important}
  .note,.report-kpi .rk-sub,.report-kpi .rk-note{font-size:6.5px!important}
  .card,.panel{padding:7px!important}
}

/* =========================================================
   MÓVIL 431–767 · mini laptop al ancho real
   ========================================================= */
@media (min-width:431px) and (max-width:767px){
  :root{--v270-page-x:4px;--v270-gap:4px}
  .main{
    width:100%!important;max-width:100vw!important;min-width:0!important;
    padding:
      max(4px,env(safe-area-inset-top))
      max(4px,env(safe-area-inset-left))
      calc(58px + env(safe-area-inset-bottom))
      max(4px,env(safe-area-inset-right))!important;
  }
  .hero{padding:8px 9px!important;margin-bottom:4px!important;border-radius:11px!important}
  .hero h1{font-size:17px!important;line-height:1.02!important}
  .hero p{font-size:8px!important;margin-top:2px!important}
  .hero-greeting,.badge{display:none!important}
  .title{font-size:15px!important;margin:5px 0 2px!important}
  .subtitle{font-size:8px!important;margin:0 0 4px!important}

  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    height:46px!important;min-height:46px!important;max-height:46px!important;
    grid-template-rows:46px!important;column-gap:2px!important;margin:3px 0 5px!important;padding:0!important;
  }
  body.v238-module-operativo #operativoNav>button,
  body.v238-module-analysis #analysisNav>button,
  body.v238-module-operation #v200OperationTabs>button{
    height:46px!important;min-height:46px!important;max-height:46px!important;
    padding:2px 1px!important;border-radius:7px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-icon,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-icon{
    width:11px!important;height:11px!important;min-width:11px!important;min-height:11px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-label,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-label{
    font-size:clamp(5.2px,1.35vw,6px)!important;
    line-height:.98!important;height:21px!important;min-height:21px!important;
  }

  #operativoPeriodBar{padding:0 4px 5px!important;margin:3px 0 5px!important;border-radius:10px!important}
  #operativoPeriodBar>.or-report-filter-brand{
    width:calc(100% + 8px)!important;min-height:39px!important;margin:0 -4px 4px!important;padding:5px 6px!important;
  }
  #operativoPeriodBar>.or-report-filter-grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.7fr) repeat(var(--v270-oper-filter-cols,2),minmax(0,1fr))!important;
    gap:4px!important;align-items:end!important;overflow:visible!important;
  }
  #operativoPeriodBar .v266-period-view{
    min-width:0!important;width:100%!important;max-width:100%!important;flex:none!important;
  }
  #operativoPeriodBar .v266-period-title{height:11px!important;min-height:11px!important;font-size:6.4px!important}
  #operativoPeriodBar .v266-period-title-icon,
  #operativoPeriodBar .v266-period-title-icon svg{width:11px!important;height:11px!important;min-width:11px!important}
  #operativoPeriodBar .v266-period-buttons,
  #operativoPeriodBar .v266-period-btn{height:34px!important;min-height:34px!important}
  #operativoPeriodBar .v266-period-btn{font-size:6.2px!important;padding:0 1px!important;gap:1px!important}
  #operativoPeriodBar .v266-period-mode-icon,
  #operativoPeriodBar .v266-period-mode-icon svg{width:10px!important;height:10px!important;min-width:10px!important}
  #operativoPeriodBar .or-fcontrol label{font-size:6.2px!important;margin-bottom:2px!important}
  #operativoPeriodBar select,#operativoPeriodBar input{height:34px!important;min-height:34px!important;padding:3px 18px 3px 5px!important;font-size:7.3px!important}

  #v161FilterBar{padding:3px!important;margin:3px 0 5px!important}
  #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(var(--v270-analysis-cols,5),minmax(0,1fr))!important;
    gap:3px!important;overflow:visible!important;
  }
  #v161FilterGrid .v161-field{padding:3px 3px 3px 20px!important}
  #v161FilterGrid .v166-filter-icon{left:4px!important;width:13px!important;height:13px!important}
  #v161FilterGrid .v166-filter-icon svg{width:12px!important;height:12px!important}
  #v161FilterGrid .v161-field label{font-size:5.5px!important}
  #v161FilterGrid .v161-field select,#v161FilterGrid .v161-field input{height:29px!important;min-height:29px!important;font-size:6.5px!important;padding-left:3px!important;padding-right:12px!important}

  .kpi,.report-kpi{min-height:56px!important;height:auto!important;padding:5px!important;border-radius:8px!important}
  .lab,.report-kpi .rk-label{font-size:5.8px!important;line-height:1!important}
  .val,.report-kpi .rk-value{font-size:14px!important;line-height:1!important;margin:3px 0 1px!important}
  .note,.report-kpi .rk-sub,.report-kpi .rk-note{font-size:5.7px!important;line-height:1.05!important}
  .card,.panel{padding:5px!important;border-radius:8px!important}

  table.v270-scroll-table{min-width:max(100%,calc(var(--v270-cols,8) * 58px))!important}
  .table th,.table td,table th,table td{padding:5px 5px!important;font-size:7.2px!important;line-height:1.05!important}
}

/* =========================================================
   MÓVIL PEQUEÑO 320–430
   ========================================================= */
@media (max-width:430px){
  :root{--v270-page-x:3px;--v270-gap:3px}
  .main{
    width:100%!important;max-width:100vw!important;min-width:0!important;
    padding:
      max(3px,env(safe-area-inset-top))
      max(3px,env(safe-area-inset-left))
      calc(56px + env(safe-area-inset-bottom))
      max(3px,env(safe-area-inset-right))!important;
  }
  .hero{padding:7px 8px!important;margin-bottom:3px!important;border-radius:10px!important}
  .hero h1{font-size:clamp(15px,4.3vw,17px)!important;line-height:1!important}
  .hero p{font-size:7px!important;margin-top:2px!important}
  .hero-greeting,.badge{display:none!important}
  .title{font-size:14px!important;margin:4px 0 2px!important}
  .subtitle{font-size:7px!important;margin:0 0 4px!important}

  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    height:43px!important;min-height:43px!important;max-height:43px!important;
    grid-template-rows:43px!important;column-gap:1px!important;margin:3px 0 4px!important;padding:0!important;
  }
  body.v238-module-operativo #operativoNav>button,
  body.v238-module-analysis #analysisNav>button,
  body.v238-module-operation #v200OperationTabs>button{
    height:43px!important;min-height:43px!important;max-height:43px!important;
    padding:2px 0!important;border-radius:6px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-icon,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-icon{
    width:10px!important;height:10px!important;min-width:10px!important;min-height:10px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-label,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-label{
    font-size:clamp(4.7px,1.35vw,5.5px)!important;
    line-height:.96!important;height:19px!important;min-height:19px!important;
  }

  #operativoPeriodBar{padding:0 3px 4px!important;margin:3px 0 4px!important;border-radius:9px!important}
  #operativoPeriodBar>.or-report-filter-brand{
    width:calc(100% + 6px)!important;min-height:36px!important;margin:0 -3px 4px!important;padding:4px 5px!important;
  }
  #operativoPeriodBar>.or-report-filter-grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.72fr) repeat(var(--v270-oper-filter-cols,2),minmax(0,1fr))!important;
    gap:3px!important;align-items:end!important;overflow:visible!important;
  }
  #operativoPeriodBar .v266-period-view{
    min-width:0!important;width:100%!important;max-width:100%!important;flex:none!important;
  }
  #operativoPeriodBar .v266-period-title{height:10px!important;min-height:10px!important;font-size:5.6px!important}
  #operativoPeriodBar .v266-period-title-icon,
  #operativoPeriodBar .v266-period-title-icon svg{width:10px!important;height:10px!important;min-width:10px!important}
  #operativoPeriodBar .v266-period-buttons,
  #operativoPeriodBar .v266-period-btn{height:31px!important;min-height:31px!important}
  #operativoPeriodBar .v266-period-btn{font-size:5.5px!important;padding:0!important;gap:1px!important}
  #operativoPeriodBar .v266-period-mode-icon,
  #operativoPeriodBar .v266-period-mode-icon svg{width:9px!important;height:9px!important;min-width:9px!important}
  #operativoPeriodBar .or-fcontrol label{font-size:5.4px!important;margin-bottom:2px!important}
  #operativoPeriodBar select,#operativoPeriodBar input{height:31px!important;min-height:31px!important;padding:2px 14px 2px 4px!important;font-size:6.3px!important}

  #v161FilterBar{padding:2px!important;margin:3px 0 4px!important}
  #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(var(--v270-analysis-cols,5),minmax(0,1fr))!important;
    gap:2px!important;overflow:visible!important;
  }
  #v161FilterGrid .v161-field{padding:2px 2px 2px 17px!important}
  #v161FilterGrid .v166-filter-icon{left:3px!important;width:11px!important;height:11px!important}
  #v161FilterGrid .v166-filter-icon svg{width:10px!important;height:10px!important}
  #v161FilterGrid .v161-field label{font-size:4.9px!important}
  #v161FilterGrid .v161-field select,#v161FilterGrid .v161-field input{height:27px!important;min-height:27px!important;font-size:5.8px!important;padding-left:2px!important;padding-right:10px!important}

  .kpi,.report-kpi{min-height:52px!important;height:auto!important;padding:4px!important;border-radius:7px!important}
  .lab,.report-kpi .rk-label{font-size:5.2px!important;line-height:1!important}
  .val,.report-kpi .rk-value{font-size:12px!important;line-height:1!important;margin:2px 0 1px!important}
  .note,.report-kpi .rk-sub,.report-kpi .rk-note{font-size:5.1px!important;line-height:1.02!important}
  .card,.panel{padding:4px!important;border-radius:7px!important}

  table.v270-scroll-table{min-width:max(100%,calc(var(--v270-cols,8) * 54px))!important}
  .table th,.table td,table th,table td{padding:4px 4px!important;font-size:6.5px!important;line-height:1.03!important}
}

/* Landscape móvil = mini-laptop. */
@media (max-width:900px) and (orientation:landscape){
  .main{padding-left:5px!important;padding-right:5px!important}
  .kpis:not(.v149-kpis):not(.v204-kpis),
  .report-kpis:not(.v149-kpis):not(.v204-kpis),
  .lingerie-kpis{
    grid-template-columns:repeat(var(--v270-landscape-kpi-cols,4),minmax(0,1fr))!important;
  }
}

/* iOS/Safari: safe area y sin zoom accidental. */
@supports (-webkit-touch-callout:none){
  html,body,#appView,.shell{min-height:-webkit-fill-available}
  @media(max-width:767px){
    input,select,textarea{font-size:16px}
  }
}

/* Accesibilidad/movimiento. */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{
    animation-duration:.01ms!important;
    animation-iteration-count:1!important;
    transition-duration:.01ms!important;
    scroll-behavior:auto!important;
  }
}
</style>'''

    js = r'''<script id="v270-desktop-compact-responsive-js">
(function(){
  if(window.__V270_DESKTOP_COMPACT_RESPONSIVE)return;
  window.__V270_DESKTOP_COMPACT_RESPONSIVE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function visible(el){
    if(!el||el.hidden||el.classList.contains('hidden')||el.classList.contains('v249-hidden'))return false;
    const cs=getComputedStyle(el);
    return cs.display!=='none'&&cs.visibility!=='hidden';
  }

  function mobileCols(n,w){
    if(n<=0)return 1;
    if(w>=768)return Math.min(n,5);
    if(n<=5)return n;
    if(n===6)return 3;
    if(n<=8)return 4;
    return 5;
  }

  function syncNav(){
    qa('#operativoNav,#analysisNav,#v200OperationTabs').forEach(nav=>{
      const n=qa(':scope > button',nav).filter(visible).length;
      if(n)nav.style.setProperty('--v270-tab-count',String(n));
    });
  }

  function syncKpis(){
    const w=window.innerWidth||document.documentElement.clientWidth||1024;
    qa('.kpis,.report-kpis,.lingerie-kpis').forEach(grid=>{
      if(grid.classList.contains('v149-kpis')||grid.classList.contains('v204-kpis'))return;
      const n=Array.from(grid.children).filter(visible).length;
      if(!n)return;
      const cols=mobileCols(n,w);
      grid.style.setProperty('--v270-kpi-cols',String(cols));
      grid.style.setProperty('--v270-landscape-kpi-cols',String(Math.min(n,6)));
    });
    qa('.cards').forEach(grid=>{
      const n=Array.from(grid.children).filter(visible).length;
      if(n)grid.style.setProperty('--v270-card-cols',String(Math.min(n,3)));
    });
  }

  function syncFilters(){
    const grid=q('#operativoPeriodBar>.or-report-filter-grid');
    if(grid){
      const period=q(':scope > .v266-period-view',grid);
      const extras=Array.from(grid.children).filter(el=>visible(el)&&el!==period&&el.id!=='operPeriodModeWrap');
      grid.style.setProperty('--v270-oper-filter-cols',String(Math.max(1,Math.min(extras.length,4))));
    }
    const af=q('#v161FilterGrid');
    if(af){
      const n=Array.from(af.children).filter(visible).length;
      af.style.setProperty('--v270-analysis-cols',String(Math.max(1,Math.min(n,5))));
    }
  }

  function classifyTables(){
    qa('.tablewrap>table,.model-sticky-table>table,.table-scroll-35>table,.model-scroll-30>table,.monthly-cross-desktop>table,.lingerie-table-wrap>table').forEach(table=>{
      const row=table.querySelector('thead tr')||table.querySelector('tr');
      const cols=row?row.querySelectorAll('th,td').length:0;
      if(!cols)return;
      table.style.setProperty('--v270-cols',String(cols));
      const fit=cols<=5;
      table.classList.toggle('v270-fit-table',fit);
      table.classList.toggle('v270-scroll-table',!fit);
    });
  }

  function fixViewport(){
    let meta=q('meta[name="viewport"]');
    const content='width=device-width,initial-scale=1,viewport-fit=cover';
    if(!meta){
      meta=document.createElement('meta');
      meta.name='viewport';
      document.head.appendChild(meta);
    }
    if(meta.content!==content)meta.content=content;
  }

  function sync(){
    fixViewport();
    syncNav();
    syncKpis();
    syncFilters();
    classifyTables();
  }

  let timer=0;
  function queue(ms=40){
    clearTimeout(timer);
    timer=setTimeout(sync,ms);
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav,#analysisNav,#v200OperationTabs,#operativoPeriodBar,#v161FilterBar,[data-main]')){
      [0,60,180,420].forEach(ms=>setTimeout(sync,ms));
    }
  },false);
  document.addEventListener('change',()=>[0,80,220].forEach(ms=>setTimeout(sync,ms)),false);
  window.addEventListener('resize',()=>queue(30),{passive:true});
  window.addEventListener('orientationchange',()=>[60,220,520].forEach(ms=>setTimeout(sync,ms)),{passive:true});

  const observer=new MutationObserver(()=>queue(65));
  function start(){
    const root=q('.main')||document.body;
    if(root)observer.observe(root,{subtree:true,childList:true});
    sync();
    [120,350,800,1600].forEach(ms=>setTimeout(sync,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V270] autoridad responsive Desktop Compact activa.');
})();
</script>'''

    @m.app.middleware("http")
    async def v270_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")

            if 'name="viewport"' not in html:
                html=html.replace(
                    "<head>",
                    '<head><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
                    1,
                )
            if 'id="v270-desktop-compact-responsive-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v270-desktop-compact-responsive-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)

            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V270-DESKTOP-COMPACT-RESPONSIVE",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V270] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V270_DESKTOP_COMPACT_RESPONSIVE=True
    print("[V270] autoridad responsive Desktop Compact instalada.",flush=True)
