"""V401: la respuesta 520 del proxy no pierde un Excel ya recibido/publicado."""
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import sqlite3
import subprocess

import pytest
from fastapi import HTTPException

import web_app


@pytest.fixture
def isolated_upload_db(monkeypatch,tmp_path):
    filepath=tmp_path/"upload-regression.sqlite3"
    with sqlite3.connect(filepath) as con:
        con.executescript("""
        CREATE TABLE upload_jobs(
          id TEXT PRIMARY KEY,module TEXT,filename TEXT,status TEXT,progress INTEGER,
          message TEXT,error TEXT,result_json TEXT,created_at TEXT,
          started_at TEXT,finished_at TEXT,created_by TEXT,resume_count INTEGER);
        CREATE TABLE upload_history(
          id INTEGER PRIMARY KEY,module TEXT,filename TEXT,valid_records INTEGER,
          rejected_records INTEGER,period_detected TEXT,published INTEGER,job_id TEXT);
        """)
    @contextmanager
    def test_db():
        con=sqlite3.connect(filepath)
        con.row_factory=sqlite3.Row
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
    monkeypatch.setattr(web_app,"db",test_db)
    return test_db


def add_job(database,id="newjob",username="admin",filename="Base.xlsx",status="processing",
            created_at=None):
    with database() as con:
        con.execute(
            "INSERT INTO upload_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (id,"operations",filename,status,25,"Analizando","",json.dumps({}),
             created_at or datetime.now().isoformat(timespec="seconds"),
             "","",username,0)
        )


def test_uploaded_job_is_confirmed_from_history_after_disconnected_worker(isolated_upload_db):
    add_job(isolated_upload_db)
    with isolated_upload_db() as con:
        con.execute(
            "INSERT INTO upload_history(module,filename,valid_records,rejected_records,period_detected,published,job_id) "
            "VALUES(?,?,?,?,?,?,?)",
            ("Cambios y Muertos","Base.xlsx",14816,0,"2026-10",1,"newjob")
        )
    recovered=web_app._get_upload_job("newjob")
    assert recovered["status"]=="complete"
    assert recovered["progress"]==100
    assert recovered["result"]["rows"]==14816
    assert recovered["result"]["recovered"] is True
    assert web_app._get_upload_job("newjob")["status"]=="complete"


def test_uploaded_job_unpublished_must_remain_processing(isolated_upload_db):
    add_job(isolated_upload_db)
    job=web_app._get_upload_job("newjob")
    assert job["status"]=="processing"
    assert job["result"]=={}


def test_recent_lookup_filters_owner_and_filename(isolated_upload_db,monkeypatch):
    add_job(isolated_upload_db,id="other",username="otheruser")
    add_job(isolated_upload_db,id="older",username="admin",created_at=(
        datetime.now()-timedelta(days=1)).isoformat(timespec="seconds"))
    add_job(isolated_upload_db,id="newjob",username="admin")
    monkeypatch.setattr(web_app,"require_user",lambda *_args,**_kwargs:{"username":"admin","role":"admin"})
    found=web_app.latest_operations_upload(object(),"Base.xlsx")
    assert found["id"]=="newjob"
    with pytest.raises(HTTPException) as err:
        web_app.latest_operations_upload(object(),"different.xlsx")
    assert err.value.status_code==404


def test_frontend_keeps_job_identifier_when_proxy_returns_520():
    source=(web_app.WEB/"index.html").read_text(encoding="utf-8")
    assert "function transientUploadError(error)" in source
    for status in (520,521,522,523,524,529,530):
        assert str(status) in source[source.index("function transientUploadError"):source.index("async function waitForUploadJob")]
    assert "/api/upload/jobs/operations/latest?filename=" in source
    assert "localStorage.setItem(storageKey,job.id)" in source
    assert "No vuelvas a subirlo" in source or "No vuelvas a cargarlo" in source
    assert "document.hidden?12000:5500" in source


def test_pwa_rolls_to_version_401():
    worker=(web_app.WEB/"service-worker.js").read_text(encoding="utf-8")
    assert "operaciones-ropa-runtime-safe-update-v401" in worker
    result=subprocess.run(["node","--check"],input=worker,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
