"""V390: Ingresado sólo desde operación de tiendas Proyecto.

El comparativo comercial de recuperación conserva el alcance de todas las
tiendas; ni sus DEV ni sus cantidades de venta se suman a Ingresado.
"""
import asyncio
from types import SimpleNamespace
from fastapi import FastAPI
from starlette.requests import Request

from v372_dev_total_pending_patch import reconcile_result
from v153_project_scope_backend_authoritative_patch import install
from v375_center_card_metrics import center_card_metrics


def test_commercial_dev_never_increases_ingreso_operativo_and_is_idempotent():
    out={
        "stores":[
            {"store":"Puebla Sur","is_project":True,"recolectadas":100,"ingresos":100,
             "total_pzs":100,"dev_pzs":0,"acondicionado":125,"ubicado":100},
            {"store":"Vallejo","is_project":True,"recolectadas":50,"ingresos":50,
             "total_pzs":50,"dev_pzs":0,"acondicionado":35,"ubicado":70},
        ],
        "recovery_by_store":[{"store":"Puebla Sur","dev_pzs":0},
                             {"store":"Vallejo","dev_pzs":0}],
        "metrics":{},
    }
    fifo=[
        {"date":"2026-10-25","store":"Puebla Sur","dev_pzs":60,
         "converted_pieces":35,"return_value":1000,"recovered_value":500},
        {"date":"2026-10-25","store":"Vallejo","dev_pzs":25,
         "converted_pieces":15,"return_value":450,"recovered_value":300},
    ]
    for _ in range(3):
        out=reconcile_result(out,fifo,"day","2026-10-25")
        assert out["metrics"]["ingresos"] == 150
        assert out["metrics"]["total_pzs"] == 150
        assert out["metrics"]["dev_pzs"] == 85
        assert [r["total_pzs"] for r in out["stores"]] == [100,50]
    card=center_card_metrics(out)
    assert card["ingresos"] == 150
    assert card["acondicionado"] == 135  # min(125,100) + min(35,50)
    assert card["ubicado"] == 150         # min(100,100) + min(70,50)
    assert card["pct_acondicionado"] == 90.0
    assert card["pct_ubicado"] == 100.0
    assert sum(x["dev_pzs"] for x in out["recovery_by_store"]) == 85


def test_company_cards_exclude_unmarked_stores_but_recovery_keeps_all():
    projects=["Arco Norte","Ecatepec","Ixtapaluca","Miravalle","Puebla Sur","Vallejo"]
    project_rows=[{"store":s,"is_project":True,"recolectadas":10,
                   "ingresos":10,"total_pzs":10,"acondicionado":9,"ubicado":8}
                  for s in projects]
    other_row={"store":"Aguascalientes","is_project":False,
               "recolectadas":25000,"ingresos":25000,"total_pzs":25000,
               "acondicionado":25000,"ubicado":25000}
    recovery=[{"store":s,"dev_pzs":11} for s in projects+["Aguascalientes"]]
    calls=[]
    def operations(req,**kwargs):
        calls.append(kwargs["project_only"])
        return {
            "stores":project_rows+[other_row],  # defensa contra resultado previo mal filtrado
            "recovery_by_store":recovery,
            "metrics":{"ingresos":25060},
        }
    def require_user(req):return {"role":"admin"}
    m=SimpleNamespace(
        app=FastAPI(), operations=operations,
        project_store_names=lambda active=True:projects,
        require_user=require_user,
        effective_store=lambda actor,store:store,
    )
    install(m)
    endpoint=next(r.endpoint for r in m.app.router.routes
                  if getattr(r,"path",None)=="/api/operations/project-scope-v151")
    req=Request({"type":"http","method":"GET","path":"/api/operations/project-scope-v151","headers":[]})
    result=asyncio.run(endpoint(req,store="Compañía",
                                period_type="day",period_value="2026-10-25"))
    assert calls == [True,False]
    assert len(result["stores"]) == 6
    assert {r["store"] for r in result["stores"]} == set(projects)
    assert result["center_card_metrics"]["ingresos"] == 60
    assert result["center_card_metrics"]["acondicionado"] == 54
    assert len(result["recovery_by_store"]) == 7
    assert result["v153_project_store_count"] == 6
