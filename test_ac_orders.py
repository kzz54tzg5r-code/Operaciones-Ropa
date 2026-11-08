"""Pedidos AC: capacidades reales simuladas, reservas atómicas y resurtido completo."""
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from io import BytesIO
import pytest
from openpyxl import Workbook
from ac_bridge import ACBridge


def capacities():
    book=Workbook()
    sheet=book.active
    sheet.append(["TIENDA","ID_ART","TALLA","CURVA","CAPACIDAD"])
    sheet.append(["Iztapalapa","914629","M",18,20])
    sheet.append(["Iztapalapa","914629","G",12,14])
    out=BytesIO();book.save(out);book.close()
    return out.getvalue()


@pytest.fixture
def setup():
    with tempfile.TemporaryDirectory() as temp:
        bridge=ACBridge(temp);bridge.initialize()
        bridge.upload_capacities(capacities(),version="Corte-A",admin_user="admin")
        floor=bridge.operation.add_location(store="Iztapalapa",kind="Piso",aisle="03")
        sep=bridge.operation.add_location(store="Iztapalapa",kind="Septimos",aisle="07",level="3")
        tar=bridge.operation.add_location(store="Iztapalapa",kind="Tarima",pallet="T08")
        bridge.operation.seed_verified_stock(store="Iztapalapa",location_id=floor,
            model_id="914629",sizes={"M":7,"G":3})
        bridge.operation.seed_verified_stock(store="Iztapalapa",location_id=sep,
            model_id="914629",sizes={"M":9,"G":3})
        bridge.operation.seed_verified_stock(store="Iztapalapa",location_id=tar,
            model_id="914629",sizes={"M":8,"G":8})
        yield bridge,floor,sep,tar


def approve(ac,key,sizes=None):
    return ac.approve_order(
        event_key=key,store="Iztapalapa",model_id="914629",area="Colgado",
        requested_by="G1",approver_role="gerente",sizes=sizes)


def test_preview_requires_verified_floor_and_capacity(setup):
    ac,*_=setup
    p=ac.order_preview(store="Iztapalapa",model_id="914629",area="Colgado")
    vals={x["size"]:x for x in p["sizes"]}
    assert vals["M"]["suggested"]==11
    assert vals["G"]["suggested"]==9
    assert p["total"]==20
    other=ac.order_preview(store="Vallejo",model_id="914629",area="Colgado",sizes=["M"])
    assert other["sizes"][0]["status"]=="missing_capacity"


def test_approve_reserves_exactly_once_and_blocks_second_order(setup):
    ac,floor,sep,tar=setup
    order=approve(ac,"pedido-000001",["M"])
    assert order["total"]==11
    assert approve(ac,"pedido-000001",["M"])["id"]==order["id"]
    assert ac.operation.available("Iztapalapa",sep,"914629","M")["reserved"]==9
    assert ac.operation.available("Iztapalapa",tar,"914629","M")["reserved"]==2
    new=ac.order_preview(store="Iztapalapa",model_id="914629",area="Colgado",sizes=["M"])
    assert new["sizes"][0]["incoming"]==11
    assert new["sizes"][0]["suggested"]==0
    with pytest.raises(ValueError):
        approve(ac,"pedido-000002",["M"])
    assert len(ac.list_orders(store="Iztapalapa"))==1
    with pytest.raises(ValueError,match="reutilizada"):
        ac.approve_order(event_key="pedido-000001",store="Vallejo",
            model_id="914629",area="Colgado",requested_by="G1",
            approver_role="gerente",sizes=["M"])


def test_pickup_to_transit_then_to_floor_without_double_inventory(setup):
    ac,floor,sep,tar=setup
    order=approve(ac,"pedido-000003",["M"])
    assert order["total"]==11
    sid=ac.start(store="Iztapalapa",employee_id="PICK",flow="Resurtido",
                 stage="Pizca",area="Colgado")
    pick_tasks=ac.tasks(store="Iztapalapa",flow="Resurtido",stage="Pizca",
                        area="Colgado",employee_id="PICK")
    assert len(pick_tasks)==2
    for n,task in enumerate(pick_tasks):
        ac.claim(store="Iztapalapa",task_id=task["id"],session_id=sid,employee_id="PICK")
        args=dict(event_key="pizca-000"+str(n),session_id=sid,employee_id="PICK",
                  task_id=task["id"],model_id="914629",sizes=task["remaining"])
        assert ac.capture(**args)==ac.capture(**args)
    assert ac.operation.available("Iztapalapa",sep,"914629","M")["pieces"]==0
    assert ac.operation.available("Iztapalapa",tar,"914629","M")["pieces"]==6
    assert ac.operation.available("Iztapalapa",floor,"914629","M")["pieces"]==7
    with ac.operation.transaction() as db:
        transit=db.execute(
            "SELECT id FROM ac_locations WHERE store='Iztapalapa' "
            "AND kind='Transito' AND aisle='RESURTIDO'"
        ).fetchone()["id"]
    assert ac.operation.available("Iztapalapa",transit,"914629","M")["pieces"]==11
    assert ac.operation.available("Iztapalapa",sep,"914629","M")["reserved"]==0
    assert ac.operation.available("Iztapalapa",tar,"914629","M")["reserved"]==0

    sid2=ac.start(store="Iztapalapa",employee_id="COND",flow="Resurtido",
                  stage="Acondicionar",area="Colgado")
    for n,task in enumerate(ac.tasks(store="Iztapalapa",flow="Resurtido",
                                      stage="Acondicionar",area="Colgado",employee_id="COND")):
        ac.claim(store="Iztapalapa",task_id=task["id"],session_id=sid2,employee_id="COND")
        ac.capture(event_key="acond-000"+str(n),session_id=sid2,employee_id="COND",
                   model_id="914629",task_id=task["id"],sizes=task["remaining"])

    sid3=ac.start(store="Iztapalapa",employee_id="UBIC",flow="Resurtido",
                  stage="Ubicar",area="Colgado")
    for n,task in enumerate(ac.tasks(store="Iztapalapa",flow="Resurtido",
                                      stage="Ubicar",area="Colgado",employee_id="UBIC")):
        ac.claim(store="Iztapalapa",task_id=task["id"],session_id=sid3,employee_id="UBIC")
        kwargs=dict(event_key="ubic-000"+str(n),session_id=sid3,
                    employee_id="UBIC",model_id="914629",task_id=task["id"],
                    sizes=task["remaining"],target_location_id=floor)
        assert ac.capture(**kwargs)==ac.capture(**kwargs)
    assert ac.operation.available("Iztapalapa",transit,"914629","M")["pieces"]==0
    assert ac.operation.available("Iztapalapa",floor,"914629","M")["pieces"]==18
    with ac.operation.transaction() as db:
        totals={row["stage"]:row["count"] for row in db.execute(
            "SELECT c.stage,SUM(cs.pieces) count FROM ac_captures c "
            "JOIN ac_capture_sizes cs ON cs.capture_id=c.id WHERE c.flow='Resurtido' "
            "GROUP BY c.stage"
        )}
    assert totals=={"Pizca":11,"Acondicionar":11,"Ubicar":11}


def test_unapproved_pizca_and_cross_store_floor_rejected(setup):
    ac,floor,*_=setup
    sid=ac.start(store="Iztapalapa",employee_id="PICK",flow="Resurtido",
                 stage="Pizca",area="Colgado")
    with pytest.raises(ValueError):
        ac.capture(event_key="unapproved-pick",session_id=sid,employee_id="PICK",
                   model_id="914629",sizes={"M":3})
    order=approve(ac,"pedido-000004",["M"])
    sid2=ac.start(store="Iztapalapa",employee_id="COND",flow="Resurtido",
                 stage="Acondicionar",area="Colgado")
    with pytest.raises(ValueError):
        ac.capture(event_key="unapproved-cond",session_id=sid2,employee_id="COND",
                   model_id="914629",sizes={"M":1})


def test_parallel_approvals_dont_exceed_target(setup):
    ac,*_=setup
    def attempt(i):
        try:
            return ac.approve_order(
                event_key=f"parallel-order-{i}",store="Iztapalapa",
                model_id="914629",area="Colgado",requested_by=f"G{i}",
                approver_role="gerente",sizes=["M"])["total"]
        except ValueError:
            return 0
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,range(2)))
    assert sum(results)==11


def test_only_authorized_roles_can_approve(setup):
    ac,*_=setup
    with pytest.raises(ValueError):
        ac.approve_order(event_key="not-manager",store="Iztapalapa",
            model_id="914629",area="Colgado",requested_by="EMP",
            approver_role="colaborador_operativo",sizes=["M"])
