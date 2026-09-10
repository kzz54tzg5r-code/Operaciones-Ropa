"""Compatibilidad mínima para V116: ReportLab HexColor acepta 'white'."""
from __future__ import annotations


def install(m):
    try:
        from reportlab.lib import colors
        if getattr(colors, "_V116_SAFE_HEX", False):
            return
        original = colors.HexColor

        def safe_hex(value, *args, **kwargs):
            if isinstance(value, str):
                key = value.strip().lower()
                named = {
                    "white": colors.white,
                    "black": colors.black,
                    "red": colors.red,
                    "green": colors.green,
                    "blue": colors.blue,
                }
                if key in named:
                    return named[key]
            return original(value, *args, **kwargs)

        colors.HexColor = safe_hex
        colors._V116_SAFE_HEX = True
        print("[V116-FIX] ReportLab acepta colores nominales para PDF espejo.", flush=True)
    except Exception as exc:
        print(f"[V116-FIX] ERROR: {type(exc).__name__}: {exc}", flush=True)
