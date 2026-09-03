"""Parche de memoria para la carga de Cambios y Muertos en Render.

Se instala desde ``server_entry.py`` antes de que FastAPI ejecute sus eventos de
startup. Conserva el cálculo FIFO por tienda/SKU/color/semana, pero no retiene
cada lote en RAM: una vez calculado, lo consolida a tienda-día en SQLite. Los
reportes de la aplicación consumen esos campos de forma aditiva, por lo que las
métricas de conversión y recuperación se mantienen y la carga deja de acercarse
al límite de 512 MB del servicio.
"""
from __future__ import annotations

import math


def install(module) -> None:
    """Instala el lector FIFO compacto sobre el módulo ``web_app``."""
    if getattr(module, "_RENDER_FIFO_MEMORY_PATCH", False):
        return

    def _stream_monthly_recovery_fifo_compact(path, sheets: list[str], stream_book=None):
        if not sheets:
            return [], [], [], []
        if stream_book is None:
            with module._xlsx_stream_book(path) as owned_book:
                return _stream_monthly_recovery_fifo_compact(path, sheets, owned_book)

        con = stream_book["con"]
        weeks = set()
        months = set()
        errors = []
        fifo = []
        try:
            con.executescript(
                """
                DROP TABLE IF EXISTS daily;
                DROP TABLE IF EXISTS fifo_daily;
                CREATE TABLE daily(
                    store TEXT NOT NULL,
                    year_iso INTEGER NOT NULL,
                    week_iso INTEGER NOT NULL,
                    id_art TEXT NOT NULL,
                    color TEXT NOT NULL,
                    date TEXT NOT NULL,
                    dev REAL NOT NULL,
                    sales REAL NOT NULL,
                    sales_value REAL NOT NULL,
                    return_cost REAL NOT NULL
                );
                CREATE TABLE fifo_daily(
                    store TEXT NOT NULL,
                    year_iso INTEGER NOT NULL,
                    week_iso INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    dev_pzs REAL NOT NULL DEFAULT 0,
                    vta_pzs REAL NOT NULL DEFAULT 0,
                    converted_pieces REAL NOT NULL DEFAULT 0,
                    return_value REAL NOT NULL DEFAULT 0,
                    recovered_value REAL NOT NULL DEFAULT 0,
                    pending_pieces REAL NOT NULL DEFAULT 0,
                    pending_value REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY(store, year_iso, week_iso, date)
                );
                """
            )

            archive = stream_book["archive"]
            sheet_paths = stream_book["sheet_paths"]
            shared_value = stream_book["shared_value"]

            for sheet in sheets:
                member = sheet_paths.get(sheet, "")
                if not member or member not in archive.namelist():
                    errors.append(f"{sheet}: hoja no encontrada durante lectura optimizada")
                    continue
                try:
                    row_iter = module._xlsx_monthly_rows(archive, member, shared_value)
                    first = dict(next(row_iter, {}) or {})
                    next(row_iter, None)
                    date_columns = []
                    max_column = max(first.keys(), default=28)
                    for index in range(29, max_column + 1, 3):
                        date_iso, week_iso, year_iso, month_key = module._safe_date_iso(first.get(index))
                        if date_iso and week_iso and year_iso:
                            date_columns.append((index, date_iso, int(week_iso), int(year_iso), month_key))
                            weeks.add(f"{int(year_iso)}-W{int(week_iso):02d}")
                            if month_key:
                                months.add(month_key)
                    if not date_columns:
                        errors.append(f"{sheet}: no se detectaron fechas diarias desde la columna 30")
                        continue

                    batch = []

                    def cell(values, index, default=None):
                        return values.get(index, default)

                    def number(value):
                        try:
                            result = float(value or 0)
                            return result if math.isfinite(result) else 0.0
                        except Exception:
                            return 0.0

                    for values in row_iter:
                        values = dict(values or {})
                        store = module._normalize_store_value(cell(values, 25, ""))
                        art = module._clean_occurrence(cell(values, 1, ""))
                        if not store or not art:
                            continue
                        color = module._clean_text(cell(values, 7, ""))
                        price = max(number(cell(values, 24, 0)), 0.0)
                        for index, date_iso, week_iso, year_iso, _month in date_columns:
                            sales = max(number(cell(values, index, 0)), 0.0)
                            dev = max(number(cell(values, index + 1, 0)), 0.0)
                            sales_value = max(number(cell(values, index + 2, 0)), 0.0)
                            if sales <= 0 and dev <= 0 and sales_value <= 0:
                                continue
                            return_cost = price * dev if price > 0 and dev > 0 else sales_value
                            batch.append((store, year_iso, week_iso, art, color, date_iso, dev, sales, sales_value, max(return_cost, 0.0)))
                            if len(batch) >= 5000:
                                con.executemany("INSERT INTO daily VALUES(?,?,?,?,?,?,?,?,?,?)", batch)
                                batch.clear()
                    if batch:
                        con.executemany("INSERT INTO daily VALUES(?,?,?,?,?,?,?,?,?,?)", batch)
                    con.commit()
                except Exception as exc:
                    errors.append(f"{sheet}: {type(exc).__name__}: {exc}")

            con.execute("CREATE INDEX IF NOT EXISTS idx_daily_fifo ON daily(store,year_iso,week_iso,id_art,color,date)")
            con.commit()

            query = """
                SELECT store,year_iso,week_iso,id_art,color,date,
                       SUM(dev),SUM(sales),SUM(sales_value),SUM(return_cost)
                FROM daily
                GROUP BY store,year_iso,week_iso,id_art,color,date
                ORDER BY store,year_iso,week_iso,id_art,color,date
            """
            upsert_sql = """
                INSERT INTO fifo_daily(
                    store,year_iso,week_iso,date,dev_pzs,vta_pzs,
                    converted_pieces,return_value,recovered_value,
                    pending_pieces,pending_value
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(store,year_iso,week_iso,date) DO UPDATE SET
                    dev_pzs=dev_pzs+excluded.dev_pzs,
                    vta_pzs=vta_pzs+excluded.vta_pzs,
                    converted_pieces=converted_pieces+excluded.converted_pieces,
                    return_value=return_value+excluded.return_value,
                    recovered_value=recovered_value+excluded.recovered_value,
                    pending_pieces=pending_pieces+excluded.pending_pieces,
                    pending_value=pending_value+excluded.pending_value
            """

            current_key = None
            group = []
            fifo_batch = []

            def flush_fifo_batch():
                if fifo_batch:
                    con.executemany(upsert_sql, fifo_batch)
                    fifo_batch.clear()

            def flush_group():
                if not group:
                    return
                for lot in module._build_recovery_fifo_rows(group):
                    fifo_batch.append((
                        str(lot.get("store") or ""), int(lot.get("year_iso") or 0), int(lot.get("week_iso") or 0),
                        str(lot.get("date") or ""), float(lot.get("dev_pzs") or 0), float(lot.get("vta_pzs") or 0),
                        float(lot.get("converted_pieces") or 0), float(lot.get("return_value") or 0),
                        float(lot.get("recovered_value") or 0), float(lot.get("pending_pieces") or 0),
                        float(lot.get("pending_value") or 0),
                    ))
                    if len(fifo_batch) >= 2000:
                        flush_fifo_batch()

            for store, year_iso, week_iso, art, color, date, dev, sales, sales_value, return_cost in con.execute(query):
                key = (store, int(year_iso), int(week_iso), art, color)
                if current_key is not None and key != current_key:
                    flush_group()
                    group.clear()
                current_key = key
                group.append({
                    "store": store, "year_iso": int(year_iso), "week_iso": int(week_iso),
                    "id_art": art, "color": color, "date": date,
                    "dev_pzs": float(dev or 0), "vta_pzs": float(sales or 0),
                    "vta_imp": float(sales_value or 0), "costo_dev": float(return_cost or 0),
                })
            flush_group()
            flush_fifo_batch()
            con.commit()

            result_query = """
                SELECT store,year_iso,week_iso,date,dev_pzs,vta_pzs,
                       converted_pieces,return_value,recovered_value,
                       pending_pieces,pending_value
                FROM fifo_daily
                ORDER BY date,store
            """
            for store, year_iso, week_iso, date, dev, sales, converted, return_value, recovered_value, pending_pieces, pending_value in con.execute(result_query):
                dev = max(float(dev or 0), 0.0)
                converted = min(max(float(converted or 0), 0.0), dev)
                return_value = max(float(return_value or 0), 0.0)
                recovered_value = min(max(float(recovered_value or 0), 0.0), return_value)
                fifo.append({
                    "date": str(date or ""), "store": str(store or ""),
                    "year_iso": int(year_iso or 0), "week_iso": int(week_iso or 0),
                    "id_art": "", "color": "", "dev_pzs": dev,
                    "vta_pzs": float(sales or 0), "converted_pieces": converted,
                    "conversion_pct": converted / dev * 100 if dev else 0.0,
                    "return_value": return_value, "recovered_value": recovered_value,
                    "recovery_pct": recovered_value / return_value * 100 if return_value else 0.0,
                    "pending_pieces": max(float(pending_pieces or 0), 0.0),
                    "pending_value": max(float(pending_value or 0), 0.0),
                })

            print(f"[UPLOAD] FIFO consolidado en {len(fifo)} filas tienda-día sin retener lotes SKU/color en RAM", flush=True)
            return fifo, sorted(weeks), sorted(months), errors
        finally:
            try:
                con.execute("DROP TABLE IF EXISTS daily")
                con.execute("DROP TABLE IF EXISTS fifo_daily")
                con.commit()
            except Exception:
                pass
            try:
                module._release_process_memory()
            except Exception:
                pass

    module._stream_monthly_recovery_fifo = _stream_monthly_recovery_fifo_compact
    module._RENDER_FIFO_MEMORY_PATCH = True
