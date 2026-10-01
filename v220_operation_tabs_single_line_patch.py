"""V220 · Operación: pestañas dinámicas en una sola línea.

Regla:
- todas las pestañas visibles de Operación caben en una sola fila;
- el tamaño se calcula con base en el número real de pestañas visibles y
  el ancho disponible del dispositivo/ventana;
- a mayor cantidad de pestañas, menor tarjeta, icono y tipografía;
- no hay segunda fila ni carrusel obligatorio;
- no cambia contenido, orden, permisos, visibilidad ni listeners.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V220_OPERATION_TABS_SINGLE_LINE", False):
        return

    css = r"""<style id="v220-operation-tabs-single-line-css">
/* ==========================================================
   OPERACIÓN · TODAS LAS PESTAÑAS EN UNA SOLA LÍNEA
   ========================================================== */
body[data-v163-module="operation"] #v200OperationTabs{
  --v220-count:5;
  --v220-gap:4px;
  --v220-tab-h:64px;
  --v220-icon:27px;
  --v220-font:8px;
  --v220-radius:13px;
  display:grid!important;
  grid-template-columns:repeat(var(--v220-count),minmax(0,1fr))!important;
  gap:var(--v220-gap)!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  height:auto!important;
  min-height:0!important;
  margin:3px 0 8px!important;
  padding:5px 0 9px!important;
  overflow:visible!important;
  overflow-x:visible!important;
  overflow-y:visible!important;
  scroll-snap-type:none!important;
  scroll-padding:0!important;
  white-space:normal!important;
}

body[data-v163-module="operation"] #v200OperationTabs button,
body[data-v163-module="operation"] #v200OperationTabs button.active{
  position:relative!important;
  display:flex!important;
  flex:initial!important;
  flex-basis:auto!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  min-height:var(--v220-tab-h)!important;
  height:var(--v220-tab-h)!important;
  max-height:var(--v220-tab-h)!important;
  margin:0!important;
  padding:4px 2px 6px!important;
  border-radius:var(--v220-radius)!important;
  align-items:center!important;
  justify-content:center!important;
  gap:3px!important;
  overflow:visible!important;
  white-space:normal!important;
  text-align:center!important;
  font-size:var(--v220-font)!important;
  line-height:1.02!important;
  scroll-snap-align:none!important;
}

body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon{
  flex:0 0 var(--v220-icon)!important;
  width:var(--v220-icon)!important;
  min-width:var(--v220-icon)!important;
  max-width:var(--v220-icon)!important;
  height:var(--v220-icon)!important;
  min-height:var(--v220-icon)!important;
  max-height:var(--v220-icon)!important;
  border-radius:calc(var(--v220-radius) - 3px)!important;
}
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon svg{
  width:calc(var(--v220-icon) * .57)!important;
  height:calc(var(--v220-icon) * .57)!important;
  max-width:calc(var(--v220-icon) * .57)!important;
  max-height:calc(var(--v220-icon) * .57)!important;
}

body[data-v163-module="operation"] #v200OperationTabs .v203-tab-label{
  display:-webkit-box!important;
  -webkit-box-orient:vertical!important;
  -webkit-line-clamp:var(--v220-lines,2)!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:normal!important;
  word-break:normal!important;
  overflow-wrap:anywhere!important;
  font-size:var(--v220-font)!important;
  line-height:1.02!important;
  text-align:center!important;
  margin:0!important;
  padding:0!important;
}

/* La pestaña activa conserva el estilo actual, pero no crece. */
body[data-v163-module="operation"] #v200OperationTabs button.active{
  transform:translateY(-1px)!important;
}
body[data-v163-module="operation"] #v200OperationTabs button.active:after{
  bottom:-6px!important;
  width:min(28px,70%)!important;
  height:3px!important;
}

/* Cualquier regla móvil anterior queda anulada aquí. */
@media(max-width:900px){
  body[data-v163-module="operation"] #v200OperationTabs{
    display:grid!important;
    grid-template-columns:repeat(var(--v220-count),minmax(0,1fr))!important;
    gap:var(--v220-gap)!important;
    width:100%!important;
    max-width:100%!important;
    margin-left:0!important;
    margin-right:0!important;
    padding-left:0!important;
    padding-right:0!important;
    overflow:visible!important;
    scroll-snap-type:none!important;
    scroll-padding-inline:0!important;
  }
  body[data-v163-module="operation"] #v200OperationTabs button,
  body[data-v163-module="operation"] #v200OperationTabs button.active{
    flex:initial!important;
    flex-basis:auto!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    min-height:var(--v220-tab-h)!important;
    height:var(--v220-tab-h)!important;
    max-height:var(--v220-tab-h)!important;
    border-radius:var(--v220-radius)!important;
    padding:4px 2px 6px!important;
    font-size:var(--v220-font)!important;
  }
}

/* Cuando hay muchas pestañas, el texto puede usar hasta 3 líneas dentro
   de la misma tarjeta sin crear una segunda fila de pestañas. */
body[data-v163-module="operation"] #v200OperationTabs.v220-many .v203-tab-label{
  -webkit-line-clamp:3!important;
}
</style>"""

    js = r"""<script id="v220-operation-tabs-single-line-js">
(function(){
  if(window.__V220_OPERATION_TABS_SINGLE_LINE)return;
  window.__V220_OPERATION_TABS_SINGLE_LINE=true;

  const host=()=>document.getElementById('v200OperationTabs');
  const visible=b=>{
    if(!b||b.hidden||b.classList.contains('hidden')||b.getAttribute('aria-hidden')==='true')return false;
    const cs=getComputedStyle(b);
    return cs.display!=='none'&&cs.visibility!=='hidden';
  };
  const clamp=(min,v,max)=>Math.max(min,Math.min(max,v));

  function fit(){
    const h=host();
    if(!h||String(document.body.dataset.v163Module||'').toLowerCase()!=='operation')return;
    const tabs=[...h.querySelectorAll(':scope > button[data-v200-op]')].filter(visible);
    const count=tabs.length||1;
    const width=Math.max(280,h.clientWidth||h.getBoundingClientRect().width||window.innerWidth-24);

    // Reduce separación según aumenta el número de pestañas.
    const gap=count<=5?4:count<=7?3:2;
    const cell=Math.max(20,(width-gap*(count-1))/count);

    // Escala proporcional. En 5 pestañas móviles queda aprox. 70px por tab;
    // si aparecen más, icono/texto/alto se reducen automáticamente.
    const icon=clamp(15,cell*.38,30);
    const font=clamp(5.4,cell*.115,8.8);
    const height=clamp(52,cell*.88,68);
    const radius=clamp(9,cell*.18,14);

    h.style.setProperty('--v220-count',String(count));
    h.style.setProperty('--v220-gap',gap+'px');
    h.style.setProperty('--v220-icon',icon.toFixed(1)+'px');
    h.style.setProperty('--v220-font',font.toFixed(2)+'px');
    h.style.setProperty('--v220-tab-h',height.toFixed(1)+'px');
    h.style.setProperty('--v220-radius',radius.toFixed(1)+'px');
    h.style.setProperty('--v220-lines',count>=8?'3':'2');
    h.classList.toggle('v220-many',count>=8);
  }

  let raf=0;
  function schedule(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(fit);
  }

  const ro=new ResizeObserver(schedule);
  const mo=new MutationObserver(schedule);

  function init(){
    const h=host();if(!h)return;
    if(!h.dataset.v220Observed){
      h.dataset.v220Observed='1';
      ro.observe(h);
      mo.observe(h,{
        childList:true,
        subtree:true,
        attributes:true,
        attributeFilter:['class','hidden','aria-hidden','style']
      });
    }
    fit();
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();

  [80,250,700,1500].forEach(ms=>setTimeout(init,ms));
  window.addEventListener('resize',schedule,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(schedule,120),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,60),{passive:true});
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(fit,30));
  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main="operation"],#v200OperationTabs>button'))setTimeout(fit,60);
  },true);

  console.info('[V220] Operación · pestañas dinámicas en una sola línea.');
})();
</script>"""

    @m.app.middleware("http")
    async def v220_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v220-operation-tabs-single-line-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v220-operation-tabs-single-line-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V220-OP-TABS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V220] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V220_OPERATION_TABS_SINGLE_LINE=True
    print("[V220] Operación · pestañas dinámicas en una sola línea.",flush=True)
