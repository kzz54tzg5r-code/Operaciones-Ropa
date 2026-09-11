"""V124 · Operación como módulo principal independiente.

- Saca Operación de las pestañas internas de Cambios y Muertos.
- La agrega al menú principal, entre Cambios y Muertos y Análisis Comercial.
- Conserva el reporte/captura V121 reutilizando la vista operativa existente.
- Mantiene el acceso directo del perfil Colaborador.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V124_OPERATION_MAIN_MODULE", False):
        return

    from fastapi.responses import HTMLResponse

    # Ya no es una pestaña administrable dentro de Cambios y Muertos.
    try:
        m.REPORT_TABS.pop("operations.operation", None)
    except Exception:
        pass

    css = r'''<style id="v124-operation-main-css">
/* Operación ahora vive en el menú principal, no dentro del switch de C&M. */
#operativoNav [data-opview="Operación"]{display:none!important}
.shell.sidebar-collapsed .nav[data-main="operation"]:before{content:"▣";font-size:18px;display:block}
@media(max-width:900px){#mobileMainNav{grid-template-columns:repeat(5,1fr)}}
</style>'''

    js = r'''<script id="v124-operation-main-js">
(function(){
  const OP='Operación';
  const subtitle='Control diario, productividad por colaborador y eficiencia de mercancía';

  function ensureMainEntries(){
    const cm=document.querySelector('.side .nav[data-main="operativo"]');
    if(cm && !document.querySelector('.side .nav[data-main="operation"]')){
      cm.insertAdjacentHTML('afterend','<button class="nav" data-main="operation">Operación<small>Control diario y productividad</small></button>');
    }
    const mcm=document.querySelector('#mobileMainNav .mnav[data-main="operativo"]');
    if(mcm && !document.querySelector('#mobileMainNav .mnav[data-main="operation"]')){
      mcm.insertAdjacentHTML('afterend','<button class="mnav" data-main="operation"><span class="mnav-icon">▣</span><span>Operación</span></button>');
    }
    bindOperationEntries();
    syncMobileColumns();
  }

  function syncMobileColumns(){
    const nav=document.querySelector('#mobileMainNav');
    if(!nav) return;
    if(USER?.role==='colaborador') nav.style.gridTemplateColumns='1fr';
    else if(['superadmin','admin'].includes(USER?.role)) nav.style.gridTemplateColumns='repeat(5,1fr)';
    else nav.style.gridTemplateColumns='repeat(3,1fr)';
  }

  function markMainActive(name){
    document.querySelectorAll('[data-main]').forEach(x=>x.classList.toggle('active',x.dataset.main===name));
  }

  async function openOperationMain(){
    try{
      MAIN='operation';
      markMainActive('operation');
      document.querySelector('#analysisNav')?.classList.add('hidden');
      document.querySelector('#operativoNav')?.classList.add('hidden');
      document.querySelector('#globalFilters')?.classList.add('hidden');
      if(typeof showPage==='function') showPage('operativo');
      const heroTitle=document.querySelector('#heroTitle');
      const heroSub=document.querySelector('#heroSub');
      if(heroTitle) heroTitle.textContent='Operación';
      if(heroSub) heroSub.textContent=subtitle;
      OP_VIEW=OP;
      OPER_PERIOD={type:'day',value:''};
      if(typeof window.renderOperativoView==='function') await window.renderOperativoView(OP,true);
      else if(typeof renderOperativoView==='function') await renderOperativoView(OP,true);
      if(heroTitle) heroTitle.textContent='Operación';
      if(heroSub) heroSub.textContent=subtitle;
    }catch(err){
      console.error('[V124] Error abriendo Operación',err);
      const box=document.querySelector('#operativoDynamicContent');
      const detail=(err && (err.message||err.detail)) || String(err||'Error desconocido');
      if(box) box.innerHTML=`<div class="infoempty">No fue posible abrir Operación: ${String(detail)}</div>`;
    }
  }

  function bindOperationEntries(){
    document.querySelectorAll('[data-main="operation"]').forEach(btn=>{
      btn.onclick=async ev=>{ev?.preventDefault?.();await openOperationMain()};
    });
  }

  // Al volver a Cambios y Muertos, mantener Operación fuera de su submenú.
  const previousGoMain=window.goMain;
  if(typeof previousGoMain==='function'){
    window.goMain=async function(name){
      if(name==='operation') return openOperationMain();
      const result=await previousGoMain.apply(this,arguments);
      document.querySelector('#operativoNav [data-opview="Operación"]')?.classList.add('hidden');
      ensureMainEntries();
      return result;
    };
  }

  // El flujo de login/preview puede reconstruir visibilidad y columnas móviles.
  const previousEnter=window.enter;
  if(typeof previousEnter==='function'){
    window.enter=async function(user){
      const result=await previousEnter.apply(this,arguments);
      ensureMainEntries();
      if(user?.role==='colaborador'){
        document.querySelector('.side .nav[data-main="operativo"]')?.classList.add('hidden');
        document.querySelector('#mobileMainNav .mnav[data-main="operativo"]')?.classList.add('hidden');
        markMainActive('operation');
        MAIN='operation';
        document.querySelector('#operativoNav')?.classList.add('hidden');
        const heroTitle=document.querySelector('#heroTitle');
        const heroSub=document.querySelector('#heroSub');
        if(heroTitle) heroTitle.textContent='Operación';
        if(heroSub) heroSub.textContent=subtitle;
      }
      syncMobileColumns();
      return result;
    };
  }

  ensureMainEntries();
  // V123 tiene timers cortos que pueden reinsertar el chip interno; CSS lo mantiene oculto.
  setTimeout(ensureMainEntries,0);
  setTimeout(ensureMainEntries,600);
  setTimeout(ensureMainEntries,1800);
  console.info('[V124] Operación movida al menú principal.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v124_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v124-operation-main-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Operations-UI-Version": "V124",
                },
            )
        except Exception as exc:
            print(f"[V124] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V124_OPERATION_MAIN_MODULE = True
    print("[V124] Operación instalada como módulo del menú principal.", flush=True)
