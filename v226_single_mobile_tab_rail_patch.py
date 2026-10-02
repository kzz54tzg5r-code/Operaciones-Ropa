"""V228 · Pestañas móviles pulidas como el diseño aprobado."""
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
    margin:0 0 9px!important;padding:0!important;overflow:hidden!important
  }
  .v226-tab-shell.hidden{display:none!important}
  .v226-tab-arrow,.v222-tab-arrow{display:none!important}

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail{
    display:grid!important;
    grid-template-columns:repeat(var(--v228-count,5),minmax(0,1fr))!important;
    grid-auto-flow:column!important;
    grid-auto-columns:minmax(0,1fr)!important;
    align-items:stretch!important;
    justify-items:stretch!important;
    gap:var(--v228-gap,3px)!important;
    width:100%!important;max-width:100%!important;min-width:0!important;
    height:auto!important;min-height:0!important;
    margin:0!important;padding:5px 2px 7px!important;
    overflow:hidden!important;
    white-space:normal!important;
    touch-action:auto!important;
    scroll-snap-type:none!important;
    box-sizing:border-box!important;
    position:relative!important;left:auto!important;right:auto!important;top:auto!important;
    transform:none!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button{
    position:relative!important;inset:auto!important;float:none!important;
    display:flex!important;flex-direction:column!important;
    align-items:center!important;justify-content:center!important;
    gap:var(--v228-inner-gap,3px)!important;
    width:auto!important;min-width:0!important;max-width:none!important;
    height:var(--v228-h,64px)!important;
    min-height:var(--v228-h,64px)!important;
    max-height:var(--v228-h,64px)!important;
    margin:0!important;padding:4px 1px 5px!important;
    overflow:hidden!important;white-space:normal!important;text-align:center!important;
    border:1px solid #d5e2ef!important;
    border-radius:var(--v228-radius,13px)!important;
    background:rgba(255,255,255,.98)!important;
    color:#3f6388!important;
    box-shadow:0 4px 12px rgba(25,72,118,.055)!important;
    box-sizing:border-box!important;
    transform:none!important;scroll-snap-align:none!important;
    opacity:1!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.active,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[aria-selected="true"],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.rt-icon-user-active{
    color:#fff!important;
    border-color:#0a5da7!important;
    background:linear-gradient(145deg,#0d4f8b 0%,#0878df 100%)!important;
    box-shadow:0 7px 18px rgba(13,79,139,.20)!important;
    transform:none!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-icon,.v203-tab-icon,.v228-tab-icon){
    display:grid!important;place-items:center!important;
    width:var(--v228-icon,22px)!important;min-width:var(--v228-icon,22px)!important;max-width:var(--v228-icon,22px)!important;
    height:var(--v228-icon,22px)!important;min-height:var(--v228-icon,22px)!important;max-height:var(--v228-icon,22px)!important;
    flex:0 0 var(--v228-icon,22px)!important;
    margin:0!important;padding:0!important;
    border:1px solid #deebf7!important;
    border-radius:calc(var(--v228-radius,13px) - 4px)!important;
    background:#edf5fd!important;
    color:#4d7398!important;
    box-shadow:none!important;
    pointer-events:none!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-icon,.v203-tab-icon,.v228-tab-icon) svg{
    display:block!important;
    width:58%!important;height:58%!important;max-width:58%!important;max-height:58%!important;
    stroke:currentColor!important;fill:none!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.active :is(.rt-tab-icon,.v203-tab-icon,.v228-tab-icon),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[aria-selected="true"] :is(.rt-tab-icon,.v203-tab-icon,.v228-tab-icon),
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.rt-icon-user-active :is(.rt-tab-icon,.v203-tab-icon,.v228-tab-icon){
    background:rgba(255,255,255,.14)!important;
    border-color:rgba(255,255,255,.22)!important;
    color:#fff!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail :is(.rt-tab-label,.v203-tab-label,.v228-tab-label){
    position:static!important;
    display:-webkit-box!important;
    -webkit-box-orient:vertical!important;
    -webkit-line-clamp:3!important;
    width:100%!important;max-width:100%!important;min-width:0!important;
    margin:0!important;padding:0!important;
    overflow:hidden!important;
    color:inherit!important;
    font-size:var(--v228-font,7.4px)!important;
    line-height:1.04!important;
    font-weight:850!important;
    letter-spacing:-.04px!important;
    white-space:pre-line!important;
    text-align:center!important;
    text-overflow:clip!important;
    overflow-wrap:anywhere!important;
    word-break:normal!important;
    hyphens:auto!important;
    pointer-events:none!important
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button.hidden,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[hidden],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v226-mobile-rail>button[aria-hidden="true"]{
    display:none!important
  }
}
</style>'''
    js=r'''<script id="v226-single-mobile-tab-rail-js">
(function(){
  if(window.__V228_POLISHED_MOBILE_TABS)return;
  window.__V228_POLISHED_MOBILE_TABS=true;

  const IDS=['operativoNav','analysisNav','v200OperationTabs'];
  const mobile=()=>window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900;
  const clamp=(min,v,max)=>Math.max(min,Math.min(max,v));
  const visible=b=>b&&!b.hidden&&!b.classList.contains('hidden')&&b.getAttribute('aria-hidden')!=='true'&&getComputedStyle(b).display!=='none';

  const PATHS={
    dashboard:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    gear:'<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6.2L14.7 4h-4l-.3 2.2a8 8 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 1.5.9l.3 2.2h4l.3-2.2a8 8 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/>',
    repeat:'<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    dollar:'<path d="M12 3v18M16 7.5c-.9-.8-2.1-1.2-3.5-1.2-2.2 0-3.7 1-3.7 2.6 0 3.6 7.3 1.8 7.3 5.5 0 1.7-1.6 2.8-3.8 2.8-1.6 0-3-.5-4.1-1.5"/>',
    store:'<path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/>',
    chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    truck:'<path d="M3 6h11v10H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    route:'<path d="M5 19c3-6 11-5 14-12"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="7" r="2"/>',
    upload:'<path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 20h14"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    accordion:'<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="4" rx="1.5"/><rect x="3" y="17" width="18" height="3" rx="1.5"/>',
    building:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h2M14 7h2M8 11h2M14 11h2M8 15h2M14 15h2M9 21v-3h6v3"/>',
    checklist:'<path d="M9 5h10M9 12h10M9 19h10"/><path d="m3 5 1.2 1.2L6.5 4M3 12l1.2 1.2L6.5 11M3 19l1.2 1.2L6.5 18"/>',
    percent:'<path d="m19 5-14 14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    database:'<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>'
  };

  function svg(name){
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(PATHS[name]||PATHS.chart)+'</svg>';
  }

  function norm(s){
    return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  }

  function moduleName(){
    let m='';try{m=String(MAIN||'').toLowerCase()}catch(_){}
    if(m)return m==='commercial'?'analysis':m;
    const tagged=String(document.body.dataset.v163Module||'').toLowerCase();
    if(tagged)return tagged;
    const active=document.querySelector('#mobileMainNav [data-main].active')||document.querySelector('.side [data-main].active');
    return String(active?.dataset?.main||'').toLowerCase();
  }

  function activeHostId(){
    const m=moduleName();
    if(m==='operativo')return'operativoNav';
    if(m==='analysis')return'analysisNav';
    if(m==='operation')return'v200OperationTabs';
    return'';
  }

  function infer(btn){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview);
    const sub=norm(btn.dataset.sub);
    const remembered=String(btn.dataset.v228Full||'').trim();
    const dataLabel=String(btn.dataset.rtLabel||btn.dataset.v203Label||'').trim();
    const raw=remembered||dataLabel||String(btn.title||'').trim()||String(btn.textContent||'').replace(/\s+/g,' ').trim();
    const t=norm(raw);

    if(key==='operations.center'||t.includes('centro operativo')||t.includes('centro ejecutivo'))return['Centro Operativo','Centro\nOperativo','dashboard'];
    if(t==='operacion'||t.startsWith('operacion '))return['Operación','Operación','gear'];
    if(key==='operations.conversion'||op.includes('convers')||t.includes('conversion'))return['Conversión','Conversión','repeat'];
    if(key==='operations.recovery'||op.includes('recuperacion economica')||t.includes('recuperacion 
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
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V228"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V228] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response
    m._V226_SINGLE_MOBILE_TAB_RAIL=True
    print("[V228] pestañas móviles pulidas como diseño aprobado.",flush=True)
)||t==='recuperaciones')return['Recuperación 
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
,'Recuperac.\n
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
,'dollar'];
    if(key==='operations.recovery_store'||op.includes('recuperacion por tienda')||t.includes('recuperacion por tienda'))return['Recuperación por Tienda','Recuperac.\npor Tienda','store'];
    if(t.includes('cargar productividad'))return['Cargar Productividad','Cargar\nProductiv.','truck'];
    if(key==='operations.productivity'||op.includes('productividad')||t==='productividad')return['Productividad','Producti-\nvidad','chart'];
    if(key==='operations.routes'||op.includes('recorridos')||t.includes('recorridos'))return['Recorridos','Recorridos','route'];
    if(btn.id==='openGoalsBtn'||t.includes('metas y tiendas')||t==='metas')return['Metas y tiendas','Metas y\ntiendas','target'];
    if(op.includes('carga de datos')||sub==='analysis-upload'||t.includes('carga de datos'))return['Carga de datos','Carga de\ndatos','database'];

    if(key==='commercial.macro'||sub==='macro'||t.includes('macro compania'))return['Macro compañía','Macro\ncompañía','dashboard'];
    if(key==='commercial.accordion'||sub==='accordion'||t.includes('acordeon comercial'))return['Acordeón comercial','Acordeón\ncomercial','accordion'];
    if(key==='commercial.stores'||sub==='stores'||t==='tiendas')return['Tiendas','Tiendas','building'];
    if(key==='commercial.lingerie_checklist'||sub==='lingerie-checklist'||t.includes('checklist lenceria'))return['Checklist lencería','Checklist\nlencería','checklist'];
    if(t.includes('% sell through')||t.includes('sell through %'))return['% Sell Through','% Sell\nThrough','percent'];
    if(key==='commercial.sellthrough'||sub.includes('sell')||t==='sell through')return['Sell Through','Sell\nThrough','percent'];

    if(t.includes('captura diaria'))return['Captura diaria','Captura\ndiaria','dashboard'];
    if(t.includes('estandares operativos'))return['Estándares Operativos','Estándares\nOperativos','target'];
    if(t==='resumen')return['Resumen','Resumen','dashboard'];

    return[raw||'Reporte',raw||'Reporte','chart'];
  }

  function decorate(btn){
    const [full,mobileLabel,icon]=infer(btn);
    if(!btn.dataset.v228Full)btn.dataset.v228Full=full;
    const signature=full+'|'+mobileLabel+'|'+icon;
    const label=btn.querySelector(':scope > .v228-tab-label');
    if(btn.dataset.v228Signature===signature&&label)return;
    btn.dataset.v228Signature=signature;
    btn.dataset.rtLabel=full;
    btn.title=full;
    btn.innerHTML='<span class="rt-tab-icon v228-tab-icon">'+svg(icon)+'</span><span class="rt-tab-label v228-tab-label"></span>';
    const lab=btn.querySelector(':scope > .v228-tab-label');
    if(lab)lab.textContent=mobileLabel;
  }

  function scrubLegacy(){
    if(!mobile())return;
    document.querySelectorAll('.v222-tab-stage').forEach(stage=>{
      const host=stage.querySelector(':scope > #operativoNav,:scope > #analysisNav,:scope > #v200OperationTabs');
      if(host&&stage.parentNode)stage.parentNode.insertBefore(host,stage);
      stage.remove();
    });
    document.querySelectorAll('.v222-tab-arrow,.v226-tab-arrow').forEach(x=>x.remove());
  }

  function shellOf(host){
    return host?.parentElement?.classList?.contains('v226-tab-shell')?host.parentElement:null;
  }

  function ensureShell(host){
    let shell=shellOf(host);
    if(shell){
      shell.querySelectorAll('.v226-tab-arrow').forEach(x=>x.remove());
      return shell;
    }
    shell=document.createElement('div');
    shell.className='v226-tab-shell';
    shell.dataset.host=host.id;
    host.parentNode.insertBefore(shell,host);
    shell.append(host);
    return shell;
  }

  function styleHost(host){
    const tabs=[...host.children].filter(x=>x.tagName==='BUTTON'&&visible(x));
    const count=Math.max(1,tabs.length);
    const box=host.parentElement?.getBoundingClientRect?.();
    const width=Math.max(300,box?.width||window.innerWidth-24);
    const gap=count<=6?4:count<=8?3:count<=10?2:1;
    const cell=Math.max(24,(width-4-gap*(count-1))/count);
    const icon=clamp(16,cell*.50,27);
    const font=clamp(5.8,cell*.175,9.3);
    const height=clamp(58,icon+font*3.05+18,68);
    const radius=clamp(9,cell*.22,14);
    const innerGap=count>=9?2:3;

    host.classList.add('v226-mobile-rail');
    host.dataset.v228Count=String(count);
    host.style.setProperty('--v228-count',String(count));
    host.style.setProperty('--v228-gap',gap+'px');
    host.style.setProperty('--v228-icon',icon.toFixed(1)+'px');
    host.style.setProperty('--v228-font',font.toFixed(2)+'px');
    host.style.setProperty('--v228-h',height.toFixed(1)+'px');
    host.style.setProperty('--v228-radius',radius.toFixed(1)+'px');
    host.style.setProperty('--v228-inner-gap',innerGap+'px');

    host.style.setProperty('display','grid','important');
    host.style.setProperty('grid-template-columns','repeat('+count+',minmax(0,1fr))','important');
    host.style.setProperty('grid-auto-flow','column','important');
    host.style.setProperty('grid-auto-columns','minmax(0,1fr)','important');
    host.style.setProperty('width','100%','important');
    host.style.setProperty('max-width','100%','important');
    host.style.setProperty('min-width','0','important');
    host.style.setProperty('overflow','hidden','important');
    host.style.setProperty('gap',gap+'px','important');
    host.scrollLeft=0;

    tabs.forEach(btn=>{
      decorate(btn);
      btn.style.setProperty('width','auto','important');
      btn.style.setProperty('min-width','0','important');
      btn.style.setProperty('max-width','none','important');
      btn.style.setProperty('flex','none','important');
      btn.style.setProperty('position','relative','important');
      btn.style.setProperty('left','auto','important');
      btn.style.setProperty('right','auto','important');
      btn.style.setProperty('top','auto','important');
      btn.style.setProperty('transform','none','important');
      btn.style.setProperty('overflow','hidden','important');
    });
  }

  function syncHero(){
    const m=moduleName(),title=document.querySelector('#heroTitle'),sub=document.querySelector('#heroSub');
    if(!title||!sub)return;
    if(m==='operation'){
      title.textContent='Operación';
      sub.textContent='Control diario, productividad por colaborador y eficiencia de mercancía';
    }else if(m==='operativo'){
      title.textContent='Cambios y Muertos';
      sub.textContent='Recuperación, conversión, recolección y seguimiento operativo';
    }else if(m==='analysis'){
      title.textContent='Análisis Comercial';
      sub.textContent='Venta, sugerido y utilidad';
    }
  }

  let raf=0;
  function apply(){
    if(!mobile())return;
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      scrubLegacy();
      const activeId=activeHostId();
      IDS.forEach(id=>{
        const host=document.getElementById(id);
        if(!host)return;
        if(id!==activeId){
          const shell=shellOf(host);
          if(shell)shell.classList.add('hidden');
          host.style.setProperty('display','none','important');
          return;
        }
        host.classList.remove('hidden');
        host.removeAttribute('hidden');
        host.style.removeProperty('display');
        const shell=ensureShell(host);
        shell.classList.remove('hidden');
        styleHost(host);
      });
      syncHero();
    });
  }

  const mo=new MutationObserver(mutations=>{
    if(!mobile())return;
    if(mutations.some(x=>x.type==='childList'||(x.type==='attributes'&&['class','hidden','aria-hidden'].includes(x.attributeName))))setTimeout(apply,0);
  });

  function init(){
    if(!mobile())return;
    if(!document.body.dataset.v228Observed){
      document.body.dataset.v228Observed='1';
      mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']});
    }
    apply();
    [80,220,600,1400,3000].forEach(ms=>setTimeout(apply,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button,#v200OperationTabs>button')){
      [0,60,160,360].forEach(ms=>setTimeout(apply,ms));
    }
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(apply,40));
  window.addEventListener('resize',()=>setTimeout(apply,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(apply,160),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});

  console.info('[V228] pestañas móviles pulidas y legibles en una sola fila.');
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
