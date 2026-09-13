"""V145 · Mueve Modelos lentos y Sugerido 0 a Macro compañía.

Conserva íntegramente las tablas y reglas instaladas en V144 (comparación contra
la tienda inmediata superior; Top 1 contra Top 2, sugerido de tienda comparada,
reglas de antigüedad y ubicación). Únicamente cambia su ubicación visual dentro
del demo Comercial: ambas quedan en la primera pestaña, Macro compañía.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V145_COMMERCIAL_MACRO_MODELS", False):
        return

    js = r'''<script id="v145-commercial-macro-models-js">
(function(){
  function shadow(){
    var h=document.getElementById('v141CommercialHost');
    return h&&h.shadowRoot?h.shadowRoot:null;
  }
  function root(){
    var sh=shadow();
    return sh?sh.getElementById('v139-demo-root'):null;
  }
  function clean(t){return String(t||'').replace(/\s+/g,' ').trim().toLowerCase();}
  function headingNode(scope, phrase){
    if(!scope)return null;
    var nodes=scope.querySelectorAll('.section-title,.model-title,.headrow b,.headrow strong,h1,h2,h3,h4,b,strong');
    phrase=phrase.toLowerCase();
    for(var i=0;i<nodes.length;i++){
      var tx=clean(nodes[i].textContent);
      if(tx===phrase || tx.indexOf(phrase)===0)return nodes[i];
    }
    return null;
  }
  function topBlock(node, page){
    if(!node)return null;
    var el=node;
    var candidate=null;
    while(el && el!==page){
      if(el.classList && (el.classList.contains('card') || el.classList.contains('modelbox'))){candidate=el;}
      if(el.parentElement===page) return el;
      el=el.parentElement;
    }
    return candidate;
  }
  function styleWrap(el, id){
    if(!el)return null;
    if(el.parentElement && el.parentElement.id===id)return el.parentElement;
    if(el.classList && el.classList.contains('card')){el.id=el.id||id;return el;}
    var wrap=document.createElement('div');
    wrap.className='card'; wrap.id=id;
    el.parentElement.insertBefore(wrap,el); wrap.appendChild(el);
    return wrap;
  }
  function move(){
    var r=root(); if(!r)return false;
    var macro=r.querySelector('#page-macro');
    var more=r.querySelector('#page-more');
    if(!macro||!more)return false;

    var slowHead=headingNode(more,'modelos lentos') || headingNode(r,'modelos lentos');
    var zeroHead=headingNode(more,'sugerido 0') || headingNode(r,'sugerido 0');

    var slow=slowHead?topBlock(slowHead,more):r.querySelector('#v145-macro-slow');
    var zero=zeroHead?topBlock(zeroHead,more):r.querySelector('#v145-macro-zero');

    if(slow && slow!==macro){
      slow=styleWrap(slow,'v145-macro-slow');
      if(slow && slow.parentElement!==macro) macro.appendChild(slow);
    }
    if(zero && zero!==macro){
      zero=styleWrap(zero,'v145-macro-zero');
      if(zero && zero.parentElement!==macro) macro.appendChild(zero);
    }

    // Si V144 creó bloques identificables, muévelos también sin duplicarlos.
    var v144Slow=r.querySelector('[data-v144="slow"],#v144-slow-models');
    var v144Zero=r.querySelector('[data-v144="zero"],#v144-zero-models');
    if(v144Slow && v144Slow.parentElement!==macro) macro.appendChild(v144Slow);
    if(v144Zero && v144Zero.parentElement!==macro) macro.appendChild(v144Zero);

    // Añade una separación visual clara al final de Macro.
    [r.querySelector('#v145-macro-slow'),r.querySelector('#v145-macro-zero')].forEach(function(x){
      if(x){x.style.marginTop='7px';x.style.minWidth='0';}
    });
    return true;
  }
  function retry(n){if(move())return;if(n>0)setTimeout(function(){retry(n-1);},250);}
  document.addEventListener('click',function(e){
    var t=e.target&&e.target.closest?e.target.closest('[data-main],.tab,#query'):null;
    if(t)setTimeout(function(){retry(12);},120);
  },true);
  document.addEventListener('change',function(){setTimeout(function(){retry(10);},120);},true);
  setTimeout(function(){retry(24);},250);
  console.info('[V145] Modelos lentos y Sugerido 0 preparados en Macro compañía.');
})();
</script>'''

    @m.app.middleware('http')
    async def _v145_html(request, call_next):
        response = await call_next(request)
        if request.url.path != '/' or getattr(response, 'status_code', 200) != 200:
            return response
        try:
            body=b''
            async for chunk in response.body_iterator:
                body += chunk
            html=body.decode('utf-8',errors='replace')
            if 'v145-commercial-macro-models-js' not in html:
                html=html.replace('</body>',js+'</body>',1)
            return HTMLResponse(html,status_code=response.status_code,headers={
                'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                'Pragma':'no-cache','Expires':'0',
                'X-Operations-UI-Version':'V145-COMMERCIAL-MACRO-MODELS',
            })
        except Exception as exc:
            print(f'[V145] HTML warning: {type(exc).__name__}: {exc}',flush=True)
            return response

    m._V145_COMMERCIAL_MACRO_MODELS=True
    print('[V145] Modelos lentos y Sugerido 0 movidos a Macro compañía.',flush=True)
