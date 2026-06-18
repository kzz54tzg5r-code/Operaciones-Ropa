import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="ORION",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 ORION")
st.subheader("Plataforma de Indicadores de Recuperación de Mercancía")
st.caption("Operaciones Ropa")

archivo = st.file_uploader("📂 Carga tu archivo Excel", type=["xlsx"])

if archivo is None:
    st.info("Por favor cargue un archivo Excel para iniciar ORION.")
    st.stop()

try:
    xls = pd.ExcelFile(archivo)
    hojas = xls.sheet_names
except Exception as e:
    st.error(f"No se pudo leer el archivo Excel: {e}")
    st.stop()

st.success("Archivo cargado correctamente")

hoja_productividad = None
for hoja in hojas:
    if "productividad" in hoja.lower():
        hoja_productividad = hoja
        break

if hoja_productividad is None:
    hoja_productividad = st.selectbox("Selecciona la hoja principal", hojas)
else:
    st.info(f"Hoja principal detectada: {hoja_productividad}")

try:
    df = pd.read_excel(archivo, sheet_name=hoja_productividad)
except Exception as e:
    st.error(f"No se pudo leer la hoja seleccionada: {e}")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]

if "nombre" in df.columns and "Nombre" not in df.columns:
    df = df.rename(columns={"nombre": "Nombre"})

columnas_necesarias = [
    "Fecha",
    "Ubicación",
    "Actividad Realizada",
    "Área",
    "Número de Piezas",
    "Nombre",
    "Motivo de ingreso",
    "Recorridos"
]

for col in columnas_necesarias:
    if col not in df.columns:
        df[col] = np.nan

df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
df["Número de Piezas"] = pd.to_numeric(df["Número de Piezas"], errors="coerce").fillna(0)
df["Recorridos"] = pd.to_numeric(df["Recorridos"], errors="coerce").fillna(0)

df["Ubicación"] = df["Ubicación"].fillna("SIN DATO").astype(str)
df["Actividad Realizada"] = df["Actividad Realizada"].fillna("SIN DATO").astype(str)
df["Área"] = df["Área"].fillna("SIN DATO").astype(str)
df["Nombre"] = df["Nombre"].fillna("SIN DATO").astype(str)
df["Motivo de ingreso"] = df["Motivo de ingreso"].fillna("SIN DATO").astype(str)

df["Semana"] = df["Fecha"].dt.isocalendar().week
df["Mes"] = df["Fecha"].dt.month_name()

st.sidebar.header("Filtros")

tiendas = sorted(df["Ubicación"].dropna().unique())
actividades = sorted(df["Actividad Realizada"].dropna().unique())
colaboradores = sorted(df["Nombre"].dropna().unique())

f_tienda = st.sidebar.multiselect("Tienda / Ubicación", tiendas)
f_actividad = st.sidebar.multiselect("Actividad", actividades)
f_colaborador = st.sidebar.multiselect("Colaborador", colaboradores)

df_filtrado = df.copy()

if f_tienda:
    df_filtrado = df_filtrado[df_filtrado["Ubicación"].isin(f_tienda)]

if f_actividad:
    df_filtrado = df_filtrado[df_filtrado["Actividad Realizada"].isin(f_actividad)]

if f_colaborador:
    df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(f_colaborador)]

piezas = df_filtrado["Número de Piezas"].sum()
registros = len(df_filtrado)
colabs = df_filtrado["Nombre"].nunique()
recorridos = df_filtrado["Recorridos"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Piezas", f"{piezas:,.0f}")
c2.metric("🧾 Registros", f"{registros:,.0f}")
c3.metric("👤 Colaboradores", f"{colabs:,.0f}")
c4.metric("🚶 Recorridos", f"{recorridos:,.0f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Panel Ejecutivo",
    "Productividad",
    "Recorridos",
    "Rankings",
    "Base de Datos"
])

with tab1:
    st.subheader("📊 Panel Ejecutivo")

    resumen_tienda = df_filtrado.groupby("Ubicación", as_index=False).agg(
        Piezas=("Número de Piezas", "sum"),
        Registros=("Número de Piezas", "count"),
        Recorridos=("Recorridos", "sum"),
        Colaboradores=("Nombre", "nunique")
    ).sort_values("Piezas", ascending=False)

    st.dataframe(resumen_tienda, use_container_width=True)

    if not resumen_tienda.empty:
        fig = px.bar(
            resumen_tienda.head(20),
            x="Ubicación",
            y="Piezas",
            title="Piezas por tienda"
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("👤 Productividad por colaborador")

    prod_colab = df_filtrado.groupby("Nombre", as_index=False).agg(
        Piezas=("Número de Piezas", "sum"),
        Registros=("Número de Piezas", "count")
    ).sort_values("Piezas", ascending=False)

    st.dataframe(prod_colab, use_container_width=True)

    if not prod_colab.empty:
        fig = px.bar(
            prod_colab.head(30),
            x="Nombre",
            y="Piezas",
            title="Top colaboradores por piezas"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Productividad por actividad")

    prod_act = df_filtrado.groupby("Actividad Realizada", as_index=False).agg(
        Piezas=("Número de Piezas", "sum")
    ).sort_values("Piezas", ascending=False)

    st.dataframe(prod_act, use_container_width=True)

with tab3:
    st.subheader("🚶 Cumplimiento de recorridos")

    meta_recorridos = st.number_input("Meta de recorridos", min_value=1, value=47)

    rec_tienda = df_filtrado.groupby("Ubicación", as_index=False).agg(
        Recorridos=("Recorridos", "sum")
    )

    rec_tienda["Meta"] = meta_recorridos
    rec_tienda["Cumplimiento %"] = np.where(
        rec_tienda["Meta"] > 0,
        rec_tienda["Recorridos"] / rec_tienda["Meta"] * 100,
        0
    )

    rec_tienda["Estatus"] = np.where(
        rec_tienda["Cumplimiento %"] >= 100,
        "🟢 Cumple",
        np.where(rec_tienda["Cumplimiento %"] >= 80, "🟡 Atención", "🔴 Bajo")
    )

    st.dataframe(rec_tienda.sort_values("Cumplimiento %", ascending=False), use_container_width=True)

with tab4:
    st.subheader("🏆 Ranking ORION")

    ranking = df_filtrado.groupby("Ubicación", as_index=False).agg(
        Piezas=("Número de Piezas", "sum"),
        Recorridos=("Recorridos", "sum"),
        Colaboradores=("Nombre", "nunique"),
        Registros=("Número de Piezas", "count")
    )

    if not ranking.empty:
        ranking["Score"] = (
            ranking["Piezas"].rank(pct=True) * 60 +
            ranking["Recorridos"].rank(pct=True) * 25 +
            ranking["Registros"].rank(pct=True) * 15
        ).round(1)

        ranking["Nivel"] = np.where(
            ranking["Score"] >= 80,
            "🟢 Alto",
            np.where(ranking["Score"] >= 60, "🟡 Medio", "🔴 Bajo")
        )

        ranking = ranking.sort_values("Score", ascending=False)

    st.dataframe(ranking, use_container_width=True)

with tab5:
    st.subheader("🧾 Base de datos cargada")
    st.dataframe(df_filtrado, use_container_width=True)

    st.download_button(
        "⬇️ Descargar base filtrada CSV",
        data=df_filtrado.to_csv(index=False).encode("utf-8-sig"),
        file_name="orion_base_filtrada.csv",
        mime="text/csv"
    )
