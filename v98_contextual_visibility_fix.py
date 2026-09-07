"""V98: hace visibles los filtros contextuales para el Super Administrador.

V97 ya insertaba correctamente el panel, pero comprobaba el usuario mediante
``window.USER``. La app declara ``USER`` con ``let``, por lo que no se publica
como propiedad de ``window`` y V97 terminaba ocultando tanto el panel como el
botón de retorno. Este parche sincroniza ambos estados y activa una sola vez la
vista contextual para el propietario, sin cambiar datos, cálculos, APIs ni PDF.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V98_CONTEXTUAL_VISIBILITY_FIX", False):
        return

    from fastapi.responses import HTMLResponse

    script = r'''
<script id="v98-contextual-visibility-fix-js">
(function(){
  const STORAGE='operacionesRopaFiltroUI';
  const MIGRATION='operacionesRopaFiltroUI_v98_owner_fix';
  let activated=false;

  function lexicalUser(){
    try{return (typeof USER!=='undefined' && USER)?USER:null}catch(e){return null}
  }
  function isOwner(u){
    return !!(u && (u.real_role==='superadmin'||u.role==='superadmin'||u.can_preview_roles===true));
  }
  function sync(){
    const u=lexicalUser();
    if(!u)return;

    // V97 consulta window.USER. La aplicación principal declara USER con `let`.
    // Mantenerlos sincronizados permite que la detección de propietario funcione.
    window.USER=u;

    const panel=document.getElementById('ctxPanel');
    const launcher=document.getElementById('ctxLauncher');
    if(!panel||!launcher)return;

    if(!isOwner(u)){
      panel.classList.add('hidden');
      launcher.classList.add('hidden');
      document.body.classList.remove('ctx-filter-mode');
      return;
    }

    // El fallo anterior pudo guardar "classic" antes de que terminara el login.
    // En la primera carga V98 se abre la nueva propuesta para que sea visible.
    if(!localStorage.getItem(MIGRATION)){
      localStorage.setItem(STORAGE,'contextual');
      localStorage.setItem(MIGRATION,'1');
      activated=false;
    }

    const mode=localStorage.getItem(STORAGE)||'contextual';
    if(mode==='contextual'){
      if(!activated || panel.classList.contains('hidden')){
        const btn=document.getElementById('ctxEnable');
        if(btn){btn.click();activated=true;}
      }
      panel.classList.remove('hidden');
      launcher.classList.add('hidden');
      document.body.classList.add('ctx-filter-mode');
    }else{
      panel.classList.add('hidden');
      launcher.classList.remove('hidden');
      document.body.classList.remove('ctx-filter-mode');
      activated=false;
    }
  }

  // Reaccionar al botón Vista clásica aunque V97 gestione internamente su modo.
  document.addEventListener('click',function(e){
    const classic=e.target.closest('#ctxClassic');
    if(classic){
      localStorage.setItem(STORAGE,'classic');
      setTimeout(sync,20);
      return;
    }
    const contextual=e.target.closest('#ctxEnable');
    if(contextual){
      localStorage.setItem(STORAGE,'contextual');
      activated=true;
      setTimeout(sync,20);
    }
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',sync);
  else sync();
  // USER se asigna después de validar la sesión/login, por eso se revalida.
  setInterval(sync,500);
})();
</script>
'''

    @module.app.middleware("http")
    async def _v98_contextual_visibility(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v98-contextual-visibility-fix-js" not in html:
                html = html.replace("</body>", script + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache", "Expires":"0"
            })
        except Exception as exc:
            print(f"[V98] UI warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    module._V98_CONTEXTUAL_VISIBILITY_FIX = True
    print("[V98] Visibilidad de filtros contextuales corregida para Super Administrador.", flush=True)
