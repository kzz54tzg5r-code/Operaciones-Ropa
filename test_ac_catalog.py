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
