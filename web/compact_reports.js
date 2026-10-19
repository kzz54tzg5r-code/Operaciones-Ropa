/* Option 3: progressive disclosure; source data and export tables stay intact. */
(function(){
'use strict';
const KPI='.report-kpis,.kpis,.rr243-kpis,.v331-kpis,.mct-kpi-grid';
const state=new Map();let queued=false,printing=false;
const text=el=>el?el.textContent.trim().replace(/\s+/g,' '):'';
function key(){return [...document.querySelectorAll('#operativoNav .active,#page-operativo [data-opview].active')].map(text).join('|')||'report';}
function disclosure(root,block,title,metric,id){
 const doc=root.ownerDocument,section=doc.createElement('details');section.className='compact-section';section.dataset.section=id;
 const head=doc.createElement('summary'),label=doc.createElement('strong'),value=doc.createElement('span'),action=doc.createElement('span');
 label.textContent=title;value.textContent=metric||'';value.className='compact-section-value';action.className='compact-section-action';action.textContent='Ver detalle';head.append(label,value,action);
 const body=doc.createElement('div');body.className='compact-section-body';
 const back=doc.createElement('button');back.type='button';back.className='compact-section-back';back.textContent='← Regresar al resumen';
 const reportKey=key(),sectionKey=reportKey+'|'+id;
 let y=0;
 back.addEventListener('click',()=>{section.open=false;head.focus({preventScroll:true});window.scrollTo({top:y,behavior:'auto'});});
 section.addEventListener('toggle',()=>{
  if(printing)return;
  state.set(sectionKey,section.open);
  if(section.open){y=window.scrollY;root.querySelectorAll('details.compact-section').forEach(other=>{if(other!==section)other.open=false;});window.dispatchEvent(new Event('resize'));}
  action.textContent=section.open?'Cerrar detalle':'Ver detalle';
 });
 section.append(head,body);body.append(back,block);section.open=!!state.get(sectionKey);return section;
}
function metricGrid(rows,headers){
 const grid=document.createElement('div');grid.className='compact-data-grid';grid.setAttribute('role','table');
 const add=(values,head)=>{const line=document.createElement('div');line.className='compact-data-row';line.setAttribute('role','row');values.forEach(v=>{const c=document.createElement(head?'strong':'span');c.setAttribute('role',head?'columnheader':'cell');c.textContent=v;line.append(c);});grid.append(line);};
 add(headers,true);rows.forEach(r=>add(r,false));return grid;
}
function monthly(root){
 const table=root.querySelector('.monthly-cross-table'),cards=root.querySelector('.mct-kpi-grid');
 if(!table||!cards||root.querySelector('.compact-monthly-sections'))return;
 // Copy text into accessible small grids, not duplicate tables. Original full
 // table remains mounted and export handlers continue to read that same table.
 const rows=[...table.querySelectorAll('tbody tr')].map(tr=>{
  const cells=[...tr.cells].filter(c=>!c.classList.contains('monthly-cat'));
  return cells.map(c=>{const main=c.querySelector('.mct-value-pieces b'),sub=c.querySelector('.mct-value-pieces small');return main?(text(main).includes('%')&&sub?text(main)+' · '+text(sub):text(main)):text(c)});
 });
 const byLabel=label=>rows.find(r=>r[0]&&r[0].includes(label));
 const card=label=>[...cards.children].find(c=>text(c.querySelector('.mct-kpi-label')).includes(label));
 const value=label=>text(card(label)?.querySelector('.mct-kpi-value'));
 const container=document.createElement('div');container.className='compact-monthly-sections';
 const specs=[
  ['collection','Operación (Recolección)',value('TOTAL OPERACIÓN')+' pzas',rows.filter(r=>/^(DEV PZS|MUERTOS|PROBADOR|CAJAS|PENDIENTE ANTERIOR|TOTAL OPERACIÓN)/.test(r[0]||''))],
  ['progress','Acondicionado y ubicado',[value('% ACONDICIONADO'),value('% UBICADO')].filter(Boolean).join(' / '),[byLabel('% ACONDICIONADO'),byLabel('% UBICADO')].filter(Boolean)],
  ['routes','Recorridos',value('RECORRIDOS'),[byLabel('RECORRIDOS')].filter(Boolean)],
  ['pending','Pendientes',value('TOTAL PENDIENTES')+' pzas',rows.filter(r=>/^(PENDIENTE DE|TOTAL PENDIENTES)/.test(r[0]||''))]
 ];
 specs.forEach(([id,title,metric,data])=>{if(data.length)container.append(disclosure(root,metricGrid(data,['Indicador','Valor / Piezas','%','Meta','Total']),title,metric,id));});
 cards.after(container);cards.classList.add('compact-summary-band');
 // Keep all six original KPI cards available in the complete detail as well.
 const original=table.closest('.monthly-cross-desktop')||table.parentElement;
 const sourceHolder=document.createElement('div');original.before(sourceHolder);sourceHolder.append(original);
 const mobile=root.querySelector('.monthly-cross-mobile');if(mobile)sourceHolder.append(mobile);
 container.append(disclosure(root,sourceHolder,'Tabla completa del reporte',value('TOTAL GENERAL')+' pzas','full-table'));
}
function decorate(root){
 if(!root.children.length)return;
 root.classList.add('compact-report');
 root.querySelectorAll('.compact-preview,.compact-detail-bar').forEach(el=>el.remove());
 monthly(root);
 const elements=[...root.querySelectorAll('table,canvas,.plotly-graph-div,.js-plotly-plot,.bars,.v331-rank,.combo-svg,.recovery-svg,.rr243-chart')].filter(el=>!el.closest('.compact-section'));
 const blocks=new Set();
 elements.forEach(el=>{
  let block=el;
  while(block.parentElement&&block.parentElement!==root&&!block.parentElement.matches('.v331-root,.rr243-root')&&!block.parentElement.querySelector(KPI+',input,select,textarea,form,details.compact-section'))block=block.parentElement;
  if(block.querySelector('input,select,textarea,form')||block.closest('.compact-section'))return;
  blocks.add(block);
 });
 [...blocks].filter(b=>![...blocks].some(other=>other!==b&&other.contains(b))).forEach((block,i)=>{
  let heading=block.querySelector('h2,h3,h4,.panel-head,.chart-title,.v331-panelhead,.rr243-chart-head,caption');
  const previous=block.previousElementSibling;
  if(!heading&&previous&&previous.matches('h2,h3,h4,.title,.chart-title'))heading=previous;
  const title=text(heading)||(block.matches('table')||block.querySelector('table')?'Tabla del reporte':'Gráfico del reporte');
  const marker=document.createComment('report-section');block.before(marker);
  if(block.matches('table')){const wrap=document.createElement('div');wrap.className='compact-table-scroll';wrap.append(block);block=wrap;}
  const section=disclosure(root,block,title,'',title+'|'+i);marker.replaceWith(section);
  if(heading&&heading!==block&&!block.contains(heading))heading.hidden=true;
 });
}
function run(){queued=false;document.querySelectorAll('#operativoDynamicContent').forEach(decorate);}
function schedule(){if(!queued){queued=true;requestAnimationFrame(run);}}
function start(){
 const observer=new MutationObserver(records=>{if(records.some(r=>[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&!n.closest?.('.compact-section'))))schedule();});
 document.querySelectorAll('#page-operativo,main.main').forEach(el=>observer.observe(el,{childList:true,subtree:true}));
 let printState=[];
 window.addEventListener('beforeprint',()=>{printing=true;printState=[...document.querySelectorAll('details.compact-section')].map(el=>[el,el.open]);printState.forEach(([el])=>{el.open=true;});});
 window.addEventListener('afterprint',()=>{printState.forEach(([el,open])=>{el.open=open;});printState=[];setTimeout(()=>{printing=false;},0);});
 schedule();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
