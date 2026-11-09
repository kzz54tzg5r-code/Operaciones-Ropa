"""V413: Centro Operativo compacto en móvil sin alterar el reporte real."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/"web/centro_movil_paridad_v413.css").read_text(encoding="utf-8")
HTML=(ROOT/"web/index.html").read_text(encoding="utf-8")
SW=(ROOT/"web/service-worker.js").read_text(encoding="utf-8")
SOURCE=(ROOT/"web/center_lanes.js").read_text(encoding="utf-8")

def test_mobile_center_is_last_stylesheet_and_cache_is_versioned():
    assert HTML.count('centro_movil_paridad_v413.css?v=413')==1
    assert HTML.index('acordeon_jerarquico_v412.css')<HTML.index('centro_movil_paridad_v413.css')
    assert SW.count("'/static/centro_movil_paridad_v413.css?v=413'")==1
    assert "operaciones-ropa-runtime-safe-update-v416" in SW

def test_four_lanes_in_one_row_and_no_oversized_flex_metric():
    assert '@media screen and (max-width:700px)' in CSS
    assert 'grid-template-columns:repeat(4,minmax(0,1fr))!important' in CSS
    assert '.ocl-lane>.ocl-lane-metric' in CSS
    assert 'flex:0 0 auto!important' in CSS
    assert 'min-height:0!important;height:auto!important;max-height:none!important' in CSS
    assert 'overflow-wrap:normal!important;word-break:normal!important' in CSS
    assert '.ocl-number,.ocl-route-number' in CSS
    assert 'white-space:nowrap!important' in CSS
    assert '.ocl-pending b' in CSS
    assert '.ocl-lane>.ocl-detail-button' in CSS
    assert 'env(safe-area-inset-top,0px)' in CSS

def test_original_numbers_buttons_filters_and_source_untouched():
    assert "const specs=[" in SOURCE
    assert "{id:'received'" in SOURCE
    assert "{id:'conditioned'" in SOURCE
    assert "{id:'located'" in SOURCE
    assert "const route=el('section','ocl-lane" in SOURCE
    assert "function detailButton(id)" in SOURCE
    assert "const complete=el('details','ocl-full')" in SOURCE
    assert "window.RopaCenterLanes={isActive,mount,fit,filters}" in SOURCE
    # El archivo nuevo debe ser estrictamente CSS y actuar solo sobre el centro operativo.
    assert "fetch(" not in CSS and "onclick" not in CSS
    assert "@media print" not in CSS
    assert CSS.count("html body.or410-ui.or356-center-active")>=20

def test_detail_tables_remain_readable_by_local_horizontal_scrolling():
    assert ".ocl-original :is(.tablewrap,.or356-scroll,.monthly-cross-desktop,.chart-scroll)" in CSS
    assert "overflow-x:auto!important" in CSS
    assert "width:max-content!important;min-width:max(660px,100%)!important" in CSS
    assert "table-layout:auto!important" in CSS
    assert "overscroll-behavior-x:contain!important" in CSS

def test_css_braces_balanced():
    without_comments=re.sub(r"/\*[\s\S]*?\*/","",CSS)
    assert without_comments.count("{")==without_comments.count("}")
