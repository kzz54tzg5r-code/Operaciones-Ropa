"""Regresión del lector de ventas mensuales: fechas y encabezados seguros."""
from datetime import date, datetime, timedelta
from itertools import chain

import pytest

from daily_sales_headers import (
    _date_iso, _metric, locate_daily_headers, resolve_daily_groups,
)


@pytest.mark.parametrize("value, expected", [
    ("01/04/26", "2026-04-01"),
    ("01-04-2026", "2026-04-01"),
    ("2026-04-01", "2026-04-01"),
    ("2026/04/01 00:00:00", "2026-04-01"),
    ("01.04.26", "2026-04-01"),
    ("01-abr-26", "2026-04-01"),
    ("1 de abril de 2026", "2026-04-01"),
    ("10/may/26", "2026-05-10"),
    ("07-jun-26", "2026-06-07"),
    ("12-jul-26", "2026-07-12"),
    ("03-ago-26", "2026-08-03"),
    ("02-sept-26", "2026-09-02"),
    ("25-oct-26", "2026-10-25"),
    (date(2026, 10, 25), "2026-10-25"),
    (datetime(2026, 10, 25, 0, 0), "2026-10-25"),
])
def test_recognizes_safe_calendar_dates(value, expected):
    assert _date_iso(value)[0] == expected


@pytest.mark.parametrize("raw, kind", [
    ("Ventas Neta Pzs", "sales"),
    ("Ventas Netas Pzas", "sales"),
    ("Vta Neta Pzs", "sales"),
    ("DEV PZS", "dev"),
    ("Devoluciones Piezas", "dev"),
    ("Devolución Pzs", "dev"),
    ("Venta Neta en $", "value"),
    ("Ventas Neta $", "value"),
    ("Vta Importe MXN", "value"),
])
def test_recognizes_only_concrete_labels(raw, kind):
    assert _metric(raw) == kind


def month_rows(date_string, prefix=0):
    title = {0: "Reporte mensual"}  # Encabezado previo opcional.
    next_day = date.fromisoformat(_date_iso(date_string)[0]) + timedelta(days=1)
    date_header = {29: date_string, 32: next_day.isoformat()}
    metric_header = {
        29: "Ventas Neta Pzs", 30: "Dev Pzs", 31: "Venta Neta en $",
        32: "Ventas Neta Pzs", 33: "Dev Pzs", 34: "Venta Neta en $",
    }
    data = {1:"SKU", 25:"Puebla Sur", 29:10, 30:3, 31:100, 32:1, 33:4, 34:50}
    result = [date_header, metric_header, data]
    return [title] + result if prefix else result


@pytest.mark.parametrize("day", [
    "01/04/26", "02/05/26", "03/06/26", "04/07/26",
    "05/08/26", "06/09/26", "07/10/26",
])
@pytest.mark.parametrize("prefix", [0, 1])
def test_every_month_detected_and_product_row_survives(day, prefix):
    rows = month_rows(day, prefix)
    groups, warnings, last_header = locate_daily_headers(rows)
    assert len(groups) == 2, (day, warnings)
    assert warnings == []
    assert last_header == 1 + prefix
    iterator = iter(rows)
    probe = [dict(next(iterator, {}) or {}) for _ in range(6)]
    columns, errors, ending = locate_daily_headers(probe)
    assert len(columns) == 2
    assert errors == []
    replay = list(chain(probe[ending+1:], iterator))
    assert replay[0][25] == "Puebla Sur"
    assert replay[0][30] == 3


def test_unsafe_header_reordering_stays_blocked():
    dates = {29:"01/10/26"}
    values = {29:"Dev Pzs", 30:"Ventas Neta Pzs", 31:"Venta Neta en $"}
    groups, warnings = resolve_daily_groups(dates, values)
    assert groups == []
    assert any("orden inválido" in issue for issue in warnings)


def test_missing_date_for_metric_group_stays_blocked():
    dates = {29:"01/10/26"}
    values = {
        29:"Ventas Neta Pzs", 30:"Dev Pzs", 31:"Venta Neta en $",
        32:"Ventas Neta Pzs", 33:"Dev Pzs", 34:"Venta Neta en $",
    }
    groups, warnings = resolve_daily_groups(dates, values)
    assert len(groups) == 1
    assert any("sin fecha válida" in issue for issue in warnings)


def test_invalid_day_never_inferred_from_sheet_name():
    assert _date_iso("35/10/26") is None
    assert _date_iso("Octubre 26") is None
