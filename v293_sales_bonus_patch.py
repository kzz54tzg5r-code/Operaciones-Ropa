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
        entries = capacity_entries(month)
        if not entries:
            return None, {}, {}
        _d, _stamp, entry = entries[-1]
        frame = load_frame(entry)
        work = scope_frame(frame, stores)
        sales = sales_by_store(work)
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
                w["investment"] = pd.to_numeric(w.get("Inversión", 0), errors="coerce").fillna(0.0)
                agg = w.groupby(["store", "id_art"], sort=False, observed=True).agg(
                    ddi=("ddi", "max"), investment=("investment", "sum")
                ).reset_index()
                current = {(str(x["store"]), str(x["id_art"])): {"ddi": num(x["ddi"]), "investment": num(x["investment"])} for x in agg.to_dict("records")}
        try:
            del work, frame
            m._release_process_memory()
        except Exception:
            pass
        return entry, current, sales

    def build_store_metric(store, month, rows, current, sales, attendance, snapshot, current_entry):
        details = []
        by_cat = {c: [] for c in CATALOGS}
        for row in rows:
            ident = str(row.get("id_art") or "")
            cur = current.get((store, ident))
            has_current = current_entry is not None
            current_ddi = num(cur.get("ddi")) if cur is not None else (0.0 if has_current else num(row.get("initial_ddi")))
            current_inv = num(cur.get("investment")) if cur is not None else (0.0 if has_current else num(row.get("initial_investment")))
            initial_ddi = num(row.get("initial_ddi"))
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
        ddi_component = sum(component_values) / len(component_values) if component_values else 0.0
        goal = store_goal(store, month)
        actual_sales = num(sales.get(store))
        sales_pct = (actual_sales / goal * 100.0) if goal > 0 else 0.0
        att = attendance.get(store)
        attendance_pct = num(att.get("attendance_pct")) if att is not None else None
        score = min(max(sales_pct, 0.0), 100.0) * 0.50 + min(max(ddi_component, 0.0), 100.0) * 0.30
        if attendance_pct is not None:
            score += min(max(attendance_pct, 0.0), 100.0) * 0.20
        ready = bool(goal > 0 and current_entry is not None and attendance_pct is not None)
        snap = snapshot.get(store) or {}
        details.sort(key=lambda x: (x["progress_pct"], x["id_art"]))
        return {
            "store": store,
            "month": month,
            "period_label": period_label(month),
            "sales": {"actual": round(actual_sales, 2), "goal": round(goal, 2), "pct": round(sales_pct, 1)},
            "ddi": {"pct": round(ddi_component, 1), "catalogs": catalog_summary},
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
        ensure_snapshots(month, stores)
        targets = target_rows(month, stores)
        snapshots = snapshot_rows(month, stores)
        attendance = attendance_rows(month, stores)
        current_entry, current, sales = current_maps(month, stores, targets)
        by_store = defaultdict(list)
        for row in targets:
            by_store[str(row.get("store") or "")].append(row)
        metrics = [build_store_metric(s, month, by_store.get(s, []), current, sales, attendance, snapshots, current_entry) for s in stores]
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
         