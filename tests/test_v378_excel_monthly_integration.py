"""Prueba integral del XLSX con siete hojas y filas de cabecera no contiguas.

Usa un libro de prueba fabricado: nunca modifica bases reales ni publica datos.
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from daily_sales_headers import _header_date, locate_daily_headers


def test_weekday_prefix_in_monthly_header():
    assert _header_date("DOMINGO, 25 de Octubre de 2026")[0] == "2026-10-25"
    assert _header_date("Viernes 02/10/26")[0] == "2026-10-02"
    assert _header_date("JUEVES 1 DE ABRIL DE 2026")[0] == "2026-04-01"
    assert _header_date("35 de Octubre de 2026") is None


def test_18_header_rows_with_separator_are_not_lost():
    headers = [{} for _ in range(18)]
    headers[8] = {29: "DOMINGO, 25 de Octubre de 2026"}
    headers[10] = {
        29: "Ventas Neta Pzs",
        30: "Dev Pzs",
        31: "Venta Neta en $",
    }
    headers[11] = {1: "1234", 25: "Vallejo", 29: 2, 30: 7, 31: 120}
    groups, errors, idx = locate_daily_headers(headers)
    assert len(groups) == 1, errors
    assert errors == []
    assert idx == 10
    assert groups[0][1] == "2026-10-25"
    assert headers[idx + 1][30] == 7


def test_real_xml_streaming_across_april_october(tmp_path):
    """Valida XLSX físico y SQLite, no solamente diccionarios de prueba."""
    from web_app import _xlsx_stream_book, _stream_monthly_recovery_fifo
    month_names = ["Abril 26", "Mayo 26", "Junio 26", "Julio 26",
                   "Agosto 26", "Septiembre 26", "Octubre 26"]
    wb = Workbook()
    wb.remove(wb.active)
    for month, name in enumerate(month_names, 4):
        ws = wb.create_sheet(name)
        ws["A1"] = "Reporte de ventas y devoluciones"
        ws["AD9"] = date(2026, month, 1)
        ws["AD11"] = "Venta Neta Pzs"
        ws["AE11"] = "Dev Pzs"
        ws["AF11"] = "Venta Neta en $"
        ws["B12"] = f"SKU-{month}"
        ws["H12"] = "AZUL"
        ws["Y12"] = 100
        ws["Z12"] = "Vallejo"
        ws["AB12"] = 5
        ws["AD12"] = 2
        ws["AE12"] = 5
        ws["AF12"] = 200
    path = Path(tmp_path) / "Base de datos muertos y cambios.xlsx"
    wb.save(path)
    with _xlsx_stream_book(path) as book:
        fifo, weeks, months, errors = _stream_monthly_recovery_fifo(
            path, month_names, book
        )
    assert errors == []
    assert months == [f"2026-{month:02d}" for month in range(4, 11)]
    assert len(fifo) == 7
    assert sum(item.get("dev_pzs") or 0 for item in fifo) == 35
    assert all(item["store"] == "Vallejo" for item in fifo)



def test_unrecognized_metric_labels_are_only_accepted_with_ab_ae_match(tmp_path):
    from web_app import _xlsx_stream_book, _stream_monthly_recovery_fifo

    def make_xlsx(filename, monthly_dev, daily_dev):
        wb = Workbook()
        ws = wb.active
        ws.title = "Octubre 26"
        ws["AD6"] = "DOMINGO, 25 de Octubre de 2026"
        # Encabezados de ventas de un formato alternativo, sin los nombres
        # exactos esperados por el validador rígido anterior.
        ws["AD8"] = "Piezas movidas"
        ws["AE8"] = "Devoluciones"
        ws["AF8"] = "Importe Neto"
        ws["B9"] = "SKU-FECHA-TEST"
        ws["H9"] = "AZUL"
        ws["Y9"] = 110
        ws["Z9"] = "Puebla Sur"
        ws["AB9"] = monthly_dev
        ws["AD9"] = 2
        ws["AE9"] = daily_dev
        ws["AF9"] = 220
        output = tmp_path / filename
        wb.save(output)
        return output

    correct = make_xlsx("correct.xlsx", 7, 7)
    with _xlsx_stream_book(correct) as book:
        rows, weeks, months, errors = _stream_monthly_recovery_fifo(
            correct, ["Octubre 26"], book
        )
        audit = book["recovery_header_audit"]["Octubre 26"]
    assert errors == []
    assert audit["recognition_mode"] == "dates_and_AB_AE_reconciliation"
    assert sum(x["dev_pzs"] for x in rows) == 7
    assert months == ["2026-10"]

    wrong = make_xlsx("wrong.xlsx", 9, 7)
    with _xlsx_stream_book(wrong) as book:
        rows, weeks, months, errors = _stream_monthly_recovery_fifo(
            wrong, ["Octubre 26"], book
        )
    assert any("conciliar DEV" in msg for msg in errors), errors


def test_reversed_labels_never_use_positional_fallback():
    from daily_sales_headers import infer_dated_groups_without_labels
    rows = [
        {29:"2026-10-25"},
        {29:"Dev Pzs", 30:"Ventas Neta Pzs", 31:"Venta Neta en $"},
        {1:"SKU",25:"Puebla Sur",27:5,29:5,30:2,31:100},
    ]
    detected, idx = infer_dated_groups_without_labels(rows)
    assert detected == []
