import streamlit as st

BLUE = '#3366CC'
PINK = '#FF99FF'

def setup_page(title='ORION PRO'):
    st.set_page_config(page_title=title, page_icon='📊', layout='wide')
    st.markdown(f'''
    <style>
    .main .block-container {{padding-top: 1.2rem;}}
    .orion-header {{background: linear-gradient(90deg,{BLUE},#6D7CFF,{PINK}); padding:18px; border-radius:18px; color:white; margin-bottom:18px;}}
    .kpi-card {{background:#fff; border:1px solid #E5E7EB; border-radius:16px; padding:16px; box-shadow:0 4px 14px rgba(0,0,0,.06);}}
    .kpi-title {{font-size:13px; color:#64748B;}}
    .kpi-value {{font-size:28px; font-weight:800; color:#111827;}}
    </style>
    ''', unsafe_allow_html=True)

def header(subtitle='Operaciones Ropa'):
    st.markdown(f'<div class="orion-header"><h1>📊 ORION PRO</h1><p>Plataforma Indicadores de Recuperación de Mercancía · {subtitle}</p></div>', unsafe_allow_html=True)

def kpi(label, value):
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">{label}</div><div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)

def money(v):
    try: return '${:,.0f}'.format(float(v))
    except Exception: return '$0'

def pct(v):
    try: return '{:,.1f}%'.format(float(v))
    except Exception: return '0.0%'
