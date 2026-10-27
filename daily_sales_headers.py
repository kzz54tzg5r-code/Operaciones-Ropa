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
    """Reconoce encabezados de ventas y DEV con variaciones de la plantilla."""
    text = _text(value)
    words = re.sub(r"[^a-z0-9$]+", " ", text)
    tokens = set(words.split())
    piece = bool(tokens.intersection({"pz", "pzs", "pza", "pzas", "pieza", "piezas"}))
    returns = any(x in text for x in ("dev", "devol", "cambio"))
    sales = any(x in text for x in ("venta", "vta"))
    currency = "$" in text or any(x in text for x in ("importe", "monto", "peso", "mxn"))
    if returns and piece:
        return "dev"
    if sales and currency and not piece:
        return "value"
    if sales and piece and not currency:
        return "sales"
    return ""


_MONTH_NAMES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3, "abr": 4, "abril": 4,
    "may": 5, "mayo": 5, "jun": 6, "junio": 6,
    "jul": 7, "julio": 7, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "septiembre": 9, "setiembre": 9,
    "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}


def _year(value):
    year = int(value)
    return 2000 + year if 0 <= year < 100 else year


def _date_iso(value):
    """Fecha visible de Excel: serial, ISO, dd/mm/aa o dd-mes-aa.

    Nunca infiere días ni intercambia ventas con devoluciones.
    """
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, (float, int)) and not isinstance(value, bool):
        if not math.isfinite(float(value)) or not (20000 <= value <= 100000):
            return None
        parsed = (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
    else:
        text = _text(value).strip()
        if not text:
            return None
        parsed = None
        # La hoja puede traer '01/04/26', '01-abr-26', '1 de abril de 2026'
        # o una fecha ISO con hora. Se interpretan únicamente valores explícitos.
        match = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ t].*)?", text)
        if match:
            try:
                parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                return None
        else:
            match = re.fullmatch(r"(\d{1,2})[-/. ]+(?:de[ ]+)?([a-z]+|\d{1,2})[-/. ]+(?:de[ ]+)?(\d{2}|\d{4})(?:[ ]+.*)?", text)
            if match:
                try:
                    raw_month = match.group(2)
                    month = _MONTH_NAMES.get(raw_month) if raw_month.isalpha() else int(raw_month)
                    if month is not None:
                        parsed = date(_year(match.group(3)), int(month), int(match.group(1)))
                except ValueError:
                    return None
        if parsed is None:
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

def locate_daily_headers(header_rows, first_daily_index=29):
    """Identifica dos filas consecutivas de fechas + métricas.

    No da por hecho que sean físicamente filas 1 y 2. Devuelve el índice
    de la segunda cabecera para no descartar ni duplicar filas de datos.
    """
    best = ([], ["No se encontraron fechas y encabezados diarios"], 1)
    for idx in range(max(len(header_rows) - 1, 0)):
        columns, warnings = resolve_daily_groups(
            header_rows[idx], header_rows[idx + 1], first_daily_index
        )
        if len(columns) > len(best[0]) or (
            len(columns) == len(best[0]) and len(warnings) < len(best[1])
        ):
            best = (columns, warnings, idx + 1)
    return best
