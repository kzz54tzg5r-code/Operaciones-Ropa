"""Pruebas AC aisladas. Ejecutar: python -m unittest -v test_ac_bridge.py"""
import tempfile
import unittest
from io import BytesIO
from openpyxl import Workbook
from ac_bridge import ACBridge

def make_excel(curve=18):
    workbook=Workbook()
    sheet=workbook.active
    sheet.append(["TIENDA","ID_ART","TALLA","CURVA","CAPACIDAD"])
    sheet.append(["Iztapalapa","914629","M",curve,20])
    sheet.append(["Iztapalapa","914629","G",12,14])
    dest=BytesIO();workbook.save(dest)
    return dest.getvalue()

class TestACBridge(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.ac=ACBridge(self.tmp.name)
        self.ac.initialize()
    def tearDown(self):
        self.tmp.cleanup()
    def test_excel_version_and_missing(self):
        self.assertEqual(self.ac.suggest(store="Iztapalapa",model_id="914629",size="M")["status"],"missing_capacity")
        self.ac.upload_capacities(make_excel(),version="A",admin_user="admin")
        self.ac.upload_capacities(make_excel(22),version="B",admin_user="admin")
        self.assertEqual(self.ac.capacities.latest("Iztapalapa","914629","M")["curve"],22)
        with self.assertRaises(Exception):
            self.ac.upload_capacities(make_excel(),version="A",admin_user="admin")
    def test_capture_retries_no_duplicates(self):
        sid=self.ac.start(store="Iztapalapa",employee_id="EMP1",flow="Surtido",stage="Separar",area="Colgado")
        kwargs=dict(event_key="scan-1",session_id=sid,employee_id="EMP1",model_id="914629",sizes={"G":6,"XCH":5,"M":7})
        self.assertEqual(self.ac.capture(**kwargs),self.ac.capture(**kwargs))
        self.ac.finish(sid,"EMP1")
        with self.assertRaises(ValueError):
            self.ac.capture(**dict(kwargs,event_key="scan-2"))
    def test_suggest_excludes_rack_and_reservations(self):
        self.ac.upload_capacities(make_excel(),version="A",admin_user="admin")
        floor=self.ac.operation.add_location(store="Iztapalapa",kind="Piso",aisle="1")
        sept=self.ac.operation.add_location(store="Iztapalapa",kind="Septimos",aisle="1",level="3")
        rack=self.ac.operation.add_location(store="Iztapalapa",kind="Rack",aisle="1",level="4")
        for loc,qty in [(floor,8),(sept,9),(rack,50)]:
            self.ac.operation.seed_verified_stock(store="Iztapalapa",location_id=loc,model_id="914629",sizes={"M":qty})
        self.assertEqual(self.ac.suggest(store="Iztapalapa",model_id="914629",size="M")["suggested"],9)
        self.ac.operation.reserve(event_key="res-1",store="Iztapalapa",location_id=sept,model_id="914629",size="M",pieces=6,requested_by="gerente")
        self.assertEqual(self.ac.suggest(store="Iztapalapa",model_id="914629",size="M")["suggested"],3)
    def test_paired_movement_is_one(self):
        floor=self.ac.operation.add_location(store="Iztapalapa",kind="Piso",aisle="1")
        sept=self.ac.operation.add_location(store="Iztapalapa",kind="Septimos",aisle="1",level="3")
        self.ac.operation.seed_verified_stock(store="Iztapalapa",location_id=floor,model_id="914629",sizes={"M":8})
        args=dict(event_key="move-1",store="Iztapalapa",model_id="914629",sizes={"M":5},source=floor,target=sept,employee_id="ABAJO",partner_id="ARRIBA")
        self.assertEqual(self.ac.operation.move(**args),self.ac.operation.move(**args))
        self.assertEqual(self.ac.operation.available("Iztapalapa",sept,"914629","M")["pieces"],5)
        self.assertEqual(self.ac.operation.available("Iztapalapa",floor,"914629","M")["pieces"],3)

if __name__=="__main__":unittest.main()
