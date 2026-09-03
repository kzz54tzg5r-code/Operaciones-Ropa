"""Entrada de producción para Render.

Carga la aplicación y aplica antes del startup los parches de memoria y fechas.
El primero evita picos de RAM durante Excel grandes; el segundo distingue
correctamente fechas ISO de dd/mm/yyyy y reprocesa el archivo ya persistido.
"""
import web_app
from render_memory_patch import install as _install_render_memory_patch
from september_date_patch import install as _install_september_date_patch

_install_render_memory_patch(web_app)
_install_september_date_patch(web_app)
app = web_app.app
