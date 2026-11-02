"""Presentación de semanas ISO: 2026-W44 (interno) -> 2026-S44 (visible).

NO se transforma el valor de consulta o de almacenamiento: sólo etiquetas,
textos de PDF, rótulos o nombres de archivos exportados.
"""
from __future__ import annotations
import re

_ISO_WEEK=re.compile(r"(?<![A-Za-z0-9])((?:19|20)\d{2})-W([0-5]\d)(?![0-9])")
_SHORT_WEEK=re.compile(r"(?<![A-Za-z0-9])W([0-5]\d)(?![0-9])")


def format_week_label(value):
    """Conservar semana ISO semánticamente, cambiando sólo su prefijo visual."""
    text=str(value if value is not None else "")
    text=_ISO_WEEK.sub(r"\1-S\2",text)
    return _SHORT_WEEK.sub(r"S\1",text)
