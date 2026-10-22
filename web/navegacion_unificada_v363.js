/* V363: Control estable de menú y pestañas; conserva todos los botones originales. */
(() => {
 'use strict';
 if(window.__or363NavigationInstalled)return;
 window.__or363NavigationInstalled=true;
 const doc=document;
 const body=doc.body;
 const q=s=>doc.querySelector(s);
 const navs=['operativoNav','analysisNav','v200OperationTabs'];
 body.classList.add('or363-navigation');
 const removeLegacy=(el,props)=>{
  if(!el)return;
  for(const prop of props){
   if(el.style.getPropertyValue(prop))el.style.removeProperty(prop);
  }
 };
 const navProperties=['height','min-height','max-height','flex','flex-basis',
  'width','min-width','max-width','gap','padding','margin','grid-template-columns',
  'grid-auto-flow','grid-auto-rows','grid-template-rows','overflow','overflow-x',
  'overflow-y','scroll-snap-type','touch-action','position'];
 const tabProperties=['flex','flex-basis','width','min-width','max-width',
  'height','min-height','max-height','padding','margin','font-size','display',
  'grid-row','grid-column','order','overflow','white-space','transform'];
 const isVisible=btn=>{
  if(btn.hidden||btn.classList.contains('hidden')||btn.getAttribute('aria-hidden')==='true')return false;
  const cs=getComputedStyle(btn);
  return cs.display!=='none'&&cs.visibility!=='hidden';
 };
 function ownNav(id){
  const active=String(body.dataset.v163Module||body.dataset.main||'');
  if(id==='operativoNav')return active==='operativo'||!!q('#operativoNav .active')&&!active;
  if(id==='analysisNav')return active==='analysis';
  return active==='operation'||!!q('#v200OperationTabs [data-v200-op].active')&&active==='operativo';
 }
 function normalize(nav){
  const belongs=ownNav(nav.id);
  // Las pestañas se ocultan por rol/modulo, nunca se vuelven a mostrar a la fuerza.
  if(belongs){
   removeLegacy(nav,navProperties);
  }else{
   removeLegacy(nav,navProperties.filter(p=>p!=='display'));
  }
  if(nav.dataset.v221Scroll==='0')nav.dataset.v221Scroll='1';
  for(const btn of [...nav.children].filter(el=>el.tagName==='BUTTON')){
   removeLegacy(btn,tabProperties);
   // Los demás motores ya insertaron iconos. Solo se deja visible el primero.
   const icons=btn.querySelectorAll(':scope > .rt-tab-icon,:scope > .or-tab-icon,:scope > .v203-tab-icon,:scope > .v164-tab-icon');
   icons.forEach((icon,i)=>{
    if(i===0)icon.removeAttribute('aria-hidden');
    else icon.setAttribute('aria-hidden','true');
   });
   if(!btn.title){
    btn.title=btn.dataset.rtLabel||btn.textContent.trim();
   }
   if(btn.classList.contains('active')){
    btn.setAttribute('aria-selected','true');
   }else if(btn.getAttribute('aria-selected')==='true'){
    btn.setAttribute('aria-selected','false');
   }
  }
 }
 function revealActive(nav){
  if(!ownNav(nav.id)||nav.closest('.hidden'))return;
  const active=nav.querySelector(':scope > button.active');
  if(!active||!isVisible(active))return;
  const cr=nav.getBoundingClientRect(),br=active.getBoundingClientRect();
  if(br.left<cr.left+3)nav.scrollLeft-=Math.ceil(cr.left+3-br.left);
  else if(br.right>cr.right-3)nav.scrollLeft+=Math.ceil(br.right-cr.right+3);
 }
 let scheduled=false;
 function refresh(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(()=>{
   scheduled=false;
   if(!q('#appView')||q('#appView').classList.contains('hidden'))return;
   body.classList.add('or363-navigation');
   navs.forEach(id=>{const nav=doc.getElementById(id);if(nav)normalize(nav)});
  });
 }
 function wire(nav){
  if(!nav||nav.dataset.or363Wired)return;
  nav.dataset.or363Wired='1';
  nav.addEventListener('click',e=>{
   const b=e.target.closest('button');
   if(!b||b.parentElement!==nav)return;
   requestAnimationFrame(()=>revealActive(nav));
  },false);
  nav.addEventListener('keydown',e=>{
   if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
   const buttons=[...nav.children].filter(btn=>btn.tagName==='BUTTON'&&isVisible(btn));
   if(!buttons.length)return;
   const current=buttons.indexOf(doc.activeElement);
   const ix=e.key==='Home'?0:e.key==='End'?buttons.length-1:
    Math.max(0,Math.min(buttons.length-1,(current<0?0:current)+(e.key==='ArrowRight'?1:-1)));
   e.preventDefault();
   buttons[ix].focus({preventScroll:true});
   buttons[ix].click();
   revealActive(nav);
  });
  nav.addEventListener('wheel',e=>{
   if(Math.abs(e.deltaY)<=Math.abs(e.deltaX) || nav.scrollWidth<=nav.clientWidth+2)return;
   if(!e.shiftKey && Math.abs(e.deltaY)<3)return;
   e.preventDefault();
   nav.scrollLeft+=e.deltaY;
  },{passive:false});
  const observer=new MutationObserver(mutations=>{
   if(mutations.some(m=>m.type==='childList'||(m.type==='attributes'&&m.attributeName==='style')))refresh();
  });
  observer.observe(nav,{childList:true,subtree:false,attributes:true,attributeFilter:['style']});
 }
 function init(){
  body.classList.add('or363-navigation');
  navs.forEach(id=>wire(doc.getElementById(id)));
  refresh();
  const observer=new MutationObserver(mutations=>{
   if(mutations.some(m=>m.type==='childList')){
    navs.forEach(id=>wire(doc.getElementById(id)));
    refresh();
   }
  });
  const app=q('#appView');if(app)observer.observe(app,{childList:true,subtree:false});
  window.addEventListener('resize',refresh,{passive:true});
  doc.addEventListener('report-tabs-visibility-changed',refresh);
  doc.addEventListener('click',e=>{
   if(e.target.closest('#sidebar [data-main],#operativoNav [data-opview],#analysisNav [data-sub],#v200OperationTabs [data-v200-op]')){
    requestAnimationFrame(()=>{refresh();navs.forEach(id=>{const nav=doc.getElementById(id);if(nav)revealActive(nav)})});
   }
  });
 }
 if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();
