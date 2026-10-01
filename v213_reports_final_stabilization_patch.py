"""V213 · estabilización final de reportes, navegación y filtros.

Objetivo:
- una sola navegación por módulo, sin carruseles que reordenen el DOM;
- Cambios y Muertos, Operación y Análisis Comercial totalmente aislados;
- pestañas con el mismo lenguaje visual de Operación;
- filtros debajo de las pestañas/título;
- Cambios y Muertos vuelve a usar su renderer real, no el Centro legacy vacío;
- Análisis Comercial siempre abre una pestaña comercial válida y conserva
  Periodo/Tienda/Sección/Catálogo/Estatus;
- Operación abre su Resumen y conserva sus cinco pestañas;
- no se tocan cálculos, endpoints, archivos históricos ni permisos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V213_REPORTS_FINAL_STABILIZATION", False):
        return

    css = r"""<style id="v213-reports-final-css">
:root{
  --v213-blue:#0878df;
  --v213-navy:#0d4f8b;
  --v213-ink:#123f73;
  --v213-muted:#70849a;
  --v213-line:#d6e3f0;
  --v213-soft:#f6f9fd;
}

/* ==========================================================
   UNA SOLA NAVEGACIÓN POR MÓDULO
   ========================================================== */
#operativoNav.hidden,#analysisNav.hidden,#v200OperationTabs.hidden,
#operativoNav[hidden],#analysisNav[hidden],#v200OperationTabs[hidden],
#operativoNav>button.hidden,#analysisNav>button.hidden,#v200OperationTabs>button.hidden,
#operativoNav>button[hidden],#analysisNav>button[hidden],#v200OperationTabs>button[hidden]{
  display:none!important;
}

body[data-v213-module="operativo"] #operativoNav:not(.hidden){
  display:flex!important;
}
body[data-v213-module="operativo"] #analysisNav,
body[data-v213-module="operativo"] #v200OperationTabs{
  display:none!important;
}

body[data-v213-module="analysis"] #analysisNav:not(.hidden){
  display:flex!important;
}
body[data-v213-module="analysis"] #operativoNav,
body[data-v213-module="analysis"] #v200OperationTabs{
  display:none!important;
}

body[data-v213-module="operation"] #v200OperationTabs:not(.hidden){
  display:flex!important;
}
body[data-v213-module="operation"] #operativoNav,
body[data-v213-module="operation"] #analysisNav{
  display:none!important;
}

body[data-v213-module="users"] :is(#operativoNav,#analysisNav,#v200OperationTabs),
body[data-v213-module="share"] :is(#operativoNav,#analysisNav,#v200OperationTabs){
  display:none!important;
}

/* Retirar las capas visuales antiguas, sin mover botones ni destruir listeners. */
#v161FilterBar,
.rt-icon-rail-v1-current,
.rt-icon-rail-v1-indicator,
.rt-worldcup-current,
.rt-worldcup-pedestal,
.rt-mundial-current,
.rt-m7-current{
  display:none!important;
}
.rt-carousel-shell,
.rt-icon-rail-v1-shell{
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  margin:0!important;
  padding:0!important;
  background:transparent!important;
  border:0!important;
  box-shadow:none!important;
}
.rt-carousel-shell:before,.rt-carousel-shell:after,
.rt-icon-rail-v1-shell:before,.rt-icon-rail-v1-shell:after{
  display:none!important;
  content:none!important;
}

/* Ocultar títulos duplicados del renderer operativo; V213 deja uno solo. */
body[data-v213-module="operativo"] #operativoDynamicTitle,
body[data-v213-module="operativo"] #operativoDynamicSub,
body[data-v213-module="operation"] #operativoDynamicTitle,
body[data-v213-module="operation"] #operativoDynamicSub,
#v207Context-cm,#v207Context-analysis,#v207Context-operation{
  display:none!important;
}

/* ==========================================================
   PESTAÑAS: MISMO PATRÓN PARA LOS TRES REPORTES
   ========================================================== */
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs){
  align-items:stretch!important;
  justify-content:flex-start!important;
  flex-wrap:nowrap!important;
  gap:9px!important;
  width:100%!important;
  max-width:100%!important;
  min-height:96px!important;
  height:auto!important;
  margin:4px 0 8px!important;
  padding:7px 3px 13px!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  background:transparent!important;
  border:0!important;
  border-radius:0!important;
  box-shadow:none!important;
  white-space:nowrap!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important;
  scroll-snap-type:x mandatory!important;
  overscroll-behavior-x:contain!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)::-webkit-scrollbar{
  display:none!important;
}

body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button{
  position:relative!important;
  display:flex!important;
  flex:0 0 112px!important;
  width:112px!important;
  min-width:112px!important;
  max-width:112px!important;
  min-height:82px!important;
  height:82px!important;
  max-height:82px!important;
  margin:0!important;
  padding:8px 7px 10px!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  border:1px solid var(--v213-line)!important;
  border-radius:18px!important;
  background:#fff!important;
  color:#55718d!important;
  box-shadow:0 5px 18px rgba(28,72,116,.06)!important;
  transform:none!important;
  opacity:1!important;
  font-size:9px!important;
  line-height:1.12!important;
  font-weight:850!important;
  white-space:normal!important;
  text-align:center!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
  overflow:visible!important;
}

body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button:hover{
  transform:translateY(-1px)!important;
  border-color:#b7cfe7!important;
  box-shadow:0 8px 22px rgba(28,72,116,.10)!important;
}

/* Sólo la iconografía canónica. */
body[data-v213-module] :is(#operativoNav,#analysisNav) .rt-tab-icon,
body[data-v213-module] :is(#operativoNav,#analysisNav) .rt-tab-label,
body[data-v213-module] :is(#operativoNav,#analysisNav) .v166-tab-icon{
  display:none!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) .v206-tab-icon,
body[data-v213-module="operation"] #v200OperationTabs .v203-tab-icon{
  display:grid!important;
  place-items:center!important;
  flex:0 0 38px!important;
  width:38px!important;
  min-width:38px!important;
  max-width:38px!important;
  height:38px!important;
  min-height:38px!important;
  max-height:38px!important;
  margin:0!important;
  padding:0!important;
  border:1px solid #dce8f4!important;
  border-radius:13px!important;
  background:#edf5fd!important;
  color:#567c9f!important;
  box-shadow:none!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) .v206-tab-icon svg,
body[data-v213-module="operation"] #v200OperationTabs .v203-tab-icon svg{
  display:block!important;
  width:21px!important;
  height:21px!important;
  min-width:21px!important;
  max-width:21px!important;
  stroke:currentColor!important;
  fill:none!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) .v206-tab-label,
body[data-v213-module="operation"] #v200OperationTabs .v203-tab-label{
  position:static!important;
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  height:auto!important;
  min-height:0!important;
  margin:0!important;
  padding:0!important;
  overflow:visible!important;
  clip:auto!important;
  clip-path:none!important;
  white-space:normal!important;
  text-overflow:clip!important;
  color:inherit!important;
  font-size:9px!important;
  line-height:1.12!important;
  font-weight:850!important;
  text-align:center!important;
  opacity:1!important;
}

body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button.active,
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button[aria-selected="true"]{
  color:#fff!important;
  border-color:#0a5da7!important;
  background:linear-gradient(145deg,var(--v213-navy) 0%,var(--v213-blue) 100%)!important;
  box-shadow:0 12px 28px rgba(13,79,139,.24)!important;
  transform:translateY(-2px)!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav)>button.active .v206-tab-icon,
body[data-v213-module] :is(#operativoNav,#analysisNav)>button[aria-selected="true"] .v206-tab-icon,
body[data-v213-module="operation"] #v200OperationTabs>button.active .v203-tab-icon,
body[data-v213-module="operation"] #v200OperationTabs>button[aria-selected="true"] .v203-tab-icon{
  background:rgba(255,255,255,.14)!important;
  border-color:rgba(255,255,255,.22)!important;
  color:#fff!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button.active:after,
body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button[aria-selected="true"]:after{
  content:""!important;
  display:block!important;
  position:absolute!important;
  left:50%!important;
  right:auto!important;
  top:auto!important;
  bottom:-7px!important;
  width:32px!important;
  height:4px!important;
  border-radius:999px!important;
  background:#1185ef!important;
  transform:translateX(-50%)!important;
  box-shadow:0 2px 7px rgba(17,133,239,.24)!important;
}

/* ==========================================================
   TÍTULO ÚNICO DEL REPORTE
   ========================================================== */
#v213ReportContext{
  width:100%;
  margin:5px 0 10px;
  padding:0 2px;
}
#v213ReportContext h2{
  margin:0;
  color:#0b3f75;
  font-size:26px;
  line-height:1.06;
  font-weight:950;
  letter-spacing:-.03em;
}
#v213ReportContext p{
  margin:5px 0 0;
  color:#70849a;
  font-size:9px;
  line-height:1.3;
  font-weight:750;
}

/* ==========================================================
   FILTRO OPERATIVO NATIVO: C&M Y OPERACIÓN
   ========================================================== */
#operativoPeriodBar{display:none!important}
body.v213-show-oper-filter #operativoPeriodBar{
  display:block!important;
  border:1px solid var(--v213-line)!important;
  border-radius:18px!important;
  background:#fff!important;
  box-shadow:0 8px 24px rgba(14,79,139,.08)!important;
  overflow:hidden!important;
  margin:8px 0 12px!important;
}
body.v213-show-oper-filter #operativoPeriodBar .or-report-filter-brand,
body.v213-show-oper-filter #operativoPeriodBar .v161-filter-head,
body.v213-show-oper-filter #operativoPeriodBar .filter-head{
  background:linear-gradient(135deg,#103f72,#0878df)!important;
  color:#fff!important;
}
body.v213-show-oper-filter #operativoPeriodBar label{
  color:#61758b!important;
  font-size:8px!important;
  font-weight:900!important;
  letter-spacing:.04em!important;
}
body.v213-show-oper-filter #operativoPeriodBar select,
body.v213-show-oper-filter #operativoPeriodBar input{
  min-height:44px!important;
  border:1px solid #cbd9e8!important;
  border-radius:12px!important;
  background:#fbfdff!important;
  color:var(--v213-ink)!important;
  box-shadow:none!important;
}
body.v213-show-oper-filter #operPeriodApply{
  min-height:44px!important;
  border:0!important;
  border-radius:12px!important;
  background:linear-gradient(135deg,#176fe8,#0a83ef)!important;
  color:#fff!important;
  font-weight:950!important;
  box-shadow:0 8px 18px rgba(23,111,232,.18)!important;
}

/* ==========================================================
   FILTRO ÚNICO DE ANÁLISIS COMERCIAL
   ========================================================== */
body[data-v213-module="analysis"] #globalFilters,
body[data-v213-module="analysis"] .filters{
  display:none!important;
}
#v213AnalysisFilterCard{
  display:none;
  width:100%;
  max-width:100%;
  margin:8px 0 12px;
  padding:0;
  border:1px solid var(--v213-line);
  border-radius:18px;
  background:#fff;
  box-shadow:0 8px 24px rgba(14,79,139,.08);
  overflow:hidden;
}
body[data-v213-module="analysis"] #v213AnalysisFilterCard.on{display:block}
#v213AnalysisFilterCard .v213-filter-head{
  min-height:56px;
  display:flex;
  align-items:center;
  gap:11px;
  padding:10px 14px;
  color:#fff;
  background:linear-gradient(135deg,#103f72,#0878df);
}
.v213-filter-head-icon{
  width:34px;height:34px;min-width:34px;border-radius:10px;
  display:grid;place-items:center;background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.12);
}
.v213-filter-head-icon svg{width:18px;height:18px;stroke:currentColor;fill:none}
.v213-filter-head b{display:block;font-size:12px;font-weight:950;line-height:1.1}
.v213-filter-head small{display:block;margin-top:3px;font-size:8px;font-weight:700;opacity:.84}
.v213-filter-grid{
  display:grid;
  grid-template-columns:repeat(5,minmax(120px,1fr)) auto;
  gap:8px;
  align-items:end;
  padding:12px 13px 13px;
}
.v213-field{position:relative;min-width:0}
.v213-field.hidden{display:none!important}
.v213-field label{
  display:block;margin:0 0 5px 2px;color:#61758b;
  font-size:8px;font-weight:950;text-transform:uppercase;letter-spacing:.04em;
}
.v213-field select{
  width:100%;height:44px;min-width:0;
  border:1px solid #cbd9e8;border-radius:12px;background:#fbfdff;
  color:var(--v213-ink);padding:7px 30px 7px 10px;
  font-size:10px;font-weight:850;outline:none;
}
.v213-filter-apply{
  height:44px;min-width:126px;padding:0 18px;border:0;border-radius:12px;
  background:linear-gradient(135deg,#176fe8,#0a83ef);
  color:#fff;font-size:9px;font-weight:950;cursor:pointer;
  box-shadow:0 8px 18px rgba(23,111,232,.18);
}

/* Contenido: no volver a mostrar el Centro legacy con guiones. */
body[data-v213-module="operativo"] #operativoCentro,
body[data-v213-module="operation"] #operativoCentro{
  display:none!important;
}
body[data-v213-module="operativo"] #operativoDynamic,
body[data-v213-module="operation"] #operativoDynamic{
  display:block!important;
}

/* Responsive coherente para escritorio reducido y móvil. */
@media(max-width:1120px){
  .v213-filter-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .v213-filter-apply{width:100%}
}
@media(max-width:900px){
  body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs){
    gap:8px!important;
    width:auto!important;
    max-width:none!important;
    min-height:92px!important;
    margin-left:-13px!important;
    margin-right:-13px!important;
    padding:7px max(14px,calc((100vw - 112px)/2)) 13px!important;
    scroll-padding-inline:calc((100vw - 112px)/2)!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav,#v200OperationTabs)>button{
    flex:0 0 112px!important;
    width:112px!important;
    min-width:112px!important;
    max-width:112px!important;
    min-height:76px!important;
    height:76px!important;
    max-height:76px!important;
    border-radius:17px!important;
    font-size:8.2px!important;
    padding:7px 6px 9px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v206-tab-icon,
  body[data-v213-module="operation"] #v200OperationTabs .v203-tab-icon{
    width:34px!important;min-width:34px!important;max-width:34px!important;
    height:34px!important;min-height:34px!important;max-height:34px!important;
    flex-basis:34px!important;border-radius:12px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v206-tab-icon svg,
  body[data-v213-module="operation"] #v200OperationTabs .v203-tab-icon svg{
    width:19px!important;height:19px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v206-tab-label,
  body[data-v213-module="operation"] #v200OperationTabs .v203-tab-label{
    font-size:8.2px!important;
  }
  #v213ReportContext h2{font-size:21px}
  #v213ReportContext p{font-size:9px}
  #v213AnalysisFilterCard{border-radius:15px;margin:7px 0 11px}
  #v213AnalysisFilterCard .v213-filter-head{min-height:54px;padding:9px 11px}
  .v213-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:10px}
  .v213-field select{height:43px;font-size:12px}
  .v213-filter-apply{grid-column:1/-1;width:100%;height:44px;font-size:11px}
}
</style>"""

    js = r"""<script id="v213-reports-final-js">
(function(){
  if(window.__V213_REPORTS_FINAL)return;
  window.__V213_REPORTS_FINAL=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const norm=v=>String(v||'').replace(/\s+/g,' ').trim().toLowerCase();
  let moduleSeq=0;

  const meta={
    operativo:{
      'centro ejecutivo':['Centro Operativo','Resumen ejecutivo de Cambios y Muertos'],
      'centro operativo':['Centro Operativo','Resumen ejecutivo de Cambios y Muertos'],
      'conversión':['Conversión y recuperación','Seguimiento de devolución a venta en la misma semana ISO'],
      'recuperación económica':['Recuperación económica','Recuperación en pesos derivada de la venta'],
      'recuperación por tienda':['Recuperación por tienda','Comparativo de recuperación por tienda'],
      'productividad por colaborador':['Productividad por colaborador','Desempeño operativo por colaborador'],
      'cumplimiento de recorridos':['Cumplimiento de recorridos','Avance de recorridos contra la meta definida'],
      'índice integral':['Índice integral','Lectura consolidada de conversión, productividad y recorridos'],
      'alertas inteligentes':['Alertas inteligentes','Hallazgos y desviaciones que requieren seguimiento'],
      'carga de datos':['Carga de datos','Actualización y publicación de la base de Cambios y Muertos'],
      'metas y tiendas':['Metas y tiendas','Configuración de metas y alcance por tienda']
    },
    analysis:{
      macro:['Macro Compañía','Vista general del desempeño comercial a nivel compañía'],
      accordion:['Acordeón Comercial','Consulta comercial consolidada por periodo'],
      stores:['Tiendas','Radiografía comercial y comparativo por tienda'],
      sections:['Sección / Rubro','Análisis de desempeño por sección y rubro'],
      areas:['Ubicación / Área','Consulta por colgado, doblado, jeans y lencería'],
      'lingerie-checklist':['Checklist Lencería','Seguimiento de campeones y ejecución por familia'],
      more:['Más opciones','Acceso a reportes comerciales complementarios'],
      'analysis-upload':['Carga de datos','Actualización de ventas, capacidades y existencias']
    },
    operation:{
      summary:['Resumen de Operación','Indicadores generales de operación del periodo consultado'],
      daily:['Captura diaria','Registro diario de actividades operativas por tienda'],
      capture:['Cargar productividad','Actividad, área, piezas y tiempo real por colaborador'],
      productivity:['Productividad','Ranking por colaborador y tienda'],
      standards:['Estándares Operativos','Niveles, rangos de antigüedad y metas de productividad']
    }
  };

  function visibleButton(host,selector='button'){
    if(!host)return null;
    return qa(':scope > '+selector,host).find(x=>
      !x.hidden && !x.classList.contains('hidden') &&
      x.getAttribute('aria-hidden')!=='true' &&
      getComputedStyle(x).display!=='none'
    )||null;
  }

  function cleanLegacyVisuals(){
    qa('.rt-icon-rail-v1-current,.rt-icon-rail-v1-indicator,.rt-worldcup-current,.rt-worldcup-pedestal,.rt-mundial-current,.rt-m7-current')
      .forEach(x=>x.remove());
    ['operativoNav','analysisNav'].forEach(id=>{
      const host=document.getElementById(id);if(!host)return;
      host.classList.remove('rt-icon-rail-v1','rt-icon-has-user-selection');
      qa(':scope > button',host).forEach(b=>b.classList.remove('rt-icon-user-active'));
    });
  }

  function setModule(mod){
    document.body.dataset.v213Module=mod;
    document.body.dataset.v163Module=mod;
    document.body.classList.remove('v213-show-oper-filter');

    qa('[data-main]').forEach(x=>x.classList.toggle('active',String(x.dataset.main||'')===mod));

    const cm=q('#operativoNav'),an=q('#analysisNav');
    if(cm)cm.classList.toggle('hidden',mod!=='operativo');
    if(an)an.classList.toggle('hidden',mod!=='analysis');
    q('#globalFilters')?.classList.add('hidden');

    const op=q('#v200OperationTabs');
    if(op)op.classList.toggle('hidden',mod!=='operation');

    cleanLegacyVisuals();
  }

  function currentCmName(){
    try{
      if(typeof OP_VIEW!=='undefined' && OP_VIEW)return String(OP_VIEW);
    }catch(_){}
    const b=q('#operativoNav>button.active:not(.hidden):not([hidden])');
    return b?.dataset.opview||'Centro Ejecutivo';
  }

  function currentAnalysisSub(){
    try{
      if(typeof SUB!=='undefined' && SUB)return String(SUB);
    }catch(_){}
    return q('#analysisNav>button.active:not(.hidden):not([hidden])')?.dataset.sub||'macro';
  }

  function currentOperationTab(){
    return String(window.V149_OPERATION_TAB||window.V125_OPERATION_TAB||'summary');
  }

  function contextFor(mod){
    if(mod==='operativo'){
      const name=currentCmName();
      return meta.operativo[norm(name)]||[name||'Cambios y Muertos','Consulta operativa'];
    }
    if(mod==='analysis'){
      const sub=currentAnalysisSub();
      return meta.analysis[sub]||['Análisis Comercial','Consulta comercial'];
    }
    if(mod==='operation'){
      const tab=currentOperationTab();
      return meta.operation[tab]||['Operación','Control diario y productividad'];
    }
    return['Operaciones Ropa',''];
  }

  function navFor(mod){
    if(mod==='operativo')return q('#operativoNav');
    if(mod==='analysis')return q('#analysisNav');
    if(mod==='operation')return q('#v200OperationTabs');
    return null;
  }

  function ensureContext(mod){
    const nav=navFor(mod);if(!nav)return null;
    let box=q('#v213ReportContext');
    if(!box){
      box=document.createElement('section');
      box.id='v213ReportContext';
      box.innerHTML='<h2></h2><p></p>';
    }
    if(box.previousElementSibling!==nav)nav.insertAdjacentElement('afterend',box);
    const [title,sub]=contextFor(mod);
    q('h2',box).textContent=title;
    q('p',box).textContent=sub;
    return box;
  }

  function markActive(host,btn){
    if(!host||!btn)return;
    qa(':scope > button',host).forEach(x=>{
      const on=x===btn;
      x.classList.toggle('active',on);
      x.setAttribute('aria-selected',on?'true':'false');
    });
  }

  function showOperationalFilter(mod){
    let show=false;
    if(mod==='operativo'){
      const name=norm(currentCmName());
      const title=norm(q('#operativoDynamicTitle')?.textContent||'');
      show=!!name && name!=='carga de datos' && !title.includes('metas y tiendas');
    }else if(mod==='operation'){
      show=['summary','daily','productivity'].includes(currentOperationTab());
    }
    document.body.classList.toggle('v213-show-oper-filter',show);
    const bar=q('#operativoPeriodBar');
    if(bar){
      bar.classList.toggle('hidden',!show);
      if(show)bar.style.removeProperty('display');
    }
  }

  function copyOptions(src,dst){
    if(!src||!dst)return;
    const sig=[...src.options].map(o=>o.value+'|'+o.text).join('¦');
    if(dst.dataset.v213sig!==sig){
      dst.innerHTML='';
      [...src.options].forEach(o=>dst.add(new Option(o.text,o.value)));
      dst.dataset.v213sig=sig;
    }
    if([...dst.options].some(o=>o.value===src.value))dst.value=src.value;
    else if(dst.options.length)dst.selectedIndex=0;
    dst.disabled=!!src.disabled;
  }

  function ensureStatusProxy(){
    let field=q('#v166StatusField');
    let sel=q('#v166StatusSelect');
    if(!field){
      field=document.createElement('div');
      field.id='v166StatusField';
      field.hidden=true;
      field.style.display='none';
      field.innerHTML='<select id="v166StatusSelect"><option value="Todos">Todos</option></select>';
      document.body.appendChild(field);
      sel=q('#v166StatusSelect');
    }
    return sel;
  }

  function ensureAnalysisFilter(){
    let card=q('#v213AnalysisFilterCard');
    if(!card){
      card=document.createElement('section');
      card.id='v213AnalysisFilterCard';
      card.innerHTML=
        '<div class="v213-filter-head">'+
          '<span class="v213-filter-head-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h16M7 12h10m-7 7h4"/></svg></span>'+
          '<div><b>Filtros del reporte</b><small>Define la vista comercial antes de consultar</small></div>'+
        '</div>'+
        '<div class="v213-filter-grid">'+
          '<div class="v213-field" data-v213-field="period"><label>Periodo</label><select id="v213AnalysisPeriod"></select></div>'+
          '<div class="v213-field" data-v213-field="store"><label>Tienda</label><select id="v213AnalysisStore"></select></div>'+
          '<div class="v213-field" data-v213-field="section"><label>Sección</label><select id="v213AnalysisSection"></select></div>'+
          '<div class="v213-field" data-v213-field="catalog"><label>Catálogo</label><select id="v213AnalysisCatalog"></select></div>'+
          '<div class="v213-field" data-v213-field="status"><label>Estatus</label><select id="v213AnalysisStatus"><option value="Todos">Todos</option></select></div>'+
          '<button type="button" class="v213-filter-apply" id="v213AnalysisApply">Consultar</button>'+
        '</div>';
    }
    const context=ensureContext('analysis');
    if(context && card.previousElementSibling!==context)context.insertAdjacentElement('afterend',card);
    return card;
  }

  async function loadAnalysisStatus(){
    const view=q('#v213AnalysisStatus');
    const proxy=ensureStatusProxy();
    if(!view||!proxy)return;
    const week=q('#week')?.value||'';
    if(view.dataset.loadedFor===String(week)){
      proxy.value=view.value||'Todos';
      return;
    }
    try{
      const d=typeof api==='function'
        ?await api('/api/commercial/status-options-v166?week='+encodeURIComponent(week),{timeoutMs:60000})
        :await fetch('/api/commercial/status-options-v166?week='+encodeURIComponent(week),{credentials:'same-origin'}).then(r=>r.json());
      const cur=view.value||proxy.value||'Todos';
      const vals=['Todos',...(d.values||[])];
      view.innerHTML='';proxy.innerHTML='';
      vals.forEach(x=>{view.add(new Option(x,x));proxy.add(new Option(x,x))});
      if(vals.includes(cur)){view.value=cur;proxy.value=cur}
      view.dataset.loadedFor=String(week);
    }catch(e){
      console.warn('[V213] Estatus comercial',e);
    }
  }

  function bindAnalysisFilter(card){
    if(card.dataset.v213Bound==='1')return;
    card.dataset.v213Bound='1';

    q('#v213AnalysisPeriod')?.addEventListener('change',e=>{
      const x=q('#week');
      if(x){x.value=e.target.value;x.dispatchEvent(new Event('change',{bubbles:true}))}
      const status=q('#v213AnalysisStatus');
      if(status)status.dataset.loadedFor='';
      setTimeout(loadAnalysisStatus,30);
    });
    q('#v213AnalysisStore')?.addEventListener('change',e=>{
      const x=q('#store');if(x)x.value=e.target.value;
    });
    q('#v213AnalysisSection')?.addEventListener('change',e=>{
      const x=q('#section');if(x)x.value=e.target.value;
    });
    q('#v213AnalysisCatalog')?.addEventListener('change',e=>{
      const x=q('#catalog');if(x)x.value=e.target.value;
    });
    q('#v213AnalysisStatus')?.addEventListener('change',e=>{
      const p=ensureStatusProxy();if(p)p.value=e.target.value;
    });

    q('#v213AnalysisApply')?.addEventListener('click',async()=>{
      const pairs=[
        ['#week','#v213AnalysisPeriod'],
        ['#store','#v213AnalysisStore'],
        ['#section','#v213AnalysisSection'],
        ['#catalog','#v213AnalysisCatalog']
      ];
      pairs.forEach(([nativeId,facadeId])=>{
        const n=q(nativeId),f=q(facadeId);
        if(n&&f&&[...n.options].some(o=>o.value===f.value))n.value=f.value;
      });
      const proxy=ensureStatusProxy();
      if(proxy)proxy.value=q('#v213AnalysisStatus')?.value||'Todos';

      try{
        if(typeof refreshActiveCommercialTab==='function')await refreshActiveCommercialTab();
        else if(typeof loadDash==='function')await loadDash();
      }catch(e){
        console.error('[V213] Consulta comercial',e);
      }
      setModule('analysis');
      ensureContext('analysis');
      setTimeout(syncAnalysisFilter,30);
    });
  }

  async function syncAnalysisFilter(){
    if(document.body.dataset.v213Module!=='analysis')return;
    const card=ensureAnalysisFilter();
    const sub=currentAnalysisSub();
    if(sub==='analysis-upload'){
      card.classList.remove('on');
      return;
    }

    copyOptions(q('#week'),q('#v213AnalysisPeriod'));
    copyOptions(q('#store'),q('#v213AnalysisStore'));
    copyOptions(q('#section'),q('#v213AnalysisSection'));
    copyOptions(q('#catalog'),q('#v213AnalysisCatalog'));

    const storeField=q('[data-v213-field="store"]',card);
    const sectionField=q('[data-v213-field="section"]',card);
    const catalogField=q('[data-v213-field="catalog"]',card);

    storeField?.classList.toggle('hidden',sub==='stores');
    const lingerie=sub==='lingerie-checklist';
    sectionField?.classList.toggle('hidden',lingerie);
    catalogField?.classList.toggle('hidden',lingerie);

    bindAnalysisFilter(card);
    card.classList.add('on');
    await loadAnalysisStatus();
  }

  function syncChrome(mod){
    setModule(mod);
    ensureContext(mod);
    showOperationalFilter(mod);
    if(mod==='analysis')syncAnalysisFilter();
    const ac=q('#v213AnalysisFilterCard');
    if(ac && mod!=='analysis')ac.classList.remove('on');
  }

  async function openCambios(){
    const seq=++moduleSeq;
    try{MAIN='operativo'}catch(_){}
    setModule('operativo');

    if(typeof showPage==='function')showPage('operativo');
    q('#operativoCentro')?.classList.add('hidden');
    q('#operativoDynamic')?.classList.remove('hidden');
    if(q('#operativoDynamicContent'))q('#operativoDynamicContent').innerHTML='<div class="infoempty">Cargando Cambios y Muertos…</div>';

    const host=q('#operativoNav');
    const btn=visibleButton(host);
    const name=btn?.dataset.opview||'Centro Ejecutivo';
    if(btn)markActive(host,btn);
    try{OP_VIEW=name}catch(_){}
    try{OPER_PERIOD={type:'month',value:''}}catch(_){}

    try{
      if(typeof refreshOperativoMeta==='function')await refreshOperativoMeta();
      if(seq!==moduleSeq)return;
      if(typeof window.renderOperativoView==='function')await window.renderOperativoView(name,true);
      if(seq!==moduleSeq)return;
    }catch(e){
      console.error('[V213] Cambios y Muertos',e);
      if(q('#operativoDynamicContent'))q('#operativoDynamicContent').innerHTML='<div class="infoempty">No fue posible abrir Cambios y Muertos: '+String(e.message||e)+'</div>';
    }
    syncChrome('operativo');
  }

  async function openAnalysis(){
    const seq=++moduleSeq;
    try{MAIN='analysis'}catch(_){}
    setModule('analysis');

    const host=q('#analysisNav');
    const btn=visibleButton(host);
    const sub=btn?.dataset.sub||'macro';
    if(btn)markActive(host,btn);

    try{
      if(typeof goSub==='function')await goSub(sub);
      if(seq!==moduleSeq)return;
    }catch(e){
      console.error('[V213] Análisis Comercial',e);
    }
    syncChrome('analysis');
  }

  async function openOperation(){
    const seq=++moduleSeq;
    try{MAIN='operation'}catch(_){}
    setModule('operation');

    if(typeof showPage==='function')showPage('operativo');
    q('#operativoCentro')?.classList.add('hidden');
    q('#operativoDynamic')?.classList.remove('hidden');

    const ht=q('#heroTitle'),hs=q('#heroSub');
    if(ht)ht.textContent='Operación';
    if(hs)hs.textContent='Control diario, productividad por colaborador y eficiencia de mercancía';

    try{OP_VIEW='Operación'}catch(_){}
    try{OPER_PERIOD={type:'month',value:''}}catch(_){}
    window.V149_OPERATION_TAB='summary';
    window.V125_OPERATION_TAB='summary';

    try{
      if(typeof window.renderOperativoView==='function')await window.renderOperativoView('Operación',true);
      if(seq!==moduleSeq)return;
    }catch(e){
      console.error('[V213] Operación',e);
      if(q('#operativoDynamicContent'))q('#operativoDynamicContent').innerHTML='<div class="infoempty">No fue posible abrir Operación: '+String(e.message||e)+'</div>';
    }

    setModule('operation');
    q('#v200OperationTabs')?.classList.remove('hidden');
    ensureContext('operation');
    showOperationalFilter('operation');
    if(ht)ht.textContent='Operación';
    if(hs)hs.textContent='Control diario, productividad por colaborador y eficiencia de mercancía';
  }

  function handleMainClick(event){
    const btn=event.target.closest?.('[data-main]');
    if(!btn)return;
    const mod=String(btn.dataset.main||'');
    if(!['operativo','analysis','operation'].includes(mod))return;

    /* Las capas antiguas registraron varios onclick sobre los mismos botones.
       V213 se convierte en la única ruta para estos tres módulos. */
    event.preventDefault();
    event.stopImmediatePropagation();

    if(mod==='operativo')openCambios();
    else if(mod==='analysis')openAnalysis();
    else openOperation();
  }

  document.addEventListener('click',handleMainClick,true);

  document.addEventListener('click',e=>{
    const cm=e.target.closest?.('#operativoNav>button');
    if(cm){
      setModule('operativo');
      [20,100,350].forEach(ms=>setTimeout(()=>syncChrome('operativo'),ms));
      return;
    }
    const an=e.target.closest?.('#analysisNav>button');
    if(an){
      setModule('analysis');
      [20,100,350].forEach(ms=>setTimeout(()=>syncChrome('analysis'),ms));
      return;
    }
    const op=e.target.closest?.('#v200OperationTabs>button');
    if(op){
      setModule('operation');
      [20,100,350].forEach(ms=>setTimeout(()=>syncChrome('operation'),ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(e.target?.matches?.('#week,#store,#section,#catalog,#operPeriodMode,#operPeriodSelect,#operStoreSelect,#operAreaSelect,#operActivitySelect')){
      const mod=document.body.dataset.v213Module;
      setTimeout(()=>syncChrome(mod),90);
    }
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>{
    const mod=document.body.dataset.v213Module;
    setTimeout(()=>syncChrome(mod),50);
  });

  function syncFromActive(){
    cleanLegacyVisuals();
    const active=q('.side [data-main].active,#mobileMainNav [data-main].active');
    const mod=String(active?.dataset.main||'');
    if(['operativo','analysis','operation','users','share'].includes(mod))syncChrome(mod);
  }

  function initial(){
    cleanLegacyVisuals();
    syncFromActive();
    const app=q('#appView');
    if(app && !app.classList.contains('hidden')){
      const mod=document.body.dataset.v213Module;
      /* Si una capa previa dejó visible el Centro legacy vacío, rehacer sólo
         la vista actual una vez. */
      if(mod==='operativo' && !q('#operativoCentro')?.classList.contains('hidden')){
        setTimeout(openCambios,120);
      }
    }
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initial,{once:true});
  else initial();

  [180,600,1400].forEach(ms=>setTimeout(syncFromActive,ms));
  window.addEventListener('pageshow',()=>setTimeout(syncFromActive,60),{passive:true});
  window.addEventListener('resize',()=>setTimeout(syncFromActive,90),{passive:true});

  console.info('[V213] reportes estabilizados: navegación única, filtros correctos y módulos aislados.');
})();
</script>"""

    @m.app.middleware("http")
    async def v213_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v213-reports-final-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v213-reports-final-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V213",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V213] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V213_REPORTS_FINAL_STABILIZATION=True
    print("[V213] navegación única + filtros + aislamiento de reportes instalados.",flush=True)
