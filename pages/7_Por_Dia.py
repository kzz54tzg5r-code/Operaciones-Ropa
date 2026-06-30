import streamlit as st
import pandas as pd
from modules.ui import setup_page, header, kpi, pct, money
from modules.auth import require_login
from modules.indicadores import compute_summary, by_store, by_person
from modules.settings import load_settings

setup_page('ORION PRO')
user = require_login()
op = st.session_state.get('op', pd.DataFrame())
com = st.session_state.get('com', pd.DataFrame())
header()

if op.empty and com.empty:
    st.warning('Primero carga el Excel en la página principal app.py.')
    st.stop()

page = __file__.split('/')[-1].replace('.py','').replace('_',' ')
st.title(page)
summary = compute_summary(op, com)

if 'Panel' in page:
    c = st.columns(4)
    with c[0]: kpi('Conversión', pct(summary['conversion_pct']))
    with c[1]: kpi('Recuperación $', money(summary['venta_imp']))
    with c[2]: kpi('Habilitado', f"{summary['habilitado']:,.0f}")
    with c[3]: kpi('Ubicado', f"{summary['ubicado']:,.0f}")
    st.dataframe(by_store(op), use_container_width=True)
elif 'Productividad' in page:
    st.dataframe(by_person(op), use_container_width=True)
elif 'Conversion' in page or 'Conversión' in page:
    st.metric('Dev Pzs', f"{summary['dev_pzs']:,.0f}")
    st.metric('Vta Pzs', f"{summary['vta_pzs']:,.0f}")
    st.metric('Conversión', pct(summary['conversion_pct']))
elif 'Recorridos' in page:
    metas = load_settings()
    st.metric('Recorridos reales', f"{summary['recorridos']:,.0f}")
    st.metric('Meta semanal', metas.get('meta_recorridos_semanal', 47))
elif 'Rankings' in page:
    st.dataframe(by_store(op).sort_values(by_store(op).columns[-1], ascending=False), use_container_width=True)
elif 'Macro' in page:
    if 'Semana' in op.columns:
        st.dataframe(op.groupby('Semana', as_index=False).size().rename(columns={'size':'Registros'}), use_container_width=True)
    else:
        st.info('No se encontró columna Semana.')
elif 'Por Dia' in page or 'Por Día' in page:
    if 'Fecha' in op.columns:
        st.dataframe(op.groupby(op['Fecha'].dt.date, as_index=False).size().rename(columns={'Fecha':'Fecha','size':'Registros'}), use_container_width=True)
    else:
        st.info('No se encontró columna Fecha.')
elif 'Configuracion' in page or 'Configuración' in page:
    metas = load_settings()
    st.json(metas)
    if user['role'] != 'Administrador':
        st.info('Sólo Administrador puede modificar metas.')
else:
    st.dataframe(op.head(200), use_container_width=True)
