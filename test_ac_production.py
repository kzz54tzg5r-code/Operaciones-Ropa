"""Pruebas de instalación AC en app original simulada, sin tocar Render."""
import os
import tempfile
import unicodedata
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from ac_production import install


def key(text):
    normalized=unicodedata.normalize("NFKD",str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold().strip()


def web(tmp):
    app=FastAPI()
    app.add_middleware(SessionMiddleware,secret_key="test-secret-key")
    original_roles=("superadmin","admin","director","tienda","colaborador_operativo")
    @app.get("/legacy")
    def legacy():
        return {"legacy":"available"}
    def require_user(request:Request,roles=None):
        role=request.headers.get("x-role")
        if not role:raise HTTPException(401,"Sesión requerida")
        if roles and role not in roles:raise HTTPException(403,"Rol inválido")
        return {"id":request.headers.get("x-id","1"),
                "username":"test-user","role":role,"real_role":role,
                "store":request.headers.get("x-store","")}
    return SimpleNamespace(
        DATA_ROOT=Path(tmp),
        ROLES=original_roles,
        ROLE_LABELS={r:r for r in original_roles},
        app=app,
        PROJECT_STORES=("Iztapalapa","Vallejo","Atemajac"),
        project_store_names=lambda active_only=True:["Iztapalapa","Vallejo","Atemajac"],
        login_key=key,
        require_user=require_user,
        _latest_capacity_frame=lambda:None,
    )


def test_disabled_feature_keeps_original_app_and_user_roles(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.delenv("OPERACIONES_ROPA_AC_ENABLED",raising=False)
        m=web(tmp)
        assert install(m) is False
        assert "gerente" not in m.ROLES
        with TestClient(m.app) as client:
            assert client.get("/legacy").status_code==200
            assert client.get("/ac").status_code==404
            assert not (Path(tmp)/"ac").exists()


def test_enabled_feature_has_scope_roles_and_isolated_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("OPERACIONES_ROPA_AC_ENABLED","1")
        m=web(tmp)
        assert install(m) is True
        assert {"supervisor","gerente"}.issubset(m.ROLES)
        assert (Path(tmp)/"ac"/"propuesta_ac.sqlite3").exists()
        with TestClient(m.app) as client:
            assert client.get("/legacy").json()["legacy"]=="available"
            assert client.get("/ac").status_code==401
            assert client.get("/ac/captura",headers={"x-role":"director"}).status_code==403
            admin={"x-role":"admin"}
            assert client.get("/api/ac/stores",headers=admin).json()["selected"]==""
            assert client.get("/api/ac/health",headers=admin).json()["status"]=="ready"
            selected=client.post("/api/ac/select-store",headers=admin,json={"store":"Iztapalapa"})
            assert selected.status_code==200,selected.text
            assert client.get("/api/ac/me",headers=admin).json()["store"]=="Iztapalapa"
            assert client.get("/ac/captura",headers=admin).status_code==200
            assert client.get("/ac/configuracion",headers=admin).status_code==200
            assert client.get("/ac/pedidos",headers=admin).status_code==200
            assert client.post("/api/ac/select-store",headers={**admin,"origin":"https://evil.example"},
                               json={"store":"Vallejo"}).status_code==403
            assert client.post("/api/ac/select-store",headers=admin,json={"store":"No existe"}).status_code==400
            assert client.get("/api/ac/me",headers={"x-role":"gerente","x-store":"Vallejo"}).json()["store"]=="Vallejo"
            assert client.get("/ac/pedidos",headers={"x-role":"gerente","x-store":"Vallejo"}).status_code==200
            assert client.get("/ac/pedidos",headers={"x-role":"gerente"}).status_code==403
            assert client.get("/api/ac/me",headers={"x-role":"gerente","x-store":"Fuera proyecto"}).status_code==403
            assert client.post("/api/ac/orders/approve",headers={"x-role":"colaborador_operativo","x-store":"Vallejo"},
                json={"event_key":"test-refusal-1","model_id":"1","area":"Colgado"}).status_code==403


def test_conteo_manual_verificado_una_vez_y_auditado(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("OPERACIONES_ROPA_AC_ENABLED","1")
        m=web(tmp);assert install(m)
        headers={"x-role":"supervisor","x-store":"Iztapalapa"}
        with TestClient(m.app) as client:
            a=client.post("/api/ac/stock/locations",headers=headers,
                json={"kind":"Piso","aisle":"03","face":"A"})
            assert a.status_code==201,a.text
            loc=a.json()["id"]
            payload={"event_key":"stock-initial-01","location_id":loc,
                     "model_id":"914629","size":"M","pieces":7}
            first=client.post("/api/ac/stock/initial-count",headers=headers,json=payload)
            assert first.status_code==201,first.text
            assert client.post("/api/ac/stock/initial-count",headers=headers,json=payload).json()["id"]==first.json()["id"]
            assert client.post("/api/ac/stock/initial-count",headers=headers,
                json={**payload,"pieces":8}).status_code==400
            assert client.post("/api/ac/stock/initial-count",headers=headers,
                json={**payload,"event_key":"another-01"}).status_code==400
            wrong=client.post("/api/ac/stock/initial-count",headers={"x-role":"gerente","x-store":"Vallejo"},
                json={**payload,"event_key":"from-another-store"})
            assert wrong.status_code==400
            stock=client.get("/api/ac/stock?model_id=914629",headers=headers).json()["stock"]
            assert len(stock)==1 and stock[0]["pieces"]==7
            assert client.post("/api/ac/stock/locations",headers={"x-role":"colaborador_operativo","x-store":"Iztapalapa"},
                json={"kind":"Piso","aisle":"04"}).status_code==403

def test_low_disk_fails_closed_without_changing_roles(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        import ac_production
        monkeypatch.setenv("OPERACIONES_ROPA_AC_ENABLED","1")
        monkeypatch.setattr(ac_production.shutil,"disk_usage",
                            lambda path:SimpleNamespace(free=0))
        m=web(tmp)
        before=m.ROLES
        assert install(m) is False
        assert m.ROLES==before
        assert "gerente" not in m.ROLE_LABELS
        with TestClient(m.app) as client:
            assert client.get("/legacy").status_code==200
            assert client.get("/ac").status_code==404
