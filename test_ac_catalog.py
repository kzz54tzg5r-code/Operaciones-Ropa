"""Pruebas de ficha por tienda sin archivos ni servicios reales."""
import pandas as pd
from ac_catalog import ExistingCatalogLookup, from_capacity_frame

def example_frame():
    return pd.DataFrame([
        {"Tienda":"Iztapalapa","ID_ART":"914629","Modelo":"BLUSA BÁSICA",
         "Color":"Rosa","Ubicación detalle":"Pasillo 03 / A"},
        {"Tienda":"Iztapalapa","ID_ART":"914629.0","Modelo":"BLUSA BÁSICA",
         "Color":"Rosa","Ubicación detalle":"Mesa 07"},
        {"Tienda":"Vallejo","ID_ART":"914629","Modelo":"BLUSA BÁSICA",
         "Color":"Azul","Ubicación detalle":"Pasillo 12"},
        {"Tienda":"Iztapalapa","ID_ART":"1322682","Modelo":"CAMISA",
         "Color":"","Ubicación detalle":"Pasillo 02"},
    ])

def test_exact_store_model_and_color():
    info=from_capacity_frame(example_frame(),"IZTAPALAPA","914629")
    assert info["name"]=="BLUSA BÁSICA"
    assert info["color"]=="Rosa"
    assert info["location"]=="Pasillo 03 / A / Mesa 07"

def test_other_store_does_not_leak():
    info=from_capacity_frame(example_frame(),"Vallejo","914629")
    assert info["color"]=="Azul"
    assert info["location"]=="Pasillo 12"
    assert from_capacity_frame(example_frame(),"Ecatepec","914629") is None

def test_missing_color_is_not_invented():
    info=from_capacity_frame(example_frame(),"Iztapalapa","1322682")
    assert info["name"]=="CAMISA"
    assert info["color"] is None

def test_empty_catalog_is_handled():
    assert from_capacity_frame(pd.DataFrame(),"Iztapalapa","914629") is None

def test_lookup_uses_existing_frame_without_writes():
    frame=example_frame()
    catalog=ExistingCatalogLookup(lambda: frame)
    assert catalog("Iztapalapa","914629")["color"]=="Rosa"
    assert len(frame)==4

def test_api_returns_catalog_fields_and_bonos_photo():
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from tempfile import TemporaryDirectory
    from ac_bridge import ACBridge
    from ac_api import create_ac_router
    with TemporaryDirectory() as tmp:
        bridge=ACBridge(tmp)
        bridge.initialize()
        app=FastAPI()
        def actor(request):
            return {"id": 7, "role": "colaborador_operativo",
                    "store": request.headers.get("x-store", "Iztapalapa")}
        app.include_router(create_ac_router(bridge, actor,
                          catalog_lookup=ExistingCatalogLookup(example_frame)))
        with TestClient(app) as client:
            izt=client.get("/api/ac/model?model_id=914629")
            assert izt.status_code==200
            assert izt.json()["name"]=="BLUSA BÁSICA"
            assert izt.json()["color"]=="Rosa"
            assert izt.json()["location"]=="Pasillo 03 / A / Mesa 07"
            assert izt.json()["photo_url"]=="/api/bonuses/product-photo/914629"
            vall=client.get("/api/ac/model?model_id=914629",
                            headers={"x-store":"Vallejo"}).json()
            assert vall["color"]=="Azul"
            assert vall["location"]=="Pasillo 12"
            missing=client.get("/api/ac/model?model_id=914629",
                               headers={"x-store":"Ecatepec"}).json()
            assert missing["name"] is None
            assert missing["photo_url"]=="/api/bonuses/product-photo/914629"

