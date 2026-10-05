"""V271 · Paridad visual Centro Operativo: móvil/tablet = laptop compacta.

Corrige específicamente la diferencia visible entre Centro Operativo en laptop y
móvil/tablet:
- filtros en la misma fila lógica (Vista operativa + periodo + tienda);
- 6 KPIs en una sola fila, compactos;
- tabla principal con la misma matriz de 6 columnas del escritorio;
- elimina la versión móvil apilada de esa tabla;
- no cambia datos, cálculos, endpoints, roles, permisos ni eventos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V271_CENTER_OPERATIVO_LAPTOP_PARITY", False):
        return

    css = r'''<style id="v271-center-operativo-laptop-parity-css">
/* =========================================================
   V271 · CENTRO OPERATIVO
   Laptop/PC es la referencia visual.
   Móvil/tablet conserva la MISMA estructura, sólo compacta.
   ========================================================= */

@media (max-width:900px){
  /* ---------- Filtros: Vista + Periodo + Tienda en una sola fila ---------- */
  body.v271-center-parity #operativoPeriodBar{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    margin:3px 0 6px!important;
    padding:0 4px 5px!important;
    overflow:hidden!important;
    border-radius:9px!important;
  }

  body.v271-center-parity #operativoPeriodBar>.or-report-filter-brand{
    width:calc(100% + 8px)!important;
    min-height:30px!important;
    height:30px!important;
    margin:0 -4px 4px!important;
    padding:3px 6px!important;
    gap:5px!important;
    border-radius:0!important;
    overflow:hidden!important;
  }
  body.v271-center-parity #operativoPeriodBar .or-report-filter-brand-icon{
    width:22px!important;
    min-width:22px!important;
    height:22px!important;
    border-radius:6px!important;
  }
  body.v271-center-parity #operativoPeriodBar .or-report-filter-brand-icon svg{
    width:13px!important;height:13px!important;
  }
  body.v271-center-parity #operativoPeriodBar>.or-report-filter-brand b{
    font-size:9px!important;
    line-height:1!important;
    white-space:nowrap!important;
  }
  body.v271-center-parity #operativoPeriodBar>.or-report-filter-brand small{
    display:block!important;
    margin-top:1px!important;
    font-size:5.8px!important;
    line-height:1!important;
    white-space:nowrap!important;
  }

  body.v271-center-parity #operativoPeriodBar>.or-report-filter-grid{
    display:grid!important;
    grid-template-columns:minmax(0,2.25fr) minmax(0,.95fr) minmax(0,.95fr)!important;
    grid-template-rows:auto!important;
    grid-auto-flow:row!important;
    align-items:end!important;
    gap:3px!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    overflow:visible!important;
    padding:0!important;
    margin:0!important;
  }

  body.v271-center-parity #operativoPeriodBar .v266-period-view{
    grid-column:1!important;
    grid-row:1!important;
    display:flex!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    flex:none!important;
    margin:0!important;
    padding:0!important;
    gap:2px!important;
    align-self:end!important;
  }
  body.v271-center-parity #operativoPeriodBar #operPeriodSelectWrap{
    grid-column:2!important;
    grid-row:1!important;
    display:flex!important;
  }
  body.v271-center-parity #operativoPeriodBar #operStoreWrap{
    grid-column:3!important;
    grid-row:1!important;
    display:flex!important;
  }
  body.v271-center-parity #operativoPeriodBar #operPeriodSelectWrap,
  body.v271-center-parity #operativoPeriodBar #operStoreWrap{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    flex:none!important;
    flex-direction:column!important;
    align-self:end!important;
    margin:0!important;
    padding:0!important;
  }

  /* En Centro Operativo la referencia de laptop muestra sólo estos 3 bloques. */
  body.v271-center-parity #operativoPeriodBar #operAreaWrap,
  body.v271-center-parity #operativoPeriodBar #operActivityWrap,
  body.v271-center-parity #operativoPeriodBar #operStartWrap,
  body.v271-center-parity #operativoPeriodBar #operEndWrap,
  body.v271-center-parity #operativoPeriodBar #operPeriodApply{
    display:none!important;
  }

  body.v271-center-parity #operativoPeriodBar .v266-period-title,
  body.v271-center-parity #operativoPeriodBar .or-fcontrol label{
    min-height:9px!important;
    height:9px!important;
    margin:0 0 2px!important;
    gap:2px!important;
    font-size:5.5px!important;
    line-height:1!important;
    font-weight:900!important;
    overflow:hidden!important;
    white-space:nowrap!important;
  }
  body.v271-center-parity #operativoPeriodBar .v266-period-title-icon,
  body.v271-center-parity #operativoPeriodBar .v266-period-title-icon svg,
  body.v271-center-parity #operativoPeriodBar .or-fcontrol-icon,
  body.v271-center-parity #operativoPeriodBar .or-fcontrol-icon svg{
    width:9px!important;
    min-width:9px!important;
    height:9px!important;
  }

  body.v271-center-parity #operativoPeriodBar .v266-period-buttons{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    height:28px!important;
    min-height:28px!important;
    border-radius:7px!important;
  }
  body.v271-center-parity #operativoPeriodBar .v266-period-btn{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    height:28px!important;
    min-height:28px!important;
    padding:0 1px!important;
    gap:1px!important;
    font-size:5.4px!important;
    line-height:1!important;
    white-space:nowrap!important;
    overflow:hidden!important;
  }
  body.v271-center-parity #operativoPeriodBar .v266-period-mode-icon,
  body.v271-center-parity #operativoPeriodBar .v266-period-mode-icon svg{
    width:8px!important;
    min-width:8px!important;
    height:8px!important;
  }

  body.v271-center-parity #operativoPeriodBar select{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    height:28px!important;
    min-height:28px!important;
    padding:2px 13px 2px 4px!important;
    border-radius:7px!important;
    font-size:6px!important;
    line-height:1!important;
    text-overflow:ellipsis!important;
  }

  /* ---------- KPIs: exactamente la misma fila de laptop ---------- */
  body.v271-center-parity #operativoDynamicContent .mct-kpi-grid{
    display:grid!important;
    grid-template-columns:repeat(6,minmax(0,1fr))!important;
    gap:3px!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    margin:0 0 5px!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    min-height:50px!important;
    height:50px!important;
    padding:4px 4px 3px!important;
    border-radius:7px!important;
    overflow:hidden!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-label{
    min-height:12px!important;
    height:12px!important;
    font-size:5px!important;
    line-height:1.02!important;
    letter-spacing:0!important;
    white-space:normal!important;
    overflow:hidden!important;
    text-overflow:clip!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-value{
    margin:3px 0 1px!important;
    font-size:11px!important;
    line-height:1!important;
    white-space:nowrap!important;
    overflow:hidden!important;
    text-overflow:ellipsis!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-sub{
    margin-top:2px!important;
    font-size:5px!important;
    line-height:1!important;
    white-space:nowrap!important;
    overflow:hidden!important;
    text-overflow:ellipsis!important;
  }

  /* ---------- Tabla principal: NO sustituir por tarjetas/apilado ---------- */
  body.v271-center-parity #operativoDynamicContent .monthly-cross-mobile{
    display:none!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-desktop{
    display:block!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    margin:0 0 7px!important;
    overflow:hidden!important;
    border-radius:8px!important;
  }
  body.v271-center-parity #operativoDynamicContent table.monthly-cross-table{
    display:table!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    table-layout:fixed!important;
    border-collapse:separate!important;
    border-spacing:0!important;
    font-size:6.3px!important;
  }

  body.v271-center-parity #operativoDynamicContent .monthly-cross-table th:nth-child(1){width:17%!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table th:nth-child(2){width:29%!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table th:nth-child(3){width:17%!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table th:nth-child(4){width:10%!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table th:nth-child(5){width:11%!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table th:nth-child(6){width:16%!important}

  body.v271-center-parity #operativoDynamicContent .monthly-cross-table thead th{
    position:sticky!important;
    top:0!important;
    z-index:2!important;
    height:24px!important;
    padding:4px 3px!important;
    font-size:6.4px!important;
    line-height:1!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    text-align:center!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td{
    height:22px!important;
    min-height:22px!important;
    padding:3px 3px!important;
    font-size:6.4px!important;
    line-height:1.03!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    vertical-align:middle!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td b{
    font-size:6.8px!important;
    line-height:1.02!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat{
    padding:3px 2px!important;
    font-size:6.6px!important;
    line-height:1.03!important;
    text-align:center!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat span{
    font-size:5.4px!important;
    line-height:1!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-value-pieces{
    display:flex!important;
    align-items:baseline!important;
    justify-content:center!important;
    gap:2px!important;
    min-width:0!important;
    white-space:nowrap!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-value-pieces small{
    margin:0!important;
    font-size:4.8px!important;
    line-height:1!important;
    white-space:nowrap!important;
  }

  body.v271-center-parity #operativoDynamicTitle{
    font-size:14px!important;
    line-height:1.05!important;
    margin:4px 0 2px!important;
  }
  body.v271-center-parity #operativoDynamicSub{
    font-size:6.8px!important;
    line-height:1.05!important;
    margin:0 0 4px!important;
  }
  body.v271-center-parity #operativoDynamicContent>.title{
    font-size:12px!important;
    line-height:1.05!important;
    margin:7px 0 4px!important;
  }
}

/* iPhone / Android pequeños: comprimir aún más, nunca apilar. */
@media (max-width:430px){
  body.v271-center-parity #operativoPeriodBar>.or-report-filter-grid{
    grid-template-columns:minmax(0,2.35fr) minmax(0,.92fr) minmax(0,.92fr)!important;
    gap:2px!important;
  }
  body.v271-center-parity #operativoPeriodBar .v266-period-btn{
    font-size:4.9px!important;
  }
  body.v271-center-parity #operativoPeriodBar select{
    font-size:5.5px!important;
    padding-left:3px!important;
  }

  body.v271-center-parity #operativoDynamicContent .mct-kpi-grid{gap:2px!important}
  body.v271-center-parity #operativoDynamicContent .mct-kpi{
    min-height:46px!important;height:46px!important;padding:3px!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-label{
    min-height:11px!important;height:11px!important;font-size:4.6px!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-value{
    font-size:10px!important;margin-top:2px!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-sub{font-size:4.5px!important}

  body.v271-center-parity #operativoDynamicContent .monthly-cross-table thead th{
    padding:3px 2px!important;font-size:5.8px!important;height:22px!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td{
    padding:3px 2px!important;font-size:5.9px!important;height:21px!important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td b{font-size:6.2px!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat{font-size:6px!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat span{font-size:4.9px!important}
  body.v271-center-parity #operativoDynamicContent .mct-value-pieces small{font-size:4.3px!important}
}

/* Tablet/iPad: misma matriz, con lectura más cómoda. */
@media (min-width:701px) and (max-width:900px){
  body.v271-center-parity #operativoPeriodBar>.or-report-filter-grid{
    grid-template-columns:minmax(0,2fr) minmax(0,.8fr) minmax(0,.8fr)!important;
    gap:5px!important;
  }
  body.v271-center-parity #operativoPeriodBar .v266-period-buttons,
  body.v271-center-parity #operativoPeriodBar .v266-period-btn,
  body.v271-center-parity #operativoPeriodBar select{
    height:36px!important;min-height:36px!important;
  }
  body.v271-center-parity #operativoPeriodBar .v266-period-btn{font-size:7px!important}
  body.v271-center-parity #operativoPeriodBar select{font-size:8px!important}

  body.v271-center-parity #operativoDynamicContent .mct-kpi{
    min-height:62px!important;height:62px!important;padding:6px!important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-label{font-size:6.8px!important;min-height:16px!important;height:16px!important}
  body.v271-center-parity #operativoDynamicContent .mct-kpi-value{font-size:15px!important}
  body.v271-center-parity #operativoDynamicContent .mct-kpi-sub{font-size:6.5px!important}

  body.v271-center-parity #operativoDynamicContent .monthly-cross-table thead th{font-size:8px!important;padding:5px 4px!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td{font-size:8px!important;padding:4px!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td b{font-size:8.5px!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat{font-size:8.5px!important}
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat span{font-size:7px!important}
}
</style>'''

    js = r'''<script id="v271-center-operativo-laptop-parity-js">
(function(){
  if(window.__V271_CENTER_OPERATIVO_LAPTOP_PARITY)return;
  window.__V271_CENTER_OPERATIVO_LAPTOP_PARITY=true;

  const q=(s,r=document)=>r.querySelector(s);
  let timer=0;

  function sync(){
    const b=q('#operativoNav > button[data-tab-key="operations.center"]') ||
            q('#operativoNav > button[data-opview="Centro Ejecutivo"]');
    const active=!!b && (
      b.classList.contains('active') ||
      b.getAttribute('aria-selected')==='true'
    );
    document.body.classList.toggle('v271-center-parity',active);

    if(active){
      const period=q('#operPeriodSelectWrap');
      const store=q('#operStoreWrap');
      period?.classList.remove('hidden','v249-hidden');
      store?.classList.remove('hidden','v249-hidden');
      period?.removeAttribute('hidden');
      store?.removeAttribute('hidden');
    }
  }

  function queue(delay=25){
    clearTimeout(timer);
    timer=setTimeout(sync,delay);
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav,#operativoPeriodBar')){
      [0,50,140,320].forEach(ms=>setTimeout(sync,ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(e.target.closest?.('#operativoPeriodBar')){
      [0,60,180].forEach(ms=>setTimeout(sync,ms));
    }
  },true);

  const observer=new MutationObserver(()=>queue(30));
  function start(){
    const nav=q('#operativoNav');
    const dyn=q('#operativoDynamic');
    if(nav)observer.observe(nav,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected','hidden']});
    if(dyn)observer.observe(dyn,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden']});
    sync();
    [100,300,700,1400].forEach(ms=>setTimeout(sync,ms));
  }

  window.addEventListener('resize',()=>queue(20),{passive:true});
  window.addEventListener('orientationchange',()=>[60,220].forEach(ms=>setTimeout(sync,ms)),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(sync,80),{passive:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V271] Centro Operativo: paridad laptop compacta en móvil/tablet activa.');
})();
</script>'''

    @m.app.middleware("http")
    async def v271_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v271-center-operativo-laptop-parity-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v271-center-operativo-laptop-parity-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)

            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V271-CENTER-LAPTOP-PARITY",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V271] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V271_CENTER_OPERATIVO_LAPTOP_PARITY=True
    print("[V271] Centro Operativo con paridad visual laptop compacta instalado.",flush=True)
