"""V116: paridad visual Día / Semanal / Mensual en web y PDF.

- Tabla: Acondicionado | Ubicado | % Acondicionado | % Ubicado.
- Semanal y Mensual usan las mismas 10 tarjetas de Operación Diaria.
- PDF de Día, Semanal y Mensual comparte colores, tarjetas, tablas y semáforos.
- Semanal/Mensual conservan Recuperación por tienda y sus gráficas.
"""
from __future__ import annotations

import io


def install(m):
    if getattr(m, "_V116_OPERATIONAL_MIRROR", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v116-operational-mirror-css">
.v116-pct{font-weight:950}.v116-good{color:#159447!important}.v116-warn{color:#d99b00!important}.v116-bad{color:#d72c2c!important}
</style>
'''

    js = r'''
<script id="v116-operational-mirror-js">
(function(){
  const n=v=>Number(v||0);
  const p=v=>`${n(v).toFixed(1)}%`;
  const pc=v=>n(v)>=80?'v116-good':(n(v)>=65?'v116-warn':'v116-bad');
  const z=v=>n(v)===0?`<b class="zero-alert">${fmt(v)}</b>`:fmt(v);

  operationalDetailTable=function(stores,recovery=[]){
    const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
    return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
      <th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>Ubicado</th><th>% Acondicionado</th><th>% Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th>
    </tr></thead><tbody>${rows.map((r,i)=>{
      const total=Number(r.total_pzs ?? r.ingresos ?? 0);
      const pac=r.pct_acondicionado!=null?Number(r.pct_acondicionado):(total?Number(r.acondicionado||0)/total*100:0);
      const pub=r.pct_ubicado!=null?Number(r.pct_ubicado):(total?Number(r.ubicado||0)/total*100:0);
      return `<tr class="${r.is_project?'project-row':''}">
        <td><b>#${i+1}</b></td><td><b>${r.store}</b></td>
        <td>${z(r.dev_pzs)}</td><td>${z(r.muertos)}</td><td>${z(r.probador)}</td><td>${z(r.cajas)}</td><td>${z(r.pendiente_anterior||0)}</td><td><b>${fmt(total)}</b></td><td>${z(r.recorridos)}</td>
        <td>${z(r.acondicionado)}</td><td>${z(r.ubicado)}</td>
        <td><b class="v116-pct ${pc(pac)}">${p(pac)}</b></td><td><b class="v116-pct ${pc(pub)}">${p(pub)}</b></td>
        <td>${fmt(r.pendiente_acondicionar)}</td><td>${fmt(r.pendiente_ubicar)}</td>
      </tr>`;
    }).join('')}</tbody></table></div>`;
  };

  const oldRender=renderOperativoView;
  renderOperativoView=async function(name,force=false){
    await oldRender(name,force);
    if(name!=='Reporte Semanal' && name!=='Reporte Mensual')return;
    try{
      const type=currentPeriodTypeForView(name), value=OPER_PERIOD.value||'';
      const store=$('#operStoreSelect')?.value||'Compañía', area=$('#operAreaSelect')?.value||'', activity=$('#operActivitySelect')?.value||'';
      const d=await api(`/api/operations?store=${encodeURIComponent(store)}&period_type=${encodeURIComponent(type)}&period_value=${encodeURIComponent(value)}&area=${encodeURIComponent(area)}&activity=${encodeURIComponent(activity)}&start_date=&end_date=&compact=true&project_only=false`,{timeoutMs:180000});
      const mt=d.metrics||{};
      const cards=reportKpis([
        kpiCard('Dev pzs',fmt(mt.dev_pzs),'Devoluciones del periodo','#173B73'),
        kpiCard('Muertos',fmt(mt.muertos),'Recolección · motivo Muertos','#EC007C'),
        kpiCard('Probador',fmt(mt.probador),'Motivo Probador','#F59E0B'),
        kpiCard('Cajas',fmt(mt.cajas),'Recolección · Cajas','#7C3AED'),
        kpiCard('Total pzs',fmt(mt.total_pzs??mt.ingresos),'Dev + Muertos + Cajas + Probador','#246FE5'),
        kpiCard('Recorridos realizados',fmt(mt.recorridos),`${pct(mt.pct_recorridos||0)} · meta ${fmt(mt.meta_recorridos||0)}`,'#10B981'),
        kpiCard('% Acondicionado',pct(mt.pct_acondicionado),`${fmt(mt.acondicionado)} piezas acondicionadas`,'#7C3AED',metricClass(mt.pct_acondicionado,80,65)),
        kpiCard('% Ubicado',pct(mt.pct_ubicado),`${fmt(mt.ubicado)} piezas ubicadas`,'#EC007C',metricClass(mt.pct_ubicado,80,65)),
        kpiCard('Pendiente de acondicionar',fmt(mt.pendiente_acondicionar),'Total pzs - Acondicionado','#F59E0B'),
        kpiCard('Pendiente de ubicar',fmt(mt.pendiente_ubicar),'Total pzs - Ubicado','#EF4444')
      ]);
      const host=document.querySelector('#operativoDynamicContent .report-kpis');
      if(host){const temp=document.createElement('div');temp.innerHTML=cards;const repl=temp.firstElementChild;if(repl)host.replaceWith(repl)}
    }catch(e){console.warn('[V116] No se pudieron homogeneizar tarjetas',e)}
  };
  console.log('[V116] Día/Semanal/Mensual: tarjetas y detalle operativo unificados.');
})();
</script>
'''

    @m.app.middleware("http")
    async def _v116_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator: body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v116-operational-mirror-js" not in html:
                html=html.replace("</head>",css+"</head>",1).replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"})
        except Exception as exc:
            print(f"[V116-WEB] warning {type(exc).__name__}: {exc}",flush=True)
            return response

    old_pdf=m._build_operations_pdf

    def build_pdf(d:dict,report:str,scope:str="Compañía")->bytes:
        if report not in ("Operación Diaria","Reporte Semanal","Reporte Mensual"):
            return old_pdf(d,report,scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth

        def num(v):
            try:return float(v or 0)
            except Exception:return 0.0
        def f(v):return f"{num(v):,.0f}"
        def pctv(v):return f"{num(v):.1f}%"
        def pcolor(v):
            v=num(v)
            return GREEN if v>=80 else (ORANGE if v>=65 else RED)

        BLUE="#173B73"; BLUE2="#246FE5"; PINK="#EC007C"; PURPLE="#7C3AED"; GREEN="#10B981"; ORANGE="#F59E0B"; RED="#EF4444"; TXT="#102A56"; MUT="#6B778C"; LINE="#D7E0EA"; BG="#F3F6FA"; PROJECT="#DDEAFF"
        W,H=landscape(letter); M=26; bio=io.BytesIO(); c=canvas.Canvas(bio,pagesize=(W,H))
        rows=list(d.get("stores") or []); mt=d.get("metrics") or {}; rec=list(d.get("recovery_by_store") or []); period=str(d.get("period_value") or "Histórico")
        project_rows=[r for r in rows if r.get("is_project")]
        detail_rows=rows if report=="Operación Diaria" else (project_rows or rows)
        report_label={"Operación Diaria":"Operación Diaria","Reporte Semanal":"Reporte Semanal","Reporte Mensual":"Reporte Mensual"}[report]

        def header(suffix=""):
            c.setFillColor(colors.HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,H-88,W-2*M,58,11,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setFont("Helvetica-Bold",17);c.drawString(M+18,H-55,"Cambios y Muertos")
            c.setFont("Helvetica",8);c.drawString(M+18,H-72,"Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold",9);c.drawRightString(W-M-18,H-54,"Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica",7);c.drawRightString(W-M-18,H-70,report_label+((" · "+suffix) if suffix else ""))

        def cards(y):
            items=[
              ("DEV PZS",f(mt.get("dev_pzs")),"Devoluciones del periodo",BLUE),
              ("MUERTOS",f(mt.get("muertos")),"Recolección · motivo Muertos",PINK),
              ("PROBADOR",f(mt.get("probador")),"Motivo Probador",ORANGE),
              ("CAJAS",f(mt.get("cajas")),"Recolección · Cajas",PURPLE),
              ("TOTAL PZS",f(mt.get("total_pzs",mt.get("ingresos"))),"Dev + Muertos + Cajas + Probador",BLUE2),
              ("RECORRIDOS REALIZADOS",f(mt.get("recorridos")),f"{pctv(mt.get('pct_recorridos'))} · meta {f(mt.get('meta_recorridos'))}",GREEN),
              ("% ACONDICIONADO",pctv(mt.get("pct_acondicionado")),f"{f(mt.get('acondicionado'))} piezas acondicionadas",PURPLE),
              ("% UBICADO",pctv(mt.get("pct_ubicado")),f"{f(mt.get('ubicado'))} piezas ubicadas",PINK),
              ("PENDIENTE DE ACONDICIONAR",f(mt.get("pendiente_acondicionar")),"Total pzs - Acondicionado",ORANGE),
              ("PENDIENTE DE UBICAR",f(mt.get("pendiente_ubicar")),"Total pzs - Ubicado",RED),
            ]
            gap=7;cw=(W-2*M-gap*4)/5;ch=53
            for i,(lab,val,sub,col) in enumerate(items):
                rr=i//5;cc=i%5;x=M+cc*(cw+gap);yy=y-rr*(ch+gap)-ch
                c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(x,yy,cw,ch,7,fill=1,stroke=1)
                c.setFillColor(colors.HexColor(col));c.rect(x,yy,4,ch,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica-Bold",5.8);c.drawString(x+10,yy+38,lab)
                valcol=pcolor(mt.get("pct_acondicionado")) if lab=="% ACONDICIONADO" else (pcolor(mt.get("pct_ubicado")) if lab=="% UBICADO" else TXT)
                c.setFillColor(colors.HexColor(valcol));c.setFont("Helvetica-Bold",15);c.drawString(x+10,yy+18,val)
                c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",5.2);c.drawString(x+10,yy+7,sub[:38])
            return y-2*(ch+gap)-4

        def section_title(y,text):
            c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica-Bold",11);c.drawString(M,y,text);return y-15

        def detail_table(y, rr):
            head=["#","Tienda","Dev","Muertos","Prob.","Cajas","Pend.Ant.","Total","Recorr.","Acond.","Ubicado","% Acond.","% Ubic.","Pend.Acond.","Pend.Ubic."]
            fr=[.032,.105,.056,.052,.052,.048,.062,.06,.067,.064,.06,.072,.066,.102,.102];tw=W-2*M;xs=[M];acc=M
            for zf in fr[:-1]:acc+=tw*zf;xs.append(acc)
            hh=19;c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,y-hh+3,tw,hh,4,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",4.2)
            for j,h in enumerate(head):c.drawString(xs[j]+2,y-8,h)
            y-=hh; rh=13 if len(rr)<=7 else (11.5 if len(rr)<=12 else 10.3)
            for i,r in enumerate(rr):
                total=r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"); pac=r.get("pct_acondicionado"); pub=r.get("pct_ubicado")
                if pac is None: pac=num(r.get("acondicionado"))/num(total)*100 if num(total) else 0
                if pub is None: pub=num(r.get("ubicado"))/num(total)*100 if num(total) else 0
                vals=[f"#{i+1}",r.get("store",""),f(r.get("dev_pzs")),f(r.get("muertos")),f(r.get("probador")),f(r.get("cajas")),f(r.get("pendiente_anterior")),f(total),f(r.get("recorridos")),f(r.get("acondicionado")),f(r.get("ubicado")),pctv(pac),pctv(pub),f(r.get("pendiente_acondicionar")),f(r.get("pendiente_ubicar"))]
                c.setFillColor(colors.HexColor(PROJECT if r.get("is_project") else ("#F7FAFD" if i%2 else "#FFFFFF")));c.rect(M,y-rh+2,tw,rh,fill=1,stroke=0)
                if r.get("is_project"):c.setFillColor(colors.HexColor(BLUE2));c.rect(M,y-rh+2,3,rh,fill=1,stroke=0)
                c.setFont("Helvetica",4.25)
                for j,v in enumerate(vals):
                    col=TXT
                    if j in (2,3,4,5,6,7,8,9,10) and num(v)==0: col=RED
                    if j==11: col=pcolor(pac)
                    if j==12: col=pcolor(pub)
                    c.setFillColor(colors.HexColor(col));c.drawString(xs[j]+2,y-8,str(v)[:20])
                y-=rh
            return y-7

        def ops_chart(y, rr, title):
            y=section_title(y,title); x0=M+42;x1=W-M-12;base=42;top=y-8;ph=max(95,top-base);gw=(x1-x0)/max(1,len(rr));bw=min(13,gw*.22)
            mx=max([num(v) for r in rr for v in ((r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")),r.get("acondicionado"),r.get("ubicado"))]+[1])*1.15
            c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.6)
            for q in range(5):gy=base+ph*q/4;c.line(x0,gy,x1,gy);c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",5);c.drawRightString(x0-5,gy-2,f(mx*q/4))
            pts=[]
            for i,r in enumerate(rr):
                cx=x0+gw*(i+.5);total=num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"));ac=num(r.get("acondicionado"));ub=num(r.get("ubicado"))
                ah=ph*ac/mx;uh=ph*ub/mx;c.setFillColor(colors.HexColor(BLUE));c.rect(cx-bw-2,base,bw,max(.8,ah),fill=1,stroke=0);c.setFillColor(colors.HexColor(PINK));c.rect(cx+2,base,bw,max(.8,uh),fill=1,stroke=0)
                c.setFillColor(colors.HexColor(BLUE));c.setFont("Helvetica-Bold",5);c.drawCentredString(cx-bw/2-2,base+ah+3,"A "+f(ac));c.setFillColor(colors.HexColor(PINK));c.drawCentredString(cx+bw/2+2,base+uh+3,"U "+f(ub))
                py=base+ph*total/mx;pts.append((cx,py,total));c.setFillColor(colors.HexColor(BLUE2));c.circle(cx,py,2.5,fill=1,stroke=0);c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica",5.2);c.drawCentredString(cx,base-13,str(r.get("store",""))[:13])
            c.setStrokeColor(colors.HexColor(BLUE2));c.setLineWidth(1.4)
            for a,b in zip(pts,pts[1:]):c.line(a[0],a[1],b[0],b[1])
            for cx,py,total in pts:c.setFillColor(colors.HexColor(BLUE2));c.setFont("Helvetica-Bold",5);c.drawCentredString(cx,min(top,py+6),"Total "+f(total))

        def recovery_table(y):
            if not rec:return y
            y=section_title(y,"Recuperación por tienda")
            heads=["#","Tienda","Dev Pzs","Pzas recup.","Conversión","Valor dev.","Recuperación $","Recup. %","Pend. Pzs","Pend. $"];fr=[.035,.15,.08,.09,.09,.12,.13,.09,.09,.115];tw=W-2*M;xs=[M];acc=M
            for zf in fr[:-1]:acc+=tw*zf;xs.append(acc)
            c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,y-17+3,tw,17,4,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",4.5)
            for j,h in enumerate(heads):c.drawString(xs[j]+2,y-7,h)
            y-=17; project={str(r.get('store')):bool(r.get('is_project')) for r in rows}
            for i,r in enumerate(rec):
                vals=[f"#{i+1}",r.get("store",""),f(r.get("dev_pzs")),f(r.get("converted_pieces")),pctv(r.get("conversion_pct")),f"${num(r.get('return_value')):,.0f}",f"${num(r.get('recovered_value')):,.0f}",pctv(r.get("recovery_pct")),f(r.get("pending_pieces")),f"${num(r.get('pending_value')):,.0f}"]
                c.setFillColor(colors.HexColor(PROJECT if project.get(str(r.get('store'))) else ("#F7FAFD" if i%2 else "#FFFFFF")));c.rect(M,y-9+1,tw,9,fill=1,stroke=0)
                if project.get(str(r.get('store'))):c.setFillColor(colors.HexColor(BLUE2));c.rect(M,y-8,3,9,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica",4.1)
                for j,v in enumerate(vals):c.drawString(xs[j]+2,y-6,str(v)[:21])
                y-=9
            return y-5

        # Página 1
        header(); y=H-105;c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",7);c.drawString(M,y,f"Periodo: {period}   ·   Alcance: {scope}");y-=13;y=cards(y)
        if report=="Operación Diaria":
            y=section_title(y,"Detalle operativo · "+period);y=detail_table(y,detail_rows)
            if y<210:c.showPage();header("gráfico");y=H-106
            ops_chart(y,detail_rows,"Ingreso vs Acondicionado vs Ubicado · "+period)
        else:
            y=recovery_table(y)
            c.showPage();header("Detalle operativo");y=H-106;y=section_title(y,"Detalle operativo · tiendas del proyecto");y=detail_table(y,detail_rows)
            if y<210:c.showPage();header("gráfico operativo");y=H-106
            ops_chart(y,detail_rows,"Ingreso vs Acondicionado vs Ubicado · "+period)

        c.save();pdf=bio.getvalue();return pdf if pdf.startswith(b"%PDF") else old_pdf(d,report,scope)

    m._build_operations_pdf=build_pdf
    m._V116_OPERATIONAL_MIRROR=True
    print("[V116] Día/Semanal/Mensual unificados en tarjetas, tabla y PDF.",flush=True)
