"""V177 · Foundation de escalamiento para alta concurrencia.

Esta capa es reversible y no migra ni destruye datos.
Objetivos:
- evitar recalcular los mismos reportes para muchos usuarios;
- colapsar consultas simultáneas iguales;
- limitar cálculos pesados concurrentes para evitar OOM en el plan actual;
- dejar soporte opcional para Redis compartido mediante REDIS_URL;
- comprimir respuestas JSON grandes;
- invalidar caché tras operaciones de escritura.

Punto de regreso antes de V177:
  branch: rollback/pre-scale-800-2026-09-21
  commit: 20d486726b64765d7fb4608653a9b32603167d03
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from collections import OrderedDict

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.gzip import GZipMiddleware


def install(m):
    if getattr(m, "_V177_SCALE_FOUNDATION", False):
        return

    # Compresión: importante cuando 100s de clientes descargan las mismas tablas.
    try:
        m.app.add_middleware(GZipMiddleware, minimum_size=1200, compresslevel=5)
    except Exception as exc:
        print(f"[V177] GZip no instalado: {type(exc).__name__}: {exc}", flush=True)

    ttl_by_path = {
        "/api/dashboard": 90,
        "/api/commercial-filter-options-v176": 300,
        "/api/commercial/status-options-v166": 300,
        "/api/commercial-sales-v176": 180,
        "/api/commercial-area-v176": 180,
        "/api/commercial-models-v176": 300,
        "/api/operations/coverage-v169": 120,
        "/api/operation/meta": 120,
        "/api/operation/origin-summary-v166": 120,
    }

    mutation_prefixes = (
        "/api/upload",
        "/api/goals",
        "/api/stores",
        "/api/users",
        "/api/model-checklist",
        "/api/commercial/",
        "/api/operation/",
    )

    # Caché local acotada. En el Starter actual no dejamos crecer memoria
    # indefinidamente. Cuando REDIS_URL esté conectado, Redis será la capa
    # compartida y esto seguirá siendo un L1 pequeño por instancia.
    max_local_bytes = int(os.environ.get("OPS_CACHE_LOCAL_BYTES", str(24 * 1024 * 1024)))
    max_item_bytes = int(os.environ.get("OPS_CACHE_ITEM_BYTES", str(2 * 1024 * 1024)))
    local = OrderedDict()
    local_bytes = 0
    cache_lock = asyncio.Lock()
    miss_locks = {}
    heavy_gate = asyncio.Semaphore(max(1, int(os.environ.get("OPS_HEAVY_CONCURRENCY", "1"))))
    stats = {"hit": 0, "miss": 0, "bypass": 0, "stored": 0, "evicted": 0, "invalidations": 0}

    redis_client = None
    redis_url = str(os.environ.get("REDIS_URL") or os.environ.get("OPS_REDIS_URL") or "").strip()
    if redis_url:
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(
                redis_url,
                encoding=None,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
            print("[V177] Redis configurado como caché compartido.", flush=True)
        except Exception as exc:
            redis_client = None
            print(f"[V177] Redis no disponible, usando caché local: {type(exc).__name__}: {exc}", flush=True)
    else:
        print("[V177] REDIS_URL no configurado; caché L1 local activo.", flush=True)

    def _actor_scope(request):
        try:
            actor = m.require_user(request)
            role = str(actor.get("role") or "user")
            store = str(actor.get("store") or "")
            return role, store
        except Exception:
            return "", ""

    def _cache_key(request, epoch="0"):
        role, assigned_store = _actor_scope(request)
        raw = "|".join((
            "v177",
            str(epoch),
            request.url.path,
            request.url.query,
            role,
            assigned_store,
        ))
        return "opsropa:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _redis_epoch():
        if redis_client is None:
            return "0"
        try:
            value = await redis_client.get(b"opsropa:cache_epoch")
            return (value or b"0").decode("utf-8", "ignore")
        except Exception:
            return "0"

    async def _invalidate():
        nonlocal local_bytes
        async with cache_lock:
            local.clear()
            local_bytes = 0
            stats["invalidations"] += 1
        if redis_client is not None:
            try:
                await redis_client.incr(b"opsropa:cache_epoch")
            except Exception:
                pass

    async def _local_get(key):
        nonlocal local_bytes
        now = time.monotonic()
        async with cache_lock:
            item = local.get(key)
            if not item:
                return None
            expires, status_code, headers, body = item
            if expires <= now:
                local.pop(key, None)
                local_bytes -= len(body)
                return None
            local.move_to_end(key)
            return status_code, headers, body

    async def _local_set(key, ttl, status_code, headers, body):
        nonlocal local_bytes
        if len(body) > max_item_bytes:
            return
        async with cache_lock:
            old = local.pop(key, None)
            if old:
                local_bytes -= len(old[3])
            local[key] = (time.monotonic() + ttl, status_code, headers, body)
            local_bytes += len(body)
            stats["stored"] += 1
            while local and local_bytes > max_local_bytes:
                _k, item = local.popitem(last=False)
                local_bytes -= len(item[3])
                stats["evicted"] += 1

    async def _shared_get(key):
        hit = await _local_get(key)
        if hit is not None:
            return hit
        if redis_client is None:
            return None
        try:
            body = await redis_client.get(key.encode("utf-8"))
            if body is None:
                return None
            # Redis sólo guarda cuerpos JSON 200. Cabeceras seguras son fijas.
            headers = {"content-type": "application/json; charset=utf-8", "x-ops-cache": "redis"}
            await _local_set(key, 30, 200, headers, body)
            return 200, headers, body
        except Exception:
            return None

    async def _shared_set(key, ttl, status_code, headers, body):
        await _local_set(key, ttl, status_code, headers, body)
        if redis_client is not None and status_code == 200 and len(body) <= max_item_bytes:
            try:
                await redis_client.setex(key.encode("utf-8"), ttl, body)
            except Exception:
                pass

    @m.app.get("/api/system/cache-v177")
    async def cache_status_v177(request: Request):
        m.require_user(request, ("superadmin", "admin"))
        return {
            "ok": True,
            "version": "V177",
            "backend": "redis+l1" if redis_client is not None else "local-l1",
            "entries": len(local),
            "local_bytes": local_bytes,
            "local_limit_bytes": max_local_bytes,
            "heavy_concurrency": getattr(heavy_gate, "_value", None),
            "stats": dict(stats),
            "rollback_branch": "rollback/pre-scale-800-2026-09-21",
            "rollback_commit": "20d486726b64765d7fb4608653a9b32603167d03",
        }

    @m.app.middleware("http")
    async def v177_scale_cache(request, call_next):
        path = request.url.path

        # Las escrituras nunca se cachean. Si terminan correctamente invalidan
        # todos los reportes para que los usuarios vean datos nuevos.
        if request.method != "GET":
            response = await call_next(request)
            if response.status_code < 400 and any(path.startswith(p) for p in mutation_prefixes):
                await _invalidate()
            return response

        ttl = ttl_by_path.get(path)
        if not ttl:
            stats["bypass"] += 1
            return await call_next(request)

        epoch = await _redis_epoch()
        key = _cache_key(request, epoch)
        hit = await _shared_get(key)
        if hit is not None:
            stats["hit"] += 1
            status_code, headers, body = hit
            out_headers = dict(headers)
            out_headers["x-ops-cache"] = out_headers.get("x-ops-cache", "hit")
            out_headers["cache-control"] = "private, max-age=0"
            return Response(content=body, status_code=status_code, headers=out_headers)

        stats["miss"] += 1
        # Un solo cálculo por clave en la instancia. Evita estampidas cuando
        # decenas de usuarios abren el mismo reporte a la vez.
        async with cache_lock:
            lock = miss_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                miss_locks[key] = lock

        async with lock:
            second = await _shared_get(key)
            if second is not None:
                stats["hit"] += 1
                status_code, headers, body = second
                out_headers = dict(headers)
                out_headers["x-ops-cache"] = out_headers.get("x-ops-cache", "coalesced")
                out_headers["cache-control"] = "private, max-age=0"
                return Response(content=body, status_code=status_code, headers=out_headers)

            # En el plan actual (0.5 CPU / 512 MB) sólo dejamos un cálculo
            # pesado a la vez. Los demás esperan y luego reutilizan el resultado.
            async with heavy_gate:
                response = await call_next(request)
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                headers = dict(response.headers)
                headers.pop("content-length", None)
                ctype = str(headers.get("content-type") or "")
                safe_headers = {
                    k: v for k, v in headers.items()
                    if k.lower() in ("content-type", "etag", "last-modified")
                }

                if response.status_code == 200 and ctype.startswith("application/json"):
                    await _shared_set(key, ttl, response.status_code, safe_headers, body)

                safe_headers["x-ops-cache"] = "miss"
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=safe_headers,
                    media_type=None,
                )

    m._V177_SCALE_FOUNDATION = True
    print("[V177] foundation de alta concurrencia instalada.", flush=True)
