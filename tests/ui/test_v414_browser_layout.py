"""Renderizado real Chrome de los controles existentes de Cargar Productividad V414.

Esta prueba reconstruye el HTML que emite V241 con valores de ejemplo, y
carga los CSS del proyecto. Comprueba que ninguna pieza/input/acción/horario
se encime a 1440, 1080, 800, 390 y 320 px.
No usa ni escribe datos reales, ni pretende validar la sesión de producción.
"""
import os
from pathlib import Path
import re
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
V241=(ROOT/"v241_cm_capture_authoritative_patch.py").read_text(encoding="utf-8")
INDEX=(ROOT/"web/index.html").read_text(encoding="utf-8")
stylesheet_pattern=re.compile(r'<link\b[^>]*rel="stylesheet"[^>]*href="/static/([^"?]+\.css)(?:\?[^"]*)?"',re.I)
stylesheets=[]
for match in stylesheet_pattern.finditer(INDEX):
    asset=ROOT/"web"/match.group(1)
    if asset.exists():
        stylesheets.append(asset.read_text(encoding="utf-8"))
v241_css=re.search(r"css = r'''(<style id=\"v241-cm-capture-css\">[\s\S]*?</style>)'''",V241)
assert v241_css,"Falta estilo original de V241"
# En producción el parche de V241 se añade al documento; las reglas V414 son más específicas.
css="".join(f"<style>{x}</style>" for x in stylesheets)+"\n"+v241_css.group(1)
meta="".join(f'<span><small>{label}</small><b>{value}</b></span>' for label,value in [
    ("Fecha","2026-11-05"),("Tienda","Aguascalientes"),
    ("Colaborador","Prueba visual"),("Nómina","00000")
])
areas="".join(f'<div class="v241-area-box"><label>Clasificado · {area}</label><input type="number" value="0"></div>'
              for area in ("Colgado","Doblado","Jeans","Lencería"))
markup=f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">{css}</head>
<body class="or410-ui v241-cm-capture or411-fix"><div id="appView"><main class="main"><div id="page-operativo">
<section id="operativoDynamicContent"><div id="v241CmCapture" class="v241-capture-panel">
 <div class="v241-capture-head"><h3>Registro de productividad</h3></div>
 <div class="v241-capture-meta">{meta}</div>
 <div class="v241-field"><label>Actividad realizada</label><select id="v241Activity"><option>Clasificado</option></select></div>
 <div id="v241PieceCaptureHost"><div class="v241-area-capture">
  <div class="v241-area-title"><b>Piezas · Clasificado</b><span>Captura las piezas realizadas por área.</span></div>
  <div class="v241-area-grid">{areas}</div>
 </div></div>
 <div class="v241-actions">
  <button id="v241Start" class="v241-start">▶ Inicio</button>
  <button id="v241Finish" class="v241-finish">■ Fin</button>
  <div class="v241-clockbox"><div class="v241-clock-times">
   <span><small>Hora de inicio</small><b>—</b></span>
   <span><small>Hora de fin</small><b>—</b></span>
  </div><div class="v241-clock-current"><small>Tiempo de sesión</small><b id="v241Timer">00:00:00</b></div></div>
  <span id="v241Msg"></span>
 </div></div>
<div id="v241Performance"><div class="v241-performance-kpi">Piezas del día 0</div></div>
</section></div></main></div></body></html>"""

def rect(page, selector):
    box=page.locator(selector).bounding_box()
    assert box is not None and box["width"]>0 and box["height"]>0,selector
    return box

def overlap(a,b):
    return max(0,min(a["x"]+a["width"],b["x"]+b["width"])-max(a["x"],b["x"])) * \
           max(0,min(a["y"]+a["height"],b["y"]+b["height"])-max(a["y"],b["y"]))

def test_capture_without_overlap_at_pc_tablet_and_phone():
    with sync_playwright() as p:
        binary=shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
        browser=p.chromium.launch(headless=True,executable_path=binary if binary else None,args=["--no-sandbox"])
        try:
            for width in [1440,1080,800,390,320]:
                page=browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
                page.set_content(markup,wait_until="load")
                activity=rect(page,"#v241CmCapture>.v241-field")
                pieces=rect(page,"#v241PieceCaptureHost")
                actions=rect(page,"#v241CmCapture>.v241-actions")
                start=rect(page,"#v241Start")
                finish=rect(page,"#v241Finish")
                clock=rect(page,".v241-clockbox")
                area_inputs=[r.bounding_box() for r in page.locator(".v241-area-box input").all()]
                for i,(left,right) in enumerate([(activity,pieces),(pieces,actions),(activity,actions),
                                                  (start,finish),(start,clock),(finish,clock)]):
                    assert overlap(left,right)<=1.0,(width,i,left,right)
                for area in area_inputs:
                    assert area and overlap(area,start)<=1.0 and overlap(area,finish)<=1.0,(width,area)
                for b in [activity,pieces,actions,clock,start,finish,*area_inputs]:
                    assert b["x"]>=-1 and b["x"]+b["width"]<=width+1,(width,b)
                assert page.locator("#v241Activity").count()==1
                assert page.locator(".v241-area-box input").count()==4
                assert page.locator("#v241Start").count()==1 and page.locator("#v241Finish").count()==1
                page.close()
        finally:
            browser.close()
