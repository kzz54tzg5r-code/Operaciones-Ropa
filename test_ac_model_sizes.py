"""AC: un ID distinto tiene su propio rango de tallas del corte de capacidades."""
from io import BytesIO
from tempfile import TemporaryDirectory

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from openpyxl import Workbook

from ac_bridge import ACBridge
from ac_api import create_ac_router


def book(rows):
    wb=Workbook()
    sheet=wb.active
    sheet.append(["TIENDA","ID_ART","TALLA","CURVA","CAPACIDAD"])
    for row in rows:
        sheet.append(row)
    buf=BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def sample_rows():
    return [
        ("Iztapalapa","1334087","13/14",2,4),
        ("Iztapalapa","1334087","7/8",2,4),
        ("Iztapalapa","1334087","11/12",2,4),
        ("Iztapalapa","1334087","9/10",2,4),
        ("Iztapalapa","1224000","9/10",2,3),
        ("Iztapalapa","1224000","11/12",2,3),
        ("Vallejo","1334087","XCH",2,4),
        ("Vallejo","1334087","CH",2,4),
    ]


def test_model_sizes_are_specific_to_store_model_and_one_version():
    with TemporaryDirectory() as folder:
        bridge=ACBridge(folder);bridge.initialize()
        bridge.upload_capacities(book(sample_rows()),version="Corte1",admin_user="admin")
        kids=bridge.capacities.model_sizes("Iztapalapa","1334087")
        assert [x["size"] for x in kids["sizes"]]==["7/8","9/10","11/12","13/14"]
        assert kids["from_size"]=="7/8"
        assert kids["to_size"]=="13/14"
        assert kids["version"]=="Corte1"
        smaller=bridge.capacities.model_sizes("Iztapalapa","1224000")
        assert [x["size"] for x in smaller["sizes"]]==["9/10","11/12"]
        vallejo=bridge.capacities.model_sizes("Vallejo","1334087")
        assert [x["size"] for x in vallejo["sizes"]]==["XCH","CH"]
        assert bridge.capacities.model_sizes("Ecatepec","1334087")["status"]=="not_found"
        assert bridge.capacities.model_sizes("Iztapalapa","inexistente")["sizes"]==[]
        # El corte nuevo reemplaza el rango de este modelo; NO mezcla
        # tallas descontinuadas de la versión anterior.
        bridge.upload_capacities(book([
            ("Iztapalapa","1334087","7/8",3,5),
            ("Iztapalapa","1334087","11/12",3,5)
        ]),version="Corte2",admin_user="admin")
        current=bridge.capacities.model_sizes("Iztapalapa","1334087")
        assert current["version"]=="Corte2"
        assert [x["size"] for x in current["sizes"]]==["7/8","11/12"]


def test_model_sizes_endpoint_uses_authenticated_store():
    with TemporaryDirectory() as folder:
        bridge=ACBridge(folder);bridge.initialize()
        bridge.upload_capacities(book(sample_rows()),version="Corte1",admin_user="admin")
        def actor(request: Request):
            return {"id":"2","role":"tienda","store":request.headers.get("x-store","Iztapalapa")}
        app=FastAPI();app.include_router(create_ac_router(bridge,actor))
        with TestClient(app) as client:
            result=client.get("/api/ac/capacity/model-sizes?model_id=1334087")
            assert result.status_code==200, result.text
            assert result.json()["sizes"][0]["size"]=="7/8"
            other=client.get("/api/ac/capacity/model-sizes?model_id=1334087",
                             headers={"x-store":"Vallejo"})
            assert [x["size"] for x in other.json()["sizes"]]==["XCH","CH"]
            assert client.get("/api/ac/capacity/model-sizes?model_id=1334087",
                              headers={"x-store":""}).status_code==403
