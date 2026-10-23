/* V365: Detalle Operativo — gráfica 1 con barras verticales agrupadas.
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
      .filter(row=>row && paint.some(p=>numeric(row[p.key])>0))
      .slice().sort((a,b)=>numeric(b.ingresos)-numeric(a.ingresos));
    if(!data.length){
      return '<div class="infoempty">Información no disponible para Ingreso vs Acondicionado vs Ubicado.</div>';
    }
    const width=Math.max(650,Math.round(data.length*112+104));
    const height=333,left=61,right=25,top=52,bottom=65;
    const plotHeight=height-top-bottom,plotWidth=width-left-right,baseline=top+plotHeight;
    const maximum=Math.max(1,...data.flatMap(row=>paint.map(p=>numeric(row[p.key]))));
    const groupWidth=plotWidth/data.length;
    const barWidth=Math.min(20,Math.max(11,groupWidth*.18));
    const gap=Math.min(4,groupWidth*.035);
    const fmtTick=n=>escapeText(numberLabel(n));
    const y=value=>baseline-(numeric(value)/maximum*plotHeight);
    const parts=['<svg class="combo-svg or365-vertical-svg" role="img" '+
      'aria-label="Comparativo de ingresos, acondicionado y ubicado por tienda en barras verticales" '+
      'style="--or365-min-width:'+width+'px" viewBox="0 0 '+width+' '+height+'" preserveAspectRatio="xMinYMin meet">'];
    parts.push('<title>Ingresos, acondicionado y ubicado por tienda</title>');
    for(let i=0;i<=4;i++){
      const value=maximum*i/4,yy=y(value);
      parts.push('<line x1="'+left+'" x2="'+(width-right)+'" y1="'+yy+'" y2="'+yy+
        '" stroke="#e1e9f4" stroke-width="1"/>');
      parts.push('<text x="'+(left-9)+'" y="'+(yy+3)+'" text-anchor="end" fill="#6b7d91" font-size="10">'+fmtTick(value)+'</text>');
    }
    paint.forEach((series,i)=>{
      const x=left+i*163;
      parts.push('<rect x="'+x+'" y="12" width="11" height="11" rx="2" fill="'+series.color+'"/>');
      parts.push('<text x="'+(x+16)+'" y="21" fill="#3c526f" font-size="11">'+series.label+'</text>');
    });
    data.forEach((row,i)=>{
      const center=left+(i+.5)*groupWidth;
      paint.forEach((series,j)=>{
        const value=numeric(row[series.key]);
        const barHeight=value/maximum*plotHeight;
        const x=center+(j-1)*(barWidth+gap)-barWidth/2;
        const barTop=baseline-barHeight;
        const barTitle=escapeText(row.store)+' · '+series.label+': '+fmtTick(value);
        parts.push('<rect x="'+x.toFixed(2)+'" y="'+barTop.toFixed(2)+'" width="'+barWidth+
          '" height="'+barHeight.toFixed(2)+'" rx="2" fill="'+series.color+'"><title>'+barTitle+'</title></rect>');
        const labelY=Math.max(top+10,barTop-6);
        parts.push('<text x="'+(x+barWidth/2).toFixed(2)+'" y="'+labelY.toFixed(2)+
          '" text-anchor="middle" font-size="9" font-weight="750" fill="'+series.color+
          '" paint-order="stroke" stroke="#fff" stroke-width="3">'+fmtTick(value)+'</text>');
      });
      parts.push('<text x="'+center.toFixed(2)+'" y="'+(baseline+22)+
        '" font-size="10" text-anchor="middle" fill="#29496c">'+escapeText(row.store)+'</text>');
      parts.push('<text x="'+center.toFixed(2)+'" y="'+(baseline+36)+
        '" font-size="9" text-anchor="middle" fill="#708197">#'+(i+1)+'</text>');
    });
    parts.push('</svg>');
    const textPeriod=escapeText(period||'Histórico');
    const textScope=escapeText(scope||'Todas las tiendas');
    return '<div class="chart-box chart-scroll or365-detail-chart" data-or365-chart="grouped-vertical">'+
      '<h3 class="or365-chart-title">Ingresos vs Acondicionado vs Ubicado · '+textScope+' · '+textPeriod+'</h3>'+
      '<div class="or365-chart-hint">Comparativo por tienda · desliza horizontalmente para ver todas las tiendas</div>'+
      parts.join('')+'</div>';
  };
})();
