"""V414: las acciones de captura no comparten celda con los campos de piezas.

Las aserciones están ligadas a la jerarquía HTML de V241 y a las áreas del CSS
final; es un contrato de estructura, NO una prueba de captura visual autenticada.
"""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/"web/designs_25_approved_v410.css").read_text(encoding="utf-8")
V241=(ROOT/"v241_cm_capture_authoritative_patch.py").read_text(encoding="utf-8")
HTML=(ROOT/"web/index.html").read_text(encoding="utf-8")

def test_capture_three_disjoint_areas_in_authorized_option_two():
    assert 'grid-template-areas:"head head head" "meta meta meta" "activity pieces actions"' in CSS
    for node,area in [
        ('> .v241-capture-head','head'),
        ('> .v241-capture-meta','meta'),
        ('> .v241-field','activity'),
        ('> #v241PieceCaptureHost','pieces'),
        ('> .v241-actions','actions'),
    ]:
        pattern=rf'#v241CmCapture\s*{re.escape(node)}\s*\{{([^{{}}]*)\}}'
        match=re.search(pattern,CSS)
        assert match,f"Falta regla específica del componente {node}"
        assert f'grid-area:{area}!important' in match.group(1),f"{node}: no usa área {area}"

def test_buttons_and_clock_are_grid_children_with_nonoverlap():
    for key,grid_area in [('v241Start','1 / 1 / 2 / 2'),('v241Finish','2 / 1 / 3 / 2')]:
        assert f'> #{key}' in CSS
        assert f'grid-area:{grid_area}!important' in CSS
        assert f'id="{key}"' in V241 or f"'{key}'" in V241
    assert 'grid-area:1 / 2 / 3 / 3!important' in CSS
    assert 'min-width:0!important;max-width:100%!important;width:100%!important' in CSS
    assert 'box-sizing:border-box!important' in CSS
    assert 'position:static!important;transform:none!important' in CSS

def test_responsive_grid_never_places_actions_over_pieces():
    assert 'grid-template-areas:"head head" "meta meta" "activity pieces" "actions actions"' in CSS
    assert 'grid-template-areas:"head" "meta" "activity" "pieces" "actions"' in CSS
    assert "grid-template-columns:repeat(2,minmax(0,1fr))!important" in CSS
    assert "grid-template-columns:minmax(0,1fr)!important" in CSS

def test_real_data_events_and_all_four_areas_preserved():
    for term in ["Clasificado","Acondicionado","Ubicado","Recolección","Planchado"]:
        assert term in V241
    for term in ["Colgado","Doblado","Jeans","Lencería"]:
        assert term in V241
    for path in ["/api/cm-productivity/start","/api/cm-productivity/"]:
        assert path in V241
    assert "q('#v241Start')?.addEventListener('click'" in V241
    assert "q('#v241Finish')?.addEventListener('click'" in V241
    for term in ['Piezas del día','Meta diaria','Cumplimiento','Tiempo efectivo','<th>Inicio</th><th>Fin</th>']:
        assert term in V241
    assert 'designs_25_approved_v410.css?v=410' in HTML

def test_no_rogue_v412_fixed_column_spans_remain():
    section=CSS.split('/* V414: Cargar Productividad',1)[1]
    assert 'grid-column:8/span5' not in section
    assert 'grid-column:4/span4' not in section
    assert 'grid-row:3!important' not in section
    uncomm=re.sub(r'/\*[\s\S]*?\*/','',CSS)
    assert uncomm.count('{')==uncomm.count('}')
