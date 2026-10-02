"""V244 · Filtros autoritativos por pestaña en Cambios y Muertos.

Corrige el caso donde "Consultar" reutilizaba OP_VIEW/periodo de Centro Operativo
y regresaba a la pestaña principal. Mantiene Tienda como filtro compartido entre
reportes, pero hace que Vista/Periodo y la acción Consultar pertenezcan siempre
a la pestaña activa.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V244_TAB_FILTERS", False):
        return

    js = r'''<script id="v244-tab-filters-js">
(function(){
  if(window.__V244_TAB_FILTERS)return;
  window.__V244_TAB_FILTERS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const RECOVERY='Recuperación por Tienda';
  const CENTER='Centro Ejecutivo';
  const RECOVERY_KEY='operations.recovery_store';
  const PERIOD_MEMORY_KEY='or.v244.periods';

  function readMemory(){
    try{return JSON.parse(sessionStorage.getItem(PERIOD_MEMORY_KEY)||'{}')||{}}
    catch(_e){return{}}
  }
  function writeMemory(data){
    try{sessionStorage.setItem(PERIOD_MEMORY_KEY,JSON.stringify(data||{}))}catch(_e){}
  }
  const periods=readMemory();

  function tabKey(btn){
    return String(btn?.dataset?.tabKey||btn?.dataset?.opview||'').trim();
  }
  function buttonForView(name){
    return qa('#operativoNav>button[data-opview]').find(b=>String(b.dataset.opview||'')===String(name||''))||null;
  }
  function activeButton(){
    const buttons=qa('#operativoNav>button[data-opview]:not(.hidden)');
    const exact=buttons.find(b=>b.classList.contains('active'));
    if(exact)return exact;
    try{
      const byView=buttons.find(b=>String(b.dataset.opview||'')===String(OP_VIEW||''));
      if(byView)return byView;
    }catch(_e){}
    return buttons.find(b=>b.getAttribute('aria-selected')==='true')||null;
  }
  function setActive(btn){
    if(!btn)return;
    qa('#operativoNav>button[data-opview]').forEach(b=>{
      const on=b===btn;
      b.classList.toggle('active',on);
      b.setAttribute('aria-selected',on?'true':'false');
    });
    try{OP_VIEW=btn.dataset.opview}catch(_e){}
  }

  function listFor(mode){
    const d=window.OPSDATA||{};
    if(mode==='day')return (d.available_dates||[]).filter(Boolean);
    if(mode==='week')return (d.available_weeks||[]).filter(Boolean);
    if(mode==='month')return (d.available_months||[]).filter(Boolean);
    return [];
  }
  function savePeriod(btn){
    if(!btn)return;
    const key=tabKey(btn);
    const mode=q('#operPeriodMode')?.value||'';
    const value=q('#operPeriodSelect')?.value||'';
    if(key){
      periods[key]={mode,value};
      writeMemory(periods);
    }
  }
  function setVisibility(name){
    const area=q('#operAreaWrap'),activity=q('#operActivityWrap');
    const recoveryFamily=[RECOVERY,'Conversión','Recuperación Económica'].includes(String(name||''));
    [area,activity].forEach(el=>{
      if(!el)return;
      el.classList.toggle('hidden',recoveryFamily);
      el.style.display=recoveryFamily?'none':'';
    });
  }

  function configureRecoveryFilters(preferredMode='',preferredValue=''){
    const bar=q('#operativoPeriodBar'),modeWrap=q('#operPeriodModeWrap'),mode=q('#operPeriodMode');
    const sel=q('#operPeriodSelect'),lab=q('#operPeriodLabel');
    if(!bar||!modeWrap||!mode||!sel||!lab)return;

    bar.classList.remove('hidden');bar.style.removeProperty('display');
    modeWrap.classList.remove('hidden');modeWrap.style.removeProperty('display');
    q('#operStartWrap')?.classList.add('hidden');
    q('#operEndWrap')?.classList.add('hidden');

    const saved=periods[RECOVERY_KEY]||{};
    const wantedMode=['week','day'].includes(preferredMode)?preferredMode:
      (['week','day'].includes(saved.mode)?saved.mode:'week');

    mode.innerHTML='<option value="week">Semanal</option><option value="day">Diario</option>';
    mode.value=wantedMode;

    const values=listFor(wantedMode);
    const wantedValue=preferredValue||saved.value||'';
    const selected=(wantedValue&&values.includes(wantedValue))?wantedValue:(values.at(-1)||'');
    lab.textContent=wantedMode==='day'?'Fecha':'Semana ISO';
    sel.innerHTML=values.map(v=>'<option value="'+String(v).replaceAll('"','&quot;')+'">'+v+'</option>').join('');
    if(selected)sel.value=selected;

    try{
      OPER_PERIOD.type=wantedMode;
      OPER_PERIOD.value=selected;
      OP_VIEW=RECOVERY;
    }catch(_e){}
    periods[RECOVERY_KEY]={mode:wantedMode,value:selected};
    writeMemory(periods);
    setVisibility(RECOVERY);
  }

  function fixRecoveryLabel(){
    const btn=q('#operativoNav [data-tab-key="'+RECOVERY_KEY+'"]');
    if(!btn)return;
    btn.dataset.v232Original='Tasa de recuperación';
    btn.dataset.rtLabel='Tasa de recuperación';
    btn.title='Tasa de recuperación';
    const lab=q(':scope>.v238-tab-label,:scope>.v232-tab-label,:scope>.v203-tab-label,:scope>.rt-tab-label',btn);
    if(lab){
      const compact=window.innerWidth<=600?'Tasa de\nrecup.':'Tasa de\nrecuperación';
      if(lab.textContent!==compact)lab.textContent=compact;
    }else if(btn.children.length===0 && btn.textContent!=='Tasa de recuperación'){
      btn.textContent='Tasa de recuperación';
    }
  }

  async function renderActive(btn){
    if(!btn)return;
    const name=String(btn.dataset.opview||'');
    setActive(btn);
    setVisibility(name);

    const mode=q('#operPeriodMode')?.value||'';
    const value=q('#operPeriodSelect')?.value||'';
    try{
      OP_VIEW=name;
      if(typeof OPER_PERIOD==='object'){
        if(mode)OPER_PERIOD.type=mode;
        OPER_PERIOD.value=value;
      }
    }catch(_e){}
    savePeriod(btn);

    const host=q('#operativoDynamicContent');
    if(host)host.innerHTML='<div class="infoempty">Cargando reporte...</div>';

    try{
      await window.renderOperativoView(name,false);
    }finally{
      // Ningún renderer o filtro puede apropiarse de la selección después de consultar.
      setActive(btn);
      if(name===RECOVERY){
        configureRecoveryFilters(mode,value);
        const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub');
        if(title)title.textContent='Tasa de recuperación';
        if(sub)sub.textContent='Sell-Through Neto · Stock Inicial + devoluciones habilitadas vs venta del mismo periodo';
      }else{
        setVisibility(name);
      }
      savePeriod(btn);
      fixRecoveryLabel();
    }
  }

  // Tasa de recuperación tiene un periodo distinto de Centro Operativo:
  // interceptamos su pestaña antes del onclick legado que reseteaba OPER_PERIOD.
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#operativoNav [data-tab-key="'+RECOVERY_KEY+'"]');
    if(!btn)return;
    e.preventDefault();
    e.stopImmediatePropagation();
    setActive(btn);
    const saved=periods[RECOVERY_KEY]||{};
    configureRecoveryFilters(saved.mode||'week',saved.value||'');
    Promise.resolve(renderActive(btn)).catch(err=>{
      console.error('[V244] Tasa de recuperación',err);
      const host=q('#operativoDynamicContent');
      if(host)host.innerHTML='<div class="infoempty">No fue posible consultar Tasa de recuperación: '+String(err?.message||err)+'</div>';
    });
  },true);

  // Consultar siempre usa la pestaña ACTIVA, nunca OP_VIEW heredado.
  document.addEventListener('click',e=>{
    const apply=e.target.closest?.('#operPeriodApply');
    if(!apply)return;
    const btn=activeButton();
    if(!btn)return;
    const name=String(btn.dataset.opview||'');
    if(name===CENTER)return; // Centro conserva el controlador V239.
    if(name==='Carga de datos'||name==='Cargar productividad')return;

    e.preventDefault();
    e.stopImmediatePropagation();
    if(name===RECOVERY){
      configureRecoveryFilters(q('#operPeriodMode')?.value||'week',q('#operPeriodSelect')?.value||'');
    }
    Promise.resolve(renderActive(btn)).catch(err=>{
      console.error('[V244] Consultar pestaña',name,err);
      const host=q('#operativoDynamicContent');
      if(host)host.innerHTML='<div class="infoempty">No fue posible consultar '+name+': '+String(err?.message||err)+'</div>';
    });
  },true);

  // En Tasa de recuperación sólo existen Semana ISO y Día.
  document.addEventListener('change',e=>{
    const btn=activeButton();
    if(!btn)return;
    const name=String(btn.dataset.opview||'');
    if(name!==RECOVERY){
      if(['operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect'].includes(e.target.id))savePeriod(btn);
      return;
    }

    if(e.target.id==='operPeriodMode'){
      e.stopImmediatePropagation();
      configureRecoveryFilters(e.target.value,'');
      return;
    }
    if(e.target.id==='operPeriodSelect'){
      try{OPER_PERIOD.type=q('#operPeriodMode')?.value||'week';OPER_PERIOD.value=e.target.value}catch(_e){}
      savePeriod(btn);
      return;
    }
  },true);

  // Al abandonar recuperación se restauran filtros operativos que sí aplican.
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#operativoNav>button[data-opview]');
    if(!btn||tabKey(btn)===RECOVERY_KEY)return;
    setTimeout(()=>{
      const active=activeButton();
      if(active)setVisibility(active.dataset.opview);
      fixRecoveryLabel();
    },0);
  });

  const nav=q('#operativoNav');
  if(nav){
    const obs=new MutationObserver(()=>setTimeout(fixRecoveryLabel,0));
    obs.observe(nav,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','aria-selected']});
  }

  function init(){
    fixRecoveryLabel();
    const btn=activeButton();
    if(btn)setVisibility(btn.dataset.opview);
    if(tabKey(btn)===RECOVERY_KEY){
      setActive(btn);
      const saved=periods[RECOVERY_KEY]||{};
      configureRecoveryFilters(saved.mode||'week',saved.value||'');
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  [120,500,1200,2500].forEach(ms=>setTimeout(init,ms));
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});

  console.info('[V244] Filtros por pestaña activos; Consultar conserva la pestaña seleccionada.');
})();
</script>'''

    @m.app.middleware("http")
    async def v244_tab_filters_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v244-tab-filters-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V244-TAB-FILTERS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V244] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V244_TAB_FILTERS = True
    print("[V244] Filtros autoritativos por pestaña instalados.", flush=True)
