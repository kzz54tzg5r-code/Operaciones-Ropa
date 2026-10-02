"""V226 · Navegación móvil única y estable."""
from __future__ import annotations
from fastapi.responses import HTMLResponse

def install(m):
    if getattr(m, "_V226_SINGLE_MOBILE_TAB_RAIL", False):
        return
    css=r'''<style id="v226-single-mobile-tab-rail-css">
@media(max-width:900px){
  .v226-tab-shell{display:grid!important;grid-template-columns:32px minmax(0,1fr) 32px!important;align-items:center!important;gap:4px!important;width:100%!important;max-width:100%!important;min-width:0!important;margin:0 0 8px!important;overflow:hidden!important}
  .v226-tab-shell.hidden{display:none!important}
  .v226-tab-arrow{display:grid!important;place-items:center!important;width:32px!important;min-width:32px!important;max-width:32px!important;height:46px!important;margin:0!important;padding:0!important;border:1px solid #d5e2ef!important;border-radius:12px!important;background:#fff!important;color:#0871cc!important;font-size:24px!important;font-weight:950!important;box-shadow:0 4px 12px rgba(25,72,118,.06)!important;position:relative!important;inset:auto!important;transform:none!important;z-index:3!important}
  .v226-tab-arrow:disabled{opacity:.2!important;pointer-events:none!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail{display:flex!important;grid-template-columns:none!important;grid-auto-flow:unset!important;flex-wrap:nowrap!important;justify-content:flex-start!important;align-items:stretch!important;gap:6px!important;width:100%!important;max-width:100%!important;min-width:0!important;height:auto!important;min-height:0!important;margin:0!important;padding:6px 3px 10px!important;overflow-x:auto!important;overflow-y:hidden!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior-x:contain!important;touch-action:pan-x pan-y!important;scroll-snap-type:x mandatory!important;scroll-padding-inline:6px!important;scrollbar-width:none!important;white-space:nowrap!important;position:relative!important;left:auto!important;right:auto!important;top:auto!important;transform:none!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail::-webkit-scrollbar{display:none!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button{position:relative!important;inset:auto!important;float:none!important;flex:0 0 var(--v226-card-w,104px)!important;flex-basis:var(--v226-card-w,104px)!important;width:var(--v226-card-w,104px)!important;min-width:var(--v226-card-w,104px)!important;max-width:var(--v226-card-w,104px)!important;height:72px!important;min-height:72px!important;max-height:72px!important;margin:0!important;padding:7px 5px 9px!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:5px!important;overflow:hidden!important;white-space:normal!important;text-align:center!important;border-radius:16px!important;box-sizing:border-box!important;scroll-snap-align:center!important;scroll-snap-stop:always!important;transform:none!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.active{transform:none!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-icon,.v203-tab-icon){width:32px!important;min-width:32px!important;max-width:32px!important;height:32px!important;min-height:32px!important;max-height:32px!important;flex:0 0 32px!important;margin:0!important;border-radius:11px!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-icon,.v203-tab-icon) svg{width:18px!important;height:18px!important;max-width:18px!important;max-height:18px!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-label,.v203-tab-label){display:-webkit-box!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:2!important;width:100%!important;max-width:100%!important;min-width:0!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:normal!important;overflow-wrap:anywhere!important;font-size:8.4px!important;line-height:1.06!important;text-align:center!important;margin:0!important;padding:0!important}
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.hidden,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[hidden],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[aria-hidden="true"]{display:none!important}
}
</style>'''
    js=r'''<script id="v226-single-mobile-tab-rail-js">
(function(){
  if(window.__V226_SINGLE_MOBILE_TAB_RAIL)return;window.__V226_SINGLE_MOBILE_TAB_RAIL=true;
  const IDS=['operativoNav','analysisNav','v200OperationTabs'];
  const mobile=()=>window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900;
  const visible=b=>b&&!b.hidden&&!b.classList.contains('hidden')&&b.getAttribute('aria-hidden')!=='true'&&getComputedStyle(b).display!=='none';
  const imp=(el,k,v)=>el?.style?.setProperty(k,v,'important');
  function moduleName(){let m='';try{m=String(MAIN||'').toLowerCase()}catch(_){}if(m)return m==='commercial'?'analysis':m;const tagged=String(document.body.dataset.v163Module||'').toLowerCase();if(tagged)return tagged;const active=document.querySelector('#mobileMainNav [data-main].active')||document.querySelector('.side [data-main].active');return String(active?.dataset?.main||'').toLowerCase()}
  function activeHostId(){const m=moduleName();if(m==='operativo')return'operativoNav';if(m==='analysis')return'analysisNav';if(m==='operation')return'v200OperationTabs';return''}
  function scrubLegacy(){if(!mobile())return;document.querySelectorAll('.v222-tab-stage').forEach(stage=>{const host=stage.querySelector(':scope > #operativoNav,:scope > #analysisNav,:scope > #v200OperationTabs');if(host&&stage.parentNode)stage.parentNode.insertBefore(host,stage);stage.remove()});document.querySelectorAll('.v222-tab-arrow').forEach(x=>x.remove())}
  function shellOf(host){return host?.parentElement?.classList?.contains('v226-tab-shell')?host.parentElement:null}
  function arrow(dir){const b=document.createElement('button');b.type='button';b.className='v226-tab-arrow '+dir;b.setAttribute('aria-label',dir==='prev'?'Pestaña anterior':'Pestaña siguiente');b.textContent=dir==='prev'?'‹':'›';return b}
  function updateArrows(host){const shell=shellOf(host);if(!shell)return;const prev=shell.querySelector('.prev'),next=shell.querySelector('.next'),max=Math.max(0,host.scrollWidth-host.clientWidth),ok=max>3;if(prev)prev.disabled=!ok||host.scrollLeft<=2;if(next)next.disabled=!ok||host.scrollLeft>=max-2}
  function ensureShell(host){let shell=shellOf(host);if(shell)return shell;shell=document.createElement('div');shell.className='v226-tab-shell';shell.dataset.host=host.id;const prev=arrow('prev'),next=arrow('next');host.parentNode.insertBefore(shell,host);shell.append(prev,host,next);const step=()=>{const first=[...host.children].find(x=>x.tagName==='BUTTON'&&visible(x));const gap=parseFloat(getComputedStyle(host).gap||'6')||6;return(first?.getBoundingClientRect().width||104)+gap};prev.onclick=e=>{e.preventDefault();host.scrollBy({left:-step(),behavior:'smooth'})};next.onclick=e=>{e.preventDefault();host.scrollBy({left:step(),behavior:'smooth'})};host.addEventListener('scroll',()=>updateArrows(host),{passive:true});return shell}
  function nearest(host){const tabs=[...host.children].filter(x=>x.tagName==='BUTTON'&&visible(x));if(!tabs.length)return null;const hr=host.getBoundingClientRect(),cx=hr.left+hr.width/2;let best=tabs[0],dist=Infinity;tabs.forEach(b=>{const r=b.getBoundingClientRect(),d=Math.abs((r.left+r.width/2)-cx);if(d<dist){dist=d;best=b}});return best}
  function center(host,b,behavior='smooth'){if(!b)return;const hr=host.getBoundingClientRect(),br=b.getBoundingClientRect(),target=host.scrollLeft+(br.left+br.width/2)-(hr.left+hr.width/2);try{host.scrollTo({left:Math.max(0,target),behavior})}catch(_){host.scrollLeft=Math.max(0,target)}}
  function bind(host){if(host.dataset.v226Bound==='1')return;host.dataset.v226Bound='1';let start=0;host.addEventListener('touchstart',()=>{start=host.scrollLeft},{passive:true});host.addEventListener('touchend',()=>{if(Math.abs(host.scrollLeft-start)<10)return;setTimeout(()=>{const b=nearest(host);if(!b)return;center(host,b,'smooth');if(!b.classList.contains('active'))b.click()},180)},{passive:true});host.addEventListener('click',e=>{const b=e.target.closest?.('button');if(!b||b.parentElement!==host)return;setTimeout(()=>center(host,b,'smooth'),60)})}
  function styleHost(host){const shell=shellOf(host),available=Math.max(260,shell?.getBoundingClientRect().width||window.innerWidth)-72,card=Math.max(98,Math.min(112,available*.31));host.classList.add('v226-mobile-rail');host.style.setProperty('--v226-card-w',card.toFixed(1)+'px');[['display','flex'],['grid-template-columns','none'],['grid-auto-flow','unset'],['flex-wrap','nowrap'],['justify-content','flex-start'],['align-items','stretch'],['width','100%'],['max-width','100%'],['min-width','0'],['margin','0'],['overflow-x','auto'],['overflow-y','hidden'],['touch-action','pan-x pan-y'],['scroll-snap-type','x mandatory']].forEach(([k,v])=>imp(host,k,v));[...host.children].filter(x=>x.tagName==='BUTTON'&&visible(x)).forEach(b=>{imp(b,'flex','0 0 '+card.toFixed(1)+'px');imp(b,'flex-basis',card.toFixed(1)+'px');imp(b,'width',card.toFixed(1)+'px');imp(b,'min-width',card.toFixed(1)+'px');imp(b,'max-width',card.toFixed(1)+'px');imp(b,'position','relative');imp(b,'left','auto');imp(b,'right','auto');imp(b,'top','auto');imp(b,'transform','none')});updateArrows(host)}
  function syncHero(){const m=moduleName(),title=document.querySelector('#heroTitle'),sub=document.querySelector('#heroSub');if(!title||!sub)return;if(m==='operation'){title.textContent='Operación';sub.textContent='Control diario, productividad por colaborador y eficiencia de mercancía'}else if(m==='operativo'){title.textContent='Cambios y Muertos';sub.textContent='Recuperación, conversión, recolección y seguimiento operativo'}else if(m==='analysis'&&title.textContent==='Operación'){title.textContent='Análisis Comercial';sub.textContent='Venta, sugerido y utilidad'}}
  let raf=0;function apply(centerActive=false){if(!mobile())return;cancelAnimationFrame(raf);raf=requestAnimationFrame(()=>{scrubLegacy();const activeId=activeHostId();IDS.forEach(id=>{const host=document.getElementById(id);if(!host)return;if(id!==activeId){const shell=shellOf(host);if(shell)shell.classList.add('hidden');host.style.setProperty('display','none','important');return}host.classList.remove('hidden');host.removeAttribute('hidden');host.style.removeProperty('display');const shell=ensureShell(host);shell.classList.remove('hidden');bind(host);styleHost(host);if(centerActive){const a=[...host.children].find(x=>x.tagName==='BUTTON'&&visible(x)&&(x.classList.contains('active')||x.getAttribute('aria-selected')==='true'));if(a)setTimeout(()=>center(host,a,'auto'),20)}});syncHero()})}
  const mo=new MutationObserver(m=>{if(mobile()&&m.some(x=>x.type==='childList'||(x.type==='attributes'&&['class','hidden','aria-hidden'].includes(x.attributeName))))setTimeout(()=>apply(false),0)});
  function init(){if(!mobile())return;mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']});apply(true);[80,220,600,1400,3000].forEach(ms=>setTimeout(()=>apply(ms<700),ms))}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('click',e=>{if(e.target.closest?.('[data-main]'))[0,60,160,360].forEach(ms=>setTimeout(()=>apply(true),ms));else if(e.target.closest?.('#operativoNav>button,#analysisNav>button,#v200OperationTabs>button'))setTimeout(()=>apply(true),80)},true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(()=>apply(true),40));window.addEventListener('resize',()=>setTimeout(()=>apply(false),80),{passive:true});window.addEventListener('orientationchange',()=>setTimeout(()=>apply(true),160),{passive:true});window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});
  console.info('[V226] navegación móvil única activa.');
})();
</script>'''
    @m.app.middleware("http")
    async def v226_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v226-single-mobile-tab-rail-css" not in html:html=html.replace("</head>",css+"</head>",1)
            if "v226-single-mobile-tab-rail-js" not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None)
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V226"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V226] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response
    m._V226_SINGLE_MOBILE_TAB_RAIL=True
    print("[V226] navegación móvil única instalada.",flush=True)
