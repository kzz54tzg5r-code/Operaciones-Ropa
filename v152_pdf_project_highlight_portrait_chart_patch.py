"""V152 · PDF Cambios y Muertos: resaltado Proyecto + gráfica vertical exclusiva.

Reglas:
- Día / Semana / Mes / Año (Centro Operativo) usan la misma estructura PDF.
- Hoja 1 horizontal: KPIs + Recuperación por tienda (todas las tiendas).
- Si esa tabla mezcla tiendas Proyecto y no Proyecto, las Proyecto se resaltan
  igual que en web (fondo azul tenue + barra lateral + etiqueta Proyecto).
- Si la tabla contiene sólo tiendas Proyecto, no se aplica resaltado especial.
- Hoja 2 VERTICAL exclusiva: gráfica Devolución vs Recuperación, para que las
  17 tiendas se lean completas y sin comprimir el gráfico.
- Hoja 3 horizontal: detalle operativo sólo Proyecto + gráfica operativa.

No recalcula datos: consume exactamente el payload ya filtrado por V151.
"""
from __future__ import annotations

import io
import math


def _num(v):
    try:
        x = float(v or 0)
        return x if math.isfinite(x) else 0.0
    except Exception:
        return 0.0


def install(m):
    if getattr(m, "_V152_PDF_PROJECT_PORTRAIT", False):
        return

    old = m._build_operations_pdf

    controlled = {"Operación Diaria", "Reporte Semanal", "Reporte Mensual", "Centro Ejecutivo"}

    def build(data: dict, report: str, scope: str = "Compañía") -> bytes:
        if report not in controlled:
            return old(data, report, scope)

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape, portrait
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase.pdfmetrics import stringWidth

            LW, LH = landscape(letter)
            PW, PH = portrait(letter)
            M = 26
            NAVY = "#173F78"
            NAVY2 = "#1D4A83"
            BLUE = "#246FE5"
            PINK = "#EC007C"
            PURPLE = "#7338EF"
            GREEN = "#10B981"
            GOLD = "#F3A300"
            RED = "#EF3434"
            TEXT = "#0F3463"
            MUT = "#667892"
            LINE = "#D6E0EC"
            BG = "#F2F6FB"
            ALT = "#EEF4FB"
            PROJ = "#DDEAFF"

            metrics = dict(data.get("metrics") or {})
            recovery = [dict(x) for x in (data.get("recovery_by_store") or [])]
            project_rows = [dict(x) for x in (data.get("stores") or [])]
            project_names = {str(x).strip() for x in (data.get("project_stores") or []) if str(x).strip()}
            if not project_names:
                project_names = {
                    str(r.get("store") or "").strip()
                    for r in project_rows if r.get("is_project")
                }
            recovery.sort(key=lambda r: (-_num(r.get("conversion_pct")), str(r.get("store") or "")))
            project_rows = [r for r in project_rows if str(r.get("store") or "").strip() in project_names or r.get("is_project")]
            project_rows.sort(key=lambda r: (-_num(r.get("total_pzs", r.get("ingresos"))), str(r.get("store") or "")))

            period_type = str(data.get("period_type") or "").lower()
            period_value = str(data.get("period_value") or "")
            start_date = str(data.get("start_date") or "")
            end_date = str(data.get("end_date") or "")
            period = period_value or (f"{start_date} a {end_date}" if start_date or end_date else "Histórico")
            mode_label = {
                "day": "Diario", "week": "Semanal", "month": "Mensual", "year": "Anual", "all": "Histórico"
            }.get(period_type, "Semanal" if report == "Reporte Semanal" else ("Mensual" if report == "Reporte Mensual" else "Operativo"))

            shown_recovery = recovery[:17]
            visible_names = {str(r.get("store") or "").strip() for r in shown_recovery}
            visible_project = visible_names & project_names
            # Resaltar sólo cuando Proyecto convive con otras tiendas en la misma tabla.
            mixed_recovery = bool(visible_project) and bool(visible_names - project_names)

            def f(v):
                return f"{_num(v):,.0f}"

            def pct(v):
                return f"{_num(v):.1f}%"

            def money(v):
                return f"${_num(v):,.0f}"

            def metric_color(v):
                return GREEN if _num(v) >= 80 else (GOLD if _num(v) >= 65 else RED)

            bio = io.BytesIO()
            c = canvas.Canvas(bio, pagesize=(LW, LH))
            y = 0

            def header_landscape(suffix=""):
                nonlocal y
                c.setPageSize((LW, LH))
                c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, LW, LH, fill=1, stroke=0)
                c.setFillColor(colors.HexColor(NAVY2)); c.roundRect(M, LH-92, LW-2*M, 64, 12, fill=1, stroke=0)
                c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 18); c.drawString(M+18, LH-56, "Cambios y Muertos")
                c.setFont("Helvetica", 8); c.drawString(M+18, LH-74, "Recuperación, conversión, recolección y seguimiento operativo")
                c.setFont("Helvetica-Bold", 9.2); c.drawRightString(LW-M-18, LH-54, "Operaciones Ropa - Price Shoes")
                c.setFont("Helvetica", 7.4); c.drawRightString(LW-M-18, LH-72, f"Centro Operativo · {mode_label}" + ((" · "+suffix) if suffix else ""))
                y = LH - 108
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 7)
                c.drawString(M, y, f"Periodo: {period}   ·   Alcance KPI: tiendas Proyecto")
                y -= 14

            def header_portrait():
                nonlocal y
                c.setPageSize((PW, PH))
                c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, PW, PH, fill=1, stroke=0)
                c.setFillColor(colors.HexColor(NAVY2)); c.roundRect(M, PH-92, PW-2*M, 64, 12, fill=1, stroke=0)
                c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 16); c.drawString(M+16, PH-57, "Cambios y Muertos")
                c.setFont("Helvetica", 7.4); c.drawString(M+16, PH-74, "Recuperación por tienda · comparativo compañía")
                c.setFont("Helvetica-Bold", 8); c.drawRightString(PW-M-16, PH-56, "Operaciones Ropa - Price Shoes")
                c.setFont("Helvetica", 6.5); c.drawRightString(PW-M-16, PH-72, f"Centro Operativo · {mode_label}")
                y = PH - 112
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 7); c.drawString(M, y, f"Periodo: {period}")
                y -= 18

            def new_landscape(suffix=""):
                c.showPage(); header_landscape(suffix)

            def new_portrait():
                c.showPage(); header_portrait()

            def card(x, yy, w, h, lab, val, sub, accent, value_color=None):
                c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x, yy, w, h, 8, fill=1, stroke=1)
                c.setFillColor(colors.HexColor(accent)); c.rect(x, yy, 4.5, h, fill=1, stroke=0)
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica-Bold", 5.8); c.drawString(x+11, yy+h-16, str(lab).upper()[:30])
                c.setFillColor(colors.HexColor(value_color or TEXT)); c.setFont("Helvetica-Bold", 15); c.drawString(x+11, yy+h-38, str(val)[:18])
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 5.1); c.drawString(x+11, yy+7, str(sub)[:42])

            def kpi_cards():
                nonlocal y
                gap = 7; cols = 5; cw = (LW-2*M-gap*(cols-1))/cols; ch = 48
                items = [
                    ("Dev pzs", f(metrics.get("dev_pzs")), "Devoluciones del periodo", NAVY, None),
                    ("Muertos", f(metrics.get("muertos")), "Recolección · motivo Muertos", PINK, None),
                    ("Probador", f(metrics.get("probador")), "Motivo Probador", GOLD, RED if _num(metrics.get("probador")) == 0 else None),
                    ("Cajas", f(metrics.get("cajas")), "Recolección · Cajas", PURPLE, RED if _num(metrics.get("cajas")) == 0 else None),
                    ("Total pzs", f(metrics.get("total_pzs", metrics.get("ingresos"))), "Dev + Muertos + Cajas + Probador + Pend. Ant.", BLUE, None),
                    ("Recorridos realizados", f(metrics.get("recorridos")), f"{pct(metrics.get('pct_recorridos'))} · meta {f(metrics.get('meta_recorridos'))}", GREEN, None),
                    ("% Acondicionado", pct(metrics.get("pct_acondicionado")), f"{f(metrics.get('acondicionado'))} piezas acondicionadas", PURPLE, metric_color(metrics.get("pct_acondicionado"))),
                    ("% Ubicado", pct(metrics.get("pct_ubicado")), f"{f(metrics.get('ubicado'))} piezas ubicadas", PINK, metric_color(metrics.get("pct_ubicado"))),
                    ("Pendiente de acondicionar", f(metrics.get("pendiente_acondicionar")), "Total pzs - Acondicionado", GOLD, None),
                    ("Pendiente de ubicar", f(metrics.get("pendiente_ubicar")), "Total pzs - Ubicado", RED, None),
                ]
                for i, item in enumerate(items):
                    rr, cc = divmod(i, cols)
                    x = M + cc*(cw+gap); yy = y - rr*(ch+gap) - ch
                    card(x, yy, cw, ch, *item)
                y -= 2*(ch+gap)+4

            def recovery_table(rows):
                nonlocal y
                if not rows: return
                c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica-Bold", 11.5); c.drawString(M, y, "Recuperación por tienda")
                if mixed_recovery:
                    c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 5.8); c.drawRightString(LW-M, y, "Azul tenue = tienda Proyecto")
                y -= 15
                heads = ["#", "Tienda", "Dev Pzs", "Pzas recup.", "Conversión", "Valor dev.", "Recuperación $", "Recup. %", "Pend. Pzs", "Pend. $"]
                fr = [.035,.13,.08,.09,.09,.12,.13,.09,.09,.105]; tw = LW-2*M; xs=[M]; acc=M
                for q in fr[:-1]: acc += tw*q; xs.append(acc)
                hh=17; rh=8.5 if len(rows)>=15 else 10
                c.setFillColor(colors.HexColor(NAVY2)); c.roundRect(M, y-hh+2, tw, hh, 4, fill=1, stroke=0)
                c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.6)
                for j,h in enumerate(heads): c.drawString(xs[j]+2, y-7, h)
                y -= hh
                for i,r in enumerate(rows):
                    name = str(r.get("store") or "").strip(); is_proj = mixed_recovery and name in project_names
                    c.setFillColor(colors.HexColor(PROJ if is_proj else (ALT if i%2 else "#FFFFFF"))); c.rect(M, y-rh+1, tw, rh, fill=1, stroke=0)
                    if is_proj:
                        c.setFillColor(colors.HexColor(BLUE)); c.rect(M, y-rh+1, 2.8, rh, fill=1, stroke=0)
                    vals=[f"#{i+1}",name,f(r.get("dev_pzs")),f(r.get("converted_pieces")),pct(r.get("conversion_pct")),money(r.get("return_value")),money(r.get("recovered_value")),pct(r.get("recovery_pct")),f(r.get("pending_pieces")),money(r.get("pending_value"))]
                    c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica",4.35)
                    for j,v in enumerate(vals):
                        if j==1 and is_proj:
                            c.setFont("Helvetica-Bold",4.35); c.drawString(xs[j]+2,y-6.4,str(v)[:17]); c.setFillColor(colors.HexColor(BLUE)); c.setFont("Helvetica-Bold",3.65); c.drawRightString(xs[2]-4,y-6.4,"Proyecto"); c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica",4.35)
                        else:
                            c.drawString(xs[j]+2,y-6.4,str(v)[:24])
                    y -= rh
                y -= 3

            def recovery_chart_portrait(rows):
                nonlocal y
                if not rows: return
                new_portrait()
                c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica-Bold", 13)
                c.drawString(M, y, f"Devolución y recuperación · Todas las tiendas · {period}")
                y -= 18
                c.setFillColor(colors.HexColor(NAVY)); c.rect(M+86,y-2,8,8,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica",6.5); c.drawString(M+99,y,"Dev Pzs")
                c.setFillColor(colors.HexColor(PINK)); c.rect(M+148,y-2,8,8,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(TEXT)); c.drawString(M+161,y,"Recup. Pzs")
                if mixed_recovery:
                    c.setFillColor(colors.HexColor(PROJ)); c.rect(M+229,y-2,8,8,fill=1,stroke=0); c.setFillColor(colors.HexColor(TEXT)); c.drawString(M+242,y,"Proyecto")
                y -= 17
                shown=rows[:17]; maxv=max([_num(r.get("dev_pzs")) for r in shown]+[1]); left=M+92; x0=M+104; x1=PW-116; right=x1+10; avail=max(180,x1-x0); group_h=min(31.5,max(27.0,(y-48)/max(1,len(shown))))
                for i,r in enumerate(shown):
                    top=y-i*group_h; name=str(r.get("store") or "").strip(); dev=_num(r.get("dev_pzs")); got=_num(r.get("converted_pieces")); conv=_num(r.get("conversion_pct")); econ=_num(r.get("recovery_pct")); dw=avail*dev/maxv; gw=avail*got/maxv
                    if mixed_recovery and name in project_names:
                        c.setFillColor(colors.HexColor(PROJ)); c.roundRect(M+4,top-25,PW-2*M-8,25.5,4,fill=1,stroke=0); c.setFillColor(colors.HexColor(BLUE)); c.rect(M+4,top-25,2.5,25.5,fill=1,stroke=0)
                    c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica-Bold" if name in project_names and mixed_recovery else "Helvetica",5.6); c.drawRightString(left,top-8,f"#{i+1} · {name[:17]}")
                    c.setFillColor(colors.HexColor("#E5ECF5")); c.roundRect(x0,top-11,avail,7.2,2.5,fill=1,stroke=0); c.setFillColor(colors.HexColor(NAVY)); c.roundRect(x0,top-11,max(.8,dw),7.2,2.5,fill=1,stroke=0); c.setFont("Helvetica-Bold",5.4); c.drawString(min(x1-26,x0+dw+4),top-9.6,f(dev))
                    c.setFillColor(colors.HexColor("#E5ECF5")); c.roundRect(x0,top-22,avail,7.2,2.5,fill=1,stroke=0); c.setFillColor(colors.HexColor(PINK)); c.roundRect(x0,top-22,max(.8,gw),7.2,2.5,fill=1,stroke=0); c.setFont("Helvetica-Bold",5.4); c.drawString(min(x1-26,x0+gw+4),top-20.6,f(got))
                    c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica",4.9); c.drawString(right,top-14.3,f"Conv. {conv:.1f}% · Econ. {econ:.1f}%")

            def operational_table(rows):
                nonlocal y
                if not rows: return
                c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica-Bold",11.5); c.drawString(M,y,"Detalle operativo · tiendas del proyecto"); y-=16
                heads=["#","Tienda","Dev","Muertos","Prob.","Cajas","Pend.Ant.","Total","Recorr.","Acond.","Ubic.","% Acond.","% Ubic.","Pend.Acond.","Pend.Ubic."]
                fr=[.035,.105,.055,.05,.052,.045,.058,.055,.074,.065,.058,.068,.064,.105,.104]; tw=LW-2*M; xs=[M]; acc=M
                for q in fr[:-1]: acc+=tw*q; xs.append(acc)
                hh=20; rh=15 if len(rows)<=8 else 11.5
                c.setFillColor(colors.HexColor(NAVY2)); c.roundRect(M,y-hh+2,tw,hh,5,fill=1,stroke=0); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",4.4)
                for j,h in enumerate(heads): c.drawString(xs[j]+2,y-8,h)
                y-=hh
                for i,r in enumerate(rows):
                    total=_num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")); pa=_num(r.get("pct_acondicionado")) if r.get("pct_acondicionado") is not None else (_num(r.get("acondicionado"))/total*100 if total else 0); pu=_num(r.get("pct_ubicado")) if r.get("pct_ubicado") is not None else (_num(r.get("ubicado"))/total*100 if total else 0)
                    c.setFillColor(colors.HexColor(ALT if i%2 else "#FFFFFF")); c.rect(M,y-rh+1,tw,rh,fill=1,stroke=0)
                    vals=[f"#{i+1}",str(r.get("store") or ""),f(r.get("dev_pzs")),f(r.get("muertos")),f(r.get("probador")),f(r.get("cajas")),f(r.get("pendiente_anterior")),f(total),f(r.get("recorridos")),f(r.get("acondicionado")),f(r.get("ubicado")),pct(pa),pct(pu),f(r.get("pendiente_acondicionar")),f(r.get("pendiente_ubicar"))]
                    for j,v in enumerate(vals):
                        col=TEXT
                        if j in (2,3,4,5,6,7,8,9,10) and _num(str(v).replace(",",""))==0: col=RED
                        if j==11: col=metric_color(pa)
                        if j==12: col=metric_color(pu)
                        c.setFillColor(colors.HexColor(col)); c.setFont("Helvetica-Bold" if j in (0,1,7,11,12) else "Helvetica",4.55); c.drawString(xs[j]+2,y-8.3,str(v)[:22])
                    y-=rh
                y-=7

            def combo_chart(rows):
                nonlocal y
                if not rows: return
                if y < 240: new_landscape("Detalle Proyecto")
                c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica-Bold",11.5); c.drawString(M,y,f"Ingreso vs Acondicionado vs Ubicado · {period}"); y-=18
                x0=M+44; x1=LW-M-12; base=42; top=y-4; ph=max(105,top-base); gw=(x1-x0)/max(1,len(rows)); bw=min(13,gw*.23); mx=max([_num(v) for r in rows for v in (r.get("total_pzs",r.get("ingresos")),r.get("acondicionado"),r.get("ubicado"))]+[1])*1.12
                c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(.6)
                for q in range(5):
                    gy=base+ph*q/4; c.line(x0,gy,x1,gy); c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",4.7); c.drawRightString(x0-5,gy-2,f(mx*q/4))
                pts=[]
                def tag(cx,cy,text,col):
                    w=stringWidth(text,"Helvetica-Bold",4.8)+5; c.setFillColor(colors.white); c.roundRect(cx-w/2,cy-2,w,7.5,2,fill=1,stroke=0); c.setFillColor(colors.HexColor(col)); c.setFont("Helvetica-Bold",4.8); c.drawCentredString(cx,cy,text)
                for i,r in enumerate(rows):
                    cx=x0+gw*(i+.5); tot=_num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")); ac=_num(r.get("acondicionado")); ub=_num(r.get("ubicado")); ah=ph*ac/mx; uh=ph*ub/mx
                    c.setFillColor(colors.HexColor(NAVY)); c.rect(cx-bw-2,base,bw,max(.7,ah),fill=1,stroke=0); c.setFillColor(colors.HexColor(PINK)); c.rect(cx+2,base,bw,max(.7,uh),fill=1,stroke=0)
                    py=base+ph*tot/mx; pts.append((cx,py,tot)); c.setFillColor(colors.HexColor(BLUE)); c.circle(cx,py,2.4,fill=1,stroke=0); c.setFillColor(colors.HexColor(TEXT)); c.setFont("Helvetica",5); c.drawCentredString(cx,base-12,str(r.get("store") or "")[:13])
                    if ac==0 and ub==0: tag(cx,base+3,"A 0 / U 0",RED)
                    else: tag(cx-bw/2-2,base+ah+3,"A "+f(ac),NAVY); tag(cx+bw/2+2,base+uh+3,"U "+f(ub),PINK)
                c.setStrokeColor(colors.HexColor(BLUE)); c.setLineWidth(1.3)
                for p1,p2 in zip(pts,pts[1:]): c.line(p1[0],p1[1],p2[0],p2[1])
                for cx,py,tot in pts: tag(cx,min(top-2,py+6),"Total "+f(tot),BLUE)

            # Hoja 1: KPIs Proyecto + comparativo de todas las tiendas.
            header_landscape(); kpi_cards(); recovery_table(shown_recovery)
            # Hoja 2: gráfica exclusiva vertical, como la versión validada V107.
            recovery_chart_portrait(shown_recovery)
            # Hoja 3: sólo Proyecto. No se pinta azul porque no está mezclado con otras tiendas.
            if project_rows:
                new_landscape("Tiendas Proyecto"); operational_table(project_rows); combo_chart(project_rows)

            c.save(); result=bio.getvalue()
            if not result.startswith(b"%PDF"):
                raise RuntimeError("V152 no produjo PDF válido")
            print(f"[V152-PDF] {mode_label} · proyecto={len(project_names)} · recuperación={len(shown_recovery)} · mixed={mixed_recovery} · vertical=1", flush=True)
            return result
        except Exception as exc:
            print(f"[V152-PDF] warning {type(exc).__name__}: {exc}", flush=True)
            return old(data, report, scope)

    m._build_operations_pdf = build
    m._V152_PDF_PROJECT_PORTRAIT = True
    print("[V152-PDF] Proyecto resaltado sólo en tablas mixtas + gráfica recuperación en hoja vertical exclusiva.", flush=True)
