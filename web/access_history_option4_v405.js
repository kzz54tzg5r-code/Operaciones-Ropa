/* V405: Opción 4 de historial de ingresos para Super Administrador.
 * Solo muestra eventos auditados; sin datos inventados. */
(() => {
  'use strict';
  if(window.V405_ACCESS)return;
  const q=(s,r=document)=>r.querySelector(s);
  const fmt=n=>Number(n||0).toLocaleString('es-MX');
  const label={superadmin:'Super Administrador',admin:'Administrador',director:'Director / Consulta',
    tienda:'Tienda',colaborador_lenceria:'Lencería',colaborador_operativo:'Operativo'};
  const events={login_success:'Inicio de sesión',login_failed:'Intento fallido',
    logout:'Cierre de sesión',password_reset:'Contraseña restablecida'};
  const dateTime=raw=>{
    if(!raw)return '—';
    const d=new Date(raw);if(isNaN(d))return String(raw);
    return new Intl.DateTimeFormat('es-MX',{timeZone:'America/Mexico_City',dateStyle:'short',timeStyle:'short'}).format(d);
  };
  const node=(name,className,value)=>{
    const n=document.createElement(name);if(className)n.className=className;
    if(value!==undefined)n.textContent=String(value);
    return n;
  };
  let page=1;
  let querySeq=0;
  const root=()=>q('#v405AccessHistory');
  const filters=()=>({
    period:q('#v405Period',root())?.value||'day',
    reference:q('#v405Reference',root())?.value||'',
    username:q('#v405User',root())?.value||'',
    role:q('#v405Role',root())?.value||'',
    store:q('#v405Store',root())?.value||'',
  });
  const qs=data=>new URLSearchParams(data).toString();
  async function fetchJson(url){
    const r=await fetch(url,{cache:'no-store',credentials:'same-origin'});
    if(!r.ok)throw Error('HTTP '+r.status);
    return r.json();
  }
  function fillSelect(id,rows,defaultLabel,selected){
    const select=q(id,root());if(!select)return;
    select.replaceChildren(new Option(defaultLabel,''));
    for(const key of rows)select.add(new Option(label[key]||key,key));
    if([...select.options].some(o=>o.value===selected))select.value=selected;
  }
  function addBadge(td,event){
    const status=node('span','v405-badge '+(event==='login_success'?'good':event==='login_failed'?'bad':'neutral'),events[event]||event);
    td.append(status);
  }
  function drawTable(selector,rows,columns,emptyText,createRow){
    const body=q(selector,root());if(!body)return;
    body.replaceChildren();
    if(!rows.length){const tr=node('tr');const td=node('td','v405-empty',emptyText);
      td.colSpan=columns;tr.append(td);body.append(tr);return;}
    for(let i=0;i<rows.length;i++){
      const tr=node('tr');createRow(tr,rows[i],i);body.append(tr);
    }
  }
  function render(data){
    if(!root())return;
    const set=(id,val)=>{const x=q(id,root());if(x)x.textContent=val;};
    set('#v405Count',fmt(data.successful));
    set('#v405Unique',fmt(data.unique_users));
    set('#v405Failed',fmt(data.failed));
    set('#v405Closed',fmt(data.closed));
    set('#v405Total',fmt(data.total));
    set('#v405Meta',data.from+' a '+data.to);
    const chosen=filters();
    fillSelect('#v405User',data.filters.users,'Todos los usuarios',chosen.username);
    fillSelect('#v405Role',data.filters.roles,'Todos los roles',chosen.role);
    fillSelect('#v405Store',data.filters.stores,'Todas las tiendas',chosen.store);
    drawTable('#v405RecentRows',data.recent,5,'Aún no hay ingresos registrados.',(tr,r)=>{
      [r.username,label[r.role]||r.role||'—',r.store||'Sin tienda',
       fmt(r.accesses),dateTime(r.latest)].forEach(v=>tr.append(node('td',null,v)));
    });
    drawTable('#v405AlertRows',data.alerts,3,'Sin alertas en el periodo.',(tr,r)=>{
      tr.append(node('td',null,dateTime(r.occurred_at)));
      tr.append(node('td','v405-strong',r.username));
      const td=node('td');addBadge(td,r.event);tr.append(td);
    });
    drawTable('#v405LogRows',data.rows,8,'Sin accesos registrados para estos filtros.',(tr,r,i)=>{
      tr.append(node('td',null,((data.page-1)*data.page_size)+i+1));
      tr.append(node('td','v405-strong',r.username));
      tr.append(node('td',null,label[r.role]||r.role||'—'));
      tr.append(node('td',null,r.store||'Sin tienda'));
      tr.append(node('td',null,dateTime(r.occurred_at)));
      const eventTd=node('td');addBadge(eventTd,r.event);tr.append(eventTd);
      tr.append(node('td',null,r.device||'No disponible'));
      tr.append(node('td',null,r.ip_mask||'No disponible'));
    });
    set('#v405Pagination',`Página ${data.page} de ${data.pages} · ${fmt(data.total)} eventos`);
    q('#v405Back',root()).disabled=data.page<=1;
    q('#v405Next',root()).disabled=data.page>=data.pages;
    set('#v405Note',data.tracking_since);
  }
  async function load(){
    const host=root();if(!host||host.closest('.hidden'))return;
    const id=++querySeq;
    const status=q('#v405Status',host);status.textContent='Consultando accesos…';
    try{
      const data=await fetchJson('/api/admin/access-history-v405?'+qs({...filters(),page,page_size:20}));
      if(id!==querySeq||!host.isConnected)return;
      render(data);status.textContent='Datos actualizados.';
    }catch(e){
      if(id!==querySeq)return;
      status.textContent='No se pudo consultar el historial: '+e.message;
      if(/40[13]/.test(String(e.message)))host.classList.add('hidden');
    }
  }
  async function download(format){
    const button=q(format==='xlsx'?'#v405Excel':'#v405Pdf',root());
    const name=button.textContent;button.disabled=true;button.textContent='Generando…';
    try{
      const response=await fetch('/api/admin/access-history-v405/export?'+qs({...filters(),format}),
        {cache:'no-store',credentials:'same-origin'});
      if(!response.ok)throw Error('HTTP '+response.status);
      const blob=await response.blob();
      const url=URL.createObjectURL(blob);
      const a=node('a');a.href=url;
      a.download='historial_accesos_'+(filters().reference||'actual')+'.'+format;
      document.body.append(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),5000);
    }catch(e){q('#v405Status',root()).textContent='Error al descargar: '+e.message;}
    finally{button.disabled=false;button.textContent=name;}
  }
  function mount(role){
    const host=root();
    if(!host)return;
    const allowed=role==='superadmin';
    host.classList.toggle('hidden',!allowed);
    if(!allowed)return;
    if(host.dataset.installed==='1'){load();return;}
    host.dataset.installed='1';
    host.innerHTML=`
      <div class="v405-title"><div><h2>Historial de ingresos de usuarios</h2>
        <p>Bitácora de actividad · Exclusivo para Super Administrador</p></div>
        <span class="v405-locked">Acceso exclusivo</span></div>
      <div class="v405-filters">
        <label>PERIODO <select id="v405Period"><option value="day">Día</option><option value="week">Semana</option><option value="month">Mes</option></select></label>
        <label>FECHA <input id="v405Reference" type="date"></label>
        <label>USUARIO <select id="v405User"><option value="">Todos</option></select></label>
        <label>ROL <select id="v405Role"><option value="">Todos</option></select></label>
        <label>TIENDA <select id="v405Store"><option value="">Todas</option></select></label>
        <button id="v405Consult" type="button">Consultar</button>
      </div>
      <div class="v405-meta" id="v405Meta"></div>
      <div class="v405-top">
        <section class="v405-panel v405-recent"><header>Usuarios registrados recientemente</header>
          <div class="v405-scroll"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Tienda</th><th>Ingresos</th><th>Último acceso</th></tr></thead><tbody id="v405RecentRows"></tbody></table></div>
        </section>
        <div class="v405-side">
          <section class="v405-panel"><header>Resumen de accesos</header>
            <div class="v405-metrics">
              <article><b id="v405Count">—</b><span>Ingresos exitosos</span></article>
              <article><b id="v405Unique">—</b><span>Usuarios únicos</span></article>
              <article><b id="v405Failed">—</b><span>Intentos fallidos</span></article>
              <article><b id="v405Closed">—</b><span>Sesiones cerradas manualmente</span></article>
            </div>
          </section>
          <section class="v405-panel"><header>Alertas de seguridad</header>
            <div class="v405-scroll"><table><thead><tr><th>Fecha</th><th>Usuario</th><th>Evento</th></tr></thead><tbody id="v405AlertRows"></tbody></table></div>
          </section>
        </div>
      </div>
      <section class="v405-panel v405-log"><header><span>Bitácora completa de accesos</span>
        <div class="v405-exports"><button type="button" id="v405Excel">Exportar Excel</button>
        <button type="button" id="v405Pdf">Exportar PDF</button></div></header>
        <div class="v405-scroll"><table><thead><tr><th>#</th><th>Usuario</th><th>Rol</th><th>Tienda</th><th>Fecha y hora (CDMX)</th><th>Tipo de acceso</th><th>Dispositivo</th><th>IP parcial</th></tr></thead><tbody id="v405LogRows"></tbody></table></div>
        <div class="v405-foot"><span id="v405Pagination"></span><div>
          <button type="button" id="v405Back">Anterior</button><button type="button" id="v405Next">Siguiente</button>
        </div></div>
      </section>
      <p class="v405-caption" id="v405Note"></p>
      <p class="v405-caption" role="status" id="v405Status"></p>
    `;
    q('#v405Consult',host).onclick=()=>{page=1;load();};
    q('#v405Period',host).onchange=()=>{page=1;load();};
    q('#v405Back',host).onclick=()=>{page=Math.max(1,page-1);load();};
    q('#v405Next',host).onclick=()=>{page++;load();};
    q('#v405Excel',host).onclick=()=>download('xlsx');
    q('#v405Pdf',host).onclick=()=>download('pdf');
    load();
  }
  window.V405_ACCESS={mount,refresh:load};
})();