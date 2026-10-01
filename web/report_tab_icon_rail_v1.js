/*
 * Compatibilidad V213.
 *
 * El carrusel circular anterior reordenaba físicamente los botones de
 * #operativoNav/#analysisNav y añadía una segunda capa visual. Eso terminó
 * mezclando pestañas entre módulos. Desde V213 las pestañas conservan su DOM,
 * listeners y permisos originales; sólo se limpia cualquier residuo visual.
 */
(()=>{
  'use strict';

  function clean(){
    ['operativoNav','analysisNav'].forEach(id=>{
      const host=document.getElementById(id);
      if(!host)return;
      host.classList.remove('rt-icon-rail-v1','rt-icon-has-user-selection');
      host.querySelectorAll(':scope > button').forEach(btn=>{
        btn.classList.remove('rt-icon-user-active');
        btn.style.removeProperty('--rt-ring-order');
      });
    });
    document.querySelectorAll('.rt-icon-rail-v1-current,.rt-icon-rail-v1-indicator').forEach(x=>x.remove());
  }

  const api={refresh:clean,select:()=>{}};
  window.ReportTabIconRailV1=api;
  window.ReportTabIconRailV3=api;
  window.ReportTabIconRailV5=api;
  window.ReportTabIconRailV6=api;
  window.ReportTabIconRailV7=api;
  window.ReportTabIconRailV8=api;
  window.ReportTabIconRailV10=api;

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',clean,{once:true});
  else clean();
  window.addEventListener('pageshow',clean,{passive:true});
})();
