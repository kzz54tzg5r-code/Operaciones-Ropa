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

/* ==============================================================
 * V290 · refuerzo visual móvil basado en captura real del iPhone.
 * Mantiene las mismas tarjetas, tablas, colores, datos y pestañas.
 * Sólo cambia distribución y tipografía en anchuras móviles.
 * ============================================================== */
@media (max-width: 700px) {
  /* La página entera desplaza verticalmente. Las tablas anchas desplazan
     horizontalmente DENTRO del reporte, sin forzar zoom ni cortar importes. */
  html,body,#appView:not(.hidden),.shell,.main,section.page.active,
  #operativoDynamicContent,#analysisContent {
    overflow-y: visible !important;
    overscroll-behavior-y: auto !important;
    touch-action: pan-y pinch-zoom !important;
  }
  html,body { overflow-x:hidden !important; }
  .main { padding-inline: max(6px,env(safe-area-inset-left)) max(6px,env(safe-area-inset-right)) !important; }
  :is(.tablewrap,.rr243-tablewrap,.monthly-cross-desktop,.model-sticky-table,
      .table-scroll,.table-responsive,.v279-tablewrap,.v281-tablewrap) {
    min-width:0 !important;
    max-width:100% !important;
    overflow-x:auto !important;
    -webkit-overflow-scrolling:touch !important;
    touch-action:pan-x pan-y pinch-zoom !important;
  }

  /* Hasta diez pestañas: 2 filas de cinco, todas visibles y sin carrusel
     horizontal que obligue a desplazar el menú. Mantener su orden e iconos. */
  html body.v238-module-operativo #operativoNav:not(.hidden),
  html body.v238-module-analysis #analysisNav:not(.hidden),
  html body.v238-module-operation #v200OperationTabs:not(.hidden) {
    display:grid !important;
    grid-template-columns:repeat(5,minmax(0,1fr)) !important;
    grid-template-rows:none !important;
    grid-auto-rows:minmax(52px,auto) !important;
    height:auto !important;
    min-height:0 !important;
    max-height:none !important;
    gap:4px !important;
    margin:7px 0 9px !important;
    padding:0 !important;
    overflow:visible !important;
    white-space:normal !important;
    touch-action:pan-y pinch-zoom !important;
  }
  html body :is(#operativoNav,#analysisNav,#v200OperationTabs) > button {
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    width:100% !important;
    min-width:0 !important;
    min-height:52px !important;
    height:auto !important;
    max-height:none !important;
    padding:5px 2px !important;
    gap:3px !important;
    border-radius:10px !important;
    line-height:1.1 !important;
    overflow:hidden !important;
  }
  html body :is(#operativoNav,#analysisNav,#v200OperationTabs)
    :is(.v238-tab-icon,.v232-tab-icon) {
    width:19px !important;
    height:19px !important;
    min-width:19px !important;
    min-height:19px !important;
    flex-shrink:0 !important;
  }
  html body :is(#operativoNav,#analysisNav,#v200OperationTabs)
    :is(.v238-tab-label,.v232-tab-label) {
    display:block !important;
    width:100% !important;
    min-height:0 !important;
    height:auto !important;
    max-height:none !important;
    font-size:clamp(8px,2.35vw,9.5px) !important;
    line-height:1.12 !important;
    white-space:normal !important;
    word-break:normal !important;
    overflow-wrap:break-word !important;
    text-align:center !important;
    overflow:visible !important;
  }

  /* Títulos y cabecera: proporciones de laptop, sin gigantismo ni recortes. */
  .hero { min-height:0 !important; padding:9px 12px !important; }
  .hero h1 { font-size:clamp(18px,4.8vw,21px) !important;line-height:1.1 !important; }
  .hero p { font-size:10px !important;line-height:1.2 !important; }
  #operativoDynamicTitle { font-size:clamp(18px,4.5vw,20px) !important;line-height:1.15 !important; }
  #operativoDynamicSub { font-size:10px !important;line-height:1.2 !important; }
  #operativoDynamicContent>.title { font-size:clamp(16px,4.1vw,19px) !important;line-height:1.12 !important;margin:10px 0 6px !important; }

  #operativoPeriodBar>.or-report-filter-brand {
    min-height:42px !important;
    height:auto !important;
    padding:7px 9px !important;
    gap:8px !important;
  }
  #operativoPeriodBar>.or-report-filter-brand b {
    font-size:clamp(13px,3.8vw,17px) !important;
    line-height:1.05 !important;
  }
  #operativoPeriodBar>.or-report-filter-brand small {
    font-size:9px !important;
    line-height:1.12 !important;
  }
  #operativoPeriodBar .or-report-filter-brand-icon {
    width:33px !important;
    height:33px !important;
    min-width:33px !important;
  }
  #operativoPeriodBar .v266-period-title,
  #operativoPeriodBar .or-fcontrol label { font-size:9px !important; }
  #operativoPeriodBar .v266-period-btn {
    font-size:clamp(8px,2.2vw,10px) !important;
    line-height:1.15 !important;
    min-width:0 !important;
  }
  #operativoPeriodBar .v266-period-mode-icon,
  #operativoPeriodBar .v266-period-mode-icon svg {
    width:12px !important;height:12px !important;min-width:12px !important;
  }

  /* CENTRO OPERATIVO · mismas seis tarjetas y mismos valores, en 3 × 2. */
  body.v271-center-parity #operativoDynamicContent .mct-kpi-grid {
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:5px !important;
    margin:5px 0 8px !important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi {
    height:auto !important;
    min-height:66px !important;
    max-height:none !important;
    padding:7px !important;
    border-radius:10px !important;
    overflow:hidden !important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-label {
    height:auto !important;
    min-height:17px !important;
    max-height:none !important;
    font-size:8px !important;
    line-height:1.12 !important;
    overflow:visible !important;
    white-space:normal !important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-value {
    font-size:clamp(13px,3.6vw,16px) !important;
    line-height:1.06 !important;
    margin:5px 0 3px !important;
    overflow:visible !important;
    text-overflow:clip !important;
    white-space:normal !important;
    word-break:keep-all !important;
    overflow-wrap:normal !important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-kpi-sub {
    font-size:8px !important;
    line-height:1.1 !important;
    white-space:normal !important;
    overflow:visible !important;
    text-overflow:clip !important;
  }

  /* Matriz principal: conserva sus seis columnas y jerarquía, con valores
     completos, sin quiebres de dígitos ni letras microscopicas. */
  body.v271-center-parity #operativoDynamicContent .monthly-cross-desktop {
    overflow-x:auto !important;
    overflow-y:visible !important;
  }
  body.v271-center-parity #operativoDynamicContent table.monthly-cross-table.v273-fit {
    width:100% !important;
    min-width:0 !important;
    table-layout:fixed !important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table thead th {
    font-size:8px !important;
    line-height:1.1 !important;
    padding:5px 2px !important;
    height:34px !important;
    min-height:34px !important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td {
    font-size:8.5px !important;
    line-height:1.16 !important;
    padding:5px 2px !important;
    height:auto !important;
    min-height:27px !important;
    overflow-wrap:normal !important;
    word-break:normal !important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td b {
    font-size:8.7px !important;line-height:1.12 !important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table tbody td.v273-num {
    white-space:nowrap !important;
    overflow:visible !important;
    font-variant-numeric:tabular-nums !important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat {
    font-size:8px !important;
    line-height:1.12 !important;
    overflow-wrap:break-word !important;
  }
  body.v271-center-parity #operativoDynamicContent .monthly-cross-table .monthly-cat span {
    font-size:7px !important;line-height:1.12 !important;
  }
  body.v271-center-parity #operativoDynamicContent .mct-value-pieces small {
    font-size:7px !important;
  }
}

/* En pantallas extremadamente angostas usar 4 pestañas por fila y
   permitir scroll local para matrices que no caben con 6 columnas. */
@media (max-width:360px) {
  html body.v238-module-operativo #operativoNav:not(.hidden),
  html body.v238-module-analysis #analysisNav:not(.hidden),
  html body.v238-module-operation #v200OperationTabs:not(.hidden) {
    grid-template-columns:repeat(4,minmax(0,1fr)) !important;
    grid-auto-rows:minmax(50px,auto) !important;
  }
  body.v271-center-parity #operativoDynamicContent table.monthly-cross-table.v273-scroll {
    width:max-content !important;
    min-width:440px !important;
    max-width:none !important;
    table-layout:auto !important;
  }
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
