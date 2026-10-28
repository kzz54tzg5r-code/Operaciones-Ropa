"""V383: validar el flujo completo de la DEV de 25/oct desde AA/AC/AE.

Fixtures sintéticos: no contienen datos comerciales reales del usuario.
"""
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

from daily_sales_headers import detect_monthly_layout
from v372_dev_total_pending_patch import reconcile_result


def make_october(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Octubre 26"
    ws["AA2"] = "Tienda"
    ws["AB2"] = "Ventas Netas Pzs"
    ws["AC2"] = "Dev Pzs"
    ws["AD2"] = "Venta Neta en $"
    for offset in range(27):
        day = date(2026, 10, 1) + timedelta(days=offset)
        col = 31 + 3 * offset  # Excel AE, AH, AK... (1-based)
        ws.cell(1, col, day)
        ws.cell(2, col, "Ventas Neta Pzs")
        ws.cell(2, col+1, "Dev Pzs")
        ws.cell(2, col+2, "Venta Neta en $")
    for row_num, store, pieces in (
        (3, "PUEBLA SUR", 4),
        (4, "VALLEJO", 3),
        (5, "ARCO NORTE", 2),
    ):
        ws.cell(row_num, 2, f"SKU-{row_num}")
        ws.cell(row_num, 8, "NEGRO")
        ws.cell(row_num, 25, 100)
        ws.cell(row_num, 26, 499) # costo en Z NO tienda
        ws.cell(row_num, 27, store)
        ws.cell(row_num, 29, pieces) # AC total DEV mensual
        # 25/oct => ventas en CC, devoluciones en CD, valor CE.
        start=31 + 24*3
        ws.cell(row_num, start, 1)
        ws.cell(row_num, start+1, pieces)
        ws.cell(row_num, start+2, 100)
    wb.save(path)


def test_dev_from_october_25_in_day_week_month(tmp_path):
    from web_app import _xlsx_stream_book, _stream_monthly_recovery_fifo
    from commercial.parsers import canon_store
    path = tmp_path / "Octubre_26_test.xlsx"
    make_october(path)
    with _xlsx_stream_book(path) as book:
        fifo, weeks, months, errors = _stream_monthly_recovery_fifo(
            path, ["Octubre 26"], book
        )
        meta = book["recovery_header_audit"]["Octubre 26"]
    assert errors == [], errors
    assert len(fifo) == 3
    assert {r["store"] for r in fifo} == {"Puebla Sur", "Vallejo", "Arco Norte"}
    assert all(r["date"] == "2026-10-25" for r in fifo)
    assert sum(r["dev_pzs"] for r in fifo) == 9
    assert meta["first_daily_col"] == 30
    assert meta["monthly_dev_col"] == 28
    assert "2026-W43" in weeks
    assert "2026-10" in months

    expected = ["Puebla Sur", "Vallejo", "Arco Norte"]
    for period_type, period_value in [
        ("day", "2026-10-25"),
        ("week", "2026-W43"),
        ("month", "2026-10"),
    ]:
        result = {
            "stores": [{"store": s, "dev_pzs": 0, "total_pzs": 15,
                        "acondicionado": 5, "ubicado": 3} for s in expected],
            "recovery_by_store": [{"store": s, "dev_pzs": 0} for s in expected],
            "metrics": {},
        }
        reconciled = reconcile_result(
            result, fifo, period_type, period_value, canon=canon_store
        )
        assert reconciled["metrics"]["dev_pzs"] == 9
        assert sum(s["dev_pzs"] for s in reconciled["recovery_by_store"]) == 9
        assert reconciled["recovery_source"]["period_dev_pzs"] == 9
        assert sorted(reconciled["recovery_by_store"], key=lambda r:r["store"])[0]["dev_pzs"] > 0
