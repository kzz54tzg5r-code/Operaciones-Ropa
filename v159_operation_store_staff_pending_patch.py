"""V159 · Operación por tienda + personal requerido + piezas pendientes.

- Conserva el filtro real de Tienda y garantiza que el Resumen se recalcule por tienda.
- Agrega "Colaboradores necesarios" al Resumen y al desempeño por tienda.
- Agrega "Piezas pendientes" a Captura diaria de Origen.
- Piezas pendientes capturadas son el cierre autoritativo de Origen; si no existen,
  se usa el pendiente derivado histórico como compatibilidad.
- Personal requerido = ceil(pendiente Origen / estándar ponderado Colgado-Doblado)
  + ceil(pendiente Cambios y Muertos / estándar C&M).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import math
import re

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V159_OPERATION_STORE_STAFF_PENDING", False):
        return

    # Migración no destructiva: los registros anteriores quedan NULL y conservan
    # la fórmula histórica hasta que la tienda capture el pendiente explícito.
    try:
        with m.db() as con:
            cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(operation_daily_capture)").fetchall()}
            if "pending_manual" not in cols:
                con.execute("ALTER TABLE operation_daily_capture ADD COLUMN pending_manual REAL")
    except Exception as exc:
        print(f"[V159] Migración pending_manual: {type(exc).__name__}: {exc}", flush=True)

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def iso_day(v):
        s = str(v or "")[:10]
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except Exception:
            raise HTTPException(400, "Fecha inválida")

    def bounds(kind, value):
        kind = str(kind or "day").lower().strip(); value = str(value or "").strip(); today = datetime.now(MX).date()
        if kind == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date(); return d, d
        if kind == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt: y, w = int(mt.group(1)), int(mt.group(2))
            else: iso = today.isocalendar(); y, w = iso.year, iso.week
            d = date.fromisocalendar(y, w, 1); return d, d + timedelta(days=6)
        if kind == "month":
            if value:
                y, mo = [int(x) for x in value.split("-")[:2]]
            else: y, mo = today.year, today.month
            d = date(y, mo, 1); nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1); return d, nxt - timedelta(days=1)
        if kind == "year":
            y = int(value or today.year); return date(y, 1, 1), date(y, 12, 31)
        raise HTTPException(400, "Vista inválida")

    def scoped(actor, requested):
        role = str(actor.get("role") or ""); assigned = str(actor.get("store") or "").strip()
        if role in ("tienda", "colaborador"):
            if not assigned:
                raise HTTPException(409, "El usuario no tiene tienda asignada")
            return assigned
        return str(requested or "Compañía").strip() or "Compañía"

    def stores_for(actor, requested):
        selected = scoped(actor, requested)
        if selected != "Compañía":
            return [selected], selected
        try:
            return list(m.store_names(True)), "Compañía"
        except Exception:
            return list(getattr(m, "PROJECT_STORES", [])), "Compañía"

    def stds():
        out = {"Colgado": 1228.0, "Doblado": 906.0, "Cambios y Muertos": 670.0}
        try:
            with m.db() as con:
                for r in con.execute("SELECT origin,pieces_per_shift FROM operation_standards").fetchall():
                    out[str(r["origin"])] = num(r["pieces_per_shift"])
        except Exception:
            pass
        return out

    def is_open(store, day):
        with m.db() as con:
            r = con.execute("SELECT status FROM operation_day_status WHERE date=? AND store=?", (day, store)).fetchone()
        return not r or str(r["status"] or "open") != "closed"

    @m.app.get("/api/operation/origin-capture-v159")
    def origin_capture_v159(request: Request, date: str, store: str):
        actor = m.require_user(request); day = iso_day(date); st = scoped(actor, store)
        if not st or st == "Compañía":
            raise HTTPException(400, "Selecciona una tienda")
        with m.db() as con:
            row = con.execute("SELECT arrival,released,pending_manual,notes,updated_at,updated_by FROM operation_daily_capture WHERE date=? AND store=? AND origin='Origen'", (day, st)).fetchone()
            if row:
                data = dict(row)
            else:
                legacy = con.execute("SELECT COALESCE(SUM(arrival),0) arrival,COALESCE(SUM(released),0) released FROM operation_daily_capture WHERE date=? AND store=? AND origin IN ('Colgado','Doblado')", (day, st)).fetchone()
                data = {"arrival": num(legacy["arrival"]) if legacy else 0, "released": num(legacy["released"]) if legacy else 0, "pending_manual": None, "notes":"", "updated_at":"", "updated_by":""}
            status = con.execute("SELECT status,closed_at,closed_by FROM operation_day_status WHERE date=? AND store=?", (day, st)).fetchone()
        return {"date":day,"store":st,"arrival":num(data.get("arrival")),"released":num(data.get("released")),"pending":None if data.get("pending_manual") is None else num(data.get("pending_manual")),"status":dict(status) if status else {"status":"open"},"can_capture":str(actor.get("role") or "") in ("superadmin","admin","tienda")}

    @m.app.post("/api/operation/origin-capture-v159")
    async def origin_capture_save_v159(request: Request):
        actor = m.require_user(request, ("superadmin","admin","tienda")); body = await request.json(); day = iso_day(body.get("date")); st = scoped(actor, body.get("store"))
        if not st or st == "Compañía":
            raise HTTPException(400, "Selecciona una tienda")
        if not is_open(st, day):
            raise HTTPException(409, "El corte de ese día está cerrado")
        arrival = max(num(body.get("arrival")), 0); released = max(num(body.get("released")), 0); pending = max(num(body.get("pending")), 0); now = datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            con.execute("""INSERT INTO operation_daily_capture(date,store,origin,arrival,released,pending_manual,notes,updated_at,updated_by)
                           VALUES(?,?,?,?,?,?,'',?,?)
                           ON CONFLICT(date,store,origin) DO UPDATE SET arrival=excluded.arrival,released=excluded.released,pending_manual=excluded.pending_manual,updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
                        (day, st, "Origen", arrival, released, pending, now, str(actor.get("username") or "")))
            try:
                con.execute("INSERT INTO operation_audit(entity,entity_key,action,before_json,after_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)", ("daily_capture", f"{day}|{st}|Origen", "upsert_v159", "{}", f'{{"arrival":{arrival},"released":{released},"pending":{pending}}}', now, str(actor.get("username") or "")))
            except Exception:
                pass
        return {"ok":True,"message":"Captura diaria guardada","arrival":arrival,"released":released,"pending":pending}

    @m.app.get("/api/operation/staff-needed-v159")
    def staff_needed_v159(request: Request, period_type: str="day", period_value: str="", store: str="Compañía"):
        actor = m.require_user(request); start, end = bounds(period_type, period_value); stores, selected = stores_for(actor, store); ss, es = start.isoformat(), end.isoformat(); standard = stds()
        if not stores:
            return {"store":selected,"total_required":0,"rows":[],"formula":""}
        ph = ",".join("?" for _ in stores)
        with m.db() as con:
            caps = [dict(r) for r in con.execute(f"SELECT date,store,arrival,pending_manual FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ({ph}) ORDER BY date", (es,*stores)).fetchall()]
            prod = [dict(r) for r in con.execute(f"SELECT date,store,origin,pieces FROM operation_productivity WHERE origin IN ('Colgado','Doblado') AND date<=? AND store IN ({ph}) ORDER BY date", (es,*stores)).fetchall()]
            try:
                active = {str(r["store"]):int(r["c"]) for r in con.execute(f"SELECT store,COUNT(*) c FROM users WHERE role='colaborador' AND active=1 AND store IN ({ph}) GROUP BY store", tuple(stores)).fetchall()}
            except Exception:
                active = {}
        stset = set(stores); cm=[]
        try:
            for r in (m.load_ops() or {}).get("rows",[]):
                ds=str(r.get("date") or "")[:10]; st=str(r.get("store") or "").strip()
                if not ds or st not in stset: continue
                try: d=date.fromisoformat(ds)
                except Exception: continue
                if d>end: continue
                cm.append({"date":ds,"store":st,"arrival":num(r.get("recolectadas")),"processed":num(r.get("acondicionado"))})
        except Exception as exc:
            print(f"[V159] staff C&M: {type(exc).__name__}: {exc}", flush=True)

        rows=[]
        for st in stores:
            # Pendiente derivado histórico de Origen al cierre del periodo.
            hist_arr=sum(num(r.get("arrival")) for r in caps if r["store"]==st and str(r["date"])<=es)
            hist_proc=sum(num(r.get("pieces")) for r in prod if r["store"]==st and str(r["date"])<=es)
            derived=max(hist_arr-hist_proc,0.0)
            # Si existe captura explícita de pendientes, usa la más reciente del periodo.
            explicit=[r for r in caps if r["store"]==st and ss<=str(r["date"])<=es and r.get("pending_manual") is not None]
            explicit.sort(key=lambda r:str(r["date"]))
            origin_pending=num(explicit[-1]["pending_manual"]) if explicit else derived
            # Mezcla real Colgado/Doblado del periodo; si no hay mezcla, usa promedio simple.
            pc=sum(num(r.get("pieces")) for r in prod if r["store"]==st and ss<=str(r["date"])<=es and r.get("origin")=="Colgado")
            pd=sum(num(r.get("pieces")) for r in prod if r["store"]==st and ss<=str(r["date"])<=es and r.get("origin")=="Doblado")
            mix=pc+pd
            origin_std=((pc*standard["Colgado"]+pd*standard["Doblado"])/mix) if mix>0 else ((standard["Colgado"]+standard["Doblado"])/2)
            cm_arr=sum(num(r["arrival"]) for r in cm if r["store"]==st and str(r["date"])<=es); cm_proc=sum(num(r["processed"]) for r in cm if r["store"]==st and str(r["date"])<=es); cm_pending=max(cm_arr-cm_proc,0.0)
            req_origin=int(math.ceil(origin_pending/origin_std)) if origin_pending>0 and origin_std>0 else 0
            req_cm=int(math.ceil(cm_pending/standard["Cambios y Muertos"])) if cm_pending>0 and standard["Cambios y Muertos"]>0 else 0
            required=req_origin+req_cm; current=int(active.get(st,0)); gap=max(required-current,0)
            rows.append({"store":st,"origin_pending":origin_pending,"cm_pending":cm_pending,"pending_total":origin_pending+cm_pending,"origin_standard":origin_std,"origin_required":req_origin,"cm_required":req_cm,"required":required,"active_collaborators":current,"gap":gap,"pending_source":"capturado" if explicit else "calculado"})
        rows.sort(key=lambda x:(-x["required"],-x["pending_total"],x["store"]))
        total_required=sum(r["required"] for r in rows); total_active=sum(r["active_collaborators"] for r in rows); total_gap=sum(r["gap"] for r in rows)
        return {"store":selected,"start_date":ss,"end_date":es,"total_required":total_required,"total_active":total_active,"total_gap":total_gap,"rows":rows,"formula":"Origen = redondeo superior(pendiente / estándar ponderado Colgado-Doblado); C&M = redondeo superior(pendiente / estándar 670); total = ambos."}

    css=r'''<style id="v159-operation-css">
.v159-staff{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;margin:9px 0}.v159-staff h3{margin:0 0 7px;color:var(--navy);font-size:12px}.v159-staff-note{font-size:8px;color:#667085;line-height:1.45;margin-top:6px}.v159-pending-field{min-width:0}.v159-pending-field label{display:block;font-size:8px;font-weight:950;color:#667085;text-transform:uppercase;margin-bottom:5px}.v159-pending-field input{width:100%;min-height:44px;border:1px solid #ccd6e2;border-radius:10px;background:#fff;color:var(--text);padding:9px 10px;font-size:16px}@media(max-width:900px){.v159-staff{padding:10px}.v159-pending-field input{font-size:16px}}</style>'''

    js=r'''<script id="v159-operation-js">
(function(){
if(window.__V159_OPERATION)return;window.__V159_OPERATION=true;
const OP='Operación',num=v=>Number(v||0),fmt=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:0}),f1=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1}),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function activeTab(){const a=document.querySelector('.v125-tabs .active');const t=(a?.textContent||'').toLowerCase();if(t.includes('captura diaria'))return'daily';if(t.includes('resumen'))return'summary';return''}
async function decorateDaily(){
 if(activeTab()!=='daily')return;const store=document.getElementById('operStoreSelect')?.value||'',day=document.getElementById('operPeriodSelect')?.value||'';if(!store||store==='Compañía'||!day)return;
 let data;try{data=await api('/api/operation/origin-capture-v159?'+new URLSearchParams({date:day,store}),{timeoutMs:60000})}catch(e){console.warn('[V159] pendiente diario',e);return}
 if(!document.getElementById('v159OriginPending')){const rel=document.getElementById('v125OriginReleased');const host=rel?.closest('.v125-field')||rel?.parentElement;if(host){const w=document.createElement('div');w.className='v159-pending-field';w.innerHTML='<label>Origen · Piezas pendientes</label><input id="v159OriginPending" type="number" min="0" inputmode="numeric" value="0">';host.insertAdjacentElement('afterend',w)}}
 const inp=document.getElementById('v159OriginPending');if(inp)inp.value=data.pending==null?'0':String(data.pending);
 const old=document.getElementById('v125SaveOrigin');if(old&&!old.dataset.v159){const b=old.cloneNode(true);b.dataset.v159='1';old.replaceWith(b);b.addEventListener('click',async()=>{const msg=document.getElementById('v125DailyMsg');try{const r=await api('/api/operation/origin-capture-v159',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:document.getElementById('operPeriodSelect')?.value||day,store:document.getElementById('operStoreSelect')?.value||store,arrival:num(document.getElementById('v125OriginArrival')?.value),released:num(document.getElementById('v125OriginReleased')?.value),pending:num(document.getElementById('v159OriginPending')?.value)})});if(msg){msg.className='v125-msg ok';msg.textContent=r.message}setTimeout(()=>window.renderOperativoView(OP,true),300)}catch(e){if(msg){msg.className='v125-msg err';msg.textContent=e.message}else alert(e.message)}})}
}
function findPanel(title){return [...document.querySelectorAll('.v149-panel')].find(p=>(p.querySelector('h3')?.textContent||'').trim()===title)}
async function decorateSummary(){
 if(activeTab()!=='summary')return;const store=document.getElementById('operStoreSelect')?.value||'Compañía',ptype=(document.getElementById('operPeriodMode')?.value||'day'),pval=document.getElementById('operPeriodSelect')?.value||'';let d;try{d=await api('/api/operation/staff-needed-v159?'+new URLSearchParams({period_type:ptype,period_value:pval,store}),{timeoutMs:180000})}catch(e){console.warn('[V159] personal requerido',e);return}
 const k=document.querySelector('.v149-kpis');if(k&&!k.querySelector('[data-v159-staff-kpi]')){const x=document.createElement('div');x.className='v149-kpi';x.dataset.v159StaffKpi='1';x.style.setProperty('--k','#0f766e');const row=d.rows?.[0],sub=store==='Compañía'?`Brecha total: ${fmt(d.total_gap)}`:`Origen ${fmt(row?.origin_required)} · C&M ${fmt(row?.cm_required)}`;x.innerHTML=`<small>Colaboradores necesarios</small><b>${fmt(d.total_required)}</b><span>${sub}</span>`;k.appendChild(x)}
 const panel=findPanel('Desempeño por tienda');const table=panel?.querySelector('table');if(table&&!table.dataset.v159){table.dataset.v159='1';const th=document.createElement('th');th.textContent='Colab. necesarios';table.querySelector('thead tr')?.appendChild(th);const map=new Map((d.rows||[]).map(r=>[r.store,r]));table.querySelectorAll('tbody tr').forEach(tr=>{const name=(tr.cells?.[0]?.textContent||'').trim();const r=map.get(name);const td=document.createElement('td');td.innerHTML=r?`<b>${fmt(r.required)}</b><div style="font-size:7px;color:#667085">Actual ${fmt(r.active_collaborators)} · Faltan ${fmt(r.gap)}</div>`:'—';tr.appendChild(td)})}
 if(panel&&!document.getElementById('v159StaffDetail')){const box=document.createElement('div');box.id='v159StaffDetail';box.className='v159-staff';box.innerHTML=`<h3>Personal requerido · ${esc(store)}</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Pendiente Origen</th><th>Pendiente C&M</th><th>Necesarios</th><th>Activos</th><th>Brecha</th></tr></thead><tbody>${(d.rows||[]).map(r=>`<tr><td><b>${esc(r.store)}</b></td><td>${fmt(r.origin_pending)} <small>(${esc(r.pending_source)})</small></td><td>${fmt(r.cm_pending)}</td><td><b>${fmt(r.required)}</b></td><td>${fmt(r.active_collaborators)}</td><td>${fmt(r.gap)}</td></tr>`).join('')}</tbody></table></div><div class="v159-staff-note">${esc(d.formula||'')}</div>`;panel.insertAdjacentElement('afterend',box)}
}
async function decorate(){if(String(window.MAIN||'').toLowerCase()!=='operation'&&window.OP_VIEW!==OP)return;await decorateDaily();await decorateSummary()}
const previous=window.renderOperativoView;window.renderOperativoView=async function(name,force=false){const out=await previous(name,force);if(name===OP){await decorate();setTimeout(decorate,120)}return out};
document.addEventListener('click',e=>{if(e.target.closest?.('[data-main="operation"],.v125-tab,#operPeriodApply'))setTimeout(decorate,350)},true);document.addEventListener('change',e=>{if(e.target?.matches?.('#operStoreSelect,#operPeriodMode,#operPeriodSelect'))setTimeout(decorate,250)},true);setTimeout(decorate,600);console.info('[V159] Tienda + colaboradores necesarios + piezas pendientes activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v159_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator: body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v159-operation-css" not in html: html=html.replace("</head>",css+"</head>",1)
            if "v159-operation-js" not in html: html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V159"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V159] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V159_OPERATION_STORE_STAFF_PENDING=True
    print("[V159] Operación: filtro por tienda, personal requerido y piezas pendientes activos.",flush=True)
