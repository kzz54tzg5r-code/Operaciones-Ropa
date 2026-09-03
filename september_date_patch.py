"""Corrección de fechas de septiembre para Operaciones Ropa en Render.

El Excel real mezcla dos formatos: timestamps ISO en Resultados productividad
(`2026-09-02 19:30:27`) y encabezados latinos en hojas mensuales
(`01/09/2026`). Pandas interpreta el segundo como 9 de enero si no se indica
el orden día/mes. Este parche detecta ambos formatos explícitamente y, tras el
despliegue, reprocesa en segundo plano el Excel ya persistido para que el
usuario no tenga que volver a cargar 147 MB.
"""
from __future__ import annotations

import math
import re
import threading
import time
from datetime import datetime

PARSER_VERSION = 46


def install(module) -> None:
    if getattr(module, "_SEPTEMBER_DATE_PATCH", False):
        return

    def _safe_date_iso_fixed(value):
        try:
            numeric = float(value)
        except Exception:
            numeric = None

        if numeric is not None and math.isfinite(numeric) and 20000 <= numeric <= 100000:
            dt = module.pd.to_datetime(
                numeric, unit="D", origin="1899-12-30", errors="coerce"
            )
        else:
            dt = module.pd.NaT
            text = str(value or "").strip()
            if text:
                match_iso = re.match(
                    r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:\D|$)", text
                )
                if match_iso:
                    try:
                        dt = module.pd.Timestamp(
                            year=int(match_iso.group(1)),
                            month=int(match_iso.group(2)),
                            day=int(match_iso.group(3)),
                        )
                    except Exception:
                        dt = module.pd.NaT

                if module.pd.isna(dt):
                    match_latam = re.match(
                        r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:\D|$)", text
                    )
                    if match_latam:
                        try:
                            dt = module.pd.Timestamp(
                                year=int(match_latam.group(3)),
                                month=int(match_latam.group(2)),
                                day=int(match_latam.group(1)),
                            )
                        except Exception:
                            dt = module.pd.NaT

                if module.pd.isna(dt):
                    dt = module.pd.to_datetime(text, errors="coerce", dayfirst=True)

        if module.pd.isna(dt) and value is not None:
            text = module.normalize_col(value)
            weekdays = (
                "lunes", "martes", "miercoles", "jueves",
                "viernes", "sabado", "domingo",
            )
            for weekday in weekdays:
                text = re.sub(rf"^{weekday},?\s*", "", text)
            month_map = {
                "enero": "01", "febrero": "02", "marzo": "03",
                "abril": "04", "mayo": "05", "junio": "06",
                "julio": "07", "agosto": "08", "septiembre": "09",
                "setiembre": "09", "octubre": "10", "noviembre": "11",
                "diciembre": "12",
            }
            match_text = re.search(
                r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})\b", text
            )
            if match_text and match_text.group(2) in month_map:
                dt = module.pd.to_datetime(
                    f"{match_text.group(3)}-{month_map[match_text.group(2)]}-{int(match_text.group(1)):02d}",
                    errors="coerce",
                )

        if module.pd.isna(dt):
            return "", None, None, ""
        iso = dt.isocalendar()
        return (
            dt.date().isoformat(),
            int(iso.week),
            int(iso.year),
            dt.strftime("%Y-%m"),
        )

    module._safe_date_iso = _safe_date_iso_fixed
    module.OPERATIONS_PARSER_VERSION = max(
        int(getattr(module, "OPERATIONS_PARSER_VERSION", 0) or 0), PARSER_VERSION
    )

    @module.app.on_event("startup")
    def _schedule_existing_excel_reparse():
        """Reprocesa el archivo ya cargado sin bloquear el arranque de Render."""

        def worker():
            time.sleep(4)
            try:
                meta = dict(module.load_operations_meta() or {})
                current_version = int(meta.get("parser_version") or 0)
                if current_version >= PARSER_VERSION:
                    print(
                        f"[SEPTIEMBRE] Parser {current_version} ya vigente; no requiere reproceso.",
                        flush=True,
                    )
                    return

                raw_file = module.DATA_ROOT / "cambios_muertos_actual.xlsx"
                if not raw_file.exists():
                    print(
                        "[SEPTIEMBRE] No existe cambios_muertos_actual.xlsx; se aplicará la corrección en la próxima carga.",
                        flush=True,
                    )
                    return

                for _ in range(120):
                    lock = getattr(module, "_UPLOAD_JOB_LOCK", None)
                    active = getattr(module, "_ACTIVE_UPLOAD_JOBS", set())
                    if lock is None:
                        busy = bool(active)
                    else:
                        with lock:
                            busy = bool(active)
                    if not busy:
                        break
                    time.sleep(5)
                else:
                    print(
                        "[SEPTIEMBRE] Hay una carga activa; el reproceso automático se pospone al siguiente reinicio.",
                        flush=True,
                    )
                    return

                print(
                    f"[SEPTIEMBRE] Reprocesando {raw_file.name} con fechas dd/mm/yyyy e ISO explícitas...",
                    flush=True,
                )
                payload = module._parse_operations_external(raw_file, "septiembre_v46")
                now = datetime.now().isoformat(timespec="seconds")

                uploaded_by = "Corrección automática septiembre"
                try:
                    with module.db() as con:
                        row = con.execute(
                            "SELECT uploaded_by FROM upload_history "
                            "WHERE module='Cambios y Muertos' ORDER BY id DESC LIMIT 1"
                        ).fetchone()
                    if row and row["uploaded_by"]:
                        uploaded_by = str(row["uploaded_by"])
                except Exception:
                    pass

                payload["parser_version"] = PARSER_VERSION
                payload["source_file"] = meta.get("source_file") or raw_file.name
                payload["uploaded_by"] = uploaded_by
                payload["uploaded_at"] = meta.get("uploaded_at") or now
                payload["migration_at"] = now

                september_rows = [
                    row for row in (payload.get("recovery_fifo") or [])
                    if str(row.get("date") or "").startswith("2026-09")
                ]
                september_dev = sum(float(row.get("dev_pzs") or 0) for row in september_rows)
                september_dates = sorted({
                    str(row.get("date") or "") for row in september_rows if row.get("date")
                })
                if not september_rows or september_dev <= 0:
                    raise ValueError(
                        "El reproceso no detectó Dev Pzs de septiembre; se conserva la base anterior."
                    )

                tmp = module.DATA_ROOT / "operaciones_ropa_operativo.septiembre_v46.tmp.json"
                module._write_json_stream(tmp, payload)
                tmp.replace(module.OPS_FILE)
                module._clear_operations_caches(clear_meta_file=True)
                try:
                    module.OPS_RECOVERY_CACHE_FILE.unlink(missing_ok=True)
                except Exception:
                    pass

                try:
                    stamp = module._ops_source_stamp()
                    new_meta = module._build_operations_meta(payload, stamp)
                    module._write_json_stream(module.OPS_META_CACHE_FILE, new_meta)
                    module._OPS_META_CACHE["stamp"] = stamp
                    module._OPS_META_CACHE["data"] = new_meta
                except Exception:
                    pass

                print(
                    "[SEPTIEMBRE] CORRECCIÓN PUBLICADA: "
                    f"fechas={september_dates[:10]} dev_pzs={september_dev:g} "
                    f"fifo_rows={len(september_rows)} parser={PARSER_VERSION}",
                    flush=True,
                )
            except Exception as exc:
                print(
                    f"[SEPTIEMBRE] ERROR: {type(exc).__name__}: {exc}",
                    flush=True,
                )
                try:
                    module._release_process_memory()
                except Exception:
                    pass

        threading.Thread(
            target=worker,
            daemon=True,
            name="reparse-septiembre-v46",
        ).start()

    module._SEPTEMBER_DATE_PATCH = True
