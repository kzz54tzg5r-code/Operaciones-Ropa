"""V169 · Periodos operativos unificados.

El selector Día/Semanal/Mensual/Anual no debe quedar limitado a la hoja
Resultados de productividad. Centro Operativo también consume devoluciones /
conversión de las hojas mensuales; por eso los periodos disponibles se forman
con la unión de filas operativas + recovery_fifo + commercial_daily.
"""
from __future__ import annotations

from datetime import datetime


def install(m):
    if getattr(m, "_V169_PERIOD_META", False):
        return

    original_build = m._build_operations_meta

    def build_operations_meta_v169(data: dict, stamp: int = 0):
        meta = original_build(data, stamp)
        sources = []
        for key in ("rows", "recovery_fifo", "commercial_daily"):
            value = data.get(key)
            if isinstance(value, list):
                sources.extend(value)

        dates = set(str(x) for x in (meta.get("available_dates") or []) if str(x))
        weeks = set(str(x) for x in (meta.get("available_weeks") or []) if str(x))
        months = set(str(x) for x in (meta.get("available_months") or []) if str(x))

        stores = set(str(x).strip() for x in (meta.get("stores_detected") or []) if str(x).strip())
        for r in sources:
            if not isinstance(r, dict):
                continue
            ds = str(r.get("date") or "")[:10]
            if ds:
                try:
                    d = datetime.strptime(ds, "%Y-%m-%d").date()
                    dates.add(d.isoformat())
                    iso = d.isocalendar()
                    weeks.add(f"{iso.year}-W{iso.week:02d}")
                    months.add(d.strftime("%Y-%m"))
                except Exception:
                    pass
            else:
                y = r.get("year_iso")
                w = r.get("week_iso")
                if y and w:
                    try:
                        weeks.add(f"{int(y)}-W{int(w):02d}")
                    except Exception:
                        pass
                mo = str(r.get("month") or "")
                if len(mo) >= 7:
                    months.add(mo[:7])
            st = str(r.get("store") or "").strip()
            if st:
                stores.add(st)

        meta["available_dates"] = sorted(dates)
        meta["available_weeks"] = sorted(weeks)
        meta["available_months"] = sorted(months)
        meta["stores_detected"] = sorted(stores)
        meta["period_sources_v169"] = {
            "operational_rows": len(data.get("rows") or []),
            "recovery_fifo": len(data.get("recovery_fifo") or []),
            "commercial_daily": len(data.get("commercial_daily") or []),
            "last_date": max(dates) if dates else "",
        }
        return meta

    m._build_operations_meta = build_operations_meta_v169

    # La caché anterior puede seguir marcando 13-sep aunque el archivo ya tenga
    # movimientos posteriores en recovery/commercial. Se invalida sólo el índice
    # liviano; nunca se toca la base operativa publicada.
    try:
        m._OPS_META_CACHE["stamp"] = None
        m._OPS_META_CACHE["data"] = None
        m.OPS_META_CACHE_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    m._V169_PERIOD_META = True
    print("[V169] periodos operativos unificados desde operación + conversión.", flush=True)
