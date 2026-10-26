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
    return html


def install(m):
    if getattr(m, "_V366_MILES_DISPLAY", False):
        return

    @m.app.middleware("http")
    async def _v366_miles_display(request, call_next):
        response = await call_next(request)
        if (request.method != "GET" or request.url.path != "/"
                or response.status_code != 200
                or "text/html" not in response.headers.get("content-type", "")):
            return response
        try:
            body = b"".join([chunk async for chunk in response.body_iterator])
            html = body.decode("utf-8")
            updated = _apply_money_format(html)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            headers.pop("content-encoding", None)
            return HTMLResponse(updated, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V366] Formato moneda no disponible: {exc}", flush=True)
            return response

    m._V366_MILES_DISPLAY = True
    print("[V366] Moneda web en miles; originales y fórmulas inalterados.", flush=True)
