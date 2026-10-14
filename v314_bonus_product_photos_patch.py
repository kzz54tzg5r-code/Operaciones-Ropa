"""V314: fotografías por ID en Modelos a Detalle de Bonos 1–6.
No modifica cálculos ni fuentes de datos de los bonos.
Consulta exclusivamente al host de imágenes configurado para Price Shoes.
"""
import asyncio
import re
import urllib.request
import urllib.error
from collections import OrderedDict
from threading import Lock
from fastapi import Request, HTTPException
from fastapi.responses import Response, HTMLResponse

_BASE = "http://static.priceshoes.com.mx/imgs/original/articulo/"
_ALLOWED_ID = re.compile(r"^[0-9]{1,15}$")
_CACHE = OrderedDict()
_LOCK = Lock()
_MAX_CACHE = 300

def install(m):
    if getattr(m, "_V314_BONUS_PRODUCT_PHOTOS", False):
        return

    def fetch_photo(product_id):
        with _LOCK:
            found = _CACHE.get(product_id)
            if found:
                _CACHE.move_to_end(product_id)
                return found
        # La ruta exacta se probará en producción; ante error no se muestra imagen inventada.
        url = _BASE + product_id + ".jpg"
        req = urllib.request.Request(url, headers={"User-Agent": "OperacionesRopa/1.0", "Accept": "image/jpeg,image/*;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                mime = response.headers.get("Content-Type","").split(";")[0].lower().strip()
                if mime not in ("image/jpeg","image/jpg","image/png","image/webp"):
                    return None
                content = response.read(2_000_001)
                if not content or len(content)>2_000_000:
                    return None
                signature = (content[:3]==b"\xff\xd8\xff" or content[:8]==b"\x89PNG\r\n\x1a\n" or (content[:4]==b"RIFF" and content[8:12]==b"WEBP"))
                if not signature:
                    return None
                with _LOCK:
                    _CACHE[product_id]=(content,mime)
                    _CACHE.move_to_end(product_id)
                    while len(_CACHE)>_MAX_CACHE:
                        _CACHE.popitem(last=False)
                return content,mime
        except (urllib.error.URLError,TimeoutError,OSError,ValueError):
            return None

    @m.app.get("/api/bonuses/product-photo/{product_id}")
    async def bonus_product_photo(product_id:str, request:Request):
        m.require_user(request)
        if not _ALLOWED_ID.fullmatch(product_id):
            raise HTTPException(status_code=400,detail="ID inválido")
        image = await asyncio.to_thread(fetch_photo,product_id)
        if not image:
            raise HTTPException(status_code=404,detail="Fotografía no disponible")
        return Response(image[0],media_type=image[1],headers={"Cache-Control":"private, max-age=86400","X-Content-Type-Options":"nosniff"})

    css = """<style id="v314-bonus-photos-css">
#v313Host .v314-photo-cell{width:52px;min-width:52px;padding:3px 5px!important}
#v313Host .v314-photo{display:block;width:42px;height:54px;object-fit:contain;background:#f0f4f8;border:1px solid #dde5ec;border-radius:5px;cursor:zoom-in}
#v313Host .v314-photo-missing{display:grid;place-items:center;width:42px;height:54px;background:#f5f7fa;border:1px dashed #d6dce5;border-radius:5px;color:#70829a;font-size:8px;white-space:normal;line-height:1.15;text-align:center}
</style>"""
    js = """<script id="v314-bonus-photos-js">(function(){
if(window.__V314_BONUS_PHOTOS)return;window.__V314_BONUS_PHOTOS=true;
function exportControls(root){
 var panel=root.querySelector('.v313-panel');
 var table=Array.from(root.querySelectorAll('table')).find(function(t){return /DDI inicial/.test(t.textContent||'')&&/Inv. actual/.test(t.textContent||'')});
 if(!table)return;
 var bar=table.closest('.v313-panel')||table.parentElement;
 if(!bar||bar.querySelector('[data-v314-export]'))return;
 var div=document.createElement('div');div.dataset.v314Export='1';div.style.cssText='display:flex;justify-content:flex-end;gap:6px;padding:6px 10px;flex-wrap:wrap';
 function button(label,fn){var b=document.createElement('button');b.textContent=label;b.type='button';b.style.cssText='border:1px solid #bad1ec;background:#fff;color:#124476;border-radius:6px;padding:6px 10px;font-weight:700;cursor:pointer';b.onclick=fn;div.appendChild(b)}
 function rows(){return Array.from(table.querySelectorAll('tr')).map(function(tr){return Array.from(tr.querySelectorAll('th,td')).map(function(c){return (c.innerText||'').trim()})}).filter(function(r){return r.length>2})}
 function filename(){var store=document.querySelector('#v313Store')?.value||'Tienda';var cat=root.querySelector('[data-v313-cat].active')?.textContent||'Catalogo';return ('Bonos_'+store+'_'+cat).replace(/[^a-zA-Z0-9_-]/g,'_')}
 button('Excel (CSV)',function(){
  var data=rows();if(data.length<2){alert('No hay modelos para exportar');return}
  var csv='\\ufeff'+data.map(function(r){return r.map(function(v){return '"'+String(v).replace(/"/g,'""')+'"'}).join(',')}).join('\\r\\n');
  var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download=filename()+'.csv';a.click();setTimeout(function(){URL.revokeObjectURL(a.href)},2000);
 });
 button('PDF / Imprimir',function(){
  var data=rows();if(data.length<2){alert('No hay modelos para exportar');return}
  var w=window.open('','_blank');if(!w){alert('Permite ventanas emergentes para imprimir');return}
  var title=filename();var cloned=table.cloneNode(true);
  cloned.querySelectorAll('img').forEach(function(im){im.style.cssText='width:35px;height:45px;object-fit:contain'});
  w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>'+title+'</title><style>@page{size:A4 landscape;margin:8mm}body{font-family:Arial;font-size:9px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #bbb;padding:3px}th{background:#eaf2fc}</style></head><body><h2>'+title+'</h2>'+cloned.outerHTML+'</body></html>');
  w.document.close();w.onload=function(){w.focus();w.print()};
 });
 bar.insertBefore(div,table);
}
function apply(){
 var root=document.getElementById('v313Host');if(!root)return;
 var tables=root.querySelectorAll('table');
 tables.forEach(function(table){
  var head=table.querySelector('thead tr');
  if(!head || !/ID/.test(head.textContent||'') || !/DDI inicial/.test(head.textContent||'') || !/Inv. actual/.test(head.textContent||''))return;
  if(!head.querySelector('[data-v314-photo-head]')){
   var th=document.createElement('th');th.textContent='Foto';th.dataset.v314PhotoHead='1';th.className='v314-photo-cell';head.insertBefore(th,head.firstChild);
  }
  table.querySelectorAll('tbody tr').forEach(function(tr){
   if(tr.querySelector('[data-v314-photo-cell]'))return;
   var first=tr.querySelector('td');if(!first)return;
   var id=(first.textContent||'').trim();
   var td=document.createElement('td');td.className='v314-photo-cell';td.dataset.v314PhotoCell='1';
   if(!/^\\d{1,15}$/.test(id)){td.innerHTML='<span class="v314-photo-missing">Sin foto</span>';}
   else{
    var img=document.createElement('img');img.className='v314-photo';img.alt='Foto ID '+id;img.loading='lazy';img.decoding='async';img.src='/api/bonuses/product-photo/'+encodeURIComponent(id);
    img.onerror=function(){if(img.parentNode){var span=document.createElement('span');span.className='v314-photo-missing';span.textContent='Sin foto';img.replaceWith(span)}};
    img.onclick=function(){
     var overlay=document.createElement('div');overlay.style.cssText='position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,.88);display:flex;align-items:center;justify-content:center;padding:56px 14px 14px;box-sizing:border-box';
     var big=document.createElement('img');big.src=img.src;big.alt=img.alt;big.style.cssText='max-width:100%;max-height:100%;object-fit:contain';
     var back=document.createElement('button');back.type='button';back.textContent='← Regresar al listado';back.style.cssText='position:absolute;top:12px;left:12px;background:#fff;color:#123d73;border:0;border-radius:8px;padding:12px 16px;font-weight:700;cursor:pointer';
     function close(){overlay.remove();document.removeEventListener('keydown',esc)}
     function esc(e){if(e.key==='Escape')close()}
     back.onclick=close;overlay.onclick=function(e){if(e.target===overlay)close()};
     overlay.appendChild(big);overlay.appendChild(back);document.body.appendChild(overlay);document.addEventListener('keydown',esc);
    };
    td.appendChild(img);
   }
   tr.insertBefore(td,first);
  });
 });
 exportControls(root);
}
function boot(){
 var root=document.getElementById('v313Host');if(!root)return;
 if(root.dataset.v314Observing==='1')return;root.dataset.v314Observing='1';
 new MutationObserver(function(){apply()}).observe(root,{childList:true,subtree:true});
 apply();
}
document.addEventListener('DOMContentLoaded',boot);
var retries=0;
var rootWatcher=new MutationObserver(function(){
  var root=document.getElementById('v313Host');
  if(root){boot();apply();if(root.dataset.v314Observing==='1')rootWatcher.disconnect();}
  else if(++retries>200)rootWatcher.disconnect();
});
rootWatcher.observe(document.documentElement,{childList:true,subtree:true});
[1000,2500,5000].forEach(function(t){setTimeout(boot,t)});
})();</script>"""

    @m.app.middleware("http")
    async def v314_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            content=b""
            async for chunk in response.body_iterator:
                content+=chunk
            html=content.decode("utf-8",errors="replace")
            if 'id="v314-bonus-photos-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v314-bonus-photos-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(response.headers);headers.pop("content-length",None)
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception:
            return response

    m._V314_BONUS_PRODUCT_PHOTOS=True
    print("[V314] Fotos por ID habilitadas para Modelos a Detalle (Bonos 1–6).",flush=True)
