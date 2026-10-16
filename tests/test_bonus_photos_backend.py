"""Pruebas de la fuente real de fotos para Modelos a Detalle."""
import asyncio
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from fastapi import FastAPI, HTTPException
from PIL import Image

import v314_bonus_product_photos_patch as photos


def image_bytes(fmt):
    buffer = BytesIO()
    Image.new("RGB", (50, 60), (62, 78, 150)).save(buffer, format=fmt)
    return buffer.getvalue()


def install_api():
    app = FastAPI()
    model = SimpleNamespace(app=app, require_user=lambda req: {"role": "admin"})
    photos.install(model)
    return model, next(route.endpoint for route in app.routes
                       if getattr(route, "path", "") == "/api/bonuses/product-photo/{product_id}")


class Remote:
    def __init__(self, image):
        self.headers = {"Content-Type": "application/octet-stream"}
        self.image = image
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self, _size):
        return self.image


def test_missing_jpg_finds_png_of_same_article(monkeypatch):
    seen = []
    png = image_bytes("PNG")
    def remote(request, timeout=6):
        seen.append(request.full_url)
        if request.full_url.endswith("88888001.jpg"):
            raise HTTPError(request.full_url, 404, "not found", {}, None)
        if request.full_url.endswith("88888001.png"):
            return Remote(png)
        raise AssertionError("The resolver must never search a different product ID")
    monkeypatch.setattr(photos.urllib.request, "urlopen", remote)
    model, endpoint = install_api()
    response = asyncio.run(endpoint(product_id="88888001", request=None))
    assert response.status_code == 200
    assert response.media_type == "image/png"
    assert response.body == png
    assert len(seen) == 2
    # The export and web view must agree on this exact article.
    assert model._bonus_photo_export_v314("88888001")


def test_true_not_found_returns_404_without_other_id_or_placeholders(monkeypatch):
    requested = []
    def missing(request, timeout=6):
        requested.append(request.full_url)
        raise HTTPError(request.full_url, 404, "not found", {}, None)
    monkeypatch.setattr(photos.urllib.request, "urlopen", missing)
    _, endpoint = install_api()
    with pytest.raises(HTTPException) as error:
        asyncio.run(endpoint(product_id="88888002", request=None))
    assert error.value.status_code == 404
    assert "no tiene una foto" in error.value.detail
    assert [url[-4:] for url in requested] == [".jpg",".png","webp"]
    # A second request is satisfied by the negative cache.
    with pytest.raises(HTTPException):
        asyncio.run(endpoint(product_id="88888002", request=None))
    assert len(requested) == 3


def test_transient_server_error_is_retried_without_false_missing(monkeypatch):
    calls = []
    jpg = image_bytes("JPEG")
    def remote(request, timeout=6):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 503, "temporarily unavailable", {}, None)
        return Remote(jpg)
    monkeypatch.setattr(photos.urllib.request, "urlopen", remote)
    monkeypatch.setattr(photos.time, "sleep", lambda _:None)
    _, endpoint = install_api()
    image = asyncio.run(endpoint(product_id="88888003", request=None))
    assert image.status_code == 200
    assert image.media_type == "image/jpeg"
    assert len(calls) == 2
    assert all(url.endswith("88888003.jpg") for url in calls)


def test_temporary_failure_returns_retryable_503(monkeypatch):
    def failing(request, timeout=6):
        raise HTTPError(request.full_url, 429, "rate limit", {}, None)
    monkeypatch.setattr(photos.urllib.request, "urlopen", failing)
    monkeypatch.setattr(photos.time, "sleep", lambda _:None)
    _, endpoint = install_api()
    with pytest.raises(HTTPException) as error:
        asyncio.run(endpoint(product_id="88888004", request=None))
    assert error.value.status_code == 503
    assert error.value.headers["Retry-After"] == "3"
