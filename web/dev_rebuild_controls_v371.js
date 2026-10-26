/* V371: reprocesamiento administrativo del Excel vigente. El servidor controla
   roles, valida resultados y conserva un respaldo antes de publicarlos. */
(() => {
  'use strict';
  if(window.__or371DevUi)return;
  window.__or371DevUi=true;
  const get=id=>document.getElementById(id);
  const api='/api/operations/rebuild-dev-v368';
  let timer=null,processing=false;
  const message=(text,error=false)=>{
    const el=get('or371Status')||get('or371LegacyStatus');
    if(el){el.textContent=text;el.style.color=error?'#b42318':'#234f80'}
  };
  const explain=x=>String(x?.detail||x?.message||x?.error||'Error de conexión');
  async function state(){
    try{
      const response=await fetch(api,{credentials:'same-origin',cache:'no-store'});
      const data=await response.json();
      if(!response.ok)throw Error(explain(data));
      if(data.status==='completed'){
        processing=false;
        clearInterval(timer);timer=null;
        message('DEV publicadas: '+Number(data.previous_dev||0).toLocaleString('es-MX')+
          ' → '+Number(data.rebuilt_dev||0).toLocaleString('es-MX')+
          ' piezas. Vuelve a consultar el reporte.');
        audit();
      }else if(['failed','interrupted'].includes(data.status)){
        processing=false;clearInterval(timer);timer=null;
        message('Base anterior conservada: '+explain(data),true);
      }else{
        processing=['queued','processing','publishing'].includes(data.status);
        message(data.message||'Procesamiento en curso.');
      }
    }catch(error){message('Estado no disponible: '+error.message,true)}
  }
  async function run(month){
    if(processing)return message('Ya existe un reprocesamiento en curso.');
    if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))return message('Selecciona un mes válido.',true);
    processing=true;
    message('Verificando el Excel vigente sin reemplazar la base actual…');
    try{
      const response=await fetch(api,{
        method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({period_type:'month',period_value:month})
      });
      const result=await response.json();
      if(!response.ok)throw Error(explain(result));
      message('Reprocesamiento solicitado para '+month+'. Se verificará antes de publicar.');
      clearInterval(timer);timer=setInterval(state,5000);state();
    }catch(error){processing=false;message('No se inició: '+error.message,true)}
  }
  async function audit(){
    const target=get('or371Audit');
    if(!target)return;
    try{
      const response=await fetch('/api/upload/operations/current',{credentials:'same-origin',cache:'no-store'});
      if(!response.ok)throw Error('sin acceso');
      const records=Object.entries((await response.json()).recovery_header_audit||{});
      target.replaceChildren();
      if(!records.length){target.textContent='Sin auditoría anterior. Reprocesa el Excel vigente para generarla.';return}
      for(const [name,row] of records){
        const div=document.createElement('div');
        const count=Number(row.daily_dates||0);
        div.textContent=name+': '+count+' días ('+(row.first_date||'—')+' a '+(row.last_date||'—')+
          '), DEV diarias '+Number(row.total_daily_dev||0).toLocaleString('es-MX')+
          ', DEV total '+Number(row.total_monthly_dev||0).toLocaleString('es-MX')+
          (row.warnings?.length?' · Revisar: '+row.warnings.join('; '):' · Validado');
        target.append(div);
      }
    }catch(_){target.textContent='Auditoría no disponible en esta sesión.'}
  }
  function render(){
    if(get('operativoDynamicTitle')?.textContent?.trim()!=='Carga de datos')return;
    const buttons=document.querySelector('#operativoDynamicContent .upload-actions');
    if(!buttons||get('or371Tools'))return;
    const panel=document.createElement('section');
    panel.id='or371Tools';
    panel.style.cssText='margin:9px 0;padding:9px;border:1px solid #d5e5f6;border-radius:8px;background:white';
    panel.innerHTML='<b style="font-size:12px">Reprocesar DEV del Excel vigente</b>'+
      '<div style="display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:8px 0">'+
      '<label for="or371Month">Mes</label><input id="or371Month" type="month" style="padding:6px;min-width:145px">'+
      '<button type="button" id="or371Run" class="primary">Verificar y actualizar DEV</button>'+
      '<button type="button" id="or371Check">Consultar estado</button></div>'+
      '<div class="note" id="or371Status" role="status">Se conserva la base anterior hasta validar el resultado.</div>'+
      '<div class="note" style="margin-top:5px">Auditoría de fechas, columnas y DEV</div>'+
      '<div id="or371Audit" style="font-size:10px;line-height:1.5;overflow-wrap:anywhere"></div>';
    buttons.after(panel);
    const d=new Date();
    get('or371Month').value=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');
    get('or371Run').addEventListener('click',()=>run(get('or371Month').value));
    get('or371Check').addEventListener('click',state);
    audit();
  }
  document.addEventListener('click',event=>{
    const button=event.target.closest('#v368RebuildButton');
    if(!button)return;
    event.preventDefault();
    if(!get('or371LegacyStatus')){
      const el=document.createElement('div');el.id='or371LegacyStatus';
      el.setAttribute('role','status');button.after(el);
    }
    const value=get('operPeriodSelect')?.value||'';
    const d=new Date();
    run(/^\d{4}-\d{2}/.test(value)?value.slice(0,7):
      d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0'));
  });
  function init(){
    const host=get('operativoDynamicContent');
    if(!host)return;
    new MutationObserver(render).observe(host,{childList:true,subtree:false});
    render();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();