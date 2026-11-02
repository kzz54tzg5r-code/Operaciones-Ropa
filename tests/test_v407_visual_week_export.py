"""V407: descarga Excel única, semanas en S, logo y pestañas adaptables."""
from io import BytesIO
from pathlib import Path
import subprocess

from pypdf import PdfReader

from v407_week_display import format_week_label
from v272_center_pdf_parity_patch import install

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"web"


def test_week_uses_s_only_in_visible_labels():
    assert format_week_label("2026-W44")=="2026-S44"
    assert format_week_label("Periodo: 2026-W44 · Semana W44")=="Periodo: 2026-S44 · Semana S44"
    assert format_week_label("2026-S44")=="2026-S44"
    assert format_week_label("2026-W99")=="2026-W99"
    assert format_week_label("Valor W no es una semana")=="Valor W no es una semana"


def test_center_footer_download_is_excel_only():
    page=(WEB/"index.html").read_text(encoding="utf-8")
    assert "const pdfButton=name==='Centro Ejecutivo'?'':" in page
    assert 'downloadCurrentReport(\'xlsx\'' in page
    # El backend PDF de otras pestañas permanece disponible.
    assert "downloadCurrentReport('pdf'" in page
    assert "reporte_adaptable_v407.js?v=407" in page


def test_missing_productivity_has_no_profile_activity_ui_pdf_excel_or_api():
    ui=(WEB/"colaboradores_sin_productividad_v400.js").read_text("utf-8")
    backend=(ROOT/"v400_missing_productivity_center_pdf.py").read_text("utf-8")
    assert "Perfil / actividad" not in ui
    assert "row.profile" not in ui
    assert "Perfil / actividad" not in backend
    assert "Perfil / Actividad" not in backend
    assert '"profile": r.get(' not in backend
    assert '"name","store","last_date","status"' in backend


def test_css_wins_old_fixed_tabs_and_old_white_logo_background():
    css=(WEB/"reporte_adaptable_v407.css").read_text("utf-8")
    for label in ("#operativoNav","#analysisNav","#v200OperationTabs"):
        assert label in css
    assert "var(--v407-tab-width" in css
    assert "min-height:78px!important" in css
    assert "max-height:none!important" in css
    assert "overflow:visible!important" in css
    assert "html body.or363-navigation #appView #sidebar .sidebrand img" in css
    assert "background:transparent!important" in css
    js=(WEB/"reporte_adaptable_v407.js").read_text("utf-8")
    assert "measureText" in js
    assert "MutationObserver" in js
    assert "--v407-tab-width" in js
    assert "replace(week,'$1-S$2')" in js
    assert "new MutationObserver" in js
    assert "option.value" not in js
    test=subprocess.run(["node","--check"],text=True,input=js,capture_output=True)
    assert test.returncode==0,test.stderr


def test_week_labels_are_s_in_real_center_pdf():
    from tests.test_v366_pdf_visual_parity import _sample
    data=_sample("week")
    pages=PdfReader(BytesIO(data)).pages
    txt=" ".join((p.extract_text() or "") for p in pages)
    assert "2026-S43" in txt
    assert "2026-W43" not in txt


def test_legacy_pdf_builders_also_have_visible_s_label():
    for filename in ("v96_center_exec_pdf_patch.py",
                     "v105_week_month_pdf_mirror_patch.py",
                     "v152_pdf_project_highlight_portrait_chart_patch.py",
                     "v272_center_pdf_parity_patch.py"):
        source=(ROOT/filename).read_text("utf-8")
        assert "format_week_label" in source,filename
