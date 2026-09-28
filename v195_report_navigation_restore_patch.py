"""V195 · Guardas finales de navegación de reportes.

Objetivos:
- Evitar que una consulta lenta de una pestaña anterior vuelva a pintar el contenido
  después de que el usuario ya cambió de reporte.
- Garantizar que Carga de datos de Cambios y Muertos conserve su formulario.
- Garantizar que cada pestaña de Análisis Comercial active su página real y que
  Carga de datos comercial muestre sus fuentes/historial sin filtros ajenos.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V195_REPORT_NAVIGATION_RESTORE", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''<style id="v195-report-navigation-css">
body.v195-commercial-upload #globalFilters{display:none!important}
body.v195-commercial-upload #page-analysis-upload.active{display:block!important}
</style>'''

    js = r'''<script id="v195-report-navigation-js">
(function(){
  if(window.__V195_REPORT_NAVIGATION_RESTORE)return;
  window.__V195_REPORT_NAVIGATION_RESTORE=true;

  const q=s=>document.querySelector(s);
  let epoch=0;
  let desiredOperational='';
  let restoreTimer=0;
  let restoring=false;

  function currentOperational(){
    try{return String(OP_VIEW||desiredOperational||'')}catch(_){return desiredOperational||''}
  }

  function currentMain(){
    try{return String(MAIN||'')}catch(_){return document.body.dataset.v163Module||''}
  }

  function scheduleRestore(view,delay=20){
    if(!view)return;
    clearTimeout(restoreTimer);
    restoreTimer=setTimeout(async()=>{
      if(restoring)return;
      if(currentMain()!=='operativo' && currentMain()!=='operation')return;
      const latest=currentOperational()||desiredOperational;
      if(latest!==view)return;
      if(typeof window.renderOperativoView!=='function')return;
      restoring=true;
      try{await window.renderOperativoView(view,true)}
      catch(err){console.error('[V195] restore operational view',view,err)}
      finally{restoring=false}
    },delay);
  }

  const previousRender=window.renderOperativoView;
  if(typeof previousRender==='function' && !previousRender.__v195){
    const wrapped=async function(name,...args){
      const my=++epoch;
      desiredOperational=String(name||'');
      const out=await previousRender.call(this,name,...args);

      // Si una llamada anterior terminó después de una navegación más nueva,
      // volvemos a pintar únicamente la vista que sigue siendo la seleccionada.
      if(my!==epoch){
        const latest=currentOperational()||desiredOperational;
        if(latest)scheduleRestore(latest,0);
        return out;
      }

      if(name==='Carga de datos'){
        setTimeout(()=>{
          if(currentOperational()!=='Carga de datos')return;
          if(!q('#opsDropzone') || !q('#opsModuleFile')){
            scheduleRestore('Carga de datos',0);
          }
        },80);
      }
      return out;
    };
    wrapped.__v195=true;
    window.renderOperativoView=wrapped;
  }

  function verifyOperationalButton(btn){
    const view=String(btn?.dataset?.opview||'');
    if(!view)return;
    desiredOperational=view;
    [80,360,1000,1800].forEach(ms=>setTimeout(()=>{
      if(currentOperational()!==view)return;
      if(view==='Carga de datos'){
        const ok=Boolean(q('#opsDropzone')&&q('#opsModuleFile')&&q('#opsModuleUploadBtn'));
        if(!ok)scheduleRestore(view,0);
        return;
      }
      const content=q('#operativoDynamicContent');
      if(!content || !content.children.length)scheduleRestore(view,0);
    },ms));
  }

  function syncCommercialUpload(){
    let sub='';
    try{sub=String(SUB||'')}catch(_){
      sub=String(q('#analysisNav [data-sub].active')?.dataset?.sub||'');
    }
    const active=currentMain()==='analysis' && sub==='analysis-upload';
    document.body.classList.toggle('v195-commercial-upload',active);
    if(!active)return;
    q('#globalFilters')?.classList.add('hidden');
    const page=document.getElementById('page-analysis-upload');
    if(page&&!page.classList.contains('active')){
      document.querySelectorAll('.page').forEach(x=>x.classList.toggle('active',x===page));
    }
    try{if(typeof loadUploadHistories==='function')loadUploadHistories()}catch(err){
      console.error('[V195] commercial upload history',err);
    }
  }

  function verifyCommercialButton(btn){
    const sub=String(btn?.dataset?.sub||'');
    if(!sub)return;
    [60,260,700].forEach(ms=>setTimeout(()=>{
      let current='';
      try{current=String(SUB||'')}catch(_){}
      const page=document.getElementById('page-'+sub);
      if(current!==sub || !page?.classList.contains('active')){
        try{
          if(typeof goSub==='function')goSub(sub);
          else if(typeof window.goSub==='function')window.goSub(sub);
        }catch(err){console.error('[V195] reopen commercial tab',sub,err)}
      }
      syncCommercialUpload();
    },ms));
  }

  document.addEventListener('click',event=>{
    const op=event.target.closest?.('#operativoNav [data-opview]');
    if(op)verifyOperationalButton(op);

    const commercial=event.target.closest?.('#analysisNav [data-sub]');
    if(commercial)verifyCommercialButton(commercial);
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>{
    setTimeout(syncCommercialUpload,60);
  });

  setTimeout(syncCommercialUpload,120);
  console.info('[V195] navegación de reportes y cargas protegida contra renders tardíos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v195_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v195-report-navigation-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v195-report-navigation-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V195",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V195] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V195_REPORT_NAVIGATION_RESTORE = True
    print("[V195] navegación y carga de reportes restauradas.", flush=True)
