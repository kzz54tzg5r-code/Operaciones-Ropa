"""Local synthetic benchmark; never connects to or writes production data."""
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory(prefix="ropa-benchmark-") as folder:
        output = Path(folder)
        os.environ["OPERACIONES_ROPA_DATA"] = str(output / "data")
        with redirect_stdout(StringIO()):
            import web_app as m
            m.WEB = output / "web"
            shutil.copytree(ROOT / "web", m.WEB)
            import server_entry
            from fastapi.testclient import TestClient
            from openpyxl import Workbook

            workbook = Workbook(write_only=True)
            sheet = workbook.create_sheet("Resultados productividad 1")
            sheet.append(["Fecha", "Ocurrencia", "Tienda", "Tabla", "Actividad Realizada", "Área",
                          "Número de Piezas", "Hora Inicio", "Hora Fin", "Nombre", "Motivo de ingreso", "RECORRIDOS"])
            activities = ["Recolección de muertos", "Acondicionado", "Ubicado"]
            for index in range(2400):
                sheet.append([datetime(2026, 10, 1), str(index), "Iztapalapa", "Operación",
                              activities[index % 3], "Piso", 10, "08:00", "09:00",
                              f"Persona {index % 10}", "Muertos", 1 if index % 3 == 0 else 0])
            path = output / "synthetic.xlsx"
            workbook.save(path)
            payload = m.parse_operations_excel(path, persist=False)
            assert len(payload["rows"]) == 2400
            m.OPS_FILE.write_text(m._safe_json_dump(payload), encoding="utf-8")
            m._clear_operations_caches(clear_meta_file=True)
            m.require_user = lambda *_: {"id": 1, "username": "Synthetic QA", "role": "superadmin",
                                          "real_role": "superadmin", "store": ""}
            with m.db() as connection:
                connection.execute("UPDATE stores SET project=1 WHERE name='Iztapalapa'")
            results = []
            with TestClient(server_entry.app) as client:
                for mode, value in (("day", "2026-10-01"), ("week", "2026-W40"),
                                    ("month", "2026-10"), ("year", "2026")):
                    url = f"/api/operations?compact=true&store=Iztapalapa&period_type={mode}&period_value={value}"
                    baseline = client.get(url, headers={"Cache-Control": "no-cache"})
                    baseline.raise_for_status()
                    assert baseline.json().get("available")
                    measurements = {}
                    for label, headers in (("uncached", {"Cache-Control": "no-cache"}), ("cached", {})):
                        client.get(url, headers=headers).raise_for_status()
                        durations = []
                        for _ in range(10):
                            started = time.perf_counter()
                            response = client.get(url, headers=headers)
                            durations.append((time.perf_counter() - started) * 1000)
                            response.raise_for_status()
                            assert response.json() == baseline.json(), "Numerical output changed"
                            if label == "cached":
                                assert response.headers.get("x-report-cache") == "HIT", "Real report did not use the cache"
                        measurements[label] = round(statistics.median(durations), 2)
                    results.append({"period": mode, "uncached_median_ms": measurements["uncached"],
                                    "cached_median_ms": measurements["cached"], "identical_json": True})
        print(json.dumps({"environment": "local synthetic; not physical devices or production capacity",
                          "operation_rows": 2400, "requests_per_mode": 10, "results": results},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
