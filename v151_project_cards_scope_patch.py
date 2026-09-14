"""V151 · KPIs de Cambios y Muertos sólo con tiendas Proyecto.

Objetivo:
- Día, Semanal, Mensual y Anual: tarjetas/KPIs, detalle operativo,
  productividad y recorridos se calculan únicamente con tiendas marcadas Proyecto.
- La tabla "Recuperación por tienda" conserva todas las tiendas del alcance para
  comparación y sigue resaltando las tiendas Proyecto.
- PDF/Excel usan exactamente el mismo alcance que la pantalla.

Se calcula a partir de una sola respuesta de /api/operations para no duplicar la
lectura de la base grande en Render.
"""
from __future__ import annotations

import io
import re
from datetime import date

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response


def install(m):
    if getattr(m, "_V151_PROJECT_CARDS_SCOPE", False):
        return

    def _num(v):
        try:
            return float(v or 0)
        except Exception:
            return 0.0

    def _year_bounds(value: str):
        txt = str(value or "").strip()
        if not (len(txt) == 4 and txt.isdigit()):
            raise HTTPException(400, "Año inválido")
        y = int(txt)
        if y < 2000 or y > 2100:
            raise HTTPException(400, "Año inválido")
        return f"{y}-01-01", f"{y}-12-31"

    def _scope_counts(actor, requested_store: str):
        try:
            selected = m.effective_store(actor, requested_store)
        except Exception:
            selected = str(requested_store or "Compañía")
        projects = set(str(x) for x in m.project_store_names(True))
        if selected and selected != "Compañía":
            return selected, 1, (1 if selected in projects else 0), projects
        try:
            all_count = len(m.store_names(True))
        except Exception:
            all_count = len(getattr(m, "PROJECT_STORES", ()) or ())
        return "Compañía", all_count, len(projects), projects

    def _project_view(
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
        actor = m.require_user(request)
        original_type = str(period_type or "all").lower()
        original_value = str(period_value or "")
        query_type, query_value = original_type, original_value
        qstart, qend = start_date, end_date
        if original_type == "year":
            qstart, qend = _year_bounds(original_value)
            query_type, query_value = "all", ""

        # Una sola consulta completa. Después se recortan únicamente los KPIs,
        # detalle y productividad al conjunto Proyecto; recuperación conserva todas.
        data = m.operations(
            request,
            store=store,
            period_type=query_type,
            period_value=query_value,
            area=area,
            activity=activity,
            start_date=qstart,
            end_date=qend,
            compact=compact,
            project_only=False,
        )
        if not isinstance(data, dict):
            return data

        selected, all_scope_count, project_scope_count, project_names = _scope_counts(actor, store)
        all_stores = list(data.get("stores") or [])
        project_stores = [
            dict(r) for r in all_stores
            if bool(r.get("is_project")) or str(r.get("store") or "") in project_names
        ]
        all_recovery = [dict(r) for r in (data.get("recovery_by_store") or [])]
        project_recovery = [
            r for r in all_recovery
            if str(r.get("store") or "") in project_names
        ]
        all_productivity = [dict(r) for r in (data.get("productivity") or [])]
        project_productivity = [
            r for r in all_productivity
            if str(r.get("store") or "") in project_names
        ]

        # Si se seleccionó una tienda específica no Proyecto, el alcance Proyecto
        # es deliberadamente vacío: la regla solicitada es estricta.
        if selected != "Compañía" and selected not in project_names:
            project_stores = []
            project_recovery = []
            project_productivity = []
            project_scope_count = 0

        mt = dict(data.get("metrics") or {})
        out_mt = dict(mt)

        def sum_store(key):
            return sum(_num(r.get(key)) for r in project_stores)

        # Volumen operativo de las tarjetas.
        for key in (
            "muertos", "cajas", "probador", "sistema_devoluciones", "sin_clasificar",
            "recolectadas", "total_pzs", "ingresos", "ingresos_periodo",
            "pendiente_anterior", "acondicionado", "ubicado", "recorridos",
            "pendiente_acondicionar", "pendiente_ubicar", "productividad_piezas",
        ):
            out_mt[key] = sum_store(key)

        # Conversión/recuperación: sólo Proyecto para tarjetas, aunque la tabla
        # de recuperación conserva todas las tiendas.
        dev = sum(_num(r.get("dev_pzs")) for r in project_recovery)
        converted = sum(_num(r.get("converted_pieces")) for r in project_recovery)
        return_value = sum(_num(r.get("return_value")) for r in project_recovery)
        recovered_value = sum(_num(r.get("recovered_value")) for r in project_recovery)
        out_mt["dev_pzs"] = dev
        out_mt["cambios"] = dev
        out_mt["converted_pieces"] = converted
        out_mt["conversion_pct"] = converted / dev * 100 if dev else 0.0
        out_mt["return_value"] = return_value
        out_mt["recovered_value"] = recovered_value
        out_mt["recovery_pct"] = recovered_value / return_value * 100 if return_value else 0.0
        out_mt["pending_recovery_pieces"] = max(dev - converted, 0.0)
        out_mt["pending_recovery_value"] = max(return_value - recovered_value, 0.0)

        total = _num(out_mt.get("total_pzs") or out_mt.get("ingresos"))
        acond = _num(out_mt.get("acondicionado"))
        ubicado = _num(out_mt.get("ubicado"))
        out_mt["ingresos"] = total
        out_mt["total_pzs"] = total
        out_mt["pct_acondicionado"] = acond / total * 100 if total else 0.0
        out_mt["pct_ubicado"] = ubicado / total * 100 if total else 0.0
        out_mt["pct_ubicado_acondicionado"] = ubicado / acond * 100 if acond else 0.0
        out_mt["pct_procesado"] = (total - _num(out_mt.get("pendiente_ubicar"))) / total * 100 if total else 0.0

        # Recorridos: conservar exactamente la meta proporcional del periodo,
        # pero multiplicada sólo por el número de tiendas Proyecto del alcance.
        all_meta = _num(mt.get("meta_recorridos"))
        per_store_meta = all_meta / all_scope_count if all_scope_count else 0.0
        project_meta = per_store_meta * project_scope_count
        out_mt["meta_recorridos"] = project_meta
        out_mt["pct_recorridos"] = _num(out_mt.get("recorridos")) / project_meta * 100 if project_meta else 0.0
        out_mt["faltante_recorridos"] = max(project_meta - _num(out_mt.get("recorridos")), 0.0)

        # Productividad: misma fórmula original, pero sólo colaboradores Proyecto.
        prod_days = sum(_num(x.get("days")) for x in project_productivity)
        prod_pieces = sum(_num(x.get("pieces")) for x in project_productivity)
        prod_daily = prod_pieces / prod_days if prod_days else 0.0
        goal_prod = _num((data.get("goals") or {}).get("productividad_diaria", 784))
        out_mt["productivity_days"] = prod_days
        out_mt["productivity_daily"] = prod_daily
        out_mt["productivity_pct"] = prod_daily / goal_prod * 100 if goal_prod else 0.0

        integral = (
            min(max(_num(out_mt.get("conversion_pct")), 0), 100) * 0.40
            + min(max(_num(out_mt.get("productivity_pct")), 0), 100) * 0.40
            + min(max(_num(out_mt.get("pct_recorridos")), 0), 100) * 0.20
        )
        out_mt["score"] = integral
        out_mt["integral_score"] = integral

        out = dict(data)
        out["metrics"] = out_mt
        out["stores"] = project_stores
        out["productivity"] = project_productivity
        # Comparativo visible: TODAS las tiendas. Ésta es la excepción deliberada.
        out["recovery_by_store"] = all_recovery
        out["score_by_store"] = [
            r for r in (data.get("score_by_store") or [])
            if str(r.get("store") or "") in project_names
        ]
        out["project_stores"] = sorted(project_names)
        out["v151_project_scope"] = True
        out["v151_project_store_count"] = project_scope_count
        out["v151_all_store_count"] = all_scope_count
        out["period_type"] = original_type
        out["period_value"] = original_value
        if original_type == "year":
            out["start_date"], out["end_date"] = qstart, qend
        return out

    @m.app.get("/api/operations/project-scope-v151")
    def operations_project_scope_v151(
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
        return _project_view(
            request, store, period_type, period_value, area, activity,
            start_date, end_date, compact,
        )

    @m.app.get("/api/export/operations/project-scope-v151")
    def export_project_scope_v151(
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
        data = _project_view(
            request, store, period_type, period_value, area, activity,
            start_date, end_date, True,
        )
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", report).strip("_").lower() or "reporte"
        period_safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(period_value or period_type)).strip("_")
        filename = f"{safe}_{period_safe}_proyecto" if period_safe else f"{safe}_proyecto"

        if format.lower() == "pdf":
            try:
                payload = m._build_operations_pdf(data, report, scope=store)
                return Response(
                    content=payload,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}.pdf"',
                        "Cache-Control": "no-store",
                    },
                )
            except Exception as exc:
                raise HTTPException(500, f"No fue posible generar PDF Proyecto: {type(exc).__name__}: {exc}")

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

    js = r'''<script id="v151-project-cards-scope-js">
(function(){
  const CONTROLLED=new Set(['Operación Diaria','Reporte Semanal','Reporte Mensual','Centro Ejecutivo']);
  function paramsFor(name){
    let type='all';
    if(name==='Operación Diaria')type='day';
    else if(name==='Reporte Semanal')type='week';
    else if(name==='Reporte Mensual')type='month';
    else if(name==='Centro Ejecutivo')type=$('#operPeriodMode')?.value||OPER_PERIOD?.type||'week';
    const value=OPER_PERIOD?.value||$('#operPeriodSelect')?.value||'';
    return {
      type,value,
      store:$('#operStoreSelect')?.value||'Compañía',
      area:$('#operAreaSelect')?.value||'',
      activity:$('#operActivitySelect')?.value||''
    };
  }
  function qs(p){
    return `store=${encodeURIComponent(p.store)}&period_type=${encodeURIComponent(p.type)}&period_value=${encodeURIComponent(p.value)}&area=${encodeURIComponent(p.area)}&activity=${encodeURIComponent(p.activity)}&compact=true`;
  }

  const previousFetch=window.fetchOpsForView;
  window.fetchOpsForView=async function(name){
    if(CONTROLLED.has(name)){
      const p=paramsFor(name);
      const d=await api('/api/operations/project-scope-v151?'+qs(p),{timeoutMs:180000});
      window.__V151_PROJECT_SCOPE=d;
      return d;
    }
    return previousFetch(name);
  };

  const previousDownload=window.downloadCurrentReport;
  window.downloadCurrentReport=async function(format,name,button){
    if(CONTROLLED.has(name)){
      const p=paramsFor(name),old=button?.textContent||'Descargar';
      const url=`/api/export/operations/project-scope-v151?format=${encodeURIComponent(format)}&report=${encodeURIComponent(name)}&store=${encodeURIComponent(p.store)}&period_type=${encodeURIComponent(p.type)}&period_value=${encodeURIComponent(p.value)}&area=${encodeURIComponent(p.area)}&activity=${encodeURIComponent(p.activity)}`;
      try{
        if(button){button.disabled=true;button.textContent=format==='pdf'?'Generando PDF…':'Generando Excel…'}
        const res=await fetch(url,{credentials:'same-origin',cache:'no-store'});
        if(!res.ok){let msg=`Error ${res.status}`;try{const j=await res.json();msg=j.detail||msg}catch(_){}throw new Error(typeof msg==='string'?msg:JSON.stringify(msg))}
        const blob=await res.blob(),cd=res.headers.get('content-disposition')||'',mt=cd.match(/filename="?([^";]+)"?/i);
        const filename=mt?.[1]||`cambios_muertos_${p.type}_${p.value||'proyecto'}.${format}`;
        const obj=URL.createObjectURL(blob),a=document.createElement('a');a.href=obj;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(obj),1500);
        if(button)button.textContent='Descargado ✓';
      }catch(e){alert('No fue posible descargar el reporte: '+(e.message||e));}
      finally{setTimeout(()=>{if(button){button.disabled=false;button.textContent=old}},1200)}
      return;
    }
    return previousDownload(format,name,button);
  };

  const previousRender=window.renderOperativoView;
  if(typeof previousRender==='function'){
    window.renderOperativoView=async function(name,force=false){
      const result=await previousRender(name,force);
      if(CONTROLLED.has(name)){
        const sub=$('#operativoDynamicSub');
        if(sub && !sub.textContent.includes('tiendas Proyecto')) sub.textContent=(sub.textContent||'')+' · KPIs: tiendas Proyecto';
      }
      return result;
    };
  }
  console.info('[V151] Día/Semanal/Mensual/Anual: KPIs sólo Proyecto; recuperación comparativa conserva todas.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v151_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v151-project-cards-scope-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Operations-UI-Version": "V151-PROJECT-SCOPE",
                },
            )
        except Exception as exc:
            print(f"[V151] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V151_PROJECT_CARDS_SCOPE = True
    print("[V151] KPIs Día/Semana/Mes/Año limitados a tiendas Proyecto; recuperación mantiene comparativo total.", flush=True)
