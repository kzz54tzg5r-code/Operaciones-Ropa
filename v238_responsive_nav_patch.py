"""V238.1 · Navegación responsive unificada para PC, tablet, iOS y Android.

Objetivo:
- hacer visibles las pestañas del módulo activo también en escritorio;
- neutralizar wrappers/flechas V222 que podían ocultar la barra en PC;
- usar una sola fila sin scroll horizontal en móvil/tablet;
- permitir scroll vertical con un dedo en Android;
- adaptar icono, texto y altura al ancho real disponible.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V238_RESPONSIVE_NAV", False):
        return

    css = r'''<style id="v238-responsive-nav-css">
/* V222 puede seguir creando el wrapper en PC, pero ya no controla visibilidad. */
body .v222-tab-stage,
body .v222-tab-stage.v222-stage-hidden,
body .v226-tab-shell{
  display:contents!important;
}
body .v222-tab-arrow,
body .v226-tab-arrow,
body .rt-carousel-arrow{
  display:none!important;
}

/* Sólo se muestra la barra del módulo activo. */
body.v238-module-operativo #analysisNav,
body.v238-module-operativo #v200OperationTabs,
body.v238-module-analysis #operativoNav,
body.v238-module-analysis #v200OperationTabs,
body.v238-module-operation #operativoNav,
body.v238-module-operation #analysisNav,
body.v238-module-users :is(#operativoNav,#analysisNav,#v200OperationTabs),
body.v238-module-share :is(#operativoNav,#analysisNav,#v200OperationTabs){
  display:none!important;
}

body.v238-module-operativo #operativoNav:not(.hidden),
body.v238-module-analysis #analysisNav:not(.hidden),
body.v238-module-operation #v200OperationTabs:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(var(--v238-count,5),minmax(0,1fr))!important;
  grid-template-rows:var(--v238-h,60px)!important;
  grid-auto-flow:row!important;
  grid-auto-rows:0!important;
  align-items:stretch!important;
  justify-items:stretch!important;
  column-gap:var(--v238-gap,4px)!important;
  row-gap:0!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  height:var(--v238-h,60px)!important;
  min-height:var(--v238-h,60px)!important;
  max-height:var(--v238-h,60px)!important;
  margin:6px 0 10px!important;
  padding:0 2px!important;
  border:0!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
  overflow:hidden!important;
  overflow-x:hidden!important;
  overflow-y:hidden!important;
  white-space:normal!important;
  touch-action:pan-y!important;
  overscroll-behavior-x:none!important;
  scroll-snap-type:none!important;
  scrollbar-width:none!important;
  box-sizing:border-box!important;
}
body.v238-module-operativo #operativoNav::-webkit-scrollbar,
body.v238-module-analysis #analysisNav::-webkit-scrollbar,
body.v238-module-operation #v200OperationTabs::-webkit-scrollbar{display:none!important}

body.v238-module-operativo #operativoNav>button,
body.v238-module-analysis #analysisNav>button,
body.v238-module-operation #v200OperationTabs>button{
  position:relative!important;
  inset:auto!important;
  float:none!important;
  display:flex!important;
  flex:none!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:var(--v238-inner-gap,3px)!important;
  grid-row:1!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:var(--v238-h,60px)!important;
  min-height:var(--v238-h,60px)!important;
  max-height:var(--v238-h,60px)!important;
  margin:0!important;
  padding:var(--v238-pad-y,5px) 2px!important;
  overflow:hidden!important;
  white-space:normal!important;
  text-align:center!important;
  box-sizing:border-box!important;
  border:1px solid #d5e2ef!important;
  border-radius:var(--v238-radius,11px)!important;
  background:#fff!important;
  color:#466887!important;
  opacity:1!important;
  box-shadow:0 3px 10px rgba(25,72,118,.055)!important;
  transform:none!important;
  touch-action:manipulation!important;
}
body.v238-module-operativo #operativoNav>button.active,
body.v238-module-operativo #operativoNav>button[aria-selected="true"],
body.v238-module-analysis #analysisNav>button.active,
body.v238-module-analysis #analysisNav>button[aria-selected="true"],
body.v238-module-operation #v200OperationTabs>button.active,
body.v238-module-operation #v200OperationTabs>button[aria-selected="true"]{
  color:#fff!important;
  border-color:#0a5da7!important;
  background:linear-gradient(145deg,#0d4f8b 0%,#0878df 100%)!important;
  box-shadow:0 7px 17px rgba(13,79,139,.19)!important;
}

:is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-icon,
:is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-icon{
  display:grid!important;
  place-items:center!important;
  flex:0 0 var(--v238-icon,18px)!important;
  width:var(--v238-icon,18px)!important;
  min-width:var(--v238-icon,18px)!important;
  max-width:var(--v238-icon,18px)!important;
  height:var(--v238-icon,18px)!important;
  min-height:var(--v238-icon,18px)!important;
  max-height:var(--v238-icon,18px)!important;
  margin:0!important;
  padding:0!important;
  color:currentColor!important;
}
:is(#operativoNav,#analysisNav,#v200OperationTabs) :is(.v238-tab-icon,.v232-tab-icon) svg{
  display:block!important;
  width:100%!important;
  height:100%!important;
  max-width:100%!important;
  max-height:100%!important;
  stroke:currentColor!important;
}

:is(#operativoNav,#analysisNav,#v200OperationTabs) .v238-tab-label,
:is(#operativoNav,#analysisNav,#v200OperationTabs) .v232-tab-label{
  position:static!important;
  inset:auto!important;
  transform:none!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  width:100%!important;
  min-width:0!important;
  height:var(--v238-label-h,26px)!important;
  min-height:var(--v238-label-h,26px)!important;
  max-height:var(--v238-label-h,26px)!important;
  margin:0!important;
  padding:0!important;
  overflow:hidden!important;
  white-space:pre-line!important;
  overflow-wrap:normal!important;
  word-break:normal!important;
  hyphens:none!important;
  text-overflow:clip!important;
  text-align:center!important;
  font-size:var(--v238-font,8px)!important;
  line-height:1.05!important;
  font-weight:900!important;
  letter-spacing:0!important;
}

/* Teléfono: todas visibles, compactas y sin capturar el gesto vertical. */
@media(max-width:600px){
  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    margin:5px 0 9px!important;
    padding:0 2px!important;
    column-gap:2px!important;
    touch-action:pan-y!important;
  }
}

/* Tablet: misma navegación, algo más aire y letra. Incluye iPad 1024px. */
@media(min-width:601px) and (max-width:1024px){
  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    margin:7px 0 11px!important;
    padding:0 3px!important;
    column-gap:4px!important;
    touch-action:pan-y!important;
  }
}

/* PC: sin wrapper oculto ni carrusel; todas las pestañas visibles. */
@media(min-width:1025px){
  body.v238-module-operativo #operativoNav:not(.hidden),
  body.v238-module-analysis #analysisNav:not(.hidden),
  body.v238-module-operation #v200OperationTabs:not(.hidden){
    margin:8px 0 12px!important;
    padding:0!important;
    column-gap:6px!important;
    overflow:visible!important;
  }
}
</style>'''

    js = r'''<script id="v238-responsive-nav-js">
(function(){
  if(window.__V238_RESPONSIVE_NAV)return;
  window.__V238_RESPONSIVE_NAV=true;

  const IDS=['operativoNav','analysisNav','v200OperationTabs'];
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const clamp=(a,v,b)=>Math.max(a,Math.min(v,b));
  let applying=false,raf=0;

  const PATHS={
    dashboard:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    gear:'<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6.2L14.7 4h-4l-.3 2.2a8 8 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 1.5.9l.3 2.2h4l.3-2.2a8 8 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/>',
    repeat:'<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    dollar:'<path d="M12 3v18M16 7.5c-.9-.8-2.1-1.2-3.5-1.2-2.2 0-3.7 1-3.7 2.6 0 3.6 7.3 1.8 7.3 5.5 0 1.7-1.6 2.8-3.8 2.8-1.6 0-3-.5-4.1-1.5"/>',
    store:'<path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/>',
    chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    truck:'<path d="M3 6h11v10H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    route:'<path d="M5 19c3-6 11-5 14-12"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="7" r="2"/>',
    database:'<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    accordion:'<rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="4" rx="1.5"/><rect x="3" y="17" width="18" height="3" rx="1.5"/>',
    building:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h2M14 7h2M8 11h2M14 11h2M8 15h2M14 15h2M9 21v-3h6v3"/>',
    checklist:'<path d="M9 5h10M9 12h10M9 19h10"/><path d="m3 5 1.2 1.2L6.5 4M3 12l1.2 1.2L6.5 11M3 19l1.2 1.2L6.5 18"/>',
    percent:'<path d="m19 5-14 14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>'
  };
  const svg=name=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(PATHS[name]||PATHS.chart)+'</svg>';

  function currentModule(){
    let m='';
    try{m=String(MAIN||'').toLowerCase();}catch(_e){}
    if(m==='commercial')m='analysis';
    if(['operativo','analysis','operation','users','share'].includes(m))return m;
    const active=q('.side [data-main].active')||q('#mobileMainNav [data-main].active')||q('[data-main].active');
    m=String(active&&active.dataset&&active.dataset.main||'').toLowerCase();
    if(m==='commercial')m='analysis';
    if(['operativo','analysis','operation','users','share'].includes(m))return m;
    m=String(document.body.dataset.v163Module||'').toLowerCase();
    if(m==='commercial')m='analysis';
    return ['operativo','analysis','operation','users','share'].includes(m)?m:'';
  }

  function setModule(mod){
    ['operativo','analysis','operation','users','share'].forEach(x=>document.body.classList.toggle('v238-module-'+x,mod===x));
    if(mod)document.body.dataset.v163Module=mod;
  }

  function activeHostId(mod){
    if(mod==='operativo')return'operativoNav';
    if(mod==='analysis')return'analysisNav';
    if(mod==='operation')return'v200OperationTabs';
    return'';
  }

  function buttonVisible(btn){
    if(!btn||btn.tagName!=='BUTTON')return false;
    if(btn.hidden||btn.classList.contains('hidden')||btn.getAttribute('aria-hidden')==='true')return false;
    const s=getComputedStyle(btn);
    return s.display!=='none'&&s.visibility!=='hidden'&&s.opacity!=='0';
  }

  function original(btn){
    return String(btn.dataset.v232Original||btn.dataset.rtLabel||btn.dataset.v203Label||btn.title||btn.textContent||'Reporte').replace(/\s+/g,' ').trim();
  }

  function meta(btn,kind,cell){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview);
    const sub=norm(btn.dataset.sub);
    const raw=original(btn),t=norm(raw);
    const phone=window.innerWidth<=600;
    const tiny=cell<52;

    if(kind==='operativo'){
      if(key==='operations.center'||t.includes('centro operativo')||t.includes('centro ejecutivo'))return['Centro Operativo',phone?'Centro\nOperat.':'Centro\nOperativo','dashboard'];
      if(t==='operacion'||t.startsWith('operacion '))return['Operación','Operación','gear'];
      if(key==='operations.conversion'||op.includes('convers')||t.includes('conversion'))return['Conversión','Conversión','repeat'];
      if(key==='operations.recovery'||op.includes('recuperacion economica')||t.includes('recuperacion $')||t.includes('recuperaciones'))return['Recuperación $',phone?'Recup.\n$':'Recuperación\n$','dollar'];
      if(key==='operations.recovery_store'||op.includes('recuperacion por tienda')||t.includes('tasa de recuperacion')||t.includes('recuperacion por tienda'))return['Tasa de recuperación',phone?'Tasa\nrecup.':'Tasa de\nrecuperación','store'];
      if(t.includes('cargar productividad'))return['Cargar productividad',phone?'Cargar\nProd.':'Cargar\nProductividad','truck'];
      if(key==='operations.productivity'||op.includes('productividad')||t==='productividad')return['Productividad',phone?'Productiv.':'Productividad','chart'];
      if(key==='operations.routes'||op.includes('recorridos')||t.includes('recorridos'))return['Recorridos',phone&&tiny?'Recorrid.':'Recorridos','route'];
      if(key==='operations.score'||op.includes('indice integral')||t==='score')return['Score','Score','chart'];
      if(key==='operations.alerts'||op.includes('alertas')||t.includes('alertas'))return['Alertas','Alertas','target'];
      if(op.includes('carga de datos')||t.includes('carga de datos'))return['Carga de datos','Carga de\ndatos','database'];
      if(btn.id==='openGoalsBtn'||t.includes('metas y tiendas')||t==='metas')return['Metas y tiendas','Metas y\ntiendas','target'];
    }

    if(kind==='analysis'){
      if(key==='commercial.macro'||sub==='macro'||t.includes('macro compania'))return['Macro compañía','Macro\ncompañía','dashboard'];
      if(key==='commercial.accordion'||sub==='accordion'||t.includes('acordeon comercial'))return['Acordeón comercial','Acordeón\ncomercial','accordion'];
      if(key==='commercial.stores'||sub==='stores'||t==='tiendas')return['Tiendas','Tiendas','building'];
      if(key==='commercial.lingerie_checklist'||sub==='lingerie-checklist'||t.includes('checklist lenceria'))return['Checklist lencería','Checklist\nlencería','checklist'];
      if(key==='commercial.sellthrough'||sub.includes('sell')||t.includes('sell through'))return['Sell Through','Sell Through','percent'];
      if(key==='commercial.upload'||sub==='analysis-upload'||t.includes('carga de datos'))return['Carga de datos','Carga de\ndatos','database'];
    }

    if(kind==='operation'){
      const opKey=String(btn.dataset.v200Op||'').toLowerCase();
      if(opKey==='summary'||t.includes('resumen'))return['Resumen','Resumen','dashboard'];
      if(opKey==='daily'||t.includes('captura diaria'))return['Captura diaria','Captura\ndiaria','dashboard'];
      if(opKey==='capture'||t.includes('cargar productividad'))return['Cargar productividad','Cargar\nProductividad','truck'];
      if(opKey==='productivity'||t==='productividad')return['Productividad','Productividad','chart'];
      if(opKey==='standards'||t.includes('estandares'))return['Estándares Operativos','Estándares\nOperativos','target'];
      if(t.includes('diaria')||t.includes('operacion'))return[raw,raw,'gear'];
    }
    return[raw,raw,'chart'];
  }

  function decorateLarge(host,btn,kind,cell){
    if(window.innerWidth<=900)return;
    const [full,shortLabel,icon]=meta(btn,kind,cell);
    const shown=cell<92?shortLabel:full;
    const iconClass=host.id==='v200OperationTabs'?'v203-tab-icon':'rt-tab-icon';
    const labelClass=host.id==='v200OperationTabs'?'v203-tab-label':'rt-tab-label';
    let ico=q(':scope>.v238-tab-icon',btn),lab=q(':scope>.v238-tab-label',btn);
    if(!ico||!lab){
      btn.querySelectorAll(':scope>.or-tab-icon,:scope>.rt-tab-icon,:scope>.v203-tab-icon,:scope>.v238-tab-icon,:scope>.rt-tab-label,:scope>.v203-tab-label,:scope>.v238-tab-label,:scope>svg').forEach(x=>x.remove());
      btn.innerHTML='<span class="'+iconClass+' v238-tab-icon">'+svg(icon)+'</span><span class="'+labelClass+' v238-tab-label"></span>';
      ico=q(':scope>.v238-tab-icon',btn);
      lab=q(':scope>.v238-tab-label',btn);
    }
    if(lab&&lab.textContent!==shown)lab.textContent=shown;
    btn.dataset.rtLabel=full;
    btn.title=full;
  }

  function relabelMobile(host,btn,kind,cell){
    const lab=q(':scope>.v232-tab-label',btn);
    if(!lab)return;
    const [,shortLabel]=meta(btn,kind,cell);
    if(lab.textContent!==shortLabel)lab.textContent=shortLabel;
  }

  function sizeHost(host,kind){
    const tabs=Array.from(host.children).filter(buttonVisible);
    const count=Math.max(1,tabs.length);
    // V247: medir el espacio REAL de contenido. Usar window.innerWidth hacía
    // que la barra fuera más ancha que .main cuando existía sidebar y cortaba
    // las últimas pestañas.
    const main=host.closest('.main');
    const parent=host.parentElement;
    const measured=Number(main?.clientWidth||parent?.clientWidth||host.clientWidth||0);
    const width=Math.max(280,measured||Math.max(280,window.innerWidth-24));
    const gap=window.innerWidth<=600?2:window.innerWidth<=1024?4:6;
    const cell=Math.max(24,(width-gap*(count-1)-4)/count);

    let h,icon,font,labelH,radius,innerGap,padY;
    if(window.innerWidth<=430){
      h=kind==='operativo'?58:64;
      icon=kind==='operativo'?14:19;
      font=kind==='operativo'?clamp(5.4,cell*.15,6.15):clamp(6.8,cell*.14,7.7);
      labelH=kind==='operativo'?28:29;radius=10;innerGap=2;padY=4;
    }else if(window.innerWidth<=600){
      h=kind==='operativo'?62:68;
      icon=kind==='operativo'?16:20;
      font=kind==='operativo'?clamp(6.2,cell*.14,7.0):clamp(7.3,cell*.13,8.2);
      labelH=30;radius=11;innerGap=3;padY=5;
    }else if(window.innerWidth<=1024){
      h=kind==='operativo'?70:72;
      icon=kind==='operativo'?19:22;
      font=kind==='operativo'?clamp(7.2,cell*.115,8.7):clamp(8.2,cell*.105,9.8);
      labelH=32;radius=12;innerGap=4;padY=5;
    }else{
      h=62;
      icon=22;
      font=clamp(9.0,cell*.105,11.2);
      labelH=27;radius=12;innerGap=4;padY=6;
    }

    host.style.setProperty('--v238-count',String(count));
    host.style.setProperty('--v238-gap',gap+'px');
    host.style.setProperty('--v238-h',h+'px');
    host.style.setProperty('--v238-icon',icon+'px');
    host.style.setProperty('--v238-font',font.toFixed(2)+'px');
    host.style.setProperty('--v238-label-h',labelH+'px');
    host.style.setProperty('--v238-radius',radius+'px');
    host.style.setProperty('--v238-inner-gap',innerGap+'px');
    host.style.setProperty('--v238-pad-y',padY+'px');
    host.style.setProperty('display','grid','important');
    host.style.setProperty('width','100%','important');
    host.style.setProperty('max-width','100%','important');
    host.style.setProperty('box-sizing','border-box','important');
    host.style.setProperty('grid-template-columns','repeat('+count+',minmax(0,1fr))','important');
    host.style.setProperty('grid-template-rows',h+'px','important');
    host.style.setProperty('height',h+'px','important');
    host.style.setProperty('min-height',h+'px','important');
    host.style.setProperty('max-height',h+'px','important');
    host.style.setProperty('overflow','hidden','important');
    host.style.setProperty('touch-action','pan-y','important');
    host.scrollLeft=0;

    tabs.forEach(btn=>{
      if(window.innerWidth<=900)relabelMobile(host,btn,kind,cell);
      else decorateLarge(host,btn,kind,cell);
      btn.style.setProperty('display','flex','important');
      btn.style.setProperty('width','100%','important');
      btn.style.setProperty('min-width','0','important');
      btn.style.setProperty('max-width','100%','important');
      btn.style.setProperty('height',h+'px','important');
      btn.style.setProperty('min-height',h+'px','important');
      btn.style.setProperty('max-height',h+'px','important');
      btn.style.setProperty('overflow','hidden','important');
      btn.style.setProperty('touch-action','manipulation','important');
    });
  }

  function apply(){
    if(applying)return;
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      applying=true;
      try{
        const mod=currentModule();
        setModule(mod);
        const active=activeHostId(mod);
        IDS.forEach(id=>{
          const host=document.getElementById(id);
          if(!host)return;
          if(id!==active){
            host.style.setProperty('display','none','important');
            return;
          }
          host.classList.remove('hidden');
          host.removeAttribute('hidden');
          host.style.removeProperty('display');
          sizeHost(host,mod);
        });
      }finally{applying=false;}
    });
  }

  const observer=new MutationObserver(muts=>{
    if(applying)return;
    if(muts.some(m=>m.type==='childList'||(m.type==='attributes'&&['class','hidden','aria-hidden','data-main'].includes(m.attributeName))))setTimeout(apply,0);
  });

  function init(){
    if(!document.body.dataset.v238Observer){
      document.body.dataset.v238Observer='1';
      observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-hidden','data-main']});
    }
    apply();
    [80,220,600,1200,2500].forEach(ms=>setTimeout(apply,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('click',e=>{
    if(e.target.closest&&e.target.closest('[data-main],#operativoNav>button,#analysisNav>button,#v200OperationTabs>button')){
      [0,50,140,320].forEach(ms=>setTimeout(apply,ms));
    }
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(apply,30));
  window.addEventListener('resize',()=>setTimeout(apply,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(apply,160),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});

  console.info('[V247] navegación responsive ajustada al ancho real; todas las pestañas visibles.');
})();
</script>'''

    @m.app.middleware("http")
    async def v238_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v238-responsive-nav-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v238-responsive-nav-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V238-RESPONSIVE-NAV",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V238] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V238_RESPONSIVE_NAV = True
    print("[V238] navegación responsive PC/tablet/iOS/Android instalada.", flush=True)
