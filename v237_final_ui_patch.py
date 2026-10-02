"""V237 · Cierre de UI móvil y Centro Operativo.

Corrige los dos problemas que seguían visibles:
- Centro Operativo ya no depende de la cadena V119/V120/V151 para renderizar y no se queda en "Cargando reporte…".
- Cambios y Muertos ajusta etiquetas/iconos al ancho real sin cortar palabras.
- Macro Comercial empieza por dashboard y deja el bootstrap pesado en paralelo para evitar KPIs en guiones durante varios segundos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V237_FINAL_UI", False):
        return

    css = r'''<style id="v237-final-ui-css">
@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs{
    column-gap:2px!important;
    margin:5px 0 10px!important;
    padding:0 2px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button{
    min-width:0!important;
    height:56px!important;
    min-height:56px!important;
    max-height:56px!important;
    gap:2px!important;
    padding:4px 1px 5px!important;
    border-radius:10px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon{
    position:static!important;
    transform:none!important;
    width:14px!important;
    min-width:14px!important;
    max-width:14px!important;
    height:14px!important;
    min-height:14px!important;
    max-height:14px!important;
    flex:0 0 14px!important;
    margin:0!important;
    padding:0!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{
    position:static!important;
    left:auto!important;
    right:auto!important;
    transform:none!important;
    display:flex!important;
    align-items:center!important;
    justify-content:center!important;
    width:100%!important;
    min-width:0!important;
    height:28px!important;
    min-height:28px!important;
    max-height:28px!important;
    margin:0!important;
    padding:0 1px!important;
    overflow:hidden!important;
    white-space:pre-line!important;
    overflow-wrap:normal!important;
    word-break:normal!important;
    hyphens:none!important;
    text-align:center!important;
    font-size:5.75px!important;
    line-height:1.02!important;
    font-weight:900!important;
    letter-spacing:-.04px!important;
  }
}
@media(min-width:431px) and (max-width:700px){
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button{
    height:62px!important;min-height:62px!important;max-height:62px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon{
    width:17px!important;min-width:17px!important;max-width:17px!important;
    height:17px!important;min-height:17px!important;max-height:17px!important;flex-basis:17px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{
    font-size:6.8px!important;height:30px!important;min-height:30px!important;max-height:30px!important;
  }
}
@media(min-width:701px) and (max-width:900px){
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button{
    height:68px!important;min-height:68px!important;max-height:68px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon{
    width:20px!important;min-width:20px!important;max-width:20px!important;
    height:20px!important;min-height:20px!important;max-height:20px!important;flex-basis:20px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{
    font-size:8px!important;height:32px!important;min-height:32px!important;max-height:32px!important;
  }
}
</style>'''

    js = r'''<script id="v237-final-ui-js">
(function(){
  if(window.__V237_FINAL_UI)return;
  window.__V237_FINAL_UI=true;

  const CENTER='Centro Ejecutivo';
  const LABEL={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
  const SUB={
    day:'Consulta por fecha · ingresos, pendientes y avance por tienda',
    week:'Semana ISO · operación, conversión, recuperación, productividad y recorridos',
    month:'Mes seleccionado · operación y desempeño consolidado',
    year:'Acumulado anual · operación, conversión, recuperación, productividad y recorridos'
  };
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  let centerSeq=0;

  function isMobile(){return (window.matchMedia&&window.matchMedia('(max-width:900px)').matches)||window.innerWidth<=900;}

  function cmLabel(btn,compact){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview);
    const raw=norm(btn.dataset.v232Original||btn.dataset.rtLabel||btn.title||btn.textContent);
    const choose=(full,small)=>compact?small:full;
    if(key==='operations.center'||raw.includes('centro operativo')||raw.includes('centro ejecutivo'))return choose('Centro Operativo','Centro\nOperativo');
    if(raw==='operacion'||raw.startsWith('operacion '))return 'Operación';
    if(key==='operations.conversion'||op.includes('convers')||raw.includes('conversion'))return 'Conversión';
    if(key==='operations.recovery'||op.includes('recuperacion economica')||raw.includes('recuperacion $')||raw.includes('recuperaciones'))return choose('Recuperación $','Recupera-\nciones');
    if(key==='operations.recovery_store'||op.includes('recuperacion por tienda')||raw.includes('recuperacion por tienda'))return choose('Recuperación por Tienda','Recuperac.\npor Tienda');
    if(raw.includes('cargar productividad'))return choose('Cargar productividad','Cargar\nProductividad');
    if(key==='operations.productivity'||op.includes('productividad')||raw==='productividad')return choose('Productividad','Producti-\nvidad');
    if(key==='operations.routes'||op.includes('recorridos')||raw.includes('recorridos'))return 'Recorridos';
    if(op.includes('carga de datos')||raw.includes('carga de datos'))return choose('Carga de datos','Carga de\ndatos');
    if(btn.id==='openGoalsBtn'||raw.includes('metas y tiendas')||raw==='metas')return choose('Metas y tiendas','Metas y\ntiendas');
    return String(btn.dataset.rtLabel||btn.title||btn.textContent||'').replace(/\s+/g,' ').trim();
  }

  function fitCmTabs(){
    if(!isMobile())return;
    const host=q('#operativoNav');
    if(!host)return;
    const buttons=qa(':scope>button',host).filter(b=>!b.hidden&&!b.classList.contains('hidden')&&b.getAttribute('aria-hidden')!=='true'&&getComputedStyle(b).display!=='none');
    if(!buttons.length)return;
    const width=host.getBoundingClientRect().width||window.innerWidth;
    const cell=(width-Math.max(0,buttons.length-1)*2-4)/buttons.length;
    const compact=cell<59;
    buttons.forEach(btn=>{
      const lab=q(':scope>.v232-tab-label',btn);
      if(!lab)return;
      const t=cmLabel(btn,compact);
      if(lab.textContent!==t)lab.textContent=t;
    });
  }

  function modeValue(){
    const el=q('#operPeriodMode');
    const v=el?el.value:'';
    if(['day','week','month','year'].includes(v))return v;
    try{if(['day','week','month','year'].includes(OPER_PERIOD.type))return OPER_PERIOD.type;}catch(_e){}
    return 'month';
  }

  function yearList(meta){
    const raw=[].concat(meta&&meta.available_dates||[],meta&&meta.available_months||[]);
    return Array.from(new Set(raw.map(v=>String(v||'').slice(0,4)).filter(v=>/^\d{4}$/.test(v)))).sort();
  }

  function setupCenterPeriod(meta,keep){
    const mode=q('#operPeriodMode'),wrap=q('#operPeriodModeWrap'),sel=q('#operPeriodSelect'),lab=q('#operPeriodLabel'),bar=q('#operativoPeriodBar');
    if(!mode||!wrap||!sel||!lab||!bar)return;
    const prior=modeValue();
    const opts=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
    mode.innerHTML=opts.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    mode.value=opts.some(x=>x[0]===prior)?prior:'month';
    wrap.classList.remove('hidden');
    bar.classList.remove('hidden');
    const type=mode.value;
    let list=type==='day'?(meta&&meta.available_dates||[]):type==='week'?(meta&&meta.available_weeks||[]):type==='month'?(meta&&meta.available_months||[]):yearList(meta||{});
    list=Array.from(list||[]).filter(Boolean);
    lab.textContent=type==='day'?'Fecha':type==='week'?'Semana ISO':type==='month'?'Mes':'Año';
    const previous=keep?String(sel.value||''):'';
    const value=previous&&list.includes(previous)?previous:(list.length?list[list.length-1]:'');
    sel.innerHTML=list.map(v=>'<option value="'+String(v).replace(/"/g,'&quot;')+'">'+v+'</option>').join('');
    sel.value=value;
    try{OPER_PERIOD.type=type;OPER_PERIOD.value=value;}catch(_e){}
  }

  function markCenterActive(){
    const btn=q('#operativoNav [data-opview="Centro Ejecutivo"]');
    if(!btn)return;
    qa('#operativoNav>button').forEach(x=>{
      const active=x===btn;
      x.classList.toggle('active',active);
      if(active)x.setAttribute('aria-selected','true');else x.removeAttribute('aria-selected');
    });
    try{OP_VIEW=CENTER;}catch(_e){}
  }

  function setCenterHeader(type,projectCount){
    const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub');
    if(title)title.textContent='Centro Operativo · '+(LABEL[type]||'');
    if(sub){
      let txt=SUB[type]||'';
      if(projectCount>0)txt+=' · KPIs: '+projectCount+' tiendas Proyecto';
      sub.textContent=txt;
    }
  }

  function showCenterLoading(type){
    const centro=q('#operativoCentro'),dyn=q('#operativoDynamic'),content=q('#operativoDynamicContent');
    if(centro)centro.classList.add('hidden');
    if(dyn)dyn.classList.remove('hidden');
    setCenterHeader(type,0);
    if(content)content.innerHTML='<div class="infoempty">Cargando reporte…</div>';
  }

  function centerParams(type,value){
    return {
      type:type,
      value:value,
      store:(q('#operStoreSelect')&&q('#operStoreSelect').value)||'Compañía',
      area:(q('#operAreaSelect')&&q('#operAreaSelect').value)||'',
      activity:(q('#operActivitySelect')&&q('#operActivitySelect').value)||''
    };
  }

  async function fetchCenter(p){
    if(p.type==='year'){
      return await api('/api/operations/year?year='+encodeURIComponent(p.value)+'&store='+encodeURIComponent(p.store)+'&area='+encodeURIComponent(p.area)+'&activity='+encodeURIComponent(p.activity)+'&compact=true&project_only=false',{timeoutMs:120000});
    }
    const qs='store='+encodeURIComponent(p.store)+'&period_type='+encodeURIComponent(p.type)+'&period_value='+encodeURIComponent(p.value)+'&area='+encodeURIComponent(p.area)+'&activity='+encodeURIComponent(p.activity)+'&compact=true';
    return await api('/api/operations/project-scope-v151?'+qs,{timeoutMs:120000});
  }

  function renderCenterData(data,p,seq){
    if(seq!==centerSeq)return;
    const content=q('#operativoDynamicContent');
    if(!content)return;
    const rawCount=(data&&data.v153_project_store_count!=null)?data.v153_project_store_count:(data&&data.v151_project_store_count!=null?data.v151_project_store_count:((data&&data.project_stores)||[]).length);
    const projectCount=Number(rawCount||0);
    setCenterHeader(p.type,projectCount);
    if(data&&data.available===false&&!data.metrics){
      content.innerHTML='<div class="infoempty">No hay una Base de datos Muertos y Cambios procesada.</div>';
      return;
    }
    try{
      content.innerHTML=typeof monthlyCrossTable==='function'?monthlyCrossTable((data&&data.metrics)||{}):'<div class="infoempty">No fue posible construir el resumen operativo.</div>';
    }catch(err){
      content.innerHTML='<div class="infoempty">No fue posible construir el resumen: '+String(err&&err.message||err)+'</div>';
      return;
    }
    const append=()=>{
      if(seq!==centerSeq)return;
      try{
        const rec=(data&&data.recovery_by_store)||[];
        const stores=(data&&data.stores)||[];
        const ordered=typeof orderByConversion==='function'?orderByConversion(stores.filter(x=>x.is_project),rec):stores.filter(x=>x.is_project);
        const scope=p.store==='Compañía'?'Todas las tiendas':p.store;
        let extra='';
        if(typeof recoveryTable==='function')extra+='<div class="title">Recuperación por tienda</div>'+recoveryTable(rec);
        if(typeof recoveryHorizontalChart==='function')extra+=recoveryHorizontalChart(rec,p.value||LABEL[p.type]||'',scope);
        if(typeof operationalDetailTable==='function')extra+='<div class="title">Detalle operativo · tiendas del proyecto</div>'+(ordered.length?operationalDetailTable(ordered,rec):'<div class="infoempty">No hay tiendas guardadas como Proyecto.</div>');
        if(ordered.length&&typeof opsComboSvg==='function')extra+=opsComboSvg(ordered,p.value||LABEL[p.type]||'',scope,rec);
        if(typeof reportDownloadBar==='function')extra+=reportDownloadBar(CENTER);
        if(extra)content.insertAdjacentHTML('beforeend',extra);
      }catch(err){console.warn('[V237] bloques secundarios',err);}
    };
    if('requestIdleCallback' in window)requestIdleCallback(append,{timeout:700});else setTimeout(append,60);
  }

  async function renderCenter(options){
    const seq=++centerSeq;
    markCenterActive();
    fitCmTabs();
    let meta=null;
    try{
      if(typeof OPSDATA!=='undefined'&&OPSDATA)meta=OPSDATA;
      if(!meta&&typeof refreshOperativoMeta==='function')meta=await refreshOperativoMeta();
      if(!meta&&typeof OPSDATA!=='undefined')meta=OPSDATA;
    }catch(_e){meta={};}
    if(seq!==centerSeq)return;
    setupCenterPeriod(meta||{},!(options&&options.resetPeriod));
    const type=modeValue();
    const period=q('#operPeriodSelect');
    const value=String((period&&period.value)||'');
    try{OPER_PERIOD.type=type;OPER_PERIOD.value=value;}catch(_e){}
    showCenterLoading(type);
    const p=centerParams(type,value);
    try{
      const data=await fetchCenter(p);
      renderCenterData(data,p,seq);
    }catch(err){
      if(seq!==centerSeq)return;
      setCenterHeader(type,0);
      const content=q('#operativoDynamicContent');
      if(content)content.innerHTML='<div class="infoempty">Error al cargar el reporte: '+String(err&&err.message||err)+'</div>';
    }
  }

  const previousRender=window.renderOperativoView;
  window.renderOperativoView=async function(name,force){
    if(name===CENTER)return await renderCenter({resetPeriod:false,force:!!force});
    return typeof previousRender==='function'?await previousRender(name,force):undefined;
  };

  const previousGoSub=window.goSub;
  window.goSub=async function(p){
    if(p!=='macro'||typeof loadDash!=='function'){
      return typeof previousGoSub==='function'?await previousGoSub(p):undefined;
    }
    try{SUB='macro';MAIN='analysis';}catch(_e){}
    const gf=q('#globalFilters');if(gf)gf.classList.remove('hidden');
    qa('[data-main]').forEach(x=>x.classList.toggle('active',x.dataset.main==='analysis'));
    const an=q('#analysisNav'),on=q('#operativoNav');if(an)an.classList.remove('hidden');if(on)on.classList.add('hidden');
    if(typeof showPage==='function')showPage('macro');
    const wanted=(typeof ANALYSIS_STORE!=='undefined'&&ANALYSIS_STORE)||((q('#store')&&q('#store').value)||'Compañía');
    const section=(q('#section')&&q('#section').value)||'Todas';
    const dashPromise=loadDash(wanted,section);
    if(typeof loadCommercialBootstrap==='function')Promise.resolve(loadCommercialBootstrap()).catch(e=>console.warn('[V237] bootstrap comercial',e));
    return await dashPromise;
  };

  function activeOpsViewV246(){
    const btn=q('#operativoNav>button[data-opview].active')||q('#operativoNav>button[data-opview][aria-selected="true"]');
    return btn?.dataset?.opview||((typeof OP_VIEW!=='undefined'&&OP_VIEW)||CENTER);
  }
  function syncActiveOpsV246(view){
    const btn=q('#operativoNav>button[data-opview="'+String(view||'').replace(/"/g,'\\\"')+'"]');
    if(!btn)return;
    qa('#operativoNav>button[data-opview]').forEach(x=>{
      const on=x===btn;
      x.classList.toggle('active',on);
      x.setAttribute('aria-selected',on?'true':'false');
    });
    try{OP_VIEW=view}catch(_e){}
  }
  function bind(){
    const center=q('#operativoNav [data-opview="Centro Ejecutivo"]');
    if(center)center.onclick=e=>{if(e)e.preventDefault();renderCenter({resetPeriod:false});};

    const mode=q('#operPeriodMode');
    if(mode)mode.onchange=()=>{
      const view=activeOpsViewV246();
      if(view===CENTER){
        setupCenterPeriod((typeof OPSDATA!=='undefined'&&OPSDATA)||{},false);
        renderCenter({resetPeriod:false});
        return;
      }
      // El filtro Vista pertenece a la pestaña activa; nunca manda al Centro Operativo.
      syncActiveOpsV246(view);
      try{
        OPER_PERIOD.type=typeof currentPeriodTypeForView==='function'?currentPeriodTypeForView(view):(mode.value||'month');
        OPER_PERIOD.value='';
      }catch(_e){}
      if(typeof setPeriodSelector==='function'){
        setPeriodSelector(view,(typeof OPSDATA!=='undefined'&&OPSDATA)||{available_dates:[],available_weeks:[],available_months:[],available_years:[]});
      }
      if(typeof resolveOpsPeriod==='function'){
        Promise.resolve(resolveOpsPeriod(OPER_PERIOD.type)).then(()=>{
          syncActiveOpsV246(view);
        }).catch(err=>console.warn('[V246] no se pudo resolver periodo',err));
      }
    };

    const consult=q('#operativoPeriodBar .primary');
    if(consult)consult.onclick=e=>{
      const view=activeOpsViewV246();
      if(e)e.preventDefault();
      if(view===CENTER){
        renderCenter({resetPeriod:false});
        return;
      }
      // Consultar re-renderiza exclusivamente la pestaña visible.
      syncActiveOpsV246(view);
      try{
        OPER_PERIOD.type=typeof currentPeriodTypeForView==='function'?currentPeriodTypeForView(view):((q('#operPeriodMode')&&q('#operPeriodMode').value)||'month');
        OPER_PERIOD.value=(q('#operPeriodSelect')&&q('#operPeriodSelect').value)||'';
      }catch(_e){}
      if(typeof renderOperativoView==='function'){
        Promise.resolve(renderOperativoView(view,false)).catch(err=>console.error('[V246] consultar '+view,err));
      }
    };
    fitCmTabs();
  }

  function init(){bind();setTimeout(bind,200);setTimeout(bind,700);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(bind,30));
  window.addEventListener('resize',()=>setTimeout(fitCmTabs,60),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(fitCmTabs,120),{passive:true});
  console.info('[V237] UI final: Centro Operativo estable + Comercial rápido + tabs móviles.');
})();
</script>'''

    @m.app.middleware("http")
    async def v237_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v237-final-ui-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v237-final-ui-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V237-FINAL",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V237] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V237_FINAL_UI = True
    print("[V237] UI final instalada: Centro Operativo + Comercial rápido + pestañas móviles.", flush=True)
