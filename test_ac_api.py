"""Pruebas sin Render ni usuarios reales: FastAPI con sesiones simuladas, SQLite temporal."""
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from openpyxl import Workbook
from ac_api import create_ac_router
from ac_bridge import ACBridge

def actor(req: Request):
    role=req.headers.get("x-test-role")
    if not role:
        raise HTTPException(401,"Sesión requerida")
    return {"role":role,"store":req.headers.get("x-test-store","Iztapalapa"),
            "id":req.headers.get("x-test-user","123"),"username":"PRUEBAS"}

def xlsx():
    book=Workbook()
    sheet=book.active
    sheet.append(["TIENDA","ID_ART","TALLA","CURVA","CAPACIDAD"])
    sheet.append(["Iztapalapa","914629","M",18,20])
    out=BytesIO();book.save(out);book.close()
    return out.getvalue()

class TestCaptureAPI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.bridge=ACBridge(Path(self.temp.name))
        self.bridge.initialize()
        app=FastAPI()
        app.include_router(create_ac_router(self.bridge,actor))
        self.client=TestClient(app)
        self.user={"x-test-role":"colaborador","x-test-store":"Iztapalapa","x-test-user":"123"}

    def tearDown(self):
        self.client.close();self.temp.cleanup()

    def test_login_required_and_role_restrictions(self):
        self.assertEqual(self.client.get("/api/ac/me").status_code,401)
        self.assertEqual(self.client.post("/api/ac/session/start",
                         headers={"x-test-role":"director"},json={
                         "flow":"Surtido","stage":"Separar","area":"Colgado"}).status_code,403)

    def test_sessions_and_capture_idempotency(self):
        started=self.client.post("/api/ac/session/start",headers=self.user,json={
            "flow":"Surtido","stage":"Separar","area":"Colgado"})
        self.assertEqual(started.status_code,201,started.text)
        sid=started.json()["session_id"]
        self.assertEqual(self.client.post("/api/ac/session/start",headers=self.user,json={
            "flow":"Surtido","stage":"Separar","area":"Colgado"}).json()["session_id"],sid)
        payload={"session_id":sid,"event_key":"scan-123456","model_id":"914629",
                 "sizes":{"XCH":5,"M":7,"G":6}}
        first=self.client.post("/api/ac/capture",headers=self.user,json=payload)
        self.assertEqual(first.status_code,201,first.text)
        second=self.client.post("/api/ac/capture",headers=self.user,json=payload)
        self.assertEqual(second.json()["capture_id"],first.json()["capture_id"])
        third=self.client.post("/api/ac/capture",headers=self.user,
            json={**payload,"sizes":{"XCH":99}})
        self.assertEqual(third.status_code,400)
        foreign=self.client.post("/api/ac/capture",headers={**self.user,"x-test-store":"Vallejo"},json=payload)
        self.assertEqual(foreign.status_code,403)
        self.assertEqual(self.client.get("/api/ac/session/active",headers=self.user).json()["session"]["id"],sid)
        self.assertEqual(self.client.post("/api/ac/session/finish",headers=self.user,json={"session_id":sid}).status_code,200)

    def test_capacity_upload_only_admin_and_no_fake_photo(self):
        invalid=self.client.post("/api/ac/capacity/upload?version=A",headers=self.user,
                                 files={"file":("curve.xlsx",xlsx(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        self.assertEqual(invalid.status_code,403)
        result=self.client.post("/api/ac/capacity/upload?version=A",
            headers={"x-test-role":"admin","x-test-user":"9"},
            files={"file":("curve.xlsx",xlsx(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        self.assertEqual(result.status_code,201,result.text)
        meta=self.client.get("/api/ac/model?model_id=914629",headers=self.user)
        self.assertEqual(meta.status_code,200)
        self.assertIsNone(meta.json()["photo_url"])
        self.assertEqual(meta.json()["photo_status"],"catalog_not_connected")

    def test_cross_site_post_blocked(self):
        result=self.client.post("/api/ac/session/start",
            headers={**self.user,"origin":"https://evil.example"},
            json={"flow":"Surtido","stage":"Separar","area":"Colgado"})
        self.assertEqual(result.status_code,403)

if __name__=="__main__":
    unittest.main()
