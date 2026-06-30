import streamlit as st
import pandas as pd
from modules.ui import setup_page, header, kpi, money, pct
from modules.auth import require_login
from modules.loader import read_excel
from modules.indicadores import compute_summary, by_store, by_person
from modules.pdf import create_simple_pdf

setup_page('ORION PRO v3')
user = require_login()
header('Panel Ejecutivo Nacional')

st.sidebar.markdown('---')
uploaded = st.sidebar.file_uploader('Carga tu Excel de operación', type=['xlsx','xls'])

if uploaded:
    op, com, sheets = read_excel(uploaded)
    st.session_state['op'] = op
    st.session_state['com'] = com
    st.sidebar.success(f'Archivo cargado · {len(sheets)} hojas')
else:
    op = st.session_state.get('op', pd.DataFrame())
    com = st.session_state.get('com', pd.DataFrame())

if op.empty and com.empty:
    st.info('Carga tu archivo Excel desde el menú lateral para iniciar el análisis.')
    st.stop()

summary = compute_summary(op, com)
cols = st.columns(4)
with cols[0]: kpi('Conversión Dev→Venta', pct(summary['conversion_pct']))
with cols[1]: kpi('Recuperación económica', money(summary['venta_imp']))
with cols[2]: kpi('Piezas habilitadas', f"{summary['habilitado']:,.0f}")
with cols[3]: kpi('Piezas ubicadas', f"{summary['ubicado']:,.0f}")

st.subheader('Resumen por tienda')
st.dataframe(by_store(op), use_container_width=True)

st.subheader('Productividad por colaborador')
st.dataframe(by_person(op).head(20), use_container_width=True)

pdf = create_simple_pdf('ORION PRO - Resumen Ejecutivo', summary)
st.download_button('Descargar resumen PDF', data=pdf, file_name='orion_resumen.pdf', mime='application/pdf')
