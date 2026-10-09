"""V293 · Bonos por tienda: Venta vs Meta + DDI/Inversión + Asistencia.

Boceto 5 aplicado al indicador Bonos.
- 50% Venta vs Meta (metas 2026, hoja ROPA).
- 30% reducción de modelos críticos por catálogo: Abrigador, Licencias y Básicos.
- 20% Asistencia.

El listado objetivo se fija por tienda/mes usando la primera capacidad disponible
del mes. Un modelo entra si DDI > 90 y su inversión es mayor al promedio de
inversión de su catálogo en esa tienda. Al cierre se compara el mismo ID contra
la última capacidad disponible del mes.
"""
from __future__ import annotations

import json
import math
import re
import threading
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")
CATALOGS = ("Abrigador", "Licencias", "Básicos")
ADMIN = ("superadmin", "admin")
RESTRICTED = ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria")
MONTH_LABELS = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

_META_CACHE = None


def install(m):
    if getattr(m, "_V293_SALES_BONUS", False):
        return

    try:
        m.REPORT_TABS["operation.bonuses"] = "Bonos"
    except Exception:
        pass

    with m.db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sales_bonus_snapshot_v293(
                month TEXT NOT NULL,
                store TEXT NOT NULL,
                source_period TEXT NOT NULL DEFAULT '',
                source_date TEXT NOT NULL DEFAULT '',
                fixed_at TEXT NOT NULL,
                model_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(month,store)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS sales_bonus_targets_v293(
                month TEXT NOT NULL,
                store TEXT NOT NULL,
                id_art TEXT NOT NULL,
                catalog TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                initial_ddi REAL NOT NULL DEFAULT 0,
                initial_investment REAL NOT NULL DEFAULT 0,
                avg_investment REAL NOT NULL DEFAULT 0,
                source_period TEXT NOT NULL DEFAULT '',
                source_date TEXT NOT NULL DEFAULT '',
                fixed_at TEXT NOT NULL,
                PRIMARY KEY(month,store,id_art)
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS ix_sales_bonus_targets_v293_month_store ON sales_bonus_targets_v293(month,store,catalog)")
        target_cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(sales_bonus_targets_v293)").fetchall()}
        if "initial_existence" not in target_cols:
            con.execute("ALTER TABLE sales_bonus_targets_v293 ADD COLUMN initial_existence REAL NOT NULL DEFAULT 0")
        con.execute("""
            CREATE TABLE IF NOT EXISTS sales_bonus_attendance_v293(
                month TEXT NOT NULL,
                store TEXT NOT NULL,
                attendance_pct REAL NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                PRIMARY KEY(month,store)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS sales_bonus_store_sales_v295(
                source_stamp INTEGER NOT NULL,
                month TEXT NOT NULL,
                store TEXT NOT NULL,
                sales_value REAL NOT NULL DEFAULT 0,
                sales_pieces REAL NOT NULL DEFAULT 0,
                source_available INTEGER NOT NULL DEFAULT 0,
                built_at TEXT NOT NULL,
                PRIMARY KEY(source_stamp,month,store)
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS ix_sales_bonus_store_sales_v295_month ON sales_bonus_store_sales_v295(month,source_stamp)")

    def norm(value):
        try:
            return m.login_key(value)
        except Exception:
            return str(value or "").strip().casefold()

    def fold(value):
        raw = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(ch for ch in raw if not unicodedata.combining(ch)).upper()

    def num(value):
        try:
            out = float(value or 0)
            return out if math.isfinite(out) else 0.0
        except Exception:
            return 0.0

    def all_stores():
        return list(m.store_names(True) or [])

    def canon_store(value, stores):
        key = norm(value)
        for store in stores:
            if norm(store) == key:
                return store
        aliases = {
            "centro historico": "Centro",
            "guadalajara": "Atemajac",
            "guadalajara miravalle": "Miravalle",
            "olivar del conde": "Olivar",
            "queretaro": "Querétaro",
            "leon": "León",
        }
        target = aliases.get(fold(value).lower())
        if target:
            for store in stores:
                if norm(store) == norm(target):
                    return store
        return str(value or "").strip()

    def month_key(raw):
        text = str(raw or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}", text):
            now = datetime.now(MX)
            text = f"{now.year:04d}-{now.month:02d}"
        yy, mm = (int(x) for x in text.split("-"))
        if mm < 1 or mm > 12:
            raise HTTPException(400, "Mes inválido")
        return f"{yy:04d}-{mm:02d}"

    def period_label(month):
        yy, mm = (int(x) for x in month.split("-"))
        return f"{MONTH_LABELS.get(mm, str(mm))} {yy}"

    def meta_payload():
        global _META_CACHE
        if _META_CACHE is not None:
            return _META_CACHE
        path = Path(__file__).resolve().parent / "data" / "metas_ropa_2026.json"
        try:
            _META_CACHE = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[V293] No se pudo leer metas 2026: {type(exc).__name__}: {exc}", flush=True)
            _META_CACHE = {"year": 2026, "unit": "MXN", "stores": {}}
        return _META_CACHE

    def store_goal(store, month):
        payload = meta_payload()
        yy, mm = (int(x) for x in month.split("-"))
        if int(payload.get("year") or 0) != yy:
            return 0.0
        goals = payload.get("stores") or {}
        direct = goals.get(store)
        if direct is None:
            for key, value in goals.items():
                if norm(key) == norm(store):
                    direct = value
                    break
        if not isinstance(direct, dict):
            return 0.0
        return num(direct.get(f"{mm:02d}"))

    def available_goal_months():
        payload = meta_payload()
        yy = int(payload.get("year") or 2026)
        return [f"{yy:04d}-{mm:02d}" for mm in range(1, 13)]

    manifest_cache = {"mtime": None, "entries": []}
    manifest_cache_lock = threading.Lock()

    def _fast_processed_capacity_entries():
        """Lee manifest.json directamente; evita descubrir/hash de archivos en cada consulta."""
        manifest_path = Path(m.COMMERCIAL_DATA_ROOT) / "manifest.json"
        try:
            stamp = manifest_path.stat().st_mtime_ns if manifest_path.exists() else 0
        except Exception:
            stamp = 0
        with manifest_cache_lock:
            if manifest_cache.get("mtime") == stamp:
                return list(manifest_cache.get("entries") or [])
        entries = []
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            entries = [
                dict(x) for x in (payload.get("capacities") or [])
                if str(x.get("status") or "").strip().lower() == "procesado"
            ]
        except Exception as exc:
            print(f"[V299] Manifest capacidades no disponible: {type(exc).__name__}: {exc}", flush=True)
        with manifest_cache_lock:
            manifest_cache["mtime"] = stamp
            manifest_cache["entries"] = list(entries)
        return entries

    def capacity_entries(month):
        """Cortes procesados que pertenecen exactamente al mes."""
        out = []
        for entry in _fast_processed_capacity_entries():
            try:
                d = m._capacity_report_date(entry)
            except Exception:
                continue
            if f"{d.year:04d}-{d.month:02d}" == month:
                out.append((d, str(entry.get("uploaded_at") or entry.get("created_at") or ""), entry))
        out.sort(key=lambda x: (x[0], x[1]))
        return out

    def _capacity_all_entries():
        out = []
        for entry in _fast_processed_capacity_entries():
            try:
                d = m._capacity_report_date(entry)
            except Exception:
                continue
            out.append((d, str(entry.get("uploaded_at") or entry.get("created_at") or ""), entry))
        out.sort(key=lambda x: (x[0], x[1]))
        return out

    def opening_capacity_entry(month):
        """Corte que fija la cartera del mes: último disponible al iniciar el mes.

        Ejemplo: para octubre, un corte 29/09 es la apertura correcta. Si no
        existe ningún corte previo, usa el primero disponible dentro del mes.
        """
        yy, mm = (int(x) for x in month.split("-"))
        month_start = date(yy, mm, 1)
        all_entries = _capacity_all_entries()
        prior = [x for x in all_entries if x[0] <= month_start]
        if prior:
            return prior[-1]
        exact = [x for x in all_entries if x[0].year == yy and x[0].month == mm]
        return exact[0] if exact else None

    def current_capacity_entry(month):
        """Último corte conocido hasta el mes consultado, sin usar datos futuros."""
        yy, mm = (int(x) for x in month.split("-"))
        candidates = [
            x for x in _capacity_all_entries()
            if (x[0].year, x[0].month) <= (yy, mm)
        ]
        return candidates[-1] if candidates else None

    def period_for_entry(entry):
        if not entry:
            return ""
        d = m._capacity_report_date(entry)
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    BONUS_CAPACITY_CACHE_VERSION = 1
    capacity_jobs = set()
    capacity_jobs_lock = threading.Lock()

    def _bonus_capacity_cache_path(entry):
        base = m._capacity_cache_path(str(entry.get("id") or "capacity"))
        return base.with_name(base.stem + f".bonus-v{BONUS_CAPACITY_CACHE_VERSION}.pkl")

    def _load_or_build_bonus_capacity(entry):
        target = _bonus_capacity_cache_path(entry)
        try:
            if target.exists() and target.is_file():
                frame = pd.read_pickle(target)
                if isinstance(frame, pd.DataFrame) and not frame.empty:
                    return frame
        except Exception:
            pass
        frame = pd.DataFrame()
        try:
            frame = m._load_capacity_cache(entry)
        except Exception:
            frame = pd.DataFrame()
        if frame is None or frame.empty:
            try:
                source_path = m.resolve_entry_path(entry)
                frame = m.read_capacity_file(source_path)
                if isinstance(frame, pd.DataFrame) and not frame.empty:
                    frame = m._prepare_capacity_frame(frame)
                    normalized = m._capacity_cache_path(str(entry.get("id") or ""))
                    frame.to_pickle(normalized)
                    m.update_entry(
                        "capacities", str(entry.get("id") or ""),
                        cache_file=str(normalized.relative_to(m.DATA_ROOT))
                    )
            except Exception as exc:
                print(f"[V299] No se pudo reconstruir capacidad de Bonos: {type(exc).__name__}: {exc}", flush=True)
                frame = pd.DataFrame()
        if frame is None or frame.empty:
            return pd.DataFrame()
        keep = [x for x in [
            "Tienda", "ID_ART", "Modelo", "Marca", "Categoría", "Subcategoría", "Tipo catálogo",
            "DDI", "Existencia", "Inversión", "_TiendaKey"
        ] if x in frame.columns]
        light = frame.loc[:, keep].copy()
        try:
            light.to_pickle(target)
        except Exception as exc:
            print(f"[V299] No se pudo persistir cache ligero de Bonos: {type(exc).__name__}: {exc}", flush=True)
        try:
            del frame
            m._release_process_memory()
        except Exception:
            pass
        return light

    def _build_capacity_cache(entry):
        key = str(entry.get("id") or "")
        try:
            frame = _load_or_build_bonus_capacity(entry)
            print(f"[V299] Cache ligero capacidad listo: {key} filas={len(frame)}", flush=True)
        except Exception as exc:
            print(f"[V299] Error preparando cache capacidad {key}: {type(exc).__name__}: {exc}", flush=True)
        finally:
            with capacity_jobs_lock:
                capacity_jobs.discard(key)

    def load_frame(entry):
        """La petición sólo lee el cache ligero. Si falta, se prepara fuera de la petición."""
        if not entry:
            return pd.DataFrame(), False
        key = str(entry.get("id") or "")
        target = _bonus_capacity_cache_path(entry)
        try:
            if target.exists() and target.is_file():
                frame = pd.read_pickle(target)
                if isinstance(frame, pd.DataFrame) and not frame.empty:
                    return frame, False
        except Exception as exc:
            print(f"[V299] Cache ligero ilegible {key}: {type(exc).__name__}: {exc}", flush=True)
        with capacity_jobs_lock:
            pending = key in capacity_jobs
            if not pending:
                capacity_jobs.add(key)
                pending = True
                threading.Thread(
                    target=_build_capacity_cache,
                    args=(dict(entry),),
                    daemon=True,
                    name=f"bonus-cap-{key[:10]}",
                ).start()
        return pd.DataFrame(), pending

    def scope_frame(frame, stores):
        if frame is None or frame.empty or not stores:
            return pd.DataFrame()
        if "Tienda" not in frame.columns:
            return pd.DataFrame()
        keys = {norm(x) for x in stores}
        if "_TiendaKey" in frame.columns:
            mask = frame["_TiendaKey"].astype(str).isin(keys)
        else:
            mask = frame["Tienda"].astype(str).map(norm).isin(keys)
        cols = [c for c in [
            "Tienda", "ID_ART", "Modelo", "Marca", "Categoría", "Subcategoría", "Tipo catálogo",
            "DDI", "Existencia", "Inversión"
        ] if c in frame.columns]
        return frame.loc[mask, cols].copy()

    def classify_catalog(work):
        if work.empty:
            return pd.Series(dtype="object")
        parts = []
        for col in ("Tipo catálogo", "Categoría", "Subcategoría", "Marca", "Modelo"):
            if col in work.columns:
                parts.append(work[col].fillna("").astype(str))
        if not parts:
            return pd.Series("", index=work.index, dtype="object")
        text = parts[0]
        for part in parts[1:]:
            text = text.str.cat(part, sep=" | ")
        text = text.map(fold)
        out = pd.Series("", index=work.index, dtype="object")
        license_mask = text.str.contains(r"\bLICEN(?:CIA|CIAS|CIADO|CIADOS)?\b|DISNEY|MARVEL|MICKEY|MINNIE|PIXAR|STAR WARS|PRINCES", regex=True, na=False)
        coat_mask = text.str.contains(r"ABRIGADOR|ABRIGO|CHAMARRA|CHAQUETA|PARKA", regex=True, na=False)
        basic_mask = text.str.contains(r"\bBASIC(?:O|OS|A|AS)?\b", regex=True, na=False)
        out.loc[basic_mask] = "Básicos"
        out.loc[coat_mask] = "Abrigador"
        out.loc[license_mask] = "Licencias"
        return out

    def aggregate_models(work):
        if work.empty or "ID_ART" not in work.columns:
            return pd.DataFrame(columns=["store", "id_art", "model", "catalog", "ddi", "existence", "investment"])
        w = work.copy()
        w["store"] = w.get("Tienda", "").astype(str).map(lambda x: canon_store(x, all_stores()))
        w["id_art"] = w["ID_ART"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        w = w[~w["id_art"].isin(["", "nan", "None"])]
        if w.empty:
            return pd.DataFrame(columns=["store", "id_art", "model", "catalog", "ddi", "existence", "investment"])
        w["catalog"] = classify_catalog(w)
        w = w[w["catalog"].isin(CATALOGS)]
        if w.empty:
            return pd.DataFrame(columns=["store", "id_art", "model", "catalog", "ddi", "investment"])
        w["ddi"] = pd.to_numeric(w.get("DDI", 0), errors="coerce").replace([math.inf, -math.inf], pd.NA).fillna(0.0)
        w["existence"] = pd.to_numeric(w.get("Existencia", 0), errors="coerce").fillna(0.0)
        w["investment"] = pd.to_numeric(w.get("Inversión", 0), errors="coerce").fillna(0.0)
        w["model"] = w.get("Modelo", w["id_art"]).fillna("").astype(str).str.strip()
        grouped = w.groupby(["store", "id_art", "catalog"], sort=False, observed=True).agg(
            model=("model", "first"),
            ddi=("ddi", "max"),
            existence=("existence", "max"),
            investment=("investment", "max"),
        ).reset_index()
        return grouped

    sales_jobs = set()
    sales_jobs_lock = threading.Lock()

    def _persist_operations_sales(stamp, month, stores, totals, pieces, source_available):
        now = datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            for store in stores:
                con.execute("""
                    INSERT INTO sales_bonus_store_sales_v295(
                        source_stamp,month,store,sales_value,sales_pieces,source_available,built_at
                    ) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(source_stamp,month,store) DO UPDATE SET
                        sales_value=excluded.sales_value,
                        sales_pieces=excluded.sales_pieces,
                        source_available=excluded.source_available,
                        built_at=excluded.built_at
                """, (
                    stamp, month, store, totals.get(store, 0.0), pieces.get(store, 0.0),
                    1 if source_available else 0, now,
                ))

    def _build_operations_sales_cache(month, stores, stamp):
        key = (stamp, month)
        raw_path = Path(m.DATA_ROOT) / "cambios_muertos_actual.xlsx"
        totals = {s: 0.0 for s in stores}
        pieces = {s: 0.0 for s in stores}
        source_available = False
        monthly_sheets = []
        try:
            if raw_path.exists():
                wanted = set(stores)
                with m._xlsx_stream_book(raw_path) as book:
                    archive = book["archive"]
                    sheet_paths = book["sheet_paths"]
                    shared_value = book["shared_value"]
                    _yy, mm = (int(x) for x in month.split("-"))
                    wanted_month_name = fold(MONTH_LABELS.get(mm, str(mm)))
                    monthly_sheets = [
                        sheet for sheet in list(sheet_paths)
                        if m._monthly_sheet_name(sheet) and wanted_month_name in fold(sheet)
                    ]
                    # Nunca recorrer todos los meses como fallback: si la hoja del
                    # mes no existe, la fuente simplemente no está disponible.
                    for sheet in monthly_sheets:
                        member = sheet_paths.get(sheet, "")
                        if not member or member not in archive.namelist():
                            continue
                        row_iter = m._xlsx_monthly_rows(archive, member, shared_value)
                        first = dict(next(row_iter, {}) or {})
                        next(row_iter, None)
                        date_columns = []
                        max_column = max(first.keys(), default=28)
                        for index in range(29, max_column + 1, 3):
                            _date_iso, _week_iso, _year_iso, month_key_value = m._safe_date_iso(first.get(index))
                            if month_key_value == month:
                                date_columns.append(index)
                        if not date_columns:
                            continue
                        source_available = True
                        for values in row_iter:
                            values = dict(values or {})
                            store = canon_store(m._normalize_store_value(values.get(25, "")), stores)
                            if store not in wanted:
                                continue
                            for index in date_columns:
                                pieces[store] += max(num(values.get(index, 0)), 0.0)
                                totals[store] += max(num(values.get(index + 2, 0)), 0.0)
            _persist_operations_sales(stamp, month, stores, totals, pieces, source_available)
            print(
                f"[V297] Ventas Base Muertos listas {month}: hojas={len(monthly_sheets)} "
                f"tiendas={len(stores)} disponible={source_available}",
                flush=True,
            )
        except Exception as exc:
            print(f"[V297] Error preparando ventas {month}: {type(exc).__name__}: {exc}", flush=True)
        finally:
            with sales_jobs_lock:
                sales_jobs.discard(key)

    def operations_sales_by_store(month, stores):
        """Responde sin bloquear; prepara Base Muertos en segundo plano si falta caché."""
        stores = [s for s in stores if s]
        if not stores:
            return {}, {}, False, False
        try:
            stamp = int(m._ops_source_stamp() or 0)
        except Exception:
            stamp = 0
        if stamp <= 0:
            return {}, {}, False, False

        marks = ",".join("?" for _ in stores)
        with m.db() as con:
            cached = con.execute(
                f"SELECT store,sales_value,sales_pieces,source_available FROM sales_bonus_store_sales_v295 "
                f"WHERE source_stamp=? AND month=? AND store IN ({marks})",
                (stamp, month, *stores),
            ).fetchall()
        if len(cached) == len(stores):
            values = {str(r["store"]): num(r["sales_value"]) for r in cached}
            pieces = {str(r["store"]): num(r["sales_pieces"]) for r in cached}
            available = any(bool(r["source_available"]) for r in cached)
            return values, pieces, available, False

        try:
            meta = m.load_operations_meta() or {}
            available_months = set(str(x) for x in (meta.get("available_months") or []))
        except Exception:
            available_months = set()
        if available_months and month not in available_months:
            totals = {s: 0.0 for s in stores}
            pieces = {s: 0.0 for s in stores}
            _persist_operations_sales(stamp, month, stores, totals, pieces, False)
            return totals, pieces, False, False

        key = (stamp, month)
        with sales_jobs_lock:
            pending = key in sales_jobs
            if not pending:
                sales_jobs.add(key)
                pending = True
                threading.Thread(
                    target=_build_operations_sales_cache,
                    args=(month, list(stores), stamp),
                    daemon=True,
                    name=f"bonus-sales-{month}",
                ).start()
        return {s: 0.0 for s in stores}, {s: 0.0 for s in stores}, False, pending

    snapshot_jobs = set()
    snapshot_jobs_lock = threading.Lock()

    def _build_month_snapshots(month, stores, opening):
        source_date, _stamp, entry = opening
        job_key = (month, str(entry.get("id") or ""))
        try:
            frame = _load_or_build_bonus_capacity(entry)
            if frame is None or frame.empty:
                print(f"[V299] Snapshot {month}: capacidad sin datos", flush=True)
                return
            work = scope_frame(frame, stores)
            models = aggregate_models(work)
            now = datetime.now(MX).isoformat(timespec="seconds")
            source_period = period_for_entry(entry)
            by_store = {s: pd.DataFrame() for s in stores}
            if not models.empty:
                for store, group in models.groupby("store", sort=False):
                    by_store[str(store)] = group

            with m.db() as con:
                for store in stores:
                    con.execute("DELETE FROM sales_bonus_targets_v293 WHERE month=? AND store=?", (month, store))
                    con.execute("DELETE FROM sales_bonus_snapshot_v293 WHERE month=? AND store=?", (month, store))
                    g = by_store.get(store)
                    selected = pd.DataFrame()
                    if g is not None and not g.empty:
                        g = g.copy()
                        g["avg_investment"] = g.groupby("catalog", observed=True)["investment"].transform("mean")
                        selected = g[(g["ddi"] > 90.0) & (g["investment"] > g["avg_investment"])].copy()
                        for row in selected.to_dict("records"):
                            con.execute("""
                                INSERT INTO sales_bonus_targets_v293(
                                    month,store,id_art,catalog,model,initial_ddi,initial_existence,initial_investment,avg_investment,
                                    source_period,source_date,fixed_at
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                            """, (
                                month, store, str(row.get("id_art") or ""), str(row.get("catalog") or ""),
                                str(row.get("model") or row.get("id_art") or ""), num(row.get("ddi")), num(row.get("existence")),
                                num(row.get("investment")), num(row.get("avg_investment")), source_period, source_date.isoformat(), now,
                            ))
                    con.execute("""
                        INSERT INTO sales_bonus_snapshot_v293(month,store,source_period,source_date,fixed_at,model_count)
                        VALUES(?,?,?,?,?,?)
                    """, (month, store, source_period, source_date.isoformat(), now, int(len(selected))))
            print(
                f"[V299] Snapshot Bonos {month} listo · corte={source_date.isoformat()} · "
                f"tiendas={len(stores)} · modelos={len(models)}",
                flush=True,
            )
            try:
                del work, models, frame
                m._release_process_memory()
            except Exception:
                pass
        except Exception as exc:
            print(f"[V299] Error snapshot Bonos {month}: {type(exc).__name__}: {exc}", flush=True)
        finally:
            with snapshot_jobs_lock:
                snapshot_jobs.discard(job_key)

    def ensure_snapshots(month, stores):
        """Nunca construye la cartera mensual dentro de la petición HTTP."""
        stores = [s for s in stores if s]
        if not stores:
            return {"entry": None, "created": 0, "pending": False}
        opening = opening_capacity_entry(month)
        if not opening:
            return {"entry": None, "created": 0, "pending": False}
        source_date, _stamp, entry = opening
        expected_source_date = source_date.isoformat()

        with m.db() as con:
            rows = con.execute(
                "SELECT store,source_date FROM sales_bonus_snapshot_v293 WHERE month=?",
                (month,),
            ).fetchall()
        valid_existing = {
            str(r["store"]) for r in rows
            if str(r["source_date"] or "") == expected_source_date
        }
        missing = [s for s in stores if s not in valid_existing]
        if not missing:
            return {"entry": entry, "created": 0, "pending": False}

        job_key = (month, str(entry.get("id") or ""))
        with snapshot_jobs_lock:
            pending = job_key in snapshot_jobs
            if not pending:
                snapshot_jobs.add(job_key)
                pending = True
                threading.Thread(
                    target=_build_month_snapshots,
                    args=(month, list(missing), opening),
                    daemon=True,
                    name=f"bonus-snapshot-{month}",
                ).start()
        return {"entry": entry, "created": 0, "pending": pending}

    def actor_stores(actor):
        stores = all_stores()
        role = str(actor.get("role") or "").lower()
        if role in RESTRICTED:
            assigned = canon_store(actor.get("store"), stores)
            return [assigned] if assigned in stores else []
        return stores

    def target_rows(month, stores):
        if not stores:
            return []
        marks = ",".join("?" for _ in stores)
        with m.db() as con:
            rows = con.execute(
                f"SELECT * FROM sales_bonus_targets_v293 WHERE month=? AND store IN ({marks}) ORDER BY store,catalog,id_art",
                (month, *stores),
            ).fetchall()
        return [dict(r) for r in rows]

    def snapshot_rows(month, stores):
        if not stores:
            return {}
        marks = ",".join("?" for _ in stores)
        with m.db() as con:
            rows = con.execute(
                f"SELECT * FROM sales_bonus_snapshot_v293 WHERE month=? AND store IN ({marks})",
                (month, *stores),
            ).fetchall()
        return {str(r["store"]): dict(r) for r in rows}

    def attendance_rows(month, stores):
        if not stores:
            return {}
        marks = ",".join("?" for _ in stores)
        with m.db() as con:
            rows = con.execute(
                f"SELECT store,attendance_pct,updated_at,updated_by FROM sales_bonus_attendance_v293 WHERE month=? AND store IN ({marks})",
                (month, *stores),
            ).fetchall()
        return {str(r["store"]): dict(r) for r in rows}

    def current_maps(month, stores, targets):
        sales, sales_pieces, sales_available, sales_pending = operations_sales_by_store(month, stores)
        if not targets:
            return None, {}, sales, sales_pieces, sales_available, sales_pending, False
        current_pick = current_capacity_entry(month)
        if not current_pick:
            return None, {}, sales, sales_pieces, sales_available, sales_pending, False
        _d, _stamp, entry = current_pick
        frame, capacity_pending = load_frame(entry)
        if frame is None or frame.empty:
            return None, {}, sales, sales_pieces, sales_available, sales_pending, bool(capacity_pending)
        work = scope_frame(frame, stores)
        current = {}
        ids_by_store = defaultdict(set)
        for row in targets:
            ids_by_store[str(row.get("store") or "")].add(str(row.get("id_art") or ""))
        if ids_by_store and not work.empty and "ID_ART" in work.columns:
            w = work.copy()
            w["store"] = w.get("Tienda", "").astype(str).map(lambda x: canon_store(x, all_stores()))
            w["id_art"] = w["ID_ART"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            valid = pd.Series(False, index=w.index)
            for store, ids in ids_by_store.items():
                if ids:
                    valid = valid | ((w["store"] == store) & w["id_art"].isin(ids))
            w = w.loc[valid]
            if not w.empty:
                w["ddi"] = pd.to_numeric(w.get("DDI", 0), errors="coerce").fillna(0.0)
                w["existence"] = pd.to_numeric(w.get("Existencia", 0), errors="coerce").fillna(0.0)
                w["investment"] = pd.to_numeric(w.get("Inversión", 0), errors="coerce").fillna(0.0)
                agg = w.groupby(["store", "id_art"], sort=False, observed=True).agg(
                    ddi=("ddi", "max"), existence=("existence", "max"), investment=("investment", "max")
                ).reset_index()
                current = {
                    (str(x["store"]), str(x["id_art"])): {
                        "ddi": num(x["ddi"]), "existence": num(x["existence"]), "investment": num(x["investment"])
                    } for x in agg.to_dict("records")
                }
        try:
            del work, frame
            m._release_process_memory()
        except Exception:
            pass
        return entry, current, sales, sales_pieces, sales_available, sales_pending, bool(capacity_pending)

    def build_store_metric(store, month, rows, current, sales, sales_pieces, sales_available, attendance, snapshot, current_entry):
        details = []
        by_cat = {c: [] for c in CATALOGS}
        for row in rows:
            ident = str(row.get("id_art") or "")
            cur = current.get((store, ident))
            has_current = current_entry is not None
            current_ddi = num(cur.get("ddi")) if cur is not None else (0.0 if has_current else num(row.get("initial_ddi")))
            current_exist = num(cur.get("existence")) if cur is not None else (0.0 if has_current else num(row.get("initial_existence")))
            current_inv = num(cur.get("investment")) if cur is not None else (0.0 if has_current else num(row.get("initial_investment")))
            initial_ddi = num(row.get("initial_ddi"))
            initial_exist = num(row.get("initial_existence"))
            initial_inv = num(row.get("initial_investment"))
            ddi_red = ((initial_ddi - current_ddi) / initial_ddi * 100.0) if initial_ddi > 0 else 0.0
            inv_red = ((initial_inv - current_inv) / initial_inv * 100.0) if initial_inv > 0 else 0.0
            progress = (max(0.0, min(100.0, ddi_red)) + max(0.0, min(100.0, inv_red))) / 2.0
            status = "Excelente" if progress >= 85 else "Bueno" if progress >= 60 else "En riesgo" if progress >= 30 else "Crítico"
            item = {
                "id_art": ident,
                "model": str(row.get("model") or ident),
                "catalog": str(row.get("catalog") or ""),
                "initial_ddi": round(initial_ddi, 1),
                "current_ddi": round(current_ddi, 1),
                "initial_existence": round(initial_exist, 1),
                "current_existence": round(current_exist, 1),
                "initial_investment": round(initial_inv, 2),
                "current_investment": round(current_inv, 2),
                "ddi_reduction_pct": round(ddi_red, 1),
                "investment_reduction_pct": round(inv_red, 1),
                "progress_pct": round(progress, 1),
                "ddi_reduced": bool(has_current and current_ddi < initial_ddi),
                "investment_reduced": bool(has_current and current_inv < initial_inv),
                "status": status,
            }
            details.append(item)
            if item["catalog"] in by_cat:
                by_cat[item["catalog"]].append(item)
        catalog_summary = []
        component_values = []
        for catalog in CATALOGS:
            items = by_cat[catalog]
            total = len(items)
            ddi_pct = (sum(1 for x in items if x["ddi_reduced"]) / total * 100.0) if total else 0.0
            inv_pct = (sum(1 for x in items if x["investment_reduced"]) / total * 100.0) if total else 0.0
            combined = (ddi_pct + inv_pct) / 2.0 if total else 0.0
            if total:
                component_values.append(combined)
            catalog_summary.append({
                "catalog": catalog,
                "models": total,
                "ddi_reduced_models": sum(1 for x in items if x["ddi_reduced"]),
                "investment_reduced_models": sum(1 for x in items if x["investment_reduced"]),
                "ddi_reduction_pct": round(ddi_pct, 1),
                "investment_reduction_pct": round(inv_pct, 1),
                "combined_pct": round(combined, 1),
            })
        ddi_component_raw = sum(component_values) / len(component_values) if component_values else 0.0
        ddi_component = ddi_component_raw if current_entry is not None else None
        goal = store_goal(store, month)
        actual_sales = num(sales.get(store))
        actual_sales_pieces = num(sales_pieces.get(store))
        sales_pct = (actual_sales / goal * 100.0) if sales_available and goal > 0 else None
        att = attendance.get(store)
        attendance_pct = num(att.get("attendance_pct")) if att is not None else None
        score = 0.0
        if sales_pct is not None:
            score += min(max(sales_pct, 0.0), 100.0) * 0.50
        if ddi_component is not None:
            score += min(max(ddi_component, 0.0), 100.0) * 0.30
        if attendance_pct is not None:
            score += min(max(attendance_pct, 0.0), 100.0) * 0.20
        ready = bool(goal > 0 and sales_available and current_entry is not None and attendance_pct is not None)
        snap = snapshot.get(store) or {}
        details.sort(key=lambda x: (x["progress_pct"], x["id_art"]))
        return {
            "store": store,
            "month": month,
            "period_label": period_label(month),
            "sales": {
                "actual": round(actual_sales, 2),
                "pieces": round(actual_sales_pieces, 1),
                "goal": round(goal, 2),
                "pct": None if sales_pct is None else round(sales_pct, 1),
                "available": bool(sales_available),
                "source": "Base Muertos / Cambios",
            },
            "ddi": {
                "pct": None if ddi_component is None else round(ddi_component, 1),
                "catalogs": catalog_summary,
                "available": bool(current_entry is not None),
                "source": "Capacidades",
            },
            "attendance": {"pct": None if attendance_pct is None else round(attendance_pct, 1), "updated_at": str((att or {}).get("updated_at") or ""), "updated_by": str((att or {}).get("updated_by") or "")},
            "score": round(score, 1),
            "score_ready": ready,
            "target_models": len(details),
            "snapshot": {
                "source_period": str(snap.get("source_period") or ""),
                "source_date": str(snap.get("source_date") or ""),
                "fixed_at": str(snap.get("fixed_at") or ""),
            },
            "details": details,
        }

    def monthly_payload(actor, month, selected_store):
        stores = actor_stores(actor)
        snapshot_state = ensure_snapshots(month, stores)
        targets = target_rows(month, stores)
        snapshots = snapshot_rows(month, stores)
        attendance = attendance_rows(month, stores)
        current_entry, current, sales, sales_pieces, sales_available, sales_pending, capacity_pending = current_maps(month, stores, targets)
        capacity_pending = bool(capacity_pending or snapshot_state.get("pending"))
        by_store = defaultdict(list)
        for row in targets:
            by_store[str(row.get("store") or "")].append(row)
        metrics = [build_store_metric(s, month, by_store.get(s, []), current, sales, sales_pieces, sales_available, attendance, snapshots, current_entry) for s in stores]
        ranking = sorted(metrics, key=lambda x: (not x["score_ready"], -x["score"], norm(x["store"])))
        position = 0
        for item in ranking:
            if item["score_ready"]:
                position += 1
                item["rank"] = position
            else:
                item["rank"] = None
        selected = canon_store(selected_store, stores) if selected_store else ""
        if selected not in stores:
            actor_store = canon_store(actor.get("store"), stores)
            selected = actor_store if actor_store in stores else (ranking[0]["store"] if ranking else (stores[0] if stores else ""))
        selected_metric = next((x for x in metrics if x["store"] == selected), None)
        return {
            "month": month,
            "period_label": period_label(month),
            "months": [{"value": x, "label": period_label(x)} for x in available_goal_months()],
            "stores": stores,
            "selected_store": selected,
            "selected": selected_metric,
            "ranking": [{
                "rank": x["rank"], "store": x["store"], "sales_pct": x["sales"]["pct"], "ddi_pct": x["ddi"]["pct"],
                "attendance_pct": x["attendance"]["pct"], "score": x["score"], "score_ready": x["score_ready"],
                "target_models": x["target_models"],
            } for x in ranking],
            "current_source_period": period_for_entry(current_entry),
            "current_source_date": m._capacity_report_date(current_entry).isoformat() if current_entry else "",
            "can_edit_attendance": str(actor.get("role") or "").lower() in ADMIN,
            "weights": {"sales": 50, "ddi": 30, "attendance": 20},
            "rules": {"ddi_gt": 90, "investment": "Mayor al promedio del catálogo por tienda", "snapshot": "Listado fijo mensual"},
            "meta_source": "METAS 2026.xlsx · hoja ROPA · valores convertidos de miles de pesos a MXN",
            "sources": {
                "capacity": "Capacidades: Existencia, DDI e Inversión",
                "sales": "Base Muertos / Cambios: Ventas mensuales",
                "attendance": "Captura de Asistencia",
            },
            "source_dates": {
                "opening_capacity": str((snapshot_state.get("entry") and m._capacity_report_date(snapshot_state.get("entry")).isoformat()) or ""),
                "current_capacity": m._capacity_report_date(current_entry).isoformat() if current_entry else "",
                "base_muertos_latest": str(max((m.load_operations_meta() or {}).get("available_dates") or [""]) or ""),
            },
            "processing": {
                "sales": bool(sales_pending),
                "capacity": bool(capacity_pending),
            },
        }

    @m.app.get("/api/operation/sales-bonus-v293")
    def sales_bonus_v293(request: Request, month: str = "", store: str = ""):
        actor = m.require_user(request)
        return monthly_payload(actor, month_key(month), store)

    @m.app.post("/api/operation/sales-bonus-v293/attendance")
    async def sales_bonus_attendance_v293(request: Request):
        actor = m.require_user(request, ADMIN)
        body = await request.json()
        month = month_key(body.get("month"))
        stores = all_stores()
        store = canon_store(body.get("store"), stores)
        if store not in stores:
            raise HTTPException(400, "Tienda inválida")
        pct = num(body.get("attendance_pct"))
        if pct < 0 or pct > 100:
            raise HTTPException(400, "La asistencia debe estar entre 0 y 100%")
        now = datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            con.execute("""
                INSERT INTO sales_bonus_attendance_v293(month,store,attendance_pct,updated_at,updated_by)
                VALUES(?,?,?,?,?)
                ON CONFLICT(month,store) DO UPDATE SET
                    attendance_pct=excluded.attendance_pct,
                    updated_at=excluded.updated_at,
                    updated_by=excluded.updated_by
            """, (month, store, pct, now, str(actor.get("username") or "")))
        return {"ok": True, "message": "Asistencia actualizada", "attendance_pct": round(pct, 1)}

    css = r'''<style id="v293-bonus-css">
body[data-v163-module="operation"][data-v293-view="bonuses"] #operativoPeriodBar{display:none!important}
.v293{color:#123f73;min-width:0}.v293 *{box-sizing:border-box}.v293-head{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin:2px 0 7px}.v293-title h2{font-size:17px!important;margin:0!important}.v293-sub{font-size:7px;font-weight:800;color:#60758b;margin-top:2px}.v293-filters{display:grid;grid-template-columns:180px 150px 170px;gap:6px}.v293-field label{display:block;font-size:6px;font-weight:950;color:#66798d;margin:0 0 2px}.v293-field select,.v293-field input{width:100%;height:31px;border:1px solid #ccdae8;border-radius:8px;background:#fff;color:#173f72;padding:0 8px;font-size:7px;font-weight:850}.v293-tabs{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:3px;margin:5px 0 8px;padding:3px;border:1px solid #dce7f1;border-radius:10px;background:#f8fbfe}.v293-tabs button{height:32px;border:0;border-radius:7px;background:transparent;color:#365a7e;font-size:6.5px;font-weight:950;white-space:nowrap}.v293-tabs button.active{background:#176fe8;color:#fff;box-shadow:0 2px 8px rgba(23,111,232,.18)}
.v293-top{display:grid;grid-template-columns:1.08fr .82fr 1.1fr;gap:6px}.v293-panel{border:1px solid #dae5ef;border-radius:11px;background:#fff;overflow:hidden}.v293-ph{display:flex;justify-content:space-between;align-items:center;padding:7px 9px;font-size:8px;font-weight:950;color:#123f73;border-bottom:1px solid #e9eff5}.v293-info{display:inline-grid;place-items:center;width:15px;height:15px;border:1px solid #b9ccdf;border-radius:50%;font-size:6px;color:#4f6f8f}.v293-components{padding:8px;display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.v293-comp{border:1px solid #dce6ef;border-radius:10px;overflow:hidden;text-align:center;min-width:0}.v293-comp .w{padding:5px 3px;color:#fff;font-size:8px;font-weight:950}.v293-comp.sales .w{background:#1eae68}.v293-comp.ddi .w{background:#ff8a2b}.v293-comp.att .w{background:#7149e8}.v293-comp .ico{height:38px;display:grid;place-items:center}.v293-comp .ico svg{width:27px;height:27px;stroke:currentColor;fill:none;stroke-width:1.8}.v293-comp.sales{color:#129159}.v293-comp.ddi{color:#e45f00}.v293-comp.att{color:#6336d1}.v293-big{font-size:22px;font-weight:950;color:#102f52;line-height:1}.v293-badge{display:inline-flex;margin:5px 0 7px;padding:4px 8px;border-radius:999px;background:#eaf8f0;color:#137345;font-size:6px;font-weight:950}.v293-badge.warn{background:#fff4d6;color:#9a6500}.v293-badge.bad{background:#ffe9eb;color:#b12239}.v293-source{font-size:5.3px;color:#6f8295;font-weight:850;margin:-2px 3px 5px}.v293-att-edit{display:flex;gap:3px;padding:0 5px 6px}.v293-att-edit input{min-width:0;width:100%;height:25px;border:1px solid #d1ddea;border-radius:6px;padding:0 5px;font-size:7px}.v293-att-edit button{border:0;border-radius:6px;background:#7149e8;color:#fff;padding:0 7px;font-size:6px;font-weight:900}
.v293-score{padding:10px;display:grid;place-items:center}.v293-ring{--p:0;width:132px;height:132px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#20b96b calc(var(--p)*1%),#edf2f6 0);position:relative}.v293-ring:after{content:'';position:absolute;width:96px;height:96px;background:#fff;border-radius:50%}.v293-ring>div{position:relative;z-index:1;text-align:center}.v293-ring b{display:block;font-size:27px;color:#102f52}.v293-ring small{font-size:6px;color:#65798c;font-weight:850}.v293-score-note{margin-top:7px;text-align:center;font-size:7px;color:#60758a;font-weight:800}.v293-score.pending .v293-ring{background:conic-gradient(#9fb0c0 calc(var(--p)*1%),#edf2f6 0)}
.v293-rank-wrap{overflow:auto;max-height:265px}.v293-table{width:100%;border-collapse:collapse;min-width:690px;table-layout:auto}.v293-table th{background:#eff5fb;color:#21496f;padding:5px 4px;font-size:5.5px;text-align:center;white-space:nowrap}.v293-table td{border-top:1px solid #edf2f6;padding:5px 4px;font-size:6px;text-align:center;white-space:nowrap}.v293-table td.left,.v293-table th.left{text-align:left}.v293-table tr.selected{background:#e9f3ff}.v293-cell-good{background:#e3f7ea!important;color:#126d41;font-weight:900}.v293-cell-mid{background:#fff2cc!important;color:#8b6300;font-weight:900}.v293-cell-bad{background:#ffe1e5!important;color:#aa2038;font-weight:900}
.v293-mid{display:grid;grid-template-columns:.85fr 1.15fr;gap:6px;margin-top:6px}.v293-target{padding:9px;display:grid;grid-template-columns:110px 1fr;gap:8px;align-items:center}.v293-target-num{text-align:center}.v293-target-num .target{font-size:31px;font-weight:950;color:#102f52}.v293-target-num small{display:block;font-size:6px;color:#65798c}.v293-mini{width:100%;border-collapse:collapse}.v293-mini th,.v293-mini td{padding:5px;border-bottom:1px solid #edf2f6;font-size:6px;text-align:center}.v293-mini th{color:#4b6783;background:#f7faff}.v293-cats{padding:7px;display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.v293-cat{border:1px solid #e0e8f1;border-radius:9px;padding:7px;min-width:0}.v293-cat h4{margin:0 0 5px;font-size:8px;display:flex;gap:5px;align-items:center}.v293-cat h4 svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.8}.v293-cat b{font-size:15px}.v293-cat small{font-size:5.5px;color:#6c8094}.v293-two{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:6px}.v293-two div{padding:5px;border-radius:7px;background:#f3faf6;text-align:center}.v293-two span{display:block;font-size:5px;color:#688078}.v293-two strong{font-size:10px;color:#148050}
.v293-detail{margin-top:6px}.v293-tools{display:flex;align-items:center;justify-content:space-between;gap:5px;padding:6px}.v293-tools-left{display:flex;align-items:center;gap:6px;font-size:7px;font-weight:950}.v293-tools-right{display:flex;gap:5px}.v293-tools input,.v293-tools select{height:28px;border:1px solid #ccd9e7;border-radius:7px;padding:0 7px;font-size:6px;color:#234d73}.v293-detail-wrap{overflow:auto;max-height:410px}.v293-bar{display:inline-flex;align-items:center;gap:4px;min-width:95px}.v293-bar span{display:block;width:70px;height:8px;background:#edf1f5;border-radius:99px;overflow:hidden}.v293-bar i{display:block;height:100%;background:#20b96b}.v293-status{display:inline-flex;padding:3px 6px;border-radius:999px;font-size:5.5px;font-weight:950}.v293-status.critical{background:#ffe5e8;color:#b31f38}.v293-status.risk{background:#fff0d5;color:#9c6100}.v293-status.good{background:#e6f8ed;color:#137446}.v293-status.excellent{background:#ede8ff;color:#6033ca}.v293-note{padding:6px 9px;background:#f6f9fc;border-top:1px solid #e4ecf3;font-size:5.5px;color:#687d91}.v293-empty{padding:24px;text-align:center;color:#6b7f92;font-size:8px}.v293-only{display:none}
@media(max-width:900px){.v293-head{align-items:flex-start}.v293-title h2{font-size:12px!important}.v293-sub{font-size:5px}.v293-filters{grid-template-columns:repeat(3,minmax(0,1fr));width:52%}.v293-field select,.v293-field input{height:26px;font-size:5px;padding:0 4px}.v293-tabs{gap:2px;margin:3px 0 5px}.v293-tabs button{height:26px;font-size:4.7px;padding:0 2px}.v293-top{gap:3px}.v293-ph{padding:5px 6px;font-size:5.7px}.v293-components{padding:5px;gap:3px}.v293-comp .w{font-size:5.5px;padding:4px 2px}.v293-comp .ico{height:28px}.v293-comp .ico svg{width:19px;height:19px}.v293-big{font-size:15px}.v293-badge{font-size:4.5px;margin:3px 0 4px;padding:3px 5px}.v293-ring{width:91px;height:91px}.v293-ring:after{width:65px;height:65px}.v293-ring b{font-size:18px}.v293-ring small{font-size:4px}.v293-score{padding:6px}.v293-score-note{font-size:4.5px}.v293-rank-wrap{max-height:190px}.v293-table{min-width:620px}.v293-table th,.v293-table td{font-size:4.5px;padding:4px 2px}.v293-mid{gap:3px;margin-top:3px}.v293-target{padding:5px;grid-template-columns:70px 1fr}.v293-target-num .target{font-size:21px}.v293-mini th,.v293-mini td{font-size:4.5px;padding:3px}.v293-cats{padding:4px;gap:3px}.v293-cat{padding:4px}.v293-cat h4{font-size:5.5px}.v293-cat h4 svg{width:14px;height:14px}.v293-cat b{font-size:11px}.v293-cat small,.v293-two span{font-size:4px}.v293-two strong{font-size:7px}.v293-detail{margin-top:3px}.v293-tools{padding:4px}.v293-tools-left{font-size:5px}.v293-tools input,.v293-tools select{height:24px;font-size:4.5px}.v293-detail-wrap{max-height:300px}.v293-note{font-size:4px}}
@media(max-width:620px){.v293{min-width:760px;transform-origin:top left}.v293-head{gap:4px}.v293-filters{width:56%}.v293-top{grid-template-columns:1.08fr .82fr 1.1fr}.v293-mid{grid-template-columns:.85fr 1.15fr}}
.shell.sidebar-collapsed .nav[data-main="bonuses"]:before{content:"★";font-size:18px;display:block}
#page-bonuses{min-width:0}
#page-bonuses #v293StandaloneHost{min-width:0}
body[data-v293-standalone="1"] #analysisNav,body[data-v293-standalone="1"] #operativoNav,body[data-v293-standalone="1"] #globalFilters{display:none!important}
</style>'''

    js = r'''<script id="v293-bonus-js">(function(){if(window.__V293_SALES_BONUS)return;window.__V293_SALES_BONUS=true;
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)],esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),n=v=>Number(v||0)||0,nf=v=>Math.round(n(v)).toLocaleString('es-MX'),pc=v=>v==null?'N/D':n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%',money=v=>'$'+n(v).toLocaleString('es-MX',{maximumFractionDigits:0});
let S={month:'',store:'',view:'summary',catalog:'Todos',data:null,busy:false,seq:0,controller:null,poll:null};
const isOp=()=>String(document.body.dataset.v163Module||'').toLowerCase()==='operation';
async function A(u,o={}){let r=await fetch(u,{credentials:'same-origin',cache:'no-store',...o}),d={};try{d=await r.json()}catch(_){d={}}if(!r.ok)throw new Error(d.detail||d.message||('HTTP '+r.status));return d}
function icon(kind){if(kind==='sales')return '<svg viewBox="0 0 24 24"><path d="M4 19V11M10 19V7M16 19V4M3 19h18"/></svg>';if(kind==='ddi')return '<svg viewBox="0 0 24 24"><path d="M4 7l8-4 8 4-8 4-8-4Z"/><path d="M4 7v10l8 4 8-4V7M12 11v10"/></svg>';if(kind==='att')return '<svg viewBox="0 0 24 24"><circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2.5 20c.5-4 2.6-6 5.5-6s5 2 5.5 6M13 15c3.8-.6 6.7 1.1 7.5 5"/></svg>';if(kind==='coat')return '<svg viewBox="0 0 24 24"><path d="M8 3 5 5 3 11l4 2v8h10v-8l4-2-2-6-3-2-4 3-4-3Z"/><path d="M12 6v15M8 3c.7 2 1.8 3 4 3s3.3-1 4-3"/></svg>';if(kind==='license')return '<svg viewBox="0 0 24 24"><path d="m5 19 9-9M4 20l2-5 3 3-5 2ZM15 3l.7 2.3L18 6l-2.3.7L15 9l-.7-2.3L12 6l2.3-.7L15 3ZM20 8l.5 1.5L22 10l-1.5.5L20 12l-.5-1.5L18 10l1.5-.5L20 8Z"/></svg>';return '<svg viewBox="0 0 24 24"><path d="M8 4 4 7l3 4v9h10v-9l3-4-4-3-4 3-4-3Z"/><path d="M9 4c.5 2 1.5 3 3 3s2.5-1 3-3"/></svg>'}
function badge(v){let x=n(v);if(x>=90)return ['Excelente',''];if(x>=70)return ['Bueno',''];if(x>=50)return ['En riesgo','warn'];return ['Crítico','bad']}
function cellClass(v){if(v==null)return '';v=n(v);return v>=90?'v293-cell-good':v>=70?'v293-cell-mid':'v293-cell-bad'}
function syncMobile(){let mn=q('#mobileMainNav');if(!mn)return;let visible=qa(':scope > .mnav',mn).filter(x=>!x.classList.contains('hidden')&&!x.hidden).length;mn.style.setProperty('grid-template-columns','repeat('+Math.max(1,visible)+',1fr)','important')}
function menu(){let side=q('#sidebar'),b=q('#sidebar [data-main="bonuses"]');if(side&&!b){b=document.createElement('button');b.className='nav';b.dataset.main='bonuses';b.innerHTML='Bonos<small>Venta vs Meta, DDI y Asistencia</small>';let before=q('#sidebar [data-main="users"]')||q('#sidebar [data-main="share"]')||q('#sidebar .profile');before?side.insertBefore(b,before):side.appendChild(b)}
let mn=q('#mobileMainNav'),mb=q('#mobileMainNav [data-main="bonuses"]');if(mn&&!mb){mb=document.createElement('button');mb.className='mnav';mb.dataset.main='bonuses';mb.innerHTML='<span class="mnav-icon">★</span><span>Bonos</span>';let before=q('#mobileMainNav [data-main="users"]')||q('#mobileMainNav [data-main="share"]');before?mn.insertBefore(mb,before):mn.appendChild(mb)}
let main=q('main.main'),page=q('#page-bonuses');if(main&&!page){page=document.createElement('section');page.className='page';page.id='page-bonuses';page.innerHTML='<div id="v293StandaloneHost"></div>';main.appendChild(page)}
let role='';try{role=String(USER?.role||'').toLowerCase()}catch(_){}let blocked=['colaborador_lenceria','colaborador_operativo'].includes(role);if(b)b.classList.toggle('hidden',blocked);if(mb)mb.classList.toggle('hidden',blocked);syncMobile();return {b,mb}}
function active(){menu();try{MAIN='bonuses'}catch(_){}document.body.dataset.v293Standalone='1';qa('[data-main]').forEach(x=>x.classList.toggle('active',x.dataset.main==='bonuses'));q('#analysisNav')?.classList.add('hidden');q('#operativoNav')?.classList.add('hidden');q('#globalFilters')?.classList.add('hidden');qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-bonuses'));let t=q('#heroTitle'),s=q('#heroSub');if(t)t.textContent='Bonos';if(s)s.textContent='Venta vs Meta, reducción de DDI e inversión y asistencia'}
function filters(d){return '<div class="v293-filters"><div class="v293-field"><label>Tienda</label><select id="v293Store">'+(d.stores||[]).map(x=>'<option '+(x===d.selected_store?'selected':'')+'>'+esc(x)+'</option>').join('')+'</select></div><div class="v293-field"><label>Periodo</label><select id="v293Month">'+(d.months||[]).map(x=>'<option value="'+x.value+'" '+(x.value===d.month?'selected':'')+'>'+esc(x.label)+'</option>').join('')+'</select></div><div class="v293-field"><label>Catálogo</label><select id="v293Catalog"><option>Todos</option>'+['Abrigador','Licencias','Básicos'].map(x=>'<option '+(S.catalog===x?'selected':'')+'>'+x+'</option>').join('')+'</select></div></div>'}
function tabs(){let xs=[['summary','Resumen general'],['ranking','Ranking de tiendas'],['models','Modelos a detalle'],['Abrigador','Abrigador'],['Licencias','Licencias'],['Básicos','Básicos']];return '<div class="v293-tabs">'+xs.map(x=>'<button data-v293-view="'+x[0]+'" class="'+(S.view===x[0]?'active':'')+'">'+x[1]+'</button>').join('')+'</div>'}
function compCard(cls,title,weight,value,ico,extra){let b=badge(value),display=value==null?'N/D':pc(value);return '<div class="v293-comp '+cls+'"><div class="w">'+weight+'%<br>'+title+'</div><div class="ico">'+icon(ico)+'</div><div class="v293-big">'+display+'</div><span class="v293-badge '+b[1]+'">'+(value==null?'Pendiente':b[0])+'</span>'+extra+'</div>'}
function components(d){let s=d.selected;if(!s)return '<div class="v293-empty">Sin tienda disponible.</div>';let edit='';if(d.can_edit_attendance){edit='<div class="v293-att-edit"><input id="v293Att" type="number" min="0" max="100" step="0.1" placeholder="%" value="'+(s.attendance.pct==null?'':s.attendance.pct)+'"><button id="v293AttSave">Guardar</button></div>'}let salesState=d.processing?.sales?'preparando ventas…':(s.sales.available?(money(s.sales.actual)+' venta · '+nf(s.sales.pieces)+' pzas'):('sin datos del mes'+(d.source_dates?.base_muertos_latest?' · última fecha '+esc(d.source_dates.base_muertos_latest):'')));let capState=d.processing?.capacity?' · preparando capacidad…':(d.source_dates?.opening_capacity?' · corte inicial '+esc(d.source_dates.opening_capacity):'');let salesSrc='<div class="v293-source">Fuente: Base Muertos · '+salesState+'</div>';let ddiSrc='<div class="v293-source">Fuente: Capacidades · Existencia + DDI + Inversión'+capState+'</div>';let attSrc='<div class="v293-source">Fuente: Asistencia</div>';return '<section class="v293-panel"><div class="v293-ph"><span>Desempeño por componente del bono</span><span class="v293-info">i</span></div><div class="v293-components">'+compCard('sales','Venta vs Meta',50,s.sales.pct,'sales',salesSrc)+compCard('ddi','DDI por Cat',30,s.ddi.pct,'ddi',ddiSrc)+compCard('att','Asistencia',20,s.attendance.pct,'att',attSrc+edit)+'</div></section>'}
function score(d){let s=d.selected;if(!s)return '';return '<section class="v293-panel"><div class="v293-ph"><span>Resultado del Bono · '+esc(s.store)+'</span><span class="v293-info">i</span></div><div class="v293-score '+(s.score_ready?'':'pending')+'"><div class="v293-ring" style="--p:'+Math.min(100,n(s.score))+'"><div><b>'+pc(s.score)+'</b><small>'+(s.score_ready?'Cumplimiento':'Parcial · falta información')+'</small></div></div><div class="v293-score-note">50% Venta vs Meta + 30% DDI por Cat + 20% Asistencia</div></div></section>'}
function rankRows(d,limit){let a=d.ranking||[];if(limit)a=a.slice(0,limit);return a.map(r=>'<tr class="'+(r.store===d.selected_store?'selected':'')+'" data-v293-store="'+esc(r.store)+'"><td>'+(r.rank??'—')+'</td><td class="left"><b>'+esc(r.store)+'</b></td><td class="'+cellClass(r.sales_pct)+'">'+pc(r.sales_pct)+'</td><td class="'+cellClass(r.ddi_pct)+'">'+pc(r.ddi_pct)+'</td><td class="'+cellClass(r.attendance_pct)+'">'+pc(r.attendance_pct)+'</td><td><b>'+(r.score_ready?pc(r.score):pc(r.score)+'*')+'</b></td></tr>').join('')}
function ranking(d,full=false){return '<section class="v293-panel"><div class="v293-ph"><span>🏆 Ranking de tiendas (de mejor a peor)</span><span>'+((d.ranking||[]).filter(x=>x.score_ready).length)+' con score completo</span></div><div class="v293-rank-wrap"><table class="v293-table"><thead><tr><th>#</th><th class="left">Tienda</th><th>Venta vs Meta<br>50%</th><th>DDI por Cat<br>30%</th><th>Asistencia<br>20%</th><th>Resultado<br>Bono</th></tr></thead><tbody>'+rankRows(d,full?0:8)+'</tbody></table></div><div class="v293-note">Venta: Base Muertos / Cambios · DDI, existencia e inversión: Capacidades · * Score parcial si falta alguna fuente o Asistencia.</div></section>'}
function catIcon(c){return c==='Abrigador'?icon('coat'):c==='Licencias'?icon('license'):icon('basic')}
function targetSummary(d){let s=d.selected;if(!s)return '';let cats=s.ddi.catalogs||[];return '<section class="v293-panel"><div class="v293-ph"><span>Modelos objetivo destacados</span><span class="v293-info">i</span></div><div class="v293-target"><div class="v293-target-num"><div class="target">'+nf(s.target_models)+'</div><small>modelos fijos del mes</small></div><table class="v293-mini"><thead><tr><th>Catálogo</th><th>Modelos</th><th>%</th></tr></thead><tbody>'+cats.map(x=>'<tr><td>'+esc(x.catalog)+'</td><td>'+nf(x.models)+'</td><td>'+pc(s.target_models?x.models/s.target_models*100:0)+'</td></tr>').join('')+'</tbody></table></div><div class="v293-note">Criterio fijo: DDI inicial &gt; 90 días e inversión inicial mayor al promedio del catálogo en la tienda. Fuente inicial: '+esc(s.snapshot.source_period||'Sin capacidad del mes')+'.</div></section>'}
function catalogSummary(d){let s=d.selected;if(!s)return '';return '<section class="v293-panel"><div class="v293-ph"><span>Resumen por catálogo (modelos objetivo)</span><span class="v293-info">i</span></div><div class="v293-cats">'+(s.ddi.catalogs||[]).map(x=>'<div class="v293-cat"><h4>'+catIcon(x.catalog)+' '+esc(x.catalog)+'</h4><b>'+nf(x.ddi_reduced_models)+' / '+nf(x.models)+'</b><small>modelos con DDI reducido</small><div class="v293-two"><div><span>Reducción DDI</span><strong>'+pc(x.ddi_reduction_pct)+'</strong></div><div><span>Reducción inversión</span><strong>'+pc(x.investment_reduction_pct)+'</strong></div></div></div>').join('')+'</div><div class="v293-note">El 30% del bono usa el promedio de avance de los catálogos con modelos objetivo; dentro de cada catálogo se promedia % de modelos que redujeron DDI y % de modelos que redujeron inversión.</div></section>'}
function detailRows(d){let s=d.selected;if(!s)return '';let rows=s.details||[],f=S.catalog!=='Todos'?S.catalog:(['Abrigador','Licencias','Básicos'].includes(S.view)?S.view:'Todos'),term=(q('#v293Search')?.value||'').trim().toLowerCase();if(f!=='Todos')rows=rows.filter(x=>x.catalog===f);if(term)rows=rows.filter(x=>(x.id_art+' '+x.model).toLowerCase().includes(term));return rows.map((r,i)=>{let cls=r.status==='Crítico'?'critical':r.status==='En riesgo'?'risk':r.status==='Bueno'?'good':'excellent';return '<tr><td>'+(i+1)+'</td><td class="left"><b>'+esc(r.id_art)+'</b></td><td class="left">'+esc(r.model)+'</td><td>'+esc(r.catalog)+'</td><td>'+n(r.initial_existence).toLocaleString('es-MX',{maximumFractionDigits:0})+'</td><td>'+n(r.current_existence).toLocaleString('es-MX',{maximumFractionDigits:0})+'</td><td>'+n(r.initial_ddi).toLocaleString('es-MX',{maximumFractionDigits:1})+'</td><td>'+n(r.current_ddi).toLocaleString('es-MX',{maximumFractionDigits:1})+'</td><td>'+money(r.initial_investment)+'</td><td>'+money(r.current_investment)+'</td><td>'+pc(r.ddi_reduction_pct)+'</td><td>'+pc(r.investment_reduction_pct)+'</td><td><div class="v293-bar"><span><i style="width:'+Math.max(0,Math.min(100,n(r.progress_pct)))+'%"></i></span><b>'+pc(r.progress_pct)+'</b></div></td><td><span class="v293-status '+cls+'">'+esc(r.status)+'</span></td></tr>'}).join('')||'<tr><td colspan="14">Sin modelos para esta selección</td></tr>'}
function details(d){return '<section class="v293-panel v293-detail"><div class="v293-tools"><div class="v293-tools-left"><span>Avance por ID · ordenado del peor al mejor</span><span class="v293-info">i</span></div><div class="v293-tools-right"><input id="v293Search" placeholder="Buscar ID o modelo…"><select id="v293DetailCat"><option>Todos</option>'+['Abrigador','Licencias','Básicos'].map(x=>'<option '+(S.catalog===x?'selected':'')+'>'+x+'</option>').join('')+'</select></div></div><div class="v293-detail-wrap"><table class="v293-table"><thead><tr><th>#</th><th class="left">ID Modelo</th><th class="left">Modelo / Descripción</th><th>Catálogo</th><th>Exist. inicial</th><th>Exist. actual</th><th>DDI inicial</th><th>DDI actual</th><th>Inversión inicial</th><th>Inversión actual</th><th>% Reducción DDI</th><th>% Reducción inversión</th><th>Avance</th><th>Estatus</th></tr></thead><tbody id="v293DetailBody">'+detailRows(d)+'</tbody></table></div><div class="v293-note">Capacidades aporta Existencia, DDI e Inversión. El listado queda fijado al inicio del mes y se ordena del peor al mejor avance.</div></section>'}
function summary(d){return '<div class="v293-top">'+components(d)+score(d)+ranking(d,false)+'</div><div class="v293-mid">'+targetSummary(d)+catalogSummary(d)+'</div>'+details(d)}
function body(d){if(S.view==='ranking')return ranking(d,true);if(S.view==='models'||['Abrigador','Licencias','Básicos'].includes(S.view))return catalogSummary(d)+details(d);return summary(d)}
function page(d){return '<div class="v293"><div class="v293-head"><div class="v293-title"><h2>Bonos</h2><div class="v293-sub">50% Venta vs Meta + 30% DDI por Cat + 20% Asistencia</div></div>'+filters(d)+'</div>'+tabs()+body(d)+'</div>'}
function bind(d){q('#v293Store')?.addEventListener('change',e=>{S.store=e.target.value;load()});q('#v293Month')?.addEventListener('change',e=>{S.month=e.target.value;load()});q('#v293Catalog')?.addEventListener('change',e=>{S.catalog=e.target.value;render()});qa('[data-v293-view]').forEach(b=>b.addEventListener('click',()=>{S.view=b.dataset.v293View;if(['Abrigador','Licencias','Básicos'].includes(S.view))S.catalog=S.view;render()}));qa('[data-v293-store]').forEach(tr=>tr.addEventListener('click',()=>{S.store=tr.dataset.v293Store;S.view='summary';load()}));q('#v293AttSave')?.addEventListener('click',saveAttendance);q('#v293Search')?.addEventListener('input',()=>{let b=q('#v293DetailBody');if(b)b.innerHTML=detailRows(S.data)});q('#v293DetailCat')?.addEventListener('change',e=>{S.catalog=e.target.value;let top=q('#v293Catalog');if(top)top.value=S.catalog;let b=q('#v293DetailBody');if(b)b.innerHTML=detailRows(S.data)})}
function render(){active();let h=q('#v293StandaloneHost');if(!h||!S.data)return;h.innerHTML=page(S.data);bind(S.data)}
async function saveAttendance(){let v=Number(q('#v293Att')?.value);if(!Number.isFinite(v)||v<0||v>100)return;let b=q('#v293AttSave');if(b){b.disabled=true;b.textContent='…'}try{await A('/api/operation/sales-bonus-v293/attendance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({month:S.month,store:S.store,attendance_pct:v})});await load()}catch(e){alert(e.message||e)}finally{if(b){b.disabled=false;b.textContent='Guardar'}}}
async function load(){let seq=++S.seq;S.busy=true;active();if(S.controller)try{S.controller.abort()}catch(_){};if(S.poll){clearTimeout(S.poll);S.poll=null}S.controller=new AbortController();let timer=setTimeout(()=>{try{S.controller.abort()}catch(_){}},20000);let h=q('#v293StandaloneHost');if(h&&!S.data)h.innerHTML='<div class="v293-empty">Cargando Bonos…</div>';else if(h&&S.data){let n=document.createElement('div');n.className='v293-source';n.style.padding='5px 8px';n.textContent='Actualizando periodo…';h.prepend(n)}try{let p=new URLSearchParams();if(S.month)p.set('month',S.month);if(S.store)p.set('store',S.store);let d=await A('/api/operation/sales-bonus-v293?'+p,{signal:S.controller.signal});if(seq!==S.seq)return;S.data=d;S.month=d.month;S.store=d.selected_store;if(!S.catalog)S.catalog='Todos';render();if(d.processing?.sales||d.processing?.capacity){S.poll=setTimeout(()=>{if(seq===S.seq)load()},3500)}}catch(e){if(seq!==S.seq)return;if(e?.name==='AbortError'){if(h)h.innerHTML='<div class="v293-empty">La consulta tardó demasiado. Intenta de nuevo; el sistema seguirá preparando la información.</div>'}else if(h)h.innerHTML='<div class="v293-empty">No fue posible cargar Bonos: '+esc(e.message||e)+'</div>'}finally{clearTimeout(timer);if(seq===S.seq)S.busy=false}}
function open(){active();load()}
function boot(){let x=menu();for(let b of [x.b,x.mb])if(b&&!b.dataset.v293Bound){b.dataset.v293Bound='1';b.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();open()},true)}let mn=q('#mobileMainNav');if(mn&&!mn.dataset.v294Obs){mn.dataset.v294Obs='1';new MutationObserver(()=>syncMobile()).observe(mn,{attributes:true,subtree:true,attributeFilter:['class','hidden']})}let app=q('#appView');if(app&&!app.dataset.v294BonusObs){app.dataset.v294BonusObs='1';new MutationObserver(()=>setTimeout(()=>{menu();syncMobile()},0)).observe(app,{attributes:true,attributeFilter:['class']})}let pr=q('#profileRole');if(pr&&!pr.dataset.v294BonusObs){pr.dataset.v294BonusObs='1';new MutationObserver(()=>setTimeout(()=>{menu();syncMobile()},0)).observe(pr,{childList:true,characterData:true,subtree:true})}syncMobile()}
document.addEventListener('DOMContentLoaded',()=>setTimeout(boot,250),{once:true});document.addEventListener('click',e=>{let b=e.target.closest?.('[data-main]');if(b&&b.dataset.main!=='bonuses'){document.body.removeAttribute('data-v293-standalone');setTimeout(()=>{menu();syncMobile()},80)}},true);[550,1300,2600].forEach(ms=>setTimeout(boot,ms));
})();</script>'''

    @m.app.middleware("http")
    async def v293_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v293-bonus-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v293-bonus-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-Bonus-Version"] = "V298-OPENING-CAPACITY"
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V293] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V293_SALES_BONUS = True
    print("[V298] Bonos: apertura mensual usa último corte de Capacidades previo al inicio del mes.", flush=True)
