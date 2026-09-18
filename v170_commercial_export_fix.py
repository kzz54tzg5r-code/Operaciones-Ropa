"""V170 · Correcciones integradas solicitadas el 18/09/2026.

- Una sola consulta/caché para Macro 80/20, modelos lentos y sugerido 0–1.
- En alcance Compañía no se selecciona una tienda implícita ni se muestra checklist.
- Ventas reutiliza el motor reparado V166/V167 (enero, año anterior y fallback
  de capacidades) y agrega el acumulado por tienda de los OCR disponibles.
- Exportación PDF serializada y con endpoint estable para evitar solicitudes
  concurrentes que agotaban el proceso de Render.
"""
from __future__ import annotations

import asyncio
import inspect
import math
import re
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from fastapi.responses import Response


def install(m):
    if getattr(m, "_V170_COMMERCIAL_EXPORT_FIX", False):
        return

    model_cache = {}
    model_lock = threading.RLock()
    export_lock = asyncio.Lock()

    def num(value):
        try:
            out = float(value or 0)
            return out if math.isfinite(out) else 0.0
        except Exception:
            return 0.0

    def norm(value):
        import unicodedata
        text = unicodedata.normalize("NFKD", str(value or ""))
        return " ".join("".join(c for c in text if not unicodedata.combining(c)).casefold().split())

    def route_endpoint(path, method="GET"):
        candidates = [r for r in m.app.router.routes if getattr(r, "path", None) == path and method in (getattr(r, "methods", set()) or set())]
        return candidates[-1].endpoint if candidates else None

    @m.app.get("/api/commercial-models-v170")
    def commercial_models_v170(
        request: Request, week: str = "", store: str = "Compañía",
        section: str = "Todas", catalog: str = "Todos",
    ):
        actor = m.require_user(request)
        selected = str(m.effective_store(actor, store) or "Compañía")
        key = (week, norm(selected), norm(section), norm(catalog))
        now = time.monotonic()
        with model_lock:
            cached = model_cache.get(key)
            if cached and now - cached[0] < 600:
                return cached[1]
            payload = {
                "week": week, "store": selected, "section": section, "catalog": catalog,
                "champions": list(m._capacity_model_rows(selected, section, "80_20", week, catalog) or []),
                "slow": list(m._capacity_model_rows(selected, section, "slow", week, catalog) or []),
                "zero": list(m._capacity_model_rows(selected, section, "suggested_zero", week, catalog) or []),
                "checklist_enabled": selected != "Compañía",
            }
            if len(model_cache) >= 24:
                model_cache.pop(next(iter(model_cache)))
            model_cache[key] = (now, payload)
            return payload

    base_sales = route_endpoint("/api/commercial-sales-summary")

    @m.app.get("/api/commercial-sales-v170")
    async def commercial_sales_v170(
        request: Request, year: int | None = None,
        through_month: int | None = None, store: str = "Compañía",
    ):
        actor = m.require_user(request)
        yy = int(year or m.datetime.now().year)
        cut = max(1, min(12, int(through_month or m.datetime.now().month)))
        scope = str(m.effective_store(actor, store) or "Compañía")
        if base_sales is None:
            raise HTTPException(500, "Motor de ventas no disponible")
        result = base_sales(request=request, year=yy, through_month=cut, store=scope)
        if inspect.isawaitable(result):
            result = await result
        result = dict(result or {})
        months = [dict(x) for x in (result.get("months") or [])]
        for row in months:
            row.setdefault("source", f"{int(row.get('sources') or 0)} PDF" if row.get("sources") else "—")
            row.setdefault("compliance", row.get("compliance_pct"))
            row.setdefault("growth", row.get("growth_pct"))
        totals0 = dict(result.get("totals") or {})
        current = num(totals0.get("current_ytd", totals0.get("current")))
        previous = num(totals0.get("previous_ytd", totals0.get("previous")))
        target = num(totals0.get("goal_ytd", totals0.get("target")))

        # Acumulado por tienda: suma cada PDF mensual válido hasta el corte.
        stores = defaultdict(lambda: {"current": 0.0, "previous": 0.0, "target": 0.0, "months": 0})
        if scope == "Compañía" and hasattr(m, "ocr_for_entry"):
            entries = list((m.load_manifest() or {}).get("sales") or [])
            latest = {}
            for raw in entries:
                entry = dict(raw); y = int(entry.get("year") or 0); mo = int(entry.get("month") or 0)
                if y != yy or not (1 <= mo <= cut):
                    continue
                old = latest.get(mo)
                if old is None or str(entry.get("uploaded_at") or "") >= str(old.get("uploaded_at") or ""):
                    latest[mo] = entry
            for mo, entry in latest.items():
                try:
                    payload = m.ocr_for_entry(entry) or {}
                except Exception:
                    payload = {}
                for name, row in (payload.get("stores") or {}).items():
                    target_row = stores[str(name)]
                    target_row["current"] += num(row.get("current"))
                    target_row["previous"] += num(row.get("previous"))
                    target_row["target"] += num(row.get("target"))
                    target_row["months"] += 1
        store_rows = []
        for name, row in stores.items():
            cur, prev, goal = row["current"], row["previous"], row["target"]
            store_rows.append({"store": name, **row, "diff_goal": cur-goal if goal else None,
                "pct_goal": cur/goal*100 if goal else None,
                "diff_previous": cur-prev if prev else None,
                "pct_previous": (cur/prev-1)*100 if prev else None})
        store_rows.sort(key=lambda x: (-num(x.get("current")), norm(x.get("store"))))
        for rank, row in enumerate(store_rows, 1): row["rank"] = rank

        return {**result, "year": yy, "previous_year": yy-1, "through_month": cut,
            "store": scope, "months": months, "stores": store_rows,
            "totals": {"current": current, "previous": previous, "target": target,
                "compliance": current/target*100 if target else None,
                "growth": (current/previous-1)*100 if previous else None},
            "source_label": "PDF de ventas + respaldo histórico validado",
            "source_count": int(result.get("source_count") or sum(int(x.get("sources") or 0) for x in months[:cut])),
        }

    old_export = route_endpoint("/api/export/operations/project-scope-v151")

    @m.app.get("/api/export/operations-v170")
    async def export_operations_v170(
        request: Request, format: str = "pdf", report: str = "Centro Ejecutivo",
        store: str = "Compañía", period_type: str = "all", period_value: str = "",
        area: str = "", activity: str = "", start_date: str = "", end_date: str = "",
    ):
        if old_export is None:
            raise HTTPException(500, "Exportador no disponible")
        async with export_lock:
            result = old_export(request=request, format=format, report=report, store=store,
                period_type=period_type, period_value=period_value, area=area, activity=activity,
                start_date=start_date, end_date=end_date)
            if inspect.isawaitable(result): result = await result
            if not isinstance(result, Response) or int(getattr(result, "status_code", 500)) >= 400:
                raise HTTPException(500, "No fue posible construir el reporte")
            return result

    # Exponer el OCR para que el endpoint V170 lo reutilice sin duplicar parser.
    try:
        import v168_backend_patch as v168
        # ocr_for_entry es local en V168; se recupera del closure de su endpoint.
        endpoint = route_endpoint("/api/commercial-sales-v168")
        if endpoint:
            for cell in (endpoint.__closure__ or ()):
                value = cell.cell_contents
                if callable(value) and getattr(value, "__name__", "") == "ocr_for_entry":
                    m.ocr_for_entry = value; break
    except Exception:
        pass

    css = r'''<style id="v170-commercial-fix-css">
/* Un solo lenguaje visual y sin filtros de sección duplicados: manda la barra superior. */
#v166ChampionFilter,#v166SlowFilter,#v166ZeroFilter,#v166MacroSectionFilter,
#champSectionSwitch,[data-v166-for="champSection"],[data-v166-for="slowSection"],[data-v166-for="zeroSection"]{display:none!important}
#page-macro .v168-filter-strip{grid-template-columns:repeat(auto-fit,minmax(115px,1fr))!important;max-width:none!important}
#page-macro .v168-filter-strip button{min-height:42px!important;width:auto!important;margin:0!important}
body.v170-company-models #checklistStoreWrap{display:none!important}
body.v170-company-models .tablewrap:has(#slowTable) tr>*:nth-child(n+11),
body.v170-company-models .tablewrap:has(#zeroTable) tr>*:nth-child(n+12){display:none!important}
body.v170-company-models #slowTable{min-width:820px!important}body.v170-company-models #zeroTable{min-width:900px!important}
.v170-load-note{color:#5e718c;font-weight:750}
</style>'''

    js = r'''<script id="v170-commercial-fix-js">
(function(){
const $=s=>document.querySelector(s), escv=v=>encodeURIComponent(v==null?'':v);

// Todas las lecturas de venta y exportaciones pasan por las rutas corregidas.
const priorFetch=window.fetch.bind(window);
window.fetch=function(input,init){
  try{
    let raw=typeof input==='string'?input:(input?.url||'');
    if(raw.includes('/api/commercial-sales-v168')) raw=raw.replace('/api/commercial-sales-v168','/api/commercial-sales-v170');
    if(raw.includes('/api/export/operations/project-scope-v151')) raw=raw.replace('/api/export/operations/project-scope-v151','/api/export/operations-v170');
    if(typeof input==='string') input=raw; else if(raw!==input?.url) input=new Request(raw,input);
  }catch(_){ }
  return priorFetch(input,init);
};

window.loadModelTables=async function(){
  if(!window.DASH)return;
  const company=(DASH.selected_store||'Compañía')==='Compañía';
  const scope=company?'Compañía':DASH.selected_store;
  document.body.classList.toggle('v170-company-models',company);
  const section=$('#section')?.value||'Todas', cat=$('#catalog')?.value||'Todos', week=$('#week')?.value||'';
  if($('#champTable'))$('#champTable').innerHTML='<tr><td colspan="16" class="v170-load-note">Cargando 80/20…</td></tr>';
  if($('#slowTable'))$('#slowTable').innerHTML='<tr><td colspan="15" class="v170-load-note">Cargando modelos lentos…</td></tr>';
  if($('#zeroTable'))$('#zeroTable').innerHTML='<tr><td colspan="16" class="v170-load-note">Cargando sugerido 0 a 1…</td></tr>';
  try{
    const d=await api(`/api/commercial-models-v170?week=${escv(week)}&store=${escv(scope)}&section=${escv(section)}&catalog=${escv(cat)}`,{timeoutMs:240000});
    let ck={rows:[],editable:false},target='';
    if(!company){
      target=scope;
      ck=await api(`/api/model-checklist?week=${escv(week)}&store=${escv(target)}`,{timeoutMs:60000});
    }
    const map={};(ck.rows||[]).forEach(r=>map[String(r.id_art)]=r);
    renderModelRows(d.champions||[],d.slow||[],d.zero||[],section,section,scope,map,!!ck.editable,target,scope);
    $('#checklistStoreWrap')?.classList.add('hidden');
    if(!company&&ck.editable){
      const unique=new Map();[...(d.slow||[]),...(d.zero||[])].forEach(r=>unique.set(String(r.id_art),{id_art:r.id_art,model:r.model,section:r.section,rubro:r.rubro}));
      try{await api('/api/model-checklist/scope',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({week,store:target,models:[...unique.values()]})})}catch(_){ }
    }
    await loadParetoSummary();
    await loadChecklistSummary();
  }catch(e){
    const msg='No fue posible cargar la información: '+(e.message||e);
    if($('#champTable'))$('#champTable').innerHTML='<tr><td colspan="16">'+msg+'</td></tr>';
    if($('#slowTable'))$('#slowTable').innerHTML='<tr><td colspan="15">'+msg+'</td></tr>';
    if($('#zeroTable'))$('#zeroTable').innerHTML='<tr><td colspan="16">'+msg+'</td></tr>';
  }
};

function unify(){
  const top=$('#section')?.value||'Todas';
  ['champSection','slowSection'].forEach(id=>{const x=$('#'+id);if(x)x.value=top});
  const company=($('#store')?.value||'Compañía')==='Compañía';document.body.classList.toggle('v170-company-models',company);
}
document.addEventListener('change',e=>{if(e.target.matches?.('#section,#store,#week,#catalog,#v166StatusSelect'))setTimeout(()=>{unify();window.loadModelTables?.()},0)},true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',unify);else unify();
console.info('[V170] alcance Compañía, ventas, filtros y descargas corregidos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v170_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator: body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v170-commercial-fix-css" not in html: html = html.replace("</head>", css + "</head>", 1)
            if "v170-commercial-fix-js" not in html: html = html.replace("</body>", js + "</body>", 1)
            headers = dict(response.headers); headers.pop("content-length", None)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V170_COMMERCIAL_EXPORT_FIX = True
    print("[V170] ventas, modelos, filtros y exportación estable instalados.", flush=True)
