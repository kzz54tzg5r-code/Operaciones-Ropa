"""V153 · Alcance Proyecto autoritativo en backend para Cambios y Muertos.

Corrige V151: la pantalla ya indicaba "KPIs: tiendas Proyecto", pero la vista
Semanal podía seguir mostrando los totales de Compañía porque el recorte se
hacía después de construir el payload. Esta versión usa directamente la lógica
madura de `operations(..., project_only=True)` para TODOS los KPIs/detalle y
sólo reincorpora `recovery_by_store` del alcance completo para conservar el
comparativo de todas las tiendas.

Reglas:
- Compañía + Día/Semana/Mes/Año: KPIs, tarjetas, detalle, productividad,
  recorridos y score = sólo tiendas marcadas Proyecto.
- Recuperación por tienda = todas las tiendas, con bandera `is_project`.
- Tienda específica conserva su comportamiento normal; el endpoint explícito
  project-scope es estricto y deja vacío si la tienda no es Proyecto.
- PDF/XLSX del endpoint V151 usan exactamente el mismo payload V153.
- /api/operations queda como respaldo autoritativo para que, aunque un wrapper
  JS anterior no se ejecute, el agregado Compañía no vuelva a ser general.
"""
from __future__ import annotations

import inspect
import io
import re
import traceback

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response


def install(m):
    if getattr(m, "_V153_PROJECT_SCOPE_BACKEND", False):
        return

    project_names_at_boot = list(m.project_store_names(True))
    print(
        f"[V153] Tiendas Proyecto configuradas ({len(project_names_at_boot)}): "
        + ", ".join(project_names_at_boot),
        flush=True,
    )

    def _year_bounds(value: str):
        txt = str(value or "").strip()
        if not (len(txt) == 4 and txt.isdigit()):
            raise HTTPException(400, "Año inválido")
        y = int(txt)
        if y < 2000 or y > 2100:
            raise HTTPException(400, "Año inválido")
        return txt, f"{y}-01-01", f"{y}-12-31"

    async def _ops_call(
        request: Request,
        *,
        store: str,
        period_type: str,
        period_value: str,
        area: str,
        activity: str,
        start_date: str,
        end_date: str,
        compact: bool,
        project_only: bool,
    ):
        result = m.operations(
            request,
            store=store,
            period_type=period_type,
            period_value=period_value,
            area=area,
            activity=activity,
            start_date=start_date,
            end_date=end_date,
            compact=compact,
            project_only=project_only,
        )
        if inspect.isawaitable(result):
            result = await result
        return result

    async def _project_payload(
        request: Request,
        *,
        store: str = "Compañía",
        period_type: str = "all",
        period_value: str = "",
        area: str = "",
        activity: str = "",
        start_date: str = "",
        end_date: str = "",
        compact: bool = True,
        strict_project: bool = True,
    ):
        actor = m.require_user(request)
        selected = m.effective_store(actor, store)
        original_type = str(period_type or "all").lower()
        original_value = str(period_value or "")
        query_type, query_value = original_type, original_value
        qstart, qend = start_date, end_date
        if original_type == "year":
            _, qstart, qend = _year_bounds(original_value)
            query_type, query_value = "all", ""

        project_names = set(m.project_store_names(True))

        # Tienda concreta: el endpoint project-scope es estricto; /api/operations
        # normal conserva la tienda elegida para no romper análisis individuales.
        if selected != "Compañía":
            use_project = strict_project
            data = await _ops_call(
                request,
                store=store,
                period_type=query_type,
                period_value=query_value,
                area=area,
                activity=activity,
                start_date=qstart,
                end_date=qend,
                compact=compact,
                project_only=use_project,
            )
            if isinstance(data, dict):
                out = dict(data)
                out["v153_project_scope"] = bool(use_project)
                out["v153_project_store_count"] = 1 if selected in project_names and use_project else 0
                out["v153_project_stores"] = sorted(project_names)
                out["period_type"] = original_type
                out["period_value"] = original_value
                if original_type == "year":
                    out["start_date"], out["end_date"] = qstart, qend
                return out
            return data

        # Compañía: dos consultas cacheables sobre la base persistida. La primera
        # es la fuente autoritativa de KPIs Proyecto; la segunda sólo aporta el
        # comparativo de Recuperación de todas las tiendas y metadatos de filtros.
        project_data = await _ops_call(
            request,
            store="Compañía",
            period_type=query_type,
            period_value=query_value,
            area=area,
            activity=activity,
            start_date=qstart,
            end_date=qend,
            compact=compact,
            project_only=True,
        )
        all_data = await _ops_call(
            request,
            store="Compañía",
            period_type=query_type,
            period_value=query_value,
            area=area,
            activity=activity,
            start_date=qstart,
            end_date=qend,
            compact=True,
            project_only=False,
        )
        if not isinstance(project_data, dict):
            return project_data
        if not isinstance(all_data, dict):
            all_data = {}

        out = dict(project_data)
        # ÚNICA excepción al alcance Proyecto: comparativo de recuperación.
        out["recovery_by_store"] = list(all_data.get("recovery_by_store") or [])

        # Mantener catálogos/periodos completos para no perder opciones del filtro.
        for key in (
            "available_dates", "available_weeks", "available_months", "available_years",
            "areas_available", "activities_available", "source_file", "source_name",
            "loaded_at", "updated_at", "available",
        ):
            if key in all_data:
                out[key] = all_data[key]

        out["v153_project_scope"] = True
        out["v153_project_store_count"] = len(project_names)
        out["v153_project_stores"] = sorted(project_names)
        # Compatibilidad con PDF V152 / V151.
        out["project_stores"] = sorted(project_names)
        out["period_type"] = original_type
        out["period_value"] = original_value
        if original_type == "year":
            out["start_date"], out["end_date"] = qstart, qend

        pm = out.get("metrics") or {}
        am = all_data.get("metrics") or {}
        print(
            "[V153-SCOPE] "
            f"{original_type}:{original_value or qstart or 'hist'} · proyectos={len(project_names)} · "
            f"dev_proyecto={float(pm.get('dev_pzs') or 0):.0f} vs dev_compania={float(am.get('dev_pzs') or 0):.0f} · "
            f"total_proyecto={float(pm.get('total_pzs') or pm.get('ingresos') or 0):.0f} vs total_compania={float(am.get('total_pzs') or am.get('ingresos') or 0):.0f}",
            flush=True,
        )
        return out

    def _remove_get(path: str):
        for route in list(m.app.router.routes):
            if getattr(route, "path", None) == path and "GET" in (getattr(route, "methods", set()) or set()):
                try:
                    m.app.router.routes.remove(route)
                except ValueError:
                    pass

    # 1) Endpoint explícito que usa V151 en navegador.
    _remove_get("/api/operations/project-scope-v151")

    async def operations_project_scope_v153(
        request: Request,
        store: str = "Compañía",
        period_type: str = "all",
        period_value: str = "",
        area: str = "",
        activity: str = "",
        start_date: str = "",
        end_date: str = "",
        compact: bool = True,
    ):
        return await _project_payload(
            request,
            store=store,
            period_type=period_type,
            period_value=period_value,
            area=area,
            activity=activity,
            start_date=start_date,
            end_date=end_date,
            compact=compact,
            strict_project=True,
        )

    m.app.add_api_route(
        "/api/operations/project-scope-v151",
        operations_project_scope_v153,
        methods=["GET"],
    )

    # 2) Respaldo autoritativo de /api/operations. En Compañía devuelve siempre
    # KPIs Proyecto + recuperación total. Así no dependemos del monkey-patch JS.
    _remove_get("/api/operations")

    async def operations_v153(
        request: Request,
        store: str = "Compañía",
        period_type: str = "all",
        period_value: str = "",
        area: str = "",
        activity: str = "",
        start_date: str = "",
        end_date: str = "",
        compact: bool = False,
        project_only: bool = False,
    ):
        try:
            if project_only:
                return await _ops_call(
                    request,
                    store=store,
                    period_type=period_type,
                    period_value=period_value,
                    area=area,
                    activity=activity,
                    start_date=start_date,
                    end_date=end_date,
                    compact=compact,
                    project_only=True,
                )
            return await _project_payload(
                request,
                store=store,
                period_type=period_type,
                period_value=period_value,
                area=area,
                activity=activity,
                start_date=start_date,
                end_date=end_date,
                compact=compact,
                strict_project=False,
            )
        except HTTPException:
            raise
        except Exception as exc:
            print(f"[V153-OPS] {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=12)}", flush=True)
            raise HTTPException(500, f"{type(exc).__name__}: {exc}")

    m.app.add_api_route("/api/operations", operations_v153, methods=["GET"])

    # 3) Anual también autoritativo aunque V119 sea el que lo invoque.
    _remove_get("/api/operations/year")

    async def operations_year_v153(
        request: Request,
        year: str,
        store: str = "Compañía",
        area: str = "",
        activity: str = "",
        compact: bool = True,
        project_only: bool = False,
    ):
        y, start, end = _year_bounds(year)
        if project_only:
            data = await _ops_call(
                request,
                store=store,
                period_type="all",
                period_value="",
                area=area,
                activity=activity,
                start_date=start,
                end_date=end,
                compact=compact,
                project_only=True,
            )
        else:
            data = await _project_payload(
                request,
                store=store,
                period_type="year",
                period_value=y,
                area=area,
                activity=activity,
                compact=compact,
                strict_project=False,
            )
        if isinstance(data, dict):
            data = dict(data)
            data["period_type"] = "year"
            data["period_value"] = y
            data["start_date"] = start
            data["end_date"] = end
        return data

    m.app.add_api_route("/api/operations/year", operations_year_v153, methods=["GET"])

    # 4) Export V151 corregido: consume el MISMO payload autoritativo V153.
    _remove_get("/api/export/operations/project-scope-v151")

    async def export_project_scope_v153(
        request: Request,
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
        data = await _project_payload(
            request,
            store=store,
            period_type=period_type,
            period_value=period_value,
            area=area,
            activity=activity,
            start_date=start_date,
            end_date=end_date,
            compact=True,
            strict_project=True,
        )
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", report).strip("_").lower() or "reporte"
        period_safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(period_value or period_type)).strip("_")
        filename = f"{safe}_{period_safe}_proyecto" if period_safe else f"{safe}_proyecto"

        if format.lower() == "pdf":
            payload = m._build_operations_pdf(data, report, scope=store)
            return Response(
                content=payload,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.pdf"',
                    "Cache-Control": "no-store",
                },
            )
        if format.lower() == "xlsx":
            summary, stores, recovery, productivity = m._report_export_payload(data, report)
            bio = io.BytesIO()
            with m.pd.ExcelWriter(bio, engine="openpyxl") as writer:
                m.pd.DataFrame(summary, columns=["Indicador", "Valor"]).to_excel(writer, sheet_name="Resumen Proyecto", index=False)
                m.pd.DataFrame(stores).to_excel(writer, sheet_name="Detalle Proyecto", index=False)
                m.pd.DataFrame(recovery).to_excel(writer, sheet_name="Recuperacion Todas", index=False)
                m.pd.DataFrame(productivity).to_excel(writer, sheet_name="Productividad Proyecto", index=False)
            bio.seek(0)
            return Response(
                content=bio.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.xlsx"',
                    "Cache-Control": "no-store",
                },
            )
        raise HTTPException(400, "Formato no soportado")

    m.app.add_api_route(
        "/api/export/operations/project-scope-v151",
        export_project_scope_v153,
        methods=["GET"],
    )

    # 5) Indicador verificable en pantalla: ya no sólo dice "Proyecto", muestra
    # cuántas tiendas Proyecto entraron realmente en el payload.
    js = r'''<script id="v153-project-scope-backend-js">
(function(){
  const CONTROLLED=new Set(['Operación Diaria','Reporte Semanal','Reporte Mensual','Centro Ejecutivo']);
  const prevFetch=window.fetchOpsForView;
  if(typeof prevFetch==='function'){
    window.fetchOpsForView=async function(name){
      const d=await prevFetch(name);
      if(d&&d.v153_project_scope) window.__V153_PROJECT_SCOPE=d;
      return d;
    };
  }
  const prevRender=window.renderOperativoView;
  if(typeof prevRender==='function'){
    window.renderOperativoView=async function(name,force=false){
      const out=await prevRender(name,force);
      if(CONTROLLED.has(name)){
        const d=window.__V153_PROJECT_SCOPE;
        const sub=document.querySelector('#operativoDynamicSub');
        if(sub&&d&&d.v153_project_scope){
          const n=Number(d.v153_project_store_count||0);
          let txt=String(sub.textContent||'').replace(/\s*·\s*KPIs:\s*tiendas Proyecto/gi,'').replace(/\s*·\s*KPIs:\s*\d+\s*tiendas Proyecto/gi,'');
          sub.textContent=txt+` · KPIs: ${n} tienda${n===1?'':'s'} Proyecto`;
        }
      }
      return out;
    };
  }
  console.info('[V153] Alcance Proyecto autoritativo en backend activo.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v153_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v153-project-scope-backend-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Operations-UI-Version": "V153-PROJECT-BACKEND",
                },
            )
        except Exception as exc:
            print(f"[V153] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V153_PROJECT_SCOPE_BACKEND = True
    print("[V153] Backend Proyecto autoritativo instalado en Día/Semana/Mes/Año.", flush=True)
