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
import difflib
import inspect
import math
import re
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

    store_repair_cache = {}

    def targeted_store_ocr(entry, store_name):
        """OCR puntual de una fila sin alterar el caché/total corporativo V168."""
        if not entry:
            return {}
        key = (str(entry.get("id") or ""), norm(store_name))
        cached = store_repair_cache.get(key)
        if cached is not None:
            return dict(cached)
        wanted = "TOLUC" if norm(store_name) == norm("Toluca") else ("PUESU" if norm(store_name) == norm("Puebla Sur") else "")
        if not wanted:
            return {}
        result = {}
        try:
            import pdfplumber
            import pytesseract
            from pytesseract import Output
            path = m.resolve_entry_path(entry)
            if not path.exists():
                return {}
            with pdfplumber.open(path) as pdf:
                if not pdf.pages:
                    return {}
                image = pdf.pages[0].to_image(resolution=180).original
            w, h = image.size
            crop = image.crop((int(.03*w), int(.66*h), int(.97*w), int(.985*h)))
            df = pytesseract.image_to_data(crop, lang="eng", config="--psm 6", output_type=Output.DATAFRAME)
            try:
                df = df.dropna(subset=["text"])
            except Exception:
                pass
            tokens = []
            for _, rr in df.iterrows():
                txt = str(rr.get("text") or "").strip()
                if txt:
                    tokens.append({
                        "text": txt, "left": float(rr.get("left") or 0),
                        "top": float(rr.get("top") or 0), "width": float(rr.get("width") or 0),
                    })
            tokens.sort(key=lambda x: x["top"])
            groups = []
            for token in tokens:
                group = None
                for candidate in reversed(groups[-6:]):
                    if abs(candidate["top"] - token["top"]) <= 6:
                        group = candidate; break
                if group is None:
                    group = {"top": token["top"], "tokens": []}; groups.append(group)
                group["tokens"].append(token)

            cw = crop.size[0]
            def clean_code(value):
                return re.sub(r"[^A-Z]", "", str(value or "").upper().replace("1","I").replace("0","O"))
            def parse_token(value):
                raw = str(value or "").replace("$","").replace(",","").replace(" ","").replace("O","0").replace("o","0")
                raw = re.sub(r"[^0-9.-]", "", raw)
                try: return float(raw)
                except Exception: return 0.0
            def infer(raw_value, current, signed_diff):
                raw_value = num(raw_value); current = num(current); signed_diff = num(signed_diff)
                if raw_value > 0:
                    if current <= 0 or signed_diff == 0:
                        return raw_value
                    delta = abs(signed_diff)
                    choices = [max(current-delta,0.0), current+delta]
                    return min(choices, key=lambda x: abs(x-raw_value))
                candidate = current - signed_diff
                if current > 0 and signed_diff != 0 and candidate > 0 and .20 <= candidate/current <= 3.0:
                    return candidate
                return 0.0

            for group in groups:
                line = sorted(group["tokens"], key=lambda x: x["left"])
                codes = []
                for token in line:
                    code = clean_code(token["text"])
                    if code:
                        score = difflib.SequenceMatcher(None, code, wanted).ratio()
                        if score >= .55:
                            codes.append(score)
                if not codes:
                    continue
                def zone(a,b):
                    vals=[]
                    for token in line:
                        xc=(token["left"]+token["width"]/2)/cw
                        if a<=xc<b and re.search(r"\d",token["text"]):
                            vals.append(parse_token(token["text"]))
                    return max(vals,key=lambda x:abs(x)) if vals else 0.0
                raw_goal=zone(.40,.48); raw_prev=zone(.48,.545); current=zone(.545,.625)
                diff_goal=zone(.675,.755); diff_prev=zone(.805,.86)
                result={
                    "target": infer(raw_goal,current,diff_goal),
                    "previous": infer(raw_prev,current,diff_prev),
                    "current": num(current),
                    "pieces_previous": zone(.15,.215),
                    "pieces": zone(.215,.30),
                }
                break
        except Exception as exc:
            print(f"[V176-TARGETED-OCR] {store_name}: {type(exc).__name__}: {exc}", flush=True)
            result = {}
        store_repair_cache[key] = dict(result)
        return result

    def store_rows_from_entries(latest, months_to_use, year):
        acc = defaultdict(lambda: {
            "current": 0.0, "previous": 0.0, "target": 0.0,
            "pieces": 0.0, "pieces_previous": 0.0, "months": 0,
            "opening_month": None, "comparison_note": "",
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
                is_puebla_sur = norm(name) == norm("Puebla Sur") and int(year) == 2026
                # Puebla Sur inició operación en agosto 2026: no se le atribuyen
                # meses previos ni un comparativo 2025 que no es homologable.
                if is_puebla_sur and mo < 8:
                    continue
                x = acc[str(name)]
                x["current"] += num(row.get("current"))
                x["target"] += num(row.get("target"))
                x["pieces"] += num(row.get("pieces"))
                if is_puebla_sur:
                    x["opening_month"] = 8
                    x["comparison_note"] = "Apertura Ago 2026 · sin base comparable 2025"
                else:
                    x["previous"] += num(row.get("previous"))
                    x["pieces_previous"] += num(row.get("pieces_previous"))
                x["months"] += 1
        out = []
        for name, x in acc.items():
            cur, prev, goal = x["current"], x["previous"], x["target"]
            special = bool(x.get("comparison_note"))
            out.append({
                "store": name, **x,
                "pct_goal": cur / goal * 100 if goal else None,
                "pct_previous": None if special else ((cur / prev - 1) * 100 if prev else None),
                "pieces_growth": None if special else (
                    (x["pieces"] / x["pieces_previous"] - 1) * 100
                    if x["pieces_previous"] else None
                ),
            })
        out.sort(key=lambda x: (-num(x.get("current")), norm(x.get("store"))))
        for i, row in enumerate(out, 1):
            row["rank"] = i
        return out, (cut_dates[-1] if cut_dates else "")

    def enrich_sales_months(rows, scope, latest, available, all_twelve=True):
        indexed = {}
        for raw in rows or []:
            try:
                mo = int(raw.get("month") or 0)
            except Exception:
                mo = 0
            if mo in range(1, 13):
                indexed[mo] = dict(raw)
        result = []
        month_range = range(1, 13) if all_twelve else sorted(indexed)
        for mo in month_range:
            row = dict(indexed.get(mo) or {})
            row["month"] = mo
            row["label"] = MONTH_LABELS[mo-1]
            for key in ("current", "previous", "target", "pieces", "pieces_previous"):
                row[key] = num(row.get(key))
            entry = latest.get(mo)
            vals, _payload = scope_ocr(entry, scope)
            if vals:
                row["pieces"] = num(vals.get("pieces")) or row["pieces"]
                row["pieces_previous"] = num(vals.get("pieces_previous")) or row["pieces_previous"]
            row["pdf_loaded"] = mo in available
            row["pct_goal"] = row["current"] / row["target"] * 100 if row["target"] else None
            row["pct_previous"] = (row["current"] / row["previous"] - 1) * 100 if row["previous"] else None
            row["pieces_growth"] = (
                (row["pieces"] / row["pieces_previous"] - 1) * 100
                if row["pieces_previous"] else None
            )
            if not row.get("source"):
                row["source"] = "PDF" if entry else "—"
            result.append(row)
        return result

    @m.app.get("/api/commercial-sales-v176")
    async def commercial_sales_v176(
        request: Request, year: int | None = None, month: int = 0,
        store: str = "Compañía",
    ):
        actor = m.require_user(request)
        yy = int(year or m.datetime.now().year)
        requested_scope = str(m.effective_store(actor, store) or "Compañía")
        latest = latest_sales_entries(yy)
        available = sorted(latest)
        max_month = max(available) if available else max(1, min(12, m.datetime.now().month))
        selected_month = int(month or 0)
        if selected_month and selected_month not in available:
            selected_month = 0

        if sales_base is None:
            raise RuntimeError("Motor de ventas V174 no disponible")

        # Regla de lectura:
        # - Mes específico => comparar todas las tiendas en gráfica/tabla.
        # - Sin mes + Compañía => evolución por mes.
        # - Sin mes + tienda => evolución mensual de esa tienda.
        view_scope = "Compañía" if selected_month else requested_scope
        base = sales_base(request=request, year=yy, through_month=max_month, store=view_scope)
        if inspect.isawaitable(base):
            base = await base
        base = dict(base or {})
        months = enrich_sales_months(base.get("months") or [], view_scope, latest, available, True)

        # La tabla mensual es deliberadamente independiente del filtro Tienda/Mes:
        # siempre representa Compañía, enero-diciembre, y sólo cambia Pesos/Piezas.
        if is_company(view_scope):
            company_months = [dict(x) for x in months]
        else:
            company_base = sales_base(request=request, year=yy, through_month=max_month, store="Compañía")
            if inspect.isawaitable(company_base):
                company_base = await company_base
            company_base = dict(company_base or {})
            company_months = enrich_sales_months(
                company_base.get("months") or [], "Compañía", latest, available, True
            )

        use_months = [selected_month] if selected_month else available
        selected_rows = [r for r in months if int(r.get("month") or 0) in use_months]
        total_current = sum(num(r.get("current")) for r in selected_rows)
        total_previous = sum(num(r.get("previous")) for r in selected_rows)
        total_target = sum(num(r.get("target")) for r in selected_rows)
        total_pieces = sum(num(r.get("pieces")) for r in selected_rows)
        total_pieces_prev = sum(num(r.get("pieces_previous")) for r in selected_rows)

        stores, store_cut = store_rows_from_entries(latest, use_months, yy)

        # Reparación selectiva por tienda. El OCR de la tabla resumen puede perder
        # una sola celda (caso observado: Toluca, Venta 2025). V174 ya dispone de
        # respaldo por tienda/mismo mes, así que sólo consultamos las filas que
        # llegaron incompletas, sin inventar cifras.
        if selected_month:
            async def _store_month_detail(store_name):
                detail = sales_base(
                    request=request, year=yy,
                    through_month=selected_month, store=store_name,
                )
                if inspect.isawaitable(detail):
                    detail = await detail
                rows = list((detail or {}).get("months") or [])
                return dict(rows[selected_month-1]) if len(rows) >= selected_month else {}

            by_store = {norm(r.get("store")): r for r in stores}
            for row in list(stores):
                current_value = num(row.get("current"))
                missing_previous = current_value > 0 and num(row.get("previous")) <= 0
                missing_target = current_value > 0 and num(row.get("target")) <= 0
                is_puebla_sur = norm(row.get("store")) == norm("Puebla Sur") and yy == 2026
                if not (missing_previous or missing_target or is_puebla_sur):
                    continue
                try:
                    month_row = await _store_month_detail(str(row.get("store") or ""))
                except Exception as exc:
                    print(f"[V176-SALES-STORE-REPAIR] {row.get('store')}: {type(exc).__name__}: {exc}", flush=True)
                    month_row = {}
                if missing_previous and not is_puebla_sur and num(month_row.get("previous")) > 0:
                    row["previous"] = num(month_row.get("previous"))
                    row["pieces_previous"] = num(month_row.get("pieces_previous"))
                if missing_target and num(month_row.get("target")) > 0:
                    row["target"] = num(month_row.get("target"))
                if num(row.get("pieces")) <= 0 and num(month_row.get("pieces")) > 0:
                    row["pieces"] = num(month_row.get("pieces"))

                # Si el motor normal sigue con una celda vacía, reparar únicamente
                # Toluca/Puebla Sur desde la fila visual del PDF. No modifica los
                # totales ni el OCR corporativo almacenado.
                still_missing_prev = num(row.get("current")) > 0 and num(row.get("previous")) <= 0 and not is_puebla_sur
                still_missing_target = num(row.get("current")) > 0 and num(row.get("target")) <= 0
                if still_missing_prev or still_missing_target:
                    targeted = targeted_store_ocr(latest.get(selected_month), str(row.get("store") or ""))
                    if still_missing_prev and num(targeted.get("previous")) > 0:
                        row["previous"] = num(targeted.get("previous"))
                        row["pieces_previous"] = num(targeted.get("pieces_previous")) or num(row.get("pieces_previous"))
                    if still_missing_target and num(targeted.get("target")) > 0:
                        row["target"] = num(targeted.get("target"))
                    if num(row.get("pieces")) <= 0 and num(targeted.get("pieces")) > 0:
                        row["pieces"] = num(targeted.get("pieces"))
                cur = num(row.get("current")); prev = num(row.get("previous")); goal = num(row.get("target"))
                row["pct_goal"] = cur / goal * 100 if goal else None
                row["pct_previous"] = (cur / prev - 1) * 100 if prev and not is_puebla_sur else None
                if is_puebla_sur:
                    row["opening_month"] = 8
                    row["comparison_note"] = "Apertura Ago 2026 · comparación 2025 no aplica"

            # Puebla Sur debe aparecer desde agosto aunque una lectura OCR puntual
            # no haya reconocido su renglón. Se recupera del motor estable por tienda.
            puebla_key = norm("Puebla Sur")
            if yy == 2026 and selected_month >= 8 and puebla_key not in by_store:
                try:
                    puebla_month = await _store_month_detail("Puebla Sur")
                except Exception:
                    puebla_month = {}
                targeted_puebla = targeted_store_ocr(latest.get(selected_month), "Puebla Sur")
                if num(puebla_month.get("current")) <= 0 and num(targeted_puebla.get("current")) > 0:
                    puebla_month["current"] = num(targeted_puebla.get("current"))
                if num(puebla_month.get("target")) <= 0 and num(targeted_puebla.get("target")) > 0:
                    puebla_month["target"] = num(targeted_puebla.get("target"))
                if num(puebla_month.get("pieces")) <= 0 and num(targeted_puebla.get("pieces")) > 0:
                    puebla_month["pieces"] = num(targeted_puebla.get("pieces"))
                if any(num(puebla_month.get(k)) > 0 for k in ("current","target","pieces")):
                    cur = num(puebla_month.get("current")); goal = num(puebla_month.get("target"))
                    stores.append({
                        "store": "Puebla Sur",
                        "current": cur, "previous": 0.0, "target": goal,
                        "pieces": num(puebla_month.get("pieces")), "pieces_previous": 0.0,
                        "months": 1, "opening_month": 8,
                        "comparison_note": "Apertura Ago 2026 · comparación 2025 no aplica",
                        "pct_goal": cur / goal * 100 if goal else None,
                        "pct_previous": None, "pieces_growth": None,
                    })

            stores.sort(key=lambda x: (-num(x.get("current")), norm(x.get("store"))))
            for rank, row in enumerate(stores, 1):
                row["rank"] = rank

        # En un mes específico SIEMPRE se muestran todas las tiendas. Sólo en
        # evolución acumulada se respeta un alcance de tienda individual.
        if not selected_month and not is_company(requested_scope):
            stores = [r for r in stores if norm(r.get("store")) == norm(requested_scope)]

        years = sorted(
            {int(e.get("year") or 0) for e in (m.load_manifest() or {}).get("sales", []) if int(e.get("year") or 0) > 0}
            | {yy, yy - 1},
            reverse=True,
        )
        return {
            **base,
            "year": yy, "previous_year": yy - 1, "store": view_scope,
            "requested_store": requested_scope,
            "selected_month": selected_month, "available_months": available,
            "available_years": years, "months": months, "company_months": company_months,
            "stores": stores,
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
            "source_label": "PDF mensual · comparativo por mes/tienda · V176",
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

/* Filtro principal: misma barra visual que Macro compañía / Acordeón / Tiendas. */
body[data-v163-module="analysis"] #v161FilterBar{
  background:#fff!important;
  border:1px solid var(--v161-line,#d5e1ee)!important;
  border-radius:13px!important;
  padding:4px!important;
  margin:7px 0 9px!important;
  box-shadow:none!important;
  overflow:hidden!important
}
body[data-v163-module="analysis"] #v161FilterGrid{
  display:flex!important;
  flex-wrap:nowrap!important;
  align-items:stretch!important;
  gap:4px!important;
  width:100%!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important
}
body[data-v163-module="analysis"] #v161FilterGrid::-webkit-scrollbar{display:none!important}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field{
  position:relative!important;
  flex:1 1 0!important;
  min-width:132px!important;
  min-height:48px!important;
  margin:0!important;
  padding:4px 5px 3px 34px!important;
  border:1px solid transparent!important;
  border-radius:9px!important;
  background:#fff!important;
  color:#284f7d!important;
  box-shadow:none!important
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field:hover,
body[data-v163-module="analysis"] #v161FilterGrid .v161-field:focus-within{
  background:#f5f8fc!important;
  border-color:#e3ebf4!important
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field label{
  display:block!important;
  margin:1px 0 0!important;
  color:#6c7f96!important;
  font-size:7px!important;
  line-height:1!important;
  font-weight:900!important;
  text-transform:uppercase!important;
  letter-spacing:.02em!important;
  pointer-events:none!important
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-field select,
body[data-v163-module="analysis"] #v161FilterGrid .v161-field input{
  width:100%!important;
  height:29px!important;
  min-height:29px!important;
  padding:3px 22px 3px 0!important;
  border:0!important;
  border-radius:6px!important;
  outline:0!important;
  background:transparent!important;
  color:#173f78!important;
  font-size:9px!important;
  line-height:1.05!important;
  font-weight:900!important;
  box-shadow:none!important
}
body[data-v163-module="analysis"] #v161FilterGrid .v166-filter-icon{
  left:9px!important;
  bottom:13px!important;
  width:17px!important;
  height:17px!important;
  color:#176fe8!important
}
body[data-v163-module="analysis"] #v161FilterGrid .v161-apply{
  flex:0 0 126px!important;
  min-width:126px!important;
  min-height:48px!important;
  height:auto!important;
  margin:0!important;
  border:1px solid transparent!important;
  border-radius:9px!important;
  background:var(--v161-blue,#176fe8)!important;
  color:#fff!important;
  padding:7px 12px!important;
  font-size:9px!important;
  font-weight:950!important;
  box-shadow:none!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important
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
  display:grid!important;
  grid-template-columns:repeat(auto-fit,minmax(108px,1fr))!important;
  align-items:stretch!important;
  gap:5px!important;
  width:100%!important;
  overflow:visible!important;
  margin:2px 0 5px!important;
  padding:0!important
}
body[data-v163-module="analysis"] #page-macro .compact-filter .switches>button,
body[data-v163-module="analysis"] #page-sections .compact-filter .switches>button,
body[data-v163-module="analysis"] #page-areas .compact-filter .switches>button{
  width:100%!important;
  min-width:0!important;
  min-height:40px!important;
  height:40px!important;
  padding:7px 10px!important;
  margin:0!important;
  border:1px solid transparent!important;
  border-radius:9px!important;
  background:#fff!important;
  color:#284f7d!important;
  font-size:8.5px!important;
  line-height:1.1!important;
  font-weight:900!important;
  box-shadow:none!important;
  white-space:nowrap!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:5px!important
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

/* Filtros tipo pestaña horizontal: sólo cambia los controles, no los reportes. */
.v176-table-filter-row,.v176-table-filter-field{display:none!important}
.v176-switches-hidden{display:flex!important}

body[data-v163-module="analysis"] #metricSwitch,
body[data-v163-module="analysis"] #macroAreaSectionSwitch,
body[data-v163-module="analysis"] #macroAreaGroupSwitch,
body[data-v163-module="analysis"] #paretoGroupSwitch,
body[data-v163-module="analysis"] #champSectionSwitch,
body[data-v163-module="analysis"] #rubroSectionSwitch,
body[data-v163-module="analysis"] .v176-select-tabs{
  position:static!important;
  display:flex!important;
  flex-wrap:nowrap!important;
  align-items:stretch!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  height:auto!important;
  min-height:0!important;
  gap:4px!important;
  margin:0 0 8px!important;
  padding:0!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important
}
body[data-v163-module="analysis"] #metricSwitch::-webkit-scrollbar,
body[data-v163-module="analysis"] #macroAreaSectionSwitch::-webkit-scrollbar,
body[data-v163-module="analysis"] #macroAreaGroupSwitch::-webkit-scrollbar,
body[data-v163-module="analysis"] #paretoGroupSwitch::-webkit-scrollbar,
body[data-v163-module="analysis"] #champSectionSwitch::-webkit-scrollbar,
body[data-v163-module="analysis"] #rubroSectionSwitch::-webkit-scrollbar,
body[data-v163-module="analysis"] .v176-select-tabs::-webkit-scrollbar{display:none!important}

body[data-v163-module="analysis"] #metricSwitch>button,
body[data-v163-module="analysis"] #macroAreaSectionSwitch>button,
body[data-v163-module="analysis"] #macroAreaGroupSwitch>button,
body[data-v163-module="analysis"] #paretoGroupSwitch>button,
body[data-v163-module="analysis"] #champSectionSwitch>button,
body[data-v163-module="analysis"] #rubroSectionSwitch>button,
body[data-v163-module="analysis"] .v176-select-tabs>button{
  flex:1 1 0!important;
  min-width:126px!important;
  width:auto!important;
  height:40px!important;
  min-height:40px!important;
  padding:7px 12px!important;
  margin:0!important;
  border:1px solid transparent!important;
  border-radius:9px!important;
  background:#fff!important;
  color:#173f78!important;
  font-size:8.5px!important;
  line-height:1.1!important;
  font-weight:900!important;
  white-space:nowrap!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:8px!important;
  box-shadow:none!important
}
.v176-tab-icon{
  display:inline-flex!important;
  width:18px!important;height:18px!important;flex:0 0 18px!important;
  align-items:center!important;justify-content:center!important;
  color:currentColor!important;pointer-events:none!important
}
.v176-tab-icon svg{
  width:17px!important;height:17px!important;
  stroke:currentColor!important;fill:none!important;stroke-width:1.9!important;
  stroke-linecap:round!important;stroke-linejoin:round!important
}
body[data-v163-module="analysis"] #metricSwitch>button.active,
body[data-v163-module="analysis"] #macroAreaSectionSwitch>button.active,
body[data-v163-module="analysis"] #macroAreaGroupSwitch>button.active,
body[data-v163-module="analysis"] #paretoGroupSwitch>button.active,
body[data-v163-module="analysis"] #champSectionSwitch>button.active,
body[data-v163-module="analysis"] #rubroSectionSwitch>button.active,
body[data-v163-module="analysis"] .v176-select-tabs>button.active{
  background:#176fe8!important;
  border-color:#176fe8!important;
  color:#fff!important;
  box-shadow:0 2px 8px rgba(23,111,232,.14)!important
}

/* Los dos filtros de Ubicación van en filas independientes para que nunca se encimen. */
body[data-v163-module="analysis"] #macroAreaSectionSwitch,
body[data-v163-module="analysis"] #macroAreaGroupSwitch{
  clear:both!important
}
body[data-v163-module="analysis"] #page-macro .compact-filter{
  overflow:visible!important
}
body[data-v163-module="analysis"] #page-macro .compact-filter .filter-caption{
  display:block!important;
  margin:2px 3px 5px!important
}

/* Modelos lentos: el select original se oculta y se refleja como pestañas. */
body[data-v163-module="analysis"] #slowSection.v176-select-tab-source{
  display:none!important
}
body[data-v163-module="analysis"] .v176-select-tabs{
  margin-top:4px!important
}

@media(max-width:900px){
  body[data-v163-module="analysis"] #metricSwitch,
  body[data-v163-module="analysis"] #macroAreaSectionSwitch,
  body[data-v163-module="analysis"] #macroAreaGroupSwitch,
  body[data-v163-module="analysis"] #paretoGroupSwitch,
  body[data-v163-module="analysis"] #champSectionSwitch,
  body[data-v163-module="analysis"] #rubroSectionSwitch,
  body[data-v163-module="analysis"] .v176-select-tabs{
    gap:4px!important;
    margin-bottom:6px!important
  }
  body[data-v163-module="analysis"] #metricSwitch>button,
  body[data-v163-module="analysis"] #macroAreaSectionSwitch>button,
  body[data-v163-module="analysis"] #macroAreaGroupSwitch>button,
  body[data-v163-module="analysis"] #paretoGroupSwitch>button,
  body[data-v163-module="analysis"] #champSectionSwitch>button,
  body[data-v163-module="analysis"] #rubroSectionSwitch>button,
  body[data-v163-module="analysis"] .v176-select-tabs>button{
    flex:0 0 auto!important;
    min-width:116px!important;
    height:36px!important;
    min-height:36px!important;
    padding:6px 10px!important;
    font-size:8px!important;
    gap:6px!important
  }
}

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
.sales-chart-scroll{overflow-x:auto!important;overflow-y:hidden!important}
.v176-chart-svg{display:block;width:auto!important;max-width:none!important;min-width:100%!important}
.v176-opening{display:inline-block;font-size:8px;font-weight:900;color:#7a5d00;background:#fff7d6;border:1px solid #f1d46a;border-radius:999px;padding:3px 7px;white-space:nowrap}
.v176-general-row td{font-weight:950!important;background:#eef4fb!important;border-top:2px solid #18477f!important;color:#103d73!important}
.v176-general-row td:first-child{color:#18477f!important}
.v176-month-store-bar{display:flex;justify-content:flex-end;align-items:flex-end;gap:8px;margin:7px 0 6px}
.v176-month-store-filter,.v176-store-sales-month-filter{display:flex;flex-direction:column;gap:3px;min-width:205px}
.v176-month-store-filter span,.v176-store-sales-month-filter span{font-size:7px;line-height:1;font-weight:950;color:#667085;text-transform:uppercase;letter-spacing:.025em}
.v176-month-store-filter select,.v176-store-sales-month-filter select{height:38px;min-height:38px;border:1px solid #cad8e8;border-radius:9px;background:#fff;color:#173f78;padding:6px 30px 6px 10px;font-size:9px;font-weight:900;box-shadow:none;outline:none}
.v176-month-store-filter select:focus,.v176-store-sales-month-filter select:focus{border-color:#176fe8;box-shadow:0 0 0 2px rgba(23,111,232,.10)}
.v176-store-sales-head{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:14px 0 7px}
.v176-store-sales-head .title{margin:0!important}
.v176-store-sales-month-filter{min-width:190px}

/* Ubicación agrupada. */
.v176-area-company td:nth-child(1),.v176-area-company td:nth-child(2){font-weight:900}
#champTable td,#champTable th{white-space:nowrap}
#champTable th:nth-child(7),#champTable th:nth-child(8){min-width:105px}

@media(max-width:900px){
  body[data-v163-module="analysis"] #v161FilterBar{
    padding:4px!important;
    border-radius:11px!important;
    overflow:hidden!important
  }
  body[data-v163-module="analysis"] #v161FilterGrid{
    display:flex!important;
    flex-wrap:nowrap!important;
    gap:4px!important;
    overflow-x:auto!important
  }
  body[data-v163-module="analysis"] #v161FilterGrid .v161-field{
    flex:0 0 118px!important;
    min-width:118px!important;
    min-height:42px!important;
    padding:3px 4px 2px 29px!important
  }
  body[data-v163-module="analysis"] #v161FilterGrid .v161-field label{font-size:6px!important}
  body[data-v163-module="analysis"] #v161FilterGrid .v161-field select,
  body[data-v163-module="analysis"] #v161FilterGrid .v161-field input{
    height:27px!important;
    min-height:27px!important;
    font-size:8.5px!important;
    padding-right:17px!important
  }
  body[data-v163-module="analysis"] #v161FilterGrid .v166-filter-icon{
    left:7px!important;bottom:11px!important;width:15px!important;height:15px!important
  }
  body[data-v163-module="analysis"] #v161FilterGrid .v161-apply{
    flex:0 0 102px!important;
    min-width:102px!important;
    min-height:42px!important;
    font-size:8px!important
  }
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
  .v176-month-store-bar{justify-content:flex-start;margin:6px 0 5px}
  .v176-month-store-filter,.v176-store-sales-month-filter{min-width:165px;max-width:210px}
  .v176-month-store-filter select,.v176-store-sales-month-filter select{height:34px;min-height:34px;font-size:8px}
  .v176-store-sales-head{align-items:flex-start;margin:10px 0 6px}
  .v176-table-filter-row{gap:5px!important;margin:3px 0 6px!important}
  .v176-table-filter-field{min-width:145px!important;max-width:185px!important}
  .v176-table-filter-field select{height:34px!important;min-height:34px!important;font-size:8px!important}
  body[data-v163-module="analysis"] #page-macro #slowSection,
  body[data-v163-module="analysis"] #page-macro #checklistStoreSelect{
    height:34px!important;min-height:34px!important;font-size:8px!important;max-width:185px!important
  }
  .v176-compact-converted{width:100%!important;padding:6px!important}
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
let salesMetric='money',salesMonth=0,salesSort={key:'',dir:-1},salesBusy=false,modelsBusy=false,salesTableStore='Compañía',salesTableBusy=false,salesTableData=null,salesStoreTableMonth=0,salesStoreTableBusy=false,salesStoreTableData=null;const modelClientCache=new Map();

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

const v176TabIcons={
  grid:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  chart:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/></svg>',
  box:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 8-9 5-9-5"/><path d="m3 8 9-5 9 5v8l-9 5-9-5Z"/><path d="M12 13v8"/></svg>',
  layers:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></svg>',
  clock:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  store:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10h18"/><path d="m5 10 1-6h12l1 6"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></svg>',
  map:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 6 5-3 8 3 5-3v15l-5 3-8-3-5 3Z"/><path d="M8 3v15"/><path d="M16 6v15"/></svg>',
  tag:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 13 11 22l-9-9V4h9l9 9Z"/><circle cx="7" cy="9" r="1.5"/></svg>',
  list:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
  table:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M9 4v16"/></svg>',
  user:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.4-4 4.1-6 8-6s6.6 2 8 6"/></svg>',
  hanger:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 6a2 2 0 1 1 3.5 1.3L12 9"/><path d="m12 9 9 7H3l9-7Z"/></svg>'
};
function v176IconName(groupId,label){
  const t=String(label||'').toLowerCase();
  if(groupId==='metricSwitch'){
    if(t.includes('suger'))return 'chart';
    if(t.includes('exist'))return 'box';
    if(t.includes('piso'))return 'store';
    if(t.includes('bodega'))return 'box';
    if(t.includes('ddi'))return 'clock';
  }
  if(groupId==='macroAreaGroupSwitch'){
    if(t.includes('colgado'))return 'hanger';
    if(t.includes('doblado'))return 'layers';
    if(t.includes('jeans'))return 'tag';
    if(t.includes('lencer'))return 'hanger';
    return 'grid';
  }
  if(groupId==='paretoGroupSwitch'){
    if(t.includes('área')||t.includes('area'))return 'map';
    if(t.includes('catálogo')||t.includes('catalogo'))return 'list';
    if(t.includes('macro'))return 'table';
    return 'grid';
  }
  if(groupId==='champSectionSwitch'||groupId==='rubroSectionSwitch'||groupId==='macroAreaSectionSwitch'||groupId==='v176SlowSectionTabs'||groupId==='v176ZeroSectionTabs'){
    if(t.includes('dama'))return 'user';
    if(t.includes('caballero'))return 'user';
    if(t.includes('infantil'))return 'user';
    return 'grid';
  }
  return 'grid';
}
function decorateHorizontalTabGroup(groupId){
  const group=q('#'+groupId);if(!group)return;
  qa('button',group).forEach(btn=>{
    btn.querySelectorAll('.v176-tab-icon').forEach(x=>x.remove());
    const label=(btn.textContent||'').replace(/\s+/g,' ').trim();
    const icon=document.createElement('span');
    icon.className='v176-tab-icon';
    icon.innerHTML=v176TabIcons[v176IconName(groupId,label)]||v176TabIcons.grid;
    btn.prepend(icon);
  });
}

function restoreButtonTabs(groupId){
  const group=q('#'+groupId);if(!group)return;
  // Borra cualquier selector compacto generado por versiones anteriores.
  const parent=group.parentElement;
  qa('.v176-table-filter-row',parent||document).forEach(row=>row.remove());
  group.classList.remove('v176-switches-hidden');
  ['display','width','height','min-height','margin','padding','overflow'].forEach(p=>group.style.removeProperty(p));
  decorateHorizontalTabGroup(groupId);
}

function tabsFromSelect(selectId,tabsId){
  const sel=q('#'+selectId);if(!sel)return;
  let tabs=q('#'+tabsId);
  if(!tabs){
    tabs=document.createElement('div');
    tabs.id=tabsId;
    tabs.className='v176-select-tabs';
    sel.parentNode.insertBefore(tabs,sel.nextSibling);
  }
  const current=sel.value;
  tabs.innerHTML=[...sel.options].map(o=>
    '<button type="button" class="'+(o.value===current?'active':'')+'" data-value="'+esc(o.value)+'">'+esc(o.textContent||o.value)+'</button>'
  ).join('');
  decorateHorizontalTabGroup(tabsId);
  qa('button',tabs).forEach(btn=>btn.addEventListener('click',()=>{
    const value=btn.dataset.value||'';
    if(sel.value!==value){
      sel.value=value;
      sel.dispatchEvent(new Event('change',{bubbles:true}));
    }
    qa('button',tabs).forEach(x=>x.classList.toggle('active',x===btn));
  }));
  sel.classList.add('v176-select-tab-source');
}

function installCompactTableFilters(){
  // El nombre se conserva para no romper llamadas previas, pero ahora restaura
  // exactamente filtros tipo pestaña horizontal.
  ['metricSwitch','macroAreaSectionSwitch','macroAreaGroupSwitch','paretoGroupSwitch','champSectionSwitch','rubroSectionSwitch']
    .forEach(restoreButtonTabs);

  // Remueve campos select compactos que pudieron quedar de una ejecución anterior.
  ['v176MetricSelectField','v176AreaSectionSelectField','v176AreaGroupSelectField','v176ParetoSelectField','v176ChampSectionSelectField','v176RubroSectionSelectField']
    .forEach(id=>q('#'+id)?.remove());

  // Modelos lentos y sugerido 0 a 1 también usan pestañas horizontales con icono.
  tabsFromSelect('slowSection','v176SlowSectionTabs');
  tabsFromSelect('zeroSection','v176ZeroSectionTabs');

  // Reaplica iconos por si otro parche regeneró botones después del primer render.
  ['metricSwitch','macroAreaSectionSwitch','macroAreaGroupSwitch','paretoGroupSwitch','champSectionSwitch','rubroSectionSwitch','v176SlowSectionTabs','v176ZeroSectionTabs']
    .forEach(decorateHorizontalTabGroup);
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
  const store=visibleStoreControl()?.value||q('#store')?.value||((typeof DASH!=='undefined'&&DASH?.selected_store)?DASH.selected_store:'Compañía');
  const week=q('#week')?.value||((typeof DASH!=='undefined'&&DASH?.week)?DASH.week:'');
  const section=q('#section')?.value||'Todas',catalog=q('#catalog')?.value||'Todos',gb=paretoGroup();
  // Nunca lanzar el análisis pesado antes de que el periodo esté listo.
  if(!week)return;
  const cacheKey=[week,store,section,catalog,gb].join('|');
  const cached=modelClientCache.get(cacheKey);
  modelsBusy=true;
  try{
    if(!cached){
      if(q('#champTable'))q('#champTable').innerHTML='<tr><td colspan="16">Cargando 80/20…</td></tr>';
      if(q('#slowTable'))q('#slowTable').innerHTML='<tr><td colspan="15">Cargando modelos lentos…</td></tr>';
      if(q('#zeroTable'))q('#zeroTable').innerHTML='<tr><td colspan="16">Cargando sugerido 0 a 1…</td></tr>';
    }
    let d=cached&&!force?cached:null;
    if(!d){
      const url='/api/commercial-models-v176?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store)+'&section='+encodeURIComponent(section)+'&catalog='+encodeURIComponent(catalog)+'&group_by='+encodeURIComponent(gb);
      try{
        d=await A(url,{timeoutMs:240000});
      }catch(first){
        // Un reinicio de Render es transitorio. Reintentar una vez y, si ya
        // existe una respuesta válida en memoria del navegador, conservarla.
        if(cached)d=cached;
        else{
          await new Promise(resolve=>setTimeout(resolve,4500));
          d=await A(url,{timeoutMs:240000});
        }
      }
      if(d)modelClientCache.set(cacheKey,d);
    }
    if(!d)throw new Error('Sin respuesta de modelos');
    let ck={rows:[],editable:false};
    if(store!=='Compañía'){
      try{ck=await A('/api/model-checklist?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store),{timeoutMs:60000})}catch(_){}
    }
    const map={};(ck.rows||[]).forEach(r=>map[String(r.id_art)]=r);
    if(typeof window.renderModelRows==='function'){
      window.renderModelRows((d.champions||[]).slice(0,150),d.slow||[],d.zero||[],section,section,store,map,!!ck.editable,store==='Compañía'?'':store,store);
    }
    fixModelHead();renderPareto(d.pareto?.rows||[]);
  }catch(e){
    if(cached){
      try{
        if(typeof window.renderModelRows==='function')window.renderModelRows((cached.champions||[]).slice(0,150),cached.slow||[],cached.zero||[],section,section,store,{},false,'',store);
        fixModelHead();renderPareto(cached.pareto?.rows||[]);
      }catch(_){}
    }else{
      const msg='No fue posible cargar la información. Reintentaremos al consultar nuevamente.';
      if(q('#champTable'))q('#champTable').innerHTML='<tr><td colspan="16">'+msg+'</td></tr>';
      if(q('#slowTable'))q('#slowTable').innerHTML='<tr><td colspan="15">'+msg+'</td></tr>';
      if(q('#zeroTable'))q('#zeroTable').innerHTML='<tr><td colspan="16">'+msg+'</td></tr>';
      console.warn('[V176] modelos',e);
    }
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
  const rows=graphRows(d),metric=salesMetric,isStores=!!d.selected_month;
  const W=Math.max(isStores?1320:1050,(isStores?118:105)*Math.max(rows.length,1)+120),H=390,L=72,R=24,T=76,B=62,pw=W-L-R,ph=H-T-B;
  const cur=r=>metric==='pieces'?n(r.pieces):n(r.current),prev=r=>metric==='pieces'?n(r.pieces_previous):n(r.previous);
  const vals=[];rows.forEach(r=>{vals.push(cur(r),prev(r));if(metric==='money')vals.push(n(r.target))});
  const mx=Math.max(1,...vals)*1.18,y=v=>T+ph-n(v)/mx*ph,gw=pw/Math.max(rows.length,1),bw=Math.min(27,gw*.25),base=T+ph;
  let svg='<svg class="v176-chart-svg" width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'">';
  for(let i=0;i<=4;i++){const val=mx*i/4,yy=y(val);svg+='<line x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'" stroke="#dce4ee"/><text x="'+(L-8)+'" y="'+(yy+3)+'" text-anchor="end" font-size="8" fill="#6b778c">'+shortVal(val,metric)+'</text>'}
  const pts=[];let metaOverlays='';
  rows.forEach((r,i)=>{
    const cx=L+gw*(i+.5),a=cur(r),b=prev(r),g=n(r.target),ya=y(a),yb=y(b),yg=y(g);
    const gp=prev(r)>0?(a/prev(r)-1)*100:null,mp=n(r.target)>0?n(r.current)/n(r.target)*100:null;
    svg+='<rect x="'+(cx-bw-3)+'" y="'+ya+'" width="'+bw+'" height="'+Math.max(0,base-ya)+'" rx="3" fill="#1769e8"/>';
    svg+='<rect x="'+(cx+3)+'" y="'+yb+'" width="'+bw+'" height="'+Math.max(0,base-yb)+'" rx="3" fill="#9fb0c6"/>';

    // Valor dentro de la parte inferior de cada barra. Si la barra es demasiado
    // corta, se coloca inmediatamente arriba para conservar legibilidad.
    if(a>0){
      const h=Math.max(0,base-ya),inside=h>=22,ty=inside?base-7:Math.max(T+10,ya-5);
      svg+='<text class="v176-chart-value" x="'+(cx-bw/2-3)+'" y="'+ty+'" text-anchor="middle" font-size="7" fill="'+(inside?'#fff':'#173f78')+'">'+shortVal(a,metric)+'</text>';
    }
    if(b>0){
      const h=Math.max(0,base-yb),inside=h>=22,ty=inside?base-7:Math.max(T+10,yb-5);
      svg+='<text class="v176-chart-value" x="'+(cx+bw/2+3)+'" y="'+ty+'" text-anchor="middle" font-size="7" fill="'+(inside?'#fff':'#52657d')+'">'+shortVal(b,metric)+'</text>';
    }

    const top=Math.min(ya,yb,metric==='money'&&g>0?yg:9999);
    const growthY=gp!=null?Math.max(14,top-34-(i%2)*10):null;
    if(gp!=null){
      svg+='<text class="v176-chart-growth" x="'+cx+'" y="'+growthY+'" text-anchor="middle" font-size="7.5" fill="'+(gp>=0?'#118a52':'#d92d20')+'">'+(gp>=0?'+':'')+gp.toFixed(1)+'% vs '+d.previous_year+'</text>';
    }

    if(metric==='money'&&g>0){
      pts.push(cx+','+yg);
      svg+='<circle cx="'+cx+'" cy="'+yg+'" r="3" fill="#ec007c"/>';
      if(mp!=null){
        const label=mp.toFixed(1)+'% Meta';
        const pillW=Math.max(48,label.length*4.25+12),pillH=15;
        let labelY=Math.max(T+12,yg-10);
        if(growthY!=null&&Math.abs(labelY-growthY)<18)labelY=Math.min(base-12,yg+18);
        const pillX=cx-pillW/2,pillY=labelY-10.5;
        metaOverlays+='<rect x="'+pillX+'" y="'+pillY+'" width="'+pillW+'" height="'+pillH+'" rx="7.5" fill="#fff0f7" stroke="#ec007c" stroke-width=".7" opacity=".98"/>';
        metaOverlays+='<text x="'+cx+'" y="'+labelY+'" text-anchor="middle" font-size="7" font-weight="950" fill="#b00063">'+label+'</text>';
      }
    }
    const raw=String(r.label||r.store||''),lab=raw.length>16?raw.slice(0,15)+'…':raw;
    svg+='<text x="'+cx+'" y="'+(H-23)+'" text-anchor="middle" font-size="8" fill="#52657c">'+esc(lab)+'</text>';
  });
  if(metric==='money'&&pts.length>1)svg+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="#ec007c" stroke-width="2.5"/>';
  svg+=metaOverlays;
  host.innerHTML=svg+'</svg>';
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
function monthlyStoreOptions(){
  const src=visibleStoreControl()||q('#store');
  const values=[];
  if(src){
    [...src.options].forEach(o=>{
      const value=String(o.value||'').trim(),label=String(o.textContent||value).trim();
      if(value&&!values.some(x=>x.value===value))values.push({value,label});
    });
  }
  if(!values.some(x=>x.value==='Compañía'))values.unshift({value:'Compañía',label:'Compañía'});
  return values;
}
function ensureMonthTableStoreControl(d){
  const wrap=q('#salesExecRows')?.closest('.tablewrap');if(!wrap)return null;
  let bar=q('#v176MonthStoreBar');
  if(!bar){
    bar=document.createElement('div');bar.id='v176MonthStoreBar';bar.className='v176-month-store-bar';
    bar.innerHTML='<label class="v176-month-store-filter"><span>Tienda</span><select id="v176MonthStoreSelect" aria-label="Tienda para tabla mensual"></select></label>';
    wrap.parentNode.insertBefore(bar,wrap);
  }
  const sel=q('#v176MonthStoreSelect',bar),opts=monthlyStoreOptions();
  if(sel){
    const previous=salesTableStore||'Compañía';
    sel.innerHTML=opts.map(o=>'<option value="'+esc(o.value)+'">'+esc(o.label)+'</option>').join('');
    salesTableStore=opts.some(o=>o.value===previous)?previous:'Compañía';
    sel.value=salesTableStore;
    if(!sel.dataset.v176bound){
      sel.dataset.v176bound='1';
      sel.addEventListener('change',()=>{
        salesTableStore=sel.value||'Compañía';
        salesTableData=null;
        loadMonthTableStore(window.__V176_SALES_DATA);
      });
    }
  }
  return sel;
}
function renderMonthTableRows(d,rows){
  const metric=salesMetric;
  const ordered=[...(rows||[])].sort((a,b)=>n(a.month)-n(b.month));
  const table=q('#salesExecRows')?.closest('table'),head=table?.querySelector('thead tr');
  const currentHead=metric==='pieces'?'Piezas '+d.year:'Venta '+d.year;
  const previousHead=metric==='pieces'?'Piezas '+d.previous_year:'Venta '+d.previous_year;
  const lastHead=metric==='pieces'?'Venta $':'Venta pzas';
  if(head)head.innerHTML='<th>Mes</th><th>Meta</th><th id="salesYearTh">'+currentHead+'</th><th id="salesPrevTh">'+previousHead+'</th><th>'+(metric==='pieces'?'% Meta $':'% Meta')+'</th><th>% vs '+d.previous_year+'</th><th>'+lastHead+'</th>';
  const monthBody=q('#salesExecRows');
  if(!monthBody)return;
  const detail=ordered.map(r=>{
    const pctPrev=metric==='pieces'?r.pieces_growth:r.pct_previous;
    const cv=metric==='pieces'?nf(r.pieces):money(r.current),pv=metric==='pieces'?nf(r.pieces_previous):money(r.previous);
    const last=metric==='pieces'?money(r.current):nf(r.pieces);
    return '<tr><td><b>'+esc(r.label)+'</b></td><td>'+(n(r.target)>0?money(r.target):'—')+'</td><td><b>'+cv+'</b></td><td>'+pv+'</td><td class="'+tone(r.pct_goal,true)+'">'+pct(r.pct_goal)+'</td><td class="'+tone(pctPrev,false)+'">'+pct(pctPrev)+'</td><td>'+last+'</td></tr>';
  }).join('');

  if(!ordered.length){
    monthBody.innerHTML='<tr><td colspan="7">Sin información para la tienda seleccionada.</td></tr>';
    return;
  }
  const totals=ordered.reduce((a,r)=>{
    a.target+=n(r.target);a.current+=n(r.current);a.previous+=n(r.previous);
    a.pieces+=n(r.pieces);a.piecesPrevious+=n(r.pieces_previous);return a;
  },{target:0,current:0,previous:0,pieces:0,piecesPrevious:0});
  const goalPct=totals.target?totals.current/totals.target*100:null;
  const prevPct=metric==='pieces'
    ?(totals.piecesPrevious?(totals.pieces/totals.piecesPrevious-1)*100:null)
    :(totals.previous?(totals.current/totals.previous-1)*100:null);
  const totalCurrent=metric==='pieces'?nf(totals.pieces):money(totals.current);
  const totalPrevious=metric==='pieces'?nf(totals.piecesPrevious):money(totals.previous);
  const totalLast=metric==='pieces'?money(totals.current):nf(totals.pieces);
  const pueblaNoCompare=salesTableStore==='Puebla Sur'&&Number(d.year)===2026;
  monthBody.innerHTML=detail+
    '<tr class="v176-general-row"><td>GENERAL</td><td>'+money(totals.target)+'</td><td>'+totalCurrent+'</td><td>'+(pueblaNoCompare?'No aplica':totalPrevious)+'</td><td>'+pct(goalPct)+'</td><td>'+(pueblaNoCompare?'No aplica':pct(prevPct))+'</td><td>'+totalLast+'</td></tr>';
}
async function loadMonthTableStore(baseD){
  if(!baseD||salesTableBusy)return;
  ensureMonthTableStoreControl(baseD);
  if(salesTableStore==='Compañía'){
    salesTableData={year:baseD.year,store:'Compañía',months:baseD.company_months||baseD.months||[]};
    renderMonthTableRows(baseD,salesTableData.months);
    return;
  }
  if(salesTableData&&Number(salesTableData.year)===Number(baseD.year)&&salesTableData.store===salesTableStore){
    renderMonthTableRows(baseD,salesTableData.months||[]);
    return;
  }
  salesTableBusy=true;
  const body=q('#salesExecRows');
  if(body)body.innerHTML='<tr><td colspan="7">Cargando '+esc(salesTableStore)+'…</td></tr>';
  try{
    const data=await A('/api/commercial-sales-v176?year='+encodeURIComponent(baseD.year)+'&month=0&store='+encodeURIComponent(salesTableStore),{timeoutMs:180000});
    salesTableData={year:data.year,store:salesTableStore,months:data.months||[]};
    renderMonthTableRows(baseD,salesTableData.months);
  }catch(e){
    if(body)body.innerHTML='<tr><td colspan="7">No fue posible consultar '+esc(salesTableStore)+'.</td></tr>';
    console.warn('[V176] tabla mensual por tienda',e);
  }finally{salesTableBusy=false}
}
function storeSalesTitle(d,month){
  const m=Number(month||0);
  if(!m)return 'Venta por tienda · acumulado anual';
  const now=new Date(),isCurrent=Number(d.year)===now.getFullYear()&&m===(now.getMonth()+1);
  return 'Venta por tienda · '+(isCurrent?'acumulado ':'')+monthLong[m-1];
}
function renderStoreSalesTable(baseD,data){
  const metric=salesMetric,month=Number(salesStoreTableMonth||0);
  let box=q('#v168SalesStores');if(!box){box=document.createElement('div');box.id='v168SalesStores';q('#v109-sales-exec')?.append(box)}
  let stores=sortRows(((data&&data.stores)||[]).map(r=>({...r,pct_previous:metric==='pieces'?r.pieces_growth:r.pct_previous})));
  const opts=['<option value="0">Todos los meses</option>'].concat((baseD.available_months||[]).map(m=>'<option value="'+m+'">'+monthLong[m-1]+'</option>'));
  const t=(data&&data.totals)||{},totalGrowth=metric==='pieces'?t.pieces_growth:t.growth;
  const totalCurrent=metric==='pieces'?nf(t.pieces):money(t.current);
  const totalPrevious=metric==='pieces'?nf(t.pieces_previous):money(t.previous);
  const totalRow='<tr class="v176-general-row"><td></td><td>GENERAL</td><td>'+money(t.target)+'</td><td>'+totalCurrent+'</td><td>'+totalPrevious+'</td><td>'+pct(t.compliance)+'</td><td>'+pct(totalGrowth)+'</td></tr>';
  box.innerHTML=
    '<div class="v176-store-sales-head">'+
      '<div class="title">'+storeSalesTitle(baseD,month)+'</div>'+
      '<label class="v176-store-sales-month-filter"><span>Mes</span><select id="v176StoreSalesMonth">'+opts.join('')+'</select></label>'+
    '</div>'+
    '<div class="tablewrap"><table class="table v168-sales-rank v176-sales-rank"><thead><tr><th>#</th><th>Tienda</th><th>Meta</th><th>Venta '+baseD.year+'</th><th>Venta '+baseD.previous_year+'</th><th>'+sortButton('pct_goal','% Meta')+'</th><th>'+sortButton('pct_previous','% vs '+baseD.previous_year)+'</th></tr></thead><tbody>'+
    (stores.length?stores.map((r,i)=>{
      const cv=metric==='pieces'?nf(r.pieces):money(r.current),pv=metric==='pieces'?nf(r.pieces_previous):money(r.previous);
      const opening=r.comparison_note?'<span class="v176-opening">'+esc(r.comparison_note)+'</span>':pct(r.pct_previous);
      const prevCell=r.comparison_note?'No aplica':pv;
      const targetCell=n(r.target)>0?money(r.target):'—';
      return '<tr><td>#'+(i+1)+'</td><td><b>'+esc(r.store)+'</b></td><td>'+targetCell+'</td><td><b>'+cv+'</b></td><td>'+prevCell+'</td><td class="'+(r.pct_goal==null?'':(n(r.pct_goal)>=100?'v176-pos':'v176-neg'))+'">'+pct(r.pct_goal)+'</td><td class="'+(r.comparison_note?'':(n(r.pct_previous)>=0?'v176-pos':'v176-neg'))+'">'+opening+'</td></tr>';
    }).join('')+totalRow:'<tr><td colspan="7">Sin información para el periodo seleccionado.</td></tr>')+
    '</tbody></table></div>';

  const sel=q('#v176StoreSalesMonth',box);
  if(sel){
    sel.value=String(month);
    sel.addEventListener('change',()=>{
      salesStoreTableMonth=Number(sel.value||0);
      salesStoreTableData=null;
      loadStoreSalesMonth(baseD);
    });
  }
  bindSort(box,baseD);
}
async function loadStoreSalesMonth(baseD){
  if(!baseD||salesStoreTableBusy)return;
  const month=Number(salesStoreTableMonth||0);
  if(salesStoreTableData&&Number(salesStoreTableData.year)===Number(baseD.year)&&Number(salesStoreTableData.month)===month){
    renderStoreSalesTable(baseD,salesStoreTableData.payload);
    return;
  }
  salesStoreTableBusy=true;
  let box=q('#v168SalesStores');
  if(!box){box=document.createElement('div');box.id='v168SalesStores';q('#v109-sales-exec')?.append(box)}
  box.innerHTML='<div class="v176-store-sales-head"><div class="title">'+storeSalesTitle(baseD,month)+'</div><label class="v176-store-sales-month-filter"><span>Mes</span><select disabled><option>Cargando…</option></select></label></div>';
  try{
    const data=await A('/api/commercial-sales-v176?year='+encodeURIComponent(baseD.year)+'&month='+encodeURIComponent(month)+'&store='+encodeURIComponent('Compañía'),{timeoutMs:180000});
    salesStoreTableData={year:baseD.year,month,payload:data};
    renderStoreSalesTable(baseD,data);
  }catch(e){
    box.innerHTML='<div class="v176-store-sales-head"><div class="title">'+storeSalesTitle(baseD,month)+'</div></div><div class="tablewrap"><table class="table"><tbody><tr><td>No fue posible consultar la venta por tienda.</td></tr></tbody></table></div>';
    console.warn('[V176] venta por tienda por mes',e);
  }finally{salesStoreTableBusy=false}
}
function renderSalesTables(d){
  ensureMonthTableStoreControl(d);
  if(salesTableStore==='Compañía'){
    renderMonthTableRows(d,d.company_months||d.months||[]);
  }else if(salesTableData&&Number(salesTableData.year)===Number(d.year)&&salesTableData.store===salesTableStore){
    renderMonthTableRows(d,salesTableData.months||[]);
  }else{
    setTimeout(()=>loadMonthTableStore(d),0);
  }

  // "Venta por tienda" tiene su propio selector compacto de Mes y no depende
  // del selector de mes de la gráfica superior.
  if(salesStoreTableData&&Number(salesStoreTableData.year)===Number(d.year)&&Number(salesStoreTableData.month)===Number(salesStoreTableMonth||0)){
    renderStoreSalesTable(d,salesStoreTableData.payload);
  }else{
    setTimeout(()=>loadStoreSalesMonth(d),0);
  }
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
      if(id==='salesExecYear'){salesTableData=null;salesStoreTableData=null;}
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
    const kpi=(l,v,sub,c,cl)=>'<div class="sales-kpi" style="--sk:'+c+'"><div class="sl">'+l+'</div><div class="sv '+(cl||'')+'">'+v+'</div><div class="ss">'+sub+'</div></div>';
    const kpis=q('#salesExecKpis');
    if(kpis)kpis.innerHTML=
      kpi('Meta acumulada',money(t.target),t.target?(gap>=0?'Meta superada por '+money(gap):'Brecha '+money(Math.abs(gap))):'Sin meta cargada','#ec007c')+
      kpi('Venta '+d.year,money(t.current),d.selected_month?monthLong[d.selected_month-1]:'Meses con PDF','#1769e8')+
      kpi('Venta '+d.previous_year,money(t.previous),'Mismo alcance','#9fb0c6')+
      kpi('Cumplimiento',pct(t.compliance),'Venta / Meta','#10b981',tone(t.compliance,true))+
      kpi('Crecimiento',pct(t.growth),d.year+' vs '+d.previous_year,'#f59e0b',tone(t.growth,false));
    const empty=q('#salesExecEmpty');if(empty)empty.classList.toggle('hidden',n(t.current)>0||n(t.previous)>0||n(t.target)>0);
    const src=q('#salesExecSource');if(src)src.textContent=d.source_label+' · '+d.store;
    const title=q('#salesChartTitle');if(title)title.textContent=d.selected_month?'Venta por tienda · '+monthLong[d.selected_month-1]+' '+d.year:'Venta mensual '+d.year+' vs '+d.previous_year+' · '+d.store;
    const coverage=q('#salesCoverage');if(coverage)coverage.textContent=(d.available_months||[]).length+' PDF/mes disponibles'+(d.cut_date?' · último corte '+d.cut_date:'');
    salesChart176(d);renderSalesTables(d);
  }catch(e){
    console.warn('[V176] ventas',e);
    const src=q('#salesExecSource');if(src)src.textContent='Ventas: no fue posible actualizar en este intento. Conserva la última vista y vuelve a consultar.';
  }finally{salesBusy=false}
}
window.loadSalesExecutive=function(){return renderSales176(null,true)};

async function refreshAll(){
  fixSidebar();fixAnalysisNav();
  if(!activeAnalysis())return;
  installCompactTableFilters();
  await fixStores();
  if(macroActive()){
    renderExcess();
    detachOldSalesListeners();
    await renderSales176();
    await renderArea();
    await renderModels();
  }
}
let v176RefreshTimer=0;
function schedule(){
  clearTimeout(v176RefreshTimer);
  v176RefreshTimer=setTimeout(()=>{refreshAll().catch(e=>console.warn('[V176] refresh',e))},140);
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
  const old=window.loadDash;const wrapped=async function(){const r=await old.apply(this,arguments);setTimeout(()=>{fixSidebar();fixAnalysisNav();installCompactTableFilters();fixStores();renderExcess();detachOldSalesListeners();renderSales176()},60);return r};wrapped.__v176=true;window.loadDash=wrapped;
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
