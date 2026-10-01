"""V211 · Restauración de navegación definida + responsive al redimensionar.

Corrige únicamente presentación/navegación:
- revierte el reordenamiento/reescritura V209;
- impide que pestañas de Análisis Comercial aparezcan en Cambios y Muertos;
- retira del menú de Cambios y Muertos la captura legacy "Cargar productividad"
  (la captura vigente vive en Operación);
- conserva las pestañas, nombres, iconos, visibilidad y listeners ya definidos;
- hace que reportes, KPI, tarjetas, filtros, tablas y gráficas respondan al
  tamaño real de la ventana al minimizar/maximizar.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V211_REPORT_NAV_RESPONSIVE_FIX", False):
        return

    # V199 creó una captura legacy dentro de Cambios y Muertos. Desde V200 la
    # captura oficial está en Operación; no debe aparecer en "Pestañas visibles".
    try:
        m.REPORT_TABS.pop("operations.productivity_capture", None)
    except Exception:
        pass

    css = r"""<style id="v211-report-nav-responsive-css">
/* Separación estricta por reporte. */
#operativoNav.hidden,
#analysisNav.hidden{display:none!important}
body:not([data-v163-module="operativo"]) #operativoNav{display:none!important}
body:not([data-v163-module="analysis"]) #analysisNav{display:none!important}

/* Captura legacy de Cambios/Muertos: la vigente está en Operación. */
#operativoNav [data-opview="Cargar productividad"],
#operativoNav [data-tab-key="operations.productivity_capture"]{
  display:none!important;
}

/* Nunca permitir que un hijo fuerce ancho del documento. */
.main,
.page,
.panel,
.card,
.kpi,
.grid,
.cards,
.kpis,
.filters,
.or-report-filter-card,
.v161-filter-grid,
#operativoDynamicContent,
#analysisContent{
  min-width:0!important;
  max-width:100%;
}
.main{overflow-x:hidden!important}
.tablewrap,
.model-sticky-table,
.model-scroll-30,
.table-scroll-35,
.chart-scroll,
.sales-chart-scroll,
.v168-pivot-wrap,
.v168-plan-matrix,
.v210-matrix-wrap{
  width:100%!important;
  max-width:100%!important;
  overflow:auto!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior:contain!important;
}
canvas,
.chart-box svg,
.panel svg,
.card svg,
img{max-width:100%}

/* Los nombres de las pestañas deben seguir visibles; no convertirlos en "...". */
#operativoNav .v206-tab-label,
#analysisNav .v206-tab-label,
#v200OperationTabs .v203-tab-label{
  text-overflow:clip!important;
  overflow:visible!important;
  white-space:normal!important;
  word-break:normal!important;
}

/* Ventana de escritorio reducida: sidebar y contenido se adaptan sin desbordarse. */
@media (min-width:901px) and (max-width:1400px){
  .side{
    width:196px!important;
  }
  .main{
    margin-left:196px!important;
    width:calc(100% - 196px)!important;
    padding:10px 12px 70px!important;
  }
  .shell.sidebar-collapsed .side{width:68px!important}
  .shell.sidebar-collapsed .main{
    margin-left:68px!important;
    width:calc(100% - 68px)!important;
  }
  .hero{padding:13px 16px!important;border-radius:15px!important}
  .hero h1{font-size:clamp(20px,2vw,26px)!important}
  .hero p{font-size:9px!important}

  #operativoNav.op-tabs>button,
  #analysisNav>button{
    flex-basis:74px!important;
    width:74px!important;
    min-width:74px!important;
    max-width:74px!important;
    min-height:62px!important;
    height:62px!important;
    font-size:6.7px!important;
  }
  #operativoNav .v206-tab-label,
  #analysisNav .v206-tab-label{
    font-size:6.7px!important;
    line-height:1.05!important;
  }
  .v207-context-title{font-size:22px!important}

  .kpis,
  .report-kpis,
  .v149-kpis,
  .v126-kpis,
  .v125-kpis,
  .v164-matrix-kpis,
  .v165-mini-kpis,
  .v168-plan-kpis,
  .sales-kpi-grid,
  .lingerie-kpis,
  .v201-demo-grid{
    grid-template-columns:repeat(auto-fit,minmax(145px,1fr))!important;
    gap:6px!important;
  }
  .cards{
    grid-template-columns:repeat(auto-fit,minmax(205px,1fr))!important;
    gap:7px!important;
  }
  .grid{
    grid-template-columns:repeat(auto-fit,minmax(330px,1fr))!important;
    gap:7px!important;
  }
  .table{
    min-width:680px!important;
    width:100%!important;
    font-size:7.7px!important;
  }
  .table th,.table td{padding:7px 6px!important}
}

@media (min-width:901px) and (max-width:1120px){
  .side{width:170px!important}
  .main{
    margin-left:170px!important;
    width:calc(100% - 170px)!important;
    padding:8px 9px 66px!important;
  }
  .shell.sidebar-collapsed .side{width:64px!important}
  .shell.sidebar-collapsed .main{
    margin-left:64px!important;
    width:calc(100% - 64px)!important;
  }
  .sidebrand-text b{font-size:11px!important}
  .sidebrand-text small,.nav small{font-size:6.7px!important}
  .nav{font-size:8.5px!important;padding-left:8px!important;padding-right:8px!important}

  #operativoNav.op-tabs,
  #analysisNav,
  #v200OperationTabs{
    gap:3px!important;
    padding-left:2px!important;
    padding-right:2px!important;
  }
  #operativoNav.op-tabs>button,
  #analysisNav>button{
    flex-basis:66px!important;
    width:66px!important;
    min-width:66px!important;
    max-width:66px!important;
    min-height:60px!important;
    height:60px!important;
  }
  #operativoNav .v206-tab-icon,
  #analysisNav .v206-tab-icon{
    width:29px!important;
    min-width:29px!important;
    max-width:29px!important;
    height:29px!important;
    min-height:29px!important;
    max-height:29px!important;
    flex-basis:29px!important;
  }
  #operativoNav .v206-tab-label,
  #analysisNav .v206-tab-label{
    font-size:6.1px!important;
  }

  .hero h1{font-size:19px!important}
  .v207-context-title,.title{font-size:18px!important}
  .v207-context-sub,.subtitle{font-size:8px!important}

  .kpis,
  .report-kpis,
  .v149-kpis,
  .v126-kpis,
  .v125-kpis,
  .sales-kpi-grid,
  .v201-demo-grid{
    grid-template-columns:repeat(auto-fit,minmax(130px,1fr))!important;
  }
  .cards{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))!important}
  .grid{grid-template-columns:1fr!important}
  .table{min-width:610px!important;font-size:7.2px!important}
  .table th,.table td{padding:6px 5px!important}
  .panel,.card{padding:9px!important}
}

@media (min-width:901px) and (max-width:980px){
  .side{width:148px!important}
  .main{
    margin-left:148px!important;
    width:calc(100% - 148px)!important;
    padding:7px 7px 62px!important;
  }
  .shell.sidebar-collapsed .side{width:60px!important}
  .shell.sidebar-collapsed .main{
    margin-left:60px!important;
    width:calc(100% - 60px)!important;
  }
  #operativoNav.op-tabs>button,
  #analysisNav>button{
    flex-basis:60px!important;
    width:60px!important;
    min-width:60px!important;
    max-width:60px!important;
  }
  #operativoNav .v206-tab-label,
  #analysisNav .v206-tab-label{font-size:5.8px!important}
  .kpis,
  .report-kpis,
  .v149-kpis,
  .v126-kpis,
  .v125-kpis,
  .sales-kpi-grid,
  .v201-demo-grid{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
  }
  .cards{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .table{min-width:570px!important;font-size:6.9px!important}
}

/* Móvil: el ancho pertenece a la pantalla, nunca al contenido de una tabla. */
@media(max-width:900px){
  .main,.page{width:100%!important;max-width:100%!important;overflow-x:hidden!important}
  .tablewrap,
  .model-sticky-table,
  .model-scroll-30,
  .table-scroll-35,
  .chart-scroll,
  .sales-chart-scroll,
  .v210-matrix-wrap{
    max-width:100vw!important;
  }
}
</style>"""

    js = r"""<script id="v211-report-nav-responsive-js">
(function(){
  if(window.__V211_REPORT_NAV_RESPONSIVE)return;
  window.__V211_REPORT_NAV_RESPONSIVE=true;

  function removeLegacyCapture(){
    const btn=document.querySelector('#operativoNav [data-opview="Cargar productividad"],#operativoNav [data-tab-key="operations.productivity_capture"]');
    if(!btn)return;
    btn.hidden=true;
    btn.classList.add('hidden');
    btn.setAttribute('aria-hidden','true');
    btn.setAttribute('aria-selected','false');
  }

  function fitCharts(){
    document.querySelectorAll('canvas').forEach(el=>{
      el.style.maxWidth='100%';
      if(el.parentElement)el.parentElement.style.maxWidth='100%';
    });
  }

  function refresh(){
    removeLegacyCapture();
    fitCharts();
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});
  else refresh();

  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(refresh,20));
  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button,#v200OperationTabs>button')){
      [40,160,360].forEach(ms=>setTimeout(refresh,ms));
    }
  },true);
  window.addEventListener('resize',()=>setTimeout(refresh,60),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(refresh,120),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(refresh,50),{passive:true});

  console.info('[V211] navegación restaurada y responsive de ventana activo.');
})();
</script>"""

    @m.app.middleware("http")
    async def v211_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v211-report-nav-responsive-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v211-report-nav-responsive-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V211",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V211] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V211_REPORT_NAV_RESPONSIVE_FIX = True
    print("[V211] navegación restaurada + responsive al redimensionar instalado.",flush=True)
