"""Regresión: capar cada tienda antes de sumar tarjetas, nunca datos originales."""
import copy
from pathlib import Path

from v375_center_card_metrics import center_card_metrics


def sample():
    return {
        "metrics": {
            "ingresos": 2336, "total_pzs": 2336,
            "acondicionado": 1056, "ubicado": 2266,
            "pct_acondicionado": 45.2, "pct_ubicado": 97.0,
            "recorridos": 11, "meta_recorridos": 48,
            "dev_pzs": 17,
        },
        "stores": [
            {"store": "Puebla Sur", "total_pzs": 1899, "acondicionado": 39, "ubicado": 404},
            {"store": "Vallejo", "total_pzs": 409, "acondicionado": 417, "ubicado": 712},
            {"store": "Arco Norte", "total_pzs": 28, "acondicionado": 600, "ubicado": 1150},
        ],
        "recovery_by_store": [{"store": "Puebla Sur", "dev_pzs": 17}],
    }


def test_cap_applied_before_aggregation_retains_real_rows():
    source = sample()
    untouched = copy.deepcopy(source)
    display = center_card_metrics(source)
    assert display["total_pzs"] == 2336
    assert display["acondicionado"] == 476  # 39 + min(417,409) + min(600,28)
    assert display["ubicado"] == 841  # 404 + min(712,409) + min(1150,28)
    assert display["pct_acondicionado"] == 476 / 2336 * 100
    assert display["pct_ubicado"] == 841 / 2336 * 100
    assert display["pendiente_acondicionar"] == 1860
    assert display["pendiente_ubicar"] == 1495
    assert display["recorridos"] == 11
    assert display["dev_pzs"] == 17
    assert source == untouched
    assert source["stores"][1]["acondicionado"] == 417
    assert source["stores"][2]["ubicado"] == 1150


def test_unbalanced_stores_cannot_offset_each_others_shortfall():
    report = {
        "metrics": {},
        "stores": [
            {"total_pzs": 100, "acondicionado": 200, "ubicado": 200},
            {"total_pzs": 100, "acondicionado": 0, "ubicado": 0},
        ],
    }
    mt = center_card_metrics(report)
    assert mt["total_pzs"] == 200
    assert mt["acondicionado"] == 100
    assert mt["ubicado"] == 100
    assert mt["pct_acondicionado"] == 50
    assert mt["pct_ubicado"] == 50
    assert mt["pendiente_acondicionar"] == 100
    assert mt["pendiente_ubicar"] == 100


def test_zeros_and_excess_on_zero_incoming_cannot_inflate_cards():
    mt = center_card_metrics({"metrics":{"recorridos":4}, "stores": [
        {"total_pzs":0, "acondicionado":890, "ubicado":30},
        {"total_pzs":0, "acondicionado":0, "ubicado":0},
    ]})
    assert mt["ingresos"] == 0
    assert mt["acondicionado"] == 0
    assert mt["ubicado"] == 0
    assert mt["pct_acondicionado"] == 0
    assert mt["pct_ubicado"] == 0
    assert mt["recorridos"] == 4


def test_front_end_uses_same_period_and_response_for_table_and_cards():
    root = Path(__file__).resolve().parents[1]
    script = (root / "v240_center_routes_calendar_patch.py").read_text(encoding="utf-8")
    assert "data?.center_card_metrics||data?.metrics" in script
    assert "OR375_CENTER_RECOVERY" in script
    assert "recoveryTable(rec)" in script
    reusable = (root / "web" / "recuperacion_visible_v373.js").read_text(encoding="utf-8")
    assert "const current=window.OR375_CENTER_RECOVERY;" in reusable
    assert "current.period_type===filter.period_type" in reusable
    assert "current.period_value===filter.period_value" in reusable
    assert "current.store===filter.store" in reusable
    server = (root / "v153_project_scope_backend_authoritative_patch.py").read_text(encoding="utf-8")
    assert server.count('out["center_card_metrics"] = center_card_metrics(out)') == 2
