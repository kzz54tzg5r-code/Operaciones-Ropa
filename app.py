
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import json
import re
from pathlib import Path
from io import BytesIO
from datetime import datetime

# ==========================================================
# Recuperación Cambios y Muertos LIMPIO
# PRICE SHOES | OPERACIONES ROPA
# Plataforma Indicadores de Recuperación de Mercancía
# ==========================================================

st.set_page_config(page_title="Recuperación Cambios y Muertos", page_icon="🚀", layout="wide")

DATA_DIR = Path("orion_data")
DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR = Path("assets")
LOGO_PATH = ASSETS_DIR / "logo.png"

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
    "acondicionado_ingresos": 85.0,
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
:root{--magenta:#EC007C;--blue:#0047B3;--blue-dark:#14172F;--green:#00A651;--orange:#F39800;--purple:#6F35B5;--navy:#2F4A8A;--border:#E5E7EB;--muted:#6B7280;}
html,body,.stApp{background:#FFFFFF!important;color:var(--blue-dark);}
.block-container{padding-top:.6rem;padding-left:1.8rem;padding-right:1.8rem;padding-bottom:2rem;max-width:1680px;}
section[data-testid="stSidebar"]{background:#FAFAFC;border-right:1px solid #ECEEF3;}
.orion-top{background:#FFFFFF;padding:12px 4px 14px 4px;}
.orion-top-inner{display:grid;grid-template-columns:140px minmax(470px,1fr) 720px;gap:16px;align-items:center;}
.orion-logo{width:132px;height:82px;display:flex;align-items:center;justify-content:center;overflow:hidden;}
.orion-logo-fallback{color:#0D4A9C;font-size:27px;font-weight:950;line-height:.9;text-align:center;border:2px solid #0D4A9C;border-radius:50%;padding:12px 8px;background:#F6FBFF;}
.orion-title-main{font-size:36px;font-weight:950;color:var(--blue-dark);margin:0;line-height:1.02;white-space:nowrap;letter-spacing:-.02em;}
.orion-sub-main{font-size:18px;color:var(--muted);font-weight:600;margin-top:6px;white-space:nowrap;}
.orion-top-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
.orion-mini-kpi{display:flex;align-items:center;gap:12px;min-width:0;}
.orion-mini-icon{width:56px;height:56px;min-width:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:900;}
.icon-rec{background:#FCE2EF;color:var(--magenta)}.icon-cam{background:#E8EEF9;color:var(--blue)}.icon-mue{background:#EFE8FB;color:var(--purple)}
.orion-mini-label{font-size:13px;color:var(--blue-dark);font-weight:900;line-height:1.1}.orion-mini-value{font-size:22px;font-weight:950;margin-top:3px;line-height:1.05}.value-rec{color:var(--magenta)}.value-cam{color:var(--blue)}.value-mue{color:var(--purple)}
.orion-pink-bar{background:var(--magenta);color:white;padding:16px 26px;margin-left:-1.8rem;margin-right:-1.8rem;margin-bottom:14px;font-size:28px;line-height:1;font-weight:950;}
.stTabs [data-baseweb="tab-list"]{gap:0;background:#FFFFFF;border-bottom:1px solid #D7DAE2;padding:0;overflow-x:auto;}
.stTabs [data-baseweb="tab"]{min-width:190px;height:58px;padding:0 16px;color:#2E3248;font-weight:850;border-bottom:4px solid transparent;}
.stTabs [aria-selected="true"]{color:var(--magenta)!important;border-bottom:4px solid var(--magenta);background:#FFFFFF!important;}
h1,h2,h3{color:var(--blue-dark)!important;letter-spacing:-.01em;}h2{font-weight:950!important;}
div[data-testid="stDateInput"]{max-width:330px!important;}div[data-testid="stDateInput"] input{height:46px!important;border-radius:6px!important;}
button[kind="primary"]{background:var(--magenta)!important;border:none!important;color:white!important;font-weight:900!important;}
.boceto-card-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0 14px 0;}
.boceto-kpi-card{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;min-height:120px;padding:20px;display:flex;align-items:center;gap:20px;box-shadow:0 1px 8px rgba(17,24,39,.04);}
.boceto-big-icon{width:64px;height:64px;min-width:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:32px;font-weight:950;}
.big-magenta{background:var(--magenta)}.big-blue{background:var(--blue)}.big-orange{background:var(--orange)}.big-green{background:var(--green)}
.boceto-card-title{color:var(--blue-dark);font-size:14px;font-weight:900;margin-bottom:9px;line-height:1.15}.boceto-card-value{font-size:24px;font-weight:950;margin-bottom:10px}.boceto-card-foot{color:var(--blue-dark);font-size:13px;}
.wow-title{font-size:22px;font-weight:950;color:#2F4A8A;margin:18px 0 12px 0;border-left:7px solid var(--magenta);padding-left:14px;}
.wow-row{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin:12px 0 22px 0;}
.wow-card{border:1px solid #D6DAE3;border-radius:8px;background:#F8F9FB;overflow:hidden;}
.wow-head{background:#2F4A8A;color:white;text-align:center;font-weight:950;font-size:18px;padding:12px;}
.wow-body{padding:14px 18px}.wow-line{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;align-items:center;border-bottom:1px solid #E5E7EB;padding:10px 0}.wow-line:last-child{border-bottom:0}
.wow-lbl{font-size:13px;font-weight:900;color:#666}.wow-num{font-size:21px;font-weight:950;color:#2F4A8A;text-align:right}.wow-var{font-size:13px;font-weight:900;text-align:right}.wow-up{color:#00A651}.wow-down{color:#EC004C}.wow-flat{color:#777}
.boceto-section{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;padding:12px;box-shadow:0 1px 8px rgba(17,24,39,.04);margin-bottom:14px;}
.boceto-section h3{font-size:18px!important;margin:0 0 10px 0!important;color:#14172F!important;}
div[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:8px;overflow:hidden;}
@media(max-width:1200px){.orion-top-inner{grid-template-columns:1fr}.orion-top-kpis{grid-template-columns:1fr}.boceto-card-row{grid-template-columns:1fr}.wow-row{grid-template-columns:1fr}.orion-title-main{white-space:normal;}}
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
    percent_cols = [c for c in df.columns if "%" in str(c) or "cumplimiento" in str(c).lower() or "acondicionado" in str(c).lower()]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    fmt = {c: ("{:,.1f}%" if c in percent_cols else "{:,.0f}") for c in numeric_cols}
    return (df.style
        .set_table_styles([
            {"selector":"th","props":[("background-color","#2F4A8A"),("color","white"),("font-weight","900"),("border","1px solid #2F4A8A"),("text-align","center")]},
            {"selector":"td","props":[("border","1px solid #E5E7EB"),("background-color","#FFFFFF"),("color","#14172F"),("text-align","center")]},
            {"selector":"tbody tr:nth-child(even) td","props":[("background-color","#FCFCFD")]}
        ]).format(fmt))

def excel_export(sheets):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return bio.getvalue()


def pdf_dia_anterior_bytes(resumen_general, detalle, fecha_texto=""):
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = [Paragraph("Recuperación Cambios y Muertos", styles["Title"]), Paragraph(f"Operaciones Ropa | Día anterior / Pendiente {fecha_texto}", styles["Normal"]), Spacer(1, 12)]
    def prep(df, max_rows=28):
        d = df.copy().head(max_rows)
        for col in d.columns:
            if pd.api.types.is_numeric_dtype(d[col]):
                if "%" in str(col): d[col] = d[col].apply(lambda x: f"{x:,.1f}%")
                else: d[col] = d[col].apply(lambda x: f"{x:,.0f}")
        return [list(d.columns)] + d.astype(str).values.tolist()
    for title, df in [("Resumen general", resumen_general), ("Detalle por tienda", detalle)]:
        story.append(Paragraph(title, styles["Heading2"]))
        table = Table(prep(df), repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2F4A8A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#D1D5DB")),("ALIGN",(0,0),(-1,-1),"CENTER")]))
        story += [table, Spacer(1, 12)]
    doc.build(story); bio.seek(0); return bio.getvalue()

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

    for _hora_col in ["Hora Inicio", "Hora Fin"]:
        if _hora_col in df.columns:
            df[_hora_col] = df[_hora_col].apply(lambda x: "" if pd.isna(x) else str(x))


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
    df["Acondicionado"] = np.where(act.str.contains("acondicionado|habilitar", regex=True), df["Número de Piezas"], 0)
    df["Ubicado"] = np.where(act.str.contains("ubicado|ubicar", regex=True), df["Número de Piezas"], 0)

    df["Recolección de Muertos"] = df["Muertos"] + df["Cajas"] + df["Probador"]
    df["Ingresos Operativos"] = df["Recolección de Muertos"]
    df["Productividad Total"] = df["Recolección de Muertos"] + df["Acondicionado"] + df["Ubicado"]

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


def preparar_para_parquet(df):
    """Convierte columnas mixtas a tipos seguros para evitar errores de PyArrow."""
    if df is None or df.empty:
        return df
    df = df.copy()

    for col in df.columns:
        # Columnas de hora o columnas tipo objeto con valores mixtos se guardan como texto
        if (
            str(col).lower() in ["hora inicio", "hora fin", "hora_inicio", "hora_fin"]
            or df[col].dtype == "object"
        ):
            df[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(x))

    return df


def guardar_datos(op, co, daily, diag, filename):
    op = preparar_para_parquet(op)
    co = preparar_para_parquet(co)
    daily = preparar_para_parquet(daily)

    if op is not None and not op.empty:
        op.to_parquet(OPERACION_FILE, index=False)
    if co is not None and not co.empty:
        co.to_parquet(COMERCIAL_FILE, index=False)
    if daily is not None and not daily.empty:
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

    num_cols = ["Número de Piezas", "Recorridos", "Muertos", "Cajas", "Probador", "Acondicionado", "Ubicado"]
    for c in num_cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Recorridos solo cuenta valor 1
    df["Recorridos"] = np.where(df["Recorridos"] == 1, 1, 0)

    df["Recolección de Muertos"] = df["Muertos"] + df["Cajas"] + df["Probador"]
    df["Ingresos Operativos"] = df["Recolección de Muertos"]
    df["Productividad Total"] = df["Recolección de Muertos"] + df["Acondicionado"] + df["Ubicado"]

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




def render_orion_header():
    logo_html_local = """
    <div class="orion-logo">
        <div class="orion-logo-fallback">Price<br>Shoes</div>
    </div>
    """
    if LOGO_PATH.exists():
        import base64
        logo_b64_local = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        logo_html_local = f"""
        <div class="orion-logo">
            <img src="data:image/png;base64,{logo_b64_local}" style="max-width:132px;max-height:82px;">
        </div>
        """
    st.markdown(f"""
    <div class="orion-top">
        <div class="orion-top-inner">
            {logo_html_local}
            <div>
                <div class="orion-title-main">Recuperación Cambios y Muertos</div>
                <div class="orion-sub-main">Matriz de Operaciones</div>
            </div>
            <div class="orion-top-kpis">
                <div class="orion-mini-kpi"><div class="orion-mini-icon icon-rec">↻</div><div><div class="orion-mini-label">Recuperación</div><div class="orion-mini-value value-rec">Operaciones</div></div></div>
                <div class="orion-mini-kpi"><div class="orion-mini-icon icon-cam">↔</div><div><div class="orion-mini-label">Cambios</div><div class="orion-mini-value value-cam">Ropa</div></div></div>
                <div class="orion-mini-kpi"><div class="orion-mini-icon icon-mue">♟</div><div><div class="orion-mini-label">Muertos</div><div class="orion-mini-value value-mue">Compañía</div></div></div>
            </div>
        </div>
    </div>
    <div class="orion-pink-bar">Operaciones Ropa</div>
    """, unsafe_allow_html=True)

render_orion_header()

# ==========================================================
# SIDEBAR ACCESO / CARGA
# ==========================================================
with st.sidebar:
    st.header("🔐 Acceso")
    rol = st.radio("Rol", ["Consulta", "Gerente", "Administrador"], horizontal=True)

    is_admin = False
    is_manager = False
    can_upload = False
    can_config = False
    can_edit_names = False
    can_view_diagnostics = False

    if rol == "Administrador":
        clave = st.text_input("Clave administrador", type="password")
        is_admin = clave == st.secrets.get("ADMIN_PASSWORD", "orion_admin")
        if is_admin:
            can_upload = True
            can_config = True
            can_edit_names = True
            can_view_diagnostics = True
        elif clave:
            st.warning("Clave incorrecta.")

    elif rol == "Gerente":
        clave_gerente = st.text_input("Clave gerente", type="password")
        is_manager = clave_gerente == st.secrets.get("GERENTE_PASSWORD", "orion_gerente")
        if is_manager:
            can_edit_names = True
            can_view_diagnostics = True
        elif clave_gerente:
            st.warning("Clave de gerente incorrecta.")

    else:
        st.caption("Modo consulta: solo visualización.")

    st.caption(f"Rol activo: {rol}")
    if is_admin:
        st.success("Permisos: carga, metas, nombres y diagnóstico.")
    elif is_manager:
        st.success("Permisos: consulta, corrección de nombres y diagnóstico.")
    elif rol == "Consulta":
        st.info("Permisos: solo consulta.")

    st.divider()
    st.header("📂 Fuente de datos")
    if can_upload:
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
        st.caption("Este rol no puede cargar ni reemplazar archivos.")

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


def asegurar_acondicionado_alias(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if "Acondicionado" not in df.columns and "Acondicionado" in df.columns:
        df["Acondicionado"] = pd.to_numeric(df["Acondicionado"], errors="coerce").fillna(0)
    if "Acondicionado" not in df.columns and "Acondicionado" in df.columns:
        df["Acondicionado"] = pd.to_numeric(df["Acondicionado"], errors="coerce").fillna(0)
    return df

op_all = asegurar_acondicionado_alias(op_all)
op = asegurar_acondicionado_alias(op)

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
            Acondicionado=("Acondicionado","sum"),
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

    for c in ["Muertos","Cajas","Probador","Recoleccion","Acondicionado","Ubicado","Productividad","Recorridos","Dev_Pzs","Vta_Pzs","Recuperación $","Costo_Dev"]:
        if c not in out.columns:
            out[c] = 0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    out["Piezas Ingresadas"] = out["Dev_Pzs"] + out["Muertos"] + out["Cajas"] + out["Probador"]
    out["% Acondicionado"] = sdiv(out["Acondicionado"], out["Piezas Ingresadas"]) * 100
    out["% Ubicado"] = sdiv(out["Ubicado"], out["Piezas Ingresadas"]) * 100
    out["Conversión %"] = sdiv(out["Vta_Pzs"], out["Dev_Pzs"]) * 100
    out["Recuperación %"] = sdiv(out["Recuperación $"], out["Costo_Dev"]) * 100
    out["Meta Recorridos"] = meta_recorridos_periodo(opdf)
    out["% Recorridos"] = sdiv(out["Recorridos"], out["Meta Recorridos"]) * 100
    out["Estado"] = np.select(
        [
            (out["Productividad"] > 0) & (out["Recuperación $"] > 0),
            (out["Productividad"] > 0) & (out["Recuperación $"] == 0),
            (out["Productividad"] == 0) & (out["Recuperación $"] > 0),
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

total_ingresos = ss["Piezas Ingresadas"].sum() if not ss.empty else 0
productividad = ss["Productividad"].sum() if not ss.empty else 0
acondicionado = ss["Acondicionado"].sum() if not ss.empty else 0
ubicado = ss["Ubicado"].sum() if not ss.empty else 0
recorridos = ss["Recorridos"].sum() if not ss.empty else 0
dev_pzs = ss["Dev_Pzs"].sum() if not ss.empty else 0
vta_pzs = ss["Vta_Pzs"].sum() if not ss.empty else 0
recuperacion = ss["Recuperacion"].sum() if not ss.empty else 0
costo_dev = ss["Costo_Dev"].sum() if not ss.empty else 0

conv_pct = pct(vta_pzs, dev_pzs)
rec_pct = pct(recuperacion, costo_dev)
hab_pct = pct(acondicionado, total_ingresos)
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
def render_wow_cards(op_source):
    if op_source is None or op_source.empty or "Semana ISO" not in op_source.columns:
        return
    tmp = asegurar_acondicionado_alias(op_source)
    sem = tmp.groupby("Semana ISO", as_index=False).agg(Piezas=("Productividad Total","sum"), Acondicionado=("Acondicionado","sum"), Ubicado=("Ubicado","sum"), Recorridos=("Recorridos","sum")).sort_values("Semana ISO").tail(4)
    if sem.empty:
        return
    html = '<div class="wow-title">📊 Resumen Ejecutivo WoW (Dinámico)</div><div class="wow-row">'
    prev = None
    for _, r in sem.iterrows():
        def v(col):
            if prev is None or float(prev[col]) == 0:
                return '<span class="wow-flat">—</span>'
            pctv = (float(r[col])-float(prev[col]))/float(prev[col])*100
            cls = "wow-up" if pctv >= 0 else "wow-down"
            arrow = "▲" if pctv >= 0 else "▼"
            return f'<span class="{cls}">{arrow} {abs(pctv):.1f}%</span>'
        html += f'<div class="wow-card"><div class="wow-head">Sem {int(r["Semana ISO"])}</div><div class="wow-body">'
        html += f'<div class="wow-line"><div class="wow-lbl">INGRESOS</div><div class="wow-num">{float(r["Piezas"]):,.0f}</div><div class="wow-var">{v("Piezas")}</div></div>'
        html += f'<div class="wow-line"><div class="wow-lbl">ACONDICIONADO</div><div class="wow-num">{float(r["Acondicionado"]):,.0f}</div><div class="wow-var">{v("Acondicionado")}</div></div>'
        html += f'<div class="wow-line"><div class="wow-lbl">UBICADO</div><div class="wow-num">{float(r["Ubicado"]):,.0f}</div><div class="wow-var">{v("Ubicado")}</div></div>'
        html += f'<div class="wow-line"><div class="wow-lbl">RECORRIDOS</div><div class="wow-num">{float(r["Recorridos"]):,.0f}</div><div class="wow-var">—</div></div>'
        html += '</div></div>'
        prev = r
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

render_wow_cards(op_all)

# ==========================================================
# PESTAÑAS
# ==========================================================
tabs_names = [
    "0. Día Anterior / Pendiente",
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
    "17. Corrección de Nombres",
    "18. Configuración de Metas",
    "19. Diagnóstico de Datos",
    "20. Compartir ORION"
]
if not can_config and "18. Configuración de Metas" in tabs_names:
    tabs_names.remove("18. Configuración de Metas")
if not can_view_diagnostics and "19. Diagnóstico de Datos" in tabs_names:
    tabs_names.remove("19. Diagnóstico de Datos")
tabs = st.tabs(tabs_names)
tab = dict(zip(tabs_names, tabs))


# 0 Día Anterior / Pendiente
with tab["0. Día Anterior / Pendiente"]:
    st.subheader("Día Anterior | Ingresos y Pendiente por Procesar")
    st.caption("Muestra únicamente tiendas con productividad registrada. Formato: piezas con coma, pesos con $, porcentajes con %.")

    if op_all.empty:
        st.warning("Sin datos operativos.")
    else:
        temp_op = op_all.copy()
        temp_daily = daily_all.copy()

        fechas_validas = pd.to_datetime(temp_op["Fecha Día"], errors="coerce").dropna()

        if fechas_validas.empty:
            st.warning("No hay fechas válidas para calcular día anterior.")
        else:
            ultima_fecha = fechas_validas.max().date()
            dia_anterior = ultima_fecha - pd.Timedelta(days=1)

            fecha_col, btn_col, spacer_col = st.columns([2.2, 1.0, 2.8])
            with fecha_col:
                fecha_consulta = st.date_input(
                    "Fecha del día anterior:",
                    value=dia_anterior,
                    help="Por default se toma el día anterior al último día con registro en la base."
                )
            with btn_col:
                st.write("")
                st.button("↻ Actualizar", type="primary")

            op_dia = temp_op[pd.to_datetime(temp_op["Fecha Día"], errors="coerce").dt.date == fecha_consulta].copy()

            if not temp_daily.empty and "Fecha Día" in temp_daily.columns:
                daily_dia = temp_daily[pd.to_datetime(temp_daily["Fecha Día"], errors="coerce").dt.date == fecha_consulta].copy()
            else:
                daily_dia = pd.DataFrame()

            if not op_dia.empty:
                op_resumen = op_dia.groupby("Tienda", as_index=False).agg(
                    Muertos=("Muertos", "sum"),
                    Cajas=("Cajas", "sum"),
                    Probador=("Probador", "sum"),
                    Acondicionado=("Acondicionado", "sum"),
                    Ubicado=("Ubicado", "sum"),
                    Recorridos=("Recorridos", "sum"),
                )
            else:
                op_resumen = pd.DataFrame(columns=["Tienda", "Muertos", "Cajas", "Probador", "Acondicionado", "Ubicado", "Recorridos"])

            if not daily_dia.empty:
                sys_resumen = daily_dia.groupby("Tienda", as_index=False).agg(
                    Dev_Pzs=("Dev_Pzs", "sum")
                )
            else:
                sys_resumen = pd.DataFrame(columns=["Tienda", "Dev_Pzs"])

            # Solo tiendas con registro de productividad operativa en el día.
            # No se incluyen tiendas que solo traen sistema/dev sin productividad.
            if not op_resumen.empty:
                op_resumen["Productividad Registrada"] = (
                    pd.to_numeric(op_resumen["Muertos"], errors="coerce").fillna(0) +
                    pd.to_numeric(op_resumen["Cajas"], errors="coerce").fillna(0) +
                    pd.to_numeric(op_resumen["Probador"], errors="coerce").fillna(0) +
                    pd.to_numeric(op_resumen["Acondicionado"], errors="coerce").fillna(0) +
                    pd.to_numeric(op_resumen["Ubicado"], errors="coerce").fillna(0)
                )
                op_resumen = op_resumen[op_resumen["Productividad Registrada"] > 0]

            tiendas_dia = sorted(set(op_resumen["Tienda"].astype(str).tolist()))

            if not tiendas_dia:
                st.info("No hay registros para la fecha seleccionada.")
            else:
                resumen = pd.DataFrame({"Tienda": tiendas_dia})
                resumen = resumen.merge(op_resumen, on="Tienda", how="left")
                resumen = resumen.merge(sys_resumen, on="Tienda", how="left")
                resumen = resumen.fillna(0)

                for c in ["Dev_Pzs", "Muertos", "Cajas", "Probador", "Acondicionado", "Ubicado", "Recorridos"]:
                    resumen[c] = pd.to_numeric(resumen[c], errors="coerce").fillna(0)

                resumen["Piezas Ingresadas Día Anterior"] = resumen["Dev_Pzs"] + resumen["Muertos"] + resumen["Cajas"] + resumen["Probador"]
                resumen["Acondicionado"] = resumen["Acondicionado"]
                resumen["Pendiente Acondicionar"] = (resumen["Piezas Ingresadas Día Anterior"] - resumen["Acondicionado"]).clip(lower=0)
                resumen["Pendiente Ubicar"] = (resumen["Piezas Ingresadas Día Anterior"] - resumen["Ubicado"]).clip(lower=0)
                resumen["% Acondicionado"] = sdiv(resumen["Acondicionado"], resumen["Piezas Ingresadas Día Anterior"]) * 100
                resumen["% Ubicado"] = sdiv(resumen["Ubicado"], resumen["Piezas Ingresadas Día Anterior"]) * 100

                resumen["Estatus"] = np.where(
                    resumen["Pendiente Ubicar"] <= 0,
                    "🟢 Completo",
                    np.where(resumen["% Ubicado"] >= 80, "🟡 En proceso", "🔴 Pendiente")
                )

                resumen["Ranking Pendiente"] = resumen["Pendiente Ubicar"].rank(method="dense", ascending=False).astype(int)
                resumen = resumen.sort_values(["Pendiente Ubicar", "Pendiente Acondicionar"], ascending=False)

                total_ing_dia = resumen["Piezas Ingresadas Día Anterior"].sum()
                total_aco_dia = resumen["Acondicionado"].sum()
                total_ubi_dia = resumen["Ubicado"].sum()
                total_proc_dia = total_aco_dia + total_ubi_dia
                total_pend_dia = resumen["Pendiente Ubicar"].sum()
                pct_proc_dia = pct(total_proc_dia, total_ing_dia)

                st.markdown(f"""
                <div class="boceto-card-row">
                    <div class="boceto-kpi-card"><div class="boceto-big-icon big-magenta">↻</div><div><div class="boceto-card-title">Piezas Ingresadas Día Anterior<br>(Cambios y Devoluciones)</div><div class="boceto-card-value" style="color:#EC007C;">{n0(total_ing_dia)}</div><div class="boceto-card-foot">Total piezas</div></div></div>
                    <div class="boceto-kpi-card"><div class="boceto-big-icon big-blue">✓</div><div><div class="boceto-card-title">Procesado (Acondicionado + Ubicado)</div><div class="boceto-card-value" style="color:#0047B3;">{n0(total_proc_dia)}</div><div class="boceto-card-foot">Total piezas</div></div></div>
                    <div class="boceto-kpi-card"><div class="boceto-big-icon big-orange">⌛</div><div><div class="boceto-card-title">Pendiente por Procesar</div><div class="boceto-card-value" style="color:#F39800;">{n0(total_pend_dia)}</div><div class="boceto-card-foot">Total piezas</div></div></div>
                    <div class="boceto-kpi-card"><div class="boceto-big-icon big-green">%</div><div><div class="boceto-card-title">% Procesado</div><div class="boceto-card-value" style="color:#00A651;">{p1(pct_proc_dia)}</div><div class="boceto-card-foot">Del ingreso total</div></div></div>
                </div>
                """, unsafe_allow_html=True)

                resumen_general = pd.DataFrame([{
                    "Tiendas con Productividad": resumen["Tienda"].nunique(),
                    "Piezas Ingresadas Día Anterior (Cambios y Devoluciones)": total_ing_dia,
                    "Acondicionado": total_aco_dia,
                    "Ubicado": total_ubi_dia,
                    "Procesado": total_proc_dia,
                    "Pendiente por Procesar": total_pend_dia,
                    "% Procesado": pct_proc_dia
                }])
                st.markdown("<div class='boceto-section'><h3>RESUMEN GENERAL – DÍA ANTERIOR</h3>", unsafe_allow_html=True)
                st.dataframe(style_dataframe(resumen_general), width="stretch")
                st.markdown("</div>", unsafe_allow_html=True)

                columnas = [
                    "Tienda",
                    "Piezas Ingresadas",
                    "Acondicionado",
                    "Ubicado",
                    "Pendiente Acondicionar",
                    "Pendiente Ubicar",
                    "% Acondicionado"
                ]

                st.markdown("<div class='boceto-section'><h3>DETALLE POR TIENDA – DÍA ANTERIOR</h3>", unsafe_allow_html=True)
                st.dataframe(style_dataframe(resumen[columnas]), width="stretch")
                st.markdown("</div>", unsafe_allow_html=True)
                chart_col1, chart_col2 = st.columns(2)
                with chart_col1:
                    st.markdown("<div class='boceto-section'><h3>INGRESO vs ACONDICIONADO vs UBICADO POR TIENDA</h3>", unsafe_allow_html=True)
                    fig_combo = go.Figure()
                    fig_combo.add_bar(x=resumen["Tienda"], y=resumen["Acondicionado"], name="Acondicionado (Piezas)", text=resumen["Acondicionado"], textposition="outside", marker_color="#00A651")
                    fig_combo.add_bar(x=resumen["Tienda"], y=resumen["Ubicado"], name="Ubicado (Piezas)", text=resumen["Ubicado"], textposition="outside", marker_color="#F39800")
                    fig_combo.add_scatter(x=resumen["Tienda"], y=resumen["Piezas Ingresadas"], name="Piezas Ingresadas", mode="lines+markers+text", text=[f"{x:,.0f}" for x in resumen["Piezas Ingresadas"]], textposition="top center", line=dict(color="#0047B3", width=4))
                    fig_combo.update_layout(barmode="group", height=400, margin=dict(l=20,r=20,t=40,b=20), legend=dict(orientation="h"))
                    st.plotly_chart(fig_combo, width="stretch")
                    st.markdown("</div>", unsafe_allow_html=True)
                with chart_col2:
                    st.markdown("<div class='boceto-section'><h3>PENDIENTES POR PROCESAR</h3>", unsafe_allow_html=True)
                    fig_pend = go.Figure()
                    fig_pend.add_bar(x=resumen["Tienda"], y=resumen["Pendiente Acondicionar"], name="Pendiente por Acondicionar", text=resumen["Pendiente Acondicionar"], textposition="outside", marker_color="#00A651")
                    fig_pend.add_bar(x=resumen["Tienda"], y=resumen["Pendiente Ubicar"], name="Pendiente por Ubicar", text=resumen["Pendiente Ubicar"], textposition="outside", marker_color="#F39800")
                    fig_pend.add_scatter(x=resumen["Tienda"], y=resumen["Piezas Ingresadas"], name="Piezas Ingresadas", mode="lines+markers+text", text=[f"{x:,.0f}" for x in resumen["Piezas Ingresadas"]], textposition="top center", line=dict(color="#0047B3", width=4))
                    fig_pend.update_layout(barmode="group", height=400, margin=dict(l=20,r=20,t=40,b=20), legend=dict(orientation="h"))
                    st.plotly_chart(fig_pend, width="stretch")
                    st.markdown("</div>", unsafe_allow_html=True)
                pdf_data = pdf_dia_anterior_bytes(resumen_general, resumen[columnas], str(fecha_consulta))
                st.download_button("⬇️ Descargar PDF", data=pdf_data, file_name=f"dia_anterior_pendiente_{fecha_consulta}.pdf", mime="application/pdf")


                st.markdown("<div class='boceto-section'><h3>GRÁFICA COMBINADA: PIEZAS VS ACONDICIONADO VS UBICADO</h3>", unsafe_allow_html=True)
                fig_combo = go.Figure()
                fig_combo.add_bar(x=resumen["Tienda"], y=resumen["Acondicionado"], name="Acondicionado", text=[f"{x:,.0f}" for x in resumen["Acondicionado"]], textposition="outside", marker_color="#0047B3")
                fig_combo.add_bar(x=resumen["Tienda"], y=resumen["Ubicado"], name="Ubicado", text=[f"{x:,.0f}" for x in resumen["Ubicado"]], textposition="outside", marker_color="#EC007C")
                fig_combo.add_scatter(x=resumen["Tienda"], y=resumen["Piezas Ingresadas Día Anterior"], name="Piezas Ingresadas Día Anterior", mode="lines+markers+text", text=[f"{x:,.0f}" for x in resumen["Piezas Ingresadas Día Anterior"]], textposition="top center", line=dict(color="#F39800", width=4))
                fig_combo.update_layout(barmode="group", height=430, margin=dict(l=20,r=20,t=40,b=20), legend=dict(orientation="h"))
                st.plotly_chart(fig_combo, width="stretch")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='boceto-section'><h3>GRÁFICA COMBINADA: PENDIENTES POR PROCESAR</h3>", unsafe_allow_html=True)
                fig_pend = go.Figure()
                fig_pend.add_bar(x=resumen["Tienda"], y=resumen["Pendiente Acondicionar"], name="Pendiente por Acondicionar", text=[f"{x:,.0f}" for x in resumen["Pendiente Acondicionar"]], textposition="outside", marker_color="#0047B3")
                fig_pend.add_bar(x=resumen["Tienda"], y=resumen["Pendiente Ubicar"], name="Pendiente por Ubicar", text=[f"{x:,.0f}" for x in resumen["Pendiente Ubicar"]], textposition="outside", marker_color="#EC007C")
                fig_pend.add_scatter(x=resumen["Tienda"], y=resumen["Piezas Ingresadas Día Anterior"], name="Piezas Ingresadas", mode="lines+markers+text", text=[f"{x:,.0f}" for x in resumen["Piezas Ingresadas Día Anterior"]], textposition="top center", line=dict(color="#F39800", width=4))
                fig_pend.update_layout(barmode="group", height=430, margin=dict(l=20,r=20,t=40,b=20), legend=dict(orientation="h"))
                st.plotly_chart(fig_pend, width="stretch")
                st.markdown("</div>", unsafe_allow_html=True)

                export_buttons("dia_anterior_pendiente", {"Dia_Anterior_Pendiente": resumen[columnas]})
                pdf_data = pdf_dia_anterior_bytes(resumen_general, resumen[columnas], str(fecha_consulta))
                st.download_button("⬇️ Descargar PDF Día Anterior", data=pdf_data, file_name=f"dia_anterior_pendiente_{fecha_consulta}.pdf", mime="application/pdf")


# 1 Panel Ejecutivo
with tab["1. Panel Ejecutivo"]:
    st.subheader("Panel Ejecutivo")
    st.caption("Top y Bottom solo consideran tiendas con registros. Se descartan registros no coherentes mediante agrupación por ID empleado / Ocurrencia.")

    score_df = ss.copy()
    if not score_df.empty:
        score_df["Score"] = (
            score_df["Productividad"].rank(pct=True)*40 +
            score_df["% Acondicionado"].rank(pct=True)*25 +
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
            Acondicionado=("Acondicionado","sum"),
            Ubicado=("Ubicado","sum")
        )
        sys_week = daily_all.groupby("Semana ISO", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum")) if not daily_all.empty else pd.DataFrame(columns=["Semana ISO","Dev_Pzs"])
        macro = macro.merge(sys_week, on="Semana ISO", how="left").fillna(0)
        macro["Piezas Ingresadas"] = macro["Dev_Pzs"] + macro["Muertos"] + macro["Cajas"] + macro["Probador"]
        macro["% Acondicionado"] = sdiv(macro["Acondicionado"], macro["Piezas Ingresadas"]) * 100
        macro["% Ubicado"] = sdiv(macro["Ubicado"], macro["Piezas Ingresadas"]) * 100
        macro["Semana ISO"] = macro["Semana ISO"].astype(int)
        macro = macro.sort_values("Semana ISO").tail(4)
        st.dataframe(style_dataframe(macro), width="stretch")
        st.plotly_chart(px.bar(macro, x="Semana ISO", y="Piezas Ingresadas", text_auto=True,
                               title="Total de ingresos por semana", color_discrete_sequence=["#3366CC"]),
                        width="stretch")
        st.plotly_chart(px.line(macro, x="Semana ISO", y=["% Acondicionado","% Ubicado"], markers=True,
                                title="% Acondicionado vs % Ubicado", color_discrete_sequence=["#3366CC","#FF99FF"]),
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
    eco = ss[["Tienda","Recuperación $","Costo_Dev","Recuperación %","Estado"]].copy()
    eco = eco.rename(columns={"Recuperación $":"Recuperación $", "Costo_Dev":"Costo Dev $"})
    eco["Valor Pendiente $"] = eco["Costo Dev $"] - eco["Recuperación $"]
    st.dataframe(style_dataframe(eco.sort_values("Recuperación $", ascending=False)), width="stretch")
    st.plotly_chart(px.bar(eco.sort_values("Recuperación $", ascending=False), x="Tienda", y="Recuperación $",
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
            Acondicionado=("Acondicionado","sum"),
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
            "Actividad": ["Recolección de muertos", "Acondicionado", "Ubicado"],
            "Piezas": [op["Recolección de Muertos"].sum(), op["Acondicionado"].sum(), op["Ubicado"].sum()]
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
    c1.metric("Piezas Ingresadas", n0(total_ingresos))
    c2.metric("Acondicionado", n0(acondicionado))
    c3.metric("Ubicado", n0(ubicado))
    c4.metric("% Acondicionado", p1(hab_pct))
    c5.metric("% Ubicado", p1(ubi_pct))
    ef = ss.copy()
    ef["Ranking"] = ef["% Ubicado"].rank(method="dense", ascending=False).astype(int)
    ef = ef[["Ranking","Tienda","Piezas Ingresadas","Acondicionado","Ubicado","% Acondicionado","% Ubicado","Estado"]].sort_values("Ranking")
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
            Acondicionado=("Acondicionado","sum"),
            Ubicado=("Ubicado","sum"),
            Recorridos=("Recorridos","sum")
        )
        sys_day = daily.groupby(["Fecha Día","Tienda"], as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum")) if not daily.empty else pd.DataFrame(columns=["Fecha Día","Tienda","Dev_Pzs"])
        diaria = diaria.merge(sys_day, on=["Fecha Día","Tienda"], how="left").fillna(0)
        diaria["Piezas Ingresadas"] = diaria["Dev_Pzs"] + diaria["Recoleccion"]
        diaria["% Acondicionado"] = sdiv(diaria["Acondicionado"], diaria["Piezas Ingresadas"]) * 100
        diaria["% Ubicado"] = sdiv(diaria["Ubicado"], diaria["Piezas Ingresadas"]) * 100
        diaria["Meta"] = metas["productividad_diaria"]
        diaria["Productividad"] = diaria["Recoleccion"] + diaria["Acondicionado"] + diaria["Ubicado"]
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
        st.dataframe(style_dataframe(cat.sort_values("Recuperación $", ascending=False)), width="stretch")
        st.plotly_chart(px.bar(cat.sort_values("Recuperación $", ascending=False), x="Categoria", y="Recuperación $",
                               color_discrete_sequence=["#3366CC"]), width="stretch")

# 12 Subcategoría
with tab["12. Análisis por Subcategoría"]:
    st.subheader("Análisis por Subcategoría")
    if co.empty:
        st.warning("Sin información comercial.")
    else:
        sub = co.groupby("Subcategoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum"))
        sub["Conversión %"] = sdiv(sub["Vta_Pzs"], sub["Dev_Pzs"]) * 100
        st.dataframe(style_dataframe(sub.sort_values("Recuperación $", ascending=False)), width="stretch")
        st.plotly_chart(px.bar(sub.sort_values("Recuperación $", ascending=False).head(30), x="Subcategoria", y="Recuperación $",
                               color_discrete_sequence=["#FF99FF"]), width="stretch")

# 13 Ranking Tiendas
with tab["13. Ranking de Tiendas"]:
    st.subheader("Ranking de Tiendas")
    rank = ss_all.copy()
    rank["Score"] = (
        rank["Productividad"].rank(pct=True)*40 +
        rank["% Acondicionado"].rank(pct=True)*25 +
        rank["% Ubicado"].rank(pct=True)*15 +
        rank["Conversión %"].rank(pct=True)*10 +
        rank["% Recorridos"].rank(pct=True)*10
    ).round(1)
    rank["Ranking"] = rank["Score"].rank(method="dense", ascending=False).astype(int)
    rank = rank.rename(columns={"Recuperacion":"Recuperación $"})
    rank = rank[["Ranking","Tienda","Dev_Pzs","Vta_Pzs","Recuperación $","Conversión %","Productividad","Recorridos","Score","Estado"]].sort_values("Ranking")
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
        "Componente": ["Productividad", "Acondicionado", "Ubicado", "Conversión", "Recorridos"],
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


# 17 Corrección de Nombres
if "17. Corrección de Nombres" in tab:
    with tab["17. Corrección de Nombres"]:
        st.subheader("Corrección de Nombres por ID Empleado / Ocurrencia")
        st.caption("Disponible para Administrador y Gerente. Permite unificar nombres mal capturados usando la Ocurrencia.")

        if op_all.empty:
            st.warning("Sin datos operativos.")
        else:
            empleados = op_all.groupby("Ocurrencia", as_index=False).agg(Nombre_actual=("Nombre","first"))
            empleados = empleados.sort_values("Ocurrencia")
            edit = st.data_editor(empleados, width="stretch", num_rows="fixed")

            if st.button("Guardar nombres corregidos"):
                mapping = dict(zip(edit["Ocurrencia"].astype(str), edit["Nombre_actual"].astype(str)))
                save_nombre_map(mapping)
                st.success("Nombres actualizados correctamente.")
                st.rerun()


# 17 Configuración
if "18. Configuración de Metas" in tab:
    with tab["18. Configuración de Metas"]:
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

        st.write("Historial de metas")
        st.dataframe(style_dataframe(get_historial_metas()), width="stretch")

# 18 Diagnóstico
if "19. Diagnóstico de Datos" in tab:
    with tab["19. Diagnóstico de Datos"]:
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
with tab["20. Compartir ORION"]:
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
