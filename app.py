import streamlit as st
import traceback
from pathlib import Path

st.set_page_config(page_title="Diagnóstico ORION Main", page_icon="🧪", layout="wide")

st.success("✅ app.py está cargando correctamente")
st.write("Ahora vamos a validar `orion_main.py` sin ejecutar toda la app de golpe.")

main_file = Path("orion_main.py")

if not main_file.exists():
    st.error("No existe orion_main.py en la raíz del repositorio.")
    st.stop()

code_text = main_file.read_text(encoding="utf-8")
st.write("Tamaño de orion_main.py:", f"{len(code_text):,} caracteres")

try:
    compiled = compile(code_text, "orion_main.py", "exec")
    st.success("✅ orion_main.py compila correctamente. No es error de sintaxis.")
except Exception:
    st.error("❌ Error de sintaxis/compilación en orion_main.py")
    st.code(traceback.format_exc(), language="python")
    st.stop()

st.warning("Presiona el botón para ejecutar ORION. Si falla, aquí debe aparecer el error exacto.")

if st.button("🚀 Ejecutar ORION ahora"):
    try:
        exec(compiled, globals())
    except BaseException:
        st.error("❌ ORION falló al ejecutarse. Copia este error completo.")
        st.code(traceback.format_exc(), language="python")
        st.stop()
else:
    st.info("Aún no se ejecutó ORION. Presiona el botón para obtener el error exacto sin que Streamlit lo oculte.")
