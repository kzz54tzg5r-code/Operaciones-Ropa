/* V362: implementaciones de presentación aprobadas.
   Sin nuevas mutaciones de datos ni cambios de endpoints; mantiene listeners originales. */
(() => {
 'use strict';
 if(window.__or362Installed)return;
 window.__or362Installed=true;
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
  if(key)document.body.dataset.or362View=key;
  else delete document.body.dataset.or362View;
  const host=q('#operativoDynamicContent');
  if(key==='operations.goals'&&host)decorateGoals(host);
  if(key==='operations.productivity'&&host)decorateProductivity(host);
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
  if(host)decorateProductivity(host);
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
