from datetime import datetime
import json

import pandas as pd
from openpyxl import Workbook

import web_app


def _operations_workbook(path):
    wb=Workbook()
    op=wb.active
    op.title="Resultados productividad 1"
    op.append([
        "Fecha","Ocurrencia","Tienda","Tabla","Actividad Realizada","Área",
        "Número de Piezas","Hora Inicio","Hora Fin","Nombre","Motivo de ingreso","RECORRIDOS",
    ])
    op.append([
        datetime(2026,8,24),"1","Iztapalapa","Operación","Recolección de muertos","Piso",
        10,"08:00","09:00","Persona","Muertos",1,
    ])

    monthly=wb.create_sheet("Agosto 26")
    first=[None]*32
    first[29]=datetime(2026,8,24)
    monthly.append(first)
    monthly.append([None]*32)
    row=[None]*32
    row[1]="1001";row[7]="ROJO";row[24]=10;row[25]="Iztapalapa"
    row[29]=4;row[30]=10;row[31]=40
    monthly.append(row)
    wb.save(path)


def test_operations_parser_stores_compact_fifo_without_daily_rows(tmp_path):
    source=tmp_path/"operaciones.xlsx"
    _operations_workbook(source)

    payload=web_app.parse_operations_excel(source,persist=False)

    assert payload["parser_version"]==41
    assert "commercial_daily" not in payload
    assert "commercial" not in payload
    assert len(payload["rows"])==1
    assert len(payload["recovery_fifo"])==1
    lot=payload["recovery_fifo"][0]
    assert lot["dev_pzs"]==10
    assert lot["converted_pieces"]==4
    assert lot["return_value"]==100
    assert lot["recovered_value"]==40


def test_model_detail_is_capped_to_keep_browser_responsive(monkeypatch):
    count=220
    frame=pd.DataFrame({
        "Tienda":["Iztapalapa"]*count,
        "ID_ART":[str(index) for index in range(count)],
        "Modelo":[f"M{index}" for index in range(count)],
        "Marca":["Marca"]*count,
        "Sección":["Dama"]*count,
        "Subcategoría":["Blusa"]*count,
        "Tipo catálogo":["VIGENTE"]*count,
        "Existencia":[1.0]*count,
        "Existencia piso":[1.0]*count,
        "Existencia bodega":[0.0]*count,
        "VPD":[1.0]*count,
        "Capacidad":[1.0]*count,
        "Venta pzas 7":[1.0]*count,
        "Venta pzas 30":[1.0]*count,
        "Venta pzas":[1.0]*count,
        "Venta $ 7":[1.0]*count,
        "Venta $ mes":[1.0]*count,
        "DDI":[1.0]*count,
        "Pzas última entrada":[0.0]*count,
        "Última entrada CEDIS a tienda":[pd.NaT]*count,
        "Ubicación detalle":["Piso"]*count,
        "Exhibición":["Colgado"]*count,
    })
    monkeypatch.setattr(web_app,"_capacity_frame_for_period",lambda _period:frame)
    monkeypatch.setattr(web_app,"store_names",lambda _active=True:["Iztapalapa"])

    rows=web_app._capacity_model_rows("Compañía","Todas","80_20","2026-W35","Todos")

    assert len(rows)==150


def test_legacy_operations_json_is_compacted_without_daily_history(monkeypatch,tmp_path):
    source=tmp_path/"operaciones.json"
    source.write_text(web_app._safe_json_dump({
        "parser_version":40,
        "rows":[{"store":"Iztapalapa","date":"2026-08-24"}],
        "commercial":[{"unused":True}],
        "commercial_daily":[{"unused":True}],
        "recovery_fifo":[{"store":"Iztapalapa","date":"2026-08-24","dev_pzs":2.5}],
        "weeks":["2026-W35"],
    }),encoding="utf-8")
    monkeypatch.setattr(web_app,"OPS_FILE",source)
    monkeypatch.setattr(web_app,"_OPS_LEGACY_COMPACT_MIN_BYTES",0)

    web_app._compact_legacy_operations_file()
    compact=json.loads(source.read_text(encoding="utf-8"))

    assert compact["parser_version"]==41
    assert compact["rows"][0]["store"]=="Iztapalapa"
    assert compact["recovery_fifo"][0]["dev_pzs"]==2.5
    assert "commercial" not in compact
    assert "commercial_daily" not in compact


def test_frontend_hides_render_html_errors_and_serializes_rankings():
    source=(web_app.WEB/"index.html").read_text(encoding="utf-8")
    assert "El servicio se reinició durante el proceso" in source
    assert "cleanText=/<\\s*!doctype|<\\s*html/i.test(raw)?'':" in source
    ranking_block=source[source.index("async function loadModelTables"):source.index("async function loadChecklistSummary")]
    assert "Promise.all(calls)" not in ranking_block
