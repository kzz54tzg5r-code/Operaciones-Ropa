"""V102: selector de filtro visible e interactivo, aplicado como última capa.

Corrige el problema observado en V100/V101 donde el despliegue estaba activo
pero el control no aparecía en el HTML final. V102 se instala como el último
middleware y modifica la respuesta final de `/`, por encima de los middlewares
anteriores. El selector se inserta como HTML real dentro de `<main>`, por lo
que es visible aun antes de que se rendericen las tablas.

No modifica cálculos, datos, PDFs ni permisos. Los experimentos V97-V101 quedan
fuera del arranque de producción y se conserva respaldo en ramas Git.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V102_FINAL_FILTER_SWITCH", False):
        return

    from fastapi.responses import HTMLResponse, JSONResponse

    css = r'''
<style id="v102-filter-css">
#ctxPanel,#ctxLauncher,#v99Drillbar,#v100FilterSwitch,#v101FilterSwitch,#v101DrillBar{display:none!important}
#v102FilterMode{margin:10px 0 12px;padding:10px 12px;border:1px solid #cfdceb;border-radius:12px;background:#fff;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;box-shadow:0 1px 3px rgba(15,23,42,.05)}
#v102FilterMode .v102-left{display:grid;gap:2px}#v102FilterMode .v102-title{font-size:8px;font-weight:950;text-transform:uppercase;letter-spacing:.4px;color:#64748b}#v102FilterMode .v102-sub{font-size:7.5px;color:#7b8798}
#v102FilterMode .v102-tabs{display:flex;gap:4px;background:#edf3f9;border-radius:9px;padding:3px}
#v102FilterMode button{border:0;background:transparent;color:#526174;border-radius:7px;padding:7px 11px;font-size:8px;font-weight:900;cursor:pointer}
#v102FilterMode button.active{background:#1769e8;color:#fff;box-shadow:0 1px 2px rgba(15,23,42,.15)}
#v102FilterMode .v102-version{font-size:7px;font-weight:900;color:#1769e8;border:1px solid #bdd5fb;border-radius:999px;padding:4px 7px;background:#f4f8ff}
#v102Drill{display:none;margin:-4px 0 12px;padding:10px 12px;border:1px solid #d7e3f0;border-radius:12px;background:#f8fbff;gap:8px}#v102Drill.show{display:grid}
.v102-crumbs{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.v102-chip{border:1px solid #cbd9ea;background:#fff;color:#123b73;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:850;cursor:pointer}.v102-arrow{font-size:9px;color:#94a3b8;font-weight:900}
.v102-next{display:flex;align-items:end;gap:7px;flex-wrap:wrap}.v102-field{min-width:190px;max-width:300px;flex:0 1 260px}.v102-field label{display:block;margin:0 0 3px;font-size:7px;font-weight:950;text-transform:uppercase;letter-spacing:.35px;color:#748196}.v102-field select{width:100%;min-height:34px;border:1px solid #cbd9e6;border-radius:8px;background:#fff;color:#123b73;padding:6px 8px;font-size:9px;font-weight:800}.v102-reset{border:1px solid #cbd9e6;background:#fff;color:#123b73;border-radius:8px;min-height:34px;padding:6px 10px;font-size:8px;font-weight:900;cursor:pointer}
.v102-clickable{cursor:pointer!important}.v102-clickable:hover{background:#eef6ff!important;box-shadow:inset 0 0 0 1px #b8d7ff}.v102-clickable:after{content:' ›';color:#1769e8;font-weight:950}
body.v102-classic .v102-clickable{cursor:default!important}body.v102-classic .v102-clickable:after{display:none!important}
@media(max-width:900px){#v102FilterMode{padding:8px 9px}#v102FilterMode .v102-tabs{width:100%}#v102FilterMode button{flex:1;font-size:7.5px;padding:7px 6px}.v102-next{display:grid;grid-template-columns:1fr auto}.v102-field{min-width:0;max-width:none}}
</style>
'''

    bar = '''<div id="v102FilterMode" data-ui-version="V102"><div class="v102-left"><div class="v102-title">Forma de filtrar este reporte</div><div class="v102-sub">Puedes conservar los filtros actuales o seleccionar directamente dentro de la tabla.</div></div><div class="v102-tabs"><button type="button" data-v102="classic">Filtro clásico</button><button type="button" data-v102="interactive">Desglose interactivo · nuevo</button></div><span class="v102-version">V102</span></div><div id="v102Drill"></div>'''

    js = r'''
<script id="v102-filter-js">
(function(){
  const STORAGE='operacionesRopaFilterModeV102';
  const byId=id=>document.getElementById(id), txt=v=>String(v==null?'':v).trim();
  const generic=new Set(['','Compañía','Compania','Todas','Todos','Todas las tiendas','Todos los rubros']);
  let timer=null,busy=false;
  const mode=()=>{try{return localStorage.getItem(STORAGE)||'classic'}catch(e){return'classic'}};
  function dims(){
    if(byId('operStoreSelect')) return [
      {label:'Tienda',id:'operStoreSelect',defaults:new Set(['','Compañía','Compania'])},
      {label:'Área',id:'operAreaSelect',defaults:new Set(['','Todas','Todos'])},
      {label:'Actividad',id:'operActivitySelect',defaults:new Set(['','Todas','Todos'])}
    ];
    if(byId('store')) return [
      {label:'Tienda',id:'store',defaults:new Set(['','Compañía','Compania'])},
      {label:'Sección',id:'section',defaults:new Set(['','Todas','Todos'])},
      {label:'Tipo catálogo',id:'catalog',defaults:new Set(['','Todas','Todos'])}
    ];
    return [];
  }
  function opts(d){const s=byId(d.id);return s&&s.options?[...s.options].map(o=>({v:o.value,t:txt(o.textContent)})).filter(o=>o.t):[]}
  function useful(d){return opts(d).filter(o=>!generic.has(o.t)&&!d.defaults.has(o.v)&&!d.defaults.has(o.t))}
  function current(d){const s=byId(d.id);if(!s)return'';const t=txt(s.options?.[s.selectedIndex]?.textContent||s.value);return d.defaults.has(s.value)||d.defaults.has(t)||generic.has(t)?'':t}
  function resetDim(d){const s=byId(d.id);if(!s)return;const o=[...s.options].find(x=>d.defaults.has(x.value)||d.defaults.has(txt(x.textContent)))||s.options[0];if(o)s.value=o.value}
  function setMode(m){m=m==='interactive'?'interactive':'classic';try{localStorage.setItem(STORAGE,m)}catch(e){};document.body.classList.toggle('v102-classic',m==='classic');document.body.classList.toggle('v102-interactive',m==='interactive');document.querySelectorAll('#v102FilterMode [data-v102]').forEach(b=>b.classList.toggle('active',b.dataset.v102===m));refresh()}
  async function rerender(){
    if(busy)return;busy=true;
    try{
      const q=byId('operPeriodApply');
      if(q){q.click();}
      else if(byId('refresh')){byId('refresh').click();}
      else dims().forEach(d=>byId(d.id)?.dispatchEvent(new Event('change',{bubbles:true})));
    }catch(e){console.warn('[V102] rerender',e)}finally{busy=false;setTimeout(refresh,120)}
  }
  async function choose(d,value){const ds=dims().filter(x=>byId(x.id)&&useful(x).length),idx=ds.findIndex(x=>x.id===d.id);if(idx<0)return;const s=byId(d.id),o=[...s.options].find(x=>x.value===value||txt(x.textContent)===value);if(!o)return;s.value=o.value;for(let i=idx+1;i<ds.length;i++)resetDim(ds[i]);await rerender()}
  async function clearFrom(i){const ds=dims().filter(x=>byId(x.id)&&useful(x).length);for(let j=i;j<ds.length;j++)resetDim(ds[j]);await rerender()}
  async function resetAll(){dims().forEach(resetDim);await rerender()}
  function renderDrill(){
    const drill=byId('v102Drill');if(!drill)return;const ds=dims().filter(d=>byId(d.id)&&useful(d).length);
    if(mode()!=='interactive'||!ds.length){drill.classList.remove('show');return}
    drill.classList.add('show');const selected=ds.map((d,i)=>({d,i,v:current(d)})).filter(x=>x.v);let next=0;while(next<ds.length&&current(ds[next]))next++;
    let crumbs=selected.length?'':'<span style="font-size:8px;color:#667085">Haz clic en una tienda de la tabla o selecciona el siguiente nivel.</span>';
    selected.forEach((x,n)=>{if(n)crumbs+='<span class="v102-arrow">›</span>';crumbs+=`<button type="button" class="v102-chip" data-clear="${x.i}"><b>${x.d.label}:</b> ${x.v} ×</button>`});
    let tail='';if(next<ds.length){const d=ds[next],oo=useful(d).map(o=>`<option value="${o.v}">${o.t}</option>`).join('');tail=`<div class="v102-next"><div class="v102-field"><label>Siguiente nivel · ${d.label}</label><select id="v102Next"><option value="">Selecciona ${d.label.toLowerCase()}…</option>${oo}</select></div><button type="button" class="v102-reset" id="v102Reset">Restablecer</button></div>`}else tail='<div class="v102-next"><span style="font-size:8px;color:#667085"><b>Detalle filtrado.</b> Quita un nivel o restablece.</span><button type="button" class="v102-reset" id="v102Reset">Restablecer</button></div>';
    drill.innerHTML='<div class="v102-crumbs">'+crumbs+'</div>'+tail;drill.querySelectorAll('[data-clear]').forEach(b=>b.onclick=()=>clearFrom(Number(b.dataset.clear)));const n=byId('v102Next');if(n&&next<ds.length)n.onchange=()=>{if(n.value)choose(ds[next],n.value)};byId('v102Reset')?.addEventListener('click',resetAll)
  }
  function mark(){document.querySelectorAll('.v102-clickable').forEach(c=>{c.classList.remove('v102-clickable');delete c.dataset.v102Dim;delete c.dataset.v102Val});if(mode()!=='interactive')return;const ds=dims().filter(d=>byId(d.id)&&useful(d).length),maps=ds.map(d=>({d,m:new Map(useful(d).map(o=>[o.t.toLocaleLowerCase('es-MX'),o.v]))}));document.querySelectorAll('table td').forEach(c=>{const value=txt(c.textContent).replace(/\s+/g,' ').toLocaleLowerCase('es-MX'),hit=maps.find(x=>x.m.has(value));if(hit){c.classList.add('v102-clickable');c.dataset.v102Dim=hit.d.id;c.dataset.v102Val=hit.m.get(value);c.title=`Filtrar por ${hit.d.label}: ${txt(c.textContent)}`}})}
  function moveBar(){const bar=byId('v102FilterMode'),drill=byId('v102Drill');if(!bar)return;const nav=byId('operativoNav');if(nav&&nav.parentNode){nav.insertAdjacentElement('afterend',bar);bar.insertAdjacentElement('afterend',drill);return}const filters=byId('globalFilters');if(filters&&filters.parentNode){filters.insertAdjacentElement('afterend',bar);bar.insertAdjacentElement('afterend',drill)}}
  function refresh(){clearTimeout(timer);timer=setTimeout(()=>{moveBar();document.querySelectorAll('#v102FilterMode [data-v102]').forEach(b=>b.classList.toggle('active',b.dataset.v102===mode()));document.body.classList.toggle('v102-classic',mode()==='classic');document.body.classList.toggle('v102-interactive',mode()==='interactive');renderDrill();mark()},50)}
  document.addEventListener('click',e=>{const m=e.target.closest('#v102FilterMode [data-v102]');if(m){setMode(m.dataset.v102);return}const c=e.target.closest('.v102-clickable');if(c&&mode()==='interactive'){const d=dims().find(x=>x.id===c.dataset.v102Dim);if(d){e.preventDefault();e.stopPropagation();choose(d,c.dataset.v102Val);return}}if(e.target.closest('[data-main],[data-opview],[data-sub],#operPeriodApply,#refresh'))setTimeout(refresh,120)},true);
  document.addEventListener('change',e=>{if(e.target.matches('#operStoreSelect,#operAreaSelect,#operActivitySelect,#store,#section,#catalog,#week,#operPeriodSelect'))setTimeout(refresh,80)},true);
  const start=()=>{setMode(mode());new MutationObserver(()=>refresh()).observe(document.body,{childList:true,subtree:true});refresh()};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''

    @module.app.middleware("http")
    async def _v102_final_ui(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            # Limpiar controles experimentales si fueron inyectados por alguna capa antigua.
            if "v102-filter-js" not in html:
                html=html.replace("</head>",css+"\n</head>",1)
                if '<main class="main">' in html:
                    html=html.replace('<main class="main">','<main class="main">'+bar,1)
                else:
                    html=html.replace("<body>","<body>"+bar,1)
                html=html.replace("</body>",js+"\n</body>",1)
            html=html.replace("V93 · HTML", "V102 · filtro clásico / interactivo")
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operaciones-UI":"V102",
            })
        except Exception as exc:
            print(f"[V102] ERROR UI {type(exc).__name__}: {exc}",flush=True)
            return response

    @module.app.get("/api/ui-version-v102")
    def _v102_version():
        return JSONResponse({"ui":"V102","filter_switch":True,"mode_options":["classic","interactive"]})

    module._V102_FINAL_FILTER_SWITCH=True
    print("[V102] Selector final clásico/interactivo instalado como última capa.",flush=True)
