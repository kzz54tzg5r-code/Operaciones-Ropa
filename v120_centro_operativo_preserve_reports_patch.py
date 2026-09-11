"""V120: Centro Operativo conserva la estructura validada de Día/Semanal/Mensual.

La navegación permanece consolidada en un solo botón "Centro Operativo" y el
usuario elige el corte desde "Vista operativa". Para Día, Semanal y Mensual se
reutiliza exactamente el render validado de cada reporte (incluidos V117 y sus
PDF), de modo que el filtro sustituye a las pestañas sin cambiar estructura,
tarjetas, tablas, gráficas ni cálculos.

Anual no existía como reporte independiente previo, por lo que conserva la
vista integral anual introducida por V119 hasta que se defina su estructura
propia.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V120_CENTRO_PRESERVE_REPORTS", False):
        return

    from fastapi.responses import HTMLResponse

    js = r'''<script id="v120-centro-preserve-reports-js">
(function(){
  const CENTER='Centro Ejecutivo';
  const MAP={day:'Operación Diaria',week:'Reporte Semanal',month:'Reporte Mensual'};
  const LABEL={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
  const previousRender=window.renderOperativoView;
  if(typeof previousRender!=='function')return;

  window.renderOperativoView=async function(name,force=false){
    if(name!==CENTER)return previousRender(name,force);

    const modeEl=$('#operPeriodMode');
    const mode=(modeEl?.value||OPER_PERIOD?.type||'week');
    const value=OPER_PERIOD?.value||$('#operPeriodSelect')?.value||'';
    const mapped=MAP[mode];

    // Anual es nuevo: V119 mantiene su vista integral anual y su endpoint de
    // rango 01-ene/31-dic. Día/Semana/Mes reutilizan sus reportes originales.
    if(!mapped){
      const out=await previousRender(CENTER,force);
      const title=$('#operativoDynamicTitle'),sub=$('#operativoDynamicSub');
      if(title)title.textContent='Centro Operativo · Anual';
      if(sub)sub.textContent='Acumulado anual · operación, conversión, recuperación, productividad y recorridos';
      return out;
    }

    const savedType=mode,savedValue=value;
    OPER_PERIOD.type=savedType;OPER_PERIOD.value=savedValue;

    // Esta llamada atraviesa los renderizadores V115/V117 ya validados:
    // conserva tarjetas, detalle operativo, gráficas, colores y descarga PDF.
    const out=await previousRender(mapped,force);

    // Volver a presentar el selector único de Centro Operativo sin modificar
    // el contenido recién renderizado del reporte elegido.
    OPER_PERIOD.type=savedType;OPER_PERIOD.value=savedValue;
    try{setPeriodSelector(CENTER,OPSDATA||{});}catch(_){ }
    const msel=$('#operPeriodMode');if(msel)msel.value=savedType;
    const psel=$('#operPeriodSelect');if(psel&&savedValue&&Array.from(psel.options).some(o=>o.value===savedValue)){psel.value=savedValue;OPER_PERIOD.value=savedValue;}

    const title=$('#operativoDynamicTitle'),sub=$('#operativoDynamicSub');
    if(title)title.textContent=`Centro Operativo · ${LABEL[savedType]||''}`;
    if(sub){
      const texts={
        day:'Consulta por fecha · ingresos, pendientes y avance por tienda',
        week:'Semana ISO · operación, conversión, recuperación, productividad y recorridos',
        month:'Mes seleccionado · operación y desempeño consolidado'
      };
      sub.textContent=texts[savedType]||'';
    }
    return out;
  };

  // Al cambiar Vista operativa, renderizar de inmediato la estructura correcta
  // sin navegar a otra pestaña.
  const mode=$('#operPeriodMode');
  if(mode){
    mode.onchange=async()=>{
      const t=mode.value||'week';
      OPER_PERIOD.type=t;OPER_PERIOD.value='';
      setPeriodSelector(CENTER,OPSDATA||{available_dates:[],available_weeks:[],available_months:[]});
      await window.renderOperativoView(CENTER,true);
    };
  }
  console.info('[V120] Centro Operativo conserva estructura Día/Semanal/Mensual según filtro.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v120_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'v120-centro-preserve-reports-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V120'
            })
        except Exception as exc:
            print(f'[V120] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V120_CENTRO_PRESERVE_REPORTS=True
    print('[V120] Centro Operativo: filtro único reutiliza estructura validada Día/Semanal/Mensual.',flush=True)
