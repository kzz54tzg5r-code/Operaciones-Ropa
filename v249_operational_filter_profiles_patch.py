"""V249 · perfiles de filtros por pestaña de Cambios y Muertos.

- Centro/Conversión/Recuperación/Tasa/Score: Día, Semana, Mes, Año + Tienda.
- Productividad: Día, Semana, Mes + Tienda.
- Recorridos: Día, Semana, Mes, Año + Tienda + Tipo de recolección.
- Filtros compactos en escritorio y meses con nombre.
- Refuerza acceso a Metas y tiendas.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V249_OPERATIONAL_FILTER_PROFILES", False):
        return

    css = r'''<style id="v249-operational-filter-profiles-css">
/* V249 · dejar el bloque de filtros sólo en la mitad izquierda en escritorio. */
body.v238-module-operativo #operativoPeriodBar.v249-compact{
  width:min(760px,54%)!important;
  max-width:760px!important;
  min-width:600px!important;
  margin-left:0!important;
  margin-right:auto!important;
  box-sizing:border-box!important;
}
body.v238-module-operativo #operativoPeriodBar.v249-compact .or-report-filter-grid{
  display:grid!important;
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
  gap:8px!important;
}
body.v238-module-operativo #operativoPeriodBar.v249-compact #operPeriodApply{
  grid-column:1!important;
  width:100%!important;
  min-width:0!important;
}
body.v238-module-operativo #operativoPeriodBar.v249-compact .v249-hidden{
  display:none!important;
}
@media(max-width:1180px){
  body.v238-module-operativo #operativoPeriodBar.v249-compact{
    width:min(820px,72%)!important;
    max-width:820px!important;
    min-width:0!important;
  }
}
@media(max-width:760px){
  body.v238-module-operativo #operativoPeriodBar.v249-compact{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
  }
  body.v238-module-operativo #operativoPeriodBar.v249-compact .or-report-filter-grid{
    grid-template-columns:1fr!important;
  }
  body.v238-module-operativo #operativoPeriodBar.v249-compact #operPeriodApply{
    grid-column:1!important;
  }
}
</style>'''

    js = r'''<script id="v249-operational-filter-profiles-js">
(function(){
  if(window.__V249_OPERATIONAL_FILTER_PROFILES)return;
  window.__V249_OPERATIONAL_FILTER_PROFILES=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const MONTHS=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
  const FULL_KEYS=new Set([
    'operations.center','operations.conversion','operations.recovery',
    'operations.recovery_store','operations.routes','operations.score'
  ]);
  const PRODUCTIVITY_KEY='operations.productivity';
  const ROUTES_KEY='operations.routes';

  function activeButton(){
    return q('#operativoNav>button.active[data-opview]')||
      q('#operativoNav>button[aria-selected="true"][data-opview]')||
      q('#operativoNav>button[data-opview="Centro Ejecutivo"]');
  }
  function keyOf(btn){return String(btn?.dataset?.tabKey||'')}
  function viewOf(btn){return String(btn?.dataset?.opview||'Centro Ejecutivo')}

  function show(el,on){
    if(!el)return;
    el.classList.toggle('v249-hidden',!on);
    if(on){
      el.classList.remove('hidden');
      el.removeAttribute('hidden');
      el.style.removeProperty('display');
    }else{
      el.classList.add('hidden');
    }
  }
  function setOptions(select,items,preserve=true){
    if(!select)return;
    const before=preserve?select.value:'';
    const html=items.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    if(select.innerHTML!==html)select.innerHTML=html;
    if(items.some(x=>x[0]===before))select.value=before;
  }
  function modeOptions(key){
    if(FULL_KEYS.has(key))return [['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
    if(key===PRODUCTIVITY_KEY)return [['day','Día'],['week','Semanal'],['month','Mensual']];
    return null;
  }
  function monthLabel(value){
    const mt=String(value||'').match(/^(\d{4})-(\d{2})$/);
    if(!mt)return String(value||'');
    const ix=Number(mt[2])-1;
    return (MONTHS[ix]||mt[2])+' '+mt[1];
  }
  function relabelPeriod(){
    const mode=q('#operPeriodMode')?.value||'';
    if(mode!=='month')return;
    const sel=q('#operPeriodSelect');
    if(!sel)return;
    [...sel.options].forEach(o=>{o.textContent=monthLabel(o.value)});
  }
  function collectionTypeOptions(){
    const sel=q('#operActivitySelect');
    if(!sel)return;
    const current=['','Muertos','Cambios','Probador'].includes(sel.value)?sel.value:'';
    setOptions(sel,[['','Todos'],['Muertos','Muertos'],['Cambios','Cambios'],['Probador','Probador']],false);
    sel.value=current;
    const label=q('#operActivityWrap label span:last-child');
    if(label)label.textContent='Tipo de recolección';
  }

  function applyProfile(){
    const btn=activeButton();
    const key=keyOf(btn),view=viewOf(btn);
    const target=FULL_KEYS.has(key)||key===PRODUCTIVITY_KEY;
    const bar=q('#operativoPeriodBar');
    if(!bar)return;
    bar.classList.toggle('v249-compact',target);

    if(!target){
      return;
    }

    const opts=modeOptions(key);
    const modeWrap=q('#operPeriodModeWrap'),mode=q('#operPeriodMode');
    show(modeWrap,true);
    if(opts&&mode){
      const before=mode.value;
      setOptions(mode,opts,true);
      if(!opts.some(x=>x[0]===mode.value)){
        mode.value=opts.some(x=>x[0]===before)?before:(key===PRODUCTIVITY_KEY?'month':'month');
      }
    }

    show(q('#operPeriodSelectWrap'),true);
    show(q('#operStoreWrap'),true);
    show(q('#operStartWrap'),false);
    show(q('#operEndWrap'),false);
    show(q('#operAreaWrap'),false);

    if(key===ROUTES_KEY){
      show(q('#operActivityWrap'),true);
      collectionTypeOptions();
    }else{
      show(q('#operActivityWrap'),false);
      const lab=q('#operActivityWrap label span:last-child');
      if(lab)lab.textContent='Actividad';
    }

    relabelPeriod();

    // Mantener el encabezado correcto en Metas/administración.
    if(view==='Metas y tiendas'){
      bar.classList.remove('v249-compact');
      bar.classList.add('hidden');
    }
  }

  const previous=window.renderOperativoView;
  if(typeof previous==='function'){
    window.renderOperativoView=async function(name,force=false){
      const result=await previous.apply(this,arguments);
      applyProfile();
      [40,180,500].forEach(ms=>setTimeout(applyProfile,ms));
      return result;
    };
  }

  document.addEventListener('click',e=>{
    const tab=e.target.closest?.('#operativoNav>button');
    if(tab){
      [0,30,120,350].forEach(ms=>setTimeout(applyProfile,ms));
    }
    if(e.target.closest?.('#openGoalsBtn')){
      try{
        window.OP_VIEW='Metas y tiendas';
      }catch(_){}
      qa('#operativoNav>button').forEach(b=>{
        const on=b.id==='openGoalsBtn';
        b.classList.toggle('active',on);
        b.setAttribute('aria-selected',on?'true':'false');
      });
      const bar=q('#operativoPeriodBar');
      if(bar){bar.classList.remove('v249-compact');bar.classList.add('hidden')}
    }
  },true);

  document.addEventListener('change',e=>{
    if(e.target?.id==='operPeriodMode'){
      setTimeout(()=>{applyProfile();relabelPeriod()},20);
      setTimeout(relabelPeriod,160);
    }
    if(e.target?.id==='operPeriodSelect')setTimeout(relabelPeriod,0);
    if(e.target?.id==='operActivitySelect'&&keyOf(activeButton())===ROUTES_KEY){
      setTimeout(applyProfile,0);
    }
  },true);

  const observer=new MutationObserver(()=>setTimeout(applyProfile,0));
  const start=()=>{
    const nav=q('#operativoNav');
    const bar=q('#operativoPeriodBar');
    if(nav)observer.observe(nav,{subtree:true,attributes:true,attributeFilter:['class','aria-selected']});
    if(bar)observer.observe(bar,{subtree:true,childList:true});
    applyProfile();
    [100,350,900,1800].forEach(ms=>setTimeout(applyProfile,ms));
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V249] perfiles compactos de filtros por pestaña activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v249_filter_profiles_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v249-operational-filter-profiles-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v249-operational-filter-profiles-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V249-FILTER-PROFILES",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V249] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V249_OPERATIONAL_FILTER_PROFILES = True
    print("[V249] Perfiles compactos de filtros por pestaña instalados.",flush=True)
