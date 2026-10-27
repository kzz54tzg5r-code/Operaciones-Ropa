"""Evita que la falta de tiendas en Octubre produzca DEV y recuperación falsas en cero."""
import pytest
from types import SimpleNamespace

from v370_monthly_store_guard_patch import (
    _missing_store_with_movements, MonthlyStoreMissingError, install
)


def test_october_with_stores_is_valid():
    article = {1: "ART-123", 25: "Puebla Sur", 26: 16, 27: 5,
               29: 11, 30: 5, 31: 1500}
    assert not _missing_store_with_movements(article)


@pytest.mark.parametrize("values", [
    {1: "ART-123", 25: "", 27: 5, 30: 5},
    {1: "ART-123", 25: None, 29: 1},
    {1: "ART-123", 25: "nan", 28: 1000},
])
def test_october_with_movements_and_no_store_must_be_rejected(values):
    assert _missing_store_with_movements(values)


@pytest.mark.parametrize("row", [
    {1: "", 25: "", 27: 100},
    {1: "ART-123", 25: "", 27: 0, 30: 0},
    {1: "ART-123", 25: "Vallejo", 27: 5, 30: 5}
])
def test_does_not_mistake_headers_empty_rows_or_valid_shops(row):
    assert not _missing_store_with_movements(row)


def test_stream_rejects_partial_october_and_preserves_old_payload():
    rows = [
        {29: "2026-10-25"}, {29: "Vta Pzs", 30: "Dev Pzs"},
        {1: "ART-123", 25: "", 27: 7, 30: 7},
    ]
    mod = SimpleNamespace(
        _xlsx_monthly_rows=lambda *a: iter(rows),
        _stream_monthly_recovery_fifo=None
    )

    def parser(path, sheets, stream_book=None):
        errors = []
        try:
            list(mod._xlsx_monthly_rows(None, "octubre", None))
        except Exception as exc:
            errors.append(f"Octubre 2026: {exc}")
        return [], [], [], errors

    mod._stream_monthly_recovery_fifo = parser
    install(mod)
    with pytest.raises(ValueError, match="columna Z"):
        mod._stream_monthly_recovery_fifo(None, ["Octubre 2026"])

    rows[2][25] = "Puebla Sur"
    result = mod._stream_monthly_recovery_fifo(None, ["Octubre 2026"])
    assert result == ([], [], [], []) or result == [[], [], [], []]


def test_empty_month_without_dev_is_not_rejected():
    rows = [{29: "2026-10-25"}, {29: "Vta Pzs"}, {1: "ART", 25: "", 27: 0, 30: 0}]
    mod = SimpleNamespace(_xlsx_monthly_rows=lambda *a: iter(rows),
                          _stream_monthly_recovery_fifo=None)
    def parser(path, sheets, stream_book=None):
        list(mod._xlsx_monthly_rows(None,"octubre",None))
        return [], [], [], []
    mod._stream_monthly_recovery_fifo = parser
    install(mod)
    assert mod._stream_monthly_recovery_fifo(None, ["Octubre"]) == ([], [], [], []) or mod._stream_monthly_recovery_fifo(None, ["Octubre"]) == [[], [], [], []]
