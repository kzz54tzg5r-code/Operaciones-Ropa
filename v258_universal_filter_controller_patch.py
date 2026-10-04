"""V258 · controlador único de Vista operativa.

Corrige la regresión observada en video:
- el selector aparecía al entrar a Conversión y desaparecía después de pulsarlo;
- fuera de Centro Operativo el cambio de vista no ejecutaba el reporte;
- V250/V256/V257 competían por reconstruir la misma fila.

V258 se convierte en la única capa visual/funcional para Día/Semanal/Mensual/Anual.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V258_UNIVERSAL_FILTER", False):
        return

    css = r'''<style id="v258-universal-filter-css">
#operativoPeriodBar.v258-universal-period .v250-quick-period,
#operativoPeriodBar.v258-universal-period .v256-center-view,
#operativoPeriodBar.v258-universal-period .v257-period-view,
#operativoPeriodBar.v258-universal-period #operPeriodModeWrap{
  display:none!important;
}

#operativoPeriodBar .v258-period-view{
  display:none;
}
#operativoPeriodBar.v258-universal-period .v258-period-view{
  order:-10!important;
  display:flex!important;
  flex:1.48 1 360px!important;
  min-width:330px!important;
  width:auto!important;
  max-width:none!important;
  flex-direction:column!important;
  gap:5px!important;
  margin:0!important;
  padding:0!important;
  align-self:flex-end!important;
  box-sizing:border-box!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-title{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
  height:14px!important;
  min-height:14px!important;
  margin:0!important;
  color:#294b70!important;
  font-size:9px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.025em!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-title-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-title-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-buttons{
  display:grid!important;
  grid-template-columns:repeat(var(--v258-mode-count,4),minmax(0,1fr))!important;
  width:100%!important;
  min-height:48px!important;
  height:48px!important;
  overflow:hidden!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  background:#fff!important;
  box-shadow:0 1px 0 rgba(255,255,255,.85) inset!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-btn{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  min-width:0!important;
  min-height:48px!important;
  height:48px!important;
  margin:0!important;
  padding:0 9px!important;
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
  transform:none!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-btn:last-child{
  border-right:0!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-btn:hover{
  background:#f4f9ff!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-btn.active{
  color:#fff!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.16)!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
#operativoPeriodBar.v258-universal-period .v258-period-mode-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}

/* Mantener toda la fila en línea y el reset bien centrado. */
#operativoPeriodBar.v250-option9b > .or-report-filter-grid{
  align-items:flex-end!important;
  column-gap:10px!important;
  row-gap:0!important;
  padding-right:6px!important;
  box-sizing:border-box!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters{
  order:21!important;
  display:inline-grid!important;
  place-items:center!important;
  align-self:flex-end!important;
  flex:0 0 48px!important;
  width:48px!important;
  min-width:48px!important;
  max-width:48px!important;
  height:48px!important;
  min-height:48px!important;
  max-height:48px!important;
  padding:0!important;
  margin:0 3px 0 2px!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  box-sizing:border-box!important;
  color:#164a82!important;
  background:#fff!important;
  line-height:0!important;
  transform:none!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters svg{
  display:block!important;
  width:21px!important;
  height:21px!important;
  margin:0!important;
  position:static!important;
  transform:none!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
  align-self:flex-end!important;
  transform:none!important;
}

@media(max-width:1050px){
  #operativoPeriodBar.v258-universal-period .v258-period-view{
    flex:0 0 330px!important;
    min-width:330px!important;
  }
}
@media(max-width:650px){
  #operativoPeriodBar.v258-universal-period .v258-period-view{
    flex:0 0 288px!important;
    min-width:288px!important;
  }
  #operativoPeriodBar.v258-universal-period .v258-period-buttons{
    min-height:42px!important;
    height:42px!important;
  }
  #operativoPeriodBar.v258-universal-period .v258-period-btn{
    min-height:42px!important;
    height:42px!important;
    gap:4px!important;
    padding:0 5px!important;
    font-size:8px!important;
  }
  #operativoPeriodBar.v258-universal-period .v258-period-title{
    font-size:7.5px!important;
  }
  #operativoPeriodBar.v258-universal-period .v258-period-mode-icon{
    width:13px!important;
    height:13px!important;
    min-width:13px!important;
  }
  #operativoPeriodBar.v258-universal-period .v258-period-mode-icon svg{
    width:13px!important;
    height:13px!important;
  }
  html body #operativoPeriodBar.v250-option9b #v254ResetFilters{
    flex-basis:42px!important;
    width:42px!important;
    min-width:42px!important;
    max-width:42px!important;
    height:42px!important;
    min-height:42px!important;
    max-height:42px!important;
  }
}
</style>'''

    js = r'''<script id="v258-universal-filter-js">
(function(){
  if(window.__V258_UNIVERSAL_FILTER)return;
  window.__V258_UNIVERSAL_FILTER=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  const MODES={
    fullperiod:[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']],
    productivityperiod:[['day','Día'],['week','Semanal'],['month','Mensual']],
    flex:[['week','Semanal'],['month','Mensual']]
  };
  const ICONS={
    day:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M8 14h3"/></svg>',
    week:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M7 14h2M11 14h2M15 14h2"/></svg>',
    month:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M7 14h3M12 14h3M7 17h3M12 17h3"/></svg>',
    year:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v4M17 2v4M3 9h18"/><path d="M8 13h8M8 17h5"/></svg>'
  };
  const EYE='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';

  let lastView='';
  let lastKey='';
  let rendering=false;

  function activeBtn(){
    return q('#operativoNav>button.active[data-opview]')||
           q('#operativoNav>button[aria-selected="true"][data-opview]');
  }
  function context(){
    const b=activeBtn();
    if(b){
      const view=String(b.dataset.opview||'');
      const key=String(b.dataset.tabKey||('view:'+view));
      lastView=view;
      lastKey=key;
      return {view,key};
    }
    return {view:lastView,key:lastKey};
  }
  function profile(view){
    if(!view||view==='Carga de datos'||view==='Metas y tiendas')return '';
    try{
      const p=typeof fixedPeriodTypeForView==='function'?fixedPeriodTypeForView(view):'';
      return MODES[p]?p:'';
    }catch(_){return ''}
  }
  function optionsFor(view){
    return MODES[profile(view)]||[];
  }
  function currentMode(opts){
    const sel=q('#operPeriodMode');
    const v=String(sel?.value||'');
    if(opts.some(x=>x[0]===v))return v;
    try{
      const gp=String(OPER_PERIOD?.type||'');
      if(opts.some(x=>x[0]===gp))return gp;
    }catch(_){}
    return opts[0]?.[0]||'';
  }
  function setNativeMode(opts,mode){
    const sel=q('#operPeriodMode');
    if(!sel||!opts.length)return;
    const signature=opts.map(x=>x[0]+'|'+x[1]).join('¦');
    const current=[...sel.options].map(o=>o.value+'|'+o.textContent.trim()).join('¦');
    if(current!==signature){
      sel.innerHTML=opts.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    }
    if(opts.some(x=>x[0]===mode))sel.value=mode;
  }
  function sync(mode){
    qa('#operativoPeriodBar .v258-period-btn').forEach(b=>{
      const on=b.dataset.mode===mode;
      b.classList.toggle('active',on);
      b.setAttribute('aria-pressed',on?'true':'false');
    });
  }
  function alignReset(){
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    const apply=q('#operPeriodApply',grid);
    const reset=q('#v254ResetFilters',grid);
    if(grid&&apply&&reset&&reset.previousElementSibling!==apply){
      apply.insertAdjacentElement('afterend',reset);
    }
  }
  function ensure(){
    const bar=q('#operativoPeriodBar');
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    if(!bar||!grid)return;

    alignReset();

    const {view}=context();
    const opts=optionsFor(view);
    const activeHasProfile=opts.length>0;

    if(!activeHasProfile){
      bar.classList.remove('v258-universal-period');
      const old=q(':scope > .v258-period-view',grid);
      if(old)old.style.display='none';
      return;
    }

    bar.classList.remove('hidden');
    bar.classList.add('v258-universal-period');

    let mode=currentMode(opts);
    if(!mode)mode=opts[0][0];
    setNativeMode(opts,mode);

    let host=q(':scope > .v258-period-view',grid);
    if(!host){
      host=document.createElement('div');
      host.className='v258-period-view';
      grid.insertBefore(host,grid.firstElementChild||null);
    }

    const signature=opts.map(x=>x.join('|')).join('¦');
    if(host.dataset.signature!==signature){
      host.dataset.signature=signature;
      host.style.setProperty('--v258-mode-count',String(opts.length));
      host.innerHTML=
        '<div class="v258-period-title"><span class="v258-period-title-icon">'+EYE+'</span><span>Vista operativa</span></div>'+
        '<div class="v258-period-buttons">'+
          opts.map(x=>'<button type="button" class="v258-period-btn" data-mode="'+x[0]+'" aria-pressed="false">'+
            '<span class="v258-period-mode-icon">'+ICONS[x[0]]+'</span><span>'+x[1]+'</span></button>').join('')+
        '</div>';
    }
    host.style.removeProperty('display');
    host.style.setProperty('--v258-mode-count',String(opts.length));
    sync(mode);
  }

  async function applyMode(mode){
    if(rendering)return;
    const {view,key}=context();
    const opts=optionsFor(view);
    if(!opts.some(x=>x[0]===mode))return;

    rendering=true;
    try{
      setNativeMode(opts,mode);
      try{
        if(typeof OPER_PERIOD==='object'&&OPER_PERIOD){
          OPER_PERIOD.type=mode;
          OPER_PERIOD.value='';
        }
      }catch(_){}

      /* Actualiza Fecha/Semana/Mes/Año sin disparar los handlers heredados
         que eliminaban el selector. */
      if(typeof setPeriodSelector==='function'){
        setPeriodSelector(view,window.OPSDATA||{
          available_dates:[],available_weeks:[],available_months:[],available_years:[]
        });
      }
      try{
        if(typeof resolveOpsPeriod==='function')await resolveOpsPeriod(mode);
      }catch(_){}

      sync(mode);

      /* Centro usa su controlador especializado. Los demás usan el mismo
         render real del reporte, por lo que el filtro funciona al instante. */
      if(key==='operations.center'&&typeof window.V240_renderCenter==='function'){
        await window.V240_renderCenter(mode,false);
      }else if(typeof window.renderOperativoView==='function'){
        await window.renderOperativoView(view,true);
      }
    }catch(err){
      console.error('[V258] aplicar Vista operativa',view,mode,err);
      const host=q('#operativoDynamicContent');
      if(host&&!host.innerHTML.trim()){
        host.innerHTML='<div class="infoempty">No fue posible cambiar la vista del reporte.</div>';
      }
    }finally{
      rendering=false;
      [0,40,120,300,700].forEach(ms=>setTimeout(ensure,ms));
    }
  }

  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#operativoPeriodBar .v258-period-btn');
    if(!btn)return;
    e.preventDefault();
    e.stopImmediatePropagation();
    applyMode(String(btn.dataset.mode||''));
  },true);

  /* Al cambiar de pestaña V254 puede detener el click; observamos el estado
     real del nav y no dependemos de recibir ese evento. */
  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operPeriodApply,#v254ResetFilters')){
      [0,60,180,500].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  document.addEventListener('change',e=>{
    if(['operPeriodSelect','operStoreSelect','operActivitySelect','operAreaSelect'].includes(e.target?.id||'')){
      [0,80,200].forEach(ms=>setTimeout(ensure,ms));
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

  console.info('[V258] controlador único de Vista operativa activo.');
})();
</script>'''

    @m.app.middleware("http")
    async def v258_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v258-universal-filter-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v258-universal-filter-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V258-UNIVERSAL-FILTER",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V258] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V258_UNIVERSAL_FILTER = True
    print("[V258] controlador único de Vista operativa instalado.",flush=True)
