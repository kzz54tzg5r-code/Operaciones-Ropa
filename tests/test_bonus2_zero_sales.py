"""V327: new Bono 2 cohort and reporting, independent of Bono 1."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI, HTTPException
from openpyxl import load_workbook
from io import BytesIO
from types import SimpleNamespace

from v327_bonus2_zero_sales_patch import qualify_bono2_rows
from v322_bonus_model_exports import install as install_export


def raw_fixture():
    return pd.DataFrame({
        "TIENDA": ["OLIVAR DEL CONDE"] * 9,
        "ID_ART": [str(10001+i) for i in range(9)],
        "MODELO": [f"M{i}" for i in range(9)],
        "CATALOGO": [
            "LICENCIAS | DIG | 2026", "COL IMP | ABRIGADOR | 2026",
            "BASICOS | OTO-INV | 2026", "LICENCIAS | DIG | 2026",
            "BASICOS | OTO-INV | 2026", "BASICOS | OTO-INV | 2026",
            "BASICOS | OTO-INV | 2026", "BASICOS | OTO-INV | 2026",
            "OTRO | DIG | 2026",
        ],
        "TIPO CATALOGO MAX VIG": [
            "VIGENTE","VIGENTE","VIGENTE","VIGENTE","VIGENTE",
            "DESCONTINUADO","VIGENTE","VIGENTE","VIGENTE",
        ],
        "VTA EN PZAS 30": [0,0,0,4,0,0,None,0,0],
        "ULTIMA ENTRADA CEDIS A TIENDA": [
            "2026-10-13","2026-10-08","2026-10-06",
            "2026-10-11","2026-10-05","2026-10-14",
            "2026-10-12","","2026-10-14",
        ],
        "DIAS DE INVENTARIO SUG 7": [135,200,300,150,390,180,111,135,100],
        "EXISTENCIA TOTAL": [10]*9,
        "PRECIO MAYOREO": [125]*9,
    })


def test_bono2_zero_sales_and_arrival_age_including_day_7():
    rows=qualify_bono2_rows(raw_fixture(),date(2026,10,13),Path("Capacidades_13.10.26.xlsx"))
    assert [r["id_art"] for r in rows]==["10001","10002","10003"]
    assert [r["catalog"] for r in rows]==["Licencias","Abrigador","Básicos"]
    assert [r["arrival_age_days"] for r in rows]==[0,5,7]
    assert all(r["sales_30"]==0 for r in rows)
    assert all(r["initial_ddi"] is None for r in rows)


def test_unknown_sales_dates_or_missing_headers_do_not_count_as_zero():
    x=raw_fixture()
    x.loc[0,"VTA EN PZAS 30"]=None
    x.loc[1,"ULTIMA ENTRADA CEDIS A TIENDA"]="2026-10-05"
    assert [r["id_art"] for r in qualify_bono2_rows(x,date(2026,10,13),Path("x.xlsx"))]==["10003"]
    with pytest.raises(ValueError,match="Columnas de Capacidades"):
        qualify_bono2_rows(x.drop(columns=["VTA EN PZAS 30"]),date(2026,10,13),Path("x.xlsx"))


def test_bono2_exports_use_independent_filtered_rows_not_bono1():
    app=FastAPI()
    model={"id_art":"10001","model":"M1","catalog":"Licencias","sales_30":0,
           "last_arrival":"2026-10-13","arrival_age_days":0,"current_ddi":135,
           "current_existence":10,"current_investment":1250}
    m=SimpleNamespace(app=app,require_user=lambda request:{"role":"admin"},
      _v327_bonus2_payload=lambda request,month,store:{
         "b2_status":"ready","details":[model],"selected_store":store,"month":month,
      })
    install_export(m)
    exp=next(r.endpoint for r in app.routes if getattr(r,"path",None)=="/api/bonuses/models-export")
    result=exp(None,"2026-10","Olivar",2,"Licencias","xlsx",False)
    assert result.status_code==200
    sheet=load_workbook(BytesIO(result.body)).active
    assert sheet["B5"].value=="10001"
    assert sheet["E5"].value==0
    assert sheet["F5"].value=="2026-10-13"
    pdf=exp(None,"2026-10","Olivar",2,"Licencias","pdf",False)
    assert pdf.body.startswith(b"%PDF-")
    assert pdf.status_code==200


def test_bono2_export_pending_gives_clear_409():
    app=FastAPI()
    m=SimpleNamespace(app=app,require_user=lambda request:{"role":"admin"},
     _v327_bonus2_payload=lambda request,month,store:{"b2_status":"pending","details":[]})
    install_export(m)
    exp=next(r.endpoint for r in app.routes if getattr(r,"path",None)=="/api/bonuses/models-export")
    with pytest.raises(HTTPException) as err:
        exp(None,"2026-10","Olivar",2,"Licencias","xlsx",False)
    assert err.value.status_code==409
