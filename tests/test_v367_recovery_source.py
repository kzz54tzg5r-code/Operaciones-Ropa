"""Regresiones de la fuente DEV/FIFO usada en Centro Operativo."""
from types import SimpleNamespace

from v367_recovery_source_patch import install


def _fake_module(rows=None, daily=None, monthly_sheets=None, errors=None):
    observed = {"fifo_builds": 0}
    data = {"recovery_fifo": rows if rows is not None else [],
            "commercial_daily": daily if daily is not None else []}
    pages = [
        {29: "", 32: ""},
        {29: "2026-10-25", 32: "2026-10-26"},
        {1: "SKU12", 25: "Vallejo", 29: 12, 30: 4},
    ]

    def source_fifo(value):
        return value["recovery_fifo"]

    def build_fifo(value):
        observed["fifo_builds"] += 1
        return [{"date":"2026-10-25", "store":"Vallejo", "dev_pzs":4}]

    def date(value):
        return (str(value), 43, 2026, "2026-10") if isinstance(value,str) and value.startswith("2026-") else ("",None,None,"")

    def ops(*args, **kwargs):
        return {"monthly_sheets":monthly_sheets if monthly_sheets is not None else ["Octubre 2026"],
                "parse_errors":errors or [],
                "recovery_by_store":[{"store":"Vallejo","dev_pzs":4}]}

    module = SimpleNamespace(
        _monthly_sheet_name=lambda name:"octubre 2026" in str(name).lower(),
        _xlsx_monthly_rows=lambda *a: iter(pages),
        _safe_date_iso=date,
        normalize_col=lambda value:str(value).lower(),
        _get_recovery_fifo_rows=source_fifo,
        _build_recovery_fifo_rows=build_fifo,
        operations=ops,
        load_ops=lambda:data,
    )
    install(module)
    return module, data, observed


def test_recognizes_other_month_year_and_second_header_dates():
    m, data, _ = _fake_module()
    assert m._monthly_sheet_name("Septiembre 2025")
    assert m._monthly_sheet_name("Octubre 2026")
    assert m._monthly_sheet_name("Enero")
    assert not m._monthly_sheet_name("Resumen productividad")
    first, second, third = list(m._xlsx_monthly_rows(None,None,None))
    assert first[29] == "2026-10-25"
    assert first[32] == "2026-10-26"
    assert second[29] == "2026-10-25"
    assert third[30] == 4


def test_legacy_daily_dev_uses_fifo_without_multiplying():
    m, data, state = _fake_module(daily=[{"date":"2026-10-25","store":"Vallejo","dev_pzs":4}])
    a = m._get_recovery_fifo_rows(data)
    b = m._get_recovery_fifo_rows(data)
    assert a == b
    assert a[0]["dev_pzs"] == 4
    assert state["fifo_builds"] == 1
    result=m.operations()
    assert result["recovery_source"]["source_ready"] is True
    assert result["recovery_source"]["source_warning"] == ""


def test_missing_recovery_data_warns_instead_of_asserting_valid_zero():
    m, _, _ = _fake_module(monthly_sheets=[])
    result=m.operations()
    assert result["recovery_source"]["source_ready"] is False
    assert "no incluye hojas mensuales" in result["recovery_source"]["source_warning"]


def test_parser_errors_cause_explicit_warning():
    m, _, _ = _fake_module(errors=["Octubre 2026: no se detectaron fechas diarias"])
    result=m.operations()
    assert "lectura de fechas diarias" in result["recovery_source"]["source_warning"]
