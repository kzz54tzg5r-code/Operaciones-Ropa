"""V331 regressions: the parallel audit never overwrites the original V243."""
from datetime import date

import pandas as pd
import pytest

from v331_recovery_audit_tab import (corrected_stock, cut_quality, revise_payload, insert_before_document_body_end)


@pytest.mark.parametrize(("cut", "status"), [
    (date(2026, 10, 5), "coincidente"),
    (date(2026, 10, 1), "estimado"),
    (date(2026, 9, 26), "corte_antiguo"),
    (date(2026, 10, 6), "corte_futuro"),
    (None, "sin_corte"),
])
def test_cut_must_never_be_future_or_stale(cut, status):
    assert cut_quality(date(2026, 10, 5), cut)[0] == status


def test_stock_aggregates_independent_location_rows_instead_of_maximum():
    data = pd.DataFrame([
        {"Tienda": "Centro", "ID_ART": "123", "Existencia": 12},
        {"Tienda": "Centro", "ID_ART": "123", "Existencia": 8},
        {"Tienda": "Centro", "ID_ART": "456", "Existencia": 3},
        {"Tienda": "Olivar", "ID_ART": "123", "Existencia": 5},
    ])
    assert corrected_stock(data, lambda s: s) == {"Centro": 23.0, "Olivar": 5.0}


def mock_payload(sales=10):
    return {
        "available": True,
        "status": "ready",
        "rows": [{
            "store": "Centro",
            "is_project": True,
            "inv_initial_pzs": 12,
            "dev_pzs": 4,
            "sales_pzs": sales,
            "sales_value": 1000,
        }],
        "trend": [{"date": "2026-10-05", "sales_pzs": sales, "dev_pzs": 4}],
    }


def test_fixed_stock_changes_rate_but_preserves_original_input():
    before = mock_payload()
    after = revise_payload(before, {"Centro": 20}, date(2026, 10, 5),
                           "Capacidades 05.10.26", date(2026, 10, 5))
    assert before["rows"][0]["inv_initial_pzs"] == 12
    assert after["rows"][0]["inv_initial_pzs"] == 20
    assert after["rows"][0]["inv_total_pzs"] == 24
    assert after["rows"][0]["inv_final_pzs"] == 14
    assert after["rows"][0]["sell_through_pct"] == pytest.approx(41.6666666667)
    assert after["metrics"]["sell_through_pct"] == pytest.approx(41.6666666667)
    assert after["metrics"]["inv_total_amount"] is None
    assert after["audit"]["returns_enabled_verified"] is False
    assert after["audit"]["stock_conciliated"] is False


def test_future_or_stale_cut_never_publishes_a_rate():
    for cut in (date(2026, 10, 6), date(2026, 9, 26), None):
        result = revise_payload(mock_payload(), {"Centro": 20}, cut,
                                "Capacidades", date(2026, 10, 5))
        assert result["rows"][0]["sell_through_pct"] is None
        assert result["metrics"]["sell_through_pct"] is None


def test_sales_greater_than_estimated_stock_are_flagged_not_above_100_percent():
    out = revise_payload(mock_payload(sales=40), {"Centro": 20},
                         date(2026, 10, 5), "Capacidades", date(2026, 10, 5))
    assert out["rows"][0]["data_quality"] == "ventas_superan_base"
    assert out["rows"][0]["sell_through_pct"] is None
    assert out["metrics"]["sell_through_pct"] is None
    assert out["rows"][0]["inv_final_pzs"] == -16


def test_company_rate_is_weighted_not_average_of_store_rates():
    source = mock_payload()
    source["rows"].append({
        "store": "Olivar", "dev_pzs": 0, "sales_pzs": 2, "sales_value": 300,
    })
    out = revise_payload(source, {"Centro": 20, "Olivar": 4},
                         date(2026, 10, 5), "Capacidades", date(2026, 10, 5))
    # 10 + 2 sales / (20 + 4 returns + 4 Olivar stock)
    assert out["metrics"]["sell_through_pct"] == pytest.approx(100 * 12 / 28)
    assert out["metrics"]["stores_in_scope"] == 2
    assert out["metrics"]["valid_stores"] == 2


def test_v314_quoted_closing_body_does_not_swallow_v331_script():
    # The V314 photo exporter has </body> embedded inside a JS string.
    v314 = """<script id="v314-bonus-photos-js">
    (function(){w.document.write('<html><body>Foto</body></html>');})();
    </script>"""
    original = "<!doctype html><html><head></head><body>" + v314 + "</body></html>"
    v331 = '<script id="v331-recovery-audit-js">window.recoveryRateImprovedView=function(){};</script>'
    result = insert_before_document_body_end(original, v331)
    assert v314 in result
    assert result.count('id="v331-recovery-audit-js"') == 1
    assert result.index('</script>', result.index('id="v314-bonus-photos-js"')) < result.index('id="v331-recovery-audit-js"')
    assert result.endswith(v331 + "</body></html>")
    assert "Foto</body></html>" in result


def test_appended_script_when_host_page_lacks_explicit_body_end():
    assert insert_before_document_body_end("<html>ok", "<script>1</script>") == "<html>ok<script>1</script>"
