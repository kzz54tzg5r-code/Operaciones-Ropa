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

    def capacity_entries(month):
        out = []
        for entry in list(m._capacity_processed_entries() or []):
            try:
                d = m._capacity_report_date(entry)
            except Exception:
                continue
            if f"{d.year:04d}-{d.month:02d}" == month:
                out.append((d, str(entry.get("uploaded_at") or entry.get("created_at") or ""), entry))
        out.sort(key=lambda x: (x[0], x[1]))
        return out

    def period_for_entry(entry):
        if not entry:
            return ""
        d = m._capacity_report_date(entry)
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    def load_frame(entry):
        if not entry:
            return pd.DataFrame()
        try:
            frame = m._load_capacity_cache(entry)
            if frame is not None and not frame.empty:
                return frame
        except Exception:
            pass
        try:
            path = m.resolve_entry_path(entry)
            frame = m.read_capacity_file(path)
            return m._prepare_capacity_frame(frame)
        except Exception as exc:
            print(f"[V293] No se pudo leer capacidad {entry.get('id')}: {type(exc).__name__}: {exc}", flush=True)
            return pd.DataFrame()

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
            "DDI", "Inversión", "Venta $ mes", "Venta $", "Venta $ 7"
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
            return pd.DataFrame(columns=["store", "id_art", "model", "catalog", "ddi", "investment"])
        w = work.copy()
        w["store"] = w.get("Tienda", "").astype(str).map(lambda x: canon_store(x, all_stores()))
        w["id_art"] = w["ID_ART"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        w = w[~w["id_art"].isin(["", "nan", "None"])]
        if w.empty:
            return pd.DataFrame(columns=["store", "id_art", "model", "catalog", "ddi", "investment"])
        w["catalog"] = classify_catalog(w)
        w = w[w["catalog"].isin(CATALOGS)]
        if w.empty:
            return pd.DataFrame(columns=["store", "id_art", "model", "catalog", "ddi", "investment"])
        w["ddi"] = pd.to_numeric(w.get("DDI", 0), errors="coerce").replace([math.inf, -math.inf], pd.NA).fillna(0.0)
        w["investment"] = pd.to_numeric(w.get("Inversión", 0), errors="coerce").fillna(0.0)
        w["model"] = w.get("Modelo", w["id_art"]).fillna("").astype(str).str.strip()
        grouped = w.groupby(["store", "id_art", "catalog"], sort=False, observed=True).agg(
            model=("model", "first"),
            ddi=("ddi", "max"),
            investment=("investment", "sum"),
        ).reset_index()
        return grouped

    def sales_by_store(work):
        if work.empty or "ID_ART" not in work.columns:
            return {}
        w = work.copy()
        w["store"] = w.get("Tienda", "").astype(str).map(lambda x: canon_store(x, all_stores()))
        w["id_art"] = w["ID_ART"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        w = w[~w["id_art"].isin(["", "nan", "None"])]
        if w.empty:
            return {}
        preferred = pd.to_numeric(w.get("Venta $ mes", 0), errors="coerce").fillna(0.0)
        fallback = pd.to_numeric(w.get("Venta $", w.get("Venta $ 7", 0)), errors="coerce").fillna(0.0)
        w["sales_value"] = preferred.where(preferred > 0, fallback)
        per_id = w.groupby(["store", "id_art"], sort=False, observed=True)["sales_value"].max().reset_index()
        totals = per_id.groupby("store", sort=False)["sales_value"].sum()
        return {str(k): float(v or 0) for k, v in totals.items()}

    def ensure_snapshots(month, stores):
        stores = [s for s in stores if s]
        if not stores:
            return {"entry": None, "created": 0}
        with m.db() as con:
            existing = {str(r["store"]) for r in con.execute(
                "SELECT store FROM sales_bonus_snapshot_v293 WHERE month=?", (month,)
            ).fetchall()}
        missing = [s for s in stores if s not in existing]
        if not missing:
            entries = capacity_entries(month)
            return {"entry": entries[0][2] if entries else None, "created": 0}
        entries = capacity_entries(month)
        if not entries:
            return {"entry": None, "created": 0}
        source_date, _stamp, entry = entries[0]
        frame = load_frame(entry)
        work = scope_frame(frame, missing)
        models = aggregate_models(work)
        created = 0
        now = datetime.now(MX).isoformat(timespec="seconds")
        source_period = period_for_entry(entry)
        by_store = {s: pd.DataFrame() for s in missing}
        if not models.empty:
            for store, group in models.groupby("store", sort=False):
                by_store[str(store)] = group
        with m.db() as con:
            for store in missing:
                g = by_store.get(store)
                selected = pd.DataFrame()
                if g is not None and not g.empty:
                    g = g.copy()
                    g["avg_investment"] = g.groupby("catalog", observed=True)["investment"].transform("mean")
                    selected = g[(g["ddi"] > 90.0) & (g["investment"] > g["avg_investment"])].copy()
                    for row in selected.to_dict("records"):
                        con.execute("""
                            INSERT OR IGNORE INTO sales_bonus_targets_v293(
                                month,store,id_art,catalog,model,initial_ddi,initial_investment,avg_investment,
                                source_period,source_date,fixed_at
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            month, store, str(row.get("id_art") or ""), str(row.get("catalog") or ""),
                            str(row.get("model") or row.get("id_art") or ""), num(row.get("ddi")), num(row.get("investment")),
                            num(row.get("avg_investment")), source_period, source_date.isoformat(), now,
                        ))
                con.execute("""
                    INSERT OR IGNORE INTO sales_bonus_snapshot_v293(month,store,source_period,source_date,fixed_at,model_count)
                    VALUES(?,?,?,?,?,?)
                """, (month, store, source_period, source_date.isoformat(), now, int(len(selected))))
                created += int(len(selected))
        try:
            del work, models, frame
            m._release_process_memory()
        except Exception:
            pass
        return {"entry": entry, "created": created}

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
        entries = capacity_entries(month