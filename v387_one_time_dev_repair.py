"""V387: una sola reparación segura de DEV (25/oct) desde Excel persistente.

Se ejecuta una vez por huella del archivo original y sólo si:
- el FIFO publicado no contiene DEV para el día esperado;
- el Excel original contiene cabeceras explícitas para ese día;
- existe espacio suficiente en disco.
Reutiliza V368 para validación, respaldo hardlink y publicación atómica.
No escribe en operaciones_ropa_operativo.json directamente.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from threading import Thread
from datetime import datetime, timezone
import time

TARGET_DAY="2026-10-25"
MARKER_NAME="v387_once_repair_20261025.json"


def _date_covered_in_original(m, raw):
    from daily_sales_headers import detect_monthly_layout,locate_daily_headers
    with m._xlsx_stream_book(raw) as book:
        months=[name for name in book["sheet_paths"]
                if m._monthly_sheet_name(name) and
                ("octubre" in name.lower() or "october" in name.lower())]
        if not months:
            return False,"No se encontró hoja Octubre en el Excel persistente"
        for name in months:
            reader=m._xlsx_monthly_rows(
                book["archive"],book["sheet_paths"][name],book["shared_value"]
            )
            try:
                lines=[dict(next(reader,{}) or {}) for _ in range(18)]
            finally:
                reader.close()
            layout=detect_monthly_layout(lines)
            groups,warnings,_=locate_daily_headers(
                lines,first_daily_index=layout["first_daily_col"]
            )
            if warnings:
                return False,"Encabezado mensual inválido: "+"; ".join(warnings[:2])
            if any(str(g[1])==TARGET_DAY for g in groups):
                return True,name
        return False,"El Excel persistente no contiene encabezado del 25 de octubre"


def _write_marker(path,data):
    temp=path.with_name(path.name+".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    os.replace(temp,path)


def install(m):
    marker=Path(m.DATA_ROOT)/MARKER_NAME
    raw=Path(m.DATA_ROOT)/"cambios_muertos_actual.xlsx"
    def launch():
        time.sleep(12)  # primero dejar que Render complete la inicialización
        try:
            if not raw.is_file() or not m.OPS_FILE.is_file():
                print("[V387] Omisión: falta base original o base procesada",flush=True)
                return
            fingerprint=f"{raw.stat().st_size}:{raw.stat().st_mtime_ns}"
            try:
                previous=json.loads(marker.read_text(encoding="utf-8"))
            except (FileNotFoundError,ValueError,TypeError):
                previous={}
            if previous.get("fingerprint")==fingerprint and previous.get("status")=="queued":
                print("[V387] Esta huella de Excel ya tiene un intento de reparación; no repetir.",flush=True)
                return
            source=m.load_ops()
            fifo=m._get_recovery_fifo_rows(source) or ()
            current=sum(max(float(r.get("dev_pzs") or 0),0)
                        for r in fifo if str(r.get("date") or "")[:10]==TARGET_DAY)
            if current>0:
                print(f"[V387] Base ya contiene DEV 25/oct: {current:.0f}; no modificar.",flush=True)
                return
            if shutil.disk_usage(m.DATA_ROOT).free < 70*1024*1024:
                print("[V387] Disco insuficiente: se conserva base vigente.",flush=True)
                return
            ok,description=_date_covered_in_original(m,raw)
            if not ok:
                print(f"[V387] Fuente no apta: {description}; sin modificaciones.",flush=True)
                return
            request=m._V368_start_internal_rebuild("day",TARGET_DAY)
            if request.get("status")!="queued":
                print(f"[V387] No se inició: {request}",flush=True)
                return
            marker_data={
                "fingerprint":fingerprint,"status":"queued",
                "target_day":TARGET_DAY,"job_id":request["job_id"],
                "created_at":datetime.now(timezone.utc).isoformat(),
            }
            _write_marker(marker,marker_data)
            print(
                f"[V387] Reparación solicitada al worker V368. "
                f"job={request['job_id']} origen={description}; respaldo obligatorio.",
                flush=True,
            )
        except Exception as exc:
            print(f"[V387] Sin cambios en la base: {type(exc).__name__}: {exc}",flush=True)
    Thread(target=launch,daemon=True,name="dev-once-v387").start()
