"""V142 · Ajuste móvil del demo Comercial + 17 tiendas.

Corrige desbordes observados en iPhone sobre la réplica V141: KPIs, Macro sección,
Sección/Rubro y Sell Through se compactan sin superponer textos. Las tablas
anchas usan desplazamiento local cuando realmente lo requieren. Además, Tiendas
muestra las 17 tiendas del proyecto tanto en ranking como en comparativo visual.
Sólo afecta el demo del propietario; no modifica datos reales.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V142_COMMERCIAL_MOBILE_FIT", False):
        return

    js = r'''<script id="v142-commercial-mobile-fit-js">
(function(){
  var storeRows=[
    {n:'Iztapalapa',s:452610,c:'A',e:218500,o:92.3,d:48,status:'Exceso',cls:'bad'},
    {n:'Vallejo',s:438900,c:'B',e:211240,o:89.6,d:54,status:'Óptimo',cls:''},
    {n:'Ecatepec',s:362250,c:'B',e:176340,o:78.4,d:71,status:'Óptimo',cls:''},
    {n:'Querétaro',s:358890,c:'B',e:159040,o:74.2,d:84,status:'Atención',cls:'warn'},
    {n:'Puebla',s:298760,c:'C',e:146800,o:69.7,d:96,status:'Atención',cls:'warn'},
    {n:'León',s:276310,c:'C',e:128650,o:63.5,d:112,status:'Riesgo',cls:'bad'},
    {n:'Toluca',s:268450,c:'B',e:131420,o:76.8,d:82,status:'Atención',cls:'warn'},
    {n:'Centro',s:257980,c:'B',e:124360,o:80.2,d:69,status:'Óptimo',cls:''},
    {n:'Ixtapaluca',s:246730,c:'B',e:119840,o:77.5,d:73,status:'Óptimo',cls:''},
    {n:'Arco Norte',s:232540,c:'C',e:112650,o:70.4,d:91,status:'Atención',cls:'warn'},
    {n:'Olivar',s:218960,c:'C',e:104300,o:68.2,d:98,status:'Atención',cls:'warn'},
    {n:'Naucalpan',s:207440,c:'C',e:101250,o:72.1,d:88,status:'Atención',cls:'warn'},
    {n:'Puebla Sur',s:194820,c:'C',e:95780,o:66.7,d:104,status:'Riesgo',cls:'bad'},
    {n:'Aguascalientes',s:183610,c:'C',e:89420,o:64.8,d:109,status:'Riesgo',cls:'bad'},
    {n:'Veracruz',s:176950,c:'C',e:86300,o:62.4,d:115,status:'Riesgo',cls:'bad'},
    {n:'Atemajac',s:169380,c:'C',e:82740,o:67.5,d:101,status:'Riesgo',cls:'bad'},
    {n:'Miravalle',s:162740,c:'C',e:79560,o:65.9,d:107,status:'Riesgo',cls:'bad'}
  ];
  var storeNames=storeRows.map(function(x){return x.n});
  var patchedRoot=null;
  function fmt(n){return Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});}
  function money(n){return '$'+fmt(n);}
  function hostShadow(){var h=document.getElementById('v141CommercialHost');return h&&h.shadowRoot?h.shadowRoot:null;}
  function root(){var sh=hostShadow();return sh?sh.getElementById('v139-demo-root'):null;}
  function mobileCss(){return `
:host{display:block!important;max-width:100%!important;overflow-x:hidden!important}
#v139-demo-root.app{width:100%!important;max-width:100%!important;min-width:0!important;overflow-x:hidden!important}
.card,.page,.filters,.kpis,.kpi,.grid2,.grid3,.macrosec,.highlight,.modelbox,.accordion-card,.tablewrap{min-width:0!important;max-width:100%!important}
.tablewrap{overflow-x:auto!important;overscroll-behavior-x:contain!important;-webkit-overflow-scrolling:touch!important}
.demo-note{padding:7px 9px!important;gap:7px!important}.demo-note .info{width:22px!important;height:22px!important;font-size:13px!important}.demo-note b{font-size:9px!important}.demo-note span{font-size:7px!important;line-height:1.25!important}
#sectionButtons{flex-wrap:nowrap!important;overflow-x:auto!important;-webkit-overflow-scrolling:touch!important;scrollbar-width:none!important}#sectionButtons::-webkit-scrollbar{display:none!important}
#sectionButtons .filterbtn{flex:0 0 auto!important}
#page-sell .st-table th{white-space:normal!important;line-height:1.05!important;text-align:left!important}
#page-sell .st-table td:nth-child(3){white-space:normal!important;line-height:1.1!important}
#page-more .table.wide{min-width:690px!important;width:690px!important;table-layout:auto!important}
@media(max-width:430px){
 .app{gap:6px!important}.card{padding:7px!important;border-radius:10px!important}.filters{gap:5px!important;padding:7px!important}.field label{font-size:6.5px!important;margin-bottom:4px!important}.field select{height:37px!important;font-size:10px!important;padding-left:7px!important}.query{height:40px!important;font-size:14px!important}.tab{min-height:34px!important;font-size:8px!important;padding:0 10px!important}.section-title{font-size:15px!important}.section-sub{font-size:8px!important}.link{font-size:7.5px!important}
 .kpis{gap:5px!important;margin-top:7px!important}.kpis.six{grid-template-columns:repeat(3,minmax(0,1fr))!important}.kpis.four,.st-kpis{grid-template-columns:repeat(4,minmax(0,1fr))!important}
 .kpi{min-height:60px!important;padding:5px 4px!important;gap:3px!important;border-radius:8px!important}.kpi .ico{width:25px!important;height:25px!important;font-size:12px!important}.kpi .label{font-size:6.3px!important;line-height:1.05!important}.kpi .value{font-size:10.5px!important;line-height:1!important;letter-spacing:-.35px!important;white-space:nowrap!important;overflow:visible!important}.kpi .unit{font-size:5.7px!important;line-height:1.05!important}.kpis.six .kpi .value{font-size:11.5px!important}.st-kpis .kpi .value{font-size:10.3px!important}
 .macrosec{padding:6px!important;overflow:hidden!important}.macrosec .top{gap:4px!important}.garment{width:28px!important;height:28px!important;font-size:15px!important}.macrosec .name{font-size:8px!important}.macrosec .big{font-size:10.8px!important;white-space:nowrap!important;letter-spacing:-.2px!important}.macrosec small{font-size:5.3px!important;white-space:normal!important;line-height:1.18!important;margin-top:4px!important;overflow-wrap:anywhere!important}
 .grid2{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important}.grid3{gap:5px!important}.bar{grid-template-columns:53px minmax(34px,1fr) 46px!important;gap:4px!important;font-size:6.7px!important}.bar b{font-size:6.8px!important}.track{height:11px!important}.percent{font-size:6.7px!important;padding:3px 4px!important}
 .table{font-size:6px!important}.table th,.table td{padding:4px 3px!important}.table th{white-space:normal!important;line-height:1.08!important}.table td{line-height:1.1!important}.badge{font-size:6.4px!important;padding:3px 5px!important}
 #page-stores .table{font-size:5.8px!important;table-layout:fixed!important;width:100%!important;min-width:0!important}#page-stores .table th,#page-stores .table td{padding:4px 2px!important}#page-stores .table th:nth-child(1),#page-stores .table td:nth-child(1){width:5%!important}#page-stores .table th:nth-child(2),#page-stores .table td:nth-child(2){width:17%!important}#page-stores .table th:nth-child(3),#page-stores .table td:nth-child(3){width:18%!important}#page-stores .table th:nth-child(4),#page-stores .table td:nth-child(4){width:8%!important}#page-stores .table th:nth-child(5),#page-stores .table td:nth-child(5){width:18%!important}#page-stores .table th:nth-child(6),#page-stores .table td:nth-child(6){width:14%!important}#page-stores .table th:nth-child(7),#page-stores .table td:nth-child(7){width:7%!important}#page-stores .table th:nth-child(8),#page-stores .table td:nth-child(8){width:13%!important}
 #page-sell .st-table{font-size:5.6px!important;table-layout:fixed!important;width:100%!important;min-width:0!important}#page-sell .st-table th,#page-sell .st-table td{padding:4px 2px!important}#page-sell .st-table th:nth-child(1),#page-sell .st-table td:nth-child(1){width:12%!important}#page-sell .st-table th:nth-child(2),#page-sell .st-table td:nth-child(2){width:10%!important}#page-sell .st-table th:nth-child(3),#page-sell .st-table td:nth-child(3){width:20%!important}#page-sell .st-table th:nth-child(4),#page-sell .st-table td:nth-child(4){width:11%!important}#page-sell .st-table th:nth-child(5),#page-sell .st-table td:nth-child(5){width:10%!important}#page-sell .st-table th:nth-child(6),#page-sell .st-table td:nth-child(6){width:10%!important}#page-sell .st-table th:nth-child(7),#page-sell .st-table td:nth-child(7){width:13%!important}#page-sell .st-table th:nth-child(8),#page-sell .st-table td:nth-child(8){width:14%!important}#page-sell .st-table td{white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}#page-sell .st-table td:nth-child(3){white-space:normal!important;overflow:visible!important}.stpct{min-width:33px!important;font-size:5.9px!important;padding:3px 3px!important}
 .filters-inline{gap:4px!important}.filterbtn{height:31px!important;padding:0 10px!important;font-size:7.5px!important}.mini-kpis{gap:3px!important}.mini{padding:4px!important}.mini .label{font-size:5.7px!important}.mini .value{font-size:8px!important}.models-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important}
}
`;}
  function ensureStyle(sh){if(sh.getElementById('v142-mobile-fit-style'))return;var s=document.createElement('style');s.id='v142-mobile-fit-style';s.textContent=mobileCss();sh.appendChild(s);}
  function ensureStoreOptions(r){var sel=r.querySelector('#store');if(!sel)return;var current=sel.value||'Compañía';var expected=['Compañía'].concat(storeNames);var actual=Array.from(sel.options).map(function(o){return o.value||o.textContent});if(expected.join('|')!==actual.join('|')){sel.innerHTML=expected.map(function(n){return '<option>'+n+'</option>';}).join('');if(expected.indexOf(current)>=0)sel.value=current;}}
  function patchStores(r){var page=r.querySelector('#page-stores');if(!page)return;var table=null;page.querySelectorAll('table').forEach(function(t){var txt=(t.querySelector('thead')||{}).textContent||'';if(!table&&/Tienda/i.test(txt)&&/Sugerido/i.test(txt))table=t;});if(table){var tb=table.querySelector('tbody');if(tb){tb.innerHTML=storeRows.map(function(x,i){return '<tr><td>'+(i+1)+'</td><td><b>'+x.n+'</b></td><td>'+money(x.s)+'</td><td>'+x.c+'</td><td>'+fmt(x.e)+'</td><td>'+x.o.toFixed(1)+'%</td><td>'+x.d+'</td><td><span class="badge '+x.cls+'">'+x.status+'</span></td></tr>';}).join('');}var hs=table.querySelectorAll('th');hs.forEach(function(h){h.textContent=h.textContent.replace(/pares/gi,'pzas');});}
    var bars=page.querySelector('.bars');if(bars){var mx=storeRows[0].s;bars.innerHTML=storeRows.map(function(x){var pct=Math.max(18,Math.round(x.s/mx*100));return '<div class="bar"><b>'+x.n+'</b><div class="track"><div class="fill" style="width:'+pct+'%"></div></div><span>'+money(x.s)+'</span></div>';}).join('');}
    var rankTitle=page.querySelector('.headrow .link');if(rankTitle&&/Ver todas/i.test(rankTitle.textContent||''))rankTitle.textContent='17 tiendas';
  }
  function fullComparator(store){if(!store||store==='Compañía')return 'Iztapalapa';var i=storeNames.indexOf(store);if(i<0)return 'Iztapalapa';return i===0?storeNames[1]:storeNames[i-1];}
  function updateComparator(r){var sel=r.querySelector('#store');var c=fullComparator(sel?sel.value:'Compañía');r.querySelectorAll('.cmp-store').forEach(function(x){x.textContent=c;});}
  function bindComparator(r){if(r.getAttribute('data-v142-bound')==='1')return;r.setAttribute('data-v142-bound','1');r.addEventListener('change',function(e){if(e.target&&e.target.id==='store')setTimeout(function(){updateComparator(r);},0);});r.addEventListener('click',function(e){if(e.target&&e.target.closest&&e.target.closest('#query'))setTimeout(function(){updateComparator(r);},0);});}
  function patch(){var sh=hostShadow(),r=root();if(!sh||!r)return false;ensureStyle(sh);ensureStoreOptions(r);patchStores(r);bindComparator(r);updateComparator(r);patchedRoot=r;return true;}
  function attempt(n){if(patch())return;if(n>0)setTimeout(function(){attempt(n-1);},260);}
  document.addEventListener('click',function(e){var m=e.target&&e.target.closest?e.target.closest('[data-main]'):null;if(m){var v=m.getAttribute('data-main');if(v==='analysis'||v==='commercial')setTimeout(function(){attempt(12);},180);}},true);
  setTimeout(function(){attempt(16);},300);
  console.info('[V142] Ajuste móvil Comercial + 17 tiendas preparado.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v142_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode('utf-8', errors='replace')
            if 'v142-commercial-mobile-fit-js' not in html:
                html = html.replace('</body>', js + '</body>', 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Operations-UI-Version': 'V142-COMMERCIAL-MOBILE-FIT-17-STORES',
            })
        except Exception as exc:
            print(f'[V142] HTML warning: {type(exc).__name__}: {exc}', flush=True)
            return response

    m._V142_COMMERCIAL_MOBILE_FIT = True
    print('[V142] Comercial móvil ajustado + 17 tiendas instaladas.', flush=True)
