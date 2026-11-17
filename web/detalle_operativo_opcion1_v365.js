/* V408: Detalle Operativo — gráfica mixta (2 barras y línea de Ubicado).
   La tabla original y sus 15 campos se respetan (V117); solo se estiliza mediante CSS.
   Se consumen exclusivamente los datos y filtros ya entregados al reporte. */
(function(){
  'use strict';
  if(window.__or365DetailOption1Installed)return;
  window.__or365DetailOption1Installed=true;
  const numeric=value=>{
    const n=Number(value);
    return Number.isFinite(n)?Math.max(0,n):0;
  };
  const escapeText=value=>String(value==null?'':value).replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[char]);
  const numberLabel=value=>typeof fmt==='function'?fmt(value):Math.round(value).toLocaleString('es-MX');
  const paint=[
    {key:'ingresos',label:'Ingresos',color:'#1769e8'},
    {key:'acondicionado',label:'Acondicionado',color:'#173b73'},
    {key:'ubicado',label:'Ubicado',color:'#e50076'}
  ];
  window.opsComboSvg=function(rows,period,scope,rec=[]){
    // No modificar ni normalizar registros: solo leerlos para dibujar el gráfico.
    const data=(Array.isArray(rows)?rows:[])
      .filter(row=>row && String(row.store||'').trim())
      .slice().sort((a,b)=>numeric(b.ingresos)-numeric(a.ingresos));
    if(!data.length){
      return '<div class="infoempty">Información no disponible para Ingreso vs Acondicionado vs Ubicado.</div>';
    }
    // Vista completa: distribuir todas las tiendas dentro del ancho del panel.
    // El SVG se ajusta al contenedor sin ancho mínimo ni barra horizontal.
    const width=Math.max(1050,Math.round(data.length*86+92));
    const height=385,left=58,right=22,top=54,bottom=91;
    const plotHeight=height-top-bottom,plotWidth=width-left-right,baseline=top+plotHeight;
    const maximum=Math.max(1,...data.flatMap(row=>paint.map(p=>numeric(row[p.key]))));
    const groupWidth=plotWidth/data.length;
    const barWidth=Math.min(17,Math.max(10,groupWidth*.19));
    const gap=Math.min(4,groupWidth*.035);
    const fmtTick=n=>escapeText(numberLabel(n));
    const y=value=>baseline-(numeric(value)/maximum*plotHeight);
    const parts=['<svg class="combo-svg or365-vertical-svg" role="img" '+
      'aria-label="Gráfico mixto: ingresos y acondicionado en barras, ubicado como línea rosa" '+
      'viewBox="0 0 '+width+' '+height+'" preserveAspectRatio="xMidYMid meet">'];
    parts.push('<title>Ingresos, acondicionado y ubicado por tienda</title>');
    for(let i=0;i<=4;i++){
      const value=maximum*i/4,yy=y(value);
      parts.push('<line x1="'+left+'" x2="'+(width-right)+'" y1="'+yy+'" y2="'+yy+
        '" stroke="#e1e9f4" stroke-width="1"/>');
      parts.push('<text x="'+(left-9)+'" y="'+(yy+3)+'" text-anchor="end" fill="#6b7d91" font-size="10">'+fmtTick(value)+'</text>');
    }
    paint.forEach((series,i)=>{
      const x=left+i*163;
      if(series.key==='ubicado'){
        parts.push('<line x1="'+x+'" y1="17.5" x2="'+(x+13)+'" y2="17.5" stroke="'+series.color+'" stroke-width="3"/>');
        parts.push('<circle cx="'+(x+7)+'" cy="17.5" r="3" fill="'+series.color+'" stroke="#fff"/>');
      }else{
        parts.push('<rect x="'+x+'" y="12" width="11" height="11" rx="2" fill="'+series.color+'"/>');
      }
      parts.push('<text x="'+(x+17)+'" y="21" fill="#3c526f" font-size="11">'+series.label+'</text>');
    });
    const ubicPoints=[];
    const labels=[];
    data.forEach((row,i)=>{
      const center=left+(i+.5)*groupWidth;
      const bars=paint.slice(0,2);
      const barCoordinates=[];
      bars.forEach((series,j)=>{
        const value=numeric(row[series.key]);
        const barHeight=value/maximum*plotHeight;
        const x=center+(j===0?-1:1)*(barWidth/2+gap/2)-barWidth/2;
        const barTop=baseline-barHeight;
        const barTitle=escapeText(row.store)+' · '+series.label+': '+fmtTick(value);
        parts.push('<rect x="'+x.toFixed(2)+'" y="'+barTop.toFixed(2)+'" width="'+barWidth+
          '" height="'+barHeight.toFixed(2)+'" rx="2" fill="'+series.color+'"><title>'+barTitle+'</title></rect>');
        barCoordinates.push({x:x+barWidth/2,y:barTop,value:value,color:series.color});
      });
      const ubic=numeric(row.ubicado);
      const pointY=y(ubic);
      ubicPoints.push({x:center,y:pointY,value:ubic,store:String(row.store||'')});
      // Etiquetas dibujadas al final, encima de la línea y con halo blanco.
      for(let j=0;j<barCoordinates.length;j++){
        const bar=barCoordinates[j],other=barCoordinates[1-j];
        let labelY=Math.max(top+10,bar.y-7);
        if(Math.abs(bar.y-other.y)<14)labelY+=j===0?-9:10;
        labels.push('<text x="'+bar.x.toFixed(2)+'" y="'+Math.max(top+11,labelY).toFixed(2)+
          '" text-anchor="middle" font-size="9" font-weight="750" fill="'+bar.color+
          '" paint-order="stroke" stroke="#fff" stroke-width="3">'+fmtTick(bar.value)+'</text>');
      }
      let ubicLabelY=Math.max(top+11,pointY-13);
      if(barCoordinates.some(p=>Math.abs(p.y-pointY)<18))ubicLabelY=Math.max(top+11,ubicLabelY-18);
      labels.push('<text x="'+center.toFixed(2)+'" y="'+ubicLabelY.toFixed(2)+
        '" text-anchor="middle" font-size="9" font-weight="800" fill="#e50076" '+
        'paint-order="stroke" stroke="#fff" stroke-width="3">'+fmtTick(ubic)+'</text>');
      // Rótulo inclinado: las 17 tiendas caben sin superposición.
      parts.push('<text transform="translate('+center.toFixed(2)+','+(baseline+17)+') rotate(-37)"'+
        ' font-size="11" text-anchor="end" fill="#29496c">'+escapeText(row.store)+'</text>');
      parts.push('<text x="'+center.toFixed(2)+'" y="'+(height-8)+
        '" font-size="9" text-anchor="middle" fill="#708197">#'+(i+1)+'</text>');
    });
    // Ubicado: línea continua con marcas visibles (incluye ceros reales).
    const points=ubicPoints.map(p=>p.x.toFixed(2)+','+p.y.toFixed(2)).join(' ');
    parts.push('<polyline points="'+points+'" fill="none" stroke="#e50076" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>');
    ubicPoints.forEach(p=>{
      parts.push('<circle cx="'+p.x.toFixed(2)+'" cy="'+p.y.toFixed(2)+
        '" r="4.4" fill="#e50076" stroke="#fff" stroke-width="1.5"><title>'+
        escapeText(p.store)+' · Ubicado: '+fmtTick(p.value)+'</title></circle>');
    });
    parts.push(...labels);
    parts.push('</svg>');
    const textPeriod=escapeText(period||'Histórico');
    const textScope=escapeText(scope||'Todas las tiendas');
    return '<div class="chart-box chart-scroll or365-detail-chart" data-or365-chart="mixed-bars-line">'+
      '<h3 class="or365-chart-title">Ingresos vs Acondicionado vs Ubicado · '+textScope+' · '+textPeriod+'</h3>'+
      '<div class="or365-chart-hint">Comparativo por tienda · todas las tiendas visibles en una sola gráfica</div>'+
      parts.join('')+'</div>';
  };
})();


/* V431: paridad visual de Detalle operativo en Día/Semana/Mes/Año.
   Reordenar columnas sin alterar el conjunto de datos ni el score. */
(function(){
  'use strict';
  const normalize = value => String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/\s+/g,' ').trim().toLowerCase();
  function correctTable(table){
    if(table.dataset.orDetailPercentV431==='1'||!table.tHead||!table.tBodies.length)return;
    const header=table.tHead.rows[0];
    if(!header)return;
    const original=Array.from(header.cells);
    const labels=original.map(cell=>normalize(cell.textContent));
    const find=(...parts)=>labels.findIndex(label=>parts.every(part=>label.includes(part)));
    const store=find('tienda'), total=find('total','pzs'), routes=find('recorridos','realiz'),
      acond=find('acondicionado'), ubic=find('ubicado'),
      percentRoutes=find('%','recorridos'), percentAcond=find('%','acondi'),
      percentUbic=find('%','ubicado'),
      pendAcond=find('pendiente','acond'), pendUbic=find('pendiente','ubicar'), score=find('score');
    // Aplicar sólo a la tabla operativa de 15 campos; no modificar recuperación ni otras tablas.
    if([store,total,routes,acond,ubic,percentRoutes,percentAcond,pendAcond,pendUbic,score].some(i=>i<0))return;
    if(original.length<14 || table.tBodies[0].rows.length===0)return;
    const before=original.slice(0,ubic+1).map((_,i)=>i);
    const trailing=original.map((_,i)=>i).filter(i=>!before.includes(i) &&
      ![percentRoutes,percentAcond,percentUbic,pendAcond,pendUbic,score].includes(i));
    const order=[...before,percentRoutes,percentAcond,...(percentUbic>=0?[percentUbic]:[]),
      pendAcond,pendUbic,score,...trailing];
    const formatPercent = (ubicado,total) => {
      const asNum=text=>{
        const cleaned=String(text||'').replace(/[^0-9.,-]/g,'').replace(/,/g,'');
        return Number(cleaned)||0;
      };
      const den=asNum(total),num=asNum(ubicado);
      return (den>0?num/den*100:0).toFixed(1)+'%';
    };
    table.dataset.orDetailPercentV431='1';
    const heads=[...original];
    heads[percentRoutes].textContent='% Recorridos';
    heads[percentAcond].textContent='% Acond.';
    heads[pendAcond].textContent='Pend. Acond.';
    heads[pendUbic].textContent='Pend. Ubicar';
    if(percentUbic>=0)heads[percentUbic].textContent='% Ubicado';
    else {
      const newHead=document.createElement('th');
      newHead.textContent='% Ubicado';
      const pivot=order.indexOf(percentAcond);
      order.splice(pivot+1,0,heads.length);
      heads.push(newHead);
    }
    header.replaceChildren(...order.map(i=>heads[i]));
    for(const body of table.tBodies){
      for(const row of body.rows){
        const cells=Array.from(row.cells);
        if(cells.length!==original.length)continue;
        if(percentUbic<0){
          const cell=document.createElement('td');
          cell.textContent=formatPercent(cells[ubic]?.textContent,cells[total]?.textContent);
          cell.style.fontWeight='700';
          cells.push(cell);
        }
        row.replaceChildren(...order.map(i=>cells[i]));
      }
    }
  }
  function scan(){
    const root=document.getElementById('page-operativo')||document;
    root.querySelectorAll('table').forEach(correctTable);
  }
  function init(){
    const root=document.getElementById('page-operativo')||document.body;
    if(!root||root.dataset.orDetailObserverV431)return;
    root.dataset.orDetailObserverV431='1';
    let queued=false;
    new MutationObserver(()=>{
      if(queued)return;
      queued=true;
      requestAnimationFrame(()=>{queued=false;scan();});
    }).observe(root,{childList:true,subtree:true});
    scan();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();


/* V434: Detalle operativo sin scroll interno ni sticky; pendientes antes de porcentajes. */
(function(){
  'use strict';
  const cssId='or-detail-groups-v434-css';
  function installCss(){
    if(document.getElementById(cssId))return;
    const style=document.createElement('style');
    style.id=cssId;
    style.textContent=[
      '#page-operativo .or-detail-fixed-v434{overflow:visible!important;overflow-x:visible!important;overflow-y:visible!important;max-height:none!important;height:auto!important;scrollbar-width:none!important;}',
      '#page-operativo table.or-detail-groups-v434{border-collapse:separate!important;border-spacing:0!important;width:100%!important;table-layout:fixed!important;}',
      '#page-operativo table.or-detail-groups-v434 thead tr.or-detail-groups-row>th{position:static!important;top:auto!important;z-index:auto!important;background:#103968!important;color:white!important;height:34px!important;text-align:center!important;vertical-align:middle!important;font-size:12px!important;font-weight:800!important;padding:7px 3px!important;white-space:nowrap!important;}',
      '#page-operativo table.or-detail-groups-v434 thead tr:not(.or-detail-groups-row)>th{position:static!important;top:auto!important;z-index:auto!important;background:#194d82!important;color:white!important;text-align:center!important;vertical-align:middle!important;}',
      '#page-operativo table.or-detail-groups-v434 .or-detail-separator{border-left:2px dashed #e53935!important;}',
      '#page-operativo table.or-detail-groups-v434 tbody tr>td.or-detail-score{background:#d3d8df!important;}',
      '#page-operativo table.or-detail-groups-v434 thead tr>th.or-detail-rank,',
      '#page-operativo table.or-detail-groups-v434 tbody tr>td.or-detail-rank{text-align:center!important;vertical-align:middle!important;}',
      '#page-operativo table.or-detail-groups-v434 tbody tr>td.or-detail-indicator{background:transparent!important;}',
      '#page-operativo table.or-detail-groups-v434 tbody tr:nth-child(even)>td.or-detail-indicator{background:#eaf1f9!important;}'
    ].join('');
    document.head.appendChild(style);
  }
  const norm=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  function apply(table){
    if(table.dataset.orDetailGroupsV434==='1'||table.dataset.orDetailPercentV431!=='1')return;
    if(!table.tHead||table.tHead.rows.length!==1||!table.tBodies.length)return;
    const row=table.tHead.rows[0], heads=Array.from(row.cells);
    if(heads.length!==16)return;
    const titles=heads.map(cell=>norm(cell.textContent));
    const checks=[[1,'tienda'],[2,'dev'],[6,'total'],[7,'recorridos'],[8,'acondicionado'],
      [9,'ubicado'],[10,'% recorridos'],[11,'% acond'],[12,'% ubicado'],
      [13,'pend. acond'],[14,'pend. ubicar'],[15,'score']];
    if(!checks.every(([i,t])=>titles[i].includes(t)))return;
    installCss();
    // Cada fila se mueve por columnas completas para conservar sus valores originales.
    const order=[0,1,2,3,4,5,6,7,8,9,13,14,10,11,12,15];
    heads[0].textContent='Rank.';
    heads[13].textContent='Acond.';
    heads[14].textContent='Ubicar';
    heads[15].textContent='Score %';
    row.replaceChildren(...order.map(i=>heads[i]));
    for(const body of table.tBodies){
      for(const tr of body.rows){
        const cells=Array.from(tr.cells);
        if(cells.length!==16)continue;
        tr.replaceChildren(...order.map(i=>cells[i]));
      }
    }
    const separators=[2,7,10,12,15];
    const bottomHeads=Array.from(row.cells);
    separators.forEach(i=>bottomHeads[i].classList.add('or-detail-separator'));
    bottomHeads[0].classList.add('or-detail-rank');
    const grouped=document.createElement('tr');
    grouped.className='or-detail-groups-row';
    function add(span,label,klass=''){
      const cell=document.createElement('th');
      cell.colSpan=span;cell.textContent=label;cell.className=klass;
      grouped.appendChild(cell);
    }
    add(2,'');
    add(5,'Recolección','or-detail-separator');
    add(3,'Actividad','or-detail-separator');
    add(2,'Pendientes','or-detail-separator');
    add(3,'% x Indicador','or-detail-separator');
    add(1,'Score','or-detail-separator');
    table.tHead.insertBefore(grouped,row);
    for(const body of table.tBodies){
      for(const tr of body.rows){
        if(tr.cells.length!==16)continue;
        const cells=Array.from(tr.cells);
        cells[0].classList.add('or-detail-rank');
        separators.forEach(i=>cells[i].classList.add('or-detail-separator'));
        [12,13,14].forEach(i=>{
          const cell=cells[i];
          cell.classList.add('or-detail-indicator');
          const num=Number(String(cell.textContent||'').replace('%','').trim());
          if(!Number.isFinite(num))return;
          // Semáforo: verde >=80; ámbar 60–79.9; rojo <60.
          cell.style.setProperty('color',num>=80?'#008744':num>=60?'#ad7100':'#d51d25','important');
          cell.style.setProperty('font-weight','800','important');
        });
        cells[15].classList.add('or-detail-score');
      }
    }
    table.classList.add('or-detail-groups-v434');
    const wrapper=table.closest('.tablewrap');
    if(wrapper)wrapper.classList.add('or-detail-fixed-v434');
    table.dataset.orDetailGroupsV434='1';
  }
  function scan(){
    const root=document.getElementById('page-operativo')||document;
    root.querySelectorAll('table').forEach(apply);
  }
  function init(){
    const root=document.getElementById('page-operativo')||document.body;
    if(!root||root.dataset.orDetailObserverV434)return;
    root.dataset.orDetailObserverV434='1';
    let queued=false;
    new MutationObserver(()=>{
      if(queued)return;
      queued=true;
      requestAnimationFrame(()=>{queued=false;scan()});
    }).observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['data-or-detail-percent-v431']});
    scan();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();


/* V439 — Detalle operativo diario: mismos campos, Pendientes antes de % x Indicador.
   No altera los cálculos ni las vistas semanal, mensual y anual. */
(function(){
  'use strict';
  const marker='orDetailDailyV439';
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/\s+/g,' ').trim().toLowerCase();
  function installStyle(){
    if(document.getElementById('or-detail-daily-v439-style'))return;
    const style=document.createElement('style');
    style.id='or-detail-daily-v439-style';
    style.textContent=[
      '#page-operativo table.or-detail-daily-v439{width:100%!important;table-layout:fixed!important;border-collapse:separate!important;border-spacing:0!important;}',
      '#page-operativo table.or-detail-daily-v439 thead tr.or-daily-group-row th{background:#103968!important;color:#fff!important;text-align:center!important;vertical-align:middle!important;font-size:12px!important;font-weight:800!important;padding:7px 3px!important;position:static!important;white-space:nowrap!important;}',
      '#page-operativo table.or-detail-daily-v439 thead tr:not(.or-daily-group-row) th{position:static!important;text-align:center!important;vertical-align:middle!important;}',
      '#page-operativo table.or-detail-daily-v439 .or-daily-boundary{border-left:2px dashed #e53935!important;}',
      '#page-operativo table.or-detail-daily-v439 tbody td.or-daily-score{background:#d3d8df!important;}',
      '#page-operativo table.or-detail-daily-v439 thead th.or-daily-rank,',
      '#page-operativo table.or-detail-daily-v439 tbody td.or-daily-rank{text-align:center!important;}',
      '#page-operativo .or-detail-daily-v439-wrapper{overflow:visible!important;overflow-x:visible!important;overflow-y:visible!important;max-height:none!important;height:auto!important;}'
    ].join('');
    document.head.appendChild(style);
  }
  function apply(table){
    if(table.dataset[marker]==='1'||!table.tHead||table.tHead.rows.length!==1||!table.tBodies.length)return;
    const header=table.tHead.rows[0];
    const cols=Array.from(header.cells);
    if(cols.length!==16)return;
    const labels=cols.map(th=>norm(th.textContent));
    // El diario conserva Pend. Ant. y carece de % Recorridos.
    const checks=[[1,'tienda'],[2,'dev'],[3,'muertos'],[4,'proba'],[5,'cajas'],
      [6,'pend'],[7,'total'],[8,'recorridos'],[9,'acondi'],[10,'ubicado'],
      [11,'% acond'],[12,'% ubicado'],[13,'pendiente'],[14,'pendiente'],[15,'score']];
    if(!checks.every(([i,label])=>labels[i].includes(label)))return;
    if(labels[6].includes('acond')||labels[6].includes('ubicar')||labels[6].includes('ubicado'))return;
    installStyle();
    const order=[0,1,2,3,4,5,6,7,8,9,10,13,14,11,12,15];
    cols[0].textContent='Rank.';
    cols[13].textContent='Acond.';
    cols[14].textContent='Ubicar';
    cols[11].textContent='% Acond.';
    cols[12].textContent='% Ubicado';
    cols[15].textContent='Score %';
    header.replaceChildren(...order.map(i=>cols[i]));
    for(const tbody of table.tBodies){
      for(const tr of tbody.rows){
        const cells=Array.from(tr.cells);
        if(cells.length!==16)continue;
        tr.replaceChildren(...order.map(i=>cells[i]));
        const ordered=Array.from(tr.cells);
        ordered[0].classList.add('or-daily-rank');
        [2,8,11,13,15].forEach(i=>ordered[i].classList.add('or-daily-boundary'));
        [13,14].forEach(i=>{
          const td=ordered[i],val=Number(td.textContent.replace('%','').replace(/,/g,'').trim());
          if(!Number.isFinite(val))return;
          td.style.setProperty('color',val>=80?'#008744':val>=60?'#ad7100':'#d51d25','important');
          td.style.setProperty('font-weight','800','important');
        });
        ordered[15].classList.add('or-daily-score');
      }
    }
    const lower=Array.from(header.cells);
    lower[0].classList.add('or-daily-rank');
    [2,8,11,13,15].forEach(i=>lower[i].classList.add('or-daily-boundary'));
    const band=document.createElement('tr');band.className='or-daily-group-row';
    for(const [count,title] of [[2,''],[6,'Recolección'],[3,'Actividad'],
      [2,'Pendientes'],[2,'% x Indicador'],[1,'Score']]){
      const th=document.createElement('th');th.colSpan=count;th.textContent=title;
      if(title)th.classList.add('or-daily-boundary');
      band.appendChild(th);
    }
    table.tHead.insertBefore(band,header);
    table.classList.add('or-detail-daily-v439');
    const wrap=table.closest('.tablewrap');
    if(wrap)wrap.classList.add('or-detail-daily-v439-wrapper');
    table.dataset[marker]='1';
  }
  function scan(){
    const page=document.getElementById('page-operativo');
    if(page)page.querySelectorAll('table').forEach(apply);
  }
  function init(){
    const root=document.getElementById('page-operativo');
    if(!root||root.dataset.orDailyObserverV439)return;
    root.dataset.orDailyObserverV439='1';
    let queued=false;
    new MutationObserver(()=>{
      if(queued)return;queued=true;
      requestAnimationFrame(()=>{queued=false;scan()});
    }).observe(root,{subtree:true,childList:true});
    scan();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();


/* V440: centrar Recolección exactamente sobre su colspan (Día, Semana, Mes, Año).
   Un estilo heredado fuerza el segundo th del encabezado a alineación izquierda;
   centrar el texto con una capa absoluta independiente evita esa interferencia. */
(function(){
  'use strict';
  const rootSelector='#page-operativo';
  const sheetId='or-recoleccion-center-v440';
  function css(){
    if(document.getElementById(sheetId))return;
    const sheet=document.createElement('style');
    sheet.id=sheetId;
    sheet.textContent=[
      rootSelector+' table.or-detail-daily-v439 thead tr.or-daily-group-row th.or-recoleccion-v440,',
      rootSelector+' table.or-detail-groups-v434 thead tr.or-detail-groups-row th.or-recoleccion-v440',
      '{position:relative!important;text-align:center!important;padding-left:0!important;padding-right:0!important;}',
      rootSelector+' th.or-recoleccion-v440 > span.or-recoleccion-label-v440',
      '{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;',
      'display:flex!important;align-items:center!important;justify-content:center!important;',
      'text-align:center!important;padding:0!important;margin:0!important;',
      'font:inherit!important;color:inherit!important;line-height:1.1!important;pointer-events:none!important;}'
    ].join('');
    document.head.appendChild(sheet);
  }
  function apply(){
    const root=document.querySelector(rootSelector);
    if(!root)return;
    root.querySelectorAll('table.or-detail-daily-v439, table.or-detail-groups-v434').forEach(table=>{
      const row=table.tHead?.rows[0];
      if(!row||!row.classList.contains('or-daily-group-row')&&!row.classList.contains('or-detail-groups-row'))return;
      const header=Array.from(row.cells).find(th=>th.textContent.trim()==='Recolección');
      if(!header||header.classList.contains('or-recoleccion-v440'))return;
      css();
      header.classList.add('or-recoleccion-v440');
      const label=document.createElement('span');
      label.className='or-recoleccion-label-v440';
      label.textContent='Recolección';
      header.replaceChildren(label);
    });
  }
  function initialize(){
    const root=document.querySelector(rootSelector);
    if(!root||root.dataset.orRecoleccionObserverV440)return;
    root.dataset.orRecoleccionObserverV440='1';
    let pending=false;
    new MutationObserver(()=>{
      if(pending)return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;apply();});
    }).observe(root,{childList:true,subtree:true});
    apply();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize);
  else initialize();
})();


/* V441: corregir la CAUSA del desplazamiento de Recolección.
   Con table-layout:fixed el navegador calcula el ancho de columnas a partir
   de la primera fila con colspan; eso genera un grupo desplazado. En auto,
   los 16 encabezados inferiores determinan las columnas y los colspan las
   agrupan sin distorsionar sus límites. */
(function(){
  'use strict';
  function addStyles(){
    if(document.getElementById('or-groups-column-align-v441'))return;
    const style=document.createElement('style');
    style.id='or-groups-column-align-v441';
    style.textContent=[
      '#page-operativo table.or-detail-daily-v439,',
      '#page-operativo table.or-detail-groups-v434',
      '{table-layout:auto!important;width:100%!important;border-collapse:separate!important;border-spacing:0!important;}',
      '#page-operativo table.or-detail-daily-v439 thead tr.or-daily-group-row>th,',
      '#page-operativo table.or-detail-groups-v434 thead tr.or-detail-groups-row>th',
      '{width:auto!important;min-width:0!important;max-width:none!important;box-sizing:border-box!important;text-align:center!important;vertical-align:middle!important;}',
      '#page-operativo th.or-recoleccion-v440{padding-left:0!important;padding-right:0!important;}'
    ].join('');
    document.head.appendChild(style);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',addStyles);
  else addStyles();
})();
