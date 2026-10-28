"""Regresión: la interfaz muestra que faltan DEV del periodo sin ocultar la tabla."""
from pathlib import Path


def test_center_keeps_tables_and_surfaces_missing_source_status():
    root=Path(__file__).resolve().parents[1]
    text=(root/"v240_center_routes_calendar_patch.py").read_text(encoding="utf-8")
    assert "data?.recovery_source?.source_warning" in text
    assert "noDev&&devWarning" in text
    assert "esc(devWarning)" in text
    assert 'recoveryTable(rec)' in text
    assert 'operationalDetailTable(ordered,rec)' in text
    assert "reprocesar DEV desde Excel vigente" not in text
    assert "v240-source-note" in text


def test_backend_preserves_causal_source_metadata():
    root=Path(__file__).resolve().parents[1]
    source=(root/"v367_recovery_source_patch.py").read_text(encoding="utf-8")
    assert '"latest_monthly_day": latest_monthly_day' in source
    assert '"source_warning": warning' in source
    project=(root/"v153_project_scope_backend_authoritative_patch.py").read_text(encoding="utf-8")
    assert 'out["recovery_source"] = dict(all_data.get("recovery_source") or {})' in project
