"""Ajustes de paridad visual para la versión web de Operaciones Ropa.

Replica en la aplicación FastAPI el comportamiento estable del menú lateral
que ya tenía la versión Python/Streamlit: permanece completo en pantalla al
hacer scroll y conserva el botón para contraer/expandir. En móvil no toca la
barra inferior ni la navegación responsive existente.
"""
from __future__ import annotations

from pathlib import Path


_PATCH_MARKER = "V49_FIXED_DESKTOP_SIDEBAR"


_DESKTOP_CSS = r"""

/* ============================================================
   V49_FIXED_DESKTOP_SIDEBAR
   Escritorio: menú completo, fijo y siempre desplegable/colapsable.
   Móvil conserva la navegación inferior V47/V48.
   ============================================================ */
@media (min-width: 901px) {
  html, body {
    min-height: 100%;
    overflow-x: hidden;
  }

  .shell {
    display: block !important;
    min-height: 100vh !important;
  }

  .side {
    display: flex !important;
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    bottom: 0 !important;
    width: 218px !important;
    height: 100dvh !important;
    min-height: 100vh !important;
    z-index: 1000 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    background: #fff !important;
  }

  .main {
    margin-left: 218px !important;
    width: calc(100% - 218px) !important;
    min-width: 0 !important;
    min-height: 100vh !important;
  }

  .shell.sidebar-collapsed .side {
    width: 72px !important;
  }

  .shell.sidebar-collapsed .main {
    margin-left: 72px !important;
    width: calc(100% - 72px) !important;
  }

  .sidebar-toggle {
    position: sticky !important;
    top: 7px !important;
    z-index: 5 !important;
    flex: 0 0 auto !important;
    background: #fff !important;
  }

  .sidebrand,
  .group,
  .nav {
    flex: 0 0 auto !important;
  }

  .profile {
    margin-top: auto !important;
    flex: 0 0 auto !important;
    background: #fff !important;
    padding-bottom: 10px !important;
  }

  /* Cuando la altura es reducida, sólo se desplaza el propio menú lateral. */
  @media (max-height: 700px) {
    .side {
      padding-top: 8px !important;
      padding-bottom: 8px !important;
    }
    .sidebrand {
      padding-bottom: 8px !important;
    }
    .nav {
      padding-top: 8px !important;
      padding-bottom: 8px !important;
    }
  }
}
"""


def install(module) -> None:
    """Inyecta el ajuste de escritorio en el HTML servido por la app."""
    if getattr(module, "_V49_DESKTOP_UI_PATCH", False):
        return

    web_dir = Path(getattr(module, "WEB"))
    index_path = web_dir / "index.html"
    if not index_path.exists():
        print("[V49-UI] No se encontró web/index.html; no se aplicó el parche.", flush=True)
        return

    try:
        html = index_path.read_text(encoding="utf-8")
        if _PATCH_MARKER not in html:
            if "</style>" not in html:
                raise RuntimeError("No se encontró </style> en web/index.html")
            html = html.replace("</style>", _DESKTOP_CSS + "\n</style>", 1)

        # Indicador visible para confirmar que la interfaz nueva está activa.
        html = html.replace("V47 · versión móvil", "V49 · menú fijo + móvil")
        html = html.replace("V47 · Móvil · Excel capacidades", "V49 · Menú fijo · Excel capacidades")
        html = html.replace("V47 móvil listo para recibir archivos.", "V49 · menú fijo y móvil listo para recibir archivos.")

        index_path.write_text(html, encoding="utf-8")
        module._V49_DESKTOP_UI_PATCH = True
        print("[V49-UI] Menú lateral fijo, completo y colapsable instalado.", flush=True)
    except Exception as exc:
        print(f"[V49-UI] No se pudo instalar: {type(exc).__name__}: {exc}", flush=True)
