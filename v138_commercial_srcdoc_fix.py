"""V138 · Corrige pantalla en blanco del demo Comercial en Safari/iPhone.

Evita navegar el iframe a una ruta interna. Carga el HTML V137 con fetch y lo
inyecta mediante srcdoc, por lo que no depende de frame-ancestors/X-Frame-Options
ni de la navegación interna de Safari. Mantiene filtros y 7 pestañas, incluido
Sell Through, sin modificar datos reales.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V138_COMMERCIAL_SRCDOC_FIX", False):
        return

    css = r'''<style id="v138-commercial-srcdoc-css">
body.v133-commercial-demo #v133CommercialDemoHost{display:block!important;position:relative!important;z-index:2147483646!important;pointer-events:auto!important;overflow:visible!important}
body.v133-commercial-demo #v133CommercialDemoHost .v138-shell{display:block!important;margin:0!important;padding:0!important;background:#f2f6fb!important}
#v138CommercialFrame{display:block!important;width:100%!important;height:1200px;border:0!important;background:#f2f6fb!important;pointer-events:auto!important;touch-action:auto!important;overflow:hidden!important}
#v138CommercialLoading{display:grid;place-items:center;min-height:180px;background:#f2f6fb;color:#315985;font:800 13px system-ui,-apple-system,sans-serif;text-align:center;padding:24px}
#v138CommercialError{display:none;margin:8px;padding:12px;border:1px solid #f1c9ce;border-radius:10px;background:#fff5f6;color:#9f2030;font:700 12px system-ui,-apple-system,sans-serif}
</style>'''

    js = r'''<script id="v138-commercial-srcdoc-js">
(function(){
  var loading=false, loaded=false;
  function owner(){return typeof USER!=='undefined'&&(USER&&((USER.role==='superadmin')||(USER.real_role==='superadmin')||(USER.can_preview_roles===true)));}
  function isCommercial(){var h=(document.getElementById('heroTitle')||{}).textContent||'';return document.body.classList.contains('v133-commercial-demo')||/Análisis Comercial/i.test(h);}
  function host(){return document.getElementById('v133CommercialDemoHost');}
  function setHeight(){
    var f=document.getElementById('v138CommercialFrame');if(!f)return;
    try{var d=f.contentDocument;if(d&&d.documentElement){var h=Math.max(560,Math.min(6000,d.documentElement.scrollHeight+12));if(h>0)f.style.height=h+'px';}}catch(e){}
  }
  function showError(msg){var l=document.getElementById('v138CommercialLoading'),e=document.getElementById('v138CommercialError');if(l)l.style.display='none';if(e){e.style.display='block';e.textContent=msg||'No fue posible cargar el demo Comercial.';}}
  function build(){
    if(!owner()||!isCommercial())return;
    var h=host();if(!h)return;
    if(document.getElementById('v138CommercialFrame'))return;
    h.innerHTML='<div class="v133-shell v138-shell"><div id="v136CommercialFrame" style="display:none!important" aria-hidden="true"></div><div id="v137CommercialFrame" style="display:none!important" aria-hidden="true"></div><div id="v138CommercialLoading">Cargando demo Comercial…</div><div id="v138CommercialError"></div><iframe id="v138CommercialFrame" title="Demo Análisis Comercial" src="about:blank"></iframe></div>';
    h.style.setProperty('display','block','important');h.style.setProperty('pointer-events','auto','important');
  }
  async function load(){
    if(loaded||loading||!owner()||!isCommercial())return;
    build();var f=document.getElementById('v138CommercialFrame');if(!f)return;
    loading=true;
    try{
      var r=await fetch('/commercial-demo-v137?v=138&ts='+Date.now(),{cache:'no-store',credentials:'same-origin'});
      if(!r.ok)throw new Error('HTTP '+r.status);
      var html=await r.text();
      if(!html||html.length<500)throw new Error('HTML incompleto');
      f.onload=function(){loaded=true;loading=false;var l=document.getElementById('v138CommercialLoading');if(l)l.style.display='none';f.style.display='block';setHeight();setTimeout(setHeight,150);setTimeout(setHeight,700);};
      f.srcdoc=html;
      setTimeout(function(){if(!loaded){var l=document.getElementById('v138CommercialLoading');if(l)l.style.display='none';setHeight();}},1200);
    }catch(err){loading=false;showError('Error cargando el demo Comercial: '+(err&&err.message?err.message:err));}
  }
  function ensure(){if(!owner()||!isCommercial())return;build();load();}
  window.addEventListener('message',function(e){if(e.data&&e.data.type==='v137-height'){var f=document.getElementById('v138CommercialFrame');if(f){var n=Number(e.data.height)||1100;f.style.height=Math.max(560,Math.min(6000,n))+'px';}}});
  document.addEventListener('click',function(e){var m=e.target&&e.target.closest?e.target.closest('[data-main]'):null;if(m&&(m.dataset.main==='analysis'||m.dataset.main==='commercial'))setTimeout(ensure,120);},true);
  new MutationObserver(function(){if(isCommercial())setTimeout(ensure,0)}).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
  setInterval(function(){if(isCommercial()){ensure();if(loaded)setHeight();}},700);
  setTimeout(ensure,100);setTimeout(ensure,500);setTimeout(ensure,1200);
  console.info('[V138] Demo Comercial cargado por srcdoc para Safari/iPhone.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v138_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v138-commercial-srcdoc-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V138-COMMERCIAL-SRCDOC-FIX",
            })
        except Exception as exc:
            print(f"[V138] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V138_COMMERCIAL_SRCDOC_FIX = True
    print("[V138] Fix Safari Comercial instalado: demo por srcdoc, sin navegación de iframe.", flush=True)
