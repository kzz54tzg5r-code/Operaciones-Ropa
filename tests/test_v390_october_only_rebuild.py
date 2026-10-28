"""V390: octubre reemplazado íntegro sin alterar operaciones u otros meses."""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from v390_rebuild_october_fifo import rebuild_month


def _setup(fake_monthly=5):
    previous=[
        {"date":"2026-09-30","store":"Puebla Sur","dev_pzs":8},
        {"date":"2026-10-24","store":"Puebla Sur","dev_pzs":90},
    ]
    original={
        "rows":[{"date":"2026-10-25","pieces":23}],
        "recovery_fifo":previous,
        "uploaded_at":"2026-10-26T17:13:40",
        "source_file":"base.xlsx",
        "monthly_sheets":["Octubre 26"],
        "recovery_header_audit":{},
        "meta_index":{"available_dates":["2026-09-30"],"available_months":["2026-09"]},
    }
    @contextmanager
    def stream(_):
        yield {"sheet_paths":{"Octubre 26":"sheet.xml"}}
    def parse(_,names,stream_book):
        stream_book["recovery_header_audit"]={
            "Octubre 26":{"last_date":"2026-10-25","warnings":[],
                           "total_monthly_dev":fake_monthly}
        }
        rows=[
            {"date":"2026-10-24","store":"Puebla Sur","dev_pzs":2},
            {"date":"2026-10-25","store":"Puebla Sur","dev_pzs":3},
        ]
        return rows,["2026-W43"],["2026-10"],[]
    m=SimpleNamespace(load_ops=lambda:original,
                      _xlsx_stream_book=stream,
                      _stream_monthly_recovery_fifo=parse,
                      _monthly_sheet_name=lambda x:x.endswith("26"))
    return m,original


def test_replaces_october_not_old_months_or_productivity():
    m,original=_setup()
    updated=rebuild_month(m,"base.xlsx","2026-10-25")
    fifo=updated["recovery_fifo"]
    assert [(r["date"],r["dev_pzs"]) for r in fifo]==[
        ("2026-09-30",8),("2026-10-24",2),("2026-10-25",3)
    ]
    assert updated["rows"]==original["rows"]
    assert updated["uploaded_at"]==original["uploaded_at"]
    assert original["recovery_fifo"][1]["dev_pzs"]==90
    assert "2026-10-25" in updated["meta_index"]["available_dates"]


def test_rejects_monthly_dev_mismatch_without_modifying_existing():
    m,original=_setup(fake_monthly=9)
    with pytest.raises(ValueError,match="no concilian"):
        rebuild_month(m,"base.xlsx","2026-10-25")
    assert original["recovery_fifo"][1]["dev_pzs"]==90


def test_cannot_change_other_months():
    m,_=_setup()
    with pytest.raises(ValueError,match="solo puede corregir"):
        rebuild_month(m,"base.xlsx","2026-09-25")
