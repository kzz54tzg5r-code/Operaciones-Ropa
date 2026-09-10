"""Complemento V109: repara una sola vez los PDF de ventas ya persistidos.

Después de instalar el parser V109, reprocesa en segundo plano únicamente las
entradas antiguas con año/mes válido y persiste totales/tienda. Así el reporte
Macro queda listo sin esperar al primer clic del usuario.
"""
from __future__ import annotations

from pathlib import Path
import threading
import time


def install(m):
    if getattr(m, "_V109_SALES_REPAIR_STARTUP", False):
        return

    @m.app.on_event("startup")
    def _schedule_sales_repair():
        def worker():
            time.sleep(7)
            try:
                entries = list((m.load_manifest() or {}).get("sales") or [])
                pending = [
                    dict(e) for e in entries
                    if Path(str(e.get("name") or e.get("path") or "")).suffix.lower() == ".pdf"
                    and int(e.get("year") or 0) > 0
                    and int(e.get("month") or 0) in range(1, 13)
                    and int(e.get("parser_version") or 0) < 109
                ]
                repaired = detected = 0
                for item in pending:
                    try:
                        path = m.resolve_entry_path(item)
                        if not path.exists():
                            print(f"[V109-REPAIR] archivo no disponible: {item.get('name','')}", flush=True)
                            continue
                        parsed = m.parse_sales_pdf(path, int(item.get("year") or 0), int(item.get("month") or 0))
                        changes = {
                            "status": parsed.get("status", ""),
                            "store": parsed.get("store", ""),
                            "rows": parsed.get("rows", 0),
                            "stores": parsed.get("stores", 0),
                            "pages": parsed.get("pages", 0),
                            "total_pieces": parsed.get("total_pieces", 0),
                            "total_sales": parsed.get("total_sales", 0),
                            "parser_version": 109,
                            "source_line": parsed.get("source_line", ""),
                        }
                        m.update_entry("sales", str(item.get("id") or ""), **changes)
                        try:
                            m.save_sales_pdf_snapshot(str(item.get("id") or ""), parsed)
                        except Exception:
                            pass
                        repaired += 1
                        if float(parsed.get("total_sales") or 0) > 0:
                            detected += 1
                        print(
                            f"[V109-REPAIR] {item.get('name','')} · {item.get('year')}-{int(item.get('month') or 0):02d} · "
                            f"{parsed.get('store') or 'Compañía'} · {parsed.get('status')} · venta={float(parsed.get('total_sales') or 0):.2f}",
                            flush=True,
                        )
                    except Exception as exc:
                        print(f"[V109-REPAIR] error {item.get('name','')}: {type(exc).__name__}: {exc}", flush=True)
                print(f"[V109-REPAIR] terminado · reparados={repaired} · venta detectada={detected}/{len(pending)}", flush=True)
            except Exception as exc:
                print(f"[V109-REPAIR] ERROR general: {type(exc).__name__}: {exc}", flush=True)
        threading.Thread(target=worker, daemon=True, name="v109-sales-history-repair").start()

    m._V109_SALES_REPAIR_STARTUP = True
    print("[V109-REPAIR] reparación de historial programada.", flush=True)
