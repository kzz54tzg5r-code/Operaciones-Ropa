"""Render the real production middleware chain using an isolated data/web root."""
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
output = Path(sys.argv[1])
os.environ["OPERACIONES_ROPA_DATA"] = str(output / "data")

import web_app

# Some historical installers edit index.html on startup. Keep the checkout clean.
web_app.WEB = output / "web"
shutil.copytree(ROOT / "web", web_app.WEB)

import server_entry
from fastapi.testclient import TestClient

with TestClient(server_entry.app) as client:
    response = client.get("/")
    response.raise_for_status()
    (output / "page.html").write_text(response.text, encoding="utf-8")
