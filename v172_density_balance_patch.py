"""V172 · Balance de densidad: móvil compacto y escritorio ampliado."""
from __future__ import annotations


def install(m):
    if getattr(m, "_V172_DENSITY_BALANCE", False):
        return

    css = r'''<style id="v172-density-balance-css">
/* PC: mayor lectura a distancia. */
@media(min-width:901px){
  body{font-size:13px!important}
  .main{padding:18px 24px 32px!important}
  .hero h1{font-size:27px!important}.hero p{font-size:12px!important}
  .title{font-size:23px!important}.subtitle{font-size:11.5px!important}
  .filter label,.v161-field label,.v166-internal-filter label{font-size:10.5px!important}
  .filter select,.filter input,.v161-field select,.v161-field input,.v166-internal-filter select{font-size:13px!important;min-height:48px!important}
  button,.switch,.v125-tabs button,.op-tabs button{font-size:12px!important}
  .kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi{min-height:120px!important}
  .lab,.report-kpi .rk-label,.v149-kpi small,.v126-kpi small,.v125-kpi small{font-size:10px!important}
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b{font-size:32px!important}
  .note,.report-kpi .rk-sub,.v149-kpi span,.v126-kpi span,.v125-kpi span{font-size:10.5px!important}
  .table{font-size:11.5px!important}.table th{font-size:11px!important;padding:12px 11px!important}.table td{font-size:11.5px!important;padding:11px!important}
  .chart-title,.panel-head b{font-size:15px!important}
}

/* Móvil: máxima información visible sin perder legibilidad. */
@media(max-width:900px){
  body{font-size:10px!important}
  .main{padding:5px 6px calc(76px + env(safe-area-inset-bottom))!important}
  .hero{padding:8px 9px!important;min-height:52px!important}.hero h1{font-size:16px!important}.hero p{font-size:7.5px!important;margin-top:2px!important}
  .title{font-size:16px!important;margin:9px 1px 5px!important}.subtitle{font-size:7.5px!important;line-height:1.3!important;margin-bottom:5px!important}
  .filters,.v161-filter-shell{padding:5px!important}.v161-filter-grid,.filters{gap:5px!important}
  .filter label,.v161-field label{font-size:6.5px!important;margin-bottom:2px!important}
  .filter select,.filter input,.v161-field select,.v161-field input{min-height:40px!important;font-size:11px!important;padding-top:6px!important;padding-bottom:6px!important}
  .primary,.v161-actions button{min-height:40px!important;font-size:11px!important}

  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{gap:5px!important;margin:5px 0 7px!important}
  .kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi,.v164-matrix-kpi,.v165-mini-kpi,.v168-plan-kpi,.sales-kpi{
    min-height:88px!important;padding:8px 5px 7px 39px!important;border-radius:9px!important
  }
  .v166-kpi-icon,.v164-kpi-icon{left:8px!important;top:11px!important;width:24px!important;height:24px!important}
  .v166-kpi-icon svg,.v164-kpi-icon svg{width:14px!important;height:14px!important}
  .lab,.report-kpi .rk-label,.v149-kpi small,.v126-kpi small,.v125-kpi small,.v164-matrix-kpi small,.v165-mini-kpi small,.sales-kpi .sl{
    font-size:6.3px!important;line-height:1.12!important;letter-spacing:.01em!important
  }
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b,.v164-matrix-kpi b,.v165-mini-kpi b,.v168-plan-kpi b,.sales-kpi .sv{
    font-size:clamp(17px,5.1vw,23px)!important;line-height:1!important;margin:5px 0 3px!important;letter-spacing:-.04em!important
  }
  .note,.report-kpi .rk-sub,.v149-kpi span,.v126-kpi span,.v125-kpi span,.v164-matrix-kpi span,.v168-plan-kpi span,.sales-kpi .ss{
    font-size:6.7px!important;line-height:1.18!important
  }
  #analysisNav,#operativoNav,.v125-tabs,.op-tabs,.switches{gap:4px!important;padding:5px!important}
  #analysisNav>button,#operativoNav>button,.v125-tabs>button,.op-tabs>button,.switches>button{
    flex-basis:108px!important;min-width:108px!important;min-height:46px!important;padding:5px!important;font-size:7.5px!important
  }
  .table{font-size:7.5px!important;min-width:680px!important}.table th{font-size:7px!important;padding:7px 6px!important}.table td{font-size:7.5px!important;padding:6px!important}
  .panel,.card,.chart-box{padding:8px!important}.chart-title,.panel-head b{font-size:10px!important}
  .mobile{min-height:62px!important;padding:4px 4px calc(4px + env(safe-area-inset-bottom))!important}
  .mnav{min-height:49px!important;font-size:7px!important;padding:4px 1px!important}.mnav-icon{font-size:17px!important;line-height:18px!important}
}

@media(max-width:340px){
  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b{font-size:16px!important}
}
</style>'''

    @m.app.middleware("http")
    async def v172_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v172-density-balance-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            headers = dict(response.headers); headers.pop("content-length", None)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V172_DENSITY_BALANCE = True
    print("[V172] móvil compacto y escritorio ampliado instalados.", flush=True)
