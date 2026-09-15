"""V157 · Diseño Opción 1 alineado a bocetos + filtro único.

Objetivo:
- Un solo sistema de filtros visible por módulo.
- Recuperar el look de los bocetos sin tocar tablas, gráficas ni exportaciones.
- Quitar V102/V103/V104 del arranque para evitar banners, chips y observers.
- Mantener los filtros nativos como fuente de verdad y sólo cambiar su presentación.

Este parche es CSS-only y no agrega observers, intervalos ni listeners.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V157_OPTION1_BOCETO", False):
        return

    css = r'''<style id="v157-option1-boceto-css">
:root{
  --v157-navy:#0a3d78;
  --v157-navy2:#0d4f94;
  --v157-blue:#176ff0;
  --v157-bg:#f4f7fb;
  --v157-line:#d7e3ef;
  --v157-text:#113a70;
  --v157-muted:#667a91;
}

/* Base general del boceto */
body{background:var(--v157-bg)!important;color:var(--v157-text)!important}
.shell{background:var(--v157-bg)!important}
.main{background:var(--v157-bg)!important;padding:14px 18px 82px!important}

/* Sidebar Opción 1 */
.side{
  background:linear-gradient(180deg,#0a3d78 0%,#0e4f92 58%,#0a376d 100%)!important;
  border-right:0!important;box-shadow:8px 0 24px rgba(10,55,109,.08)!important;
}
.sidebrand{border-bottom:1px solid rgba(255,255,255,.13)!important;padding-bottom:16px!important;margin-bottom:8px!important}
.sidebrand b,.sidebrand small,.profile b,.profile small{color:#fff!important}
.group{color:rgba(255,255,255,.52)!important}
.nav{color:rgba(255,255,255,.9)!important;background:transparent!important;border-radius:11px!important;margin:2px 0!important}
.nav:hover{background:rgba(255,255,255,.08)!important}
.nav.active{background:#1774f6!important;color:#fff!important;box-shadow:0 6px 16px rgba(0,34,88,.2)!important}
.nav small{color:inherit!important;opacity:.72!important}
.profile{border-top:1px solid rgba(255,255,255,.15)!important}
.logout,.sidebar-toggle{background:rgba(255,255,255,.1)!important;color:#fff!important;border-color:rgba(255,255,255,.2)!important}

/* Encabezado compacto como boceto */
.hero{
  min-height:102px!important;
  background:linear-gradient(118deg,#0b3e7d 0%,#0d579f 68%,#0a3c77 100%)!important;
  border-radius:18px!important;padding:18px 22px!important;border:0!important;box-shadow:none!important;
}
.hero h1{font-size:25px!important;letter-spacing:-.02em!important;margin:0!important}
.hero p{font-size:10px!important;color:#d7e7fa!important;margin-top:5px!important}
.hero .badge{background:rgba(255,255,255,.12)!important;border-color:rgba(255,255,255,.18)!important}

/*
   FILTRO ÚNICO:
   V102/V103/V104 ya no se instalan. Si una respuesta cacheada llegara a traerlos,
   se ocultan. Los filtros reales/nativos son la única interfaz visible.
*/
#v102FilterMode,#v102Drill,#v103FilterShell,#v103ClassicBack{display:none!important}

.filters:not(.hidden),#globalFilters:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(auto-fit,minmax(165px,1fr));
  align-items:end!important;
  gap:10px!important;
  background:#fff!important;
  border:1px solid var(--v157-line)!important;
  border-radius:15px!important;
  padding:12px!important;
  margin:10px 0!important;
  box-shadow:0 4px 14px rgba(31,77,128,.04)!important;
}
.filter{min-width:0!important;width:auto!important}
.filter label,
#globalFilters label{
  display:block!important;
  color:#627b96!important;
  font-size:8px!important;
  font-weight:900!important;
  text-transform:uppercase!important;
  letter-spacing:.035em!important;
  margin:0 0 5px!important;
}
.filter select,.filter input,
#globalFilters select,#globalFilters input{
  width:100%!important;
  min-height:39px!important;
  border:1px solid #cddbeb!important;
  border-radius:10px!important;
  background:#fff!important;
  color:#123b73!important;
  padding:7px 10px!important;
  font-size:10px!important;
  box-shadow:none!important;
}
.filters .primary,#globalFilters .primary,
.filters button.primary,#globalFilters button.primary{
  min-height:39px!important;
  border-radius:10px!important;
  background:var(--v157-blue)!important;
  box-shadow:none!important;
}

/* Pestañas tipo pill, tal como en el boceto */
.switches:not(.hidden),#operativoNav:not(.hidden),#analysisNav:not(.hidden),.v125-tabs:not(.hidden){
  display:flex!important;
  align-items:center!important;
  gap:6px!important;
  flex-wrap:wrap!important;
  background:#fff!important;
  border:1px solid var(--v157-line)!important;
  border-radius:14px!important;
  padding:5px!important;
  margin:9px 0 12px!important;
  box-shadow:none!important;
}
.switch,.v125-tab,
#operativoNav button,#analysisNav button{
  border-radius:9px!important;
  min-height:32px!important;
  padding:7px 11px!important;
  font-size:8px!important;
  font-weight:900!important;
  border:1px solid transparent!important;
  background:transparent!important;
  color:#315b87!important;
}
.switch.active,.v125-tab.active,
#operativoNav button.active,#analysisNav button.active{
  background:var(--v157-blue)!important;
  color:#fff!important;
  box-shadow:0 3px 9px rgba(23,111,240,.16)!important;
}

/* Títulos y tarjetas: visual del boceto sin tocar su contenido */
.title{color:#0d3d77!important;font-size:18px!important;letter-spacing:-.01em!important;margin-top:14px!important}
.subtitle{color:#70839a!important;font-size:9px!important}
.kpis,.report-kpis{gap:10px!important}
.kpi,.report-kpi,.card,.useritem{
  background:#fff!important;
  border:1px solid var(--v157-line)!important;
  border-radius:14px!important;
  box-shadow:0 2px 10px rgba(31,77,128,.035)!important;
}
.kpi,.report-kpi{padding:12px 13px!important;min-height:96px!important}
.lab,.report-kpi .rk-label{color:#637a94!important;font-size:8px!important}
.val,.report-kpi .rk-value{color:#0d3d77!important;letter-spacing:-.02em!important}
.panel,.drop{
  background:#fff!important;
  border-color:var(--v157-line)!important;
  border-radius:14px!important;
  box-shadow:0 2px 10px rgba(31,77,128,.03)!important;
}

/* Usuarios y Compartir: una sola hoja, misma identidad visual */
.usergrid{gap:10px!important}
.useritem{padding:13px!important}
.drop{padding:14px!important}

/* Preservación estricta de reportes construidos */
table,.table,.tablewrap,canvas,svg{ }
a[download],[data-export],[id*="download" i],[id*="export" i]{ }

/* Demos comerciales heredados nunca aparecen */
#v139CommercialHost,#v141CommercialHost,#v133CommercialDemoHost{display:none!important}

.shell.sidebar-collapsed{grid-template-columns:74px minmax(0,1fr)!important}

@media(max-width:900px){
  .main{padding:8px 8px 76px!important}
  .hero{min-height:auto!important;border-radius:14px!important;padding:14px!important}
  .hero h1{font-size:20px!important}
  .filters:not(.hidden),#globalFilters:not(.hidden){
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    padding:9px!important;gap:7px!important;border-radius:13px!important;
  }
  .switches:not(.hidden),#operativoNav:not(.hidden),#analysisNav:not(.hidden),.v125-tabs:not(.hidden){
    overflow-x:auto!important;flex-wrap:nowrap!important;padding:4px!important;
  }
  .switch,.v125-tab,#operativoNav button,#analysisNav button{white-space:nowrap!important}
}
@media(max-width:560px){
  .filters:not(.hidden),#globalFilters:not(.hidden){grid-template-columns:1fr!important}
}
</style>'''

    @m.app.middleware('http')
    async def _v157_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode('utf-8', errors='replace')
            if 'v157-option1-boceto-css' not in html:
                html = html.replace('</head>', css + '</head>', 1)
            headers = dict(getattr(response, 'headers', {}) or {})
            headers.pop('content-length', None)
            headers.update({
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma':'no-cache',
                'Expires':'0',
                'X-Operations-UI-Version':'V157-OPTION1-BOCETO-SINGLE-FILTER'
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f'[V157] HTML warning: {type(exc).__name__}: {exc}', flush=True)
            return response

    m._V157_OPTION1_BOCETO = True
    print('[V157] Opción 1 boceto activa; filtro único nativo; tablas/gráficas/PDF/Excel preservados.', flush=True)
