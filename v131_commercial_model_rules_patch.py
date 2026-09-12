"""V131 · Reglas comerciales para modelos lentos, sugerido 0 y sin ubicación.

- Modelos lentos: sólo ubicaciones operativas (Mesa, Pasillo, Ropa Colgada / RC), nunca exhibiciones.
- Modelos lentos: excluye entradas de los últimos 30 días respecto al corte consultado.
- Sugerido 0: sugerido exactamente 0, entrada entre corte y 30 días hacia atrás y ubicación operativa.
- Comparativo: Top 1 vs Top 2; desde Top 2 compara contra la tienda inmediatamente superior por venta.
- Agrega venta, sugerido, última entrada y ubicación de la tienda comparada.
- Agrega modo no_location: sugerido 0 sin ubicación, sólo Próximo a salir, Descontinuado e Impulso,
  ordenados en ese orden.

Este patch modifica la lógica real del API; el demo visual se maneja por separado.
"""
from __future__ import annotations

import re
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V131_COMMERCIAL_MODEL_RULES", False):
        return

    pd = m.pd
    np = m.np
    original_model_rows = m._capacity_model_rows

    def _norm(value):
        try:
            return m.login_key(value)
        except Exception:
            return str(value or "").strip().lower()

    def _operational_location_map(work):
        """Primera ubicación operativa por ID_ART, excluyendo exhibiciones."""
        if work is None or work.empty or "ID_ART" not in work.columns:
            return {}
        raw_col = "Ubicación detalle" if "Ubicación detalle" in work.columns else ("Pasillo" if "Pasillo" in work.columns else "")
        if not raw_col:
            return {}
        ids = work["ID_ART"].fillna("").astype(str).str.strip()
        raw = work[raw_col].fillna("").astype(str)
        parts = raw.str.split(r"[,;/]+", regex=True).explode().astype(str).str.strip()
        parts = parts[parts.ne("") & ~parts.str.lower().isin(["nan", "none"])]
        if parts.empty:
            return {}
        key = parts.map(_norm).str.upper()
        excluded = key.str.contains(r"EXHIB|CABECERA|BOTADERO|ISLA|ROUNDER|PONY|OFERTA|PROBADOR|PASTELERA|ARBOL|OUTLET", regex=True, na=False)
        valid = key.str.contains(r"\bMESA\b|\bPASILLO\b|ROPA\s*COLG|R\.?\s*COLGAD[AO]|\bR\.?\s*C\.?\b|\bRC\b", regex=True, na=False) & ~excluded
        chosen = parts[valid]
        if chosen.empty:
            return {}
        tmp = pd.DataFrame({"id": ids.reindex(chosen.index), "loc": chosen})
        tmp = tmp[tmp["id"].ne("")].drop_duplicates(["id", "loc"])
        if tmp.empty:
            return {}
        return tmp.groupby("id", sort=False)["loc"].agg(lambda s: m._combine_labels(s, 3)).to_dict()

    def _comparison_store(frame, store, section, catalog, period):
        if not store or store == "Compañía" or frame is None or frame.empty:
            return {"store": "", "current_rank": None, "comparison_rank": None}
        managed = m.store_names(True) or list(m.PROJECT_STORES)
        rows = m._capacity_store_comparative_v45(frame, managed, section, catalog, period)
        ranked = [r for r in rows if r.get("available") and r.get("sales_value") is not None]
        ranked.sort(key=lambda r: (-float(r.get("sales_value") or 0), str(r.get("store") or "")))
        idx = next((i for i, r in enumerate(ranked) if _norm(r.get("store")) == _norm(store)), None)
        if idx is None or len(ranked) < 2:
            return {"store": "", "current_rank": None, "comparison_rank": None}
        comp_idx = 1 if idx == 0 else idx - 1
        return {"store": str(ranked[comp_idx].get("store") or ""), "current_rank": idx + 1, "comparison_rank": comp_idx + 1}

    def _comparison_metrics(frame, comparison_store, section, catalog, period, ids):
        if not comparison_store or not ids or frame is None or frame.empty:
            return {}
        work = m._capacity_scope_v45(frame, comparison_store, section, catalog, add_area=True)
        if work.empty or "ID_ART" not in work.columns:
            return {}
        work = work.copy()
        work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
        work = work[work["__id"].isin(set(map(str, ids)))]
        if work.empty:
            return {}
        pcol, vcol = m._capacity_period_columns(period)
        loc_map = _operational_location_map(work)
        result = {}
        for rid, g in work.groupby("__id", sort=False):
            dates = pd.to_datetime(g.get("Última entrada CEDIS a tienda", pd.Series(index=g.index, dtype="object")), errors="coerce")
            result[str(rid)] = {
                "comparison_sales_pzas": float(pd.to_numeric(g.get(pcol, 0), errors="coerce").fillna(0).sum()),
                "comparison_sales_value": float(pd.to_numeric(g.get(vcol, 0), errors="coerce").fillna(0).sum()),
                "comparison_suggested": float(pd.to_numeric(g.get("VPD", 0), errors="coerce").fillna(0).sum()),
                "comparison_existence": float(pd.to_numeric(g.get("Existencia", 0), errors="coerce").fillna(0).sum()),
                "comparison_last_entry": "" if dates.dropna().empty else dates.max().strftime("%Y-%m-%d"),
                "comparison_location": str(loc_map.get(str(rid), "") or ""),
            }
        return result

    def _enrich(rows, frame, store, section, catalog, period):
        if not rows:
            return []
        comp = _comparison_store(frame, store, section, catalog, period)
        ids = [str(r.get("id_art") or "") for r in rows]
        metrics = _comparison_metrics(frame, comp.get("store", ""), section, catalog, period, ids)
        out = []
        for row in rows:
            item = dict(row)
            rid = str(item.get("id_art") or "")
            extra = metrics.get(rid, {})
            item.update(extra)
            item["comparison_store"] = comp.get("store", "")
            item["current_store_rank"] = comp.get("current_rank")
            item["comparison_store_rank"] = comp.get("comparison_rank")
            item["comparison_has_sale"] = bool(float(extra.get("comparison_sales_pzas") or 0) > 0 or float(extra.get("comparison_sales_value") or 0) > 0)
            out.append(item)
        return out

    def _no_location_rows(frame, store, section, period):
        work = m._capacity_scope_v45(frame, store, section, "Todos", add_area=True)
        if work.empty or "ID_ART" not in work.columns:
            return []
        work = work.copy()
        work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
        work = work[~work["__id"].isin(["", "nan", "None"])]
        if work.empty:
            return []
        loc_map = _operational_location_map(work)
        ids = work["__id"]
        sug = pd.to_numeric(work.get("VPD", 0), errors="coerce").fillna(0).groupby(ids).sum()
        ex = pd.to_numeric(work.get("Existencia", 0), errors="coerce").fillna(0).groupby(ids).sum()
        pcol, vcol = m._capacity_period_columns(period)
        sp = pd.to_numeric(work.get(pcol, 0), errors="coerce").fillna(0).groupby(ids).sum()
        sv = pd.to_numeric(work.get(vcol, 0), errors="coerce").fillna(0).groupby(ids).sum()
        dates = pd.to_datetime(work.get("Última entrada CEDIS a tienda", pd.Series(index=work.index, dtype="object")), errors="coerce").groupby(ids).max()

        def first_series(col, default=""):
            if col not in work.columns:
                return pd.Series(default, index=sug.index)
            s = work[col].fillna("").astype(str).str.strip().replace({"nan": "", "None": ""})
            return pd.DataFrame({"id": ids, "v": s.replace("", pd.NA)}).groupby("id", sort=False)["v"].first().reindex(sug.index).fillna(default)

        meta = pd.DataFrame(index=sug.index)
        meta["model"] = first_series("Modelo")
        meta["brand"] = first_series("Marca", "Sin marca")
        meta["section"] = first_series("Sección", "Sin sección")
        meta["rubro"] = first_series("Subcategoría", "Sin rubro")
        meta["catalog"] = first_series("Tipo catálogo")
        meta["suggested"] = sug
        meta["existence"] = ex.reindex(meta.index).fillna(0)
        meta["sales_pzas"] = sp.reindex(meta.index).fillna(0)
        meta["sales_value"] = sv.reindex(meta.index).fillna(0)
        meta["ultima_cedis"] = dates.reindex(meta.index)
        meta["has_location"] = [str(idx) in loc_map for idx in meta.index]

        def cat_label(v):
            key = _norm(v)
            if "proximo" in key and "salir" in key:
                return "PRÓXIMO A SALIR"
            if "descontinu" in key:
                return "DESCONTINUADO"
            if "impulso" in key:
                return "IMPULSO"
            return ""

        meta["catalog_label"] = meta["catalog"].map(cat_label)
        meta = meta[(meta["suggested"] <= 0.0001) & (~meta["has_location"]) & meta["catalog_label"].isin(["PRÓXIMO A SALIR", "DESCONTINUADO", "IMPULSO"])]
        if meta.empty:
            return []
        priority = {"PRÓXIMO A SALIR": 0, "DESCONTINUADO": 1, "IMPULSO": 2}
        meta["priority"] = meta["catalog_label"].map(priority).fillna(9)
        meta = meta.sort_values(["priority", "existence", "sales_pzas"], ascending=[True, False, True]).head(100)
        rows = []
        for rank, (rid, r) in enumerate(meta.iterrows(), 1):
            dt = r.get("ultima_cedis")
            rows.append({
                "id_art": str(rid), "model": str(r.get("model") or rid), "brand": str(r.get("brand") or "Sin marca"),
                "section": str(r.get("section") or "Sin sección"), "rubro": str(r.get("rubro") or "Sin rubro"),
                "catalog": str(r.get("catalog_label") or ""), "location": "", "exhibition": "", "store": store,
                "rank": rank, "suggested": float(r.get("suggested") or 0), "existence": float(r.get("existence") or 0),
                "sales_pzas": float(r.get("sales_pzas") or 0), "sales_pzas_30": 0.0, "sales_value": float(r.get("sales_value") or 0),
                "ultima_cedis": "" if pd.isna(dt) else pd.Timestamp(dt).strftime("%Y-%m-%d"), "recurrence_weeks": 0,
            })
        return rows

    def patched_model_rows(store="Compañía", section="Todas", mode="80_20", period="", catalog="Todos"):
        mode_key = str(mode or "80_20").lower()
        frame = m._capacity_frame_for_period(period)
        if frame is None or frame.empty:
            return original_model_rows(store, section, mode, period, catalog)

        if mode_key in ("no_location", "sin_ubicacion", "without_location"):
            rows = _no_location_rows(frame, store, section, period)
            return _enrich(rows, frame, store, section, "Todos", period)

        rows = original_model_rows(store, section, mode, period, catalog)
        if not rows:
            return []

        if mode_key in ("slow", "lentos", "suggested_zero", "sin_venta", "sug0"):
            work = m._capacity_scope_v45(frame, store, section, catalog, add_area=True)
            loc_map = _operational_location_map(work)
            entry = m._capacity_source_entry(period)
            report_date = pd.Timestamp(m._capacity_report_date(entry)) if entry else pd.Timestamp.now().normalize()
            cutoff = report_date - pd.Timedelta(days=30)
            filtered = []
            for row in rows:
                rid = str(row.get("id_art") or "")
                dt = pd.to_datetime(row.get("ultima_cedis") or None, errors="coerce")
                has_operational_location = bool(loc_map.get(rid))
                if mode_key in ("slow", "lentos"):
                    # Lentos: ubicación operativa obligatoria y última entrada estrictamente anterior a 30 días.
                    if not has_operational_location or pd.isna(dt) or not (dt < cutoff):
                        continue
                    item = dict(row)
                    item["location"] = loc_map.get(rid, item.get("location", ""))
                    filtered.append(item)
                else:
                    # Sugerido 0: exactamente 0, ubicación operativa y entrada dentro de los últimos 30 días.
                    suggested = float(row.get("suggested") or 0)
                    if not has_operational_location or abs(suggested) > 0.0001 or pd.isna(dt) or not (cutoff <= dt <= report_date):
                        continue
                    item = dict(row)
                    item["location"] = loc_map.get(rid, item.get("location", ""))
                    filtered.append(item)
            rows = filtered

        return _enrich(rows, frame, store, section, catalog, period)

    m._capacity_model_rows = patched_model_rows

    css = r'''<style id="v131-commercial-rules-css">
.v131-compare-yes{display:inline-block;padding:3px 6px;border-radius:999px;background:#e8f8ed;color:#128447;font-weight:900;font-size:7px}.v131-compare-no{display:inline-block;padding:3px 6px;border-radius:999px;background:#f3f5f8;color:#667085;font-weight:900;font-size:7px}.v131-rule-note{margin:8px 0;padding:8px 10px;border:1px solid #cfe0f4;border-radius:9px;background:#f7fbff;color:#31557e;font-size:8px}.v131-status{display:inline-block;padding:4px 7px;border-radius:999px;font-size:7px;font-weight:950}.v131-status.next{background:#fff0c7;color:#9a6500}.v131-status.disc{background:#ffe3e6;color:#bd2535}.v131-status.imp{background:#e9f2ff;color:#1769d7}
</style>'''

    js = r'''<script id="v131-commercial-rules-js">
(function(){
  const fmt=n=>Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const old=window.renderModelRows;
  if(typeof old==='function'){
    window.renderModelRows=function(champs,slows,zeros,champSec,slowSec,scope,checkMap,checkEditable,checkStore,modelScope){
      const out=old.apply(this,arguments);
      const add=(tableId,rows)=>{
        const table=document.querySelector(tableId);if(!table)return;
        const head=table.closest('table')?.querySelector('thead tr');
        if(head&&!head.querySelector('[data-v131-head]')){
          ['Tienda comparación','Venta comp.','Sugerido comp.','Últ. entrada comp.','Ubicación comp.','¿Vende?'].forEach((t,i)=>{const th=document.createElement('th');th.textContent=t;if(i===0)th.dataset.v131Head='1';head.appendChild(th)});
        }
        const map=new Map((rows||[]).map(r=>[String(r.id_art),r]));
        table.querySelectorAll('tr[data-model-id]').forEach(tr=>{
          if(tr.querySelector('[data-v131-cell]'))return;
          const r=map.get(String(tr.dataset.modelId));if(!r)return;
          const vals=[esc(r.comparison_store||'—'),fmt(r.comparison_sales_pzas),Number(r.comparison_suggested||0).toLocaleString('es-MX',{maximumFractionDigits:2}),esc(r.comparison_last_entry||'—'),esc(r.comparison_location||'—'),r.comparison_has_sale?'<span class="v131-compare-yes">Sí vende</span>':'<span class="v131-compare-no">Sin venta</span>'];
          vals.forEach((v,i)=>{const td=document.createElement('td');td.innerHTML=v;if(i===0)td.dataset.v131Cell='1';tr.appendChild(td)});
        });
      };
      add('#slowTable',slows);add('#zeroTable',zeros);
      setTimeout(()=>loadNoLocation(modelScope||scope||'Compañía',slowSec||'Todas'),0);
      return out;
    };
  }
  async function loadNoLocation(store,section){
    const zero=document.querySelector('#zeroTable');if(!zero||typeof api!=='function')return;
    let host=document.querySelector('#v131NoLocationWrap');
    if(!host){host=document.createElement('div');host.id='v131NoLocationWrap';const wrap=zero.closest('.tablewrap');wrap?.insertAdjacentElement('afterend',host)}
    if(!host)return;
    host.innerHTML='<div class="title">Modelos sin ubicación · sugerido 0</div><div class="v131-rule-note">Sólo Próximo a salir → Descontinuado → Impulso. No incluye Vigente.</div><div class="panel">Cargando…</div>';
    try{
      const week=document.querySelector('#week')?.value||'';
      const catalog='Todos';
      const d=await api(`/api/model-ranking?week=${encodeURIComponent(week)}&store=${encodeURIComponent(store||'Compañía')}&section=${encodeURIComponent(section||'Todas')}&mode=no_location&catalog=${encodeURIComponent(catalog)}`,{timeoutMs:120000});
      const rows=d?.rows||[];
      const status=v=>{const x=String(v||'');const c=x.includes('PRÓXIMO')?'next':x.includes('DESCONT')?'disc':'imp';return `<span class="v131-status ${c}">${esc(x)}</span>`};
      host.innerHTML=`<div class="title">Modelos sin ubicación · sugerido 0</div><div class="v131-rule-note">Orden: Próximo a salir → Descontinuado → Impulso. Excluye Vigente y cualquier modelo con Mesa, Pasillo, Ropa Colgada o RC.</div><div class="tablewrap table-scroll-35"><table class="table"><thead><tr><th>ID_ART</th><th>Modelo</th><th>Marca</th><th>Sección</th><th>Rubro</th><th>Status catálogo</th><th>Existencia</th><th>Sugerido</th><th>Últ. entrada</th><th>Tienda comp.</th><th>Venta comp.</th><th>Últ. entrada comp.</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.id_art)}</td><td>${esc(r.model)}</td><td>${esc(r.brand)}</td><td>${esc(r.section)}</td><td>${esc(r.rubro)}</td><td>${status(r.catalog)}</td><td>${fmt(r.existence)}</td><td>${Number(r.suggested||0).toFixed(0)}</td><td>${esc(r.ultima_cedis||'—')}</td><td>${esc(r.comparison_store||'—')}</td><td>${fmt(r.comparison_sales_pzas)}</td><td>${esc(r.comparison_last_entry||'—')}</td></tr>`).join('')||'<tr><td colspan="12">Sin modelos para esta selección.</td></tr>'}</tbody></table></div>`;
    }catch(e){host.innerHTML=`<div class="title">Modelos sin ubicación · sugerido 0</div><div class="panel">No fue posible cargar: ${esc(e.message||e)}</div>`}
  }
  console.info('[V131] Reglas de lentos/sugerido 0/comparativo de tienda instaladas.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v131_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v131-commercial-rules-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache", "Expires": "0", "X-Operations-UI-Version": "V131-COMMERCIAL-MODEL-RULES"
            })
        except Exception as exc:
            print(f"[V131] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V131_COMMERCIAL_MODEL_RULES = True
    print("[V131] Reglas comerciales instaladas: lentos >30 días + ubicación, sugerido 0 <=30 días, comparación de tienda y sin ubicación.", flush=True)
