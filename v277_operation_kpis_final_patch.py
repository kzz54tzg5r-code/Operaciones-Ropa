"""V277 · Operación: 8 tarjetas finales, sin duplicados ni iconos.

Alcance exclusivo al módulo Operación / Resumen:
- elimina la tarjeta "Llegada Origen" marcada por el usuario;
- elimina la tarjeta duplicada #v162Staff ("Colab. necesarios Origen");
- conserva la tarjeta correcta "Colaboradores necesarios" del resumen;
- usa el <small> nativo como encabezado de color para que el título nunca desaparezca;
- elimina cintas/iconos heredados V166/V269/V275/V276;
- desktop: 8 tarjetas en una fila; tablet/móvil compactan sin perder scroll vertical.
No modifica cálculos, datos, filtros, permisos ni endpoints.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V277_OPERATION_KPIS_FINAL", False):
        return

    css = r'''<style id="v277-operation-kpis-final-css">
/* Ocultar cualquier decoración heredada: la tarjeta usa únicamente su encabezado nativo. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi
:is(.v166-kpi-icon,.v164-kpi-icon,.v269-ribbon,.v275-ribbon,.v276-ribbon){
  display:none!important;
  visibility:hidden!important;
  opacity:0!important;
  pointer-events:none!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi:before{
  display:none!important;
}

/* Matriz final. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpis{
  display:grid!important;
  grid-template-columns:repeat(var(--v277-cols,8),minmax(0,1fr))!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  gap:5px!important;
  margin:5px 0 7px!important;
  align-items:stretch!important;
}

/* Tarjeta compacta, pero con título visible. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi{
  position:relative!important;
  box-sizing:border-box!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:61px!important;
  min-height:61px!important;
  max-height:61px!important;
  margin:0!important;
  padding:23px 7px 5px!important;
  overflow:hidden!important;
  border:1px solid #d7e3ef!important;
  border-radius:9px!important;
  background:#fff!important;
  box-shadow:0 2px 7px rgba(18,63,115,.045)!important;
}

/* El small original es el encabezado: no depende de JS para verse. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>small{
  position:absolute!important;
  z-index:40!important;
  left:0!important;
  right:0!important;
  top:0!important;
  display:flex!important;
  align-items:center!important;
  width:100%!important;
  height:19px!important;
  min-height:19px!important;
  margin:0!important;
  padding:0 7px!important;
  border-radius:8px 8px 0 0!important;
  background:var(--k,#176fe8)!important;
  color:#fff!important;
  font-size:6.2px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:0!important;
  text-transform:uppercase!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>b{
  display:block!important;
  margin:1px 0 0!important;
  padding:0!important;
  color:#103f76!important;
  font-size:18px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:-.02em!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>span:not(.v166-kpi-icon):not(.v164-kpi-icon){
  display:block!important;
  margin:3px 0 0!important;
  padding:0!important;
  color:#6b7f96!important;
  font-size:6px!important;
  line-height:1!important;
  font-weight:650!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

/* La tarjeta duplicada no debe ocupar espacio ni un instante mientras el observer la retira. */
body:is(.v238-module-operation,[data-v163-module="operation"]) #v162Staff{
  display:none!important;
}

/* Tablet */
@media(min-width:701px) and (max-width:1024px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:4px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:57px!important;
    min-height:57px!important;
    max-height:57px!important;
    padding:21px 5px 4px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>small{height:18px!important;min-height:18px!important;font-size:5.8px!important}
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>b{font-size:16px!important}
}

/* Móvil: aspecto de laptop, 4 por fila, scroll vertical libre. */
@media(max-width:700px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:3px!important;
    margin:4px 0 6px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:54px!important;
    min-height:54px!important;
    max-height:54px!important;
    padding:20px 3px 3px!important;
    border-radius:7px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>small{
    height:17px!important;
    min-height:17px!important;
    padding:0 3px!important;
    border-radius:6px 6px 0 0!important;
    font-size:4.6px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>b{font-size:13px!important}
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>span:not(.v166-kpi-icon):not(.v164-kpi-icon){font-size:4.7px!important}

  html,
  html body.v238-module-operation,
  html body[data-v163-module="operation"]{
    min-height:100%!important;
    height:auto!important;
    max-height:none!important;
    overflow-y:auto!important;
    overflow-x:hidden!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-y pinch-zoom!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  :is(#appView,.shell,.main,section.page,section.page.active,#operativoDynamic,#operativoDynamicContent){
    min-height:0!important;
    height:auto!important;
    max-height:none!important;
    overflow-y:visible!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-y pinch-zoom!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"]) .main{
    overflow-x:hidden!important;
    padding-bottom:92px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"]) .tablewrap{
    touch-action:pan-x pan-y pinch-zoom!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:auto!important;
  }
}
</style>'''

    js = r'''<script id="v277-operation-kpis-final-js">
(function(){
  if(window.__V277_OPERATION_KPIS_FINAL)return;
  window.__V277_OPERATION_KPIS_FINAL=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const imp=(el,p,v)=>el&&el.style.setProperty(p,v,'important');

  function isOperation(){
    if(document.body.classList.contains('v238-module-operation'))return true;
    if(String(document.body.dataset.v163Module||'').toLowerCase()==='operation')return true;
    try{return String(window.MAIN||MAIN||'').toLowerCase()==='operation'}catch(_){return false}
  }

  function label(card){
    return String(
      q(':scope>small',card)?.textContent ||
      q(':scope>.v275-ribbon .v275-title',card)?.textContent ||
      q(':scope>.v276-ribbon .v276-title',card)?.textContent ||
      q(':scope>.v269-ribbon .v269-title',card)?.textContent ||
      ''
    ).replace(/\s+/g,' ').trim();
  }

  function clean(){
    if(!isOperation())return;
    const grid=q('#operativoDynamicContent .v149-kpis');
    if(!grid)return;

    /* 1) eliminar la tarjeta duplicada inferior marcada. */
    q('#v162Staff')?.remove();

    /* 2) eliminar Llegada Origen marcada. */
    qa(':scope>.v149-kpi',grid).forEach(card=>{
      const l=label(card).toLowerCase();
      if(l==='llegada origen'||l.startsWith('llegada origen ')){
        card.remove();
        return;
      }

      /* Nada de iconos/cintas superpuestas: conservar small/b/span originales. */
      qa(':scope>.v166-kpi-icon,:scope>.v164-kpi-icon,:scope>.v269-ribbon,:scope>.v275-ribbon,:scope>.v276-ribbon',card)
        .forEach(x=>x.remove());
      card.classList.remove('v166-iconized-card','v269-option4-card');
      card.style.removeProperty('padding-left');
    });

    const cards=qa(':scope>.v149-kpi',grid);
    const count=cards.length||8;
    let cols;
    if(window.innerWidth>=1025)cols=count;
    else if(window.innerWidth>=701)cols=Math.min(4,count);
    else cols=Math.min(4,count);
    grid.style.setProperty('--v277-cols',String(cols));
    imp(grid,'grid-template-columns','repeat('+cols+',minmax(0,1fr))');
  }

  function unlockScroll(){
    if(!isOperation()||window.innerWidth>900)return;
    if(q('.modal-backdrop:not(.hidden),[role="dialog"]:not(.hidden)'))return;
    [document.documentElement,document.body,q('#appView'),q('.shell'),q('.main'),q('section.page.active'),q('#operativoDynamic'),q('#operativoDynamicContent')]
      .filter(Boolean).forEach(el=>{
        imp(el,'height','auto');
        imp(el,'max-height','none');
        imp(el,'overflow-y',(el===document.documentElement||el===document.body)?'auto':'visible');
        imp(el,'overscroll-behavior-y','auto');
        imp(el,'touch-action','pan-y pinch-zoom');
      });
    imp(document.documentElement,'overflow-x','hidden');
    imp(document.body,'overflow-x','hidden');
  }

  function sync(){clean();unlockScroll()}
  let t=0;
  function queue(ms=20){clearTimeout(t);t=setTimeout(sync,ms)}

  const mo=new MutationObserver(()=>queue(25));
  function start(){
    mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    sync();
    [50,120,250,500,900,1500,2500,4000].forEach(ms=>setTimeout(sync,ms));
  }
  document.addEventListener('click',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  document.addEventListener('change',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  document.addEventListener('touchstart',()=>unlockScroll(),{passive:true,capture:true});
  window.addEventListener('resize',()=>queue(30),{passive:true});
  window.addEventListener('orientationchange',()=>[80,220,500].forEach(ms=>setTimeout(sync,ms)),{passive:true});
  window.addEventListener('pageshow',()=>[40,160,420].forEach(ms=>setTimeout(sync,ms)),{passive:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V277] Operación: 8 KPIs finales; Llegada Origen y duplicado de personal retirados.');
})();
</script>'''

    @m.app.middleware("http")
    async def v277_html(request, call_next):
        response=await call_next(request)
        if request.url.path != "/" or getattr(response,"status_code",200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v277-operation-kpis-final-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v277-operation-kpis-final-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V277-OPERATION-KPIS-FINAL",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V277] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V277_OPERATION_KPIS_FINAL=True
    print("[V277] Operación: 8 KPIs finales y scroll móvil instalados.",flush=True)
