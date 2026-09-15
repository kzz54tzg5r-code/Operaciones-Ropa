"""V163 · Limpieza definitiva de navegación y filtros por módulo.

Corrige dos regresiones visuales introducidas por las capas V158/V161:
- Las barras de pestañas de Cambios y Muertos y Análisis Comercial se mostraban
  también dentro de Operación porque una regla CSS forzaba display:flex incluso
  cuando tenían la clase hidden.
- Al colapsar el menú lateral quedaba visible el contenedor blanco del perfil.

No modifica tablas, gráficas, cálculos, PDF ni Excel.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V163_MODULE_NAV_CLEANUP", False):
        return

    css = r'''<style id="v163-module-nav-cleanup-css">
/* La clase hidden vuelve a ser autoritativa aun frente a V161/V162. */
#operativoNav.hidden,
#analysisNav.hidden,
.v125-tabs.hidden{
  display:none!important;
}

/* Sólo se muestra la navegación correspondiente al módulo activo. */
body[data-v163-module="operation"] #operativoNav,
body[data-v163-module="operation"] #analysisNav{
  display:none!important;
}
body[data-v163-module="operation"] .v125-tabs:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(5,minmax(0,1fr))!important;
}

body[data-v163-module="operativo"] #analysisNav,
body[data-v163-module="operativo"] .v125-tabs{
  display:none!important;
}
body[data-v163-module="operativo"] #operativoNav:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(5,minmax(0,1fr))!important;
}

body[data-v163-module="analysis"] #operativoNav,
body[data-v163-module="analysis"] .v125-tabs{
  display:none!important;
}
body[data-v163-module="analysis"] #analysisNav:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(5,minmax(0,1fr))!important;
}

body[data-v163-module="users"] #operativoNav,
body[data-v163-module="users"] #analysisNav,
body[data-v163-module="users"] .v125-tabs,
body[data-v163-module="share"] #operativoNav,
body[data-v163-module="share"] #analysisNav,
body[data-v163-module="share"] .v125-tabs{
  display:none!important;
}

/* Evita el rectángulo blanco vacío al contraer el menú lateral. */
@media(min-width:901px){
  .shell.sidebar-collapsed .profile{
    display:none!important;
  }
}

/* En escritorio las pestañas quedan compactas, alineadas y sin filas fantasma. */
@media(min-width:901px){
  body[data-v163-module="operation"] .v125-tabs:not(.hidden),
  body[data-v163-module="operativo"] #operativoNav:not(.hidden),
  body[data-v163-module="analysis"] #analysisNav:not(.hidden){
    gap:4px!important;
    padding:4px!important;
    margin:7px 0 9px!important;
    border-radius:12px!important;
    overflow:visible!important;
  }
}
</style>'''

    js = r'''<script id="v163-module-nav-cleanup-js">
(function(){
  if(window.__V163_MODULE_NAV_CLEANUP)return;
  window.__V163_MODULE_NAV_CLEANUP=true;

  function currentModule(){
    let main='';
    try{main=String(window.MAIN||'').toLowerCase()}catch(_){ }
    if(main==='operation')return'operation';
    if(main==='operativo')return'operativo';
    if(main==='analysis'||main==='commercial')return'analysis';
    if(main==='users')return'users';
    if(main==='share')return'share';
    const active=document.querySelector('.nav.active[data-main]');
    const dm=String(active?.dataset?.main||'').toLowerCase();
    if(dm==='operation')return'operation';
    if(dm==='operativo')return'operativo';
    if(dm==='analysis')return'analysis';
    if(dm==='users')return'users';
    if(dm==='share')return'share';
    return'';
  }

  function enforce(){
    const mod=currentModule();
    if(mod)document.body.dataset.v163Module=mod;
    else delete document.body.dataset.v163Module;
  }

  async function openOperationClean(){
    enforce();
    if(currentModule()!=='operation')return;
    try{
      window.OP_VIEW='Operación';
      window.V149_OPERATION_TAB='summary';
      window.V125_OPERATION_TAB='summary';
      if(typeof window.renderOperativoView==='function'){
        await window.renderOperativoView('Operación',true);
      }
    }catch(err){
      console.warn('[V163] No fue posible restablecer Resumen de Operación',err);
    }
    enforce();
  }

  function schedule(){[0,80,220,600].forEach(ms=>setTimeout(enforce,ms))}

  document.addEventListener('click',e=>{
    const main=e.target.closest?.('[data-main]');
    if(main){
      const target=String(main.dataset.main||'').toLowerCase();
      schedule();
      if(target==='operation')setTimeout(openOperationClean,120);
    }
    if(e.target.closest?.('#operativoNav,#analysisNav,.v125-tabs,#v161FilterBar'))schedule();
  },true);
  document.addEventListener('change',e=>{
    if(e.target?.matches?.('select,input'))schedule();
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{schedule();setTimeout(()=>{if(currentModule()==='operation')openOperationClean()},350)});
  else{schedule();setTimeout(()=>{if(currentModule()==='operation')openOperationClean()},350)}

  console.info('[V163] Navegación exclusiva por módulo y menú colapsado limpio.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v163_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body=b''
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode('utf-8',errors='replace')
            if 'v163-module-nav-cleanup-css' not in html:
                html=html.replace('</head>',css+'</head>',1)
            if 'v163-module-nav-cleanup-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            headers=dict(getattr(response,'headers',{}) or {})
            headers.pop('content-length',None)
            headers.update({'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V163'})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f'[V163] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V163_MODULE_NAV_CLEANUP=True
    print('[V163] Navegación por módulo corregida; perfil colapsado sin bloque blanco.',flush=True)
