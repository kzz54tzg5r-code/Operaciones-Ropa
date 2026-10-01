"""V203 · Operación · UI estilo opción 7 para las cinco pestañas.

Sólo modifica presentación. No cambia endpoints, cálculos, filtros ni persistencia.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V203_OPERATION_OPTION7_UI", False):
        return

    css = r'''<style id="v203-operation-option7-css">
/* ================================================================
   V203 · OPERACIÓN · OPCIÓN 7
   ================================================================ */
body[data-v163-module="operation"] #operativoDynamic{
  --op7-blue:#0d4f8b;
  --op7-blue-2:#0878df;
  --op7-ink:#123f73;
  --op7-muted:#70849a;
  --op7-line:#d6e3f0;
  --op7-soft:#f5f9fe;
  --op7-shadow:0 10px 28px rgba(14,79,139,.10);
}

/* ---- barra de 5 pestañas: dock visual ---- */
body[data-v163-module="operation"] #v200OperationTabs{
  display:grid!important;
  grid-template-columns:repeat(5,minmax(0,1fr));
  gap:9px;
  width:100%;
  overflow:visible;
  padding:7px 3px 12px;
  margin:3px 0 9px;
  background:transparent;
}
body[data-v163-module="operation"] #v200OperationTabs button{
  position:relative;
  min-width:0;
  width:100%;
  min-height:82px;
  padding:8px 8px 10px;
  border:1px solid var(--op7-line);
  border-radius:18px;
  background:rgba(255,255,255,.96);
  color:#55718d;
  box-shadow:0 5px 18px rgba(28,72,116,.06);
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:6px;
  font-size:9px;
  line-height:1.15;
  font-weight:850;
  white-space:normal;
  text-align:center;
  transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease;
  scroll-snap-align:center;
}
body[data-v163-module="operation"] #v200OperationTabs button:hover{
  transform:translateY(-1px);
  border-color:#b7cfe7;
  box-shadow:0 8px 22px rgba(28,72,116,.10);
}
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon{
  width:38px;height:38px;border-radius:13px;
  display:grid;place-items:center;
  background:#edf5fd;
  color:#567c9f;
  border:1px solid #dce8f4;
  transition:all .18s ease;
}
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon svg{
  width:21px;height:21px;display:block;
}
body[data-v163-module="operation"] #v200OperationTabs .v203-tab-label{
  display:block;
  max-width:100%;
}
body[data-v163-module="operation"] #v200OperationTabs button.active{
  color:#fff;
  border-color:#0a5da7;
  background:linear-gradient(145deg,var(--op7-blue) 0%,var(--op7-blue-2) 100%);
  box-shadow:0 12px 28px rgba(13,79,139,.24);
  transform:translateY(-2px);
}
body[data-v163-module="operation"] #v200OperationTabs button.active .v203-tab-icon{
  background:rgba(255,255,255,.14);
  border-color:rgba(255,255,255,.22);
  color:#fff;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.04);
}
body[data-v163-module="operation"] #v200OperationTabs button.active:after{
  content:"";
  position:absolute;
  left:50%;bottom:-7px;
  width:32px;height:4px;
  transform:translateX(-50%);
  border-radius:999px;
  background:#1185ef;
  box-shadow:0 2px 7px rgba(17,133,239,.24);
}

/* ---- encabezado de la vista ---- */
body[data-v163-module="operation"] #operativoDynamicTitle{
  color:var(--op7-ink);
  font-weight:950;
  letter-spacing:-.025em;
}
body[data-v163-module="operation"] #operativoDynamicSub{
  color:var(--op7-muted);
  font-weight:650;
}

/* ---- filtro único, integrado con la estética ---- */
body[data-v163-module="operation"] #operativoPeriodBar{
  border:1px solid var(--op7-line)!important;
  border-radius:18px!important;
  background:#fff!important;
  box-shadow:var(--op7-shadow)!important;
  overflow:hidden!important;
  margin:7px 0 12px!important;
}
body[data-v163-module="operation"] #operativoPeriodBar .v161-filter-head,
body[data-v163-module="operation"] #operativoPeriodBar .filter-head{
  background:linear-gradient(135deg,#103f72,#0878df)!important;
  color:#fff!important;
}
body[data-v163-module="operation"] #operativoPeriodBar label{
  color:#61758b!important;
  font-size:8px!important;
  font-weight:900!important;
  letter-spacing:.04em!important;
}
body[data-v163-module="operation"] #operativoPeriodBar select,
body[data-v163-module="operation"] #operativoPeriodBar input{
  border:1px solid #cbd9e8!important;
  border-radius:12px!important;
  background:#fbfdff!important;
  color:var(--op7-ink)!important;
  min-height:44px!important;
  box-shadow:none!important;
}
body[data-v163-module="operation"] #operPeriodApply{
  border:0!important;
  border-radius:12px!important;
  background:linear-gradient(135deg,#176fe8,#0a83ef)!important;
  color:#fff!important;
  min-height:44px!important;
  font-weight:950!important;
  box-shadow:0 8px 18px rgba(23,111,232,.18)!important;
}

/* ---- cards comunes de las 5 vistas ---- */
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi,
body[data-v163-module="operation"] #operativoDynamicContent .v149-panel,
body[data-v163-module="operation"] #operativoDynamicContent .v200-op-card,
body[data-v163-module="operation"] #operativoDynamicContent .v201-demo-card,
body[data-v163-module="operation"] #operativoDynamicContent .panel{
  border:1px solid var(--op7-line)!important;
  border-radius:16px!important;
  background:#fff!important;
  box-shadow:0 6px 20px rgba(25,72,118,.06)!important;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi{
  min-height:112px;
  padding:13px!important;
  overflow:hidden;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi small,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi .rk-label{
  color:#6c7e92!important;
  font-size:7.5px!important;
  font-weight:950!important;
  text-transform:uppercase;
  letter-spacing:.04em;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi b,
body[data-v163-module="operation"] #operativoDynamicContent .report-kpi .rk-value{
  color:var(--op7-ink)!important;
  font-weight:950!important;
  letter-spacing:-.03em;
}
body[data-v163-module="operation"] #operativoDynamicContent .v149-panel h3,
body[data-v163-module="operation"] #operativoDynamicContent .v200-op-card h3,
body[data-v163-module="operation"] #operativoDynamicContent .v201-demo-card h3{
  color:var(--op7-ink)!important;
  font-weight:950!important;
  letter-spacing:-.02em;
}

/* ---- tablas ---- */
body[data-v163-module="operation"] #operativoDynamicContent .tablewrap,
body[data-v163-module="operation"] #operativoDynamicContent .v201-demo-tablewrap{
  border:1px solid #d8e4ef!important;
  border-radius:13px!important;
  overflow:auto!important;
  background:#fff!important;
  -webkit-overflow-scrolling:touch;
}
body[data-v163-module="operation"] #operativoDynamicContent table{
  border-collapse:separate!important;
  border-spacing:0!important;
}
body[data-v163-module="operation"] #operativoDynamicContent table thead th{
  background:#124d84!important;
  color:#fff!important;
  font-weight:900!important;
  border-color:rgba(255,255,255,.16)!important;
  white-space:nowrap;
}
body[data-v163-module="operation"] #operativoDynamicContent table tbody tr:nth-child(even) td{
  background:#f8fbfe!important;
}
body[data-v163-module="operation"] #operativoDynamicContent table tbody tr:hover td{
  background:#eef6ff!important;
}

/* ---- Cargar productividad ---- */
body[data-v163-module="operation"] .v200-op-card{
  padding:16px!important;
}
body[data-v163-module="operation"] .v200-op-timer{
  background:linear-gradient(145deg,#eef5ff,#e6f1fd)!important;
  color:#0e467e!important;
  border:1px solid #d6e5f4;
  border-radius:15px!important;
  min-width:150px;
  font-size:29px!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8);
}
body[data-v163-module="operation"] .v200-op-auto span{
  background:#f7faff!important;
  border:1px solid #dbe6f1!important;
  color:#60758d!important;
  font-weight:750!important;
}
body[data-v163-module="operation"] .v200-op-field select,
body[data-v163-module="operation"] .v200-op-field input{
  border-radius:12px!important;
  border:1px solid #ccd9e7!important;
  background:#fbfdff!important;
}
body[data-v163-module="operation"] .v200-op-start{
  border-radius:12px!important;
  background:linear-gradient(135deg,#12a64b,#17b95a)!important;
  box-shadow:0 8px 18px rgba(18,166,75,.18);
}
body[data-v163-module="operation"] .v200-op-finish{
  border-radius:12px!important;
  background:linear-gradient(135deg,#ef8c8c,#f59c9c)!important;
}

/* ---- DEMO ---- */
body[data-v163-module="operation"] .v201-demo-toolbar{
  justify-content:flex-end!important;
  margin:0 0 8px!important;
}
body[data-v163-module="operation"] .v201-demo-btn{
  min-height:34px;
  border-radius:10px!important;
  padding:7px 12px!important;
}
body[data-v163-module="operation"] .v201-demo-grid{
  gap:9px!important;
}
body[data-v163-module="operation"] .v201-demo-kpi{
  border-radius:15px!important;
  box-shadow:0 5px 18px rgba(25,72,118,.05);
}
body[data-v163-module="operation"] .v201-demo-note{
  border-radius:13px!important;
  background:linear-gradient(135deg,#f0f7ff,#eaf5ff)!important;
}

/* ---- jerarquía y ritmo visual ---- */
body[data-v163-module="operation"] #operativoDynamicContent{
  animation:v203Fade .18s ease-out;
}
@keyframes v203Fade{
  from{opacity:.55;transform:translateY(3px)}
  to{opacity:1;transform:none}
}

/* ================================================================
   MÓVIL · mismo patrón, navegación uno por uno
   ================================================================ */
@media(max-width:900px){
  body[data-v163-module="operation"] #v200OperationTabs{
    display:flex!important;
    grid-template-columns:none;
    gap:8px;
    overflow-x:auto;
    overflow-y:visible;
    scroll-snap-type:x mandatory;
    padding:7px max(14px,calc((100vw - 112px)/2)) 13px;
    margin-left:-13px;
    margin-right:-13px;
    width:auto;
    scrollbar-width:none;
    scroll-padding-inline:calc((100vw - 112px)/2);
  }
  body[data-v163-module="operation"] #v200OperationTabs::-webkit-scrollbar{display:none}
  body[data-v163-module="operation"] #v200OperationTabs button{
    flex:0 0 112px;
    width:112px;
    min-height:76px;
    border-radius:17px;
    scroll-snap-align:center;
    font-size:8.2px;
    padding:7px 6px 9px;
  }
  body[data-v163-module="operation"] #v200OperationTabs button.active{
    flex-basis:118px;
  }
  body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon{
    width:34px;height:34px;border-radius:12px;
  }
  body[data-v163-module="operation"] #v200OperationTabs .v203-tab-icon svg{
    width:19px;height:19px;
  }
  body[data-v163-module="operation"] #operativoDynamicTitle{
    font-size:21px!important;
  }
  body[data-v163-module="operation"] #operativoDynamicSub{
    font-size:9px!important;
    line-height:1.35;
  }
  body[data-v163-module="operation"] #operativoPeriodBar{
    border-radius:15px!important;
  }
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpis,
  body[data-v163-module="operation"] #operativoDynamicContent .report-kpis,
  body[data-v163-module="operation"] #operativoDynamicContent .v201-demo-grid{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:7px!important;
  }
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi,
  body[data-v163-module="operation"] #operativoDynamicContent .report-kpi{
    min-height:102px;
    padding:11px!important;
  }
  body[data-v163-module="operation"] .v200-op-card{
    border-radius:15px!important;
    padding:13px!important;
  }
  body[data-v163-module="operation"] .v200-op-head{
    gap:8px!important;
  }
  body[data-v163-module="operation"] .v200-op-timer{
    font-size:24px!important;
    min-width:132px;
  }
  body[data-v163-module="operation"] .v200-op-grid{
    grid-template-columns:1fr 1fr!important;
  }
  body[data-v163-module="operation"] #operativoDynamicContent table{
    font-size:8px!important;
  }
}
@media(max-width:390px){
  body[data-v163-module="operation"] .v200-op-grid{grid-template-columns:1fr!important}
}
</style>'''

    js = r'''<script id="v203-operation-option7-js">
(function(){
  if(window.__V203_OPERATION_OPTION7_UI)return;
  window.__V203_OPERATION_OPTION7_UI=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];

  const icons={
    summary:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    daily:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/><path d="M8 14h3M8 17h6"/></svg>',
    capture:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6M17 5l2-2"/></svg>',
    productivity:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/><path d="m4 8 6-5 6 8 5-4"/></svg>',
    standards:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/></svg>'
  };
  const labels={
    summary:'Resumen',
    daily:'Captura diaria',
    capture:'Cargar productividad',
    productivity:'Productividad',
    standards:'Estándares'
  };

  function isOperation(){
    return String(document.body.dataset.v163Module||'').toLowerCase()==='operation';
  }

  function decorate(){
    const host=q('#v200OperationTabs');if(!host)return;
    qa('[data-v200-op]',host).forEach(btn=>{
      const key=btn.dataset.v200Op;
      if(!icons[key])return;
      if(btn.dataset.v203Decorated!=='1'){
        btn.dataset.v203Decorated='1';
        btn.innerHTML='<span class="v203-tab-icon" aria-hidden="true">'+icons[key]+'</span><span class="v203-tab-label">'+labels[key]+'</span>';
      }
      btn.title=labels[key];
    });
    centerActive(false);
  }

  function centerActive(smooth=true){
    if(!isOperation()||window.innerWidth>900)return;
    const active=q('#v200OperationTabs [data-v200-op].active');if(!active)return;
    try{active.scrollIntoView({behavior:smooth?'smooth':'auto',block:'nearest',inline:'center'})}catch(_){}
  }

  function tagActiveView(){
    const active=q('#v200OperationTabs [data-v200-op].active');
    const key=active?.dataset.v200Op||'summary';
    document.body.dataset.v203OperationTab=key;
  }

  function refresh(smooth=false){
    if(!isOperation())return;
    decorate();
    tagActiveView();
    centerActive(smooth);
  }

  document.addEventListener('click',e=>{
    const tab=e.target.closest?.('#v200OperationTabs [data-v200-op]');
    if(tab){
      [40,160,380].forEach((ms,i)=>setTimeout(()=>refresh(i>0),ms));
    }
    const main=e.target.closest?.('[data-main]');
    if(main?.dataset.main==='operation'){
      [80,260,700].forEach((ms,i)=>setTimeout(()=>refresh(i>0),ms));
    }
  },true);

  const observer=new MutationObserver(()=>{if(isOperation())refresh(false)});
  if(document.documentElement)observer.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-v163-module']});

  function setup(){if(isOperation())refresh(false)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [180,500,1200,2400].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('resize',()=>setTimeout(()=>centerActive(false),80),{passive:true});
  window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});
  console.info('[V203] Operación estilizada con opción 7 en sus cinco pestañas.');
})();
</script>'''

    @m.app.middleware("http")
    async def v203_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v203-operation-option7-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v203-operation-option7-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V203",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V203] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V203_OPERATION_OPTION7_UI = True
    print("[V203] Opción 7 aplicada a las cinco pestañas de Operación.", flush=True)
