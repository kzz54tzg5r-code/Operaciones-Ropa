"""V236 · Centro Operativo estable y pestañas móviles finales.

- Evita la cadena de wrappers que podía dejar Centro Operativo en "Cargando reporte…".
- Mantiene Centro Operativo como pestaña activa y el título sincronizado con la vista.
- Renderiza primero la tabla operativa y difiere los bloques pesados.
- En móvil abrevia sólo cuando el ancho real no alcanza; tablet/escritorio conserva nombres completos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V236_CENTER_OPERATIVO_FINAL", False):
        return

    css = r'''<style id="v236-center-operativo-final-css">
@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs{
    column-gap:2px!important;
    margin:5px 0 10px!important;
    padding:0 2px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button{
    height:56px!important;
    min-height:56px!important;
    max-height:56px!important;
    gap:2px!important;
    padding:4px 1px 5px!important;
    border-radius:10px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon{
    width:15px!important;
    min-width:15px!important;
    max-width:15px!important;
    height:15px!important;
    min-height:15px!important;
    max-height:15px!important;
    flex:0 0 15px!important;
    margin:0!important;
    padding:0!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{
    display:flex!important;
    align-items:center!important;
    justify-content:center!important;
    width:100%!important;
    height:28px!important;
    min-height:28px!important;
    max-height:28px!important;
    margin:0!important;
    padding:0!important;
    overflow:hidden!important;
    white-space:pre-line!important;
    overflow-wrap:normal!important;
    word-break:normal!important;
    hyphens:none!important;
    text-align:center!important;
    font-size:6.25px!important;
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
    width:18px!important;min-width:18px!important;max-width:18px!important;
    height:18px!important;min-height:18px!important;max-height:18px!important;flex-basis:18px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{font-size:7.2px!important;height:30px!important;min-height:30px!important;max-height:30px!important}
}
@media(min-width:701px) and (max-width:900px){
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button{
    height:68px!important;min-height:68px!important;max-height:68px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon{
    width:20px!important;min-width:20px!important;max-width:20px!important;
    height:20px!important;min-height:20px!important;max-height:20px!important;flex-basis:20px!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{font-size:8px!important;height:32px!important;min-height:32px!important;max-height:32px!important}
}
</style>'''

    js = r'''<script id="v236-center-operativo-final-js">
(function(){
  if(window.__V236_CENTER_OPERATIVO_FINAL)return;
  window.__V236_CENTER_OPERATIVO_FINAL=true;

  const CENTER='Centro Ejecutivo';
  const LABEL={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
  const SUB={
    day:'Consulta por fecha · ingresos, pendientes y avance por tienda',
    week:'Semana ISO · operación, conversión, recuperación, productividad y recorridos',
    month:'Mes seleccionado · operación y desempeño consolidado',
    year:'Acumulado anual · operación, conversión, recuperación, productividad y recorridos'
  };
  const $q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  let seq=0;

  function mobile(){return window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900}

  function cmText(btn,compact){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview);
    const raw=norm(btn.dataset.v232Original||btn.dataset.rtLabel||btn.title||btn.textContent);
    const pair=(full,small)=>compact?small:full;
    if(key==='operations.center'||raw.includes('centro operativo')||raw.includes('centro ejecutivo'))return pair('Centro Operativo','Centro\nOperativo');
    if(raw==='operacion'||raw.startsWith('operacion '))return 'Operación';
    if(key==='operations.conversion'||op.includes('convers')||raw.includes('conversion'))return 'Conversión';
    if(key==='operations.recovery'||op.includes('recuperacion economica')||raw.includes('recuperacion $')||raw==='recuperaciones')return pair('Recuperación $','Recupera-\nciones');
    if(key==='operations.recovery_store'||op.includes('recuperacion por tienda')||raw.includes('recuperacion por tienda'))return pair('Recuperación por Tienda','Recuperac.\npor Tienda');
    if(raw.includes('cargar productividad'))return pair('Cargar productividad','Cargar\nProductividad');
    if(key==='operations.productivity'||op.includes('productividad')||raw==='productividad')return pair('Productividad','Producti-\nvidad');
    if(key==='operations.routes'||op.includes('recorridos')||raw.includes('recorridos'))return 'Recorridos';
    if(op.includes('carga de datos')||raw.includes('carga de datos'))return pair('Carga de datos','Carga de\ndatos');
    if(btn.id==='openGoalsBtn'||raw.includes('metas y tiendas')||raw==='metas')return pair('Metas y tiendas','Metas y\ntiendas');
    return String(btn.dataset.rtLabel||btn.title||btn.textContent||'').replace(/\s+/g,' ').trim();
  }

  function fitCmTabs(){
    if(!mobile())return;
    const host=$q('#operativoNav');if(!host)return;
    const buttons=qa(':scope>button',host).filter(b=>!b.hidden&&!b.classList.contains('hidden')&&b.getAttribute('aria-hidden')!=='true'&&getComputedStyle(b).display!=='none');
    if(!buttons.length)return;
    const cell=(host.getBoundingClientRect().width-Math.max(0,buttons.length-1)*2)/buttons.length;
    const compact=cell<58;
    buttons.forEach(btn=>{
      const lab=$q(':scope>.v232-tab-label',btn);if(!lab)return;
      const t=cmText(btn,compact);if(lab.textContent!==t)lab.textContent=t;
    });
  }

  function yearList(meta){
    return Array.from(new Set([...(meta?.available_dates||[]),...(meta?.available_months||[])].map(v=>String(v||'').slice(0,4)).filter(v=>/^\d{4}$/.test(v)))).sort();
  }

  function modeValue(){
    const m=$q('#operPeriodMode')?.value||'';
    if(['day','week','month','year'].includes(m))return m;
    try{if(['day','week','month','year'].includes(OPER_PERIOD?.type))return OPER_PERIOD.type}catch(_){}
    return 'month';
  }

  function setupPeriod(meta,keep=true){
    const mode=$q('#operPeriodMode'),wrap=$q('#operPeriodModeWrap'),sel=$q('#operPeriodSelect'),lab=$q('#operPeriodLabel'),bar=$q('#operativoPeriodBar');
    if(!mode||!sel||!lab||!wrap||!bar)return;
    const prior=modeValue();
    const options=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
    mode.innerHTML=options.map(([v,t])=>`<option value="${v}">${t}</option>`).join('');
    mode.value=options.some(x=>x[0]===prior)?prior:'month';
    wrap.classList.remove('hidden');bar.classList.remove('hidden');
    const t=mode.value;
    let list=t==='day'?(meta?.available_dates||[]):t==='week'?(meta?.available_weeks||[]):t==='month'?(meta?.available_months||[]):yearList(meta);
    list=[...list].filter(Boolean);
    lab.textContent=t==='day'?'Fecha':t==='week'?'Semana ISO':t==='month'?'Mes':'Año';
    const prev=keep?String(sel.value||''):'';
    const val=(prev&&list.includes(prev))?prev:(list.at(-1)||'');
    sel.innerHTML=list.map(v=>`<option value="${v}">${v}</option>`).join('');
    sel.value=val;
    try{OPER_PERIOD.type=t;OPER_PERIOD.value=val}catch(_){}
  }

  function centerActive(){
    const b=$q('#operativoNav [data-opview="Centro Ejecutivo"]');
    return !!b&&(b.classList.contains('active')||b.getAttribute('aria-selected')==='true');
  }

  function markCenter(){
    const b=$q('#operativoNav [data-opview="Centro Ejecutivo"]');
    if(!b)return;
    qa('#operativoNav>button').forEach(x=>{x.classList.toggle('active',x===b);if(x===b)x.setAttribute('aria-selected','true');else x.removeAttribute('aria-selected')});
    try{OP_VIEW=CENTER}catch(_){}
  }

  function setLoading(mode){
    const centro=$q('#operativoCentro'),dyn=$q('#operativoDynamic'),title=$q('#operativoDynamicTitle'),sub=$q('#operativoDynamicSub'),content=$q('#operativoDynamicContent');
    if(centro)centro.classList.add('hidden');if(dyn)dyn.classList.remove('hidden');
    if(title)title.textContent=`Centro Operativo · ${LABEL[mode]||''}`;
    if(sub)sub.textContent=SUB[mode]||'';
    if(content)content.innerHTML='<div class="infoempty">Cargando reporte…</div>';
  }

  function queryParams(mode,value){
    const store=$q('#operStoreSelect')?.value||'Compañía',area=$q('#operAreaSelect')?.value||'',activity=$q('#operActivitySelect')?.value||'';
    return {store,area,activity,type:mode,value};
  }

  async function getData(p){
    if(p.type==='year'){
      return await api(`/api/operations/year?year=${encodeURIComponent(p.value)}&store=${encodeURIComponent(p.store)}&area=${encodeURIComponent(p.area)}&activity=${encodeURIComponent(p.activity)}&compact=true&project_only=false`,{timeoutMs:120000});
    }
    const qs=`store=${encodeURIComponent(p.store)}&period_type=${encodeURIComponent(p.type)}&period_value=${encodeURIComponent(p.value)}&area=${encodeURIComponent(p.area)}&activity=${encodeURIComponent(p.activity)}&compact=true`;
    return await api('/api/operations/project-scope-v151?'+qs,{timeoutMs:120000});
  }

  function renderPrimary(d,p,mySeq){
    if(mySeq!==seq)return;
    const content=$q('#operativoDynamicContent'),title=$q('#operativoDynamicTitle'),sub=$q('#operativoDynamicSub');if(!content)return;
    if(title)title.textContent=`Centro Operativo · ${LABEL[p.type]||''}`;
    const projectCount=Number(d?.v153_project_store_count??d?.v151_project_store_count??(d?.project_stores||[]).length||0);
    if(sub)sub.textContent=(SUB[p.type]||'')+(projectCount?` · KPIs: ${projectCount} tiendas Proyecto`:'');
    if(!d?.available){content.innerHTML='<div class="infoempty">No hay una Base de datos Muertos y Cambios procesada. Cárgala desde la pestaña Carga de datos.</div>';return;}
    try{
      content.innerHTML=typeof monthlyCrossTable==='function'?monthlyCrossTable(d.metrics||{}):'<div class="infoempty">Reporte recibido, pero no fue posible construir la tabla operativa.</div>';
    }catch(e){content.innerHTML='<div class="infoempty">No fue posible construir el resumen: '+String(e?.message||e)+'</div>';return;}

    const appendHeavy=()=>{
      if(mySeq!==seq||!centerActive())return;
      try{
        const rec=d.recovery_by_store||[],stores=d.stores||[];
        const ordered=typeof orderByConversion==='function'?orderByConversion(stores.filter(x=>x.is_project),rec):stores.filter(x=>x.is_project);
        const scope=p.store==='Compañía'?'Todas las tiendas':p.store;
        let extra='';
        if(typeof recoveryTable==='function')extra+='<div class="title">Recuperación por tienda</div>'+recoveryTable(rec);
        if(typeof recoveryHorizontalChart==='function')extra+=recoveryHorizontalChart(rec,p.value||LABEL[p.type]||'',scope);
        if(typeof operationalDetailTable==='function')extra+='<div class="title">Detalle operativo · tiendas del proyecto</div>'+(ordered.length?operationalDetailTable(ordered,rec):'<div class="infoempty">No hay tiendas guardadas como Proyecto.</div>');
        if(ordered.length&&typeof opsComboSvg==='function')extra+=opsComboSvg(ordered,p.value||LABEL[p.type]||'',scope,rec);
        if(typeof reportDownloadBar==='function')extra+=reportDownloadBar('Centro Ejecutivo');
        if(extra)content.insertAdjacentHTML('beforeend',extra);
      }catch(e){console.warn('[V236] bloques secundarios:',e)}
    };
    if('requestIdleCallback'in window)requestIdleCallback(appendHeavy,{timeout:900});else setTimeout(appendHeavy,80);
  }

  async function renderCenter(resetPeriod=false){
    const mySeq=++seq;
    markCenter();fitCmTabs();
    let meta;
    try{
      meta=window.OPSDATA||null;
      if(!meta&&typeof refreshOperativoMeta==='function')meta=await refreshOperativoMeta();
      if(!meta)meta=window.OPSDATA||{};
    }catch(e){meta=window.OPSDATA||{};}
    if(mySeq!==seq)return;
    setupPeriod(meta,!resetPeriod);
    const mode=modeValue(),value=String($q('#operPeriodSelect')?.value||'');
    try{OPER_PERIOD.type=mode;OPER_PERIOD.value=value}catch(_){}
    setLoading(mode);
    const p=queryParams(mode,value);
    try{
      const d=await getData(p);
      renderPrimary(d,p,mySeq);
    }catch(e){
      if(mySeq!==seq)return;
      const c=$q('#operativoDynamicContent'),s=$q('#operativoDynamicSub');
      if(s)s.textContent='No fue posible abrir Centro Operativo';
      if(c)c.innerHTML='<div class="infoempty">Error al cargar el reporte: '+String(e?.message||e)+'</div>';
    }
  }

  function bind(){
    const center=$q('#operativoNav [data-opview="Centro Ejecutivo"]');
    if(center){
      center.onclick=async e=>{e?.preventDefault?.();await renderCenter(false)};
    }
    const mode=$q('#operPeriodMode');
    if(mode)mode.onchange=async()=>{setupPeriod(window.OPSDATA||{},false);await renderCenter(false)};
    const consult=$q('#operativoPeriodBar .primary');
    if(consult)consult.onclick=async e=>{if(!centerActive())return;e?.preventDefault?.();await renderCenter(false)};
    fitCmTabs();
  }

  function init(){
    bind();
    if(centerActive())setTimeout(()=>renderCenter(false),80);
    [250,700,1500].forEach(ms=>setTimeout(()=>{bind();fitCmTabs()},ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(()=>{bind();fitCmTabs()},40));
  window.addEventListener('resize',()=>setTimeout(fitCmTabs,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(fitCmTabs,150),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(()=>{bind();if(centerActive())renderCenter(false)},100),{passive:true});
  console.info('[V236] Centro Operativo estable + pestañas móviles finales activo.');
})();
</script>'''

    @m.app.middleware("http")
    async def v236_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v236-center-operativo-final-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v236-center-operativo-final-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V236-CENTER-FINAL",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V236] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V236_CENTER_OPERATIVO_FINAL = True
    print("[V236] Centro Operativo estable y pestañas móviles finales instalado.", flush=True)
