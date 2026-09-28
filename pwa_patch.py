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
        commit = (os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or "local").strip()
        deploy_id = (os.getenv("RENDER_DEPLOY_ID") or "").strip()
        return JSONResponse(
            {
                "version": commit[:12] if commit else "local",
                "commit": commit,
                "deploy_id": deploy_id,
            },
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
