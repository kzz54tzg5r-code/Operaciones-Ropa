"""Contrato Buen Fin sin depender de fotos ni del XLSX de producción."""
from io import BytesIO
import zipfile
from xml.sax.saxutils import escape

from buen_fin_module import STRATEGIES, WITHDRAWALS, parse_workbook, _scan_id, _status

def _book():
    names = list(WITHDRAWALS) + list(STRATEGIES)
    workbook = ('<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' +
      ''.join('<sheet name="'+escape(name, {'"':'&quot;'})+'" sheetId="'+str(i)+'" r:id="rId'+str(i)+'"/>'
        for i,name in enumerate(names,1)) + '</sheets></workbook>')
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(
        '<Relationship Id="rId'+str(i)+'" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet'+str(i)+'.xml"/>' for i in range(1,len(names)+1))+'</Relationships>'
    def row(n, pairs):
        return '<row r="'+str(n)+'">'+''.join(
          '<c r="'+k+str(n)+'" t="inlineStr"><is><t>'+escape(str(v))+'</t></is></c>'
          for k,v in pairs.items())+'</row>'
    buf=BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml',workbook)
        z.writestr('xl/_rels/workbook.xml.rels',rels)
        for i,name in enumerate(names,1):
            if name in WITHDRAWALS:
                rows = row(4,{'C':'ID'})+row(5,{'C':'1234567','N':'PROMO 30%', 'S':'FINDE 20-30%'})
            else:
                rows = row(4,{'B':'NOTAS CANCELACIONES','C':'ID','D':'Corrida','E':'Modelo',
                    'F':'Marca Price','O':'Precio actual','P':'Precio propuesto','Q':'Descuento',
                    'R':'Precio actual Veracruz','S':'Precio propuesto Veracruz'})
                if name == STRATEGIES[0]:
                    rows += row(5,{'C':'1234567','B':'PENDIENTE DE LIBERACIÓN · EN COSTOS','E':'A100','F':'MARCA','O':'2do al 50% o 3x2'})
                elif name == STRATEGIES[1]:
                    rows += row(5,{'C':'1234567','B':'REINTEGRADO','E':'A100','F':'MARCA',
                        'O':'399','P':'319.2','Q':'0.2','R':'499','S':'399.2'})
                else:
                    rows += row(5,{'C':str(1234500+i),'E':'A100','F':'MARCA','O':'399',
                        'P':'299','Q':'0.25'})
            z.writestr(f'xl/worksheets/sheet{i}.xml',
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+rows+'</sheetData></worksheet>')
    return buf.getvalue()

def test_sin_duplicar_imagenes():
    d=parse_workbook(_book())
    assert d['resumen']['registros']==len(STRATEGIES)
    assert d['resumen']['retiros']==2
    assert d['resumen']['estados']['Reintegrado']==1
    assert d['resumen']['estados']['Pendiente de liberación']==1
    assert d['rows'][0]['precio_tienda'] is None
    assert d['rows'][1]['precio_tienda']==399
    assert d['rows'][1]['precio_veracruz']==499
    assert d['rows'][1]['descuento']==0.2
    assert d['retiros'][0]['promocion_retirada']=='PROMO 30%'
    assert not any('foto' in k for record in d['rows'] for k in record)

def test_escaneo_y_cancelacion():
    assert _scan_id('133408714$')=='1334087'
    assert _scan_id('36007')=='36007'
    assert _scan_id('ZX0987')==''
    assert _status('SE CANCELA DE ESTA PROMOCIÓN PARA PARTICIPAR EN 3X999')=='Cancelado'
    assert _status('NUEVO · Gancho sem 45 reactivado')=='Vigente'


def test_precios_de_mayoreo_ultimo_capacidades_por_tienda():
    import pandas as pd
    from buen_fin_module import _wholesale_snapshot, _priced_record, _store_for_user

    class FakeApp:
        pd = pd
        version = 1

        def _capacity_source_entry(self, period=""):
            return {"id": str(self.version), "status": "procesado",
                    "name": "capacidades_ultima_carga.xlsx",
                    "uploaded_at": "2026-11-13T12:00:00"}

        def _latest_capacity_frame(self):
            price = 159.90 if self.version == 2 else 119.90
            return pd.DataFrame([
                {"ID_ART": "1234567", "Tienda": "Iztapalapa", "Costo unitario": price},
                {"ID_ART": "1234567", "Tienda": "Vallejo", "Costo unitario": price},
                {"ID_ART": "1234567", "Tienda": "Veracruz", "Costo unitario": 129.90},
                {"ID_ART": "7777777", "Tienda": "Iztapalapa", "Costo unitario": 1.00},
            ])

        def login_key(self, value):
            return str(value or "").casefold().strip()

        def store_names(self, active=True):
            return ["Iztapalapa", "Vallejo", "Veracruz"]

    app = FakeApp()
    data = parse_workbook(_book())
    three_for_two = next(x for x in data["rows"] if x["estrategia"] == STRATEGIES[0])
    twenty_off = next(x for x in data["rows"] if x["estrategia"] == STRATEGIES[1])
    snapshot = _wholesale_snapshot(app, data)
    assert snapshot["source"]["archivo"] == "capacidades_ultima_carga.xlsx"
    priced = _priced_record(app, three_for_two, snapshot, "Iztapalapa")
    assert priced["precio_tienda"] == 119.90
    assert priced["precio_veracruz"] == 129.90
    assert priced["precio_promo_tienda"] is None
    assert priced["precio_promo_veracruz"] is None
    assert priced["fuente_precio"].startswith("Precio mayoreo")
    assert _priced_record(app, twenty_off, snapshot)["precio_tienda"] == 399
    assert _priced_record(app, twenty_off, snapshot)["precio_promo_tienda"] == 319.2
    assert _store_for_user(app, {"role": "tienda", "store": "Iztapalapa"}, "Veracruz") == "Iztapalapa"

    # Entra otro archivo de Capacidades: se renueva el precio, sin actualizar Buen Fin.
    app.version = 2
    latest = _wholesale_snapshot(app, data)
    assert _priced_record(app, three_for_two, latest, "Iztapalapa")["precio_tienda"] == 159.90
    assert _priced_record(app, three_for_two, latest, "Veracruz")["precio_tienda"] == 129.90

    # No suponer que Veracruz tiene precio si la tienda no aparece en la fuente.
    app._latest_capacity_frame = lambda: pd.DataFrame([
        {"ID_ART": "1234567", "Tienda": "Iztapalapa", "Costo unitario": 100.00}
    ])
    app.version = 3
    no_ver = _wholesale_snapshot(app, data)
    assert _priced_record(app, three_for_two, no_ver, "Iztapalapa")["precio_veracruz"] is None
    assert _priced_record(app, three_for_two, no_ver, "Vallejo")["precio_tienda"] is None
