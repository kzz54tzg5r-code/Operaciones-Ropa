"""V285 · Densidad global de tablas.
Regla transversal: fuentes legibles, filas compactas y columnas sin espacio horizontal
innecesario. No agrega observers ni lógica de navegación.
"""

def install(m):
    if getattr(m,"_V285_GLOBAL_TABLE_DENSITY",False):
        return
    from fastapi.responses import HTMLResponse

    css=r'''<style id="v285-global-table-density-css">
/* Regla global de tablas: más lectura y menos aire horizontal. */
:root{
  --v285-th-font:9px;
  --v285-td-font:10px;
  --v285-cell-x:4px;
  --v285-cell-y:3px;
  --v285-row-line:1.08;
}

/* Todas las tablas de reportes y administración usan contenido como guía de ancho. */
body table{
  table-layout:auto!important;
  border-collapse:collapse!important;
  border-spacing:0!important;
  width:100%;
}
body table th,
body table td{
  padding:var(--v285-cell-y) var(--v285-cell-x)!important;
  line-height:var(--v285-row-line)!important;
  vertical-align:middle!important;
  box-sizing:border-box!important;
}
body table th{
  font-size:var(--v285-th-font)!important;
  font-weight:850!important;
  letter-spacing:0!important;
  white-space:nowrap;
}
body table td{
  font-size:var(--v285-td-font)!important;
  letter-spacing:0!important;
}
/* Los números y controles no necesitan aire lateral extra. */
body table td.num,
body table td.number,
body table td.numeric,
body table td.right,
body table td.center,
body table td[align="right"],
body table td[align="center"]{
  white-space:nowrap;
}
body table input,
body table select,
body table button{
  font-size:inherit!important;
}
/* Evita espacios amplios en encabezados/celdas de extremos. */
body table th:first-child,
body table td:first-child{padding-left:5px!important}
body table th:last-child,
body table td:last-child{padding-right:5px!important}

/* Resurtido: columnas numéricas realmente compactas; % absorbe el espacio útil. */
.v281 .v281-table{table-layout:auto!important}
.v281 .v281-table th:nth-child(1),
.v281 .v281-table td:nth-child(1){width:1%!important;min-width:54px!important;white-space:nowrap!important}
.v281 .v281-table th:nth-child(2),
.v281 .v281-table td:nth-child(2){width:1%!important;min-width:74px!important;white-space:nowrap!important}
.v281 .v281-table th:nth-child(3),
.v281 .v281-table td:nth-child(3){width:1%!important;min-width:66px!important;white-space:nowrap!important}
.v281 .v281-table th:nth-child(4),
.v281 .v281-table td:nth-child(4){width:1%!important;min-width:58px!important;white-space:nowrap!important}
.v281 .v281-table th:nth-child(5),
.v281 .v281-table td:nth-child(5){width:auto!important;min-width:170px!important}
.v281 .v281-table th:nth-child(6),
.v281 .v281-table td:nth-child(6){width:1%!important;min-width:72px!important;white-space:nowrap!important}
.v281 .v281-table th:nth-child(7),
.v281 .v281-table td:nth-child(7){width:1%!important;min-width:76px!important;white-space:nowrap!important}
.v281 .v281-table th,
.v281 .v281-table td{padding-left:4px!important;padding-right:4px!important}
.v281 .v281-table th{font-size:8.5px!important}
.v281 .v281-table td{font-size:9.5px!important}
.v281 .v281-table .v281-pct{grid-template-columns:minmax(80px,1fr) 34px!important;gap:4px!important}
.v281 .v281-table .v281-track{height:7px!important}
.v281 .v281-table .v281-prio{font-size:7px!important}
.v281 .v281-block{margin-top:4px!important;margin-bottom:4px!important}
.v281 .v281-bhead{min-height:32px!important}

/* Tablas anchas: compactar sin forzar columnas artificialmente iguales. */
.v279-table,
.v267-table,
.v268-table,
.v243-table,
.dataframe,
.table,
.report-table,
.compact-table{
  table-layout:auto!important;
}
.v279-table th,.v279-table td,
.v267-table th,.v267-table td,
.v268-table th,.v268-table td,
.v243-table th,.v243-table td,
.dataframe th,.dataframe td,
.table th,.table td,
.report-table th,.report-table td,
.compact-table th,.compact-table td{
  padding-left:4px!important;
  padding-right:4px!important;
}

/* Escritorio: legibilidad sin aumentar la altura. */
@media (min-width:1201px){
  body table th{font-size:9px!important}
  body table td{font-size:10px!important}
  body table th,body table td{padding-top:3px!important;padding-bottom:3px!important}
}

/* Tablet/iPad: conservar matriz de laptop pero compacta. */
@media (min-width:701px) and (max-width:1200px){
  :root{--v285-th-font:7.8px;--v285-td-font:8.6px;--v285-cell-x:3px;--v285-cell-y:2.5px}
  body table th,body table td{line-height:1.05!important}
  .v281 .v281-table th{font-size:7.3px!important}
  .v281 .v281-table td{font-size:8px!important}
}

/* Móvil: más compacto, sin volver ilegibles los números. */
@media (max-width:700px){
  :root{--v285-th-font:6.2px;--v285-td-font:7px;--v285-cell-x:2px;--v285-cell-y:2px}
  body table th,body table td{line-height:1.02!important}
  body table th:first-child,body table td:first-child{padding-left:3px!important}
  body table th:last-child,body table td:last-child{padding-right:3px!important}
  .v281 .v281-table th{font-size:5.8px!important}
  .v281 .v281-table td{font-size:6.5px!important}
  .v281 .v281-table th:nth-child(1),.v281 .v281-table td:nth-child(1){min-width:30px!important}
  .v281 .v281-table th:nth-child(2),.v281 .v281-table td:nth-child(2){min-width:46px!important}
  .v281 .v281-table th:nth-child(3),.v281 .v281-table td:nth-child(3){min-width:40px!important}
  .v281 .v281-table th:nth-child(4),.v281 .v281-table td:nth-child(4){min-width:36px!important}
  .v281 .v281-table th:nth-child(5),.v281 .v281-table td:nth-child(5){min-width:86px!important}
  .v281 .v281-table th:nth-child(6),.v281 .v281-table td:nth-child(6){min-width:46px!important}
  .v281 .v281-table th:nth-child(7),.v281 .v281-table td:nth-child(7){min-width:48px!important}
}
</style>'''

    @m.app.middleware("http")
    async def v285_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v285-global-table-density-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers["Cache-Control"]="no-store"
            headers["X-Table-Density"]="V285"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V285] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V285_GLOBAL_TABLE_DENSITY=True
    print("[V285] densidad global de tablas instalada.",flush=True)
