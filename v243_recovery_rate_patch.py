"""V243 · Tasa de recuperación / Sell-Through Neto.

Reemplaza visualmente la pestaña histórica "Recuperación por Tienda" sin romper
su clave interna ni las preferencias de visibilidad ya guardadas. El cálculo
usa ventas y devoluciones diarias de la Base de muertos y cambios y el corte de
existencias de capacidades más cercano al inicio del periodo.
"""
from __future__ import annotations

import math
import sqlite3
import threading
from datetime import date, datetime, timedelta

from fastapi import Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V243_RECOVERY_RATE", False):
        return

    try:
        m.REPORT_TABS["operations.recovery_store"] = "Tasa de recuperación"
    except Exception:
        pass

    cache_path = m.DATA_ROOT / "recovery_rate_daily_v243.sqlite3"
    cache_lock = threading.Lock()
    cache_state = {"building": False, "error": ""}
    cache_version = "243.1"

    def num(value):
        try:
            result = float(value or 0)
            return result if math.isfinite(result) else 0.0
        except Exception:
            return 0.0

    def source_path():
        return m.DATA_ROOT / "cambios_muertos_actual.xlsx"

    def source_stamp():
        path = source_path()
        try:
            stat = path.stat()
            return f"{stat.st_mtime_ns}:{stat.st_size}"
        except Exception:
            return ""

    def cache_meta():
        if not cache_path.exists():
            return {}
        try:
            con = sqlite3.connect(cache_path, timeout=15)
            try:
                return {str(k): str(v) for k, v in con.execute("SELECT k,v FROM meta")}
            finally:
                con.close()
        except Exception:
            return {}

    def cache_ready():
        stamp = source_stamp()
        if not stamp or not cache_path.exists():
            return False
        meta = cache_meta()
        return meta.get("version") == cache_version and meta.get("source_stamp") == stamp

    def build_daily_cache():
        src = source_path()
        if not src.exists():
            raise FileNotFoundError("No está disponible el Excel vigente de Cambios y Muertos")

        tmp = cache_path.with_suffix(".tmp.sqlite3")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

        target = sqlite3.connect(tmp, timeout=60)
        try:
            target.executescript(
                """
                PRAGMA journal_mode=OFF;
                PRAGMA synchronous=OFF;
                PRAGMA temp_store=FILE;
                CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
                CREATE TABLE daily(
                    store TEXT NOT NULL,
                    date TEXT NOT NULL,
                    year_iso INTEGER NOT NULL,
                    week_iso INTEGER NOT NULL,
                    sales REAL NOT NULL,
                    dev REAL NOT NULL,
                    sales_value REAL NOT NULL,
                    return_value REAL NOT NULL,
                    PRIMARY KEY(store,date)
                );
                CREATE INDEX idx_rr_daily_date ON daily(date);
                CREATE INDEX idx_rr_daily_week ON daily(year_iso,week_iso);
                CREATE INDEX idx_rr_daily_store ON daily(store);
                """
            )

            with m._xlsx_stream_book(src) as book:
                archive = book["archive"]
                shared_value = book["shared_value"]
                names = list(book["sheet_paths"])
                sheets = [name for name in names if m._monthly_sheet_name(name)]
                sheets_used = []

                for sheet in sheets:
                    member = book["sheet_paths"].get(sheet, "")
                    if not member or member not in archive.namelist():
                        continue
                    rows = m._xlsx_monthly_rows(archive, member, shared_value)
                    first = dict(next(rows, {}) or {})
                    next(rows, None)
                    date_columns = []
                    max_column = max(first.keys(), default=28)
                    for index in range(29, max_column + 1, 3):
                        date_iso, week_iso, year_iso, _month = m._safe_date_iso(first.get(index))
                        if date_iso and week_iso and year_iso:
                            date_columns.append((index, date_iso, int(week_iso), int(year_iso)))
                    if not date_columns:
                        continue

                    batch = []
                    for values in rows:
                        values = dict(values or {})
                        store = m._normalize_store_value(values.get(25, ""))
                        if not store:
                            continue
                        price = max(num(values.get(24, 0)), 0.0)
                        for index, date_iso, week_iso, year_iso in date_columns:
                            sales = max(num(values.get(index, 0)), 0.0)
                            dev = max(num(values.get(index + 1, 0)), 0.0)
                            sales_value = max(num(values.get(index + 2, 0)), 0.0)
                            if sales <= 0 and dev <= 0 and sales_value <= 0:
                                continue
                            return_value = max(price * dev, 0.0)
                            batch.append((store, date_iso, year_iso, week_iso, sales, dev, sales_value, return_value))
                            if len(batch) >= 5000:
                                target.executemany(
                                    """
                                    INSERT INTO daily(store,date,year_iso,week_iso,sales,dev,sales_value,return_value)
                                    VALUES(?,?,?,?,?,?,?,?)
                                    ON CONFLICT(store,date) DO UPDATE SET
                                      sales=daily.sales+excluded.sales,
                                      dev=daily.dev+excluded.dev,
                                      sales_value=daily.sales_value+excluded.sales_value,
                                      return_value=daily.return_value+excluded.return_value
                                    """,
                                    batch,
                                )
                                batch.clear()
                    if batch:
                        target.executemany(
                            """
                            INSERT INTO daily(store,date,year_iso,week_iso,sales,dev,sales_value,return_value)
                            VALUES(?,?,?,?,?,?,?,?)
                            ON CONFLICT(store,date) DO UPDATE SET
                              sales=daily.sales+excluded.sales,
                              dev=daily.dev+excluded.dev,
                              sales_value=daily.sales_value+excluded.sales_value,
                              return_value=daily.return_value+excluded.return_value
                            """,
                            batch,
                        )
                    target.commit()
                    sheets_used.append(sheet)

            target.executemany(
                "INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)",
                [
                    ("version", cache_version),
                    ("source_stamp", source_stamp()),
                    ("source_file", src.name),
                    ("built_at", datetime.now().isoformat(timespec="seconds")),
                    ("sheets", " | ".join(sheets_used)),
                ],
            )
            target.commit()
        finally:
            target.close()

        tmp.replace(cache_path)
        print("[V243] Cache diario de Tasa de recuperación construido.", flush=True)

    def start_cache_build():
        if cache_ready():
            return False
        with cache_lock:
            if cache_state["building"]:
                return True
            cache_state["building"] = True
            cache_state["error"] = ""

        def worker():
            try:
                build_daily_cache()
            except Exception as exc:
                cache_state["error"] = f"{type(exc).__name__}: {exc}"
                print(f"[V243] Error construyendo cache diario: {cache_state['error']}", flush=True)
            finally:
                cache_state["building"] = False
                try:
                    m._release_process_memory()
                except Exception:
                    pass

        threading.Thread(target=worker, name="recovery-rate-v243", daemon=True).start()
        return True

    def parse_period(period_type: str, period_value: str):
        period_type = str(period_type or "week").lower()
        period_value = str(period_value or "").strip()
        if period_type == "day":
            try:
                d = datetime.strptime(period_value, "%Y-%m-%d").date()
            except Exception:
                raise ValueError("Fecha inválida. Usa YYYY-MM-DD")
            iso = d.isocalendar()
            return d, d, f"{d.isoformat()} · {iso.year}-W{iso.week:02d}"
        if period_type == "week":
            try:
                year_txt, week_txt = period_value.split("-W", 1)
                start = date.fromisocalendar(int(year_txt), int(week_txt), 1)
            except Exception:
                raise ValueError("Semana ISO inválida. Usa YYYY-W##")
            end = start + timedelta(days=6)
            return start, end, period_value
        if period_type == "month":
            try:
                start = datetime.strptime(period_value, "%Y-%m").date().replace(day=1)
            except Exception:
                raise ValueError("Mes inválido. Usa YYYY-MM")
            if start.month == 12:
                next_month = date(start.year + 1, 1, 1)
            else:
                next_month = date(start.year, start.month + 1, 1)
            end = next_month - timedelta(days=1)
            return start, end, period_value
        if period_type == "year":
            try:
                year = int(period_value)
                start = date(year, 1, 1)
            except Exception:
                raise ValueError("Año inválido. Usa YYYY")
            return start, date(start.year, 12, 31), str(start.year)
        raise ValueError("El reporte Tasa de recuperación admite Diario, Semana ISO, Mensual o Anual")

    def capacity_entry_for_start(start: date):
        try:
            entries = list(m._capacity_processed_entries() or [])
        except Exception:
            entries = []
        dated = []
        for entry in entries:
            try:
                d = m._capacity_report_date(entry)
                dated.append((d, str(entry.get("uploaded_at") or ""), entry))
            except Exception:
                continue
        if not dated:
            return None, None, False
        prior = [item for item in dated if item[0] <= start]
        if prior:
            d, _uploaded, entry = max(prior, key=lambda x: (x[0], x[1]))
            return entry, d, False
        d, _uploaded, entry = min(dated, key=lambda x: (x[0], x[1]))
        return entry, d, True

    def stock_by_store(start: date):
        entry, source_date, future_cut = capacity_entry_for_start(start)
        if not entry:
            return {}, None, "", False, ["No existe un corte de capacidades/existencias procesado para obtener el Stock Inicial."]

        frame = m._load_capacity_compact_cache(entry)
        if frame is None or frame.empty or "Tienda" not in frame.columns or "ID_ART" not in frame.columns:
            return {}, source_date, str(entry.get("name") or ""), future_cut, ["El corte de capacidades no contiene Tienda + ID_ART utilizables."]

        import pandas as pd

        store_series = frame["Tienda"].fillna("").astype(str).map(m._normalize_store_value)
        id_series = frame["ID_ART"].fillna("").astype(str).str.strip()
        if "Existencia" in frame.columns:
            existence = pd.to_numeric(frame["Existencia"], errors="coerce").fillna(0.0)
        else:
            floor = pd.to_numeric(frame["Existencia piso"], errors="coerce").fillna(0.0) if "Existencia piso" in frame.columns else pd.Series(0.0, index=frame.index)
            warehouse = pd.to_numeric(frame["Existencia bodega"], errors="coerce").fillna(0.0) if "Existencia bodega" in frame.columns else pd.Series(0.0, index=frame.index)
            existence = floor + warehouse

        slim = pd.DataFrame({"store": store_series, "id": id_series, "existence": existence})
        slim = slim[(slim["store"] != "") & (~slim["id"].isin(["", "nan", "None"]))]
        if slim.empty:
            return {}, source_date, str(entry.get("name") or ""), future_cut, ["El corte seleccionado no contiene existencias por tienda/modelo."]

        by_model = slim.groupby(["store", "id"], sort=False, observed=True)["existence"].max()
        by_store = by_model.groupby(level=0, sort=False).sum()
        result = {str(k): max(num(v), 0.0) for k, v in by_store.items()}
        del slim, by_model, by_store
        try:
            m._release_process_memory()
        except Exception:
            pass
        return result, source_date, str(entry.get("name") or entry.get("id") or "Corte de capacidades"), future_cut, []

    def active_store_names():
        try:
            names = [m._normalize_store_value(x) for x in m.store_names(True)]
            return [x for x in names if x]
        except Exception:
            return []

    def available_periods(con):
        dates = [str(r[0]) for r in con.execute("SELECT DISTINCT date FROM daily ORDER BY date") if r[0]]
        weeks = [f"{int(y)}-W{int(w):02d}" for y, w in con.execute("SELECT DISTINCT year_iso,week_iso FROM daily ORDER BY year_iso,week_iso")]
        months = [str(r[0]) for r in con.execute("SELECT DISTINCT substr(date,1,7) FROM daily WHERE length(date)>=7 ORDER BY 1") if r[0]]
        years = [str(r[0]) for r in con.execute("SELECT DISTINCT substr(date,1,4) FROM daily WHERE length(date)>=4 ORDER BY 1") if r[0]]
        return dates, weeks, months, years

    def loading_payload(status="building"):
        try:
            meta = m.load_operations_meta()
        except Exception:
            meta = {}
        return {
            "available": True,
            "status": status,
            "error": cache_state.get("error") or "",
            "available_dates": meta.get("available_dates") or [],
            "available_weeks": meta.get("available_weeks") or [],
            "available_months": meta.get("available_months") or [],
            "available_years": sorted({str(x)[:4] for x in (meta.get("available_months") or []) if str(x)[:4].isdigit()}),
            "rows": [],
            "trend": [],
            "metrics": {},
        }

    @m.app.get("/api/operations/recovery-rate")
    def recovery_rate(
        request: Request,
        store: str = "Compañía",
        period_type: str = "week",
        period_value: str = "",
    ):
        user = m.require_user(request)
        store = m.effective_store(user, store)

        if not source_path().exists():
            payload = loading_payload("missing_source")
            payload["error"] = "No está disponible el Excel vigente de Cambios y Muertos. Vuelve a publicar la base para calcular ventas y devoluciones diarias."
            return payload

        if not cache_ready():
            start_cache_build()
            return loading_payload("building" if not cache_state.get("error") else "error")

        if not period_value:
            meta = m.load_operations_meta()
            if period_type == "day":
                values = meta.get("available_dates") or []
            elif period_type == "week":
                values = meta.get("available_weeks") or []
            elif period_type == "month":
                values = meta.get("available_months") or []
            elif period_type == "year":
                values = sorted({str(x)[:4] for x in (meta.get("available_months") or []) if str(x)[:4].isdigit()})
            else:
                values = []
            period_value = (values or [""])[-1]
        try:
            start, end, period_label = parse_period(period_type, period_value)
        except ValueError as exc:
            payload = loading_payload("error")
            payload["error"] = str(exc)
            return payload

        stocks, stock_date, stock_name, future_cut, warnings = stock_by_store(start)
        configured = set(active_store_names())
        project_set = set(m.project_store_names(True)) if hasattr(m, "project_store_names") else set()

        con = sqlite3.connect(cache_path, timeout=30)
        con.row_factory = sqlite3.Row
        try:
            daily_rows = [dict(r) for r in con.execute(
                """
                SELECT store,date,year_iso,week_iso,
                       SUM(sales) sales,SUM(dev) dev,SUM(sales_value) sales_value,SUM(return_value) return_value
                FROM daily
                WHERE date BETWEEN ? AND ?
                GROUP BY store,date,year_iso,week_iso
                ORDER BY date,store
                """,
                (start.isoformat(), end.isoformat()),
            )]
            available_dates, available_weeks, available_months, available_years = available_periods(con)
        finally:
            con.close()

        events = {}
        for row in daily_rows:
            s = m._normalize_store_value(row.get("store") or "")
            if not s:
                continue
            d = events.setdefault(s, {"sales": 0.0, "dev": 0.0, "sales_value": 0.0, "return_value": 0.0})
            for key in ("sales", "dev", "sales_value", "return_value"):
                d[key] += num(row.get(key))

        if store and store != "Compañía":
            requested = m._normalize_store_value(store)
            scope = [requested] if requested else []
        else:
            universe = set(stocks) | set(events)
            if configured:
                universe = {s for s in universe if s in configured}
            scope = sorted(universe)

        if not scope and store and store != "Compañía":
            scope = [m._normalize_store_value(store)]

        rows = []
        missing_stock = []
        for s in scope:
            event = events.get(s, {})
            stock_available = s in stocks
            initial = num(stocks.get(s)) if stock_available else 0.0
            dev = num(event.get("dev"))
            sales = num(event.get("sales"))
            sales_value = num(event.get("sales_value"))
            return_value = num(event.get("return_value"))
            avg_price = sales_value / sales if sales > 0 else (return_value / dev if dev > 0 else 0.0)
            enabled = initial + dev
            enabled_amount = enabled * avg_price
            residual = enabled - sales
            residual_amount = residual * avg_price
            sell_through = sales / enabled * 100 if enabled > 0 and stock_available else None
            impact_dev = dev / enabled * 100 if enabled > 0 and stock_available else None
            if not stock_available:
                missing_stock.append(s)
            rows.append({
                "store": s,
                "period": period_label,
                "is_project": s in project_set,
                "stock_available": stock_available,
                "inv_initial_pzs": initial if stock_available else None,
                "dev_pzs": dev,
                "inv_total_pzs": enabled if stock_available else None,
                "avg_price": avg_price,
                "inv_total_amount": enabled_amount if stock_available else None,
                "sales_pzs": sales,
                "sales_value": sales_value,
                "inv_final_pzs": residual if stock_available else None,
                "inv_final_amount": residual_amount if stock_available else None,
                "sell_through_pct": sell_through,
                "impact_dev_pct": impact_dev,
            })

        total_initial = sum(num(r.get("inv_initial_pzs")) for r in rows if r.get("stock_available"))
        total_dev = sum(num(r.get("dev_pzs")) for r in rows)
        total_sales = sum(num(r.get("sales_pzs")) for r in rows)
        total_sales_value = sum(num(r.get("sales_value")) for r in rows)
        total_return_value = sum(num(events.get(r.get("store"), {}).get("return_value")) for r in rows)
        total_enabled = total_initial + total_dev
        global_avg = total_sales_value / total_sales if total_sales > 0 else (total_return_value / total_dev if total_dev > 0 else 0.0)
        total_residual = total_enabled - total_sales
        stock_complete = bool(rows) and not missing_stock
        metrics = {
            "inv_initial_pzs": total_initial if rows else None,
            "dev_pzs": total_dev,
            "inv_total_pzs": total_enabled if rows else None,
            "avg_price": global_avg,
            "inv_total_amount": total_enabled * global_avg if rows else None,
            "sales_pzs": total_sales,
            "sales_value": total_sales_value,
            "inv_final_pzs": total_residual if rows else None,
            "inv_final_amount": total_residual * global_avg if rows else None,
            "sell_through_pct": (total_sales / total_enabled * 100) if total_enabled > 0 and stock_complete else None,
            "impact_dev_pct": (total_dev / total_enabled * 100) if total_enabled > 0 and stock_complete else None,
            "stock_complete": stock_complete,
        }

        if missing_stock:
            warnings.append("Sin Stock Inicial para: " + ", ".join(sorted(missing_stock)) + ". El KPI global se oculta hasta completar el corte.")
        if future_cut and stock_date:
            warnings.append(
                f"No había un corte de existencias anterior al inicio del periodo; se usó el corte disponible del {stock_date.isoformat()}."
            )
        if any(num(r.get("inv_final_pzs")) < 0 for r in rows if r.get("stock_available")):
            warnings.append("Hay tiendas donde las ventas superan Stock Inicial + Devoluciones. Se conserva el residual negativo para evidenciar entradas no contempladas por esta fórmula.")

        daily_scope = {}
        for row in daily_rows:
            s = m._normalize_store_value(row.get("store") or "")
            if s not in scope:
                continue
            d = daily_scope.setdefault(str(row.get("date") or ""), {"sales": 0.0, "dev": 0.0})
            d["sales"] += num(row.get("sales"))
            d["dev"] += num(row.get("dev"))

        trend = []
        cumulative_sales = 0.0
        cumulative_dev = 0.0
        cursor = start
        while cursor <= end:
            values = daily_scope.get(cursor.isoformat(), {})
            cumulative_sales += num(values.get("sales"))
            cumulative_dev += num(values.get("dev"))
            enabled_to_date = total_initial + cumulative_dev
            iso = cursor.isocalendar()
            include_point = (
                period_type != "year"
                or cursor == end
                or (cursor + timedelta(days=1)).month != cursor.month
            )
            if include_point:
                trend.append({
                    "date": cursor.isoformat(),
                    "label": cursor.strftime("%b").capitalize() if period_type == "year" else cursor.strftime("%d/%m"),
                    "week_iso": f"{iso.year}-W{iso.week:02d}",
                    "sales_pzs": cumulative_sales,
                    "dev_pzs": cumulative_dev,
                    "inv_total_pzs": enabled_to_date if rows else None,
                    "sell_through_pct": (cumulative_sales / enabled_to_date * 100) if enabled_to_date > 0 and stock_complete else None,
                    "impact_dev_pct": (cumulative_dev / enabled_to_date * 100) if enabled_to_date > 0 and stock_complete else None,
                })
            cursor += timedelta(days=1)

        rows.sort(key=lambda x: str(x.get("store") or ""))
        return {
            "available": True,
            "status": "ready",
            "period_type": period_type,
            "period_value": period_value,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "stock_source_date": stock_date.isoformat() if stock_date else None,
            "stock_source_name": stock_name,
            "metrics": metrics,
            "rows": rows,
            "trend": trend,
            "warnings": warnings,
            "available_dates": available_dates,
            "available_weeks": available_weeks,
            "available_months": available_months,
            "available_years": available_years,
            "definition": "Sell-Through Neto = Piezas Vendidas / (Stock Inicial + Piezas Devueltas) × 100",
        }

    css = r'''<style id="v243-recovery-rate-css">
.rr243-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:8px 0 14px}
.rr243-kpi{position:relative;min-width:0;background:#fff;border:1px solid #d8e0eb;border-radius:13px;padding:14px 15px;box-shadow:0 2px 8px rgba(23,59,115,.06);overflow:hidden}
.rr243-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--rr243,#1769e8)}
.rr243-kpi .lab{font-size:11px;line-height:1.1;font-weight:900;color:#667085;text-transform:uppercase;letter-spacing:.02em}
.rr243-kpi .val{margin-top:5px;font-size:25px;line-height:1;font-weight:950;color:#173B73;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rr243-kpi .sub{margin-top:5px;font-size:10px;line-height:1.15;font-weight:750;color:#667085}
.rr243-definition{margin:6px 0 12px;padding:10px 12px;border:1px solid #d8e0eb;border-radius:10px;background:#f7faff;color:#173B73;font-size:11px;line-height:1.35}
.rr243-source{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0 12px;font-size:10px;color:#667085}
.rr243-source b{color:#173B73}
.rr243-tablewrap{width:100%;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid #d8e0eb;border-radius:12px;background:#fff}
.rr243-table{min-width:1480px;margin:0!important}
.rr243-table th{position:sticky;top:0;z-index:2;white-space:nowrap}
.rr243-table td{white-space:nowrap}
.rr243-table tr.project-row td{background:#EAF3FF}
.rr243-negative{color:#C2410C!important;font-weight:900}
.rr243-chart-panel{margin-top:14px;background:#fff;border:1px solid #d8e0eb;border-radius:13px;padding:12px;overflow:hidden}
.rr243-chart-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px}
.rr243-chart-head b{font-size:14px;color:#173B73}
.rr243-expand{border:1px solid #cbdcf4;background:#fff;color:#173B73;border-radius:8px;padding:6px 10px;font-weight:850;cursor:pointer}
.rr243-chart-scroll{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
.rr243-chart-scroll svg{display:block;width:100%;min-width:720px;height:auto}
.rr243-chart-panel:fullscreen{background:#fff;padding:28px;overflow:auto}
.rr243-chart-panel:fullscreen .rr243-chart-scroll svg{min-width:1100px;max-height:82vh}
.rr243-warning{margin:8px 0;padding:9px 11px;border-left:4px solid #F59E0B;background:#FFF8E8;border-radius:8px;color:#7A5200;font-size:10px;line-height:1.3}
.rr243-loading{padding:22px;border:1px solid #d8e0eb;border-radius:12px;background:#fff;color:#173B73;font-weight:800;text-align:center}
@media(max-width:1100px){.rr243-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.rr243-kpi .val{font-size:22px}}
@media(max-width:700px){.rr243-kpis{grid-template-columns:1fr;gap:7px}.rr243-kpi{padding:11px 12px}.rr243-kpi .lab{font-size:9px}.rr243-kpi .val{font-size:19px}.rr243-kpi .sub{font-size:9px}.rr243-definition{font-size:9px}.rr243-chart-head b{font-size:12px}.rr243-expand{font-size:9px;padding:5px 8px}.rr243-table{font-size:10px}.rr243-table th,.rr243-table td{padding:7px 8px!important}}
</style>'''

    js = r'''<script id="v243-recovery-rate-js">
(function(){
  function esc(v){return String(v==null?'':v).replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]||c})}
  function n(v){if(v===null||v===undefined||!Number.isFinite(Number(v)))return '—';return Number(v).toLocaleString('es-MX',{maximumFractionDigits:0})}
  function money(v){if(v===null||v===undefined||!Number.isFinite(Number(v)))return '—';return Number(v).toLocaleString('es-MX',{style:'currency',currency:'MXN',minimumFractionDigits:2,maximumFractionDigits:2})}
  function pc(v){if(v===null||v===undefined||!Number.isFinite(Number(v)))return '—';return Number(v).toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1})+'%'}
  function kpi(label,value,sub,tone){return '<div class="rr243-kpi" style="--rr243:'+tone+'"><div class="lab">'+esc(label)+'</div><div class="val">'+value+'</div><div class="sub">'+esc(sub||'')+'</div></div>'}

  function chart(rows){
    rows=(rows||[]).filter(function(x){return x.sell_through_pct!==null&&x.sell_through_pct!==undefined&&Number.isFinite(Number(x.sell_through_pct))});
    if(!rows.length)return '<div class="infoempty">El gráfico estará disponible cuando exista un corte de Stock Inicial válido.</div>';
    var W=1200,H=320,L=70,R=35,T=50,B=55;
    var vals=rows.map(function(x){return Number(x.sell_through_pct||0)});
    var max=Math.max.apply(null,[100].concat(vals));max=Math.ceil(max/25)*25;
    var plotW=W-L-R,plotH=H-T-B;
    function X(i){return rows.length===1?L+plotW/2:L+plotW*i/(rows.length-1)}
    function Y(v){return T+plotH-(Number(v||0)/max)*plotH}
    var grid='';for(var q=0;q<=4;q++){var v=max*q/4,y=Y(v);grid+='<line x1="'+L+'" y1="'+y+'" x2="'+(W-R)+'" y2="'+y+'" stroke="#E4EAF2" stroke-width="1"/><text x="'+(L-10)+'" y="'+(y+4)+'" text-anchor="end" font-size="11" fill="#667085">'+v.toFixed(0)+'%</text>'}
    var pts=rows.map(function(x,i){return X(i)+','+Y(x.sell_through_pct)}).join(' ');
    var marks=rows.map(function(x,i){var xx=X(i),yy=Y(x.sell_through_pct);return '<circle cx="'+xx+'" cy="'+yy+'" r="5" fill="#1769E8" stroke="#fff" stroke-width="2"/><text x="'+xx+'" y="'+(yy-12)+'" text-anchor="middle" font-size="12" font-weight="900" fill="#173B73">'+pc(x.sell_through_pct)+'</text><text x="'+xx+'" y="'+(H-24)+'" text-anchor="middle" font-size="11" font-weight="800" fill="#667085">'+esc(x.label||x.date||'')+'</text>'}).join('');
    return '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Sell-Through Neto cronológico">'+grid+'<polyline points="'+pts+'" fill="none" stroke="#1769E8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'+marks+'</svg>';
  }

  window.recoveryRateView=function(d){
    if(!d||d.status==='building'){
      window.setTimeout(function(){var b=document.querySelector('#operativoNav [data-tab-key="operations.recovery_store"].active');if(b&&typeof renderOperativoView==='function')renderOperativoView('Recuperación por Tienda')},4000);
      return '<div class="rr243-loading">Preparando ventas y devoluciones diarias para calcular la Tasa de recuperación…<br><small>Este proceso se ejecuta una sola vez por cada archivo publicado.</small></div>';
    }
    if(d.status!=='ready')return '<div class="infoempty">'+esc(d.error||'No fue posible calcular la Tasa de recuperación.')+'</div>';
    var m=d.metrics||{},rows=d.rows||[];
    var out='<div class="rr243-definition"><b>% Sell-Through Neto:</b> Piezas Vendidas ÷ (Stock Inicial del periodo + Piezas Devueltas que regresan al piso) × 100.</div>';
    out+='<div class="rr243-kpis">'+
      kpi('Stock Total Habilitado (Pzs)',n(m.inv_total_pzs),'Stock Inicial + Devoluciones','#1769E8')+
      kpi('Venta Total ($)',money(m.sales_value),n(m.sales_pzs)+' piezas vendidas','#10B981')+
      kpi('Stock Final Residual (Pzs)',n(m.inv_final_pzs),'Stock habilitado - venta','#F59E0B')+
      kpi('% Sell-Through Neto Global',pc(m.sell_through_pct),'KPI principal del periodo','#7C3AED')+
      '</div>';
    out+='<div class="rr243-source"><span><b>Periodo:</b> '+esc(d.period_start||'')+(d.period_end&&d.period_end!==d.period_start?' al '+esc(d.period_end):'')+'</span><span>·</span><span><b>Stock inicial:</b> '+esc(d.stock_source_date||'Sin corte')+'</span><span>·</span><span>'+esc(d.stock_source_name||'')+'</span></div>';
    (d.warnings||[]).forEach(function(w){out+='<div class="rr243-warning">'+esc(w)+'</div>'});
    out+='<div class="title">Matriz operativa · Tasa de recuperación por tienda</div><div class="rr243-tablewrap"><table class="table rr243-table"><thead><tr><th>Tienda</th><th>Periodo</th><th>Stock Inicial Pzs</th><th>Devueltas Pzs</th><th>Stock Total Habilitado Pzs</th><th>Stock Total Habilitado $</th><th>Vendidas Pzs</th><th>Venta Total $</th><th>Precio Promedio</th><th>Stock Final Residual Pzs</th><th>Stock Final Residual $</th><th>% Sell-Through Neto</th><th>% Impacto Dev</th></tr></thead><tbody>';
    out+=rows.map(function(r){var neg=Number(r.inv_final_pzs)<0?' rr243-negative':'';return '<tr class="'+(r.is_project?'project-row':'')+'"><td><b>'+esc(r.store)+'</b></td><td>'+esc(r.period)+'</td><td>'+n(r.inv_initial_pzs)+'</td><td>'+n(r.dev_pzs)+'</td><td><b>'+n(r.inv_total_pzs)+'</b></td><td>'+money(r.inv_total_amount)+'</td><td><b>'+n(r.sales_pzs)+'</b></td><td>'+money(r.sales_value)+'</td><td>'+money(r.avg_price)+'</td><td class="'+neg+'">'+n(r.inv_final_pzs)+'</td><td class="'+neg+'">'+money(r.inv_final_amount)+'</td><td><b>'+pc(r.sell_through_pct)+'</b></td><td>'+pc(r.impact_dev_pct)+'</td></tr>'}).join('');
    out+='</tbody></table></div>';
    out+='<div class="rr243-chart-panel" id="rr243ChartPanel"><div class="rr243-chart-head"><b>Sell-Through Neto · evolución cronológica</b><button class="rr243-expand" type="button" onclick="document.getElementById(\'rr243ChartPanel\').requestFullscreen?.()">Pantalla completa</button></div><div class="rr243-chart-scroll">'+chart(d.trend||[])+'</div></div>';
    return out;
  };

  function renameTab(){var b=document.querySelector('#operativoNav [data-tab-key="operations.recovery_store"]');if(b)b.textContent='Tasa de recuperación'}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',renameTab,{once:true});else renameTab();
  setTimeout(renameTab,500);setTimeout(renameTab,1800);
})();
</script>'''

    def patch_html(html: str) -> str:
        html = html.replace(
            'data-opview="Recuperación por Tienda" data-tab-key="operations.recovery_store">Recuperación por Tienda</button>',
            'data-opview="Recuperación por Tienda" data-tab-key="operations.recovery_store">Tasa de recuperación</button>',
        )
        html = html.replace(
            "'Recuperación por Tienda':'Impacto económico por tienda con devoluciones, piezas recuperadas y venta recuperada estimada',",
            "'Recuperación por Tienda':'Sell-Through Neto · Stock Inicial + devoluciones habilitadas vs venta del mismo periodo',",
        )
        html = html.replace(
            "  if(name==='Productividad por Colaborador'||name==='Ranking de Colaboradores')return 'period';",
            "  if(name==='Recuperación por Tienda')return 'recovery';\n  if(name==='Productividad por Colaborador'||name==='Ranking de Colaboradores')return 'period';",
        )
        html = html.replace(
            "  if(fixed==='flex' || fixed==='period') return $('#operPeriodMode')?.value || 'month';",
            "  if(fixed==='flex' || fixed==='period' || fixed==='recovery') return $('#operPeriodMode')?.value || (fixed==='recovery'?'week':'month');",
        )
        html = html.replace(
            "    if(fixed==='flex') opts=[['week','Semanal'],['month','Mensual']];\n    else if(fixed==='period') opts=[['week','Semanal'],['month','Mensual'],['day','Diario']];",
            "    if(fixed==='flex') opts=[['week','Semanal'],['month','Mensual']];\n    else if(fixed==='recovery') opts=[['week','Semanal'],['day','Diario']];\n    else if(fixed==='period') opts=[['week','Semanal'],['month','Mensual'],['day','Diario']];",
        )

        fetch_marker = "async function fetchOpsForView(name){"
        if "V243_RECOVERY_RATE_FETCH" not in html and fetch_marker in html:
            injection = """async function fetchOpsForView(name){
  /* V243_RECOVERY_RATE_FETCH */
  if(name==='Recuperación por Tienda'){
    const type=currentPeriodTypeForView(name);
    const value=await resolveOpsPeriod(type);
    const store=$('#operStoreSelect')?.value||'Compañía';
    const url='/api/operations/recovery-rate?store='+encodeURIComponent(store)+'&period_type='+encodeURIComponent(type)+'&period_value='+encodeURIComponent(value);
    const d=await api(url,{timeoutMs:120000});
    if(d?.status==='ready')mergeOpsMetaFromResult(d);
    return d;
  }
"""
            html = html.replace(fetch_marker, injection, 1)

        start_marker = "}else if(name==='Recuperación por Tienda'){"
        end_marker = "}else if(name==='Productividad por Colaborador'||name==='Ranking de Colaboradores'){"
        start = html.find(start_marker)
        end = html.find(end_marker, start + 1) if start >= 0 else -1
        if start >= 0 and end > start and "V243_RECOVERY_RATE_BRANCH" not in html[start:end]:
            branch = """}else if(name==='Recuperación por Tienda'){
    /* V243_RECOVERY_RATE_BRANCH */
    $('#operativoDynamicTitle').textContent='Tasa de recuperación';
    $('#operativoDynamicSub').textContent='Sell-Through Neto · Stock Inicial + devoluciones habilitadas vs venta del mismo periodo';
    out=recoveryRateView(d);
  """
            html = html[:start] + branch + html[end:]

        final_download = "  out+=reportDownloadBar(name);"
        pos = html.rfind(final_download)
        if pos >= 0:
            html = html[:pos] + "  if(name!=='Recuperación por Tienda') out+=reportDownloadBar(name);" + html[pos + len(final_download):]

        if 'id="v243-recovery-rate-css"' not in html:
            html = html.replace("</head>", css + "</head>", 1)
        if 'id="v243-recovery-rate-js"' not in html:
            html = html.replace("</body>", js + "</body>", 1)
        return html

    @m.app.middleware("http")
    async def v243_recovery_rate_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = patch_html(body.decode("utf-8", errors="replace"))
            headers = dict(response.headers)
            headers.pop("content-length", None)
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-Recovery-Rate"] = "V243"
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V243_RECOVERY_RATE = True
    print("[V243] Tasa de recuperación instalada: Sell-Through Neto por día/semana ISO.", flush=True)
