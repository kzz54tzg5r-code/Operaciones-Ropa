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
