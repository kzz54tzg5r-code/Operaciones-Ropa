"""V110: integra Resultados por Checklist y nombres de descarga operativa.

Objetivos:
- reconocer la hoja nueva "Resultados por Checklist" junto con las hojas
  históricas "Resultados productividad";
- conservar la lógica existente de Ingreso/Recolección, Acondicionado, Ubicado
  y Recorridos, evitando perder filas válidas al consolidar varias hojas;
- forzar una sola relectura del Excel persistente cuando éste ya contiene la
  hoja nueva pero la base JSON fue creada con un parser anterior;
- nombrar los PDF operativos con reporte + periodo, por ejemplo
  Operacion_Diaria_09.09.26.pdf.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
import threading
import time
import unicodedata


def _plain(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^0-9A-Za-z]+", "_", text).strip("_")
    return text or "Reporte"


def _date_suffix(period_type: str, period_value: str) -> str:
    ptype = str(period_type or "").lower().strip()
    value = str(period_value or "").strip()

    # Día: el valor del filtro es la fecha de corte. Si por alguna razón llega
    # vacío, usar el corte operativo estándar: día anterior en México.
    if ptype == "day":
        try:
            dt = datetime.strptime(value[:10], "%Y-%m-%d")
        except Exception:
            dt = datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=1)
        return dt.strftime("%d.%m.%y")

    # Semana ISO, por ejemplo 2026-W37 -> S37_2026.
    if ptype == "week":
        match = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, flags=re.I)
        if match:
            return f"S{int(match.group(2)):02d}_{match.group(1)}"

    # Mes, por ejemplo 2026-09 -> 09.2026.
    if ptype == "month":
        match = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
        if match:
            return f"{int(match.group(2)):02d}.{match.group(1)}"

    # Para reportes flexibles, conservar el periodo real siempre que venga en
    # un formato conocido. En ausencia de periodo se identifica con el corte
    # del día anterior para que la descarga nunca sea genérica.
    try:
        dt = datetime.strptime(value[:10], "%Y-%m-%d")
        return dt.strftime("%d.%m.%y")
    except Exception:
        pass
    match = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, flags=re.I)
    if match:
        return f"S{int(match.group(2)):02d}_{match.group(1)}"
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
    if match:
        return f"{int(match.group(2)):02d}.{match.group(1)}"
    return (datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=1)).strftime("%d.%m.%y")


def _download_basename(report: str, period_type: str, period_value: str) -> str:
    names = {
        "Centro Ejecutivo": "Centro_Ejecutivo",
        "Operación Diaria": "Operacion_Diaria",
        "Reporte Semanal": "Operacion_Semanal",
        "Reporte Mensual": "Operacion_Mensual",
        "Conversión": "Conversion",
        "Recuperación Económica": "Recuperacion_Economica",
        "Productividad por Colaborador": "Productividad",
        "Productividad por Actividad": "Productividad_Actividad",
        "Eficiencia Operativa": "Eficiencia_Operativa",
        "Cumplimiento de Recorridos": "Recorridos",
        "Indicadores Diarios": "Indicadores_Diarios",
        "Ranking de Tiendas": "Ranking_Tiendas",
        "Ranking de Colaboradores": "Ranking_Colaboradores",
        "Índice Integral": "Indice_Integral",
        "Alertas Inteligentes": "Alertas",
    }
    prefix = names.get(str(report or "").strip(), _plain(report))
    return f"{prefix}_{_date_suffix(period_type, period_value)}"


def install(m):
    if getattr(m, "_V110_OPERATIONAL_CHECKLIST", False):
        return

    old_detector = m._detect_operational_sheets

    def detect_operational_sheets(names):
        """Incluye hojas históricas y el nuevo resultado del checklist."""
        out = []
        for name in names or []:
            key = m.normalize_col(name)
            is_productivity = (
                key.startswith("resultados productividad")
                or key.startswith("resultados de productividad")
            )
            is_checklist = (
                key.startswith("resultados por checklist")
                or key.startswith("resultados checklist")
                or key.startswith("resultados por check list")
                or (key.startswith("resultados") and ("checklist" in key or "check list" in key))
            )
            if is_productivity or is_checklist:
                out.append(name)
        return out

    m._detect_operational_sheets = detect_operational_sheets
    # Hace que cualquier carga nueva quede identificada con la versión V110 y
    # permite reparar el Excel persistente que había sido publicado antes.
    try:
        m.OPERATIONS_PARSER_VERSION = max(int(getattr(m, "OPERATIONS_PARSER_VERSION", 0) or 0), 110)
    except Exception:
        m.OPERATIONS_PARSER_VERSION = 110

    @m.app.middleware("http")
    async def _v110_download_filename(request, call_next):
        response = await call_next(request)
        if (
            request.url.path == "/api/export/operations"
            and response.status_code < 400
            and str(request.query_params.get("format") or "").lower() == "pdf"
        ):
            report = request.query_params.get("report") or "Reporte"
            ptype = request.query_params.get("period_type") or ""
            pvalue = request.query_params.get("period_value") or ""
            basename = _download_basename(report, ptype, pvalue)
            response.headers["Content-Disposition"] = f'attachment; filename="{basename}.pdf"'
            response.headers["X-Operations-Report-Version"] = "V110"
        return response

    @m.app.on_event("startup")
    def _schedule_checklist_reparse():
        def worker():
            # V109 repara PDF comerciales a los 7 s. Darle prioridad evita que
            # dos procesos pesados compitan por memoria en Render.
            time.sleep(75)
            try:
                raw = m.DATA_ROOT / "cambios_muertos_actual.xlsx"
                if not raw.exists():
                    print("[V110-OPS] Sin Excel operativo persistente; no hay nada que reparar.", flush=True)
                    return

                names = []
                try:
                    with m._xlsx_stream_book(raw) as book:
                        names = list(book.get("sheet_paths") or [])
                except Exception as exc:
                    print(f"[V110-OPS] No se pudo inspeccionar hojas: {type(exc).__name__}: {exc}", flush=True)
                    return

                old_names = set(old_detector(names) or [])
                new_names = detect_operational_sheets(names)
                extra = [name for name in new_names if name not in old_names]
                if not extra:
                    print(
                        "[V110-OPS] Excel vigente no contiene hojas Checklist nuevas; "
                        "las próximas cargas usarán V110.",
                        flush=True,
                    )
                    return

                current = m.load_ops() or {}
                if int(current.get("parser_version") or 0) >= 110:
                    print("[V110-OPS] Base operativa ya está procesada con V110.", flush=True)
                    return

                print(
                    f"[V110-OPS] Reprocesando Excel vigente para integrar: {', '.join(extra)}",
                    flush=True,
                )
                m._ensure_operations_parser_current()
                meta = m.load_operations_meta() or {}
                dates = list(meta.get("available_dates") or [])
                print(
                    f"[V110-OPS] Reproceso terminado · parser={meta.get('parser_version')} · "
                    f"hojas={', '.join(meta.get('operational_sheets') or [])} · "
                    f"última fecha={dates[-1] if dates else 'sin fecha'}",
                    flush=True,
                )
            except Exception as exc:
                print(f"[V110-OPS] ERROR reparando base vigente: {type(exc).__name__}: {exc}", flush=True)

        threading.Thread(target=worker, daemon=True, name="v110-operational-checklist-reparse").start()

    # Autoprueba con la estructura exacta visible en Resultados por Checklist.
    try:
        detected = detect_operational_sheets([
            "Resultados productividad",
            "Resultados productividad 2",
            "Resultados por Checklist",
            "Septiembre 26",
        ])
        assert "Resultados por Checklist" in detected

        headers = [
            "Occurrence", "Fecha", "Ubicación", "Tabla", "Nómina",
            "Actividad Realizada", "Ingreso al area de acondicionado",
            "Número de piezas", "Hora Inicio", "Hora Fin", "Recorrido",
        ]
        missing = [h for h in headers if not m._operational_canonical_header(h)]
        assert not missing, f"encabezados sin reconocer: {missing}"

        # Muestra Arco Norte visible en la evidencia: valida que el motivo de
        # Ubicado/Acondicionado no se sume otra vez como ingreso.
        samples = [
            ("Clasificado", "Muertos", 275),
            ("Acondicionado", "Muertos", 128),
            ("Ubicado", "Muertos", 128),
            ("Acondicionado", "Muertos", 117),
            ("Ubicado", "Muertos", 117),
            ("Ingreso", "Muertos", 50),
            ("Ingreso", "Muertos", 13),
            ("Ingreso", "Muertos", 50),
            ("Recolección de muertos", "Muertos", 15),
            ("Recolección de muertos", "Cajas", 20),
            ("Acondicionado", "Muertos", 90),
            ("Ubicado", "Muertos", 90),
            ("Ubicado", "Muertos", 500),
            ("Acondicionado", "Muertos", 182),
            ("Clasificado", "Muertos", 50),
            ("Clasificado", "Muertos", 38),
            ("Acondicionado", "Muertos", 238),
        ]
        totals = {"muertos": 0.0, "cajas": 0.0, "ingresos": 0.0, "acondicionado": 0.0, "ubicado": 0.0}
        for activity_raw, reason, pieces in samples:
            activity = m._activity_class(activity_raw)
            is_input = activity == "Recolección de muertos" or m.normalize_col(activity_raw) == "ingreso"
            motive = m._motive_class(reason) if is_input else "No aplica"
            if is_input:
                totals["ingresos"] += pieces
                if motive == "Muertos":
                    totals["muertos"] += pieces
                if motive == "Cajas":
                    totals["cajas"] += pieces
            if activity == "Acondicionado":
                totals["acondicionado"] += pieces
            if activity == "Ubicado":
                totals["ubicado"] += pieces
        assert totals == {
            "muertos": 128.0,
            "cajas": 20.0,
            "ingresos": 148.0,
            "acondicionado": 755.0,
            "ubicado": 835.0,
        }, totals
        assert _download_basename("Operación Diaria", "day", "2026-09-09") == "Operacion_Diaria_09.09.26"
        print(
            "[V110-SELFTEST] Checklist + encabezados + clasificación + nombre PDF OK · "
            f"muestra Arco Norte={totals}",
            flush=True,
        )
    except Exception as exc:
        print(f"[V110-SELFTEST] ERROR: {type(exc).__name__}: {exc}", flush=True)

    m._V110_OPERATIONAL_CHECKLIST = True
    print(
        "[V110] Resultados por Checklist habilitado; PDF operativo usa reporte + fecha/periodo.",
        flush=True,
    )
