"""Pruebas de la cola AC: cadena de tareas y piezas conservadas."""
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from ac_bridge import ACBridge


@pytest.fixture
def ac():
    with tempfile.TemporaryDirectory() as d:
        bridge=ACBridge(Path(d))
        bridge.initialize()
        yield bridge


def session(ac, who, stage):
    return ac.start(store="Iztapalapa",employee_id=who,flow="Surtido",
                    stage=stage,area="Colgado")


def queue(ac, stage, who):
    return ac.tasks(store="Iztapalapa",flow="Surtido",stage=stage,
                    area="Colgado",employee_id=who)


def test_full_chain_and_exactly_one_initial_income(ac):
    s1=session(ac,"SEP","Separar")
    initial=ac.capture(event_key="initial-1",session_id=s1,employee_id="SEP",
                       model_id="914629",sizes={"XCH":5,"M":7,"G":6},color="ROSA")
    assert initial==ac.capture(event_key="initial-1",session_id=s1,employee_id="SEP",
                               model_id="914629",sizes={"XCH":5,"M":7,"G":6},color="ROSA")
    tasks=queue(ac,"Acondicionar","ACOND")
    assert len(tasks)==1
    assert tasks[0]["remaining"]=={"XCH":5,"M":7,"G":6}

    s2=session(ac,"ACOND","Acondicionar")
    task=tasks[0]["id"]
    assert ac.claim(store="Iztapalapa",task_id=task,session_id=s2,employee_id="ACOND")==task
    with pytest.raises(ValueError):
        ac.capture(event_key="too-much",session_id=s2,employee_id="ACOND",
                   task_id=task,model_id="914629",color="ROSA",sizes={"M":8})
    assert queue(ac,"Ubicar","UBIC")==[]

    partial=ac.capture(event_key="partial-1",session_id=s2,employee_id="ACOND",
                       task_id=task,model_id="914629",color="ROSA",sizes={"XCH":5,"M":2})
    assert partial==ac.capture(event_key="partial-1",session_id=s2,employee_id="ACOND",
                               task_id=task,model_id="914629",color="ROSA",sizes={"XCH":5,"M":2})
    remaining=queue(ac,"Acondicionar","ACOND")
    assert remaining[0]["remaining"]=={"M":5,"G":6}
    assert len(queue(ac,"Ubicar","UBIC"))==1

    ac.capture(event_key="partial-2",session_id=s2,employee_id="ACOND",
               task_id=task,model_id="914629",color="ROSA",sizes={"M":5,"G":6})
    assert queue(ac,"Acondicionar","ACOND")==[]
    assert len(queue(ac,"Ubicar","UBIC"))==2

    s3=session(ac,"UBIC","Ubicar")
    for row in queue(ac,"Ubicar","UBIC"):
        ac.claim(store="Iztapalapa",task_id=row["id"],session_id=s3,employee_id="UBIC")
        ac.capture(event_key="ubicar-"+row["id"],session_id=s3,employee_id="UBIC",
                   task_id=row["id"],model_id=row["model_id"],
                   color=row["color"],sizes=row["remaining"])
    assert queue(ac,"Ubicar","UBIC")==[]

    with ac.operation.transaction() as db:
        counts={row["stage"]:row["pieces"] for row in db.execute("""
            SELECT c.stage,SUM(s.pieces) AS pieces
            FROM ac_captures c JOIN ac_capture_sizes s ON s.capture_id=c.id
            GROUP BY c.stage""")}
        assert counts=={"Separar":18,"Acondicionar":18,"Ubicar":18}
        assert db.execute("SELECT COUNT(*) FROM ac_tasks").fetchone()[0]==3
        # Una pieza separada y luego ubicada no es una pieza adicional recibida.
        assert counts["Separar"]==18


def test_claim_prevents_duplicate_and_cross_store(ac):
    origin=session(ac,"SEP","Separar")
    ac.capture(event_key="initial",session_id=origin,employee_id="SEP",
               model_id="111",sizes={"M":10})
    task=queue(ac,"Acondicionar","A")[0]["id"]
    a=session(ac,"A","Acondicionar")
    b=session(ac,"B","Acondicionar")
    ac.claim(store="Iztapalapa",task_id=task,session_id=a,employee_id="A")
    with pytest.raises(ValueError):
        ac.claim(store="Iztapalapa",task_id=task,session_id=b,employee_id="B")
    with pytest.raises(ValueError):
        ac.claim(store="Vallejo",task_id=task,session_id=b,employee_id="B")
    with pytest.raises(ValueError):
        ac.capture(event_key="fraud",session_id=b,employee_id="B",task_id=task,
                   model_id="111",sizes={"M":1})
    with pytest.raises(ValueError):
        ac.capture(event_key="without-task",session_id=b,employee_id="B",
                   model_id="111",sizes={"M":1})


def test_partial_task_returned_when_worker_finishes(ac):
    origin=session(ac,"SEP","Separar")
    ac.capture(event_key="initial",session_id=origin,employee_id="SEP",
               model_id="111",sizes={"M":10})
    task=queue(ac,"Acondicionar","A")[0]["id"]
    a=session(ac,"A","Acondicionar")
    ac.claim(store="Iztapalapa",task_id=task,session_id=a,employee_id="A")
    ac.capture(event_key="first-half",session_id=a,employee_id="A",
               task_id=task,model_id="111",sizes={"M":4})
    ac.finish(a,"A")
    pending=queue(ac,"Acondicionar","B")
    assert len(pending)==1 and pending[0]["remaining"]=={"M":6}
    b=session(ac,"B","Acondicionar")
    ac.claim(store="Iztapalapa",task_id=task,session_id=b,employee_id="B")
    ac.capture(event_key="second-half",session_id=b,employee_id="B",
               task_id=task,model_id="111",sizes={"M":6})
    assert len(queue(ac,"Ubicar","U"))==2


def test_concurrent_claim_only_one_winner(ac):
    sid=session(ac,"SEP","Separar")
    ac.capture(event_key="seed",session_id=sid,employee_id="SEP",
               model_id="2",sizes={"M":3})
    task=queue(ac,"Acondicionar","A")[0]["id"]
    sessions=[session(ac,v,"Acondicionar") for v in ("A","B")]
    def attempt(item):
        name,session_id=item
        try:
            ac.claim(store="Iztapalapa",task_id=task,
                     session_id=session_id,employee_id=name)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,zip(("A","B"),sessions)))
    assert sorted(results)==[False,True]


def test_resurtido_pizca_requires_approved_order(ac):
    sid=ac.start(store="Iztapalapa",employee_id="R",flow="Resurtido",
                 stage="Pizca",area="Colgado")
    with pytest.raises(ValueError,match="pedido"):
        ac.capture(event_key="no-order",session_id=sid,employee_id="R",
                   model_id="111",sizes={"M":3})
