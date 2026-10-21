"""Bounded runtime work; report values and business rules stay in their endpoints."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from concurrent.futures import Future
from functools import wraps
import inspect
import logging
from pathlib import Path
from queue import Queue
import threading
import time
from weakref import WeakKeyDictionary

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import request_response
from starlette.requests import Request

log = logging.getLogger("operaciones.performance")


def serialized(lock):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            with lock:
                return function(*args, **kwargs)
        return call
    return decorate


class SerialJobQueue:
    """One worker, not one thread per upload. The existing DB is the durable queue."""

    def __init__(self, on_error=None):
        self._queue = Queue()
        self._lock = threading.Lock()
        self._pending = set()
        self._worker = None
        self._on_error = on_error
        self._running = 0

    def submit(self, job_id, target, args):
        with self._lock:
            if job_id in self._pending:
                return False
            self._pending.add(job_id)
            self._queue.put((job_id, target, args))
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(
                    target=self._run, daemon=True, name="ropa-upload-queue"
                )
                self._worker.start()
        return True

    def _run(self):
        while True:
            job_id, target, args = self._queue.get()
            with self._lock:
                self._running = 1
            try:
                target(*args)
            except Exception as exc:
                log.exception("Upload worker failed")
                if self._on_error:
                    try:
                        self._on_error(job_id, exc)
                    except Exception:
                        log.exception("Could not record upload failure")
            finally:
                with self._lock:
                    self._running = 0
                    self._pending.discard(job_id)
                self._queue.task_done()

    def stats(self):
        with self._lock:
            return {"running": self._running, "queued": len(self._pending) - self._running}


def file_stamp(path):
    path = Path(path)
    try:
        stat = path.stat()
        return (str(path), stat.st_ino, stat.st_mtime_ns, stat.st_size)
    except OSError:
        return (str(path), None)


def data_revision(root):
    """Stat only, never load an Excel/JSON. Includes SQLite WAL commits and cuts."""
    root = Path(root)
    paths = set()
    for folder in (root, root / "commercial"):
        paths.update(folder.glob("*.json"))
        for database in folder.glob("*.sqlite3"):
            paths.add(database)
            paths.add(Path(str(database) + "-wal"))
    return tuple(file_stamp(path) for path in sorted(paths))


class ReportCache:
    """Immutable JSON bytes, byte/entry/time limits and non-blocking single-flight."""

    def __init__(self, max_bytes=8 * 1024 * 1024, max_entries=48,
                 max_item_bytes=2 * 1024 * 1024, ttl=20, clock=time.monotonic):
        self.max_bytes, self.max_entries = max_bytes, max_entries
        self.max_item_bytes, self.ttl, self.clock = max_item_bytes, ttl, clock
        self._entries = OrderedDict()
        self._inflight = {}
        self._lock = threading.Lock()
        self._bytes = 0
        self._hits = self._misses = self._shared = 0

    def _drop(self, key):
        self._bytes -= len(self._entries.pop(key)[1])

    def acquire(self, key):
        with self._lock:
            now = self.clock()
            for old in [k for k, (expires, _) in self._entries.items() if expires <= now]:
                self._drop(old)
            if key in self._entries:
                self._hits += 1
                self._entries.move_to_end(key)
                return "HIT", self._entries[key][1]
            if key in self._inflight:
                self._shared += 1
                return "SHARED", self._inflight[key]
            self._misses += 1
            future = Future()
            self._inflight[key] = future
            return "MISS", future

    def finish(self, key, body=None, *, cacheable=True, error=None):
        with self._lock:
            future = self._inflight.pop(key, None)
            if (error is None and body is not None and cacheable
                    and len(body) <= min(self.max_bytes, self.max_item_bytes)):
                if key in self._entries:
                    self._drop(key)
                self._entries[key] = (self.clock() + self.ttl, body)
                self._bytes += len(body)
                while self._bytes > self.max_bytes or len(self._entries) > self.max_entries:
                    self._drop(next(iter(self._entries)))
        # Complete outside the lock: Future callbacks can re-enter the cache.
        if future is not None and not future.done():
            if error is not None:
                future.set_exception(error)
            else:
                future.set_result(body)

    def stats(self):
        with self._lock:
            return {"entries": len(self._entries), "bytes": self._bytes,
                    "inflight": len(self._inflight), "hits": self._hits,
                    "misses": self._misses, "shared": self._shared,
                    "max_bytes": self.max_bytes, "ttl_seconds": self.ttl}


REPORT_PATHS = frozenset({
    "/api/operations", "/api/operations/meta", "/api/operations/year",
    "/api/operations/project-scope-v151",
    "/api/operations/recovery-rate", "/api/operations/recovery-rate-audit-v331",
    "/api/operations/routes-calendar-v240",
    "/api/operations/collection-hour-matrix-v240",
    "/api/operations/collection-week-summary-v240",
    "/api/operation/report", "/api/operation/meta", "/api/operation/summary-v149",
    "/api/operation-productivity-ranking-v204", "/api/dashboard",
    "/api/commercial-sales-v109", "/api/commercial-sellthrough-v2",
    "/api/bonuses-v313", "/api/bonuses-v330", "/api/bonuses-b2-v340",
    "/api/commercial-accordion", "/api/commercial-detail",
    "/api/commercial-summary-v199", "/api/commercial-bootstrap-v188",
})


class TextGZipMiddleware:
    """Compress HTML/JSON. Leave files, photos and export streams unchanged."""

    def __init__(self, app):
        self.app = app
        self.compressed = GZipMiddleware(app, minimum_size=1024, compresslevel=4)

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        selected = path == "/" or path in REPORT_PATHS
        target = self.compressed if scope.get("type") == "http" and selected else self.app
        await target(scope, receive, send)


def install(m):
    if getattr(m, "_RUNTIME_PERFORMANCE_INSTALLED", False):
        return
    cache = ReportCache()
    # Expensive distinct reports are bounded too; matching requests await the same
    # Future without occupying additional Starlette worker threads.
    limits = WeakKeyDictionary()

    def context(request):
        actor = m.require_user(request)  # Always validate session, role and geofence.
        identity = tuple(str(actor.get(k) or "") for k in (
            "id", "username", "role", "real_role", "store", "view_role", "view_store"
        ))
        return identity, data_revision(m.DATA_ROOT)

    def response(body, status):
        return Response(body, media_type="application/json", headers={
            "Cache-Control": "private, no-store", "X-Report-Cache": status
        })

    def decorate(endpoint):
        async def invoke(*args, **kwargs):
            if inspect.iscoroutinefunction(endpoint):
                return await endpoint(*args, **kwargs)
            return await run_in_threadpool(endpoint, *args, **kwargs)

        @wraps(endpoint)
        async def report(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                return await invoke(*args, **kwargs)
            identity, revision = await run_in_threadpool(context, request)
            directives = request.headers.get("cache-control", "").lower()
            bypass = "no-cache" in directives or "no-store" in directives
            key = (request.url.path, tuple(sorted(request.query_params.multi_items(), key=lambda item: item[0])),
                   identity, revision)
            status, pending = ("BYPASS", None) if bypass else cache.acquire(key)
            if status == "HIT":
                return response(pending, status)
            if status == "SHARED":
                body = await asyncio.shield(asyncio.wrap_future(pending))
                if body is not None:
                    return response(body, status)
            started = time.monotonic()
            try:
                loop = asyncio.get_running_loop()
                gate = limits.setdefault(loop, asyncio.Semaphore(2))
                async with gate:
                    result = await invoke(*args, **kwargs)
                # Native downloads/errors/custom responses keep their own behavior.
                if not isinstance(result, (dict, list)):
                    if status == "MISS":
                        cache.finish(key)
                    return result
                body = await run_in_threadpool(lambda: JSONResponse(jsonable_encoder(result)).body)
                fresh = await run_in_threadpool(data_revision, m.DATA_ROOT)
                progress = result.get("processing") if isinstance(result, dict) else None
                processing = isinstance(result, dict) and (
                    (any(progress.values()) if isinstance(progress, dict) else bool(progress))
                    or result.get("weekly_pending") or result.get("available") is False
                )
                if status == "MISS":
                    cache.finish(key, body, cacheable=revision == fresh and not processing)
                return response(body, status)
            except BaseException as exc:
                if status == "MISS":
                    cache.finish(key, error=exc)
                raise
            finally:
                elapsed = time.monotonic() - started
                if elapsed > 1.5:
                    log.info("report path=%s duration_ms=%d cache=%s",
                             request.url.path, elapsed * 1000, status)
        return report

    installed = []
    for route in m.app.routes:
        if (getattr(route, "path", "") in REPORT_PATHS
                and "GET" in (getattr(route, "methods", set()) or set())
                and hasattr(route, "dependant")):
            endpoint = route.dependant.call
            # Preserve route.endpoint for internal exports and calculations which
            # intentionally call the original endpoint and expect a Python dict.
            route.dependant.call = decorate(endpoint)
            route.app = request_response(route.get_route_handler())
            installed.append(route.path)

    @m.app.get("/api/system/performance")
    def performance(request: Request):
        m.require_real_superadmin(request)
        return {"reports": cache.stats(), "report_paths": installed,
                "uploads": m._UPLOAD_QUEUE.stats()}

    m.app.add_middleware(TextGZipMiddleware)
    m._REPORT_PERFORMANCE_CACHE = cache
    m._RUNTIME_PERFORMANCE_INSTALLED = True
