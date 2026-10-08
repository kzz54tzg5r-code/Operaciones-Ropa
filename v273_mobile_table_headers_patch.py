"""V273.2 · Encabezados compactos universales para tablas en móvil/tablet.

- Sólo <=1024 px: escritorio queda intacto.
- Todas las tablas de reportes usan encabezados abreviados y de 2–3 líneas.
- Se usa altura del encabezado en lugar de ensanchar columnas.
- Tablas de hasta 12 columnas caben al ancho; tablas mayores conservan scroll interno,
  pero con columnas mucho más estrechas.
- No modifica datos, cálculos, filtros, ordenamientos ni endpoints.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V273_MOBILE_TABLE_HEADERS", False):
        return

    css = r'''<style id="v273-mobile-table-headers-css">
/* =========================================================
   V273 · TABLAS MOBILE/TABLET
   Alto antes que ancho: encabezados abreviados y multilínea.
   ========================================================= */
@media (max-width:1024px){
  /* Todos los contenedores de tablas se quedan dentro del viewport. */
  html body :is(
    .tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30,
    .monthly-cross-desktop,.lingerie-table-wrap,.rr243-tablewrap,
    .v240-matrix-wrap,.v240-route-calendar
  ){
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    overflow-x:auto!important;
    overflow-y:auto!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior:contain!important;
    touch-action:pan-x pan-y!important;
  }

  /* Fallback autoritativo: si el JS tarda o una tabla se repinta, no recuperar min-width heredado. */
  html body :is(.tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30,.monthly-cross-desktop,.lingerie-table-wrap,.rr243-tablewrap) > table.table{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    table-layout:fixed!important;
  }
  html body :is(.tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30,.monthly-cross-desktop,.lingerie-table-wrap,.rr243-tablewrap) > table.table thead th{
    white-space:normal!important;
    overflow-wrap:normal!important;
    word-break:normal!important;
    height:54px!important;
    min-height:54px!important;
    padding:3px 1px!important;
  }
  html body :is(.tablewrap,.model-sticky-table,.table-scroll-35,.model-scroll-30,.monthly-cross-desktop,.lingerie-table-wrap,.rr243-tablewrap) > table.table tbody td{
    min-width:0!important;
    padding-left:1.5px!important;
    padding-right:1.5px!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
  }

  /* Base universal para tablas de reportes. */
  html body table.v273-mobile-table{
    border-collapse:collapse!important;
    font-variant-numeric:tabular-nums!important;
  }

  /* <=12 columnas: prioridad absoluta a caber al ancho de móvil/tablet. */
  html body table.v273-mobile-table.v273-fit{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    table-layout:fixed!important;
  }

  /* Tablas realmente grandes: scroll interno, pero ya no 68–90 px por columna. */
  html body table.v273-mobile-table.v273-scroll{
    width:max-content!important;
    max-width:none!important;
    min-width:max(100%,calc(var(--v273-cols,13) * 78px))!important;
    table-layout:fixed!important;
  }

  /* Encabezados: más altos, angostos y centrados. */
  html body table.v273-mobile-table thead th{
    min-width:0!important;
    width:auto;
    height:54px!important;
    min-height:54px!important;
    max-height:none!important;
    padding:3px 1px!important;
    white-space:normal!important;
    word-break:normal!important;
    overflow-wrap:normal!important;
    hyphens:none!important;
    vertical-align:middle!important;
    text-align:center!important;
    font-size:7px!important;
    line-height:1.02!important;
    letter-spacing:0!important;
  }
  html body table.v273-mobile-table thead th.v273-left{
    text-align:left!important;
  }
  html body table.v273-mobile-table thead th .v273-head{
    display:flex!important;
    flex-direction:column!important;
    align-items:center!important;
    justify-content:center!important;
    width:100%!important;
    height:100%!important;
    min-width:0!important;
    gap:0!important;
  }
  html body table.v273-mobile-table thead th.v273-left .v273-head{
    align-items:flex-start!important;
  }
  html body table.v273-mobile-table thead th .v273-line{
    display:block!important;
    width:100%!important;
    min-width:0!important;
    white-space:nowrap!important;
    overflow:hidden!important;
    text-overflow:clip!important;
  }

  /* Celdas: densidad alta para conservar la matriz de laptop. */
  html body table.v273-mobile-table tbody td{
    min-width:0!important;
    padding:4px 2px!important;
    font-size:7px!important;
    line-height:1.04!important;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    word-break:normal!important;
    vertical-align:middle!important;
  }
  html body table.v273-mobile-table tbody td.v273-num{
    text-align:right!important;
    white-space:nowrap!important;
    overflow:hidden!important;
    text-overflow:clip!important;
    font-size:6.8px!important;
  }
  html body table.v273-mobile-table tbody td.v273-rank{
    text-align:center!important;
    white-space:nowrap!important;
  }

  /* Las reglas heredadas no deben volver a ensanchar estas tablas. */
  html body table.v273-mobile-table.v273-fit.v264-scroll-table,
  html body table.v273-mobile-table.v273-fit.v270-scroll-table,
  html body .rr243-table.v273-mobile-table.v273-fit,
  html body .monthly-cross-table.v273-mobile-table.v273-fit{
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    table-layout:fixed!important;
  }

  /* Categorías de la matriz principal pueden usar altura, no ancho. */
  html body table.v273-mobile-table .monthly-cat{
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    padding-left:2px!important;
    padding-right:2px!important;
  }
}

/* Tablet: algo más legible, misma lógica compacta. */
@media (min-width:701px) and (max-width:1024px){
  html body table.v273-mobile-table thead th{
    height:48px!important;
    min-height:48px!important;
    padding:4px 3px!important;
    font-size:8.3px!important;
  }
  html body table.v273-mobile-table tbody td{
    padding:5px 3px!important;
    font-size:8.2px!important;
  }
  html body table.v273-mobile-table tbody td.v273-num{
    font-size:8px!important;
  }
  html body table.v273-mobile-table.v273-scroll{
    min-width:max(100%,calc(var(--v273-cols,13) * 72px))!important;
  }
}

/* iPhone/Android: usa todavía más alto de cabecera y menos ancho. */
@media (max-width:700px){
  html body table.v273-mobile-table thead th{
    height:46px!important;
    min-height:46px!important;
    padding:3px 1px!important;
    font-size:6.2px!important;
    line-height:.98!important;
  }
  html body table.v273-mobile-table tbody td{
    padding:4px 1.5px!important;
    font-size:6.2px!important;
    line-height:1.02!important;
  }
  html body table.v273-mobile-table tbody td.v273-num{
    font-size:6px!important;
  }
  html body table.v273-mobile-table.v273-scroll{
    min-width:max(100%,calc(var(--v273-cols,13) * 86px))!important;
  }
}

/* Teléfonos muy angostos: 3 líneas son preferibles a ensanchar columnas. */
@media (max-width:430px){
  html body table.v273-mobile-table thead th{
    height:50px!important;
    min-height:50px!important;
    font-size:5.7px!important;
    padding:2px 1px!important;
  }
  html body table.v273-mobile-table tbody td{
    font-size:5.8px!important;
    padding:3.5px 1px!important;
  }
  html body table.v273-mobile-table tbody td.v273-num{
    font-size:5.6px!important;
  }
}

/* V290: only wide tables scroll; no number, price or percentage may wrap or crop. */
@media (max-width:1024px){
  html body :is(.tablewrap,.rr243-tablewrap,.monthly-cross-desktop,.model-sticky-table) > table.v273-mobile-table.v273-scroll{
    table-layout:auto!important;
    width:max-content!important;
    max-width:none!important;
  }
  html body table.v273-mobile-table.v273-scroll thead th{
    font-size:9px!important;
    line-height:1.15!important;
    height:40px!important;
    min-height:40px!important;
    padding:4px 6px!important;
  }
  html body table.v273-mobile-table.v273-scroll tbody td,
  html body table.v273-mobile-table.v273-scroll tbody td.v273-num{
    font-size:10px!important;
    line-height:1.18!important;
    white-space:nowrap!important;
    overflow:visible!important;
    overflow-wrap:normal!important;
    word-break:normal!important;
    padding:5px 7px!important;
    font-variant-numeric:tabular-nums!important;
  }
  html body table.v273-mobile-table.v273-scroll th .v273-line{
    white-space:nowrap!important;
    text-overflow:clip!important;
  }
}

/* V291 · Centro Operativo: matriz completa proporcional, sin importes rotos.
   El contenido sigue siendo la misma tabla con las mismas celdas. */
@media (max-width:700px){
  html body #operativoDynamicContent :is(.tablewrap,.rr243-tablewrap) > table.v273-mobile-table.v273-zoom {
    width:max-content!important;
    min-width:max-content!important;
    max-width:none!important;
    table-layout:auto!important;
    border-collapse:collapse!important;
  }
  html body #operativoDynamicContent table.v273-zoom thead th {
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    height:52px!important;
    min-height:52px!important;
    padding:8px 10px!important;
    font-size:14px!important;
    line-height:1.16!important;
    white-space:nowrap!important;
    word-break:normal!important;
    overflow:visible!important;
  }
  html body #operativoDynamicContent table.v273-zoom thead th .v273-line {
    white-space:nowrap!important;
    overflow:visible!important;
    text-overflow:clip!important;
  }
  html body #operativoDynamicContent table.v273-zoom tbody td,
  html body #operativoDynamicContent table.v273-zoom tbody td.v273-num,
  html body #operativoDynamicContent table.v273-zoom tbody td.v273-rank {
    width:auto!important;
    min-width:0!important;
    font-size:15px!important;
    line-height:1.18!important;
    padding:8px 10px!important;
    white-space:nowrap!important;
    overflow:visible!important;
    word-break:normal!important;
    overflow-wrap:normal!important;
    font-variant-numeric:tabular-nums!important;
  }
  html body #operativoDynamicContent table.v273-zoom tbody td b,
  html body #operativoDynamicContent table.v273-zoom tbody td span {
    white-space:nowrap!important;
    overflow-wrap:normal!important;
  }
  #operativoDynamicContent .v291-table-toolbar {
    display:flex;
    align-items:center;
    justify-content:flex-end;
    min-height:24px;
    margin:2px 0 3px;
    padding:0 2px;
    max-width:100%;
  }
  #operativoDynamicContent .v291-zoom-toggle {
    min-height:23px;
    border:1px solid #c9d9ed;
    background:#f1f7ff;
    color:#184e86;
    font-size:10px!important;
    line-height:1.1;
    font-weight:800;
    border-radius:7px;
    padding:4px 9px;
    cursor:pointer;
  }
  #operativoDynamicContent .v291-zoom-toggle:focus-visible{
    outline:2px solid #1376df;
    outline-offset:2px;
  }
}

/* V292 · Prevent an unreadable 10-16-column squeeze on iPhones.
   Keep every column; scroll only the grid, with frozen rank/store columns. */
@media (max-width:700px) {
  html body #operativoDynamicContent :is(.tablewrap,.rr243-tablewrap):has(>table.v273-scroll) {
    width:100%!important;
    min-width:0!important;
    max-width:100%!important;
    overflow-x:auto!important;
    overflow-y:auto!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-x:contain!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-x pan-y pinch-zoom!important;
    scrollbar-width:thin;
    scrollbar-color:#8ab1dc #eff5fa;
  }
  html body #operativoDynamicContent :is(.tablewrap,.rr243-tablewrap)>table.v273-scroll,
  html body #operativoDynamicContent :is(.tablewrap,.rr243-tablewrap)>table.v270-scroll-table.v273-scroll {
    display:table!important;
    zoom:1!important;
    width:max-content!important;
    min-width:max(100%,calc(var(--v273-cols,10)*86px))!important;
    max-width:none!important;
    table-layout:auto!important;
    border-collapse:separate!important;
    border-spacing:0!important;
  }
  html body #operativoDynamicContent table.v273-scroll thead th {
    width:auto!important;
    height:auto!important;
    min-height:45px!important;
    max-height:none!important;
    padding:8px 9px!important;
    font-size:11px!important;
    line-height:1.15!important;
    vertical-align:middle!important;
    white-space:nowrap!important;
    word-break:normal!important;
    overflow-wrap:normal!important;
  }
  html body #operativoDynamicContent table.v273-scroll tbody td,
  html body #operativoDynamicContent table.v273-scroll tbody td.v273-num,
  html body #operativoDynamicContent table.v273-scroll tbody td.v273-rank {
    width:auto!important;
    height:auto!important;
    min-height:32px!important;
    padding:8px 9px!important;
    font-size:11px!important;
    line-height:1.18!important;
    vertical-align:middle!important;
    white-space:nowrap!important;
    word-break:normal!important;
    overflow-wrap:normal!important;
    overflow:visible!important;
    text-overflow:clip!important;
    font-variant-numeric:tabular-nums!important;
  }
  html body #operativoDynamicContent table.v273-scroll tbody td :is(b,span,small) {
    white-space:nowrap!important;
    word-break:normal!important;
    overflow-wrap:normal!important;
    text-overflow:clip!important;
  }
  html body #operativoDynamicContent table.v273-scroll :is(th,td):first-child {
    position:sticky!important;
    left:0!important;
    z-index:3!important;
    min-width:47px!important;
    width:47px!important;
    box-shadow:1px 0 0 #c7d7e8;
    background:#fff!important;
  }
  html body #operativoDynamicContent table.v273-scroll :is(th,td):nth-child(2) {
    position:sticky!important;
    left:47px!important;
    z-index:3!important;
    min-width:145px!important;
    width:145px!important;
    max-width:145px!important;
    box-shadow:2px 0 4px rgba(5,41,81,.11);
    background:#fff!important;
  }
  html body #operativoDynamicContent table.v273-scroll thead th:first-child,
  html body #operativoDynamicContent table.v273-scroll thead th:nth-child(2) {
    z-index:5!important;
    background:#123b73!important;
    color:#fff!important;
  }
  html body #operativoDynamicContent table.v273-scroll tbody tr.project-row td:is(:first-child,:nth-child(2)) {
    background:#eaf3ff!important;
  }
  #operativoDynamicContent .v292-scroll-hint {
    width:100%;
    margin:7px 0 4px;
    color:#285e97;
    font-size:11px;
    font-weight:800;
    text-align:right;
    letter-spacing:0;
  }
}
@media (min-width:701px){
  #operativoDynamicContent .v292-scroll-hint {display:none!important;}
}
</style>'''

    js = r'''<script id="v273-mobile-table-headers-js">
(function(){
  if(window.__V273_MOBILE_TABLE_HEADERS)return;
  window.__V273_MOBILE_TABLE_HEADERS=true;

  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const norm=s=>String(s||'')
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/\s+/g,' ').trim().toLowerCase();

  const PHRASES=[
    [/piezas recuperadas/gi,'Pzas recup.'],
    [/pzas recuperadas/gi,'Pzas recup.'],
    [/piezas procesadas/gi,'Pzas proc.'],
    [/valor devoluci[oó]n/gi,'Valor dev.'],
    [/venta recuperada estimada/gi,'Vta recup. est.'],
    [/recuperaci[oó]n econ[oó]mica/gi,'Recup. $'],
    [/recuperaci[oó]n/gi,'Recup.'],
    [/conversi[oó]n/gi,'Conv.'],
    [/pendiente de acondicionar/gi,'Pend. acond.'],
    [/pendiente acondicionar/gi,'Pend. acond.'],
    [/pendiente de ubicar/gi,'Pend. ubic.'],
    [/pendiente ubicar/gi,'Pend. ubic.'],
    [/pendiente anterior/gi,'Pend. ant.'],
    [/recorridos realizados/gi,'Recorr. real.'],
    [/recorridos real/gi,'Recorr. real.'],
    [/total general/gi,'Total gral.'],
    [/stock total habilitado/gi,'Stock hab.'],
    [/stock final residual/gi,'Stock final'],
    [/stock inicial/gi,'Stock inic.'],
    [/precio promedio/gi,'Precio prom.'],
    [/venta total/gi,'Vta total'],
    [/existencia cedis/gi,'Exist. CEDIS'],
    [/existencia bodega/gi,'Exist. bod.'],
    [/existencia piso/gi,'Exist. piso'],
    [/existencia/gi,'Exist.'],
    [/tipo cat[aá]logo vigente/gi,'Cat. vig.'],
    [/tipo cat[aá]logo/gi,'Tipo cat.'],
    [/venta acumulada/gi,'Vta acum.'],
    [/a[nñ]o anterior/gi,'Año ant.'],
    [/cumplimiento/gi,'Cumpl.'],
    [/productividad/gi,'Prod.'],
    [/colaboradores/gi,'Colabs.'],
    [/colaborador/gi,'Colab.'],
    [/subcategor[ií]a/gi,'Subcat.'],
    [/participaci[oó]n/gi,'Part.'],
    [/acondicionado/gi,'Acond.'],
    [/acondicionar/gi,'Acond.'],
    [/ubicado/gi,'Ubic.'],
    [/ubicaci[oó]n/gi,'Ubic.'],
    [/devoluci[oó]n/gi,'Dev.'],
    [/sugerido/gi,'Sug.'],
    [/utilidad/gi,'Util.'],
    [/cantidad/gi,'Cant.'],
    [/promedio/gi,'Prom.'],
    [/ranking/gi,'Rank.'],
    [/categor[ií]a/gi,'Cat.'],
    [/indicador/gi,'Indic.'],
    [/piezas/gi,'Pzs'],
    [/pzas/gi,'Pzs'],
    [/realizados/gi,'Real.'],
    [/realizado/gi,'Real.'],
    [/pendiente/gi,'Pend.'],
    [/acumulada/gi,'Acum.'],
    [/acumulado/gi,'Acum.'],
    [/disponible/gi,'Disp.'],
    [/habilitado/gi,'Hab.']
  ];

  function compact(raw){
    let s=String(raw||'').replace(/\s+/g,' ').trim();
    PHRASES.forEach(([rx,to])=>{s=s.replace(rx,to)});
    s=s.replace(/\s*\/\s*/g,' / ').replace(/\s+/g,' ').trim();
    return s;
  }

  function linesFor(shortText,th){
    let words=String(shortText||'').split(' ').filter(Boolean);
    if(words.length<=1)return words.length?words:[''];

    // Encabezados monetarios y porcentuales se separan naturalmente.
    if(words.length===2)return words;
    if(words.length===3){
      if(words.join(' ').length<=13)return [words[0]+' '+words[1],words[2]];
      return words;
    }

    // Máximo 3 líneas: reparte palabras para usar alto sin ensanchar.
    const lines=['','',''];
    words.forEach((w,i)=>{
      const idx=i%3;
      lines[idx]=(lines[idx]+' '+w).trim();
    });
    return lines.filter(Boolean);
  }

  function weightFor(text,index){
    const n=norm(text);
    if(index===0 && (n==='#'||n.includes('rank')))return .48;
    if(n.includes('tienda')||n.includes('colab')||n.includes('modelo')||n.includes('descripcion')||n.includes('indic'))return 1.55;
    if(n.includes('$')||n.includes('valor')||n.includes('venta'))return 1.18;
    if(n.includes('fecha')||n.includes('periodo'))return 1.05;
    if(n.includes('%')||n.includes('pzs')||n.includes('dev')||n.includes('recup')||n.includes('meta'))return .86;
    return .95;
  }

  function decorate(table){
    if(!table || table.closest('.hidden'))return;
    const headRow=table.tHead?.rows?.[0] || table.querySelector('thead tr');
    if(!headRow)return;
    const ths=Array.from(headRow.cells).filter(c=>c.tagName==='TH');
    if(!ths.length)return;

    table.classList.add('v273-mobile-table');
    table.style.setProperty('--v273-cols',String(ths.length));
    // A 390px phone can read a six-column summary, not a ten-column ledger.
    // Keep desktop/tablet parity but never squeeze currency into broken digits.
    const viewport=window.innerWidth||document.documentElement.clientWidth||1024;
    const fitLimit=viewport<=360?5:viewport<=700?6:viewport<=900?9:12;
    // Centro Operativo: miniatura fiel de la tabla para evitar cifras partidas.
    // El botón de ampliación permite leer cualquier columna a tamaño completo.
    // Wide operational reports must remain readable, not scaled to a 390px screen.
    // Their scroll container keeps the complete laptop column structure.
    const centerWide=false;
    const fits=ths.length<=fitLimit;
    table.classList.toggle('v273-fit',fits);
    table.classList.toggle('v273-scroll',!fits && !centerWide);
    table.classList.toggle('v273-zoom',centerWide);
    if(!centerWide && table.dataset.v291Measured!==undefined){
      table.style.removeProperty('zoom');
      delete table.dataset.v291Measured;
      delete table.dataset.v291Expanded;
      const previous=table.parentElement?.previousElementSibling;
      if(previous?.classList.contains('v291-table-toolbar'))previous.remove();
    }

    if(centerWide){
      table.style.setProperty('width','max-content','important');
      table.style.setProperty('min-width','max-content','important');
      table.style.setProperty('max-width','none','important');
      table.style.setProperty('table-layout','auto','important');
      const wrap=table.parentElement;
      if(wrap){
        wrap.style.setProperty('max-width','100%','important');
        wrap.style.setProperty('overflow-x','hidden','important');
      }
    }else if(fits){
      table.style.setProperty('width','100%','important');
      table.style.setProperty('min-width','0','important');
      table.style.setProperty('max-width','100%','important');
      table.style.setProperty('table-layout','fixed','important');
      const wrap=table.parentElement;
      if(wrap){
        wrap.style.setProperty('width','100%','important');
        wrap.style.setProperty('max-width','100%','important');
        wrap.style.setProperty('min-width','0','important');
        wrap.style.setProperty('overflow-x','hidden','important');
      }
    }else{
      // Remove previous forced-fit inline !important rules after viewport/period changes.
      ['width','min-width','max-width','table-layout'].forEach(prop=>table.style.removeProperty(prop));
      const wrap=table.parentElement;
      if(wrap){
        ['width','max-width','min-width','overflow-x'].forEach(prop=>wrap.style.removeProperty(prop));
        wrap.style.setProperty('overflow-x','auto','important');
        wrap.style.setProperty('-webkit-overflow-scrolling','touch');
      }
    }

    const weights=[];
    ths.forEach((th,index)=>{
      const interactive=th.querySelector('button,input,select,a,[onclick]');
      const raw=th.dataset.v273Original || th.textContent.trim();
      if(!th.dataset.v273Original)th.dataset.v273Original=raw;
      const short=compact(raw);
      weights.push(weightFor(short,index));

      const left = norm(raw).includes('tienda') || norm(raw).includes('colab') ||
                   norm(raw).includes('modelo') || norm(raw).includes('indic') ||
                   norm(raw).includes('descripcion');
      th.classList.toggle('v273-left',left);
      th.title=raw;

      if(!interactive){
        // With horizontal scrolling there is space for real, readable labels.
        // Old multiline headers are restored if the viewport changes.
        if(!fits){
          if(th.dataset.v273Signature || th.textContent.trim()!==raw){
            th.textContent=raw;
            delete th.dataset.v273Signature;
          }
        }else{
          const lines=linesFor(short,th);
          const signature=lines.join('|');
          if(th.dataset.v273Signature!==signature){
            th.innerHTML='<span class="v273-head">'+lines.map(x=>'<span class="v273-line">'+
              String(x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))+
            '</span>').join('')+'</span>';
            th.dataset.v273Signature=signature;
          }
        }
      }
    });

    if(centerWide){
      ths.forEach(th=>th.style.removeProperty('width'));
      scaleCenterTable(table);
    }else if(fits){
      const total=weights.reduce((a,b)=>a+b,0)||1;
      ths.forEach((th,i)=>{
        th.style.setProperty('width',(weights[i]/total*100).toFixed(2)+'%','important');
      });
    }else{
      ths.forEach(th=>th.style.removeProperty('width'));
      const wrap=table.parentElement;
      const operational=viewport<=700 && !!table.closest('#operativoDynamicContent') &&
        !!table.closest('.tablewrap,.rr243-tablewrap,.monthly-cross-desktop');
      if(operational && wrap){
        let hint=wrap.previousElementSibling;
        if(!hint?.classList.contains('v292-scroll-hint')){
          hint=document.createElement('div');
          hint.className='v292-scroll-hint';
          hint.textContent='← Desliza para ver todas las columnas →';
          wrap.before(hint);
        }
        hint.setAttribute('role','note');
        wrap.setAttribute('role','region');
        wrap.setAttribute('tabindex','0');
        wrap.setAttribute('aria-label','Tabla operativa, desliza horizontalmente para leer todas las columnas');
      }else if(wrap){
        const hint=wrap.previousElementSibling;
        if(hint?.classList.contains('v292-scroll-hint'))hint.remove();
      }
    }

    // Clasificación de cuerpo para mantener números compactos.
    qa('tbody tr',table).forEach(row=>{
      Array.from(row.cells).forEach((td,index)=>{
        const txt=td.textContent.trim();
        const header=ths[index]?.dataset.v273Original||'';
        const hn=norm(header);
        const numeric=/^[-+]?[$€£]?\s*[\d,.]+\s*%?$/.test(txt.replace(/\s+/g,' '));
        td.classList.toggle('v273-num',numeric || hn.includes('%') || hn.includes('$') || hn.includes('pzs') || hn.includes('valor'));
        td.classList.toggle('v273-rank',index===0 && (hn==='#'||hn.includes('rank')));
      });
    });
  }

  function scaleCenterTable(table){
    const wrap=table.parentElement;
    if(!wrap)return;
    let toolbar=wrap.previousElementSibling;
    if(!toolbar || !toolbar.classList.contains('v291-table-toolbar')){
      toolbar=document.createElement('div');
      toolbar.className='v291-table-toolbar';
      const button=document.createElement('button');
      button.type='button';
      button.className='v291-zoom-toggle';
      toolbar.appendChild(button);
      wrap.parentElement?.insertBefore(toolbar,wrap);
      button.addEventListener('click',()=>{
        table.dataset.v291Expanded=table.dataset.v291Expanded==='1'?'0':'1';
        delete table.dataset.v291Measured;
        scaleCenterTable(table);
      });
    }
    const button=toolbar.querySelector('button');
    const expanded=table.dataset.v291Expanded==='1';
    if(button){
      button.textContent=expanded?'Ajustar a pantalla':'Ampliar tabla';
      button.setAttribute('aria-pressed',String(expanded));
      button.setAttribute('aria-label',expanded?'Mostrar todas las columnas al ancho del teléfono':'Ampliar tabla para leer sus cifras sin reducir');
    }
    const available=Math.max(0,wrap.clientWidth-2);
    const signature=available+'|'+table.rows.length+'|'+expanded;
    if(table.dataset.v291Measured===signature)return;
    table.style.setProperty('zoom','1','important');
    wrap.style.setProperty('overflow-x',expanded?'auto':'hidden','important');
    const natural=table.getBoundingClientRect().width;
    if(!expanded && available>0 && natural>0){
      let factor=Math.min(1,(available/natural)*.96);
      // CSS zoom redondea anchos intrínsecos; dejar margen evita cortar
      // la última columna en Safari y navegadores con zoom de texto.
      table.style.setProperty('zoom',String(Math.max(.01,Math.floor(factor*10000)/10000)),'important');
      const actual=table.getBoundingClientRect().width;
      if(actual>available){
        factor=Math.max(.01,factor*(available/actual)*.98);
        table.style.setProperty('zoom',String(Math.floor(factor*10000)/10000),'important');
      }
    }
    table.dataset.v291Measured=signature;
  }

  function restoreDesktop(table){
    if(!table)return;
    table.classList.remove('v273-mobile-table','v273-fit','v273-scroll','v273-zoom');
    table.style.removeProperty('zoom');
    delete table.dataset.v291Measured;
    delete table.dataset.v291Expanded;
    const toolbar=table.parentElement?.previousElementSibling;
    if(toolbar?.classList.contains('v291-table-toolbar'))toolbar.remove();
    table.style.removeProperty('--v273-cols');
    table.style.removeProperty('width');
    table.style.removeProperty('min-width');
    table.style.removeProperty('max-width');
    table.style.removeProperty('table-layout');
    const wrap=table.parentElement;
    if(wrap){
      wrap.style.removeProperty('width');
      wrap.style.removeProperty('max-width');
      wrap.style.removeProperty('min-width');
      wrap.style.removeProperty('overflow-x');
    }
    qa('thead th',table).forEach(th=>{
      if(th.dataset.v273Original){
        th.textContent=th.dataset.v273Original;
        delete th.dataset.v273Signature;
      }
      th.classList.remove('v273-left');
      th.style.removeProperty('width');
    });
    qa('tbody td',table).forEach(td=>td.classList.remove('v273-num','v273-rank'));
  }

  function scan(){
    const mobileTablet=matchMedia('(max-width:1024px)').matches;
    qa('table').forEach(table=>mobileTablet?decorate(table):restoreDesktop(table));
  }

  let timer=0;
  function queue(ms=30){
    clearTimeout(timer);
    timer=setTimeout(scan,ms);
  }

  const observer=new MutationObserver(()=>queue(35));
  function start(){
    const root=document.querySelector('#appView')||document.body;
    observer.observe(root,{subtree:true,childList:true});
    scan();
    [100,300,700,1400,2400].forEach(ms=>setTimeout(scan,ms));
  }

  document.addEventListener('click',()=>[40,160,400].forEach(ms=>setTimeout(scan,ms)),true);
  document.addEventListener('change',()=>[40,160,400].forEach(ms=>setTimeout(scan,ms)),true);
  window.addEventListener('resize',()=>queue(20),{passive:true});
  window.addEventListener('orientationchange',()=>[80,260,600].forEach(ms=>setTimeout(scan,ms)),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(scan,80),{passive:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V273.2] encabezados compactos sólo móvil/tablet; escritorio restaurado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v273_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v273-mobile-table-headers-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v273-mobile-table-headers-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)

            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V273-MOBILE-TABLE-HEADERS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V273] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V273_MOBILE_TABLE_HEADERS=True
    print("[V273.2] Tablas compactas limitadas a móvil/tablet; escritorio sin estilos inline heredados.",flush=True)
