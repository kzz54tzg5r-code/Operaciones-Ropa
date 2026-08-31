from __future__ import annotations
import json, os, platform, sys
from pathlib import Path

if os.name == "nt":
    platform.machine = lambda: "AMD64"

def main():
    if len(sys.argv) != 3:
        print("Uso: operations_parse_worker.py <xlsx> <salida.json>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])

    import web_app
    payload = web_app.parse_operations_excel(src, persist=False)
    out.write_text(web_app._safe_json_dump(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(payload.get("rows") or [])}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
