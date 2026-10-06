"""Entrada de producción para Render.

V166 reemplaza las capas visuales V164/V165 que usaban MutationObserver global.
Conserva V161 como filtro base y agrega una capa final estable para Vista
Día/Semanal/Mensual/Anual, roster de colaboradores, Matriz integrada a Recorridos,
Operación exclusiva de Origen, filtros comerciales uniformes, Estatus/MARCA real,
80/20 completo y reparación de meta/año anterior de Ventas.
V167 corrige iconografía y cierre de sesión, resalta la Matriz sobre promedio,
convierte Recorridos por día a tabla por tienda/fecha, agrega tendencias dinámicas
de 4 periodos, estabiliza Operación y agrega comparativos de venta con ranking,
diferencias contra Meta/año anterior y filtros Macro/Tiendas.
V168 compacta filtros internos, corrige 80/20 por alcance, estabiliza Operación,
reordena Recorridos por tienda/día, agrega comparación temporal y planeación de
la semana siguiente con devoluciones y error de pronóstico, recupera Acordeón
y lee el Resumen Ejecutivo rasterizado de los PDF de ventas mediante OCR.
V169 unifica los periodos disponibles de operación y conversión para no cortar Día en el 13.
"""
# V197 · Preflight de disco persistente.
# Render usa un disco de 1 GB y los catálogos normalizados son cachés
# reconstruibles. Si el disco se llena, SQLite ni siquiera puede iniciar.
# Esta limpieza ocurre ANTES de importar web_app y nunca toca Excel/PDF
# históricos, manifiestos, evidencias ni la base SQLite.
import json as _pre_json
import os as _pre_os
import time as _pre_time
from pathlib import Path as _PrePath

def _preflight_persistent_disk_cleanup():
    root=_PrePath(_pre_os.environ.get("OPERACIONES_ROPA_DATA") or "/var/data")
    if not root.exists():
        return
    removed=0
    freed=0

    def _unlink(path):
        nonlocal removed,freed
        try:
            if not path.is_file():
                return
            size=path.stat().st_size
            path.unlink(missing_ok=True)
            removed+=1
            freed+=size
        except Exception:
            pass

    # Preservar el cache normalizado de la capacidad vigente cuando se puede
    # identificar en el manifiesto. Todo lo demás aquí se puede regenerar.
    keep_prefix=""
    try:
        manifest_path=root/"commercial"/"manifest.json"
        payload=_pre_json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        caps=[x for x in (payload.get("capacities") or []) if str(x.get("status") or "").lower()=="procesado"]
        if caps:
            latest=max(caps,key=lambda x:str(x.get("uploaded_at") or x.get("created_at") or ""))
            cache_rel=str(latest.get("cache_file") or "").strip()
            if cache_rel:
                keep_prefix=_PrePath(cache_rel).stem
    except Exception:
        keep_prefix=""

    normalized=root/"capacity_normalized"
    if normalized.exists():
        files=sorted((p for p in normalized.glob("*.pkl") if p.is_file()),key=lambda p:p.stat().st_mtime,reverse=True)
        # Si el manifiesto no dice cuál es el vigente, conservar sólo el más reciente.
        newest_name=files[0].stem if files else ""
        for p in files:
            keep=bool(keep_prefix and p.name.startswith(keep_prefix))
            if not keep_prefix:
                keep=(p.stem==newest_name)
            if not keep:
                _unlink(p)

    # Cache comercial: siempre reconstruible desde las fuentes resguardadas.
    commercial_cache=root/"commercial"/"cache"
    if commercial_cache.exists():
        for p in commercial_cache.rglob("*"):
            if p.is_file():
                _unlink(p)

    # Temporales abandonados. Los jobs operativos grandes se conservan 24 h
    # para no interrumpir una carga reciente; después se pueden volver a subir
    # desde su histórico/origen si hubieran quedado huérfanos.
    staging=root/"staging"
    now=_pre_time.time()
    if staging.exists():
        for p in staging.iterdir():
            if not p.is_file():
                continue
            try:
                age=now-p.stat().st_mtime
            except Exception:
                age=0
            name=p.name.lower()
            disposable=(
                name.startswith("capacity_job_")
                or name.startswith("legacy_")
                or name.endswith(".worker.json")
                or name.endswith(".payload.json")
            )
            stale_ops=name.startswith("operations_job_") and age>24*3600
            stale_other=age>48*3600 and name.endswith((".tmp",".part"))
            if disposable or stale_ops or stale_other:
                _unlink(p)

    if removed:
        print(f"[V197-DISK] cachés/temporales eliminados={removed} · liberado={freed/1024/1024:.1f} MB",flush=True)

_preflight_persistent_disk_cleanup()

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
from v149_operation_summary_restore_patch import install as _install_v149_operation_summary_restore_patch
from v150_operations_endpoint_guard_patch import install as _install_v150_operations_endpoint_guard_patch
from v151_project_cards_scope_patch import install as _install_v151_project_cards_scope_patch
from v152_pdf_project_highlight_portrait_chart_patch import install as _install_v152_pdf_project_highlight_portrait_chart_patch
from v153_project_scope_backend_authoritative_patch import install as _install_v153_project_scope_backend_authoritative_patch
from v154_pdf_period_rules_patch import install_pre as _install_v154_pdf_period_pre, install_post as _install_v154_pdf_period_post
from v157_option1_boceto_filters_patch import install as _install_v157_option1_boceto_filters_patch
from v158_boceto_exact_filters_patch import install as _install_v158_boceto_exact_filters_patch
from v159_operation_store_staff_pending_patch import install as _install_v159_operation_store_staff_pending_patch
from v161_unified_boceto_filters_cards_patch import install as _install_v161_unified_boceto_filters_cards_patch
from v162_visual_parity_patch import install as _install_v162_visual_parity_patch
from v162_dynamic_headers_staff_patch import install as _install_v162_dynamic_headers_staff_patch
from v163_module_nav_cleanup_patch import install as _install_v163_module_nav_cleanup_patch
from v166_stability_roster_filters_patch import install as _install_v166_stability_roster_filters_patch
from v167_backend_patch import install as _install_v167_backend_patch
from v167_frontend_patch import install as _install_v167_frontend_patch
from v168_backend_patch import install as _install_v168_backend_patch
from v168_frontend_patch import install as _install_v168_frontend_patch
from v169_period_meta_patch import install as _install_v169_period_meta_patch
from v169_period_freshness_patch import install as _install_v169_period_freshness_patch
from v170_commercial_export_fix import install as _install_v170_commercial_export_fix
from v171_responsive_typography_patch import install as _install_v171_responsive_typography_patch
from v172_density_balance_patch import install as _install_v172_density_balance_patch
from v174_mobile_sales_repair_patch import install as _install_v174_mobile_sales_repair_patch
from v175_compact_filter_tabs_patch import install as _install_v175_compact_filter_tabs_patch
from v176_commercial_integral_patch import install as _install_v176_commercial_integral_patch
from v177_sellthrough_report_patch import install as _install_v177_sellthrough_report_patch
from v190_lingerie_checklist_patch import install as _install_v190_lingerie_checklist_patch
from v192_sellthrough_raw_rebuild import install as _install_v192_sellthrough_raw_rebuild
from v193_sellthrough_clean_ui import install as _install_v193_sellthrough_clean_ui
from pwa_patch import install as _install_pwa_patch
from v194_mobile_ui_final_patch import install as _install_v194_mobile_ui_final_patch
from v195_report_navigation_restore_patch import install as _install_v195_report_navigation_restore_patch
from v196_android_single_finger_scroll_patch import install as _install_v196_android_single_finger_scroll_patch
from v198_commercial_area_offer_patch import install as _install_v198_commercial_area_offer_patch
from v199_access_perf_productivity_patch import install as _install_v199_access_perf_productivity_patch
from v200_operation_tabs_timer_patch import install as _install_v200_operation_tabs_timer_patch
from v201_operation_sales_demo_patch import install as _install_v201_operation_sales_demo_patch
from v203_operation_option7_ui_patch import install as _install_v203_operation_option7_ui_patch
from v204_operation_productivity_ranking_patch import install as _install_v204_operation_productivity_ranking_patch
from v205_store_geofence_patch import install as _install_v205_store_geofence_patch
from v210_operational_standards_tenure_patch import install as _install_v210_operational_standards_tenure_patch
from v219_share_users_option3_patch import install as _install_v219_share_users_option3_patch
from v220_operation_tabs_single_line_patch import install as _install_v220_operation_tabs_single_line_patch
from v221_report_tabs_match_operation_patch import install as _install_v221_report_tabs_match_operation_patch
from v222_operation_capture_nav_admin_patch import install as _install_v222_operation_capture_nav_admin_patch
from v225_final_mobile_tab_rail_patch import install as _install_v225_final_mobile_tab_rail_patch
from v226_single_mobile_tab_rail_patch import install as _install_v226_single_mobile_tab_rail_patch
from v229_mobile_tabs_final_patch import install as _install_v229_mobile_tabs_final_patch
from v234_exact_mobile_tabs_patch import install as _install_v234_exact_mobile_tabs_patch
from v237_final_ui_patch import install as _install_v237_final_ui_patch
from v238_responsive_nav_patch import install as _install_v238_responsive_nav_patch
from v239_functional_close_patch import install as _install_v239_functional_close_patch
from v240_center_routes_calendar_patch import install as _install_v240_center_routes_calendar_patch
from v241_cm_capture_authoritative_patch import install as _install_v241_cm_capture_authoritative_patch
from v243_recovery_rate_patch import install as _install_v243_recovery_rate_patch
from v249_operational_filter_profiles_patch import install as _install_v249_operational_filter_profiles_patch
from v250_option9b_filters_patch import install as _install_v250_option9b_filters_patch
from v254_filters_final_patch import install as _install_v254_filters_final_patch
from v256_center_quick_view_restore_patch import install as _install_v256_center_quick_view_restore_patch
from v257_universal_period_filter_patch import install as _install_v257_universal_period_filter_patch
from v258_universal_filter_controller_patch import install as _install_v258_universal_filter_controller_patch
from v259_stable_report_filter_patch import install as _install_v259_stable_report_filter_patch
from v260_responsive_layout_patch import install as _install_v260_responsive_layout_patch
from v261_option9_commercial_auto_operational_filters_patch import install as _install_v261_option9_commercial_auto_operational_filters_patch
from v262_hide_filter_actions_patch import install as _install_v262_hide_filter_actions_patch
from v263_laptop_mobile_density_patch import install as _install_v263_laptop_mobile_density_patch
from v264_uniform_responsive_patch import install as _install_v264_uniform_responsive_patch
from v265_desktop_matrix_mobile_patch import install as _install_v265_desktop_matrix_mobile_patch
from v266_operational_period_authority_patch import install as _install_v266_operational_period_authority_patch
from v267_option7_monthly_table_patch import install as _install_v267_option7_monthly_table_patch
from v268_option10_kpis_patch import install as _install_v268_option10_kpis_patch
from v269_operation_option4_kpis_patch import install as _install_v269_operation_option4_kpis_patch
from v270_desktop_compact_responsive_authority_patch import install as _install_v270_desktop_compact_responsive_authority_patch
from v271_center_operativo_laptop_parity_patch import install as _install_v271_center_operativo_laptop_parity_patch
from v272_center_pdf_parity_patch import install as _install_v272_center_pdf_parity_patch
from v273_mobile_table_headers_patch import install as _install_v273_mobile_table_headers_patch
from v275_operation_ui_final_patch import install as _install_v275_operation_ui_final_patch
from v276_operation_ui_scroll_final_patch import install as _install_v276_operation_ui_scroll_final_patch
from v277_operation_kpis_final_patch import install as _install_v277_operation_kpis_final_patch
from v279_operation_bonus_cluster_patch import install as _install_v279_operation_bonus_cluster_patch
from v279_aisle_resupply_patch import install as _install_v279_aisle_resupply_patch
from v281_aisle_resupply_boceto_patch import install as _install_v281_aisle_resupply_boceto_patch
from v285_global_table_density_patch import install as _install_v285_global_table_density_patch
from v286_scroll_type_authority_patch import install as _install_v286_scroll_type_authority_patch
from v288_operation_daily_option5_patch import install as _install_v288_operation_daily_option5_patch

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
_install_v120_centro_operativo_preserve_reports_patch(web_app)
_install_v121_operation_indicator_patch(web_app)
_install_v122_collaborator_entry_patch(web_app)
_install_v123_operation_visibility_patch(web_app)
_install_v124_operation_main_module_patch(web_app)
_install_v125_operation_tabs_patch(web_app)
_install_v126_operation_summary_patch(web_app)

# Los demos V127/V128 no se instalan en producción.
_install_v149_operation_summary_restore_patch(web_app)
_install_v150_operations_endpoint_guard_patch(web_app)
_install_v151_project_cards_scope_patch(web_app)

_install_v154_pdf_period_pre(web_app)
_install_v152_pdf_project_highlight_portrait_chart_patch(web_app)
_install_v153_project_scope_backend_authoritative_patch(web_app)
_install_v154_pdf_period_post(web_app)

_install_v157_option1_boceto_filters_patch(web_app)
_install_v158_boceto_exact_filters_patch(web_app)
_install_v159_operation_store_staff_pending_patch(web_app)
_install_v161_unified_boceto_filters_cards_patch(web_app)

# Paridad móvil y navegación por módulo.
_install_v162_visual_parity_patch(web_app)
_install_v162_dynamic_headers_staff_patch(web_app)
_install_v163_module_nav_cleanup_patch(web_app)

# V164/V165 quedan fuera de producción: sus observers globales provocaban
# re-render y movimiento continuo en Carga de datos. V166 absorbe sus funciones.
_install_v166_stability_roster_filters_patch(web_app)
_install_v167_backend_patch(web_app)
_install_v167_frontend_patch(web_app)
# V168 al final para que sus reglas prevalezcan sobre las capas anteriores.
_install_v168_backend_patch(web_app)
_install_v168_frontend_patch(web_app)
# V169 al final: cobertura y actualización de periodos tras nuevas cargas.
_install_v169_period_freshness_patch(web_app)
_install_v170_commercial_export_fix(web_app)
_install_v171_responsive_typography_patch(web_app)
_install_v172_density_balance_patch(web_app)
_install_v174_mobile_sales_repair_patch(web_app)
_install_v175_compact_filter_tabs_patch(web_app)
_install_v176_commercial_integral_patch(web_app)
_install_v177_sellthrough_report_patch(web_app)
_install_v190_lingerie_checklist_patch(web_app)
_install_v192_sellthrough_raw_rebuild(web_app)
_install_v193_sellthrough_clean_ui(web_app)
_install_pwa_patch(web_app)
# V194 SIEMPRE al final: capa visual definitiva posterior a V171/V172 y demás parches.
_install_v194_mobile_ui_final_patch(web_app)
_install_v195_report_navigation_restore_patch(web_app)
_install_v196_android_single_finger_scroll_patch(web_app)
_install_v198_commercial_area_offer_patch(web_app)
_install_v199_access_perf_productivity_patch(web_app)
_install_v200_operation_tabs_timer_patch(web_app)
_install_v201_operation_sales_demo_patch(web_app)
_install_v203_operation_option7_ui_patch(web_app)
# V218: conservar funciones aprobadas posteriores sin reinstalar las capas UI V206–V217.
_install_v204_operation_productivity_ranking_patch(web_app)
_install_v205_store_geofence_patch(web_app)
_install_v210_operational_standards_tenure_patch(web_app)
_install_v219_share_users_option3_patch(web_app)
_install_v220_operation_tabs_single_line_patch(web_app)
# V229 reemplaza V221 en móvil para evitar doble render de pestañas.
# _install_v221_report_tabs_match_operation_patch(web_app)
_install_v222_operation_capture_nav_admin_patch(web_app)
# V229 reemplaza V225: no instalar el carrusel/wrapper heredado.
# _install_v225_final_mobile_tab_rail_patch(web_app)
# V229 reemplaza V226/V228, cuyo JS quedó en conflicto con capas previas.
# _install_v226_single_mobile_tab_rail_patch(web_app)
_install_v229_mobile_tabs_final_patch(web_app)
# V234 va después de V229 para dominar únicamente la presentación móvil aprobada.
# _install_v234_exact_mobile_tabs_patch(web_app)  # reemplazado por V238
# V237 es la última capa: estabiliza Centro Operativo y acelera Macro Comercial.
_install_v237_final_ui_patch(web_app)
# V238 es la capa autoritativa de navegación para PC, tablet, iOS y Android.
_install_v238_responsive_nav_patch(web_app)
# V239 queda al final: Centro Operativo, administración de pestañas y Cargar productividad.
_install_v239_functional_close_patch(web_app)
# V240 es la capa final para Centro Operativo y Recorridos.
_install_v240_center_routes_calendar_patch(web_app)
# V241 queda al final: Cargar productividad C&M autoritativo y limpieza inmediata de Recorridos.
_install_v241_cm_capture_authoritative_patch(web_app)
# V243 reemplaza Recuperación por Tienda por Tasa de recuperación / Sell-Through Neto.
_install_v243_recovery_rate_patch(web_app)
# V249 queda fuera: su grid compacto entra en conflicto con la Opción 9B horizontal.
# _install_v249_operational_filter_profiles_patch(web_app)
# V252/V250 es la capa final autoritativa para filtros por pestaña y Opción 9B.
_install_v250_option9b_filters_patch(web_app)
# V254 queda al final: filtros 9B definitivos por pestaña.
_install_v254_filters_final_patch(web_app)
# V259 sustituye V256/V257/V258 como único controlador de Vista operativa.
# _install_v256_center_quick_view_restore_patch(web_app)
# _install_v257_universal_period_filter_patch(web_app)
# _install_v258_universal_filter_controller_patch(web_app)
_install_v259_stable_report_filter_patch(web_app)
# V260 es sólo CSS/layout y se instala al final para envolver visualmente toda la interfaz.
_install_v260_responsive_layout_patch(web_app)
# V261: Opción 9 en Comercial; Cambios y Muertos sin Consultar/Restablecer y actualización automática.
_install_v261_option9_commercial_auto_operational_filters_patch(web_app)
# V262: oculta Consultar/Restablecer con prioridad superior a V259/V254.
_install_v262_hide_filter_actions_patch(web_app)
# V263: capa visual base; móvil conserva estructura tipo laptop con mayor densidad.
_install_v263_laptop_mobile_density_patch(web_app)
# V264: base responsive general.
_install_v264_uniform_responsive_patch(web_app)
# V265: autoridad final; conserva la matriz real de laptop en móvil/tablet y sólo la compacta.
_install_v265_desktop_matrix_mobile_patch(web_app)
# V266: autoridad final del periodo operativo; corrige Semana y texto/icono dinámicos.
_install_v266_operational_period_authority_patch(web_app)
# V267: rediseño visual Opción 7 de la tabla Centro Operativo.
_install_v267_option7_monthly_table_patch(web_app)
# V268: Opción 10 en Conversión, Recuperación $ y Score.
_install_v268_option10_kpis_patch(web_app)
# V269: Opción 4 compacta en Resumen y Productividad del módulo Operación.
_install_v269_operation_option4_kpis_patch(web_app)
# V270: autoridad responsive final. Laptop/PC como referencia; móvil/tablet/iPad compactos al ancho real.
_install_v270_desktop_compact_responsive_authority_patch(web_app)
# V271: Centro Operativo móvil/tablet conserva exactamente la matriz de laptop, sólo compacta.
_install_v271_center_operativo_laptop_parity_patch(web_app)
# V272: PDF de Centro Operativo refleja la vista consultada (tarjetas, tablas y gráfico vigente).
_install_v272_center_pdf_parity_patch(web_app)
# V273: encabezados universales compactos para todas las tablas en móvil/tablet.
_install_v273_mobile_table_headers_patch(web_app)
# V275: capa final exclusiva de Operación; pestañas y tarjetas compactas.
_install_v275_operation_ui_final_patch(web_app)
# V276: limpia iconos heredados, compacta KPIs y desbloquea scroll móvil de Operación.
_install_v276_operation_ui_scroll_final_patch(web_app)
# V277: 8 tarjetas finales; elimina Llegada Origen y el duplicado de personal.
_install_v277_operation_kpis_final_patch(web_app)
# V279: Bonos Operativos por clúster A/B/C/D + configuración en Estándares.
_install_v279_operation_bonus_cluster_patch(web_app)

# V279: Resurtido de Pasillos · Sugerido 7 + productividad por parejas + avance por pasillo.
_install_v279_aisle_resupply_patch(web_app)

# V281: layout final del boceto 2+7+9 + historial + soporte DEMO.
_install_v281_aisle_resupply_boceto_patch(web_app)

# V285: densidad global de tablas; fuentes legibles y columnas compactas.
_install_v285_global_table_density_patch(web_app)

# V286: autoridad final de scroll y tipografía para iOS/Android/tablet/laptop/PC.
_install_v286_scroll_type_authority_patch(web_app)

# V288: Opción 5 final para Captura diaria de Operación.
_install_v288_operation_daily_option5_patch(web_app)
app = web_app.app
