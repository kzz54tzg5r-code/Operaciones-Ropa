/* V357 — Gestión autorizada de capturas C&M en el ranking digital.
 * Los permisos se validan SIEMPRE en el endpoint; esta vista sólo ofrece selección. */
(() => {
 'use strict';
 const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=x=>Number(x||0).toLocaleString('es-MX',{maximumFractionDigits:0});
 const chosen=()=>document.querySelector('#operativoDynamicContent .or357-delete-toolbar');
 window.OR_CM_MANAGE=function(report){
   const host=document.getElementById('operativoDynamicContent');
   if(!host||!host.querySelector('.v199-digital-badge'))return;
   let role='';
   try{role=String(USER?.role||'').toLowerCase()}catch(_){}
   if(!['admin','superadmin'].includes(role))return;
   const items=(report?.items||[]).filter(x=>x.status==='finished'&&Number.isSafeInteger(Number(x.id))&&Number(x.id)>0);
   host.querySelector('.or357-delete-toolbar')?.remove();
   const section=document.createElement('section');
   section.className='or357-delete-toolbar';
   section.innerHTML='<div class="or357-title"><div><h3>Administrar capturas digitales</h3>'+
    '<p>Selecciona registros individuales. No afecta archivos Excel ni registros en curso.</p></div>'+
    '<div class="or357-actions"><span class="or357-count" aria-live="polite">0 seleccionados</span>'+
    '<button type="button" class="or357-delete" disabled>Eliminar seleccionados</button></div></div>'+
    '<div class="or357-scroll"><table class="or357-table"><thead><tr>'+
    '<th><input type="checkbox" class="or357-all" aria-label="Seleccionar todas las capturas visibles"></th>'+
    '<th>Fecha</th><th>Colaborador</th><th>Tienda</th><th>Actividad</th><th>Piezas</th><th>Tiempo</th></tr></thead><tbody>'+
    (items.length?items.map(x=>'<tr><td><input type="checkbox" class="or357-choice" value="'+Number(x.id)+'" aria-label="Seleccionar captura '+Number(x.id)+' de '+esc(x.employee_name)+'"></td>'+
      '<td>'+esc(x.date)+'</td><td>'+esc(x.employee_name)+'</td><td>'+esc(x.store)+'</td>'+
      '<td>'+esc(x.activity)+'</td><td>'+fmt(x.pieces)+'</td><td>'+esc(x.duration_seconds?Math.floor(Number(x.duration_seconds)/60)+' min':'—')+'</td></tr>').join('')
      :'<tr><td colspan="7">No hay capturas individuales finalizadas para eliminar.</td></tr>')+
    '</tbody></table></div><p class="or357-note" role="status"></p>';
   host.append(section);
   const checks=[...section.querySelectorAll('.or357-choice')];
   const all=section.querySelector('.or357-all'),del=section.querySelector('.or357-delete');
   const count=section.querySelector('.or357-count'),note=section.querySelector('.or357-note');
   if(!checks.length)all.disabled=true;
   function update(){
     const selected=checks.filter(c=>c.checked);
     count.textContent=selected.length+' seleccionados';
     del.disabled=!selected.length;
     all.checked=!!checks.length&&selected.length===checks.length;
     all.indeterminate=!!selected.length&&selected.length!==checks.length;
   }
   checks.forEach(c=>c.addEventListener('change',update));
   all.addEventListener('change',()=>{checks.forEach(c=>c.checked=all.checked);update()});
   del.addEventListener('click',async()=>{
     const ids=checks.filter(c=>c.checked).map(c=>Number(c.value));
     if(!ids.length||ids.length>50)return;
     const target=checks.filter(c=>c.checked).slice(0,3).map(c=>c.closest('tr')?.cells[2]?.textContent||'').join(', ');
     if(!window.confirm('¿Eliminar '+ids.length+' captura(s) de productividad?\n\n'+target+
       (ids.length>3?'…':'')+'\n\nEl ranking se recalculará. La baja queda auditada.'))return;
     del.disabled=true;all.disabled=true;checks.forEach(c=>c.disabled=true);
     note.textContent='Eliminando registros seleccionados…';
     try{
       let result;
       const options={method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids}),credentials:'same-origin'};
       if(typeof api==='function')result=await api('/api/cm-productivity/delete-selected',options);
       else{
         const response=await fetch('/api/cm-productivity/delete-selected',options);
         result=await response.json();
         if(!response.ok)throw Error(result.detail||'No fue posible eliminar');
       }
       if(!result?.ok)throw Error('La operación no se confirmó');
       note.textContent=result.message||'Registros eliminados.';
       if(typeof window.renderOperativoView==='function')await window.renderOperativoView('Productividad por Colaborador',true);
     }catch(e){
       note.textContent='No se eliminó la selección: '+String(e?.message||e);
       all.disabled=!checks.length;checks.forEach(c=>c.disabled=false);
       update();
     }
   });
 };
})();
