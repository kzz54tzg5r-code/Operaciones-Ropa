"""V210 · Estándares Operativos por antigüedad.

Agrega:
- 3 niveles: Nuevo ingreso, Intermedio y Experto.
- Rangos configurables por Administrador/Super Administrador con vigencia.
- Fecha de ingreso para colaboradores operativos/lencería/legado.
- Estándares Doblado/Frontal por nivel y vigencia.
- Ranking con cumplimiento contra estándar individual.
- Snapshot de nivel/estándar al finalizar una productividad temporizada.
"""
from __future__ import annotations

import calendar
import json
import math
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")
STAFF_ROLES = ("colaborador_operativo", "colaborador_lenceria", "colaborador")
LEVELS = ("Nuevo ingreso", "Intermedio", "Experto")
STANDARD_AREAS = ("Doblado", "Frontal")
RANKING_AREAS = ("Doblado", "Frontal", "Colgado", "Jeans", "Lencería")
RANKING_ACTIVITIES = ("Acondicionado", "Clasificado", "Ubicado")
PRIVILEGED = ("superadmin", "admin", "director", "consulta")


def install(m):
    if getattr(m, "_V210_OPERATIONAL_STANDARDS_TENURE", False):
        return

    now = datetime.now(MX).isoformat(timespec="seconds")
    with m.db() as con:
        user_cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(users)").fetchall()}
        if "fecha_ingreso" not in user_cols:
            con.execute("ALTER TABLE users ADD COLUMN fecha_ingreso TEXT DEFAULT ''")

        con.execute("""CREATE TABLE IF NOT EXISTS operation_experience_versions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            effective_from TEXT NOT NULL UNIQUE,
            new_cutoff_months INTEGER NOT NULL DEFAULT 3,
            expert_cutoff_months INTEGER NOT NULL DEFAULT 12,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS operation_level_standards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            effective_from TEXT NOT NULL,
            area TEXT NOT NULL,
            level TEXT NOT NULL,
            pieces_per_day REAL NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            UNIQUE(effective_from,area,level)
        )""")
        con.execute("""CREATE INDEX IF NOT EXISTS ix_operation_level_standards_lookup
            ON operation_level_standards(area,level,effective_from)""")
        con.execute(
            "INSERT OR IGNORE INTO operation_experience_versions"
            "(effective_from,new_cutoff_months,expert_cutoff_months,updated_at,updated_by)"
            " VALUES('2000-01-01',3,12,?,?)",
            (now, "system"),
        )

        for table in ("operation_productivity_timer", "operation_productivity"):
            try:
                cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(%s)" % table).fetchall()}
            except Exception:
                cols = set()
            if not cols:
                continue
            additions = (
                ("hire_date", "TEXT DEFAULT ''"),
                ("experience_level", "TEXT DEFAULT ''"),
                ("standard_value", "REAL DEFAULT 0"),
                ("standard_effective_from", "TEXT DEFAULT ''"),
            )
            for col, decl in additions:
                if col not in cols:
                    con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, decl))

    def _num(value):
        try:
            v = float(value or 0)
            return v if math.isfinite(v) else 0.0
        except Exception:
            return 0.0

    def _norm(value):
        try:
            return m.login_key(value)
        except Exception:
            return str(value or "").strip().casefold()

    def _iso_day(value, field="Fecha"):
        raw = str(value or "").strip()[:10]
        try:
            return date.fromisoformat(raw)
        except Exception:
            raise HTTPException(400, field + " inválida")

    def _real_row(request):
        actor = m.require_user(request)
        with m.db() as con:
            row = con.execute("SELECT * FROM users WHERE id=?", (actor["id"],)).fetchone()
        if not row:
            raise HTTPException(401, "Sesión requerida")
        return actor, dict(row)

    def _fallback_target():
        value = 784.0
        try:
            goals = m.get_goals() or {}
            for key in ("productividad_diaria", "productivity_daily", "productivity", "productividad"):
                n = _num(goals.get(key))
                if n > 0:
                    value = n
                    break
        except Exception:
            pass
        return value

    def _range_version(for_day):
        ds = for_day.isoformat() if isinstance(for_day, date) else str(for_day or "")[:10]
        with m.db() as con:
            row = con.execute(
                "SELECT * FROM operation_experience_versions "
                "WHERE effective_from<=? ORDER BY effective_from DESC,id DESC LIMIT 1",
                (ds,),
            ).fetchone()
            if not row:
                row = con.execute(
                    "SELECT * FROM operation_experience_versions ORDER BY effective_from,id LIMIT 1"
                ).fetchone()
        return dict(row) if row else {
            "effective_from": "2000-01-01", "new_cutoff_months": 3, "expert_cutoff_months": 12
        }

    def _add_months(d, months):
        total = d.year * 12 + (d.month - 1) + int(months)
        year, month0 = divmod(total, 12)
        month = month0 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _level_for(hire_date, for_day):
        if not hire_date:
            return "Sin fecha", _range_version(for_day)
        try:
            hire = date.fromisoformat(str(hire_date)[:10])
        except Exception:
            return "Sin fecha", _range_version(for_day)
        cfg = _range_version(for_day)
        new_cut = max(1, int(cfg.get("new_cutoff_months") or 3))
        expert_cut = max(new_cut + 1, int(cfg.get("expert_cutoff_months") or 12))
        if for_day < hire:
            return "Nuevo ingreso", cfg
        if for_day < _add_months(hire, new_cut):
            return "Nuevo ingreso", cfg
        if for_day < _add_months(hire, expert_cut):
            return "Intermedio", cfg
        return "Experto", cfg

    def _standard_for(area, level, for_day):
        fallback = _fallback_target()
        if level not in LEVELS:
            return fallback, "", "Meta general"
        ds = for_day.isoformat()
        with m.db() as con:
            row = con.execute(
                "SELECT pieces_per_day,effective_from FROM operation_level_standards "
                "WHERE area=? AND level=? AND effective_from<=? "
                "ORDER BY effective_from DESC,id DESC LIMIT 1",
                (str(area or ""), level, ds),
            ).fetchone()
        if row and _num(row["pieces_per_day"]) > 0:
            return _num(row["pieces_per_day"]), str(row["effective_from"] or ""), "Estándar operativo"
        return fallback, "", "Meta general"

    def _current_matrix(for_day):
        cfg = _range_version(for_day)
        ds = for_day.isoformat()
        matrix = {area: {} for area in STANDARD_AREAS}
        with m.db() as con:
            for area in STANDARD_AREAS:
                for level in LEVELS:
                    row = con.execute(
                        "SELECT pieces_per_day,effective_from FROM operation_level_standards "
                        "WHERE area=? AND level=? AND effective_from<=? "
                        "ORDER BY effective_from DESC,id DESC LIMIT 1",
                        (area, level, ds),
                    ).fetchone()
                    matrix[area][level] = {
                        "value": _num(row["pieces_per_day"]) if row else 0,
                        "effective_from": str(row["effective_from"] or "") if row else "",
                    }
        return cfg, matrix

    def _audit(actor, entity, key, action, before, after, con=None):
        params = (
            entity, str(key), action,
            json.dumps(before or {}, ensure_ascii=False),
            json.dumps(after or {}, ensure_ascii=False),
            datetime.now(MX).isoformat(timespec="seconds"),
            str(actor.get("username") or ""),
        )
        try:
            if con is not None:
                con.execute(
                    "INSERT INTO operation_audit(entity,entity_key,action,before_json,after_json,changed_at,changed_by)"
                    " VALUES(?,?,?,?,?,?,?)", params
                )
            else:
                with m.db() as acon:
                    acon.execute(
                        "INSERT INTO operation_audit(entity,entity_key,action,before_json,after_json,changed_at,changed_by)"
                        " VALUES(?,?,?,?,?,?,?)", params
                    )
        except Exception:
            pass

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
            return _canonical_store(req, stores)
        return "Compañía"

    def _period_bounds(period_type, period_value):
        ptype = str(period_type or "month").strip().lower()
        value = str(period_value or "").strip()
        today = datetime.now(MX).date()
        if ptype == "day":
            d = _iso_day(value or today.isoformat(), "Fecha")
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

    def _staff_map():
        result = {}
        with m.db() as con:
            rows = con.execute(
                "SELECT id,username,role,store,employee_no,full_name,fecha_ingreso "
                "FROM users WHERE active=1"
            ).fetchall()
        for row in rows:
            d = dict(row)
            result[("id", int(d["id"]))] = d
            eno = str(d.get("employee_no") or "").strip()
            if eno:
                result[("eno", eno)] = d
        return result

    def _read_rows(start, end, stores):
        if not stores:
            return []
        marks = ",".join("?" for _ in stores)
        params = (start.isoformat(), end.isoformat(), *stores)
        with m.db() as con:
            legacy_cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(operation_productivity)").fetchall()}
            timer_cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(operation_productivity_timer)").fetchall()}
            legacy_extra = (
                ",hire_date,experience_level,standard_value,standard_effective_from"
                if "standard_value" in legacy_cols else
                ",'' AS hire_date,'' AS experience_level,0 AS standard_value,'' AS standard_effective_from"
            )
            timer_extra = (
                ",hire_date,experience_level,standard_value,standard_effective_from"
                if "standard_value" in timer_cols else
                ",'' AS hire_date,'' AS experience_level,0 AS standard_value,'' AS standard_effective_from"
            )
            legacy = [
                dict(r) for r in con.execute(
                    "SELECT id,date,store,user_id,employee_no,employee_name,origin,activity,pieces,created_at"
                    + legacy_extra +
                    " FROM operation_productivity WHERE date>=? AND date<=? AND store IN (" + marks + ") ORDER BY date,id",
                    params,
                ).fetchall()
            ]
            timer = [
                dict(r) for r in con.execute(
                    "SELECT id,date,store,user_id,employee_no,employee_name,area,activity,pieces,started_at,duration_seconds"
                    + timer_extra +
                    " FROM operation_productivity_timer WHERE date>=? AND date<=? AND store IN (" + marks + ")"
                    " AND status='finished' ORDER BY date,id",
                    params,
                ).fetchall()
            ]

        def row_key(row, area_key, time_key):
            employee = str(row.get("employee_no") or "").strip() or _norm(row.get("employee_name"))
            return (
                str(row.get("date") or ""), _norm(row.get("store")), _norm(employee),
                _norm(row.get(area_key)), _norm(row.get("activity")),
                round(_num(row.get("pieces")), 3), str(row.get(time_key) or ""),
            )

        timer_keys = {row_key(r, "area", "started_at") for r in timer}
        rows = []
        for r in legacy:
            if row_key(r, "origin", "created_at") in timer_keys:
                continue
            rows.append({
                **r, "area": str(r.get("origin") or ""), "duration_seconds": 0, "source": "historical"
            })
        for r in timer:
            rows.append({**r, "source": "timer"})
        return rows

    def _snapshot_record(record_id):
        try:
            with m.db() as con:
                row = con.execute("SELECT * FROM operation_productivity_timer WHERE id=?", (record_id,)).fetchone()
                if not row or str(row["status"] or "") != "finished":
                    return
                data = dict(row)
                urow = None
                if data.get("user_id"):
                    urow = con.execute("SELECT fecha_ingreso FROM users WHERE id=?", (data["user_id"],)).fetchone()
                if not urow and str(data.get("employee_no") or "").strip():
                    urow = con.execute(
                        "SELECT fecha_ingreso FROM users WHERE employee_no=? ORDER BY id LIMIT 1",
                        (str(data.get("employee_no") or "").strip(),),
                    ).fetchone()
                hire = str(urow["fecha_ingreso"] or "") if urow else ""
                record_day = date.fromisoformat(str(data.get("date") or "")[:10])
                level, _cfg = _level_for(hire, record_day)
                standard, effective, _source = _standard_for(data.get("area"), level, record_day)
                con.execute(
                    "UPDATE operation_productivity_timer SET hire_date=?,experience_level=?,standard_value=?,standard_effective_from=? WHERE id=?",
                    (hire, level, standard, effective, record_id),
                )
                try:
                    con.execute(
                        "UPDATE operation_productivity SET hire_date=?,experience_level=?,standard_value=?,standard_effective_from=? "
                        "WHERE date=? AND store=? AND employee_no=? AND origin=? AND activity=? AND created_at=?",
                        (
                            hire, level, standard, effective,
                            data.get("date"), data.get("store"), data.get("employee_no"),
                            data.get("area"), data.get("activity"), data.get("started_at"),
                        ),
                    )
                except Exception:
                    pass
        except Exception as exc:
            print("[V210] snapshot warning:", type(exc).__name__, exc, flush=True)

    @m.app.get("/api/operation/standards-v210")
    def standards_v210(request: Request, effective_date: str = ""):
        actor = m.require_user(request)
        today = datetime.now(MX).date()
        day = _iso_day(effective_date, "Fecha de consulta") if effective_date else today
        cfg, matrix = _current_matrix(day)
        history = []
        if str(actor.get("role") or "") in ("superadmin", "admin"):
            with m.db() as con:
                history = [
                    dict(r) for r in con.execute(
                        "SELECT effective_from,new_cutoff_months,expert_cutoff_months,updated_at,updated_by "
                        "FROM operation_experience_versions ORDER BY effective_from DESC,id DESC LIMIT 30"
                    ).fetchall()
                ]
        return {
            "levels": list(LEVELS),
            "areas": list(STANDARD_AREAS),
            "ranges": {
                "new_cutoff_months": int(cfg.get("new_cutoff_months") or 3),
                "expert_cutoff_months": int(cfg.get("expert_cutoff_months") or 12),
                "effective_from": str(cfg.get("effective_from") or ""),
            },
            "matrix": matrix,
            "fallback_target": _fallback_target(),
            "editable": str(actor.get("role") or "") in ("superadmin", "admin"),
            "history": history,
        }

    @m.app.post("/api/operation/standards-v210")
    async def standards_v210_save(request: Request):
        actor = m.require_user(request, ("superadmin", "admin"))
        body = await request.json()
        effective = _iso_day(body.get("effective_from") or datetime.now(MX).date().isoformat(), "Fecha de vigencia")
        try:
            new_cut = int(body.get("new_cutoff_months"))
            expert_cut = int(body.get("expert_cutoff_months"))
        except Exception:
            raise HTTPException(400, "Captura rangos válidos en meses")
        if new_cut < 1:
            raise HTTPException(400, "Nuevo ingreso debe tener al menos 1 mes")
        if expert_cut <= new_cut:
            raise HTTPException(400, "El límite de Experto debe ser mayor al de Nuevo ingreso")
        if expert_cut > 120:
            raise HTTPException(400, "El rango de Intermedio no puede superar 120 meses")

        raw_matrix = body.get("matrix") or {}
        clean = {}
        for area in STANDARD_AREAS:
            clean[area] = {}
            src = raw_matrix.get(area) or {}
            for level in LEVELS:
                val = _num(src.get(level))
                if val < 0:
                    raise HTTPException(400, "Los estándares no pueden ser negativos")
                clean[area][level] = val

        with m.db() as con:
            before_range = con.execute(
                "SELECT * FROM operation_experience_versions WHERE effective_from=?",
                (effective.isoformat(),),
            ).fetchone()
            con.execute(
                "INSERT INTO operation_experience_versions"
                "(effective_from,new_cutoff_months,expert_cutoff_months,updated_at,updated_by)"
                " VALUES(?,?,?,?,?) ON CONFLICT(effective_from) DO UPDATE SET "
                "new_cutoff_months=excluded.new_cutoff_months,"
                "expert_cutoff_months=excluded.expert_cutoff_months,"
                "updated_at=excluded.updated_at,updated_by=excluded.updated_by",
                (effective.isoformat(), new_cut, expert_cut, datetime.now(MX).isoformat(timespec="seconds"), actor["username"]),
            )
            for area in STANDARD_AREAS:
                for level in LEVELS:
                    con.execute(
                        "INSERT INTO operation_level_standards"
                        "(effective_from,area,level,pieces_per_day,updated_at,updated_by)"
                        " VALUES(?,?,?,?,?,?) ON CONFLICT(effective_from,area,level) DO UPDATE SET "
                        "pieces_per_day=excluded.pieces_per_day,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
                        (
                            effective.isoformat(), area, level, clean[area][level],
                            datetime.now(MX).isoformat(timespec="seconds"), actor["username"],
                        ),
                    )
            _audit(
                actor, "operational_standards", effective.isoformat(), "save",
                dict(before_range) if before_range else {},
                {
                    "new_cutoff_months": new_cut,
                    "expert_cutoff_months": expert_cut,
                    "matrix": clean,
                    "effective_from": effective.isoformat(),
                },
                con=con,
            )
        return {
            "ok": True,
            "message": "Estándares Operativos guardados",
            "effective_from": effective.isoformat(),
        }

    @m.app.get("/api/operation/staff-v210")
    def staff_v210(request: Request):
        m.require_user(request, ("superadmin", "admin"))
        marks = ",".join("?" for _ in STAFF_ROLES)
        with m.db() as con:
            rows = [
                dict(r) for r in con.execute(
                    "SELECT id,username,role,store,employee_no,full_name,fecha_ingreso,active "
                    "FROM users WHERE role IN (" + marks + ") ORDER BY store,full_name,username",
                    STAFF_ROLES,
                ).fetchall()
            ]
        today = datetime.now(MX).date()
        for r in rows:
            level, _ = _level_for(str(r.get("fecha_ingreso") or ""), today)
            r["experience_level"] = level
        return {"items": rows}

    @m.app.post("/api/operation/staff-v210/{user_id}/hire-date")
    async def staff_hire_date_v210(user_id: int, request: Request):
        actor = m.require_user(request, ("superadmin", "admin"))
        body = await request.json()
        hire = _iso_day(body.get("fecha_ingreso"), "Fecha de ingreso")
        if hire > datetime.now(MX).date():
            raise HTTPException(400, "La fecha de ingreso no puede estar en el futuro")
        with m.db() as con:
            row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Usuario no encontrado")
            if str(row["role"] or "") not in STAFF_ROLES:
                raise HTTPException(400, "Este usuario no utiliza estándar por antigüedad")
            old = str(row["fecha_ingreso"] or "")
            con.execute(
                "UPDATE users SET fecha_ingreso=?,updated_at=? WHERE id=?",
                (hire.isoformat(), datetime.now(MX).isoformat(timespec="seconds"), user_id),
            )
            _audit(
                actor, "user_hire_date", user_id, "update",
                {"fecha_ingreso": old},
                {"fecha_ingreso": hire.isoformat()},
                con=con,
            )
        return {"ok": True, "message": "Fecha de ingreso actualizada"}

    @m.app.get("/api/operation/my-hire-date-v210")
    def my_hire_date_v210(request: Request):
        actor, row = _real_row(request)
        real_role = str(row.get("role") or "")
        hire = str(row.get("fecha_ingreso") or "")
        today = datetime.now(MX).date()
        level, cfg = _level_for(hire, today)
        standard_rows = {}
        if hire:
            for area in STANDARD_AREAS:
                val, eff, source = _standard_for(area, level, today)
                standard_rows[area] = {"value": val, "effective_from": eff, "source": source}
        return {
            "applicable": real_role in STAFF_ROLES,
            "role": real_role,
            "fecha_ingreso": hire,
            "needs_date": real_role in STAFF_ROLES and not hire,
            "experience_level": level,
            "ranges": {
                "new_cutoff_months": int(cfg.get("new_cutoff_months") or 3),
                "expert_cutoff_months": int(cfg.get("expert_cutoff_months") or 12),
            },
            "standards": standard_rows,
        }

    @m.app.post("/api/operation/my-hire-date-v210")
    async def my_hire_date_v210_save(request: Request):
        actor, row = _real_row(request)
        role = str(row.get("role") or "")
        if role not in STAFF_ROLES:
            raise HTTPException(403, "Este perfil no requiere fecha de ingreso")
        if str(row.get("fecha_ingreso") or "").strip():
            raise HTTPException(409, "Tu fecha de ingreso ya está registrada. Solicita una corrección al Administrador.")
        body = await request.json()
        hire = _iso_day(body.get("fecha_ingreso"), "Fecha de ingreso")
        today = datetime.now(MX).date()
        if hire > today:
            raise HTTPException(400, "La fecha de ingreso no puede estar en el futuro")
        if hire.year < 1980:
            raise HTTPException(400, "Revisa la fecha de ingreso")
        with m.db() as con:
            con.execute(
                "UPDATE users SET fecha_ingreso=?,updated_at=? WHERE id=?",
                (hire.isoformat(), datetime.now(MX).isoformat(timespec="seconds"), row["id"]),
            )
            _audit(
                actor, "user_hire_date", row["id"], "self_capture", {},
                {"fecha_ingreso": hire.isoformat()}, con=con
            )
        level, _ = _level_for(hire.isoformat(), today)
        return {"ok": True, "message": "Fecha de ingreso guardada", "experience_level": level}

    @m.app.get("/api/operation-productivity-ranking-v210")
    def productivity_ranking_v210(
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
                scope_stores = [selected_store]
            else:
                scope_stores = active_stores
        else:
            scope_stores = [selected_store]

        rows = _read_rows(start, end, scope_stores)
        rows = [
            r for r in rows
            if str(r.get("area") or "") in RANKING_AREAS
            and str(r.get("activity") or "") in RANKING_ACTIVITIES
        ]
        if area and area != "Todas":
            rows = [r for r in rows if str(r.get("area") or "") == area]
        if activity and activity != "Todas":
            rows = [r for r in rows if str(r.get("activity") or "") == activity]

        staff = _staff_map()
        people = {}
        today = datetime.now(MX).date()
        for r in rows:
            eno = str(r.get("employee_no") or "").strip()
            name = " ".join(str(r.get("employee_name") or "Sin nombre").split())
            st = _canonical_store(r.get("store"), active_stores)
            person_key = (eno or _norm(name), _norm(st))
            user = staff.get(("id", int(r.get("user_id") or 0))) if r.get("user_id") else None
            if not user and eno:
                user = staff.get(("eno", eno))
            hire = str((user or {}).get("fecha_ingreso") or r.get("hire_date") or "")
            try:
                rday = date.fromisoformat(str(r.get("date") or "")[:10])
            except Exception:
                rday = end
            snap_standard = _num(r.get("standard_value"))
            snap_level = str(r.get("experience_level") or "").strip()
            if snap_standard > 0 and snap_level:
                level = snap_level
                standard = snap_standard
                standard_eff = str(r.get("standard_effective_from") or "")
                standard_source = "Snapshot"
            else:
                level, _cfg = _level_for(hire, rday)
                standard, standard_eff, standard_source = _standard_for(r.get("area"), level, rday)

            g = people.setdefault(person_key, {
                "employee_no": eno,
                "name": name,
                "store": st,
                "pieces": 0.0,
                "dates": set(),
                "areas": set(),
                "activities": set(),
                "duration_seconds": 0,
                "target_keys": {},
                "hire_date": hire,
                "standard_sources": set(),
            })
            g["pieces"] += _num(r.get("pieces"))
            if r.get("date"):
                g["dates"].add(str(r.get("date")))
            if r.get("area"):
                g["areas"].add(str(r.get("area")))
            if r.get("activity"):
                g["activities"].add(str(r.get("activity")))
            g["duration_seconds"] += int(_num(r.get("duration_seconds")))
            key = (str(r.get("date") or ""), str(r.get("area") or ""))
            if key not in g["target_keys"]:
                g["target_keys"][key] = {
                    "value": standard,
                    "level": level,
                    "effective": standard_eff,
                }
            g["standard_sources"].add(standard_source)

        collaborators = []
        for g in people.values():
            days = max(len(g["dates"]), 1)
            target_total = sum(_num(x.get("value")) for x in g["target_keys"].values())
            if target_total <= 0:
                target_total = _fallback_target() * days
            daily = g["pieces"] / days
            target_daily = target_total / days if days else 0
            compliance = g["pieces"] / target_total * 100.0 if target_total else 0.0
            current_level, _ = _level_for(g["hire_date"], today)
            collaborators.append({
                "employee_no": g["employee_no"],
                "name": g["name"],
                "store": g["store"],
                "pieces": g["pieces"],
                "days": days,
                "daily": daily,
                "target": target_total,
                "target_daily": target_daily,
                "compliance_pct": compliance,
                "areas": sorted(g["areas"]),
                "activities": sorted(g["activities"]),
                "duration_seconds": g["duration_seconds"],
                "hire_date": g["hire_date"],
                "experience_level": current_level,
                "standard_source": ", ".join(sorted(g["standard_sources"])),
            })

        store_names = scope_stores if selected_store != "Compañía" else active_stores
        store_rows = []
        for st in store_names:
            people_st = [r for r in collaborators if _norm(r["store"]) == _norm(st)]
            pieces = sum(_num(r["pieces"]) for r in people_st)
            target_total = sum(_num(r["target"]) for r in people_st)
            collaborator_days = sum(int(r["days"]) for r in people_st)
            daily = pieces / collaborator_days if collaborator_days else 0.0
            target_daily = target_total / collaborator_days if collaborator_days else _fallback_target()
            compliance = pieces / target_total * 100.0 if target_total else 0.0
            store_rows.append({
                "store": st,
                "pieces": pieces,
                "collaborators": len(people_st),
                "collaborator_days": collaborator_days,
                "daily": daily,
                "target": target_total,
                "target_daily": target_daily,
                "compliance_pct": compliance,
            })
        store_rows.sort(key=lambda r: (-r["compliance_pct"], -r["pieces"], _norm(r["store"])))
        for idx, row in enumerate(store_rows, 1):
            row["rank"] = idx

        detailed = []
        for st_row in store_rows:
            local = [r for r in collaborators if _norm(r["store"]) == _norm(st_row["store"])]
            local.sort(key=lambda r: (-r["compliance_pct"], -r["pieces"], _norm(r["name"])))
            for local_rank, person in enumerate(local, 1):
                item = dict(person)
                item["store_rank"] = st_row["rank"]
                item["rank_in_store"] = local_rank
                detailed.append(item)

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
            "target_daily": _fallback_target(),
            "areas": list(RANKING_AREAS),
            "activities": list(RANKING_ACTIVITIES),
            "store_ranking": store_rows,
            "collaborator_ranking": detailed,
            "total_pieces": sum(_num(r["pieces"]) for r in detailed),
            "collaborators": len(detailed),
            "standards_mode": "tenure_v210",
        }

    css = r'''<style id="v210-operational-standards-css">
.v210-std-panel{background:#fff;border:1px solid #d6e3f0;border-radius:16px;padding:14px;margin:9px 0;box-shadow:0 6px 20px rgba(25,72,118,.05)}
.v210-std-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap}
.v210-std-head h3{margin:0;color:#123f73;font-size:15px;font-weight:950}
.v210-note{margin-top:5px;color:#71849a;font-size:8px;line-height:1.5}
.v210-range-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px}
.v210-range{border:1px solid #dbe6f1;border-radius:13px;padding:11px;background:#f9fbfe}
.v210-range b{display:block;color:#123f73;font-size:12px}
.v210-range span{display:block;margin-top:5px;color:#667b92;font-size:8px}
.v210-config{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}
.v210-field label{display:block;margin:0 0 5px;color:#667085;font-size:8px;font-weight:950;text-transform:uppercase}
.v210-field input{width:100%;height:40px;border:1px solid #ccd8e6;border-radius:10px;padding:8px 10px;background:#fff;color:#123b73;font-weight:850}
.v210-matrix-wrap{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #d8e4ef;border-radius:12px;margin-top:10px}
.v210-matrix{width:100%;min-width:630px;border-collapse:separate;border-spacing:0;font-size:8px}
.v210-matrix th{background:#124d84;color:#fff;padding:9px 8px;text-align:left;white-space:nowrap}
.v210-matrix td{padding:8px;border-bottom:1px solid #e5edf5;color:#294b70}
.v210-matrix input{width:110px;height:34px;border:1px solid #ccd8e6;border-radius:8px;padding:5px 7px;font-weight:900;color:#123f73}
.v210-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px}
.v210-msg{font-size:8px;font-weight:800;color:#667085}
.v210-staff-table{width:100%;min-width:780px;border-collapse:separate;border-spacing:0;font-size:8px}
.v210-staff-table th{position:sticky;top:0;background:#124d84;color:#fff;padding:8px 7px;text-align:left}
.v210-staff-table td{padding:7px;border-bottom:1px solid #e5edf5;color:#294b70}
.v210-staff-table input{height:32px;border:1px solid #ccd8e6;border-radius:8px;padding:5px 7px}
.v210-mini{border:0;border-radius:8px;background:#0b67bd;color:#fff;padding:7px 9px;font-size:8px;font-weight:900;cursor:pointer}
.v210-badge{display:inline-flex;border-radius:999px;background:#eaf3ff;color:#0b579f;padding:4px 7px;font-weight:900}
#v210HireModal{position:fixed;inset:0;background:#081425cc;display:grid;place-items:center;z-index:100500}
#v210HireModal.hidden{display:none!important}
.v210-hire-card{width:min(440px,calc(100% - 28px));background:#fff;border-radius:18px;padding:22px;box-shadow:0 30px 90px #0007}
.v210-hire-card h2{margin:0;color:#123f73;font-size:19px}
.v210-hire-card p{font-size:10px;color:#667085;line-height:1.5}
.v210-hire-card input{width:100%;height:45px;border:1px solid #ccd8e6;border-radius:10px;padding:9px 10px;font-size:15px}
.v210-hire-card button{width:100%;margin-top:12px}
@media(max-width:900px){
 .v210-range-grid,.v210-config{grid-template-columns:1fr}
 .v210-std-panel{padding:11px}
 .v210-matrix{min-width:560px}
}
</style>'''

    modal = r'''<div id="v210HireModal" class="hidden"><div class="v210-hire-card">
<h2>Fecha de ingreso</h2>
<p>Captura tu fecha real de ingreso una sola vez. El sistema calculará automáticamente tu antigüedad, nivel y estándar. Si después necesitas corregirla, deberá hacerlo un Administrador.</p>
<div class="v210-field"><label>Fecha de ingreso</label><input id="v210HireDate" type="date"></div>
<button class="primary" id="v210HireSave">Guardar y continuar</button>
<div class="v210-msg" id="v210HireMsg"></div>
</div></div>'''

    js = r'''<script id="v210-operational-standards-js">
(function(){
 if(window.__V210_OPERATIONAL_STANDARDS)return;
 window.__V210_OPERATIONAL_STANDARDS=true;
 const q=(s,r=document)=>r.querySelector(s);
 const qa=(s,r=document)=>[...r.querySelectorAll(s)];
 const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=v=>{const n=Number(v||0);return Number.isFinite(n)?n:0};
 const nf=v=>Math.round(num(v)).toLocaleString('es-MX');
 const staffRoles=new Set(['colaborador_operativo','colaborador_lenceria','colaborador']);
 let hireCheckedFor='';

 async function A(url,opt={}){if(typeof api==='function')return api(url,opt);const r=await fetch(url,{credentials:'same-origin',...opt});if(!r.ok)throw new Error(await r.text());return r.json()}

 function rangesHtml(d){
   const a=d.ranges||{},n=Number(a.new_cutoff_months||3),e=Number(a.expert_cutoff_months||12);
   return '<div class="v210-range-grid">'+
    '<div class="v210-range"><b>Nuevo ingreso</b><span>Desde ingreso hasta cumplir '+n+' meses</span></div>'+
    '<div class="v210-range"><b>Intermedio</b><span>Desde '+n+' hasta cumplir '+e+' meses</span></div>'+
    '<div class="v210-range"><b>Experto</b><span>Desde '+e+' meses · sin límite</span></div>'+
   '</div>';
 }

 function matrixHtml(d){
   const levels=d.levels||[],areas=d.areas||[],editable=!!d.editable,m=d.matrix||{};
   return '<div class="v210-matrix-wrap"><table class="v210-matrix"><thead><tr><th>Modalidad</th>'+
     levels.map(x=>'<th>'+esc(x)+'</th>').join('')+
     '</tr></thead><tbody>'+areas.map(area=>'<tr><td><b>'+esc(area)+'</b></td>'+
       levels.map(level=>{
         const v=num(m?.[area]?.[level]?.value);
         return '<td>'+(editable?'<input class="v210-standard-input" data-area="'+esc(area)+'" data-level="'+esc(level)+'" type="number" min="0" step="1" value="'+(v||'')+'" placeholder="Sin configurar">':(v?nf(v)+' pzas':'Meta general'))+'</td>';
       }).join('')+'</tr>').join('')+
     '</tbody></table></div>';
 }

 async function loadStaff(){
   const host=q('#v210Staff');if(!host)return;
   try{
     const d=await A('/api/operation/staff-v210');
     const rows=(d.items||[]).map(r=>'<tr data-id="'+r.id+'"><td><b>'+esc(r.full_name||r.username)+'</b><br><small>'+esc(r.username)+'</small></td><td>'+esc(r.store||'—')+'</td><td>'+esc(r.employee_no||'—')+'</td><td>'+esc(r.role)+'</td><td><input class="v210-staff-date" type="date" value="'+esc(r.fecha_ingreso||'')+'"></td><td><span class="v210-badge">'+esc(r.experience_level||'Sin fecha')+'</span></td><td><button class="v210-mini v210-save-hire">Guardar</button></td></tr>').join('');
     host.innerHTML='<div class="v210-matrix-wrap"><table class="v210-staff-table"><thead><tr><th>Colaborador</th><th>Tienda</th><th>Nómina</th><th>Perfil</th><th>Fecha ingreso</th><th>Nivel actual</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>';
     qa('.v210-save-hire',host).forEach(btn=>btn.onclick=async()=>{
       const tr=btn.closest('tr'),input=q('.v210-staff-date',tr);if(!input?.value)return;
       btn.disabled=true;btn.textContent='Guardando…';
       try{await A('/api/operation/staff-v210/'+tr.dataset.id+'/hire-date',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha_ingreso:input.value})});await loadStaff()}
       catch(e){alert(e.message||e);btn.disabled=false;btn.textContent='Guardar'}
     });
   }catch(e){host.innerHTML='<div class="infoempty">No fue posible cargar colaboradores: '+esc(e.message||e)+'</div>'}
 }

 async function renderStandards(){
   const host=q('#operativoDynamicContent');if(!host)return;
   q('#operativoCentro')?.classList.add('hidden');q('#operativoDynamic')?.classList.remove('hidden');
   const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub');
   if(title)title.textContent='Estándares Operativos';
   if(sub)sub.textContent='Niveles por antigüedad · Doblado y Frontal';
   q('#operativoPeriodBar')?.classList.add('hidden');
   if(q('#operativoPeriodBar'))q('#operativoPeriodBar').style.display='none';
   host.innerHTML='<div class="infoempty">Cargando Estándares Operativos…</div>';
   try{
     const d=await A('/api/operation/standards-v210');
     const r=d.ranges||{},editable=!!d.editable;
     const config=editable?'<div class="v210-config"><div class="v210-field"><label>Nuevo ingreso · hasta (meses)</label><input id="v210NewCut" type="number" min="1" max="119" value="'+Number(r.new_cutoff_months||3)+'"></div><div class="v210-field"><label>Intermedio · hasta (meses)</label><input id="v210ExpertCut" type="number" min="2" max="120" value="'+Number(r.expert_cutoff_months||12)+'"></div><div class="v210-field"><label>Aplicar desde</label><input id="v210Effective" type="date" value="'+new Date().toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'})+'"></div></div>':'';
     const save=editable?'<div class="v210-actions"><button class="primary" id="v210SaveStandards">Guardar cambios</button><span class="v210-msg" id="v210StdMsg"></span></div>':'';
     host.innerHTML='<div class="v210-std-panel"><div class="v210-std-head"><div><h3>Estándares Operativos</h3><div class="v210-note">Tres niveles automáticos según fecha de ingreso. Los rangos no están fijos en código.</div></div><span class="v210-badge">Vigente desde '+esc(r.effective_from||'')+'</span></div>'+
       rangesHtml(d)+config+
       '<h3 style="margin:16px 0 0;color:#123f73">Productividad por nivel</h3><div class="v210-note">Configura las piezas por día para Doblado y Frontal. Un campo vacío conserva como respaldo la meta general actual de '+nf(d.fallback_target)+' pzas.</div>'+
       matrixHtml(d)+save+'</div>'+
       (editable?'<div class="v210-std-panel"><h3>Fechas de ingreso de colaboradores</h3><div class="v210-note">El colaborador la captura una sola vez. Administrador y Super Administrador pueden corregirla aquí; cada cambio queda auditado.</div><div id="v210Staff"><div class="infoempty">Cargando colaboradores…</div></div></div>':'');
     if(editable)loadStaff();

     q('#v210SaveStandards')?.addEventListener('click',async()=>{
       const msg=q('#v210StdMsg'),nc=Number(q('#v210NewCut')?.value||0),ec=Number(q('#v210ExpertCut')?.value||0),eff=q('#v210Effective')?.value;
       if(!eff){msg.textContent='Selecciona fecha de vigencia';return}
       if(nc<1||ec<=nc){msg.textContent='Revisa los rangos: Intermedio debe terminar después de Nuevo ingreso.';return}
       const matrix={};
       qa('.v210-standard-input').forEach(i=>{matrix[i.dataset.area]=matrix[i.dataset.area]||{};matrix[i.dataset.area][i.dataset.level]=num(i.value)});
       if(!confirm('¿Guardar estos rangos y estándares desde '+eff+'? Los periodos anteriores conservarán su configuración histórica.'))return;
       msg.textContent='Guardando…';
       try{
         const res=await A('/api/operation/standards-v210',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({effective_from:eff,new_cutoff_months:nc,expert_cutoff_months:ec,matrix})});
         msg.textContent=res.message||'Guardado';setTimeout(renderStandards,350);
       }catch(e){msg.textContent=e.message||String(e)}
     });
   }catch(e){host.innerHTML='<div class="infoempty">No fue posible cargar Estándares Operativos: '+esc(e.message||e)+'</div>'}
 }

 function bindStandardsTab(){
   const btn=q('#v200OperationTabs [data-v200-op="standards"]');if(!btn)return;
   const label=q('.v203-tab-label,.v206-tab-label',btn);
   if(label){
     if(label.textContent!=='Estándares Operativos')label.textContent='Estándares Operativos';
   }else if(btn.textContent!=='Estándares Operativos'){
     btn.textContent='Estándares Operativos';
   }
   btn.title='Estándares Operativos';
   if(btn.dataset.v210Bound==='1')return;
   btn.dataset.v210Bound='1';
   btn.addEventListener('click',e=>{
     const mod=String(document.body.dataset.v163Module||'').toLowerCase();
     if(mod!=='operation')return;
     e.preventDefault();e.stopImmediatePropagation();
     qa('#v200OperationTabs [data-v200-op]').forEach(x=>x.classList.toggle('active',x===btn));
     try{window.V125_OPERATION_TAB='standards'}catch(_){}
     renderStandards();
   },true);
 }

 async function checkHireDate(force=false){
   let u=null;try{u=USER}catch(_){u=window.USER} if(!u)return;
   const real=String(u.real_role||u.role||'');
   if(!staffRoles.has(real))return;
   const key=String(u.id||u.username||real);
   if(!force&&hireCheckedFor===key)return;
   hireCheckedFor=key;
   try{
     const d=await A('/api/operation/my-hire-date-v210');
     if(!d.needs_date){q('#v210HireModal')?.classList.add('hidden');return}
     const input=q('#v210HireDate');if(input&&!input.value)input.max=new Date().toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'});
     q('#v210HireModal')?.classList.remove('hidden');
   }catch(e){console.warn('[V210] fecha ingreso',e)}
 }

 q('#v210HireSave')?.addEventListener('click',async()=>{
   const date=q('#v210HireDate')?.value,msg=q('#v210HireMsg');if(!date){msg.textContent='Selecciona tu fecha de ingreso';return}
   try{
     const r=await A('/api/operation/my-hire-date-v210',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha_ingreso:date})});
     msg.textContent=r.message+' · Nivel: '+r.experience_level;
     setTimeout(()=>q('#v210HireModal')?.classList.add('hidden'),650);
   }catch(e){msg.textContent=e.message||String(e)}
 });

 const previousEnter=window.enter;
 if(typeof previousEnter==='function'){
   window.enter=async function(u){const r=await previousEnter(u);setTimeout(()=>checkHireDate(true),450);setTimeout(bindStandardsTab,250);return r}
 }

 const mo=new MutationObserver(()=>{clearTimeout(window.__v210Bind);window.__v210Bind=setTimeout(bindStandardsTab,25)});
 const tabs=q('#v200OperationTabs');if(tabs)mo.observe(tabs,{childList:true,subtree:true});
 bindStandardsTab();
 setTimeout(()=>checkHireDate(false),900);
 [200,700,1600].forEach(ms=>setTimeout(bindStandardsTab,ms));
 console.info('[V210] Estándares Operativos por antigüedad activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v210_middleware(request, call_next):
        response = await call_next(request)
        path = request.url.path

        match = re.fullmatch(r"/api/operation-productivity-timer/(\d+)/finish", path)
        if match and request.method.upper() == "POST" and getattr(response, "status_code", 500) < 400:
            _snapshot_record(int(match.group(1)))

        if path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")

            # V204 sigue siendo dueño visual del ranking/captura; sólo sustituimos
            # su fuente de ranking por la V210, que aplica antigüedad + estándar.
            html = html.replace(
                "/api/operation-productivity-ranking-v204?",
                "/api/operation-productivity-ranking-v210?",
            )
            if "v210-operational-standards-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v210HireModal" not in html:
                html = html.replace('<div id="appView"', modal + '<div id="appView"', 1)
            if "v210-operational-standards-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V210",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print("[V210] HTML warning:", type(exc).__name__, exc, flush=True)
            return response

    m._V210_OPERATIONAL_STANDARDS_TENURE = True
    print("[V210] Estándares Operativos: 3 niveles, rangos editables y fecha de ingreso.", flush=True)
