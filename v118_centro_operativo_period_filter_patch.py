"""V118: consolida Día / Semanal / Mensual dentro de Centro Operativo.

Mantiene intactos los reportes y cálculos existentes. Solo reorganiza la
navegación: Centro Ejecutivo pasa a llamarse Centro Operativo y usa el selector
"Vista operativa" para elegir Día, Semanal o Mensual. Las tres pestañas
independientes dejan de mostrarse para evitar duplicidad.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V118_CENTRO_OPERATIVO", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''<style id="v118-centro-operativo-css">
#operativoNav [data-opview="Operación Diaria"],
#operativoNav [data-opview="Reporte Semanal"],
#operativoNav [data-opview="Reporte Mensual"]{display:none!important}
#operPeriodModeWrap.v118-oper-mode{display:block!important;min-width:170px}
</style>'''

    js = r'''<script id="v118-centro-operativo-js">
(function(){
  function renameCentro(){
    const b=document.querySelector('#operativoNav [data-opview="Centro Ejecutivo"]');
    if(b)b.textContent='Centro Operativo';
    const t=document.getElementById('operativoDynamicTitle');
    if(t&&t.textContent.trim()==='Centro Ejecutivo')t.textContent='Centro Operativo';
    const lab=document.getElementById('operPeriodModeLabel');
    if(lab)lab.textContent='Vista operativa';
    document.querySelectorAll('[data-tab-setting="operations.center"] + span').forEach(s=>{s.textContent='Centro Operativo'});
  }
  function markMode(){
    const wrap=document.getElementById('operPeriodModeWrap');
    if(wrap)wrap.classList.toggle('v118-oper-mode',typeof OP_VIEW!=='undefined'&&OP_VIEW==='Centro Ejecutivo');
  }
  renameCentro();markMode();
  const obs=new MutationObserver(()=>{renameCentro();markMode()});
  obs.observe(document.body,{subtree:true,childList:true,characterData:true});
})();
</script>'''

    @m.app.middleware("http")
    async def _v118_centro_operativo(request, call_next):
        response = await call_next(request)

        # Nombre de descarga del Centro Operativo sin tocar la clave interna
        # "Centro Ejecutivo" que todavía usa el backend validado.
        if request.url.path == "/api/export/operations" and getattr(response, "status_code", 200) < 400:
            try:
                if (request.query_params.get("report") or "") == "Centro Ejecutivo":
                    cd = response.headers.get("Content-Disposition", "")
                    if "Centro_Ejecutivo" in cd:
                        response.headers["Content-Disposition"] = cd.replace("Centro_Ejecutivo", "Centro_Operativo")
            except Exception:
                pass
            return response

        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")

            # Navegación: conservamos las claves internas para no alterar
            # fórmulas, exportaciones ni permisos.
            html=html.replace(
                'data-opview="Centro Ejecutivo" data-tab-key="operations.center">Centro Ejecutivo</button>',
                'data-opview="Centro Ejecutivo" data-tab-key="operations.center">Centro Operativo</button>'
            )

            # Centro Operativo admite los tres cortes solicitados.
            html=html.replace(
                "if(fixed==='flex') opts=[['week','Semanal'],['month','Mensual']];",
                "if(fixed==='flex') opts=[['day','Día'],['week','Semanal'],['month','Mensual']];"
            )

            # Título/subtítulo visibles del contenedor.
            html=html.replace(
                "$('#operativoDynamicTitle').textContent='Centro Ejecutivo';",
                "$('#operativoDynamicTitle').textContent='Centro Operativo';"
            )
            html=html.replace(
                "$('#operativoDynamicSub').textContent='Indicadores acumulados · operación, conversión, productividad y recorridos';",
                "$('#operativoDynamicSub').textContent='Indicadores operativos por día, semana o mes · conversión, productividad y recorridos';"
            )
            html=html.replace(
                "$('#operativoDynamicTitle').textContent=OP_VIEW;",
                "$('#operativoDynamicTitle').textContent=(OP_VIEW==='Centro Ejecutivo'?'Centro Operativo':OP_VIEW);"
            )

            if "v118-centro-operativo-js" not in html:
                html=html.replace("</head>",css+"</head>",1).replace("</body>",js+"</body>",1)

            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers={
                    "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma":"no-cache",
                    "Expires":"0",
                    "X-Operations-UI-Version":"V118",
                },
            )
        except Exception as exc:
            print(f"[V118] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V118_CENTRO_OPERATIVO=True
    print("[V118] Centro Operativo activo · Día/Semanal/Mensual consolidados como filtro.",flush=True)
