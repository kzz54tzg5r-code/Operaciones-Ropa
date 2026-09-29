(() => {
  'use strict';
  // Compatibility shim V8.
  // The pedestal/"Mundial" renderer is intentionally disabled.
  // Report navigation is now owned by report_tab_carousel.js +
  // report_tab_icon_rail_v1.js for both Cambios y Muertos and Análisis Comercial.
  function cleanup(){
    document.querySelectorAll('.rt-carousel-shell').forEach(shell=>{
      shell.classList.remove('rt-mundial-v4','rt-mundial-v5','rt-mundial-v6','rt-mundial-v7');
      shell.querySelectorAll(
        ':scope > .rt-worldcup-pedestal,'+
        ':scope > .rt-worldcup-current,'+
        ':scope > .rt-mundial-current,'+
        ':scope > .rt-m7-current'
      ).forEach(x=>x.remove());
    });
    document.querySelectorAll('#operativoNav,#analysisNav,.v125-tabs').forEach(viewport=>{
      viewport.querySelectorAll('.rt-m7-base,.rt-m7-face,.rt-mundial-base,.rt-mundial-face').forEach(x=>x.remove());
    });
  }
  window.ReportTabMundialV7={refresh:cleanup,disabled:true};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',cleanup,{once:true});
  else cleanup();
})();
