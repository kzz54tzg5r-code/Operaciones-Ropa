"""V267 · Tabla Centro Operativo estilo Opción 7.

Capa exclusivamente visual:
- transforma .monthly-cross-table al diseño Opción 7 aprobado;
- agrega iconos/secciones sin tocar valores ni cálculos;
- adapta ancho, tipografía y espaciado a desktop/tablet/móvil; V267.2 compacta y fusiona Valor/Piezas.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V267_OPTION7_MONTHLY_TABLE", False):
        return

    css = r'''<style id="v267-option7-monthly-table-css">
/* =========================================================
   V267 · OPCIÓN 7 · TABLA CENTRO OPERATIVO
   ========================================================= */

.monthly-cross-desktop.v267-option7-wrap{
  width:min(100%,1080px)!important;
  max-width:1080px!important;
  margin:0 0 10px!important;
  padding:0!important;
  border:0!important;
  border-radius:16px!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  background:transparent!important;
  box-shadow:none!important;
  -webkit-overflow-scrolling:touch!important;
}

.monthly-cross-table.v267-option7{
  width:100%!important;
  min-width:720px!important;
  max-width:1080px!important;
  table-layout:fixed!important;
  border-collapse:separate!important;
  border-spacing:0!important;
  background:transparent!important;
  color:#173B73!important;
  font-variant-numeric:tabular-nums!important;
}

/* Distribución de columnas: aprovecha el ancho sin deformar. */
.monthly-cross-table.v267-option7 th:nth-child(1){width:15%!important}
.monthly-cross-table.v267-option7 th:nth-child(2){width:30%!important}
.monthly-cross-table.v267-option7 th:nth-child(3){width:19%!important}
.monthly-cross-table.v267-option7 th:nth-child(4){width:10%!important}
.monthly-cross-table.v267-option7 th:nth-child(5){width:11%!important}
.monthly-cross-table.v267-option7 th:nth-child(6){width:15%!important}

/* Encabezado */
.monthly-cross-table.v267-option7 thead th{
  position:sticky!important;
  top:0!important;
  z-index:3!important;
  height:36px!important;
  padding:5px clamp(6px,.55vw,9px)!important;
  border:0!important;
  border-right:1px solid rgba(255,255,255,.13)!important;
  background:linear-gradient(100deg,#0a3e75 0%,#0b5597 100%)!important;
  color:#fff!important;
  font-size:clamp(12px,.76vw,15px)!important;
  line-height:1!important;
  font-weight:950!important;
  text-align:left!important;
  white-space:nowrap!important;
  box-shadow:none!important;
}
.monthly-cross-table.v267-option7 thead th:first-child{
  border-radius:14px 0 0 0!important;
}
.monthly-cross-table.v267-option7 thead th:last-child{
  border-right:0!important;
  border-radius:0 14px 0 0!important;
}
.monthly-cross-table.v267-option7 thead th:nth-child(n+3){
  text-align:center!important;
}

/* Cuerpo */
.monthly-cross-table.v267-option7 tbody td{
  height:29px!important;
  min-height:29px!important;
  padding:3px clamp(6px,.55vw,9px)!important;
  border:0!important;
  border-bottom:1px solid #dbe6f2!important;
  background:#fff!important;
  color:#294667!important;
  font-size:clamp(12px,.76vw,15px)!important;
  line-height:1.08!important;
  vertical-align:middle!important;
}
.monthly-cross-table.v267-option7 tbody td:nth-child(n+3){
  text-align:center!important;
}
.monthly-cross-table.v267-option7 tbody td:nth-child(2){
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}
.monthly-cross-table.v267-option7 tbody td,
.monthly-cross-table.v267-option7 thead th{
  letter-spacing:0!important;
}
.monthly-cross-table.v267-option7 .monthly-cat{
  white-space:normal!important;
}
.monthly-cross-table.v267-option7 .monthly-cat br{
  display:none!important;
}
.monthly-cross-table.v267-option7 .monthly-cat span:not(.v267-cat-icon){
  display:block!important;
}
.monthly-cross-table.v267-option7 tbody td b{
  color:#173B73!important;
  font-size:clamp(12px,.76vw,15px)!important;
  line-height:1.02!important;
  font-weight:900!important;
}
.monthly-cross-table.v267-option7 .mct-value-pieces{
  display:inline-flex!important;
  align-items:baseline!important;
  justify-content:center!important;
  gap:5px!important;
  max-width:100%!important;
  white-space:nowrap!important;
}
.monthly-cross-table.v267-option7 .mct-value-pieces small{
  color:#69809a!important;
  font-size:clamp(9px,.58vw,11px)!important;
  line-height:1!important;
  font-weight:750!important;
}
.monthly-cross-table.v267-option7 tbody tr:not(.v267-total-operation):not(.v267-total-pending):not(.v267-general-total):hover td:not(.monthly-cat){
  background:#f8fbff!important;
}

/* Categorías tipo Opción 7 */
.monthly-cross-table.v267-option7 .monthly-cat{
  position:relative!important;
  padding:5px 6px!important;
  text-align:center!important;
  font-size:clamp(14px,.9vw,18px)!important;
  line-height:1.05!important;
  font-weight:950!important;
  letter-spacing:.005em!important;
  border-bottom:0!important;
  border-radius:12px 0 0 12px!important;
  overflow:hidden!important;
}
.monthly-cross-table.v267-option7 .monthly-cat span:not(.v267-cat-icon){
  display:inline-block!important;
  margin-top:3px!important;
  font-size:clamp(11px,.7vw,14px)!important;
  font-weight:850!important;
}
.monthly-cross-table.v267-option7 .monthly-cat.v267-operation-cat{
  color:#047857!important;
  background:linear-gradient(105deg,#e6fbf2 0%,#f3fff9 100%)!important;
  box-shadow:inset 7px 0 0 #35d17d!important;
}
.monthly-cross-table.v267-option7 .monthly-cat.v267-pending-cat{
  color:#c2410c!important;
  background:linear-gradient(105deg,#fff0df 0%,#fff8f0 100%)!important;
  box-shadow:inset 7px 0 0 #ff8a1f!important;
}
.monthly-cross-table.v267-option7 .monthly-cat.v267-progress-cat{
  color:#6d28d9!important;
  background:linear-gradient(105deg,#f1e9ff 0%,#faf7ff 100%)!important;
  box-shadow:inset 7px 0 0 #8b5cf6!important;
}

/* Iconos de categoría */
.monthly-cross-table.v267-option7 .v267-cat-icon{
  display:grid!important;
  place-items:center!important;
  width:26px!important;
  height:26px!important;
  margin:0 auto 3px!important;
  border-radius:50%!important;
}
.monthly-cross-table.v267-option7 .v267-cat-icon svg{
  width:15px!important;
  height:15px!important;
  display:block!important;
}
.monthly-cross-table.v267-option7 .v267-operation-cat .v267-cat-icon{
  color:#07865e!important;
  background:#c9f5df!important;
}
.monthly-cross-table.v267-option7 .v267-pending-cat .v267-cat-icon{
  color:#d64b0b!important;
  background:#ffe0c2!important;
}
.monthly-cross-table.v267-option7 .v267-progress-cat .v267-cat-icon{
  color:#6d28d9!important;
  background:#e8dcff!important;
}

/* Separación visual entre bloques. */
.monthly-cross-table.v267-option7 tr.v267-group-start:not(:first-child) > td{
  border-top:2px solid #f3f7fb!important;
}
.monthly-cross-table.v267-option7 tr.v267-general-total > td{
  border-top:2px solid #f3f7fb!important;
}

/* Totales por bloque */
.monthly-cross-table.v267-option7 tr.v267-total-operation td{
  background:linear-gradient(90deg,#e9faf3 0%,#f4fffa 100%)!important;
  color:#0a6f55!important;
  border-bottom:0!important;
}
.monthly-cross-table.v267-option7 tr.v267-total-operation td b{
  color:#0a6f55!important;
}
.monthly-cross-table.v267-option7 tr.v267-total-pending td{
  background:linear-gradient(90deg,#fff0df 0%,#fff7ee 100%)!important;
  color:#c2410c!important;
  border-bottom:0!important;
}
.monthly-cross-table.v267-option7 tr.v267-total-pending td b{
  color:#c2410c!important;
}

/* Total General independiente */
.monthly-cross-table.v267-option7 tr.v267-general-total td{
  height:32px!important;
  background:linear-gradient(100deg,#dcebff 0%,#edf6ff 100%)!important;
  color:#0d4b91!important;
  border-top:2px solid #f3f7fb!important;
  border-bottom:0!important;
  font-weight:950!important;
}
.monthly-cross-table.v267-option7 tr.v267-general-total td:first-child{
  border-radius:12px 0 0 12px!important;
  box-shadow:inset 7px 0 0 #4097f5!important;
}
.monthly-cross-table.v267-option7 tr.v267-general-total td:last-child{
  border-radius:0 12px 12px 0!important;
}
.monthly-cross-table.v267-option7 tr.v267-general-total td b{
  color:#0d4b91!important;
  font-size:clamp(14px,.9vw,18px)!important;
}

/* Icono Total General */
.monthly-cross-table.v267-option7 .v267-general-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:24px!important;
  height:24px!important;
  margin-right:6px!important;
  border-radius:8px!important;
  color:#1675d1!important;
  background:#cae4ff!important;
  vertical-align:middle!important;
}
.monthly-cross-table.v267-option7 .v267-general-icon svg{
  width:15px!important;
  height:15px!important;
}

/* Último bloque */
.monthly-cross-table.v267-option7 tr.v267-progress-last td{
  border-bottom:0!important;
}
.monthly-cross-table.v267-option7 tr.v267-progress-last td:last-child{
  border-radius:0 0 12px 0!important;
}

/* Pantallas anchas: un poco más de aire, sin desperdiciar espacio. */
@media(min-width:1500px){
  .monthly-cross-table.v267-option7 tbody td{
    height:36px!important;
    padding-top:4px!important;
    padding-bottom:4px!important;
  }
  .monthly-cross-table.v267-option7 .monthly-cat{
    padding-left:20px!important;
    padding-right:20px!important;
  }
}

/* Laptop/tablet landscape */
@media(min-width:701px) and (max-width:1199px){
  .monthly-cross-table.v267-option7{
    min-width:700px!important;
  }
  .monthly-cross-table.v267-option7 thead th{
    height:32px!important;
    padding:4px 6px!important;
    font-size:10.5px!important;
  }
  .monthly-cross-table.v267-option7 tbody td{
    height:27px!important;
    padding:3px 6px!important;
    font-size:10.5px!important;
  }
  .monthly-cross-table.v267-option7 tbody td b{
    font-size:12px!important;
  }
  .monthly-cross-table.v267-option7 .monthly-cat{
    font-size:12px!important;
  }
  .monthly-cross-table.v267-option7 .v267-cat-icon{
    width:28px!important;
    height:28px!important;
    margin-bottom:4px!important;
  }
  .monthly-cross-table.v267-option7 .v267-cat-icon svg{
    width:16px!important;
    height:16px!important;
  }
}

/* Móvil: conservar la versión vertical existente, pero con identidad Opción 7 */
@media(max-width:700px){
  .monthly-cross-mobile{
    border:0!important;
    background:transparent!important;
    overflow:visible!important;
  }
  .mct-mobile-head{
    border-radius:11px 11px 0 0!important;
    background:linear-gradient(100deg,#0a3e75,#0b5597)!important;
  }
  .mct-mobile-section{
    position:relative!important;
    margin-top:8px!important;
    padding:9px 10px 9px 15px!important;
    border:1px solid #dbe6f2!important;
    border-bottom:0!important;
    border-radius:11px 11px 0 0!important;
  }
  .mct-mobile-section::before{
    content:""!important;
    position:absolute!important;
    left:0!important;
    top:0!important;
    bottom:0!important;
    width:5px!important;
    border-radius:11px 0 0 0!important;
  }
  .mct-mobile-section.operation::before{background:#35d17d!important}
  .mct-mobile-section.pending::before{background:#ff8a1f!important}
  .mct-mobile-section.progress::before{background:#8b5cf6!important}
  .mct-mobile-row{
    background:#fff!important;
    border-left:1px solid #dbe6f2!important;
    border-right:1px solid #dbe6f2!important;
  }
  .mct-mobile-row.mct-total{
    background:#eafaf4!important;
  }
  .mct-mobile-row.mct-pending-total{
    background:#fff2e5!important;
  }
  .mct-mobile-row.mct-general{
    margin-top:8px!important;
    border:1px solid #c9def7!important;
    border-left:5px solid #4097f5!important;
    border-radius:10px!important;
    background:#e6f2ff!important;
  }
}
</style>'''

    js = r'''<script id="v267-option7-monthly-table-js">
(function(){
  if(window.__V267_OPTION7_MONTHLY_TABLE)return;
  window.__V267_OPTION7_MONTHLY_TABLE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toUpperCase();

  const ICON_BOX='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/><path d="M12 11v10"/></svg>';
  const ICON_CLIP='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M9 9h6M9 13h6M9 17h4"/></svg>';
  const ICON_CHART='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 20V11M10 20V5M16 20v-8M22 20V8"/></svg>';
  const ICON_LAYERS='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></svg>';

  function iconSpan(svg,cls='v267-cat-icon'){
    return '<span class="'+cls+'" aria-hidden="true">'+svg+'</span>';
  }

  function decorate(table){
    if(!table)return;
    table.classList.add('v267-option7');
    const wrap=table.closest('.monthly-cross-desktop');
    if(wrap)wrap.classList.add('v267-option7-wrap');

    const rows=qa('tbody tr',table);
    rows.forEach(row=>{
      const cells=qa(':scope > td',row);
      if(!cells.length)return;
      const firstText=norm(cells[0]?.textContent);
      const fullText=norm(row.textContent);

      const cat=cells.find(td=>td.classList.contains('monthly-cat'));
      if(cat){
        const catText=norm(cat.textContent);
        row.classList.add('v267-group-start');
        if(catText.includes('OPERACIÓN')||catText.includes('OPERACION')){
          cat.classList.add('v267-operation-cat');
          if(!q('.v267-cat-icon',cat))cat.insertAdjacentHTML('afterbegin',iconSpan(ICON_BOX));
        }else if(catText.includes('PENDIENTES')){
          cat.classList.add('v267-pending-cat');
          if(!q('.v267-cat-icon',cat))cat.insertAdjacentHTML('afterbegin',iconSpan(ICON_CLIP));
        }else if(catText.includes('AVANCE')){
          cat.classList.add('v267-progress-cat');
          if(!q('.v267-cat-icon',cat))cat.insertAdjacentHTML('afterbegin',iconSpan(ICON_CHART));
        }
      }

      if(fullText.includes('TOTAL OPERACIÓN')||fullText.includes('TOTAL OPERACION')){
        row.classList.add('v267-total-operation');
      }
      if(fullText.includes('TOTAL PENDIENTES')){
        row.classList.add('v267-total-pending');
      }
      if(fullText.includes('TOTAL GENERAL')){
        row.classList.add('v267-general-total');
        const first=cells[0];
        if(first&&!q('.v267-general-icon',first)){
          const b=q('b',first);
          if(b)b.insertAdjacentHTML('afterbegin',iconSpan(ICON_LAYERS,'v267-general-icon'));
          else first.insertAdjacentHTML('afterbegin',iconSpan(ICON_LAYERS,'v267-general-icon'));
        }
      }
      if(fullText.includes('% UBICADO'))row.classList.add('v267-progress-last');
    });
  }

  function scan(){
    qa('.monthly-cross-table').forEach(decorate);
  }

  let timer=0;
  const obs=new MutationObserver(()=>{
    clearTimeout(timer);
    timer=setTimeout(scan,20);
  });

  function start(){
    scan();
    const root=q('#operativoDynamicContent')||q('#operativoDynamic')||document.body;
    obs.observe(root,{subtree:true,childList:true});
    [80,250,600,1200].forEach(ms=>setTimeout(scan,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V267] Tabla Centro Operativo · Opción 7 activa.');
})();
</script>'''

    @m.app.middleware("http")
    async def v267_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v267-option7-monthly-table-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v267-option7-monthly-table-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V267-OPTION7-TABLE",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V267] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V267_OPTION7_MONTHLY_TABLE=True
    print("[V267] Tabla Centro Operativo estilo Opción 7 instalada.",flush=True)
