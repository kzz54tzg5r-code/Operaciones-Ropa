"""V321 · Carga mensual del corte inicial de Bonos + ajuste responsive específico.

El corte inicial queda asociado explícitamente al periodo elegido sin sustituir
el histórico general de Capacidades. Los seis bonos y sus cálculos se conservan.
"""
from __future__ import annotations

import asyncio
import errno
import hashlib
import re
import secrets
import shutil
import tempfile
from datetime import datetime
from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

ADMIN = ("superadmin", "admin")


def _valid_month(value: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise HTTPException(400, "Selecciona un mes válido.")
    year, month = (int(x) for x in value.split("-"))
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        raise HTTPException(400, "Selecciona un mes válido.")
    return value


def install(m):
    if getattr(m, "_V321_BONUS_INITIAL_UPLOAD_RESPONSIVE", False):
        return

    @m.app.get("/api/bonuses/initial-capacity")
    def list_bonus_initial_capacity(request: Request, month: str = ""):
        m.require_user(request, ADMIN)
        month = _valid_month(month) if month else ""
        manifest = m.load_manifest()
        cuts = manifest.get("bonus_initial_cuts") or {}
        all_capacity_entries = list(manifest.get("capacities") or []) + list(manifest.get("bonus_initial_capacity_entries") or [])
        entries = {
            str(x.get("id") or ""): dict(x)
            for x in all_capacity_entries
            if isinstance(x, dict)
        }
        items = []
        for period, value in sorted(cuts.items(), key=lambda item: str(item[0]), reverse=True):
            entry_id = value.get("entry_id") if isinstance(value, dict) else value
            entry = entries.get(str(entry_id or ""), {})
            items.append({
                "month": str(period),
                "entry_id": str(entry_id or ""),
                "name": str(entry.get("name") or "Archivo no encontrado"),
                "status": str(entry.get("status") or "Archivo no encontrado"),
                "report_date": str(entry.get("report_date") or ""),
                "uploaded_at": str(entry.get("uploaded_at") or ""),
                "rows": entry.get("rows"),
                "stores_count": len(entry.get("stores") or []),
                "error": str(entry.get("error") or ""),
            })
        selected = next((x for x in items if x["month"] == month), None)
        return {"items": items, "selected": selected, "month": month}

    def _run_bonus_initial_cut_job(job_id: str, entry: dict, filename: str, month: str, username: str) -> None:
        with m._UPLOAD_JOB_LOCK:
            if job_id in m._ACTIVE_UPLOAD_JOBS:
                return
            m._ACTIVE_UPLOAD_JOBS.add(job_id)
        try:
            m._update_upload_job(
                job_id, status="processing", progress=20,
                message=f"Procesando el corte inicial de {month}. La pantalla seguirá disponible.",
                started_at=datetime.now().isoformat(timespec="seconds"),
            )
            result = m._process_capacity_entry(entry, filename)
            if not result.get("ok"):
                raise ValueError(str(result.get("message") or "No se pudo procesar el Excel."))

            manifest = m.load_manifest()
            entry_id = str(entry.get("id") or "")
            processed = next(
                (dict(x) for x in (manifest.get("capacities") or [])
                 if str(x.get("id") or "") == entry_id
                 and str(x.get("status") or "").lower() == "procesado"),
                None,
            )
            if not processed:
                processed = next(
                    (dict(x) for x in (manifest.get("bonus_initial_capacity_entries") or [])
                     if str(x.get("id") or "") == entry_id
                     and str(x.get("status") or "").lower() == "procesado"),
                    None,
                )
            if not processed:
                raise RuntimeError("El Excel terminó sin quedar registrado como procesado; no se asignó al mes.")

            # Una fuente nueva queda separada del catálogo comercial normal.
            # Si ya existía como Capacidades comercial procesada, se conserva su registro.
            if not entry.get("duplicate"):
                source_path = m.resolve_entry_path(processed)
                target_dir = m.Path(m.COMMERCIAL_DATA_ROOT) / "bonus_initial_capacity"
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / (
                    str(processed.get("id") or "initial") + "_" +
                    m.Path(processed.get("name") or filename).name
                )
                try:
                    if source_path.exists() and source_path.resolve() != target_path.resolve():
                        m.shutil.move(str(source_path), str(target_path))
                    if not target_path.exists():
                        raise FileNotFoundError("No se pudo mover el Excel al histórico aislado de Bonos.")
                except Exception as exc:
                    raise RuntimeError(f"No se pudo aislar el corte inicial: {str(exc)[:250]}") from exc

                processed["path"] = str(target_path.relative_to(m.COMMERCIAL_DATA_ROOT))
                manifest["capacities"] = [
                    dict(x) for x in (manifest.get("capacities") or [])
                    if str(x.get("id") or "") != entry_id
                ]
                bonus_entries = manifest.setdefault("bonus_initial_capacity_entries", [])
                existing_index = next(
                    (i for i, x in enumerate(bonus_entries) if str(x.get("id") or "") == entry_id),
                    None,
                )
                processed["bonus_initial_only"] = True
                if existing_index is None:
                    bonus_entries.append(processed)
                else:
                    updated_entry = dict(bonus_entries[existing_index])
                    updated_entry.update(processed)
                    bonus_entries[existing_index] = updated_entry
                    processed = updated_entry

            cuts = manifest.setdefault("bonus_initial_cuts", {})
            previous = cuts.get(month)
            cuts[month] = entry_id
            m.save_manifest(manifest)

            payload = {
                "ok": True,
                "month": month,
                "entry_id": entry_id,
                "file": str(processed.get("name") or filename),
                "report_date": str(processed.get("report_date") or ""),
                "rows": result.get("rows", processed.get("rows")),
                "stores": result.get("stores", len(processed.get("stores") or [])),
                "replaced_previous": bool(previous and str(previous) != entry_id),
                "message": "Corte inicial procesado y asociado al periodo seleccionado.",
            }
            m._finish_upload_job(job_id, payload)
            print(
                f"[V321] Corte inicial de Bonos asignado: mes={month} archivo={payload['file']} usuario={username}",
                flush=True,
            )
        except Exception as exc:
            m._update_upload_job(
                job_id, status="error", progress=100,
                message="No se pudo procesar el corte inicial. La asignación anterior del mes se conserva.",
                error=f"{type(exc).__name__}: {exc}",
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )
            print(f"[V321] Error en corte inicial: {type(exc).__name__}: {exc}", flush=True)
        finally:
            with m._UPLOAD_JOB_LOCK:
                m._ACTIVE_UPLOAD_JOBS.discard(job_id)

    # web_app.py usa este registro para poder reanudar la carga si Railway reinicia.
    m._run_bonus_initial_cut_job = _run_bonus_initial_cut_job

    @m.app.post("/api/bonuses/initial-capacity", status_code=202)
    async def upload_bonus_initial_capacity(
        request: Request,
        month: str = Form(...),
        file: UploadFile = File(...),
    ):
        actor = m.require_user(request, ADMIN)
        month = _valid_month(month)
        filename = file.filename or "capacidades_inicial.xlsx"
        suffix = m.Path(filename).suffix.lower()
        if suffix not in (".xlsx", ".xls"):
            raise HTTPException(400, "Selecciona un archivo Excel .xlsx o .xls.")
        # Evitar un segundo archivo de 56 MB dentro del volumen persistente:
        # el original se conserva en /data/commercial/capacidades.
        stage_path = m.Path(tempfile.gettempdir()) / f"bonus_initial_{secrets.token_hex(12)}{suffix}"
        try:
            size = await m._save_upload_stream(file, stage_path)
            if not size:
                raise HTTPException(400, "El archivo está vacío.")

            # Verificar espacio antes de copiar al volumen y crear el caché
            # normalizado. En un volumen lleno es mejor responder 507 que 500.
            free = shutil.disk_usage(m.COMMERCIAL_DATA_ROOT).free

            # Si la misma fuente ya está procesada y su caché existe, no
            # necesitará otro archivo de 56 MB para un nuevo corte mensual.
            def existing_processed_source():
                digest = hashlib.sha256()
                with stage_path.open("rb") as stream:
                    for part in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(part)
                manifest = m.load_manifest()
                entries = list(manifest.get("capacities") or []) + list(
                    manifest.get("bonus_initial_capacity_entries") or []
                )
                for candidate in entries:
                    if candidate.get("sha256") != digest.hexdigest():
                        continue
                    if str(candidate.get("status") or "").lower() != "procesado":
                        continue
                    if not m.resolve_entry_path(candidate).is_file():
                        continue
                    relative = str(candidate.get("cache_file") or "").strip()
                    cache = ((m.DATA_ROOT / relative) if relative else
                             m._capacity_cache_path(str(candidate.get("id") or "")))
                    if cache.is_file():
                        return True
                return False

            already_cached = await asyncio.to_thread(existing_processed_source)
            minimum_free = (4 * 1024 * 1024 if already_cached
                            else size + 64 * 1024 * 1024)
            if free < minimum_free:
                raise HTTPException(
                    status_code=507,
                    detail=(
                        "El volumen de Railway no tiene espacio para procesar "
                        "este nuevo corte inicial. "
                        f"Disponibles: {free // (1024 * 1024)} MB; "
                        f"necesarios al menos {minimum_free // (1024 * 1024)} MB. "
                        "La aplicación conserva los históricos sin borrarlos."
                    ),
                )
            entry = await asyncio.to_thread(m._save_capacity_source_path, stage_path, filename, True)
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                raise HTTPException(
                    status_code=507,
                    detail=(
                        "El almacenamiento del servidor está lleno. "
                        "Amplía el volumen en Railway sin borrar los históricos."
                    ),
                ) from exc
            raise
        finally:
            try:
                stage_path.unlink(missing_ok=True)
            except Exception:
                pass

        source_path = m.resolve_entry_path(entry)
        if not source_path.exists():
            raise HTTPException(409, "El archivo recibido no quedó disponible en el almacenamiento persistente.")

        job = m._create_upload_job(
            "bonus_initial_capacity", filename, source_path, str(actor.get("username") or "admin")
        )
        m._update_upload_job(
            job["id"], progress=10,
            message=f"Corte inicial recibido; mes={month}. Preparando procesamiento.",
            result_json=m.json.dumps(
                {"month": month, "entry_id": str(entry.get("id") or "")},
                ensure_ascii=False,
            ),
        )
        m.threading.Thread(
            target=_run_bonus_initial_cut_job,
            args=(job["id"], entry, filename, month, str(actor.get("username") or "admin")),
            daemon=True,
            name=f"bonus-initial-{job['id'][:8]}",
        ).start()
        return JSONResponse(
            status_code=202,
            content={
                "ok": True, "job_id": job["id"], "module": "bonus_initial_capacity",
                "status": "queued", "progress": 10, "month": month, "file": filename,
                "message": "Archivo recibido. El corte inicial se está procesando en segundo plano.",
            },
        )

    css = r"""<style id="v321-bonus-responsive-css">
/* Bonos V313: anular el ancho mínimo de 980px que rompía el móvil. */
body[data-v313="1"] .v313,
body[data-v313="1"] #page-bonuses,
body[data-v313="1"] #v313Host {
  box-sizing:border-box!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
}
body[data-v313="1"] #page-bonuses,
body[data-v313="1"] #v313Host,
body[data-v313="1"] .v313 {
  height:auto!important;
  max-height:none!important;
  overflow:visible!important;
}
html:has(body[data-v313="1"]),
body[data-v313="1"] {
  height:auto!important;
  min-height:100%!important;
  overflow-x:hidden!important;
  overflow-y:auto!important;
  -webkit-overflow-scrolling:touch!important;
  touch-action:pan-x pan-y pinch-zoom!important;
}
body[data-v313="1"] main.main,
body[data-v313="1"] section.page,
body[data-v313="1"] section.page.active {
  height:auto!important;
  min-height:0!important;
  max-height:none!important;
  overflow-x:hidden!important;
  overflow-y:visible!important;
  touch-action:pan-x pan-y pinch-zoom!important;
}
.v313 .v313-bonus {
  grid-template-columns:repeat(6,minmax(0,1fr))!important;
  min-width:0!important;
}
.v313 .v313-bonus.v313-bonus-admin {
  grid-template-columns:repeat(7,minmax(0,1fr))!important;
}
.v313 .v313-tabs {
  min-width:0!important;
}
.v313 .v313-scroll {
  width:100%!important;
  max-width:100%!important;
  overflow-x:auto!important;
  overflow-y:hidden!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
  touch-action:pan-x pan-y pinch-zoom!important;
}
.v313 .v313-table {width:max-content;min-width:100%}
.v313 .v313-upload-grid {
  display:grid;
  grid-template-columns:minmax(0,1fr) minmax(0,1.5fr) auto;
  align-items:end;
  gap:10px;
}
.v313 .v313-upload-grid label {
  display:block;font-size:10px;font-weight:850;color:#315676;margin:0 0 5px;
}
.v313 .v313-upload-grid select,
.v313 .v313-upload-grid input[type=file] {
  box-sizing:border-box;width:100%;min-width:0;max-width:100%;
  min-height:36px;padding:7px;border:1px solid #cbd8e8;border-radius:8px;
  background:#fff;color:#123968;font-size:12px;
}
.v313 .v321-upload-button {
  min-height:36px;border:0;border-radius:8px;background:#1475ee;color:#fff;
  font-size:11px;font-weight:900;padding:8px 14px;cursor:pointer;
}
.v313 .v321-upload-button:disabled {opacity:.55;cursor:wait}
.v313 .v321-history {width:100%;border-collapse:collapse;font-size:11px;margin-top:8px}
.v313 .v321-history th,.v313 .v321-history td {
  padding:7px 8px;border-bottom:1px solid #e5edf5;text-align:left;vertical-align:top;
}
.v313 .v321-history th {background:#f3f7fb;color:#315676}
.v313 .v321-state {font-size:11px;font-weight:800;padding:8px 10px;border-radius:8px;margin-top:8px;background:#eef6ff;color:#244c7a;white-space:normal}
.v313 .v321-state.ok {background:#e8f8ee;color:#147a46}
.v313 .v321-state.err {background:#fff0f1;color:#b42332}
@media(max-width:900px) {
  body[data-v313="1"] .v313 {min-width:0!important;width:100%!important;max-width:100%!important;padding:0 0 18px!important}
  .v313 .v313-head {align-items:stretch;flex-direction:column;gap:8px}
  .v313 .v313-filters {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);width:100%;min-width:0}
  .v313 .v313-field,.v313 .v313-field select {width:100%;min-width:0;max-width:100%;box-sizing:border-box}
  .v313 .v313-bonus {
    display:flex!important;flex-wrap:nowrap!important;overflow-x:auto!important;overflow-y:hidden!important;
    gap:6px;padding:2px 1px 7px;max-width:100%;width:100%;
    -webkit-overflow-scrolling:touch;scrollbar-width:thin;
    touch-action:pan-x pan-y pinch-zoom!important;overscroll-behavior-x:contain;
  }
  .v313 .v313-bonus button {flex:0 0 auto;min-width:74px;max-width:none;height:34px;font-size:10px}
  .v313 .v313-bonus button[data-v313-initial] {min-width:112px}
  .v313 .v313-tabs {
    display:flex!important;flex-wrap:nowrap!important;overflow-x:auto!important;overflow-y:hidden!important;
    gap:6px;padding:2px 1px 7px;max-width:100%;width:100%;
    -webkit-overflow-scrolling:touch;scrollbar-width:thin;
    touch-action:pan-x pan-y pinch-zoom!important;overscroll-behavior-x:contain;
  }
  .v313 .v313-tabs button {flex:0 0 auto;min-width:106px;height:34px;font-size:10px}
  .v313 .v313-subtabs {max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;touch-action:pan-x pan-y pinch-zoom}
  .v313 .v313-subtabs button {flex:0 0 auto;min-width:90px}
  .v313 .v313-cutbar {grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  .v313 .v313-cut {min-width:0;overflow-wrap:anywhere}
  .v313 .v313-cut b {font-size:11px}
  .v313 .v313-hero {align-items:flex-start;flex-direction:column;gap:7px}
  .v313 .v313-hero .tag {white-space:normal;max-width:100%}
  .v313 .v313-kpis {grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:6px}
  .v313 .v313-kpi {min-width:0;min-height:66px;padding:7px}
  .v313 .v313-kpi b {font-size:clamp(15px,4.5vw,20px)}
  .v313 .v313-main {grid-template-columns:minmax(0,1fr)!important;gap:7px}
  .v313 .v313-components {grid-template-columns:repeat(3,minmax(0,1fr));gap:4px}
  .v313 .v313-comp .value {padding:7px 3px}
  .v313 .v313-comp .value b {font-size:clamp(16px,4.4vw,22px)}
  .v313 .v313-matrixcards {grid-template-columns:repeat(2,minmax(0,1fr))}
  .v313 .v313-levels {grid-template-columns:repeat(5,minmax(0,1fr));gap:3px}
  .v313 .v313-level {padding:7px 2px}
  .v313 .v313-level b {font-size:15px}
  .v313 .v313-pairs {grid-template-columns:repeat(2,minmax(0,1fr))}
  .v313 .v313-weeks {grid-template-columns:repeat(2,minmax(0,1fr))}
  .v313 .v313-bars {grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}
  .v313 .v313-bartrack i {width:20px}
  .v313 .v313-upload-grid {grid-template-columns:minmax(0,1fr);gap:9px}
  .v313 .v313-upload-grid label {font-size:11px}
  .v313 .v321-upload-button {width:100%;min-height:40px}
  .v313 .v321-history-wrap {max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;touch-action:pan-x pan-y pinch-zoom}
  .v313 .v321-history {min-width:520px}
}
@media(max-width:430px) {
  .v313 .v313-cutbar {grid-template-columns:minmax(0,1fr)}
  .v313 .v313-filters {grid-template-columns:minmax(0,1fr)}
  .v313 .v313-kpis {grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .v313 .v313-components {grid-template-columns:minmax(0,1fr)}
  .v313 .v313-comp .value {display:flex;align-items:center;justify-content:space-between;gap:8px;text-align:left}
  .v313 .v313-comp .value b {font-size:19px}
  .v313 .v313-levels {grid-template-columns:repeat(3,minmax(0,1fr))}
}
</style>"""

    @m.app.middleware("http")
    async def v321_bonus_responsive_html(request: Request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v321-bonus-responsive-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-Bonus-Version": "V321-INITIAL-CUT-RESPONSIVE",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V321] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V321_BONUS_INITIAL_UPLOAD_RESPONSIVE = True
    print("[V321] Carga mensual de corte inicial y ajuste responsive de Bonos instalados.", flush=True)
