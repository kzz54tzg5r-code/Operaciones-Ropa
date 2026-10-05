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
    min-width:max(100%,calc(var(--v273-cols,13) * 44px))!important;
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
    min-width:max(100%,calc(var(--v273-cols,13) * 55px))!important;
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
    min-width:max(100%,calc(var(--v273-cols,13) * 39px))!important;
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
    table.classList.toggle('v273-fit',ths.length<=16);
    table.classList.toggle('v273-scroll',ths.length>16);

    if(ths.length<=16){
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
        const lines=linesFor(short,th);
        const signature=lines.join('|');
        if(th.dataset.v273Signature!==signature){
          th.innerHTML='<span class="v273-head">'+lines.map(x=>'<span class="v273-line">'+
            String(x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))+
          '</span>').join('')+'</span>';
          th.dataset.v273Signature=signature;
        }
      }
    });

    if(ths.length<=16){
      const total=weights.reduce((a,b)=>a+b,0)||1;
      ths.forEach((th,i)=>{
        th.style.setProperty('width',(weights[i]/total*100).toFixed(2)+'%','important');
      });
    }else{
      ths.forEach(th=>th.style.removeProperty('width'));
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

  function restoreDesktop(table){
    if(!table)return;
    table.classList.remove('v273-mobile-table','v273-fit','v273-scroll');
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
