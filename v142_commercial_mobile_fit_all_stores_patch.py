"""V143 · Corrección móvil del demo Comercial.

Reacomoda el diseño del demo aprobado para iPhone: KPIs en 2 columnas,
Macro sección a una tarjeta por fila, bloques dobles apilados y tablas anchas
con desplazamiento horizontal local en lugar de comprimir texto. Mantiene las
17 tiendas, filtros y comparador automático. Sólo afecta el demo del propietario.
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
    {n:'Vallejo',s:398320,c:'B',e:194120,o:86.1,d:62,status:'Óptimo',cls:''},
    {n:'Ecatepec',s:362250,c:'B',e:176340,o:78.4,d:71,status:'Óptimo',cls:''},
    {n:'Querétaro',s:358890,c:'B',e:159040,o:74.2,d:84,status:'Atención',cls:'warn'},
    {n:'Toluca',s:334800,c:'B',e:165900,o:76.9,d:79,status:'Óptimo',cls:''},
    {n:'Arco Norte',s:318240,c:'B',e:158300,o:75.1,d:83,status:'Atención',cls:'warn'},
    {n:'Ixtapaluca',s:309550,c:'B',e:151880,o:74.3,d:86,status:'Atención',cls:'warn'},
    {n:'Centro',s:301220,c:'B',e:149760,o:73.4,d:88,status:'Atención',cls:'warn'},
    {n:'Puebla',s:298760,c:'C',e:146800,o:69.7,d:96,status:'Atención',cls:'warn'},
    {n:'Naucalpan',s:289100,c:'B',e:143280,o:72.4,d:89,status:'Atención',cls:'warn'},
    {n:'Olivar',s:287430,c:'C',e:141550,o:71.8,d:91,status:'Atención',cls:'warn'},
    {n:'León',s:276310,c:'C',e:128650,o:63.5,d:112,status:'Riesgo',cls:'bad'},
    {n:'Puebla Sur',s:265980,c:'C',e:130420,o:67.8,d:102,status:'Riesgo',cls:'bad'},
    {n:'Aguascalientes',s:248360,c:'C',e:121600,o:66.1,d:106,status:'Riesgo',cls:'bad'},
    {n:'Veracruz',s:241980,c:'C',e:118740,o:65.5,d:108,status:'Riesgo',cls:'bad'},
    {n:'Miravalle',s:232440,c:'C',e:113920,o:64.2,d:111,status:'Riesgo',cls:'bad'},
    {n:'Atemajac',s:227350,c:'C',e:111630,o:63.8,d:113,status:'Riesgo',cls:'bad'}
  ];
  var storeNames=storeRows.map(function(x){return x.n});
  function fmt(n){return Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});}
  function money(n){return '$'+fmt(n);}
  function hostShadow(){var h=document.getElementById('v141CommercialHost');return h&&h.shadowRoot?h.shadowRoot:null;}
  function root(){var sh=hostShadow();return sh?sh.getElementById('v139-demo-root'):null;}
  function mobileCss(){return `
:host{display:block!important;width:100%!important;max-width:100%!important;overflow-x:hidden!important}
#v139-demo-root.app{width:100%!important;max-width:100%!important;min-width:0!important;overflow-x:hidden!important}
.card,.page,.filters,.kpis,.kpi,.grid2,.grid3,.macrosec,.highlight,.modelbox,.accordion-card,.tablewrap{min-width:0!important;max-width:100%!important}
.tabs{overflow-x:auto!important;-webkit-overflow-scrolling:touch!important;scrollbar-width:none!important}.tabs::-webkit-scrollbar{display:none!important}
.tablewrap{overflow-x:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior-x:contain!important;max-width:100%!important}
.demo-note{padding:8px 10px!important;gap:8px!important}.demo-note .info{width:24px!important;height:24px!important;font-size:14px!important}.demo-note b{font-size:10px!important}.demo-note span{font-size:8px!important;line-height:1.28!important}
#sectionButtons,.filters-inline{overflow-x:auto!important;flex-wrap:nowrap!important;-webkit-overflow-scrolling:touch!important;scrollbar-width:none!important}#sectionButtons::-webkit-scrollbar,.filters-inline::-webkit-scrollbar{display:none!important}
#sectionButtons .filterbtn,.filters-inline .filterbtn{flex:0 0 auto!important}
@media(max-width:430px){
 .app{gap:7px!important}.card{padding:9px!important;border-radius:11px!important}
 .filters{grid-template-columns:1fr!important;gap:8px!important;padding:9px!important}
 .field label{font-size:7px!important;margin-bottom:5px!important}.field select{height:42px!important;font-size:12px!important;padding-left:9px!important}.query{height:44px!important;font-size:16px!important}
 .tab{min-height:38px!important;font-size:10px!important;padding:0 13px!important;flex:0 0 auto!important}.section-title{font-size:17px!important;line-height:1.08!important}.section-sub{font-size:9px!important;line-height:1.25!important}.link{font-size:8px!important}
 .kpis.six,.kpis.four,.st-kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
 .kpi{min-height:76px!important;padding:8px!important;gap:7px!important;border-radius:9px!important;overflow:hidden!important}.kpi .ico{width:32px!important;height:32px!important;font-size:15px!important}.kpi .label{font-size:8px!important;line-height:1.12!important}.kpi .value{font-size:15px!important;line-height:1.04!important;letter-spacing:-.25px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}.kpi .unit{font-size:7px!important;line-height:1.08!important}
 #page-macro .grid3{grid-template-columns:1fr!important;gap:7px!important}.macrosec{padding:9px!important;overflow:hidden!important}.macrosec .top{gap:8px!important}.garment{width:36px!important;height:36px!important;font-size:19px!important}.macrosec .name{font-size:11px!important}.macrosec .big{font-size:14px!important;white-space:nowrap!important}.macrosec small{font-size:8px!important;white-space:normal!important;line-height:1.25!important;margin-top:6px!important;overflow-wrap:anywhere!important}
 .grid2{grid-template-columns:1fr!important;gap:8px!important}.grid3{gap:7px!important}
 .bar{grid-template-columns:82px minmax(75px,1fr) 62px!important;gap:6px!important;font-size:9px!important}.bar b{font-size:9px!important}.track{height:14px!important}.percent{font-size:8px!important;padding:4px 5px!important}
 .mini-kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:6px!important}.mini{padding:7px!important}.mini .label{font-size:7px!important}.mini .value{font-size:10px!important}.accordion-card .grid2{grid-template-columns:1fr!important}
 .table{font-size:10px!important}.table th,.table td{padding:7px 6px!important;white-space:nowrap!important;line-height:1.15!important}.badge{font-size:8px!important;padding:4px 7px!important}
 #page-stores .table{min-width:860px!important;width:860px!important;table-layout:auto!important;font-size:10px!important}
 #page-sections .table,#page-section .table{min-width:760px!important;width:760px!important;table-layout:auto!important;font-size:10px!important}
 #page-areas .table{min-width:900px!important;width:900px!important;table-layout:auto!important;font-size:10px!important}
 #page-more .table.wide,#page-more .table{min-width:900px!important;table-layout:auto!important;font-size:10px!important}
 #page-sell .st-table{min-width:980px!important;width:980px!important;table-layout:auto!important;font-size:10px!important}
 #page-sell .st-table th,#page-sell .st-table td{padding:7px 6px!important;white-space:nowrap!important;overflow:visible!important;text-overflow:clip!important}.stpct{min-width:42px!important;font-size:8px!important;padding:4px 5px!important}
 .filterbtn{height:36px!important;padding:0 14px!important;font-size:9px!important;flex:0 0 auto!important}.models-grid{grid-template-columns:1fr!important;gap:7px!important}
}
`;}
  function ensureStyle(sh){var old=sh.getElementById('v142-mobile-fit-style');if(old)old.remove();var s=document.createElement('style');s.id='v142-mobile-fit-style';s.textContent=mobileCss();sh.appendChild(s);}
  function ensureStoreOptions(r){var sel=r.querySelector('#store');if(!sel)return;var current=sel.value||'Compañía';var expected=['Compañía'].concat(storeNames);sel.innerHTML=expected.map(function(n){return '<option>'+n+'</option>';}).join('');if(expected.indexOf(current)>=0)sel.value=current;}
  function patchStores(r){var page=r.querySelector('#page-stores');if(!page)return;var table=null;page.querySelectorAll('table').forEach(function(t){var txt=(t.querySelector('thead')||{}).textContent||'';if(!table&&/Tienda/i.test(txt)&&/Sugerido/i.test(txt))table=t;});if(table){var tb=table.querySelector('tbody');if(tb){tb.innerHTML=storeRows.map(function(x,i){return '<tr><td>'+(i+1)+'</td><td><b>'+x.n+'</b></td><td>'+money(x.s)+'</td><td>'+x.c+'</td><td>'+fmt(x.e)+'</td><td>'+x.o.toFixed(1)+'%</td><td>'+x.d+'</td><td><span class="badge '+x.cls+'">'+x.status+'</span></td></tr>';}).join('');}table.querySelectorAll('th').forEach(function(h){h.textContent=h.textContent.replace(/pares/gi,'pzas');});}var bars=page.querySelector('.bars');if(bars){var mx=storeRows[0].s;bars.innerHTML=storeRows.map(function(x){var pct=Math.max(18,Math.round(x.s/mx*100));return '<div class="bar"><b>'+x.n+'</b><div class="track"><div class="fill" style="width:'+pct+'%"></div></div><span>'+money(x.s)+'</span></div>';}).join('');}page.querySelectorAll('.headrow .link').forEach(function(x){if(/Ver todas/i.test(x.textContent||''))x.textContent='17 tiendas';});}
  function fullComparator(store){if(!store||store==='Compañía')return'Iztapalapa';var i=storeNames.indexOf(store);if(i<0)return'Iztapalapa';return i===0?storeNames[1]:storeNames[i-1];}
  function updateComparator(r){var sel=r.querySelector('#store');var c=fullComparator(sel?sel.value:'Compañía');r.querySelectorAll('.cmp-store').forEach(function(x){x.textContent=c;});}
  function bindComparator(r){if(r.getAttribute('data-v143-bound')==='1')return;r.setAttribute('data-v143-bound','1');r.addEventListener('change',function(e){if(e.target&&e.target.id==='store')setTimeout(function(){updateComparator(r);},0);});r.addEventListener('click',function(e){if(e.target&&e.target.closest&&e.target.closest('#query'))setTimeout(function(){updateComparator(r);},0);});}
  function patch(){var sh=hostShadow(),r=root();if(!sh||!r)return false;ensureStyle(sh);ensureStoreOptions(r);patchStores(r);bindComparator(r);updateComparator(r);return true;}
  function attempt(n){if(patch())return;if(n>0)setTimeout(function(){attempt(n-1);},260);}
  document.addEventListener('click',function(e){var m=e.target&&e.target.closest?e.target.closest('[data-main]'):null;if(m){var v=m.getAttribute('data-main');if(v==='analysis'||v==='commercial')setTimeout(function(){attempt(16);},180);}},true);
  setTimeout(function(){attempt(20);},300);
  console.info('[V143] Comercial móvil reacomodado: 2 columnas + tablas con scroll + 17 tiendas.');
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
                'X-Operations-UI-Version': 'V143-COMMERCIAL-MOBILE-EXACT',
            })
        except Exception as exc:
            print(f'[V143] HTML warning: {type(exc).__name__}: {exc}', flush=True)
            return response

    m._V142_COMMERCIAL_MOBILE_FIT = True
    print('[V143] Comercial móvil exacto instalado: 2 columnas, scroll local y 17 tiendas.', flush=True)
