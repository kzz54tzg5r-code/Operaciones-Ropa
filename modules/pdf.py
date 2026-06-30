from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_simple_pdf(title, summary):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    w, h = letter
    c.setFont('Helvetica-Bold', 16)
    c.drawString(40, h-50, title)
    c.setFont('Helvetica', 11)
    y = h-90
    for k, v in summary.items():
        c.drawString(40, y, f'{k}: {v}')
        y -= 22
    c.save()
    buffer.seek(0)
    return buffer
