"""V100: selector visible entre filtros clásicos y desglose interactivo.

Corrige la experiencia de V99: el usuario siempre puede ver y elegir dentro del
propio reporte entre usar los filtros clásicos existentes o el nuevo desglose
por clic dentro de la tabla. V100 no modifica cálculos, datos, PDFs ni permisos.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V100_VISIBLE_FILTER_MODE", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v100-visible-filter-mode-css">
.v100-filter-switch{
  margin:8px 0 10px;padding:8px 10px;border:1px solid #d9e3ef;border-radius:11px;
  background:#fff;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap
}
.v100-filter-switch .v100-label{font-size:8px;font-weight:950;color:#64748b;text-transform:uppercase;letter-spacing:.35px}
.v100-filter-switch .v100-tabs{display:flex;gap:4px;background:#eef3f8;border-radius:9px;padding:3px}
.v100-filter-switch button{border:0;background:transparent;color:#526174;border-radius:7px;padding:7px 10px;font-size:8px;font-weight:900;cursor:pointer}
.v100-filter-switch button.active{background:#1769e8;color:#fff;box-shadow:0 1px 2px rgba(15,23,42,.12)}
body.v100-classic-mode #v99Drillbar{display:none!important}
body.v100-classic-mode .v99-clickable{cursor:default!important;box-shadow:none!important}
body.v100-classic-mode .v99-clickable:after{display:none!important}
body.v100-classic-mode .v99-clickable:hover{background:inherit!important;box-shadow:none!important}
@media(max-width:900px){
 .v100-filter-switch{padding:7px 8px}.v100-filter-switch .v100-label{font-size:7.5px}
 .v100-filter-switch button{font-size:7.5px;padding:6px 8px}
}
</style>
'''

    script = r'''
<script id="v100-visible-filter-mode-js">
(function(){
  const STORAGE='operacionesRopaReportFilterMode';
  const byId=id=>document.getElementById(id);
  const visible=el=>!!(el&&(el.offsetParent!==null||el.getClientRects().length));
  let switcher=null,timer=null;

  function currentMode(){
    try{return localStorage.getItem(STORAGE)||'classic'}catch(e){return 'classic'}
  }
  function findAnchor(){
    const tables=[...document.querySelectorAll('#app table,main table,.main table')].filter(visible).filter(t=>!t.closest('#ctxPanel'));
    if(tables.length){
      const table=tables[0];const card=table.closest('.card,.panel,.section,.box,.table-wrap,.table-container')||table.parentElement;
      if(card?.parentNode)return{parent:card.parentNode,before:card};
      if(table.parentNode)return{parent:table.parentNode,before:table};
    }
    const host=['#operativoPanel','#analysisPanel','#app main','#app .content','.main','.content'].map(s=>document.querySelector(s)).find(visible);
    return host?{parent:host,before:host.firstChild}:null;
  }
  function pokeV99(){
    const host=byId('app')||document.body;
    const n=document.createElement('i');n.style.display='none';host.appendChild(n);n.remove();
  }
  function applyMode(mode){
    mode=mode==='interactive'?'interactive':'classic';
    try{localStorage.setItem(STORAGE,mode)}catch(e){}
    document.body.classList.toggle('v100-classic-mode',mode==='classic');
    document.body.classList.toggle('v100-interactive-mode',mode==='interactive');
    if(switcher){
      switcher.querySelector('[data-v100="classic"]')?.classList.toggle('active',mode==='classic');
      switcher.querySelector('[data-v100="interactive"]')?.classList.toggle('active',mode==='interactive');
    }
    if(mode==='classic'){
      document.querySelectorAll('.v99-clickable').forEach(c=>{
        c.classList.remove('v99-clickable');delete c.dataset.v99Dim;delete c.dataset.v99Value;
      });
      const drill=byId('v99Drillbar');if(drill)drill.style.display='none';
    }else{
      const drill=byId('v99Drillbar');if(drill)drill.style.removeProperty('display');
    }
    pokeV99();
  }
  function render(){
    const a=findAnchor();if(!a)return;
    if(!switcher){
      switcher=document.createElement('div');switcher.id='v100FilterSwitch';switcher.className='v100-filter-switch';
      switcher.innerHTML='<div class="v100-label">Forma de filtrar este reporte</div><div class="v100-tabs"><button type="button" data-v100="classic">Filtro clásico</button><button type="button" data-v100="interactive">Desglose interactivo · nuevo</button></div>';
      switcher.addEventListener('click',e=>{const b=e.target.closest('[data-v100]');if(b)applyMode(b.dataset.v100)});
    }
    if(switcher.parentNode!==a.parent||switcher.nextSibling!==a.before)a.parent.insertBefore(switcher,a.before||null);
    applyMode(currentMode());
  }
  function refresh(){clearTimeout(timer);timer=setTimeout(render,35)}
  const start=()=>{
    const host=byId('app')||document.body;
    new MutationObserver(()=>refresh()).observe(host,{childList:true,subtree:true});
    refresh();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''

    @module.app.middleware("http")
    async def _v100_visible_filter_mode(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")

            # Hacer que V99 respete el selector visible V100.
            html=html.replace(
                "const $=s=>document.querySelector(s), byId=id=>document.getElementById(id);\n  let busy=false, bar=null, observer=null, timer=null;",
                "const $=s=>document.querySelector(s), byId=id=>document.getElementById(id);\n  let busy=false, bar=null, observer=null, timer=null;\n  const v99Interactive=()=>{try{return (localStorage.getItem('operacionesRopaReportFilterMode')||'classic')==='interactive'}catch(e){return false}};"
            )
            html=html.replace(
                "function renderBar(){\n    if(!ensureBar()) return;",
                "function renderBar(){\n    if(!ensureBar()) return;\n    if(!v99Interactive()){bar.style.display='none';return;}"
            )
            html=html.replace(
                "function markClickable(){\n    const dims=availableDims(); if(!dims.length) return;",
                "function markClickable(){\n    document.querySelectorAll('#app table td, #app table th, main table td, main table th').forEach(cell=>{cell.classList.remove('v99-clickable');delete cell.dataset.v99Dim;delete cell.dataset.v99Value;});\n    if(!v99Interactive()) return;\n    const dims=availableDims(); if(!dims.length) return;"
            )
            html=html.replace(
                "const cell=e.target.closest('.v99-clickable'); if(cell && !busy){",
                "const cell=e.target.closest('.v99-clickable'); if(v99Interactive() && cell && !busy){"
            )

            if "v100-visible-filter-mode-js" not in html:
                html=html.replace("</head>",css+"</head>",1)
                html=html.replace("</body>",script+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0"
            })
        except Exception as exc:
            print(f"[V100] UI warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    module._V100_VISIBLE_FILTER_MODE=True
    print("[V100] Selector visible Filtro clásico / Desglose interactivo activo.",flush=True)
