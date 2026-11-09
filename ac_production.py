"""Montaje opcional de Propuesta AC en la aplicación Render existente.

El módulo no altera operaciones históricas: crea una SQLite independiente
bajo OPERACIONES_ROPA_DATA/ac/, reutiliza la sesión y el servicio de fotos de
Bonos V314 ya instalados por server_entry. Se activa exclusivamente mediante
OPERACIONES_ROPA_AC_ENABLED=1.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from ac_bridge import ACBridge
from ac_api import create_ac_router
from ac_catalog import ExistingCatalogLookup

LOG=logging.getLogger("operaciones_ropa.ac")

def install(web_app):
    if os.getenv("OPERACIONES_ROPA_AC_ENABLED","0")!="1":
        LOG.info("Propuesta AC no activada: rutas de producción intactas")
        return False

    root=Path(web_app.DATA_ROOT).resolve()
    dbdir=root/"ac"
    if not str(dbdir).startswith(str(root)+os.sep):
        raise RuntimeError("Directorio AC fuera de la persistencia autorizada")
    try:
        if not root.is_dir() or shutil.disk_usage(root).free < 64 * 1024 * 1024:
            LOG.error("AC no se activó: disco persistente ausente o menos de 64 MiB libres")
            return False
    except OSError:
        LOG.exception("AC no se activó: no se pudo verificar espacio del disco persistente")
        return False
    try:
        bridge=ACBridge(dbdir)
        bridge.initialize()
    except Exception:
        LOG.exception("AC no pudo inicializar su SQLite; la aplicación anterior sigue operativa")
        # No registrar rutas con una base incompleta.
        return False

    # Los roles quedan disponibles para crear cuentas en la administración
    # existente; no se cambian cuentas ni se conceden permisos por defecto.
    web_app.ROLES=tuple(dict.fromkeys((*web_app.ROLES,"supervisor","gerente")))
    web_app.ROLE_LABELS.update({
        "supervisor":"Supervisor · Operaciones AC",
        "gerente":"Gerente · Operaciones AC",
    })

    def authorized_stores():
        # Sólo tiendas activas y marcadas como Proyecto en el sistema actual.
        # Se consulta dinámicamente: un cambio de alcance se aplica también
        # a sesiones AC existentes, sin reiniciar el módulo.
        selected=web_app.project_store_names(True)
        approved={web_app.login_key(s) for s in web_app.PROJECT_STORES}
        return {
            web_app.login_key(s):s
            for s in selected
            if web_app.login_key(s) in approved
        }

    def store_from_user(request: Request,user: dict):
        role=str(user.get("role") or "")
        real=str(user.get("real_role") or role)
        if role in {"admin","superadmin"} and real in {"admin","superadmin"}:
            requested=str(request.session.get("ac_store") or user.get("store") or "")
        else:
            requested=str(user.get("store") or "")
        return authorized_stores().get(web_app.login_key(requested),"") if requested else ""

    def actor(request: Request):
        user=web_app.require_user(request)
        user=dict(user)
        role=str(user.get("role") or "")
        user["store"]=store_from_user(request,user)
        # Sólo cuentas con tienda real o alcance explícito admin/superadmin.
        if role in {"supervisor","gerente","tienda","colaborador_operativo"} and not user["store"]:
            raise HTTPException(403,"Tu perfil no tiene una tienda válida asignada")
        return user

    web_app.app.include_router(
        create_ac_router(bridge,actor,
                         catalog_lookup=ExistingCatalogLookup(web_app._latest_capacity_frame))
    )

    def require_ac_user(request,roles):
        user=actor(request)
        if str(user["role"]) not in roles:
            raise HTTPException(403,"Este perfil no puede abrir la pantalla AC")
        if not user["store"] and user["role"] not in {"admin","superadmin"}:
            raise HTTPException(403,"Selecciona una tienda autorizada")
        return user

    def html_file(path):
        return FileResponse(
            Path(__file__).resolve().parent/path,
            media_type="text/html",
            headers={"Cache-Control":"no-store",
                     "X-Robots-Tag":"noindex",
                     "Content-Security-Policy":"frame-ancestors 'none'"},
        )

    @web_app.app.get("/ac", include_in_schema=False)
    def ac_home(request: Request):
        user=require_ac_user(request,{"superadmin","admin","supervisor","gerente","tienda","colaborador_operativo"})
        target="/ac/configuracion" if user["role"] in {"admin","superadmin"} and not user["store"] else (
            "/ac/pedidos" if user["role"] in {"supervisor","gerente"} else "/ac/captura"
        )
        return RedirectResponse(target,status_code=303)

    @web_app.app.get("/ac/captura", include_in_schema=False)
    def ac_capture_page(request: Request):
        require_ac_user(request,{"superadmin","admin","tienda","colaborador_operativo"})
        return html_file("ac_capture_laboratorio.html")

    @web_app.app.get("/ac/pedidos", include_in_schema=False)
    def ac_order_page(request: Request):
        u=require_ac_user(request,{"superadmin","admin","supervisor","gerente"})
        if not u["store"]:
            return RedirectResponse("/ac/configuracion",303)
        return html_file("ac_orders_laboratorio.html")

    @web_app.app.get("/ac/configuracion", include_in_schema=False)
    def ac_configuration(request: Request):
        require_ac_user(request,{"superadmin","admin","supervisor","gerente"})
        return html_file("ac_configuracion.html")

    def check_same_site(request):
        from urllib.parse import urlsplit
        origin=request.headers.get("origin","")
        if origin and urlsplit(origin).netloc!=request.url.netloc:
            raise HTTPException(403,"Origen no autorizado")
        if request.headers.get("sec-fetch-site") in ("cross-site","same-site"):
            raise HTTPException(403,"Petición externa bloqueada")

    @web_app.app.get("/api/ac/stores")
    def ac_stores(request: Request):
        u=require_ac_user(request,{"superadmin","admin","supervisor","gerente"})
        if u["role"] in {"superadmin","admin"}:
            return {"stores":list(authorized_stores().values()),"selected":u["store"]}
        return {"stores":[u["store"]],"selected":u["store"]}

    @web_app.app.post("/api/ac/select-store")
    async def ac_select_store(request: Request):
        check_same_site(request)
        user=web_app.require_user(request,("superadmin","admin"))
        body=await request.json()
        store=authorized_stores().get(web_app.login_key(body.get("store")),"")
        if not store:
            raise HTTPException(400,"La tienda no existe dentro del proyecto")
        request.session["ac_store"]=store
        return {"ok":True,"store":store}

    @web_app.app.get("/api/ac/health")
    def ac_health(request: Request):
        require_ac_user(request,{"superadmin","admin"})
        with bridge.operation.transaction() as db:
            tables=[r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ac_%'"
            )]
        return {"status":"ready","database":"isolated","schema_tables":len(tables)}

    LOG.info("AC activada en rutas propias con almacenamiento aislado")
    return True
