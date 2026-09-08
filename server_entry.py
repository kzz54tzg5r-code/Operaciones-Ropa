"""Entrada de producción para Render.

Mantiene las optimizaciones y reportes validados hasta V96. V102 conserva el
selector clásico/interactivo anterior y V103 se aplica al final como capa de
interfaz reversible: barra compacta sticky, chips activos, panel "Más filtros"
y desglose interactivo dentro de las tablas.
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
# V103 debe ir al final: conserva V102 como respaldo y reemplaza visualmente
# su selector por la barra sticky con chips + Más filtros + drill-down.
_install_v103_compact_filter_bar_patch(web_app)
app = web_app.app
