import asyncio
import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from v321_bonus_initial_upload_responsive_patch import install


def test_initial_bonus_cut_upload_returns_quickly_and_finishes_in_background(tmp_path):
    app = FastAPI()
    commercial_root = tmp_path / "commercial"
    staging_dir = tmp_path / "staging"
    capacity_dir = commercial_root / "capacidades"
    capacity_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)
    manifest = {"capacities": [], "bonus_initial_capacity_entries": [], "bonus_initial_cuts": {}}
    jobs = {}
    target = SimpleNamespace(
        app=app,
        Path=Path,
        STAGING_DIR=staging_dir,
        COMMERCIAL_DATA_ROOT=commercial_root,
        shutil=shutil,
        json=json,
        threading=threading,
        datetime=datetime,
        secrets=__import__("secrets"),
        _UPLOAD_JOB_LOCK=threading.RLock(),
        _ACTIVE_UPLOAD_JOBS=set(),
        _V321_BONUS_INITIAL_UPLOAD_RESPONSIVE=False,
    )
    target.require_user = lambda request, roles: {"username": "admin", "role": "admin"}
    target.load_manifest = lambda: manifest
    target.save_manifest = lambda payload: None
    target.resolve_entry_path = lambda entry: commercial_root / str(entry["path"])

    async def save_upload(upload, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        await upload.seek(0)
        data = await upload.read()
        destination.write_bytes(data)
        return len(data)

    target._save_upload_stream = save_upload

    def save_source(source, filename, exclusive_initial_cut=False):
        destination = capacity_dir / filename
        shutil.copy2(source, destination)
        entry = {
            "id": "test-entry-001",
            "name": filename,
            "path": str(destination.relative_to(commercial_root)),
            "status": "Pendiente de validación",
            "uploaded_at": "2026-10-14T10:00:00",
        }
        manifest["capacities"].append(entry)
        return {**entry, "duplicate": False}

    target._save_capacity_source_path = save_source

    def process_entry(entry, filename):
        for item in manifest["capacities"]:
            if item["id"] == entry["id"]:
                item.update({
                    "status": "Procesado",
                    "rows": 123,
                    "stores": ["Vallejo", "Puebla Sur", "Miravalle"],
                    "report_date": "2026-10-01",
                    "cache_file": "capacity_normalized/test-entry-001.pkl",
                })
        return {"ok": True, "rows": 123, "stores": 3, "message": "Excel procesado"}

    target._process_capacity_entry = process_entry

    def create_job(module, filename, source_path, username):
        job = {
            "id": "job-initial-001",
            "module": module,
            "filename": filename,
            "source_path": str(source_path),
            "status": "queued",
            "progress": 10,
            "message": "En cola",
            "result": {},
            "created_by": username,
        }
        jobs[job["id"]] = job
        return job

    def update_job(job_id, **changes):
        job = jobs[job_id]
        for key, value in changes.items():
            if key == "result_json":
                job["result"] = json.loads(value or "{}")
            else:
                job[key] = value

    def finish_job(job_id, result):
        jobs[job_id].update(status="complete", progress=100, result=result, message=result["message"])

    target._create_upload_job = create_job
    target._update_upload_job = update_job
    target._finish_upload_job = finish_job

    @app.get("/api/upload/jobs/{job_id}")
    def get_job(job_id: str):
        return JSONResponse(jobs[job_id])

    install(target)

    with TestClient(app) as client:
        response = client.post(
            "/api/bonuses/initial-capacity",
            data={"month": "2026-10"},
            files={"file": ("capacidades.xlsx", b"excel-test-content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 202
        body = response.json()
        assert body["job_id"] == "job-initial-001"
        assert body["module"] == "bonus_initial_capacity"

        for _ in range(100):
            job_response = client.get("/api/upload/jobs/job-initial-001")
            if job_response.json().get("status") in ("complete", "error"):
                break
            time.sleep(0.02)

    job = jobs["job-initial-001"]
    assert job["status"] == "complete", job
    assert job["result"]["month"] == "2026-10"
    assert job["result"]["rows"] == 123
    assert manifest["bonus_initial_cuts"]["2026-10"] == "test-entry-001"
    assert manifest["capacities"] == []
    assert manifest["bonus_initial_capacity_entries"][0]["bonus_initial_only"] is True
    assert (commercial_root / manifest["bonus_initial_capacity_entries"][0]["path"]).exists()
