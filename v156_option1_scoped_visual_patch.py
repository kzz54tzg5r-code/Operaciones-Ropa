"""V156 · Opción 1 visual por módulo, sin alterar reportes.

Corrige V155: elimina la contaminación visual entre módulos y deja el
rediseño sólo como capa de presentación sobre las pantallas reales.

Reglas:
- No reemplaza tablas ni gráficas.
- No modifica cálculos, APIs, PDF ni Excel.
- No monta demos/Shadow DOM de Análisis Comercial.
- Cada módulo conserva únicamente su contenido real.
- Sólo cambia shell, navegación, encabezados, filtros, pestañas y tarjetas.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V156_SCOPED_OPTION1", False):
        return

    css = r'''<style id="v156-scoped-option1-css">
body.v156-option1{
  --v156-navy:#0b3f7d;--v156-blue:#1675f5;--v156-soft:#f3f7fc;
  --v156-line:#d8e5f3;--v156-ink:#103d78;
  background:var(--v156-soft)!important;
}
body.v156-option1 .shell{grid-template-columns:230px minmax(0,1fr)!important;background:var(--v156-soft)!important}
body.v156-option1 .side{
  background:linear-gradient(180deg,#0a3c76 0%,#0d4d91 60%,#0a386e 100%)!important;
  border-right:0!important;padding:16px 12px!important;box-shadow:8px 0 28px rgba(15,54,101,.08)!important;
}
body.v156-option1 .sidebrand{padding:6px 8px 18px!important;border-bottom:1px solid rgba(255,255,255,.14)!important;margin-bottom:6px!important}
body.v156-option1 .sidebrand b,body.v156-option1 .sidebrand small,body.v156-option1 .profile b,body.v156-option1 .profile small{color:#fff!important}
body.v156-option1 .group{color:rgba(255,255,255,.55)!important}
body.v156-option1 .nav{color:rgba(255,255,255,.9)!important;border-radius:11px!important;padding:11px 12px!important;margin:1px 0!important;background:transparent!important}
body.v156-option1 .nav:hover{background:rgba(255,255,255,.08)!important}
body.v156-option1 .nav.active{background:var(--v156-blue)!important;color:#fff!important;box-shadow:0 7px 16px rgba(0,38,100,.22)!important}
body.v156-option1 .nav small{color:inherit!important;opacity:.72!important}
body.v156-option1 .profile{border-top:1px solid rgba(255,255,255,.16)!important}
body.v156-option1 .logout,body.v156-option1 .sidebar-toggle{background:rgba(255,255,255,.1)!important;border-color:rgba(255,255,255,.24)!important;color:#fff!important}
body.v156-option1 .main{padding:16px 20px 86px!important;background:var(--v156-soft)!important}
body.v156-option1 .hero{
  position:relative!important;overflow:hidden!important;
  background:linear-gradient(118deg,#0b3e7c 0%,#0c559f 70%,#0b407d 100%)!important;
  border-radius:18px!important;padding:20px 24px!important;border:1px solid rgba(255,255,255,.12)!important;box-shadow:none!important;
}
body.v156-option1 .hero:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 80% 35%,rgba(255,255,255,.11),transparent 28%),linear-gradient(130deg,transparent 56%,rgba(255,255,255,.05) 56%,rgba(255,255,255,.05) 67%,transparent 67%);pointer-events:none}
body.v156-option1 .hero h1{font-size:27px!important;letter-spacing:-.02em!important;position:relative!important}
body.v156-option1 .hero p{font-size:10px!important;color:#d7e8fb!important;position:relative!important}
body.v156-option1 .hero:after{content:"DEMO VISUAL · OPCIÓN 1";position:absolute;right:22px;top:14px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.2);color:#fff;padding:5px 10px;font-size:8px;font-weight:900;letter-spacing:.04em;pointer-events:none}

/* Filtros: misma lógica y mismos campos; sólo presentación. */
body.v156-option1 .filters,
body.v156-option1 #globalFilters,
body.v156-option1 #v103FilterShell{
  background:#fff!important;border:1px solid var(--v156-line)!important;border-radius:16px!important;
  padding:12px 14px!important;margin:11px 0!important;gap:10px!important;box-shadow:0 4px 14px rgba(30,79,135,.045)!important;
}
body.v156-option1 .filter{min-width:145px;flex:1 1 145px}
body.v156-option1 .filter label{color:#466887!important;font-size:8px!important;letter-spacing:.03em!important;margin-bottom:5px!important}
body.v156-option1 .filter select,body.v156-option1 .filter input,
body.v156-option1 #globalFilters select,body.v156-option1 #globalFilters input,
body.v156-option1 #v103FilterShell select,body.v156-option1 #v103FilterShell input{
  min-height:40px!important;border:1px solid #cfdeee!important;border-radius:10px!important;background:#fff!important;color:#143d70!important;
}
body.v156-option1 .primary{border-radius:10px!important;min-height:40px!important;background:var(--v156-blue)!important}

/* Pestañas de cada reporte: sin cambiar orden, contenido ni comportamiento. */
body.v156-option1 .switches,
body.v156-option1 #operativoNav,
body.v156-option1 #analysisNav,
body.v156-option1 .v125-tabs{
  background:#fff!important;border:1px solid var(--v156-line)!important;border-radius:14px!important;padding:5px!important;gap:5px!important;margin:10px 0!important;
}
body.v156-option1 .switch,body.v156-option1 .v125-tab{border-radius:10px!important}
body.v156-option1 .switch.active,body.v156-option1 .v125-tab.active{background:var(--v156-blue)!important;color:#fff!important;box-shadow:0 4px 10px rgba(22,117,245,.18)!important}

/* Sólo tarjetas/contenedores. Tablas, canvas, svg y exportaciones NO se estilizan aquí. */
body.v156-option1 .kpis,body.v156-option1 .report-kpis{gap:10px!important}
body.v156-option1 .kpi,body.v156-option1 .report-kpi,body.v156-option1 .card,body.v156-option1 .useritem{
  background:#fff!important;border:1px solid var(--v156-line)!important;border-radius:15px!important;box-shadow:0 3px 12px rgba(29,76,126,.04)!important;
}
body.v156-option1 .panel,body.v156-option1 .chart-box,body.v156-option1 .drop{
  background:#fff!important;border-color:var(--v156-line)!important;border-radius:15px!important;box-shadow:0 3px 12px rgba(29,76,126,.035)!important;
}
body.v156-option1 .val,body.v156-option1 .report-kpi .rk-value{color:var(--v156-ink)!important}
body.v156-option1 .title{color:var(--v156-ink)!important;font-size:17px!important}

/* Blindaje contra demos comerciales heredados. El comercial real vive sólo en su módulo. */
#v139CommercialHost,#v141CommercialHost,#v133CommercialDemoHost{display:none!important}
body.v156-option1 main.main>section.page.active{display:block!important}

/* Menú colapsado mantiene la estética. */
body.v156-option1 .shell.sidebar-collapsed{grid-template-columns:76px minmax(0,1fr)!important}

@media(max-width:900px){
  body.v156-option1 .main{padding:8px 8px 76px!important}
  body.v156-option1 .hero{border-radius:14px!important;padding:15px 14px!important}
  body.v156-option1 .hero h1{font-size:21px!important;padding-right:72px!important}
  body.v156-option1 .hero:after{right:10px;top:10px;font-size:6.5px;padding:4px 7px}
  body.v156-option1 .filters,body.v156-option1 #globalFilters,body.v156-option1 #v103FilterShell{padding:9px!important;gap:7px!important;border-radius:13px!important}
  body.v156-option1 .switches,body.v156-option1 #operativoNav,body.v156-option1 #analysisNav,body.v156-option1 .v125-tabs{overflow-x:auto!important;flex-wrap:nowrap!important}
}
</style>'''

    js = r'''<script id="v156-scoped-option1-js">
(function(){
  if(window.__V156_SCOPED_OPTION1)return;window.__V156_SCOPED_OPTION1=true;
  document.body.classList.remove('v155-option1','v141-commercial-exact','v139-commercial-direct');
  document.body.classList.add('v156-option1');

  function detectModule(){
    var a=document.querySelector('.nav.active');
    var t=((a&&a.textContent)||'').toLowerCase();
    var m='';
    try{m=String(window.MAIN||'').toLowerCase()}catch(_){m=''}
    if(t.includes('análisis comercial')||m==='analysis'||m==='commercial')return'analysis';
    if(t.includes('cambios y muertos')||m==='operativo')return'cambios';
    if(t.trim().startsWith('operación')||m==='operation')return'operation';
    if(t.includes('usuarios')||m==='users')return'users';
    if(t.includes('compartir')||m==='share')return'share';
    return m||'cambios';
  }
  function sync(){
    document.body.classList.remove('v155-option1','v141-commercial-exact','v139-commercial-direct');
    document.body.classList.add('v156-option1');
    document.body.setAttribute('data-v156-module',detectModule());
    ['v139CommercialHost','v141CommercialHost','v133CommercialDemoHost'].forEach(function(id){var x=document.getElementById(id);if(x)x.style.setProperty('display','none','important')});
  }
  document.addEventListener('click',function(e){if(e.target&&e.target.closest&&e.target.closest('.nav'))setTimeout(sync,80)},false);
  new MutationObserver(sync).observe(document.documentElement,{subtree:true,attributes:true,attributeFilter:['class']});
  sync();setInterval(sync,700);
  console.info('[V156] Opción 1 por módulo activa; contenido real preservado.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v156_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body=b''
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode('utf-8',errors='replace')
            if 'v156-scoped-option1-css' not in html:
                html=html.replace('</head>',css+'</head>',1)
            if 'v156-scoped-option1-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            headers=dict(getattr(response,'headers',{}) or {})
            headers.pop('content-length',None)
            headers.update({'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V156-SCOPED-OPTION1-REAL-REPORTS'})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f'[V156] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V156_SCOPED_OPTION1=True
    print('[V156] Diseño Opción 1 por módulo instalado; sin demos cruzados, tablas/gráficas/PDF/Excel intactos.',flush=True)
