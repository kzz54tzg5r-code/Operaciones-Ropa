"""V368: reprocesamiento controlado de DEV desde el Excel original persistente.

No dispara análisis costosos durante las consultas ni al iniciar Render.
POST exclusivo admin/superadmin. Conserva versión anterior como hardlink,
y publica atómicamente sólo si hay DEV adicionales en el periodo solicitado.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
import json
import math
import os
import shutil
import uuid

from fastapi import HTTPException, Request

_GUARD = Lock()
_RUNNING = {"job": "", "thread": None}
_WORKER_ID = uuid.uuid4().hex


def _period_matches(row, mode, value):
    ds = str(row.get("date") or "")[:10]
    if not ds:
        return False
    if mode == "day":
        return ds == value
    if mode == "week":
        try:
            from datetime import date
            iso = date.fromisoformat(ds).isocalendar()
            return f"{iso.year}-W{iso.week:02d}" == value
        except ValueError:
            return False
    if mode == "month":
        return ds.startswith(value)
    if mode == "year":
        return ds.startswith(value)
    return False


def _period_dev(rows, mode, value):
    total = 0.0
    for row in rows or ():
        if not isinstance(row, dict) or not _period_matches(row, mode, value):
            continue
        try:
            value_num = float(row.get("dev_pzs") or 0)
            if math.isfinite(value_num) and value_num > 0:
                total += value_num
        except (ValueError, TypeError, OverflowError):
            pass
    return total


def install(m):
    if getattr(m, "_V368_REBUILD_DEV_INSTALLED", False):
        return

    status_file = m.DATA_ROOT / "recovery_rebuild_status_v368.json"
    raw_excel = m.DATA_ROOT / "cambios_muertos_actual.xlsx"

    def write_status(job_id, state, message, **extra):
        payload = {
            "job_id": job_id, "status": state, "message": message,
            "worker_id": _WORKER_ID,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            **extra,
        }
        temp = status_file.with_name(f"{status_file.name}.{job_id}.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temp.replace(status_file)

    def read_status():
        try:
            value = json.loads(status_file.read_text(encoding="utf-8"))
            if value.get("worker_id") != _WORKER_ID and value.get("status") in ("queued", "processing", "publishing"):
                value.update(status="interrupted", message="Render reinició el proceso. La base anterior se conservó.")
            return value
        except (OSError, ValueError):
            return {"status": "idle", "message": "Sin reprocesamiento reciente"}

    def work(job_id, mode, period_value):
        temporary = m.DATA_ROOT / f"recovery_rebuild_{job_id}.tmp.json"
        try:
            write_status(job_id, "processing", "Leyendo el Excel vigente; los reportes siguen disponibles.")
            # No alterar ni mover el Excel fuente: se necesita para otros procesos.
            before_raw = (raw_excel.stat().st_size, raw_excel.stat().st_mtime_ns)
            before_ops_stamp = m._ops_source_stamp()
            source = m.load_ops()
            before_op_rows = len(source.get("rows") or ())
            # Reutiliza el listado cacheado: duplicarlo agotaría la RAM de Render.
            previous_fifo = m._get_recovery_fifo_rows(source) or ()
            previous_dev = _period_dev(previous_fifo, mode, period_value)
            metadata = {
                "source_file": source.get("source_file") or raw_excel.name,
                "uploaded_at": source.get("uploaded_at"),
                "uploaded_by": source.get("uploaded_by"),
            }
            # External parser explicitly frees the old large in-memory cache.
            del source, previous_fifo
            updated = m._parse_operations_external(raw_excel, job_id)
            after_raw = (raw_excel.stat().st_size, raw_excel.stat().st_mtime_ns)
            if before_raw != after_raw or m._ops_source_stamp() != before_ops_stamp:
                raise RuntimeError("Cambió el archivo publicado durante la revisión. Reintenta con el corte vigente.")
            if not updated.get("monthly_sheets"):
                raise RuntimeError("El Excel no contiene hojas mensuales reconocibles. Se conservó la base anterior.")
            if not updated.get("recovery_fifo"):
                failures = "; ".join(str(x) for x in (updated.get("errors") or [])[:2])
                raise RuntimeError("No se pudieron extraer lotes diarios DEV del Excel. " + failures[:250])
            count = len(updated.get("rows") or ())
            if not count or (before_op_rows > 0 and count < before_op_rows * 0.95):
                raise RuntimeError("La lectura nueva perdió registros operativos; no se sustituyó la base anterior.")
            new_dev = _period_dev(updated["recovery_fifo"], mode, period_value)
            if new_dev <= previous_dev:
                raise RuntimeError(
                    f"No se encontraron devoluciones adicionales para {period_value} "
                    f"(vigente {previous_dev:,.0f}; reprocesado {new_dev:,.0f}). "
                    "Revisa las columnas diarias del Excel original."
                )
            if shutil.disk_usage(m.DATA_ROOT).free < 64 * 1024 * 1024:
                raise RuntimeError("No hay margen suficiente en el disco para publicar sin riesgo.")

            for key, value in metadata.items():
                if value is not None:
                    updated[key] = value
            updated["recovery_rebuilt_at"] = datetime.now().isoformat(timespec="seconds")
            updated["recovery_rebuilt_period"] = f"{mode}:{period_value}"
            write_status(
                job_id, "publishing", "DEV verificadas; guardando la versión reparada.",
                previous_dev=previous_dev, rebuilt_dev=new_dev
            )
            m._write_json_stream(temporary, updated)
            if before_raw != (raw_excel.stat().st_size, raw_excel.stat().st_mtime_ns) or m._ops_source_stamp() != before_ops_stamp:
                raise RuntimeError("La versión cambió mientras se guardaba. La base actual se conserva.")
            history = m.OPERATIONS_HISTORY_DIR
            history.mkdir(parents=True, exist_ok=True)
            backup = history / f"previo_recuperacion_dev_{job_id}.json"
            # Un hardlink resguarda los bytes exactos originales sin duplicar RAM.
            os.link(m.OPS_FILE, backup)
            temporary.replace(m.OPS_FILE)
            m._clear_operations_caches(clear_meta_file=True)
            write_status(
                job_id, "completed", "Devoluciones recuperadas y publicadas.",
                previous_dev=previous_dev, rebuilt_dev=new_dev,
                period_type=mode, period_value=period_value,
                backup_saved=True
            )
            print(f"[V368] Reparación DEV {mode}:{period_value}: {previous_dev:.0f} -> {new_dev:.0f}", flush=True)
        except Exception as exc:
            write_status(job_id, "failed", str(exc)[:400])
            print(f"[V368] Base anterior conservada; fallo DEV: {type(exc).__name__}: {exc}", flush=True)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            with _GUARD:
                if _RUNNING["job"] == job_id:
                    _RUNNING["job"] = ""
                    _RUNNING["thread"] = None

    @m.app.post("/api/operations/rebuild-dev-v368", status_code=202)
    async def rebuild_dev(request: Request):
        m.require_user(request, ("superadmin", "admin"))
        params = await request.json()
        if not isinstance(params, dict):
            raise HTTPException(400, "Filtros inválidos")
        mode = str(params.get("period_type") or "").lower()
        value = str(params.get("period_value") or "")
        import re
        patterns = {
            "day": r"\d{4}-\d{2}-\d{2}",
            "week": r"\d{4}-W\d{2}",
            "month": r"\d{4}-\d{2}",
            "year": r"\d{4}",
        }
        if mode not in patterns or not re.fullmatch(patterns[mode], value):
            raise HTTPException(400, "Selecciona un día, semana, mes o año válido")
        if not raw_excel.is_file():
            raise HTTPException(404, "No existe el Excel original en el disco persistente. No se alteró la base.")
        with _GUARD:
            old = _RUNNING["thread"]
            if old is not None and old.is_alive():
                raise HTTPException(409, "Ya se está reprocesando una base. Consulta su estado.")
            job_id = uuid.uuid4().hex[:16]
            write_status(job_id, "queued", "Reprocesamiento DEV preparado")
            t = Thread(target=work, args=(job_id, mode, value),
                       daemon=True, name="rebuild-dev-v368")
            _RUNNING.update(job=job_id, thread=t)
            t.start()
        return {"ok": True, "job_id": job_id, "status": "queued"}

    @m.app.get("/api/operations/rebuild-dev-v368")
    def rebuild_dev_status(request: Request):
        m.require_user(request, ("superadmin", "admin"))
        return read_status()

    m._V368_REBUILD_DEV_INSTALLED = True
    print("[V368] Reparación segura DEV con validación antes de publicar.", flush=True)
