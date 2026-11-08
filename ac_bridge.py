"""Integración AC aislada. No registra endpoints ni altera la app productiva."""
from __future__ import annotations
from pathlib import Path
from ac_capacities import CapacityStore
from ac_storage import ACStore, suggested_quantity
from ac_orders import OrderService

class ACBridge:
    def __init__(self, data_directory):
        self.path=Path(data_directory)/"propuesta_ac.sqlite3"
        self.capacities=CapacityStore(self.path)
        self.operation=ACStore(self.path)
        self.orders=OrderService(self)

    def initialize(self):
        self.operation.initialize()
        self.capacities.initialize()
        self.orders.initialize()

    def upload_capacities(self, excel_bytes, *, version, admin_user):
        """Única carga Excel del módulo nuevo; permisos se verifican en el servidor."""
        return self.capacities.upload(excel_bytes, version=version, uploaded_by=admin_user)

    def start(self, *, store, employee_id, flow, stage, area):
        return self.operation.start_session(store,employee_id,flow,stage,area)

    def capture(self, *, event_key, session_id, employee_id, model_id, sizes,
                color="", task_id=None):
        """Un movimiento operativo y su siguiente tarea se confirman juntos."""
        return self.operation.capture(event_key=event_key,session_id=session_id,
            employee_id=employee_id,model_id=model_id,color=color,sizes=sizes,
            task_id=task_id)

    def tasks(self, *, store, flow, stage, area, employee_id):
        return self.operation.list_tasks(store=store,flow=flow,stage=stage,
                                         area=area,employee_id=employee_id)

    def claim(self, *, store, task_id, session_id, employee_id):
        return self.operation.claim_task(store=store,task_id=task_id,
                                         session_id=session_id,employee_id=employee_id)

    def finish(self, session_id, employee_id):
        return self.operation.finish_session(session_id,employee_id)

    def suggest(self, *, store, model_id, size, criterion="curve"):
        """Sugerido informativo por talla; no crea pedido ni reserva automáticamente."""
        if criterion not in {"curve","capacity"}:raise ValueError("Criterio inválido")
        cap=self.capacities.latest(store,model_id,size)
        if cap is None:return {"status":"missing_capacity","suggested":0}
        with self.operation.transaction() as db:
            rows=db.execute("""SELECT l.kind,COALESCE(SUM(s.pieces),0) AS pieces,
              COALESCE(SUM(s.pieces-s.reserved),0) AS available
              FROM ac_stock s JOIN ac_locations l ON l.id=s.location_id
              WHERE s.store=? AND l.store=? AND s.model_id=? AND s.size=? AND l.active=1
              GROUP BY l.kind""",(store,store,model_id,size.upper())).fetchall()
        values={r["kind"]:dict(r) for r in rows}
        floor=int(values.get("Piso",{}).get("pieces",0))
        surplus=sum(int(values.get(kind,{}).get("available",0)) for kind in ("Septimos","Tarima"))
        goal=int(cap[criterion])
        return {"status":"calculated","version":cap["version"],"store":store,"model_id":model_id,
                "size":size.upper(),"criterion":criterion,"goal":goal,
                "physical_floor":floor,"available_surplus":surplus,
                "suggested":suggested_quantity(goal,floor,surplus)}
