"""V159.1 · Operación Origen + personal requerido + piezas pendientes.

- Conserva el filtro real de Tienda y garantiza que el Resumen se recalcule por tienda.
- Agrega "Colaboradores necesarios" al Resumen y al desempeño por tienda.
- Agrega "Piezas pendientes" a Captura diaria de Origen.
- Piezas pendientes capturadas son el cierre autoritativo de Origen; si no existen,
  se usa el pendiente derivado histórico como compatibilidad.
- Personal requerido = ceil(pendiente Origen / estándar ponderado Colgado-Doblado).
- Cambios y Muertos no participa en los cálculos del módulo Operación.
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

    # V287: pendiente inicial único + excedente separado.
    try:
        with m.db() as con:
            cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(operation_daily_capture)").fetchall()}
            if "pending_manual" not in cols:
                con.execute("ALTER TABLE operation_daily_capture ADD COLUMN pending_manual REAL")
            if "excess" not in cols:
                con.execute("ALTER TABLE operation_daily_capture ADD COLUMN excess REAL NOT NULL DEFAULT 0")
            con.execute("""CREATE TABLE IF NOT EXISTS operation_pending_seed(
                store TEXT PRIMARY KEY,
                seed_date TEXT NOT NULL,
                seed_pending REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT ''
            )""")
            now = datetime.now(MX).isoformat(timespec="seconds")
            anchors = con.execute(
                """SELECT c.store,c.date,c.pending_manual,c.updated_at,c.updated_by
                   FROM operation_daily_capture c
                   JOIN (
                     SELECT store,MAX(date) max_date
                     FROM operation_daily_capture
                     WHERE origin='Origen' AND pending_manual IS NOT NULL
                     GROUP BY store
                   ) x ON x.store=c.store AND x.max_date=c.date
                   WHERE c.origin='Origen' AND c.pending_manual IS NOT NULL"""
            ).fetchall()
            for a in anchors:
                con.execute(
                    """INSERT OR IGNORE INTO operation_pending_seed(
                         store,seed_date,seed_pending,created_at,created_by
                       ) VALUES(?,?,?,?,?)""",
                    (
                        str(a["store"] or ""),
                        str(a["date"] or "")[:10],
                        float(a["pending_manual"] or 0),
                        str(a["updated_at"] or now),
                        str(a["updated_by"] or ""),
                    ),
                )
    except Exception as exc:
        print(f"[V159] Migración pendiente/excedente: {type(exc).__name__}: {exc}", flush=True)

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def _origin_ubicado(con, st, start_exclusive, end_inclusive):
        """Piezas que reducen pendiente: sólo Origen · Ubicado.
        El excedente nunca participa en esta resta.
        """
        try:
            count = con.execute(
                """SELECT COUNT(*) c FROM operation_productivity_timer
                   WHERE store=? AND status='finished' AND operation_type='Origen'
                     AND activity='Ubicado' AND date>? AND date<=?""",
                (st, start_exclusive, end_inclusive),
            ).fetchone()
            if count and int(count["c"] or 0) > 0:
                row = con.execute(
                    """SELECT COALESCE(SUM(pieces),0) p FROM operation_productivity_timer
                       WHERE store=? AND status='finished' AND operation_type='Origen'
                         AND activity='Ubicado' AND date>? AND date<=?""",
                    (st, start_exclusive, end_inclusive),
                ).fetchone()
                return num(row["p"] if row else 0)
        except Exception:
            pass
        try:
            row = con.execute(
                """SELECT COALESCE(SUM(pieces),0) p FROM operation_productivity
                   WHERE store=? AND activity='Ubicado'
                     AND origin IN ('Colgado','Doblado','Jeans','Lencería')
                     AND date>? AND date<=?""",
                (st, start_exclusive, end_inclusive),
            ).fetchone()
            return num(row["p"] if row else 0)
        except Exception:
            return 0.0

    def _pending_at(st, cutoff):
        cutoff = iso_day(cutoff)
        with m.db() as con:
            seed = con.execute(
                """SELECT seed_date,seed_pending FROM operation_pending_seed
                   WHERE store=? AND seed_date<=?""",
                (st, cutoff),
            ).fetchone()
            if not seed:
                return None, "captura_inicial", ""
            seed_day = str(seed["seed_date"] or "")[:10]
            balance = num(seed["seed_pending"])
            row = con.execute(
                """SELECT COALESCE(SUM(arrival),0) a FROM operation_daily_capture
                   WHERE store=? AND origin='Origen' AND date>? AND date<=?""",
                (st, seed_day, cutoff),
            ).fetchone()
            balance += num(row["a"] if row else 0)
            balance -= _origin_ubicado(con, st, seed_day, cutoff)
            return max(balance, 0.0), "automatico", seed_day

    m.operation_pending_at = _pending_at

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
            row = con.execute("SELECT arrival,released,excess,pending_manual,notes,updated_at,updated_by FROM operation_daily_capture WHERE date=? AND store=? AND origin='Origen'", (day, st)).fetchone()
            if row:
                data = dict(row)
            else:
                legacy = con.execute("SELECT COALESCE(SUM(arrival),0) arrival,COALESCE(SUM(released),0) released FROM operation_daily_capture WHERE date=? AND store=? AND origin IN ('Colgado','Doblado')", (day, st)).fetchone()
                data = {"arrival": num(legacy["arrival"]) if legacy else 0, "released": num(legacy["released"]) if legacy else 0, "excess":0, "pending_manual": None, "notes":"", "updated_at":"", "updated_by":""}
            seed = con.execute("SELECT seed_date,seed_pending FROM operation_pending_seed WHERE store=?", (st,)).fetchone()
            status = con.execute("SELECT status,closed_at,closed_by FROM operation_day_status WHERE date=? AND store=?", (day, st)).fetchone()
        auto_pending, pending_source, seed_day = _pending_at(st, day)
        pending_editable = seed is None
        return {
            "date":day,"store":st,"arrival":num(data.get("arrival")),"released":num(data.get("released")),
            "excess":num(data.get("excess")),
            "pending":None if pending_editable else num(auto_pending),
            "pending_editable":pending_editable,"pending_source":pending_source,"pending_seed_date":seed_day,
            "status":dict(status) if status else {"status":"open"},
            "can_capture":str(actor.get("role") or "") in ("superadmin","admin","tienda")
        }

    @m.app.post("/api/operation/origin-capture-v159")
    async def origin_capture_save_v159(request: Request):
        actor = m.require_user(request, ("superadmin","admin","tienda")); body = await request.json(); day = iso_day(body.get("date")); st = scoped(actor, body.get("store"))
        if not st or st == "Compañía":
            raise HTTPException(400, "Selecciona una tienda")
        if not is_open(st, day):
            raise HTTPException(409, "El corte de ese día está cerrado")
        arrival = max(num(body.get("arrival")), 0)
        released = max(num(body.get("released")), 0)
        excess = max(num(body.get("excess")), 0)
        now = datetime.now(MX).isoformat(timespec="seconds")
        user = str(actor.get("username") or "")
        seed_created = False
        with m.db() as con:
            seed = con.execute("SELECT seed_date,seed_pending FROM operation_pending_seed WHERE store=?", (st,)).fetchone()
            if not seed:
                raw_pending = body.get("pending")
                if raw_pending is None or str(raw_pending).strip()=="":
                    raise HTTPException(400, "Captura las piezas pendientes iniciales; sólo se solicitarán esta primera vez")
                pending_seed = max(num(raw_pending), 0)
                con.execute(
                    """INSERT INTO operation_pending_seed(store,seed_date,seed_pending,created_at,created_by)
                       VALUES(?,?,?,?,?)""",
                    (st, day, pending_seed, now, user),
                )
                seed_created = True
            con.execute(
                """INSERT INTO operation_daily_capture(
                     date,store,origin,arrival,released,pending_manual,excess,notes,updated_at,updated_by
                   ) VALUES(?,?,?,?,?,?,?,'',?,?)
                   ON CONFLICT(date,store,origin) DO UPDATE SET
                     arrival=excluded.arrival,released=excluded.released,excess=excluded.excess,
                     pending_manual=CASE
                       WHEN operation_daily_capture.pending_manual IS NULL AND ?=1
                       THEN excluded.pending_manual
                       ELSE operation_daily_capture.pending_manual
                     END,
                     updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
                (
                    day, st, "Origen", arrival, released,
                    max(num(body.get("pending")),0) if seed_created else None,
                    excess, now, user, 1 if seed_created else 0,
                ),
            )
            try:
                con.execute(
                    "INSERT INTO operation_audit(entity,entity_key,action,before_json,after_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",
                    (
                        "daily_capture", f"{day}|{st}|Origen", "upsert_v287", "{}",
                        f'{{"arrival":{arrival},"released":{released},"excess":{excess},"seed_created":{str(seed_created).lower()}}}',
                        now, user,
                    ),
                )
            except Exception:
                pass
        pending, pending_source, seed_day = _pending_at(st, day)
        return {
            "ok":True,"message":"Captura diaria guardada","arrival":arrival,"released":released,
            "excess":excess,"pending":num(pending),"pending_source":pending_source,
            "pending_editable":False,"pending_seed_date":seed_day
        }

    @m.app.get("/api/operation/staff-needed-v159")
    def staff_needed_v159(request: Request, period_type: str="day", period_value: str="", store: str="Compañía"):
        """Personal requerido del módulo Operación, sólo para Origen.

        El último pendiente capturado es autoritativo y se actualiza únicamente
        con movimientos posteriores. C&M no participa en esta vista.
        """
        actor = m.require_user(request)
        start, end = bounds(period_type, period_value)
        stores, selected = stores_for(actor, store)
        ss, es = start.isoformat(), end.isoformat()
        standard = stds()
        if not stores:
            return {"store":selected,"total_required":0,"rows":[],"formula":""}

        ph = ",".join("?" for _ in stores)
        with m.db() as con:
            caps = [dict(r) for r in con.execute(
                f"""SELECT date,store,arrival,pending_manual
                    FROM operation_daily_capture
                    WHERE origin='Origen' AND date<=? AND store IN ({ph})
                    ORDER BY date""",
                (es,*stores)
            ).fetchall()]
            prod = [dict(r) for r in con.execute(
                f"""SELECT date,store,origin,pieces
                    FROM operation_productivity
                    WHERE origin IN ('Colgado','Doblado','Jeans','Lencería')
                      AND date<=? AND store IN ({ph})
                    ORDER BY date""",
                (es,*stores)
            ).fetchall()]
            try:
                active = {
                    str(r["store"]):int(r["c"])
                    for r in con.execute(
                        f"""SELECT store,COUNT(*) c
                            FROM users
                            WHERE role IN ('colaborador','colaborador_operativo')
                              AND active=1 AND store IN ({ph})
                            GROUP BY store""",
                        tuple(stores)
                    ).fetchall()
                }
            except Exception:
                active = {}

        def family(origin):
            org=str(origin or "")
            if org in ("Colgado","Lencería"):
                return "Colgado"
            if org in ("Doblado","Jeans"):
                return "Doblado"
            return org

        def closing_pending(st):
            value, source, _seed_day = _pending_at(st, es)
            if value is None:
                return 0.0, "captura_inicial"
            return value, source

        rows=[]
        for st in stores:
            origin_pending,pending_source=closing_pending(st)

            # Estándar ponderado según la mezcla real del periodo. Lencería
            # usa estándar Colgado y Jeans usa estándar Doblado.
            colgado=sum(
                num(r.get("pieces")) for r in prod
                if str(r.get("store") or "")==st and ss<=str(r.get("date") or "")<=es
                and family(r.get("origin"))=="Colgado"
            )
            doblado=sum(
                num(r.get("pieces")) for r in prod
                if str(r.get("store") or "")==st and ss<=str(r.get("date") or "")<=es
                and family(r.get("origin"))=="Doblado"
            )
            mix=colgado+doblado
            origin_std=(
                (colgado*standard["Colgado"]+doblado*standard["Doblado"])/mix
                if mix>0 else (standard["Colgado"]+standard["Doblado"])/2
            )
            req_origin=int(math.ceil(origin_pending/origin_std)) if origin_pending>0 and origin_std>0 else 0
            current=int(active.get(st,0))
            gap=max(req_origin-current,0)

            rows.append({
                "store":st,
                "origin_pending":origin_pending,
                "pending_total":origin_pending,
                "origin_standard":origin_std,
                "origin_required":req_origin,
                "required":req_origin,
                "active_collaborators":current,
                "gap":gap,
                "pending_source":pending_source,
            })

        rows.sort(key=lambda x:(-x["required"],-x["pending_total"],x["store"]))
        total_required=sum(r["required"] for r in rows)
        total_active=sum(r["active_collaborators"] for r in rows)
        total_gap=sum(r["gap"] for r in rows)
        return {
            "store":selected,
            "start_date":ss,
            "end_date":es,
            "total_required":total_required,
            "total_active":total_active,
            "total_gap":total_gap,
            "rows":rows,
            "formula":"Origen = redondeo superior(pendiente vigente / estándar ponderado Colgado-Doblado).",
        }

    css=r'''<style id="v159-operation-css">
.v159-staff{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;margin:9px 0}.v159-staff h3{margin:0 0 7px;color:var(--navy);font-size:12px}.v159-staff-note{font-size:8px;color:#667085;line-height:1.45;margin-top:6px}.v159-pending-field,.v159-excess-field{min-width:0}.v159-pending-field label,.v159-excess-field label{display:block;font-size:8px;font-weight:950;color:#667085;text-transform:uppercase;margin-bottom:5px}.v159-pending-field input,.v159-excess-field input{width:100%;min-height:44px;border:1px solid #ccd6e2;border-radius:10px;background:#fff;color:var(--text);padding:9px 10px;font-size:16px}.v159-pending-field input:disabled{background:#f2f7fb;color:#123f73;font-weight:900}.v159-auto-note{display:block;margin-top:4px;color:#5f748a;font-size:7px;font-weight:750}.v159-excess-field input{border-color:#9cd8bd;background:#f4fff9}.v159-excess-field label{color:#087a4b}@media(max-width:900px){.v159-staff{padding:10px}.v159-pending-field input,.v159-excess-field input{font-size:16px}}</style>'''

    js=r'''<script id="v159-operation-js">
(function(){
if(window.__V159_OPERATION)return;window.__V159_OPERATION=true;
const OP='Operación',num=v=>Number(v||0),fmt=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:0}),f1=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1}),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function activeTab(){const b=document.querySelector('#v200OperationTabs [data-v200-op].active')||document.querySelector('#v200OperationTabs [data-v200-op][aria-selected="true"]');if(b?.dataset?.v200Op)return b.dataset.v200Op;const a=document.querySelector('.v125-tabs .active');const t=(a?.textContent||'').toLowerCase();if(t.includes('captura diaria'))return'daily';if(t.includes('resumen'))return'summary';return''}
async function decorateDaily(){
 if(activeTab()!=='daily')return;const store=document.getElementById('operStoreSelect')?.value||'',day=document.getElementById('operPeriodSelect')?.value||'';if(!store||store==='Compañía'||!day)return;
 let data;try{data=await api('/api/operation/origin-capture-v159?'+new URLSearchParams({date:day,store}),{timeoutMs:60000})}catch(e){console.warn('[V159] pendiente diario',e);return}
 if(!document.getElementById('v159OriginPending')){
   const rel=document.getElementById('v125OriginReleased');const host=rel?.closest('.v125-field')||rel?.parentElement;
   if(host){
     const w=document.createElement('div');w.className='v159-pending-field';
     w.innerHTML='<label id="v159PendingLabel">Origen · Piezas pendientes</label><input id="v159OriginPending" type="number" min="0" inputmode="numeric" value="0"><small id="v159PendingNote" class="v159-auto-note"></small>';
     host.insertAdjacentElement('afterend',w);
     const x=document.createElement('div');x.className='v159-excess-field';
     x.innerHTML='<label>Origen · Excedente</label><input id="v159OriginExcess" type="number" min="0" inputmode="numeric" value="0"><small class="v159-auto-note">Suma al avance productivo; no modifica el pendiente.</small>';
     w.insertAdjacentElement('afterend',x);
   }
 }
 const inp=document.getElementById('v159OriginPending'),lab=document.getElementById('v159PendingLabel'),note=document.getElementById('v159PendingNote'),exc=document.getElementById('v159OriginExcess');
 const isClosed=String(data.status?.status||'open')==='closed';
 if(inp){inp.value=data.pending==null?'0':String(data.pending);inp.disabled=!data.pending_editable||!data.can_capture||isClosed}
 if(lab)lab.textContent=data.pending_editable?'Origen · Piezas pendientes iniciales':'Origen · Pendiente automático';
 if(note)note.textContent=data.pending_editable?'Se captura sólo esta primera vez.':('Calculado desde '+(data.pending_seed_date||'la captura inicial')+'; ya no requiere captura manual.');
 if(exc){exc.value=String(data.excess||0);exc.disabled=!data.can_capture||isClosed}
 const old=document.getElementById('v125SaveOrigin');if(old&&!old.dataset.v159){const b=old.cloneNode(true);b.dataset.v159='1';old.replaceWith(b);b.addEventListener('click',async()=>{const msg=document.getElementById('v125DailyMsg');try{const p=document.getElementById('v159OriginPending');const r=await api('/api/operation/origin-capture-v159',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:document.getElementById('operPeriodSelect')?.value||day,store:document.getElementById('operStoreSelect')?.value||store,arrival:num(document.getElementById('v125OriginArrival')?.value),released:num(document.getElementById('v125OriginReleased')?.value),pending:data.pending_editable?num(p?.value):null,excess:num(document.getElementById('v159OriginExcess')?.value)})});if(msg){msg.className='v125-msg ok';msg.textContent=r.message+' · Pendiente actual: '+Math.round(num(r.pending)).toLocaleString('es-MX')}setTimeout(()=>window.renderOperativoView(OP,true),300)}catch(e){if(msg){msg.className='v125-msg err';msg.textContent=e.message}else alert(e.message)}})}
}
function findPanel(title){return [...document.querySelectorAll('.v149-panel')].find(p=>(p.querySelector('h3')?.textContent||'').trim()===title)}
async function decorateSummary(){
 if(activeTab()!=='summary')return;const store=document.getElementById('operStoreSelect')?.value||'Compañía',ptype=(document.getElementById('operPeriodMode')?.value||'day'),pval=document.getElementById('operPeriodSelect')?.value||'';let d;try{d=await api('/api/operation/staff-needed-v159?'+new URLSearchParams({period_type:ptype,period_value:pval,store}),{timeoutMs:180000})}catch(e){console.warn('[V159] personal requerido',e);return}
 const k=document.querySelector('.v149-kpis');if(k&&!k.querySelector('[data-v159-staff-kpi]')){const x=document.createElement('div');x.className='v149-kpi';x.dataset.v159StaffKpi='1';x.style.setProperty('--k','#0f766e');const row=d.rows?.[0],sub=store==='Compañía'?`Brecha total: ${fmt(d.total_gap)}`:`Origen ${fmt(row?.origin_required)}`;x.innerHTML=`<small>Colaboradores necesarios</small><b>${fmt(d.total_required)}</b><span>${sub}</span>`;k.appendChild(x)}
 const panel=findPanel('Desempeño por tienda');const table=panel?.querySelector('table');if(table&&!table.dataset.v159){table.dataset.v159='1';const th=document.createElement('th');th.textContent='Colab. necesarios';table.querySelector('thead tr')?.appendChild(th);const map=new Map((d.rows||[]).map(r=>[r.store,r]));table.querySelectorAll('tbody tr').forEach(tr=>{const name=(tr.cells?.[0]?.textContent||'').trim();const r=map.get(name);const td=document.createElement('td');td.innerHTML=r?`<b>${fmt(r.required)}</b><div style="font-size:7px;color:#667085">Actual ${fmt(r.active_collaborators)} · Faltan ${fmt(r.gap)}</div>`:'—';tr.appendChild(td)})}
 if(panel&&!document.getElementById('v159StaffDetail')){const box=document.createElement('div');box.id='v159StaffDetail';box.className='v159-staff';box.innerHTML=`<h3>Personal requerido · ${esc(store)}</h3><div class="tablewrap"><table class="table"><thead><tr><th>Tienda</th><th>Pendiente Origen</th><th>Necesarios</th><th>Activos</th><th>Brecha</th></tr></thead><tbody>${(d.rows||[]).map(r=>`<tr><td><b>${esc(r.store)}</b></td><td>${fmt(r.origin_pending)} <small>(${esc(r.pending_source)})</small></td><td><b>${fmt(r.required)}</b></td><td>${fmt(r.active_collaborators)}</td><td>${fmt(r.gap)}</td></tr>`).join('')}</tbody></table></div><div class="v159-staff-note">${esc(d.formula||'')}</div>`;panel.insertAdjacentElement('afterend',box)}
}
async function decorate(){if(String(window.MAIN||'').toLowerCase()!=='operation'&&window.OP_VIEW!==OP)return;await decorateDaily();await decorateSummary()}
const previous=window.renderOperativoView;window.renderOperativoView=async function(name,force=false){const out=await previous(name,force);if(name===OP){await decorate();setTimeout(decorate,120)}return out};
document.addEventListener('click',e=>{if(e.target.closest?.('[data-main="operation"],.v125-tab,#operPeriodApply'))setTimeout(decorate,350)},true);document.addEventListener('change',e=>{if(e.target?.matches?.('#operStoreSelect,#operPeriodMode,#operPeriodSelect'))setTimeout(decorate,250)},true);setTimeout(decorate,600);console.info('[V159.1] Operación Origen-only: personal requerido + pendiente capturado activos.');
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
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V159.1"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V159] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V159_OPERATION_STORE_STAFF_PENDING=True
    print("[V159.1] Operación: sólo Origen, personal requerido y pendiente capturado activos.",flush=True)
