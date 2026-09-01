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

# Parche visual y de estabilidad: se aplica a la respuesta HTML sin duplicar el
# archivo web/index.html de gran tamaño.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class _OpsUIPatch(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or response.status_code!=200:
            return response
        body=b""
        async for chunk in response.body_iterator:
            body+=chunk
        try:
            html=body.decode("utf-8")
        except UnicodeDecodeError:
            return Response(body,status_code=response.status_code,headers=dict(response.headers),media_type="text/html")
        patch=r'''<style>
#macroAreaTableWrap{max-height:1185px;overflow-y:auto;position:relative}
#macroAreaTableWrap .table th{position:sticky;top:0;z-index:4}
#macroAreaAreaSwitch{display:flex;gap:6px;flex-wrap:wrap;margin:5px 0 9px}
</style><script>
(()=>{const $=s=>document.querySelector(s);let AF='Todas',ROWS=[];
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const n=v=>typeof v==='number'?v.toLocaleString('es-MX',{maximumFractionDigits:2}):'—';
const p=v=>v==null?'N/D':Number(v).toFixed(1)+'%';
const scope=()=>window.DASH?.selected_store||$('#store')?.value||'Compañía';
function setup(){const t=$('#macroAreaTitle');if(t)t.textContent='Ubicación · '+scope();
 const old=$('#macroAreaSectionSwitch');if(old)old.style.display='none';
 const sub=old?.parentElement?.previousElementSibling;
 if(sub&&!$('#macroAreaAreaSwitch')){const bar=document.createElement('div');bar.id='macroAreaAreaSwitch';
 ['Todas','Colgado','Doblado','Jeans','Lencería'].forEach(a=>{const b=document.createElement('button');b.className='switch'+(a===AF?' active':'');b.textContent=a;b.onclick=()=>{AF=a;document.querySelectorAll('#macroAreaAreaSwitch .switch').forEach(x=>x.classList.toggle('active',x.textContent===a));paint()};bar.appendChild(b)});sub.after(bar)}
 const tb=$('#macroAreaTable');if(tb){const w=tb.closest('.tablewrap');if(w)w.id='macroAreaTableWrap'}
 document.querySelectorAll('th').forEach(x=>{if(/^Últ?\.? CEDIS$/i.test(x.textContent.trim()))x.textContent='Ult entrada'})}
 function paint(){const b=$('#macroAreaTable');if(!b)return;const d=AF==='Todas'?ROWS:ROWS.filter(r=>String(r.group||'')===AF);
 b.innerHTML=d.length?d.map(r=>'<tr><td>'+esc(r.group)+'</td><td>'+esc(r.location)+'</td><td>'+n(r.ids)+'</td><td>'+n(r.capacity)+'</td><td>'+n(r.floor)+'</td><td>'+n(r.warehouse)+'</td><td>'+n(r.existence)+'</td><td>'+n(r.suggested)+'</td><td>'+n(r.ddi)+'</td><td>'+n(r.sales_pzas)+'</td><td>+n(r.sales_value)+'</td><td>'+p(r.occupancy)+'</td></tr>').join(''):'<tr><td colspan="12">Sin información para el filtro seleccionado.</td></tr>'}
 window.loadMacroAreaDetail=async()=>{setup();const b=$('#macroAreaTable');if(b)b.innerHTML='<tr><td colspan="12">Cargando ubicación…</td></tr>';try{const d=await api('/api/commercial-detail?week='+encodeURIComponent($('#week')?.value||'')+'&store='+encodeURIComponent(scope())+'&section=Todas&catalog='+encodeURIComponent($('#catalog')?.value||'Todos'),{timeoutMs:120000});ROWS=d.locations||[];paint()}catch(e){if(b)b.innerHTML='<tr><td colspan="12">No fue posible consultar ubicación: '+esc(e.message)+'</td></tr>'}setup()};
 const bind=()=>{const btn=$('#uploadOps');if(!btn||btn.dataset.patch)return;btn.dataset.patch='1';btn.onclick=async()=>{const f=$('#opsFile')?.files?.[0];if(!f){log('Selecciona Excel operativo de Cambios y Muertos.');return}btn.disabled=true;btn.textContent='Procesando…';let ok=false,last='';for(let i=0;i<2&&!ok;i++){try{const r=await postFile('/api/upload/operations',f);log('Excel de Cambios y Muertos cargado correctamente\\nFilas: '+(r.rows||0));ok=true;await safeRefreshDash()}catch(e){last=e.message;if(i===0){log('Reintentando automáticamente la carga…');await new Promise(r=>setTimeout(r,5000))}}}if(!ok)log('Error real de carga: '+last);btn.disabled=false;btn.textContent='Procesar operativo'}};
 const end=w=>{const m=/^(\\d{4})-W(\\d+)/.exec(w||'');if(!m)return new Date();const j=new Date(+m[1],0,4),day=j.getDay()||7;const mon=new Date(j);mon.setDate(j.getDate()-day+1+(+m[2]-1)*7);mon.setDate(mon.getDate()+6);return mon};
 const orig=window.renderModelRows;if(typeof orig==='function')window.renderModelRows=function(a,b,z,...x){const base=end($('#week')?.value||'');z=(z||[]).filter(r=>{const s=String(r.ultima_cedis||'').trim();if(!s||s==='—')return false;const d=new Date(s+'T00:00:00'),q=(base-d)/86400000;return !Number.isNaN(q)&&q>=0&&q<=30});return orig.call(this,a,b,z,...x)};
 new MutationObserver(()=>{setup();bind()}).observe(document.body,{childList:true,subtree:true});setTimeout(()=>{setup();bind()},100)
})();
</script>'''
        html=html.replace("</body>",patch+"</body>",1)
        return Response(html.encode("utf-8"),status_code=200,media_type="text/html")

app.add_middleware(_OpsUIPatch)
