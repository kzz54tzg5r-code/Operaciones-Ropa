"""V372: las DEV del FIFO se muestran en el periodo y tienda correctos."""
from v372_dev_total_pending_patch import reconcile_result


def record():
    return {
        "stores": [
            {"store": "Puebla Sur", "dev_pzs": 0, "muertos": 145, "probador": 219, "cajas": 0,
             "acondicionado": 39, "ubicado": 404, "total_pzs": 1899, "pendiente_anterior": 1535},
            {"store": "Vallejo", "dev_pzs": 0, "muertos": 0, "probador": 0, "cajas": 363,
             "acondicionado": 417, "ubicado": 712, "total_pzs": 409, "pendiente_anterior": 46}
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
    assert [x["store"] for x in r["stores"]] == ["Puebla Sur", "Vallejo"]
    assert m["total_pzs"] == 2308  # ingreso operativo sin sumar DEV comercial
    assert m["pendiente_acondicionar"] == 1860
    assert m["pendiente_ubicar"] == 1495
    assert r["recovery_source"]["fifo_restored_from_published_data"]
    assert m["pct_ubicado"] == (1116 / 2308 * 100)


def test_pendientes_use_total_not_acondicionado():
    r = reconcile_result(record(), (), "day", "2026-10-25")
    row = next(x for x in r["stores"] if x["store"] == "Puebla Sur")
    assert row["total_pzs"] == 1899
    assert row["pendiente_acondicionar"] == 1860
    assert row["pendiente_ubicar"] == 1495
    assert round(row["pct_ubicado"], 1) == 21.3


def test_month_and_week_iso_preserve_original_lots():
    month = reconcile_result(record(), fifo(), "month", "2026-10")
    assert month["metrics"]["dev_pzs"] == 109  # 3+7+99; exclude Arco Norte.
    week = reconcile_result(record(), fifo(), "week", "2026-W43")
    assert week["metrics"]["dev_pzs"] == 10


def test_legacy_variadic_wrapper_does_not_turn_day_into_all_history():
    """Reproduce la firma V367 (*args, **kwargs) que provocó 73 mil DEV diarias."""
    from types import SimpleNamespace
    from v372_dev_total_pending_patch import install

    # La función de V367 no preserva inspect.signature del endpoint original.
    def variadic_operations(*args, **kwargs):
        return record()
    module = SimpleNamespace(
        operations=variadic_operations,
        load_ops=lambda: {"recovery_fifo": fifo()},
        _get_recovery_fifo_rows=lambda data: data["recovery_fifo"],
        _normalize_store_value=lambda store: store,
    )
    install(module)
    day = module.operations(object(), store="Compañía", period_type="day", period_value="2026-10-25")
    assert day["metrics"]["dev_pzs"] == 10
    assert day["recovery_source"]["fifo_restored_from_published_data"]
    assert day["metrics"]["dev_pzs"] != 109

    # Cambio de fecha obliga a filtrar de nuevo, no a conservar el acumulado.
    next_day = module.operations(object(), store="Compañía", period_type="day", period_value="2026-10-26")
    assert next_day["metrics"]["dev_pzs"] == 99
    week = module.operations(object(), period_type="week", period_value="2026-W43")
    assert week["metrics"]["dev_pzs"] == 10
    month = module.operations(object(), period_type="month", period_value="2026-10")
    assert month["metrics"]["dev_pzs"] == 109


def test_missing_day_is_never_converted_into_historical_totals():
    from types import SimpleNamespace
    from v372_dev_total_pending_patch import install

    def variadic_operations(*args, **kwargs):
        return record()
    module = SimpleNamespace(
        operations=variadic_operations,
        load_ops=lambda: {"recovery_fifo": fifo()},
        _get_recovery_fifo_rows=lambda data: data["recovery_fifo"],
    )
    install(module)
    result = module.operations(object(), period_type="day", period_value="")
    assert result["metrics"]["dev_pzs"] == 0
    assert not result["recovery_source"]["fifo_restored_from_published_data"]


def test_day_range_never_includes_outside_dates():
    result = reconcile_result(
        record(), fifo(), "all", "", "2026-10-25", "2026-10-25"
    )
    assert result["metrics"]["dev_pzs"] == 10
