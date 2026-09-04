"""V91 - PDF compacto, con datos visibles en gráficos y bloques sin cortes.

Se instala despues de V90. No cambia los calculos ni la carga: solo la
presentacion/exportacion PDF de Cambios y Muertos.
"""
from __future__ import annotations

import io
import math


def _num(value):
    try:
        value = float(value or 0)
        return value if math.isfinite(value) else 0.0
    except Exception:
        return 0.0


def install(module) -> None:
    if getattr(module, "_V91_PDF_LAYOUT_PATCH", False):
        return

    previous_builder = module._build_operations_pdf

    def build_pdf_v91(data: dict, report: str, scope: str = "Compañía") -> bytes:
        handled = {
            "Operación Diaria", "Centro Ejecutivo", "Reporte Semanal", "Reporte Mensual",
            "Conversión", "Recuperación Económica",
        }
        if report not in handled:
            return previous_builder(data, report, scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        BLUE = "#173B73"; BLUE2 = "#246FE5"; PINK = "#EC007C"; PURPLE = "#7C3AED"
        GREEN = "#10B981"; ORANGE = "#F59E0B"; RED = "#EF4444"; TXT = "#102A56"
        BG = "#F3F6FA"; LINE = "#D7E0EA"; MUTED = "#6B778C"; ALT = "#EEF4FB"
        WHITE = colors.white
        width, height = landscape(letter)
        M = 26; BOTTOM = 28; CONTENT_TOP = height - 106
        USABLE = CONTENT_TOP - BOTTOM
        bio = io.BytesIO(); c = canvas.Canvas(bio, pagesize=(width, height)); y = CONTENT_TOP
        mt = data.get("metrics") or {}
        stores = list(data.get("stores") or [])
        recovery = list(data.get("recovery_by_store") or [])
        period = str(data.get("period_value") or "Histórico")

        def n(v): return f"{_num(v):,.0f}"
        def pc(v): return f"{_num(v):.1f}%"
        def money(v): return f"${_num(v):,.0f}"
        def safe(v): return "-" if v is None else str(v)
        def remaining(): return y - BOTTOM

        def page_header(suffix=""):
            nonlocal y
            c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, width, height, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M, height-88, width-2*M, 58, 11, fill=1, stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 17); c.drawString(M+18, height-55, "Cambios y Muertos")
            c.setFont("Helvetica", 8); c.drawString(M+18, height-72, "Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold", 9); c.drawRightString(width-M-18, height-54, "Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica", 7); c.drawRightString(width-M-18, height-70, f"{report}{(' - '+suffix) if suffix else ''}")
            y = CONTENT_TOP

        def new_page(suffix=""):
            c.showPage(); page_header(suffix)

        def ensure_atomic(total_h, suffix=""):
            """Mueve el bloque completo a la pagina siguiente cuando puede caber entero."""
            if total_h <= USABLE and remaining() < total_h:
                new_page(suffix)

        def section(title):
            nonlocal y
            if remaining() < 20: new_page()
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 11.2); c.drawString(M, y, title)
            y -= 16

        def wrap(text, limit=34):
            words = safe(text).split(); lines=[]; cur=""
            for word in words:
                candidate=(cur+" "+word).strip()
                if not cur or len(candidate)<=limit: cur=candidate
                else: lines.append(cur); cur=word
            if cur: lines.append(cur)
            return lines[:2]

        def kpis(items):
            nonlocal y
            cols=min(5,max(1,len(items))); gap=7; card_h=56
            rows_count=(len(items)+cols-1)//cols
            total_h=rows_count*(card_h+gap)+2
            ensure_atomic(total_h,"KPIs")
            card_w=(width-2*M-gap*(cols-1))/cols
            for idx,(label,value,sub,tone) in enumerate(items):
                rr=idx//cols; cc=idx%cols; x=M+cc*(card_w+gap); yy=y-rr*(card_h+gap)-card_h
                c.setFillColor(WHITE); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x,yy,card_w,card_h,7,fill=1,stroke=1)
                c.setFillColor(colors.HexColor(tone)); c.roundRect(x,yy,4,card_h,2,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(MUTED)); c.setFont("Helvetica-Bold",6.2); c.drawString(x+11,yy+40,safe(label).upper()[:28])
                c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold",15); c.drawString(x+11,yy+21,safe(value)[:20])
                c.setFillColor(colors.HexColor(MUTED)); c.setFont("Helvetica",5.5)
                lines=wrap(sub,33)
                if len(lines)==1: c.drawString(x+11,yy+7,lines[0])
                elif lines:
                    c.drawString(x+11,yy+10,lines[0]); c.drawString(x+11,yy+3.5,lines[1])
            y -= total_h

        def table_metrics(headers, rows, row_h):
            head_h = 25 if any("\n" in safe(h) for h in headers) else 18
            return 16 + head_h + len(rows)*row_h + 7, head_h

        def draw_table(headers, rows, widths, title, row_h=13, font=4.7, highlight_project=False, keep_with=0):
            """No parte tablas que caben completas. Si son mas altas que una pagina, corta solo entre filas."""
            nonlocal y
            if not rows:
                ensure_atomic(44,title); section(title)
                c.setFillColor(WHITE); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(M,y-20,width-2*M,22,6,fill=1,stroke=1)
                c.setFillColor(colors.HexColor(MUTED)); c.setFont("Helvetica",7); c.drawString(M+10,y-12,"Información no disponible")
                y-=29; return
            full_h, head_h = table_metrics(headers, rows, row_h)
            if full_h + keep_with <= USABLE:
                ensure_atomic(full_h + keep_with, title)
            elif full_h <= USABLE:
                ensure_atomic(full_h, title)

            total_w=width-2*M; xs=[M]; acc=M
            for frac in widths[:-1]: acc += total_w*frac; xs.append(acc)

            def draw_heading(cont=False):
                nonlocal y
                section(title + (" - continuación" if cont else ""))
                c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M,y-head_h+4,total_w,head_h,4,fill=1,stroke=0)
                c.setFillColor(WHITE); c.setFont("Helvetica-Bold",font)
                for i,h in enumerate(headers):
                    lines=safe(h).split("\n")
                    c.drawString(xs[i]+2.2,y-7,lines[0][:24])
                    if len(lines)>1:c.drawString(xs[i]+2.2,y-14.5,lines[1][:24])
                y-=head_h+1

            draw_heading(False)
            for ridx,row in enumerate(rows):
                # Una fila nunca se corta. Cuando ya no cabe, nueva pagina + encabezado.
                if remaining() < row_h + 3:
                    new_page(title); draw_heading(True)
                project = bool(row[-1]) if highlight_project else False
                display_row = row[:-1] if highlight_project else row
                bg = colors.HexColor("#DDEAFF") if project else (WHITE if ridx%2==0 else colors.HexColor(ALT))
                c.setFillColor(bg); c.rect(M,y-row_h+2,total_w,row_h,fill=1,stroke=0)
                if project:
                    c.setFillColor(colors.HexColor(BLUE2)); c.rect(M,y-row_h+2,3,row_h,fill=1,stroke=0)
                for i,val in enumerate(display_row):
                    emph=project and i==1
                    c.setFillColor(colors.HexColor(BLUE if emph else TXT)); c.setFont("Helvetica-Bold" if emph else "Helvetica",font)
                    c.drawString(xs[i]+2.2,y-7.8,safe(val)[:27])
                y-=row_h
            y-=6

        def label_box(cx, cy, text, color_hex, font=5.8):
            text=safe(text); tw=stringWidth(text,"Helvetica-Bold",font)+5
            c.setFillColor(colors.Color(1,1,1,alpha=0.90)); c.roundRect(cx-tw/2,cy-2,tw,8,2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(color_hex)); c.setFont("Helvetica-Bold",font); c.drawCentredString(cx,cy,text)

        def mixed_chart(title, rows, min_chart_h=142, preferred_chart_h=205):
            """Grafico atomico y adaptable: muestra Total/Acondicionado/Ubicado por tienda."""
            nonlocal y
            rows=list(rows or [])
            if not rows: return
            min_total=16+min_chart_h
            if remaining() < min_total: new_page(title)
            chart_h=max(min_chart_h,min(preferred_chart_h,remaining()-18))
            chart_h=min(chart_h,USABLE-18)
            ensure_atomic(16+chart_h,title)
            section(title)

            values=[]
            for r in rows:
                total=r.get("total_pzs")
                if total is None: total=r.get("ingresos")
                values += [_num(total),_num(r.get("acondicionado")),_num(r.get("ubicado"))]
            data_max=max(values+[1]); axis_max=max(1,data_max*1.14)
            x0=M+43; x1=width-M-12; legend_h=14; bottom_labels=36 if len(rows)<=8 else 46
            base=y-chart_h+bottom_labels; top=y-legend_h-8; plot_h=max(58,top-base)
            group_w=(x1-x0)/max(1,len(rows)); bar_w=min(13,max(4,group_w*.23))

            c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(.6)
            for q in range(5):
                val=axis_max*q/4; gy=base+plot_h*x/4
                c.line(x0,gy,x1,gy); c.setFillColor(colors.HexColor(MUTED)); c.setFont("Helvetica",5.4); c.drawRightString(x0-5,gy-2,n(val))

            points=[]
            for i,r in enumerate(rows):
                cx=x0+group_w*(i+.5); total=r.get("total_pzs")
                if total is None: total=r.get("ingresos")
                total=_num(total); acond=_num(r.get("acondicionado")); ubic=_num(r.get("ubicado"))
                a_h=plot_h*acond/axis_max; u_h=plot_h*ubic/axis_max
                # Barras.
                c.setFillColor(colors.HexColor(BLUE)); c.rect(cx-bar_w-2,base,bar_w,max(.8,a_h),fill=1,stroke=0)
                c.setFillColor(colors.HexColor(PINK)); c.rect(cx+2,base,bar_w,max(.8,u_h),fill=1,stroke=0)
                # Etiquetas de barras. Si ambas son 0, mostrarlo una sola vez para evitar ruido.
                if acond==0 and ubic==0:
                    label_box(cx,base+3,"A 0 / U 0",MUTED,5.2)
                else:
                    label_box(cx-bar_w/2-2,base+a_h+3,f"A {n(acond)}",BLUE,5.2)
                    label_box(cx+bar_w/2+2,base+u_h+3,f"U {n(ubic)}",PINK,5.2)
                # Linea Total pzs.
                py=base+plot_h*total/axis_max; points.append((cx,py,total))
                c.setFillColor(colors.HexColor(BLUE2)); c.circle(cx,py,2.7,fill=1,stroke=0)

                # Nombre de tienda.
                c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",5.1 if len(rows)>8 else 5.7)
                store=safe(r.get("store"))[:15]
                if len(rows)<=6:
                    c.drawCentredString(cx,base-13,store)
                else:
                    c.saveState(); c.translate(cx-2,base-7); c.rotate(38); c.drawString(0,0,store); c.restoreState()

            if len(points)>1:
                c.setStrokeColor(colors.HexColor(BLUE2)); c.setLineWidth(1.5)
                for p1,p2 in zip(points,points[1:]):c.line(p1[0],p1[1],p2[0],p2[1])
            for cx,py,total in points:
                # Separar el Total de las etiquetas de barras cercanas.
                label_box(cx,min(top-2,py+7),f"Total {n(total)}",BLUE2,5.7)

            # Leyenda clara.
            lx=x0
            c.setStrokeColor(colors.HexColor(BLUE2)); c.setLineWidth(1.5); c.line(lx,y-4,lx+13,y-4); c.setFillColor(colors.HexColor(BLUE2)); c.circle(lx+6.5,y-4,2.2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",6); c.drawString(lx+17,y-6,"Total pzs")
            lx+=86; c.setFillColor(colors.HexColor(BLUE)); c.rect(lx,y-8,8,7,fill=1,stroke=0); c.setFillColor(colors.HexColor(TXT)); c.drawString(lx+12,y-6,"Acondicionado")
            lx+=98; c.setFillColor(colors.HexColor(PINK)); c.rect(lx,y-8,8,7,fill=1,stroke=0); c.setFillColor(colors.HexColor(TXT)); c.drawString(lx+12,y-6,"Ubicado")
            y-=chart_h

        def horizontal_chart(title, rows, series):
            nonlocal y
            rows=list(rows or [])
            if not rows:return
            h=max(118,min(235,35+len(rows)*14))
            ensure_atomic(16+h,title); section(title)
            x0=M+110;x1=width-M-18;maxv=max([_num(r.get(k)) for r in rows for k,_,_ in series]+[1])
            for i,r in enumerate(rows):
                yy=y-7-i*14;c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica",5.8);c.drawRightString(x0-6,yy,safe(r.get("store") or r.get("label") or r.get("date")))
                for j,(key,col,lab) in enumerate(series):
                    v=_num(r.get(key));bw=(x1-x0)*v/maxv;c.setFillColor(colors.HexColor(col));c.roundRect(x0,yy-4-j*6,max(1,bw),4.5,2,fill=1,stroke=0)
                    if v>0: label_box(min(x1-14,x0+bw+13),yy-3-j*6,n(v),col,5)
            y-=h

        def operational_rows():
            out=[]
            for i,r in enumerate(stores,1):
                total=r.get("total_pzs")
                if total is None: total=r.get("ingresos")
                out.append([f"#{i}",r.get("store"),n(r.get("dev_pzs")),n(r.get("muertos")),n(r.get("probador")),n(r.get("cajas")),n(r.get("pendiente_anterior")),n(total),n(r.get("recorridos")),n(r.get("acondicionado")),n(r.get("ubicado")),n(r.get("pendiente_acondicionar")),n(r.get("pendiente_ubicar")),bool(r.get("is_project"))])
            return out

        OP_HEADERS=["Ranking","Tienda","Dev pzs","Muertos","Probador","Cajas","Pend. Ant.","Total pzs","Recorridos\nrealizados","Acondicionado","Ubicado","Pendiente de\nacondicionar","Pendiente de\nubicar"]
        OP_WIDTHS=[.035,.12,.065,.06,.06,.055,.07,.07,.075,.075,.07,.125,.12]

        def operational_table_and_chart(title="Detalle operativo"):
            rows=operational_rows(); count=len(rows)
            row_h=14 if count<=7 else (12 if count<=18 else 10.5)
            table_h,_=table_metrics(OP_HEADERS,rows,row_h)
            chart_keep=16+142+4
            # Si tabla + grafico pueden caber juntos en una sola hoja, se mantienen unidos.
            keep=chart_keep if table_h+chart_keep<=USABLE else 0
            draw_table(OP_HEADERS,rows,OP_WIDTHS,title,row_h=row_h,font=4.45,highlight_project=True,keep_with=keep)
            mixed_chart(f"Ingreso vs Acondicionado vs Ubicado - {period}",stores)

        def recovery_table(title="Recuperación por tienda"):
            ordered=sorted(recovery,key=lambda r:(-_num(r.get("conversion_pct")),-_num(r.get("recovery_pct")),safe(r.get("store"))))
            rows=[]
            for i,r in enumerate(ordered,1):
                rows.append([f"#{i}",r.get("store"),n(r.get("dev_pzs")),n(r.get("converted_pieces")),pc(r.get("conversion_pct")),money(r.get("return_value")),money(r.get("recovered_value")),pc(r.get("recovery_pct")),n(r.get("pending_pieces")),money(r.get("pending_value")),bool(r.get("is_project"))])
            draw_table(["#","Tienda","Dev Pzs","Pzas\nrecuperadas","Conversión","Valor\ndevolución","Recuperación $","Recup. %","Pend. Pzs","Pend. $"],rows,[.04,.16,.08,.09,.09,.13,.13,.09,.09,.10],title,row_h=12,font=4.8,highlight_project=True)

        page_header()
        c.setFillColor(colors.HexColor(MUTED));c.setFont("Helvetica",7);c.drawString(M,y,f"Periodo: {period}   -   Alcance: {scope}");y-=13

        if report=="Operación Diaria":
            kpis([
                ("Dev pzs",n(mt.get("dev_pzs")),"Devoluciones del periodo",BLUE),
                ("Muertos",n(mt.get("muertos")),"Recolección - motivo Muertos",PINK),
                ("Probador",n(mt.get("probador")),"Motivo Probador",ORANGE),
                ("Cajas",n(mt.get("cajas")),"Recolección - Cajas",PURPLE),
                ("Total pzs",n(mt.get("total_pzs") if mt.get("total_pzs") is not None else mt.get("ingresos")),"Dev + Muertos + Cajas + Probador + Pend. Ant.",BLUE2),
                ("Recorridos realizados",n(mt.get("recorridos")),f"{pc(mt.get('pct_recorridos'))} - meta {n(mt.get('meta_recorridos'))}",GREEN),
                ("Acondicionado",n(mt.get("acondicionado")),pc(mt.get("pct_acondicionado")),PURPLE),
                ("Ubicado",n(mt.get("ubicado")),pc(mt.get("pct_ubicado")),PINK),
                ("Pendiente de acondicionar",n(mt.get("pendiente_acondicionar")),"Total pzs - Acondicionado",ORANGE),
                ("Pendiente de ubicar",n(mt.get("pendiente_ubicar")),"Total pzs - Ubicado",RED),
            ])
            operational_table_and_chart(f"Detalle operativo - {period}")

        elif report=="Centro Ejecutivo":
            kpis([
                ("Conversión",pc(mt.get("conversion_pct")),"FIFO diario - misma semana ISO",PURPLE),
                ("Pzas recuperadas",n(mt.get("converted_pieces")),"Ventas posteriores a la devolución",GREEN),
                ("Recuperación económica",pc(mt.get("recovery_pct")),"Recuperación $ / Valor devolución",PINK),
                ("Valor devolución",money(mt.get("return_value")),"Devoluciones del periodo",BLUE2),
                ("Recuperación $",money(mt.get("recovered_value")),"Misma semana ISO",GREEN),
                ("Pendiente $",money(mt.get("pending_recovery_value")),"Valor devolución - Recuperación",RED),
            ])
            recovery_table(); horizontal_chart("Devolución y recuperación",recovery,[("dev_pzs",BLUE,"Dev Pzs"),("converted_pieces",PINK,"Recuperadas")]); operational_table_and_chart("Detalle operativo")

        elif report in ("Reporte Semanal","Reporte Mensual"):
            kpis([
                ("Total pzs" if report=="Reporte Semanal" else "Total pzs mes",n(mt.get("total_pzs") if mt.get("total_pzs") is not None else mt.get("ingresos")),period,BLUE2),
                ("Acondicionado",pc(mt.get("pct_acondicionado")),n(mt.get("acondicionado")),PURPLE),
                ("Ubicado",pc(mt.get("pct_ubicado")),n(mt.get("ubicado")),PINK),
                ("Conversión",pc(mt.get("conversion_pct")),f"{n(mt.get('converted_pieces'))} piezas",GREEN),
                ("Recuperación económica",pc(mt.get("recovery_pct")),money(mt.get("recovered_value")),BLUE),
                ("Productividad",pc(mt.get("productivity_pct")),f"{n(mt.get('productivity_daily'))} pzs/día",ORANGE),
                ("Recorridos",pc(mt.get("pct_recorridos")),f"{n(mt.get('recorridos'))} realizados",RED),
            ])
            recovery_table(); horizontal_chart("Devolución y recuperación",recovery,[("dev_pzs",BLUE,"Dev Pzs"),("converted_pieces",PINK,"Recuperadas")]); operational_table_and_chart("Detalle operativo")

        elif report=="Conversión":
            kpis([("Dev Pzs",n(mt.get("dev_pzs")),"Devoluciones detectadas",BLUE2),("Piezas convertidas",n(mt.get("converted_pieces")),"Venta validada misma semana",GREEN),("% Conversión",pc(mt.get("conversion_pct")),"Convertidas / Dev Pzs",GREEN),("Pendiente",n(mt.get("pending_recovery_pieces")),"Dev - convertidas",RED)])
            recovery_table()

        elif report=="Recuperación Económica":
            kpis([("Valor devolución",money(mt.get("return_value")),"Precio unitario neto x Dev Pzs",BLUE2),("Recuperación $",money(mt.get("recovered_value")),"Venta recuperada",GREEN),("% Recuperación",pc(mt.get("recovery_pct")),"Recuperado / valor devolución",GREEN),("Pendiente $",money(mt.get("pending_recovery_value")),"Valor aún no recuperado",RED)])
            recovery_table()

        c.save(); pdf=bio.getvalue()
        if not pdf.startswith(b"%PDF"): raise RuntimeError("El generador no produjo un PDF válido")
        return pdf

    module._build_operations_pdf = build_pdf_v91
    module._V91_PDF_LAYOUT_PATCH = True
    print("[V91-PDF] PDF compacto: gráficos con datos y bloques tabla/gráfico sin cortes.", flush=True)
