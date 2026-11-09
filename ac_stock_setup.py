"""Conteo físico inicial AC (sólo capturas, ningún Excel nuevo).

La primera existencia por tienda/ubicación/modelo/talla debe ser verificada
explícitamente por un responsable. Nunca crea inventario por defecto ni
sobrescribe reservas o movimientos ya registrados. Auditoría inmutable.
"""
from __future__ import annotations
import sqlite3
import uuid
from ac_storage import STORAGE_KINDS, normalize_sizes, require_text, timestamp

SCHEMA = """
CREATE TABLE IF NOT EXISTS ac_stock_initial_counts (
 id TEXT PRIMARY KEY,
 event_key TEXT NOT NULL UNIQUE,
 store TEXT NOT NULL,
 location_id TEXT NOT NULL REFERENCES ac_locations(id),
 model_id TEXT NOT NULL,
 size TEXT NOT NULL,
 pieces INTEGER NOT NULL CHECK(pieces>=0),
 verified_by TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(store,location_id,model_id,size)
);
CREATE INDEX IF NOT EXISTS ac_initial_counts_store ON ac_stock_initial_counts(store,created_at);
"""

class StockSetup:
    def __init__(self,bridge):
        self.bridge=bridge

    def initialize(self):
        with sqlite3.connect(self.bridge.path,timeout=15) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA)

    def add_location(self, *, store, kind, aisle="", face="", section="",level="",pallet=""):
        if kind not in {"Piso","Rack","Septimos","Tarima"}:
            raise ValueError("Tipo de ubicación inválido")
        return self.bridge.operation.add_location(
            store=store,kind=kind,aisle=aisle,face=face,section=section,
            level=level,pallet=pallet
        )

    def initial_count(self, *, event_key, store, location_id, model_id,
                      size, pieces, verified_by):
        if not isinstance(pieces,int) or isinstance(pieces,bool) or pieces<0:
            raise ValueError("El conteo debe ser un entero no negativo")
        store=require_text(store,"Tienda")
        location_id=require_text(location_id,"Ubicación")
        model_id=require_text(model_id,"ID artículo")
        size=require_text(size,"Talla").upper()
        verified_by=require_text(verified_by,"Responsable")
        event_key=require_text(event_key,"Clave de conteo")
        with self.bridge.operation.transaction() as db:
            old=db.execute(
                "SELECT * FROM ac_stock_initial_counts WHERE event_key=?",
                (event_key,)
            ).fetchone()
            if old:
                if any((old["store"]!=store,old["location_id"]!=location_id,
                        old["model_id"]!=model_id,old["size"]!=size,
                        old["pieces"]!=pieces,old["verified_by"]!=verified_by)):
                    raise ValueError("Clave de conteo reutilizada con distintos datos")
                return old["id"]
            loc=db.execute(
                "SELECT id FROM ac_locations WHERE id=? AND store=? AND active=1",
                (location_id,store)
            ).fetchone()
            if not loc:
                raise ValueError("Ubicación ajena a tienda o inactiva")
            existing=db.execute(
                "SELECT pieces,reserved FROM ac_stock WHERE store=? "
                "AND location_id=? AND model_id=? AND size=?",
                (store,location_id,model_id,size)
            ).fetchone()
            if existing:
                raise ValueError("La existencia ya fue registrada o movida; no se permite sobrescribirla")
            if db.execute(
                "SELECT 1 FROM ac_stock_initial_counts WHERE "
                "store=? AND location_id=? AND model_id=? AND size=?",
                (store,location_id,model_id,size)
            ).fetchone():
                raise ValueError("El conteo inicial ya existe")
            code=uuid.uuid4().hex
            db.execute(
                "INSERT INTO ac_stock_initial_counts "
                "(id,event_key,store,location_id,model_id,size,pieces,verified_by,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (code,event_key,store,location_id,model_id,size,pieces,verified_by,timestamp())
            )
            db.execute(
                "INSERT INTO ac_stock(store,location_id,model_id,size,pieces) VALUES(?,?,?,?,?)",
                (store,location_id,model_id,size,pieces)
            )
            return code

    def locations(self, *, store, kind=""):
        with self.bridge.operation.transaction() as db:
            rows=db.execute(
                "SELECT id,kind,aisle,face,section,level,pallet FROM ac_locations "
                "WHERE store=? AND active=1 AND (?='' OR kind=?) "
                "ORDER BY kind,aisle,face,section,level,pallet",
                (store,kind,kind)
            ).fetchall()
            return [dict(row) for row in rows]

    def stock(self, *, store, model_id):
        with self.bridge.operation.transaction() as db:
            rows=db.execute("""
                SELECT s.location_id,l.kind,l.aisle,l.face,l.section,l.level,l.pallet,
                       s.size,s.pieces,s.reserved,(s.pieces-s.reserved) AS available
                FROM ac_stock s JOIN ac_locations l ON l.id=s.location_id
                WHERE s.store=? AND l.store=? AND s.model_id=? AND l.active=1
                ORDER BY l.kind,l.aisle,s.size
            """,(store,store,model_id)).fetchall()
            return [dict(row) for row in rows]
