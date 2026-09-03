"""Diagnóstico temporal y ligero del contenido operativo publicado."""
from __future__ import annotations

import collections
import threading
import time


def install(module) -> None:
    if getattr(module, "_OPERATIONS_DIAGNOSTIC_PATCH", False):
        return

    @module.app.on_event("startup")
    def _schedule_operations_diagnostic():
        def worker():
            time.sleep(8)
            try:
                data = module.load_ops() or {}
                rows = data.get("rows") or []
                fifo = data.get("recovery_fifo") or []
                dates = sorted({str(r.get("date") or "") for r in rows if r.get("date")})
                print(
                    f"[DIAG-OPS] parser={data.get('parser_version')} rows={len(rows)} "
                    f"min_date={(dates[0] if dates else '')} max_date={(dates[-1] if dates else '')} "
                    f"latest={dates[-5:]}", flush=True,
                )
                for date in dates[-3:]:
                    scoped = [r for r in rows if str(r.get("date") or "") == date]
                    activities = collections.Counter()
                    motives = collections.Counter()
                    stores = collections.Counter()
                    recorridos = 0.0
                    for row in scoped:
                        pz = float(row.get("pieces") or 0)
                        activities[str(row.get("activity") or "")] += pz
                        motives[str(row.get("motive_class") or "")] += pz
                        stores[str(row.get("store") or "")] += pz
                        recorridos += float(row.get("recorridos") or 0)
                    print(
                        f"[DIAG-OPS] date={date} count={len(scoped)} "
                        f"activities={dict(activities)} motives={dict(motives)} "
                        f"stores={dict(stores)} recorridos_raw={recorridos}", flush=True,
                    )
                fifo_dates = sorted({str(r.get("date") or "") for r in fifo if r.get("date")})
                for date in fifo_dates[-3:]:
                    scoped = [r for r in fifo if str(r.get("date") or "") == date]
                    dev = sum(float(r.get("dev_pzs") or 0) for r in scoped)
                    rec = sum(float(r.get("converted_pieces") or 0) for r in scoped)
                    print(
                        f"[DIAG-FIFO] date={date} rows={len(scoped)} dev={dev:g} recovered={rec:g}",
                        flush=True,
                    )
            except Exception as exc:
                print(f"[DIAG-OPS] ERROR {type(exc).__name__}: {exc}", flush=True)

        threading.Thread(target=worker, daemon=True, name="operations-diagnostic").start()

    module._OPERATIONS_DIAGNOSTIC_PATCH = True
