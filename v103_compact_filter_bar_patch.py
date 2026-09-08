"""V103: barra compacta sticky + chips + Más filtros + drill-down.

La V102 queda disponible como respaldo. V103 conserva los selectores y APIs
existentes como fuente de verdad; únicamente cambia la forma de interactuar con
ellos. El usuario puede volver a la vista clásica desde la propia barra.

Diseño:
- barra compacta sticky dentro del reporte;
- chips para filtros activos, removibles con un clic;
- panel desplegable "Más filtros" con todos los filtros del contexto;
- modo "Desglose" para filtrar haciendo clic en valores de las tablas;
- restablecer sin tocar datos, cálculos, permisos ni PDF.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V103_COMPACT_FILTER_BAR", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v103-filter-css">
#v102FilterMode,#v102Drill,#ctxPanel,#ctxLauncher,#v99Drillbar,#v100FilterSwitch,#v101FilterSwitch,#v101DrillBar{display:none!important}
#v103FilterShell{position:sticky;top:8px;z-index:45;margin:9px 0 12px}
#v103CompactBar{min-height:46px;padding:7px 9px;border:1px solid #cfdceb;border-radius:12px;background:rgba(255,255,255,.97);backdrop-filter:blur(8px);box-shadow:0 5px 18px rgba(15,23,42,.09);display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.v103-title{font-size:7.5px;font-weight:950;color:#64748b;text-transform:uppercase;letter-spacing:.4px;margin-right:2px;white-space:nowrap}
.v103-chiprow{display:flex;align-items:center;gap:5px;flex:1;min-width:160px;overflow-x:auto;scrollbar-width:thin;padding:1px 0}
.v103-chip{border:1px solid #bfd0e5;background:#f7faff;color:#123b73;border-radius:999px;padding:5px 8px;font-size:8px;font-weight:850;white-space:nowrap;cursor:pointer;display:inline-flex;gap:5px;align-items:center}
.v103-chip b{font-weight:950}.v103-chip .x{color:#7c8da3;font-size:10px;line-height:1}.v103-empty{font-size:8px;color:#8793a5;white-space:nowrap}
.v103-actions{display:flex;align-items:center;gap:5px;margin-left:auto}
.v103-btn{border:1px solid #cbd8e8;background:#fff;color:#123b73;border-radius:8px;min-height:32px;padding:6px 9px;font-size:8px;font-weight:900;cursor:pointer;white-space:nowrap}
.v103-btn:hover{background:#f2f7fd}.v103-btn.primary{background:#1769e8;border-color:#1769e8;color:#fff}.v103-btn.active{background:#eaf2ff;border-color:#9fc3f6;color:#1769e8}.v103-version{font-size:7px;font-weight:950;color:#1769e8;background:#f4f8ff;border:1px solid #bdd5fb;border-radius:999px;padding:4px 6px}
#v103More{display:none;margin-top:5px;padding:10px;border:1px solid #d4dfec;border-radius:12px;background:#fff;box-shadow:0 9px 28px rgba(15,23,42,.12)}#v103More.open{display:block}
.v103-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:8px}.v103-field label{display:block;margin:0 0 4px;font-size:7px;font-weight:950;color:#748196;text-transform:uppercase;letter-spacing:.35px}.v103-field select,.v103-field input{width:100%;min-height:35px;border:1px solid #cbd9e6;border-radius:8px;background:#fff;color:#123b73;padding:6px 8px;font-size:9px;font-weight:800}
.v103-morefoot{display:flex;justify-content:flex-end;gap:6px;margin-top:9px;padding-top:8px;border-top:1px solid #edf1f5}
.v103-clickable{cursor:pointer!important}.v103-clickable:hover{background:#eef6ff!important;box-shadow:inset 0 0 0 1px #b8d7ff}.v103-clickable:after{content:' ›';color:#1769e8;font-weight:950}
body.v103-classic #v103FilterShell{display:none!important}body.v103-classic .v103-clickable:after{display:none!important}body.v103-classic .v103-clickable{cursor:default!important}
body.v103-compact .filters{display:none!important}
body.v103-drill .filters{display:none!important}
#v103ClassicBack{display:none;margin:7px 0 0;border:1px solid #cbd8e8;background:#fff;color:#123b73;border-radius:8px;padding:6px 9px;font-size:8px;font-weight:900;cursor:pointer}
body.v103-classic #v103ClassicBack{display:inline-flex}
@media(max-width:900px){#v103FilterShell{top:5px}.v103-title{display:none}.v103-actions{width:100%;margin-left:0}.v103-actions .v103-btn{flex:1}.v103-version{display:none}.v103-chiprow{order:2;width:100%}.v103-grid{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.v103-grid{grid-template-columns:1fr}}
</style>
'''

    bar = '''<div id="v103FilterShell" data-ui-version="V103"><div id="v103CompactBar"><span class="v103-title">Filtros</span><div class="v103-chiprow" id="v103Chips"></div><div class="v103-actions"><button class="v103-btn" id="v103MoreBtn" type="button">Más filtros ▾</button><button class="v103-btn" id="v103DrillBtn" type="button">Desglose interactivo</button><button class="v103-btn" id="v103ClassicBtn" type="button">Vista clásica</button><span class="v103-version">V103</span></div></div><div id="v103More"><div class="v103-grid" id="v103MoreGrid"></div><div class="v103-morefoot"><button class="v103-btn" id="v103Reset" type="button">Restablecer</button><button class="v103-btn primary" id="v103Apply" type="button">Aplicar</button></div></div></div><button id="v103ClassicBack" type="button">Usar barra compacta</button>'''

    js = r'''
<script id="v103-filter-js">
(function(){
  const MODE_KEY='operacionesRopaFilterModeV103';
  const byId=id=>document.getElementById(id), txt=v=>String(v==null?'':v).trim();
  const generic=new Set(['','Compañía','Compania','Todas','Todos','Todas las tiendas','Todos los rubros','Todo']);
  let timer=null,busy=false;
  const mode=()=>{try{return localStorage.getItem(MODE_KEY)||'compact'}catch(e){return'compact'}};
  function setSavedMode(m){try{localStorage.setItem(MODE_KEY,m)}catch(e){}}
  function context(){
    if(byId('operStoreSelect')) return 'operations';
    if(byId('store')) return 'commercial';
    return '';
  }
  function defs(){
    if(context()==='operations') return [
      {label:'Periodo',id:'operPeriodSelect',kind:'period',defaults:new Set([''])},
      {label:'Tienda',id:'operStoreSelect',defaults:new Set(['','Compañía','Compania'])},
      {label:'Área',id:'operAreaSelect',defaults:new Set(['','Todas','Todos'])},
      {label:'Actividad',id:'operActivitySelect',defaults:new Set(['','Todas','Todos'])}
    ];
    if(context()==='commercial') return [
      {label:'Periodo',id:'week',kind:'period',defaults:new Set([''])},
      {label:'Tienda',id:'store',defaults:new Set(['','Compañía','Compania'])},
      {label:'Sección',id:'section',defaults:new Set(['','Todas','Todos'])},
      {label:'Tipo catálogo',id:'catalog',defaults:new Set(['','Todas','Todos'])}
    ];
    return [];
  }
  function detailDefs(){return defs().filter(d=>d.kind!=='period')}
  function display(d){const s=byId(d.id);if(!s)return'';return txt(s.options?.[s.selectedIndex]?.textContent||s.value)}
  function active(d){const s=byId(d.id);if(!s)return false;const t=display(d);if(d.kind==='period')return !!t;return !(d.defaults?.has(s.value)||d.defaults?.has(t)||generic.has(t))}
  function resetOne(d){const s=byId(d.id);if(!s)return;let o=null;if(d.kind==='period')return;o=[...s.options].find(x=>d.defaults?.has(x.value)||d.defaults?.has(txt(x.textContent)))||s.options[0];if(o)s.value=o.value}
  async function rerender(){
    if(busy)return;busy=true;
    try{
      if(context()==='operations'){
        const b=byId('operPeriodApply');if(b)b.click();else if(typeof renderOperativoView==='function')await renderOperativoView((typeof OP_VIEW!=='undefined'&&OP_VIEW)||'Centro Ejecutivo');
      }else if(context()==='commercial'){
        const b=byId('refresh');if(b)b.click();else if(typeof loadDash==='function'){const sec=byId('section')?.value||'Todas',st=byId('store')?.value||'Compañía';await loadDash(st,sec)}
      }
    }catch(e){console.warn('[V103] rerender',e)}finally{busy=false;setTimeout(refresh,120)}
  }
  function setMode(m){
    if(!['classic','compact','drill'].includes(m))m='compact';setSavedMode(m);
    document.body.classList.toggle('v103-classic',m==='classic');document.body.classList.toggle('v103-compact',m==='compact');document.body.classList.toggle('v103-drill',m==='drill');
    byId('v103DrillBtn')?.classList.toggle('active',m==='drill');mark();renderChips();
  }
  function renderChips(){
    const host=byId('v103Chips');if(!host)return;const aa=defs().filter(active);
    if(!aa.length){host.innerHTML='<span class="v103-empty">Sin filtros adicionales · vista Compañía</span>';return}
    host.innerHTML=aa.map(d=>`<button type="button" class="v103-chip" data-clear-id="${d.id}"><b>${d.label}:</b> ${display(d)} ${d.kind==='period'?'':'<span class="x">×</span>'}</button>`).join('');
    host.querySelectorAll('[data-clear-id]').forEach(b=>b.onclick=async()=>{const d=defs().find(x=>x.id===b.dataset.clearId);if(!d||d.kind==='period')return;resetOne(d);const list=detailDefs(),idx=list.findIndex(x=>x.id===d.id);for(let i=idx+1;i<list.length;i++)resetOne(list[i]);await rerender()});
  }
  function renderMore(){
    const grid=byId('v103MoreGrid');if(!grid)return;grid.innerHTML='';
    defs().forEach(d=>{const src=byId(d.id);if(!src)return;const w=document.createElement('div');w.className='v103-field';const lab=document.createElement('label');lab.textContent=d.label;const clone=src.cloneNode(true);clone.removeAttribute('id');clone.dataset.source=d.id;clone.value=src.value;w.append(lab,clone);grid.appendChild(w)});
  }
  function applyMoreValues(){byId('v103MoreGrid')?.querySelectorAll('[data-source]').forEach(cl=>{const src=byId(cl.dataset.source);if(src)src.value=cl.value})}
  async function resetAll(){detailDefs().forEach(resetOne);renderMore();await rerender()}
  function tableCells(){return [...document.querySelectorAll('table td')].filter(c=>!c.closest('#ctxPanel'))}
  function mark(){
    document.querySelectorAll('.v103-clickable').forEach(c=>{c.classList.remove('v103-clickable');delete c.dataset.v103Id;delete c.dataset.v103Val});if(mode()!=='drill')return;
    const maps=detailDefs().map(d=>{const s=byId(d.id),m=new Map();if(s)for(const o of [...s.options]){const t=txt(o.textContent);if(t&&!generic.has(t)&&!(d.defaults?.has(t)||d.defaults?.has(o.value)))m.set(t.toLocaleLowerCase('es-MX'),o.value)}return{d,m}});
    tableCells().forEach(c=>{const raw=txt(c.textContent).replace(/\s+Proyecto\s*$/i,'').trim(),key=raw.toLocaleLowerCase('es-MX'),hit=maps.find(x=>x.m.has(key));if(hit){c.classList.add('v103-clickable');c.dataset.v103Id=hit.d.id;c.dataset.v103Val=hit.m.get(key);c.title=`Filtrar por ${hit.d.label}: ${raw}`}})
  }
  async function drillChoose(id,val){
    const list=detailDefs(),idx=list.findIndex(d=>d.id===id);if(idx<0)return;const d=list[idx],s=byId(id);if(!s)return;const o=[...s.options].find(x=>x.value===val);if(!o)return;s.value=o.value;for(let i=idx+1;i<list.length;i++)resetOne(list[i]);await rerender();
  }
  function bind(){
    byId('v103MoreBtn')?.addEventListener('click',()=>{const p=byId('v103More');p?.classList.toggle('open');if(p?.classList.contains('open'))renderMore()});
    byId('v103DrillBtn')?.addEventListener('click',()=>setMode(mode()==='drill'?'compact':'drill'));
    byId('v103ClassicBtn')?.addEventListener('click',()=>setMode('classic'));
    byId('v103ClassicBack')?.addEventListener('click',()=>setMode('compact'));
    byId('v103Reset')?.addEventListener('click',resetAll);
    byId('v103Apply')?.addEventListener('click',async()=>{applyMoreValues();byId('v103More')?.classList.remove('open');await rerender()});
  }
  function refresh(){clearTimeout(timer);timer=setTimeout(()=>{setMode(mode());renderChips();if(byId('v103More')?.classList.contains('open'))renderMore();mark()},60)}
  document.addEventListener('click',e=>{const c=e.target.closest('.v103-clickable');if(c&&mode()==='drill'){e.preventDefault();e.stopPropagation();drillChoose(c.dataset.v103Id,c.dataset.v103Val);return}if(e.target.closest('[data-main],[data-opview],[data-sub],#operPeriodApply,#refresh'))setTimeout(refresh,120)},true);
  document.addEventListener('change',e=>{if(defs().some(d=>d.id===e.target.id))setTimeout(refresh,70)},true);
  const start=()=>{bind();setMode(mode());const host=byId('app')||document.querySelector('main')||document.body;new MutationObserver(()=>refresh()).observe(host,{childList:true,subtree:true});refresh()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''

    @module.app.middleware("http")
    async def _v103_compact_filter_bar(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v103-filter-js" not in html:
                html=html.replace("</head>",css+"</head>",1)
                marker='<div id="operativoNav"'
                pos=html.find(marker)
                if pos>=0:
                    html=html[:pos]+bar+html[pos:]
                else:
                    html=html.replace('<main class="main">','<main class="main">'+bar,1)
                html=html.replace("</body>",js+"</body>",1)
            html=html.replace("V93 · HTML", "V103 · barra compacta")
            html=html.replace("V102", "V103") if 'data-ui-version="V102"' in html else html
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0","X-Operaciones-Ropa-UI":"V103"
            })
        except Exception as exc:
            print(f"[V103] UI warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    module._V103_COMPACT_FILTER_BAR=True
    print("[V103] Barra sticky + chips + Más filtros + desglose interactivo activa.",flush=True)
