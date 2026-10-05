"""V275 · Operación UI final: pestañas y tarjetas compactas.

Alcance exclusivo al módulo Operación:
- 5 pestañas compactas en una sola fila.
- Resumen con KPIs Opción 4 restaurados, cinta superior e icono.
- En laptop ancha las 9 tarjetas caben en una sola fila; en anchos menores
  se adaptan 5/3/2 columnas sin dejar una tarjeta aislada innecesariamente.
- Corrige el subtítulo duplicado de Filtros del reporte.
- No modifica datos, cálculos, filtros, roles ni endpoints.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V275_OPERATION_UI_FINAL", False):
        return

    css = r'''<style id="v275-operation-ui-final-css">
/* =========================================================
   V275 · OPERACIÓN · pestañas compactas
   ========================================================= */
body.v238-module-operation #v200OperationTabs:not(.hidden),
body[data-v163-module="operation"] #v200OperationTabs:not(.hidden){
  display:grid!important;
  grid-template-columns:repeat(5,minmax(0,1fr))!important;
  grid-template-rows:50px!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  height:50px!important;
  min-height:50px!important;
  max-height:50px!important;
  gap:5px!important;
  margin:5px 0 8px!important;
  padding:0!important;
  overflow:hidden!important;
  border:0!important;
  background:transparent!important;
  box-shadow:none!important;
}
body.v238-module-operation #v200OperationTabs>button,
body[data-v163-module="operation"] #v200OperationTabs>button{
  display:flex!important;
  flex-direction:column!important;
  align-items:center!important;
  justify-content:center!important;
  gap:2px!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:50px!important;
  min-height:50px!important;
  max-height:50px!important;
  padding:3px 2px!important;
  margin:0!important;
  border:1px solid #d6e2ef!important;
  border-radius:10px!important;
  background:#fff!important;
  color:#365f86!important;
  box-shadow:0 2px 8px rgba(18,63,115,.045)!important;
  overflow:hidden!important;
  transform:none!important;
}
body.v238-module-operation #v200OperationTabs>button.active,
body.v238-module-operation #v200OperationTabs>button[aria-selected="true"],
body[data-v163-module="operation"] #v200OperationTabs>button.active,
body[data-v163-module="operation"] #v200OperationTabs>button[aria-selected="true"]{
  color:#fff!important;
  background:linear-gradient(145deg,#0d5597 0%,#087cdf 100%)!important;
  border-color:#0b64b6!important;
  box-shadow:0 5px 13px rgba(10,93,167,.16)!important;
}
body.v238-module-operation #v200OperationTabs :is(.v238-tab-icon,.v232-tab-icon,.v203-tab-icon),
body[data-v163-module="operation"] #v200OperationTabs :is(.v238-tab-icon,.v232-tab-icon,.v203-tab-icon){
  width:17px!important;
  min-width:17px!important;
  max-width:17px!important;
  height:17px!important;
  min-height:17px!important;
  max-height:17px!important;
  margin:0!important;
}
body.v238-module-operation #v200OperationTabs :is(.v238-tab-label,.v232-tab-label,.v203-tab-label),
body[data-v163-module="operation"] #v200OperationTabs :is(.v238-tab-label,.v232-tab-label,.v203-tab-label){
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  width:100%!important;
  min-width:0!important;
  height:18px!important;
  min-height:18px!important;
  max-height:18px!important;
  margin:0!important;
  padding:0!important;
  font-size:8.2px!important;
  line-height:1!important;
  font-weight:900!important;
  text-align:center!important;
  white-space:pre-line!important;
  overflow:hidden!important;
}

/* =========================================================
   V275 · RESUMEN · tarjetas KPI Opción 4 compactas
   ========================================================= */
body.v238-module-operation #operativoDynamicContent .v149-kpis,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpis{
  display:grid!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  gap:5px!important;
  margin:5px 0 7px!important;
  align-items:stretch!important;
}

body.v238-module-operation #operativoDynamicContent .v149-kpi,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi{
  position:relative!important;
  box-sizing:border-box!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:64px!important;
  min-height:64px!important;
  max-height:64px!important;
  margin:0!important;
  padding:23px 7px 5px!important;
  overflow:hidden!important;
  border:1px solid #d7e3ef!important;
  border-radius:9px!important;
  background:#fff!important;
  box-shadow:0 2px 7px rgba(18,63,115,.045)!important;
}
body.v238-module-operation #operativoDynamicContent .v149-kpi:before,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi:before{
  display:none!important;
}

body.v238-module-operation #operativoDynamicContent .v149-kpi .v275-ribbon,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi .v275-ribbon{
  position:absolute!important;
  z-index:20!important;
  left:0!important;
  right:0!important;
  top:0!important;
  display:flex!important;
  align-items:center!important;
  width:100%!important;
  height:20px!important;
  min-height:20px!important;
  padding:0 5px 0 25px!important;
  border-radius:8px 8px 0 0!important;
  background:var(--v275,#168cff)!important;
  color:#fff!important;
  overflow:hidden!important;
}
body.v238-module-operation #operativoDynamicContent .v149-kpi .v275-icon,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi .v275-icon{
  position:absolute!important;
  left:4px!important;
  top:2px!important;
  display:grid!important;
  place-items:center!important;
  width:16px!important;
  height:16px!important;
  min-width:16px!important;
  border-radius:50%!important;
  background:#fff!important;
  color:var(--v275,#168cff)!important;
  border:1px solid rgba(255,255,255,.95)!important;
}
body.v238-module-operation #operativoDynamicContent .v149-kpi .v275-icon svg,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi .v275-icon svg{
  width:9px!important;height:9px!important
}
body.v238-module-operation #operativoDynamicContent .v149-kpi .v275-title,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi .v275-title{
  display:block!important;
  width:100%!important;
  min-width:0!important;
  color:#fff!important;
  font-size:6.3px!important;
  line-height:1!important;
  font-weight:950!important;
  text-transform:uppercase!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body.v238-module-operation #operativoDynamicContent .v149-kpi>small,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi>small{
  display:none!important;
}
body.v238-module-operation #operativoDynamicContent .v149-kpi>b,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi>b{
  display:block!important;
  margin:1px 0 0!important;
  padding:0!important;
  color:#103f76!important;
  font-size:18px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:-.02em!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}
body.v238-module-operation #operativoDynamicContent .v149-kpi>span:not(.v275-ribbon):not(.v269-ribbon),
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi>span:not(.v275-ribbon):not(.v269-ribbon){
  display:block!important;
  margin:3px 0 0!important;
  padding:0!important;
  color:#6b7f96!important;
  font-size:6px!important;
  line-height:1!important;
  font-weight:650!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

/* Ocultar cinta anterior de V269 para que nunca se duplique. */
body.v238-module-operation #operativoDynamicContent .v149-kpi>.v269-ribbon,
body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi>.v269-ribbon{
  display:none!important;
}

/* Laptop ancho: las 9 tarjetas caben en una sola fila. */
@media(min-width:1360px){
  body.v238-module-operation #operativoDynamicContent .v149-kpis,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(var(--v275-kpi-count,9),minmax(0,1fr))!important;
  }
}
/* Laptop estándar: 5 + 4. */
@media(min-width:1025px) and (max-width:1359px){
  body.v238-module-operation #operativoDynamicContent .v149-kpis,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(5,minmax(0,1fr))!important;
  }
}
/* Tablet: 3 columnas. */
@media(min-width:701px) and (max-width:1024px){
  body.v238-module-operation #v200OperationTabs:not(.hidden),
  body[data-v163-module="operation"] #v200OperationTabs:not(.hidden){
    height:46px!important;min-height:46px!important;max-height:46px!important;
    grid-template-rows:46px!important;gap:3px!important;margin:4px 0 6px!important;
  }
  body.v238-module-operation #v200OperationTabs>button,
  body[data-v163-module="operation"] #v200OperationTabs>button{
    height:46px!important;min-height:46px!important;max-height:46px!important;
    padding:2px 1px!important;border-radius:8px!important;
  }
  body.v238-module-operation #v200OperationTabs :is(.v238-tab-icon,.v232-tab-icon,.v203-tab-icon),
  body[data-v163-module="operation"] #v200OperationTabs :is(.v238-tab-icon,.v232-tab-icon,.v203-tab-icon){
    width:14px!important;min-width:14px!important;height:14px!important;min-height:14px!important;
  }
  body.v238-module-operation #v200OperationTabs :is(.v238-tab-label,.v232-tab-label,.v203-tab-label),
  body[data-v163-module="operation"] #v200OperationTabs :is(.v238-tab-label,.v232-tab-label,.v203-tab-label){
    font-size:6.8px!important;height:17px!important;min-height:17px!important;
  }
  body.v238-module-operation #operativoDynamicContent .v149-kpis,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
  }
  body.v238-module-operation #operativoDynamicContent .v149-kpi,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi{
    height:62px!important;min-height:62px!important;max-height:62px!important;
  }
}
/* Móvil: 2 columnas, pero conservando el mismo diseño. */
@media(max-width:700px){
  body.v238-module-operation #v200OperationTabs:not(.hidden),
  body[data-v163-module="operation"] #v200OperationTabs:not(.hidden){
    height:44px!important;min-height:44px!important;max-height:44px!important;
    grid-template-rows:44px!important;gap:2px!important;margin:3px 0 5px!important;
  }
  body.v238-module-operation #v200OperationTabs>button,
  body[data-v163-module="operation"] #v200OperationTabs>button{
    height:44px!important;min-height:44px!important;max-height:44px!important;
    padding:2px 1px!important;border-radius:7px!important;
  }
  body.v238-module-operation #v200OperationTabs :is(.v238-tab-icon,.v232-tab-icon,.v203-tab-icon),
  body[data-v163-module="operation"] #v200OperationTabs :is(.v238-tab-icon,.v232-tab-icon,.v203-tab-icon){
    width:12px!important;min-width:12px!important;height:12px!important;min-height:12px!important;
  }
  body.v238-module-operation #v200OperationTabs :is(.v238-tab-label,.v232-tab-label,.v203-tab-label),
  body[data-v163-module="operation"] #v200OperationTabs :is(.v238-tab-label,.v232-tab-label,.v203-tab-label){
    font-size:5.7px!important;height:16px!important;min-height:16px!important;
  }
  body.v238-module-operation #operativoDynamicContent .v149-kpis,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:4px!important;
  }
  body.v238-module-operation #operativoDynamicContent .v149-kpi,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi{
    height:60px!important;min-height:60px!important;max-height:60px!important;
    padding:22px 6px 4px!important;
  }
  body.v238-module-operation #operativoDynamicContent .v149-kpi .v275-ribbon,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi .v275-ribbon{
    height:19px!important;min-height:19px!important;
  }
  body.v238-module-operation #operativoDynamicContent .v149-kpi>b,
  body[data-v163-module="operation"] #operativoDynamicContent .v149-kpi>b{
    font-size:16px!important;
  }
}

/* Filtro: una sola descripción, sin texto duplicado. */
body.v238-module-operation #operativoPeriodBar>.or-report-filter-brand small,
body[data-v163-module="operation"] #operativoPeriodBar>.or-report-filter-brand small{
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}
</style>'''

    js = r'''<script id="v275-operation-ui-final-js">
(function(){
  if(window.__V275_OPERATION_UI_FINAL)return;
  window.__V275_OPERATION_UI_FINAL=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const imp=(el,p,v)=>el&&el.style.setProperty(p,v,'important');

  const ICONS={
    truck:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
    bars:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 19V11M12 19V5M19 19v-9"/></svg>',
    cube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/></svg>',
    clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>',
    percent:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M19 5 5 19"/></svg>',
    people:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="8" r="3"/><path d="M3 19v-1a6 6 0 0 1 12 0v1"/><circle cx="17" cy="9" r="2.3"/></svg>',
    target:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/></svg>'
  };
  const tones=['#168cff','#7c3aed','#e91e78','#ef4444','#10b981','#f59e0b','#0fa9a2','#1d568d','#2563a7'];

  function isOperation(){
    if(document.body.classList.contains('v238-module-operation'))return true;
    if(String(document.body.dataset.v163Module||'').toLowerCase()==='operation')return true;
    try{return String(window.MAIN||MAIN||'').toLowerCase()==='operation'}catch(_){return false}
  }

  function iconFor(label){
    const t=String(label||'').toLowerCase();
    if(t.includes('llegada'))return ICONS.truck;
    if(t.includes('mercanc'))return ICONS.cube;
    if(t.includes('pendiente'))return ICONS.clock;
    if(t.includes('eficiencia')||t.includes('cumpl'))return ICONS.percent;
    if(t.includes('colaborador'))return ICONS.people;
    if(t.includes('prod'))return ICONS.bars;
    return ICONS.target;
  }

  function fixTabs(){
    const host=q('#v200OperationTabs');
    if(!host)return;
    const buttons=qa(':scope>button',host).filter(b=>!b.hidden&&!b.classList.contains('hidden'));
    if(!buttons.length)return;

    imp(host,'display','grid');
    imp(host,'grid-template-columns','repeat(5,minmax(0,1fr))');
    imp(host,'width','100%');
    imp(host,'max-width','100%');
    imp(host,'overflow','hidden');

    const labels={
      summary:'Resumen',
      daily:'Captura diaria',
      capture:'Cargar productividad',
      productivity:'Productividad',
      standards:'Estándares Operativos'
    };
    buttons.forEach(btn=>{
      const key=String(btn.dataset.v200Op||'').toLowerCase();
      btn.removeAttribute('title');
      const lab=q(':scope>.v238-tab-label,:scope>.v232-tab-label,:scope>.v203-tab-label',btn);
      if(lab&&labels[key])lab.textContent=labels[key];
    });
  }

  function decorateCard(card,index){
    if(!card)return;
    card.removeAttribute('title');
    const small=q(':scope>small',card);
    const label=(small?.textContent||q('.v269-title',card)?.textContent||'Indicador').trim();
    const tone=tones[index%tones.length];
    card.style.setProperty('--v275',tone);

    let ribbon=q(':scope>.v275-ribbon',card);
    if(!ribbon){
      ribbon=document.createElement('div');
      ribbon.className='v275-ribbon';
      card.insertBefore(ribbon,card.firstChild);
    }
    ribbon.innerHTML='<span class="v275-icon">'+iconFor(label)+'</span><span class="v275-title"></span>';
    q('.v275-title',ribbon).textContent=label;

    // La cinta V269 queda anulada para evitar iconos/títulos dobles.
    const old=q(':scope>.v269-ribbon',card);
    if(old)imp(old,'display','none');
  }

  function fixCards(){
    const grid=q('#operativoDynamicContent .v149-kpis');
    if(!grid)return;
    const cards=qa(':scope>.v149-kpi',grid);
    if(!cards.length)return;

    grid.style.setProperty('--v275-kpi-count',String(cards.length));
    let cols;
    if(window.innerWidth>=1360)cols=cards.length;
    else if(window.innerWidth>=1025)cols=Math.min(5,cards.length);
    else if(window.innerWidth>=701)cols=Math.min(3,cards.length);
    else cols=Math.min(2,cards.length);
    imp(grid,'grid-template-columns','repeat('+cols+',minmax(0,1fr))');
    cards.forEach(decorateCard);
  }

  function fixFilterBrand(){
    const small=q('#operativoPeriodBar>.or-report-filter-brand small');
    if(small&&small.textContent.trim()!=='Define la vista antes de consultar'){
      small.textContent='Define la vista antes de consultar';
    }
  }

  function sync(){
    if(!isOperation())return;
    fixTabs();
    fixCards();
    fixFilterBrand();
  }

  let timer=0;
  function queue(ms=20){clearTimeout(timer);timer=setTimeout(sync,ms)}
  const mo=new MutationObserver(()=>queue(25));

  function start(){
    mo.observe(document.body,{subtree:true,childList:true});
    sync();
    [60,140,280,520,900,1600,2600,4200].forEach(ms=>setTimeout(sync,ms));
  }

  document.addEventListener('click',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  document.addEventListener('change',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  window.addEventListener('resize',()=>queue(30),{passive:true});
  window.addEventListener('pageshow',()=>[50,180,500].forEach(ms=>setTimeout(sync,ms)),{passive:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V275] Operación: pestañas y tarjetas compactas restauradas.');
})();
</script>'''

    @m.app.middleware("http")
    async def v275_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v275-operation-ui-final-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v275-operation-ui-final-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V275-OPERATION-UI-FINAL",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V275] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V275_OPERATION_UI_FINAL=True
    print("[V275] Operación: pestañas y tarjetas compactas finales instaladas.",flush=True)
