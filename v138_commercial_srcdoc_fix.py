"""V138.1 · Estabiliza Análisis Comercial en Safari/iPhone.

Correcciones sobre V138:
- Evita el bucle de MutationObserver + setInterval que podía dejar Safari en
  "Cargando demo Comercial…" y terminar recargando la página.
- Escribe el HTML estático V137 directamente dentro del iframe about:blank;
  si Safari bloquea document.write, usa Blob URL como respaldo.
- Corrige definitivamente el 422 de /api/commercial-sales-summary: los parches
  V112/V113 importaban Request dentro de install() y, por `from __future__
  import annotations`, FastAPI podía interpretarlo como query param. Aquí se
  vuelve a registrar la ruta con Request disponible a nivel de módulo.

Mantiene el demo, filtros y siete pestañas. No modifica datos reales.
"""
from __future__ import annotations

import inspect

from fastapi import Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V138_COMMERCIAL_SRCDOC_FIX", False):
        return

    # ------------------------------------------------------------------
    # 1) Reparar la firma HTTP de ventas. Conserva toda la lógica V113;
    #    únicamente corrige cómo FastAPI recibe Request.
    # ------------------------------------------------------------------
    def _route(path: str, method: str = "GET"):
        for route in list(m.app.router.routes):
            if getattr(route, "path", None) == path and method.upper() in (getattr(route, "methods", set()) or set()):
                return route
        return None

    summary_route = _route("/api/commercial-sales-summary", "GET")
    old_summary = getattr(summary_route, "endpoint", None)
    if summary_route is not None and callable(old_summary):
        try:
            m.app.router.routes.remove(summary_route)
        except ValueError:
            pass

        async def sales_summary_v1381(
            request: Request,
            year: int | None = None,
            through_month: int | None = None,
            store: str = "Compañía",
        ):
            result = old_summary(
                request=request,
                year=year,
                through_month=through_month,
                store=store,
            )
            if inspect.isawaitable(result):
                result = await result
            return result

        m.app.add_api_route(
            "/api/commercial-sales-summary",
            sales_summary_v1381,
            methods=["GET"],
        )

    css = r'''<style id="v138-commercial-srcdoc-css">
body.v133-commercial-demo #v133CommercialDemoHost{display:block!important;position:relative!important;z-index:2147483646!important;pointer-events:auto!important;overflow:visible!important}
body.v133-commercial-demo #v133CommercialDemoHost .v138-shell{display:block!important;margin:0!important;padding:0!important;background:#f2f6fb!important}
#v138CommercialFrame{display:block!important;width:100%!important;height:1200px;border:0!important;background:#f2f6fb!important;pointer-events:auto!important;touch-action:auto!important;overflow:hidden!important}
#v138CommercialLoading{display:grid;place-items:center;min-height:180px;background:#f2f6fb;color:#315985;font:800 13px system-ui,-apple-system,sans-serif;text-align:center;padding:24px}
#v138CommercialError{display:none;margin:8px;padding:12px;border:1px solid #f1c9ce;border-radius:10px;background:#fff5f6;color:#9f2030;font:700 12px system-ui,-apple-system,sans-serif}
</style>'''

    js = r'''<script id="v138-commercial-srcdoc-js">
(function(){
  var loading=false,loaded=false,blobUrl='';
  function owner(){return typeof USER!=='undefined'&&(USER&&((USER.role==='superadmin')||(USER.real_role==='superadmin')||(USER.can_preview_roles===true)));}
  function isCommercial(){var h=(document.getElementById('heroTitle')||{}).textContent||'';var a=document.querySelector('[data-main="analysis"].active,[data-main="commercial"].active');return document.body.classList.contains('v133-commercial-demo')||/Análisis Comercial/i.test(h)||!!a;}
  function host(){return document.getElementById('v133CommercialDemoHost');}
  function setHeight(){
    var f=document.getElementById('v138CommercialFrame');if(!f)return;
    try{var d=f.contentDocument;if(d&&d.documentElement){var h=Math.max(560,Math.min(6000,d.documentElement.scrollHeight+12));if(h>0)f.style.height=h+'px';}}catch(e){}
  }
  function finish(){
    loaded=true;loading=false;
    var l=document.getElementById('v138CommercialLoading'),e=document.getElementById('v138CommercialError'),f=document.getElementById('v138CommercialFrame');
    if(l)l.style.display='none';if(e)e.style.display='none';if(f)f.style.display='block';
    setTimeout(setHeight,40);setTimeout(setHeight,250);setTimeout(setHeight,900);
  }
  function showError(msg){
    loading=false;
    var l=document.getElementById('v138CommercialLoading'),e=document.getElementById('v138CommercialError');
    if(l)l.style.display='none';if(e){e.style.display='block';e.textContent=msg||'No fue posible cargar el demo Comercial.';}
  }
  function build(){
    if(!owner()||!isCommercial())return;
    var h=host();if(!h)return;
    if(document.getElementById('v138CommercialFrame'))return;
    h.innerHTML='<div class="v133-shell v138-shell"><div id="v136CommercialFrame" style="display:none!important" aria-hidden="true"></div><div id="v137CommercialFrame" style="display:none!important" aria-hidden="true"></div><div id="v138CommercialLoading">Cargando demo Comercial…</div><div id="v138CommercialError"></div><iframe id="v138CommercialFrame" title="Demo Análisis Comercial" src="about:blank"></iframe></div>';
    h.style.setProperty('display','block','important');h.style.setProperty('pointer-events','auto','important');
  }
  async function load(){
    if(loaded||loading||!owner()||!isCommercial())return;
    build();var f=document.getElementById('v138CommercialFrame');if(!f)return;
    loading=true;
    try{
      var r=await fetch('/commercial-demo-v137?v=1381&ts='+Date.now(),{cache:'no-store',credentials:'same-origin'});
      if(!r.ok)throw new Error('HTTP '+r.status);
      var html=await r.text();
      if(!html||html.length<500)throw new Error('HTML incompleto');

      // Safari/iPhone es más estable escribiendo en about:blank que esperando
      // el onload de srcdoc. Además marcamos la carga como terminada de forma
      // inmediata para que nunca quede el loader bloqueado.
      try{
        var d=f.contentWindow&&f.contentWindow.document;
        if(!d)throw new Error('iframe sin documento');
        d.open();d.write(html);d.close();finish();
      }catch(writeErr){
        try{
          if(blobUrl){try{URL.revokeObjectURL(blobUrl)}catch(_){}blobUrl='';}
          blobUrl=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
          f.onload=function(){finish();};
          f.src=blobUrl;
          setTimeout(function(){if(!loaded)finish();},1400);
        }catch(blobErr){
          throw writeErr;
        }
      }
    }catch(err){showError('Error cargando el demo Comercial: '+(err&&err.message?err.message:err));}
  }
  function ensure(){if(!owner()||!isCommercial())return;build();load();}

  window.addEventListener('message',function(e){
    if(e.data&&e.data.type==='v137-height'){
      var f=document.getElementById('v138CommercialFrame');if(f){var n=Number(e.data.height)||1100;f.style.height=Math.max(560,Math.min(6000,n))+'px';}
    }
  });

  // Un solo intento por entrada al módulo. Se eliminan el MutationObserver
  // global y el setInterval de V138 original, que en Safari podían acumular
  // trabajo y provocar una recarga completa de la SPA.
  document.addEventListener('click',function(e){
    var m=e.target&&e.target.closest?e.target.closest('[data-main]'):null;
    if(m&&(m.dataset.main==='analysis'||m.dataset.main==='commercial')){
      loaded=false;loading=false;
      setTimeout(ensure,220);setTimeout(function(){if(!loaded&&!loading)ensure();},900);
    }
  },true);

  setTimeout(ensure,350);setTimeout(function(){if(!loaded&&!loading)ensure();},1100);
  window.addEventListener('pagehide',function(){if(blobUrl){try{URL.revokeObjectURL(blobUrl)}catch(_){}blobUrl='';}});
  console.info('[V138.1] Comercial Safari estable: iframe por document.write + API ventas corregida.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v138_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v138-commercial-srcdoc-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V138.1-COMMERCIAL-SAFARI-STABLE",
            })
        except Exception as exc:
            print(f"[V138.1] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V138_COMMERCIAL_SRCDOC_FIX = True
    print("[V138.1] Comercial Safari estable + sales-summary Request reparado.", flush=True)
