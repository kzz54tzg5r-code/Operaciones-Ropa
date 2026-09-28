"""V194 · Capa visual final móvil.
Se instala al final para prevalecer sobre V171/V172 y demás estilos históricos.
No modifica lógica de negocio, datos, endpoints ni permisos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V194_MOBILE_UI_FINAL", False):
        return

    css = r'''<style id="v194-mobile-ui-final-css">
/* ===== Barra superior / safe area ===== */
@media(max-width:900px){
  html,body{margin:0!important}
  .main{
    padding-top:max(14px,calc(env(safe-area-inset-top) + 10px))!important;
    padding-left:6px!important;
    padding-right:6px!important;
    padding-bottom:calc(18px + env(safe-area-inset-bottom))!important;
    overflow-x:hidden!important;
  }
  html.pwa-standalone .main{
    padding-top:max(16px,calc(env(safe-area-inset-top) + 12px))!important;
  }
  .hero{
    margin-top:0!important;
    min-height:62px!important;
    padding:10px 48px 10px 12px!important;
    border-radius:14px!important;
    box-shadow:0 5px 16px rgba(7,45,83,.12)!important;
  }
  .hero h1{font-size:17px!important;line-height:1.08!important}
  .hero p{font-size:8.5px!important;line-height:1.2!important;margin-top:4px!important}
  .or-mobile-menu-trigger{
    right:10px!important;left:auto!important;top:50%!important;
    transform:translateY(-50%)!important;
    width:35px!important;height:35px!important;
    border:1px solid rgba(255,255,255,.44)!important;
    background:rgba(0,26,58,.32)!important;
    color:#fff!important;border-radius:10px!important;
  }
}

/* ===== Tabs con iconografía outline ===== */
#operativoNav.op-tabs,#analysisNav{
  display:flex!important;
  grid-template-columns:none!important;
  flex-wrap:nowrap!important;
  align-items:center!important;
  gap:5px!important;
  width:100%!important;
  max-width:100%!important;
  min-height:0!important;
  padding:4px 2px 6px!important;
  margin:0 0 6px!important;
  background:transparent!important;
  border:0!important;
  border-radius:0!important;
  box-shadow:none!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  white-space:nowrap!important;
  -webkit-overflow-scrolling:touch!important;
  scrollbar-width:none!important;
  scroll-snap-type:x proximity;
}
#operativoNav.op-tabs::-webkit-scrollbar,#analysisNav::-webkit-scrollbar{display:none!important}
#operativoNav.op-tabs>div,#analysisNav>div{display:contents!important}
#operativoNav.op-tabs .switch,#analysisNav .switch{
  flex:0 0 auto!important;
  width:auto!important;
  min-width:0!important;
  min-height:39px!important;
  height:39px!important;
  margin:0!important;
  padding:0 9px!important;
  display:inline-flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:5px!important;
  border:1px solid #d8e2ed!important;
  border-radius:10px!important;
  background:#fff!important;
  color:#294b70!important;
  box-shadow:0 1px 3px rgba(18,55,91,.035)!important;
  font-size:8.6px!important;
  line-height:1!important;
  font-weight:850!important;
  white-space:nowrap!important;
  scroll-snap-align:start;
}
#operativoNav.op-tabs .switch.active,#analysisNav .switch.active{
  background:linear-gradient(135deg,#0b3a6e,#0d67bd)!important;
  border-color:#0b4b8a!important;
  color:#fff!important;
  box-shadow:0 4px 12px rgba(11,58,110,.17)!important;
}
#operativoNav.op-tabs .switch:hover,#analysisNav .switch:hover{
  border-color:#a9bfd6!important;
  background:#f7faff!important;
}
#operativoNav.op-tabs .switch.active:hover,#analysisNav .switch.active:hover{
  background:linear-gradient(135deg,#0b3a6e,#0d67bd)!important;
}
#operativoNav .or-tab-icon,#analysisNav .or-tab-icon{
  display:inline-grid!important;
  place-items:center!important;
  width:15px!important;height:15px!important;
  min-width:15px!important;flex:0 0 15px!important;
  color:#0d6fd1!important;
}
#operativoNav .or-tab-icon svg,#analysisNav .or-tab-icon svg{
  display:block!important;
  width:15px!important;height:15px!important;
  stroke:currentColor!important;
}
#operativoNav .switch.active .or-tab-icon,#analysisNav .switch.active .or-tab-icon{color:#fff!important}

/* ===== Filtro operativo V5: componente propio, no hereda .filter ===== */
#operativoPeriodBar.or-report-filter-card{
  position:relative!important;
  display:block!important;
  width:100%!important;
  min-width:0!important;
  margin:2px 0 8px!important;
  padding:0!important;
  overflow:hidden!important;
  background:#fff!important;
  border:1px solid #cddbea!important;
  border-radius:12px!important;
  box-shadow:0 4px 14px rgba(13,58,104,.055)!important;
}
#operativoPeriodBar.or-report-filter-card.hidden{display:none!important}
#operativoPeriodBar.or-report-filter-card>.or-report-filter-brand{
  display:flex!important;
  grid-template-columns:none!important;
  align-items:center!important;
  gap:8px!important;
  min-height:34px!important;
  margin:0!important;
  padding:6px 9px!important;
  border:0!important;
  border-radius:0!important;
  background:linear-gradient(100deg,#0b3a6e 0%,#0c579e 62%,#0d7ff4 100%)!important;
  color:#fff!important;
  box-shadow:none!important;
}
.or-report-filter-brand-icon{
  display:grid;place-items:center;
  width:24px;height:24px;flex:0 0 24px;
  border-radius:7px;background:rgba(255,255,255,.14);
}
.or-report-filter-brand-icon svg{width:14px;height:14px;stroke:#fff}
.or-report-filter-brand b{
  display:block;font-size:9px!important;line-height:1!important;
  font-weight:900!important;letter-spacing:.015em;color:#fff!important;
}
.or-report-filter-brand small{
  display:block;margin-top:3px;font-size:6.8px!important;line-height:1!important;
  color:rgba(255,255,255,.72)!important;font-weight:650!important;
}
#operativoPeriodBar.or-report-filter-card>.or-report-filter-grid{
  display:grid!important;
  grid-template-columns:repeat(6,minmax(0,1fr))!important;
  gap:5px!important;
  align-items:end!important;
  margin:0!important;
  padding:7px!important;
  border:0!important;
  border-radius:0!important;
  background:linear-gradient(180deg,#fff,#fbfdff)!important;
  box-shadow:none!important;
}
.or-fcontrol{
  position:relative!important;
  display:block!important;
  min-width:0!important;
  width:100%!important;
  margin:0!important;padding:0!important;
  background:transparent!important;border:0!important;box-shadow:none!important;
}
.or-fcontrol.hidden{display:none!important}
.or-fcontrol label{
  display:flex!important;align-items:center!important;gap:4px!important;
  min-height:12px!important;margin:0 0 3px!important;padding:0 1px!important;
  color:#58708b!important;
  font-size:7px!important;line-height:1!important;
  font-weight:900!important;letter-spacing:.045em!important;text-transform:uppercase!important;
}
.or-fcontrol-icon{
  display:inline-grid!important;place-items:center!important;
  width:12px!important;height:12px!important;flex:0 0 12px!important;
  color:#0d7ff4!important;
}
.or-fcontrol-icon svg{display:block!important;width:12px!important;height:12px!important;stroke:currentColor!important}
.or-fcontrol select,.or-fcontrol input{
  display:block!important;
  width:100%!important;min-width:0!important;
  height:34px!important;min-height:34px!important;max-height:34px!important;
  margin:0!important;padding:0 7px!important;
  border:1px solid #c9d7e5!important;
  border-radius:8px!important;
  background:#f8fbff!important;
  color:#173f70!important;
  font-size:10px!important;line-height:34px!important;
  font-weight:800!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8)!important;
}
.or-fcontrol select:focus,.or-fcontrol input:focus{
  border-color:#0d7ff4!important;
  box-shadow:0 0 0 2px rgba(13,127,244,.10)!important;
  outline:0!important;
}
.or-fcontrol select{
  appearance:auto!important;
  -webkit-appearance:menulist!important;
}
#operPeriodModeWrap,#operPeriodSelectWrap{grid-column:span 3!important}
#operStoreWrap,#operAreaWrap,#operActivityWrap{grid-column:span 2!important}
#operStartWrap,#operEndWrap{grid-column:span 3!important}
#operPeriodApply.or-filter-apply-v5{
  grid-column:span 2!important;
  display:flex!important;align-items:center!important;justify-content:center!important;gap:6px!important;
  width:100%!important;height:34px!important;min-height:34px!important;
  margin:1px 0 0!important;padding:0 12px!important;
  border:0!important;border-radius:8px!important;
  background:linear-gradient(100deg,#0b5eb8,#0d7ff4)!important;
  color:#fff!important;font-size:10px!important;font-weight:900!important;
  box-shadow:0 3px 9px rgba(13,127,244,.16)!important;
}
.or-filter-apply-icon{display:grid;place-items:center;width:14px;height:14px}
.or-filter-apply-icon svg{display:block!important;width:14px!important;height:14px!important;stroke:#fff!important}

/* ===== Global/Comercial: misma marca y densidad ===== */
#globalFilters.filters{
  position:relative!important;
  display:grid!important;
  grid-template-columns:repeat(5,minmax(0,1fr))!important;
  gap:5px!important;
  width:100%!important;
  margin:2px 0 8px!important;
  padding:9px 7px 7px!important;
  border:1px solid #cddbea!important;
  border-top:3px solid #0d7ff4!important;
  border-radius:10px!important;
  background:#fff!important;
  box-shadow:0 3px 12px rgba(13,58,104,.045)!important;
}
#globalFilters.hidden{display:none!important}
#globalFilters .filter{min-width:0!important;width:100%!important}
#globalFilters .filter label{font-size:7px!important;margin-bottom:3px!important;color:#58708b!important}
#globalFilters .filter select,#globalFilters .filter input{
  width:100%!important;height:34px!important;min-height:34px!important;
  padding:0 7px!important;border-radius:8px!important;
  border:1px solid #c9d7e5!important;background:#f8fbff!important;
  font-size:10px!important;color:#173f70!important;
}
#globalFilters>.primary,#globalFilters>.or-clear-filters{
  height:34px!important;min-height:34px!important;border-radius:8px!important;font-size:9.5px!important;
}

/* ===== Móvil ===== */
@media(max-width:900px){
  #operativoNav.op-tabs,#analysisNav{
    gap:5px!important;padding:3px 1px 5px!important;margin:0 0 5px!important;
  }
  #operativoNav.op-tabs .switch,#analysisNav .switch{
    min-height:38px!important;height:38px!important;padding:0 8px!important;font-size:8.2px!important;
  }

  #operativoPeriodBar.or-report-filter-card{margin:1px 0 7px!important;border-radius:11px!important}
  #operativoPeriodBar.or-report-filter-card>.or-report-filter-brand{
    min-height:32px!important;padding:5px 8px!important;
  }
  #operativoPeriodBar.or-report-filter-card>.or-report-filter-grid{
    grid-template-columns:repeat(6,minmax(0,1fr))!important;
    gap:5px!important;padding:6px!important;
  }
  .or-fcontrol label{font-size:6.6px!important;margin-bottom:3px!important}
  .or-fcontrol select,.or-fcontrol input{
    height:32px!important;min-height:32px!important;max-height:32px!important;
    line-height:32px!important;font-size:9.4px!important;padding:0 6px!important;
  }
  #operPeriodApply.or-filter-apply-v5{
    height:32px!important;min-height:32px!important;font-size:9.6px!important;
  }
  #globalFilters.filters{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;padding:7px!important;
  }
  #globalFilters>.primary:last-of-type{grid-column:1/-1!important}
}

@media(max-width:360px){
  #operativoPeriodBar.or-report-filter-card>.or-report-filter-grid{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
  }
  #operPeriodModeWrap,#operPeriodSelectWrap,#operStoreWrap,#operAreaWrap,#operActivityWrap,#operStartWrap,#operEndWrap{
    grid-column:span 1!important;
  }
  #operPeriodApply.or-filter-apply-v5{grid-column:span 1!important}
}
</style>'''

    @m.app.middleware("http")
    async def v194_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v194-mobile-ui-final-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V194_MOBILE_UI_FINAL = True
    print("[V194] capa visual final móvil instalada.", flush=True)
