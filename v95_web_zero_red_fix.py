"""V95: corrección web para ceros rojos en tablas operativas.

Se instala después de V94 y redefine únicamente la presentación del HTML.
No cambia datos, cálculos ni PDF.
"""
from __future__ import annotations


def install(module) -> None:
    if getattr(module, "_V95_WEB_ZERO_RED_FIX", False):
        return

    from fastapi.responses import HTMLResponse

    css = r'''
<style id="v95-zero-red-css">
.zero-alert{color:#d92d20!important;font-weight:950!important}
.ops-zero-table tbody tr:nth-child(even) td{background:#eef4fb!important}
.ops-zero-table tbody tr:nth-child(odd) td{background:#fff!important}
.ops-zero-table tbody tr.project-row td:first-child{box-shadow:inset 3px 0 0 #246fe5}
</style>
'''

    script = r'''
<script id="v95-zero-red-js">
(function(){
  const zeroCell=v=>Number(v||0)===0?`<b class="zero-alert">${fmt(v)}</b>`:fmt(v);
  const normalCell=v=>fmt(v);

  operationalDetailTable=function(stores,recovery=[]){
    const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
    return `<div class="tablewrap"><table class="table ops-zero-table"><thead><tr>
      <th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th>
      </tr></thead><tbody>${rows.map((r,i)=>{
        const total=(r.total_pzs ?? r.ingresos ?? 0);
        return `<tr class="${r.is_project?'project-row':''}">
        <td><b>#${i+1}</b></td><td><b>${r.store}</b></td>
        <td>${zeroCell(r.dev_pzs)}</td><td>${zeroCell(r.muertos)}</td><td>${zeroCell(r.probador)}</td><td>${zeroCell(r.cajas)}</td>
        <td>${zeroCell(r.pendiente_anterior||0)}</td><td><b class="${Number(total)===0?'zero-alert':''}">${fmt(total)}</b></td>
        <td>${zeroCell(r.recorridos)}</td><td>${zeroCell(r.acondicionado)}</td><td>${zeroCell(r.ubicado)}</td>
        <td>${normalCell(r.pendiente_acondicionar)}</td><td>${normalCell(r.pendiente_ubicar)}</td>
        </tr>`;
      }).join('')}</tbody></table></div>`;
  };

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

  function markDailyKpiZeros(){
    if(typeof OP_VIEW!=='undefined' && OP_VIEW!=='Operación Diaria')return;
    document.querySelectorAll('#operativoDynamicContent .report-kpis .report-kpi').forEach((card,idx)=>{
      if(idx>7)return;
      const val=card.querySelector('.rk-value');
      if(!val)return;
      const raw=(val.textContent||'').replace(/[^0-9.-]/g,'');
      val.classList.toggle('zero-alert',raw!==''&&Number(raw)===0);
    });
  }
  const target=document.getElementById('operativoDynamicContent');
  if(target){
    new MutationObserver(markDailyKpiZeros).observe(target,{childList:true,subtree:true});
    markDailyKpiZeros();
  }
})();
</script>
'''

    @module.app.middleware("http")
    async def _v95_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v95-zero-red-js" not in html:
                html = html.replace("</head>", css + "</head>", 1)
                html = html.replace("</body>", script + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache", "Expires":"0"
            })
        except Exception as exc:
            print(f"[V95] UI warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    module._V95_WEB_ZERO_RED_FIX = True
    print("[V95] Ceros rojos web activos hasta Ubicado.", flush=True)
