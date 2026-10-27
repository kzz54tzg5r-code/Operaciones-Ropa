"""V366 · Presentación monetaria consistente sin alterar la base ni los cálculos.

Se aplica al HTML servido, no al archivo index.html: evita tocar un archivo
grande y mantiene intactas las adaptaciones anteriores de la interfaz.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse

_OLD_MONEY = "money=n=>'$'+fmt(n),"
_OLD_FMT_MONEY = "function fmtMoney(v){return '$'+Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0})}"
_NEW_FMT_MONEY = """function fmtMoney(v){
  const amount=Number(v||0);
  if(!Number.isFinite(amount))return '—';
  if(amount===0)return '$0 mil';
  const digits=Math.abs(amount)<1000?3:1;
  return '$'+(amount/1000).toLocaleString('es-MX',
    {minimumFractionDigits:digits,maximumFractionDigits:digits})+' mil';
}"""


def _apply_money_format(html: str) -> str:
    # Cambio exclusivamente visual: todas las llamadas reciben el monto
    # original en MXN y sólo la salida mostrada se divide entre 1,000.
    if _OLD_MONEY in html:
        html = html.replace(_OLD_MONEY, "money=n=>fmtMoney(n),", 1)
    if _OLD_FMT_MONEY in html:
        html = html.replace(_OLD_FMT_MONEY, _NEW_FMT_MONEY, 1)
    # Auditoría de Tasa de recuperación usa un formateador aislado.
    old_mxn = "var mxn=function(v){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:0})};"
    new_mxn = """var mxn=function(v){if(v==null||!Number.isFinite(Number(v)))return '—';var p=Number(v);var dec=Math.abs(p)<1000?3:1;return p===0?'$0 mil':'$'+(p/1000).toLocaleString('es-MX',{minimumFractionDigits:dec,maximumFractionDigits:dec})+' mil'};"""
    if old_mxn in html:
        html = html.replace(old_mxn, new_mxn, 1)

    # V369: conservar la tabla de recuperación en la ruta diaria heredada,
    # sin mostrar banners ni controles de verificación/reprocesamiento.
    legacy_daily = "    out=monthlyCrossTable(mt,true);"
    recovered_daily = """    out=monthlyCrossTable(mt,true);
    out+=`<div class="title">Recuperación por tienda</div>${recoveryTable(rec)}`;"""
    if legacy_daily in html and "if(name==='Operación Diaria'){" in html:
        daily = html.split("if(name==='Operación Diaria'){", 1)[1].split("}else if(name==='Reporte Semanal'){", 1)[0]
        if "recoveryTable(rec)" not in daily:
            html = html.replace(legacy_daily, recovered_daily, 1)
    # La pantalla Carga de datos vuelve al flujo original Cargar/Reemplazar.
    html = html.replace('<script src="/static/dev_rebuild_controls_v371.js?v=371" defer></script>', '')
    return html


def install(m):
    if getattr(m, "_V366_MILES_DISPLAY", False):
        return

    @m.app.middleware("http")
    async def _v366_miles_display(request, call_next):
        response = await call_next(request)
        if (request.method != "GET" or request.url.path != "/"
                or response.status_code != 200
                or "text/html" not in response.headers.get("content-type", "")
                or response.headers.get("content-encoding")):
            # Nunca consumir contenido comprimido: debe llegar intacto al navegador.
            return response

        # Consumir una única vez. Si la sustitución de formato falla, NO
        # devolver el StreamingResponse agotado (respuesta vacía / error 520).
        body = b"".join([chunk async for chunk in response.body_iterator])
        headers = dict(response.headers)
        for key in ("content-length", "transfer-encoding"):
            headers.pop(key, None)
        try:
            html = body.decode("utf-8")
            updated = _apply_money_format(html)
            return HTMLResponse(updated, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V366] Se conserva HTML original: {type(exc).__name__}: {exc}", flush=True)
            return HTMLResponse(content=body, status_code=response.status_code, headers=headers)

    m._V366_MILES_DISPLAY = True
    print("[V366] Moneda web en miles; originales y fórmulas inalterados.", flush=True)
