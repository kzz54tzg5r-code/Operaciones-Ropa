"""V105: PDF Semanal/Mensual con el mismo lenguaje visual del Diario.

Respeta el contenido real del reporte en pantalla:
1) KPIs del periodo;
2) Recuperación por tienda + gráfico de devolución/recuperación;
3) Detalle operativo de tiendas Proyecto + gráfico Ingreso/Acondicionado/Ubicado.

Cada bloque se mantiene completo: una tabla o gráfico que no cabe pasa entero a
la hoja siguiente. Se evita el gran espacio vacío observado en versiones
anteriores. Los ceros del detalle operativo, desde Dev pzs hasta Ubicado, se
pintan en rojo como en el PDF Diario.
"""
from __future__ import annotations
import io
import math


def _num(v):
    try:
        x=float(v or 0)
        return x if math.isfinite(x) else 0.0
    except Exception:
        return 0.0


def install(m):
    if getattr(m,'_V105_WEEK_MONTH_PDF',False):
        return
    old=m._build_operations_pdf

    def build(d,report,scope='Compañía'):
        if report not in ('Reporte Semanal','Reporte Mensual'):
            return old(d,report,scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape,letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth

        W,H=landscape(letter);M=26
        BLUE='#173B73';BLUE2='#246FE5';PINK='#EC007C';PURPLE='#7C3AED';GREEN='#10B981';ORANGE='#F59E0B';RED='#EF4444';TXT='#102A56';MUT='#6B778C';LINE='#D7E0EA';BG='#F3F6FA';ROWALT='#EEF4FB'
        mt=d.get('metrics') or {};stores=list(d.get('stores') or []);rec=list(d.get('recovery_by_store') or [])
        period=str(d.get('period_value') or 'Histórico')
        project=[r for r in stores if r.get('is_project')]
        rec_by_store={str(r.get('store') or ''):r for r in rec}
        project.sort(key=lambda r:(-_num((rec_by_store.get(str(r.get('store') or '')) or {}).get('conversion_pct')),str(r.get('store') or '')))
        rec.sort(key=lambda r:(-_num(r.get('conversion_pct')),str(r.get('store') or '')))
        b=io.BytesIO();c=canvas.Canvas(b,pagesize=(W,H));y=0

        def f(v):return f'{_num(v):,.0f}'
        def pct(v):return f'{_num(v):.1f}%'
        def money(v):return f'${_num(v):,.0f}'

        def header(suffix=''):
            nonlocal y
            c.setFillColor(colors.HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,H-88,W-2*M,58,11,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setFont('Helvetica-Bold',17);c.drawString(M+18,H-55,'Cambios y Muertos')
            c.setFont('Helvetica',8);c.drawString(M+18,H-72,'Recuperación, conversión, recolección y seguimiento operativo')
            c.setFont('Helvetica-Bold',9);c.drawRightString(W-M-18,H-54,'Operaciones Ropa - Price Shoes')
            c.setFont('Helvetica',7);c.drawRightString(W-M-18,H-70,report+((' - '+suffix) if suffix else ''))
            y=H-106;c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',7);c.drawString(M,y,f'Periodo: {period}   -   Alcance: {scope}');y-=13

        def new_page(suffix=''):
            c.showPage();header(suffix)

        def card_grid(items):
            nonlocal y
            gap=7;cols=5;cw=(W-2*M-gap*(cols-1))/cols;ch=48;rows=(len(items)+cols-1)//cols
            for i,(lab,val,sub,col) in enumerate(items):
                rr=i//cols;cc=i%cols;x=M+cc*(cw+gap);yy=y-rr*(ch+gap)-ch
                c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(LINE));c.roundRect(x,yy,cw,ch,7,fill=1,stroke=1)
                c.setFillColor(colors.HexColor(col));c.rect(x,yy,4,ch,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica-Bold',5.6);c.drawString(x+10,yy+34,str(lab).upper()[:26])
                c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica-Bold',14);c.drawString(x+10,yy+17,str(val)[:18])
                c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',5.2);c.drawString(x+10,yy+6,str(sub)[:34])
            y-=rows*(ch+gap)+5

        def title(text):
            nonlocal y
            c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica-Bold',11);c.drawString(M,y,text);y-=14

        def recovery_table(rows):
            nonlocal y
            if not rows:return
            title('Recuperación por tienda')
            head=['#','Tienda','Dev Pzs','Pzas recup.','Conversión','Valor dev.','Recuperación $','Recup. %','Pend. Pzs','Pend. $']
            fr=[.035,.13,.08,.09,.09,.12,.13,.09,.09,.105];tw=W-2*M;xs=[M];acc=M
            for q in fr[:-1]:acc+=tw*q;xs.append(acc)
            hh=17;rh=8.5 if len(rows)>=15 else 10
            c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,y-hh+2,tw,hh,4,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Helvetica-Bold',4.6)
            for j,h in enumerate(head):c.drawString(xs[j]+2,y-7,h)
            y-=hh
            for i,r in enumerate(rows):
                c.setFillColor(colors.HexColor(ROWALT if i%2 else '#FFFFFF'));c.rect(M,y-rh+1,tw,rh,fill=1,stroke=0)
                vals=[f'#{i+1}',r.get('store',''),f(r.get('dev_pzs')),f(r.get('converted_pieces')),pct(r.get('conversion_pct')),money(r.get('return_value')),money(r.get('recovered_value')),pct(r.get('recovery_pct')),f(r.get('pending_pieces')),money(r.get('pending_value'))]
                c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica',4.35)
                for j,v in enumerate(vals):c.drawString(xs[j]+2,y-6.4,str(v)[:24])
                y-=rh
            y-=5

        def recovery_chart(rows):
            nonlocal y
            if not rows:return
            # 17 tiendas caben en un bloque compacto de ~132 pt.
            block=137
            if y-block<32:new_page('Recuperación');
            title('Devolución y recuperación - '+period)
            shown=rows[:17];xlab=M+75;x0=M+105;x1=W-M-18;avail=x1-x0;maxv=max([_num(r.get('dev_pzs')) for r in shown]+[1])
            rh=min(6.3,max(4.9,(y-38)/max(1,len(shown))));
            for i,r in enumerate(shown):
                yy=y-i*rh;dev=_num(r.get('dev_pzs'));got=_num(r.get('converted_pieces'));w1=avail*dev/maxv;w2=avail*got/maxv
                c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',4.2);c.drawRightString(xlab,yy-3,str(r.get('store') or '')[:14])
                c.setFillColor(colors.HexColor('#DCE6F2'));c.roundRect(x0,yy-5,avail,4,2,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(BLUE));c.roundRect(x0,yy-5,max(.5,w1),4,2,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(PINK));c.roundRect(x0,yy-3.9,max(.5,w2),1.8,.8,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica-Bold',3.9);c.drawString(min(x1-30,x0+w1+3),yy-4,f(dev))
            y-=len(shown)*rh+8

        def operational_table(rows):
            nonlocal y
            if not rows:return
            title('Detalle operativo - tiendas del proyecto')
            head=['#','Tienda','Dev','Muertos','Prob.','Cajas','Pend.Ant.','Total','Recorr.','Acond.','Ubic.','Pend.Acond.','Pend.Ubic.']
            fr=[.035,.12,.065,.06,.06,.055,.07,.07,.075,.075,.07,.125,.12];tw=W-2*M;xs=[M];acc=M
            for q in fr[:-1]:acc+=tw*q;xs.append(acc)
            hh=17;rh=9.5 if len(rows)<=8 else 8.1
            c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,y-hh+2,tw,hh,4,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Helvetica-Bold',4.5)
            for j,h in enumerate(head):c.drawString(xs[j]+2,y-7,h)
            y-=hh
            for i,r in enumerate(rows):
                total=r.get('total_pzs') if r.get('total_pzs') is not None else r.get('ingresos')
                raw=[i+1,r.get('store',''),_num(r.get('dev_pzs')),_num(r.get('muertos')),_num(r.get('probador')),_num(r.get('cajas')),_num(r.get('pendiente_anterior')),_num(total),_num(r.get('recorridos')),_num(r.get('acondicionado')),_num(r.get('ubicado')),_num(r.get('pendiente_acondicionar')),_num(r.get('pendiente_ubicar'))]
                vals=[f'#{i+1}',r.get('store','')]+[f(x) for x in raw[2:]]
                c.setFillColor(colors.HexColor(ROWALT if i%2 else '#FFFFFF'));c.rect(M,y-rh+1,tw,rh,fill=1,stroke=0)
                c.setFont('Helvetica',4.25)
                for j,v in enumerate(vals):
                    # Dev..Ubicado = columnas 2..10: cero en rojo/negrita.
                    is_red=(2<=j<=10 and _num(raw[j])==0)
                    c.setFillColor(colors.HexColor(RED if is_red else TXT));c.setFont('Helvetica-Bold' if is_red else 'Helvetica',4.25)
                    c.drawString(xs[j]+2,y-6.3,str(v)[:23])
                y-=rh
            y-=6

        def combo_chart(rows):
            nonlocal y
            if not rows:return
            # Nunca dividir el gráfico; si no cabe, hoja nueva.
            need=205
            if y-need<28:new_page('Detalle operativo')
            title('Ingreso vs Acondicionado vs Ubicado - '+period)
            x0=M+42;x1=W-M-12;base=42;top=y-8;ph=max(95,top-base);gw=(x1-x0)/max(1,len(rows));bw=min(13,gw*.23)
            mx=max([_num(v) for r in rows for v in ((r.get('total_pzs') if r.get('total_pzs') is not None else r.get('ingresos')),r.get('acondicionado'),r.get('ubicado'))]+[1])*1.12
            c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.6)
            for q in range(5):
                gy=base+ph*q/4;c.line(x0,gy,x1,gy);c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',4.7);c.drawRightString(x0-5,gy-2,f(mx*q/4))
            pts=[]
            def tag(cx,cy,text,col):
                w=stringWidth(text,'Helvetica-Bold',4.8)+5;c.setFillColor(colors.white);c.roundRect(cx-w/2,cy-2,w,7.5,2,fill=1,stroke=0);c.setFillColor(colors.HexColor(col));c.setFont('Helvetica-Bold',4.8);c.drawCentredString(cx,cy,text)
            for i,r in enumerate(rows):
                cx=x0+gw*(i+.5);tot=_num(r.get('total_pzs') if r.get('total_pzs') is not None else r.get('ingresos'));ac=_num(r.get('acondicionado'));ub=_num(r.get('ubicado'));ah=ph*ac/mx;uh=ph*ub/mx
                c.setFillColor(colors.HexColor(BLUE));c.rect(cx-bw-2,base,bw,max(.7,ah),fill=1,stroke=0)
                c.setFillColor(colors.HexColor(PINK));c.rect(cx+2,base,bw,max(.7,uh),fill=1,stroke=0)
                if ac==0 and ub==0:tag(cx,base+3,'A 0 / U 0',RED)
                else:
                    tag(cx-bw/2-2,base+ah+3,'A '+f(ac),BLUE)
                    tag(cx+bw/2+2,base+uh+3,'U '+f(ub),PINK)
                py=base+ph*tot/mx;pts.append((cx,py,tot));c.setFillColor(colors.HexColor(BLUE2));c.circle(cx,py,2.4,fill=1,stroke=0);c.setFillColor(colors.HexColor(TXT));c.setFont('Helvetica',5);c.drawCentredString(cx,base-12,str(r.get('store') or '')[:13])
            c.setStrokeColor(colors.HexColor(BLUE2));c.setLineWidth(1.3)
            for p1,p2 in zip(pts,pts[1:]):c.line(p1[0],p1[1],p2[0],p2[1])
            for cx,py,tot in pts:tag(cx,min(top-2,py+6),'Total '+f(tot),BLUE2)
            y=base-20

        header()
        if report=='Reporte Semanal':
            cards=[('Total pzs',f(mt.get('total_pzs',mt.get('ingresos'))),period,BLUE2),('Acondicionado',pct(mt.get('pct_acondicionado')),f(mt.get('acondicionado')),PURPLE),('Ubicado',pct(mt.get('pct_ubicado')),f(mt.get('ubicado')),PINK),('Conversión',pct(mt.get('conversion_pct')),f(mt.get('converted_pieces'))+' piezas',GREEN),('Recuperación económica',pct(mt.get('recovery_pct')),money(mt.get('recovered_value')),BLUE),('Productividad',pct(mt.get('productivity_pct')),f(mt.get('productivity_daily'))+' pzs/día',ORANGE),('Recorridos',pct(mt.get('pct_recorridos')),f(mt.get('recorridos'))+' realizados',RED)]
        else:
            cards=[('Ingresos mes',f(mt.get('total_pzs',mt.get('ingresos'))),period,BLUE2),('Acondicionado',pct(mt.get('pct_acondicionado')),f(mt.get('acondicionado')),PURPLE),('Ubicado',pct(mt.get('pct_ubicado')),f(mt.get('ubicado')),PINK),('Conversión mensual',pct(mt.get('conversion_pct')),f(mt.get('converted_pieces'))+' piezas',GREEN),('Recuperación económica',pct(mt.get('recovery_pct')),money(mt.get('recovered_value')),BLUE),('Productividad',pct(mt.get('productivity_pct')),f(mt.get('productivity_daily'))+' pzs/día',ORANGE),('Recorridos',pct(mt.get('pct_recorridos')),f(mt.get('recorridos'))+' realizados',RED)]
        card_grid(cards)
        recovery_table(rec)
        recovery_chart(rec)

        # Página 2: igual que Diario, detalle + gráfico juntos cuando sea posible.
        if project:
            new_page('Tiendas Proyecto')
            operational_table(project)
            combo_chart(project)
        else:
            new_page('Tiendas Proyecto')
            title('Detalle operativo - tiendas del proyecto')
            c.setFillColor(colors.HexColor(MUT));c.setFont('Helvetica',8);c.drawString(M,y,'No hay tiendas guardadas como Proyecto para el periodo seleccionado.')

        c.save();pdf=b.getvalue()
        if not pdf.startswith(b'%PDF'):
            raise RuntimeError('El generador V105 no produjo un PDF válido')
        return pdf

    m._build_operations_pdf=build
    m._V105_WEEK_MONTH_PDF=True
    print('[V105-PDF] Semanal y Mensual replican el diseño del Diario y evitan cortes de bloques.',flush=True)
