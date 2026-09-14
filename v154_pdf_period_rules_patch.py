"""V154 · Reglas de PDF por periodo en Cambios y Muertos.

- Día: vuelve al generador PDF validado previo a V152 (sin hoja vertical extra).
- Semana / Mes / Año: conserva V152, incluida la hoja vertical de Devolución y recuperación.
- Históricos/otros: usan el generador previo a V152 salvo que el reporte sea Semanal/Mensual.
- El nombre descargado ya no agrega el sufijo "_proyecto".

Se instala en dos fases: `install_pre` ANTES de V152 para capturar el generador
anterior, y `install_post` DESPUÉS de V153 para aplicar la regla y ajustar el
Content-Disposition del endpoint autoritativo de exportación.
"""
from __future__ import annotations

import inspect
import re


def install_pre(m):
    if getattr(m, "_V154_PDF_PERIOD_PRE", False):
        return
    # Captura exacta del PDF que existía antes de V152; es el formato diario
    # que ya estaba validado por el usuario.
    m._V154_PRE_V152_PDF_BUILDER = m._build_operations_pdf
    m._V154_PDF_PERIOD_PRE = True
    print("[V154-PDF] Generador diario previo a V152 capturado.", flush=True)


def install_post(m):
    if getattr(m, "_V154_PDF_PERIOD_POST", False):
        return

    pre_v152 = getattr(m, "_V154_PRE_V152_PDF_BUILDER", None)
    v152_builder = m._build_operations_pdf

    if callable(pre_v152):
        def period_aware_builder(data: dict, report: str, scope: str = "Compañía") -> bytes:
            period_type = str((data or {}).get("period_type") or "").strip().lower()
            # La hoja vertical exclusiva sólo corresponde a Semana, Mes y Año.
            use_v152 = (
                period_type in {"week", "month", "year"}
                or report in {"Reporte Semanal", "Reporte Mensual"}
            )
            if use_v152:
                return v152_builder(data, report, scope)
            return pre_v152(data, report, scope)

        m._build_operations_pdf = period_aware_builder

    # Captura el endpoint de exportación V153 y sólo modifica el nombre final.
    export_path = "/api/export/operations/project-scope-v151"
    old_route = None
    for route in list(m.app.router.routes):
        if getattr(route, "path", None) == export_path and "GET" in (getattr(route, "methods", set()) or set()):
            old_route = route
            break

    if old_route is not None:
        old_endpoint = old_route.endpoint
        try:
            m.app.router.routes.remove(old_route)
        except ValueError:
            pass

        async def export_without_project_suffix(
            request,
            format: str = "pdf",
            report: str = "Centro Ejecutivo",
            store: str = "Compañía",
            period_type: str = "all",
            period_value: str = "",
            area: str = "",
            activity: str = "",
            start_date: str = "",
            end_date: str = "",
        ):
            result = old_endpoint(
                request=request,
                format=format,
                report=report,
                store=store,
                period_type=period_type,
                period_value=period_value,
                area=area,
                activity=activity,
                start_date=start_date,
                end_date=end_date,
            )
            if inspect.isawaitable(result):
                result = await result
            try:
                cd = result.headers.get("content-disposition", "")
                if cd:
                    clean = re.sub(r"_proyecto(?=\.(?:pdf|xlsx)(?:\"|$))", "", cd, flags=re.I)
                    clean = clean.replace("_proyecto.pdf", ".pdf").replace("_proyecto.xlsx", ".xlsx")
                    result.headers["Content-Disposition"] = clean
            except Exception as exc:
                print(f"[V154-PDF] nombre warning: {type(exc).__name__}: {exc}", flush=True)
            return result

        # Preservar el tipado de Request que FastAPI necesita para inyección.
        try:
            from fastapi import Request
            export_without_project_suffix.__annotations__["request"] = Request
        except Exception:
            pass

        m.app.add_api_route(export_path, export_without_project_suffix, methods=["GET"])

    m._V154_PDF_PERIOD_POST = True
    print(
        "[V154-PDF] Día=PDF previo; Semana/Mes/Año=V152 vertical; nombre sin _proyecto.",
        flush=True,
    )
