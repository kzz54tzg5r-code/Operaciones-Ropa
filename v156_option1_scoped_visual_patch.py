"""V156.1 · Opción 1 visual estable, sin alterar reportes.

Corrección crítica del congelamiento de Chrome: se elimina por completo el
MutationObserver y el setInterval que reaccionaban a cambios de clase y podían
entrar en un ciclo de repintado continuo.

Reglas:
- Sólo CSS de presentación.
- No reemplaza tablas ni gráficas.
- No modifica cálculos, APIs, PDF ni Excel.
- No monta demos de Análisis Comercial.
- Cada módulo conserva exclusivamente su contenido real.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V156_SCOPED_OPTION1", False):
        return

    css = r'''<style id="v156-scoped-option1-css">
:root{
  --v156-navy:#0b3f7d;
  --v156-navy2:#0d4d91;
  --v156-blue:#1675f5;
  --v156-soft:#f3f7fc;
  --v156-line:#d8e5f3;
  --v156-ink:#103d78;
}
body{background:var(--v156-soft)!important;}
.shell{grid-template-columns:230px minmax(0,1fr)!important;background:var(--v156-soft)!important}
.side{
  background:linear-gradient(180deg,#0a3c76 0%,#0d4d91 60%,#0a386e 100%)!important;
  border-right:0!important;padding:16px 12px!important;
  box-shadow:8px 0 28px rgba(15,54,101,.08)!important;
}
.sidebrand{padding:6px 8px 18px!important;border-bottom:1px solid rgba(255,255,255,.14)!important;margin-bottom:6px!important}
.sidebrand b,.sidebrand small,.profile b,.profile small{color:#fff!important}
.group{color:rgba(255,255,255,.55)!important}
.nav{color:rgba(255,255,255,.9)!important;border-radius:11px!important;padding:11px 12px!important;margin:1px 0!important;background:transparent!important}
.nav:hover{background:rgba(255,255,255,.08)!important}
.nav.active{background:var(--v156-blue)!important;color:#fff!important;box-shadow:0 7px 16px rgba(0,38,100,.22)!important}
.nav small{color:inherit!important;opacity:.72!important}
.profile{border-top:1px solid rgba(255,255,255,.16)!important}
.logout,.sidebar-toggle{background:rgba(255,255,255,.1)!important;border-color:rgba(255,255,255,.24)!important;color:#fff!important}

.main{padding:16px 20px 86px!important;background:var(--v156-soft)!important}
.hero{
  position:relative!important;overflow:hidden!important;
  background:linear-gradient(118deg,#0b3e7c 0%,#0c559f 70%,#0b407d 100%)!important;
  border-radius:18px!important;padding:20px 24px!important;
  border:1px solid rgba(255,255,255,.12)!important;box-shadow:none!important;
}
.hero:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 80% 35%,rgba(255,255,255,.11),transparent 28%),linear-gradient(130deg,transparent 56%,rgba(255,255,255,.05) 56%,rgba(255,255,255,.05) 67%,transparent 67%);pointer-events:none}
.hero h1{font-size:27px!important;letter-spacing:-.02em!important;position:relative!important}
.hero p{font-size:10px!important;color:#d7e8fb!important;position:relative!important}

/* Filtros: misma lógica, mismos campos, sólo nueva presentación. */
.filters,#globalFilters,#v103FilterShell{
  background:#fff!important;border:1px solid var(--v156-line)!important;border-radius:16px!important;
  padding:12px 14px!important;margin:11px 0!important;gap:10px!important;
  box-shadow:0 4px 14px rgba(30,79,135,.045)!important;
}
.filter{min-width:145px;flex:1 1 145px}
.filter label{color:#466887!important;font-size:8px!important;letter-spacing:.03em!important;margin-bottom:5px!important}
.filter select,.filter input,#globalFilters select,#globalFilters input,#v103FilterShell select,#v103FilterShell input{
  min-height:40px!important;border:1px solid #cfdeee!important;border-radius:10px!important;background:#fff!important;color:#143d70!important;
}
.primary{border-radius:10px!important;min-height:40px!important;background:var(--v156-blue)!important}

/* Pestañas: mismo orden, contenido y eventos. */
.switches,#operativoNav,#analysisNav,.v125-tabs{
  background:#fff!important;border:1px solid var(--v156-line)!important;border-radius:14px!important;
  padding:5px!important;gap:5px!important;margin:10px 0!important;
}
.switch,.v125-tab{border-radius:10px!important}
.switch.active,.v125-tab.active{background:var(--v156-blue)!important;color:#fff!important;box-shadow:0 4px 10px rgba(22,117,245,.18)!important}

/* Tarjetas y contenedores. No se tocan table, canvas, svg ni exportaciones. */
.kpis,.report-kpis{gap:10px!important}
.kpi,.report-kpi,.card,.useritem{
  background:#fff!important;border:1px solid var(--v156-line)!important;border-radius:15px!important;
  box-shadow:0 3px 12px rgba(29,76,126,.04)!important;
}
.panel,.chart-box,.drop{
  background:#fff!important;border-color:var(--v156-line)!important;border-radius:15px!important;
  box-shadow:0 3px 12px rgba(29,76,126,.035)!important;
}
.val,.report-kpi .rk-value{color:var(--v156-ink)!important}
.title{color:var(--v156-ink)!important;font-size:17px!important}

/* Blindaje: hosts de demos comerciales antiguos nunca se muestran. */
#v139CommercialHost,#v141CommercialHost,#v133CommercialDemoHost{display:none!important}

.shell.sidebar-collapsed{grid-template-columns:76px minmax(0,1fr)!important}

@media(max-width:900px){
  .main{padding:8px 8px 76px!important}
  .hero{border-radius:14px!important;padding:15px 14px!important}
  .hero h1{font-size:21px!important}
  .filters,#globalFilters,#v103FilterShell{padding:9px!important;gap:7px!important;border-radius:13px!important}
  .switches,#operativoNav,#analysisNav,.v125-tabs{overflow-x:auto!important;flex-wrap:nowrap!important}
}
</style>'''

    @m.app.middleware('http')
    async def _v156_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode('utf-8', errors='replace')
            if 'v156-scoped-option1-css' not in html:
                html = html.replace('</head>', css + '</head>', 1)
            headers = dict(getattr(response, 'headers', {}) or {})
            headers.pop('content-length', None)
            headers.update({
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma':'no-cache',
                'Expires':'0',
                'X-Operations-UI-Version':'V156.1-STABLE-CSS-ONLY'
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f'[V156.1] HTML warning: {type(exc).__name__}: {exc}', flush=True)
            return response

    m._V156_SCOPED_OPTION1 = True
    print('[V156.1] Diseño visual estable cargado; sin observer, intervalos ni JS reactivo.', flush=True)
