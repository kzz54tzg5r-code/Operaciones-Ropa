# ORION APP13 - Cloud Safe Lazy Tabs

Mantiene el diseño APP13 y las pestañas completas, pero cambia la navegación para que sólo se renderice una pestaña a la vez.

Motivo:
Streamlit Cloud estaba mostrando "Oh no" sin traceback. Los logs no muestran excepción, lo que indica caída de sesión/proceso por carga pesada al renderizar todas las pestañas al mismo tiempo.

Cambios:
- st.tabs reemplazado por navegación horizontal con st.radio.
- Sólo se ejecuta/renderiza la pestaña seleccionada.
- components.html eliminado.
- app.py captura BaseException para mostrar traceback si existe.
- Mantiene PDF y detalle de registros del último paquete.
