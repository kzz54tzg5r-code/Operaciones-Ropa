"""V261 · Opción 9 Comercial + filtros operativos automáticos sin botones.

Presentación:
- Análisis Comercial usa la Opción 9 aprobada: card con encabezado azul y filtros.
- Cambios y Muertos conserva el boceto 9B aprobado, sin Consultar ni Restablecer.

Interacción:
- Los botones originales permanecen en DOM sólo como puente de compatibilidad,
  pero quedan ocultos.
- Cambiar Periodo/Tienda/Área/Actividad en Cambios y Muertos ejecuta el mismo
  flujo de consulta que ya existía.
- Los filtros comerciales siguen disparando los onchange nativos existentes.
- No altera cálculos, endpoints, KPIs, tablas ni datos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V261_FILTER_UI_AUTO", False):
        return

    css = r'''<style id="v261-filter-ui-auto-css">
/* =========================================================
   V261 · ANÁLISIS COMERCIAL · OPCIÓN 9
   ========================================================= */
body[data-v163-module="analysis"] #v161FilterBar{
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin:8px 0 12px!important;
  padding:0 12px 12px!important;
  overflow:hidden!important;
  border:1px solid #bfd8f2!important;
  border-radius:16px!important;
  background:linear-gradient(115deg,#f8fbff 0%,#edf6ff 58%,#dceeff 100%)!important;
  box-shadow:0 8px 24px rgba(18,63,115,.08)!important;
  box-sizing:border-box!important;
}
body[data-v163-module="analysis"] #v161FilterBar:not(.on){
  display:none!important;
}
body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand{
  width:calc(100% + 24px)!important;
  min-height:66px!important;
  margin:0 -12px 12px!important;
  padding:12px 18px!important;
  display:flex!important;
  align-items:center!important;
  gap:12px!important;
  color:#fff!important;
  background:linear-gradient(100deg,#0a4b91 0%,#0b67c8 55%,#1187ff 100%)!important;
  border:0!important;
  box-sizing:border-box!important;
}
body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand-icon{
  display:grid!important;
  place-items:center!important;
  flex:0 0 38px!important;
  width:38px!important;
  height:38px!important;
  border-radius:11px!important;
  color:#fff!important;
  background:rgba(255,255,255,.14)!important;
  border:1px solid rgba(255,255,255,.16)!important;
}
body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand-icon svg{
  width:22px!important;
  height:22px!important;
}
body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand b{
  display:block!important;
  margin:0!important;
  color:#fff!important;
  font-size:16px!important;
  line-height:1.05!important;
  font-weight:950!important;
}
body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand small{
  display:block!important;
  margin-top:3px!important;
  color:rgba(255,255,255,.9)!important;
  font-size:10px!important;
  line-height:1.15!important;
  font-weight:650!important;
}

/* La Opción 9 usa una sola franja de filtros, sin botón de consulta. */
body[data-v163-module="analysis"] #v161FilterGrid{
  display:grid!important;
  grid-template-columns:repeat(var(--v261-analysis-count,5),minmax(0,1fr))!important;
  align-items:end!important;
  gap:10px!important;
  width:100%!important;
  min-width:0!important;
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field{
  position:relative!important;
  min-width:0!important;
  width:100%!important;
  padding:4px 8px 7px 42px!important;
  border-right:1px solid #d9e6f3!important;
  background:rgba(255,255,255,.52)!important;
  border-radius:9px!important;
  box-sizing:border-box!important;
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field:last-of-type{
  border-right:0!important;
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field label{
  display:block!important;
  margin:0 0 4px!important;
  color:#637995!important;
  font-size:8px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.025em!important;
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field select,
body[data-v163-module="analysis"] #v161FilterGrid .v161-field input{
  width:100%!important;
  min-width:0!important;
  height:36px!important;
  min-height:36px!important;
  padding:5px 26px 5px 0!important;
  border:0!important;
  border-radius:0!important;
  outline:none!important;
  background:transparent!important;
  box-shadow:none!important;
  color:#113f78!important;
  font-size:11px!important;
  line-height:1!important;
  font-weight:900!important;
}
body[data-v163-module="analysis"] #v161FilterGrid .v166-filter-icon{
  position:absolute!important;
  left:10px!important;
  top:50%!important;
  transform:translateY(-50%)!important;
  display:grid!important;
  place-items:center!important;
  width:24px!important;
  height:24px!important;
  color:#0f76ed!important;
  pointer-events:none!important;
}
body[data-v163-module="analysis"] #v161FilterGrid .v166-filter-icon svg{
  width:21px!important;
  height:21px!important;
}

/* Consultar/Restablecer fuera de la experiencia visual, sin destruir la lógica. */
body[data-v163-module="analysis"] #v161FilterGrid .v161-apply,
body[data-v163-module="analysis"] #globalFilters #refresh,
body[data-v163-module="analysis"] #globalFilters #v254CommercialReset,
body[data-v163-module="analysis"] #globalFilters #v253CommercialReset{
  display:none!important;
}

/* =========================================================
   V261 · CAMBIOS Y MUERTOS · BOCETO APROBADO
   ========================================================= */
body[data-v163-module="operativo"] #operativoPeriodBar{
  width:100%!important;
  max-width:100%!important;
}
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-brand small{
  font-size:0!important;
}
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-brand small::after{
  content:"Define la vista del reporte"!important;
  font-size:10px!important;
}

/* Ocultar visualmente Consultar y Restablecer. */
body[data-v163-module="operativo"] #operPeriodApply,
body[data-v163-module="operativo"] #v254ResetFilters,
body[data-v163-module="operativo"] #v253ResetFilters{
  display:none!important;
}

/* Redistribuir todo el espacio entre Vista + Periodo + Tienda y filtros
   especiales que alguna pestaña necesite conservar. */
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid{
  display:flex!important;
  flex-wrap:nowrap!important;
  align-items:flex-end!important;
  gap:10px!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  padding:0 0 2px!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  box-sizing:border-box!important;
  -webkit-overflow-scrolling:touch!important;
}
body[data-v163-module="operativo"] #operativoPeriodBar .v259-period-view{
  flex:1.45 1 380px!important;
  min-width:330px!important;
}
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid > #operPeriodSelectWrap{
  flex:1 1 250px!important;
  min-width:200px!important;
}
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid > #operStoreWrap{
  flex:1.1 1 280px!important;
  min-width:220px!important;
}
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid > #operAreaWrap,
body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid > #operActivityWrap{
  flex:.9 1 210px!important;
  min-width:175px!important;
}

/* Tablet */
@media(max-width:1199px) and (min-width:768px){
  body[data-v163-module="analysis"] #v161FilterGrid{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
  }
  body[data-v163-module="analysis"] #v161FilterGrid .v161-field{
    border-right:0!important;
  }
}

/* Móvil: conserva controles completos y desplazamiento táctil en una sola fila. */
@media(max-width:767px){
  body[data-v163-module="analysis"] #v161FilterBar{
    padding:0 8px 8px!important;
    border-radius:13px!important;
  }
  body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand{
    width:calc(100% + 16px)!important;
    min-height:54px!important;
    margin:0 -8px 8px!important;
    padding:9px 11px!important;
  }
  body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand b{
    font-size:13px!important;
  }
  body[data-v163-module="analysis"] #v161FilterBar .v261-analysis-brand small{
    font-size:8px!important;
  }
  body[data-v163-module="analysis"] #v161FilterGrid{
    display:flex!important;
    flex-wrap:nowrap!important;
    gap:7px!important;
    overflow-x:auto!important;
    overflow-y:hidden!important;
    padding-bottom:2px!important;
    -webkit-overflow-scrolling:touch!important;
    scroll-snap-type:x proximity!important;
  }
  body[data-v163-module="analysis"] #v161FilterGrid .v161-field{
    flex:0 0 170px!important;
    width:170px!important;
    min-width:170px!important;
    border-right:0!important;
    scroll-snap-align:start!important;
  }

  body[data-v163-module="operativo"] #operativoPeriodBar .v259-period-view{
    flex:0 0 286px!important;
    min-width:286px!important;
  }
  body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid > #operPeriodSelectWrap{
    flex:0 0 190px!important;
    min-width:190px!important;
  }
  body[data-v163-module="operativo"] #operativoPeriodBar > .or-report-filter-grid > #operStoreWrap{
    flex:0 0 210px!important;
    min-width:210px!important;
  }
}
</style>'''

    js = r'''<script id="v261-filter-ui-auto-js">
(function(){
  if(window.__V261_FILTER_UI_AUTO)return;
  window.__V261_FILTER_UI_AUTO=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  const FILTER_ICON='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5Z"/></svg>';

  function moduleName(){
    const x=String(document.body.dataset.v163Module||'').toLowerCase();
    if(x)return x;
    try{
      const main=String(MAIN||'').toLowerCase();
      if(main==='analysis')return'analysis';
      if(main==='operativo')return'operativo';
    }catch(_){}
    return '';
  }

  function ensureAnalysisOption9(){
    if(moduleName()!=='analysis')return;
    const host=q('#v161FilterBar');
    const grid=q('#v161FilterGrid');
    const nav=q('#analysisNav');
    if(!host||!grid)return;

    /* Mantener la Opción 9 justo debajo de las pestañas comerciales. */
    if(nav && nav.nextElementSibling!==host){
      nav.insertAdjacentElement('afterend',host);
    }

    let brand=q(':scope > .v261-analysis-brand',host);
    if(!brand){
      brand=document.createElement('div');
      brand.className='v261-analysis-brand';
      brand.innerHTML='<span class="v261-analysis-brand-icon">'+FILTER_ICON+'</span>'+
        '<div><b>Filtros de Análisis Comercial</b><small>Define la vista del reporte</small></div>';
      host.insertBefore(brand,grid);
    }

    /* El botón se conserva oculto como puente de compatibilidad, pero nunca
       participa en el layout. */
    const apply=q('.v161-apply',grid);
    if(apply){
      apply.setAttribute('aria-hidden','true');
      apply.tabIndex=-1;
    }

    const fields=qa(':scope > .v161-field',grid).filter(el=>getComputedStyle(el).display!=='none');
    grid.style.setProperty('--v261-analysis-count',String(Math.max(1,fields.length)));
  }

  let opTimer=0;
  let opBusy=false;
  let opQueued=false;

  async function runOperationalQuery(){
    if(moduleName()!=='operativo')return;
    if(opBusy){opQueued=true;return}
    const apply=q('#operPeriodApply');
    if(!apply||typeof apply.onclick!=='function')return;

    opBusy=true;
    try{
      /* Invoca exactamente el flujo ya validado de Consultar, sin duplicar
         cálculos ni construir una ruta alternativa. */
      const result=apply.onclick();
      if(result&&typeof result.then==='function')await result;
    }catch(err){
      console.error('[V261] actualización automática operativa',err);
    }finally{
      opBusy=false;
      if(opQueued){
        opQueued=false;
        clearTimeout(opTimer);
        opTimer=setTimeout(runOperationalQuery,80);
      }
    }
  }

  function scheduleOperationalQuery(delay=90){
    clearTimeout(opTimer);
    opTimer=setTimeout(runOperationalQuery,delay);
  }

  function bindOperationalAuto(){
    ['operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect'].forEach(id=>{
      const el=q('#'+id);
      if(!el||el.dataset.v261Auto==='1')return;
      el.dataset.v261Auto='1';
      el.addEventListener('change',()=>{
        /* Esperar a que los handlers nativos sincronicen OPER_PERIOD/estado
           antes de ejecutar la misma consulta que hacía el botón. */
        scheduleOperationalQuery(100);
      });
    });
  }

  function ensureOperationalVisual(){
    if(moduleName()!=='operativo')return;
    const bar=q('#operativoPeriodBar');
    if(!bar)return;
    const apply=q('#operPeriodApply');
    const reset=q('#v254ResetFilters');
    if(apply){
      apply.setAttribute('aria-hidden','true');
      apply.tabIndex=-1;
    }
    if(reset){
      reset.setAttribute('aria-hidden','true');
      reset.tabIndex=-1;
    }
    bindOperationalAuto();
  }

  function ensure(){
    ensureAnalysisOption9();
    ensureOperationalVisual();
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#analysisNav>button,#operativoNav>button')){
      [0,40,120,320,700].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  document.addEventListener('change',e=>{
    if(e.target?.matches?.('#week,#store,#section,#catalog,#v166StatusSelect')){
      [0,60,160].forEach(ms=>setTimeout(ensure,ms));
    }
  },false);

  const observer=new MutationObserver(()=>{
    clearTimeout(window.__v261EnsureTimer);
    window.__v261EnsureTimer=setTimeout(ensure,25);
  });

  function start(){
    const main=q('.main')||document.body;
    if(main)observer.observe(main,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    ensure();
    [100,300,700,1400,2400].forEach(ms=>setTimeout(ensure,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V261] Opción 9 Comercial + filtros operativos automáticos sin botones.');
})();
</script>'''

    @m.app.middleware("http")
    async def v261_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v261-filter-ui-auto-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v261-filter-ui-auto-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V261-FILTER-UI-AUTO",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V261] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V261_FILTER_UI_AUTO = True
    print("[V261] Opción 9 Comercial + auto-filtros operativos instalados.",flush=True)
