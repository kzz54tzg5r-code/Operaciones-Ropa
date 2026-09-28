(() => {
  'use strict';

  const STYLE_ID='rt-mundial-v6-style';
  const BOUND=new WeakMap();

  const css=`
    /* Mundial V6: cada pestaña es una ficha compuesta,
       no un botón con texto. */
    .rt-carousel-shell.rt-mundial-v6{
      --rt-card-w:174px!important;
      --rt-gap:12px!important;
      position:relative!important;
      width:100%!important;
      max-width:100%!important;
      min-height:154px!important;
      margin:2px 0 5px!important;
      padding:0!important;
      overflow:visible!important;
      isolation:isolate!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-carousel{
      position:relative!important;
      z-index:2!important;
      display:flex!important;
      flex-wrap:nowrap!important;
      align-items:flex-start!important;
      width:100%!important;
      max-width:100%!important;
      height:124px!important;
      min-height:124px!important;
      padding:8px var(--rt-edge-pad) 16px!important;
      margin:0!important;
      gap:var(--rt-gap)!important;
      overflow-x:auto!important;
      overflow-y:visible!important;
      scroll-snap-type:x mandatory!important;
      scroll-padding-inline:var(--rt-edge-pad)!important;
      background:transparent!important;
      border:0!important;
      border-radius:0!important;
      box-shadow:none!important;
      scrollbar-width:none!important;
      perspective:none!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-carousel::-webkit-scrollbar{
      display:none!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-carousel .switch,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel .v125-tab,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel>button{
      --rt-m-scale:.68;
      --rt-m-y:15px;
      --rt-m-opacity:.66;
      --rt-m-base-alpha:.58;
      --rt-m-shadow-alpha:.06;
      position:relative!important;
      isolation:isolate!important;
      flex:0 0 var(--rt-card-w)!important;
      width:var(--rt-card-w)!important;
      min-width:var(--rt-card-w)!important;
      max-width:var(--rt-card-w)!important;
      height:104px!important;
      min-height:104px!important;
      margin:0!important;
      padding:0!important;
      border:0!important;
      border-radius:0!important;
      background:transparent!important;
      color:#0b4f91!important;
      box-shadow:none!important;
      opacity:var(--rt-m-opacity)!important;
      transform:translateY(var(--rt-m-y)) scale(var(--rt-m-scale))!important;
      transform-origin:center bottom!important;
      transition:transform .08s linear,opacity .08s linear!important;
      will-change:transform,opacity!important;
      scroll-snap-align:center!important;
      scroll-snap-stop:always!important;
      overflow:visible!important;
      white-space:normal!important;
      cursor:pointer!important;
      z-index:var(--rt-m-z,1)!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-carousel .switch.active,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel .v125-tab.active,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel>button.active,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel [aria-selected="true"]{
      border:0!important;
      background:transparent!important;
      color:#0b4f91!important;
      box-shadow:none!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-carousel .switch::after,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel .v125-tab::after,
    .rt-carousel-shell.rt-mundial-v6 .rt-carousel>button::after{
      display:none!important;
      content:none!important;
    }

    /* Base de color individual, equivalente a la base detrás de cada bandera. */
    .rt-mundial-base{
      position:absolute!important;
      left:50%!important;
      bottom:3px!important;
      width:150px!important;
      height:62px!important;
      transform:translateX(-50%)!important;
      z-index:0!important;
      border-radius:29px 29px 9px 9px!important;
      background:
        linear-gradient(145deg,
          rgba(7,58,112,var(--rt-m-base-alpha)),
          rgba(13,127,244,var(--rt-m-base-alpha)))!important;
      box-shadow:0 8px 18px rgba(8,58,108,var(--rt-m-shadow-alpha))!important;
      pointer-events:none!important;
    }

    .rt-mundial-base::before,
    .rt-mundial-base::after{
      content:""!important;
      position:absolute!important;
      bottom:0!important;
      width:42px!important;
      height:45px!important;
      border-radius:25px 25px 8px 8px!important;
      background:inherit!important;
    }
    .rt-mundial-base::before{left:-24px!important}
    .rt-mundial-base::after{right:-24px!important}

    /* Cara frontal blanca: equivalente a la tarjeta con la bandera. */
    .rt-mundial-face{
      position:absolute!important;
      left:50%!important;
      top:0!important;
      width:132px!important;
      height:76px!important;
      transform:translateX(-50%)!important;
      z-index:3!important;
      display:grid!important;
      place-items:center!important;
      border:2px solid rgba(198,215,231,.95)!important;
      border-radius:12px!important;
      background:linear-gradient(160deg,#ffffff 0%,#f8fbff 100%)!important;
      box-shadow:
        0 6px 15px rgba(10,49,87,.10),
        inset 0 1px 0 rgba(255,255,255,.92)!important;
      pointer-events:none!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-tab-icon{
      display:grid!important;
      place-items:center!important;
      width:39px!important;
      height:39px!important;
      min-width:39px!important;
      margin:0!important;
      color:#0d6fc8!important;
      transform:none!important;
      pointer-events:none!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-tab-icon svg{
      display:block!important;
      width:39px!important;
      height:39px!important;
      stroke:currentColor!important;
      stroke-width:1.6!important;
      fill:none!important;
    }

    /* El nombre no vive dentro de la ficha, igual que en el video de referencia. */
    .rt-carousel-shell.rt-mundial-v6 .rt-tab-label{
      position:absolute!important;
      width:1px!important;
      height:1px!important;
      overflow:hidden!important;
      clip:rect(0 0 0 0)!important;
      clip-path:inset(50%)!important;
      white-space:nowrap!important;
      opacity:0!important;
      pointer-events:none!important;
    }

    .rt-mundial-current{
      position:absolute!important;
      left:50%!important;
      bottom:0!important;
      z-index:6!important;
      width:min(88%,420px)!important;
      transform:translateX(-50%)!important;
      display:flex!important;
      align-items:center!important;
      justify-content:center!important;
      min-height:31px!important;
      padding:3px 16px 4px!important;
      color:#0b3a6e!important;
      font-size:15px!important;
      line-height:1.12!important;
      font-weight:900!important;
      letter-spacing:-.02em!important;
      text-align:center!important;
      white-space:normal!important;
      pointer-events:none!important;
    }

    .rt-mundial-current::before,
    .rt-mundial-current::after{
      content:""!important;
      display:block!important;
      width:18px!important;
      height:2px!important;
      margin:0 8px!important;
      border-radius:999px!important;
      background:#0d7ff4!important;
      opacity:.28!important;
    }

    .rt-carousel-shell.rt-mundial-v6 .rt-carousel-arrow{
      top:57px!important;
    }

    @media(max-width:900px){
      .rt-carousel-shell.rt-mundial-v6{
        --rt-card-w:164px!important;
        --rt-gap:10px!important;
        min-height:148px!important;
        margin-top:0!important;
        margin-bottom:4px!important;
      }

      .rt-carousel-shell.rt-mundial-v6 .rt-carousel{
        height:119px!important;
        min-height:119px!important;
        padding-top:6px!important;
        padding-bottom:14px!important;
      }

      .rt-carousel-shell.rt-mundial-v6 .rt-carousel .switch,
      .rt-carousel-shell.rt-mundial-v6 .rt-carousel .v125-tab,
      .rt-carousel-shell.rt-mundial-v6 .rt-carousel>button{
        height:100px!important;
        min-height:100px!important;
      }

      .rt-mundial-base{
        width:140px!important;
        height:59px!important;
      }

      .rt-mundial-base::before,
      .rt-mundial-base::after{
        width:38px!important;
        height:42px!important;
      }
      .rt-mundial-base::before{left:-22px!important}
      .rt-mundial-base::after{right:-22px!important}

      .rt-mundial-face{
        width:124px!important;
        height:72px!important;
        border-radius:11px!important;
      }

      .rt-carousel-shell.rt-mundial-v6 .rt-tab-icon,
      .rt-carousel-shell.rt-mundial-v6 .rt-tab-icon svg{
        width:37px!important;
        height:37px!important;
        min-width:37px!important;
      }

      .rt-mundial-current{
        min-height:29px!important;
        font-size:14px!important;
      }

      .rt-carousel-shell.rt-mundial-v6 .rt-carousel-arrow{
        display:none!important;
      }
    }

    @media(min-width:901px){
      .rt-carousel-shell.rt-mundial-v6{
        --rt-card-w:174px!important;
        --rt-gap:13px!important;
      }
    }

    @media(prefers-reduced-motion:reduce){
      .rt-carousel-shell.rt-mundial-v6 .rt-carousel .switch,
      .rt-carousel-shell.rt-mundial-v6 .rt-carousel .v125-tab,
      .rt-carousel-shell.rt-mundial-v6 .rt-carousel>button{
        transition:none!important;
      }
    }
  `;

  function installStyle(){
    if(document.getElementById(STYLE_ID)) return;
    const s=document.createElement('style');
    s.id=STYLE_ID;
    s.textContent=css;
    document.head.appendChild(s);
  }

  function cards(viewport){
    return [...viewport.children].filter(el=>
      el instanceof HTMLButtonElement &&
      !el.hidden &&
      !el.classList.contains('hidden') &&
      getComputedStyle(el).display!=='none'
    );
  }

  function labelOf(btn){
    return btn.dataset.rtLabel ||
      btn.querySelector('.rt-tab-label')?.textContent?.trim() ||
      btn.dataset.rtOriginalLabel ||
      btn.textContent?.trim() ||
      'Pestaña';
  }

  function buildCard(btn){
    if(btn.dataset.rtMundialV6==='1') return;

    const icon=btn.querySelector('.rt-tab-icon');
    const label=btn.querySelector('.rt-tab-label');
    if(!icon||!label) return;

    const base=document.createElement('span');
    base.className='rt-mundial-base';
    base.setAttribute('aria-hidden','true');

    const face=document.createElement('span');
    face.className='rt-mundial-face';
    face.setAttribute('aria-hidden','true');

    face.appendChild(icon);
    btn.insertBefore(base,btn.firstChild);
    btn.insertBefore(face,label);

    btn.dataset.rtMundialV6='1';
    btn.setAttribute('aria-label',labelOf(btn));
  }

  function centerPadding(viewport){
    const list=cards(viewport);
    if(!list.length||!viewport.clientWidth) return;
    const edge=Math.max(12,(viewport.clientWidth-list[0].offsetWidth)/2);
    viewport.style.setProperty('--rt-edge-pad',edge+'px');
  }

  function setTitle(state,btn){
    if(!state.current||!btn) return;
    const txt=labelOf(btn);
    if(state.current.textContent!==txt) state.current.textContent=txt;
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
    const cx=vr.left+vr.width/2;
    const step=Math.max(1,list[0].offsetWidth + 10);

    let nearest=null;
    let nearestDist=Infinity;

    for(const btn of list){
      const r=btn.getBoundingClientRect();
      const center=r.left+r.width/2;
      const dist=Math.abs(center-cx);
      const n=Math.min(1,dist/step);
      const focus=1-n;

      // Aproxima la progresión visual del Mundial:
      // lateral ~68%, central 100%.
      const scale=.68 + .32*focus;
      const y=15 - 18*focus;
      const opacity=.66 + .34*focus;
      const baseAlpha=.52 + .45*focus;
      const shadowAlpha=.04 + .16*focus;
      const z=2+Math.round(focus*20);

      btn.style.setProperty('--rt-m-scale',scale.toFixed(3));
      btn.style.setProperty('--rt-m-y',y.toFixed(1)+'px');
      btn.style.setProperty('--rt-m-opacity',opacity.toFixed(3));
      btn.style.setProperty('--rt-m-base-alpha',baseAlpha.toFixed(3));
      btn.style.setProperty('--rt-m-shadow-alpha',shadowAlpha.toFixed(3));
      btn.style.setProperty('--rt-m-z',String(z));

      if(dist<nearestDist){
        nearestDist=dist;
        nearest=btn;
      }
    }

    if(nearest) setTitle(state,nearest);
  }

  function schedule(viewport){
    const state=BOUND.get(viewport);
    if(!state||state.raf) return;
    state.raf=requestAnimationFrame(()=>update(viewport));
  }

  function enhance(viewport){
    if(!(viewport instanceof HTMLElement)||!viewport.classList.contains('rt-carousel')) return;

    const old=BOUND.get(viewport);
    if(old){
      cards(viewport).forEach(buildCard);
      schedule(viewport);
      return;
    }

    const shell=viewport.closest('.rt-carousel-shell');
    if(!shell) return;

    // Neutraliza restos de V5 si una actualización ocurre sin recargar completamente.
    shell.classList.remove('rt-mundial-stage');
    shell.querySelector(':scope > .rt-worldcup-pedestal')?.remove();
    shell.querySelector(':scope > .rt-worldcup-current')?.remove();

    shell.classList.add('rt-mundial-v6');

    let current=shell.querySelector(':scope > .rt-mundial-current');
    if(!current){
      current=document.createElement('div');
      current.className='rt-mundial-current';
      current.setAttribute('aria-live','polite');
      shell.appendChild(current);
    }

    const state={shell,current,raf:null};
    BOUND.set(viewport,state);

    cards(viewport).forEach(buildCard);
    centerPadding(viewport);

    viewport.addEventListener('scroll',()=>schedule(viewport),{passive:true});
    viewport.addEventListener('touchmove',()=>schedule(viewport),{passive:true});
    viewport.addEventListener('touchend',()=>setTimeout(()=>schedule(viewport),20),{passive:true});
    viewport.addEventListener('click',()=>setTimeout(()=>schedule(viewport),25));

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
    setTimeout(()=>schedule(viewport),100);
  }

  function scan(){
    installStyle();
    document.querySelectorAll('.rt-carousel').forEach(enhance);
  }

  function init(){
    scan();

    const mo=new MutationObserver(()=>{
      clearTimeout(window.__rtMundialV6Scan);
      window.__rtMundialV6Scan=setTimeout(scan,30);
    });
    mo.observe(document.body,{subtree:true,childList:true});

    window.addEventListener('resize',()=>{
      clearTimeout(window.__rtMundialV6Resize);
      window.__rtMundialV6Resize=setTimeout(()=>{
        document.querySelectorAll('.rt-carousel').forEach(v=>{
          centerPadding(v);
          schedule(v);
        });
      },80);
    },{passive:true});

    window.ReportTabMundialV6={
      refresh:scan,
      update:schedule
    };
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();