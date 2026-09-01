from io import BytesIO

from pypdf import PdfReader

from web_app import _build_operations_pdf, _operations_export_sections, _report_export_payload


def _sample_report_data():
    stores=[]
    recovery=[]
    for index,name in enumerate(("Vallejo","Toluca","Puebla Sur"),1):
        stores.append({
            "store":name,
            "is_project":False,
            "muertos":index * 10,
            "probador":0,
            "cajas":index,
            "recolectadas":index * 11,
            "recorridos":index,
            "acondicionado":index * 9,
            "ubicado":index * 8,
            "pendiente_acondicionar":index * 2,
            "pendiente_ubicar":index,
        })
        recovery.append({
            "store":name,
            "is_project":False,
            "dev_pzs":index * 20,
            "converted_pieces":index * 10,
            "conversion_pct":50,
            "return_value":index * 1000,
            "recovered_value":index * 500,
            "recovery_pct":50,
        })
    return {
        "period_value":"2026-08",
        "metrics":{},
        "stores":stores,
        "recovery_by_store":recovery,
        "productivity":[],
        "project_stores":["Vallejo","Puebla Sur"],
    }


def test_export_scope_keeps_company_recovery_and_project_detail():
    data=_sample_report_data()
    stores,recovery=_operations_export_sections(data)
    assert [row["store"] for row in stores] == ["Vallejo","Puebla Sur"]
    assert [row["store"] for row in recovery] == ["Vallejo","Toluca","Puebla Sur"]
    assert [row["store"] for row in recovery if row["is_project"]] == ["Vallejo","Puebla Sur"]

    _,excel_stores,excel_recovery,_=_report_export_payload(data,"Centro Ejecutivo")
    assert [row["store"] for row in excel_stores] == ["Vallejo","Puebla Sur"]
    assert [row["store"] for row in excel_recovery] == ["Vallejo","Toluca","Puebla Sur"]


def test_pdf_labels_all_recovery_and_marks_project_stores():
    pdf=_build_operations_pdf(_sample_report_data(),"Centro Ejecutivo")
    text="\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)
    assert "Recuperación por tienda · todas las tiendas" in text
    assert "Detalle operativo · tiendas del proyecto" in text
    assert "Vallejo (Proyecto)" in text
    assert "Puebla Sur (Proyecto)" in text
    assert "Toluca (Proyecto)" not in text
