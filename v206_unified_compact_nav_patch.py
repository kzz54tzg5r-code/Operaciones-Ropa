"""V206 · Navegación compacta unificada + corrección visual Operación.

Patrón final:
- Cambios y Muertos, Operación y Análisis Comercial usan el mismo dock compacto.
- Mantiene carrusel horizontal, snap y centrado de la pestaña activa.
- Operación conserva sus iconos V203 pero a escala compacta.
- Corrige iconos/decoraciones que invadían los valores de KPI.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V206_UNIFIED_COMPACT_NAV", False):
        return

    css = r'''<style id="v206-unified-compact-nav-css">
/* ===============================================================
   PATRÓN ÚNICO DE NAVEGACIÓN INTERNA
   =============================================================== */
#operativoNav.op-tabs,
#analysisNav,
body[data-v163-module="operation"] #v200OperationTabs{
  display:flex!important;
  grid-template-columns:none!important;
  flex-wrap:nowrap!important;
  align-items:flex-start!important;
  gap:5px!important;
  width:100%!important;
  max-width:100%!important;
  min-height:70px!important;
  height:auto!important;
  margin:2px 0 8px!important;
  padding:4px 6px 8px!important;
  border:0!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  white-space:nowrap!important;
  -webkit-overflow-scrolling:touch!important;
  overscroll-behavior-x:contain!important;
  scroll-snap-type:x mandatory!important;
  scroll-behavior:smooth;
  scrollbar-width:none!important;
}
#operativoNav.op-tabs::-webkit-scrollbar,
#analysisNav::-webkit-scrollbar,
body[data-v163-module="operation"] #v200OperationTabs::-webkit-scrollbar{display:none!important}

#operativoNav.op-tabs>button,
#analysisNav>button,
body[data-v163-module="operation"] #v200OperationTabs>button{
  position:relative!important;
  display:flex!important;
  flex:0 0 82px!important;
  width:82px!important;
  min-width:82px!important;
  max-width:82px!important;
  height:62px!important;
  min-height:62px!important;
  max-height:62px!important;
  margin:0!important;
  padding:4px 3px 5px!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:3px!important;
  border:1px solid transparent!important;
  border-radius:14px!important;
  background:transparent!important;
  color:#607991!important;
  box-shadow:none!important;
  transform:none!important;
  font-size:7.2px!important;
  line-height:1.08!important;
  font-weight:850!important;
  white-space:normal!important;
  text-align:center!important;
  scroll-snap-align:center!important;
  scroll-snap-stop:always!important;
  touch-action:pan-x!important;
}
#operativoNav.op-tabs>button.hidden,
#analysisNav>button.hidden,
#operativoNav.op-tabs>button[hidden],
#analysisNav>button[hidden]{display:none!important}

#operativoNav .v206-tab-icon,
#analysisNav .v206-tab-icon,
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon{
  display:grid!important;
  place-items:center!important;
  flex:0 0 32px!important;
  width:32px!important;
  min-width:32px!important;
  max-width:32px!important;
  height:32px!important;
  min-height:32px!important;
  max-height:32px!important;
  margin:0!important;
  padding:0!important;
  border:1px solid #d8e5f1!important;
  border-radius:50%!important;
  background:#fff!important;
  color:#597d9f!important;
  box-shadow:0 2px 7px rgba(18,70,118,.06)!important;
  transform:none!important;
}
#operativoNav .v206-tab-icon svg,
#analysisNav .v206-tab-icon svg,
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon svg{
  display:block!important;
  width:17px!important;
  height:17px!important;
  max-width:17px!important;
  max-height:17px!important;
  margin:0!important;
  stroke:currentColor!important;
  transform:none!important;
}
#operativoNav .v206-tab-label,
#analysisNav .v206-tab-label,
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-label{
  display:block!important;
  width:100%!important;
  max-width:100%!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:normal!important;
  line-height:1.08!important;
  text-align:center!important;
}

#operativoNav.op-tabs>button.active,
#analysisNav>button.active,
body[data-v163-module="operation"] #v200OperationTabs>button.active{
  color:#fff!important;
  border-color:#0a5da7!important;
  background:linear-gradient(145deg,#0d4f8b 0%,#0878df 100%)!important;
  box-shadow:0 7px 17px rgba(13,79,139,.19)!important;
  transform:none!important;
}
#operativoNav.op-tabs>button.active .v206-tab-icon,
#analysisNav>button.active .v206-tab-icon,
body[data-v163-module="operation"] #v200OperationTabs>button.active .v203-tab-icon{
  border-color:rgba(255,255,255,.22)!important;
  background:rgba(255,255,255,.10)!important;
  color:#fff!important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.04)!important;
}
#operativoNav.op-tabs>button.active:after,
#analysisNav>button.active:after,
body[data-v163-module="operation"] #v200OperationTabs>button.active:after{
  content:""!important;
  position:absolute!important;
  left:50%!important;
  right:auto!important;
  top:auto!important;
  bottom:-6px!important;
  width:26px!important;
  height:3px!important;
  border-radius:999px!important;
  background:#1185ef!important;
  transform:translateX(-50%)!important;
  box-shadow:0 2px 5px rgba(17,133,239,.20)!important;
}

/* Operación: ya no vuelve al dock grande de V203. */
@media(min-width:901px){
  body[data-v163-module="operation"] #v200OperationTabs{
    justify-content:center!important;
  }
}

/* ===============================================================
   KPI OPERACIÓN: icono y cifra nunca comparten la misma zona
   =============================================================== */
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi{
  position:relative!important;
  min-height:100px!important;
  padding:11px 12px!important;
  overflow:hidden!important;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi small,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi .rk-label{
  position:relative!important;
  z-index:3!important;
  display:block!important;
  min-height:18px!important;
  padding-right:38px!important;
  margin:0!important;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi b,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi .rk-value{
  position:relative!important;
  z-index:3!important;
  display:block!important;
  clear:both!important;
  margin:7px 0 3px!important;
  padding:0!important;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi span,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi .rk-sub{
  position:relative!important;
  z-index:3!important;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi > svg,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi > svg,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi > [class*="icon"],
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi > [class*="icon"]{
  position:absolute!important;
  z-index:1!important;
  top:9px!important;
  right:10px!important;
  left:auto!important;
  bottom:auto!important;
  width:28px!important;
  height:28px!important;
  max-width:28px!important;
  max-height:28px!important;
  margin:0!important;
  pointer-events:none!important;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi:after,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi:after{
  top:9px!important;
  right:10px!important;
  left:auto!important;
  bottom:auto!important;
  max-width:28px!important;
  max-height:28px!important;
  opacity:.72!important;
  pointer-events:none!important;
}

/* DEMO visible y ordenado arriba del dock. */
body[data-v163-module="operation"] .v201-demo-toolbar{
  display:flex;
  justify-content:flex-end!important;
  align-items:center!important;
  gap:6px!important;
  margin:0 0 3px!important;
}
body[data-v163-module="operation"] .v201-demo-btn{
  min-height:30px!important;
  height:30px!important;
  padding:0 10px!important;
  font-size:8px!important;
  border-radius:9px!important;
}

/* Móvil: mismo tamaño visual, carrusel centrado uno a uno. */
@media(max-width:900px){
  #operativoNav.op-tabs,
  #analysisNav,
  body[data-v163-module="operation"] #v200OperationTabs{
    justify-content:flex-start!important;
    gap:5px!important;
    min-height:68px!important;
    padding:4px max(12px,calc((100vw - 76px)/2)) 8px!important;
    margin-left:-6px!important;
    margin-right:-6px!important;
    width:auto!important;
    max-width:none!important;
    scroll-padding-inline:calc((100vw - 76px)/2)!important;
  }
  #operativoNav.op-tabs>button,
  #analysisNav>button,
  body[data-v163-module="operation"] #v200OperationTabs>button{
    flex-basis:76px!important;
    width:76px!important;
    min-width:76px!important;
    max-width:76px!important;
    height:60px!important;
    min-height:60px!important;
    max-height:60px!important;
    font-size:6.9px!important;
    border-radius:13px!important;
  }
  #operativoNav .v206-tab-icon,
  #analysisNav .v206-tab-icon,
  body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon{
    width:31px!important;min-width:31px!important;max-width:31px!important;
    height:31px!important;min-height:31px!important;max-height:31px!important;
  }
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi,
  body[data-v163-module="operation"] #operativoDynamicContent .report-kpi{
    min-height:96px!important;
  }
}
</style>'''

    js = r'''<script id="v206-unified-compact-nav-js">
(function(){
  if(window.__V206_UNIFIED_COMPACT_NAV)return;
  window.__V206_UNIFIED_COMPACT_NAV=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];

  const iconMap={
    'centro ejecutivo':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    'conversión':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7h12l-3-3m3 3-3 3M17 17H5l3 3m-3-3 3-3"/></svg>',
    'recuperación económica':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M15 8.5c-.7-.7-1.7-1-3-1-1.7 0-3 .8-3 2s1.3 1.8 3 2 3 .8 3 2-1.3 2-3 2c-1.3 0-2.4-.4-3-1M12 5v14"/></svg>',
    'recuperación por tienda':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h16M6 10V7l2-3h8l2 3v3M6 10v9h12v-9M9 19v-5h6v5"/></svg>',
    'productividad por colaborador':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="m4 8 6-5 6 8 5-4"/></svg>',
    'cumplimiento de recorridos':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 17c3-1 2-5 5-6s3-3 3-3"/></svg>',
    'índice integral':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3M21 12h-3M12 21v-3M3 12h3"/></svg>',
    'alertas inteligentes':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>',
    'carga de datos':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 16V4m0 0L7 9m5-5 5 5M4 20h16"/></svg>',
    'metas y tiendas':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19 13.5v-3l-2-.6-.7-1.7 1-1.8-2.1-2.1-1.8 1-1.7-.7L11 2H8l-.6 2.6-1.7.7-1.8-1-2.1 2.1 1 1.8-.7 1.7-2 .6v3l2 .6.7 1.7-1 1.8 2.1 2.1 1.8-1 1.7.7L8 22h3l.6-2.6 1.7-.7 1.8 1 2.1-2.1-1-1.8.7-1.7 2-.6Z"/></svg>',
    'macro compañía':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    'acordeón comercial':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="4" rx="1"/><rect x="4" y="10" width="16" height="4" rx="1"/><rect x="4" y="16" width="16" height="4" rx="1"/></svg>',
    'tiendas':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h16M6 10V7l2-3h8l2 3v3M6 10v9h12v-9"/></svg>',
    'sección / rubro':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    'ubicación / área':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    'checklist lencería':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m5 7 2 2 4-4M5 14l2 2 4-4M13 8h6M13 15h6"/></svg>',
    'más opciones':'<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/></svg>'
  };
  const fallback='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/><path d="M8 12h8M12 8v8"/></svg>';

  function cleanLabel(btn){
    const existing=btn.querySelector('.v206-tab-label,.v203-tab-label');
    if(existing)return existing.textContent.trim();
    return (btn.textContent||'').trim();
  }

  function decorateStandard(host){
    if(!host)return;
    qa(':scope > button',host).forEach(btn=>{
      if(btn.closest('#v200OperationTabs'))return;
      if(btn.dataset.v206Decorated==='1')return;
      const label=cleanLabel(btn);
      const key=String(btn.dataset.opview||btn.dataset.sub||label).trim().toLowerCase();
      const aliases={
        'macro':'macro compañía',
        'accordion':'acordeón comercial',
        'stores':'tiendas',
        'sections':'sección / rubro',
        'areas':'ubicación / área',
        'lingerie-checklist':'checklist lencería',
        'more':'más opciones',
        'analysis-upload':'carga de datos'
      };
      const iconKey=aliases[key]||key;
      const labelKey=String(label||'').trim().toLowerCase();
      btn.dataset.v206Decorated='1';
      btn.innerHTML='<span class="v206-tab-icon" aria-hidden="true">'+(iconMap[iconKey]||iconMap[labelKey]||fallback)+'</span><span class="v206-tab-label">'+label+'</span>';
      btn.title=label;
    });
  }

  function center(host,smooth=false){
    if(!host||host.classList.contains('hidden'))return;
    const active=host.querySelector(':scope > button.active:not(.hidden):not([hidden])');
    if(!active)return;
    try{
      active.scrollIntoView({behavior:smooth?'smooth':'auto',block:'nearest',inline:'center'});
    }catch(_){}
  }

  function refresh(smooth=false){
    const op=q('#operativoNav'),an=q('#analysisNav'),operation=q('#v200OperationTabs');
    decorateStandard(op);decorateStandard(an);
    [op,an,operation].forEach(h=>center(h,smooth));
  }

  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#operativoNav>button,#analysisNav>button,#v200OperationTabs>button');
    if(btn)[40,150,320].forEach((ms,i)=>setTimeout(()=>refresh(i>0),ms));
    const main=e.target.closest?.('[data-main]');
    if(main)[80,240,600].forEach((ms,i)=>setTimeout(()=>refresh(i>0),ms));
  },true);

  document.addEventListener('report-tabs-visibility-changed',()=>setTimeout(()=>refresh(false),40));
  const obs=new MutationObserver(()=>setTimeout(()=>refresh(false),0));
  ['operativoNav','analysisNav','v200OperationTabs'].forEach(id=>{
    const h=document.getElementById(id);
    if(h)obs.observe(h,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-hidden']});
  });

  function setup(){refresh(false)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [180,600,1400,2800].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('resize',()=>setTimeout(()=>refresh(false),100),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});
  console.info('[V206] Navegación compacta unificada instalada.');
})();
</script>'''

    @m.app.middleware("http")
    async def v206_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v206-unified-compact-nav-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v206-unified-compact-nav-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V206",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V206] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V206_UNIFIED_COMPACT_NAV=True
    print("[V206] Navegación compacta unificada + KPI Operación corregidos.",flush=True)
