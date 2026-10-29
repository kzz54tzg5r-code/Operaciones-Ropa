/* V402: Administración de colaboradores en Metas y tiendas.
   Padrón real, bajas/reactivaciones múltiples, alias entre nombres de una tienda.
   No modifica cuentas de inicio de sesión ni productividad histórica. */
(() => {
  'use strict';
  if (window.V402_ROSTER) return;
  const $ = (s,root=document)=>root.querySelector(s);
  const text = (tag,cls,val) => {
    const e=document.createElement(tag);
    if(cls)e.className=cls;
    if(val!==undefined)e.textContent=String(val);
    return e;
  };
  const keyOf = r=>JSON.stringify([r.store,r.name_key]);
  let records=[],selection=new Set(),inflight=false,loaded=false,root=null;
  const match = r=>selection.has(keyOf(r));
  async function request(path,options={}){
    const resp=await fetch(path,{credentials:'same-origin',cache:'no-store',...options});
    let body={};try{body=await resp.json()}catch(_){}
    if(!resp.ok)throw new Error(body.detail||body.message||('Error HTTP '+resp.status));
    return body;
  }
  const toast = (msg,error=false) => {
    const e=$('#v402Message',root);
    if(!e)return;
    e.textContent=msg;e.style.color=error?'#b42318':'#087954';
  };
  function selectedRecords(){return records.filter(match)}
  const selectedStore = ()=>$('#v402Store',root)?.value||'Compañía';
  function renderTable(){
    if(!root?.isConnected)return;
    const currentStore=selectedStore();
    const keyword=($('#v402Search',root)?.value||'').trim().toLocaleLowerCase('es-MX');
    const status=$('#v402Status',root)?.value||'Todos';
    const filtered=records.filter(r=>
      (currentStore==='Compañía'||r.store===currentStore) &&
      (status==='Todos'||(status==='Activos'?!!r.active:!r.active)) &&
      (r.name+' '+r.store+' '+(r.aliases||[]).join(' ')).toLocaleLowerCase('es-MX').includes(keyword)
    );
    const body=$('#v402Rows',root);if(!body)return;
    body.replaceChildren();
    const selectedVisible=filtered.filter(match).length;
    const all=$('#v402All',root);
    if(all){all.checked=filtered.length>0&&selectedVisible===filtered.length;all.indeterminate=selectedVisible>0&&!all.checked;}
    filtered.forEach(r=>{
      const tr=text('tr');
      const cb=text('input');cb.type='checkbox';cb.checked=match(r);
      cb.setAttribute('aria-label','Seleccionar '+r.name+' de '+r.store);
      cb.addEventListener('change',()=>{
        if(cb.checked)selection.add(keyOf(r));
        else selection.delete(keyOf(r));
        renderTable();
      });
      const first=text('td');first.append(cb);tr.append(first);
      const name=text('td','v402-name',r.name);tr.append(name);
      tr.append(text('td',null,r.store));
      const state=text('td',r.active?'v402-active':'v402-inactive',r.active?'Activo':'Baja');
      tr.append(state);
      const alias=text('td',null,(r.aliases||[]).join(', ')||'—');
      alias.title=(r.aliases||[]).join(', ');tr.append(alias);
      tr.append(text('td',null,r.last_seen||'Sin registro'));
      tr.append(text('td',null,r.updated_by||'—'));
      body.append(tr);
    });
    if(!filtered.length){
      const tr=text('tr'),td=text('td','v402-empty','No hay colaboradores para los filtros seleccionados.');
      td.colSpan=7;tr.append(td);body.append(tr);
    }
    const selected=selectedRecords(),sameStore=selected.length>1&&
      selected.every(r=>r.store===selected[0].store);
    $('#v402Selected',root).textContent=selected.length+' seleccionados';
    $('#v402Deactivate',root).disabled=selected.length===0||inflight;
    $('#v402Reactivate',root).disabled=selected.length===0||inflight;
    $('#v402Merge',root).disabled=!sameStore||inflight;
    const canonical=$('#v402Canonical',root), prior=canonical.value;
    canonical.replaceChildren(new Option('Nombre principal…',''));
    if(sameStore)selected.forEach(r=>canonical.add(new Option(r.name+' · '+r.store,keyOf(r))));
    canonical.value=selected.some(r=>keyOf(r)===prior)?prior:'';
    canonical.disabled=!sameStore||inflight;
    $('#v402MergeTip',root).textContent=sameStore
      ?'Selecciona el nombre principal que conservarás. Los demás serán alias.'
      :'Para unificar, selecciona al menos dos nombres de la misma tienda.';
    $('#v402Total',root).textContent=records.filter(r=>r.active).length+' activos · '+
      records.filter(r=>!r.active).length+' bajas · '+records.reduce((n,r)=>n+(r.aliases||[]).length,0)+' alias';
  }
  function markBusy(value){
    inflight=value;
    renderTable();
  }
  async function refresh(forceSync=false){
    if(!root?.isConnected)return;
    const filter=selectedStore();
    try {
      if(forceSync)await request('/api/operations/collaborators-v166?store=Compa%C3%B1%C3%ADa&include_inactive=true');
      const d=await request('/api/operations/collaborator-admin-v402');
      records=Array.isArray(d.rows)?d.rows:[];
      selection.clear();
      const store=$('#v402Store',root);
      const oldValue=store.value;
      store.replaceChildren(new Option('Compañía','Compañía'));
      [...new Set(records.map(r=>r.store))].sort((a,b)=>a.localeCompare(b,'es-MX'))
        .forEach(name=>store.add(new Option(name,name)));
      store.value=[...store.options].some(o=>o.value===oldValue)?oldValue:filter;
      if(!store.value)store.value='Compañía';
      loaded=true;
      renderTable();
      toast('Padrón actualizado. Se conservará el histórico de las bajas y de los alias.');
    }catch(e){toast('No se pudo leer el padrón: '+(e.message||e),true);}
  }
  async function updateStatus(active){
    const chosen=selectedRecords();
    if(!chosen.length||inflight)return;
    const action=active?'reactivar':'dar de baja';
    if(!confirm('¿Deseas '+action+' '+chosen.length+' colaborador(es)?\n' +
      (active?'Volverán a considerarse para reportes sin productividad.':
      'Dejarán de aparecer en colaboradores sin productividad. No se eliminarán sus capturas.')))return;
    try{
      markBusy(true);
      const d=await request('/api/operations/collaborator-admin-v402/status',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({active,items:chosen.map(r=>({store:r.store,name_key:r.name_key}))})
      });
      await refresh();
      toast(d.message||'Estatus actualizado.');
    }catch(e){toast('No se guardaron los cambios: '+(e.message||e),true);}
    finally{markBusy(false);}
  }
  async function merge(){
    const chosen=selectedRecords(),code=$('#v402Canonical',root)?.value||'';
    if(chosen.length<2||!code||inflight)return toast('Selecciona varios nombres y uno principal.',true);
    const primary=chosen.find(r=>keyOf(r)===code);
    if(!primary||chosen.some(r=>r.store!==primary.store))
      return toast('Sólo se pueden unificar nombres de la misma tienda.',true);
    const aliases=chosen.filter(r=>r!==primary);
    if(!confirm('Unificar en '+primary.store+'\n\nNombre principal: '+primary.name+
      '\nVariantes: '+aliases.map(r=>r.name).join(', ')+
      '\n\n¿Confirmar? Se conserva el histórico; el estatus de '+primary.name+' no cambia.'))return;
    try{
      markBusy(true);
      const d=await request('/api/operations/collaborator-admin-v402/merge',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          store:primary.store,canonical_key:primary.name_key,
          alias_keys:aliases.map(r=>r.name_key)
        })
      });
      await refresh();
      toast(d.message||'Nombres unificados.');
    }catch(e){toast('No se pudo unificar: '+(e.message||e),true);}
    finally{markBusy(false);}
  }
  function mount(){
    const node=$('#v402RosterManagement');
    if(!node)return;
    if(root===node&&loaded)return;
    root=node;loaded=false;selection.clear();
    node.innerHTML=`
      <div class="v402-head">
        <div><div class="title">Colaboradores · altas, bajas y nombres unificados</div>
          <p>Selecciona colaboradores dados de baja para excluirlos de «Sin productividad». Unifica nombres duplicados sin borrar sus capturas. Estos cambios no desactivan cuentas de acceso.</p>
        </div><span id="v402Total">Consultando…</span>
      </div>
      <div class="v402-filters">
        <label>Tienda <select id="v402Store"><option>Compañía</option></select></label>
        <label>Estatus <select id="v402Status"><option>Todos</option><option>Activos</option><option>Bajas</option></select></label>
        <label class="v402-search">Buscar colaborador <input id="v402Search" placeholder="Nombre o variante"></label>
        <button type="button" id="v402Refresh">Actualizar padrón</button>
      </div>
      <div class="v402-actions">
        <b id="v402Selected">0 seleccionados</b>
        <button type="button" id="v402Deactivate" disabled>Dar de baja seleccionados</button>
        <button type="button" id="v402Reactivate" disabled>Reactivar seleccionados</button>
      </div>
      <div class="v402-table-scroll"><table><thead><tr>
        <th><input type="checkbox" id="v402All" aria-label="Seleccionar filas visibles"></th>
        <th>Colaborador</th><th>Tienda</th><th>Estatus</th>
        <th>Nombres unificados</th><th>Última actividad</th><th>Actualizado por</th>
      </tr></thead><tbody id="v402Rows"><tr><td colspan="7">Cargando padrón...</td></tr></tbody></table></div>
      <div class="v402-merge"><label>Nombre principal que se conserva
         <select id="v402Canonical" disabled><option value="">Nombre principal…</option></select></label>
         <button type="button" id="v402Merge" disabled>Unificar nombres seleccionados</button>
         <small id="v402MergeTip">Selecciona dos nombres de la misma tienda.</small>
      </div>
      <p id="v402Message" role="status" aria-live="polite"></p>
    `;
    $('#v402Store',node).onchange=renderTable;
    $('#v402Status',node).onchange=renderTable;
    $('#v402Search',node).oninput=renderTable;
    $('#v402Refresh',node).onclick=()=>refresh(true);
    $('#v402Deactivate',node).onclick=()=>updateStatus(false);
    $('#v402Reactivate',node).onclick=()=>updateStatus(true);
    $('#v402Merge',node).onclick=merge;
    $('#v402All',node).onchange=e=>{
      const store=selectedStore(),status=$('#v402Status',node).value;
      const search=$('#v402Search',node).value.toLocaleLowerCase('es-MX').trim();
      records.filter(r=>(store==='Compañía'||r.store===store)&&
        (status==='Todos'||(status==='Activos'?!!r.active:!r.active))&&
        (r.name+' '+r.store+' '+(r.aliases||[]).join(' ')).toLocaleLowerCase('es-MX').includes(search)
      ).forEach(r=>e.target.checked?selection.add(keyOf(r)):selection.delete(keyOf(r)));
      renderTable();
    };
    refresh(true);
  }
  window.V402_ROSTER={mount};
})();
