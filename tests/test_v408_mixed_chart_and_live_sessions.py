"""V408: gráfico mixto y reconocimiento de sesiones persistentes."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_mixed_chart_is_consistent_between_web_and_pdf():
    html=(ROOT/"web/index.html").read_text("utf-8")
    chart=html.split("function opsComboSvg(",1)[1].split("function recoveryTable(",1)[0]
    assert '#1769e8" rx="2"></rect>' in chart   # Ingresos
    assert '#173B73" rx="2"></rect>' in chart   # Acondicionado
    assert 'pts.push(`${cx},${y(ub)}`)' in chart
    assert 'pts.push(`${cx},${y(ing)}`)' not in chart
    assert '<polyline points=' in chart and 'stroke="#EC007C"' in chart
    assert 'fill="#EC007C" rx="2"' not in chart  # Ubicado ya NO es barra
    pdf=(ROOT/"v272_center_pdf_parity_patch.py").read_text("utf-8")
    chart_pdf=pdf.split("def draw_combo_chart():",1)[1].split("# ---------- Construcción ----------",1)[0]
    assert "points.append((cx, py, ubic))" in chart_pdf
    assert "set_stroke(PINK)" in chart_pdf
    assert "set_fill(BLUE)" in chart_pdf and "set_fill(NAVY)" in chart_pdf
    assert "c.roundRect(cx+2, base, bar_w, max(0.01,ah)" in chart_pdf
    assert "max(0.01,ih)" in chart_pdf
    assert "set_fill(PINK); c.rect" not in chart_pdf
    assert "Ubicado" in chart_pdf


def test_access_control_separates_login_from_session_seen():
    module=(ROOT/"v405_user_access_history.py").read_text("utf-8")
    web=(ROOT/"web/index.html").read_text("utf-8")
    ui=(ROOT/"web/access_history_option4_v405.js").read_text("utf-8")
    assert "@m.app.post(\"/api/access/session-observed-v408\")" in module
    assert 'request.session.get("v408_audit_seen")' in module
    assert 'request.session["v408_audit_seen"]=True' in module
    assert "session_observed" in module
    assert '"observed":int(counts["observed"] or 0)' in module
    assert "m.require_real_superadmin(request)" in module
    assert "session-observed-v408" in web
    assert "session-observed-v408" in ui
    assert 'id="v405Observed"' in ui
    assert "dateTime(r.latest)" in ui
    assert "sesiones" in ui.casefold()
    assert "session_observed:'Sesión vigente detectada'" in ui


def test_updated_web_ui_script_and_pdf_compile():
    html=(ROOT/"web/index.html").read_text("utf-8")
    # Extraer solamente el JS embebido, no las etiquetas HTML.
    start=html.index("<script>",html.index("</style>")) if "<script>" in html else -1
    # La prueba de sintaxis de la página completa se realiza en tests/ui.
    for path in [ROOT/"web"/"access_history_option4_v405.js",ROOT/"web"/"service-worker.js"]:
        p=subprocess.run(["node","--check",str(path)],capture_output=True,text=True)
        assert p.returncode==0,p.stderr
    import ast
    ast.parse((ROOT/"v405_user_access_history.py").read_text("utf-8"))
    ast.parse((ROOT/"v272_center_pdf_parity_patch.py").read_text("utf-8"))


def test_live_v365_override_renders_two_bar_series_and_ubicado_line():
    """La capa V365 sobrescribe opsComboSvg; verificar el SVG QUE VE EL USUARIO."""
    source=ROOT/"web"/"detalle_operativo_opcion1_v365.js"
    js=r"""
const fs=require('fs'),vm=require('vm');
const context={window:{},fmt:n=>Math.round(n).toLocaleString('es-MX')};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const html=context.window.opsComboSvg([
  {store:'Vallejo',ingresos:1915,acondicionado:1189,ubicado:1546},
  {store:'Arco Norte',ingresos:668,acondicionado:1000,ubicado:1750},
  {store:'Puebla Sur',ingresos:255,acondicionado:54,ubicado:289},
],'2026-S44','Todas las tiendas');
if(!html.includes('data-or365-chart="mixed-bars-line"'))throw Error('No es mixto');
if(!html.includes('<polyline points=')||!html.includes('stroke="#e50076"'))throw Error('No hay línea rosa');
if(html.includes('rx="2" fill="#e50076"'))throw Error('Ubicado sigue como barra');
for(const shade of ['#1769e8','#173b73']){
 const count=(html.match(new RegExp('rx="2" fill="'+shade+'"','g'))||[]).length;
 if(count!==3)throw Error('Las barras '+shade+' no coinciden con 3 tiendas: '+count);
}
if((html.match(/<circle cx=/g)||[]).length < 3)throw Error('Faltan puntos de Ubicado');
if(!html.includes('Vallejo')||!html.includes('Puebla Sur'))throw Error('No hay tiendas');
"""
    run=subprocess.run(["node","-e",js,str(source)],text=True,capture_output=True)
    assert run.returncode==0,run.stderr
