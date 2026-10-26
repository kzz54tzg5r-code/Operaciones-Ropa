"""V331 · Vista paralela y auditable de Tasa de recuperación.

No sustituye la V243. Reutiliza su cache de ventas/devoluciones diarias y
recalcula la existencia con SUMA de filas fuente, como el motor Sell Through.
No inventa entradas, salidas ni fechas de habilitado no presentes en la fuente.
"""
from __future__ import annotations

import math
import json
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta

from fastapi import Request
from fastapi.responses import HTMLResponse

VIEW_KEY = "operations.recovery_audit"
VIEW_NAME = "Tasa de recuperación · Revisión"
MAX_CUT_AGE_DAYS = 7


def insert_before_document_body_end(page: str, fragment: str) -> str:
    """Insert at the LAST closing body tag, not tags quoted inside other JS.

    V314 contains document.write('</body></html>') inside a <script>. Using
    str.replace('</body>', ..., 1) injects our <script> into that JavaScript,
    breaks the host document and prints its remainder as visible text.
    """
    lower = page.lower()
    index = lower.rfind("</body>")
    if index < 0:
        return page + fragment
    return page[:index] + fragment + page[index:]


def safe_number(value):
    try:
        v = float(value or 0)
        return v if math.isfinite(v) else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def cut_quality(period_start, cut_date, max_age_days=MAX_CUT_AGE_DAYS):
    """Devuelve estado, edad; jamás valida cortes futuros o demasiado viejos."""
    if not cut_date:
        return "sin_corte", None
    age = (period_start - cut_date).days
    if age < 0:
        return "corte_futuro", age
    if age > max_age_days:
        return "corte_antiguo", age
    return ("coincidente" if age == 0 else "estimado"), age


def corrected_stock(frame, normalize_store):
    """Suma existencias por tienda/ID, incluidas ubicaciones independientes.

    Las filas del archivo de capacidades son registros de inventario, NO
    snapshots duplicados que deban colapsarse con max(ID_ART).
    """
    import pandas as pd

    if frame is None or frame.empty or "Tienda" not in frame or "ID_ART" not in frame:
        return {}
    keys = frame["Tienda"].fillna("").astype(str).map(normalize_store)
    articles = frame["ID_ART"].fillna("").astype(str).str.strip()
    if "Existencia" in frame:
        qty = pd.to_numeric(frame["Existencia"], errors="coerce").fillna(0.0)
    else:
        floor = pd.to_numeric(frame["Existencia piso"], errors="coerce").fillna(0.0) if "Existencia piso" in frame else pd.Series(0.0, index=frame.index)
        storehouse = pd.to_numeric(frame["Existencia bodega"], errors="coerce").fillna(0.0) if "Existencia bodega" in frame else pd.Series(0.0, index=frame.index)
        qty = floor + storehouse
    compact = pd.DataFrame({"store": keys, "id": articles, "qty": qty})
    compact = compact[(compact["store"] != "") & (~compact["id"].isin(["", "nan", "None"]))]
    if compact.empty:
        return {}
    by_model = compact.groupby(["store", "id"], observed=True, sort=False)["qty"].sum()
    total = by_model.groupby(level=0, sort=False).sum()
    return {str(k): max(safe_number(v), 0.0) for k, v in total.items()}


def revise_payload(raw, stocks, source_date, source_name, period_start,
                   max_age_days=MAX_CUT_AGE_DAYS):
    """Cálculo puro: sólo publica tasas cuando todos sus supuestos se cumplen."""
    result = dict(raw)
    state, age = cut_quality(period_start, source_date, max_age_days)
    usable_cut = state in ("coincidente", "estimado")
    rows = []
    incomplete = []
    warnings = [
        "Las devoluciones proceden del Excel de Cambios y Muertos. La fuente no certifica que cada pieza ya haya sido habilitada y ubicada en piso.",
        "Las ventas corresponden al total registrado para el periodo, no necesariamente a venta atribuible a devoluciones.",
        "No se dispone en esta vista de entradas, salidas, traspasos y ajustes completos; el stock residual es teórico, no existencia física conciliada.",
    ]
    if state == "corte_futuro":
        warnings.append("Se encontró un corte POSTERIOR al inicio del periodo. Se anula la tasa: usarlo introduciría información futura.")
    elif state == "corte_antiguo":
        warnings.append("El corte de stock tiene " + str(age) + " días de antigüedad; límite permitido: " + str(max_age_days) + ". Se anula la tasa.")
    elif state == "sin_corte":
        warnings.append("No hay corte de capacidades para establecer inventario inicial.")
    elif state == "estimado":
        warnings.append("El corte precede el inicio del periodo por " + str(age) + " días. La tasa es una estimación pendiente de conciliación de movimientos.")

    for row in raw.get("rows") or []:
        item = dict(row)
        store = str(item.get("store") or "")
        has_stock = store in stocks
        initial = safe_number(stocks.get(store)) if has_stock else None
        dev = safe_number(item.get("dev_pzs"))
        sales = safe_number(item.get("sales_pzs"))
        sales_value = safe_number(item.get("sales_value"))
        available = (initial + dev) if initial is not None else None
        balance = (available - sales) if available is not None else None
        valid = usable_cut and has_stock and bool(available and available > 0) and sales <= available
        if not usable_cut:
            status = state
        elif not has_stock:
            status = "sin_stock_tienda"
        elif available is None or available <= 0:
            status = "sin_base"
        elif sales > available:
            status = "ventas_superan_base"
        else:
            status = state
        if not valid:
            incomplete.append(store)
        item.update({
            "stock_available": has_stock,
            "inv_initial_pzs": initial,
            "inv_total_pzs": available,
            "inv_final_pzs": balance,
            "sell_through_pct": (sales / available * 100.0) if valid else None,
            "impact_dev_pct": (dev / available * 100.0) if valid else None,
            "inv_total_amount": None,  # No convertir piezas a pesos con precio de venta.
            "inv_final_amount": None,  # Valor de stock requiere costo unitario real.
            "data_quality": status,
            "audit_valid": valid,
            "registered_returns_pzs": dev,
            "verified_enabled_returns_pzs": None,
            "sales_total_pzs": sales,
            "sales_value": sales_value,
        })
        rows.append(item)

    totals = {
        "inv_initial_pzs": sum(safe_number(r["inv_initial_pzs"]) for r in rows if r["inv_initial_pzs"] is not None),
        "dev_pzs": sum(safe_number(r["dev_pzs"]) for r in rows),
        "sales_pzs": sum(safe_number(r["sales_pzs"]) for r in rows),
        "sales_value": sum(safe_number(r["sales_value"]) for r in rows),
    }
    totals["inv_total_pzs"] = totals["inv_initial_pzs"] + totals["dev_pzs"]
    totals["inv_final_pzs"] = totals["inv_total_pzs"] - totals["sales_pzs"]
    complete = bool(rows) and not incomplete
    totals["sell_through_pct"] = (totals["sales_pzs"] / totals["inv_total_pzs"] * 100.0
                                  if complete and totals["inv_total_pzs"] > 0 else None)
    totals["impact_dev_pct"] = (totals["dev_pzs"] / totals["inv_total_pzs"] * 100.0
                                if complete and totals["inv_total_pzs"] > 0 else None)
    totals["stock_complete"] = complete
    totals["valid_stores"] = sum(1 for r in rows if r["audit_valid"])
    totals["stores_in_scope"] = len(rows)
    totals["inv_total_amount"] = None
    totals["inv_final_amount"] = None

    if incomplete:
        warnings.append("Sin indicador confiable para: " + ", ".join(incomplete) + ". El indicador de Compañía queda suspendido hasta completar la conciliación.")
    if any(r["data_quality"] == "ventas_superan_base" for r in rows):
        warnings.append("Las ventas superan el inventario estimado en al menos una tienda. Revisar movimientos omitidos antes de calcular una tasa.")

    trend = []
    for point in raw.get("trend") or []:
        p = dict(point)
        base = totals["inv_initial_pzs"] + safe_number(p.get("dev_pzs"))
        sold = safe_number(p.get("sales_pzs"))
        p["inv_total_pzs"] = base if complete else None
        p["sell_through_pct"] = (100.0 * sold / base if complete and base > 0 and sold <= base else None)
        trend.append(p)

    result.update({
        "rows": rows,
        "metrics": totals,
        "trend": trend,
        "stock_source_date": source_date.isoformat() if source_date else None,
        "stock_source_name": source_name,
        "audit": {
            "model": "Stock inicial del corte + devoluciones registradas - ventas totales",
            "cut_status": state,
            "cut_age_days": age,
            "max_cut_age_days": max_age_days,
            "stock_conciliated": False,
            "returns_enabled_verified": False,
            "all_inventory_movements_verified": False,
            "valid_store_count": totals["valid_stores"],
            "total_store_count": totals["stores_in_scope"],
        },
        "warnings": warnings,
        "definition": "Tasa estimada = ventas registradas / (stock inicial + devoluciones registradas) × 100. No equivale a conversión comprobada de devoluciones.",
    })
    return result


def install(m):
    if getattr(m, "_V331_RECOVERY_AUDIT", False):
        return
    m.REPORT_TABS[VIEW_KEY] = VIEW_NAME

    baseline = next((route.endpoint for route in m.app.routes
                     if getattr(route, "path", "") == "/api/operations/recovery-rate"), None)
    if baseline is None:
        raise RuntimeError("V331 requiere el endpoint de V243 previamente instalado")


    # Lightweight daily aggregate in existing V243 sqlite; inventory summary
    # is written to disk once per cut in a daemon worker, not per HTTP request.
    daily_path = m.DATA_ROOT / "recovery_rate_daily_v243.sqlite3"
    stock_file = m.DATA_ROOT / "recovery_audit_stock_v331.json"
    lock = threading.Lock()
    state = {"key": "", "stocks": None, "building": False, "error": "", "retry_at": 0.0}

    def bounds(mode, value):
        try:
            if mode == "day":
                d = date.fromisoformat(value)
                return d, d
            if mode == "week":
                year, week = value.split("-W", 1)
                d = date.fromisocalendar(int(year), int(week), 1)
                return d, d + timedelta(days=6)
            if mode == "month":
                d = datetime.strptime(value, "%Y-%m").date().replace(day=1)
                after = date(d.year + int(d.month == 12), d.month % 12 + 1, 1)
                return d, after - timedelta(days=1)
            if mode == "year":
                d = date(int(value), 1, 1)
                return d, date(d.year, 12, 31)
        except (ValueError, TypeError, OverflowError, AttributeError):
            raise ValueError("Periodo inválido para la vista seleccionada.")
        raise ValueError("Vista inválida. Selecciona día, semana, mes o año.")

    def meta():
        try:
            data = m.load_operations_meta()
        except Exception:
            data = {}
        d = data.get("available_dates") or []
        w = data.get("available_weeks") or []
        mo = data.get("available_months") or []
        return {"available_dates": d, "available_weeks": w, "available_months": mo,
                "available_years": sorted({str(x)[:4] for x in mo if str(x)[:4].isdigit()})}

    def cut_for_start(start):
        try:
            entries = list(m._capacity_processed_entries() or [])
        except Exception:
            entries = []
        dated = []
        for item in entries:
            try:
                dated.append((m._capacity_report_date(item), str(item.get("uploaded_at") or ""), item))
            except Exception:
                continue
        prev = [x for x in dated if x[0] <= start]
        if prev:
            d, _, item = max(prev, key=lambda x: (x[0], x[1]))
        elif dated:
            d, _, item = min(dated, key=lambda x: (x[0], x[1]))
        else:
            return None, None, ""
        return item, d, str(item.get("name") or item.get("id") or "")

    def stock_summary(item, cut_date):
        key = "|".join((str(item.get("id") or ""), str(item.get("sha256") or ""),
                        str(cut_date), "schema2"))
        with lock:
            if state["key"] == key and isinstance(state["stocks"], dict):
                return dict(state["stocks"]), "ready"
            # Never load two full 192k-row capacity frames concurrently.
            if state["building"]:
                return {}, "building"
            if stock_file.exists():
                try:
                    saved = json.loads(stock_file.read_text(encoding="utf-8"))
                    if saved.get("key") == key and isinstance(saved.get("stocks"), dict):
                        state.update(key=key, stocks=saved["stocks"], building=False, error="")
                        return dict(state["stocks"]), "ready"
                except Exception:
                    pass
            if state["key"] == key and time.monotonic() < state["retry_at"]:
                return {}, "error"
            state.update(key=key, stocks=None, building=True, error="")

        def build():
            try:
                frame = m._load_capacity_compact_cache(item)
                stocks = corrected_stock(frame, m._normalize_store_value)
                del frame
                if not stocks:
                    raise ValueError("El corte no tiene existencia disponible por tienda.")
                temp = stock_file.with_name(stock_file.name + ".tmp")
                try:
                    temp.write_text(json.dumps({"key": key, "stocks": stocks}, ensure_ascii=False), encoding="utf-8")
                    temp.replace(stock_file)
                except Exception:
                    temp.unlink(missing_ok=True)
                with lock:
                    if state["key"] == key:
                        state.update(stocks=stocks, building=False, error="")
            except Exception as exc:
                with lock:
                    if state["key"] == key:
                        state.update(building=False, error=type(exc).__name__,
                                     retry_at=time.monotonic() + 60)
                print("[V331] Error preparando stock:", type(exc).__name__, str(exc)[:160], flush=True)
            finally:
                try:
                    m._release_process_memory()
                except Exception:
                    pass

        threading.Thread(target=build, daemon=True, name="recovery-audit-stock").start()
        return {}, "building"

    def daily_aggregate(start, end, selected, allowed):
        con = sqlite3.connect("file:" + str(daily_path) + "?mode=ro", uri=True, timeout=2)
        try:
            src = m.DATA_ROOT / "cambios_muertos_actual.xlsx"
            if not src.exists():
                return None, None
            st = src.stat()
            stamp = str(st.st_mtime_ns) + ":" + str(st.st_size)
            dbmeta = dict(con.execute("SELECT k,v FROM meta"))
            if dbmeta.get("version") != "243.1" or dbmeta.get("source_stamp") != stamp:
                return None, None
            sql = ("SELECT store,SUM(sales),SUM(dev),SUM(sales_value) "
                   "FROM daily WHERE date>=? AND date<=? ")
            args = [start.isoformat(), end.isoformat()]
            if selected != "Compañía":
                sql += "AND store=? "
                args.append(selected)
            sql += "GROUP BY store"
            events = {
                str(s): {"sales_pzs": safe_number(v), "dev_pzs": safe_number(d),
                         "sales_value": safe_number(amount)}
                for s, v, d, amount in con.execute(sql, args)
                if selected != "Compañía" or not allowed or s in allowed
            }
            return events, con.execute("SELECT MAX(date) FROM daily").fetchone()[0]
        finally:
            con.close()

    @m.app.get("/api/operations/recovery-rate-audit-v331")
    def rate_audit(request: Request, store: str = "Compañía",
                   period_type: str = "week", period_value: str = ""):
        # Same authenticated store restriction as original V243.
        user = m.require_user(request)
        selected = m.effective_store(user, store)
        metadata = meta()
        if not period_value:
            k = {"day": "available_dates", "week": "available_weeks",
                 "month": "available_months", "year": "available_years"}.get(period_type)
            period_value = (metadata.get(k) or [""])[-1]
        try:
            start, end = bounds(period_type, period_value)
        except ValueError as exc:
            return {**metadata, "status": "error", "error": str(exc)}

        try:
            allowed = {m._normalize_store_value(s) for s in m.store_names(True)}
        except Exception:
            allowed = set()
        try:
            events, last_date = daily_aggregate(start, end, selected, allowed)
        except (sqlite3.Error, OSError, ValueError):
            events, last_date = None, None

        if events is None:
            # V243 performs its own background rebuild when SQLite is missing.
            try:
                result = baseline(request=request, store=selected,
                                  period_type=period_type, period_value=period_value)
                return {**metadata, "status": result.get("status") or "building",
                        "error": result.get("error") or "",
                        "phase": "sales", "retry_seconds": 5}
            except Exception as exc:
                return {**metadata, "status": "error",
                        "error": "No fue posible preparar ventas: " + type(exc).__name__}

        item, cut_date, name = cut_for_start(start)
        cut_status, days = cut_quality(start, cut_date)
        stocks, phase = {}, "not_applicable"
        if item and cut_status in ("coincidente", "estimado"):
            stocks, phase = stock_summary(item, cut_date)
        scope = [selected] if selected != "Compañía" else sorted(allowed or set(events))
        try:
            projects = {m._normalize_store_value(s) for s in m.project_store_names(True)}
        except Exception:
            projects = set()
        rows = [{
            "store": s, "period": period_value, "is_project": s in projects,
            "dev_pzs": events.get(s, {}).get("dev_pzs", 0.0),
            "sales_pzs": events.get(s, {}).get("sales_pzs", 0.0),
            "sales_value": events.get(s, {}).get("sales_value", 0.0),
        } for s in scope]
        raw = {"status": "ready", "available": True,
               "period_start": start.isoformat(), "period_end": end.isoformat(),
               "period_type": period_type, "period_value": period_value,
               "rows": rows, "trend": [], **metadata}
        data = revise_payload(raw, stocks, cut_date, name, start)
        data["audit"]["stock_phase"] = phase
        data["audit"]["source_last_date"] = last_date
        if phase == "building":
            data["warnings"].append("Preparando el corte de inventario una sola vez. Ventas y devoluciones ya están disponibles.")
            data["retry_seconds"] = 4
        elif phase == "error":
            data["warnings"].append("No fue posible procesar el stock. Se permite reintentar después de 60 segundos.")
            data["retry_seconds"] = 60
        data["audit"]["period_partial"] = bool(last_date and end.isoformat() > last_date)
        if data["audit"]["period_partial"]:
            data["warnings"].append("Periodo parcial: información publicada hasta el " + last_date + ".")
        return data

    css = """<style id="v331-recovery-audit-css">
.v331-root{font-family:inherit;color:#173b69}
.v331-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;background:linear-gradient(110deg,#f1f6ff,#fff);border:1px solid #cbdcf0;border-radius:12px;padding:11px 13px;margin:8px 0}
.v331-toolbar b{font-size:12px;color:#143c73}.v331-toolbar small{color:#607590;font-size:10px}
.v331-tags{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.v331-pill{font-size:10px;font-weight:850;border-radius:999px;padding:5px 9px;background:#eaf0fa;color:#214d7d;white-space:nowrap}
.v331-pill.warn{background:#fff1d7;color:#966213}.v331-pill.fail{background:#fff0f0;color:#ac3030}.v331-pill.ok{background:#dff7ed;color:#087951}
.v331-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:10px 0}
.v331-card{background:#fff;border:1px solid #dce5f0;border-radius:12px;padding:12px 12px 10px;min-width:0;box-shadow:0 2px 7px #193f7410;position:relative;overflow:hidden}
.v331-card:before{content:"";position:absolute;inset:0 auto 0 0;background:var(--accent,#1d6fcb);width:3px}
.v331-card .label{font-size:10px;font-weight:800;text-transform:uppercase;line-height:1.3;color:#637893}
.v331-card .number{display:block;font-size:clamp(16px,1.5vw,24px);line-height:1.2;font-weight:950;letter-spacing:-.035em;color:#163e78;margin:7px 0 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v331-card .hint{font-size:10px;line-height:1.3;color:#60748b}
.v331-bottom{display:grid;grid-template-columns:minmax(260px,0.9fr) minmax(0,2fr);gap:10px;margin:12px 0}
.v331-panel{background:#fff;border:1px solid #dce5f0;border-radius:12px;min-width:0;overflow:hidden}
.v331-panelhead{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 13px;border-bottom:1px solid #e7edf5}
.v331-panelhead b{font-size:12px;color:#123d72}.v331-panelhead small{font-size:10px;color:#667a90}
.v331-rank{padding:11px 13px;max-height:310px;overflow-y:auto}
.v331-rankrow{display:grid;grid-template-columns:minmax(75px,1fr) 2fr 48px;gap:8px;align-items:center;margin:0 0 11px;font-size:10px;font-weight:750}
.v331-rankrow .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.v331-track{background:#e8f0fa;height:8px;border-radius:99px;overflow:hidden}
.v331-fill{height:100%;background:linear-gradient(90deg,#0b64c9,#37a3fc);border-radius:99px}
.v331-tablewrap{overflow-x:auto;width:100%;max-height:355px;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}
.v331-table{width:100%;min-width:910px;border-collapse:separate;border-spacing:0;font-size:11px;font-variant-numeric:tabular-nums}
.v331-table th,.v331-table td{padding:10px 9px;text-align:right;border-bottom:1px solid #ebeff5;white-space:nowrap}
.v331-table th{position:sticky;top:0;background:#edf4ff;z-index:2;text-transform:uppercase;color:#244c7b;font-size:9px;letter-spacing:.01em}
.v331-table td:first-child,.v331-table th:first-child{text-align:left;position:sticky;left:0;background:#fff;z-index:1}
.v331-table th:first-child{z-index:3;background:#edf4ff}
.v331-table tr:nth-child(even) td{background:#f8fbff}
.v331-table tr:nth-child(even) td:first-child{background:#f8fbff}
.v331-table tr.project-row td{background:#edf5ff}.v331-table tr.project-row td:first-child{background:#edf5ff}
.v331-quality{font-size:9px;white-space:nowrap;font-weight:850}
.v331-quality.warn{color:#9a6711}.v331-quality.fail{color:#bd3940}.v331-quality.ok{color:#087951}
.v331-empty{padding:18px;color:#627990;font-size:11px;line-height:1.5;text-align:center}
.v331-disclosure{border:1px solid #dce5f0;border-radius:11px;background:#fff;margin:9px 0;overflow:hidden}
.v331-disclosure summary{list-style:none;cursor:pointer;padding:11px 13px;font-size:11px;font-weight:850;color:#1b4a7e}
.v331-disclosure summary:after{content:"▾";float:right}
.v331-disclosure[open] summary:after{content:"▴"}
.v331-disclosure .details{padding:0 14px 13px;font-size:11px;line-height:1.5;color:#5d7087}
.v331-disclosure ul{margin:8px 0 0;padding-left:17px}
.v331-actions{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:7px 0 13px;flex-wrap:wrap}
.v331-actions p{margin:0;color:#64788e;font-size:10px}
.v331-retry{border:1px solid #b4cef1;border-radius:8px;background:#fff;color:#165ca8;font-weight:850;padding:7px 11px;font-size:11px;cursor:pointer}
.v331-retry:hover{background:#eef6ff}
@media(max-width:1300px){.v331-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:850px){.v331-bottom{grid-template-columns:1fr}.v331-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v331-card{padding:10px}.v331-card .number{font-size:19px}.v331-panelhead{padding:10px}}
</style>"""
    script = """<script id="v331-recovery-audit-js">
(function(){
 if(window.__v331AuditVisualInstalled)return;
 window.__v331AuditVisualInstalled=true;
 var esc=function(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})};
 var n=function(v){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('es-MX',{maximumFractionDigits:0})};
 var pct=function(v){return v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1})+'%'};
 var mxn=function(v){if(v==null||!Number.isFinite(Number(v)))return '—';var p=Number(v);return p===0?'$0 mil':'
 var titles={coincidente:'Corte coincidente',estimado:'Corte cercano',sin_corte:'Sin corte',corte_futuro:'Corte posterior',corte_antiguo:'Corte antiguo',sin_stock_tienda:'Falta stock',sin_base:'Sin base',ventas_superan_base:'Revisar ventas'};
 var title=function(s){return titles[s]||'Revisar dato'};
 var icon=function(k){return k==='ok'?'✓':k==='fail'?'!':'·'};
 var pill=function(label,tone){return '<span class="v331-pill '+tone+'">'+esc(label)+'</span>'};
 var card=function(label,value,sub,color){return '<div class="v331-card" style="--accent:'+color+'"><span class="label">'+esc(label)+'</span><strong class="number">'+value+'</strong><span class="hint">'+esc(sub)+'</span></div>'};
 window.v331Refresh=function(){if(typeof window.renderOperativoView==='function')window.renderOperativoView('Tasa de recuperación · Revisión',true)};
 window.recoveryRateImprovedView=function(d){
   if(window.__v331Poll){clearTimeout(window.__v331Poll);window.__v331Poll=null}
   if(!d)d={status:'error',error:'No se recibió información de la consulta.'};
   var a=d.audit||{}, m=d.metrics||{}, rows=d.rows||[];
   var busy=d.status==='building'||a.stock_phase==='building';
   if(busy&&Number(d.retry_seconds||5)>0){
     window.__v331Poll=setTimeout(function(){
       var tab=document.querySelector('#operativoNav [data-tab-key="operations.recovery_audit"].active');
       if(tab)window.v331Refresh();
     },Math.max(4,Number(d.retry_seconds||5))*1000);
   }
   if(d.status!=='ready'){
     var waiting=d.status==='building',info=waiting?'Preparando el resumen diario en segundo plano…':(d.error||'No fue posible consultar el reporte.');
     return '<div class="v331-root"><div class="v331-toolbar"><div><b>'+esc(waiting?'Preparando información':'Consulta no disponible')+'</b><small style="display:block">'+esc(info)+'</small></div>'+pill(waiting?'Procesando':'Revisar','warn')+'</div><button type="button" class="v331-retry" onclick="window.v331Refresh()">Reintentar consulta</button></div>';
   }
   var noRate=m.sell_through_pct==null;
   var statusLabel=a.stock_phase==='building'?'Preparando existencias':a.period_partial?'Periodo parcial':noRate?'Pendiente de conciliación':'Estimación disponible';
   var statusTone=a.stock_phase==='building'?'warn':noRate?'fail':'warn';
   var head='<div class="v331-toolbar"><div><b>Auditoría paralela · '+esc(d.period_value||d.period_start||'')+'</b><small style="display:block">Stock y movimientos con trazabilidad por tienda · sin modificar la pestaña original</small></div><div class="v331-tags">'+pill(statusLabel,statusTone)+pill('Corte '+(d.stock_source_date||'no disponible'),'')+pill('Fuente '+(a.source_last_date||'sin ventas'),'')+'</div></div>';
   var kpis='<div class="v331-kpis">'+
     card('Stock inicial',m.stock_complete?n(m.inv_initial_pzs):'—','Referencia no conciliada','#196fce')+
     card('Devoluciones',n(m.dev_pzs),'Registradas · habilitado no verificado','#7754ce')+
     card('Piezas vendidas',n(m.sales_pzs),'Ventas registradas del periodo','#12a884')+
     card('Base estimada',m.stock_complete?n(m.inv_total_pzs):'—','Inicial + devoluciones','#2583d3')+
     card('Tasa de desplazamiento',pct(m.sell_through_pct),'No equivale a conversión FIFO','#8b65cf')+
     card('Tiendas con cálculo',n(m.valid_stores)+' / '+n(m.stores_in_scope),'Sujetas a conciliación','#de9a28')+
     '</div>';
   var good=rows.filter(function(r){return r.sell_through_pct!=null&&Number.isFinite(Number(r.sell_through_pct))})
      .sort(function(x,y){return Number(y.sell_through_pct)-Number(x.sell_through_pct)});
   var bars=good.length?good.slice(0,10).map(function(r){
     var v=Math.max(0,Math.min(100,Number(r.sell_through_pct)));
     return '<div class="v331-rankrow"><span class="name" title="'+esc(r.store)+'">'+esc(r.store)+'</span><span class="v331-track"><span class="v331-fill" style="display:block;width:'+v+'%"></span></span><strong>'+pct(r.sell_through_pct)+'</strong></div>';
   }).join(''):'<div class="v331-empty">Sin tasas validadas para mostrar un ranking. Revisa la fecha del corte y las alertas del periodo.</div>';
   var table=rows.map(function(r){
     var st=a.stock_phase==='building'?'Preparando stock':title(r.data_quality);
     var tone=r.audit_valid?'warn':'fail';
     return '<tr class="'+(r.is_project?'project-row':'')+'"><td><b>'+esc(r.store)+'</b></td><td>'+n(r.inv_initial_pzs)+'</td><td>'+n(r.dev_pzs)+'</td><td>'+n(r.sales_pzs)+'</td><td>'+n(r.inv_total_pzs)+'</td><td>'+n(r.inv_final_pzs)+'</td><td><b>'+pct(r.sell_through_pct)+'</b></td><td><span class="v331-quality '+tone+'">'+icon(tone)+' '+esc(st)+'</span></td></tr>';
   }).join('');
   var lower='<div class="v331-bottom"><div class="v331-panel"><div class="v331-panelhead"><b>Desplazamiento por tienda</b><small>Orden descendente · sólo cortes válidos</small></div><div class="v331-rank">'+bars+'</div></div>'+
    '<div class="v331-panel"><div class="v331-panelhead"><b>Matriz de revisión por tienda</b><small>'+n(rows.length)+' tiendas</small></div><div class="v331-tablewrap"><table class="v331-table"><thead><tr><th>Tienda</th><th>Stock inicial</th><th>Dev.</th><th>Vta. pzs</th><th>Base</th><th>Residual</th><th>Tasa</th><th>Estado</th></tr></thead><tbody>'+table+'</tbody></table></div></div></div>';
   var warnings=d.warnings||[];
   var acc='<details class="v331-disclosure"'+(noRate?' open':'')+'><summary>Calidad de la información y advertencias ('+warnings.length+')</summary><div class="details"><ul>'+warnings.map(function(w){return '<li>'+esc(w)+'</li>'}).join('')+'</ul></div></details>';
   var methodology='<details class="v331-disclosure"><summary>Cómo se calcula y qué falta conciliar</summary><div class="details"><b>Estimación:</b> venta total en piezas ÷ (existencia inicial del corte + devoluciones registradas) × 100. Para considerarla confiable falta conciliar transferencias, entradas, salidas, ajustes e inventario final. Las devoluciones no equivalen automáticamente a unidades habilitadas en piso. Los importes de ventas no son recuperación atribuible a devoluciones.</div></details>';
   var actions='<div class="v331-actions"><p>Periodo '+esc(d.period_start||'')+' al '+esc(d.period_end||'')+' · Venta registrada: '+mxn(m.sales_value)+' · Residual: '+(m.stock_complete?n(m.inv_final_pzs):'—')+' pzs</p><button class="v331-retry" type="button" onclick="window.v331Refresh()">Actualizar datos ↻</button></div>';
   return '<section class="v331-root">'+head+kpis+lower+acc+methodology+actions+'</section>';
 };
})();
</script>"""

    @m.app.middleware("http")
    async def recovery_audit_markup(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or not response.headers.get("content-type", "").startswith("text/html"):
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        page = body.decode("utf-8", errors="replace")
        # La nueva vista aún no tiene exportador auditado: no exponer descargas heredadas incorrectas.
        page = page.replace(
            "if(name!=='Recuperación por Tienda') out+=reportDownloadBar(name);",
            "if(name!=='Recuperación por Tienda' && name!=='Tasa de recuperación · Revisión') out+=reportDownloadBar(name);",
        )
        if 'id="v331-recovery-audit-css"' not in page:
            page = page.replace("</head>", css + "</head>", 1)
        if 'id="v331-recovery-audit-js"' not in page:
            page = insert_before_document_body_end(page, script)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers["X-Recovery-Audit"] = "V331"
        return HTMLResponse(page, status_code=response.status_code, headers=headers)

    m._V331_RECOVERY_AUDIT = True
    print("[V331] Tasa de recuperación · Revisión instalada sin modificar V243.", flush=True)
+(p/1000).toLocaleString('es-MX',{minimumFractionDigits:Math.abs(p)<1000?3:1,maximumFractionDigits:Math.abs(p)<1000?3:1})+' mil'};
 var titles={coincidente:'Corte coincidente',estimado:'Corte cercano',sin_corte:'Sin corte',corte_futuro:'Corte posterior',corte_antiguo:'Corte antiguo',sin_stock_tienda:'Falta stock',sin_base:'Sin base',ventas_superan_base:'Revisar ventas'};
 var title=function(s){return titles[s]||'Revisar dato'};
 var icon=function(k){return k==='ok'?'✓':k==='fail'?'!':'·'};
 var pill=function(label,tone){return '<span class="v331-pill '+tone+'">'+esc(label)+'</span>'};
 var card=function(label,value,sub,color){return '<div class="v331-card" style="--accent:'+color+'"><span class="label">'+esc(label)+'</span><strong class="number">'+value+'</strong><span class="hint">'+esc(sub)+'</span></div>'};
 window.v331Refresh=function(){if(typeof window.renderOperativoView==='function')window.renderOperativoView('Tasa de recuperación · Revisión',true)};
 window.recoveryRateImprovedView=function(d){
   if(window.__v331Poll){clearTimeout(window.__v331Poll);window.__v331Poll=null}
   if(!d)d={status:'error',error:'No se recibió información de la consulta.'};
   var a=d.audit||{}, m=d.metrics||{}, rows=d.rows||[];
   var busy=d.status==='building'||a.stock_phase==='building';
   if(busy&&Number(d.retry_seconds||5)>0){
     window.__v331Poll=setTimeout(function(){
       var tab=document.querySelector('#operativoNav [data-tab-key="operations.recovery_audit"].active');
       if(tab)window.v331Refresh();
     },Math.max(4,Number(d.retry_seconds||5))*1000);
   }
   if(d.status!=='ready'){
     var waiting=d.status==='building',info=waiting?'Preparando el resumen diario en segundo plano…':(d.error||'No fue posible consultar el reporte.');
     return '<div class="v331-root"><div class="v331-toolbar"><div><b>'+esc(waiting?'Preparando información':'Consulta no disponible')+'</b><small style="display:block">'+esc(info)+'</small></div>'+pill(waiting?'Procesando':'Revisar','warn')+'</div><button type="button" class="v331-retry" onclick="window.v331Refresh()">Reintentar consulta</button></div>';
   }
   var noRate=m.sell_through_pct==null;
   var statusLabel=a.stock_phase==='building'?'Preparando existencias':a.period_partial?'Periodo parcial':noRate?'Pendiente de conciliación':'Estimación disponible';
   var statusTone=a.stock_phase==='building'?'warn':noRate?'fail':'warn';
   var head='<div class="v331-toolbar"><div><b>Auditoría paralela · '+esc(d.period_value||d.period_start||'')+'</b><small style="display:block">Stock y movimientos con trazabilidad por tienda · sin modificar la pestaña original</small></div><div class="v331-tags">'+pill(statusLabel,statusTone)+pill('Corte '+(d.stock_source_date||'no disponible'),'')+pill('Fuente '+(a.source_last_date||'sin ventas'),'')+'</div></div>';
   var kpis='<div class="v331-kpis">'+
     card('Stock inicial',m.stock_complete?n(m.inv_initial_pzs):'—','Referencia no conciliada','#196fce')+
     card('Devoluciones',n(m.dev_pzs),'Registradas · habilitado no verificado','#7754ce')+
     card('Piezas vendidas',n(m.sales_pzs),'Ventas registradas del periodo','#12a884')+
     card('Base estimada',m.stock_complete?n(m.inv_total_pzs):'—','Inicial + devoluciones','#2583d3')+
     card('Tasa de desplazamiento',pct(m.sell_through_pct),'No equivale a conversión FIFO','#8b65cf')+
     card('Tiendas con cálculo',n(m.valid_stores)+' / '+n(m.stores_in_scope),'Sujetas a conciliación','#de9a28')+
     '</div>';
   var good=rows.filter(function(r){return r.sell_through_pct!=null&&Number.isFinite(Number(r.sell_through_pct))})
      .sort(function(x,y){return Number(y.sell_through_pct)-Number(x.sell_through_pct)});
   var bars=good.length?good.slice(0,10).map(function(r){
     var v=Math.max(0,Math.min(100,Number(r.sell_through_pct)));
     return '<div class="v331-rankrow"><span class="name" title="'+esc(r.store)+'">'+esc(r.store)+'</span><span class="v331-track"><span class="v331-fill" style="display:block;width:'+v+'%"></span></span><strong>'+pct(r.sell_through_pct)+'</strong></div>';
   }).join(''):'<div class="v331-empty">Sin tasas validadas para mostrar un ranking. Revisa la fecha del corte y las alertas del periodo.</div>';
   var table=rows.map(function(r){
     var st=a.stock_phase==='building'?'Preparando stock':title(r.data_quality);
     var tone=r.audit_valid?'warn':'fail';
     return '<tr class="'+(r.is_project?'project-row':'')+'"><td><b>'+esc(r.store)+'</b></td><td>'+n(r.inv_initial_pzs)+'</td><td>'+n(r.dev_pzs)+'</td><td>'+n(r.sales_pzs)+'</td><td>'+n(r.inv_total_pzs)+'</td><td>'+n(r.inv_final_pzs)+'</td><td><b>'+pct(r.sell_through_pct)+'</b></td><td><span class="v331-quality '+tone+'">'+icon(tone)+' '+esc(st)+'</span></td></tr>';
   }).join('');
   var lower='<div class="v331-bottom"><div class="v331-panel"><div class="v331-panelhead"><b>Desplazamiento por tienda</b><small>Orden descendente · sólo cortes válidos</small></div><div class="v331-rank">'+bars+'</div></div>'+
    '<div class="v331-panel"><div class="v331-panelhead"><b>Matriz de revisión por tienda</b><small>'+n(rows.length)+' tiendas</small></div><div class="v331-tablewrap"><table class="v331-table"><thead><tr><th>Tienda</th><th>Stock inicial</th><th>Dev.</th><th>Vta. pzs</th><th>Base</th><th>Residual</th><th>Tasa</th><th>Estado</th></tr></thead><tbody>'+table+'</tbody></table></div></div></div>';
   var warnings=d.warnings||[];
   var acc='<details class="v331-disclosure"'+(noRate?' open':'')+'><summary>Calidad de la información y advertencias ('+warnings.length+')</summary><div class="details"><ul>'+warnings.map(function(w){return '<li>'+esc(w)+'</li>'}).join('')+'</ul></div></details>';
   var methodology='<details class="v331-disclosure"><summary>Cómo se calcula y qué falta conciliar</summary><div class="details"><b>Estimación:</b> venta total en piezas ÷ (existencia inicial del corte + devoluciones registradas) × 100. Para considerarla confiable falta conciliar transferencias, entradas, salidas, ajustes e inventario final. Las devoluciones no equivalen automáticamente a unidades habilitadas en piso. Los importes de ventas no son recuperación atribuible a devoluciones.</div></details>';
   var actions='<div class="v331-actions"><p>Periodo '+esc(d.period_start||'')+' al '+esc(d.period_end||'')+' · Venta registrada: '+mxn(m.sales_value)+' · Residual: '+(m.stock_complete?n(m.inv_final_pzs):'—')+' pzs</p><button class="v331-retry" type="button" onclick="window.v331Refresh()">Actualizar datos ↻</button></div>';
   return '<section class="v331-root">'+head+kpis+lower+acc+methodology+actions+'</section>';
 };
})();
</script>"""

    @m.app.middleware("http")
    async def recovery_audit_markup(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or not response.headers.get("content-type", "").startswith("text/html"):
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        page = body.decode("utf-8", errors="replace")
        # La nueva vista aún no tiene exportador auditado: no exponer descargas heredadas incorrectas.
        page = page.replace(
            "if(name!=='Recuperación por Tienda') out+=reportDownloadBar(name);",
            "if(name!=='Recuperación por Tienda' && name!=='Tasa de recuperación · Revisión') out+=reportDownloadBar(name);",
        )
        if 'id="v331-recovery-audit-css"' not in page:
            page = page.replace("</head>", css + "</head>", 1)
        if 'id="v331-recovery-audit-js"' not in page:
            page = insert_before_document_body_end(page, script)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers["X-Recovery-Audit"] = "V331"
        return HTMLResponse(page, status_code=response.status_code, headers=headers)

    m._V331_RECOVERY_AUDIT = True
    print("[V331] Tasa de recuperación · Revisión instalada sin modificar V243.", flush=True)
