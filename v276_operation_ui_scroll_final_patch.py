"""V276 · Operación UI compacta + scroll móvil definitivo.

Correcciones exclusivas del módulo Operación:
- elimina iconos heredados V166/V269 que quedaban encimados;
- tarjetas más pequeñas y uniformes;
- laptop: 9 KPIs en una sola fila cuando hay ancho suficiente;
- tablet/móvil conservan el mismo diseño compacto de laptop;
- desbloquea scroll vertical táctil en iOS/Android y WebView;
- limpia el subtítulo duplicado de Filtros del reporte.
No modifica datos, cálculos, periodos, permisos ni endpoints.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V276_OPERATION_UI_SCROLL_FINAL", False):
        return

    css = r'''<style id="v276-operation-ui-scroll-final-css">
/* =========================================================
   V276 · OPERACIÓN · TARJETAS LIMPIAS Y MÁS COMPACTAS
   ========================================================= */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpis{
  display:grid!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  gap:4px!important;
  margin:4px 0 6px!important;
  align-items:stretch!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi{
  position:relative!important;
  box-sizing:border-box!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:54px!important;
  min-height:54px!important;
  max-height:54px!important;
  margin:0!important;
  padding:19px 5px 4px!important;
  overflow:hidden!important;
  border:1px solid #d7e3ef!important;
  border-radius:8px!important;
  background:#fff!important;
  box-shadow:0 2px 6px rgba(18,63,115,.04)!important;
}

/* Quitar TODOS los iconos heredados que quedaban en el cuerpo de la tarjeta. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>.v166-kpi-icon,
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>.v164-kpi-icon,
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>.v269-ribbon{
  display:none!important;
  visibility:hidden!important;
  opacity:0!important;
  pointer-events:none!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi:before{
  display:none!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>.v276-ribbon{
  position:absolute!important;
  z-index:30!important;
  left:0!important;
  right:0!important;
  top:0!important;
  display:flex!important;
  align-items:center!important;
  width:100%!important;
  height:17px!important;
  min-height:17px!important;
  padding:0 4px 0 21px!important;
  border-radius:7px 7px 0 0!important;
  background:var(--v276,#168cff)!important;
  color:#fff!important;
  overflow:hidden!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi .v276-icon{
  position:absolute!important;
  left:3px!important;
  top:2px!important;
  display:grid!important;
  place-items:center!important;
  width:13px!important;
  height:13px!important;
  min-width:13px!important;
  min-height:13px!important;
  border-radius:50%!important;
  background:#fff!important;
  color:var(--v276,#168cff)!important;
}
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi .v276-icon svg{
  display:block!important;
  width:7px!important;
  height:7px!important;
  max-width:7px!important;
  max-height:7px!important;
}
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi .v276-title{
  display:block!important;
  width:100%!important;
  min-width:0!important;
  color:#fff!important;
  font-size:5.6px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:0!important;
  text-transform:uppercase!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>small{
  display:none!important;
}
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>b{
  display:block!important;
  margin:1px 0 0!important;
  padding:0!important;
  color:#103f76!important;
  font-size:15px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:-.02em!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>span:not(.v276-ribbon):not(.v166-kpi-icon):not(.v164-kpi-icon){
  display:block!important;
  margin:2px 0 0!important;
  padding:0!important;
  color:#6b7f96!important;
  font-size:5.2px!important;
  line-height:1!important;
  font-weight:650!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

/* Laptop / PC: matriz horizontal compacta. */
@media(min-width:1200px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(var(--v276-kpi-count,9),minmax(0,1fr))!important;
  }
}

/* Laptop más estrecha: 5 + resto. */
@media(min-width:1025px) and (max-width:1199px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(5,minmax(0,1fr))!important;
  }
}

/* Tablet: misma tarjeta de laptop, sólo comprimida. */
@media(min-width:701px) and (max-width:1024px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:4px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:50px!important;
    min-height:50px!important;
    max-height:50px!important;
    padding:18px 4px 3px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>b{font-size:14px!important}
}

/* Móvil: conserva diseño tipo laptop, 3 tarjetas por fila y vertical scroll libre. */
@media(max-width:700px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
    gap:3px!important;
    margin:3px 0 5px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:48px!important;
    min-height:48px!important;
    max-height:48px!important;
    padding:17px 3px 3px!important;
    border-radius:7px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>.v276-ribbon{
    height:16px!important;
    min-height:16px!important;
    padding-left:19px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi .v276-icon{
    width:12px!important;height:12px!important;min-width:12px!important;min-height:12px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi .v276-title{font-size:4.8px!important}
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>b{font-size:12.5px!important}
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>span:not(.v276-ribbon):not(.v166-kpi-icon):not(.v164-kpi-icon){
    font-size:4.5px!important;
  }

  /* Scroll vertical autoritativo para Operación en iPhone/Android/PWA/WebView. */
  html,
  html body.v238-module-operation,
  html body[data-v163-module="operation"]{
    min-height:100%!important;
    height:auto!important;
    max-height:none!important;
    overflow-x:hidden!important;
    overflow-y:auto!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-y pinch-zoom!important;
  }

  body:is(.v238-module-operation,[data-v163-module="operation"]) #appView,
  body:is(.v238-module-operation,[data-v163-module="operation"]) .shell,
  body:is(.v238-module-operation,[data-v163-module="operation"]) .main,
  body:is(.v238-module-operation,[data-v163-module="operation"]) section.page,
  body:is(.v238-module-operation,[data-v163-module="operation"]) section.page.active,
  body:is(.v238-module-operation,[data-v163-module="operation"]) #operativoDynamic,
  body:is(.v238-module-operation,[data-v163-module="operation"]) #operativoDynamicContent{
    min-height:0!important;
    height:auto!important;
    max-height:none!important;
    overflow-y:visible!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-y pinch-zoom!important;
  }

  body:is(.v238-module-operation,[data-v163-module="operation"]) .main{
    overflow-x:hidden!important;
    padding-bottom:90px!important;
  }

  body:is(.v238-module-operation,[data-v163-module="operation"])
  :is(#v200OperationTabs,#operativoPeriodBar,.v149-kpis,.v149-panel,.tablewrap){
    touch-action:pan-y pinch-zoom!important;
    overscroll-behavior-y:auto!important;
  }

  body:is(.v238-module-operation,[data-v163-module="operation"]) .tablewrap{
    touch-action:pan-x pan-y pinch-zoom!important;
    -webkit-overflow-scrolling:touch!important;
  }
}

/* iPhone angosto: no cambiar el diseño, sólo hacerlo más denso. */
@media(max-width:430px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
    gap:2px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:46px!important;
    min-height:46px!important;
    max-height:46px!important;
  }
}

/* Filtros: una sola leyenda. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoPeriodBar>.or-report-filter-brand small::after{
  content:none!important;
  display:none!important;
}
</style>'''

    js = r'''<script id="v276-operation-ui-scroll-final-js">
(function(){
  if(window.__V276_OPERATION_UI_SCROLL_FINAL)return;
  window.__V276_OPERATION_UI_SCROLL_FINAL=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const imp=(el,p,v)=>el&&el.style.setProperty(p,v,'important');

  const ICONS={
    truck:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
    bars:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 19V11M12 19V5M19 19v-9"/></svg>',
    cube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/></svg>',
    clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>',
    percent:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M19 5 5 19"/></svg>',
    people:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="8" r="3"/><path d="M3 19v-1a6 6 0 0 1 12 0v1"/><circle cx="17" cy="9" r="2.3"/></svg>',
    target:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/></svg>'
  };
  const tones=['#168cff','#7c3aed','#e91e78','#ef4444','#10b981','#f59e0b','#0fa9a2','#1d568d','#2563a7'];

  function isOperation(){
    if(document.body.classList.contains('v238-module-operation'))return true;
    if(String(document.body.dataset.v163Module||'').toLowerCase()==='operation')return true;
    try{return String(window.MAIN||MAIN||'').toLowerCase()==='operation'}catch(_){return false}
  }

  function iconFor(label){
    const t=String(label||'').toLowerCase();
    if(t.includes('llegada'))return ICONS.truck;
    if(t.includes('mercanc'))return ICONS.cube;
    if(t.includes('pendiente'))return ICONS.clock;
    if(t.includes('eficiencia')||t.includes('cumpl'))return ICONS.percent;
    if(t.includes('colaborador'))return ICONS.people;
    if(t.includes('prod'))return ICONS.bars;
    return ICONS.target;
  }

  function cleanCard(card,index){
    if(!card)return;

    /* V166/V269 eran la causa de los iconos encimados. Se eliminan del DOM. */
    qa(':scope>.v166-kpi-icon,:scope>.v164-kpi-icon,:scope>.v269-ribbon',card).forEach(x=>x.remove());
    card.classList.remove('v166-iconized-card','v269-option4-card');
    card.style.removeProperty('padding-left');

    const small=q(':scope>small',card);
    const label=(small?.textContent||q(':scope>.v276-ribbon .v276-title',card)?.textContent||'Indicador').trim();
    card.style.setProperty('--v276',tones[index%tones.length]);

    let ribbon=q(':scope>.v276-ribbon',card);
    if(!ribbon){
      ribbon=document.createElement('div');
      ribbon.className='v276-ribbon';
      card.insertBefore(ribbon,card.firstChild);
    }
    ribbon.innerHTML='<span class="v276-icon">'+iconFor(label)+'</span><span class="v276-title"></span>';
    q('.v276-title',ribbon).textContent=label;
  }

  function cards(){
    const grid=q('#operativoDynamicContent .v149-kpis');
    if(!grid)return;
    const list=qa(':scope>.v149-kpi',grid);
    if(!list.length)return;

    grid.style.setProperty('--v276-kpi-count',String(list.length));
    let cols;
    if(window.innerWidth>=1200)cols=list.length;
    else if(window.innerWidth>=1025)cols=Math.min(5,list.length);
    else if(window.innerWidth>=701)cols=Math.min(4,list.length);
    else cols=Math.min(3,list.length);
    imp(grid,'grid-template-columns','repeat('+cols+',minmax(0,1fr))');
    list.forEach(cleanCard);
  }

  function cleanFilterBrand(){
    const small=q('#operativoPeriodBar>.or-report-filter-brand small');
    if(!small)return;
    small.textContent='Define la vista antes de consultar';
  }

  function unlockMobileScroll(){
    if(!isOperation()||window.innerWidth>900)return;
    const modal=q('.modal-backdrop:not(.hidden),[role="dialog"]:not(.hidden)');
    if(modal)return;

    [document.documentElement,document.body,q('#appView'),q('.shell'),q('.main'),q('section.page.active'),q('#operativoDynamic'),q('#operativoDynamicContent')]
      .filter(Boolean)
      .forEach(el=>{
        imp(el,'height','auto');
        imp(el,'max-height','none');
        imp(el,'overflow-y',el===document.documentElement||el===document.body?'auto':'visible');
        imp(el,'overscroll-behavior-y','auto');
        imp(el,'touch-action','pan-y pinch-zoom');
      });

    imp(document.documentElement,'min-height','100%');
    imp(document.body,'min-height','100%');
    imp(document.documentElement,'overflow-x','hidden');
    imp(document.body,'overflow-x','hidden');
    imp(q('.main'),'padding-bottom','90px');
  }

  function sync(){
    if(!isOperation())return;
    cards();
    cleanFilterBrand();
    unlockMobileScroll();
  }

  let timer=0;
  function queue(ms=20){clearTimeout(timer);timer=setTimeout(sync,ms)}
  const mo=new MutationObserver(()=>queue(30));

  function start(){
    mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    sync();
    [50,120,250,500,900,1500,2500,4000].forEach(ms=>setTimeout(sync,ms));
  }

  document.addEventListener('click',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  document.addEventListener('change',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  window.addEventListener('resize',()=>queue(30),{passive:true});
  window.addEventListener('orientationchange',()=>[80,220,500].forEach(ms=>setTimeout(sync,ms)),{passive:true});
  window.addEventListener('pageshow',()=>[40,160,420].forEach(ms=>setTimeout(sync,ms)),{passive:true});
  document.addEventListener('touchstart',()=>unlockMobileScroll(),{passive:true,capture:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V276] Operación: tarjetas limpias/compactas y scroll móvil desbloqueado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v276_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v276-operation-ui-scroll-final-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v276-operation-ui-scroll-final-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V276-OPERATION-UI-SCROLL-FINAL",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V276] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V276_OPERATION_UI_SCROLL_FINAL=True
    print("[V276] Operación: tarjetas compactas sin iconos duplicados + scroll móvil instalado.",flush=True)
