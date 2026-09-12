"""V127 · Demo visual temporal de Operación.

Muestra al Super Administrador un demo de sólo lectura en Operación > Resumen,
con datos ficticios acumulados de enero a septiembre 2026 y el diseño aprobado.
No inserta, modifica ni reemplaza datos reales. Quitar este patch restaura V126.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V127_OPERATION_DEMO", False):
        return

    css = r'''<style id="v127-operation-demo-css">
.v127-demo-badge{display:inline-flex;align-items:center;margin-left:8px;padding:4px 9px;border-radius:999px;background:#dff7ff;color:#0b5f84;font-size:10px;font-weight:950;vertical-align:middle;letter-spacing:.02em}
.v127-demo-note{display:flex;align-items:center;gap:8px;padding:9px 11px;border:1px solid #b9d8ff;background:#eef6ff;border-radius:11px;color:#174b85;font-size:9px;font-weight:800;margin:8px 0 12px}
.v127-section{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;margin:10px 0}.v127-section h3{margin:0;color:var(--navy);font-size:15px}.v127-sub{color:#68768e;font-size:9px;margin-top:3px}
.v127-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin-top:12px}.v127-kpi{border:1px solid #dfe7f0;border-radius:13px;padding:12px;background:#fff;min-width:0}.v127-kpi small{display:block;font-size:8px;font-weight:900;color:#56667e}.v127-kpi b{display:block;font-size:24px;color:#0f3975;margin-top:6px;line-height:1}.v127-kpi em{display:block;font-size:8px;color:#79879b;margin-top:5px;font-style:normal}.v127-kpi.good{background:#eefcf5;border-color:#bfead4}.v127-kpi.good b,.v127-kpi.good small{color:#14834a}.v127-kpi.warn{background:#fff5f5;border-color:#ffd1d1}.v127-kpi.warn b,.v127-kpi.warn small{color:#d62939}.v127-kpi.purple{background:#f7f3ff;border-color:#ddd0ff}.v127-kpi.purple b,.v127-kpi.purple small{color:#5f32c9}
.v127-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v127-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;min-width:0}.v127-card h4{margin:0;color:var(--navy);font-size:13px}.v127-table{width:100%;border-collapse:collapse;margin-top:10px;font-size:9px}.v127-table th{background:#f2f6fb;color:#53657e;text-align:left;padding:8px;border-bottom:1px solid #dce5ef}.v127-table td{padding:8px;border-bottom:1px solid #e7edf4;color:#163c73}.v127-table tr:last-child td{font-weight:900;background:#eef6ff;color:#1763c6}
.v127-store-row{display:grid;grid-template-columns:92px minmax(80px,1fr) 58px;align-items:center;gap:8px;margin:9px 0;font-size:9px;color:#173f78}.v127-track{height:13px;background:#e8edf3;border-radius:7px;overflow:hidden}.v127-fill{height:100%;border-radius:7px;background:#2e6de6}.v127-pill{padding:5px 7px;border-radius:999px;background:#e8f8ed;color:#168044;font-weight:900;text-align:center}
.v127-toprow{display:grid;grid-template-columns:30px minmax(100px,1fr) 80px;gap:7px;align-items:center;padding:8px 0;border-bottom:1px solid #e7edf4;font-size:9px}.v127-toprow:last-child{border-bottom:0}.v127-toprow b{color:#173f78}.v127-rank{font-weight:950;color:#173f78}.v127-value{text-align:right;color:#173f78;font-weight:900}
.v127-alert{display:grid;grid-template-columns:30px minmax(0,1fr) 18px;gap:8px;align-items:center;padding:10px 0;border-bottom:1px solid #e8edf3}.v127-alert:last-child{border-bottom:0}.v127-dot{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-weight:950;color:#fff;background:#2e6de6}.v127-dot.red{background:#ef3f50}.v127-dot.orange{background:#f4a000}.v127-alert b{display:block;color:#163c73;font-size:9px}.v127-alert span{display:block;color:#758298;font-size:8px;margin-top:2px}.v127-chevron{font-size:16px;color:#7d899b}
.v127-demo-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.v127-demo-actions button{min-height:40px}
@media(max-width:900px){.v127-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v127-grid{grid-template-columns:1fr}.v127-kpi{padding:11px}.v127-kpi b{font-size:22px}.v127-section,.v127-card{padding:12px}.v127-store-row{grid-template-columns:88px minmax(70px,1fr) 54px}.v127-demo-note{font-size:8px}}
</style>'''

    js = r'''<script id="v127-operation-demo-js">
(function(){
  const OP='Operación';
  const isDemoUser=()=>USER?.role==='superadmin';
  const fmt=n=>Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const pct=n=>`${Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:1})}%`;
  const demo={
    summary:{arrival:148320,processed:139870,released:136540,pending:8450,efficiency:94.3,avg:1042,compliance:101.8,collaborators:128},
    origin:[['Origen',148320,'92.6%'],['Cambios',7180,'4.5%'],['Muertos',4680,'2.9%'],['Total',160180,'100.0%']],
    stores:[['Iztapalapa',97.2],['Vallejo',95.6],['Ecatepec',93.1],['Puebla',92.8],['León',90.4]],
    top:[['Ana Martínez',2436],['Carlos López',2215],['María González',2102],['Jorge Ramírez',1998],['Laura Torres',1876]],
    alerts:[['red','!','2 tiendas con eficiencia menor a 90%','Puebla 88.5% · León 86.2%'],['orange','!','Pendiente de liberar > 5,000','8,450 prendas en total'],['blue','i','3 tiendas sin captura en los últimos 3 días','Toluca · Querétaro · Aguascalientes'],['blue','i','Productividad por debajo del estándar','12 colaboradores']]
  };

  function setHeader(){
    const hero=$('#heroTitle');if(hero)hero.innerHTML='Operación <span class="v127-demo-badge">DEMO</span>';
    const hs=$('#heroSub');if(hs)hs.textContent='Control diario, productividad por colaborador y eficiencia de mercancía';
    const title=$('#operativoDynamicTitle');if(title)title.innerHTML='Operación <span class="v127-demo-badge">DEMO</span>';
    const sub=$('#operativoDynamicSub');if(sub)sub.textContent='Demo visual · acumulado enero a septiembre 2026';
  }
  function configureFilters(){
    const bar=$('#operativoPeriodBar');bar?.classList.remove('hidden');
    const modeWrap=$('#operPeriodModeWrap');modeWrap?.classList.remove('hidden');
    const mode=$('#operPeriodMode');if(mode){mode.innerHTML='<option value="year">Año</option>';mode.value='year';mode.disabled=true}
    const period=$('#operPeriodSelect');if(period){period.innerHTML='<option value="2026">2026</option>';period.value='2026';period.disabled=true}
    $('#operPeriodModeLabel') && ($('#operPeriodModeLabel').textContent='Vista');
    $('#operPeriodLabel') && ($('#operPeriodLabel').textContent='Periodo');
    const store=$('#operStoreSelect');if(store){store.innerHTML='<option value="Compañía">Compañía</option>';store.value='Compañía';store.disabled=true;store.closest('.filter')?.classList.remove('hidden');store.parentElement.querySelector('label').textContent='Tienda'}
    $('#operAreaSelect')?.closest('.filter')?.classList.add('hidden');
    $('#operActivitySelect')?.closest('.filter')?.classList.add('hidden');
    const btn=$('#operPeriodApply');if(btn){btn.textContent='Consultar';btn.disabled=false;btn.onclick=()=>renderDemo()}
  }
  function tabs(){return `<div class="v125-tabs" role="tablist"><button class="v125-tab active" data-v127-tab="summary">Resumen</button><button class="v125-tab" data-v127-tab="daily">Captura diaria</button><button class="v125-tab" data-v127-tab="capture">Cargar productividad</button><button class="v125-tab" data-v127-tab="productivity">Productividad</button><button class="v125-tab" data-v127-tab="standards">Estándares</button></div>`}
  function kpis(){const s=demo.summary,items=[['Llegada Origen',fmt(s.arrival),'Colgado + Doblado',''],['Productividad registrada',fmt(s.processed),'Acumulado','good'],['Mercancía liberada',fmt(s.released),'Origen','purple'],['Pendiente',fmt(s.pending),'Por liberar','warn'],['Eficiencia',pct(s.efficiency),'Procesadas / carga',''],['Prod. promedio',fmt(s.avg),'Pzas / colaborador / día',''],['Cumplimiento',pct(s.compliance),'Vs estándar','good'],['Colaboradores',fmt(s.collaborators),'Con productividad','']];return `<div class="v127-kpis">${items.map(x=>`<div class="v127-kpi ${x[3]}"><small>${x[0]}</small><b>${x[1]}</b><em>${x[2]}</em></div>`).join('')}</div>`}
  function originTable(){return `<div class="v127-card"><h4>Origen vs Cambios y Muertos</h4><div class="v127-sub">Acumulado 2026</div><table class="v127-table"><thead><tr><th>Tipo</th><th>Cantidad</th><th>% del total</th></tr></thead><tbody>${demo.origin.map(r=>`<tr><td>${r[0]}</td><td>${fmt(r[1])}</td><td>${r[2]}</td></tr>`).join('')}</tbody></table></div>`}
  function stores(){return `<div class="v127-card"><h4>Desempeño por tienda</h4><div class="v127-sub">Llegada vs mercancía liberada</div>${demo.stores.map(r=>`<div class="v127-store-row"><b>${r[0]}</b><div class="v127-track"><div class="v127-fill" style="width:${r[1]}%"></div></div><span class="v127-pill">${pct(r[1])}</span></div>`).join('')}</div>`}
  function top(){return `<div class="v127-card"><h4>Top 5 colaboradores</h4><div class="v127-sub">Por productividad registrada · acumulado</div><div style="margin-top:8px">${demo.top.map((r,i)=>`<div class="v127-toprow"><span class="v127-rank">#${i+1}</span><b>${r[0]}</b><span class="v127-value">${fmt(r[1])}</span></div>`).join('')}</div></div>`}
  function alerts(){return `<div class="v127-card"><h4>Alertas operativas</h4><div class="v127-sub">Prioridades para seguimiento</div>${demo.alerts.map(a=>`<div class="v127-alert"><span class="v127-dot ${a[0]==='blue'?'':a[0]}">${a[1]}</span><div><b>${a[2]}</b><span>${a[3]}</span></div><span class="v127-chevron">›</span></div>`).join('')}</div>`}
  function renderDemo(){
    if(!isDemoUser())return false;
    V125_OPERATION_TAB='summary';OP_VIEW=OP;OPER_PERIOD={type:'year',value:'2026'};
    const centro=$('#operativoCentro'),dyn=$('#operativoDynamic');centro?.classList.add('hidden');dyn?.classList.remove('hidden');setHeader();configureFilters();
    const content=$('#operativoDynamicContent');if(!content)return true;
    content.innerHTML=`${tabs()}<div class="v127-demo-note"><span>DEMO</span><span>Datos ficticios para visualizar el indicador lleno. No modifica la información real.</span></div><div class="v127-section"><h3>Resumen ejecutivo · Ene – Sep 2026</h3><div class="v127-sub">Indicadores acumulados del año al 11 de septiembre</div>${kpis()}</div><div class="v127-grid">${originTable()}${stores()}${top()}${alerts()}</div>`;
    document.querySelectorAll('[data-v127-tab]').forEach(b=>b.onclick=async()=>{
      const tab=b.dataset.v127Tab;if(tab==='summary'){renderDemo();return}
      V125_OPERATION_TAB=tab;OPER_PERIOD.value='';if(tab!=='productivity')OPER_PERIOD.type='day';await previousRender(OP,true);
    });
    return true;
  }

  const previousRender=window.renderOperativoView;
  window.renderOperativoView=async function(name,force=false){
    if(name===OP&&isDemoUser()&&(V125_OPERATION_TAB==='summary'||!V125_OPERATION_TAB)){renderDemo();return}
    return previousRender(name,force);
  };
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-main="operation"]');if(b&&isDemoUser()){V125_OPERATION_TAB='summary';setTimeout(renderDemo,80)}},true);
  if(isDemoUser()){V125_OPERATION_TAB='summary';setTimeout(()=>{if(window.MAIN==='operation'||window.OP_VIEW===OP)renderDemo()},350)}
  console.info('[V127] Demo visual de Operación activo para Super Administrador; datos reales intactos.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v127_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v127-operation-demo-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache", "Expires": "0", "X-Operations-UI-Version": "V127-DEMO"
            })
        except Exception as exc:
            print(f"[V127] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V127_OPERATION_DEMO = True
    print("[V127] Demo visual de Operación instalado para Super Administrador; sin tocar datos reales.", flush=True)
