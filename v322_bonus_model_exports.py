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
            req = urllib.request.Request(IMG_BASE + product_id + ".jpg",
                       headers={"User-Agent": "OperacionesRopa/1.0", "Accept": "image/jpeg"})
            with urllib.request.urlopen(req, timeout=2.5) as res:
                raw = res.read(1_200_001)
            if len(raw)>1_200_000 or not raw.startswith(b"\xff\xd8\xff"):
                return None
            from PIL import Image as PILImage
            with PILImage.open(BytesIO(raw)) as im:
                im.thumbnail((94, 110))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                out = BytesIO()
                im.save(out, format="JPEG", quality=70, optimize=True)
                return out.getvalue()
        except (OSError, URLError, ValueError):
            return None

    def fetch_images(rows):
        pictures = {}
        ids = {str(r.get("id_art") or "") for r in rows}
        ids = [i for i in ids if re.fullmatch(r"\d{1,15}", i)]
        if not ids:
            return pictures
        # Cota de concurrencia para no saturar el servicio ni el host de fotografías.
        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="bono-foto") as pool:
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
        if key in ("id_art", "model", "catalog"):
            return str(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return ""

    def excel(rows, store, month, catalog, pictures):
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image as XLSImage
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        wb=Workbook()
        ws=wb.active
        ws.title="Modelos a Detalle"
        ws.merge_cells("A1:L1")
        ws["A1"]="Operaciones Ropa — Bonos · Modelos a Detalle"
        ws["A1"].font=Font(size=16, bold=True, color="FFFFFF")
        ws["A1"].fill=PatternFill("solid",fgColor="123B73")
        ws.merge_cells("A2:L2")
        ws["A2"]=f"Tienda: {store}  |  Periodo: {month}  |  Catálogo: {catalog}  |  Modelos: {len(rows)}"
        ws["A2"].font=Font(size=11, bold=True, color="123B73")
        ws.append([])
        for col,(label,_key) in enumerate(FIELDS,1):
            c=ws.cell(4,col,label)
            c.font=Font(bold=True,color="FFFFFF")
            c.fill=PatternFill("solid",fgColor="1769E8")
            c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
        ws.row_dimensions[4].height=32
        for idx,row in enumerate(rows,5):
            ident=str(row.get("id_art") or "")
            photo=pictures.get(ident)
            ws.row_dimensions[idx].height=42
            if photo:
                try:
                    image=XLSImage(BytesIO(photo))
                    image.width=36;image.height=43
                    ws.add_image(image, f"A{idx}")
                except Exception:
                    ws.cell(idx,1,"Sin foto")
            else:
                ws.cell(idx,1,"Sin foto")
            for col,(_label,key) in enumerate(FIELDS[1:],2):
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
        widths=[11,16,18,17,16,16,19,18,18,20,20,20]
        for col,w in enumerate(widths,1):
            ws.column_dimensions[get_column_letter(col)].width=w
        ws.freeze_panes="C5"
        ws.auto_filter.ref=f"B4:L{len(rows)+4}"
        ws.sheet_properties.pageSetUpPr.fitToPage=True
        ws.page_setup.orientation="landscape"
        ws.page_setup.paperSize=ws.PAPERSIZE_A3
        buf=BytesIO();wb.save(buf)
        return buf.getvalue()

    def pdf(rows, store, month, catalog, pictures):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A3
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer, Image as PDFImage
        buf=BytesIO()
        doc=SimpleDocTemplate(buf,pagesize=landscape(A3),rightMargin=15,leftMargin=15,topMargin=18,bottomMargin=18)
        styles=getSampleStyleSheet()
        safe=lambda s: str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        story=[Paragraph("Operaciones Ropa — Bonos · Modelos a Detalle",styles["Heading2"]),
               Paragraph(f"Tienda: {safe(store)} &nbsp;&nbsp; Periodo: {safe(month)} &nbsp;&nbsp; Catálogo: {safe(catalog)} &nbsp;&nbsp; Modelos: {len(rows)}",styles["Normal"]),Spacer(1,9)]
        headers=[x[0] for x in FIELDS]
        data=[headers]
        for row in rows:
            ident=str(row.get("id_art") or "")
            photo=pictures.get(ident)
            if photo:
                try:
                    im=PDFImage(BytesIO(photo),width=30,height=34)
                except Exception:
                    im="—"
            else:
                im="—"
            line=[im]
            for _label,key in FIELDS[1:]:
                v=cell_value(row,key)
                if isinstance(v,float):
                    line.append(("$"+format(v,",.2f")) if "investment" in key else format(v,",.1f"))
                else:
                    line.append(str(v)[:26])
            data.append(line)
        widths=[44,63,91,76,70,70,86,89,89,98,98,104]
        table=LongTable(data,colWidths=widths,repeatRows=1,hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123B73")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),6.4),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F2F6FB")]),
            ("LINEBELOW",(0,0),(-1,-1),0.2,colors.HexColor("#D3DFEC")),
        ]))
        story.append(table)
        doc.build(story)
        return buf.getvalue()

    @m.app.get("/api/bonuses/models-export")
    def export_bonus_models(request:Request,month:str="",store:str="",bonus:int=1,catalog:str="Abrigador",format:str="xlsx",photos:bool=True):
        m.require_user(request)
        if bonus not in range(1,7) or catalog not in (*CATALOGS,"Todos") or format not in ("xlsx","pdf"):
            raise HTTPException(400,"Parámetros de exportación inválidos")
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
        output=excel(rows,selected_store,period,catalog,images) if format=="xlsx" else pdf(rows,selected_store,period,catalog,images)
        mimetype=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format=="xlsx" else "application/pdf")
        return Response(output,media_type=mimetype,headers={
            "Content-Disposition":f'attachment; filename="{base}.{format}"',
            "Cache-Control":"private, no-store",
            "X-Photos-Included":str(len(images)),
        })

    m._V322_BONUS_EXPORTS=True
    print("[V322] Exportaciones XLSX/PDF de Bonos habilitadas.",flush=True)
