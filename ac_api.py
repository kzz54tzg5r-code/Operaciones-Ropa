"""Rutas opcionales de Propuesta AC. NO se importan ni montan en producción.

Integración futura, explícita:
    router = create_ac_router(ACBridge(AC_DATA_DIRECTORY), require_actor)
    app.include_router(router)

require_actor(request) debe ser la autenticación real del servidor y devolver
{role, store, id/username}. No se admite tienda/colaborador desde el navegador.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from typing import Dict

from ac_bridge import ACBridge

COLLABORATOR_ROLES = {"colaborador", "colaborador_operativo"}
CAPTURE_ROLES = COLLABORATOR_ROLES | {"admin", "superadmin", "tienda"}
CAPACITY_ROLES = {"admin", "superadmin"}
VIEW_ROLES = CAPTURE_ROLES | {"director"}

class StartActivity(BaseModel):
    flow: str
    stage: str
    area: str

class CaptureSizes(BaseModel):
    session_id: str
    event_key: str = Field(min_length=8, max_length=128)
    model_id: str = Field(min_length=1, max_length=120)
    color: str = Field(default="", max_length=120)
    sizes: Dict[str, int]

class FinishActivity(BaseModel):
    session_id: str

def create_ac_router(bridge: ACBridge, require_actor):
    """Montar sólo después de validar identidad/alcance y aprobar integración."""
    router = APIRouter(prefix="/api/ac", tags=["AC experimental"])

    def actor_from(request: Request, allowed):
        try:
            actor = require_actor(request)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(401, "Sesión no autorizada")
        if not isinstance(actor, dict):
            try:actor = dict(actor)
            except Exception:raise HTTPException(401, "Sesión inválida")
        role = str(actor.get("role") or "").lower().strip()
        if role not in allowed:
            raise HTTPException(403, "Rol sin permiso")
        employee_id = str(actor.get("id") or actor.get("user_id") or "").strip()
        if not employee_id:
            raise HTTPException(401, "Usuario sin ID autenticado")
        store = str(actor.get("store") or "").strip()
        if not store and role in COLLABORATOR_ROLES | {"tienda"}:
            raise HTTPException(403, "El usuario no tiene tienda asignada")
        return role, store, employee_id, actor

    def fail(exc):
        if isinstance(exc, ValueError):
            raise HTTPException(400, str(exc))
        if isinstance(exc, HTTPException):
            raise exc
        raise exc

    @router.post("/session/start", status_code=201)
    def start_activity(payload: StartActivity, request: Request):
        role, store, employee_id, actor = actor_from(request, CAPTURE_ROLES)
        if not store:
            raise HTTPException(403, "Seleccione una tienda mediante autorización del servidor")
        try:
            return {"session_id": bridge.start(store=store, employee_id=employee_id,
                    flow=payload.flow, stage=payload.stage, area=payload.area)}
        except Exception as exc:fail(exc)

    @router.post("/capture", status_code=201)
    def capture_sizes(payload: CaptureSizes, request: Request):
        role, store, employee_id, actor = actor_from(request, CAPTURE_ROLES)
        if not store:
            raise HTTPException(403, "Se requiere tienda asignada")
        # Verificar además el alcance en la base de datos: no confiar en session_id.
        with bridge.operation.transaction() as db:
            session = db.execute(
                "SELECT store, employee_id FROM ac_sessions WHERE id=?",
                (payload.session_id,)
            ).fetchone()
        if not session or session["store"] != store or session["employee_id"] != employee_id:
            raise HTTPException(403, "Sesión ajena a la tienda o colaborador")
        try:
            return {"capture_id": bridge.capture(event_key=payload.event_key,
                    session_id=payload.session_id,employee_id=employee_id,
                    model_id=payload.model_id,color=payload.color,sizes=payload.sizes)}
        except Exception as exc:fail(exc)

    @router.post("/session/finish")
    def finish_activity(payload: FinishActivity, request: Request):
        _, store, employee_id, _ = actor_from(request, CAPTURE_ROLES)
        try:
            bridge.finish(payload.session_id,employee_id)
            return {"ok":True}
        except Exception as exc:fail(exc)

    @router.get("/capacity")
    def capacity_by_size(request: Request, model_id: str, size: str):
        _, store, _, _ = actor_from(request, VIEW_ROLES)
        if not store:
            raise HTTPException(403, "Consulta nacional pendiente de implementación")
        return bridge.capacities.latest(store, model_id, size) or {"status":"not_found"}

    @router.get("/suggest")
    def suggested_replenishment(request: Request, model_id: str, size: str, criterion: str = "curve"):
        _, store, _, _ = actor_from(request, VIEW_ROLES)
        if not store:
            raise HTTPException(403, "Consulta nacional pendiente de implementación")
        try:
            return bridge.suggest(store=store,model_id=model_id,size=size,criterion=criterion)
        except Exception as exc:fail(exc)

    @router.post("/capacity/upload", status_code=201)
    async def upload_capacities(request: Request, file: UploadFile = File(...),
                                version: str = ""):
        _, _, _, actor = actor_from(request, CAPACITY_ROLES)
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            raise HTTPException(400, "Sólo se permite un archivo .xlsx")
        contents = await file.read(15*1024*1024+1)
        if len(contents)>15*1024*1024:
            raise HTTPException(413, "El archivo supera 15 MB")
        try:
            batch = bridge.upload_capacities(contents,version=version,
                admin_user=str(actor.get("username") or actor.get("id")))
            return {"batch_id":batch,"ok":True}
        except Exception as exc:fail(exc)

    return router
