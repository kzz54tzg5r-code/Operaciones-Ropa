"""V140 · Guardia del demo Comercial en móvil/Safari.

El demo V139 ya se renderiza directo en el DOM. Este parche evita que el mismo
clic continúe hacia goMain('analysis'), porque esa ruta dispara el dashboard real
(loadDash + tablas/modelos) aunque el propietario sólo está validando el demo.
En iPhone esa doble carga dejaba la pantalla en blanco y podía terminar en una
recarga de la SPA, que vuelve por defecto a Cambios y Muertos.

V140 se registra después de V139. Por ello V139 recibe primero el clic y programa
su render inmediato; V140 corta la propagación antes de los handlers base.
No modifica datos ni APIs.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V140_COMMERCIAL_DEMO_GUARD", False):
        return

    js = r'''<script id="v140-commercial-demo-guard-js">
(function(){
  function owner(){
    return typeof USER!=='undefined' && USER && (
      USER.role==='superadmin' || USER.real_role==='superadmin' || USER.can_preview_roles===true
    );
  }
  function selectCommercialNav(){
    try{
      document.querySelectorAll('[data-main]').forEach(function(x){
        x.classList.toggle('active', x.getAttribute('data-main')==='analysis' || x.getAttribute('data-main')==='commercial');
      });
      var op=document.getElementById('operativoNav'); if(op)op.classList.add('hidden');
      var an=document.getElementById('analysisNav'); if(an)an.classList.add('hidden');
      var gf=document.getElementById('globalFilters'); if(gf)gf.classList.add('hidden');
      try{ MAIN='analysis'; SUB='macro'; }catch(_){ }
    }catch(_){ }
  }

  // Captura DESPUÉS de V139 pero ANTES del onclick/bubble de la app base.
  document.addEventListener('click', function(e){
    if(!owner()) return;
    var main=e.target && e.target.closest ? e.target.closest('[data-main]') : null;
    if(!main) return;
    var v=main.getAttribute('data-main');
    if(v!=='analysis' && v!=='commercial') return;
    selectCommercialNav();
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);

  // Respaldo táctil para Safari si click sintetizado llega tarde.
  document.addEventListener('touchend', function(e){
    if(!owner()) return;
    var main=e.target && e.target.closest ? e.target.closest('[data-main]') : null;
    if(!main) return;
    var v=main.getAttribute('data-main');
    if(v!=='analysis' && v!=='commercial') return;
    selectCommercialNav();
  }, true);

  console.info('[V140] Demo Comercial aislado del loadDash real.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v140_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v140-commercial-demo-guard-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = {
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V140-COMMERCIAL-DEMO-GUARD",
            }
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V140] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V140_COMMERCIAL_DEMO_GUARD = True
    print("[V140] Demo Comercial aislado de carga real y navegación base.", flush=True)
