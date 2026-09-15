"""V158.1 · Barra de filtros visible y layout alineado a boceto.

Usa los selectores reales de cada módulo como fuente de verdad, sin modificar
tablas, gráficas, cálculos ni exportaciones. No usa MutationObserver ni
intervalos; sólo reacciona a navegación y acciones directas del usuario.
"""
from __future__ import annotations
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V158_BOCETO_EXACT_FILTERS", False):
        return

    css = r'''<style id="v158-boceto-css">
:root{--v158-blue:#1769e8;--v158-navy:#0e3f7a;--v158-bg:#f5f8fc;--v158-line:#d7e3f0;--v158-muted:#6d7f93}
body{background:var(--v158-bg)!important}
.main{padding:10px 14px 78px!important;background:var(--v158-bg)!important}
.hero{min-height:96px!important;padding:17px 22px!important;border-radius:18px!important;background:linear-gradient(125deg,#0d3f7d,#0d5aa5)!important;box-shadow:none!important}
.hero h1{font-size:24px!important;line-height:1.05!important}.hero p{font-size:9px!important}

#v158FilterBar{display:none;background:#fff;border:1px solid var(--v158-line);border-radius:14px;padding:9px 10px;margin:8px 0 7px;box-shadow:0 2px 8px rgba(19,64,117,.04)}
#v158FilterBar.on{display:block}
.v158-grid{display:grid;grid-template-columns:.8fr 1.25fr 1fr 1fr 1fr auto;gap:7px;align-items:end}
.v158-field{min-width:0}.v158-field label{display:block;font-size:7px;font-weight:950;text-transform:uppercase;letter-spacing:.02em;color:#5e7690;margin:0 0 4px 2px}
.v158-field select,.v158-field input{width:100%;height:34px;border:1px solid #cfdeed;border-radius:8px;background:#fff;color:#123b73;padding:5px 27px 5px 8px;font-size:8.5px;font-weight:750}
.v158-actions{display:flex;gap:6px;align-items:end}.v158-apply{height:34px;border:0;border-radius:8px;padding:0 16px;background:var(--v158-blue);color:#fff;font-size:8px;font-weight:950;cursor:pointer;white-space:nowrap}.v158-more{height:34px;border:1px solid #a9c8ee;border-radius:8px;padding:0 12px;background:#fff;color:var(--v158-blue);font-size:8px;font-weight:950;cursor:pointer;white-space:nowrap}
.v158-quick{display:flex;gap:4px;justify-content:flex-end;margin-top:6px}.v158-chip{border:1px solid #d4e2f1;background:#f7faff;color:#496b8f;border-radius:7px;padding:4px 7px;font-size:7px;font-weight:900;cursor:pointer}.v158-chip.active{background:#1769e8;color:#fff;border-color:#1769e8}
#v158MorePanel{display:none;border-top:1px solid #edf2f7;margin-top:8px;padding-top:8px}.v158-more-open #v158MorePanel{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:7px}

/* Un solo sistema visible de filtros. */
body.v158-ready .filters,body.v158-ready #globalFilters,body.v158-ready #v103FilterShell,body.v158-ready #v102FilterMode,body.v158-ready #v102Drill{display:none!important}

/* Pestañas: mismo orden y comportamiento, sólo diseño. */
body[data-v158-module="cambios"] #operativoNav,body[data-v158-module="analysis"] #analysisNav,body[data-v158-module="operation"] .v125-tabs{display:flex!important;background:#fff!important;border:1px solid var(--v158-line)!important;border-radius:12px!important;padding:4px!important;margin:6px 0 8px!important;gap:4px!important;overflow-x:auto!important;flex-wrap:nowrap!important}
#operativoNav .switch,#analysisNav .switch,.v125-tab{border-radius:8px!important;padding:7px 11px!important;font-size:7.5px!important;white-space:nowrap!important;border:1px solid transparent!important;color:#254f7e!important;background:#fff!important}
#operativoNav .switch.active,#analysisNav .switch.active,.v125-tab.active{background:var(--v158-blue)!important;color:#fff!important;box-shadow:none!important}

/* Tarjetas compactas como boceto. */
.report-kpis,.kpis{gap:7px!important;margin:7px 0 9px!important}
.report-kpi,.kpi{min-height:82px!important;border-radius:11px!important;padding:9px 10px!important;box-shadow:0 2px 7px rgba(22,65,116,.04)!important}
.report-kpi .rk-value,.val{font-size:20px!important;margin:5px 0 2px!important}.report-kpi .rk-label,.lab{font-size:7px!important}.report-kpi .rk-sub,.note{font-size:7px!important}
.title{font-size:15px!important;margin:9px 0 6px!important}.subtitle{font-size:8px!important;margin:-3px 0 7px!important}
.panel,.card,.chart-box,.drop,.useritem{border-radius:12px!important;box-shadow:0 2px 8px rgba(22,65,116,.035)!important}
/* Deliberadamente no se estilizan table, canvas, svg ni botones de descarga. */

@media(max-width:1100px){.v158-grid{grid-template-columns:1fr 1fr 1fr}.v158-actions{grid-column:auto}.v158-actions button{flex:1}}
@media(max-width:900px){
  .main{padding:7px 7px 72px!important}.hero{min-height:78px!important;padding:13px 13px!important}.hero h1{font-size:19px!important}
  .v158-grid{grid-template-columns:1fr 1fr}.v158-actions{grid-column:1/-1}.v158-apply,.v158-more{flex:1}.v158-more-open #v158MorePanel{grid-template-columns:1fr 1fr}
  .v158-quick{justify-content:flex-start;overflow-x:auto}
}
</style>'''

    js = r'''<script id="v158-boceto-js">
(function(){
  if(window.__V158_BOCETO)return;window.__V158_BOCETO=true;
  const $=id=>document.getElementById(id);
  const defs={
    cambios:[['Vista','operPeriodMode'],['Periodo','operPeriodSelect'],['Tienda','operStoreSelect'],['Área','operAreaSelect'],['Actividad','operActivitySelect']],
    operation:[['Vista','operPeriodMode'],['Periodo','operPeriodSelect'],['Tienda','operStoreSelect'],['Origen','operAreaSelect'],['Colaborador','operActivitySelect']],
    analysis:[['Periodo','week'],['Tienda','store'],['Sección','section'],['Catálogo','catalog']]
  };
  function module(){
    const a=document.querySelector('.nav.active');const t=((a&&a.textContent)||'').toLowerCase();let m='';try{m=String(window.MAIN||'').toLowerCase()}catch(_){ }
    if(t.includes('análisis comercial')||m==='analysis'||m==='commercial')return'analysis';
    if(t.trim().startsWith('operación')||m==='operation')return'operation';
    if(t.includes('cambios y muertos')||m==='operativo')return'cambios';
    if(t.includes('usuarios')||m==='users')return'users';if(t.includes('compartir')||m==='share')return'share';return'cambios';
  }
  function ensureHost(){
    let h=$('v158FilterBar');if(h)return h;
    h=document.createElement('div');h.id='v158FilterBar';
    h.innerHTML='<div class="v158-grid" id="v158Grid"></div><div class="v158-quick" id="v158Quick"><button type="button" class="v158-chip" data-mode="day">Día</button><button type="button" class="v158-chip" data-mode="week">Semana</button><button type="button" class="v158-chip" data-mode="month">Mes</button><button type="button" class="v158-chip" data-mode="year">Año</button></div><div id="v158MorePanel"></div>';
    const hero=document.querySelector('.hero');if(hero&&hero.parentNode)hero.insertAdjacentElement('afterend',h);else(document.querySelector('.main')||document.body).prepend(h);return h;
  }
  function cloneSelect(label,id){
    const s=$(id);if(!s)return null;const w=document.createElement('div');w.className='v158-field';const l=document.createElement('label');l.textContent=label;const c=s.cloneNode(true);c.removeAttribute('id');c.dataset.source=id;c.value=s.value;
    c.addEventListener('change',()=>{const src=$(id);if(src){src.value=c.value;src.dispatchEvent(new Event('change',{bubbles:true}))}});w.append(l,c);return w;
  }
  function wireQuick(mod){
    const q=$('v158Quick'),mode=$('operPeriodMode');if(!q)return;
    if((mod!=='cambios'&&mod!=='operation')||!mode){q.style.display='none';return}q.style.display='flex';
    q.querySelectorAll('[data-mode]').forEach(b=>{b.classList.toggle('active',b.dataset.mode===mode.value);b.onclick=()=>{mode.value=b.dataset.mode;mode.dispatchEvent(new Event('change',{bubbles:true}));setTimeout(apply,180)}});
  }
  function apply(){
    const mod=module();document.body.dataset.v158Module=mod;document.body.classList.add('v158-ready');const h=ensureHost(),grid=$('v158Grid'),more=$('v158MorePanel');grid.innerHTML='';more.innerHTML='';
    if(!defs[mod]){h.classList.remove('on');return}h.classList.add('on');let count=0;
    defs[mod].forEach((d,i)=>{const el=cloneSelect(d[0],d[1]);if(!el)return;count++;if(i<5)grid.appendChild(el);else more.appendChild(el)});
    const acts=document.createElement('div');acts.className='v158-actions';
    const go=document.createElement('button');go.type='button';go.className='v158-apply';go.textContent='⌕  Consultar';go.onclick=()=>{const id=mod==='analysis'?'refresh':'operPeriodApply';const b=$(id);if(b)b.click();else defs[mod].forEach(d=>$(d[1])?.dispatchEvent(new Event('change',{bubbles:true})));setTimeout(apply,180)};
    const mb=document.createElement('button');mb.type='button';mb.className='v158-more';mb.textContent='☷  Más filtros';mb.onclick=()=>h.classList.toggle('v158-more-open');acts.append(go,mb);grid.appendChild(acts);wireQuick(mod);if(!count)h.classList.remove('on');
  }
  function schedule(){[40,220,700].forEach(ms=>setTimeout(apply,ms))}
  document.addEventListener('click',e=>{if(e.target.closest('[data-main],[data-sub],[data-opview],#refresh,#operPeriodApply'))schedule()},true);
  document.addEventListener('change',e=>{if(e.target&&e.target.matches('select,input'))setTimeout(apply,90)},true);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();
  console.info('[V158.1] Boceto visual + filtro único visible activo.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v158_html(request, call_next):
        response=await call_next(request)
        if request.url.path!='/' or getattr(response,'status_code',200)!=200:return response
        try:
            body=b''
            async for chunk in response.body_iterator: body+=chunk
            html=body.decode('utf-8',errors='replace')
            if 'v158-boceto-css' not in html: html=html.replace('</head>',css+'</head>',1)
            if 'v158-boceto-js' not in html: html=html.replace('</body>',js+'</body>',1)
            headers=dict(getattr(response,'headers',{}) or {});headers.pop('content-length',None)
            headers.update({'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V158.1-BOCETO-FILTERS'})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f'[V158.1] HTML warning: {type(exc).__name__}: {exc}',flush=True);return response
    m._V158_BOCETO_EXACT_FILTERS=True
    print('[V158.1] Filtros visibles Día/Semana/Mes/Año + selectores reales; tablas/gráficas/PDF/Excel intactos.',flush=True)
