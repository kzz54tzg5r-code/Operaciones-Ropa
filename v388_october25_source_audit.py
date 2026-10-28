"""V388 - auditoria no destructiva de DEV 24/25 octubre en Excel persistente."""
from collections import defaultdict
from itertools import chain
from threading import Thread
import math,time

def num(v):
    try:
        n=float(v or 0)
        return n if math.isfinite(n) and n>0 else 0.
    except (ValueError,TypeError,OverflowError):return 0.

def audit(m):
    from daily_sales_headers import detect_monthly_layout, locate_daily_headers
    raw=m.DATA_ROOT/"cambios_muertos_actual.xlsx"
    if not raw.is_file():return {"error":"Excel original ausente"}
    with m._xlsx_stream_book(raw) as book:
        names=[n for n in book["sheet_paths"] if "octubre" in n.casefold() and m._monthly_sheet_name(n)]
        if not names:return {"error":"Hoja octubre ausente"}
        name=names[0]
        reader=m._xlsx_monthly_rows(book["archive"],book["sheet_paths"][name],book["shared_value"])
        header=[dict(next(reader,{}) or {}) for _ in range(18)]
        layout=detect_monthly_layout(header)
        groups,warnings,last=locate_daily_headers(header,first_daily_index=layout["first_daily_col"])
        cols={g[1]:g[0] for g in groups if g[1] in ("2026-10-24","2026-10-25")}
        stats={day:{"dev":0.,"sales":0.,"rows_dev":0,"stores":defaultdict(float)} for day in cols}
        monthly=0.;nrows=0
        for row in chain(header[last+1:],reader):
            if not str(row.get(1) or "").strip():continue
            store=m._normalize_store_value(row.get(layout["store_col"]))
            if not store:continue
            nrows+=1;monthly+=num(row.get(layout["monthly_dev_col"]))
            for day,index in cols.items():
                stats[day]["sales"]+=num(row.get(index))
                dev=num(row.get(index+1))
                stats[day]["dev"]+=dev
                if dev:
                    stats[day]["rows_dev"]+=1
                    stats[day]["stores"][store]+=dev
        for v in stats.values():v["stores"]=dict(sorted(v["stores"].items()))
        return {"sheet":name,"last_date":max((g[1] for g in groups),default=""),
                "col_nums_1based":{day:i+1 for day,i in cols.items()},
                "warning_count":len(warnings),"sku_rows":nrows,
                "monthly_dev_total":monthly,"daily":stats}

def install(m):
    def work():
        time.sleep(12)
        try:
            src=m.load_ops()
            fifo=m._get_recovery_fifo_rows(src) or []
            counts={d:sum(num(r.get("dev_pzs")) for r in fifo if str(r.get("date") or "")[:10]==d)
                    for d in ("2026-10-24","2026-10-25")}
            print(f"[V388-AUDIT] current_fifo={counts}",flush=True)
            print(f"[V388-AUDIT] raw_xlsx={audit(m)}",flush=True)
        except Exception as exc:
            print(f"[V388-AUDIT] error={type(exc).__name__}: {str(exc)[:260]}",flush=True)
    Thread(target=work,daemon=True,name="v388-read-only-audit").start()
