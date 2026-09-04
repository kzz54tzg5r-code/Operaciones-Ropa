"""Entrada de producción para Render.

Carga la aplicación y aplica antes del startup las optimizaciones necesarias
para Render y, al final, la paridad funcional/visual validada en Python.
V93 compacta el PDF Diario, V94 aplica diseño/ceros rojos, V95 mantiene el
mismo criterio en web y V96 sincroniza el PDF de Centro Ejecutivo con el
reporte visible.
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
from v95_web_zero_red_fix import install as _install_v95_web_zero_red_fix
from v96_center_exec_pdf_patch import install as _install_v96_center_exec_pdf_patch

_install_render_memory_patch(web_app)
_install_september_date_patch(web_app)
_install_operations_diagnostic_patch(web_app)
_install_desktop_ui_patch(web_app)
_install_v87_operations_patch(web_app)
_install_v90_render_parity_patch(web_app)
_install_v93_daily_pdf_compact_patch(web_app)
_install_v94_zero_red_table_patch(web_app)
_install_v95_web_zero_red_fix(web_app)
# V96 queda al final porque sólo reemplaza el PDF de Centro Ejecutivo.
_install_v96_center_exec_pdf_patch(web_app)
app = web_app.app
