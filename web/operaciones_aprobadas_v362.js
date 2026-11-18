/* V362: implementaciones de presentación aprobadas.
   Sin nuevas mutaciones de datos ni cambios de endpoints; mantiene listeners originales. */
(() => {
 'use strict';
 if(window.__or362Installed)return;
 window.__or362Installed=true;
 const APPROVED=new Set(['operations.center','operations.conversion','operations.recovery','operations.recovery_store','operations.recovery_audit','operations.productivity','operations.productivity_capture','operations.routes','operations.upload','operations.goals']);
 const q=(s,root=document)=>root.querySelector(s);
 const qa=(s,root=document)=>[...root.querySelectorAll(s)];
 const mk=(tag,cls,txt)=>{
  const e=document.createElement(tag);
  if(cls)e.className=cls;
  if(txt!==undefined)e.textContent=String(txt);
  return e;
 };
 const numeric=x=>{
  if(x===null||x===undefined||x==='')return 0;
  const n=Number(String(x).replace(/,/g,''));
  return Number.isFinite(n)?n:0;
 };
 const fmt=n=>new Intl.NumberFormat('es-MX',{maximumFractionDigits:0}).format(numeric(n));
 const visibleView=()=>{
  if(!q('#page-operativo.active')||q('#appView')?.classList.contains('hidden'))return '';
  const b=q('#operativoNav [data-opview].active');
  const key=String(b?.dataset.tabKey||'');
  if(key)return key;
  const name=String(b?.dataset.opview||'');
  return name==='Carga de datos'?'operations.upload':name==='Metas y tiendas'?'operations.goals':
   name==='Cargar productividad'?'operations.productivity_capture':'';
 };
 function setView(){
  const key=visibleView();
  if(APPROVED.has(key))document.body.dataset.or362View=key;
  else delete document.body.dataset.or362View;
  const host=q('#operativoDynamicContent');
  if(key==='operations.goals'&&host)decorateGoals(host);
  // V364 · Productividad opción 1: ranking a todo lo ancho, sin panel lateral de tiendas.
  // El reporte original y los controles de eliminación auditada siguen intactos.
  // No envolver la tabla en el layout opción 4.

 }
 let scheduled=false;
 function schedule(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;setView();});
 }
 function decorateGoals(host){
  if(!q('tr[data-store-id]',host))return;
  const rows=qa('tr[data-store-id]',host);
  let toolbar=q('.or362-goals-toolbar',host);
  if(!toolbar){
   toolbar=mk('div','or362-goals-toolbar');
   const search=mk('label',null,'Buscar tienda');
   const input=mk('input');input.type='search';input.placeholder='Nombre de tienda';input.id='or362GoalsSearch';
   search.append(input);
   const status=mk('label',null,'Estatus / proyecto');
   const select=mk('select');select.id='or362GoalsStatus';
   [['all','Todas las tiendas'],['active','Activas'],['inactive','Inactivas'],['project','Tiendas Proyecto']].forEach(([value,label])=>{
    const opt=mk('option',null,label);opt.value=value;select.append(opt);
   });
   status.append(select);
   const reset=mk('button',null,'Restablecer filtros');reset.type='button';
   toolbar.append(search,status,reset);
   const first=host.firstElementChild;host.insertBefore(toolbar,first);
   function filter(){
    const term=(input.value||'').trim().toLocaleLowerCase('es-MX'),scope=select.value;
    qa('tr[data-store-id]',host).forEach(row=>{
     const name=q('.storeNameEdit',row)?.value||'';
     const active=q('.storeActiveEdit',row)?.checked;
     const project=q('.storeProjectEdit',row)?.checked;
     row.hidden=!(name.toLocaleLowerCase('es-MX').includes(term)&&(
      scope==='all'||(scope==='active'&&active)||(scope==='inactive'&&!active)||
      (scope==='project'&&project)
     ));
    });
   }
   input.addEventListener('input',filter);
   select.addEventListener('change',filter);
   reset.addEventListener('click',()=>{input.value='';select.value='all';filter()});
  }
  let stats=q('.or362-goals-kpis',host);
  if(!stats){
   stats=mk('div','or362-goals-kpis');
   const labels=['Tiendas registradas','Tiendas activas','Tiendas Proyecto','Metas configuradas'];
   labels.forEach(t=>{const card=mk('div');card.append(mk('small',null,t),mk('b',null,'0'));stats.append(card)});
   toolbar.after(stats);
  }
  const counts=[
   rows.length,
   rows.filter(x=>q('.storeActiveEdit',x)?.checked).length,
   rows.filter(x=>q('.storeProjectEdit',x)?.checked).length,
   qa('.goalInput',host).length
  ];
  qa('.or362-goals-kpis b',stats).forEach((node,i)=>{
   if(node.textContent!==String(counts[i]))node.textContent=String(counts[i]);
  });
 }
 // Opción Productividad 4: resumen REAL por tienda, ranking REAL por colaborador.
 // En capturas digitales utiliza report.productivity; para Excel usa la tabla
 // ya presentada por el motor original y no reinterpreta ningún cálculo.
 let lastProductivityReport=null;
 function collectReportRows(host){
  if(!q('.v199-digital-badge',host))lastProductivityReport=null;
  if(lastProductivityReport?.length)return lastProductivityReport;
  const t=qa('.tablewrap table',host).find(table=>{
   const labels=qa('thead th',table).map(x=>x.textContent.trim().toLocaleLowerCase('es-MX'));
   return labels.some(x=>x.includes('colaborador'))&&labels.some(x=>x.includes('tienda'))&&labels.some(x=>x.includes('piezas'));
  });
  if(!t)return [];
  const heads=qa('thead th',t).map(x=>x.textContent.trim().toLocaleLowerCase('es-MX'));
  const ix=term=>heads.findIndex(x=>x.includes(term));
  const storeIndex=ix('tienda'),piecesIndex=ix('piezas'),collabIndex=ix('colaborador');
  if(storeIndex<0||piecesIndex<0||collabIndex<0)return [];
  return qa('tbody tr',t).map(tr=>{
   const cells=qa('td',tr),store=cells[storeIndex]?.textContent.trim();
   return {store,pieces:numeric(cells[piecesIndex]?.textContent),name:cells[collabIndex]?.textContent.trim()};
  }).filter(r=>r.store&&r.name);
 }
 function decorateProductivity(host){
  if(q('.or362-productivity-layout',host))return;
  const wrap=qa('.tablewrap',host).find(x=>{
   const headings=qa('thead th',x).map(z=>z.textContent.trim().toLocaleLowerCase('es-MX'));
   return headings.some(s=>s.includes('colaborador'))&&headings.some(s=>s.includes('tienda'));
  });
  if(!wrap)return;
  const rows=collectReportRows(host);
  if(!rows.length)return;
  const summary=new Map();
  rows.forEach(r=>{
   const key=r.store;
   const obj=summary.get(key)||{store:key,pieces:0,collaborators:new Set()};
   obj.pieces+=numeric(r.pieces);
   obj.collaborators.add(r.name);
   summary.set(key,obj);
  });
  const records=[...summary.values()].sort((a,b)=>b.pieces-a.pieces);
  const layout=mk('div','or362-productivity-layout'),left=mk('section','or362-prod-stores'),right=mk('section','or362-prod-collaborators');
  left.append(mk('h3',null,'Resumen por tienda'));
  right.append(mk('h3',null,'Detalle de colaboradores'));
  const showStore=name=>{
   const table=q('table',wrap);
   if(!table)return;
   const header=qa('thead th',table).map(th=>th.textContent.trim().toLocaleLowerCase('es-MX'));
   const idx=header.findIndex(x=>x.includes('tienda'));
   qa('tbody tr',table).forEach(tr=>{
    const cells=qa('td',tr);
    tr.hidden=!!name && String(cells[idx]?.textContent||'').trim()!==name;
   });
   qa('.or362-prod-store-btn',left).forEach(btn=>{
    btn.classList.toggle('active',btn.dataset.store===name);
    btn.setAttribute('aria-pressed',btn.dataset.store===name?'true':'false');
   });
  };
  const allButton=mk('button','or362-prod-store-btn','Todas las tiendas');
  allButton.type='button';allButton.dataset.store='';allButton.addEventListener('click',()=>showStore(''));left.append(allButton);
  records.forEach(row=>{
   const b=mk('button','or362-prod-store-btn');
   b.type='button';b.dataset.store=row.store;
   b.append(mk('span',null,row.store+' · '+row.collaborators.size+' colab.'),mk('b',null,fmt(row.pieces)+' pzas'));
   b.addEventListener('click',()=>showStore(row.store));
   left.append(b);
  });
  const title=wrap.previousElementSibling;
  const storeTitle=title?.classList.contains('title')?title:null;
  wrap.before(layout);layout.append(left,right);
  if(storeTitle)storeTitle.remove();
  right.append(wrap);
  showStore('');
 }
 window.OR362_PRODUCTIVITY_LAYOUT=rep=>{
  // La captura digital ya consolida la productividad por colaborador.
  lastProductivityReport=Array.isArray(rep?.productivity)?rep.productivity.map(r=>({
   name:String(r.name||''),store:String(r.store||''),pieces:numeric(r.pieces)
  })).filter(r=>r.name&&r.store):null;
  const host=q('#operativoDynamicContent');
  // Se mantienen los datos del reporte, sin reestructurar el ranking de la opción 1.
 };
 // Recorridos opción 1: convertir las series devueltas por la API en tablas
 // con sus cifras reales y conservar cuatro tarjetas existentes.
 window.OR362_ENHANCE_REPORT=(name,report)=>{
  if(name!=='Cumplimiento de Recorridos')return;
  const host=q('#operativoDynamicContent');if(!host||!report)return;
  if(q('.or362-routes-detail',host))return;
  const stores=Array.isArray(report.stores)?report.stores.filter(r=>r&&r.store):[];
  const days=Array.isArray(report.daily_peaks)?report.daily_peaks.filter(r=>r&&r.date):[];
  const create=(title,headers,rows)=>{
   const section=mk('section','or362-routes-table');
   section.append(mk('h3',null,title));
   const wrapper=mk('div','tablewrap'),table=mk('table','table');
   const head=mk('thead'),tr=mk('tr');
   headers.forEach(t=>tr.append(mk('th',null,t)));head.append(tr);table.append(head);
   const tbody=mk('tbody');
   if(rows.length)rows.forEach(row=>{
    const line=mk('tr');row.forEach(v=>line.append(mk('td',null,v)));tbody.append(line);
   });
   else{const tr=mk('tr'),cell=mk('td',null,'Sin registros para este periodo');cell.colSpan=headers.length;tr.append(cell);tbody.append(tr);}
   table.append(tbody);wrapper.append(table);section.append(wrapper);return section;
  };
  const container=mk('div','or362-routes-detail');
  container.append(create('Recorridos por tienda',['Tienda','Recorridos realizados'],stores.map(r=>[
   String(r.store),fmt(r.recorridos)
  ])));
  container.append(create('Recorridos por día',['Fecha','Recorridos realizados','Piezas recolectadas'],days.map(r=>[
   String(r.date),fmt(r.recorridos),fmt(r.recolectadas)
  ])));
  const after=q('.report-kpis',host);
  if(after)after.after(container);else host.prepend(container);
 };
 function init(){
  const nav=q('#operativoNav'),page=q('#page-operativo'),host=q('#operativoDynamicContent');
  if(nav)new MutationObserver(schedule).observe(nav,{subtree:true,attributes:true,attributeFilter:['class','hidden','style','aria-selected']});
  if(page)new MutationObserver(schedule).observe(page,{attributes:true,attributeFilter:['class']});
  if(host)new MutationObserver(schedule).observe(host,{childList:true,subtree:true});
  document.addEventListener('change',e=>{
   if(e.target.matches('.storeActiveEdit,.storeProjectEdit,.storeNameEdit'))schedule();
  },true);
  window.addEventListener('pageshow',schedule,{passive:true});
  schedule();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();


/* V446: Productividad nacional — opción 1 aprobada. Sólo presentación.
   Usa el ranking completo ya autorizado por el servidor; pondera por colaborador-día. */
(function(){
 'use strict';
 const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
 const num=s=>{const x=Number(String(s??'').replace(/,/g,'').replace(/%/g,'').trim());return Number.isFinite(x)?x:0};
 const fmt=n=>Math.round(n).toLocaleString('es-MX');
 const pct=n=>n==null?'—':n.toFixed(1)+'%';
 const tone=n=>n==null?'neutral':n>=100?'good':n>=80?'warn':'bad';
 const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!=null)n.textContent=txt;return n};
 function style(){
  if(document.getElementById('or446-css'))return;
  const s=el('style');s.id='or446-css';s.textContent=
 '#page-operativo #operativoDynamicContent .or446-productivity{min-width:0;max-width:100%;color:#123b73;font-variant-numeric:tabular-nums}'+
 '.or446-productivity .or446-banner{background:#123b73;color:white;border-radius:10px;padding:12px 16px;margin:6px 0 9px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}'+
 '.or446-banner h2{font-size:24px!important;color:white!important;margin:0!important}.or446-banner small{color:white!important}'+
 '.or446-kpis{display:grid!important;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px;margin:8px 0}.or446-kpi{min-width:0;border:1px solid #d6e4f3;border-top:4px solid var(--tone);background:var(--bg);padding:10px;border-radius:10px}.or446-kpi small{display:block;font-size:11px;line-height:1.2;font-weight:750}.or446-kpi strong{display:block;font-size:clamp(17px,2vw,29px);color:var(--tone);line-height:1.25;white-space:nowrap}.or446-kpi em{font-style:normal;font-size:10px;color:#64748b}'+
 '.or446-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.05fr);gap:9px;align-items:start}.or446-panel{min-width:0;background:white;border:1px solid #d6e4f3;border-radius:10px;padding:10px}.or446-panel h3{margin:0 0 4px!important;color:#123b73;font-size:16px!important}.or446-note{font-size:11px;color:#63758a;margin:3px 0 10px}'+
 '#page-operativo #operativoDynamicContent .or446-wrap{width:100%!important;max-width:100%!important;min-width:0!important;overflow-x:auto!important;overflow-y:hidden!important;max-height:none!important;border-radius:7px;touch-action:pan-x pan-y}'+
 '#page-operativo #operativoDynamicContent .or446-table{width:100%!important;min-width:450px!important;max-width:none!important;border-collapse:separate!important;border-spacing:0!important;table-layout:auto!important}'+
 '#page-operativo #operativoDynamicContent .or446-table :is(th,td){position:static!important;white-space:nowrap!important;overflow-wrap:normal!important;word-break:normal!important;vertical-align:middle!important;padding:7px 5px!important;font-size:11px!important;line-height:1.25!important;text-align:right!important;border-bottom:1px solid #e0e8f2}'+
 '#page-operativo #operativoDynamicContent .or446-table th{background:#174778!important;color:white!important;text-align:center!important}'+
 '#page-operativo #operativoDynamicContent .or446-table td:nth-child(2){text-align:left!important;font-weight:700}'+
 '.or446-table tbody tr:nth-child(even){background:#edf3fa}.or446-good{color:#008044!important;font-weight:800}.or446-warn{color:#a66b00!important;font-weight:800}.or446-bad{color:#d71e2b!important;font-weight:800}.or446-neutral{color:#667085!important}'+
 '.or446-track{height:13px;position:relative;background:#e5edf6;border-radius:7px;min-width:110px;overflow:hidden}.or446-fill{height:100%;border-radius:7px}.or446-fill.good{background:#008b50}.or446-fill.warn{background:#e4a514}.or446-fill.bad{background:#d72c38}.or446-fill.neutral{background:#8493a5}.or446-marker{position:absolute;top:0;bottom:0;border-left:2px dashed #123b73}'+
 '.or446-legend{display:flex;flex-wrap:wrap;gap:8px;font-size:10px;margin-top:10px}.or446-actions{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;justify-content:flex-end}.or446-actions button{background:#123b73;color:#fff;border:0;border-radius:7px;padding:8px 12px;font-weight:750}.or446-full{margin-top:9px;border:1px solid #d6e4f3;border-radius:9px;padding:8px;background:white;min-width:0}.or446-full summary{cursor:pointer;font-weight:750;color:#123b73}.or446-full .tablewrap{max-width:100%!important;overflow-x:auto!important;max-height:none!important}'+
 '@media(max-width:900px){.or446-kpis{grid-template-columns:repeat(3,minmax(0,1fr))!important}.or446-grid{grid-template-columns:minmax(0,1fr)!important}.or446-banner h2{font-size:18px!important}}'+
 '@media(max-width:480px){.or446-kpis{gap:4px}.or446-kpi{padding:5px}.or446-kpi small{font-size:9px}.or446-kpi strong{font-size:15px}.or446-kpi em{font-size:8px}.or446-panel{padding:6px}.or446-panel h3{font-size:13px!important}.or446-banner{padding:8px}.or446-actions button{padding:7px 10px;font-size:11px}}';
  document.head.append(s);
 }
 function table(headers,rows){
  const wrap=el('div','or446-wrap'),t=el('table','or446-table'),head=el('thead'),hr=el('tr'),body=el('tbody');
  headers.forEach(h=>hr.append(el('th','',h)));head.append(hr);t.append(head);
  rows.forEach(row=>{const tr=el('tr');row.forEach(v=>{const td=el('td');if(v instanceof Node)td.append(v);else td.textContent=v;tr.append(td)});body.append(tr)});
  t.append(body);wrap.append(t);return wrap;
 }
 function apply(host){
  if(!host)return false;
  if(host.querySelector(':scope > .or446-productivity'))return true;
  const active=document.querySelector('#operativoNav [data-opview].active');
  if(!['Productividad por Colaborador','Ranking de Colaboradores'].includes(active?.dataset.opview))return false;
  const source=[...host.querySelectorAll('table')].find(t=>{
   const h=[...t.querySelectorAll('thead tr:last-child th')].map(x=>norm(x.textContent));
   return ['colaborador','tienda','piezas','dias','meta','cumplimiento'].every(k=>h.includes(k));
  });
  if(!source)return false;
  const hs=[...source.querySelectorAll('thead tr:last-child th')].map(x=>norm(x.textContent));
  const rows=[...source.querySelectorAll('tbody tr')].filter(tr=>tr.cells.length===hs.length).map(tr=>{
   const get=k=>tr.cells[hs.indexOf(k)]?.textContent.trim()||'';
   return {name:get('colaborador'),store:get('tienda'),pieces:num(get('piezas')),days:num(get('dias')),target:num(get('meta')),pct:num(get('cumplimiento'))};
  }).filter(r=>r.name&&r.store);
  const observed=rows.filter(r=>r.pieces>0),eligible=observed.filter(r=>r.target>0);
  const pieces=rows.reduce((s,r)=>s+r.pieces,0),days=rows.reduce((s,r)=>s+r.days,0),target=rows.reduce((s,r)=>s+r.target,0);
  const passed=eligible.filter(r=>r.pieces>=r.target).length,below=eligible.length-passed;
  const capped=target?rows.reduce((s,r)=>s+Math.min(r.pieces,r.target),0)/target*100:null;
  const groups=new Map();
  for(const r of rows){const g=groups.get(r.store)||{store:r.store,pieces:0,days:0,target:0};g.pieces+=r.pieces;g.days+=r.days;g.target+=r.target;groups.set(r.store,g)}
  const stores=[...groups.values()].map(g=>({...g,avg:g.days?g.pieces/g.days:0,pct:g.target?g.pieces/g.target*100:null})).sort((a,b)=>b.avg-a.avg||a.store.localeCompare(b.store));
  const scale=Math.max(100,...stores.map(g=>g.pct||0));
  style();
  const dashboard=el('div','or446-productivity'),banner=el('div','or446-banner'),heading=el('div');
  heading.append(el('h2','','Productividad nacional'),el('small','','Operaciones Ropa · '+(document.querySelector('#operPeriodSelect')?.value||'Periodo consultado')+' · '+(document.querySelector('#operStoreSelect')?.value||'Compañía')));
  banner.append(heading);dashboard.append(banner);
  const cards=el('div','or446-kpis');
  [['Piezas procesadas',fmt(pieces),'Actividades productivas','#00816c','#eaf9f4'],['Productividad diaria',days?fmt(pieces/days):'—','Pzas. / colaborador-día','#cd5d06','#fff3e8'],['Cumplimiento',target?pct(pieces/target*100):'—','Real · topado: '+pct(capped),'#7334c8','#f3efff'],['Con productividad',fmt(observed.length),'Colaboradores con piezas','#1564ad','#edf5ff'],['Cumplen meta',passed+' de '+eligible.length,'100% o más','#008044','#edf9f0'],['Debajo de meta',below+' de '+eligible.length,'Menor a 100%','#da2835','#fff0f1']].forEach(([l,v,n,c,b])=>{const card=el('div','or446-kpi');card.style.setProperty('--tone',c);card.style.setProperty('--bg',b);card.append(el('small','',l),el('strong','',v),el('em','',n));cards.append(card)});
  dashboard.append(cards);
  const actions=el('div','or446-actions');
  for(const [f,label] of [['xlsx','Descargar Excel'],['pdf','Descargar PDF']]){const b=el('button','',label);b.type='button';b.addEventListener('click',()=>{if(typeof window.downloadCurrentReport==='function')window.downloadCurrentReport(f,'Productividad por Colaborador',b)});actions.append(b)}
  dashboard.append(actions);
  const grid=el('div','or446-grid'),left=el('section','or446-panel'),right=el('section','or446-panel');
  left.append(el('h3','','Productividad promedio por tienda'),el('p','or446-note','Promedio ponderado por colaborador-día · línea punteada = 100% de la meta'));
  left.append(table(['Rank.','Tienda','Avance vs meta','Pzas. prom.','Cumpl.'],stores.map((g,i)=>{
   const track=el('div','or446-track'),fill=el('div','or446-fill '+tone(g.pct)),marker=el('div','or446-marker');
   fill.style.width=Math.min(100,Math.max(0,(g.pct||0)/scale*100))+'%';marker.style.left=100/scale*100+'%';track.append(fill,marker);track.title=pct(g.pct);
   return ['#'+(i+1),g.store,track,g.days?fmt(g.avg):'—',el('span','or446-'+tone(g.pct),pct(g.pct))];
  })));
  const legend=el('div','or446-legend');[['good','● ≥100%'],['warn','● 80–99.9%'],['bad','● <80%']].forEach(([c,l])=>legend.append(el('span','or446-'+c,l)));left.append(legend);
  right.append(el('h3','','Ranking de colaboradores'),el('p','or446-note','Ordenado por piezas procesadas · periodo seleccionado'));
  right.append(table(['Rank.','Colaborador','Tienda','Pzas.','Cumpl.'],rows.slice().sort((a,b)=>b.pieces-a.pieces||a.name.localeCompare(b.name)).map((r,i)=>['#'+(i+1),r.name,r.store,fmt(r.pieces),el('span','or446-'+tone(r.target?r.pct:null),pct(r.target?r.pct:null))])));
  grid.append(left,right);dashboard.append(grid);
  const full=el('details','or446-full');full.append(el('summary','','Detalle completo · días, productividad, meta y faltante'));
  const original=source.closest('.tablewrap')||source;full.append(original);dashboard.append(full);
  // Conservar los controles administrativos y origen digital; no copiar listeners.
  const badge=host.querySelector('.v199-digital-badge'),admin=host.querySelector('.or357-delete-toolbar');
  if(badge)dashboard.append(badge);
  if(admin)dashboard.append(admin);
  host.replaceChildren(dashboard);
  return true;
 }
 window.OR446_PRODUCTIVITY=apply;
 function init(){const host=document.getElementById('operativoDynamicContent');if(!host)return;let queued=false;const run=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;apply(host)})};new MutationObserver(run).observe(host,{childList:true,subtree:true});run()}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
