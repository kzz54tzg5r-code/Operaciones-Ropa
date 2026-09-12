"""V134 · Rescate de interacción móvil para el demo Comercial V133.

Corrige taps bloqueados en iPhone/iPad sin tocar datos reales: eleva la capa del
demo, intercepta el toque por coordenadas y ofrece un selector propio para los
filtros. Las pestañas y Consultar se ejecutan aunque otra capa transparente del
portal capture el evento original.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V134_COMMERCIAL_TOUCH_FIX", False):
        return

    css = r'''<style id="v134-commercial-touch-css">
body.v133-commercial-demo main.main{
  position:relative!important;
  z-index:2147483000!important;
  pointer-events:auto!important;
}
body.v133-commercial-demo #v133CommercialDemoHost{
  position:relative!important;
  z-index:2147483646!important;
  pointer-events:auto!important;
  isolation:isolate!important;
}
body.v133-commercial-demo #v133CommercialDemoHost,
body.v133-commercial-demo #v133CommercialDemoHost *{
  pointer-events:auto!important;
}
body.v133-commercial-demo #v133CommercialDemoHost .v133-tab,
body.v133-commercial-demo #v133CommercialDemoHost .v133-query,
body.v133-commercial-demo #v133CommercialDemoHost select{
  touch-action:manipulation!important;
  -webkit-tap-highlight-color:rgba(37,112,232,.16);
}
#v134PickerOverlay{display:none;position:fixed;inset:0;z-index:2147483647;background:rgba(14,35,65,.28);align-items:flex-end;justify-content:center;padding:12px;pointer-events:auto!important}
#v134PickerOverlay.open{display:flex!important}
#v134PickerSheet{width:min(520px,100%);max-height:70vh;overflow:auto;background:#fff;border-radius:18px;padding:10px;box-shadow:0 18px 50px rgba(9,35,75,.28);-webkit-overflow-scrolling:touch}
.v134-picker-title{font:900 13px/1.2 system-ui,-apple-system,sans-serif;color:#123b73;padding:8px 8px 10px}
.v134-option{display:flex;width:100%;min-height:44px;align-items:center;justify-content:space-between;border:0;border-bottom:1px solid #e7edf4;background:#fff;color:#173f78;padding:10px 9px;font:800 13px/1.15 system-ui,-apple-system,sans-serif;text-align:left;pointer-events:auto!important}
.v134-option:last-child{border-bottom:0}.v134-option.selected{color:#1769e8;background:#f2f7ff}.v134-option .check{font-weight:950}
.v134-picker-cancel{width:100%;height:42px;border:0;border-radius:11px;background:#eef3f9;color:#53657e;font:900 12px system-ui,-apple-system,sans-serif;margin-top:8px;pointer-events:auto!important}
</style>'''

    js = r'''<script id="v134-commercial-touch-js">
(function(){
  let lastTouch=0, pickerSelect=null, internal=false;
  const H=()=>document.getElementById('v133CommercialDemoHost');
  const active=()=>!!(H()&&document.body.classList.contains('v133-commercial-demo'));
  const visible=el=>{if(!el)return false;const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'};
  const inside=(el,x,y)=>{if(!visible(el))return false;const r=el.getBoundingClientRect();return x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom};
  const point=e=>{const t=e.changedTouches&&e.changedTouches[0];return t?{x:t.clientX,y:t.clientY}:{x:e.clientX,y:e.clientY}};
  const hit=(sel,x,y)=>[...(H()?.querySelectorAll(sel)||[])].find(el=>inside(el,x,y));

  function ensurePicker(){
    let o=document.getElementById('v134PickerOverlay');
    if(o)return o;
    o=document.createElement('div');o.id='v134PickerOverlay';
    o.innerHTML='<div id="v134PickerSheet"><div class="v134-picker-title">Selecciona una opción</div><div id="v134PickerOptions"></div><button type="button" class="v134-picker-cancel">Cancelar</button></div>';
    document.body.appendChild(o);
    o.querySelector('.v134-picker-cancel').addEventListener('click',closePicker);
    o.addEventListener('click',e=>{if(e.target===o)closePicker()});
    return o;
  }
  function labelFor(sel){const field=sel.closest('.v133-field');return field?.querySelector('label')?.textContent||'Selecciona una opción'}
  function openPicker(sel){
    const o=ensurePicker();pickerSelect=sel;
    o.querySelector('.v134-picker-title').textContent=labelFor(sel);
    o.querySelector('#v134PickerOptions').innerHTML=[...sel.options].map((opt,i)=>`<button type="button" class="v134-option ${opt.value===sel.value?'selected':''}" data-v134-index="${i}"><span>${opt.textContent}</span><span class="check">${opt.value===sel.value?'✓':''}</span></button>`).join('');
    o.classList.add('open');
  }
  function closePicker(){const o=document.getElementById('v134PickerOverlay');o?.classList.remove('open');pickerSelect=null}
  function choose(btn){
    if(!pickerSelect)return;
    const i=Number(btn.dataset.v134Index);const opt=pickerSelect.options[i];if(!opt)return;
    pickerSelect.value=opt.value;pickerSelect.dispatchEvent(new Event('change',{bubbles:true}));closePicker();
  }
  function synthClick(el){if(!el)return;internal=true;try{el.click()}finally{setTimeout(()=>internal=false,0)}}

  function rescue(e){
    if(internal||!active())return;
    const now=Date.now();if(e.type==='touchend'){lastTouch=now}else if(e.type==='pointerup'&&now-lastTouch<450){return}
    const p=point(e);if(!Number.isFinite(p.x)||!Number.isFinite(p.y))return;
    const overlay=document.getElementById('v134PickerOverlay');
    if(overlay?.classList.contains('open')){
      const option=[...overlay.querySelectorAll('.v134-option')].find(el=>inside(el,p.x,p.y));
      if(option){e.preventDefault();e.stopPropagation();choose(option);return}
      const cancel=overlay.querySelector('.v134-picker-cancel');
      if(inside(cancel,p.x,p.y)){e.preventDefault();e.stopPropagation();closePicker();return}
      const sheet=overlay.querySelector('#v134PickerSheet');
      if(!inside(sheet,p.x,p.y)){e.preventDefault();e.stopPropagation();closePicker();return}
      return;
    }
    const sel=hit('select',p.x,p.y);
    if(sel){e.preventDefault();e.stopPropagation();openPicker(sel);return}
    const tab=hit('[data-v133-tab]',p.x,p.y);
    if(tab){e.preventDefault();e.stopPropagation();synthClick(tab);return}
    const query=hit('#v133Query',p.x,p.y);
    if(query){e.preventDefault();e.stopPropagation();synthClick(query);return}
  }

  document.addEventListener('pointerup',rescue,true);
  document.addEventListener('touchend',rescue,{capture:true,passive:false});

  function elevate(){
    const h=H();if(!h)return;
    h.style.setProperty('z-index','2147483646','important');
    h.style.setProperty('pointer-events','auto','important');
    const main=h.closest('main.main');
    if(main){main.style.setProperty('position','relative','important');main.style.setProperty('z-index','2147483000','important');main.style.setProperty('pointer-events','auto','important')}
  }
  new MutationObserver(()=>{if(active())elevate()}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style']});
  setTimeout(elevate,300);setTimeout(elevate,1200);
  console.info('[V134] Rescate táctil Comercial activo: filtros, Consultar y pestañas protegidos contra capas transparentes.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v134_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v134-commercial-touch-js" not in html:
                html = html.replace("</head>", css + "</head>", 1).replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V134-COMMERCIAL-TOUCH-FIX",
            })
        except Exception as exc:
            print(f"[V134] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V134_COMMERCIAL_TOUCH_FIX = True
    print("[V134] Rescate táctil Comercial instalado: filtros y pestañas interactivos en móvil.", flush=True)
