"""Entrada de producción para Render.

Mantiene las optimizaciones y reportes validados hasta V108. V109 agrega en
Análisis Comercial > Macro el reporte ejecutivo de ventas Año vs Año pasado,
metas mensuales, tendencia gráfica y repara la carga/procesamiento de los PDF
de ventas mensuales. También reprocesa una sola vez el historial ya cargado
para que Macro quede listo sin esperar al primer clic. V110 incorpora la hoja
Resultados por Checklist al consolidado operativo y nombra cada PDF con su
reporte y fecha/periodo de corte. V111 ajusta Operación Diaria para mostrar
%Acondicionado y %Ubicado en tarjetas y sólo %Ubicado en la tabla. V112 repara
la API de ventas y V113 evita valores falsos. V114 inspecciona temporalmente el
layout real de Meta_ROPA_SEPTIEMBRE. V115 muestra Acondicionado y Ubicado en
piezas y porcentaje tanto en la tabla diaria como en su PDF. V116 hace que el
PDF Diario replique visualmente la pantalla. V117 unifica Día, Semanal y
Mensual: mismas tarjetas, mismo orden de detalle y misma identidad visual en PDF.
V119 sustituye V118 para evitar el congelamiento del navegador y consolida
Día, Semanal, Mensual y Anual dentro de Centro Operativo. V120 conserva la
estructura validada de Día/Semanal/Mensual y hace que únicamente cambie el filtro.
V121 agrega el indicador Operación, captura diaria, productividad por colaborador,
perfil Colaborador, cierre de día, acumulados y exportaciones sin modificar los
reportes validados de Centro Operativo. V122 hace que el Colaborador entre
directamente a Operación sin consultar módulos restringidos. V123 garantiza que
Operación permanezca visible. V124 corrige la API de Operación y la mueve como
módulo independiente al menú principal. V125 agrupa Colgado + Doblado como Origen
en la captura diaria y separa Captura, Productividad y Estándares en pestañas.
V126 restaura el Resumen ejecutivo/operativo como primera pestaña. V127 agrega
un demo visual temporal, sólo para Super Administrador, sin modificar datos reales.
V128 replica fielmente los bocetos aprobados en las cinco pestañas del demo.
"""
import web_app
from fastapi import Request as _FastAPIRequest
import v121_operation_indicator_patch as _v121_operation_module
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
from v107_portrait_recovery_chart_patch import install as _install_v107_portrait_recovery_chart_patch
from v108_project_mark_pdf_patch import install as _install_v108_project_mark_pdf_patch
from v109_macro_sales_patch import install as _install_v109_macro_sales_patch
from v109_sales_repair_startup import install as _install_v109_sales_repair_startup
from v110_operational_checklist_patch import install as _install_v110_operational_checklist_patch
from v111_daily_percent_fix import install as _install_v111_daily_percent_fix
from v112_sales_pdf_repair import install as _install_v112_sales_pdf_repair
from v113_sales_guard_patch import install as _install_v113_sales_guard_patch
from v114_sales_layout_probe import install as _install_v114_sales_layout_probe
from v115_daily_pieces_percent_patch import install as _install_v115_daily_pieces_percent_patch
from v116_reportlab_color_fix import install as _install_v116_reportlab_color_fix
from v116_daily_pdf_mirror_patch import install as _install_v116_daily_pdf_mirror_patch
from v117_operational_visual_parity_patch import install as _install_v117_operational_visual_parity_patch
from v119_centro_operativo_safe_annual_patch import install as _install_v119_centro_operativo_safe_annual_patch
from v120_centro_operativo_preserve_reports_patch import install as _install_v120_centro_operativo_preserve_reports_patch
from v121_operation_indicator_patch import install as _install_v121_operation_indicator_patch
from v122_collaborator_entry_patch import install as _install_v122_collaborator_entry_patch
from v123_operation_visibility_patch import install as _install_v123_operation_visibility_patch
from v124_operation_main_module_patch import install as _install_v124_operation_main_module_patch
from v125_operation_tabs_patch import install as _install_v125_operation_tabs_patch
from v126_operation_summary_patch import install as _install_v126_operation_summary_patch
from v127_operation_demo_dashboard_patch import install as _install_v127_operation_demo_dashboard_patch
from v128_operation_demo_exact_patch import install as _install_v128_operation_demo_exact_patch

# FastAPI resuelve las anotaciones diferidas de V121 contra los globales del
# módulo. Sin este enlace, `request: Request` se interpretaba como parámetro de
# consulta y /api/operation/meta respondía 422.
_v121_operation_module.Request = _FastAPIRequest

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
_install_v106_pdf_selftest_patch(web_app)
_install_v107_portrait_recovery_chart_patch(web_app)
_install_v108_project_mark_pdf_patch(web_app)
_install_v109_macro_sales_patch(web_app)
_install_v109_sales_repair_startup(web_app)
_install_v110_operational_checklist_patch(web_app)
_install_v111_daily_percent_fix(web_app)
_install_v112_sales_pdf_repair(web_app)
_install_v113_sales_guard_patch(web_app)
_install_v114_sales_layout_probe(web_app)
_install_v115_daily_pieces_percent_patch(web_app)
_install_v116_reportlab_color_fix(web_app)
_install_v116_daily_pdf_mirror_patch(web_app)
_install_v117_operational_visual_parity_patch(web_app)
_install_v119_centro_operativo_safe_annual_patch(web_app)
# V120 mantiene los reportes validados de Centro Operativo.
_install_v120_centro_operativo_preserve_reports_patch(web_app)
# V121 agrega Operación y perfil Colaborador.
_install_v121_operation_indicator_patch(web_app)
# V122 evita que Colaborador atraviese Centro Operativo durante el inicio.
_install_v122_collaborator_entry_patch(web_app)
# V123 conserva compatibilidad de la vista Operación.
_install_v123_operation_visibility_patch(web_app)
# V124 la separa de Cambios y Muertos y la coloca en el menú principal.
_install_v124_operation_main_module_patch(web_app)
# V125 organiza Operación en pestañas y simplifica la captura diaria.
_install_v125_operation_tabs_patch(web_app)
# V126 devuelve el Resumen como primera pestaña del módulo Operación.
_install_v126_operation_summary_patch(web_app)
# V127 activa el demo visual temporal sólo para Super Administrador.
_install_v127_operation_demo_dashboard_patch(web_app)
# V128 replica los cinco bocetos aprobados sin escribir datos reales.
_install_v128_operation_demo_exact_patch(web_app)
app = web_app.app
