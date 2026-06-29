
import streamlit as st
import pandas as pd
import numpy as np
import json, re, unicodedata
from pathlib import Path
from io import BytesIO
from datetime import date
import plotly.graph_objects as go

DATA_DIR = Path("orion_data")
DATA_DIR.mkdir(exist_ok=True)
OP_FILE = DATA_DIR / "operacion.parquet"
CO_FILE = DATA_DIR / "comercial.parquet"
CONFIG_FILE = DATA_DIR / "config.json"

PRICE_BLUE = "#2F4A8A"
PRICE_PINK = "#EC007C"
PRICE_PURPLE = "#3E3A8C"
DARK = "#17132F"

TIENDAS_DEFAULT = ["Iztapalapa","Vallejo","Ecatepec","Toluca","Arco Norte","Ixtapaluca","Querétaro","Centro","Olivar","León","Puebla","Puebla Sur","Aguascalientes","Veracruz","Naucalpan","Miravalle","Atemajac"]

st.set_page_config(page_title="Recuperación Cambios y Muertos", page_icon="🚀", layout="wide")

st.markdown(f"""
<style>
.block-container{{padding-top:2.8rem; max-width:1500px;}}
.title h1{{font-size:54px;line-height:0.95;margin:0;color:{DARK};font-weight:900;}}
.title p{{font-size:24px;margin:12px 0 0 0;color:#707789;font-weight:700;}}
.pinkbar{{background:{PRICE_PINK};color:white;font-size:30px;font-weight:900;padding:12px 26px;margin:18px 0 28px 0;}}
.section-title{{border-left:8px solid {PRICE_PINK};padding-left:16px;color:{PRICE_PURPLE};font-size:27px;font-weight:900;margin:20px 0;}}
.wow-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin-bottom:28px;}}
.wow-card{{border:1px solid #D7DBE8;border-radius:12px;overflow:hidden;background:#F7F8FB;}}
.wow-head{{background:{PRICE_PURPLE};color:white;text-align:center;font-size:20px;font-weight:900;padding:16px;}}
.wow-body{{padding:16px 22px;}}
.wow-line{{display:grid;grid-template-columns:1fr 105px 74px;gap:6px;border-bottom:1px solid #E0E3EC;padding:12px 0;align-items:center;}}
.wow-lbl{{font-size:13px;font-weight:900;color:#666;}}
.wow-num{{font-size:22px;font-weight:900;color:{PRICE_PURPLE};text-align:right;}}
.wow-var{{font-size:12px;font-weight:900;text-align:right;white-space:nowrap;}}
.up{{color:#00A95C;}} .down{{color:#F50057;}}
</style>
""", unsafe_allow_html=True)

def norm_txt(x):
    s = str(x).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8").lower()
    return re.sub(r"[^a-z0-9]+", "", s)

def pick_col(df, aliases):
    m = {norm_txt(c): c for c in df.columns}
    for a in aliases:
        k = norm_txt(a)
        if k in m:
            return m[k]
    for c in df.columns:
        cn = norm_txt(c)
        for a in aliases:
            if norm_txt(a) in cn:
                return c
    return None

def num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def fmt_n(v):
    try: return f"{float(v):,.0f}"
    except Exception: return "0"

def fmt_money(v):
    try: return f"${float(v):,.0f}"
    except Exception: return "$0"

def fmt_pct(v):
    try: return f"{float(v):,.1f}%"
    except Exception: return "0.0%"

def pct(a,b):
    a=float(a or 0); b=float(b or 0)
    return (a/b*100) if b else 0

def load_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception: pass
    return {"project_stores": TIENDAS_DEFAULT[:5], "meta_productividad": 784, "admin_password": "admin123"}

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_operacion(df):
    d = df.copy()
    fecha = pick_col(d, ["Fecha Día","Fecha Dia","Fecha","Timestamp","Marca temporal"])
    tienda = pick_col(d, ["Tienda","Sucursal"])
    actividad = pick_col(d, ["Actividad Realizada","Actividad"])
    motivo = pick_col(d, ["Motivo de ingreso","Ingreso","Motivo ingreso"])
    piezas = pick_col(d, ["Número de Piezas","Numero de Piezas","Piezas","Pzas","Cantidad"])
    nombre = pick_col(d, ["Nombre","Colaborador","Usuario"])
    ocurr = pick_col(d, ["Ocurrencia","Occurrence","Empleado","ID empleado"])
    area = pick_col(d, ["Área","Area","Tabla"])
    out = pd.DataFrame()
    out["Fecha"] = pd.to_datetime(d[fecha], errors="coerce") if fecha else pd.NaT
    out["Fecha Día"] = out["Fecha"].dt.date
    out["Semana ISO"] = out["Fecha"].dt.isocalendar().week.astype("Float64").fillna(0).astype(int)
    out["Mes"] = out["Fecha"].dt.strftime("%Y-%m").fillna("")
    out["Tienda"] = d[tienda].astype(str).str.strip() if tienda else "Sin tienda"
    out["Actividad Realizada"] = d[actividad].astype(str).str.strip() if actividad else ""
    out["Motivo de ingreso"] = d[motivo].astype(str).str.strip() if motivo else ""
    out["Número de Piezas"] = num(d[piezas]) if piezas else 0
    out["Nombre"] = d[nombre].astype(str).str.strip() if nombre else "Sin nombre"
    out["Ocurrencia"] = d[ocurr].astype(str).str.strip() if ocurr else ""
    out["Área"] = d[area].astype(str).str.strip() if area else ""
    act = out["Actividad Realizada"].map(norm_txt)
    mot = out["Motivo de ingreso"].map(norm_txt)
    p = out["Número de Piezas"]
    out["Recoleccion"] = np.where(act.str.contains("recoleccion|recolec|muerto", regex=True), p, 0)
    out["Acondicionado"] = np.where(act.str.contains("acondicionado|habilitado|habilitar", regex=True), p, 0)
    out["Ubicado"] = np.where(act.str.contains("ubicado|ubicar", regex=True), p, 0)
    out["Recorridos"] = np.where(act.str.contains("recorrido", regex=True), 1, 0)
    out["Muertos Piso Venta"] = np.where((out["Recoleccion"]>0) & mot.str.contains("muerto", regex=True), p, 0)
    out["Ingresos Cajas"] = np.where((out["Recoleccion"]>0) & mot.str.contains("caja", regex=True), p, 0)
    out["Ingresos Probador"] = np.where((out["Recoleccion"]>0) & mot.str.contains("probador", regex=True), p, 0)
    return out

def normalize_comercial(df):
    d = df.copy()
    fecha = pick_col(d, ["Fecha Día","Fecha Dia","Fecha","Fecha Venta","Fecha_Venta","Fecha Devolución","Fecha Dev","Date"])
    tienda = pick_col(d, ["Tienda","Sucursal"])
    dev = pick_col(d, ["Dev_Pzs","Dev Pzs","Dev pzs","Devoluciones","Pzs Dev"])
    vta = pick_col(d, ["Vta_Pzs","Ventas Netas Pzs","Vta Pzs","Venta Pzs"])
    imp = pick_col(d, ["Vta_Imp","Venta $","Vta Imp","Venta Importe","Ventas Netas $"])
    costo = pick_col(d, ["Costo_Dev","Costo Dev","Costo Devolución","Valor Devolución"])
    modelo = pick_col(d, ["ID","Id","Modelo","ID Modelo","Articulo","Artículo"])
    color = pick_col(d, ["Color"])
    talla = pick_col(d, ["Talla"])
    out = pd.DataFrame()
    out["Fecha"] = pd.to_datetime(d[fecha], errors="coerce") if fecha else pd.NaT
    out["Fecha Día"] = out["Fecha"].dt.date
    out["Semana ISO"] = out["Fecha"].dt.isocalendar().week.astype("Float64").fillna(0).astype(int)
    out["Mes"] = out["Fecha"].dt.strftime("%Y-%m").fillna("")
    out["Tienda"] = d[tienda].astype(str).str.strip() if tienda else "Sin tienda"
    out["Dev_Pzs"] = num(d[dev]) if dev else 0
    out["Vta_Pzs"] = num(d[vta]) if vta else 0
    out["Vta_Imp"] = num(d[imp]) if imp else 0
    out["Costo_Dev"] = num(d[costo]) if costo else 0
    out["ID/Modelo"] = d[modelo].astype(str).str.strip() if modelo else "Sin modelo"
    out["Color"] = d[color].astype(str).str.strip() if color else "Sin color"
    out["Talla"] = d[talla].astype(str).str.strip() if talla else "Sin talla"
    return out

@st.cache_data(show_spinner=False)
def process_excel(file_bytes):
    xls = pd.ExcelFile(BytesIO(file_bytes))
    ops, cos = [], []
    for sh in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sh)
            cols = " ".join(map(str, df.columns)).lower()
            if ("actividad" in cols and "tienda" in cols) or "resultados" in sh.lower():
                ops.append(normalize_operacion(df))
            if any(x in cols for x in ["dev", "vta", "venta", "devol"]):
                co = normalize_comercial(df)
                if co[["Dev_Pzs","Vta_Pzs","Vta_Imp","Costo_Dev"]].sum().sum() > 0:
                    cos.append(co)
        except Exception:
            pass
    op = pd.concat(ops, ignore_index=True) if ops else pd.DataFrame()
    co = pd.concat(cos, ignore_index=True) if cos else pd.DataFrame()
    return op, co

def load_data():
    op = pd.read_parquet(OP_FILE) if OP_FILE.exists() else pd.DataFrame()
    co = pd.read_parquet(CO_FILE) if CO_FILE.exists() else pd.DataFrame()
    return op, co

def save_data(op, co):
    op.to_parquet(OP_FILE, index=False)
    co.to_parquet(CO_FILE, index=False)

def render_header():
    c1,c2,c3 = st.columns([1,4,5])
    with c1:
        logo = Path("assets/logo.png")
        if logo.exists(): st.image(str(logo), width=125)
    with c2:
        st.markdown('<div class="title"><h1>Recuperación<br>Cambios y Muertos</h1><p>Matriz de Operaciones</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown("<br><br><h3 style='color:#EC007C;'>Recuperación Operaciones &nbsp;&nbsp; Cambios Ropa &nbsp;&nbsp; Indicadores Compañía</h3>", unsafe_allow_html=True)
    st.markdown('<div class="pinkbar">Operaciones Ropa</div>', unsafe_allow_html=True)

def filtered_project(op, co, stores):
    if stores:
        if not op.empty and "Tienda" in op: op = op[op["Tienda"].isin(stores)].copy()
        if not co.empty and "Tienda" in co: co = co[co["Tienda"].isin(stores)].copy()
    return op, co

def resumen_sem(op, co, stores):
    opf, cof = filtered_project(op, co, stores)
    semanas = sorted(set(opf.get("Semana ISO", pd.Series(dtype=int)).dropna().astype(int).tolist() + cof.get("Semana ISO", pd.Series(dtype=int)).dropna().astype(int).tolist()))
    rows = []
    for sem in semanas[-4:]:
        o = opf[opf["Semana ISO"]==sem] if not opf.empty else pd.DataFrame()
        c = cof[cof["Semana ISO"]==sem] if not cof.empty else pd.DataFrame()
        ingresos = (c["Dev_Pzs"].sum() if not c.empty else 0) + (o["Muertos Piso Venta"].sum() + o["Ingresos Cajas"].sum() + o["Ingresos Probador"].sum() if not o.empty else 0)
        acond = o["Acondicionado"].sum() if not o.empty else 0
        ubic = o["Ubicado"].sum() if not o.empty else 0
        recorr = o["Recorridos"].sum() if not o.empty else 0
        rows.append({"Semana ISO":sem,"Ingresos":ingresos,"Acondicionado":acond,"Ubicado":ubic,"Recorridos":recorr,"% Acond":pct(acond, ingresos), "% Ubic":pct(ubic, ingresos)})
    return pd.DataFrame(rows)

def wow_cards(df):
    if df.empty: return
    html = '<div class="section-title">📊 Resumen Ejecutivo</div><div class="wow-row">'
    prev = None
    for _,r in df.iterrows():
        if prev is not None and prev["Ingresos"]:
            var=(r["Ingresos"]-prev["Ingresos"])/prev["Ingresos"]*100
            cls="up" if var>=0 else "down"; arr="▲" if var>=0 else "▼"
            var_html=f'<span class="{cls}">{arr} {abs(var):.1f}%</span>'
        else:
            var_html="-"
        html += (
            f'<div class="wow-card"><div class="wow-head">Sem {int(r["Semana ISO"])}</div><div class="wow-body">'
            f'<div class="wow-line"><div class="wow-lbl">INGRESOS</div><div class="wow-num">{fmt_n(r["Ingresos"])}</div><div class="wow-var">{var_html}</div></div>'
            f'<div class="wow-line"><div class="wow-lbl">ACONDICIONADO</div><div class="wow-num">{fmt_n(r["Acondicionado"])}</div><div class="wow-var">{fmt_pct(r["% Acond"])}</div></div>'
            f'<div class="wow-line"><div class="wow-lbl">UBICADO</div><div class="wow-num">{fmt_n(r["Ubicado"])}</div><div class="wow-var">{fmt_pct(r["% Ubic"])}</div></div>'
            f'<div class="wow-line"><div class="wow-lbl">RECORRIDOS</div><div class="wow-num">{fmt_n(r["Recorridos"])}</div><div class="wow-var">-</div></div>'
            '</div></div>'
        )
        prev = r
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def table(df, height=420):
    st.dataframe(df, width="stretch", height=height, hide_index=True)

def page_dia(op, co, stores):
    st.header("Día Anterior | Ingresos y Pendiente por Procesar")
    opf, cof = filtered_project(op, co, stores)
    fechas = sorted(set([x for x in opf.get("Fecha Día", pd.Series(dtype=object)).dropna().tolist()] + [x for x in cof.get("Fecha Día", pd.Series(dtype=object)).dropna().tolist()]))
    f = st.date_input("Fecha a consultar", value=fechas[-1] if fechas else date.today())
    o = opf[opf["Fecha Día"]==f] if not opf.empty else pd.DataFrame()
    c = cof[cof["Fecha Día"]==f] if not cof.empty else pd.DataFrame()
    stores_base = stores or sorted(set(opf.get("Tienda",pd.Series(dtype=str)).tolist()+cof.get("Tienda",pd.Series(dtype=str)).tolist()))
    rows=[]
    for t in stores_base:
        ot=o[o["Tienda"]==t] if not o.empty else pd.DataFrame()
        ct=c[c["Tienda"]==t] if not c.empty else pd.DataFrame()
        dev=ct["Dev_Pzs"].sum() if not ct.empty else 0
        muertos=ot["Muertos Piso Venta"].sum() if not ot.empty else 0
        cajas=ot["Ingresos Cajas"].sum() if not ot.empty else 0
        prob=ot["Ingresos Probador"].sum() if not ot.empty else 0
        total=dev+muertos+cajas+prob
        rec=ot["Recoleccion"].sum() if not ot.empty else 0
        acond=ot["Acondicionado"].sum() if not ot.empty else 0
        ubic=ot["Ubicado"].sum() if not ot.empty else 0
        rows.append({"Tienda":t,"Dev pzs":dev,"Muertos":muertos,"Cajas":cajas,"Probador":prob,"Total":total,"Recolectadas":rec,"Acondicionado":acond,"Pend. Hab.":max(total-acond,0),"% Acond.":pct(acond,total),"Ubicadas":ubic,"Pend. Ub.":max(total-ubic,0),"% Ubic.":pct(ubic,total)})
    det=pd.DataFrame(rows).sort_values("Total", ascending=False)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Piezas Ingresadas", fmt_n(det["Total"].sum()))
    c2.metric("Acondicionado", fmt_n(det["Acondicionado"].sum()))
    c3.metric("Ubicado", fmt_n(det["Ubicadas"].sum()))
    c4.metric("Pendiente Ubicar", fmt_n(det["Pend. Ub."].sum()))
    c5.metric("% Procesado", fmt_pct(pct(det["Acondicionado"].sum(), det["Total"].sum())))
    table(det)
    if not det.empty:
        fig=go.Figure()
        fig.add_bar(x=det["Tienda"], y=det["Acondicionado"], name="Acondicionado", marker_color=PRICE_BLUE, text=det["Acondicionado"], textposition="outside")
        fig.add_bar(x=det["Tienda"], y=det["Ubicadas"], name="Ubicado", marker_color=PRICE_PINK, text=det["Ubicadas"], textposition="outside")
        fig.add_scatter(x=det["Tienda"], y=det["Total"], name="Total ingresos", mode="lines+markers+text", text=det["Total"], textposition="top center", line=dict(color=PRICE_PURPLE, width=3))
        fig.update_layout(height=470, barmode="group", legend=dict(orientation="h"))
        st.plotly_chart(fig, width="stretch")

def page_periodo(op, co, stores, mode):
    st.header("Reporte Semanal" if mode=="semana" else "Reporte Mensual")
    opf, cof = filtered_project(op, co, stores)
    if mode=="semana":
        vals=sorted(set(opf.get("Semana ISO", pd.Series(dtype=int)).dropna().astype(int).tolist()+cof.get("Semana ISO", pd.Series(dtype=int)).dropna().astype(int).tolist()))
        sel=st.multiselect("Semana ISO", vals, default=vals[-1:] if vals else [])
        if sel:
            opf=opf[opf["Semana ISO"].isin(sel)] if not opf.empty else opf
            cof=cof[cof["Semana ISO"].isin(sel)] if not cof.empty else cof
    else:
        vals=sorted(set(opf.get("Mes", pd.Series(dtype=str)).dropna().tolist()+cof.get("Mes", pd.Series(dtype=str)).dropna().tolist()))
        sel=st.multiselect("Mes", vals, default=vals[-1:] if vals else [])
        if sel:
            opf=opf[opf["Mes"].isin(sel)] if not opf.empty else opf
            cof=cof[cof["Mes"].isin(sel)] if not cof.empty else cof
    stores_base=stores or sorted(set(opf.get("Tienda",pd.Series(dtype=str)).tolist()+cof.get("Tienda",pd.Series(dtype=str)).tolist()))
    rows=[]
    for t in stores_base:
        o=opf[opf["Tienda"]==t] if not opf.empty else pd.DataFrame()
        c=cof[cof["Tienda"]==t] if not cof.empty else pd.DataFrame()
        ingresos=(c["Dev_Pzs"].sum() if not c.empty else 0)+(o["Muertos Piso Venta"].sum()+o["Ingresos Cajas"].sum()+o["Ingresos Probador"].sum() if not o.empty else 0)
        acond=o["Acondicionado"].sum() if not o.empty else 0
        ubic=o["Ubicado"].sum() if not o.empty else 0
        rows.append({"Tienda":t,"Ingresos":ingresos,"Acondicionado":acond,"% Acond":pct(acond,ingresos),"Ubicado":ubic,"% Ubic":pct(ubic,ingresos),"Recorridos":o["Recorridos"].sum() if not o.empty else 0})
    df=pd.DataFrame(rows).sort_values("Ingresos",ascending=False)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Piezas Ingresadas", fmt_n(df["Ingresos"].sum()))
    c2.metric("Acondicionado", fmt_n(df["Acondicionado"].sum()), fmt_pct(pct(df["Acondicionado"].sum(), df["Ingresos"].sum())))
    c3.metric("Ubicado", fmt_n(df["Ubicado"].sum()), fmt_pct(pct(df["Ubicado"].sum(), df["Ingresos"].sum())))
    c4.metric("Pendiente por Procesar", fmt_n(max(df["Ingresos"].sum()-df["Ubicado"].sum(),0)))
    table(df)

def page_conversion(co, titulo="Conversión Semanal Dev → Venta"):
    st.header(titulo)
    if co.empty:
        st.info("No hay datos comerciales.")
        return
    fechas=pd.to_datetime(co["Fecha Día"], errors="coerce").dropna()
    d=co.copy()
    if not fechas.empty:
        c1,c2=st.columns(2)
        ini=c1.date_input("Fecha inicio", fechas.min().date())
        fin=c2.date_input("Fecha final", fechas.max().date())
        d=co[(pd.to_datetime(co["Fecha Día"], errors="coerce").dt.date>=ini)&(pd.to_datetime(co["Fecha Día"], errors="coerce").dt.date<=fin)].copy()
    g=d.groupby(["Semana ISO","Tienda","ID/Modelo","Color","Talla"], as_index=False).agg(Dev_Pzs=("Dev_Pzs","sum"), Vta_Pzs=("Vta_Pzs","sum"), Vta_Imp=("Vta_Imp","sum"), Costo_Dev=("Costo_Dev","sum"))
    g["Conv. Pzs"]=np.minimum(g["Dev_Pzs"], g["Vta_Pzs"])
    ratio=np.where(g["Vta_Pzs"]>0, g["Conv. Pzs"]/g["Vta_Pzs"], 0)
    g["Conv. $"]=g["Vta_Imp"]*ratio
    g["Pend. Conv."]=np.maximum(g["Dev_Pzs"]-g["Conv. Pzs"],0)
    g["Venta No Conv."]=np.maximum(g["Costo_Dev"]-g["Conv. $"],0)
    res=g.groupby(["Semana ISO","Tienda"], as_index=False).sum(numeric_only=True)
    res["% Conv."]=np.where(res["Dev_Pzs"]>0, res["Conv. Pzs"]/res["Dev_Pzs"]*100,0)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Dev Pzs Semana", fmt_n(res["Dev_Pzs"].sum()))
    c2.metric("Conversión Dev → Venta Pzs", fmt_n(res["Conv. Pzs"].sum()))
    c3.metric("Conversión Dev → Venta $", fmt_money(res["Conv. $"].sum()))
    c4.metric("% Conversión", fmt_pct(pct(res["Conv. Pzs"].sum(), res["Dev_Pzs"].sum())))
    c5.metric("Pendiente por Convertir Pzs", fmt_n(res["Pend. Conv."].sum()))
    table(res)

def page_config(op, co, cfg):
    st.header("Configuración de Metas")
    tiendas=sorted(set(TIENDAS_DEFAULT + op.get("Tienda",pd.Series(dtype=str)).dropna().astype(str).tolist()+co.get("Tienda",pd.Series(dtype=str)).dropna().astype(str).tolist()))
    sel=st.multiselect("Tiendas del proyecto Cambios y Muertos", tiendas, default=[t for t in cfg.get("project_stores",[]) if t in tiendas])
    meta=st.number_input("Meta Productividad Diaria", value=float(cfg.get("meta_productividad",784)), step=1.0)
    if st.button("Guardar configuración", type="primary"):
        cfg["project_stores"]=sel
        cfg["meta_productividad"]=meta
        save_config(cfg)
        st.success("Configuración guardada. Cambia de pestaña para ver la información actualizada.")

cfg=load_config()
with st.sidebar:
    st.header("🔐 Acceso")
    rol=st.radio("Rol", ["Consulta","Administrador"], horizontal=True)
    admin=False
    if rol=="Administrador":
        clave=st.text_input("Clave administrador", type="password")
        admin = clave == cfg.get("admin_password","admin123")
        if admin: st.success("Administrador activo")
        elif clave: st.warning("Clave incorrecta")
    st.divider()
    if admin:
        up=st.file_uploader("Cargar/Reemplazar Excel", type=["xlsx"])
        if up and st.button("Procesar archivo", type="primary"):
            with st.spinner("Procesando Excel..."):
                op, co=process_excel(up.getvalue())
                save_data(op, co)
                st.success("Archivo procesado.")
        if st.button("Borrar datos persistidos"):
            for f in [OP_FILE,CO_FILE]:
                if f.exists(): f.unlink()
            st.success("Datos borrados.")
    st.divider()
    pagina=st.radio("Navegación", ["0. Día Anterior / Pendiente","1. Reporte Semanal","2. Reporte Mensual","3. Conversión","4. Recuperación Económica","18. Configuración de Metas"])

op, co = load_data()
render_header()

if op.empty and co.empty:
    st.warning("No hay datos cargados. Entra como Administrador y carga el Excel.")
    st.stop()

stores=cfg.get("project_stores", [])
wow_cards(resumen_sem(op, co, stores))

if pagina=="0. Día Anterior / Pendiente":
    page_dia(op, co, stores)
elif pagina=="1. Reporte Semanal":
    page_periodo(op, co, stores, "semana")
elif pagina=="2. Reporte Mensual":
    page_periodo(op, co, stores, "mes")
elif pagina=="3. Conversión":
    page_conversion(co, "Conversión Semanal Dev → Venta")
elif pagina=="4. Recuperación Económica":
    page_conversion(co, "Recuperación Económica")
elif pagina=="18. Configuración de Metas":
    if admin: page_config(op, co, cfg)
    else: st.warning("Sólo administrador puede modificar configuración.")

st.markdown("<hr><b>CONFIDENCIAL</b><br>© Price Shoes | Operaciones Ropa", unsafe_allow_html=True)
