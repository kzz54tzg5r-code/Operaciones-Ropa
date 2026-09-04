"""V94: tabla operativa con diseño espejo y ceros en rojo hasta Ubicado.

Aplica la misma lectura visual en pantalla y PDF Diario:
- Encabezado azul oscuro y filas alternadas blanco/azul muy tenue.
- Tiendas Proyecto conservan una línea azul lateral, sin perder el zebra.
- Los valores 0 se muestran en rojo desde Dev pzs hasta Ubicado.
- Las columnas posteriores (pendientes) conservan su color normal.
"""
from __future__ import annotations

import io
import math


def _num(value):
    try:
        value = float(value or 0)
        return value if math.isfinite(value) else 0.0
    except Exception:
        return 0.0


def install(module) -> None:
    if getattr(module, "_V94_ZERO_RED_TABLE_PATCH", False):
        return

    previous_builder = module._build_operations_pdf

    def build_pdf_v94(data: dict, report: str, scope: str = "Compañía") -> bytes:
        if report != "Operación Diaria":
            return previous_builder(data, report, scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        W, H = landscape(letter)
        M = 26
        BLUE = "#173B73"; BLUE2 = "#246FE5"; PINK = "#EC007C"; PURPLE = "#7C3AED"
        GREEN = "#10B981"; ORANGE = "#F59E0B"; RED = "#D92D20"; TXT = "#102A56"
        MUT = "#6B778C"; LINE = "#D7E0EA"; BG = "#F3F6FA"; ALT = "#EEF4FB"
        rows = list(data.get("stores") or [])
        mt = data.get("metrics") or {}
        period = str(data.get("period_value") or "Histórico")
        out = io.BytesIO()
        c = canvas.Canvas(out, pagesize=(W, H))

        def f(v): return f"{_num(v):,.0f}"
        def pct(v): return f"{_num(v):.1f}%"

        def header(suffix="Operación Diaria"):
            c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, W, H, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M, H-88, W-2*M, 58, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 17); c.drawString(M+18, H-55, "Cambios y Muertos")
            c.setFont("Helvetica", 8); c.drawString(M+18, H-72, "Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold", 9); c.drawRightString(W-M-18, H-54, "Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica", 7); c.drawRightString(W-M-18, H-70, suffix)

        header()
        y = H - 106
        c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 7)
        c.drawString(M, y, f"Periodo: {period}   -   Alcance: {scope}")
        y -= 13

        # KPIs: si el valor es cero, también se enfatiza en rojo hasta Ubicado.
        items = [
            ("Dev pzs", f(mt.get("dev_pzs")), BLUE, _num(mt.get("dev_pzs"))),
            ("Muertos", f(mt.get("muertos")), PINK, _num(mt.get("muertos"))),
            ("Probador", f(mt.get("probador")), ORANGE, _num(mt.get("probador"))),
            ("Cajas", f(mt.get("cajas")), PURPLE, _num(mt.get("cajas"))),
            ("Total pzs", f(mt.get("total_pzs", mt.get("ingresos"))), BLUE2, _num(mt.get("total_pzs", mt.get("ingresos")))),
            ("Recorridos", f(mt.get("recorridos")), GREEN, _num(mt.get("recorridos"))),
            ("Acondicionado", f(mt.get("acondicionado")), PURPLE, _num(mt.get("acondicionado"))),
            ("Ubicado", f(mt.get("ubicado")), PINK, _num(mt.get("ubicado"))),
            ("Pend. acond.", f(mt.get("pendiente_acondicionar")), ORANGE, None),
            ("Pend. ubicar", f(mt.get("pendiente_ubicar")), RED, None),
        ]
        gap = 7; cw = (W-2*M-gap*4)/5; ch = 53
        for i, (lab, val, col, zero_check) in enumerate(items):
            rr = i//5; cc = i%5; x = M+cc*(cw+gap); yy = y-rr*(ch+gap)-ch
            c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x, yy, cw, ch, 7, fill=1, stroke=1)
            c.setFillColor(colors.HexColor(col)); c.rect(x, yy, 4, ch, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica-Bold", 6); c.drawString(x+10, yy+38, lab.upper())
            value_color = RED if zero_check is not None and zero_check == 0 else TXT
            c.setFillColor(colors.HexColor(value_color)); c.setFont("Helvetica-Bold", 15); c.drawString(x+10, yy+18, val)

        y -= 2*(ch+gap)+4
        c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 11); c.drawString(M, y, "Detalle operativo - "+period)
        y -= 15

        headers = ["Ranking","Tienda","Dev pzs","Muertos","Probador","Cajas","Pend. Ant.","Total pzs","Recorridos\nrealizados","Acondicionado","Ubicado","Pendiente de\nacondicionar","Pendiente de\nubicar"]
        widths = [.035,.12,.065,.06,.06,.055,.07,.07,.075,.075,.07,.125,.12]
        tw = W - 2*M; xs = [M]; acc = M
        for frac in widths[:-1]:
            acc += tw*frac; xs.append(acc)

        hh = 23
        c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M, y-hh+3, tw, hh, 5, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.5)
        for j, h in enumerate(headers):
            parts = h.split("\n")
            c.drawString(xs[j]+2, y-7, parts[0])
            if len(parts) > 1:
                c.drawString(xs[j]+2, y-14, parts[1])
        y -= hh

        # Compactar la tabla para 17 tiendas, manteniendo el zebra del reporte web.
        rh = 13 if len(rows) <= 7 else (11.5 if len(rows) <= 12 else 10.3)
        for i, r in enumerate(rows):
            total = r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")
            raw_values = [
                f"#{i+1}", r.get("store", ""), r.get("dev_pzs"), r.get("muertos"), r.get("probador"), r.get("cajas"),
                r.get("pendiente_anterior"), total, r.get("recorridos"), r.get("acondicionado"), r.get("ubicado"),
                r.get("pendiente_acondicionar"), r.get("pendiente_ubicar")
            ]
            display_values = [raw_values[0], raw_values[1]] + [f(v) for v in raw_values[2:]]
            bg = colors.white if i % 2 == 0 else colors.HexColor(ALT)
            c.setFillColor(bg); c.rect(M, y-rh+2, tw, rh, fill=1, stroke=0)
            # Proyecto: línea lateral sin cubrir el zebra.
            if r.get("is_project"):
                c.setFillColor(colors.HexColor(BLUE2)); c.rect(M, y-rh+2, 2.4, rh, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#E4EAF1")); c.setLineWidth(.25); c.line(M, y-rh+2, M+tw, y-rh+2)
            for j, val in enumerate(display_values):
                is_zero_red = 2 <= j <= 10 and _num(raw_values[j]) == 0
                if j in (0,1):
                    c.setFont("Helvetica-Bold", 4.5)
                    c.setFillColor(colors.HexColor(TXT))
                elif is_zero_red:
                    c.setFont("Helvetica-Bold", 4.6)
                    c.setFillColor(colors.HexColor(RED))
                else:
                    c.setFont("Helvetica", 4.5)
                    c.setFillColor(colors.HexColor(TXT))
                c.drawString(xs[j]+2, y-7.7, str(val)[:23])
            y -= rh

        # Gráfico atómico: si no cabe completo, pasa entero a una hoja nueva.
        y -= 7
        if y < 215:
            c.showPage(); header("Operación Diaria - gráfico"); y = H - 106

        c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 11)
        c.drawString(M, y, "Ingreso vs Acondicionado vs Ubicado - "+period)
        y -= 15
        x0 = M+42; x1 = W-M-12; base = 44; top = y-12; ph = max(70, top-base)
        gw = (x1-x0)/max(1, len(rows)); bw = min(13, gw*.23)
        mx = max([_num(v) for r in rows for v in ((r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")), r.get("acondicionado"), r.get("ubicado"))] + [1]) * 1.15
        c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(.6)
        for q in range(5):
            gy = base+ph*q/4; c.line(x0,gy,x1,gy); c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",5); c.drawRightString(x0-5,gy-2,f(mx*q/4))

        def tag(cx, cy, text, col):
            w = stringWidth(text, "Helvetica-Bold", 5.2)+5
            c.setFillColor(colors.white); c.roundRect(cx-w/2,cy-2,w,8,2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(col)); c.setFont("Helvetica-Bold",5.2); c.drawCentredString(cx,cy,text)

        pts = []
        for i, r in enumerate(rows):
            cx = x0+gw*(i+.5)
            total = _num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"))
            ac = _num(r.get("acondicionado")); ub = _num(r.get("ubicado"))
            ah = ph*ac/mx; uh = ph*ub/mx
            c.setFillColor(colors.HexColor(BLUE)); c.rect(cx-bw-2,base,bw,max(.8,ah),fill=1,stroke=0)
            c.setFillColor(colors.HexColor(PINK)); c.rect(cx+2,base,bw,max(.8,uh),fill=1,stroke=0)
            if ac == 0 and ub == 0:
                tag(cx,base+3,"A 0 / U 0",RED)
            else:
                tag(cx-bw/2-2,base+ah+3,"A "+f(ac), RED if ac == 0 else BLUE)
                tag(cx+bw/2+2,base+uh+3,"U "+f(ub), RED if ub == 0 else PINK)
            py = base+ph*total/mx; pts.append((cx,py,total))
            c.setFillColor(colors.HexColor(BLUE2)); c.circle(cx,py,2.6,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",5.5); c.drawCentredString(cx,base-13,str(r.get("store", ""))[:14])

        c.setStrokeColor(colors.HexColor(BLUE2)); c.setLineWidth(1.4)
        for p1, p2 in zip(pts, pts[1:]): c.line(p1[0],p1[1],p2[0],p2[1])
        for cx, py, total in pts: tag(cx,min(top-2,py+7),"Total "+f(total), RED if total == 0 else BLUE2)

        c.save()
        pdf = out.getvalue()
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError("El generador V94 no produjo un PDF válido")
        return pdf

    module._build_operations_pdf = build_pdf_v94

    # El middleware se instala al final para trabajar sobre el HTML ya modificado por V90.
    from fastapi.responses import HTMLResponse
    css = r'''
<style id="v94-zero-red-css">
.zero-alert{color:#d92d20!important;font-weight:950!important}
.ops-zero-table tbody tr:nth-child(even) td{background:#eef4fb!important}
.ops-zero-table tbody tr:nth-child(odd) td{background:#fff!important}
.ops-zero-table tbody tr.project-row td:first-child{box-shadow:inset 3px 0 0 #246fe5}
</style>
'''
    script = r'''
<script id="v94-zero-red-js">
(function(){
  const zeroCell=v=>Number(v||0)===0?`<b class="zero-alert">${fmt(v)}</b>`:fmt(v);
  const normalCell=v=>fmt(v);

  // Tabla usada en Día, Centro Ejecutivo, Semanal, Mensual y demás vistas operativas.
  operationalDetailTable=function(stores,recovery=[]){
    const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
    return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
      <th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th>
      </tr></thead><tbody>${rows.map((r,i)=>`<tr class="${r.is_project?'project-row':''}">
      <td><b>#${i+1}</b></td><td><b>${r.store}</b></td>
      <td>${zeroCell(r.dev_pzs)}</td><td>${zeroCell(r.muertos)}</td><td>${zeroCell(r.probador)}</td><td>${zeroCell(r.cajas)}</td>
      <td>${zeroCell(r.pendiente_anterior||0)}</td><td><b class="${Number(r.total_pzs??r.ingresos||0)===0?'zero-alert':''}">${fmt(r.total_pzs??r.ingresos)}</b></td>
      <td>${zeroCell(r.recorridos)}</td><td>${zeroCell(r.acondicionado)}</td><td>${zeroCell(r.ubicado)}</td>
      <td>${normalCell(r.pendiente_acondicionar)}</td><td>${normalCell(r.pendiente_ubicar)}</td>
      </tr>`).join('')}</tbody></table></div>`;
  };

  // También aplica el criterio visual en la tabla operativa alternativa.
  if(typeof opTable==='function'){
    opTable=function(rows,rec=[]){
      const ordered=orderByConversion(rows,rec), cm=conversionMap(rec);
      return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
      <th>#</th><th>Tienda</th><th>Conversión</th><th>Dev Pzs</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Ingresos</th><th>Acondicionado (Habilitado)</th><th>Pend. Acond.</th><th>% Acond.</th><th>Ubicado</th><th>Pend. Ubicar</th><th>% Ubicado</th><th>Recorridos</th>
      </tr></thead><tbody>${ordered.map((r,i)=>`<tr class="${r.is_project?'project-row':''}"><td><b>#${i+1}</b></td><td><b>${r.store}</b></td><td><b>${pct(cm[String(r.store)]||0)}</b></td>
      <td>${zeroCell(r.dev_pzs)}</td><td>${zeroCell(r.muertos)}</td><td>${zeroCell(r.cajas)}</td><td>${zeroCell(r.probador)}</td><td>${zeroCell(r.ingresos)}</td>
      <td>${zeroCell(r.acondicionado)}</td><td>${fmt(r.pendiente_acondicionar)}</td><td>${pct(r.pct_acondicionado)}</td><td>${zeroCell(r.ubicado)}</td><td>${fmt(r.pendiente_ubicar)}</td><td>${pct(r.pct_ubicado)}</td><td>${zeroCell(r.recorridos)}</td></tr>`).join('')}</tbody></table></div>`;
    };
  }

  // En Operación Diaria, los KPI desde Dev pzs hasta Ubicado también muestran 0 en rojo.
  function markDailyKpiZeros(){
    if(typeof OP_VIEW!=='undefined' && OP_VIEW!=='Operación Diaria')return;
    document.querySelectorAll('#operativoDynamicContent .report-kpis .report-kpi').forEach((card,idx)=>{
      if(idx>7)return;
      const val=card.querySelector('.rk-value'); if(!val)return;
      const raw=(val.textContent||'').replace(/[^0-9.-]/g,'');
      val.classList.toggle('zero-alert', raw!=='' && Number(raw)===0);
    });
  }
  const target=document.getElementById('operativoDynamicContent');
  if(target){new MutationObserver(()=>markDailyKpiZeros()).observe(target,{childList:true,subtree:true});markDailyKpiZeros();}
})();
</script>
'''

    @module.app.middleware("http")
    async def _v94_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v94-zero-red-js" not in html:
                html = html.replace("</head>", css+"</head>", 1)
                html = html.replace("</body>", script+"</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"})
        except Exception as exc:
            print(f"[V94] UI warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    module._V94_ZERO_RED_TABLE_PATCH = True
    print("[V94] Tabla espejo + ceros rojos hasta Ubicado en pantalla y PDF Diario.", flush=True)
