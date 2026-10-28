/* V400 · Panel plegable como "Reporte completo por tienda", sin alterar KPIs. */
(() => {
  'use strict';
  if (window.__or400Missing) return;
  window.__or400Missing = true;
  const $ = s => document.querySelector(s);
  const fmt = n => new Intl.NumberFormat('es-MX',{maximumFractionDigits:0}).format(Number(n)||0);
  const el = (tag,cls,text) => {
    const node = document.createElement(tag);
    if(cls) node.className=cls;
    if(text!==undefined) node.textContent=String(text);
    return node;
  };
  const isCenter = () => !!$('#page-operativo.active') &&
    !$('#appView')?.classList.contains('hidden') &&
    !!$('#operativoNav [data-opview="Centro Ejecutivo"].active');
  const selection = () => ({
    period_type:$('#operPeriodMode')?.value||'day',
    period_value:$('#operPeriodSelect')?.value||'',
    store:$('#operStoreSelect')?.value||'Compañía'
  });
  const url = (path,args) => path+'?'+new URLSearchParams(args).toString();
  let userOpened=false;
  let requestIndex=0;

  function table(data,host) {
    host.replaceChildren();
    const rows=Array.isArray(data.rows)?data.rows:[];
    const caption=el('div','or400-note','Padrón activo del proyecto. Sin captura no significa inasistencia; validar turnos y asistencia con cada tienda.');
    host.append(caption);
    if(!rows.length){
      host.append(el('div','or400-empty','Sin colaboradores activos pendientes de captura para los filtros seleccionados.'));
      return;
    }
    const scroll=el('div','or400-table-scroll');
    const grid=el('table','or400-table');
    const head=el('thead'),hrow=el('tr');
    ['#','Colaborador','Tienda','Perfil / actividad','Último registro','Días sin captura','Estatus']
      .forEach(label=>hrow.append(el('th',null,label)));
    head.append(hrow);grid.append(head);
    const body=el('tbody');
    rows.forEach((row,i)=>{
      const line=el('tr');
      const values=[i+1,row.name||'—',row.store||'—',row.profile||'—',
          row.last_date||'Sin registro',fmt(row.days_without_record),
          row.status||'Sin captura'];
      values.forEach((v,j)=>{
        const cell=el('td',j===1?'or400-person':j===6?'or400-status':'',v);
        if(j===6){const dot=el('span','or400-dot');cell.prepend(dot);}
        line.append(cell);
      });
      body.append(line);
    });
    grid.append(body);scroll.append(grid);host.append(scroll);
  }

  async function load(section,force=false){
    if(!section?.isConnected || !isCenter() || !section.open)return;
    const data=selection();
    const key=JSON.stringify(data);
    if(!force && section.dataset.loadedKey===key)return;
    const token=++requestIndex;
    const body=section.querySelector('.or400-body');
    body.replaceChildren(el('div','or400-empty','Consultando padrón activo y registros de productividad…'));
    const header=section.querySelector('.or400-summary');
    header.querySelector('.or400-count').textContent='— colaboradores';
    header.querySelector('.or400-stores').textContent='— tiendas';
    try{
      const resp=await fetch(url('/api/operations/without-productivity-v400',data),
         {credentials:'same-origin',cache:'no-store'});
      if(!resp.ok)throw new Error('Error '+resp.status);
      const result=await resp.json();
      if(token!==requestIndex || !section.isConnected || !section.open)return;
      section.dataset.loadedKey=key;
      header.querySelector('.or400-count').textContent=fmt(result.count)+' colaboradores';
      header.querySelector('.or400-stores').textContent=fmt(result.store_count)+' tiendas';
      table(result,body);
    }catch(error){
      if(token!==requestIndex || !section.isConnected)return;
      body.replaceChildren(el('div','or400-empty','No se pudieron consultar colaboradores: '+(error.message||error)));
    }
  }

  function mount(){
    if(!isCenter())return;
    const full=$('#operativoDynamicContent .ocl-full');
    if(!full || !full.parentElement)return;
    if(full.parentElement.querySelector(':scope > #or400WithoutProductivity'))return;
    const details=el('details','or400-section');
    details.id='or400WithoutProductivity';
    const summary=el('summary','or400-summary');
    const left=el('span','or400-title','Colaboradores sin productividad');
    const counters=el('span','or400-counters');
    counters.append(el('span','or400-count','— colaboradores'),
      el('span','or400-stores','— tiendas'));
    summary.append(left,counters);
    const panel=el('div','or400-panel');
    const head=el('div','or400-head');
    const info=el('div');
    info.append(el('h3',null,'Colaboradores sin productividad'),
      el('p',null,'Personas activas sin captura productiva en el periodo y tiendas del proyecto.'));
    const actions=el('div','or400-actions');
    const exportButton=el('button','or400-export','↓ Exportar Excel');
    exportButton.type='button';
    exportButton.addEventListener('click',async event=>{
      event.preventDefault();event.stopPropagation();
      if(exportButton.disabled)return;
      const old=exportButton.textContent;
      exportButton.disabled=true;exportButton.textContent='Preparando Excel…';
      try{
        const response=await fetch(url('/api/export/operations/without-productivity-v400',selection()),
          {credentials:'same-origin'});
        if(!response.ok)throw new Error('Error '+response.status);
        const blob=await response.blob();
        const objectUrl=URL.createObjectURL(blob);
        const link=el('a');link.href=objectUrl;
        link.download='colaboradores_sin_productividad_'+(selection().period_value||'consulta')+'.xlsx';
        document.body.append(link);link.click();link.remove();
        setTimeout(()=>URL.revokeObjectURL(objectUrl),3000);
      }catch(e){alert('No fue posible exportar: '+(e.message||e));}
      finally{exportButton.disabled=false;exportButton.textContent=old;}
    });
    actions.append(exportButton);
    head.append(info,actions);
    panel.append(head,el('div','or400-body','Abre el apartado para consultar los registros.'));
    details.append(summary,panel);
    full.after(details);
    details.open=userOpened;
    details.addEventListener('toggle',()=>{
      userOpened=details.open;
      if(details.open)load(details);
    });
    if(details.open)load(details);
  }

  let queued=false;
  const schedule=()=>{
    if(queued)return;
    queued=true;
    requestAnimationFrame(()=>{queued=false;mount();});
  };
  const init=()=>{
    const root=$('#operativoDynamicContent');
    if(root) new MutationObserver(schedule).observe(root,{childList:true,subtree:true});
    const nav=$('#operativoNav');
    if(nav)new MutationObserver(schedule).observe(nav,{subtree:true,attributes:true,attributeFilter:['class']});
    ['operPeriodApply','centerLaneRefresh'].forEach(id=>
      document.addEventListener('click',e=>{
        if(e.target.closest('#'+id)){
          const section=$('#or400WithoutProductivity');
          if(section?.open) setTimeout(()=>load(section,true),350);
        }
      },true)
    );
    ['operPeriodMode','operPeriodSelect','operStoreSelect'].forEach(id=>{
      document.addEventListener('change',e=>{
        if(e.target?.id!==id)return;
        const section=$('#or400WithoutProductivity');
        if(section?.open)setTimeout(()=>load(section,true),220);
      });
    });
    schedule();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
