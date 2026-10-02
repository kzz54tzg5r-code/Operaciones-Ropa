"""V241 · Cargar productividad C&M autoritativo + limpieza inmediata de Recorridos.

Corrige el cruce visible en video del 2026-10-02:
- Cargar productividad (Cambios y Muertos) ya no puede mostrar el ranking de Productividad.
- Mantiene captura con temporizador y Capturas de hoy.
- Nuevas capturas usan únicamente Clasificado, Acondicionado, Ubicado y Pizca.
- Si existe una captura legacy en curso (por ejemplo Recolección), permite terminarla.
- Al entrar a Recorridos se ocultan de inmediato los gráficos heredados mientras V240 carga
  la matriz/calendario/resumen, evitando que se vea por unos instantes "Recorridos por día".
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V241_CM_CAPTURE_AUTHORITATIVE", False):
        return

    css = r'''<style id="v241-cm-capture-css">
body.v241-cm-capture #operativoPeriodBar,
body.v241-cm-capture #v161FilterBar{
  display:none!important;
}
body.v241-cm-capture #v166MissingProductivity{
  display:none!important;
}
.v241-capture-panel{
  background:#fff;border:1px solid #d6e3f0;border-radius:16px;
  padding:14px;margin:8px 0;box-shadow:0 5px 18px rgba(25,72,118,.05)
}
.v241-capture-head{
  display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap
}
.v241-capture-head h3{margin:0;color:#123f73;font-size:15px;font-weight:950}
.v241-capture-note{margin-top:4px;color:#71849a;font-size:8px;line-height:1.4}
.v241-timer{
  min-width:145px;padding:9px 12px;border-radius:12px;background:#edf5ff;
  color:#123f73;font-size:27px;font-weight:950;text-align:center;font-variant-numeric:tabular-nums
}
.v241-capture-meta{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.v241-capture-meta span{
  padding:5px 8px;border-radius:999px;background:#f2f6fb;color:#526d88;font-size:8px;font-weight:800
}
.v241-field{margin-top:10px}
.v241-field label{
  display:block;margin:0 0 5px;color:#526b84;font-size:8px;font-weight:950;
  text-transform:uppercase;letter-spacing:.04em
}
.v241-field select,.v241-field input{
  width:100%;min-height:44px;border:1px solid #ccd9e7;border-radius:10px;
  padding:8px 10px;background:#fff;color:#123f73;font-size:13px;font-weight:850
}
.v241-pieces{max-width:310px}
.v241-legacy-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}
.v241-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px}
.v241-actions button{
  min-width:110px;min-height:42px;border:0;border-radius:11px;color:#fff;font-weight:950;cursor:pointer
}
.v241-start{background:#0aa44b}.v241-finish{background:#e85c64}
.v241-actions button:disabled{opacity:.45;cursor:default}
.v241-msg{min-height:16px;color:#526b84;font-size:9px;font-weight:800}
.v241-history{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #d9e5f1;border-radius:12px}
.v241-history table{width:100%;min-width:760px;border-collapse:collapse}
.v241-history th{padding:8px;background:#124d84;color:#fff;text-align:left;font-size:8px;white-space:nowrap}
.v241-history td{padding:8px;border-bottom:1px solid #e8eef5;color:#294b70;font-size:8px;white-space:nowrap}
@media(max-width:600px){
  .v241-capture-panel{padding:10px;border-radius:13px}
  .v241-timer{min-width:118px;font-size:22px}
  .v241-legacy-grid{grid-template-columns:1fr}
}
</style>'''

    js = r'''<script id="v241-cm-capture-js">
(function(){
  if(window.__V241_CM_CAPTURE)return;
  window.__V241_CM_CAPTURE=true;

  const C='Cargar productividad';
  const ALLOWED=['Clasificado','Acondicionado','Ubicado','Pizca'];
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=v=>{const x=Number(v||0);return Number.isFinite(x)?x:0};
  const nf=v=>Math.round(n(v)).toLocaleString('es-MX');
  let active=null,timer=0,seq=0;

  function isCm(){
    let main='';try{main=String(window.MAIN||'').toLowerCase()}catch(_){}
    return main==='operativo'||String(document.body.dataset.v163Module||'').toLowerCase()==='operativo'||document.body.classList.contains('v238-module-operativo');
  }
  function hms(sec){
    sec=Math.max(0,Math.floor(Number(sec)||0));
    const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;
    return [h,m,s].map(x=>String(x).padStart(2,'0')).join(':');
  }
  function mxToday(){
    return new Intl.DateTimeFormat('en-CA',{
      timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'
    }).format(new Date());
  }
  async function A(url,opt){
    if(typeof api==='function')return api(url,{timeoutMs:60000,...(opt||{})});
    const r=await fetch(url,{credentials:'same-origin',...(opt||{})});
    const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch(_){}
    if(!r.ok)throw Error(d.detail||d.message||('HTTP '+r.status));
    return d;
  }
  function updateClock(){
    const el=q('#v241Timer');if(!el)return;
    if(!active?.started_at){el.textContent='00:00:00';return}
    const start=new Date(active.started_at).getTime();
    el.textContent=hms((Date.now()-start)/1000);
  }
  function startClock(){
    clearInterval(timer);updateClock();timer=setInterval(updateClock,1000);
  }
  function markCapture(){
    document.body.classList.add('v241-cm-capture');
    try{window.OP_VIEW=C;OP_VIEW=C}catch(_){}
    qa('#operativoNav>button[data-opview]').forEach(btn=>{
      const on=btn.dataset.opview===C||btn.dataset.tabKey==='operations.productivity_capture';
      btn.classList.toggle('active',on);
      btn.setAttribute('aria-selected',on?'true':'false');
    });
    q('#operativoCentro')?.classList.add('hidden');
    q('#operativoDynamic')?.classList.remove('hidden');
    const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub');
    if(title)title.textContent=C;
    if(sub)sub.textContent='Cambios y Muertos · piezas y tiempo real';
    q('#operativoPeriodBar')?.classList.add('hidden');
    const facade=q('#v161FilterBar');if(facade)facade.classList.remove('on');
  }
  function leaveCapture(){
    document.body.classList.remove('v241-cm-capture');
    clearInterval(timer);
  }
  function selectedStore(meta){
    const assigned=String(meta?.user?.store||'').trim();
    if(assigned)return assigned;
    const current=String(q('#operStoreSelect')?.value||'').trim();
    if(current&&current!=='Compañía')return current;
    return String(meta?.stores?.[0]||'');
  }
  function historyDetail(r){
    if(String(r.activity||'').toLowerCase().includes('recolec')){
      return 'Muertos '+nf(r.muertos)+' · Cajas '+nf(r.cajas)+' · Probador '+nf(r.probador);
    }
    return '—';
  }
  function rowPieces(r){
    const pieces=n(r.pieces);
    return pieces>0?pieces:n(r.muertos)+n(r.cajas)+n(r.probador);
  }

  async function renderCmCapture(){
    if(!isCm())return;
    const mine=++seq;
    markCapture();
    const host=q('#operativoDynamicContent');if(!host)return;
    host.innerHTML='<div class="infoempty">Preparando captura…</div>';
    try{
      const [meta,run]=await Promise.all([
        A('/api/cm-productivity/meta'),
        A('/api/cm-productivity/active')
      ]);
      if(mine!==seq)return;
      active=run?.item||null;
      if(meta?.user?.profile_required){
        host.innerHTML='<div class="infoempty">Completa tu nombre completo y nómina en tu perfil antes de registrar productividad.</div>';
        return;
      }
      const store=selectedStore(meta);
      const hist=await A('/api/cm-productivity/history?date='+encodeURIComponent(mxToday())+'&store='+encodeURIComponent(store));
      if(mine!==seq)return;

      const legacyCollection=!!active&&String(active.activity||'').toLowerCase().includes('recolec');
      const activity=active?.activity||ALLOWED[0];
      const options=(active&&!ALLOWED.includes(activity)?[activity,...ALLOWED]:ALLOWED)
        .map(x=>'<option value="'+esc(x)+'" '+(x===activity?'selected':'')+'>'+esc(x)+'</option>').join('');

      host.innerHTML=
        '<div id="v241CmCapture" class="v241-capture-panel">'+
          '<div class="v241-capture-head"><div><h3>Registro de productividad</h3>'+
            '<div class="v241-capture-note">Fecha, tienda, nombre y nómina se asignan automáticamente desde tu sesión.</div></div>'+
            '<div id="v241Timer" class="v241-timer">00:00:00</div></div>'+
          '<div class="v241-capture-meta"><span>'+esc(mxToday())+'</span><span>'+esc(store||'Sin tienda')+'</span>'+
            '<span>'+esc(meta?.user?.full_name||meta?.user?.username||'')+'</span><span>Nómina '+esc(meta?.user?.employee_no||'—')+'</span></div>'+
          '<div class="v241-field"><label>Actividad realizada</label><select id="v241Activity" '+(active?'disabled':'')+'>'+options+'</select></div>'+
          (legacyCollection
            ?'<div class="v241-legacy-grid">'+
               '<div class="v241-field"><label>Muertos · piezas</label><input id="v241Muertos" type="number" min="0" inputmode="numeric" value="'+n(active?.muertos)+'"></div>'+
               '<div class="v241-field"><label>Cajas · piezas</label><input id="v241Cajas" type="number" min="0" inputmode="numeric" value="'+n(active?.cajas)+'"></div>'+
               '<div class="v241-field"><label>Probador · piezas</label><input id="v241Probador" type="number" min="0" inputmode="numeric" value="'+n(active?.probador)+'"></div>'+
             '</div>'
            :'<div class="v241-field v241-pieces"><label>Piezas</label><input id="v241Pieces" type="number" min="0" inputmode="numeric" value="'+n(active?.pieces)+'"></div>')+
          '<div class="v241-actions"><button id="v241Start" class="v241-start" '+(active?'disabled':'')+'>▶ Inicio</button>'+
            '<button id="v241Finish" class="v241-finish" '+(!active?'disabled':'')+'>■ Fin</button><span id="v241Msg" class="v241-msg"></span></div>'+
        '</div>'+
        '<div class="v241-capture-panel"><h3 style="margin:0 0 9px;color:#123f73">Capturas de hoy</h3>'+
          '<div class="v241-history"><table><thead><tr><th>Colaborador</th><th>Actividad</th><th>Piezas</th><th>Detalle recolección</th><th>Tiempo</th><th>Estado</th></tr></thead><tbody>'+
          ((hist?.items||[]).map(r=>'<tr><td><b>'+esc(r.employee_name)+'</b></td><td>'+esc(r.activity)+'</td><td><b>'+nf(rowPieces(r))+'</b></td>'+
            '<td>'+esc(historyDetail(r))+'</td><td>'+hms(r.duration_seconds)+'</td><td>'+esc(r.status==='active'?'En curso':'Finalizado')+'</td></tr>').join('')||
            '<tr><td colspan="6">Sin capturas de hoy.</td></tr>')+
          '</tbody></table></div></div>';

      if(active)startClock();else{clearInterval(timer);updateClock()}

      q('#v241Start')?.addEventListener('click',async()=>{
        const msg=q('#v241Msg');if(msg)msg.textContent='Iniciando…';
        try{
          const activity=q('#v241Activity')?.value||ALLOWED[0];
          if(!ALLOWED.includes(activity))throw Error('Selecciona una actividad válida');
          const r=await A('/api/cm-productivity/start',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({store,activity})
          });
          if(msg)msg.textContent=r.message||'Tiempo iniciado';
          await renderCmCapture();
        }catch(e){if(msg)msg.textContent=e.message||String(e)}
      });

      q('#v241Finish')?.addEventListener('click',async()=>{
        if(!active)return;
        const msg=q('#v241Msg');if(msg)msg.textContent='Finalizando…';
        try{
          const payload=legacyCollection
            ?{muertos:n(q('#v241Muertos')?.value),cajas:n(q('#v241Cajas')?.value),probador:n(q('#v241Probador')?.value)}
            :{pieces:n(q('#v241Pieces')?.value)};
          const r=await A('/api/cm-productivity/'+encodeURIComponent(active.id)+'/finish',{
            method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)
          });
          if(msg)msg.textContent=r.message||'Productividad guardada';
          active=null;clearInterval(timer);
          await renderCmCapture();
        }catch(e){if(msg)msg.textContent=e.message||String(e)}
      });
    }catch(e){
      if(mine!==seq)return;
      host.innerHTML='<div class="infoempty">No fue posible abrir Cargar productividad: '+esc(e.message||e)+'</div>';
    }
  }
  window.V241_renderCmCapture=renderCmCapture;

  function cleanRouteLegacyNow(){
    const activeBtn=q('#operativoNav .active');
    const isRoutes=String(activeBtn?.dataset.tabKey||'')==='operations.routes'||
      String(activeBtn?.dataset.opview||'').toLowerCase().includes('recorridos');
    if(!isRoutes)return;
    q('#v167MatrixVisual')?.remove();
    qa('#operativoDynamicContent .chart-box').forEach(box=>{
      const title=String(q('.chart-title',box)?.textContent||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
      if(title.includes('recorridos por dia')||title.includes('distribucion por hora y dia')||title.includes('tendencia de recoleccion')){
        box.style.display='none';
      }
    });
  }

  const previous=window.renderOperativoView;
  if(typeof previous==='function'){
    const wrapped=async function(name,force=false){
      if(String(name||'')===C){
        return await renderCmCapture();
      }
      leaveCapture();
      return await previous.apply(this,arguments);
    };
    // V199 reintenta su instalación varias veces. Marcar la función evita que
    // vuelva a envolver V241 y recupere el renderer antiguo de captura.
    wrapped.__v199=true;
    wrapped.__v241=true;
    window.renderOperativoView=wrapped;
  }

  document.addEventListener('click',e=>{
    const capture=e.target.closest?.('#operativoNav [data-tab-key="operations.productivity_capture"],#operativoNav [data-opview="Cargar productividad"]');
    if(capture&&isCm()){
      e.preventDefault();e.stopImmediatePropagation();
      renderCmCapture();
      return;
    }
    const other=e.target.closest?.('#operativoNav [data-opview]');
    if(other&&other.dataset.opview!==C){
      leaveCapture();
      if(String(other.dataset.tabKey||'')==='operations.routes'||String(other.dataset.opview||'').toLowerCase().includes('recorridos')){
        setTimeout(cleanRouteLegacyNow,0);
        setTimeout(cleanRouteLegacyNow,80);
      }
    }
  },true);

  function init(){
    const capture=q('#operativoNav [data-tab-key="operations.productivity_capture"],#operativoNav [data-opview="Cargar productividad"]');
    if(capture){
      capture.dataset.v241='1';
      capture.title=C;
    }
    cleanRouteLegacyNow();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  [120,500,1200,2400].forEach(ms=>setTimeout(init,ms));
  window.addEventListener('pageshow',()=>setTimeout(init,80),{passive:true});

  console.info('[V241] Cargar productividad C&M autoritativo + Recorridos sin visual heredado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v241_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v241-cm-capture-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v241-cm-capture-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0",
                "X-Operations-UI-Version":"V241-CM-CAPTURE",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V241] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V241_CM_CAPTURE_AUTHORITATIVE = True
    print("[V241] Cargar productividad C&M autoritativo instalado.", flush=True)
