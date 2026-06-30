import pandas as pd

def safe_div(a,b):
    try:
        return 0 if float(b)==0 else float(a)/float(b)*100
    except Exception:
        return 0

def activity_pieces(df, keyword):
    if df.empty or 'Actividad' not in df.columns: return 0
    mask = df['Actividad'].astype(str).str.lower().str.contains(keyword.lower(), na=False)
    if 'Piezas' in df.columns:
        return df.loc[mask, 'Piezas'].sum()
    return mask.sum()

def compute_summary(op, com):
    habilitado = activity_pieces(op, 'habil')
    ubicado = activity_pieces(op, 'ubic')
    recorridos = op['Recorridos'].sum() if 'Recorridos' in op.columns else activity_pieces(op, 'recorr')
    dev = com['Dev Pzs'].sum() if 'Dev Pzs' in com.columns else 0
    vta = com['Vta Pzs'].sum() if 'Vta Pzs' in com.columns else 0
    venta_imp = com['Vta Imp'].sum() if 'Vta Imp' in com.columns else 0
    return {
        'habilitado': habilitado,
        'ubicado': ubicado,
        'recorridos': recorridos,
        'dev_pzs': dev,
        'vta_pzs': vta,
        'venta_imp': venta_imp,
        'conversion_pct': safe_div(vta, dev),
        'ubicado_habilitado_pct': safe_div(ubicado, habilitado),
    }

def by_store(op):
    if op.empty or 'Tienda' not in op.columns: return pd.DataFrame()
    pieces = 'Piezas' if 'Piezas' in op.columns else None
    if pieces:
        return op.groupby('Tienda', as_index=False)[pieces].sum().rename(columns={pieces:'Piezas'})
    return op.groupby('Tienda', as_index=False).size().rename(columns={'size':'Registros'})

def by_person(op):
    if op.empty or 'Nombre' not in op.columns: return pd.DataFrame()
    pieces = 'Piezas' if 'Piezas' in op.columns else None
    if pieces:
        return op.groupby('Nombre', as_index=False)[pieces].sum().rename(columns={pieces:'Piezas'}).sort_values('Piezas', ascending=False)
    return op.groupby('Nombre', as_index=False).size().rename(columns={'size':'Registros'})
