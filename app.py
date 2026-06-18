import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from io import BytesIO
from datetime import datetime
import re
import sqlite3
import json

# =========================================================
# ORION V2
# Acoplado a: Base de datos muertos y cambios.xlsx
# PRICE SHOES | OPERACIONES ROPA
# =========================================================

st.set_page_config(
    page_title="ORION V2",
    page_icon="🚀",
    layout="wide"
)

DATA_DIR = Path("orion_data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "orion_config.db"
OPERACION_PARQUET = DATA_DIR / "operacion.parquet"
COMERCIAL_PARQUET = DATA_DIR / "comercial.parquet"

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

# -------------------------------
# ESTILO VISUAL
# -------------------------------
st.markdown("""
<style>
    .stApp {background-color:#F5F5F5;}
    .block-container {padding-top:1rem; padding-bottom:2rem;}
    .orion-header {
        background: linear-gradient(90deg, #003366, #3366CC);
        color:white;
        padding:22px 28px;
        border-radius:24px;
        margin-bottom:18px;
        box-shadow:0 8px 26px rgba(0,0,0,.18);
    }
    .orion-title {font-size:40px;font-weight:900;margin:0;}
    .orion-subtitle {font-size:18px;margin-top:6px;}
    .orion-mini {font-size:13px;margin-top:10px;opacity:.95;}
    div[data-testid="stMetric"] {
        background:#FFFFFF;
        border:1px solid #E2E8F0;
        border-radius:18px;
        padding:15px;
        box-shadow:0 5px 18px rgba(15,23,42,.06);
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

# -------------------------------
# DB CONFIG
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            clave TEXT PRIMARY KEY,
            valor REAL,
            actualizado TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            hora TEXT,
            usuario TEXT,
            meta TEXT,
            anterior REAL,
            nueva REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estado (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
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
    cur.execute(
        "UPDATE metas SET valor=?, actualizado=? WHERE clave=?",
        (float(valor), datetime.now().isoformat(), clave)
    )
    now = datetime.now()
    cur.execute("""
        INSERT INTO historial_metas(fecha, hora, usuario, meta, anterior, nueva)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(now.date()), now.strftime("%H:%M:%S"), usuario, clave, anterior, float(valor)))
    conn.commit()
    conn.close()

def get_historial():
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

init_db()

# -------------------------------
# UTILIDADES
# -------------------------------
def normalizar_texto(x):
    if pd.isna(x):
        return "Sin registros"
    s = str(x).strip()
    return s if s else "Sin registros"

def to_num(x):
    if pd.isna(x):
        return 0.0
    if isinstance(x, str):
        x = x.replace("$", "").replace(",", "").replace(" ", "").strip()
        if x in ["", "-", "nan", "None"]:
            return 0.0
    try:
        y = pd.to_numeric(x, errors="coerce")
        if pd.isna(y):
            return 0.0
        return float(y)
    except Exception:
        return 0.0

def consolidar_columnas_duplicadas(df):
    """
    Evita el error: The truth value of a Series is ambiguous.
    En el Excel real existe Nombre y nombre. Al renombrar ambas a Nombre,
    pandas devuelve un DataFrame cuando se pide df["Nombre"].
    Esta función une duplicados tomando el primer valor no vacío por fila.
    """
    df = df.copy()
    if not df.columns.duplicated().any():
        return df

    resultado = pd.DataFrame(index=df.index)
    for col in pd.unique(df.columns):
        temp = df.loc[:, df.columns == col]
        if temp.shape[1] == 1:
            resultado[col] = temp.iloc[:, 0]
        else:
            combinado = temp.bfill(axis=1).iloc[:, 0]
            resultado[col] = combinado
    return resultado

def serie_columna(df, col, default=None):
    """
    Devuelve siempre una Serie aunque existan columnas duplicadas.
    """
    if col not in df.columns:
        return pd.Series(default, index=df.index)
    value = df.loc[:, df.columns == col]
    if isinstance(value, pd.DataFrame):
        if value.shape[1] == 1:
            return value.iloc[:, 0]
        return value.bfill(axis=1).iloc[:, 0]
    return value

def pct(a, b):
    try:
        a = float(a)
        b = float(b)
        return (a / b * 100) if b else 0.0
    except Exception:
        return 0.0

def safe_div_series(a, b):
    a = pd.to_numeric(a, errors="coerce").fillna(0)
    b = pd.to_numeric(b, errors="coerce").fillna(0)
    return np.where(b != 0, a / b, 0)

def buscar_columna(df, opciones):
    cols_norm = {str(c).strip().lower(): c for c in df.columns}
    for op in opciones:
        if op.lower() in cols_norm:
            return cols_norm[op.lower()]
    return None

def preparar_tiendas(df, cols_valor):
    base = pd.DataFrame({"Tienda": TIENDAS_OFICIALES})
    if df is None or df.empty:
        for c in cols_valor:
            base[c] = 0
        base["Estado"] = "🔴 Sin registros"
        return base
    out = base.merge(df, on="Tienda", how="left")
    for c in cols_valor:
        if c not in out.columns:
            out[c] = 0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
    out["Estado"] = np.where(out[cols_valor].sum(axis=1) > 0, "🟢 Con registros", "🔴 Sin registros")
    return out

def excel_export(sheets):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return bio.getvalue()

def exportar(nombre, sheets):
    st.download_button(
        f"⬇️ Descargar {nombre} Excel",
        data=excel_export(sheets),
        file_name=f"{nombre}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    if sheets:
        first = list(sheets.values())[0]
        if isinstance(first, pd.DataFrame):
            st.download_button(
                f"⬇️ Descargar {nombre} CSV",
                data=first.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{nombre}.csv",
                mime="text/csv"
            )

# -------------------------------
# LECTURA ACOPLADA AL EXCEL REAL
# -------------------------------
def detectar_hoja_productividad(hojas):
    for h in hojas:
        clean = h.lower().replace(" ", "")
        if "resultados" in clean and "productividad" in clean:
            return h
    for h in hojas:
        if "productividad" in h.lower():
            return h
    return None

def detectar_hojas_mensuales(hojas):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    out = []
    for h in hojas:
        hl = h.lower()
        if any(m in hl for m in meses) and ("26" in hl or "2026" in hl):
            out.append(h)
    return out

def cargar_operacion(file, hoja):
    df = pd.read_excel(file, sheet_name=hoja)
    df.columns = [str(c).strip() for c in df.columns]

    rename = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ["ubicación", "ubicacion", "sucursal"]:
            rename[c] = "Tienda"
        elif cl in ["nombre", "usuario", "colaborador"]:
            rename[c] = "Nombre"
        elif cl in ["fecha"]:
            rename[c] = "Fecha"
        elif cl in ["actividad realizada", "actividad"]:
            rename[c] = "Actividad Realizada"
        elif cl in ["número de piezas", "numero de piezas", "piezas", "pzas"]:
            rename[c] = "Número de Piezas"
        elif cl in ["recorridos", "recorridos", "recorridos", "recorridos"]:
            rename[c] = "Recorridos"
        elif cl in ["recorridos", "recorridos", "recorridos", "recorridos", "recorridos"]:
            rename[c] = "Recorridos"
        elif "recorrido" in cl:
            rename[c] = "Recorridos"
        elif cl in ["motivo de ingreso", "motivo"]:
            rename[c] = "Motivo de ingreso"
        elif cl in ["ocurrencia", "occurrence"]:
            rename[c] = "Ocurrencia"

    df = df.rename(columns=rename)
    df = consolidar_columnas_duplicadas(df)

    for c in ["Fecha", "Tienda", "Actividad Realizada", "Número de Piezas", "Nombre", "Motivo de ingreso", "Recorridos", "Ocurrencia"]:
        if c not in df.columns:
            df[c] = np.nan

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Tienda"] = df["Tienda"].apply(normalizar_texto)
    df["Nombre"] = df["Nombre"].apply(normalizar_texto)
    df["Actividad Realizada"] = df["Actividad Realizada"].apply(normalizar_texto)
    df["Motivo de ingreso"] = df["Motivo de ingreso"].apply(normalizar_texto)
    df["Ocurrencia"] = df["Ocurrencia"].apply(normalizar_texto)
    df["Número de Piezas"] = df["Número de Piezas"].apply(to_num)
    df["Recorridos"] = df["Recorridos"].apply(to_num)

    # Clasificación por actividad/motivo
    act = (df["Actividad Realizada"].astype(str) + " " + df["Motivo de ingreso"].astype(str)).str.lower()

    df["Muertos"] = np.where(act.str.contains("muerto"), df["Número de Piezas"], 0)
    df["Cajas"] = np.where(act.str.contains("caja"), df["Número de Piezas"], 0)
    df["Probador"] = np.where(act.str.contains("probado|probador"), df["Número de Piezas"], 0)
    df["Habilitado"] = np.where(act.str.contains("habilitado|habilitar"), df["Número de Piezas"], 0)
    df["Ubicado"] = np.where(act.str.contains("ubicado|ubicar"), df["Número de Piezas"], 0)

    df["Ingresos"] = df["Muertos"] + df["Cajas"] + df["Probador"]
    df["Productividad Total"] = df["Ingresos"] + df["Habilitado"] + df["Ubicado"]

    df["Semana ISO"] = df["Fecha"].dt.isocalendar().week.astype("Int64")
    df["Año ISO"] = df["Fecha"].dt.isocalendar().year.astype("Int64")
    df["Mes"] = df["Fecha"].dt.month_name()
    df["Día"] = df["Fecha"].dt.date

    df["Habilitado / Ingresos"] = safe_div_series(df["Habilitado"], df["Ingresos"]) * 100
    df["Ubicado / Habilitado"] = safe_div_series(df["Ubicado"], df["Habilitado"]) * 100
    df["Ubicado / Ingresos"] = safe_div_series(df["Ubicado"], df["Ingresos"]) * 100

    return df

def cargar_hoja_mensual(file, hoja):
    # En el archivo real, las hojas comerciales tienen encabezado fuerte en fila 1
    raw = pd.read_excel(file, sheet_name=hoja, header=None)

    # Buscar fila con encabezados reales
    header_row = 1
    for i in range(min(8, len(raw))):
        row_text = " ".join(raw.iloc[i].astype(str).str.lower().tolist())
        score = sum(k in row_text for k in ["art padre", "id art", "modelo", "tiendas", "ventas netas", "dev pzs"])
        if score >= 2:
            header_row = i
            break

    df = pd.read_excel(file, sheet_name=hoja, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    df = consolidar_columnas_duplicadas(df)
    df = df.dropna(how="all")

    # Quitar columnas Unnamed vacías
    valid_cols = [c for c in df.columns if not str(c).lower().startswith("unnamed")]
    if valid_cols:
        df = df[valid_cols]

    col_tienda = buscar_columna(df, ["Tiendas", "Tienda", "Sucursal", "Ubicación", "Ubicacion"])
    col_modelo = buscar_columna(df, ["Modelo", "Modelo Proveedor"])
    col_categoria = buscar_columna(df, ["Categoria", "Categoría"])
    col_subcat = buscar_columna(df, ["Sub Categoria", "Sub Categoría", "Subcategoria", "Subcategoría"])
    col_dev = buscar_columna(df, ["Dev Pzs", "Dev_pzs", "Dev_Pzs"])
    col_vta = buscar_columna(df, ["Ventas Netas Pzs", "Vta_Pzs", "Vta Pzs"])
    col_imp = buscar_columna(df, ["Venta Neta en $", "Venta Neta $", "Vta_Imp", "Vta Imp"])
    col_costo = buscar_columna(df, ["Costo Devolución", "Costo Dev", "Costo_Dev"])
    col_id = buscar_columna(df, ["Id Art", "ID", "Id"])
    col_color = buscar_columna(df, ["Color"])

    out = pd.DataFrame()
    out["Mes_Origen"] = hoja
    out["Tienda"] = serie_columna(df, col_tienda, "Sin registros").apply(normalizar_texto) if col_tienda else pd.Series("Sin registros", index=df.index)
    out["Modelo"] = serie_columna(df, col_modelo, "Sin registros").apply(normalizar_texto) if col_modelo else pd.Series("Sin registros", index=df.index)
    out["Categoria"] = serie_columna(df, col_categoria, "Sin registros").apply(normalizar_texto) if col_categoria else pd.Series("Sin registros", index=df.index)
    out["Subcategoria"] = serie_columna(df, col_subcat, "Sin registros").apply(normalizar_texto) if col_subcat else pd.Series("Sin registros", index=df.index)
    out["Id Art"] = serie_columna(df, col_id, "Sin registros").apply(normalizar_texto) if col_id else pd.Series("Sin registros", index=df.index)
    out["Color"] = serie_columna(df, col_color, "Sin registros").apply(normalizar_texto) if col_color else pd.Series("Sin registros", index=df.index)
    out["Dev_Pzs"] = serie_columna(df, col_dev, 0).apply(to_num) if col_dev else pd.Series(0, index=df.index)
    out["Vta_Pzs"] = serie_columna(df, col_vta, 0).apply(to_num) if col_vta else pd.Series(0, index=df.index)
    out["Vta_Imp"] = serie_columna(df, col_imp, 0).apply(to_num) if col_imp else pd.Series(0, index=df.index)

    if col_costo:
        out["Costo_Dev"] = serie_columna(df, col_costo, 0).apply(to_num)
    else:
        # Si no existe costo, usamos Vta_Imp como base para evitar ruptura.
        out["Costo_Dev"] = out["Vta_Imp"]

    out["Piezas Vendidas Validadas"] = np.minimum(out["Vta_Pzs"], out["Dev_Pzs"])
    out["Conversión %"] = safe_div_series(out["Piezas Vendidas Validadas"], out["Dev_Pzs"]) * 100
    out["Valor Recuperado"] = out["Vta_Imp"]
    out["Valor Pendiente"] = out["Costo_Dev"] - out["Vta_Imp"]
    out["Recuperación %"] = safe_div_series(out["Valor Recuperado"], out["Costo_Dev"]) * 100

    return out, header_row, list(df.columns)

def procesar_excel(file):
    xls = pd.ExcelFile(file)
    hojas = xls.sheet_names
    hoja_operacion = detectar_hoja_productividad(hojas)
    hojas_mensuales = detectar_hojas_mensuales(hojas)

    diagnostics = {
        "hojas_detectadas": hojas,
        "hoja_operacion": hoja_operacion,
        "hojas_mensuales": hojas_mensuales,
        "encabezados_mensuales": {},
        "columnas_mensuales": {},
        "errores": []
    }

    if hoja_operacion:
        operacion = cargar_operacion(file, hoja_operacion)
        diagnostics["columnas_operacion"] = list(operacion.columns)
    else:
        operacion = pd.DataFrame()
        diagnostics["errores"].append("No se encontró hoja Resultados productividad.")

    comercial_list = []
    for hoja in hojas_mensuales:
        try:
            temp, header_row, cols = cargar_hoja_mensual(file, hoja)
            diagnostics["encabezados_mensuales"][hoja] = header_row
            diagnostics["columnas_mensuales"][hoja] = cols
            comercial_list.append(temp)
        except Exception as e:
            diagnostics["errores"].append(f"Error en hoja {hoja}: {e}")

    comercial = pd.concat(comercial_list, ignore_index=True) if comercial_list else pd.DataFrame()

    return operacion, comercial, diagnostics

def guardar_datos(operacion, comercial, diagnostics, filename):
    if not operacion.empty:
        operacion.to_parquet(OPERACION_PARQUET, index=False)
    if not comercial.empty:
        comercial.to_parquet(COMERCIAL_PARQUET, index=False)

    set_estado("ultima_actualizacion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    set_estado("archivo", filename)
    set_estado("diagnostico", json.dumps(diagnostics, ensure_ascii=False, default=str))

def cargar_persistido():
    operacion = pd.read_parquet(OPERACION_PARQUET) if OPERACION_PARQUET.exists() else pd.DataFrame()
    comercial = pd.read_parquet(COMERCIAL_PARQUET) if COMERCIAL_PARQUET.exists() else pd.DataFrame()
    return operacion, comercial

# -------------------------------
# HEADER
# -------------------------------
ultima = get_estado("ultima_actualizacion", "Sin actualización")
archivo_estado = get_estado("archivo", "Sin archivo cargado")
estado_info = "Disponible" if OPERACION_PARQUET.exists() or COMERCIAL_PARQUET.exists() else "Sin datos"
now = datetime.now()

st.markdown(f"""
<div class="orion-header">
    <div style="font-weight:800;letter-spacing:.08em;">PRICE SHOES | OPERACIONES ROPA</div>
    <div class="orion-title">🚀 ORION V2</div>
    <div class="orion-subtitle">Plataforma Indicadores de Recuperación de Mercancía</div>
    <div class="orion-mini">
        Productividad | Conversión | Recuperación Económica | Eficiencia Operativa<br>
        Fecha actual: {now.strftime('%Y-%m-%d')} | Hora actual: {now.strftime('%H:%M:%S')} |
        Última actualización: {ultima} | Estado de información: {estado_info}
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------
# SIDEBAR
# -------------------------------
with st.sidebar:
    st.header("🔐 Acceso")
    rol = st.radio("Rol", ["Consulta", "Administrador"], horizontal=True)
    is_admin = rol == "Administrador"

    if is_admin:
        clave = st.text_input("Clave administrador", type="password")
        is_admin = clave == st.secrets.get("ADMIN_PASSWORD", "orion_admin")

    st.divider()
    st.header("📂 Datos")

    if is_admin:
        uploaded = st.file_uploader("Cargar/Reemplazar Excel", type=["xlsx"])
        if uploaded is not None:
            try:
                operacion_new, comercial_new, diag = procesar_excel(uploaded)
                guardar_datos(operacion_new, comercial_new, diag, uploaded.name)
                st.success("Archivo procesado y guardado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo procesar el archivo: {e}")
                st.exception(e)
    else:
        st.caption("Modo consulta: no requiere cargar Excel.")

operacion, comercial = cargar_persistido()

if operacion.empty and comercial.empty:
    st.warning("No hay datos persistidos. Un administrador debe cargar el Excel por primera vez.")
    st.stop()

metas = get_metas()

# -------------------------------
# FILTROS GLOBALES
# -------------------------------
with st.sidebar:
    st.divider()
    st.header("🎛️ Filtros Globales")

    meses = sorted(set(operacion.get("Mes", pd.Series(dtype=str)).dropna().astype(str).tolist() + comercial.get("Mes_Origen", pd.Series(dtype=str)).dropna().astype(str).tolist()))
    semanas = sorted([int(x) for x in operacion.get("Semana ISO", pd.Series(dtype=float)).dropna().unique()]) if not operacion.empty and "Semana ISO" in operacion else []
    tiendas = TIENDAS_OFICIALES
    actividades = sorted(operacion.get("Actividad Realizada", pd.Series(dtype=str)).dropna().astype(str).unique()) if not operacion.empty else []
    categorias = sorted(comercial.get("Categoria", pd.Series(dtype=str)).dropna().astype(str).unique()) if not comercial.empty else []
    subcats = sorted(comercial.get("Subcategoria", pd.Series(dtype=str)).dropna().astype(str).unique()) if not comercial.empty else []
    modelos = sorted(comercial.get("Modelo", pd.Series(dtype=str)).dropna().astype(str).unique()) if not comercial.empty else []
    colaboradores = sorted(operacion.get("Nombre", pd.Series(dtype=str)).dropna().astype(str).unique()) if not operacion.empty else []
    ocurrencias = sorted(operacion.get("Ocurrencia", pd.Series(dtype=str)).dropna().astype(str).unique()) if not operacion.empty else []

    f_mes = st.multiselect("Mes", meses)
    f_semana = st.multiselect("Semana", semanas)
    f_tienda = st.multiselect("Tienda", tiendas)
    f_actividad = st.multiselect("Actividad", actividades)
    f_categoria = st.multiselect("Categoría", categorias)
    f_subcat = st.multiselect("Subcategoría", subcats)
    f_modelo = st.multiselect("Modelo", modelos)
    f_colaborador = st.multiselect("Colaborador", colaboradores)
    f_ocurrencia = st.multiselect("Ocurrencia", ocurrencias)

op = operacion.copy()
co = comercial.copy()

if f_mes:
    if not op.empty:
        op = op[op["Mes"].isin(f_mes)]
    if not co.empty:
        co = co[co["Mes_Origen"].isin(f_mes)]
if f_semana and not op.empty:
    op = op[op["Semana ISO"].isin(f_semana)]
if f_tienda:
    if not op.empty:
        op = op[op["Tienda"].isin(f_tienda)]
    if not co.empty:
        co = co[co["Tienda"].isin(f_tienda)]
if f_actividad and not op.empty:
    op = op[op["Actividad Realizada"].isin(f_actividad)]
if f_categoria and not co.empty:
    co = co[co["Categoria"].isin(f_categoria)]
if f_subcat and not co.empty:
    co = co[co["Subcategoria"].isin(f_subcat)]
if f_modelo and not co.empty:
    co = co[co["Modelo"].isin(f_modelo)]
if f_colaborador and not op.empty:
    op = op[op["Nombre"].isin(f_colaborador)]
if f_ocurrencia and not op.empty:
    op = op[op["Ocurrencia"].isin(f_ocurrencia)]

# -------------------------------
# KPI CALCULATIONS
# -------------------------------
total_ingresos = op["Ingresos"].sum() if not op.empty else 0
productividad = op["Productividad Total"].sum() if not op.empty else 0
recorridos = op["Recorridos"].sum() if not op.empty else 0
colaboradores_count = op["Nombre"].nunique() if not op.empty else 0

dev_pzs = co["Dev_Pzs"].sum() if not co.empty else 0
vta_pzs = co["Piezas Vendidas Validadas"].sum() if not co.empty else 0
vta_imp = co["Vta_Imp"].sum() if not co.empty else 0
costo_dev = co["Costo_Dev"].sum() if not co.empty else 0

conversion = pct(vta_pzs, dev_pzs)
recuperacion = pct(vta_imp, costo_dev)

hab_ing = pct(op["Habilitado"].sum(), op["Ingresos"].sum()) if not op.empty else 0
ubi_hab = pct(op["Ubicado"].sum(), op["Habilitado"].sum()) if not op.empty else 0
ubi_ing = pct(op["Ubicado"].sum(), op["Ingresos"].sum()) if not op.empty else 0

prod_meta_total = metas["productividad_diaria"] * max(colaboradores_count, 1)
prod_score = min(pct(productividad, prod_meta_total), 100)
hab_score = min(hab_ing, 100)
ubi_score = min(ubi_ing, 100)
conv_score = min(conversion, 100)
recorr_score = min(pct(recorridos, metas["recorridos_semanales"] * max(op["Tienda"].nunique() if not op.empty else 1, 1)), 100)

score_integral = round(prod_score*.40 + hab_score*.25 + ubi_score*.15 + conv_score*.10 + recorr_score*.10, 1)

# -------------------------------
# TOP KPIs
# -------------------------------
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Total Ingresos", f"{total_ingresos:,.0f}")
k2.metric("Conversión", f"{conversion:.1f}%")
k3.metric("Recuperación $", f"${vta_imp:,.0f}")
k4.metric("Productividad", f"{productividad:,.0f}")
k5.metric("Score Integral", f"{score_integral:.1f}/100")

# -------------------------------
# TABS
# -------------------------------
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
    st.caption(f"Archivo cargado: {archivo_estado} | Última actualización: {ultima}")

    c1,c2 = st.columns(2)

    tienda_op = op.groupby("Tienda", as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum")) if not op.empty else pd.DataFrame(columns=["Tienda","Productividad","Recorridos"])
    tienda_co = co.groupby("Tienda", as_index=False).agg(Recuperacion=("Vta_Imp","sum"), Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum")) if not co.empty else pd.DataFrame(columns=["Tienda","Recuperacion","Dev_Pzs","Vta_Pzs"])

    resumen = pd.DataFrame({"Tienda": TIENDAS_OFICIALES}).merge(tienda_op, on="Tienda", how="left").merge(tienda_co, on="Tienda", how="left").fillna(0)
    resumen["Conversión %"] = safe_div_series(resumen["Vta_Pzs"], resumen["Dev_Pzs"]) * 100
    resumen["Score"] = (
        resumen["Productividad"].rank(pct=True) * 40 +
        resumen["Recuperacion"].rank(pct=True) * 30 +
        resumen["Recorridos"].rank(pct=True) * 20 +
        resumen["Conversión %"].rank(pct=True) * 10
    ).round(1)
    resumen["Clasificación"] = np.select(
        [
            (resumen["Productividad"] > 0) & (resumen["Recuperacion"] > 0),
            (resumen["Productividad"] > 0) & (resumen["Recuperacion"] == 0),
            (resumen["Productividad"] == 0) & (resumen["Recuperacion"] > 0),
        ],
        [
            "🟢 Productividad + Recuperación",
            "🟡 Productividad sin Recuperación",
            "🟠 Recuperación sin Productividad",
        ],
        default="🔴 Sin registros"
    )

    with c1:
        st.write("Top 2 Tiendas")
        st.dataframe(resumen.sort_values("Score", ascending=False).head(2), width="stretch")
    with c2:
        st.write("Bottom 2 Tiendas")
        st.dataframe(resumen.sort_values("Score", ascending=True).head(2), width="stretch")

    c1,c2 = st.columns(2)
    colab = op.groupby("Nombre", as_index=False).agg(Productividad=("Productividad Total","sum")).sort_values("Productividad", ascending=False) if not op.empty else pd.DataFrame()
    with c1:
        st.write("Top 3 Colaboradores")
        st.dataframe(colab.head(3), width="stretch")
    with c2:
        st.write("Bottom 3 Colaboradores")
        st.dataframe(colab.tail(3), width="stretch")

    st.plotly_chart(px.bar(resumen, x="Tienda", y="Score", color="Clasificación", title="Score por tienda"), width="stretch")
    exportar("panel_ejecutivo", {"Resumen_Tiendas": resumen, "Colaboradores": colab})

# 2 Macro
with tab["2. Macro"]:
    st.subheader("Macro | Últimas semanas y meses")
    if not op.empty:
        sem = op.groupby("Semana ISO", as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum")).tail(4)
        st.dataframe(sem, width="stretch")
        st.plotly_chart(px.line(sem, x="Semana ISO", y=["Productividad","Recorridos"], markers=True), width="stretch")

    if not co.empty:
        mes = co.groupby("Mes_Origen", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum")).tail(3)
        mes["Conversión %"] = safe_div_series(mes["Vta_Pzs"], mes["Dev_Pzs"]) * 100
        st.dataframe(mes, width="stretch")
        st.plotly_chart(px.bar(mes, x="Mes_Origen", y=["Dev_Pzs","Vta_Pzs"]), width="stretch")

# 3 Conversión
with tab["3. Conversión"]:
    st.subheader("Conversión")
    if co.empty:
        st.warning("Sin datos comerciales.")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("Dev_Pzs", f"{dev_pzs:,.0f}")
        c2.metric("Vta_Pzs validada", f"{vta_pzs:,.0f}")
        c3.metric("Conversión", f"{conversion:.1f}%")

        df = co.groupby("Tienda", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"))
        df["Conversión %"] = safe_div_series(df["Vta_Pzs"], df["Dev_Pzs"]) * 100
        df = preparar_tiendas(df, ["Dev_Pzs", "Vta_Pzs", "Conversión %"])
        st.dataframe(df, width="stretch")
        st.plotly_chart(px.bar(df, x="Tienda", y="Conversión %", color="Estado"), width="stretch")

# 4 Recuperación
with tab["4. Recuperación Económica"]:
    st.subheader("Recuperación Económica")
    if co.empty:
        st.warning("Sin datos comerciales.")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("Valor Recuperado", f"${vta_imp:,.0f}")
        c2.metric("Costo Dev", f"${costo_dev:,.0f}")
        c3.metric("Valor Pendiente", f"${(costo_dev-vta_imp):,.0f}")

        df = co.groupby("Tienda", as_index=False).agg(Valor_Recuperado=("Vta_Imp","sum"), Costo_Dev=("Costo_Dev","sum"), Valor_Pendiente=("Valor Pendiente","sum"))
        df["Recuperación %"] = safe_div_series(df["Valor_Recuperado"], df["Costo_Dev"]) * 100
        df = preparar_tiendas(df, ["Valor_Recuperado", "Costo_Dev", "Valor_Pendiente", "Recuperación %"])
        st.dataframe(df, width="stretch")
        st.plotly_chart(px.bar(df, x="Tienda", y="Valor_Recuperado", color="Estado"), width="stretch")

# 5 Productividad colaborador
with tab["5. Productividad por Colaborador"]:
    st.subheader("Productividad por Colaborador")
    if op.empty:
        st.warning("Sin datos operativos.")
    else:
        df = op.groupby(["Nombre","Tienda"], as_index=False).agg(Productividad=("Productividad Total","sum"), Registros=("Nombre","count"))
        df["Meta"] = metas["productividad_diaria"]
        df["Cumplimiento %"] = safe_div_series(df["Productividad"], df["Meta"]) * 100
        st.dataframe(df.sort_values("Productividad", ascending=False), width="stretch")
        st.plotly_chart(px.bar(df.sort_values("Productividad", ascending=False).head(30), x="Nombre", y="Productividad", color="Tienda"), width="stretch")

# 6 Productividad actividad
with tab["6. Productividad por Actividad"]:
    st.subheader("Productividad por Actividad")
    if op.empty:
        st.warning("Sin datos operativos.")
    else:
        df = op.groupby("Actividad Realizada", as_index=False).agg(Productividad=("Productividad Total","sum"), Piezas=("Número de Piezas","sum"))
        st.dataframe(df.sort_values("Productividad", ascending=False), width="stretch")
        st.plotly_chart(px.pie(df, names="Actividad Realizada", values="Productividad", hole=.45), width="stretch")

# 7 Eficiencia
with tab["7. Eficiencia Operativa"]:
    st.subheader("Eficiencia Operativa")
    c1,c2,c3 = st.columns(3)
    c1.metric("Habilitado / Ingresos", f"{hab_ing:.1f}%")
    c2.metric("Ubicado / Habilitado", f"{ubi_hab:.1f}%")
    c3.metric("Ubicado / Ingresos", f"{ubi_ing:.1f}%")

    if not op.empty:
        df = op.groupby("Tienda", as_index=False).agg(Ingresos=("Ingresos","sum"), Habilitado=("Habilitado","sum"), Ubicado=("Ubicado","sum"))
        df["Habilitado / Ingresos"] = safe_div_series(df["Habilitado"], df["Ingresos"]) * 100
        df["Ubicado / Habilitado"] = safe_div_series(df["Ubicado"], df["Habilitado"]) * 100
        df["Ubicado / Ingresos"] = safe_div_series(df["Ubicado"], df["Ingresos"]) * 100
        df = preparar_tiendas(df, ["Ingresos", "Habilitado", "Ubicado", "Habilitado / Ingresos", "Ubicado / Habilitado", "Ubicado / Ingresos"])
        st.dataframe(df, width="stretch")

# 8 Recorridos
with tab["8. Cumplimiento de Recorridos"]:
    st.subheader("Cumplimiento de Recorridos por Tienda")
    if op.empty:
        st.warning("Sin recorridos.")
    else:
        df = op.groupby("Tienda", as_index=False).agg(Recorridos=("Recorridos","sum"))
        df = preparar_tiendas(df, ["Recorridos"])
        df["Meta Semanal"] = metas["recorridos_semanales"]
        df["Cumplimiento %"] = safe_div_series(df["Recorridos"], df["Meta Semanal"]) * 100
        df["Estatus"] = np.where(df["Cumplimiento %"] >= 100, "🟢 Cumple", np.where(df["Cumplimiento %"] >= 80, "🟡 Atención", "🔴 Bajo"))
        st.dataframe(df.sort_values("Cumplimiento %", ascending=False), width="stretch")
        st.plotly_chart(px.bar(df, x="Tienda", y="Cumplimiento %", color="Estatus"), width="stretch")

# 9 Diarios
with tab["9. Indicadores Diarios"]:
    st.subheader("Indicadores Diarios")
    if op.empty:
        st.warning("Sin datos.")
    else:
        df = op.groupby(["Fecha","Tienda","Ocurrencia","Nombre"], as_index=False).agg(
            Ingresos=("Ingresos","sum"),
            Habilitado=("Habilitado","sum"),
            Ubicado=("Ubicado","sum"),
            Recorridos=("Recorridos","sum")
        )
        df["Habilitado / Ingresos"] = safe_div_series(df["Habilitado"], df["Ingresos"]) * 100
        df["Ubicado / Habilitado"] = safe_div_series(df["Ubicado"], df["Habilitado"]) * 100
        df["Ubicado / Ingresos"] = safe_div_series(df["Ubicado"], df["Ingresos"]) * 100
        df["Meta"] = metas["recorridos_semanales"] / 7
        df["Cumplimiento %"] = safe_div_series(df["Recorridos"], df["Meta"]) * 100
        st.dataframe(df, width="stretch")

# 10 Top 30 Modelos
with tab["10. Top 30 Modelos"]:
    st.subheader("Top 30 Modelos")
    if co.empty:
        st.warning("Sin datos de modelos.")
    else:
        df = co.groupby(["Modelo","Categoria","Subcategoria"], as_index=False).agg(
            Dev_Pzs=("Dev_Pzs","sum"),
            Vta_Pzs=("Piezas Vendidas Validadas","sum"),
            Recuperacion_Dinero=("Vta_Imp","sum"),
            Costo_Dev=("Costo_Dev","sum")
        )
        df["Recuperación %"] = safe_div_series(df["Recuperacion_Dinero"], df["Costo_Dev"]) * 100
        df["Valor Pendiente"] = df["Costo_Dev"] - df["Recuperacion_Dinero"]
        criterio = st.selectbox("Ranking", ["Mayor recuperación económica", "Mayor recuperación %", "Mayor venta", "Mayor pendiente"])
        col = {
            "Mayor recuperación económica": "Recuperacion_Dinero",
            "Mayor recuperación %": "Recuperación %",
            "Mayor venta": "Vta_Pzs",
            "Mayor pendiente": "Valor Pendiente"
        }[criterio]
        top = df.sort_values(col, ascending=False).head(30)
        st.dataframe(top, width="stretch")
        st.plotly_chart(px.bar(top, x="Modelo", y=col, color="Categoria"), width="stretch")

# 11 Categoria
with tab["11. Análisis por Categoría"]:
    st.subheader("Análisis por Categoría")
    if co.empty:
        st.warning("Sin datos.")
    else:
        df = co.groupby("Categoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum"))
        df["Conversión %"] = safe_div_series(df["Vta_Pzs"], df["Dev_Pzs"]) * 100
        st.dataframe(df.sort_values("Recuperacion", ascending=False), width="stretch")
        st.plotly_chart(px.bar(df, x="Categoria", y="Recuperacion"), width="stretch")

# 12 Subcategoria
with tab["12. Análisis por Subcategoría"]:
    st.subheader("Análisis por Subcategoría")
    if co.empty:
        st.warning("Sin datos.")
    else:
        df = co.groupby("Subcategoria", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum"))
        df["Conversión %"] = safe_div_series(df["Vta_Pzs"], df["Dev_Pzs"]) * 100
        st.dataframe(df.sort_values("Recuperacion", ascending=False), width="stretch")
        st.plotly_chart(px.bar(df.head(30), x="Subcategoria", y="Recuperacion"), width="stretch")

# 13 Ranking Tiendas
with tab["13. Ranking de Tiendas"]:
    st.subheader("Ranking de Tiendas")
    tienda_op = op.groupby("Tienda", as_index=False).agg(Productividad=("Productividad Total","sum"), Recorridos=("Recorridos","sum"), Habilitado=("Habilitado","sum"), Ingresos=("Ingresos","sum"), Ubicado=("Ubicado","sum")) if not op.empty else pd.DataFrame(columns=["Tienda","Productividad","Recorridos","Habilitado","Ingresos","Ubicado"])
    tienda_co = co.groupby("Tienda", as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Piezas Vendidas Validadas","sum"), Recuperacion=("Vta_Imp","sum")) if not co.empty else pd.DataFrame(columns=["Tienda","Dev_Pzs","Vta_Pzs","Recuperacion"])
    df = pd.DataFrame({"Tienda": TIENDAS_OFICIALES}).merge(tienda_op, on="Tienda", how="left").merge(tienda_co, on="Tienda", how="left").fillna(0)
    df["Conversión %"] = safe_div_series(df["Vta_Pzs"], df["Dev_Pzs"]) * 100
    df["Score"] = (
        df["Productividad"].rank(pct=True) * 40 +
        df["Habilitado"].rank(pct=True) * 25 +
        df["Ubicado"].rank(pct=True) * 15 +
        df["Conversión %"].rank(pct=True) * 10 +
        df["Recorridos"].rank(pct=True) * 10
    ).round(1)
    df["Clasificación"] = np.select(
        [
            (df["Productividad"] > 0) & (df["Recuperacion"] > 0),
            (df["Productividad"] > 0) & (df["Recuperacion"] == 0),
            (df["Productividad"] == 0) & (df["Recuperacion"] > 0),
        ],
        [
            "🟢 Productividad + Recuperación",
            "🟡 Productividad sin Recuperación",
            "🟠 Recuperación sin Productividad",
        ],
        default="🔴 Sin registros"
    )
    st.dataframe(df.sort_values("Score", ascending=False), width="stretch")
    st.plotly_chart(px.bar(df.sort_values("Score", ascending=False), x="Tienda", y="Score", color="Clasificación"), width="stretch")

# 14 Ranking Colaboradores
with tab["14. Ranking de Colaboradores"]:
    st.subheader("Ranking de Colaboradores")
    if op.empty:
        st.warning("Sin datos.")
    else:
        df = op.groupby("Nombre", as_index=False).agg(Productividad=("Productividad Total","sum"), Registros=("Nombre","count"), Recorridos=("Recorridos","sum"))
        df["Score"] = (
            df["Productividad"].rank(pct=True) * 70 +
            df["Registros"].rank(pct=True) * 20 +
            df["Recorridos"].rank(pct=True) * 10
        ).round(1)
        st.dataframe(df.sort_values("Score", ascending=False), width="stretch")

# 15 Índice
with tab["15. Índice Integral"]:
    st.subheader("Índice Integral ORION")
    st.metric("Score Integral", f"{score_integral:.1f}/100")
    st.progress(min(score_integral / 100, 1))
    st.write("Score = 40% Productividad + 25% Habilitado + 15% Ubicado + 10% Conversión + 10% Cumplimiento de Recorridos")

# 16 Alertas
with tab["16. Alertas Inteligentes"]:
    st.subheader("Alertas Inteligentes")
    alertas = []

    if conversion < metas["conversion"]:
        alertas.append(["Conversión", "Alta", f"Conversión menor a meta: {conversion:.1f}% vs {metas['conversion']:.1f}%"])
    if recuperacion < metas["recuperacion"]:
        alertas.append(["Recuperación", "Alta", f"Recuperación menor a meta: {recuperacion:.1f}% vs {metas['recuperacion']:.1f}%"])
    if prod_score < 80:
        alertas.append(["Productividad", "Media", f"Productividad debajo del 80% de meta calculada: {prod_score:.1f}%"])
    if recorr_score < 80:
        alertas.append(["Recorridos", "Media", f"Recorridos debajo del 80% de meta: {recorr_score:.1f}%"])

    tiendas_op = set(op[op["Productividad Total"] > 0]["Tienda"].unique()) if not op.empty else set()
    tiendas_co = set(co[co["Vta_Imp"] > 0]["Tienda"].unique()) if not co.empty else set()
    for t in TIENDAS_OFICIALES:
        if t not in tiendas_op and t not in tiendas_co:
            alertas.append(["Tienda sin registros", "Alta", f"{t} no tiene registros."])
        elif t in tiendas_op and t not in tiendas_co:
            alertas.append(["Productividad sin recuperación", "Media", f"{t} tiene productividad sin recuperación."])

    alert_df = pd.DataFrame(alertas, columns=["Tipo", "Prioridad", "Alerta"])
    if alert_df.empty:
        st.success("Sin alertas críticas.")
    else:
        st.dataframe(alert_df, width="stretch")

# 17 Configuración
if "17. Configuración de Metas" in tab:
    with tab["17. Configuración de Metas"]:
        st.subheader("⚙️ Configuración de Metas")
        st.caption("Visible únicamente para administradores.")
        cols = st.columns(3)
        nuevos = {}
        for i, (k, v) in enumerate(metas.items()):
            with cols[i % 3]:
                nuevos[k] = st.number_input(k, value=float(v), step=1.0)

        if st.button("Guardar metas"):
            for k, v in nuevos.items():
                if float(v) != float(metas[k]):
                    update_meta(k, v)
            st.success("Metas actualizadas correctamente.")
            st.rerun()

        st.write("Historial de metas")
        st.dataframe(get_historial(), width="stretch")

# 18 Diagnóstico
if "18. Diagnóstico de Datos" in tab:
    with tab["18. Diagnóstico de Datos"]:
        st.subheader("Diagnóstico de Datos")
        diag_raw = get_estado("diagnostico", "{}")
        try:
            diag = json.loads(diag_raw)
        except Exception:
            diag = {}

        st.write("Hojas detectadas")
        st.json(diag.get("hojas_detectadas", []))

        st.write("Hoja operativa")
        st.json(diag.get("hoja_operacion", ""))

        st.write("Hojas mensuales")
        st.json(diag.get("hojas_mensuales", []))

        st.write("Encabezados mensuales utilizados")
        st.json(diag.get("encabezados_mensuales", {}))

        st.write("Columnas operación")
        st.json(diag.get("columnas_operacion", []))

        st.write("Columnas mensuales")
        st.json(diag.get("columnas_mensuales", {}))

        st.write("Errores detectados")
        st.json(diag.get("errores", []))

        c1,c2,c3 = st.columns(3)
        c1.metric("Registros operación", f"{len(operacion):,.0f}")
        c2.metric("Registros comercial", f"{len(comercial):,.0f}")
        c3.metric("Duplicados operación", f"{operacion.duplicated().sum() if not operacion.empty else 0:,.0f}")

        if not operacion.empty:
            st.write("Valores nulos operación")
            st.dataframe(operacion.isna().sum().reset_index().rename(columns={"index": "Columna", 0: "Nulos"}), width="stretch")

# 19 Compartir
with tab["19. Compartir ORION"]:
    st.subheader("Compartir ORION")
    st.write("URL de la aplicación:")
    st.code("https://operaciones-ropa.streamlit.app")
    st.write(f"Fecha de actualización: {ultima}")
    st.write(f"Archivo cargado: {archivo_estado}")
    st.info("Los usuarios consulta visualizan la información persistida sin cargar Excel.")

st.markdown("""
<div class="confidencial">
<b>CONFIDENCIAL</b><br>
La información contenida en esta plataforma es propiedad de Price Shoes y está destinada exclusivamente para uso interno de Operaciones Ropa.
Queda prohibida su reproducción, distribución o divulgación sin autorización expresa de la Dirección correspondiente.<br>
© Price Shoes | Operaciones Ropa
</div>
""", unsafe_allow_html=True)
