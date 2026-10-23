"""Regresiones del error ENOSPC de cargas de Cambios y Muertos en Render."""
import asyncio
import io
import sqlite3
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

import web_app


def _configure_job_db(monkeypatch, tmp_path, active=False):
    database=tmp_path/"jobs.sqlite3"
    connection=sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE upload_jobs (id TEXT, module TEXT, status TEXT, created_at TEXT)"
    )
    if active:
        connection.execute(
            "INSERT INTO upload_jobs VALUES (?,?,?,?)",
            ("anterior","operations","processing","2026-10-23T14:44:00")
        )
    connection.commit()
    connection.close()

    @contextmanager
    def db():
        con=sqlite3.connect(database)
        con.row_factory=sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()
    monkeypatch.setattr(web_app,"db",db)


def _file():
    return UploadFile(file=io.BytesIO(b"un xlsx de prueba"), filename="operaciones.xlsx")


def test_operations_second_upload_is_blocked_before_writing(monkeypatch, tmp_path):
    _configure_job_db(monkeypatch,tmp_path,active=True)
    monkeypatch.setattr(web_app,"STAGING_DIR",tmp_path)
    monkeypatch.setattr(web_app,"require_user",lambda *_args,**_kw:{"username":"admin"})
    with pytest.raises(HTTPException) as error:
        asyncio.run(web_app.start_operations_job(None,_file()))
    assert error.value.status_code == 409
    assert "anterior" in str(error.value.detail)
    assert not list(tmp_path.glob("operations_job_*.xlsx"))


def test_operations_upload_rejects_insufficient_disk_without_staging(monkeypatch,tmp_path):
    _configure_job_db(monkeypatch,tmp_path)
    monkeypatch.setattr(web_app,"STAGING_DIR",tmp_path)
    monkeypatch.setattr(web_app,"require_user",lambda *_args,**_kw:{"username":"admin"})
    monkeypatch.setattr(web_app.shutil,"disk_usage",
                        lambda _p:SimpleNamespace(free=web_app._OPERATIONS_UPLOAD_DISK_RESERVE-1))
    with pytest.raises(HTTPException) as error:
        asyncio.run(web_app.start_operations_job(None,_file()))
    assert error.value.status_code == 507
    assert not list(tmp_path.glob("operations_job_*.xlsx"))


def test_upload_stream_deletes_partial_file_after_no_space(tmp_path):
    class FullDisk(io.BytesIO):
        def read(self,_size=-1):
            raise OSError(28,"No space left on device")

    upload=UploadFile(file=FullDisk(b"data"),filename="archivo.xlsx")
    target=tmp_path/"incompleto.xlsx"
    with pytest.raises(HTTPException) as error:
        asyncio.run(web_app._save_upload_stream(upload,target))
    assert error.value.status_code == 507
    assert not target.exists()


def test_operations_upload_enqueues_once_and_keeps_stage_until_worker(monkeypatch,tmp_path):
    _configure_job_db(monkeypatch,tmp_path)
    monkeypatch.setattr(web_app,"STAGING_DIR",tmp_path)
    monkeypatch.setattr(web_app,"require_user",lambda *_args,**_kw:{"username":"admin"})
    monkeypatch.setattr(web_app.shutil,"disk_usage",
                        lambda _p:SimpleNamespace(free=400*1024*1024))
    observed=[]
    monkeypatch.setattr(web_app,"_create_upload_job",
                        lambda module,name,stage,user:{"id":"job-1","status":"queued"})
    monkeypatch.setattr(web_app,"_submit_upload_job",
                        lambda jid,fn,args:observed.append((jid,args)) or True)
    result=asyncio.run(web_app.start_operations_job(None,_file()))
    assert result["id"]=="job-1"
    assert len(observed)==1
    assert observed[0][1][0]=="job-1"
    stages=list(tmp_path.glob("operations_job_*.xlsx"))
    assert len(stages)==1
    assert stages[0].read_bytes()==b"un xlsx de prueba"
