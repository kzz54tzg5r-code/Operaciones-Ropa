"""V254 · filtros 9B definitivos.

- Restablecer es únicamente un icono.
- Los iconos de los filtros quedan visibles.
- Cada pestaña operativa conserva su propio estado.
- Los botones Día/Semanal/Mensual/Anual y Consultar actúan sobre la pestaña
  activa, sin volver al Centro Operativo.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V254_FILTERS_FINAL", False):
        return

    css = r'''<style id="v254-filters-final-css">
/* Prioridad superior a capas anteriores de 9B. */
html body #operativoPeriodBar.v250-option9b .or-fcontrol label{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
}
html body #operativoPeriodBar.v250-option9b .or-fcontrol-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
html body #operativoPeriodBar.v250-option9b .or-fcontrol-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}
html body #operativoPeriodBar.v250-option9b .v250-quick-title{
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
}
html body #operativoPeriodBar.v250-option9b .v250-quick-btn{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
}
html body #operativoPeriodBar.v250-option9b .v254-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
html body #operativoPeriodBar.v250-option9b .v254-mode-icon svg{
  display:block!important;
  width:15px!important;
  height:15px!important;
}
html body #operativoPeriodBar.v250-option9b #operPeriodApply{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:7px!important;
}
html body #operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:18px!important;
  height:18px!important;
  min-width:18px!important;
}
html body #operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon svg{
  display:block!important;
  width:18px!important;
  height:18px!important;
}

/* Restablecer = icono únicamente. */
html body #operativoPeriodBar.v250-option9b #v254ResetFilters{
  order:21!important;
  display:grid!important;
  place-items:center!important;
  flex:0 0 50px!important;
  width:50px!important;
  min-width:50px!important;
  max-width:50px!important;
  height:48px!important;
  min-height:48px!important;
  padding:0!important;
  margin:0!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  color:#164a82!important;
  background:#fff!important;
  box-shadow:0 1px 0 rgba(255,255,255,.85) inset!important;
  cursor:pointer!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters:hover{
  border-color:#438fdd!important;
  background:#f8fbff!important;
  transform:translateY(-1px);
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters svg{
  display:block!important;
  width:20px!important;
  height:20px!important;
}

/* Oculta el botón textual de V253 si una caché vieja llegara a conservarlo. */
html body #operativoPeriodBar #v253ResetFilters{display:none!important}

/* Comercial: mismo criterio para restablecer. */
html body #globalFilters.v250-option9b #v254CommercialReset{
  display:grid!important;
  place-items:center!important;
  flex:0 0 50px!important;
  width:50px!important;
  min-width:50px!important;
  max-width:50px!important;
  height:48px!important;
  min-height:48px!important;
  padding:0!important;
  margin:0!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  color:#164a82!important;
  background:#fff!important;
  cursor:pointer!important;
}
html body #globalFilters.v250-option9b #v254CommercialReset svg{
  display:block!important;
  width:20px!important;
  height:20px!important;
}
html body #globalFilters #v253CommercialReset{display:none!important}

@media(max-width:650px){
  html body #operativoPeriodBar.v250-option9b #v254ResetFilters,
  html body #globalFilters.v250-option9b #v254CommercialReset{
    flex-basis:42px!important;
    width:42px!important;
    min-width:42px!important;
    max-width:42px!important;
    height:42px!important;
    min-height:42px!important;
  }
}
</style>'''

    js = r'''<script id="v254-filters-final-js">
(function(){
  if(window.__V254_FILTERS_FINAL)return;
  window.__V254_FILTERS_FINAL=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const states=new Map();
  let busy=false;

  const RESET='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v6h6"/></svg>';

  function activeBtn(){
    return q('#operativoNav>button.active[data-opview]')||
           q('#operativoNav>button[aria-selected="true"][data-opview]');
  }
  function keyOf(btn){
    if(!btn)return '';
    return String(btn.dataset.tabKey||('view:'+String(btn.dataset.opview||btn.textContent||'')));
  }
  function activeKey(){return keyOf(activeBtn())}
  function activeView(){return String(activeBtn()?.dataset?.opview||'')}

  function setVal(el,value){
    if(!el)return false;
    const v=String(value??'');
    const ok=[...el.options].some(o=>o.value===v);
    if(ok)el.value=v;
    return ok;
  }

  function readState(){
    return {
      mode:q('#operPeriodMode')?.value||'',
      period:q('#operPeriodSelect')?.value||'',
      store:q('#operStoreSelect')?.value||'Compañía',
      area:q('#operAreaSelect')?.value||'',
      activity:q('#operActivitySelect')?.value||''
    };
  }
  function saveActive(){
    const key=activeKey();
    if(key)states.set(key,readState());
  }

  function defaultMode(view){
    try{
      const fixed=typeof fixedPeriodTypeForView==='function'?fixedPeriodTypeForView(view):'fullperiod';
      if(['day','week','month','year'].includes(fixed))return fixed;
      if(fixed==='all')return 'all';
    }catch(_){}
    return 'month';
  }
  function freshState(view){
    return {mode:defaultMode(view),period:'',store:'Compañía',area:'',activity:''};
  }

  function setGlobals(view,state){
    try{window.OP_VIEW=view}catch(_){}
    try{
      if(typeof OPER_PERIOD==='object'&&OPER_PERIOD){
        OPER_PERIOD.type=state.mode||defaultMode(view);
        OPER_PERIOD.value=state.period||'';
      }else{
        OPER_PERIOD={type:state.mode||defaultMode(view),value:state.period||''};
      }
    }catch(_){}
  }

  function prime(state,view){
    if(!state)return;
    setVal(q('#operPeriodMode'),state.mode);
    setVal(q('#operStoreSelect'),state.store);
    setVal(q('#operAreaSelect'),state.area);
    setVal(q('#operActivitySelect'),state.activity);
    setGlobals(view,state);
  }

  function syncQuick(mode){
    qa('#operativoPeriodBar .v250-quick-btn').forEach(b=>{
      b.classList.toggle('active',String(b.dataset.mode||'')===String(mode||''));
    });
  }

  function restoreVisible(state,view){
    if(!state)return;
    setVal(q('#operPeriodMode'),state.mode);
    if(state.period)setVal(q('#operPeriodSelect'),state.period);
    setVal(q('#operStoreSelect'),state.store);
    setVal(q('#operAreaSelect'),state.area);
    setVal(q('#operActivitySelect'),state.activity);
    const final=readState();
    if(!state.period)state.period=final.period;
    if(!state.mode)state.mode=final.mode;
    states.set(activeKey(),{...state,...final,mode:state.mode||final.mode,period:state.period||final.period});
    setGlobals(view,states.get(activeKey())||state);
    syncQuick((states.get(activeKey())||state).mode);
  }

  function markTab(btn){
    qa('#operativoNav>button[data-opview]').forEach(b=>{
      const on=b===btn;
      b.classList.toggle('active',on);
      b.setAttribute('aria-selected',on?'true':'false');
    });
  }

  function showLoading(view){
    const centro=q('#operativoCentro'),dyn=q('#operativoDynamic');
    if(centro)centro.classList.add('hidden');
    if(dyn)dyn.classList.remove('hidden');
    const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub'),content=q('#operativoDynamicContent');
    if(title)title.textContent=view;
    if(sub)sub.textContent='Cargando información...';
    if(content)content.innerHTML='<div class="infoempty">Cargando reporte...</div>';
  }

  function ensureReset(){
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    const apply=q('#operPeriodApply',grid);
    if(grid&&apply){
      let old=q('#v253ResetFilters',grid); if(old)old.remove();
      let btn=q('#v254ResetFilters',grid);
      if(!btn){
        btn=document.createElement('button');
        btn.type='button';
        btn.id='v254ResetFilters';
        btn.setAttribute('aria-label','Restablecer filtros');
        btn.setAttribute('title','Restablecer filtros');
        btn.innerHTML=RESET;
        apply.insertAdjacentElement('afterend',btn);
      }
    }

    const commercial=q('#globalFilters');
    const refresh=q('#refresh',commercial);
    if(commercial&&refresh){
      let old=q('#v253CommercialReset',commercial); if(old)old.remove();
      let btn=q('#v254CommercialReset',commercial);
      if(!btn){
        btn=document.createElement('button');
        btn.type='button';
        btn.id='v254CommercialReset';
        btn.setAttribute('aria-label','Restablecer filtros');
        btn.setAttribute('title','Restablecer filtros');
        btn.innerHTML=RESET;
        refresh.insertAdjacentElement('afterend',btn);
      }
    }
  }

  function ensureIcons(){
    ensureReset();
    /* Los SVG de cada campo ya existen en el HTML; V254 fuerza su visibilidad.
       Si Vista fue regenerada por V250, sus iconos vienen embebidos allí. */
  }

  async function renderTab(btn){
    if(!btn||busy)return;
    busy=true;
    try{
      saveActive();
      const key=keyOf(btn);
      const view=String(btn.dataset.opview||'');
      const state=states.get(key)||freshState(view);

      markTab(btn);
      prime(state,view);
      showLoading(view);

      if(view==='Metas y tiendas'&&typeof renderGoalsConfig==='function'){
        await renderGoalsConfig();
        return;
      }

      if(typeof renderOperativoView==='function'){
        await renderOperativoView(view,false);
      }

      /* setPeriodSelector se ejecuta dentro de renderOperativoView.
         Aquí reaplicamos sólo el estado propio de ESTA pestaña. */
      restoreVisible(state,view);
      ensureIcons();
      [40,140].forEach(ms=>setTimeout(()=>{
        if(activeKey()===key){
          restoreVisible(states.get(key)||state,view);
          ensureIcons();
        }
      },ms));
    }catch(err){
      console.error('[V254] abrir pestaña',err);
      const content=q('#operativoDynamicContent');
      if(content)content.innerHTML='<div class="infoempty">No fue posible abrir el reporte: '+String(err&&err.message||err)+'</div>';
    }finally{
      busy=false;
    }
  }

  function changeMode(mode){
    const view=activeView(),key=activeKey();
    if(!view||!key)return;
    let st=states.get(key)||readState();
    st={...st,mode:String(mode||'month'),period:''};
    states.set(key,st);
    setVal(q('#operPeriodMode'),st.mode);
    setGlobals(view,st);

    try{
      if(typeof setPeriodSelector==='function'){
        setPeriodSelector(view,window.OPSDATA||{available_dates:[],available_weeks:[],available_months:[],available_years:[]});
      }
    }catch(err){console.warn('[V254] selector periodo',err)}

    st={...st,...readState(),mode:st.mode};
    states.set(key,st);
    setGlobals(view,st);
    syncQuick(st.mode);
    ensureIcons();
  }

  async function consultActive(){
    if(busy)return;
    const btn=activeBtn();
    if(!btn)return;
    const view=String(btn.dataset.opview||''),key=keyOf(btn);
    const st=readState();
    states.set(key,st);
    setGlobals(view,st);
    busy=true;
    try{
      if(typeof renderOperativoView==='function')await renderOperativoView(view,true);
      restoreVisible(states.get(key)||st,view);
      ensureIcons();
    }catch(err){
      console.error('[V254] consultar',view,err);
      const content=q('#operativoDynamicContent');
      if(content)content.innerHTML='<div class="infoempty">Error al consultar '+view+': '+String(err&&err.message||err)+'</div>';
    }finally{
      busy=false;
    }
  }

  async function resetActive(){
    const btn=activeBtn();
    if(!btn)return;
    const key=keyOf(btn),view=String(btn.dataset.opview||'');
    const st=freshState(view);
    states.set(key,st);
    prime(st,view);
    try{
      if(typeof setPeriodSelector==='function'){
        setPeriodSelector(view,window.OPSDATA||{available_dates:[],available_weeks:[],available_months:[],available_years:[]});
      }
    }catch(_){}
    const final={...st,...readState(),mode:st.mode};
    states.set(key,final);
    setGlobals(view,final);
    syncQuick(final.mode);
    await consultActive();
  }

  /* Capa autoritativa: evita que los handlers viejos regresen al Centro
     o vuelvan a escribir el periodo de otra pestaña. */
  document.addEventListener('click',e=>{
    const quick=e.target.closest?.('#operativoPeriodBar .v250-quick-btn');
    if(quick){
      e.preventDefault();
      e.stopImmediatePropagation();
      changeMode(quick.dataset.mode);
      return;
    }

    const apply=e.target.closest?.('#operPeriodApply');
    if(apply&&activeKey()!=='operations.center'){
      e.preventDefault();
      e.stopImmediatePropagation();
      consultActive();
      return;
    }

    const reset=e.target.closest?.('#v254ResetFilters');
    if(reset){
      e.preventDefault();
      e.stopImmediatePropagation();
      resetActive();
      return;
    }

    const commercialReset=e.target.closest?.('#v254CommercialReset');
    if(commercialReset){
      e.preventDefault();
      e.stopImmediatePropagation();
      const store=q('#store'),section=q('#section'),catalog=q('#catalog'),week=q('#week');
      if(store)setVal(store,'Compañía');
      if(section)setVal(section,'Todas');
      if(catalog)setVal(catalog,'Todos');
      if(week&&week.options.length)week.selectedIndex=0;
      q('#refresh')?.click();
      return;
    }

    const tab=e.target.closest?.('#operativoNav>button[data-opview]');
    if(tab){
      const key=keyOf(tab);
      /* Centro Operativo conserva su controlador especializado V240.
         Metas conserva su controlador especializado V252. */
      if(key==='operations.center'||key==='operations.goals')return;
      e.preventDefault();
      e.stopImmediatePropagation();
      renderTab(tab);
    }
  },true);

  document.addEventListener('change',e=>{
    const id=e.target?.id||'';
    if(['operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect'].includes(id)){
      const key=activeKey(),view=activeView();
      if(key){
        const st=readState();
        states.set(key,st);
        setGlobals(view,st);
      }
    }
  },false);

  const observer=new MutationObserver(()=>setTimeout(ensureIcons,0));
  function start(){
    const bar=q('#operativoPeriodBar'),commercial=q('#globalFilters');
    if(bar)observer.observe(bar,{subtree:true,childList:true});
    if(commercial)observer.observe(commercial,{subtree:true,childList:true});
    ensureIcons();
    const key=activeKey();
    if(key)states.set(key,readState());
    [100,350,900,1800].forEach(ms=>setTimeout(ensureIcons,ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V254] filtros 9B definitivos activos: iconos + reset icon-only + estado por pestaña.');
})();
</script>'''

    @m.app.middleware("http")
    async def v254_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v254-filters-final-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v254-filters-final-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V254-FILTERS-FINAL",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V254] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V254_FILTERS_FINAL = True
    print("[V254] Filtros 9B definitivos instalados.",flush=True)
