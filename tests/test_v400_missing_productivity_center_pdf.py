"""V400: padrón activo real, filtros Proyecto y apéndice en la última hoja PDF."""
from contextlib import contextmanager
from io import BytesIO
import sqlite3

from pypdf import PdfReader
from reportlab.pdfgen import canvas

from v400_missing_productivity_center_pdf import build_missing, appendix, bounds


class FakeModule:
    def __init__(self):
        self.connection=sqlite3.connect(":memory:")
        self.connection.row_factory=sqlite3.Row
        self.connection.execute("""CREATE TABLE operation_collaborators
             (store TEXT,name_key TEXT,name TEXT,first_seen TEXT,last_seen TEXT,
              last_activity TEXT,active INTEGER)""")
        self.connection.executemany(
            "INSERT INTO operation_collaborators VALUES(?,?,?,?,?,?,?)",
            [
                ("Puebla Sur","ana lopez","Ana López","2026-09-20","2026-10-24","Ubicado",1),
                ("Puebla Sur","carlos","Carlos","2026-09-20","2026-10-25","Recolección",1),
                ("Puebla Sur","maria","María","2026-09-20","2026-10-24","Acondicionado",1),
                ("Vallejo","baja","Baja","2026-09-15","2026-10-20","Ubicado",0),
                ("Ecatepec","other","Otro","2026-09-15","2026-10-20","Ubicado",1),
                ("Puebla Sur","new","Alta posterior","2026-10-26","2026-10-26","Ubicado",1),
            ],
        )
        self.connection.execute("""CREATE TABLE operation_productivity
            (store TEXT,employee_name TEXT,date TEXT,pieces REAL)""")
        self.connection.execute("""CREATE TABLE operation_productivity_timer
            (store TEXT,employee_name TEXT,date TEXT,pieces REAL,status TEXT)""")
        self.connection.execute(
            "INSERT INTO operation_productivity_timer VALUES(?,?,?,?,?)",
            ("Puebla Sur","María","2026-10-25",15,"finished")
        )
        self.rows=[
            {"store":"Puebla Sur","name":"Ana López","date":"2026-10-24",
             "activity":"Ubicado","pieces":25},
            {"store":"Puebla Sur","name":"Carlos","date":"2026-10-25",
             "activity":"Recolección","pieces":10},
            {"store":"Ecatepec","name":"Otro","date":"2026-10-20",
             "activity":"Ubicado","pieces":30},
        ]
    @contextmanager
    def db(self):
        yield self.connection
    def load_ops(self):
        return {"rows":self.rows}


def test_only_active_project_roster_without_positive_capture():
    m=FakeModule()
    result=build_missing(m,["Puebla Sur","Vallejo"],"day","2026-10-25")
    assert result["count"]==1
    assert result["store_count"]==1
    assert [r["name"] for r in result["rows"]]==["Ana López"]
    assert result["rows"][0]["last_date"]=="2026-10-24"
    assert "days_without_record" not in result["rows"][0]
    assert result["rows"][0]["status"]=="Sin captura de productividad"


def test_week_is_monday_to_sunday_and_not_other_stores():
    m=FakeModule()
    a,b=bounds("week","2026-W43")
    assert a.isoformat()=="2026-10-19"
    assert b.isoformat()=="2026-10-25"
    result=build_missing(m,["Puebla Sur"],"week","2026-W43")
    assert result["count"]==0   # Ana sí capturó el 24 dentro de esa semana.
    only_ecatepec=build_missing(m,["Ecatepec"],"day","2026-10-25")
    assert [r["name"] for r in only_ecatepec["rows"]]==["Otro"]
    assert build_missing(m,[],"day","2026-10-25")["count"]==0


def test_empty_roster_fails_closed_no_made_up_names():
    m=FakeModule()
    m.connection.execute("DELETE FROM operation_collaborators")
    result=build_missing(m,["Puebla Sur"],"day","2026-10-25")
    assert result["rows"] == []


def test_pdf_appends_last_table_and_preserves_prior_pages():
    original=BytesIO()
    c=canvas.Canvas(original)
    c.drawString(50,600,"Pagina original - conservar")
    c.save()
    data=build_missing(FakeModule(),["Puebla Sur"],"day","2026-10-25")
    merged=appendix(original.getvalue(),data)
    doc=PdfReader(BytesIO(merged))
    assert len(doc.pages)==2
    assert "Pagina original" in doc.pages[0].extract_text()
    assert "Colaboradores sin productividad" in doc.pages[-1].extract_text()
    assert "Ana" in doc.pages[-1].extract_text()
    assert "Puebla Sur" in doc.pages[-1].extract_text()
    assert "Días sin captura" not in doc.pages[-1].extract_text()


def test_pdf_many_employees_paginated_without_omitting_names():
    base=BytesIO()
    c=canvas.Canvas(base);c.drawString(40,500,"Reporte base");c.save()
    data={"period_value":"2026-10","start_date":"2026-10-01",
          "end_date":"2026-10-31","count":78,"store_count":2,
          "rows":[{"name":f"Colaborador {i:03d}","store":"Vallejo",
                   "last_date":"","profile":"Operativo",
                   "status":"Sin captura"}
                  for i in range(78)]}
    out=PdfReader(BytesIO(appendix(base.getvalue(),data)))
    assert len(out.pages)>=4
    last_text=" ".join(p.extract_text() for p in out.pages[1:])
    assert "Colaborador 000" in last_text
    assert "Colaborador 077" in last_text
