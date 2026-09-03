"""Parche V87 para Cambios y Muertos sin volver a cargar el Excel.

Aplica sobre la base ya publicada las reglas validadas con el archivo real:
- Recolección de muertos sin motivo explícito = Muertos.
- Total pzs = Dev pzs + Muertos + Cajas + Probador.
- Ingresos y pendientes usan Total pzs, no sólo Recolección.
- Conversión/recuperación se consolidan únicamente con las tiendas del alcance.
- La vista web muestra Dev pzs y Total pzs en Día/Semana/Mes.
"""
from __future__ import annotations

from collections import defaultdict
from functools import wraps
import inspect


def install(module) -> None:
    if getattr(module, "_V87_OPERATIONS_PATCH", False):
        return

    original = getattr(module, "operations", None)
    if not callable(original):
        print("[V87-PATCH] No se encontró la función operations.", flush=True)
        return

    signature = inspect.signature(original)

    def _in_period(row, period_type: str, period_value: str) -> bool:
        if period_type == "all" or not period_value:
            return True
        date_text = str(row.get("date") or "")
        if period_type == "day":
            return date_text == period_value
        if period_type == "month":
            return date_text.startswith(period_value)
        if period_type == "week":
            try:
                year, week = period_value.split("-W", 1)
                return (
                    int(row.get("year_iso") or 0) == int(year)
                    and int(row.get("week_iso") or 0) == int(week)
                )
            except Exception:
                return False
        return True

    def _patch_result(result: dict, params: dict) -> dict:
        if not isinstance(result, dict):
            return result

        stores = result.get("stores") or []
        if not isinstance(stores, list):
            return result

        period_type = str(params.get("period_type") or "all")
        period_value = str(params.get("period_value") or "")
        start_date = str(params.get("start_date") or "")
        end_date = str(params.get("end_date") or "")
        area = str(params.get("area") or "")
        activity = str(params.get("activity") or "")

        allowed = {str(row.get("store") or "") for row in stores if row.get("store")}
        rec_by_store = {
            str(row.get("store") or ""): row
            for row in (result.get("recovery_by_store") or [])
            if row.get("store")
        }

        # Sincronizar Dev Pzs con el resumen de recuperación, que ya respeta
        # tienda, rol y selección de Proyecto del endpoint original.
        for store_row in stores:
            name = str(store_row.get("store") or "")
            recovery = rec_by_store.get(name)
            if recovery is not None:
                store_row["dev_pzs"] = float(recovery.get("dev_pzs") or 0)

        # V87: una fila de "Recolección de muertos" sin motivo se considera
        # Muertos. El archivo real de septiembre contiene este caso.
        blank_recollection = defaultdict(float)
        try:
            source_rows = (module.load_ops() or {}).get("rows") or []
            wanted_area = module.normalize_col(area) if area else ""
            wanted_activity = module.normalize_col(activity) if activity else ""
            for row in source_rows:
                store_name = str(row.get("store") or "")
                if allowed and store_name not in allowed:
                    continue
                if not _in_period(row, period_type, period_value):
                    continue
                date_text = str(row.get("date") or "")
                if start_date and (not date_text or date_text < start_date):
                    continue
                if end_date and (not date_text or date_text > end_date):
                    continue
                if wanted_area and module.normalize_col(row.get("area") or "") != wanted_area:
                    continue
                if wanted_activity:
                    if (
                        module.normalize_col(row.get("activity") or "") != wanted_activity
                        and module.normalize_col(row.get("activity_original") or "") != wanted_activity
                    ):
                        continue
                if (
                    str(row.get("activity") or "") == "Recolección de muertos"
                    and str(row.get("motive_class") or "") == "Sin clasificar"
                ):
                    blank_recollection[store_name] += float(row.get("pieces") or 0)
        except Exception as exc:
            print(f"[V87-PATCH] Advertencia al reclasificar Muertos: {type(exc).__name__}: {exc}", flush=True)

        for store_row in stores:
            name = str(store_row.get("store") or "")
            move = float(blank_recollection.get(name, 0) or 0)
            if move:
                store_row["muertos"] = float(store_row.get("muertos") or 0) + move
                store_row["sin_clasificar"] = max(
                    float(store_row.get("sin_clasificar") or 0) - move, 0.0
                )

            # Regla V87 validada con el Excel real.
            total = (
                float(store_row.get("dev_pzs") or 0)
                + float(store_row.get("muertos") or 0)
                + float(store_row.get("cajas") or 0)
                + float(store_row.get("probador") or 0)
            )
            acondicionado = float(store_row.get("acondicionado") or 0)
            ubicado = float(store_row.get("ubicado") or 0)
            store_row["total_pzs"] = total
            store_row["ingresos"] = total
            store_row["pendiente_acondicionar"] = max(total - acondicionado, 0.0)
            store_row["pendiente_ubicar"] = max(acondicionado - ubicado, 0.0)
            store_row["pct_acondicionado"] = acondicionado / total * 100 if total else 0.0
            store_row["pct_ubicado"] = ubicado / acondicionado * 100 if acondicionado else 0.0
            store_row["pct_ubicado_acondicionado"] = store_row["pct_ubicado"]

        stores.sort(key=lambda row: (-float(row.get("ingresos") or 0), str(row.get("store") or "")))
        result["stores"] = stores

        metrics = result.setdefault("metrics", {})

        def sum_store(key: str) -> float:
            return float(sum(float(row.get(key) or 0) for row in stores))

        for key in (
            "dev_pzs", "muertos", "cajas", "probador", "sistema_devoluciones",
            "sin_clasificar", "recolectadas", "total_pzs", "ingresos",
            "acondicionado", "ubicado", "recorridos", "pendiente_acondicionar",
            "pendiente_ubicar", "productividad_piezas",
        ):
            metrics[key] = sum_store(key)
        metrics["cambios"] = metrics["dev_pzs"]
        metrics["pct_acondicionado"] = (
            metrics["acondicionado"] / metrics["ingresos"] * 100
            if metrics["ingresos"] else 0.0
        )
        metrics["pct_ubicado"] = (
            metrics["ubicado"] / metrics["acondicionado"] * 100
            if metrics["acondicionado"] else 0.0
        )
        metrics["pct_ubicado_acondicionado"] = metrics["pct_ubicado"]
        metrics["pct_procesado"] = (
            (metrics["ingresos"] - metrics["pendiente_ubicar"]) / metrics["ingresos"] * 100
            if metrics["ingresos"] else 0.0
        )

        # Recalcular conversión/recuperación desde recovery_by_store evita que
        # Darkstore u otra ubicación fuera del alcance contamine el consolidado.
        recovery_rows = list(result.get("recovery_by_store") or [])
        dev = float(sum(float(row.get("dev_pzs") or 0) for row in recovery_rows))
        converted = float(sum(float(row.get("converted_pieces") or 0) for row in recovery_rows))
        return_value = float(sum(float(row.get("return_value") or 0) for row in recovery_rows))
        recovered_value = float(sum(float(row.get("recovered_value") or 0) for row in recovery_rows))
        metrics["dev_pzs"] = dev
        metrics["cambios"] = dev
        metrics["converted_pieces"] = converted
        metrics["conversion_pct"] = converted / dev * 100 if dev else 0.0
        metrics["return_value"] = return_value
        metrics["recovered_value"] = recovered_value
        metrics["recovery_pct"] = recovered_value / return_value * 100 if return_value else 0.0
        metrics["pending_recovery_pieces"] = max(dev - converted, 0.0)
        metrics["pending_recovery_value"] = max(return_value - recovered_value, 0.0)

        # Dev por tienda ya se sincronizó con recovery_by_store, por lo que el
        # Total pzs debe recalcularse una última vez después del consolidado.
        for store_row in stores:
            total = (
                float(store_row.get("dev_pzs") or 0)
                + float(store_row.get("muertos") or 0)
                + float(store_row.get("cajas") or 0)
                + float(store_row.get("probador") or 0)
            )
            store_row["total_pzs"] = total
            store_row["ingresos"] = total
            acondicionado = float(store_row.get("acondicionado") or 0)
            ubicado = float(store_row.get("ubicado") or 0)
            store_row["pendiente_acondicionar"] = max(total - acondicionado, 0.0)
            store_row["pendiente_ubicar"] = max(acondicionado - ubicado, 0.0)
            store_row["pct_acondicionado"] = acondicionado / total * 100 if total else 0.0
            store_row["pct_ubicado"] = ubicado / acondicionado * 100 if acondicionado else 0.0
            store_row["pct_ubicado_acondicionado"] = store_row["pct_ubicado"]

        metrics["total_pzs"] = sum_store("total_pzs")
        metrics["ingresos"] = metrics["total_pzs"]
        metrics["pendiente_acondicionar"] = sum_store("pendiente_acondicionar")
        metrics["pendiente_ubicar"] = sum_store("pendiente_ubicar")
        metrics["pct_acondicionado"] = (
            metrics["acondicionado"] / metrics["total_pzs"] * 100
            if metrics["total_pzs"] else 0.0
        )
        metrics["pct_ubicado"] = (
            metrics["ubicado"] / metrics["acondicionado"] * 100
            if metrics["acondicionado"] else 0.0
        )
        metrics["pct_ubicado_acondicionado"] = metrics["pct_ubicado"]

        # Evitar que una respuesta cacheada con la lógica anterior vuelva a salir.
        try:
            module._OPS_RESPONSE_CACHE.clear()
        except Exception:
            pass
        return result

    @wraps(original)
    def patched_operations(*args, **kwargs):
        bound = signature.bind_partial(*args, **kwargs)
        result = original(*args, **kwargs)
        return _patch_result(result, dict(bound.arguments))

    # Los endpoints de exportación resuelven el nombre global operations en
    # tiempo de ejecución; sustituirlo también corrige PDF/Excel.
    module.operations = patched_operations
    for route in module.app.router.routes:
        if getattr(route, "path", None) == "/api/operations" and hasattr(route, "dependant"):
            route.dependant.call = patched_operations

    # Servir la interfaz actual con cambios mínimos V87 sin reemplazar el HTML
    # ni perder las mejoras de carga V48 que ya existen en main.
    try:
        from fastapi.responses import HTMLResponse

        @module.app.middleware("http")
        async def _v87_ui_middleware(request, call_next):
            if request.url.path != "/":
                return await call_next(request)
            try:
                html = (module.WEB / "index.html").read_text(encoding="utf-8")

                # Día: Dev pzs + Total pzs, exactamente como la versión validada.
                old_daily = """    out=reportKpis([\n      kpiCard('Muertos',fmt(mt.muertos),'Recolección · motivo Muertos','#EC007C'),"""
                new_daily = """    out=reportKpis([\n      kpiCard('Dev pzs',fmt(mt.dev_pzs),'Devoluciones del día','#3366CC'),\n      kpiCard('Muertos',fmt(mt.muertos),'Recolección · motivo Muertos','#EC007C'),"""
                html = html.replace(old_daily, new_daily, 1)
                html = html.replace(
                    "kpiCard('Piezas recolectadas',fmt(mt.recolectadas),'Total Recolección de muertos','#3366CC'),",
                    "kpiCard('Total pzs',fmt(mt.total_pzs??mt.ingresos),'Dev + Muertos + Cajas + Probador','#3366CC'),"
                )
                html = html.replace(
                    "kpiCard('Pendiente de acondicionar',fmt(mt.pendiente_acondicionar),'Recolectadas - Acondicionado','#F59E0B'),",
                    "kpiCard('Pendiente de acondicionar',fmt(mt.pendiente_acondicionar),'Total pzs - Acondicionado','#F59E0B'),"
                )
                html = html.replace(
                    "kpiCard('Piezas ingresadas',fmt(mt.ingresos),OPER_PERIOD.value,'#3366CC'),",
                    "kpiCard('Total pzs',fmt(mt.total_pzs??mt.ingresos),OPER_PERIOD.value,'#3366CC'),"
                )
                html = html.replace(
                    "kpiCard('Ingresos mes',fmt(mt.ingresos),OPER_PERIOD.value,'#3366CC'),",
                    "kpiCard('Total pzs mes',fmt(mt.total_pzs??mt.ingresos),OPER_PERIOD.value,'#3366CC'),"
                )

                # Detalle diario/semanal/mensual: hacer visibles Dev y Total pzs.
                html = html.replace(
                    "<th>Ranking</th><th>Tienda</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Piezas recolectadas</th>",
                    "<th>Ranking</th><th>Tienda</th><th>Dev Pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Total pzs</th>"
                )
                html = html.replace(
                    "<td><b>#${i+1}</b></td><td><b>${r.store}</b></td><td>${fmt(r.muertos)}</td><td>${fmt(r.probador)}</td><td>${fmt(r.cajas)}</td>\n    <td><b>${fmt(r.recolectadas)}</b></td>",
                    "<td><b>#${i+1}</b></td><td><b>${r.store}</b></td><td>${fmt(r.dev_pzs)}</td><td>${fmt(r.muertos)}</td><td>${fmt(r.probador)}</td><td>${fmt(r.cajas)}</td>\n    <td><b>${fmt(r.total_pzs??r.ingresos)}</b></td>"
                )

                # El navegador no debe conservar la versión vieja después del despliegue.
                return HTMLResponse(
                    html,
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
                )
            except Exception as exc:
                print(f"[V87-PATCH] No se pudo parchear la interfaz: {type(exc).__name__}: {exc}", flush=True)
                return await call_next(request)
    except Exception as exc:
        print(f"[V87-PATCH] No se instaló middleware UI: {type(exc).__name__}: {exc}", flush=True)

    @module.app.on_event("startup")
    def _v87_startup_check():
        try:
            data = module.load_ops() or {}
            fifo = module._get_recovery_fifo_rows(data)
            allowed = set(module.project_store_names(True))
            for day in ("2026-09-01", "2026-09-02"):
                raw = [r for r in (data.get("rows") or []) if str(r.get("date") or "") == day and (not allowed or r.get("store") in allowed)]
                rec = [r for r in fifo if str(r.get("date") or "") == day and (not allowed or r.get("store") in allowed)]
                dev = sum(float(r.get("dev_pzs") or 0) for r in rec)
                muertos = sum(float(r.get("muertos") or 0) for r in raw)
                muertos += sum(
                    float(r.get("pieces") or 0) for r in raw
                    if str(r.get("activity") or "") == "Recolección de muertos"
                    and str(r.get("motive_class") or "") == "Sin clasificar"
                )
                cajas = sum(float(r.get("cajas") or 0) for r in raw)
                probador = sum(float(r.get("probador") or 0) for r in raw)
                total = dev + muertos + cajas + probador
                ubicado = sum(float(r.get("ubicado") or 0) for r in raw)
                acondicionado = sum(float(r.get("acondicionado") or 0) for r in raw)
                print(
                    f"[V87-PATCH] {day}: dev={dev:g} muertos={muertos:g} cajas={cajas:g} "
                    f"probador={probador:g} total_pzs={total:g} acondicionado={acondicionado:g} ubicado={ubicado:g}",
                    flush=True,
                )
        except Exception as exc:
            print(f"[V87-PATCH] Diagnóstico: {type(exc).__name__}: {exc}", flush=True)

    module._V87_OPERATIONS_PATCH = True
    print("[V87-PATCH] Lógica operativa V87 instalada sobre la base vigente.", flush=True)
