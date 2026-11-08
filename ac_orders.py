"""Pedidos de Resurtido AC: aprobación atómica y reservas por talla.

Sólo se construye un pedido cuando hay corte de capacidades, existencia física
de Piso registrada y excedente disponible de Séptimos/Tarima. Nunca utiliza
inventario de Rack para el sugerido ni duplica las reservas existentes.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from ac_storage import AREAS, require_text, timestamp

ORDER_SCHEMA = """
CREATE TABLE IF NOT EXISTS ac_orders (
 id TEXT PRIMARY KEY,
 event_key TEXT NOT NULL UNIQUE,
 store TEXT NOT NULL, model_id TEXT NOT NULL, area TEXT NOT NULL,
 criterion TEXT NOT NULL CHECK(criterion IN ('curve','capacity')),
 size_filter_json TEXT NOT NULL,
 requested_by TEXT NOT NULL, approver_role TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('approved','completed')),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ac_order_lines (
 id TEXT PRIMARY KEY,
 order_id TEXT NOT NULL REFERENCES ac_orders(id),
 task_id TEXT NOT NULL UNIQUE REFERENCES ac_tasks(id),
 reservation_id TEXT NOT NULL UNIQUE REFERENCES ac_reservations(id),
 location_id TEXT NOT NULL REFERENCES ac_locations(id),
 size TEXT NOT NULL, pieces INTEGER NOT NULL CHECK(pieces > 0),
 completed INTEGER NOT NULL DEFAULT 0 CHECK(completed>=0 AND completed<=pieces)
);
CREATE INDEX IF NOT EXISTS ac_order_lines_order ON ac_order_lines(order_id);
"""

def clean_sizes(sizes):
    if sizes is None:
        return None
    if not isinstance(sizes,list) or not sizes or len(sizes)>25:
        raise ValueError("Selecciona de 1 a 25 tallas")
    result=[require_text(s,"Talla").upper() for s in sizes]
    if len(set(result))!=len(result):
        raise ValueError("Tallas duplicadas")
    return sorted(result)


class OrderService:
    def __init__(self, bridge):
        self.bridge=bridge

    def initialize(self):
        # sqlite3.executescript confirma implícitamente las transacciones:
        # inicializar esquema fuera de ACStore.transaction().
        with sqlite3.connect(self.bridge.path,timeout=15) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(ORDER_SCHEMA)

    def _capacity_rows(self, db, store, model_id, selected):
        rows=db.execute("""
            SELECT s.size,s.curve,s.capacity,b.version
            FROM ac_capacity_excel_sizes s
            JOIN ac_capacity_excel_batches b ON b.id=s.batch_id
            WHERE s.store=? AND s.model=?
            ORDER BY b.id DESC
        """,(store,model_id)).fetchall()
        latest={}
        for row in rows:
            size=row["size"].upper()
            if size not in latest:
                latest[size]=dict(row)
        if selected is None:
            selected=sorted(latest)
        return selected,latest

    def _preview_locked(self, db, *, store, model_id, criterion, sizes):
        if criterion not in {"curve","capacity"}:
            raise ValueError("Criterio de capacidad no permitido")
        selected, caps=self._capacity_rows(db,store,model_id,clean_sizes(sizes))
        if not selected:
            raise ValueError("No existe un corte de capacidades por talla para este modelo")
        rows=[]
        for size in selected:
            cap=caps.get(size)
            if cap is None:
                rows.append({"size":size,"status":"missing_capacity","suggested":0})
                continue
            floor=db.execute("""
                SELECT COALESCE(SUM(s.pieces),0) AS pieces, COUNT(*) AS sources
                FROM ac_stock s JOIN ac_locations l ON l.id=s.location_id
                WHERE s.store=? AND l.store=? AND l.active=1 AND l.kind='Piso'
                  AND s.model_id=? AND s.size=?
            """,(store,store,model_id,size)).fetchone()
            if not floor["sources"]:
                rows.append({"size":size,"status":"missing_verified_floor",
                             "version":cap["version"],"suggested":0})
                continue
            surplus=db.execute("""
                SELECT s.location_id,l.kind,l.aisle,l.face,l.section,l.level,l.pallet,
                       s.pieces-s.reserved AS available
                FROM ac_stock s JOIN ac_locations l ON l.id=s.location_id
                WHERE s.store=? AND l.store=? AND l.active=1
                  AND l.kind IN ('Septimos','Tarima')
                  AND s.model_id=? AND s.size=? AND s.pieces>s.reserved
                ORDER BY CASE l.kind WHEN 'Septimos' THEN 0 ELSE 1 END,
                         l.aisle,l.face,l.section,l.level,l.pallet,s.location_id
            """,(store,store,model_id,size)).fetchall()
            goal=int(cap[criterion]); physical=int(floor["pieces"])
            total=sum(int(r["available"]) for r in surplus)
            suggested=min(max(goal-physical,0),total)
            status=("ready" if suggested else
                    "at_goal" if physical>=goal else "no_available_surplus")
            rows.append({"size":size,"goal":goal,"physical_floor":physical,
                         "available_surplus":total,"suggested":suggested,
                         "version":cap["version"],"status":status,
                         "sources":[dict(r) for r in surplus]})
        return rows

    def preview(self, *, store, model_id, area, criterion="curve", sizes=None):
        if area not in AREAS:
            raise ValueError("Área no autorizada")
        store=require_text(store,"Tienda")
        model_id=require_text(model_id,"ID de modelo")
        with self.bridge.operation.transaction() as db:
            rows=self._preview_locked(db,store=store,model_id=model_id,
                                      criterion=criterion,sizes=sizes)
        return {"store":store,"model_id":model_id,"area":area,
                "criterion":criterion,"sizes":rows,
                "total":sum(r["suggested"] for r in rows)}

    def approve(self, *, event_key, store, model_id, area, requested_by,
                approver_role, criterion="curve", sizes=None):
        if approver_role not in {"supervisor","gerente","admin","superadmin"}:
            raise ValueError("Sólo Supervisor y Gerente o Administradores pueden aprobar")
        if area not in AREAS or criterion not in {"curve","capacity"}:
            raise ValueError("Área o criterio inválido")
        event_key=require_text(event_key,"Clave de pedido")
        store=require_text(store,"Tienda")
        model_id=require_text(model_id,"ID de modelo")
        requested_by=require_text(requested_by,"Autorizador")
        selected=clean_sizes(sizes)
        signature=json.dumps(selected,ensure_ascii=False)
        with self.bridge.operation.transaction() as db:
            old=db.execute("SELECT * FROM ac_orders WHERE event_key=?",(event_key,)).fetchone()
            if old:
                if (old["store"]!=store or old["model_id"]!=model_id
                    or old["area"]!=area or old["criterion"]!=criterion
                    or old["size_filter_json"]!=signature
                    or old["requested_by"]!=requested_by
                    or old["approver_role"]!=approver_role):
                    raise ValueError("Clave de pedido reutilizada con datos diferentes")
                return self._summary_locked(db,old["id"])

            rows=self._preview_locked(db,store=store,model_id=model_id,
                                      criterion=criterion,sizes=selected)
            plan=[r for r in rows if r["suggested"]>0]
            if not plan:
                raise ValueError("No existe sugerido disponible y verificable para reservar")
            order_id=uuid.uuid4().hex
            db.execute("""INSERT INTO ac_orders
                (id,event_key,store,model_id,area,criterion,size_filter_json,
                 requested_by,approver_role,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,'approved',?)""",
                (order_id,event_key,store,model_id,area,criterion,signature,
                 requested_by,approver_role,timestamp()))

            for item in plan:
                remaining=int(item["suggested"])
                for source in item["sources"]:
                    qty=min(remaining,int(source["available"]))
                    if qty<=0:
                        continue
                    location_id=source["location_id"]
                    changed=db.execute("""UPDATE ac_stock SET reserved=reserved+?
                        WHERE store=? AND location_id=? AND model_id=? AND size=?
                          AND pieces-reserved>=?""",
                        (qty,store,location_id,model_id,item["size"],qty)).rowcount
                    if changed!=1:
                        raise ValueError("El excedente cambió antes de la autorización")
                    reservation_id=uuid.uuid4().hex
                    db.execute("""INSERT INTO ac_reservations
                        (id,event_key,store,location_id,model_id,size,pieces,
                         requested_by,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (reservation_id,event_key+":"+reservation_id,store,location_id,
                         model_id,item["size"],qty,requested_by,timestamp()))
                    task_id=uuid.uuid4().hex
                    db.execute("""INSERT INTO ac_tasks
                        (id,source_capture_id,store,model_id,color,flow,stage,area,created_at)
                        VALUES(?,NULL,?,?,'','Resurtido','Pizca',?,?)""",
                        (task_id,store,model_id,area,timestamp()))
                    db.execute("INSERT INTO ac_task_sizes(task_id,size,total) VALUES(?,?,?)",
                               (task_id,item["size"],qty))
                    db.execute("""INSERT INTO ac_order_lines
                        (id,order_id,task_id,reservation_id,location_id,size,pieces)
                        VALUES(?,?,?,?,?,?,?)""",
                        (uuid.uuid4().hex,order_id,task_id,reservation_id,
                         location_id,item["size"],qty))
                    remaining-=qty
                    if remaining==0:break
                if remaining:
                    raise ValueError("No fue posible reservar todas las piezas autorizadas")
            return self._summary_locked(db,order_id)

    def _summary_locked(self,db,order_id):
        order=dict(db.execute("SELECT * FROM ac_orders WHERE id=?",(order_id,)).fetchone())
        items=[dict(r) for r in db.execute("""
            SELECT a.task_id,a.location_id,l.kind,l.aisle,l.face,l.section,
                   l.level,l.pallet,a.size,a.pieces,a.completed,
                   (a.pieces-a.completed) AS remaining
            FROM ac_order_lines a JOIN ac_locations l ON l.id=a.location_id
            WHERE a.order_id=? ORDER BY a.size,l.kind,l.aisle,l.id
        """,(order_id,))]
        order["lines"]=items
        order["total"]=sum(r["pieces"] for r in items)
        order["picked"]=sum(r["completed"] for r in items)
        return order

    def list_orders(self, *, store, limit=30):
        with self.bridge.operation.transaction() as db:
            ids=db.execute("""SELECT id FROM ac_orders WHERE store=?
                ORDER BY created_at DESC,id DESC LIMIT ?""",(store,max(1,min(100,limit)))).fetchall()
            return [self._summary_locked(db,r["id"]) for r in ids]
