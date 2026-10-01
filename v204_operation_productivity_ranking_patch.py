"""V204 · Separación definitiva Captura vs Productividad + ranking por rol.

- Cargar productividad: captura real (Actividad, Área, Piezas, Inicio/Fin).
- Productividad: sólo consulta/ranking.
- Tienda: únicamente colaboradores de su tienda.
- Director/Admin/Superadmin/Consulta: ranking de tiendas + detalle de colaboradores.
- El detalle de colaboradores se ordena primero por ranking de tienda y después
  por ranking del colaborador dentro de esa tienda.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")
AREAS = ("Doblado", "Colgado", "Jeans", "Lencería")
ACTIVITIES = ("Acondicionado", "Clasificado", "Ubicado")
PRIVILEGED = ("superadmin", "admin", "director", "consulta")


def install(m):
    if getattr(m, "_V204_OPERATION_PRODUCTIVITY_RANKING", False):
        return

    def _num(value):
        try:
            v = float(value or 0)
            return v if math.isfinite(v) else 0.0
        except Exception:
            return 0.0

    def _norm(value):
        return m.login_key(value) if hasattr(m, "login_key") else str(value or "").strip().casefold()

    def _period_bounds(period_type, period_value):
        ptype = str(period_type or "month").strip().lower()
        value = str(period_value or "").strip()
        today = datetime.now(MX).date()
        if ptype == "day":
            d = datetime.strptime(value[:10], "%Y-%m-%d").date() if value else today
            return d, d
        if ptype == "week":
            if value:
                mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, flags=re.I)
                if not mt:
                    raise HTTPException(400, "Semana ISO inválida")
                start = date.fromisocalendar(int(mt.group(1)), int(mt.group(2)), 1)
            else:
                iso = today.isocalendar()
                start = date.fromisocalendar(iso.year, iso.week, 1)
            return start, start + timedelta(days=6)
        if ptype == "year":
            year = int(value[:4]) if value else today.year
            return date(year, 1, 1), date(year, 12, 31)
        # month
        if value:
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            if not mt:
                raise HTTPException(400, "Mes inválido")
            year, month = int(mt.group(1)), int(mt.group(2))
        else:
            year, month = today.year, today.month
        start = date(year, month, 1)
        end = date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
        return start, end

    def _target():
        result = 784.0
        try:
            goals = m.get_goals() or {}
            for key in ("productividad_diaria", "productivity_daily", "productivity", "productividad"):
                value = _num(goals.get(key))
                if value > 0:
                    result = value
                    break
        except Exception:
            pass
        return result

    def _canonical_store(value, stores):
        key = _norm(value)
        for store in stores:
            if _norm(store) == key:
                return store
        return str(value or "").strip()

    def _effective_store(actor, requested):
        role = str(actor.get("role") or "").strip().lower()
        stores = list(m.store_names(True) or [])
        assigned = _canonical_store(actor.get("store"), stores)
        if role in ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria"):
            if not assigned:
                raise HTTPException(409, "El usuario no tiene tienda asignada")
            return assigned
        req = str(requested or "Compañía").strip()
        if req and req != "Compañía":
            canon = _canonical_store(req, stores)
            if canon:
                return canon
        return "Compañía"

    def _row_key(row, area_key="origin", time_key="created_at"):
        employee = str(row.get("employee_no") or "").strip() or _norm(row.get("employee_name"))
        return (
            str(row.get("date") or ""),
            _norm(row.get("store")),
            _norm(employee),
            _norm(row.get(area_key)),
            _norm(row.get("activity")),
            round(_num(row.get("pieces")), 3),
            str(row.get(time_key) or ""),
        )

    def _read_productivity_rows(start, end, stores):
        if not stores:
            return []
        marks = ",".join("?" for _ in stores)
        params = (start.isoformat(), end.isoformat(), *stores)
        with m.db() as con:
            legacy = [
                dict(r) for r in con.execute(
                    f"""SELECT date,store,user_id,employee_no,employee_name,
                               origin,activity,pieces,created_at
                        FROM operation_productivity
                        WHERE date>=? AND date<=? AND store IN ({marks})
                        ORDER BY date,id""",
                    params,
                ).fetchall()
            ]
            try:
                timer = [
                    dict(r) for r in con.execute(
                        f"""SELECT date,store,user_id,employee_no,employee_name,
                                   area,activity,pieces,started_at,duration_seconds
                            FROM operation_productivity_timer
                            WHERE date>=? AND date<=? AND store IN ({marks})
                              AND status='finished'
                            ORDER BY date,id""",
                        params,
                    ).fetchall()
                ]
            except Exception:
                timer = []

        # V200 copies Colgado/Doblado captures into operation_productivity.
        # Remove that exact duplicate and retain the timer row as source of truth.
        timer_keys = {_row_key(r, "area", "started_at") for r in timer}
        rows = []
        for r in legacy:
            if _row_key(r, "origin", "created_at") in timer_keys:
                continue
            rows.append({
                "date": str(r.get("date") or ""),
                "store": str(r.get("store") or ""),
                "user_id": r.get("user_id"),
                "employee_no": str(r.get("employee_no") or ""),
                "employee_name": str(r.get("employee_name") or ""),
                "area": str(r.get("origin") or ""),
                "activity": str(r.get("activity") or ""),
                "pieces": _num(r.get("pieces")),
                "duration_seconds": 0,
                "source": "historical",
            })
        for r in timer:
            rows.append({
                "date": str(r.get("date") or ""),
                "store": str(r.get("store") or ""),
                "user_id": r.get("user_id"),
                "employee_no": str(r.get("employee_no") or ""),
                "employee_name": str(r.get("employee_name") or ""),
                "area": str(r.get("area") or ""),
                "activity": str(r.get("activity") or ""),
                "pieces": _num(r.get("pieces")),
                "duration_seconds": int(_num(r.get("duration_seconds"))),
                "source": "timer",
            })
        return rows

    @m.app.get("/api/operation-productivity-ranking-v204")
    def productivity_ranking_v204(
        request: Request,
        period_type: str = "month",
        period_value: str = "",
        store: str = "Compañía",
        area: str = "Todas",
        activity: str = "Todas",
    ):
        actor = m.require_user(request)
        role = str(actor.get("role") or "").strip().lower()
        start, end = _period_bounds(period_type, period_value)
        active_stores = list(m.store_names(True) or [])
        selected_store = _effective_store(actor, store)

        if selected_store == "Compañía":
            if role not in PRIVILEGED:
                selected_store = _effective_store(actor, actor.get("store"))
            else:
                scope_stores = active_stores
        if selected_store != "Compañía":
            scope_stores = [selected_store]

        rows = _read_productivity_rows(start, end, scope_stores)
        # Operations ranking uses exactly the three activities and four areas
        # defined for the Operations capture.
        rows = [
            r for r in rows
            if str(r.get("area") or "") in AREAS
            and str(r.get("activity") or "") in ACTIVITIES
        ]
        if area and area != "Todas":
            rows = [r for r in rows if str(r.get("area") or "") == area]
        if activity and activity != "Todas":
            rows = [r for r in rows if str(r.get("activity") or "") == activity]

        target = _target()
        people = {}
        for r in rows:
            eno = str(r.get("employee_no") or "").strip()
            name = " ".join(str(r.get("employee_name") or "Sin nombre").split())
            st = _canonical_store(r.get("store"), active_stores)
            person_key = (eno or _norm(name), _norm(st))
            g = people.setdefault(person_key, {
                "employee_no": eno,
                "name": name,
                "store": st,
                "pieces": 0.0,
                "dates": set(),
                "areas": set(),
                "activities": set(),
                "duration_seconds": 0,
            })
            g["pieces"] += _num(r.get("pieces"))
            if r.get("date"):
                g["dates"].add(str(r.get("date")))
            if r.get("area"):
                g["areas"].add(str(r.get("area")))
            if r.get("activity"):
                g["activities"].add(str(r.get("activity")))
            g["duration_seconds"] += int(_num(r.get("duration_seconds")))

        collaborators = []
        for g in people.values():
            days = max(len(g["dates"]), 1)
            daily = g["pieces"] / days
            compliance = daily / target * 100.0 if target else 0.0
            collaborators.append({
                "employee_no": g["employee_no"],
                "name": g["name"],
                "store": g["store"],
                "pieces": g["pieces"],
                "days": days,
                "daily": daily,
                "target_daily": target,
                "compliance_pct": compliance,
                "areas": sorted(g["areas"]),
                "activities": sorted(g["activities"]),
                "duration_seconds": g["duration_seconds"],
            })

        # Build all active stores in company view so the table always keeps the
        # complete company structure; stores without captures remain at zero.
        store_names = scope_stores if selected_store != "Compañía" else active_stores
        store_rows = []
        for st in store_names:
            people_st = [r for r in collaborators if _norm(r["store"]) == _norm(st)]
            pieces = sum(_num(r["pieces"]) for r in people_st)
            collaborator_days = sum(int(r["days"]) for r in people_st)
            daily = pieces / collaborator_days if collaborator_days else 0.0
            compliance = daily / target * 100.0 if target else 0.0
            store_rows.append({
                "store": st,
                "pieces": pieces,
                "collaborators": len(people_st),
                "collaborator_days": collaborator_days,
                "daily": daily,
                "target_daily": target,
                "compliance_pct": compliance,
            })
        store_rows.sort(key=lambda r: (-r["daily"], -r["pieces"], _norm(r["store"])))
        store_rank_map = {}
        for idx, row in enumerate(store_rows, 1):
            row["rank"] = idx
            store_rank_map[_norm(row["store"])] = idx

        # Detail appears in store-ranking order, then collaborator ranking within
        # each store, exactly as requested: Iztapalapa -> its collaborators,
        # next ranked store -> its collaborators, etc.
        detailed = []
        for st_row in store_rows:
            local = [r for r in collaborators if _norm(r["store"]) == _norm(st_row["store"])]
            local.sort(key=lambda r: (-r["daily"], -r["pieces"], _norm(r["name"])))
            for local_rank, person in enumerate(local, 1):
                item = dict(person)
                item["store_rank"] = st_row["rank"]
                item["rank_in_store"] = local_rank
                detailed.append(item)

        # Store/Collaborator roles can never receive other stores in payload.
        restricted = role in ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria")
        if restricted:
            store_rows = [r for r in store_rows if _norm(r["store"]) == _norm(selected_store)]
            detailed = [r for r in detailed if _norm(r["store"]) == _norm(selected_store)]

        return {
            "period_type": str(period_type or "month"),
            "period_value": str(period_value or ""),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "role": role,
            "assigned_store": str(actor.get("store") or ""),
            "selected_store": selected_store,
            "restricted_to_store": restricted,
            "show_store_ranking": role in PRIVILEGED,
            "target_daily": target,
            "areas": list(AREAS),
            "activities": list(ACTIVITIES),
            "store_ranking": store_rows,
            "collaborator_ranking": detailed,
            "total_pieces": sum(_num(r["pieces"]) for r in detailed),
            "collaborators": len(detailed),
        }

    css = r'''<style id="v204-operation-productivity-css">
body[data-v163-module="operation"][data-v204-view="productivity"] #operativoPeriodBar{display:block!important}
body[data-v163-module="operation"][data-v204-view="capture"] #operativoPeriodBar{display:none!important}
.v204-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:9px 0 11px}
.v204-kpi{background:#fff;border:1px solid #d6e3f0;border-radius:15px;padding:12px;box-shadow:0 5px 18px rgba(25,72,118,.05)}
.v204-kpi small{display:block;color:#6d8094;font-size:7px;font-weight:950;text-transform:uppercase;letter-spacing:.04em}
.v204-kpi b{display:block;color:#123f73;font-size:21px;font-weight:950;margin-top:5px;letter-spacing:-.025em}
.v204-panel{background:#fff;border:1px solid #d6e3f0;border-radius:16px;padding:13px;margin:9px 0;box-shadow:0 6px 20px rgba(25,72,118,.05)}
.v204-panel h3{margin:0;color:#123f73;font-size:14px;font-weight:950}
.v204-note{margin-top:4px;color:#71849a;font-size:8px;line-height:1.45}
.v204-tablewrap{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #d8e4ef;border-radius:12px;margin-top:10px;background:#fff}
.v204-table{width:100%;min-width:880px;border-collapse:separate;border-spacing:0;font-size:8px}
.v204-table th{position:sticky;top:0;z-index:2;background:#124d84;color:#fff;padding:8px 7px;text-align:left;white-space:nowrap}
.v204-table td{padding:8px 7px;border-bottom:1px solid #e8eef4;color:#274d74;white-space:nowrap}
.v204-table tbody tr:nth-child(even) td{background:#f9fbfe}
.v204-table .num{text-align:right}.v204-table .strong{font-weight:950;color:#123f73}
.v204-store-rank{display:inline-grid;place-items:center;width:23px;height:23px;border-radius:8px;background:#eaf4ff;color:#0e62ad;font-weight:950}
.v204-local-rank{display:inline-flex;align-items:center;gap:5px;font-weight:950;color:#123f73}
.v204-store-group td{background:#edf6ff!important;color:#0e4c83!important;font-weight:950!important;border-bottom:1px solid #cfe3f6!important}
.v204-good{color:#079447!important;font-weight:950}.v204-warn{color:#d97706!important;font-weight:950}.v204-bad{color:#d92d20!important;font-weight:950}
.v204-empty{padding:24px;text-align:center;color:#71849a;font-size:9px}
.v204-capture-card{background:#fff;border:1px solid #d6e3f0;border-radius:16px;padding:16px;margin:8px 0 11px;box-shadow:0 6px 20px rgba(25,72,118,.05)}
.v204-capture-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap}
.v204-capture-head h3{margin:0;color:#123f73;font-size:15px;font-weight:950}
.v204-timer{min-width:145px;padding:10px 14px;border-radius:15px;background:#edf5ff;border:1px solid #d6e5f4;color:#10497f;font-size:28px;font-weight:950;text-align:center;font-variant-numeric:tabular-nums}
.v204-auto{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.v204-auto span{border:1px solid #dbe6f1;background:#f8fbff;color:#627890;border-radius:999px;padding:4px 8px;font-size:8px;font-weight:800}
.v204-form{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:10px}
.v204-field label{display:block;color:#66798e;font-size:8px;font-weight:950;text-transform:uppercase;margin-bottom:5px}
.v204-field select,.v204-field input{width:100%;min-height:48px;border:1px solid #ccd9e7;border-radius:12px;background:#fbfdff;color:#123f73;padding:9px 11px;font-size:15px;font-weight:800}
.v204-pieces{max-width:300px;margin-top:10px}.v204-pieces input{font-size:22px;font-weight:950}
.v204-actions{display:flex;gap:8px;margin-top:12px}.v204-actions button{border:0;border-radius:12px;padding:12px 19px;font-weight:950}
.v204-start{background:#13ad4f;color:#fff}.v204-finish{background:#ef9797;color:#fff}.v204-actions button:disabled{opacity:.45}
.v204-msg{min-height:16px;margin-top:7px;font-size:8.5px;color:#687b90}
@media(max-width:900px){
 .v204-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
 .v204-table{min-width:820px}
 .v204-form{grid-template-columns:1fr 1fr}
 .v204-capture-card{padding:13px}
 .v204-timer{font-size:24px;min-width:132px}
}
@media(max-width:390px){.v204-form{grid-template-columns:1fr}}
</style>'''

    js = r'''<script id="v204-operation-productivity-js">
(function(){
  if(window.__V204_OPERATION_PRODUCTIVITY)return;
  window.__V204_OPERATION_PRODUCTIVITY=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=v=>{const x=Number(v||0);return Number.isFinite(x)?x:0};
  const nf=v=>Math.round(n(v)).toLocaleString('es-MX');
  const pct=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%';
  const tone=v=>n(v)>=100?'v204-good':n(v)>=75?'v204-warn':'v204-bad';
  let currentView='';
  let timerRecord=null,timerId=0;

  function isOperation(){return String(document.body.dataset.v163Module||'').toLowerCase()==='operation'}
  function role(){try{return String(USER?.role||'').toLowerCase()}catch(_){return ''}}
  function assignedStore(){try{return String(USER?.store||'')}catch(_){return ''}}
  function isRestricted(){return ['tienda','colaborador','colaborador_operativo','colaborador_lenceria'].includes(role())}
  function setTab(key){
    window.V149_OPERATION_TAB=key;
    window.V125_OPERATION_TAB=key==='summary'?'daily':key;
    qa('#v200OperationTabs [data-v200-op]').forEach(btn=>{
      const on=btn.dataset.v200Op===key;
      btn.classList.toggle('active',on);
      btn.setAttribute('aria-selected',on?'true':'false');
    });
    const active=q('#v200OperationTabs [data-v200-op="'+key+'"]');
    try{active?.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}catch(_){}
  }
  async function A(url,opt){
    if(typeof api==='function')return api(url,{timeoutMs:120000,...(opt||{})});
    const r=await fetch(url,{credentials:'same-origin',...(opt||{})});
    const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch(_){}
    if(!r.ok)throw Error(d.detail||d.message||('HTTP '+r.status));return d;
  }
  function showShell(title,sub,key){
    setTab(key);currentView=key;document.body.dataset.v204View=key;
    const centro=q('#operativoCentro'),dyn=q('#operativoDynamic');
    centro?.classList.add('hidden');dyn?.classList.remove('hidden');
    if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent=title;
    if(q('#operativoDynamicSub'))q('#operativoDynamicSub').textContent=sub;
  }
  function mxToday(){
    return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  }
  function weekOfDate(ds){
    const d=new Date(ds+'T12:00:00'),target=new Date(d.valueOf());
    const dayNr=(d.getDay()+6)%7;target.setDate(target.getDate()-dayNr+3);
    const firstThursday=new Date(target.getFullYear(),0,4);
    const week=1+Math.round(((target-firstThursday)/86400000-3+(firstThursday.getDay()+6)%7)/7);
    return target.getFullYear()+'-W'+String(week).padStart(2,'0');
  }
  function setOptions(el,values,current){
    if(!el)return;el.innerHTML='';
    values.forEach(v=>el.add(new Option(v.label??v.value??v,v.value??v)));
    if(current&&Array.from(el.options).some(o=>o.value===current))el.value=current;
  }
  async function configureRankingFilters(){
    const meta=await A('/api/operation/meta');
    const bar=q('#operativoPeriodBar');bar?.classList.remove('hidden');if(bar)bar.style.display='block';
    const mode=q('#operPeriodMode'),period=q('#operPeriodSelect'),store=q('#operStoreSelect'),area=q('#operAreaSelect'),activity=q('#operActivitySelect');
    const currentMode=String(mode?.value||OPER_PERIOD?.type||'month');
    if(mode){
      setOptions(mode,[{label:'Día',value:'day'},{label:'Semanal',value:'week'},{label:'Mensual',value:'month'},{label:'Anual',value:'year'}],currentMode);
      mode.value=['day','week','month','year'].includes(currentMode)?currentMode:'month';
    }
    const ptype=String(mode?.value||'month');
    let vals=ptype==='day'?(meta.dates||[]):ptype==='week'?(meta.weeks||[]):ptype==='year'?(meta.years||[]):(meta.months||[]);
    const today=mxToday();
    const fallback=ptype==='day'?today:ptype==='week'?weekOfDate(today):ptype==='year'?today.slice(0,4):today.slice(0,7);
    vals=[...new Set([...(vals||[]),fallback])].sort();
    const oldPeriod=String(period?.value||OPER_PERIOD?.value||fallback);
    setOptions(period,vals,vals.includes(oldPeriod)?oldPeriod:fallback);
    if(period&&!period.value)period.value=fallback;
    try{OPER_PERIOD.type=ptype;OPER_PERIOD.value=period?.value||fallback}catch(_){}
    if(q('#operPeriodModeLabel'))q('#operPeriodModeLabel').textContent='Vista';
    if(q('#operPeriodLabel'))q('#operPeriodLabel').textContent=ptype==='day'?'Fecha':ptype==='week'?'Semana ISO':ptype==='year'?'Año':'Periodo';

    if(store){
      const old=String(store.value||'');
      store.innerHTML='';
      if(!isRestricted())store.add(new Option('Compañía','Compañía'));
      (meta.stores||[]).forEach(s=>store.add(new Option(s,s)));
      if(isRestricted()){
        store.value=assignedStore()||meta.stores?.[0]||'';store.disabled=true;
      }else{
        store.disabled=false;
        store.value=Array.from(store.options).some(o=>o.value===old)?old:'Compañía';
      }
      store.closest('.filter')?.classList.remove('hidden');
      const lab=store.closest('.filter')?.querySelector('label');if(lab)lab.textContent='Tienda';
    }
    if(area){
      const old=String(area.value||'Todas');
      setOptions(area,['Todas','Doblado','Colgado','Jeans','Lencería'],old);
      area.value=Array.from(area.options).some(o=>o.value===old)?old:'Todas';
      area.closest('.filter')?.classList.remove('hidden');
      const lab=area.closest('.filter')?.querySelector('label');if(lab)lab.textContent='Área';
    }
    if(activity){
      const old=String(activity.value||'Todas');
      setOptions(activity,['Todas','Acondicionado','Clasificado','Ubicado'],old);
      activity.value=Array.from(activity.options).some(o=>o.value===old)?old:'Todas';
      activity.disabled=false;activity.closest('.filter')?.classList.remove('hidden');
      const lab=activity.closest('.filter')?.querySelector('label');if(lab)lab.textContent='Actividad';
    }
  }
  function rankingQuery(){
    const mode=q('#operPeriodMode')?.value||'month',period=q('#operPeriodSelect')?.value||'';
    try{OPER_PERIOD.type=mode;OPER_PERIOD.value=period}catch(_){}
    return new URLSearchParams({
      period_type:mode,period_value:period,
      store:q('#operStoreSelect')?.value||assignedStore()||'Compañía',
      area:q('#operAreaSelect')?.value||'Todas',
      activity:q('#operActivitySelect')?.value||'Todas'
    });
  }
  function storeTable(rows){
    return '<div class="v204-tablewrap"><table class="v204-table"><thead><tr><th>#</th><th>Tienda</th><th class="num">Piezas</th><th class="num">Colaboradores</th><th class="num">Días-colab.</th><th class="num">Pzas/día</th><th class="num">% Meta</th></tr></thead><tbody>'+
      (rows||[]).map(r=>'<tr><td><span class="v204-store-rank">'+r.rank+'</span></td><td class="strong">'+esc(r.store)+'</td><td class="num">'+nf(r.pieces)+'</td><td class="num">'+nf(r.collaborators)+'</td><td class="num">'+nf(r.collaborator_days)+'</td><td class="num"><b>'+nf(r.daily)+'</b></td><td class="num '+tone(r.compliance_pct)+'">'+pct(r.compliance_pct)+'</td></tr>').join('')+
      (!(rows||[]).length?'<tr><td colspan="7" class="v204-empty">Sin productividad para el periodo.</td></tr>':'')+
      '</tbody></table></div>';
  }
  function collaboratorTable(rows,grouped){
    let lastStore='';
    const body=(rows||[]).map(r=>{
      let group='';
      if(grouped&&r.store!==lastStore){
        lastStore=r.store;
        group='<tr class="v204-store-group"><td colspan="10">#'+r.store_rank+' · '+esc(r.store)+'</td></tr>';
      }
      return group+'<tr><td><span class="v204-local-rank">#'+r.rank_in_store+'</span></td><td class="strong">'+esc(r.name)+'</td><td>'+esc(r.employee_no||'—')+'</td><td>'+esc(r.store)+'</td><td class="num">'+nf(r.pieces)+'</td><td class="num">'+nf(r.days)+'</td><td class="num"><b>'+nf(r.daily)+'</b></td><td class="num '+tone(r.compliance_pct)+'">'+pct(r.compliance_pct)+'</td><td>'+esc((r.areas||[]).join(', '))+'</td><td>'+esc((r.activities||[]).join(', '))+'</td></tr>';
    }).join('');
    return '<div class="v204-tablewrap"><table class="v204-table"><thead><tr><th>Ranking</th><th>Colaborador</th><th>Nómina</th><th>Tienda</th><th class="num">Piezas</th><th class="num">Días</th><th class="num">Pzas/día</th><th class="num">% Meta</th><th>Área</th><th>Actividad</th></tr></thead><tbody>'+
      (body||'<tr><td colspan="10" class="v204-empty">Sin colaboradores con productividad para el periodo seleccionado.</td></tr>')+
      '</tbody></table></div>';
  }
  async function renderRanking(){
    showShell('Productividad','Ranking de tiendas y colaboradores','productivity');
    clearInterval(timerId);
    const host=q('#operativoDynamicContent');if(!host)return;
    host.innerHTML='<div class="infoempty">Calculando ranking de productividad…</div>';
    try{
      await configureRankingFilters();
      const d=await A('/api/operation-productivity-ranking-v204?'+rankingQuery());
      const rows=d.collaborator_ranking||[],stores=d.store_ranking||[];
      const avg=rows.length?rows.reduce((a,r)=>a+n(r.daily),0)/rows.length:0;
      const avgPct=rows.length?rows.reduce((a,r)=>a+n(r.compliance_pct),0)/rows.length:0;
      const scope=d.restricted_to_store?('Sólo '+(d.selected_store||d.assigned_store)):((d.selected_store||'Compañía')==='Compañía'?'Todas las tiendas':d.selected_store);
      let html='<div class="v204-kpis">'+
        '<div class="v204-kpi"><small>Piezas</small><b>'+nf(d.total_pieces)+'</b></div>'+
        '<div class="v204-kpi"><small>Colaboradores</small><b>'+nf(d.collaborators)+'</b></div>'+
        '<div class="v204-kpi"><small>Prod. diaria prom.</small><b>'+nf(avg)+'</b></div>'+
        '<div class="v204-kpi"><small>Cumplimiento prom.</small><b>'+pct(avgPct)+'</b></div>'+
      '</div>';
      if(d.show_store_ranking){
        html+='<div class="v204-panel"><h3>Ranking de tiendas</h3><div class="v204-note">Ordenado por productividad promedio diaria. '+esc(scope)+' · Meta '+nf(d.target_daily)+' pzas/día.</div>'+storeTable(stores)+'</div>';
      }
      html+='<div class="v204-panel"><h3>'+(d.restricted_to_store?'Ranking de colaboradores · '+esc(d.selected_store):'Detalle de colaboradores por ranking de tienda')+'</h3>'+
        '<div class="v204-note">'+(d.restricted_to_store?'Este perfil sólo puede consultar colaboradores de su propia tienda.':'Primero aparece la tienda según su posición y debajo sus colaboradores ordenados por productividad.')+'</div>'+
        collaboratorTable(rows,!d.restricted_to_store)+'</div>';
      host.innerHTML=html;
    }catch(e){host.innerHTML='<div class="infoempty">No fue posible cargar Productividad: '+esc(e.message||e)+'</div>'}
  }

  function hms(sec){
    sec=Math.max(0,Math.floor(Number(sec)||0));
    return [Math.floor(sec/3600),Math.floor((sec%3600)/60),sec%60].map(x=>String(x).padStart(2,'0')).join(':');
  }
  function updateClock(){
    const el=q('#v204Timer');if(!el)return;
    if(!timerRecord?.started_at){el.textContent='00:00:00';return}
    el.textContent=hms((Date.now()-new Date(timerRecord.started_at).getTime())/1000);
  }
  function startClock(){clearInterval(timerId);updateClock();timerId=setInterval(updateClock,1000)}
  async function renderCapture(){
    showShell('Cargar productividad','Operación · registro de actividad, área, piezas y tiempo real','capture');
    const bar=q('#operativoPeriodBar');bar?.classList.add('hidden');if(bar)bar.style.display='none';
    const host=q('#operativoDynamicContent');if(!host)return;
    host.innerHTML='<div class="infoempty">Preparando captura…</div>';
    try{
      const [meta,active]=await Promise.all([
        A('/api/operation-productivity-timer/meta?store='+encodeURIComponent(assignedStore())),
        A('/api/operation-productivity-timer/active')
      ]);
      timerRecord=active.item||null;
      const hist=await A('/api/operation-productivity-timer/history?date='+encodeURIComponent(meta.date)+'&store='+encodeURIComponent(meta.store||''));
      const selectedActivity=timerRecord?.activity||'Acondicionado';
      const selectedArea=timerRecord?.area||'Doblado';
      host.innerHTML='<div class="v204-capture-card"><div class="v204-capture-head"><div><h3>Registro de productividad</h3><div class="v204-note">La fecha, tienda, colaborador y nómina se asignan automáticamente desde tu sesión.</div></div><div id="v204Timer" class="v204-timer">00:00:00</div></div>'+
        '<div class="v204-auto"><span>'+esc(meta.date)+'</span><span>'+esc(meta.store)+'</span><span>'+esc(meta.employee_name)+'</span><span>Nómina '+esc(meta.employee_no||'—')+'</span></div>'+
        '<div class="v204-form"><div class="v204-field"><label>Actividad</label><select id="v204Activity" '+(timerRecord?'disabled':'')+'>'+['Acondicionado','Clasificado','Ubicado'].map(x=>'<option '+(x===selectedActivity?'selected':'')+'>'+x+'</option>').join('')+'</select></div>'+
        '<div class="v204-field"><label>Área</label><select id="v204Area" '+(timerRecord?'disabled':'')+'>'+['Doblado','Colgado','Jeans','Lencería'].map(x=>'<option '+(x===selectedArea?'selected':'')+'>'+x+'</option>').join('')+'</select></div></div>'+
        '<div class="v204-field v204-pieces"><label>Piezas</label><input id="v204Pieces" type="number" min="0" inputmode="numeric" value="'+n(timerRecord?.pieces)+'"></div>'+
        '<div class="v204-actions"><button id="v204Start" class="v204-start" '+(timerRecord?'disabled':'')+'>▶ Inicio</button><button id="v204Finish" class="v204-finish" '+(!timerRecord?'disabled':'')+'>■ Fin</button></div><div id="v204Msg" class="v204-msg"></div></div>'+
        '<div class="v204-panel"><h3>Capturas de hoy</h3><div class="v204-note">Registro real de productividad de la sesión.</div>'+
        '<div class="v204-tablewrap"><table class="v204-table"><thead><tr><th>Colaborador</th><th>Nómina</th><th>Actividad</th><th>Área</th><th class="num">Piezas</th><th class="num">Tiempo</th><th>Estado</th></tr></thead><tbody>'+
        ((hist.items||[]).map(r=>'<tr><td class="strong">'+esc(r.employee_name)+'</td><td>'+esc(r.employee_no||'—')+'</td><td>'+esc(r.activity)+'</td><td>'+esc(r.area)+'</td><td class="num">'+nf(r.pieces)+'</td><td class="num">'+hms(r.duration_seconds)+'</td><td>'+(r.status==='active'?'En curso':'Finalizado')+'</td></tr>').join('')||'<tr><td colspan="7" class="v204-empty">Sin capturas de hoy.</td></tr>')+
        '</tbody></table></div></div>';
      if(timerRecord)startClock();else{clearInterval(timerId);updateClock()}
      q('#v204Start')?.addEventListener('click',async()=>{
        const msg=q('#v204Msg');msg.textContent='Iniciando…';
        try{
          const r=await A('/api/operation-productivity-timer/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({store:meta.store,activity:q('#v204Activity').value,area:q('#v204Area').value})});
          msg.textContent=r.message;await renderCapture();
        }catch(e){msg.textContent=e.message||String(e)}
      });
      q('#v204Finish')?.addEventListener('click',async()=>{
        if(!timerRecord)return;const msg=q('#v204Msg');msg.textContent='Finalizando…';
        try{
          const r=await A('/api/operation-productivity-timer/'+timerRecord.id+'/finish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pieces:n(q('#v204Pieces')?.value)})});
          msg.textContent=r.message;timerRecord=null;clearInterval(timerId);await renderCapture();
        }catch(e){msg.textContent=e.message||String(e)}
      });
    }catch(e){host.innerHTML='<div class="infoempty">No fue posible abrir Cargar productividad: '+esc(e.message||e)+'</div>'}
  }

  // Capture phase takes ownership of the two tabs so older renderers cannot
  // cross their contents again.
  document.addEventListener('click',e=>{
    if(!isOperation())return;
    const tab=e.target.closest?.('#v200OperationTabs [data-v200-op]');
    if(tab){
      const key=tab.dataset.v200Op;
      if(key==='capture'||key==='productivity'){
        // Let DEMO V201 own its own tabs when DEMO is active.
        if(document.body.classList.contains('v201-demo-mode'))return;
        e.preventDefault();e.stopImmediatePropagation();
        if(key==='capture')renderCapture();else renderRanking();
        return;
      }
    }
    const consult=e.target.closest?.('#operPeriodApply');
    if(consult&&currentView==='productivity'&&!document.body.classList.contains('v201-demo-mode')){
      e.preventDefault();e.stopImmediatePropagation();renderRanking();return;
    }
  },true);

  document.addEventListener('change',e=>{
    if(currentView!=='productivity'||document.body.classList.contains('v201-demo-mode'))return;
    if(e.target?.matches?.('#operPeriodMode')){
      try{OPER_PERIOD.type=e.target.value;OPER_PERIOD.value=''}catch(_){}
      setTimeout(renderRanking,30);
    }
  },true);

  function setup(){
    if(!isOperation())return;
    const active=q('#v200OperationTabs [data-v200-op].active')?.dataset.v200Op;
    if(active==='capture'&&currentView!=='capture')renderCapture();
    if(active==='productivity'&&currentView!=='productivity')renderRanking();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [450,1200].forEach(ms=>setTimeout(setup,ms));
  console.info('[V204] Captura y ranking de Productividad separados por rol.');
})();
</script>'''

    @m.app.middleware("http")
    async def v204_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v204-operation-productivity-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v204-operation-productivity-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V204",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V204] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V204_OPERATION_PRODUCTIVITY_RANKING = True
    print("[V204] Productividad separada de captura + ranking por rol instalado.", flush=True)
