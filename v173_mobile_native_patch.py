"""V173 · Experiencia móvil nativa para Operaciones Ropa.

Capa exclusivamente visual e interactiva para pantallas <= 900 px.
No modifica endpoints, cálculos, archivos cargados, reglas de negocio ni exportaciones.

Objetivos:
- reducir altura desperdiciada sin volver ilegibles los KPIs;
- convertir Recuperación por tienda en tarjetas progresivas en móvil;
- mejorar navegación inferior y pestañas horizontales;
- conservar las tablas completas en escritorio y como fuente de verdad en DOM;
- respetar safe areas de iPhone mediante viewport-fit=cover.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V173_MOBILE_NATIVE", False):
        return

    css = r'''<style id="v173-mobile-native-css">
/* Escritorio permanece gobernado por V171/V172. */
.v173-recovery-list{display:none}

@media(max-width:900px){
  html{scroll-padding-bottom:76px;-webkit-tap-highlight-color:transparent}
  body{background:#f3f6fa!important}
  .main{padding:6px 7px calc(72px + env(safe-area-inset-bottom))!important}

  /* Encabezado: compacto, con jerarquía clara. */
  .hero{min-height:54px!important;padding:9px 10px!important;border-radius:13px!important;margin-bottom:6px!important}
  .hero h1{font-size:17px!important;line-height:1.08!important;letter-spacing:-.025em!important}
  .hero p{font-size:8.2px!important;line-height:1.25!important;margin-top:3px!important}
  .title{font-size:18px!important;line-height:1.12!important;margin:11px 1px 6px!important;letter-spacing:-.02em!important}
  .subtitle{font-size:8.4px!important;line-height:1.35!important;margin-bottom:6px!important;color:#6e7f94!important}

  /* Filtros: dos columnas, controles táctiles de 42 px. */
  .filters,.v161-filter-shell,#v161FilterBar{padding:6px!important;border-radius:12px!important}
  .v161-filter-grid,.filters{gap:6px!important}
  .filter label,.v161-field label,.v166-internal-filter label{font-size:7.3px!important;line-height:1.15!important;margin-bottom:3px!important}
  .filter select,.filter input,.v161-field select,.v161-field input,.v166-internal-filter select{
    min-height:42px!important;height:42px!important;font-size:12px!important;padding-top:7px!important;padding-bottom:7px!important;border-radius:10px!important
  }
  .primary,.v161-actions button,.v161-apply{min-height:42px!important;height:42px!important;font-size:11.5px!important;border-radius:10px!important}

  /* KPIs: 2 columnas, menos aire y texto más legible que V172. */
  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{
    display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:6px!important;margin:6px 0 9px!important;width:100%!important
  }
  .kpi,.report-kpi,.v149-kpi,.v126-kpi,.v125-kpi,.v164-matrix-kpi,.v165-mini-kpi,.v168-plan-kpi,.sales-kpi{
    min-width:0!important;min-height:80px!important;height:auto!important;padding:9px 7px 8px 36px!important;border-radius:11px!important;
    border-color:#d5e1ee!important;box-shadow:0 1px 3px rgba(18,59,115,.045)!important;overflow:hidden!important
  }
  .v166-kpi-icon,.v164-kpi-icon,.v167-card-icon{
    left:8px!important;top:11px!important;width:22px!important;height:22px!important;min-width:22px!important;border-radius:50%!important
  }
  .v166-kpi-icon svg,.v164-kpi-icon svg,.v167-card-icon svg{width:13px!important;height:13px!important}
  .lab,.report-kpi .rk-label,.v149-kpi small,.v126-kpi small,.v125-kpi small,.v164-matrix-kpi small,.v165-mini-kpi small,.sales-kpi .sl{
    font-size:7.2px!important;line-height:1.12!important;letter-spacing:.015em!important;font-weight:900!important;overflow-wrap:anywhere!important
  }
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b,.v164-matrix-kpi b,.v165-mini-kpi b,.v168-plan-kpi b,.sales-kpi .sv{
    font-size:clamp(20px,5.45vw,25px)!important;line-height:1!important;margin:5px 0 4px!important;letter-spacing:-.045em!important;
    font-variant-numeric:tabular-nums!important;white-space:nowrap!important
  }
  .note,.report-kpi .rk-sub,.v149-kpi span,.v126-kpi span,.v125-kpi span,.v164-matrix-kpi span,.v168-plan-kpi span,.sales-kpi .ss{
    font-size:7.4px!important;line-height:1.22!important;color:#718197!important;overflow-wrap:anywhere!important
  }

  /* Pestañas: carrusel horizontal corto. Los dos botones utilitarios entran al mismo carrusel. */
  #analysisNav,#operativoNav,.v125-tabs,.op-tabs,.switches{
    display:flex!important;grid-template-columns:none!important;flex-wrap:nowrap!important;gap:5px!important;overflow-x:auto!important;overflow-y:hidden!important;
    padding:5px!important;margin-top:5px!important;margin-bottom:7px!important;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch!important;scrollbar-width:none!important
  }
  #analysisNav::-webkit-scrollbar,#operativoNav::-webkit-scrollbar,.v125-tabs::-webkit-scrollbar,.op-tabs::-webkit-scrollbar,.switches::-webkit-scrollbar{display:none!important}
  #operativoNav>div{display:contents!important;margin:0!important}
  #analysisNav>button,#operativoNav>button,#operativoNav>div>button,.v125-tabs>button,.op-tabs>button,.switches>button{
    flex:0 0 102px!important;min-width:102px!important;min-height:44px!important;height:auto!important;padding:6px 6px!important;border-radius:10px!important;
    font-size:8px!important;line-height:1.12!important;scroll-snap-align:start!important;white-space:normal!important
  }
  .v166-tab-icon,.v167-tab-icon{width:16px!important;height:16px!important;flex-basis:16px!important}
  .v166-tab-icon svg,.v167-tab-icon svg{width:14px!important;height:14px!important}

  /* Paneles y gráficas. */
  .panel,.card,.chart-box{padding:9px!important;border-radius:11px!important}
  .chart-title,.panel-head b{font-size:10.5px!important;line-height:1.2!important}
  .chart-scroll,.sales-chart-scroll,.v168-pivot-wrap,.v168-plan-matrix{max-width:100%!important;overflow:auto!important;-webkit-overflow-scrolling:touch!important}

  /* Tablas normales conservan scroll horizontal, con lectura un poco mayor. */
  .tablewrap{max-width:100%!important;overflow:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior-x:contain!important;border-radius:10px!important}
  .table{width:max-content!important;min-width:700px!important;font-size:8.2px!important}
  .table th{font-size:7.6px!important;padding:7px 6px!important;white-space:nowrap!important;position:sticky!important;top:0!important;z-index:3!important}
  .table td{font-size:8.2px!important;padding:6.5px 6px!important;line-height:1.25!important;white-space:nowrap!important}

  /* Recuperación por tienda: vista de tarjetas en móvil, tabla original intacta en DOM. */
  .v173-recovery-wrap{overflow:visible!important;border:0!important;background:transparent!important;border-radius:0!important}
  .v173-recovery-wrap table.table{display:none!important}
  .v173-recovery-list{display:grid!important;gap:6px!important;width:100%!important}
  .v173-recovery-card{background:#fff;border:1px solid #d7e2ee;border-radius:11px;box-shadow:0 1px 3px rgba(18,59,115,.045);overflow:hidden}
  .v173-recovery-card.is-project{border-left:3px solid #1769e8;background:linear-gradient(90deg,#f5f9ff 0,#fff 24%)}
  .v173-recovery-head{display:flex;align-items:center;gap:6px;padding:8px 9px 4px}
  .v173-rank{display:inline-grid;place-items:center;min-width:25px;height:22px;padding:0 6px;border-radius:7px;background:#edf3fa;color:#173f78;font-size:8px;font-weight:950}
  .v173-store{min-width:0;flex:1;font-size:10.5px;line-height:1.1;font-weight:950;color:#173f78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .v173-project{flex:0 0 auto;padding:3px 6px;border-radius:999px;background:#eaf2ff;color:#1769e8;font-size:6.6px;font-weight:950}
  .v173-recovery-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:3px 8px 7px}
  .v173-metric{min-width:0;padding:6px 5px;border-radius:8px;background:#f7f9fc;border:1px solid #edf1f6}
  .v173-metric span{display:block;font-size:6.2px;line-height:1.12;font-weight:850;color:#78889c;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .v173-metric b{display:block;margin-top:3px;font-size:12.5px;line-height:1;font-weight:950;color:#173f78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}
  .v173-metric.primary b{color:#1769e8}
  .v173-detail-toggle{display:flex!important;align-items:center!important;justify-content:center!important;gap:4px!important;width:100%!important;min-height:29px!important;border:0!important;border-top:1px solid #eef2f6!important;border-radius:0!important;background:#fff!important;color:#64768c!important;font-size:7.3px!important;font-weight:900!important;padding:5px!important}
  .v173-detail-toggle:after{content:'⌄';font-size:10px;transition:transform .16s ease}
  .v173-detail-toggle[aria-expanded="true"]:after{transform:rotate(180deg)}
  .v173-recovery-details{display:grid;grid-template-columns:1fr 1fr;gap:0 10px;padding:2px 9px 8px;border-top:1px solid #f1f4f7;background:#fbfcfe}
  .v173-recovery-details[hidden]{display:none!important}
  .v173-detail-row{display:flex;align-items:center;justify-content:space-between;gap:6px;min-width:0;padding:5px 0;border-bottom:1px solid #f0f3f6;font-size:7.2px;color:#718197}
  .v173-detail-row b{font-size:8px;color:#173f78;white-space:nowrap;font-variant-numeric:tabular-nums}

  /* Navegación inferior estilo app: visible, estable y con safe-area. */
  .mobile{
    display:grid!important;grid-template-columns:none!important;grid-auto-flow:column!important;grid-auto-columns:minmax(0,1fr)!important;
    position:fixed!important;left:0!important;right:0!important;bottom:0!important;z-index:500!important;min-height:58px!important;
    padding:4px 5px calc(4px + env(safe-area-inset-bottom))!important;background:rgba(255,255,255,.97)!important;border-top:1px solid #dbe3ed!important;
    box-shadow:0 -4px 16px rgba(11,45,92,.09)!important;backdrop-filter:blur(12px)!important;-webkit-backdrop-filter:blur(12px)!important
  }
  .mnav{position:relative!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:1px!important;min-height:48px!important;padding:4px 2px!important;border-radius:10px!important;font-size:7.6px!important;line-height:1.05!important;font-weight:900!important;color:#6f7f92!important}
  .mnav-icon{font-size:18px!important;line-height:19px!important;margin:0!important}
  .mnav.active{background:#eaf2ff!important;color:#1769e8!important;box-shadow:none!important}
  .mnav.active:after{content:"";position:absolute;left:50%;bottom:3px;width:18px;height:2px;border-radius:99px;background:#1769e8;transform:translateX(-50%)}
}

@media(max-width:520px){
  .main{padding-left:5px!important;padding-right:5px!important}
  .v161-filter-grid,.filters{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .v161-actions,.filters .primary{grid-column:1/-1!important;width:100%!important}
}

@media(max-width:340px){
  .kpis,.report-kpis,.v149-kpis,.v126-kpis,.v125-kpis,.v164-matrix-kpis,.v165-mini-kpis,.v168-plan-kpis,.sales-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .val,.report-kpi .rk-value,.v149-kpi b,.v126-kpi b,.v125-kpi b{font-size:18px!important}
  .v173-recovery-details{grid-template-columns:1fr!important}
}
</style>'''

    js = r'''<script id="v173-mobile-native-js">
(function(){
  if(window.__V173_MOBILE_NATIVE)return;
  window.__V173_MOBILE_NATIVE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const mobile=()=>window.matchMedia('(max-width:900px)').matches;
  const norm=v=>String(v||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/s+/g,' ').trim();
  const esc=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

  function headerIndex(headers,tests){
    return headers.findIndex(h=>tests.some(t=>h.includes(t)));
  }

  function isRecoveryTable(table){
    const headers=qa('thead th',table).map(x=>norm(x.textContent));
    if(!headers.length)return false;
    return headerIndex(headers,['tienda'])>=0 &&
      headerIndex(headers,['dev pzs','dev'])>=0 &&
      headerIndex(headers,['pzas recuperadas','piezas recuperadas','recup.'])>=0 &&
      headerIndex(headers,['conversion'])>=0;
  }

  function recoverySignature(table){
    const heads=qa('thead th',table).map(x=>norm(x.textContent)).join('|');
    const rows=qa('tbody tr',table).map(r=>qa('td',r).map(c=>norm(c.textContent)).join('|')).join('||');
    return heads+'::'+rows;
  }

  function buildRecoveryCards(wrap,table){
    const headers=qa('thead th',table).map(x=>norm(x.textContent));
    const idx={
      rank:headerIndex(headers,['#','ranking']),
      store:headerIndex(headers,['tienda']),
      dev:headerIndex(headers,['dev pzs','dev']),
      recovered:headerIndex(headers,['pzas recuperadas','piezas recuperadas','recup.']),
      conversion:headerIndex(headers,['conversion']),
      returnValue:headerIndex(headers,['valor devolucion','valor dev']),
      recoveredValue:headerIndex(headers,['recuperacion $','recup. $']),
      recoveredPct:headerIndex(headers,['recup. %','recuperacion %']),
      pendingPieces:headerIndex(headers,['pend. pzs','pend pzs','pendiente pzs']),
      pendingValue:headerIndex(headers,['pend. $','pend $','pendiente $'])
    };
    const sig=recoverySignature(table);
    if(wrap.dataset.v173Sig===sig && q('.v173-recovery-list',wrap))return;
    wrap.dataset.v173Sig=sig;
    wrap.classList.add('v173-recovery-wrap');
    q('.v173-recovery-list',wrap)?.remove();

    const list=document.createElement('div');
    list.className='v173-recovery-list';
    const rows=qa('tbody tr',table).filter(r=>qa('td',r).length>1);
    list.innerHTML=rows.map((row,i)=>{
      const cells=qa('td',row).map(c=>String(c.textContent||'').replace(/s+/g,' ').trim());
      const val=k=>idx[k]>=0?(cells[idx[k]]||'—'):'—';
      const project=row.classList.contains('project-row') || /proyecto/i.test(val('store'));
      const store=val('store').replace(/s*Proyectos*$/i,'').trim();
      const rank=idx.rank>=0?val('rank'):'#'+(i+1);
      const detailPairs=[
        ['Valor devolución',val('returnValue')],['Recuperación $',val('recoveredValue')],
        ['Recup. %',val('recoveredPct')],['Pend. Pzs',val('pendingPieces')],['Pend. $',val('pendingValue')]
      ].filter(x=>x[1]!=='—');
      return `<article class="v173-recovery-card${project?' is-project':''}">
        <div class="v173-recovery-head"><span class="v173-rank">${esc(rank)}</span><span class="v173-store">${esc(store)}</span>${project?'<span class="v173-project">Proyecto</span>':''}</div>
        <div class="v173-recovery-metrics">
          <div class="v173-metric"><span>Dev Pzs</span><b>${esc(val('dev'))}</b></div>
          <div class="v173-metric"><span>Recuperadas</span><b>${esc(val('recovered'))}</b></div>
          <div class="v173-metric primary"><span>Conversión</span><b>${esc(val('conversion'))}</b></div>
        </div>
        ${detailPairs.length?`<button type="button" class="v173-detail-toggle" aria-expanded="false">Ver detalle</button><div class="v173-recovery-details" hidden>${detailPairs.map(x=>`<div class="v173-detail-row"><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div>`:''}
      </article>`;
    }).join('');
    if(rows.length)wrap.appendChild(list);
  }

  function enhanceRecoveryTables(){
    qa('.tablewrap').forEach(wrap=>{
      const table=q('table.table',wrap);
      if(!table||!isRecoveryTable(table))return;
      buildRecoveryCards(wrap,table);
    });
  }

  function centerActiveNav(){
    if(!mobile())return;
    ['#operativoNav','#analysisNav','.v125-tabs'].forEach(sel=>{
      const nav=q(sel); if(!nav||nav.classList.contains('hidden'))return;
      const active=q('.active',nav); if(!active)return;
      const left=active.offsetLeft-(nav.clientWidth-active.clientWidth)/2;
      if(Math.abs(nav.scrollLeft-left)>80) nav.scrollTo({left:Math.max(0,left),behavior:'smooth'});
    });
  }

  function enhance(){
    if(!mobile())return;
    enhanceRecoveryTables();
    centerActiveNav();
  }

  function schedule(){[0,90,280,700].forEach(ms=>setTimeout(enhance,ms))}

  document.addEventListener('click',e=>{
    const toggle=e.target.closest?.('.v173-detail-toggle');
    if(toggle){
      const details=toggle.nextElementSibling;
      const open=toggle.getAttribute('aria-expanded')==='true';
      toggle.setAttribute('aria-expanded',String(!open));
      toggle.textContent=open?'Ver detalle':'Ocultar detalle';
      if(details)details.hidden=open;
      return;
    }
    if(e.target.closest?.('#operativoNav,#analysisNav,.v125-tabs,.op-tabs,.mnav,[data-opview],[data-main],[data-sub],#refresh'))schedule();
  },true);

  document.addEventListener('change',e=>{
    if(e.target.matches?.('select,input,#operPeriodMode,#operPeriodSelect,#operStoreSelect,#store,#week,#section,#catalog'))schedule();
  },true);

  window.addEventListener('resize',()=>setTimeout(enhance,120),{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(enhance,220),{passive:true});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
  console.info('[V173] experiencia móvil nativa instalada.');
})();
</script>'''

    @m.app.middleware("http")
    async def v173_mobile_native(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "viewport-fit=cover" not in html:
                html = html.replace(
                    'content="width=device-width,initial-scale=1"',
                    'content="width=device-width,initial-scale=1,viewport-fit=cover"',
                    1,
                )
            if "v173-mobile-native-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v173-mobile-native-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V173_MOBILE_NATIVE = True
    print("[V173] experiencia móvil nativa instalada.", flush=True)
