"""V402 · bajas, reactivaciones, alias y compatibilidad con el reporte V400."""
import asyncio
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException

from v402_collaborator_roster_merge import install
from v400_missing_productivity_center_pdf import build_missing


class FakeModule:
    def __init__(self,dbfile):
        self.dbfile=dbfile
        self.app=FastAPI()
        self.actor={"username":"Encargado","role":"admin"}
        self.ops=[
            {"store":"Vallejo","name":"Ana L.","date":"2026-10-25",
             "activity":"Ubicado","pieces":30},
        ]
        with self.db() as con:
            con.execute("""CREATE TABLE operation_collaborators(
                store TEXT, name_key TEXT, name TEXT, active INTEGER,
                first_seen TEXT, last_seen TEXT,last_activity TEXT,
                updated_at TEXT,updated_by TEXT,PRIMARY KEY(store,name_key)
            )""")
            con.executemany(
                "INSERT INTO operation_collaborators VALUES(?,?,?,?,?,?,?,?,?)",
                [
                  ("Vallejo","ana lopez","Ana López",1,"2026-09-02",
                   "2026-10-20","Clasificado","",""),
                  ("Vallejo","ana l.","Ana L.",1,"2026-09-02",
                   "2026-10-25","Ubicado","",""),
                  ("Vallejo","carlos","Carlos",1,"2026-09-03",
                   "2026-10-21","Acondicionado","",""),
                  ("Ecatepec","ana l.","Ana L.",1,"2026-09-02",
                   "2026-10-24","Ubicado","",""),
                ]
            )
    @contextmanager
    def db(self):
        con=sqlite3.connect(self.dbfile)
        con.row_factory=sqlite3.Row
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
    def require_user(self,request,allowed=None):
        if allowed and self.actor["role"] not in allowed:
            raise HTTPException(403,"Sin permiso")
        return self.actor
    def load_ops(self):
        return {"rows":self.ops}

class JsonRequest:
    def __init__(self,data):
        self.data=data
    async def json(self):
        return self.data

def endpoint(module,path):
    return next(r.endpoint for r in module.app.routes if getattr(r,"path","")==path)

@pytest.fixture
def app(tmp_path):
    m=FakeModule(tmp_path/"test.sqlite")
    install(m)
    return m


def test_can_select_inactive_and_audit_without_deleting_captures(app):
    fetch=endpoint(app,"/api/operations/collaborator-admin-v402")
    update=endpoint(app,"/api/operations/collaborator-admin-v402/status")
    assert len(fetch(None)["rows"])==4
    old_ops=list(app.ops)
    r=asyncio.run(update(JsonRequest({"active":False,"items":[
        {"store":"Vallejo","name_key":"Ana Lopez"},
        {"store":"Vallejo","name_key":"Carlos"}]})))
    assert r["changed"]==2
    data=fetch(None)
    assert data["count_active"]==2
    assert data["count_inactive"]==2
    result=build_missing(app,["Vallejo"],"day","2026-10-25")
    assert result["count"]==0  # Ana L. capturó; Carlos y Ana López están de baja
    # El reporte sólo trae el padrón activo; no se borran piezas ni las capturas.
    assert app.ops==old_ops
    with app.db() as con:
        assert con.execute("SELECT count(*) FROM operation_collaborator_admin_audit").fetchone()[0]==2
    r=asyncio.run(update(JsonRequest({"active":True,"items":[
        {"store":"Vallejo","name_key":"ana lopez"}]})))
    assert r["changed"]==1
    names={x["name"] for x in build_missing(app,["Vallejo"],"day","2026-10-25")["rows"]}
    assert names=={"Ana López"}


def test_merge_two_spellings_and_only_count_one_person(app):
    get=endpoint(app,"/api/operations/collaborator-admin-v402")
    merge=endpoint(app,"/api/operations/collaborator-admin-v402/merge")
    before=build_missing(app,["Vallejo"],"day","2026-10-25")
    assert {"Ana López","Carlos"}.issubset({r["name"] for r in before["rows"]})
    r=asyncio.run(merge(JsonRequest({
        "store":"Vallejo","canonical_key":"ana lopez","alias_keys":["ana l."]})))
    assert r["merged"]==1
    after=get(None)
    assert len([r for r in after["rows"] if r["store"]=="Vallejo"])==2
    ana=next(r for r in after["rows"] if r["name"]=="Ana López")
    assert ana["active"]==1
    assert ana["aliases"]==["Ana L."]
    assert ana["last_seen"]=="2026-10-25"
    missing=build_missing(app,["Vallejo"],"day","2026-10-25")
    assert [r["name"] for r in missing["rows"]]==["Carlos"]
    # La actividad de Ana L. se reconoce como la de Ana López; no se suma
    # ni se mueve el registro de la fuente.
    assert app.ops[0]["name"]=="Ana L."
    with app.db() as con:
        assert con.execute(
            "SELECT active FROM operation_collaborators "
            "WHERE store='Vallejo' AND name_key='ana l.'"
        ).fetchone()["active"]==0
        assert con.execute("SELECT count(*) FROM operation_collaborator_admin_audit").fetchone()[0]==1


def test_alias_unification_is_store_scoped_and_rejects_cycles(app):
    merge=endpoint(app,"/api/operations/collaborator-admin-v402/merge")
    bad=JsonRequest({"store":"Ecatepec","canonical_key":"ana l.",
                     "alias_keys":["ana lopez"]})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(merge(bad))
    assert exc.value.status_code==409
    good=JsonRequest({"store":"Vallejo","canonical_key":"ana lopez",
                      "alias_keys":["ana l."]})
    asyncio.run(merge(good))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(merge(good))
    assert exc.value.status_code==409
    report=build_missing(app,["Ecatepec"],"day","2026-10-25")
    assert report["rows"][0]["name"]=="Ana L."


def test_authorization_and_selection_validation(app):
    read=endpoint(app,"/api/operations/collaborator-admin-v402")
    update=endpoint(app,"/api/operations/collaborator-admin-v402/status")
    app.actor={"username":"Tienda","role":"tienda"}
    with pytest.raises(HTTPException) as exc:
        read(None)
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        asyncio.run(update(JsonRequest({"active":False,"items":[
            {"store":"Vallejo","name_key":"carlos"}]})))
    assert exc.value.status_code==403
    app.actor={"username":"Encargado","role":"admin"}
    with pytest.raises(HTTPException) as exc:
        asyncio.run(update(JsonRequest({"active":"false","items":[
            {"store":"Vallejo","name_key":"carlos"}]})))
    assert exc.value.status_code==400
    with pytest.raises(HTTPException) as exc:
        asyncio.run(update(JsonRequest({"active":False,"items":[
            {"store":"Vallejo","name_key":"no existe"}]})))
    assert exc.value.status_code==409


def test_browser_assets_integrated_and_node_valid():
    import subprocess
    root=Path(__file__).resolve().parents[1]
    source=(root/"web"/"index.html").read_text(encoding="utf-8")
    assert 'id="v402RosterManagement"' in source
    assert "window.V402_ROSTER?.mount()" in source
    js=(root/"web"/"colaborador_bajas_unificacion_v402.js").read_text(encoding="utf-8")
    for text in ("v402Deactivate","v402Reactivate","v402Merge",
                 "v402Canonical","v402Status","v402Store","confirm("):
        assert text in js
    syntax=subprocess.run(["node","--check"],input=js,text=True,capture_output=True)
    assert syntax.returncode==0,syntax.stderr
