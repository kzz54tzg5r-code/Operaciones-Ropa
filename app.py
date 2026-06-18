
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
from datetime import datetime
import sqlite3, json, re

st.set_page_config(page_title="ORION V5.2 HOTFIX.2 HOTFIX", page_icon="🚀", layout="wide")

DATA_DIR = Path("orion_data"); DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "orion_v5.db"
OP_PATH = DATA_DIR / "operacion.parquet"
CO_PATH = DATA_DIR / "comercial.parquet"

AZUL = "#3366CC"; ROSA = "#FF99FF"; AZUL_OSCURO = "#003366"; FONDO = "#F5F5F5"
TIENDAS = ["Iztapalapa","Vallejo","Ecatepec","Toluca","Arco Norte","Ixtapaluca","Querétaro","Centro","Olivar","León","Puebla","Puebla Sur","Aguascalientes","Veracruz","Naucalpan","Miravalle","Atemajac"]
METAS_DEFAULT = {"productividad_diaria":784.0,"conversion":80.0,"recuperacion":80.0,"habilitado_ingresos":85.0,"ubicado_ingresos":80.0,"recorridos_semanales":47.0,"recorridos_lunes":5.0,"recorridos_martes":5.0,"recorridos_miercoles":5.0,"recorridos_jueves":8.0,"recorridos_viernes":8.0,"recorridos_sabado":8.0,"recorridos_domingo":8.0}

st.markdown(f"""
<style>
.stApp {{background:{FONDO};}}
.block-container {{padding-top:1rem;}}
.orion-header {{background:linear-gradient(90deg,{AZUL_OSCURO},{AZUL}); color:white; padding:22px 28px; border-radius:24px; margin-bottom:16px; box-shadow:0 8px 26px rgba(0,0,0,.18);}}
.orion-title {{font-size:40px; font-weight:900; margin:0;}}
.orion-sub {{font-size:18px; margin-top:4px;}}
.orion-mini {{font-size:13px; margin-top:10px; opacity:.95;}}
div[data-testid="stMetric"] {{background:white; border:1px solid #E2E8F0; border-radius:18px; padding:15px; box-shadow:0 5px 18px rgba(15,23,42,.07);}}
.ps-card {{background:white; border-top:5px solid {ROSA}; padding:16px; border-radius:18px; box-shadow:0 5px 18px rgba(15,23,42,.06); margin-bottom:12px;}}
.confidencial {{background:white; border-left:7px solid {ROSA}; padding:12px 16px; border-radius:14px; color:#334155; font-size:12px; margin-top:20px;}}
</style>
""", unsafe_allow_html=True)

# ---------------- DB ----------------
def init_db():
    con=sqlite3.connect(DB_PATH); cur=con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS metas(clave TEXT PRIMARY KEY, valor REAL, actualizado TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS historial_metas(id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, usuario TEXT, meta TEXT, anterior REAL, nueva REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS estado(clave TEXT PRIMARY KEY, valor TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS nombres(occurrence TEXT PRIMARY KEY, nombre_final TEXT)")
    for k,v in METAS_DEFAULT.items(): cur.execute("INSERT OR IGNORE INTO metas VALUES(?,?,?)",(k,float(v),datetime.now().isoformat()))
    con.commit(); con.close()

def sql_df(q, params=()):
    con=sqlite3.connect(DB_PATH); df=pd.read_sql_query(q,con,params=params); con.close(); return df

def get_metas():
    init_db(); df=sql_df("SELECT clave, valor FROM metas"); m=METAS_DEFAULT.copy(); m.update(dict(zip(df.clave,df.valor))); return m

def update_meta(k,v):
    m=get_metas(); old=float(m.get(k,0)); con=sqlite3.connect(DB_PATH); cur=con.cursor(); now=datetime.now()
    cur.execute("UPDATE metas SET valor=?, actualizado=? WHERE clave=?",(float(v),now.isoformat(),k))
    cur.execute("INSERT INTO historial_metas(fecha,hora,usuario,meta,anterior,nueva) VALUES(?,?,?,?,?,?)",(str(now.date()),now.strftime('%H:%M:%S'),'Administrador',k,old,float(v)))
    con.commit(); con.close()

def set_estado(k,v):
    con=sqlite3.connect(DB_PATH); cur=con.cursor(); cur.execute("INSERT OR REPLACE INTO estado VALUES(?,?)",(k,str(v))); con.commit(); con.close()

def get_estado(k,default=""):
    con=sqlite3.connect(DB_PATH); cur=con.cursor(); cur.execute("SELECT valor FROM estado WHERE clave=?",(k,)); row=cur.fetchone(); con.close(); return row[0] if row else default

def get_name_map():
    init_db(); df=sql_df("SELECT occurrence, nombre_final FROM nombres"); return dict(zip(df.occurrence.astype(str), df.nombre_final.astype(str))) if not df.empty else {}

def save_name_map(occ,nombre):
    con=sqlite3.connect(DB_PATH); cur=con.cursor(); cur.execute("INSERT OR REPLACE INTO nombres VALUES(?,?)",(str(occ),str(nombre).strip())); con.commit(); con.close()

init_db()

# ---------------- Helpers ----------------
def norm(x):
    if pd.isna(x): return "Sin registros"
    s=str(x).strip(); return s if s else "Sin registros"

def to_num(x):
    if pd.isna(x): return 0.0
    if isinstance(x,str): x=x.replace('$','').replace(',','').replace(' ','').strip()
    try:
        y=pd.to_numeric(x, errors='coerce')
        return 0.0 if pd.isna(y) else float(y)
    except Exception: return 0.0

def fmt_int(x):
    try: return f"{float(x):,.0f}"
    except Exception: return "0"

def fmt_pct(x):
    try: return f"{float(x):,.0f}%"
    except Exception: return "0%"

def pct(a,b):
    try: return (float(a)/float(b)*100) if float(b)!=0 else 0.0
    except Exception: return 0.0

def sdiv(a,b):
    a=pd.to_numeric(a, errors='coerce').fillna(0); b=pd.to_numeric(b, errors='coerce').fillna(0)
    return np.where(b!=0, a/b, 0)

def style_df(df):
    if df is None or df.empty: return df
    num_cols=df.select_dtypes(include='number').columns
    fmt={c:"{:,.0f}" for c in num_cols}
    pct_cols=[c for c in df.columns if '%' in str(c)]
    for c in pct_cols: fmt[c]="{:,.0f}%"
    return df.style.format(fmt).set_table_styles([
        {'selector':'th','props':f'background-color:{AZUL_OSCURO}; color:white; font-weight:bold;'},
        {'selector':'tbody tr:nth-child(even)','props':'background-color:#F8FAFC;'},
        {'selector':'tbody tr:hover','props':f'background-color:{ROSA}33;'}
    ])

def export_excel(sheets):
    bio=BytesIO()
    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
        for name,df in sheets.items():
            if isinstance(df,pd.DataFrame): df.to_excel(writer, sheet_name=name[:31], index=False)
    return bio.getvalue()

def exportar(nombre, sheets):
    st.download_button(f"⬇️ Exportar {nombre} Excel", data=export_excel(sheets), file_name=f"{nombre}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- Excel parser ----------------
def detect_oper_sheet(hojas):
    for h in hojas:
        if 'productividad' in h.lower(): return h
    return None

def detect_month_sheets(hojas):
    meses='enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre'
    return [h for h in hojas if re.search(meses,h.lower()) and re.search(r'26|2026',h.lower())]

def load_oper(file, hoja):
    df=pd.read_excel(file, sheet_name=hoja)
    df.columns=[str(c).strip() for c in df.columns]
    rename={}
    for c in df.columns:
        cl=str(c).strip().lower()
        if cl in ['ubicación','ubicacion','tienda','sucursal']: rename[c]='Tienda'
        elif cl in ['occurrence','ocurrencia']: rename[c]='Occurrence'
        elif cl=='fecha': rename[c]='Fecha'
        elif cl in ['nombre','usuario','colaborador']: rename[c]='Nombre'
        elif cl in ['actividad realizada','actividad']: rename[c]='Actividad Realizada'
        elif cl in ['número de piezas','numero de piezas','piezas','pzas']: rename[c]='Número de Piezas'
        elif 'recorrido' in cl: rename[c]='Recorridos'
        elif cl in ['motivo de ingreso','motivo']: rename[c]='Motivo de ingreso'
        elif cl=='área' or cl=='area': rename[c]='Área'
    df=df.rename(columns=rename)
    for c in ['Fecha','Tienda','Occurrence','Nombre','Actividad Realizada','Motivo de ingreso','Área','Número de Piezas','Recorridos']:
        if c not in df.columns: df[c]=np.nan
    # si hay columnas duplicadas por renombre, tomar primera o combinar
    df=df.loc[:,~df.columns.duplicated()].copy()
    df['Fecha']=pd.to_datetime(df['Fecha'], errors='coerce')
    df['Fecha Día']=df['Fecha'].dt.date
    df['Semana ISO']=df['Fecha'].dt.isocalendar().week.astype('Int64')
    df['Año ISO']=df['Fecha'].dt.isocalendar().year.astype('Int64')
    df['Mes']=df['Fecha'].dt.month_name()
    for c in ['Tienda','Occurrence','Nombre','Actividad Realizada','Motivo de ingreso','Área']:
        df[c]=df[c].apply(norm)
    df['Número de Piezas']=df['Número de Piezas'].apply(to_num)
    rec_num=df['Recorridos'].apply(to_num)
    df['Recorridos']=np.where(rec_num==1,1,0)  # solo cuenta registros con 1
    act=(df['Actividad Realizada'].astype(str)+' '+df['Motivo de ingreso'].astype(str)).str.lower()
    df['Muertos']=np.where(act.str.contains('muerto', regex=False), df['Número de Piezas'], 0)
    df['Cajas']=np.where(act.str.contains('caja', regex=False), df['Número de Piezas'], 0)
    df['Probador']=np.where(act.str.contains('probado|probador', regex=True), df['Número de Piezas'], 0)
    df['Habilitado']=np.where(act.str.contains('habilitado|habilitar', regex=True), df['Número de Piezas'], 0)
    df['Ubicado']=np.where(act.str.contains('ubicado|ubicar', regex=True), df['Número de Piezas'], 0)
    df['Recolección de Muertos']=df['Muertos']+df['Cajas']+df['Probador']
    df['Productividad Total']=df['Recolección de Muertos']+df['Habilitado']+df['Ubicado']
    return df

def find_col(df, opts):
    lookup={str(c).strip().lower():c for c in df.columns}
    for o in opts:
        if o.lower() in lookup: return lookup[o.lower()]
    return None

def load_month(file, sheet):
    df=pd.read_excel(file, sheet_name=sheet, header=1)
    df.columns=[str(c).strip() for c in df.columns]
    df=df.dropna(how='all')
    df=df.loc[:,~df.columns.duplicated()].copy()
    c_t=find_col(df,['Tiendas','Tienda','Sucursal','Ubicación'])
    c_mod=find_col(df,['Modelo','Modelo Proveedor'])
    c_cat=find_col(df,['Categoria','Categoría'])
    c_sub=find_col(df,['Sub Categoria','Sub Categoría','Subcategoria','Subcategoría'])
    c_id=find_col(df,['Id Art','ID','Id'])
    c_color=find_col(df,['Color'])
    c_prec=find_col(df,['Precio Menudeo','precio Mayoreo','Precio Mayoreo'])
    out=pd.DataFrame()
    out['Mes_Origen']=sheet
    out['Tienda']=df[c_t].apply(norm) if c_t else 'Sin registros'
    out['Modelo']=df[c_mod].apply(norm) if c_mod else 'Sin registros'
    out['Categoria']=df[c_cat].apply(norm) if c_cat else 'Sin registros'
    out['Subcategoria']=df[c_sub].apply(norm) if c_sub else 'Sin registros'
    out['Id Art']=df[c_id].apply(norm) if c_id else 'Sin registros'
    out['Color']=df[c_color].apply(norm) if c_color else 'Sin registros'
    precio=df[c_prec].apply(to_num) if c_prec else pd.Series([0]*len(df))
    vta_cols=[c for c in df.columns if str(c).lower().startswith('ventas netas pzs')]
    dev_cols=[c for c in df.columns if str(c).lower().startswith('dev pzs')]
    imp_cols=[c for c in df.columns if str(c).lower().startswith('venta neta en') or str(c).lower().startswith('venta neta $')]
    out['Vta_Pzs']=df[vta_cols].apply(lambda r: sum(to_num(x) for x in r), axis=1) if vta_cols else 0
    out['Dev_Pzs']=df[dev_cols].apply(lambda r: sum(to_num(x) for x in r), axis=1) if dev_cols else 0
    out['Vta_Imp']=df[imp_cols].apply(lambda r: sum(to_num(x) for x in r), axis=1) if imp_cols else 0
    out['Costo_Dev']=out['Dev_Pzs']*precio
    out['Piezas Vendidas Validadas']=np.minimum(out['Vta_Pzs'], out['Dev_Pzs'])
    out['Conversión %']=sdiv(out['Piezas Vendidas Validadas'], out['Dev_Pzs'])*100
    out['Valor Recuperado']=out['Vta_Imp']
    out['Valor Pendiente']=out['Costo_Dev']-out['Vta_Imp']
    out['Recuperación %']=sdiv(out['Valor Recuperado'], out['Costo_Dev'])*100
    return out, list(df.columns), {'vta_cols':vta_cols,'dev_cols':dev_cols,'imp_cols':imp_cols}

def process_excel(file):
    xls=pd.ExcelFile(file); hojas=xls.sheet_names
    op_sheet=detect_oper_sheet(hojas); month_sheets=detect_month_sheets(hojas)
    diag={'hojas':hojas,'hoja_operacion':op_sheet,'hojas_mensuales':month_sheets,'columnas_mensuales':{},'metric_cols':{},'errores':[]}
    op=load_oper(file, op_sheet) if op_sheet else pd.DataFrame()
    diag['columnas_operacion']=list(op.columns) if not op.empty else []
    frames=[]
    for s in month_sheets:
        try:
            temp, cols, metric_cols=load_month(file,s); frames.append(temp); diag['columnas_mensuales'][s]=cols; diag['metric_cols'][s]=metric_cols
        except Exception as e:
            diag['errores'].append(f'{s}: {e}')
    co=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    return op,co,diag

def save_data(op,co,diag,filename):
    if not op.empty: op.to_parquet(OP_PATH,index=False)
    if not co.empty: co.to_parquet(CO_PATH,index=False)
    set_estado('ultima_actualizacion',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    set_estado('archivo',filename)
    set_estado('diagnostico',json.dumps(diag,ensure_ascii=False,default=str))

def load_saved():
    op=pd.read_parquet(OP_PATH) if OP_PATH.exists() else pd.DataFrame()
    co=pd.read_parquet(CO_PATH) if CO_PATH.exists() else pd.DataFrame()
    # aplicar nombres corregidos por Occurrence
    if not op.empty:
        mp=get_name_map()
        if mp:
            op['Nombre Original']=op['Nombre']
            op['Nombre']=op['Occurrence'].astype(str).map(mp).fillna(op['Nombre'])
    return op,co

# Header
ultima=get_estado('ultima_actualizacion','Sin actualización'); archivo=get_estado('archivo','Sin archivo cargado')
now=datetime.now(); estado='Disponible' if OP_PATH.exists() or CO_PATH.exists() else 'Sin datos'
st.markdown(f"""
<div class="orion-header"><div style="font-weight:800;letter-spacing:.08em;">PRICE SHOES | OPERACIONES ROPA</div><div class="orion-title">🚀 ORION V5.2 HOTFIX.2 HOTFIX</div><div class="orion-sub">Plataforma Indicadores de Recuperación de Mercancía</div><div class="orion-mini">Productividad | Conversión | Recuperación Económica | Eficiencia Operativa<br>Fecha actual: {now:%Y-%m-%d} | Hora actual: {now:%H:%M:%S} | Última actualización: {ultima} | Estado de información: {estado}</div></div>
""",unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header('🔐 Acceso')
    rol=st.radio('Rol',['Consulta','Administrador'],horizontal=True)
    is_admin=rol=='Administrador'
    if is_admin:
        clave=st.text_input('Clave administrador',type='password')
        is_admin=clave==st.secrets.get('ADMIN_PASSWORD','orion_admin')
    st.divider(); st.header('📂 Datos')
    if is_admin:
        up=st.file_uploader('Cargar/Reemplazar Excel',type=['xlsx'])
        if up is not None:
            st.info('Archivo listo. Presiona el botón solo una vez.')
            if st.button('🚀 Procesar archivo',type='primary'):
                with st.spinner('Procesando Excel...'):
                    try:
                        op_new,co_new,diag=process_excel(up); save_data(op_new,co_new,diag,up.name)
                        st.success('Archivo procesado y guardado. Cambia a Consulta para visualizar.')
                    except Exception as e: st.error(f'No se pudo procesar el archivo: {e}')
    else:
        st.caption('Modo consulta: visualiza sin cargar archivo.')

op_all, co_all = load_saved()
if op_all.empty and co_all.empty:
    st.warning('No hay datos persistidos. Un administrador debe cargar el Excel por primera vez.')
    st.stop()
metas=get_metas()

# Defaults week current/max
available_weeks=sorted([int(x) for x in op_all['Semana ISO'].dropna().unique()]) if not op_all.empty and 'Semana ISO' in op_all else []
current_iso=datetime.now().isocalendar().week
default_week=[current_iso] if current_iso in available_weeks else ([max(available_weeks)] if available_weeks else [])

with st.sidebar:
    st.divider(); st.header('🎛️ Filtros globales')
    f_sem=st.multiselect('Semana ISO',available_weeks,default=default_week)
    months=sorted(set(op_all.get('Mes',pd.Series(dtype=str)).dropna().astype(str).tolist()+co_all.get('Mes_Origen',pd.Series(dtype=str)).dropna().astype(str).tolist()))
    f_mes=st.multiselect('Mes',months)
    f_tienda=st.multiselect('Tienda',TIENDAS)
    f_act=st.multiselect('Actividad',sorted(op_all.get('Actividad Realizada',pd.Series(dtype=str)).dropna().astype(str).unique()) if not op_all.empty else [])
    f_cat=st.multiselect('Categoría',sorted(co_all.get('Categoria',pd.Series(dtype=str)).dropna().astype(str).unique()) if not co_all.empty else [])
    f_sub=st.multiselect('Subcategoría',sorted(co_all.get('Subcategoria',pd.Series(dtype=str)).dropna().astype(str).unique()) if not co_all.empty else [])
    f_mod=st.multiselect('Modelo',sorted(co_all.get('Modelo',pd.Series(dtype=str)).dropna().astype(str).unique()) if not co_all.empty else [])
    f_col=st.multiselect('Colaborador',sorted(op_all.get('Nombre',pd.Series(dtype=str)).dropna().astype(str).unique()) if not op_all.empty else [])
    f_occ=st.multiselect('ID de empleado / Occurrence',sorted(op_all.get('Occurrence',pd.Series(dtype=str)).dropna().astype(str).unique()) if not op_all.empty else [])

op=op_all.copy(); co=co_all.copy()
if f_sem and not op.empty: op=op[op['Semana ISO'].isin(f_sem)]
if f_mes:
    if not op.empty: op=op[op['Mes'].isin(f_mes)]
    if not co.empty: co=co[co['Mes_Origen'].isin(f_mes)]
if f_tienda:
    if not op.empty: op=op[op['Tienda'].isin(f_tienda)]
    if not co.empty: co=co[co['Tienda'].isin(f_tienda)]
if f_act and not op.empty: op=op[op['Actividad Realizada'].isin(f_act)]
if f_cat and not co.empty: co=co[co['Categoria'].isin(f_cat)]
if f_sub and not co.empty: co=co[co['Subcategoria'].isin(f_sub)]
if f_mod and not co.empty: co=co[co['Modelo'].isin(f_mod)]
if f_col and not op.empty: op=op[op['Nombre'].isin(f_col)]
if f_occ and not op.empty: op=op[op['Occurrence'].isin(f_occ)]

# Summaries
def commercial_store(df):
    return df.groupby('Tienda',as_index=False).agg(Dev_Pzs=('Dev_Pzs','sum'),Vta_Pzs=('Piezas Vendidas Validadas','sum'),Vta_Imp=('Vta_Imp','sum'),Costo_Dev=('Costo_Dev','sum'),Valor_Pendiente=('Valor Pendiente','sum')) if not df.empty else pd.DataFrame(columns=['Tienda','Dev_Pzs','Vta_Pzs','Vta_Imp','Costo_Dev','Valor_Pendiente'])


def ensure_dashboard_columns(df):
    """Asegura columnas numéricas requeridas para rankings y KPIs sin KeyError."""
    if df is None:
        return pd.DataFrame()
    df = df.copy()

    if "Tienda" not in df.columns:
        df["Tienda"] = "Sin registros"
    if "Nombre" not in df.columns:
        df["Nombre"] = "Sin registros"
    if "Actividad Realizada" not in df.columns:
        df["Actividad Realizada"] = "Sin registros"
    if "Ocurrencia" not in df.columns:
        df["Ocurrencia"] = "Sin registros"

    required_numeric = [
        "Muertos", "Cajas", "Probador", "Habilitado", "Ubicado",
        "Productividad Total", "Recorridos", "Número de Piezas",
        "Ingresos", "Recolección de Muertos"
    ]

    for col in required_numeric:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Recolección de Muertos"] = df["Muertos"] + df["Cajas"] + df["Probador"]
    df["Ingresos"] = df["Muertos"] + df["Cajas"] + df["Probador"]

    if df["Productividad Total"].sum() == 0:
        df["Productividad Total"] = df["Recolección de Muertos"] + df["Habilitado"] + df["Ubicado"]

    return df

def operation_store(df):
    df = ensure_dashboard_columns(df)
    return df.groupby('Tienda',as_index=False).agg(Muertos=('Muertos','sum'),Cajas=('Cajas','sum'),Probador=('Probador','sum'),Recoleccion=('Recolección de Muertos','sum'),Habilitado=('Habilitado','sum'),Ubicado=('Ubicado','sum'),Productividad=('Productividad Total','sum'),Recorridos=('Recorridos','sum')) if not df.empty else pd.DataFrame(columns=['Tienda','Muertos','Cajas','Probador','Recoleccion','Habilitado','Ubicado','Productividad','Recorridos'])

def store_summary(opdf,codf, only_registered=False):
    base=pd.DataFrame({'Tienda':TIENDAS})
    out=base.merge(operation_store(opdf),on='Tienda',how='left').merge(commercial_store(codf),on='Tienda',how='left').fillna(0)
    for c in out.columns:
        if c!='Tienda': out[c]=pd.to_numeric(out[c],errors='coerce').fillna(0)
    out['Total Ingresos']=out['Dev_Pzs']+out['Muertos']+out['Cajas']+out['Probador']
    out['% Habilitado']=sdiv(out['Habilitado'],out['Total Ingresos'])*100
    out['% Ubicado']=sdiv(out['Ubicado'],out['Total Ingresos'])*100
    out['Conversión %']=sdiv(out['Vta_Pzs'],out['Dev_Pzs'])*100
    out['Recuperación %']=sdiv(out['Vta_Imp'],out['Costo_Dev'])*100
    out['Con Registro']=out[['Productividad','Dev_Pzs','Vta_Imp','Recorridos']].sum(axis=1)>0
    if only_registered: out=out[out['Con Registro']].copy()
    return out

ss=store_summary(op,co,only_registered=False)
ss_reg=store_summary(op,co,only_registered=True)

def meta_recorridos_periodo(opdf):
    if opdf.empty: return metas['recorridos_semanales']
    days=opdf[['Fecha Día']].dropna().drop_duplicates().shape[0]
    weeks=max(1, len(opdf['Semana ISO'].dropna().unique()))
    if days<=7: return metas['recorridos_semanales']
    return metas['recorridos_semanales']*weeks

def meta_prod_periodo(opdf):
    if opdf.empty: return metas['productividad_diaria']
    days=max(1, opdf[['Fecha Día']].dropna().drop_duplicates().shape[0])
    return metas['productividad_diaria']*days

# KPIs top
k1,k2,k3,k4,k5=st.columns(5)
k1.metric('Total Ingresos', fmt_int(ss_reg['Total Ingresos'].sum()))
k2.metric('% Habilitado', fmt_pct(pct(ss_reg['Habilitado'].sum(),ss_reg['Total Ingresos'].sum())))
k3.metric('% Ubicado', fmt_pct(pct(ss_reg['Ubicado'].sum(),ss_reg['Total Ingresos'].sum())))
k4.metric('Conversión', fmt_pct(pct(ss_reg['Vta_Pzs'].sum(),ss_reg['Dev_Pzs'].sum())))
score=round(min(pct(ss_reg['Productividad'].sum(), meta_prod_periodo(op)*max(op['Nombre'].nunique() if not op.empty else 1,1)),100)*.40 + min(pct(ss_reg['Habilitado'].sum(),ss_reg['Total Ingresos'].sum()),100)*.25 + min(pct(ss_reg['Ubicado'].sum(),ss_reg['Total Ingresos'].sum()),100)*.15 + min(pct(ss_reg['Vta_Pzs'].sum(),ss_reg['Dev_Pzs'].sum()),100)*.10 + min(pct(ss_reg['Recorridos'].sum(),meta_recorridos_periodo(op)*max(ss_reg['Tienda'].nunique(),1)),100)*.10,1)
k5.metric('Score Integral', f'{score:,.0f}/100')

# Tabs
tab_names=['Panel Ejecutivo','Macro','Conversión','Recuperación Económica','Productividad por Colaborador','Productividad por Actividad','Eficiencia Operativa','Cumplimiento de Recorridos','Indicadores Diarios','Top 30 Modelos','Análisis por Categoría','Análisis por Subcategoría','Ranking de Tiendas','Ranking de Colaboradores','Índice Integral','Alertas Inteligentes','Configuración de Metas','Diagnóstico de Datos','Compartir ORION']
if not is_admin:
    tab_names.remove('Configuración de Metas'); tab_names.remove('Diagnóstico de Datos')
tabs=st.tabs(tab_names); T=dict(zip(tab_names,tabs))

with T['Panel Ejecutivo']:
    st.subheader('Panel Ejecutivo')
    st.caption('Top y bottom muestran únicamente tiendas con registro. Se excluyen nombres no coherentes agrupando por ID de empleado / Occurrence.')
    panel=ss_reg.copy()
    panel['Score']=(panel['Productividad'].rank(pct=True)*40 + panel['Vta_Imp'].rank(pct=True)*25 + panel['Recorridos'].rank(pct=True)*20 + panel['Conversión %'].rank(pct=True)*15).round(0)
    c1,c2=st.columns(2)
    with c1:
        st.write('Top 2 Tiendas'); st.dataframe(style_df(panel.sort_values('Score',ascending=False).head(2)),width='stretch')
    with c2:
        st.write('Bottom 2 Tiendas'); st.dataframe(style_df(panel.sort_values('Score').head(2)),width='stretch')
    colab=op.groupby(['Occurrence','Nombre'],as_index=False).agg(Productividad=('Productividad Total','sum')) if not op.empty else pd.DataFrame()
    colab=colab[colab['Nombre'].astype(str).str.len()>2].sort_values('Productividad',ascending=False) if not colab.empty else colab
    c1,c2=st.columns(2)
    with c1: st.write('Top 3 Colaboradores'); st.dataframe(style_df(colab.head(3)),width='stretch')
    with c2: st.write('Bottom 3 Colaboradores'); st.dataframe(style_df(colab[colab['Productividad']>0].tail(3) if not colab.empty else colab),width='stretch')
    st.plotly_chart(px.bar(panel.sort_values('Score',ascending=False),x='Tienda',y='Score',color='Score',color_continuous_scale=[ROSA,AZUL],title='Score card por tienda'),width='stretch')

with T['Macro']:
    st.subheader('Macro | Comparativo últimas 4 semanas')
    macro=store_summary(op_all,co_all,False)
    if not op_all.empty:
        sem=op_all.groupby('Semana ISO',as_index=False).agg(Muertos=('Muertos','sum'),Cajas=('Cajas','sum'),Probador=('Probador','sum'),Habilitado=('Habilitado','sum'),Ubicado=('Ubicado','sum'),Recorridos=('Recorridos','sum')).sort_values('Semana ISO').tail(4)
        co_sem = pd.DataFrame()
        # Comercial no trae fecha diaria confiable, se presenta operacional por semana
        sem['Total Ingresos']=sem['Muertos']+sem['Cajas']+sem['Probador']
        sem['% Habilitado']=sdiv(sem['Habilitado'],sem['Total Ingresos'])*100
        sem['% Ubicado']=sdiv(sem['Ubicado'],sem['Total Ingresos'])*100
        st.dataframe(style_df(sem[['Semana ISO','Total Ingresos','Habilitado','Ubicado','% Habilitado','% Ubicado','Recorridos']]),width='stretch')
        fig=go.Figure(); fig.add_bar(x=sem['Semana ISO'].astype(str),y=sem['Total Ingresos'],name='Total Ingresos',marker_color=AZUL); fig.add_scatter(x=sem['Semana ISO'].astype(str),y=sem['% Habilitado'],name='% Habilitado',mode='lines+markers',line=dict(color=ROSA,width=3)); fig.add_scatter(x=sem['Semana ISO'].astype(str),y=sem['% Ubicado'],name='% Ubicado',mode='lines+markers',line=dict(color=AZUL_OSCURO,width=3)); fig.update_layout(title='Comparativo por Semana ISO',yaxis_title='Ingresos / %')
        st.plotly_chart(fig,width='stretch')

with T['Conversión']:
    st.subheader('Conversión')
    c1,c2,c3=st.columns(3); c1.metric('Dev_Pzs',fmt_int(ss_reg['Dev_Pzs'].sum())); c2.metric('Vta_Pzs validada',fmt_int(ss_reg['Vta_Pzs'].sum())); c3.metric('Conversión',fmt_pct(pct(ss_reg['Vta_Pzs'].sum(),ss_reg['Dev_Pzs'].sum())))
    df=ss_reg[['Tienda','Dev_Pzs','Vta_Pzs','Conversión %']].sort_values('Conversión %',ascending=False)
    st.dataframe(style_df(df),width='stretch'); st.plotly_chart(px.bar(df,x='Tienda',y='Conversión %',color='Conversión %',color_continuous_scale=[ROSA,AZUL]),width='stretch')

with T['Recuperación Económica']:
    st.subheader('Recuperación Económica')
    c1,c2,c3=st.columns(3); c1.metric('Valor Recuperado',f"${fmt_int(ss_reg['Vta_Imp'].sum())}"); c2.metric('Costo Dev',f"${fmt_int(ss_reg['Costo_Dev'].sum())}"); c3.metric('Valor Pendiente',f"${fmt_int(ss_reg['Valor_Pendiente'].sum())}")
    df=ss_reg[['Tienda','Vta_Imp','Costo_Dev','Valor_Pendiente','Recuperación %']].sort_values('Vta_Imp',ascending=False)
    st.dataframe(style_df(df),width='stretch'); st.plotly_chart(px.bar(df,x='Tienda',y='Vta_Imp',color='Recuperación %',color_continuous_scale=[ROSA,AZUL]),width='stretch')

with T['Productividad por Colaborador']:
    st.subheader('Ranking de Productividad por Colaborador')
    if not op.empty:
        area=op.groupby(['Occurrence','Nombre','Tienda','Área'],as_index=False).agg(Piezas=('Productividad Total','sum'))
        idx=area.groupby(['Occurrence','Nombre','Tienda'])['Piezas'].idxmax(); area_max=area.loc[idx].rename(columns={'Área':'Área mayor productividad','Piezas':'Piezas área mayor'})
        df=op.groupby(['Occurrence','Nombre','Tienda'],as_index=False).agg(Recoleccion=('Recolección de Muertos','sum'),Habilitado=('Habilitado','sum'),Ubicado=('Ubicado','sum'),Productividad=('Productividad Total','sum'))
        df=df.merge(area_max[['Occurrence','Nombre','Tienda','Área mayor productividad','Piezas área mayor']],on=['Occurrence','Nombre','Tienda'],how='left')
        df['Meta']=meta_prod_periodo(op); df['Cumplimiento %']=sdiv(df['Productividad'],df['Meta'])*100; df['Ranking']=df['Productividad'].rank(method='first',ascending=False).astype(int)
        df=df.sort_values('Ranking')[['Ranking','Occurrence','Nombre','Tienda','Recoleccion','Habilitado','Ubicado','Productividad','Meta','Cumplimiento %','Área mayor productividad','Piezas área mayor']]
        st.dataframe(style_df(df),width='stretch'); st.plotly_chart(px.bar(df.head(30),x='Nombre',y='Productividad',color='Cumplimiento %',color_continuous_scale=[ROSA,AZUL]),width='stretch')

with T['Productividad por Actividad']:
    st.subheader('Productividad por Actividad')
    c1,c2=st.columns(2)
    act_df=pd.DataFrame({'Actividad':['Recolección de muertos','Habilitado','Ubicado'],'Piezas':[op['Recolección de Muertos'].sum() if not op.empty else 0, op['Habilitado'].sum() if not op.empty else 0, op['Ubicado'].sum() if not op.empty else 0]})
    ing_df=pd.DataFrame({'Ingreso':['Sistema Dev_Pzs','Piso de venta / Muertos','Recolección cajas','Recolección probador'],'Piezas':[co['Dev_Pzs'].sum() if not co.empty else 0, op['Muertos'].sum() if not op.empty else 0, op['Cajas'].sum() if not op.empty else 0, op['Probador'].sum() if not op.empty else 0]})
    with c1: st.write('Por actividad'); st.dataframe(style_df(act_df),width='stretch'); st.plotly_chart(px.pie(act_df,names='Actividad',values='Piezas',hole=.45,color_discrete_sequence=[AZUL,ROSA,AZUL_OSCURO]),width='stretch')
    with c2: st.write('Por ingresos'); st.dataframe(style_df(ing_df),width='stretch'); st.plotly_chart(px.bar(ing_df,x='Ingreso',y='Piezas',color='Ingreso',color_discrete_sequence=[AZUL,ROSA,AZUL_OSCURO,'#94A3B8']),width='stretch')

with T['Eficiencia Operativa']:
    st.subheader('Eficiencia Operativa | Solo tiendas con registro')
    df=ss_reg.copy(); df['Ranking']=df['% Habilitado'].rank(method='first',ascending=False).astype(int); df=df.sort_values('Ranking')
    c1,c2,c3,c4,c5=st.columns(5); c1.metric('Total Ingresos',fmt_int(df['Total Ingresos'].sum())); c2.metric('Habilitado',fmt_int(df['Habilitado'].sum())); c3.metric('Ubicado',fmt_int(df['Ubicado'].sum())); c4.metric('% Habilitado',fmt_pct(pct(df['Habilitado'].sum(),df['Total Ingresos'].sum()))); c5.metric('% Ubicado',fmt_pct(pct(df['Ubicado'].sum(),df['Total Ingresos'].sum())))
    cols=['Ranking','Tienda','Total Ingresos','Habilitado','Ubicado','% Habilitado','% Ubicado']; st.dataframe(style_df(df[cols]),width='stretch')

with T['Cumplimiento de Recorridos']:
    st.subheader('Cumplimiento de Recorridos')
    df=ss_reg[['Tienda','Recorridos']].copy(); df['Meta semanal']=meta_recorridos_periodo(op); df['% Cumplimiento']=sdiv(df['Recorridos'],df['Meta semanal'])*100; df['Estatus']=np.where(df['% Cumplimiento']>=100,'🟢 Cumple',np.where(df['% Cumplimiento']>=80,'🟡 Atención','🔴 Bajo')); df['Ranking']=df['% Cumplimiento'].rank(method='first',ascending=False).astype(int); df=df.sort_values('Ranking')
    st.dataframe(style_df(df[['Ranking','Tienda','Estatus','Meta semanal','Recorridos','% Cumplimiento']]),width='stretch')
    fig=go.Figure(); fig.add_bar(x=df['Tienda'],y=df['Recorridos'],name='Recorridos',marker_color=AZUL); fig.add_scatter(x=df['Tienda'],y=df['Meta semanal'],name='Meta',mode='lines+markers',line=dict(color=ROSA,width=4)); st.plotly_chart(fig,width='stretch')

with T['Indicadores Diarios']:
    st.subheader('Indicadores Diarios')
    if not op.empty:
        df=op.groupby(['Fecha Día','Tienda','Occurrence','Nombre'],as_index=False).agg(Productividad=('Productividad Total','sum'),Ingresos=('Recolección de Muertos','sum'),Habilitado=('Habilitado','sum'),Ubicado=('Ubicado','sum'),Recorridos=('Recorridos','sum'))
        df['Meta']=metas['productividad_diaria']; df['Cumplimiento %']=sdiv(df['Productividad'],df['Meta'])*100; df['% Habilitado']=sdiv(df['Habilitado'],df['Ingresos'])*100; df['% Ubicado']=sdiv(df['Ubicado'],df['Ingresos'])*100
        df=df.rename(columns={'Occurrence':'ID de empleado','Fecha Día':'Fecha'})
        st.dataframe(style_df(df),width='stretch')
        if is_admin:
            st.write('Modificar nombre por ID de empleado')
            ids=sorted(op_all['Occurrence'].astype(str).unique())
            occ=st.selectbox('ID de empleado',ids)
            current=op_all.loc[op_all['Occurrence'].astype(str)==occ,'Nombre'].mode()
            suggested=current.iloc[0] if not current.empty else ''
            new_name=st.text_input('Nombre correcto',value=suggested)
            if st.button('Guardar nombre corregido'):
                save_name_map(occ,new_name); st.success('Nombre guardado. Actualiza la app para reagrupar.')

with T['Top 30 Modelos']:
    st.subheader('Top 30 Modelos')
    if not co.empty:
        df=co.groupby(['Modelo','Categoria','Subcategoria'],as_index=False).agg(Dev_Pzs=('Dev_Pzs','sum'),Vta_Pzs=('Piezas Vendidas Validadas','sum'),Recuperacion_Dinero=('Vta_Imp','sum'),Costo_Dev=('Costo_Dev','sum'),Valor_Pendiente=('Valor Pendiente','sum'))
        df['Recuperación %']=sdiv(df['Recuperacion_Dinero'],df['Costo_Dev'])*100
        crit=st.selectbox('Ranking',['Mayor recuperación económica','Mayor recuperación %','Mayor venta','Mayor pendiente'])
        col={'Mayor recuperación económica':'Recuperacion_Dinero','Mayor recuperación %':'Recuperación %','Mayor venta':'Vta_Pzs','Mayor pendiente':'Valor_Pendiente'}[crit]
        top=df.sort_values(col,ascending=False).head(30)
        st.dataframe(style_df(top),width='stretch'); st.plotly_chart(px.bar(top,x='Modelo',y=col,color='Categoria',color_discrete_sequence=[AZUL,ROSA,AZUL_OSCURO]),width='stretch')

with T['Análisis por Categoría']:
    st.subheader('Análisis por Categoría')
    if not co.empty:
        df=co.groupby('Categoria',as_index=False).agg(Dev_Pzs=('Dev_Pzs','sum'),Vta_Pzs=('Piezas Vendidas Validadas','sum'),Recuperacion=('Vta_Imp','sum'),Costo_Dev=('Costo_Dev','sum'))
        df['Conversión %']=sdiv(df['Vta_Pzs'],df['Dev_Pzs'])*100; df['Recuperación %']=sdiv(df['Recuperacion'],df['Costo_Dev'])*100
        st.dataframe(style_df(df.sort_values('Recuperacion',ascending=False)),width='stretch'); st.plotly_chart(px.bar(df,x='Categoria',y='Recuperacion',color='Recuperación %',color_continuous_scale=[ROSA,AZUL]),width='stretch')

with T['Análisis por Subcategoría']:
    st.subheader('Análisis por Subcategoría')
    if not co.empty:
        df=co.groupby('Subcategoria',as_index=False).agg(Dev_Pzs=('Dev_Pzs','sum'),Vta_Pzs=('Piezas Vendidas Validadas','sum'),Recuperacion=('Vta_Imp','sum'),Costo_Dev=('Costo_Dev','sum'))
        df['Conversión %']=sdiv(df['Vta_Pzs'],df['Dev_Pzs'])*100; df['Recuperación %']=sdiv(df['Recuperacion'],df['Costo_Dev'])*100
        st.dataframe(style_df(df.sort_values('Recuperacion',ascending=False)),width='stretch'); st.plotly_chart(px.bar(df.head(30),x='Subcategoria',y='Recuperacion',color='Recuperación %',color_continuous_scale=[ROSA,AZUL]),width='stretch')

with T['Ranking de Tiendas']:
    st.subheader('Ranking de Tiendas')
    df=ss.copy(); df['Score']=(df['Productividad'].rank(pct=True)*40+df['Habilitado'].rank(pct=True)*25+df['Ubicado'].rank(pct=True)*15+df['Conversión %'].rank(pct=True)*10+df['Recorridos'].rank(pct=True)*10).round(0); df['Ranking']=df['Score'].rank(method='first',ascending=False).astype(int)
    cols=['Ranking','Tienda','Productividad','Dev_Pzs','Vta_Pzs','Vta_Imp','Recuperación %','Conversión %','Recorridos','Score']; st.dataframe(style_df(df.sort_values('Ranking')[cols]),width='stretch')

with T['Ranking de Colaboradores']:
    st.subheader('Ranking de Colaboradores')
    if not op.empty:
        df=op.groupby(['Occurrence','Nombre'],as_index=False).agg(Productividad=('Productividad Total','sum'),Recorridos=('Recorridos','sum'))
        df['Score']=(df['Productividad'].rank(pct=True)*85+df['Recorridos'].rank(pct=True)*15).round(0); df['Ranking']=df['Score'].rank(method='first',ascending=False).astype(int)
        st.dataframe(style_df(df.sort_values('Ranking')),width='stretch')

with T['Índice Integral']:
    st.subheader('Índice Integral')
    st.metric('Score Integral',f'{score:,.0f}/100'); st.progress(min(score/100,1)); st.write('40% Productividad | 25% Habilitado | 15% Ubicado | 10% Conversión | 10% Recorridos')

with T['Alertas Inteligentes']:
    st.subheader('Alertas Inteligentes')
    alerts=[]
    if pct(ss_reg['Vta_Pzs'].sum(),ss_reg['Dev_Pzs'].sum())<metas['conversion']: alerts.append(['Conversión','Alta','Conversión menor a meta'])
    if pct(ss_reg['Vta_Imp'].sum(),ss_reg['Costo_Dev'].sum())<metas['recuperacion']: alerts.append(['Recuperación','Alta','Recuperación menor a meta'])
    for _,r in ss.iterrows():
        if r['Con Registro']==False: alerts.append(['Tienda sin registros','Media',f"{r['Tienda']} sin registros"])
        elif r['Productividad']>0 and r['Vta_Imp']==0: alerts.append(['Productividad sin recuperación','Media',f"{r['Tienda']} tiene productividad sin recuperación"])
    st.dataframe(style_df(pd.DataFrame(alerts,columns=['Tipo','Prioridad','Alerta'])),width='stretch') if alerts else st.success('Sin alertas críticas.')

if 'Configuración de Metas' in T:
    with T['Configuración de Metas']:
        st.subheader('Configuración de Metas')
        cols=st.columns(3); nuevos={}
        for i,(k,v) in enumerate(metas.items()):
            with cols[i%3]: nuevos[k]=st.number_input(k,value=float(v),step=1.0)
        if st.button('Guardar metas'):
            for k,v in nuevos.items():
                if float(v)!=float(metas[k]): update_meta(k,v)
            st.success('Metas actualizadas.'); st.rerun()
        st.dataframe(style_df(sql_df('SELECT * FROM historial_metas ORDER BY id DESC')),width='stretch')

if 'Diagnóstico de Datos' in T:
    with T['Diagnóstico de Datos']:
        st.subheader('Diagnóstico de Datos')
        try: diag=json.loads(get_estado('diagnostico','{}'))
        except Exception: diag={}
        st.json(diag); c1,c2,c3=st.columns(3); c1.metric('Registros operación',fmt_int(len(op_all))); c2.metric('Registros comercial',fmt_int(len(co_all))); c3.metric('Duplicados operación',fmt_int(op_all.duplicated().sum() if not op_all.empty else 0))
        if not op_all.empty: st.dataframe(style_df(op_all.isna().sum().reset_index().rename(columns={'index':'Columna',0:'Nulos'})),width='stretch')

with T['Compartir ORION']:
    st.subheader('Compartir ORION')
    app_url = st.text_input('URL pública de la aplicación', value='https://operaciones-ropa-vjmsxlqrzqrmm3fhdgvcpt.streamlit.app')
    st.code(app_url)
    st.write(f'Última actualización: {ultima}')
    st.write(f'Archivo cargado: {archivo}')
    st.info('Una vez cargado el archivo por administrador, los usuarios en rol Consulta pueden ver la información sin cargar Excel.')

st.markdown("""<div class="confidencial"><b>CONFIDENCIAL</b><br>La información contenida en esta plataforma es propiedad de Price Shoes y está destinada exclusivamente para uso interno de Operaciones Ropa. Queda prohibida su reproducción, distribución o divulgación sin autorización expresa de la Dirección correspondiente.<br>© Price Shoes | Operaciones Ropa</div>""", unsafe_allow_html=True)
