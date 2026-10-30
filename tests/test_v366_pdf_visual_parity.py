"""Regresión del PDF de Centro Operativo en sus vistas Día/Semana/Mes."""
from io import BytesIO
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

from v272_center_pdf_parity_patch import install


def _sample(period):
    stores = [
        dict(store="Puebla Sur", is_project=True, dev_pzs=6, muertos=12,
             probador=8, cajas=2, pendiente_anterior=18, total_pzs=640,
             ingresos=640, recorridos=6, acondicionado=160, ubicado=200,
             pendiente_acondicionar=480, pendiente_ubicar=440),
        dict(store="Vallejo", is_project=True, dev_pzs=4, muertos=8,
             probador=5, cajas=3, pendiente_anterior=0, total_pzs=360,
             ingresos=360, recorridos=4, acondicionado=330, ubicado=400,
             pendiente_acondicionar=30, pendiente_ubicar=0),
    ]
    recovery = [
        dict(store="Puebla Sur", is_project=True, dev_pzs=12,
             converted_pieces=6, conversion_pct=50, return_value=1500,
             recovered_value=750, recovery_pct=50, pending_pieces=6,
             pending_value=750),
        dict(store="Vallejo", is_project=True, dev_pzs=8,
             converted_pieces=4, conversion_pct=50, return_value=4000,
             recovered_value=2000, recovery_pct=50, pending_pieces=4,
             pending_value=2000),
    ]
    date = {"day":"2026-10-24","week":"2026-W43","month":"2026-10"}[period]
    data = dict(period_type=period,period_value=date,stores=stores,
                recovery_by_store=recovery,metrics=dict(total_pzs=1000,dev_pzs=10,
                muertos=20,probador=13,cajas=5,pendiente_anterior=18,
                acondicionado=490,ubicado=600,recorridos=10,meta_recorridos=48,
                pct_recorridos=20.833,pct_acondicionado=49,pct_ubicado=60,
                pendiente_acondicionar=510,pendiente_ubicar=400))
    state = SimpleNamespace(
        _build_operations_pdf=lambda data, report, scope="Compañía": b"fallback",
        _operations_export_sections=lambda data: (stores, recovery),
    )
    install(state)
    return state._build_operations_pdf(data,"Centro Operativo",scope="Compañía")


@pytest.mark.parametrize("period", ["day","week","month"])
def test_pdf_four_cards_and_full_detail(period):
    pdf=_sample(period)
    assert pdf.startswith(b"%PDF")
    reader=PdfReader(BytesIO(pdf))
    assert reader.pages
    text="\n".join(page.extract_text() or "" for page in reader.pages)
    for label in ("Ingresado","En proceso","En piso","Recorridos",
                  "Reporte completo por tienda","Detalle operativo","Puebla Sur",
                  "Vallejo", "Ingreso vs Acondicionado vs Ubicado"):
        assert label in text
    assert "TOTAL OPERACIÓN" not in text  # antigua matriz ausente en la web
    assert "Recuperación por tienda" in text
    assert "miles de pesos" in text
    assert "$1.5 mil" in text


def test_pdf_uses_embedded_price_shoes_asset():
    pdf=_sample("day")
    reader=PdfReader(BytesIO(pdf))
    resources=reader.pages[0]["/Resources"]
    images=resources.get("/XObject")
    assert images is not None
    entries=images.get_object()
    assert any(obj.get_object().get("/Subtype")=="/Image" for obj in entries.values())



def test_pdf_visual_hierarchy_has_readable_typography_and_transparent_brand():
    """Guarda la composición del reporte: 4 tarjetas, dos tablas y gráfico."""
    import pdfplumber
    from v403_white_price_logo_pdf import price_white_reader

    pdf=_sample("day")
    with pdfplumber.open(BytesIO(pdf)) as document:
        assert len(document.pages) <= 3
        assert all(int(page.width)==792 and int(page.height)==612 for page in document.pages)
        words=[word for page in document.pages
               for word in page.extract_words(extra_attrs=["size"])]
        assert any("Ingresado" in word["text"] and word["size"]>=10 for word in words)
        assert any("Vallejo" in word["text"] and word["size"]>=7.2 for word in words)
        assert any("Recuperación" in word["text"] and word["size"]>=11 for word in words)
    img=price_white_reader()
    assert img.getSize()==(211,121)
    raw=img._image.convert("RGBA")
    # El fondo del gráfico original no debe pintarse de blanco.
    assert raw.getpixel((0,0))[3] < 50
    assert any(raw.getpixel((x,y))[3]>70
               for x in range(20,191,12) for y in range(10,111,12))
