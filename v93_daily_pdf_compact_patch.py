"""V93: PDF Diario compacto. V90 queda intacto para los demás reportes."""
import io, math

def _n(v):
    try:return float(v or 0)
    except:return 0.0

def install(m):
    if getattr(m,'_V93_DAILY_PDF',False):return
    old=m._build_operations_pdf
    def build(d,report,scope='Compañía'):
        rows=list(d.get('stores') or [])
        if report!='Operación Diaria' or len(rows)>7:return old(d,report,scope)
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape,letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth
        W,H=landscape(letter);M=26;BLUE='#173B73';BLUE2='#246FE5';PINK='#EC007C';PURPLE='#7C3AED';GREEN='#10B981';ORANGE='#F59E0B';RED='#EF4444';TXT='#102A56';MUT='#6B778C';LINE='#D7E0EA';BG='#F3F6FA'
        mt=d.get('metrics') or {};period=str(d.get('period_value') or 'Histórico');b=io.BytesIO();c=canvas.Canvas(b,pagesize=(W,H))
        def f(v):return f'{_n(v):,.0f}'
        def pct(v):return f'{_n(v):.1f}%'
        c.setFillColor(colors.HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,H-88,W-2*M,58,11,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Helvetica-Bold',17);c.drawString(M+18,H-55,'Cambios y Muertos');c.setFont('Helvetica',8);c.drawString(M+18,H-72,'Recuperación, conversión, recolección y seguimiento operativo');c.setFont('Helvetica-Bold',9);c.drawRightString(W-M-18,H-54,'Operaciones Ropa - Price Shoes');c.setFont('Helvetica',7);c.drawRightString(W-M-18,H-70,'Operación Diaria')
        y=H-106;c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',7);c.drawString(M,y,f'Periodo: {period}   -   Alcance: {scope}');y-=13
        items=[('Dev pzs',f(mt.get('dev_pzs')),BLUE),('Muertos',f(mt.get('muertos')),PINK),('Probador',f(mt.get('probador')),ORANGE),('Cajas',f(mt.get('cajas')),PURPLE),('Total pzs',f(mt.get('total_pzs',mt.get('ingresos'))),BLUE2),('Recorridos',f(mt.get('recorridos')),GREEN),('Acondicionado',f(mt.get('acondicionado')),PURPLE),('Ubicado',f(mt.get('ubicado')),PINK),('Pend. acond.',f(mt.get('pendiente_acondicionar')),ORANGE),('Pend. ubicar',f(mt.get('pendiente_ubicar')),RED)]
        gap=7;cw=(W-2*M-gap*4)/5;ch=53
        for i,(lab,val,col) in enumerate(items):
            r=i//5;q=i%5;x=M+q*(cw+gap);yy=y-r*(ch+gap)-ch;c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(x,yy,cw,ch,7,fill=1,stroke=1);c.setFillColor(colors.HexColor(col));c.rect(x,yy,4,ch,fill=1,stroke=0);c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica-Bold',6);c.drawString(x+10,yy+38,lab.upper());c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica-Bold',15);c.drawString(x+10,yy+18,val)
        y-=2*(ch+gap)+4;c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica-Bold',11);c.drawString(M,y,'Detalle operativo - '+period);y-=15
        head=['#','Tienda','Dev','Muertos','Prob.','Cajas','Pend.Ant.','Total','Recorr.','Acond.','Ubic.','Pend.Acond.','Pend.Ubic.'];fr=[.035,.12,.065,.06,.06,.055,.07,.07,.075,.075,.07,.125,.12];tw=W-2*M;xs=[M];a=M
        for z in fr[:-1]:a+=tw*z;xs.append(a)
        hh=19;c.setFillColor(colors.HexColor(BLUE));c.rect(M,y-hh+3,tw,hh,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Helvetica-Bold',4.5)
        for j,h in enumerate(head):c.drawString(xs[j]+2,y-8,h)
        y-=hh
        rh=13
        for i,r in enumerate(rows):
            total=r.get('total_pzs') if r.get('total_pzs') is not None else r.get('ingresos');vals=[f'#{i+1}',r.get('store',''),f(r.get('dev_pzs')),f(r.get('muertos')),f(r.get('probador')),f(r.get('cajas')),f(r.get('pendiente_anterior')),f(total),f(r.get('recorridos')),f(r.get('acondicionado')),f(r.get('ubicado')),f(r.get('pendiente_acondicionar')),f(r.get('pendiente_ubicar'))];c.setFillColor(colors.HexColor('#DDEAFF') if r.get('is_project') else colors.white);c.rect(M,y-rh+2,tw,rh,fill=1,stroke=0);c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica',4.5)
            for j,v in enumerate(vals):c.drawString(xs[j]+2,y-8,str(v)[:23])
            y-=rh
        y-=7;c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica-Bold',11);c.drawString(M,y,'Ingreso vs Acondicionado vs Ubicado - '+period);y-=15
        x0=M+42;x1=W-M-12;base=44;top=y-12;ph=max(70,top-base);gw=(x1-x0)/max(1,len(rows));bw=min(13,gw*.23);mx=max([_n(v) for r in rows for v in ((r.get('total_pzs') if r.get('total_pzs') is not None else r.get('ingresos')),r.get('acondicionado'),r.get('ubicado'))]+[1])*1.15
        c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.6)
        for q in range(5):gy=base+ph*q/4;c.line(x0,gy,x1,gy);c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',5);c.drawRightString(x0-5,gy-2,f(mx*q/4))
        pts=[]
        def tag(cx,cy,text,col):
            w=stringWidth(text,'Helvetica-Bold',5.2)+5;c.setFillColor(colors.white);c.roundRect(cx-w/2,cy-2,w,8,2,fill=1,stroke=0);c.setFillColor(colors.HexColor(col));c.setFont('Helvetica-Bold',5.2);c.drawCentredString(cx,cy,text)
        for i,r in enumerate(rows):
            cx=x0+gw*(i+.5);t=_n(r.get('total_pzs') if r.get('total_pzs') is not None else r.get('ingresos'));ac=_n(r.get('acondicionado'));u=_n(r.get('ubicado'));ah=ph*ac/mx;uh=ph*u/mx;c.setFillColor(colors.HexColor(BLUE));c.rect(cx-bw-2,base,bw,max(.8,ah),fill=1,stroke=0);c.setFillColor(colors.HexColor(PINK));c.rect(cx+2,base,bw,max(.8,uh),fill=1,stroke=0);tag(cx,base+3,'A 0 / U 0',MUT) if ac==0 and u==0 else (tag(cx-bw/2-2,base+ah+3,'A '+f(ac),BLUE),tag(cx+bw/2+2,base+uh+3,'U '+f(u),PINK));py=base+ph*t/mx;pts.append((cx,py,t));c.setFillColor(colors.HexColor(BLUE2));c.circle(cx,py,2.6,fill=1,stroke=0);c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica',5.5);c.drawCentredString(cx,base-13,str(r.get('store',''))[:14])
        c.setStrokeColor(colors.HexColor(BLUE2));c.setLineWidth(1.4)
        for p1,p2 in zip(pts,pts[1:]):c.line(p1[0],p1[1],p2[0],p2[1])
        for cx,py,t in pts:tag(cx,min(top-2,py+7),'Total '+f(t),BLUE2)
        c.save();pdf=b.getvalue();return pdf
    m._build_operations_pdf=build;m._V93_DAILY_PDF=True;print('[V93-PDF] Diario compacto y con datos visibles.',flush=True)
