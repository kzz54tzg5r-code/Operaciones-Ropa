"""V117: paridad visual completa para Día / Semanal / Mensual.

Web:
- Orden de detalle: Acondicionado, Ubicado, % Acondicionado, % Ubicado.
- Semanal y Mensual usan las mismas 10 tarjetas que Día (6 + 4).

PDF:
- Día, Semanal y Mensual comparten encabezado, colores, tarjetas, tabla rayada,
  semáforos y gráfica operativa.
- Semanal/Mensual conservan además el bloque de recuperación por tienda.
"""
from __future__ import annotations
import io


def install(m):
    if getattr(m, "_V117_OPERATIONAL_VISUAL_PARITY", False):
        return
    from fastapi.responses import HTMLResponse

    css=r'''<style id="v117-css">
.v117-pct{font-weight:950}.v117-good{color:#159447!important}.v117-warn{color:#d99b00!important}.v117-bad{color:#d72c2c!important}
</style>'''
    js=r'''<script id="v117-js">
(function(){
 const n=v=>Number(v||0), pt=v=>`${n(v).toFixed(1)}%`, pc=v=>n(v)>=80?'v117-good':(n(v)>=65?'v117-warn':'v117-bad');
 const zero=v=>n(v)===0?`<b class="zero-alert">${fmt(v)}</b>`:fmt(v);
 operationalDetailTable=function(stores,recovery=[]){
   const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
   return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
   <th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>Ubicado</th><th>% Acondicionado</th><th>% Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th>
   </tr></thead><tbody>${rows.map((r,i)=>{const t=Number(r.total_pzs??r.ingresos??0),pa=r.pct_acondicionado!=null?Number(r.pct_acondicionado):(t?Number(r.acondicionado||0)/t*100:0),pu=r.pct_ubicado!=null?Number(r.pct_ubicado):(t?Number(r.ubicado||0)/t*100:0);return `<tr class="${r.is_project?'project-row':''}"><td><b>#${i+1}</b></td><td><b>${r.store}</b></td><td>${zero(r.dev_pzs)}</td><td>${zero(r.muertos)}</td><td>${zero(r.probador)}</td><td>${zero(r.cajas)}</td><td>${zero(r.pendiente_anterior||0)}</td><td><b>${fmt(t)}</b></td><td>${zero(r.recorridos)}</td><td>${zero(r.acondicionado)}</td><td>${zero(r.ubicado)}</td><td><b class="v117-pct ${pc(pa)}">${pt(pa)}</b></td><td><b class="v117-pct ${pc(pu)}">${pt(pu)}</b></td><td>${fmt(r.pendiente_acondicionar)}</td><td>${fmt(r.pendiente_ubicar)}</td></tr>`}).join('')}</tbody></table></div>`;
 };
 const oldRender=renderOperativoView;
 renderOperativoView=async function(name,force=false){
   await oldRender(name,force);
   if(!['Reporte Semanal','Reporte Mensual'].includes(name))return;
   try{
     const type=currentPeriodTypeForView(name),value=OPER_PERIOD.value||'',store=$('#operStoreSelect')?.value||'Compañía',area=$('#operAreaSelect')?.value||'',activity=$('#operActivitySelect')?.value||'';
     const d=await api(`/api/operations?store=${encodeURIComponent(store)}&period_type=${encodeURIComponent(type)}&period_value=${encodeURIComponent(value)}&area=${encodeURIComponent(area)}&activity=${encodeURIComponent(activity)}&start_date=&end_date=&compact=true&project_only=false`,{timeoutMs:180000});const mt=d.metrics||{};
     const html=reportKpis([
       kpiCard('Dev pzs',fmt(mt.dev_pzs),'Devoluciones del periodo','#173F78'),kpiCard('Muertos',fmt(mt.muertos),'Recolección · motivo Muertos','#EC007C'),kpiCard('Probador',fmt(mt.probador),'Motivo Probador','#F3A300'),kpiCard('Cajas',fmt(mt.cajas),'Recolección · Cajas','#7338EF'),kpiCard('Total pzs',fmt(mt.total_pzs??mt.ingresos),'Dev + Muertos + Cajas + Probador + Pend. Ant.','#246FE5'),kpiCard('Recorridos realizados',fmt(mt.recorridos),`${pct(mt.pct_recorridos||0)} · meta ${fmt(mt.meta_recorridos||0)}`,'#10B981'),
       kpiCard('% Acondicionado',pct(mt.pct_acondicionado),`${fmt(mt.acondicionado)} piezas acondicionadas`,'#7338EF',metricClass(mt.pct_acondicionado,80,65)),kpiCard('% Ubicado',pct(mt.pct_ubicado),`${fmt(mt.ubicado)} piezas ubicadas`,'#EC007C',metricClass(mt.pct_ubicado,80,65)),kpiCard('Pendiente de acondicionar',fmt(mt.pendiente_acondicionar),'Total pzs - Acondicionado','#F3A300'),kpiCard('Pendiente de ubicar',fmt(mt.pendiente_ubicar),'Total pzs - Ubicado','#EF3434')]);
     const cur=document.querySelector('#operativoDynamicContent .report-kpis');if(cur){const x=document.createElement('div');x.innerHTML=html;cur.replaceWith(x.firstElementChild)}
   }catch(e){console.warn('[V117] tarjetas semana/mes',e)}
 };
})();</script>'''

    @m.app.middleware("http")
    async def _v117_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v117-js" not in html:html=html.replace("</head>",css+"</head>",1).replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"})
        except Exception as exc:
            print(f"[V117-WEB] {type(exc).__name__}: {exc}",flush=True);return response

    old_pdf=m._build_operations_pdf
    def build_pdf(data:dict,report:str,scope:str="Compañía")->bytes:
        if report not in ("Operación Diaria","Reporte Semanal","Reporte Mensual"):return old_pdf(data,report,scope)
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape,letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth
        def n(v):
            try:return float(v or 0)
            except:return 0.0
        def f(v):return f"{n(v):,.0f}"
        def pctv(v):return f"{n(v):.1f}%"
        NAVY="#173F78";NAVY2="#1D4A83";BLUE="#246FE5";PINK="#EC007C";PURPLE="#7338EF";GREEN="#10B981";GOLD="#F3A300";RED="#EF3434";TEXT="#0F3463";MUT="#667892";LINE="#D6E0EC";BG="#F2F6FB";ALT="#EAF2FC";PROJ="#DDEAFF"
        def pcol(v):return GREEN if n(v)>=80 else (GOLD if n(v)>=65 else RED)
        rows=list(data.get("stores") or []);metrics=data.get("metrics") or {};rec=list(data.get("recovery_by_store") or []);period=str(data.get("period_value") or "Histórico")
        details=rows if report=="Operación Diaria" else ([r for r in rows if r.get("is_project")] or rows)
        label={"Operación Diaria":"Operación Diaria","Reporte Semanal":"Reporte Semanal","Reporte Mensual":"Reporte Mensual"}[report]
        W,H=landscape(letter);M=28;bio=io.BytesIO();c=canvas.Canvas(bio,pagesize=(W,H))
        def header(suffix=""):
            c.setFillColor(colors.HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(colors.HexColor(NAVY2));c.roundRect(M,H-92,W-2*M,64,12,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",18);c.drawString(M+18,H-56,"Cambios y Muertos");c.setFont("Helvetica",8);c.drawString(M+18,H-74,"Recuperación, conversión, recolección y seguimiento operativo");c.setFont("Helvetica-Bold",9.2);c.drawRightString(W-M-18,H-54,"Operaciones Ropa - Price Shoes");c.setFont("Helvetica",7.4);c.drawRightString(W-M-18,H-72,label+((" · "+suffix) if suffix else ""))
        def card(x,y,w,h,lab,val,sub,accent,vcol=None):
            c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(x,y,w,h,8,fill=1,stroke=1);c.setFillColor(colors.HexColor(accent));c.rect(x,y,4.5,h,fill=1,stroke=0);c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica-Bold",6);c.drawString(x+11,y+h-17,lab.upper()[:30]);c.setFillColor(colors.HexColor(vcol or TEXT));c.setFont("Helvetica-Bold",15.5);c.drawString(x+11,y+h-40,val);c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",5.5);c.drawString(x+11,y+7,sub[:42])
        def cards(y):
            gap=8;cw=(W-2*M-gap*5)/6;ch=58
            a=[("Dev pzs",f(metrics.get("dev_pzs")),"Devoluciones del periodo",NAVY,None),("Muertos",f(metrics.get("muertos")),"Recolección · motivo Muertos",PINK,None),("Probador",f(metrics.get("probador")),"Motivo Probador",GOLD,RED if n(metrics.get("probador"))==0 else None),("Cajas",f(metrics.get("cajas")),"Recolección · Cajas",PURPLE,RED if n(metrics.get("cajas"))==0 else None),("Total pzs",f(metrics.get("total_pzs",metrics.get("ingresos"))),"Dev + Muertos + Cajas + Probador + Pend. Ant.",BLUE,None),("Recorridos realizados",f(metrics.get("recorridos")),f"{pctv(metrics.get('pct_recorridos'))} · meta {f(metrics.get('meta_recorridos'))}",GREEN,None)]
            b=[("% Acondicionado",pctv(metrics.get("pct_acondicionado")),f"{f(metrics.get('acondicionado'))} piezas acondicionadas",PURPLE,pcol(metrics.get("pct_acondicionado"))),("% Ubicado",pctv(metrics.get("pct_ubicado")),f"{f(metrics.get('ubicado'))} piezas ubicadas",PINK,pcol(metrics.get("pct_ubicado"))),("Pendiente de acondicionar",f(metrics.get("pendiente_acondicionar")),"Total pzs - Acondicionado",GOLD,None),("Pendiente de ubicar",f(metrics.get("pendiente_ubicar")),"Total pzs - Ubicado",RED,None)]
            y1=y-ch
            for i,it in enumerate(a):card(M+i*(cw+gap),y1,cw,ch,*it)
            y2=y1-gap-ch
            for i,it in enumerate(b):card(M+i*(cw+gap),y2,cw,ch,*it)
            return y2-16
        def detail(y,rr):
            c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold",11.5);c.drawString(M,y,f"Detalle operativo · {period}");y-=16
            heads=[["Ranking"],["Tienda"],["Dev","pzs"],["Muertos"],["Probador"],["Cajas"],["Pend.","Ant."],["Total","pzs"],["Recorridos","realizados"],["Acondicionado"],["Ubicado"],["% Acond."],["% Ubicado"],["Pendiente de","acondicionar"],["Pendiente de","ubicar"]];fr=[.042,.105,.055,.05,.052,.045,.058,.055,.074,.065,.058,.068,.064,.105,.104];tw=W-2*M;xs=[M];acc=M
            for q in fr[:-1]:acc+=tw*q;xs.append(acc)
            hh=24;c.setFillColor(colors.HexColor(NAVY2));c.roundRect(M,y-hh+2,tw,hh,5,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",4.7)
            for j,ls in enumerate(heads):c.drawString(xs[j]+2,y-8,ls[0]);len(ls)>1 and c.drawString(xs[j]+2,y-15,ls[1])
            y-=hh;rh=17 if len(rr)<=7 else (14 if len(rr)<=12 else 11.5)
            for i,r in enumerate(rr):
                total=r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos");pa=r.get("pct_acondicionado");pu=r.get("pct_ubicado");pa=n(pa) if pa is not None else (n(r.get("acondicionado"))/n(total)*100 if n(total) else 0);pu=n(pu) if pu is not None else (n(r.get("ubicado"))/n(total)*100 if n(total) else 0)
                c.setFillColor(colors.HexColor(PROJ if r.get("is_project") else (ALT if i%2 else "#FFFFFF")));c.rect(M,y-rh+2,tw,rh,fill=1,stroke=0)
                if r.get("is_project"):c.setFillColor(colors.HexColor(BLUE));c.rect(M,y-rh+2,3,rh,fill=1,stroke=0)
                vals=[f"#{i+1}",str(r.get("store") or ""),f(r.get("dev_pzs")),f(r.get("muertos")),f(r.get("probador")),f(r.get("cajas")),f(r.get("pendiente_anterior")),f(total),f(r.get("recorridos")),f(r.get("acondicionado")),f(r.get("ubicado")),pctv(pa),pctv(pu),f(r.get("pendiente_acondicionar")),f(r.get("pendiente_ubicar"))]
                for j,v in enumerate(vals):
                    col=TEXT
                    if j in (2,3,4,5,6,7,8,9,10) and n(str(v).replace(',',''))==0:col=RED
                    if j==11:col=pcol(pa)
                    if j==12:col=pcol(pu)
                    c.setFillColor(colors.HexColor(col));c.setFont("Helvetica-Bold" if j in (0,1,7,11,12) else "Helvetica",5 if len(rr)<=10 else 4.6);c.drawString(xs[j]+2,y-10,str(v)[:23])
                y-=rh
            return y-10
        def graph(y,rr):
            ph=min(220,max(165,y-28));py=y-ph;c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(M,py,W-2*M,ph,9,fill=1,stroke=1);c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold",12);c.drawString(M+20,y-26,f"Ingreso vs Acondicionado vs Ubicado · Todas las tiendas · {period}")
            x0=M+62;x1=W-M-18;base=py+28;top=y-58;h=max(68,top-base);mx=max([n(v) for r in rr for v in (r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"),r.get("acondicionado"),r.get("ubicado"))]+[1])*1.15;gw=(x1-x0)/max(1,len(rr));bw=min(15,gw*.20);pts=[]
            for q in range(5):gy=base+h*q/4;c.setStrokeColor(colors.HexColor(LINE));c.line(x0,gy,x1,gy);c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",5);c.drawRightString(x0-6,gy-2,f(mx*q/4))
            for i,r in enumerate(rr):
                cx=x0+gw*(i+.5);tot=n(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"));ac=n(r.get("acondicionado"));ub=n(r.get("ubicado"));ah=h*ac/mx;uh=h*ub/mx;c.setFillColor(colors.HexColor(NAVY2));c.rect(cx-bw-2,base,bw,max(.7,ah),fill=1,stroke=0);c.setFillColor(colors.HexColor(PINK));c.rect(cx+2,base,bw,max(.7,uh),fill=1,stroke=0);yy=base+h*tot/mx;pts.append((cx,yy));c.setFillColor(colors.HexColor(BLUE));c.circle(cx,yy,2.6,fill=1,stroke=0);c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica",5.2);c.drawCentredString(cx,base-14,str(r.get("store") or "")[:13])
            c.setStrokeColor(colors.HexColor(BLUE));c.setLineWidth(1.7)
            for a,b in zip(pts,pts[1:]):c.line(a[0],a[1],b[0],b[1])
        def recovery_page():
            c.showPage();header("Recuperación por tienda");y=H-112;c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica-Bold",12);c.drawString(M,y,"Recuperación por tienda");y-=17;tw=W-2*M;heads=["#","Tienda","Dev Pzs","Pzas recup.","Conversión","Valor devolución","Recuperación $","Recup. %","Pend. Pzs","Pend. $"];fr=[.04,.15,.08,.09,.09,.12,.13,.09,.09,.11];xs=[M];acc=M
            for q in fr[:-1]:acc+=tw*q;xs.append(acc)
            c.setFillColor(colors.HexColor(NAVY2));c.roundRect(M,y-19+2,tw,19,5,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",4.8)
            for j,hx in enumerate(heads):c.drawString(xs[j]+2,y-8,hx)
            y-=19;project={str(r.get('store')):r.get('is_project') for r in rows}
            for i,r in enumerate(rec):
                c.setFillColor(colors.HexColor(PROJ if project.get(str(r.get('store'))) else (ALT if i%2 else '#FFFFFF')));c.rect(M,y-13+2,tw,13,fill=1,stroke=0);vals=[f"#{i+1}",r.get("store",""),f(r.get("dev_pzs")),f(r.get("converted_pieces")),pctv(r.get("conversion_pct")),f"${n(r.get('return_value')):,.0f}",f"${n(r.get('recovered_value')):,.0f}",pctv(r.get("recovery_pct")),f(r.get("pending_pieces")),f"${n(r.get('pending_value')):,.0f}"];c.setFillColor(colors.HexColor(TEXT));c.setFont("Helvetica",4.7)
                for j,v in enumerate(vals):c.drawString(xs[j]+2,y-9,str(v)[:24])
                y-=13
        header();y=H-107;c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",7.2);c.drawString(M,y,f"Periodo: {period}   ·   Alcance: {scope}");y-=14;y=cards(y);y=detail(y,details)
        if y<205:c.showPage();header("gráfico");y=H-112
        graph(y,details)
        if report in ("Reporte Semanal","Reporte Mensual") and rec:recovery_page()
        c.save();pdf=bio.getvalue();return pdf if pdf.startswith(b"%PDF") else old_pdf(data,report,scope)
    m._build_operations_pdf=build_pdf
    m._V117_OPERATIONAL_VISUAL_PARITY=True
    print("[V117] Día/Semanal/Mensual con mismo diseño web/PDF y orden Acondicionado, Ubicado, %Acond., %Ubicado.",flush=True)
