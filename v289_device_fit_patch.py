"""V289 · Adaptación de pantalla sin rediseño.

Capa únicamente CSS, aplicada tras las autoridades V260–V288.
Conserva el DOM, columnas lógicas, cálculos, endpoints, roles y pestañas.
"""


def install(m):
    if getattr(m, "_V289_DEVICE_FIT", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''<style id="v289-device-fit-css">
/* V289 · mismos reportes, ancho real de la pantalla y scroll nativo */
:root { --v289-inline-space: clamp(4px, .9vw, 12px); }
html, body {
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: clip;
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
}
*, *::before, *::after { box-sizing: border-box; }

/* Un hijo de Grid/Flex nunca debe ensanchar la página. */
#appView, .shell, .main, .page, .page.active,
#operativoCentro, #operativoDynamic, #operativoDynamicContent,
#analysisDynamic, #analysisContent, #globalContent,
.panel, .card, .kpi, .report-kpi, .filters,
.kpis, .cards, .report-kpis, .grid,
#operativoPeriodBar, #v161FilterBar, #v161FilterGrid,
.v279, .v281, .v288-capture-panel {
  min-width: 0 !important;
  max-width: 100% !important;
}
.shell, .main { min-inline-size: 0 !important; }
.main { width: auto !important; }
.main > * { min-width: 0; }
.main img, .main video, .main canvas { max-inline-size: 100%; height: auto; }
.main .hero, .main .panel, .main .card {
  overflow-wrap: break-word;
}

/* Las cifras conservan su alineación; los títulos sí pueden ajustarse. */
.kpi .lab, .report-kpi .rk-label, .card h3,
.panel h3, .v288-kpi-label, .v281-kpi-label,
.hero h1, .title {
  min-width: 0;
  overflow-wrap: anywhere;
}
.report-kpis > *, .kpis > *, .cards > *,
.v288-capture-grid > *, #v288DailyKpis > * {
  min-width: 0;
}

/* Tablas y gráficos largos desplazan sólo dentro de su contenedor.
   No modificar el ancho mínimo ni reordenar columnas. */
.tablewrap, .table-scroll, .table-responsive,
.model-sticky-table, .model-scroll-30, .table-scroll-35,
.monthly-cross-desktop, .v168-pivot-wrap, .v168-plan-matrix,
.v279-tablewrap, .v278-tw, .chart-scroll {
  min-width: 0 !important;
  max-width: 100% !important;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
  touch-action: pan-x pan-y pinch-zoom !important;
}
.tablewrap, .table-scroll, .table-responsive, .v279-tablewrap,
.monthly-cross-desktop, .v168-pivot-wrap, .v168-plan-matrix {
  overflow-x: auto !important;
}
.tablewrap > table, .table-scroll > table, .table-responsive > table {
  max-width: none;
}
#operativoNav, #analysisNav, #v200OperationTabs,
.rt-carousel, .switches, .op-tabs {
  max-width: 100% !important;
  min-width: 0 !important;
  touch-action: pan-x pan-y pinch-zoom !important;
}

/* El desplazamiento vertical es de la página y nunca requiere zoom. */
html, body, #appView:not(.hidden), .shell, .main,
section.page, section.page.active {
  min-height: 0;
  height: auto;
  overscroll-behavior-y: auto;
}
@media (min-width: 768px) {
  .shell { min-height: 100dvh; }
}
@media (max-width: 1024px) {
  .main { min-width: 0 !important; max-width: 100% !important; }
  .panel, .card, .kpi, .report-kpi { min-width: 0 !important; }
  .filters .filter, #operativoPeriodBar .or-fcontrol,
  #v161FilterGrid .v161-field {
    min-width: 0 !important;
    max-width: 100% !important;
  }
  .filters input, .filters select,
  #operativoPeriodBar input, #operativoPeriodBar select,
  #v161FilterGrid input, #v161FilterGrid select {
    min-width: 0 !important;
    max-width: 100% !important;
    text-overflow: ellipsis;
  }
}
@media (max-width: 767px) {
  .main {
    width: 100% !important;
    padding-inline: var(--v289-inline-space) !important;
    padding-bottom: calc(72px + env(safe-area-inset-bottom)) !important;
    overflow-x: clip !important;
  }
  section.page, section.page.active,
  #operativoDynamicContent, #analysisContent {
    overflow-y: visible !important;
    touch-action: pan-x pan-y pinch-zoom !important;
  }
  .kpi, .report-kpi, .card, .panel { min-width: 0 !important; }
  .hero h1, .title, .card h3 { max-width: 100%; }
  /* Evita zoom involuntario al enfocar campos en Safari iOS sin
     agrandar permanentemente los controles compactos aprobados. */
  @supports (-webkit-touch-callout: none) {
    input:focus:not([type="checkbox"]):not([type="radio"]),
    select:focus, textarea:focus { font-size: 16px !important; }
  }
}
@media (max-width: 360px) {
  .main { padding-inline: 4px !important; }
  .kpi, .report-kpi, .card, .panel { padding-inline: clamp(4px, 1.2vw, 8px); }
}
@media (prefers-reduced-motion: reduce) {
  html, body { scroll-behavior: auto !important; }
}
</style>'''

    @m.app.middleware("http")
    async def v289_device_fit(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        html = body.decode("utf-8", errors="replace")
        if 'id="v289-device-fit-css"' not in html:
            html = html.replace("</head>", css + "</head>", 1)
        headers = dict(getattr(response, "headers", {}) or {})
        headers.pop("content-length", None)
        headers["X-Operations-UI-Version"] = "V289-DEVICE-FIT"
        return HTMLResponse(html, status_code=response.status_code, headers=headers)

    m._V289_DEVICE_FIT = True
    print("[V289] Device fit CSS installed without changing report layouts.", flush=True)
