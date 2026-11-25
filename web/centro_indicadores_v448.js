/* V448: tabla de indicadores por tiendas y productividad real.
   El PDF y las tablas originales no se modifican. */
(function(){
'use strict';
if(window.OR448_SUMMARY_INSTALLED)return;
window.OR448_SUMMARY_INSTALLED=true;
const query=(s,r=document)=>r.querySelector(s);
const node=(tag,cls,label)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(label!==undefined){if(label instanceof Node)e.append(label);else e.textContent=String(label);}return e};
const norm=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
const numeric=v=>{if(v===null||v===undefined||v==='')return null;const n=Number(String(v).replace(/[, %]/g,''));return Number.isFinite(n)?n:null};
const fmt=v=>v==null?'—':Math.round(v).toLocaleString('es-MX');
const pct=v=>v==null?'—':v.toFixed(1)+'%';
const cls=v=>v==null?'unknown':v>=80?'good':v>=60?'medium':'low';
const cache=new Map();
let scheduled=false,activeSignature='';
function setup(){
 const box=query('#operativoDynamicContent'),shell=box&&query('.ocl-shell',box),lanes=shell&&query('.ocl-lanes',shell);
 const payload=window.OR448_CENTER_DATA;
 if(!shell||!lanes||!payload||!query('#page-operativo.active')||!query('#operativoNav [data-opview="Centro Ejecutivo"].active'))return;
 const request=payload.request||{},sig=[payload.sequence,request.period_type,request.period_value,request.store].join('|');
 let summary=query('.or448-summary',shell);
 if(summary&&summary.dataset.signature===sig)return;
 if(!summary){summary=node('section','or448-summary');summary.setAttribute('aria-label','Resumen por tiendas, indicadores y colaboradores con productividad');lanes.after(summary);}
 summary.dataset.signature=sig;activeSignature=sig;
 const cacheKey=[request.period_type,request.period_value,request.store].join('|');
 const saved=cache.get(cacheKey);
 paint(summary,payload.response,saved||null,saved?'':'Consultando productividad...');
 if(saved)return;
 const params=new URLSearchParams({period_type:request.period_type,period_value:request.period_value,store:request.store||'Compañía'});
 fetch('/api/cm-productivity/report?'+params.toString(),{credentials:'same-origin'})
 .then(async r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()})
 .then(d=>{cache.set(cacheKey,d);if(activeSignature===sig&&summary.isConnected)paint(summary,payload.response,d,'')})
 .catch(e=>{console.warn('[V448] Reporte de productividad:',e);if(activeSignature===sig&&summary.isConnected)paint(summary,payload.response,null,'No se pudo consultar la captura digital; se utiliza el padrón productivo del reporte operativo.')});
}
function dataRows(data,digital){
 const all=(Array.isArray(data?.stores)?data.stores:[]).filter(r=>r&&r.store);
 const names=new Set((data?.project_stores||[]).map(x=>norm(typeof x==='string'?x:x?.store||x?.name)).filter(Boolean));
 const selected=norm(window.OR448_CENTER_DATA?.request?.store);
 const allowed=r=>!selected||selected==='compania'||norm(r.store)===selected;
 const byName=all.filter(r=>(!names.size||names.has(norm(r.store)))&&allowed(r));
 const stores=byName.length?byName:all.filter(r=>r.is_project!==false&&allowed(r));
 const goals=numeric(data?.metrics?.meta_recorridos);
 const storeGoal=goals&&stores.length?goals/stores.length:null;
 const routes=new Map((data?.score_by_store||[]).filter(r=>r&&r.store).map(r=>[norm(r.store),numeric(r.recorridos_pct)]));
 // Una persona se cuenta una vez por tienda. Si hay captura digital en la
 // tienda, se sustituye la lectura Excel de esa tienda: nunca se suman ambas.
 const people=new Map();
 function put(records,origin){
  for(const r of Array.isArray(records)?records:[]){
   const p=numeric(r.pieces);if(p==null||p<=0)continue;
   const st=norm(r.store),person=norm(r.employee_no||r.name||r.employee_name);
   if(!st||!person)continue;
   const key=st+'|'+person;
   if(!people.has(key))people.set(key,{store:st,pieces:p,days:Math.max(1,numeric(r.days)||1),origin});
  }
 }
 put(data?.productivity,'Excel');
 if(digital?.use_digital){
  const rows=digital.productivity||[];
  const digitalStores=new Set(rows.filter(r=>numeric(r.pieces)>0).map(r=>norm(r.store)));
  for(const [key,r] of people)if(digitalStores.has(r.store))people.delete(key);
  put(rows,'digital');
 }
 const totals=new Map();
 for(const person of people.values()){
  const agg=totals.get(person.store)||{collaborators:0,pieces:0,days:0};
  agg.collaborators++;agg.pieces+=person.pieces;agg.days+=person.days;
  totals.set(person.store,agg);
 }
 return stores.map(r=>{
  const key=norm(r.store),total=numeric(r.total_pzs)??numeric(r.ingresos)??0;
  const acond=numeric(r.pct_acondicionado)??(total?100*(numeric(r.acondicionado)||0)/total:0);
  const ubicado=numeric(r.pct_ubicado)??(total?100*(numeric(r.ubicado)||0)/total:0);
  const recorridos=routes.get(key)??(storeGoal?100*(numeric(r.recorridos)||0)/storeGoal:0);
  const score=[acond,ubicado,recorridos].reduce((sum,v)=>sum+Math.min(100,Math.max(0,v)),0)/3;
  const prod=totals.get(key);
  return {store:String(r.store),acond,ubicado,recorridos,score,
    collaborators:prod?prod.collaborators:0,average:prod?.collaborators?prod.pieces/prod.collaborators:null};
 }).sort((a,b)=>b.score-a.score||a.store.localeCompare(b.store,'es-MX'));
}
function metric(value,productivity=false){
 return node('span','or448-meter '+(productivity?'productivity':cls(value)),productivity?fmt(value):pct(value));
}
function renderTable(rows){
 const card=node('div','or448-table-card'),scroll=node('div','or448-scroll'),table=node('table','or448-table'),thead=node('thead'),head=node('tr');
 ['#','Tienda','Colabs. con productividad','Prod. promedio por colaborador','% Acond.','% Ubicado','% Recorridos','Score %']
 .forEach(t=>head.append(node('th','',t)));
 thead.append(head);table.append(thead);
 const body=node('tbody'),rendered=[];
 rows.forEach((r,i)=>{
  const tr=node('tr');
  tr.append(node('td','', '#'+(i+1)),node('td','',r.store),
    node('td','',metric(r.collaborators,true)),node('td','',metric(r.average,true)),
    node('td','',metric(r.acond)),node('td','',metric(r.ubicado)),
    node('td','',metric(r.recorridos)),node('td','',metric(r.score)));
  if(i>=10)tr.hidden=true;
  rendered.push(tr);body.append(tr);
 });
 if(!rows.length){const tr=node('tr'),td=node('td','', 'Sin tiendas disponibles para el filtro seleccionado');td.colSpan=8;tr.append(td);body.append(tr);}
 table.append(body);scroll.append(table);card.append(scroll);return {card,rendered};
}
function readout(rows){
 const panel=node('aside','or448-reading');
 panel.append(node('h4','', '◈ Lectura ejecutiva'));
 const data=[
  ['Mejor desempeño (Score %)',rows.filter(r=>r.score>=80).slice(0,3),'good','No hay tiendas con Score ≥80%.'],
  ['Desempeño medio',rows.filter(r=>r.score>=60&&r.score<80).slice(0,3),'medium','No hay tiendas entre 60 y 79.9%.'],
  ['Atención prioritaria',rows.filter(r=>r.score<60).sort((a,b)=>a.score-b.score).slice(0,3),'low','Sin tiendas con Score bajo 60%.']
 ];
 for(const [title,stores,tone,empty] of data){
  const block=node('div','or448-read-item '+tone);
  block.append(node('strong','',title),node('span','',stores.length?stores.map(s=>s.store+' ('+pct(s.score)+')').join(' · '):empty));
  panel.append(block);
 }
 return panel;
}
function paint(el,data,digital,message){
 if(!el.isConnected)return;
 const rows=dataRows(data,digital);el.replaceChildren();
 const heading=node('div','or448-heading'),copy=node('div'),legend=node('div','or448-legend');
 copy.append(node('h3','', '▥ Resumen por tiendas · indicadores %'),
  node('p','', 'Por tienda: colaboradores que capturaron, productividad promedio y porcentajes del periodo.'));
 [['good','≥ 80%'],['medium','60–79.9%'],['low','< 60%']].forEach(([key,label])=>{
  const item=node('span');item.append(node('i','or448-dot '+key),document.createTextNode(label));legend.append(item);
 });
 heading.append(copy,legend);el.append(heading);
 const grid=node('div','or448-grid'),result=renderTable(rows);
 grid.append(result.card,readout(rows));el.append(grid);
 const foot=node('div','or448-footer');
 foot.append(node('span','',message||'Prod. prom.: piezas procesadas ÷ colaboradores con captura del periodo. Score: promedio de % Acond., % Ubicado y % Recorridos (topados a 100%).'));
 if(rows.length>10){
  const more=node('button','or448-more','Ver las '+rows.length+' tiendas');more.type='button';let opened=false;
  more.addEventListener('click',()=>{
   opened=!opened;result.rendered.forEach((r,i)=>r.hidden=!opened&&i>=10);
   more.textContent=opened?'Ver primeras 10 tiendas':'Ver las '+rows.length+' tiendas';
  });foot.append(more);
 }
 el.append(foot);
}
function queue(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;setup()});}
function init(){
 const host=query('#operativoDynamicContent');
 if(host)new MutationObserver(records=>{
  if(records.some(r=>[...r.addedNodes].some(n=>n.nodeType===1&&(n.matches?.('.ocl-shell,.ocl-lanes')||n.querySelector?.('.ocl-lanes')))))queue();
 }).observe(host,{subtree:true,childList:true});
 addEventListener('or448:center-data',queue);
 addEventListener('pageshow',queue);
 queue();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();