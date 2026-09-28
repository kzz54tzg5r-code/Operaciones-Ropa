(() => {
  'use strict';

  const STYLE_ID='rt-icon-rail-v1-style';
  const TARGET_ID='operativoNav';
  const STATE=new WeakMap();

  const css=`
    /* =========================================================
       OPTION 1 · Carrusel de iconos + nombre activo
       Sólo Cambios y Muertos / #operativoNav
       ========================================================= */

    #operativoNav.rt-carousel.rt-icon-rail-v1{
      --rt-card-w:66px!important;
      --rt-gap:10px!important;
      display:flex!important;
      grid-template-columns:none!important;
      flex-wrap:nowrap!important;
      align-items:center!important;
      gap:var(--rt-gap)!important;
      width:100%!important;
      max-width:100%!important;
      min-height:74px!important;
      height:74px!important;
      padding:7px var(--rt-edge-pad) 8px!important;
      margin:0!important;
      overflow-x:auto!important;
      overflow-y:visible!important;
      scroll-snap-type:x mandatory!important;
      scroll-padding-inline:var(--rt-edge-pad)!important;
      background:linear-gradient(180deg,rgba(255,255,255,.78),rgba(247,251,255,.64))!important;
      border:1px solid rgba(199,216,233,.72)!important;
      border-radius:22px!important;
      box-shadow:0 5px 18px rgba(12,53,92,.055)!important;
      scrollbar-width:none!important;
      -webkit-overflow-scrolling:touch!important;
    }
    #operativoNav.rt-carousel.rt-icon-rail-v1::-webkit-scrollbar{display:none!important}

    #operativoNav.rt-carousel.rt-icon-rail-v1>.switch,
    #operativoNav.rt-carousel.rt-icon-rail-v1>button{
      position:relative!important;
      flex:0 0 var(--rt-card-w)!important;
      width:var(--rt-card-w)!important;
      min-width:var(--rt-card-w)!important;
      max-width:var(--rt-card-w)!important;
      height:60px!important;
      min-height:60px!important;
      max-height:60px!important;
      margin:0!important;
      padding:0!important;
      display:grid!important;
      place-items:center!important;
      border:0!important;
      border-radius:0!important;
      background:transparent!important;
      box-shadow:none!important;
      color:#6b7f94!important;
      opacity:.78!important;
      transform:none!important;
      scroll-snap-align:center!important;
      scroll-snap-stop:always!important;
      white-space:nowrap!important;
      overflow:visible!important;
      transition:opacity .16s ease,color .16s ease,transform .16s ease!important;
      -webkit-tap-highlight-color:transparent!important;
    }

    #operativoNav.rt-carousel.rt-icon-rail-v1>.switch::after,
    #operativoNav.rt-carousel.rt-icon-rail-v1>button::after{
      display:none!important;
      content:none!important;
    }

    /* círculo visual */
    #operativoNav.rt-carousel.rt-icon-rail-v1 .rt-tab-icon{
      display:grid!important;
      place-items:center!important;
      width:44px!important;
      height:44px!important;
      min-width:44px!important;
      max-width:44px!important;
      margin:0!important;
      padding:0!important;
      border:1px solid #d9e4ef!important;
      border-radius:50%!important;
      background:#fff!important;
      color:#4f6f90!important;
      opacity:1!important;
      visibility:visible!important;
      box-shadow:0 3px 10px rgba(14,52,89,.055)!important;
      transform:scale(1)!important;
      transition:
        width .18s ease,
        height .18s ease,
        border-color .18s ease,
        background .18s ease,
        color .18s ease,
        box-shadow .18s ease,
        transform .18s ease!important;
      pointer-events:none!important;
    }

    #operativoNav.rt-carousel.rt-icon-rail-v1 .rt-tab-icon svg{
      display:block!important;
      width:21px!important;
      height:21px!important;
      min-width:21px!important;
      max-width:21px!important;
      stroke:currentColor!important;
      fill:none!important;
      opacity:1!important;
      visibility:visible!important;
      transition:width .18s ease,height .18s ease,transform .18s ease!important;
    }

    /* activo: ligeramente más grande, no tarjeta grande */
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>.switch.active,
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>button.active,
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>[aria-selected="true"],
    #operativoNav.rt-carousel.rt-icon-rail-v1>.rt-icon-user-active{
      opacity:1!important;
      color:#fff!important;
      z-index:3!important;
      transform:translateY(-1px)!important;
    }

    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>.switch.active .rt-tab-icon,
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>button.active .rt-tab-icon,
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>[aria-selected="true"] .rt-tab-icon,
    #operativoNav.rt-carousel.rt-icon-rail-v1>.rt-icon-user-active .rt-tab-icon{
      width:52px!important;
      height:52px!important;
      min-width:52px!important;
      max-width:52px!important;
      border-color:#0d6fd1!important;
      background:linear-gradient(145deg,#0b3a6e 0%,#0c579e 58%,#0d7ff4 100%)!important;
      color:#fff!important;
      box-shadow:0 8px 18px rgba(10,69,126,.22)!important;
      transform:scale(1.02)!important;
    }

    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>.switch.active .rt-tab-icon svg,
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>button.active .rt-tab-icon svg,
    #operativoNav.rt-carousel.rt-icon-rail-v1:not(.rt-icon-has-user-selection)>[aria-selected="true"] .rt-tab-icon svg,
    #operativoNav.rt-carousel.rt-icon-rail-v1>.rt-icon-user-active .rt-tab-icon svg{
      width:25px!important;
      height:25px!important;
      transform:scale(1.02)!important;
    }

    /* nombre interno oculto: el texto se muestra sólo debajo */
    #operativoNav.rt-carousel.rt-icon-rail-v1 .rt-tab-label{
      position:absolute!important;
      width:1px!important;
      height:1px!important;
      margin:-1px!important;
      padding:0!important;
      overflow:hidden!important;
      clip:rect(0,0,0,0)!important;
      clip-path:inset(50%)!important;
      white-space:nowrap!important;
      border:0!important;
      opacity:0!important;
      pointer-events:none!important;
    }

    .rt-icon-rail-v1-shell{
      position:relative!important;
      width:100%!important;
      margin:0 0 8px!important;
      padding:0!important;
      isolation:isolate!important;
    }

    .rt-icon-rail-v1-shell::before,
    .rt-icon-rail-v1-shell::after{
      content:""!important;
      position:absolute!important;
      top:5px!important;
      z-index:8!important;
      width:24px!important;
      height:64px!important;
      pointer-events:none!important;
    }
    .rt-icon-rail-v1-shell::before{
      left:0!important;
      background:linear-gradient(90deg,#f4f8fc 12%,rgba(244,248,252,0))!important;
      border-radius:22px 0 0 22px!important;
    }
    .rt-icon-rail-v1-shell::after{
      right:0!important;
      background:linear-gradient(270deg,#f4f8fc 12%,rgba(244,248,252,0))!important;
      border-radius:0 22px 22px 0!important;
    }

    .rt-icon-rail-v1-current{
      display:flex!important;
      align-items:center!important;
      justify-content:center!important;
      min-height:28px!important;
      margin:-2px 0 0!important;
      padding:0 12px 4px!important;
      color:#0b3a6e!important;
      font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;
      font-size:13.5px!important;
      line-height:1.1!important;
      font-weight:900!important;
      letter-spacing:-.015em!important;
      text-align:center!important;
      white-space:normal!important;
      pointer-events:none!important;
    }

    .rt-icon-rail-v1-current::before,
    .rt-icon-rail-v1-current::after{
      content:""!important;
      width:16px!important;
      height:2px!important;
      margin:0 8px!important;
      border-radius:999px!important;
      background:#0d7ff4!important;
      opacity:.22!important;
    }

    .rt-icon-rail-v1-indicator{
      display:block!important;
      width:32px!important;
      height:3px!important;
      margin:0 auto 1px!important;
      border-radius:999px!important;
      background:linear-gradient(90deg,#0d7ff4,#0b4f91)!important;
      opacity:.78!important;
      pointer-events:none!important;
      box-shadow:0 1px 4px rgba(13,127,244,.16)!important;
    }
    .rt-icon-rail-v1-dot{display:none!important}

    /* neutraliza restos de las variantes Mundial anteriores */
    #operativoNav.rt-icon-rail-v1 .rt-m7-base,
    #operativoNav.rt-icon-rail-v1 .rt-m7-face,
    #operativoNav.rt-icon-rail-v1 .rt-mundial-base,
    #operativoNav.rt-icon-rail-v1 .rt-mundial-face{
      display:none!important;
    }

    @media(max-width:900px){
      #operativoNav.rt-carousel.rt-icon-rail-v1{
        --rt-card-w:64px!important;
        --rt-gap:8px!important;
        min-height:72px!important;
        height:72px!important;
        padding-top:6px!important;
        padding-bottom:7px!important;
      }

      #operativoNav.rt-carousel.rt-icon-rail-v1>.switch,
      #operativoNav.rt-carousel.rt-icon-rail-v1>button{
        height:58px!important;
        min-height:58px!important;
        max-height:58px!important;
      }

      #operativoNav.rt-carousel.rt-icon-rail-v1 .rt-tab-icon{
        width:42px!important;
        height:42px!important;
        min-width:42px!important;
        max-width:42px!important;
      }

      #operativoNav.rt-carousel.rt-icon-rail-v1 .rt-tab-icon svg{
        width:20px!important;
        height:20px!important;
      }

      #operativoNav.rt-carousel.rt-icon-rail-v1>.switch.active .rt-tab-icon,
      #operativoNav.rt-carousel.rt-icon-rail-v1>button.active .rt-tab-icon,
      #operativoNav.rt-carousel.rt-icon-rail-v1>[aria-selected="true"] .rt-tab-icon{
        width:50px!important;
        height:50px!important;
        min-width:50px!important;
        max-width:50px!important;
      }

      #operativoNav.rt-carousel.rt-icon-rail-v1>.switch.active .rt-tab-icon svg,
      #operativoNav.rt-carousel.rt-icon-rail-v1>button.active .rt-tab-icon svg,
      #operativoNav.rt-carousel.rt-icon-rail-v1>[aria-selected="true"] .rt-tab-icon svg{
        width:24px!important;
        height:24px!important;
      }

      .rt-icon-rail-v1-current{
        min-height:27px!important;
        font-size:13px!important;
      }
    }

    @media(min-width:901px){
      #operativoNav.rt-carousel.rt-icon-rail-v1{
        --rt-card-w:72px!important;
        --rt-gap:10px!important;
      }
    }

    /* La configuración Pestañas visibles manda sobre cualquier carrusel.
       Ningún !important histórico puede volver a pintar una pestaña desmarcada. */
    #operativoNav.rt-carousel>button.hidden,
    #analysisNav.rt-carousel>button.hidden,
    .v125-tabs.rt-carousel>button.hidden,
    #operativoNav.rt-carousel>button[hidden],
    #analysisNav.rt-carousel>button[hidden],
    .v125-tabs.rt-carousel>button[hidden]{
      display:none!important;
      visibility:hidden!important;
      flex:0 0 0!important;
      width:0!important;
      min-width:0!important;
      max-width:0!important;
      height:0!important;
      min-height:0!important;
      max-height:0!important;
      margin:0!important;
      padding:0!important;
      border:0!important;
      opacity:0!important;
      pointer-events:none!important;
      overflow:hidden!important;
    }

    @media(prefers-reduced-motion:reduce){
      #operativoNav.rt-carousel.rt-icon-rail-v1>.switch,
      #operativoNav.rt-carousel.rt-icon-rail-v1>button,
      #operativoNav.rt-carousel.rt-icon-rail-v1 .rt-tab-icon{
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

  function reconnectObserver(state){
    if(!state?.observer) return;
    state.observer.disconnect();
    state.observer.observe(state.viewport,{
      subtree:true,
      childList:true,
      attributes:true,
      attributeFilter:['class','aria-selected','hidden','style']
    });
  }

  function logicalCards(state){
    if(!state.logicalButtons?.length){
      state.logicalButtons=cards(state.viewport).slice();
      state.logicalButtons.forEach((btn,i)=>btn.dataset.rtRingOrder=String(i));
    }

    // Registrar botones nuevos sin alterar el orden lógico ya conocido.
    [...state.viewport.children].forEach(el=>{
      if(!(el instanceof HTMLButtonElement)) return;
      if(state.logicalButtons.includes(el)) return;
      el.dataset.rtRingOrder=String(state.logicalButtons.length);
      state.logicalButtons.push(el);
    });

    return state.logicalButtons.filter(btn=>
      btn.isConnected &&
      btn.parentElement===state.viewport &&
      !btn.hidden &&
      !btn.classList.contains('hidden') &&
      getComputedStyle(btn).display!=='none'
    );
  }

  function centerButtonLocal(viewport,btn,behavior='auto'){
    if(!viewport||!btn) return;
    const left=btn.offsetLeft + btn.offsetWidth/2 - viewport.clientWidth/2;
    viewport.scrollTo({left:Math.max(0,left),behavior});
  }

  function circularizeAround(state,selected,{behavior='auto'}={}){
    const viewport=state.viewport;
    const visible=logicalCards(state);
    if(!selected || visible.length<3 || !visible.includes(selected)) return;
    if(state.reordering) return;

    const idx=visible.indexOf(selected);
    const before=Math.floor(visible.length/2);
    const ordered=[];
    for(let step=-before; step<visible.length-before; step++){
      ordered.push(visible[(idx+step+visible.length)%visible.length]);
    }

    state.reordering=true;
    state.observer?.disconnect();

    const frag=document.createDocumentFragment();
    ordered.forEach(btn=>frag.appendChild(btn));

    // Los ocultos se mantienen en DOM para conservar permisos/listeners.
    state.logicalButtons
      .filter(btn=>btn.isConnected && !visible.includes(btn))
      .forEach(btn=>frag.appendChild(btn));

    viewport.appendChild(frag);
    centerPadding(viewport);

    requestAnimationFrame(()=>{
      centerButtonLocal(viewport,selected,behavior);
      requestAnimationFrame(()=>centerButtonLocal(viewport,selected,'auto'));
    });

    setTimeout(()=>{
      state.reordering=false;
      reconnectObserver(state);
    },50);
  }

  function labelOf(btn){
    return (
      btn.dataset.rtLabel ||
      btn.dataset.rtOriginalLabel ||
      btn.getAttribute('aria-label') ||
      btn.textContent ||
      'Pestaña'
    ).replace(/\s+/g,' ').trim();
  }

  function restoreIcon(btn){
    // Mundial V7 metió el icono dentro de .rt-m7-face.
    const face=btn.querySelector(':scope > .rt-m7-face');
    if(face){
      const icon=face.querySelector('.rt-tab-icon');
      if(icon) btn.insertBefore(icon,face);
      face.remove();
    }

    // Mundial V6.
    const face6=btn.querySelector(':scope > .rt-mundial-face');
    if(face6){
      const icon=face6.querySelector('.rt-tab-icon');
      if(icon) btn.insertBefore(icon,face6);
      face6.remove();
    }

    btn.querySelector(':scope > .rt-m7-base')?.remove();
    btn.querySelector(':scope > .rt-mundial-base')?.remove();
  }

  function activeButton(viewport){
    const list=cards(viewport);
    return list.find(btn => btn.classList.contains('active'))
      || list.find(btn => btn.getAttribute('aria-selected')==='true')
      || list[0]
      || null;
  }

  function visualButton(state){
    const list=cards(state.viewport);
    if(state.userSelectedButton && list.includes(state.userSelectedButton)){
      return state.userSelectedButton;
    }
    return activeButton(state.viewport);
  }

  function applyVisualSelection(state){
    const selected=visualButton(state);
    const list=cards(state.viewport);

    state.viewport.classList.toggle('rt-icon-has-user-selection',!!state.userSelectedButton);
    list.forEach(btn=>{
      btn.classList.toggle('rt-icon-user-active',btn===selected);
    });

    if(!selected) return;
    const label=labelOf(selected);
    if(state.current.textContent!==label) state.current.textContent=label;

    const idx=list.indexOf(selected);
    [...state.indicator.children].forEach((dot,i)=>dot.classList.toggle('active',i===idx));
  }

  function setCurrent(state){
    applyVisualSelection(state);
  }

  function rebuildDots(state){
    // En un carrusel circular no existe un inicio/fin real; usamos una
    // pequeña barra de foco en vez de una fila de puntos.
    if(state.indicator.childElementCount) state.indicator.innerHTML='';
  }

  function centerPadding(viewport){
    const first=cards(viewport)[0];
    if(!first || !viewport.clientWidth) return;
    const edge=Math.max(10,(viewport.clientWidth-first.offsetWidth)/2);
    viewport.style.setProperty('--rt-edge-pad',edge+'px');
  }

  function enhance(){
    installStyle();

    const viewport=document.getElementById(TARGET_ID);
    if(!(viewport instanceof HTMLElement) || !viewport.classList.contains('rt-carousel')) return;

    const shell=viewport.closest('.rt-carousel-shell');
    if(!shell) return;

    let state=STATE.get(viewport);
    if(state){
      cards(viewport).forEach(restoreIcon);
      rebuildDots(state);
      setCurrent(state);
      centerPadding(viewport);
      return;
    }

    // Retira capas visuales Mundial anteriores sólo de Cambios y Muertos.
    shell.classList.remove('rt-mundial-stage','rt-mundial-v6','rt-mundial-v7');
    shell.querySelector(':scope > .rt-worldcup-pedestal')?.remove();
    shell.querySelector(':scope > .rt-worldcup-current')?.remove();
    shell.querySelector(':scope > .rt-mundial-current')?.remove();
    shell.querySelector(':scope > .rt-m7-current')?.remove();

    shell.classList.add('rt-icon-rail-v1-shell');
    viewport.classList.add('rt-icon-rail-v1');

    cards(viewport).forEach(restoreIcon);

    const current=document.createElement('div');
    current.className='rt-icon-rail-v1-current';
    current.setAttribute('aria-live','polite');

    const indicator=document.createElement('div');
    indicator.className='rt-icon-rail-v1-indicator';
    indicator.setAttribute('aria-hidden','true');

    shell.append(current,indicator);

    state={viewport,shell,current,indicator,observer:null,userSelectedButton:null,logicalButtons:cards(viewport).slice(),reordering:false};
    STATE.set(viewport,state);

    state.logicalButtons.forEach((btn,i)=>btn.dataset.rtRingOrder=String(i));
    rebuildDots(state);
    setCurrent(state);
    centerPadding(viewport);
    setTimeout(()=>circularizeAround(state,visualButton(state),{behavior:'auto'}),60);

    viewport.addEventListener('click',event=>{
      const btn=event.target.closest('button');
      if(!btn || btn.parentElement!==viewport) return;

      // La selección visual responde inmediatamente al usuario.
      state.userSelectedButton=btn;
      applyVisualSelection(state);

      // Al terminar la selección reordenamos los mismos botones reales en forma
      // circular: antes del primero aparece el último y después del último el primero.
      setTimeout(()=>applyVisualSelection(state),40);
      setTimeout(()=>{
        applyVisualSelection(state);
        circularizeAround(state,btn,{behavior:'smooth'});
      },210);
    },true);
    viewport.addEventListener('scroll',()=>{}, {passive:true});

    const mo=new MutationObserver(mutations=>{
      if(state.reordering) return;

      cards(viewport).forEach(restoreIcon);
      logicalCards(state);
      rebuildDots(state);

      // Mantener la selección hecha por el usuario aunque el reporte cambie
      // clases/aria-selected durante su renderizado.
      const visible=logicalCards(state);
      if(state.userSelectedButton && !visible.includes(state.userSelectedButton)){
        state.userSelectedButton=null;
      }

      applyVisualSelection(state);
      centerPadding(viewport);

      const visibilityChanged=mutations.some(m=>
        m.type==='childList' ||
        (m.type==='attributes' && ['hidden','style'].includes(m.attributeName))
      );
      if(visibilityChanged){
        const selected=visualButton(state);
        setTimeout(()=>circularizeAround(state,selected,{behavior:'auto'}),30);
      }
    });
    state.observer=mo;
    reconnectObserver(state);
  }

  function init(){
    enhance();

    document.addEventListener('report-tabs-visibility-changed',()=>{
      const viewport=document.getElementById(TARGET_ID);
      const state=viewport?STATE.get(viewport):null;
      if(!state)return;

      const visible=logicalCards(state);
      if(state.userSelectedButton && !visible.includes(state.userSelectedButton)){
        state.userSelectedButton=null;
      }

      rebuildDots(state);
      applyVisualSelection(state);
      centerPadding(viewport);
      const selected=visualButton(state);
      setTimeout(()=>circularizeAround(state,selected,{behavior:'auto'}),20);
    });

    const mo=new MutationObserver(()=>{
      clearTimeout(window.__rtIconRailScan);
      window.__rtIconRailScan=setTimeout(enhance,35);
    });
    mo.observe(document.body,{subtree:true,childList:true});

    window.addEventListener('resize',()=>{
      clearTimeout(window.__rtIconRailResize);
      window.__rtIconRailResize=setTimeout(enhance,80);
    },{passive:true});

    const api={
      refresh:enhance,
      select:(btn)=>{
        const viewport=document.getElementById(TARGET_ID);
        const state=viewport?STATE.get(viewport):null;
        if(!state || !(btn instanceof HTMLButtonElement)) return;
        state.userSelectedButton=btn;
        applyVisualSelection(state);
        setTimeout(()=>circularizeAround(state,btn,{behavior:'smooth'}),40);
      }
    };
    window.ReportTabIconRailV1=api;
    window.ReportTabIconRailV3=api;
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();