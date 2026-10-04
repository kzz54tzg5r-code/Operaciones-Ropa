"""V265 · Layout de escritorio real en móvil/tablet.

Corrige V264: la petición es conservar la matriz de laptop, no reacomodarla como
una interfaz móvil. Esta capa mantiene el mismo número de columnas que escritorio
y sólo reduce tipografías, espacios y alturas para caber en teléfono/tablet.
No altera consultas, datos, cálculos, roles, endpoints ni eventos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V265_DESKTOP_MATRIX_MOBILE", False):
        return

    css = r'''<style id="v265-desktop-matrix-mobile-css">
/* El texto del encabezado de filtros debe ser único y exacto. */
#operativoPeriodBar > .or-report-filter-brand small{
  font-size:0!important;
}
#operativoPeriodBar > .or-report-filter-brand small::after{
  content:"Define la vista del reporte"!important;
  display:inline!important;
  font-size:10px!important;
  line-height:1.1!important;
}
#operativoPeriodBar .or-report-filter-brand-icon{
  color:#fff!important;
}
#operativoPeriodBar .or-report-filter-brand-icon svg{
  display:block!important;
  stroke:currentColor!important;
}

/* =========================================================
   TABLET · conserva la matriz de laptop
   ========================================================= */
@media (min-width:601px) and (max-width:1024px){
  .main{
    width:100%!important;
    max-width:100%!important;
    padding-left:8px!important;
    padding-right:8px!important;
    overflow-x:hidden!important;
  }

  .kpis,.report-kpis,.lingerie-kpis,.kpis.or-kpi-matrix{
    display:grid!important;
    grid-template-columns:repeat(var(--v265-kpi-cols,5),minmax(0,1fr))!important;
    gap:6px!important;
  }
  .cards{
    display:grid!important;
    grid-template-columns:repeat(var(--v265-card-cols,3),minmax(0,1fr))!important;
    gap:6px!important;
  }
  .grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.3fr) minmax(0,.7fr)!important;
    gap:7px!important;
  }
  .uploadgrid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .usergrid{grid-template-columns:repeat(4,minmax(0,1fr))!important}

  .kpi,.report-kpi{
    min-width:0!important;
    min-height:76px!important;
    padding:8px 7px!important;
  }
  .lab,.report-kpi .rk-label{font-size:7px!important;line-height:1.08!important}
  .val,.report-kpi .rk-value{font-size:18px!important;line-height:1!important;margin:5px 0 3px!important}
  .note,.report-kpi .rk-note,.report-kpi .rk-sub{font-size:7px!important;line-height:1.15!important}
  .card,.panel{min-width:0!important;padding:8px!important}
  .card h3,.panel h3{font-size:9px!important}
  .big{font-size:16px!important}

  #operativoPeriodBar > .or-report-filter-grid{
    display:flex!important;
    flex-wrap:nowrap!important;
    gap:7px!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    overflow-x:hidden!important;
  }
  #operativoPeriodBar .v259-period-view{
    flex:1.55 1 0!important;
    min-width:0!important;
    width:auto!important;
  }
  #operativoPeriodBar > .or-report-filter-grid > .or-fcontrol:not(.hidden):not(.v249-hidden){
    flex:1 1 0!important;
    min-width:0!important;
    width:auto!important;
  }
  #operativoPeriodBar select,#operativoPeriodBar input{
    min-width:0!important;
    width:100%!important;
    max-width:100%!important;
  }
}

/* =========================================================
   MÓVIL · MISMA MATRIZ DE LAPTOP, sólo reducida
   ========================================================= */
@media (max-width:600px){
  .main{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    padding-left:4px!important;
    padding-right:4px!important;
    overflow-x:hidden!important;
  }

  /* Encabezado más compacto, sin sacrificar contenido. */
  .hero{
    min-height:0!important;
    padding:8px 9px!important;
    margin-bottom:4px!important;
    border-radius:12px!important;
  }
  .hero h1{
    font-size:clamp(17px,4.9vw,21px)!important;
    line-height:1.04!important;
  }
  .hero p{
    font-size:clamp(8px,2.35vw,10px)!important;
    line-height:1.12!important;
  }

  .title{
    font-size:clamp(15px,4.2vw,18px)!important;
    line-height:1.04!important;
    margin:6px 1px 3px!important;
  }
  .subtitle{
    font-size:clamp(8px,2.35vw,10px)!important;
    line-height:1.14!important;
    margin:0 1px 5px!important;
  }

  /* Navegación igual a laptop: una fila completa, más baja y densa. */
  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    display:grid!important;
    grid-template-columns:repeat(var(--v238-count,var(--v265-tab-count,8)),minmax(0,1fr))!important;
    grid-template-rows:48px!important;
    height:48px!important;
    min-height:48px!important;
    max-height:48px!important;
    column-gap:2px!important;
    padding:0 1px!important;
    margin:4px 0 6px!important;
    overflow:hidden!important;
  }
  body.v238-module-operativo #operativoNav>button,
  body.v238-module-analysis #analysisNav>button,
  body.v238-module-operation #v200OperationTabs>button{
    height:48px!important;
    min-height:48px!important;
    max-height:48px!important;
    padding:3px 1px!important;
    gap:1px!important;
    border-radius:8px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-icon,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-icon{
    width:12px!important;
    min-width:12px!important;
    max-width:12px!important;
    height:12px!important;
    min-height:12px!important;
    max-height:12px!important;
    flex-basis:12px!important;
  }
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-label,
  :is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-label{
    height:22px!important;
    min-height:22px!important;
    max-height:22px!important;
    font-size:clamp(5.2px,1.45vw,6.4px)!important;
    line-height:1!important;
  }

  /* Filtros: misma fila de escritorio. Nada queda fuera del viewport. */
  #operativoPeriodBar{
    width:100%!important;
    max-width:100%!important;
    padding:0 5px 6px!important;
    margin:4px 0 6px!important;
    border-radius:11px!important;
    overflow:hidden!important;
  }
  #operativoPeriodBar > .or-report-filter-brand{
    width:calc(100% + 10px)!important;
    min-height:42px!important;
    margin:0 -5px 5px!important;
    padding:6px 8px!important;
    gap:6px!important;
  }
  #operativoPeriodBar .or-report-filter-brand-icon{
    width:30px!important;
    min-width:30px!important;
    height:30px!important;
    border-radius:8px!important;
  }
  #operativoPeriodBar .or-report-filter-brand-icon svg{
    width:16px!important;
    height:16px!important;
  }
  #operativoPeriodBar > .or-report-filter-brand b{
    font-size:clamp(13px,3.8vw,16px)!important;
    line-height:1!important;
  }
  #operativoPeriodBar > .or-report-filter-brand small::after{
    font-size:clamp(7px,2.1vw,9px)!important;
  }

  #operativoPeriodBar > .or-report-filter-grid{
    display:flex!important;
    flex-wrap:nowrap!important;
    align-items:flex-end!important;
    gap:4px!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    overflow:hidden!important;
    padding:0!important;
  }
  #operativoPeriodBar .v259-period-view{
    display:flex!important;
    flex:1.65 1 0!important;
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    gap:2px!important;
  }
  #operativoPeriodBar > .or-report-filter-grid > .or-fcontrol:not(.hidden):not(.v249-hidden),
  #operativoPeriodBar > .or-report-filter-grid > #operPeriodSelectWrap,
  #operativoPeriodBar > .or-report-filter-grid > #operStoreWrap,
  #operativoPeriodBar > .or-report-filter-grid > #operAreaWrap,
  #operativoPeriodBar > .or-report-filter-grid > #operActivityWrap{
    flex:1 1 0!important;
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    margin:0!important;
  }
  #operativoPeriodBar > .or-report-filter-grid > #operStoreWrap{
    flex:1.1 1 0!important;
  }
  #operativoPeriodBar .v259-period-title{
    min-height:10px!important;
    height:10px!important;
    margin:0 0 2px!important;
    font-size:clamp(5.6px,1.7vw,7px)!important;
    gap:2px!important;
  }
  #operativoPeriodBar .v259-period-title-icon,
  #operativoPeriodBar .v259-period-title-icon svg{
    width:9px!important;
    min-width:9px!important;
    height:9px!important;
  }
  #operativoPeriodBar .v259-period-buttons{
    min-height:32px!important;
    height:32px!important;
    border-radius:8px!important;
  }
  #operativoPeriodBar .v259-period-btn{
    min-height:32px!important;
    height:32px!important;
    padding:0 1px!important;
    gap:1px!important;
    font-size:clamp(5.4px,1.55vw,6.5px)!important;
  }
  #operativoPeriodBar .v259-period-mode-icon,
  #operativoPeriodBar .v259-period-mode-icon svg{
    width:8px!important;
    min-width:8px!important;
    height:8px!important;
  }
  #operativoPeriodBar .or-fcontrol label{
    margin:0 0 2px!important;
    gap:2px!important;
    font-size:clamp(5.6px,1.65vw,7px)!important;
    line-height:1!important;
  }
  #operativoPeriodBar .or-fcontrol-icon,
  #operativoPeriodBar .or-fcontrol-icon svg{
    width:10px!important;
    min-width:10px!important;
    height:10px!important;
  }
  #operativoPeriodBar select,
  #operativoPeriodBar input{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:32px!important;
    height:32px!important;
    padding:4px 16px 4px 4px!important;
    border-radius:8px!important;
    font-size:clamp(6.5px,1.9vw,8px)!important;
    text-overflow:ellipsis!important;
  }

  /* KPI: MISMO número de columnas que en laptop, calculado por JS. */
  .kpis,.report-kpis,.lingerie-kpis,.kpis.or-kpi-matrix{
    display:grid!important;
    grid-template-columns:repeat(var(--v265-kpi-cols,5),minmax(0,1fr))!important;
    gap:3px!important;
    width:100%!important;
    max-width:100%!important;
    margin-bottom:5px!important;
  }
  .kpi,.report-kpi{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:58px!important;
    height:auto!important;
    padding:5px 4px!important;
    border-radius:8px!important;
    overflow:hidden!important;
  }
  .lab,.report-kpi .rk-label{
    font-size:clamp(5.1px,1.45vw,6.2px)!important;
    line-height:1.04!important;
    letter-spacing:0!important;
    overflow-wrap:anywhere!important;
  }
  .val,.report-kpi .rk-value{
    margin:4px 0 2px!important;
    font-size:clamp(12px,3.5vw,15px)!important;
    line-height:1!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
  }
  .note,.report-kpi .rk-note,.report-kpi .rk-sub{
    font-size:clamp(4.9px,1.4vw,6px)!important;
    line-height:1.08!important;
    overflow-wrap:anywhere!important;
  }

  /* Tarjetas y paneles con la misma matriz de escritorio. */
  .cards{
    display:grid!important;
    grid-template-columns:repeat(var(--v265-card-cols,3),minmax(0,1fr))!important;
    gap:3px!important;
  }
  .card,.panel{
    min-width:0!important;
    max-width:100%!important;
    padding:5px!important;
    border-radius:8px!important;
  }
  .card h3,.panel h3{
    font-size:clamp(6.2px,1.8vw,7.5px)!important;
    line-height:1.08!important;
  }
  .big{
    font-size:clamp(11px,3.1vw,14px)!important;
    margin:3px 0!important;
  }
  .card small{
    font-size:clamp(5px,1.45vw,6.2px)!important;
    line-height:1.08!important;
  }
  .grid{
    display:grid!important;
    grid-template-columns:minmax(0,1.3fr) minmax(0,.7fr)!important;
    gap:4px!important;
  }
  .uploadgrid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .usergrid{grid-template-columns:repeat(4,minmax(0,1fr))!important}

  /* Tablas: densidad laptop; sólo la tabla grande puede hacer scroll interno. */
  .tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30{
    width:100%!important;
    max-width:100%!important;
    overflow-x:auto!important;
    -webkit-overflow-scrolling:touch!important;
    touch-action:pan-x pan-y!important;
  }
  .table{
    font-size:clamp(6.5px,1.85vw,8px)!important;
  }
  .table th,.table td{
    padding:5px 5px!important;
    line-height:1.05!important;
  }
  table.v264-fit-table{
    width:100%!important;
    min-width:0!important;
    table-layout:auto!important;
  }
  table.v264-fit-table th,table.v264-fit-table td{
    white-space:normal!important;
  }

  /* Análisis Comercial también conserva matriz de laptop. */
  #v161FilterGrid{
    display:grid!important;
    grid-template-columns:repeat(var(--v265-analysis-cols,4),minmax(0,1fr))!important;
    gap:4px!important;
    overflow:visible!important;
  }
  #v161FilterGrid .v161-field{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    padding:3px 4px 4px 24px!important;
  }
  #v161FilterGrid .v166-filter-icon{
    left:5px!important;
    width:14px!important;
    height:14px!important;
  }
  #v161FilterGrid .v166-filter-icon svg{width:13px!important;height:13px!important}
  #v161FilterGrid .v161-field label{font-size:5.8px!important}
  #v161FilterGrid .v161-field select,
  #v161FilterGrid .v161-field input{
    min-height:28px!important;
    height:28px!important;
    font-size:7px!important;
  }
}

/* 320px: NO apilar. Mantener matriz laptop y comprimir todavía más. */
@media (max-width:360px){
  .kpi,.report-kpi{padding:4px 3px!important;min-height:54px!important}
  .val,.report-kpi .rk-value{font-size:11px!important}
  .lab,.report-kpi .rk-label{font-size:4.8px!important}
  .note,.report-kpi .rk-note,.report-kpi .rk-sub{font-size:4.7px!important}
  .card,.panel{padding:4px!important}
  #operativoPeriodBar > .or-report-filter-grid{gap:3px!important}
}
</style>'''

    js = r'''<script id="v265-desktop-matrix-mobile-js">
(function(){
  if(window.__V265_DESKTOP_MATRIX_MOBILE)return;
  window.__V265_DESKTOP_MATRIX_MOBILE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function visible(el){
    if(!el || el.hidden || el.classList.contains('hidden'))return false;
    const cs=getComputedStyle(el);
    return cs.display!=='none' && cs.visibility!=='hidden';
  }

  function setCols(selector,variable,maxCols){
    qa(selector).forEach(host=>{
      const items=Array.from(host.children).filter(visible);
      if(!items.length)return;
      host.style.setProperty(variable,String(Math.max(1,Math.min(items.length,maxCols))));
    });
  }

  function exactFilterSubtitle(){
    const small=q('#operativoPeriodBar > .or-report-filter-brand small');
    if(small && small.textContent.trim()!=='Define la vista del reporte'){
      small.textContent='Define la vista del reporte';
    }
  }

  function sync(){
    exactFilterSubtitle();

    /* Desktop base: KPI=5 columnas; report KPI permite hasta 6; cards=3. */
    setCols('.kpis:not(.report-kpis):not(.lingerie-kpis)','--v265-kpi-cols',5);
    setCols('.report-kpis','--v265-kpi-cols',6);
    setCols('.lingerie-kpis','--v265-kpi-cols',5);
    setCols('.cards','--v265-card-cols',3);

    qa('#operativoNav,#analysisNav,#v200OperationTabs').forEach(host=>{
      const count=Array.from(host.children).filter(el=>el.tagName==='BUTTON'&&visible(el)).length;
      if(count)host.style.setProperty('--v265-tab-count',String(count));
    });

    const af=q('#v161FilterGrid');
    if(af){
      const n=Array.from(af.children).filter(visible).length;
      af.style.setProperty('--v265-analysis-cols',String(Math.max(1,Math.min(n,5))));
    }
  }

  let timer=0;
  function queue(ms=40){
    clearTimeout(timer);
    timer=setTimeout(sync,ms);
  }

  const observer=new MutationObserver(()=>queue(55));
  function start(){
    const root=q('.main')||document.body;
    if(root)observer.observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','style']});
    sync();
    [100,250,600,1200,2200].forEach(ms=>setTimeout(sync,ms));
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav,#analysisNav,#v200OperationTabs,[data-main]')){
      [0,50,160,400].forEach(ms=>setTimeout(sync,ms));
    }
  },false);
  document.addEventListener('change',()=>queue(80),false);
  window.addEventListener('resize',()=>queue(30),{passive:true});
  window.addEventListener('orientationchange',()=>[80,250,600].forEach(ms=>setTimeout(sync,ms)),{passive:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V265] matriz de laptop conservada en móvil/tablet.');
})();
</script>'''

    @m.app.middleware("http")
    async def v265_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v265-desktop-matrix-mobile-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v265-desktop-matrix-mobile-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)

            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V265-DESKTOP-MATRIX-MOBILE",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V265] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V265_DESKTOP_MATRIX_MOBILE = True
    print("[V265] matriz de laptop en móvil/tablet instalada.",flush=True)
