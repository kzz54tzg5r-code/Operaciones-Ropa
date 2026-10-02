"""V234 · Ajuste visual exacto de pestañas móviles contra el mockup aprobado."""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V234_EXACT_MOBILE_TABS", False):
        return

    css = r'''<style id="v234-exact-mobile-tabs-css">
@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs{
    --v234-h:72px;
    --v234-gap:3px;
    display:grid!important;
    grid-template-rows:var(--v234-h)!important;
    height:var(--v234-h)!important;
    min-height:var(--v234-h)!important;
    max-height:var(--v234-h)!important;
    column-gap:var(--v234-gap)!important;
    margin:5px 0 12px!important;
    padding:0 3px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button{
    display:flex!important;
    flex-direction:column!important;
    align-items:center!important;
    justify-content:center!important;
    gap:4px!important;
    height:var(--v234-h)!important;
    min-height:var(--v234-h)!important;
    max-height:var(--v234-h)!important;
    padding:5px 1px 6px!important;
    border-radius:11px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon{
    display:grid!important;
    place-items:center!important;
    width:23px!important;
    min-width:23px!important;
    max-width:23px!important;
    height:23px!important;
    min-height:23px!important;
    max-height:23px!important;
    flex:0 0 23px!important;
    margin:0!important;
    padding:0!important;
    border:0!important;
    border-radius:0!important;
    background:transparent!important;
    color:#17477f!important;
    box-shadow:none!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-icon svg{
    width:100%!important;
    height:100%!important;
    max-width:100%!important;
    max-height:100%!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button.active .v232-tab-icon,
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs>button[aria-selected="true"] .v232-tab-icon{
    color:#fff!important;
    background:transparent!important;
    border:0!important;
  }
  body[data-v163-module="operativo"] #operativoNav.v232-mobile-tabs .v232-tab-label{
    display:block!important;
    width:100%!important;
    height:auto!important;
    min-height:0!important;
    max-height:34px!important;
    margin:0!important;
    padding:0!important;
    overflow:hidden!important;
    white-space:pre-line!important;
    overflow-wrap:normal!important;
    word-break:normal!important;
    hyphens:none!important;
    text-align:center!important;
    font-size:7.5px!important;
    line-height:1.06!important;
    font-weight:900!important;
    letter-spacing:0!important;
  }

  body[data-v163-module="analysis"] #analysisNav.v232-mobile-tabs{
    --v234-analysis-h:72px;
    display:grid!important;
    grid-template-rows:var(--v234-analysis-h)!important;
    height:var(--v234-analysis-h)!important;
    min-height:var(--v234-analysis-h)!important;
    max-height:var(--v234-analysis-h)!important;
    column-gap:4px!important;
    margin:5px 0 12px!important;
    padding:0 3px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="analysis"] #analysisNav.v232-mobile-tabs>button{
    display:flex!important;
    flex-direction:column!important;
    align-items:center!important;
    justify-content:center!important;
    gap:0!important;
    height:var(--v234-analysis-h)!important;
    min-height:var(--v234-analysis-h)!important;
    max-height:var(--v234-analysis-h)!important;
    padding:7px 4px!important;
    border-radius:13px!important;
    overflow:hidden!important;
  }
  body[data-v163-module="analysis"] #analysisNav.v232-mobile-tabs .v232-tab-icon{
    display:none!important;
  }
  body[data-v163-module="analysis"] #analysisNav.v232-mobile-tabs .v232-tab-label{
    display:flex!important;
    align-items:center!important;
    justify-content:center!important;
    width:100%!important;
    height:100%!important;
    min-height:100%!important;
    max-height:100%!important;
    margin:0!important;
    padding:0!important;
    overflow:hidden!important;
    white-space:normal!important;
    overflow-wrap:normal!important;
    word-break:normal!important;
    hyphens:none!important;
    text-align:center!important;
    font-size:8.8px!important;
    line-height:1.12!important;
    font-weight:900!important;
    letter-spacing:0!important;
  }

  body[data-v163-module="operation"] #v200OperationTabs.v232-mobile-tabs .v232-tab-icon{
    border:0!important;
    border-radius:0!important;
    background:transparent!important;
  }
}
</style>'''

    js = r'''<script id="v234-exact-mobile-tabs-js">
(function(){
  if(window.__V234_EXACT_MOBILE_TABS)return;
  window.__V234_EXACT_MOBILE_TABS=true;
  const mobile=()=>window.matchMedia?.('(max-width:900px)')?.matches ?? window.innerWidth<=900;
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();

  function currentModule(){
    let m='';
    try{m=String(MAIN||'').toLowerCase()}catch(_){}
    if(m)return m==='commercial'?'analysis':m;
    return String(document.body.dataset.v163Module||'').toLowerCase();
  }

  function cmLabel(btn){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview);
    const raw=norm(btn.dataset.v232Original||btn.dataset.rtLabel||btn.title||btn.textContent);
    if(key==='operations.center'||raw.includes('centro operativo')||raw.includes('centro ejecutivo'))return'Centro\nOperativo';
    if(raw==='operacion'||raw.startsWith('operacion '))return'Operación';
    if(key==='operations.conversion'||op.includes('convers')||raw.includes('conversion'))return'Conversión';
    if(key==='operations.recovery'||op.includes('recuperacion economica')||raw.includes('recuperacion $'))return'Recupera-\nciones';
    if(key==='operations.recovery_store'||op.includes('recuperacion por tienda')||raw.includes('recuperacion por tienda'))return'Recuperac.\npor Tienda';
    if(raw.includes('cargar productividad'))return'Cargar\nProductividad';
    if(key==='operations.productivity'||op.includes('productividad')||raw==='productividad')return'Producti-\nvidad';
    if(key==='operations.routes'||op.includes('recorridos')||raw.includes('recorridos'))return'Recorridos';
    if(op.includes('carga de datos')||raw.includes('carga de datos'))return'Carga de\ndatos';
    if(btn.id==='openGoalsBtn'||raw.includes('metas y tiendas')||raw==='metas')return'Metas y\ntiendas';
    return String(btn.dataset.rtLabel||btn.title||btn.textContent||'').replace(/\s+/g,' ').trim();
  }

  function analysisLabel(btn){
    const key=String(btn.dataset.tabKey||'');
    const sub=String(btn.dataset.sub||'').toLowerCase();
    const raw=norm(btn.dataset.v232Original||btn.dataset.rtLabel||btn.title||btn.textContent);
    if(key==='commercial.macro'||sub==='macro'||raw.includes('macro compania'))return'Macro compañía';
    if(key==='commercial.accordion'||sub==='accordion'||raw.includes('acordeon comercial'))return'Acordeón comercial';
    if(key==='commercial.stores'||sub==='stores'||raw==='tiendas')return'Tiendas';
    if(key==='commercial.lingerie_checklist'||sub==='lingerie-checklist'||raw.includes('checklist lenceria'))return'Checklist lencería';
    if(key==='commercial.sellthrough'||sub.includes('sell')||raw.includes('sell through'))return'Sell Through';
    if(key==='commercial.upload'||sub==='analysis-upload'||raw.includes('carga de datos'))return'Carga de datos';
    if(key==='commercial.sections'||sub==='sections')return'Sección / Rubro';
    if(key==='commercial.areas'||sub==='areas')return'Ubicación / Área';
    if(key==='commercial.more'||sub==='more')return'Más opciones';
    return String(btn.dataset.rtLabel||btn.title||btn.textContent||'').replace(/\s+/g,' ').trim();
  }

  function applyHost(host,kind){
    if(!host)return;
    [...host.children].filter(x=>x.tagName==='BUTTON').forEach(btn=>{
      if(btn.hidden||btn.classList.contains('hidden')||btn.getAttribute('aria-hidden')==='true')return;
      const label=btn.querySelector(':scope>.v232-tab-label');
      if(!label)return;
      const text=kind==='cm'?cmLabel(btn):analysisLabel(btn);
      if(label.textContent!==text)label.textContent=text;
    });
  }

  let raf=0;
  function fix(){
    if(!mobile())return;
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      const mod=currentModule();
      if(mod==='operativo')applyHost(document.getElementById('operativoNav'),'cm');
      if(mod==='analysis')applyHost(document.getElementById('analysisNav'),'analysis');
    });
  }

  const observer=new MutationObserver(muts=>{
    if(!mobile())return;
    if(muts.some(m=>m.type==='childList'||m.type==='attributes'))setTimeout(fix,15);
  });

  function init(){
    if(!mobile())return;
    if(!document.body.dataset.v234Observer){
      document.body.dataset.v234Observer='1';
      observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']});
    }
    fix();
    [80,220,500,1000,2000].forEach(ms=>setTimeout(fix,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav>button,#analysisNav>button'))[20,100,260].forEach(ms=>setTimeout(fix,ms));
  },true);
  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(fix,30));
  window.addEventListener('resize',()=>setTimeout(fix,80),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(fix,150),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});
  console.info('[V234] ajuste exacto de pestañas móviles aplicado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v234_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v234-exact-mobile-tabs-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v234-exact-mobile-tabs-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V234-EXACT-TABS",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V234] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V234_EXACT_MOBILE_TABS = True
    print("[V234] ajuste exacto de pestañas móviles instalado.", flush=True)
