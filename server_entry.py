"""Entrada de producción para Render.

Mantiene las optimizaciones y reportes validados hasta V96. V103 aporta la
barra compacta; V104 deja esa barra como única forma visible de filtrar y
mantiene el desglose por clic en tabla siempre activo. V105 replica en los PDF
Semanal y Mensual el lenguaje visual y la paginación compacta del PDF Diario.
V106 ejecuta una prueba de humo de ambos PDF al arrancar.
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
from v103_compact_filter_bar_patch import install as _install_v103_compact_filter_bar_patch
from v104_single_filter_patch import install as _install_v104_single_filter_patch
from v105_week_month_pdf_mirror_patch import install as _install_v105_week_month_pdf_mirror_patch
from v106_pdf_selftest_patch import install as _install_v106_pdf_selftest_patch

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
_install_v102_final_filter_switch_patch(web_app)
_install_v103_compact_filter_bar_patch(web_app)
_install_v104_single_filter_patch(web_app)
_install_v105_week_month_pdf_mirror_patch(web_app)
# La prueba se ejecuta después de instalar V105, sin modificar datos reales.
_install_v106_pdf_selftest_patch(web_app)
app = web_app.app
