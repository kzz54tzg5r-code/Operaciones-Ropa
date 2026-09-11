"""V122 · Entrada segura del perfil Colaborador.

Evita que el flujo general de inicio intente abrir Centro Operativo antes de
mostrar Operación. El colaborador entra directamente a su captura, sin consultar
endpoints de Cambios y Muertos, Análisis Comercial, Usuarios o configuración.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V122_COLLABORATOR_ENTRY", False):
        return
    from fastapi.responses import HTMLResponse

    js=r'''<script id="v122-collaborator-entry-js">
(function(){
  const previousEnter=window.enter;
  if(typeof previousEnter!=='function')return;
  window.enter=async function(u){
    if(!u||u.role!=='colaborador')return previousEnter(u);
    USER=u;
    $('#loginView')?.classList.add('hidden');
    $('#appView')?.classList.remove('hidden');
    if($('#profileName'))$('#profileName').textContent=u.username||'Colaborador';
    if($('#profileRole'))$('#profileRole').textContent='Colaborador';
    if($('#profileMeta'))$('#profileMeta').textContent='V122 · captura de productividad';
    if($('#viewRoleBox'))$('#viewRoleBox').classList.add('hidden');
    document.querySelectorAll('.superOnly,.adminOnly').forEach(x=>x.classList.add('hidden'));
    document.querySelectorAll('[data-main]').forEach(x=>x.classList.toggle('hidden',x.dataset.main!=='operativo'));
    if($('#analysisNav'))$('#analysisNav').classList.add('hidden');
    if($('#globalFilters'))$('#globalFilters').classList.add('hidden');
    if($('#operativoNav'))$('#operativoNav').classList.remove('hidden');
    document.querySelectorAll('#operativoNav [data-opview]').forEach(x=>{
      const keep=x.dataset.opview==='Operación';x.classList.toggle('hidden',!keep);x.classList.toggle('active',keep);
    });
    const main=document.querySelector('[data-main="operativo"]');
    if(main){main.classList.add('active');main.innerHTML='Operación<small>Captura de productividad</small>'}
    MAIN='operativo';OP_VIEW='Operación';OPER_PERIOD={type:'day',value:''};
    showPage('operativo');
    refreshHeaderClock?.();
    await renderOperativoView('Operación',true);
    try{
      const p=await api('/api/operation/profile');
      if(!p.profile_complete&&!p.must_change_password){
        if($('#v121ProfileStore'))$('#v121ProfileStore').textContent=`Tienda asignada: ${p.store||'Sin asignar'}`;
        if($('#v121ProfileNomina'))$('#v121ProfileNomina').value=p.employee_no||'';
        if($('#v121ProfileName'))$('#v121ProfileName').value=p.full_name||'';
        $('#v121ProfileModal')?.classList.remove('hidden');
      }
    }catch(e){console.warn('[V122] perfil colaborador',e)}
  };
  console.info('[V122] Entrada Colaborador directa a Operación activa.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v122_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'v122-collaborator-entry-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V122'
            })
        except Exception as exc:
            print(f'[V122] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V122_COLLABORATOR_ENTRY=True
    print('[V122] Colaborador entra directo a Operación sin consultar módulos restringidos.',flush=True)
