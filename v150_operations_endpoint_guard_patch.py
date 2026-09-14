"""V150 · Repara el endpoint principal de Cambios y Muertos.

Síntoma observado en producción: Centro Ejecutivo muestra
"No fue posible consultar Centro Ejecutivo: [object Object]".
Ese texto ocurre cuando FastAPI devuelve un `detail` estructurado (típicamente
422 de validación) y el front lo convierte directamente a Error.

Este parche vuelve a registrar GET /api/operations con Request tipado a nivel
de módulo, conservando la lógica operativa vigente (incluidos V87/V90). También
normaliza el mensaje de error del front para que nunca vuelva a ocultarse como
[object Object].
"""
from __future__ import annotations

import inspect
import json
import traceback

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V150_OPERATIONS_ENDPOINT_GUARD", False):
        return

    # ------------------------------------------------------------------
    # 1) Re-registrar /api/operations con una firma limpia y Request real.
    #    No reemplaza m.operations: llama la lógica ya parcheada V87/V90.
    # ------------------------------------------------------------------
    old_routes = []
    for route in list(m.app.router.routes):
        if getattr(route, "path", None) == "/api/operations" and "GET" in (getattr(route, "methods", set()) or set()):
            old_routes.append(route)
    for route in old_routes:
        try:
            m.app.router.routes.remove(route)
        except ValueError:
            pass

    async def operations_v150(
        request: Request,
        store: str = "Compañía",
        period_type: str = "all",
        period_value: str = "",
        area: str = "",
        activity: str = "",
        start_date: str = "",
        end_date: str = "",
        compact: bool = False,
        project_only: bool = False,
    ):
        try:
            result = m.operations(
                request,
                store=store,
                period_type=period_type,
                period_value=period_value,
                area=area,
                activity=activity,
                start_date=start_date,
                end_date=end_date,
                compact=compact,
                project_only=project_only,
            )
            if inspect.isawaitable(result):
                result = await result
            return result
        except HTTPException:
            raise
        except Exception as exc:
            print(
                f"[V150-OPS] ERROR {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=12)}",
                flush=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"{type(exc).__name__}: {exc}",
            )

    m.app.add_api_route("/api/operations", operations_v150, methods=["GET"])

    # ------------------------------------------------------------------
    # 2) El front vigente hace new Error(j.detail). Si detail es array/objeto,
    #    termina mostrando [object Object]. Normalizar sólo ese bloque.
    # ------------------------------------------------------------------
    js = r'''<script id="v150-api-error-normalizer-js">
(function(){
  const oldApi=window.api;
  if(typeof oldApi!=='function')return;
  function detailText(v){
    if(v===null||v===undefined)return '';
    if(typeof v==='string')return v;
    if(Array.isArray(v))return v.map(function(x){
      if(x&&typeof x==='object')return x.msg||x.message||JSON.stringify(x);
      return String(x);
    }).join(' · ');
    if(typeof v==='object')return v.message||v.msg||v.detail||JSON.stringify(v);
    return String(v);
  }
  window.api=async function(url,opt){
    try{return await oldApi(url,opt||{});}
    catch(err){
      if(err instanceof Error && err.message && err.message!=='[object Object]')throw err;
      const text=detailText(err&&err.detail?err.detail:err);
      const out=new Error(text||'No fue posible completar la consulta.');
      if(err&&err.status)out.status=err.status;
      throw out;
    }
  };
  console.info('[V150] Mensajes API estructurados normalizados.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v150_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v150-api-error-normalizer-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Operations-UI-Version": "V150-OPS-ENDPOINT-GUARD",
                },
            )
        except Exception as exc:
            print(f"[V150] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V150_OPERATIONS_ENDPOINT_GUARD = True
    print("[V150] /api/operations re-registrado con Request tipado y errores legibles.", flush=True)
