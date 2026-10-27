"""V375 · Centro Operativo: tope 100% aplicado ANTES de agregar por tienda.

Conserva registros operativos, cantidad capturada y métricas crudas; sólo
produce un resumen independiente para las cuatro tarjetas y su matriz.
"""
from __future__ import annotations
import math


def _quantity(value):
    try:
        result = float(value or 0)
        return max(0.0, result) if math.isfinite(result) else 0.0
    except (ValueError, TypeError, OverflowError):
        return 0.0


def center_card_metrics(data):
    """Piezas computables = min(piezas registradas en actividad, ingresos de tienda).

    El consolidado suma los topes individuales, NO min(sum(actividad), sum(ingresos)).
    Así el exceso de unas tiendas no compensa el pendiente de otras.
    """
    source = data.get("metrics") or {}
    stores = data.get("stores") or []
    if not isinstance(source, dict):
        source = {}
    if not isinstance(stores, list):
        stores = []
    summary = dict(source)
    if not stores:
        for field in ("acondicionado", "ubicado", "pct_acondicionado",
                      "pct_ubicado", "pendiente_acondicionar", "pendiente_ubicar"):
            summary[field] = 0.0
        return summary

    incoming = conditioned = located = pending_condition = pending_location = 0.0
    for row in stores:
        if not isinstance(row, dict):
            continue
        amount = _quantity(row.get("total_pzs", row.get("ingresos", 0)))
        ac = min(_quantity(row.get("acondicionado")), amount)
        ub = min(_quantity(row.get("ubicado")), amount)
        incoming += amount
        conditioned += ac
        located += ub
        pending_condition += max(amount - ac, 0.0)
        pending_location += max(amount - ub, 0.0)

    summary["total_pzs"] = incoming
    summary["ingresos"] = incoming
    summary["acondicionado"] = conditioned
    summary["ubicado"] = located
    summary["pendiente_acondicionar"] = pending_condition
    summary["pendiente_ubicar"] = pending_location
    summary["pct_acondicionado"] = conditioned / incoming * 100.0 if incoming else 0.0
    summary["pct_ubicado"] = located / incoming * 100.0 if incoming else 0.0
    summary["pct_procesado"] = summary["pct_ubicado"]
    return summary
