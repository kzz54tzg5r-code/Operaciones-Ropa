"""V372: las DEV del FIFO se muestran en el periodo y tienda correctos."""
from v372_dev_total_pending_patch import reconcile_result


def record():
    return {
        "stores": [
            {"store": "Puebla Sur", "dev_pzs": 0, "muertos": 145, "probador": 219, "cajas": 0,
             "acondicionado": 39, "ubicado": 404},
            {"store": "Vallejo", "dev_pzs": 0, "muertos": 0, "probador": 0, "cajas": 363,
             "acondicionado": 417, "ubicado": 712}
        ],
        "recovery_by_store": [
            {"store": "Puebla Sur", "dev_pzs": 0, "converted_pieces": 0, "return_value": 0, "recovered_value": 0},
            {"store": "Vallejo", "dev_pzs": 0, "converted_pieces": 0, "return_value": 0, "recovered_value": 0}
        ],
        "metrics": {}
    }


def fifo():
    return [
        {"store": "PUEBLA SUR", "date": "2026-10-25", "dev_pzs": 3, "converted_pieces": 2,
         "return_value": 300, "recovered_value": 200},
        {"store": "VALLEJO", "date": "2026-10-25", "dev_pzs": 7, "converted_pieces": 5,
         "return_value": 700, "recovered_value": 500},
        {"store": "ARCO NORTE", "date": "2026-10-25", "dev_pzs": 80, "converted_pieces": 60,
         "return_value": 8000, "recovered_value": 6000},
        {"store": "VALLEJO", "date": "2026-10-26", "dev_pzs": 99, "converted_pieces": 0,
         "return_value": 0, "recovered_value": 0}
    ]


def test_restores_correct_date_and_only_authorized_stores():
    r = reconcile_result(record(), fifo(), "day", "2026-10-25")
    m = r["metrics"]
    assert m["dev_pzs"] == 10
    assert m["converted_pieces"] == 7
    assert m["pending_recovery_pieces"] == 3
    assert len(r["recovery_by_store"]) == 2
    assert [x["store"] for x in r["stores"]] == ["Vallejo", "Puebla Sur"]
    assert m["total_pzs"] == 737  # 363+7 + 145+219+3
    assert m["pendiente_acondicionar"] == 328 + 0  # Puebla 367-39; Vallejo 370-417
    assert m["pendiente_ubicar"] == 0  # Ambas ya tienen más ubicado que total.
    assert r["recovery_source"]["fifo_restored_from_published_data"]
    assert m["pct_ubicado"] == (1116 / 737 * 100)


def test_pendientes_use_total_not_acondicionado():
    r = reconcile_result(record(), (), "day", "2026-10-25")
    row = next(x for x in r["stores"] if x["store"] == "Puebla Sur")
    assert row["total_pzs"] == 364
    assert row["pendiente_acondicionar"] == 325
    assert row["pendiente_ubicar"] == 0  # 404 supera total; no negativos.
    assert row["pct_ubicado"] > 100


def test_month_and_week_iso_preserve_original_lots():
    month = reconcile_result(record(), fifo(), "month", "2026-10")
    assert month["metrics"]["dev_pzs"] == 109  # 3+7+99; exclude Arco Norte.
    week = reconcile_result(record(), fifo(), "week", "2026-W43")
    assert week["metrics"]["dev_pzs"] == 10
