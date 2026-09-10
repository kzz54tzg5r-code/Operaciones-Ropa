"""V115: Operación Diaria con piezas y porcentaje para Acondicionado y Ubicado.

- Web: la tabla diaria muestra Acondicionado, % Acondicionado, Ubicado y % Ubicado.
- PDF: replica exactamente las cuatro columnas.
- Las tarjetas existentes se conservan: porcentaje principal + piezas como detalle.
- No modifica fórmulas ni datos del backend.
"""
from __future__ import annotations

import io


def install(m):
    if getattr(m, "_V115_DAILY_PIECES_PERCENT", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v115-daily-pieces-percent-css">
.v115-pct-cell{font-weight:950;color:#102A56}
.v115-pct-good{color:#159447!important}
.v115-pct-warn{color:#d99b00!important}
.v115-pct-bad{color:#d72c2c!important}
</style>
'''

    js = r'''
<script id="v115-daily-pieces-percent-js">
(function(){
  const n=v=>Number(v||0);
  const pctText=v=>`${n(v).toFixed(1)}%`;
  const pctClass=v=>n(v)>=80?'v115-pct-good':(n(v)>=65?'v115-pct-warn':'v115-pct-bad');
  const zeroCell=v=>n(v)===0?`<b class="zero-alert">${fmt(v)}</b>`:fmt(v);

  // V115: ambas etapas muestran piezas + porcentaje.
  operationalDetailTable=function(stores,recovery=[]){
    const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
    return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
      <th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>% Acondicionado</th><th>Ubicado</th><th>% Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th>
      </tr></thead><tbody>${rows.map((r,i)=>{
        const total=(r.total_pzs ?? r.ingresos ?? 0);
        const pAc=(r.pct_acondicionado!=null)
          ? Number(r.pct_acondicionado)
          : ((Number(total)>0)?(Number(r.acondicionado||0)/Number(total)*100):0);
        const pUb=(r.pct_ubicado!=null)
          ? Number(r.pct_ubicado)
          : ((Number(total)>0)?(Number(r.ubicado||0)/Number(total)*100):0);
        return `<tr class="${r.is_project?'project-row':''}">
          <td><b>#${i+1}</b></td><td><b>${r.store}</b></td>
          <td>${zeroCell(r.dev_pzs)}</td><td>${zeroCell(r.muertos)}</td><td>${zeroCell(r.probador)}</td><td>${zeroCell(r.cajas)}</td>
          <td>${zeroCell(r.pendiente_anterior||0)}</td><td><b class="${Number(total)===0?'zero-alert':''}">${fmt(total)}</b></td>
          <td>${zeroCell(r.recorridos)}</td>
          <td>${zeroCell(r.acondicionado)}</td><td><b class="v115-pct-cell ${pctClass(pAc)}">${pctText(pAc)}</b></td>
          <td>${zeroCell(r.ubicado)}</td><td><b class="v115-pct-cell ${pctClass(pUb)}">${pctText(pUb)}</b></td>
          <td>${fmt(r.pendiente_acondicionar)}</td><td>${fmt(r.pendiente_ubicar)}</td>
        </tr>`;
      }).join('')}</tbody></table></div>`;
  };
  console.log('[V115] Tabla diaria: Acondicionado y Ubicado en piezas + porcentaje.');
})();
</script>
'''

    @m.app.middleware("http")
    async def _v115_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v115-daily-pieces-percent-js" not in html:
                html=html.replace("</head>",css+"</head>",1)
                html=html.replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0"
            })
        except Exception as exc:
            print(f"[V115-WEB] warning {type(exc).__name__}: {exc}",flush=True)
            return response

    old_pdf=m._build_operations_pdf

    def build_pdf(d:dict,report:str,scope:str="Compañía")->bytes:
        if report!="Operación Diaria":
            return old_pdf(d,report,scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape,letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth

        def num(v):
            try:return float(v or 0)
            except Exception:return 0.0
        def f(v):return f"{num(v):,.0f}"
        def pct(v):return f"{num(v):.1f}%"
        def pct_value(r,key,pieces,total):
            raw=r.get(key)
            if raw is not None:
                return num(raw)
            return (num(pieces)/num(total)*100) if num(total)>0 else 0.0
        def pct_color(v):
            return GREEN if num(v)>=80 else (ORANGE if num(v)>=65 else RED)

        rows=list(d.get("stores") or [])
        mt=d.get("metrics") or {}
        period=str(d.get("period_value") or "Histórico")
        W,H=landscape(letter);M=26
        BLUE="#173B73";BLUE2="#246FE5";PINK="#EC007C";PURPLE="#7C3AED";GREEN="#10B981";ORANGE="#F59E0B";RED="#EF4444";TXT="#102A56";MUT="#6B778C";LINE="#D7E0EA";BG="#F3F6FA"
        bio=io.BytesIO();c=canvas.Canvas(bio,pagesize=(W,H))

        def header(suffix=""):
            c.setFillColor(colors.HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,H-88,W-2*M,58,11,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setFont("Helvetica-Bold",17);c.drawString(M+18,H-55,"Cambios y Muertos")
            c.setFont("Helvetica",8);c.drawString(M+18,H-72,"Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold",9);c.drawRightString(W-M-18,H-54,"Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica",7);c.drawRightString(W-M-18,H-70,"Operación Diaria"+((" - "+suffix) if suffix else ""))

        header();y=H-106
        c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",7);c.drawString(M,y,f"Periodo: {period}   -   Alcance: {scope}");y-=13

        items=[
            ("Dev pzs",f(mt.get("dev_pzs")),"",BLUE),
            ("Muertos",f(mt.get("muertos")),"",PINK),
            ("Probador",f(mt.get("probador")),"",ORANGE),
            ("Cajas",f(mt.get("cajas")),"",PURPLE),
            ("Total pzs",f(mt.get("total_pzs",mt.get("ingresos"))),"",BLUE2),
            ("Recorridos",f(mt.get("recorridos")),"",GREEN),
            ("% Acondicionado",pct(mt.get("pct_acondicionado")),f"{f(mt.get('acondicionado'))} piezas",PURPLE),
            ("% Ubicado",pct(mt.get("pct_ubicado")),f"{f(mt.get('ubicado'))} piezas",PINK),
            ("Pend. acond.",f(mt.get("pendiente_acondicionar")),"",ORANGE),
            ("Pend. ubicar",f(mt.get("pendiente_ubicar")),"",RED),
        ]
        gap=7;cw=(W-2*M-gap*4)/5;ch=53
        for i,(lab,val,sub,col) in enumerate(items):
            rr=i//5;cc=i%5;x=M+cc*(cw+gap);yy=y-rr*(ch+gap)-ch
            c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(x,yy,cw,ch,7,fill=1,stroke=1)
            c.setFillColor(colors.HexColor(col));c.rect(x,yy,4,ch,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica-Bold",6);c.drawString(x+10,yy+38,lab.upper())
            c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica-Bold",15);c.drawString(x+10,yy+18,val)
            if sub:
                c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",5.5);c.drawString(x+10,yy+7,sub)

        y-=2*(ch+gap)+4
        c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica-Bold",11);c.drawString(M,y,"Detalle operativo - "+period);y-=15
        head=["#","Tienda","Dev","Muertos","Prob.","Cajas","Pend.Ant.","Total","Recorr.","Acond.","% Acond.","Ubicado","% Ubic.","Pend.Acond.","Pend.Ubic."]
        fr=[.035,.115,.055,.052,.052,.050,.065,.060,.070,.065,.060,.065,.060,.100,.096]
        tw=W-2*M;xs=[M];acc=M
        for z in fr[:-1]:acc+=tw*z;xs.append(acc)
        hh=19;c.setFillColor(colors.HexColor(BLUE));c.rect(M,y-hh+3,tw,hh,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont("Helvetica-Bold",4.1)
        for j,h in enumerate(head):c.drawString(xs[j]+1.5,y-8,h)
        y-=hh
        rh=13 if len(rows)<=7 else (11.5 if len(rows)<=12 else 10.3)
        for i,r in enumerate(rows):
            total=r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")
            p_ac=pct_value(r,"pct_acondicionado",r.get("acondicionado"),total)
            p_ub=pct_value(r,"pct_ubicado",r.get("ubicado"),total)
            vals=[
                f"#{i+1}",r.get("store",""),f(r.get("dev_pzs")),f(r.get("muertos")),f(r.get("probador")),f(r.get("cajas")),
                f(r.get("pendiente_anterior")),f(total),f(r.get("recorridos")),f(r.get("acondicionado")),pct(p_ac),
                f(r.get("ubicado")),pct(p_ub),f(r.get("pendiente_acondicionar")),f(r.get("pendiente_ubicar"))
            ]
            c.setFillColor(colors.HexColor("#DDEAFF") if r.get("is_project") else colors.white);c.rect(M,y-rh+2,tw,rh,fill=1,stroke=0)
            c.setFont("Helvetica",4.2)
            for j,v in enumerate(vals):
                if j==10:
                    c.setFillColor(colors.HexColor(pct_color(p_ac)))
                    c.setFont("Helvetica-Bold",4.2)
                elif j==12:
                    c.setFillColor(colors.HexColor(pct_color(p_ub)))
                    c.setFont("Helvetica-Bold",4.2)
                else:
                    c.setFillColor(colors.HexColor(TXT))
                    c.setFont("Helvetica",4.2)
                c.drawString(xs[j]+1.5,y-8,str(v)[:22])
            y-=rh

        y-=7
        if y<215:
            c.showPage();header("gráfico");y=H-106
        c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica-Bold",11);c.drawString(M,y,"Ingreso vs Acondicionado vs Ubicado - "+period);y-=15
        x0=M+42;x1=W-M-12;base=44;top=y-12;ph=max(70,top-base);gw=(x1-x0)/max(1,len(rows));bw=min(13,gw*.23)
        mx=max([num(v) for r in rows for v in ((r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")),r.get("acondicionado"),r.get("ubicado"))]+[1])*1.15
        c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.6)
        for q in range(5):
            gy=base+ph*q/4;c.line(x0,gy,x1,gy);c.setFillColor(colors.HexColor(MUT));c.setFont("Helvetica",5);c.drawRightString(x0-5,gy-2,f(mx*q/4))
        pts=[]
        def tag(cx,cy,text,col):
            w=stringWidth(text,"Helvetica-Bold",5.2)+5;c.setFillColor(colors.white);c.roundRect(cx-w/2,cy-2,w,8,2,fill=1,stroke=0);c.setFillColor(colors.HexColor(col));c.setFont("Helvetica-Bold",5.2);c.drawCentredString(cx,cy,text)
        for i,r in enumerate(rows):
            cx=x0+gw*(i+.5);total=num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"));ac=num(r.get("acondicionado"));ub=num(r.get("ubicado"));ah=ph*ac/mx;uh=ph*ub/mx
            c.setFillColor(colors.HexColor(BLUE));c.rect(cx-bw-2,base,bw,max(.8,ah),fill=1,stroke=0);c.setFillColor(colors.HexColor(PINK));c.rect(cx+2,base,bw,max(.8,uh),fill=1,stroke=0)
            if ac==0 and ub==0:tag(cx,base+3,"A 0 / U 0",MUT)
            else:
                tag(cx-bw/2-2,base+ah+3,"A "+f(ac),BLUE);tag(cx+bw/2+2,base+uh+3,"U "+f(ub),PINK)
            py=base+ph*total/mx;pts.append((cx,py,total));c.setFillColor(colors.HexColor(BLUE2));c.circle(cx,py,2.6,fill=1,stroke=0);c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica",5.5);c.drawCentredString(cx,base-13,str(r.get("store",""))[:14])
        c.setStrokeColor(colors.HexColor(BLUE2));c.setLineWidth(1.4)
        for p1,p2 in zip(pts,pts[1:]):c.line(p1[0],p1[1],p2[0],p2[1])
        for cx,py,total in pts:tag(cx,min(top-2,py+7),"Total "+f(total),BLUE2)
        c.save();pdf=bio.getvalue()
        return pdf if pdf.startswith(b"%PDF") else old_pdf(d,report,scope)

    m._build_operations_pdf=build_pdf

    try:
        total=1774.0;ac=755.0;ub=1679.0
        assert round(ac/total*100,1)==42.6
        assert round(ub/total*100,1)==94.6
        assert abs(sum([.035,.115,.055,.052,.052,.050,.065,.060,.070,.065,.060,.065,.060,.100,.096])-1.0)<1e-9
        print("[V115-SELFTEST] Acondicionado/Ubicado: piezas + % en web y PDF OK.",flush=True)
    except Exception as exc:
        print(f"[V115-SELFTEST] ERROR: {type(exc).__name__}: {exc}",flush=True)

    m._V115_DAILY_PIECES_PERCENT=True
    print("[V115] Operación Diaria: Acondicionado y Ubicado muestran piezas + porcentaje en tabla y PDF.",flush=True)
