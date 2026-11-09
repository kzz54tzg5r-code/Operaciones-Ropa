"""AC photo regression: an authorized administrator can query Bonos photos
without an active store; capacities remain store-scoped. No real user data."""
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from ac_bridge import ACBridge
from ac_api import create_ac_router


def actor(req: Request):
    role=req.headers.get("x-role")
    if not role:
        raise HTTPException(401, "Session required")
    return {"id":"ac-test-1", "role":role, "store":req.headers.get("x-store","")}


def make_client(temp, catalog=None):
    bridge=ACBridge(Path(temp))
    bridge.initialize()
    app=FastAPI()
    app.include_router(create_ac_router(bridge, actor, catalog_lookup=catalog))
    return TestClient(app)


def test_admin_without_store_can_fetch_bonus_photo_address():
    with TemporaryDirectory() as folder:
        with make_client(folder) as client:
            admin={"x-role":"admin"}
            reply=client.get("/api/ac/model?model_id=1328808",headers=admin)
            assert reply.status_code==200,reply.text
            assert reply.json()["photo_url"]=="/api/bonuses/product-photo/1328808"
            assert reply.json()["name"] is None
            # Inventory sizes still require a store chosen and signed by the app.
            caps=client.get("/api/ac/capacity/model-sizes?model_id=1328808",headers=admin)
            assert caps.status_code==403
            assert "tienda" in caps.text.lower()
            assert client.get("/api/ac/model?model_id=1328808").status_code==401
            assert client.get("/api/ac/model?model_id=1328808",
                    headers={"x-role":"colaborador_operativo"}).status_code==403


def test_catalog_failure_does_not_remove_bonos_photo():
    def faulty_catalog(store,model):
        raise RuntimeError("Catalog temporarily unavailable")
    with TemporaryDirectory() as folder:
        with make_client(folder,catalog=faulty_catalog) as client:
            res=client.get("/api/ac/model?model_id=1328808",
                           headers={"x-role":"admin","x-store":"Iztapalapa"})
            assert res.status_code==200,res.text
            assert res.json()["photo_url"]=="/api/bonuses/product-photo/1328808"
            assert res.json()["location"] is None


def test_catalog_metadata_keeps_store_scope_but_photo_is_same():
    calls=[]
    def scoped(store,model):
        calls.append((store,model))
        return {"name":"Prenda", "color":"Azul", "location":"Pasillo 2"}
    with TemporaryDirectory() as folder:
        with make_client(folder,catalog=scoped) as client:
            for store in ["Iztapalapa","Vallejo"]:
                response=client.get("/api/ac/model?model_id=1328808",
                                    headers={"x-role":"tienda","x-store":store})
                assert response.status_code==200,response.text
                assert response.json()["photo_url"]=="/api/bonuses/product-photo/1328808"
                assert response.json()["location"]=="Pasillo 2"
            assert calls==[("Iztapalapa","1328808"),("Vallejo","1328808")]
            no_store=client.get("/api/ac/model?model_id=1328808",
                                headers={"x-role":"superadmin"})
            assert no_store.status_code==200
            assert no_store.json()["photo_url"]=="/api/bonuses/product-photo/1328808"
            assert calls==[("Iztapalapa","1328808"),("Vallejo","1328808")]


def test_photo_uses_exact_numeric_id_only():
    with TemporaryDirectory() as folder:
        with make_client(folder) as client:
            resp=client.get("/api/ac/model?model_id=INV%C3%81LIDO",
                            headers={"x-role":"admin"})
            assert resp.status_code==200
            assert resp.json()["photo_url"] is None
            assert resp.json()["photo_status"]=="invalid_photo_id"
