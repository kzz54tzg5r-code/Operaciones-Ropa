"""Rutas PWA de Operaciones Ropa.

Sirve el manifest y el service worker desde el alcance raíz sin almacenar
respuestas de /api/. La lógica de negocio permanece en web_app.
"""
from pathlib import Path
import os

from fastapi.responses import FileResponse, JSONResponse


def install(mod):
    web = Path(mod.WEB)

    @mod.app.get("/manifest.webmanifest", include_in_schema=False)
    def pwa_manifest():
        return FileResponse(
            web / "manifest.webmanifest",
            media_type="application/manifest+json",
            headers={"Cache-Control": "public, max-age=300"},
        )

    @mod.app.get("/service-worker.js", include_in_schema=False)
    def pwa_service_worker():
        return FileResponse(
            web / "service-worker.js",
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Service-Worker-Allowed": "/",
            },
        )

    @mod.app.get("/api/app-version", include_in_schema=False)
    def pwa_app_version():
        # Railway y Render usan variables distintas. Devolver "local" en Railway
        # impedía detectar versiones nuevas y ocultaba el banner de actualización.
        commit = (
            os.getenv("RAILWAY_GIT_COMMIT_SHA")
            or os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GIT_COMMIT")
            or ""
        ).strip()
        deploy_id = (
            os.getenv("RAILWAY_DEPLOYMENT_ID")
            or os.getenv("RENDER_DEPLOY_ID")
            or ""
        ).strip()
        # En despliegues que no exponen el SHA, usar una huella reproducible del
        # código servido, evitando que todas las versiones reporten "local".
        if not commit:
            import hashlib
            fingerprint = hashlib.sha256()
            for relative_path in (
                "server_entry.py", "pwa_patch.py", "v293_sales_bonus_patch.py",
                "v313_bonus_visual_and_cut_patch.py", "v314_bonus_product_photos_patch.py",
                "v322_bonus_model_exports.py", "web/pwa_install.js",
            ):
                candidate = Path(__file__).resolve().parent / relative_path
                try:
                    fingerprint.update(relative_path.encode("utf-8"))
                    fingerprint.update(candidate.read_bytes())
                except OSError:
                    continue
            commit = fingerprint.hexdigest()
        return JSONResponse(
            {
                "version": commit[:12],
                "commit": commit,
                "deploy_id": deploy_id,
            },
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
