"""V413: Centro Operativo no debe repetir el cuadro Categoría / Indicador / Valor.

Este cuadro todavía alimenta las cuatro tarjetas, pero no debe mostrarse
ni en PC ni en móvil/PWA con un viewport que simula computadora.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
compact=(ROOT/"web/compact_reports.css").read_text(encoding="utf-8")
approved=(ROOT/"web/centro_operativo_opcion4_v356.css").read_text(encoding="utf-8")
html=(ROOT/"web/index.html").read_text(encoding="utf-8")
sw=(ROOT/"web/service-worker.js").read_text(encoding="utf-8")


def test_no_unconditional_force_show_of_old_table():
    # Esta línea era más específica que la regla que intentaba ocultar el bloque.
    old="html body #page-operativo .ocl-original .monthly-cross-desktop{display:block!important"
    assert old not in compact
    # Otros diseños pueden conservar su reporte anterior, no se oculta globalmente.
    assert 'html body #page-operativo .ocl-shell:not([data-design="ultracompact-four"]) .ocl-original .monthly-cross-desktop{display:block!important}' in compact


def test_only_duplicate_center_block_is_hidden():
    part=compact[compact.index("/* V413: evitar que el bloque antiguo"):]
    required=(
        ".ocl-original .monthly-cross-desktop",
        ".ocl-original .monthly-cross-mobile",
        ".ocl-original .mct-kpi-grid",
    )
    for selector in required:
        assert 'html body #page-operativo .ocl-shell[data-design="ultracompact-four"] '+selector in part
    assert re.search(r'\.ocl-original \.mct-kpi-grid\s*\{\s*display:none!important',part)
    assert 'tablewrap' not in part.split("display:none!important")[0]
    assert "recovery" not in part.split("display:none!important")[0].lower()
    assert "ocl-lanes" in approved and "ocl-full" in approved
    assert 'data-design="ultracompact-four"' in approved


def test_recovery_table_and_exporters_still_exist():
    assert "Recuperación por tienda" in html
    assert 'function monthlyCrossTable(' in html
    assert 'function opTable(' in html
    assert 'class="tablewrap monthly-cross-desktop"' in html
    # Los contenidos fuente no se eliminan: solo cambia la presentación.
    assert "monthly-cross-table" in html
    assert "Recuperación por tienda" in approved or "Tablas por tienda" in approved


def test_mobile_pwa_uses_versioned_css():
    assert "/static/compact_reports.css?v=413" in html
    assert "'/static/compact_reports.css?v=413'" in sw
    assert "operaciones-ropa-runtime-safe-update-v413" in sw
