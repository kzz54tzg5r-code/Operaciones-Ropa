"""V175 · Filtros comerciales compactos tipo pestaña.

Objetivo solicitado:
- Sustituir los filtros internos grandes (select + botón Consultar) de V166 por
  las pestañas compactas originales, con el mismo lenguaje visual de analysisNav.
- Eliminar duplicados visuales en Ubicación/Área y en los filtros 80/20.
- Mantener la lógica y endpoints existentes; sólo cambia presentación y sincronía.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V175_COMPACT_FILTER_TABS", False):
        return

    css = r'''<style id="v175-compact-filter-tabs-css">
/* En Comercial ya no mostramos los filtros grandes generados por V166. */
body[data-v163-module="analysis"] #page-macro .v166-internal-filter,
body[data-v163-module="analysis"] #page-areas .v166-internal-filter,
body[data-v163-module="analysis"] #page-sections .v166-internal-filter,
body[data-v163-module="analysis"] #v166AreaFilter,
body[data-v163-module="analysis"] #v166MacroSectionFilter,
body[data-v163-module="analysis"] #v166MacroAreaFilter,
body[data-v163-module="analysis"] #v166ParetoFilter{
  display:none!important;
}

/* Recuperamos las pestañas nativas que V166 ocultaba. */
body[data-v163-module="analysis"] #macroAreaSectionSwitch.v166-native-internal-hidden,
body[data-v163-module="analysis"] #macroAreaGroupSwitch.v166-native-internal-hidden,
body[data-v163-module="analysis"] #paretoGroupSwitch.v166-native-internal-hidden{
  display:flex!important;
}

/* Contenedor visual: mismo lenguaje que la navegación comercial subrayada. */
body[data-v163-module="analysis"] .compact-filter{
  background:#fff!important;
  border:1px solid #d8e4f0!important;
  border-radius:12px!important;
  padding:6px!important;
  margin:7px 0 10px!important;
  box-shadow:none!important;
}
body[data-v163-module="analysis"] .compact-filter .filter-caption{
  margin:2px 3px 4px!important;
  color:#64768d!important;
  font-size:8px!important;
  line-height:1.15!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  letter-spacing:.02em!important;
}

/* Cualquier grupo de filtros tipo botones se convierte en barra compacta. */
body[data-v163-module="analysis"] .compact-filter .switches,
body[data-v163-module="analysis"] .v168-filter-strip,
body[data-v163-module="analysis"] .v165-subfilters{
  display:flex!important;
  grid-template-columns:none!important;
  align-items:stretch!important;
  flex-wrap:wrap!important;
  gap:5px!important;
  width:100%!important;
  min-height:0!important;
  padding:0!important;
  margin:3px 0 6px!important;
  background:transparent!important;
  border:0!important;
  border-radius:0!important;
  box-shadow:none!important;
  overflow:visible!important;
}

body[data-v163-module="analysis"] .compact-filter .switches>button,
body[data-v163-module="analysis"] .v168-filter-strip>button,
body[data-v163-module="analysis"] .v165-subfilters>button{
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  flex:0 0 auto!important;
  width:auto!important;
  min-width:104px!important;
  min-height:43px!important;
  height:43px!important;
  margin:0!important;
  padding:6px 11px!important;
  border:1px solid transparent!important;
  border-radius:9px!important;
  background:#fff!important;
  color:#173f78!important;
  box-shadow:none!important;
  font-size:9px!important;
  line-height:1.1!important;
  font-weight:900!important;
  white-space:nowrap!important;
}

body[data-v163-module="analysis"] .compact-filter .switches>button:hover,
body[data-v163-module="analysis"] .v168-filter-strip>button:hover,
body[data-v163-module="analysis"] .v165-subfilters>button:hover{
  background:#f5f8fc!important;
  border-color:#d8e4f0!important;
}

body[data-v163-module="analysis"] .compact-filter .switches>button.active,
body[data-v163-module="analysis"] .v168-filter-strip>button.active,
body[data-v163-module="analysis"] .v165-subfilters>button.active{
  background:#176fe8!important;
  border-color:#176fe8!important;
  color:#fff!important;
  box-shadow:0 2px 6px rgba(23,105,232,.14)!important;
}

/* En Ubicación/Área evitamos el bloque doble: sólo sección + área, cada uno en una barra. */
body[data-v163-module="analysis"] #macroAreaSectionSwitch,
body[data-v163-module="analysis"] #macroAreaGroupSwitch{
  margin-bottom:5px!important;
}
body[data-v163-module="analysis"] #macroAreaSectionSwitch + .filter-caption{
  margin-top:7px!important;
}

/* Móvil: una sola franja horizontal desplazable, como la barra subrayada. */
@media(max-width:900px){
  body[data-v163-module="analysis"] .compact-filter{
    padding:5px!important;
    margin:5px 0 8px!important;
  }
  body[data-v163-module="analysis"] .compact-filter .switches,
  body[data-v163-module="analysis"] .v168-filter-strip,
  body[data-v163-module="analysis"] .v165-subfilters{
    flex-wrap:nowrap!important;
    overflow-x:auto!important;
    overflow-y:hidden!important;
    overscroll-behavior-x:contain!important;
    -webkit-overflow-scrolling:touch!important;
    scrollbar-width:none!important;
    padding-bottom:1px!important;
  }
  body[data-v163-module="analysis"] .compact-filter .switches::-webkit-scrollbar,
  body[data-v163-module="analysis"] .v168-filter-strip::-webkit-scrollbar,
  body[data-v163-module="analysis"] .v165-subfilters::-webkit-scrollbar{display:none!important}

  body[data-v163-module="analysis"] .compact-filter .switches>button,
  body[data-v163-module="analysis"] .v168-filter-strip>button,
  body[data-v163-module="analysis"] .v165-subfilters>button{
    flex:0 0 auto!important;
    min-width:96px!important;
    min-height:42px!important;
    height:42px!important;
    padding:6px 10px!important;
    font-size:8px!important;
  }

  body[data-v163-module="analysis"] .compact-filter .filter-caption{
    font-size:7px!important;
    margin:2px 2px 4px!important;
  }
}
</style>'''

    js = r'''<script id="v175-compact-filter-tabs-js">
(function(){
  if(window.__V175_COMPACT_FILTER_TABS)return;
  window.__V175_COMPACT_FILTER_TABS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function syncAreaBridge(){
    // La tabla única de V166 sigue usando su select interno. Lo dejamos oculto,
    // pero sincronizado con las pestañas compactas visibles.
    qa('[data-area-group]').forEach(btn=>{
      if(btn.dataset.v175Bridge)return;
      btn.dataset.v175Bridge='1';
      btn.addEventListener('click',()=>{
        const raw=btn.dataset.areaGroup||'Todas';
        const wanted=raw==='Todas'?'General':raw;
        setTimeout(()=>{
          const sel=q('#v166AreaFilter select');
          if(sel && sel.value!==wanted){
            sel.value=wanted;
            sel.dispatchEvent(new Event('change',{bubbles:true}));
          }
        },0);
      },true);
    });
  }

  function restoreNativeBars(){
    if(document.body.dataset.v163Module!=='analysis')return;
    ['#macroAreaSectionSwitch','#macroAreaGroupSwitch','#paretoGroupSwitch'].forEach(sel=>{
      const el=q(sel);
      if(!el)return;
      el.classList.remove('v166-native-internal-hidden');
      el.classList.add('v175-filter-tabs');
      el.style.removeProperty('display');
    });

    // Los filtros grandes pueden reaparecer por los observers de V166; quedan
    // fuera del flujo visual, sin destruir su estado ni su lógica.
    qa('#page-macro .v166-internal-filter,#page-areas .v166-internal-filter,#page-sections .v166-internal-filter').forEach(el=>{
      el.setAttribute('aria-hidden','true');
    });
    syncAreaBridge();
  }

  function schedule(){
    [0,80,220,600].forEach(ms=>setTimeout(restoreNativeBars,ms));
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#analysisNav,[data-area-section],[data-area-group],[data-pareto-group],.v161-apply,[data-main]'))schedule();
  },true);
  document.addEventListener('change',e=>{
    if(e.target.matches?.('#store,#section,#catalog,#week,#v165Status'))schedule();
  },true);

  const mo=new MutationObserver(()=>{clearTimeout(window.__v175t);window.__v175t=setTimeout(restoreNativeBars,60)});
  if(document.body)mo.observe(document.body,{childList:true,subtree:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
  console.info('[V175] filtros comerciales compactos tipo pestaña activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v175_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v175-compact-filter-tabs-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v175-compact-filter-tabs-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(response.headers);headers.pop("content-length",None)
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V175"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        return response

    m._V175_COMPACT_FILTER_TABS=True
    print("[V175] filtros internos grandes reemplazados visualmente por pestañas compactas.",flush=True)
