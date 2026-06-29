import streamlit as st
import traceback
import sys
import os
import time
import faulthandler
from pathlib import Path

st.set_page_config(
    page_title="ORION Diagnóstico Runtime",
    page_icon="🧪",
    layout="wide"
)

try:
    faulthandler.enable()
except Exception:
    pass

ERROR_FILE = Path("orion_runtime_error.txt")

def show_last_error():
    if ERROR_FILE.exists():
        st.error("Último error guardado en ejecución anterior:")
        st.code(ERROR_FILE.read_text(encoding="utf-8", errors="replace"), language="python")

with st.sidebar:
    st.markdown("### 🧪 Diagnóstico")
    st.caption("Esta versión muestra el error real si ORION falla durante filtros o recálculos.")
    if st.button("🧹 Limpiar error guardado"):
        try:
            ERROR_FILE.unlink(missing_ok=True)
            st.success("Error guardado eliminado.")
        except Exception as e:
            st.warning(str(e))
    show_last_error()

try:
    st.session_state["_orion_debug_last_step"] = "Leyendo orion_main.py"
    main_path = Path("orion_main.py")

    if not main_path.exists():
        raise FileNotFoundError("No existe orion_main.py en la raíz del repositorio.")

    code_text = main_path.read_text(encoding="utf-8")

    st.session_state["_orion_debug_last_step"] = "Compilando orion_main.py"
    code = compile(code_text, "orion_main.py", "exec")

    st.session_state["_orion_debug_last_step"] = "Ejecutando orion_main.py"
    exec(code, globals())

except BaseException:
    tb = traceback.format_exc()
    step = st.session_state.get("_orion_debug_last_step", "Paso no identificado")
    msg = (
        "ORION FALLÓ EN TIEMPO DE EJECUCIÓN\n"
        f"Paso: {step}\n"
        f"Python: {sys.version}\n"
        f"Carpeta: {os.getcwd()}\n"
        f"Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        + tb
    )

    try:
        ERROR_FILE.write_text(msg, encoding="utf-8")
    except Exception:
        pass

    st.error("La app falló. Copia este error completo y envíalo.")
    st.code(msg, language="python")
    st.stop()
