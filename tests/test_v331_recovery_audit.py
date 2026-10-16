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


def test_fast_daily_sqlite_path_preserves_security_and_weighted_company_rate(tmp_path):
    import json
    import sqlite3
    from types import SimpleNamespace
    from fastapi import FastAPI
    from v331_recovery_audit_tab import install

    source = tmp_path / "cambios_muertos_actual.xlsx"
    source.write_bytes(b"v243 normalized sample")
    stamp = source.stat()
    db = sqlite3.connect(tmp_path / "recovery_rate_daily_v243.sqlite3")
    db.executescript("""
    CREATE TABLE meta (k TEXT PRIMARY KEY,v TEXT);
    CREATE TABLE daily (store TEXT,date TEXT,year_iso INTEGER,week_iso INTEGER,
                        sales REAL,dev REAL,sales_value REAL,return_value REAL);
    """)
    db.executemany("INSERT INTO meta VALUES (?,?)", [
        ("version", "243.1"), ("source_stamp", f"{stamp.st_mtime_ns}:{stamp.st_size}")])
    db.executemany("INSERT INTO daily VALUES (?,?,?,?,?,?,?,?)", [
        ("Centro", "2026-10-12", 2026, 42, 10, 4, 1000, 0),
        ("Olivar", "2026-10-12", 2026, 42, 2, 0, 200, 0),
    ])
    db.commit()
    db.close()

    item = {"id": "cut-oct", "sha256": "test-hash",
            "name": "Capacidades_12.10.26.xlsx"}
    (tmp_path / "recovery_audit_stock_v331.json").write_text(
        json.dumps({"key": "cut-oct|test-hash|2026-10-12|schema2",
                    "stocks": {"Centro": 20, "Olivar": 4}}), encoding="utf-8")
    app = FastAPI()
    calls = {"baseline": 0, "user": 0}

    @app.get("/api/operations/recovery-rate")
    def existing_baseline():
        calls["baseline"] += 1
        raise AssertionError("The audited view must not execute the slow baseline")

    def require_user(request):
        calls["user"] += 1
        return {"role": "admin"}

    m = SimpleNamespace(
        app=app, DATA_ROOT=tmp_path, REPORT_TABS={},
        require_user=require_user,
        effective_store=lambda user, store: store,
        store_names=lambda active: ["Centro", "Olivar"],
        project_store_names=lambda active: ["Centro"],
        load_operations_meta=lambda: {
            "available_dates": ["2026-10-12"],
            "available_weeks": ["2026-W42"],
            "available_months": ["2026-10"],
        },
        _capacity_processed_entries=lambda: [item],
        _capacity_report_date=lambda entry: date(2026, 10, 12),
        _normalize_store_value=lambda text: text,
        _load_capacity_compact_cache=lambda entry: (_ for _ in ()).throw(
            AssertionError("Stock must come from summarized cache")),
    )
    install(m)
    endpoint = next(x.endpoint for x in app.routes
                    if x.path == "/api/operations/recovery-rate-audit-v331")
    result = endpoint(request=object(), store="Compañía",
                      period_type="week", period_value="2026-W42")
    assert result["status"] == "ready"
    assert result["metrics"]["sell_through_pct"] == pytest.approx(100 * 12 / 28)
    assert result["metrics"]["sales_pzs"] == 12
    assert result["audit"]["period_partial"] is True
    assert result["audit"]["stock_phase"] == "ready"
    assert calls == {"baseline": 0, "user": 1}

    other = endpoint(request=object(), store="Centro", period_type="week",
                     period_value="2026-W42")
    assert other["metrics"]["sell_through_pct"] == pytest.approx(100 * 10 / 24)
    assert len(other["rows"]) == 1
    assert other["rows"][0]["store"] == "Centro"
    assert calls["baseline"] == 0


def test_original_recovery_uses_nearby_new_snapshot_as_reference_not_april_stock():
    from v243_recovery_rate_patch import select_capacity_cut, stock_cut_is_valid
    previous = (date(2026, 4, 24), "2026-08-16", {"name": "capacidades_24.04.26.xls"})
    upcoming = (date(2026, 10, 13), "2026-10-13", {"name": "Capacidades_13.10.26.xlsx"})
    selected, flag = select_capacity_cut([previous, upcoming], date(2026, 10, 12))
    assert flag == "reference_future"
    assert selected[0] == date(2026, 10, 13)
    assert stock_cut_is_valid(selected[0], date(2026, 10, 12), True) is False


def test_original_recovery_accepts_prior_cut_and_rejects_old_stale_cuts():
    from v243_recovery_rate_patch import select_capacity_cut, stock_cut_is_valid
    near = (date(2026, 10, 11), "", {"name": "Prev day"})
    after = (date(2026, 10, 13), "", {"name": "Next day"})
    selected, flag = select_capacity_cut([near, after], date(2026, 10, 12))
    assert flag == "valid"
    assert selected[0] == date(2026, 10, 11)
    assert stock_cut_is_valid(selected[0], date(2026, 10, 12), False)
    selected, flag = select_capacity_cut([(date(2026, 4, 24), "", {})],
                                         date(2026, 10, 12))
    assert flag == "stale"
    assert not stock_cut_is_valid(selected[0], date(2026, 10, 12), False)


def test_original_recovery_formats_pesos_in_thousands_without_changing_pieces():
    from v243_recovery_rate_patch import money_in_thousands
    assert money_in_thousands(9812466.88) == pytest.approx(9812.5)
    assert money_in_thousands(304.39, 3) == pytest.approx(0.304)
    assert money_in_thousands(-12000.0) == pytest.approx(-12.0)
