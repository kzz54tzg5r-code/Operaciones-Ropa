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
/* V269.1 · Opción 4 ultra compacta · Resumen + Productividad */
body[data-v163-module="operation"] .v149-kpis,
body[data-v163-module="operation"] .v204-kpis{
  display:grid!important;
  gap:6px!important;
  margin:6px 0 8px!important;
  align-items:stretch!important;
}
body[data-v163-module="operation"] .v149-kpis{grid-template-columns:repeat(5,minmax(0,1fr))!important}
body[data-v163-module="operation"] .v204-kpis{grid-template-columns:repeat(4,minmax(0,1fr))!important}

body[data-v163-module="operation"] .v149-kpi.v269-option4-card,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card{
  position:relative!important;
  box-sizing:border-box!important;
  height:78px!important;
  min-height:78px!important;
  max-height:78px!important;
  padding:28px 8px 6px!important;
  margin:0!important;
  overflow:hidden!important;
  border:1px solid #d5e2ef!important;
  border-radius:10px!important;
  background:#fff!important;
  box-shadow:0 3px 9px rgba(18,63,115,.05)!important;
}
body[data-v163-module="operation"] .v149-kpi.v269-option4-card:before,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card:before{display:none!important}

body[data-v163-module="operation"] .v269-option4-card .v269-ribbon{
  position:absolute!important;
  z-index:5!important;
  left:0!important;
  right:0!important;
  top:0!important;
  width:100%!important;
  height:24px!important;
  min-height:24px!important;
  display:flex!important;
  align-items:center!important;
  gap:5px!important;
  padding:0 6px 0 30px!important;
  box-sizing:border-box!important;
  border-radius:9px 9px 0 0!important;
  background:var(--v269,#1679e8)!important;
  color:#fff!important;
  opacity:1!important;
  visibility:visible!important;
  clip-path:none!important;
}
body[data-v163-module="operation"] .v269-option4-card .v269-icon{
  position:absolute!important;
  z-index:6!important;
  left:5px!important;
  top:3px!important;
  transform:none!important;
  display:grid!important;
  place-items:center!important;
  width:18px!important;
  height:18px!important;
  min-width:18px!important;
  min-height:18px!important;
  border:1.5px solid rgba(255,255,255,.92)!important;
  border-radius:50%!important;
  background:#fff!important;
  color:var(--v269,#1679e8)!important;
  box-shadow:none!important;
}
body[data-v163-module="operation"] .v269-option4-card .v269-icon svg{
  width:10px!important;height:10px!important;display:block!important
}
body[data-v163-module="operation"] .v269-option4-card .v269-title{
  display:block!important;
  min-width:0!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:nowrap!important;
  color:#fff!important;
  font-size:7px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:.01em!important;
  text-transform:uppercase!important;
}

body[data-v163-module="operation"] .v149-kpi.v269-option4-card > small,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card > small{
  display:none!important;
}

body[data-v163-module="operation"] .v149-kpi.v269-option4-card > b,
body[data-v163-module="operation"] .v204-kpi.v269-option4-card > b{
  display:block!important;
  margin:2px 0 0!important;
  padding:0!important;
  color:#103f76!important;
  font-size:20px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:-.025em!important;
  white-space:nowrap!important;
}
body[data-v163-module="operation"] .v149-kpi.v269-option4-card > span:not(.v269-ribbon),
body[data-v163-module="operation"] .v204-kpi.v269-option4-card > span:not(.v269-ribbon){
  display:block!important;
  margin:3px 0 0!important;
  padding:0!important;
  color:#6b7f96!important;
  font-size:6.8px!important;
  line-height:1!important;
  font-weight:650!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="blue"]{--v269:#168cff}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="purple"]{--v269:#7c3aed}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="pink"]{--v269:#e91e78}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="red"]{--v269:#ef4444}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="green"]{--v269:#10b981}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="orange"]{--v269:#f59e0b}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="teal"]{--v269:#0fa9a2}
body[data-v163-module="operation"] .v269-option4-card[data-v269-tone="navy"]{--v269:#1d568d}

@media(max-width:1100px) and (min-width:701px){
  body[data-v163-module="operation"] .v149-kpis{grid-template-columns:repeat(4,minmax(0,1fr))!important}
  body[data-v163-module="operation"] .v204-kpis{grid-template-columns:repeat(4,minmax(0,1fr))!important}
}
@media(max-width:700px){
  body[data-v163-module="operation"] .v149-kpis,
  body[data-v163-module="operation"] .v204-kpis{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:5px!important;
  }
  body[data-v163-module="operation"] .v149-kpi.v269-option4-card,
  body[data-v163-module="operation"] .v204-kpi.v269-option4-card{
    height:70px!important;
    min-height:70px!important;
    max-height:70px!important;
    padding:25px 6px 5px!important;
  }
  body[data-v163-module="operation"] .v269-option4-card .v269-ribbon{height:22px!important;min-height:22px!important}
  body[data-v163-module="operation"] .v149-kpi.v269-option4-card > b,
  body[data-v163-module="operation"] .v204-kpi.v269-option4-card > b{font-size:18px!important}
}
</style>'''

    js = r'''<script id="v269-operation-option4-kpis-js">
(function(){
  if(window.__V269_OPERATION_OPTION4_KPIS_V2)return;
  window.__V269_OPERATION_OPTION4_KPIS_V2=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const imp=(el,p,v)=>el&&el.style.setProperty(p,v,'important');

  const ICONS={
    truck:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
    bars:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 19V11M12 19V5M19 19v-9"/></svg>',
    cube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/></svg>',
    clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>',
    percent:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M19 5 5 19"/></svg>',
    people:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="9" cy="8" r="3"/><path d="M3 19v-1a6 6 0 0 1 12 0v1"/><circle cx="17" cy="9" r="2.3"/></svg>',
    target:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/></svg>'
  };
  const colors={
    blue:'#168cff',purple:'#7c3aed',pink:'#e91e78',red:'#ef4444',
    green:'#10b981',orange:'#f59e0b',teal:'#0fa9a2',navy:'#1d568d'
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

  function forceGrid(grid,type){
    if(!grid)return;
    const mobile=window.innerWidth<=700;
    const tablet=window.innerWidth<=1100;
    const cols=mobile?2:(type==='summary'?(tablet?4:5):4);
    imp(grid,'display','grid');
    imp(grid,'grid-template-columns','repeat('+cols+',minmax(0,1fr))');
    imp(grid,'gap',mobile?'5px':'6px');
    imp(grid,'margin','6px 0 8px');
    imp(grid,'align-items','stretch');
  }

  function decorateCard(card,tone){
    if(!card)return;
    const color=colors[tone]||colors.blue;
    card.classList.add('v269-option4-card');
    card.dataset.v269Tone=tone;

    const label=q(':scope > small',card)?.textContent?.trim()||'Indicador';
    let ribbon=q(':scope > .v269-ribbon',card);
    if(!ribbon){
      ribbon=document.createElement('div');
      ribbon.className='v269-ribbon';
      card.insertBefore(ribbon,card.firstChild);
    }
    ribbon.innerHTML='<span class="v269-icon">'+iconFor(label)+'</span><span class="v269-title"></span>';
    q('.v269-title',ribbon).textContent=label;

    const mobile=window.innerWidth<=700;
    const h=mobile?'70px':'78px';

    imp(card,'position','relative');
    imp(card,'box-sizing','border-box');
    imp(card,'height',h);
    imp(card,'min-height',h);
    imp(card,'max-height',h);
    imp(card,'padding',mobile?'25px 6px 5px':'28px 8px 6px');
    imp(card,'margin','0');
    imp(card,'overflow','hidden');
    imp(card,'border','1px solid #d5e2ef');
    imp(card,'border-radius','10px');
    imp(card,'background','#fff');
    imp(card,'box-shadow','0 3px 9px rgba(18,63,115,.05)');

    imp(ribbon,'position','absolute');
    imp(ribbon,'z-index','50');
    imp(ribbon,'left','0');
    imp(ribbon,'right','0');
    imp(ribbon,'top','0');
    imp(ribbon,'width','100%');
    imp(ribbon,'height',mobile?'22px':'24px');
    imp(ribbon,'min-height',mobile?'22px':'24px');
    imp(ribbon,'display','flex');
    imp(ribbon,'align-items','center');
    imp(ribbon,'gap','5px');
    imp(ribbon,'padding','0 6px 0 30px');
    imp(ribbon,'box-sizing','border-box');
    imp(ribbon,'border-radius','9px 9px 0 0');
    imp(ribbon,'background',color);
    imp(ribbon,'background-color',color);
    imp(ribbon,'color','#fff');
    imp(ribbon,'opacity','1');
    imp(ribbon,'visibility','visible');
    imp(ribbon,'clip-path','none');

    const icon=q('.v269-icon',ribbon),title=q('.v269-title',ribbon);
    imp(icon,'position','absolute');imp(icon,'z-index','51');imp(icon,'left','5px');imp(icon,'top','3px');
    imp(icon,'transform','none');imp(icon,'display','grid');imp(icon,'place-items','center');
    imp(icon,'width','18px');imp(icon,'height','18px');imp(icon,'border','1.5px solid rgba(255,255,255,.92)');
    imp(icon,'border-radius','50%');imp(icon,'background','#fff');imp(icon,'color',color);imp(icon,'box-shadow','none');

    imp(title,'display','block');imp(title,'color','#fff');imp(title,'font-size','7px');imp(title,'font-weight','950');
    imp(title,'line-height','1');imp(title,'white-space','nowrap');imp(title,'overflow','hidden');imp(title,'text-overflow','ellipsis');

    const old=q(':scope > small',card),value=q(':scope > b',card);
    if(old)imp(old,'display','none');
    if(value){
      imp(value,'display','block');imp(value,'margin','2px 0 0');imp(value,'padding','0');
      imp(value,'font-size',mobile?'18px':'20px');imp(value,'line-height','1');imp(value,'font-weight','950');imp(value,'color','#103f76');
    }
    qa(':scope > span:not(.v269-ribbon)',card).forEach(detail=>{
      imp(detail,'display','block');imp(detail,'margin','3px 0 0');imp(detail,'padding','0');
      imp(detail,'font-size',mobile?'6.4px':'6.8px');imp(detail,'line-height','1');imp(detail,'color','#6b7f96');
      imp(detail,'white-space','nowrap');imp(detail,'overflow','hidden');imp(detail,'text-overflow','ellipsis');
    });
  }

  function enforce(){
    if(String(document.body.dataset.v163Module||'').toLowerCase()!=='operation')return;
    qa('.v149-kpis').forEach(grid=>{
      forceGrid(grid,'summary');
      qa(':scope > .v149-kpi',grid).forEach((card,i)=>decorateCard(card,summaryTones[i%summaryTones.length]));
    });
    qa('.v204-kpis').forEach(grid=>{
      forceGrid(grid,'productivity');
      qa(':scope > .v204-kpi',grid).forEach((card,i)=>decorateCard(card,prodTones[i%prodTones.length]));
    });
  }

  let raf=0;
  function schedule(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(enforce);
  }
  const mo=new MutationObserver(schedule);

  function start(){
    mo.observe(document.body,{subtree:true,childList:true});
    enforce();
    [80,200,450,900,1600].forEach(ms=>setTimeout(enforce,ms));
  }
  window.addEventListener('resize',schedule,{passive:true});
  document.addEventListener('click',()=>setTimeout(enforce,50),true);
  document.addEventListener('change',()=>setTimeout(enforce,50),true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
  console.info('[V269.1] Opción 4 ultra compacta aplicada con estilos inline.');
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
                "X-Operations-UI-Version":"V269.1-OPTION4-KPIS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V269] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V269_OPERATION_OPTION4_KPIS=True
    print("[V269.1] Opción 4 ultra compacta instalada en Resumen y Productividad.",flush=True)
