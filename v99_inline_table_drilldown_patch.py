"""V99: desglose contextual directamente dentro del reporte.

Sustituye el experimento visual lateral V97/V98 por una interacción dentro de
las propias tablas: al hacer clic en una tienda (o en la siguiente dimensión)
se aplica el filtro del reporte actual y aparece, junto a la tabla, el siguiente
nivel de desglose disponible.

No modifica cálculos, APIs ni permisos; reutiliza los selectores y funciones de
render existentes, por lo que sólo permite valores que ya están disponibles
para el usuario actual.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V99_INLINE_TABLE_DRILLDOWN", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v99-inline-drill-css">
/* V99 reemplaza la prueba de filtros en sidebar. Los filtros clásicos originales
   permanecen disponibles; el nuevo desglose vive dentro del reporte. */
#ctxPanel,#ctxLauncher{display:none!important}
.v99-drillbar{
  margin:10px 0 12px;padding:10px 12px;border:1px solid #d9e3ef;border-radius:12px;
  background:#f8fbff;box-shadow:0 1px 2px rgba(15,23,42,.03);display:grid;gap:8px
}
.v99-drilltop{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.v99-drilltitle{font-size:10px;font-weight:950;color:#123b73;letter-spacing:.2px}
.v99-drillhint{font-size:8px;color:#667085;line-height:1.35}
.v99-crumbs{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.v99-chip{border:1px solid #cbd9ea;background:#fff;color:#123b73;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:850;cursor:pointer}
.v99-chip b{font-weight:950}.v99-arrow{font-size:9px;color:#94a3b8;font-weight:900}
.v99-next{display:flex;align-items:end;gap:7px;flex-wrap:wrap}
.v99-nextfield{min-width:175px;max-width:280px;flex:0 1 240px}
.v99-nextfield label{display:block;margin:0 0 3px;font-size:7px;font-weight:950;text-transform:uppercase;letter-spacing:.35px;color:#748196}
.v99-nextfield select{width:100%;min-height:34px;border:1px solid #cbd9e6;border-radius:8px;background:#fff;color:#123b73;padding:6px 8px;font-size:9px;font-weight:800}
.v99-reset{border:1px solid #cbd9e6;background:#fff;color:#123b73;border-radius:8px;min-height:34px;padding:6px 10px;font-size:8px;font-weight:900;cursor:pointer}
.v99-clickable{cursor:pointer!important;position:relative}
.v99-clickable:hover{background:#eef6ff!important;box-shadow:inset 0 0 0 1px #b8d7ff}
.v99-clickable:after{content:'›';margin-left:5px;color:#1769e8;font-weight:950}
@media(max-width:900px){
 .v99-drillbar{margin:8px 0 10px;padding:9px;border-radius:10px}
 .v99-drilltitle{font-size:9px}.v99-drillhint{font-size:7.5px}
 .v99-next{display:grid;grid-template-columns:1fr auto;width:100%}
 .v99-nextfield{min-width:0;max-width:none;width:100%}.v99-chip{font-size:7.5px}
}
</style>
'''

    script = r'''
<script id="v99-inline-drill-js">
(function(){
  const $=s=>document.querySelector(s), byId=id=>document.getElementById(id);
  let busy=false, bar=null, observer=null, timer=null;
  try{ localStorage.setItem('operacionesRopaFiltroUI','classic'); }catch(e){}

  const generic = new Set(['','Compañía','Compania','Todas','Todos','Todas las tiendas','Todos los rubros']);
  const txt = v => String(v==null?'':v).trim();
  const esc = s => String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const visible = el => !!(el && (el.offsetParent!==null || el.getClientRects().length));

  function mode(){ try{return typeof MAIN!=='undefined'?MAIN:''}catch(e){return ''} }
  function sourceDimensions(){
    if(mode()==='operativo') return [
      {key:'store',label:'Tienda',id:'operStoreSelect',defaults:new Set(['','Compañía','Compania'])},
      {key:'area',label:'Área',id:'operAreaSelect',defaults:new Set(['','Todas','Todos'])},
      {key:'activity',label:'Actividad',id:'operActivitySelect',defaults:new Set(['','Todas','Todos'])}
    ];
    if(mode()==='analysis') return [
      {key:'store',label:'Tienda',id:'store',defaults:new Set(['','Compañía','Compania'])},
      {key:'section',label:'Sección',id:'section',defaults:new Set(['','Todas','Todos'])},
      {key:'catalog',label:'Tipo catálogo',id:'catalog',defaults:new Set(['','Todas','Todos'])}
    ];
    return [];
  }
  function options(dim){
    const s=byId(dim.id); if(!s || !s.options) return [];
    return [...s.options].map(o=>({value:o.value,text:txt(o.textContent)})).filter(o=>o.text);
  }
  function meaningful(dim){ return options(dim).filter(o=>!generic.has(o.text) && !dim.defaults.has(o.value) && !dim.defaults.has(o.text)); }
  function current(dim){
    const s=byId(dim.id); if(!s) return '';
    const label=txt(s.options?.[s.selectedIndex]?.textContent || s.value);
    if(dim.defaults.has(s.value)||dim.defaults.has(label)||generic.has(label)) return '';
    return label;
  }
  function availableDims(){ return sourceDimensions().filter(d=>byId(d.id) && meaningful(d).length); }

  function findAnchor(){
    const tables=[...document.querySelectorAll('#app table, main table, .main table')].filter(visible).filter(t=>!t.closest('#ctxPanel'));
    if(tables.length){
      const table=tables[0]; const card=table.closest('.card,.panel,.section,.box,.table-wrap,.table-container')||table.parentElement;
      if(card?.parentNode) return {parent:card.parentNode,before:card};
      if(table.parentNode) return {parent:table.parentNode,before:table};
    }
    const host=['#operativoPanel','#analysisPanel','#app main','#app .content','.main','.content'].map($).find(visible);
    return host?{parent:host,before:host.firstChild}:null;
  }
  function ensureBar(){
    if(!bar){ bar=document.createElement('div');bar.id='v99Drillbar';bar.className='v99-drillbar'; }
    const a=findAnchor(); if(!a) return false;
    if(bar.parentNode!==a.parent || bar.nextSibling!==a.before) a.parent.insertBefore(bar,a.before||null);
    return true;
  }
  function setSource(dim,value){
    const s=byId(dim.id); if(!s) return false;
    const opt=[...s.options].find(o=>o.value===value || txt(o.textContent)===value);
    if(!opt) return false;
    s.value=opt.value; return true;
  }
  function resetDim(dim){
    const s=byId(dim.id); if(!s) return;
    const preferred=[...s.options].find(o=>dim.defaults.has(o.value)||dim.defaults.has(txt(o.textContent))) || s.options[0];
    if(preferred) s.value=preferred.value;
  }
  async function rerender(){
    if(busy) return; busy=true;
    try{
      if(mode()==='operativo'){
        try{ if(typeof OPER_PERIOD!=='undefined') OPER_PERIOD.value=byId('operPeriodSelect')?.value||''; }catch(e){}
        if(typeof renderOperativoView==='function') await renderOperativoView((typeof OP_VIEW!=='undefined'&&OP_VIEW)||'Centro Ejecutivo');
      }else if(mode()==='analysis'){
        const sec=byId('section')?.value||'Todas', store=byId('store')?.value||'Compañía';
        if(typeof loadDash==='function'){
          if(typeof SUB!=='undefined'&&SUB==='stores') await loadDash('Compañía',sec); else await loadDash(store,sec);
          if(typeof SUB!=='undefined'&&SUB==='sections'&&typeof loadCommercialDetail==='function') await loadCommercialDetail('rubro');
          if(typeof SUB!=='undefined'&&SUB==='areas'&&typeof loadCommercialDetail==='function') await loadCommercialDetail('area');
        }
      }
    }catch(e){ console.warn('[V99] drill render',e); }
    finally{ busy=false; setTimeout(refresh,60); }
  }
  async function selectDimension(dim, value){
    const dims=availableDims(), idx=dims.findIndex(d=>d.id===dim.id); if(idx<0) return;
    if(!setSource(dim,value)) return;
    for(let i=idx+1;i<dims.length;i++) resetDim(dims[i]);
    await rerender();
  }
  async function clearFrom(index){
    const dims=availableDims(); for(let i=index;i<dims.length;i++) resetDim(dims[i]); await rerender();
  }
  async function resetAll(){
    availableDims().forEach(resetDim); await rerender();
  }

  function renderBar(){
    if(!ensureBar()) return;
    const dims=availableDims();
    if(!dims.length){ bar.style.display='none'; return; }
    bar.style.display='grid';
    const selected=dims.map((d,i)=>({d,i,v:current(d)})).filter(x=>x.v);
    let nextIndex=0;
    while(nextIndex<dims.length && current(dims[nextIndex])) nextIndex++;
    const next=nextIndex<dims.length?dims[nextIndex]:null;
    let crumbs='';
    selected.forEach((x,n)=>{ if(n) crumbs+='<span class="v99-arrow">›</span>'; crumbs+=`<button type="button" class="v99-chip" data-clear="${x.i}" title="Quitar este nivel y los siguientes"><b>${esc(x.d.label)}:</b> ${esc(x.v)} ×</button>`; });
    if(!crumbs) crumbs='<span class="v99-drillhint">Sin desglose aplicado. Puedes iniciar desde la tabla o desde el selector.</span>';
    let nextHtml='';
    if(next){
      const opts=meaningful(next).map(o=>`<option value="${esc(o.value)}">${esc(o.text)}</option>`).join('');
      nextHtml=`<div class="v99-next"><div class="v99-nextfield"><label>Siguiente nivel · ${esc(next.label)}</label><select id="v99Next"><option value="">Selecciona ${esc(next.label.toLowerCase())}…</option>${opts}</select></div><button type="button" class="v99-reset" id="v99Reset">Restablecer</button></div>`;
    }else nextHtml='<div class="v99-next"><span class="v99-drillhint"><b>Detalle filtrado.</b> Haz clic en un nivel superior para cambiarlo.</span><button type="button" class="v99-reset" id="v99Reset">Restablecer</button></div>';
    bar.innerHTML=`<div class="v99-drilltop"><div><div class="v99-drilltitle">Desglose dentro del reporte</div><div class="v99-drillhint">Haz clic en una tienda o dimensión de la tabla para filtrar sin salir del reporte.</div></div></div><div class="v99-crumbs">${crumbs}</div>${nextHtml}`;
    bar.querySelectorAll('[data-clear]').forEach(b=>b.onclick=()=>clearFrom(Number(b.dataset.clear)));
    const n=byId('v99Next'); if(n&&next) n.onchange=()=>{ if(n.value) selectDimension(next,n.value); };
    const r=byId('v99Reset'); if(r) r.onclick=resetAll;
  }

  function markClickable(){
    const dims=availableDims(); if(!dims.length) return;
    const lookups=dims.map(d=>({d,map:new Map(meaningful(d).map(o=>[o.text.toLocaleLowerCase('es-MX'),o.value]))}));
    document.querySelectorAll('#app table td, #app table th, main table td, main table th').forEach(cell=>{
      cell.classList.remove('v99-clickable'); delete cell.dataset.v99Dim; delete cell.dataset.v99Value;
      const val=txt(cell.textContent).replace(/\s+/g,' ').toLocaleLowerCase('es-MX'); if(!val) return;
      const hit=lookups.find(x=>x.map.has(val)); if(!hit) return;
      cell.classList.add('v99-clickable'); cell.dataset.v99Dim=hit.d.id; cell.dataset.v99Value=hit.map.get(val);
      cell.title=`Filtrar por ${hit.d.label}: ${txt(cell.textContent)}`;
    });
  }
  function refresh(){
    clearTimeout(timer); timer=setTimeout(()=>{ try{renderBar();markClickable();}catch(e){console.warn('[V99] refresh',e)} },20);
  }

  document.addEventListener('click',e=>{
    const cell=e.target.closest('.v99-clickable'); if(cell && !busy){
      const dim=availableDims().find(d=>d.id===cell.dataset.v99Dim); if(dim){ e.preventDefault(); e.stopPropagation(); selectDimension(dim,cell.dataset.v99Value); return; }
    }
    if(e.target.closest('[data-main],[data-opview],[data-sub],#refresh,#operPeriodApply')) setTimeout(refresh,80);
  },true);
  document.addEventListener('change',e=>{
    if(e.target.matches('#operStoreSelect,#operAreaSelect,#operActivitySelect,#store,#section,#catalog,#week,#operPeriodSelect')) setTimeout(refresh,50);
  },true);

  const start=()=>{
    const host=byId('app')||document.body;
    observer=new MutationObserver(()=>refresh()); observer.observe(host,{childList:true,subtree:true});
    refresh();
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start); else start();
})();
</script>
'''

    @module.app.middleware("http")
    async def _v99_inline_table_drilldown(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v99-inline-drill-js" not in html:
                html = html.replace("</head>", css + "</head>", 1)
                html = html.replace("</body>", script + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache", "Expires":"0"
            })
        except Exception as exc:
            print(f"[V99] UI warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    module._V99_INLINE_TABLE_DRILLDOWN = True
    print("[V99] Desglose contextual dentro de tablas activo.", flush=True)
