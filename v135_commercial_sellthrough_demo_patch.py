"""V135 · Pestaña Sell Through para el demo Comercial.

Agrega al demo compacto una séptima pestaña Sell Through alineada al boceto
aprobado. Es sólo visual para el propietario: usa datos ficticios, respeta los
filtros del demo y no escribe ni modifica información real.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V135_COMMERCIAL_SELLTHROUGH_DEMO", False):
        return

    css = r'''<style id="v135-sellthrough-css">
.v135-st-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:6px}
.v135-st-kpi{border:1px solid #dfe7f0;border-radius:6px;padding:5px;background:#fff;display:grid;grid-template-columns:22px minmax(0,1fr);gap:4px;align-items:center;min-width:0;min-height:50px}
.v135-st-kpi.good{background:#effbf4;border-color:#c8ead6}.v135-st-kpi.warn{background:#fff9e9;border-color:#f3e0a8}.v135-st-kpi.purple{background:#f7f3ff;border-color:#ded2ff}
.v135-st-icon{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;background:#edf5ff;color:#1769e8;font-size:11px;font-weight:950}.v135-st-kpi.good .v135-st-icon{background:#e3f8eb;color:#13834a}.v135-st-kpi.warn .v135-st-icon{background:#fff1c8;color:#a36d00}.v135-st-kpi.purple .v135-st-icon{background:#efe8ff;color:#6030cb}
.v135-st-kpi small{display:block;font-size:4.8px;color:#64748b;font-weight:900;line-height:1.1}.v135-st-kpi b{display:block;font-size:9.2px;color:#103d7c;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.v135-st-kpi.good b{color:#168447}.v135-st-kpi.warn b{color:#a36d00}.v135-st-kpi.purple b{color:#6030cb}.v135-st-kpi em{display:block;font-size:4.2px;color:#8290a2;font-style:normal}
.v135-st-tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:5px;border:1px solid #e3eaf2;border-radius:6px;background:#fff}
.v135-st-table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:4.6px;min-width:100%}.v135-st-table th{background:#f1f6fb;color:#53657e;text-align:left;padding:4px 3px;border-bottom:1px solid #dfe7f0;line-height:1.1;font-weight:950}.v135-st-table td{padding:4px 3px;border-bottom:1px solid #e8edf3;color:#153f79;line-height:1.1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.v135-st-table tr:nth-child(even) td{background:#fafcff}.v135-st-table tr:last-child td{border-bottom:0}
.v135-st-pct{display:inline-block;min-width:30px;text-align:center;padding:2px 3px;border-radius:999px;background:#e7f8ed;color:#128447;font-weight:950}.v135-st-pct.mid{background:#fff3d6;color:#9a6a00}.v135-st-pct.low{background:#f1f4f8;color:#5d6f85}
.v135-st-foot{display:flex;align-items:center;gap:4px;margin-top:5px;color:#61758e;font-size:4.8px}.v135-st-foot .i{width:13px;height:13px;border-radius:50%;display:grid;place-items:center;background:#e9f2ff;color:#1769e8;font-size:7px;font-weight:950}
@media(max-width:430px){.v135-st-kpis{grid-template-columns:repeat(4,minmax(0,1fr));gap:3px}.v135-st-kpi{grid-template-columns:18px minmax(0,1fr);gap:2px;padding:4px;min-height:44px}.v135-st-icon{width:18px;height:18px;font-size:9px}.v135-st-kpi b{font-size:7.3px}.v135-st-kpi small{font-size:4.1px}.v135-st-kpi em{font-size:3.8px}.v135-st-table{font-size:4.1px}.v135-st-table th,.v135-st-table td{padding:3px 2px}}
</style>'''

    js = r'''<script id="v135-sellthrough-js">
(function(){
  let stActive=false;
  const baseRows=[
    {pct:92.4,id:'MD1023',model:'Vestido Floral',color:'Rosa',exist:28,sug:320,price:420},
    {pct:89.7,id:'MD0876',model:'Blusa Básica',color:'Blanco',exist:42,sug:410,price:280},
    {pct:85.1,id:'MD0543',model:'Pantalón Wide',color:'Azul',exist:36,sug:380,price:350},
    {pct:78.6,id:'MD0982',model:'Falda Midi',color:'Beige',exist:52,sug:510,price:460},
    {pct:76.3,id:'MD0631',model:'Playera Estampada',color:'Negro',exist:25,sug:260,price:380},
    {pct:71.9,id:'MD0715',model:'Jeans Skinny',color:'Azul',exist:68,sug:620,price:220},
    {pct:66.4,id:'MD0934',model:'Sudadera',color:'Gris',exist:48,sug:580,price:400},
    {pct:58.7,id:'MD1102',model:'Chamarra Ligera',color:'Verde',exist:62,sug:720,price:310},
    {pct:52.1,id:'MD1201',model:'Blusa Satinada',color:'Blanco',exist:46,sug:690,price:480},
    {pct:47.3,id:'MD0664',model:'Pantalón Recto',color:'Negro',exist:38,sug:810,price:500}
  ];
  const H=()=>document.getElementById('v133CommercialDemoHost');
  const C=()=>document.getElementById('v133Content');
  const fmt=n=>Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const money=n=>'$'+fmt(n);
  function values(){const h=H();return{period:h?.querySelector('#v133Period')?.value||'Sep 2026',store:h?.querySelector('#v133Store')?.value||'Compañía',section:h?.querySelector('#v133Section')?.value||'Todas'}}
  function factor(v){const pf={'Sep 2026':1,'Ago 2026':.94,'Jul 2026':.88}[v.period]||1;const sf={'Compañía':1,'Iztapalapa':1,'Vallejo':.97,'Ecatepec':.80,'Querétaro':.79,'Puebla':.66,'León':.61}[v.store]||1;const q={'Todas':1,'Dama':.47,'Caballero':.35,'Infantil':.18,'Lencería':.10}[v.section]||1;return pf*sf*q}
  function ensureTab(){const h=H();const tabs=h?.querySelector('.v133-tabs');if(!tabs)return;let b=tabs.querySelector('[data-v135-sellthrough]');if(!b){b=document.createElement('button');b.type='button';b.className='v133-tab';b.dataset.v135Sellthrough='1';b.textContent='Sell Through';tabs.appendChild(b)}}
  function activateTabStyle(){const h=H();h?.querySelectorAll('.v133-tab').forEach(x=>x.classList.remove('active'));h?.querySelector('[data-v135-sellthrough]')?.classList.add('active')}
  function pctClass(p){return p>=80?'':p>=50?'mid':'low'}
  function render(){const c=C();if(!c)return;const v=values(),f=factor(v);const rows=baseRows.map(r=>({...r,exist:Math.max(1,Math.round(r.exist*f)),sug:Math.max(1,Math.round(r.sug*f)),pct:Math.max(0,Math.min(99.9,r.pct+(f-1)*4))})).sort((a,b)=>b.pct-a.pct);const avg=rows.reduce((a,r)=>a+r.pct,0)/rows.length;const gt80=rows.filter(r=>r.pct>=80).length;const mid=rows.filter(r=>r.pct>=50&&r.pct<80).length;const inv=rows.reduce((a,r)=>a+r.exist*r.price,0);
    const tableRows=rows.map(r=>`<tr><td><span class="v135-st-pct ${pctClass(r.pct)}">${r.pct.toFixed(1)}%</span></td><td><b>${r.id}</b></td><td>${r.model}</td><td>${r.color}</td><td>${fmt(r.exist)}</td><td>${fmt(r.sug)}</td><td>${money(r.price)}</td><td><b>${money(r.exist*r.price)}</b></td></tr>`).join('');
    c.innerHTML=`<div class="v133-filter-summary"><span class="v133-filter-chip">${v.period}</span><span class="v133-filter-chip">${v.store}</span><span class="v133-filter-chip">${v.section}</span></div>
      <div class="v133-panel"><div class="v133-head"><div><div class="v133-title">Sell Through · ${v.period}</div><div class="v133-sub">Modelos ordenados de mayor a menor % Sell Through</div></div></div>
        <div class="v135-st-kpis">
          <div class="v135-st-kpi"><div class="v135-st-icon">%</div><div><small>Sell Through promedio</small><b>${avg.toFixed(1)}%</b><em>sobre sugerido</em></div></div>
          <div class="v135-st-kpi good"><div class="v135-st-icon">▥</div><div><small>Modelos &gt;80%</small><b>${gt80}</b><em>de ${rows.length} modelos</em></div></div>
          <div class="v135-st-kpi warn"><div class="v135-st-icon">◕</div><div><small>Modelos 50–79%</small><b>${mid}</b><em>${(mid/rows.length*100).toFixed(1)}%</em></div></div>
          <div class="v135-st-kpi purple"><div class="v135-st-icon">$</div><div><small>Inversión total</small><b>${money(inv)}</b><em>MXN</em></div></div>
        </div>
      </div>
      <div class="v133-panel"><div class="v133-head"><div><div class="v133-title">Ranking de modelos por Sell Through</div><div class="v133-sub">Mayor a menor porcentaje</div></div><span class="v133-link">Ver todos</span></div>
        <div class="v135-st-tablewrap"><table class="v135-st-table"><colgroup><col style="width:12%"><col style="width:11%"><col style="width:20%"><col style="width:11%"><col style="width:10%"><col style="width:10%"><col style="width:13%"><col style="width:13%"></colgroup><thead><tr><th>% Sell Through</th><th>ID</th><th>Modelo</th><th>Color</th><th>Existencia</th><th>Sugerido</th><th>Precio mayoreo</th><th>Inversión</th></tr></thead><tbody>${tableRows}</tbody></table></div>
        <div class="v135-st-foot"><span class="i">i</span><span>Inversión = Precio mayoreo × piezas en existencia</span></div>
      </div>`;
    activateTabStyle();
  }
  function enter(e){e?.preventDefault?.();e?.stopImmediatePropagation?.();stActive=true;render()}
  function leave(){stActive=false}
  document.addEventListener('click',e=>{const sell=e.target.closest?.('[data-v135-sellthrough]');if(sell){enter(e);return}const old=e.target.closest?.('[data-v133-tab]');if(old){leave();return}if(stActive&&e.target.closest?.('#v133Query')){e.preventDefault();e.stopImmediatePropagation();setTimeout(render,0)}},true);
  document.addEventListener('touchend',e=>{const sell=e.target.closest?.('[data-v135-sellthrough]');if(sell){enter(e)}},true);
  document.addEventListener('change',e=>{if(stActive&&e.target.matches?.('#v133Period,#v133Store,#v133Section'))setTimeout(render,0)},true);
  const obs=new MutationObserver(()=>{ensureTab();if(stActive&&C()&&!C().querySelector('.v135-st-table'))render()});obs.observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(ensureTab,350);setTimeout(ensureTab,1000);setTimeout(ensureTab,2000);
  console.info('[V135] Pestaña Sell Through demo instalada: ranking, existencia, sugerido, precio mayoreo e inversión.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v135_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v135-sellthrough-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V135-COMMERCIAL-SELLTHROUGH-DEMO",
            })
        except Exception as exc:
            print(f"[V135] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V135_COMMERCIAL_SELLTHROUGH_DEMO = True
    print("[V135] Sell Through demo instalado en Comercial; datos ficticios y sólo lectura.", flush=True)
