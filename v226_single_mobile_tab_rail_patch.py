"""V227 · Pestañas móviles completas sin desplazamiento."""
from __future__ import annotations
from fastapi.responses import HTMLResponse

def install(m):
    if getattr(m, "_V226_SINGLE_MOBILE_TAB_RAIL", False):
        return
    css=r'''<style id="v226-single-mobile-tab-rail-css">
@media(max-width:900px){
  .v226-tab-shell{
    display:block!important;
    width:100%!important;max-width:100%!important;min-width:0!important;
    margin:0 0 8px!important;padding:0!important;overflow:hidden!important
  }
  .v226-tab-shell.hidden{display:none!important}
  .v226-tab-arrow{display:none!important}

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail{
    display:grid!important;
    grid-template-columns:repeat(var(--v227-tab-count,5),minmax(0,1fr))!important;
    grid-auto-flow:column!important;
    grid-auto-columns:minmax(0,1fr)!important;
    align-items:stretch!important;justify-items:stretch!important;
    gap:2px!important;
    width:100%!important;max-width:100%!important;min-width:0!important;
    height:auto!important;min-height:0!important;
    margin:0!important;padding:4px 2px 6px!important;
    overflow:visible!important;
    touch-action:auto!important;
    scroll-snap-type:none!important;
    white-space:normal!important;
    position:relative!important;left:auto!important;right:auto!important;top:auto!important;
    transform:none!important;box-sizing:border-box!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button{
    position:relative!important;inset:auto!important;float:none!important;
    display:flex!important;flex-direction:column!important;
    align-items:center!important;justify-content:center!important;
    gap:2px!important;
    width:auto!important;min-width:0!important;max-width:none!important;
    height:58px!important;min-height:58px!important;max-height:58px!important;
    margin:0!important;padding:4px 1px!important;
    overflow:hidden!important;white-space:normal!important;text-align:center!important;
    border-radius:10px!important;box-sizing:border-box!important;
    transform:none!important;scroll-snap-align:none!important
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.active{
    transform:none!important;
    box-shadow:0 2px 7px rgba(20,93,160,.12)!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-icon,.v203-tab-icon){
    width:22px!important;min-width:22px!important;max-width:22px!important;
    height:22px!important;min-height:22px!important;max-height:22px!important;
    flex:0 0 22px!important;margin:0!important;border-radius:7px!important
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-icon,.v203-tab-icon) svg{
    width:14px!important;height:14px!important;max-width:14px!important;max-height:14px!important
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-label,.v203-tab-label){
    display:block!important;
    width:100%!important;max-width:100%!important;min-width:0!important;
    overflow:hidden!important;text-overflow:ellipsis!important;
    white-space:normal!important;overflow-wrap:anywhere!important;
    font-size:6.8px!important;line-height:1.02!important;font-weight:850!important;
    text-align:center!important;margin:0!important;padding:0!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="9"] :is(.rt-tab-icon,.v203-tab-icon),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="10"] :is(.rt-tab-icon,.v203-tab-icon),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="11"] :is(.rt-tab-icon,.v203-tab-icon),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="12"] :is(.rt-tab-icon,.v203-tab-icon){
    width:19px!important;min-width:19px!important;max-width:19px!important;
    height:19px!important;min-height:19px!important;max-height:19px!important;flex-basis:19px!important
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="9"] :is(.rt-tab-icon,.v203-tab-icon) svg,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="10"] :is(.rt-tab-icon,.v203-tab-icon) svg,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="11"] :is(.rt-tab-icon,.v203-tab-icon) svg,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="12"] :is(.rt-tab-icon,.v203-tab-icon) svg{
    width:12px!important;height:12px!important;max-width:12px!important;max-height:12px!important
  }
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="9"] :is(.rt-tab-label,.v203-tab-label),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="10"] :is(.rt-tab-label,.v203-tab-label),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="11"] :is(.rt-tab-label,.v203-tab-label),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail[data-v227-count="12"] :is(.rt-tab-label,.v203-tab-label){
    font-size:5.8px!important;line-height:1!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.hidden,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[hidden],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[aria-hidden="true"]{display:none!important}
}
</style>'''
    js=r'''<script id="v226-single-mobile-tab-rail-js">
(function(){
  if(window.__V227_ALL_TABS_VISIBLE)return;window.__V227_ALL_TABS_VISIBLE=true;
  const IDS=['operativoNav','analysisNav','v200OperationTabs'];
  const mobile=()=>window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900;
  const visible=b=>b&&!b.hidden&&!b.classList.contains('hidden')&&b.getAttribute('aria-hidden')!=='true'&&getComputedStyle(b).display!=='none';
  const SHORT={
    'Centro Operativo':'Centro','Centro Ejecutivo':'Centro','Conversión':'Conv.',
    'Recuperación $':'Rec. $','Recuperación por Tienda':'Tienda','Productividad':'Prod.',
    'Recorridos':'Recorr.','Score':'Score','Alertas':'Alertas','Carga de datos':'Carga',
    'Metas y tiendas':'Metas','Macro compañía':'Macro','Acordeón comercial':'Acord.',
    'Tiendas':'Tiendas','Sección / Rubro':'Rubro','Ubicación / Área':'Área',
    'Checklist lencería':'Lencería','Más opciones':'Más','Resumen':'Resumen',
    'Captura diaria':'Captura','Cargar productividad':'Cargar','Estándares Operativos':'Estánd.'
  };
  function moduleName(){
    let m='';try{m=String(MAIN||'').toLowerCase()}catch(_){}
    if(m)return m==='commercial'?'analysis':m;
    const tagged=String(document.body.dataset.v163Module||'').toLowerCase();
    if(tagged)return tagged;
    const active=document.querySelector('#mobileMainNav [data-main].active')||document.querySelector('.side [data-main].active');
    return String(active?.dataset?.main||'').toLowerCase()
  }
  function activeHostId(){
    const m=moduleName();
    if(m==='operativo')return'operativoNav';
    if(m==='analysis')return'analysisNav';
    if(m==='operation')return'v200OperationTabs';
    return''
  }
  function scrubLegacy(){
    if(!mobile())return;
    document.querySelectorAll('.v222-tab-stage').forEach(stage=>{
      const host=stage.querySelector(':scope > #operativoNav,:scope > #analysisNav,:scope > #v200OperationTabs');
      if(host&&stage.parentNode)stage.parentNode.insertBefore(host,stage);
      stage.remove()
    });
    document.querySelectorAll('.v222-tab-arrow,.v226-tab-arrow').forEach(x=>x.remove())
  }
  function shellOf(host){return host?.parentElement?.classList?.contains('v226-tab-shell')?host.parentElement:null}
  function ensureShell(host){
    let shell=shellOf(host);if(shell){shell.querySelectorAll('.v226-tab-arrow').forEach(x=>x.remove());return shell}
    shell=document.createElement('div');shell.className='v226-tab-shell';shell.dataset.host=host.id;
    host.parentNode.insertBefore(shell,host);shell.append(host);return shell
  }
  function compactLabel(btn){
    let label=btn.querySelector('.rt-tab-label,.v203-tab-label');
    if(!label)return;
    if(!label.dataset.v227Full)label.dataset.v227Full=String(label.textContent||'').trim();
    const full=label.dataset.v227Full;
    label.textContent=SHORT[full]||full;
    btn.title=full
  }
  function styleHost(host){
    const tabs=[...host.children].filter(x=>x.tagName==='BUTTON'&&visible(x));
    const count=Math.max(1,tabs.length);
    host.classList.add('v226-mobile-rail');
    host.dataset.v227Count=String(count);
    host.style.setProperty('--v227-tab-count',String(count));
    host.style.setProperty('display','grid','important');
    host.style.setProperty('grid-template-columns','repeat('+count+',minmax(0,1fr))','important');
    host.style.setProperty('grid-auto-flow','column','important');
    host.style.setProperty('grid-auto-columns','minmax(0,1fr)','important');
    host.style.setProperty('width','100%','important');
    host.style.setProperty('max-width','100%','important');
    host.style.setProperty('min-width','0','important');
    host.style.setProperty('overflow','visible','important');
    host.style.setProperty('gap','2px','important');
    host.scrollLeft=0;
    tabs.forEach(btn=>{
      compactLabel(btn);
      btn.style.setProperty('width','auto','important');
      btn.style.setProperty('min-width','0','important');
      btn.style.setProperty('max-width','none','important');
      btn.style.setProperty('flex','none','important');
      btn.style.setProperty('position','relative','important');
      btn.style.setProperty('left','auto','important');
      btn.style.setProperty('right','auto','important');
      btn.style.setProperty('top','auto','important');
      btn.style.setProperty('transform','none','important')
    })
  }
  function syncHero(){
    const m=moduleName(),title=document.querySelector('#heroTitle'),sub=document.querySelector('#heroSub');
    if(!title||!sub)return;
    if(m==='operation'){title.textContent='Operación';sub.textContent='Control diario, productividad por colaborador y eficiencia de mercancía'}
    else if(m==='operativo'){title.textContent='Cambios y Muertos';sub.textContent='Recuperación, conversión, recolección y seguimiento operativo'}
    else if(m==='analysis'&&title.textContent==='Operación'){title.textContent='Análisis Comercial';sub.textContent='Venta, sugerido y utilidad'}
  }
  let raf=0;
  function apply(){
    if(!mobile())return;
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      scrubLegacy();
      const activeId=activeHostId();
      IDS.forEach(id=>{
        const host=document.getElementById(id);if(!host)return;
        if(id!==activeId){
          const shell=shellOf(host);if(shell)shell.classList.add('hidden');
          host.style.setProperty('display','none','important');return
        }
        host.classList.remove('hidden');host.removeAttribute('hidden');host.style.removeProperty('display');
        const shell=ensureShell(host);shell.classList.remove('hidden');
        styleHost(host)
      });
      syncHero()
    })
  }
  const mo=new MutationObserver(m=>{
    if(mobile()&&m.some(x=>x.type==='childList'||(x.type==='attributes'&&['class','hidden','aria-hidden'].includes(x.attributeName))))setTimeout(apply,0)
  });
  function init(){
    if(!mobile())return;
    mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']});
    apply();[80,220,600,1400,3000].forEach(ms=>setTimeout(apply,ms))
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button,#v200OperationTabs>button'))[0,60,160,360].forEach(ms=>setTimeout(apply,ms))
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(apply,40));
  window.addEventListener('resize',()=>setTimeout(apply,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(apply,160),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});
  console.info('[V227] todas las pestañas móviles visibles en una sola fila.');
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
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V227"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V226] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response
    m._V226_SINGLE_MOBILE_TAB_RAIL=True
    print("[V227] todas las pestañas móviles visibles sin desplazamiento.",flush=True)
