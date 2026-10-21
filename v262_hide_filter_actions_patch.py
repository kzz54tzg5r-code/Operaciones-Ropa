"""V262 · Oculta Consultar/Restablecer salvo en Centro Operativo (opción 3).

Corrige el conflicto de especificidad con V259/V254:
- Elimina visualmente Consultar y Restablecer en TODAS las pestañas que reutilizan
  #operativoPeriodBar.
- Mantiene los nodos en DOM para reutilizar la lógica existente de consulta automática.
- No toca cálculos, KPIs, tablas, endpoints ni datos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V262_HIDE_FILTER_ACTIONS", False):
        return

    css = r'''<style id="v262-hide-filter-actions-css">
/* Autoridad máxima sobre V259/V254. Los nodos siguen en DOM para compatibilidad. */
html body:not(.center-three-lanes) #operativoPeriodBar.v250-option9b.v259-has-period > .or-report-filter-grid > button#operPeriodApply,
html body:not(.center-three-lanes) #operativoPeriodBar.v250-option9b > .or-report-filter-grid > button#operPeriodApply,
html body:not(.center-three-lanes) #operativoPeriodBar > .or-report-filter-grid > button#operPeriodApply,
html body:not(.center-three-lanes) #operativoPeriodBar.v250-option9b.v259-has-period > .or-report-filter-grid > button#v254ResetFilters,
html body:not(.center-three-lanes) #operativoPeriodBar.v250-option9b > .or-report-filter-grid > button#v254ResetFilters,
html body:not(.center-three-lanes) #operativoPeriodBar > .or-report-filter-grid > button#v254ResetFilters,
html body:not(.center-three-lanes) #operativoPeriodBar > .or-report-filter-grid > button#v253ResetFilters{
  display:none!important;
  visibility:hidden!important;
  opacity:0!important;
  pointer-events:none!important;
  position:absolute!important;
  width:0!important;
  min-width:0!important;
  max-width:0!important;
  height:0!important;
  min-height:0!important;
  max-height:0!important;
  flex:0 0 0!important;
  padding:0!important;
  margin:0!important;
  border:0!important;
  overflow:hidden!important;
}

/* Al quitar acciones, los filtros útiles absorben todo el ancho. */
html body:not(.center-three-lanes) #operativoPeriodBar.v250-option9b > .or-report-filter-grid,
html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  padding-right:0!important;
}
html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period .v259-period-view{
  flex:1.45 1 390px!important;
}
html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operPeriodSelectWrap{
  flex:1 1 255px!important;
}
html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operStoreWrap{
  flex:1.1 1 285px!important;
}
html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operAreaWrap,
html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operActivityWrap{
  flex:.9 1 220px!important;
}

/* También evita que botones antiguos reaparezcan por caché. */
html body:not(.center-three-lanes) #operativoPeriodBar #v252ResetFilters,
html body:not(.center-three-lanes) #operativoPeriodBar #v253ResetFilters{
  display:none!important;
}

@media(max-width:650px){
  html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period .v259-period-view{
    flex:0 0 286px!important;
    min-width:286px!important;
  }
  html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operPeriodSelectWrap{
    flex:0 0 190px!important;
    min-width:190px!important;
  }
  html body:not(.center-three-lanes) #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operStoreWrap{
    flex:0 0 210px!important;
    min-width:210px!important;
  }
}
</style>'''

    js = r'''<script id="v262-hide-filter-actions-js">
(function(){
  if(window.__V262_HIDE_FILTER_ACTIONS)return;
  window.__V262_HIDE_FILTER_ACTIONS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function hardHide(el){
    if(!el)return;
    // Evita reescribir los mismos estilos y activar continuamente el observer.
    if(el.dataset.v262Hidden==='1'&&el.style.getPropertyValue('display')==='none'&&el.getAttribute('aria-hidden')==='true')return;
    el.style.setProperty('display','none','important');
    el.style.setProperty('visibility','hidden','important');
    el.style.setProperty('opacity','0','important');
    el.style.setProperty('pointer-events','none','important');
    el.style.setProperty('position','absolute','important');
    el.style.setProperty('width','0','important');
    el.style.setProperty('min-width','0','important');
    el.style.setProperty('max-width','0','important');
    el.style.setProperty('height','0','important');
    el.style.setProperty('min-height','0','important');
    el.style.setProperty('max-height','0','important');
    el.style.setProperty('flex','0 0 0','important');
    el.style.setProperty('padding','0','important');
    el.style.setProperty('margin','0','important');
    el.style.setProperty('border','0','important');
    el.style.setProperty('overflow','hidden','important');
    el.dataset.v262Hidden='1';
    el.setAttribute('aria-hidden','true');
    el.tabIndex=-1;
  }

  // Centro Operativo usa la opción 3 aprobada, que sí tiene Consultar.
  // Conservar el ocultamiento histórico únicamente en las otras pestañas.
  function isCenter(){
    // Clase fijada por el controlador operativo real (no por un tab oculto).
    // Las vistas no activas pueden mantener el botón Centro con clase active.
    return document.body.classList.contains('center-three-lanes');
  }
  const forced=['display','visibility','opacity','pointer-events','position',
    'width','min-width','max-width','height','min-height','max-height',
    'flex','padding','margin','border','overflow'];
  function restoreApply(el){
    if(!el)return;
    // Algunas capas antiguas dejan aria-hidden/tabindex sin marcas de propiedad.
    // Retirarlos siempre que Centro Operativo esté realmente activo.
    if(el.dataset.v262Hidden==='1'){
      forced.forEach(prop=>el.style.removeProperty(prop));
      delete el.dataset.v262Hidden;
    }
    if(el.hasAttribute('aria-hidden'))el.removeAttribute('aria-hidden');
    if(el.hasAttribute('tabindex')&&el.tabIndex<0)el.removeAttribute('tabindex');
  }
  function enforce(){
    const bar=q('#operativoPeriodBar');
    if(!bar)return;
    const center=isCenter();
    ['#operPeriodApply','#v254ResetFilters','#v253ResetFilters','#v252ResetFilters'].forEach(sel=>{
      qa(sel,bar).forEach(el=>{
        if(center&&sel==='#operPeriodApply')restoreApply(el);
        else hardHide(el);
      });
    });
  }

  let timer=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(timer);
    timer=setTimeout(enforce,10);
  });

  function start(){
    const bar=q('#operativoPeriodBar');
    if(bar){
      observer.observe(bar,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    }
    observer.observe(document.body,{attributes:true,attributeFilter:['class']});
    enforce();
    [50,150,350,700,1400,2400].forEach(ms=>setTimeout(enforce,ms));
    setInterval(enforce,750);
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button,[data-main],#v200OperationTabs>button')){
      [0,40,120,300,700].forEach(ms=>setTimeout(enforce,ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(e.target?.matches?.('#operPeriodMode,#operPeriodSelect,#operStoreSelect,#operAreaSelect,#operActivitySelect')){
      [0,30,120].forEach(ms=>setTimeout(enforce,ms));
    }
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V262] Consultar/Restablecer ocultos autoritativamente en filtros operativos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v262_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v262-hide-filter-actions-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v262-hide-filter-actions-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V262-HIDE-FILTER-ACTIONS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V262] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V262_HIDE_FILTER_ACTIONS=True
    print("[V262] Consultar/Restablecer ocultos en todas las pestañas operativas.",flush=True)
