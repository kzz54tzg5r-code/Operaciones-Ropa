"""V391: Total pzs suma DEV, Muertos, Probador, Cajas y Pend. Ant.

Regresión de los datos marcados del 25 de octubre de 2026.
La tabla conserva cantidades reales y las tarjetas aplican tope por tienda.
"""
from v372_dev_total_pending_patch import reconcile_result
from v375_center_card_metrics import center_card_metrics


def _daily_detail():
    # DEV corresponde al periodo seleccionado, no a un acumulado histórico.
    sample = [
        ("Puebla Sur", 144, 145, 219, 0, 2413, 39, 404),
        ("Vallejo", 554, 0, 0, 363, 4813, 417, 712),
        ("Arco Norte", 385, 0, 0, 28, 1300, 600, 1150),
        ("Ecatepec", 558, 0, 0, 0, 3788, 0, 0),
        ("Ixtapaluca", 272, 0, 0, 0, 1778, 0, 0),
        ("Miravalle", 71, 0, 0, 0, 471, 0, 0),
    ]
    stores = [
        {
            "store": store, "dev_pzs": dev, "muertos": muertos,
            "probador": probador, "cajas": cajas,
            "pendiente_anterior": prev, "recolectadas": muertos + probador + cajas,
            "acondicionado": ac, "ubicado": ub,
            "ingresos": muertos + probador + cajas, "total_pzs": muertos + probador + cajas,
        }
        for store, dev, muertos, probador, cajas, prev, ac, ub in sample
    ]
    return {
        "stores": stores,
        "recovery_by_store": [
            {"store": s["store"], "dev_pzs": s["dev_pzs"]}
            for s in stores
        ],
        "metrics": {},
    }


def test_detail_recalculates_exact_five_fields_and_summary():
    report = _daily_detail()
    expected = {
        "Puebla Sur": 2921,
        "Vallejo": 5730,
        "Arco Norte": 1713,
        "Ecatepec": 4346,
        "Ixtapaluca": 2050,
        "Miravalle": 542,
    }
    for _ in range(3):
        report = reconcile_result(report, (), "day", "2026-10-25")
        by_store = {r["store"]: r for r in report["stores"]}
        assert {store: r["total_pzs"] for store, r in by_store.items()} == expected
        assert sum(r["total_pzs"] for r in report["stores"]) == 17302
        assert report["metrics"]["total_pzs"] == 17302
        assert report["metrics"]["ingresos"] == 17302
        assert report["metrics"]["pendiente_anterior"] == 14563
        assert report["metrics"]["dev_pzs"] == 1984
        assert by_store["Puebla Sur"]["pct_ubicado"] == 404 / 2921 * 100
        assert by_store["Arco Norte"]["pendiente_acondicionar"] == 1113
        assert by_store["Arco Norte"]["pendiente_ubicar"] == 563

    summary = center_card_metrics(report)
    assert summary["ingresos"] == 17302
    assert summary["acondicionado"] == 1056
    assert summary["ubicado"] == 2266
    assert summary["pct_acondicionado"] == 1056 / 17302 * 100
    assert summary["pct_ubicado"] == 2266 / 17302 * 100


def test_card_does_not_exceed_100_even_if_table_does():
    report = {
        "stores": [
            {"store": "A", "dev_pzs": 10, "muertos": 20, "probador": 0,
             "cajas": 0, "pendiente_anterior": 70, "acondicionado": 140,
             "ubicado": 130},
            {"store": "B", "dev_pzs": 0, "muertos": 0, "probador": 0,
             "cajas": 10, "pendiente_anterior": 90, "acondicionado": 0,
             "ubicado": 0},
        ],
        "recovery_by_store": [
            {"store": "A", "dev_pzs": 10}, {"store": "B", "dev_pzs": 0}
        ],
        "metrics": {},
    }
    reconcile_result(report, (), "day", "2026-10-25")
    rows = {r["store"]: r for r in report["stores"]}
    assert rows["A"]["pct_acondicionado"] == 140
    assert rows["A"]["pct_ubicado"] == 130
    cards = center_card_metrics(report)
    assert cards["ingresos"] == 200
    assert cards["acondicionado"] == 100
    assert cards["ubicado"] == 100
    assert cards["pct_acondicionado"] == 50
    assert cards["pct_ubicado"] == 50
