"""La tabla diaria debe quedar tanto en la ruta moderna como en la heredada."""
from pathlib import Path
from v366_miles_display_patch import _apply_money_format


def test_day_recovery_is_reinjected_in_legacy_renderer():
    base=(Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert "out=monthlyCrossTable(mt,true);" in base
    rendered = _apply_money_format(base)
    daily = rendered.split("if(name==='Operación Diaria'){",1)[1].split("}else if(name==='Reporte Semanal'){",1)[0]
    assert 'Recuperación por tienda' in daily
    assert "recoveryTable(rec)" in daily
    assert "recoveryWarning" not in daily
    assert "v368RebuildButton" not in daily
    assert "Reprocesar DEV" not in rendered
    assert "dev_rebuild_controls_v371.js" not in rendered
    # Reaplicaciones por capas de middleware no deben duplicar tablas.
    assert _apply_money_format(rendered) == rendered


def test_three_views_keep_recovery():
    base=(Path(__file__).resolve().parents[1] / "v240_center_routes_calendar_patch.py").read_text(encoding="utf-8")
    center=base.split("function centerHtml(",1)[1].split("async function renderCenter(",1)[0]
    assert "if(typeof recoveryTable==='function')" in center
    assert "if(mode!=='day'" not in center

def test_no_additional_dev_polling_and_header_contrast():
    root = Path(__file__).resolve().parents[1]
    center = (root / "v240_center_routes_calendar_patch.py").read_text(encoding="utf-8")
    banner = center.split("function centerHtml(",1)[1].split("async function renderCenter(",1)[0]
    assert "v368RebuildButton" not in banner
    assert "Reprocesar DEV" not in banner
    assert "recoveryTable(rec)" in banner
    recovery = (root / "web" / "recuperacion_visible_v373.js").read_text(encoding="utf-8")
    assert "Verifica la conciliación" not in recovery
    assert "cache:'no-store'" not in recovery
    styles = (root / "web" / "recuperacion_visible_v373.css").read_text(encoding="utf-8")
    assert "html body.or356-center-active #appView .main>.hero #heroTitle" in styles
    assert "color:#ffffff!important" in styles
    old_controls = (root / "web" / "dev_rebuild_controls_v371.js").read_text(encoding="utf-8")
    assert "MutationObserver" not in old_controls
    assert "await fetch" not in old_controls
