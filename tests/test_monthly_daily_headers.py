"""La fila 1 identifica fechas y la fila 2 identifica la métrica de cada día."""
from datetime import date
from pathlib import Path
import openpyxl

from daily_sales_headers import resolve_daily_groups, _date_iso
import web_app


def _headers():
    first = {26: "Total", 27: "Total", 28: "Total"}
    second = {26: "Ventas Neta Pzs", 27: "Dev Pzs", 28: "Venta Neta en $"}
    for start, day in ((29, "01/10/2026"), (32, "02/10/2026"), (35, "03/10/2026"), (38, "04/10/2026")):
        for offset, label in enumerate(("Ventas Neta Pzs", "Dev Pzs", "Venta Neta en $")):
            first[start + offset] = day
            second[start + offset] = label
    return first, second


def test_october_dates_use_day_first_and_ignore_total_columns():
    first, second = _headers()
    groups, warnings = resolve_daily_groups(first, second)
    assert warnings == []
    assert [(column, day) for column, day, *_ in groups] == [
        (29, "2026-10-01"), (32, "2026-10-02"), (35, "2026-10-03"), (38, "2026-10-04")]
    assert all(month == "2026-10" for *_, month in groups)
    assert _date_iso("12/10/2026")[0] == "2026-10-12"
    assert _date_iso(date(2026, 10, 1))[0] == "2026-10-01"
    assert _date_iso(46326)[0] == "2026-10-01"


def test_misplaced_devolution_header_is_rejected():
    first, second = _headers()
    second[30], second[31] = second[31], second[30]
    groups, warnings = resolve_daily_groups(first, second)
    assert len(groups) == 3
    assert warnings and "orden inválido" in warnings[0]


def test_merged_date_cell_is_valid():
    first, second = _headers()
    first[30] = None
    first[31] = None
    groups, warnings = resolve_daily_groups(first, second)
    assert len(groups) == 4
    assert not warnings


def test_monthly_parser_uses_ad_ae_af_and_not_monthly_totals(tmp_path):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Octubre 26"
    first, second = _headers()
    for column, value in first.items():
        sheet.cell(1, column + 1, value)
    for column, value in second.items():
        sheet.cell(2, column + 1, value)
    sheet["B3"] = 100001
    sheet["H3"] = "AZUL"
    sheet["Y3"] = 150
    sheet["Z3"] = "Vallejo"
    sheet["AA3"] = 8  # Total venta mensual; NO sumar como día.
    sheet["AB3"] = 3  # Total DEV mensual; NO sumar como día.
    sheet["AC3"] = 1200
    sheet["AD3"] = 2
    sheet["AE3"] = 2
    sheet["AF3"] = 300
    sheet["AG3"] = 3
    sheet["AH3"] = 1
    sheet["AI3"] = 450
    sheet["AJ3"] = 1
    sheet["AK3"] = 0
    sheet["AL3"] = 150
    sheet["AM3"] = 2
    sheet["AN3"] = 0
    sheet["AO3"] = 300
    path = tmp_path / "base.xlsx"
    book.save(path)
    rows, weeks, months, errors = web_app._stream_monthly_recovery_fifo(path, ["Octubre 26"])
    assert not errors
    assert len(rows) == 2  # Un lote por fecha con DEV.
    assert {row["date"]: row["dev_pzs"] for row in rows} == {
        "2026-10-01": 2.0, "2026-10-02": 1.0}
    assert sum(row["dev_pzs"] for row in rows) == 3
    assert "2026-10" in months
    assert "2026-W40" in weeks
