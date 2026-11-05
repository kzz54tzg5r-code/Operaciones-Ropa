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
AREAS = {"Colgado", "Doblado"}
STORAGE_KINDS = {"Piso", "Rack", "Septimos", "Tarima", "Transito"}
SESSION_STATES = {"active", "paused", "finished"}
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
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA)

    def start_session(self, store, employee_id, flow, stage, area):
        if flow not in FLOWS or stage not in STAGES or area not in AREAS:
            raise ValueError("Proceso, actividad o clasificación inválido")
        sid = uuid.uuid4().hex
        with self.transaction() as db:
            db.execute("INSERT INTO ac_sessions(id,store,employee_id,flow,stage,area,started_at) VALUES(?,?,?,?,?,?,?)",
                       (sid,require_text(store,"Tienda"),require_text(employee_id,"Colaborador"),flow,stage,area,timestamp()))
        return sid

    def finish_session(self, sid, employee_id):
        with self.transaction() as db:
            changed = db.execute("UPDATE ac_sessions SET status='finished',ended_at=? WHERE id=? AND employee_id=? AND status IN ('active','paused')",
                                 (timestamp(),sid,employee_id)).rowcount
            if not changed:
                raise ValueError("La sesión no existe, no pertenece al colaborador o ya finalizó")

    def capture(self, *, event_key, session_id, employee_id, model_id, color="", sizes):
        """Guarda una captura validada una sola vez, incluso ante reintentos de red."""
        pieces = normalize_sizes(sizes)
        event_key = require_text(event_key, "Clave de evento")
        model_id = require_text(model_id, "ID de modelo")
        with self.transaction() as db:
            existing = db.execute("SELECT id FROM ac_captures WHERE event_key=?", (event_key,)).fetchone()
            if existing:
                return existing["id"]
            s = db.execute("SELECT * FROM ac_sessions WHERE id=? AND employee_id=?", (session_id,employee_id)).fetchone()
            if not s or s["status"] != "active":
                raise ValueError("Sesión no activa o colaborador no autorizado")
            cid = uuid.uuid4().hex
            db.execute("INSERT INTO ac_captures(id,event_key,store,model_id,color,flow,stage,area,session_id,recorded_at,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (cid,event_key,s["store"],model_id,str(color or ""),s["flow"],s["stage"],s["area"],session_id,timestamp(),employee_id))
            db.executemany("INSERT INTO ac_capture_sizes(capture_id,size,pieces) VALUES(?,?,?)",
                           [(cid,size,qty) for size,qty in pieces.items()])
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
