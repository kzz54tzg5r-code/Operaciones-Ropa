"""V253 · Opción 9B completa + filtros independientes por pestaña.

Completa el diseño 9B con iconografía visible y botón Restablecer, y hace que
cada pestaña operativa conserve/aplique su propio estado de filtros sin regresar
al Centro Operativo.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V253_FILTERS_PER_TAB", False):
        return

    css = r'''<style id="v253-filters-per-tab-css">
/* ===== Opción 9B · iconografía ===== */
#operativoPeriodBar.v250-option9b .or-fcontrol label{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:17px!important;
  height:17px!important;
  min-width:17px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol-icon svg{
  width:16px!important;
  height:16px!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-title{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
}
#operativoPeriodBar.v250-option9b .v253-title-icon,
#operativoPeriodBar.v250-option9b .v253-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  flex:0 0 auto!important;
}
#operativoPeriodBar.v250-option9b .v253-title-icon{
  width:17px!important;
  height:17px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v250-option9b .v253-mode-icon{
  width:15px!important;
  height:15px!important;
}
#operativoPeriodBar.v250-option9b .v253-title-icon svg,
#operativoPeriodBar.v250-option9b .v253-mode-icon svg{
  width:100%!important;
  height:100%!important;
}
#operativoPeriodBar.v250-option9b .v250-quick-btn{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:7px!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon{
  display:inline-grid!important;
  place-items:center!important;
  flex:0 0 18px!important;
  width:18px!important;
  height:18px!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon svg{
  width:18px!important;
  height:18px!important;
}

/* ===== Restablecer ===== */
#operativoPeriodBar.v250-option9b #v253ResetFilters{
  order:21!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:7px!important;
  flex:.58 1 138px!important;
  min-width:128px!important;
  width:auto!important;
  max-width:none!important;
  height:48px!important;
  min-height:48px!important;
  margin:0!important;
  padding:8px 12px!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  color:#164a82!important;
  background:rgba(255,255,255,.9)!important;
  font-size:11px!important;
  font-weight:900!important;
  box-shadow:0 1px 0 rgba(255,255,255,.8) inset!important;
  cursor:pointer!important;
  white-space:nowrap!important;
}
#operativoPeriodBar.v250-option9b #v253ResetFilters:hover{
  border-color:#438fdd!important;
  background:#fff!important;
  transform:translateY(-1px);
}
#operativoPeriodBar.v250-option9b #v253ResetFilters svg{
  width:17px!important;
  height:17px!important;
}

/* Ajuste final para que 9B quepa en UNA sola línea en PC. */
@media(min-width:1051px){
  #operativoPeriodBar.v250-option9b .v250-quick-period{
    flex:1.45 1 310px!important;
    min-width:275px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodSelectWrap{
    flex:.88 1 170px!important;
    min-width:145px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operStoreWrap{
    flex:1 1 185px!important;
    min-width:155px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operActivityWrap{
    flex:.9 1 175px!important;
    min-width:150px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid > #operPeriodApply{
    flex:.62 1 135px!important;
    min-width:125px!important;
  }
}

/* En tablet/móvil se mantiene una sola línea con scroll-X fluido. */
@media(max-width:1050px){
  #operativoPeriodBar.v250-option9b #v253ResetFilters{
    flex:0 0 130px!important;
    min-width:130px!important;
  }
}
@media(max-width:650px){
  #operativoPeriodBar.v250-option9b #v253ResetFilters{
    flex:0 0 118px!important;
    min-width:118px!important;
    height:42px!important;
    min-height:42px!important;
    font-size:9px!important;
  }
}

/* Análisis Comercial: iconos + Restablecer con el mismo lenguaje 9B. */
#globalFilters.v250-option9b .filter label{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
}
#globalFilters.v250-option9b .v253-commercial-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#globalFilters.v250-option9b .v253-commercial-icon svg{
  width:15px!important;
  height:15px!important;
}
#globalFilters.v250-option9b #v253CommercialReset{
  min-height:48px!important;
  height:48px!important;
  padding:8px 12px!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  color:#164a82!important;
  background:#fff!important;
  font-size:11px!important;
  font-weight:900!important;
  cursor:pointer!important;
}
</style>'''

    js = r'''<script id="v253-filters-per-tab-js">
(function(){
  if(window.__V253_FILTERS_PER_TAB)return;
  window.__V253_FILTERS_PER_TAB=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  const ICON={
    view:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>',
    day:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M8 14h3"/></svg>',
    week:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M7 14h2M11 14h2M15 14h2"/></svg>',
    month:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M7 14h3M12 14h3M7 17h3M12 17h3"/></svg>',
    year:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v4M17 2v4M3 9h18"/><path d="M8 13h8M8 17h5"/></svg>',
    reset:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v6h6"/></svg>',
    calendar:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>',
    store:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/></svg>',
    section:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/></svg>',
    tag:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13 11 22l-9-9V4h9l9 9Z"/><circle cx="7" cy="9" r="1.5"/></svg>'
  };

  const opStates=new Map();
  const opDefaults=new Map();
  let suppressState=false;

  function activeOpButton(){
    return q('#operativoNav>button.active[data-opview]')||
      q('#operativoNav>button[aria-selected="true"][data-opview]');
  }
  function keyForView(view){
    return q('#operativoNav>button[data-opview="'+String(view||'').replace(/"/g,'\\"')+'"]')?.dataset?.tabKey||'';
  }
  function viewForKey(key){
    return q('#operativoNav>button[data-tab-key="'+String(key||'').replace(/"/g,'\\"')+'"]')?.dataset?.opview||'';
  }
  function currentKey(){return String(activeOpButton()?.dataset?.tabKey||'')}
  function currentView(){return String(activeOpButton()?.dataset?.opview||'')}

  function readOpState(){
    return {
      mode:q('#operPeriodMode')?.value||'',
      period:q('#operPeriodSelect')?.value||'',
      store:q('#operStoreSelect')?.value||'Compañía',
      area:q('#operAreaSelect')?.value||'',
      activity:q('#operActivitySelect')?.value||''
    };
  }
  function setSelectValue(el,value){
    if(!el)return;
    const v=String(value??'');
    if([...el.options].some(o=>o.value===v))el.value=v;
  }
  function primeOpState(state){
    if(!state)return;
    const mode=q('#operPeriodMode'),store=q('#operStoreSelect'),area=q('#operAreaSelect'),activity=q('#operActivitySelect');
    setSelectValue(mode,state.mode);
    setSelectValue(store,state.store);
    setSelectValue(area,state.area);
    setSelectValue(activity,state.activity);
    try{
      OPER_PERIOD.type=state.mode||OPER_PERIOD.type;
      OPER_PERIOD.value=state.period||'';
    }catch(_){}
  }
  function restoreOpVisual(state){
    if(!state)return;
    suppressState=true;
    try{
      setSelectValue(q('#operPeriodMode'),state.mode);
      setSelectValue(q('#operPeriodSelect'),state.period);
      setSelectValue(q('#operStoreSelect'),state.store);
      setSelectValue(q('#operAreaSelect'),state.area);
      setSelectValue(q('#operActivitySelect'),state.activity);
      try{
        OPER_PERIOD.type=state.mode||OPER_PERIOD.type;
        OPER_PERIOD.value=state.period||'';
      }catch(_){}
      qa('#operativoPeriodBar .v250-quick-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
    }finally{
      suppressState=false;
    }
  }
  function saveCurrentOp(){
    if(suppressState)return;
    const key=currentKey();
    if(!key||key==='operations.goals')return;
    opStates.set(key,readOpState());
  }
  function establishDefault(key){
    if(!key||opDefaults.has(key))return;
    const st=readOpState();
    opDefaults.set(key,{...st});
    if(!opStates.has(key))opStates.set(key,{...st});
  }

  function enhanceQuickIcons(){
    const quick=q('#operativoPeriodBar .v250-quick-period');
    if(!quick)return;
    const title=q('.v250-quick-title',quick);
    if(title&&!q('.v253-title-icon',title)){
      title.insertAdjacentHTML('afterbegin','<span class="v253-title-icon">'+ICON.view+'</span>');
    }
    qa('.v250-quick-btn',quick).forEach(btn=>{
      if(q('.v253-mode-icon',btn))return;
      const mode=btn.dataset.mode||'month';
      btn.insertAdjacentHTML('afterbegin','<span class="v253-mode-icon">'+(ICON[mode]||ICON.calendar)+'</span>');
    });
  }

  function ensureOpReset(){
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    const apply=q('#operPeriodApply',grid);
    if(!grid||!apply)return;
    let btn=q('#v253ResetFilters',grid);
    if(!btn){
      btn=document.createElement('button');
      btn.type='button';
      btn.id='v253ResetFilters';
      btn.innerHTML=ICON.reset+'<span>Restablecer</span>';
      apply.insertAdjacentElement('afterend',btn);
    }
  }

  function ensureCommercialIcons(){
    const bar=q('#globalFilters');
    if(!bar)return;
    const icons={
      globalPeriodLabel:ICON.calendar,
      globalStoreFilter:ICON.store,
      globalSectionFilter:ICON.section,
      globalCatalogFilter:ICON.tag
    };
    qa(':scope > .filter',bar).forEach(box=>{
      const label=q('label',box);
      if(!label||q('.v253-commercial-icon',label))return;
      let svg=ICON.section;
      if(label.id==='globalPeriodLabel')svg=ICON.calendar;
      else if(box.id==='globalStoreFilter')svg=ICON.store;
      else if(box.id==='globalCatalogFilter')svg=ICON.tag;
      label.insertAdjacentHTML('afterbegin','<span class="v253-commercial-icon">'+svg+'</span>');
    });
    const refresh=q('#refresh',bar);
    if(refresh&&!q('#v253CommercialReset',bar)){
      const b=document.createElement('button');
      b.type='button';
      b.id='v253CommercialReset';
      b.textContent='Restablecer';
      refresh.insertAdjacentElement('afterend',b);
    }
  }

  function enhance(){
    ensureOpReset();
    enhanceQuickIcons();
    ensureCommercialIcons();
  }

  /* Guardar/restaurar por pestaña alrededor del render real. */
  const previousRender=window.renderOperativoView;
  if(typeof previousRender==='function'){
    window.renderOperativoView=async function(name,force=false){
      const key=keyForView(name);
      const remembered=key?opStates.get(key):null;
      if(remembered&&key!=='operations.center')primeOpState(remembered);
      const out=await previousRender.apply(this,arguments);
      if(key){
        if(remembered){
          restoreOpVisual(remembered);
          [40,180].forEach(ms=>setTimeout(()=>restoreOpVisual(opStates.get(key)),ms));
        }else{
          establishDefault(key);
        }
      }
      enhance();
      return out;
    };
  }

  /* Consultar: cada pestaña usa exclusivamente sus propios filtros. */
  document.addEventListener('click',async e=>{
    const apply=e.target.closest?.('#operPeriodApply');
    if(apply){
      const key=currentKey();
      if(key&&key!=='operations.center'){
        e.preventDefault();
        e.stopImmediatePropagation();
        const view=currentView();
        const st=readOpState();
        opStates.set(key,{...st});
        try{
          OP_VIEW=view;
          OPER_PERIOD.type=st.mode||currentPeriodTypeForView(view);
          OPER_PERIOD.value=st.period||'';
        }catch(_){}
        qa('#operativoNav>button[data-opview]').forEach(b=>{
          const on=b.dataset.tabKey===key;
          b.classList.toggle('active',on);
          b.setAttribute('aria-selected',on?'true':'false');
        });
        if(typeof renderOperativoView==='function'){
          await renderOperativoView(view,true);
        }
        return;
      }
    }

    const reset=e.target.closest?.('#v253ResetFilters');
    if(reset){
      e.preventDefault();
      e.stopImmediatePropagation();
      const key=currentKey(),view=currentView();
      if(!key)return;

      if(key==='operations.center'){
        try{localStorage.removeItem('operacionesRopa.centerMode.v240')}catch(_){}
        const store=q('#operStoreSelect'); if(store)setSelectValue(store,'Compañía');
        const mode=q('#operPeriodMode');
        if(mode){
          setSelectValue(mode,'month');
          mode.dispatchEvent(new Event('change',{bubbles:true}));
        }
        return;
      }

      let def=opDefaults.get(key);
      if(!def){
        def={...readOpState(),store:'Compañía',area:'',activity:'',period:''};
      }
      opStates.set(key,{...def});
      primeOpState(def);
      restoreOpVisual(def);
      try{
        OP_VIEW=view;
        OPER_PERIOD.type=def.mode||currentPeriodTypeForView(view);
        OPER_PERIOD.value=def.period||'';
      }catch(_){}
      if(typeof renderOperativoView==='function')await renderOperativoView(view,true);
      return;
    }

    const commercialReset=e.target.closest?.('#v253CommercialReset');
    if(commercialReset){
      e.preventDefault();
      const store=q('#store'),section=q('#section'),catalog=q('#catalog'),week=q('#week');
      if(store)setSelectValue(store,'Compañía');
      if(section)setSelectValue(section,'Todas');
      if(catalog)setSelectValue(catalog,'Todos');
      if(week&&week.options.length)week.selectedIndex=0;
      q('#refresh')?.click();
      return;
    }

    const tab=e.target.closest?.('#operativoNav>button[data-opview]');
    if(tab){
      const outgoing=currentKey();
      if(outgoing&&outgoing!==tab.dataset.tabKey)saveCurrentOp();
      const targetKey=String(tab.dataset.tabKey||'');
      [0,80,260,700].forEach(ms=>setTimeout(()=>{
        const st=opStates.get(targetKey);
        if(st)restoreOpVisual(st);
        enhance();
      },ms));
    }
  },true);

  /* Al cambiar controles, guardar sólo el estado de la pestaña activa. */
  document.addEventListener('change',e=>{
    if(suppressState)return;
    const id=e.target?.id||'';
    if(['operPeriodMode','operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect'].includes(id)){
      setTimeout(()=>{
        const key=currentKey();
        if(key)opStates.set(key,readOpState());
        enhanceQuickIcons();
      },0);
    }
  },false);

  const observer=new MutationObserver(()=>setTimeout(enhance,0));
  function start(){
    const bar=q('#operativoPeriodBar');
    const commercial=q('#globalFilters');
    if(bar)observer.observe(bar,{subtree:true,childList:true});
    if(commercial)observer.observe(commercial,{subtree:true,childList:true});
    enhance();
    const key=currentKey();
    if(key){
      establishDefault(key);
      opStates.set(key,readOpState());
    }
    [120,400,1000].forEach(ms=>setTimeout(enhance,ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V253] 9B completa: iconos, Restablecer y filtros independientes por pestaña.');
})();
</script>'''

    @m.app.middleware("http")
    async def v253_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v253-filters-per-tab-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v253-filters-per-tab-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V253-FILTERS-PER-TAB",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V253] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V253_FILTERS_PER_TAB = True
    print("[V253] Opción 9B completa + filtros por pestaña instalada.",flush=True)
