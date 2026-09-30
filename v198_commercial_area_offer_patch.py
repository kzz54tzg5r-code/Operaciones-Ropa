"""V198 · Comercial por áreas, Oferta y detalles compactos.

- Elimina Comparativo Compañía de Macro.
- Agrega Oferta como quinta agrupación, basada exclusivamente en Estatus comercial:
  Oferta, Gran remate (por descontinuar), Oferta(por descontinuar),
  Outlet y Outlet(por descontinuar).
- Oferta se desglosa por Dama/Caballero/Infantil en Ubicación.
- Añade resúmenes Colgado/Doblado/Jeans/Lencería/Oferta para 80/20,
  Modelos lentos y Sugerido 0 a 1.
- Los detalles quedan cerrados por defecto con + Detalle ....
"""
from __future__ import annotations

from collections import defaultdict
import threading
import time

import pandas as pd
from fastapi import Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V198_COMMERCIAL_AREA_OFFER", False):
        return

    offer_keys = {
        m.login_key("Oferta"),
        m.login_key("Gran remate (por descontinuar)"),
        m.login_key("Oferta(por descontinuar)"),
        m.login_key("Outlet"),
        m.login_key("Outlet(por descontinuar)"),
    }
    physical_areas = ("Colgado", "Doblado", "Jeans", "Lencería")

    # El cache compacto anterior no conservaba Estatus comercial. Forzar una
    # nueva versión permite reconstruirlo desde el Excel fuente sin alterar éste.
    if hasattr(m, "_CAPACITY_COMPACT_CACHE_VERSION"):
        m._CAPACITY_COMPACT_CACHE_VERSION = max(
            int(getattr(m, "_CAPACITY_COMPACT_CACHE_VERSION", 0) or 0), 6
        )
    original_columns = getattr(m, "_commercial_capacity_columns", None)
    if callable(original_columns) and not getattr(original_columns, "_v198_wrapped", False):
        def v198_columns(frame):
            cols = list(original_columns(frame) or [])
            if "Estatus comercial" in getattr(frame, "columns", []) and "Estatus comercial" not in cols:
                cols.append("Estatus comercial")
            return cols
        v198_columns._v198_wrapped = True
        m._commercial_capacity_columns = v198_columns

    meta_cache = {}
    meta_lock = threading.RLock()

    def _meta_for_scope(period, store, section, catalog):
        try:
            entry = m._capacity_source_entry(period) or {}
            source_id = str(entry.get("id") or entry.get("uploaded_at") or "latest")
        except Exception:
            source_id = "latest"
        key = (source_id, str(store), str(section), str(catalog))
        now = time.monotonic()
        with meta_lock:
            hit = meta_cache.get(key)
            if hit and now - hit[0] < 600:
                return hit[1]

        area_map, status_map, offer_map = {}, {}, {}
        try:
            frame = m._capacity_frame_for_period(period)
            work = m._capacity_scope_v45(frame, store, section, catalog, add_area=True)
            if work is not None and not work.empty and "ID_ART" in work.columns:
                ids = work["ID_ART"].fillna("").astype(str).str.strip()
                valid = ~ids.isin(["", "nan", "None"])
                base = pd.DataFrame({"__id": ids.loc[valid]})

                if "Área reporte" in work.columns:
                    area = work.loc[valid, "Área reporte"].fillna("").astype(str).str.strip()
                    at = pd.DataFrame({"__id": base["__id"], "area": area.values})
                    at = at[at["area"].isin(physical_areas)].drop_duplicates()
                    if not at.empty:
                        area_map = at.groupby("__id", sort=False)["area"].agg(
                            lambda s: list(dict.fromkeys(str(x) for x in s if str(x)))
                        ).to_dict()

                if "Estatus comercial" in work.columns:
                    status = work.loc[valid, "Estatus comercial"].fillna("").astype(str).str.strip()
                    st = pd.DataFrame({"__id": base["__id"], "status": status.values})
                    st = st[~st["status"].isin(["", "nan", "None"])].drop_duplicates()
                    if not st.empty:
                        status_map = st.groupby("__id", sort=False)["status"].agg(
                            lambda s: " / ".join(list(dict.fromkeys(str(x) for x in s if str(x)))[:5])
                        ).to_dict()
                        st["__offer"] = st["status"].map(m.login_key).isin(offer_keys)
                        offer_map = st.groupby("__id", sort=False)["__offer"].any().to_dict()
        except Exception as exc:
            print(f"[V198-META] {type(exc).__name__}: {exc}", flush=True)

        payload = (area_map, status_map, offer_map)
        with meta_lock:
            if len(meta_cache) >= 10:
                meta_cache.pop(next(iter(meta_cache)))
            meta_cache[key] = (now, payload)
        return payload

    base_model_rows = getattr(m, "_capacity_model_rows", None)
    if callable(base_model_rows) and not getattr(base_model_rows, "_v198_wrapped", False):
        def v198_model_rows(
            store: str = "Compañía", section: str = "Todas",
            mode: str = "80_20", period: str = "", catalog: str = "Todos",
        ):
            rows = list(base_model_rows(store, section, mode, period, catalog) or [])
            if not rows:
                return rows
            area_map, status_map, offer_map = _meta_for_scope(period, store, section, catalog)
            for row in rows:
                rid = str(row.get("id_art") or "")
                row["area_groups"] = list(area_map.get(rid, []) or [])
                row["commercial_status"] = str(status_map.get(rid, "") or "")
                row["offer"] = bool(offer_map.get(rid, False))
            return rows
        v198_model_rows._v198_wrapped = True
        m._capacity_model_rows = v198_model_rows

    area_base = None
    for route in list(m.app.router.routes):
        if getattr(route, "path", None) == "/api/commercial-area-v176" and "GET" in (getattr(route, "methods", set()) or set()):
            area_base = getattr(route, "endpoint", None)

    def _is_company(value):
        return m.login_key(value) in ("", m.login_key("Compañía"), "company")

    def _offer_rows(period, selected, section, catalog):
        try:
            frame = m._capacity_frame_for_period(period)
            work = m._capacity_scope_v45(frame, selected, section, catalog, add_area=True)
            if work is None or work.empty or "Estatus comercial" not in work.columns:
                return []
            mask = work["Estatus comercial"].fillna("").astype(str).map(m.login_key).isin(offer_keys)
            offer = work[mask]
            if offer.empty:
                return []

            company = _is_company(selected)
            group_cols = ["Tienda", "Sección"] if company else ["Sección"]
            rows = []
            for keys, group in offer.groupby(group_cols, dropna=False, sort=False, observed=True):
                if company:
                    store_name, section_name = keys if isinstance(keys, tuple) else (keys, "Sin sección")
                else:
                    store_name, section_name = selected, keys
                metrics = m._capacity_metrics(group, period)
                ids = 0
                if "ID_ART" in group.columns:
                    model_ids = group["ID_ART"].fillna("").astype(str).str.strip()
                    ids = int(model_ids[~model_ids.isin(["", "nan", "None"])].nunique())
                rows.append({
                    "store": str(store_name or selected),
                    "group": "Oferta",
                    "location": "Oferta",
                    "section": str(section_name or "Sin sección"),
                    "ids": ids,
                    **metrics,
                })
            sec_order = {"Dama": 1, "Caballero": 2, "Infantil": 3, "Sin sección": 9}
            rows.sort(key=lambda r: (
                m.login_key(r.get("store")),
                sec_order.get(str(r.get("section") or ""), 8),
                str(r.get("section") or ""),
            ))
            return rows
        except Exception as exc:
            print(f"[V198-OFFER] {type(exc).__name__}: {exc}", flush=True)
            return []

    @m.app.get("/api/commercial-area-v198")
    def commercial_area_v198(
        request: Request, week: str = "", store: str = "Compañía",
        section: str = "Todas", catalog: str = "Todos",
    ):
        if not callable(area_base):
            return {"store": store, "mode": "grouped", "rows": [], "groups": list(physical_areas) + ["Oferta"]}
        base = dict(area_base(request=request, week=week, store=store, section=section, catalog=catalog) or {})
        selected = str(base.get("store") or store or "Compañía")
        rows = [dict(r) for r in (base.get("rows") or []) if str(r.get("group") or "") != "Oferta"]
        rows.extend(_offer_rows(week, selected, section, catalog))
        order = {"Colgado": 1, "Doblado": 2, "Jeans": 3, "Lencería": 4, "Oferta": 5}
        rows.sort(key=lambda r: (
            order.get(str(r.get("group") or ""), 99),
            m.login_key(r.get("store")),
            str(r.get("section") or ""),
            -float(r.get("suggested") or 0),
        ))
        base["rows"] = rows
        base["groups"] = list(physical_areas) + ["Oferta"]
        return base

    css = r'''<style id="v198-commercial-area-offer-css">
.v198-detail{margin:9px 0 14px;border:1px solid #d8e3ef;border-radius:11px;background:#fff;overflow:hidden}
.v198-detail>summary{list-style:none;cursor:pointer;padding:10px 12px;font-size:10px;font-weight:950;color:#13477f;background:#f7faff;display:flex;align-items:center;gap:7px;user-select:none}
.v198-detail>summary::-webkit-details-marker{display:none}
.v198-detail>summary:before{content:'+';display:inline-grid;place-items:center;width:20px;height:20px;border:1px solid #b9cce1;border-radius:50%;font-size:15px;line-height:1;color:#1769e8;background:#fff}
.v198-detail[open]>summary:before{content:'−'}
.v198-detail>.tablewrap{margin:0!important;border:0!important;border-radius:0!important}
.v198-area-summary{margin:8px 0 10px}
.v198-area-summary .table{min-width:920px}
.v198-area-summary .v198-zero td{color:#6b778c}
.v198-summary-label{font-weight:950;color:#123b73}
#macroAreaGroupSwitch [data-area-group="Oferta"]{white-space:nowrap}
@media(max-width:900px){
  .v198-detail>summary{font-size:8px;padding:8px 9px}
  .v198-area-summary .table{min-width:780px}
}
</style>'''

    js = r'''<script id="v198-commercial-area-offer-js">
(function(){
  if(window.__V198_COMMERCIAL_AREA_OFFER)return;
  window.__V198_COMMERCIAL_AREA_OFFER=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const AREAS=['Colgado','Doblado','Jeans','Lencería','Oferta'];
  const modelPayloads={};
  let setupTimer=0;
  let offerRequest=0;
  let summaryLoadKey='';
  let summaryLoadBusy=false;
  let summaryObserver=null;
  let summaryObservedNode=null;

  const nativeFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    let url=typeof input==='string'?input:(input&&input.url)||'';
    if(url.includes('/api/commercial-area-v176')){
      const next=url.replace('/api/commercial-area-v176','/api/commercial-area-v198');
      input=typeof input==='string'?next:new Request(next,input);
      url=next;
    }
    const promise=nativeFetch(input,init);
    if(url.includes('/api/commercial-models-v176')){
      promise.then(res=>{
        try{
          const u=new URL(url,location.origin);
          const mode=u.searchParams.get('mode')||'all';
          res.clone().json().then(data=>{
            modelPayloads[mode]=data||{};
            setTimeout(renderAllSummaries,0);
          }).catch(()=>{});
        }catch(_){}
      }).catch(()=>{});
    }
    return promise;
  };

  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const x=Number(v||0);return Number.isFinite(x)?x:0};
  const nf=v=>Math.round(num(v)).toLocaleString('es-MX');
  const money=v=>'$'+Math.round(num(v)).toLocaleString('es-MX');
  const pct=v=>v==null||!Number.isFinite(Number(v))?'N/D':Number(v).toFixed(1)+'%';
  const norm=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase().replace(/\s+/g,' ');

  function removeCompanyComparison(){
    const title=q('#macroRankingTitle');
    if(!title)return;
    const panel=title.nextElementSibling;
    if(panel&&panel.classList.contains('panel'))panel.remove();
    title.remove();
  }

  function ensureOfferTab(){
    const group=q('#macroAreaGroupSwitch');
    if(!group)return;
    let btn=q('[data-area-group="Oferta"]',group);
    if(!btn){
      btn=document.createElement('button');
      btn.type='button';
      btn.className='switch';
      btn.dataset.areaGroup='Oferta';
      btn.innerHTML='<span aria-hidden="true" style="font-size:13px">◇</span><span>Oferta</span>';
      group.appendChild(btn);
    }
  }

  function wrapDetail(tableId,detailsId,label,onOpen){
    const body=q('#'+tableId),wrap=body&&body.closest('.tablewrap');
    if(!wrap)return null;
    let details=q('#'+detailsId);
    if(!details){
      details=document.createElement('details');
      details.id=detailsId;
      details.className='v198-detail';
      const summary=document.createElement('summary');
      summary.textContent=label;
      wrap.parentNode.insertBefore(details,wrap);
      details.append(summary,wrap);
      if(onOpen)details.addEventListener('toggle',()=>{if(details.open)onOpen()});
    }
    return details;
  }

  function ensureSummaryShell(tableId,summaryId,detailsId,label){
    const body=q('#'+tableId),wrap=body&&body.closest('.tablewrap');
    if(!wrap)return;
    let host=q('#'+summaryId);
    if(!host){
      host=document.createElement('div');
      host.id=summaryId;
      wrap.parentNode.insertBefore(host,wrap);
    }
    wrapDetail(tableId,detailsId,label,null);
  }

  function ensureShells(){
    wrapDetail('macroAreaTable','v198AreaDetails','Detalle ubicación',()=>{
      if(activeArea()==='Oferta')renderOfferArea();
      else if(typeof window.loadMacroAreaDetail==='function')window.loadMacroAreaDetail();
    });
    ensureSummaryShell('champTable','v198ChampSummary','v198ChampDetails','Detalle 80/20');
    ensureSummaryShell('slowTable','v198SlowSummary','v198SlowDetails','Detalle modelos lentos');
    ensureSummaryShell('zeroTable','v198ZeroSummary','v198ZeroDetails','Detalle sugerido 0 a 1');
  }

  function rowGroups(row){
    const out=[];
    const supplied=Array.isArray(row&&row.area_groups)?row.area_groups:[];
    supplied.forEach(x=>{x=String(x||'');if(AREAS.includes(x)&&!out.includes(x))out.push(x)});
    if(!supplied.length){
      const raw=norm(row&&(row.location||row.area||row.location_type||row.type_location));
      if(raw.includes('colgad'))out.push('Colgado');
      if(raw.includes('doblad')||raw.includes('mesa'))out.push('Doblado');
      if(raw.includes('jean')||raw.includes('fergino')||raw.includes('seven')||raw.includes('mezclilla'))out.push('Jeans');
      if(raw.includes('lencer'))out.push('Lencería');
    }
    const status=norm(row&&row.commercial_status);
    if((row&&row.offer)||status.includes('oferta')||status.includes('gran remate')||status.includes('outlet')){
      if(!out.includes('Oferta'))out.push('Oferta');
    }
    return out;
  }

  function summaryRows(rows){
    return AREAS.map(area=>{
      const subset=(rows||[]).filter(r=>rowGroups(r).includes(area));
      const ids=new Set(subset.map(r=>String(r.id_art||'')).filter(Boolean));
      const sum=k=>subset.reduce((a,r)=>a+num(r&&r[k]),0);
      const suggested=sum('suggested'),capacity=sum('capacity'),existence=sum('existence');
      const weighted=subset.reduce((a,r)=>a+num(r&&r.ddi)*Math.max(num(r&&r.suggested),0),0);
      const ddi=suggested>0?weighted/suggested:(subset.length?subset.reduce((a,r)=>a+num(r&&r.ddi),0)/subset.length:0);
      return {area:area,models:ids.size,sales_pzas:sum('sales_pzas'),sales_value:sum('sales_value'),
        existence:existence,cedis:sum('cedis'),suggested:suggested,ddi:ddi,capacity:capacity,
        occupancy:capacity>0?existence/capacity*100:null};
    });
  }

  function renderSummary(id,rows,loaded,errorText){
    const host=q('#'+id);
    if(!host)return;
    if(!loaded){
      host.innerHTML='<div class="tablewrap v198-area-summary"><table class="table"><thead><tr>'+
        '<th>Área</th><th>Modelos</th><th>Vta pzas</th><th>Venta $</th><th>Existencia</th>'+
        '<th>Exist. CEDIS</th><th>Sugerido 7</th><th>DDI 7</th><th>Capacidad</th><th>% Ocupación</th>'+
        '</tr></thead><tbody><tr><td colspan="10">'+esc(errorText||'Cargando información real del reporte…')+'</td></tr></tbody></table></div>';
      return;
    }
    const data=summaryRows(rows);
    host.innerHTML='<div class="tablewrap v198-area-summary"><table class="table"><thead><tr>'+
      '<th>Área</th><th>Modelos</th><th>Vta pzas</th><th>Venta $</th><th>Existencia</th>'+
      '<th>Exist. CEDIS</th><th>Sugerido 7</th><th>DDI 7</th><th>Capacidad</th><th>% Ocupación</th>'+
      '</tr></thead><tbody>'+
      data.map(r=>'<tr class="'+(r.models?'':'v198-zero')+'"><td class="v198-summary-label">'+esc(r.area)+'</td>'+
        '<td>'+nf(r.models)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td>'+
        '<td>'+nf(r.existence)+'</td><td>'+nf(r.cedis)+'</td>'+
        '<td>'+num(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td>'+
        '<td>'+nf(r.ddi)+'</td><td>'+nf(r.capacity)+'</td><td>'+pct(r.occupancy)+'</td></tr>').join('')+
      '</tbody></table></div>';
  }

  function sectionFiltered(rows){
    const sel=q('#slowSection');
    const wanted=sel?String(sel.value||'Todas'):'Todas';
    if(wanted==='Todas')return rows||[];
    const key=norm(wanted);
    return (rows||[]).filter(r=>norm(r&&r.section).startsWith(key));
  }

  function renderPrecomputedSummary(id,rows,errorText){
    const host=q('#'+id);if(!host)return;
    if(errorText){
      host.innerHTML='<div class="tablewrap v198-area-summary"><table class="table"><thead><tr><th>Área</th><th>Modelos</th><th>Vta pzas</th><th>Venta $</th><th>Existencia</th><th>Exist. CEDIS</th><th>Sugerido 7</th><th>DDI 7</th><th>Capacidad</th><th>% Ocupación</th></tr></thead><tbody><tr><td colspan="10">'+esc(errorText)+'</td></tr></tbody></table></div>';
      return;
    }
    if(!rows){
      renderSummary(id,[],false,'Cargando resumen optimizado…');return;
    }
    host.innerHTML='<div class="tablewrap v198-area-summary"><table class="table"><thead><tr><th>Área</th><th>Modelos</th><th>Vta pzas</th><th>Venta $</th><th>Existencia</th><th>Exist. CEDIS</th><th>Sugerido 7</th><th>DDI 7</th><th>Capacidad</th><th>% Ocupación</th></tr></thead><tbody>'+
      rows.map(r=>'<tr class="'+(Number(r.models||0)?'':'v198-zero')+'"><td class="v198-summary-label">'+esc(r.area)+'</td><td>'+nf(r.models)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td><td>'+nf(r.existence)+'</td><td>'+nf(r.cedis)+'</td><td>'+n(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td><td>'+nf(r.ddi)+'</td><td>'+nf(r.capacity)+'</td><td>'+(r.occupancy==null?'N/D':pct(r.occupancy))+'</td></tr>').join('')+
      '</tbody></table></div>';
  }

  function renderAllSummaries(){
    ensureShells();
    if(modelPayloads.__v199summary||modelPayloads.__v199error){
      const s=modelPayloads.__v199summary||{};
      renderPrecomputedSummary('v198ChampSummary',s['80_20'],modelPayloads.__v199error);
      renderPrecomputedSummary('v198SlowSummary',s.slow,modelPayloads.__v199error);
      renderPrecomputedSummary('v198ZeroSummary',s.suggested_zero,modelPayloads.__v199error);
      return;
    }
    const champData=modelPayloads['80_20'];
    const slowData=modelPayloads.slow;
    const zeroData=modelPayloads.suggested_zero;
    const champ=(champData&&champData.champions)||[];
    const slow=sectionFiltered((slowData&&slowData.slow)||[]);
    const zero=sectionFiltered((zeroData&&zeroData.zero)||[]);
    renderSummary('v198ChampSummary',champ,!!champData&&!champData.__error,champData&&champData.__error);
    renderSummary('v198SlowSummary',slow,!!slowData&&!slowData.__error,slowData&&slowData.__error);
    renderSummary('v198ZeroSummary',zero,!!zeroData&&!zeroData.__error,zeroData&&zeroData.__error);
  }

  function summaryContextKey(){
    return [
      currentWeek(),
      currentStore(),
      q('#section')?.value||'Todas',
      currentCatalog()
    ].join('|');
  }

  async function loadSummaryData(force){
    const page=q('#page-macro');
    if(!page||!page.classList.contains('active')||!currentWeek())return;
    const key=summaryContextKey();
    if(!force&&summaryLoadKey===key&&modelPayloads.__v199summary)return;
    if(summaryLoadBusy&&summaryLoadKey===key)return;

    if(summaryLoadKey!==key||force){
      delete modelPayloads.__v199summary;
      delete modelPayloads.__v199error;
      renderAllSummaries();
    }
    summaryLoadKey=key;
    summaryLoadBusy=true;
    const section=q('#section')?.value||'Todas';
    const url='/api/commercial-model-summaries-v199?week='+encodeURIComponent(currentWeek())+
      '&store='+encodeURIComponent(currentStore())+
      '&section='+encodeURIComponent(section)+
      '&catalog='+encodeURIComponent(currentCatalog());
    try{
      const res=await nativeFetch(url,{credentials:'same-origin'});
      if(!res.ok){
        let detail='HTTP '+res.status;
        try{const j=await res.clone().json();detail=j.detail||j.message||detail}catch(_){}
        throw Error(detail);
      }
      const data=await res.json();
      if(key!==summaryContextKey())return;
      modelPayloads.__v199summary=(data&&data.summaries)||{};
      delete modelPayloads.__v199error;
    }catch(e){
      modelPayloads.__v199error='No fue posible cargar el resumen. '+String(e&&e.message||e);
    }finally{
      if(key===summaryContextKey())summaryLoadBusy=false;
      renderAllSummaries();
    }
  }

  function armLazySummaryLoad(){
    const node=q('#v198ChampSummary');
    if(!node)return;
    if(summaryObservedNode===node&&summaryObserver)return;
    try{summaryObserver?.disconnect?.()}catch(_){}
    summaryObservedNode=node;
    if('IntersectionObserver' in window){
      summaryObserver=new IntersectionObserver(entries=>{
        if(entries.some(x=>x.isIntersecting)){
          summaryObserver.disconnect();
          summaryObserver=null;
          summaryObservedNode=null;
          loadSummaryData(false);
        }
      },{root:null,rootMargin:'420px 0px 420px 0px',threshold:0.01});
      summaryObserver.observe(node);
    }else{
      setTimeout(()=>loadSummaryData(false),900);
    }
  }

  function wrapModelRenderer(){
    if(typeof window.renderModelRows!=='function'||window.renderModelRows.__v198)return;
    const base=window.renderModelRows;
    const wrapped=function(){
      const result=base.apply(this,arguments);
      ensureShells();
      setTimeout(renderAllSummaries,0);
      return result;
    };
    wrapped.__v198=true;
    window.renderModelRows=wrapped;
  }

  function activeArea(){
    const b=q('#macroAreaGroupSwitch [data-area-group].active');
    return b?String(b.dataset.areaGroup||'Todas'):'Todas';
  }

  function currentStore(){
    return q('#v161FilterGrid select[data-source="store"]')?.value||q('#store')?.value||'Compañía';
  }
  function currentSection(){
    return q('#macroAreaSectionSwitch [data-area-section].active')?.dataset.areaSection||'Todas';
  }
  function currentWeek(){return q('#week')?.value||''}
  function currentCatalog(){return q('#catalog')?.value||'Todos'}

  async function renderOfferArea(){
    if(activeArea()!=='Oferta'||!q('#macroAreaTable'))return;
    const request=++offerRequest;
    const url='/api/commercial-area-v198?week='+encodeURIComponent(currentWeek())+
      '&store='+encodeURIComponent(currentStore())+
      '&section='+encodeURIComponent(currentSection())+
      '&catalog='+encodeURIComponent(currentCatalog());
    try{
      const res=await nativeFetch(url,{credentials:'same-origin'});
      if(!res.ok)throw Error('HTTP '+res.status);
      const data=await res.json();
      if(request!==offerRequest||activeArea()!=='Oferta')return;
      const rows=(data.rows||[]).filter(r=>r.group==='Oferta');
      const body=q('#macroAreaTable'),table=body&&body.closest('table'),head=table&&table.querySelector('thead tr');
      if(!body||!head)return;
      const company=(data.mode==='grouped');
      if(company){
        head.innerHTML='<th>Tienda</th><th>Sección</th><th>Modelos</th><th>Curva</th><th>Piso</th><th>Bodega</th><th>Existencia</th><th>Sugerido 7</th><th>DDI 7</th><th>Vta pzas</th><th>Venta $</th><th>% Ocupación</th>';
        body.innerHTML=rows.length?rows.map(r=>'<tr><td>'+esc(r.store)+'</td><td><b>'+esc(r.section||'Sin sección')+'</b></td>'+
          '<td>'+nf(r.ids)+'</td><td>'+nf(r.capacity)+'</td><td>'+nf(r.floor)+'</td><td>'+nf(r.warehouse)+'</td>'+
          '<td>'+nf(r.existence)+'</td><td>'+num(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td>'+
          '<td>'+nf(r.ddi)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td><td>'+pct(r.occupancy)+'</td></tr>').join(''):
          '<tr><td colspan="12">Sin modelos con estatus Oferta para este filtro.</td></tr>';
      }else{
        head.innerHTML='<th>Sección</th><th>Grupo</th><th>Modelos</th><th>Curva</th><th>Piso</th><th>Bodega</th><th>Existencia</th><th>Sugerido 7</th><th>DDI 7</th><th>Vta pzas</th><th>Venta $</th><th>% Ocupación</th>';
        body.innerHTML=rows.length?rows.map(r=>'<tr><td><b>'+esc(r.section||'Sin sección')+'</b></td><td>Oferta</td>'+
          '<td>'+nf(r.ids)+'</td><td>'+nf(r.capacity)+'</td><td>'+nf(r.floor)+'</td><td>'+nf(r.warehouse)+'</td>'+
          '<td>'+nf(r.existence)+'</td><td>'+num(r.suggested).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td>'+
          '<td>'+nf(r.ddi)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+money(r.sales_value)+'</td><td>'+pct(r.occupancy)+'</td></tr>').join(''):
          '<tr><td colspan="12">Sin modelos con estatus Oferta para este filtro.</td></tr>';
      }
      const title=q('#macroAreaTitle');
      if(title)title.textContent='Ubicación · '+currentStore()+(currentSection()!=='Todas'?' · '+currentSection():'')+' · Oferta';
    }catch(e){
      const body=q('#macroAreaTable');
      if(body)body.innerHTML='<tr><td colspan="12">No fue posible consultar Oferta: '+esc(e.message||e)+'</td></tr>';
    }
  }

  function activateOffer(button){
    const group=q('#macroAreaGroupSwitch');
    if(!group)return;
    qa('[data-area-group]',group).forEach(x=>x.classList.toggle('active',x===button));
    setTimeout(renderOfferArea,140);
    setTimeout(renderOfferArea,360);
  }

  function setup(){
    clearTimeout(setupTimer);
    removeCompanyComparison();
    ensureOfferTab();
    ensureShells();
    wrapModelRenderer();
    renderAllSummaries();
    armLazySummaryLoad();
    if(activeArea()==='Oferta')setTimeout(renderOfferArea,80);
  }

  document.addEventListener('click',event=>{
    const offer=event.target.closest&&event.target.closest('#macroAreaGroupSwitch [data-area-group="Oferta"]');
    if(offer)activateOffer(offer);
    if(event.target.closest&&event.target.closest('#macroAreaSectionSwitch [data-area-section]')&&activeArea()==='Oferta'){
      setTimeout(renderOfferArea,220);
    }
    if(event.target.closest&&event.target.closest('#analysisNav,[data-main="analysis"],#refresh')){
      setTimeout(setup,180);
      setTimeout(setup,700);
    }
    if(event.target.closest&&event.target.closest('#v176SlowSectionTabs button')){
      setTimeout(renderAllSummaries,100);
    }
  },true);

  document.addEventListener('change',event=>{
    if(event.target.matches&&event.target.matches('#store,#week,#section,#catalog,#v161FilterGrid select')){
      summaryLoadKey='';
      delete modelPayloads['80_20'];delete modelPayloads.slow;delete modelPayloads.suggested_zero;delete modelPayloads.__v199summary;delete modelPayloads.__v199error;
      try{summaryObserver?.disconnect?.()}catch(_){}
      summaryObserver=null;summaryObservedNode=null;
      setTimeout(setup,180);
      if(activeArea()==='Oferta')setTimeout(renderOfferArea,320);
    }
    if(event.target.matches&&event.target.matches('#slowSection')){
      setTimeout(renderAllSummaries,80);
    }
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});
  else setup();
  [250,700,1500,3000].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('pageshow',()=>setTimeout(setup,100),{passive:true});
  console.info('[V198] Oferta, resúmenes por área y detalles colapsables instalados.');
})();
</script>'''

    @m.app.middleware("http")
    async def v198_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v198-commercial-area-offer-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v198-commercial-area-offer-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V198",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V198] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V198_COMMERCIAL_AREA_OFFER = True
    print("[V198] Comercial Oferta + resúmenes por área + detalles instalado.", flush=True)
