"""V147 · Participación de tienda en Macro 80/20 del demo Comercial.

Cuando el filtro Tienda está en Compañía, la tabla 80/20 permanece igual.
Cuando se selecciona una tienda:
- muestra arriba a la derecha una regla de participación en rosa/rojo;
- calcula participación tienda = Σ Sugerido tienda / Σ Sugerido compañía;
- en cada ID muestra la participación de venta de esa tienda contra la venta
  compañía del mismo modelo (Venta tienda / Venta compañía del ID).
Sólo afecta el demo visual; no modifica datos reales.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V147_COMMERCIAL_8020_STORE_PARTICIPATION", False):
        return

    js = r'''<script id="v147-commercial-8020-store-participation-js">
(function(){
  const STORE_SHARE={
    'Iztapalapa':0.132,'Vallejo':0.118,'Ecatepec':0.106,'Toluca':0.094,
    'Arco Norte':0.089,'Ixtapaluca':0.083,'Querétaro':0.081,'Centro':0.076,
    'Puebla':0.073,'Olivar':0.069,'León':0.064,'Puebla Sur':0.059,
    'Aguascalientes':0.055,'Veracruz':0.051,'Naucalpan':0.049,
    'Miravalle':0.043,'Atemajac':0.039
  };
  function sh(){const h=document.getElementById('v141CommercialHost');return h&&h.shadowRoot?h.shadowRoot:null}
  function root(){const s=sh();return s?s.getElementById('v139-demo-root'):null}
  function num(txt){return Number(String(txt||'').replace(/[^0-9.-]/g,''))||0}
  function fmt(n){return Math.round(Number(n||0)).toLocaleString('es-MX',{maximumFractionDigits:0})}
  function storeName(r){const s=r&&r.querySelector('#store');return s?s.value:'Compañía'}
  function variation(i,kind){
    const a=kind==='sale'?17:11;
    const b=kind==='sale'?0.08:0.05;
    return 0.82+(((i*a+7)%7)*b);
  }
  function addCss(s){
    if(s.getElementById('v147-style'))return;
    const st=document.createElement('style');st.id='v147-style';st.textContent=`
      #v147-store-rule{margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:2px;background:#ffe7ee;border:1px solid #ffb6c7;color:#c51643;border-radius:10px;padding:6px 9px;line-height:1.05;min-width:150px}
      #v147-store-rule b{font-size:9px;color:#b80f38}#v147-store-rule strong{font-size:15px;color:#d30d43}#v147-store-rule small{font-size:7px;color:#9c3a55;text-align:right}
      #v144-8020-card .v147-part-head,#v144-8020-card .v147-part-cell{background:#fff0f4;color:#be1740;font-weight:900;text-align:center}
      #v144-8020-card .v147-part-pill{display:inline-block;min-width:48px;padding:3px 6px;border-radius:999px;background:#ffe1e9;color:#c31540;font-weight:950;text-align:center}
      @media(max-width:430px){#v147-store-rule{min-width:132px;padding:5px 7px}#v147-store-rule strong{font-size:13px}#v147-store-rule b{font-size:8px}#v147-store-rule small{font-size:6.5px}}
    `;s.appendChild(st);
  }
  function ensureCompanyData(tr){
    if(!tr || tr.children.length<6)return;
    if(!tr.dataset.v147CompanySug)tr.dataset.v147CompanySug=String(num(tr.children[4].textContent));
    if(!tr.dataset.v147CompanySale)tr.dataset.v147CompanySale=String(num(tr.children[5].textContent));
  }
  function removePartColumn(table){
    if(!table)return;
    table.querySelectorAll('.v147-part-head,.v147-part-cell').forEach(x=>x.remove());
  }
  function restoreCompany(card,table){
    const rule=card.querySelector('#v147-store-rule');if(rule)rule.remove();
    removePartColumn(table);
    const ths=table.querySelectorAll('thead th');
    if(ths[4])ths[4].textContent='Sugerido pzas';
    if(ths[5])ths[5].textContent='Venta pzas';
    table.querySelectorAll('tbody tr').forEach(tr=>{
      ensureCompanyData(tr);
      if(tr.children[4])tr.children[4].textContent=fmt(Number(tr.dataset.v147CompanySug||0));
      if(tr.children[5])tr.children[5].textContent=fmt(Number(tr.dataset.v147CompanySale||0));
    });
  }
  function applyStore(card,table,store){
    removePartColumn(table);
    const rows=Array.from(table.querySelectorAll('tbody tr'));
    if(!rows.length)return;
    const base=STORE_SHARE[store]||0.06;
    let companySugTotal=0,storeSugTotal=0;
    rows.forEach((tr,i)=>{
      ensureCompanyData(tr);
      const cs=Number(tr.dataset.v147CompanySug||0),cv=Number(tr.dataset.v147CompanySale||0);
      companySugTotal+=cs;
      const storeSug=Math.max(0,Math.round(cs*base*variation(i,'sug')));
      const storeSale=Math.max(0,Math.round(cv*base*variation(i,'sale')));
      storeSugTotal+=storeSug;
      if(tr.children[4])tr.children[4].textContent=fmt(storeSug);
      if(tr.children[5])tr.children[5].textContent=fmt(storeSale);
      const pct=cv>0?(storeSale/cv*100):0;
      const td=document.createElement('td');td.className='v147-part-cell';td.innerHTML='<span class="v147-part-pill">'+pct.toFixed(1)+'%</span>';
      tr.insertBefore(td,tr.children[6]||null);
    });
    const ths=table.querySelectorAll('thead th');
    if(ths[4])ths[4].textContent='Sugerido tienda pzas';
    if(ths[5])ths[5].textContent='Venta tienda pzas';
    const th=document.createElement('th');th.className='v147-part-head';th.innerHTML='Part. venta tienda<br>vs. compañía';
    const hr=table.querySelector('thead tr');if(hr)hr.insertBefore(th,hr.children[6]||null);
    const overall=companySugTotal>0?(storeSugTotal/companySugTotal*100):0;
    let rule=card.querySelector('#v147-store-rule');
    if(!rule){
      rule=document.createElement('div');rule.id='v147-store-rule';
      const head=card.querySelector('.headrow');
      if(head)head.appendChild(rule);else card.insertBefore(rule,card.firstChild);
    }
    rule.innerHTML='<b>Regla de venta · '+store+'</b><strong>'+overall.toFixed(1)+'%</strong><small>Σ Sugerido tienda ÷ Σ Sugerido compañía</small>';
  }
  function apply(){
    const s=sh(),r=root();if(!s||!r)return false;addCss(s);
    const card=r.querySelector('#v144-8020-card');if(!card)return false;
    const table=card.querySelector('.v144-8020-table');if(!table)return false;
    const store=storeName(r);
    if(store==='Compañía')restoreCompany(card,table);else applyStore(card,table,store);
    return true;
  }
  function retry(n){if(apply())return;if(n>0)setTimeout(()=>retry(n-1),180)}
  function bind(){
    const r=root();if(!r)return false;
    const sel=r.querySelector('#store'),q=r.querySelector('#query');
    if(sel&&!sel.dataset.v147bound){sel.dataset.v147bound='1';sel.addEventListener('change',()=>setTimeout(()=>retry(8),80));}
    if(q&&!q.dataset.v147bound){q.dataset.v147bound='1';q.addEventListener('click',()=>setTimeout(()=>retry(8),80));}
    const card=r.querySelector('#v144-8020-card');
    if(card&&!card.dataset.v147obs){card.dataset.v147obs='1';let busy=false;new MutationObserver(()=>{if(busy)return;busy=true;setTimeout(()=>{apply();busy=false},40)}).observe(card,{childList:true,subtree:true});}
    return true;
  }
  setInterval(()=>{bind();apply();},1200);
  setTimeout(()=>retry(24),350);
  console.info('[V147] Participación de tienda en Macro 80/20 instalada.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v147_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body += chunk
            html=body.decode("utf-8",errors="replace")
            if "v147-commercial-8020-store-participation-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V147-COMMERCIAL-8020-STORE-PARTICIPATION",
            })
        except Exception as exc:
            print(f"[V147] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V147_COMMERCIAL_8020_STORE_PARTICIPATION=True
    print("[V147] Macro 80/20 con participación de tienda instalado.",flush=True)
