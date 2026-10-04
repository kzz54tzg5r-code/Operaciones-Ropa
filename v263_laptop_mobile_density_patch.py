"""V263 · Densidad responsive tipo laptop para móvil.

Capa final exclusivamente visual:
- carga web/laptop_mobile_v263.css al final del <head>;
- domina V260/V261/V262 sólo en presentación;
- no altera datos, cálculos, endpoints, filtros ni eventos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V263_LAPTOP_MOBILE", False):
        return

    link = '<link id="v263-laptop-mobile" rel="stylesheet" href="/static/laptop_mobile_v263.css?v=20261004-1">'

    @m.app.middleware("http")
    async def v263_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")

            if 'id="v263-laptop-mobile"' not in html:
                html = html.replace("</head>", link + "</head>", 1)

            # Asegurar viewport correcto para iOS/Android/PWA sin duplicarlo.
            if 'name="viewport"' not in html:
                html = html.replace(
                    "<head>",
                    '<head><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
                    1,
                )

            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V263-LAPTOP-MOBILE",
            })
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers=headers,
            )
        except Exception as exc:
            print(f"[V263] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V263_LAPTOP_MOBILE = True
    print("[V263] responsive móvil tipo laptop instalado.", flush=True)
