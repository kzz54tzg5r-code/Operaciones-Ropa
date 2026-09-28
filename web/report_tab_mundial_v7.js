(() => {
  'use strict';

  const STYLE_ID = 'rt-mundial-v7-style';
  const BOUND = new WeakMap();

  const KEY_LABELS = {
    'operations.center':'Centro Ejecutivo',
    'operations.day':'Día',
    'operations.week':'Semanal',
    'operations.month':'Mensual',
    'operations.conversion':'Conversión',
    'operations.recovery':'Recuperación $',
    'operations.recovery_store':'Recuperación por Tienda',
    'operations.productivity':'Productividad',
    'operations.routes':'Recorridos',
    'operations.score':'Score',
    'operations.alerts':'Alertas',
    'commercial.macro':'Macro Compañía',
    'commercial.accordion':'Acordeón Comercial',
    'commercial.stores':'Tiendas',
    'commercial.sections':'Sección / Rubro',
    'commercial.areas':'Ubicación / Área',
    'commercial.lingerie_checklist':'Checklist Lencería',
    'commercial.sellthrough':'Sell Through',
    'commercial.more':'Más opciones'
  };

  const OPVIEW_LABELS = {
    'Centro Operativo':'Centro Ejecutivo',
    'Operación Diaria':'Día',
    'Reporte Semanal':'Semanal',
    'Reporte Mensual':'Mensual',
    'Conversión':'Conversión',
    'Recuperación $':'Recuperación $',
    'Recuperación por Tienda':'Recuperación por Tienda',
    'Productividad':'Productividad',
    'Recorridos':'Recorridos',
    'Score':'Score',
    'Alertas':'Alertas',
    'Carga de datos':'Carga de datos'
  };

  const V125_LABELS = {
    daily:'Captura diaria',
    capture:'Cargar productividad',
    productivity:'Productividad',
    standards:'Estándares'
  };

  const css = `
    /*
     * Mundial V7 · ajuste por proporciones del video de referencia (512 px):
     * - cara central ~196×131 px;
     * - ficha adyacente apenas asoma ~55–70 px;
     * - escala lateral ~56%;
     * - nombre activo separado debajo.
     */

    .rt-carousel-shell.rt-mundial-v7{
      --rt-card-w:220px!important;
      --rt-gap:24px!important;
      position:relative!important;
      width:100%!important;
      max-width:100%!important;
      min-height:218px!important;
      margin:0 0 6px!important;
      padding:0!important;
      overflow:visible!important;
      isolation:isolate!important;
    }

    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel{
      position:relative!important;
      z-index:2!important;
      display:flex!important;
      grid-template-columns:none!important;
      flex-wrap:nowrap!important;
      align-items:flex-start!important;
      width:100%!important;
      max-width:100%!important;
      height:184px!important;
      min-height:184px!important;
      margin:0!important;
      padding:9px var(--rt-edge-pad) 16px!important;
      gap:var(--rt-gap)!important;
      overflow-x:auto!important;
      overflow-y:visible!important;
      scroll-snap-type:x mandatory!important;
      scroll-padding-inline:var(--rt-edge-pad)!important;
      scroll-behavior:smooth!important;
      background:transparent!important;
      border:0!important;
      border-radius:0!important;
      box-shadow:none!important;
      scrollbar-width:none!important;
      -webkit-overflow-scrolling:touch!important;
    }

    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel::-webkit-scrollbar{
      display:none!important;
    }

    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .switch,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .v125-tab,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel>button{
      --rt-m7-scale:.56;
      --rt-m7-y:30px;
      --rt-m7-opacity:.94;
      --rt-m7-base-opacity:.86;
      --rt-m7-z:1;

      position:relative!important;
      isolation:isolate!important;
      flex:0 0 var(--rt-card-w)!important;
      width:var(--rt-card-w)!important;
      min-width:var(--rt-card-w)!important;
      max-width:var(--rt-card-w)!important;
      height:164px!important;
      min-height:164px!important;
      max-height:164px!important;
      margin:0!important;
      padding:0!important;
      display:block!important;
      border:0!important;
      border-radius:0!important;
      background:transparent!important;
      color:#0b4d8c!important;
      box-shadow:none!important;
      opacity:var(--rt-m7-opacity)!important;
      transform:translateY(var(--rt-m7-y)) scale(var(--rt-m7-scale))!important;
      transform-origin:center top!important;
      transition:transform .075s linear,opacity .075s linear!important;
      will-change:transform,opacity!important;
      overflow:visible!important;
      white-space:normal!important;
      scroll-snap-align:center!important;
      scroll-snap-stop:always!important;
      z-index:var(--rt-m7-z)!important;
      cursor:pointer!important;
      -webkit-tap-highlight-color:transparent!important;
    }

    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .switch.active,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .v125-tab.active,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel>button.active,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel [aria-selected="true"]{
      border:0!important;
      background:transparent!important;
      color:#0b4d8c!important;
      box-shadow:none!important;
    }

    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .switch::after,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .v125-tab::after,
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel>button::after{
      display:none!important;
      content:none!important;
    }

    /* Base azul individual de cada ficha, equivalente a la placa bajo la bandera. */
    .rt-m7-base{
      position:absolute!important;
      left:50%!important;
      top:55px!important;
      z-index:1!important;
      width:230px!important;
      height:107px!important;
      transform:translateX(-50%)!important;
      border-radius:46px 46px 10px 10px!important;
      background:
        linear-gradient(145deg,
          rgba(7,58,112,var(--rt-m7-base-opacity)),
          rgba(13,127,244,var(--rt-m7-base-opacity)))!important;
      box-shadow:0 12px 26px rgba(8,58,108,.16)!important;
      pointer-events:none!important;
    }

    .rt-m7-base::before,
    .rt-m7-base::after{
      content:""!important;
      position:absolute!important;
      bottom:0!important;
      width:58px!important;
      height:77px!important;
      background:inherit!important;
      border-radius:38px 38px 9px 9px!important;
      pointer-events:none!important;
    }
    .rt-m7-base::before{left:-30px!important}
    .rt-m7-base::after{right:-30px!important}

    /* Cara blanca central. En la referencia mide ~196×131 px. */
    .rt-m7-face{
      position:absolute!important;
      left:50%!important;
      top:0!important;
      z-index:3!important;
      width:196px!important;
      height:131px!important;
      transform:translateX(-50%)!important;
      display:grid!important;
      place-items:center!important;
      border:2px solid #d7e3ef!important;
      border-radius:13px!important;
      background:linear-gradient(160deg,#ffffff 0%,#f8fbff 100%)!important;
      box-shadow:
        0 8px 20px rgba(11,55,98,.13),
        inset 0 1px 0 rgba(255,255,255,.96)!important;
      pointer-events:none!important;
    }

    .rt-m-nearest .rt-m7-face{
      border-color:#ffffff!important;
      box-shadow:
        0 12px 26px rgba(8,52,98,.20),
        0 0 0 2px rgba(13,127,244,.16)!important;
    }

    /* Fuerza los SVG a verse; V4/V194 ocultaban svg dentro de #operativoNav. */
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .rt-m7-face .rt-tab-icon{
      display:grid!important;
      place-items:center!important;
      width:60px!important;
      height:60px!important;
      min-width:60px!important;
      max-width:60px!important;
      margin:0!important;
      padding:0!important;
      color:#0d6fc8!important;
      opacity:1!important;
      visibility:visible!important;
      transform:none!important;
      pointer-events:none!important;
    }

    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .rt-m7-face .rt-tab-icon svg{
      display:block!important;
      width:60px!important;
      height:60px!important;
      min-width:60px!important;
      max-width:60px!important;
      opacity:1!important;
      visibility:visible!important;
      stroke:currentColor!important;
      fill:none!important;
      stroke-width:1.65!important;
    }

    /* El texto interno se conserva para accesibilidad/datos, pero no se pinta. */
    .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .rt-tab-label{
      position:absolute!important;
      width:1px!important;
      height:1px!important;
      padding:0!important;
      margin:-1px!important;
      overflow:hidden!important;
      clip:rect(0,0,0,0)!important;
      clip-path:inset(50%)!important;
      white-space:nowrap!important;
      border:0!important;
      opacity:0!important;
      pointer-events:none!important;
    }

    /* Nombre activo separado debajo, como en el Mundial. */
    .rt-m7-current{
      position:relative!important;
      z-index:6!important;
      display:flex!important;
      align-items:center!important;
      justify-content:center!important;
      width:100%!important;
      min-height:34px!important;
      margin:-8px 0 0!important;
      padding:0 16px 3px!important;
      color:#0b3a6e!important;
      text-align:center!important;
      pointer-events:none!important;
    }

    .rt-m7-current-label{
      display:block!important;
      max-width:min(82vw,430px)!important;
      color:#0b3a6e!important;
      font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;
      font-size:17px!important;
      line-height:1.1!important;
      font-weight:900!important;
      letter-spacing:-.025em!important;
      opacity:1!important;
      visibility:visible!important;
      white-space:normal!important;
      text-shadow:none!important;
    }

    .rt-m7-current::before,
    .rt-m7-current::after{
      content:""!important;
      display:block!important;
      width:13px!important;
      height:18px!important;
      margin:0 9px!important;
      opacity:.22!important;
      border-left:2px solid #0d72d4!important;
      border-radius:50%!important;
      transform:rotate(-22deg)!important;
    }
    .rt-m7-current::after{
      transform:scaleX(-1) rotate(-22deg)!important;
    }

    .rt-carousel-shell.rt-mundial-v7 .rt-carousel-arrow{
      top:88px!important;
    }

    @media(max-width:900px){
      .rt-carousel-shell.rt-mundial-v7{
        --rt-card-w:220px!important;
        --rt-gap:24px!important;
        min-height:214px!important;
      }

      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel{
        height:181px!important;
        min-height:181px!important;
        padding-top:7px!important;
        padding-bottom:14px!important;
      }

      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .switch,
      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .v125-tab,
      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel>button{
        height:162px!important;
        min-height:162px!important;
        max-height:162px!important;
      }

      .rt-m7-current{
        margin-top:-7px!important;
        min-height:32px!important;
      }
      .rt-m7-current-label{font-size:16px!important}

      .rt-carousel-shell.rt-mundial-v7 .rt-carousel-arrow{
        display:none!important;
      }
    }

    @media(min-width:901px){
      .rt-carousel-shell.rt-mundial-v7{
        --rt-card-w:200px!important;
        --rt-gap:16px!important;
      }

      .rt-m7-face{
        width:178px!important;
        height:119px!important;
      }

      .rt-m7-base{
        width:208px!important;
        height:98px!important;
        top:50px!important;
      }

      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .rt-m7-face .rt-tab-icon,
      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .rt-m7-face .rt-tab-icon svg{
        width:52px!important;
        height:52px!important;
        min-width:52px!important;
        max-width:52px!important;
      }
    }

    @media(prefers-reduced-motion:reduce){
      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .switch,
      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel .v125-tab,
      .rt-carousel-shell.rt-mundial-v7 :is(#operativoNav,#analysisNav,.v125-tabs).rt-carousel>button{
        transition:none!important;
      }
    }
  `;

  function installStyle(){
    if(document.getElementById(STYLE_ID)) return;
    const style=document.createElement('style');
    style.id=STYLE_ID;
    style.textContent=css;
    document.head.appendChild(style);
  }

  function cards(viewport){
    return [...viewport.children].filter(el =>
      el instanceof HTMLButtonElement &&
      !el.hidden &&
      !el.classList.contains('hidden') &&
      getComputedStyle(el).display!=='none'
    );
  }

  function labelOf(btn){
    return (
      btn.dataset.rtLabel ||
      KEY_LABELS[btn.dataset.tabKey] ||
      V125_LABELS[btn.dataset.v125Tab] ||
      OPVIEW_LABELS[btn.dataset.opview] ||
      btn.dataset.rtOriginalLabel ||
      btn.getAttribute('aria-label') ||
      (btn.id==='openGoalsBtn' ? 'Metas y tiendas' : '') ||
      'Pestaña'
    ).trim();
  }

  function cleanupOldCard(btn){
    const oldFace=btn.querySelector(':scope > .rt-mundial-face');
    if(oldFace){
      const icon=oldFace.querySelector('.rt-tab-icon');
      if(icon) btn.insertBefore(icon,oldFace);
      oldFace.remove();
    }
    btn.querySelector(':scope > .rt-mundial-base')?.remove();
  }

  function buildCard(btn){
    cleanupOldCard(btn);

    if(btn.dataset.rtMundialV7==='1'){
      const face=btn.querySelector(':scope > .rt-m7-face');
      const icon=btn.querySelector('.rt-tab-icon');
      if(face && icon && icon.parentElement!==face) face.appendChild(icon);
      return;
    }

    const icon=btn.querySelector('.rt-tab-icon');
    const label=btn.querySelector('.rt-tab-label');
    if(!icon||!label) return;

    const base=document.createElement('span');
    base.className='rt-m7-base';
    base.setAttribute('aria-hidden','true');

    const face=document.createElement('span');
    face.className='rt-m7-face';
    face.setAttribute('aria-hidden','true');
    face.appendChild(icon);

    btn.insertBefore(base,btn.firstChild);
    btn.insertBefore(face,label);

    btn.dataset.rtMundialV7='1';
    btn.setAttribute('aria-label',labelOf(btn));
  }

  function centerPadding(viewport){
    const list=cards(viewport);
    if(!list.length||!viewport.clientWidth) return;
    const edge=Math.max(10,(viewport.clientWidth-list[0].offsetWidth)/2);
    viewport.style.setProperty('--rt-edge-pad',edge+'px');
  }

  function setCurrentLabel(state,btn){
    if(!state.currentLabel||!btn) return;
    const text=labelOf(btn);
    if(state.currentLabel.textContent!==text){
      state.currentLabel.textContent=text;
    }
  }

  function update(viewport){
    const state=BOUND.get(viewport);
    if(!state||!viewport.clientWidth) return;
    state.raf=null;

    const list=cards(viewport);
    if(!list.length) return;

    list.forEach(buildCard);
    centerPadding(viewport);

    const vr=viewport.getBoundingClientRect();
    const cx=vr.left + vr.width/2;
    const gap=parseFloat(getComputedStyle(viewport).columnGap||getComputedStyle(viewport).gap||'24')||24;
    const step=Math.max(1,list[0].offsetWidth + gap);

    let nearest=null;
    let nearestDist=Infinity;

    for(const btn of list){
      const r=btn.getBoundingClientRect();
      const cardCenter=r.left + r.width/2;
      const dist=Math.abs(cardCenter-cx);
      const normalized=Math.min(1,dist/step);
      const focus=1-normalized;

      // Pixel-match aproximado al Mundial:
      // centro 100%; lateral ~56%; lateral baja ~30 px.
      const scale=.56 + .44*focus;
      const y=30 - 30*focus;
      const opacity=.94 + .06*focus;
      const baseOpacity=.86 + .14*focus;
      const z=2 + Math.round(focus*30);

      btn.style.setProperty('--rt-m7-scale',scale.toFixed(3));
      btn.style.setProperty('--rt-m7-y',y.toFixed(1)+'px');
      btn.style.setProperty('--rt-m7-opacity',opacity.toFixed(3));
      btn.style.setProperty('--rt-m7-base-opacity',baseOpacity.toFixed(3));
      btn.style.setProperty('--rt-m7-z',String(z));

      btn.classList.toggle('rt-m-nearest',false);

      if(dist<nearestDist){
        nearestDist=dist;
        nearest=btn;
      }
    }

    if(nearest){
      nearest.classList.add('rt-m-nearest');
      setCurrentLabel(state,nearest);
    }
  }

  function schedule(viewport){
    const state=BOUND.get(viewport);
    if(!state||state.raf) return;
    state.raf=requestAnimationFrame(()=>update(viewport));
  }

  function enhance(viewport){
    if(!(viewport instanceof HTMLElement)||!viewport.classList.contains('rt-carousel')) return;

    const existing=BOUND.get(viewport);
    if(existing){
      cards(viewport).forEach(buildCard);
      schedule(viewport);
      return;
    }

    const shell=viewport.closest('.rt-carousel-shell');
    if(!shell) return;

    // Retira cualquier DOM visual heredado de V5/V6.
    shell.classList.remove('rt-mundial-stage','rt-mundial-v6');
    shell.querySelector(':scope > .rt-worldcup-pedestal')?.remove();
    shell.querySelector(':scope > .rt-worldcup-current')?.remove();
    shell.querySelector(':scope > .rt-mundial-current')?.remove();

    shell.classList.add('rt-mundial-v7');

    const current=document.createElement('div');
    current.className='rt-m7-current';
    current.setAttribute('aria-live','polite');

    const currentLabel=document.createElement('span');
    currentLabel.className='rt-m7-current-label';
    current.appendChild(currentLabel);
    shell.appendChild(current);

    const state={shell,current,currentLabel,raf:null};
    BOUND.set(viewport,state);

    cards(viewport).forEach(buildCard);
    centerPadding(viewport);

    viewport.addEventListener('scroll',()=>schedule(viewport),{passive:true});
    viewport.addEventListener('touchmove',()=>schedule(viewport),{passive:true});
    viewport.addEventListener('touchend',()=>setTimeout(()=>schedule(viewport),18),{passive:true});
    viewport.addEventListener('click',()=>setTimeout(()=>schedule(viewport),22));

    const mo=new MutationObserver(()=>{
      cards(viewport).forEach(buildCard);
      schedule(viewport);
    });
    mo.observe(viewport,{
      subtree:true,
      childList:true,
      attributes:true,
      attributeFilter:['class','aria-selected','style']
    });
    state.observer=mo;

    schedule(viewport);
    setTimeout(()=>schedule(viewport),80);
    setTimeout(()=>schedule(viewport),240);
  }

  function scan(){
    installStyle();
    document.querySelectorAll('.rt-carousel').forEach(enhance);
  }

  function init(){
    scan();

    const mo=new MutationObserver(()=>{
      clearTimeout(window.__rtMundialV7Scan);
      window.__rtMundialV7Scan=setTimeout(scan,25);
    });
    mo.observe(document.body,{subtree:true,childList:true});

    window.addEventListener('resize',()=>{
      clearTimeout(window.__rtMundialV7Resize);
      window.__rtMundialV7Resize=setTimeout(()=>{
        document.querySelectorAll('.rt-carousel').forEach(viewport=>{
          centerPadding(viewport);
          schedule(viewport);
        });
      },70);
    },{passive:true});

    window.ReportTabMundialV7={
      refresh:scan,
      update:schedule
    };
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',init,{once:true});
  }else{
    init();
  }
})();