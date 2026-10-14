"""V321 · Carga mensual del corte inicial de Bonos + ajuste responsive específico.

El corte inicial queda asociado explícitamente al periodo elegido sin sustituir
el histórico general de Capacidades. Los seis bonos y sus cálculos se conservan.
"""
from __future__ import annotations

import asyncio
import re
import secrets
from datetime import datetime
from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

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
        entries = {
            str(x.get("id") or ""): dict(x)
            for x in (manifest.get("capacities") or [])
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

    @m.app.post("/api/bonuses/initial-capacity")
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
        stage_path = m.STAGING_DIR / f"bonus_initial_{secrets.token_hex(8)}{suffix}"
        try:
            size = await m._save_upload_stream(file, stage_path)
            if not size:
                raise HTTPException(400, "El archivo está vacío.")
            entry = await asyncio.to_thread(m._save_capacity_source_path, stage_path, filename)
        finally:
            try:
                stage_path.unlink(missing_ok=True)
            except Exception:
                pass

        try:
            result = await asyncio.to_thread(m._process_capacity_entry, entry, filename)
        except Exception as exc:
            raise HTTPException(400, f"No se pudo procesar el corte inicial: {str(exc)[:350]}")

        if not result.get("ok"):
            raise HTTPException(400, str(result.get("message") or "No se pudo procesar el Excel."))

        manifest = m.load_manifest()
        processed = next(
            (dict(x) for x in (manifest.get("capacities") or [])
             if str(x.get("id") or "") == str(entry.get("id") or "")),
            None,
        )
        if not processed or str(processed.get("status") or "").lower() != "procesado":
            raise HTTPException(409, "El Excel no quedó procesado; el corte inicial no se asignó al mes.")

        cuts = manifest.setdefault("bonus_initial_cuts", {})
        previous = cuts.get(month)
        cuts[month] = str(processed.get("id") or "")
        m.save_manifest(manifest)

        print(
            f"[V321] Corte inicial de Bonos asignado: mes={month} archivo={processed.get('name')} "
            f"usuario={actor.get('username', 'admin')}",
            flush=True,
        )
        return {
            "ok": True,
            "month": month,
            "entry_id": str(processed.get("id") or ""),
            "file": str(processed.get("name") or filename),
            "report_date": str(processed.get("report_date") or ""),
            "rows": result.get("rows"),
            "stores": result.get("stores"),
            "replaced_previous": bool(previous and str(previous) != str(processed.get("id") or "")),
            "message": "Corte inicial procesado y asociado al periodo seleccionado.",
        }

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
body[data-v313="1"] html,
body[data-v313="1"] body {
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
  grid-template-columns:repeat(7,minmax(0,1fr))!important;
  min-width:0!important;
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
