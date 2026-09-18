"""V171 · Legibilidad responsive para móvil y escritorio.

Mantiene toda la estructura y datos de V170. Sólo corrige escala, distribución,
desbordamiento y áreas seguras para que cifras completas sean visibles.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V171_RESPONSIVE_TYPOGRAPHY", False):
        return

    css = r'''<style id="v171-responsive-typography-css">
/* Base legible y números que nunca se recortan. */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
.kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi,.v164-matrix-kpi,.v165-mini-kpi,.sales-kpi{min-width:0!important}
.val,.rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b,.v164-matrix-kpi b,.v165-mini-kpi b,.sales-kpi .sv{
  max-width:100%!important;white-space:nowrap!important;overflow:visible!important;text-overflow:clip!important;font-variant-numeric:tabular-nums
}
.tablewrap{position:relative}
.table th,.table td{vertical-align:middle}

/* Escritorio: recuperar tamaño visual; las capas compactas anteriores dejaron texto de 7–8 px. */
@media(min-width:901px){
  body{font-size:12px!important}
  .main{padding:16px 20px 28px!important}
  .hero h1{font-size:24px!important}.hero p{font-size:11px!important}
  .title{font-size:21px!important;line-height:1.2!important;margin:16px 0 8px!important}
  .subtitle{font-size:10.5px!important;line-height:1.45!important}
  .filter label,.v161-field label,.v166-internal-filter label{font-size:9.5px!important}
  .filter select,.filter input,.v161-field select,.v161-field input,.v166-internal-filter select{font-size:12px!important;min-height:46px!important}
  button,.switch,.v125-tabs button,.op-tabs button{font-size:11px!important}
  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis{gap:11px!important}
  .kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi{min-height:112px!important;padding-top:14px!important;padding-bottom:13px!important}
  .lab,.report-kpi .rk-label,.v149-kpi small,.v126-kpi small,.v125-kpi small{font-size:9px!important;line-height:1.25!important}
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b{font-size:28px!important;line-height:1.05!important;margin:8px 0 5px!important}
  .note,.report-kpi .rk-sub,.v149-kpi span,.v126-kpi span,.v125-kpi span{font-size:9.5px!important;line-height:1.35!important}
  .panel,.card,.chart-box{font-size:11px!important}
  .chart-title,.panel-head b{font-size:14px!important}
  .table{font-size:10.5px!important}.table th{font-size:10px!important;padding:11px 10px!important}.table td{padding:10px!important;line-height:1.35!important}
  .sales-kpi .sl{font-size:9px!important}.sales-kpi .sv{font-size:25px!important}.sales-kpi .ss{font-size:9.5px!important}
  .mnav{font-size:9px!important}
}

/* Móvil: dos KPIs reales por fila, navegación táctil y tablas sin comprimir. */
@media(max-width:900px){
  body{font-size:12px!important}
  .main{padding:8px 8px calc(92px + env(safe-area-inset-bottom))!important;overflow-x:hidden!important}
  .hero{padding:12px!important}.hero h1{font-size:19px!important}.hero p{font-size:9.5px!important}
  .title{font-size:20px!important;line-height:1.18!important;margin:14px 2px 7px!important}
  .subtitle{font-size:9.5px!important;line-height:1.4!important}

  .filters,.v161-filter-shell{padding:8px!important}
  .v161-filter-grid,.filters{gap:8px!important}
  .filter label,.v161-field label{font-size:8px!important;margin-bottom:5px!important}
  .filter select,.filter input,.v161-field select,.v161-field input{min-height:48px!important;font-size:14px!important;padding-top:9px!important;padding-bottom:9px!important}
  .primary,.v161-actions button{min-height:48px!important;font-size:13px!important}

  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{
    display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;width:100%!important
  }
  .kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi,.v164-matrix-kpi,.v165-mini-kpi,.v168-plan-kpi,.sales-kpi{
    width:100%!important;min-height:118px!important;padding:13px 10px 11px 47px!important;border-radius:12px!important;overflow:visible!important
  }
  .v166-kpi-icon,.v164-kpi-icon{left:10px!important;top:15px!important;width:29px!important;height:29px!important}
  .lab,.report-kpi .rk-label,.v149-kpi small,.v126-kpi small,.v125-kpi small,.v164-matrix-kpi small,.v165-mini-kpi small,.sales-kpi .sl{
    font-size:8px!important;line-height:1.22!important;letter-spacing:.02em!important;overflow-wrap:anywhere
  }
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b,.v164-matrix-kpi b,.v165-mini-kpi b,.v168-plan-kpi b,.sales-kpi .sv{
    font-size:clamp(21px,6.2vw,29px)!important;line-height:1.05!important;margin:8px 0 5px!important;letter-spacing:-.035em!important
  }
  .note,.report-kpi .rk-sub,.v149-kpi span,.v126-kpi span,.v125-kpi span,.v164-matrix-kpi span,.v168-plan-kpi span,.sales-kpi .ss{
    font-size:8.5px!important;line-height:1.3!important;overflow-wrap:anywhere
  }

  #analysisNav,#operativoNav,.v125-tabs,.op-tabs,.switches{
    display:flex!important;grid-template-columns:none!important;gap:6px!important;overflow-x:auto!important;overflow-y:hidden!important;flex-wrap:nowrap!important;
    padding:7px!important;-webkit-overflow-scrolling:touch!important;scroll-snap-type:x proximity;scrollbar-width:none
  }
  #analysisNav::-webkit-scrollbar,#operativoNav::-webkit-scrollbar,.v125-tabs::-webkit-scrollbar,.op-tabs::-webkit-scrollbar,.switches::-webkit-scrollbar{display:none}
  #analysisNav>button,#operativoNav>button,.v125-tabs>button,.op-tabs>button,.switches>button{
    flex:0 0 132px!important;min-width:132px!important;min-height:58px!important;padding:8px 7px!important;font-size:9px!important;line-height:1.2!important;scroll-snap-align:start
  }

  .tablewrap{width:100%!important;max-width:100%!important;overflow-x:auto!important;overflow-y:auto!important;-webkit-overflow-scrolling:touch!important}
  .table{width:max-content!important;min-width:760px!important;font-size:9px!important}
  .table th{font-size:8px!important;padding:9px 8px!important;white-space:nowrap!important;position:sticky!important;top:0!important;z-index:3!important}
  .table td{font-size:9px!important;padding:8px!important;line-height:1.3!important;white-space:nowrap!important}
  .table th:first-child,.table td:first-child{position:sticky!important;left:0!important;z-index:4!important}
  .table td:first-child{background:#fff!important}.table tr:nth-child(even) td:first-child{background:#f6f9fd!important}
  .chart-box,.panel,.card{max-width:100%!important;overflow:hidden!important}
  .chart-scroll,.sales-chart-scroll,.v168-pivot-wrap,.v168-plan-matrix{overflow:auto!important;-webkit-overflow-scrolling:touch!important}

  .mobile{min-height:72px!important;padding:6px 5px calc(7px + env(safe-area-inset-bottom))!important}
  .mnav{min-height:56px!important;font-size:8px!important;line-height:1.15!important;padding:6px 2px!important}
  .mnav-icon{font-size:20px!important;line-height:22px!important}
}

@media(max-width:520px){
  .v161-filter-grid,.filters{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .v161-actions,.filters .primary{grid-column:1/-1!important;width:100%!important}
  .sales-exec-controls{display:grid!important;grid-template-columns:1fr 1fr!important}
  .sales-exec-controls>*{min-width:0!important}
}

@media(max-width:340px){
  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{grid-template-columns:1fr!important}
  .v161-filter-grid,.filters{grid-template-columns:1fr!important}
}
</style>'''

    @m.app.middleware("http")
    async def v171_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v171-responsive-typography-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V171_RESPONSIVE_TYPOGRAPHY = True
    print("[V171] responsive móvil y tipografía de escritorio instalados.", flush=True)
