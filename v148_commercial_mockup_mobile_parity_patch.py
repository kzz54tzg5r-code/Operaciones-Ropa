"""V148 · Paridad móvil del demo Comercial con los bocetos aprobados.

Corrige la composición visual que V142 había apilado en exceso y que dejaba
Macro 80/20 dentro de una columna lateral. Mantiene todas las reglas funcionales
V144–V147 y únicamente reacomoda/estiliza el demo:
- filtros superiores compactos en una sola fila;
- KPIs compactos como en bocetos;
- Macro sección sin textos montados;
- Comparativo de tiendas + Macro sección/Compañía en dos bloques;
- Macro 80/20 a ancho completo debajo de ambos bloques, con sus 80 modelos y
  scroll interno;
- tablas de Tiendas, Sección/Rubro, Ubicación/Área, Más opciones y Sell Through
  compactas y legibles en móvil.
No modifica información real.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V148_COMMERCIAL_MOCKUP_MOBILE_PARITY", False):
        return

    js = r'''<script id="v148-commercial-mockup-mobile-parity-js">
(function(){
  function shadow(){
    var h=document.getElementById('v141CommercialHost');
    return h&&h.shadowRoot?h.shadowRoot:null;
  }
  function root(){
    var s=shadow();
    return s?s.getElementById('v139-demo-root'):null;
  }
  function titleText(el){
    if(!el)return '';
    var t=el.querySelector('.section-title');
    return (t?t.textContent:el.textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
  }
  function cardBy(page,rx){
    if(!page)return null;
    return Array.from(page.querySelectorAll('.card')).find(function(c){return rx.test(titleText(c));})||null;
  }
  function relocateMacro(){
    var r=root(); if(!r)return false;
    var page=r.querySelector('#page-macro'); if(!page)return false;
    var c8020=r.querySelector('#v144-8020-card') || cardBy(page,/macro\s*80\/20/i);
    var cmp=cardBy(page,/comparativo de tiendas/i);
    if(c8020 && cmp){
      var grid=cmp.closest('.grid2');
      if(grid && grid.parentElement){
        if(c8020.parentElement!==grid.parentElement || c8020.previousElementSibling!==grid){
          grid.parentElement.insertBefore(c8020,grid.nextSibling);
        }
        c8020.setAttribute('data-v148-full','1');
      }
    }
    var slow=r.querySelector('#v145-macro-slow,#v144-slow-card');
    var zero=r.querySelector('#v145-macro-zero,#v144-zero-card');
    if(c8020 && c8020.parentElement){
      var p=c8020.parentElement;
      if(slow && slow.parentElement===p && slow.previousElementSibling!==c8020){p.insertBefore(slow,c8020.nextSibling);}
      if(zero && zero.parentElement===p && slow && zero.previousElementSibling!==slow){p.insertBefore(zero,slow.nextSibling);}
    }
    return true;
  }
  function injectCss(s){
    var old=s.getElementById('v148-parity-style'); if(old)old.remove();
    var st=document.createElement('style'); st.id='v148-parity-style'; st.textContent=`
:host{display:block!important;width:100%!important;max-width:100%!important;overflow-x:hidden!important}
#v139-demo-root.app{width:100%!important;max-width:100%!important;min-width:0!important;overflow-x:hidden!important;gap:6px!important}
#v139-demo-root .card{min-width:0!important;max-width:100%!important}
#v139-demo-root .tablewrap{max-width:100%!important;-webkit-overflow-scrolling:touch!important}
#page-macro #v144-8020-card[data-v148-full="1"]{width:100%!important;max-width:100%!important;grid-column:1/-1!important;margin-top:0!important}
#page-macro #v144-8020-card .headrow{align-items:center!important}
#page-macro #v144-8020-card .v144-fixed-table{width:100%!important;max-width:100%!important;height:310px!important;overflow:auto!important}
#page-macro #v144-8020-card .v144-8020-table{min-width:760px!important;width:760px!important}
#page-macro #v145-macro-slow,#page-macro #v145-macro-zero,#page-macro #v144-slow-card,#page-macro #v144-zero-card{width:100%!important;max-width:100%!important}

@media(max-width:520px){
  #v139-demo-root.app{gap:5px!important}
  #v139-demo-root .card{padding:7px!important;border-radius:10px!important}
  #v139-demo-root .filters{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:5px!important;padding:7px!important}
  #v139-demo-root .field label{font-size:6.5px!important;margin-bottom:3px!important}
  #v139-demo-root .field select{height:32px!important;font-size:8px!important;padding:0 18px 0 6px!important;border-radius:6px!important}
  #v139-demo-root .query{grid-column:1/-1!important;height:34px!important;font-size:10px!important;border-radius:6px!important}
  #v139-demo-root .tabs{gap:4px!important;padding:1px 0 2px!important}
  #v139-demo-root .tab{min-height:28px!important;height:28px!important;padding:0 8px!important;font-size:6.5px!important;border-radius:14px!important}
  #v139-demo-root .demo-note{padding:6px 8px!important;gap:6px!important;border-radius:8px!important}
  #v139-demo-root .demo-note .info{width:20px!important;height:20px!important;font-size:11px!important}
  #v139-demo-root .demo-note b{font-size:8px!important}
  #v139-demo-root .demo-note span{font-size:6.5px!important;line-height:1.2!important}
  #v139-demo-root .section-title{font-size:13px!important;line-height:1.05!important}
  #v139-demo-root .section-sub{font-size:7.3px!important;line-height:1.2!important;margin-top:2px!important}
  #v139-demo-root .link{font-size:6.5px!important}
  #v139-demo-root .headrow{gap:5px!important}

  /* KPIs como los bocetos: compactos, sin cortar valores */
  #page-macro .kpis.six{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:5px!important}
  #page-stores .kpis.four,#page-section .kpis.four,#page-sections .kpis.four,#page-areas .kpis.four,#page-more .kpis.four,#page-sell .st-kpis{grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:4px!important}
  #v139-demo-root .kpi{min-height:58px!important;padding:5px!important;gap:5px!important;border-radius:8px!important;overflow:hidden!important}
  #v139-demo-root .kpi .ico{width:25px!important;height:25px!important;font-size:12px!important;flex:0 0 25px!important}
  #v139-demo-root .kpi .label{font-size:6.3px!important;line-height:1.05!important;white-space:normal!important}
  #v139-demo-root .kpi .value{font-size:10.8px!important;line-height:1.02!important;letter-spacing:-.15px!important;white-space:nowrap!important;overflow:visible!important;text-overflow:clip!important}
  #v139-demo-root .kpi .unit{font-size:5.8px!important;line-height:1!important;margin-top:1px!important}

  /* Macro sección: tres tarjetas en una fila, textos contenidos */
  #page-macro .grid3{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:5px!important}
  #page-macro .macrosec{padding:6px!important;min-height:78px!important;border-radius:8px!important;overflow:hidden!important}
  #page-macro .macrosec .top{gap:5px!important;align-items:center!important}
  #page-macro .garment{width:28px!important;height:28px!important;font-size:15px!important;flex:0 0 28px!important}
  #page-macro .macrosec .name{font-size:8px!important;line-height:1!important}
  #page-macro .macrosec .big{font-size:10.5px!important;line-height:1!important;white-space:nowrap!important}
  #page-macro .macrosec small{font-size:5.6px!important;line-height:1.18!important;white-space:normal!important;margin-top:4px!important;overflow-wrap:anywhere!important}

  /* Bloque central como boceto: dos paneles y 80/20 completo debajo */
  #page-macro>.grid2,#page-macro .grid2:has(> .card){grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important;align-items:start!important}
  #page-macro .bars{gap:5px!important;margin-top:6px!important}
  #page-macro .bar{grid-template-columns:52px minmax(45px,1fr) 42px!important;gap:4px!important;font-size:6.4px!important}
  #page-macro .bar b{font-size:6.4px!important}.track{height:9px!important}.percent{font-size:6px!important;padding:2px 3px!important}

  /* Macro 80/20 ancho completo, filtros compactos y tabla fija */
  #page-macro #v144-8020-card{padding:7px!important}
  #page-macro #v144-8020-card .v144-levels,#page-macro #v144-8020-card .v144-subs{gap:4px!important;padding:4px 0!important}
  #page-macro #v144-8020-card .filterbtn{height:25px!important;padding:0 8px!important;font-size:6.5px!important;border-radius:13px!important}
  #page-macro #v144-8020-card .v144-fixed-table{height:285px!important;border-radius:7px!important}
  #page-macro #v144-8020-card .v144-8020-table{min-width:720px!important;width:720px!important;font-size:7px!important}
  #page-macro #v144-8020-card .v144-8020-table th,#page-macro #v144-8020-card .v144-8020-table td{padding:5px 4px!important;line-height:1.1!important}
  #page-macro #v147-store-rule{min-width:118px!important;padding:5px 6px!important;border-radius:8px!important}
  #page-macro #v147-store-rule b{font-size:6.5px!important}#page-macro #v147-store-rule strong{font-size:11px!important}#page-macro #v147-store-rule small{font-size:5.5px!important}

  /* Tablas principales: conservar estructura pre-demo, sólo diseño */
  #page-stores .table,#page-section .table,#page-sections .table,#page-areas .table{min-width:0!important;width:100%!important;table-layout:auto!important;font-size:6.2px!important}
  #page-stores .table th,#page-stores .table td,#page-section .table th,#page-section .table td,#page-sections .table th,#page-sections .table td,#page-areas .table th,#page-areas .table td{padding:4px 3px!important;line-height:1.08!important;white-space:nowrap!important}
  #page-stores .badge,#page-section .badge,#page-sections .badge,#page-areas .badge{font-size:5.8px!important;padding:2px 4px!important}
  #page-stores .bar{grid-template-columns:58px minmax(55px,1fr) 48px!important;gap:4px!important;font-size:6.2px!important}

  /* Sección/Rubro y Ubicación/Área conservan paneles dobles del boceto */
  #page-section .grid2,#page-sections .grid2,#page-areas .grid2,#page-more>.grid2{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important;align-items:start!important}
  #v139-demo-root .filters-inline{gap:4px!important;flex-wrap:nowrap!important;overflow-x:auto!important}
  #v139-demo-root .filterbtn{height:28px!important;padding:0 9px!important;font-size:6.7px!important;border-radius:14px!important;flex:0 0 auto!important}

  /* Más opciones: tablas siguen completas con scroll local cuando haga falta */
  #page-more .tablewrap{overflow-x:auto!important}
  #page-more .table.wide,#page-more .table{min-width:760px!important;width:760px!important;font-size:7px!important}
  #page-more .table th,#page-more .table td{padding:5px 4px!important}
  #page-more .models-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important}

  /* Sell Through como el boceto: KPIs compactos y tabla completa */
  #page-sell .st-table{min-width:760px!important;width:760px!important;table-layout:auto!important;font-size:7px!important}
  #page-sell .st-table th,#page-sell .st-table td{padding:5px 4px!important;white-space:nowrap!important}
  #page-sell .stpct{min-width:34px!important;font-size:6.5px!important;padding:3px 4px!important}

  /* Modelos lentos y Sugerido 0 en Macro: ancho completo y scroll local */
  #page-macro #v145-macro-slow .tablewrap,#page-macro #v145-macro-zero .tablewrap,#page-macro #v144-slow-card .tablewrap,#page-macro #v144-zero-card .tablewrap{overflow-x:auto!important}
  #page-macro #v145-macro-slow .table,#page-macro #v145-macro-zero .table,#page-macro #v144-slow-card .table,#page-macro #v144-zero-card .table{min-width:980px!important;width:980px!important;font-size:7px!important}
  #page-macro #v145-macro-slow .table th,#page-macro #v145-macro-slow .table td,#page-macro #v145-macro-zero .table th,#page-macro #v145-macro-zero .table td,#page-macro #v144-slow-card .table th,#page-macro #v144-slow-card .table td,#page-macro #v144-zero-card .table th,#page-macro #v144-zero-card .table td{padding:5px 4px!important}
}
`;
    s.appendChild(st);
  }
  function apply(){
    var s=shadow(),r=root(); if(!s||!r)return false;
    injectCss(s); relocateMacro(); r.setAttribute('data-v148','1'); return true;
  }
  function retry(n){if(apply())return;if(n>0)setTimeout(function(){retry(n-1);},220);}
  document.addEventListener('click',function(e){
    var t=e.target&&e.target.closest?e.target.closest('[data-main],.tab,#query'):null;
    if(t)setTimeout(function(){retry(12);},100);
  },true);
  document.addEventListener('change',function(){setTimeout(function(){retry(8);},100);},true);
  setInterval(function(){var r=root();if(r){relocateMacro();}},1200);
  setTimeout(function(){retry(24);},300);
  console.info('[V148] Comercial móvil reacomodado para paridad con bocetos.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v148_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body += chunk
            html=body.decode("utf-8",errors="replace")
            if "v148-commercial-mockup-mobile-parity-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V148-COMMERCIAL-MOCKUP-MOBILE-PARITY",
            })
        except Exception as exc:
            print(f"[V148] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V148_COMMERCIAL_MOCKUP_MOBILE_PARITY=True
    print("[V148] Comercial móvil reacomodado para paridad con bocetos.",flush=True)
