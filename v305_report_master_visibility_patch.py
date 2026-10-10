"""V305 · Bonos catalog navigation + master visibility per report.

- Bonos keeps four main tabs: Resumen general, Ranking de tiendas,
  Modelos a detalle and Abrigador.
- Abrigador contains Abrigador / Licencias / Básicos as internal selectors
  (implemented in V302 UI layer, this patch adds the report visibility feature).
- Users can disable the complete reports Cambios y Muertos, Operación,
  and Análisis Comercial from one master switch per report group.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")

REPORT_MODULES = {
    "operativo": "Cambios y Muertos",
    "operation": "Operación",
    "analysis": "Análisis Comercial",
}


def install(m):
    if getattr(m, "_V305_REPORT_MASTER_VISIBILITY", False):
        return

    now = datetime.now(MX).isoformat(timespec="seconds")
    with m.db() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS report_module_visibility_v305(
                report_key TEXT PRIMARY KEY,
                visible INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL
            )"""
        )
        for key in REPORT_MODULES:
            con.execute(
                "INSERT OR IGNORE INTO report_module_visibility_v305(report_key,visible,updated_at,updated_by) VALUES(?,?,?,?)",
                (key, 1, now, "system-v305"),
            )

    def _module_state():
        with m.db() as con:
            rows = con.execute(
                "SELECT report_key,visible,updated_at,updated_by FROM report_module_visibility_v305"
            ).fetchall()
        stored = {str(r["report_key"]): dict(r) for r in rows}
        return [
            {
                "key": key,
                "label": label,
                "visible": bool(stored.get(key, {}).get("visible", 1)),
                "updated_at": str(stored.get(key, {}).get("updated_at", "")),
                "updated_by": str(stored.get(key, {}).get("updated_by", "")),
            }
            for key, label in REPORT_MODULES.items()
        ]

    @m.app.get("/api/settings/report-modules-v305")
    def get_report_modules_v305(request: Request):
        m.require_user(request)
        return {"modules": _module_state()}

    @m.app.put("/api/settings/report-modules-v305")
    async def put_report_modules_v305(request: Request):
        actor = m.require_real_superadmin(request)
        body = await request.json()
        values = body.get("visibility") or {}
        if not isinstance(values, dict):
            raise m.HTTPException(400, "Configuración inválida")
        stamp = datetime.now(MX).isoformat(timespec="seconds")
        changed = []
        with m.db() as con:
            for key in REPORT_MODULES:
                if key not in values:
                    continue
                visible = 1 if bool(values[key]) else 0
                con.execute(
                    "INSERT INTO report_module_visibility_v305(report_key,visible,updated_at,updated_by) "
                    "VALUES(?,?,?,?) ON CONFLICT(report_key) DO UPDATE SET "
                    "visible=excluded.visible,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
                    (key, visible, stamp, str(actor.get("username") or "")),
                )
                changed.append(key)
        return {"ok": True, "changed": changed, "modules": _module_state()}

    css = r'''<style id="v305-report-master-css">
/* Reporte completo manda sobre cualquier pestaña interna. */
body[data-v305-hide-operativo="1"] [data-main="operativo"],
body[data-v305-hide-operation="1"] [data-main="operation"],
body[data-v305-hide-analysis="1"] [data-main="analysis"]{
  display:none!important;
  visibility:hidden!important;
  pointer-events:none!important;
}

/* Switch maestro dentro de Usuarios. */
#page-users .v305-report-master{
  display:flex!important;
  align-items:center!important;
  gap:7px!important;
  min-height:38px!important;
  margin:0 0 4px!important;
  padding:5px 4px 7px!important;
  border-bottom:2px solid #e5edf5!important;
}
#page-users .v305-report-master-icon{
  width:25px;height:25px;min-width:25px;
  display:grid;place-items:center;border-radius:7px;
  background:#eaf4ff;color:#0b78df;font-size:13px;font-weight:950;
}
#page-users .v305-report-master-copy{min-width:0;flex:1}
#page-users .v305-report-master-copy b{
  display:block;color:#123f73;font-size:9px;line-height:1.05;font-weight:950;
}
#page-users .v305-report-master-copy small{
  display:block;margin-top:2px;color:#71849a;font-size:7px;line-height:1.15;font-weight:700;
}
#page-users input[data-report-module-setting]{
  appearance:none!important;
  -webkit-appearance:none!important;
  position:relative!important;
  flex:0 0 34px!important;
  width:34px!important;min-width:34px!important;height:19px!important;
  margin:0!important;border:0!important;border-radius:999px!important;
  background:#cad7e5!important;cursor:pointer!important;outline:none!important;
  box-shadow:inset 0 0 0 1px rgba(33,70,106,.06)!important;
  transition:.18s ease!important;
}
#page-users input[data-report-module-setting]::after{
  content:""!important;position:absolute!important;top:2px!important;left:2px!important;
  width:15px!important;height:15px!important;border-radius:50%!important;background:#fff!important;
  box-shadow:0 2px 5px rgba(12,49,84,.22)!important;transition:.18s ease!important;
}
#page-users input[data-report-module-setting]:checked{background:#0b88f6!important}
#page-users input[data-report-module-setting]:checked::after{transform:translateX(15px)!important}
#page-users input[data-report-module-setting]:disabled{opacity:.55;cursor:wait!important}
#page-users .v305-report-off{
  opacity:.67;
}
#page-users .v305-report-off > label.field{
  opacity:.72;
}
#page-users .v305-master-message{
  grid-column:1/-1;
  min-height:14px;margin:2px 0 0;
  color:#486681;font-size:8px;font-weight:750;
}

@media(max-width:900px){
  #page-users .v305-report-master-copy b{font-size:10px}
  #page-users .v305-report-master-copy small{font-size:7.5px}
}
</style>'''

    js = r'''<script id="v305-report-master-js">
(function(){
  if(window.__V305_REPORT_MASTER_VISIBILITY)return;
  window.__V305_REPORT_MASTER_VISIBILITY=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const MODULES={
    operativo:{label:'Cambios y Muertos',titles:['cambios y muertos']},
    operation:{label:'Operación',titles:['operación','operacion']},
    analysis:{label:'Análisis Comercial',titles:['análisis comercial','analisis comercial']}
  };
  let STATE={operativo:true,operation:true,analysis:true};
  let loading=false;
  let decorateTimer=null;

  function norm(s){
    return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  }
  async function callApi(url,opts={}){
    const r=await fetch(url,{credentials:'same-origin',cache:'no-store',...opts});
    let d={};try{d=await r.json()}catch(_){}
    if(!r.ok)throw new Error(d.detail||d.message||('HTTP '+r.status));
    return d;
  }
  function setState(payload){
    const rows=payload?.modules||[];
    for(const row of rows){
      if(Object.prototype.hasOwnProperty.call(STATE,row.key))STATE[row.key]=row.visible!==false;
    }
    applyModuleVisibility();
    scheduleDecorate();
  }
  function applyModuleVisibility(){
    document.body.dataset.v305HideOperativo=STATE.operativo?'0':'1';
    document.body.dataset.v305HideOperation=STATE.operation?'0':'1';
    document.body.dataset.v305HideAnalysis=STATE.analysis?'0':'1';
    for(const key of Object.keys(MODULES)){
      qa('[data-main="'+key+'"]').forEach(el=>{
        const off=STATE[key]===false;
        el.setAttribute('aria-hidden',off?'true':'false');
        if('disabled' in el)el.disabled=off;
        el.dataset.v305ReportDisabled=off?'1':'0';
      });
    }
  }
  async function loadState(){
    if(loading)return;
    loading=true;
    try{setState(await callApi('/api/settings/report-modules-v305'))}
    catch(e){console.warn('[V305] No se pudo cargar visibilidad de reportes',e)}
    finally{loading=false}
  }
  function keyForGroup(section){
    const title=norm(q('.v222-vis-title',section)?.textContent||'');
    if(title.includes('cambios')&&title.includes('muertos'))return'operativo';
    if(title==='operacion')return'operation';
    if(title.includes('analisis')&&title.includes('comercial'))return'analysis';
    return'';
  }
  function masterRow(key){
    const row=document.createElement('div');
    row.className='v305-report-master';
    row.dataset.v305Master=key;
    row.innerHTML=
      '<span class="v305-report-master-icon">▦</span>'+
      '<span class="v305-report-master-copy"><b>Reporte completo</b><small>Oculta o muestra todo '+MODULES[key].label+'.</small></span>'+
      '<input type="checkbox" data-report-module-setting="'+key+'" aria-label="Activar o desactivar '+MODULES[key].label+'">';
    const input=q('input',row);
    input.checked=STATE[key]!==false;
    input.addEventListener('change',async()=>{
      const wanted=!!input.checked;
      const old=STATE[key]!==false;
      input.disabled=true;
      try{
        const d=await callApi('/api/settings/report-modules-v305',{
          method:'PUT',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({visibility:{[key]:wanted}})
        });
        setState(d);
        document.dispatchEvent(new CustomEvent('report-modules-visibility-changed',{detail:{key,visible:wanted}}));
      }catch(e){
        STATE[key]=old;input.checked=old;
        alert('No fue posible cambiar el reporte completo: '+(e.message||e));
      }finally{input.disabled=false}
    });
    return row;
  }
  function decorateUsers(){
    const box=q('#tabVisibilityOptions');
    if(!box)return;
    qa('.v222-vis-group',box).forEach(section=>{
      const key=keyForGroup(section);
      if(!key)return;
      let row=q(':scope>.v305-report-master',section);
      if(!row){
        row=masterRow(key);
        const title=q(':scope>.v222-vis-title',section);
        if(title)title.insertAdjacentElement('afterend',row);else section.prepend(row);
      }else{
        const input=q('input[data-report-module-setting]',row);
        if(input&&!input.disabled)input.checked=STATE[key]!==false;
      }
      section.classList.toggle('v305-report-off',STATE[key]===false);
    });
    const head=q('#tabVisibilityPanel .v219-tabs-head p');
    if(head)head.textContent='Activa o desactiva el reporte completo y, debajo, decide qué pestañas internas quedan visibles.';
  }
  function scheduleDecorate(){
    clearTimeout(decorateTimer);
    decorateTimer=setTimeout(()=>{decorateUsers();applyModuleVisibility()},35);
  }

  // Impedir abrir reportes completos desactivados, incluso si otro parche
  // vuelve a insertar temporalmente una entrada del menú.
  document.addEventListener('click',e=>{
    const entry=e.target.closest?.('[data-main]');
    if(!entry)return;
    const key=String(entry.dataset.main||'');
    if(Object.prototype.hasOwnProperty.call(STATE,key)&&STATE[key]===false){
      e.preventDefault();e.stopImmediatePropagation();
      console.info('[V305] Reporte completo desactivado:',key);
    }
  },true);

  const previousGoMain=window.goMain;
  if(typeof previousGoMain==='function'){
    window.goMain=async function(name){
      const key=String(name||'').toLowerCase();
      if(Object.prototype.hasOwnProperty.call(STATE,key)&&STATE[key]===false){
        console.info('[V305] Navegación bloqueada: reporte desactivado',key);
        return null;
      }
      return previousGoMain.apply(this,arguments);
    };
  }

  const previousEnter=window.enter;
  if(typeof previousEnter==='function'){
    window.enter=async function(){
      const result=await previousEnter.apply(this,arguments);
      await loadState();
      scheduleDecorate();
      return result;
    };
  }

  const observer=new MutationObserver(muts=>{
    if(muts.some(x=>x.type==='childList'))scheduleDecorate();
  });
  function observe(){
    const box=q('#tabVisibilityOptions');
    if(box)observer.observe(box,{childList:true,subtree:true});
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',()=>{loadState();observe();[80,300,900,1800].forEach(ms=>setTimeout(scheduleDecorate,ms))},{once:true});
  }else{
    loadState();observe();[0,120,500,1300].forEach(ms=>setTimeout(scheduleDecorate,ms));
  }
  window.addEventListener('pageshow',()=>{loadState();scheduleDecorate()},{passive:true});
  document.addEventListener('report-tabs-visibility-changed',scheduleDecorate);
  document.addEventListener('report-modules-visibility-changed',scheduleDecorate);

  console.info('[V305] Interruptor maestro por reporte instalado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v305_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if 'id="v305-report-master-css"' not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if 'id="v305-report-master-js"' not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-Visibility-Version"] = "V305-REPORT-MASTER"
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V305] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V305_REPORT_MASTER_VISIBILITY = True
    print("[V305] Reportes completos configurables: Cambios y Muertos, Operación y Análisis Comercial.", flush=True)
