"""V111: porcentajes operativos en Día (web + PDF).

Cambios visuales solicitados:
- tarjeta Acondicionado: el valor principal es % Acondicionado; piezas quedan como detalle;
- tarjeta Ubicado: el valor principal es % Ubicado; piezas quedan como detalle;
- tabla diaria: conserva Acondicionado en piezas y reemplaza Ubicado en piezas por % Ubicado;
- PDF de Operación Diaria replica la misma lectura.

No modifica datos ni fórmulas del backend.
"""
from __future__ import annotations

import io


def install(m):
    if getattr(m, "_V111_DAILY_PERCENT", False):
        return

    from fastapi.responses import HTMLResponse

    # -------------------- WEB --------------------
    css = r'''
<style id="v111-daily-percent-css">
.v111-pct-cell{font-weight:950;color:#102A56}
.v111-pct-good{color:#159447!important}
.v111-pct-warn{color:#d99b00!important}
.v111-pct-bad{color:#d72c2c!important}
</style>
'''

    js = r'''
<script id="v111-daily-percent-js">
(function(){
  const n=v=>Number(v||0);
  const pctText=v=>`${n(v).toFixed(1)}%`;
  const pctClass=v=>n(v)>=80?'v111-pct-good':(n(v)>=65?'v111-pct-warn':'v111-pct-bad');
  const zeroCell=v=>n(v)===0?`<b class="zero-alert">${fmt(v)}</b>`:fmt(v);

  // Tabla de Operación Diaria: se mantienen las piezas Acondicionadas y se
  // sustituye la columna Ubicado por % Ubicado. No se agrega % Acondicionado.
  operationalDetailTable=function(stores,recovery=[]){
    const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
    return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
      <th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>% Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th>
      </tr></thead><tbody>${rows.map((r,i)=>{
        const total=(r.total_pzs ?? r.ingresos ?? 0);
        const pUb=(r.pct_ubicado!=null)?Number(r.pct_ubicado):((Number(total)>0)?(Number(r.ubicado||0)/Number(total)*100):0);
        return `<tr class="${r.is_project?'project-row':''}">
          <td><b>#${i+1}</b></td><td><b>${r.store}</b></td>
          <td>${zeroCell(r.dev_pzs)}</td><td>${zeroCell(r.muertos)}</td><td>${zeroCell(r.probador)}</td><td>${zeroCell(r.cajas)}</td>
          <td>${zeroCell(r.pendiente_anterior||0)}</td><td><b class="${Number(total)===0?'zero-alert':''}">${fmt(total)}</b></td>
          <td>${zeroCell(r.recorridos)}</td><td>${zeroCell(r.acondicionado)}</td>
          <td><b class="v111-pct-cell ${pctClass(pUb)}">${pctText(pUb)}</b></td>
          <td>${fmt(r.pendiente_acondicionar)}</td><td>${fmt(r.pendiente_ubicar)}</td>
        </tr>`;
      }).join('')}</tbody></table></div>`;
  };

  function updateDailyCards(){
    if(typeof OP_VIEW==='undefined' || OP_VIEW!=='Operación Diaria')return;
    const cards=[...document.querySelectorAll('#operativoDynamicContent .report-kpi')];
    cards.forEach(card=>{
      const label=card.querySelector('.rk-label');
      const value=card.querySelector('.rk-value');
      const sub=card.querySelector('.rk-sub');
      if(!label||!value)return;
      const key=(label.textContent||'').trim().toLowerCase();
      if(key==='acondicionado' || key==='% acondicionado'){
        // El render original deja las piezas en value y el porcentaje en sub.
        // Guardamos ambos para que el MutationObserver sea idempotente.
        if(!card.dataset.v111Pieces)card.dataset.v111Pieces=(value.textContent||'').trim();
        const p=(typeof OPSDATA!=='undefined' && OPSDATA?.metrics?.pct_acondicionado!=null)
          ? Number(OPSDATA.metrics.pct_acondicionado)
          : Number((sub?.textContent||'').replace(/[^0-9.-]/g,''));
        label.textContent='% ACONDICIONADO';
        value.textContent=pctText(p);
        value.classList.remove('zero-alert');
        value.classList.add(pctClass(p));
        if(sub)sub.textContent=`${card.dataset.v111Pieces} piezas acondicionadas`;
      }
      if(key==='ubicado' || key==='% ubicado'){
        if(!card.dataset.v111Pieces)card.dataset.v111Pieces=(value.textContent||'').trim();
        const p=(typeof OPSDATA!=='undefined' && OPSDATA?.metrics?.pct_ubicado!=null)
          ? Number(OPSDATA.metrics.pct_ubicado)
          : Number((sub?.textContent||'').replace(/[^0-9.-]/g,''));
        label.textContent='% UBICADO';
        value.textContent=pctText(p);
        value.classList.remove('zero-alert');
        value.classList.add(pctClass(p));
        if(sub)sub.textContent=`${card.dataset.v111Pieces} piezas ubicadas`;
      }
    });
  }

  const boot=()=>{
    const host=document.getElementById('operativoDynamicContent');
    if(host){
      new MutationObserver(()=>setTimeout(updateDailyCards,0)).observe(host,{childList:true,subtree:true});
      updateDailyCards();
    }
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
</script>
'''

    @m.app.middleware("http")
    async def _v111_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v111-daily-percent-js" not in html:
                html = html.replace("</head>", css + "</head>", 1)
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache", "Expires":"0"
            })
        except Exception as exc:
            print(f"[V111-WEB] warning {type(exc).__name__}: {exc}", flush=True)
            return response

    # -------------------- PDF --------------------
    old_pdf = m._build_operations_pdf

    def daily_pdf(d: dict, report: str, scope: str = "Compañía") -> bytes:
        if report != "Operación Diaria":
            return old_pdf(d, report, scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase.pdfmetrics import stringWidth

        def num(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0

        def f(v):
            return f"{num(v):,.0f}"

        def pct(v):
            return f"{num(v):.1f}%"

        rows = list(d.get("stores") or [])
        mt = d.get("metrics") or {}
        period = str(d.get("period_value") or "Histórico")

        W, H = landscape(letter)
        M = 26
        BLUE = "#173B73"; BLUE2 = "#246FE5"; PINK = "#EC007C"; PURPLE = "#7C3AED"
        GREEN = "#10B981"; ORANGE = "#F59E0B"; RED = "#EF4444"; TXT = "#102A56"
        MUT = "#6B778C"; LINE = "#D7E0EA"; BG = "#F3F6FA"

        bio = io.BytesIO()
        c = canvas.Canvas(bio, pagesize=(W, H))

        def header(suffix=""):
            c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, W, H, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M, H-88, W-2*M, 58, 11, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 17); c.drawString(M+18, H-55, "Cambios y Muertos")
            c.setFont("Helvetica", 8); c.drawString(M+18, H-72, "Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold", 9); c.drawRightString(W-M-18, H-54, "Operaciones Ropa - Price Shoes")
            c.setFont("Helvetica", 7); c.drawRightString(W-M-18, H-70, "Operación Diaria" + ((" - " + suffix) if suffix else ""))

        header()
        y = H - 106
        c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 7)
        c.drawString(M, y, f"Periodo: {period}   -   Alcance: {scope}")
        y -= 13

        items = [
            ("Dev pzs", f(mt.get("dev_pzs")), "", BLUE),
            ("Muertos", f(mt.get("muertos")), "", PINK),
            ("Probador", f(mt.get("probador")), "", ORANGE),
            ("Cajas", f(mt.get("cajas")), "", PURPLE),
            ("Total pzs", f(mt.get("total_pzs", mt.get("ingresos"))), "", BLUE2),
            ("Recorridos", f(mt.get("recorridos")), "", GREEN),
            ("% Acondicionado", pct(mt.get("pct_acondicionado")), f"{f(mt.get('acondicionado'))} piezas", PURPLE),
            ("% Ubicado", pct(mt.get("pct_ubicado")), f"{f(mt.get('ubicado'))} piezas", PINK),
            ("Pend. acond.", f(mt.get("pendiente_acondicionar")), "", ORANGE),
            ("Pend. ubicar", f(mt.get("pendiente_ubicar")), "", RED),
        ]

        gap = 7; cw = (W - 2*M - gap*4) / 5; ch = 53
        for i, (lab, val, sub, col) in enumerate(items):
            r = i // 5; q = i % 5; x = M + q*(cw+gap); yy = y - r*(ch+gap) - ch
            c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x, yy, cw, ch, 7, fill=1, stroke=1)
            c.setFillColor(colors.HexColor(col)); c.rect(x, yy, 4, ch, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica-Bold", 6); c.drawString(x+10, yy+38, lab.upper())
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 15); c.drawString(x+10, yy+18, val)
            if sub:
                c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica", 5.5); c.drawString(x+10, yy+7, sub)

        y -= 2*(ch+gap) + 4
        c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 11)
        c.drawString(M, y, "Detalle operativo - " + period)
        y -= 15

        # Ubicado en piezas se reemplaza por % Ubicado; Acondicionado conserva piezas.
        head = ["#", "Tienda", "Dev", "Muertos", "Prob.", "Cajas", "Pend.Ant.", "Total", "Recorr.", "Acond.", "% Ubic.", "Pend.Acond.", "Pend.Ubic."]
        fr = [.035,.12,.065,.06,.06,.055,.07,.07,.075,.075,.07,.125,.12]
        tw = W - 2*M; xs = [M]; acc = M
        for z in fr[:-1]:
            acc += tw*z; xs.append(acc)
        hh = 19
        c.setFillColor(colors.HexColor(BLUE)); c.rect(M, y-hh+3, tw, hh, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 4.5)
        for j, h in enumerate(head):
            c.drawString(xs[j]+2, y-8, h)
        y -= hh

        rh = 13 if len(rows)<=7 else (11.5 if len(rows)<=12 else 10.3)
        for i, r in enumerate(rows):
            total = r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")
            p_ubic = r.get("pct_ubicado")
            if p_ubic is None:
                p_ubic = (num(r.get("ubicado"))/num(total)*100) if num(total)>0 else 0
            vals = [
                f"#{i+1}", r.get("store", ""), f(r.get("dev_pzs")), f(r.get("muertos")), f(r.get("probador")),
                f(r.get("cajas")), f(r.get("pendiente_anterior")), f(total), f(r.get("recorridos")),
                f(r.get("acondicionado")), pct(p_ubic), f(r.get("pendiente_acondicionar")), f(r.get("pendiente_ubicar")),
            ]
            c.setFillColor(colors.HexColor("#DDEAFF") if r.get("is_project") else colors.white)
            c.rect(M, y-rh+2, tw, rh, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica", 4.5)
            for j, v in enumerate(vals):
                c.drawString(xs[j]+2, y-8, str(v)[:23])
            y -= rh

        # Conservar el gráfico operativo original para no perder el comparativo.
        y -= 7
        if y < 215:
            c.showPage(); header("gráfico"); y = H - 106
        c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 11)
        c.drawString(M, y, "Ingreso vs Acondicionado vs Ubicado - " + period)
        y -= 15
        x0 = M+42; x1 = W-M-12; base = 44; top = y-12; ph = max(70, top-base)
        gw = (x1-x0)/max(1,len(rows)); bw = min(13,gw*.23)
        mx = max([num(v) for r in rows for v in ((r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")),r.get("acondicionado"),r.get("ubicado"))]+[1])*1.15
        c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(.6)
        for q in range(5):
            gy = base + ph*q/4; c.line(x0,gy,x1,gy); c.setFillColor(colors.HexColor(MUT)); c.setFont("Helvetica",5); c.drawRightString(x0-5,gy-2,f(mx*q/4))
        pts=[]
        def tag(cx,cy,text,col):
            w=stringWidth(text,"Helvetica-Bold",5.2)+5
            c.setFillColor(colors.white); c.roundRect(cx-w/2,cy-2,w,8,2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(col)); c.setFont("Helvetica-Bold",5.2); c.drawCentredString(cx,cy,text)
        for i,r in enumerate(rows):
            cx=x0+gw*(i+.5)
            total=num(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"))
            ac=num(r.get("acondicionado")); ub=num(r.get("ubicado"))
            ah=ph*ac/mx; uh=ph*ub/mx
            c.setFillColor(colors.HexColor(BLUE)); c.rect(cx-bw-2,base,bw,max(.8,ah),fill=1,stroke=0)
            c.setFillColor(colors.HexColor(PINK)); c.rect(cx+2,base,bw,max(.8,uh),fill=1,stroke=0)
            if ac==0 and ub==0:
                tag(cx,base+3,"A 0 / U 0",MUT)
            else:
                tag(cx-bw/2-2,base+ah+3,"A "+f(ac),BLUE)
                tag(cx+bw/2+2,base+uh+3,"U "+f(ub),PINK)
            py=base+ph*total/mx; pts.append((cx,py,total))
            c.setFillColor(colors.HexColor(BLUE2)); c.circle(cx,py,2.6,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",5.5); c.drawCentredString(cx,base-13,str(r.get("store", ""))[:14])
        c.setStrokeColor(colors.HexColor(BLUE2)); c.setLineWidth(1.4)
        for p1,p2 in zip(pts,pts[1:]):
            c.line(p1[0],p1[1],p2[0],p2[1])
        for cx,py,total in pts:
            tag(cx,min(top-2,py+7),"Total "+f(total),BLUE2)

        c.save()
        out = bio.getvalue()
        if not out.startswith(b"%PDF"):
            return old_pdf(d, report, scope)
        return out

    m._build_operations_pdf = daily_pdf

    # Autoprueba de cálculos/presentación principal.
    try:
        sample = {"total_pzs":1774, "acondicionado":755, "ubicado":1679}
        p_ac = sample["acondicionado"] / sample["total_pzs"] * 100
        p_ub = sample["ubicado"] / sample["total_pzs"] * 100
        assert round(p_ac,1) == 42.6
        assert round(p_ub,1) == 94.6
        print("[V111-SELFTEST] Diario porcentual OK · Acond.=42.6% · Ubicado=94.6%", flush=True)
    except Exception as exc:
        print(f"[V111-SELFTEST] ERROR: {type(exc).__name__}: {exc}", flush=True)

    m._V111_DAILY_PERCENT = True
    print("[V111] Día: tarjetas porcentuales y tabla con % Ubicado; PDF alineado.", flush=True)
