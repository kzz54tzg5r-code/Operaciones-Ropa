"""V201 · Demo de Operación basado en ventas reales disponibles desde abril.

El demo es de sólo lectura y sólo se construye bajo demanda. No escribe datos
operativos ni sustituye capturas reales. Usa la venta/piezas disponible como
escala y genera estimaciones operativas explícitamente etiquetadas como DEMO.
"""
from __future__ import annotations

import inspect
import math
import threading
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V201_OPERATION_SALES_DEMO", False):
        return

    sales_endpoint = None
    for route in list(m.app.router.routes):
        if getattr(route, "path", None) == "/api/commercial-sales-v176" and "GET" in (getattr(route, "methods", set()) or set()):
            sales_endpoint = getattr(route, "endpoint", None)
            break

    cache = {}
    cache_lock = threading.RLock()

    def _num(value):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def _workdays(start: date, end: date):
        if end < start:
            return 1
        cur = start
        total = 0
        while cur <= end:
            if cur.weekday() < 5:
                total += 1
            cur = cur.fromordinal(cur.toordinal() + 1)
        return max(total, 1)

    def _seed(name: str):
        return sum((i + 1) * ord(ch) for i, ch in enumerate(str(name or ""))) % 997

    def _canonical_map(rows):
        return {m.login_key(r.get("store")): dict(r) for r in (rows or []) if str(r.get("store") or "").strip()}

    async def _build_demo(request):
        if not callable(sales_endpoint):
            raise HTTPException(503, "La fuente de ventas no está disponible")

        now = datetime.now(MX)
        year = now.year
        cache_key = f"{year}-{now.month}"
        with cache_lock:
            hit = cache.get(cache_key)
            if hit and time.monotonic() - hit[0] < 900:
                return hit[1]

        sales = sales_endpoint(request=request, year=year, month=0, store="Compañía")
        if inspect.isawaitable(sales):
            sales = await sales
        sales = dict(sales or {})

        # La demo usa únicamente meses desde abril con información disponible.
        month_rows = []
        for raw in sales.get("months") or []:
            row = dict(raw or {})
            mo = int(row.get("month") or 0)
            loaded = bool(row.get("pdf_loaded"))
            has_data = _num(row.get("pieces")) > 0 or _num(row.get("current")) > 0
            if mo >= 4 and mo <= now.month and (loaded or has_data):
                month_rows.append(row)

        if not month_rows:
            # Si la fuente no marcó pdf_loaded, conservar abril→mes actual con datos.
            month_rows = [
                dict(r or {}) for r in (sales.get("months") or [])
                if 4 <= int((r or {}).get("month") or 0) <= now.month
                and (_num((r or {}).get("pieces")) > 0 or _num((r or {}).get("current")) > 0)
            ]

        total_sales_pieces = sum(_num(r.get("pieces")) for r in month_rows)
        total_sales_value = sum(_num(r.get("current")) for r in month_rows)

        # Si la fuente de piezas viene vacía, usar sólo para escala demo una
        # conversión aproximada desde $; se etiqueta en el payload.
        pieces_fallback = False
        if total_sales_pieces <= 0 and total_sales_value > 0:
            total_sales_pieces = total_sales_value / 250.0
            pieces_fallback = True

        active_stores = list(m.store_names(True) or [])
        if not active_stores:
            active_stores = [
                "Iztapalapa","Vallejo","Ecatepec","Toluca","Arco Norte","Ixtapaluca",
                "Querétaro","Centro","Olivar","León","Puebla","Puebla Sur",
                "Aguascalientes","Veracruz","Naucalpan","Miravalle","Atemajac",
            ]

        source_map = _canonical_map(sales.get("stores") or [])
        raw_weights = {}
        positives = []
        for store in active_stores:
            src = source_map.get(m.login_key(store), {})
            w = _num(src.get("pieces"))
            if w <= 0:
                w = _num(src.get("current")) / 250.0
            raw_weights[store] = w
            if w > 0:
                positives.append(w)

        fallback_weight = (sorted(positives)[len(positives)//2] * 0.35) if positives else 1.0
        for store in active_stores:
            if raw_weights[store] <= 0:
                raw_weights[store] = fallback_weight
        weight_total = sum(raw_weights.values()) or 1.0

        period_start = date(year, 4, 1)
        period_end = now.date()
        workdays = _workdays(period_start, period_end)
        goals = m.get_goals() if hasattr(m, "get_goals") else {}
        productivity_target = _num((goals or {}).get("productividad_diaria")) or 784.0

        stores = []
        for store in active_stores:
            share = raw_weights[store] / weight_total
            sales_pieces = total_sales_pieces * share
            sales_value = total_sales_value * share
            s = _seed(store)

            # Estimaciones DEMO: sólo dan escala y variación visual.
            arrival = sales_pieces * (1.10 + (s % 9) / 100.0)
            efficiency = 90.0 + (s % 74) / 10.0  # 90.0% – 97.3%
            processed = arrival * efficiency / 100.0
            release_rate = 95.0 + ((s // 7) % 30) / 10.0  # 95.0% – 97.9%
            released = processed * release_rate / 100.0
            pending = max(arrival - released, 0.0)

            desired_prod = productivity_target * (0.91 + ((s // 11) % 19) / 100.0)
            collaborators = max(3, int(round(processed / max(desired_prod * workdays, 1))))
            productivity = processed / max(collaborators * workdays, 1)
            compliance = productivity / productivity_target * 100.0 if productivity_target else 0.0

            # Distribución por áreas/actividades sólo para visualización demo.
            colgado = arrival * (0.36 + (s % 5) / 100.0)
            doblado = arrival * (0.33 + ((s // 3) % 4) / 100.0)
            jeans = arrival * (0.18 + ((s // 5) % 3) / 100.0)
            lenceria = max(arrival - colgado - doblado - jeans, 0.0)
            acondicionado = processed * (0.36 + (s % 4) / 100.0)
            clasificado = processed * (0.29 + ((s // 4) % 4) / 100.0)
            ubicado = max(processed - acondicionado - clasificado, 0.0)

            stores.append({
                "store": store,
                "sales_pieces": sales_pieces,
                "sales_value": sales_value,
                "share": share * 100.0,
                "arrival": arrival,
                "processed": processed,
                "released": released,
                "pending": pending,
                "efficiency": efficiency,
                "productivity": productivity,
                "compliance": compliance,
                "collaborators": collaborators,
                "areas": {
                    "Colgado": colgado, "Doblado": doblado,
                    "Jeans": jeans, "Lencería": lenceria,
                },
                "activities": {
                    "Acondicionado": acondicionado,
                    "Clasificado": clasificado,
                    "Ubicado": ubicado,
                },
            })

        stores.sort(key=lambda r: (-r["sales_pieces"], m.login_key(r["store"])))
        for idx, row in enumerate(stores, 1):
            row["rank"] = idx

        # Ranking DEMO por colaborador. Se reutilizan nombres/nóminas reales ya
        # registrados cuando existen; las tiendas sin plantilla suficiente se
        # completan con colaboradores DEMO para poder visualizar el reporte.
        roster = {}
        def add_person(store_name, employee_no, employee_name):
            st = str(store_name or "").strip()
            name = " ".join(str(employee_name or "").strip().split())
            no = str(employee_no or "").strip()
            if not st or not name:
                return
            key = m.login_key(st)
            bucket = roster.setdefault(key, [])
            dedup = (m.login_key(no), m.login_key(name))
            if any((m.login_key(x.get("employee_no")), m.login_key(x.get("name"))) == dedup for x in bucket):
                return
            bucket.append({"store": st, "employee_no": no, "name": name, "synthetic": False})

        try:
            with m.db() as con:
                try:
                    rows = con.execute(
                        """SELECT store,employee_no,
                                  COALESCE(NULLIF(TRIM(full_name),''),username) AS employee_name
                           FROM users
                           WHERE active=1 AND TRIM(COALESCE(store,''))<>''"""
                    ).fetchall()
                    for r in rows:
                        add_person(r["store"], r["employee_no"], r["employee_name"])
                except Exception:
                    pass
                try:
                    rows = con.execute(
                        """SELECT DISTINCT store,employee_no,employee_name
                           FROM operation_productivity
                           WHERE TRIM(COALESCE(store,''))<>'' AND TRIM(COALESCE(employee_name,''))<>''"""
                    ).fetchall()
                    for r in rows:
                        add_person(r["store"], r["employee_no"], r["employee_name"])
                except Exception:
                    pass
                try:
                    rows = con.execute(
                        """SELECT DISTINCT store,employee_no,employee_name
                           FROM operation_productivity_timer
                           WHERE TRIM(COALESCE(store,''))<>'' AND TRIM(COALESCE(employee_name,''))<>''"""
                    ).fetchall()
                    for r in rows:
                        add_person(r["store"], r["employee_no"], r["employee_name"])
                except Exception:
                    pass
        except Exception:
            pass

        collaborator_rows = []
        areas = ("Doblado","Colgado","Jeans","Lencería")
        activities = ("Acondicionado","Clasificado","Ubicado")
        store_lookup = {m.login_key(r["store"]): r for r in stores}
        for store in active_stores:
            skey = m.login_key(store)
            base_store = store_lookup.get(skey) or {}
            people = list(roster.get(skey) or [])
            wanted = max(3, min(8, int(base_store.get("collaborators") or 3)))
            while len(people) < wanted:
                pos = len(people) + 1
                people.append({
                    "store": store,
                    "employee_no": f"DEMO-{(active_stores.index(store)+1):02d}-{pos:02d}",
                    "name": f"Colaborador Demo {pos:02d}",
                    "synthetic": True,
                })
            people = people[:max(wanted, len(roster.get(skey) or []))]
            base_prod = _num(base_store.get("productivity")) or productivity_target
            for pos, person in enumerate(people, 1):
                ps = _seed(f"{store}|{person.get('employee_no')}|{person.get('name')}|{pos}")
                factor = 0.84 + (ps % 35) / 100.0
                daily_productivity = base_prod * factor
                area = areas[ps % len(areas)]
                activity = activities[(ps // 5) % len(activities)]
                collaborator_rows.append({
                    "store": store,
                    "employee_no": str(person.get("employee_no") or ""),
                    "name": str(person.get("name") or ""),
                    "synthetic": bool(person.get("synthetic")),
                    "area": area,
                    "activity": activity,
                    "daily_productivity": daily_productivity,
                    "pieces": daily_productivity * workdays,
                    "compliance": daily_productivity / productivity_target * 100.0 if productivity_target else 0.0,
                })

        collaborator_rows.sort(key=lambda r: (-r["daily_productivity"], m.login_key(r["name"])))
        for idx, row in enumerate(collaborator_rows, 1):
            row["global_rank"] = idx

        company = {
            "sales_pieces": sum(r["sales_pieces"] for r in stores),
            "sales_value": sum(r["sales_value"] for r in stores),
            "arrival": sum(r["arrival"] for r in stores),
            "processed": sum(r["processed"] for r in stores),
            "released": sum(r["released"] for r in stores),
            "pending": sum(r["pending"] for r in stores),
            "collaborators": sum(r["collaborators"] for r in stores),
        }
        company["efficiency"] = company["processed"] / company["arrival"] * 100.0 if company["arrival"] else 0.0
        company["productivity"] = company["processed"] / max(company["collaborators"] * workdays, 1)
        company["compliance"] = company["productivity"] / productivity_target * 100.0 if productivity_target else 0.0

        company["areas"] = {
            area: sum(r["areas"][area] for r in stores)
            for area in ("Colgado","Doblado","Jeans","Lencería")
        }
        company["activities"] = {
            act: sum(r["activities"][act] for r in stores)
            for act in ("Acondicionado","Clasificado","Ubicado")
        }

        month_labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        trend = []
        total_month_piece_source = sum(_num(r.get("pieces")) for r in month_rows)
        for row in month_rows:
            mo = int(row.get("month") or 0)
            p = _num(row.get("pieces"))
            if p <= 0 and _num(row.get("current")) > 0:
                p = _num(row.get("current")) / 250.0
            arrival = p * 1.14
            eff = 93.4 + ((mo * 7) % 18) / 10.0
            processed = arrival * eff / 100.0
            trend.append({
                "month": mo,
                "label": month_labels[mo-1] if 1 <= mo <= 12 else str(mo),
                "sales_pieces": p,
                "arrival": arrival,
                "processed": processed,
                "efficiency": eff,
            })

        period_label = "Abr"
        if trend:
            period_label = f"{trend[0]['label']} – {trend[-1]['label']} {year}"

        payload = {
            "demo": True,
            "read_only": True,
            "year": year,
            "period_label": period_label,
            "workdays": workdays,
            "productivity_target": productivity_target,
            "pieces_fallback": pieces_fallback,
            "source_label": "Venta real disponible desde abril · Operación estimada DEMO",
            "sales_source_label": str(sales.get("source_label") or "Ventas"),
            "sales_cut_date": str(sales.get("cut_date") or ""),
            "company": company,
            "stores": stores,
            "collaborators": collaborator_rows,
            "trend": trend,
            "store_count": len(stores),
        }
        with cache_lock:
            cache[cache_key] = (time.monotonic(), payload)
        return payload

    @m.app.get("/api/operation-demo-v201")
    async def operation_demo_v201(request: Request):
        actor = m.require_user(request)
        if str(actor.get("role") or "") not in ("superadmin","admin","director","consulta"):
            raise HTTPException(403, "Demo disponible para perfiles de consulta/administración")
        return await _build_demo(request)

    css = r'''<style id="v201-operation-demo-css">
.v201-demo-toolbar{display:none;align-items:center;justify-content:flex-end;gap:7px;margin:-2px 0 7px}
body[data-v163-module="operation"] .v201-demo-toolbar{display:flex}
.v201-demo-btn{
  border:1px solid #8cb7e3;border-radius:999px;background:#eef6ff;color:#0e5fa9;
  padding:7px 11px;font-size:8px;font-weight:950;cursor:pointer
}
.v201-demo-btn.active{background:#0e5fa9;color:#fff;border-color:#0e5fa9}
.v201-real-btn{border-color:#d6e0ec;background:#fff;color:#49647f}
.v201-demo-note{
  display:flex;align-items:flex-start;gap:8px;padding:9px 11px;border-radius:11px;
  border:1px solid #9fc6ee;background:#eef7ff;color:#174b85;font-size:8.5px;
  font-weight:750;line-height:1.4;margin:7px 0 10px
}
.v201-demo-note b{white-space:nowrap}
.v201-demo-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:8px 0 10px}
.v201-demo-kpi{background:#fff;border:1px solid #d8e3ef;border-radius:12px;padding:11px;min-width:0}
.v201-demo-kpi small{display:block;color:#667b93;font-size:7px;font-weight:950;text-transform:uppercase}
.v201-demo-kpi b{display:block;color:#123f73;font-size:22px;line-height:1.05;margin-top:5px}
.v201-demo-kpi span{display:block;color:#7a899c;font-size:7.5px;margin-top:5px}
.v201-demo-card{background:#fff;border:1px solid #d8e3ef;border-radius:13px;padding:12px;margin:8px 0}
.v201-demo-card h3{margin:0;color:#123f73;font-size:14px}.v201-demo-card .sub{color:#73849a;font-size:8px;margin-top:3px}
.v201-demo-split{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.v201-demo-bars{display:grid;gap:7px;margin-top:10px}
.v201-demo-bar{display:grid;grid-template-columns:96px 1fr 70px;align-items:center;gap:7px;font-size:8px}
.v201-demo-bar b{color:#123f73}.v201-demo-track{height:10px;background:#e8eef5;border-radius:8px;overflow:hidden}
.v201-demo-fill{height:100%;background:#176fe8;border-radius:8px}
.v201-demo-val{text-align:right;color:#315b84;font-weight:900}
.v201-demo-tablewrap{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #d8e3ef;border-radius:11px;margin-top:9px}
.v201-demo-table{width:100%;min-width:1050px;border-collapse:collapse;font-size:8px;background:#fff}
.v201-demo-table th{position:sticky;top:0;background:#0f4a83;color:#fff;padding:8px 7px;text-align:left;white-space:nowrap}
.v201-demo-table td{padding:7px;border-bottom:1px solid #e7edf4;color:#274d74;white-space:nowrap}
.v201-demo-table tr:nth-child(even) td{background:#fafcff}
.v201-demo-table .num{text-align:right}.v201-demo-table .store{font-weight:900;color:#123f73}
.v201-demo-pill{display:inline-flex;padding:3px 6px;border-radius:999px;background:#eaf5ff;color:#1464ad;font-size:7px;font-weight:950}
.v201-demo-good{color:#079447!important;font-weight:950}.v201-demo-warn{color:#d97706!important;font-weight:950}
.v201-demo-demo{color:#d92d20!important;font-weight:950}
.v201-demo-months{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;margin-top:10px}
.v201-demo-month{border:1px solid #dae5f0;border-radius:10px;padding:9px;background:#fbfdff}
.v201-demo-month small{display:block;color:#6b7d92;font-size:7px}.v201-demo-month b{display:block;color:#123f73;font-size:14px;margin-top:4px}
.v201-demo-month span{font-size:7px;color:#72849a}
body.v201-demo-mode #v161FilterBar{display:none!important}
body.v201-demo-mode.v201-demo-filtered #operativoPeriodBar{display:block!important}
body.v201-demo-mode:not(.v201-demo-filtered) #operativoPeriodBar{display:none!important}
@media(max-width:900px){
 .v201-demo-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .v201-demo-split{grid-template-columns:1fr}
 .v201-demo-kpi b{font-size:20px}
 .v201-demo-months{grid-template-columns:repeat(3,minmax(0,1fr))}
 .v201-demo-table{min-width:980px}
 .v201-demo-bar{grid-template-columns:84px 1fr 60px}
}
</style>'''

    js = r'''<script id="v201-operation-demo-js">
(function(){
  if(window.__V201_OPERATION_SALES_DEMO)return;
  window.__V201_OPERATION_SALES_DEMO=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=v=>{const x=Number(v||0);return Number.isFinite(x)?x:0};
  const nf=v=>Math.round(n(v)).toLocaleString('es-MX');
  const money=v=>'$'+Math.round(n(v)).toLocaleString('es-MX');
  const pct=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%';
  const p=v=>pct(v);
  let demoMode=false,demoData=null,demoLoading=false,demoTab='summary';

  function isOperation(){
    return String(document.body.dataset.v163Module||'').toLowerCase()==='operation';
  }
  function canDemo(){
    try{
      const role=String(USER?.real_role||USER?.role||'').toLowerCase();
      return ['superadmin','admin','director','consulta'].includes(role)||USER?.can_preview_roles===true;
    }catch(_){return false}
  }
  async function A(url){
    if(typeof api==='function')return api(url,{timeoutMs:120000});
    const r=await fetch(url,{credentials:'same-origin'});
    const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch(_){}
    if(!r.ok)throw Error(d.detail||('HTTP '+r.status));return d;
  }
  function tone(v){return n(v)>=100?'v201-demo-good':n(v)>=95?'':'v201-demo-warn'}

  function ensureToolbar(){
    if(!canDemo())return;
    let bar=q('#v201DemoToolbar');
    if(!bar){
      bar=document.createElement('div');bar.id='v201DemoToolbar';bar.className='v201-demo-toolbar';
      bar.innerHTML='<button id="v201DemoOn" class="v201-demo-btn">DEMO con ventas</button><button id="v201DemoOff" class="v201-demo-btn v201-real-btn">Volver a real</button>';
      const tabs=q('#v200OperationTabs');
      tabs?.parentNode?.insertBefore(bar,tabs);
      q('#v201DemoOn')?.addEventListener('click',()=>openDemo('summary'));
      q('#v201DemoOff')?.addEventListener('click',closeDemo);
    }
    bar.style.display=isOperation()?'flex':'none';
  }

  function syncTab(){
    qa('#v200OperationTabs [data-v200-op]').forEach(btn=>{
      const on=btn.dataset.v200Op===demoTab;
      btn.classList.toggle('active',on);
      btn.setAttribute('aria-selected',on?'true':'false');
    });
    q('#v201DemoOn')?.classList.toggle('active',demoMode);
  }

  async function loadDemo(){
    if(demoData)return demoData;
    if(demoLoading)return null;
    demoLoading=true;
    try{demoData=await A('/api/operation-demo-v201');return demoData}
    finally{demoLoading=false}
  }

  function note(d){
    const fallback=d.pieces_fallback?' · Piezas estimadas desde venta $ por falta de piezas en la fuente':'';
    return '<div class="v201-demo-note"><b>DEMO</b><span>La venta es la referencia real disponible. Llegada, procesadas, liberadas, eficiencia y productividad son estimaciones para visualizar el reporte lleno; no se guardan como operación real.'+esc(fallback)+'</span></div>';
  }

  function kpis(d){
    const s=d.company;
    const needed=Math.max(0,Math.ceil(n(s.arrival)/Math.max(n(d.productivity_target)*Math.max(1,n(d.workdays)),1)));
    const rows=[
      ['Productividad registrada',nf(s.processed),'Piezas procesadas','#7338ef'],
      ['Mercancía liberada',nf(s.released),'Origen','#ec007c'],
      ['Pendiente',nf(s.pending),'Piezas por procesar','#ef3434'],
      ['Eficiencia',pct(s.efficiency),'Procesadas / carga','#10b981'],
      ['Prod. promedio',nf(s.productivity),'Pzas / colaborador / día','#f3a300'],
      ['Cumplimiento',pct(s.compliance),'Vs estándar','#10b981'],
      ['Colaboradores',nf(s.collaborators),'Con productividad','#173f78'],
      ['Colaboradores necesarios',nf(needed),'Estimación DEMO','#0f7f73'],
    ];
    return '<div class="v149-kpis">'+rows.map(x=>'<div class="v149-kpi" style="--k:'+x[3]+'"><small>'+x[0]+'</small><b>'+x[1]+'</b><span>'+x[2]+'</span></div>').join('')+'</div>';
  }

  function demoAlerts(d){
    return '<div class="v149-panel"><h3>Alertas operativas</h3>'+
      '<div class="v149-alert good">DEMO activo: los valores usan la venta real disponible como base y no se guardan como operación real.</div>'+
    '</div>';
  }

  function demoStoreTable(d){
    const rows=(d.stores||[]).map(r=>{
      const target=n(r.collaborators)*n(d.productivity_target)*Math.max(1,n(d.workdays));
      const compliance=target?n(r.processed)/target*100:0;
      const cls=compliance>=100?'metric-good':compliance>=75?'metric-warn':'metric-bad';
      return '<tr><td><b>'+esc(r.store)+'</b></td><td>'+nf(r.arrival)+'</td><td>'+nf(r.processed)+'</td><td>'+nf(r.released)+'</td><td>'+nf(target)+'</td><td><b class="'+cls+'">'+pct(compliance)+'</b></td></tr>';
    }).join('');
    return '<div class="v149-panel"><h3>Desempeño por tienda</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Llegada</th><th>Procesadas</th><th>Liberadas</th><th>Meta</th><th>Cumplimiento</th></tr></thead><tbody>'+
      (rows||'<tr><td colspan="6">Sin información para el periodo.</td></tr>')+
      '</tbody></table></div></div>';
  }

  function demoTop(d){
    const rows=[...(d.collaborators||[])].sort((a,b)=>n(b.daily_productivity)-n(a.daily_productivity)).slice(0,5);
    const body=rows.map((r,i)=>{
      const compliance=n(r.compliance);
      const cls=compliance>=100?'metric-good':compliance>=75?'metric-warn':'metric-bad';
      return '<tr><td>#'+(i+1)+'</td><td><b>'+esc(r.name)+'</b></td><td>'+esc(r.store)+'</td><td>'+nf(r.pieces)+'</td><td>'+nf(r.daily_productivity)+'</td><td><b class="'+cls+'">'+pct(compliance)+'</b></td></tr>';
    }).join('');
    return '<div class="v149-panel"><h3>Top 5 colaboradores</h3><div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Colaborador</th><th>Tienda</th><th>Piezas</th><th>Prod. diaria</th><th>Cumplimiento</th></tr></thead><tbody>'+
      (body||'<tr><td colspan="6">Sin productividad registrada.</td></tr>')+
      '</tbody></table></div></div>';
  }

  function allStoresTable(d,kind){
    const head=kind==='daily'
      ?'<th>#</th><th>Tienda</th><th class="num">Llegada día</th><th class="num">Procesadas día</th><th class="num">Liberadas día</th><th class="num">Pendiente día</th><th class="num">Eficiencia</th>'
      :'<th>#</th><th>Tienda</th><th class="num">Venta pzas base</th><th class="num">Llegada</th><th class="num">Procesadas</th><th class="num">Liberadas</th><th class="num">Pendiente</th><th class="num">Eficiencia</th><th class="num">Prod. diaria</th><th class="num">% Meta</th><th class="num">Colab.</th>';
    const body=d.stores.map(r=>{
      if(kind==='daily'){
        return '<tr><td>'+r.rank+'</td><td class="store">'+esc(r.store)+'</td><td class="num">'+nf(r.arrival/d.workdays)+'</td><td class="num">'+nf(r.processed/d.workdays)+'</td><td class="num">'+nf(r.released/d.workdays)+'</td><td class="num">'+nf(r.pending/d.workdays)+'</td><td class="num '+tone(r.efficiency)+'">'+pct(r.efficiency)+'</td></tr>';
      }
      return '<tr><td>'+r.rank+'</td><td class="store">'+esc(r.store)+'</td><td class="num">'+nf(r.sales_pieces)+'</td><td class="num">'+nf(r.arrival)+'</td><td class="num">'+nf(r.processed)+'</td><td class="num">'+nf(r.released)+'</td><td class="num">'+nf(r.pending)+'</td><td class="num '+tone(r.efficiency)+'">'+pct(r.efficiency)+'</td><td class="num">'+nf(r.productivity)+'</td><td class="num '+tone(r.compliance)+'">'+pct(r.compliance)+'</td><td class="num">'+nf(r.collaborators)+'</td></tr>';
    }).join('');
    return '<div class="v201-demo-tablewrap"><table class="v201-demo-table"><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>';
  }

  function areaBars(d){
    const total=Object.values(d.company.areas||{}).reduce((a,b)=>a+n(b),0)||1;
    return '<div class="v201-demo-bars">'+Object.entries(d.company.areas||{}).map(([name,val])=>'<div class="v201-demo-bar"><b>'+esc(name)+'</b><div class="v201-demo-track"><div class="v201-demo-fill" style="width:'+Math.min(100,n(val)/total*100)+'%"></div></div><span class="v201-demo-val">'+pct(n(val)/total*100)+'</span></div>').join('')+'</div>';
  }
  function activityBars(d){
    const total=Object.values(d.company.activities||{}).reduce((a,b)=>a+n(b),0)||1;
    return '<div class="v201-demo-bars">'+Object.entries(d.company.activities||{}).map(([name,val])=>'<div class="v201-demo-bar"><b>'+esc(name)+'</b><div class="v201-demo-track"><div class="v201-demo-fill" style="width:'+Math.min(100,n(val)/total*100)+'%"></div></div><span class="v201-demo-val">'+pct(n(val)/total*100)+'</span></div>').join('')+'</div>';
  }

  /* V279 · El Resumen DEMO replica exactamente la Opción 1 del reporte real.
     Los valores siguen siendo DEMO/estimados y nunca se guardan. */
  function v279Status(score){
    if(score>=95)return ['Excelente','excellent'];
    if(score>=80)return ['En objetivo','target'];
    if(score>=70)return ['Atención','attention'];
    return ['Crítico','critical'];
  }
  function v279DemoRows(d){
    return (d.stores||[]).map((r,i)=>{
      const target=n(r.collaborators)*n(d.productivity_target)*Math.max(1,n(d.workdays));
      const productivity=target?n(r.processed)/target*100:n(r.compliance);
      const flow=n(r.arrival)?n(r.released)/n(r.arrival)*100:0;
      const pendingScore=n(r.arrival)?Math.max(0,Math.min(100,(1-n(r.pending)/n(r.arrival))*100)):100;
      const advance=Math.max(68,Math.min(112,n(r.efficiency)+((i%5)-2)*2.2));
      const offsets=[4,-3,1,-1];
      const areaPct={};
      ['Colgado','Doblado','Jeans','Lencería'].forEach((a,j)=>{
        areaPct[a]=Math.max(60,Math.min(112,productivity+offsets[(j+i)%offsets.length]));
      });
      const coverage=Object.values(areaPct).reduce((a,b)=>a+Math.min(100,n(b)),0)/4;
      let score=Math.min(100,productivity)*.35+Math.min(100,flow)*.30+pendingScore*.20+Math.min(100,advance)*.10+coverage*.05;
      if(pendingScore<70)score=Math.min(score,94);
      const st=v279Status(score);
      const clas=n(r.arrival)*.72;
      const pizca=n(r.arrival)*.28;
      const originUb=n(r.released)*.70;
      const resUb=n(r.released)*.30;
      return {
        ...r,rank:i+1,score,status:st[0],status_key:st[1],
        productivity_pct:productivity,flow_pct:flow,pending_score:pendingScore,
        advance_pct:advance,coverage_pct:coverage,area_pct:areaPct,
        origin:{Clasificado:clas,Acondicionado:Math.max(originUb,clas*.91),Ubicado:originUb},
        resupply:{Pizca:pizca,Acondicionado:Math.max(resUb,pizca*.92),Ubicado:resUb}
      };
    }).sort((a,b)=>n(b.score)-n(a.score)||n(b.productivity_pct)-n(a.productivity_pct)||String(a.store).localeCompare(String(b.store),'es'))
      .map((r,i)=>({...r,rank:i+1}));
  }
  function v279Flow(x,names){
    const a=n(x[names[0]]),b=n(x[names[1]]),c=n(x[names[2]]);
    return '<div class="v278-steps"><div class="v278-step">'+names[0]+'</div><div class="v278-step">'+names[1]+'</div><div class="v278-step">'+names[2]+'</div></div>'+
      '<div class="v278-nums"><div><b>'+nf(a)+'</b><span>inicio</span></div><div><b>'+nf(b)+'</b><span>'+(a?p(b/a*100):'0')+'%</span></div><div><b>'+nf(c)+'</b><span>'+(a?p(c/a*100):'0')+'%</span></div></div>';
  }
  function v279Areas(rows,d){
    return ['Colgado','Doblado','Jeans','Lencería'].map(a=>{
      const pieces=rows.reduce((s,r)=>s+n(r.areas?.[a]),0);
      const cp=rows.length?rows.reduce((s,r)=>s+n(r.area_pct?.[a]),0)/rows.length:0;
      const target=cp?pieces/(cp/100):0;
      return {area:a,pieces,target,compliance_pct:cp};
    });
  }
  function v279Kpis(s){
    const tag=s.status||'Sin datos';
    return '<div class="v278-kpis">'+
      '<div class="v278-kpi g"><div class="v278-l">Score Operativo</div><div class="v278-ring" style="--p:'+Math.min(100,Math.max(0,n(s.score)))+'"><b>'+p(s.score)+'</b></div><span class="v278-tag">'+esc(tag)+'</span></div>'+
      '<div class="v278-kpi b"><div class="v278-l">Productividad</div><div class="v278-v">'+p(s.productivity_pct)+'%</div><div class="v278-s">'+nf(s.productivity_pieces)+' / '+nf(s.productivity_target)+'</div><div class="v278-bar"><i style="width:'+Math.min(100,n(s.productivity_pct))+'%"></i></div></div>'+
      '<div class="v278-kpi p"><div class="v278-l">Cierre de flujo</div><div class="v278-v">'+p(s.flow_pct)+'%</div><div class="v278-s">Ubicado ÷ inicio</div><div class="v278-bar"><i style="width:'+Math.min(100,n(s.flow_pct))+'%;background:#8056e8"></i></div></div>'+
      '<div class="v278-kpi o"><div class="v278-l">Pendiente actual</div><div class="v278-v" style="color:#ef7b08">'+nf(s.pending)+'</div><div class="v278-s">Control '+p(s.pending_score)+'%</div></div>'+
      '<div class="v278-kpi r"><div class="v278-l">Avance vs esperado</div><div class="v278-v" style="color:#e71954">'+p(s.advance_pct)+'%</div><div class="v278-s">Ritmo del periodo</div></div>'+
      '<div class="v278-kpi b"><div class="v278-l">Pzas ubicadas</div><div class="v278-v">'+nf(s.located_pieces)+'</div><div class="v278-s">Origen + Resurtido</div></div>'+
    '</div>';
  }
  function v279Ranking(rows){
    return '<div class="v278-rank"><div class="v278-rr h"><div>#</div><div>Tienda</div><div>Score Operativo</div><div></div></div>'+
      rows.map(r=>'<div class="v278-rr"><b>'+r.rank+'</b><b title="'+esc(r.store)+'">'+esc(r.store)+'</b><div class="v278-rb"><i style="width:'+Math.min(100,n(r.score))+'%"></i></div><div class="v278-rs">'+p(r.score)+'</div></div>').join('')+
      '</div>';
  }
  function v279States(rows){
    const counts={'Excelente':0,'En objetivo':0,'Atención':0,'Crítico':0};
    rows.forEach(r=>counts[r.status]=(counts[r.status]||0)+1);
    return '<table class="v278-status">'+[['Excelente','excellent'],['En objetivo','target'],['Atención','attention'],['Crítico','critical']].map(x=>{
      const v=n(counts[x[0]]);return '<tr><td><span class="v278-dot '+x[1]+'"></span><b>'+x[0]+'</b></td><td>'+v+'</td><td>'+(rows.length?p(v/rows.length*100):'0')+'%</td></tr>';
    }).join('')+'</table>';
  }
  function v279Detail(rows){
    return '<div class="v278-tw"><table class="v278-table"><thead><tr><th>#</th><th>Tienda</th><th>Score</th><th>Productividad<span class="v278-w">35%</span></th><th>Cierre de flujo<span class="v278-w">30%</span></th><th>Pendientes<span class="v278-w">20%</span></th><th>Avance<span class="v278-w">10%</span></th><th>Cobertura áreas<span class="v278-w">5%</span></th><th>Estado</th></tr></thead><tbody>'+
      rows.map(r=>'<tr><td>'+r.rank+'</td><td><b>'+esc(r.store)+'</b></td><td><span class="v278-chip">'+p(r.score)+'</span></td><td>'+p(r.productivity_pct)+'%</td><td>'+p(r.flow_pct)+'%</td><td>'+nf(r.pending)+' pzs</td><td>'+p(r.advance_pct)+'%</td><td>'+p(r.coverage_pct)+'%</td><td><span class="v278-state '+r.status_key+'">'+esc(r.status)+'</span></td></tr>').join('')+
      '</tbody></table></div>';
  }
  function summary(d){
    const ranking=v279DemoRows(d);
    const selected=String(q('#operStoreSelect')?.value||'Compañía');
    const view=selected==='Compañía'?ranking:ranking.filter(r=>String(r.store)===selected);
    const active=view.length?view:ranking;
    const areas=v279Areas(active,d);
    const productivityPieces=active.reduce((s,r)=>s+n(r.processed),0);
    const productivityTarget=active.reduce((s,r)=>s+n(r.collaborators)*n(d.productivity_target)*Math.max(1,n(d.workdays)),0);
    const productivityPct=productivityTarget?productivityPieces/productivityTarget*100:0;
    const arrival=active.reduce((s,r)=>s+n(r.arrival),0);
    const located=active.reduce((s,r)=>s+n(r.released),0);
    const flowPct=arrival?located/arrival*100:0;
    const pending=active.reduce((s,r)=>s+n(r.pending),0);
    const pendingScore=arrival?Math.max(0,Math.min(100,(1-pending/arrival)*100)):100;
    const advance=active.length?active.reduce((s,r)=>s+n(r.advance_pct),0)/active.length:0;
    const coverage=areas.length?areas.reduce((s,r)=>s+Math.min(100,n(r.compliance_pct)),0)/areas.length:0;
    let score=Math.min(100,productivityPct)*.35+Math.min(100,flowPct)*.30+pendingScore*.20+Math.min(100,advance)*.10+coverage*.05;
    if(pendingScore<70)score=Math.min(score,94);
    const st=v279Status(score);
    const s={score,status:st[0],productivity_pct:productivityPct,productivity_pieces:productivityPieces,productivity_target:productivityTarget,flow_pct:flowPct,pending,pending_score:pendingScore,advance_pct:advance,coverage_pct:coverage,located_pieces:located};
    const origin={Clasificado:active.reduce((x,r)=>x+n(r.origin.Clasificado),0),Acondicionado:active.reduce((x,r)=>x+n(r.origin.Acondicionado),0),Ubicado:active.reduce((x,r)=>x+n(r.origin.Ubicado),0)};
    const resupply={Pizca:active.reduce((x,r)=>x+n(r.resupply.Pizca),0),Acondicionado:active.reduce((x,r)=>x+n(r.resupply.Acondicionado),0),Ubicado:active.reduce((x,r)=>x+n(r.resupply.Ubicado),0)};
    const areaHtml=areas.map(x=>'<div class="v278-ar"><b>'+esc(x.area)+'</b><div class="v278-pr"><i style="width:'+Math.min(100,n(x.compliance_pct))+'%"></i></div><div class="v278-ap">'+p(x.compliance_pct)+'%</div><div class="v278-an">'+nf(x.pieces)+' / '+nf(x.target)+'</div></div>').join('');
    return '<span class="v201-demo-marker" hidden></span><div class="v278">'+
      '<div class="v278-head"><div><h2>Reporte de Operación <span style="font-size:9px;padding:4px 7px;border-radius:999px;background:#ffffff24;vertical-align:middle">DEMO</span></h2><p>Tienda: '+esc(selected)+' &nbsp;|&nbsp; '+esc(d.period_label||'')+' · datos simulados para visualización</p></div><div class="v278-date">'+esc(d.period_label||'DEMO')+'</div></div>'+
      v279Kpis(s)+
      '<div class="v278-grid"><div class="v278-panel"><h3>▦ Flujo de Operación</h3><div class="v278-flows"><div class="v278-flow"><div class="v278-ft">Origen</div>'+v279Flow(origin,['Clasificado','Acondicionado','Ubicado'])+'</div><div class="v278-flow"><div class="v278-ft">Resurtido</div>'+v279Flow(resupply,['Pizca','Acondicionado','Ubicado'])+'</div></div></div><div class="v278-panel"><h3>▥ Productividad por área <small>Meta 100%</small></h3>'+areaHtml+'</div></div>'+
      '<div class="v278-grid"><div class="v278-panel"><h3>🏆 Ranking por tienda — Score Operativo <small>'+ranking.length+' tiendas</small></h3>'+v279Ranking(ranking)+'</div><div class="v278-panel"><h3>▥ Estado de indicadores</h3>'+v279States(ranking)+'</div></div>'+
      '<div class="v278-panel"><h3>▦ Detalle de evaluación por tienda <small>Score: 35% Productividad · 30% Cierre · 20% Pendientes · 10% Avance · 5% Cobertura</small></h3>'+v279Detail(ranking)+'</div>'+
      '<div class="v201-demo-note"><b>DEMO</b><span>Estos valores sirven únicamente para visualizar la Opción 1 llena. No se guardan ni sustituyen la operación real.</span></div>'+
      '</div>';
  }

  function daily(d){
    return note(d)+
      '<div class="v201-demo-card"><h3>Captura diaria · vista simulada</h3><div class="sub">Promedio diario equivalente del periodo '+esc(d.period_label)+' · '+d.workdays+' días hábiles</div>'+
      '<div class="v201-demo-grid">'+
      '<div class="v201-demo-kpi"><small>Llegada día</small><b>'+nf(d.company.arrival/d.workdays)+'</b><span>Compañía</span></div>'+
      '<div class="v201-demo-kpi"><small>Procesadas día</small><b>'+nf(d.company.processed/d.workdays)+'</b><span>Compañía</span></div>'+
      '<div class="v201-demo-kpi"><small>Liberadas día</small><b>'+nf(d.company.released/d.workdays)+'</b><span>Compañía</span></div>'+
      '<div class="v201-demo-kpi"><small>Eficiencia</small><b>'+pct(d.company.efficiency)+'</b><span>DEMO</span></div></div>'+
      allStoresTable(d,'daily')+'</div>';
  }

  function capture(d){
    const acts=['Acondicionado','Clasificado','Ubicado'],areas=['Doblado','Colgado','Jeans','Lencería'];
    const rows=d.stores.map((r,i)=>{
      const act=acts[i%acts.length],area=areas[i%areas.length];
      const pieces=Math.round((r.processed/d.workdays)/(1+(i%4)*.18));
      const mins=38+(i*7)%54;
      return '<tr><td class="store">'+esc(r.store)+'</td><td>'+act+'</td><td>'+area+'</td><td class="num">'+nf(pieces)+'</td><td class="num">00:'+(mins<10?'0':'')+mins+':00</td><td><span class="v201-demo-pill">Finalizado</span></td></tr>';
    }).join('');
    return note(d)+'<div class="v201-demo-card"><h3>Cargar productividad · ejemplo lleno</h3><div class="sub">Una captura representativa por cada tienda. Sólo visual; no escribe datos.</div><div class="v201-demo-tablewrap"><table class="v201-demo-table"><thead><tr><th>Tienda</th><th>Actividad</th><th>Área</th><th class="num">Piezas</th><th class="num">Tiempo</th><th>Estado</th></tr></thead><tbody>'+rows+'</tbody></table></div></div>';
  }

  function demoFilterState(){
    return {
      period:String(q('#operPeriodSelect')?.value||'').trim(),
      store:String(q('#operStoreSelect')?.value||'Compañía').trim()||'Compañía',
      area:String(q('#operAreaSelect')?.value||'Todas').trim()||'Todas',
      activity:String(q('#operActivitySelect')?.value||'Todas').trim()||'Todas'
    };
  }
  function demoPeriodDays(d,period){
    const v=String(period||'');
    if(/^\d{4}-\d{2}-\d{2}$/.test(v))return 1;
    if(/^\d{4}-W\d{2}$/.test(v))return 5;
    if(/^\d{4}-\d{2}$/.test(v))return 22;
    if(/^\d{4}$/.test(v))return Math.max(1,n(d.workdays));
    return Math.max(1,n(d.workdays));
  }
  function productivity(d){
    const f=demoFilterState();
    const userRole=(()=>{try{return String(USER?.role||'').toLowerCase()}catch(_){return ''}})();
    const restricted=['tienda','colaborador','colaborador_operativo','colaborador_lenceria'].includes(userRole);
    const assigned=(()=>{try{return String(USER?.store||'')}catch(_){return ''}})();
    if(restricted&&assigned)f.store=assigned;
    const days=demoPeriodDays(d,f.period);
    let people=[...(d.collaborators||[])];
    if(f.store&&f.store!=='Compañía')people=people.filter(r=>String(r.store||'')===f.store);
    if(f.area&&f.area!=='Todas')people=people.filter(r=>String(r.area||'')===f.area);
    if(f.activity&&f.activity!=='Todas')people=people.filter(r=>String(r.activity||'')===f.activity);

    // Store ranking is calculated from the filtered collaborator set so Area
    // and Activity affect both ranking levels in the same way.
    const storeMap=new Map();
    people.forEach(r=>{
      const st=String(r.store||'');
      const g=storeMap.get(st)||{store:st,pieces:0,collaborators:new Set(),days:0};
      const key=String(r.employee_no||r.name||'');
      g.collaborators.add(key);
      g.pieces+=n(r.daily_productivity)*days;
      g.days+=Math.max(1,days);
      storeMap.set(st,g);
    });
    let storeRows=[...storeMap.values()].map(g=>{
      const daily=g.days?g.pieces/g.days:0;
      return {store:g.store,pieces:g.pieces,collaborators:g.collaborators.size,daily,compliance:d.productivity_target?daily/d.productivity_target*100:0};
    });
    if(!restricted&&f.store==='Compañía'){
      (d.stores||[]).forEach(s=>{
        if(!storeMap.has(String(s.store||'')))storeRows.push({store:String(s.store||''),pieces:0,collaborators:0,daily:0,compliance:0});
      });
    }
    storeRows.sort((a,b)=>n(b.daily)-n(a.daily)||n(b.pieces)-n(a.pieces)||String(a.store).localeCompare(String(b.store),'es'));
    const storeRank=new Map();
    storeRows.forEach((r,i)=>{r.rank=i+1;storeRank.set(r.store,i+1)});

    const grouped=[];
    storeRows.forEach(sr=>{
      const local=people.filter(r=>String(r.store||'')===sr.store)
        .sort((a,b)=>n(b.daily_productivity)-n(a.daily_productivity)||String(a.name||'').localeCompare(String(b.name||''),'es'));
      local.forEach((r,i)=>grouped.push({...r,store_rank:sr.rank,local_rank:i+1}));
    });

    const kpiPieces=grouped.reduce((a,r)=>a+n(r.daily_productivity)*days,0);
    const avg=grouped.length?grouped.reduce((a,r)=>a+n(r.daily_productivity),0)/grouped.length:0;
    const avgPct=grouped.length?grouped.reduce((a,r)=>a+n(r.compliance),0)/grouped.length:0;

    const storeTable='<div class="v201-demo-tablewrap"><table class="v201-demo-table"><thead><tr><th>#</th><th>Tienda</th><th class="num">Piezas</th><th class="num">Colaboradores</th><th class="num">Pzas/día</th><th class="num">% Meta</th></tr></thead><tbody>'+
      storeRows.map(r=>'<tr><td><b>#'+r.rank+'</b></td><td class="store">'+esc(r.store)+'</td><td class="num">'+nf(r.pieces)+'</td><td class="num">'+nf(r.collaborators)+'</td><td class="num"><b>'+nf(r.daily)+'</b></td><td class="num '+tone(r.compliance)+'">'+pct(r.compliance)+'</td></tr>').join('')+
      (!storeRows.length?'<tr><td colspan="6">Sin tiendas con productividad para los filtros seleccionados.</td></tr>':'')+
      '</tbody></table></div>';

    let last='';
    const collaboratorBody=grouped.map(r=>{
      let header='';
      if(!restricted&&String(r.store||'')!==last){
        last=String(r.store||'');
        header='<tr><td colspan="9" style="background:#edf6ff;color:#0e4c83;font-weight:950">#'+r.store_rank+' · '+esc(r.store)+'</td></tr>';
      }
      const periodPieces=n(r.daily_productivity)*days;
      return header+'<tr><td><b>#'+r.local_rank+'</b></td><td class="store">'+esc(r.name)+(r.synthetic?' <span class="v201-demo-pill">DEMO</span>':'')+'</td><td>'+esc(r.employee_no||'—')+'</td><td>'+esc(r.store)+'</td><td>'+esc(r.area)+'</td><td>'+esc(r.activity)+'</td><td class="num"><b>'+nf(periodPieces)+'</b></td><td class="num">'+nf(r.daily_productivity)+'</td><td class="num '+tone(r.compliance)+'">'+pct(r.compliance)+'</td></tr>';
    }).join('');
    const collaboratorTable='<div class="v201-demo-tablewrap"><table class="v201-demo-table"><thead><tr><th>Ranking</th><th>Colaborador</th><th>Nómina</th><th>Tienda</th><th>Área</th><th>Actividad</th><th class="num">Piezas periodo</th><th class="num">Pzas/día</th><th class="num">% Meta</th></tr></thead><tbody>'+
      (collaboratorBody||'<tr><td colspan="9">Sin colaboradores para los filtros seleccionados.</td></tr>')+
      '</tbody></table></div>';

    const scope=restricted?('Sólo '+(assigned||f.store)):(f.store==='Compañía'?'Todas las tiendas':f.store);
    let html=note(d)+
      '<div class="v201-demo-grid">'+
        '<div class="v201-demo-kpi"><small>Piezas</small><b>'+nf(kpiPieces)+'</b><span>'+esc(scope)+'</span></div>'+
        '<div class="v201-demo-kpi"><small>Colaboradores</small><b>'+nf(grouped.length)+'</b><span>Con productividad</span></div>'+
        '<div class="v201-demo-kpi"><small>Prod. diaria prom.</small><b>'+nf(avg)+'</b><span>Pzas/día</span></div>'+
        '<div class="v201-demo-kpi"><small>Cumplimiento prom.</small><b>'+pct(avgPct)+'</b><span>Vs meta '+nf(d.productivity_target)+'</span></div>'+
      '</div>';
    if(!restricted){
      html+='<div class="v201-demo-card"><h3>Ranking de tiendas</h3><div class="sub">Primero se ordenan las tiendas por productividad promedio diaria.</div>'+storeTable+'</div>';
    }
    html+='<div class="v201-demo-card"><h3>'+(restricted?'Ranking de colaboradores · '+esc(assigned||f.store):'Detalle de colaboradores por ranking de tienda')+'</h3>'+
      '<div class="sub">'+(restricted?'Este perfil sólo puede consultar colaboradores de su tienda.':'La tienda aparece por posición y debajo se ordenan sus colaboradores.')+'</div>'+
      collaboratorTable+'</div>';
    return html;
  }
  function standards(d){
    const areas=[['Colgado',Math.round(d.productivity_target*1.08)],['Doblado',Math.round(d.productivity_target*.96)],['Jeans',Math.round(d.productivity_target*.90)],['Lencería',Math.round(d.productivity_target*.84)]];
    const acts=[['Acondicionado',Math.round(d.productivity_target)],['Clasificado',Math.round(d.productivity_target*.92)],['Ubicado',Math.round(d.productivity_target*1.04)]];
    return note(d)+'<div class="v201-demo-split"><div class="v201-demo-card"><h3>Estándares por área · DEMO</h3><div class="sub">Referencia visual, no modifica metas reales.</div><div class="v201-demo-bars">'+areas.map(x=>'<div class="v201-demo-bar"><b>'+x[0]+'</b><div class="v201-demo-track"><div class="v201-demo-fill" style="width:'+Math.min(100,x[1]/(d.productivity_target*1.15)*100)+'%"></div></div><span class="v201-demo-val">'+nf(x[1])+'</span></div>').join('')+'</div></div><div class="v201-demo-card"><h3>Estándares por actividad · DEMO</h3><div class="sub">Meta general actual: '+nf(d.productivity_target)+'</div><div class="v201-demo-bars">'+acts.map(x=>'<div class="v201-demo-bar"><b>'+x[0]+'</b><div class="v201-demo-track"><div class="v201-demo-fill" style="width:'+Math.min(100,x[1]/(d.productivity_target*1.15)*100)+'%"></div></div><span class="v201-demo-val">'+nf(x[1])+'</span></div>').join('')+'</div></div></div>';
  }

  function trend(d){
    return '<div class="v201-demo-card"><h3>Base de venta desde abril</h3><div class="sub">Piezas reales usadas para dimensionar el DEMO</div><div class="v201-demo-months">'+(d.trend||[]).map(r=>'<div class="v201-demo-month"><small>'+esc(r.label)+'</small><b>'+nf(r.sales_pieces)+'</b><span>venta pzas · eficiencia demo '+pct(r.efficiency)+'</span></div>').join('')+'</div></div>';
  }

  function renderDemo(){
    if(!demoMode||!demoData)return;
    syncTab();
    document.body.classList.add('v201-demo-mode');
    const centro=q('#operativoCentro'),dyn=q('#operativoDynamic');centro?.classList.add('hidden');dyn?.classList.remove('hidden');
    if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent='Operación · DEMO';
    if(q('#operativoDynamicSub'))q('#operativoDynamicSub').textContent='Datos de venta reales como base · operación estimada para visualización';
    const host=q('#operativoDynamicContent');if(!host)return;
    const views={summary,daily,capture,productivity,standards};
    const needsFilter=['summary','productivity'].includes(demoTab);
    document.body.classList.toggle('v201-demo-filtered',needsFilter);
    const nativeBar=q('#operativoPeriodBar');
    if(nativeBar){
      nativeBar.classList.toggle('hidden',!needsFilter);
      nativeBar.style.display=needsFilter?'block':'none';
    }
    host.dataset.v201DemoView=demoTab;
    host.innerHTML=(views[demoTab]||summary)(demoData);

    /* El DEMO usa exactamente la misma estructura visual que la vista real.
       Sólo cambian los valores y la marca DEMO, nunca el layout. */
    const modeMap={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
    let mode='day';
    try{mode=String(OPER_PERIOD?.type||q('#operPeriodMode')?.value||'day')}catch(_){}
    if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent='Operación · '+(modeMap[mode]||'Día')+' · DEMO';
    if(q('#operativoDynamicSub'))q('#operativoDynamicSub').textContent='Resumen ejecutivo de operación y productividad · DEMO con ventas';
  }

  let demoGuardTimer=0;
  function guardDemo(){
    if(!demoMode||!demoData||!isOperation())return;
    clearTimeout(demoGuardTimer);
    demoGuardTimer=setTimeout(()=>{
      if(!demoMode||!demoData||!isOperation())return;
      const host=q('#operativoDynamicContent');
      if(!host)return;
      const marker=host.querySelector('.v201-demo-marker,.v201-demo-note');
      if(!marker||host.dataset.v201DemoView!==demoTab){
        renderDemo();
        return;
      }
      document.body.classList.add('v201-demo-mode');
      const title=q('#operativoDynamicTitle');
      const sub=q('#operativoDynamicSub');
      const modeMap={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
      let mode='day';try{mode=String(OPER_PERIOD?.type||q('#operPeriodMode')?.value||'day')}catch(_){}
      const wantedTitle='Operación · '+(modeMap[mode]||'Día')+' · DEMO';
      const wantedSub='Resumen ejecutivo de operación y productividad · DEMO con ventas';
      if(title&&title.textContent!==wantedTitle)title.textContent=wantedTitle;
      if(sub&&sub.textContent!==wantedSub)sub.textContent=wantedSub;
      syncTab();
    },25);
  }

  async function openDemo(tab='summary'){
    if(!isOperation()||!canDemo())return;
    demoMode=true;demoTab=tab;
    document.body.classList.add('v201-demo-mode');
    syncTab();
    const host=q('#operativoDynamicContent');
    if(host)host.innerHTML='<div class="infoempty">Preparando DEMO con la venta disponible desde abril…</div>';
    try{
      const d=await loadDemo();
      if(d)renderDemo();
    }catch(e){
      if(host)host.innerHTML='<div class="infoempty">No fue posible preparar el DEMO: '+esc(e.message||e)+'</div>';
    }
  }
  async function closeDemo(){
    demoMode=false;demoData=null;document.body.classList.remove('v201-demo-mode','v201-demo-filtered');
    q('#v201DemoOn')?.classList.remove('active');
    if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent='Operación';
    if(typeof window.renderOperativoView==='function')await window.renderOperativoView('Operación',true);
  }

  document.addEventListener('click',e=>{
    const consult=e.target.closest?.('#operPeriodApply');
    if(consult&&demoMode){
      e.preventDefault();e.stopImmediatePropagation();
      renderDemo();return;
    }
    const tab=e.target.closest?.('#v200OperationTabs [data-v200-op]');
    if(tab&&demoMode){
      e.preventDefault();e.stopImmediatePropagation();
      demoTab=tab.dataset.v200Op||'summary';renderDemo();return;
    }
    const main=e.target.closest?.('[data-main]');
    if(main){
      setTimeout(()=>{
        ensureToolbar();
        if(String(main.dataset.main||'')!=='operation'&&demoMode){
          demoMode=false;document.body.classList.remove('v201-demo-mode','v201-demo-filtered');
        }
      },100);
    }
  },true);

  function bindDemoFilters(){
    ['#operStoreSelect','#operAreaSelect','#operActivitySelect','#operPeriodSelect'].forEach(sel=>{
      const el=q(sel);if(!el||el.dataset.v201Bound==='1')return;
      el.dataset.v201Bound='1';
      el.addEventListener('change',()=>{if(demoMode&&demoTab==='productivity')renderDemo()});
    });
  }
  let demoObserver=null;
  function setupDemoGuard(){
    if(demoObserver)return;
    demoObserver=new MutationObserver(()=>guardDemo());
    demoObserver.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','style','aria-selected']});
    setInterval(()=>{if(demoMode)guardDemo()},250);
  }
  function setup(){ensureToolbar();bindDemoFilters();setupDemoGuard();if(demoMode&&isOperation())guardDemo()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [250,800,1600].forEach(ms=>setTimeout(setup,ms));
  console.info('[V201.2] DEMO de Operación conserva el mismo formato visual de la vista real.');
})();
</script>'''

    @m.app.middleware("http")
    async def v201_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v201-operation-demo-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v201-operation-demo-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache", "Expires": "0",
                "X-Operations-UI-Version": "V201.2-DEMO-NATIVE-LAYOUT",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V201] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V201_OPERATION_SALES_DEMO = True
    print("[V201.2] Demo Operación: formato nativo conservado y datos demo protegidos.", flush=True)
