"""V384: distinguir cobertura mensual ausente de DEV=0 sin inventar datos."""
from types import SimpleNamespace

from v367_recovery_source_patch import install


def make_app(last_day):
    base = {
        "period_type": "day",
        "period_value": "2026-10-25",
        "monthly_sheets": ["Octubre 26"],
        "recovery_by_store": [{"store": "Puebla Sur", "dev_pzs": 0}],
        "parse_errors": [],
    }
    source = {
        "monthly_sheets": ["Octubre 26"],
        "recovery_header_audit": {
            "Octubre 26": {"last_date": last_day}
        },
        "recovery_fifo": [{
            "date": "2026-10-10", "year_iso": 2026, "week_iso": 41,
            "store": "Puebla Sur", "dev_pzs": 2,
        }],
    }
    m = SimpleNamespace(
        _monthly_sheet_name=lambda name: bool(name),
        normalize_col=lambda value: str(value).casefold(),
        _xlsx_monthly_rows=lambda archive, member, shared_value: iter(()),
        _get_recovery_fifo_rows=lambda data: data["recovery_fifo"],
        _build_recovery_fifo_rows=lambda rows: rows,
        operations=lambda **kwargs: dict(base),
        load_ops=lambda: source,
    )
    install(m)
    return m


def test_missing_25_october_is_flagged_not_claimed_as_zero_sales():
    m = make_app("2026-10-12")
    response = m.operations()
    assert response["recovery_source"]["coverage_missing_for_day"] is True
    assert response["recovery_source"]["latest_monthly_day"] == "2026-10-12"
    assert "no contiene aún las DEV" in response["recovery_source"]["source_warning"]
    assert response["recovery_by_store"][0]["dev_pzs"] == 0  # no invented records


def test_when_25_october_is_in_the_source_no_gap_warning():
    m = make_app("2026-10-25")
    response = m.operations()
    assert response["recovery_source"]["coverage_missing_for_day"] is False
    assert "no contiene aún" not in response["recovery_source"]["source_warning"]
