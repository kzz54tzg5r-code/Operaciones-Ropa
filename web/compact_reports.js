/* Compact report presentation. Never changes data, filters or export sources. */
(function(){
'use strict';
const roots='#operativoDynamicContent';
const states=new Map();
let queued=false;
function key(root){
 const scope=root.id==='v313Host'?'#page-bonuses':'#page-operativo';
 const active=[...document.querySelectorAll(scope+' button.active')].map(x=>x.textContent.trim()).join('|');
 return root.id+'|'+active;
}
function decorate(root){
 if(!root.children.length)return;
 root.classList.add('compact-report');
 const k=key(root),state=states.get(k)||{open:false,y:0};
 states.set(k,state);
 // Keep cards, warnings, filters and editing forms visible. Collapse only full
 // analytical blocks; nodes stay mounted so exports and bound handlers survive.
 const candidates=[...root.querySelectorAll('table, canvas, .plotly-graph-div, .js-plotly-plot, .bars, .v331-rank, .v313-components, .v313-matrix, .combo-svg, .recovery-svg, .rr243-chart')];
 const blocks=new Set();
 candidates.forEach(el=>{
   let block=el;
   while(block.parentElement && block.parentElement!==root &&
     !block.parentElement.querySelector('.report-kpis,.kpis,.v313-kpis,.rr243-kpis,.v331-kpis,input,select,textarea,form') &&
     !block.parentElement.matches('.v313,.v331-root'))block=block.parentElement;
   if(block.matches('table')){
     const wrap=document.createElement('div');wrap.className='compact-table-scroll';
     block.before(wrap);wrap.append(block);block=wrap;
   }
   if(!block.querySelector('input,select,textarea,form'))blocks.add(block);
 });
 const selected=[...blocks].filter(b=>![...blocks].some(other=>other!==b&&other.contains(b)));
 let bar=root.querySelector(':scope > .compact-detail-bar');
 if(!selected.length){if(bar)bar.remove();return;}
 selected.forEach(b=>{b.classList.add('compact-detail-block');b.classList.toggle('compact-detail-closed',!state.open);});
 if(!bar){
   bar=document.createElement('div');bar.className='compact-detail-bar';
   const label=document.createElement('span');label.textContent='Tablas y gráficos del reporte';
   const button=document.createElement('button');button.type='button';
   button.addEventListener('click',()=>{
     const s=states.get(key(root));if(!s)return;
     if(!s.open)s.y=window.scrollY;
     s.open=!s.open;decorate(root);
     if(!s.open){window.scrollTo({top:s.y,behavior:'auto'});button.focus({preventScroll:true});}
     else window.dispatchEvent(new Event('resize'));
   });
   bar.append(label,button);
   let anchor=[...root.children].find(c=>selected.some(b=>c===b||c.contains(b)));
   root.insertBefore(bar,anchor||null);
 }
 const button=bar.querySelector('button');
 const text=state.open?'← Regresar al resumen':'Ver detalle';
 if(button.textContent!==text)button.textContent=text;
 button.setAttribute('aria-expanded',String(state.open));
}
function run(){queued=false;document.querySelectorAll(roots).forEach(decorate);}
function schedule(){if(!queued){queued=true;requestAnimationFrame(run);}}
function start(){
 // Only content replacements trigger work; presentation attributes are ignored.
 const observer=new MutationObserver(records=>{
   if(records.some(r=>[...r.addedNodes,...r.removedNodes].some(n=>
      n.nodeType===1&&!n.matches('.compact-detail-bar')&&!n.closest?.('.compact-detail-bar'))))schedule();
 });
 document.querySelectorAll('#page-operativo,#page-bonuses,main.main').forEach(r=>observer.observe(r,{childList:true,subtree:true}));
 document.addEventListener('click',e=>{if(e.target.closest('[data-opview],[data-v313-section],[data-v313-bonus]'))schedule();});
 schedule();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
