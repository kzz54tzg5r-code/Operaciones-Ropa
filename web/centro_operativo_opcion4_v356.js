/* V360: Centro Operativo compacto con registros del backend, sin datos ficticios.
   Usa únicamente la respuesta real de Centro Operativo y conserva el reporte original. */
(() => {
 'use strict';
 if (window.__or360CenterInstalled) return;
 window.__or360CenterInstalled = true;
 const q = selector => document.querySelector(selector);
 const el = (tag,cls,text) => {
  const node=document.createElement(tag);
  if(cls) node.className=cls;
  if(text!==undefined) node.textContent=String(text);
  return node;
 };
 const num=value=>{
  if(value===null||value===undefined||value==='')return null;
  const n=Number(value);
  return Number.isFinite(n)?n:null;
 };
 const fmt=value=>value===null||value===undefined?'—':new Intl.NumberFormat('es-MX',{maximumFractionDigits:0}).format(value);
 const pct=value=>value===null||value===undefined?'—':Number(value).toFixed(1)+'%';
 const moduleActive=()=>!!q('#page-operativo.active')&&!q('#appView')?.classList.contains('hidden');
 const centerActive=()=>moduleActive()&&!!q('#operativoNav [data-opview="Centro Ejecutivo"].active');
 function panel(title,subtitle,color){
  const box=el('section','or356-card');
  box.style.borderTop='3px solid '+color;
  const head=el('header','or356-cardhead'),copy=el('div');
  copy.append(el('strong',null,title),el('small',null,subtitle));
  head.append(copy);box.append(head);
  return {box,head};
 }
 function table(rows,original,scope){
  const out=panel('Detalle por tienda','Ingresos, acondicionado, ubicado y recorridos · '+scope,'#1676e6');
  const exportBtn=el('button','or356-action','Exportar');
  exportBtn.type='button';
  exportBtn.addEventListener('click',()=>{
   const target=original.querySelector('.report-actions');
   (target||original).scrollIntoView({block:'start',behavior:'smooth'});
   target?.querySelector('button')?.focus({preventScroll:true});
  });
  out.head.append(exportBtn);
  if(!rows.length){
   out.box.append(el('p','or356-empty','No hay registros por tienda para el periodo y alcance seleccionados.'));
   return out.box;
  }
  const scroll=el('div','or356-scroll'),t=el('table','or356-table');
  t.setAttribute('aria-label','Detalle operativo real por tienda');
  const thead=el('thead'),tr=el('tr');
  ['#','Tienda','Ingresos','Acondicionado','Ubicado','Pend. acond.','Pend. ubicar','Recorridos'].forEach(label=>tr.append(el('th',null,label)));
  thead.append(tr);t.append(thead);
  const tbody=el('tbody');
  rows.forEach((r,i)=>{
   const line=el('tr');
   [i+1,r.store,fmt(num(r.ingresos)),fmt(num(r.acondicionado)),fmt(num(r.ubicado)),
    fmt(num(r.pendiente_acondicionar)),fmt(num(r.pendiente_ubicar)),fmt(num(r.recorridos))]
    .forEach(value=>line.append(el('td',null,value)));
   tbody.append(line);
  });
  t.append(tbody);scroll.append(t);out.box.append(scroll);
  return out.box;
 }
 function bars(title,subtitle,source,color,limit){
  const card=panel(title,subtitle,color);
  const rows=source.filter(r=>r&&r.store&&num(r.n)!==null).slice(0,limit||6);
  if(!rows.length){
   card.box.append(el('p','or356-empty','No hay valores publicados para este indicador en el periodo.'));
   return card.box;
  }
  const list=el('div','or356-rows');
  const max=Math.max(1,...rows.map(r=>num(r.n)||0));
  rows.forEach(r=>{
   const n=num(r.n),line=el('div','or356-row'),name=el('span','or356-name',r.store);
   name.title=r.store;
   const track=el('div','or356-track'),fill=el('div','or356-fill');
   fill.style.setProperty('--or356-color',color);
   fill.style.width=Math.min(100,Math.max(0,100*n/max)).toFixed(2)+'%';
   track.append(fill);
   line.append(name,track,el('span','or356-value',r.label||fmt(n)));
   list.append(line);
  });
  card.box.append(list);
  return card.box;
 }
 let signature='',scheduled=false;
 function render(){
  document.body.classList.toggle('or356-module-active',moduleActive());
  document.body.classList.toggle('or356-center-active',centerActive());
  if(!centerActive())return;
  const shell=q('#operativoDynamicContent .ocl-shell');
  const original=shell?.querySelector('.ocl-original'),lanes=shell?.querySelector('.ocl-lanes');
  if(!shell||!original||!lanes)return;
  const payload=window.OR356_CENTER_DATA;
  if(!payload||!payload.response||!payload.response.available)return;
  const request=payload.request||{},data=payload.response;
  const stores=Array.isArray(data.stores)?data.stores.filter(r=>r&&r.store):[];
  const recovery=Array.isArray(data.recovery_by_store)?data.recovery_by_store.filter(r=>r&&r.store):[];
  const key=JSON.stringify({request,stores,recovery});
  let dash=shell.querySelector(':scope > .or356-dashboard');
  if(dash&&signature===key)return;
  if(!dash){
   dash=el('div','or356-dashboard');
   lanes.after(dash);
   dash.after(el('div','or356-divider','↓ Fin de pantalla principal · Desplaza para ver el reporte completo ↓'));
  }
  signature=key;
  const right=el('div','or356-sidepanels');
  const pending=stores.map(r=>({
   store:String(r.store),n:num(r.pendiente_acondicionar),label:fmt(num(r.pendiente_acondicionar))+' pzas'
  })).sort((a,b)=>(b.n||0)-(a.n||0));
  const recovered=recovery.map(r=>({
   store:String(r.store),n:num(r.recovery_pct),label:pct(num(r.recovery_pct))
  })).sort((a,b)=>(b.n||0)-(a.n||0));
  const progress=stores.map(r=>{
   const ingreso=num(r.ingresos),ubicado=num(r.ubicado);
   const computed=ingreso>0&&ubicado!==null?100*ubicado/ingreso:null;
   const n=num(r.pct_ubicado)??computed;
   return {store:String(r.store),n,label:pct(n)};
  }).sort((a,b)=>(b.n||0)-(a.n||0));
  right.append(
   bars('Pendientes por tienda','Piezas pendientes de acondicionar',pending,'#f04463',6),
   bars('Recuperación por tienda','Recuperación económica sobre valor devuelto',recovered,'#18ae79',6),
   bars('Avance en piso por tienda','Piezas ubicadas sobre ingresos',progress,'#8842ef',6)
  );
  const scope=[request.value,request.store].filter(Boolean).join(' · ')||'Periodo consultado';
  dash.replaceChildren(table(stores,original,scope),right);
 }
 function schedule(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;render();});
 }
 function init(){
  schedule();
  const nav=q('#operativoNav'),page=q('#page-operativo'),app=q('#appView');
  if(nav)new MutationObserver(schedule).observe(nav,{attributes:true,attributeFilter:['class','style','aria-selected'],childList:true,subtree:true});
  if(page)new MutationObserver(schedule).observe(page,{attributes:true,attributeFilter:['class']});
  if(app)new MutationObserver(schedule).observe(app,{attributes:true,attributeFilter:['class']});
  const content=q('#operativoDynamicContent');
  if(content)new MutationObserver(schedule).observe(content,{childList:true,subtree:true});
  window.addEventListener('or356:center-data',schedule);
  window.addEventListener('pageshow',schedule,{passive:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();
