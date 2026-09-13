"""V146 · Comparativo explícito en Macro para Modelos lentos y Sugerido 0.

Garantiza que ambas tablas, ya ubicadas en Macro compañía, muestren de forma
visible el nombre de la tienda comparativa y el sugerido del mismo modelo en esa
tienda. Conserva la regla: Top 1 compara con Top 2; desde Top 2 hacia abajo se
compara contra la tienda inmediata superior. Sólo afecta el demo visual.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V146_COMMERCIAL_COMPARISON_COLUMNS", False):
        return

    js = r'''<script id="v146-commercial-comparison-columns-js">
(function(){
  const RANK=['Iztapalapa','Vallejo','Ecatepec','Toluca','Arco Norte','Ixtapaluca','Querétaro','Centro','Puebla','Olivar','León','Puebla Sur','Aguascalientes','Veracruz','Naucalpan','Miravalle','Atemajac'];
  const NAMES=['Blusa básica','Vestido floral','Playera estampada','Pantalón wide leg','Falda midi','Chamarra ligera','Conjunto tejido','Sudadera'];
  function sh(){const h=document.getElementById('v141CommercialHost');return h&&h.shadowRoot?h.shadowRoot:null}
  function root(){const s=sh();return s?s.getElementById('v139-demo-root'):null}
  function baseStore(r){const s=r&&r.querySelector('#store');const v=s?s.value:'Compañía';return v==='Compañía'?'Iztapalapa':v}
  function compareStore(store){let i=RANK.indexOf(store);if(i<0)i=0;return i===0?RANK[1]:RANK[i-1]}
  function card(r,id,title){
    let c=r.querySelector(id);if(c)return c;
    const macro=r.querySelector('#page-macro');if(!macro)return null;
    const cards=Array.from(macro.querySelectorAll('.card'));
    c=cards.find(x=>((x.textContent||'').toLowerCase().indexOf(title.toLowerCase())>=0));
    return c||null;
  }
  function slowRows(base,comp){
    const locs=['Mesa 14','Pasillo 7','RC 03','Ropa Colgada','Mesa 22'];
    const dates=['18/07/26','29/06/26','05/07/26','02/08/26','10/08/26'];
    const sugg=[48,36,42,60,24];
    return sugg.map((s,i)=>{
      const cs=Math.round(s*(1.25+i*.08));
      return `<tr><td>PS-${4312+i*317}</td><td>${NAMES[(i+2)%NAMES.length]}</td><td>${['Dama','Caballero','Infantil','Dama','Caballero'][i]}</td><td>${locs[i]}</td><td>${dates[i]}</td><td>${s}</td><td><b>${comp}</b></td><td><b>${cs}</b></td><td>${['02/07/26','15/07/26','28/06/26','19/07/26','25/07/26'][i]}</td><td>✅</td><td>${i%2?'✅':'❌'}</td><td>${i===2?'✅':'❌'}</td><td>${i%3?'✅':'❌'}</td></tr>`;
    }).join('');
  }
  function zeroRows(base,comp){
    const dates=['01/09/26','28/08/26','22/08/26','19/08/26','15/08/26'];
    const cs=[12,8,6,10,7];
    return cs.map((s,i)=>`<tr><td>PS-${7001+i*409}</td><td>${NAMES[(i+4)%NAMES.length]}</td><td>${['Dama','Dama','Infantil','Caballero','Dama'][i]}</td><td>${[120,86,64,53,42][i]}</td><td>${dates[i]}</td><td>0</td><td><b>${comp}</b></td><td><b>${s}</b></td><td>${['03/09/26','30/08/26','25/08/26','21/08/26','18/08/26'][i]}</td><td>${['Próximo a salir','Descontinuado','Impulso','Descontinuado','Próximo a salir'][i]}</td></tr>`).join('');
  }
  function render(){
    const r=root();if(!r)return false;
    const macro=r.querySelector('#page-macro');if(!macro)return false;
    const base=baseStore(r),comp=compareStore(base),rule=base===RANK[0]?'Top 1 → compara con Top 2':'Compara con la tienda inmediata superior';
    let slow=card(r,'#v145-macro-slow','modelos lentos')||r.querySelector('#v144-slow-card');
    let zero=card(r,'#v145-macro-zero','sugerido 0')||r.querySelector('#v144-zero-card');
    if(slow){
      slow.id='v146-macro-slow';
      slow.innerHTML=`<div class="headrow"><div><div class="section-title" style="font-size:14px">Modelos lentos</div><div class="section-sub">Sólo Mesa / Pasillo / RC / Ropa Colgada · última entrada mayor a 30 días</div></div><span class="link">Comparativo automático</span></div><div class="v146-rule"><b>Tienda consultada:</b> ${base} · <b>Tienda comparativa:</b> ${comp} · ${rule}</div><div class="tablewrap"><table class="table wide v146-table"><thead><tr><th>ID</th><th>Modelo</th><th>Sección</th><th>Ubicación</th><th>Últ. entrada</th><th>Sugerido tienda consultada (pzas)</th><th>Tienda comparativa</th><th>Sugerido tienda comparativa (pzas)</th><th>Últ. entrada comparativa</th><th>Está en ubicación</th><th>Cenefa correcta</th><th>Todas las tallas</th><th>Exhibido</th></tr></thead><tbody>${slowRows(base,comp)}</tbody></table></div>`;
    }
    if(zero){
      zero.id='v146-macro-zero';
      zero.innerHTML=`<div class="headrow"><div><div class="section-title" style="font-size:14px">Sugerido 0</div><div class="section-sub">Última entrada dentro de los últimos 30 días · no se repiten en Modelos lentos</div></div><span class="link">Comparativo automático</span></div><div class="v146-rule"><b>Tienda consultada:</b> ${base} · <b>Tienda comparativa:</b> ${comp} · ${rule}</div><div class="tablewrap"><table class="table wide v146-table"><thead><tr><th>ID</th><th>Modelo</th><th>Sección</th><th>Existencia</th><th>Últ. entrada</th><th>Sugerido tienda consultada</th><th>Tienda comparativa</th><th>Sugerido tienda comparativa (pzas)</th><th>Últ. entrada comparativa</th><th>Estatus catálogo</th></tr></thead><tbody>${zeroRows(base,comp)}</tbody></table></div>`;
    }
    const s=sh();if(s&&!s.getElementById('v146-style')){const st=document.createElement('style');st.id='v146-style';st.textContent=`.v146-rule{font-size:8px;color:#365d9f;background:#f4f8ff;border:1px solid #d7e6f7;border-radius:7px;padding:6px 8px;margin:6px 0}.v146-table{min-width:1180px!important}.v146-table th:nth-child(7),.v146-table td:nth-child(7),.v146-table th:nth-child(8),.v146-table td:nth-child(8){background:#eef7ff;font-weight:800}@media(max-width:430px){.v146-table{font-size:8px!important}.v146-table th,.v146-table td{padding:6px 5px!important}}`;s.appendChild(st)}
    return true;
  }
  function retry(n){if(render())return;if(n>0)setTimeout(()=>retry(n-1),250)}
  setTimeout(()=>retry(28),300);
  document.addEventListener('change',e=>{if(e.target&&e.target.id==='store')setTimeout(()=>retry(12),100)},true);
  document.addEventListener('click',e=>{const t=e.target&&e.target.closest?e.target.closest('#query,.tab,[data-main]'):null;if(t)setTimeout(()=>retry(12),160)},true);
  console.info('[V146] Comparativo explícito: tienda y sugerido comparado instalados.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v146_html(request, call_next):
        response=await call_next(request)
        if request.url.path!='/' or getattr(response,'status_code',200)!=200:
            return response
        try:
            body=b''
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode('utf-8',errors='replace')
            if 'v146-commercial-comparison-columns-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            return HTMLResponse(html,status_code=response.status_code,headers={'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache','Expires':'0','X-Operations-UI-Version':'V146-COMMERCIAL-COMPARISON-COLUMNS'})
        except Exception as exc:
            print(f'[V146] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V146_COMMERCIAL_COMPARISON_COLUMNS=True
    print('[V146] Tienda comparativa y sugerido comparado visibles en Macro.',flush=True)
