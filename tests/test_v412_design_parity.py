"""Regresión V412: 25 diseños conectados con sus componentes reales.

Comprueba contratos de interfaz en el código publicado. No sustituye la
validación visual autenticada con datos reales y permisos de cada tienda.
"""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/"web/designs_25_approved_v410.css").read_text(encoding="utf-8")
JS=(ROOT/"web/designs_25_approved_v410.js").read_text(encoding="utf-8")
NAV=(ROOT/"web/correccion_visual_v411.js").read_text(encoding="utf-8")
NAVCSS=(ROOT/"web/correccion_visual_v411.css").read_text(encoding="utf-8")
HTML=(ROOT/"web/index.html").read_text(encoding="utf-8")

# Clave autorizada, selector presente en CSS, archivo que genera realmente el nodo.
APPROVED=[
 ("operations.center", ".ocl-lanes", "web/centro_operativo_opcion4_v356.js"),
 ("operations.conversion", ".report-kpis", "web/index.html"),
 ("operations.recovery", ".report-kpis", "web/index.html"),
 ("operations.recovery_store", ".rr243-kpis", "v243_recovery_rate_patch.py"),
 ("operations.recovery_audit", ".v331-kpis", "v331_recovery_audit_tab.py"),
 ("operations.productivity", ".or362-productivity-layout", "web/operaciones_aprobadas_v362.js"),
 ("operations.capture", "#v241CmCapture", "v241_cm_capture_authoritative_patch.py"),
 ("operations.routes", ".v240-route-calendar", "v240_center_routes_calendar_patch.py"),
 ("operations.upload", ".uploadgrid", "web/index.html"),
 ("operations.goals", ".or362-goals-kpis", "web/operaciones_aprobadas_v362.js"),
 ("operations.bonuses", ".v313-kpis", "v313_bonus_visual_and_cut_patch.py"),
 ("commercial.macro", "#sectionSummary", "web/index.html"),
 ("commercial.stores", "#storeTable", "web/index.html"),
 ("commercial.sections", "#rubroTable", "web/index.html"),
 ("commercial.areas", "#areaTables", "web/index.html"),
 ("commercial.pareto", "#paretoSummaryTable", "web/index.html"),
 ("commercial.slow", "#slowTable", "web/index.html"),
 ("commercial.zero", "#zeroTable", "web/index.html"),
 ("commercial.sales", ".sales-month-table", "v176_commercial_integral_patch.py"),
 ("commercial.sell", "#page-sellthrough-clean", "v193_sellthrough_clean_ui.py"),
 ("commercial.accordion", "#accordion", "web/index.html"),
 ("commercial.subcat", "#subcatParticipationReports", "web/index.html"),
 ("commercial.lingerie_checklist", ".lingerie-grid", "web/index.html"),
 ("commercial.upload", "#analysisCapacityHistory", "web/index.html"),
 ("commercial.more", "#page-more", "web/index.html"),
]


def test_25_real_components_have_approved_style_targets():
    assert len(APPROVED)==25
    assert len({key for key, _, _ in APPROVED})==25
    assert len({(key, target) for key, target, _ in APPROVED})==25
    for key, selector, file in APPROVED:
        assert f"'{key}'" in JS, f"{key}: sin registro de autorización"
        assert selector in CSS, f"{key}: selector sin diseño"
        source=(ROOT/file).read_text(encoding="utf-8")
        marker=selector[1:]
        assert marker in source, f"{key}: selector {selector} ausente en fuente real {file}"


def test_no_ghost_sellthrough_or_older_capture_selectors():
    assert "#page-sell :is(.st-kpis" not in CSS
    assert "#page-sellthrough-clean" in CSS
    assert "#v241CmCapture" in CSS
    assert "#v193StTable" in CSS
    assert "#v198SlowSummary" not in CSS
    assert "#v198ZeroSummary" not in CSS
    assert "'sellthrough-clean':'commercial.sell'" in JS
    assert "if(liveSell)return 'commercial.sell'" in JS
    assert "if(capture)return 'operations.capture'" in JS


def test_tab_scroll_text_and_original_actions_preserved():
    assert "function alignActive(nav)" in NAV
    assert "alignActive(op);alignActive(analysis)" in NAV
    assert "scroll-snap-align:start" in NAVCSS
    assert "or411-duplicate" in NAV
    assert "querySelector(':scope > button.active" in NAV
    capture=(ROOT/"v241_cm_capture_authoritative_patch.py").read_text(encoding="utf-8")
    for original_id in ("v241Start","v241Finish","v241Timer","v241Activity","v241PieceCaptureHost"):
        assert original_id in capture
    # No llamadas al backend ni nueva lógica transaccional en los parches de estilo.
    for source in (JS,NAV):
        assert "fetch(" not in source
        assert "XMLHttpRequest" not in source
        assert ".submit()" not in source


def test_25_styles_syntax_and_order():
    uncommented=re.sub(r"/\*[\s\S]*?\*/","",CSS)
    assert uncommented.count("{")==uncommented.count("}")
    assert HTML.index("reporte_adaptable_v407.css")<HTML.index("designs_25_approved_v410.css")
    assert HTML.index("designs_25_approved_v410.css")<HTML.index("correccion_visual_v411.css")
    for path in ("web/designs_25_approved_v410.js","web/correccion_visual_v411.js"):
        result=subprocess.run(["node","--check",str(ROOT/path)],capture_output=True,text=True,check=False)
        assert result.returncode==0,result.stderr
