"""V327: new Bono 2 cohort and reporting, independent of Bono 1."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI, HTTPException
from openpyxl import load_workbook
from io import BytesIO
from types import SimpleNamespace

from v327_bonus2_zero_sales_patch import qualify_bono2_rows, build_bono2_cohort, install as install_bono2
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
    assert [r["id_art"] for r in rows]==["10003","10005"]
    assert [r["catalog"] for r in rows]==["Básicos","Básicos"]
    assert [r["arrival_age_days"] for r in rows]==[7,8]
    assert all(r["sales_30"]==0 for r in rows)
    assert [r["initial_ddi"] for r in rows]==[300,390]
    assert all(r["current_ddi"] is None for r in rows)
    assert all(r["last_arrival"] <= "2026-10-06" for r in rows)


def test_unknown_sales_dates_or_missing_headers_do_not_count_as_zero():
    x=raw_fixture()
    x.loc[0,"VTA EN PZAS 30"]=None
    x.loc[1,"ULTIMA ENTRADA CEDIS A TIENDA"]="2026-10-05"
    assert [r["id_art"] for r in qualify_bono2_rows(x,date(2026,10,13),Path("x.xlsx"))]==["10002","10003","10005"]
    with pytest.raises(ValueError,match="Columnas de Capacidades"):
        qualify_bono2_rows(x.drop(columns=["VTA EN PZAS 30"]),date(2026,10,13),Path("x.xlsx"))


def test_bono2_exports_use_independent_filtered_rows_not_bono1():
    app=FastAPI()
    model={"id_art":"10001","model":"M1","catalog":"Licencias","sales_30":0,
           "last_arrival":"2026-10-05","arrival_age_days":8,"initial_ddi":135,
           "initial_existence":10,"initial_investment":1250}
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
    assert sheet["F5"].value=="2026-10-05"
    assert sheet["H5"].value==135
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


def test_arrival_stays_with_correct_id_when_nonmatching_rows_are_interspersed():
    source=raw_fixture()
    # Sólo ID 10003 y 10005 cumplen edad >=7 días y cero ventas.
    source.loc[0,"TIPO CATALOGO MAX VIG"]="DESCONTINUADO"
    source.loc[0,"ULTIMA ENTRADA CEDIS A TIENDA"]=""
    source.loc[3,"ULTIMA ENTRADA CEDIS A TIENDA"]=""
    out=qualify_bono2_rows(source,date(2026,10,13),Path("Capacidades.xlsx"))
    assert [r["id_art"] for r in out]==["10003","10005"]
    assert [r["last_arrival"] for r in out]==["2026-10-06","2026-10-05"]
    assert [r["arrival_age_days"] for r in out]==[7,8]


def test_date_boundary_rejects_6_days_accepts_7_and_older():
    x=raw_fixture()
    # 6 days = recent shipment, 7 days = full week, 8 days = older.
    x.loc[1,"ULTIMA ENTRADA CEDIS A TIENDA"]="2026-10-07"
    x.loc[2,"ULTIMA ENTRADA CEDIS A TIENDA"]="2026-10-06"
    x.loc[4,"ULTIMA ENTRADA CEDIS A TIENDA"]="2026-10-05"
    ids=[r["id_art"] for r in qualify_bono2_rows(x,date(2026,10,13),Path("initial.xlsx"))]
    assert "10002" not in ids
    assert "10003" in ids and "10005" in ids


def test_same_id_cannot_pass_if_another_variant_sold_or_arrived_recently(tmp_path):
    base=raw_fixture().copy()
    variants=base.iloc[[2,4]].copy()
    variants.iloc[0,variants.columns.get_loc("ULTIMA ENTRADA CEDIS A TIENDA")]="2026-10-12"
    variants.iloc[1,variants.columns.get_loc("VTA EN PZAS 30")]=2
    frame=pd.concat([base,variants],ignore_index=True)
    initial=tmp_path/"Capacidades_13.10.26.xlsx"
    frame.to_excel(initial,index=False)
    rows=build_bono2_cohort(initial,date(2026,10,13))
    assert "10003" not in {r["id_art"] for r in rows}
    assert "10005" not in {r["id_art"] for r in rows}


def test_bono2_uses_assigned_prior_month_initial_cut_not_latest_cut(tmp_path):
    """An Oct bono must honor Sep 29 assigned initial despite Oct 13 current."""
    import time
    initial=tmp_path/"Capacidades_29.09.26.xlsx"
    original=raw_fixture()
    # For the initial date Sep 29, the 7-day rule accepts a Sep 21 shipment.
    original["ULTIMA ENTRADA CEDIS A TIENDA"]="2026-09-21"
    original.to_excel(initial,index=False)
    opening_entry={"id":"initial_oct_2026","name":initial.name,"path":str(initial)}
    latest_entry={"id":"current_oct_2026","name":"Capacidades_13.10.26.xlsx"}
    calls=[]
    def select_cut(month):
        calls.append(month)
        return (date(2026,9,29),"",opening_entry)
    m=SimpleNamespace(
        app=FastAPI(), DATA_ROOT=tmp_path,COMMERCIAL_DATA_ROOT=tmp_path,
        require_user=lambda request:{"role":"admin"},
        store_names=lambda active_only=True:["Olivar"],
        resolve_entry_path=lambda entry:Path(entry["path"]),
        _capacity_report_date=lambda entry:date(2026,9,29),
        _sales_bonus_opening_capacity_v293=select_cut,
        _release_process_memory=lambda:None,
    )
    install_bono2(m)
    endpoint=next(r.endpoint for r in m.app.routes if getattr(r,"path",None)=="/api/bonuses-b2-v327")
    response=endpoint(None,"2026-10","Olivar")
    assert response["cutoff_date"]=="2026-09-29"
    assert response["cutoff_name"]==initial.name
    assert response["source_dates"]["current_capacity"]==""
    assert calls==["2026-10"]
    # Background scanner may need time to finish its first read.
    for _ in range(100):
        if response["b2_status"]!="pending":
            break
        time.sleep(0.05)
        response=endpoint(None,"2026-10","Olivar")
    assert response["b2_status"]=="ready",response.get("source_error")
    assert response["b2_stats"]["models"]>0
    assert all(r["arrival_age_days"]>=7 for r in response["details"])
    assert all(r["sales_30"]==0 for r in response["details"])
