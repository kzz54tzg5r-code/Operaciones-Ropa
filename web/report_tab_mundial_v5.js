(() => {
  'use strict';

  const STYLE_ID='rt-mundial-v5-style';
  const BOUND=new WeakMap();

  const css=`
    .rt-carousel-shell.rt-mundial-stage{
      --rt-card-w:170px!important;
      --rt-gap:16px!important;
      position:relative!important;
      overflow:visible!important;
      padding-top:2px!important;
      margin-bottom:8px!important;
      isolation:isolate;
    }

    .rt-carousel-shell.rt-mundial-stage .rt-carousel{
      position:relative!important;
      z-index:2!important;
      min-height:126px!important;
      padding-top:14px!important;
      padding-bottom:24px!important;
      background:transparent!important;
      scroll-snap-type:x mandatory!important;
      scroll-padding-inline:var(--rt-edge-pad)!important;
      perspective:700px!important;
    }

    .rt-carousel-shell.rt-mundial-stage .rt-carousel .switch,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel .v125-tab,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel>button{
      --rt-wc-scale:.64;
      --rt-wc-y:18px;
      --rt-wc-opacity:.55;
      flex:0 0 var(--rt-card-w)!important;
      width:var(--rt-card-w)!important;
      min-width:var(--rt-card-w)!important;
      max-width:var(--rt-card-w)!important;
      height:82px!important;
      min-height:82px!important;
      padding:9px 12px!important;
      border-radius:17px!important;
      border:1px solid #d8e4ef!important;
      background:linear-gradient(160deg,#ffffff 0%,#f8fbff 100%)!important;
      color:#526a82!important;
      opacity:var(--rt-wc-opacity)!important;
      transform:translateY(var(--rt-wc-y)) scale(var(--rt-wc-scale))!important;
      transform-origin:center bottom!important;
      box-shadow:0 3px 11px rgba(16,53,91,.06)!important;
      transition:
        transform .10s ease-out,
        opacity .10s ease-out,
        border-color .12s ease,
        box-shadow .12s ease,
        background .12s ease!important;
      will-change:transform,opacity!important;
      scroll-snap-align:center!important;
      scroll-snap-stop:always!important;
      z-index:var(--rt-wc-z,1)!important;
    }

    .rt-carousel-shell.rt-mundial-stage .rt-carousel .switch.active,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel .v125-tab.active,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel>button.active,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel [aria-selected="true"]{
      border:2px solid rgba(255,255,255,.98)!important;
      background:linear-gradient(155deg,#ffffff 0%,#eef6ff 100%)!important;
      color:#0b447f!important;
      box-shadow:
        0 10px 24px rgba(10,63,116,.20),
        0 0 0 1px rgba(13,127,244,.12)!important;
    }

    .rt-carousel-shell.rt-mundial-stage .rt-carousel .switch.active::after,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel .v125-tab.active::after,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel>button.active::after,
    .rt-carousel-shell.rt-mundial-stage .rt-carousel [aria-selected="true"]::after{
      display:none!important;
      content:none!important;
    }

    .rt-carousel-shell.rt-mundial-stage .rt-tab-icon{
      width:27px!important;
      height:27px!important;
      min-width:27px!important;
      color:#0d72d4!important;
      transform:scale(var(--rt-wc-icon-scale,1))!important;
      transition:transform .10s ease-out,color .12s ease!important;
    }
    .rt-carousel-shell.rt-mundial-stage .rt-tab-icon svg{
      width:27px!important;
      height:27px!important;
      stroke-width:1.75!important;
    }
    .rt-carousel-shell.rt-mundial-stage .rt-tab-label{
      max-width:142px!important;
      font-size:10px!important;
      line-height:1.08!important;
      font-weight:780!important;
      color:inherit!important;
      opacity:var(--rt-wc-label-opacity,.75)!important;
      transition:opacity .10s ease-out!important;
    }

    .rt-worldcup-pedestal{
      position:absolute!important;
      left:50%!important;
      top:47px!important;
      width:154px!important;
      height:68px!important;
      transform:translateX(-50%)!important;
      z-index:1!important;
      pointer-events:none!important;
      border-radius:24px 24px 7px 7px!important;
      background:
        linear-gradient(145deg,rgba(8,72,136,.95),rgba(13,127,244,.95))!important;
      box-shadow:0 12px 28px rgba(7,53,101,.17)!important;
      opacity:.96!important;
    }
    .rt-worldcup-pedestal::before,
    .rt-worldcup-pedestal::after{
      content:""!important;
      position:absolute!important;
      bottom:0!important;
      width:32px!important;
      height:43px!important;
      background:inherit!important;
      border-radius:20px 20px 4px 4px!important;
      opacity:.92!important;
    }
    .rt-worldcup-pedestal::before{left:-23px!important}
    .rt-worldcup-pedestal::after{right:-23px!important}

    .rt-worldcup-current{
      position:relative!important;
      z-index:4!important;
      display:flex!important;
      align-items:center!important;
      justify-content:center!important;
      gap:8px!important;
      min-height:28px!important;
      margin-top:-14px!important;
      padding:0 14px 4px!important;
      color:#0b3a6e!important;
      font-size:15px!important;
      line-height:1.1!important;
      font-weight:900!important;
      letter-spacing:-.02em!important;
      text-align:center!important;
      pointer-events:none!important;
    }
    .rt-worldcup-current::before,
    .rt-worldcup-current::after{
      content:""!important;
      width:15px!important;
      height:20px!important;
      opacity:.22!important;
      background:
        radial-gradient(ellipse at 70% 20%,#0b5fa8 0 28%,transparent 30%),
        radial-gradient(ellipse at 30% 48%,#0b5fa8 0 24%,transparent 26%),
        radial-gradient(ellipse at 75% 75%,#0b5fa8 0 23%,transparent 25%)!important;
    }
    .rt-worldcup-current::after{transform:scaleX(-1)!important}

    @media(max-width:900px){
      .rt-carousel-shell.rt-mundial-stage{
        --rt-card-w:clamp(154px,41vw,168px)!important;
        --rt-gap:13px!important;
        margin-top:1px!important;
        margin-bottom:4px!important;
      }
      .rt-carousel-shell.rt-mundial-stage .rt-carousel{
        min-height:124px!important;
        padding-top:13px!important;
        padding-bottom:23px!important;
      }
      .rt-carousel-shell.rt-mundial-stage .rt-carousel .switch,
      .rt-carousel-shell.rt-mundial-stage .rt-carousel .v125-tab,
      .rt-carousel-shell.rt-mundial-stage .rt-carousel>button{
        height:80px!important;
        min-height:80px!important;
        border-radius:16px!important;
      }
      .rt-worldcup-pedestal{
        top:45px!important;
        width:146px!important;
        height:65px!important;
      }
      .rt-worldcup-current{
        margin-top:-13px!important;
        font-size:14px!important;
      }
      .rt-carousel-shell.rt-mundial-stage .rt-carousel-arrow{
        display:none!important;
      }
    }

    @media(min-width:901px){
      .rt-carousel-shell.rt-mundial-stage{
        --rt-card-w:clamp(160px,15vw,184px)!important;
        --rt-gap:16px!important;
      }
      .rt-worldcup-pedestal{
        width:158px!important;
      }
      .rt-worldcup-current{
        font-size:14px!important;
      }
    }

    @media(prefers-reduced-motion:reduce){
      .rt-carousel-shell.rt-mundial-stage .rt-carousel .switch,
      .rt-carousel-shell.rt-mundial-stage .rt-carousel .v125-tab,
      .rt-carousel-shell.rt-mundial-stage .rt-carousel>button{
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

  function buttons(viewport){
    return [...viewport.children].filter(el=>el instanceof HTMLButtonElement && !el.hidden && !el.classList.contains('hidden') && getComputedStyle(el).display!=='none');
  }

  function layoutEdge(viewport){
    const first=buttons(viewport)[0];
    if(!first||!viewport.clientWidth) return;
    const edge=Math.max(12,(viewport.clientWidth-first.offsetWidth)/2);
    viewport.style.setProperty('--rt-edge-pad',edge+'px');
  }

  function nearest(viewport){
    const list=buttons(viewport);
    if(!list.length) return null;
    const vr=viewport.getBoundingClientRect();
    const cx=vr.left+vr.width/2;
    let best=list[0],dist=Infinity;
    for(const btn of list){
      const r=btn.getBoundingClientRect();
      const d=Math.abs((r.left+r.width/2)-cx);
      if(d<dist){dist=d;best=btn;}
    }
    return best;
  }

  function setCurrentLabel(state,btn){
    if(!btn||!state.current) return;
    const label=btn.dataset.rtLabel || btn.querySelector('.rt-tab-label')?.textContent?.trim() || btn.textContent?.trim() || '';
    if(state.current.textContent!==label) state.current.textContent=label;
  }

  function updateCoverflow(viewport){
    const state=BOUND.get(viewport);
    if(!state||!viewport.clientWidth) return;
    state.raf=null;

    const list=buttons(viewport);
    if(!list.length) return;

    layoutEdge(viewport);

    const vr=viewport.getBoundingClientRect();
    const cx=vr.left+vr.width/2;
    const step=Math.max(1,(list[0].offsetWidth + 13));

    let closest=null;
    let closestDist=Infinity;

    list.forEach(btn=>{
      const r=btn.getBoundingClientRect();
      const cardCenter=r.left+r.width/2;
      const dist=Math.abs(cardCenter-cx);
      const normalized=Math.min(1,dist/step);
      const focus=1-normalized;

      // Mundial: la tarjeta central crece, las laterales se reducen y bajan.
      const scale=.64 + (.36*focus);
      const y=18 - (24*focus);
      const opacity=.52 + (.48*focus);
      const z=2 + Math.round(focus*18);
      const iconScale=.82 + (.28*focus);
      const labelOpacity=.44 + (.56*focus);

      btn.style.setProperty('--rt-wc-scale',scale.toFixed(3));
      btn.style.setProperty('--rt-wc-y',y.toFixed(1)+'px');
      btn.style.setProperty('--rt-wc-opacity',opacity.toFixed(3));
      btn.style.setProperty('--rt-wc-z',String(z));
      btn.style.setProperty('--rt-wc-icon-scale',iconScale.toFixed(3));
      btn.style.setProperty('--rt-wc-label-opacity',labelOpacity.toFixed(3));

      if(dist<closestDist){
        closestDist=dist;
        closest=btn;
      }
    });

    if(closest) setCurrentLabel(state,closest);
  }

  function schedule(viewport){
    const state=BOUND.get(viewport);
    if(!state||state.raf) return;
    state.raf=requestAnimationFrame(()=>updateCoverflow(viewport));
  }

  function enhance(viewport){
    if(!(viewport instanceof HTMLElement) || !viewport.classList.contains('rt-carousel')) return;

    const existing=BOUND.get(viewport);
    if(existing){
      schedule(viewport);
      return;
    }

    const shell=viewport.closest('.rt-carousel-shell');
    if(!shell) return;

    shell.classList.add('rt-mundial-stage');

    let pedestal=shell.querySelector(':scope > .rt-worldcup-pedestal');
    if(!pedestal){
      pedestal=document.createElement('div');
      pedestal.className='rt-worldcup-pedestal';
      pedestal.setAttribute('aria-hidden','true');
      shell.insertBefore(pedestal,viewport);
    }

    let current=shell.querySelector(':scope > .rt-worldcup-current');
    if(!current){
      current=document.createElement('div');
      current.className='rt-worldcup-current';
      current.setAttribute('aria-live','polite');
      shell.appendChild(current);
    }

    const state={shell,pedestal,current,raf:null};
    BOUND.set(viewport,state);

    viewport.addEventListener('scroll',()=>schedule(viewport),{passive:true});
    viewport.addEventListener('touchmove',()=>schedule(viewport),{passive:true});
    viewport.addEventListener('touchend',()=>setTimeout(()=>schedule(viewport),25),{passive:true});
    viewport.addEventListener('click',()=>setTimeout(()=>schedule(viewport),20));

    const observer=new MutationObserver(()=>schedule(viewport));
    observer.observe(viewport,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected','style']});
    state.observer=observer;

    layoutEdge(viewport);
    schedule(viewport);
    setTimeout(()=>schedule(viewport),120);
  }

  function scan(){
    installStyle();
    document.querySelectorAll('.rt-carousel').forEach(enhance);
  }

  function init(){
    scan();

    const mo=new MutationObserver(()=>{
      clearTimeout(window.__rtMundialScan);
      window.__rtMundialScan=setTimeout(scan,30);
    });
    mo.observe(document.body,{subtree:true,childList:true});

    window.addEventListener('resize',()=>{
      clearTimeout(window.__rtMundialResize);
      window.__rtMundialResize=setTimeout(()=>{
        document.querySelectorAll('.rt-carousel').forEach(v=>{
          layoutEdge(v);
          schedule(v);
        });
      },80);
    },{passive:true});

    window.ReportTabMundial={
      refresh:scan,
      update:(viewport)=>schedule(viewport)
    };
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();