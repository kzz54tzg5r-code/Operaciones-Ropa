"""V403 · Marca Price Shoes blanca y transparente sobre fondos azules.

Mantiene la silueta del logotipo original, convierte la tinta a blanco y elimina
el fondo blanco. Compartido entre encabezado del PDF y apéndice de colaboradores.
"""
from functools import lru_cache
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader


@lru_cache(maxsize=1)
def price_white_reader():
    root = Path(__file__).resolve().parent
    source = root / "assets" / "price_shoes_logo.png"
    if not source.exists():
        source = root / "web" / "price_shoes_logo.png"
    with Image.open(source) as original:
        rgba = original.convert("RGBA")
    rgba_data = []
    for r,g,b,a in rgba.getdata():
        # Convertir a transparencia según la oscuridad del color:
        # tinta azul -> opaca; fondo blanco -> completamente transparente.
        lum = .30*r + .59*g + .11*b
        ink = max(0,min(255,round((255-lum)*1.9)))
        opacity = round(a*ink/255)
        rgba_data.append((255,255,255,opacity))
    rgba.putdata(rgba_data)
    return ImageReader(rgba)


def draw_price_white(canvas,x,y,width,height):
    img=price_white_reader()
    canvas.drawImage(img,x,y,width=width,height=height,
                     preserveAspectRatio=True,anchor="c",mask="auto")
