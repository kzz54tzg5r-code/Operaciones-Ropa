"""V390: reconstruir únicamente octubre desde Excel, preservando operación y otros meses.

Utiliza el lector compacto V389, encabezados verificados, validación de totales
mensuales y luego la escritura atómica + respaldo de V368. No publica por sí solo.
"""
from __future__ import annotations
from collections import defaultdict
import math


def _num(value):
    try:
        n=float(value or 0)
        return n if math.isfinite(n) and n>0 else 0.0
    except (TypeError,ValueError,OverflowError):
        return 0.0


def rebuild_month(m,raw_excel,period):
    month=str(period or "")[:7]
    if month != "2026-10":
        raise ValueError("V390 solo puede corregir el corte auditado Octubre 2026")
    current=m.load_ops()
    old=current.get("recovery_fifo")
    if not isinstance(old,list):
        raise ValueError("La base vigente no tiene lotes originales seguros")
    with m._xlsx_stream_book(raw_excel) as book:
        month_sheets=[name for name in book["sheet_paths"]
                      if m._monthly_sheet_name(name) and
                      "octubre" in str(name).casefold()]
        if len(month_sheets)!=1:
            raise ValueError(f"Se requiere una única hoja Octubre 26; encontradas {len(month_sheets)}")
        new_fifo,weeks,months,errors=m._stream_monthly_recovery_fifo(
            raw_excel,month_sheets,stream_book=book
        )
        audit=dict(book.get("recovery_header_audit") or {})
    if errors:
        raise ValueError("No se reemplaza la base: "+"; ".join(str(v) for v in errors[:2]))
    month_audit=audit.get(month_sheets[0]) or {}
    if month_audit.get("warnings"):
        raise ValueError("No se reemplaza la base: cabeceras de octubre inválidas")
    if not month_audit.get("last_date") or month_audit["last_date"] < "2026-10-25":
        raise ValueError("El Excel no cubre el día 25 de octubre")
    if any(str(r.get("date") or "")[:7]!=month for r in new_fifo):
        raise ValueError("Se detectaron lotes fuera de octubre; no se publicó")
    actual=sum(_num(r.get("dev_pzs")) for r in new_fifo)
    monthly=_num(month_audit.get("total_monthly_dev"))
    if actual<=0 or monthly<=0 or abs(actual-monthly)>max(1.,monthly*.01):
        raise ValueError(f"DEV de octubre no concilian: total={monthly:.0f}, reconstruido={actual:.0f}")
    byday=defaultdict(float)
    for row in new_fifo:byday[str(row.get("date") or "")[:10]]+=_num(row.get("dev_pzs"))
    if byday.get("2026-10-25",0)<=0:
        raise ValueError("La columna DEV del 25/oct no produjo lotes, se conserva la base anterior")
    other=[r for r in old if str(r.get("date") or "")[:7]!=month]
    updated=dict(current)
    updated["recovery_fifo"]=sorted(
        other+new_fifo,key=lambda r:(str(r.get("date") or ""),str(r.get("store") or ""))
    )
    headers=dict(current.get("recovery_header_audit") or {})
    headers.update(audit)
    updated["recovery_header_audit"]=headers
    updated["errors"]=[x for x in current.get("errors",[])
                       if not any(str(x).startswith(n+":") for n in month_sheets)]
    index=dict(updated.get("meta_index") or {})
    index["available_dates"]=sorted(set(index.get("available_dates") or [])
                                     | {str(r.get("date")) for r in new_fifo if r.get("date")})
    index["available_weeks"]=sorted(set(index.get("available_weeks") or [])|set(weeks))
    index["available_months"]=sorted(set(index.get("available_months") or [])|set(months))
    updated["meta_index"]=index
    print(f"[V390] Octubre corregido: DEV total={actual:.0f} "
          f"DEV 24/oct={byday.get('2026-10-24',0):.0f} "
          f"DEV 25/oct={byday.get('2026-10-25',0):.0f}; "
          f"FIFO octubre={len(new_fifo)}; "
          f"otros meses intactos={len(other)}",flush=True)
    return updated
