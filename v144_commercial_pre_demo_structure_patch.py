"""V144 · Ajusta el demo Comercial a la estructura pre-demo.

- Sugerido se presenta en piezas, no en pesos.
- Macro 80/20 usa filtros por nivel y una tabla fija con 80 modelos desplazables
  verticalmente dentro de la propia tabla.
- Modelos lentos y Sugerido 0 comparan contra la tienda inmediata superior del
  ranking; sólo el primer lugar compara contra el segundo.
- Modelos lentos conservan únicamente ubicaciones operativas válidas y entradas
  mayores a 30 días; Sugerido 0 usa entradas de los últimos 30 días.
Sólo afecta el demo visual del propietario; no modifica datos reales.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V144_COMMERCIAL_PRE_DEMO_STRUCTURE", False):
        return

    js = r'''<script id="v144-commercial-pre-demo-structure-js">
(function(){
  const RANK=[
    'Iztapalapa','Vallejo','Ecatepec','Toluca','Arco Norte','Ixtapaluca',
    'Querétaro','Centro','Puebla','Olivar','León','Puebla Sur',
    'Aguascalientes','Veracruz','Naucalpan','Miravalle','Atemajac'
  ];
  const NAMES=['Blusa básica','Vestido floral','Playera estampada','Pantalón wide leg','Falda midi','Chamarra ligera','Conjunto tejido','Sudadera','Jeans skinny','Blusa satinada','Pantalón recto','Vestido camisero','Playera básica','Conjunto casual','Blusa manga larga','Pantalón cargo','Falda plisada','Chamarra denim','Vestido midi','Playera cuello V'];
  const COLORS=['Negro','Blanco','Azul','Rosa','Beige','Verde','Gris','Vino','Café','Marino'];
  const LEVELS={
    'Sección':['Todas','Dama','Caballero','Infantil','Lencería'],
    'Área':['Todas','Colgado','Doblado','Jeans','Lencería'],
    'Tipo catálogo':['Todas','Vigente','Descontinuado','Próximo a salir','Impulso'],
    'Macro':['Todas','Piso','Bodega']
  };
  function sh(){const h=document.getElementById('v141CommercialHost');return h&&h.shadowRoot?h.shadowRoot:null}
  function root(){const s=sh();return s?s.getElementById('v139-demo-root'):null}
  function fmt(n){return Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0})}
  function selectedStore(r){const s=r&&r.querySelector('#store');return s?s.value:'Compañía'}
  function baseStore(r){const s=selectedStore(r);return s==='Compañía'?'Iztapalapa':s}
  function compareStore(store){let i=RANK.indexOf(store);if(i<0)i=0;return i===0?RANK[1]:RANK[i-1]}
  function cardByTitle(page,re){if(!page)return null;return Array.from(page.querySelectorAll('.card')).find(c=>re.test(((c.querySelector('.section-title')||{}).textContent||'')+' '+(c.textContent||'')))||null}
  function normalizeSuggested(r){
    if(!r)return;
    r.querySelectorAll('.kpi').forEach(k=>{const lab=k.querySelector('.label');if(lab&&/sugerido/i.test(lab.textContent||'')){const v=k.querySelector('.value');const u=k.querySelector('.unit');if(v)v.textContent=(v.textContent||'').replace(/\$/g,'');if(u)u.textContent='pzas';}});
    r.querySelectorAll('.mini').forEach(k=>{const lab=k.querySelector('.label');if(lab&&/sugerido/i.test(lab.textContent||'')){const v=k.querySelector('.value');if(v)v.textContent=(v.textContent||'').replace(/\$/g,'');}});
    r.querySelectorAll('.macrosec').forEach(k=>{const b=k.querySelector('.big');if(b)b.textContent=(b.textContent||'').replace(/\$/g,'');});
    r.querySelectorAll('table').forEach(t=>{
      const ths=Array.from(t.querySelectorAll('thead th'));
      ths.forEach((th,idx)=>{if(/sugerido/i.test(th.textContent||'')){th.textContent=(th.textContent||'').replace(/MXN/gi,'pzas');Array.from(t.querySelectorAll('tbody tr')).forEach(tr=>{const td=tr.children[idx];if(td)td.textContent=(td.textContent||'').replace(/\$/g,'');});}});
    });
    const stores=r.querySelector('#page-stores');
    if(stores){const sub=Array.from(stores.querySelectorAll('.section-sub')).find(x=>/Sugerido por tienda/i.test(x.textContent||''));if(sub)sub.textContent='Sugerido por tienda (pzas)';stores.querySelectorAll('.bars .bar span').forEach(x=>x.textContent=(x.textContent||'').replace(/\$/g,''));}
  }
  function rows80(level,filter){
    let out='';let total=0;
    for(let i=0;i<80;i++){
      const sug=Math.max(22,980-i*9+(i%7)*5);const venta=Math.max(8,Math.round(sug*(0.94-i*0.006)));const part=Math.max(.4,4.8-i*.045);total+=part;
      const id=String(104000+i*17);const model=NAMES[i%NAMES.length];const color=COLORS[i%COLORS.length];
      out+='<tr><td>'+(i+1)+'</td><td>'+id+'</td><td>'+model+'</td><td>'+color+'</td><td>'+fmt(sug)+'</td><td>'+fmt(venta)+'</td><td>'+part.toFixed(1)+'%</td><td>'+Math.min(100,total).toFixed(1)+'%</td><td><span class="v144-8020-badge">80</span></td></tr>';
    }
    return out;
  }
  function render8020(r){
    const page=r.querySelector('#page-macro');if(!page)return;
    const old=cardByTitle(page,/Macro\s*80\/20/i);if(!old)return;
    old.id='v144-8020-card';
    old.innerHTML=`<div class="headrow"><div><div class="section-title" style="font-size:14px">Macro 80/20</div><div class="section-sub">Top 80 modelos por el nivel seleccionado · Sugerido en piezas</div></div><span class="link">80 modelos</span></div>
      <div class="v144-levels" id="v144Levels"></div><div class="v144-subs" id="v144Subs"></div>
      <div class="v144-fixed-table"><table class="table wide v144-8020-table"><thead><tr><th>#</th><th>ID</th><th>Modelo</th><th>Color</th><th>Sugerido pzas</th><th>Venta pzas</th><th>% Part. venta</th><th>% Acum.</th><th>80/20</th></tr></thead><tbody id="v144Rows80"></tbody></table></div>
      <div class="footnote">Tabla fija: desplázate verticalmente dentro de la tabla para consultar los 80 modelos.</div>`;
    const levels=old.querySelector('#v144Levels'),subs=old.querySelector('#v144Subs'),tbody=old.querySelector('#v144Rows80');let current='Sección',sub='Todas';
    function paintLevels(){levels.innerHTML=Object.keys(LEVELS).map(x=>'<button type="button" class="filterbtn '+(x===current?'active':'')+'" data-lvl="'+x+'">'+x+'</button>').join('');}
    function paintSubs(){subs.innerHTML=LEVELS[current].map(x=>'<button type="button" class="filterbtn '+(x===sub?'active':'')+'" data-sub="'+x+'">'+x+'</button>').join('');tbody.innerHTML=rows80(current,sub);}
    levels.addEventListener('click',e=>{const b=e.target.closest('[data-lvl]');if(!b)return;current=b.dataset.lvl;sub='Todas';paintLevels();paintSubs();});
    subs.addEventListener('click',e=>{const b=e.target.closest('[data-sub]');if(!b)return;sub=b.dataset.sub;paintSubs();});
    paintLevels();paintSubs();
  }
  function slowRows(r){const base=baseStore(r),comp=compareStore(base);const locs=['Mesa 14','Pasillo 7','RC 03','Ropa Colgada','Mesa 22'];const dates=['18/07/26','29/06/26','05/07/26','02/08/26','10/08/26'];let out='';for(let i=0;i<5;i++){const sug=[48,36,42,60,24][i],cs=Math.round(sug*(1.25+i*.08));out+='<tr><td>PS-'+(4312+i*317)+'</td><td>'+NAMES[(i+3)%NAMES.length]+'</td><td>'+['Dama','Caballero','Infantil','Dama','Caballero'][i]+'</td><td>'+locs[i]+'</td><td>'+dates[i]+'</td><td>'+sug+'</td><td>'+comp+'</td><td>'+cs+'</td><td>'+['02/07/26','15/07/26','28/06/26','19/07/26','25/07/26'][i]+'</td><td>✅</td><td>'+(i%2?'✅':'❌')+'</td><td>'+(i===2?'✅':'❌')+'</td><td>'+(i%3?'✅':'❌')+'</td></tr>';}return out}
  function zeroRows(r){const base=baseStore(r),comp=compareStore(base);const dates=['01/09/26','28/08/26','22/08/26','19/08/26','15/08/26'];let out='';for(let i=0;i<5;i++){const cs=[12,8,6,10,7][i];out+='<tr><td>PS-'+(7001+i*409)+'</td><td>'+NAMES[(i+8)%NAMES.length]+'</td><td>'+['Dama','Dama','Infantil','Caballero','Dama'][i]+'</td><td>'+[120,86,64,53,42][i]+'</td><td>'+dates[i]+'</td><td>0</td><td>'+comp+'</td><td>'+cs+'</td><td>'+['03/09/26','30/08/26','25/08/26','21/08/26','18/08/26'][i]+'</td><td>'+['Próximo a salir','Descontinuado','Impulso','Descontinuado','Próximo a salir'][i]+'</td></tr>';}return out}
  function renderComparisons(r){
    const page=r.querySelector('#page-more');if(!page)return;
    const slow=cardByTitle(page,/Modelos lentos/i);if(slow){slow.id='v144-slow-card';slow.innerHTML=`<div class="headrow"><div><div class="section-title" style="font-size:14px">Modelos lentos</div><div class="section-sub">Sólo Mesa / Pasillo / RC / Ropa Colgada · última entrada mayor a 30 días</div></div><span class="link">Comparativo automático</span></div><div class="footnote v144-rule"></div><div class="tablewrap"><table class="table wide"><thead><tr><th>ID</th><th>Modelo</th><th>Sección</th><th>Ubicación</th><th>Últ. entrada</th><th>Sugerido pzas</th><th>Tienda comparada</th><th>Sugerido comp. pzas</th><th>Últ. entrada comp.</th><th>Está en ubicación</th><th>Cenefa correcta</th><th>Todas las tallas</th><th>Exhibido</th></tr></thead><tbody>${slowRows(r)}</tbody></table></div>`;}
    const zero=cardByTitle(page,/Sugerido\s*0/i);if(zero){zero.id='v144-zero-card';zero.innerHTML=`<div class="headrow"><div><div class="section-title" style="font-size:14px">Sugerido 0</div><div class="section-sub">Última entrada dentro de los últimos 30 días · no se repiten en Modelos lentos</div></div><span class="link">Comparativo automático</span></div><div class="footnote v144-rule"></div><div class="tablewrap"><table class="table wide"><thead><tr><th>ID</th><th>Modelo</th><th>Sección</th><th>Existencia</th><th>Últ. entrada</th><th>Sugerido</th><th>Tienda comparada</th><th>Sugerido comp. pzas</th><th>Últ. entrada comp.</th><th>Estatus catálogo</th></tr></thead><tbody>${zeroRows(r)}</tbody></table></div>`;}
    const base=baseStore(r),comp=compareStore(base);page.querySelectorAll('.v144-rule').forEach(x=>x.textContent='Tienda base: '+base+' · Comparación: '+comp+(base===RANK[0]?' (Top 1 compara hacia abajo con Top 2)':' (compara con la tienda inmediata superior)'));
  }
  function css(s){if(s.getElementById('v144-style'))return;const st=document.createElement('style');st.id='v144-style';st.textContent=`
    #v144-8020-card .v144-levels,#v144-8020-card .v144-subs{display:flex;gap:5px;overflow-x:auto;padding:5px 0;scrollbar-width:none}#v144-8020-card .v144-levels::-webkit-scrollbar,#v144-8020-card .v144-subs::-webkit-scrollbar{display:none}
    #v144-8020-card .filterbtn{flex:0 0 auto;height:31px;padding:0 10px;font-size:7.5px}
    .v144-fixed-table{height:330px;overflow-y:auto;overflow-x:auto;border:1px solid #dce6f2;border-radius:8px;-webkit-overflow-scrolling:touch}.v144-fixed-table thead th{position:sticky;top:0;z-index:3;background:#f2f7fc}.v144-8020-table{min-width:780px!important}.v144-8020-badge{display:inline-block;background:#e3f8eb;color:#078946;border-radius:999px;padding:2px 6px;font-weight:900}
    #v144-slow-card .table,#v144-zero-card .table{min-width:1050px!important}.v144-rule{font-weight:700;color:#3c61a2;background:#f5f9ff;border-radius:7px;margin:6px 0;padding:6px 8px}
    @media(max-width:430px){.v144-fixed-table{height:315px}.v144-8020-table{font-size:8px!important}.v144-8020-table th,.v144-8020-table td{padding:6px 5px!important}#v144-slow-card .table,#v144-zero-card .table{font-size:8px!important}}
  `;s.appendChild(st)}
  function apply(){const s=sh(),r=root();if(!s||!r)return false;css(s);normalizeSuggested(r);render8020(r);renderComparisons(r);r.setAttribute('data-v144','1');return true}
  function refreshComparisons(){const r=root();if(!r)return;renderComparisons(r);normalizeSuggested(r)}
  function retry(n){if(apply())return;if(n>0)setTimeout(()=>retry(n-1),250)}
  document.addEventListener('click',e=>{const m=e.target&&e.target.closest?e.target.closest('[data-main]'):null;if(m&&['analysis','commercial'].includes(m.getAttribute('data-main')))setTimeout(()=>retry(16),200)},true);
  setInterval(()=>{const r=root();if(r&&r.getAttribute('data-v144')!=='1')apply()},900);
  setTimeout(()=>retry(20),350);
  setTimeout(()=>{const r=root();if(r){const sel=r.querySelector('#store'),q=r.querySelector('#query');if(sel)sel.addEventListener('change',()=>setTimeout(refreshComparisons,0));if(q)q.addEventListener('click',()=>setTimeout(refreshComparisons,0));}},1800);
  console.info('[V144] Estructura pre-demo Comercial: 80/20 + comparativos instalada.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v144_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v144-commercial-pre-demo-structure-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V144-COMMERCIAL-PRE-DEMO-STRUCTURE",
            })
        except Exception as exc:
            print(f"[V144] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V144_COMMERCIAL_PRE_DEMO_STRUCTURE = True
    print("[V144] Comercial pre-demo: 80 modelos fijos + comparador superior instalado.", flush=True)
