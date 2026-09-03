"""Entrada de producción para Render.

Carga la aplicación y aplica antes del startup el parche de memoria del FIFO.
Así las cargas grandes conservan el cálculo por SKU/color, pero el payload final
queda consolidado por tienda-día y no rebasa el límite de memoria del servicio.
"""
import web_app
from render_memory_patch import install as _install_render_memory_patch

_install_render_memory_patch(web_app)
app = web_app.app
