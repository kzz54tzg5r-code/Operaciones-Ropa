import streamlit as st
import traceback

st.set_page_config(
    page_title="Recuperación Cambios y Muertos",
    page_icon="🚀",
    layout="wide"
)

try:
    with open("orion_main.py", "r", encoding="utf-8") as f:
        code = compile(f.read(), "orion_main.py", "exec")
    exec(code, globals())
except BaseException:
    st.error("La app no pudo iniciar o se detuvo. Copia este error y envíalo para corregirlo exacto.")
    st.code(traceback.format_exc(), language="python")
    st.stop()
