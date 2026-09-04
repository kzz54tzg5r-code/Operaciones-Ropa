"""V97: filtros contextuales reversibles para escritorio.

La versión estable V96 queda respaldada en ramas separadas. Este parche no
cambia cálculos, APIs ni datos: sólo agrega una capa visual opcional para que el
Super Administrador pueda probar filtros en la barra lateral, como en el
referente compartido, y volver al diseño clásico con un clic.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V97_CONTEXTUAL_FILTERS", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v97-contextual-filters-css">
@media (min-width:901px){
  .ctx-launcher,.ctx-panel{margin:7px 4px 4px;border:1px solid #dce4ee;border-radius:11px;background:#f7faff}
  .ctx-launcher{padding:7px}.ctx-launcher button{width:100%;border:0;border-radius:8px;background:#eef5ff;color:#123b73;padding:8px 7px;font-size:8px;font-weight:950;cursor:pointer}
  .ctx-panel{padding:9px;display:grid;gap:7px;max-height:48vh;overflow:auto}
  .ctx-head{display:flex;align-items:center;justify-content:space-between;gap:6px}.ctx-head b{font-size:8px;letter-spacing:.45px;text-transform:uppercase;color:#667085}
  .ctx-classic{border:1px solid #c8d5e6;background:#fff;color:#123b73;border-radius:7px;padding:5px 7px;font-size:7px;font-weight:900;cursor:pointer}
  .ctx-context{font-size:8px;line-height:1.3;color:#53657a;padding:6px 7px;background:#fff;border-radius:8px;border:1px solid #e2e8f0}
  .ctx-field label{display:block;margin:0 0 3px;font-size:6.8px;font-weight:950;color:#7b8797;text-transform:uppercase;letter-spacing:.3px}
  .ctx-field select,.ctx-field input{width:100%;min-height:31px;border:1px solid #cfd9e6;border-radius:8px;background:#fff;color:#123b73;padding:5px 7px;font-size:8px;font-weight:750}
  .ctx-actions{display:grid;grid-template-columns:1fr 1fr;gap:5px}.ctx-apply,.ctx-reset{border-radius:8px;padding:8px 6px;font-size:8px;font-weight:950;cursor:pointer}
  .ctx-apply{border:0;background:#1769e8;color:#fff}.ctx-reset{border:1px solid #cbd7e6;background:#fff;color:#123b73}
  body.ctx-filter-mode #operativoPeriodBar,body.ctx-filter-mode #globalFilters{display:none!important}
  .shell.sidebar-collapsed .ctx-panel,.shell.sidebar-collapsed .ctx-launcher{display:none!important}
}
@media(max-width:900px){.ctx-panel,.ctx-launcher{display:none!important}}
</style>
'''

    script = r'''
<script id="v97-contextual-filters-js">
(function(){
  const STORAGE='operacionesRopaFiltroUI';
  const q=s=>document.querySelector(s);
  const byId=id=>document.getElementById(id);
  let mounted=false;

  function isOwner(){
    try{return !!(window.USER && (USER.real_role==='superadmin'||USER.role==='superadmin'));}catch(e){return false}
  }
  function selectedText(sel){return sel?.options?.[sel.selectedIndex]?.textContent||''}
  function cloneOptions(src,dst){
    if(!src||!dst)return;
    const current=src.value;
    dst.innerHTML=[...src.options].map(o=>`<option value="${String(o.value).replace(/"/g,'&quot;')}">${o.textContent}</option>`).join('');
    if([...dst.options].some(o=>o.value===current))dst.value=current;
  }
  function field(id,label,sourceId,type='select'){
    const src=byId(sourceId);if(!src)return '';
    if(type==='select' && !src.options?.length)return '';
    const hidden=src.closest('.hidden')||src.closest('[id$="Wrap"]')?.classList.contains('hidden');
    if(hidden)return '';
    if(type==='date')return `<div class="ctx-field"><label>${label}</label><input type="date" id="${id}" value="${src.value||''}"></div>`;
    return `<div class="ctx-field"><label>${label}</label><select id="${id}"></select></div>`;
  }
  function visibleWrapper(id){const el=byId(id);return !!el&&!el.classList.contains('hidden')}

  function ensureMounted(){
    const side=q('.side');if(!side||mounted)return;
    const launcher=document.createElement('div');launcher.id='ctxLauncher';launcher.className='ctx-launcher hidden';launcher.innerHTML='<button type="button" id="ctxEnable">☰ Probar filtros contextuales</button>';
    const panel=document.createElement('div');panel.id='ctxPanel';panel.className='ctx-panel hidden';panel.innerHTML='<div class="ctx-head"><b>Filtros contextuales</b><button type="button" class="ctx-classic" id="ctxClassic">Vista clásica</button></div><div class="ctx-context" id="ctxContext"></div><div id="ctxFields"></div><div class="ctx-actions"><button class="ctx-reset" type="button" id="ctxReset">Restablecer</button><button class="ctx-apply" type="button" id="ctxApply">Aplicar</button></div>';
    const anchor=byId('viewRoleBox')||q('.profile');
    side.insertBefore(launcher,anchor||null);side.insertBefore(panel,anchor||null);mounted=true;
    byId('ctxEnable').onclick=()=>setMode('contextual');
    byId('ctxClassic').onclick=()=>setMode('classic');
    byId('ctxReset').onclick=resetContext;
    byId('ctxApply').onclick=applyContext;
  }

  function setMode(mode){
    if(!isOwner())mode='classic';
    localStorage.setItem(STORAGE,mode);
    document.body.classList.toggle('ctx-filter-mode',mode==='contextual');
    byId('ctxPanel')?.classList.toggle('hidden',mode!=='contextual');
    byId('ctxLauncher')?.classList.toggle('hidden',mode==='contextual'||!isOwner());
    if(mode==='contextual')renderContext();
  }

  function contextTitle(){
    try{
      if(MAIN==='operativo')return `Cambios y Muertos · ${OP_VIEW||'Centro Ejecutivo'}`;
      if(MAIN==='analysis'){
        const active=q('#analysisNav .switch.active');return `Análisis Comercial · ${active?.textContent?.trim()||'Reporte'}`;
      }
      return '';
    }catch(e){return ''}
  }

  function renderContext(){
    if(!mounted||!isOwner()||localStorage.getItem(STORAGE)!=='contextual')return;
    const fields=byId('ctxFields');if(!fields)return;
    let html='';
    try{
      if(MAIN==='operativo'){
        if(visibleWrapper('operPeriodModeWrap'))html+=field('ctxOperMode','Vista periodo','operPeriodMode');
        html+=field('ctxOperPeriod',byId('operPeriodLabel')?.textContent||'Periodo','operPeriodSelect');
        html+=field('ctxOperStore','Tienda','operStoreSelect');
        html+=field('ctxOperArea','Área','operAreaSelect');
        html+=field('ctxOperActivity','Actividad','operActivitySelect');
        if(visibleWrapper('operStartWrap'))html+=field('ctxOperStart','Desde','operStartDate','date');
        if(visibleWrapper('operEndWrap'))html+=field('ctxOperEnd','Hasta','operEndDate','date');
      }else if(MAIN==='analysis'){
        html+=field('ctxWeek','Periodo','week');
        if(visibleWrapper('globalStoreFilter'))html+=field('ctxStore','Tienda','store');
        if(visibleWrapper('globalSectionFilter'))html+=field('ctxSection','Sección','section');
        if(visibleWrapper('globalCatalogFilter'))html+=field('ctxCatalog','Tipo catálogo','catalog');
      }
    }catch(e){console.warn('[V97] render context',e)}
    fields.innerHTML=html||'<div class="ctx-context">Este apartado no necesita filtros.</div>';
    byId('ctxContext').textContent=contextTitle()||'Filtros según el reporte abierto';
    [['ctxOperMode','operPeriodMode'],['ctxOperPeriod','operPeriodSelect'],['ctxOperStore','operStoreSelect'],['ctxOperArea','operAreaSelect'],['ctxOperActivity','operActivitySelect'],['ctxWeek','week'],['ctxStore','store'],['ctxSection','section'],['ctxCatalog','catalog']].forEach(([a,b])=>cloneOptions(byId(b),byId(a)));
    const mode=byId('ctxOperMode');if(mode){mode.onchange=()=>{const src=byId('operPeriodMode');if(src){src.value=mode.value;if(typeof src.onchange==='function')src.onchange();setTimeout(renderContext,20)}}}
  }

  async function applyContext(){
    try{
      if(MAIN==='operativo'){
        const pairs=[['ctxOperPeriod','operPeriodSelect'],['ctxOperStore','operStoreSelect'],['ctxOperArea','operAreaSelect'],['ctxOperActivity','operActivitySelect']];
        pairs.forEach(([a,b])=>{const s=byId(a),t=byId(b);if(s&&t)t.value=s.value});
        const s1=byId('ctxOperStart'),t1=byId('operStartDate');if(s1&&t1)t1.value=s1.value;
        const s2=byId('ctxOperEnd'),t2=byId('operEndDate');if(s2&&t2)t2.value=s2.value;
        if(typeof OPER_PERIOD!=='undefined')OPER_PERIOD.value=byId('operPeriodSelect')?.value||'';
        if(typeof renderOperativoView==='function')await renderOperativoView(OP_VIEW||'Centro Ejecutivo');
      }else if(MAIN==='analysis'){
        [['ctxWeek','week'],['ctxStore','store'],['ctxSection','section'],['ctxCatalog','catalog']].forEach(([a,b])=>{const s=byId(a),t=byId(b);if(s&&t)t.value=s.value});
        const sec=byId('section')?.value||'Todas',store=byId('store')?.value||'Compañía';
        if(typeof loadDash==='function'){
          if(typeof SUB!=='undefined'&&SUB==='stores')await loadDash('Compañía',sec);else await loadDash(store,sec);
          if(typeof SUB!=='undefined'&&SUB==='sections'&&typeof loadCommercialDetail==='function')await loadCommercialDetail('rubro');
          if(typeof SUB!=='undefined'&&SUB==='areas'&&typeof loadCommercialDetail==='function')await loadCommercialDetail('area');
        }
      }
      setTimeout(renderContext,30);
    }catch(e){alert('No fue posible aplicar los filtros: '+(e.message||e))}
  }

  async function resetContext(){
    try{
      if(MAIN==='operativo'){
        const store=byId('ctxOperStore');if(store&&[...store.options].some(o=>o.value==='Compañía'))store.value='Compañía';
        const area=byId('ctxOperArea');if(area)area.value='';const act=byId('ctxOperActivity');if(act)act.value='';
      }else if(MAIN==='analysis'){
        const store=byId('ctxStore');if(store&&[...store.options].some(o=>o.value==='Compañía'))store.value='Compañía';
        const sec=byId('ctxSection');if(sec&&[...sec.options].some(o=>o.value==='Todas'))sec.value='Todas';
        const cat=byId('ctxCatalog');if(cat&&[...cat.options].some(o=>o.value==='Todos'))cat.value='Todos';
      }
      await applyContext();
    }catch(e){console.warn(e)}
  }

  function refresh(){
    ensureMounted();
    if(!isOwner()){setMode('classic');return}
    const saved=localStorage.getItem(STORAGE)||'contextual';setMode(saved);
  }

  document.addEventListener('click',e=>{
    if(e.target.closest('[data-main],[data-opview],[data-sub],#refresh,#operPeriodApply'))setTimeout(renderContext,60);
  },true);
  document.addEventListener('change',e=>{
    if(e.target.matches('#operPeriodSelect,#operStoreSelect,#operAreaSelect,#operActivitySelect,#week,#store,#section,#catalog'))setTimeout(renderContext,40);
  },true);
  const mo=new MutationObserver(()=>{if(isOwner()&&localStorage.getItem(STORAGE)!=='classic')setTimeout(renderContext,20)});
  const start=()=>{ensureMounted();const host=byId('app')||document.body;mo.observe(host,{childList:true,subtree:true});refresh()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  setInterval(()=>{if(!mounted||!isOwner())refresh()},1200);
})();
</script>
'''

    @module.app.middleware("http")
    async def _v97_contextual_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v97-contextual-filters-js" not in html:
                html = html.replace("</head>", css + "</head>", 1)
                html = html.replace("</body>", script + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache", "Expires":"0"
            })
        except Exception as exc:
            print(f"[V97] UI warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    module._V97_CONTEXTUAL_FILTERS = True
    print("[V97] Filtros contextuales reversibles activos para Super Administrador.", flush=True)
