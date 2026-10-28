"""V391: Ingresado = DEV + motivos de recoleccion + Pend. Ant. por Proyecto.

El comparativo de recuperación conserva todas las tiendas, pero Total pzs
se consolida sólo con las tiendas marcadas Proyecto, sin doble conteo.
"""
import asyncio
from types import SimpleNamespace
from fastapi import FastAPI
from starlette.requests import Request

from v372_dev_total_pending_patch import reconcile_result
from v153_project_scope_backend_authoritative_patch import install
from v375_center_card_metrics import center_card_metrics


def test_period_dev_is_added_once_to_project_operational_components():
    out={
        "stores":[
            {"store":"Puebla Sur","is_project":True,"recolectadas":100,"ingresos":100,
             "muertos":80,"probador":20,"cajas":0,"pendiente_anterior":20,
             "total_pzs":100,"dev_pzs":0,"acondicionado":125,"ubicado":100},
            {"store":"Vallejo","is_project":True,"recolectadas":50,"ingresos":50,
             "muertos":0,"probador":0,"cajas":50,"pendiente_anterior":10,
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
        assert out["metrics"]["ingresos"] == 265
        assert out["metrics"]["total_pzs"] == 265
        assert out["metrics"]["dev_pzs"] == 85
        assert [r["total_pzs"] for r in out["stores"]] == [180,85]
    card=center_card_metrics(out)
    assert card["ingresos"] == 265
    assert card["acondicionado"] == 160  # min(125,180) + min(35,85)
    assert card["ubicado"] == 170         # min(100,180) + min(70,85)
    assert card["pct_acondicionado"] == 160 / 265 * 100
    assert card["pct_ubicado"] == 170 / 265 * 100
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
