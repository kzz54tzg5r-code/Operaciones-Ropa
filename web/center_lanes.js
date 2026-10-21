/* Centro Operativo: approved three-lane overview; original reports remain mounted. */
(function(){
'use strict';
let panel='',originY=0;
const plain=node=>(node?.textContent||'').replace(/\s+/g,' ').trim();
const norm=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/\s+/g,' ').trim();
const el=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;};
function isActive(){
 const active=document.querySelector('#operativoNav [data-opview].active');
 return active?/^(CENTRO EJECUTIVO|CENTRO OPERATIVO)$/.test(norm(active.dataset.opview)):/^CENTRO OPERATIVO\b/.test(norm(plain(document.querySelector('#operativoDynamicTitle'))));
}
function sourceRows(table){return [...table.querySelectorAll('tbody tr')].map(tr=>[...tr.cells].filter(c=>!c.classList.contains('monthly-cat'))).filter(cells=>cells.length>1).map(cells=>({label:plain(cells[0]),cells:cells.slice(1).map(c=>{const pair=c.querySelector('.mct-value-pieces');return pair?[plain(pair.querySelector('b')),plain(pair.querySelector('small'))].filter(Boolean).join(' · '):plain(c)}),amount:plain(cells[1].querySelector('.mct-value-pieces small'))||(/%/.test(plain(cells[1].querySelector('b')))?'':plain(cells[1].querySelector('b'))||plain(cells[1]))}));}
function value(row){return row?.cells[0]||'N/D';}
function amount(row){return row?.amount?.replace(/\s*(pzs|pzas|piezas)\.?$/i,'')||'N/D';}
function numeric(value){const n=Number(String(value).replace(/,/g,'').replace(/[^\d.\-]/g,''));return /\d/.test(String(value))&&Number.isFinite(n)?n:null;}
function meter(percent){const track=el('div','ocl-track'),fill=el('i');const n=numeric(percent);fill.style.width=(n==null?0:Math.max(0,Math.min(100,n)))+'%';track.append(fill);track.setAttribute('aria-hidden','true');return track;}
function stamp(){const option=document.querySelector('#operPeriodSelect')?.selectedOptions[0];return [option?.dataset.centerFullLabel||option?.textContent,document.querySelector('#operStoreSelect')?.value].filter(Boolean).join(' · ');}
function icon(name){const span=el('span','ocl-icon');span.innerHTML=window.RopaCompact?.icon(name,'blue')||'';return span;}
function mount(root){
 if(!isActive())return false;
 const existing=root.querySelector(':scope>.ocl-shell');
 if(existing){const original=existing.querySelector('.ocl-original');[...root.children].filter(n=>n!==existing).forEach(n=>original.append(n));return true;}
 const table=root.querySelector('.monthly-cross-table');
 if(!table)return true; // Keep original loading, no-data and error messages visible.
 const rows=sourceRows(table),get=label=>rows.find(r=>norm(r.label).startsWith(norm(label)));
 const ac=get('% ACONDICIONADO'),ub=get('% UBICADO'),routes=get('RECORRIDOS REALIZADOS');
 const received=get('TOTAL GENERAL'),pendingAc=get('PENDIENTE DE ACONDICIONAR'),pendingUb=get('PENDIENTE DE UBICAR');
 const shell=el('div','ocl-shell'),lanes=el('div','ocl-lanes'),drawer=el('section','ocl-drawer'),original=el('div','ocl-original');
 shell.dataset.design='three-lanes';drawer.hidden=true;drawer.id='centerLaneDetail';drawer.setAttribute('aria-label','Detalle del indicador');
 const buttons={};
 function close(){panel='';drawer.hidden=true;drawer.replaceChildren();Object.values(buttons).forEach(b=>b.setAttribute('aria-expanded','false'));window.scrollTo({top:originY,behavior:'auto'});}
 function open(id,focus=false){
  if(!panel)originY=window.scrollY;panel=id;drawer.hidden=false;drawer.replaceChildren();
  const titles={received:'Ingresos · Recibido',conditioned:'Acondicionado · En proceso',located:'Ubicado · En piso',routes:'Recorridos'};
  const heading=el('div','ocl-drawer-head'),title=el('h3',null,titles[id]),context=el('p','ocl-context',stamp()),back=el('button','ocl-back','← Regresar al resumen');back.type='button';
  back.addEventListener('click',()=>{close();buttons[id]?.focus({preventScroll:true});});heading.append(title,back);drawer.append(heading,context);
  const wanted={received:r=>/^(DEV PZS|MUERTOS|PROBADOR|CAJAS|PENDIENTE ANTERIOR|TOTAL OPERACION|TOTAL GENERAL)/.test(norm(r.label)),conditioned:r=>/ACONDICIONADO|PENDIENTE DE ACONDICIONAR|TOTAL GENERAL/.test(norm(r.label)),located:r=>/UBICADO|PENDIENTE DE UBICAR|TOTAL GENERAL/.test(norm(r.label)),routes:r=>norm(r.label).startsWith('RECORRIDOS')};
  const wrap=el('div','ocl-detail-scroll'),detail=el('table','ocl-detail-table'),thead=el('thead'),tr=el('tr');
  ['Indicador','Valor / Piezas','%','Meta','Total'].forEach(x=>tr.append(el('th',null,x)));thead.append(tr);detail.append(thead);const tbody=el('tbody');
  rows.filter(wanted[id]).forEach(r=>{const line=el('tr');line.append(el('th',null,r.label));r.cells.forEach(x=>line.append(el('td',null,x)));tbody.append(line);});detail.append(tbody);wrap.append(detail);drawer.append(wrap);
  const full=el('button','ocl-full-link','Ver reporte completo por tienda');full.type='button';full.addEventListener('click',()=>{complete.open=true;complete.scrollIntoView({block:'start',behavior:'smooth'});});drawer.append(full);
  Object.entries(buttons).forEach(([key,b])=>b.setAttribute('aria-expanded',String(key===id)));
  if(focus){title.tabIndex=-1;title.focus({preventScroll:true});drawer.scrollIntoView({block:'nearest',behavior:'smooth'});}
  window.dispatchEvent(new Event('resize'));
 }
 function detailButton(id){const b=el('button','ocl-detail-button','Ver detalle');b.type='button';b.setAttribute('aria-expanded','false');b.setAttribute('aria-controls',drawer.id);b.setAttribute('aria-label','Ver detalle de '+({received:'ingresos',conditioned:'acondicionado',located:'ubicado',routes:'recorridos'})[id]);b.addEventListener('click',()=>open(id,true));buttons[id]=b;return b;}
 const specs=[
  {id:'received',title:'Recibido',caption:'Mercancía ingresada en el periodo',label:'Ingresos',value:amount(received),icon:'box'},
  {id:'conditioned',title:'En proceso',caption:'Acondicionamiento de mercancía',label:'Acondicionado',value:amount(ac),pct:ac?.cells[1]||value(ac),pending:amount(pendingAc),pendingLabel:'por acondicionar',icon:'target'},
  {id:'located',title:'En piso',caption:'Mercancía ubicada en tienda',label:'Ubicado',value:amount(ub),pct:ub?.cells[1]||value(ub),pending:amount(pendingUb),pendingLabel:'por ubicar',icon:'store'}
 ];
 specs.forEach(s=>{
  const card=el('section','ocl-lane ocl-'+s.id),head=el('header','ocl-lane-head'),heading=el('div');heading.append(el('h3',null,s.title),el('p','ocl-caption',s.caption));head.append(icon(s.icon),heading);card.append(head);
  const body=el('div','ocl-lane-metric'),quantity=el('div','ocl-quantity');quantity.append(el('b','ocl-number',s.value),el('span','ocl-unit','pzas'));body.append(el('span','ocl-label',s.label),quantity);
  if(s.pct){const percentage=el('div','ocl-percent');percentage.append(el('b',null,s.pct),el('span',null,'Avance del periodo'));body.append(percentage,meter(s.pct));}
  if(s.pending){const pending=el('div','ocl-pending');pending.append(el('b',null,s.pending+' pzas'),el('span',null,s.pendingLabel));body.append(pending);}
  card.append(body,detailButton(s.id));lanes.append(card);
 });
 const route=el('section','ocl-routes'),routeHead=el('div','ocl-route-head'),routeText=el('div');routeText.append(el('h3',null,'Recorridos'),el('p','ocl-caption','Realizados frente a la meta del periodo'));routeHead.append(icon('chart'),routeText);
 const routeScore=el('div','ocl-route-score');routeScore.append(el('b','ocl-route-number',amount(routes)+' / '+(routes?.cells[2]||'N/D')));const rp=el('div','ocl-route-percent');rp.append(el('b',null,routes?.cells[1]||'N/D'),el('span',null,'de meta'));routeScore.append(rp);
 route.append(routeHead,routeScore,meter(routes?.cells[1]||''),detailButton('routes'));
 const complete=el('details','ocl-full'),summary=el('summary',null,'Reporte completo por tienda · tablas y gráficos');
 const fullBack=el('button','ocl-back','← Regresar al resumen');fullBack.type='button';fullBack.addEventListener('click',()=>{complete.open=false;summary.focus({preventScroll:true});});
 while(root.firstChild)original.append(root.firstChild);
 complete.append(summary,original,fullBack);
 shell.append(el('p','ocl-scope',stamp()),lanes,route,drawer,complete);root.append(shell);
 complete.addEventListener('toggle',()=>{if(complete.open)window.dispatchEvent(new Event('resize'));});
 if(panel)open(panel);
 return true;
}
function fit(){document.querySelectorAll('.ocl-number').forEach(n=>{n.style.removeProperty('font-size');let px=parseFloat(getComputedStyle(n).fontSize);while(n.scrollWidth>n.clientWidth+1&&px>13){px--;n.style.setProperty('font-size',px+'px','important');}});}
function filters(){
 const active=isActive(),grid=document.querySelector('#operativoPeriodBar>.or-report-filter-grid'),period=document.querySelector('#operPeriodSelect');
 if(period){const months={enero:'Ene',febrero:'Feb',marzo:'Mar',abril:'Abr',mayo:'May',junio:'Jun',julio:'Jul',agosto:'Ago',septiembre:'Sep',octubre:'Oct',noviembre:'Nov',diciembre:'Dic'};
  [...period.options].forEach(option=>{const full=option.dataset.centerFullLabel||option.textContent,m=full.match(/^(\w+) (\d{4})$/i);if(m&&months[m[1].toLowerCase()]){option.dataset.centerFullLabel=full;const target=active&&innerWidth<=700?months[m[1].toLowerCase()]+' '+m[2]:full;if(option.textContent!==target)option.textContent=target;}});
 }
 if(!grid)return;
 let button=document.getElementById('centerLaneRefresh');
 const modeLabel=document.querySelector('#operPeriodModeWrap label');
 if(!active){button?.remove();if(modeLabel?.dataset.centerLabel){modeLabel.innerHTML=modeLabel.dataset.centerLabel;delete modeLabel.dataset.centerLabel;}return;}
 if(modeLabel&&!modeLabel.dataset.centerLabel){modeLabel.dataset.centerLabel=modeLabel.innerHTML;modeLabel.textContent='Vista';}
 if(!button){button=el('button','ocl-filter-refresh','↻');button.id='centerLaneRefresh';button.type='button';button.title='Actualizar reporte';button.setAttribute('aria-label','Actualizar reporte');button.addEventListener('click',async()=>{button.disabled=true;try{if(typeof window.V240_renderCenter==='function')await window.V240_renderCenter(document.querySelector('#operPeriodMode')?.value||'month',false);else document.querySelector('#operPeriodSelect')?.dispatchEvent(new Event('change',{bubbles:true}));}finally{button.disabled=false;}});grid.append(button);}
}
window.RopaCenterLanes={isActive,mount,fit,filters};
let printOpen=[];
addEventListener('beforeprint',()=>{printOpen=[...document.querySelectorAll('.ocl-full')].map(x=>[x,x.open]);printOpen.forEach(([x])=>x.open=true);});
addEventListener('afterprint',()=>{printOpen.forEach(([x,open])=>x.open=open);printOpen=[];});
})();
