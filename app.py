import streamlit as st
import sys
import os
from pathlib import Path

st.set_page_config(page_title="Diagnóstico ORION", page_icon="✅", layout="wide")

st.success("✅ Streamlit sí está leyendo este app.py correctamente")

st.write("Python:", sys.version)
st.write("Carpeta actual:", os.getcwd())

st.subheader("Archivos encontrados en la raíz")
st.write([p.name for p in Path(".").iterdir()])

st.info("Si ves esta pantalla, el despliegue funciona. El problema está dentro de orion_main.py. Si sigues viendo 'Oh no', Streamlit NO está leyendo este app.py o falló la instalación de requirements.")
