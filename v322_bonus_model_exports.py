"""V322: exportación real XLSX y PDF de Modelos a Detalle en Bonos 1–6.
Sólo consulta los datos calculados por V313; no modifica fórmulas, cartera ni base de datos.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import re
import urllib.request
from urllib.error import URLError
from fastapi import HTTPException, Request
from fastapi.responses import Response

FIELDS = [
    ("Foto", "photo"),
    ("ID", "id_art"),
    ("Modelo", "model"),
    ("Catálogo", "catalog"),
    ("DDI inicial", "initial_ddi"),
    ("DDI actual", "current_ddi"),
    ("Reducción DDI (%)", "ddi_reduction_pct"),
    ("Existencia inicial", "initial_existence"),
    ("Existencia actual", "current_existence"),
    ("Inversión inicial ($)", "initial_investment"),
    ("Inversión actual ($)", "current_investment"),
    ("Reducción inversión (%)", "investment_reduction_pct"),
]
FIELDS_B2 = [
    ("Foto", "photo"),("ID", "id_art"),("Modelo", "model"),("Catálogo", "catalog"),
    ("Venta pzas 30 días", "sales_30"),("Última llegada", "last_arrival"),
    ("Días desde llegada", "arrival_age_days"),("DDI inicial", "initial_ddi"),
    ("Existencia inicial", "initial_existence"),("Inversión inicial ($)", "initial_investment"),
]
CATALOGS = ("Abrigador", "Licencias", "Básicos")
IMG_BASE = "http://static.priceshoes.com.mx/imgs/original/articulo/"

def install(m):
    if getattr(m, "_V322_BONUS_EXPORTS", False):
        return

    def fetch_image(product_id):
        product_id = str(product_id or "").strip()
        if not re.fullmatch(r"\d{1,15}", product_id):
            return None
        try:
            # El reporte web ya tiene un servicio de fotos autenticado, con
            # caché y validación de MIME; exportaciones deben usar el MISMO origen.
            shared = getattr(m, "_bonus_photo_fetch_v314", None)
            if shared:
                result = shared(product_id)
                if not result:
                    return None
                raw = result[0]
            else:
                req = urllib.request.Request(
                    IMG_BASE + product_id + ".jpg",
                    headers={"User-Agent": "OperacionesRopa/1.0",
                             "Accept": "image/jpeg,image/png,image/webp"}
                )
                with urllib.request.urlopen(req, timeout=5.0) as res:
                    raw = res.read(2_000_001)
            if len(raw) > 2_000_000:
                return None
            from PIL import Image as PILImage
            with PILImage.open(BytesIO(raw)) as im:
                im.thumbnail((150, 180))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                out = BytesIO()
                im.save(out, format="JPEG", quality=76, optimize=True)
                return out.getvalue()
        except (OSError, URLError, ValueError, TypeError):
            return None

    def fetch_images(rows):
        pictures = {}
        ids = {str(r.get("id_art") or "") for r in rows}
        ids = [i for i in ids if re.fullmatch(r"\d{1,15}", i)]
        if not ids:
            return pictures
        # Cota de concurrencia para no saturar el servicio ni el host de fotografías.
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="bono-foto") as pool:
            futures = {pool.submit(fetch_image, key):key for key in ids}
            for future in as_completed(futures):
                try:
                    value=future.result()
                    if value:
                        pictures[futures[future]]=value
                except Exception:
                    continue
        return pictures

    def cell_value(row, key):
        value = row.get(key)
        if value is None:
            return ""
        if key in ("id_art", "model", "catalog", "last_arrival"):
            return str(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return ""

    def excel(rows, store, month, catalog, pictures, fields=FIELDS):
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image as XLSImage
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        wb=Workbook()
        ws=wb.active
        ws.title="Modelos a Detalle"
        ws.merge_cells(f"A1:{get_column_letter(len(fields))}1")
        ws["A1"]="Operaciones Ropa — Bonos · Modelos a Detalle"
        ws["A1"].font=Font(size=16, bold=True, color="FFFFFF")
        ws["A1"].fill=PatternFill("solid",fgColor="123B73")
        ws.merge_cells(f"A2:{get_column_letter(len(fields))}2")
        ws["A2"]=f"Tienda: {store}  |  Periodo: {month}  |  Catálogo: {catalog}  |  Modelos: {len(rows)}"
        ws["A2"].font=Font(size=11, bold=True, color="123B73")
        ws.append([])
        for col,(label,_key) in enumerate(fields,1):
            c=ws.cell(4,col,label)
            c.font=Font(bold=True,color="FFFFFF")
            c.fill=PatternFill("solid",fgColor="1769E8")
            c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
        ws.row_dimensions[4].height=32
        for idx,row in enumerate(rows,5):
            ident=str(row.get("id_art") or "")
            photo=pictures.get(ident)
            ws.row_dimensions[idx].height=53
            if photo:
                try:
                    image=XLSImage(BytesIO(photo))
                    image.width=52;image.height=65
                    ws.add_image(image, f"A{idx}")
                except Exception:
                    ws.cell(idx,1,"Sin foto")
            else:
                ws.cell(idx,1,"Sin foto")
            for col,(_label,key) in enumerate(fields[1:],2):
                value=cell_value(row,key)
                c=ws.cell(idx,col,value)
                c.alignment=Alignment(vertical="center")
                if key=="id_art":
                    c.number_format="@"
                elif key in ("initial_investment","current_investment"):
                    c.number_format='"$"#,##0.00'
                elif key.endswith("_pct"):
                    c.number_format='0.0"%"'
                elif isinstance(value,float):
                    c.number_format='#,##0.00'
                if idx%2==0:
                    c.fill=PatternFill("solid",fgColor="F1F5FB")
        widths=([14,16,18,17,16,16,19,18,18,20,20,20] if fields is FIELDS else [14,16,18,20,22,20,20,17,21,23])
        for col,w in enumerate(widths,1):
            ws.column_dimensions[get_column_letter(col)].width=w
        ws.freeze_panes="C5"
        ws.auto_filter.ref=f"B4:{get_column_letter(len(fields))}{len(rows)+4}"
        ws.sheet_properties.pageSetUpPr.fitToPage=True
        ws.page_setup.orientation="landscape"
        ws.page_setup.paperSize=ws.PAPERSIZE_A3
        buf=BytesIO();wb.save(buf)
        return buf.getvalue()

    def pdf(rows, store, month, catalog, pictures, fields=FIELDS):
        """A3 apaisado: tabla completa al ancho útil, tipografía legible y fotos."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A3
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer,
            Image as PDFImage
        )
        from xml.sax.saxutils import escape as xml_escape

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=landscape(A3), rightMargin=16, leftMargin=16,
            topMargin=20, bottomMargin=21
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "BonusTitle", parent=styles["Heading2"],
            fontName="Helvetica-Bold", fontSize=15, leading=18,
            textColor=colors.HexColor("#123B73"), spaceAfter=5
        )
        label_style = ParagraphStyle(
            "BonusMeta", parent=styles["Normal"], fontSize=10.2,
            leading=13, textColor=colors.HexColor("#244B73")
        )
        heading_style = ParagraphStyle(
            "BonusTableHeading", fontName="Helvetica-Bold",
            fontSize=8.1, leading=9.7, textColor=colors.white,
            alignment=TA_CENTER
        )
        story = [
            Paragraph("Operaciones Ropa — Bonos · Modelos a Detalle", title_style),
            Paragraph(
                f"Tienda: {xml_escape(str(store))}  |  Periodo: {xml_escape(str(month))}"
                f"  |  Catálogo: {xml_escape(str(catalog))}  |  Modelos: {len(rows)}",
                label_style
            ),
            Spacer(1, 10),
        ]
        # Distribución proporcional al ANCHO DISPONIBLE, sin dejar la cuarta
        # parte de la hoja en blanco como sucedía con anchos fijos.
        weights = (
            [57, 65, 76, 76, 76, 76, 104, 80, 80, 102, 102, 107]
            if fields is FIELDS else
            [59, 68, 77, 76, 98, 93, 82, 79, 80, 108]
        )
        total = sum(weights)
        widths = [doc.width * weight / total for weight in weights]
        data = [[Paragraph(xml_escape(label), heading_style) for label, _ in fields]]
        for row in rows:
            ident = str(row.get("id_art") or "")
            photo = pictures.get(ident)
            picture = "—"
            if photo:
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(BytesIO(photo)) as original:
                        w, h = original.size
                    factor = min(44/max(1,w), 47/max(1,h))
                    picture = PDFImage(
                        BytesIO(photo), width=max(1,w*factor), height=max(1,h*factor)
                    )
                except (OSError, ValueError):
                    pass
            line = [picture]
            for _label, key in fields[1:]:
                value = cell_value(row, key)
                if isinstance(value, float):
                    if key.endswith("_pct"):
                        line.append(format(value,",.1f") + "%")
                    elif key in ("initial_investment", "current_investment"):
                        line.append("$" + format(value,",.2f"))
                    else:
                        line.append(format(value,",.1f"))
                else:
                    line.append(str(value)[:28])
            data.append(line)
        table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#123B73")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTSIZE", (0,1), (-1,-1), 8.4),
            ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("ALIGN", (2,1), (3,-1), "LEFT"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,0), 9),
            ("BOTTOMPADDING", (0,0), (-1,0), 9),
            ("TOPPADDING", (0,1), (-1,-1), 5),
            ("BOTTOMPADDING", (0,1), (-1,-1), 5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#EFF4FA")]),
            ("LINEBELOW", (0,0), (-1,-1), .3, colors.HexColor("#D2DFEC")),
        ]))
        story.append(table)
        def footer(canvas, document):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#66798D"))
            canvas.drawRightString(
                landscape(A3)[0] - 17, 11,
                f"Operaciones Ropa · Página {document.page}"
            )
            canvas.restoreState()
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        return buf.getvalue()

    @m.app.get("/api/bonuses/models-export")
    def export_bonus_models(request:Request,month:str="",store:str="",bonus:int=1,catalog:str="Abrigador",format:str="xlsx",photos:bool=True):
        m.require_user(request)
        if bonus not in range(1,7) or catalog not in (*CATALOGS,"Todos") or format not in ("xlsx","pdf"):
            raise HTTPException(400,"Parámetros de exportación inválidos")
        if bonus == 2:
            cohort=getattr(m, "_v327_bonus2_payload", None)
            if not cohort:
                raise HTTPException(503,"La cartera específica del Bono 2 aún no está habilitada")
            data=cohort(request=request,month=month,store=store)
            if (data.get("b2_status") or "") == "pending":
                raise HTTPException(409,"Bono 2 está preparando los modelos. Vuelve a intentar cuando termine la consulta.")
            if data.get("b2_status")=="error":
                raise HTTPException(503,"No fue posible validar las ventas y la última llegada del corte")
        else:
            handler=next((r.endpoint for r in m.app.routes if getattr(r,"path",None)=="/api/bonuses-v313"),None)
            if not handler:
                raise HTTPException(503,"Módulo de Bonos no disponible")
            data=handler(request=request,month=month,store=store,bonus=bonus)
        selected_store=str(data.get("selected_store") or "")
        if not selected_store or selected_store=="Compañía":
            raise HTTPException(400,"Selecciona una tienda para exportar modelos")
        rows=[dict(r) for r in data.get("details",[]) if catalog=="Todos" or r.get("catalog")==catalog]
        if not rows:
            raise HTTPException(404,"No hay modelos para exportar en este catálogo y periodo")
        images=fetch_images(rows) if photos else {}
        period=str(data.get("month") or month)
        base=re.sub(r"[^a-zA-Z0-9_-]","_",f"Bonos_{selected_store}_{catalog}_{period}")
        fields=FIELDS_B2 if bonus==2 else FIELDS
        output=excel(rows,selected_store,period,catalog,images,fields) if format=="xlsx" else pdf(rows,selected_store,period,catalog,images,fields)
        mimetype=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format=="xlsx" else "application/pdf")
        return Response(output,media_type=mimetype,headers={
            "Content-Disposition":f'attachment; filename="{base}.{format}"',
            "Cache-Control":"private, no-store",
            "X-Photos-Included":str(len(images)),
        })

    m._V322_BONUS_EXPORTS=True
    print("[V322] Exportaciones XLSX/PDF de Bonos habilitadas.",flush=True)
