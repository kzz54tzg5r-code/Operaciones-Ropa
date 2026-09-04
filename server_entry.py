"""Entrada de producción para Render.

Carga la aplicación y aplica antes del startup las optimizaciones necesarias
para Render y, al final, la paridad funcional/visual V89-V90 validada en la
versión Python. Así se conserva la carga de archivos grandes sin perder Pend.
Ant., Total pzs, vistas del Super Administrador ni los PDF espejo.
"""
import web_app
from render_memory_patch import install as _install_render_memory_patch
from september_date_patch import install as _install_september_date_patch
from operations_diagnostic_patch import install as _install_operations_diagnostic_patch
from desktop_ui_patch import install as _install_desktop_ui_patch
from v87_operations_patch import install as _install_v87_operations_patch
from v90_render_parity_patch import install as _install_v90_render_parity_patch

_install_render_memory_patch(web_app)
_install_september_date_patch(web_app)
_install_operations_diagnostic_patch(web_app)
_install_desktop_ui_patch(web_app)
_install_v87_operations_patch(web_app)
# V90 debe ser el último parche: parte de la respuesta V87 ya optimizada y
# restaura exactamente el corte diario D-1, menú/roles y exportaciones PDF.
_install_v90_render_parity_patch(web_app)
app = web_app.app
