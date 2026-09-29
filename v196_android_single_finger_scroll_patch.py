"""V196 · Android single-finger vertical scroll.

Corrige el conflicto entre carruseles horizontales, nested scroll containers y
overscroll mobile que impedía desplazar reportes con un dedo en Android.
No modifica datos, endpoints, permisos ni cálculos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V196_ANDROID_SINGLE_FINGER_SCROLL", False):
        return

    css = r'''<style id="v196-android-single-finger-scroll-css">
@media(max-width:900px){
  html.android-one-finger-scroll,
  html.android-one-finger-scroll body{
    min-height:100%!important;
    height:auto!important;
    overflow-y:auto!important;
    overscroll-behavior-y:auto!important;
  }

  html.android-one-finger-scroll body,
  html.android-one-finger-scroll .shell,
  html.android-one-finger-scroll .main,
  html.android-one-finger-scroll section.page,
  html.android-one-finger-scroll section.page.active{
    touch-action:auto!important;
    overscroll-behavior-y:auto!important;
  }

  /* Navegaciones horizontales: el navegador conserva pan vertical.
     El JS sólo intercepta después de confirmar intención horizontal. */
  html.android-one-finger-scroll #operativoNav,
  html.android-one-finger-scroll #analysisNav,
  html.android-one-finger-scroll .rt-carousel,
  html.android-one-finger-scroll .switches,
  html.android-one-finger-scroll .v165-subfilters{
    touch-action:pan-y pinch-zoom!important;
    overscroll-behavior-y:auto!important;
  }

  /* Tablas y gráficas pueden moverse lateralmente, pero nunca deben
     bloquear el encadenamiento vertical hacia la página. */
  html.android-one-finger-scroll .tablewrap,
  html.android-one-finger-scroll .model-sticky-table,
  html.android-one-finger-scroll .model-scroll-30,
  html.android-one-finger-scroll .table-scroll-35,
  html.android-one-finger-scroll .chart-scroll,
  html.android-one-finger-scroll .sales-chart-scroll,
  html.android-one-finger-scroll .v168-pivot-wrap,
  html.android-one-finger-scroll .v168-plan-matrix{
    touch-action:pan-x pan-y pinch-zoom!important;
    overscroll-behavior-y:auto!important;
  }

  html.android-one-finger-scroll .panel,
  html.android-one-finger-scroll .card,
  html.android-one-finger-scroll .kpi,
  html.android-one-finger-scroll .report-kpi,
  html.android-one-finger-scroll .filters,
  html.android-one-finger-scroll .or-filter-panel-v3{
    touch-action:auto!important;
    overscroll-behavior-y:auto!important;
  }
}
</style>'''

    js = r'''<script id="v196-android-single-finger-scroll-js">
(function(){
  if(window.__V196_ANDROID_SINGLE_FINGER_SCROLL)return;
  window.__V196_ANDROID_SINGLE_FINGER_SCROLL=true;

  const android=/Android/i.test(navigator.userAgent||'');
  document.documentElement.classList.toggle('android-one-finger-scroll',android);
  if(!android)return;

  // Elimina bloqueos inline accidentales sólo cuando no hay un modal abierto.
  function unlockPage(){
    const modal=document.querySelector('.modal-backdrop:not(.hidden),[role="dialog"]:not(.hidden)');
    if(modal)return;
    document.documentElement.style.removeProperty('overflow-y');
    document.body.style.removeProperty('overflow-y');
    document.documentElement.classList.add('android-one-finger-scroll');
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',unlockPage,{once:true});
  }else{
    unlockPage();
  }
  window.addEventListener('pageshow',unlockPage,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(unlockPage,120),{passive:true});
  window.addEventListener('resize',()=>setTimeout(unlockPage,80),{passive:true});

  console.info('[V196] Android: scroll vertical de un dedo habilitado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v196_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v196-android-single-finger-scroll-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v196-android-single-finger-scroll-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V196",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V196] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V196_ANDROID_SINGLE_FINGER_SCROLL = True
    print("[V196] Android single-finger scroll instalado.", flush=True)
