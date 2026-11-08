"""Servidor de laboratorio AC sobre la autenticación REAL de web_app.

Ejecutar SÓLO con un directorio aislado:
    AC_LAB_DATA_DIR=/tmp/operaciones-ac-lab uvicorn ac_lab_server:app --host 127.0.0.1 --port 8091

No se importa desde server_entry ni modifica la aplicación productiva.
La base y sesiones web de esta instancia pertenecen al laboratorio.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

LAB = os.environ.get("AC_LAB_DATA_DIR", "").strip()
if not LAB:
    raise RuntimeError("AC_LAB_DATA_DIR es obligatorio para iniciar el laboratorio AC")

lab_root = Path(LAB).expanduser().resolve()
repo_root = Path(__file__).resolve().parent
if (
    lab_root == repo_root
    or repo_root in lab_root.parents
    or lab_root == Path("/var/data")
    or Path("/var/data") in lab_root.parents
):
    raise RuntimeError("No está permitido usar el repositorio ni /var/data como directorio de laboratorio")

# El directorio se fija ANTES de importar web_app para aislar su SQLite y archivos.
os.environ["OPERACIONES_ROPA_DATA"] = str(lab_root)
import web_app  # noqa: E402
from web_app import app, require_user  # noqa: E402
from ac_api import create_ac_router  # noqa: E402
from ac_bridge import ACBridge  # noqa: E402
from ac_catalog import ExistingCatalogLookup  # noqa: E402
from v314_bonus_product_photos_patch import install as install_bonus_photos  # noqa: E402

# V314 ya está instalado por server_entry en la aplicación habitual.
# Este laboratorio importa sólo web_app: instalar el MISMO V314 aquí hace
# disponible /api/bonuses/product-photo/{ID} sin inventar otro servicio.
install_bonus_photos(web_app)

# Impedir la importación de usuarios desde una base heredada del repositorio.
# Los perfiles de prueba deben pertenecer EXCLUSIVAMENTE al directorio de laboratorio.
web_app.LEGACY_DB = lab_root / "legacy_user_import_disabled.db"

ac = ACBridge(lab_root)
ac.initialize()
app.include_router(create_ac_router(
    ac, require_user,
    catalog_lookup=ExistingCatalogLookup(web_app._latest_capacity_frame),
))

@app.get("/ac/laboratorio", include_in_schema=False)
def ac_lab_ui(request: Request):
    user = require_user(request)
    if str(user.get("role") or "") not in {
        "colaborador", "colaborador_operativo", "tienda", "admin", "superadmin"
    }:
        raise HTTPException(403, "La captura AC no está autorizada para este perfil")
    return FileResponse(
        repo_root / "ac_capture_laboratorio.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"}
    )
