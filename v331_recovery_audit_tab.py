"""V331 · Vista paralela y auditable de Tasa de recuperación.

No sustituye la V243. Reutiliza su cache de ventas/devoluciones diarias y
recalcula la existencia con SUMA de filas fuente, como el motor Sell Through.
No inventa entradas, salidas ni fechas de habilitado no presentes en la fuente.
"""
from __future__ import annotations

import math
from datetime import date

from fastapi import Request
from fastapi.responses import HTMLResponse

VIEW_KEY = "operations.recovery_audit"
VIEW_NAME = "Tasa de recuperación · Revisión"
MAX_CUT_AGE_DAYS = 7


def insert_before_document_body_end(page: str, fragment: str) -> str:
    """Insert at the LAST closing body tag, not tags quoted inside other JS.

    V314 contains document.write('</body></html>') inside a <script>. Using
    str.replace('</body>', ..., 1) injects our <script> into that JavaScript,
    breaks the host document and prints its remainder as visible text.
    """
    lower = page.lower()
    index = lower.rfind("</body>")
    if index < 0:
        return page + fragment
    return page[:index] + fragment + page[index:]


def safe_number(value):
    try:
        v = float(value or 0)
        return v if math.isfinite(v) else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def cut_quality(period_start, cut_date, max_age_days=MAX_CUT_AGE_DAYS):
    """Devuelve estado, edad; jamás valida cortes futuros o demasiado viejos."""
    if not cut_date:
        return "sin_corte", None
    age = (period_start - cut_date).days
    if age < 0:
        return "corte_futuro", age
    if age > max_age_days:
        return "corte_antiguo", age
    return ("coincidente" if age == 0 else "estimado"), age


def corrected_stock(frame, normalize_store):
    """Suma existencias por tienda/ID, incluidas ubicaciones independientes.

    Las filas del archivo de capacidades son registros de inventario, NO
    snapshots duplicados que deban colapsarse con max(ID_ART).
    """
    import pandas as pd

    if frame is None or frame.empty or "Tienda" not in frame or "ID_ART" not in frame:
        return {}
    keys = frame["Tienda"].fillna("").astype(str).map(normalize_store)
    articles = frame["ID_ART"].fillna("").astype(str).str.strip()
    if "Existencia" in frame:
        qty = pd.to_numeric(frame["Existencia"], errors="coerce").fillna(0.0)
    else:
        floor = pd.to_numeric(frame["Existencia piso"], errors="coerce").fillna(0.0) if "Existencia piso" in frame else pd.Series(0.0, index=frame.index)
        storehouse = pd.to_numeric(frame["Existencia bodega"], errors="coerce").fillna(0.0) if "Existencia bodega" in frame else pd.Series(0.0, index=frame.index)
        qty = floor + storehouse
    compact = pd.DataFrame({"store": keys, "id": articles, "qty": qty})
    compact = compact[(compact["store"] != "") & (~compact["id"].isin(["", "nan", "None"]))]
    if compact.empty:
        return {}
    by_model = compact.groupby(["store", "id"], observed=True, sort=False)["qty"].sum()
    total = by_model.groupby(level=0, sort=False).sum()
    return {str(k): max(safe_number(v), 0.0) for k, v in total.items()}


def revise_payload(raw, stocks, source_date, source_name, period_start,
                   max_age_days=MAX_CUT_AGE_DAYS):
    """Cálculo puro: sólo publica tasas cuando todos sus supuestos se cumplen."""
    result = dict(raw)
    state, age = cut_quality(period_start, source_date, max_age_days)
    usable_cut = state in ("coincidente", "estimado")
    rows = []
    incomplete = []
    warnings = [
        "Las devoluciones proceden del Excel de Cambios y Muertos. La fuente no certifica que cada pieza ya haya sido habilitada y ubicada en piso.",
        "Las ventas corresponden al total registrado para el periodo, no necesariamente a venta atribuible a devoluciones.",
        "No se dispone en esta vista de entradas, salidas, traspasos y ajustes completos; el stock residual es teórico, no existencia física conciliada.",
    ]
    if state == "corte_futuro":
        warnings.append("Se encontró un corte POSTERIOR al inicio del periodo. Se anula la tasa: usarlo introduciría información futura.")
    elif state == "corte_antiguo":
        warnings.append("El corte de stock tiene " + str(age) + " días de antigüedad; límite permitido: " + str(max_age_days) + ". Se anula la tasa.")
    elif state == "sin_corte":
        warnings.append("No hay corte de capacidades para establecer inventario inicial.")
    elif state == "estimado":
        warnings.append("El corte precede el inicio del periodo por " + str(age) + " días. La tasa es una estimación pendiente de conciliación de movimientos.")

    for row in raw.get("rows") or []:
        item = dict(row)
        store = str(item.get("store") or "")
        has_stock = store in stocks
        initial = safe_number(stocks.get(store)) if has_stock else None
        dev = safe_number(item.get("dev_pzs"))
        sales = safe_number(item.get("sales_pzs"))
        sales_value = safe_number(item.get("sales_value"))
        available = (initial + dev) if initial is not None else None
        balance = (available - sales) if available is not None else None
        valid = usable_cut and has_stock and bool(available and available > 0) and sales <= available
        if not usable_cut:
            status = state
        elif not has_stock:
            status = "sin_stock_tienda"
        elif available is None or available <= 0:
            status = "sin_base"
        elif sales > available:
            status = "ventas_superan_base"
        else:
            status = state
        if not valid:
            incomplete.append(store)
        item.update({
            "stock_available": has_stock,
            "inv_initial_pzs": initial,
            "inv_total_pzs": available,
            "inv_final_pzs": balance,
            "sell_through_pct": (sales / available * 100.0) if valid else None,
            "impact_dev_pct": (dev / available * 100.0) if valid else None,
            "inv_total_amount": None,  # No convertir piezas a pesos con precio de venta.
            "inv_final_amount": None,  # Valor de stock requiere costo unitario real.
            "data_quality": status,
            "audit_valid": valid,
            "registered_returns_pzs": dev,
            "verified_enabled_returns_pzs": None,
            "sales_total_pzs": sales,
            "sales_value": sales_value,
        })
        rows.append(item)

    totals = {
        "inv_initial_pzs": sum(safe_number(r["inv_initial_pzs"]) for r in rows if r["inv_initial_pzs"] is not None),
        "dev_pzs": sum(safe_number(r["dev_pzs"]) for r in rows),
        "sales_pzs": sum(safe_number(r["sales_pzs"]) for r in rows),
        "sales_value": sum(safe_number(r["sales_value"]) for r in rows),
    }
    totals["inv_total_pzs"] = totals["inv_initial_pzs"] + totals["dev_pzs"]
    totals["inv_final_pzs"] = totals["inv_total_pzs"] - totals["sales_pzs"]
    complete = bool(rows) and not incomplete
    totals["sell_through_pct"] = (totals["sales_pzs"] / totals["inv_total_pzs"] * 100.0
                                  if complete and totals["inv_total_pzs"] > 0 else None)
    totals["impact_dev_pct"] = (totals["dev_pzs"] / totals["inv_total_pzs"] * 100.0
                                if complete and totals["inv_total_pzs"] > 0 else None)
    totals["stock_complete"] = complete
    totals["valid_stores"] = sum(1 for r in rows if r["audit_valid"])
    totals["stores_in_scope"] = len(rows)
    totals["inv_total_amount"] = None
    totals["inv_final_amount"] = None

    if incomplete:
        warnings.append("Sin indicador confiable para: " + ", ".join(incomplete) + ". El indicador de Compañía queda suspendido hasta completar la conciliación.")
    if any(r["data_quality"] == "ventas_superan_base" for r in rows):
        warnings.append("Las ventas superan el inventario estimado en al menos una tienda. Revisar movimientos omitidos antes de calcular una tasa.")

    trend = []
    for point in raw.get("trend") or []:
        p = dict(point)
        base = totals["inv_initial_pzs"] + safe_number(p.get("dev_pzs"))
        sold = safe_number(p.get("sales_pzs"))
        p["inv_total_pzs"] = base if complete else None
        p["sell_through_pct"] = (100.0 * sold / base if complete and base > 0 and sold <= base else None)
        trend.append(p)

    result.update({
        "rows": rows,
        "metrics": totals,
        "trend": trend,
        "stock_source_date": source_date.isoformat() if source_date else None,
        "stock_source_name": source_name,
        "audit": {
            "model": "Stock inicial del corte + devoluciones registradas - ventas totales",
            "cut_status": state,
            "cut_age_days": age,
            "max_cut_age_days": max_age_days,
            "stock_conciliated": False,
            "returns_enabled_verified": False,
            "all_inventory_movements_verified": False,
            "valid_store_count": totals["valid_stores"],
            "total_store_count": totals["stores_in_scope"],
        },
        "warnings": warnings,
        "definition": "Tasa estimada = ventas registradas / (stock inicial + devoluciones registradas) × 100. No equivale a conversión comprobada de devoluciones.",
    })
    return result


def install(m):
    if getattr(m, "_V331_RECOVERY_AUDIT", False):
        return
    m.REPORT_TABS[VIEW_KEY] = VIEW_NAME

    baseline = next((route.endpoint for route in m.app.routes
                     if getattr(route, "path", "") == "/api/operations/recovery-rate"), None)
    if baseline is None:
        raise RuntimeError("V331 requiere el endpoint de V243 previamente instalado")

    @m.app.get("/api/operations/recovery-rate-audit-v331")
    def rate_audit(request: Request, store: str = "Compañía",
                   period_type: str = "week", period_value: str = ""):
        # Auth, geocerca por tienda y cache diaria son los mismos que en V243.
        raw = baseline(request=request, store=store, period_type=period_type,
                       period_value=period_value)
        if raw.get("status") != "ready":
            return raw
        start = date.fromisoformat(raw["period_start"])
        # No usar cortes futuros aunque sean los únicos disponibles.
        try:
            entries = list(m._capacity_processed_entries() or [])
        except Exception:
            entries = []
        dated = []
        for entry in entries:
            try:
                cut_date = m._capacity_report_date(entry)
                if cut_date <= start:
                    dated.append((cut_date, str(entry.get("uploaded_at") or ""), entry))
            except Exception:
                continue
        chosen = max(dated, key=lambda x: (x[0], x[1])) if dated else None
        cut_date = chosen[0] if chosen else None
        entry = chosen[2] if chosen else None
        source = str(entry.get("name") or entry.get("id") or "") if entry else ""
        stocks = {}
        if entry and (start - cut_date).days <= MAX_CUT_AGE_DAYS:
            try:
                stocks = corrected_stock(m._load_capacity_compact_cache(entry),
                                         m._normalize_store_value)
            except Exception as exc:
                result = revise_payload(raw, {}, cut_date, source, start)
                result["warnings"].append("No se pudo procesar stock: " + type(exc).__name__ + ".")
                return result
        return revise_payload(raw, stocks, cut_date, source, start)

    css = """<style id="v331-recovery-audit-css">
.v331-note{border:1px solid #cbdcf3;border-radius:10px;background:#f4f8ff;padding:12px;font-size:12px;line-height:1.5;margin-bottom:10px}
.v331-warning{border-left:3px solid #cb8919;background:#fff8ed;padding:9px 11px;font-size:11px;margin-bottom:6px;line-height:1.45}
.v331-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}
.v331-card{background:white;border:1px solid #d9e3ef;border-radius:10px;padding:11px;min-width:0}
.v331-card small{font-size:10px;color:#526783;display:block}
.v331-card strong{font-size:21px;color:#153c72;display:block;margin:5px 0}
.v331-table-wrap{overflow-x:auto;width:100%;-webkit-overflow-scrolling:touch}
.v331-table{min-width:1030px;width:100%;border-collapse:collapse;font-size:12px}
.v331-table th,.v331-table td{border-bottom:1px solid #e3eaf2;padding:9px;text-align:right;white-space:nowrap}
.v331-table th:first-child,.v331-table td:first-child{text-align:left}
.v331-table th{background:#edf4ff;color:#1c487c;position:sticky;top:0}
.v331-status{font-weight:800;color:#905e12}
.v331-status.ok{color:#0d7b58}
.v331-table tr.project-row{background:#edf6ff}
@media(max-width:750px){.v331-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v331-card strong{font-size:17px}.v331-table{font-size:10px}}
</style>"""
    script = """<script id="v331-recovery-audit-js">
(function(){
 var esc=function(x){return String(x==null?'':x).replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]})};
 var nf=function(x){return x===null||x===undefined||!Number.isFinite(Number(x))?'—':Number(x).toLocaleString('es-MX',{maximumFractionDigits:0})};
 var pc=function(x){return x===null||x===undefined||!Number.isFinite(Number(x))?'—':Number(x).toLocaleString('es-MX',{maximumFractionDigits:1,minimumFractionDigits:1})+'%'};
 var money=function(x){return x===null||x===undefined?'—':Number(x).toLocaleString('es-MX',{style:'currency',currency:'MXN'})};
 var status=function(x){return {'coincidente':'Corte coincidente · estimado','estimado':'Corte cercano · estimado','sin_corte':'Sin corte','corte_futuro':'Corte futuro: bloqueado','corte_antiguo':'Corte antiguo: bloqueado','sin_stock_tienda':'Sin stock','sin_base':'Sin base','ventas_superan_base':'Ventas > base: revisar'}[x]||'Revisar'};
 function card(name,val,sub){return '<div class="v331-card"><small>'+esc(name)+'</small><strong>'+val+'</strong><small>'+esc(sub)+'</small></div>'}
 window.recoveryRateImprovedView=function(d){
   if(!d||d.status==='building'){
     window.setTimeout(function(){var active=document.querySelector('#operativoNav [data-tab-key="operations.recovery_audit"].active');if(active&&typeof window.renderOperativoView==='function')window.renderOperativoView('Tasa de recuperación · Revisión',true)},5000);
     return '<div class="v331-note">Preparando datos diarios de ventas y devoluciones. La pestaña se actualizará automáticamente cuando termine la carga.</div>';
   }
   if(d.status!=='ready')return '<div class="v331-note">'+esc(d.error||'No se pudo procesar el corte de recuperación.')+'</div>';
   var m=d.metrics||{}, a=d.audit||{},rows=d.rows||[];
   var out='<div class="v331-note"><b>Versión de revisión independiente.</b> Usa la suma de existencias de los registros de capacidades por tienda e ID_ART. El porcentaje es <b>estimado</b> y no constituye recuperación comprobada de devoluciones. Sólo se publica si existe corte válido y ventas no superan la base.</div>';
   out+='<div class="v331-kpis">'+card('Stock inicial de referencia',m.stock_complete?nf(m.inv_initial_pzs):'—','Piezas · falta conciliación de movimientos')+card('Devoluciones registradas',nf(m.dev_pzs),'Habilitación sin verificar')+card('Ventas totales',nf(m.sales_pzs),'Durante el periodo consultado')+card('Tasa estimada de desplazamiento',pc(m.sell_through_pct),'No es conversión FIFO')+card('Base inicial + devoluciones',m.stock_complete?nf(m.inv_total_pzs):'—','Piezas potencialmente disponibles')+card('Stock residual teórico',m.stock_complete?nf(m.inv_final_pzs):'—','No es existencia física')+card('Venta registrada ($)',money(m.sales_value),'No es recuperación atribuible')+card('Tiendas con indicador',nf(m.valid_stores)+' / '+nf(m.stores_in_scope),'Sujetas a conciliación')+'</div>';
   out+='<div class="v331-note"><b>Periodo:</b> '+esc(d.period_start)+' a '+esc(d.period_end)+' · <b>Corte:</b> '+esc(d.stock_source_date||'No disponible')+' · '+esc(d.stock_source_name||'')+' · <b>Calidad:</b> '+esc(status(a.cut_status))+'</div>';
   (d.warnings||[]).forEach(function(w){out+='<div class="v331-warning">'+esc(w)+'</div>'});
   out+='<div class="title">Detalle y trazabilidad por tienda</div><div class="v331-table-wrap"><table class="v331-table"><thead><tr><th>Tienda</th><th>Stock inicial</th><th>Dev. registradas</th><th>Base estimada</th><th>Ventas (pzs)</th><th>Residual teórico</th><th>Tasa estimada</th><th>Impacto Dev.</th><th>Calidad del dato</th></tr></thead><tbody>';
   rows.forEach(function(r){out+='<tr class="'+(r.is_project?'project-row':'')+'"><td><b>'+esc(r.store)+'</b></td><td>'+nf(r.inv_initial_pzs)+'</td><td>'+nf(r.dev_pzs)+'</td><td>'+nf(r.inv_total_pzs)+'</td><td>'+nf(r.sales_pzs)+'</td><td>'+nf(r.inv_final_pzs)+'</td><td><b>'+pc(r.sell_through_pct)+'</b></td><td>'+pc(r.impact_dev_pct)+'</td><td class="v331-status '+(r.audit_valid?'ok':'')+'">'+esc(status(r.data_quality))+'</td></tr>'});
   out+='</tbody></table></div>';
   out+='<div class="v331-note" style="margin-top:12px"><b>Próxima conciliación requerida:</b> entradas a tienda, traspasos, ajustes, movimientos de habilitado/ubicado y existencias al cierre. Hasta disponer de estas fuentes, los importes de inventario y la conversión atribuible a devoluciones quedan expresamente sin certificar. La pestaña original no fue modificada.</div>';
   return out;
 };
})();
</script>"""

    @m.app.middleware("http")
    async def recovery_audit_markup(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or not response.headers.get("content-type", "").startswith("text/html"):
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        page = body.decode("utf-8", errors="replace")
        # La nueva vista aún no tiene exportador auditado: no exponer descargas heredadas incorrectas.
        page = page.replace(
            "if(name!=='Recuperación por Tienda') out+=reportDownloadBar(name);",
            "if(name!=='Recuperación por Tienda' && name!=='Tasa de recuperación · Revisión') out+=reportDownloadBar(name);",
        )
        if 'id="v331-recovery-audit-css"' not in page:
            page = page.replace("</head>", css + "</head>", 1)
        if 'id="v331-recovery-audit-js"' not in page:
            page = insert_before_document_body_end(page, script)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers["X-Recovery-Audit"] = "V331"
        return HTMLResponse(page, status_code=response.status_code, headers=headers)

    m._V331_RECOVERY_AUDIT = True
    print("[V331] Tasa de recuperación · Revisión instalada sin modificar V243.", flush=True)
