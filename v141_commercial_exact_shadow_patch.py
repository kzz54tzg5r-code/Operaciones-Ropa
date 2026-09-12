"""V141 · Monta el demo Comercial exacto a los bocetos aprobados.

Usa el HTML de v139_commercial_mockup_parity_patch.py como fuente visual y lo
monta en Shadow DOM directamente dentro de la app, sin iframe. De esta forma no
interfiere con los estilos/eventos históricos del dashboard y conserva Safari
iPhone estable. Mantiene filtros, 7 pestañas y reglas de modelos. Sólo demo.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V141_COMMERCIAL_EXACT_SHADOW", False):
        return

    css = r'''<style id="v141-commercial-exact-css">
#v141CommercialHost{display:none}
body.v141-commercial-exact #v139CommercialHost{display:none!important}
body.v141-commercial-exact #v133CommercialDemoHost{display:none!important}
body.v141-commercial-exact #analysisNav,body.v141-commercial-exact #globalFilters,body.v141-commercial-exact #v103FilterShell,body.v141-commercial-exact #v103ClassicBack{display:none!important}
body.v141-commercial-exact main.main>section.page{display:none!important}
body.v141-commercial-exact #v141CommercialHost{display:block!important;width:100%!important;position:relative!important;z-index:2147483647!important;margin:8px 0 14px!important;overflow:visible!important}
body.v141-commercial-exact #heroTitle{position:relative!important;padding-right:92px!important}
#v141HeroBrand{position:absolute;right:2px;top:-2px;display:flex;align-items:center;gap:8px;color:#fff;font-size:13px;line-height:.82;font-weight:950;text-align:center}
#v141HeroBrand .bars{display:flex;align-items:flex-end;gap:3px;height:28px;opacity:.42}#v141HeroBrand .bars i{display:block;width:6px;border-radius:4px;background:#fff}#v141HeroBrand .bars i:nth-child(1){height:12px}#v141HeroBrand .bars i:nth-child(2){height:20px}#v141HeroBrand .bars i:nth-child(3){height:28px}
@media(max-width:430px){body.v141-commercial-exact #heroTitle{padding-right:82px!important}#v141HeroBrand{font-size:11px}}
</style>'''

    js = r'''<script id="v141-commercial-exact-js">
(function(){
  var loaded=false,loading=false,lastCommercial=false;
  function owner(){return typeof USER!=='undefined'&&USER&&((USER.role==='superadmin')||(USER.real_role==='superadmin')||(USER.can_preview_roles===true));}
  function isCommercial(){var a=document.querySelector('[data-main="analysis"].active,[data-main="commercial"].active');var h=(document.getElementById('heroTitle')||{}).textContent||'';return !!a||/Análisis Comercial/i.test(h);}
  function ensureHost(){var h=document.getElementById('v141CommercialHost');if(h)return h;var main=document.querySelector('main.main');if(!main)return null;h=document.createElement('div');h.id='v141CommercialHost';main.appendChild(h);return h;}
  function brand(){var t=document.getElementById('heroTitle');if(t&&!document.getElementById('v141HeroBrand')){t.innerHTML='Análisis Comercial <span style="display:inline-flex;margin-left:5px;padding:2px 7px;border-radius:999px;background:#bff3ff;color:#075a7b;font-size:9px;font-weight:950;vertical-align:middle">DEMO</span><span id="v141HeroBrand"><span>Price<br>Shoes</span><span class="bars"><i></i><i></i><i></i></span></span>';}var s=document.getElementById('heroSub');if(s)s.textContent='Información comercial para una mejor toma de decisiones';}
  function patchClothing(root){
    if(!root)return;
    var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);var n;while(n=walker.nextNode()){if(/\bpares\b/i.test(n.nodeValue||''))n.nodeValue=(n.nodeValue||'').replace(/pares/gi,'pzas');}
    var macro=root.querySelector('#page-macro');if(macro){var tables=macro.querySelectorAll('table');for(var i=0;i<tables.length;i++){var th=(tables[i].querySelector('th')||{}).textContent||'';if(th.trim()==='Sección'){var tb=tables[i].querySelector('tbody');if(tb)tb.innerHTML='<tr><td>Dama</td><td>A</td><td>612,340</td><td>1,012,300</td><td>68</td><td><span class="badge">86.2%</span></td></tr><tr><td>Caballero</td><td>B</td><td>452,610</td><td>762,800</td><td>72</td><td><span class="badge">79.4%</span></td></tr><tr><td>Infantil</td><td>A</td><td>218,500</td><td>371,220</td><td>60</td><td><span class="badge">88.7%</span></td></tr><tr><td>Lencería</td><td>C</td><td>98,420</td><td>214,110</td><td>55</td><td><span class="badge">76.8%</span></td></tr>';break;}}}
  }
  function bind(sh){
    var root=sh.getElementById('v139-demo-root');if(!root)return;
    var periods={'Sep 2026':1,'Ago 2026':.94,'Jul 2026':.88};var stores={'Compañía':1,'Iztapalapa':1,'Vallejo':.97,'Ecatepec':.80,'Toluca':.74,'Arco Norte':.69,'Ixtapaluca':.72,'Querétaro':.79,'Centro':.76,'Olivar':.66,'León':.61,'Puebla':.66,'Puebla Sur':.58,'Aguascalientes':.56,'Veracruz':.54,'Naucalpan':.63,'Miravalle':.51,'Atemajac':.53};var sections={'Todas':1,'Dama':.47,'Caballero':.35,'Infantil':.18,'Lencería':.10};var rank=['Iztapalapa','Vallejo','Ecatepec','Querétaro','Puebla','León'];
    function fmt(x){return Math.round(x).toLocaleString('es-MX')}function money(x){return '$'+fmt(x)}function comparator(store){if(store==='Compañía')return'Iztapalapa';var i=rank.indexOf(store);if(i<0)return'Iztapalapa';return i===0?rank[1]:rank[i-1]}
    function show(name){root.querySelectorAll('.page').forEach(function(p){p.classList.toggle('active',p.id==='page-'+name)});root.querySelectorAll('.tab').forEach(function(b){b.classList.toggle('active',b.getAttribute('data-page')===name)});}
    root.querySelectorAll('.tab').forEach(function(b){b.addEventListener('click',function(){show(b.getAttribute('data-page'))})});
    root.querySelectorAll('[data-acc]').forEach(function(card){var btn=card.querySelector('.acc-toggle');if(btn)btn.addEventListener('click',function(){card.classList.toggle('open')})});
    root.querySelectorAll('#sectionButtons .filterbtn').forEach(function(b){b.addEventListener('click',function(){root.querySelectorAll('#sectionButtons .filterbtn').forEach(function(x){x.classList.remove('active')});b.classList.add('active');var title=root.querySelector('#sectionTitle');if(title)title.textContent=b.getAttribute('data-sec');var sel=root.querySelector('#section');if(sel)sel.value=b.getAttribute('data-sec')==='Todas'?'Todas':b.getAttribute('data-sec');apply()})});
    root.querySelectorAll('#page-areas .filters-inline').forEach(function(group){group.querySelectorAll('.filterbtn').forEach(function(b){b.addEventListener('click',function(){group.querySelectorAll('.filterbtn').forEach(function(x){x.classList.remove('active')});b.classList.add('active')})})});
    function apply(){var p=root.querySelector('#period').value,s=root.querySelector('#store').value,c=root.querySelector('#section').value;root.querySelectorAll('.ctx-period').forEach(function(x){x.textContent=p});var f=(periods[p]||1)*(stores[s]||1)*(sections[c]||1);root.querySelectorAll('.dyn').forEach(function(x){var v=Number(x.getAttribute('data-base')||0)*f;x.textContent=x.getAttribute('data-kind')==='money'?money(v):fmt(v)});root.querySelectorAll('.cmp-store').forEach(function(x){x.textContent=comparator(s)})}
    var q=root.querySelector('#query');if(q)q.addEventListener('click',apply);['period','store','section'].forEach(function(id){var x=root.querySelector('#'+id);if(x)x.addEventListener('change',apply)});
    show('macro');apply();
  }
  async function load(){
    if(loading||loaded||!owner()||!isCommercial())return;loading=true;var host=ensureHost();if(!host){loading=false;return;}
    try{
      var r=await fetch('/commercial-demo-v139?v=141&ts='+Date.now(),{cache:'no-store',credentials:'same-origin'});if(!r.ok)throw new Error('HTTP '+r.status);var html=await r.text();if(!html||html.length<1000)throw new Error('HTML incompleto');
      var doc=new DOMParser().parseFromString(html,'text/html');var source=doc.getElementById('v139-demo-root');var style=doc.querySelector('style');if(!source||!style)throw new Error('Fuente visual incompleta');
      var sh=host.shadowRoot||host.attachShadow({mode:'open'});sh.innerHTML='<style>:host{display:block;width:100%;background:#f4f8fd;color:#0a3193;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}'+style.textContent+'</style>'+source.outerHTML;
      patchClothing(sh);bind(sh);loaded=true;loading=false;brand();
    }catch(err){loading=false;host.innerHTML='<div style="padding:18px;border:1px solid #f1c9ce;border-radius:10px;background:#fff5f6;color:#9f2030;font:700 12px system-ui">No fue posible cargar el demo Comercial exacto: '+String(err&&err.message||err)+'</div>';}
  }
  function activate(){if(!owner())return;document.body.classList.add('v141-commercial-exact');brand();load();}
  function deactivate(){document.body.classList.remove('v141-commercial-exact');}
  function tick(){var c=owner()&&isCommercial();if(c){activate();}else if(lastCommercial){deactivate();}lastCommercial=c;}
  setInterval(tick,550);setTimeout(tick,120);setTimeout(tick,700);
  console.info('[V141] Comercial exacto a bocetos montado en Shadow DOM.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v141_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v141-commercial-exact-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V141-COMMERCIAL-MOCKUP-EXACT",
            })
        except Exception as exc:
            print(f"[V141] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V141_COMMERCIAL_EXACT_SHADOW = True
    print("[V141] Comercial exacto a bocetos instalado: Shadow DOM + 7 pestañas.", flush=True)
