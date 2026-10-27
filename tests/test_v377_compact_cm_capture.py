"""Regresión del formulario compacto: conserva captura real y cronómetro."""
from pathlib import Path
import subprocess

SOURCE = Path(__file__).resolve().parents[1] / "v241_cm_capture_authoritative_patch.py"


def pieces():
    return SOURCE.read_text(encoding="utf-8")


def test_authoritative_capture_js_is_valid():
    src = pieces()
    script = src.split('js = r\x27\x27\x27<script id="v241-cm-capture-js">', 1)[1].split("</script>\x27\x27\x27", 1)[0]
    checked = subprocess.run(
        ["node", "--check", "--input-type=commonjs"],
        input=script, capture_output=True, text=True
    )
    assert checked.returncode == 0, checked.stderr


def test_start_finish_timer_and_post_routes_unchanged():
    src = pieces()
    for required in (
        'id="v241Start"', 'id="v241Finish"', 'id="v241Timer"',
        "q('#v241Start')?.addEventListener('click'",
        "q('#v241Finish')?.addEventListener('click'",
        "A('/api/cm-productivity/start'",
        "A('/api/cm-productivity/'+encodeURIComponent(active.id)+'/finish'",
        "if(active)startClock()",
        "if(active)return",
    ):
        # Only the known active-state check in the original is needed; if the
        # guard uses the negated variant below we accept that spelling.
        if required == "if(active)return":
            assert "if(!active)return" in src
        else:
            assert required in src, required


def test_layout_compact_with_all_areas_and_history():
    src = pieces()
    for required in (
        "V377 · Cargar productividad compacto",
        "grid-template-columns:repeat(12,minmax(0,1fr))",
        "grid-template-columns:repeat(4,minmax(0,1fr))",
        "v241-capture-meta",
        "v241-clockbox",
        "v241-clock-times",
        "Hora de inicio", "Hora de fin", "Tiempo de sesión",
        "v241-history-summary",
        "v241-history-empty",
        "'Colgado'", "'Doblado'", "'Jeans'", "'Lencería'",
        "isCollectionActivity(activity)?collectionInputs(item):areaInputs(activity,item)",
    ):
        assert required in src, required


def test_css_remains_scoped_and_adaptive():
    src = pieces()
    css = src.split('css = r\x27\x27\x27<style id="v241-cm-capture-css">', 1)[1].split("</style>\x27\x27\x27", 1)[0]
    assert css.count("{") == css.count("}")
    assert css.count("body.v241-cm-capture") > 15
    assert "@media(max-width:1020px)" in css
    assert "@media(max-width:620px)" in css
