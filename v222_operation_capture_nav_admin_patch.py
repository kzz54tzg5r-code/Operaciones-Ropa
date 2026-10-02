"""V222 · Captura Operación por tipo/actividad/área + navegación consolidada.

Incluye:
- Cargar productividad con Tipo de operación: Origen / Resurtido.
- Origen: Clasificado / Acondicionado / Ubicado.
- Resurtido: Motivo Excedente / Bodega y Pizca / Acondicionado / Ubicado.
- Captura de piezas en tabla para Colgado, Doblado, Jeans y Lencería.
- Compatibilidad con ranking/summary mediante registros por área.
- Flechas laterales cuando una barra de pestañas requiere desplazamiento.
- Limpieza defensiva de iconos duplicados.
- Visibilidad de pestañas compacta y agrupada por reporte.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V222_OPERATION_CAPTURE_NAV_ADMIN", False):
        return

    AREAS = ("Colgado", "Doblado", "Jeans", "Lencería")
    ORIGIN_ACTIVITIES = ("Clasificado", "Acondicionado", "Ubicado")
    RESUPPLY_ACTIVITIES = ("Pizca", "Acondicionado", "Ubicado")
    RESUPPLY_REASONS = ("Excedente", "Bodega")

    # La configuración de pestañas ahora distingue los tres reportes.
    for key, label in (
        ("operation.summary", "Resumen"),
        ("operation.daily", "Captura diaria"),
        ("operation.capture", "Cargar productividad"),
        ("operation.productivity", "Productividad"),
        ("operation.standards", "Estándares Operativos"),
    ):
        m.REPORT_TABS.setdefault(key, label)

    with m.db() as con:
        cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(operation_productivity_timer)").fetchall()}
        for col, decl in (
            ("operation_type", "TEXT DEFAULT ''"),
            ("supply_reason", "TEXT DEFAULT ''"),
            ("capture_group", "TEXT DEFAULT ''"),
        ):
            if col not in cols:
                con.execute("ALTER TABLE operation_productivity_timer ADD COLUMN %s %s" % (col, decl))
        con.execute("CREATE INDEX IF NOT EXISTS ix_op_timer_capture_group ON operation_productivity_timer(capture_group)")

    def _profile(actor):
        with m.db() as con:
            row = con.execute(
                "SELECT id,username,store,full_name,employee_no FROM users WHERE id=? AND active=1",
                (actor.get("id"),),
            ).fetchone()
        if not row:
            raise HTTPException(401, "Sesión requerida")
        return dict(row)

    def _resolve_store(actor, requested=""):
        profile = _profile(actor)
        role = str(actor.get("role") or "")
        assigned = str(actor.get("store") or profile.get("store") or "").strip()
        if role in ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria"):
            if not assigned:
                raise HTTPException(409, "Tu usuario no tiene tienda asignada")
            return assigned
        stores = list(m.store_names(True) or [])
        active = {m.login_key(x): x for x in stores}
        req = str(requested or "").strip()
        if req and req != "Compañía":
            chosen = active.get(m.login_key(req))
            if chosen:
                return chosen
        if assigned:
            chosen = active.get(m.login_key(assigned))
            if chosen:
                return chosen
        if stores:
            return stores[0]
        raise HTTPException(409, "No hay tiendas activas")

    def _today():
        return datetime.now(MX).date().isoformat()

    def _parse_dt(value):
        try:
            return datetime.fromisoformat(str(value or ""))
        except Exception:
            return None

    def _clean_capture(operation_type, supply_reason, activity):
        op = str(operation_type or "").strip().title()
        if op not in ("Origen", "Resurtido"):
            raise HTTPException(400, "Selecciona Tipo de operación: Origen o Resurtido")
        act = str(activity or "").strip()
        allowed = ORIGIN_ACTIVITIES if op == "Origen" else RESUPPLY_ACTIVITIES
        if act not in allowed:
            raise HTTPException(400, "Selecciona una actividad válida")
        reason = str(supply_reason or "").strip().title()
        if op == "Resurtido":
            if reason not in RESUPPLY_REASONS:
                raise HTTPException(400, "Selecciona Motivo Surtido: Excedente o Bodega")
        else:
            reason = ""
        return op, reason, act

    @m.app.get("/api/operation-capture-v222/meta")
    def v222_capture_meta(request: Request, store: str = ""):
        actor = m.require_user(request)
        profile = _profile(actor)
        return {
            "date": _today(),
            "store": _resolve_store(actor, store),
            "employee_name": str(profile.get("full_name") or profile.get("username") or ""),
            "employee_no": str(profile.get("employee_no") or ""),
            "profile_required": not bool(
                str(profile.get("full_name") or "").strip()
                and str(profile.get("employee_no") or "").strip()
            ),
            "operation_types": ["Origen", "Resurtido"],
            "origin_activities": list(ORIGIN_ACTIVITIES),
            "resupply_activities": list(RESUPPLY_ACTIVITIES),
            "resupply_reasons": list(RESUPPLY_REASONS),
            "areas": list(AREAS),
        }

    @m.app.get("/api/operation-capture-v222/active")
    def v222_capture_active(request: Request):
        actor = m.require_user(request)
        with m.db() as con:
            row = con.execute(
                "SELECT * FROM operation_productivity_timer "
                "WHERE created_by=? AND status='active' ORDER BY id DESC LIMIT 1",
                (str(actor.get("username") or ""),),
            ).fetchone()
        item = dict(row) if row else None
        if item:
            item["operation_type"] = str(item.get("operation_type") or "Origen")
            item["supply_reason"] = str(item.get("supply_reason") or "")
        return {"item": item}

    @m.app.post("/api/operation-capture-v222/start")
    async def v222_capture_start(request: Request):
        actor = m.require_user(
            request, ("superadmin", "admin", "tienda", "colaborador", "colaborador_operativo")
        )
        body = await request.json()
        op, reason, activity = _clean_capture(
            body.get("operation_type"), body.get("supply_reason"), body.get("activity")
        )
        profile = _profile(actor)
        full_name = str(profile.get("full_name") or "").strip()
        employee_no = str(profile.get("employee_no") or "").strip()
        if not full_name or not employee_no:
            raise HTTPException(409, "Completa tu nombre completo y nómina antes de registrar productividad")
        store = _resolve_store(actor, body.get("store"))
        now_dt = datetime.now(MX)
        now = now_dt.isoformat(timespec="seconds")
        day = now_dt.date().isoformat()
        created_by = str(actor.get("username") or "")
        group_id = "v222-" + uuid.uuid4().hex
        with m.db() as con:
            running = con.execute(
                "SELECT id FROM operation_productivity_timer WHERE created_by=? AND status='active' LIMIT 1",
                (created_by,),
            ).fetchone()
            if running:
                raise HTTPException(409, "Ya tienes una actividad en curso. Finalízala antes de iniciar otra.")
            cur = con.execute(
                """INSERT INTO operation_productivity_timer(
                    date,store,user_id,employee_no,employee_name,area,activity,pieces,
                    started_at,ended_at,duration_seconds,status,created_by,created_at,updated_at,
                    operation_type,supply_reason,capture_group
                ) VALUES(?,?,?,?,?,'Pendiente',?,0,?,'',0,'active',?,?,?,?,?,?)""",
                (
                    day, store, int(profile.get("id") or actor.get("id") or 0),
                    employee_no, full_name, activity, now, created_by, now, now,
                    op, reason, group_id,
                ),
            )
            rid = int(cur.lastrowid)
        return {
            "ok": True, "id": rid, "capture_group": group_id, "started_at": now,
            "date": day, "store": store, "operation_type": op,
            "supply_reason": reason, "activity": activity, "message": "Tiempo iniciado",
        }

    @m.app.post("/api/operation-capture-v222/{record_id}/finish")
    async def v222_capture_finish(record_id: int, request: Request):
        actor = m.require_user(
            request, ("superadmin", "admin", "tienda", "colaborador", "colaborador_operativo")
        )
        body = await request.json()
        raw = body.get("pieces_by_area") or {}
        pieces_by_area = {}
        for area in AREAS:
            try:
                value = max(float(raw.get(area) or 0), 0.0)
            except Exception:
                raise HTTPException(400, "Revisa las piezas capturadas en " + area)
            if value > 0:
                pieces_by_area[area] = value
        if not pieces_by_area:
            raise HTTPException(400, "Captura piezas en al menos un área")

        now_dt = datetime.now(MX)
        now = now_dt.isoformat(timespec="seconds")
        created_by = str(actor.get("username") or "")
        created_ids = []

        with m.db() as con:
            row = con.execute("SELECT * FROM operation_productivity_timer WHERE id=?", (record_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Registro no encontrado")
            data = dict(row)
            role = str(actor.get("role") or "")
            if role not in ("superadmin", "admin") and str(data.get("created_by") or "") != created_by:
                raise HTTPException(403, "No puedes finalizar este registro")
            if str(data.get("status") or "") != "active":
                raise HTTPException(409, "El registro ya fue finalizado")

            op = str(data.get("operation_type") or body.get("operation_type") or "Origen")
            reason = str(data.get("supply_reason") or body.get("supply_reason") or "")
            op, reason, activity = _clean_capture(op, reason, data.get("activity") or body.get("activity"))
            start = _parse_dt(data.get("started_at"))
            duration = max(int((now_dt - start).total_seconds()), 0) if start else 0
            group_id = str(data.get("capture_group") or "") or ("v222-" + uuid.uuid4().hex)
            ordered = [(a, pieces_by_area[a]) for a in AREAS if a in pieces_by_area]
            first_area, first_pieces = ordered[0]

            con.execute(
                """UPDATE operation_productivity_timer
                   SET area=?,activity=?,pieces=?,ended_at=?,duration_seconds=?,status='finished',
                       updated_at=?,operation_type=?,supply_reason=?,capture_group=?
                   WHERE id=?""",
                (first_area, activity, first_pieces, now, duration, now, op, reason, group_id, record_id),
            )
            created_ids.append(record_id)

            for area, pieces in ordered[1:]:
                cur = con.execute(
                    """INSERT INTO operation_productivity_timer(
                        date,store,user_id,employee_no,employee_name,area,activity,pieces,
                        started_at,ended_at,duration_seconds,status,created_by,created_at,updated_at,
                        operation_type,supply_reason,capture_group
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,0,'finished',?,?,?,?,?,?)""",
                    (
                        data.get("date"), data.get("store"), data.get("user_id"),
                        data.get("employee_no"), data.get("employee_name"), area, activity, pieces,
                        data.get("started_at"), now, data.get("created_by"), data.get("created_at") or data.get("started_at"),
                        now, op, reason, group_id,
                    ),
                )
                created_ids.append(int(cur.lastrowid))

            # Fuente histórica usada por Resumen de Operación. Guardamos las
            # cuatro áreas con su nombre real; V149 agrupa Jeans->Doblado y
            # Lencería->Colgado únicamente para el estándar.
            for area, pieces in ordered:
                exists = con.execute(
                    """SELECT id FROM operation_productivity
                       WHERE date=? AND store=? AND employee_no=? AND origin=? AND activity=?
                         AND created_at=? AND pieces=? LIMIT 1""",
                    (
                        data.get("date"), data.get("store"), data.get("employee_no"),
                        area, activity, data.get("started_at"), pieces,
                    ),
                ).fetchone()
                if not exists:
                    con.execute(
                        """INSERT INTO operation_productivity(
                            date,store,user_id,employee_no,employee_name,origin,activity,pieces,
                            created_at,created_by,updated_at,updated_by
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            data.get("date"), data.get("store"), data.get("user_id"),
                            data.get("employee_no"), data.get("employee_name"), area, activity, pieces,
                            data.get("started_at"), data.get("created_by"), now, created_by,
                        ),
                    )

        return {
            "ok": True,
            "record_ids": created_ids,
            "pieces_by_area": pieces_by_area,
            "total_pieces": sum(pieces_by_area.values()),
            "duration_seconds": duration,
            "message": "Tiempo finalizado y productividad guardada por área",
        }

    @m.app.get("/api/operation-capture-v222/history")
    def v222_capture_history(request: Request, date: str = "", store: str = ""):
        actor = m.require_user(request)
        profile = _profile(actor)
        day = str(date or _today())[:10]
        role = str(actor.get("role") or "")
        where = ["date=?", "status='finished'"]
        params = [day]
        if role in ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria"):
            where.append("store=?")
            params.append(str(profile.get("store") or ""))
        elif store and store != "Compañía":
            where.append("store=?")
            params.append(store)
        if role in ("colaborador", "colaborador_operativo"):
            where.append("created_by=?")
            params.append(str(actor.get("username") or ""))

        with m.db() as con:
            rows = [
                dict(r) for r in con.execute(
                    "SELECT * FROM operation_productivity_timer WHERE " + " AND ".join(where)
                    + " ORDER BY started_at DESC,id ASC LIMIT 240",
                    tuple(params),
                ).fetchall()
            ]

        grouped = {}
        order = []
        for row in rows:
            gid = str(row.get("capture_group") or "") or ("legacy-" + str(row.get("id")))
            if gid not in grouped:
                grouped[gid] = {
                    "capture_group": gid,
                    "employee_name": str(row.get("employee_name") or ""),
                    "employee_no": str(row.get("employee_no") or ""),
                    "store": str(row.get("store") or ""),
                    "operation_type": str(row.get("operation_type") or "Origen"),
                    "supply_reason": str(row.get("supply_reason") or ""),
                    "activity": str(row.get("activity") or ""),
                    "started_at": str(row.get("started_at") or ""),
                    "duration_seconds": 0,
                    "pieces_by_area": {a: 0.0 for a in AREAS},
                    "total_pieces": 0.0,
                }
                order.append(gid)
            g = grouped[gid]
            area = str(row.get("area") or "")
            try:
                pieces = max(float(row.get("pieces") or 0), 0.0)
            except Exception:
                pieces = 0.0
            if area in AREAS:
                g["pieces_by_area"][area] += pieces
            g["total_pieces"] += pieces
            try:
                g["duration_seconds"] = max(g["duration_seconds"], int(float(row.get("duration_seconds") or 0)))
            except Exception:
                pass
        return {"items": [grouped[x] for x in order[:80]], "areas": list(AREAS)}

    css = r"""<style id="v222-operation-capture-nav-admin-css">
/* ---------- Captura Operación ---------- */
.v222-capture-card{background:#fff;border:1px solid #d6e3f0;border-radius:17px;padding:14px;margin:8px 0;box-shadow:0 6px 20px rgba(25,72,118,.06)}
.v222-capture-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}
.v222-capture-head h3{margin:0;color:#123f73;font-size:15px;font-weight:950}
.v222-note{margin-top:4px;color:#71849a;font-size:8px;line-height:1.45}
.v222-timer{min-width:145px;padding:9px 12px;border-radius:12px;background:#edf5ff;color:#123f73;font-size:27px;font-weight:950;text-align:center;font-variant-numeric:tabular-nums}
.v222-meta{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.v222-meta span{padding:5px 8px;border-radius:999px;background:#f2f6fb;color:#526d88;font-size:8px;font-weight:800}
.v222-section{margin-top:12px}
.v222-section>label{display:block;margin-bottom:6px;color:#526b84;font-size:8px;font-weight:950;text-transform:uppercase;letter-spacing:.04em}
.v222-choice{display:flex;gap:7px;flex-wrap:wrap}
.v222-choice button{min-height:38px;padding:7px 14px;border:1px solid #d3e0ed;border-radius:11px;background:#f8fbff;color:#315677;font-size:10px;font-weight:900;cursor:pointer}
.v222-choice button.selected{border-color:#0b6cc5;background:linear-gradient(135deg,#0d4f8b,#0b82ed);color:#fff;box-shadow:0 7px 16px rgba(13,93,167,.16)}
.v222-choice button:disabled{cursor:default;opacity:.75}
.v222-area-wrap{margin-top:12px;border:1px solid #d9e5f1;border-radius:13px;overflow:hidden}
.v222-area-table{width:100%;border-collapse:collapse}
.v222-area-table th{padding:9px 11px;background:#124d84;color:#fff;text-align:left;font-size:9px}
.v222-area-table td{padding:8px 11px;border-bottom:1px solid #e8eef5;color:#264b70;font-size:10px}
.v222-area-table tr:last-child td{border-bottom:0}
.v222-area-table td:first-child{font-weight:900}
.v222-area-table input{width:100%;height:38px;border:1px solid #ccd9e7;border-radius:9px;padding:6px 9px;background:#fff;color:#123f73;font-size:13px;font-weight:900}
.v222-total-row{background:#f2f7fd}
.v222-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px}
.v222-actions button{min-width:110px;min-height:42px;border:0;border-radius:11px;color:#fff;font-weight:950}
.v222-start{background:#0aa44b}.v222-finish{background:#e85c64}
.v222-actions button:disabled{opacity:.45}
.v222-msg{font-size:9px;font-weight:800;color:#526b84}
.v222-history-wrap{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #d9e5f1;border-radius:13px}
.v222-history{width:100%;min-width:900px;border-collapse:collapse}
.v222-history th{padding:8px;background:#124d84;color:#fff;text-align:left;font-size:8px;white-space:nowrap}
.v222-history td{padding:8px;border-bottom:1px solid #e8eef5;color:#294b70;font-size:8px;white-space:nowrap}

/* ---------- Flechas de navegación ---------- */
.v222-tab-stage{display:grid;grid-template-columns:30px minmax(0,1fr) 30px;align-items:center;gap:5px;width:100%;min-width:0}
.v222-tab-stage.v222-stage-hidden{display:none!important}
.v222-tab-arrow{width:30px;height:42px;border:1px solid #d7e3ef;border-radius:12px;background:#fff;color:#0b67bd;display:grid;place-items:center;font-size:22px;font-weight:900;box-shadow:0 4px 12px rgba(25,72,118,.06);cursor:pointer}
.v222-tab-arrow:disabled{opacity:.18;cursor:default}
.v222-tab-stage.v222-no-scroll .v222-tab-arrow{visibility:hidden;pointer-events:none}
.v222-tab-stage>:is(#operativoNav,#analysisNav,#v200OperationTabs){min-width:0!important;margin-left:0!important;margin-right:0!important}

/* ---------- Visibilidad agrupada y compacta ---------- */
#page-users.v219-users #tabVisibilityOptions.v222-grouped{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px!important;align-items:start}
.v222-vis-group{min-width:0;border:1px solid #dce7f1;border-radius:13px;background:#fbfdff;padding:8px}
.v222-vis-title{margin:0 0 5px;padding:2px 3px 7px;border-bottom:1px solid #e8eef5;color:#133f70;font-size:11px;font-weight:950}
#page-users.v219-users .v222-vis-group label.field{padding:5px 2px!important;gap:7px!important}
#page-users.v219-users .v222-vis-group .v219-tab-icon{width:27px!important;height:27px!important;min-width:27px!important;border-radius:8px!important}
#page-users.v219-users .v222-vis-group .v219-tab-icon svg{width:15px!important;height:15px!important}
#page-users.v219-users .v222-vis-group label.field>span:not(.v219-tab-icon){font-size:9px!important}
#page-users.v219-users .v222-vis-group input[type="checkbox"][data-tab-setting]{flex-basis:32px!important;width:32px!important;min-width:32px!important;height:18px!important}
#page-users.v219-users .v222-vis-group input[type="checkbox"][data-tab-setting]::after{top:2px!important;left:2px!important;width:14px!important;height:14px!important}
#page-users.v219-users .v222-vis-group input[type="checkbox"][data-tab-setting]:checked::after{transform:translateX(14px)!important}

@media(max-width:900px){
 .v222-capture-card{padding:11px}
 .v222-timer{font-size:23px;min-width:130px}
 .v222-choice{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}
 .v222-choice.v222-two{grid-template-columns:repeat(2,minmax(0,1fr))}
 .v222-choice button{min-width:0;padding:6px 5px;font-size:9px}
 .v222-tab-stage{grid-template-columns:26px minmax(0,1fr) 26px;gap:3px}
 .v222-tab-arrow{width:26px;height:38px;border-radius:10px;font-size:19px}
 #page-users.v219-users #tabVisibilityOptions.v222-grouped{grid-template-columns:1fr;gap:7px!important}
}
</style>"""

    js = r"""<script id="v222-operation-capture-nav-admin-js">
(function(){
  if(window.__V222_OPERATION_CAPTURE_NAV_ADMIN)return;
  window.__V222_OPERATION_CAPTURE_NAV_ADMIN=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const n=Number(v||0);return Number.isFinite(n)?Math.max(n,0):0};
  const hms=sec=>{sec=Math.max(0,Math.floor(Number(sec)||0));const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;return[h,m,s].map(x=>String(x).padStart(2,'0')).join(':')};
  let captureState={operation_type:'Origen',supply_reason:'Excedente',activity:'Clasificado'};
  let timerHandle=0;
  let timerStartedAt='';

  async function A(url,opt={}){
    if(typeof api==='function')return api(url,opt);
    const r=await fetch(url,{credentials:'same-origin',...opt});
    const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch(_){}
    if(!r.ok)throw new Error(d.detail||d.message||raw||('HTTP '+r.status));
    return d;
  }

  function moduleName(){
    const active=q('.side [data-main].active')||q('#mobileMainNav [data-main].active');
    return String(active?.dataset?.main||document.body.dataset.v163Module||'').toLowerCase();
  }
  function isOperation(){return moduleName()==='operation'}

  function selectedStore(){
    const v=q('#operStoreSelect')?.value||'';
    return v&&v!=='Compañía'?v:'';
  }

  function setCaptureTabActive(){
    try{window.V149_OPERATION_TAB='capture';window.V125_OPERATION_TAB='capture'}catch(_){}
    qa('#v200OperationTabs [data-v200-op]').forEach(btn=>{
      const on=btn.dataset.v200Op==='capture';
      btn.classList.toggle('active',on);
      btn.setAttribute('aria-selected',on?'true':'false');
    });
    const bar=q('#operativoPeriodBar');
    if(bar){bar.classList.add('hidden');bar.style.display='none'}
  }

  function startClock(started){
    clearInterval(timerHandle);
    timerStartedAt=started||'';
    const tick=()=>{
      const el=q('#v222Timer');if(!el)return;
      if(!timerStartedAt){el.textContent='00:00:00';return}
      const ms=new Date(timerStartedAt).getTime();
      el.textContent=hms((Date.now()-ms)/1000);
    };
    tick();
    if(timerStartedAt)timerHandle=setInterval(tick,1000);
  }

  function areasFromInputs(){
    const out={};
    qa('[data-v222-area]').forEach(i=>out[i.dataset.v222Area]=num(i.value));
    return out;
  }

  function updateAreaTotal(){
    const total=Object.values(areasFromInputs()).reduce((a,b)=>a+b,0);
    const el=q('#v222AreaTotal');if(el)el.textContent=Math.round(total).toLocaleString('es-MX');
  }

  function activityOptions(type,meta){
    return type==='Resurtido'?(meta.resupply_activities||['Pizca','Acondicionado','Ubicado']):(meta.origin_activities||['Clasificado','Acondicionado','Ubicado']);
  }

  function paintCapture(meta,active,history){
    const host=q('#operativoDynamicContent');if(!host)return;
    const running=!!active;
    const type=running?String(active.operation_type||'Origen'):captureState.operation_type;
    const reasons=meta.resupply_reasons||['Excedente','Bodega'];
    let reason=running?String(active.supply_reason||''):captureState.supply_reason;
    if(type==='Resurtido'&&!reasons.includes(reason))reason=reasons[0]||'Excedente';
    const acts=activityOptions(type,meta);
    let activity=running?String(active.activity||''):captureState.activity;
    if(!acts.includes(activity))activity=acts[0]||'Acondicionado';
    captureState={operation_type:type,supply_reason:reason,activity};

    const typeButtons=['Origen','Resurtido'].map(x=>'<button type="button" data-v222-type="'+x+'" class="'+(x===type?'selected':'')+'" '+(running?'disabled':'')+'>'+x+'</button>').join('');
    const reasonHtml=type==='Resurtido'
      ?'<div class="v222-section"><label>Motivo Surtido:</label><div class="v222-choice v222-two">'+reasons.map(x=>'<button type="button" data-v222-reason="'+esc(x)+'" class="'+(x===reason?'selected':'')+'" '+(running?'disabled':'')+'>'+esc(x)+'</button>').join('')+'</div></div>'
      :'';
    const activityButtons=acts.map(x=>'<button type="button" data-v222-activity="'+esc(x)+'" class="'+(x===activity?'selected':'')+'" '+(running?'disabled':'')+'>'+esc(x)+'</button>').join('');
    const areaRows=(meta.areas||['Colgado','Doblado','Jeans','Lencería']).map(area=>
      '<tr><td>'+esc(area)+'</td><td><input type="number" min="0" step="1" inputmode="numeric" data-v222-area="'+esc(area)+'" value="" placeholder="0" '+(!running?'disabled':'')+'></td></tr>'
    ).join('');
    const hist=(history.items||[]).map(r=>{
      const p=r.pieces_by_area||{};
      return '<tr><td><b>'+esc(r.employee_name||'')+'</b></td><td>'+esc(r.operation_type||'Origen')+'</td><td>'+esc(r.supply_reason||'—')+'</td><td>'+esc(r.activity||'')+'</td>'+
        '<td>'+Math.round(num(p.Colgado)).toLocaleString('es-MX')+'</td><td>'+Math.round(num(p.Doblado)).toLocaleString('es-MX')+'</td><td>'+Math.round(num(p.Jeans)).toLocaleString('es-MX')+'</td><td>'+Math.round(num(p['Lencería'])).toLocaleString('es-MX')+'</td>'+
        '<td><b>'+Math.round(num(r.total_pieces)).toLocaleString('es-MX')+'</b></td><td>'+hms(r.duration_seconds)+'</td></tr>';
    }).join('');

    host.innerHTML=
      '<div id="v222CaptureCard" class="v222-capture-card">'+
        '<div class="v222-capture-head"><div><h3>Registro de productividad</h3><div class="v222-note">Selecciona el tipo de operación y la actividad. Al finalizar captura las piezas por área.</div></div><div id="v222Timer" class="v222-timer">00:00:00</div></div>'+
        '<div class="v222-meta"><span>'+esc(meta.date||'')+'</span><span>'+esc(meta.store||'')+'</span><span>'+esc(meta.employee_name||'')+'</span><span>Nómina '+esc(meta.employee_no||'—')+'</span></div>'+
        '<div class="v222-section"><label>Tipo de operación</label><div class="v222-choice v222-two">'+typeButtons+'</div></div>'+
        reasonHtml+
        '<div class="v222-section"><label>Actividad</label><div class="v222-choice">'+activityButtons+'</div></div>'+
        '<div class="v222-section"><label>Piezas por área</label><div class="v222-area-wrap"><table class="v222-area-table"><thead><tr><th>Área</th><th>Piezas</th></tr></thead><tbody>'+areaRows+'<tr class="v222-total-row"><td>Total</td><td><b id="v222AreaTotal">0</b></td></tr></tbody></table></div></div>'+
        '<div class="v222-actions"><button type="button" id="v222Start" class="v222-start" '+(running?'disabled':'')+'>▶ Inicio</button><button type="button" id="v222Finish" class="v222-finish" '+(!running?'disabled':'')+'>■ Fin</button><span id="v222Msg" class="v222-msg"></span></div>'+
      '</div>'+
      '<div class="v222-capture-card"><h3 style="margin:0 0 9px;color:#123f73">Capturas de hoy</h3><div class="v222-history-wrap"><table class="v222-history"><thead><tr><th>Colaborador</th><th>Tipo</th><th>Motivo</th><th>Actividad</th><th>Colgado</th><th>Doblado</th><th>Jeans</th><th>Lencería</th><th>Total</th><th>Tiempo</th></tr></thead><tbody>'+(hist||'<tr><td colspan="10">Sin capturas de hoy.</td></tr>')+'</tbody></table></div></div>';

    startClock(active?.started_at||'');

    qa('[data-v222-type]').forEach(btn=>btn.onclick=()=>{
      captureState.operation_type=btn.dataset.v222Type;
      captureState.activity=activityOptions(captureState.operation_type,meta)[0];
      if(captureState.operation_type==='Resurtido')captureState.supply_reason=reasons[0]||'Excedente';
      paintCapture(meta,null,history);
    });
    qa('[data-v222-reason]').forEach(btn=>btn.onclick=()=>{
      captureState.supply_reason=btn.dataset.v222Reason;
      paintCapture(meta,null,history);
    });
    qa('[data-v222-activity]').forEach(btn=>btn.onclick=()=>{
      captureState.activity=btn.dataset.v222Activity;
      paintCapture(meta,null,history);
    });
    qa('[data-v222-area]').forEach(inp=>inp.addEventListener('input',updateAreaTotal));

    q('#v222Start')?.addEventListener('click',async()=>{
      const msg=q('#v222Msg');msg.textContent='Iniciando…';
      try{
        const res=await A('/api/operation-capture-v222/start',{
          method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            store:meta.store||selectedStore(),
            operation_type:captureState.operation_type,
            supply_reason:captureState.operation_type==='Resurtido'?captureState.supply_reason:'',
            activity:captureState.activity
          })
        });
        msg.textContent=res.message||'Tiempo iniciado';
        await renderCapture();
      }catch(e){msg.textContent=e.message||String(e)}
    });

    q('#v222Finish')?.addEventListener('click',async()=>{
      if(!active)return;
      const msg=q('#v222Msg');msg.textContent='Guardando…';
      try{
        const pieces=areasFromInputs();
        const res=await A('/api/operation-capture-v222/'+active.id+'/finish',{
          method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({pieces_by_area:pieces})
        });
        clearInterval(timerHandle);timerStartedAt='';
        msg.textContent=res.message||'Productividad guardada';
        await renderCapture();
      }catch(e){msg.textContent=e.message||String(e)}
    });
  }

  async function renderCapture(){
    if(!isOperation())return;
    setCaptureTabActive();
    q('#operativoCentro')?.classList.add('hidden');
    q('#operativoDynamic')?.classList.remove('hidden');
    if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent='Cargar productividad';
    if(q('#operativoDynamicSub'))q('#operativoDynamicSub').textContent='Tipo de operación, actividad y piezas por área';
    const host=q('#operativoDynamicContent');if(!host)return;
    host.innerHTML='<div class="infoempty">Preparando captura…</div>';
    try{
      const store=selectedStore();
      const [meta,active]=await Promise.all([
        A('/api/operation-capture-v222/meta?store='+encodeURIComponent(store)),
        A('/api/operation-capture-v222/active')
      ]);
      const history=await A('/api/operation-capture-v222/history?date='+encodeURIComponent(meta.date||'')+'&store='+encodeURIComponent(meta.store||store));
      paintCapture(meta,active.item||null,history);
    }catch(e){
      host.innerHTML='<div class="infoempty">No fue posible abrir Cargar productividad: '+esc(e.message||e)+'</div>';
    }
  }
  window.V222_renderOperationCapture=renderCapture;

  // Intercepta la pestaña antes del renderer V200 heredado.
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#v200OperationTabs [data-v200-op="capture"]');
    if(!btn||!isOperation())return;
    e.preventDefault();
    e.stopImmediatePropagation();
    setCaptureTabActive();
    renderCapture();
  },true);

  function wrapRenderer(){
    const current=window.renderOperativoView;
    if(typeof current!=='function'||current.__v222Capture)return;
    const base=current;
    const wrapped=async function(name,force){
      const tab=String(window.V149_OPERATION_TAB||window.V125_OPERATION_TAB||'summary');
      if(name==='Operación'&&tab==='capture')return renderCapture();
      return base.apply(this,arguments);
    };
    wrapped.__v222Capture=true;
    wrapped.__v222Base=base;
    window.renderOperativoView=wrapped;
  }

  /* ---------- navegación / iconos ---------- */
  function cleanDuplicateIcons(){
    qa('#v200OperationTabs>button').forEach(btn=>{
      btn.querySelectorAll(':scope>.rt-tab-icon,:scope>.v164-tab-icon,:scope>.v166-tab-icon,:scope>.v206-tab-icon,:scope>.v217-tab-icon').forEach(x=>x.remove());
      const icons=qa(':scope>.v203-tab-icon',btn);icons.slice(1).forEach(x=>x.remove());
      const labels=qa(':scope>.v203-tab-label',btn);labels.slice(1).forEach(x=>x.remove());
      qa(':scope>svg',btn).forEach(x=>x.remove());
    });
    qa('#operativoNav>button,#analysisNav>button').forEach(btn=>{
      btn.querySelectorAll(':scope>.v164-tab-icon,:scope>.v166-tab-icon,:scope>.v203-tab-icon,:scope>.v206-tab-icon,:scope>.v217-tab-icon').forEach(x=>x.remove());
      const icons=qa(':scope>.rt-tab-icon',btn);icons.slice(1).forEach(x=>x.remove());
      const labels=qa(':scope>.rt-tab-label',btn);labels.slice(1).forEach(x=>x.remove());
      qa(':scope>svg',btn).forEach(x=>x.remove());
    });
  }

  function operationTabKeys(){
    const map={summary:'operation.summary',daily:'operation.daily',capture:'operation.capture',productivity:'operation.productivity',standards:'operation.standards'};
    qa('#v200OperationTabs>[data-v200-op]').forEach(btn=>{
      const key=map[btn.dataset.v200Op];if(key)btn.dataset.tabKey=key;
    });
  }

  function stageFor(host){
    if(!host)return null;
    let stage=host.parentElement?.classList?.contains('v222-tab-stage')?host.parentElement:null;
    if(stage)return stage;
    stage=document.createElement('div');
    stage.className='v222-tab-stage';
    stage.dataset.host=host.id;
    const left=document.createElement('button');left.type='button';left.className='v222-tab-arrow';left.setAttribute('aria-label','Pestañas anteriores');left.textContent='‹';
    const right=document.createElement('button');right.type='button';right.className='v222-tab-arrow';right.setAttribute('aria-label','Pestañas siguientes');right.textContent='›';
    host.parentNode.insertBefore(stage,host);
    stage.append(left,host,right);
    left.addEventListener('click',()=>host.scrollBy({left:-Math.max(160,host.clientWidth*.72),behavior:'smooth'}));
    right.addEventListener('click',()=>host.scrollBy({left:Math.max(160,host.clientWidth*.72),behavior:'smooth'}));
    host.addEventListener('scroll',()=>updateStage(stage,host),{passive:true});
    return stage;
  }

  function ownsHost(host){
    const mod=moduleName();
    return (host.id==='operativoNav'&&mod==='operativo')||(host.id==='analysisNav'&&mod==='analysis')||(host.id==='v200OperationTabs'&&mod==='operation');
  }

  function updateStage(stage,host){
    if(!stage||!host)return;
    const owns=ownsHost(host);
    stage.classList.toggle('v222-stage-hidden',!owns);
    if(!owns)return;
    const overflow=host.scrollWidth>host.clientWidth+4;
    stage.classList.toggle('v222-no-scroll',!overflow);
    const buttons=qa('.v222-tab-arrow',stage);
    if(buttons[0])buttons[0].disabled=!overflow||host.scrollLeft<=2;
    if(buttons[1])buttons[1].disabled=!overflow||host.scrollLeft+host.clientWidth>=host.scrollWidth-3;
  }

  function refreshNav(){
    operationTabKeys();
    cleanDuplicateIcons();
    ['operativoNav','analysisNav','v200OperationTabs'].forEach(id=>{
      const host=q('#'+id);if(!host)return;
      const stage=stageFor(host);
      requestAnimationFrame(()=>updateStage(stage,host));
    });
  }

  /* ---------- Configuración de visibilidad ---------- */
  function groupVisibility(){
    const box=q('#tabVisibilityOptions');if(!box)return;
    const direct=qa(':scope>label.field',box);
    if(!direct.length)return;
    const groups=[
      ['Cambios y Muertos','operations.'],
      ['Operación','operation.'],
      ['Análisis Comercial','commercial.']
    ];
    const byPrefix=new Map(groups.map(x=>[x[1],[]]));
    direct.forEach(row=>{
      const key=q('[data-tab-setting]',row)?.dataset.tabSetting||'';
      const prefix=key.startsWith('operations.')?'operations.':key.startsWith('operation.')?'operation.':key.startsWith('commercial.')?'commercial.':'';
      if(prefix)byPrefix.get(prefix).push(row);
    });
    box.innerHTML='';
    box.classList.add('v222-grouped');
    groups.forEach(([title,prefix])=>{
      const section=document.createElement('section');section.className='v222-vis-group';section.dataset.prefix=prefix;
      const h=document.createElement('h3');h.className='v222-vis-title';h.textContent=title;section.appendChild(h);
      (byPrefix.get(prefix)||[]).forEach(row=>section.appendChild(row));
      box.appendChild(section);
    });
  }

  // Nunca guardar un reporte completamente sin pestañas visibles.
  q('#saveTabVisibility')?.addEventListener('click',e=>{
    const groups=[
      ['operations.','Cambios y Muertos'],
      ['operation.','Operación'],
      ['commercial.','Análisis Comercial']
    ];
    for(const [prefix,label] of groups){
      const inputs=qa('[data-tab-setting^="'+prefix+'"]');
      if(inputs.length&&!inputs.some(x=>x.checked)){
        e.preventDefault();e.stopImmediatePropagation();
        const msg=q('#tabVisibilityMsg');if(msg)msg.textContent='Debe quedar visible al menos una pestaña de '+label+'.';
        return;
      }
    }
  },true);

  const visObserver=new MutationObserver(()=>setTimeout(()=>{groupVisibility();refreshNav()},0));
  const visBox=q('#tabVisibilityOptions');if(visBox)visObserver.observe(visBox,{childList:true,subtree:false});

  const navObserver=new MutationObserver(()=>setTimeout(refreshNav,0));
  ['operativoNav','analysisNav','v200OperationTabs'].forEach(id=>{const h=q('#'+id);if(h)navObserver.observe(h,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']})});

  // Si se oculta la pestaña activa de Operación, abre la primera visible.
  document.addEventListener('report-tabs-visibility-changed',()=>{
    setTimeout(()=>{
      operationTabKeys();refreshNav();
      if(!isOperation())return;
      const active=q('#v200OperationTabs>[data-v200-op].active');
      const hidden=active&&(active.hidden||active.classList.contains('hidden')||active.getAttribute('aria-hidden')==='true');
      if(hidden){
        const next=qa('#v200OperationTabs>[data-v200-op]').find(x=>!x.hidden&&!x.classList.contains('hidden')&&x.getAttribute('aria-hidden')!=='true');
        next?.click();
      }
    },40);
  });

  function setup(){
    wrapRenderer();
    operationTabKeys();
    groupVisibility();
    refreshNav();
    // Defensa: si otro renderer heredado pinta el formulario antiguo mientras
    // Captura está activa, se sustituye inmediatamente por V222.
    if(isOperation()){
      const tab=String(window.V149_OPERATION_TAB||window.V125_OPERATION_TAB||'summary');
      if(tab==='capture'&&q('#v200OpActivity')&&!q('#v222CaptureCard'))renderCapture();
    }
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [100,300,800,1600,2800].forEach(ms=>setTimeout(setup,ms));
  document.addEventListener('click',e=>{if(e.target.closest?.('[data-main],#operativoNav,#analysisNav,#v200OperationTabs'))setTimeout(refreshNav,50)},true);
  window.addEventListener('resize',()=>setTimeout(refreshNav,60),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(refreshNav,150),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});

  console.info('[V222] captura por tipo/área + navegación con flechas + visibilidad agrupada.');
})();
</script>"""

    @m.app.middleware("http")
    async def v222_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v222-operation-capture-nav-admin-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v222-operation-capture-nav-admin-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V222",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print("[V222] HTML warning:", type(exc).__name__, exc, flush=True)
            return response

    m._V222_OPERATION_CAPTURE_NAV_ADMIN = True
    print("[V222] captura Operación + tabs con flechas + visibilidad por reporte instalada.", flush=True)
