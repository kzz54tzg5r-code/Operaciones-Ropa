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
     