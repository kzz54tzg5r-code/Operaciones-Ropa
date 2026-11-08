"""Laboratorio AC: órdenes accesibles únicamente a perfiles autorizados por tienda."""
import tempfile
from io import BytesIO
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from openpyxl import Workbook
from ac_bridge import ACBridge
from ac_api import create_ac_router


def excel():
    book=Workbook();sheet=book.active
    sheet.append(["TIENDA","ID_ART","TALLA","CURVA","CAPACIDAD"])
    sheet.append(["Iztapalapa","914629","M",18,20])
    out=BytesIO();book.save(out);book.close()
    return out.getvalue()


def actor(request: Request):
    return {"role":request.headers.get("x-role","colaborador_operativo"),
            "id":request.headers.get("x-user","C1"),
            "store":request.headers.get("x-store","Iztapalapa")}


def test_api_approval_restricts_role_and_store():
    with tempfile.TemporaryDirectory() as temp:
        bridge=ACBridge(temp);bridge.initialize()
        bridge.upload_capacities(excel(),version="A",admin_user="admin")
        floor=bridge.operation.add_location(store="Iztapalapa",kind="Piso",aisle="03")
        sept=bridge.operation.add_location(store="Iztapalapa",kind="Septimos",aisle="07",level="2")
        bridge.operation.seed_verified_stock(store="Iztapalapa",location_id=floor,
            model_id="914629",sizes={"M":8})
        bridge.operation.seed_verified_stock(store="Iztapalapa",location_id=sept,
            model_id="914629",sizes={"M":12})
        app=FastAPI();app.include_router(create_ac_router(bridge,actor))
        with TestClient(app) as client:
            worker={"x-role":"colaborador_operativo","x-user":"C1"}
            supervisor={"x-role":"supervisor","x-user":"SUP"}
            manager={"x-role":"gerente","x-user":"GER"}
            payload={"event_key":"approved-order-001","model_id":"914629",
                     "area":"Colgado","sizes":["M"]}
            assert client.get("/api/ac/orders/preview?model_id=914629&area=Colgado",
                              headers=worker).status_code==403
            assert client.post("/api/ac/orders/approve",headers=worker,json=payload).status_code==403
            data=client.get("/api/ac/orders/preview?model_id=914629&area=Colgado",
                            headers=supervisor)
            assert data.status_code==200
            assert data.json()["total"]==10
            wrong=client.get("/api/ac/orders/preview?model_id=914629&area=Colgado",
                             headers={**supervisor,"x-store":"Vallejo"})
            assert wrong.status_code==400  # Sin corte de capacidades de esa tienda
            issued=client.post("/api/ac/orders/approve",headers=manager,json=payload)
            assert issued.status_code==201,issued.text
            oid=issued.json()["id"]
            assert issued.json()["total"]==10
            retry=client.post("/api/ac/orders/approve",headers=manager,json=payload)
            assert retry.status_code==201 and retry.json()["id"]==oid
            conflict=client.post("/api/ac/orders/approve",headers=supervisor,json=payload)
            assert conflict.status_code==400
            assert client.get("/api/ac/orders",headers=manager).json()["orders"][0]["id"]==oid
            assert client.get("/api/ac/orders",headers={**manager,"x-store":"Vallejo"}).json()["orders"]==[]
            sid=client.post("/api/ac/session/start",headers=worker,json={
                "flow":"Resurtido","stage":"Pizca","area":"Colgado"}).json()["session_id"]
            queue=client.get("/api/ac/tasks?session_id="+sid,headers=worker)
            assert queue.status_code==200
            assert queue.json()["tasks"][0]["remaining"]=={"M":10}
            assert queue.json()["tasks"][0]["source_location"]["kind"]=="Septimos"
            loc=client.get("/api/ac/locations?kind=Piso",headers=worker)
            assert loc.status_code==200
            assert loc.json()["locations"][0]["id"]==floor
            assert client.post("/api/ac/orders/approve",headers={**manager,"origin":"https://example.org"},
                json={**payload,"event_key":"approved-order-002"}).status_code==403
