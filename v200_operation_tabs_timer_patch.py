"""V200 · Sincronía de pestañas + Operación con captura temporizada por área.

Objetivos:
- En Cambios y Muertos, la pestaña activa siempre coincide con el contenido real.
- Operación conserva exactamente: Resumen, Captura diaria, Cargar productividad,
  Productividad y Estándares.
- Operación muestra un solo sistema de filtros, nunca dos bloques simultáneos.
- Cargar productividad de Operación usa Actividad (Acondicionado/Clasificado/Ubicado),
  Área (Doblado/Colgado/Jeans/Lencería), Piezas e Inicio/Fin.
- Fecha, tienda, nombre y nómina se toman automáticamente del perfil/sesión.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")


def install(m):
    if getattr(m, "_V200_OPERATION_TABS_TIMER", False):
        return

    AREAS = ("Doblado", "Frontal", "Colgado", "Jeans", "Lencería")
    ACTIVITIES = ("Acondicionado", "Clasificado", "Ubicado")

    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS operation_productivity_timer(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            store TEXT NOT NULL,
            user_id INTEGER,
            employee_no TEXT DEFAULT '',
            employee_name TEXT NOT NULL,
            area TEXT NOT NULL,
            activity TEXT NOT NULL,
            pieces REAL NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            ended_at TEXT DEFAULT '',
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_op_timer_date_store "
            "ON operation_productivity_timer(date,store)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_op_timer_actor_status "
            "ON operation_productivity_timer(created_by,status)"
        )

    def _profile(actor):
        with m.db() as con:
            row = con.execute(
                "SELECT id,username,store,full_name,employee_no "
                "FROM users WHERE id=? AND active=1",
                (actor.get("id"),),
            ).fetchone()
        if not row:
            raise HTTPException(401, "Sesión requerida")
        return dict(row)

    def _resolve_store(actor, requested=""):
        profile = _profile(actor)
        assigned = str(actor.get("store") or profile.get("store") or "").strip()
        role = str(actor.get("role") or "")
        if role in ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria"):
            if not assigned:
                raise HTTPException(409, "Tu usuario no tiene tienda asignada")
            return assigned

        req = str(requested or "").strip()
        stores = list(m.store_names(True) or [])
        active = {m.login_key(x): x for x in stores}
        if req and req != "Compañía":
            chosen = active.get(m.login_key(req))
            if chosen:
                return chosen
        if assigned:
            chosen = active.get(m.login_key(assigned))
            if chosen:
                return chosen
        if stores:
            # Super/Admin sin tienda fija: mantener captura utilizable para revisión.
            return stores[0]
        raise HTTPException(409, "No hay tiendas activas")

    def _today():
        return datetime.now(MX).date().isoformat()

    def _parse_dt(value):
        try:
            return datetime.fromisoformat(str(value or ""))
        except Exception:
            return None

    @m.app.get("/api/operation-productivity-timer/meta")
    def operation_productivity_timer_meta(request: Request, store: str = ""):
        actor = m.require_user(request)
        profile = _profile(actor)
        resolved = _resolve_store(actor, store)
        return {
            "areas": list(AREAS),
            "activities": list(ACTIVITIES),
            "date": _today(),
            "store": resolved,
            "employee_name": str(profile.get("full_name") or profile.get("username") or ""),
            "employee_no": str(profile.get("employee_no") or ""),
            "profile_required": not bool(
                str(profile.get("full_name") or "").strip()
                and str(profile.get("employee_no") or "").strip()
            ),
        }

    @m.app.get("/api/operation-productivity-timer/active")
    def operation_productivity_timer_active(request: Request):
        actor = m.require_user(request)
        with m.db() as con:
            row = con.execute(
                "SELECT * FROM operation_productivity_timer "
                "WHERE created_by=? AND status='active' ORDER BY id DESC LIMIT 1",
                (str(actor.get("username") or ""),),
            ).fetchone()
        return {"item": dict(row) if row else None}

    @m.app.post("/api/operation-productivity-timer/start")
    async def operation_productivity_timer_start(request: Request):
        actor = m.require_user(
            request, ("superadmin", "admin", "tienda", "colaborador", "colaborador_operativo")
        )
        body = await request.json()
        area = str(body.get("area") or "").strip()
        activity = str(body.get("activity") or "").strip()
        if area not in AREAS:
            raise HTTPException(400, "Selecciona un área válida")
        if activity not in ACTIVITIES:
            raise HTTPException(400, "Selecciona una actividad válida")

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
        with m.db() as con:
            running = con.execute(
                "SELECT id FROM operation_productivity_timer "
                "WHERE created_by=? AND status='active' LIMIT 1",
                (created_by,),
            ).fetchone()
            if running:
                raise HTTPException(409, "Ya tienes una actividad en curso. Finalízala antes de iniciar otra.")
            cur = con.execute(
                """INSERT INTO operation_productivity_timer(
                    date,store,user_id,employee_no,employee_name,area,activity,pieces,
                    started_at,ended_at,duration_seconds,status,created_by,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,0,?,'',0,'active',?,?,?)""",
                (
                    day, store, int(profile.get("id") or actor.get("id") or 0),
                    employee_no, full_name, area, activity, now,
                    created_by, now, now,
                ),
            )
            rid = int(cur.lastrowid)
        return {
            "ok": True, "id": rid, "started_at": now, "date": day,
            "store": store, "message": "Tiempo iniciado",
        }

    @m.app.post("/api/operation-productivity-timer/{record_id}/finish")
    async def operation_productivity_timer_finish(record_id: int, request: Request):
        actor = m.require_user(
            request, ("superadmin", "admin", "tienda", "colaborador", "colaborador_operativo")
        )
        body = await request.json()
        try:
            pieces = max(float(body.get("pieces") or 0), 0.0)
        except Exception:
            raise HTTPException(400, "Piezas debe ser un número válido")
        if pieces <= 0:
            raise HTTPException(400, "Captura las piezas realizadas")

        now_dt = datetime.now(MX)
        now = now_dt.isoformat(timespec="seconds")
        with m.db() as con:
            row = con.execute(
                "SELECT * FROM operation_productivity_timer WHERE id=?",
                (record_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Registro no encontrado")
            data = dict(row)
            role = str(actor.get("role") or "")
            if role not in ("superadmin", "admin") and str(data.get("created_by") or "") != str(actor.get("username") or ""):
                raise HTTPException(403, "No puedes finalizar este registro")
            if str(data.get("status") or "") != "active":
                raise HTTPException(409, "El registro ya fue finalizado")
            start = _parse_dt(data.get("started_at"))
            duration = max(int((now_dt - start).total_seconds()), 0) if start else 0
            con.execute(
                """UPDATE operation_productivity_timer
                   SET pieces=?,ended_at=?,duration_seconds=?,status='finished',updated_at=?
                   WHERE id=?""",
                (pieces, now, duration, now, record_id),
            )

            # Mantener compatibilidad con la tabla histórica: Colgado/Doblado
            # siguen apareciendo en los reportes existentes. Jeans/Lencería
            # permanecen en la captura digital V200 para el nuevo alcance.
            if str(data.get("area") or "") in ("Colgado", "Doblado"):
                exists = con.execute(
                    """SELECT id FROM operation_productivity
                       WHERE date=? AND store=? AND employee_no=? AND origin=? AND activity=?
                         AND created_at=? LIMIT 1""",
                    (
                        data.get("date"), data.get("store"), data.get("employee_no"),
                        data.get("area"), data.get("activity"), data.get("started_at"),
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
                            data.get("employee_no"), data.get("employee_name"),
                            data.get("area"), data.get("activity"), pieces,
                            data.get("started_at"), data.get("created_by"), now,
                            str(actor.get("username") or ""),
                        ),
                    )
        return {
            "ok": True, "pieces": pieces, "duration_seconds": duration,
            "message": "Tiempo finalizado y productividad guardada",
        }

    @m.app.get("/api/operation-productivity-timer/history")
    def operation_productivity_timer_history(
        request: Request, date: str = "", store: str = ""
    ):
        actor = m.require_user(request)
        day = str(date or _today())[:10]
        role = str(actor.get("role") or "")
        profile = _profile(actor)
        params = [day]
        where = ["date=?"]
        if role in ("tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria"):
            where.append("store=?")
            params.append(str(profile.get("store") or ""))
        elif store and store != "Compañía":
            where.append("store=?")
            params.append(store)

        # Los colaboradores ven sus capturas; administradores ven el alcance de tienda.
        if role in ("colaborador", "colaborador_operativo"):
            where.append("created_by=?")
            params.append(str(actor.get("username") or ""))

        with m.db() as con:
            rows = con.execute(
                "SELECT * FROM operation_productivity_timer WHERE "
                + " AND ".join(where)
                + " ORDER BY id DESC LIMIT 80",
                tuple(params),
            ).fetchall()
        return {"items": [dict(r) for r in rows]}

    css = r'''<style id="v200-operation-tabs-timer-css">
/* Pestañas propias de Operación: una sola fuente visual. */
#v200OperationTabs{
  display:none;
  gap:6px;
  overflow-x:auto;
  overflow-y:hidden;
  white-space:nowrap;
  scrollbar-width:none;
  -webkit-overflow-scrolling:touch;
  scroll-snap-type:x proximity;
  margin:5px 0 8px;
  padding:4px 2px;
}
#v200OperationTabs::-webkit-scrollbar{display:none}
body.v200-operation #v200OperationTabs,
body[data-v163-module="operation"] #v200OperationTabs{display:flex!important}
#v200OperationTabs button{
  flex:0 0 auto;
  min-height:38px;
  border:1px solid #d7e2ee;
  border-radius:10px;
  background:#fff;
  color:#294b70;
  padding:0 11px;
  font-size:8.5px;
  line-height:1;
  font-weight:900;
  scroll-snap-align:center;
}
#v200OperationTabs button.active{
  background:linear-gradient(135deg,#0b3a6e,#0d67bd);
  color:#fff;
  border-color:#0b4b8a;
  box-shadow:0 4px 12px rgba(11,58,110,.16);
}

/* Operación usa sólo el filtro branded nativo (el segundo bloque de la vista).
   La fachada V161 de arriba se elimina para evitar filtros duplicados. */
body.v200-operation #operativoDynamicContent>.v125-tabs,
body.v200-operation #operativoDynamicContent>.v167-safe-tabs,
body.v200-operation #operativoDynamicContent .v125-tabs,
body.v200-operation #operativoDynamicContent .v167-safe-tabs,
body[data-v163-module="operation"] #operativoDynamicContent>.v125-tabs,
body[data-v163-module="operation"] #operativoDynamicContent>.v167-safe-tabs{
  display:none!important;
}
body.v200-operation #v161FilterBar,
body[data-v163-module="operation"] #v161FilterBar{
  display:none!important;
}
body.v200-operation.v200-operation-has-filter #operativoPeriodBar,
body[data-v163-module="operation"].v200-operation-has-filter #operativoPeriodBar{
  display:block!important;
}
body.v200-operation.v200-operation-no-filter #operativoPeriodBar,
body[data-v163-module="operation"].v200-operation-no-filter #operativoPeriodBar{
  display:none!important;
}

/* Captura temporizada de Operación. */
.v200-op-card{
  background:#fff;
  border:1px solid #d6e2ee;
  border-radius:14px;
  padding:14px;
  margin:6px 0 11px;
}
.v200-op-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap}
.v200-op-head h3{margin:0;color:#123b73;font-size:15px}
.v200-op-note{margin-top:5px;color:#687b93;font-size:8.5px;line-height:1.4}
.v200-op-timer{
  min-width:132px;padding:9px 14px;border-radius:12px;background:#eef5ff;
  color:#123b73;font-size:27px;font-weight:950;text-align:center;
  font-variant-numeric:tabular-nums;
}
.v200-op-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:12px}
.v200-op-field label{display:block;margin:0 0 5px;color:#667085;font-size:8px;font-weight:950;text-transform:uppercase}
.v200-op-field select,.v200-op-field input{
  width:100%;min-height:44px;border:1px solid #ccd8e6;border-radius:10px;
  background:#fff;color:#123b73;padding:9px 10px;font-size:14px;font-weight:750;
}
.v200-op-pieces{margin-top:10px;max-width:280px}
.v200-op-pieces input{font-size:21px;font-weight:950}
.v200-op-actions{display:flex;gap:8px;margin-top:12px}
.v200-op-start,.v200-op-finish{
  border:0;border-radius:10px;padding:11px 18px;font-weight:950;cursor:pointer
}
.v200-op-start{background:#16a34a;color:#fff}
.v200-op-finish{background:#ef8f8f;color:#fff}
.v200-op-start:disabled,.v200-op-finish:disabled{opacity:.48;cursor:not-allowed}
.v200-op-msg{min-height:16px;margin-top:8px;color:#667085;font-size:8.5px}
.v200-op-auto{
  display:flex;gap:8px;flex-wrap:wrap;margin-top:9px;color:#64748b;font-size:8px
}
.v200-op-auto span{background:#f7faff;border:1px solid #e1eaf3;border-radius:999px;padding:4px 7px}
.v200-op-history .table{min-width:680px}

@media(max-width:900px){
  #v200OperationTabs{gap:5px;margin:3px 0 7px;padding:3px 1px}
  #v200OperationTabs button{min-height:38px;padding:0 9px;font-size:8.2px}
  .v200-op-card{padding:12px}
  .v200-op-grid{grid-template-columns:1fr 1fr}
  .v200-op-timer{font-size:23px}
}
@media(max-width:390px){
  .v200-op-grid{grid-template-columns:1fr}
}
</style>'''

    js = r'''<script id="v200-operation-tabs-timer-js">
(function(){
  if(window.__V200_OPERATION_TABS_TIMER)return;
  window.__V200_OPERATION_TABS_TIMER=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const n=Number(v||0);return Number.isFinite(n)?n:0};
  const fmt=v=>Math.round(num(v)).toLocaleString('es-MX');
  const TABS=[
    ['summary','Resumen'],
    ['daily','Captura diaria'],
    ['capture','Cargar productividad'],
    ['productivity','Productividad'],
    ['standards','Estándares Operativos'],
  ];
  let activeTimer=null;
  let timerInterval=0;
  let wrappedRenderer=null;

  function mainName(){
    const tagged=String(document.body.dataset.v163Module||'').toLowerCase();
    if(tagged)return tagged;
    try{
      const w=String(window.MAIN||'').toLowerCase();
      if(w)return w;
    }catch(_){}
    try{return String(MAIN||'').toLowerCase()}catch(_){return ''}
  }
  function isOperation(){return mainName()==='operation'}
  function opTab(){
    try{return String(window.V149_OPERATION_TAB||window.V125_OPERATION_TAB||'summary')}
    catch(_){return 'summary'}
  }
  function setOpTab(key){
    window.V149_OPERATION_TAB=key;
    window.V125_OPERATION_TAB=key==='summary'?'daily':key;
  }

  function ensureOperationTabs(){
    let host=q('#v200OperationTabs');
    if(!host){
      host=document.createElement('div');
      host.id='v200OperationTabs';
      host.setAttribute('role','tablist');
      host.innerHTML=TABS.map(([k,l])=>'<button type="button" data-v200-op="'+k+'">'+l+'</button>').join('');
      const anchor=q('#operativoPeriodBar')||q('#operativoDynamic')||q('#page-operativo');
      anchor?.parentNode?.insertBefore(host,anchor);
    }
    host.querySelectorAll('[data-v200-op]').forEach(btn=>{
      if(btn.dataset.bound!=='1'){
        btn.dataset.bound='1';
        btn.addEventListener('click',async()=>{
          const key=btn.dataset.v200Op;
          setOpTab(key);
          syncOperationChrome(key,true);
          if(key==='capture') await renderOperationCapture();
          else if(typeof window.renderOperativoView==='function') await window.renderOperativoView('Operación',true);
        });
      }
    });
    return host;
  }

  function centerButton(btn){
    if(!btn)return;
    try{btn.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}catch(_){}
  }

  function syncOperationChrome(key=opTab(),center=false){
    const op=isOperation();
    document.body.classList.toggle('v200-operation',op);
    document.body.classList.remove('v200-operation-has-filter','v200-operation-no-filter');
    if(!op)return;

    ensureOperationTabs();
    const host=q('#v200OperationTabs');
    host?.querySelectorAll('[data-v200-op]').forEach(btn=>{
      const on=btn.dataset.v200Op===key;
      btn.classList.toggle('active',on);
      btn.setAttribute('aria-selected',on?'true':'false');
      if(on&&center)centerButton(btn);
    });

    // Resumen/Captura diaria/Productividad conservan únicamente el filtro
    // branded nativo (#operativoPeriodBar). La fachada V161 de arriba se oculta.
    // Cargar productividad y Estándares no necesitan filtro externo.
    const needsFilter=['summary','daily','productivity'].includes(key);
    document.body.classList.toggle('v200-operation-has-filter',needsFilter);
    document.body.classList.toggle('v200-operation-no-filter',!needsFilter);
    const facade=q('#v161FilterBar');
    if(facade)facade.classList.remove('on');
    const nativeBar=q('#operativoPeriodBar');
    if(nativeBar){
      nativeBar.classList.toggle('hidden',!needsFilter);
      nativeBar.style.display=needsFilter?'block':'none';
    }

    // Ocultar pestañas históricas que se renderizan dentro del contenido.
    qa('#operativoDynamicContent .v125-tabs,#operativoDynamicContent .v167-safe-tabs').forEach(x=>x.style.display='none');
  }

  function syncCmCaptureNav(center=false){
    if(mainName()!=='operativo')return;
    let current='';
    try{current=String(OP_VIEW||'')}catch(_){}
    const title=String(q('#operativoDynamicTitle')?.textContent||'').trim();
    if(current!=='Cargar productividad' && title!=='Cargar productividad')return;
    const nav=q('#operativoNav');if(!nav)return;
    const btn=q('[data-opview="Cargar productividad"]',nav);if(!btn)return;
    qa('[data-opview]',nav).forEach(x=>{
      const on=x===btn;
      x.classList.toggle('active',on);
      x.setAttribute('aria-selected',on?'true':'false');
    });
    if(center)centerButton(btn);
  }

  async function capApi(url,opt){
    if(typeof api==='function')return api(url,opt||{});
    const r=await fetch(url,{credentials:'same-origin',...(opt||{})});
    const raw=await r.text();let data={};try{data=raw?JSON.parse(raw):{}}catch(_){}
    if(!r.ok)throw Error(data.detail||data.message||('HTTP '+r.status));
    return data;
  }

  function hms(sec){
    sec=Math.max(0,Math.floor(Number(sec)||0));
    const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;
    return [h,m,s].map(x=>String(x).padStart(2,'0')).join(':');
  }
  function updateTimer(){
    const el=q('#v200OpTimer');if(!el)return;
    if(!activeTimer?.started_at){el.textContent='00:00:00';return}
    const start=new Date(activeTimer.started_at).getTime();
    el.textContent=hms((Date.now()-start)/1000);
  }
  function beginClock(){
    clearInterval(timerInterval);updateTimer();timerInterval=setInterval(updateTimer,1000);
  }

  function chosenStore(){
    const s=q('#operStoreSelect')?.value||'';
    return s&&s!=='Compañía'?s:'';
  }

  async function renderOperationCapture(){
    if(!isOperation())return;
    setOpTab('capture');
    syncOperationChrome('capture',true);
    const centro=q('#operativoCentro'),dyn=q('#operativoDynamic');
    centro?.classList.add('hidden');dyn?.classList.remove('hidden');
    if(q('#operativoDynamicTitle'))q('#operativoDynamicTitle').textContent='Cargar productividad';
    if(q('#operativoDynamicSub'))q('#operativoDynamicSub').textContent='Operación · actividad, área, piezas y tiempo real';
    const host=q('#operativoDynamicContent');if(!host)return;
    host.innerHTML='<div class="infoempty">Preparando captura…</div>';

    try{
      const [meta,active]=await Promise.all([
        capApi('/api/operation-productivity-timer/meta?store='+encodeURIComponent(chosenStore())),
        capApi('/api/operation-productivity-timer/active')
      ]);
      activeTimer=active.item||null;
      const selectedArea=activeTimer?.area||meta.areas?.[0]||'Doblado';
      const selectedActivity=activeTimer?.activity||meta.activities?.[0]||'Acondicionado';
      const history=await capApi(
        '/api/operation-productivity-timer/history?date='+encodeURIComponent(meta.date)+
        '&store='+encodeURIComponent(meta.store||'')
      );

      host.innerHTML=
        '<div class="v200-op-card">'+
          '<div class="v200-op-head"><div><h3>Registro de productividad</h3>'+
          '<div class="v200-op-note">Fecha, tienda, colaborador y nómina se asignan automáticamente desde tu sesión.</div></div>'+
          '<div id="v200OpTimer" class="v200-op-timer">00:00:00</div></div>'+
          '<div class="v200-op-auto"><span>'+esc(meta.date)+'</span><span>'+esc(meta.store)+'</span><span>'+esc(meta.employee_name)+'</span><span>Nómina '+esc(meta.employee_no||'—')+'</span></div>'+
          '<div class="v200-op-grid">'+
            '<div class="v200-op-field"><label>Actividad</label><select id="v200OpActivity" '+(activeTimer?'disabled':'')+'>'+
              (meta.activities||[]).map(x=>'<option '+(x===selectedActivity?'selected':'')+'>'+esc(x)+'</option>').join('')+
            '</select></div>'+
            '<div class="v200-op-field"><label>Área</label><select id="v200OpArea" '+(activeTimer?'disabled':'')+'>'+
              (meta.areas||[]).map(x=>'<option '+(x===selectedArea?'selected':'')+'>'+esc(x)+'</option>').join('')+
            '</select></div>'+
          '</div>'+
          '<div class="v200-op-field v200-op-pieces"><label>Piezas</label><input id="v200OpPieces" type="number" min="0" inputmode="numeric" value="'+num(activeTimer?.pieces)+'"></div>'+
          '<div class="v200-op-actions"><button id="v200OpStart" class="v200-op-start" '+(activeTimer?'disabled':'')+'>▶ Inicio</button>'+
          '<button id="v200OpFinish" class="v200-op-finish" '+(!activeTimer?'disabled':'')+'>■ Fin</button></div>'+
          '<div id="v200OpMsg" class="v200-op-msg"></div>'+
        '</div>'+
        '<div class="v200-op-card v200-op-history"><h3 style="margin-top:0">Capturas de hoy</h3>'+
          '<div class="tablewrap"><table class="table"><thead><tr><th>Colaborador</th><th>Actividad</th><th>Área</th><th>Piezas</th><th>Tiempo</th><th>Estado</th></tr></thead><tbody>'+
          ((history.items||[]).map(r=>'<tr><td><b>'+esc(r.employee_name)+'</b></td><td>'+esc(r.activity)+'</td><td>'+esc(r.area)+'</td><td><b>'+fmt(r.pieces)+'</b></td><td>'+hms(r.duration_seconds)+'</td><td>'+esc(r.status==='active'?'En curso':'Finalizado')+'</td></tr>').join('')||'<tr><td colspan="6">Sin capturas de hoy.</td></tr>')+
          '</tbody></table></div></div>';

      if(activeTimer)beginClock();else{clearInterval(timerInterval);updateTimer()}

      q('#v200OpStart')?.addEventListener('click',async()=>{
        const msg=q('#v200OpMsg');msg.textContent='Iniciando…';
        try{
          const r=await capApi('/api/operation-productivity-timer/start',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
              store:meta.store||chosenStore(),
              activity:q('#v200OpActivity').value,
              area:q('#v200OpArea').value
            })
          });
          msg.textContent=r.message;
          await renderOperationCapture();
        }catch(e){msg.textContent=e.message||String(e)}
      });

      q('#v200OpFinish')?.addEventListener('click',async()=>{
        if(!activeTimer)return;
        const msg=q('#v200OpMsg');msg.textContent='Finalizando…';
        try{
          const r=await capApi('/api/operation-productivity-timer/'+activeTimer.id+'/finish',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({pieces:num(q('#v200OpPieces')?.value)})
          });
          msg.textContent=r.message;
          activeTimer=null;clearInterval(timerInterval);
          await renderOperationCapture();
        }catch(e){msg.textContent=e.message||String(e)}
      });
    }catch(e){
      host.innerHTML='<div class="infoempty">No fue posible abrir Cargar productividad: '+esc(e.message||e)+'</div>';
    }
  }

  function installFinalRenderer(){
    const current=window.renderOperativoView;
    if(typeof current!=='function')return;
    if(wrappedRenderer || current.__v200)return;
    /* V214: cada wrapper conserva SU renderer base. Antes todos compartían
       finalRenderer; al reenvolver después de V166/V167/V168 se formaba un
       ciclo entre wrappers y terminaba en Maximum call stack size exceeded. */
    const baseRenderer=current;
    const wrapped=async function(name,force){
      if(name==='Operación' && opTab()==='capture'){
        return renderOperationCapture();
      }
      const out=await baseRenderer.apply(this,arguments);
      if(name==='Operación'){
        syncOperationChrome(opTab(),false);
      }else if(name==='Cargar productividad'){
        [0,80,260].forEach(ms=>setTimeout(()=>syncCmCaptureNav(ms>0),ms));
      }
      return out;
    };
    wrapped.__v200=true;
    wrapped.__v200Base=current;
    window.renderOperativoView=wrapped;
    wrappedRenderer=wrapped;
  }

  function setup(){
    ensureOperationTabs();
    installFinalRenderer();
    if(isOperation())syncOperationChrome(opTab(),false);
    else document.body.classList.remove('v200-operation','v200-operation-has-filter','v200-operation-no-filter');
    syncCmCaptureNav(false);
  }

  document.addEventListener('click',event=>{
    const main=event.target.closest?.('[data-main]');
    if(main){
      setTimeout(()=>{
        if(main.dataset.main==='operation'){
          document.body.classList.add('v200-operation');
          ensureOperationTabs();
          syncOperationChrome(opTab(),true);
        }else{
          document.body.classList.remove('v200-operation','v200-operation-has-filter','v200-operation-no-filter');
        }
      },60);
    }
    const cm=event.target.closest?.('#operativoNav [data-opview="Cargar productividad"]');
    if(cm)[0,80,240,520].forEach(ms=>setTimeout(()=>syncCmCaptureNav(true),ms));
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(setup,60));
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [150,500,1200,2500].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('pageshow',()=>setTimeout(setup,100),{passive:true});
  console.info('[V200] pestañas sincronizadas + Operación temporizada por actividad/área.');
})();
</script>'''

    @m.app.middleware("http")
    async def v200_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v200-operation-tabs-timer-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v200-operation-tabs-timer-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V200",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V200] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V200_OPERATION_TABS_TIMER = True
    print("[V200] tabs + filtro único + productividad temporizada de Operación instalados.", flush=True)
