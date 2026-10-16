from datetime import date
from pathlib import Path

from v243_recovery_rate_patch import partial_rate_after_future_cut


def normal(s):
    return str(s).strip()


def test_valid_partial_after_cut_does_not_include_cut_day_or_earlier():
    # Monday 12 Oct, cut at Tuesday 13 Oct; only Wednesday onwards are comparable.
    data = [
        {"store": "Olivar", "date": "2026-10-12", "sales": 400, "dev": 10},
        {"store": "Olivar", "date": "2026-10-13", "sales": 100, "dev": 20},
        {"store": "Olivar", "date": "2026-10-14", "sales": 25, "dev": 5},
        {"store": "Olivar", "date": "2026-10-15", "sales": 25, "dev": 5},
    ]
    result = partial_rate_after_future_cut(
        data, {"Olivar": 90}, date(2026, 10, 13),
        date(2026, 10, 12), date(2026, 10, 18), ["Olivar"], normal
    )
    assert result["start"] == "2026-10-14"
    assert result["end"] == "2026-10-15"
    assert result["rows"]["Olivar"]["base"] == 100
    assert result["rows"]["Olivar"]["sales"] == 50
    assert result["rows"]["Olivar"]["sell_through_pct"] == 50.0
    assert result["rows"]["Olivar"]["impact_dev_pct"] == 10.0
    assert result["global"]["sell_through_pct"] == 50.0


def test_no_future_cut_full_week_rates_and_no_guessing_missing_stores():
    data = [{"store": "Olivar", "date": "2026-10-14", "sales": 8, "dev": 0}]
    assert partial_rate_after_future_cut(
        data, {"Olivar": 100}, date(2026, 10, 12),
        date(2026, 10, 12), date(2026, 10, 18), ["Olivar"], normal
    ) is None
    partial = partial_rate_after_future_cut(
        data, {"Olivar": 100, "Vallejo": 80}, date(2026, 10, 13),
        date(2026, 10, 12), date(2026, 10, 18), ["Olivar", "Vallejo"], normal
    )
    assert partial["rows"]["Olivar"]["sell_through_pct"] == 8.0
    assert partial["rows"]["Vallejo"] is None
    assert partial["global"] is None


def test_no_sales_since_cut_remains_unavailable_not_zero():
    rows = [{"store": "Olivar", "date": "2026-10-13", "sales": 9, "dev": 0}]
    partial = partial_rate_after_future_cut(
        rows, {"Olivar": 100}, date(2026, 10, 13),
        date(2026, 10, 12), date(2026, 10, 18), ["Olivar"], normal
    )
    assert partial["end"] is None
    assert partial["global"] is None


def test_unsustainable_sales_greater_than_stock_stays_blank():
    partial = partial_rate_after_future_cut(
        [{"store": "Olivar", "date": "2026-10-14", "sales": 150, "dev": 0}],
        {"Olivar": 100}, date(2026, 10, 13),
        date(2026, 10, 12), date(2026, 10, 18), ["Olivar"], normal
    )
    assert partial["rows"]["Olivar"]["sell_through_pct"] is None
    assert partial["global"] is None


def test_official_rate_is_not_replaced_with_partial_result():
    src = Path("v243_recovery_rate_patch.py").read_text("utf-8")
    assert 'sell_through = sales / enabled * 100 if enabled and stock_available and cut_valid' in src
    assert '"partial_reference": partial' in src
    assert "stockReference?r.partial_sell_through_pct:r.sell_through_pct" in src


def test_global_multiline_style_keeps_units_only_in_headers():
    src = Path("v332_compact_table_headers_patch.py").read_text("utf-8")
    assert "table thead tr th" in src
    assert "white-space:normal!important" in src
    assert "min-width:970px!important" in src
    assert "table tbody td" in src
    assert "pattern=/(" in src
    assert 'id="v332-universal-multiline-headers"' in src
    assert 'body.table' not in src  # Do not require a particular table class.
