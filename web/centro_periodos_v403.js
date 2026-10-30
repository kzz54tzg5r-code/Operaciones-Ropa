/* V403: barra día/semana/mes/año, mantiene V266 como fuente de verdad */
(()=>{
'use strict';
if(window.__v403Modes)return;window.__v403Modes=true;
const q=s=>document.querySelector(s);
const entries=[['day','Día'],['week','Semana'],['month','Mensual'],['year','Anual']];
function active(){
 const nav=q('#operativoNav [data-opview="Centro Ejecutivo"]');
 return q('#page-operativo')?.classList.contains('active')&&
        nav?.classList.contains('active')&&
        !document.body.classList.contains('v238-module-operation');
}
function paint(mode){
 q('#v403CenterModes')?.querySelectorAll('button[data-mode]').forEach(b=>{
  const on=b.dataset.mode===(mode||q('#operPeriodMode')?.value||'day');
  b.classList.toggle('active',on);
  b.setAttribute('aria-pressed',String(on));
 });
}
async function choose(mode){
 if(!active())return;
 const original=q('#operativoPeriodBar .v266-period-btn[data-mode="'+mode+'"]');
 if(original){
  // V266 sabe reconstruir los periodos ISO y los filtros del reporte.
  original.click();paint(mode);return;
 }
 const native=q('#operPeriodMode');if(!native)return;
 if(![...native.options].some(o=>o.value===mode))native.add(new Option(entries.find(x=>x[0]===mode)[1],mode));
 native.value=mode;
 native.dispatchEvent(new Event('change',{bubbles:true}));
 if(typeof window.V240_renderCenter==='function'){
  try{await window.V240_renderCenter(mode,false)}catch(e){console.warn('[V403] Vista',e)}
 }else q('#operPeriodSelect')?.dispatchEvent(new Event('change',{bubbles:true}));
 paint(mode);
}
function mount(){
 const on=active(),grid=q('#operativoPeriodBar .or-report-filter-grid');
 document.body.classList.toggle('v403-center-mode',!!on);
 if(!on||!grid)return;
 let host=q('#v403CenterModes');
 if(!host){
  host=document.createElement('div');host.id='v403CenterModes';host.className='v403-center-view';
  const cap=document.createElement('div');cap.className='v403-mode-label';cap.textContent='◉ VISTA';
  const buttons=document.createElement('div');buttons.className='v403-mode-buttons';
  for(const [key,label] of entries){
   const b=document.createElement('button');b.type='button';b.dataset.mode=key;b.textContent=label;
   b.addEventListener('click',()=>choose(key));buttons.append(b);
  }
  host.append(cap,buttons);grid.prepend(host);
 }
 paint();
}
let scheduled=false;
function schedule(){
 if(scheduled)return;scheduled=true;
 requestAnimationFrame(()=>{scheduled=false;mount()});
}
function start(){
 const bar=q('#operativoPeriodBar'),nav=q('#operativoNav');
 if(bar)new MutationObserver(schedule).observe(bar,{childList:true,subtree:true});
 if(nav)new MutationObserver(schedule).observe(nav,{attributes:true,subtree:true,attributeFilter:['class','aria-selected']});
 document.addEventListener('change',e=>{if(['operPeriodMode','operPeriodSelect'].includes(e.target?.id))schedule()},true);
 document.addEventListener('click',e=>{if(e.target.closest?.('[data-opview],[data-main]'))setTimeout(schedule,80)},true);
 schedule();[120,450,1000].forEach(ms=>setTimeout(schedule,ms));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
else start();
})();