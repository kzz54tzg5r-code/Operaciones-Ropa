"""The repair must never interpret a future/other period as new DEV."""
from v368_rebuild_dev_patch import _period_dev, _period_matches


def test_period_boundaries_day_week_month_year():
    row = {"date": "2026-10-25", "dev_pzs": 5}
    assert _period_matches(row, "day", "2026-10-25")
    assert not _period_matches(row, "day", "2026-10-24")
    assert _period_matches(row, "week", "2026-W43")
    assert not _period_matches(row, "week", "2026-W44")
    assert _period_matches(row, "month", "2026-10")
    assert not _period_matches(row, "month", "2026-09")
    assert _period_matches(row, "year", "2026")


def test_only_selected_period_and_valid_positive_dev():
    rows = [
        {"date": "2026-10-24", "dev_pzs": 5},
        {"date": "2026-10-25", "dev_pzs": 12},
        {"date": "2026-10-26", "dev_pzs": 30},
        {"date": "2026-10-25", "dev_pzs": "nan"},
        {"date": "2026-10-25", "dev_pzs": -7},
    ]
    assert _period_dev(rows, "day", "2026-10-25") == 12
    assert _period_dev(rows, "week", "2026-W43") == 17
    assert _period_dev(rows, "month", "2026-10") == 47
    assert _period_dev(rows, "month", "2026-09") == 0
