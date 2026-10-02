"""V225 · Rail móvil final y autoritativo para pestañas.

Objetivo:
- una sola implementación móvil para Cambios y Muertos, Operación y Análisis;
- tarjetas legibles, nunca comprimidas ni encimadas;
- swipe horizontal nativo + flechas que avanzan una tarjeta;
- neutralizar estilos inline de capas anteriores sin tocar datos, permisos ni reportes.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V225_FINAL_MOBILE_TAB_RAIL", False):
        return

    css = r'''<style id="v225-final-mobile-tab-rail-css">
@media(max-width:900px){
  /* Wrapper único entre flechas. */
  body .v222-tab-stage{
    display:grid!important;
    grid-template-columns:30px minmax(0,1fr) 30px!important;
    align-items:center!important;
    gap:4px!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    overflow:hidden!important;
    margin:0 0 8px!important;
  }
  body .v222-tab-stage.v222-stage-hidden{display:none!important}

  body .v222-tab-stage>.v222-tab-arrow{
    display:grid!important;
    place-items:center!important;
    position:relative!important;
    inset:auto!important;
    transform:none!important;
    width:30px!important;
    min-width:30px!important;
    max-width:30px!important;
    height:44px!important;
    margin:0!important;
    padding:0!important;
    border-radius:12px!important;
    z-index:3!important;
  }

  /* Los tres navegadores comparten exactamente el mismo rail. */
  body[data-v163-module] .v222-tab-stage>:is(#operativoNav,#analysisNav,#v200OperationTabs),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail{
    display:flex!important;
    grid-template-columns:none!important;
    grid-auto-flow:unset!important;
    flex-wrap:nowrap!important;
    justify-content:flex-start!important;
    align-items:stretch!important;
    gap:6px!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    height:auto!important;
    min-height:0!important;
    margin:0!important;
    padding:6px 2px 10px!important;
    overflow-x:auto!important;
    overflow-y:hidden!important;
    overscroll-behavior-x:contain!important;
    -webkit-overflow-scrolling:touch!important;
    scroll-snap-type:x mandatory!important;
    scroll-padding-inline:6px!important;
    scroll-behavior:smooth!important;
    touch-action:pan-x pan-y!important;
    white-space:nowrap!important;
    scrollbar-width:none!important;
    position:relative!important;
    left:auto!important;
    right:auto!important;
    top:auto!important;
    transform:none!important;
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail::-webkit-scrollbar{
    display:none!important;
  }

  /* La tarjeta siempre conserva un ancho real; nunca se aplasta. */
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail>button{
    position:relative!important;
    inset:auto!important;
    float:none!important;
    flex:0 0 var(--v225-card-w,96px)!important;
    flex-basis:var(--v225-card-w,96px)!important;
    width:var(--v225-card-w,96px)!important;
    min-width:var(--v225-card-w,96px)!important;
    max-width:var(--v225-card-w,96px)!important;
    height:66px!important;
    min-height:66px!important;
    max-height:66px!important;
    margin:0!important;
    padding:6px 5px 8px!important;
    display:flex!important;
    flex-direction:column!important;
    align-items:center!important;
    justify-content:center!important;
    gap:5px!important;
    overflow:hidden!important;
    border-radius:15px!important;
    white-space:normal!important;
    text-align:center!important;
    scroll-snap-align:center!important;
    scroll-snap-stop:always!important;
    transform:none!important;
    box-sizing:border-box!important;
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail>button.active{
    transform:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail :is(.rt-tab-icon,.v203-tab-icon){
    flex:0 0 29px!important;
    width:29px!important;
    min-width:29px!important;
    max-width:29px!important;
    height:29px!important;
    min-height:29px!important;
    max-height:29px!important;
    margin:0!important;
    border-radius:10px!important;
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail :is(.rt-tab-icon,.v203-tab-icon) svg{
    width:17px!important;
    height:17px!important;
    max-width:17px!important;
    max-height:17px!important;
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail :is(.rt-tab-label,.v203-tab-label){
    display:-webkit-box!important;
    -webkit-box-orient:vertical!important;
    -webkit-line-clamp:2!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    overflow:hidden!important;
    text-overflow:ellipsis!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    font-size:8.2px!important;
    line-height:1.05!important;
    text-align:center!important;
    margin:0!important;
    padding:0!important;
  }

  /* Si una pestaña está oculta, no deja espacio fantasma. */
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail>button.hidden,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail>button[hidden],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v225-mobile-rail>button[aria-hidden="true"]{
    display:none!important;
  }

  /* El contenido nunca hereda el ancho del rail. */
  body .main,
  body #page-operativo,
  body #operativoDynamic,
  body #operativoDynamicContent{
    min-width:0!important;
    max-width:100vw!important;
  }
}
</style>'''

    js = r'''<script id="v225-final-mobile-tab-rail-js">
(function(){
  if(window.__V225_FINAL_MOBILE_TAB_RAIL)return;
  window.__V225_FINAL_MOBILE_TAB_RAIL=true;
  if(window.matchMedia?.('(max-width:900px)')?.matches ?? (window.innerWidth<=900)){
    console.info('[V225] móvil delegado a V226.');
    return;
  }

  const ids=['operativoNav','analysisNav','v200OperationTabs'];
  const q=id=>document.getElementById(id);
  const mobile=()=>window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900;
  const visible=b=>b && !b.hidden && !b.classList.contains('hidden') && b.getAttribute('aria-hidden')!=='true' && getComputedStyle(b).display!=='none';
  const imp=(el,k,v)=>el?.style?.setProperty(k,v,'important');

  function currentModule(){
    const active=document.querySelector('.side [data-main].active')||document.querySelector('#mobileMainNav [data-main].active');
    return String(active?.dataset?.main||document.body.dataset.v163Module||'').toLowerCase();
  }

  function owns(host){
    const mod=currentModule();
    return (host.id==='operativoNav'&&mod==='operativo') ||
      (host.id==='analysisNav'&&mod==='analysis') ||
      (host.id==='v200OperationTabs'&&mod==='operation');
  }

  function sanitizeStages(){
    const valid=new Set(ids);
    const seen=new Set();
    [...document.querySelectorAll('.v222-tab-stage')].forEach(stage=>{
      const host=[...stage.children].find(x=>valid.has(x.id));
      if(!host){stage.remove();return}
      if(seen.has(host.id)){
        stage.parentNode?.insertBefore(host,stage);
        stage.remove();
        return;
      }
      seen.add(host.id);
      stage.dataset.host=host.id;
      const arrows=[...stage.children].filter(x=>x.classList?.contains('v222-tab-arrow'));
      arrows.slice(2).forEach(x=>x.remove());
    });
  }

  function stageOf(host){
    if(!host)return null;
    const p=host.parentElement;
    return p?.classList?.contains('v222-tab-stage')?p:null;
  }

  function cardWidth(host){
    const stage=stageOf(host);
    const available=Math.max(250,stage?.getBoundingClientRect().width||host.getBoundingClientRect().width||window.innerWidth);
    return Math.max(90,Math.min(104,available*.28));
  }

  function applyHost(host){
    if(!host||!host.isConnected)return;
    const own=owns(host);
    const stage=stageOf(host);

    if(stage){
      stage.classList.toggle('v222-stage-hidden',!own);
      if(!own)return;
    }else if(!own){
      return;
    }

    if(!mobile()){
      host.classList.remove('v225-mobile-rail');
      host.style.removeProperty('--v225-card-w');
      return;
    }

    host.classList.add('v225-mobile-rail');
    const cw=cardWidth(host);
    host.style.setProperty('--v225-card-w',cw.toFixed(1)+'px');

    // Inline !important derrota las capas V203/V220/V221 que siguen vivas.
    imp(host,'display','flex');
    imp(host,'grid-template-columns','none');
    imp(host,'grid-auto-flow','unset');
    imp(host,'flex-wrap','nowrap');
    imp(host,'justify-content','flex-start');
    imp(host,'align-items','stretch');
    imp(host,'width','100%');
    imp(host,'max-width','100%');
    imp(host,'min-width','0');
    imp(host,'margin','0');
    imp(host,'padding','6px 2px 10px');
    imp(host,'overflow-x','auto');
    imp(host,'overflow-y','hidden');
    imp(host,'touch-action','pan-x pan-y');
    imp(host,'scroll-snap-type','x mandatory');
    imp(host,'scroll-padding-inline','6px');
    imp(host,'position','relative');
    imp(host,'left','auto');
    imp(host,'right','auto');
    imp(host,'transform','none');

    [...host.children].filter(x=>x.tagName==='BUTTON').forEach(btn=>{
      if(!visible(btn))return;
      imp(btn,'position','relative');
      imp(btn,'left','auto');imp(btn,'right','auto');imp(btn,'top','auto');
      imp(btn,'flex','0 0 '+cw.toFixed(1)+'px');
      imp(btn,'flex-basis',cw.toFixed(1)+'px');
      imp(btn,'width',cw.toFixed(1)+'px');
      imp(btn,'min-width',cw.toFixed(1)+'px');
      imp(btn,'max-width',cw.toFixed(1)+'px');
      imp(btn,'height','66px');
      imp(btn,'min-height','66px');
      imp(btn,'max-height','66px');
      imp(btn,'margin','0');
      imp(btn,'transform','none');
      imp(btn,'scroll-snap-align','center');
    });

    updateArrows(host);
  }

  function updateArrows(host){
    const stage=stageOf(host);if(!stage)return;
    const arrows=[...stage.children].filter(x=>x.classList?.contains('v222-tab-arrow'));
    const overflow=host.scrollWidth>host.clientWidth+3;
    stage.classList.toggle('v222-no-scroll',!overflow);
    if(arrows[0])arrows[0].disabled=!overflow||host.scrollLeft<=2;
    if(arrows[1])arrows[1].disabled=!overflow||host.scrollLeft+host.clientWidth>=host.scrollWidth-3;
  }

  function centerNearest(host){
    const tabs=[...host.children].filter(x=>x.tagName==='BUTTON'&&visible(x));
    if(!tabs.length)return;
    const hr=host.getBoundingClientRect(),cx=hr.left+hr.width/2;
    let best=tabs[0],dist=Infinity;
    tabs.forEach(b=>{
      const r=b.getBoundingClientRect();
      const d=Math.abs((r.left+r.width/2)-cx);
      if(d<dist){dist=d;best=b}
    });
    try{best.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}catch(_){}
  }

  function bind(host){
    if(!host||host.dataset.v225Bound==='1')return;
    host.dataset.v225Bound='1';

    let sx=0,sy=0,start=0,mode='idle',drag=false;
    host.addEventListener('touchstart',e=>{
      if(!mobile()||!e.touches||e.touches.length!==1)return;
      const t=e.touches[0];sx=t.clientX;sy=t.clientY;start=host.scrollLeft;mode='pending';drag=false;
    },{passive:true});

    host.addEventListener('touchmove',e=>{
      if(!mobile()||!e.touches||e.touches.length!==1||mode==='idle')return;
      const t=e.touches[0],dx=t.clientX-sx,dy=t.clientY-sy;
      if(mode==='pending'){
        if(Math.abs(dx)<5&&Math.abs(dy)<5)return;
        if(Math.abs(dx)>Math.abs(dy)*1.08)mode='horizontal';
        else {mode='vertical';return}
      }
      if(mode==='horizontal'){
        drag=drag||Math.abs(dx)>7;
        e.preventDefault();
        host.scrollLeft=start-dx;
        updateArrows(host);
      }
    },{passive:false});

    const end=()=>{
      if(mode==='horizontal'&&drag)setTimeout(()=>centerNearest(host),20);
      mode='idle';
    };
    host.addEventListener('touchend',end,{passive:true});
    host.addEventListener('touchcancel',end,{passive:true});
    host.addEventListener('scroll',()=>updateArrows(host),{passive:true});

    host.addEventListener('click',e=>{
      const btn=e.target.closest?.(':scope > button');
      if(!btn)return;
      [40,120].forEach(ms=>setTimeout(()=>{
        try{btn.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}catch(_){}
      },ms));
    });
  }

  function bindStageArrows(host){
    const stage=stageOf(host);if(!stage||stage.dataset.v225Arrows==='1')return;
    stage.dataset.v225Arrows='1';
    const arrows=[...stage.children].filter(x=>x.classList?.contains('v222-tab-arrow'));
    const step=()=>{
      const first=[...host.children].find(x=>x.tagName==='BUTTON'&&visible(x));
      const gap=parseFloat(getComputedStyle(host).gap||'6')||6;
      return (first?.getBoundingClientRect().width||96)+gap;
    };
    if(arrows[0])arrows[0].addEventListener('click',e=>{
      e.preventDefault();e.stopPropagation();
      host.scrollBy({left:-step(),behavior:'smooth'});
    },true);
    if(arrows[1])arrows[1].addEventListener('click',e=>{
      e.preventDefault();e.stopPropagation();
      host.scrollBy({left:step(),behavior:'smooth'});
    },true);
  }

  let raf=0;
  function apply(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      sanitizeStages();
      ids.forEach(id=>{
        const host=q(id);if(!host)return;
        bind(host);
        bindStageArrows(host);
        applyHost(host);
      });
    });
  }

  const observers=[];
  function observe(){
    ids.forEach(id=>{
      const host=q(id);
      if(!host||host.dataset.v225Observed==='1')return;
      host.dataset.v225Observed='1';
      const mo=new MutationObserver(muts=>{
        if(muts.some(m=>m.type==='childList'||m.type==='attributes')){
          requestAnimationFrame(apply);
          setTimeout(apply,20);
        }
      });
      mo.observe(host,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']});
      observers.push(mo);
    });
  }

  function init(){
    observe();
    apply();
    // Ejecutarse detrás de las capas históricas que tienen timers propios.
    [120,340,860,1700,2900].forEach(ms=>setTimeout(apply,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav,#analysisNav,#v200OperationTabs')){
      [0,90,180,320,720].forEach(ms=>setTimeout(apply,ms));
    }
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>[30,120,260].forEach(ms=>setTimeout(apply,ms)));
  window.addEventListener('resize',()=>setTimeout(apply,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(apply,160),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});

  console.info('[V225] rail móvil final: swipe + flechas + tarjetas sin encimar.');
})();
</script>'''

    @m.app.middleware("http")
    async def v225_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v225-final-mobile-tab-rail-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v225-final-mobile-tab-rail-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V225-FINAL-MOBILE-RAIL",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V225] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V225_FINAL_MOBILE_TAB_RAIL=True
    print("[V225] rail móvil final instalado.",flush=True)
