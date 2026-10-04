"""V256 · restaura Vista operativa del Centro Operativo sobre Opción 9B.

La vista Día / Semanal / Mensual / Anual pertenece al controlador V240.
V250/V254 usan un selector rápido genérico; en Centro Operativo ese selector
podía quedar oculto y sus clics eran interceptados antes de llegar a V240.
Esta capa final muestra un selector propio sólo en Centro Operativo y delega
cada cambio directamente a V240_renderCenter.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V256_CENTER_VIEW_RESTORE", False):
        return

    css = r'''<style id="v256-center-view-css">
#operativoPeriodBar.v256-center-active .v250-quick-period{
  display:none!important;
}
#operativoPeriodBar .v256-center-view{
  display:none;
}
#operativoPeriodBar.v256-center-active .v256-center-view{
  order:-10!important;
  display:flex!important;
  flex:1.55 1 390px!important;
  min-width:350px!important;
  width:auto!important;
  max-width:none!important;
  flex-direction:column!important;
  gap:5px!important;
  margin:0!important;
  padding:0!important;
  align-self:flex-end!important;
}
#operativoPeriodBar.v256-center-active .v256-center-title{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
  height:14px!important;
  margin:0!important;
  color:#294b70!important;
  font-size:9px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.025em!important;
}
#operativoPeriodBar.v256-center-active .v256-center-title-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v256-center-active .v256-center-title-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}
#operativoPeriodBar.v256-center-active .v256-center-buttons{
  display:grid!important;
  grid-template-columns:repeat(4,minmax(0,1fr))!important;
  align-items:stretch!important;
  width:100%!important;
  min-height:48px!important;
  height:48px!important;
  overflow:hidden!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  background:#fff!important;
  box-shadow:0 1px 0 rgba(255,255,255,.85) inset!important;
}
#operativoPeriodBar.v256-center-active .v256-center-mode-btn{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  min-width:0!important;
  min-height:48px!important;
  height:48px!important;
  padding:0 10px!important;
  margin:0!important;
  border:0!important;
  border-right:1px solid #d4e5f6!important;
  border-radius:0!important;
  background:#fff!important;
  color:#244e78!important;
  box-shadow:none!important;
  font-size:10px!important;
  line-height:1!important;
  font-weight:900!important;
  white-space:nowrap!important;
  cursor:pointer!important;
}
#operativoPeriodBar.v256-center-active .v256-center-mode-btn:last-child{
  border-right:0!important;
}
#operativoPeriodBar.v256-center-active .v256-center-mode-btn:hover{
  background:#f4f9ff!important;
}
#operativoPeriodBar.v256-center-active .v256-center-mode-btn.active{
  color:#fff!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.15)!important;
}
#operativoPeriodBar.v256-center-active .v256-center-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
#operativoPeriodBar.v256-center-active .v256-center-mode-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}

@media(max-width:1050px){
  #operativoPeriodBar.v256-center-active .v256-center-view{
    flex:0 0 350px!important;
    min-width:350px!important;
  }
}
@media(max-width:650px){
  #operativoPeriodBar.v256-center-active .v256-center-view{
    flex:0 0 292px!important;
    min-width:292px!important;
  }
  #operativoPeriodBar.v256-center-active .v256-center-buttons{
    height:42px!important;
    min-height:42px!important;
  }
  #operativoPeriodBar.v256-center-active .v256-center-mode-btn{
    min-height:42px!important;
    height:42px!important;
    padding:0 6px!important;
    gap:4px!important;
    font-size:8px!important;
  }
  #operativoPeriodBar.v256-center-active .v256-center-title{
    font-size:7.5px!important;
  }
  #operativoPeriodBar.v256-center-active .v256-center-mode-icon{
    width:13px!important;
    height:13px!important;
    min-width:13px!important;
  }
  #operativoPeriodBar.v256-center-active .v256-center-mode-icon svg{
    width:13px!important;
    height:13px!important;
  }
}
</style>'''

    js = r'''<script id="v256-center-view-js">
(function(){
  if(window.__V256_CENTER_VIEW_RESTORE)return;
  window.__V256_CENTER_VIEW_RESTORE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const MODES=[
    ['day','Día'],
    ['week','Semanal'],
    ['month','Mensual'],
    ['year','Anual']
  ];
  const ICONS={
    day:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M8 14h3"/></svg>',
    week:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M7 14h2M11 14h2M15 14h2"/></svg>',
    month:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M7 14h3M12 14h3M7 17h3M12 17h3"/></svg>',
    year:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v4M17 2v4M3 9h18"/><path d="M8 13h8M8 17h5"/></svg>'
  };
  const EYE='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';

  function activeButton(){
    return q('#operativoNav>button.active[data-opview]')||
           q('#operativoNav>button[aria-selected="true"][data-opview]');
  }
  function isCenter(){
    const b=activeButton();
    return String(b?.dataset?.tabKey||'')==='operations.center' ||
           String(b?.dataset?.opview||'')==='Centro Ejecutivo';
  }
  function currentMode(){
    const v=q('#operPeriodMode')?.value||'';
    if(MODES.some(x=>x[0]===v))return v;
    try{
      const saved=localStorage.getItem('operacionesRopa.centerMode.v240');
      if(MODES.some(x=>x[0]===saved))return saved;
    }catch(_){}
    return 'month';
  }
  function ensureModeOptions(){
    const sel=q('#operPeriodMode');
    if(!sel)return;
    const expected=MODES.map(x=>x[0]+'|'+x[1]).join('¦');
    const actual=[...sel.options].map(o=>o.value+'|'+o.textContent.trim()).join('¦');
    const keep=currentMode();
    if(actual!==expected){
      sel.innerHTML=MODES.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    }
    if(MODES.some(x=>x[0]===keep))sel.value=keep;
  }
  function sync(mode){
    qa('#operativoPeriodBar .v256-center-mode-btn').forEach(b=>{
      b.classList.toggle('active',b.dataset.mode===mode);
      b.setAttribute('aria-pressed',b.dataset.mode===mode?'true':'false');
    });
  }
  function ensure(){
    const bar=q('#operativoPeriodBar');
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    if(!bar||!grid)return;

    const center=isCenter();
    bar.classList.toggle('v256-center-active',center);

    let host=q(':scope > .v256-center-view',grid);
    if(!center){
      if(host)host.style.display='none';
      return;
    }

    ensureModeOptions();

    if(!host){
      host=document.createElement('div');
      host.className='v256-center-view';
      host.innerHTML=
        '<div class="v256-center-title"><span class="v256-center-title-icon">'+EYE+'</span><span>Vista operativa</span></div>'+
        '<div class="v256-center-buttons">'+
          MODES.map(x=>'<button type="button" class="v256-center-mode-btn" data-mode="'+x[0]+'" aria-pressed="false">'+
            '<span class="v256-center-mode-icon">'+ICONS[x[0]]+'</span><span>'+x[1]+'</span></button>').join('')+
        '</div>';
      grid.insertBefore(host,grid.firstElementChild||null);
    }
    host.style.removeProperty('display');
    sync(currentMode());
  }

  document.addEventListener('click',async e=>{
    const btn=e.target.closest?.('#operativoPeriodBar .v256-center-mode-btn');
    if(!btn||!isCenter())return;
    e.preventDefault();
    e.stopImmediatePropagation();

    const mode=String(btn.dataset.mode||'month');
    const sel=q('#operPeriodMode');
    ensureModeOptions();
    if(sel)sel.value=mode;
    sync(mode);

    try{
      localStorage.setItem('operacionesRopa.centerMode.v240',mode);
    }catch(_){}

    try{
      if(typeof window.V240_renderCenter==='function'){
        await window.V240_renderCenter(mode,true);
      }else if(sel){
        sel.dispatchEvent(new Event('change',{bubbles:true}));
      }
    }catch(err){
      console.error('[V256] cambiar Vista operativa',err);
    }finally{
      setTimeout(ensure,0);
      setTimeout(ensure,120);
    }
  },true);

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button[data-opview]')){
      [0,50,160,450].forEach(ms=>setTimeout(ensure,ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(['operPeriodMode','operPeriodSelect','operStoreSelect'].includes(e.target?.id||'')){
      setTimeout(ensure,0);
      setTimeout(ensure,100);
    }
  },false);

  let queued=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(queued);
    queued=setTimeout(ensure,20);
  });

  function start(){
    const bar=q('#operativoPeriodBar'),nav=q('#operativoNav');
    if(bar)observer.observe(bar,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
    if(nav)observer.observe(nav,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected']});
    ensure();
    [100,350,900,1800].forEach(ms=>setTimeout(ensure,ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V256] Vista operativa del Centro restaurada y conectada a V240.');
})();
</script>'''

    @m.app.middleware("http")
    async def v256_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v256-center-view-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v256-center-view-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V256-CENTER-VIEW",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V256] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V256_CENTER_VIEW_RESTORE = True
    print("[V256] Vista operativa Centro restaurada.",flush=True)
