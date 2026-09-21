"""V177 · Restaura Sell Through en Análisis Comercial con datos reales.

El reporte anterior de Sell Through existía sólo dentro de demos visuales V135/V136.
Esta versión lo integra a producción usando el Excel de capacidades vigente.
"""
from __future__ import annotations

import math
import time
import unicodedata

from fastapi import Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V177_SELLTHROUGH_REPORT", False):
        return

    # La pestaña vuelve a formar parte de la configuración de visibilidad.
    try:
        if "commercial.sellthrough" not in m.REPORT_TABS:
            items = list(m.REPORT_TABS.items())
            m.REPORT_TABS.clear()
            inserted = False
            for key, label in items:
                m.REPORT_TABS[key] = label
                if key == "commercial.areas":
                    m.REPORT_TABS["commercial.sellthrough"] = "Sell Through"
                    inserted = True
            if not inserted:
                m.REPORT_TABS["commercial.sellthrough"] = "Sell Through"
    except Exception:
        pass

    def norm(v):
        t = unicodedata.normalize("NFKD", str(v or ""))
        return " ".join("".join(c for c in t if not unicodedata.combining(c)).casefold().split())

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    cache = {}

    @m.app.get("/api/commercial-sellthrough-v177")
    def commercial_sellthrough_v177(
        request: Request,
        week: str = "",
        store: str = "Compañía",
        section: str = "Todas",
        catalog: str = "Todos",
    ):
        actor = m.require_user(request)
        selected_store = str(m.effective_store(actor, store) or "Compañía")
        key = (week, norm(selected_store), norm(section), norm(catalog))
        now = time.monotonic()
        cached = cache.get(key)
        if cached and now - cached[0] < 300:
            return cached[1]

        frame = m._capacity_frame_for_period(week)
        if frame is None or frame.empty:
            return {
                "week": week, "store": selected_store, "section": section,
                "catalog": catalog, "rows": [], "totals": {},
                "formula": "Venta pzas / (Venta pzas + Existencia)",
            }

        work = m._capacity_scope_v45(frame, selected_store, section, catalog)
        if work is None or work.empty or "ID_ART" not in work.columns:
            return {
                "week": week, "store": selected_store, "section": section,
                "catalog": catalog, "rows": [], "totals": {},
                "formula": "Venta pzas / (Venta pzas + Existencia)",
            }

        pd = m.pd
        work = work.copy()
        work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
        work = work[~work["__id"].isin(["", "nan", "None"])]
        if work.empty:
            return {
                "week": week, "store": selected_store, "section": section,
                "catalog": catalog, "rows": [], "totals": {},
                "formula": "Venta pzas / (Venta pzas + Existencia)",
            }

        pcol, _vcol = m._capacity_period_columns(week)
        agg = pd.DataFrame(index=work.index)
        agg["__id"] = work["__id"]
        agg["sales_pzas"] = pd.to_numeric(work.get(pcol, 0), errors="coerce").fillna(0.0)
        agg["existence"] = pd.to_numeric(work.get("Existencia", 0), errors="coerce").fillna(0.0)
        agg["suggested"] = pd.to_numeric(work.get("VPD", 0), errors="coerce").fillna(0.0)
        numeric = agg.groupby("__id", sort=False)[["sales_pzas","existence","suggested"]].sum()

        meta_cols = {
            "model": "Modelo",
            "brand": "Marca",
            "section": "Sección",
            "rubro": "Subcategoría",
        }
        for dest, src in meta_cols.items():
            if src in work.columns:
                values = work[src].fillna("").astype(str).str.strip().replace({"nan":"", "None":""})
                part = pd.DataFrame({"__id":work["__id"], dest:values.replace("", pd.NA)})
                numeric = numeric.join(part.groupby("__id", sort=False)[dest].first(), how="left")

        for col, default in (("model",""),("brand","Sin marca"),("section","Sin sección"),("rubro","Sin rubro")):
            if col not in numeric.columns:
                numeric[col] = default
            numeric[col] = numeric[col].fillna(default).astype(str)

        models = numeric.reset_index().rename(columns={"__id":"id_art"})
        models["available_base"] = models["sales_pzas"] + models["existence"]
        models["sell_through"] = (
            models["sales_pzas"] / models["available_base"].replace(0, pd.NA) * 100
        ).fillna(0.0).clip(lower=0, upper=100)

        total_sales = float(models["sales_pzas"].sum())
        total_exist = float(models["existence"].sum())
        total_base = total_sales + total_exist
        overall = (total_sales / total_base * 100) if total_base else 0.0
        total_models = int(len(models))
        over80 = int((models["sell_through"] >= 80).sum())
        mid = int(((models["sell_through"] >= 50) & (models["sell_through"] < 80)).sum())
        low = int((models["sell_through"] < 50).sum())

        models = models.sort_values(
            ["sell_through","sales_pzas","existence"],
            ascending=[False,False,False],
        ).head(300).reset_index(drop=True)

        rows = []
        for idx, row in models.iterrows():
            rows.append({
                "rank": int(idx + 1),
                "id_art": str(row.get("id_art") or ""),
                "model": str(row.get("model") or row.get("id_art") or ""),
                "brand": str(row.get("brand") or "Sin marca"),
                "section": str(row.get("section") or "Sin sección"),
                "rubro": str(row.get("rubro") or "Sin rubro"),
                "sales_pzas": num(row.get("sales_pzas")),
                "existence": num(row.get("existence")),
                "available_base": num(row.get("available_base")),
                "suggested": num(row.get("suggested")),
                "sell_through": num(row.get("sell_through")),
            })

        payload = {
            "week": week,
            "store": selected_store,
            "section": section,
            "catalog": catalog,
            "rows": rows,
            "totals": {
                "sell_through": overall,
                "sales_pzas": total_sales,
                "existence": total_exist,
                "available_base": total_base,
                "models": total_models,
                "over80": over80,
                "mid50_79": mid,
                "under50": low,
            },
            "formula": "Venta pzas / (Venta pzas + Existencia)",
            "source": "Excel de capacidades",
        }
        if len(cache) >= 24:
            cache.pop(next(iter(cache)))
        cache[key] = (now, payload)
        print(
            f"[V177-SELLTHROUGH] {week} {selected_store} {section} "
            f"modelos={total_models} ST={overall:.1f}%",
            flush=True,
        )
        return payload

    css = r'''<style id="v177-sellthrough-css">
#page-sellthrough .v177-st-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:9px 0}
#page-sellthrough .v177-st-kpi{background:#fff;border:1px solid #d9e4f1;border-radius:12px;padding:12px 14px;min-width:0}
#page-sellthrough .v177-st-kpi .lab{font-size:8px;font-weight:950;color:#66768d;text-transform:uppercase}
#page-sellthrough .v177-st-kpi .val{font-size:22px;font-weight:950;color:#123f7b;margin-top:3px}
#page-sellthrough .v177-st-kpi .note{font-size:8px;color:#75849a;margin-top:2px}
#page-sellthrough .v177-st-head{display:flex;align-items:end;justify-content:space-between;gap:8px;flex-wrap:wrap;margin:8px 0}
#page-sellthrough .v177-st-tabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
#page-sellthrough .v177-st-tabs::-webkit-scrollbar{display:none}
#page-sellthrough .v177-st-tabs button{border:1px solid #d7e1ee;background:#fff;color:#17477f;border-radius:9px;min-height:36px;padding:7px 12px;font-size:8px;font-weight:900;white-space:nowrap;cursor:pointer}
#page-sellthrough .v177-st-tabs button.active{background:#176fe8;border-color:#176fe8;color:#fff}
#page-sellthrough .v177-st-pill{display:inline-block;min-width:48px;padding:3px 6px;border-radius:999px;text-align:center;font-weight:950;background:#eef4fb;color:#17477f}
#page-sellthrough .v177-st-pill.good{background:#e9f8ef;color:#118a52}
#page-sellthrough .v177-st-pill.mid{background:#fff5d9;color:#9a6a00}
#page-sellthrough .v177-st-table td,#page-sellthrough .v177-st-table th{white-space:nowrap}
#page-sellthrough .v177-st-note{font-size:8px;color:#64748b;margin:6px 0}
#analysisNav [data-sub="sellthrough"] .v177-nav-ico{display:inline-flex;width:18px;height:18px;align-items:center;justify-content:center;margin-right:6px;vertical-align:middle}
#analysisNav [data-sub="sellthrough"] .v177-nav-ico svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
@media(max-width:900px){
  #page-sellthrough .v177-st-kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  #page-sellthrough .v177-st-kpi{padding:9px 10px}
  #page-sellthrough .v177-st-kpi .val{font-size:16px}
  #page-sellthrough .v177-st-tabs button{min-height:34px;padding:6px 10px}
}
</style>'''

    js = r'''<script id="v177-sellthrough-js">
(function(){
  const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const p1=v=>Number(v||0).toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';
  let band='all',busy=false,lastData=null;

  function ensureUI(){
    const nav=q('#analysisNav');
    if(nav&&!q('[data-sub="sellthrough"]',nav)){
      const btn=document.createElement('button');
      btn.type='button';btn.className='switch';btn.dataset.sub='sellthrough';btn.dataset.tabKey='commercial.sellthrough';
      btn.innerHTML='<span class="v177-nav-ico"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="17" r="3"/><path d="M19 5 5 19"/></svg></span><span>Sell Through</span>';
      const before=q('[data-sub="more"]',nav)||q('[data-sub="analysis-upload"]',nav);
      nav.insertBefore(btn,before||null);
      btn.onclick=()=>openSellThrough();
    }

    if(!q('#page-sellthrough')){
      const page=document.createElement('section');
      page.className='page';page.id='page-sellthrough';
      page.innerHTML=
        '<div class="title">Sell Through</div>'+
        '<div class="subtitle">Rotación real por modelo con venta e inventario del periodo seleccionado.</div>'+
        '<div class="v177-st-kpis" id="v177StKpis"></div>'+
        '<div class="v177-st-head"><div><div class="title" style="margin:0">Ranking de modelos</div><div class="v177-st-note" id="v177StContext"></div></div>'+
          '<div class="v177-st-tabs" id="v177StTabs">'+
            '<button type="button" class="active" data-st-band="all">Todos</button>'+
            '<button type="button" data-st-band="over80">≥ 80%</button>'+
            '<button type="button" data-st-band="mid">50–79%</button>'+
            '<button type="button" data-st-band="low">&lt; 50%</button>'+
          '</div>'+
        '</div>'+
        '<div class="v177-st-note">Sell Through = Venta pzas / (Venta pzas + Existencia actual). Fuente: Excel de capacidades vigente.</div>'+
        '<div class="tablewrap"><table class="table v177-st-table"><thead><tr>'+
          '<th>#</th><th>% Sell Through</th><th>ID_ART</th><th>Modelo</th><th>Marca</th><th>Sección</th><th>Rubro</th><th>Venta pzas</th><th>Existencia</th><th>Base disponible</th><th>Sugerido 7</th>'+
        '</tr></thead><tbody id="v177StRows"><tr><td colspan="11">Selecciona Sell Through para consultar.</td></tr></tbody></table></div>';
      const anchor=q('#page-more')||q('#page-analysis-upload')||q('#appView');
      if(anchor?.parentNode)anchor.parentNode.insertBefore(page,anchor);
      else document.body.appendChild(page);
      qa('[data-st-band]',page).forEach(b=>b.onclick=()=>{
        band=b.dataset.stBand||'all';
        qa('[data-st-band]',page).forEach(x=>x.classList.toggle('active',x===b));
        renderRows(lastData);
      });
    }
  }

  async function A(url){
    const res=await fetch(url,{credentials:'same-origin',cache:'no-store'});
    if(!res.ok){let msg='Error '+res.status;try{const j=await res.json();msg=j.detail||msg}catch(_){}throw new Error(msg)}
    return res.json();
  }

  function inBand(x){
    const st=Number(x.sell_through||0);
    if(band==='over80')return st>=80;
    if(band==='mid')return st>=50&&st<80;
    if(band==='low')return st<50;
    return true;
  }
  function pill(st){
    const c=st>=80?'good':st>=50?'mid':'';
    return '<span class="v177-st-pill '+c+'">'+p1(st)+'</span>';
  }
  function renderRows(d){
    if(!d)return;
    const rows=(d.rows||[]).filter(inBand);
    const body=q('#v177StRows');
    if(body)body.innerHTML=rows.map((r,i)=>
      '<tr><td><b>#'+(i+1)+'</b></td><td>'+pill(r.sell_through)+'</td><td>'+esc(r.id_art)+'</td><td><b>'+esc(r.model)+'</b></td><td>'+esc(r.brand)+'</td><td>'+esc(r.section)+'</td><td>'+esc(r.rubro)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+nf(r.existence)+'</td><td>'+nf(r.available_base)+'</td><td>'+Number(r.suggested||0).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td></tr>'
    ).join('')||'<tr><td colspan="11">Sin modelos para este rango.</td></tr>';
  }
  function render(d){
    lastData=d;
    const t=d.totals||{};
    const k=q('#v177StKpis');
    if(k)k.innerHTML=
      '<div class="v177-st-kpi"><div class="lab">Sell Through general</div><div class="val">'+p1(t.sell_through)+'</div><div class="note">ponderado por piezas</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Venta pzas</div><div class="val">'+nf(t.sales_pzas)+'</div><div class="note">periodo seleccionado</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Existencia</div><div class="val">'+nf(t.existence)+'</div><div class="note">inventario actual</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Modelos ≥ 80%</div><div class="val">'+nf(t.over80)+'</div><div class="note">de '+nf(t.models)+' modelos</div></div>';
    const ctx=q('#v177StContext');
    if(ctx)ctx.textContent=(d.store||'Compañía')+' · '+(d.section||'Todas')+' · '+(d.week||'Periodo actual')+' · '+(d.source||'Excel capacidades');
    renderRows(d);
  }

  async function load(){
    if(busy)return;
    ensureUI();busy=true;
    const body=q('#v177StRows');if(body)body.innerHTML='<tr><td colspan="11">Cargando Sell Through…</td></tr>';
    try{
      const week=q('#week')?.value||'';
      const store=q('#store')?.value||'Compañía';
      const section=q('#section')?.value||'Todas';
      const catalog=q('#catalog')?.value||'Todos';
      const d=await A('/api/commercial-sellthrough-v177?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store)+'&section='+encodeURIComponent(section)+'&catalog='+encodeURIComponent(catalog));
      render(d);
    }catch(e){
      if(body)body.innerHTML='<tr><td colspan="11">No fue posible cargar Sell Through: '+esc(e.message||e)+'</td></tr>';
    }finally{busy=false}
  }

  function openSellThrough(){
    ensureUI();
    try{
      if(typeof goSub==='function')goSub('sellthrough');
      else{
        qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-sellthrough'));
        qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('active',x.dataset.sub==='sellthrough'));
      }
    }catch(_){
      qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-sellthrough'));
      qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('active',x.dataset.sub==='sellthrough'));
    }
    const cf=q('.commercialFilter');if(cf)cf.style.display='block';
    const ht=q('#heroTitle'),hs=q('#heroSub');
    if(ht)ht.textContent='Análisis Comercial';
    if(hs)hs.textContent='Sell Through · rotación por modelo';
    load();
  }
  window.loadSellThroughV177=load;

  document.addEventListener('change',e=>{
    if(e.target.matches?.('#week,#store,#section,#catalog,#v166StatusSelect')&&q('#page-sellthrough.active'))load();
  },true);
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('#analysisNav [data-sub="sellthrough"]');
    if(b){e.preventDefault();e.stopImmediatePropagation();openSellThrough();}
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensureUI,{once:true});
  else ensureUI();
  setTimeout(ensureUI,300);setTimeout(ensureUI,1200);
  console.info('[V177] Sell Through real restaurado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v177_sellthrough_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v177-sellthrough-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v177-sellthrough-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-SellThrough"] = "V177"
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V177_SELLTHROUGH_REPORT = True
    print("[V177] Sell Through de producción restaurado con datos reales.", flush=True)
