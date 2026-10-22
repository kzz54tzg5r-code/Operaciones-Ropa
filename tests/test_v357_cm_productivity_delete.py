"""V357: solo administradores pueden ocultar capturas finalizadas, con auditoría."""
import asyncio
from contextlib import contextmanager
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from v357_cm_productivity_deletion_patch import install


@pytest.fixture
def endpoint(tmp_path):
    filepath = str(tmp_path / "productivity.sqlite")
    def db():
        @contextmanager
        def session():
            con = sqlite3.connect(filepath)
            con.row_factory = sqlite3.Row
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise
            finally:
                con.close()
        return session()
    with db() as con:
        con.execute("""CREATE TABLE cm_productivity_capture(
            id INTEGER PRIMARY KEY,date TEXT,store TEXT,employee_name TEXT,
            pieces REAL,status TEXT,updated_at TEXT
        )""")
        con.execute(
            "INSERT INTO cm_productivity_capture VALUES(1,'2026-10-22','Centro','Persona A',610,'finished','2026-10-22')"
        )
        con.execute(
            "INSERT INTO cm_productivity_capture VALUES(2,'2026-10-22','Centro','Persona B',200,'finished','2026-10-22')"
        )
        con.execute(
            "INSERT INTO cm_productivity_capture VALUES(3,'2026-10-22','Centro','Persona C',0,'active','2026-10-22')"
        )
    actor = {"id": 12, "username": "Auditor", "role": "admin"}
    def user(_request, allowed):
        if actor["role"] not in allowed:
            raise HTTPException(403, "No autorizado")
        return dict(actor)
    app = FastAPI()
    m = SimpleNamespace(app=app, db=db, require_user=user)
    install(m)
    path = next(r.endpoint for r in app.routes if r.path == "/api/cm-productivity/delete-selected")
    class Request:
        def __init__(self, values):
            self.values = values
        async def json(self):
            return self.values
    def run(values):
        return asyncio.run(path(Request(values)))
    return run, db, actor


def test_admin_can_select_one_without_deleting_others(endpoint):
    run, db, actor = endpoint
    result = run({"ids": [1]})
    assert result["ok"] and result["deleted"] == 1
    with db() as con:
        rows = con.execute("SELECT id,status FROM cm_productivity_capture ORDER BY id").fetchall()
        log = con.execute("SELECT capture_id,deleted_by,snapshot_json FROM cm_productivity_deletion_log").fetchone()
    assert [(r["id"],r["status"]) for r in rows] == [(1,"deleted"),(2,"finished"),(3,"active")]
    assert log["capture_id"] == 1 and log["deleted_by"] == "Auditor"
    assert '"pieces": 610.0' in log["snapshot_json"]


def test_reject_unprivileged_and_active_and_atomic_batch(endpoint):
    run, db, actor = endpoint
    actor["role"] = "tienda"
    with pytest.raises(HTTPException) as ex:
        run({"ids": [1]})
    assert ex.value.status_code == 403
    actor["role"] = "superadmin"
    with pytest.raises(HTTPException) as ex:
        run({"ids": [1, 3]})
    assert ex.value.status_code == 409
    with db() as con:
        assert con.execute("SELECT status FROM cm_productivity_capture WHERE id=1").fetchone()[0] == "finished"
        assert con.execute("SELECT COUNT(*) FROM cm_productivity_deletion_log").fetchone()[0] == 0
    with pytest.raises(HTTPException) as ex:
        run({"ids": [1, 1]})
    assert ex.value.status_code == 400
    with pytest.raises(HTTPException) as ex:
        run({"ids": [99]})
    assert ex.value.status_code == 404
    assert run({"ids": [1, 2]})["deleted"] == 2
    with db() as con:
        assert con.execute("SELECT COUNT(*) FROM cm_productivity_deletion_log").fetchone()[0] == 2
