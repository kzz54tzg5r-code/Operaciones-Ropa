"""V123 · Visibilidad estable de Operación.

Garantiza que la nueva vista Operación permanezca disponible dentro de
Cambios y Muertos, aparezca en la configuración de pestañas visibles y pueda
abrirse de forma consistente en la interfaz desplegada en Render.
"""
from __future__ import annotations


def install(m):
    if getattr(m, "_V123_OPERATION_VISIBILITY", False):
        return

    from datetime import datetime
    from fastapi.responses import HTMLResponse

    # Mantener Operación como pestaña interna de Cambios y Muertos y colocarla
    # inmediatamente después de Centro Ejecutivo en la configuración global.
    ordered = {}
    inserted = False
    for key, label in list(m.REPORT_TABS.items()):
        ordered[key] = label
        if key == "operations.center":
            ordered["operations.operation"] = "Operación"
            inserted = True
    if not inserted:
        ordered["operations.operation"] = "Operación"
    m.REPORT_TABS.clear()
    m.REPORT_TABS.update(ordered)

    # La tabla se inicializa antes de que se instalen los parches V121+; por eso
    # persistimos explícitamente la pestaña nueva para que también aparezca en
    # “Pestañas visibles”.
    try:
        with m.db() as con:
            con.execute(
                "INSERT OR IGNORE INTO report_tab_visibility(tab_key,visible,updated_at,updated_by) VALUES(?,?,?,?)",
                ("operations.operation", 1, datetime.now().isoformat(timespec="seconds"), "system-v123"),
            )
    except Exception as exc:
        print(f"[V123] No fue posible persistir visibilidad: {type(exc).__name__}: {exc}", flush=True)

    js = r'''<script id="v123-operation-visibility-js">
(function(){
  const OP='Operación', KEY='operations.operation';

  function isVisible(){
    try{
      if(USER?.role==='colaborador') return true;
      return typeof TAB_VISIBILITY!=='object' || TAB_VISIBILITY[KEY]!==false;
    }catch(_){ return true; }
  }

  function ensureOperationButton(){
    const nav=document.querySelector('#operativoNav');
    if(!nav) return null;
    let btn=nav.querySelector('[data-opview="Operación"]');
    if(!btn){
      btn=document.createElement('button');
      btn.className='switch';
      btn.dataset.opview=OP;
      btn.textContent=OP;
      const center=nav.querySelector('[data-opview="Centro Ejecutivo"],[data-opview="Centro Operativo"]');
      if(center) center.insertAdjacentElement('afterend',btn); else nav.prepend(btn);
    }
    btn.dataset.tabKey=KEY;
    btn.textContent=OP;
    btn.classList.toggle('hidden',!isVisible());
    btn.onclick=async function(ev){
      ev?.preventDefault?.();
      try{
        OP_VIEW=OP;
        document.querySelectorAll('#operativoNav [data-opview]').forEach(x=>x.classList.toggle('active',x===btn));
        if(typeof OPER_PERIOD==='object'){
          OPER_PERIOD.type='day';
          if(OPER_PERIOD.value===undefined) OPER_PERIOD.value='';
        }
        if(typeof window.renderOperativoView==='function'){
          await window.renderOperativoView(OP,true);
        }else if(typeof renderOperativoView==='function'){
          await renderOperativoView(OP,true);
        }
      }catch(err){
        console.error('[V123] No fue posible abrir Operación',err);
        const dyn=document.querySelector('#operativoDynamicContent');
        if(dyn) dyn.innerHTML=`<div class="infoempty">No fue posible abrir Operación: ${String(err?.message||err)}</div>`;
      }
    };
    return btn;
  }

  const oldApply=window.applyTabVisibility;
  if(typeof oldApply==='function'){
    window.applyTabVisibility=function(){
      const out=oldApply.apply(this,arguments);
      ensureOperationButton();
      return out;
    };
  }

  const oldLoad=window.loadTabVisibility;
  if(typeof oldLoad==='function'){
    window.loadTabVisibility=async function(){
      const out=await oldLoad.apply(this,arguments);
      ensureOperationButton();
      return out;
    };
  }

  ensureOperationButton();
  setTimeout(ensureOperationButton,0);
  setTimeout(ensureOperationButton,500);
  setTimeout(ensureOperationButton,1500);
  console.info('[V123] Operación visible, configurable y enlazada al reporte.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v123_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v123-operation-visibility-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(
                html,
                status_code=response.status_code,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Operations-UI-Version": "V123",
                },
            )
        except Exception as exc:
            print(f"[V123] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V123_OPERATION_VISIBILITY = True
    print("[V123] Operación asegurada en Cambios y Muertos y en Pestañas visibles.", flush=True)
