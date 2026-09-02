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


def test_xlsx_operations_parser_never_materializes_sheets_with_pandas(monkeypatch,tmp_path):
    source=tmp_path/"operaciones_stream.xlsx"
    _operations_workbook(source)
    monkeypatch.setattr(pd,"read_excel",lambda *_args,**_kwargs:(_ for _ in ()).throw(AssertionError("read_excel no debe usarse para XLSX")))

    payload=web_app.parse_operations_excel(source,persist=False)

    assert len(payload["rows"])==1
    assert len(payload["recovery_fifo"])==1


def test_operations_upload_parser_uses_single_runtime(monkeypatch,tmp_path):
    source=tmp_path/"operaciones.xlsx"
    source.write_bytes(b"placeholder")
    called=[]
    monkeypatch.setitem(web_app._OPS_DATA_CACHE,"stamp",123)
    monkeypatch.setitem(web_app._OPS_DATA_CACHE,"data",{"rows":[{"old":True}]})
    monkeypatch.setattr(web_app,"parse_operations_excel",lambda path,persist=False:called.append((path,persist)) or {"ok":True})
    monkeypatch.setattr(web_app,"_release_process_memory",lambda:None)

    payload=web_app._parse_operations_external(source,"token")

    assert payload=={"ok":True}
    assert called==[(source,False)]
    assert web_app._OPS_DATA_CACHE["stamp"] is None
    assert web_app._OPS_DATA_CACHE["data"] is None


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
def test_recent_low_suggested_models_are_not_repeated_in_slow(monkeypatch):
    frame=pd.DataFrame({
        "Tienda":["Iztapalapa"]*4,
        "ID_ART":["ZERO-OLD","ZERO-NEW","ONE-NEW","SLOW"],
        "Modelo":["Cero antiguo","Cero reciente","Uno reciente","Lento"],
        "Marca":["Marca"]*4,
        "Sección":["Dama"]*4,
        "Subcategoría":["Blusa"]*4,
        "Tipo catálogo":["VIGENTE"]*4,
        "Existencia":[10.0,9.0,8.0,7.0],
        "Existencia piso":[10.0,9.0,8.0,7.0],
        "Existencia bodega":[0.0]*4,
        "VPD":[0.0,0.0,1.0,1.0],
        "Capacidad":[10.0]*4,
        "Venta pzas 7":[0.0,0.0,0.0,1.0],
        "Venta pzas 30":[0.0,0.0,0.0,1.0],
        "Venta pzas":[0.0,0.0,0.0,1.0],
        "Venta $ 7":[0.0,0.0,0.0,10.0],
        "Venta $ mes":[0.0,0.0,0.0,10.0],
        "DDI":[0.0]*4,
        "Pzas última entrada":[1.0]*4,
        "Última entrada CEDIS a tienda":[
            pd.Timestamp("2026-07-01"),pd.Timestamp("2026-08-20"),
            pd.Timestamp("2026-08-18"),pd.Timestamp("2026-07-15"),
        ],
        "Ubicación detalle":["R. COLGADA 01"]*4,
        "Exhibición":["Colgado"]*4,
    })
    monkeypatch.setattr(web_app,"_capacity_frame_for_period",lambda _period:frame)
    monkeypatch.setattr(web_app,"_capacity_source_entry",lambda _period:{"id":"now","report_date":"2026-09-01"})
    monkeypatch.setattr(web_app,"store_names",lambda _active=True:["Iztapalapa"])
    monkeypatch.setattr(web_app,"_capacity_recurrence_counts",lambda ids,*_args:{value:(2 if value=="ONE-NEW" else 1) for value in ids})

    zeros=web_app._capacity_model_rows("Compañía","Todas","suggested_zero","2026-W36","Todos")
    slows=web_app._capacity_model_rows("Compañía","Todas","slow","2026-W36","Todos")

    assert [row["id_art"] for row in zeros]==["ZERO-NEW","ONE-NEW"]
    assert next(row for row in zeros if row["id_art"]=="ONE-NEW")["recurrence_weeks"]==2
    assert {"ZERO-NEW","ONE-NEW"}.isdisjoint({row["id_art"] for row in slows})
    assert {row["id_art"] for row in slows}=={"ZERO-OLD","SLOW"}


def test_exhibition_uses_each_specific_location(monkeypatch):
    frame=pd.DataFrame({
        "Tienda":["Iztapalapa","Iztapalapa"],"ID_ART":["1001","1001"],
        "Modelo":["M1","M1"],"Marca":["Marca","Marca"],"Sección":["Dama","Dama"],
        "Subcategoría":["Blusa","Blusa"],"Tipo catálogo":["VIGENTE","VIGENTE"],
        "Existencia":[1.0,1.0],"Existencia piso":[1.0,1.0],"Existencia bodega":[0.0,0.0],
        "VPD":[1.0,1.0],"Capacidad":[1.0,1.0],"Venta pzas 7":[2.0,2.0],
        "Venta pzas 30":[2.0,2.0],"Venta pzas":[2.0,2.0],"Venta $ 7":[20.0,20.0],
        "Venta $ mes":[20.0,20.0],"DDI":[1.0,1.0],"Pzas última entrada":[0.0,0.0],
        "Última entrada CEDIS a tienda":[pd.NaT,pd.NaT],
        "Ubicación detalle":["Cabecera 30A","Isla 02"],"Exhibición":["Cabecera","Isla"],
    })
    monkeypatch.setattr(web_app,"_capacity_frame_for_period",lambda _period:frame)
    monkeypatch.setattr(web_app,"store_names",lambda _active=True:["Iztapalapa"])

    rows=web_app._capacity_model_rows("Compañía","Todas","80_20","2026-W36","Todos")

    assert len(rows)==1
    assert "Cabecera 30A" in rows[0]["exhibition"]
    assert "Isla 02" in rows[0]["exhibition"]


def test_capacity_preparation_and_requested_frontend_controls():
    frame=pd.DataFrame({
        "Tienda":["Iztapalapa","Iztapalapa"],
        "Sección":["Dama","Caballero"],
        "Tipo catálogo":["VIGENTE","VIGENTE"],
        "Ubicación":["R. COLGADA 01","MESA 04"],
        "Pasillo":["R. COLGADA 01","MESA 04"],
    })
    prepared=web_app._prepare_capacity_frame(frame)
    assert str(prepared["Tienda"].dtype)=="category"
    assert {"Área reporte","Pasillo operativo","_TiendaKey","_SeccionKey","_CatalogKey"}.issubset(prepared.columns)

    source=(web_app.WEB/"index.html").read_text(encoding="utf-8")
    for label in ('data-area-group="Colgado"','data-area-group="Doblado"','data-area-group="Jeans"','data-area-group="Lencería"'):
        assert label in source
    assert "table-scroll-35" in source
    assert "Últ. entrada" in source
    assert "recurrence-yellow" in source and "recurrence-red" in source
    assert "/api/export/checklist-evidence" in source
    for label in ('data-rubro-section="Dama"','data-rubro-section="Caballero"','data-rubro-section="Infantil"','data-rubro-section="Lencería"'):
        assert label in source
    assert "% checklist" in source and "% evidencias" in source
    assert "Piso '+fmt(k.floor)+' pzas" in source
