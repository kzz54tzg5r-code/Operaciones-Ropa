"""V286 · Autoridad universal de scroll + tipografía responsive.
Objetivo:
- todo reporte/pestaña puede desplazarse verticalmente con un dedo, rueda o trackpad;
- tablas anchas sólo desplazan horizontalmente cuando lo requieren;
- escalas tipográficas coherentes en iOS, Android, tablet/iPad, laptop y PC;
- sin MutationObserver ni intervalos globales.
"""

def install(m):
    if getattr(m,"_V286_SCROLL_TYPE_AUTHORITY",False):
        return

    from fastapi.responses import HTMLResponse

    css=r'''<style id="v286-scroll-type-authority-css">
:root{
  --v286-body:12px;
  --v286-small:9px;
  --v286-control:11px;
  --v286-th:9.5px;
  --v286-td:10.5px;
  --v286-h1:24px;
  --v286-h2:18px;
  --v286-title:15px;
}

/* ---------- Scroll vertical autoritativo ---------- */
html{
  width:100%!important;
  min-height:100%!important;
  height:auto!important;
  overflow-x:hidden!important;
  overflow-y:auto!important;
  overscroll-behavior-y:auto!important;
  -webkit-text-size-adjust:100%!important;
  text-size-adjust:100%!important;
  scroll-behavior:auto!important;
}
body{
  width:100%!important;
  min-height:100%!important;
  height:auto!important;
  overflow-x:hidden!important;
  overflow-y:auto!important;
  overscroll-behavior-y:auto!important;
  -webkit-overflow-scrolling:touch!important;
  touch-action:pan-x pan-y pinch-zoom!important;
}

/* Ninguna vista/report host debe convertirse en un viewport vertical independiente. */
#appView:not(.hidden),
.shell,
.main,
section.page,
section.page.active,
#operativoCentro,
#operativoDynamic,
#operativoDynamicContent,
#analysisDynamic,
#analysisContent,
#globalContent,
.report-content,
.report-body,
.dashboard-content{
  height:auto!important;
  max-height:none!important;
  min-height:0!important;
  overflow-y:visible!important;
  overscroll-behavior-y:auto!important;
  touch-action:pan-x pan-y pinch-zoom!important;
}

/* Navegaciones horizontales nunca bloquean el gesto vertical. */
#operativoNav,
#analysisNav,
#v200OperationTabs,
.rt-carousel,
.switches,
.v165-subfilters,
.op-tabs,
.report-tabs{
  touch-action:pan-x pan-y pinch-zoom!important;
  overscroll-behavior-y:auto!important;
  -webkit-overflow-scrolling:touch!important;
}

/* Contenedores de tablas: horizontal local, vertical heredado de la página. */
.tablewrap,
.table-scroll,
.table-responsive,
.model-sticky-table,
.monthly-cross-desktop,
.v168-pivot-wrap,
.v168-plan-matrix,
.v279-tablewrap,
.v281-panel,
[data-testid="stDataFrame"],
[data-testid="stDataEditor"]{
  max-width:100%!important;
  overscroll-behavior-y:auto!important;
  -webkit-overflow-scrolling:touch!important;
  touch-action:pan-x pan-y pinch-zoom!important;
}
.tablewrap,
.table-scroll,
.table-responsive,
.monthly-cross-desktop,
.v168-pivot-wrap,
.v168-plan-matrix,
.v279-tablewrap{
  overflow-x:auto!important;
  overflow-y:visible!important;
}

/* Tablas que antes tenían scroll vertical interno: en móvil/tablet se integra a la página. */
@media(max-width:1024px){
  .model-sticky-table,
  .model-scroll-30,
  .table-scroll-35,
  .chart-scroll,
  .sales-chart-scroll{
    max-height:none!important;
    height:auto!important;
    overflow-x:auto!important;
    overflow-y:visible!important;
    overscroll-behavior-y:auto!important;
    -webkit-overflow-scrolling:touch!important;
    touch-action:pan-x pan-y pinch-zoom!important;
  }
}
/* En laptop/PC pueden conservar su alto interno, pero deben encadenar la rueda. */
@media(min-width:1025px){
  .model-sticky-table,
  .model-scroll-30,
  .table-scroll-35{
    overscroll-behavior:auto!important;
    touch-action:pan-x pan-y!important;
  }
}

/* Gráficas/tarjetas no secuestran el swipe vertical. */
.chart-scroll,
.sales-chart-scroll,
.chart-box,
.panel canvas,
.panel svg,
.js-plotly-plot,
.plot-container,
[data-testid="stPlotlyChart"],
[data-testid="stVegaLiteChart"]{
  overscroll-behavior-y:auto!important;
  touch-action:pan-y pinch-zoom!important;
}

/* Sólo los overlays reales pueden tener su propio scroll vertical. */
.modal-backdrop,
.modal-card,
.login-v15,
.side,
.or-mobile-drawer-open .side{
  overscroll-behavior-y:contain;
}

/* ---------- Tipografía transversal ---------- */
body,
button,
input,
select,
textarea{
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif!important;
}
body{
  font-size:var(--v286-body)!important;
  line-height:1.2!important;
  font-variant-numeric:tabular-nums;
}
button,
input,
select,
textarea{
  font-size:var(--v286-control)!important;
  line-height:1.15!important;
}
small,
.note,
.subtitle,
.filter-caption,
.v281-sub,
.v281-msg,
.rk-note,
.kpi-note,
.card-note{
  font-size:var(--v286-small)!important;
  line-height:1.15!important;
}
.hero h1,
h1.title,
.title{
  font-size:var(--v286-h1)!important;
  line-height:1.06!important;
}
h2,
.panel-title,
.report-title,
.v281-head h2{
  font-size:var(--v286-h2)!important;
  line-height:1.08!important;
}
h3,
.card-title,
.section-title,
.v281-panel-h{
  font-size:var(--v286-title)!important;
  line-height:1.1!important;
}

/* Todas las tablas usan la misma jerarquía tipográfica. */
body table th{
  font-size:var(--v286-th)!important;
  line-height:1.04!important;
  font-weight:850!important;
}
body table td{
  font-size:var(--v286-td)!important;
  line-height:1.08!important;
}
/* Mantiene densidad sin hacer ilegibles los datos. */
body table th,
body table td{
  padding-top:3px!important;
  padding-bottom:3px!important;
}

/* KPIs/números principales: consistencia visual. */
.val,
.report-kpi .rk-value,
.kpi .value,
.kpi-value,
.v281-kpi b,
.v279-card strong{
  font-size:clamp(18px,1.55vw,28px)!important;
  line-height:1!important;
}
.lab,
.report-kpi .rk-label,
.kpi-label,
.v281-kpi small{
  font-size:clamp(7.5px,.58vw,9.5px)!important;
  line-height:1.08!important;
}

/* ---------- Laptop ---------- */
@media(min-width:1025px) and (max-width:1439px){
  :root{
    --v286-body:11px;
    --v286-small:8.5px;
    --v286-control:10.5px;
    --v286-th:8.7px;
    --v286-td:9.7px;
    --v286-h1:22px;
    --v286-h2:17px;
    --v286-title:14px;
  }
}

/* ---------- Tablet / iPad ---------- */
@media(min-width:701px) and (max-width:1024px){
  :root{
    --v286-body:10.5px;
    --v286-small:8px;
    --v286-control:10px;
    --v286-th:7.8px;
    --v286-td:8.8px;
    --v286-h1:20px;
    --v286-h2:15px;
    --v286-title:12px;
  }
  body table th,body table td{
    padding-top:2.5px!important;
    padding-bottom:2.5px!important;
  }
  .val,.report-kpi .rk-value,.kpi .value,.kpi-value,.v281-kpi b{
    font-size:clamp(16px,2.15vw,23px)!important;
  }
}

/* ---------- iPhone / Android ---------- */
@media(max-width:700px){
  :root{
    --v286-body:10px;
    --v286-small:7.5px;
    --v286-control:9.5px;
    --v286-th:6.8px;
    --v286-td:7.6px;
    --v286-h1:18px;
    --v286-h2:14px;
    --v286-title:11px;
  }
  html,body{
    min-height:100dvh!important;
  }
  .main{
    min-height:0!important;
    height:auto!important;
    overflow-y:visible!important;
    padding-bottom:calc(72px + env(safe-area-inset-bottom))!important;
  }
  section.page,
  section.page.active{
    min-height:0!important;
    height:auto!important;
    overflow:visible!important;
  }
  body table th,body table td{
    padding-top:2px!important;
    padding-bottom:2px!important;
  }
  button,input,select,textarea{
    min-height:28px;
  }
  .hero h1,.title{
    font-size:clamp(16px,4.7vw,20px)!important;
  }
  .hero p,.subtitle{
    font-size:clamp(8px,2.45vw,10px)!important;
  }
  .val,.report-kpi .rk-value,.kpi .value,.kpi-value,.v281-kpi b{
    font-size:clamp(14px,4.2vw,20px)!important;
  }
  .lab,.report-kpi .rk-label,.kpi-label,.v281-kpi small{
    font-size:clamp(6.5px,1.9vw,8px)!important;
  }
  /* El usuario siempre puede iniciar el scroll desde tabs, tarjetas, tablas o gráficas. */
  #operativoNav,#analysisNav,#v200OperationTabs,
  .panel,.card,.kpi,.report-kpi,.filters,
  .v281,.v279,.or-filter-panel-v3{
    touch-action:pan-x pan-y pinch-zoom!important;
    overscroll-behavior-y:auto!important;
  }
  .tablewrap,.model-sticky-table,.model-scroll-30,.table-scroll-35,
  .v168-pivot-wrap,.v168-plan-matrix,.v279-tablewrap{
    touch-action:pan-x pan-y pinch-zoom!important;
  }
}

/* ---------- Teléfonos angostos ---------- */
@media(max-width:430px){
  :root{
    --v286-body:9.5px;
    --v286-small:7.2px;
    --v286-control:9px;
    --v286-th:6.3px;
    --v286-td:7px;
    --v286-h1:17px;
    --v286-h2:13px;
    --v286-title:10px;
  }
}
</style>'''

    js=r'''<script id="v286-scroll-type-authority-js">
(function(){
  if(window.__V286_SCROLL_TYPE_AUTHORITY)return;
  window.__V286_SCROLL_TYPE_AUTHORITY=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function modalOpen(){
    return !!q('.modal-backdrop:not(.hidden),.login-v15:not(.hidden),[role="dialog"]:not(.hidden),body.or-mobile-drawer-open');
  }

  function unlock(){
    document.documentElement.classList.add('v286-scroll-ready');
    if(modalOpen())return;

    /* Sólo se eliminan bloqueos inline de los hosts principales.
       No se toca contenido de reportes, tablas ni eventos. */
    [document.documentElement,document.body,q('#appView'),q('.main'),q('section.page.active')]
      .filter(Boolean)
      .forEach(el=>{
        el.style.removeProperty('overflow-y');
        el.style.removeProperty('height');
        el.style.removeProperty('max-height');
      });
  }

  function settle(){
    unlock();
    setTimeout(unlock,60);
    setTimeout(unlock,220);
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',settle,{once:true});
  }else{
    settle();
  }

  document.addEventListener('click',settle,true);
  document.addEventListener('change',settle,true);
  window.addEventListener('pageshow',settle,{passive:true});
  window.addEventListener('resize',settle,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(settle,100),{passive:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)settle()},{passive:true});

  console.info('[V286] scroll universal + tipografía responsive activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v286_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v286-scroll-type-authority-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v286-scroll-type-authority-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V286-SCROLL-TYPE-AUTHORITY",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V286] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V286_SCROLL_TYPE_AUTHORITY=True
    print("[V286] scroll universal y tipografía responsive instalados.",flush=True)
