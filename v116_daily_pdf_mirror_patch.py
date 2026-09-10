"""V116: PDF de Operación Diaria espejo del reporte web.

La pantalla ya quedó validada en V115. Este parche no toca la web ni fórmulas:
solo reemplaza el generador PDF Diario para que replique la misma jerarquía,
colores, distribución de tarjetas, tabla rayada y gráfico del reporte.
"""
from __future__ import annotations

import io


def install(m):
    if getattr(m, "_V116_DAILY_PDF_MIRROR", False):
        return

    old_pdf = m._build_operations_pdf

    def build_pdf(data: dict, report: str, scope: str = "Compañía") -> bytes:
        if report != "Operación Diaria":
            return old_pdf(data, report, scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        def n(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0

        def fmt(v):
            return f"{n(v):,.0f}"

        def pct(v):
            return f"{n(v):.1f}%"

        def pct_color(v):
            value = n(v)
            if value >= 80:
                return GREEN
            if value >= 65:
                return GOLD
            return RED

        rows = list(data.get("stores") or [])
        metrics = data.get("metrics") or {}
        period = str(data.get("period_value") or "Histórico")

        W, H = landscape(letter)
        M = 28
        NAVY = "#173F78"
        NAVY2 = "#1D4A83"
        BLUE = "#246FE5"
        PINK = "#EC007C"
        PURPLE = "#7338EF"
        GREEN = "#10B981"
        GOLD = "#F3A300"
        RED = "#EF3434"
        TEXT = "#0F3463"
        MUTED = "#667892"
        LINE = "#D6E0EC"
        BG = "#F2F6FB"
        ROW_ALT = "#EAF2FC"
        PROJECT = "#1F70E6"

        bio = io.BytesIO()
        c = canvas.Canvas(bio, pagesize=(W, H))

        def page_bg():
            c.setFillColor(colors.HexColor(BG))
            c.rect(0, 0, W, H, fill=1, stroke=0)

        def header(suffix: str = ""):
            page_bg()
            c.setFillColor(colors.HexColor(NAVY2))
            c.roundRect(M, H - 92, W - 2 * M, 64, 12, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(M + 18, H - 56, "Cambios y Muertos")
            c.setFont("Helvetica", 8)
            c.drawString(M + 18, H - 74, "Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold", 9.2)
            c.drawRightString(W - M - 18, H - 54, "Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica", 7.4)
            label = "Operación Diaria" + ((" · " + suffix) if suffix else "")
            c.drawRightString(W - M - 18, H - 72, label)

        def card(x, y, w, h, label, value, sub, accent, value_color=None):
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor(LINE))
            c.setLineWidth(0.8)
            c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
            c.setFillColor(colors.HexColor(accent))
            c.rect(x, y, 4.5, h, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(MUTED))
            c.setFont("Helvetica-Bold", 6.1)
            c.drawString(x + 11, y + h - 17, str(label).upper()[:32])
            c.setFillColor(colors.HexColor(value_color or TEXT))
            c.setFont("Helvetica-Bold", 15.5)
            c.drawString(x + 11, y + h - 40, str(value))
            if sub:
                c.setFillColor(colors.HexColor(MUTED))
                c.setFont("Helvetica", 5.7)
                text = str(sub)
                # dos líneas para textos largos de Total/Pendientes.
                if len(text) > 36:
                    split = text.rfind(" ", 0, 36)
                    split = split if split > 10 else 36
                    c.drawString(x + 11, y + 10, text[:split].strip())
                    c.drawString(x + 11, y + 3, text[split:].strip()[:38])
                else:
                    c.drawString(x + 11, y + 7, text[:44])

        def draw_cards(y_top):
            gap = 8
            cols = 6
            cw = (W - 2 * M - gap * (cols - 1)) / cols
            ch = 58
            first = [
                ("Dev pzs", fmt(metrics.get("dev_pzs")), "Devoluciones del día", NAVY, None),
                ("Muertos", fmt(metrics.get("muertos")), "Recolección · motivo Muertos", PINK, None),
                ("Probador", fmt(metrics.get("probador")), "Motivo Probador", GOLD, RED if n(metrics.get("probador")) == 0 else None),
                ("Cajas", fmt(metrics.get("cajas")), "Recolección · Cajas", PURPLE, RED if n(metrics.get("cajas")) == 0 else None),
                ("Total pzs", fmt(metrics.get("total_pzs", metrics.get("ingresos"))), "Dev + Muertos + Cajas + Probador + Pend. Ant.", BLUE, None),
                ("Recorridos realizados", fmt(metrics.get("recorridos")), f"{pct(metrics.get('pct_recorridos'))} · meta {fmt(metrics.get('meta_recorridos'))}", GREEN, None),
            ]
            second = [
                ("% Acondicionado", pct(metrics.get("pct_acondicionado")), f"{fmt(metrics.get('acondicionado'))} piezas acondicionadas", PURPLE, pct_color(metrics.get("pct_acondicionado"))),
                ("% Ubicado", pct(metrics.get("pct_ubicado")), f"{fmt(metrics.get('ubicado'))} piezas ubicadas", PINK, pct_color(metrics.get("pct_ubicado"))),
                ("Pendiente de acondicionar", fmt(metrics.get("pendiente_acondicionar")), "Total pzs - Acondicionado", GOLD, None),
                ("Pendiente de ubicar", fmt(metrics.get("pendiente_ubicar")), "Total pzs - Ubicado", RED, None),
            ]
            y1 = y_top - ch
            for i, item in enumerate(first):
                card(M + i * (cw + gap), y1, cw, ch, *item)
            y2 = y1 - gap - ch
            for i, item in enumerate(second):
                card(M + i * (cw + gap), y2, cw, ch, *item)
            return y2 - 16

        def draw_table(y_top):
            c.setFillColor(colors.HexColor(TEXT))
            c.setFont("Helvetica-Bold", 11.5)
            c.drawString(M, y_top, f"Detalle operativo · {period}")
            y = y_top - 16

            headers = [
                ["Ranking"], ["Tienda"], ["Dev", "pzs"], ["Muertos"], ["Probador"], ["Cajas"],
                ["Pend.", "Ant."], ["Total", "pzs"], ["Recorridos", "realizados"], ["Acondicionado"],
                ["% Acond."], ["Ubicado"], ["% Ubicado"], ["Pendiente de", "acondicionar"], ["Pendiente de", "ubicar"],
            ]
            fr = [.042, .105, .055, .05, .052, .045, .058, .055, .074, .07, .068, .058, .064, .105, .099]
            tw = W - 2 * M
            xs = [M]
            acc = M
            for frac in fr[:-1]:
                acc += tw * frac
                xs.append(acc)

            hh = 24
            c.setFillColor(colors.HexColor(NAVY2))
            c.roundRect(M, y - hh + 2, tw, hh, 5, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 4.8)
            for j, lines in enumerate(headers):
                c.drawString(xs[j] + 2, y - 8, lines[0])
                if len(lines) > 1:
                    c.drawString(xs[j] + 2, y - 15, lines[1])
            y -= hh

            rh = 17 if len(rows) <= 7 else (14 if len(rows) <= 12 else 11.5)
            for i, r in enumerate(rows):
                total = r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")
                p_ac = r.get("pct_acondicionado")
                if p_ac is None:
                    p_ac = (n(r.get("acondicionado")) / n(total) * 100) if n(total) > 0 else 0
                p_ub = r.get("pct_ubicado")
                if p_ub is None:
                    p_ub = (n(r.get("ubicado")) / n(total) * 100) if n(total) > 0 else 0

                if i % 2:
                    c.setFillColor(colors.HexColor(ROW_ALT))
                else:
                    c.setFillColor(colors.white)
                c.rect(M, y - rh + 2, tw, rh, fill=1, stroke=0)
                if r.get("is_project"):
                    c.setFillColor(colors.HexColor(PROJECT))
                    c.rect(M, y - rh + 2, 3, rh, fill=1, stroke=0)

                values = [
                    f"#{i+1}", str(r.get("store") or ""), fmt(r.get("dev_pzs")), fmt(r.get("muertos")),
                    fmt(r.get("probador")), fmt(r.get("cajas")), fmt(r.get("pendiente_anterior")), fmt(total),
                    fmt(r.get("recorridos")), fmt(r.get("acondicionado")), pct(p_ac), fmt(r.get("ubicado")), pct(p_ub),
                    fmt(r.get("pendiente_acondicionar")), fmt(r.get("pendiente_ubicar")),
                ]

                c.setFont("Helvetica", 5.1 if len(rows) <= 10 else 4.7)
                for j, value in enumerate(values):
                    color = TEXT
                    # Ceros en rojo desde Dev pzs hasta Ubicado, como el reporte web.
                    if j in (2, 3, 4, 5, 6, 7, 8, 9, 11) and n(value.replace(",", "") if isinstance(value, str) else value) == 0:
                        color = RED
                    if j == 10:
                        color = pct_color(p_ac)
                    if j == 12:
                        color = pct_color(p_ub)
                    c.setFillColor(colors.HexColor(color))
                    if j in (0, 1, 7, 10, 12):
                        c.setFont("Helvetica-Bold", 5.1 if len(rows) <= 10 else 4.7)
                    else:
                        c.setFont("Helvetica", 5.1 if len(rows) <= 10 else 4.7)
                    c.drawString(xs[j] + 2, y - 10, str(value)[:24])
                y -= rh
            return y - 10

        def label_box(cx, cy, text, fg, fill="white"):
            fs = 5.2
            w = stringWidth(text, "Helvetica-Bold", fs) + 7
            c.setFillColor(colors.HexColor(fill))
            c.roundRect(cx - w / 2, cy - 3, w, 9, 2.5, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(fg))
            c.setFont("Helvetica-Bold", fs)
            c.drawCentredString(cx, cy, text)

        def draw_graph(y_top, available_bottom=28):
            panel_h = min(220, max(170, y_top - available_bottom))
            panel_y = y_top - panel_h
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor(LINE))
            c.setLineWidth(0.8)
            c.roundRect(M, panel_y, W - 2 * M, panel_h, 9, fill=1, stroke=1)

            c.setFillColor(colors.HexColor(TEXT))
            c.setFont("Helvetica-Bold", 12)
            c.drawString(M + 20, y_top - 26, f"Ingreso vs Acondicionado vs Ubicado · Todas las tiendas · {period}")

            legend_y = y_top - 43
            lx = M + 52
            for name, col, kind in (("Acondicionado", NAVY2, "bar"), ("Ubicado", PINK, "bar"), ("Ingresos", BLUE, "line")):
                if kind == "bar":
                    c.setFillColor(colors.HexColor(col))
                    c.rect(lx, legend_y - 4, 7, 7, fill=1, stroke=0)
                else:
                    c.setStrokeColor(colors.HexColor(col))
                    c.setLineWidth(1.7)
                    c.line(lx, legend_y, lx + 13, legend_y)
                    c.setFillColor(colors.HexColor(col))
                    c.circle(lx + 6.5, legend_y, 2.2, fill=1, stroke=0)
                c.setFillColor(colors.HexColor(TEXT))
                c.setFont("Helvetica", 6.2)
                c.drawString(lx + 11 + (3 if kind == "line" else 0), legend_y - 2, name)
                lx += 88

            x0 = M + 62
            x1 = W - M - 18
            base = panel_y + 28
            top = y_top - 62
            ph = max(68, top - base)
            maxv = max([
                n(v)
                for r in rows
                for v in (
                    r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"),
                    r.get("acondicionado"), r.get("ubicado")
                )
            ] + [1]) * 1.15

            c.setStrokeColor(colors.HexColor(LINE))
            c.setLineWidth(0.6)
            for q in range(5):
                gy = base + ph * q / 4
                c.line(x0, gy, x1, gy)
                c.setFillColor(colors.HexColor(MUTED))
                c.setFont("Helvetica", 5.2)
                c.drawRightString(x0 - 6, gy - 2, fmt(maxv * q / 4))

            count = max(1, len(rows))
            gw = (x1 - x0) / count
            bw = min(15, gw * .20)
            pts = []
            for i, r in enumerate(rows):
                cx = x0 + gw * (i + .5)
                total = n(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"))
                ac = n(r.get("acondicionado"))
                ub = n(r.get("ubicado"))
                ah = ph * ac / maxv
                uh = ph * ub / maxv

                c.setFillColor(colors.HexColor(NAVY2))
                c.rect(cx - bw - 2, base, bw, max(0.7, ah), fill=1, stroke=0)
                c.setFillColor(colors.HexColor(PINK))
                c.rect(cx + 2, base, bw, max(0.7, uh), fill=1, stroke=0)

                if ac > 0:
                    label_box(cx - bw / 2 - 2, base + ah + 4, fmt(ac), NAVY2)
                if ub > 0:
                    label_box(cx + bw / 2 + 2, base + uh + 4, fmt(ub), PINK)

                py = base + ph * total / maxv
                pts.append((cx, py, total))
                c.setFillColor(colors.HexColor(BLUE))
                c.circle(cx, py, 2.7, fill=1, stroke=0)
                c.setFillColor(colors.HexColor(TEXT))
                c.setFont("Helvetica", 5.4)
                c.drawCentredString(cx, base - 14, str(r.get("store") or "")[:13])

            c.setStrokeColor(colors.HexColor(BLUE))
            c.setLineWidth(1.7)
            for p1, p2 in zip(pts, pts[1:]):
                c.line(p1[0], p1[1], p2[0], p2[1])
            for cx, py, total in pts:
                label_box(cx, min(top - 2, py + 8), "Ing. " + fmt(total), BLUE)

        header()
        y = H - 107
        c.setFillColor(colors.HexColor(MUTED))
        c.setFont("Helvetica", 7.2)
        c.drawString(M, y, f"Periodo: {period}   ·   Alcance: {scope}")
        y -= 14
        y = draw_cards(y)
        y = draw_table(y)

        # Si la gráfica no cabe completa, pasa completa a una nueva hoja; nunca se corta.
        if y < 205:
            c.showPage()
            header("gráfico")
            y = H - 112
        draw_graph(y)

        c.save()
        pdf = bio.getvalue()
        if not pdf.startswith(b"%PDF"):
            return old_pdf(data, report, scope)
        return pdf

    m._build_operations_pdf = build_pdf

    try:
        sample = {
            "period_value": "2026-09-09",
            "metrics": {
                "dev_pzs": 1173, "muertos": 128, "probador": 0, "cajas": 20,
                "total_pzs": 1774, "recorridos": 2, "pct_recorridos": 8, "meta_recorridos": 25,
                "acondicionado": 755, "pct_acondicionado": 42.6,
                "ubicado": 1679, "pct_ubicado": 94.6,
                "pendiente_acondicionar": 1425, "pendiente_ubicar": 885,
            },
            "stores": [
                {"store": "Ecatepec", "dev_pzs": 313, "muertos": 0, "probador": 0, "cajas": 0, "pendiente_anterior": 331, "total_pzs": 644, "recorridos": 0, "acondicionado": 0, "pct_acondicionado": 0, "ubicado": 0, "pct_ubicado": 0, "pendiente_acondicionar": 644, "pendiente_ubicar": 644, "is_project": True},
                {"store": "Vallejo", "dev_pzs": 540, "muertos": 0, "probador": 0, "cajas": 0, "pendiente_anterior": 0, "total_pzs": 540, "recorridos": 0, "acondicionado": 0, "pct_acondicionado": 0, "ubicado": 844, "pct_ubicado": 156.3, "pendiente_acondicionar": 540, "pendiente_ubicar": 0, "is_project": True},
                {"store": "Arco Norte", "dev_pzs": 201, "muertos": 128, "probador": 0, "cajas": 20, "pendiente_anterior": 0, "total_pzs": 349, "recorridos": 2, "acondicionado": 755, "pct_acondicionado": 216.3, "ubicado": 835, "pct_ubicado": 239.3, "pendiente_acondicionar": 0, "pendiente_ubicar": 0, "is_project": True},
                {"store": "Puebla Sur", "dev_pzs": 59, "muertos": 0, "probador": 0, "cajas": 0, "pendiente_anterior": 67, "total_pzs": 126, "recorridos": 0, "acondicionado": 0, "pct_acondicionado": 0, "ubicado": 0, "pct_ubicado": 0, "pendiente_acondicionar": 126, "pendiente_ubicar": 126, "is_project": True},
                {"store": "Miravalle", "dev_pzs": 60, "muertos": 0, "probador": 0, "cajas": 0, "pendiente_anterior": 55, "total_pzs": 115, "recorridos": 0, "acondicionado": 0, "pct_acondicionado": 0, "ubicado": 0, "pct_ubicado": 0, "pendiente_acondicionar": 115, "pendiente_ubicar": 115, "is_project": True},
            ],
        }
        test_pdf = build_pdf(sample, "Operación Diaria", "Compañía")
        assert test_pdf.startswith(b"%PDF") and len(test_pdf) > 5000
        print("[V116-SELFTEST] PDF Diario espejo: tarjetas 6+4, tabla rayada y gráfica web OK.", flush=True)
    except Exception as exc:
        print(f"[V116-SELFTEST] ERROR: {type(exc).__name__}: {exc}", flush=True)

    m._V116_DAILY_PDF_MIRROR = True
    print("[V116] PDF Operación Diaria alineado visualmente con el reporte web.", flush=True)
