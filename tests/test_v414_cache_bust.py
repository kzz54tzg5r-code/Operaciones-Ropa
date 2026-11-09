"""Verifica que el CSS V414 publicado no conserve el identificador de caché V410."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"web/index.html").read_text(encoding="utf-8")
WORKER=(ROOT/"web/service-worker.js").read_text(encoding="utf-8")
CSS=(ROOT/"web/designs_25_approved_v410.css").read_text(encoding="utf-8")

def test_bumped_css_and_pwa_cache_versions():
    href="/static/designs_25_approved_v410.css?v=414"
    assert HTML.count(href)==1
    assert WORKER.count("'"+href+"'")==1
    assert "operaciones-ropa-runtime-safe-update-v418" in WORKER
    assert "designs_25_approved_v410.css?v=410" not in HTML
    assert "designs_25_approved_v410.css?v=410" not in WORKER

def test_corrected_capture_grid_is_in_versioned_asset():
    assert 'grid-template-areas:"head head head" "meta meta meta" "activity pieces actions"' in CSS
    assert 'grid-area:actions!important' in CSS
    assert "grid-column:8/span5" not in CSS.split("/* V414: Cargar Productividad",1)[1]
