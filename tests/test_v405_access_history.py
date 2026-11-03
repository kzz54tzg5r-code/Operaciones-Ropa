"""V405 historial de ingreso opción 4: registros reales, privacidad y roles."""
import contextlib
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import pandas as pd
import pytest
from fastapi import FastAPI, HTTPException
from pypdf import PdfReader

from v405_user_access_history import install,record_event,query,_window


class Backend:
    def __init__(self,path):
        self.path=path
        self.app=FastAPI()
        self.role="superadmin"
        self.pd=pd
        with self.db() as con:
            con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,role TEXT,store TEXT,active INTEGER)")
            con.executemany("INSERT INTO users VALUES(?,?,?,?,1)",[
                (1,"Diana Loa","admin","Vallejo"),
                (2,"Gustavo Camargo","director",""),
                (3,"Propietario","superadmin",""),
            ])
        install(self)

    @contextlib.contextmanager
    def db(self):
        con=sqlite3.connect(self.path)
        con.row_factory=sqlite3.Row
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def require_real_superadmin(self,req):
        if self.role!="superadmin":
            raise HTTPException(403,"No autorizado")
        return {"role":"superadmin"}

    def current_user(self,req):
        return {"role":self.role}

class FakeRequest:
    headers={"user-agent":"Mozilla/5.0 (Windows NT 10.0) Chrome/122"}
    client=SimpleNamespace(host="192.168.5.81")

def endpoint(m,suffix):
    return next(r.endpoint for r in m.app.routes if r.path==suffix)

@pytest.fixture
def m(tmp_path):
    return Backend(tmp_path/"audit.sqlite3")


def test_owner_only_and_exact_counters(m):
    req=FakeRequest()
    users=[
        {"id":1,"username":"Diana Loa","role":"admin","store":"Vallejo"},
        {"id":2,"username":"Gustavo Camargo","role":"director","store":""},
    ]
    for _ in range(3):
        record_event(m,req,"login_success",user=users[0])
    record_event(m,req,"login_success",user=users[1])
    record_event(m,req,"login_failed",username="cuenta-desconocida")
    record_event(m,req,"logout",user=users[0])
    record_event(m,req,"password_reset",user=users[0])
    result=query(m)
    assert result["total"]==7
    assert result["successful"]==4
    assert result["unique_users"]==2
    assert result["failed"]==1
    assert result["closed"]==1
    assert result["resets"]==1
    assert result["recent"][0]["username"] in ("Diana Loa","Gustavo Camargo")
    assert {r["username"] for r in result["recent"]}=={"Diana Loa","Gustavo Camargo"}
    assert all(r["ip_mask"]=="192.168.5.×" for r in result["rows"])
    assert all("password" not in r for r in result["rows"])
    e=endpoint(m,"/api/admin/access-history-v405")
    assert e(req)["total"]==7
    m.role="admin"
    with pytest.raises(HTTPException) as error:
        e(req)
    assert error.value.status_code==403
    m.role="director"
    with pytest.raises(HTTPException):
        e(req)


def test_filters_are_bound_and_period_is_local_mexico(m):
    req=FakeRequest()
    u={"id":1,"username":"Diana Loa","role":"admin","store":"Vallejo"}
    record_event(m,req,"login_success",user=u)
    today=datetime.now(ZoneInfo("America/Mexico_City")).date()
    assert _window("day",today.isoformat())[2:]==(today.isoformat(),today.isoformat())
    monday=today.fromisocalendar(*today.isocalendar()[:2],1)
    a,b,first,last=_window("week",today.isoformat())
    assert first==monday.isoformat()
    assert last==(monday.replace() + __import__("datetime").timedelta(days=6)).isoformat()
    assert query(m,username="Diana Loa")["successful"]==1
    assert query(m,username="Diana Loa' OR 1=1 --")["successful"]==0
    assert query(m,role="director")["total"]==0
    assert query(m,store="Vallejo")["successful"]==1
    with pytest.raises(HTTPException):
        query(m,page_size=200)
    with pytest.raises(HTTPException):
        query(m,period="nonsense")


def test_exports_are_separately_authorized_and_preserve_entries(m):
    req=FakeRequest()
    record_event(m,req,"login_success",user={"id":1,"username":"Diana Loa","role":"admin","store":"Vallejo"})
    exp=endpoint(m,"/api/admin/access-history-v405/export")
    xlsx=exp(req,format="xlsx")
    excel=pd.read_excel(BytesIO(xlsx.body))
    assert "Diana Loa" in set(excel["Usuario"])
    assert "IP anonimizada" in excel.columns
    assert "password_hash" not in excel.columns
    pdf=exp(req,format="pdf")
    doc=PdfReader(BytesIO(pdf.body))
    assert "Historial de ingresos" in doc.pages[0].extract_text()
    assert "Diana Loa" in doc.pages[0].extract_text()
    m.role="admin"
    with pytest.raises(HTTPException) as error:
        exp(req,format="pdf")
    assert error.value.status_code==403


def test_ui_is_real_and_not_accessible_through_client_only_gate():
    root=Path(__file__).resolve().parents[1]
    page=(root/"web/index.html").read_text("utf-8")
    js=(root/"web/access_history_option4_v405.js").read_text("utf-8")
    server=(root/"web_app.py").read_text("utf-8")
    assert '<div id="v405AccessHistory" class="superOnly hidden">' in page
    assert "window.V405_ACCESS?.mount(USER?.role)" in page
    assert "login_success" in server and "login_failed" in server
    assert "record_event" in server and "password_reset" in server
    for title in ("Usuarios registrados y últimos accesos","Resumen de accesos","Alertas de seguridad","Bitácora completa de accesos"):
        assert title in js
    assert "100" in (root/"v405_user_access_history.py").read_text("utf-8")
    import subprocess
    result=subprocess.run(["node","--check"],input=js,text=True,capture_output=True)
    assert result.returncode==0,result.stderr


def test_preexisting_authenticated_session_is_real_activity_not_fake_login(m):
    """La sesión vigente se registra una sola vez y no aumenta ingresos."""
    req=FakeRequest()
    req.session={}
    m._session_user_row=lambda request:{
        "id":1,"username":"Diana Loa","role":"admin","store":"Vallejo"
    }
    observe=endpoint(m,"/api/access/session-observed-v408")
    first=observe(req)
    again=observe(req)
    assert first=={"ok":True,"recorded":True}
    assert again=={"ok":True,"recorded":False}
    stats=query(m)
    assert stats["observed"]==1
    assert stats["successful"]==0
    assert stats["unique_users"]==1
    assert stats["recent"][0]["username"]=="Diana Loa"
    assert stats["recent"][0]["accesses"]==0
    assert stats["recent"][0]["observed"]==1
    assert stats["rows"][0]["event"]=="session_observed"
    assert stats["rows"][0]["ip_mask"]=="192.168.5.×"
    # El endpoint de observación acepta a cualquier usuario autenticado,
    # pero la bitácora de administración sigue siendo solo Super Administrador.
    m.role="admin"
    assert observe(req)["recorded"] is False
    with pytest.raises(HTTPException) as exc:
        endpoint(m,"/api/admin/access-history-v405")(req)
    assert exc.value.status_code==403
    req.session={}
    m._session_user_row=lambda request:None
    with pytest.raises(HTTPException) as exc:
        observe(req)
    assert exc.value.status_code==401


def test_empty_period_shows_registered_users_but_no_invented_accesses(m):
    result=query(m)
    assert result["total"]==0
    assert result["successful"]==0
    assert result["observed"]==0
    assert result["unique_users"]==0
    assert len(result["recent"])==3
    assert {r["username"] for r in result["recent"]}=={
        "Diana Loa","Gustavo Camargo","Propietario"}
    assert all(r["accesses"]==0 and r["observed"]==0
               and r["latest"] is None and r["unrecorded"]
               for r in result["recent"])
    result=query(m,role="admin")
    assert [r["username"] for r in result["recent"]]==["Diana Loa"]
    assert result["total"]==0



def test_owner_query_recovers_preexisting_session_and_lists_other_users(m):
    """La consulta del propietario observa la sesión real; otras cuentas no desaparecen."""
    req=FakeRequest()
    req.session={}
    m._session_user_row=lambda _req:{
        "id":3,"username":"Propietario","role":"superadmin","store":""
    }
    history=endpoint(m,"/api/admin/access-history-v405")
    first=history(req)
    second=history(req)
    assert first["successful"]==0
    assert first["observed"]==1
    assert second["observed"]==1  # sin duplicar
    assert req.session["v408_audit_seen"] is True
    users={row["username"]:row for row in second["recent"]}
    assert {"Propietario","Diana Loa","Gustavo Camargo"} <= set(users)
    assert users["Propietario"]["observed"]==1
    assert users["Propietario"]["accesses"]==0
    assert users["Diana Loa"]["accesses"]==0
    assert users["Diana Loa"]["latest"] is None
    m.role="admin"
    with pytest.raises(HTTPException) as exc:
        history(req)
    assert exc.value.status_code==403
