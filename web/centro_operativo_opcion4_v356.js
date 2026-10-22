/* V356 — Centro Operativo, alternativa seleccionada: sin datos de demostración.
   Sólo extrae celdas ya publicadas por el reporte original para representarlas
   en una tabla amplia y tres paneles visuales. */
(() => {
 'use strict';
 if(window.__or356Loaded)return;
 window.__or356Loaded=true;
 const $=s=>document.querySelector(s);
 const txt=n=>(n?.textContent||'').replace(/\s+/g,' ').trim();
 const lower=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const mk=(tag,cls,value)=>{
  const n=document.createElement(tag);
  if(cls)n.className=cls;
  if(value!==undefined)n.textContent=value;
  return n;
 };
 const number=value=>{
  const s=String(value||'').replace(/[,\s$%]/g,'').replace(/[^0-9.\-]/g,'');
  const n=Number(s);
  return s!==''&&Number.isFinite(n)?n:null;
 };
 const fmt=n=>Number.isFinite(n)?new Intl.NumberFormat('es-MX',{maximumFractionDigits:0}).format(n):'—';
 const isCenter=()=>{
  const active=$('#operativoNav [data-opview].active');
  return !!(active&&/^(centro ejecutivo|centro operativo)$/i.test(active.dataset.opview||'')
   && $('#page-operativo')?.classList.contains('active'));
 };
 const isModule=()=>!!($('#page-operativo')?.classList.contains('active')
   && !$('#appView')?.classList.contains('hidden'));
 const tableByHeaders=(base,test)=>[...base.querySelectorAll('table')].find(t=>{
  const cells=[...t.querySelectorAll('thead th')].map(txt).map(lower);
  return test(cells);
 });
 // El backend de Centro Operativo ya devuelve registros por tienda; no
 // depender de que el HTML diferido se haya insertado en .ocl-original.
 const sourcePayload=()=>window.OR356_CENTER_DATA||null;
 const validNumber=v=>{const n=Number(v);return v!==null&&v!==undefined&&v!==''&&Number.isFinite(n)?n:null;};
 const getOperational=base=>{
  const data=sourcePayload();
  if(data){
   const stores=data.response?.stores||[];
   return stores.filter(r=>r&&r.store).map((r,i)=>({
    rank:String(i+1),store:String(r.store),
    received:fmt(validNumber(r.ingresos)),
    routes:fmt(validNumber(r.recorridos)),
    conditioned:fmt(validNumber(r.acondicionado)),
    located:fmt(validNumber(r.ubicado)),
    pendingCondition:fmt(validNumber(r.pendiente_acondicionar)),
    pendingLocation:fmt(validNumber(r.pendiente_ubicar)),
    rawPending:validNumber(r.pendiente_acondicionar),
    rawLocated:validNumber(r.ubicado),
    rawReceived:validNumber(r.ingresos),
    rawRoutes:validNumber(r.recorridos),
    rawAcconditioned:validNumber(r.acondicionado),
    pctLocated:validNumber(r.pct_ubicado)
   }));
  }
  const t=tableByHeaders(base,cols=>cols.some(v=>v.includes('piezas recolectadas'))&&cols.some(v=>v.includes('pendiente de ubicar')));
  if(!t)return [];
  return [...t.querySelectorAll('tbody tr')].map(tr=>{
   const c=[...tr.cells].map(txt);
   if(c.length<11||!c[1])return null;
   return {rank:c[0],store:c[1],received:c[5],routes:c[6],conditioned:c[7],located:c[8],
    pendingCondition:c[9],pendingLocation:c[10],rawPending:number(c[9]),
    rawLocated:number(c[8]),rawReceived:number(c[5])};
  }).filter(Boolean);
 };
 const getRecovery=base=>{
  const data=sourcePayload();
  if(data){
   return (data.response?.recovery_by_store||[]).filter(r=>r&&r.store).map(r=>({
    store:String(r.store),
    conversion:r.conversion_pct==null?'—':(Number(r.conversion_pct).toFixed(1)+'%'),
    money:r.recovered_value==null?'—':'
 function button(title,onClick){
  const b=mk('button','or356-action',title);b.type='button';b.addEventListener('click',onClick);return b;
 }
 function card(title,subtitle,accent){
  const section=mk('section','or356-card');
  if(accent)section.style.borderTop='3px solid '+accent;
  const head=mk('header','or356-cardhead'),meta=mk('div');
  meta.append(mk('strong',null,title),mk('small',null,subtitle));
  head.append(meta);section.append(head);
  return {section,head};
 }
 function makeTable(rows,original){
  const c=card('Detalle por tienda','Recolección, acondicionamiento y ubicación','#1676e6');
  c.head.append(button('Exportar',()=>{
   const action=original.querySelector('.report-actions');
   if(action){action.scrollIntoView({block:'center',behavior:'smooth'});action.querySelector('button')?.focus({preventScroll:true});}
   else original.scrollIntoView({block:'start',behavior:'smooth'});
  }));
  if(!rows.length){c.section.append(mk('p','or356-empty','El detalle por tienda aparecerá cuando se carguen los datos del periodo.'));return c.section;}
  const wrap=mk('div','or356-scroll'),table=mk('table','or356-table');
  table.setAttribute('aria-label','Resumen operativo por tienda, valores reales del reporte');
  const thead=mk('thead'),tr=mk('tr');
  ['#','Tienda','Ingresos','Acondicionado','Ubicado','Pend. acond.','Pend. ubicar','Recorridos'].forEach(label=>tr.append(mk('th',null,label)));
  thead.append(tr);table.append(thead);
  const body=mk('tbody');
  rows.forEach(r=>{
   const line=mk('tr');
   [r.rank,r.store,r.received,r.conditioned,r.located,r.pendingCondition,r.pendingLocation,r.routes].forEach(v=>line.append(mk('td',null,v)));
   body.append(line);
  });
  table.append(body);wrap.append(table);c.section.append(wrap);
  return c.section;
 }
 function bars(cardTitle,sub,rows,metric,accent,format,limit=6){
  const c=card(cardTitle,sub,accent);
  const n=rows.filter(r=>Number.isFinite(metric(r))).slice(0,limit);
  if(!n.length){c.section.append(mk('p','or356-empty','Sin datos disponibles para este indicador en el periodo seleccionado.'));return c.section;}
  const max=Math.max(1,...n.map(metric)),container=mk('div','or356-rows');
  n.forEach(r=>{
   const value=metric(r),line=mk('div','or356-row');
   const label=mk('span','or356-name',r.store);
   label.title=r.store;
   const track=mk('div','or356-track');
   const fill=mk('div','or356-fill');
   fill.style.setProperty('--or356-color',accent);
   fill.style.width=Math.max(0,Math.min(100,value/max*100)).toFixed(2)+'%';
   track.append(fill);
   const valueText=mk('span','or356-value',format(r));
   line.append(label,track,valueText);container.append(line);
  });
  c.section.append(container);return c.section;
 }
 function recoveryChart(rows){
  const c=card('Gráfico de recuperación','Porcentaje de recuperación por tienda, según el reporte original','#8842ef');
  const data=rows.filter(r=>Number.isFinite(number(r.pct))).slice(0,6);
  if(!data.length){c.section.append(mk('p','or356-empty','No hay porcentajes de recuperación publicados para este periodo.'));return c.section;}
  const list=mk('div','or356-rows');
  data.forEach(r=>{
   const value=number(r.pct),line=mk('div','or356-row');
   const label=mk('span','or356-name',r.store);label.title=r.store;
   const track=mk('div','or356-track'),fill=mk('div','or356-fill');
   fill.style.setProperty('--or356-color','#8842ef');
   fill.style.width=Math.max(0,Math.min(100,value)).toFixed(2)+'%';
   track.append(fill);
   line.append(label,track,mk('span','or356-value',r.pct));
   list.append(line);
  });
  c.section.append(list);return c.section;
 }
 let lastSignature='';
 function updateDashboard(){
  if(!isCenter())return;
  const shell=$('#operativoDynamicContent .ocl-shell');
  const original=shell?.querySelector('.ocl-original');
  const lanes=shell?.querySelector('.ocl-lanes');
  if(!shell||!original||!lanes)return;
  const operation=getOperational(original),recovery=getRecovery(original);
  const signature=JSON.stringify({request:sourcePayload()?.request,operation,recovery});
  let dash=shell.querySelector(':scope > .or356-dashboard');
  if(dash&&lastSignature===signature)return;
  if(!dash){
   dash=mk('div','or356-dashboard');
   lanes.after(dash);
   dash.after(mk('div','or356-divider','↓ Fin de pantalla principal · Desplaza para ver el reporte completo ↓'));
  }
  lastSignature=signature;
  const right=mk('div','or356-sidepanels');
  const pending=[...operation].sort((a,b)=>(b.rawPending??number(b.pendingCondition)??0)-(a.rawPending??number(a.pendingCondition)??0));
  const pctScope=operation.map(r=>({
   store:r.store,pct:r.pctLocated!=null?r.pctLocated:(r.rawReceived?100*(r.rawLocated||0)/r.rawReceived:null)
  }));
  right.append(
   bars('Pendientes por tienda','Piezas pendientes de acondicionar',pending,r=>r.rawPending??number(r.pendingCondition),'#f04463',r=>r.pendingCondition),
   bars('Recuperación por tienda','Porcentaje económico recuperado',recovery,r=>number(r.pct),'#18ae79',r=>r.pct),
   bars('Avance en piso por tienda','Piezas ubicadas sobre ingresos',pctScope,r=>r.pct,'#8842ef',r=>r.pct==null?'—':r.pct.toFixed(1)+'%')
  );
  dash.replaceChildren(makeTable(operation,original),right);
 }
 function updateClasses(){
  document.body.classList.toggle('or356-module-active',isModule());
  document.body.classList.toggle('or356-center-active',isCenter());
 }
 let scheduled=false;
 function refresh(){
  if(scheduled)return;scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;updateClasses();updateDashboard();});
 }
 function init(){
  refresh();
  const nav=$('#operativoNav'),page=$('#page-operativo'),app=$('#appView');
  if(nav)new MutationObserver(refresh).observe(nav,{subtree:true,attributes:true,attributeFilter:['class','hidden','style','aria-selected'],childList:true});
  if(page)new MutationObserver(refresh).observe(page,{attributes:true,attributeFilter:['class']});
  if(app)new MutationObserver(refresh).observe(app,{attributes:true,attributeFilter:['class']});
  const content=$('#operativoDynamicContent');
  if(content)new MutationObserver(refresh).observe(content,{subtree:true,childList:true});
  window.addEventListener('or356:center-data',refresh);\n  window.addEventListener('pageshow',refresh,{passive:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();
+fmt(validNumber(r.recovered_value)),
    pct:r.recovery_pct==null?'—':(Number(r.recovery_pct).toFixed(1)+'%')
   }));
  }
  const t=tableByHeaders(base,cols=>cols.some(v=>v.includes('recup. %'))&&cols.some(v=>v.includes('recuperacion 
 function button(title,onClick){
  const b=mk('button','or356-action',title);b.type='button';b.addEventListener('click',onClick);return b;
 }
 function card(title,subtitle,accent){
  const section=mk('section','or356-card');
  if(accent)section.style.borderTop='3px solid '+accent;
  const head=mk('header','or356-cardhead'),meta=mk('div');
  meta.append(mk('strong',null,title),mk('small',null,subtitle));
  head.append(meta);section.append(head);
  return {section,head};
 }
 function makeTable(rows,original){
  const c=card('Detalle por tienda','Recolección, acondicionamiento y ubicación','#1676e6');
  c.head.append(button('Exportar',()=>{
   const action=original.querySelector('.report-actions');
   if(action){action.scrollIntoView({block:'center',behavior:'smooth'});action.querySelector('button')?.focus({preventScroll:true});}
   else original.scrollIntoView({block:'start',behavior:'smooth'});
  }));
  if(!rows.length){c.section.append(mk('p','or356-empty','El detalle por tienda aparecerá cuando se carguen los datos del periodo.'));return c.section;}
  const wrap=mk('div','or356-scroll'),table=mk('table','or356-table');
  table.setAttribute('aria-label','Resumen operativo por tienda, valores reales del reporte');
  const thead=mk('thead'),tr=mk('tr');
  ['#','Tienda','Recolectadas (pzas)','Acondicionado','Ubicado','Pend. acond.','Pend. ubicar','Recorridos'].forEach(label=>tr.append(mk('th',null,label)));
  thead.append(tr);table.append(thead);
  const body=mk('tbody');
  rows.forEach(r=>{
   const line=mk('tr');
   [r.rank,r.store,r.received,r.conditioned,r.located,r.pendingCondition,r.pendingLocation,r.routes].forEach(v=>line.append(mk('td',null,v)));
   body.append(line);
  });
  table.append(body);wrap.append(table);c.section.append(wrap);
  return c.section;
 }
 function bars(cardTitle,sub,rows,metric,accent,format,limit=6){
  const c=card(cardTitle,sub,accent);
  const n=rows.filter(r=>Number.isFinite(metric(r))).slice(0,limit);
  if(!n.length){c.section.append(mk('p','or356-empty','Sin datos disponibles para este indicador en el periodo seleccionado.'));return c.section;}
  const max=Math.max(1,...n.map(metric)),container=mk('div','or356-rows');
  n.forEach(r=>{
   const value=metric(r),line=mk('div','or356-row');
   const label=mk('span','or356-name',r.store);
   label.title=r.store;
   const track=mk('div','or356-track');
   const fill=mk('div','or356-fill');
   fill.style.setProperty('--or356-color',accent);
   fill.style.width=Math.max(0,Math.min(100,value/max*100)).toFixed(2)+'%';
   track.append(fill);
   const valueText=mk('span','or356-value',format(r));
   line.append(label,track,valueText);container.append(line);
  });
  c.section.append(container);return c.section;
 }
 function recoveryChart(rows){
  const c=card('Gráfico de recuperación','Porcentaje de recuperación por tienda, según el reporte original','#8842ef');
  const data=rows.filter(r=>Number.isFinite(number(r.pct))).slice(0,6);
  if(!data.length){c.section.append(mk('p','or356-empty','No hay porcentajes de recuperación publicados para este periodo.'));return c.section;}
  const list=mk('div','or356-rows');
  data.forEach(r=>{
   const value=number(r.pct),line=mk('div','or356-row');
   const label=mk('span','or356-name',r.store);label.title=r.store;
   const track=mk('div','or356-track'),fill=mk('div','or356-fill');
   fill.style.setProperty('--or356-color','#8842ef');
   fill.style.width=Math.max(0,Math.min(100,value)).toFixed(2)+'%';
   track.append(fill);
   line.append(label,track,mk('span','or356-value',r.pct));
   list.append(line);
  });
  c.section.append(list);return c.section;
 }
 let lastSignature='';
 function updateDashboard(){
  if(!isCenter())return;
  const shell=$('#operativoDynamicContent .ocl-shell');
  const original=shell?.querySelector('.ocl-original');
  const lanes=shell?.querySelector('.ocl-lanes');
  if(!shell||!original||!lanes)return;
  const operation=getOperational(original),recovery=getRecovery(original);
  const signature=JSON.stringify({operation,recovery});
  let dash=shell.querySelector(':scope > .or356-dashboard');
  if(dash&&lastSignature===signature)return;
  if(!dash){
   dash=mk('div','or356-dashboard');
   lanes.after(dash);
   dash.after(mk('div','or356-divider','↓ Fin de pantalla principal · Desplaza para ver el reporte completo ↓'));
  }
  lastSignature=signature;
  const right=mk('div','or356-sidepanels');
  const pending=[...operation].sort((a,b)=>(number(b.pendingCondition)||0)-(number(a.pendingCondition)||0));
  right.append(
   bars('Pendientes por tienda','Piezas pendientes de acondicionar',pending,r=>number(r.pendingCondition),'#f04463',r=>r.pendingCondition),
   bars('Recuperación por tienda','Recuperación económica (%) por tienda',recovery,r=>number(r.pct),'#18ae79',r=>r.pct),
   recoveryChart(recovery)
  );
  dash.replaceChildren(makeTable(operation,original),right);
 }
 function updateClasses(){
  document.body.classList.toggle('or356-module-active',isModule());
  document.body.classList.toggle('or356-center-active',isCenter());
 }
 let scheduled=false;
 function refresh(){
  if(scheduled)return;scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;updateClasses();updateDashboard();});
 }
 function init(){
  refresh();
  const nav=$('#operativoNav'),page=$('#page-operativo'),app=$('#appView');
  if(nav)new MutationObserver(refresh).observe(nav,{subtree:true,attributes:true,attributeFilter:['class','hidden','style','aria-selected'],childList:true});
  if(page)new MutationObserver(refresh).observe(page,{attributes:true,attributeFilter:['class']});
  if(app)new MutationObserver(refresh).observe(app,{attributes:true,attributeFilter:['class']});
  const content=$('#operativoDynamicContent');
  if(content)new MutationObserver(refresh).observe(content,{subtree:true,childList:true});
  window.addEventListener('pageshow',refresh,{passive:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();
)));
  if(!t)return [];
  return [...t.querySelectorAll('tbody tr')].map(tr=>{
   const c=[...tr.cells].map(txt);
   if(c.length<10||!c[1])return null;
   return {store:c[1].replace(/\s*proyecto\s*/i,'').trim(),conversion:c[4],money:c[6],pct:c[7]};
  }).filter(Boolean);
 };
 function button(title,onClick){
  const b=mk('button','or356-action',title);b.type='button';b.addEventListener('click',onClick);return b;
 }
 function card(title,subtitle,accent){
  const section=mk('section','or356-card');
  if(accent)section.style.borderTop='3px solid '+accent;
  const head=mk('header','or356-cardhead'),meta=mk('div');
  meta.append(mk('strong',null,title),mk('small',null,subtitle));
  head.append(meta);section.append(head);
  return {section,head};
 }
 function makeTable(rows,original){
  const c=card('Detalle por tienda','Recolección, acondicionamiento y ubicación','#1676e6');
  c.head.append(button('Exportar',()=>{
   const action=original.querySelector('.report-actions');
   if(action){action.scrollIntoView({block:'center',behavior:'smooth'});action.querySelector('button')?.focus({preventScroll:true});}
   else original.scrollIntoView({block:'start',behavior:'smooth'});
  }));
  if(!rows.length){c.section.append(mk('p','or356-empty','El detalle por tienda aparecerá cuando se carguen los datos del periodo.'));return c.section;}
  const wrap=mk('div','or356-scroll'),table=mk('table','or356-table');
  table.setAttribute('aria-label','Resumen operativo por tienda, valores reales del reporte');
  const thead=mk('thead'),tr=mk('tr');
  ['#','Tienda','Recolectadas (pzas)','Acondicionado','Ubicado','Pend. acond.','Pend. ubicar','Recorridos'].forEach(label=>tr.append(mk('th',null,label)));
  thead.append(tr);table.append(thead);
  const body=mk('tbody');
  rows.forEach(r=>{
   const line=mk('tr');
   [r.rank,r.store,r.received,r.conditioned,r.located,r.pendingCondition,r.pendingLocation,r.routes].forEach(v=>line.append(mk('td',null,v)));
   body.append(line);
  });
  table.append(body);wrap.append(table);c.section.append(wrap);
  return c.section;
 }
 function bars(cardTitle,sub,rows,metric,accent,format,limit=6){
  const c=card(cardTitle,sub,accent);
  const n=rows.filter(r=>Number.isFinite(metric(r))).slice(0,limit);
  if(!n.length){c.section.append(mk('p','or356-empty','Sin datos disponibles para este indicador en el periodo seleccionado.'));return c.section;}
  const max=Math.max(1,...n.map(metric)),container=mk('div','or356-rows');
  n.forEach(r=>{
   const value=metric(r),line=mk('div','or356-row');
   const label=mk('span','or356-name',r.store);
   label.title=r.store;
   const track=mk('div','or356-track');
   const fill=mk('div','or356-fill');
   fill.style.setProperty('--or356-color',accent);
   fill.style.width=Math.max(0,Math.min(100,value/max*100)).toFixed(2)+'%';
   track.append(fill);
   const valueText=mk('span','or356-value',format(r));
   line.append(label,track,valueText);container.append(line);
  });
  c.section.append(container);return c.section;
 }
 function recoveryChart(rows){
  const c=card('Gráfico de recuperación','Porcentaje de recuperación por tienda, según el reporte original','#8842ef');
  const data=rows.filter(r=>Number.isFinite(number(r.pct))).slice(0,6);
  if(!data.length){c.section.append(mk('p','or356-empty','No hay porcentajes de recuperación publicados para este periodo.'));return c.section;}
  const list=mk('div','or356-rows');
  data.forEach(r=>{
   const value=number(r.pct),line=mk('div','or356-row');
   const label=mk('span','or356-name',r.store);label.title=r.store;
   const track=mk('div','or356-track'),fill=mk('div','or356-fill');
   fill.style.setProperty('--or356-color','#8842ef');
   fill.style.width=Math.max(0,Math.min(100,value)).toFixed(2)+'%';
   track.append(fill);
   line.append(label,track,mk('span','or356-value',r.pct));
   list.append(line);
  });
  c.section.append(list);return c.section;
 }
 let lastSignature='';
 function updateDashboard(){
  if(!isCenter())return;
  const shell=$('#operativoDynamicContent .ocl-shell');
  const original=shell?.querySelector('.ocl-original');
  const lanes=shell?.querySelector('.ocl-lanes');
  if(!shell||!original||!lanes)return;
  const operation=getOperational(original),recovery=getRecovery(original);
  const signature=JSON.stringify({operation,recovery});
  let dash=shell.querySelector(':scope > .or356-dashboard');
  if(dash&&lastSignature===signature)return;
  if(!dash){
   dash=mk('div','or356-dashboard');
   lanes.after(dash);
   dash.after(mk('div','or356-divider','↓ Fin de pantalla principal · Desplaza para ver el reporte completo ↓'));
  }
  lastSignature=signature;
  const right=mk('div','or356-sidepanels');
  const pending=[...operation].sort((a,b)=>(number(b.pendingCondition)||0)-(number(a.pendingCondition)||0));
  right.append(
   bars('Pendientes por tienda','Piezas pendientes de acondicionar',pending,r=>number(r.pendingCondition),'#f04463',r=>r.pendingCondition),
   bars('Recuperación por tienda','Recuperación económica (%) por tienda',recovery,r=>number(r.pct),'#18ae79',r=>r.pct),
   recoveryChart(recovery)
  );
  dash.replaceChildren(makeTable(operation,original),right);
 }
 function updateClasses(){
  document.body.classList.toggle('or356-module-active',isModule());
  document.body.classList.toggle('or356-center-active',isCenter());
 }
 let scheduled=false;
 function refresh(){
  if(scheduled)return;scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;updateClasses();updateDashboard();});
 }
 function init(){
  refresh();
  const nav=$('#operativoNav'),page=$('#page-operativo'),app=$('#appView');
  if(nav)new MutationObserver(refresh).observe(nav,{subtree:true,attributes:true,attributeFilter:['class','hidden','style','aria-selected'],childList:true});
  if(page)new MutationObserver(refresh).observe(page,{attributes:true,attributeFilter:['class']});
  if(app)new MutationObserver(refresh).observe(app,{attributes:true,attributeFilter:['class']});
  const content=$('#operativoDynamicContent');
  if(content)new MutationObserver(refresh).observe(content,{subtree:true,childList:true});
  window.addEventListener('pageshow',refresh,{passive:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();
