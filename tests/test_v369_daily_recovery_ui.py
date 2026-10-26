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
    assert "recoveryWarning" in daily
    assert "v368RebuildButton" in daily
    # Reaplicaciones por capas de middleware no deben duplicar tablas.
    assert _apply_money_format(rendered) == rendered


def test_three_views_keep_recovery():
    base=(Path(__file__).resolve().parents[1] / "v240_center_routes_calendar_patch.py").read_text(encoding="utf-8")
    center=base.split("function centerHtml(",1)[1].split("async function renderCenter(",1)[0]
    assert "if(typeof recoveryTable==='function')" in center
    assert "if(mode!=='day'" not in center
