"""Entrada de producción para Render.

Carga la aplicación y aplica antes del startup las optimizaciones necesarias
para Render y, al final, la paridad funcional/visual validada en Python.
V93 compacta el PDF Diario y V94 unifica el diseño de la tabla con el reporte
web y marca en rojo los valores 0 hasta la columna Ubicado.
"""
import web_app
from render_memory_patch import install as _install_render_memory_patch
from september_date_patch import install as _install_september_date_patch
from operations_diagnostic_patch import install as _install_operations_diagnostic_patch
from desktop_ui_patch import install as _install_desktop_ui_patch
from v87_operations_patch import install as _install_v87_operations_patch
from v90_render_parity_patch import install as _install_v90_render_parity_patch
from v93_daily_pdf_compact_patch import install as _install_v93_daily_pdf_compact_patch
from v94_zero_red_table_patch import install as _install_v94_zero_red_table_patch

_install_render_memory_patch(web_app)
_install_september_date_patch(web_app)
_install_operations_diagnostic_patch(web_app)
_install_desktop_ui_patch(web_app)
_install_v87_operations_patch(web_app)
_install_v90_render_parity_patch(web_app)
_install_v93_daily_pdf_compact_patch(web_app)
# V94 se instala al final para que el mismo criterio visual quede en web y PDF.
_install_v94_zero_red_table_patch(web_app)
app = web_app.app
