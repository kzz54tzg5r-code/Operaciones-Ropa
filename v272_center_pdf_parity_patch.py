"""V272.2 · PDF Centro Operativo fiel a la vista consultada.

Objetivo:
- El PDF de Centro Operativo usa exactamente el mismo alcance/periodo que la vista.
- Replica las cuatro tarjetas (Ingresado/En proceso/En piso/Recorridos),
  el detalle con 15 columnas, las tablas por periodo y el gráfico.
- Elimina del PDF el gráfico heredado "Devolución y recuperación", ya retirado
  de la pantalla por V240.
- Día, semana y mes incluyen la tabla de recuperación por tienda.
- No altera cálculos, datos, filtros, roles, permisos ni exportación Excel.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
from reportlab.lib.utils import ImageReader
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

        # La impresión refleja el mismo tope de 100% por tienda de las
        # tarjetas web; las filas del detalle conservan captura real.
        from v375_center_card_metrics import center_card_metrics
        mt = dict(data.get("center_card_metrics") or (
            center_card_metrics(data) if data.get("stores") else data.get("metrics") or {}
        ))
        project_stores, recovery = m._operations_export_sections(data)
        report_name = str(report or "").lower()
        fallback_period = ("week" if "semanal" in report_name else
                           "day" if "diaria" in report_name or "día" in report_name else
                           "month" if "mensual" in report_name else "month")
        period_type = str(data.get("period_type") or fallback_period).lower()
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
            amount = _num(v) / 1000.0
            return f"${amount:,.1f} mil" if amount else "$0 mil"

        def safe(v):
            if v is None:
                return "—"
            return str(v)

        def fit(text, max_chars):
            s = safe(text)
            return s if len(s) <= max_chars else s[:max(1, max_chars - 1)] + "…"

        def fitted_cell(value, width, base=8, font="Helvetica"):
            s=safe(value)
            size=base
            while size>=6.0 and c.stringWidth(s,font,size)>width-5:
                size-=.35
            if c.stringWidth(s,font,size)<=width-5:
                return s,size
            while s and c.stringWidth(s+"…",font,6.0)>width-5:
                s=s[:-1]
            return s+"…",6.0

        def set_fill(hex_color):
            c.setFillColor(colors.HexColor(hex_color))

        def set_stroke(hex_color):
            c.setStrokeColor(colors.HexColor(hex_color))

        def draw_header_cell(x, width, top_y, header_h, text, font_size=5.0, align="center"):
            """Encabezado compacto: usa 1-2 líneas para aprovechar alto, no ancho."""
            parts = [p.strip() for p in str(text or "").split("\n") if p.strip()]
            if not parts:
                parts = [""]
            c.setFont("Helvetica-Bold", font_size)
            line_gap = font_size + 1.2
            total_h = line_gap * len(parts)
            first_y = top_y - (header_h - total_h)/2 - font_size + 1.2
            for j, part in enumerate(parts):
                yy = first_y - j*line_gap
                if align == "left":
                    c.drawString(x + 3, yy, part)
                else:
                    c.drawCentredString(x + width/2, yy, part)

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

            # V403: letras de Price Shoes en blanco sobre azul sin recuadro.
            try:
                from v403_white_price_logo_pdf import draw_price_white
                draw_price_white(c, W-M-100, H-84, 92, 51)
            except Exception as exc:
                print(f"[PDF] Error logo blanco: {exc}", flush=True)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 9)
                c.drawRightString(W-M-15, H-57, "PRICE SHOES")

            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8.4)
            c.drawRightString(W-M-109, H-53, "Operaciones Ropa")
            c.setFont("Helvetica", 6.8)
            title = f"Centro Operativo · {mode_label}"
            if suffix:
                title += f" · {suffix}"
            c.drawRightString(W-M-109, H-69, title)
            y = H - 102

        def new_page(suffix=""):
            c.showPage()
            page_header(suffix)

        def ensure(height_needed, suffix=""):
            nonlocal y
            if y - height_needed < 24:
                new_page(suffix)

        def section(title, size=12.0):
            nonlocal y
            ensure(18)
            set_fill(TEXT)
            c.setFont("Helvetica-Bold", size)
            c.drawString(M, y, title)
            y -= 18

        def meta_line():
            nonlocal y
            set_fill(MUTED)
            c.setFont("Helvetica", 9.0)
            project_count = int(data.get("v151_project_store_count") or len(project_stores) or 0)
            left = f"Periodo: {period_label()}   ·   Tienda: {scope}"
            if project_count:
                left += f"   ·   Alcance KPI: {project_count} tiendas Proyecto"
            c.drawString(M, y, left)
            y -= 15

        def card_row(items):
            """Cuatro tarjetas del mismo contenido y orden que la pantalla web."""
            nonlocal y
            gap = 7
            card_w = (W - 2*M - 3*gap) / 4
            card_h = 115
            ensure(card_h + 10)
            for idx, item in enumerate(items):
                label, desc, metric, val, percentage, pending, tone = item
                x = M + idx*(card_w+gap)
                yy = y-card_h
                set_fill("#FFFFFF")
                set_stroke(LINE)
                c.roundRect(x, yy, card_w, card_h, 7, fill=1, stroke=1)
                set_fill(tone)
                c.roundRect(x, yy+card_h-3, card_w, 3, 1.2, fill=1, stroke=0)
                set_fill(TEXT)
                c.setFont("Helvetica-Bold", 11.4)
                c.drawString(x+11, yy+card_h-20, label)
                set_fill(MUTED)
                c.setFont("Helvetica", 8.0)
                c.drawString(x+11, yy+card_h-33, fit(desc, 33))
                set_fill("#F2F7FE")
                c.roundRect(x+7, yy+32, card_w-14, 43, 5, fill=1, stroke=0)
                set_fill(TEXT)
                c.setFont("Helvetica-Bold", 9.0)
                c.drawString(x+13, yy+61, metric)
                set_fill(tone)
                c.setFont("Helvetica-Bold", 20.0)
                c.drawString(x+13, yy+42, val)
                if percentage:
                    set_fill(TEXT)
                    c.setFont("Helvetica-Bold", 9.0)
                    c.drawString(x+13, yy+25, percentage)
                    set_fill(MUTED)
                    c.setFont("Helvetica", 7.0)
                    c.drawString(x+48, yy+25, "avance / meta")
                    set_fill("#E3EAF3")
                    c.roundRect(x+12, yy+14, card_w-24, 4.5, 2, fill=1, stroke=0)
                    try:
                        fraction=max(0.0,min(100.0,float(percentage.replace("%",""))))/100.0
                    except Exception:
                        fraction=0.0
                    if fraction:
                        set_fill(tone)
                        c.roundRect(x+12, yy+14, (card_w-24)*fraction, 4.5, 2, fill=1, stroke=0)
                if pending:
                    set_fill(ORANGE_DARK)
                    c.setFont("Helvetica-Bold", 7.7)
                    c.drawString(x+12, yy+5.5, fit(pending, 35))
            y -= card_h + 10

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

            headers = ["Cat.", "Indicador", "Valor /\nPzs", "%", "Meta", "Total"]
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
            head_h = 22
            total_rows = sum(len(g["rows"]) for g in groups)
            needed = head_h + total_rows*row_h + 8
            ensure(needed, "Resumen")

            # Header.
            set_fill(BLUE_DARK)
            c.roundRect(M, y-head_h+2, total_w, head_h, 5, fill=1, stroke=0)
            c.setFillColor(colors.white)
            for i, h in enumerate(headers):
                draw_header_cell(
                    xs[i],
                    total_w*fracs[i],
                    y,
                    head_h,
                    h,
                    font_size=5.7,
                    align="left" if i < 2 else "center",
                )
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
            # Recuperación por tienda también forma parte del reporte diario.
            rows = sorted(
                list(recovery or []),
                key=lambda r: (-_num(r.get("conversion_pct")), -_num(r.get("recovery_pct")), str(r.get("store") or "")),
            )
            if not rows:
                return

            section("Recuperación por tienda · importes en miles de pesos")
            # V272.2: abreviaturas + 2 líneas; el encabezado gana alto y
            # cada columna necesita menos ancho horizontal.
            headers = [
                "#", "Tienda", "Dev\nPzs", "Pzas\nrecup.", "Conv.\n%",
                "Valor\nDev. mil", "Recup.\n$ mil", "Recup.\n%", "Pend.\nPzs", "Pend.\n$ mil"
            ]
            fracs = [.04,.18,.075,.085,.075,.13,.13,.075,.08,.13]
            total_w = W - 2*M
            xs = [M]
            acc = M
            for frac in fracs[:-1]:
                acc += total_w*frac
                xs.append(acc)
            # 17 filas comerciales deben caber con cuatro KPI en primera hoja.
            row_h = 15.2
            head_h = 29

            def head():
                nonlocal y
                set_fill(BLUE_DARK)
                c.roundRect(M, y-head_h+2, total_w, head_h, 4, fill=1, stroke=0)
                c.setFillColor(colors.white)
                for i, h in enumerate(headers):
                    draw_header_cell(
                        xs[i], total_w*fracs[i], y, head_h, h,
                        font_size=6.6,
                        align="left" if i == 1 else "center",
                    )
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
                    font="Helvetica-Bold" if i in (0,1) else "Helvetica"
                    label,size=fitted_cell(val,total_w*fracs[i],8.1,font)
                    c.setFont(font,size)
                    if i==1:
                        c.drawString(xs[i]+3,y-11.6,label)
                    else:
                        c.drawCentredString(xs[i]+total_w*fracs[i]/2,y-11.6,label)
                y -= row_h
            y -= 6

        def draw_operational_detail():
            nonlocal y
            rows = list(project_stores or [])
            if not rows:
                return
            # Mismo ranking que la tabla visible: mayor Total pzs primero.
            rows.sort(key=lambda r: (-_num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")), str(r.get("store") or "")))
            section(f"Detalle operativo · {period_label()}")
            headers = [
                "Rank.", "Tienda", "Dev\npzs", "Muertos", "Probador", "Cajas",
                "Pend.\nant.", "Total\npzs", "Recorr.\nrealiz.", "Acondi-\ncionado",
                "Ubicado", "% Acondi-\ncionado", "%\nUbicado",
                "Pendiente\nacond.", "Pendiente\nubicar"
            ]
            fracs = [.04,.12,.055,.057,.059,.05,.062,.063,.069,.076,.059,.068,.059,.085,.078]
            total_w = W - 2*M
            # Normaliza fracciones para ocupar el ancho exacto de la página.
            norm = sum(fracs)
            widths = [total_w*x/norm for x in fracs]
            xs = [M]
            for width in widths[:-1]:
                xs.append(xs[-1]+width)
            row_h = 19.4
            head_h = 33

            def head():
                nonlocal y
                set_fill(BLUE_DARK)
                c.roundRect(M, y-head_h+2, total_w, head_h, 4, fill=1, stroke=0)
                c.setFillColor(colors.white)
                for i, h in enumerate(headers):
                    draw_header_cell(xs[i], widths[i], y, head_h, h,
                                     font_size=6.3,
                                     align="left" if i == 1 else "center")
                y -= head_h

            ensure(head_h + min(len(rows), 18)*row_h + 12, "Detalle operativo")
            head()
            for idx,r in enumerate(rows, start=1):
                if y-row_h < 26:
                    new_page("Detalle operativo")
                    head()
                total = r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")
                total_num=_num(total)
                pa = (_num(r.get("pct_acondicionado")) if r.get("pct_acondicionado") is not None
                      else _num(r.get("acondicionado"))/total_num*100 if total_num else 0)
                pu = (_num(r.get("pct_ubicado")) if r.get("pct_ubicado") is not None
                      else _num(r.get("ubicado"))/total_num*100 if total_num else 0)
                set_fill(PROJECT if r.get("is_project") else ("#FFFFFF" if idx%2 else "#EEF4FB"))
                c.rect(M, y-row_h+2, total_w, row_h, fill=1, stroke=0)
                if r.get("is_project"):
                    set_fill(BLUE)
                    c.rect(M, y-row_h+2, 2.5, row_h, fill=1, stroke=0)
                values = [
                    f"#{idx}", r.get("store"), n(r.get("dev_pzs")),
                    n(r.get("muertos")), n(r.get("probador")), n(r.get("cajas")),
                    n(r.get("pendiente_anterior")), n(total),
                    n(r.get("recorridos")), n(r.get("acondicionado")),
                    n(r.get("ubicado")), pc(pa), pc(pu),
                    n(r.get("pendiente_acondicionar")), n(r.get("pendiente_ubicar"))
                ]
                for i,val in enumerate(values):
                    tone = TEXT
                    if i in (11,12):
                        tone = GREEN_DARK if _num(val[:-1]) >= 80 else "#DC2626"
                    elif i in (2,3,4,5,6,7,8,9,10) and _num(val)==0:
                        tone = "#DC2626"
                    set_fill(tone)
                    font="Helvetica-Bold" if i in (0,1,7,11,12) else "Helvetica"
                    text_value,size=fitted_cell(val,widths[i],7.6,font)
                    c.setFont(font,size)
                    if i==1:
                        c.drawString(xs[i]+2.5, y-13.3, text_value)
                    else:
                        c.drawCentredString(xs[i]+widths[i]/2, y-13.3, text_value)
                y -= row_h
            y -= 7

        def draw_combo_chart():
            nonlocal y
            rows = list(data.get("stores") or project_stores or [])
            rows = [r for r in rows if _num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")) or _num(r.get("acondicionado")) or _num(r.get("ubicado"))]
            if not rows:
                return

            rec_lookup = {str(r.get("store") or ""): _num(r.get("conversion_pct")) for r in recovery or []}
            rows.sort(key=lambda r: (-rec_lookup.get(str(r.get("store") or ""), 0), str(r.get("store") or "")))

            # V272.1: el gráfico se dimensiona según las tiendas con información.
            # Con 1-5 tiendas no se estira de lado a lado ni deja barras aisladas.
            count = len(rows)
            # Primero evaluar el alto disponible de la página ACTUAL.
            # El gráfico usa el espacio restante tras Detalle Operativo;
            # no saltar a una nueva hoja basándose en una altura fija.
            if y < 246:
                new_page("Gráfico operativo")
            chart_h = max(184, min(456, y - 62))
            section(f"Ingreso vs Acondicionado vs Ubicado · {scope} · {period_label()}")

            available_w = W - 2*M - 52
            desired_w = max(300, min(available_w, 105*count + 100))
            x0 = M + 40 + max(0, (available_w - desired_w)/2)
            x1 = x0 + desired_w
            base = y - chart_h + 24
            top = y - 14
            plot_h = max(60, top - base)
            plot_w = x1 - x0
            maxv = max([_num(r.get(k)) for r in rows for k in ("total_pzs","ingresos","acondicionado","ubicado")] + [1])
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
                c.setFont("Helvetica", 7.3)
                c.drawRightString(x0-6, gy-1.5, n(maxv*q/4))

            points = []
            for i, r in enumerate(rows):
                cx = x0 + group_w*(i+.5)
                acond = _num(r.get("acondicionado"))
                ubic = _num(r.get("ubicado"))
                ingreso = _num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"))
                ah = plot_h*acond/maxv
                uh = plot_h*ubic/maxv

                # Barras compactas y etiquetas visibles.
                set_fill(NAVY)
                c.roundRect(cx-bar_w-2, base, bar_w, max(1,ah), 1.5, fill=1, stroke=0)
                set_fill(PINK)
                c.roundRect(cx+2, base, bar_w, max(1,uh), 1.5, fill=1, stroke=0)

                label_fs = 8.2 if count <= 6 else 7.0
                value_fs = 7.7 if count <= 6 else 6.9

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
            set_fill(TEXT); c.setFont("Helvetica",8.0); c.drawString(legend_x+10,ly-1,"Acondicionado")
            legend_x += 103
            set_fill(PINK); c.rect(legend_x,ly,7,5,fill=1,stroke=0)
            set_fill(TEXT); c.drawString(legend_x+10,ly-1,"Ubicado")
            legend_x += 75
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
            ("Ingresado", "Mercancía ingresada en el periodo", "Ingresos",
             n(total_pzs), None, None, "#00999F"),
            ("En proceso", "Acondicionamiento de mercancía", "Acondicionado",
             n(acond), pc(pct_ac), f"{n(pend_acond)} pzas por acondicionar", PURPLE),
            ("En piso", "Mercancía ubicada en tienda", "Ubicado",
             n(ubicado), pc(pct_ub), f"{n(pend_ub)} pzas por ubicar", BLUE),
            ("Recorridos", "Realizados frente a la meta", "Recorridos",
             f"{n(recorridos)} / {n(meta_rec)}", pc(pct_rec), None, ORANGE),
        ])

        # En la pantalla no existe una matriz adicional entre las tarjetas y
        # el reporte expandido. La impresión respeta esa misma jerarquía.
        section("Reporte completo por tienda · tablas y gráficos")

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
    print("[V272] PDF Centro Operativo alineado 1:1; encabezados compactos de 2 líneas y gráfico operativo compacto.", flush=True)
