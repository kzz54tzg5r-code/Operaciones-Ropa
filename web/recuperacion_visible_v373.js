/* V373: Recuperación por tienda siempre visible en Centro Operativo.
   Respeta alcance Proyecto para KPIs y devuelve todas las tiendas permitidas
   sólo a la tabla de recuperación, según /project-scope-v151. */
(() => {
 'use strict';
 if(window.__or373VisibleRecovery)return;
 window.__or373VisibleRecovery=true;
 const q=(s,root=document)=>root.querySelector(s);
 const valid=()=>!!q('#page-operativo.active')&&!q('#appView')?.classList.contains('hidden')&&
   /^(Centro Ejecutivo|Centro Operativo)$/.test(q('#operativoNav [data-opview].active')?.dataset.opview||'');
 const number=v=>{const n=Number(v);return Number.isFinite(n)?n:0};
 const pieces=v=>number(v).toLocaleString('es-MX',{maximumFractionDigits:0});
 const money=v=>'$'+(number(v)/1000).toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1});
 const title=s=>{const e=document.createElement('h3');e.className='or373-title';e.textContent=s;return e};
 const el=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=String(value);return e};
 let current='',loading='',queued=false;
 function params(){
  return {
   period_type:q('#operPeriodMode')?.value||'day',
   period_value:q('#operPeriodSelect')?.value||'',
   store:q('#operStoreSelect')?.value||'Compañía',
   area:'', activity:'', compact:'true'
  };
 }
 function table(records){
  const wrap=el('div','or373-scroll'),t=el('table','table or373-table');
  t.setAttribute('aria-label','Recuperación por tienda por periodo');
  const headers=['#','Tienda','Dev pzs','Recup. pzs','Conv. %','Valor DEV (miles $)','Recup. (miles $)','Recup. %','Pend. pzs','Pend. (miles $)'];
  const head=el('thead'),headRow=el('tr');
  headers.forEach(x=>headRow.append(el('th',null,x)));
  head.append(headRow);t.append(head);
  const body=el('tbody');
  const sorted=[...records].sort((a,b)=>number(b.dev_pzs)-number(a.dev_pzs)||String(a.store).localeCompare(String(b.store),'es'));
  if(!sorted.length){
   const tr=el('tr'),td=el('td',null,'Sin registros de recuperación para las tiendas permitidas');
   td.colSpan=headers.length;tr.append(td);body.append(tr);
  }
  sorted.forEach((r,i)=>{
   const row=el('tr',r.is_project?'or373-project':'');
   const values=[
    '#'+(i+1),r.store,pieces(r.dev_pzs),pieces(r.converted_pieces),
    number(r.conversion_pct).toFixed(1)+'%',money(r.return_value),
    money(r.recovered_value),number(r.recovery_pct).toFixed(1)+'%',
    pieces(r.pending_pieces),money(r.pending_value)
   ];
   values.forEach((v,j)=>{const cell=el('td',j===1?'or373-store':'',v);row.append(cell)});
   body.append(row);
  });
  t.append(body);wrap.append(t);return wrap;
 }
 function makeBox(container){
  const panel=el('section','or373-recovery-panel');
  panel.dataset.or373='recovery-by-store';
  panel.append(title('Recuperación por tienda'));
  const subtitle=el('p','or373-sub','Comparativo del periodo y tienda seleccionados · unidades y pesos en miles');
  panel.append(subtitle);
  const status=el('div','or373-status','Consultando recuperación del periodo…');
  status.setAttribute('role','status');panel.append(status);
  container.append(panel);
  return panel;
 }
 function relocateExisting(parent,target){
  const kids=[...parent.children];
  const heading=kids.find(node=>node.classList?.contains('title')&&/^Recuperación por tienda$/i.test(node.textContent.trim()));
  if(!heading)return false;
  const next=heading.nextElementSibling;
  if(!next?.querySelector('table'))return false;
  const rows=next.querySelectorAll('tbody tr');
  if(!rows.length)return false;
  const panel=makeBox(target);
  panel.querySelector('.or373-status').remove();
  panel.append(next);
  heading.remove();
  next.classList.add('or373-scroll');
  return true;
 }
 async function fill(panel,filter,key){
  if(loading===key)return;
  loading=key;
  try{
   const url='/api/operations/project-scope-v151?'+new URLSearchParams(filter);
   const response=await fetch(url,{cache:'no-store',credentials:'same-origin'});
   const result=await response.json();
   if(!response.ok)throw Error(String(result.detail||'No se pudo consultar recuperación'));
   if(!valid()||JSON.stringify(params())!==key||!panel.isConnected)return;
   const status=q('.or373-status',panel);
   if(status)status.remove();
   panel.append(table(Array.isArray(result.recovery_by_store)?result.recovery_by_store:[]));
   const zero=!(result.recovery_by_store||[]).some(r=>number(r.dev_pzs)>0);
   if(zero){
    const alert=el('p','or373-warning',
      result.recovery_source?.source_warning ||
      'Este periodo muestra DEV en cero. Verifica la conciliación con el archivo mensual publicado.');
    panel.append(alert);
   }
   panel.dataset.period=key;
  }catch(error){
   const status=q('.or373-status',panel);
   if(status)status.textContent='No fue posible mostrar Recuperación por tienda: '+error.message;
  }finally{if(loading===key)loading=''}
 }
 function render(){
  if(!valid())return;
  const root=q('#operativoDynamicContent'),original=q('.ocl-original',root)||root;
  if(!original?.querySelector('.monthly-cross-table'))return;
  const filter=params(),key=JSON.stringify(filter);
  const detail=[...original.querySelectorAll(':scope > .title')].find(x=>/^Detalle operativo/i.test(x.textContent.trim()));
  const target=detail||original.querySelector('.chart-box')||original.lastElementChild;
  if(!target)return;
  let section=q('.or373-recovery-panel',original);
  if(section&&section.dataset.period===key)return;
  if(section)section.remove();
  const location=document.createElement('div');
  location.className='or373-mount';
  if(detail)detail.before(location);
  else target.before(location);
  // Si el backend ya incluyó una tabla, se reutiliza sin crear una copia.
  if(relocateExisting(original,location)){q('.or373-recovery-panel',location).dataset.period=key;current=key;return;}
  section=makeBox(location);
  current=key;fill(section,filter,key);
 }
 function schedule(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(()=>{queued=false;render()});
 }
 function install(){
  const root=q('#operativoDynamicContent');
  if(root)new MutationObserver(schedule).observe(root,{childList:true,subtree:false});
  ['operPeriodMode','operPeriodSelect','operStoreSelect'].forEach(id=>q('#'+id)?.addEventListener('change',schedule));
  window.addEventListener('or356:center-data',schedule);
  q('#operativoNav')?.addEventListener('click',schedule);
  schedule();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
 else install();
})();