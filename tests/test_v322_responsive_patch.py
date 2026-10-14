from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from v322_universal_responsive_audit_patch import install


def test_v322_injects_responsive_authority_without_rewriting_report_data():
    app = FastAPI()

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return HTMLResponse(
            '<!doctype html><html><head></head><body>'
            '<main class="main"><div class="tablewrap"><table class="table">'
            '<tr><th>Encabezado</th></tr><tr><td>Dato real</td></tr>'
            '</table></div></main></body></html>'
        )

    target = SimpleNamespace(app=app)
    install(target)
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Operations-UI-Version"] == "V322-UNIVERSAL-RESPONSIVE-AUDIT"
    assert 'id="v322-universal-responsive-css"' in response.text
    assert "@media (max-width: 1180px)" in response.text
    assert "overflow-y: visible !important" in response.text
    assert "overflow-x: auto !important" in response.text
    assert "touch-action: pan-x pan-y pinch-zoom !important" in response.text
    assert "env(safe-area-inset-bottom)" in response.text
    assert "Dato real" in response.text


def test_v322_install_is_idempotent():
    app = FastAPI()

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return HTMLResponse("<html><head></head><body></body></html>")

    target = SimpleNamespace(app=app)
    install(target)
    middleware_count = len(app.user_middleware)
    install(target)
    assert len(app.user_middleware) == middleware_count
