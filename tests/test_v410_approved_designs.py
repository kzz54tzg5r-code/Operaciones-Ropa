"""Checks de regresión para la capa visual de 25 diseños (sin datos simulados)."""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CSS=ROOT/"web/designs_25_approved_v410.css"
JS=ROOT/"web/designs_25_approved_v410.js"
HTML=ROOT/"web/index.html"
EXPECTED=[
    "operations.center","operations.conversion","operations.recovery",
    "operations.recovery_store","operations.recovery_audit",
    "operations.productivity","operations.capture","operations.routes",
    "operations.upload","operations.goals","operations.bonuses",
    "commercial.macro","commercial.stores","commercial.sections",
    "commercial.areas","commercial.pareto","commercial.slow",
    "commercial.zero","commercial.sales","commercial.sell",
    "commercial.accordion","commercial.subcat",
    "commercial.lingerie_checklist","commercial.upload","commercial.more",
]


def test_25_designs_present_and_no_business_calls():
    script=JS.read_text(encoding="utf-8")
    entries=re.findall(r"\['(operations\.[^']+|commercial\.[^']+)'\s*,",script)
    assert entries==EXPECTED
    assert "OR410_APPROVED_DESIGNS" in script
    assert "fetch(" not in script
    assert "XMLHttpRequest" not in script
    assert ".click()" not in script
    assert ".submit()" not in script


def test_assets_load_last_and_css_balanced():
    html=HTML.read_text(encoding="utf-8")
    assert html.index("reporte_adaptable_v407.css")<html.index("designs_25_approved_v410.css")
    assert html.index("designs_25_approved_v410.css")<html.index("designs_25_approved_v410.js")
    assert html.count("designs_25_approved_v410.css")==1
    assert html.count("designs_25_approved_v410.js")==1
    css=CSS.read_text(encoding="utf-8")
    css=re.sub(r"/\*[\s\S]*?\*/","",css)
    assert css.count("{")==css.count("}")
    assert "grid-template-columns:repeat(4,minmax(0,1fr))!important" in css
    assert "[data-or410-tab=\"operations.recovery_audit\"]" in css
    assert "#page-sections .subcat-matrix" in css
    assert "#page-lingerie-checklist .lingerie-grid" in css


def test_js_syntax():
    result=subprocess.run(["node","--check",str(JS)],capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr
