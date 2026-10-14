"""Contrato real de Excel/PDF para Bonos -> Modelos a Detalle."""
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from openpyxl import load_workbook

from v322_bonus_model_exports import install


def app_with_sample():
    mock=SimpleNamespace(app=FastAPI(), require_user=lambda request: {"role":"admin"})

    @mock.app.get("/api/bonuses-v313")
    def get_models(request=None,month="",store="",bonus=1):
        return {
            "selected_store":store,
            "month":month,
            "details":[
                {
                    "id_art":"108180","model":"9112","catalog":"Abrigador",
                    "initial_ddi":280,"current_ddi":220,"ddi_reduction_pct":21.4,
                    "initial_existence":243,"current_existence":221,
                    "initial_investment":60507,"current_investment":54001,
                    "investment_reduction_pct":10.7,
                },
                {
                    "id_art":"1203206","model":"880","catalog":"Licencias",
                    "initial_ddi":109,"current_ddi":105,"ddi_reduction_pct":3.67,
                    "initial_existence":150,"current_existence":145,
                    "initial_investment":29000,"current_investment":28000,
                    "investment_reduction_pct":3.44,
                },
            ],
        }
    install(mock)
    return next(r.endpoint for r in mock.app.routes if getattr(r,"path",None)=="/api/bonuses/models-export")


def test_excel_is_real_xlsx_and_respects_catalog():
    export=app_with_sample()
    response=export(request=None,month="2026-10",store="Olivar",bonus=1,catalog="Abrigador",format="xlsx",photos=False)
    assert response.status_code==200
    assert response.body[:2]==b"PK"
    assert response.headers["content-disposition"].endswith('.xlsx"')
    sheet=load_workbook(BytesIO(response.body))["Modelos a Detalle"]
    assert sheet["B5"].value=="108180"
    assert sheet["D5"].value=="Abrigador"
    assert sheet["B6"].value is None


def test_pdf_is_binary_pdf_with_download_header():
    export=app_with_sample()
    response=export(request=None,month="2026-10",store="Olivar",bonus=1,catalog="Licencias",format="pdf",photos=False)
    assert response.status_code==200
    assert response.body.startswith(b"%PDF-")
    assert response.headers["content-disposition"].endswith('.pdf"')


def test_no_models_returns_clear_http_error_without_fake_file():
    export=app_with_sample()
    with pytest.raises(HTTPException) as captured:
        export(request=None,month="2026-10",store="Olivar",bonus=1,catalog="Básicos",format="xlsx",photos=False)
    assert captured.value.status_code==404
    assert "No hay modelos" in captured.value.detail
