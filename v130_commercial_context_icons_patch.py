"""V130 · Iconografía contextual del demo Comercial.

Mantiene iconos de prendas únicamente para las secciones Dama, Caballero e
Infantil. El resto de los iconos se asigna según el significado del indicador
(existencia, sugerido, venta, utilidad, capacidad, ocupación, DDI, alertas,
acciones, catálogo, ranking, etc.). No modifica datos reales.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V130_COMMERCIAL_CONTEXT_ICONS", False):
        return

    css = r'''<style id="v130-commercial-context-icons-css">
.c129-icon,.c129-section-card .cloth,.c129-acc-head .cloth,.c129-alert .cloth,.c129-model .cloth{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif!important}
.c129-icon{font-size:18px!important;font-weight:900}
.c129-model .cloth{font-size:18px!important;font-weight:900;color:#1d5fd0}
</style>'''

    js = r'''<script id="v130-commercial-context-icons-js">
(function(){
  const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();

  function metricIcon(text){
    const t=normalize(text);
    if(t.includes('existencia')||t.includes('inventario')) return '📦';
    if(t.includes('sugerido')) return '🏷';
    if(t.includes('venta')) return '🛒';
    if(t.includes('utilidad')||t.includes('margen')) return '%';
    if(t.includes('capacidad')||t.includes('curva')) return '▥';
    if(t.includes('ocupacion')) return '◕';
    if(t.includes('ddi')||t.includes('dias de inventario')) return '◷';
    if(t.includes('piso')) return '▤';
    if(t.includes('bodega')) return '▦';
    if(t.includes('participacion')||t.includes('part.')) return '◔';
    if(t.includes('modelos')) return '▦';
    if(t.includes('tendencia')) return '↗';
    if(t.includes('ranking')||t.includes('top')) return '★';
    if(t.includes('alerta')||t.includes('riesgo')||t.includes('atencion')) return '!';
    if(t.includes('accion')||t.includes('recomendada')||t.includes('sugerida')) return '◎';
    if(t.includes('catalogo')) return '☷';
    if(t.includes('vigente')) return '✓';
    if(t.includes('descontinuado')) return '×';
    if(t.includes('proximo a salir')) return '◷';
    if(t.includes('impulso')) return '↟';
    if(t.includes('eficiencia')||t.includes('cumplimiento')) return '✓';
    if(t.includes('comparativo')||t.includes('desempeno')) return '▥';
    return '•';
  }

  function sectionIcon(text){
    const t=normalize(text);
    if(t.includes('dama')) return '👗';
    if(t.includes('caballero')) return '👔';
    if(t.includes('infantil')) return '👕';
    return '▦';
  }

  function applyContextIcons(){
    if(typeof USER==='undefined'||USER?.role!=='superadmin') return;
    const hero=document.querySelector('#heroTitle');
    if(!hero||!normalize(hero.textContent).includes('analisis comercial')) return;

    // KPI: icono por significado del indicador, nunca por prenda.
    document.querySelectorAll('.c129-kpi').forEach(card=>{
      const icon=card.querySelector('.c129-icon');
      const label=card.querySelector('small')?.textContent||card.textContent;
      if(icon) icon.textContent=metricIcon(label);
    });

    // Secciones: sólo Dama, Caballero e Infantil conservan prenda.
    document.querySelectorAll('.c129-section-card,.c129-acc').forEach(card=>{
      const icon=card.querySelector('.cloth');
      const title=card.querySelector('h4')?.textContent||card.textContent;
      if(icon) icon.textContent=sectionIcon(title);
    });

    // Alertas / acciones: usar el significado del bloque, no ropa.
    document.querySelectorAll('.c129-alert').forEach(row=>{
      const icon=row.querySelector('.cloth');
      const text=row.textContent;
      if(icon) icon.textContent=metricIcon(text);
    });

    // Modelos destacados: usar señal visual de ranking/estado, no una prenda.
    document.querySelectorAll('.c129-model').forEach(row=>{
      const icon=row.querySelector('.cloth');
      if(!icon) return;
      const parent=normalize(row.closest('.c129-panel')?.textContent||'');
      icon.textContent=parent.includes('lento') ? '↓' : '★';
    });

    // Cualquier prenda residual fuera de una sección Dama/Caballero/Infantil
    // se transforma al icono contextual más cercano.
    document.querySelectorAll('.c129-wrap .cloth').forEach(icon=>{
      const host=icon.closest('.c129-kpi,.c129-alert,.c129-model,.c129-section-card,.c129-acc')||icon.parentElement;
      const txt=host?.textContent||'';
      const t=normalize(txt);
      if(t.includes('dama')||t.includes('caballero')||t.includes('infantil')) return;
      if(icon.closest('.c129-section-card,.c129-acc')) icon.textContent='▦';
      else icon.textContent=metricIcon(txt);
    });
  }

  const observer=new MutationObserver(()=>applyContextIcons());
  observer.observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('click',()=>setTimeout(applyContextIcons,40),true);
  setTimeout(applyContextIcons,0);
  setTimeout(applyContextIcons,350);
  setTimeout(applyContextIcons,1200);
  console.info('[V130] Iconos Comerciales: prendas sólo en Dama/Caballero/Infantil; resto contextual.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v130_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v130-commercial-context-icons-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V130-COMMERCIAL-CONTEXT-ICONS",
            })
        except Exception as exc:
            print(f"[V130] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V130_COMMERCIAL_CONTEXT_ICONS = True
    print("[V130] Iconografía Comercial contextual instalada; prendas sólo en Dama, Caballero e Infantil.", flush=True)
