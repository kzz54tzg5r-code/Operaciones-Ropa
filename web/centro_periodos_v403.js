/* V429: un solo selector de periodo. V266 es la fuente de verdad.
   V403 ya NO monta una segunda fila, ni escucha clics que re-renderizan. */
(()=>{
 'use strict';
 if(window.__v403Modes)return;window.__v403Modes=true;
 const q=sel=>document.querySelector(sel);
 function synchronize(){
   const nav=q('#operativoNav [data-opview="Centro Ejecutivo"]');
   const on=!!q('#page-operativo.active')&&!!nav?.classList.contains('active')&&
     !document.body.classList.contains('v238-module-operation');
   document.body.classList.toggle('v403-center-mode',on);
   // Retirar también versiones de la barra creadas por scripts almacenados
   // en una sesión anterior.
   document.querySelectorAll('#v403CenterModes,.v403-center-view').forEach(node=>node.remove());
 }
 let scheduled=false;
 function schedule(){
   if(scheduled)return;scheduled=true;
   requestAnimationFrame(()=>{scheduled=false;synchronize()});
 }
 function install(){
   const nav=q('#operativoNav');
   const bar=q('#operativoPeriodBar');
   if(nav)new MutationObserver(schedule).observe(nav,{subtree:true,attributes:true,attributeFilter:['class','aria-selected']});
   if(bar)new MutationObserver(schedule).observe(bar,{childList:true,subtree:true});
   document.addEventListener('click',e=>{
     if(e.target.closest?.('[data-opview],[data-main]'))schedule();
   },true);
   schedule();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
 else install();
})();