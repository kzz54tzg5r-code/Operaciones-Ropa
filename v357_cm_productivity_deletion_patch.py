"""V357: baja auditada de capturas digitales C&M, sólo admin/superadmin.

No toca archivos de Excel ni operaciones de otros módulos. Una baja conserva
la fila original con status='deleted' y genera un registro de auditoría.
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request


def install(m):
    if getattr(m, "_V357_CM_PRODUCTIVITY_DELETE", False):
        return

    with m.db() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS cm_productivity_deletion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_id INTEGER NOT NULL UNIQUE,
                deleted_at TEXT NOT NULL,
                deleted_by TEXT NOT NULL,
                deleted_by_id INTEGER,
                previous_status TEXT NOT NULL,
                snapshot_json TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_cm_prod_delete_time "
            "ON cm_productivity_deletion_log(deleted_at)"
        )

    @m.app.post("/api/cm-productivity/delete-selected")
    async def delete_selected_productivity(request: Request):
        actor = m.require_user(request, ("admin", "superadmin"))
        body = await request.json()
        values = body.get("ids") if isinstance(body, dict) else None
        if not isinstance(values, list) or not 1 <= len(values) <= 50:
            raise HTTPException(400, "Selecciona entre 1 y 50 capturas digitales")
        if any(isinstance(value, bool) or not isinstance(value, int)
               or value <= 0 for value in values):
            raise HTTPException(400, "Identificadores de captura inválidos")
        ids = list(dict.fromkeys(values))
        if len(ids) != len(values):
            raise HTTPException(400, "La selección contiene registros duplicados")

        stamp = datetime.now(ZoneInfo("America/Mexico_City")).isoformat(timespec="seconds")
        with m.db() as con:
            # Todas las comprobaciones antes del primer UPDATE: operación atómica.
            rows = []
            for capture_id in ids:
                found = con.execute(
                    "SELECT * FROM cm_productivity_capture WHERE id=?", (capture_id,)
                ).fetchone()
                if found is None:
                    raise HTTPException(404, f"La captura {capture_id} no existe")
                row = dict(found)
                if row.get("status") != "finished":
                    raise HTTPException(
                        409, f"La captura {capture_id} no está finalizada o ya fue eliminada"
                    )
                rows.append(row)
            for row in rows:
                capture_id = int(row["id"])
                cur = con.execute(
                    "UPDATE cm_productivity_capture SET status='deleted',updated_at=? "
                    "WHERE id=? AND status='finished'",
                    (stamp, capture_id),
                )
                if cur.rowcount != 1:
                    raise HTTPException(409, "La selección cambió; consulta nuevamente")
                con.execute(
                    "INSERT INTO cm_productivity_deletion_log "
                    "(capture_id,deleted_at,deleted_by,deleted_by_id,previous_status,snapshot_json) "
                    "VALUES(?,?,?,?,?,?)",
                    (capture_id, stamp, str(actor.get("username") or ""),
                     actor.get("id"), row["status"],
                     json.dumps(row, ensure_ascii=False, default=str)),
                )
        return {
            "ok": True,
            "deleted": len(ids),
            "ids": ids,
            "message": f"{len(ids)} captura(s) eliminada(s) del reporte. Se conservó auditoría.",
        }

    m._V357_CM_PRODUCTIVITY_DELETE = True
