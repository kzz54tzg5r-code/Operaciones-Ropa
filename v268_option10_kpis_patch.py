"""V268 · KPI cards Opción 10 en Conversión, Recuperación $ y Score.

Capa visual exclusivamente:
- aplica Opción 10 sólo a operations.conversion, operations.recovery y operations.score;
- conserva valores, cálculos, tablas, filtros y donut de Score;
- responsive desktop/tablet/móvil.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V268_OPTION10_KPIS", False):
        return

    css = r'''<style id="v268-option10-kpis-css">
/* =========================================================
   V268 · OPCIÓN 10 · KPI CARDS
   Sólo Conversión / Recuperación $ / Score
   ========================================================= */

#operativoDynamicContent .report-kpis.v268-option10-grid{
  display:grid!important;
  grid-template-columns:repeat(4,minmax(0,1fr))!important;
  gap:14px!important;
  width:100%!important;
  margin:8px 0 12px!important;
  align-items:stretch!important;
}

/* En Score el grid vive a la derecha del donut. */
#operativoDynamicContent .donut-row .report-kpis.v268-option10-grid{
  margin:0!important;
  gap:12px!important;
}

#operativoDynamicContent .report-kpi.v268-option10-card{
  --v268:#1769e8;
  --v268-soft:#eaf4ff;
  position:relative!important;
  isolation:isolate!important;
  min-width:0!important;
  min-height:156px!important;
  padding:58px 16px 14px!important;
  overflow:hidden!important;
  border:1px solid color-mix(in srgb,var(--v268) 24%,#d9e4ef)!important;
  border-radius:16px!important;
  background:
    radial-gradient(circle at 93% 93%,color-mix(in srgb,var(--v268) 13%,transparent) 0 16%,transparent 17%),
    linear-gradient(155deg,#fff 0%,#fff 58%,var(--v268-soft) 140%)!important;
  box-shadow:0 8px 22px rgba(23,59,115,.09)!important;
  transition:transform .16s ease,box-shadow .16s ease!important;
}
#operativoDynamicContent .report-kpi.v268-option10-card:hover{
  transform:translateY(-1px)!important;
  box-shadow:0 10px 26px rgba(23,59,115,.12)!important;
}

/* Ribbon superior tipo opción 10. */
#operativoDynamicContent .report-kpi.v268-option10-card .v268-ribbon{
  position:absolute!important;
  z-index:2!important;
  left:12px!important;
  top:12px!important;
  width:calc(100% - 42px)!important;
  height:44px!important;
  display:flex!important;
  align-items:center!important;
  gap:9px!important;
  padding:0 38px 0 48px!important;
  color:#fff!important;
  background:linear-gradient(100deg,color-mix(in srgb,var(--v268) 82%,#003c82),var(--v268))!important;
  border-radius:12px 4px 4px 12px!important;
  box-shadow:0 5px 12px color-mix(in srgb,var(--v268) 22%,transparent)!important;
  clip-path:polygon(0 0,100% 0,92% 100%,0 100%)!important;
}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-ribbon-title{
  min-width:0!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  white-space:nowrap!important;
  color:#fff!important;
  font-size:clamp(10px,.74vw,13px)!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:.015em!important;
  text-transform:uppercase!important;
}

/* Icono circular sobre la banda. */
#operativoDynamicContent .report-kpi.v268-option10-card .v268-icon{
  position:absolute!important;
  z-index:4!important;
  left:4px!important;
  top:50%!important;
  transform:translateY(-50%)!important;
  display:grid!important;
  place-items:center!important;
  width:38px!important;
  height:38px!important;
  border:3px solid rgba(255,255,255,.82)!important;
  border-radius:50%!important;
  color:var(--v268)!important;
  background:#fff!important;
  box-shadow:0 3px 8px rgba(0,0,0,.12)!important;
}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-icon svg{
  width:21px!important;
  height:21px!important;
  display:block!important;
}

/* Ocultamos la etiqueta original porque ya está en el ribbon. */
#operativoDynamicContent .report-kpi.v268-option10-card > .rk-label{
  position:absolute!important;
  width:1px!important;
  height:1px!important;
  padding:0!important;
  margin:-1px!important;
  overflow:hidden!important;
  clip:rect(0,0,0,0)!important;
  white-space:nowrap!important;
  border:0!important;
}

#operativoDynamicContent .report-kpi.v268-option10-card > .rk-value{
  position:relative!important;
  z-index:2!important;
  margin:13px 0 4px!important;
  color:#0c4a8f!important;
  font-size:clamp(26px,2.15vw,38px)!important;
  line-height:.98!important;
  font-weight:950!important;
  letter-spacing:-.035em!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}
#operativoDynamicContent .report-kpi.v268-option10-card > .rk-sub{
  position:relative!important;
  z-index:2!important;
  max-width:78%!important;
  margin-top:8px!important;
  color:#607791!important;
  font-size:clamp(10px,.68vw,13px)!important;
  line-height:1.16!important;
  font-weight:650!important;
}

/* Mini visual decorativo inferior derecho. */
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini{
  position:absolute!important;
  z-index:1!important;
  right:12px!important;
  bottom:14px!important;
  display:flex!important;
  align-items:flex-end!important;
  gap:4px!important;
  width:62px!important;
  height:46px!important;
  opacity:.28!important;
}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini i{
  display:block!important;
  flex:1!important;
  min-width:5px!important;
  border-radius:4px 4px 1px 1px!important;
  background:var(--v268)!important;
}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini i:nth-child(1){height:28%}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini i:nth-child(2){height:48%}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini i:nth-child(3){height:66%}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini i:nth-child(4){height:84%}
#operativoDynamicContent .report-kpi.v268-option10-card .v268-mini i:nth-child(5){height:56%}

/* Tonos por posición para reproducir la Opción 10. */
#operativoDynamicContent .report-kpi.v268-option10-card[data-v268-tone="blue"]{
  --v268:#168cff;--v268-soft:#eaf5ff;
}
#operativoDynamicContent .report-kpi.v268-option10-card[data-v268-tone="green"]{
  --v268:#11b875;--v268-soft:#e8fbf3;
}
#operativoDynamicContent .report-kpi.v268-option10-card[data-v268-tone="purple"]{
  --v268:#8247f5;--v268-soft:#f2ebff;
}
#operativoDynamicContent .report-kpi.v268-option10-card[data-v268-tone="red"]{
  --v268:#ef476f;--v268-soft:#fff0f4;
}

/* Score: compactar el donut + tarjetas sin deformar. */
#operativoDynamicContent.v268-score-active .donut-row{
  display:grid!important;
  grid-template-columns:145px minmax(0,1fr)!important;
  gap:16px!important;
  align-items:center!important;
}
#operativoDynamicContent.v268-score-active .donut-row > div[style*="flex:1"]{
  min-width:0!important;
  width:100%!important;
}
#operativoDynamicContent.v268-score-active .donut{
  width:140px!important;
  height:140px!important;
  margin:0 auto!important;
}

/* Tablet */
@media(max-width:1199px) and (min-width:701px){
  #operativoDynamicContent .report-kpis.v268-option10-grid{
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:10px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card{
    min-height:140px!important;
    padding:53px 14px 12px!important;
  }
  #operativoDynamicContent.v268-score-active .donut-row{
    grid-template-columns:120px minmax(0,1fr)!important;
  }
  #operativoDynamicContent.v268-score-active .donut{
    width:112px!important;
    height:112px!important;
  }
}

/* Móvil */
@media(max-width:700px){
  #operativoDynamicContent .report-kpis.v268-option10-grid{
    grid-template-columns:1fr!important;
    gap:8px!important;
    margin:6px 0 9px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card{
    min-height:118px!important;
    padding:48px 12px 10px!important;
    border-radius:13px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card .v268-ribbon{
    left:8px!important;
    top:8px!important;
    height:38px!important;
    width:calc(100% - 28px)!important;
    padding-left:43px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card .v268-icon{
    width:32px!important;
    height:32px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card .v268-icon svg{
    width:18px!important;height:18px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card > .rk-value{
    margin-top:8px!important;
    font-size:clamp(24px,8vw,32px)!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card > .rk-sub{
    max-width:76%!important;
    margin-top:4px!important;
    font-size:10px!important;
  }
  #operativoDynamicContent .report-kpi.v268-option10-card .v268-mini{
    width:50px!important;
    height:34px!important;
    right:9px!important;
    bottom:9px!important;
  }
  #operativoDynamicContent.v268-score-active .donut-row{
    display:block!important;
  }
  #operativoDynamicContent.v268-score-active .donut{
    width:105px!important;
    height:105px!important;
    margin:0 auto 10px!important;
  }
}
</style>'''

    js = r'''<script id="v268-option10-kpis-js">
(function(){
  if(window.__V268_OPTION10_KPIS)return;
  window.__V268_OPTION10_KPIS=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const allowed=new Set(['Conversión','Recuperación Económica','Índice Integral']);
  const tones=['blue','green','purple','red'];

  const ICONS={
    bars:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 19V11M12 19V5M19 19v-9"/></svg>',
    cube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="m4 7 8 4 8-4v10l-8 4-8-4V7Z"/><path d="M12 11v10"/></svg>',
    percent:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M19 5 5 19"/></svg>',
    money:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v20M17 6.5c-1.2-1-2.8-1.5-5-1.5-3 0-5 1.4-5 3.5S9 12 12 12s5 1.4 5 3.5S15 19 12 19c-2.1 0-3.8-.5-5-1.5"/></svg>',
    clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>',
    gauge:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 18a8 8 0 1 1 16 0"/><path d="m12 14 4-4"/><path d="M8 18h8"/></svg>'
  };

  function activeView(){
    const b=q('#operativoNav>button.active[data-opview]')||
            q('#operativoNav>button[aria-selected="true"][data-opview]');
    return String(b?.dataset?.opview||'');
  }

  function iconFor(label){
    const t=String(label||'').toLowerCase();
    if(t.includes('pieza'))return ICONS.cube;
    if(t.includes('%'))return ICONS.percent;
    if(t.includes('recuperación $')||t.includes('valor devolución'))return ICONS.money;
    if(t.includes('pendiente'))return ICONS.clock;
    if(t.includes('score'))return ICONS.gauge;
    return ICONS.bars;
  }

  function reset(){
    const root=q('#operativoDynamicContent');
    if(!root)return;
    root.classList.remove('v268-score-active');
    qa('.report-kpis.v268-option10-grid',root).forEach(g=>g.classList.remove('v268-option10-grid'));
    qa('.report-kpi.v268-option10-card',root).forEach(card=>{
      card.classList.remove('v268-option10-card');
      card.removeAttribute('data-v268-tone');
      q('.v268-ribbon',card)?.remove();
      q('.v268-mini',card)?.remove();
    });
  }

  function decorate(){
    const root=q('#operativoDynamicContent');
    if(!root)return;
    const view=activeView();
    if(!allowed.has(view)){
      reset();
      return;
    }

    root.classList.toggle('v268-score-active',view==='Índice Integral');

    const grids=qa('.report-kpis',root);
    grids.forEach(grid=>{
      const cards=qa(':scope > .report-kpi',grid);
      if(!cards.length)return;
      grid.classList.add('v268-option10-grid');
      cards.forEach((card,i)=>{
        card.classList.add('v268-option10-card');
        card.dataset.v268Tone=tones[i%tones.length];

        const label=q(':scope > .rk-label',card)?.textContent?.trim()||'Indicador';
        let ribbon=q(':scope > .v268-ribbon',card);
        if(!ribbon){
          ribbon=document.createElement('div');
          ribbon.className='v268-ribbon';
          card.insertBefore(ribbon,card.firstChild);
        }
        ribbon.innerHTML='<span class="v268-icon">'+iconFor(label)+'</span><span class="v268-ribbon-title"></span>';
        q('.v268-ribbon-title',ribbon).textContent=label;

        if(!q(':scope > .v268-mini',card)){
          const mini=document.createElement('span');
          mini.className='v268-mini';
          mini.setAttribute('aria-hidden','true');
          mini.innerHTML='<i></i><i></i><i></i><i></i><i></i>';
          card.appendChild(mini);
        }
      });
    });
  }

  let timer=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(timer);
    timer=setTimeout(decorate,24);
  });

  function start(){
    const root=q('#operativoDynamicContent');
    const nav=q('#operativoNav');
    if(root)observer.observe(root,{subtree:true,childList:true});
    if(nav)observer.observe(nav,{subtree:true,attributes:true,attributeFilter:['class','aria-selected']});
    decorate();
    [80,220,500,1000].forEach(ms=>setTimeout(decorate,ms));
  }

  document.addEventListener('click',e=>{
    if(e.target.closest?.('#operativoNav>button[data-opview]')){
      [0,50,150,400].forEach(ms=>setTimeout(decorate,ms));
    }
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V268] KPI Opción 10 activa en Conversión, Recuperación $ y Score.');
})();
</script>'''

    @m.app.middleware("http")
    async def v268_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v268-option10-kpis-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v268-option10-kpis-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V268-OPTION10-KPIS",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V268] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V268_OPTION10_KPIS=True
    print("[V268] Opción 10 aplicada a Conversión, Recuperación $ y Score.",flush=True)
