"""V229 · Navegación móvil final, única y sin duplicados.

Un solo dueño visual para las pestañas móviles de:
- Cambios y Muertos
- Análisis Comercial
- Operación

No crea botones nuevos. Reutiliza los botones existentes, elimina wrappers/flechas
heredados y fuerza una sola fila con tamaño dinámico según las pestañas visibles.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V229_MOBILE_TABS_FINAL", False):
        return

    css = r'''<style id="v229-mobile-tabs-final-css">
@media(max-width:900px){
  /* Neutraliza wrappers históricos sin duplicar navegación. */
  body .v222-tab-stage,
  body .v226-tab-shell{
    display:block!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    margin:0 0 8px!important;
    padding:0!important;
    overflow:hidden!important;
  }
  body .v222-tab-stage>.v222-tab-arrow,
  body .v226-tab-shell>.v226-tab-arrow,
  body .v222-tab-arrow,
  body .v226-tab-arrow{
    display:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs{
    display:grid!important;
    grid-template-columns:repeat(var(--v229-count,5),minmax(0,1fr))!important;
    grid-template-rows:var(--v229-h,64px)!important;
    grid-auto-flow:row!important;
    grid-auto-rows:0!important;
    align-items:stretch!important;
    justify-items:stretch!important;
    column-gap:var(--v229-gap,3px)!important;
    row-gap:0!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    height:var(--v229-h,64px)!important;
    min-height:var(--v229-h,64px)!important;
    max-height:var(--v229-h,64px)!important;
    margin:2px 0 10px!important;
    padding:0 2px!important;
    overflow:hidden!important;
    overflow-x:hidden!important;
    overflow-y:hidden!important;
    white-space:normal!important;
    touch-action:auto!important;
    scroll-snap-type:none!important;
    box-sizing:border-box!important;
    position:relative!important;
    inset:auto!important;
    transform:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.active,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button[aria-selected="true"],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.rt-icon-user-active{
    position:relative!important;
    inset:auto!important;
    float:none!important;
    display:flex!important;
    flex:none!important;
    flex-direction:column!important;
    align-items:center!important;
    justify-content:center!important;
    gap:var(--v229-inner-gap,2px)!important;
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    height:var(--v229-h,64px)!important;
    min-height:var(--v229-h,64px)!important;
    max-height:var(--v229-h,64px)!important;
    margin:0!important;
    padding:4px 1px 5px!important;
    overflow:hidden!important;
    white-space:normal!important;
    text-align:center!important;
    box-sizing:border-box!important;
    border:1px solid #d5e2ef!important;
    border-radius:var(--v229-radius,12px)!important;
    background:rgba(255,255,255,.98)!important;
    color:#436586!important;
    box-shadow:0 3px 10px rgba(25,72,118,.055)!important;
    opacity:1!important;
    transform:none!important;
    scroll-snap-align:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.active,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button[aria-selected="true"],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.rt-icon-user-active{
    color:#fff!important;
    border-color:#0a5da7!important;
    background:linear-gradient(145deg,#0d4f8b 0%,#0878df 100%)!important;
    box-shadow:0 6px 16px rgba(13,79,139,.18)!important;
    transform:none!important;
  }

  /* Quita subrayados/indicadores heredados: la selección es la tarjeta azul. */
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button::after,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button::before{
    display:none!important;
    content:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs .v229-tab-icon{
    display:grid!important;
    place-items:center!important;
    flex:0 0 var(--v229-icon,18px)!important;
    width:var(--v229-icon,18px)!important;
    min-width:var(--v229-icon,18px)!important;
    max-width:var(--v229-icon,18px)!important;
    height:var(--v229-icon,18px)!important;
    min-height:var(--v229-icon,18px)!important;
    max-height:var(--v229-icon,18px)!important;
    margin:0!important;
    padding:0!important;
    border:1px solid #dce9f5!important;
    border-radius:calc(var(--v229-radius,12px) - 4px)!important;
    background:#edf5fd!important;
    color:#496f93!important;
    box-shadow:none!important;
    pointer-events:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs .v229-tab-icon svg{
    display:block!important;
    width:58%!important;
    height:58%!important;
    max-width:58%!important;
    max-height:58%!important;
    stroke:currentColor!important;
    fill:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.active .v229-tab-icon,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button[aria-selected="true"] .v229-tab-icon,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.rt-icon-user-active .v229-tab-icon{
    background:rgba(255,255,255,.14)!important;
    border-color:rgba(255,255,255,.22)!important;
    color:#fff!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs .v229-tab-label{
    position:static!important;
    display:-webkit-box!important;
    -webkit-box-orient:vertical!important;
    -webkit-line-clamp:3!important;
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    height:auto!important;
    min-height:0!important;
    margin:0!important;
    padding:0!important;
    overflow:hidden!important;
    color:inherit!important;
    font-size:var(--v229-font,6px)!important;
    line-height:1.02!important;
    font-weight:850!important;
    letter-spacing:-.04px!important;
    white-space:pre-line!important;
    text-align:center!important;
    text-overflow:clip!important;
    overflow-wrap:anywhere!important;
    word-break:normal!important;
    hyphens:auto!important;
    pointer-events:none!important;
  }

  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button.hidden,
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button[hidden],
  body[data-v163-module] :is(#operativoNav,#analysisNav,#v200OperationTabs).v229-mobile-tabs>button[aria-hidden="true"]{
    display:none!important;
  }

  /* Nunca mostrar más de un navegador de reportes a la vez. */
  body[data-v163-module="operativo"] :is(#analysisNav,#v200OperationTabs),
  body[data-v163-module="analysis"] :is(#operativoNav,#v200OperationTabs),
  body[data-v163-module="operation"] :is(#operativoNav,#analysisNav),
  body[data-v163-module="users"] :is(#operativoNav,#analysisNav,#v200OperationTabs),
  body[data-v163-module="share"] :is(#operativoNav,#analysisNav,#v200OperationTabs){
    display:none!important;
  }
}
</style>'''

    js = r'''<script id="v229-mobile-tabs-final-js">
(function(){
  if(window.__V229_MOBILE_TABS_FINAL)return;
  window.__V229_MOBILE_TABS_FINAL=true;

  const IDS=['operativoNav','analysisNav','v200OperationTabs'];
  const mobile=()=>window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900;
  const clamp=(min,v,max)=>Math.max(min,Math.min(max,v));
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();

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

  const svg=name=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(PATHS[name]||PATHS.chart)+'</svg>';

  function moduleName(){
    let m='';
    try{m=String(MAIN||'').toLowerCase()}catch(_){}
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

  function stableKey(btn){
    if(btn.dataset.tabKey)return'tab:'+btn.dataset.tabKey;
    if(btn.dataset.sub)return'sub:'+btn.dataset.sub;
    if(btn.dataset.opview)return'op:'+btn.dataset.opview;
    if(btn.dataset.operationTab)return'operation:'+btn.dataset.operationTab;
    if(btn.id)return'id:'+btn.id;
    return'';
  }

  function dedupe(host){
    const seen=new Set();
    [...host.children].filter(x=>x.tagName==='BUTTON').forEach(btn=>{
      const key=stableKey(btn);
      if(!key)return;
      if(seen.has(key)){btn.remove();return;}
      seen.add(key);
    });
  }

  function originalLabel(btn){
    if(btn.dataset.v229Original)return btn.dataset.v229Original;
    const dataLabel=String(btn.dataset.rtLabel||btn.dataset.v203Label||'').trim();
    const current=String(btn.textContent||'').replace(/\s+/g,' ').trim();
    const title=String(btn.title||'').trim();
    const value=dataLabel||title||current||'Reporte';
    btn.dataset.v229Original=value;
    return value;
  }

  function meta(btn){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview);
    const sub=norm(btn.dataset.sub);
    const raw=originalLabel(btn);
    const t=norm(raw);

    if(key==='operations.center'||t.includes('centro operativo')||t.includes('centro ejecutivo'))return['Centro Operativo','Centro\nOperativo','dashboard'];
    if(t==='operacion'||t.startsWith('operacion '))return['Operación','Operación','gear'];
    if(key==='operations.conversion'||op.includes('convers')||t.includes('conversion'))return['Conversión','Conversión','repeat'];
    if(key==='operations.recovery'||op.includes('recuperacion economica')||t.includes('recuperacion $')||t==='recuperaciones')return['Recuperación $','Recuperac.\n$','dollar'];
    if(key==='operations.recovery_store'||op.includes('recuperacion por tienda')||t.includes('recuperacion por tienda'))return['Recuperación por Tienda','Recuperac.\npor Tienda','store'];
    if(t.includes('cargar productividad'))return['Cargar productividad','Cargar\nProductiv.','truck'];
    if(key==='operations.productivity'||op.includes('productividad')||t==='productividad')return['Productividad','Producti-\nvidad','chart'];
    if(key==='operations.routes'||op.includes('recorridos')||t.includes('recorridos'))return['Recorridos','Recorridos','route'];
    if(btn.id==='openGoalsBtn'||t.includes('metas y tiendas')||t==='metas')return['Metas y tiendas','Metas y\ntiendas','target'];
    if(op.includes('carga de datos')||sub==='analysis-upload'||t.includes('carga de datos'))return['Carga de datos','Carga de\ndatos','database'];

    if(key==='commercial.macro'||sub==='macro'||t.includes('macro compania'))return['Macro compañía','Macro\ncompañía','dashboard'];
    if(key==='commercial.accordion'||sub==='accordion'||t.includes('acordeon comercial'))return['Acordeón comercial','Acordeón\ncomercial','accordion'];
    if(key==='commercial.stores'||sub==='stores'||t==='tiendas')return['Tiendas','Tiendas','building'];
    if(key==='commercial.lingerie_checklist'||sub==='lingerie-checklist'||t.includes('checklist lenceria'))return['Checklist lencería','Checklist\nlencería','checklist'];
    if((t.includes('%')&&t.includes('sell'))||t.includes('sell through %'))return['% Sell Through','% Sell\nThrough','percent'];
    if(key==='commercial.sellthrough'||sub.includes('sell')||t==='sell through')return['Sell Through','Sell\nThrough','percent'];

    if(t.includes('captura diaria'))return['Captura diaria','Captura\ndiaria','dashboard'];
    if(t.includes('estandares operativos'))return['Estándares Operativos','Estándares\nOperativos','target'];
    if(t==='resumen')return['Resumen','Resumen','dashboard'];

    return[raw,raw,'chart'];
  }

  function decorate(btn){
    const [full,label,icon]=meta(btn);
    const sig=full+'|'+label+'|'+icon;
    if(btn.dataset.v229Signature===sig&&btn.querySelector(':scope>.v229-tab-label'))return;
    btn.dataset.v229Signature=sig;
    btn.dataset.rtLabel=full;
    btn.title=full;
    btn.innerHTML='<span class="v229-tab-icon">'+svg(icon)+'</span><span class="v229-tab-label"></span>';
    const lab=btn.querySelector(':scope>.v229-tab-label');
    if(lab)lab.textContent=label;
  }

  function unwrapLegacy(){
    document.querySelectorAll('.v222-tab-stage,.v226-tab-shell').forEach(stage=>{
      const host=stage.querySelector(':scope>#operativoNav,:scope>#analysisNav,:scope>#v200OperationTabs');
      if(host&&stage.parentNode){
        stage.parentNode.insertBefore(host,stage);
        stage.remove();
      }
    });
    document.querySelectorAll('.v222-tab-arrow,.v226-tab-arrow').forEach(x=>x.remove());
  }

  function buttonVisible(btn){
    if(!btn||btn.tagName!=='BUTTON')return false;
    if(btn.hidden||btn.classList.contains('hidden')||btn.getAttribute('aria-hidden')==='true')return false;
    if(btn.style?.display==='none')return false;
    return true;
  }

  function styleHost(host){
    host.classList.add('v229-mobile-tabs');
    host.style.setProperty('display','grid','important');
    host.style.setProperty('width','100%','important');
    host.style.setProperty('max-width','100%','important');
    host.style.setProperty('min-width','0','important');

    dedupe(host);
    const tabs=[...host.children].filter(buttonVisible);
    const count=Math.max(1,tabs.length);

    const parentWidth=host.parentElement?.getBoundingClientRect?.().width||0;
    const ownWidth=host.getBoundingClientRect?.().width||0;
    const width=Math.max(280,parentWidth,ownWidth,window.innerWidth-24);
    const gap=count<=6?4:count<=8?3:count<=10?2:1;
    const cell=Math.max(24,(width-4-gap*(count-1))/count);
    const icon=clamp(13,cell*.42,26);
    const font=clamp(5.2,cell*.16,8.6);
    const height=count>=9?62:64;
    const radius=clamp(8,cell*.20,13);

    host.style.setProperty('--v229-count',String(count));
    host.style.setProperty('--v229-gap',gap+'px');
    host.style.setProperty('--v229-icon',icon.toFixed(1)+'px');
    host.style.setProperty('--v229-font',font.toFixed(2)+'px');
    host.style.setProperty('--v229-h',height+'px');
    host.style.setProperty('--v229-radius',radius.toFixed(1)+'px');
    host.style.setProperty('--v229-inner-gap',count>=9?'1px':'2px');

    host.style.setProperty('grid-template-columns','repeat('+count+',minmax(0,1fr))','important');
    host.style.setProperty('grid-template-rows',height+'px','important');
    host.style.setProperty('grid-auto-flow','row','important');
    host.style.setProperty('grid-auto-rows','0','important');
    host.style.setProperty('height',height+'px','important');
    host.style.setProperty('min-height',height+'px','important');
    host.style.setProperty('max-height',height+'px','important');
    host.style.setProperty('overflow','hidden','important');
    host.style.setProperty('column-gap',gap+'px','important');
    host.style.setProperty('row-gap','0','important');
    host.scrollLeft=0;

    tabs.forEach(btn=>{
      decorate(btn);
      btn.style.setProperty('grid-row','1','important');
      btn.style.setProperty('width','100%','important');
      btn.style.setProperty('min-width','0','important');
      btn.style.setProperty('max-width','100%','important');
      btn.style.setProperty('height',height+'px','important');
      btn.style.setProperty('min-height',height+'px','important');
      btn.style.setProperty('max-height',height+'px','important');
      btn.style.setProperty('margin','0','important');
      btn.style.setProperty('transform','none','important');
      btn.style.setProperty('overflow','hidden','important');
    });
  }

  function syncHero(){
    const m=moduleName();
    const title=document.querySelector('#heroTitle');
    const sub=document.querySelector('#heroSub');
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
      unwrapLegacy();
      const activeId=activeHostId();
      IDS.forEach(id=>{
        const host=document.getElementById(id);
        if(!host)return;
        if(id!==activeId){
          host.style.setProperty('display','none','important');
          return;
        }
        host.classList.remove('hidden');
        host.removeAttribute('hidden');
        host.style.removeProperty('display');
        styleHost(host);
      });
      syncHero();
    });
  }

  const observer=new MutationObserver(mutations=>{
    if(!mobile())return;
    if(mutations.some(m=>m.type==='childList'||(m.type==='attributes'&&['class','hidden','aria-hidden'].includes(m.attributeName)))){
      setTimeout(apply,0);
    }
  });

  function init(){
    if(!mobile())return;
    if(!document.body.dataset.v229Observer){
      document.body.dataset.v229Observer='1';
      observer.observe(document.body,{
        subtree:true,
        childList:true,
        attributes:true,
        attributeFilter:['class','hidden','aria-hidden']
      });
    }
    apply();
    [60,180,450,900,1800,3200].forEach(ms=>setTimeout(apply,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button,#v200OperationTabs>button')){
      [0,50,140,320].forEach(ms=>setTimeout(apply,ms));
    }
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(apply,30));
  window.addEventListener('resize',()=>setTimeout(apply,70),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(apply,150),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,70),{passive:true});

  console.info('[V229] navegación móvil única, una fila y sin duplicados.');
})();
</script>'''

    @m.app.middleware("http")
    async def v229_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v229-mobile-tabs-final-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v229-mobile-tabs-final-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V229",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V229] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V229_MOBILE_TABS_FINAL = True
    print("[V229] navegación móvil final instalada.", flush=True)
