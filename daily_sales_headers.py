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



_WEEKDAYS = r"(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)"
_DATE_TOKEN = re.compile(
    r"(?<!\d)(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|"
    r"\d{1,2}[-/. ]+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|"
    r"agosto|septiembre|setiembre|sept|octubre|noviembre|diciembre|"
    r"ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|\d{1,2})"
    r"[-/. ]+(?:de\s+)?\d{2,4})(?!\d)"
)

def _header_date(value):
    """Lee fechas Excel aun con día de la semana u hora como texto.

    Nunca deduce una fecha a partir del nombre de la hoja ni del número
    de columna: cada grupo exige un encabezado comprobable.
    """
    parsed = _date_iso(value)
    if parsed:
        return parsed
    if isinstance(value, str):
        raw = _text(value).strip()
        raw = re.sub(r"^" + _WEEKDAYS + r"[,]?\s+", "", raw)
        match = _DATE_TOKEN.search(raw)
        if match:
            return _date_iso(match.group(0))
    return None

def _header_description(rows, first_daily_index=29):
    """Ejemplos cortos para un error accionable, sin datos de artículos."""
    summaries = []
    for pos, row in enumerate(rows[:15], 1):
        candidates = []
        for col, value in row.items():
            if not isinstance(col, int) or col < first_daily_index or value in ("", None):
                continue
            kind = _metric(value)
            if kind or _header_date(value):
                candidates.append(f"{col + 1}:{str(value)[:38]}")
            if len(candidates) >= 4:
                break
        if candidates:
            summaries.append(f"fila {pos} [{', '.join(candidates)}]")
        if len(summaries) >= 4:
            break
    return "; ".join(summaries) or "sin encabezados diarios reconocibles en las primeras 15 filas"


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
        dates = [_header_date(value) for value in values]
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
    """Encuentra fechas y métricas incluso con títulos/filas separadoras.

    Prioriza una fila de métricas con un bloque repetido de Ventas/DEV/Pesos
    y verifica que las fechas precedan a la fila de métricas. No se inventan
    fechas ni se asume que el orden es correcto cuando la cabecera lo contradice.
    Devuelve índice base 0 de la fila de métricas para devolver las filas de
    datos al iterador de streaming exactamente una vez.
    """
    best_score = (-1, -999, -999)
    best = ([], [], 1)
    for metrics_idx in range(1, len(header_rows)):
        row = header_rows[metrics_idx]
        signal_count = sum(
            1 for col, value in row.items()
            if isinstance(col, int) and col >= first_daily_index and _metric(value)
        )
        if signal_count < 2:
            continue
        for dates_idx in range(0, metrics_idx):
            groups, warnings = resolve_daily_groups(
                header_rows[dates_idx], row, first_daily_index
            )
            score = (len(groups), -len(warnings), signal_count)
            if score > best_score:
                best_score = score
                best = (groups, warnings, metrics_idx)
    if best_score[0] > 0:
        return best

    # No hay grupos seguros: el diagnóstico debe explicar qué se detectó,
    # en vez de acusar indiscriminadamente a siete hojas del archivo.
    description = _header_description(header_rows, first_daily_index)
    return [], [f"No se encontró un bloque verificable de fecha + Ventas/DEV/Pesos: {description}"], 1


def infer_dated_groups_without_labels(header_rows, first_daily_index=29):
    """Rescate sólo cuando las fechas existen pero las etiquetas no son legibles.

    Nunca acepta un orden explícito contrario: si AD dice DEV, AE dice
    Ventas, o AF dice piezas, no se debe inferir que la posición sea correcta.
    El llamador DEBE además comprobar que la suma de AE coincide con AB
    antes de publicar el mes. Se utiliza exclusivamente si no hay grupos
    completos verificables mediante resolve_daily_groups().
    """
    last = max((col for row in header_rows for col in row.keys()
                if isinstance(col, int)), default=first_daily_index-1)
    best = ([], 0)
    best_score = (-1, -1, -999)
    expected = ("sales", "dev", "value")
    for date_idx, row in enumerate(header_rows[:18]):
        groups = []
        for start in range(first_daily_index, last + 1, 3):
            values = [_header_date(row.get(start + off)) for off in range(3)]
            dates = [value for value in values if value is not None]
            if len({item[0] for item in dates}) == 1 and dates:
                groups.append((start, *dates[0]))
        if not groups:
            continue
        # La fila de etiquetas puede estar varias líneas debajo de fechas.
        # Inspeccionar hasta encontrar primer artículo con B/Z ocupadas.
        following = header_rows[date_idx+1:18]
        first_data_idx = next(
            (date_idx + 1 + pos for pos, r in enumerate(following)
             if str(r.get(1) or "").strip() and str(r.get(25) or "").strip()
             and any(isinstance(k,int) and k>=26
                     and isinstance(v,(int,float)) and v!=0
                     for k,v in r.items())), None
        )
        before_data = first_data_idx if first_data_idx is not None else min(len(header_rows),date_idx+6)
        conflicting = False
        last_meta_idx = date_idx
        signals = 0
        for idx in range(date_idx + 1,before_data):
            candidate = header_rows[idx]
            for group in groups:
                start = group[0]
                fields = [_metric(candidate.get(start+off)) for off in range(3)]
                signals += sum(bool(v) for v in fields)
                if any(kind and kind != expected[off] for off,kind in enumerate(fields)):
                    conflicting = True
            if any(str(value or "").strip() for col,value in candidate.items()
                   if isinstance(col,int) and col >= first_daily_index):
                last_meta_idx = idx
        if conflicting:
            continue
        # Dos días consecutivos son una señal fuerte de la matriz mensual.
        # Un solo grupo también se acepta, pero sólo con el cotejo AB/AE.
        score = (len(groups),signals,-date_idx)
        if score > best_score:
            best_score = score
            best = (groups,last_meta_idx)
    groups, idx = best
    return groups, idx

def detect_monthly_layout(header_rows):
    """Return verified indices for both retail monthly workbook layouts.

    Legacy:  Z store, AB monthly DEV, AD:AF first daily triplet.
    Current: AA store, AC monthly DEV, AE:AG first daily triplet.

    All indices are zero-based. Never infer a shifted store/DEV column
    solely from the data, since that can interpret prices as quantities.
    """
    candidates = []
    for row in header_rows[:18]:
        for store_col in (25, 26):
            daily_col = store_col + 4
            dev_col = store_col + 2
            if _text(row.get(store_col)) not in ("tienda", "sucursal"):
                continue
            if _metric(row.get(dev_col)) != "dev":
                continue
            values = tuple(_metric(row.get(daily_col + offset)) for offset in range(3))
            if values != ("sales", "dev", "value"):
                # Explicit store + monthly DEV prevents silent guessed offsets.
                continue
            candidates.append({
                "store_col": store_col,
                "monthly_dev_col": dev_col,
                "first_daily_col": daily_col,
            })
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        unique = {(x["store_col"], x["first_daily_col"]) for x in candidates}
        if len(unique) == 1:
            return candidates[0]
        raise ValueError("Encabezados ambiguos: existen dos posiciones de Tienda y DEV distintas.")

    # Synthetic/older worksheets may lack the title of the store column,
    # but the daily labels still expose an unambiguous triple.
    patterns = []
    for row in header_rows[:18]:
        for daily_col in (29, 30):
            if tuple(_metric(row.get(daily_col + offset)) for offset in range(3)) == (
                "sales", "dev", "value"
            ):
                patterns.append(daily_col)
    starts = set(patterns)
    if len(starts) == 1:
        daily_col = starts.pop()
        return {
            "store_col": daily_col - 4,
            "monthly_dev_col": daily_col - 2,
            "first_daily_col": daily_col,
        }
    raise ValueError(
        "No fue posible identificar Tienda, Total DEV y el primer bloque diario. "
        "Se esperan los layouts Z/AB/AD o AA/AC/AE."
    )
