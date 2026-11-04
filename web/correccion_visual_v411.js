/* V411 · reparar únicamente estructura visual; no modificar acciones de negocio. */
(()=>{
'use strict';
if(window.__or411VisualFix)return;window.__or411VisualFix=true;
const doc=document;
const q=s=>doc.querySelector(s);
const getNode=nav=>nav?.closest('.v226-tab-shell,.v222-tab-stage,.rt-carousel-shell')||nav;
let scheduled=false,running=false;
function normalizeTabs(nav){
 if(!nav)return;
 // No crear pestañas nuevas ni cambiar el destino o el listener de ninguna.
 const seen=new Map();
 [...nav.querySelectorAll(':scope > button')].forEach(b=>{
   if(b.dataset.or411Deduplicated==='1')b.classList.remove('or411-duplicate');
   const key=b.dataset.tabKey||b.dataset.sub||b.dataset.opview||b.dataset.v125Tab||'';
   if(!key)return;
   const signature=key+'|'+(b.textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
   const previous=seen.get(signature);
   if(previous){
     // Sólo se oculta un duplicado cuando su acción es idéntica.
     // La pestaña activa siempre tiene preferencia.
     if(b.classList.contains('active')&&!previous.classList.contains('active')){
       previous.classList.add('or411-duplicate');
       seen.set(signature,b);
     }else b.classList.add('or411-duplicate');
     b.dataset.or411Deduplicated='1';
   }else{
     b.classList.remove('or411-duplicate');
     seen.set(signature,b);
   }
 });
}
function alignActive(nav){
 if(!nav)return;
 const active=nav.querySelector(':scope > button.active:not(.or411-duplicate):not([hidden])');
 if(!active)return;
 const key=active.id||active.dataset.tabKey||active.dataset.opview||active.dataset.sub||active.textContent.trim();
 if(nav.dataset.or411Active===key)return;
 nav.dataset.or411Active=key;
 // Alinea la pestaña seleccionada; evita que a la izquierda aparezca media palabra.
 if(nav.scrollWidth<=nav.clientWidth+2)return;
 const r=active.getBoundingClientRect(),c=nav.getBoundingClientRect();
 const left=Math.max(0,nav.scrollLeft+(r.left-c.left)-5);
 if(Number.isFinite(left)&&Math.abs(nav.scrollLeft-left)>4)nav.scrollLeft=left;
}
function reconcile(){
 if(running)return;
 running=true;
 try{
  doc.body?.classList.add('or411-fix');
  const main=q('#appView main.main')||q('#appView .main');
  const hero=main?.querySelector(':scope > .hero');
  const op=q('#operativoNav'),analysis=q('#analysisNav'),filters=q('#globalFilters');
  if(hero&&op&&analysis&&filters){
   const opNode=getNode(op),analysisNode=getNode(analysis);
   // Se mueven los contenedores completos: preservar controles, flechas y eventos.
   if(opNode!==analysisNode&&
      !opNode.contains(analysisNode)&&!analysisNode.contains(opNode)){
     if(hero.nextElementSibling!==opNode)hero.after(opNode);
     if(opNode.nextElementSibling!==analysisNode)opNode.after(analysisNode);
     if(analysisNode.nextElementSibling!==filters)analysisNode.after(filters);
   }
  }
  normalizeTabs(op);normalizeTabs(analysis);
  alignActive(op);alignActive(analysis);
 }finally{running=false}
}
function schedule(){
 if(scheduled)return;scheduled=true;
 requestAnimationFrame(()=>{scheduled=false;reconcile()});
}
function init(){
 reconcile();
 doc.addEventListener('click',e=>{
  if(e.target.closest?.('[data-main],#analysisNav,#operativoNav,#v200OperationTabs'))schedule();
 },true);
 doc.addEventListener('report-tabs-visibility-changed',schedule);
 window.addEventListener('resize',schedule,{passive:true});
 window.addEventListener('pageshow',schedule,{passive:true});
 const main=q('#appView main.main')||q('#appView .main');
 if(main)new MutationObserver(mutations=>{
  if(mutations.some(m=>m.type==='childList'))schedule();
 }).observe(main,{childList:true});
 // Al montar una navegación asíncrona, ejecutar una sola vez tras la pintura.
 requestAnimationFrame(schedule);
}
if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',init,{once:true});
else init();
})();
