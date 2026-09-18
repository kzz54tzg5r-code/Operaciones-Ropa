"""V174 · Regreso al diseño móvil anterior + reparación de ventas.

- Desactiva la transformación móvil tipo tarjetas de V173 (V174 se instala sin V173).
- Mantiene el diseño de escritorio, reducido proporcionalmente en móvil.
- Repara año/mes del PDF desde el título "Meta de Ventas <Mes> <Año>".
- Prioriza Meta y Año anterior leídos del PDF/OCR sobre metas manuales incoherentes.
- Para Compañía, valida los totales OCR contra la suma de tiendas.
- Recupera enero cuando el PDF existe pero quedó registrado en un mes incorrecto.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import inspect
import math
import re
import unicodedata

from fastapi import HTTPException, Request


MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}
LABELS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]


def install(m):
    if getattr(m, "_V174_MOBILE_SALES_REPAIR", False):
        return

    def num(value):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def norm(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.casefold().split())

    def is_company(value):
        return norm(value) in ("", "compania", "company")

    def route_endpoint(path, method="GET"):
        rows = [
            r for r in m.app.router.routes
            if getattr(r, "path", None) == path and method in (getattr(r, "methods", set()) or set())
        ]
        return rows[-1].endpoint if rows else None

    # Recupera el OCR V168 si V170 no logró exponerlo.
    if not callable(getattr(m, "ocr_for_entry", None)):
        endpoint = route_endpoint("/api/commercial-sales-v168")
        if endpoint:
            try:
                for cell in endpoint.__closure__ or ():
                    value = cell.cell_contents
                    if callable(value) and getattr(value, "__name__", "") == "ocr_for_entry":
                        m.ocr_for_entry = value
                        break
            except Exception:
                pass

    period_cache = {}

    def detect_period(entry):
        path = m.resolve_entry_path(entry)
        if not path.exists() or path.suffix.lower() != ".pdf":
            return None
        try:
            stamp = path.stat().st_mtime_ns
        except Exception:
            stamp = 0
        key = (str(path), stamp)
        if key in period_cache:
            return period_cache[key]
        found = None
        try:
            import pdfplumber
            chunks = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages[:2]:
                    try:
                        chunks.append(page.extract_text(x_tolerance=2, y_tolerance=3) or "")
                    except TypeError:
                        chunks.append(page.extract_text() or "")
            text = norm("\n".join(chunks))
            names = "|".join(sorted(MONTHS, key=len, reverse=True))
            mt = re.search(rf"meta\s+de\s+ventas?\s+({names})\s+(20\d{{2}})", text, re.I)
            if not mt:
                mt = re.search(rf"\b({names})\s+(20\d{{2}})\b", text, re.I)
            if mt:
                found = (int(mt.group(2)), MONTHS[norm(mt.group(1))])
        except Exception as exc:
            print(f"[V174-PERIOD] {type(exc).__name__}: {exc}", flush=True)
        period_cache[key] = found
        return found

    def sales_entries_reconciled():
        out = []
        changes = 0
        for raw in list((m.load_manifest() or {}).get("sales") or []):
            item = dict(raw)
            try:
                detected = detect_period(item)
                if detected:
                    yy, mo = detected
                    if int(item.get("year") or 0) != yy or int(item.get("month") or 0) != mo:
                        update = {"year": yy, "month": mo, "period_reconciled_by": "V174"}
                        try:
                            m.update_entry("sales", str(item.get("id") or ""), **update)
                            item.update(update)
                            changes += 1
                        except Exception as exc:
                            print(f"[V174-PERIOD] no se pudo actualizar: {type(exc).__name__}: {exc}", flush=True)
            except Exception:
                pass
            yy = int(item.get("year") or 0)
            mo = int(item.get("month") or 0)
            path = m.resolve_entry_path(item)
            if yy > 0 and mo in range(1, 13) and path.exists() and path.suffix.lower() == ".pdf":
                out.append(item)
        counts = Counter((int(e.get("year") or 0), int(e.get("month") or 0)) for e in out)
        summary = ",".join(f"{y}-{mo:02d}x{cnt}" for (y, mo), cnt in sorted(counts.items()))
        print(f"[V174-SALES-MAP] {summary or 'sin PDF'} · corregidos={changes}", flush=True)
        return out

    # Reconciliar enero/meses desde el título al arrancar.
    try:
        _V174_ENTRIES = sales_entries_reconciled()
    except Exception as exc:
        print(f"[V174-SALES-MAP] {type(exc).__name__}: {exc}", flush=True)
        _V174_ENTRIES = []

    def entries():
        # Releer manifiesto para recoger cargas posteriores al arranque.
        return sales_entries_reconciled()

    def latest_index(rows):
        latest = {}
        for e in rows:
            key = (int(e.get("year") or 0), int(e.get("month") or 0), norm(e.get("store") or "Compañía"))
            old = latest.get(key)
            if old is None or str(e.get("uploaded_at") or "") >= str(old.get("uploaded_at") or ""):
                latest[key] = e
        return latest

    def choose_entries(latest, year, month, scope):
        vals = [e for (yy, mo, _), e in latest.items() if yy == year and mo == month]
        if scope != "Compañía":
            direct = [e for e in vals if norm(e.get("store")) == norm(scope)]
            return direct
        company = [e for e in vals if is_company(e.get("store"))]
        return company if company else vals

    def plausible(value, reference, low=.20, high=3.0):
        value = num(value); reference = num(reference)
        if value <= 0:
            return False
        if reference <= 0:
            return value >= 100000
        ratio = value / reference
        return low <= ratio <= high

    def ocr_payload(entry):
        fn = getattr(m, "ocr_for_entry", None)
        if not callable(fn):
            return {}
        try:
            return dict(fn(entry) or {})
        except Exception as exc:
            print(f"[V174-OCR] {type(exc).__name__}: {exc}", flush=True)
            return {}

    def store_row(payload, scope):
        rows = payload.get("stores") or {}
        for name, row in rows.items():
            if norm(name) == norm(scope):
                return dict(row or {})
        return {}

    def company_from_payload(payload, entry):
        comp = dict(payload.get("company") or {})
        stores = [dict(x or {}) for x in (payload.get("stores") or {}).values()]
        usable = [x for x in stores if any(num(x.get(k)) > 0 for k in ("current","previous","target"))]

        def field(name, entry_key):
            company_value = num(comp.get(name))
            summed = sum(num(x.get(name)) for x in usable)
            # Si hay suficientes tiendas, la suma es la validación más estable del total.
            if len(usable) >= 10 and summed > 0:
                if company_value <= 0 or not plausible(company_value, summed, .72, 1.28):
                    company_value = summed
            stored = num(entry.get(entry_key))
            if name == "current":
                if stored > 0 and (company_value <= 0 or plausible(stored, company_value, .70, 1.35)):
                    return stored
                return company_value or stored
            # Para meta/año anterior rechazar valores con escala absurda.
            if company_value > 0:
                return company_value
            return stored

        current = field("current", "total_sales")
        previous = field("previous", "previous_sales")
        target = field("target", "target_sales")
        pieces = num(comp.get("pieces"))
        if len(usable) >= 10 and pieces <= 0:
            pieces = sum(num(x.get("pieces")) for x in usable)
        return {
            "current": current, "previous": previous, "target": target, "pieces": pieces,
            "store_count": len(usable), "stores": payload.get("stores") or {},
            "cut_date": str(payload.get("cut_date") or ""),
        }

    def values_from_entry(entry, scope):
        if not entry:
            return {"current":0.0,"previous":0.0,"target":0.0,"pieces":0.0,"stores":{},"cut_date":""}
        payload = ocr_payload(entry)
        if scope == "Compañía":
            return company_from_payload(payload, entry)
        row = store_row(payload, scope)
        current = num(row.get("current"))
        previous = num(row.get("previous"))
        target = num(row.get("target"))
        pieces = num(row.get("pieces"))
        # Un PDF específico por tienda puede venir guardado directamente en el manifiesto.
        if not current and norm(entry.get("store")) == norm(scope):
            current = num(entry.get("total_sales"))
            previous = previous or num(entry.get("previous_sales"))
            target = target or num(entry.get("target_sales"))
            pieces = pieces or num(entry.get("total_pieces"))
        return {"current":current,"previous":previous,"target":target,"pieces":pieces,"stores":payload.get("stores") or {},"cut_date":str(payload.get("cut_date") or "")}

    def capacity_fallback(year, month, scope):
        try:
            from v112_sales_pdf_repair import _capacity_month_fallback
            return _capacity_month_fallback(m, year, month, scope)
        except Exception:
            return (0.0, 0.0, "")

    # Verificación de arranque sobre las fuentes reales ya publicadas. No inventa
    # valores: sólo registra lo que el OCR/historial pudo reconciliar por mes.
    try:
        for _entry in _V174_ENTRIES:
            _yy = int(_entry.get("year") or 0); _mo = int(_entry.get("month") or 0)
            _v = values_from_entry(_entry, "Compañía")
            print(
                f"[V174-SALES-CHECK] {_yy}-{_mo:02d} "
                f"actual={num(_v.get('current')):.0f} "
                f"prev={num(_v.get('previous')):.0f} "
                f"meta={num(_v.get('target')):.0f} "
                f"tiendas={len(_v.get('stores') or {})}",
                flush=True,
            )
    except Exception as exc:
        print(f"[V174-SALES-CHECK] {type(exc).__name__}: {exc}", flush=True)

    @m.app.get("/api/commercial-sales-v174")
    async def commercial_sales_v174(
        request: Request, year: int | None = None,
        through_month: int | None = None, store: str = "Compañía",
    ):
        actor = m.require_user(request)
        yy = int(year or datetime.now().year)
        cut = max(1, min(12, int(through_month or datetime.now().month)))
        try:
            scope = str(m.effective_store(actor, store) or "Compañía")
        except Exception:
            scope = str(store or "Compañía")
        if is_company(scope):
            scope = "Compañía"

        rows = entries()
        latest = latest_index(rows)

        with m.db() as con:
            try:
                goal_rows = con.execute(
                    "SELECT month,target FROM sales_goals WHERE year=? AND store=?",
                    (yy, scope),
                ).fetchall()
                manual = {int(r["month"]): num(r["target"]) for r in goal_rows}
            except Exception:
                manual = {}

        months = []
        source_count = 0
        latest_cut = ""
        latest_upload = ""
        store_acc = defaultdict(lambda: {"current":0.0,"previous":0.0,"target":0.0,"months":0})

        for mo in range(1, 13):
            cur_entries = choose_entries(latest, yy, mo, scope)
            cur_entry = max(cur_entries, key=lambda e: str(e.get("uploaded_at") or ""), default=None)
            val = values_from_entry(cur_entry, scope)

            current = num(val.get("current"))
            previous = num(val.get("previous"))
            target_pdf = num(val.get("target"))
            pieces = num(val.get("pieces"))
            source_parts = []

            # Histórico explícito del año pasado si existe.
            prev_entries = choose_entries(latest, yy-1, mo, scope)
            prev_entry = max(prev_entries, key=lambda e: str(e.get("uploaded_at") or ""), default=None)
            if prev_entry:
                pv = values_from_entry(prev_entry, scope)
                hist = num(pv.get("current"))
                if hist > 0:
                    previous = hist
                    source_parts.append("histórico")

            if current <= 0:
                cs, cp, _src = capacity_fallback(yy, mo, scope)
                if num(cs) > 0:
                    current = num(cs); pieces = pieces or num(cp); source_parts.append("respaldo venta")
            if previous <= 0:
                ps, _pp, _src = capacity_fallback(yy-1, mo, scope)
                if num(ps) > 0:
                    previous = num(ps); source_parts.append("respaldo año anterior")

            # Meta: PDF primero. La meta manual sólo se usa si el PDF no dio una cifra coherente.
            ref = current or previous
            target = target_pdf if plausible(target_pdf, ref, .30, 2.25) else 0.0
            manual_goal = num(manual.get(mo))
            if target <= 0 and plausible(manual_goal, ref, .30, 2.25):
                target = manual_goal
                source_parts.append("meta manual")
            elif target > 0:
                source_parts.append("meta PDF")

            # Año anterior también debe estar en una escala razonable respecto a la venta actual.
            if previous > 0 and current > 0 and not plausible(previous, current, .20, 3.0):
                # Si OCR produjo una cifra absurda, no mostrarla como válida.
                previous = 0.0
                ps, _pp, _src = capacity_fallback(yy-1, mo, scope)
                if plausible(ps, current, .20, 3.0):
                    previous = num(ps); source_parts.append("año anterior respaldo")

            if cur_entry:
                source_parts.insert(0, "PDF")
                latest_upload = max(latest_upload, str(cur_entry.get("uploaded_at") or ""))
            latest_cut = str(val.get("cut_date") or latest_cut)
            valid = current > 0 or previous > 0 or target > 0
            if valid:
                source_count += 1

            months.append({
                "month": mo, "label": LABELS[mo-1], "current": current, "previous": previous,
                "target": target, "pieces": pieces,
                "compliance": current/target*100 if target else None,
                "growth": (current/previous-1)*100 if previous else None,
                "diff_goal": current-target if target else None,
                "diff_previous": current-previous if previous else None,
                "source": " · ".join(dict.fromkeys(source_parts)) if source_parts else "—",
                "sources": 1 if cur_entry and current > 0 else 0,
            })

            # Acumulado por tienda a partir del OCR del PDF mensual actual.
            if scope == "Compañía" and cur_entry:
                payload = ocr_payload(cur_entry)
                for name, sr in (payload.get("stores") or {}).items():
                    x = store_acc[str(name)]
                    c = num(sr.get("current")); p = num(sr.get("previous")); g = num(sr.get("target"))
                    x["current"] += c
                    x["previous"] += p
                    if plausible(g, c or p, .30, 2.25):
                        x["target"] += g
                    x["months"] += 1

        use = months[:cut]
        total_current = sum(num(x["current"]) for x in use)
        total_previous = sum(num(x["previous"]) for x in use)
        total_target = sum(num(x["target"]) for x in use)

        store_rows = []
        for name, x in store_acc.items():
            cur, prev, goal = num(x["current"]), num(x["previous"]), num(x["target"])
            store_rows.append({
                "store": name, **x,
                "diff_goal": cur-goal if goal else None,
                "pct_goal": cur/goal*100 if goal else None,
                "diff_previous": cur-prev if prev else None,
                "pct_previous": (cur/prev-1)*100 if prev else None,
            })
        store_rows.sort(key=lambda x: (-num(x.get("current")), norm(x.get("store"))))
        for rank, row in enumerate(store_rows, 1):
            row["rank"] = rank

        years = sorted({int(e.get("year") or 0) for e in rows if int(e.get("year") or 0)>0} | {yy, yy-1}, reverse=True)
        return {
            "year": yy, "previous_year": yy-1, "through_month": cut, "store": scope,
            "available_years": years, "months": months, "stores": store_rows,
            "totals": {
                "current": total_current, "previous": total_previous, "target": total_target,
                "current_ytd": total_current, "previous_ytd": total_previous, "goal_ytd": total_target,
                "compliance": total_current/total_target*100 if total_target else None,
                "compliance_pct": total_current/total_target*100 if total_target else None,
                "growth": (total_current/total_previous-1)*100 if total_previous else None,
                "growth_pct": (total_current/total_previous-1)*100 if total_previous else None,
                "gap_to_goal": total_current-total_target if total_target else None,
            },
            "source_count": source_count, "last_upload": latest_upload, "cut_date": latest_cut,
            "has_sales": any(num(x["current"])>0 or num(x["previous"])>0 for x in use),
            "editable": str(actor.get("role") or "") in ("superadmin","admin"),
            "source_label": "PDF mensual · Meta/Año anterior validados contra OCR por tienda · V174",
        }

    css = r'''<style id="v174-mobile-desktop-like-css">
/* Regreso al diseño anterior: no se crean tarjetas adicionales ni se cambia la estructura. */
@media(max-width:900px){
  .main{padding:5px 6px calc(74px + env(safe-area-inset-bottom))!important}
  .hero{min-height:52px!important;padding:8px 9px!important}.hero h1{font-size:16px!important}.hero p{font-size:7.5px!important}
  .title{font-size:16px!important;margin:9px 1px 5px!important}.subtitle{font-size:7.7px!important;line-height:1.3!important}

  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important;margin:5px 0 7px!important
  }
  .kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi,.v164-matrix-kpi,.v165-mini-kpi,.v168-plan-kpi,.sales-kpi{
    min-height:84px!important;padding:8px 6px 7px 38px!important;border-radius:10px!important
  }
  .lab,.report-kpi .rk-label,.v149-kpi small,.v126-kpi small,.v125-kpi small,.sales-kpi .sl{font-size:6.8px!important;line-height:1.15!important}
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b,.sales-kpi .sv{
    font-size:clamp(17px,4.6vw,20px)!important;line-height:1!important;margin:5px 0 3px!important;letter-spacing:-.04em!important
  }
  .sales-kpi .sv{font-size:clamp(15px,4.2vw,18px)!important;letter-spacing:-.045em!important}
  .note,.report-kpi .rk-sub,.v149-kpi span,.v126-kpi span,.v125-kpi span,.sales-kpi .ss{font-size:7px!important;line-height:1.2!important}

  .sales-exec{padding:7px!important;margin:9px 0 12px!important;border-radius:11px!important}
  .sales-chart-card{padding:8px!important;margin:7px 0!important}
  .sales-chart-head{font-size:9px!important;align-items:flex-start!important}
  .sales-chart-head span{font-size:6.5px!important}
  .sales-legend{font-size:6.8px!important;margin:6px 0!important;gap:10px!important}
  .sales-chart-scroll{overflow:hidden!important;width:100%!important}
  .sales-chart-scroll svg,#salesExecChart svg{min-width:0!important;width:100%!important;max-width:100%!important;height:auto!important;display:block!important}

  .sales-month-table .table{min-width:650px!important}
  .table{font-size:7.7px!important;min-width:680px!important}.table th{font-size:7.1px!important;padding:7px 6px!important}.table td{font-size:7.7px!important;padding:6px!important}

  .mobile{min-height:62px!important;padding:4px 4px calc(4px + env(safe-area-inset-bottom))!important}
  .mnav{min-height:49px!important;font-size:7px!important;padding:4px 1px!important}.mnav-icon{font-size:17px!important;line-height:18px!important}
}
</style>'''

    js = r'''<script id="v174-sales-route-js">
(function(){
  if(window.__V174_SALES_ROUTE)return;window.__V174_SALES_ROUTE=true;
  const previous=window.fetch.bind(window);
  window.fetch=function(input,init){
    try{
      let raw=typeof input==='string'?input:(input?.url||'');
      if(raw.includes('/api/commercial-sales-v170')) raw=raw.replace('/api/commercial-sales-v170','/api/commercial-sales-v174');
      if(raw.includes('/api/commercial-sales-v168')) raw=raw.replace('/api/commercial-sales-v168','/api/commercial-sales-v174');
      if(typeof input==='string') input=raw; else if(raw!==input?.url) input=new Request(raw,input);
    }catch(_){}
    return previous(input,init);
  };
  console.info('[V174] ventas reparadas y diseño móvil anterior restaurado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v174_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v174-mobile-desktop-like-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v174-sales-route-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(response.headers); headers.pop("content-length", None)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V174_MOBILE_SALES_REPAIR = True
    print("[V174] diseño móvil anterior + ventas Meta/Año anterior/Enero instalados.", flush=True)
