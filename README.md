# ORION APP13 - Fix Oh No por components.html

Cambio:
- Se eliminó el uso de `components.html(...)`.
- El header se renderiza con `st.markdown(..., unsafe_allow_html=True)`.
- Esto evita el aviso/fallo por `st.components.v1.html` en Streamlit 1.58.

Mantiene:
- Diseño APP13 completo.
- Pestañas anteriores.
- PDF y detalle de registros del último ZIP.
