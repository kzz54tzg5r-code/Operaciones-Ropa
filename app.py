import streamlit as st
import traceback
import sys
import os
from pathlib import Path

st.set_page_config(
    page_title="ORION Safe Start",
    page_icon="🧪",
    layout="wide"
)

st.success("✅ ORION Safe Start cargó correctamente")
st.write("Versión: APP13_SAFE_START_DEBUG")
st.write("Python:", sys.version)
st.write("Carpeta:", os.getcwd())

st.info("Esta versión NO ejecuta ORION automáticamente. Primero valida que Streamlit cargue, y luego lo ejecuta con captura de error.")

main_path = Path("orion_main.py")
if not main_path.exists():
    st.error("No existe orion_main.py en la raíz.")
    st.stop()

st.write("orion_main.py encontrado:", f"{main_path.stat().st_size:,} bytes")

try:
    code_text = main_path.read_text(encoding="utf-8")
    compiled = compile(code_text, "orion_main.py", "exec")
    st.success("✅ orion_main.py compila correctamente.")
except BaseException:
    st.error("❌ Error al compilar orion_main.py")
    st.code(traceback.format_exc(), language="python")
    st.stop()

st.warning("Presiona el botón para ejecutar ORION. Si falla, aquí debe aparecer el error exacto.")

if st.button("🚀 Ejecutar ORION con diagnóstico", type="primary"):
    try:
        exec(compiled, globals())
    except BaseException:
        st.error("❌ ORION falló durante ejecución. Copia este error completo.")
        st.code(traceback.format_exc(), language="python")
        st.stop()
else:
    st.stop()
