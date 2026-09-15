"""V161 · Un solo filtro por reporte + tarjetas alineadas a boceto.

Objetivo visual solicitado:
- Un solo bloque de filtros visible en Cambios y Muertos, Operación y Comercial.
- Eliminar filtros redundantes según la pestaña activa.
- Replicar el mismo lenguaje visual de filtros en todos los reportes.
- Ajustar únicamente tarjetas, encabezados y pestañas.
- NO modificar tablas, gráficas, cálculos, PDF ni Excel.

Los selectores nativos permanecen como fuente de verdad; V161 sólo crea una
fachada compacta sincronizada con ellos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V161_UNIFIED_BOCETO", False):
        return

    css = r'''<style id="v161-unified-boceto-css">
:root{
  --v161-blue:#176fe8;
  --v161-navy:#103f7d;
  --v161-bg:#f4f7fb;
  --v161-line:#d5e1ee;
  --v161-muted:#687b93;
}

/* V161 reemplaza visualmente todos los sistemas anteriores de filtros. */
#v158FilterBar,
#v103FilterShell,
#v102FilterMode,
#v102Drill,
#v103ClassicBack,
#globalFilters,
.filters,
#operativoPeriodBar{
  display:none!important;
}

#v161FilterBar{
  display:none;
  background:#fff;
  border:1px solid var(--v161-line);
  border-radius:15px;
  padding:10px;
  margin:9px 0 8px;
  box-shadow:0 3px 12px rgba(24,64,112,.045);
}
#v161FilterBar.on{display:block}
.v161-filter-grid{
  display:grid;
  grid-template-columns:repeat(5,minmax(120px,1fr)) auto;
  gap:8px;
  align-items:end;
}
.v161-field{min-width:0}
.v161-field label{
  display:block;
  margin:0 0 5px 2px;
  color:#60758f;
  font-size:8px;
  line-height:1;
  font-weight:950;
  text-transform:uppercase;
  letter-spacing:.03em;
}
.v161-field select,.v161-field input{
  width:100%;height:40px;min-width:0;
  border:1px solid #cad9e9;
  border-radius:10px;
  background:#fff;
  color:#173f78;
  padding:7px 30px 7px 10px;
  font-size:10px;
  font-weight:800;
  outline:none;
  box-shadow:none;
}
.v161-apply{
  height:40px;min-width:128px;
  border:0;border-radius:10px;
  background:linear-gradient(90deg,#1b68df,#1778f3);
  color:#fff;font-size:9px;font-weight:950;
  padding:0 18px;cursor:pointer;white-space:nowrap;
}

/* Encabezados y pestañas: misma composición de los bocetos. */
.main{background:var(--v161-bg)!important}
.hero{
  min-height:94px!important;
  padding:16px 20px!important;
  border-radius:17px!important;
  background:linear-gradient(118deg,#0d3f7d 0%,#0e579f 70%,#0b437f 100%)!important;
  box-shadow:none!important;
}
.hero h1{font-size:24px!important;line-height:1.05!important;letter-spacing:-.02em!important}
.hero p{font-size:9px!important;margin-top:5px!important;color:#dceaf9!important}

#operativoNav,#analysisNav,.v125-tabs{
  display:flex!important;
  flex-wrap:nowrap!important;
  overflow-x:auto!important;
  gap:4px!important;
  background:#fff!important;
  border:1px solid var(--v161-line)!important;
  border-radius:13px!important;
  padding:4px!important;
  margin:7px 0 9px!important;
  box-shadow:none!important;
  scrollbar-width:none;
}
#operativoNav::-webkit-scrollbar,#analysisNav::-webkit-scrollbar,.v125-tabs::-webkit-scrollbar{display:none}
#operativoNav .switch,#analysisNav .switch,.v125-tab{
  flex:0 0 auto!important;
  border:1px solid transparent!important;
  border-radius:9px!important;
  background:#fff!important;
  color:#284f7d!important;
  padding:8px 12px!important;
  min-height:34px!important;
  font-size:8px!important;
  font-weight:900!important;
  white-space:nowrap!important;
}
#operativoNav .switch.active,#analysisNav .switch.active,.v125-tab.active{
  background:var(--v161-blue)!important;
  color:#fff!important;
  box-shadow:none!important;
}

/* TARJETAS: sí se ajustan. Tablas y gráficas quedan intactas. */
.kpis,.report-kpis,.v149-kpis,.v125-kpis{
  display:grid!important;
  grid-template-columns:repeat(4,minmax(0,1fr))!important;
  gap:8px!important;
  margin:8px 0 10px!important;
}
.kpi,.report-kpi,.v149-kpi,.v125-kpi{
  min-width:0!important;
  min-height:92px!important;
  padding:11px 12px!important;
  border:1px solid var(--v161-line)!important;
  border-radius:13px!important;
  background:#fff!important;
  box-shadow:0 2px 8px rgba(20,64,114,.035)!important;
}
.lab,.report-kpi .rk-label,.v149-kpi small,.v125-kpi small{
  color:#667a92!important;
  font-size:7.5px!important;
  line-height:1.2!important;
  font-weight:900!important;
}
.val,.report-kpi .rk-value,.v149-kpi b,.v125-kpi b{
  color:var(--v161-navy)!important;
  font-size:25px!important;
  line-height:1.05!important;
  letter-spacing:-.025em!important;
}
.note,.report-kpi .rk-sub,.v149-kpi span,.v125-kpi span{
  color:#75859a!important;
  font-size:8px!important;
  line-height:1.25!important;
}
.title{font-size:18px!important;color:var(--v161-navy)!important;margin:10px 0 5px!important}
.subtitle{font-size:9px!important;color:#71839a!important;margin-bottom:7px!important}

/* No hay reglas para table, canvas, svg ni contenedores de gráfica. */

@media(max-width:1120px){
  .v161-filter-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .v161-apply{width:100%}
}
@media(max-width:900px){
  .main{padding:8px 7px 76px!important}
  .hero{min-height:88px!important;padding:14px 14px!important;border-radius:15px!important}
  .hero h1{font-size:21px!important}.hero p{font-size:9px!important}
  #v161FilterBar{padding:9px;border-radius:13px;margin:8px 0 7px}
  .v161-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
  .v161-field select,.v161-field input{height:43px;font-size:12px}
  .v161-apply{grid-column:1/-1;height:44px;font-size:11px}
  .kpis,.report-kpis,.v149-kpis,.v125-kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
  .kpi,.report-kpi,.v149-kpi,.v125-kpi{min-height:105px!important;padding:11px!important}
  .val,.report-kpi .rk-value,.v149-kpi b,.v125-kpi b{font-size:27px!important}
  #operativoNav .switch,#analysisNav .switch,.v125-tab{padding:9px 12px!important;font-size:9px!important}
}
@media(max-width:520px){
  .v161-filter-grid{grid-template-columns:1fr 1fr}
}
</style>'''

    js = r'''<script id="v161-unified-boceto-js">
(function(){
  if(window.__V161_UNIFIED_BOCETO)return;
  window.__V161_UNIFIED_BOCETO=true;

  const gid=id=>document.getElementById(id);
  const qs=s=>document.querySelector(s);

  function moduleName(){
    let main='';try{main=String(window.MAIN||'').toLowerCase()}catch(_){ }
    const a=qs('.nav.active');const txt=((a&&a.textContent)||'').toLowerCase();
    if(main==='analysis'||main==='commercial'||txt.includes('análisis comercial'))return'analysis';
    if(main==='operation'||txt.trim().startsWith('operación'))return'operation';
    if(main==='operativo'||txt.includes('cambios y muertos'))return'cambios';
    return'';
  }

  function activeTab(mod){
    if(mod==='cambios')return (qs('#operativoNav .active')?.textContent||'Centro Operativo').trim().toLowerCase();
    if(mod==='operation')return (qs('.v125-tabs .active')?.textContent||'Resumen').trim().toLowerCase();
    if(mod==='analysis')return (qs('#analysisNav .active')?.textContent||'Macro compañía').trim().toLowerCase();
    return'';
  }

  function ensureMode(){
    const s=gid('operPeriodMode');if(!s||s.value)return;
    let wanted='day';try{wanted=String(window.OPER_PERIOD?.type||'day')}catch(_){ }
    if([...s.options].some(o=>o.value===wanted))s.value=wanted;
    else if(s.options.length)s.selectedIndex=0;
  }

  function spec(mod,tab){
    if(mod==='cambios'){
      const base=[['Vista','operPeriodMode'],['Periodo','operPeriodSelect'],['Tienda','operStoreSelect']];
      if(tab.includes('centro operativo')||tab.includes('productividad'))return [...base,['Área','operAreaSelect'],['Actividad','operActivitySelect']];
      return base;
    }
    if(mod==='operation'){
      if(tab.includes('estándar'))return[];
      if(tab.includes('productividad')&&!tab.includes('cargar'))return [['Vista','operPeriodMode'],['Periodo','operPeriodSelect'],['Tienda','operStoreSelect'],['Origen','operAreaSelect'],['Colaborador','operActivitySelect']];
      if(tab.includes('captura diaria')||tab.includes('cargar productividad'))return [['Fecha','operPeriodSelect'],['Tienda','operStoreSelect']];
      return [['Vista','operPeriodMode'],['Periodo','operPeriodSelect'],['Tienda','operStoreSelect']];
    }
    if(mod==='analysis'){
      if(tab.includes('carga de datos'))return[];
      if(tab==='tiendas'||tab.includes('tiendas'))return [['Periodo','week'],['Sección','section'],['Catálogo','catalog']];
      return [['Periodo','week'],['Tienda','store'],['Sección','section'],['Catálogo','catalog']];
    }
    return[];
  }

  function ensureHost(){
    let h=gid('v161FilterBar');if(h)return h;
    h=document.createElement('div');h.id='v161FilterBar';
    h.innerHTML='<div class="v161-filter-grid" id="v161FilterGrid"></div>';
    const hero=qs('.hero');
    if(hero)hero.insertAdjacentElement('afterend',h);
    else (qs('.main')||document.body).prepend(h);
    return h;
  }

  function copyOptions(src,dst){
    dst.innerHTML='';
    [...src.options].forEach(o=>dst.add(new Option(o.text,o.value,o.defaultSelected,o.selected)));
    dst.value=src.value;
  }

  function makeField(label,id){
    const src=gid(id);if(!src)return null;
    const wrap=document.createElement('div');wrap.className='v161-field';
    const lab=document.createElement('label');lab.textContent=label;
    let ctrl;
    if(src.tagName==='SELECT'){
      ctrl=document.createElement('select');copyOptions(src,ctrl);
      ctrl.addEventListener('change',()=>{
        src.value=ctrl.value;
        src.dispatchEvent(new Event('change',{bubbles:true}));
      });
    }else{
      ctrl=document.createElement('input');ctrl.type=src.type||'text';ctrl.value=src.value||'';
      ctrl.addEventListener('change',()=>{src.value=ctrl.value;src.dispatchEvent(new Event('change',{bubbles:true}))});
    }
    ctrl.dataset.source=id;wrap.append(lab,ctrl);return wrap;
  }

  function clickApply(mod){
    if(mod==='analysis'){
      const b=gid('refresh');if(b){b.click();return}
      ['week','store','section','catalog'].forEach(id=>gid(id)?.dispatchEvent(new Event('change',{bubbles:true})));
      return;
    }
    const b=gid('operPeriodApply');
    if(b){b.click();return}
    ['operPeriodMode','operPeriodSelect','operStoreSelect','operAreaSelect','operActivitySelect'].forEach(id=>gid(id)?.dispatchEvent(new Event('change',{bubbles:true})));
  }

  function render(){
    const mod=moduleName(),tab=activeTab(mod),h=ensureHost(),g=gid('v161FilterGrid');
    if(!mod){h.classList.remove('on');return}
    ensureMode();
    const fields=spec(mod,tab);g.innerHTML='';
    fields.forEach(d=>{const f=makeField(d[0],d[1]);if(f)g.appendChild(f)});
    if(!fields.length||!g.children.length){h.classList.remove('on');return}
    const go=document.createElement('button');go.type='button';go.className='v161-apply';go.textContent='⌕  Consultar';
    go.onclick=()=>{clickApply(mod);schedule()};g.appendChild(go);h.classList.add('on');
  }

  function schedule(){[30,180,520,1000].forEach(ms=>setTimeout(render,ms))}

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],[data-sub],[data-opview],#operativoNav,#analysisNav,.v125-tabs,#refresh,#operPeriodApply'))schedule();
  },true);
  document.addEventListener('change',e=>{
    if(e.target?.matches?.('select,input'))setTimeout(render,100);
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();
  console.info('[V161] Filtro único por reporte + tarjetas de boceto; tablas y gráficas intactas.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v161_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body=b''
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode('utf-8',errors='replace')
            if 'v161-unified-boceto-css' not in html:
                html=html.replace('</head>',css+'</head>',1)
            if 'v161-unified-boceto-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            headers=dict(getattr(response,'headers',{}) or {})
            headers.pop('content-length',None)
            headers.update({
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma':'no-cache','Expires':'0',
                'X-Operations-UI-Version':'V161-UNIFIED-BOCETO'
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f'[V161] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V161_UNIFIED_BOCETO=True
    print('[V161] Filtro único replicado en reportes; tarjetas ajustadas; tablas/gráficas intactas.',flush=True)
