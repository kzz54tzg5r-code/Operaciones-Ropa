"""V119: corrige congelamiento de V118 y agrega filtro Anual al Centro Operativo.

Cambios:
- elimina el MutationObserver de V118 que podía entrar en ciclo al renombrar
  repetidamente el mismo nodo y bloquear el navegador incluso en login;
- mantiene Centro Operativo como única entrada para Día / Semanal / Mensual;
- agrega Anual como cuarta vista operativa;
- el corte Anual usa un endpoint dedicado con rango 01-ene a 31-dic sin tocar
  la lógica validada del endpoint operativo principal;
- soporta descarga PDF/XLSX anual con nombre Centro_Operativo_<año>.
"""
from __future__ import annotations
import io


def install(m):
    if getattr(m, "_V119_CENTRO_OPERATIVO_SAFE_ANNUAL", False):
        return

    from fastapi.responses import HTMLResponse

    def _year_bounds(year: str):
        txt=str(year or "").strip()
        if not (len(txt)==4 and txt.isdigit()):
            raise m.HTTPException(400,"Año inválido")
        y=int(txt)
        if y < 2000 or y > 2100:
            raise m.HTTPException(400,"Año inválido")
        return txt,f"{txt}-01-01",f"{txt}-12-31"

    @m.app.get("/api/operations/year")
    def operations_year(
        request: m.Request,
        year: str,
        store: str="Compañía",
        area: str="",
        activity: str="",
        compact: bool=True,
        project_only: bool=False,
    ):
        y,start,end=_year_bounds(year)
        data=m.operations(
            request,store=store,period_type="all",period_value="",
            area=area,activity=activity,start_date=start,end_date=end,
            compact=compact,project_only=project_only,
        )
        out=dict(data)
        out["period_type"]="year"
        out["period_value"]=y
        out["start_date"]=start
        out["end_date"]=end
        out["available_years"]=sorted({str(d)[:4] for d in (out.get("available_dates") or []) if len(str(d))>=4})
        return out

    @m.app.get("/api/export/operations/year")
    def export_operations_year(
        request: m.Request,
        format: str="pdf",
        report: str="Centro Ejecutivo",
        year: str="",
        store: str="Compañía",
        area: str="",
        activity: str="",
        project_only: bool=False,
    ):
        y,start,end=_year_bounds(year)
        m.require_user(request)
        data=m.operations(
            request,store=store,period_type="all",period_value="",
            area=area,activity=activity,start_date=start,end_date=end,
            compact=True,project_only=project_only,
        )
        data=dict(data)
        data["period_type"]="year"
        data["period_value"]=y
        data["start_date"]=start
        data["end_date"]=end
        summary,stores,recovery,productivity=m._report_export_payload(data,report)
        base="Centro_Operativo" if report=="Centro Ejecutivo" else m.re.sub(r"[^A-Za-z0-9_-]+","_",report).strip("_")
        filename=f"{base}_{y}"

        if format.lower()=="xlsx":
            bio=io.BytesIO()
            with m.pd.ExcelWriter(bio,engine="openpyxl") as writer:
                m.pd.DataFrame(summary,columns=["Indicador","Valor"]).to_excel(writer,sheet_name="Resumen",index=False)
                m.pd.DataFrame(stores).to_excel(writer,sheet_name="Detalle Operativo",index=False)
                m.pd.DataFrame(recovery).to_excel(writer,sheet_name="Conversion Recuperacion",index=False)
                m.pd.DataFrame(productivity).to_excel(writer,sheet_name="Productividad",index=False)
            bio.seek(0)
            return m.Response(
                content=bio.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition":f'attachment; filename="{filename}.xlsx"',"Cache-Control":"no-store"},
            )

        if format.lower()=="pdf":
            try:
                payload=m._build_operations_pdf(data,report,scope=store)
                return m.Response(
                    content=payload,media_type="application/pdf",
                    headers={"Content-Disposition":f'attachment; filename="{filename}.pdf"',"Cache-Control":"no-store"},
                )
            except Exception as exc:
                raise m.HTTPException(500,f"No fue posible generar PDF anual: {type(exc).__name__}: {exc}")
        raise m.HTTPException(400,"Formato no soportado")

    css=r'''<style id="v119-centro-operativo-css">
#operativoNav [data-opview="Operación Diaria"],
#operativoNav [data-opview="Reporte Semanal"],
#operativoNav [data-opview="Reporte Mensual"]{display:none!important}
#operPeriodModeWrap.v119-oper-mode{display:block!important;min-width:170px}
</style>'''

    js=r'''<script id="v119-centro-operativo-js">
(function(){
 const CENTER='Centro Ejecutivo';
 const modes=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
 const yearsFrom=(d)=>Array.from(new Set([...(d?.available_dates||[]),...(d?.available_months||[])].map(v=>String(v||'').slice(0,4)).filter(v=>/^\d{4}$/.test(v)))).sort();

 function setCenterPeriod(d){
   const bar=$('#operativoPeriodBar'),sel=$('#operPeriodSelect'),lab=$('#operPeriodLabel'),wrap=$('#operPeriodModeWrap'),mode=$('#operPeriodMode');
   const sw=$('#operStartWrap'),ew=$('#operEndWrap');
   if(sw)sw.classList.add('hidden');if(ew)ew.classList.add('hidden');
   if(!bar||!sel||!lab||!wrap||!mode)return;
   bar.classList.remove('hidden');wrap.classList.remove('hidden');wrap.classList.add('v119-oper-mode');
   const allowed=modes.map(x=>x[0]);
   const previous=allowed.includes(mode.value)?mode.value:(allowed.includes(OPER_PERIOD.type)?OPER_PERIOD.type:'week');
   mode.innerHTML=modes.map(([v,t])=>`<option value="${v}">${t}</option>`).join('');
   mode.value=allowed.includes(previous)?previous:'week';
   const t=mode.value;OPER_PERIOD.type=t;
   const list=t==='day'?(d?.available_dates||[]):t==='week'?(d?.available_weeks||[]):t==='month'?(d?.available_months||[]):yearsFrom(d);
   lab.textContent=t==='day'?'Fecha':t==='week'?'Semana ISO':t==='month'?'Mes':'Año';
   const current=OPER_PERIOD.value&&list.includes(OPER_PERIOD.value)?OPER_PERIOD.value:(list.at(-1)||'');
   sel.innerHTML=list.map(v=>`<option value="${v}">${v}</option>`).join('');
   sel.value=current;OPER_PERIOD.value=current;
 }

 const baseSet=window.setPeriodSelector;
 window.setPeriodSelector=function(name,d){
   if(name===CENTER){setCenterPeriod(d||OPSDATA||{});return;}
   return baseSet(name,d);
 };

 const baseFetch=window.fetchOpsForView;
 window.fetchOpsForView=async function(name){
   if(name===CENTER && ($('#operPeriodMode')?.value||'')==='year'){
     const year=OPER_PERIOD.value||$('#operPeriodSelect')?.value||'';
     const store=$('#operStoreSelect')?.value||'Compañía',area=$('#operAreaSelect')?.value||'',activity=$('#operActivitySelect')?.value||'';
     return await api(`/api/operations/year?year=${encodeURIComponent(year)}&store=${encodeURIComponent(store)}&area=${encodeURIComponent(area)}&activity=${encodeURIComponent(activity)}&compact=true&project_only=false`,{timeoutMs:180000});
   }
   return baseFetch(name);
 };

 const baseDownload=window.downloadCurrentReport;
 window.downloadCurrentReport=async function(format,name,button){
   if(name===CENTER && ($('#operPeriodMode')?.value||'')==='year'){
     const year=OPER_PERIOD.value||$('#operPeriodSelect')?.value||'';
     const store=$('#operStoreSelect')?.value||'Compañía',area=$('#operAreaSelect')?.value||'',activity=$('#operActivitySelect')?.value||'';
     const url=`/api/export/operations/year?format=${encodeURIComponent(format)}&report=${encodeURIComponent(name)}&year=${encodeURIComponent(year)}&store=${encodeURIComponent(store)}&area=${encodeURIComponent(area)}&activity=${encodeURIComponent(activity)}&project_only=false`;
     const old=button?.textContent||'Descargar';
     try{
       if(button){button.disabled=true;button.textContent='Generando…'}
       const res=await fetch(url,{credentials:'same-origin',cache:'no-store'});
       if(!res.ok){let msg=`Error ${res.status}`;try{const j=await res.json();msg=j.detail||msg}catch(_){}throw new Error(msg)}
       const blob=await res.blob();
       if(format==='pdf'&&blob.type&&!blob.type.includes('pdf'))throw new Error('El servidor no devolvió un PDF válido.');
       const cd=res.headers.get('content-disposition')||'',match=cd.match(/filename="?([^";]+)"?/i),filename=match?.[1]||`Centro_Operativo_${year}.${format}`;
       const obj=URL.createObjectURL(blob),a=document.createElement('a');a.href=obj;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(obj),1500);
       if(button)button.textContent='Descargado ✓';
     }catch(e){alert('No fue posible descargar el reporte anual: '+(e.message||e));}
     finally{setTimeout(()=>{if(button){button.disabled=false;button.textContent=old}},1200)}
     return;
   }
   return baseDownload(format,name,button);
 };

 const baseRender=window.renderOperativoView;
 window.renderOperativoView=async function(name,force=false){
   const out=await baseRender(name,force);
   if(name===CENTER){
     const title=$('#operativoDynamicTitle'),sub=$('#operativoDynamicSub');
     if(title)title.textContent='Centro Operativo';
     if(sub)sub.textContent='Indicadores operativos por día, semana, mes o año · conversión, productividad y recorridos';
   }
   return out;
 };

 // Ajustes únicos y seguros: sin MutationObserver.
 const btn=document.querySelector('#operativoNav [data-opview="Centro Ejecutivo"]');if(btn)btn.textContent='Centro Operativo';
 const label=$('#operPeriodModeLabel');if(label)label.textContent='Vista operativa';
 console.info('[V119] Centro Operativo seguro + filtro Anual activo');
})();
</script>'''

    @m.app.middleware("http")
    async def _v119_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            # V118 queda desinstalado en server_entry, pero por seguridad retirar
            # cualquier script antiguo si una caché/intermedio llegara a incluirlo.
            import re
            html=re.sub(r'<script id="v118-centro-operativo-js">.*?</script>','',html,flags=re.S)
            html=html.replace('>Centro Ejecutivo</button>','>Centro Operativo</button>')
            if 'v119-centro-operativo-js' not in html:
                html=html.replace('</head>',css+'</head>',1).replace('</body>',js+'</body>',1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V119'
            })
        except Exception as exc:
            print(f"[V119] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V119_CENTRO_OPERATIVO_SAFE_ANNUAL=True
    print('[V119] Congelamiento V118 corregido · Centro Operativo con Día/Semanal/Mensual/Anual.',flush=True)
