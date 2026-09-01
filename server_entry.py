"""Entrada de producción de bajo consumo para Render."""
from __future__ import annotations
import gc
import pandas as pd
import numpy as np
import web_app as _web

def _parse_operations_external_safe(stage_path, token):
    # Evita lanzar un segundo Python que vuelve a importar toda la aplicación.
    try:
        return _web.parse_operations_excel(stage_path, persist=False)
    finally:
        gc.collect()

def _scope(frame, store="Compañía", section="Todas", catalog="Todos"):
    if frame is None or frame.empty:
        return pd.DataFrame()
    work=frame
    if store and store!="Compañía" and "Tienda" in work:
        work=work[work["Tienda"].map(_web.login_key)==_web.login_key(store)]
    if section and section!="Todas" and "Sección" in work:
        work=work[work["Sección"].map(_web.login_key)==_web.login_key(section)]
    if catalog and catalog not in ("Todos","Todas","") and "Tipo catálogo" in work:
        work=work[work["Tipo catálogo"].map(_web.login_key)==_web.login_key(catalog)]
    return work

def _scope_v45(frame, store="Compañía", section="Todas", catalog="Todos", add_area=False):
    return _scope(frame,store,section,catalog)

def _locations(work, period=""):
    if work is None or work.empty:return []
    areas=_web._capacity_area_report_series(work)
    rows=[]
    for name,idx in areas.groupby(areas,dropna=False,sort=False).groups.items():
        rows.append({"location":str(name or "Sin ubicación"),**_web._capacity_metrics(work.loc[idx],period)})
    return sorted(rows,key=lambda r:-float(r.get("suggested") or 0))

def _rubros(work, section="Todas", period=""):
    if work is None or work.empty or "Subcategoría" not in work:return []
    rub=work["Subcategoría"].fillna("").astype(str).str.strip()
    valid=rub.ne("")
    if not valid.any():return []
    scoped=work.loc[valid]; rub=rub.loc[valid]
    sec=scoped["Sección"].fillna("Sin sección").astype(str) if "Sección" in scoped else pd.Series(section if section!="Todas" else "Compañía",index=scoped.index)
    keys=pd.DataFrame({"sec":sec,"rub":rub},index=scoped.index)
    rows=[]
    for (s,r),idx in keys.groupby(["sec","rub"],sort=False).groups.items():
        g=scoped.loc[idx]; m=_web._capacity_metrics(g,period)
        models=int(g["ID_ART"].fillna("").astype(str).str.strip().replace({"nan":"","None":""}).ne("").nunique()) if "ID_ART" in g else 0
        rows.append({"store":"Compañía","section":str(s),"rubro":str(r),"models":models,**m})
    return sorted(rows,key=lambda x:(-float(x.get("sales_value") or 0),-float(x.get("suggested") or 0),x["section"],x["rubro"]))

def _detail(store="Compañía",section="Todas",catalog="Todos",period=""):
    frame=_web._capacity_frame_for_period(period)
    work=_scope(frame,store,section,catalog)
    if work.empty:return []
    loc=_web._operational_location_series(work); area=_web._capacity_area_report_series(work)
    valid=loc.fillna("").astype(str).str.strip().ne("")
    if not valid.any():return []
    w=work.loc[valid]; tmp=pd.DataFrame(index=w.index)
    tmp["Tienda"]=w.get("Tienda",pd.Series("",index=w.index)).astype(str)
    tmp["Grupo ubicación"]=area.loc[valid].fillna("").astype(str)
    tmp["Pasillo real"]=loc.loc[valid].fillna("").astype(str)
    tmp["ID_ART"]=w.get("ID_ART",pd.Series("",index=w.index)).fillna("").astype(str)
    pcol,vcol=_web._capacity_period_columns(period)
    for dst,src in (("capacity","Capacidad"),("floor","Existencia piso"),("warehouse","Existencia bodega"),("existence","Existencia"),("suggested","VPD"),("sales_pzas",pcol),("sales_value",vcol)):
        tmp[dst]=pd.to_numeric(w.get(src,0),errors="coerce").fillna(0).to_numpy()
    tmp["ddi_weighted"]=pd.to_numeric(w.get("DDI",0),errors="coerce").fillna(0).to_numpy()*tmp["suggested"]
    cols=["Grupo ubicación","Pasillo real"] if store!="Compañía" else ["Tienda","Grupo ubicación","Pasillo real"]
    sums=tmp.groupby(cols,dropna=False,sort=False)[["capacity","floor","warehouse","existence","suggested","sales_pzas","sales_value","ddi_weighted"]].sum()
    ids=tmp[tmp["ID_ART"].ne("")].groupby(cols,dropna=False,sort=False)["ID_ART"].nunique().rename("ids")
    agg=sums.join(ids,how="left").fillna({"ids":0}).reset_index()
    agg["ddi"]=agg["ddi_weighted"].div(agg["suggested"].replace(0,np.nan)).fillna(0)
    agg["occupancy"]=np.where(agg["capacity"]>0,agg["existence"]/agg["capacity"]*100,np.nan)
    out=[]
    for r in agg.to_dict("records"):
        out.append({"store":str(r.get("Tienda") or "") if store=="Compañía" else store,"group":str(r.get("Grupo ubicación") or ""),"location":str(r.get("Pasillo real") or ""),"ids":int(r.get("ids") or 0),"capacity":float(r.get("capacity") or 0),"floor":float(r.get("floor") or 0),"warehouse":float(r.get("warehouse") or 0),"existence":float(r.get("existence") or 0),"suggested":float(r.get("suggested") or 0),"ddi":float(r.get("ddi") or 0),"occupancy":None if pd.isna(r.get("occupancy")) else float(r.get("occupancy")),"sales_pzas":float(r.get("sales_pzas") or 0),"sales_value":float(r.get("sales_value") or 0),"section":section if section!="Todas" else "Todas","catalog":catalog,"source":"Excel capacidades"})
    order={"Colgado":1,"Doblado":2,"Jeans":3,"Lencería":4}
    return sorted(out,key=lambda x:(order.get(x["group"],99),-float(x.get("suggested") or 0),x["store"],x["location"]))

_web._parse_operations_external=_parse_operations_external_safe
_web._scope_capacity=_scope
_web._capacity_scope_v45=_scope_v45
_web._capacity_locations_v45=_locations
_web._capacity_rubros_v45=_rubros
_web._capacity_location_detail=_detail
app=_web.app
