"""V266 · controlador autoritativo de periodos operativos.

Corrige la desincronización entre la Vista operativa visible y el selector
real usado por los reportes. Obtiene periodos reales desde /api/operations/meta,
mantiene texto/icono dinámicos (Fecha/Semana ISO/Mes/Año) y ejecuta cada filtro
sin depender de Consultar/Restablecer.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V266_OPERATIONAL_PERIOD_AUTHORITY", False):
        return

    css = r'''<style id="v266-operational-period-authority-css">
/* V266 sustituye visualmente sólo la barra Vista operativa de V259. */
#operativoPeriodBar .v259-period-view{display:none!important}
#operativoPeriodBar .v266-period-view{
  order:-11!important;
  display:flex!important;
  flex:1.45 1 380px!important;
  min-width:330px!important;
  max-width:none!important;
  width:auto!important;
  flex-direction:column!important;
  gap:5px!important;
  margin:0!important;
  padding:0!important;
  align-self:flex-end!important;
  box-sizing:border-box!important;
}
#operativoPeriodBar .v266-period-view.hidden{display:none!important}
#operativoPeriodBar .v266-period-title{
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
#operativoPeriodBar .v266-period-title-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#operativoPeriodBar .v266-period-title-icon svg{
  display:block!important;width:15px!important;height:15px!important;
}
#operativoPeriodBar .v266-period-buttons{
  display:grid!important;
  grid-template-columns:repeat(var(--v266-mode-count,4),minmax(0,1fr))!important;
  width:100%!important;
  min-width:0!important;
  min-height:48px!important;
  height:48px!important;
  overflow:hidden!important;
  border:1px solid #9fc4e8!important;
  border-radius:11px!important;
  background:#fff!important;
}
#operativoPeriodBar .v266-period-btn{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  min-width:0!important;
  min-height:48px!important;
  height:48px!important;
  padding:0 9px!important;
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
#operativoPeriodBar .v266-period-btn:last-child{border-right:0!important}
#operativoPeriodBar .v266-period-btn:hover{background:#f4f9ff!important}
#operativoPeriodBar .v266-period-btn.active{
  color:#fff!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
}
#operativoPeriodBar .v266-period-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
#operativoPeriodBar .v266-period-mode-icon svg{
  display:block!important;width:15px!important;height:15px!important;
}
/* El select nativo de modo sigue como fuente técnica, nunca como UI visible. */
html body #operativoPeriodBar #operPeriodModeWrap{display:none!important}

@media(max-width:767px){
  #operativoPeriodBar .v266-period-view{
    flex:0 0 286px!important;
    min-width:286px!important;
  }
  #operativoPeriodBar .v266-period-btn{
    font-size:8.5px!important;
    gap:4px!important;
    padding:0 5px!important;
  }
}
</style>'''

    js = r'''<script id="v266-operational-period-authority-js">
(function(){
  if(window.__V266_OPERATIONAL_PERIOD_AUTHORITY)return;
  window.__V266_OPERATIONAL_PERIOD_AUTHORITY=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const FULL=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
  const PROD=[['day','Día'],['week','Semanal'],['month','Mensual']];
  const FLEX=[['week','Semanal'],['month','Mensual']];
  const EYE='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
  const ICONS={
    day:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M9 15h6"/></svg>',
    week:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M6.5 14h2M11 14h2M15.5 14h2M6.5 17h2M11 17h2M15.5 17h2"/></svg>',
    month:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M7 14h3M12 14h3M7 17h3M12 17h3"/></svg>',
    year:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v4M17 2v4M3 9h18"/><path d="M8 13h8M8 17h8"/></svg>'
  };
  const LABELS={day:'Fecha',week:'Semana ISO',month:'Mes',year:'Año'};
  const MONTHS=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];

  let metaCache=null;
  let metaAt=0;
  let rendering=false;
  let queued=null;
  let ensureTimer=0;

  function active(){
    const btn=q('#operativoNav>button.active[data-opview]')||
              q('#operativoNav>button[aria-selected="true"][data-opview]');
    return {
      btn,
      key:String(btn?.dataset?.tabKey||''),
      view:String(btn?.dataset?.opview||'')
    };
  }
  function profile(view){
    if(!view||view==='Carga de datos'||view==='Metas y tiendas')return'';
    if(view==='Productividad por Colaborador'||view==='Ranking de Colaboradores')return'productivityperiod';
    if(['Centro Ejecutivo','Conversión','Recuperación Económica','Recuperación por Tienda','Cumplimiento de Recorridos','Índice Integral'].includes(view))return'fullperiod';
    try{
      const fixed=typeof fixedPeriodTypeForView==='function'?String(fixedPeriodTypeForView(view)||''):'';
      if(['fullperiod','productivityperiod','flex'].includes(fixed))return fixed;
    }catch(_){}
    return'';
  }
  function options(view){
    const p=profile(view);
    return p==='fullperiod'?FULL:p==='productivityperiod'?PROD:p==='flex'?FLEX:[];
  }
  function modeKey(ctx){return'or.v266.mode.'+(ctx.key||ctx.view||'generic')}
  function periodKey(ctx,mode){return'or.v266.period.'+(ctx.key||ctx.view||'generic')+'.'+mode}
  function nativeMode(opts){
    const v=String(q('#operPeriodMode')?.value||'');
    return opts.some(x=>x[0]===v)?v:'';
  }
  function savedMode(ctx,opts){
    try{
      const v=localStorage.getItem(modeKey(ctx));
      return opts.some(x=>x[0]===v)?v:'';
    }catch(_){return''}
  }
  function defaultMode(opts){
    if(opts.some(x=>x[0]==='month'))return'month';
    return opts[0]?.[0]||'';
  }
  function setNativeMode(opts,mode){
    const sel=q('#operPeriodMode');
    if(!sel||!opts.length)return;
    const expected=opts.map(x=>x[0]+'|'+x[1]).join('¦');
    const current=[...sel.options].map(o=>o.value+'|'+o.textContent.trim()).join('¦');
    if(current!==expected)sel.innerHTML=opts.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    sel.value=mode;
  }
  async function loadMeta(force=false){
    if(!force&&metaCache&&Date.now()-metaAt<60000)return metaCache;
    try{
      const res=await fetch('/api/operations/meta',{credentials:'same-origin',cache:'no-store'});
      if(!res.ok)throw new Error('HTTP '+res.status);
      const d=await res.json();
      metaCache=d||{};
      metaAt=Date.now();
      /* Compatibilidad con V254/V259, que leen esta referencia. */
      window.OPSDATA=metaCache;
      return metaCache;
    }catch(err){
      console.error('[V266] metadata',err);
      return metaCache||{};
    }
  }
  function listFor(meta,mode){
    if(mode==='day')return [...(meta.available_dates||[])].filter(Boolean).sort();
    if(mode==='week')return [...(meta.available_weeks||[])].filter(Boolean).sort();
    if(mode==='month')return [...(meta.available_months||[])].filter(Boolean).sort();
    if(mode==='year'){
      const direct=[...(meta.available_years||[])].map(String).filter(Boolean);
      if(direct.length)return [...new Set(direct)].sort();
      return [...new Set((meta.available_months||[]).map(x=>String(x||'').slice(0,4)).filter(x=>/^\d{4}$/.test(x)))].sort();
    }
    return[];
  }
  function displayValue(mode,v){
    if(mode==='month'){
      const m=String(v||'').match(/^(\d{4})-(\d{2})$/);
      if(m)return (MONTHS[Number(m[2])-1]||m[2])+' '+m[1];
    }
    return String(v||'');
  }
  function paintPeriodIdentity(mode){
    const label=LABELS[mode]||'Periodo';
    const lab=q('#operPeriodLabel');
    if(lab&&lab.textContent!==label)lab.textContent=label;
    const icon=q('#operPeriodSelectWrap label .or-fcontrol-icon');
    if(icon&&icon.dataset.v266Mode!==mode){
      icon.innerHTML=ICONS[mode]||ICONS.month;
      icon.dataset.v266Mode=mode;
    }
  }
  function setGlobals(mode,value){
    try{
      if(typeof OPER_PERIOD==='object'&&OPER_PERIOD){
        OPER_PERIOD.type=mode;
        OPER_PERIOD.value=value||'';
      }
    }catch(_){}
    try{window.V166_VIEW_TYPE=mode}catch(_){}
  }
  async function fillPeriod(mode,preferred='',forceLatest=false){
    paintPeriodIdentity(mode);
    const meta=await loadMeta(false);
    const list=listFor(meta,mode);
    const sel=q('#operPeriodSelect');
    if(!sel)return'';

    let desired='';
    if(!forceLatest&&preferred&&list.includes(String(preferred)))desired=String(preferred);
    if(!desired&&!forceLatest&&list.includes(String(sel.value||'')))desired=String(sel.value||'');
    const ctx=active();
    if(!desired&&!forceLatest){
      try{
        const saved=localStorage.getItem(periodKey(ctx,mode));
        if(saved&&list.includes(saved))desired=saved;
      }catch(_){}
    }
    if(!desired)desired=list.at(-1)||'';

    sel.innerHTML=list.map(v=>'<option value="'+String(v).replace(/"/g,'&quot;')+'">'+displayValue(mode,v)+'</option>').join('');
    if(desired)sel.value=desired;
    setGlobals(mode,desired);
    try{if(desired)localStorage.setItem(periodKey(ctx,mode),desired)}catch(_){}
    return desired;
  }
  function syncButtons(host,mode){
    qa('.v266-period-btn',host).forEach(b=>{
      const on=b.dataset.mode===mode;
      b.classList.toggle('active',on);
      b.setAttribute('aria-pressed',on?'true':'false');
    });
  }
  function ensureHost(){
    const bar=q('#operativoPeriodBar');
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    if(!bar||!grid)return null;
    const ctx=active();
    const opts=options(ctx.view);
    let host=q(':scope > .v266-period-view',grid);
    if(!opts.length){
      if(host)host.classList.add('hidden');
      return null;
    }
    bar.classList.remove('hidden');
    if(!host){
      host=document.createElement('div');
      host.className='v266-period-view';
      grid.insertBefore(host,grid.firstElementChild||null);
    }
    host.classList.remove('hidden');
    const modeCount=String(opts.length);
    if(host.style.getPropertyValue('--v266-mode-count')!==modeCount){
      host.style.setProperty('--v266-mode-count',modeCount);
    }
    const sig=opts.map(x=>x.join('|')).join('¦');
    if(host.dataset.signature!==sig){
      host.dataset.signature=sig;
      host.innerHTML=
        '<div class="v266-period-title"><span class="v266-period-title-icon">'+EYE+'</span><span>Vista operativa</span></div>'+
        '<div class="v266-period-buttons">'+opts.map(x=>
          '<button type="button" class="v266-period-btn" data-mode="'+x[0]+'" aria-pressed="false">'+
          '<span class="v266-period-mode-icon">'+ICONS[x[0]]+'</span><span>'+x[1]+'</span></button>'
        ).join('')+'</div>';
    }
    let mode=nativeMode(opts)||savedMode(ctx,opts)||defaultMode(opts);
    setNativeMode(opts,mode);
    syncButtons(host,mode);
    paintPeriodIdentity(mode);
    return {host,ctx,opts,mode};
  }
  async function renderCurrent(mode,value){
    const ctx=active();
    if(!ctx.view)return;
    if(rendering){
      queued={mode,value};
      return;
    }
    rendering=true;
    try{
      const opts=options(ctx.view);
      setNativeMode(opts,mode);
      setGlobals(mode,value);
      if(ctx.key==='operations.center'&&typeof window.V240_renderCenter==='function'){
        await window.V240_renderCenter(mode,false);
      }else if(typeof window.renderOperativoView==='function'){
        await window.renderOperativoView(ctx.view,true);
      }
    }catch(err){
      console.error('[V266] render',ctx,mode,value,err);
    }finally{
      rendering=false;
      /* Reafirmar identidad después de que capas históricas reconstruyan controles. */
      [0,40,120,280].forEach(ms=>setTimeout(async()=>{
        const now=active();
        if(now.key!==ctx.key||now.view!==ctx.view)return;
        const opts=options(now.view);
        setNativeMode(opts,mode);
        const host=q('#operativoPeriodBar .v266-period-view');
        if(host)syncButtons(host,mode);
        paintPeriodIdentity(mode);
        const sel=q('#operPeriodSelect');
        const meta=await loadMeta(false);
        const list=listFor(meta,mode);
        if(sel&&list.length){
          const wanted=list.includes(String(value||''))?String(value):list.at(-1);
          const sig=[...sel.options].map(o=>o.value).join('¦');
          const expected=list.join('¦');
          if(sig!==expected)sel.innerHTML=list.map(v=>'<option value="'+String(v).replace(/"/g,'&quot;')+'">'+displayValue(mode,v)+'</option>').join('');
          sel.value=wanted;
          setGlobals(mode,wanted);
        }
      },ms));
      if(queued){
        const next=queued;queued=null;
        setTimeout(()=>renderCurrent(next.mode,next.value),40);
      }
    }
  }
  async function chooseMode(mode){
    const info=ensureHost();
    if(!info||!info.opts.some(x=>x[0]===mode))return;
    try{localStorage.setItem(modeKey(info.ctx),mode)}catch(_){}
    setNativeMode(info.opts,mode);
    syncButtons(info.host,mode);
    paintPeriodIdentity(mode);
    const value=await fillPeriod(mode,'',true);
    if(!value){
      console.warn('[V266] sin periodos disponibles para',mode);
      return;
    }
    await renderCurrent(mode,value);
  }
  let filterTimer=0;
  function scheduleFilter(){
    clearTimeout(filterTimer);
    filterTimer=setTimeout(async()=>{
      const info=ensureHost();
      if(!info)return;
      const mode=info.mode;
      const value=String(q('#operPeriodSelect')?.value||'');
      setGlobals(mode,value);
      try{if(value)localStorage.setItem(periodKey(info.ctx,mode),value)}catch(_){}
      await renderCurrent(mode,value);
    },90);
  }
  async function repair(){
    const info=ensureHost();
    if(!info)return;
    const sel=q('#operPeriodSelect');
    const label=q('#operPeriodLabel')?.textContent||'';
    const correct=LABELS[info.mode]||'Periodo';
    if(label!==correct||!sel||sel.options.length===0){
      const preferred=String(sel?.value||'');
      await fillPeriod(info.mode,preferred,false);
    }else{
      paintPeriodIdentity(info.mode);
      syncButtons(info.host,info.mode);
    }
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('#operativoPeriodBar .v266-period-btn');
    if(!b)return;
    e.preventDefault();
    e.stopImmediatePropagation();
    chooseMode(String(b.dataset.mode||''));
  },true);

  document.addEventListener('change',e=>{
    const id=e.target?.id||'';
    if(id==='operPeriodSelect'){
      e.stopImmediatePropagation();
      scheduleFilter();
      return;
    }
    if(['operStoreSelect','operAreaSelect','operActivitySelect'].includes(id)){
      /* Evita consultas duplicadas de V254/V261; V266 ejecuta la pestaña activa. */
      e.stopImmediatePropagation();
      scheduleFilter();
    }
  },true);

  let lastActive='';
  const observer=new MutationObserver(()=>{
    clearTimeout(ensureTimer);
    ensureTimer=setTimeout(()=>{
      const ctx=active();
      const sig=ctx.key+'|'+ctx.view;
      ensureHost();
      repair();
      if(sig!==lastActive)lastActive=sig;
    },20);
  });

  function start(){
    loadMeta(true).then(()=>repair());
    const bar=q('#operativoPeriodBar'),nav=q('#operativoNav');
    if(bar)observer.observe(bar,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    if(nav)observer.observe(nav,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected']});
    ensureHost();
    [80,220,500,1000,1800].forEach(ms=>setTimeout(repair,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V266] Periodos operativos autoritativos: Día/Semana/Mes/Año + icono dinámico.');
})();
</script>'''

    @m.app.middleware("http")
    async def v266_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v266-operational-period-authority-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v266-operational-period-authority-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V266-PERIOD-AUTHORITY",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V266] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V266_OPERATIONAL_PERIOD_AUTHORITY=True
    print("[V266] Periodos operativos autoritativos instalados.",flush=True)
