"""V155 · Demo visual Opción 1 para Operaciones Ropa.

Objetivo: aplicar únicamente el rediseño visual aprobado en los bocetos, sin
modificar datos, tablas, gráficas, endpoints ni descargas PDF/Excel.

Reglas estrictas:
- NO reemplaza ni elimina tablas existentes.
- NO reemplaza ni elimina gráficas/canvas/SVG existentes.
- NO modifica endpoints ni cálculos.
- NO modifica botones/URLs de descarga PDF o Excel.
- Sólo cambia shell, navegación, cabeceras, filtros, pestañas, tarjetas y
  superficies visuales mediante CSS.
- Análisis Comercial puede vivir en Shadow DOM; se inyecta sólo una hoja de
  estilo visual y se excluyen table/canvas/svg de cualquier regla.
- El archivo queda aislado para poder retirarlo con un solo cambio si el usuario
  pide regresar a la versión anterior.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V155_VISUAL_OPTION1", False):
        return

    css = r'''<style id="v155-option1-css">
/* V155: sólo apariencia. Tablas, gráficas y exportaciones quedan intactas. */
body.v155-option1{
  --v155-navy:#0b3f7d;--v155-navy2:#0d4d93;--v155-blue:#1675f5;
  --v155-soft:#eef5fd;--v155-line:#d8e5f3;--v155-ink:#0f376b;
  background:#f3f7fc!important;
}
body.v155-option1 .shell{grid-template-columns:230px minmax(0,1fr);background:#f3f7fc}
body.v155-option1 .side{
  background:linear-gradient(180deg,#0b3d78 0%,#0d4c8d 62%,#0b386d 100%)!important;
  border-right:0!important;padding:16px 12px!important;box-shadow:8px 0 28px rgba(16,58,110,.08);
}
body.v155-option1 .sidebrand{padding:5px 8px 18px!important;border-bottom:1px solid rgba(255,255,255,.14);margin-bottom:7px}
body.v155-option1 .sidebrand b,body.v155-option1 .sidebrand small{color:#fff!important}
body.v155-option1 .sidebrand small{opacity:.7}
body.v155-option1 .group{color:rgba(255,255,255,.52)!important;padding-top:15px!important}
body.v155-option1 .nav{color:rgba(255,255,255,.88)!important;border:1px solid transparent!important;border-radius:11px!important;padding:11px 12px!important;margin:1px 0}
body.v155-option1 .nav:hover{background:rgba(255,255,255,.09)!important}
body.v155-option1 .nav.active{background:#1675f5!important;color:#fff!important;box-shadow:0 8px 18px rgba(0,39,103,.22)}
body.v155-option1 .nav small{color:inherit!important;opacity:.7!important}
body.v155-option1 .profile{border-top:1px solid rgba(255,255,255,.16)!important;color:#fff!important}
body.v155-option1 .profile b,body.v155-option1 .profile small{color:#fff!important}
body.v155-option1 .profile small{opacity:.68}
body.v155-option1 .logout,body.v155-option1 .sidebar-toggle{background:rgba(255,255,255,.1)!important;border-color:rgba(255,255,255,.24)!important;color:#fff!important}

body.v155-option1 .main{padding:16px 20px 86px!important;background:#f3f7fc!important}
body.v155-option1 .hero{
  position:relative!important;overflow:hidden!important;
  background:linear-gradient(120deg,#0b3e7d 0%,#0c559f 68%,#0a3d78 100%)!important;
  border-radius:18px!important;padding:21px 24px!important;box-shadow:none!important;border:1px solid rgba(255,255,255,.12)!important;
}
body.v155-option1 .hero:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 80% 40%,rgba(255,255,255,.12),transparent 28%),linear-gradient(130deg,transparent 55%,rgba(255,255,255,.055) 55%,rgba(255,255,255,.055) 65%,transparent 65%);pointer-events:none}
body.v155-option1 .hero:after{content:"DEMO VISUAL · OPCIÓN 1";position:absolute;right:22px;top:14px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:999px;padding:5px 10px;font-size:8px;font-weight:900;letter-spacing:.05em;pointer-events:none}
body.v155-option1 .hero h1{font-size:27px!important;letter-spacing:-.02em;position:relative}
body.v155-option1 .hero p{font-size:10px!important;color:#d5e7fb!important;position:relative}
body.v155-option1 .hero .badge{margin-top:18px!important;position:relative}

/* Filtros: mismo contenido/función, nueva presentación */
body.v155-option1 .filters{
  background:#fff!important;border:1px solid var(--v155-line)!important;border-radius:16px!important;
  padding:12px 14px!important;margin:11px 0!important;gap:10px!important;box-shadow:0 4px 14px rgba(30,79,135,.045)!important;
}
body.v155-option1 .filter{min-width:145px;flex:1 1 145px}
body.v155-option1 .filter label{color:#456789!important;font-size:8px!important;letter-spacing:.03em!important;margin-bottom:5px!important}
body.v155-option1 .filter select,body.v155-option1 .filter input{
  min-height:40px!important;border:1px solid #cfdeee!important;border-radius:10px!important;background:#fff!important;
  color:#143d70!important;font-size:10px!important;padding-top:8px!important;padding-bottom:8px!important;
}
body.v155-option1 .filter select:focus,body.v155-option1 .filter input:focus{outline:2px solid rgba(22,117,245,.18)!important;border-color:#6faaf4!important}

/* Pestañas existentes, sin cambiar contenido */
body.v155-option1 .switches{background:#fff!important;border:1px solid var(--v155-line)!important;border-radius:14px!important;padding:5px!important;gap:5px!important;margin:10px 0!important}
body.v155-option1 .switch{border:0!important;border-radius:10px!important;padding:9px 13px!important;color:#32577f!important;background:transparent!important;font-size:8px!important}
body.v155-option1 .switch.active{background:#1675f5!important;color:#fff!important;box-shadow:0 4px 10px rgba(22,117,245,.18)!important}

/* Tarjetas y superficies; no toca table/canvas/svg */
body.v155-option1 .kpis,body.v155-option1 .report-kpis{gap:10px!important}
body.v155-option1 .kpi,body.v155-option1 .report-kpi,body.v155-option1 .card{
  border:1px solid var(--v155-line)!important;border-radius:15px!important;background:#fff!important;
  box-shadow:0 3px 12px rgba(29,76,126,.04)!important;
}
body.v155-option1 .kpi{min-height:102px!important;padding:13px 13px!important}
body.v155-option1 .val,body.v155-option1 .report-kpi .rk-value{color:#103d78!important;letter-spacing:-.02em}
body.v155-option1 .lab,body.v155-option1 .report-kpi .rk-label{color:#607892!important}
body.v155-option1 .panel,body.v155-option1 .chart-box{
  background:#fff!important;border:1px solid var(--v155-line)!important;border-radius:15px!important;
  box-shadow:0 3px 12px rgba(29,76,126,.035)!important;
}
body.v155-option1 .title{color:#103d78!important;font-size:17px!important;letter-spacing:-.01em}
body.v155-option1 .subtitle{color:#6d8299!important}

/* Conservación explícita: no se altera geometría ni estilos internos de reportes. */
body.v155-option1 table,body.v155-option1 .table,body.v155-option1 .tablewrap,
body.v155-option1 canvas,body.v155-option1 svg{ }
/* Los controles de exportación conservan sus estilos y comportamiento existentes. */
body.v155-option1 a[download],body.v155-option1 [data-export],body.v155-option1 [id*="download" i],body.v155-option1 [id*="export" i]{ }

/* Usuarios y compartir: sólo contenedores/inputs, nunca tablas. */
body.v155-option1 .usergrid{gap:10px!important}
body.v155-option1 .useritem{border:1px solid var(--v155-line)!important;border-radius:14px!important;background:#fff!important;box-shadow:0 3px 12px rgba(29,76,126,.035)!important}
body.v155-option1 .drop{border-radius:14px!important;border-color:#cbdced!important;background:#fff!important}

/* Estado cerrado del menú mantiene la estética. */
body.v155-option1 .shell.sidebar-collapsed{grid-template-columns:76px minmax(0,1fr)!important}
body.v155-option1 .shell.sidebar-collapsed .sidebrand{border-bottom:0!important}

@media(max-width:900px){
  body.v155-option1 .main{padding:8px 8px 76px!important}
  body.v155-option1 .hero{border-radius:14px!important;padding:15px 14px!important}
  body.v155-option1 .hero h1{font-size:21px!important;padding-right:72px}
  body.v155-option1 .hero:after{right:10px;top:10px;font-size:6.5px;padding:4px 7px}
  body.v155-option1 .filters{padding:9px!important;gap:7px!important;border-radius:13px!important}
  body.v155-option1 .filter{min-width:125px;flex:1 1 125px}
  body.v155-option1 .switches{overflow-x:auto!important;flex-wrap:nowrap!important}
  body.v155-option1 .switch{white-space:nowrap!important;min-height:38px}
  body.v155-option1 .kpi{min-height:90px!important}
}
</style>'''

    js = r'''<script id="v155-option1-js">
(function(){
  if(window.__V155_OPTION1_INIT)return;window.__V155_OPTION1_INIT=true;
  document.body.classList.add('v155-option1');

  // Análisis Comercial usa Shadow DOM. Sólo añadimos piel visual; no tocamos
  // tablas, gráficas, datos ni eventos del reporte.
  var shadowCss=`
    :host{--v155:#1675f5;--v155navy:#0b3f7d;--v155line:#d8e5f3;}
    #v139-demo-root{background:#f3f7fc!important;color:#123d70!important;}
    #v139-demo-root .top,#v139-demo-root .hero,#v139-demo-root header{border-radius:16px!important;}
    #v139-demo-root .tabs,#v139-demo-root .tabbar{background:#fff!important;border:1px solid var(--v155line)!important;border-radius:13px!important;padding:4px!important;}
    #v139-demo-root .tab{border-radius:9px!important;}
    #v139-demo-root .tab.active{background:var(--v155)!important;color:#fff!important;}
    #v139-demo-root .filters,#v139-demo-root .filterbar,#v139-demo-root .filters-inline{background:#fff!important;border:1px solid var(--v155line)!important;border-radius:14px!important;}
    #v139-demo-root select,#v139-demo-root input{border-radius:9px!important;border-color:#cfdeee!important;}
    #v139-demo-root .kpi,#v139-demo-root .card,#v139-demo-root .panel{border-radius:14px!important;border-color:var(--v155line)!important;box-shadow:0 3px 12px rgba(29,76,126,.035)!important;}
    /* INTENCIONALMENTE SIN REGLAS PARA table/canvas/svg/export */
  `;
  function skinShadow(root){
    if(!root||root.getElementById('v155-shadow-skin'))return;
    var s=document.createElement('style');s.id='v155-shadow-skin';s.textContent=shadowCss;root.appendChild(s);
  }
  function scan(){
    document.querySelectorAll('*').forEach(function(el){if(el.shadowRoot)skinShadow(el.shadowRoot);});
  }
  scan();
  var mo=new MutationObserver(function(){scan();});
  mo.observe(document.documentElement,{childList:true,subtree:true});

  console.info('[V155] Opción 1 visual activa. Tablas, gráficas y descargas preservadas.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v155_visual_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v155-option1-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v155-option1-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V155-OPTION1-VISUAL-PRESERVE-REPORTS",
            })
            # Content-Length anterior deja de ser válido al inyectar CSS/JS.
            headers.pop("content-length", None)
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V155] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V155_VISUAL_OPTION1 = True
    print("[V155] Demo visual Opción 1 instalado; tablas/gráficas/PDF/Excel sin modificación.", flush=True)
