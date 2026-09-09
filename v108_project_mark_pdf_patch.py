"""V108: marca visualmente las tiendas Proyecto en la primera hoja del PDF.

Se aplica después de V107 y conserva íntegramente el PDF mixto ya validado.
Sobre la tabla "Recuperación por tienda" de la primera hoja:
- pinta la fila Proyecto con fondo azul tenue sólido;
- conserva y redibuja TODOS los datos de esa misma fila para que no desaparezcan;
- añade barra azul lateral y etiqueta "Proyecto" dentro de Tienda.

La exportación se sigue regenerando sin caché y no cambia cálculos ni datos.
"""
from __future__ import annotations

import io


def install(m):
    if getattr(m, "_V108_PROJECT_MARK_PDF", False):
        return

    old = m._build_operations_pdf

    def build(d: dict, report: str, scope: str = "Compañía") -> bytes:
        pdf = old(d, report, scope)
        if report not in ("Reporte Semanal", "Reporte Mensual"):
            return pdf

        stores = list(d.get("stores") or [])
        project_names = {
            str(r.get("store") or "").strip()
            for r in stores
            if r.get("is_project")
        }
        if not project_names:
            return pdf

        rec = list(d.get("recovery_by_store") or [])
        rec.sort(
            key=lambda r: (
                -float(r.get("conversion_pct") or 0),
                str(r.get("store") or ""),
            )
        )

        marked_indexes = [
            i for i, r in enumerate(rec[:17])
            if str(r.get("store") or "").strip() in project_names
        ]
        if not marked_indexes:
            return pdf

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import landscape, letter
            from reportlab.pdfgen import canvas
            from pypdf import PdfReader, PdfWriter

            LW, LH = landscape(letter)
            M = 26
            tw = LW - 2 * M
            BLUE = "#246FE5"
            FILL = "#DDEBFF"
            TXT = "#102A56"

            def num(v):
                try:
                    return float(v or 0)
                except Exception:
                    return 0.0

            def f(v):
                return f"{num(v):,.0f}"

            def pct(v):
                return f"{num(v):.1f}%"

            def money(v):
                return f"${num(v):,.0f}"

            # Coordenadas idénticas a V107: encabezado -> tarjetas -> título -> cabecera.
            y = LH - 106
            y -= 13
            # 7 KPIs en 5 columnas => 2 filas, alto 48, gap 7, +5 final.
            y -= 2 * (48 + 7) + 5
            # Título de sección.
            y -= 14
            # Cabecera de tabla.
            hh = 17
            rh = 8.5 if len(rec) >= 15 else 10
            y -= hh

            # Misma geometría de columnas que V107.
            fr = [.035, .13, .08, .09, .09, .12, .13, .09, .09, .105]
            xs = [M]
            acc = M
            for q in fr[:-1]:
                acc += tw * q
                xs.append(acc)

            overlay_buf = io.BytesIO()
            oc = canvas.Canvas(overlay_buf, pagesize=(LW, LH))

            for idx in marked_indexes:
                r = rec[idx]
                row_top = y - idx * rh
                row_bottom = row_top - rh + 1

                # Fondo azul tenue sólido: se vuelve a dibujar el contenido encima.
                oc.setFillColor(colors.HexColor(FILL))
                oc.rect(M, row_bottom, tw, rh - 1, fill=1, stroke=0)

                # Barra lateral de proyecto.
                oc.setFillColor(colors.HexColor(BLUE))
                oc.rect(M, row_bottom, 2.7, rh - 1, fill=1, stroke=0)

                vals = [
                    f"#{idx+1}",
                    str(r.get("store") or ""),
                    f(r.get("dev_pzs")),
                    f(r.get("converted_pieces")),
                    pct(r.get("conversion_pct")),
                    money(r.get("return_value")),
                    money(r.get("recovered_value")),
                    pct(r.get("recovery_pct")),
                    f(r.get("pending_pieces")),
                    money(r.get("pending_value")),
                ]

                # Redibujar todos los valores de la fila para que queden legibles.
                oc.setFillColor(colors.HexColor(TXT))
                oc.setFont("Helvetica", 4.35)
                baseline = row_top - 6.4
                for j, value in enumerate(vals):
                    if j == 1:
                        oc.setFont("Helvetica-Bold", 4.35)
                        oc.drawString(xs[j] + 2, baseline, str(value)[:18])
                        oc.setFillColor(colors.HexColor(BLUE))
                        oc.setFont("Helvetica-Bold", 3.7)
                        oc.drawRightString(xs[2] - 4, baseline, "Proyecto")
                        oc.setFillColor(colors.HexColor(TXT))
                        oc.setFont("Helvetica", 4.35)
                    else:
                        oc.drawString(xs[j] + 2, baseline, str(value)[:24])

            oc.save()
            overlay_buf.seek(0)

            reader = PdfReader(io.BytesIO(pdf))
            overlay_reader = PdfReader(overlay_buf)
            if not reader.pages or not overlay_reader.pages:
                return pdf

            reader.pages[0].merge_page(overlay_reader.pages[0])
            out = io.BytesIO()
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.write(out)
            result = out.getvalue()

            if not result.startswith(b"%PDF"):
                return pdf

            print(
                f"[V108-PDF] Proyecto resaltado con datos visibles: {len(marked_indexes)} tiendas · {report}",
                flush=True,
            )
            return result
        except Exception as exc:
            print(
                f"[V108-PDF] warning {type(exc).__name__}: {exc}",
                flush=True,
            )
            return pdf

    m._build_operations_pdf = build
    m._V108_PROJECT_MARK_PDF = True
    print(
        "[V108-PDF] Resaltado Proyecto con datos visibles activo en Recuperación por tienda.",
        flush=True,
    )
