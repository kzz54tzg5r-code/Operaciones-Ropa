import pandas as pd
import streamlit as st

COLUMN_MAP = {
    'occurrence':'Ocurrencia','ocurrencia':'Ocurrencia','ba':'BA',
    'fecha':'Fecha','tienda':'Tienda','nombre':'Nombre','usuario':'Nombre',
    'actividad realizada':'Actividad','actividad':'Actividad','numero de piezas':'Piezas','número de piezas':'Piezas',
    'recorridos':'Recorridos','recorrido':'Recorridos',
    'semana iso':'Semana','semana_iso':'Semana','semana':'Semana',
    'dev_pzs':'Dev Pzs','dev pzs':'Dev Pzs','ventas netas pzs':'Vta Pzs','vta_pzs':'Vta Pzs','vta pzs':'Vta Pzs',
    'vta_imp':'Vta Imp','venta importe':'Vta Imp','costo_dev':'Costo Dev','costo dev':'Costo Dev'
}

def normalize_columns(df):
    df = df.copy()
    new_cols = {}
    for c in df.columns:
        key = str(c).strip().lower().replace('\n',' ')
        new_cols[c] = COLUMN_MAP.get(key, str(c).strip())
    df = df.rename(columns=new_cols)
    for col in ['Fecha']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    for col in ['Piezas','Recorridos','Dev Pzs','Vta Pzs','Vta Imp','Costo Dev','Semana']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'Actividad' in df.columns:
        df['Actividad'] = df['Actividad'].astype(str).str.strip()
    return df

@st.cache_data(show_spinner=False)
def read_excel(uploaded_file):
    xl = pd.ExcelFile(uploaded_file)
    frames = []
    commercial = []
    for sh in xl.sheet_names:
        try:
            df = pd.read_excel(uploaded_file, sheet_name=sh)
            if df.empty: continue
            df = normalize_columns(df)
            df['Hoja'] = sh
            cols = set(df.columns)
            if {'Dev Pzs','Vta Pzs'} & cols:
                commercial.append(df)
            else:
                frames.append(df)
        except Exception:
            continue
    op = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    com = pd.concat(commercial, ignore_index=True) if commercial else pd.DataFrame()
    return op, com, xl.sheet_names
