"""V259 · filtro de periodo estable por reporte.

Objetivos:
- Vista operativa nunca desaparece mientras el reporte admita periodo variable.
- Detección redundante por tab_key, data-opview, OP_VIEW y título visible.
- Estado de vista independiente por pestaña.
- Cambio de Día/Semanal/Mensual/Anual ejecuta el reporte real de la pestaña.
- Mantiene filtros Fecha/Semana/Mes/Año, Tienda, Consultar y Restablecer.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V259_STABLE_FILTER", False):
        return

    css = r'''<style id="v259-stable-filter-css">
/* Sólo V259 presenta Vista operativa. */
#operativoPeriodBar.v259-has-period .v250-quick-period,
#operativoPeriodBar.v259-has-period .v256-center-view,
#operativoPeriodBar.v259-has-period .v257-period-view,
#operativoPeriodBar.v259-has-period .v258-period-view,
#operativoPeriodBar.v259-has-period #operPeriodModeWrap{
  display:none!important;
}

#operativoPeriodBar .v259-period-view{display:none}
#operativoPeriodBar.v259-has-period .v259-period-view{
  order:-10!important;
  display:flex!important;
  flex:1.42 1 350px!important;
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
#operativoPeriodBar.v259-has-period .v259-period-title{
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
#operativoPeriodBar.v259-has-period .v259-period-title-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  color:#1769d8!important;
}
#operativoPeriodBar.v259-has-period .v259-period-title-icon svg{
  display:block!important;width:15px!important;height:15px!important;
}
#operativoPeriodBar.v259-has-period .v259-period-buttons{
  display:grid!important;
  grid-template-columns:repeat(var(--v259-mode-count,4),minmax(0,1fr))!important;
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
#operativoPeriodBar.v259-has-period .v259-period-btn{
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
  transform:none!important;
}
#operativoPeriodBar.v259-has-period .v259-period-btn:last-child{border-right:0!important}
#operativoPeriodBar.v259-has-period .v259-period-btn:hover{background:#f4f9ff!important}
#operativoPeriodBar.v259-has-period .v259-period-btn.active{
  color:#fff!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.16)!important;
}
#operativoPeriodBar.v259-has-period .v259-period-mode-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;
  height:15px!important;
  min-width:15px!important;
}
#operativoPeriodBar.v259-has-period .v259-period-mode-icon svg{
  display:block!important;width:15px!important;height:15px!important;
}

/* Fila 9B estable. */
#operativoPeriodBar.v250-option9b > .or-report-filter-grid{
  display:flex!important;
  flex-wrap:nowrap!important;
  align-items:flex-end!important;
  gap:10px!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  padding-right:6px!important;
  box-sizing:border-box!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
}
#operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operPeriodSelectWrap{
  flex:1 1 205px!important;
  min-width:180px!important;
}
#operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operStoreWrap{
  flex:1.05 1 220px!important;
  min-width:190px!important;
}
#operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operActivityWrap,
#operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operAreaWrap{
  flex:.9 1 175px!important;
  min-width:160px!important;
}
#operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operPeriodApply{
  order:20!important;
  flex:.75 1 175px!important;
  min-width:155px!important;
  align-self:flex-end!important;
  transform:none!important;
}

/* Restablecer: caja e icono centrados. */
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
  transform:none!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters:hover{
  border-color:#438fdd!important;background:#f7fbff!important;transform:none!important;
}
html body #operativoPeriodBar.v250-option9b #v254ResetFilters svg{
  display:block!important;
  position:static!important;
  width:21px!important;
  height:21px!important;
  margin:0!important;
  padding:0!important;
  transform:none!important;
}

@media(max-width:1050px){
  #operativoPeriodBar.v259-has-period .v259-period-view{
    flex:0 0 320px!important;min-width:320px!important;
  }
  #operativoPeriodBar.v259-has-period > .or-report-filter-grid > #operPeriodApply{
    flex:0 0 155px!important;min-width:155px!important;
  }
}
@media(max-width:650px){
  #operativoPeriodBar.v259-has-period .v259-period-view{
    flex:0 0 286px!important;min-width:286px!important;
  }
  #operativoPeriodBar.v259-has-period .v259-period-buttons{
    min-height:42px!important;height:42px!important;
  }
  #operativoPeriodBar.v259-has-period .v259-period-btn{
    min-height:42px!important;height:42px!important;
    gap:4px!important;padding:0 5px!important;font-size:8px!important;
  }
  #operativoPeriodBar.v259-has-period .v259-period-title{font-size:7.5px!important}
  #operativoPeriodBar.v259-has-period .v259-period-mode-icon{
    width:13px!important;height:13px!important;min-width:13px!important;
  }
  #operativoPeriodBar.v259-has-period .v259-period-mode-icon svg{
    width:13px!important;height:13px!important;
  }
  html body #operativoPeriodBar.v250-option9b #v254ResetFilters{
    flex-basis:42px!important;width:42px!important;min-width:42px!important;max-width:42px!important;
    height:42px!important;min-height:42px!important;max-height:42px!important;
  }
}
</style>'''

    js = r'''<script id="v259-stable-filter-js">
(function(){
  if(window.__V259_STABLE_FILTER)return;
  window.__V259_STABLE_FILTER=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const FULL=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
  const PROD=[['day','Día'],['week','Semanal'],['month','Mensual']];
  const FLEX=[['week','Semanal'],['month','Mensual']];
  const ICONS={
    day:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M8 14h3"/></svg>',
    week:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M7 14h2M11 14h2M15 14h2"/></svg>',
    month:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><path d="M7 14h3M12 14h3M7 17h3M12 17h3"/></svg>',
    year:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v4M17 2v4M3 9h18"/><path d="M8 13h8M8 17h5"/></svg>'
  };
  const EYE='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';

  const KEY_VIEW={
    'operations.center':'Centro Ejecutivo',
    'operations.conversion':'Conversión',
    'operations.recovery':'Recuperación Económica',
    'operations.recovery_store':'Recuperación por Tienda',
    'operations.productivity':'Productividad por Colaborador',
    'operations.routes':'Cumplimiento de Recorridos',
    'operations.score':'Índice Integral'
  };
  const VIEW_KEY=Object.fromEntries(Object.entries(KEY_VIEW).map(([k,v])=>[v,k]));
  let last={key:'operations.center',view:'Centro Ejecutivo'};
  let applying=false;

  function norm(v){
    return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  }
  function viewFromTitle(){
    const t=norm(q('#operativoDynamicTitle')?.textContent||'');
    if(!t)return '';
    if(t.includes('centro operativo')||t.includes('centro ejecutivo'))return'Centro Ejecutivo';
    if(t.startsWith('conversion'))return'Conversión';
    if(t.includes('tasa de recuperacion')||t.includes('recuperacion por tienda'))return'Recuperación por Tienda';
    if(t.includes('recuperacion'))return'Recuperación Económica';
    if(t.includes('productividad'))return'Productividad por Colaborador';
    if(t.includes('recorridos'))return'Cumplimiento de Recorridos';
    if(t.includes('score')||t.includes('indice integral'))return'Índice Integral';
    return '';
  }
  function context(){
    const btn=q('#operativoNav>button.active')||q('#operativoNav>button[aria-selected="true"]');
    let key=String(btn?.dataset?.tabKey||'');
    let view=String(btn?.dataset?.opview||'');

    if(key&&KEY_VIEW[key])view=KEY_VIEW[key];
    if(view&&VIEW_KEY[view]&&!key)key=VIEW_KEY[view];

    if(!view){
      try{
        const gv=String(OP_VIEW||'');
        if(gv)view=gv;
      }catch(_){}
    }
    if(!view)view=viewFromTitle();
    if(view&&VIEW_KEY[view]&&!key)key=VIEW_KEY[view];

    if(key==='operations.goals'||view==='Metas y tiendas')return{key:'operations.goals',view:'Metas y tiendas'};
    if(view==='Carga de datos')return{key:'operations.upload',view:'Carga de datos'};

    if(view){
      last={key:key||last.key,view};
      return last;
    }
    return last;
  }
  function profile(view){
    if(!view||view==='Carga de datos'||view==='Metas y tiendas')return '';
    if(view==='Productividad por Colaborador'||view==='Ranking de Colaboradores')return'productivityperiod';
    if(['Centro Ejecutivo','Conversión','Recuperación Económica','Recuperación por Tienda','Cumplimiento de Recorridos','Índice Integral'].includes(view))return'fullperiod';
    try{
      const p=typeof fixedPeriodTypeForView==='function'?String(fixedPeriodTypeForView(view)||''):'';
      if(['fullperiod','productivityperiod','flex'].includes(p))return p;
    }catch(_){}
    return '';
  }
  function optionsFor(view){
    const p=profile(view);
    return p==='fullperiod'?FULL:p==='productivityperiod'?PROD:p==='flex'?FLEX:[];
  }
  function storageKey(key){return'or.v259.mode.'+String(key||'generic')}
  function savedMode(key,opts){
    try{
      const v=localStorage.getItem(storageKey(key));
      if(opts.some(x=>x[0]===v))return v;
    }catch(_){}
    return '';
  }
  function defaultMode(opts){
    if(opts.some(x=>x[0]==='month'))return'month';
    return opts[0]?.[0]||'';
  }
  function nativeMode(opts){
    const v=String(q('#operPeriodMode')?.value||'');
    return opts.some(x=>x[0]===v)?v:'';
  }
  function setNative(opts,mode){
    const sel=q('#operPeriodMode');
    if(!sel||!opts.length)return;
    const sig=opts.map(x=>x[0]+'|'+x[1]).join('¦');
    const cur=[...sel.options].map(o=>o.value+'|'+o.textContent.trim()).join('¦');
    if(cur!==sig)sel.innerHTML=opts.map(x=>'<option value="'+x[0]+'">'+x[1]+'</option>').join('');
    sel.value=opts.some(x=>x[0]===mode)?mode:defaultMode(opts);
  }
  function periodList(mode){
    const meta=window.OPSDATA||{};
    if(mode==='day')return [...(meta.available_dates||[])].filter(Boolean);
    if(mode==='week')return [...(meta.available_weeks||[])].filter(Boolean);
    if(mode==='month')return [...(meta.available_months||[])].filter(Boolean);
    if(mode==='year'){
      const own=[...(meta.available_years||[])].filter(Boolean);
      if(own.length)return own;
      return [...new Set((meta.available_months||[]).map(x=>String(x||'').slice(0,4)).filter(x=>/^\\d{4}$/.test(x)))].sort();
    }
    return [];
  }
  function syncPeriodControl(mode,reset=false){
    const sel=q('#operPeriodSelect'),lab=q('#operPeriodLabel');
    if(!sel||!lab)return'';
    const list=periodList(mode);
    let desired='';
    try{
      if(!reset && OPER_PERIOD?.type===mode && list.includes(String(OPER_PERIOD.value||'')))desired=String(OPER_PERIOD.value||'');
    }catch(_){}
    if(!desired && list.includes(String(sel.value||'')))desired=String(sel.value||'');
    if(!desired)desired=list.at(-1)||'';
    const monthNames=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
    const label=v=>{
      if(mode!=='month')return String(v||'');
      const mt=String(v||'').match(/^(\\d{4})-(\\d{2})$/);
      return mt?((monthNames[Number(mt[2])-1]||mt[2])+' '+mt[1]):String(v||'');
    };
    sel.innerHTML=list.map(v=>'<option value="'+v+'">'+label(v)+'</option>').join('');
    if(desired)sel.value=desired;
    lab.textContent=mode==='day'?'Fecha':mode==='week'?'Semana ISO':mode==='year'?'Año':'Mes';
    try{OPER_PERIOD.type=mode;OPER_PERIOD.value=desired}catch(_){}
    return desired;
  }
  function alignReset(){
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    const apply=q('#operPeriodApply',grid);
    const reset=q('#v254ResetFilters',grid);
    if(grid&&apply&&reset&&reset.previousElementSibling!==apply)apply.insertAdjacentElement('afterend',reset);
  }
  function sync(host,mode){
    qa('.v259-period-btn',host).forEach(b=>{
      const on=b.dataset.mode===mode;
      b.classList.toggle('active',on);
      b.setAttribute('aria-pressed',on?'true':'false');
    });
  }
  function ensure(){
    /* V266 es la autoridad final. No recrear la Vista operativa histórica. */
    if(window.__V266_OPERATIONAL_PERIOD_AUTHORITY){
      const old=q('#operativoPeriodBar .v259-period-view');
      if(old)old.remove();
      return;
    }
    const bar=q('#operativoPeriodBar');
    const grid=q('#operativoPeriodBar .or-report-filter-grid');
    if(!bar||!grid)return;

    alignReset();
    const ctx=context();
    const opts=optionsFor(ctx.view);
    const shouldShow=opts.length>0 && ctx.view!=='Carga de datos' && ctx.view!=='Metas y tiendas';

    let host=q(':scope > .v259-period-view',grid);
    if(!shouldShow){
      bar.classList.remove('v259-has-period');
      if(host)host.style.display='none';
      return;
    }

    bar.classList.remove('hidden');
    bar.classList.add('v259-has-period');

    let mode=savedMode(ctx.key,opts)||nativeMode(opts)||defaultMode(opts);
    setNative(opts,mode);

    if(!host){
      host=document.createElement('div');
      host.className='v259-period-view';
      grid.insertBefore(host,grid.firstElementChild||null);
    }
    const sig=opts.map(x=>x.join('|')).join('¦');
    if(host.dataset.signature!==sig){
      host.dataset.signature=sig;
      host.innerHTML=
        '<div class="v259-period-title"><span class="v259-period-title-icon">'+EYE+'</span><span>Vista operativa</span></div>'+
        '<div class="v259-period-buttons">'+
          opts.map(x=>'<button type="button" class="v259-period-btn" data-mode="'+x[0]+'" aria-pressed="false">'+
            '<span class="v259-period-mode-icon">'+ICONS[x[0]]+'</span><span>'+x[1]+'</span></button>').join('')+
        '</div>';
    }
    host.style.removeProperty('display');
    host.style.setProperty('--v259-mode-count',String(opts.length));
    sync(host,mode);
  }

  async function applyMode(mode){
    if(window.__V266_OPERATIONAL_PERIOD_AUTHORITY)return;
    if(applying)return;
    const ctx=context();
    const opts=optionsFor(ctx.view);
    if(!opts.some(x=>x[0]===mode))return;

    applying=true;
    try{
      try{localStorage.setItem(storageKey(ctx.key),mode)}catch(_){}
      setNative(opts,mode);
      syncPeriodControl(mode,true);

      if(ctx.key==='operations.center'&&typeof window.V240_renderCenter==='function'){
        await window.V240_renderCenter(mode,false);
      }else if(typeof window.renderOperativoView==='function'){
        /* El render existente sigue haciendo los cálculos. Sólo fijamos antes
           el tipo/valor correcto para que cada pestaña consulte su periodo. */
        await window.renderOperativoView(ctx.view,true);
      }

      /* Algunos reportes reconstruyen los controles durante el render.
         Reafirmar el modo seleccionado evita que vuelvan a mostrar MES cuando
         el usuario eligió Semana/Día/Año. */
      setNative(opts,mode);
      syncPeriodControl(mode,false);
    }catch(err){
      console.error('[V259] aplicar filtro',ctx,mode,err);
    }finally{
      applying=false;
      [0,40,100,220,500,900].forEach(ms=>setTimeout(ensure,ms));
    }
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('#operativoPeriodBar .v259-period-btn');
    if(!b)return;
    e.preventDefault();
    e.stopImmediatePropagation();
    applyMode(String(b.dataset.mode||''));
  },true);

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button,#operPeriodApply,#v254ResetFilters')){
      [0,30,80,180,420,800].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  document.addEventListener('change',e=>{
    if(['operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect'].includes(e.target?.id||'')){
      [0,70,180].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  let queued=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(queued);
    queued=setTimeout(ensure,16);
  });

  function start(){
    const bar=q('#operativoPeriodBar'),nav=q('#operativoNav'),title=q('#operativoDynamicTitle');
    if(bar)observer.observe(bar,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    if(nav)observer.observe(nav,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected']});
    if(title)observer.observe(title,{subtree:true,childList:true,characterData:true});
    ensure();
    [100,300,700,1400,2400].forEach(ms=>setTimeout(ensure,ms));
    /* Guardia ligera: si otro render reemplaza la fila sin mutación observable
       relevante, V259 la recompone. */
    setInterval(ensure,600);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V259] filtro estable por reporte activo.');
})();
</script>'''

    @m.app.middleware("http")
    async def v259_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v259-stable-filter-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v259-stable-filter-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V259-STABLE-FILTER",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V259] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V259_STABLE_FILTER = True
    print("[V259] filtro estable por reporte instalado.",flush=True)
