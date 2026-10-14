"""V322 · Autoridad responsive universal tras la auditoría de capas V47–V321.

Sólo actúa en anchos <=1180px; escritorio amplio conserva el CSS existente.
No modifica datos, DOM de reportes, fórmulas, filtros, permisos ni endpoints.
"""

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V322_UNIVERSAL_RESPONSIVE_AUDIT", False):
        return

    css = r'''<style id="v322-universal-responsive-css">
/* V322: una sola raíz de scroll vertical; scroll horizontal limitado a rails/tablas. */
@media (max-width: 1180px) {
  html {
    width: 100% !important;
    max-width: 100% !important;
    min-height: 100% !important;
    height: auto !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    overscroll-behavior-y: auto !important;
    -webkit-text-size-adjust: 100% !important;
    text-size-adjust: 100% !important;
  }
  body {
    width: 100% !important;
    max-width: 100% !important;
    min-height: 100dvh !important;
    height: auto !important;
    overflow-x: hidden !important;
    overflow-y: visible !important;
    overscroll-behavior-y: auto !important;
    touch-action: pan-x pan-y pinch-zoom !important;
  }
  /* V321 define scroll para el host de Bonos; el viewport raíz sigue siendo html. */
  body[data-v313="1"] {
    overflow-y: visible !important;
  }
  html:has(body[data-v313="1"]) {
    overflow-y: auto !important;
  }

  #appView:not(.hidden),
  .shell,
  main.main,
  section.page,
  section.page.active,
  #operativoCentro,
  #operativoDynamic,
  #operativoDynamicContent,
  #analysisDynamic,
  #analysisContent,
  #globalContent,
  .report-content,
  .report-body,
  .dashboard-content {
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow-y: visible !important;
    overscroll-behavior-y: auto !important;
    touch-action: pan-x pan-y pinch-zoom !important;
  }
  main.main {
    min-width: 0 !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
  }
  .main > *,
  .panel,
  .card,
  .kpi,
  .report-kpi,
  .filters,
  .kpis,
  .report-kpis,
  .cards,
  .grid,
  #operativoPeriodBar,
  #v161FilterBar,
  #v161FilterGrid,
  .v313,
  .v313 > *,
  .v313-cut,
  .v313-kpi,
  .v313-panel {
    min-width: 0 !important;
    max-width: 100% !important;
  }
  img, video, canvas, svg, iframe {
    max-width: 100%;
  }

  /* Las pestañas conservan el orden, pero ya no se comprimen en cinco columnas. */
  html body :is(#operativoNav, #analysisNav, #v200OperationTabs):not(.hidden) {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    grid-template-columns: none !important;
    grid-template-rows: none !important;
    grid-auto-rows: auto !important;
    align-items: stretch !important;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    white-space: nowrap !important;
    position: relative !important;
    top: auto !important;
    scroll-snap-type: x proximity !important;
    scrollbar-width: thin !important;
    -webkit-overflow-scrolling: touch !important;
    overscroll-behavior-x: contain !important;
    overscroll-behavior-y: auto !important;
    touch-action: pan-x pan-y pinch-zoom !important;
  }
  html body :is(#operativoNav, #analysisNav, #v200OperationTabs):not(.hidden) > button,
  html body :is(#operativoNav, #analysisNav, #v200OperationTabs):not(.hidden) > div > button {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 76px !important;
    max-width: 156px !important;
    min-height: 40px !important;
    height: auto !important;
    max-height: none !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    text-align: center !important;
    scroll-snap-align: start !important;
  }
  html body :is(#operativoNav, #analysisNav, #v200OperationTabs)::-webkit-scrollbar {
    height: 3px !important;
  }

  /* Tablas: mantener el ancho lógico de las columnas; desplazar sólo su marco. */
  :is(
    .tablewrap, .table-scroll, .table-responsive, .model-sticky-table,
    .model-scroll-30, .table-scroll-35, .monthly-cross-desktop,
    .v168-pivot-wrap, .v168-plan-matrix, .v279-tablewrap, .v281-tablewrap,
    .v281-tw, .rr243-tablewrap, .v313-scroll, .v321-history-wrap,
    .lingerie-table-wrap, .chart-scroll, .sales-chart-scroll
  ) {
    min-width: 0 !important;
    max-width: 100% !important;
    -webkit-overflow-scrolling: touch !important;
    overscroll-behavior-x: contain !important;
    overscroll-behavior-y: auto !important;
    touch-action: pan-x pan-y pinch-zoom !important;
  }
  :is(
    .tablewrap, .table-scroll, .table-responsive, .model-sticky-table,
    .model-scroll-30, .table-scroll-35, .monthly-cross-desktop,
    .v168-pivot-wrap, .v168-plan-matrix, .v279-tablewrap, .v281-tablewrap,
    .v281-tw, .rr243-tablewrap, .v313-scroll, .v321-history-wrap,
    .lingerie-table-wrap
  ) {
    min-height: 0 !important;
    height: auto !important;
    max-height: none !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
  }
  :is(.tablewrap, .table-scroll, .table-responsive, .v313-scroll) > table {
    max-width: none !important;
  }

  /* Los filtros y formularios no deben ensanchar la página. */
  .filters .filter,
  #operativoPeriodBar .or-fcontrol,
  #v161FilterGrid .v161-field {
    min-width: 0 !important;
    max-width: 100% !important;
  }
  .filters input, .filters select,
  #operativoPeriodBar input, #operativoPeriodBar select,
  #v161FilterGrid input, #v161FilterGrid select,
  .v313-filters input, .v313-filters select,
  .v313-upload-grid input, .v313-upload-grid select {
    box-sizing: border-box !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }

  /* Modales con su propio scroll cuando no caben en la altura real disponible. */
  .modal-backdrop {
    max-height: 100dvh !important;
    overflow-y: auto !important;
    overscroll-behavior-y: contain !important;
    -webkit-overflow-scrolling: touch !important;
  }
  .modal-card {
    max-width: 100% !important;
    max-height: calc(100dvh - 24px - env(safe-area-inset-top) - env(safe-area-inset-bottom)) !important;
    overflow-y: auto !important;
    overscroll-behavior-y: contain !important;
    -webkit-overflow-scrolling: touch !important;
  }
}

/* Móvil: reserva el espacio de la barra inferior y respeta las áreas seguras. */
@media (max-width: 900px) {
  html body main.main {
    padding-bottom: calc(86px + env(safe-area-inset-bottom)) !important;
  }
  html body .mobile {
    bottom: 0 !important;
    padding-bottom: calc(5px + env(safe-area-inset-bottom)) !important;
    max-width: 100vw !important;
  }
  html body .mnav {
    min-width: 0 !important;
    touch-action: manipulation !important;
  }
  .modal-backdrop {
    align-items: flex-start !important;
    justify-content: center !important;
    padding:
      max(10px, env(safe-area-inset-top))
      max(10px, env(safe-area-inset-right))
      max(10px, env(safe-area-inset-bottom))
      max(10px, env(safe-area-inset-left)) !important;
  }
  .modal-card {
    width: 100% !important;
  }
  .filters input, .filters select,
  #operativoPeriodBar input, #operativoPeriodBar select,
  #v161FilterGrid input, #v161FilterGrid select {
    min-height: 36px !important;
  }
}

/* Móvil compacto: no ocultar información ni encoger más las columnas de las tablas. */
@media (max-width: 430px) {
  html body main.main {
    padding-left: max(5px, env(safe-area-inset-left)) !important;
    padding-right: max(5px, env(safe-area-inset-right)) !important;
  }
  html body :is(#operativoNav, #analysisNav, #v200OperationTabs):not(.hidden) > button,
  html body :is(#operativoNav, #analysisNav, #v200OperationTabs):not(.hidden) > div > button {
    min-width: 74px !important;
    max-width: 132px !important;
    min-height: 40px !important;
    font-size: clamp(8px, 2.5vw, 10px) !important;
  }
  .modal-card {
    max-height: calc(100dvh - 16px - env(safe-area-inset-top) - env(safe-area-inset-bottom)) !important;
  }
}
</style>'''

    @m.app.middleware("http")
    async def v322_universal_responsive_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v322-universal-responsive-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V322-UNIVERSAL-RESPONSIVE-AUDIT",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V322] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V322_UNIVERSAL_RESPONSIVE_AUDIT = True
    print("[V322] Autoridad responsive universal instalada tras la auditoría V47–V321.", flush=True)
