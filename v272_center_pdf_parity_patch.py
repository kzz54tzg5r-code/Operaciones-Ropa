"""V272.1 · PDF Centro Operativo fiel a la vista consultada.

Objetivo:
- El PDF de Centro Operativo usa exactamente el mismo alcance/periodo que la vista.
- Replica las 6 tarjetas, la matriz operativa Opción 7, las tablas y el gráfico
  Ingreso vs Acondicionado vs Ubicado.
- Elimina del PDF el gráfico heredado "Devolución y recuperación", ya retirado
  de la pantalla por V240.
- Día no imprime la tabla de recuperación, igual que la pantalla.
- No altera cálculos, datos, filtros, roles, permisos ni exportación Excel.
"""
from __future__ import annotations

import io
import math
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape


def install(m):
    if getattr(m, "_V272_CENTER_PDF_PARITY", False):
        return

    previous_builder = m._build_operations_pdf

    def _num(value):
        try:
            out = float(value or 0)
            return out if math.isfinite(out) else 0.0
        except Exception:
            return 0.0

    def _is_center_report(report: str) -> bool:
        name = str(report or "").strip().lower()
        return (
            "centro ejecutivo" in name
            or "centro operativo" in name
            or "reporte semanal" in name
            or "reporte mensual" in name
            or "operación diaria" in name
            or "operacion diaria" in name
        )

    def _build_center_pdf(data: dict, report: str, scope: str = "Compañía") -> bytes:
        bio = io.BytesIO()
        c = pdfcanvas.Canvas(bio, pagesize=landscape(letter))
        W, H = landscape(letter)

        # Paleta de la interfaz actual.
        NAVY = "#173B73"
        BLUE = "#1769E8"
        BLUE_DARK = "#0B5597"
        PINK = "#EC007C"
        PURPLE = "#7C3AED"
        GREEN = "#10B981"
        GREEN_DARK = "#047857"
        ORANGE = "#F59E0B"
        ORANGE_DARK = "#C2410C"
        BG = "#F3F6FA"
        LINE = "#D8E0EB"
        TEXT = "#173B73"
        MUTED = "#667085"
        PROJECT = "#DDEAFF"
        M = 24
        y = H - M

        mt = dict(data.get("metrics") or {})
        project_stores, recovery = m._operations_export_sections(data)
        period_type = str(data.get("period_type") or "month").lower()
        period_value = str(data.get("period_value") or "")
        mode_label = {
            "day": "Día",
            "week": "Semanal",
            "month": "Mensual",
            "year": "Anual",
        }.get(period_type, "Consulta")

        MONTHS = [
            "enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"
        ]

        def period_label():
            if period_type == "month":
                try:
                    year, month = period_value.split("-")[:2]
                    return f"{MONTHS[int(month)-1]} {year}"
                except Exception:
                    return period_value or "Histórico"
            return period_value or "Histórico"

        def n(v):
            return f"{_num(v):,.0f}"

        def pc(v):
            return f"{_num(v):.1f}%"

        def money(v):
            return f"${_num(v):,.0f}"

        def safe(v):
            if v is None:
                return "—"
            return str(v)

        def fit(text, max_chars):
            s = safe(text)
            return s if len(s) <= max_chars else s[:max(1, max_chars - 1)] + "…"

        def set_fill(hex_color):
            c.setFillColor(colors.HexColor(hex_color))

        def set_stroke(hex_color):
            c.setStrokeColor(colors.HexColor(hex_color))

        def page_header(suffix=""):
            nonlocal y
            set_fill(BG)
            c.rect(0, 0, W, H, fill=1, stroke=0)
            set_fill("#265B98")
            c.roundRect(M, H - 88, W - 2*M, 58, 11, fill=1, stroke=0)

            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 17)
            c.drawString(M + 16, H - 55, "Cambios y Muertos")
            c.setFont("Helvetica", 7.6)
            c.drawString(M + 16, H - 71, "Recuperación, conversión, recolección y seguimiento operativo")

            c.setFont("Helvetica-Bold", 8.5)
            c.drawRightString(W - M - 15, H - 53, "Operaciones Ropa · Price Shoes")
            c.setFont("Helvetica", 6.8)
            title = f"Centro Operativo · {mode_label}"
            if suffix:
                title += f" · {suffix}"
            c.drawRightString(W - M - 15, H - 69, title)

            y = H - 102

        def new_page(suffix=""):
            c.showPage()
            page_header(suffix)

        def ensure(height_needed, suffix=""):
            nonlocal y
            if y - height_needed < 24:
                new_page(suffix)

        def section(title, size=10.5):
            nonlocal y
            ensure(18)
            set_fill(TEXT)
            c.setFont("Helvetica-Bold", size)
            c.drawString(M, y, title)
            y -= 15

        def meta_line():
            nonlocal y
            set_fill(MUTED)
            c.setFont("Helvetica", 6.8)
            project_count = int(data.get("v151_project_store_count") or len(project_stores) or 0)
            left = f"Periodo: {period_label()}   ·   Tienda: {scope}"
            if project_count:
                left += f"   ·   Alcance KPI: {project_count} tiendas Proyecto"
            c.drawString(M, y, left)
            y -= 11

        def card_row(items):
            nonlocal y
            count = max(1, len(items))
            gap = 6
            card_w = (W - 2*M - gap*(count - 1)) / count
            card_h = 50
            ensure(card_h + 7)
            for idx, item in enumerate(items):
                label, value, sub, bg, tone = item
                x = M + idx*(card_w + gap)
                yy = y - card_h
                set_fill(bg)
                set_stroke(LINE)
                c.roundRect(x, yy, card_w, card_h, 7, fill=1, stroke=1)
                set_fill(tone)
                c.rect(x, yy, 4, card_h, fill=1, stroke=0)

                set_fill(tone)
                c.setFont("Helvetica-Bold", 5.8)
                c.drawString(x + 10, yy + 36, fit(label.upper(), 24))
                c.setFont("Helvetica-Bold", 13.2)
                c.drawString(x + 10, yy + 17, fit(value, 17))
                c.setFont("Helvetica-Bold", 5.5)
                c.drawString(x + 10, yy + 6, fit(sub, 28))
            y -= card_h + 8

        def draw_summary_matrix(show_opening=False):
            nonlocal y
            dev = _num(mt.get("dev_pzs"))
            muertos = _num(mt.get("muertos"))
            probador = _num(mt.get("probador"))
            cajas = _num(mt.get("cajas"))
            pending_prev = _num(mt.get("pendiente_anterior"))
            total_pzs = _num(mt.get("total_pzs") if mt.get("total_pzs") is not None else mt.get("ingresos"))
            acond = _num(mt.get("acondicionado"))
            ubicado = _num(mt.get("ubicado"))
            recorridos = _num(mt.get("recorridos"))
            meta_rec = _num(mt.get("meta_recorridos"))
            pct_rec = _num(mt.get("pct_recorridos")) if mt.get("pct_recorridos") is not None else (recorridos/meta_rec*100 if meta_rec else 0)
            pct_ac = _num(mt.get("pct_acondicionado")) if mt.get("pct_acondicionado") is not None else (acond/total_pzs*100 if total_pzs else 0)
            pct_ub = _num(mt.get("pct_ubicado")) if mt.get("pct_ubicado") is not None else (ubicado/total_pzs*100 if total_pzs else 0)
            pend_ac = _num(mt.get("pendiente_acondicionar")) if mt.get("pendiente_acondicionar") is not None else max(total_pzs-acond, 0)
            pend_ub = _num(mt.get("pendiente_ubicar")) if mt.get("pendiente_ubicar") is not None else max(total_pzs-ubicado, 0)
            total_op = dev + muertos + probador + cajas + (pending_prev if show_opening else 0)
            total_pending = pend_ac + pend_ub

            headers = ["Categoría", "Indicador", "Valor / Piezas", "%", "Meta", "Total"]
            fracs = [.14, .27, .18, .10, .11, .20]
            total_w = W - 2*M
            xs = [M]
            acc = M
            for frac in fracs[:-1]:
                acc += total_w * frac
                xs.append(acc)

            groups = [
                {
                    "name": "OPERACIÓN\n(RECOLECCIÓN)",
                    "fill": "#ECFDF5",
                    "tone": GREEN_DARK,
                    "accent": "#35D17D",
                    "rows": [
                        ("DEV PZS", n(dev), "—", "—", n(dev), ""),
                        ("MUERTOS", n(muertos), "—", "—", n(muertos), ""),
                        ("PROBADOR", n(probador), "—", "—", n(probador), ""),
                        ("CAJAS", n(cajas), "—", "—", n(cajas), ""),
                    ] + ([
                        ("PENDIENTE ANTERIOR", n(pending_prev), "—", "—", n(pending_prev), "")
                    ] if show_opening else []) + [
                        ("TOTAL OPERACIÓN", n(total_op), "—", "—", n(total_op), "total_op"),
                    ],
                },
                {
                    "name": "PENDIENTES",
                    "fill": "#FFF2E8",
                    "tone": ORANGE_DARK,
                    "accent": "#FF8A1F",
                    "rows": [
                        ("PENDIENTE DE ACONDICIONAR", n(pend_ac), "—", "—", n(pend_ac), ""),
                        ("PENDIENTE DE UBICAR", n(pend_ub), "—", "—", n(pend_ub), ""),
                        ("TOTAL PENDIENTES", n(total_pending), "—", "—", n(total_pending), "total_pending"),
                    ],
                },
                {
                    "name": "",
                    "fill": "#EAF3FF",
                    "tone": "#0D4B91",
                    "accent": "#4097F5",
                    "rows": [
                        ("TOTAL GENERAL · TOTAL PZS", n(total_pzs), "—", "—", n(total_pzs), "general"),
                    ],
                },
                {
                    "name": "AVANCE %",
                    "fill": "#F3EAFF",
                    "tone": PURPLE,
                    "accent": "#8B5CF6",
                    "rows": [
                        ("RECORRIDOS REALIZADOS", n(recorridos), pc(pct_rec), n(meta_rec), "—", ""),
                        ("% ACONDICIONADO", f"{pc(pct_ac)}  {n(acond)} pzs", pc(pct_ac), "—", "—", ""),
                        ("% UBICADO", f"{pc(pct_ub)}  {n(ubicado)} pzs", pc(pct_ub), "—", "—", ""),
                    ],
                },
            ]

            row_h = 13.2
            head_h = 18
            total_rows = sum(len(g["rows"]) for g in groups)
            needed = head_h + total_rows*row_h + 8
            ensure(needed, "Resumen")

            # Header.
            set_fill(BLUE_DARK)
            c.roundRect(M, y-head_h+2, total_w, head_h, 5, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 6.2)
            for i, h in enumerate(headers):
                if i >= 2:
                    c.drawCentredString(xs[i] + total_w*fracs[i]/2, y-10, h)
                else:
                    c.drawString(xs[i]+5, y-10, h)
            y -= head_h

            for group in groups:
                gh = len(group["rows"]) * row_h
                cat_x = xs[0]
                cat_w = total_w*fracs[0]
                cat_y = y - gh + 2
                if group["name"]:
                    set_fill(group["fill"])
                    c.roundRect(cat_x, cat_y, cat_w, gh, 6, fill=1, stroke=0)
                    set_fill(group["accent"])
                    c.roundRect(cat_x, cat_y, 5, gh, 2, fill=1, stroke=0)
                    set_fill(group["tone"])
                    parts = group["name"].split("\n")
                    c.setFont("Helvetica-Bold", 7.5)
                    base = cat_y + gh/2 + (5 if len(parts)>1 else 0)
                    for j, part in enumerate(parts):
                        c.drawCentredString(cat_x + cat_w/2 + 2, base - j*9, part)

                for ridx, row in enumerate(group["rows"]):
                    label, value, pctv, meta, totalv, cls = row
                    yy = y - row_h + 2
                    if cls == "total_op":
                        set_fill("#E9FAF3")
                    elif cls == "total_pending":
                        set_fill("#FFF0DF")
                    elif cls == "general":
                        set_fill("#DCEBFF")
                    else:
                        set_fill(colors.white.hexval() if hasattr(colors.white, "hexval") else "#FFFFFF")
                    c.rect(xs[1], yy, total_w*(1-fracs[0]), row_h, fill=1, stroke=0)
                    set_stroke("#DBE6F2")
                    c.line(xs[1], yy, M+total_w, yy)

                    vals = [label, value, pctv, meta, totalv]
                    for j, val in enumerate(vals, start=1):
                        set_fill(TEXT if cls not in ("total_op","total_pending","general") else group["tone"])
                        c.setFont("Helvetica-Bold" if (j == 1 or cls) else "Helvetica", 5.8 if j != 1 else 6.0)
                        col_w = total_w*fracs[j]
                        if j >= 2:
                            c.drawCentredString(xs[j] + col_w/2, yy + 4.1, fit(val, 24))
                        else:
                            c.drawString(xs[j] + 5, yy + 4.1, fit(val, 31))
                    y -= row_h
            y -= 7

        def draw_recovery_table():
            nonlocal y
            if period_type == "day":
                return
            rows = sorted(
                list(recovery or []),
                key=lambda r: (-_num(r.get("conversion_pct")), -_num(r.get("recovery_pct")), str(r.get("store") or "")),
            )
            if not rows:
                return

            section("Recuperación por tienda")
            headers = ["#", "Tienda", "Dev Pzs", "Pzas rec.", "Conversión", "Valor devolución", "Recuperación $", "Recup. %", "Pend. Pzs", "Pend. $"]
            fracs = [.04,.14,.07,.08,.08,.13,.13,.08,.08,.17]
            total_w = W - 2*M
            xs = [M]
            acc = M
            for frac in fracs[:-1]:
                acc += total_w*frac
                xs.append(acc)
            row_h = 10.4
            head_h = 14

            def head():
                nonlocal y
                set_fill(BLUE_DARK)
                c.roundRect(M, y-head_h+2, total_w, head_h, 4, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 4.8)
                for i, h in enumerate(headers):
                    c.drawString(xs[i]+2, y-8.8, fit(h, 18))
                y -= head_h

            ensure(head_h + min(len(rows), 17)*row_h + 8, "Recuperación")
            head()
            for idx, r in enumerate(rows, start=1):
                if y-row_h < 24:
                    new_page("Recuperación")
                    head()
                bg = PROJECT if r.get("is_project") else ("#FFFFFF" if idx%2 else "#EEF4FB")
                set_fill(bg)
                c.rect(M, y-row_h+2, total_w, row_h, fill=1, stroke=0)
                if r.get("is_project"):
                    set_fill(BLUE)
                    c.rect(M, y-row_h+2, 2.5, row_h, fill=1, stroke=0)
                values = [
                    f"#{idx}",
                    f"{r.get('store')}{' · Proyecto' if r.get('is_project') else ''}",
                    n(r.get("dev_pzs")),
                    n(r.get("converted_pieces")),
                    pc(r.get("conversion_pct")),
                    money(r.get("return_value")),
                    money(r.get("recovered_value")),
                    pc(r.get("recovery_pct")),
                    n(r.get("pending_pieces")),
                    money(r.get("pending_value")),
                ]
                for i, val in enumerate(values):
                    set_fill(TEXT)
                    c.setFont("Helvetica-Bold" if i in (0,1) else "Helvetica", 4.7)
                    c.drawString(xs[i]+2, y-7.1, fit(val, 22 if i==1 else 16))
                y -= row_h
            y -= 6

        def draw_operational_detail():
            nonlocal y
            rows = list(project_stores or [])
            if not rows:
                return
            rec_lookup = {str(r.get("store") or ""): _num(r.get("conversion_pct")) for r in recovery or []}
            rows.sort(key=lambda r: (-rec_lookup.get(str(r.get("store") or ""), 0), str(r.get("store") or "")))

            label = f"Detalle operativo · {period_label()}" if period_type == "day" else "Detalle operativo · tiendas del proyecto"
            section(label)
            headers = ["#", "Tienda", "Muertos", "Probador", "Cajas", "Ingresos", "Rec.", "Acond.", "Ubicado", "Pend.Acond", "Pend.Ubicar"]
            fracs = [.04,.14,.075,.075,.07,.09,.06,.09,.09,.115,.115]
            total_w = W - 2*M
            xs = [M]
            acc = M
            for frac in fracs[:-1]:
                acc += total_w*frac
                xs.append(acc)
            row_h = 10.2
            head_h = 14

            def head():
                nonlocal y
                set_fill(BLUE_DARK)
                c.roundRect(M, y-head_h+2, total_w, head_h, 4, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 4.8)
                for i,h in enumerate(headers):
                    c.drawString(xs[i]+2, y-8.8, fit(h, 18))
                y -= head_h

            ensure(head_h + min(len(rows),17)*row_h + 8, "Detalle operativo")
            head()
            for idx, r in enumerate(rows, start=1):
                if y-row_h < 24:
                    new_page("Detalle operativo")
                    head()
                set_fill(PROJECT if idx%2 else "#EEF4FB")
                c.rect(M, y-row_h+2, total_w, row_h, fill=1, stroke=0)
                set_fill(BLUE)
                c.rect(M, y-row_h+2, 2.5, row_h, fill=1, stroke=0)
                vals = [
                    f"#{idx}", r.get("store"), n(r.get("muertos")), n(r.get("probador")), n(r.get("cajas")),
                    n(r.get("recolectadas")), n(r.get("recorridos")), n(r.get("acondicionado")), n(r.get("ubicado")),
                    n(r.get("pendiente_acondicionar")), n(r.get("pendiente_ubicar")),
                ]
                for i,val in enumerate(vals):
                    set_fill(TEXT)
                    c.setFont("Helvetica-Bold" if i in (0,1) else "Helvetica", 4.7)
                    c.drawString(xs[i]+2, y-7.1, fit(val, 18))
                y -= row_h
            y -= 6

        def draw_combo_chart():
            nonlocal y
            rows = list(project_stores or [])
            rows = [r for r in rows if _num(r.get("recolectadas")) or _num(r.get("acondicionado")) or _num(r.get("ubicado"))]
            if not rows:
                return

            rec_lookup = {str(r.get("store") or ""): _num(r.get("conversion_pct")) for r in recovery or []}
            rows.sort(key=lambda r: (-rec_lookup.get(str(r.get("store") or ""), 0), str(r.get("store") or "")))

            # V272.1: el gráfico se dimensiona según las tiendas con información.
            # Con 1-5 tiendas no se estira de lado a lado ni deja barras aisladas.
            count = len(rows)
            chart_h = 124 if count <= 5 else (138 if count <= 9 else 154)
            ensure(chart_h + 25, "Gráfico operativo")
            section(f"Ingreso vs Acondicionado vs Ubicado · {scope} · {period_label()}")

            available_w = W - 2*M - 52
            desired_w = max(300, min(available_w, 105*count + 100))
            x0 = M + 40 + max(0, (available_w - desired_w)/2)
            x1 = x0 + desired_w
            base = y - chart_h + 24
            top = y - 14
            plot_h = max(60, top - base)
            plot_w = x1 - x0
            maxv = max([_num(r.get(k)) for r in rows for k in ("recolectadas","acondicionado","ubicado")] + [1])
            group_w = plot_w/max(1,count)
            bar_w = max(8, min(18, group_w*.24))

            # Fondo sutil para que el gráfico se lea como un bloque y no como
            # una zona vacía del PDF.
            set_fill("#FFFFFF")
            set_stroke(LINE)
            c.roundRect(x0-34, base-19, plot_w+46, plot_h+48, 7, fill=1, stroke=1)

            # Rejilla y eje Y.
            set_stroke(LINE)
            c.setLineWidth(.55)
            for q in range(5):
                gy = base + plot_h*q/4
                c.line(x0, gy, x1, gy)
                set_fill(MUTED)
                c.setFont("Helvetica", 5.1)
                c.drawRightString(x0-6, gy-1.5, n(maxv*q/4))

            points = []
            for i, r in enumerate(rows):
                cx = x0 + group_w*(i+.5)
                acond = _num(r.get("acondicionado"))
                ubic = _num(r.get("ubicado"))
                ingreso = _num(r.get("recolectadas"))
                ah = plot_h*acond/maxv
                uh = plot_h*ubic/maxv

                # Barras compactas y etiquetas visibles.
                set_fill(NAVY)
                c.roundRect(cx-bar_w-2, base, bar_w, max(1,ah), 1.5, fill=1, stroke=0)
                set_fill(PINK)
                c.roundRect(cx+2, base, bar_w, max(1,uh), 1.5, fill=1, stroke=0)

                label_fs = 5.0 if count <= 6 else 4.4
                value_fs = 4.7 if count <= 6 else 4.1

                if acond > 0:
                    set_fill(NAVY)
                    c.setFont("Helvetica-Bold", value_fs)
                    c.drawCentredString(cx-bar_w/2-2, min(top-1, base+ah+3), n(acond))
                if ubic > 0:
                    set_fill(PINK)
                    c.setFont("Helvetica-Bold", value_fs)
                    c.drawCentredString(cx+bar_w/2+2, min(top-1, base+uh+3), n(ubic))

                py = base + plot_h*ingreso/maxv
                points.append((cx, py, ingreso))
                set_fill(BLUE)
                c.circle(cx, py, 2.5, fill=1, stroke=0)
                if ingreso > 0:
                    set_fill(BLUE)
                    c.setFont("Helvetica-Bold", value_fs)
                    c.drawCentredString(cx, min(top-1, py+4), n(ingreso))

                # Tienda horizontal, centrada; evita texto inclinado/ilegible.
                set_fill(TEXT)
                c.setFont("Helvetica-Bold", label_fs)
                c.drawCentredString(cx, base-11, fit(r.get("store"), 14))

            if len(points) > 1:
                set_stroke(BLUE)
                c.setLineWidth(1.35)
                for a,b in zip(points, points[1:]):
                    c.line(a[0],a[1],b[0],b[1])

            # Leyenda compacta sobre el gráfico.
            ly = top + 8
            legend_x = x0
            set_fill(NAVY); c.rect(legend_x,ly,7,5,fill=1,stroke=0)
            set_fill(TEXT); c.setFont("Helvetica",5.3); c.drawString(legend_x+10,ly-1,"Acondicionado")
            legend_x += 86
            set_fill(PINK); c.rect(legend_x,ly,7,5,fill=1,stroke=0)
            set_fill(TEXT); c.drawString(legend_x+10,ly-1,"Ubicado")
            legend_x += 58
            set_stroke(BLUE); c.line(legend_x,ly+2,legend_x+15,ly+2)
            set_fill(BLUE); c.circle(legend_x+7.5,ly+2,2,fill=1,stroke=0)
            set_fill(TEXT); c.drawString(legend_x+20,ly-1,"Ingresos")

            y -= chart_h + 7

        # ---------- Construcción ----------
        page_header()
        meta_line()

        dev = _num(mt.get("dev_pzs"))
        muertos = _num(mt.get("muertos"))
        probador = _num(mt.get("probador"))
        cajas = _num(mt.get("cajas"))
        total_pzs = _num(mt.get("total_pzs") if mt.get("total_pzs") is not None else mt.get("ingresos"))
        acond = _num(mt.get("acondicionado"))
        ubicado = _num(mt.get("ubicado"))
        recorridos = _num(mt.get("recorridos"))
        meta_rec = _num(mt.get("meta_recorridos"))
        pending_prev = _num(mt.get("pendiente_anterior"))
        show_opening = period_type == "day" or "diaria" in str(report or "").lower()
        total_operation = dev + muertos + probador + cajas + (pending_prev if show_opening else 0)
        pend_acond = _num(mt.get("pendiente_acondicionar")) if mt.get("pendiente_acondicionar") is not None else max(total_pzs-acond,0)
        pend_ub = _num(mt.get("pendiente_ubicar")) if mt.get("pendiente_ubicar") is not None else max(total_pzs-ubicado,0)
        total_pending = pend_acond + pend_ub
        pct_ac = _num(mt.get("pct_acondicionado")) if mt.get("pct_acondicionado") is not None else (acond/total_pzs*100 if total_pzs else 0)
        pct_ub = _num(mt.get("pct_ubicado")) if mt.get("pct_ubicado") is not None else (ubicado/total_pzs*100 if total_pzs else 0)
        pct_rec = _num(mt.get("pct_recorridos")) if mt.get("pct_recorridos") is not None else (recorridos/meta_rec*100 if meta_rec else 0)

        card_row([
            ("Total operación", n(total_operation), "Piezas", "#ECFDF5", GREEN_DARK),
            ("Total pendientes", n(total_pending), "Acondicionar + ubicar", "#FFF2E8", ORANGE_DARK),
            ("Total general · Total Pzs", n(total_pzs), "Piezas", "#EAF3FF", NAVY),
            ("Recorridos realizados", f"{n(recorridos)} / {n(meta_rec)}", f"{pc(pct_rec)} cumplimiento", "#F3EAFF", PURPLE),
            ("% Acondicionado", pc(pct_ac), f"{n(acond)} piezas", "#F3EAFF", PURPLE),
            ("% Ubicado", pc(pct_ub), f"{n(ubicado)} piezas", "#F3EAFF", PURPLE),
        ])

        draw_summary_matrix(show_opening=show_opening)

        # Igual que V240: en Día no hay recuperación por tienda y nunca se
        # imprime el gráfico histórico "Devolución y recuperación".
        draw_recovery_table()
        draw_operational_detail()
        draw_combo_chart()

        c.save()
        pdf = bio.getvalue()
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError("El generador V272 no produjo un PDF válido")
        return pdf

    def builder(data: dict, report: str, scope: str = "Compañía") -> bytes:
        if _is_center_report(report):
            return _build_center_pdf(data, report, scope)
        return previous_builder(data, report, scope)

    m._build_operations_pdf = builder
    m._V272_CENTER_PDF_PARITY = True
    print("[V272] PDF Centro Operativo alineado 1:1 con la vista consultada; gráfico operativo compacto.", flush=True)
