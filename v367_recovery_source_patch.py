"""V367 · Rescate compatible de DEV PZS y diagnóstico de cobertura.

Evita reportar ceros sin avisar cuando falta la fuente de las hojas mensuales.
No lee Excel en una consulta ni recalcula conversiones históricas en cada petición.
Las reparaciones de reconocimiento sólo se aplican al siguiente procesamiento
de una base original (se conserva la publicada hasta validar la nueva).
"""
from __future__ import annotations

import re

_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def install(m):
    if getattr(m, "_V367_RECOVERY_SOURCE", False):
        return

    old_monthly_name = m._monthly_sheet_name

    def month_sheet(name):
        if old_monthly_name(name):
            return True
        clean = m.normalize_col(name)
        has_month = any(re.search(r"(?<![a-z])" + month + r"(?![a-z])", clean)
                        for month in _MONTHS)
        # Hoja con año distinto de 2026, o simplemente "Octubre".
        return bool(has_month and (
            re.search(r"(?<!\d)20\d{2}(?!\d)", clean)
            or clean.strip() in _MONTHS
        ))

    m._monthly_sheet_name = month_sheet

    original_xml_rows = m._xlsx_monthly_rows

    def monthly_rows_with_dates_from_second_header(archive, member, shared_value):
        # El detector V376+ busca las fechas en las filas reales, aunque no
        # estén en la primera línea. No fusionar la segunda fila con la primera:
        # hacerlo destruye la evidencia necesaria para validar el encabezado.
        yield from original_xml_rows(archive, member, shared_value)

    m._xlsx_monthly_rows = monthly_rows_with_dates_from_second_header

    original_fifo = m._get_recovery_fifo_rows
    fallback = {"key": None, "result": None}

    def fifo_with_legacy_fallback(data):
        rows = original_fifo(data)
        if rows:
            return rows
        daily = data.get("commercial_daily")
        # Las bases antiguas pueden guardar movimientos diarios y un FIFO [].
        # No calculamos sobre listas enormes durante una petición del usuario.
        if not isinstance(daily, list) or not daily or len(daily) > 50000:
            return rows
        marker = (id(data), len(daily), id(daily))
        if fallback["key"] == marker:
            return fallback["result"]
        try:
            recovered = m._build_recovery_fifo_rows(daily)
        except Exception as exc:
            print(f"[V367] FIFO legado no reconstruido: {type(exc).__name__}: {exc}", flush=True)
            return rows
        fallback["key"] = marker
        fallback["result"] = recovered
        return recovered

    m._get_recovery_fifo_rows = fifo_with_legacy_fallback

    previous_operations = m.operations

    def operations_with_recovery_status(*args, **kwargs):
        result = previous_operations(*args, **kwargs)
        if not isinstance(result, dict):
            return result
        out = dict(result)
        meta = dict(out.get("recovery_source") or {})
        sheets = list(out.get("monthly_sheets") or [])
        errors = list(out.get("parse_errors") or [])
        source = m.load_ops()
        fifo = m._get_recovery_fifo_rows(source)
        source_ready = bool(fifo)
        dev = sum(float(row.get("dev_pzs") or 0) for row in out.get("recovery_by_store") or [])
        issue = any(
            "no se detectaron fechas diarias" in str(error).lower()
            or "hoja no encontrada" in str(error).lower()
            for error in errors
        )
        warning = ""
        if not sheets:
            warning = ("La base publicada no incluye hojas mensuales reconocidas. "
                       "Las Dev Pzs y la recuperación no cuentan con fuente diaria.")
        elif issue:
            warning = ("La lectura de fechas diarias falló en hojas mensuales. "
                       "Revisa los errores de procesamiento al cargar la base.")
        elif not source_ready:
            warning = ("La base publicada no contiene lotes diarios de devolución "
                       "para calcular Dev Pzs y recuperación. Verifica y reprocesa "
                       "el archivo vigente desde Carga de datos.")
        elif dev == 0 and out.get("period_value"):
            warning = (
                f"El periodo {out.get('period_value')} no registra DEV en los lotes publicados. "
                "Si el Excel original contiene devoluciones en estas fechas, "
                "reprocesa DEV para reconstruir el reporte."
            )
        meta.update({
            "recognized_monthly_sheets": len(sheets),
            "source_ready": source_ready,
            "period_dev_pzs": dev,
            "source_warning": warning,
        })
        out["recovery_source"] = meta
        return out

    m.operations = operations_with_recovery_status
    m._V367_RECOVERY_SOURCE = True
    print("[V367] Lectura mensual ampliada y diagnóstico DEV instalado", flush=True)
