"""V269 · Opción 4 compacta en tarjetas de Operación.

Aplica exclusivamente a:
- Resumen: .v149-kpis / .v149-kpi
- Productividad (ranking): .v204-kpis / .v204-kpi

Diseño aprobado:
- cinta superior de color tipo KPI,
- icono circular,
- título dentro de la cinta,
- valor y detalle compactos,
- responsive sin tocar datos/cálculos.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V269_OPERATION_OPTION4_KPIS", False):
        return

    css = r'''<style id="v269-operation-option4-kpis-css">
/* =========================================================
   V269 · OPCIÓN 4 · CINTA SUPERIOR KPI · OPERACIÓN
   Sólo Resumen y Productividad ranking
   ========================================================= */

body[data-v163-module="operation"] .v149-kpis,
body[data-v163-module="operation"] .v204-kpis{
  display:grid!important;
  gap:8px!important;
  margin:8px 0 10px!important;
  align-items:stretch!important;
}
body[data-v163-module="operation"] .v149-kpis{
  grid-template-columns:repeat(4,minmax(0,1fr))!important;
}
body[data-v163-module="operation"] .v204-kpis{
  grid-template-columns:repeat(4,minmax(0,1fr))!important;
}

/* Tarjeta base compacta */
body[data-v163-module="operation"] .v149-kpi.v269-option4-card,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card{
  --v269:#1779ee;
  --v269-soft:#eaf4ff;
  position:relative!important;
  min-width:0!important;
  min-height:104px!important;
  padding:38px 11px 9px!important;
  overflow:hidden!important;
  border:1px solid #d6e3ef!important;
  border-radius:12px!important;
  background:#fff!important;
  box-shadow:0 4px 12px rgba(18,63,115,.06)!important;
}
body[data-v163-module="operation"] .v149-kpi.v269-option4-card:before,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card:before{
  display:none!important;
}

/* Cinta superior */
body[data-v163-module="operation"] .v269-option4-card .v269-ribbon{
  position:absolute!important;
  left:0!important;
  right:0!important;
  top:0!important;
  height:31px!important;
  display:flex!important;
  align-items:center!important;
  gap:7px!important;
  padding:0 9px 0 38px!important;
  color:#fff!important;
  background:linear-gradient(100deg,color-mix(in srgb,var(--v269) 84%,#073b75),var(--v269))!important;
  border-radius:11px 11px 3px 3px!important;
  clip-path:polygon(0 0,100% 0,95% 100%,0 100%)!important;
  box-sizing:border-box!important;
}

/* Icono circular compacto */
body[data-v163-module="operation"] .v269-option4-card .v269-icon{
  position:absolute!important;
  left:6px!important;
  top:50%!important;
  transform:translateY(-50%)!important;
  display:grid!important;
  place-items:center!important;
  width:25px!important;
  height:25px!important;
  border:2px solid rgba(255,255,255,.85)!important;
  border-radius:50%!important;
  color:var(--v269)!important;
  background:#fff!important;
  box-shadow:0 2px 5px rgba(0,0,0,.11)!important;
}
body[data-v163-module="operation"] .v269-option4-card .v269-icon svg{
  width:14px!important;
  height:14px!important;
  display:block!important;
}
body[data-v163-module="operation"] .v269-option4-card .v269-title{
  min-width:0!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:nowrap!important;
  color:#fff!important;
  font-size:7.2px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:.025em!important;
  text-transform:uppercase!important;
}

/* Título original oculto: ya vive en la cinta */
body[data-v163-module="operation"] .v149-kpi.v269-option4-card > small,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card > small{
  position:absolute!important;
  width:1px!important;
  height:1px!important;
  margin:-1px!important;
  padding:0!important;
  overflow:hidden!important;
  clip:rect(0,0,0,0)!important;
  white-space:nowrap!important;
  border:0!important;
}

/* Valor */
body[data-v163-module="operation"] .v149-kpi.v269-option4-card > b,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card > b{
  display:block!important;
  margin:5px 0 2px!important;
  color:#103f76!important;
  font-size:clamp(20px,1.65vw,27px)!important;
  line-height:.98!important;
  font-weight:950!important;
  letter-spacing:-.035em!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

/* Detalle */
body[data-v163-module="operation"] .v149-kpi.v269-option4-card > span:not(.v269-ribbon),
body[data-v163-module="operation"] .v204-kpi.v269-option4-card > span:not(.v269-ribbon){
  display:block!important;
  margin-top:4px!important;
  color:#6b7f96!important;
  font-size:7.5px!important;
  line-height:1.1!important;
  font-weight:600!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

/* Tonos por KPI */
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="blue"]{--v269:#168cff}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="purple"]{--v269:#7c3aed}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="pink"]{--v269:#ec007c}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="red"]{--v269:#ef4444}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="green"]{--v269:#10b981}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="orange"]{--v269:#f59e0b}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="teal"]{--v269:#0fb9b1}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="navy"]{--v269:#315779}

/* Resumen: todavía más compacto porque son 8/9 tarjetas. */
body[data-v163-module="operation"] .v149-kpis .v269-option4-card{
  min-height:98px!important;
}

/* Productividad: 4 tarjetas en una sola fila. */
body[data-v163-module="operation"] .v204-kpis .v269-option4-card{
  min-height:94px!important;
}

/* Tablet */
@media(max-width:1050px) and (min-width:601px){
  body[data-v163-module="operation"] .v149-kpis,
  body[data-v163-module="operation"] .v204-kpis{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:7px!important;
  }
  body[data-v163-module="operation"] .v149-kpi.v269-option4-card,
  body[data-v163-module="operation"] .v204-kpi.v269-option4-card{
    min-height:92px!important;
    padding:35px 9px 8px!important;
  }
}

/* Móvil: 2 por fila para conservar densidad. */
@media(max-width:600px){
  body[data-v163-module="operation"] .v149-kpis,
  body[data-v163-module="operation"] .v204-kpis{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:6px!important;
    margin:6px 0 8px!important;
  }
  body[data-v163-module="operation"] .v149-kpi.v269-option4-card,
  body[data-v163-module="operation"] .v204-kpi.v269-option4-card{
    min-height:82px!important;
    padding:31px 8px 7px!important;
    border-radius:10px!important;
  }
  body[data-v163-module="operation"] .v269-option4-card .v269-ribbon{
    height:27px!important;
    padding-left:34px!important;
    padding-right:6px!important;
  }
  body[data-v163-module="operation"] .v269-option4-card .v269-icon{
    width:22px!important;
    height:22px!important;
    left:5px!important;
  }
  body[data-v163-module="operation"] .v269-option4-card .v269-icon svg{
    width:12px!important;
    height:12px!important;
  }
  body[data-v163-module="operation"] .v269-option4-card .v269-title{
    font-size:6.2px!important;
  }
  body[data-v163-module="operation"] .v149-kpi.v269-option4-card > b,
  body[data-v163-module="operation"] .v204-kpi.v269-option4-card > b{
    font-size:18px!important;
    margin-top:3px!important;
  }
  body[data-v163-module="operation"] .v149-kpi.v269-option4-card > span:not(.v269-ribbon),
  body[data-v163-module="operation"] .v204-kpi.v269-option4-card > span:not(.v269-ribbon){
    font-size:6.6px!important;
  }
}
</style>'''

    js = r'''<script id="v269-operation-option4-kpis-js">
(function(){
  if(window.__V269_OPERATION_OPTION4_KPIS)return;
  window.__V269_OPERATION_OPTION4_KPIS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  const ICONS={
    truck:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
    bars:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 19V11M12 19V5M19 19v-9"/></svg>',
    cube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/><path d="M12 11v10"/></svg>',
    clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>',
    percent:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M19 5 5 19"/></svg>',
    people:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3"/><path d="M3 19v-1a6 6 0 0 1 12 0v1"/><circle cx="17" cy="9" r="2.3"/><path d="M15.5 14.5A5 5 0 0 1 21 19"/></svg>',
    target:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 2v3M22 12h-3M12 22v-3M2 12h3"/></svg>'
  };

  const summaryTones=['blue','purple','pink','red','green','orange','teal','navy','navy'];
  const prodTones=['blue','purple','orange','teal'];

  function iconFor(label){
    const t=String(label||'').toLowerCase();
    if(t.includes('llegada'))return ICONS.truck;
    if(t.includes('mercanc'))return ICONS.cube;
    if(t.includes('pendiente'))return ICONS.clock;
    if(t.includes('eficiencia')||t.includes('cumpl'))return ICONS.percent;
    if(t.includes('colaborador'))return ICONS.people;
    if(t.includes('prod'))return ICONS.bars;
    if(t.includes('pieza'))return ICONS.cube;
    return ICONS.target;
  }

  function decorateCard(card,tone){
    if(!card)return;
    card.classList.add('v269-option4-card');
    card.dataset.v269Tone=tone;

    const label=q(':scope > small',card)?.textContent?.trim()||'Indicador';
    let ribbon=q(':scope > .v269-ribbon',card);
    if(!ribbon){
      ribbon=document.createElement('div');
      ribbon.className='v269-ribbon';
      card.insertBefore(ribbon,card.firstChild);
    }
    if(ribbon.dataset.label!==label){
      ribbon.dataset.label=label;
      ribbon.innerHTML='<span class="v269-icon">'+iconFor(label)+'</span><span class="v269-title"></span>';
      const title=q('.v269-title',ribbon);
      if(title)title.textContent=label;
    }
  }

  function enforce(){
    if(String(document.body.dataset.v163Module||'').toLowerCase()!=='operation')return;

    qa('.v149-kpis').forEach(grid=>{
      qa(':scope > .v149-kpi',grid).forEach((card,i)=>decorateCard(card,summaryTones[i%summaryTones.length]));
    });

    qa('.v204-kpis').forEach(grid=>{
      qa(':scope > .v204-kpi',grid).forEach((card,i)=>decorateCard(card,prodTones[i%prodTones.length]));
    });
  }

  let timer=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(timer);
    timer=setTimeout(enforce,20);
  });

  function start(){
    const root=document.getElementById('operativoDynamic')||document.body;
    observer.observe(root,{subtree:true,childList:true});
    enforce();
    [80,220,500,1000,1800].forEach(ms=>setTimeout(enforce,ms));
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#v200OperationTabs [data-v200-op]')||
       e.target.closest?.('#operativoPeriodBar')){
      [0,60,180,420].forEach(ms=>setTimeout(enforce,ms));
    }
  },true);

  document.addEventListener('change',e=>{
    if(e.target?.closest?.('#operativoPeriodBar')){
      [0,80,220].forEach(ms=>setTimeout(enforce,ms));
    }
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V269] Opción 4 compacta activa en Resumen y Productividad de Operación.');
})();
</script>'''

    @m.app.middleware("http")
    async def v269_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v269-operation-option4-kpis-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v269-operation-option4-kpis-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V269-OPTION4-KPIS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V269] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V269_OPERATION_OPTION4_KPIS=True
    print("[V269] Opción 4 compacta instalada en Resumen y Productividad.",flush=True)
