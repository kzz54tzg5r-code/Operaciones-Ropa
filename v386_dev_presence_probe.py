"""Temporary read-only source-side audit for the 25 October DEV discrepancy."""
from collections import defaultdict
from v372_dev_total_pending_patch import _key, _number


def install(m):
    try:
        source = m.load_ops()
        raw = m._get_recovery_fifo_rows(source) or []
        date="2026-10-25"
        by_store=defaultdict(float)
        for r in raw:
            if str(r.get("date") or "")[:10] == date:
                store=m._normalize_store_value(r.get("store") or "")
                by_store[store] += max(_number(r.get("dev_pzs")),0)
        configured=set(m.store_names(True))
        aligned=sum(dev for store,dev in by_store.items() if store in configured)
        print(
            f"[V386-PROBE] {date} fifo_entries={len(raw)}"
            f" stores_with_dev={len(by_store)}"
            f" dev_total={sum(by_store.values()):.0f}"
            f" dev_for_configured_stores={aligned:.0f}"
            f" configured_count={len(configured)}"
            f" store_dev={dict(sorted(by_store.items()))}",
            flush=True,
        )
    except Exception as exc:
        print(f"[V386-PROBE] No se pudo evaluar la fuente: {type(exc).__name__}: {exc}",flush=True)
