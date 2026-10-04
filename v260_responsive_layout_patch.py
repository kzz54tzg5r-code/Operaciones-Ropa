"""V260 · Arquitectura responsive global.

Capa exclusivamente de presentación:
- enlaza web/adaptive_layout_v260.css al final del <head>;
- no altera datos, cálculos, endpoints, indicadores, filtros ni eventos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V260_RESPONSIVE_LAYOUT", False):
        return

    link = '<link id="v260-adaptive-layout" rel="stylesheet" href="/static/adaptive_layout_v260.css?v=20261004-1">'

    @m.app.middleware("http")
    async def v260_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v260-adaptive-layout"' not in html:
                html = html.replace("</head>", link + "</head>", 1)

            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V260-RESPONSIVE-LAYOUT",
            })
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers=headers,
            )
        except Exception as exc:
            print(f"[V260] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V260_RESPONSIVE_LAYOUT = True
    print("[V260] arquitectura responsive global instalada.", flush=True)
