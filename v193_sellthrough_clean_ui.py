"""V193 · Sell Through recreado desde cero.

No reutiliza la página ni listeners de Sell Through anteriores. La UI consume
exclusivamente /api/commercial-sellthrough-v2, cuyo inventario sale directo del
XLSX físico (RAW-V2). Así evitamos que capas legacy sobrescriban los valores.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V193_SELLTHROUGH_CLEAN_UI", False):
        return

    css=r'''
<style id="v193-sellthrough-clean-css">
#page-sellthrough-clean{display:none}
#page-sellthrough-clean.active{display:block}
.v193-st-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:12px 0 18px}
.v193-st-kpi{background:#fff;border:1px solid #d8e0eb;border-radius:16px;padding:16px;min-height:126px}
.v193-st-kpi .lab{font-size:12px;font-weight:900;color:#5d6f87;text-transform:uppercase}
.v193-st-kpi .val{font-size:30px;font-weight:950;color:#0b447f;margin-top:8px}
.v193-st-kpi .note{font-size:12px;color:#75849a;margin-top:5px;line-height:1.35}
.v193-st-source{background:#eef7ff;border:1px solid #c7e1fb;border-radius:12px;padding:10px 12px;margin:8px 0 14px;font-size:12px;color:#174a7d}
.v193-st-filters{display:flex;justify-content:flex-end;gap:8px;margin:8px 0}
.v193-st-filters button{border:1px solid #cad8e8;background:#fff;border-radius:10px;padding:9px 14px;font-weight:900;color:#0b447f}
.v193-st-filters button.active{background:#1f73e8;color:#fff;border-color:#1f73e8}
.v193-st-tablewrap{max-height:67vh;overflow:auto;border:1px solid #d8e0eb;border-radius:12px;background:#fff}
#v193StTable{min-width:1450px;width:100%;border-collapse:separate;border-spacing:0}
#v193StTable th{position:sticky;top:0;z-index:10;background:#17477f;color:#fff;padding:12px 10px;white-space:nowrap;text-align:left}
#v193StTable td{padding:11px 10px;border-bottom:1px solid #e6ebf2;white-space:nowrap}
#v193StTable tr:nth-child(even) td{background:#f8fafc}
.v193-pill{display:inline-block;border-radius:999px;padding:5px 9px;background:#eef2f7;font-weight:900}
.v193-pill.good{background:#e2f7e8;color:#087d34}.v193-pill.mid{background:#fff3cd;color:#805d00}
@media(max-width:900px){
  .v193-st-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .v193-st-kpi{min-height:108px;padding:12px}
  .v193-st-kpi .val{font-size:23px}
  .v193-st-tablewrap{max-height:62vh}
}
</style>
'''

    js=r'''
<script id="v193-sellthrough-clean-js">
(()=>{
  const q=s=>document.querySelector(s),qa=s=>Array.from(document.querySelectorAll(s));
  let busy=false,last=null,band='all';

  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const p1=v=>Number(v||0).toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';

  function hideLegacy(){
    qa('#analysisNav [data-sub="sellthrough"]').forEach(x=>x.style.display='none');
    const old=q('#page-sellthrough');if(old)old.style.display='none';
  }

  function ensure(){
    hideLegacy();
    const nav=q('#analysisNav');
    if(nav&&!q('#v193SellBtn')){
      const b=document.createElement('button');
      b.id='v193SellBtn';b.className='switch';b.dataset.sub='sellthrough-clean';b.dataset.tabKey='commercial.sellthrough';
      b.innerHTML='<span style="font-size:20px">%</span> Sell Through';
      const more=nav.querySelector('[data-sub="more"]');
      nav.insertBefore(b,more||null);
    }
    if(!q('#page-sellthrough-clean')){
      const page=document.createElement('section');
      page.className='page';page.id='page-sellthrough-clean';
      page.innerHTML=`
        <div class="title">Sell Through</div>
        <div class="subtitle">Reporte reconstruido desde el Excel fuente de capacidades + ventas acumuladas de Cambios y Muertos.</div>
        <div class="v193-st-kpis" id="v193StKpis"></div>
        <div class="v193-st-source" id="v193StSource">Preparando fuente…</div>
        <div style="display:flex;align-items:end;justify-content:space-between;gap:10px;flex-wrap:wrap">
          <div>
            <div class="title" style="margin:0">Ranking de modelos</div>
            <div class="subtitle" id="v193StContext"></div>
          </div>
          <div class="v193-st-filters">
            <button class="active" data-v193-band="all">Todos</button>
            <button data-v193-band="over80">≥ 80%</button>
            <button data-v193-band="mid">50–79%</button>
            <button data-v193-band="low">&lt; 50%</button>
          </div>
        </div>
        <div class="v193-st-source" id="v193StFormula"></div>
        <div class="v193-st-tablewrap">
          <table id="v193StTable">
            <thead><tr>
              <th>#</th><th>% Sell Through</th><th>ID_ART</th><th>Modelo</th><th>Marca</th><th>Sección</th><th>Rubro</th>
              <th>Vta acum pzs</th><th>Existencia</th><th>Existencia CEDIS</th><th>Tránsito</th>
              <th>Stock disponible</th><th>Base ST</th><th>Sugerido 7</th>
            </tr></thead>
            <tbody id="v193StRows"><tr><td colspan="14">Selecciona Sell Through para consultar.</td></tr></tbody>
          </table>
        </div>`;
      const anchor=q('#page-more')||q('#page-analysis-upload')||q('#appView');
      if(anchor?.parentNode)anchor.parentNode.insertBefore(page,anchor);else document.body.appendChild(page);
      qa('[data-v193-band]').forEach(btn=>btn.addEventListener('click',()=>{
        band=btn.dataset.v193Band||'all';
        qa('[data-v193-band]').forEach(x=>x.classList.toggle('active',x===btn));
        renderRows();
      }));
    }
  }

  function inBand(r){
    const x=Number(r.sell_through||0);
    if(band==='over80')return x>=80;
    if(band==='mid')return x>=50&&x<80;
    if(band==='low')return x<50;
    return true;
  }
  function pill(x){
    x=Number(x||0);const cls=x>=80?'good':x>=50?'mid':'';
    return '<span class="v193-pill '+cls+'">'+p1(x)+'</span>';
  }
  function renderRows(){
    const body=q('#v193StRows');if(!body||!last)return;
    const rows=(last.rows||[]).filter(inBand);
    body.innerHTML=rows.map((r,i)=>`<tr>
      <td><b>#${i+1}</b></td><td>${pill(r.sell_through)}</td><td>${esc(r.id_art)}</td><td><b>${esc(r.model)}</b></td>
      <td>${esc(r.brand)}</td><td>${esc(r.section)}</td><td>${esc(r.rubro)}</td>
      <td>${nf(r.sales_pzas)}</td><td>${nf(r.existence)}</td><td>${nf(r.cedis_existence)}</td><td>${nf(r.transit)}</td>
      <td>${nf(r.stock_available)}</td><td>${nf(r.available_base)}</td><td>${Number(r.suggested||0).toLocaleString('es-MX',{maximumFractionDigits:2})}</td>
    </tr>`).join('')||'<tr><td colspan="14">Sin modelos para este rango.</td></tr>';
  }
  function render(d){
    last=d;const t=d.totals||{};
    const over80=t.models_ge_80??t.over80??0;
    q('#v193StKpis').innerHTML=
      '<div class="v193-st-kpi"><div class="lab">Sell Through general</div><div class="val">'+p1(t.sell_through)+'</div><div class="note">'+(d.cedis_in_sellthrough?'incluye CEDIS':'CEDIS informativo')+'</div></div>'+
      '<div class="v193-st-kpi"><div class="lab">Vta acum pzs</div><div class="val">'+nf(t.sales_pzas)+'</div><div class="note">'+esc(d.sales_scope||'Acumulado')+'</div></div>'+
      '<div class="v193-st-kpi"><div class="lab">Existencia</div><div class="val">'+nf(t.existence)+'</div><div class="note">leída directo del XLSX</div></div>'+
      '<div class="v193-st-kpi"><div class="lab">Existencia CEDIS</div><div class="val">'+nf(t.cedis_existence)+'</div><div class="note">'+(d.cedis_in_sellthrough?'incluida en Compañía':'no entra por tienda')+'</div></div>'+
      '<div class="v193-st-kpi"><div class="lab">Stock disponible</div><div class="val">'+nf(t.stock_available)+'</div><div class="note">Existencia + Tránsito'+(d.cedis_in_sellthrough?' + CEDIS':'')+'</div></div>'+
      '<div class="v193-st-kpi"><div class="lab">Modelos ≥ 80%</div><div class="val">'+nf(over80)+'</div><div class="note">de '+nf(t.models)+' modelos</div></div>';
    q('#v193StSource').textContent='Fuente inventario: '+(d.source_file||'sin identificar')+' · Motor: '+(d.engine||'RAW-V2')+' · Fuente ventas: Base de muertos y cambios.';
    q('#v193StContext').textContent=(d.store||'Compañía')+' · '+(d.section||'Todas')+' · '+(d.status||'VIGENTE');
    q('#v193StFormula').textContent='Sell Through = Vta acum pzs / (Vta acum pzs + Stock disponible). Stock disponible = Existencia + Tránsito'+(d.cedis_in_sellthrough?' + Existencia CEDIS':'')+'.';
    renderRows();
  }

  async function load(){
    if(busy)return;busy=true;ensure();
    const body=q('#v193StRows');if(body)body.innerHTML='<tr><td colspan="14">Cargando Sell Through RAW…</td></tr>';
    try{
      const week=q('#week')?.value||'',store=q('#store')?.value||'Compañía',section=q('#section')?.value||'Todas';
      const res=await fetch('/api/commercial-sellthrough-v2?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store)+'&section='+encodeURIComponent(section)+'&catalog=Todos&_v=193',{credentials:'same-origin',cache:'no-store'});
      const txt=await res.text();let d={};try{d=txt?JSON.parse(txt):{}}catch(_){}
      if(!res.ok)throw new Error(d.detail||('Error HTTP '+res.status));
      render(d);
    }catch(e){
      if(body)body.innerHTML='<tr><td colspan="14">No fue posible cargar Sell Through: '+esc(e.message||e)+'</td></tr>';
    }finally{busy=false}
  }

  function open(){
    ensure();hideLegacy();
    qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-sellthrough-clean'));
    qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('active',x.dataset.sub==='sellthrough-clean'));
    const cf=q('.commercialFilter');if(cf)cf.style.display='block';
    const ht=q('#heroTitle'),hs=q('#heroSub');
    if(ht)ht.textContent='Análisis Comercial';
    if(hs)hs.textContent='Sell Through · reconstruido desde fuente RAW';
    load();
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('#v193SellBtn,[data-sub="sellthrough-clean"]');
    if(!b)return;
    e.preventDefault();e.stopImmediatePropagation();open();
  },true);
  document.addEventListener('change',e=>{
    if(e.target.matches?.('#week,#store,#section')&&q('#page-sellthrough-clean.active'))load();
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensure,{once:true});else ensure();
  setTimeout(ensure,250);setTimeout(ensure,1200);
  window.loadSellThroughCleanV193=load;
  console.info('[V193] Sell Through recreado desde cero y aislado de listeners legacy.');
})();
</script>
'''

    @m.app.middleware("http")
    async def v193_sellthrough_clean_html(request, call_next):
        response=await call_next(request)
        if request.url.path=="/" and response.headers.get("content-type","").startswith("text/html"):
            body=b""
            async for chunk in response.body_iterator: body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v193-sellthrough-clean-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v193-sellthrough-clean-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(response.headers);headers.pop("content-length",None)
            headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-SellThrough"]="V193-CLEAN"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        return response

    m._V193_SELLTHROUGH_CLEAN_UI=True
    print("[V193] Sell Through CLEAN instalado sobre endpoint RAW-V2.",flush=True)
