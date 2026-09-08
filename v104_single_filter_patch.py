"""V104: una sola experiencia de filtros.

Conserva la barra compacta V103 como única interfaz visible. Se eliminan de la
vista los botones de alternar entre "Desglose interactivo" y "Vista clásica".
El desglose por clic en tabla queda siempre activo y "Más filtros" concentra
la selección manual. Los selectores originales siguen siendo la fuente de
verdad, pero permanecen ocultos para no duplicar controles.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V104_SINGLE_FILTER", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v104-single-filter-css">
/* Una sola forma de filtrar: barra compacta + chips + Más filtros + clic tabla */
#v103DrillBtn,#v103ClassicBtn,#v103ClassicBack,#v102FilterMode,#v102Drill{display:none!important}
body .filters{display:none!important}
#v103FilterShell{display:block!important}
#v103CompactBar{padding-right:10px}
#v103MoreBtn{background:#1769e8!important;border-color:#1769e8!important;color:#fff!important}
#v103CompactBar .v103-version{font-size:0}
#v103CompactBar .v103-version:after{content:'V104';font-size:7px}
</style>
'''

    js = r'''
<script id="v104-single-filter-js">
(function(){
  const KEY='operacionesRopaFilterModeV103';
  try{localStorage.setItem(KEY,'drill')}catch(e){}
  function force(){
    document.body.classList.remove('v103-classic','v103-compact');
    document.body.classList.add('v103-drill');
    try{localStorage.setItem(KEY,'drill')}catch(e){}
  }
  function clickables(){
    /* V103 ya contiene la lógica de desglose. Forzar el modo drill hace que
       marque automáticamente Tienda/Área/Actividad o Tienda/Sección/Catálogo. */
    force();
  }
  const start=()=>{
    force();
    const host=document.getElementById('app')||document.querySelector('main')||document.body;
    new MutationObserver(()=>setTimeout(clickables,30)).observe(host,{childList:true,subtree:true});
    document.addEventListener('click',e=>{
      if(e.target.closest('#v103ClassicBtn,#v103DrillBtn,#v103ClassicBack')){
        e.preventDefault();e.stopPropagation();force();
      }
    },true);
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''

    @module.app.middleware("http")
    async def _v104_single_filter(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v104-single-filter-js" not in html:
                html=html.replace("</head>",css+"</head>",1)
                html=html.replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
            })
        except Exception as exc:
            print(f"[V104-FILTER] warning {type(exc).__name__}: {exc}",flush=True)
            return response

    module._V104_SINGLE_FILTER=True
    print('[V104-FILTER] Una sola barra de filtros activa; desglose por tabla siempre habilitado.',flush=True)
