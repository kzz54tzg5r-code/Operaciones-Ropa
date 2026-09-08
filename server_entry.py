"""Entrada de producción para Render.

Mantiene las optimizaciones y reportes validados hasta V96. La V102 agrega,
como última capa de respuesta, el selector visible entre Filtro clásico y
Desglose interactivo dentro del mismo reporte. Las pruebas V97-V101 se retiran
del arranque para evitar que oculten o reubiquen el control nuevo.
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
from v102_final_filter_switch_patch import install as _install_v102_final_filter_switch_patch

_install_render_memory_patch(web_app)
_install_september_date_patch(web_app)
_install_operations_diagnostic_patch(web_app)
_install_desktop_ui_patch(web_app)
_install_v87_operations_patch(web_app)
_install_v90_render_parity_patch(web_app)
_install_v93_daily_pdf_compact_patch(web_app)
_install_v94_zero_red_table_patch(web_app)
_install_v95_web_zero_red_fix(web_app)
_install_v96_center_exec_pdf_patch(web_app)
# V102 debe ser la última capa para modificar el HTML final después de todas
# las correcciones visuales y de PDF ya validadas.
_install_v102_final_filter_switch_patch(web_app)
app = web_app.app
