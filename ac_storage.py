"""Propuesta AC: persistencia operativa por tienda, modelo y talla.

Módulo aislado: no modifica la base operativa heredada ni registra endpoints
hasta que la integración y las pruebas sean aprobadas.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

STAGES = {"Separar", "Acondicionar", "Ubicar", "Pizca", "Excedentes"}
FLOWS = {"Surtido", "Resurtido"}
AREAS = {"Colgado", "Doblado", "Jeans", "Lencería"}
STORAGE_KINDS = {"Piso", "Rack", "Septimos", "Tarima", "Transito"}
SESSION_STATES = {"active", "paused", "finished"}
NEXT_STAGE = {
    ("Surtido", "Separar"): "Acondicionar",
    ("Surtido", "Acondicionar"): "Ubicar",
    ("Resurtido", "Pizca"): "Acondicionar",
    ("Resurtido", "Acondicionar"): "Ubicar",
}
SCHEMA = """
CREATE TABLE IF NOT EXISTS ac_capacity_batches (
 id INTEGER PRIMARY KEY, store TEXT NOT NULL, version TEXT NOT NULL,
 uploaded_by TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(store,version)
);
CREATE TABLE IF NOT EXISTS ac_capacity_sizes (
 batch_id INTEGER NOT NULL REFERENCES ac_capacity_batches(id),
 model_id TEXT NOT NULL, size TEXT NOT NULL,
 curve INTEGER NOT NULL CHECK(curve >= 0),
 capacity INTEGER NOT NULL CHECK(capacity >= 0),
 PRIMARY KEY(batch_id,model_id,size)
);
CREATE TABLE IF NOT EXISTS ac_sessions (
 id TEXT PRIMARY KEY, store TEXT NOT NULL, employee_id TEXT NOT NULL,
 flow TEXT NOT NULL, stage TEXT NOT NULL, area TEXT NOT NULL,
 started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS ac_captures (
 id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE,
 store TEXT NOT NULL, model_id TEXT NOT NULL, color TEXT NOT NULL DEFAULT '',
 flow TEXT NOT NULL, stage TEXT NOT NULL, area TEXT NOT NULL,
 session_id TEXT NOT NULL REFERENCES ac_sessions(id),
 recorded_at TEXT NOT NULL, created_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ac_capture_sizes (
 capture_id TEXT NOT NULL REFERENCES ac_captures(id),
 size TEXT NOT NULL, pieces INTEGER NOT NULL CHECK(pieces > 0),
 PRIMARY KEY(capture_id,size)
);
CREATE TABLE IF NOT EXISTS ac_tasks (
 id TEXT PRIMARY KEY,
 source_capture_id TEXT REFERENCES ac_captures(id),
 store TEXT NOT NULL, model_id TEXT NOT NULL, color TEXT NOT NULL DEFAULT '',
 flow TEXT NOT NULL, stage TEXT NOT NULL, area TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending'
 CHECK(status IN ('pending','in_progress','completed')),
 assigned_to TEXT, created_at TEXT NOT NULL, finished_at TEXT,
 UNIQUE(source_capture_id,stage)
);
CREATE TABLE IF NOT EXISTS ac_task_sizes (
 task_id TEXT NOT NULL REFERENCES ac_tasks(id),
 size TEXT NOT NULL, total INTEGER NOT NULL CHECK(total > 0),
 completed INTEGER NOT NULL DEFAULT 0 CHECK(completed >= 0 AND completed <= total),
 PRIMARY KEY(task_id,size)
);
CREATE TABLE IF NOT EXISTS ac_task_captures (
 capture_id TEXT PRIMARY KEY REFERENCES ac_captures(id),
 task_id TEXT NOT NULL REFERENCES ac_tasks(id)
);
CREATE TABLE IF NOT EXISTS ac_capture_destinations (
 capture_id TEXT PRIMARY KEY REFERENCES ac_captures(id),
 location_id TEXT NOT NULL REFERENCES ac_locations(id)
);
CREATE INDEX IF NOT EXISTS ac_tasks_queue
 ON ac_tasks(store,flow,stage,area,status,created_at);
CREATE TABLE IF NOT EXISTS ac_locations (
 id TEXT PRIMARY KEY, store TEXT NOT NULL, kind TEXT NOT NULL,
 aisle TEXT NOT NULL DEFAULT '', face TEXT NOT NULL DEFAULT '',
 section TEXT NOT NULL DEFAULT '', level TEXT NOT NULL DEFAULT '',
 pallet TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
 UNIQUE(store,kind,aisle,face,section,level,pallet)
);
CREATE TABLE IF NOT EXISTS ac_movement_batches (
 id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ac_movements (
 id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES ac_movement_batches(id),
 event_key TEXT NOT NULL UNIQUE,
 store TEXT NOT NULL, model_id TEXT NOT NULL, size TEXT NOT NULL,
 pieces INTEGER NOT NULL CHECK(pieces > 0),
 from_location TEXT REFERENCES ac_locations(id),
 to_location TEXT REFERENCES ac_locations(id),
 created_by TEXT NOT NULL, partner_id TEXT, captured_at TEXT NOT NULL,
 CHECK(from_location IS NOT to_location)
);
CREATE TABLE IF NOT EXISTS ac_stock (
 store TEXT NOT NULL, location_id TEXT NOT NULL REFERENCES ac_locations(id),
 model_id TEXT NOT NULL, size TEXT NOT NULL, pieces INTEGER NOT NULL DEFAULT 0
 CHECK(pieces >= 0),
 reserved INTEGER NOT NULL DEFAULT 0 CHECK(reserved >= 0 AND reserved <= pieces),
 PRIMARY KEY(store,location_id,model_id,size)
);
CREATE TABLE IF NOT EXISTS ac_reservations (
 id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE,
 store TEXT NOT NULL, location_id TEXT NOT NULL REFERENCES ac_locations(id),
 model_id TEXT NOT NULL, size TEXT NOT NULL,
 pieces INTEGER NOT NULL CHECK(pieces > 0), requested_by TEXT NOT NULL,
 created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
 CHECK(status IN ('active','released','fulfilled'))
);
CREATE INDEX IF NOT EXISTS ac_captures_store_model ON ac_captures(store,model_id,recorded_at);
CREATE INDEX IF NOT EXISTS ac_movements_store_model ON ac_movements(store,model_id,size);
CREATE INDEX IF NOT EXISTS ac_sessions_store_employee ON ac_sessions(store,employee_id,started_at);
CREATE UNIQUE INDEX IF NOT EXISTS ac_unique_active_session ON ac_sessions(store,employee_id) WHERE status="active";
"""

def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def require_text(value, field):
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"{field} obligatorio")
    return value

def normalize_sizes(sizes):
    if not isinstance(sizes, dict) or not sizes:
        raise ValueError("Se requieren tallas y piezas")
    result = {}
    for size, quantity in sizes.items():
        size = require_text(size, "Talla").upper()
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("Las piezas deben ser enteros positivos")
        if size in result:
            raise ValueError("Talla duplicada")
        result[size] = quantity
    return result

class ACStore:
    def __init__(self, db_path):
        self.path = Path(db_path)

    @contextmanager
    def transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(str(self.path), timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.path), timeout=15) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA)
            # Migrar únicamente la SQLite aislada de laboratorio cuando provenga
            # de una versión AC donde toda tarea exigía captura de origen.
            # Los pedidos aprobados originan tareas de Pizca sin captura previa.
            columns=db.execute("PRAGMA table_info(ac_tasks)").fetchall()
            legacy_source=next((row for row in columns if row["name"]=="source_capture_id"),None)
            if legacy_source and legacy_source["notnull"]:
                db.execute("PRAGMA foreign_keys=OFF")
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE ac_tasks_migrated (
                     id TEXT PRIMARY KEY,
                     source_capture_id TEXT REFERENCES ac_captures(id),
                     store TEXT NOT NULL, model_id TEXT NOT NULL,
                     color TEXT NOT NULL DEFAULT '', flow TEXT NOT NULL,
                     stage TEXT NOT NULL, area TEXT NOT NULL,
                     status TEXT NOT NULL DEFAULT 'pending'
                      CHECK(status IN ('pending','in_progress','completed')),
                     assigned_to TEXT, created_at TEXT NOT NULL, finished_at TEXT,
                     UNIQUE(source_capture_id,stage)
                    );
                    INSERT INTO ac_tasks_migrated
                    SELECT id,source_capture_id,store,model_id,color,flow,
                           stage,area,status,assigned_to,created_at,finished_at
                    FROM ac_tasks;
                    DROP TABLE ac_tasks;
                    ALTER TABLE ac_tasks_migrated RENAME TO ac_tasks;
                    CREATE INDEX IF NOT EXISTS ac_tasks_queue
                     ON ac_tasks(store,flow,stage,area,status,created_at);
                    COMMIT;
                """)
                db.execute("PRAGMA foreign_keys=ON")
                violations=db.execute("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise RuntimeError("La migración de tareas AC no pasó la validación referencial")

    def start_session(self, store, employee_id, flow, stage, area):
        if flow not in FLOWS or stage not in STAGES or area not in AREAS:
            raise ValueError("Proceso, actividad o clasificación inválido")
        store = require_text(store, "Tienda")
        employee_id = require_text(employee_id, "Colaborador")
        sid = uuid.uuid4().hex
        with self.transaction() as db:
            active = db.execute(
                "SELECT id,flow,stage,area FROM ac_sessions WHERE store=? AND employee_id=? AND status='active'",
                (store, employee_id)
            ).fetchone()
            if active:
                if (active["flow"], active["stage"], active["area"]) == (flow, stage, area):
                    return active["id"]
                raise ValueError("Finaliza la actividad anterior antes de iniciar otra")
            db.execute("INSERT INTO ac_sessions(id,store,employee_id,flow,stage,area,started_at) VALUES(?,?,?,?,?,?,?)",
                       (sid,store,employee_id,flow,stage,area,timestamp()))
        return sid

    def finish_session(self, sid, employee_id):
        with self.transaction() as db:
            changed = db.execute("UPDATE ac_sessions SET status='finished',ended_at=? WHERE id=? AND employee_id=? AND status IN ('active','paused')",
                                 (timestamp(),sid,employee_id)).rowcount
            if not changed:
                raise ValueError("La sesión no existe, no pertenece al colaborador o ya finalizó")
            # Al terminar el turno, las tareas incompletas vuelven a la cola.
            # Los avances por talla ya confirmados permanecen intactos.
            session = db.execute("SELECT store,flow,stage,area FROM ac_sessions WHERE id=?", (sid,)).fetchone()
            db.execute(
                "UPDATE ac_tasks SET status='pending',assigned_to=NULL "
                "WHERE assigned_to=? AND store=? AND flow=? AND stage=? AND area=? AND status='in_progress'",
                (employee_id,session["store"],session["flow"],session["stage"],session["area"])
            )

    def list_tasks(self, *, store, flow, stage, area, employee_id, limit=40):
        if flow not in FLOWS or stage not in STAGES or area not in AREAS:
            raise ValueError("Consulta de cola inválida")
        with self.transaction() as db:
            tasks = db.execute(
                "SELECT id,model_id,color,stage,flow,area,status,assigned_to,created_at "
                "FROM ac_tasks WHERE store=? AND flow=? AND stage=? AND area=? "
                "AND (status='pending' OR (status='in_progress' AND assigned_to=?)) "
                "ORDER BY CASE WHEN assigned_to=? THEN 0 ELSE 1 END,created_at,id LIMIT ?",
                (store,flow,stage,area,employee_id,employee_id,min(100,max(1,limit)))
            ).fetchall()
            result=[]
            for task in tasks:
                remaining={
                    size["size"]:size["total"]-size["completed"]
                    for size in db.execute(
                        "SELECT size,total,completed FROM ac_task_sizes WHERE task_id=?",
                        (task["id"],)
                    )
                    if size["total"]>size["completed"]
                }
                if remaining:
                    item={**dict(task),"remaining":remaining}
                    if task["flow"]=="Resurtido" and task["stage"]=="Pizca":
                        source=db.execute("""
                            SELECT l.kind,l.aisle,l.face,l.section,l.level,l.pallet
                            FROM ac_order_lines a
                            JOIN ac_locations l ON l.id=a.location_id
                            WHERE a.task_id=?
                        """,(task["id"],)).fetchone()
                        if source:item["source_location"]=dict(source)
                    result.append(item)
            return result

    def claim_task(self, *, store, task_id, session_id, employee_id):
        with self.transaction() as db:
            session=db.execute(
                "SELECT store,flow,stage,area FROM ac_sessions "
                "WHERE id=? AND employee_id=? AND status='active'",
                (session_id,employee_id)
            ).fetchone()
            task=db.execute("SELECT * FROM ac_tasks WHERE id=? AND store=?",(task_id,store)).fetchone()
            if not session or session["store"]!=store or not task:
                raise ValueError("Tarea o sesión no autorizada")
            if any(session[key]!=task[key] for key in ("flow","stage","area")):
                raise ValueError("La tarea pertenece a otra actividad")
            if task["status"]=="in_progress" and task["assigned_to"]==employee_id:
                return task_id
            if task["status"]!="pending":
                raise ValueError("La tarea ya fue tomada por otro colaborador")
            changed=db.execute(
                "UPDATE ac_tasks SET status='in_progress',assigned_to=? "
                "WHERE id=? AND status='pending'",
                (employee_id,task_id)
            ).rowcount
            if not changed:
                raise ValueError("La tarea ya no está disponible")
            return task_id

    def capture(self, *, event_key, session_id, employee_id, model_id,
                color="", sizes, task_id=None, target_location_id=None):
        """Captura, descuenta la tarea y encola la siguiente etapa EN UNA transacción.

        Una pieza sigue siendo la misma al pasar por varias actividades.
        Las capturas registran productividad, no ingresos físicos adicionales.
        """
        pieces = normalize_sizes(sizes)
        event_key = require_text(event_key, "Clave de evento")
        model_id = require_text(model_id, "ID de modelo")
        with self.transaction() as db:
            existing = db.execute("SELECT id FROM ac_captures WHERE event_key=?", (event_key,)).fetchone()
            if existing:
                previous = db.execute(
                    "SELECT * FROM ac_captures WHERE id=?", (existing["id"],)
                ).fetchone()
                old_sizes = {
                    r["size"]:r["pieces"] for r in db.execute(
                        "SELECT size,pieces FROM ac_capture_sizes WHERE capture_id=?",
                        (existing["id"],)
                    )
                }
                link = db.execute(
                    "SELECT task_id FROM ac_task_captures WHERE capture_id=?",
                    (existing["id"],)
                ).fetchone()
                old_task_id = link["task_id"] if link else None
                destination=db.execute(
                    "SELECT location_id FROM ac_capture_destinations WHERE capture_id=?",
                    (existing["id"],)
                ).fetchone()
                old_destination=destination["location_id"] if destination else None
                if (not previous or previous["session_id"] != session_id
                        or previous["created_by"] != employee_id
                        or previous["model_id"] != model_id
                        or previous["color"] != str(color or "")
                        or old_sizes != pieces or old_task_id != task_id
                        or old_destination != target_location_id):
                    raise ValueError("Clave de evento reutilizada con datos diferentes")
                return existing["id"]

            s = db.execute(
                "SELECT * FROM ac_sessions WHERE id=? AND employee_id=?",
                (session_id,employee_id)
            ).fetchone()
            if not s or s["status"] != "active":
                raise ValueError("Sesión no activa o colaborador no autorizado")

            # Acondicionar y Ubicar sólo se capturan mediante una tarea previa.
            if not task_id and s["stage"] in {"Acondicionar","Ubicar"}:
                raise ValueError("Selecciona una tarea pendiente antes de registrar piezas")
            # Resurtido necesita un pedido validado antes de autorizar Pizca.
            # No se permite inventar mercancía mediante una captura libre.
            if not task_id and s["flow"]=="Resurtido" and s["stage"]=="Pizca":
                raise ValueError("Pizca requiere pedido de resurtido confirmado")
            if not task_id and not (
                (s["flow"]=="Surtido" and s["stage"] in {"Separar","Excedentes"})
                or (s["flow"]=="Resurtido" and s["stage"]=="Excedentes")
            ):
                raise ValueError("Actividad inicial no habilitada sin tarea")

            if task_id:
                task = db.execute("SELECT * FROM ac_tasks WHERE id=?", (task_id,)).fetchone()
                if (not task or task["store"] != s["store"]
                        or task["flow"] != s["flow"] or task["stage"] != s["stage"]
                        or task["area"] != s["area"] or task["model_id"] != model_id
                        or task["color"] != str(color or "")
                        or task["assigned_to"] != employee_id
                        or task["status"] != "in_progress"):
                    raise ValueError("Tarea ajena, vencida o no asignada")
                for size,qty in pieces.items():
                    changed = db.execute(
                        "UPDATE ac_task_sizes SET completed=completed+? "
                        "WHERE task_id=? AND size=? AND total-completed>=?",
                        (qty,task_id,size,qty)
                    ).rowcount
                    if not changed:
                        raise ValueError(f"Las piezas de {size} exceden el pendiente")
                missing = db.execute(
                    "SELECT 1 FROM ac_task_sizes WHERE task_id=? AND completed<total LIMIT 1",
                    (task_id,)
                ).fetchone()
                if not missing:
                    db.execute(
                        "UPDATE ac_tasks SET status='completed',finished_at=? WHERE id=?",
                        (timestamp(),task_id)
                    )

            if target_location_id and not (
                s["flow"]=="Resurtido" and s["stage"]=="Ubicar"
            ):
                raise ValueError("Ubicación de destino no corresponde a esta actividad")

            # Pedido aprobado: Pizca consume reserva y traslada a Tránsito,
            # sin aumentar el inventario en piso antes de Ubicar.
            if s["flow"]=="Resurtido" and s["stage"]=="Pizca":
                if not task_id:
                    raise ValueError("Pizca requiere pedido autorizado")
                order_line=db.execute(
                    "SELECT * FROM ac_order_lines WHERE task_id=?",(task_id,)
                ).fetchone()
                if not order_line:
                    raise ValueError("Tarea de Pizca sin reserva validada")
                if set(pieces)!={order_line["size"]}:
                    raise ValueError("La Pizca debe registrar la talla reservada")
                qty=pieces[order_line["size"]]
                changed=db.execute(
                    "UPDATE ac_order_lines SET completed=completed+? "
                    "WHERE id=? AND pieces-completed>=?",
                    (qty,order_line["id"],qty)
                ).rowcount
                if changed!=1:
                    raise ValueError("Piezas superiores a la reserva")
                source=db.execute(
                    "UPDATE ac_stock SET pieces=pieces-?, reserved=reserved-? "
                    "WHERE store=? AND location_id=? AND model_id=? AND size=? "
                    "AND reserved>=? AND pieces>=?",
                    (qty,qty,s["store"],order_line["location_id"],model_id,
                     order_line["size"],qty,qty)
                ).rowcount
                if source!=1:
                    raise ValueError("Existencia reservada ya no coincide")
                transit=db.execute(
                    "SELECT id FROM ac_locations WHERE store=? AND kind='Transito' "
                    "AND aisle='RESURTIDO' AND active=1",
                    (s["store"],)
                ).fetchone()
                if not transit:
                    transit_id=uuid.uuid4().hex
                    db.execute(
                        "INSERT INTO ac_locations(id,store,kind,aisle) "
                        "VALUES(?,?,'Transito','RESURTIDO')",
                        (transit_id,s["store"])
                    )
                else:
                    transit_id=transit["id"]
                db.execute(
                    "INSERT INTO ac_stock(store,location_id,model_id,size,pieces) "
                    "VALUES(?,?,?,?,?) ON CONFLICT(store,location_id,model_id,size) "
                    "DO UPDATE SET pieces=pieces+excluded.pieces",
                    (s["store"],transit_id,model_id,order_line["size"],qty)
                )
                remaining=db.execute(
                    "SELECT pieces-completed AS n FROM ac_order_lines WHERE id=?",
                    (order_line["id"],)
                ).fetchone()["n"]
                if not remaining:
                    db.execute(
                        "UPDATE ac_reservations SET status='fulfilled' "
                        "WHERE id=? AND status='active'",
                        (order_line["reservation_id"],)
                    )

            # Ubicar Resurtido requiere la ubicación física de destino,
            # para evitar declarar ubicada una pieza que sigue en Tránsito.
            if s["flow"]=="Resurtido" and s["stage"]=="Ubicar":
                if not target_location_id:
                    raise ValueError("Selecciona la ubicación de piso antes de Ubicar")
                floor_loc=db.execute(
                    "SELECT id FROM ac_locations "
                    "WHERE id=? AND store=? AND kind='Piso' AND active=1",
                    (target_location_id,s["store"])
                ).fetchone()
                if not floor_loc:
                    raise ValueError("Ubicación de piso inexistente o de otra tienda")
                transit=db.execute(
                    "SELECT id FROM ac_locations WHERE store=? AND kind='Transito' "
                    "AND aisle='RESURTIDO' AND active=1",
                    (s["store"],)
                ).fetchone()
                if not transit:
                    raise ValueError("No hay piezas de resurtido en Tránsito")
                for size,qty in pieces.items():
                    changed=db.execute(
                        "UPDATE ac_stock SET pieces=pieces-? WHERE "
                        "store=? AND location_id=? AND model_id=? AND size=? "
                        "AND pieces-reserved>=?",
                        (qty,s["store"],transit["id"],model_id,size,qty)
                    ).rowcount
                    if changed!=1:
                        raise ValueError("Piezas insuficientes en Tránsito para "+size)
                    db.execute(
                        "INSERT INTO ac_stock(store,location_id,model_id,size,pieces) "
                        "VALUES(?,?,?,?,?) ON CONFLICT(store,location_id,model_id,size) "
                        "DO UPDATE SET pieces=pieces+excluded.pieces",
                        (s["store"],target_location_id,model_id,size,qty)
                    )

            cid = uuid.uuid4().hex
            db.execute(
                "INSERT INTO ac_captures(id,event_key,store,model_id,color,flow,stage,"
                "area,session_id,recorded_at,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (cid,event_key,s["store"],model_id,str(color or ""),s["flow"],
                 s["stage"],s["area"],session_id,timestamp(),employee_id)
            )
            db.executemany(
                "INSERT INTO ac_capture_sizes(capture_id,size,pieces) VALUES(?,?,?)",
                [(cid,size,qty) for size,qty in pieces.items()]
            )
            if task_id:
                db.execute(
                    "INSERT INTO ac_task_captures(capture_id,task_id) VALUES(?,?)",
                    (cid,task_id)
                )
            if target_location_id:
                db.execute(
                    "INSERT INTO ac_capture_destinations(capture_id,location_id) VALUES(?,?)",
                    (cid,target_location_id)
                )

            next_stage = NEXT_STAGE.get((s["flow"],s["stage"]))
            if next_stage:
                new_id = uuid.uuid4().hex
                db.execute(
                    "INSERT INTO ac_tasks(id,source_capture_id,store,model_id,color,"
                    "flow,stage,area,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (new_id,cid,s["store"],model_id,str(color or ""),s["flow"],
                     next_stage,s["area"],timestamp())
                )
                db.executemany(
                    "INSERT INTO ac_task_sizes(task_id,size,total) VALUES(?,?,?)",
                    [(new_id,size,qty) for size,qty in pieces.items()]
                )
            return cid


    def add_location(self, *, store, kind, aisle="", face="", section="", level="", pallet=""):
        if kind not in STORAGE_KINDS:
            raise ValueError("Tipo de ubicación inválido")
        if kind == "Tarima" and not pallet:
            raise ValueError("Tarima requiere identificador")
        loc = (require_text(store,"Tienda"),kind,str(aisle),str(face),str(section),str(level),str(pallet))
        with self.transaction() as db:
            row = db.execute("""SELECT id FROM ac_locations WHERE
              store=? AND kind=? AND aisle=? AND face=? AND section=? AND level=? AND pallet=?""",loc).fetchone()
            if row:
                return row["id"]
            key=uuid.uuid4().hex
            db.execute("INSERT INTO ac_locations(id,store,kind,aisle,face,section,level,pallet) VALUES(?,?,?,?,?,?,?,?)",(key,*loc))
            return key

    def seed_verified_stock(self, *, store, location_id, model_id, sizes):
        """Carga inventario inicial conciliado. USO RESTRINGIDO a herramienta administrativa futura."""
        sizes=normalize_sizes(sizes)
        with self.transaction() as db:
            loc=db.execute("SELECT store FROM ac_locations WHERE id=?", (location_id,)).fetchone()
            if not loc or loc["store"] != store:
                raise ValueError("Ubicación de otra tienda")
            for size,pieces in sizes.items():
                row=db.execute("SELECT reserved FROM ac_stock WHERE store=? AND location_id=? AND model_id=? AND size=?",
                               (store,location_id,model_id,size)).fetchone()
                if row and row["reserved"]>pieces:
                    raise ValueError("No puede reducir inventario debajo de las reservas")
                db.execute("""INSERT INTO ac_stock(store,location_id,model_id,size,pieces) VALUES(?,?,?,?,?)
                ON CONFLICT(store,location_id,model_id,size) DO UPDATE SET pieces=excluded.pieces""",
                (store,location_id,model_id,size,pieces))

    def move(self, *, event_key, store, model_id, sizes, source, target, employee_id, partner_id=None):
        """Movimiento único (incluso si participaron dos colaboradores)."""
        sizes=normalize_sizes(sizes)
        if not source or not target or source==target:
            raise ValueError("Origen y destino deben ser distintos")
        result=[]
        with self.transaction() as db:
            existing=db.execute("SELECT id FROM ac_movement_batches WHERE event_key=?",(event_key,)).fetchone()
            if existing:
                detail=db.execute("SELECT store,model_id,from_location,to_location,created_by,partner_id,size,pieces FROM ac_movements WHERE batch_id=?",(existing["id"],)).fetchall()
                old_sizes={r["size"]:r["pieces"] for r in detail}
                if not detail or len(detail)!=len(sizes) or old_sizes!=sizes or any(r["store"]!=store or r["model_id"]!=model_id or r["from_location"]!=source or r["to_location"]!=target or r["created_by"]!=employee_id or r["partner_id"]!=partner_id for r in detail):
                    raise ValueError("Clave de movimiento reutilizada con datos diferentes")
                return existing["id"]
            locs=db.execute("SELECT id,store FROM ac_locations WHERE id IN (?,?)",(source,target)).fetchall()
            if len(locs)!=2 or any(x["store"]!=store for x in locs):
                raise ValueError("Las ubicaciones deben pertenecer a la tienda")
            movement_id=uuid.uuid4().hex
            db.execute("INSERT INTO ac_movement_batches(id,event_key,created_at) VALUES(?,?,?)",(movement_id,event_key,timestamp()))
            for size,qty in sizes.items():
                available=db.execute("SELECT pieces-reserved AS n FROM ac_stock WHERE store=? AND location_id=? AND model_id=? AND size=?",
                    (store,source,model_id,size)).fetchone()
                if not available or available["n"]<qty:
                    raise ValueError(f"Existencia insuficiente para {size}")
                db.execute("UPDATE ac_stock SET pieces=pieces-? WHERE store=? AND location_id=? AND model_id=? AND size=?",
                           (qty,store,source,model_id,size))
                db.execute("""INSERT INTO ac_stock(store,location_id,model_id,size,pieces) VALUES(?,?,?,?,?)
                ON CONFLICT(store,location_id,model_id,size) DO UPDATE SET pieces=pieces+excluded.pieces""",
                (store,target,model_id,size,qty))
                result.append((uuid.uuid4().hex,movement_id,event_key+":"+size,store,model_id,size,qty,source,target,employee_id,partner_id,timestamp()))
            db.executemany("""INSERT INTO ac_movements(id,batch_id,event_key,store,model_id,size,pieces,from_location,to_location,created_by,partner_id,captured_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",result)
            return movement_id

    def reserve(self, *, event_key, store, location_id, model_id, size, pieces, requested_by):
        if type(pieces) is not int or pieces<=0:
            raise ValueError("Cantidad inválida")
        with self.transaction() as db:
            old=db.execute("SELECT id FROM ac_reservations WHERE event_key=?", (event_key,)).fetchone()
            if old:
                return old["id"]
            loc=db.execute("SELECT kind,store FROM ac_locations WHERE id=?", (location_id,)).fetchone()
            if not loc or loc["store"]!=store or loc["kind"] not in {"Septimos","Tarima"}:
                raise ValueError("Sólo se permite reservar en séptimos o tarimas de la tienda")
            available=db.execute("SELECT pieces-reserved AS n FROM ac_stock WHERE store=? AND location_id=? AND model_id=? AND size=?",
                                 (store,location_id,model_id,size.upper())).fetchone()
            if not available or available["n"]<pieces:
                raise ValueError("Excedente insuficiente o reservado")
            rid=uuid.uuid4().hex
            db.execute("UPDATE ac_stock SET reserved=reserved+? WHERE store=? AND location_id=? AND model_id=? AND size=?",
                       (pieces,store,location_id,model_id,size.upper()))
            db.execute("INSERT INTO ac_reservations(id,event_key,store,location_id,model_id,size,pieces,requested_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       (rid,event_key,store,location_id,model_id,size.upper(),pieces,requested_by,timestamp()))
            return rid

    def available(self, store, location_id, model_id, size):
        with self.transaction() as db:
            row=db.execute("SELECT pieces,reserved FROM ac_stock WHERE store=? AND location_id=? AND model_id=? AND size=?",
                           (store,location_id,model_id,size.upper())).fetchone()
            return {"pieces":row["pieces"],"reserved":row["reserved"],"available":row["pieces"]-row["reserved"]} if row else {"pieces":0,"reserved":0,"available":0}

def suggested_quantity(goal, physical_floor, available_surplus):
    """Por talla. Nunca confundir piso físico con piso reportado que incluye séptimos."""
    if any(type(n) is not int or n<0 for n in (goal,physical_floor,available_surplus)):
        raise ValueError("Las cantidades deben ser enteros no negativos")
    return min(max(goal-physical_floor,0),available_surplus)
