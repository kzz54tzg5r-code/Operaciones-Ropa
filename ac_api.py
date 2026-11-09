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
from typing import Dict, List
from urllib.parse import urlsplit
import re

from ac_bridge import ACBridge

COLLABORATOR_ROLES = {"colaborador", "colaborador_operativo"}
CAPTURE_ROLES = COLLABORATOR_ROLES | {"admin", "superadmin", "tienda"}
CAPACITY_ROLES = {"admin", "superadmin"}
VIEW_ROLES = CAPTURE_ROLES | {"director","supervisor","gerente"}
ORDER_ROLES = {"supervisor","gerente","admin","superadmin"}

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
    task_id: str | None = None
    target_location_id: str | None = None

class NewStockLocation(BaseModel):
    kind: str
    aisle: str = ""
    face: str = ""
    section: str = ""
    level: str = ""
    pallet: str = ""

class InitialStockCount(BaseModel):
    event_key: str = Field(min_length=8,max_length=128)
    location_id: str = Field(min_length=1,max_length=120)
    model_id: str = Field(min_length=1,max_length=120)
    size: str = Field(min_length=1,max_length=30)
    pieces: int = Field(ge=0,le=1000000)

class ApproveOrder(BaseModel):
    event_key: str = Field(min_length=8, max_length=128)
    model_id: str = Field(min_length=1, max_length=120)
    area: str
    criterion: str = "curve"
    sizes: List[str] | None = None

class TaskClaim(BaseModel):
    session_id: str

class FinishActivity(BaseModel):
    session_id: str

def create_ac_router(bridge: ACBridge, require_actor, catalog_lookup=None):
    """Montar sólo después de validar identidad/alcance y aprobar integración."""
    router = APIRouter(prefix="/api/ac", tags=["AC experimental"])

    def actor_from(request: Request, allowed):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.url.netloc:
                raise HTTPException(403, "Origen de solicitud no autorizado")
            if request.headers.get("sec-fetch-site", "") in {"cross-site", "same-site"}:
                raise HTTPException(403, "Solicitud externa no autorizada")
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

    @router.get("/me")
    def identity(request: Request):
        role, store, employee_id, _ = actor_from(request, VIEW_ROLES)
        return {"role":role,"store":store,"employee_id":employee_id}

    @router.get("/model")
    def model_info(request: Request, model_id: str):
        role, store, _, _ = actor_from(request, VIEW_ROLES)
        model_id = model_id.strip()
        # La fotografía de Bonos V314 se protege por la sesión, NO depende
        # de una tienda. Un administrador puede consultar la foto antes de
        # elegir tienda; los metadatos e inventario sí conservan el filtro.
        if not store and role not in {"admin","superadmin","director"}:
            raise HTTPException(403, "Tienda no asignada")
        if not model_id or len(model_id)>120:
            raise HTTPException(400, "ID inválido")
        # Reutilizar EXACTAMENTE el servicio de fotografías de Bonos V314.
        # Este endpoint autentica la solicitud, valida el ID, cachea y prueba
        # JPG / PNG / WebP sin sustituir nunca fotografías de otros modelos.
        photo = ("/api/bonuses/product-photo/" + model_id
                 if re.fullmatch(r"[0-9]{1,15}", model_id) else None)
        # La foto se verifica realmente al pedir la imagen: 404 significa
        # ausencia y 503 fallo temporal; nunca anticipar "foto disponible".
        if catalog_lookup is None:
            return {"model_id":model_id, "name":None, "color":None,
                    "location":None, "photo_url":photo,
                    "photo_status":"bonus_lookup_pending" if photo else "invalid_photo_id"}
        # El catálogo es complementario. Una tienda sin seleccionar o un
        # error de metadatos nunca deben impedir consultar la foto ya
        # disponible desde Bonos con el mismo inicio de sesión.
        result = None
        if store:
            try:
                result = catalog_lookup(store, model_id)
            except Exception:
                import logging
                logging.getLogger("operaciones_ropa.ac").exception(
                    "Fallo de metadatos comerciales AC para modelo %s", model_id
                )
        if not isinstance(result, dict):
            result = {}
        return {"model_id":model_id, "name":result.get("name"),
                "color":result.get("color"), "location":result.get("location"),
                "photo_url":photo,
                "photo_status":"bonus_lookup_pending" if photo else "invalid_photo_id"}

    @router.get("/session/active")
    def active_session(request: Request):
        _, store, employee_id, _ = actor_from(request, CAPTURE_ROLES)
        if not store:
            raise HTTPException(403, "Tienda no asignada")
        with bridge.operation.transaction() as db:
            row = db.execute(
                "SELECT id,flow,stage,area,started_at FROM ac_sessions "
                "WHERE store=? AND employee_id=? AND status='active' "
                "ORDER BY started_at DESC LIMIT 1", (store,employee_id)
            ).fetchone()
        return {"session":dict(row) if row else None}

    @router.get("/stock")
    def stock_view(request: Request, model_id: str):
        _, store, _, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403,"Tienda no seleccionada")
        return {"stock":bridge.stock_setup.stock(store=store,model_id=model_id)}

    @router.get("/stock/locations")
    def stock_locations(request: Request, kind: str=""):
        _, store, _, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403,"Tienda no seleccionada")
        if kind and kind not in {"Piso","Rack","Septimos","Tarima"}:
            raise HTTPException(400,"Ubicación inválida")
        return {"locations":bridge.stock_setup.locations(store=store,kind=kind)}

    @router.post("/stock/locations", status_code=201)
    def new_stock_location(payload: NewStockLocation,request: Request):
        _, store, _, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403,"Tienda no seleccionada")
        try:
            loc=bridge.stock_setup.add_location(store=store,kind=payload.kind,
                aisle=payload.aisle,face=payload.face,section=payload.section,
                level=payload.level,pallet=payload.pallet)
            return {"id":loc,"ok":True}
        except Exception as exc:fail(exc)

    @router.post("/stock/initial-count", status_code=201)
    def initial_physical_count(payload: InitialStockCount,request: Request):
        role, store, employee_id, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403,"Tienda no seleccionada")
        try:
            code=bridge.stock_setup.initial_count(event_key=payload.event_key,
                store=store,location_id=payload.location_id,
                model_id=payload.model_id,size=payload.size,pieces=payload.pieces,
                verified_by=employee_id)
            return {"id":code,"ok":True}
        except Exception as exc:fail(exc)

    @router.get("/orders/preview")
    def preview_order(request: Request, model_id: str, area: str,
                      criterion: str="curve", sizes: str=""):
        role, store, _, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403, "La aprobación requiere tienda autorizada")
        try:
            return bridge.order_preview(store=store,model_id=model_id,area=area,
                criterion=criterion,sizes=[x.strip() for x in sizes.split(",") if x.strip()] if sizes else None)
        except Exception as exc:fail(exc)

    @router.get("/orders")
    def order_history(request: Request):
        _, store, _, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403, "Consulta por tienda obligatoria")
        return {"orders":bridge.list_orders(store=store)}

    @router.post("/orders/approve", status_code=201)
    def approve_order(payload: ApproveOrder,request: Request):
        role, store, employee_id, _ = actor_from(request, ORDER_ROLES)
        if not store:
            raise HTTPException(403, "No tienes una tienda autorizada")
        try:
            return bridge.approve_order(
                event_key=payload.event_key,store=store,model_id=payload.model_id,
                area=payload.area,requested_by=employee_id,approver_role=role,
                criterion=payload.criterion,sizes=payload.sizes)
        except Exception as exc:fail(exc)

    @router.get("/locations")
    def available_locations(request: Request, kind: str="Piso"):
        _, store, _, _ = actor_from(request, VIEW_ROLES)
        if not store or kind!="Piso":
            raise HTTPException(403, "Sólo ubicaciones de piso de la tienda")
        with bridge.operation.transaction() as db:
            rows=db.execute(
                "SELECT id,aisle,face,section,level,pallet FROM ac_locations "
                "WHERE store=? AND kind='Piso' AND active=1 ORDER BY aisle,face,section,level",
                (store,)
            ).fetchall()
        return {"locations":[dict(r) for r in rows]}

    @router.get("/tasks")
    def task_queue(request: Request, session_id: str):
        _, store, employee_id, _ = actor_from(request, CAPTURE_ROLES)
        with bridge.operation.transaction() as db:
            s = db.execute(
                "SELECT flow,stage,area FROM ac_sessions WHERE id=? AND store=? "
                "AND employee_id=? AND status='active'",(session_id,store,employee_id)
            ).fetchone()
        if not s:
            raise HTTPException(403, "Debes tener una actividad activa de tu tienda")
        return {"tasks":bridge.tasks(
            store=store,flow=s["flow"],stage=s["stage"],area=s["area"],
            employee_id=employee_id
        )}

    @router.post("/tasks/{task_id}/claim")
    def claim_task(task_id: str, payload: TaskClaim, request: Request):
        _, store, employee_id, _ = actor_from(request, CAPTURE_ROLES)
        if not store:
            raise HTTPException(403, "Tienda no asignada")
        try:
            claimed=bridge.claim(store=store,task_id=task_id,
                                 session_id=payload.session_id,
                                 employee_id=employee_id)
            return {"task_id":claimed,"status":"in_progress"}
        except Exception as exc:fail(exc)

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
                    model_id=payload.model_id,color=payload.color,sizes=payload.sizes,
                    task_id=payload.task_id,
                    target_location_id=payload.target_location_id)}
        except Exception as exc:fail(exc)

    @router.post("/session/finish")
    def finish_activity(payload: FinishActivity, request: Request):
        _, store, employee_id, _ = actor_from(request, CAPTURE_ROLES)
        with bridge.operation.transaction() as db:
            owned = db.execute("SELECT id FROM ac_sessions WHERE id=? AND store=? AND employee_id=?",
                               (payload.session_id,store,employee_id)).fetchone()
        if not owned:
            raise HTTPException(403, "Sesión ajena a la tienda o colaborador")
        try:
            bridge.finish(payload.session_id,employee_id)
            return {"ok":True}
        except Exception as exc:fail(exc)

    @router.get("/capacity/model-sizes")
    def model_capacity_sizes(request: Request, model_id: str):
        _, store, _, _ = actor_from(request, VIEW_ROLES)
        if not store:
            raise HTTPException(403, "Se requiere tienda asignada para consultar tallas")
        return bridge.capacities.model_sizes(store,model_id)

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
