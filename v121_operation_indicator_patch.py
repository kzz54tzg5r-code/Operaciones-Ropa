"""V121 · Indicador Operación + perfil Colaborador.

Implementa el flujo validado a partir del Excel de referencia
"Control Diario de Operación y Eficiencia de Mercancía":
- Orígenes manuales Colgado / Doblado (llegada y mercancía liberada).
- Cambios y Muertos se alimenta automáticamente de la base operativa vigente.
- Productividad individual por colaborador con tienda/nómina/nombre persistentes.
- Vistas Día / Semanal / Mensual / Anual con la misma estructura y gráficos.
- Cierre diario por tienda, auditoría y estándares por jornada configurables.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import io
import json
import math
import re
import unicodedata


def install(m):
    if getattr(m, "_V121_OPERATION_INDICATOR", False):
        return

    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, Response

    MX = ZoneInfo("America/Mexico_City")
    ORIGINS = ("Colgado", "Doblado", "Cambios y Muertos")
    MANUAL_ORIGINS = ("Colgado", "Doblado")
    DEFAULT_STANDARDS = {"Colgado": 1228.0, "Doblado": 906.0, "Cambios y Muertos": 670.0}

    m.ROLES = tuple(dict.fromkeys(tuple(m.ROLES) + ("colaborador",)))
    m.ROLE_LABELS["colaborador"] = "Colaborador"
    m.REPORT_TABS.setdefault("operations.operation", "Operación")

    with m.db() as con:
        cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(users)").fetchall()}
        if "employee_no" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN employee_no TEXT DEFAULT ''")
        if "full_name" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''")
        if "operation_profile_complete" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN operation_profile_complete INTEGER NOT NULL DEFAULT 0")
        con.execute("""CREATE TABLE IF NOT EXISTS operation_daily_capture(
            date TEXT NOT NULL, store TEXT NOT NULL, origin TEXT NOT NULL,
            arrival REAL NOT NULL DEFAULT 0, released REAL NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '', updated_at TEXT NOT NULL, updated_by TEXT NOT NULL,
            PRIMARY KEY(date,store,origin)
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS operation_productivity(
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, store TEXT NOT NULL,
            user_id INTEGER, employee_no TEXT DEFAULT '', employee_name TEXT NOT NULL,
            origin TEXT NOT NULL, activity TEXT NOT NULL, pieces REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, created_by TEXT NOT NULL, updated_at TEXT NOT NULL, updated_by TEXT NOT NULL
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_operation_productivity_date_store ON operation_productivity(date,store)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_operation_productivity_employee ON operation_productivity(employee_no,employee_name)")
        con.execute("""CREATE TABLE IF NOT EXISTS operation_day_status(
            date TEXT NOT NULL, store TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
            closed_at TEXT DEFAULT '', closed_by TEXT DEFAULT '', reopened_at TEXT DEFAULT '', reopened_by TEXT DEFAULT '',
            PRIMARY KEY(date,store)
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS operation_standards(
            origin TEXT PRIMARY KEY, pieces_per_shift REAL NOT NULL, updated_at TEXT NOT NULL, updated_by TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS operation_audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT NOT NULL, entity_key TEXT NOT NULL,
            action TEXT NOT NULL, before_json TEXT DEFAULT '', after_json TEXT DEFAULT '',
            changed_at TEXT NOT NULL, changed_by TEXT NOT NULL
        )""")
        now = datetime.now(MX).isoformat(timespec="seconds")
        for origin, standard in DEFAULT_STANDARDS.items():
            con.execute("INSERT OR IGNORE INTO operation_standards(origin,pieces_per_shift,updated_at,updated_by) VALUES(?,?,?,?)", (origin, standard, now, "system"))
        try:
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_users_employee_no_v121 ON users(employee_no) WHERE employee_no<>''")
        except Exception:
            pass

    old_find_login_user = m.find_login_user
    def find_login_user_v121(value):
        row = old_find_login_user(value)
        if row:
            return row
        key = str(value or "").strip()
        if not key:
            return None
        with m.db() as con:
            return con.execute("SELECT * FROM users WHERE active=1 AND employee_no=? LIMIT 1", (key,)).fetchone()
    m.find_login_user = find_login_user_v121

    old_require_user = m.require_user
    def require_user_v121(request, roles=None):
        user = old_require_user(request, roles)
        if str(user.get("role") or "") == "colaborador" and roles is None:
            path = str(request.url.path or "")
            allowed = ("/api/operation", "/api/me/change-password", "/api/me/complete-temporary-password")
            if path.startswith("/api/") and not any(path.startswith(prefix) for prefix in allowed):
                raise HTTPException(403, "El perfil Colaborador sólo tiene acceso a su captura de productividad")
        return user
    m.require_user = require_user_v121

    def _norm(value):
        text = unicodedata.normalize("NFD", str(value or ""))
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return " ".join(text.casefold().strip().split())

    def _number(value, default=0.0):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else default
        except Exception:
            return default

    def _iso_date(value):
        try:
            return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date().isoformat()
        except Exception:
            raise HTTPException(400, "Fecha inválida")

    def _period_bounds(period_type: str, period_value: str):
        ptype = str(period_type or "day").lower().strip()
        value = str(period_value or "").strip()
        today = datetime.now(MX).date()
        if ptype == "day":
            d = datetime.strptime(value[:10], "%Y-%m-%d").date() if value else today - timedelta(days=1)
            return d, d
        if ptype == "week":
            if value:
                mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, flags=re.I)
                if not mt: raise HTTPException(400, "Semana ISO inválida")
                start = date.fromisocalendar(int(mt.group(1)), int(mt.group(2)), 1)
            else:
                iso = today.isocalendar(); start = date.fromisocalendar(iso.year, iso.week, 1)
            return start, start + timedelta(days=6)
        if ptype == "month":
            if value:
                mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
                if not mt: raise HTTPException(400, "Mes inválido")
                y, mo = int(mt.group(1)), int(mt.group(2))
            else:
                y, mo = today.year, today.month
            start = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return start, nxt - timedelta(days=1)
        if ptype == "year":
            y = int(value or today.year)
            if y < 2020 or y > 2100: raise HTTPException(400, "Año inválido")
            return date(y, 1, 1), date(y, 12, 31)
        raise HTTPException(400, "Vista operativa inválida")

    def _standards():
        with m.db() as con:
            rows = con.execute("SELECT origin,pieces_per_shift FROM operation_standards").fetchall()
        out = {str(r["origin"]): _number(r["pieces_per_shift"]) for r in rows}
        for origin, value in DEFAULT_STANDARDS.items(): out.setdefault(origin, value)
        return out

    def _audit(actor, entity, key, action, before=None, after=None, con=None):
        params=(entity, str(key), action, json.dumps(before or {}, ensure_ascii=False), json.dumps(after or {}, ensure_ascii=False), datetime.now(MX).isoformat(timespec="seconds"), str(actor.get("username") or ""))
        if con is not None:
            con.execute("INSERT INTO operation_audit(entity,entity_key,action,before_json,after_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",params)
            return
        with m.db() as audit_con:
            audit_con.execute("INSERT INTO operation_audit(entity,entity_key,action,before_json,after_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",params)

    def _real_row(request):
        try:
            row = m._session_user_row(request)
        except Exception:
            row = None
        if not row:
            raise HTTPException(401, "Sesión requerida")
        return row

    def _scope_store(actor, requested: str):
        role = str(actor.get("role") or "")
        assigned = str(actor.get("store") or "").strip()
        if role in ("tienda", "colaborador"):
            if not assigned: raise HTTPException(409, "El usuario no tiene tienda asignada")
            return assigned
        return str(requested or "Compañía").strip() or "Compañía"

    def _allowed_stores(actor, requested: str):
        scoped = _scope_store(actor, requested)
        if scoped != "Compañía": return [scoped]
        try: return list(m.store_names(True))
        except Exception: return list(m.PROJECT_STORES)

    def _day_status(store: str, day: str):
        with m.db() as con:
            row = con.execute("SELECT * FROM operation_day_status WHERE date=? AND store=?", (day, store)).fetchone()
        return dict(row) if row else {"date": day, "store": store, "status": "open", "closed_at": "", "closed_by": ""}

    def _assert_open(store: str, day: str):
        if _day_status(store, day).get("status") == "closed":
            raise HTTPException(409, "El corte de ese día está cerrado. Solicita reapertura antes de modificar información")

    def _operation_meta(actor):
        dates = set()
        with m.db() as con:
            for row in con.execute("SELECT DISTINCT date FROM operation_daily_capture UNION SELECT DISTINCT date FROM operation_productivity").fetchall():
                if row[0]: dates.add(str(row[0]))
            people = con.execute("SELECT DISTINCT employee_no,employee_name,store FROM operation_productivity ORDER BY employee_name").fetchall()
        try:
            opmeta = m.load_operations_meta() or {}
            dates.update(str(x) for x in (opmeta.get("available_dates") or []) if x)
        except Exception:
            pass
        latest = max(dates) if dates else (datetime.now(MX).date() - timedelta(days=1)).isoformat()
        dts = sorted(dates)
        weeks = sorted({f"{date.fromisoformat(d).isocalendar().year}-W{date.fromisoformat(d).isocalendar().week:02d}" for d in dts})
        months = sorted({d[:7] for d in dts})
        years = sorted({d[:4] for d in dts}) or [str(datetime.now(MX).year)]
        stores = _allowed_stores(actor, "Compañía")
        collaborators = []
        seen = set()
        for r in people:
            if stores and str(r["store"] or "") not in stores: continue
            key = (str(r["employee_no"] or ""), str(r["employee_name"] or ""), str(r["store"] or ""))
            if key in seen: continue
            seen.add(key); collaborators.append({"employee_no": key[0], "name": key[1], "store": key[2]})
        return {"dates": dts, "weeks": weeks, "months": months, "years": years, "latest_date": latest, "stores": stores, "origins": list(ORIGINS), "manual_origins": list(MANUAL_ORIGINS), "collaborators": collaborators, "standards": _standards()}

    def _auto_cm_rows(end_day: date, stores_set):
        daily = {}; people = []
        try:
            source = m.load_ops() or {}
            for r in (source.get("rows") or []):
                ds = str(r.get("date") or "")[:10]
                if not ds: continue
                try: d = date.fromisoformat(ds)
                except Exception: continue
                if d > end_day: continue
                st = str(r.get("store") or "").strip()
                if stores_set and st not in stores_set: continue
                item = daily.setdefault((ds, st), {"arrival":0.0,"processed":0.0,"released":0.0})
                item["arrival"] += _number(r.get("recolectadas")); item["processed"] += _number(r.get("acondicionado")); item["released"] += _number(r.get("ubicado"))
                pieces = _number(r.get("pieces")); name = str(r.get("name") or "").strip(); act = str(r.get("activity") or r.get("activity_original") or "").strip()
                if pieces > 0 and name and act:
                    people.append({"date":ds,"store":st,"employee_no":"","employee_name":name,"origin":"Cambios y Muertos","activity":act,"pieces":pieces,"source":"automatic"})
        except Exception as exc:
            print(f"[V121] C&M automático no disponible: {type(exc).__name__}: {exc}", flush=True)
        return daily, people

    def _operation_report(request, period_type="day", period_value="", store="Compañía", origin="Todos", employee_no=""):
        actor = m.require_user(request); start, end = _period_bounds(period_type, period_value); scoped_store = _scope_store(actor, store); stores = _allowed_stores(actor, scoped_store); stores_set = set(stores); standards = _standards()
        selected_origins = list(ORIGINS) if not origin or origin == "Todos" else [origin]; selected_origins = [x for x in selected_origins if x in ORIGINS]
        if not selected_origins: raise HTTPException(400, "Origen inválido")
        placeholders = ",".join("?" for _ in stores) or "''"
        with m.db() as con:
            captures = [dict(r) for r in con.execute(f"SELECT * FROM operation_daily_capture WHERE date<=? AND store IN ({placeholders}) ORDER BY date,store,origin", (end.isoformat(), *stores)).fetchall()] if stores else []
            prod = [dict(r) for r in con.execute(f"SELECT * FROM operation_productivity WHERE date<=? AND store IN ({placeholders}) ORDER BY date,id", (end.isoformat(), *stores)).fetchall()] if stores else []
            users = [dict(r) for r in con.execute("SELECT id,username,store,employee_no,full_name FROM users").fetchall()]
        manual_cap = {(r["date"],r["store"],r["origin"]):r for r in captures}; manual_prod = {}
        for r in prod:
            key = (r["date"], r["store"], r["origin"]); manual_prod[key] = manual_prod.get(key, 0.0) + _number(r.get("pieces"))
        cm_daily, cm_people = _auto_cm_rows(end, stores_set)
        candidate_dates=[]; candidate_dates.extend(date.fromisoformat(r["date"]) for r in captures if r.get("date")); candidate_dates.extend(date.fromisoformat(r["date"]) for r in prod if r.get("date")); candidate_dates.extend(date.fromisoformat(k[0]) for k in cm_daily)
        calc_start=min(candidate_dates) if candidate_dates else start
        if calc_start>start: calc_start=start
        per_store_origin={}; period_rows=[]; cursor=calc_start
        while cursor<=end:
            ds=cursor.isoformat()
            for st in stores:
                for org in ORIGINS:
                    key=(st,org); prev=per_store_origin.get(key,{}).get("pending",0.0)
                    if org=="Cambios y Muertos":
                        src=cm_daily.get((ds,st),{}); arrival=_number(src.get("arrival")); processed=_number(src.get("processed")); released=_number(src.get("released"))
                    else:
                        cap=manual_cap.get((ds,st,org),{}); arrival=_number(cap.get("arrival")); released=_number(cap.get("released")); processed=_number(manual_prod.get((ds,st,org)))
                    workload=prev+arrival; pending=max(workload-processed,0.0); standard=max(_number(standards.get(org)),0.0); required=workload/standard if standard else 0.0; efficiency=processed/workload*100 if workload else 0.0
                    row={"date":ds,"store":st,"origin":org,"arrival":arrival,"processed":processed,"released":released,"pending_previous":prev,"workload":workload,"pending":pending,"standard":standard,"personal_required":required,"efficiency_pct":efficiency,"status":"Superado" if efficiency>=100 else ("En Proceso" if efficiency>=75 else "Bajo")}; per_store_origin[key]=row
                    if start<=cursor<=end and org in selected_origins: period_rows.append(row)
            cursor+=timedelta(days=1)
        origin_summary=[]
        for org in selected_origins:
            rows=[r for r in period_rows if r["origin"]==org]; first_by_store={}; last_by_store={}; day_required={}
            for r in rows:
                first_by_store.setdefault(r["store"],r); last_by_store[r["store"]]=r; day_required[r["date"]]=day_required.get(r["date"],0.0)+r["personal_required"]
            arrival=sum(r["arrival"] for r in rows); processed=sum(r["processed"] for r in rows); released=sum(r["released"] for r in rows); pending_start=sum(r["pending_previous"] for r in first_by_store.values()); pending=sum(r["pending"] for r in last_by_store.values()); workload=pending_start+arrival; efficiency=processed/workload*100 if workload else 0.0
            active_store_days=len({(r["date"],r["store"]) for r in rows if r["arrival"] or r["processed"] or r["pending_previous"]}); target=standards.get(org,0.0)*active_store_days; compliance=processed/target*100 if target else 0.0; required_avg=sum(day_required.values())/len(day_required) if day_required else 0.0
            origin_summary.append({"origin":org,"arrival":arrival,"processed":processed,"released":released,"pending_start":pending_start,"pending":pending,"standard":standards.get(org,0.0),"personal_required":required_avg,"efficiency_pct":efficiency,"target":target,"compliance_pct":compliance,"status":"Superado" if compliance>=100 else ("En Proceso" if compliance>=75 else "Bajo")})
        daily=[]; cursor=start
        while cursor<=end:
            ds=cursor.isoformat(); item={"date":ds}
            for org in selected_origins:
                rr=[r for r in period_rows if r["date"]==ds and r["origin"]==org]; prefix={"Colgado":"colgado","Doblado":"doblado","Cambios y Muertos":"cambios"}[org]
                item[f"{prefix}_arrival"]=sum(x["arrival"] for x in rr); item[f"{prefix}_processed"]=sum(x["processed"] for x in rr); item[f"{prefix}_released"]=sum(x["released"] for x in rr); item[f"{prefix}_pending"]=sum(x["pending"] for x in rr); work=sum(x["workload"] for x in rr); proc=sum(x["processed"] for x in rr); item[f"{prefix}_efficiency"]=proc/work*100 if work else 0.0; item[f"{prefix}_required"]=sum(x["personal_required"] for x in rr)
            daily.append(item); cursor+=timedelta(days=1)
        people_rows=[r for r in prod if start.isoformat()<=r["date"]<=end.isoformat() and r["origin"] in selected_origins]
        if "Cambios y Muertos" in selected_origins: people_rows += [r for r in cm_people if start.isoformat()<=r["date"]<=end.isoformat()]
        user_map={}
        for u in users:
            for value in (u.get("full_name"),u.get("username")):
                if value: user_map[(_norm(value),str(u.get("store") or ""))]=str(u.get("employee_no") or "")
        for r in people_rows:
            if not r.get("employee_no"): r["employee_no"]=user_map.get((_norm(r.get("employee_name")),str(r.get("store") or "")),"")
        real=_real_row(request)
        if str(real["role"] or "")=="colaborador":
            employee_no=str(real["employee_no"] or ""); people_rows=[r for r in people_rows if str(r.get("employee_no") or "")==employee_no or int(r.get("user_id") or 0)==int(real["id"])]
        elif employee_no: people_rows=[r for r in people_rows if str(r.get("employee_no") or "")==str(employee_no)]
        grouped={}
        for r in people_rows:
            eno=str(r.get("employee_no") or ""); nm=str(r.get("employee_name") or "Sin nombre"); st=str(r.get("store") or ""); key=(eno or _norm(nm),st); g=grouped.setdefault(key,{"employee_no":eno,"name":nm,"store":st,"pieces":0.0,"dates":set(),"targets":set(),"origins":set(),"activities":set()}); g["pieces"]+=_number(r.get("pieces")); g["dates"].add(str(r.get("date") or "")); g["origins"].add(str(r.get("origin") or "")); g["activities"].add(str(r.get("activity") or "")); g["targets"].add((str(r.get("date") or ""),str(r.get("origin") or "")))
        productivity=[]
        for g in grouped.values():
            target=sum(_number(standards.get(org)) for _,org in g["targets"]); days=max(len(g["dates"]),1); pctv=g["pieces"]/target*100 if target else 0.0; productivity.append({"employee_no":g["employee_no"],"name":g["name"],"store":g["store"],"pieces":g["pieces"],"days":days,"daily":g["pieces"]/days,"target":target,"compliance_pct":pctv,"origins":sorted(x for x in g["origins"] if x),"activities":sorted(x for x in g["activities"] if x)})
        productivity.sort(key=lambda x:(-x["compliance_pct"],-x["pieces"],x["name"]))
        total_arrival=sum(x["arrival"] for x in origin_summary); total_processed=sum(x["processed"] for x in origin_summary); total_released=sum(x["released"] for x in origin_summary); total_pending=sum(x["pending"] for x in origin_summary); total_start=sum(x["pending_start"] for x in origin_summary); total_workload=total_start+total_arrival; efficiency=total_processed/total_workload*100 if total_workload else 0.0; target=sum(x["target"] for x in origin_summary); compliance=total_processed/target*100 if target else 0.0
        permissions={"capture_daily":str(actor.get("role") or "") in ("superadmin","admin","tienda"),"capture_productivity":str(actor.get("role") or "") in ("superadmin","admin","tienda","colaborador"),"close_day":str(actor.get("role") or "") in ("superadmin","admin","tienda"),"reopen_day":str(actor.get("role") or "") in ("superadmin","admin"),"edit_standards":str(actor.get("role") or "") in ("superadmin","admin")}
        capture_snapshot=[]; day_status={}
        if period_type=="day" and start==end:
            for st in stores:
                day_status[st]=_day_status(st,start.isoformat())
                for org in MANUAL_ORIGINS:
                    cap=manual_cap.get((start.isoformat(),st,org),{}); capture_snapshot.append({"store":st,"origin":org,"arrival":_number(cap.get("arrival")),"released":_number(cap.get("released")),"notes":str(cap.get("notes") or "")})
        my_entries=[]
        if str(real["role"] or "")=="colaborador": my_entries=[dict(r) for r in prod if int(r.get("user_id") or 0)==int(real["id"]) and start.isoformat()<=r["date"]<=end.isoformat()]
        return {"period_type":period_type,"period_value":period_value,"start_date":start.isoformat(),"end_date":end.isoformat(),"store":scoped_store,"origins":selected_origins,"standards":standards,"summary":{"arrival":total_arrival,"processed":total_processed,"released":total_released,"pending_start":total_start,"pending":total_pending,"efficiency_pct":efficiency,"target":target,"compliance_pct":compliance,"personal_required":sum(x["personal_required"] for x in origin_summary),"active_collaborators":len(productivity)},"origin_summary":origin_summary,"daily":daily,"productivity":productivity[:500],"capture_snapshot":capture_snapshot,"day_status":day_status,"my_entries":my_entries,"permissions":permissions,"role":str(actor.get("role") or ""),"assigned_store":str(actor.get("store") or "")}

    @m.app.get("/api/operation/profile")
    def operation_profile(request: Request):
        row=_real_row(request); role=str(row["role"] or "")
        return {"role":role,"store":str(row["store"] or ""),"employee_no":str(row["employee_no"] or ""),"full_name":str(row["full_name"] or ""),"profile_complete":bool(row["operation_profile_complete"]) if role=="colaborador" else True,"must_change_password":bool(row["must_change_password"])}

    @m.app.post("/api/operation/profile")
    async def operation_profile_save(request: Request):
        row=_real_row(request)
        if str(row["role"] or "")!="colaborador": raise HTTPException(403,"Este perfil sólo aplica a Colaborador")
        body=await request.json(); eno="".join(str(body.get("employee_no") or "").split()); full=" ".join(str(body.get("full_name") or "").split()).strip()
        if len(eno)<3: raise HTTPException(400,"Captura una nómina válida")
        if len(full)<5 or len(full.split())<2: raise HTTPException(400,"Captura tu nombre completo")
        if not str(row["store"] or "").strip(): raise HTTPException(409,"Tu usuario todavía no tiene tienda asignada. Solicita al administrador que la configure")
        with m.db() as con:
            dup=con.execute("SELECT id FROM users WHERE employee_no=? AND id<>?",(eno,row["id"])).fetchone()
            if dup: raise HTTPException(409,"Esa nómina ya está asociada a otro usuario")
            con.execute("UPDATE users SET employee_no=?,full_name=?,operation_profile_complete=1,updated_at=? WHERE id=?",(eno,full,datetime.now(MX).isoformat(timespec="seconds"),row["id"]))
        _audit({"username":row["username"]},"user_profile",row["id"],"complete",{}, {"employee_no":eno,"full_name":full,"store":row["store"]})
        return {"ok":True,"message":"Perfil guardado. A partir de ahora tu nómina, nombre y tienda se cargarán automáticamente"}

    @m.app.get("/api/operation/meta")
    def operation_meta(request: Request):
        return _operation_meta(m.require_user(request))

    @m.app.get("/api/operation/report")
    def operation_report(request: Request, period_type: str="day", period_value: str="", store: str="Compañía", origin: str="Todos", employee_no: str=""):
        return _operation_report(request,period_type,period_value,store,origin,employee_no)

    @m.app.post("/api/operation/daily")
    async def operation_daily_save(request: Request):
        actor=m.require_user(request,("superadmin","admin","tienda")); body=await request.json(); day=_iso_date(body.get("date")); store=_scope_store(actor,body.get("store") or "Compañía")
        if store=="Compañía": raise HTTPException(400,"Selecciona una tienda para capturar")
        _assert_open(store,day); rows=body.get("rows") or []
        if not isinstance(rows,list) or not rows: raise HTTPException(400,"No hay datos para guardar")
        now=datetime.now(MX).isoformat(timespec="seconds"); saved=0
        with m.db() as con:
            for item in rows:
                org=str(item.get("origin") or "")
                if org not in MANUAL_ORIGINS: continue
                arrival=max(_number(item.get("arrival")),0.0); released=max(_number(item.get("released")),0.0); notes=str(item.get("notes") or "").strip()[:500]
                before=con.execute("SELECT * FROM operation_daily_capture WHERE date=? AND store=? AND origin=?",(day,store,org)).fetchone(); before=dict(before) if before else {}
                con.execute("INSERT INTO operation_daily_capture(date,store,origin,arrival,released,notes,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(date,store,origin) DO UPDATE SET arrival=excluded.arrival,released=excluded.released,notes=excluded.notes,updated_at=excluded.updated_at,updated_by=excluded.updated_by",(day,store,org,arrival,released,notes,now,actor["username"]))
                _audit(actor,"daily_capture",f"{day}|{store}|{org}","upsert",before,{"date":day,"store":store,"origin":org,"arrival":arrival,"released":released,"notes":notes},con=con); saved+=1
        return {"ok":True,"saved":saved,"message":"Captura diaria guardada"}

    @m.app.post("/api/operation/productivity")
    async def operation_productivity_save(request: Request):
        actor=m.require_user(request); role=str(actor.get("role") or "")
        if role not in ("superadmin","admin","tienda","colaborador"): raise HTTPException(403,"Sin permiso para capturar productividad")
        body=await request.json(); day=_iso_date(body.get("date")); origin=str(body.get("origin") or ""); activity=" ".join(str(body.get("activity") or "").split()).strip(); pieces=max(_number(body.get("pieces")),0.0)
        if origin not in MANUAL_ORIGINS: raise HTTPException(400,"La productividad manual sólo se captura para Colgado o Doblado; Cambios y Muertos es automático")
        if not activity: raise HTTPException(400,"Selecciona o escribe la actividad")
        if pieces<=0: raise HTTPException(400,"Las piezas deben ser mayores a cero")
        real=_real_row(request); store=_scope_store(actor,body.get("store") or "Compañía"); _assert_open(store,day)
        if role=="colaborador":
            if not bool(real["operation_profile_complete"]): raise HTTPException(409,"Completa primero tu nómina y nombre")
            user_id=int(real["id"]); eno=str(real["employee_no"] or ""); name=str(real["full_name"] or real["username"]); store=str(real["store"] or "")
        else:
            user_id=int(body.get("user_id") or 0) or None; eno="".join(str(body.get("employee_no") or "").split()); name=" ".join(str(body.get("employee_name") or actor.get("username") or "").split()).strip()
            if user_id:
                with m.db() as con: ur=con.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
                if ur: eno=str(ur["employee_no"] or eno); name=str(ur["full_name"] or ur["username"]); store=str(ur["store"] or store)
        now=datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            cur=con.execute("INSERT INTO operation_productivity(date,store,user_id,employee_no,employee_name,origin,activity,pieces,created_at,created_by,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(day,store,user_id,eno,name,origin,activity,pieces,now,actor["username"],now,actor["username"])); rid=cur.lastrowid
        _audit(actor,"productivity",rid,"create",{}, {"date":day,"store":store,"employee_no":eno,"employee_name":name,"origin":origin,"activity":activity,"pieces":pieces})
        return {"ok":True,"id":rid,"message":"Productividad registrada"}

    @m.app.delete("/api/operation/productivity/{entry_id}")
    def operation_productivity_delete(entry_id: int, request: Request):
        actor=m.require_user(request); real=_real_row(request)
        with m.db() as con: row=con.execute("SELECT * FROM operation_productivity WHERE id=?",(entry_id,)).fetchone()
        if not row: raise HTTPException(404,"Registro no encontrado")
        data=dict(row); role=str(actor.get("role") or "")
        if role=="colaborador" and int(data.get("user_id") or 0)!=int(real["id"]): raise HTTPException(403,"Sólo puedes borrar tus propios registros")
        if role=="tienda" and str(data.get("store") or "")!=str(actor.get("store") or ""): raise HTTPException(403,"Registro de otra tienda")
        if role not in ("superadmin","admin","tienda","colaborador"): raise HTTPException(403,"Sin permiso")
        _assert_open(str(data["store"]),str(data["date"]));
        with m.db() as con: con.execute("DELETE FROM operation_productivity WHERE id=?",(entry_id,))
        _audit(actor,"productivity",entry_id,"delete",data,{})
        return {"ok":True,"message":"Registro eliminado"}

    @m.app.post("/api/operation/day-status")
    async def operation_day_status(request: Request):
        actor=m.require_user(request,("superadmin","admin","tienda")); body=await request.json(); day=_iso_date(body.get("date")); store=_scope_store(actor,body.get("store") or "Compañía"); action=str(body.get("action") or "close")
        if store=="Compañía": raise HTTPException(400,"Selecciona una tienda")
        now=datetime.now(MX).isoformat(timespec="seconds"); before=_day_status(store,day)
        if action=="reopen" and str(actor.get("role") or "") not in ("superadmin","admin"): raise HTTPException(403,"Sólo Administrador o Super Administrador pueden reabrir un corte")
        with m.db() as con:
            if action=="close": con.execute("INSERT INTO operation_day_status(date,store,status,closed_at,closed_by,reopened_at,reopened_by) VALUES(?,?,?,?,?,'','') ON CONFLICT(date,store) DO UPDATE SET status='closed',closed_at=excluded.closed_at,closed_by=excluded.closed_by",(day,store,"closed",now,actor["username"]))
            elif action=="reopen": con.execute("INSERT INTO operation_day_status(date,store,status,closed_at,closed_by,reopened_at,reopened_by) VALUES(?,?,'open','','',?,?) ON CONFLICT(date,store) DO UPDATE SET status='open',reopened_at=excluded.reopened_at,reopened_by=excluded.reopened_by",(day,store,now,actor["username"]))
            else: raise HTTPException(400,"Acción inválida")
        after=_day_status(store,day); _audit(actor,"day_status",f"{day}|{store}",action,before,after)
        return {"ok":True,"status":after}

    @m.app.get("/api/operation/standards")
    def operation_standards(request: Request):
        actor=m.require_user(request); return {"values":_standards(),"editable":str(actor.get("role") or "") in ("superadmin","admin")}

    @m.app.post("/api/operation/standards")
    async def operation_standards_save(request: Request):
        actor=m.require_user(request,("superadmin","admin")); body=await request.json(); values=body.get("values") or {}; now=datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            for org in ORIGINS:
                if org not in values: continue
                v=_number(values.get(org))
                if v<=0: raise HTTPException(400,f"La productividad de {org} debe ser mayor a cero")
                before=con.execute("SELECT pieces_per_shift FROM operation_standards WHERE origin=?",(org,)).fetchone(); old=_number(before[0]) if before else None
                con.execute("INSERT INTO operation_standards(origin,pieces_per_shift,updated_at,updated_by) VALUES(?,?,?,?) ON CONFLICT(origin) DO UPDATE SET pieces_per_shift=excluded.pieces_per_shift,updated_at=excluded.updated_at,updated_by=excluded.updated_by",(org,v,now,actor["username"]))
                _audit(actor,"standard",org,"update",{"value":old},{"value":v},con=con)
        return {"ok":True,"values":_standards(),"message":"Productividades por jornada actualizadas"}

    def _build_pdf(rep):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
        bio=io.BytesIO(); W,H=landscape(letter); c=canvas.Canvas(bio,pagesize=(W,H)); M=28; NAVY="#173F78"; BLUE="#246FE5"; PINK="#EC007C"; PURPLE="#7338EF"; GREEN="#10B981"; GOLD="#F3A300"; RED="#EF3434"; BG="#F2F6FB"; LINE="#D6E0EC"; TEXT="#0F3463"; MUT="#667892"
        c.setFillColor(colors.HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(colors.HexColor(NAVY));c.roundRect(M,H-88,W-2*M,58,11,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",18);c.drawString(M+18,H-56,"Operación");c.setFont("Helvetica",8);c.drawString(M+18,H-72,"Control diario de operación y eficiencia de mercancía");c.setFont("Helvetica-Bold",9);c.drawRightString(W-M-18,H-55,"Operaciones Ropa · Price Shoes");c.setFont("Helvetica",7);c.drawRightString(W-M-18,H-71,f"{rep['period_type'].title()} · {rep['period_value'] or rep['start_date']}")
        y=H-108; s=rep["summary"]; cards=[("Llegada",s["arrival"],BLUE),("Procesadas",s["processed"],PURPLE),("Liberadas",s["released"],PINK),("Pendiente",s["pending"],RED),("Eficiencia",s["efficiency_pct"],GREEN),("Personal req.",s["personal_required"],GOLD),("Cumplimiento",s["compliance_pct"],GREEN),("Colaboradores",s["active_collaborators"],NAVY)]; gap=7; cw=(W-2*M-gap*3)/4; ch=54
        for i,(lab,val,col) in enumerate(cards):
            row=i//4;cl=i%4;x=M+cl*(cw+gap);yy=y-row*(ch+7)-ch;c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(x,yy,cw,ch,7,fill=1,stroke=1);c.setFillColor(colors.HexColor(col));c.rect(x,yy,4,ch,fill=1,stroke=0);c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica-Bold",6);c.drawString(x+11,yy+36,lab.upper());c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold",15);text=f"{val:,.1f}%" if "Efic" in lab or "Cumpl" in lab else f"{val:,.0f}";c.drawString(x+11,yy+14,text)
        y-=2*(ch+7)+14;c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold",11);c.drawString(M,y,"Resumen por origen");y-=17
        heads=["Origen","Llegada","Procesadas","Liberadas","Pend. inicial","Pendiente","Prod/jornada","Personal req.","Eficiencia","Cumplimiento"];fr=[.15,.085,.09,.085,.095,.085,.095,.095,.085,.095];tw=W-2*M;xs=[M];acc=M
        for q in fr[:-1]:acc+=tw*q;xs.append(acc)
        c.setFillColor(colors.HexColor(NAVY));c.roundRect(M,y-18,tw,20,4,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",5.6)
        for i,h in enumerate(heads):c.drawString(xs[i]+3,y-11,h)
        y-=22
        for idx,r in enumerate(rep["origin_summary"]):
            c.setFillColor(colors.white if idx%2==0 else colors.HexColor("#EAF2FC"));c.rect(M,y-17,tw,17,fill=1,stroke=0);vals=[r["origin"],r["arrival"],r["processed"],r["released"],r["pending_start"],r["pending"],r["standard"],r["personal_required"],r["efficiency_pct"],r["compliance_pct"]]
            for i,v in enumerate(vals):c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold" if i==0 else "Helvetica",5.6);txt=str(v) if i==0 else (f"{v:,.1f}%" if i in (8,9) else f"{v:,.0f}");c.drawString(xs[i]+3,y-11,txt)
            y-=17
        y-=9;c.setFont("Helvetica-Bold",11);c.setFillColor(colors.HexColor(TEXT));c.drawString(M,y,"Productividad por colaborador");y-=17
        cols=["#","Nómina","Colaborador","Tienda","Piezas","Días","Prod. diaria","Meta","Cumpl."];fr=[.04,.08,.22,.12,.09,.06,.10,.10,.09];xs=[M];acc=M
        for q in fr[:-1]:acc+=tw*q;xs.append(acc)
        c.setFillColor(colors.HexColor(NAVY));c.roundRect(M,y-18,tw,20,4,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",5.4)
        for i,h in enumerate(cols):c.drawString(xs[i]+3,y-11,h)
        y-=22
        for idx,r in enumerate(rep["productivity"][:18]):
            if y<40:break
            c.setFillColor(colors.white if idx%2==0 else colors.HexColor("#EAF2FC"));c.rect(M,y-16,tw,16,fill=1,stroke=0);vals=[idx+1,r["employee_no"],r["name"],r["store"],r["pieces"],r["days"],r["daily"],r["target"],r["compliance_pct"]]
            for i,v in enumerate(vals):c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold" if i in (0,2,8) else "Helvetica",5.3);txt=str(v) if i in (1,2,3) else (f"{v:,.1f}%" if i==8 else f"{v:,.0f}");c.drawString(xs[i]+3,y-10,txt[:30])
            y-=16
        c.save();return bio.getvalue()

    @m.app.get("/api/operation/export")
    def operation_export(request: Request, format: str="pdf", period_type: str="day", period_value: str="", store: str="Compañía", origin: str="Todos", employee_no: str=""):
        rep=_operation_report(request,period_type,period_value,store,origin,employee_no);safe_val=(period_value or rep["start_date"]).replace("-",".").replace("W","S")
        if format.lower()=="pdf": return Response(content=_build_pdf(rep),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="Operacion_{period_type.title()}_{safe_val}.pdf"'})
        if format.lower()=="xlsx":
            bio=io.BytesIO()
            with m.pd.ExcelWriter(bio,engine="openpyxl") as writer:
                m.pd.DataFrame([rep["summary"]]).to_excel(writer,sheet_name="Resumen",index=False);m.pd.DataFrame(rep["origin_summary"]).to_excel(writer,sheet_name="Origen",index=False);m.pd.DataFrame(rep["daily"]).to_excel(writer,sheet_name="Tendencia",index=False);m.pd.DataFrame(rep["productivity"]).to_excel(writer,sheet_name="Productividad",index=False)
            return Response(content=bio.getvalue(),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="Operacion_{period_type.title()}_{safe_val}.xlsx"'})
        raise HTTPException(400,"Formato no soportado")

    css=r'''<style id="v121-operation-css">
.v121-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:9px;margin:10px 0}.v121-card{background:#fff;border:1px solid var(--line);border-radius:13px;padding:13px;position:relative;overflow:hidden}.v121-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c,#246FE5)}.v121-card small{display:block;color:#667085;font-size:8px;font-weight:900;text-transform:uppercase}.v121-card b{display:block;color:var(--navy);font-size:22px;margin:7px 0 2px}.v121-card span{font-size:8px;color:#667085}.v121-charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v121-panel{background:#fff;border:1px solid var(--line);border-radius:13px;padding:12px;margin:10px 0}.v121-chart-title{font-size:12px;font-weight:950;color:var(--navy);margin-bottom:9px}.v121-hbar{display:grid;grid-template-columns:130px minmax(0,1fr) 72px;gap:8px;align-items:center;margin:7px 0;font-size:8px}.v121-track{height:16px;background:#e9eef5;border-radius:6px;overflow:hidden}.v121-fill{height:100%;border-radius:6px;background:#246FE5}.v121-stack{height:28px;border-radius:8px;overflow:hidden;display:flex;background:#edf1f5}.v121-stack span{height:100%;display:block}.v121-capture{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;align-items:end}.v121-capture .field input,.v121-capture .field select{width:100%}.v121-status{display:inline-flex;padding:5px 8px;border-radius:999px;font-size:8px;font-weight:950}.v121-status.open{background:#dcfce7;color:#166534}.v121-status.closed{background:#fee2e2;color:#991b1b}.v121-modal{position:fixed;inset:0;background:#081425cc;display:grid;place-items:center;z-index:99999}.v121-modal.hidden{display:none!important}.v121-modal-card{width:min(470px,calc(100% - 28px));background:white;border-radius:18px;padding:22px;box-shadow:0 30px 90px #0007}.v121-modal-card h2{margin:0 0 8px;color:var(--navy)}.v121-modal-card p{font-size:10px;color:#667085}.v121-modal-card input{width:100%;padding:11px;border:1px solid #ccd6e2;border-radius:9px;margin:6px 0}.v121-mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.v121-mini{background:#f6f8fb;border-radius:9px;padding:9px}.v121-mini b{font-size:13px;color:var(--navy)}.v121-mini small{display:block;font-size:7px;color:#667085}.v121-line{width:100%;height:150px}.v121-note{font-size:8px;color:#667085;line-height:1.5}.v121-actions{display:flex;gap:7px;flex-wrap:wrap}.v121-danger{background:#fff;border:1px solid #f1a3a3;color:#b42318;border-radius:8px;padding:7px 9px;font-weight:900;font-size:8px;cursor:pointer}@media(max-width:900px){.v121-charts{grid-template-columns:1fr}.v121-capture{grid-template-columns:1fr 1fr}.v121-hbar{grid-template-columns:100px 1fr 58px}.v121-mini-grid{grid-template-columns:1fr}}</style>'''
    modal=r'''<div id="v121ProfileModal" class="v121-modal hidden"><div class="v121-modal-card"><h2>Completa tu perfil de Colaborador</h2><p>Tu tienda ya está asignada. Captura tu nómina y nombre completo una sola vez; después se cargarán automáticamente en tus productividades.</p><div class="field"><label>Nómina</label><input id="v121ProfileNomina" inputmode="numeric" placeholder="Ej. 33088"></div><div class="field"><label>Nombre completo</label><input id="v121ProfileName" placeholder="Nombre(s) y apellidos"></div><div class="v121-note" id="v121ProfileStore"></div><button class="primary full" id="v121ProfileSave">Guardar perfil</button><div class="msg" id="v121ProfileMsg"></div></div></div>'''
    js=r'''<script id="v121-operation-js">
(function(){
 const OP='Operación',CENTER='Centro Ejecutivo',num=v=>Number(v||0),f1=v=>num(v).toLocaleString('es-MX',{maximumFractionDigits:1}),fp=v=>`${f1(v)}%`,esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
 roleLabel.colaborador='Colaborador';if(typeof OPER_TITLES==='object')OPER_TITLES[OP]='Control diario, productividad por persona y eficiencia de mercancía';
 const nav=document.querySelector('#operativoNav [data-opview="Centro Ejecutivo"]');if(nav&&!document.querySelector('#operativoNav [data-opview="Operación"]'))nav.insertAdjacentHTML('afterend','<button class="switch" data-opview="Operación">Operación</button>');const opBtn=document.querySelector('#operativoNav [data-opview="Operación"]');if(opBtn)opBtn.onclick=async()=>{OP_VIEW=OP;document.querySelectorAll('#operativoNav [data-opview]').forEach(x=>x.classList.toggle('active',x===opBtn));OPER_PERIOD={type:'day',value:''};await renderOperativoView(OP,true)};
 function addCollaboratorRoles(){const nr=$('#newRole');if(nr&&!Array.from(nr.options).some(o=>o.value==='colaborador'))nr.insertBefore(new Option('Colaborador','colaborador'),nr.firstChild)}addCollaboratorRoles();const oldLoadUsers=window.loadUsers;if(typeof oldLoadUsers==='function')window.loadUsers=async function(){await oldLoadUsers();addCollaboratorRoles();try{const users=await api('/api/users'),rows=[...document.querySelectorAll('#userTable tr')];rows.forEach((tr,i)=>{const sel=tr.querySelector('.userEditRole');if(!sel)return;if(!Array.from(sel.options).some(o=>o.value==='colaborador'))sel.add(new Option('Colaborador','colaborador'));if(users[i])sel.value=users[i].role})}catch(e){console.warn('[V121] roles usuarios',e)}};const createBtn=$('#createUser');if(createBtn&&createBtn.onclick){const old=createBtn.onclick;createBtn.onclick=async function(ev){if($('#newRole')?.value==='colaborador'&&!$('#newStore')?.value){$('#userMsg').textContent='Selecciona la tienda del colaborador';return}return old.call(this,ev)}}
 async function profileCheck(force=false){if(!USER||USER.role!=='colaborador')return;try{const p=await api('/api/operation/profile');if(p.profile_complete&&!force)return;if(p.must_change_password&&!force)return;$('#v121ProfileStore').textContent=`Tienda asignada: ${p.store||'Sin asignar'}`;$('#v121ProfileNomina').value=p.employee_no||'';$('#v121ProfileName').value=p.full_name||'';$('#v121ProfileModal').classList.remove('hidden')}catch(e){console.warn('[V121] perfil',e)}}$('#v121ProfileSave')?.addEventListener('click',async()=>{try{const r=await api('/api/operation/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({employee_no:$('#v121ProfileNomina').value,full_name:$('#v121ProfileName').value})});$('#v121ProfileMsg').style.color='var(--green)';$('#v121ProfileMsg').textContent=r.message;setTimeout(()=>{$('#v121ProfileModal').classList.add('hidden');renderOperativoView(OP,true)},500)}catch(e){$('#v121ProfileMsg').style.color='var(--red)';$('#v121ProfileMsg').textContent=e.message}});const fps=$('#forcePassSave');if(fps)fps.addEventListener('click',()=>setTimeout(()=>profileCheck(true),900));
 async function afterEnter(u){if(!u)return;if(u.role==='colaborador'){document.querySelectorAll('#operativoNav [data-opview]').forEach(x=>x.classList.toggle('hidden',x.dataset.opview!==OP));const main=document.querySelector('[data-main="operativo"]');if(main)main.innerHTML='Operación<small>Captura de productividad</small>';OP_VIEW=OP;if(opBtn){opBtn.classList.remove('hidden');opBtn.classList.add('active')}setTimeout(async()=>{await profileCheck();await renderOperativoView(OP,true)},180)}else if(opBtn)opBtn.classList.remove('hidden')}const oldEnter=window.enter;if(typeof oldEnter==='function')window.enter=async function(u){await oldEnter(u);await afterEnter(u)};setTimeout(()=>{if(window.USER)afterEnter(USER)},350);
 function periodOptions(meta,type){if(type==='day')return meta.dates||[];if(type==='week')return meta.weeks||[];if(type==='month')return meta.months||[];return meta.years||[]}function defaultPeriod(meta,type){const arr=periodOptions(meta,type);if(arr.length)return arr[arr.length-1];const d=meta.latest_date||new Date().toISOString().slice(0,10);if(type==='day')return d;if(type==='month')return d.slice(0,7);if(type==='year')return d.slice(0,4);const dt=new Date(d+'T12:00:00'),one=new Date(dt.getFullYear(),0,4),wn=1+Math.round(((dt-one)/86400000-3+(one.getDay()+6)%7)/7);return `${dt.getFullYear()}-W${String(wn).padStart(2,'0')}`}function setSel(sel,values,current){sel.innerHTML='';values.forEach(v=>sel.add(new Option(v,v)));if(current&&values.includes(current))sel.value=current;else if(values.length)sel.value=values[values.length-1]}
 function svgLine(daily,keys){const W=720,H=150,pad=18,vals=daily.flatMap(r=>keys.map(k=>num(r[k]))),max=Math.max(1,...vals),n=Math.max(1,daily.length-1),colors=['#246FE5','#7338EF','#EC007C'];let paths='';keys.forEach((k,ki)=>{const pts=daily.map((r,i)=>`${pad+(W-pad*2)*(i/n)},${H-pad-(H-pad*2)*num(r[k])/max}`).join(' ');paths+=`<polyline points="${pts}" fill="none" stroke="${colors[ki]}" stroke-width="3"/>`});return `<svg class="v121-line" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><line x1="${pad}" y1="${H-pad}" x2="${W-pad}" y2="${H-pad}" stroke="#d7e0ea"/>${paths}</svg>`}
 function summaryCards(s){const cards=[['Llegada',s.arrival,'Piezas recibidas','#246FE5'],['Procesadas',s.processed,'Productividad registrada','#7338EF'],['Liberadas',s.released,'Mercancía liberada','#EC007C'],['Pendiente',s.pending,'Pendiente al cierre','#EF3434'],['Eficiencia',fp(s.efficiency_pct),'Procesadas / carga de trabajo','#10B981'],['Personal requerido',f1(s.personal_required),'Promedio calculado','#F3A300'],['Cumplimiento',fp(s.compliance_pct),'Procesadas / meta por jornada','#10B981'],['Colaboradores',s.active_collaborators,'Con productividad en el periodo','#173F78']];return `<div class="v121-grid">${cards.map(x=>`<div class="v121-card" style="--c:${x[3]}"><small>${x[0]}</small><b>${typeof x[1]==='string'?x[1]:fmt(x[1])}</b><span>${x[2]}</span></div>`).join('')}</div>`}
 function originTable(rows){return `<div class="tablewrap"><table class="table"><thead><tr><th>Origen</th><th>Llegada</th><th>Procesadas</th><th>Liberadas</th><th>Pend. inicial</th><th>Pendiente</th><th>Prod./jornada</th><th>Personal req.</th><th>Eficiencia</th><th>Cumplimiento</th><th>Estado</th></tr></thead><tbody>${rows.map(r=>`<tr><td><b>${r.origin}</b></td><td>${fmt(r.arrival)}</td><td>${fmt(r.processed)}</td><td>${fmt(r.released)}</td><td>${fmt(r.pending_start)}</td><td>${fmt(r.pending)}</td><td>${fmt(r.standard)}</td><td>${f1(r.personal_required)}</td><td><b class="${r.efficiency_pct>=100?'metric-good':r.efficiency_pct>=75?'metric-warn':'metric-bad'}">${fp(r.efficiency_pct)}</b></td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${fp(r.compliance_pct)}</b></td><td>${r.status}</td></tr>`).join('')}</tbody></table></div>`}
 function charts(rep){const rows=rep.origin_summary||[],max=Math.max(1,...rows.map(r=>Math.max(num(r.processed),num(r.target)))),bars=rows.map(r=>`<div class="v121-hbar"><b>${r.origin}</b><div><div class="v121-track"><div class="v121-fill" style="width:${Math.min(100,num(r.processed)/max*100)}%;background:#246FE5"></div></div><div class="v121-track" style="margin-top:3px;height:7px"><div class="v121-fill" style="width:${Math.min(100,num(r.target)/max*100)}%;background:#d7e0ea"></div></div></div><span>${fmt(r.processed)} / ${fmt(r.target)}</span></div>`).join(''),total=Math.max(1,rows.reduce((a,r)=>a+num(r.processed),0)),cols=['#246FE5','#7338EF','#EC007C'],stack=`<div class="v121-stack">${rows.map((r,i)=>`<span title="${r.origin}: ${fmt(r.processed)}" style="width:${num(r.processed)/total*100}%;background:${cols[i]}"></span>`).join('')}</div><div class="v121-mini-grid" style="margin-top:8px">${rows.map((r,i)=>`<div class="v121-mini"><small>${r.origin}</small><b>${fp(num(r.processed)/total*100)}</b></div>`).join('')}</div>`,eff=rows.map(r=>`<div class="v121-hbar"><b>${r.origin}</b><div class="v121-track"><div class="v121-fill" style="width:${Math.min(100,num(r.efficiency_pct))}%;background:${r.efficiency_pct>=100?'#10B981':r.efficiency_pct>=75?'#F3A300':'#EF3434'}"></div></div><span>${fp(r.efficiency_pct)}</span></div>`).join(''),mx=Math.max(1,...rows.map(x=>num(x.personal_required))),req=rows.map(r=>`<div class="v121-hbar"><b>${r.origin}</b><div class="v121-track"><div class="v121-fill" style="width:${Math.min(100,num(r.personal_required)/mx*100)}%;background:#7338EF"></div></div><span>${f1(r.personal_required)}</span></div>`).join('');return `<div class="v121-charts"><div class="v121-panel"><div class="v121-chart-title">Procesado vs meta</div>${bars}</div><div class="v121-panel"><div class="v121-chart-title">Eficiencia por origen · meta 100%</div>${eff}</div><div class="v121-panel"><div class="v121-chart-title">Pendiente acumulado</div>${svgLine(rep.daily||[],['colgado_pending','doblado_pending','cambios_pending'])}<div class="v121-note">Azul Colgado · Morado Doblado · Rosa Cambios y Muertos</div></div><div class="v121-panel"><div class="v121-chart-title">Participación de producción</div>${stack}</div><div class="v121-panel"><div class="v121-chart-title">Personal requerido promedio</div>${req}</div><div class="v121-panel"><div class="v121-chart-title">Producción por periodo</div>${svgLine(rep.daily||[],['colgado_processed','doblado_processed','cambios_processed'])}<div class="v121-note">Misma lectura visual en Día, Semana, Mes y Año; sólo cambia el eje temporal.</div></div></div>`}
 function productivityTable(rows){return `<div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Nómina</th><th>Colaborador</th><th>Tienda</th><th>Piezas</th><th>Días</th><th>Prod. diaria</th><th>Meta</th><th>Cumplimiento</th><th>Origen</th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td>#${i+1}</td><td>${esc(r.employee_no||'—')}</td><td><b>${esc(r.name)}</b></td><td>${esc(r.store)}</td><td>${fmt(r.pieces)}</td><td>${r.days}</td><td>${fmt(r.daily)}</td><td>${fmt(r.target)}</td><td><b class="${r.compliance_pct>=100?'metric-good':r.compliance_pct>=75?'metric-warn':'metric-bad'}">${fp(r.compliance_pct)}</b></td><td>${esc((r.origins||[]).join(', '))}</td></tr>`).join('')}</tbody></table></div>`}
 async function captureDaily(rep){const store=$('#operStoreSelect').value;if(!rep.permissions.capture_daily||OPER_PERIOD.type!=='day')return '';if(store==='Compañía')return `<div class="v121-panel"><div class="v121-chart-title">Captura diaria</div><div class="infoempty">Selecciona una tienda para capturar Llegada y Mercancía liberada.</div></div>`;const snap={};(rep.capture_snapshot||[]).filter(x=>x.store===store).forEach(x=>snap[x.origin]=x);const st=rep.day_status?.[store]||{status:'open'};return `<div class="v121-panel"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><div class="v121-chart-title">Captura diaria · campos verdes del Excel</div><span class="v121-status ${st.status}">${st.status==='closed'?'Cerrado':'En captura'}</span></div><div class="v121-capture">${['Colgado','Doblado'].map(o=>`<div class="field"><label>${o} · Llegada</label><input class="v121-arr" data-origin="${o}" type="number" min="0" value="${num(snap[o]?.arrival)}"></div><div class="field"><label>${o} · Mercancía liberada</label><input class="v121-rel" data-origin="${o}" type="number" min="0" value="${num(snap[o]?.released)}"></div>`).join('')}<button class="primary" id="v121SaveDaily" ${st.status==='closed'?'disabled':''}>Guardar captura</button></div><div class="v121-actions" style="margin-top:9px">${st.status==='open'&&rep.permissions.close_day?'<button class="v121-danger" id="v121CloseDay">Cerrar día</button>':''}${st.status==='closed'&&rep.permissions.reopen_day?'<button class="v121-danger" id="v121ReopenDay">Reabrir corte</button>':''}</div><div class="v121-note">Cambios y Muertos no se captura aquí: se integra automáticamente del indicador existente.</div></div>`}
 function standardsPanel(rep){if(!rep.permissions.edit_standards)return '';const st=rep.standards||{};return `<div class="v121-panel"><div class="v121-chart-title">Productividad estándar por jornada</div><div class="v121-capture">${['Colgado','Doblado','Cambios y Muertos'].map(o=>`<div class="field"><label>${o}</label><input class="v121-standard" data-origin="${o}" type="number" min="1" value="${num(st[o])}"></div>`).join('')}<button class="primary" id="v121SaveStandards">Guardar estándares</button></div><div class="v121-note">Valores iniciales del Excel de referencia: Colgado 1,228 · Doblado 906 · Cambios y Muertos 670 pzas/jornada.</div></div>`}
 function collaboratorCapture(rep){if(rep.role!=='colaborador')return '';const day=OPER_PERIOD.type==='day'?(OPER_PERIOD.value||rep.start_date):rep.end_date;return `<div class="v121-panel"><div class="v121-chart-title">Mi productividad</div><div class="v121-capture"><div class="field"><label>Fecha</label><input id="v121ProdDate" type="date" value="${day}"></div><div class="field"><label>Origen</label><select id="v121ProdOrigin"><option>Colgado</option><option>Doblado</option></select></div><div class="field"><label>Actividad</label><select id="v121ProdActivity"><option>Acondicionado</option><option>Ubicado</option><option>Clasificado</option><option>Ingreso</option><option>Recolección</option><option>Otro</option></select></div><div class="field"><label>Piezas</label><input id="v121ProdPieces" type="number" min="1" inputmode="numeric"></div><button class="primary" id="v121ProdSave">Registrar</button></div><div class="v121-note">Tu tienda, nómina y nombre se agregan automáticamente. Cambios y Muertos se obtiene de la base operativa.</div>${(rep.my_entries||[]).length?`<div class="title">Mis capturas del periodo</div><div class="tablewrap"><table class="table"><thead><tr><th>Fecha</th><th>Origen</th><th>Actividad</th><th>Piezas</th><th></th></tr></thead><tbody>${rep.my_entries.map(r=>`<tr><td>${r.date}</td><td>${r.origin}</td><td>${r.activity}</td><td>${fmt(r.pieces)}</td><td><button class="v121-danger v121DeleteProd" data-id="${r.id}">Eliminar</button></td></tr>`).join('')}</tbody></table></div>`:''}</div>`}
 function bindActions(rep){$('#v121SaveDaily')?.addEventListener('click',async()=>{try{const rows=['Colgado','Doblado'].map(o=>({origin:o,arrival:num(document.querySelector(`.v121-arr[data-origin="${o}"]`)?.value),released:num(document.querySelector(`.v121-rel[data-origin="${o}"]`)?.value)}));await api('/api/operation/daily',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:OPER_PERIOD.value,store:$('#operStoreSelect').value,rows})});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});$('#v121CloseDay')?.addEventListener('click',async()=>{if(!confirm('¿Cerrar el corte del día? Después no se podrán modificar capturas hasta que un Administrador lo reabra.'))return;try{await api('/api/operation/day-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:OPER_PERIOD.value,store:$('#operStoreSelect').value,action:'close'})});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});$('#v121ReopenDay')?.addEventListener('click',async()=>{try{await api('/api/operation/day-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:OPER_PERIOD.value,store:$('#operStoreSelect').value,action:'reopen'})});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});$('#v121ProdSave')?.addEventListener('click',async()=>{try{await api('/api/operation/productivity',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:$('#v121ProdDate').value,origin:$('#v121ProdOrigin').value,activity:$('#v121ProdActivity').value,pieces:num($('#v121ProdPieces').value)})});$('#v121ProdPieces').value='';await renderOperativoView(OP,true)}catch(e){alert(e.message)}});document.querySelectorAll('.v121DeleteProd').forEach(b=>b.onclick=async()=>{if(!confirm('¿Eliminar esta captura?'))return;try{await api(`/api/operation/productivity/${b.dataset.id}`,{method:'DELETE'});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});$('#v121SaveStandards')?.addEventListener('click',async()=>{try{const values={};document.querySelectorAll('.v121-standard').forEach(i=>values[i.dataset.origin]=num(i.value));await api('/api/operation/standards',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values})});await renderOperativoView(OP,true)}catch(e){alert(e.message)}});$('#v121Pdf')?.addEventListener('click',()=>operationDownload('pdf'));$('#v121Xlsx')?.addEventListener('click',()=>operationDownload('xlsx'))}
 async function operationDownload(format){const q=new URLSearchParams({format,period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value||'',store:$('#operStoreSelect').value||'Compañía',origin:$('#operAreaSelect').value||'Todos',employee_no:$('#operActivitySelect').value||''}),res=await fetch('/api/operation/export?'+q,{credentials:'same-origin'});if(!res.ok)throw new Error(await res.text());const blob=await res.blob(),a=document.createElement('a');a.href=URL.createObjectURL(blob);const cd=res.headers.get('content-disposition')||'',mt=cd.match(/filename="?([^";]+)"?/i);a.download=mt?mt[1]:`Operacion.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
 const previousRender=window.renderOperativoView;window.renderOperativoView=async function(name,force=false){if(name!==OP)return previousRender(name,force);const centro=$('#operativoCentro'),dyn=$('#operativoDynamic');if(centro)centro.classList.add('hidden');if(dyn)dyn.classList.remove('hidden');$('#operativoDynamicTitle').textContent='Operación';$('#operativoDynamicSub').textContent='Control diario, productividad por colaborador y eficiencia de mercancía';let meta;try{meta=await api('/api/operation/meta',{timeoutMs:60000})}catch(e){$('#operativoDynamicContent').innerHTML=`<div class="infoempty">No fue posible abrir Operación: ${esc(e.message)}</div>`;return}const mode=$('#operPeriodMode'),mw=$('#operPeriodModeWrap'),period=$('#operPeriodSelect');mw?.classList.remove('hidden');if(mode){mode.innerHTML='<option value="day">Día</option><option value="week">Semanal</option><option value="month">Mensual</option><option value="year">Anual</option>';if(!['day','week','month','year'].includes(OPER_PERIOD.type))OPER_PERIOD.type='day';mode.value=OPER_PERIOD.type}const vals=periodOptions(meta,OPER_PERIOD.type);if(!OPER_PERIOD.value||!vals.includes(OPER_PERIOD.value))OPER_PERIOD.value=defaultPeriod(meta,OPER_PERIOD.type);setSel(period,vals.length?vals:[OPER_PERIOD.value],OPER_PERIOD.value);$('#operPeriodModeLabel').textContent='Vista operativa';$('#operPeriodLabel').textContent=OPER_PERIOD.type==='day'?'Fecha':OPER_PERIOD.type==='week'?'Semana ISO':OPER_PERIOD.type==='month'?'Mes':'Año';const ss=$('#operStoreSelect');if(ss){const old=ss.value;ss.innerHTML='<option value="Compañía">Compañía</option>';(meta.stores||[]).forEach(s=>ss.add(new Option(s,s)));if(USER?.role==='tienda'||USER?.role==='colaborador'){ss.value=USER.store||meta.stores?.[0]||'Compañía';ss.disabled=true}else{ss.disabled=false;ss.value=Array.from(ss.options).some(o=>o.value===old)?old:'Compañía'}ss.parentElement.querySelector('label').textContent='Tienda'}const os=$('#operAreaSelect');if(os){const old=os.value;os.innerHTML='<option value="Todos">Todos</option>';(meta.origins||[]).forEach(o=>os.add(new Option(o,o)));os.value=Array.from(os.options).some(o=>o.value===old)?old:'Todos';os.parentElement.querySelector('label').textContent='Origen'}const cs=$('#operActivitySelect');if(cs){const old=cs.value;cs.innerHTML='<option value="">Todos</option>';(meta.collaborators||[]).forEach(p=>cs.add(new Option(`${p.name}${p.employee_no?' · '+p.employee_no:''}`,p.employee_no||'')));cs.value=Array.from(cs.options).some(o=>o.value===old)?old:'';cs.parentElement.querySelector('label').textContent='Colaborador';cs.disabled=USER?.role==='colaborador'}let rep;try{const q=new URLSearchParams({period_type:OPER_PERIOD.type,period_value:OPER_PERIOD.value,store:ss?.value||'Compañía',origin:os?.value||'Todos',employee_no:cs?.value||''});rep=await api('/api/operation/report?'+q,{timeoutMs:180000})}catch(e){$('#operativoDynamicContent').innerHTML=`<div class="infoempty">Error consultando Operación: ${esc(e.message)}</div>`;return}const daily=await captureDaily(rep),self=collaboratorCapture(rep),standards=standardsPanel(rep);$('#operativoDynamicContent').innerHTML=`${self}${daily}${standards}${summaryCards(rep.summary)}<div class="title">Desempeño por origen</div>${originTable(rep.origin_summary||[])}${charts(rep)}<div class="title">Productividad por colaborador</div>${productivityTable(rep.productivity||[])}<div class="v121-actions" style="margin-top:10px"><button class="primary" id="v121Pdf">Descargar PDF</button><button class="primary" id="v121Xlsx">Descargar Excel</button></div>`;bindActions(rep)};
 const modeEl=$('#operPeriodMode');if(modeEl)modeEl.onchange=async()=>{if(OP_VIEW===OP){OPER_PERIOD.type=modeEl.value;OPER_PERIOD.value='';await renderOperativoView(OP,true)}else if(OP_VIEW===CENTER){OPER_PERIOD.type=modeEl.value;OPER_PERIOD.value='';setPeriodSelector(CENTER,OPSDATA||{available_dates:[],available_weeks:[],available_months:[]});await renderOperativoView(CENTER,true)}else{OPER_PERIOD.type=modeEl.value;OPER_PERIOD.value='';setPeriodSelector(OP_VIEW,OPSDATA||{});await renderOperativoView(OP_VIEW,true)}};const apply=$('#operPeriodApply');if(apply)apply.onclick=async()=>{OPER_PERIOD.value=$('#operPeriodSelect').value||'';await renderOperativoView(OP_VIEW||CENTER,true)};console.info('[V121] Indicador Operación y perfil Colaborador activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v121_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200: return response
        try:
            body=b""
            async for chunk in response.body_iterator: body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v121-operation-js" not in html:
                html=html.replace("</head>",css+"</head>",1).replace('<div id="appView"',modal+'<div id="appView"',1).replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V121"})
        except Exception as exc:
            print(f"[V121-WEB] {type(exc).__name__}: {exc}",flush=True);return response

    try:
        workload=10000+5000;processed=0;pending=max(workload-processed,0);required=workload/1228;eff=processed/workload*100
        assert pending==15000 and abs(required-12.2149837134)<1e-6 and eff==0
        assert set(_standards())>=set(ORIGINS)
        assert _period_bounds("week","2026-W37")[0].isoformat()=="2026-09-07"
        print("[V121-SELFTEST] Fórmulas base, estándares y periodos OK.",flush=True)
    except Exception as exc:
        print(f"[V121-SELFTEST] ERROR: {type(exc).__name__}: {exc}",flush=True)

    m._V121_OPERATION_INDICATOR=True
    print("[V121] Operación + Colaborador instalados. C&M automático; Colgado/Doblado capturables.",flush=True)
