"""Entrada de producción para Render.

Carga la aplicación y aplica antes del startup los parches de memoria, fechas,
diagnóstico y reglas operativas V87 sobre la base persistente vigente.
"""
import web_app
from render_memory_patch import install as _install_render_memory_patch
from september_date_patch import install as _install_september_date_patch
from operations_diagnostic_patch import install as _install_operations_diagnostic_patch
from v87_operations_patch import install as _install_v87_operations_patch

_install_render_memory_patch(web_app)
_install_september_date_patch(web_app)
_install_operations_diagnostic_patch(web_app)
_install_v87_operations_patch(web_app)
app = web_app.app
