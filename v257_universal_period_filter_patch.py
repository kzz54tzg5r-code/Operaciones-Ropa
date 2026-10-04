"""V257 · Vista operativa universal + alineación de Restablecer.

Extiende el selector visual Día/Semanal/Mensual/Anual a todas las pestañas
operativas cuyo backend ya soporta selección de periodo. Respeta los perfiles:
- fullperiod: Día / Semanal / Mensual / Anual
- productivityperiod: Día / Semanal / Mensual
- flex: Semanal / Mensual
También normaliza el botón de Restablecer para que quede alineado con Consultar.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V257_UNIVERSAL_PERIOD_FILTER", False):
        return

    css = r'''<style id="v257-universal-period-css">
/* V257 reemplaza los selectores rápidos heredados por uno único y consistente. */
#operativoPeriodBar.v257-universal-period .v250-quick-period,
#operativoPeriodBar.v257-universal-period .v256-center-view{
  display:none!important;
}

#operativoPeriodBar .v257-period-view{
  display:none;
}
#operativoPeriodBar.v257-universal-period .v257-period-view{
  order:-10!important;
  display:flex!important;
  flex:1.45 1 350px!important;
  min-width:320px!important;
  width:auto!important;
  max-width:none!important;
  flex-direction:column!important;
  gap:5px!important;
  margin:0!important;
  padding:0!important;
  align-self:flex-end!important;
  box-sizing:border-box!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-title{
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
#operativoPeriodBar.v257-universal-period .v257-period-title-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-title-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-buttons{
  display:grid!important;
  grid-template-columns:repeat(var(--v257-mode-count,4),minmax(0,1fr))!important;
  width:100%!important;
  min-width:0!important;
  min-height:48px!important;
  height:48px!important;
  overflow:hidden!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  background:#fff!important;
  box-shadow:0 1px 0 rgba(255,255,255,.85) inset!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-btn{
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
#operativoPeriodBar.v257-universal-period .v257-period-btn:last-child{
  border-right:0!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-btn:hover{
  background:#f4f9ff!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-btn.active{
  color:#fff!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.16)!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
#operativoPeriodBar.v257-universal-period .v257-period-mode-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}

/* Una sola línea limpia y espaciado consistente en todas las pestañas. */
#operativoPeriodBar.v250-option9b > .or-report-filter-grid{
  align-items:flex-end!important;
  column-gap:10px!important;
  row-gap:0!important;
  padding-right:4px!important;
  box-sizing:border-box!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodSelectWrap{
  flex:1 1 230px!important;
  min-width:190px!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operStoreWrap{
  flex:1.05 1 250px!important;
  min-width:200px!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
  order:20!important;
  flex:.8 1 190px!important;
  min-width:170px!important;
  align-self:flex-end!important;
  margin:0!important;
  transform:none!important;
}

/* Restablecer: centrado, separado del borde y exactamente alineado con Consultar. */
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
  box-shadow:0 1px 0 rgba(255,255,255,.88) inset,0 2px 6px rgba(18,63,115,.06)!important;
  line-height:0!important;
  vertical-align:middle!important;
  transform:none!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters:hover{
  border-color:#438fdd!important;
  background:#f7fbff!important;
  transform:none!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters svg{
  display:block!important;
  position:static!important;
  width:21px!important;
  height:21px!important;
  margin:0!important;
  padding:0!important;
  transform:none!important;
  overflow:visible!important;
}

/* Comercial usa el mismo acomodo del icono. */
html body #globalFilters.v250-option9b #v254CommercialReset{
  display:inline-grid!important;
  place-items:center!important;
  align-self:end!important;
  width:48px!important;
  min-width:48px!important;
  max-width:48px!important;
  height:48px!important;
  min-height:48px!important;
  max-height:48px!important;
  padding:0!important;
  margin:0 3px 0 2px!important;
  box-sizing:border-box!important;
  line-height:0!important;
  transform:none!important;
}
html body #globalFilters.v250-option9b #v254CommercialReset svg{
  display:block!important;
  width:21px!important;
  height:21px!important;
  margin:0!important;
  transform:none!important;
}

@media(max-width:1050px){
  #operativoPeriodBar.v257-universal-period .v257-period-view{
    flex:0 0 330px!important;
    min-width:330px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
    flex:0 0 165px!important;
    min-width:165px!important;
  }
}

@media(max-width:650px){
  #operativoPeriodBar.v257-universal-period .v257-period-view{
    flex:0 0 288px!important;
    min-width:288px!important;
  }
  #operativoPeriodBar.v257-universal-period .v257-period-buttons{
    min-height:42px!important;
    height:42px!important;
  }
  #operativoPeriodBar.v257-universal-period .v257-period-btn{
    min-height:42px!important;
    height:42px!important;
    gap:4px!important;
    padding:0 5px!important;
    font-size:8px!important;
  }
  #operativoPeriodBar.v257-universal-period .v257-period-title{
    font-size:7.5px!important;
  }
  #operativoPeriodBar.v257-universal-period .v257-period-mode-icon{
    width:13px!important;
    height:13px!important;
    min-width:13px!important;
  }
  #operativoPeriodBar.v257-universal-period .v257-period-mode-icon svg{
    width:13px!important;
    height:13px!important;
  }
  html body #operativoPeriodBar.v250-option9b #v254ResetFilters,
  html body #globalFilters.v250-option9b #v254CommercialReset{
    flex-basis:42px!important;
    width:42px!important;
    min-width:42px!important;
    max-width:42px!important;
    height:42px!important;
    min-height:42px!important;
    max-height:42px!important;
    margin-right:2px!important;
  }
  html body #operativoPeriodBar.v250-option9b #v254ResetFilters svg,
  html body #globalFilters.v250-option9b #v254CommercialReset svg{
    width:19px!important;
    height:19px!important;
  }
}
</style>'''

    js = r'''<script id="v257-universal-period-js">
(function(){
  if(window.__V257_UNIVERSAL_PERIOD_FILTER)return;
  window.__V257_UNIVERSAL_PERIOD_FILTER=true;

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

  function activeBtn(){
    return q('#operativoNav>button.active[data-opview]')||
           q('#operativoNav>button[aria-selected="true"][data-opview]');
  }
  function activeView(){
    return String(activeBtn()?.dataset?.opview||'');
  }
  function activeKey(){
    const b=activeBtn();
    return String(b?.dataset?.tabKey||'');
  }
  function profile(view){
    if(!view||view==='Carga de datos'||view==='Metas y tiendas')return '';
    try{
      const p=typeof fixedPeriodTypeForView==='function'?fixedPeriodTypeForView(view):'';
      return MODES[p]?p:'';
    }catch(_){
      return '';
    }
  }
  function optionsFor(view){
    return MODES[profile(view)]||[];
  }
  function ensureNativeOptions(opts){
    const sel=q('#operPeriodMode');
    if(!sel||!opts.length)return '';
    const current=String(sel.value||'');
    const valid=opts.some(x=>x[0]===current);
    if(!valid){
      const globalType=(()=>{try{return String(OPER_PERIOD?.type||'')}catch(_){return''}})();
      const wanted=opts.some(x=>x[0]===globalType)?globalType:opts[0][0];
      sel.innerHTML=opts.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
      sel.value=wanted;
      return wanted;
    }
    return current;
  }
  function sync(mode){
    qa('#operativoPeriodBar .v257-period-btn').forEach(b=>{
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
    if(reset){
      reset.setAttribute('aria-label','Restablecer filtros');
      reset.setAttribute('title','Restablecer filtros');
    }

    const commercial=q('#globalFilters');
    const refresh=q('#refresh',commercial);
    const creset=q('#v254CommercialReset',commercial);
    if(commercial&&refresh&&creset&&creset.previousElementSibling!==refresh){
      refresh.insertAdjacentElement('afterend',creset);
    }
  }
  function ensure(){
    const bar=q('#operativoPeriodBar');
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    if(!bar||!grid)return;

    alignReset();

    const view=activeView();
    const opts=optionsFor(view);
    const show=opts.length>0 && !bar.classList.contains('hidden');
    bar.classList.toggle('v257-universal-period',show);

    let host=q(':scope > .v257-period-view',grid);
    if(!show){
      if(host)host.style.display='none';
      return;
    }

    const mode=ensureNativeOptions(opts);
    const signature=opts.map(x=>x.join('|')).join('¦');

    if(!host){
      host=document.createElement('div');
      host.className='v257-period-view';
      grid.insertBefore(host,grid.firstElementChild||null);
    }
    if(host.dataset.signature!==signature){
      host.dataset.signature=signature;
      host.style.setProperty('--v257-mode-count',String(opts.length));
      host.innerHTML=
        '<div class="v257-period-title"><span class="v257-period-title-icon">'+EYE+'</span><span>Vista operativa</span></div>'+
        '<div class="v257-period-buttons">'+
          opts.map(x=>'<button type="button" class="v257-period-btn" data-mode="'+x[0]+'" aria-pressed="false">'+
            '<span class="v257-period-mode-icon">'+ICONS[x[0]]+'</span><span>'+x[1]+'</span></button>').join('')+
        '</div>';
    }
    host.style.removeProperty('display');
    host.style.setProperty('--v257-mode-count',String(opts.length));
    sync(mode||opts[0][0]);
  }

  document.addEventListener('click',async e=>{
    const btn=e.target.closest?.('#operativoPeriodBar .v257-period-btn');
    if(!btn)return;

    const view=activeView();
    const key=activeKey();
    const opts=optionsFor(view);
    const mode=String(btn.dataset.mode||'');
    if(!opts.some(x=>x[0]===mode))return;

    e.preventDefault();
    e.stopImmediatePropagation();

    const sel=q('#operPeriodMode');
    if(sel){
      ensureNativeOptions(opts);
      sel.value=mode;
    }
    sync(mode);

    try{
      if(key==='operations.center' && typeof window.V240_renderCenter==='function'){
        await window.V240_renderCenter(mode,true);
      }else if(sel){
        /* El onchange nativo actualiza el selector de Fecha/Semana/Mes/Año.
           El reporte se ejecuta al pulsar Consultar, igual que el flujo aprobado. */
        sel.dispatchEvent(new Event('change',{bubbles:true}));
      }
    }catch(err){
      console.error('[V257] cambio de Vista operativa',view,err);
    }finally{
      [0,80,180].forEach(ms=>setTimeout(ensure,ms));
    }
  },true);

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button[data-opview],#operPeriodApply,#v254ResetFilters')){
      [0,50,160,420].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  document.addEventListener('change',e=>{
    if(['operPeriodMode','operPeriodSelect','operStoreSelect','operActivitySelect','operAreaSelect'].includes(e.target?.id||'')){
      [0,90].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  let queued=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(queued);
    queued=setTimeout(ensure,25);
  });

  function start(){
    const bar=q('#operativoPeriodBar'),nav=q('#operativoNav'),commercial=q('#globalFilters');
    if(bar)observer.observe(bar,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
    if(nav)observer.observe(nav,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected']});
    if(commercial)observer.observe(commercial,{subtree:true,childList:true});
    ensure();
    [100,350,900,1800].forEach(ms=>setTimeout(ensure,ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V257] Vista operativa universal y Restablecer alineado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v257_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v257-universal-period-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v257-universal-period-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V257-UNIVERSAL-PERIOD",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V257] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V257_UNIVERSAL_PERIOD_FILTER = True
    print("[V257] Vista operativa universal + reset alineado.",flush=True)
