"""V96: PDF de Centro Ejecutivo espejo del reporte web.

Orden visual del reporte:
1) KPIs ejecutivos + regla FIFO.
2) Recuperación por tienda.
3) Gráfica Devolución y recuperación.
4) Detalle operativo sólo de tiendas Proyecto.
5) Gráfica Ingreso vs Acondicionado vs Ubicado.

Además conserva el diseño solicitado: filas alternadas, marca Proyecto, ceros
rojos desde Dev pzs hasta Ubicado y bloques/gráficas sin cortes innecesarios.
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
    if getattr(module, "_V96_CENTER_EXEC_PDF", False):
        return

    previous_builder = module._build_operations_pdf

    def build_pdf_v96(data: dict, report: str, scope: str = "Compañía") -> bytes:
        if report != "Centro Ejecutivo":
            return previous_builder(data, report, scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        W, H = landscape(letter)
        M = 26
        BOTTOM = 28
        CONTENT_TOP = H - 106
        BLUE = "#173B73"; BLUE2 = "#246FE5"; PINK = "#EC007C"; PURPLE = "#7C3AED"
        GREEN = "#10B981"; ORANGE = "#F59E0B"; RED = "#D92D20"; TXT = "#102A56"
        MUT = "#6B778C"; LINE = "#D7E0EA"; BG = "#F3F6FA"; ALT = "#EEF4FB"

        mt = data.get("metrics") or {}
        period = str(data.get("period_value") or "Histórico")
        stores = list(data.get("stores") or [])
        recovery = list(data.get("recovery_by_store") or [])
        project_names = {str(x) for x in (data.get("project_stores") or [])}
        conversion_by_store = {
            str(r.get("store") or ""): _num(r.get("conversion_pct")) for r in recovery
        }

        project_stores = [
            r for r in stores
            if r.get("is_project") or str(r.get("store") or "") in project_names
        ]
        project_stores.sort(
            key=lambda r: (-conversion_by_store.get(str(r.get("store") or ""), 0.0), str(r.get("store") or ""))
        )
        recovery.sort(
            key=lambda r: (-_num(r.get("conversion_pct")), -_num(r.get("recovery_pct")), str(r.get("store") or ""))
        )

        out = io.BytesIO()
        c = canvas.Canvas(out, pagesize=(W, H))
        y = CONTENT_TOP

        def n(v): return f"{_num(v):,.0f}"
        def pct(v): return f"{_num(v):.1f}%"
        def money(v): return f"${_num(v):,.0f}"
        def metric_color(value, good=80, warn=60):
            value = _num(value)
            return GREEN if value >= good else (ORANGE if value >= warn else RED)

        def page_header(suffix="Centro Ejecutivo"):
            nonlocal y
            c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, W, H, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M, H-88, W-2*M, 58, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 17); c.drawString(M+18, H-55, "Cambios y Muertos")
            c.setFont("Helvetica", 8); c.drawString(M+18, H-72, "Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold", 9); c.drawRightString(W-M-18, H-54, "Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica", 7); c.drawRightString(W-M-18, H-70, suffix)
            y = CONTENT_TOP

        def new_page(suffix="Centro Ejecutivo"):
            c.showPage(); page_header(suffix)

        def period_line():
            nonlocal y
            c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 7)
            c.drawString(M, y, f"Periodo: {period}   -   Alcance: {scope}")
            y -= 13

        def section(text):
            nonlocal y
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 11)
            c.drawString(M, y, text)
            y -= 15

        def card(x, yy, w, h, label, value, sub, tone, value_color=None):
            c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x, yy, w, h, 7, fill=1, stroke=1)
            c.setFillColor(colors.HexColor(tone)); c.rect(x, yy, 4, h, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica-Bold", 5.4); c.drawString(x+9, yy+h-15, str(label).upper()[:25])
            c.setFillColor(colors.HexColor(value_color or TXT)); c.setFont("Helvetica-Bold", 12.5); c.drawString(x+9, yy+h-32, str(value)[:18])
            c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 4.7); c.drawString(x+9, yy+7, str(sub)[:34])

        def draw_recovery_table(rows):
            nonlocal y
            section("Recuperación por tienda")
            headers = ["#","Tienda","Dev Pzs","Pzas recup.","Conversión","Valor devolución","Recuperación $","Recup. %","Pend. Pzs","Pend. $"]
            widths = [.035,.15,.075,.085,.08,.13,.125,.08,.08,.11]
            tw = W-2*M; xs=[M]; acc=M
            for frac in widths[:-1]: acc += tw*frac; xs.append(acc)
            hh=20
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M,y-hh+3,tw,hh,5,fill=1,stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",4.6)
            for j,h in enumerate(headers): c.drawString(xs[j]+2,y-8,h)
            y -= hh
            rh = 9.7 if len(rows) >= 15 else 11
            for i,r in enumerate(rows):
                bg = colors.white if i%2==0 else colors.HexColor(ALT)
                c.setFillColor(bg); c.rect(M,y-rh+2,tw,rh,fill=1,stroke=0)
                if r.get("is_project") or str(r.get("store") or "") in project_names:
                    c.setFillColor(colors.HexColor(BLUE2)); c.rect(M,y-rh+2,2.4,rh,fill=1,stroke=0)
                vals = [
                    f"#{i+1}", r.get("store", ""), n(r.get("dev_pzs")), n(r.get("converted_pieces")),
                    pct(r.get("conversion_pct")), money(r.get("return_value")), money(r.get("recovered_value")),
                    pct(r.get("recovery_pct")), n(r.get("pending_pieces")), money(r.get("pending_value")),
                ]
                for j,val in enumerate(vals):
                    c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold" if j in (0,1,4) else "Helvetica",4.35)
                    c.drawString(xs[j]+2,y-7.3,str(val)[:25])
                y -= rh
            y -= 5

        def draw_recovery_chart(rows):
            nonlocal y
            if not rows: return
            if y - BOTTOM < 145:
                new_page("Centro Ejecutivo - recuperación"); period_line()
            section(f"Devolución y recuperación - {scope} - {period}")
            chart_bottom = BOTTOM + 6
            chart_top = y - 4
            available = max(100, chart_top-chart_bottom)
            row_h = min(8.0, max(6.2, available/max(1,len(rows))))
            left=M+100; right=W-M-135; plot=right-left
            max_dev=max([_num(r.get("dev_pzs")) for r in rows]+[1])
            c.setFillColor(colors.HexColor(BLUE)); c.rect(left,y-2,8,5,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",5); c.drawString(left+11,y-1,"Dev Pzs")
            c.setFillColor(colors.HexColor(PINK)); c.rect(left+55,y-2,8,5,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.drawString(left+66,y-1,"Pzas recuperadas")
            y -= 8
            for i,r in enumerate(rows):
                yy=y-i*row_h
                dev=_num(r.get("dev_pzs")); rec=_num(r.get("converted_pieces"))
                dev_w=plot*dev/max_dev; rec_w=plot*rec/max_dev
                c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",4.5); c.drawRightString(left-6,yy,str(r.get("store", ""))[:16])
                c.setFillColor(colors.HexColor(BLUE)); c.rect(left,yy-1,max(.5,dev_w),2.3,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(PINK)); c.rect(left,yy-4,max(.5,rec_w),2.3,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",4.3)
                c.drawString(right+6,yy-2,f"Conv. {pct(r.get('conversion_pct'))}  Econ. {pct(r.get('recovery_pct'))}")
            y = chart_bottom

        def draw_operational_table(rows):
            nonlocal y
            section("Detalle operativo - tiendas del proyecto")
            headers=["Ranking","Tienda","Dev pzs","Muertos","Probador","Cajas","Pend. Ant.","Total pzs","Recorridos","Acondicionado","Ubicado","Pend. acond.","Pend. ubicar"]
            widths=[.035,.12,.065,.06,.06,.055,.07,.07,.075,.075,.07,.125,.12]
            tw=W-2*M; xs=[M]; acc=M
            for frac in widths[:-1]: acc += tw*frac; xs.append(acc)
            hh=21
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M,y-hh+3,tw,hh,5,fill=1,stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",4.4)
            for j,h in enumerate(headers): c.drawString(xs[j]+2,y-8,h)
            y -= hh
            rh=10.2 if len(rows)>=15 else 11.5
            for i,r in enumerate(rows):
                bg=colors.white if i%2==0 else colors.HexColor(ALT)
                c.setFillColor(bg); c.rect(M,y-rh+2,tw,rh,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(BLUE2)); c.rect(M,y-rh+2,2.4,rh,fill=1,stroke=0)
                total=r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")
                raw=[f"#{i+1}",r.get("store",""),r.get("dev_pzs"),r.get("muertos"),r.get("probador"),r.get("cajas"),r.get("pendiente_anterior"),total,r.get("recorridos"),r.get("acondicionado"),r.get("ubicado"),r.get("pendiente_acondicionar"),r.get("pendiente_ubicar")]
                shown=[raw[0],raw[1]]+[n(v) for v in raw[2:]]
                for j,val in enumerate(shown):
                    zero_red = 2 <= j <= 10 and _num(raw[j]) == 0
                    c.setFillColor(colors.HexColor(RED if zero_red else TXT))
                    c.setFont("Helvetica-Bold" if (j in (0,1) or zero_red) else "Helvetica",4.35)
                    c.drawString(xs[j]+2,y-7.3,str(val)[:24])
                y -= rh
            y -= 6

        def tag(cx,cy,text,color_hex,font=4.8):
            width=stringWidth(text,"Helvetica-Bold",font)+4
            c.setFillColor(colors.white); c.roundRect(cx-width/2,cy-2,width,7.5,2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(color_hex)); c.setFont("Helvetica-Bold",font); c.drawCentredString(cx,cy,text)

        def draw_operational_chart(rows):
            nonlocal y
            if not rows: return
            if y - BOTTOM < 200:
                new_page("Centro Ejecutivo - gráfico operativo"); period_line()
            section(f"Ingreso vs Acondicionado vs Ubicado - {period}")
            base=BOTTOM+14; top=y-9; plot_h=max(90,top-base)
            x0=M+42; x1=W-M-12; group_w=(x1-x0)/max(1,len(rows)); bar_w=min(12,max(3.5,group_w*.22))
            axis_max=max([_num(v) for r in rows for v in ((r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")),r.get("acondicionado"),r.get("ubicado"))]+[1])*1.15
            c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(.5)
            for q in range(5):
                gy=base+plot_h*q/4; c.line(x0,gy,x1,gy)
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",4.7); c.drawRightString(x0-5,gy-2,n(axis_max*q/4))
            points=[]
            for i,r in enumerate(rows):
                cx=x0+group_w*(i+.5)
                total=_num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"))
                acond=_num(r.get("acondicionado")); ubicado=_num(r.get("ubicado"))
                ah=plot_h*acond/axis_max; uh=plot_h*ubicado/axis_max
                c.setFillColor(colors.HexColor(BLUE)); c.rect(cx-bar_w-2,base,bar_w,max(.7,ah),fill=1,stroke=0)
                c.setFillColor(colors.HexColor(PINK)); c.rect(cx+2,base,bar_w,max(.7,uh),fill=1,stroke=0)
                if len(rows) <= 8:
                    if acond == 0 and ubicado == 0:
                        tag(cx,base+2.5,"A 0 / U 0",RED,4.4)
                    else:
                        tag(cx-bar_w/2-2,base+ah+3,"A "+n(acond),RED if acond==0 else BLUE,4.3)
                        tag(cx+bar_w/2+2,base+uh+3,"U "+n(ubicado),RED if ubicado==0 else PINK,4.3)
                py=base+plot_h*total/axis_max
                points.append((cx,py,total))
                c.setFillColor(colors.HexColor(BLUE2)); c.circle(cx,py,2.2,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",4.4)
                c.saveState(); c.translate(cx-1,base-6); c.rotate(40); c.drawString(0,0,str(r.get("store", ""))[:12]); c.restoreState()
            c.setStrokeColor(colors.HexColor(BLUE2)); c.setLineWidth(1.2)
            for p1,p2 in zip(points,points[1:]): c.line(p1[0],p1[1],p2[0],p2[1])
            for cx,py,total in points: tag(cx,min(top-1,py+6),"Total "+n(total),RED if total==0 else BLUE2,4.5)

        page_header(); period_line()
        kpis=[
            ("Conversión",pct(mt.get("conversion_pct")),"FIFO diario - misma semana ISO",PURPLE,metric_color(mt.get("conversion_pct"))),
            ("Pzas recuperadas",n(mt.get("converted_pieces")),"Sólo ventas posteriores a la devolución",GREEN,None),
            ("Recuperación económica",pct(mt.get("recovery_pct")),"Recuperación $ / Valor devolución",PINK,metric_color(mt.get("recovery_pct"))),
            ("Valor de la devolución",money(mt.get("return_value")),"Devoluciones del periodo consultado",BLUE2,None),
            ("Recuperación $",money(mt.get("recovered_value")),"Misma semana ISO",GREEN,None),
            ("Pendiente $",money(mt.get("pending_recovery_value")),"Valor devolución - Recuperación $",RED,None),
        ]
        gap=6; card_w=(W-2*M-gap*5)/6; card_h=55
        for i,(label,value,sub,tone,value_color) in enumerate(kpis):
            card(M+i*(card_w+gap),y-card_h,card_w,card_h,label,value,sub,tone,value_color)
        y -= card_h+10
        c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",5.8)
        c.drawString(M,y,"Regla de recuperación: una devolución sólo recupera venta del mismo ID/SKU y tienda desde la fecha de devolución hasta el domingo de esa misma semana ISO.")
        y -= 13
        draw_recovery_table(recovery)
        draw_recovery_chart(recovery)

        new_page("Centro Ejecutivo - operación"); period_line()
        if project_stores:
            draw_operational_table(project_stores)
            draw_operational_chart(project_stores)
        else:
            section("Detalle operativo - tiendas del proyecto")
            c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",8)
            c.drawString(M,y,"No hay tiendas guardadas como Proyecto. Selecciónalas en Metas y tiendas y guarda la selección.")

        c.save()
        pdf=out.getvalue()
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError("El generador V96 no produjo un PDF válido")
        return pdf

    module._build_operations_pdf = build_pdf_v96
    module._V96_CENTER_EXEC_PDF = True
    print("[V96-PDF] Centro Ejecutivo sincronizado con el reporte web.", flush=True)
