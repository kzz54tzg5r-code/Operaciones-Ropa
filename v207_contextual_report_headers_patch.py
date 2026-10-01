"""V207 · Encabezados contextuales debajo de pestañas + navegación horizontal con iconos.

Objetivos:
- Operación: el título/subtítulo específico de la vista aparece debajo del dock.
- Cambios y Muertos y Análisis Comercial: fuerzan el mismo patrón horizontal
  con iconos de Operación, incluso frente a reglas antiguas de grid.
- El título cambia automáticamente según la pestaña activa.
- No modifica endpoints, cálculos, filtros, persistencia ni datos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V207_CONTEXTUAL_REPORT_HEADERS", False):
        return

    css = r"""<style id="v207-contextual-report-headers-css">
body[data-v163-module="operativo"] #operativoNav:not(.hidden),
body[data-v163-module="analysis"] #analysisNav:not(.hidden),
body[data-v163-module="operation"] #v200OperationTabs{
  display:flex!important;
  grid-template-columns:none!important;
  flex-wrap:nowrap!important;
  align-items:flex-start!important;
  gap:5px!important;
  width:100%!important;
  max-width:100%!important;
  min-height:70px!important;
  height:auto!important;
  margin:2px 0 4px!important;
  padding:4px 6px 9px!important;
  border:0!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  white-space:nowrap!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
  scroll-snap-type:x mandatory!important;
  scroll-behavior:smooth!important;
  scrollbar-width:none!important;
}
body[data-v163-module="operativo"] #operativoNav::-webkit-scrollbar,
body[data-v163-module="analysis"] #analysisNav::-webkit-scrollbar,
body[data-v163-module="operation"] #v200OperationTabs::-webkit-scrollbar{display:none!important}

body[data-v163-module="operativo"] #operativoNav>button,
body[data-v163-module="analysis"] #analysisNav>button,
body[data-v163-module="operation"] #v200OperationTabs>button{
  flex:0 0 82px!important;
  width:82px!important;
  min-width:82px!important;
  max-width:82px!important;
  height:62px!important;
  min-height:62px!important;
  max-height:62px!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
  touch-action:pan-x!important;
}

.v207-context-header{
  display:block;
  width:100%;
  margin:4px 0 12px;
  padding:0 1px;
}
.v207-context-header.hidden{display:none!important}
.v207-context-title{
  margin:0;
  color:#123f73;
  font-size:25px;
  line-height:1.08;
  font-weight:950;
  letter-spacing:-.028em;
}
.v207-context-sub{
  margin:5px 0 0;
  color:#70849a;
  font-size:10.5px;
  line-height:1.35;
  font-weight:650;
}

body[data-v163-module="operation"] #operativoDynamicTitle,
body[data-v163-module="operation"] #operativoDynamicSub,
body[data-v163-module="operativo"] #operativoDynamicTitle,
body[data-v163-module="operativo"] #operativoDynamicSub{
  display:none!important;
}

@media(min-width:901px){
  body[data-v163-module="operativo"] #operativoNav:not(.hidden),
  body[data-v163-module="analysis"] #analysisNav:not(.hidden),
  body[data-v163-module="operation"] #v200OperationTabs{
    justify-content:center!important;
  }
}

@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav:not(.hidden),
  body[data-v163-module="analysis"] #analysisNav:not(.hidden),
  body[data-v163-module="operation"] #v200OperationTabs{
    justify-content:flex-start!important;
    gap:5px!important;
    min-height:68px!important;
    width:auto!important;
    max-width:none!important;
    margin-left:-6px!important;
    margin-right:-6px!important;
    padding:4px max(12px,calc((100vw - 76px)/2)) 9px!important;
    scroll-padding-inline:calc((100vw - 76px)/2)!important;
  }
  body[data-v163-module="operativo"] #operativoNav>button,
  body[data-v163-module="analysis"] #analysisNav>button,
  body[data-v163-module="operation"] #v200OperationTabs>button{
    flex-basis:76px!important;
    width:76px!important;
    min-width:76px!important;
    max-width:76px!important;
    height:60px!important;
    min-height:60px!important;
    max-height:60px!important;
  }
  .v207-context-header{margin:3px 0 10px;padding:0}
  .v207-context-title{font-size:20px}
  .v207-context-sub{margin-top:4px;font-size:9px}
}
</style>"""

    js = r"""<script id="v207-contextual-report-headers-js">
(function(){
  if(window.__V207_CONTEXTUAL_REPORT_HEADERS)return;
  window.__V207_CONTEXTUAL_REPORT_HEADERS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];

  const operationMeta={
    summary:['Resumen de Operación','Indicadores generales de operación del periodo consultado'],
    daily:['Captura diaria de Operación','Registro diario de actividades operativas por tienda'],
    capture:['Registro de productividad','Captura de actividad, área, piezas y tiempo real'],
    productivity:['Ranking de productividad','Consulta de productividad por colaborador y tienda'],
    standards:['Estándares de productividad','Parámetros base para medición operativa']
  };

  const cmMeta={
    'centro ejecutivo':['Centro Operativo','Resumen ejecutivo de Cambios y Muertos'],
    'centro operativo':['Centro Operativo','Resumen ejecutivo de Cambios y Muertos'],
    'conversión':['Conversión y recuperación','Seguimiento de conversión de devolución a venta'],
    'recuperación económica':['Recuperación económica','Recuperación en pesos derivada de la venta'],
    'recuperación por tienda':['Recuperación por tienda','Comparativo de recuperación por tienda'],
    'productividad por colaborador':['Productividad por colaborador','Desempeño operativo por colaborador'],
    'cumplimiento de recorridos':['Cumplimiento de recorridos','Avance de recorridos contra la meta definida'],
    'índice integral':['Índice integral','Lectura consolidada de los indicadores del reporte'],
    'alertas inteligentes':['Alertas inteligentes','Hallazgos y desviaciones que requieren seguimiento'],
    'carga de datos':['Carga de datos','Actualización y publicación de la base de Cambios y Muertos'],
    'metas y tiendas':['Metas y tiendas','Configuración de metas y alcance por tienda']
  };

  const analysisMeta={
    'macro compañía':['Macro Compañía','Vista general del desempeño comercial a nivel compañía'],
    'acordeón comercial':['Acordeón Comercial','Consulta comercial consolidada por periodo'],
    'tiendas':['Tiendas','Radiografía comercial y comparativo por tienda'],
    'sección / rubro':['Sección / Rubro','Análisis de desempeño por sección y rubro'],
    'ubicación / área':['Ubicación / Área','Consulta por colgado, doblado, jeans y lencería'],
    'checklist lencería':['Checklist Lencería','Seguimiento de campeones y ejecución por familia'],
    'carga de datos':['Carga de datos','Actualización de ventas, capacidades y existencias'],
    'más opciones':['Más opciones','Acceso a reportes comerciales complementarios']
  };

  const svgFallback='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/><path d="M8 12h8M12 8v8"/></svg>';
  const svgByKind={
    operative:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    commercial:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>'
  };

  function norm(v){return String(v||'').replace(/\s+/g,' ').trim().toLowerCase()}

  function labelOf(btn){
    if(!btn)return'';
    const lbl=btn.querySelector('.v206-tab-label,.v203-tab-label');
    return String(lbl?.textContent||btn.textContent||'').replace(/\s+/g,' ').trim();
  }

  function currentModule(){return norm(document.body.dataset.v163Module||'')}

  function ensureHorizontal(host){
    if(!host)return;
    // V213 gobierna estas barras. No reactivar el carrusel ni emitir una
    // mutación de class en cada refresh del propio observer.
    if(!host.classList.contains('v207-icon-tabs'))host.classList.add('v207-icon-tabs');
  }

  function ensureIcons(host,kind){
    if(!host)return;
    qa(':scope > button',host).forEach(btn=>{
      if(btn.querySelector('.v206-tab-icon,.v203-tab-icon'))return;
      const label=labelOf(btn);
      const icon=svgByKind[kind]||svgFallback;
      btn.innerHTML='<span class="v206-tab-icon" aria-hidden="true">'+icon+'</span>'+
                    '<span class="v206-tab-label">'+label+'</span>';
      btn.title=label;
    });
  }

  function activeButton(host){
    return host?.querySelector(':scope > button.active:not(.hidden):not([hidden])')||
           host?.querySelector(':scope > button[aria-selected="true"]:not(.hidden):not([hidden])')||
           host?.querySelector(':scope > button:not(.hidden):not([hidden])')||null;
  }

  function ensureHeader(host,kind){
    if(!host)return null;
    const id='v207Context-'+kind;
    let wrap=document.getElementById(id);
    if(!wrap){
      wrap=document.createElement('section');
      wrap.id=id;
      wrap.className='v207-context-header';
      wrap.setAttribute('aria-live','polite');
      wrap.innerHTML='<h2 class="v207-context-title"></h2><p class="v207-context-sub"></p>';
    }
    if(wrap.previousElementSibling!==host)host.insertAdjacentElement('afterend',wrap);
    return wrap;
  }

  function metaForOperation(btn){
    const key=norm(btn?.dataset?.v200Op||'summary');
    return operationMeta[key]||[labelOf(btn)||'Operación','Consulta operativa'];
  }

  function metaForCm(btn){
    const label=labelOf(btn);
    const key=norm(btn?.dataset?.opview||label);
    return cmMeta[key]||[label||'Cambios y Muertos','Consulta del reporte de Cambios y Muertos'];
  }

  function metaForAnalysis(btn){
    const label=labelOf(btn);
    const key=norm(label);
    const subKey=norm(btn?.dataset?.sub||'');
    if(subKey==='analysis-upload')return ['Carga de datos','Actualización de ventas, capacidades y existencias'];
    return analysisMeta[key]||[label||'Análisis Comercial','Consulta del reporte comercial seleccionado'];
  }

  function updateHeader(host,kind){
    const wrap=ensureHeader(host,kind);if(!wrap)return;
    const btn=activeButton(host);
    const meta=kind==='operation'?metaForOperation(btn):(kind==='cm'?metaForCm(btn):metaForAnalysis(btn));
    const title=q('.v207-context-title',wrap);
    const sub=q('.v207-context-sub',wrap);
    if(title && title.textContent!==meta[0])title.textContent=meta[0];
    if(sub && sub.textContent!==meta[1])sub.textContent=meta[1];
  }

  function refresh(){
    const mod=currentModule();
    const cm=q('#operativoNav'),an=q('#analysisNav'),op=q('#v200OperationTabs');

    if(cm){
      ensureHorizontal(cm);ensureIcons(cm,'operative');
      const h=document.getElementById('v207Context-cm');
      if(h)h.classList.toggle('hidden',mod!=='operativo');
      if(mod==='operativo')updateHeader(cm,'cm');
    }
    if(an){
      ensureHorizontal(an);ensureIcons(an,'commercial');
      const h=document.getElementById('v207Context-analysis');
      if(h)h.classList.toggle('hidden',mod!=='analysis');
      if(mod==='analysis')updateHeader(an,'analysis');
    }
    if(op){
      const h=document.getElementById('v207Context-operation');
      if(h)h.classList.toggle('hidden',mod!=='operation');
      if(mod==='operation')updateHeader(op,'operation');
    }
  }

  document.addEventListener('click',e=>{
    const tab=e.target.closest?.('#operativoNav>button,#analysisNav>button,#v200OperationTabs>button');
    const main=e.target.closest?.('[data-main]');
    if(tab||main)[30,120,320,700].forEach(ms=>setTimeout(refresh,ms));
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(refresh,40));

  const obs=new MutationObserver(mutations=>{
    if(mutations.some(x=>x.type==='childList'||x.attributeName==='class'||x.attributeName==='aria-selected')){
      setTimeout(refresh,0);
    }
  });

  function setup(){
    ['operativoNav','analysisNav','v200OperationTabs'].forEach(id=>{
      const host=document.getElementById(id);
      if(host && host.dataset.v207Observed!=='1'){
        host.dataset.v207Observed='1';
        obs.observe(host,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-selected']});
      }
    });
    refresh();
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});
  else setup();

  [160,500,1200,2400].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('resize',()=>setTimeout(refresh,90),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});

  console.info('[V207] títulos contextuales debajo de pestañas + navegación horizontal con iconos.');
})();
</script>"""

    @m.app.middleware("http")
    async def v207_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v207-contextual-report-headers-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v207-contextual-report-headers-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V207",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V207] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V207_CONTEXTUAL_REPORT_HEADERS=True
    print("[V207] encabezados contextuales y tabs con iconos instalados.",flush=True)
