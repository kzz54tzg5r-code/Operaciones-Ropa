# ORION APP13 - Estabilización sin rerun

Base: ORION_APP13_FIX_ARRANQUE_GITHUB.

Objetivo:
- Evitar que Streamlit se caiga al filtrar tiendas del proyecto.

Cambios:
- Se eliminaron todos los st.rerun()/st.experimental_rerun().
- El guardado de tiendas del proyecto ya no fuerza recarga automática.
- Las tiendas del proyecto se guardan en session_state y persistencia.
- Filtros globales ya no seleccionan semana por defecto para reducir recálculos.
- Acceso visible sólo Consulta y Administrador.
- Margen superior para evitar cortes visuales.

Nota:
Después de guardar tiendas del proyecto, cambia de pestaña o actualiza la página una sola vez si necesitas ver el cambio aplicado al instante.
