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
# ORION CORPORATIVO
# Plataforma Indicadores de Recuperación de Mercancía
# PRICE SHOES | OPERACIONES ROPA
# ==========================================================

APP_NAME = "ORION"
APP_SUBTITLE = "Plataforma Indicadores de Recuperación de Mercancía"
DATA_DIR = Path("orion_data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "orion.db"
PARQUET_OPERACION = DATA_DIR / "operacion.parquet"
PARQUET_RECUPERACION = DATA_DIR / "recuperacion.parquet"
PARQUET_MODELOS = DATA_DIR / "modelos.parquet"

TIENDAS_OFICIALES = [
    "Iztapalapa", "Vallejo", "Ecatepec", "Toluca", "Arco Norte",
    "Ixtapaluca", "Querétaro", "Centro", "Olivar", "León",
    "Puebla", "Puebla Sur", "Aguascalientes", "Veracruz",
    "Naucalpan", "Miravalle", "Atemajac"
]

DEFAULT_GOALS = {
    "productividad_diaria": 784.0,
    "conversion": 80.0,
    "recuperacion": 80.0,
    "habilitado_ingresos": 85.0,
    "ubicado_habilitado": 85.0,
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

ALIASES = {
    "Tienda": ["Tienda", "Sucursal", "Ubicación", "Ubicacion"],
    "Nombre": ["Nombre", "Usuario", "Colaborador", "nombre"],
    "Ocurrencia": ["Ocurrencia", "Occurrence"],
    "Fecha": ["Fecha", "Dia", "Día"],
    "Actividad Realizada": ["Actividad Realizada", "Actividad", "Proceso"],
    "Número de Piezas": ["Número de Piezas", "Numero de Piezas", "Piezas", "Pzas"],
    "Recorridos": ["RECORRIDOS", "Recorridos", "recorridos"],
    "Probador": ["Probado", "Probador", "Probadores"],
    "Dev_Pzs": ["Dev_pzs", "Dev Pzs", "Dev_Pzs", "Devoluciones Pzs"],
    "Vta_Pzs": ["Ventas Netas Pzs", "Vta_Pzs", "Vta Pzs", "Venta Pzs"],
    "Vta_Imp": ["Venta Neta $", "Vta_Imp", "Vta Imp", "Venta Neta"],
    "Costo_Dev": ["Costo Devolución", "Costo_Dev", "Costo Dev", "Costo Devolucion"],
    "Modelo": ["Modelo", "Modelo Proveedor", "Modelo_Proveedor"],
    "Categoria": ["Categoría", "Categoria"],
    "Subcategoria": ["Sub Categoría", "Subcategoria", "Subcategoría", "Sub Categoria"],
    "Id Art": ["Id Art", "ID", "Id", "Artículo", "Articulo"],
    "Color": ["Color"],
}

st.set_page_config(page_title=APP_NAME, page_icon="🚀", layout="wide")

# ---------------------- CSS ----------------------
st.markdown("""
<style>
    .main, .stApp {background-color:#F5F5F5;}
    .block-container {padding-top:1.2rem; padding-bottom:2rem;}
    .orion-header {
        background: linear-gradient(90deg, #003366, #3366CC);
        color:white;
        padding:22px 26px;
        border-radius:22px;
        box-shadow:0 8px 24px rgba(0,0,0,.16);
        margin-bottom:18px;
    }
    .orion-title {font-size:34px; font-weight:900; margin:0;}
    .orion-sub {font-size:16px; opacity:.95; margin-top:4px;}
    .confidencial {
        background:#ffffff;
        border-left:6px solid #FF99FF;
        padding:12px 16px;
        border-radius:14px;
        font-size:12px;
        color:#334155;
        margin-top:18px;
    }
    div[data-testid="stMetric"] {
        background:#FFFFFF;
        border:1px solid #E2E8F0;
        border-radius:18px;
        padding:14px;
        box-shadow:0 5px 16px rgba(15, 23, 42, .06);
    }
    .status-ok {color:#166534;font-weight:800;}
    .status-mid {color:#92400E;font-weight:800;}
    .status-bad {color:#991B1B;font-weight:800;}
</style>
""", unsafe_allow_html=True)

# ---------------------- DB ----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            key TEXT PRIMARY KEY,
            value REAL,
            updated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            hora TEXT,
            usuario TEXT,
            meta TEXT,
            valor_anterior REAL,
            valor_nuevo REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    for k, v in DEFAULT_GOALS.items():
        cur.execute(
            "INSERT OR IGNORE INTO goals(key, value, updated_at) VALUES (?, ?, ?)",
            (k, float(v), datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

def get_goals():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT key, value FROM goals", conn)
    conn.close()
    goals = DEFAULT_GOALS.copy()
    goals.update(dict(zip(df["key"], df["value"])))
    return goals

def update_goal(key, value, user="Administrador"):
    goals = get_goals()
    old = float(goals.get(key, 0))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE goals SET value=?, updated_at=? WHERE key=?", (float(value), datetime.now().isoformat(), key))
    now = datetime.now()
    cur.execute(
        "INSERT INTO goal_history(fecha, hora, usuario, meta, valor_anterior, valor_nuevo) VALUES (?, ?, ?, ?, ?, ?)",
        (now.date().isoformat(), now.strftime("%H:%M:%S"), user, key, old, float(value))
    )
    conn.commit()
    conn.close()

def set_state(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO app_state(key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_state(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM app_state WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def goal_history():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM goal_history ORDER BY id DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

init_db()

# ---------------------- UTILS ----------------------
def normalize_text(x):
    if pd.isna(x):
        return "Sin registros"
    x = str(x).strip()
    return x if x else "Sin registros"

def to_num(s):
    if pd.isna(s):
        return 0.0
    if isinstance(s, str):
        s = s.replace("$", "").replace(",", "").replace(" ", "")
        if s in ["", "-", "nan", "None"]:
            return 0.0
    try:
        return float(pd.to_numeric(s, errors="coerce"))
    except Exception:
        return 0.0

def find_col(df, canonical):
    names = [canonical] + ALIASES.get(canonical, [])
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lookup:
            return lookup[n.lower()]
    return None

def standardize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for canonical in ALIASES:
        col = find_col(df, canonical)
        if col is not None and col != canonical:
            df = df.rename(columns={col: canonical})
    return df

def ensure_cols(df, cols):
    df = df.copy()
    for c in cols:
        if c not in df.columns:
            df[c] = 0 if c in ["Dev_Pzs", "Vta_Pzs", "Vta_Imp", "Costo_Dev", "Muertos", "Cajas", "Probador", "Habilitado", "Ubicado", "Recorridos", "Número de Piezas"] else np.nan
    return df

def safe_div(a, b):
    return np.where(pd.Series(b).astype(float) != 0, pd.Series(a).astype(float) / pd.Series(b).astype(float), 0)

def pct(a, b):
    try:
        return float(a) / float(b) * 100 if float(b) else 0
    except Exception:
        return 0

def detect_oper_sheet(xls):
    for s in xls.sheet_names:
        sl = s.lower().replace(" ", "")
        if "resultados" in sl and "productividad" in sl:
            return s
    for s in xls.sheet_names:
        if "productividad" in s.lower():
            return s
    return None

def detect_month_sheets(xls):
    meses = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
    out = []
    for s in xls.sheet_names:
        sl = s.lower()
        if re.search(meses, sl) and re.search(r"26|2026", sl):
            out.append(s)
    return out

def read_excel_any_header(file, sheet_name):
    raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
    best_row = 0
    best_score = -1
    keywords = ["tienda", "ubicación", "ubicacion", "nombre", "fecha", "modelo", "dev", "venta", "vta", "piezas"]
    for i in range(min(10, len(raw))):
        row = " ".join([str(x).lower() for x in raw.iloc[i].tolist()])
        score = sum(k in row for k in keywords)
        if score > best_score:
            best_score = score
            best_row = i
    df = pd.read_excel(file, sheet_name=sheet_name, header=best_row)
    df.columns = [str(c).strip() for c in df.columns]
    return df, best_row

def load_from_parquet():
    op = pd.read_parquet(PARQUET_OPERACION) if PARQUET_OPERACION.exists() else pd.DataFrame()
    rec = pd.read_parquet(PARQUET_RECUPERACION) if PARQUET_RECUPERACION.exists() else pd.DataFrame()
    mod = pd.read_parquet(PARQUET_MODELOS) if PARQUET_MODELOS.exists() else pd.DataFrame()
    return op, rec, mod

def process_file(file):
    diagnostics = {"hojas_detectadas": [], "errores": [], "encabezados": {}, "columnas": {}}
    xls = pd.ExcelFile(file)
    diagnostics["hojas_detectadas"] = xls.sheet_names

    op_sheet = detect_oper_sheet(xls)
    month_sheets = detect_month_sheets(xls)

    # Operación
    if op_sheet:
        op, header = read_excel_any_header(file, op_sheet)
        diagnostics["encabezados"][op_sheet] = header
        op = standardize_columns(op)
    else:
        op = pd.DataFrame()
        diagnostics["errores"].append("No se detectó hoja operativa Resultados de productividad.")

    op_cols = ["Ocurrencia", "Nombre", "Fecha", "Tienda", "Actividad Realizada", "Número de Piezas",
               "Recorridos", "Muertos", "Cajas", "Probador", "Habilitado", "Ubicado"]
    op = ensure_cols(op, op_cols)
    if not op.empty:
        op["Fecha"] = pd.to_datetime(op["Fecha"], errors="coerce")
        op["Semana ISO"] = op["Fecha"].dt.isocalendar().week.astype("Int64")
        op["Año ISO"] = op["Fecha"].dt.isocalendar().year.astype("Int64")
        op["Mes"] = op["Fecha"].dt.month_name()
        for c in ["Tienda", "Nombre", "Ocurrencia", "Actividad Realizada"]:
            op[c] = op[c].apply(normalize_text)
        for c in ["Número de Piezas", "Recorridos", "Muertos", "Cajas", "Probador", "Habilitado", "Ubicado"]:
            op[c] = op[c].apply(to_num)
        op["Ingresos"] = op["Muertos"] + op["Cajas"] + op["Probador"]
        op["Productividad Total"] = op["Dev_Pzs"] if "Dev_Pzs" in op.columns else 0
        op["Productividad Total"] = op["Productividad Total"] + op["Muertos"] + op["Cajas"] + op["Probador"] + op["Habilitado"] + op["Ubicado"]
        op["Habilitado / Ingresos"] = safe_div(op["Habilitado"], op["Ingresos"]) * 100
        op["Ubicado / Habilitado"] = safe_div(op["Ubicado"], op["Habilitado"]) * 100
        op["Ubicado / Ingresos"] = safe_div(op["Ubicado"], op["Ingresos"]) * 100

    # Mensuales / Recuperación
    rec_list = []
    modelos_list = []
    for s in month_sheets:
        try:
            df, header = read_excel_any_header(file, s)
            diagnostics["encabezados"][s] = header
            df = standardize_columns(df)
            df["Mes_Origen"] = s
            df = ensure_cols(df, ["Tienda", "Modelo", "Categoria", "Subcategoria", "Dev_Pzs", "Vta_Pzs", "Vta_Imp", "Costo_Dev", "Id Art", "Color"])
            for c in ["Dev_Pzs", "Vta_Pzs", "Vta_Imp", "Costo_Dev"]:
                df[c] = df[c].apply(to_num)
            for c in ["Tienda", "Modelo", "Categoria", "Subcategoria", "Id Art", "Color"]:
                df[c] = df[c].apply(normalize_text)
            df["Piezas Vendidas Validadas"] = np.minimum(df["Vta_Pzs"], df["Dev_Pzs"])
            df["Conversión %"] = safe_div(df["Piezas Vendidas Validadas"], df["Dev_Pzs"]) * 100
            df["Valor Recuperado"] = df["Vta_Imp"]
            df["Valor Pendiente"] = df["Costo_Dev"] - df["Vta_Imp"]
            df["Recuperación %"] = safe_div(df["Valor Recuperado"], df["Costo_Dev"]) * 100
            rec_list.append(df)
            modelos_list.append(df)
        except Exception as e:
            diagnostics["errores"].append(f"Error leyendo {s}: {e}")

    rec = pd.concat(rec_list, ignore_index=True) if rec_list else pd.DataFrame()
    modelos = pd.concat(modelos_list, ignore_index=True) if modelos_list else pd.DataFrame()

    diagnostics["columnas"]["operacion"] = list(op.columns) if not op.empty else []
    diagnostics["columnas"]["recuperacion"] = list(rec.columns) if not rec.empty else []

    return op, rec, modelos, diagnostics

def save_data(op, rec, mod, diagnostics, filename):
    if not op.empty:
        op.to_parquet(PARQUET_OPERACION, index=False)
    if not rec.empty:
        rec.to_parquet(PARQUET_RECUPERACION, index=False)
    if not mod.empty:
        mod.to_parquet(PARQUET_MODELOS, index=False)
    set_state("last_update", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    set_state("last_file", filename)
    set_state("diagnostics", json.dumps(diagnostics, ensure_ascii=False, default=str))

def excel_bytes(sheets):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return output.getvalue()

def complete_stores(df, value_cols):
    base = pd.DataFrame({"Tienda": TIENDAS_OFICIALES})
    if df.empty:
        for c in value_cols:
            base[c] = 0
        base["Estado"] = "Sin registros"
        return base
    out = base.merge(df, on="Tienda", how="left")
    for c in value_cols:
        out[c] = out[c].fillna(0)
    out["Estado"] = np.where(out[value_cols].sum(axis=1) > 0, "Con registros", "Sin registros")
    return out

# ---------------------- HEADER ----------------------
now = datetime.now()
last_update = get_state("last_update", "Sin actualización")
last_file = get_state("last_file", "Sin archivo cargado")

st.markdown(f"""
<div class="orion-header">
    <div style="font-weight:800; letter-spacing:.08em;">PRICE SHOES | OPERACIONES ROPA</div>
    <div class="orion-title">🚀 ORION</div>
    <div class="orion-sub">{APP_SUBTITLE}</div>
    <div style="margin-top:10px; font-size:13px;">
        Productividad | Conversión | Recuperación Económica | Eficiencia Operativa<br>
        Fecha actual: {now.strftime('%Y-%m-%d')} | Hora actual: {now.strftime('%H:%M:%S')} |
        Última actualización: {last_update} | Estado de información: {"Disponible" if PARQUET_OPERACION.exists() or PARQUET_RECUPERACION.exists() else "Sin datos"}
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------- SIDEBAR ROLE/DATA ----------------------
with st.sidebar:
    st.header("🔐 Acceso")
    rol = st.radio("Rol", ["Consulta", "Administrador"], horizontal=True)
    admin_pass = ""
    is_admin = rol == "Administrador"
    if is_admin:
        admin_pass = st.text_input("Clave administrador", type="password")
        is_admin = admin_pass == st.secrets.get("ADMIN_PASSWORD", "orion_admin")

    st.divider()
    st.header("📂 Datos")
    if is_admin:
        upload = st.file_uploader("Cargar/Reemplazar Excel", type=["xlsx"])
        if upload is not None:
            try:
                op, rec, mod, diagnostics = process_file(upload)
                save_data(op, rec, mod, diagnostics, upload.name)
                st.success("Archivo procesado y guardado.")
            except Exception as e:
                st.error(f"No se pudo procesar el archivo: {e}")
    else:
        st.caption("Modo consulta: visualización sin carga de archivos.")

op, rec, mod = load_from_parquet()

if op.empty and rec.empty:
    st.warning("No hay datos persistidos. Un administrador debe cargar el Excel por primera vez.")
    st.stop()

goals = get_goals()

# ---------------------- FILTROS GLOBALES ----------------------
with st.sidebar:
    st.divider()
    st.header("🎛️ Filtros globales")

    meses = sorted(set(op.get("Mes", pd.Series(dtype=str)).dropna().astype(str).tolist() + rec.get("Mes_Origen", pd.Series(dtype=str)).dropna().astype(str).tolist()))
    semanas = sorted([int(x) for x in op.get("Semana ISO", pd.Series(dtype=float)).dropna().unique()]) if not op.empty and "Semana ISO" in op else []
    tiendas = TIENDAS_OFICIALES
    actividades = sorted(op.get("Actividad Realizada", pd.Series(dtype=str)).dropna().astype(str).unique()) if not op.empty else []
    categorias = sorted(rec.get("Categoria", pd.Series(dtype=str)).dropna().astype(str).unique()) if not rec.empty else []
    subcats = sorted(rec.get("Subcategoria", pd.Series(dtype=str)).dropna().astype(str).unique()) if not rec.empty else []
    modelos = sorted(rec.get("Modelo", pd.Series(dtype=str)).dropna().astype(str).unique()) if not rec.empty else []
    colabs = sorted(op.get("Nombre", pd.Series(dtype=str)).dropna().astype(str).unique()) if not op.empty else []
    ocurrencias = sorted(op.get("Ocurrencia", pd.Series(dtype=str)).dropna().astype(str).unique()) if not op.empty else []

    f_mes = st.multiselect("Mes", meses)
    f_semana = st.multiselect("Semana", semanas)
    f_tienda = st.multiselect("Tienda", tiendas)
    f_actividad = st.multiselect("Actividad", actividades)
    f_categoria = st.multiselect("Categoría", categorias)
    f_subcat = st.multiselect("Subcategoría", subcats)
    f_modelo = st.multiselect("Modelo", modelos)
    f_colab = st.multiselect("Colaborador", colabs)
    f_ocurrencia = st.multiselect("Ocurrencia", ocurrencias)

op_f = op.copy()
rec_f = rec.copy()

try:
    if f_mes and not op_f.empty:
        op_f = op_f[op_f["Mes"].isin(f_mes)]
    if f_mes and not rec_f.empty:
        rec_f = rec_f[rec_f["Mes_Origen"].isin(f_mes)]
    if f_semana and not op_f.empty:
        op_f = op_f[op_f["Semana ISO"].isin(f_semana)]
    if f_tienda:
        if not op_f.empty:
            op_f = op_f[op_f["Tienda"].isin(f_tienda)]
        if not rec_f.empty:
            rec_f = rec_f[rec_f["Tienda"].isin(f_tienda)]
    if f_actividad and not op_f.empty:
        op_f = op_f[op_f["Actividad Realizada"].isin(f_actividad)]
    if f_categoria and not rec_f.empty:
        rec_f = rec_f[rec_f["Categoria"].isin(f_categoria)]
    if f_subcat and not rec_f.empty:
        rec_f = rec_f[rec_f["Subcategoria"].isin(f_subcat)]
    if f_modelo and not rec_f.empty:
        rec_f = rec_f[rec_f["Modelo"].isin(f_modelo)]
    if f_colab and not op_f.empty:
        op_f = op_f[op_f["Nombre"].isin(f_colab)]
    if f_ocurrencia and not op_f.empty:
        op_f = op_f[op_f["Ocurrencia"].isin(f_ocurrencia)]
except Exception as e:
    st.warning(f"Algunos filtros no pudieron aplicarse: {e}")

# ---------------------- KPI FUNCTIONS ----------------------
def total_ingresos(df):
    return float(df["Ingresos"].sum()) if not df.empty and "Ingresos" in df else 0

def conversion_total(df):
    if df.empty:
        return 0
    return pct(df["Piezas Vendidas Validadas"].sum(), df["Dev_Pzs"].sum())

def recuperacion_total(df):
    if df.empty:
        return 0
    return pct(df["Valor Recuperado"].sum(), df["Costo_Dev"].sum())

def productividad_total(df):
    return float(df["Productividad Total"].sum()) if not df.empty and "Productividad Total" in df else 0

def recorridos_total(df):
    return float(df["Recorridos"].sum()) if not df.empty and "Recorridos" in df else 0

def eficiencia_op(df):
    if df.empty:
        return {"Habilitado / Ingresos":0, "Ubicado / Habilitado":0, "Ubicado / Ingresos":0}
    return {
        "Habilitado / Ingresos": pct(df["Habilitado"].sum(), df["Ingresos"].sum()),
        "Ubicado / Habilitado": pct(df["Ubicado"].sum(), df["Habilitado"].sum()),
        "Ubicado / Ingresos": pct(df["Ubicado"].sum(), df["Ingresos"].sum())
    }

def score_integral(opdf, recdf):
    eff = eficiencia_op(opdf)
    prod_goal = goals["productividad_diaria"]
    prod_pct = min(pct(productividad_total(opdf), max(opdf["Nombre"].nunique(),1) * prod_goal), 100) if not opdf.empty else 0
    hab = min(eff["Habilitado / Ingresos"], 100)
    ubi = min(eff["Ubicado / Ingresos"], 100)
    conv = min(conversion_total(recdf), 100)
    rec_cump = min(pct(recorridos_total(opdf), goals["recorridos_semanales"] * max(opdf["Tienda"].nunique(),1)), 100) if not opdf.empty else 0
    return round(prod_pct*.40 + hab*.25 + ubi*.15 + conv*.10 + rec_cump*.10, 1)

score = score_integral(op_f, rec_f)

# ---------------------- EXPORT HELPER ----------------------
def export_buttons(name, sheets):
    st.download_button(
        f"⬇️ Exportar {name} Excel",
        excel_bytes(sheets),
        file_name=f"{name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    first = next(iter(sheets.values())) if sheets else pd.DataFrame()
    if isinstance(first, pd.DataFrame):
        st.download_button(
            f"⬇️ Exportar {name} CSV",
            first.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{name}.csv",
            mime="text/csv"
        )

# ---------------------- TABS ----------------------
tab_names = [
    "1. Panel Ejecutivo", "2. Macro", "3. Conversión", "4. Recuperación Económica",
    "5. Productividad por Colaborador", "6. Productividad por Actividad", "7. Eficiencia Operativa",
    "8. Cumplimiento de Recorridos", "9. Indicadores Diarios", "10. Top 30 Modelos",
    "11. Análisis por Categoría", "12. Análisis por Subcategoría", "13. Ranking de Tiendas",
    "14. Ranking de Colaboradores", "15. Índice Integral", "16. Alertas Inteligentes",
    "17. Configuración de Metas", "18. Diagnóstico de Datos", "19. Compartir ORION"
]
if not is_admin:
    tab_names.remove("17. Configuración de Metas")
    tab_names.remove("18. Diagnóstico de Datos")

tabs = st.tabs(tab_names)

tab_map = dict(zip(tab_names, tabs))

# 1 Panel Ejecutivo
with tab_map["1. Panel Ejecutivo"]:
    st.subheader("Panel Ejecutivo Nacional")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Ingresos", f"{total_ingresos(op_f):,.0f}")
    c2.metric("Conversión", f"{conversion_total(rec_f):.1f}%")
    c3.metric("Recuperación", f"{recuperacion_total(rec_f):.1f}%")
    c4.metric("Productividad", f"{productividad_total(op_f):,.0f}")
    c5.metric("Score Promedio", f"{score:.1f}")

    st.caption(f"Metas vigentes: Productividad {goals['productividad_diaria']:,.0f} | Conversión {goals['conversion']:.1f}% | Recuperación {goals['recuperacion']:.1f}% | Recorridos semanales {goals['recorridos_semanales']:,.0f}")

    tienda_op = op_f.groupby("Tienda", as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum")) if not op_f.empty else pd.DataFrame(columns=["Tienda","Productividad","Recorridos"])
    tienda_rec = rec_f.groupby("Tienda", as_index=False).agg(Recuperacion=("Valor Recuperado","sum"), Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Vta_Pzs","sum")) if not rec_f.empty else pd.DataFrame(columns=["Tienda","Recuperacion","Dev_Pzs","Vta_Pzs"])
    resumen = pd.DataFrame({"Tienda": TIENDAS_OFICIALES}).merge(tienda_op, on="Tienda", how="left").merge(tienda_rec, on="Tienda", how="left").fillna(0)
    resumen["Score"] = (resumen["Productividad"].rank(pct=True)*40 + resumen["Recorridos"].rank(pct=True)*20 + resumen["Recuperacion"].rank(pct=True)*40).round(1)
    resumen["Estado"] = np.select(
        [(resumen["Productividad"]>0)&(resumen["Recuperacion"]>0), (resumen["Productividad"]>0)&(resumen["Recuperacion"]==0), (resumen["Productividad"]==0)&(resumen["Recuperacion"]>0)],
        ["🟢 Productividad + Recuperación", "🟡 Productividad sin Recuperación", "🟠 Recuperación sin Productividad"], default="🔴 Sin registros"
    )
    a,b = st.columns(2)
    with a:
        st.write("Top 2 Tiendas")
        st.dataframe(resumen.sort_values("Score", ascending=False).head(2), use_container_width=True)
    with b:
        st.write("Bottom 2 Tiendas")
        st.dataframe(resumen.sort_values("Score", ascending=True).head(2), use_container_width=True)
    a,b = st.columns(2)
    colab = op_f.groupby("Nombre", as_index=False).agg(Productividad=("Productividad Total","sum")).sort_values("Productividad", ascending=False) if not op_f.empty else pd.DataFrame()
    with a:
        st.write("Top 3 Colaboradores")
        st.dataframe(colab.head(3), use_container_width=True)
    with b:
        st.write("Bottom 3 Colaboradores")
        st.dataframe(colab.tail(3), use_container_width=True)
    fig = px.bar(resumen, x="Tienda", y="Score", color="Estado", title="Score por tienda")
    st.plotly_chart(fig, use_container_width=True)
    export_buttons("panel_ejecutivo", {"Resumen_Tiendas": resumen, "Colaboradores": colab})

# 2 Macro
with tab_map["2. Macro"]:
    st.subheader("Macro | Últimos 3 meses y últimas 4 semanas")
    if not op_f.empty:
        macro_sem = op_f.groupby("Semana ISO", as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum")).tail(4)
        st.dataframe(macro_sem, use_container_width=True)
        st.plotly_chart(px.line(macro_sem, x="Semana ISO", y=["Productividad","Recorridos"], markers=True), use_container_width=True)
    if not rec_f.empty:
        macro_mes = rec_f.groupby("Mes_Origen", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Vta_Pzs","sum"), Recuperacion=("Valor Recuperado","sum")).tail(3)
        macro_mes["Conversión %"] = safe_div(macro_mes["Vta_Pzs"], macro_mes["Dev_Pzs"]) * 100
        st.dataframe(macro_mes, use_container_width=True)
        st.plotly_chart(px.bar(macro_mes, x="Mes_Origen", y=["Dev_Pzs","Vta_Pzs"]), use_container_width=True)

# 3 Conversión
with tab_map["3. Conversión"]:
    st.subheader("Conversión de Devoluciones a Venta")
    if rec_f.empty:
        st.warning("Sin datos de recuperación/conversión.")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("Dev_Pzs", f"{rec_f['Dev_Pzs'].sum():,.0f}")
        c2.metric("Vta_Pzs validada", f"{rec_f['Piezas Vendidas Validadas'].sum():,.0f}")
        c3.metric("Conversión", f"{conversion_total(rec_f):.1f}%")
        conv = rec_f.groupby("Tienda", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"))
        conv["Conversión %"] = safe_div(conv["Vta_Pzs"], conv["Dev_Pzs"]) * 100
        conv = complete_stores(conv, ["Dev_Pzs", "Vta_Pzs", "Conversión %"])
        st.dataframe(conv, use_container_width=True)
        st.plotly_chart(px.bar(conv, x="Tienda", y="Conversión %", color="Estado"), use_container_width=True)
        export_buttons("conversion", {"Conversion": conv})

# 4 Recuperación Económica
with tab_map["4. Recuperación Económica"]:
    st.subheader("Recuperación Económica")
    if rec_f.empty:
        st.warning("Sin datos económicos.")
    else:
        rec_f["Valor Pendiente"] = rec_f["Costo_Dev"] - rec_f["Vta_Imp"]
        c1,c2,c3 = st.columns(3)
        c1.metric("Valor Recuperado", f"${rec_f['Vta_Imp'].sum():,.0f}")
        c2.metric("Costo Devolución", f"${rec_f['Costo_Dev'].sum():,.0f}")
        c3.metric("Valor Pendiente", f"${rec_f['Valor Pendiente'].sum():,.0f}")
        eco = rec_f.groupby("Tienda", as_index=False).agg(Valor_Recuperado=("Vta_Imp","sum"), Costo_Dev=("Costo_Dev","sum"), Valor_Pendiente=("Valor Pendiente","sum"))
        eco["Recuperación %"] = safe_div(eco["Valor_Recuperado"], eco["Costo_Dev"]) * 100
        eco = complete_stores(eco, ["Valor_Recuperado","Costo_Dev","Valor_Pendiente","Recuperación %"])
        st.dataframe(eco, use_container_width=True)
        st.plotly_chart(px.bar(eco, x="Tienda", y="Valor_Recuperado", color="Estado"), use_container_width=True)
        export_buttons("recuperacion_economica", {"Recuperacion": eco})

# 5 Productividad Colaborador
with tab_map["5. Productividad por Colaborador"]:
    st.subheader("Productividad por Colaborador")
    if op_f.empty:
        st.warning("Sin operación.")
    else:
        df = op_f.groupby(["Nombre","Tienda"], as_index=False).agg(Productividad=("Productividad Total","sum"), Registros=("Nombre","count"))
        df["Meta"] = goals["productividad_diaria"]
        df["Cumplimiento %"] = safe_div(df["Productividad"], df["Meta"]) * 100
        st.dataframe(df.sort_values("Productividad", ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(df.sort_values("Productividad", ascending=False).head(30), x="Nombre", y="Productividad", color="Tienda"), use_container_width=True)
        export_buttons("productividad_colaborador", {"Productividad": df})

# 6 Productividad Actividad
with tab_map["6. Productividad por Actividad"]:
    st.subheader("Productividad por Actividad")
    if op_f.empty:
        st.warning("Sin operación.")
    else:
        df = op_f.groupby("Actividad Realizada", as_index=False).agg(Productividad=("Productividad Total","sum"), Piezas=("Número de Piezas","sum"))
        st.dataframe(df.sort_values("Productividad", ascending=False), use_container_width=True)
        st.plotly_chart(px.pie(df, names="Actividad Realizada", values="Productividad", hole=.45), use_container_width=True)

# 7 Eficiencia
with tab_map["7. Eficiencia Operativa"]:
    st.subheader("Eficiencia Operativa")
    eff = eficiencia_op(op_f)
    c1,c2,c3 = st.columns(3)
    c1.metric("Habilitado / Ingresos", f"{eff['Habilitado / Ingresos']:.1f}%")
    c2.metric("Ubicado / Habilitado", f"{eff['Ubicado / Habilitado']:.1f}%")
    c3.metric("Ubicado / Ingresos", f"{eff['Ubicado / Ingresos']:.1f}%")
    if not op_f.empty:
        df = op_f.groupby("Tienda", as_index=False).agg(Ingresos=("Ingresos","sum"), Habilitado=("Habilitado","sum"), Ubicado=("Ubicado","sum"))
        df["Habilitado / Ingresos"] = safe_div(df["Habilitado"], df["Ingresos"]) * 100
        df["Ubicado / Habilitado"] = safe_div(df["Ubicado"], df["Habilitado"]) * 100
        df["Ubicado / Ingresos"] = safe_div(df["Ubicado"], df["Ingresos"]) * 100
        df = complete_stores(df, ["Ingresos","Habilitado","Ubicado","Habilitado / Ingresos","Ubicado / Habilitado","Ubicado / Ingresos"])
        st.dataframe(df, use_container_width=True)
        export_buttons("eficiencia_operativa", {"Eficiencia": df})

# 8 Recorridos
with tab_map["8. Cumplimiento de Recorridos"]:
    st.subheader("Cumplimiento de Recorridos por Tienda")
    if op_f.empty:
        st.warning("Sin recorridos.")
    else:
        df = op_f.groupby("Tienda", as_index=False).agg(Recorridos=("Recorridos","sum"))
        df = complete_stores(df, ["Recorridos"])
        df["Meta Semanal"] = goals["recorridos_semanales"]
        df["Cumplimiento %"] = safe_div(df["Recorridos"], df["Meta Semanal"]) * 100
        df["Estatus"] = np.where(df["Cumplimiento %"]>=100, "🟢 Cumple", np.where(df["Cumplimiento %"]>=80, "🟡 Atención", "🔴 Bajo"))
        st.dataframe(df.sort_values("Cumplimiento %", ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(df, x="Tienda", y="Cumplimiento %", color="Estatus"), use_container_width=True)

# 9 Diarios
with tab_map["9. Indicadores Diarios"]:
    st.subheader("Indicadores Diarios")
    if op_f.empty:
        st.warning("Sin operación.")
    else:
        df = op_f.groupby(["Fecha","Tienda","Ocurrencia","Nombre"], as_index=False).agg(
            Ingresos=("Ingresos","sum"), Habilitado=("Habilitado","sum"), Ubicado=("Ubicado","sum"), Recorridos=("Recorridos","sum")
        )
        df["Habilitado / Ingresos"] = safe_div(df["Habilitado"], df["Ingresos"]) * 100
        df["Ubicado / Habilitado"] = safe_div(df["Ubicado"], df["Habilitado"]) * 100
        df["Ubicado / Ingresos"] = safe_div(df["Ubicado"], df["Ingresos"]) * 100
        df["Meta"] = goals["recorridos_semanales"] / 7
        df["Cumplimiento %"] = safe_div(df["Recorridos"], df["Meta"]) * 100
        st.dataframe(df, use_container_width=True)
        export_buttons("indicadores_diarios", {"Indicadores": df})

# 10 Top 30 modelos
with tab_map["10. Top 30 Modelos"]:
    st.subheader("Top 30 Modelos")
    if rec_f.empty:
        st.warning("Sin modelos.")
    else:
        df = rec_f.groupby(["Modelo","Categoria","Subcategoria"], as_index=False).agg(
            Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Vta_Pzs","sum"), Recuperacion_Dinero=("Vta_Imp","sum"), Costo_Dev=("Costo_Dev","sum")
        )
        df["Recuperación %"] = safe_div(df["Recuperacion_Dinero"], df["Costo_Dev"]) * 100
        df["Valor Pendiente"] = df["Costo_Dev"] - df["Recuperacion_Dinero"]
        criterio = st.selectbox("Ranking", ["Mayor recuperación económica", "Mayor recuperación %", "Mayor venta", "Mayor pendiente"])
        col = {"Mayor recuperación económica":"Recuperacion_Dinero", "Mayor recuperación %":"Recuperación %", "Mayor venta":"Vta_Pzs", "Mayor pendiente":"Valor Pendiente"}[criterio]
        top = df.sort_values(col, ascending=False).head(30)
        st.dataframe(top, use_container_width=True)
        st.plotly_chart(px.bar(top, x="Modelo", y=col, color="Categoria"), use_container_width=True)

# 11 Categoría
with tab_map["11. Análisis por Categoría"]:
    st.subheader("Análisis por Categoría")
    if rec_f.empty:
        st.warning("Sin categorías.")
    else:
        df = rec_f.groupby("Categoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Vta_Pzs","sum"), Recuperacion=("Vta_Imp","sum"))
        df["Conversión %"] = safe_div(df["Vta_Pzs"], df["Dev_Pzs"]) * 100
        st.dataframe(df.sort_values("Recuperacion", ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(df, x="Categoria", y="Recuperacion"), use_container_width=True)

# 12 Subcategoría
with tab_map["12. Análisis por Subcategoría"]:
    st.subheader("Análisis por Subcategoría")
    if rec_f.empty:
        st.warning("Sin subcategorías.")
    else:
        df = rec_f.groupby("Subcategoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Vta_Pzs","sum"), Recuperacion=("Vta_Imp","sum"))
        df["Conversión %"] = safe_div(df["Vta_Pzs"], df["Dev_Pzs"]) * 100
        st.dataframe(df.sort_values("Recuperacion", ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(df.head(30), x="Subcategoria", y="Recuperacion"), use_container_width=True)

# 13 Ranking Tiendas
with tab_map["13. Ranking de Tiendas"]:
    st.subheader("Ranking de Tiendas")
    tienda_op = op_f.groupby("Tienda", as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum"), Habilitado=("Habilitado","sum"), Ingresos=("Ingresos","sum"), Ubicado=("Ubicado","sum")) if not op_f.empty else pd.DataFrame(columns=["Tienda","Productividad","Recorridos","Habilitado","Ingresos","Ubicado"])
    tienda_rec = rec_f.groupby("Tienda", as_index=False).agg(Conversion_Base=("Dev_Pzs","sum"), Vta=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum")) if not rec_f.empty else pd.DataFrame(columns=["Tienda","Conversion_Base","Vta","Recuperacion"])
    df = pd.DataFrame({"Tienda":TIENDAS_OFICIALES}).merge(tienda_op, on="Tienda", how="left").merge(tienda_rec, on="Tienda", how="left").fillna(0)
    df["Conversión %"] = safe_div(df["Vta"], df["Conversion_Base"]) * 100
    df["Score"] = (df["Productividad"].rank(pct=True)*40 + df["Habilitado"].rank(pct=True)*25 + df["Ubicado"].rank(pct=True)*15 + df["Conversión %"].rank(pct=True)*10 + df["Recorridos"].rank(pct=True)*10).round(1)
    st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)

# 14 Ranking Colaboradores
with tab_map["14. Ranking de Colaboradores"]:
    st.subheader("Ranking de Colaboradores")
    if op_f.empty:
        st.warning("Sin colaboradores.")
    else:
        df = op_f.groupby("Nombre", as_index=False).agg(Productividad=("Productividad Total","sum"), Registros=("Nombre","count"), Recorridos=("Recorridos","sum"))
        df["Score"] = (df["Productividad"].rank(pct=True)*70 + df["Registros"].rank(pct=True)*20 + df["Recorridos"].rank(pct=True)*10).round(1)
        st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)

# 15 Índice Integral
with tab_map["15. Índice Integral"]:
    st.subheader("Índice Integral ORION")
    st.metric("Score Integral", f"{score:.1f}/100")
    st.write("Fórmula: 40% Productividad + 25% Habilitado + 15% Ubicado + 10% Conversión + 10% Cumplimiento de Recorridos")
    st.progress(min(score/100, 1.0))

# 16 Alertas
with tab_map["16. Alertas Inteligentes"]:
    st.subheader("Alertas Inteligentes")
    alerts = []
    if conversion_total(rec_f) < goals["conversion"]:
        alerts.append(["Conversión", "Alta", f"Conversión menor a meta: {conversion_total(rec_f):.1f}% vs {goals['conversion']:.1f}%"])
    if recuperacion_total(rec_f) < goals["recuperacion"]:
        alerts.append(["Recuperación", "Alta", f"Recuperación menor a meta: {recuperacion_total(rec_f):.1f}% vs {goals['recuperacion']:.1f}%"])
    if productividad_total(op_f) < goals["productividad_diaria"]:
        alerts.append(["Productividad", "Media", "Productividad menor a meta diaria base."])
    if not op_f.empty:
        tiendas_con_op = set(op_f[op_f["Productividad Total"]>0]["Tienda"].unique())
        tiendas_con_rec = set(rec_f[rec_f["Vta_Imp"]>0]["Tienda"].unique()) if not rec_f.empty else set()
        for t in TIENDAS_OFICIALES:
            if t not in tiendas_con_op and t not in tiendas_con_rec:
                alerts.append(["Tienda sin registros", "Alta", f"{t} no tiene registros en operación ni recuperación."])
            elif t in tiendas_con_op and t not in tiendas_con_rec:
                alerts.append(["Productividad sin recuperación", "Media", f"{t} tiene productividad sin recuperación."])
    if rec_f.empty:
        alerts.append(["Recuperación", "Alta", "No hay datos de recuperación comercial."])
    alert_df = pd.DataFrame(alerts, columns=["Tipo","Prioridad","Alerta"])
    if alert_df.empty:
        st.success("Sin alertas críticas.")
    else:
        st.dataframe(alert_df, use_container_width=True)

# 17 Configuración
if "17. Configuración de Metas" in tab_map:
    with tab_map["17. Configuración de Metas"]:
        st.subheader("⚙️ Configuración de Metas")
        st.caption("Visible únicamente para Administradores.")
        cols = st.columns(3)
        new_vals = {}
        keys = list(DEFAULT_GOALS.keys())
        for i,k in enumerate(keys):
            with cols[i % 3]:
                new_vals[k] = st.number_input(k, value=float(goals[k]), step=1.0)
        if st.button("Guardar metas y recalcular"):
            for k,v in new_vals.items():
                if float(v) != float(goals[k]):
                    update_goal(k, v)
            st.success("Metas actualizadas. Los KPIs, rankings, alertas y score se recalculan automáticamente.")
            st.rerun()
        st.write("Historial de metas")
        st.dataframe(goal_history(), use_container_width=True)

# 18 Diagnóstico
if "18. Diagnóstico de Datos" in tab_map:
    with tab_map["18. Diagnóstico de Datos"]:
        st.subheader("Diagnóstico de Datos")
        diagnostics = json.loads(get_state("diagnostics", "{}") or "{}")
        st.write("Hojas detectadas")
        st.json(diagnostics.get("hojas_detectadas", []))
        st.write("Columnas detectadas")
        st.json(diagnostics.get("columnas", {}))
        st.write("Encabezado utilizado")
        st.json(diagnostics.get("encabezados", {}))
        c1,c2,c3 = st.columns(3)
        c1.metric("Registros operación", f"{len(op):,.0f}")
        c2.metric("Registros recuperación", f"{len(rec):,.0f}")
        c3.metric("Duplicados operación", f"{op.duplicated().sum() if not op.empty else 0:,.0f}")
        st.write("Valores nulos operación")
        st.dataframe(op.isna().sum().reset_index().rename(columns={"index":"Columna",0:"Nulos"}), use_container_width=True)
        st.write("Errores encontrados")
        st.json(diagnostics.get("errores", []))

# 19 Compartir
with tab_map["19. Compartir ORION"]:
    st.subheader("Compartir ORION")
    st.write("URL de la aplicación:")
    st.code("https://orion-operaciones-ropa.streamlit.app")
    st.write(f"Fecha de actualización: {last_update}")
    st.write(f"Archivo cargado: {last_file}")
    st.info("Usuarios consulta pueden visualizar los datos persistidos sin cargar Excel.")

st.markdown("""
<div class="confidencial">
<b>CONFIDENCIAL</b><br>
La información contenida en esta plataforma es propiedad de Price Shoes y está destinada exclusivamente para uso interno de Operaciones Ropa.
Queda prohibida su reproducción, distribución o divulgación sin autorización expresa de la Dirección correspondiente.<br>
© Price Shoes | Operaciones Ropa
</div>
""", unsafe_allow_html=True)
