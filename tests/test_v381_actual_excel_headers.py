"""V381: formatos de fechas y cabeceras observados en la base real de abril-octubre.

Los datos del fixture incluyen únicamente etiquetas y fechas, nunca
artículos, empleados ni información comercial de la base del usuario.
"""
from datetime import date, timedelta
from pathlib import Path

import pytest
from daily_sales_headers import locate_daily_headers, resolve_daily_groups


@pytest.mark.parametrize("month,first,days", [
    (4,"20/04/2026",11),
    (5,46143.0,31),
    (6,46174.0,30),
    (7,46204.0,31),
    (8,46235.0,30),
    (9,46266.0,30),
    (10,"01/10/2026",12),
])
def test_real_monthly_source_headers(month, first, days):
    first_day = date(2026,month,20 if month==4 else 1)
    dates={}
    labels={}
    for i in range(days):
        next_day=first_day+timedelta(days=i)
        value=(next_day-date(1899,12,30)).days if isinstance(first,float) else next_day.strftime("%d/%m/%Y")
        start=29+i*3 # AD/AE/AF in zero-based indices
        for offset in (0,1,2):
            dates[start+offset]=value
        labels[start]="Ventas Neta Pzs" if month in (7,8) else "Ventas Netas Pzs"
        labels[start+1]="Dev Pzs"
        labels[start+2]="Venta Neta en $"
    # A partir de la fila 3 vienen los artículos, incluyendo tiendas en Z.
    product={1:"1000",25:"Vallejo",27:2,29:1,30:2,31:100}
    headers=[dates,labels,product]+[{} for _ in range(15)]
    groups,warnings,last_index=locate_daily_headers(headers)
    assert len(groups)==days, (month,warnings,len(groups),days)
    assert warnings==[]
    assert last_index==1
    assert groups[0][1]==first_day.isoformat()
    assert groups[-1][1]==(first_day+timedelta(days=days-1)).isoformat()


def test_preflight_prevents_missing_audit_false_rejection():
    content=(Path(__file__).resolve().parents[1]/"web_app.py").read_text(encoding="utf-8")
    assert "recognition_mode\":\"source_xlsx_verified" in content
    assert "peek=_xlsx_monthly_rows(archive,member,read_shared)" in content
    assert "not recovery_fifo and not broken" in content
    assert "stream_book[\"recovery_header_audit\"]=header_audit" in content


def test_wrong_columns_are_not_accepted():
    row1={29:"01/10/2026",30:"01/10/2026",31:"01/10/2026"}
    row2={29:"Dev Pzs",30:"Ventas Netas Pzs",31:"Venta Neta en $"}
    groups,issues=resolve_daily_groups(row1,row2)
    assert groups==[]
    assert any("orden inválido" in msg for msg in issues)
