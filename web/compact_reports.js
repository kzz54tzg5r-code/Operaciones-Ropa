/* Option 3: progressive disclosure; source data and export tables stay intact. */
(function(){
'use strict';
const KPI='.report-kpis,.kpis,.rr243-kpis,.v331-kpis,.mct-kpi-grid';
const state=new Map();let queued=false,printing=false;
const text=el=>el?el.textContent.trim().replace(/\s+/g,' '):'';
function key(){return [...document.querySelectorAll('#operativoNav .active,#page-operativo [data-opview].active')].map(text).join('|')||'report';}
const ICONS={
 box:'M12 3 3 8v9l9 5 9-5V8l-9-5ZM3 8l9 5 9-5M12 13v9M7 5.8l9 5',
 chart:'M4 20V10m8 10V4m8 16v-7M2 21h20',
 target:'M21 12a9 9 0 1 1-9-9 9 9 0 0 1 9 9Zm-5 0a4 4 0 1 1-4-4 4 4 0 0 1 4 4Z',
 people:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm5 8a4 4 0 0 1 4 4v2M17 3a4 4 0 0 1 0 8',
 clock:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v5l3 2',
 upload:'M12 16V3m-5 5 5-5 5 5M3 15v5h18v-5',
 store:'M3 10h18l-2-6H5l-2 6ZM5 10v11h14V10M9 21v-7h6v7',
 alert:'m12 3 10 18H2L12 3ZM12 9v5m0 3v.1',
 table:'M3 4h18v17H3V4ZM3 10h18M9 10v11M3 15h18',
 money:'M12 2v20m5-16H9a4 4 0 0 0 0 8h6a4 4 0 0 1 0 8H6',
 trophy:'M8 3h8v8a4 4 0 0 1-8 0V3ZM8 5H3v3a4 4 0 0 0 5 4m8-7h5v3a4 4 0 0 1-5 4M12 15v6m-4 0h8'
};
function theme(title){
 const t=title.toLowerCase();
 if(/pendiente|inversi|devoluci/.test(t))return ['clock','orange','Detalle del periodo consultado'];
 if(/acondicion|ubicad|criterio|evaluaci|score|estándar/.test(t))return ['target','purple','Avance y criterios del periodo'];
 if(/ranking|comparativo|top/.test(t))return ['trophy','blue','Comparativo con los datos del reporte'];
 if(/colaborador|captura|productividad/.test(t))return ['people','purple','Detalle por actividad y colaborador'];
 if(/cargar|carga|archivo|validaci/.test(t))return ['upload','blue','Archivo, validación y resultado'];
 if(/historial|seguimiento/.test(t))return ['clock','purple','Registros y cambios disponibles'];
 if(/alerta|advertencia|calidad/.test(t))return ['alert','orange','Información que requiere revisión'];
 if(/tienda|meta/.test(t))return ['store','blue','Configuración y detalle por tienda'];
 if(/recorrido|evoluci|gráfico/.test(t))return ['chart','blue','Avance del periodo consultado'];
 if(/recuperaci|venta|conversi/.test(t))return ['money','blue','Resultado y desglose del periodo'];
 return ['box','green','Detalle de la información seleccionada'];
}
function icon(name,tone){return '<span class="compact-icon compact-tone-'+tone+'" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="'+(ICONS[name]||ICONS.box)+'"/></svg></span>';}
window.RopaCompact={icon,theme};
function brandCards(root){
 root.querySelectorAll('.compact-summary-band').forEach(band=>{
  [...band.children].forEach((card,i)=>{
   card.classList.add('compact-kpi');
   if(card.querySelector(':scope>.compact-icon'))return;
   const label=card.querySelector('.mct-kpi-label,.rk-label,.lab,.label,span');
   const spec=theme(text(label));
   card.insertAdjacentHTML('afterbegin',icon(spec[0],i===0?'green':'orange'));
  });
 });
 root.querySelectorAll('.compact-section').forEach(section=>{
  const head=section.querySelector(':scope>summary,:scope>.compact-bonus-summary');if(!head)return;
  if(!head.querySelector(':scope>.compact-icon')){
   const label=head.querySelector('strong'),spec=theme(text(label));head.insertAdjacentHTML('afterbegin',icon(spec[0],spec[1]));
  }
 });
}
function disclosure(root,block,title,metric,id){
 const doc=root.ownerDocument,section=doc.createElement('details');section.className='compact-section';section.dataset.section=id;
 const head=doc.createElement('summary'),label=doc.createElement('strong'),value=doc.createElement('span'),action=doc.createElement('span');
 const spec=theme(title),titleWrap=doc.createElement('span'),caption=doc.createElement('small');titleWrap.className='compact-section-title';caption.textContent=spec[2];label.textContent=title;titleWrap.append(label,caption);value.textContent=metric||'';value.className='compact-section-value';action.className='compact-section-action';action.textContent='Ver detalle';head.insertAdjacentHTML('afterbegin',icon(spec[0],spec[1]));head.append(titleWrap,value,action);
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
 specs.forEach(([id,title,metric,data])=>{
  if(!data.length)return;
  const detail=document.createElement('div');
  if(id==='progress'){
   const meters=document.createElement('div');meters.className='compact-progress-pair';
   ['% ACONDICIONADO','% UBICADO'].forEach(label=>{
    const c=card(label),raw=value(label),num=Number(raw.replace('%','').replace(',','.'));
    const meter=document.createElement('div');meter.className='compact-progress-tile';
    const titleEl=document.createElement('strong'),amount=document.createElement('b'),note=document.createElement('small'),track=document.createElement('div'),fill=document.createElement('i');
    titleEl.textContent=label.replace('% ','');amount.textContent=raw||'Sin dato';note.textContent=text(c?.querySelector('.mct-kpi-sub'));track.className='compact-progress-track';fill.style.width=(Number.isFinite(num)?Math.max(0,Math.min(100,num)):0)+'%';track.append(fill);meter.append(titleEl,amount,note,track);meters.append(meter);
   });detail.append(meters);
  }
  detail.append(metricGrid(data,['Indicador','Valor / Piezas','%','Meta','Total']));
  container.append(disclosure(root,detail,title,metric,id));
 });
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
 const band=root.querySelector('.report-kpis,.kpis,.rr243-kpis,.v331-kpis');
 if(band&&!band.classList.contains('compact-summary-band')&&!band.closest('.compact-section')){
  band.classList.add('compact-summary-band');
  if(band.children.length>2){
   const more=document.createElement('div');more.className=band.className.replace('compact-summary-band','');
   [...band.children].slice(2).forEach(card=>more.append(card));
   band.after(disclosure(root,more,'Resultado del periodo','','period-result'));
  }
 }
 const elements=[...root.querySelectorAll(':scope>.panel, :scope>.cards, table,canvas,.plotly-graph-div,.js-plotly-plot,.bars,.v331-rank,.combo-svg,.recovery-svg,.rr243-chart')].filter(el=>!el.closest('.compact-section')&&!el.querySelector(KPI+',.compact-section'));
 const blocks=new Set();
 elements.forEach(el=>{
  let block=el;
  while(block.parentElement&&block.parentElement!==root&&!block.parentElement.matches('.v331-root,.rr243-root')&&!block.parentElement.querySelector(KPI+',input,select,textarea,form,details.compact-section'))block=block.parentElement;
  if(block.closest('.compact-section'))return;
  if(block.querySelector('input,select,textarea,form')&&!block.matches('.panel'))return;
  blocks.add(block);
 });
 [...blocks].filter(b=>![...blocks].some(other=>other!==b&&other.contains(b))).forEach((block,i)=>{
  let heading=block.querySelector('h2,h3,h4,.title,.panel-head,.chart-title,.v331-panelhead,.rr243-chart-head,caption');
  const previous=block.previousElementSibling;
  if(!heading&&previous&&previous.matches('h2,h3,h4,.title,.chart-title'))heading=previous;
  const view=text(document.querySelector('#operativoDynamicTitle'));
  const fallback=/Conversión/i.test(view)?'Comparativo por tienda':/Recuperación Económica|Recuperación \$/i.test(view)?'Ranking de tiendas':/Productividad/i.test(view)?'Detalle por colaborador':/Recorridos/i.test(view)?'Detalle por día':'';
  const title=text(heading?.querySelector('b,strong')||heading)||fallback||(block.classList.contains('cards')?'Alertas del periodo':null)||(block.matches('table')||block.querySelector('table')?'Tabla del reporte':'Gráfico del reporte');
  const marker=document.createComment('report-section');block.before(marker);
  if(block.matches('table')){const wrap=document.createElement('div');wrap.className='compact-table-scroll';wrap.append(block);block=wrap;}
  const section=disclosure(root,block,title,'',title+'|'+i);marker.replaceWith(section);
  if(block.querySelector('input:not([type=hidden]),select,textarea')&&!state.has(key()+'|'+title+'|'+i))section.open=true;
  if(heading&&heading!==block&&!block.contains(heading))heading.hidden=true;
 });
}
function setStyle(el,prop,value){if(el&&(el.style.getPropertyValue(prop)!==value||el.style.getPropertyPriority(prop)!=='important'))el.style.setProperty(prop,value,'important');}
function compactControls(){
 const nav=document.getElementById('operativoNav'),small=window.innerWidth<=700;
 if(nav){
  const active=nav.querySelector('[data-opview].active');
  if(!nav.dataset.compactOwned){
   nav.dataset.compactOwned='1';
   nav.querySelectorAll('[data-opview]').forEach(btn=>{
    const label=btn.querySelector('.rt-tab-label,.v232-tab-label');
    const short={'Centro Ejecutivo':'Centro','Recuperación por Tienda':'Tasa recup.','Tasa de recuperación · Revisión':'Tasa revisión','Carga de productividad':'Cargar prod.'};
    if(label&&btn.dataset.rtLabel)label.textContent=short[btn.dataset.opview]||btn.dataset.rtLabel;
   });
  }
  const isOperations=document.body.dataset.v163Module==='operativo'||document.body.classList.contains('v238-module-operativo');setStyle(nav,'display',isOperations?'flex':'none');
  ['grid-template-columns','grid-template-rows','grid-auto-flow','grid-auto-rows'].forEach(p=>{if(nav.style.getPropertyValue(p))nav.style.removeProperty(p);});
  setStyle(nav,'overflow-x','auto');setStyle(nav,'overflow-y','hidden');setStyle(nav,'height','58px');setStyle(nav,'min-height','58px');setStyle(nav,'max-height','58px');setStyle(nav,'gap','4px');setStyle(nav,'touch-action','pan-x pan-y');setStyle(nav,'position','relative');
  nav.querySelectorAll('[data-opview]').forEach(btn=>{
   setStyle(btn,'flex','1 0 88px');setStyle(btn,'width','auto');setStyle(btn,'min-width','88px');setStyle(btn,'max-width','none');setStyle(btn,'height','48px');setStyle(btn,'min-height','48px');setStyle(btn,'max-height','48px');setStyle(btn,'padding','5px 6px');setStyle(btn,'margin','0px');
  });
  if(active&&(active.offsetLeft<nav.scrollLeft||active.offsetLeft+active.offsetWidth>nav.scrollLeft+nav.clientWidth))nav.scrollLeft=active.offsetLeft;
 }
 const grid=document.querySelector('#operativoPeriodBar>.or-report-filter-grid');
 if(grid){
  grid.dataset.compactOwned='1';setStyle(grid,'display','grid');setStyle(grid,'grid-template-columns',small?'repeat(2,minmax(0,1fr))':'repeat(3,minmax(0,1fr))');setStyle(grid,'grid-auto-flow','row');setStyle(grid,'gap','8px');setStyle(grid,'overflow','visible');setStyle(grid,'height','auto');
  grid.querySelectorAll('.or-fcontrol').forEach(el=>{setStyle(el,'width','100%');setStyle(el,'min-width','0px');setStyle(el,'max-width','100%');setStyle(el,'flex','initial');setStyle(el,'grid-row','auto');setStyle(el,'grid-column','auto');setStyle(el,'order','0');});
  const mode=document.getElementById('operPeriodMode'),wrap=document.getElementById('operPeriodModeWrap');
  if(mode&&wrap){const on=mode.options.length>1;wrap.dataset.compactMode=on?'1':'0';if(on){setStyle(wrap,'display','flex');setStyle(wrap,'order','-3');}}
  const period=document.getElementById('operPeriodSelectWrap'),store=document.getElementById('operStoreWrap');
  setStyle(period,'order','-2');setStyle(store,'order','-1');if(small)setStyle(store,'grid-column','1 / -1');
 }
 document.querySelectorAll('#page-operativo .compact-summary-band,#page-bonuses .compact-summary-band').forEach(band=>{setStyle(band,'display','grid');setStyle(band,'grid-template-columns','repeat(2,minmax(0,1fr))');setStyle(band,'width','100%');});
}

function run(){queued=false;compactControls();document.querySelectorAll('#operativoDynamicContent').forEach(root=>{decorate(root);brandCards(root);});document.querySelectorAll('#v313Host').forEach(brandCards);}
function schedule(){if(!queued){queued=true;requestAnimationFrame(run);}}
function start(){
 window.addEventListener('resize',schedule);
 const observer=new MutationObserver(records=>{if(records.some(r=>[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&!n.closest?.('.compact-section'))))schedule();});
 document.querySelectorAll('#page-operativo,#page-bonuses,main.main').forEach(el=>observer.observe(el,{childList:true,subtree:true}));
 let printState=[];
 window.addEventListener('beforeprint',()=>{printing=true;printState=[...document.querySelectorAll('details.compact-section')].map(el=>[el,el.open]);printState.forEach(([el])=>{el.open=true;});});
 window.addEventListener('afterprint',()=>{printState.forEach(([el,open])=>{el.open=open;});printState=[];setTimeout(()=>{printing=false;},0);});
 schedule();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
