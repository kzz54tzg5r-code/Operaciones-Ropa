"""V176 · Comercial integral: filtros, ventas, ubicación, modelos y sidebar.

Solicitado 2026-09-18:
- Sidebar comprimido estable.
- Tiendas disponibles siempre visibles en filtros comerciales.
- Navegación comercial sin huecos visuales.
- KPI Excedente por compañía/sección.
- Ventas con selector Mes dependiente de PDFs cargados, Todos vs mes,
  gráfica por meses/tiendas, etiquetas, variaciones, Pesos/Piezas,
  tablas sin PDF y orden sólo por % Meta / % vs año anterior.
- Ubicación: Compañía agrupada por tienda + tipo; tienda con detalle pasillo/mesa.
- 80/20, lentos y sugerido 0-1 con carga final autoritativa.
"""
from __future__ import annotations

from collections import defaultdict
import inspect
import math
import threading
import time
import unicodedata

from fastapi import Request
from fastapi.responses import HTMLResponse


MONTH_LABELS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
MONTH_LONG = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


def install(m):
    if getattr(m, "_V176_COMMERCIAL_INTEGRAL", False):
        return

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def norm(v):
        t = unicodedata.normalize("NFKD", str(v or ""))
        return " ".join("".join(c for c in t if not unicodedata.combining(c)).casefold().split())

    def is_company(v):
        return norm(v) in ("", "compania", "company")

    def route_endpoint(path, method="GET"):
        rows = [
            r for r in m.app.router.routes
            if getattr(r, "path", None) == path
            and method in (getattr(r, "methods", set()) or set())
        ]
        return rows[-1].endpoint if rows else None

    # --------------------- Filtros de tiendas ---------------------
    @m.app.get("/api/commercial-filter-options-v176")
    def commercial_filter_options_v176(request: Request, week: str = ""):
        actor = m.require_user(request)
        if actor.get("role") == "tienda":
            assigned = str(actor.get("store") or "").strip()
            return {"stores": [assigned] if assigned else [], "company": False}

        managed = [str(x).strip() for x in (m.store_names(True) or []) if str(x).strip()]
        detected = []
        try:
            frame = m._capacity_frame_for_period(week)
            if frame is not None and not frame.empty and "Tienda" in frame.columns:
                detected = [
                    str(x).strip() for x in frame["Tienda"].dropna().astype(str).unique().tolist()
                    if str(x).strip() and norm(x) not in ("nan", "none", "compania")
                ]
        except Exception:
            detected = []

        # Catálogo configurado primero; detectadas después. Así no desaparece una
        # tienda por diferencias de alias en el Excel.
        out = []
        seen = set()
        for x in managed + detected:
            k = norm(x)
            if not k or k in seen:
                continue
            seen.add(k)
            out.append(x)
        return {"stores": out, "company": True}

    # --------------------- Ubicación / Área -----------------------
    @m.app.get("/api/commercial-area-v176")
    def commercial_area_v176(
        request: Request, week: str = "", store: str = "Compañía",
        section: str = "Todas", catalog: str = "Todos",
    ):
        actor = m.require_user(request)
        selected = str(m.effective_store(actor, store) or "Compañía")
        groups = ("Colgado", "Doblado", "Jeans", "Lencería")

        if not is_company(selected):
            rows = list(m._capacity_location_detail(selected, section, catalog, week) or [])
            rows = [r for r in rows if str(r.get("group") or "") in groups]
            return {"store": selected, "mode": "detail", "rows": rows}

        try:
            frame = m._capacity_frame_for_period(week)
            work = m._capacity_scope_v45(frame, "Compañía", section, catalog, add_area=True)
            if work is None or work.empty:
                return {"store": "Compañía", "mode": "grouped", "rows": []}
            if "Área reporte" not in work.columns:
                work = work.copy()
                work["Área reporte"] = m._capacity_area_report_series(work)
            work = work[work["Área reporte"].astype(str).isin(groups)].copy()
            rows = []
            for (st, area), g in work.groupby(["Tienda", "Área reporte"], dropna=False, sort=False):
                met = m._capacity_metrics(g, week)
                ids = 0
                if "ID_ART" in g.columns:
                    ids = int(
                        g["ID_ART"].fillna("").astype(str).str.strip()
                        .replace({"nan": "", "None": ""}).loc[lambda x: x.ne("")].nunique()
                    )
                rows.append({
                    "store": str(st or ""), "group": str(area or ""),
                    "ids": ids, **met,
                })
            order = {"Colgado": 1, "Doblado": 2, "Jeans": 3, "Lencería": 4}
            rows.sort(key=lambda r: (order.get(r["group"], 99), -num(r.get("suggested")), norm(r.get("store"))))
            return {"store": "Compañía", "mode": "grouped", "rows": rows}
        except Exception as exc:
            print(f"[V176-AREA] {type(exc).__name__}: {exc}", flush=True)
            return {"store": "Compañía", "mode": "grouped", "rows": [], "error": str(exc)}

    # --------------------- Modelos / 80-20 ------------------------
    model_cache = {}
    model_lock = threading.RLock()

    @m.app.get("/api/commercial-models-v176")
    def commercial_models_v176(
        request: Request, week: str = "", store: str = "Compañía",
        section: str = "Todas", catalog: str = "Todos", group_by: str = "section",
    ):
        actor = m.require_user(request)
        selected = str(m.effective_store(actor, store) or "Compañía")
        gb = group_by if group_by in ("section", "area", "catalog", "general") else "section"
        key = (week, norm(selected), norm(section), norm(catalog), gb)
        now = time.monotonic()
        with model_lock:
            cached = model_cache.get(key)
            if cached and now - cached[0] < 600:
                return cached[1]
            champs = list(m._capacity_model_rows(selected, section, "80_20", week, catalog) or [])
            slow = list(m._capacity_model_rows(selected, section, "slow", week, catalog) or [])
            zero = list(m._capacity_model_rows(selected, section, "suggested_zero", week, catalog) or [])
            pareto = dict(m._capacity_8020_summary(selected, section, catalog, week, gb) or {})
            payload = {
                "week": week, "store": selected, "section": section, "catalog": catalog,
                "champions": champs, "slow": slow, "zero": zero, "pareto": pareto,
                "checklist_enabled": not is_company(selected),
            }
            if len(model_cache) >= 24:
                model_cache.pop(next(iter(model_cache)))
            model_cache[key] = (now, payload)
            print(
                f"[V176-MODELS] {week} {selected} {section} "
                f"80/20={len(champs)} lentos={len(slow)} cero={len(zero)}",
                flush=True,
            )
            return payload

    # --------------------- Ventas V176 ----------------------------
    sales_base = route_endpoint("/api/commercial-sales-v174")

    def latest_sales_entries(year: int):
        latest = {}
        for raw in list((m.load_manifest() or {}).get("sales") or []):
            e = dict(raw)
            yy = int(e.get("year") or 0)
            mo = int(e.get("month") or 0)
            if yy != year or mo not in range(1, 13):
                continue
            path = m.resolve_entry_path(e)
            if not path.exists() or path.suffix.lower() != ".pdf":
                continue
            old = latest.get(mo)
            if old is None or str(e.get("uploaded_at") or "") >= str(old.get("uploaded_at") or ""):
                latest[mo] = e
        return latest

    def scope_ocr(entry, scope):
        fn = getattr(m, "ocr_for_entry", None)
        if not callable(fn) or not entry:
            return {}, {}
        try:
            payload = dict(fn(entry) or {})
        except Exception:
            return {}, {}
        if is_company(scope):
            return dict(payload.get("company") or {}), payload
        for name, row in (payload.get("stores") or {}).items():
            if norm(name) == norm(scope):
                return dict(row or {}), payload
        return {}, payload

    def store_rows_from_entries(latest, months_to_use):
        acc = defaultdict(lambda: {
            "current": 0.0, "previous": 0.0, "target": 0.0,
            "pieces": 0.0, "pieces_previous": 0.0, "months": 0,
        })
        cut_dates = []
        for mo in months_to_use:
            entry = latest.get(mo)
            if not entry:
                continue
            _company, payload = scope_ocr(entry, "Compañía")
            if payload.get("cut_date"):
                cut_dates.append(str(payload.get("cut_date")))
            for name, row in (payload.get("stores") or {}).items():
                x = acc[str(name)]
                x["current"] += num(row.get("current"))
                x["previous"] += num(row.get("previous"))
                x["target"] += num(row.get("target"))
                x["pieces"] += num(row.get("pieces"))
                x["pieces_previous"] += num(row.get("pieces_previous"))
                x["months"] += 1
        out = []
        for name, x in acc.items():
            cur, prev, goal = x["current"], x["previous"], x["target"]
            out.append({
                "store": name, **x,
                "pct_goal": cur / goal * 100 if goal else None,
                "pct_previous": (cur / prev - 1) * 100 if prev else None,
                "pieces_growth": (
                    (x["pieces"] / x["pieces_previous"] - 1) * 100
                    if x["pieces_previous"] else None
                ),
            })
        out.sort(key=lambda x: (-num(x.get("current")), norm(x.get("store"))))
        for i, row in enumerate(out, 1):
            row["rank"] = i
        return out, (cut_dates[-1] if cut_dates else "")

    @m.app.get("/api/commercial-sales-v176")
    async def commercial_sales_v176(
        request: Request, year: int | None = None, month: int = 0,
        store: str = "Compañía",
    ):
        actor = m.require_user(request)
        yy = int(year or m.datetime.now().year)
        scope = str(m.effective_store(actor, store) or "Compañía")
        latest = latest_sales_entries(yy)
        available = sorted(latest)
        max_month = max(available) if available else max(1, min(12, m.datetime.now().month))
        selected_month = int(month or 0)
        if selected_month and selected_month not in available:
            selected_month = 0

        if sales_base is None:
            raise RuntimeError("Motor de ventas V174 no disponible")

        # V174 entrega el acumulado estable y ya validado.
        base = sales_base(request=request, year=yy, through_month=max_month, store=scope)
        if inspect.isawaitable(base):
            base = await base
        base = dict(base or {})
        months = [dict(x) for x in (base.get("months") or [])]

        # Enriquecer piezas del año anterior directamente del OCR.
        for row in months:
            mo = int(row.get("month") or 0)
            entry = latest.get(mo)
            vals, _payload = scope_ocr(entry, scope)
            if vals:
                row["pieces"] = num(vals.get("pieces")) or num(row.get("pieces"))
                row["pieces_previous"] = num(vals.get("pieces_previous"))
            else:
                row.setdefault("pieces_previous", 0.0)
            row["pdf_loaded"] = bool(entry)
            row["pct_goal"] = (
                num(row.get("current")) / num(row.get("target")) * 100
                if num(row.get("target")) else None
            )
            row["pct_previous"] = (
                (num(row.get("current")) / num(row.get("previous")) - 1) * 100
                if num(row.get("previous")) else None
            )
            row["pieces_growth"] = (
                (num(row.get("pieces")) / num(row.get("pieces_previous")) - 1) * 100
                if num(row.get("pieces_previous")) else None
            )

        use_months = [selected_month] if selected_month else available
        selected_rows = [r for r in months if int(r.get("month") or 0) in use_months]
        total_current = sum(num(r.get("current")) for r in selected_rows)
        total_previous = sum(num(r.get("previous")) for r in selected_rows)
        total_target = sum(num(r.get("target")) for r in selected_rows)
        total_pieces = sum(num(r.get("pieces")) for r in selected_rows)
        total_pieces_prev = sum(num(r.get("pieces_previous")) for r in selected_rows)

        stores, store_cut = store_rows_from_entries(latest, use_months)
        if not is_company(scope):
            stores = [r for r in stores if norm(r.get("store")) == norm(scope)]

        years = sorted(
            {int(e.get("year") or 0) for e in (m.load_manifest() or {}).get("sales", []) if int(e.get("year") or 0) > 0}
            | {yy, yy - 1},
            reverse=True,
        )
        return {
            **base,
            "year": yy, "previous_year": yy - 1, "store": scope,
            "selected_month": selected_month, "available_months": available,
            "available_years": years, "months": months, "stores": stores,
            "display_mode": "stores" if selected_month else "months",
            "cut_date": store_cut or str(base.get("cut_date") or ""),
            "totals": {
                "current": total_current, "previous": total_previous, "target": total_target,
                "pieces": total_pieces, "pieces_previous": total_pieces_prev,
                "compliance": total_current / total_target * 100 if total_target else None,
                "growth": (total_current / total_previous - 1) * 100 if total_previous else None,
                "pieces_growth": (
                    (total_pieces / total_pieces_prev - 1) * 100 if total_pieces_prev else None
                ),
                "gap_to_goal": total_current - total_target if total_target else None,
            },
            "source_count": len(available),
            "source_label": "PDF mensual · Meta/Año anterior validados · V176",
        }

    # Asegura que las pestañas comerciales centrales sigan en el catálogo.
    try:
        with m.db() as con:
            for key in ("commercial.macro", "commercial.accordion", "commercial.stores", "commercial.sections", "commercial.areas"):
                con.execute(
                    "INSERT OR IGNORE INTO report_tab_visibility(tab_key,visible,updated_at,updated_by) VALUES(?,1,datetime('now'),'system-v176')",
                    (key,),
                )
    except Exception:
        pass

    css = r'''<style id="v176-commercial-css">
/* Sidebar: al contraer no se exprimen las palabras por reglas tipográficas posteriores. */
@media(min-width:901px){
  .shell.sidebar-collapsed{grid-template-columns:72px minmax(0,1fr)!important}
  .shell.sidebar-collapsed .side{padding-left:7px!important;padding-right:7px!important}
  .shell.sidebar-collapsed .nav{
    font-size:0!important;line-height:1!important;padding:10px 3px!important;
    min-height:48px!important;text-align:center!important;display:flex!important;
    align-items:center!important;justify-content:center!important;flex-direction:column!important
  }
  .shell.sidebar-collapsed .nav .v176-nav-label{display:none!important}
  .shell.sidebar-collapsed .nav:before{font-size:19px!important;line-height:22px!important;margin:0!important}
  .shell.sidebar-collapsed .nav[data-main="users"]:before{content:"♙"}
  .shell.sidebar-collapsed .sidebrand img{width:50px!important;max-width:50px!important}
}

/* Navegación comercial: sin huecos ni botones flotando. */
body[data-v163-module="analysis"] #analysisNav:not(.hidden){
  display:grid!important;grid-template-columns:repeat(auto-fit,minmax(135px,1fr))!important;
  gap:5px!important;align-items:stretch!important
}
body[data-v163-module="analysis"] #analysisNav .switch{
  width:100%!important;min-width:0!important;min-height:44px!important;margin:0!important;
  display:flex!important;align-items:center!important;justify-content:center!important;gap:6px!important
}

/* Filtros internos: mismo lenguaje visual que Macro compañía / Acordeón / Tiendas. */
body[data-v163-module="analysis"] #page-macro .compact-filter,
body[data-v163-module="analysis"] #page-sections .compact-filter,
body[data-v163-module="analysis"] #page-areas .compact-filter{
  background:#fff!important;
  border:1px solid var(--line)!important;
  border-radius:12px!important;
  padding:7px!important;
  margin:7px 0 10px!important;
  box-shadow:none!important
}
body[data-v163-module="analysis"] #page-macro .compact-filter .switches,
body[data-v163-module="analysis"] #page-sections .compact-filter .switches,
body[data-v163-module="analysis"] #page-areas .compact-filter .switches{
  display:flex!important;
  grid-template-columns:none!important;
  flex-wrap:wrap!important;
  align-items:center!important;
  gap:5px!important;
  width:100%!important;
  overflow:visible!important;
  margin:2px 0 5px!important;
  padding:0!important
}
body[data-v163-module="analysis"] #page-macro .compact-filter .switches>button,
body[data-v163-module="analysis"] #page-sections .compact-filter .switches>button,
body[data-v163-module="analysis"] #page-areas .compact-filter .switches>button{
  flex:0 0 auto!important;
  width:auto!important;
  min-width:108px!important;
  min-height:40px!important;
  height:40px!important;
  padding:7px 12px!important;
  margin:0!important;
  border:1px solid var(--line)!important;
  border-radius:999px!important;
  background:#fff!important;
  color:var(--muted)!important;
  font-size:8.5px!important;
  line-height:1.1!important;
  font-weight:900!important;
  box-shadow:none!important;
  white-space:nowrap!important
}
body[data-v163-module="analysis"] #page-macro .compact-filter .switches>button.active,
body[data-v163-module="analysis"] #page-sections .compact-filter .switches>button.active,
body[data-v163-module="analysis"] #page-areas .compact-filter .switches>button.active{
  background:var(--blue)!important;
  border-color:var(--blue)!important;
  color:#fff!important
}
body[data-v163-module="analysis"] .compact-filter .filter-caption{
  margin:2px 3px 5px!important;
  color:#64768d!important;
  font-size:8px!important;
  line-height:1.15!important;
  font-weight:950!important;
  text-transform:uppercase!important
}
body[data-v163-module="analysis"] .v166-internal-filter{display:none!important}

/* KPI de excedente. */
#v176ExcessKpi .v176-excess-sections{display:block;margin-top:3px;font-size:9px;line-height:1.35;color:#667085}
#v176ExcessKpi .v176-excess-pieces{display:block;font-size:10px;color:#52657d}

/* Ventas. */
.v176-sales-metric{display:flex;gap:4px;align-items:end}
.v176-sales-metric button{min-height:38px;border:1px solid #cad8e8;background:#fff;color:#173f78;border-radius:8px;padding:6px 11px;font-weight:900}
.v176-sales-metric button.active{background:#176fe8;color:#fff;border-color:#176fe8}
.v176-sales-sort{border:0!important;background:transparent!important;color:inherit!important;font:inherit!important;font-weight:950!important;padding:0!important;cursor:pointer}
.v176-sales-rank .v176-pos{color:#118a52;font-weight:900}.v176-sales-rank .v176-neg{color:#d92d20;font-weight:900}
.v176-chart-svg text{font-family:Inter,Segoe UI,Arial,sans-serif}
.v176-chart-value{font-weight:900}.v176-chart-growth{font-weight:950}
#salesExecThrough option[disabled]{color:#9aa7b7}

/* Ubicación agrupada. */
.v176-area-company td:nth-child(1),.v176-area-company td:nth-child(2){font-weight:900}
#champTable td,#champTable th{white-space:nowrap}
#champTable th:nth-child(7),#champTable th:nth-child(8){min-width:105px}

@media(max-width:900px){
  body[data-v163-module="analysis"] #analysisNav:not(.hidden){
    display:flex!important;overflow-x:auto!important;flex-wrap:nowrap!important;-webkit-overflow-scrolling:touch!important
  }
  body[data-v163-module="analysis"] #analysisNav .switch{flex:0 0 105px!important;min-width:105px!important}
  body[data-v163-module="analysis"] #page-macro .compact-filter .switches,
  body[data-v163-module="analysis"] #page-sections .compact-filter .switches,
  body[data-v163-module="analysis"] #page-areas .compact-filter .switches{
    display:flex!important;
    flex-wrap:nowrap!important;
    overflow-x:auto!important;
    overflow-y:hidden!important;
    scrollbar-width:none!important;
    -webkit-overflow-scrolling:touch!important
  }
  body[data-v163-module="analysis"] #page-macro .compact-filter .switches::-webkit-scrollbar,
  body[data-v163-module="analysis"] #page-sections .compact-filter .switches::-webkit-scrollbar,
  body[data-v163-module="analysis"] #page-areas .compact-filter .switches::-webkit-scrollbar{display:none!important}
  body[data-v163-module="analysis"] #page-macro .compact-filter .switches>button,
  body[data-v163-module="analysis"] #page-sections .compact-filter .switches>button,
  body[data-v163-module="analysis"] #page-areas .compact-filter .switches>button{
    flex:0 0 auto!important;
    min-width:96px!important;
    width:auto!important;
    min-height:36px!important;
    height:36px!important;
    padding:6px 10px!important;
    font-size:8px!important
  }
  #v176ExcessKpi .v176-excess-sections{font-size:6.6px!important}
  #v176ExcessKpi .v176-excess-pieces{font-size:7px!important}
}
</style>'''

    js = r'''<script id="v176-commercial-js">
(function(){
if(window.__V176_COMMERCIAL)return;window.__V176_COMMERCIAL=true;
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
const n=v=>Number(v||0),nf=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:0});
const money=v=>'$'+n(v).toLocaleString('es-MX',{maximumFractionDigits:0});
const pct=v=>v==null||!Number.isFinite(Number(v))?'—':n(v).toFixed(1)+'%';
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const months=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
const monthLong=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
let salesMetric='money',salesMonth=0,salesSort={key:'',dir:-1},salesBusy=false,modelsBusy=false;

async function A(url,opt){
  if(typeof window.api==='function')return window.api(url,opt);
  const r=await fetch(url,{credentials:'same-origin',...(opt||{})});
  const d=await r.json();if(!r.ok)throw Error(d.detail||('HTTP '+r.status));return d
}
function activeAnalysis(){return String(window.MAIN||'').toLowerCase()==='analysis'||document.body.dataset.v163Module==='analysis'}
function macroActive(){return activeAnalysis()&&q('#page-macro')?.classList.contains('active')}

function fixSidebar(){
  qa('#sidebar .nav').forEach(b=>{
    if(b.querySelector('.v176-nav-label'))return;
    const texts=[...b.childNodes].filter(x=>x.nodeType===3&&String(x.textContent||'').trim());
    if(!texts.length)return;
    const span=document.createElement('span');span.className='v176-nav-label';
    span.textContent=texts.map(x=>String(x.textContent||'').trim()).join(' ');
    texts.forEach(x=>x.remove());
    const small=b.querySelector('small');b.insertBefore(span,small||null);
  });
}

function visibleStoreControl(){
  return qa('#v161FilterGrid .v161-field').find(w=>(w.querySelector('label')?.textContent||'').trim().toLowerCase()==='tienda')?.querySelector('select')||null;
}
async function fixStores(){
  if(!activeAnalysis())return;
  try{
    const week=q('#week')?.value||'';
    const d=await A('/api/commercial-filter-options-v176?week='+encodeURIComponent(week),{timeoutMs:30000});
    const native=q('#store'),facade=visibleStoreControl();
    const controls=[native,facade].filter(Boolean);
    const current=(facade?.value||native?.value||'Compañía');
    controls.forEach(sel=>{
      const before=sel.value;
      sel.innerHTML='';
      if(d.company)sel.add(new Option('Compañía','Compañía'));
      (d.stores||[]).forEach(st=>sel.add(new Option(st,st)));
      const wanted=[...sel.options].some(o=>o.value===current)?current:
        ([...sel.options].some(o=>o.value===before)?before:(sel.options[0]?.value||''));
      sel.value=wanted;
    });
    if(facade&&!facade.dataset.v176store){
      facade.dataset.v176store='1';
      facade.addEventListener('change',()=>{
        if(native){native.value=facade.value;native.dispatchEvent(new Event('change',{bubbles:true}))}
        setTimeout(()=>window.loadDash?.(),20);
      });
    }
    if(native&&facade&&native.value!==facade.value)native.value=facade.value;
  }catch(e){console.warn('[V176] tiendas',e)}
}

function fixAnalysisNav(){
  qa('#analysisNav [data-sub]').forEach(b=>{
    b.style.removeProperty('width');b.style.removeProperty('min-width');
    const label=(b.textContent||'').replace(/\s+/g,' ').trim();
    if(label)b.title=label;
  });
}

function excessFor(x){
  const ex=n(x?.existence),cap=n(x?.capacity),p=Math.max(ex-cap,0);
  return {pieces:p,pct:cap>0?p/cap*100:0}
}
function renderExcess(){
  if(typeof DASH==='undefined'||!DASH?.kpis||!q('#page-macro .kpis'))return;
  let card=q('#v176ExcessKpi');
  if(!card){
    card=document.createElement('div');card.id='v176ExcessKpi';card.className='kpi';card.style.setProperty('--a','#ef376c');
    q('#page-macro .kpis').append(card);
  }
  const total=excessFor(DASH.kpis),secs=DASH.sections||[];
  const detail=['Dama','Caballero','Infantil'].map(name=>{
    const row=secs.find(x=>String(x.section||'').toLowerCase().startsWith(name.toLowerCase()));
    const z=excessFor(row);
    const short=name==='Caballero'?'Cab.':name==='Infantil'?'Inf.':'Dama';
    return short+' '+pct(z.pct)+' · '+nf(z.pieces)+' pzas';
  }).join(' · ');
  card.innerHTML='<div class="lab">% Excedente</div><div class="val">'+pct(total.pct)+'</div>'+
    '<span class="v176-excess-pieces">'+nf(total.pieces)+' piezas sobre capacidad</span>'+
    '<span class="v176-excess-sections">'+detail+'</span>';
  window.setTimeout(()=>{if(typeof window.__V166_STABLE_UI!=='undefined'){}},0);
}

function selectedAreaSection(){
  return q('[data-area-section].active')?.dataset.areaSection||q('#section')?.value||'Todas'
}
function selectedAreaGroup(){return q('[data-area-group].active')?.dataset.areaGroup||'Todas'}
async function renderArea(){
  if(!macroActive()||!q('#macroAreaTable'))return;
  const store=visibleStoreControl()?.value||q('#store')?.value||'Compañía',week=q('#week')?.value||'',section=selectedAreaSection(),catalog=q('#catalog')?.value||'Todos',group=selectedAreaGroup();
  const title=q('#macroAreaTitle');if(title)title.textContent='Ubicación · '+store+(section!=='Todas'?' · '+section:'')+(group!=='Todas'?' · '+group:'');
  try{
    const d=await A('/api/commercial-area-v176?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store)+'&section='+encodeURIComponent(section)+'&catalog='+encodeURIComponent(catalog),{timeoutMs:120000});
    let rows=(d.rows||[]).filter(r=>group==='Todas'||r.group===group);
    const table=q('#macroAreaTable')?.closest('table'),head=table?.querySelector('thead tr'),body=q('#macroAreaTable');
    if(d.mode==='grouped'){
      table?.classList.add('v176-area-company');
      if(head)head.innerHTML='<th>Tienda</th><th>Ubicación</th><th>Modelos</th><th>Curva</th><th>Piso</th><th>Bodega</th><th>Existencia</th><th>Sugerido 7</th><th>DDI 7</th><th>Vta pzas</th><th>Venta $</th><th>% Ocupación</th>';
      body.innerHTML=rows.length?rows.map(r=>'<tr><td>'+esc(r.store)+'</td><td>'+esc(r.group)+'</td><td>'+nf(r.ids)+'</td><td>'+nf(r.capacity)+'</td><td>'+nf(r.floor)+'</td><td>'+nf(r.warehouse)+'</td><td>'+nf(r.existence)+'</td><td>'+n(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td><td>'+nf(r.ddi)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td><td>'+pct(r.occupancy)+'</td></tr>').join(''):'<tr><td colspan="12">Sin información para este filtro.</td></tr>';
    }else{
      table?.classList.remove('v176-area-company');
      if(head)head.innerHTML='<th>Ubicación</th><th>Pasillo / Mesa</th><th>Modelos</th><th>Curva</th><th>Piso</th><th>Bodega</th><th>Existencia</th><th>Sugerido 7</th><th>DDI 7</th><th>Vta pzas</th><th>Venta $</th><th>% Ocupación</th>';
      body.innerHTML=rows.length?rows.map(r=>'<tr><td><b>'+esc(r.group)+'</b></td><td><b>'+esc(r.location)+'</b></td><td>'+nf(r.ids)+'</td><td>'+nf(r.capacity)+'</td><td>'+nf(r.floor)+'</td><td>'+nf(r.warehouse)+'</td><td>'+nf(r.existence)+'</td><td>'+n(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td><td>'+nf(r.ddi)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td><td>'+pct(r.occupancy)+'</td></tr>').join(''):'<tr><td colspan="12">Sin información para este filtro.</td></tr>';
    }
  }catch(e){q('#macroAreaTable').innerHTML='<tr><td colspan="12">No fue posible consultar Ubicación / Área: '+esc(e.message||e)+'</td></tr>'}
}
window.loadMacroAreaDetail=renderArea;

function fixModelHead(){
  const head=q('#champTable')?.closest('table')?.querySelector('thead tr');if(!head)return;
  const company=(visibleStoreControl()?.value||q('#store')?.value||'Compañía')==='Compañía';
  head.innerHTML='<th>Ranking</th><th>ID_ART</th><th>Modelo</th><th>Marca</th><th>Sección</th><th>Rubro</th><th>'+(company?'Tipo ubicación':'Ubicación')+'</th><th>'+(company?'Exhibiciones':'Exhibición')+'</th><th>Vta pzas</th><th>Venta $</th><th>Existencia</th><th>Sugerido 7</th><th>DDI 7</th><th>Capacidad</th><th>% Ocupación</th><th>% Acum.</th>';
}
function paretoGroup(){return q('[data-pareto-group].active')?.dataset.paretoGroup||'section'}
function renderPareto(rows){
  const body=q('#paretoSummaryTable');if(!body)return;
  body.innerHTML=(rows||[]).map(r=>'<tr><td><b>'+esc(r.label)+'</b></td><td>'+pct(r.participation)+'</td><td>'+nf(r.models_80)+'</td><td>'+nf(r.models_20)+'</td><td>'+nf(r.models)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td><td>'+n(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td><td>'+nf(r.ddi)+'</td><td>'+nf(r.capacity)+'</td><td>'+pct(r.occupancy)+'</td></tr>').join('')||'<tr><td colspan="11">Información no disponible.</td></tr>';
}
async function renderModels(force){
  if(!macroActive()||modelsBusy)return;
  modelsBusy=true;
  const store=visibleStoreControl()?.value||q('#store')?.value||((typeof DASH!=='undefined'&&DASH?.selected_store)?DASH.selected_store:'Compañía'),week=q('#week')?.value||'',section=q('#section')?.value||'Todas',catalog=q('#catalog')?.value||'Todos',gb=paretoGroup();
  try{
    if(q('#champTable'))q('#champTable').innerHTML='<tr><td colspan="16">Cargando 80/20…</td></tr>';
    if(q('#slowTable'))q('#slowTable').innerHTML='<tr><td colspan="15">Cargando modelos lentos…</td></tr>';
    if(q('#zeroTable'))q('#zeroTable').innerHTML='<tr><td colspan="16">Cargando sugerido 0 a 1…</td></tr>';
    const d=await A('/api/commercial-models-v176?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store)+'&section='+encodeURIComponent(section)+'&catalog='+encodeURIComponent(catalog)+'&group_by='+encodeURIComponent(gb),{timeoutMs:240000});
    let ck={rows:[],editable:false};
    if(store!=='Compañía'){
      try{ck=await A('/api/model-checklist?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store),{timeoutMs:60000})}catch(_){}
    }
    const map={};(ck.rows||[]).forEach(r=>map[String(r.id_art)]=r);
    if(typeof window.renderModelRows==='function'){
      window.renderModelRows(d.champions||[],d.slow||[],d.zero||[],section,section,store,map,!!ck.editable,store==='Compañía'?'':store,store);
    }
    fixModelHead();renderPareto(d.pareto?.rows||[]);
  }catch(e){
    const msg='No fue posible cargar la información: '+esc(e.message||e);
    if(q('#champTable'))q('#champTable').innerHTML='<tr><td colspan="16">'+msg+'</td></tr>';
    if(q('#slowTable'))q('#slowTable').innerHTML='<tr><td colspan="15">'+msg+'</td></tr>';
    if(q('#zeroTable'))q('#zeroTable').innerHTML='<tr><td colspan="16">'+msg+'</td></tr>';
  }finally{modelsBusy=false}
}
window.loadModelTables=renderModels;

function shortVal(v,metric){
  const x=n(v),a=Math.abs(x);
  if(metric==='pieces'){
    if(a>=1e6)return (x/1e6).toFixed(1)+'M';
    if(a>=1e3)return Math.round(x/1e3)+'k';
    return Math.round(x).toLocaleString('es-MX');
  }
  if(a>=1e9)return '$'+(x/1e9).toFixed(2)+'B';
  if(a>=1e6)return '$'+(x/1e6).toFixed(a>=1e8?0:1)+'M';
  if(a>=1e3)return '$'+Math.round(x/1e3)+'k';
  return '$'+Math.round(x);
}
function tone(v,meta){
  if(v==null)return'';
  if(meta)return n(v)>=100?'sales-pos':n(v)>=90?'sales-mid':'sales-neg';
  return n(v)>=0?'sales-pos':'sales-neg'
}
function graphRows(d){
  if(d.selected_month){
    return (d.stores||[]).map(x=>({...x,label:x.store}));
  }
  const allowed=new Set(d.available_months||[]);
  return (d.months||[]).filter(x=>allowed.has(Number(x.month)));
}
function salesChart176(d){
  const host=q('#salesExecChart');if(!host)return;
  const rows=graphRows(d),metric=salesMetric,W=Math.max(980,90*rows.length+100),H=340,L=68,R=18,T=45,B=52,pw=W-L-R,ph=H-T-B;
  const cur=r=>metric==='pieces'?n(r.pieces):n(r.current),prev=r=>metric==='pieces'?n(r.pieces_previous):n(r.previous);
  const vals=[];rows.forEach(r=>{vals.push(cur(r),prev(r));if(metric==='money')vals.push(n(r.target))});
  const mx=Math.max(1,...vals)*1.16,y=v=>T+ph-n(v)/mx*ph,gw=pw/Math.max(rows.length,1),bw=Math.min(24,gw*.28);
  let s='<svg class="v176-chart-svg" viewBox="0 0 '+W+' '+H+'">';
  for(let i=0;i<=4;i++){const val=mx*i/4,yy=y(val);s+='<line x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'" stroke="#dce4ee"/><text x="'+(L-7)+'" y="'+(yy+3)+'" text-anchor="end" font-size="8" fill="#6b778c">'+shortVal(val,metric)+'</text>'}
  const pts=[];
  rows.forEach((r,i)=>{
    const cx=L+gw*(i+.5),a=cur(r),b=prev(r),ya=y(a),yb=y(b),base=T+ph,g=n(r.target);
    const gp=prev(r)>0?(a/prev(r)-1)*100:null,mp=n(r.target)>0?n(r.current)/n(r.target)*100:null;
    s+='<rect x="'+(cx-bw-2)+'" y="'+ya+'" width="'+bw+'" height="'+Math.max(0,base-ya)+'" rx="3" fill="#1769e8"/>';
    s+='<rect x="'+(cx+2)+'" y="'+yb+'" width="'+bw+'" height="'+Math.max(0,base-yb)+'" rx="3" fill="#9fb0c6"/>';
    if(a>0)s+='<text class="v176-chart-value" x="'+(cx-bw/2-2)+'" y="'+Math.min(base-5,ya+14)+'" text-anchor="middle" font-size="7" fill="#fff">'+shortVal(a,metric)+'</text>';
    if(b>0)s+='<text class="v176-chart-value" x="'+(cx+bw/2+2)+'" y="'+Math.min(base-5,yb+14)+'" text-anchor="middle" font-size="7" fill="#fff">'+shortVal(b,metric)+'</text>';
    const top=Math.min(ya,yb,metric==='money'&&g>0?y(g):999);
    if(gp!=null)s+='<text class="v176-chart-growth" x="'+cx+'" y="'+Math.max(11,top-13)+'" text-anchor="middle" font-size="8" fill="'+(gp>=0?'#118a52':'#d92d20')+'">'+(gp>=0?'+':'')+gp.toFixed(1)+'% vs '+d.previous_year+'</text>';
    if(metric==='money'&&g>0){pts.push(cx+','+y(g));s+='<circle cx="'+cx+'" cy="'+y(g)+'" r="3" fill="#ec007c"/>';if(mp!=null)s+='<text x="'+cx+'" y="'+Math.max(20,y(g)-4)+'" text-anchor="middle" font-size="7" font-weight="900" fill="#b00063">'+mp.toFixed(1)+'% Meta</text>'}
    const lab=String(r.label||r.store||'').length>13?String(r.label||r.store).slice(0,12)+'…':String(r.label||r.store||'');
    s+='<text x="'+cx+'" y="'+(H-20)+'" text-anchor="middle" font-size="8" fill="#52657c">'+esc(lab)+'</text>';
  });
  if(metric==='money'&&pts.length>1)s+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="#ec007c" stroke-width="2.5"/>';
  host.innerHTML=s+'</svg>';
}
function sortRows(rows){
  if(!salesSort.key)return rows;
  return [...rows].sort((a,b)=>{
    const av=a[salesSort.key],bv=b[salesSort.key];
    if(av==null&&bv==null)return 0;if(av==null)return 1;if(bv==null)return-1;
    return (n(av)-n(bv))*salesSort.dir;
  });
}
function sortButton(key,label){
  const mark=salesSort.key===key?(salesSort.dir>0?' ↑':' ↓'):' ↕';
  return '<button class="v176-sales-sort" data-v176-sort="'+key+'">'+label+mark+'</button>'
}
function bindSort(root,d){qa('[data-v176-sort]',root).forEach(b=>b.onclick=()=>{const k=b.dataset.v176Sort;salesSort.dir=salesSort.key===k?-salesSort.dir:-1;salesSort.key=k;renderSalesTables(d)})}
function renderSalesTables(d){
  const metric=salesMetric,monthSet=new Set(d.available_months||[]);
  let rows=(d.months||[]).filter(r=>monthSet.has(Number(r.month)));
  if(d.selected_month)rows=rows.filter(r=>Number(r.month)===Number(d.selected_month));
  rows=rows.map(r=>({...r,pct_goal:r.target?n(r.current)/n(r.target)*100:null,pct_previous:metric==='pieces'?r.pieces_growth:r.pct_previous}));
  rows=sortRows(rows);
  const table=q('#salesExecRows')?.closest('table'),head=table?.querySelector('thead tr');
  if(head)head.innerHTML='<th>Mes</th><th>Meta</th><th>Venta '+d.year+'</th><th>Venta '+d.previous_year+'</th><th>'+sortButton('pct_goal','% Meta')+'</th><th>'+sortButton('pct_previous','% vs '+d.previous_year)+'</th><th>Venta pzas</th>';
  q('#salesExecRows').innerHTML=rows.map(r=>{
    const cv=metric==='pieces'?nf(r.pieces):money(r.current),pv=metric==='pieces'?nf(r.pieces_previous):money(r.previous);
    return '<tr><td><b>'+esc(r.label)+'</b></td><td>'+money(r.target)+'</td><td><b>'+cv+'</b></td><td>'+pv+'</td><td class="'+tone(r.pct_goal,true)+'">'+pct(r.pct_goal)+'</td><td class="'+tone(r.pct_previous,false)+'">'+pct(r.pct_previous)+'</td><td>'+nf(r.pieces)+'</td></tr>'
  }).join('');
  bindSort(table,d);

  let box=q('#v168SalesStores');if(!box){box=document.createElement('div');box.id='v168SalesStores';q('#v109-sales-exec')?.append(box)}
  let stores=sortRows((d.stores||[]).map(r=>({...r,pct_previous:metric==='pieces'?r.pieces_growth:r.pct_previous})));
  const title=d.selected_month?'Venta por tienda · '+monthLong[d.selected_month-1]+' '+d.year:'Venta por tienda · acumulado meses cargados';
  box.innerHTML='<div class="title">'+title+'</div><div class="tablewrap"><table class="table v168-sales-rank v176-sales-rank"><thead><tr><th>#</th><th>Tienda</th><th>Meta</th><th>Venta '+d.year+'</th><th>Venta '+d.previous_year+'</th><th>'+sortButton('pct_goal','% Meta')+'</th><th>'+sortButton('pct_previous','% vs '+d.previous_year)+'</th></tr></thead><tbody>'+stores.map((r,i)=>{
    const cv=metric==='pieces'?nf(r.pieces):money(r.current),pv=metric==='pieces'?nf(r.pieces_previous):money(r.previous);
    return '<tr><td>#'+(i+1)+'</td><td><b>'+esc(r.store)+'</b></td><td>'+money(r.target)+'</td><td><b>'+cv+'</b></td><td>'+pv+'</td><td class="'+(n(r.pct_goal)>=100?'v176-pos':'v176-neg')+'">'+pct(r.pct_goal)+'</td><td class="'+(n(r.pct_previous)>=0?'v176-pos':'v176-neg')+'">'+pct(r.pct_previous)+'</td></tr>'
  }).join('')+'</tbody></table></div>';
  bindSort(box,d);
}
function prepareSalesControls(d){
  const ms=q('#salesExecThrough'),ys=q('#salesExecYear');
  if(ys){
    const cur=String(d.year);ys.innerHTML=(d.available_years||[d.year]).map(y=>'<option value="'+y+'" '+(String(y)===cur?'selected':'')+'>'+y+'</option>').join('');ys.value=cur
  }
  if(ms){
    const opts=['<option value="0">Todos los meses</option>'].concat((d.available_months||[]).map(m=>'<option value="'+m+'">'+monthLong[m-1]+'</option>'));
    ms.innerHTML=opts.join('');ms.value=String(d.selected_month||0);
    const label=ms.closest('label');if(label){const first=[...label.childNodes].find(x=>x.nodeType===3);if(first)first.textContent='Mes';}
  }
  const controls=q('.sales-exec-controls');let met=q('#v176SalesMetric');
  if(controls&&!met){met=document.createElement('div');met.id='v176SalesMetric';met.className='v176-sales-metric';met.innerHTML='<button type="button" data-sales-metric="money">Pesos</button><button type="button" data-sales-metric="pieces">Piezas</button>';controls.insertBefore(met,q('#salesGoalsToggle'))}
  qa('[data-sales-metric]',met||document).forEach(b=>{b.classList.toggle('active',b.dataset.salesMetric===salesMetric);b.onclick=()=>{salesMetric=b.dataset.salesMetric;renderSales176(window.__V176_SALES_DATA,true)}})
}
function detachOldSalesListeners(){
  ['salesExecYear','salesExecThrough'].forEach(id=>{
    const old=q('#'+id);if(!old||old.dataset.v176clone)return;
    const c=old.cloneNode(true);c.dataset.v176clone='1';c.dataset.v168='1';old.replaceWith(c);
    c.addEventListener('change',()=>{
      if(id==='salesExecThrough')salesMonth=Number(c.value||0);
      renderSales176(null,true);
    });
  });
}
async function renderSales176(existing,force){
  if(!macroActive()||salesBusy)return;
  salesBusy=true;
  try{
    const ys=q('#salesExecYear'),store=visibleStoreControl()?.value||q('#store')?.value||'Compañía',year=Number(ys?.value||2026);
    const d=existing&&force?existing:await A('/api/commercial-sales-v176?year='+year+'&month='+salesMonth+'&store='+encodeURIComponent(store),{timeoutMs:180000});
    window.__V176_SALES_DATA=d;salesMonth=Number(d.selected_month||0);
    prepareSalesControls(d);
    const t=d.totals||{},gap=n(t.gap_to_goal);
    const kpi=(l,v,s,c,cl)=>'<div class="sales-kpi" style="--sk:'+c+'"><div class="sl">'+l+'</div><div class="sv '+(cl||'')+'">'+v+'</div><div class="ss">'+s+'</div></div>';
    q('#salesExecKpis').innerHTML=
      kpi('Meta acumulada',money(t.target),gap>=0?'Meta superada por '+money(gap):'Brecha '+money(Math.abs(gap)),'#ec007c')+
      kpi('Venta '+d.year,money(t.current),d.selected_month?monthLong[d.selected_month-1]:'Meses con PDF','#1769e8')+
      kpi('Venta '+d.previous_year,money(t.previous),'Mismo alcance','#9fb0c6')+
      kpi('Cumplimiento',pct(t.compliance),'Venta / Meta','#10b981',tone(t.compliance,true))+
      kpi('Crecimiento',pct(t.growth),d.year+' vs '+d.previous_year,'#f59e0b',tone(t.growth,false));
    q('#salesExecSource').textContent=d.source_label+' · '+d.store;
    q('#salesChartTitle').textContent=d.selected_month?'Venta por tienda · '+monthLong[d.selected_month-1]+' '+d.year:'Venta mensual '+d.year+' vs '+d.previous_year+' · '+d.store;
    q('#salesCoverage').textContent=(d.available_months||[]).length+' PDF/mes disponibles'+(d.cut_date?' · último corte '+d.cut_date:'');
    salesChart176(d);renderSalesTables(d);
  }catch(e){console.warn('[V176] ventas',e);if(q('#salesExecSource'))q('#salesExecSource').textContent='Ventas: '+(e.message||e)}
  finally{salesBusy=false}
}

function refreshAll(){
  fixSidebar();fixAnalysisNav();
  if(!activeAnalysis())return;
  fixStores();
  if(macroActive()){
    renderExcess();renderArea();renderModels();
    setTimeout(()=>{detachOldSalesListeners();renderSales176()},80);
  }
}
function schedule(){
  [20,180,520,1150].forEach(ms=>setTimeout(refreshAll,ms));
}
document.addEventListener('click',e=>{
  if(e.target.closest?.('#analysisNav,[data-main="analysis"],[data-area-section],[data-area-group],[data-pareto-group],#refresh,#sidebarToggle'))schedule();
  if(e.target.closest?.('[data-area-section],[data-area-group]'))setTimeout(renderArea,80);
  if(e.target.closest?.('[data-pareto-group]'))setTimeout(()=>renderModels(true),80);
},true);
document.addEventListener('change',e=>{
  if(e.target.matches?.('#store,#week,#section,#catalog,#v166StatusSelect'))schedule();
},true);
if(typeof window.loadDash==='function'&&!window.loadDash.__v176){
  const old=window.loadDash;const wrapped=async function(){const r=await old.apply(this,arguments);setTimeout(refreshAll,40);return r};wrapped.__v176=true;window.loadDash=wrapped;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
console.info('[V176] Comercial integral activo.');
})();
</script>'''

    @m.app.middleware("http")
    async def v176_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v176-commercial-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v176-commercial-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache", "Expires": "0",
                "X-Operations-UI-Version": "V176",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V176_COMMERCIAL_INTEGRAL = True
    print("[V176] sidebar, tiendas, excedente, ventas, ubicación y modelos instalados.", flush=True)
