"""V370 · Evita la pérdida silenciosa de DEV por tiendas ausentes.

La hoja Octubre utiliza el mismo formato de ventas que las demás:
Z=tienda, AA/AB/AC=totales, AD/AE/AF y siguientes=ventas/dev/importe
por día. El parser anterior omitía filas cuyo Z estaba vacío; ahora la
carga falla explícitamente antes de publicar si hay movimientos sin tienda.
No rellena nombres, no cambia ventas ni fórmulas y no toca datos publicados.
"""
from __future__ import annotations

import math
import re


class MonthlyStoreMissingError(ValueError):
    """Movimiento de venta o devolución sin tienda en la hoja mensual."""


def _positive_number(value):
    try:
        n = float(value)
        return bool(math.isfinite(n) and n != 0)
    except (ValueError, TypeError, OverflowError):
        return False


def _missing_store_with_movements(row):
    """Señala exclusivamente artículos con movimiento que carecen de tienda.

    No confunde encabezados, separadores vacíos o filas sin SKU con artículos.
    Se comprueban totales AA:AC y todos los tríos diarios desde AD.
    """
    if not isinstance(row, dict) or not str(row.get(1) or "").strip():
        return False
    store = str(row.get(25) or "").strip().lower()
    if store not in ("", "nan", "none", "null", "0", "0.0", "n/a",
                     "sin tienda", "sin asignar", "no asignada"):
        return False
    return any(
        _positive_number(value)
        for col, value in row.items()
        if isinstance(col, int) and col >= 26
    )


def install(m):
    if getattr(m, "_V370_MONTHLY_STORE_GUARD", False):
        return

    previous_rows = m._xlsx_monthly_rows
    previous_stream = m._stream_monthly_recovery_fifo

    def verified_rows(archive, member, shared_value):
        for pos, row in enumerate(previous_rows(archive, member, shared_value), start=1):
            # Fila 1 = fechas, fila 2 = rótulos; las filas 3+ son productos.
            if pos >= 3 and _missing_store_with_movements(row):
                sku = str(row.get(1) or "")[:60]
                raise MonthlyStoreMissingError(
                    f"Tienda faltante (columna Z), fila {pos}, artículo {sku!r}. "
                    "Completa las tiendas como en las demás hojas de ventas "
                    "y vuelve a procesar el Excel."
                )
            yield row

    def verified_stream(path, sheets, stream_book=None):
        # El lector actual guarda por hoja cualquier error y continúa.
        # Convertimos estos errores críticos en bloqueo de publicación,
        # incluso si la omisión está en una sola hoja de 12 meses.
        result = previous_stream(path, sheets, stream_book)
        if len(result) < 4:
            return result
        errors = result[3] or []
        broken = [str(e) for e in errors if "Tienda faltante (columna Z)" in str(e)]
        if broken:
            raise ValueError(
                "Carga detenida: existen ventas o devoluciones sin tienda. "
                "La base vigente no se modificó. " + " | ".join(broken[:5])
            )
        return result

    m._xlsx_monthly_rows = verified_rows
    m._stream_monthly_recovery_fifo = verified_stream
    m._V370_MONTHLY_STORE_GUARD = True
    print("[V370] Validación de tienda Z en meses de ventas y DEV activa.", flush=True)
