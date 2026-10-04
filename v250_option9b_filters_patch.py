"""V250 · Tema global de filtros Opción 9B.

Aplica el diseño 9B (gradiente azul suave, ancho completo y controles compactos)
a los filtros de Cambios y Muertos, Operación y Análisis Comercial, sin cambiar
las reglas de negocio ni los valores que cada pestaña usa.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V250_OPTION9B_FILTERS", False):
        return

    css = r'''<style id="v250-option9b-filters-css">
:root{
  --v250-filter-bg-1:#f7fbff;
  --v250-filter-bg-2:#e6f3ff;
  --v250-filter-bg-3:#cfe9ff;
  --v250-filter-line:#bfd8f2;
  --v250-filter-blue:#0d6ee8;
  --v250-filter-blue-2:#1689ff;
  --v250-filter-navy:#123f73;
}

/* ===== Opción 9B · base ===== */
#operativoPeriodBar.v250-option9b,
#globalFilters.v250-option9b{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin:0 0 12px!important;
  padding:0 14px 14px!important;
  border:1px solid var(--v250-filter-line)!important;
  border-radius:16px!important;
  box-sizing:border-box!important;
  overflow:hidden!important;
  background:
    linear-gradient(115deg,var(--v250-filter-bg-1) 0%,var(--v250-filter-bg-2) 58%,var(--v250-filter-bg-3) 100%)!important;
  box-shadow:0 8px 24px rgba(18,63,115,.08)!important;
}

/* Anula el ancho reducido de V249: Opción 9B ocupa todo el reporte. */
body.v238-module-operativo #operativoPeriodBar.v249-compact.v250-option9b{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin-left:0!important;
  margin-right:0!important;
}

/* Header azul como el boceto 9B */
#operativoPeriodBar.v250-option9b > .or-report-filter-brand,
#globalFilters.v250-option9b > .v250-filter-brand{
  grid-column:1/-1!important;
  width:calc(100% + 28px)!important;
  min-height:66px!important;
  margin:0 -14px 14px!important;
  padding:12px 18px!important;
  display:flex!important;
  align-items:center!important;
  gap:12px!important;
  box-sizing:border-box!important;
  color:#fff!important;
  background:linear-gradient(100deg,#0a4b91 0%,#0b67c8 55%,#1187ff 100%)!important;
  border:0!important;
  border-radius:0!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-brand b,
#globalFilters.v250-option9b > .v250-filter-brand b{
  display:block!important;
  margin:0!important;
  color:#fff!important;
  font-size:16px!important;
  line-height:1.05!important;
  font-weight:950!important;
}
#operativoPeriodBar.v250-option9b > .or-report-filter-brand small,
#globalFilters.v250-option9b > .v250-filter-brand small{
  display:block!important;
  margin-top:3px!important;
  color:rgba(255,255,255,.9)!important;
  font-size:10px!important;
  line-height:1.15!important;
  font-weight:650!important;
}
#operativoPeriodBar.v250-option9b .or-report-filter-brand-icon,
#globalFilters.v250-option9b .v250-filter-brand-icon{
  width:38px!important;
  height:38px!important;
  min-width:38px!important;
  display:grid!important;
  place-items:center!important;
  border-radius:11px!important;
  color:#fff!important;
  background:rgba(255,255,255,.14)!important;
  border:1px solid rgba(255,255,255,.16)!important;
}
#operativoPeriodBar.v250-option9b .or-report-filter-brand-icon svg,
#globalFilters.v250-option9b .v250-filter-brand-icon svg{
  width:22px!important;
  height:22px!important;
}

/* ===== Vista rápida: Día / Semanal / Mensual / Anual ===== */
#operativoPeriodBar.v250-option9b .v250-quick-period{
  display:flex;
  align-items:center;
  gap:10px;
  width:100%;
  margin:0 0 13px;
  padding:0 0 13px;
  border-bottom:1px solid rgba(112,154,199,.28);
}
#operativoPeriodBar.v250-option9b .v250-quick-period.hidden{display:none!important}
#operativoPeriodBar.v250-option9b .v250-quick-title{
  flex:0 0 122px;
  color:#415a77;
  font-size:10px;
  font-weight:950;
  text-transform:uppercase;
  letter-spacing:.025em;
}
#operativoPeriodBar.v250-option9b .v250-quick-buttons{
  flex:1;
  min-width:0;
  display:grid;
  grid-template-columns:repeat(var(--v250-quick-count,4),minmax(0,1fr));
  border:1px solid #bfd2e7;
  border-radius:13px;
  overflow:hidden;
  background:rgba(255,255,255,.58);
}
#operativoPeriodBar.v250-option9b .v250-quick-btn{
  min-width:0;
  min-height:44px;
  border:0;
  border-right:1px solid #c9daeb;
  border-radius:0;
  background:transparent;
  color:#153f70;
  font-size:11px;
  font-weight:900;
  cursor:pointer;
}
#operativoPeriodBar.v250-option9b .v250-quick-btn:last-child{border-right:0}
#operativoPeriodBar.v250-option9b .v250-quick-btn.active{
  color:#fff;
  background:linear-gradient(100deg,#0d67d8,#1689ff);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.15);
}
#operativoPeriodBar.v250-option9b #operPeriodModeWrap.v250-mode-source{
  display:none!important;
}

/* ===== Fila de controles ===== */
#operativoPeriodBar.v250-option9b > .or-report-filter-grid{
  display:grid!important;
  grid-template-columns:repeat(var(--v250-control-count,4),minmax(0,1fr))!important;
  align-items:end!important;
  gap:12px!important;
  width:100%!important;
  margin:0!important;
}
#globalFilters.v250-option9b{
  display:grid!important;
  grid-template-columns:repeat(var(--v250-commercial-count,5),minmax(0,1fr))!important;
  align-items:end!important;
  gap:12px!important;
}
#globalFilters.v250-option9b.hidden{display:none!important}

#operativoPeriodBar.v250-option9b .or-fcontrol,
#globalFilters.v250-option9b .filter{
  min-width:0!important;
  width:100%!important;
  max-width:none!important;
  margin:0!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol label,
#globalFilters.v250-option9b .filter label{
  display:block!important;
  margin:0 0 5px!important;
  color:#294b70!important;
  font-size:9px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.025em!important;
}
#operativoPeriodBar.v250-option9b .or-fcontrol-icon{display:none!important}

#operativoPeriodBar.v250-option9b select,
#operativoPeriodBar.v250-option9b input,
#globalFilters.v250-option9b select,
#globalFilters.v250-option9b input{
  width:100%!important;
  min-width:0!important;
  max-width:none!important;
  min-height:48px!important;
  height:48px!important;
  padding:7px 38px 7px 13px!important;
  border:1px solid #bcd0e5!important;
  border-radius:11px!important;
  box-sizing:border-box!important;
  background:rgba(255,255,255,.88)!important;
  color:#123f73!important;
  font-size:12px!important;
  font-weight:850!important;
  outline:none!important;
  box-shadow:0 1px 0 rgba(255,255,255,.72) inset!important;
}
#operativoPeriodBar.v250-option9b select:focus,
#operativoPeriodBar.v250-option9b input:focus,
#globalFilters.v250-option9b select:focus,
#globalFilters.v250-option9b input:focus{
  border-color:#3f92ed!important;
  box-shadow:0 0 0 3px rgba(22,137,255,.12)!important;
}

/* Botón igual al boceto 9B */
#operativoPeriodBar.v250-option9b #operPeriodApply,
#globalFilters.v250-option9b #refresh{
  width:100%!important;
  min-width:0!important;
  max-width:none!important;
  min-height:48px!important;
  height:48px!important;
  margin:0!important;
  padding:8px 14px!important;
  border:0!important;
  border-radius:11px!important;
  color:#fff!important;
  font-size:13px!important;
  font-weight:950!important;
  background:linear-gradient(100deg,#0d67d8,#1689ff)!important;
  box-shadow:0 7px 15px rgba(13,103,216,.18)!important;
}
#operativoPeriodBar.v250-option9b #operPeriodApply:hover,
#globalFilters.v250-option9b #refresh:hover{
  filter:brightness(1.035);
  transform:translateY(-1px);
}
#operativoPeriodBar.v250-option9b #operPeriodApply .or-filter-apply-icon{
  width:19px!important;
  height:19px!important;
}

/* Respeta ocultos definidos por cada pestaña. */
#operativoPeriodBar.v250-option9b .hidden,
#operativoPeriodBar.v250-option9b .v249-hidden{
  display:none!important;
}

/* ===== Tablet ===== */
@media(max-width:1050px){
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid,
  #globalFilters.v250-option9b{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
  }
  #operativoPeriodBar.v250-option9b #operPeriodApply,
  #globalFilters.v250-option9b #refresh{
    grid-column:1/-1!important;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-period{
    align-items:stretch;
    flex-direction:column;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-title{flex:none}
}

/* ===== Móvil ===== */
@media(max-width:650px){
  #operativoPeriodBar.v250-option9b,
  #globalFilters.v250-option9b{
    padding:0 8px 9px!important;
    border-radius:12px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-brand,
  #globalFilters.v250-option9b > .v250-filter-brand{
    width:calc(100% + 16px)!important;
    min-height:54px!important;
    margin:0 -8px 9px!important;
    padding:9px 10px!important;
  }
  #operativoPeriodBar.v250-option9b > .or-report-filter-grid,
  #globalFilters.v250-option9b{
    grid-template-columns:1fr!important;
    gap:7px!important;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-buttons{
    overflow-x:auto;
    display:flex;
    -webkit-overflow-scrolling:touch;
  }
  #operativoPeriodBar.v250-option9b .v250-quick-btn{
    flex:1 0 82px;
    min-height:38px;
    font-size:9px;
  }
  #operativoPeriodBar.v250-option9b select,
  #operativoPeriodBar.v250-option9b input,
  #globalFilters.v250-option9b select,
  #globalFilters.v250-option9b input,
  #operativoPeriodBar.v250-option9b #operPeriodApply,
  #globalFilters.v250-option9b #refresh{
    min-height:42px!important;
    height:42px!important;
    font-size:10px!important;
  }
  #operativoPeriodBar.v250-option9b .or-fcontrol label,
  #globalFilters.v250-option9b .filter label{
    font-size:7.5px!important;
  }
}
</style>'''

    js = r'''<script id="v250-option9b-filters-js">
(function(){
  if(window.__V250_OPTION9B_FILTERS)return;
  window.__V250_OPTION9B_FILTERS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  const filterIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5Z"/></svg>';

  function ensureCommercialBrand(){
    const bar=q('#globalFilters');
    if(!bar)return;
    bar.classList.add('v250-option9b');
    let brand=q(':scope > .v250-filter-brand',bar);
    if(!brand){
      brand=document.createElement('div');
      brand.className='v250-filter-brand';
      brand.innerHTML='<span class="v250-filter-brand-icon">'+filterIcon+'</span><div><b>Filtros del reporte</b><small>Define la vista antes de consultar</small></div>';
      bar.prepend(brand);
    }
    const btn=q('#refresh',bar);
    if(btn && btn.textContent.trim()!=='Consultar')btn.textContent='Consultar';

    const visible=qa(':scope > .filter, :scope > button',bar).filter(el=>{
      if(el.classList.contains('hidden'))return false;
      if(el.style.display==='none')return false;
      return true;
    });
    bar.style.setProperty('--v250-commercial-count',String(Math.max(1,Math.min(visible.length,6))));
  }

  function modeWrapVisible(){
    const wrap=q('#operPeriodModeWrap');
    if(!wrap)return false;
    return !wrap.classList.contains('hidden') &&
      !wrap.classList.contains('v249-hidden') &&
      wrap.style.display!=='none';
  }

  function syncQuickActive(){
    const sel=q('#operPeriodMode');
    const quick=q('#operativoPeriodBar .v250-quick-period');
    if(!quick||!sel)return;
    qa('.v250-quick-btn',quick).forEach(btn=>btn.classList.toggle('active',btn.dataset.mode===sel.value));
  }

  function ensureQuickMode(){
    const bar=q('#operativoPeriodBar');
    const grid=q(':scope > .or-report-filter-grid',bar);
    const mode=q('#operPeriodMode');
    const wrap=q('#operPeriodModeWrap');
    if(!bar||!grid||!mode||!wrap)return;

    let quick=q(':scope > .v250-quick-period',bar);
    if(!quick){
      quick=document.createElement('div');
      quick.className='v250-quick-period hidden';
      grid.before(quick);
    }

    const canShow=modeWrapVisible() && mode.options.length>1;
    if(!canShow){
      wrap.classList.remove('v250-mode-source');
      quick.classList.add('hidden');
      return;
    }

    wrap.classList.add('v250-mode-source');
    quick.classList.remove('hidden');

    const opts=[...mode.options].map(o=>({value:o.value,text:o.textContent.trim()}));
    quick.style.setProperty('--v250-quick-count',String(Math.max(1,opts.length)));
    const signature=opts.map(o=>o.value+'='+o.text).join('|');
    if(quick.dataset.signature!==signature){
      quick.dataset.signature=signature;
      quick.innerHTML='<div class="v250-quick-title">Vista operativa</div><div class="v250-quick-buttons">'+
        opts.map(o=>'<button type="button" class="v250-quick-btn" data-mode="'+o.value+'">'+o.text+'</button>').join('')+
        '</div>';
      qa('.v250-quick-btn',quick).forEach(btn=>btn.addEventListener('click',()=>{
        if(mode.value===btn.dataset.mode)return;
        mode.value=btn.dataset.mode;
        syncQuickActive();
        mode.dispatchEvent(new Event('change',{bubbles:true}));
      }));
    }
    syncQuickActive();
  }

  function ensureOperational(){
    const bar=q('#operativoPeriodBar');
    if(!bar)return;
    bar.classList.add('v250-option9b');

    const brand=q(':scope > .or-report-filter-brand',bar);
    if(brand){
      const icon=q('.or-report-filter-brand-icon',brand);
      if(icon)icon.innerHTML=filterIcon;
      const small=q('small',brand);
      if(small)small.textContent='Define la vista antes de consultar';
    }

    ensureQuickMode();

    const grid=q(':scope > .or-report-filter-grid',bar);
    if(!grid)return;
    const controls=qa(':scope > .or-fcontrol, :scope > button',grid).filter(el=>{
      if(el.id==='operPeriodModeWrap' && el.classList.contains('v250-mode-source'))return false;
      if(el.classList.contains('hidden')||el.classList.contains('v249-hidden'))return false;
      if(el.style.display==='none')return false;
      return true;
    });
    grid.style.setProperty('--v250-control-count',String(Math.max(1,Math.min(controls.length,6))));
  }

  function apply(){
    ensureOperational();
    ensureCommercialBrand();
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button,#analysisNav>button,[data-main]')){
      [0,40,140,400].forEach(ms=>setTimeout(apply,ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(['operPeriodMode','operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect','week','store','section','catalog'].includes(e.target?.id||'')){
      setTimeout(apply,0);
      setTimeout(apply,120);
    }
  },true);

  const observer=new MutationObserver(()=>setTimeout(apply,0));
  function start(){
    const op=q('#operativoPeriodBar'),commercial=q('#globalFilters'),nav=q('#operativoNav'),anav=q('#analysisNav');
    [op,commercial,nav,anav].filter(Boolean).forEach(el=>observer.observe(el,{subtree:true,childList:true}));
    apply();
    [120,400,900,1800].forEach(ms=>setTimeout(apply,ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  console.info('[V250] Opción 9B aplicada a filtros de Cambios y Muertos, Operación y Análisis Comercial.');
})();
</script>'''

    @m.app.middleware("http")
    async def v250_option9b_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v250-option9b-filters-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v250-option9b-filters-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V250-OPTION9B-FILTERS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V250] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V250_OPTION9B_FILTERS = True
    print("[V250] Opción 9B global de filtros instalada.",flush=True)
