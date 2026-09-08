"""V101: selector clásico/nuevo inyectado directamente en web/index.html.

V100 dependía de middleware de respuesta y en algunos ciclos de la SPA no
quedaba visible. V101 modifica el HTML base antes de servirlo y añade un
control persistente dentro del propio reporte. También implementa el drill-down
mínimo por Tienda -> Área/Sección -> Actividad/Tipo catálogo reutilizando los
selectores y funciones existentes.

No modifica cálculos, datos, PDFs ni permisos.
"""
from __future__ import annotations

from pathlib import Path

MARKER = "v101-static-filter-switch-js"

CSS = r'''
<style id="v101-static-filter-switch-css">
#v101FilterSwitch{margin:10px 0 12px;padding:9px 11px;border:1px solid #d8e3f0;border-radius:12px;background:#fff;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;box-shadow:0 1px 2px rgba(15,23,42,.04)}
#v101FilterSwitch .v101-label{font-size:8px;font-weight:950;color:#64748b;text-transform:uppercase;letter-spacing:.4px}
#v101FilterSwitch .v101-tabs{display:flex;gap:4px;background:#eef3f8;border-radius:9px;padding:3px}
#v101FilterSwitch button{border:0;background:transparent;color:#526174;border-radius:7px;padding:7px 11px;font-size:8px;font-weight:900;cursor:pointer}
#v101FilterSwitch button.active{background:#1769e8;color:#fff;box-shadow:0 1px 2px rgba(15,23,42,.12)}
#v101DrillBar{margin:0 0 12px;padding:9px 11px;border:1px solid #d8e3f0;border-radius:12px;background:#f8fbff;display:none;gap:8px}
#v101DrillBar.show{display:grid}
.v101-crumbs{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.v101-chip{border:1px solid #cbd9ea;background:#fff;color:#123b73;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:850;cursor:pointer}.v101-arrow{font-size:9px;color:#94a3b8;font-weight:900}
.v101-next{display:flex;gap:7px;align-items:end;flex-wrap:wrap}.v101-field{min-width:190px;max-width:280px}.v101-field label{display:block;margin-bottom:3px;font-size:7px;font-weight:950;color:#748196;text-transform:uppercase;letter-spacing:.35px}.v101-field select{width:100%;min-height:34px;border:1px solid #cbd9e6;border-radius:8px;background:#fff;color:#123b73;padding:6px 8px;font-size:9px;font-weight:800}.v101-reset{border:1px solid #cbd9e6;background:#fff;color:#123b73;border-radius:8px;min-height:34px;padding:6px 10px;font-size:8px;font-weight:900;cursor:pointer}
.v101-clickable{cursor:pointer!important}.v101-clickable:hover{background:#eef6ff!important;box-shadow:inset 0 0 0 1px #b8d7ff}.v101-clickable:after{content:' ›';color:#1769e8;font-weight:950}
body.v101-classic .v101-clickable:after{display:none}body.v101-classic .v101-clickable{cursor:default!important}
@media(max-width:900px){#v101FilterSwitch{padding:8px}#v101FilterSwitch .v101-label{font-size:7.5px}#v101FilterSwitch button{font-size:7.5px;padding:6px 8px}.v101-next{display:grid;grid-template-columns:1fr auto}.v101-field{min-width:0;max-width:none}}
</style>
'''

JS = r'''
<script id="v101-static-filter-switch-js">
(function(){
  const STORAGE='operacionesRopaReportFilterModeV101';
  const byId=id=>document.getElementById(id); const txt=v=>String(v==null?'':v).trim();
  const visible=el=>!!(el&&(el.offsetParent!==null||el.getClientRects().length));
  const generic=new Set(['','Compañía','Compania','Todas','Todos','Todas las tiendas','Todos los rubros']);
  let switcher=null,drill=null,timer=null,busy=false;
  function appMode(){try{return typeof MAIN!=='undefined'?MAIN:''}catch(e){return ''}}
  function mode(){try{return localStorage.getItem(STORAGE)||'classic'}catch(e){return 'classic'}}
  function dims(){
    if(appMode()==='operativo')return[
      {label:'Tienda',id:'operStoreSelect',defaults:new Set(['','Compañía','Compania'])},
      {label:'Área',id:'operAreaSelect',defaults:new Set(['','Todas','Todos'])},
      {label:'Actividad',id:'operActivitySelect',defaults:new Set(['','Todas','Todos'])}
    ];
    if(appMode()==='analysis')return[
      {label:'Tienda',id:'store',defaults:new Set(['','Compañía','Compania'])},
      {label:'Sección',id:'section',defaults:new Set(['','Todas','Todos'])},
      {label:'Tipo catálogo',id:'catalog',defaults:new Set(['','Todas','Todos'])}
    ];
    return[];
  }
  function opts(d){const s=byId(d.id);return s&&s.options?[...s.options].map(o=>({v:o.value,t:txt(o.textContent)})).filter(o=>o.t):[]}
  function useful(d){return opts(d).filter(o=>!generic.has(o.t)&&!d.defaults.has(o.v)&&!d.defaults.has(o.t))}
  function cur(d){const s=byId(d.id);if(!s)return'';const t=txt(s.options?.[s.selectedIndex]?.textContent||s.value);return(d.defaults.has(s.value)||d.defaults.has(t)||generic.has(t))?'':t}
  function resetDim(d){const s=byId(d.id);if(!s)return;const o=[...s.options].find(x=>d.defaults.has(x.value)||d.defaults.has(txt(x.textContent)))||s.options[0];if(o)s.value=o.value}
  function anchor(){
    const tables=[...document.querySelectorAll('table')].filter(visible).filter(t=>!t.closest('#ctxPanel'));
    if(!tables.length)return null;
    const t=tables[0], box=t.closest('.card,.panel,.section,.box,.tablewrap,.table-wrap,.table-container')||t.parentElement;
    return box&&box.parentNode?{parent:box.parentNode,before:box}:null;
  }
  async function rerender(){
    if(busy)return;busy=true;
    try{
      if(appMode()==='operativo'&&typeof renderOperativoView==='function')await renderOperativoView((typeof OP_VIEW!=='undefined'&&OP_VIEW)||'Centro Ejecutivo');
      else if(appMode()==='analysis'&&typeof loadDash==='function'){
        const sec=byId('section')?.value||'Todas',store=byId('store')?.value||'Compañía';
        if(typeof SUB!=='undefined'&&SUB==='stores')await loadDash('Compañía',sec);else await loadDash(store,sec);
        if(typeof SUB!=='undefined'&&SUB==='sections'&&typeof loadCommercialDetail==='function')await loadCommercialDetail('rubro');
        if(typeof SUB!=='undefined'&&SUB==='areas'&&typeof loadCommercialDetail==='function')await loadCommercialDetail('area');
      }
    }catch(e){console.warn('[V101] rerender',e)}finally{busy=false;setTimeout(refresh,80)}
  }
  async function choose(d,value){
    const ds=dims().filter(x=>byId(x.id)&&useful(x).length),idx=ds.findIndex(x=>x.id===d.id);if(idx<0)return;
    const s=byId(d.id),o=[...s.options].find(x=>x.value===value||txt(x.textContent)===value);if(!o)return;s.value=o.value;
    for(let i=idx+1;i<ds.length;i++)resetDim(ds[i]);await rerender();
  }
  async function clearFrom(i){const ds=dims().filter(x=>byId(x.id)&&useful(x).length);for(let j=i;j<ds.length;j++)resetDim(ds[j]);await rerender()}
  async function resetAll(){dims().forEach(resetDim);await rerender()}
  function apply(m){m=m==='interactive'?'interactive':'classic';try{localStorage.setItem(STORAGE,m)}catch(e){};document.body.classList.toggle('v101-classic',m==='classic');document.body.classList.toggle('v101-interactive',m==='interactive');if(switcher){switcher.querySelector('[data-v101="classic"]')?.classList.toggle('active',m==='classic');switcher.querySelector('[data-v101="interactive"]')?.classList.toggle('active',m==='interactive')}refresh()}
  function renderControls(){
    const a=anchor();if(!a)return;
    if(!switcher){switcher=document.createElement('div');switcher.id='v101FilterSwitch';switcher.innerHTML='<div class="v101-label">Forma de filtrar este reporte</div><div class="v101-tabs"><button type="button" data-v101="classic">Filtro clásico</button><button type="button" data-v101="interactive">Desglose interactivo · nuevo</button></div>';switcher.onclick=e=>{const b=e.target.closest('[data-v101]');if(b)apply(b.dataset.v101)}}
    if(switcher.parentNode!==a.parent||switcher.nextSibling!==a.before)a.parent.insertBefore(switcher,a.before);
    if(!drill){drill=document.createElement('div');drill.id='v101DrillBar'}
    if(drill.parentNode!==a.parent||drill.nextSibling!==a.before)a.parent.insertBefore(drill,a.before);
    const m=mode();switcher.querySelector('[data-v101="classic"]')?.classList.toggle('active',m==='classic');switcher.querySelector('[data-v101="interactive"]')?.classList.toggle('active',m==='interactive');document.body.classList.toggle('v101-classic',m==='classic');document.body.classList.toggle('v101-interactive',m==='interactive');
    renderDrill();mark();
  }
  function renderDrill(){
    if(!drill)return;const ds=dims().filter(d=>byId(d.id)&&useful(d).length);if(mode()!=='interactive'||!ds.length){drill.classList.remove('show');return}
    drill.classList.add('show');const sel=ds.map((d,i)=>({d,i,v:cur(d)})).filter(x=>x.v);let next=0;while(next<ds.length&&cur(ds[next]))next++;
    let crumbs=sel.length?'':'<span style="font-size:8px;color:#667085">Haz clic en una tienda de la tabla o selecciona el siguiente nivel.</span>';sel.forEach((x,n)=>{if(n)crumbs+='<span class="v101-arrow">›</span>';crumbs+=`<button class="v101-chip" data-clear="${x.i}"><b>${x.d.label}:</b> ${x.v} ×</button>`});
    let tail='';if(next<ds.length){const d=ds[next],oo=useful(d).map(o=>`<option value="${o.v}">${o.t}</option>`).join('');tail=`<div class="v101-next"><div class="v101-field"><label>Siguiente nivel · ${d.label}</label><select id="v101Next"><option value="">Selecciona ${d.label.toLowerCase()}…</option>${oo}</select></div><button class="v101-reset" id="v101Reset">Restablecer</button></div>`}else tail='<div class="v101-next"><span style="font-size:8px;color:#667085"><b>Detalle filtrado.</b> Puedes quitar un nivel o restablecer.</span><button class="v101-reset" id="v101Reset">Restablecer</button></div>';
    drill.innerHTML='<div class="v101-crumbs">'+crumbs+'</div>'+tail;drill.querySelectorAll('[data-clear]').forEach(b=>b.onclick=()=>clearFrom(Number(b.dataset.clear)));const n=byId('v101Next');if(n&&next<ds.length)n.onchange=()=>{if(n.value)choose(ds[next],n.value)};byId('v101Reset')?.addEventListener('click',resetAll)
  }
  function mark(){
    document.querySelectorAll('.v101-clickable').forEach(c=>{c.classList.remove('v101-clickable');delete c.dataset.v101Dim;delete c.dataset.v101Val});if(mode()!=='interactive')return;
    const ds=dims().filter(d=>byId(d.id)&&useful(d).length),maps=ds.map(d=>({d,m:new Map(useful(d).map(o=>[o.t.toLocaleLowerCase('es-MX'),o.v]))}));
    document.querySelectorAll('table td').forEach(c=>{const v=txt(c.textContent).replace(/\s+/g,' ').toLocaleLowerCase('es-MX'),h=maps.find(x=>x.m.has(v));if(h){c.classList.add('v101-clickable');c.dataset.v101Dim=h.d.id;c.dataset.v101Val=h.m.get(v);c.title=`Filtrar por ${h.d.label}: ${txt(c.textContent)}`}})
  }
  function refresh(){clearTimeout(timer);timer=setTimeout(renderControls,45)}
  document.addEventListener('click',e=>{const c=e.target.closest('.v101-clickable');if(c&&mode()==='interactive'){const d=dims().find(x=>x.id===c.dataset.v101Dim);if(d){e.preventDefault();e.stopPropagation();choose(d,c.dataset.v101Val);return}}if(e.target.closest('[data-main],[data-opview],[data-sub],#refresh,#operPeriodApply'))setTimeout(refresh,100)},true);
  document.addEventListener('change',e=>{if(e.target.matches('#operStoreSelect,#operAreaSelect,#operActivitySelect,#store,#section,#catalog,#week,#operPeriodSelect'))setTimeout(refresh,70)},true);
  const start=()=>{const host=byId('app')||document.body;new MutationObserver(()=>refresh()).observe(host,{childList:true,subtree:true});refresh()};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''


def install(module) -> None:
    if getattr(module, "_V101_STATIC_FILTER_SWITCH", False):
        return
    path = Path(module.WEB) / "index.html"
    if not path.exists():
        print("[V101] web/index.html no encontrado", flush=True)
        return
    try:
        html = path.read_text(encoding="utf-8")
        if MARKER not in html:
            html = html.replace("</head>", CSS + "\n</head>", 1)
            html = html.replace("</body>", JS + "\n</body>", 1)
        html = html.replace("V93 · HTML", "V101 · filtro clásico / interactivo")
        html = html.replace("V93 · HTML · Excel capacidades", "V101 · filtro clásico / interactivo · Excel capacidades")
        path.write_text(html, encoding="utf-8")
        module._V101_STATIC_FILTER_SWITCH = True
        print("[V101] Selector clásico/nuevo fijado directamente en web/index.html.", flush=True)
    except Exception as exc:
        print(f"[V101] ERROR {type(exc).__name__}: {exc}", flush=True)
