
(()=>{
  if(window.__LAB_SYNC_V240)return; window.__LAB_SYNC_V240=true;
  const q=(s,r=document)=>r.querySelector(s), qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const svg=(d)=>'<span class="sync240-icon" aria-hidden="true">'+d+'</span>';
  const icons={
    center:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    conversion:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h12M12 3l4 4-4 4M20 17H8M12 13l-4 4 4 4"/></svg>',
    money:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M15 8.5c-.7-.7-1.6-1-2.8-1-1.7 0-2.7.8-2.7 2 0 3 5.5 1.2 5.5 4.5 0 1.3-1.1 2.3-3 2.3-1.4 0-2.5-.4-3.2-1.2M12 5.5v13"/></svg>',
    store:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10v9h16v-9M3 10l2-5h14l2 5"/><path d="M8 19v-5h8v5"/></svg>',
    productivity:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></svg>',
    routes:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h5a3 3 0 0 1 0 6h-2a3 3 0 0 0 0 6h5"/></svg>',
    score:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 3 2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z"/></svg>',
    alert:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 2.5 20h19z"/><path d="M12 9v5M12 17h.01"/></svg>',
    summary:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h5"/></svg>',
    daily:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>',
    capture:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 15v5h14v-5"/></svg>',
    standards:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V8l8-4 8 4v12"/><path d="M8 20v-6h8v6M9 9h6"/></svg>'
  };
  function button(tab,label,icon){
    return '<button data-tab="'+tab+'">'+svg(icons[icon]||icons.summary)+'<span>'+label+'</span></button>';
  }
  function buildTabs(host, defs){
    host.innerHTML=defs.map((d,i)=>button(d[0],d[1],d[2])).join('');
    const bs=qa('button',host);
    bs.forEach((b,i)=>b.classList.toggle('active',i===0));
  }
  function bindTabs(report,host){
    qa('button',host).forEach(btn=>btn.addEventListener('click',()=>{
      qa('button',host).forEach(x=>x.classList.toggle('active',x===btn));
      qa('.tab-panel',report).forEach(p=>p.classList.toggle('active',p.id===btn.dataset.tab));
      btn.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'});
    }));
  }
  function ensurePanel(report,id,html){
    let p=document.getElementById(id);
    if(!p){p=document.createElement('div');p.id=id;p.className='tab-panel';p.innerHTML=html;report.appendChild(p)}
    return p;
  }
  function centerUpgrade(){
    const report=q('#cambios'); if(!report)return;
    const tabs=q('.report-tabs',report);
    buildTabs(tabs,[
      ['cy-resumen','Centro Operativo','center'],
      ['cy-conversion','Conversión','conversion'],
      ['cy-recuperacion','Recuperación $','money'],
      ['cy-rec-store','Recuperación por Tienda','store'],
      ['cy-productividad','Productividad','productivity'],
      ['cy-routes','Recorridos','routes'],
      ['cy-score','Score','score'],
      ['cy-alerts','Alertas','alert']
    ]);
    const center=q('#cy-resumen');
    if(center && !q('.sync240-center-modes',center)){
      const modes=document.createElement('div');
      modes.className='sync240-center-modes';
      modes.innerHTML='<button class="active" data-mode="day">Día</button><button data-mode="week">Semanal</button><button data-mode="month">Mensual</button><button data-mode="year">Anual</button>';
      center.prepend(modes);
      const after=document.createElement('div');
      after.className='sync240-center-meta';
      after.innerHTML='<span>Centro Operativo · vista <b id="syncCenterMode">Día</b></span><span>Las vistas Día / Semanal / Mensual / Anual viven aquí y ya no son pestañas separadas.</span>';
      modes.after(after);
      qa('button',modes).forEach(b=>b.addEventListener('click',()=>{
        qa('button',modes).forEach(x=>x.classList.toggle('active',x===b));
        const map={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
        q('#syncCenterMode').textContent=map[b.dataset.mode]||'Día';
      }));
    }
    ensurePanel(report,'cy-rec-store','<div class="section-card"><h3>Recuperación por Tienda</h3><p>Tabla de recuperación disponible para Semanal, Mensual y Anual. La gráfica horizontal fue retirada en la versión actual.</p><div class="tablewrap"><table><thead><tr><th>Tienda</th><th>Dev Pzs</th><th>Recup. Pzs</th><th>Conversión</th><th>Valor devolución</th><th>Venta recuperada</th><th>Recuperación</th></tr></thead><tbody><tr><td colspan="7" class="empty-row">Se alimentará con la copia operativa validada del laboratorio.</td></tr></tbody></table></div></div>');
    ensurePanel(report,'cy-routes','<div class="section-card"><div class="sync240-section-head"><div><h3>Recorridos</h3><p>Calendario por tienda: días en Semanal y semanas ISO en Mensual/Anual.</p></div><span class="pill">V240</span></div><div class="sync240-route-calendar"><table><thead><tr><th>Tienda</th><th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th><th>Sáb</th><th>Dom</th><th>Total</th></tr></thead><tbody id="syncRouteRows"></tbody></table></div><div class="sync240-matrix-title"><b>Matriz de recolección</b><span>10:00–19:00</span></div><div class="sync240-hour-grid" id="syncHourGrid"></div></div>');
    ensurePanel(report,'cy-score','<div class="section-card"><h3>Score integral</h3><div class="formula">40% Conversión <b>+</b> 40% Productividad <b>+</b> 20% Recorridos</div><p class="muted">La estructura queda sincronizada con el reporte actual de Producción.</p></div>');
    ensurePanel(report,'cy-alerts','<div class="section-card"><h3>Alertas</h3><div class="alert-list"><div>○ Seguimiento de pendientes operativos.</div><div>○ Desviaciones de productividad.</div><div>○ Cumplimiento de recorridos.</div><div>○ Diferencias entre ingreso, acondicionado y ubicado.</div></div></div>');
    const storeOld=q('#cy-tiendas'); if(storeOld)storeOld.remove();
    bindTabs(report,tabs);
    const rows=q('#syncRouteRows');
    if(rows && !rows.children.length){
      const stores=['Iztapalapa','Vallejo','Ecatepec','Toluca','Arco Norte','Ixtapaluca','Querétaro','Centro','Olivar','León','Puebla','Puebla Sur','Aguascalientes','Veracruz','Naucalpan','Miravalle','Atemajac'];
      rows.innerHTML=stores.map(s=>'<tr><td><b>'+s+'</b></td>'+Array(8).fill('<td>—</td>').join('')+'</tr>').join('');
    }
    const hg=q('#syncHourGrid');
    if(hg&&!hg.children.length)hg.innerHTML=Array.from({length:10},(_,i)=>'<div><b>'+String(i+10).padStart(2,'0')+':00</b><span>— pzs</span></div>').join('');
  }
  function operationUpgrade(){
    const report=q('#operaciones'); if(!report)return;
    const tabs=q('.report-tabs',report);
    buildTabs(tabs,[
      ['op-resumen','Resumen','summary'],
      ['op-daily','Captura diaria','daily'],
      ['op-capture','Cargar productividad','capture'],
      ['op-productividad','Productividad','productivity'],
      ['op-standards','Estándares Operativos','standards']
    ]);
    ensurePanel(report,'op-daily','<div class="section-card"><h3>Captura diaria</h3><p>Seguimiento diario de Operación con tienda, actividad, área y avance.</p><div class="sync240-empty">La captura real permanece aislada hasta conectar almacenamiento propio del laboratorio.</div></div>');
    ensurePanel(report,'op-capture','<div class="section-card"><div class="sync240-section-head"><div><h3>Cargar productividad</h3><p>Flujo actualizado de Operación.</p></div><span class="pill">V239</span></div><div class="sync240-choice-title">Tipo de operación</div><div class="sync240-choice" id="syncOpType"><button class="active" data-type="origin">Origen</button><button data-type="resupply">Surtido</button></div><div id="syncOrigin"><div class="sync240-choice-title">Actividad</div><div class="sync240-choice"><button class="active">Clasificado</button><button>Acondicionado</button><button>Ubicado</button></div></div><div id="syncResupply" class="hidden"><div class="sync240-choice-title">Motivo surtido</div><div class="sync240-choice"><button class="active">Excedente</button><button>Bodega</button></div><div class="sync240-choice-title">Actividad</div><div class="sync240-choice"><button class="active">Pizca</button><button>Acondicionado</button><button>Ubicado</button></div></div><div class="sync240-area-table"><table><thead><tr><th>Área</th><th>Piezas</th></tr></thead><tbody><tr><td>Colgado</td><td><input type="number" min="0" placeholder="0"></td></tr><tr><td>Doblado</td><td><input type="number" min="0" placeholder="0"></td></tr><tr><td>Jeans</td><td><input type="number" min="0" placeholder="0"></td></tr><tr><td>Lencería</td><td><input type="number" min="0" placeholder="0"></td></tr></tbody></table></div><div class="sync240-capture-actions"><button>Inicio</button><button>Fin</button></div><p class="muted">Demo del flujo actual. No escribe en Producción.</p></div>');
    ensurePanel(report,'op-standards','<div class="section-card"><h3>Estándares Operativos</h3><p>Tres niveles por antigüedad, con rangos administrables.</p><div class="sync240-levels"><article><span>NIVEL 1</span><b>Nuevo</b><small>Ingreso → rango configurable</small></article><article><span>NIVEL 2</span><b>Intermedio</b><small>Rango configurable</small></article><article><span>NIVEL 3</span><b>Experto</b><small>Rango configurable</small></article></div><div class="tablewrap"><table><thead><tr><th>Área</th><th>Nuevo</th><th>Intermedio</th><th>Experto</th><th>Regla</th></tr></thead><tbody><tr><td>Colgado</td><td>—</td><td>—</td><td>—</td><td>Colgado</td></tr><tr><td>Lencería</td><td>—</td><td>—</td><td>—</td><td>Usa estándar Colgado</td></tr><tr><td>Doblado</td><td>—</td><td>—</td><td>—</td><td>Doblado</td></tr><tr><td>Jeans</td><td>—</td><td>—</td><td>—</td><td>Usa estándar Doblado</td></tr></tbody></table></div></div>');
    ['op-ingresos','op-habilitado','op-ubicado','op-recorridos'].forEach(id=>document.getElementById(id)?.remove());
    bindTabs(report,tabs);
    const types=q('#syncOpType');
    if(types)qa('button',types).forEach(btn=>btn.addEventListener('click',()=>{
      qa('button',types).forEach(x=>x.classList.toggle('active',x===btn));
      q('#syncOrigin')?.classList.toggle('hidden',btn.dataset.type!=='origin');
      q('#syncResupply')?.classList.toggle('hidden',btn.dataset.type!=='resupply');
    }));
  }
  function updateHome(){
    const cards=qa('.home-cards article');
    if(cards[0])cards[0].querySelector('p').textContent='Centro Operativo con Día/Semanal/Mensual/Anual, conversión, recuperación, productividad, recorridos, score y alertas.';
    if(cards[1])cards[1].querySelector('p').textContent='Resumen, Captura diaria, Cargar productividad, Productividad y Estándares Operativos.';
    const hero=q('.hero p'); if(hero)hero.textContent='Sincronizado con el avance actual de GitHub/Render (V240), manteniendo este laboratorio totalmente separado de Producción.';
    const current=q('.roadmap .current strong'); if(current)current.textContent='Sincronización con Producción V240';
    const phase=q('#snapshotPhaseText'); if(phase)phase.textContent='Interfaz actualizada al avance de GitHub/Render';
  }
  function usersUpgrade(){
    const report=q('#usuarios'); if(!report)return;
    const note=document.createElement('div');note.className='sync240-notice';note.innerHTML='<b>Sincronización actual</b><span>Incluye administración de pestañas por reporte, ocultar/eliminar/restaurar para Super Administrador y vistas por rol. La geolocalización de Tienda permanece como función de Producción y no se activa en este laboratorio.</span>';
    const heading=q('.report-heading',report); if(heading && !q('.sync240-notice',report))heading.after(note);
  }
  function boot(){centerUpgrade();operationUpgrade();updateHome();usersUpgrade()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
