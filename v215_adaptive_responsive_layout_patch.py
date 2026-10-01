"""V215 · layout adaptativo real para pestañas, tarjetas, filtros y contenido.

Solicitado 2026-10-01:
- pestañas principales siempre en UNA sola línea;
- tamaño proporcional al ancho real disponible, no al sistema operativo;
- cuando el ancho ya no permite mantener legibilidad, navegación horizontal
  en una sola fila (sin saltos de línea ni segunda fila);
- misma regla para Cambios y Muertos, Operación y Análisis Comercial;
- tarjetas, filtros, paneles, tablas y gráficos se acomodan al tamaño real del
  viewport, incluyendo móvil vertical/horizontal y tablet.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V215_ADAPTIVE_RESPONSIVE_LAYOUT", False):
        return

    css = r"""<style id="v215-adaptive-responsive-layout-css">
:root{
  --v215-gap:7px;
  --v215-tab-h:70px;
  --v215-tab-font:8.4px;
  --v215-icon:32px;
}

/* ==========================================================
   REGLA GENERAL: NUNCA HACER MÁS ANCHA LA PÁGINA QUE SU ÁREA
   ========================================================== */
html,body,#appView,.shell,.main,
body[data-v213-module] .main,
body[data-v213-module] .page,
body[data-v213-module] #operativoDynamic,
body[data-v213-module] #operativoDynamicContent{
  min-width:0!important;
  max-width:100%!important;
}
body[data-v213-module] .main{
  overflow-x:hidden!important;
}
body[data-v213-module] .page,
body[data-v213-module] .panel,
body[data-v213-module] .card,
body[data-v213-module] .kpi,
body[data-v213-module] .report-kpi,
body[data-v213-module] .v149-kpi,
body[data-v213-module] .v125-kpi{
  min-width:0!important;
  max-width:100%!important;
}
body[data-v213-module] img,
body[data-v213-module] canvas{
  max-width:100%!important;
  height:auto;
}
body[data-v213-module] :is(.title,.subtitle,.note,.lab,.rk-label,.rk-sub,.v213-filter-head,.panel-head){
  overflow-wrap:anywhere;
}

/* ==========================================================
   PESTAÑAS PRINCIPALES: UNA SOLA FILA, TAMAÑO ADAPTATIVO
   ========================================================== */
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs){
  --v215-gap:7px;
  flex-direction:row!important;
  flex-wrap:nowrap!important;
  align-items:stretch!important;
  justify-content:flex-start!important;
  gap:var(--v215-gap)!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  min-height:0!important;
  height:auto!important;
  margin:3px 0 9px!important;
  padding:5px 1px 10px!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
  scroll-snap-type:x proximity!important;
  scroll-padding-inline:4px!important;
  white-space:nowrap!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)::-webkit-scrollbar{
  display:none!important;
}

/* V216: aislamiento duro de navegación.
   El bug del video era que V215 volvía display:flex los TRES menús:
   Cambios y Muertos + Análisis Comercial + Operación al mismo tiempo. */
body[data-v213-module="operativo"] :is(#analysisNav,#v200OperationTabs),
body[data-v213-module="analysis"] :is(#operativoNav,#v200OperationTabs),
body[data-v213-module="operation"] :is(#operativoNav,#analysisNav),
body[data-v213-module="users"] :is(#operativoNav,#analysisNav,#v200OperationTabs),
body[data-v213-module="share"] :is(#operativoNav,#analysisNav,#v200OperationTabs){
  display:none!important;
}
body[data-v213-module="operativo"] #operativoNav:not(.hidden):not([hidden]),
body[data-v213-module="analysis"] #analysisNav:not(.hidden):not([hidden]),
body[data-v213-module="operation"] #v200OperationTabs:not(.hidden):not([hidden]){
  display:flex!important;
}

/* En modo FIT todos los botones se reparten TODO el ancho disponible. */
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v215-tabs-fit>button{
  flex:1 1 0!important;
  width:auto!important;
  min-width:0!important;
  max-width:none!important;
}

/* En modo SCROLL siguen en UNA fila y conservan legibilidad. */
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v215-tabs-scroll>button{
  flex:0 0 var(--v215-scroll-w,88px)!important;
  width:var(--v215-scroll-w,88px)!important;
  min-width:var(--v215-scroll-w,88px)!important;
  max-width:var(--v215-scroll-w,88px)!important;
}

body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button{
  position:relative!important;
  display:flex!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:4px!important;
  min-height:var(--v215-tab-h)!important;
  height:var(--v215-tab-h)!important;
  max-height:var(--v215-tab-h)!important;
  margin:0!important;
  padding:5px 4px 7px!important;
  border-radius:14px!important;
  overflow:hidden!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
  white-space:normal!important;
  text-align:center!important;
  line-height:1.08!important;
  font-size:var(--v215-tab-font)!important;
}

body[data-v213-module] :is(#operativoNav,#analysisNav) :is(.v206-tab-icon,.rt-tab-icon),
body[data-v213-module="operation"] #v200OperationTabs .v203-tab-icon{
  flex:0 0 var(--v215-icon)!important;
  width:var(--v215-icon)!important;
  min-width:var(--v215-icon)!important;
  max-width:var(--v215-icon)!important;
  height:var(--v215-icon)!important;
  min-height:var(--v215-icon)!important;
  max-height:var(--v215-icon)!important;
  border-radius:11px!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) :is(.v206-tab-icon,.rt-tab-icon) svg,
body[data-v213-module="operation"] #v200OperationTabs .v203-tab-icon svg{
  width:calc(var(--v215-icon) * .56)!important;
  height:calc(var(--v215-icon) * .56)!important;
  max-width:calc(var(--v215-icon) * .56)!important;
  max-height:calc(var(--v215-icon) * .56)!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) :is(.v206-tab-label,.rt-tab-label),
body[data-v213-module="operation"] #v200OperationTabs .v203-tab-label{
  display:-webkit-box!important;
  -webkit-box-orient:vertical!important;
  -webkit-line-clamp:2!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow:hidden!important;
  font-size:var(--v215-tab-font)!important;
  line-height:1.08!important;
  text-overflow:ellipsis!important;
  white-space:normal!important;
  text-align:center!important;
}

/* Si una capa vieja dejó icono + texto duplicado, V215 conserva sólo
   la decoración canónica visible sin generar una segunda fila. */
body[data-v213-module] :is(#operativoNav,#analysisNav)>button>.v166-tab-icon{
  display:none!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav)>button:has(>.v206-tab-icon):is(:has(>.rt-tab-icon),:has(>.rt-tab-label))>.rt-tab-icon,
body[data-v213-module] :is(#operativoNav,#analysisNav)>button:has(>.v206-tab-label):is(:has(>.rt-tab-icon),:has(>.rt-tab-label))>.rt-tab-label,
body[data-v213-module="operation"] #v200OperationTabs>button:has(>.v203-tab-icon)>.rt-tab-icon,
body[data-v213-module="operation"] #v200OperationTabs>button:has(>.v203-tab-label)>.rt-tab-label{
  display:none!important;
}

/* ==========================================================
   CONTENIDO RESPONSIVO: KPI, TARJETAS, PANELES Y FILTROS
   ========================================================== */
body[data-v213-module] :is(.kpis,.report-kpis,.v149-kpis,.v121-grid,.v125-grid,.v200-op-grid){
  display:grid!important;
  grid-template-columns:repeat(auto-fit,minmax(min(178px,100%),1fr))!important;
  gap:clamp(7px,1vw,12px)!important;
  width:100%!important;
  max-width:100%!important;
}
body[data-v213-module] :is(.cards,.grid,.uploadgrid,.v149-grid){
  display:grid!important;
  grid-template-columns:repeat(auto-fit,minmax(min(230px,100%),1fr))!important;
  gap:clamp(8px,1vw,13px)!important;
  width:100%!important;
  max-width:100%!important;
}

body[data-v213-module] :is(.kpi,.report-kpi,.v149-kpi,.v125-kpi){
  padding:clamp(9px,1.1vw,14px)!important;
  min-height:clamp(92px,8vw,126px)!important;
}
body[data-v213-module] :is(.kpi .val,.report-kpi .rk-value,.v149-kpi b,.v125-kpi b){
  font-size:clamp(18px,2.15vw,31px)!important;
  line-height:1.02!important;
  max-width:100%!important;
  overflow-wrap:anywhere!important;
}
body[data-v213-module] :is(.kpi .lab,.report-kpi .rk-label,.v149-kpi small,.v125-kpi small){
  font-size:clamp(7.5px,.78vw,10px)!important;
}
body[data-v213-module] :is(.kpi .note,.report-kpi .rk-sub,.v149-kpi span,.v125-kpi span){
  font-size:clamp(7.5px,.72vw,9.5px)!important;
  line-height:1.24!important;
}

/* Filtros: se acomodan automáticamente según ancho real. */
#v213AnalysisFilterCard .v213-filter-grid,
body.v213-show-oper-filter #operativoPeriodBar .or-report-filter-grid{
  display:grid!important;
  grid-template-columns:repeat(auto-fit,minmax(min(165px,100%),1fr))!important;
  gap:8px!important;
  align-items:end!important;
  width:100%!important;
  max-width:100%!important;
}
#v213AnalysisFilterCard .v213-filter-apply,
body.v213-show-oper-filter #operPeriodApply{
  min-width:0!important;
  width:100%!important;
  max-width:100%!important;
}

/* Controles internos: una sola línea cuando caben y scroll local cuando no. */
body[data-v213-module] .switches{
  display:flex!important;
  flex-wrap:nowrap!important;
  max-width:100%!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important;
}
body[data-v213-module] .switches::-webkit-scrollbar{display:none!important}
body[data-v213-module] .switches>button{flex:0 0 auto!important}

/* Tablas: nunca obligan a ampliar toda la página; el scroll queda en la tabla. */
body[data-v213-module] .tablewrap,
body[data-v213-module] :is(.model-scroll-30,.table-scroll-35,.sales-chart-scroll){
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow-x:auto!important;
  overflow-y:auto;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
}
body[data-v213-module] .table{
  width:100%!important;
  max-width:none!important;
}
body[data-v213-module] .table th,
body[data-v213-module] .table td{
  white-space:nowrap;
}
body[data-v213-module] .tablewrap .table{
  min-width:max-content!important;
}

/* Gráficas y bloques de visualización dentro del ancho del reporte. */
body[data-v213-module] :is(.bars,.chart,.sales-chart-scroll,.v176-chart-wrap){
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
}
body[data-v213-module] :is(.bars,.chart,.v176-chart-wrap) svg{
  max-width:100%!important;
}

/* Hero y encabezados se compactan de forma progresiva. */
body[data-v213-module] .hero{
  min-width:0!important;
  gap:10px!important;
  padding:clamp(13px,1.6vw,22px)!important;
}
body[data-v213-module] .hero h1{
  font-size:clamp(22px,2.25vw,34px)!important;
}
body[data-v213-module] #v213ReportContext h2{
  font-size:clamp(20px,2.1vw,29px)!important;
}

/* ==========================================================
   TABLET / VENTANA REDUCIDA
   ========================================================== */
@media(max-width:1100px){
  :root{
    --v215-gap:5px;
  }
  body[data-v213-module] :is(.kpis,.report-kpis,.v149-kpis,.v121-grid,.v125-grid,.v200-op-grid){
    grid-template-columns:repeat(auto-fit,minmax(min(155px,100%),1fr))!important;
  }
  body[data-v213-module] :is(.cards,.grid,.uploadgrid,.v149-grid){
    grid-template-columns:repeat(auto-fit,minmax(min(200px,100%),1fr))!important;
  }
}

/* ==========================================================
   MÓVIL / TABLET ESTRECHA
   ========================================================== */
@media(max-width:760px){
  body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs){
    width:100%!important;
    max-width:100%!important;
    margin:2px 0 8px!important;
    padding:4px 0 9px!important;
    gap:5px!important;
  }
  body[data-v213-module] :is(.kpis,.report-kpis,.v149-kpis,.v121-grid,.v125-grid,.v200-op-grid){
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:7px!important;
  }
  body[data-v213-module] :is(.cards,.grid,.uploadgrid,.v149-grid){
    grid-template-columns:1fr!important;
  }
  #v213AnalysisFilterCard .v213-filter-grid,
  body.v213-show-oper-filter #operativoPeriodBar .or-report-filter-grid{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:7px!important;
  }
  body[data-v213-module] :is(.kpi,.report-kpi,.v149-kpi,.v125-kpi){
    min-height:88px!important;
    padding:9px!important;
  }
  body[data-v213-module] :is(.kpi .val,.report-kpi .rk-value,.v149-kpi b,.v125-kpi b){
    font-size:clamp(17px,6.2vw,24px)!important;
  }
  body[data-v213-module] .hero{
    padding:12px!important;
  }
  body[data-v213-module] .hero h1{
    font-size:clamp(20px,6vw,27px)!important;
  }
}

/* Móvil angosto: sólo si ya no caben dos KPI con lectura correcta. */
@media(max-width:390px){
  body[data-v213-module] :is(.kpis,.report-kpis,.v149-kpis,.v121-grid,.v125-grid,.v200-op-grid){
    grid-template-columns:1fr!important;
  }
  #v213AnalysisFilterCard .v213-filter-grid,
  body.v213-show-oper-filter #operativoPeriodBar .or-report-filter-grid{
    grid-template-columns:1fr!important;
  }
}

/* Horizontal en móvil/tablet: aprovechar altura y mostrar más contenido. */
@media(orientation:landscape) and (max-height:650px){
  body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs){
    padding-top:3px!important;
    padding-bottom:7px!important;
  }
  body[data-v213-module] .hero{
    padding-top:9px!important;
    padding-bottom:9px!important;
  }
  body[data-v213-module] :is(.kpis,.report-kpis,.v149-kpis,.v121-grid,.v125-grid,.v200-op-grid){
    grid-template-columns:repeat(auto-fit,minmax(min(145px,100%),1fr))!important;
  }
}
/* Defensa final: ningún breakpoint puede reactivar un menú ajeno al módulo. */
body[data-v213-module="operativo"] :is(#analysisNav,#v200OperationTabs),
body[data-v213-module="analysis"] :is(#operativoNav,#v200OperationTabs),
body[data-v213-module="operation"] :is(#operativoNav,#analysisNav),
body[data-v213-module="users"] :is(#operativoNav,#analysisNav,#v200OperationTabs),
body[data-v213-module="share"] :is(#operativoNav,#analysisNav,#v200OperationTabs){
  display:none!important;
}
</style>"""

    js = r"""<script id="v215-adaptive-responsive-layout-js">
(function(){
  if(window.__V215_ADAPTIVE_RESPONSIVE_LAYOUT)return;
  window.__V215_ADAPTIVE_RESPONSIVE_LAYOUT=true;

  const ids=['operativoNav','analysisNav','v200OperationTabs'];
  const visible=btn=>{
    if(!btn||btn.hidden||btn.classList.contains('hidden'))return false;
    const cs=getComputedStyle(btn);
    return cs.display!=='none'&&cs.visibility!=='hidden';
  };

  function normalizeHost(host){
    const all=[...host.children].filter(x=>x instanceof HTMLButtonElement);
    if(host.id!=='v200OperationTabs'&&!host.dataset.v215Canonicalized){
      host.dataset.v215Canonicalized='1';
      all.forEach(btn=>{
        // Fuerza una única reconstrucción de V206 para eliminar decoración
        // heredada y aplicar el icono correcto de la pestaña actual.
        if(btn.querySelector(':scope > .v206-tab-icon,:scope > .rt-tab-icon')){
          btn.dataset.v206Decorated='';
        }
      });
      // Un cambio de clase dispara el observer de V206 una sola vez.
      host.classList.add('v215-canonicalizing');
      requestAnimationFrame(()=>host.classList.remove('v215-canonicalizing'));
    }
    all.forEach(btn=>{
      const v206Icon=btn.querySelector(':scope > .v206-tab-icon');
      const v206Label=btn.querySelector(':scope > .v206-tab-label');
      const v203Icon=btn.querySelector(':scope > .v203-tab-icon');
      const v203Label=btn.querySelector(':scope > .v203-tab-label');
      if((v206Icon&&v206Label)||(v203Icon&&v203Label)){
        btn.querySelectorAll(':scope > .rt-tab-icon,:scope > .rt-tab-label,:scope > .v166-tab-icon')
          .forEach(x=>x.remove());
      }
    });
  }

  function fitHost(host){
    if(!host||!host.isConnected)return;
    normalizeHost(host);
    const buttons=[...host.children].filter(x=>x instanceof HTMLButtonElement&&visible(x));
    if(!buttons.length)return;

    const w=Math.max(0,host.clientWidth);
    const count=buttons.length;
    const gap=w<760?5:w<1100?5:7;
    const target=(w-gap*Math.max(0,count-1))/count;

    // Umbral de legibilidad. Si todos caben con 72 px o más, se reparte el
    // ancho exactamente; si no, conserva una sola fila con scroll horizontal.
    const fit=target>=72;
    host.classList.toggle('v215-tabs-fit',fit);
    host.classList.toggle('v215-tabs-scroll',!fit);

    const base=fit?Math.max(72,Math.min(118,target)):Math.max(80,Math.min(94,w*.24||88));
    const font=Math.max(7.1,Math.min(9.1,base*.079));
    const icon=Math.max(27,Math.min(35,base*.31));
    const height=Math.max(58,Math.min(74,base*.64));

    host.style.setProperty('--v215-tab-font',font.toFixed(2)+'px');
    host.style.setProperty('--v215-icon',icon.toFixed(1)+'px');
    host.style.setProperty('--v215-tab-h',height.toFixed(1)+'px');
    host.style.setProperty('--v215-scroll-w',Math.round(base)+'px');
    host.style.setProperty('--v215-count',String(count));
  }

  function fitAll(){
    ids.forEach(id=>fitHost(document.getElementById(id)));
  }

  let raf=0;
  function schedule(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(fitAll);
  }

  const resize=new ResizeObserver(schedule);
  function attach(){
    ids.forEach(id=>{
      const host=document.getElementById(id);
      if(host&&!host.dataset.v215Observed){
        host.dataset.v215Observed='1';
        resize.observe(host);
      }
    });
    fitAll();
  }

  const mo=new MutationObserver(mutations=>{
    if(mutations.some(m=>m.type==='childList'||m.type==='attributes'))schedule();
  });

  function init(){
    attach();
    mo.observe(document.body,{
      subtree:true,
      childList:true,
      attributes:true,
      attributeFilter:['class','hidden','style','aria-hidden']
    });
    [80,250,700,1500].forEach(ms=>setTimeout(attach,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
  window.addEventListener('resize',schedule,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(schedule,120),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(attach,80),{passive:true});
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(schedule,30));
  console.info('[V216] layout adaptativo + aislamiento de navegación instalado.');
})();
</script>"""

    @m.app.middleware("http")
    async def v215_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v215-adaptive-responsive-layout-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v215-adaptive-responsive-layout-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V216-RESPONSIVE",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V215] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V215_ADAPTIVE_RESPONSIVE_LAYOUT = True
    print("[V216] pestañas una fila + aislamiento por reporte + responsive multidispositivo instalado.", flush=True)
