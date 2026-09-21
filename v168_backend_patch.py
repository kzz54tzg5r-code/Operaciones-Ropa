from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import difflib
import json
import math
import re
import threading
import unicodedata

from fastapi import Request


def install(m):
    if getattr(m, "_V168_BACKEND", False):
        return

    def norm(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.casefold().strip().split())

    def num(value):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def iso_week_start(d: date) -> date:
        return d - timedelta(days=d.weekday())

    def bounds(kind: str, value: str):
        kind = str(kind or "week").lower().strip()
        value = str(value or "").strip()
        today = date.today()
        if kind == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date()
            return d, d
        if kind == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt:
                y, w = int(mt.group(1)), int(mt.group(2))
            else:
                iso = today.isocalendar(); y, w = iso.year, iso.week
            d = date.fromisocalendar(y, w, 1)
            return d, d + timedelta(days=6)
        if kind == "month":
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            y, mo = (int(mt.group(1)), int(mt.group(2))) if mt else (today.year, today.month)
            d = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return d, nxt - timedelta(days=1)
        if kind == "year":
            y = int(value or today.year)
            return date(y, 1, 1), date(y, 12, 31)
        return date(2000, 1, 1), today

    def selected_store(actor, requested):
        try:
            return str(m.effective_store(actor, requested) or "Compañía")
        except Exception:
            return str(requested or "Compañía")

    def accepted(r, selected, area, activity, start, end):
        ds = str(r.get("date") or "")[:10]
        try:
            d = date.fromisoformat(ds)
        except Exception:
            return None
        if not start <= d <= end:
            return None
        if selected != "Compañía" and norm(r.get("store")) != norm(selected):
            return None
        if str(area or "") not in ("", "Todas", "Todos") and norm(r.get("area")) != norm(area):
            return None
        if str(activity or "") not in ("", "Todas", "Todos"):
            a = r.get("activity") or r.get("activity_original") or ""
            if norm(a) != norm(activity):
                return None
        return d

    def hour_of(value):
        raw = str(value or "").strip()
        mt = re.search(r"(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)", raw)
        if mt:
            return int(mt.group(1))
        try:
            x = float(raw)
            if 0 <= x < 1:
                return int(x * 24)
        except Exception:
            pass
        return None

    # Recuperar Acordeón comercial en la configuración persistente.
    try:
        now_txt = datetime.now().astimezone().isoformat(timespec="seconds")
        with m.db() as con:
            con.execute(
                "INSERT INTO report_tab_visibility(tab_key,visible,updated_at,updated_by) VALUES(?,?,?,?) "
                "ON CONFLICT(tab_key) DO UPDATE SET visible=1,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
                ("commercial.accordion", 1, now_txt, "v168-restore"),
            )
    except Exception as exc:
        print(f"[V168] accordion visibility warning: {type(exc).__name__}: {exc}", flush=True)

    # 80/20: compañía = sólo Colgado/Doblado + recuento de exhibiciones.
    if hasattr(m, "_capacity_model_rows") and not getattr(m, "_V168_8020_SCOPE", False):
        old_model_rows = m._capacity_model_rows

        def _location_type_from_record(record):
            pieces = []
            for c in ("Área", "Area", "Ubicación", "Ubicacion", "Ubicación detalle", "Ubicacion detalle", "Pasillo", "Mesa"):
                try:
                    if c in record and str(record.get(c) or "").strip():
                        pieces.append(str(record.get(c)))
                except Exception:
                    pass
            text = norm(" ".join(pieces))
            types = []
            if "colgad" in text or "pasillo" in text:
                types.append("Colgado")
            if "doblad" in text or "mesa" in text or "jean" in text:
                types.append("Doblado")
            return types

        def _split_exhibitions(value):
            text = str(value or "").strip()
            if not text or norm(text) in ("nan", "none", "sin dato", "no aplica", "n/a", "0"):
                return []
            return [x.strip() for x in re.split(r"[,;/|]+", text) if x.strip() and norm(x.strip()) not in ("nan", "none", "0")]

        def model_rows_v168(store="Compañía", section="Todas", mode="80_20", period="", catalog="Todos"):
            rows = list(old_model_rows(store, section, mode, period, catalog) or [])
            if str(mode or "").lower() not in ("80_20", "8020", "top", "champions") or str(store or "") != "Compañía" or not rows:
                return rows
            try:
                frame = m._capacity_frame_for_period(period)
                work = m._capacity_scope_v45(frame, store, section, catalog)
                if work is None or work.empty or "ID_ART" not in work.columns:
                    return rows
                # V176/V166 ya limitan el detalle 80/20 a los modelos visibles.
                # Filtrar antes de convertir a records evita materializar todo el
                # catálogo de Compañía y estabiliza Render en 512 MB.
                wanted_ids = {str(r.get("id_art") or "").strip() for r in rows if str(r.get("id_art") or "").strip()}
                if wanted_ids:
                    article_ids = work["ID_ART"].fillna("").astype(str).str.strip()
                    work = work[article_ids.isin(wanted_ids)]
                loc_map = defaultdict(set)
                ex_map = defaultdict(set)
                columns = set(work.columns)
                ex_col = next((c for c in ("Exhibición", "Exhibicion", "Número exhibición", "Numero exhibicion", "No. Exhibición", "No Exhibicion") if c in columns), None)
                store_col = "Tienda" if "Tienda" in columns else None
                for rec in work.to_dict("records"):
                    rid = str(rec.get("ID_ART") or "").strip()
                    if not rid or rid.lower() in ("nan", "none"):
                        continue
                    for t in _location_type_from_record(rec):
                        loc_map[rid].add(t)
                    if ex_col:
                        st = str(rec.get(store_col) or "") if store_col else ""
                        for ex in _split_exhibitions(rec.get(ex_col)):
                            ex_map[rid].add(f"{st}|{ex}" if st else ex)
                for row in rows:
                    rid = str(row.get("id_art") or "").strip()
                    types = loc_map.get(rid) or set()
                    if "Colgado" in types and "Doblado" in types:
                        loc = "Colgado / Doblado"
                    elif "Colgado" in types:
                        loc = "Colgado"
                    elif "Doblado" in types:
                        loc = "Doblado"
                    else:
                        current = norm(row.get("location"))
                        loc = "Colgado" if ("pasillo" in current or "colgad" in current) else ("Doblado" if ("mesa" in current or "doblad" in current or "jean" in current) else "—")
                    count = len(ex_map.get(rid) or set())
                    row["location"] = loc
                    row["exhibition"] = str(count)
                    row["location_type"] = loc
                    row["exhibition_count"] = count
            except Exception as exc:
                print(f"[V168-8020] warning: {type(exc).__name__}: {exc}", flush=True)
            return rows

        m._capacity_model_rows = model_rows_v168
        m._V168_8020_SCOPE = True

    # Recorridos pivote: tienda en filas, días en columnas.
    DAYS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")

    @m.app.get("/api/operations/routes-pivot-v168")
    def routes_pivot_v168(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor = m.require_user(request)
        selected = selected_store(actor, store)
        start, end = bounds(period_type, period_value)
        grouped = defaultdict(float)
        stores = set(); dates = set()
        for r in list((m.load_ops() or {}).get("rows") or []):
            d = accepted(r, selected, area, activity, start, end)
            if not d:
                continue
            value = num(r.get("recorridos"))
            if value <= 0:
                continue
            st = str(r.get("store") or "Sin tienda").strip() or "Sin tienda"
            grouped[(st, d.isoformat())] += value
            stores.add(st); dates.add(d)
        ordered_dates = sorted(dates)
        rows = []
        for st in sorted(stores, key=lambda x: norm(x)):
            values = [grouped.get((st, d.isoformat()), 0.0) for d in ordered_dates]
            rows.append({"store": st, "values": values, "total": sum(values)})
        return {
            "dates": [{"date": d.isoformat(), "day": DAYS[d.weekday()], "label": d.strftime("%d/%m")} for d in ordered_dates],
            "rows": rows, "total": sum(r["total"] for r in rows), "store": selected,
        }

    # Tendencia = comparación entre periodos, no tarjetas horarias.
    def shift_month(first: date, delta: int) -> date:
        y, mo = first.year, first.month + delta
        while mo <= 0:
            y -= 1; mo += 12
        while mo > 12:
            y += 1; mo -= 12
        return date(y, mo, 1)

    def comparison_windows(kind, value):
        start, end = bounds(kind, value)
        if kind == "day":
            return [(start - timedelta(days=i), start - timedelta(days=i), (start - timedelta(days=i)).strftime("%a %d/%m")) for i in range(6, -1, -1)]
        if kind == "week":
            out = []
            for i in range(3, -1, -1):
                s = start - timedelta(days=7*i); iso = s.isocalendar()
                out.append((s, s + timedelta(days=6), f"{iso.year}-W{iso.week:02d}"))
            return out
        if kind == "month":
            out = []
            for i in range(3, -1, -1):
                s = shift_month(start, -i); nxt = shift_month(s, 1)
                out.append((s, nxt - timedelta(days=1), s.strftime("%Y-%m")))
            return out
        y = start.year
        return [(date(y,mo,1), shift_month(date(y,mo,1),1)-timedelta(days=1), date(y,mo,1).strftime("%b")) for mo in range(1,13)]

    @m.app.get("/api/operations/collection-comparison-v168")
    def collection_comparison_v168(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor = m.require_user(request)
        selected = selected_store(actor, store)
        source = list((m.load_ops() or {}).get("rows") or [])
        periods = []; previous_total = None
        for start, end, label in comparison_windows(str(period_type or "week").lower(), period_value):
            values = {"muertos":0.0, "cajas":0.0, "probador":0.0, "recorridos":0.0}
            for r in source:
                if not accepted(r, selected, area, activity, start, end):
                    continue
                for k in values:
                    values[k] += num(r.get(k))
            total = values["muertos"] + values["cajas"] + values["probador"]
            change = ((total / previous_total) - 1) * 100 if previous_total and previous_total > 0 else None
            periods.append({"label": label, "start": start.isoformat(), "end": end.isoformat(), **values, "total": total, "change_pct": change})
            previous_total = total
        return {"period_type": period_type, "periods": periods, "store": selected}

    # Planeación estadística para la semana siguiente.
    def _recovery_rows(data):
        daily = list(data.get("commercial_daily") or [])
        if daily:
            return daily
        try:
            if hasattr(m, "_get_recovery_fifo_rows"):
                return list(m._get_recovery_fifo_rows(data) or [])
        except Exception:
            pass
        return list(data.get("recovery_fifo") or [])

    def _weighted_average(samples):
        if not samples:
            return 0.0
        recent = samples[-8:]
        weights = [0.55 ** (len(recent)-1-i) for i in range(len(recent))]
        den = sum(weights)
        return sum(num(v) * w for (_, v), w in zip(recent, weights)) / den if den else 0.0

    def _standard_changes_dead():
        try:
            with m.db() as con:
                row = con.execute("SELECT pieces_per_shift FROM operation_standards WHERE origin='Cambios y Muertos'").fetchone()
                if row and num(row["pieces_per_shift"]) > 0:
                    return num(row["pieces_per_shift"])
        except Exception:
            pass
        try:
            with m.db() as con:
                row = con.execute("SELECT value FROM goals WHERE key='productividad_diaria'").fetchone()
                if row and num(row["value"]) > 0:
                    return num(row["value"])
        except Exception:
            pass
        return 784.0

    @m.app.get("/api/operations/next-week-plan-v168")
    def next_week_plan_v168(request: Request, store: str="Compañía"):
        actor = m.require_user(request)
        requested = selected_store(actor, store)
        data = m.load_ops() or {}
        op_rows = list(data.get("rows") or [])
        dev_rows = _recovery_rows(data)
        today = date.today(); current_start = iso_week_start(today); target_start = current_start + timedelta(days=7)
        target_iso = target_start.isocalendar(); standard = _standard_changes_dead()
        all_stores = sorted({str(r.get("store") or "").strip() for r in op_rows + dev_rows if str(r.get("store") or "").strip()}, key=norm)
        if not all_stores:
            try: all_stores = sorted(list(m.store_names(True) or []), key=norm)
            except Exception: all_stores = []
        scope_stores = all_stores if requested == "Compañía" else [requested]
        scope_set = {norm(x) for x in scope_stores}

        week_daily = defaultdict(lambda: {"muertos":0.0,"cajas":0.0,"probador":0.0})
        week_hour = defaultdict(lambda: {"muertos":0.0,"cajas":0.0,"probador":0.0})
        for r in op_rows:
            st = str(r.get("store") or "").strip()
            if not st or norm(st) not in scope_set: continue
            try: d = date.fromisoformat(str(r.get("date") or "")[:10])
            except Exception: continue
            ws = iso_week_start(d); key = (ws, st, d.weekday())
            for k in ("muertos","cajas","probador"): week_daily[key][k] += num(r.get(k))
            h = hour_of(r.get("start_time"))
            if h is not None:
                hk = (ws, st, d.weekday(), h)
                for k in ("muertos","cajas","probador"): week_hour[hk][k] += num(r.get(k))

        dev_daily = defaultdict(float)
        for r in dev_rows:
            st = str(r.get("store") or "").strip()
            if not st or norm(st) not in scope_set: continue
            try: d = date.fromisoformat(str(r.get("date") or "")[:10])
            except Exception: continue
            dev_daily[(iso_week_start(d), st, d.weekday())] += num(r.get("dev_pzs"))

        hist_weeks = sorted({k[0] for k in week_daily if k[0] < current_start} | {k[0] for k in dev_daily if k[0] < current_start})[-8:]

        def predict_for_store_day(st, dow, allowed_weeks):
            vals = {}
            for field in ("muertos","cajas","probador"):
                vals[field] = _weighted_average([(ws, week_daily[(ws,st,dow)][field]) for ws in allowed_weeks])
            vals["devoluciones"] = _weighted_average([(ws, dev_daily[(ws,st,dow)]) for ws in allowed_weeks])
            return vals

        completed_dows = list(range(min(today.weekday(), 6)))
        forecast_now = 0.0; actual_now = 0.0
        if hist_weeks and completed_dows:
            for st in scope_stores:
                for dow in completed_dows:
                    pred = predict_for_store_day(st, dow, hist_weeks)
                    forecast_now += pred["muertos"] + pred["cajas"] + pred["probador"] + pred["devoluciones"]
                    actual = week_daily[(current_start,st,dow)]
                    actual_now += actual["muertos"] + actual["cajas"] + actual["probador"] + dev_daily[(current_start,st,dow)]
        if forecast_now > 0:
            correction = min(1.30, max(0.70, actual_now / forecast_now))
            error_pct = abs(actual_now - forecast_now) / forecast_now * 100
        else:
            correction = 1.0; error_pct = None

        days = []; hourly = defaultdict(lambda: {"muertos":0.0,"cajas":0.0,"probador":0.0})
        for dow in range(7):
            dtarget = target_start + timedelta(days=dow)
            agg = {"muertos":0.0,"cajas":0.0,"probador":0.0,"devoluciones":0.0,"people":0}
            for st in scope_stores:
                pred = predict_for_store_day(st, dow, hist_weeks)
                for k in ("muertos","cajas","probador","devoluciones"):
                    pred[k] *= correction; agg[k] += pred[k]
                workload = pred["muertos"] + pred["cajas"] + pred["probador"] + pred["devoluciones"]
                agg["people"] += int(math.ceil(workload / standard)) if workload > 0 and standard > 0 else 0
                for h in range(24):
                    for field in ("muertos","cajas","probador"):
                        hourly[(dow,h)][field] += _weighted_average([(ws, week_hour[(ws,st,dow,h)][field]) for ws in hist_weeks]) * correction
            agg["total"] = agg["muertos"] + agg["cajas"] + agg["probador"] + agg["devoluciones"]
            days.append({"day": DAYS[dow], "date": dtarget.isoformat(), **agg})

        hour_rows = []
        for h in range(24):
            cells = []; any_value = False
            for dow in range(7):
                x = hourly[(dow,h)]; total = x["muertos"] + x["cajas"] + x["probador"]
                if total > 0.01: any_value = True
                cells.append({**x, "total": total})
            if any_value: hour_rows.append({"hour": h, "label": f"{h:02d}:00", "cells": cells})

        total_workload = sum(x["total"] for x in days)
        return {
            "store": requested, "stores": ["Compañía", *all_stores],
            "target_week": f"{target_iso.year}-W{target_iso.week:02d}",
            "current_week": f"{current_start.isocalendar().year}-W{current_start.isocalendar().week:02d}",
            "standard": standard, "days": days, "hours": hour_rows,
            "total_workload": total_workload, "people_week_sum": sum(int(x["people"]) for x in days),
            "error": {"actual": actual_now, "forecast": forecast_now, "margin_error_pct": error_pct, "correction_factor": correction},
            "method": "Promedio ponderado de hasta 8 semanas por tienda/día/hora, con mayor peso a semanas recientes y corrección limitada a ±30% según el error real de la semana en curso. Devoluciones se proyecta por día; no se le inventa horario.",
        }

    # OCR de PDF de ventas rasterizados (Qlik): página 1, resumen ejecutivo.
    STORE_CODES = {
        "VALLE":"Vallejo", "IZTAP":"Iztapalapa", "ECATE":"Ecatepec", "NAUCA":"Naucalpan",
        "PUESU":"Puebla Sur", "IXTAP":"Ixtapaluca", "CENTR":"Centro", "ARCO":"Arco Norte",
        "OLIVA":"Olivar", "PUEBL":"Puebla", "TOLUC":"Toluca", "QUERE":"Querétaro",
        "VERAC":"Veracruz", "ATEMA":"Atemajac", "LEON":"León", "MIRAV":"Miravalle", "AGUAS":"Aguascalientes",
    }
    OCR_DIR = Path(getattr(m, "DATA_ROOT", Path.home()/"OperacionesRopaData")) / "commercial" / "sales_ocr_v168"
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    OCR_LOCK = threading.RLock()

    def clean_code(value):
        return re.sub(r"[^A-Z]", "", str(value or "").upper().replace("1","I").replace("0","O"))

    def match_code(value):
        text = clean_code(value)
        if not text or text.startswith("TOTAL"): return None
        best = None
        for code in STORE_CODES:
            score = difflib.SequenceMatcher(None, text, code).ratio()
            if best is None or score > best[0]: best = (score, code)
        return best if best and best[0] >= 0.55 else None

    def parse_number_token(value):
        raw = str(value or "").replace("$","").replace(",","").replace(" ","").replace("O","0").replace("o","0")
        raw = re.sub(r"[^0-9.-]", "", raw)
        try: return float(raw)
        except Exception: return 0.0

    def choose_consistent(raw_value, current, diff_abs):
        raw_value = num(raw_value); current = num(current); diff_abs = abs(num(diff_abs))
        if current <= 0 or diff_abs <= 0: return raw_value
        candidates = [max(current - diff_abs, 0.0), current + diff_abs]
        if raw_value <= 0: return min(candidates)
        return min(candidates, key=lambda x: abs(x - raw_value))

    def choose_from_signed_diff(raw_value, current, signed_diff):
        raw_value = num(raw_value); current = num(current); signed_diff = num(signed_diff)
        if raw_value > 0:
            return choose_consistent(raw_value, current, signed_diff)
        # En el resumen del PDF las columnas "Dif. Meta" / "Dif. 2025"
        # representan Venta actual - referencia. Conservar el signo permite
        # reconstruir la referencia cuando OCR pierde únicamente esa celda.
        inferred = current - signed_diff
        if current > 0 and signed_diff != 0 and inferred > 0:
            ratio = inferred / current
            if .20 <= ratio <= 3.0:
                return inferred
        return 0.0

    def ocr_sales_pdf(path: Path, cache_key: str):
        cache = OCR_DIR / f"{re.sub(r'[^A-Za-z0-9_-]+','_',cache_key or path.stem)}.json"
        try:
            if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
                cached = json.loads(cache.read_text(encoding="utf-8"))
                cached_stores = cached.get("stores") or {}
                toluca = cached_stores.get("Toluca") or {}
                puebla_sur = cached_stores.get("Puebla Sur") or {}
                # Reprocesar sólo los PDF cuyo caché viejo quedó incompleto:
                # Toluca sin año anterior o Puebla Sur (post-apertura) sin meta.
                # Así no forzamos OCR de todos los meses históricos.
                needs_toluca = num(toluca.get("current")) > 0 and num(toluca.get("previous")) <= 0
                needs_puebla_sur = num(puebla_sur.get("current")) > 0 and num(puebla_sur.get("target")) <= 0
                if not (needs_toluca or needs_puebla_sur):
                    return cached
        except Exception: pass
        result = {"company":{}, "stores":{}, "cut_date":"", "ocr":False, "error":""}
        try:
            import pdfplumber
            import pytesseract
            from pytesseract import Output
            with pdfplumber.open(path) as pdf:
                if not pdf.pages: return result
                page = pdf.pages[0]; text = page.extract_text() or ""
                mt = re.search(r"Corte\s+al\s+(\d{2}/\d{2}/\d{4})", text, re.I)
                if mt: result["cut_date"] = mt.group(1)
                image = page.to_image(resolution=180).original
            w, h = image.size

            total_crop = image.crop((int(.03*w), int(.94*h), int(.97*w), int(.992*h)))
            total_text = pytesseract.image_to_string(total_crop.resize((total_crop.width*2, total_crop.height*2)), lang="eng", config="--psm 6")
            total_line = next((x for x in total_text.splitlines() if norm(x).startswith("total")), "")
            money_vals = [parse_number_token(x) for x in re.findall(r"[$€£¢]?\s*\d[\d,]{3,}", total_line)]
            big = [v for v in money_vals if v >= 500000]
            if len(big) >= 3:
                goal, previous, current = big[0], big[1], big[2]
                before_money = total_line.split("$",1)[0] if "$" in total_line else total_line
                nums_before = [parse_number_token(x) for x in re.findall(r"\d{1,3}(?:,\d{3})+", before_money)]
                pieces_prev = nums_before[-2] if len(nums_before) >= 2 else 0; pieces_cur = nums_before[-1] if nums_before else 0
                result["company"] = {"target":goal,"previous":previous,"current":current,"pieces_previous":pieces_prev,"pieces":pieces_cur}

            summary_crop = image.crop((int(.03*w), int(.66*h), int(.97*w), int(.985*h)))
            df = pytesseract.image_to_data(summary_crop, lang="eng", config="--psm 6", output_type=Output.DATAFRAME)
            try: df = df.dropna(subset=["text"])
            except Exception: pass
            tokens=[]
            for _, row in df.iterrows():
                txt=str(row.get("text") or "").strip()
                if txt: tokens.append({"text":txt,"left":float(row.get("left") or 0),"top":float(row.get("top") or 0),"width":float(row.get("width") or 0)})
            tokens.sort(key=lambda x:x["top"]); groups=[]
            for token in tokens:
                target=None
                for group in reversed(groups[-6:]):
                    if abs(group["top"]-token["top"])<=6: target=group; break
                if target is None: target={"top":token["top"],"tokens":[]}; groups.append(target)
                target["tokens"].append(token)
            cw=summary_crop.size[0]; parsed={}
            for group in groups:
                line=sorted(group["tokens"],key=lambda x:x["left"]); code_candidates=[]
                for token in line:
                    xc=(token["left"]+token["width"]/2)/cw
                    if xc<.18 or xc>.84:
                        match=match_code(token["text"])
                        if match: code_candidates.append((match[0]+(.15 if xc>.84 else 0),match[1]))
                if not code_candidates: continue
                code=max(code_candidates,key=lambda x:x[0])[1]
                def zone(a,b):
                    vals=[]
                    for token in line:
                        xc=(token["left"]+token["width"]/2)/cw
                        if a<=xc<b and re.search(r"\d",token["text"]): vals.append(parse_number_token(token["text"]))
                    return max(vals,key=lambda x:abs(x)) if vals else 0.0
                raw_goal=zone(.40,.48); raw_prev=zone(.48,.545); current=zone(.545,.625); diff_goal=zone(.675,.755); diff_prev=zone(.805,.86)
                goal=choose_from_signed_diff(raw_goal,current,diff_goal)
                previous=choose_from_signed_diff(raw_prev,current,diff_prev)
                record={"store":STORE_CODES[code],"target":goal,"previous":previous,"current":current,"pieces_previous":zone(.15,.215),"pieces":zone(.215,.30),"code":code}
                score=record["current"]+record["previous"]+record["target"]; old=parsed.get(code)
                if old is None or score>old[0]: parsed[code]=(score,record)
            result["stores"]={v[1]["store"]:v[1] for v in parsed.values()}; result["ocr"]=bool(result["company"].get("current") or result["stores"])
            cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as exc:
            result["error"]=f"{type(exc).__name__}: {exc}"; print(f"[V168-OCR] {path.name}: {result['error']}",flush=True)
        return result

    def sales_entries_v168():
        return [dict(x) for x in list((m.load_manifest() or {}).get("sales") or []) if int(x.get("year") or 0)>0 and int(x.get("month") or 0) in range(1,13)]

    def ocr_for_entry(entry):
        with OCR_LOCK:
            try:
                path=m.resolve_entry_path(entry)
                if not path.exists() or path.suffix.lower()!=".pdf": return {}
                payload=ocr_sales_pdf(path,str(entry.get("id") or path.stem)); comp=payload.get("company") or {}
                if num(comp.get("current"))>0:
                    changes={"total_sales":num(comp.get("current")),"total_pieces":num(comp.get("pieces")),"target_sales":num(comp.get("target")),"previous_sales":num(comp.get("previous")),"parser_version":168,"source_method":"OCR · Resumen Ejecutivo Acumulado","status":"Procesado · OCR V168"}
                    try: m.update_entry("sales",str(entry.get("id") or ""),**changes)
                    except Exception: pass
                    entry.update(changes)
                return payload
            except Exception as exc:
                print(f"[V168-OCR] entry warning: {type(exc).__name__}: {exc}",flush=True); return {}

    @m.app.get("/api/commercial-sales-v168")
    def commercial_sales_v168(request: Request, year: int|None=None, through_month: int|None=None, store: str="Compañía"):
        actor=m.require_user(request); yy=int(year or datetime.now().year); cut=max(1,min(12,int(through_month or datetime.now().month))); scope=selected_store(actor,store)
        entries=sales_entries_v168(); latest={}
        for entry in entries:
            if int(entry.get("year") or 0)!=yy: continue
            mo=int(entry.get("month") or 0); old=latest.get(mo)
            if old is None or str(entry.get("uploaded_at") or "")>=str(old.get("uploaded_at") or ""): latest[mo]=entry
        labels=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]; months=[]; store_rows=[]; source_count=0; last_cut=""
        for mo in range(1,13):
            entry=latest.get(mo); current=previous=target=pieces=0.0; source=""; ocr_payload={}
            if entry:
                ocr_payload=ocr_for_entry(entry); c=(ocr_payload.get("company") or {}) if scope=="Compañía" else ((ocr_payload.get("stores") or {}).get(scope) or {})
                if c:
                    current=num(c.get("current")); previous=num(c.get("previous")); target=num(c.get("target")); pieces=num(c.get("pieces")); source="OCR PDF"
                elif scope=="Compañía":
                    current=num(entry.get("total_sales")); previous=num(entry.get("previous_sales")); target=num(entry.get("target_sales")); pieces=num(entry.get("total_pieces")); source=str(entry.get("source_method") or "PDF")
                if current>0 or previous>0 or target>0: source_count+=1
                last_cut=str(ocr_payload.get("cut_date") or last_cut)
                if mo==cut and ocr_payload.get("stores"): store_rows=list((ocr_payload.get("stores") or {}).values())
            months.append({"month":mo,"label":labels[mo-1],"current":current,"previous":previous,"target":target,"pieces":pieces,"compliance":current/target*100 if target else None,"growth":(current/previous-1)*100 if previous else None,"diff_goal":current-target if target else None,"diff_previous":current-previous if previous else None,"source":source})
        use=months[:cut]; tc=sum(x["current"] for x in use); tp=sum(x["previous"] for x in use); tg=sum(x["target"] for x in use)
        store_rows.sort(key=lambda x:num(x.get("current")),reverse=True)
        for i,r in enumerate(store_rows,1):
            r["rank"]=i; r["diff_goal"]=num(r.get("current"))-num(r.get("target")) if num(r.get("target")) else None; r["diff_previous"]=num(r.get("current"))-num(r.get("previous")) if num(r.get("previous")) else None; r["pct_goal"]=num(r.get("current"))/num(r.get("target"))*100 if num(r.get("target")) else None; r["pct_previous"]=(num(r.get("current"))/num(r.get("previous"))-1)*100 if num(r.get("previous")) else None
        return {"year":yy,"previous_year":yy-1,"through_month":cut,"store":scope,"months":months,"stores":store_rows,"available_years":sorted({int(x.get("year") or 0) for x in entries if int(x.get("year") or 0)>0}|{yy},reverse=True),"totals":{"current":tc,"previous":tp,"target":tg,"compliance":tc/tg*100 if tg else None,"growth":(tc/tp-1)*100 if tp else None,"diff_goal":tc-tg if tg else None,"diff_previous":tc-tp if tp else None},"source_count":source_count,"cut_date":last_cut,"source_label":"PDF Meta de Ventas · Resumen Ejecutivo Acumulado (OCR V168)"}

    m._V168_BACKEND = True
    print("[V168-BACKEND] 80/20, recorridos pivote, comparativos, forecast y OCR de ventas instalados.", flush=True)
