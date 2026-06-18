
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sqlite3
import json
import re
from pathlib import Path
from io import BytesIO
from datetime import datetime

# ==========================================================
# ORION PRO v1.1 LIMPIO
# PRICE SHOES | OPERACIONES ROPA
# Plataforma Indicadores de Recuperación de Mercancía
# ==========================================================

st.set_page_config(page_title="ORION PRO v1.1", page_icon="🚀", layout="wide")

DATA_DIR = Path("orion_data")
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "orion_config.db"
OPERACION_FILE = DATA_DIR / "operacion.parquet"
COMERCIAL_FILE = DATA_DIR / "comercial.parquet"
DIARIO_COMERCIAL_FILE = DATA_DIR / "comercial_diario.parquet"

TIENDAS_OFICIALES = [
    "Iztapalapa", "Vallejo", "Ecatepec", "Toluca", "Arco Norte",
    "Ixtapaluca", "Querétaro", "Centro", "Olivar", "León",
    "Puebla", "Puebla Sur", "Aguascalientes", "Veracruz",
    "Naucalpan", "Miravalle", "Atemajac"
]

DEFAULT_METAS = {
    "productividad_diaria": 784.0,
    "conversion": 80.0,
    "recuperacion": 80.0,
    "habilitado_ingresos": 85.0,
    "ubicado_ingresos": 80.0,
    "recorridos_lunes": 5.0,
    "recorridos_martes": 5.0,
    "recorridos_miercoles": 5.0,
    "recorridos_jueves": 8.0,
    "recorridos_viernes": 8.0,
    "recorridos_sabado": 8.0,
    "recorridos_domingo": 8.0,
    "recorridos_semanales": 47.0,
}

# ==========================================================
# ESTILO CORPORATIVO
# ==========================================================
st.markdown("""
<style>
.stApp {background-color:#F5F5F5;}
.block-container {padding-top:1rem; padding-bottom:2rem;}
.orion-header {
    background: linear-gradient(90deg, #003366 0%, #3366CC 70%, #FF99FF 130%);
    color:white;
    padding:24px 30px;
    border-radius:24px;
    box-shadow:0 8px 26px rgba(0,0,0,.18);
    margin-bottom:18px;
}
.orion-title {font-size:40px;font-weight:900;margin:0;}
.orion-sub {font-size:17px;margin-top:4px;}
.orion-mini {font-size:13px;margin-top:10px;opacity:.95;}
div[data-testid="stMetric"] {
    background:#FFFFFF;
    border:1px solid #DDE7F7;
    border-top:5px solid #3366CC;
    border-radius:18px;
    padding:15px;
    box-shadow:0 6px 18px rgba(0,51,102,.08);
}
.card {
    background:#FFFFFF;
    border:1px solid #DDE7F7;
    border-radius:18px;
    padding:16px;
    box-shadow:0 5px 16px rgba(0,51,102,.06);
}
.confidencial {
    background:white;
    border-left:7px solid #FF99FF;
    padding:12px 16px;
    border-radius:14px;
    color:#334155;
    font-size:12px;
    margin-top:20px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# DB
# ==========================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS metas (
        clave TEXT PRIMARY KEY,
        valor REAL,
        actualizado TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS historial_metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora TEXT,
        usuario TEXT,
        meta TEXT,
        anterior REAL,
        nueva REAL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS estado (
        clave TEXT PRIMARY KEY,
        valor TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS nombres_empleado (
        ocurrencia TEXT PRIMARY KEY,
        nombre_correcto TEXT,
        actualizado TEXT
    )""")
    for k, v in DEFAULT_METAS.items():
        cur.execute(
            "INSERT OR IGNORE INTO metas(clave, valor, actualizado) VALUES (?, ?, ?)",
            (k, float(v), datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

def get_metas():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT clave, valor FROM metas", conn)
    conn.close()
    metas = DEFAULT_METAS.copy()
    if not df.empty:
        metas.update(dict(zip(df["clave"], df["valor"])))
    return metas

def update_meta(clave, valor, usuario="Administrador"):
    metas = get_metas()
    anterior = float(metas.get(clave, 0))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE metas SET valor=?, actualizado=? WHERE clave=?", (float(valor), datetime.now().isoformat(), clave))
    now = datetime.now()
    cur.execute(
        "INSERT INTO historial_metas(fecha,hora,usuario,meta,anterior,nueva) VALUES (?,?,?,?,?,?)",
        (str(now.date()), now.strftime("%H:%M:%S"), usuario, clave, anterior, float(valor))
    )
    conn.commit()
    conn.close()

def get_historial_metas():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM historial_metas ORDER BY id DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def set_estado(clave, valor):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO estado(clave, valor) VALUES (?, ?)", (clave, str(valor)))
    conn.commit()
    conn.close()

def get_estado(clave, default=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT valor FROM estado WHERE clave=?", (clave,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def get_nombre_map():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT ocurrencia, nombre_correcto FROM nombres_empleado", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        return {}
    return dict(zip(df["ocurrencia"].astype(str), df["nombre_correcto"].astype(str)))

def save_nombre_map(mapping):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    for k, v in mapping.items():
        if str(k).strip() and str(v).strip():
            cur.execute(
                "INSERT OR REPLACE INTO nombres_empleado(ocurrencia,nombre_correcto,actualizado) VALUES (?,?,?)",
                (str(k), str(v), now)
            )
    conn.commit()
    conn.close()

init_db()

# ==========================================================
# UTILIDADES
# ==========================================================
def n0(x):
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"

def p1(x):
    try:
        return f"{float(x):,.1f}%"
    except Exception:
        return "0.0%"

def money(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return "$0"

def to_num(x):
    if pd.isna(x):
        return 0.0
    if isinstance(x, str):
        x = x.replace("$", "").replace(",", "").replace(" ", "").strip()
        if x in ["", "-", "nan", "None"]:
            return 0.0
    try:
        y = pd.to_numeric(x, errors="coerce")
        return 0.0 if pd.isna(y) else float(y)
    except Exception:
        return 0.0

def clean_text(x):
    if pd.isna(x):
        return "Sin dato"
    s = str(x).strip()
    if s.lower() in ["nan", "none", ""]:
        return "Sin dato"
    return s

def pct(a, b):
    try:
        a = float(a)
        b = float(b)
        return (a / b * 100) if b else 0.0
    except Exception:
        return 0.0

def sdiv(a, b):
    a = pd.to_numeric(a, errors="coerce").fillna(0)
    b = pd.to_numeric(b, errors="coerce").fillna(0)
    return np.where(b != 0, a / b, 0)

def normalize_store(x):
    s = clean_text(x).upper()
    replacements = {
        "GUADALAJARA MIRAVALLE": "Miravalle",
        "MIRAVALLE": "Miravalle",
        "PUEBLA SUR": "Puebla Sur",
        "PUEBLA": "Puebla",
        "ARCO NORTE": "Arco Norte",
        "IZTAPALAPA": "Iztapalapa",
        "VALLEJO": "Vallejo",
        "ECATEPEC": "Ecatepec",
        "TOLUCA": "Toluca",
        "IXTAPALUCA": "Ixtapaluca",
        "QUERETARO": "Querétaro",
        "QUERÉTARO": "Querétaro",
        "CENTRO": "Centro",
        "OLIVAR": "Olivar",
        "LEON": "León",
        "LEÓN": "León",
        "AGUASCALIENTES": "Aguascalientes",
        "VERACRUZ": "Veracruz",
        "NAUCALPAN": "Naucalpan",
        "ATEMAJAC": "Atemajac",
    }
    for key, val in replacements.items():
        if key in s:
            return val
    return clean_text(x).title()

def style_dataframe(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    return df.style.set_table_styles([
        {"selector": "th", "props": [("background-color", "#003366"), ("color", "white"), ("font-weight", "bold")]},
        {"selector": "td", "props": [("border", "1px solid #DDE7F7")]},
    ]).format(precision=0, thousands=",")

def excel_export(sheets):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return bio.getvalue()

def export_buttons(name, sheets):
    st.download_button(
        f"⬇️ Exportar {name} Excel",
        data=excel_export(sheets),
        file_name=f"{name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    if sheets:
        first = list(sheets.values())[0]
        if isinstance(first, pd.DataFrame):
            st.download_button(
                f"⬇️ Exportar {name} CSV",
                data=first.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{name}.csv",
                mime="text/csv"
            )

def current_or_latest_week(df):
    if df.empty or "Semana ISO" not in df.columns:
        return []
    weeks = sorted([int(x) for x in df["Semana ISO"].dropna().unique()])
    return [max(weeks)] if weeks else []

# ==========================================================
# PROCESAMIENTO DE EXCEL REAL
# ==========================================================
def detectar_hoja_operativa(hojas):
    for h in hojas:
        h2 = h.lower().replace(" ", "")
        if "resultados" in h2 and "productividad" in h2:
            return h
    for h in hojas:
        if "productividad" in h.lower():
            return h
    return None

def detectar_hojas_mensuales(hojas):
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    return [h for h in hojas if any(m in h.lower() for m in meses) and ("26" in h or "2026" in h)]

def cargar_operacion(file, hoja):
    df = pd.read_excel(file, sheet_name=hoja)
    df.columns = [str(c).strip() for c in df.columns]

    # Renombrar columnas reales
    rename = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ["occurrence", "ocurrencia"]:
            rename[c] = "Ocurrencia"
        elif cl in ["ubicación", "ubicacion", "tienda", "sucursal"]:
            rename[c] = "Tienda"
        elif cl in ["fecha"]:
            rename[c] = "Fecha"
        elif cl in ["fecha s", "fechas"]:
            rename[c] = "Fecha Base"
        elif cl in ["actividad realizada", "actividad"]:
            rename[c] = "Actividad Realizada"
        elif cl in ["área", "area"]:
            rename[c] = "Área"
        elif cl in ["número de piezas", "numero de piezas", "piezas", "pzas"]:
            rename[c] = "Número de Piezas"
        elif "recorrido" in cl:
            rename[c] = "Recorridos"
        elif cl in ["nombre", "usuario", "colaborador"]:
            if "Nombre" not in rename.values():
                rename[c] = "Nombre"
        elif cl in ["motivo de ingreso", "motivo"]:
            rename[c] = "Motivo de ingreso"

    df = df.rename(columns=rename)

    # Si hay columna nombre duplicada minúscula, llenar nombre
    nombre_cols = [c for c in df.columns if str(c).lower() == "nombre"]
    if len(nombre_cols) > 1:
        base = df[nombre_cols[0]]
        for c in nombre_cols[1:]:
            base = base.fillna(df[c])
        df["Nombre"] = base
        df = df.loc[:, ~df.columns.duplicated()]

    required = ["Fecha", "Fecha Base", "Ocurrencia", "Tienda", "Actividad Realizada", "Área", "Número de Piezas", "Nombre", "Motivo de ingreso", "Recorridos"]
    for c in required:
        if c not in df.columns:
            df[c] = np.nan

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Fecha Base"] = pd.to_datetime(df["Fecha Base"], errors="coerce")
    df["Fecha Día"] = df["Fecha"].fillna(df["Fecha Base"]).dt.date
    df["Semana ISO"] = pd.to_datetime(df["Fecha Día"], errors="coerce").dt.isocalendar().week.astype("Int64")
    df["Año ISO"] = pd.to_datetime(df["Fecha Día"], errors="coerce").dt.isocalendar().year.astype("Int64")
    df["Mes"] = pd.to_datetime(df["Fecha Día"], errors="coerce").dt.month_name()

    for c in ["Ocurrencia", "Nombre", "Actividad Realizada", "Área", "Motivo de ingreso"]:
        df[c] = df[c].apply(clean_text)

    df["Tienda"] = df["Tienda"].apply(normalize_store)
    df["Número de Piezas"] = df["Número de Piezas"].apply(to_num)
    # Recorridos: solo cuenta registros con 1
    df["Recorridos"] = pd.to_numeric(df["Recorridos"], errors="coerce").fillna(0)
    df["Recorridos"] = np.where(df["Recorridos"] == 1, 1, 0)

    act = (df["Actividad Realizada"].astype(str) + " " + df["Motivo de ingreso"].astype(str)).str.lower()

    df["Muertos"] = np.where(act.str.contains("muerto", regex=False), df["Número de Piezas"], 0)
    df["Cajas"] = np.where(act.str.contains("caja", regex=False), df["Número de Piezas"], 0)
    df["Probador"] = np.where(act.str.contains("probado|probador", regex=True), df["Número de Piezas"], 0)
    df["Habilitado"] = np.where(act.str.contains("habilitado|habilitar", regex=True), df["Número de Piezas"], 0)
    df["Ubicado"] = np.where(act.str.contains("ubicado|ubicar", regex=True), df["Número de Piezas"], 0)

    df["Recolección de Muertos"] = df["Muertos"] + df["Cajas"] + df["Probador"]
    df["Ingresos Operativos"] = df["Recolección de Muertos"]
    df["Productividad Total"] = df["Recolección de Muertos"] + df["Habilitado"] + df["Ubicado"]

    # Nombre real agrupado por Ocurrencia
    nombre_map = get_nombre_map()
    df["Nombre Real"] = df["Ocurrencia"].astype(str).map(nombre_map).fillna(df["Nombre"])

    return df

def cargar_comercial(file, hoja):
    raw = pd.read_excel(file, sheet_name=hoja, header=None)
    # Fila 1 trae encabezados reales en el archivo actual
    header_row = 1
    rows = []
    daily_rows = []

    # posiciones reales
    meta_cols = {
        "Art Padre": 0, "Id Art": 1, "Marca": 2, "Marca Price": 3, "Modelo": 4,
        "Modelo Proveedor": 5, "Color": 7, "Categoria": 19, "Subcategoria": 20,
        "Precio Mayoreo": 23, "Precio Menudeo": 24, "Tienda": 25,
        "Vta_Pzs": 26, "Dev_Pzs": 27, "Vta_Imp": 28
    }

    data = raw.iloc[2:].copy()
    data = data.dropna(how="all")
    if data.empty:
        return pd.DataFrame(), pd.DataFrame(), header_row, []

    def col(i):
        return data.iloc[:, i] if i < data.shape[1] else pd.Series([np.nan] * len(data), index=data.index)

    df = pd.DataFrame()
    df["Mes_Origen"] = hoja
    df["Id Art"] = col(meta_cols["Id Art"]).apply(clean_text)
    df["Modelo"] = col(meta_cols["Modelo"]).apply(clean_text)
    df["Color"] = col(meta_cols["Color"]).apply(clean_text)
    df["Categoria"] = col(meta_cols["Categoria"]).apply(clean_text)
    df["Subcategoria"] = col(meta_cols["Subcategoria"]).apply(clean_text)
    df["Tienda"] = col(meta_cols["Tienda"]).apply(normalize_store)
    df["Precio Mayoreo"] = col(meta_cols["Precio Mayoreo"]).apply(to_num)
    df["Precio Menudeo"] = col(meta_cols["Precio Menudeo"]).apply(to_num)
    df["Vta_Pzs"] = col(meta_cols["Vta_Pzs"]).apply(to_num)
    df["Dev_Pzs"] = col(meta_cols["Dev_Pzs"]).apply(to_num)
    df["Vta_Imp"] = col(meta_cols["Vta_Imp"]).apply(to_num)

    # Si no hay costo dev, usar precio menudeo * devoluciones; si no hay dev, usar venta como base para no romper.
    df["Costo_Dev"] = df["Precio Menudeo"] * df["Dev_Pzs"]
    df["Costo_Dev"] = np.where(df["Costo_Dev"] > 0, df["Costo_Dev"], df["Vta_Imp"])
    df["Piezas Vendidas Validadas"] = np.minimum(df["Vta_Pzs"], df["Dev_Pzs"])
    df["Conversión %"] = sdiv(df["Piezas Vendidas Validadas"], df["Dev_Pzs"]) * 100
    df["Valor Recuperado"] = df["Vta_Imp"]
    df["Valor Pendiente"] = df["Costo_Dev"] - df["Vta_Imp"]
    df["Recuperación %"] = sdiv(df["Valor Recuperado"], df["Costo_Dev"]) * 100

    # Daily long: columnas 29 en adelante vienen en bloques de 3 con fechas en fila 0
    for idx in range(29, raw.shape[1], 3):
        if idx + 2 >= raw.shape[1]:
            continue
        fecha = pd.to_datetime(raw.iloc[0, idx], errors="coerce", dayfirst=True)
        if pd.isna(fecha):
            continue
        temp = df[["Mes_Origen", "Id Art", "Modelo", "Color", "Categoria", "Subcategoria", "Tienda", "Precio Menudeo"]].copy()
        temp["Fecha Día"] = fecha.date()
        temp["Semana ISO"] = fecha.isocalendar().week
        temp["Vta_Pzs"] = col(idx).apply(to_num)
        temp["Dev_Pzs"] = col(idx+1).apply(to_num)
        temp["Vta_Imp"] = col(idx+2).apply(to_num)
        temp["Costo_Dev"] = temp["Precio Menudeo"] * temp["Dev_Pzs"]
        temp["Costo_Dev"] = np.where(temp["Costo_Dev"] > 0, temp["Costo_Dev"], temp["Vta_Imp"])
        temp["Piezas Vendidas Validadas"] = np.minimum(temp["Vta_Pzs"], temp["Dev_Pzs"])
        temp = temp[(temp["Vta_Pzs"] != 0) | (temp["Dev_Pzs"] != 0) | (temp["Vta_Imp"] != 0)]
        daily_rows.append(temp)

    daily = pd.concat(daily_rows, ignore_index=True) if daily_rows else pd.DataFrame()
    return df, daily, header_row, [str(x) for x in raw.iloc[header_row].tolist()]

def procesar_excel(file):
    xls = pd.ExcelFile(file)
    hojas = xls.sheet_names
    hoja_op = detectar_hoja_operativa(hojas)
    hojas_mensuales = detectar_hojas_mensuales(hojas)

    diag = {
        "hojas_detectadas": hojas,
        "hoja_operativa": hoja_op,
        "hojas_mensuales": hojas_mensuales,
        "errores": [],
        "encabezados": {},
        "columnas": {}
    }

    op = pd.DataFrame()
    co_list = []
    daily_list = []

    if hoja_op:
        try:
            op = cargar_operacion(file, hoja_op)
            diag["columnas"]["operacion"] = list(op.columns)
        except Exception as e:
            diag["errores"].append(f"Operación: {e}")
    else:
        diag["errores"].append("No se detectó hoja de productividad.")

    for h in hojas_mensuales:
        try:
            co, daily, header, cols = cargar_comercial(file, h)
            diag["encabezados"][h] = header
            diag["columnas"][h] = cols
            if not co.empty:
                co_list.append(co)
            if not daily.empty:
                daily_list.append(daily)
        except Exception as e:
            diag["errores"].append(f"{h}: {e}")

    co = pd.concat(co_list, ignore_index=True) if co_list else pd.DataFrame()
    daily = pd.concat(daily_list, ignore_index=True) if daily_list else pd.DataFrame()

    return op, co, daily, diag

def guardar_datos(op, co, daily, diag, filename):
    if not op.empty:
        op.to_parquet(OPERACION_FILE, index=False)
    if not co.empty:
        co.to_parquet(COMERCIAL_FILE, index=False)
    if not daily.empty:
        daily.to_parquet(DIARIO_COMERCIAL_FILE, index=False)
    set_estado("archivo", filename)
    set_estado("ultima_actualizacion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    set_estado("diagnostico", json.dumps(diag, ensure_ascii=False, default=str))

def cargar_datos():
    op = pd.read_parquet(OPERACION_FILE) if OPERACION_FILE.exists() else pd.DataFrame()
    co = pd.read_parquet(COMERCIAL_FILE) if COMERCIAL_FILE.exists() else pd.DataFrame()
    daily = pd.read_parquet(DIARIO_COMERCIAL_FILE) if DIARIO_COMERCIAL_FILE.exists() else pd.DataFrame()
    # Aplicar nombres corregidos si ya hay mapa
    if not op.empty and "Ocurrencia" in op.columns:
        nombre_map = get_nombre_map()
        op["Nombre Real"] = op["Ocurrencia"].astype(str).map(nombre_map).fillna(op.get("Nombre", "Sin dato"))
    return op, co, daily


def normalizar_operacion(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()

    text_cols = ["Tienda", "Ocurrencia", "Nombre", "Nombre Real", "Actividad Realizada", "Área", "Motivo de ingreso"]
    for c in text_cols:
        if c not in df.columns:
            df[c] = "Sin dato"
        df[c] = df[c].fillna("Sin dato").astype(str)

    if "Fecha Día" not in df.columns:
        if "Fecha" in df.columns:
            df["Fecha Día"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
        elif "Fecha Base" in df.columns:
            df["Fecha Día"] = pd.to_datetime(df["Fecha Base"], errors="coerce").dt.date
        else:
            df["Fecha Día"] = pd.NaT

    if "Semana ISO" not in df.columns:
        df["Semana ISO"] = pd.to_datetime(df["Fecha Día"], errors="coerce").dt.isocalendar().week.astype("Int64")

    if "Mes" not in df.columns:
        df["Mes"] = pd.to_datetime(df["Fecha Día"], errors="coerce").dt.month_name()

    num_cols = ["Número de Piezas", "Recorridos", "Muertos", "Cajas", "Probador", "Habilitado", "Ubicado"]
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Recorridos solo cuenta valor 1
    df["Recorridos"] = np.where(df["Recorridos"] == 1, 1, 0)

    df["Recolección de Muertos"] = df["Muertos"] + df["Cajas"] + df["Probador"]
    df["Ingresos Operativos"] = df["Recolección de Muertos"]
    df["Productividad Total"] = df["Recolección de Muertos"] + df["Habilitado"] + df["Ubicado"]

    nombre_map = get_nombre_map()
    df["Nombre Real"] = df["Ocurrencia"].astype(str).map(nombre_map).fillna(df["Nombre Real"]).fillna(df["Nombre"])

    return df

def normalizar_comercial(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()

    text_cols = ["Mes_Origen", "Tienda", "Modelo", "Categoria", "Subcategoria", "Id Art", "Color"]
    for c in text_cols:
        if c not in df.columns:
            df[c] = "Sin dato"
        df[c] = df[c].fillna("Sin dato").astype(str)

    num_cols = ["Dev_Pzs", "Vta_Pzs", "Vta_Imp", "Costo_Dev", "Piezas Vendidas Validadas", "Valor Recuperado", "Valor Pendiente"]
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["Piezas Vendidas Validadas"] = np.minimum(df["Vta_Pzs"], df["Dev_Pzs"])
    df["Valor Recuperado"] = df["Vta_Imp"]
    df["Valor Pendiente"] = df["Costo_Dev"] - df["Vta_Imp"]
    df["Conversión %"] = sdiv(df["Piezas Vendidas Validadas"], df["Dev_Pzs"]) * 100
    df["Recuperación %"] = sdiv(df["Valor Recuperado"], df["Costo_Dev"]) * 100

    return df

def normalizar_diario_comercial(df):
    df = normalizar_comercial(df)
    if df.empty:
        return df
    if "Fecha Día" not in df.columns:
        df["Fecha Día"] = pd.NaT
    if "Semana ISO" not in df.columns:
        df["Semana ISO"] = pd.to_datetime(df["Fecha Día"], errors="coerce").dt.isocalendar().week.astype("Int64")
    return df

# ==========================================================
# HEADER
# ==========================================================
ultima = get_estado("ultima_actualizacion", "Sin actualización")
archivo_cargado = get_estado("archivo", "Sin archivo cargado")
estado = "Disponible" if OPERACION_FILE.exists() or COMERCIAL_FILE.exists() else "Sin datos"
now = datetime.now()

st.markdown(f"""
<div class="orion-header">
    <div style="font-weight:800;letter-spacing:.08em;">PRICE SHOES | OPERACIONES ROPA</div>
    <div class="orion-title">🚀 ORION PRO v1.1</div>
    <div class="orion-sub">Plataforma Indicadores de Recuperación de Mercancía</div>
    <div class="orion-mini">
        Productividad | Conversión | Recuperación Económica | Eficiencia Operativa<br>
        Fecha actual: {now.strftime('%Y-%m-%d')} | Hora actual: {now.strftime('%H:%M:%S')} |
        Última actualización: {ultima} | Estado de información: {estado}
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# SIDEBAR ACCESO / CARGA
# ==========================================================
with st.sidebar:
    st.header("🔐 Acceso")
    rol = st.radio("Rol", ["Consulta", "Administrador"], horizontal=True)
    is_admin = rol == "Administrador"
    if is_admin:
        clave = st.text_input("Clave administrador", type="password")
        is_admin = clave == st.secrets.get("ADMIN_PASSWORD", "orion_admin")
        if not is_admin and clave:
            st.warning("Clave incorrecta.")

    st.divider()
    st.header("📂 Fuente de datos")
    if is_admin:
        uploaded = st.file_uploader("Cargar/Reemplazar Excel", type=["xlsx"])
        if uploaded is not None:
            st.info("Archivo listo. Presiona el botón para procesarlo una sola vez.")
            if st.button("🚀 Procesar archivo", type="primary"):
                with st.spinner("Procesando archivo completo. Puede tardar por el tamaño del Excel..."):
                    try:
                        op_new, co_new, daily_new, diag = procesar_excel(uploaded)
                        guardar_datos(op_new, co_new, daily_new, diag, uploaded.name)
                        st.success("Archivo procesado y guardado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo procesar el archivo: {e}")
            st.caption("Si cambiaste de versión y la app conserva datos viejos, borra la persistencia y vuelve a cargar el Excel.")
        if st.button("🧹 Borrar datos persistidos"):
            for f in [OPERACION_FILE, COMERCIAL_FILE, DIARIO_COMERCIAL_FILE]:
                try:
                    if f.exists():
                        f.unlink()
                except Exception:
                    pass
            set_estado("archivo", "Sin archivo cargado")
            set_estado("ultima_actualizacion", "Sin actualización")
            st.success("Datos persistidos borrados. Vuelve a cargar el Excel.")
            st.rerun()

    else:
        st.caption("Modo consulta: visualización sin carga de archivo.")

op_all, co_all, daily_all = cargar_datos()
op_all = normalizar_operacion(op_all)
co_all = normalizar_comercial(co_all)
daily_all = normalizar_diario_comercial(daily_all)

if op_all.empty and co_all.empty:
    st.warning("No hay datos cargados. Un administrador debe cargar el Excel por primera vez.")
    st.stop()

metas = get_metas()

# ==========================================================
# FILTROS GLOBALES
# ==========================================================
with st.sidebar:
    st.divider()
    st.header("🎛️ Filtros globales")

    # Semana default: última semana disponible
    semanas_disponibles = sorted([int(x) for x in op_all.get("Semana ISO", pd.Series(dtype=float)).dropna().unique()]) if not op_all.empty else []
    default_semana = [max(semanas_disponibles)] if semanas_disponibles else []

    meses = sorted(set(op_all.get("Mes", pd.Series(dtype=str)).dropna().astype(str).tolist() + co_all.get("Mes_Origen", pd.Series(dtype=str)).dropna().astype(str).tolist()))
    tiendas = sorted(set(TIENDAS_OFICIALES + op_all.get("Tienda", pd.Series(dtype=str)).dropna().astype(str).tolist() + co_all.get("Tienda", pd.Series(dtype=str)).dropna().astype(str).tolist()))
    actividades = sorted(op_all.get("Actividad Realizada", pd.Series(dtype=str)).dropna().astype(str).unique()) if not op_all.empty else []
    categorias = sorted(co_all.get("Categoria", pd.Series(dtype=str)).dropna().astype(str).unique()) if not co_all.empty else []
    subcats = sorted(co_all.get("Subcategoria", pd.Series(dtype=str)).dropna().astype(str).unique()) if not co_all.empty else []
    modelos = sorted(co_all.get("Modelo", pd.Series(dtype=str)).dropna().astype(str).unique()) if not co_all.empty else []
    colaboradores = sorted(op_all.get("Nombre Real", pd.Series(dtype=str)).dropna().astype(str).unique()) if not op_all.empty else []
    ocurrencias = sorted(op_all.get("Ocurrencia", pd.Series(dtype=str)).dropna().astype(str).unique()) if not op_all.empty else []

    f_semana = st.multiselect("Semana ISO", semanas_disponibles, default=default_semana)
    f_mes = st.multiselect("Mes", meses)
    f_tienda = st.multiselect("Tienda", tiendas)
    f_actividad = st.multiselect("Actividad", actividades)
    f_categoria = st.multiselect("Categoría", categorias)
    f_subcat = st.multiselect("Subcategoría", subcats)
    f_modelo = st.multiselect("Modelo", modelos)
    f_colab = st.multiselect("Colaborador", colaboradores)
    f_ocurrencia = st.multiselect("ID empleado / Ocurrencia", ocurrencias)

op = op_all.copy()
co = co_all.copy()
daily = daily_all.copy()

if f_semana:
    if not op.empty:
        op = op[op["Semana ISO"].isin(f_semana)]
    if not daily.empty and "Semana ISO" in daily.columns:
        daily = daily[daily["Semana ISO"].isin(f_semana)]
if f_mes:
    if not op.empty:
        op = op[op["Mes"].isin(f_mes)]
    if not co.empty:
        co = co[co["Mes_Origen"].isin(f_mes)]
    if not daily.empty:
        daily = daily[daily["Mes_Origen"].isin(f_mes)]
if f_tienda:
    if not op.empty:
        op = op[op["Tienda"].isin(f_tienda)]
    if not co.empty:
        co = co[co["Tienda"].isin(f_tienda)]
    if not daily.empty:
        daily = daily[daily["Tienda"].isin(f_tienda)]
if f_actividad and not op.empty:
    op = op[op["Actividad Realizada"].isin(f_actividad)]
if f_categoria and not co.empty:
    co = co[co["Categoria"].isin(f_categoria)]
if f_categoria and not daily.empty:
    daily = daily[daily["Categoria"].isin(f_categoria)]
if f_subcat and not co.empty:
    co = co[co["Subcategoria"].isin(f_subcat)]
if f_subcat and not daily.empty:
    daily = daily[daily["Subcategoria"].isin(f_subcat)]
if f_modelo and not co.empty:
    co = co[co["Modelo"].isin(f_modelo)]
if f_modelo and not daily.empty:
    daily = daily[daily["Modelo"].isin(f_modelo)]
if f_colab and not op.empty:
    op = op[op["Nombre Real"].isin(f_colab)]
if f_ocurrencia and not op.empty:
    op = op[op["Ocurrencia"].isin(f_ocurrencia)]

op = normalizar_operacion(op)
co = normalizar_comercial(co)
daily = normalizar_diario_comercial(daily)

# ==========================================================
# AGREGADOS CENTRALES
# ==========================================================
def days_in_period(opdf):
    if opdf.empty or "Fecha Día" not in opdf.columns:
        return 1
    return max(1, opdf["Fecha Día"].dropna().drop_duplicates().shape[0])

def meta_prod_periodo(opdf):
    return metas["productividad_diaria"] * days_in_period(opdf)

def meta_recorridos_periodo(opdf):
    return (metas["recorridos_semanales"] / 7) * days_in_period(opdf)

def total_dev_system(codf):
    return float(codf["Dev_Pzs"].sum()) if not codf.empty and "Dev_Pzs" in codf else 0

def store_summary(opdf, codf, only_registered=True):
    op_store = pd.DataFrame(columns=["Tienda"])
    if not opdf.empty:
        op_store = opdf.groupby("Tienda", as_index=False).agg(
            Muertos=("Muertos","sum"),
            Cajas=("Cajas","sum"),
            Probador=("Probador","sum"),
            Recoleccion=("Recolección de Muertos","sum"),
            Habilitado=("Habilitado","sum"),
            Ubicado=("Ubicado","sum"),
            Productividad=("Productividad Total","sum"),
            Recorridos=("Recorridos","sum")
        )
    co_store = pd.DataFrame(columns=["Tienda"])
    if not codf.empty:
        co_store = codf.groupby("Tienda", as_index=False).agg(
            Dev_Pzs=("Dev_Pzs","sum"),
            Vta_Pzs=("Piezas Vendidas Validadas","sum"),
            Recuperacion=("Vta_Imp","sum"),
            Costo_Dev=("Costo_Dev","sum")
        )

    base = pd.DataFrame({"Tienda": TIENDAS_OFICIALES}) if not only_registered else pd.DataFrame({"Tienda": sorted(set(op_store.get("Tienda", [])) | set(co_store.get("Tienda", [])))})
    out = base.merge(op_store, on="Tienda", how="left").merge(co_store, on="Tienda", how="left").fillna(0)

    for c in ["Muertos","Cajas","Probador","Recoleccion","Habilitado","Ubicado","Productividad","Recorridos","Dev_Pzs","Vta_Pzs","Recuperacion","Costo_Dev"]:
        if c not in out.columns:
            out[c] = 0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    out["Total Ingresos"] = out["Dev_Pzs"] + out["Muertos"] + out["Cajas"] + out["Probador"]
    out["% Habilitado"] = sdiv(out["Habilitado"], out["Total Ingresos"]) * 100
    out["% Ubicado"] = sdiv(out["Ubicado"], out["Total Ingresos"]) * 100
    out["Conversión %"] = sdiv(out["Vta_Pzs"], out["Dev_Pzs"]) * 100
    out["Recuperación %"] = sdiv(out["Recuperacion"], out["Costo_Dev"]) * 100
    out["Meta Recorridos"] = meta_recorridos_periodo(opdf)
    out["% Recorridos"] = sdiv(out["Recorridos"], out["Meta Recorridos"]) * 100
    out["Estado"] = np.select(
        [
            (out["Productividad"] > 0) & (out["Recuperacion"] > 0),
            (out["Productividad"] > 0) & (out["Recuperacion"] == 0),
            (out["Productividad"] == 0) & (out["Recuperacion"] > 0),
        ],
        [
            "🟢 Productividad + Recuperación",
            "🟡 Productividad sin Recuperación",
            "🟠 Recuperación sin Productividad",
        ],
        default="🔴 Sin registros"
    )
    return out

ss = store_summary(op, co, only_registered=True)
ss_all = store_summary(op, co, only_registered=False)

total_ingresos = ss["Total Ingresos"].sum() if not ss.empty else 0
productividad = ss["Productividad"].sum() if not ss.empty else 0
habilitado = ss["Habilitado"].sum() if not ss.empty else 0
ubicado = ss["Ubicado"].sum() if not ss.empty else 0
recorridos = ss["Recorridos"].sum() if not ss.empty else 0
dev_pzs = ss["Dev_Pzs"].sum() if not ss.empty else 0
vta_pzs = ss["Vta_Pzs"].sum() if not ss.empty else 0
recuperacion = ss["Recuperacion"].sum() if not ss.empty else 0
costo_dev = ss["Costo_Dev"].sum() if not ss.empty else 0

conv_pct = pct(vta_pzs, dev_pzs)
rec_pct = pct(recuperacion, costo_dev)
hab_pct = pct(habilitado, total_ingresos)
ubi_pct = pct(ubicado, total_ingresos)
recorr_pct = pct(recorridos, meta_recorridos_periodo(op) * max(ss["Tienda"].nunique(), 1)) if not ss.empty else 0
prod_pct = pct(productividad, meta_prod_periodo(op) * max(op["Ocurrencia"].nunique() if not op.empty else 1, 1))

score_integral = round(
    min(prod_pct,100)*.40 +
    min(hab_pct,100)*.25 +
    min(ubi_pct,100)*.15 +
    min(conv_pct,100)*.10 +
    min(recorr_pct,100)*.10,
    1
)

# ==========================================================
# SCORE CARDS
# ==========================================================
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total Ingresos", n0(total_ingresos))
c2.metric("% Habilitado", p1(hab_pct))
c3.metric("% Ubicado", p1(ubi_pct))
c4.metric("Recuperación $", money(recuperacion))
c5.metric("Score Integral", f"{score_integral:,.1f}/100")

# ==========================================================
# PESTAÑAS
# ==========================================================
tabs_names = [
    "1. Panel Ejecutivo",
    "2. Macro",
    "3. Conversión",
    "4. Recuperación Económica",
    "5. Productividad por Colaborador",
    "6. Productividad por Actividad",
    "7. Eficiencia Operativa",
    "8. Cumplimiento de Recorridos",
    "9. Indicadores Diarios",
    "10. Top 30 Modelos",
    "11. Análisis por Categoría",
    "12. Análisis por Subcategoría",
    "13. Ranking de Tiendas",
    "14. Ranking de Colaboradores",
    "15. Índice Integral",
    "16. Alertas Inteligentes",
    "17. Configuración de Metas",
    "18. Diagnóstico de Datos",
    "19. Compartir ORION"
]
if not is_admin:
    tabs_names.remove("17. Configuración de Metas")
    tabs_names.remove("18. Diagnóstico de Datos")
tabs = st.tabs(tabs_names)
tab = dict(zip(tabs_names, tabs))

# 1 Panel Ejecutivo
with tab["1. Panel Ejecutivo"]:
    st.subheader("Panel Ejecutivo")
    st.caption("Top y Bottom solo consideran tiendas con registros. Se descartan registros no coherentes mediante agrupación por ID empleado / Ocurrencia.")

    score_df = ss.copy()
    if not score_df.empty:
        score_df["Score"] = (
            score_df["Productividad"].rank(pct=True)*40 +
            score_df["% Habilitado"].rank(pct=True)*25 +
            score_df["% Ubicado"].rank(pct=True)*15 +
            score_df["Conversión %"].rank(pct=True)*10 +
            score_df["% Recorridos"].rank(pct=True)*10
        ).round(1)

    a,b = st.columns(2)
    with a:
        st.write("🏆 Top 2 Tiendas")
        st.dataframe(style_dataframe(score_df.sort_values("Score", ascending=False).head(2)), width="stretch")
    with b:
        st.write("⚠️ Bottom 2 Tiendas")
        st.dataframe(style_dataframe(score_df.sort_values("Score", ascending=True).head(2)), width="stretch")

    valid = op.copy()
    if not valid.empty:
        valid = valid[~valid["Nombre Real"].str.lower().isin(["sin dato", "nan", "0", "-", ""])]
        colab = valid.groupby(["Ocurrencia","Nombre Real"], as_index=False).agg(Productividad=("Productividad Total","sum"))
        colab = colab.sort_values("Productividad", ascending=False)
    else:
        colab = pd.DataFrame()

    a,b = st.columns(2)
    with a:
        st.write("👤 Top 3 Colaboradores")
        st.dataframe(style_dataframe(colab.head(3)), width="stretch")
    with b:
        st.write("👤 Bottom 3 Colaboradores")
        st.dataframe(style_dataframe(colab[colab["Productividad"] > 0].tail(3) if not colab.empty else colab), width="stretch")

    st.plotly_chart(px.bar(score_df.sort_values("Score", ascending=False), x="Tienda", y="Score", color="Estado",
                           title="Score Card por Tienda", color_discrete_sequence=["#3366CC","#FF99FF","#003366","#94A3B8"]),
                    width="stretch")
    export_buttons("panel_ejecutivo", {"score_tiendas": score_df, "colaboradores": colab})

# 2 Macro
with tab["2. Macro"]:
    st.subheader("Macro | Últimas 4 semanas")
    if op_all.empty:
        st.warning("Sin datos operativos.")
    else:
        macro = op_all.groupby("Semana ISO", as_index=False).agg(
            Muertos=("Muertos","sum"),
            Cajas=("Cajas","sum"),
            Probador=("Probador","sum"),
            Habilitado=("Habilitado","sum"),
            Ubicado=("Ubicado","sum")
        )
        sys_week = daily_all.groupby("Semana ISO", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum")) if not daily_all.empty else pd.DataFrame(columns=["Semana ISO","Dev_Pzs"])
        macro = macro.merge(sys_week, on="Semana ISO", how="left").fillna(0)
        macro["Total Ingresos"] = macro["Dev_Pzs"] + macro["Muertos"] + macro["Cajas"] + macro["Probador"]
        macro["% Habilitado"] = sdiv(macro["Habilitado"], macro["Total Ingresos"]) * 100
        macro["% Ubicado"] = sdiv(macro["Ubicado"], macro["Total Ingresos"]) * 100
        macro["Semana ISO"] = macro["Semana ISO"].astype(int)
        macro = macro.sort_values("Semana ISO").tail(4)
        st.dataframe(style_dataframe(macro), width="stretch")
        st.plotly_chart(px.bar(macro, x="Semana ISO", y="Total Ingresos", text_auto=True,
                               title="Total de ingresos por semana", color_discrete_sequence=["#3366CC"]),
                        width="stretch")
        st.plotly_chart(px.line(macro, x="Semana ISO", y=["% Habilitado","% Ubicado"], markers=True,
                                title="% Habilitado vs % Ubicado", color_discrete_sequence=["#3366CC","#FF99FF"]),
                        width="stretch")

# 3 Conversión
with tab["3. Conversión"]:
    st.subheader("Conversión | Dev_Pzs a Venta")
    c1,c2,c3 = st.columns(3)
    c1.metric("Dev_Pzs", n0(dev_pzs))
    c2.metric("Vta_Pzs validada", n0(vta_pzs))
    c3.metric("Conversión", p1(conv_pct))
    conv = ss[["Tienda","Dev_Pzs","Vta_Pzs","Conversión %","Estado"]].copy()
    st.dataframe(style_dataframe(conv.sort_values("Conversión %", ascending=False)), width="stretch")
    st.plotly_chart(px.bar(conv.sort_values("Conversión %", ascending=False), x="Tienda", y="Conversión %",
                           color="Estado", color_discrete_sequence=["#3366CC","#FF99FF","#003366","#94A3B8"],
                           title="Conversión por tienda"), width="stretch")

# 4 Recuperación Económica
with tab["4. Recuperación Económica"]:
    st.subheader("Recuperación Económica")
    c1,c2,c3 = st.columns(3)
    c1.metric("Valor Recuperado", money(recuperacion))
    c2.metric("Costo Dev", money(costo_dev))
    c3.metric("Valor Pendiente", money(costo_dev - recuperacion))
    eco = ss[["Tienda","Recuperacion","Costo_Dev","Recuperación %","Estado"]].copy()
    eco["Valor Pendiente"] = eco["Costo_Dev"] - eco["Recuperacion"]
    st.dataframe(style_dataframe(eco.sort_values("Recuperacion", ascending=False)), width="stretch")
    st.plotly_chart(px.bar(eco.sort_values("Recuperacion", ascending=False), x="Tienda", y="Recuperacion",
                           color="Estado", color_discrete_sequence=["#3366CC","#FF99FF","#003366","#94A3B8"],
                           title="Recuperación $ por tienda"), width="stretch")

# 5 Productividad Colaborador
with tab["5. Productividad por Colaborador"]:
    st.subheader("Ranking de Productividad por Colaborador")
    if op.empty:
        st.warning("Sin datos operativos.")
    else:
        base_colab = op.groupby(["Ocurrencia","Nombre Real","Tienda"], as_index=False).agg(
            Recoleccion=("Recolección de Muertos","sum"),
            Habilitado=("Habilitado","sum"),
            Ubicado=("Ubicado","sum"),
            Productividad=("Productividad Total","sum")
        )
        area = op.groupby(["Ocurrencia","Nombre Real","Tienda","Área"], as_index=False).agg(Piezas=("Productividad Total","sum"))
        if not area.empty:
            idx = area.groupby(["Ocurrencia","Nombre Real","Tienda"])["Piezas"].idxmax()
            area_max = area.loc[idx].rename(columns={"Área":"Área mayor productividad","Piezas":"Piezas área mayor"})
            base_colab = base_colab.merge(
                area_max[["Ocurrencia","Nombre Real","Tienda","Área mayor productividad","Piezas área mayor"]],
                on=["Ocurrencia","Nombre Real","Tienda"],
                how="left"
            )
        base_colab["Meta"] = meta_prod_periodo(op)
        base_colab["Cumplimiento %"] = sdiv(base_colab["Productividad"], base_colab["Meta"]) * 100
        base_colab["Ranking"] = base_colab["Productividad"].rank(method="dense", ascending=False).astype(int)
        base_colab = base_colab.sort_values("Ranking")
        st.dataframe(style_dataframe(base_colab), width="stretch")
        st.plotly_chart(px.bar(base_colab.head(30), x="Nombre Real", y="Productividad", color="Tienda",
                               color_discrete_sequence=["#3366CC","#FF99FF","#003366"],
                               title="Top colaboradores por productividad"), width="stretch")

# 6 Productividad Actividad
with tab["6. Productividad por Actividad"]:
    st.subheader("Productividad por Actividad")
    if op.empty:
        st.warning("Sin operación.")
    else:
        act_df = pd.DataFrame({
            "Actividad": ["Recolección de muertos", "Habilitado", "Ubicado"],
            "Piezas": [op["Recolección de Muertos"].sum(), op["Habilitado"].sum(), op["Ubicado"].sum()]
        })
        st.write("Por actividad")
        st.dataframe(style_dataframe(act_df), width="stretch")
        st.plotly_chart(px.bar(act_df, x="Actividad", y="Piezas", text_auto=True,
                               color="Actividad", color_discrete_sequence=["#3366CC","#FF99FF","#003366"]),
                        width="stretch")

        ingresos_df = pd.DataFrame({
            "Concepto": ["Sistema Dev_Pzs", "Piso de venta", "Recolección Cajas", "Recolección Probador"],
            "Piezas": [total_dev_system(co), op["Muertos"].sum(), op["Cajas"].sum(), op["Probador"].sum()]
        })
        st.write("Por ingresos")
        st.dataframe(style_dataframe(ingresos_df), width="stretch")
        st.plotly_chart(px.bar(ingresos_df, x="Concepto", y="Piezas", text_auto=True,
                               color="Concepto", color_discrete_sequence=["#3366CC","#FF99FF","#003366","#94A3B8"]),
                        width="stretch")

# 7 Eficiencia Operativa
with tab["7. Eficiencia Operativa"]:
    st.subheader("Eficiencia Operativa | Solo tiendas con registro")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Ingresos", n0(total_ingresos))
    c2.metric("Habilitado", n0(habilitado))
    c3.metric("Ubicado", n0(ubicado))
    c4.metric("% Habilitado", p1(hab_pct))
    c5.metric("% Ubicado", p1(ubi_pct))
    ef = ss.copy()
    ef["Ranking"] = ef["% Ubicado"].rank(method="dense", ascending=False).astype(int)
    ef = ef[["Ranking","Tienda","Total Ingresos","Habilitado","Ubicado","% Habilitado","% Ubicado","Estado"]].sort_values("Ranking")
    st.dataframe(style_dataframe(ef), width="stretch")

# 8 Cumplimiento Recorridos
with tab["8. Cumplimiento de Recorridos"]:
    st.subheader("Cumplimiento de Recorridos")
    rec = ss[["Tienda","Estado","Recorridos","Meta Recorridos","% Recorridos"]].copy()
    rec["Estatus"] = np.where(rec["% Recorridos"] >= 100, "🟢 Cumple", np.where(rec["% Recorridos"] >= 80, "🟡 Atención", "🔴 Bajo"))
    rec["Ranking"] = rec["% Recorridos"].rank(method="dense", ascending=False).astype(int)
    rec = rec[["Ranking","Tienda","Estado","Recorridos","Meta Recorridos","% Recorridos","Estatus"]].sort_values("Ranking")
    st.dataframe(style_dataframe(rec), width="stretch")
    fig = px.bar(rec, x="Tienda", y="Recorridos", color="Estatus", title="Recorridos vs Meta",
                 color_discrete_sequence=["#3366CC","#FF99FF","#003366"])
    fig.add_scatter(x=rec["Tienda"], y=rec["Meta Recorridos"], mode="lines+markers", name="Meta", line=dict(color="#FF99FF", width=4))
    st.plotly_chart(fig, width="stretch")

# 9 Indicadores Diarios
with tab["9. Indicadores Diarios"]:
    st.subheader("Indicadores Diarios")
    if op.empty:
        st.warning("Sin datos.")
    else:
        diaria = op.groupby(["Fecha Día","Tienda","Ocurrencia","Nombre Real"], as_index=False).agg(
            Recoleccion=("Recolección de Muertos","sum"),
            Habilitado=("Habilitado","sum"),
            Ubicado=("Ubicado","sum"),
            Recorridos=("Recorridos","sum")
        )
        sys_day = daily.groupby(["Fecha Día","Tienda"], as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum")) if not daily.empty else pd.DataFrame(columns=["Fecha Día","Tienda","Dev_Pzs"])
        diaria = diaria.merge(sys_day, on=["Fecha Día","Tienda"], how="left").fillna(0)
        diaria["Total Ingresos"] = diaria["Dev_Pzs"] + diaria["Recoleccion"]
        diaria["% Habilitado"] = sdiv(diaria["Habilitado"], diaria["Total Ingresos"]) * 100
        diaria["% Ubicado"] = sdiv(diaria["Ubicado"], diaria["Total Ingresos"]) * 100
        diaria["Meta"] = metas["productividad_diaria"]
        diaria["Productividad"] = diaria["Recoleccion"] + diaria["Habilitado"] + diaria["Ubicado"]
        diaria["Cumplimiento %"] = sdiv(diaria["Productividad"], diaria["Meta"]) * 100
        diaria = diaria.rename(columns={"Ocurrencia":"ID de empleado"})
        st.dataframe(style_dataframe(diaria), width="stretch")

# 10 Top Modelos
with tab["10. Top 30 Modelos"]:
    st.subheader("Top 30 Modelos")
    if co.empty:
        st.warning("Sin información comercial.")
    else:
        top = co.groupby(["Modelo","Categoria","Subcategoria"], as_index=False).agg(
            Dev_Pzs=("Dev_Pzs","sum"),
            Vta_Pzs=("Piezas Vendidas Validadas","sum"),
            Recuperacion_Dinero=("Vta_Imp","sum"),
            Costo_Dev=("Costo_Dev","sum")
        )
        top["Recuperación %"] = sdiv(top["Recuperacion_Dinero"], top["Costo_Dev"]) * 100
        top["Valor Pendiente"] = top["Costo_Dev"] - top["Recuperacion_Dinero"]
        criterio = st.selectbox("Ranking", ["Mayor recuperación económica","Mayor recuperación %","Mayor venta","Mayor pendiente"])
        col = {"Mayor recuperación económica":"Recuperacion_Dinero","Mayor recuperación %":"Recuperación %","Mayor venta":"Vta_Pzs","Mayor pendiente":"Valor Pendiente"}[criterio]
        top = top.sort_values(col, ascending=False).head(30)
        st.dataframe(style_dataframe(top), width="stretch")
        st.plotly_chart(px.bar(top, x="Modelo", y=col, color="Categoria",
                               color_discrete_sequence=["#3366CC","#FF99FF","#003366"], title=criterio),
                        width="stretch")

# 11 Categoría
with tab["11. Análisis por Categoría"]:
    st.subheader("Análisis por Categoría")
    if co.empty:
        st.warning("Sin información comercial.")
    else:
        cat = co.groupby("Categoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum"))
        cat["Conversión %"] = sdiv(cat["Vta_Pzs"], cat["Dev_Pzs"]) * 100
        st.dataframe(style_dataframe(cat.sort_values("Recuperacion", ascending=False)), width="stretch")
        st.plotly_chart(px.bar(cat.sort_values("Recuperacion", ascending=False), x="Categoria", y="Recuperacion",
                               color_discrete_sequence=["#3366CC"]), width="stretch")

# 12 Subcategoría
with tab["12. Análisis por Subcategoría"]:
    st.subheader("Análisis por Subcategoría")
    if co.empty:
        st.warning("Sin información comercial.")
    else:
        sub = co.groupby("Subcategoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum"))
        sub["Conversión %"] = sdiv(sub["Vta_Pzs"], sub["Dev_Pzs"]) * 100
        st.dataframe(style_dataframe(sub.sort_values("Recuperacion", ascending=False)), width="stretch")
        st.plotly_chart(px.bar(sub.sort_values("Recuperacion", ascending=False).head(30), x="Subcategoria", y="Recuperacion",
                               color_discrete_sequence=["#FF99FF"]), width="stretch")

# 13 Ranking Tiendas
with tab["13. Ranking de Tiendas"]:
    st.subheader("Ranking de Tiendas")
    rank = ss_all.copy()
    rank["Score"] = (
        rank["Productividad"].rank(pct=True)*40 +
        rank["% Habilitado"].rank(pct=True)*25 +
        rank["% Ubicado"].rank(pct=True)*15 +
        rank["Conversión %"].rank(pct=True)*10 +
        rank["% Recorridos"].rank(pct=True)*10
    ).round(1)
    rank["Ranking"] = rank["Score"].rank(method="dense", ascending=False).astype(int)
    rank = rank[["Ranking","Tienda","Dev_Pzs","Vta_Pzs","Recuperacion","Conversión %","Productividad","Recorridos","Score","Estado"]].sort_values("Ranking")
    st.dataframe(style_dataframe(rank), width="stretch")

# 14 Ranking Colaboradores
with tab["14. Ranking de Colaboradores"]:
    st.subheader("Ranking de Colaboradores")
    if op.empty:
        st.warning("Sin datos.")
    else:
        rc = op.groupby(["Ocurrencia","Nombre Real"], as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum"))
        rc["Score"] = (rc["Productividad"].rank(pct=True)*85 + rc["Recorridos"].rank(pct=True)*15).round(1)
        rc["Ranking"] = rc["Score"].rank(method="dense", ascending=False).astype(int)
        st.dataframe(style_dataframe(rc.sort_values("Ranking")), width="stretch")

# 15 Índice Integral
with tab["15. Índice Integral"]:
    st.subheader("Índice Integral ORION")
    st.metric("Score Integral", f"{score_integral:,.1f}/100")
    st.progress(min(score_integral/100, 1.0))
    score_break = pd.DataFrame({
        "Componente": ["Productividad", "Habilitado", "Ubicado", "Conversión", "Recorridos"],
        "Peso": ["40%", "25%", "15%", "10%", "10%"],
        "Cumplimiento": [prod_pct, hab_pct, ubi_pct, conv_pct, recorr_pct]
    })
    st.dataframe(style_dataframe(score_break), width="stretch")

# 16 Alertas
with tab["16. Alertas Inteligentes"]:
    st.subheader("Alertas Inteligentes")
    alerts = []
    if conv_pct < metas["conversion"]:
        alerts.append(["Conversión", "Alta", f"Conversión menor a meta: {p1(conv_pct)} vs {p1(metas['conversion'])}"])
    if rec_pct < metas["recuperacion"]:
        alerts.append(["Recuperación", "Alta", f"Recuperación menor a meta: {p1(rec_pct)} vs {p1(metas['recuperacion'])}"])
    if prod_pct < 80:
        alerts.append(["Productividad", "Media", f"Productividad debajo de 80%: {p1(prod_pct)}"])
    if recorr_pct < 80:
        alerts.append(["Recorridos", "Media", f"Recorridos debajo de 80%: {p1(recorr_pct)}"])

    for _, r in ss_all.iterrows():
        if r["Estado"] == "🔴 Sin registros":
            alerts.append(["Tienda sin registros", "Alta", f"{r['Tienda']} no tiene registros."])
        if r["Estado"] == "🟡 Productividad sin Recuperación":
            alerts.append(["Productividad sin recuperación", "Media", f"{r['Tienda']} tiene productividad sin recuperación."])

    alert_df = pd.DataFrame(alerts, columns=["Tipo","Prioridad","Alerta"])
    if alert_df.empty:
        st.success("Sin alertas críticas.")
    else:
        st.dataframe(style_dataframe(alert_df), width="stretch")

# 17 Configuración
if "17. Configuración de Metas" in tab:
    with tab["17. Configuración de Metas"]:
        st.subheader("⚙️ Configuración de Metas")
        cols = st.columns(3)
        nuevos = {}
        for i, (k, v) in enumerate(metas.items()):
            with cols[i % 3]:
                nuevos[k] = st.number_input(k, value=float(v), step=1.0)
        if st.button("Guardar metas"):
            for k, v in nuevos.items():
                if float(v) != float(metas[k]):
                    update_meta(k, v)
            st.success("Metas actualizadas.")
            st.rerun()

        st.write("Corrección de nombres por ID empleado / Ocurrencia")
        if not op_all.empty:
            empleados = op_all.groupby("Ocurrencia", as_index=False).agg(Nombre_actual=("Nombre","first"))
            edit = st.data_editor(empleados, width="stretch", num_rows="fixed")
            if st.button("Guardar nombres corregidos"):
                mapping = dict(zip(edit["Ocurrencia"].astype(str), edit["Nombre_actual"].astype(str)))
                save_nombre_map(mapping)
                st.success("Nombres actualizados.")
                st.rerun()

        st.write("Historial de metas")
        st.dataframe(style_dataframe(get_historial_metas()), width="stretch")

# 18 Diagnóstico
if "18. Diagnóstico de Datos" in tab:
    with tab["18. Diagnóstico de Datos"]:
        st.subheader("Diagnóstico de Datos")
        try:
            diag = json.loads(get_estado("diagnostico", "{}"))
        except Exception:
            diag = {}
        st.json(diag)
        c1,c2,c3 = st.columns(3)
        c1.metric("Registros operación", n0(len(op_all)))
        c2.metric("Registros comercial", n0(len(co_all)))
        c3.metric("Registros comercial diario", n0(len(daily_all)))
        if not op_all.empty:
            st.write("Valores nulos operación")
            st.dataframe(op_all.isna().sum().reset_index().rename(columns={"index":"Columna",0:"Nulos"}), width="stretch")

# 19 Compartir
with tab["19. Compartir ORION"]:
    st.subheader("Compartir ORION")
    url = st.text_input("URL pública de ORION", value="https://operaciones-ropa.streamlit.app")
    st.code(url)
    st.write(f"Fecha de actualización: {ultima}")
    st.write(f"Archivo cargado: {archivo_cargado}")
    st.info("Una vez cargado el archivo por administrador, los usuarios Consulta pueden visualizar la información sin cargar Excel.")

st.markdown("""
<div class="confidencial">
<b>CONFIDENCIAL</b><br>
La información contenida en esta plataforma es propiedad de Price Shoes y está destinada exclusivamente para uso interno de Operaciones Ropa.
Queda prohibida su reproducción, distribución o divulgación sin autorización expresa de la Dirección correspondiente.<br>
© Price Shoes | Operaciones Ropa
</div>
""", unsafe_allow_html=True)
