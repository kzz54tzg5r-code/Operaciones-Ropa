"""V217 · Cambios y Muertos + Análisis Comercial con el mismo dock de Operación.

- Misma tarjeta, icono, nombre y estado activo que Operación.
- Una sola fila siempre.
- Escritorio: reparte el ancho; si ya no cabe, scroll horizontal.
- Móvil/tablet: tarjetas de 112 px, swipe horizontal y pestaña activa centrada.
- No cambia orden, permisos, visibilidad ni listeners funcionales.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V217_OTHER_REPORTS_MATCH_OPERATION", False):
        return

    css = r"""<style id="v217-other-reports-match-operation-css">
/* ==========================================================
   C&M + ANÁLISIS = MISMO DOCK VISUAL QUE OPERACIÓN
   ========================================================== */
body[data-v213-module="operativo"] #operativoNav:not(.hidden):not([hidden]),
body[data-v213-module="analysis"] #analysisNav:not(.hidden):not([hidden]){
  --v217-blue:#0d4f8b;
  --v217-blue2:#0878df;
  --v217-line:#d6e3f0;
  display:flex!important;
  flex-direction:row!important;
  flex-wrap:nowrap!important;
  align-items:stretch!important;
  justify-content:flex-start!important;
  gap:9px!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  min-height:0!important;
  height:auto!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  padding:7px 3px 12px!important;
  margin:3px 0 9px!important;
  background:transparent!important;
  border:0!important;
  box-shadow:none!important;
  scrollbar-width:none!important;
  -webkit-overflow-scrolling:touch!important;
  scroll-snap-type:x mandatory!important;
  overscroll-behavior-x:contain!important;
}
body[data-v213-module="operativo"] #operativoNav::-webkit-scrollbar,
body[data-v213-module="analysis"] #analysisNav::-webkit-scrollbar{display:none!important}

/* Exactamente una tarjeta por pestaña. */
body[data-v213-module="operativo"] #operativoNav>button,
body[data-v213-module="analysis"] #analysisNav>button{
  position:relative!important;
  display:flex!important;
  flex:1 1 0!important;
  width:auto!important;
  min-width:92px!important;
  max-width:none!important;
  min-height:82px!important;
  height:82px!important;
  max-height:82px!important;
  margin:0!important;
  padding:8px 7px 10px!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:6px!important;
  border:1px solid var(--v217-line)!important;
  border-radius:18px!important;
  background:rgba(255,255,255,.96)!important;
  color:#55718d!important;
  box-shadow:0 5px 18px rgba(28,72,116,.06)!important;
  transform:none!important;
  opacity:1!important;
  font-size:9px!important;
  line-height:1.15!important;
  font-weight:850!important;
  white-space:normal!important;
  text-align:center!important;
  overflow:hidden!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
}
body[data-v213-module="operativo"] #operativoNav>button:hover,
body[data-v213-module="analysis"] #analysisNav>button:hover{
  transform:translateY(-1px)!important;
  border-color:#b7cfe7!important;
  box-shadow:0 8px 22px rgba(28,72,116,.10)!important;
}

/* Sólo una iconografía y un nombre por pestaña. */
body[data-v213-module] :is(#operativoNav,#analysisNav)>button
  >:not(.v217-tab-icon):not(.v217-tab-label){
  display:none!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-icon{
  flex:0 0 38px!important;
  width:38px!important;
  min-width:38px!important;
  max-width:38px!important;
  height:38px!important;
  min-height:38px!important;
  max-height:38px!important;
  display:grid!important;
  place-items:center!important;
  border-radius:13px!important;
  background:#edf5fd!important;
  color:#567c9f!important;
  border:1px solid #dce8f4!important;
  box-shadow:none!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-icon svg{
  display:block!important;
  width:21px!important;
  height:21px!important;
  max-width:21px!important;
  max-height:21px!important;
  fill:none!important;
  stroke:currentColor!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-label{
  display:-webkit-box!important;
  -webkit-box-orient:vertical!important;
  -webkit-line-clamp:2!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin:0!important;
  padding:0!important;
  overflow:hidden!important;
  color:inherit!important;
  font-size:9px!important;
  line-height:1.12!important;
  font-weight:850!important;
  white-space:normal!important;
  text-overflow:ellipsis!important;
  text-align:center!important;
}

/* Estado activo idéntico a Operación. */
body[data-v213-module="operativo"] #operativoNav>button.active,
body[data-v213-module="analysis"] #analysisNav>button.active,
body[data-v213-module="operativo"] #operativoNav>button[aria-selected="true"],
body[data-v213-module="analysis"] #analysisNav>button[aria-selected="true"]{
  color:#fff!important;
  border-color:#0a5da7!important;
  background:linear-gradient(145deg,var(--v217-blue) 0%,var(--v217-blue2) 100%)!important;
  box-shadow:0 12px 28px rgba(13,79,139,.24)!important;
  transform:translateY(-2px)!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav)>button.active .v217-tab-icon,
body[data-v213-module] :is(#operativoNav,#analysisNav)>button[aria-selected="true"] .v217-tab-icon{
  background:rgba(255,255,255,.14)!important;
  border-color:rgba(255,255,255,.22)!important;
  color:#fff!important;
}
body[data-v213-module] :is(#operativoNav,#analysisNav)>button.active:after,
body[data-v213-module] :is(#operativoNav,#analysisNav)>button[aria-selected="true"]:after{
  content:""!important;
  display:block!important;
  position:absolute!important;
  left:50%!important;
  bottom:-7px!important;
  width:32px!important;
  height:4px!important;
  transform:translateX(-50%)!important;
  border-radius:999px!important;
  background:#1185ef!important;
  box-shadow:0 2px 7px rgba(17,133,239,.24)!important;
}

/* Pestañas ocultas por configuración siguen ocultas. */
body[data-v213-module] :is(#operativoNav,#analysisNav)>button.hidden,
body[data-v213-module] :is(#operativoNav,#analysisNav)>button[hidden],
body[data-v213-module] :is(#operativoNav,#analysisNav)>button[aria-hidden="true"]{
  display:none!important;
}

/* Tablet / ventana reducida: misma fila, se reduce antes de activar scroll. */
@media(min-width:901px) and (max-width:1250px){
  body[data-v213-module="operativo"] #operativoNav>button,
  body[data-v213-module="analysis"] #analysisNav>button{
    min-width:82px!important;
    min-height:74px!important;
    height:74px!important;
    padding:6px 5px 8px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-icon{
    width:33px!important;min-width:33px!important;max-width:33px!important;
    height:33px!important;min-height:33px!important;max-height:33px!important;
    flex-basis:33px!important;border-radius:11px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-icon svg{
    width:18px!important;height:18px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-label{
    font-size:7.7px!important;
  }
}

/* Móvil = el mismo comportamiento uno por uno que Operación. */
@media(max-width:900px){
  body[data-v213-module="operativo"] #operativoNav:not(.hidden):not([hidden]),
  body[data-v213-module="analysis"] #analysisNav:not(.hidden):not([hidden]){
    gap:8px!important;
    overflow-x:auto!important;
    overflow-y:visible!important;
    scroll-snap-type:x mandatory!important;
    padding:7px max(14px,calc((100vw - 112px)/2)) 13px!important;
    margin-left:-13px!important;
    margin-right:-13px!important;
    width:auto!important;
    max-width:none!important;
    scroll-padding-inline:calc((100vw - 112px)/2)!important;
  }
  body[data-v213-module="operativo"] #operativoNav>button,
  body[data-v213-module="analysis"] #analysisNav>button{
    flex:0 0 112px!important;
    width:112px!important;
    min-width:112px!important;
    max-width:112px!important;
    min-height:76px!important;
    height:76px!important;
    max-height:76px!important;
    border-radius:17px!important;
    font-size:8.2px!important;
    padding:7px 6px 9px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav)>button.active,
  body[data-v213-module] :is(#operativoNav,#analysisNav)>button[aria-selected="true"]{
    flex-basis:118px!important;
    width:118px!important;
    min-width:118px!important;
    max-width:118px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-icon{
    width:34px!important;min-width:34px!important;max-width:34px!important;
    height:34px!important;min-height:34px!important;max-height:34px!important;
    flex-basis:34px!important;border-radius:12px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-icon svg{
    width:19px!important;height:19px!important;
  }
  body[data-v213-module] :is(#operativoNav,#analysisNav) .v217-tab-label{
    font-size:8.2px!important;
  }
}
</style>"""

    js = r"""<script id="v217-other-reports-match-operation-js">
(function(){
  if(window.__V217_OTHER_REPORTS_MATCH_OPERATION)return;
  window.__V217_OTHER_REPORTS_MATCH_OPERATION=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const norm=v=>String(v||'').replace(/\s+/g,' ').trim().toLowerCase();

  const icons={
    grid:'<svg viewBox="0 0 24 24" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    conversion:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/></svg>',
    money:'<svg viewBox="0 0 24 24" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M16 8.5c-.8-.7-1.9-1-3.2-1-1.8 0-3.1.9-3.1 2.3 0 3.2 6.3 1.5 6.3 4.6 0 1.4-1.3 2.4-3.2 2.4-1.4 0-2.6-.4-3.5-1.2M12.8 5.5v13"/></svg>',
    store:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/></svg>',
    chart:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="m4 8 6-5 6 8 5-4"/></svg>',
    route:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M5 19c3-6 11-5 14-12"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="7" r="2"/></svg>',
    target:'<svg viewBox="0 0 24 24" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/></svg>',
    bell:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>',
    upload:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 20h14"/></svg>',
    settings:'<svg viewBox="0 0 24 24" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6.2L14.7 4h-4l-.3 2.2a8 8 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a8 8 0 0 0 1.5.9l.3 2.2h4l.3-2.2a8 8 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1Z"/></svg>',
    accordion:'<svg viewBox="0 0 24 24" stroke-width="1.8"><rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="4" rx="1.5"/><rect x="3" y="17" width="18" height="3" rx="1.5"/></svg>',
    pin:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z"/><circle cx="12" cy="10" r="2"/></svg>',
    checklist:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="M9 5h10M9 12h10M9 19h10"/><path d="m3 5 1.2 1.2L6.5 4M3 12l1.2 1.2L6.5 11M3 19l1.2 1.2L6.5 18"/></svg>',
    percent:'<svg viewBox="0 0 24 24" stroke-width="1.8"><path d="m6 18 12-12"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/></svg>',
    more:'<svg viewBox="0 0 24 24" stroke-width="1.8"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></svg>'
  };

  function cmMeta(btn){
    const key=String(btn.dataset.tabKey||'');
    const op=norm(btn.dataset.opview||'');
    if(key==='operations.center'||op==='centro ejecutivo'||op==='centro operativo')return['Centro Operativo','grid'];
    if(key==='operations.conversion'||op.includes('convers'))return['Conversión','conversion'];
    if(key==='operations.recovery'||op==='recuperación económica')return['Recuperación $','money'];
    if(key==='operations.recovery_store'||op.includes('recuperación por tienda'))return['Recuperación por Tienda','store'];
    if(key==='operations.productivity'||op.includes('productividad'))return['Productividad','chart'];
    if(key==='operations.routes'||op.includes('recorridos'))return['Recorridos','route'];
    if(key==='operations.score'||op.includes('índice')||op.includes('score'))return['Score','target'];
    if(key==='operations.alerts'||op.includes('alertas'))return['Alertas','bell'];
    if(btn.id==='openGoalsBtn'||op.includes('metas'))return['Metas y tiendas','settings'];
    if(op==='carga de datos')return['Carga de datos','upload'];
    const label=(btn.title||btn.textContent||'').trim();
    return[label||'Reporte','chart'];
  }

  function analysisMeta(btn){
    const sub=String(btn.dataset.sub||'');
    const map={
      macro:['Macro Compañía','chart'],
      accordion:['Acordeón Comercial','accordion'],
      stores:['Tiendas','store'],
      sections:['Sección / Rubro','grid'],
      areas:['Ubicación / Área','pin'],
      'lingerie-checklist':['Checklist Lencería','checklist'],
      'sell-through':['Sell Through','percent'],
      sellthrough:['Sell Through','percent'],
      more:['Más opciones','more'],
      'analysis-upload':['Carga de datos','upload']
    };
    if(map[sub])return map[sub];
    const raw=norm(btn.title||btn.textContent||'');
    if(raw.includes('sell through')||raw.includes('% sell'))return[(btn.title||btn.textContent||'Sell Through').trim(),'percent'];
    const label=(btn.title||btn.textContent||'').trim();
    return[label||'Reporte','grid'];
  }

  function decorate(host,kind){
    if(!host)return;
    [...host.children].forEach(node=>{
      if(!(node instanceof HTMLButtonElement))node.remove();
    });
    qa(':scope > button',host).forEach(btn=>{
      if(btn.hidden||btn.classList.contains('hidden')||btn.getAttribute('aria-hidden')==='true')return;
      const [label,icon]=kind==='cm'?cmMeta(btn):analysisMeta(btn);
      btn.dataset.v206Decorated='1';
      btn.dataset.v217Decorated='1';
      btn.innerHTML='<span class="v217-tab-icon" aria-hidden="true">'+(icons[icon]||icons.grid)+'</span><span class="v217-tab-label">'+label+'</span>';
      btn.title=label;
    });
  }

  function center(host,smooth=false){
    if(!host)return;
    const active=q(':scope > button.active:not(.hidden):not([hidden]),:scope > button[aria-selected="true"]:not(.hidden):not([hidden])',host);
    if(!active)return;
    const overflow=host.scrollWidth>host.clientWidth+4;
    if(!overflow)return;
    try{active.scrollIntoView({behavior:smooth?'smooth':'auto',block:'nearest',inline:'center'})}catch(_){}
  }

  function refresh(smooth=false){
    const mod=String(document.body.dataset.v213Module||'').toLowerCase();
    if(mod==='operativo'){
      const host=q('#operativoNav');decorate(host,'cm');center(host,smooth);
    }else if(mod==='analysis'){
      const host=q('#analysisNav');decorate(host,'analysis');center(host,smooth);
    }
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button,#analysisNav>button')){
      [20,100,280].forEach((ms,i)=>setTimeout(()=>refresh(i>0),ms));
    }
    const main=e.target.closest?.('[data-main]');
    if(main && ['operativo','analysis'].includes(main.dataset.main)){
      [50,180,500].forEach((ms,i)=>setTimeout(()=>refresh(i>0),ms));
    }
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(()=>refresh(false),30));
  const mo=new MutationObserver(muts=>{
    if(!muts.some(x=>x.type==='childList'||x.attributeName==='class'||x.attributeName==='aria-selected'||x.attributeName==='hidden'))return;
    setTimeout(()=>refresh(false),0);
  });

  function init(){
    const cm=q('#operativoNav'),an=q('#analysisNav');
    if(cm)mo.observe(cm,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected','hidden','aria-hidden']});
    if(an)mo.observe(an,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-selected','hidden','aria-hidden']});
    refresh(false);
    [120,420,1000].forEach(ms=>setTimeout(()=>refresh(false),ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
  window.addEventListener('resize',()=>setTimeout(()=>refresh(false),70),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(()=>refresh(false),140),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(()=>refresh(false),70),{passive:true});
  console.info('[V217] C&M y Análisis usan el mismo dock visual de Operación.');
})();
</script>"""

    @m.app.middleware("http")
    async def v217_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v217-other-reports-match-operation-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v217-other-reports-match-operation-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V217",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V217] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V217_OTHER_REPORTS_MATCH_OPERATION = True
    print("[V217] C&M + Análisis con el mismo dock de Operación.",flush=True)
