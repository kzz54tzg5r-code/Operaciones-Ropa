"""Reconoce fechas y métricas de la matriz diaria dentro de hojas mensuales.

AA:AC son totales. Desde AD se agrupan 3 columnas por día: ventas netas
en piezas, devoluciones en piezas y venta neta en pesos. En el Excel la
fecha es la fila 1 y la métrica es la fila 2.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
import math
import re
import unicodedata


def _text(value):
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(ascii_value.replace("_", " ").split())


def _metric(value):
    text = _text(value)
    words = re.sub(r"[^a-z0-9$]+", " ", text)
    if ("dev" in words or "devol" in words) and re.search(r"\b(pz|pzs|pza|pzas|pieza|piezas)\b", words):
        return "dev"
    if ("venta" in words or "vta" in words) and ("$" in words or "importe" in words or "monto" in words or "pesos" in words):
        return "value"
    if ("venta" in words or "vta" in words) and re.search(r"\b(pz|pzs|pza|pzas|pieza|piezas)\b", words):
        return "sales"
    return ""


def _date_iso(value):
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, (float, int)) and not isinstance(value, bool):
        if not math.isfinite(float(value)) or not (20000 <= value <= 100000):
            return None
        parsed = (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
    else:
        text = str(value or "").strip()
        if not text:
            return None
        match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
        if match:
            try:
                parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                return None
        else:
            match = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?$", text)
            if not match:
                return None
            try:
                parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                return None
    iso = parsed.isocalendar()
    return parsed.isoformat(), int(iso.week), int(iso.year), parsed.strftime("%Y-%m")


def resolve_daily_groups(dates_row, metrics_row, first_daily_index=29):
    """Lista de (columna, fecha ISO, semana ISO, año ISO, mes); y advertencias.

    Se usan conjuntamente fechas y etiquetas, nunca únicamente la posición.
    Admite fechas repetidas sobre las tres columnas o una celda combinada.
    """
    last = max([first_daily_index - 1, *dates_row.keys(), *metrics_row.keys()])
    groups, warnings = [], []
    for start in range(first_daily_index, last + 1, 3):
        fields = [_metric(metrics_row.get(start + offset)) for offset in range(3)]
        values = [dates_row.get(start + offset) for offset in range(3)]
        dates = [_date_iso(value) for value in values]
        date_values = [item for item in dates if item is not None]
        if not date_values:
            if any(fields):
                warnings.append(f"Columnas {start + 1}-{start + 3}: indicadores sin fecha válida")
            continue
        if len({item[0] for item in date_values}) != 1:
            warnings.append(f"Columnas {start + 1}-{start + 3}: fechas diferentes dentro del mismo día")
            continue
        if fields != ["sales", "dev", "value"]:
            warnings.append(f"Columnas {start + 1}-{start + 3}: orden inválido de indicadores {fields}")
            continue
        groups.append((start, *date_values[0]))
    if len({group[1] for group in groups}) != len(groups):
        warnings.append("La misma fecha aparece más de una vez en los grupos diarios")
        unique = {}
        for group in groups:
            unique.setdefault(group[1], group)
        groups = list(unique.values())
    return groups, warnings
