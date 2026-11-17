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


/* V433: encabezados agrupados estables, separación por indicador y pendientes.
   Se ejecuta después de V431 (que mantiene el orden de los valores). */
(function(){
  'use strict';
  const cssId='or-detail-groups-v433-css';
  function installCss(){
    if(document.getElementById(cssId))return;
    const style=document.createElement('style');
    style.id=cssId;
    style.textContent=[
      'table.or-detail-groups-v433{border-collapse:separate!important;border-spacing:0!important;}',
      'table.or-detail-groups-v433 thead tr.or-detail-groups-row>th{position:sticky!important;top:0!important;z-index:12!important;height:34px!important;min-height:34px!important;box-sizing:border-box!important;background:#123e70!important;color:#fff!important;text-align:center!important;vertical-align:middle!important;font-size:12px!important;font-weight:800!important;padding:6px 4px!important;white-space:nowrap!important;}',
      'table.or-detail-groups-v433 thead tr:not(.or-detail-groups-row)>th{position:sticky!important;top:34px!important;z-index:11!important;background:#194d82!important;color:white!important;text-align:center!important;vertical-align:middle!important;}',
      'table.or-detail-groups-v433 thead tr.or-detail-groups-row>th.or-detail-group-name{background:#103968!important;}',
      'table.or-detail-groups-v433 thead tr.or-detail-groups-row>th.or-detail-separator,',
      'table.or-detail-groups-v433 thead tr:not(.or-detail-groups-row)>th.or-detail-separator,',
      'table.or-detail-groups-v433 tbody tr>td.or-detail-separator{border-left:2px dashed #e53935!important;}',
      'table.or-detail-groups-v433 tbody tr>td.or-detail-percent-cell{background:#eef1f4!important;}',
      'table.or-detail-groups-v433 thead tr>th.or-detail-rank,',
      'table.or-detail-groups-v433 tbody tr>td.or-detail-rank{text-align:center!important;vertical-align:middle!important;}'
    ].join('');
    document.head.appendChild(style);
  }
  const norm=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  function group(table){
    if(table.dataset.orDetailGroupsV433==='1'||table.dataset.orDetailPercentV431!=='1')return;
    if(!table.tHead||table.tHead.rows.length!==1||!table.tBodies.length)return;
    const cells=Array.from(table.tHead.rows[0].cells);
    if(cells.length!==16)return;
    const labels=cells.map(cell=>norm(cell.textContent));
    if(!([[1,'tienda'],[2,'dev'],[6,'total'],[7,'recorridos'],[8,'acondicionado'],
      [9,'ubicado'],[10,'% recorridos'],[11,'% acond'],[12,'% ubicado'],
      [13,'pend. acond'],[14,'pend. ubicar'],[15,'score']]
       .every(([i,text])=>labels[i].includes(text))))return;
    installCss();
    const firstRow=table.tHead.rows[0];
    cells[0].textContent='Rank.';
    cells[0].classList.add('or-detail-rank');
    cells[13].textContent='Acond.';
    cells[14].textContent='Ubicar';
    // Marcar los límites de cada uno de los grupos de columnas.
    const separators=[2,7,10,13,15];
    separators.forEach(i=>cells[i].classList.add('or-detail-separator'));
    const row=document.createElement('tr');
    row.className='or-detail-groups-row';
    function add(count,label,classes=''){
      const th=document.createElement('th');
      th.colSpan=count;th.textContent=label;th.className=classes;
      row.appendChild(th);
    }
    add(2,'');
    add(5,'Recolección','or-detail-group-name or-detail-separator');
    add(3,'Actividad','or-detail-group-name or-detail-separator');
    add(3,'% x Indicador','or-detail-group-name or-detail-separator');
    add(2,'Pendientes','or-detail-group-name or-detail-separator');
    add(1,'Score','or-detail-group-name or-detail-separator');
    for(const body of table.tBodies){
      for(const tr of body.rows){
        const tds=Array.from(tr.cells);
        if(tds.length!==16)continue;
        tds[0].classList.add('or-detail-rank');
        separators.forEach(i=>tds[i].classList.add('or-detail-separator'));
        [10,11,12].forEach(i=>tds[i].classList.add('or-detail-percent-cell'));
      }
    }
    table.classList.add('or-detail-groups-v433');
    table.dataset.orDetailGroupsV433='1';
    table.tHead.insertBefore(row,firstRow);
  }
  function scan(){
    const root=document.getElementById('page-operativo')||document;
    root.querySelectorAll('table').forEach(group);
  }
  function init(){
    const root=document.getElementById('page-operativo')||document.body;
    if(!root||root.dataset.orDetailGroupObserverV433)return;
    root.dataset.orDetailGroupObserverV433='1';
    let scheduled=false;
    new MutationObserver(()=>{
      if(scheduled)return;
      scheduled=true;
      requestAnimationFrame(()=>{scheduled=false;scan()});
    }).observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['data-or-detail-percent-v431']});
    scan();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
  else init();
})();
