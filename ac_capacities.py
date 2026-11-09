"""Capacidades por talla: importación y consulta con histórico."""
from __future__ import annotations
import io
import sqlite3
import unicodedata
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from openpyxl import load_workbook

ALIASES={"store":("TIENDA","SUCURSAL"),"model":("ID_ART","ID ART","MODELO","ID"),"size":("TALLA","SIZE"),"curve":("CURVA TALLA","CURVA POR TALLA","CURVA"),"capacity":("CAPACIDAD TALLA","CAPACIDAD POR TALLA","CAPACIDAD")}
def norm(value):
    text=unicodedata.normalize("NFKD",str(value or ""))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).upper().split())
def to_int(value):
    if isinstance(value,bool) or value is None or str(value).strip()=="":
        raise ValueError("Curva/capacidad faltante")
    n=Decimal(str(value).strip())
    if n<0 or n!=n.to_integral_value():
        raise ValueError("Curva/capacidad debe ser entero no negativo")
    return int(n)
def parse_excel(content:bytes):
    if not isinstance(content,bytes) or len(content)>15*1024*1024 or not content:
        raise ValueError("Excel vacío o mayor a 15 MB")
    book=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
    try:
        values=book.active.iter_rows(values_only=True)
        header=next(values,None)
        if not header:raise ValueError("Archivo sin encabezados")
        names={norm(v):i for i,v in enumerate(header)}
        fields={}
        for key,aliases in ALIASES.items():
            fields[key]=next((names[norm(a)] for a in aliases if norm(a) in names),None)
            if fields[key] is None:raise ValueError("Falta columna "+key)
        rows=[];seen=set()
        for line,rec in enumerate(values,2):
            if not any(v is not None for v in rec):continue
            get=lambda key: rec[fields[key]] if fields[key]<len(rec) else None
            store=str(get("store") or "").strip();model=str(get("model") or "").strip();size=norm(get("size"))
            if not all((store,model,size)):raise ValueError("Fila %d sin tienda, ID o talla"%line)
            key=(norm(store),model,size)
            if key in seen:raise ValueError("Talla duplicada en fila %d"%line)
            seen.add(key);rows.append((store,model,size,to_int(get("curve")),to_int(get("capacity"))))
        if not rows:raise ValueError("Archivo sin registros")
        return rows
    finally:book.close()
class CapacityStore:
    def __init__(self,path):self.path=Path(path)
    def initialize(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS ac_capacity_excel_batches(
              id INTEGER PRIMARY KEY,version TEXT NOT NULL UNIQUE,uploaded_by TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS ac_capacity_excel_sizes(
              batch_id INTEGER REFERENCES ac_capacity_excel_batches(id),store TEXT NOT NULL,model TEXT NOT NULL,
              size TEXT NOT NULL,curve INTEGER NOT NULL CHECK(curve>=0),capacity INTEGER NOT NULL CHECK(capacity>=0),
              PRIMARY KEY(batch_id,store,model,size));
            CREATE INDEX IF NOT EXISTS ac_capacity_excel_lookup ON ac_capacity_excel_sizes(store,model,size);
            """)
    def upload(self,contents:bytes,*,version:str,uploaded_by:str):
        rows=parse_excel(contents)
        if not version.strip() or not uploaded_by.strip():raise ValueError("Versión y administrador obligatorios")
        with sqlite3.connect(self.path,timeout=15) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            cur=db.execute("INSERT INTO ac_capacity_excel_batches(version,uploaded_by,created_at) VALUES(?,?,?)",
                (version,uploaded_by,datetime.now(timezone.utc).isoformat()))
            db.executemany("INSERT INTO ac_capacity_excel_sizes VALUES(?,?,?,?,?,?)",[(cur.lastrowid,*r) for r in rows])
            return cur.lastrowid
    def model_sizes(self, store, model):
        """Tallas de UN solo corte vigente por tienda e ID: nunca mezclar
        rangos de distintas versiones del Excel.
        """
        store=str(store or "").strip()
        model=str(model or "").strip()
        if not store or not model:
            return {"status":"not_found","sizes":[],"version":None}
        with sqlite3.connect(self.path,timeout=15) as db:
            db.row_factory=sqlite3.Row
            current=db.execute("""
                SELECT s.batch_id,b.version FROM ac_capacity_excel_sizes s
                JOIN ac_capacity_excel_batches b ON b.id=s.batch_id
                WHERE UPPER(TRIM(s.store))=UPPER(?) AND s.model=?
                ORDER BY s.batch_id DESC LIMIT 1
            """,(store,model)).fetchone()
            if not current:
                return {"status":"not_found","sizes":[],"version":None}
            sizes=[dict(r) for r in db.execute("""
                SELECT size,curve,capacity FROM ac_capacity_excel_sizes
                WHERE batch_id=? AND UPPER(TRIM(store))=UPPER(?) AND model=?
            """,(current["batch_id"],store,model)).fetchall()]
        def size_key(item):
            import re
            value=item["size"].upper().strip()
            names={"XXCH":0,"XCH":1,"CH":2,"M":3,"G":4,"XG":5,"XXG":6,"3XG":7}
            if value in names:return (0,names[value],"")
            digits=re.findall(r"\d+",value)
            if digits:return (1,int(digits[0]),int(digits[1]) if len(digits)>1 else 0,value)
            return (2,0,0,value)
        sizes.sort(key=size_key)
        return {"status":"ready","sizes":sizes,"version":current["version"],
                "from_size":sizes[0]["size"] if sizes else None,
                "to_size":sizes[-1]["size"] if sizes else None}

    def latest(self,store,model,size):
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row
            row=db.execute("""SELECT s.curve,s.capacity,b.version FROM ac_capacity_excel_sizes s
              JOIN ac_capacity_excel_batches b ON b.id=s.batch_id
              WHERE s.store=? AND s.model=? AND s.size=? ORDER BY b.id DESC LIMIT 1""",
              (store,model,norm(size))).fetchone()
            return dict(row) if row else None
