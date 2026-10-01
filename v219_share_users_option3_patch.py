"""V219 · Opción 3 para Compartir sistema y Usuarios.

Parche visual aislado:
- Compartir sistema adopta el boceto Opción 3.
- Usuarios adopta el boceto Opción 3 en cambio de contraseña y pestañas visibles.
- Conserva IDs, permisos y handlers existentes.
- No toca reportes, pestañas de reportes, filtros comerciales ni cálculos.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V219_SHARE_USERS_OPTION3", False):
        return

    css = r"""<style id="v219-share-users-option3-css">
:root{
  --v219-blue:#0b4d88;
  --v219-blue2:#0b82f4;
  --v219-ink:#123f73;
  --v219-muted:#70839b;
  --v219-line:#d7e4f1;
  --v219-soft:#f3f8fe;
  --v219-card:#ffffff;
}

/* Sólo afecta Compartir y Usuarios. */
#page-share,#page-users{
  max-width:1100px;
  margin:0 auto;
}
#page-share .title,#page-users .title{
  color:var(--v219-ink);
}

/* =========================================================
   COMPARTIR SISTEMA · OPCIÓN 3
   ========================================================= */
#page-share.v219-share{
  display:none;
}
#page-share.v219-share.active{
  display:block;
}
#page-share.v219-share .v219-share-intro{
  display:grid;
  grid-template-columns:92px 1fr;
  gap:18px;
  align-items:center;
  padding:16px 18px;
  margin:0 0 12px;
  border:1px solid var(--v219-line);
  border-radius:20px;
  background:linear-gradient(135deg,#eef7ff 0%,#f8fbff 100%);
}
#page-share.v219-share .v219-share-intro-icon{
  width:82px;height:82px;
  display:grid;place-items:center;
  border-radius:20px;
  background:#fff;
  color:#0c6ed7;
  box-shadow:0 8px 22px rgba(13,79,139,.10);
}
#page-share.v219-share .v219-share-intro-icon svg{
  width:46px;height:46px;stroke:currentColor;fill:none;stroke-width:1.8;
}
#page-share.v219-share .v219-share-intro h2{
  margin:0 0 5px;
  color:var(--v219-ink);
  font-size:24px;
  line-height:1.05;
  font-weight:950;
}
#page-share.v219-share .v219-share-intro p{
  margin:0;
  color:var(--v219-muted);
  font-size:12px;
  line-height:1.42;
  font-weight:650;
}

#page-share.v219-share .v219-share-card{
  padding:16px;
  border:1px solid var(--v219-line);
  border-radius:18px;
  background:var(--v219-card);
  box-shadow:0 7px 22px rgba(15,73,120,.06);
}
#page-share.v219-share .v219-share-card + .v219-share-card{margin-top:10px}
#page-share.v219-share .v219-card-head{
  display:flex;
  gap:11px;
  align-items:center;
  margin-bottom:10px;
}
#page-share.v219-share .v219-card-icon{
  width:40px;height:40px;min-width:40px;
  display:grid;place-items:center;
  border-radius:12px;
  background:#e9f4ff;
  color:#0879e8;
}
#page-share.v219-share .v219-card-icon svg{
  width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.9;
}
#page-share.v219-share .v219-card-head h3{
  margin:0;
  color:#133d6d;
  font-size:16px;
  font-weight:950;
}
#page-share.v219-share .v219-card-head p{
  margin:3px 0 0;
  color:var(--v219-muted);
  font-size:10.5px;
  line-height:1.35;
  font-weight:650;
}
#page-share.v219-share .v219-urlbox{
  display:grid;
  grid-template-columns:minmax(0,1fr) 34px;
  align-items:center;
  gap:8px;
  min-height:44px;
  margin:8px 0;
  padding:7px 8px 7px 12px;
  border:1px solid #d8e5f2;
  border-radius:12px;
  background:#f2f7fc;
}
#page-share.v219-share .v219-urlbox .big{
  min-width:0;
  margin:0;
  color:#103d70;
  font-size:11px!important;
  line-height:1.3;
  font-weight:850;
  overflow-wrap:anywhere;
}
#page-share.v219-share .v219-copy-mini{
  width:34px;height:34px;
  border:0;
  border-radius:9px;
  display:grid;place-items:center;
  background:#fff;
  color:#0b74d9;
  cursor:pointer;
}
#page-share.v219-share .v219-copy-mini svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.9}
#page-share.v219-share .v219-copy-mini:disabled{opacity:.45;cursor:not-allowed}

#page-share.v219-share .v219-share-actions{
  display:grid;
  gap:7px;
}
#page-share.v219-share .v219-share-actions.three{
  grid-template-columns:repeat(3,minmax(0,1fr));
}
#page-share.v219-share .v219-share-actions .primary{
  width:100%;
  min-width:0;
  min-height:42px;
  margin:0!important;
  border-radius:11px;
  font-size:10px;
  font-weight:900;
}
#page-share.v219-share #whatsappShare{
  background:#dff8e9!important;
  color:#087a41!important;
  box-shadow:none!important;
}
#page-share.v219-share .v219-share-mini-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:10px;
  margin-top:10px;
}
#page-share.v219-share .v219-mini-card{
  min-width:0;
  padding:13px;
  border:1px solid var(--v219-line);
  border-radius:16px;
  background:#fff;
  box-shadow:0 6px 18px rgba(15,73,120,.05);
}
#page-share.v219-share .v219-mini-head{
  display:flex;gap:9px;align-items:flex-start;
}
#page-share.v219-share .v219-mini-icon{
  width:34px;height:34px;min-width:34px;
  display:grid;place-items:center;border-radius:10px;
  background:#eaf4ff;color:#0877df;
}
#page-share.v219-share .v219-mini-icon svg{
  width:19px;height:19px;stroke:currentColor;fill:none;stroke-width:1.9;
}
#page-share.v219-share .v219-mini-card h3{
  margin:0 0 2px;color:#143c69;font-size:13px;font-weight:950;
}
#page-share.v219-share .v219-mini-card .big{
  margin:0 0 4px;color:#153e6f;font-size:14px!important;font-weight:900;
}
#page-share.v219-share .v219-mini-card small,
#page-share.v219-share .v219-mini-card .note{
  color:var(--v219-muted);font-size:9px!important;line-height:1.35!important;
}
#page-share.v219-share #shareSourceInfo{
  padding:0!important;
  margin:0!important;
  border:0!important;
  background:transparent!important;
  box-shadow:none!important;
  color:#526b85;
  font-size:8.6px;
  line-height:1.42;
}
#page-share.v219-share .v219-usage{
  margin-top:10px;
  padding:12px 14px;
  border:1px solid var(--v219-line);
  border-radius:16px;
  background:#fff;
}
#page-share.v219-share .v219-usage-title{
  display:flex;gap:8px;align-items:center;
  margin-bottom:5px;color:#143d6c;font-size:13px;font-weight:950;
}
#page-share.v219-share .v219-usage-title span{
  width:28px;height:28px;display:grid;place-items:center;border-radius:9px;background:#eaf4ff;color:#0878e8;
}
#page-share.v219-share .v219-usage .note{
  color:var(--v219-muted);font-size:9px!important;line-height:1.5!important;
}

/* =========================================================
   USUARIOS · OPCIÓN 3
   ========================================================= */
#page-users.v219-users .v219-password-card{
  display:flex;
  align-items:center;
  gap:12px;
  padding:13px 14px;
  margin:0 0 10px;
  border:1px solid var(--v219-line);
  border-radius:17px;
  background:linear-gradient(135deg,#eef7ff,#f8fbff);
  cursor:pointer;
}
#page-users.v219-users .v219-password-icon{
  width:42px;height:42px;min-width:42px;
  display:grid;place-items:center;
  border-radius:13px;
  color:#fff;
  background:linear-gradient(135deg,#0b75dc,#0c95ff);
  box-shadow:0 7px 18px rgba(8,121,232,.20);
}
#page-users.v219-users .v219-password-icon svg{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.9}
#page-users.v219-users .v219-password-copy{min-width:0;flex:1}
#page-users.v219-users .v219-password-copy b{
  display:block;color:#153f70;font-size:14px;font-weight:950;
}
#page-users.v219-users .v219-password-copy small{
  display:block;margin-top:3px;color:var(--v219-muted);font-size:10px;font-weight:650;
}
#page-users.v219-users .v219-password-chevron{
  color:#0b73d7;font-size:22px;font-weight:900;
}
#page-users.v219-users .v219-password-card #changeMyPasswordBtn{
  position:absolute!important;
  width:1px!important;height:1px!important;overflow:hidden!important;
  clip:rect(0 0 0 0)!important;clip-path:inset(50%)!important;
  white-space:nowrap!important;
}

#page-users.v219-users #tabVisibilityPanel{
  padding:14px!important;
  border:1px solid var(--v219-line)!important;
  border-radius:18px!important;
  background:#fff!important;
  box-shadow:0 7px 22px rgba(15,73,120,.06)!important;
}
#page-users.v219-users .v219-tabs-head{
  display:flex;gap:11px;align-items:flex-start;margin-bottom:10px;
}
#page-users.v219-users .v219-tabs-head-icon{
  width:40px;height:40px;min-width:40px;
  display:grid;place-items:center;
  border-radius:12px;
  background:#e9f4ff;color:#0879e8;
}
#page-users.v219-users .v219-tabs-head-icon svg{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.9}
#page-users.v219-users .v219-tabs-head h2{
  margin:0;color:#143d6c;font-size:17px;line-height:1.1;font-weight:950;
}
#page-users.v219-users .v219-tabs-head p{
  margin:4px 0 0;color:var(--v219-muted);font-size:10px;line-height:1.36;font-weight:650;
}
#page-users.v219-users #tabVisibilityPanel > .title,
#page-users.v219-users #tabVisibilityPanel > .subtitle{
  display:none!important;
}
#page-users.v219-users #tabVisibilityOptions{
  display:block!important;
  margin:0!important;
}
#page-users.v219-users #tabVisibilityOptions label.field{
  position:relative;
  display:flex!important;
  align-items:center!important;
  gap:10px!important;
  width:100%!important;
  min-width:0!important;
  margin:0!important;
  padding:8px 0!important;
  border:0!important;
  border-bottom:1px solid #edf2f7!important;
  border-radius:0!important;
  background:transparent!important;
  box-shadow:none!important;
}
#page-users.v219-users #tabVisibilityOptions label.field:last-child{border-bottom:0!important}
#page-users.v219-users .v219-tab-icon{
  width:34px;height:34px;min-width:34px;
  display:grid;place-items:center;
  border-radius:10px;
  color:#0b78df;
  background:#eaf4ff;
}
#page-users.v219-users .v219-tab-icon.green{color:#0d8b61;background:#e4f8ef}
#page-users.v219-users .v219-tab-icon.purple{color:#784ce8;background:#f0eaff}
#page-users.v219-users .v219-tab-icon.orange{color:#dd7b05;background:#fff0d9}
#page-users.v219-users .v219-tab-icon.pink{color:#d7437c;background:#ffe7f1}
#page-users.v219-users .v219-tab-icon.money{color:#087a41;background:#def7e8}
#page-users.v219-users .v219-tab-icon svg{width:19px;height:19px;stroke:currentColor;fill:none;stroke-width:1.9}
#page-users.v219-users #tabVisibilityOptions label.field > span:not(.v219-tab-icon){
  min-width:0;flex:1;
  color:#173e6b;
  font-size:12px!important;
  line-height:1.2;
  font-weight:850;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]{
  appearance:none!important;
  -webkit-appearance:none!important;
  position:relative!important;
  order:3!important;
  flex:0 0 42px!important;
  width:42px!important;
  min-width:42px!important;
  height:24px!important;
  margin:0!important;
  border:0!important;
  border-radius:999px!important;
  background:#cad7e5!important;
  outline:0!important;
  cursor:pointer!important;
  transition:.18s ease!important;
  box-shadow:inset 0 0 0 1px rgba(33,70,106,.06)!important;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]::after{
  content:""!important;
  position:absolute!important;
  top:3px!important;left:3px!important;
  width:18px!important;height:18px!important;
  border-radius:50%!important;
  background:#fff!important;
  box-shadow:0 2px 5px rgba(12,49,84,.22)!important;
  transition:.18s ease!important;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]:checked{
  background:#0b88f6!important;
}
#page-users.v219-users #tabVisibilityOptions input[type="checkbox"][data-tab-setting]:checked::after{
  transform:translateX(18px)!important;
}
#page-users.v219-users #saveTabVisibility{
  width:100%;
  min-height:42px;
  margin-top:10px;
  border-radius:11px;
  font-size:11px;
  font-weight:900;
}

/* El resto de administración de usuarios continúa debajo sin perder funciones. */
#page-users.v219-users > .subtitle{
  margin-top:14px;
}
#page-users.v219-users > .panel:not(.superOnly){
  border-radius:18px;
}

/* =========================================================
   MÓVIL · replica el boceto Opción 3
   ========================================================= */
@media(max-width:900px){
  #page-share,#page-users{max-width:none}
  #page-share.v219-share .v219-share-intro{
    grid-template-columns:76px 1fr;
    gap:12px;
    padding:13px;
    border-radius:17px;
  }
  #page-share.v219-share .v219-share-intro-icon{
    width:68px;height:68px;border-radius:17px;
  }
  #page-share.v219-share .v219-share-intro-icon svg{width:38px;height:38px}
  #page-share.v219-share .v219-share-intro h2{font-size:20px}
  #page-share.v219-share .v219-share-intro p{font-size:10px}
  #page-share.v219-share .v219-share-card{padding:12px;border-radius:16px}
  #page-share.v219-share .v219-share-actions.three{grid-template-columns:repeat(3,minmax(0,1fr))}
  #page-share.v219-share .v219-share-actions .primary{
    padding:8px 5px!important;
    min-height:40px;
    font-size:9px;
  }
  #page-share.v219-share .v219-share-mini-grid{grid-template-columns:1fr 1fr;gap:7px}
  #page-share.v219-share .v219-mini-card{padding:10px;border-radius:14px}
  #page-share.v219-share .v219-mini-card h3{font-size:11px}
  #page-share.v219-share .v219-mini-card .big{font-size:12px!important}
  #page-share.v219-share #shareSourceInfo{font-size:7.8px}
  #page-users.v219-users .v219-password-card{padding:11px 12px}
  #page-users.v219-users #tabVisibilityPanel{padding:12px!important}
}
@media(max-width:390px){
  #page-share.v219-share .v219-share-actions.three{
    grid-template-columns:1fr 1fr 1fr;
  }
  #page-share.v219-share .v219-share-actions .primary{
    font-size:8.2px;
    padding-left:3px!important;padding-right:3px!important;
  }
}
</style>"""

    js = r"""<script id="v219-share-users-option3-js">
(function(){
  if(window.__V219_SHARE_USERS_OPTION3)return;
  window.__V219_SHARE_USERS_OPTION3=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const svg={
    phone:'<svg viewBox="0 0 24 24"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M9 5h6M10 19h4"/><path d="M8.5 13.5 11 11m2-2 2.5-2.5M10 14l4-4"/></svg>',
    globe:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21M12 3C9.5 5.5 8.5 8.5 8.5 12s1 6.5 3.5 9"/></svg>',
    wifi:'<svg viewBox="0 0 24 24"><path d="M3 9a14 14 0 0 1 18 0M6 12a9 9 0 0 1 12 0M9.5 15.5a4 4 0 0 1 5 0"/><circle cx="12" cy="19" r="1"/></svg>',
    copy:'<svg viewBox="0 0 24 24"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>',
    refresh:'<svg viewBox="0 0 24 24"><path d="M20 6v5h-5"/><path d="M4 18v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9M5.5 15A7 7 0 0 0 18 17.5L20 15"/></svg>',
    file:'<svg viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5M10 12h5M10 16h5"/></svg>',
    lock:'<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2"/></svg>',
    chart:'<svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V5M16 20v-8M22 20H2"/></svg>',
    home:'<svg viewBox="0 0 24 24"><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></svg>',
    calendar:'<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/></svg>',
    trend:'<svg viewBox="0 0 24 24"><path d="m4 17 5-5 4 4 7-8"/><path d="M16 8h4v4"/></svg>',
    money:'<svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M16 7.5c-.8-.8-2-1.2-3.5-1.2-2 0-3.5 1-3.5 2.5 0 3.5 7 1.8 7 5.2 0 1.6-1.5 2.7-3.7 2.7-1.5 0-2.9-.5-3.8-1.3"/></svg>',
    store:'<svg viewBox="0 0 24 24"><path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/></svg>',
    target:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/></svg>'
  };

  function buildShare(){
    const page=q('#page-share');
    if(!page||page.dataset.v219Built==='1')return;
    page.dataset.v219Built='1';
    page.classList.add('v219-share');
    page.innerHTML=
      '<section class="v219-share-intro">'+
        '<div class="v219-share-intro-icon">'+svg.phone+'</div>'+
        '<div><h2>Comparte tu sistema</h2><p>Da acceso a Operaciones Ropa desde cualquier lugar. Copia las ligas o compártelas por WhatsApp.</p></div>'+
      '</section>'+
      '<section class="v219-share-card">'+
        '<div class="v219-card-head"><span class="v219-card-icon">'+svg.globe+'</span><div><h3>Liga pública</h3><p>Acceso desde cualquier red cuando el sistema esté desplegado.</p></div></div>'+
        '<div class="v219-urlbox"><div class="big" id="publicShareUrl">No configurada en este equipo</div><button class="v219-copy-mini" id="v219CopyPublicMini" type="button" aria-label="Copiar liga pública">'+svg.copy+'</button></div>'+
        '<div class="v219-share-actions"><button class="primary" id="copyPublicUrl">Copiar liga pública</button></div>'+
      '</section>'+
      '<section class="v219-share-card">'+
        '<div class="v219-card-head"><span class="v219-card-icon">'+svg.wifi+'</span><div><h3>Prueba en el mismo Wi‑Fi</h3><p>Abre esta liga en el celular conectado al mismo Wi‑Fi.</p></div></div>'+
        '<div class="v219-urlbox"><div class="big" id="lanShareUrl">—</div><button class="v219-copy-mini" id="v219CopyLanMini" type="button" aria-label="Copiar liga Wi-Fi">'+svg.copy+'</button></div>'+
        '<div class="v219-share-actions three"><button class="primary" id="copyLanUrl">Copiar</button><button class="primary" id="shareBestUrl">Compartir</button><button class="primary" id="whatsappShare">WhatsApp</button></div>'+
      '</section>'+
      '<div class="v219-share-mini-grid">'+
        '<section class="v219-mini-card"><div class="v219-mini-head"><span class="v219-mini-icon">'+svg.refresh+'</span><div><h3>Actualizaciones</h3><div class="big">Misma liga</div><small>Al actualizar reportes o diseño no cambia la URL; los usuarios sólo refrescan la página.</small></div></div></section>'+
        '<section class="v219-mini-card"><div class="v219-mini-head"><span class="v219-mini-icon">'+svg.file+'</span><div style="min-width:0"><h3>Estado</h3><div id="shareSourceInfo">Cargando...</div></div></div></section>'+
      '</div>'+
      '<section class="v219-usage"><div class="v219-usage-title"><span>?</span>Uso</div><div class="note">1. Liga Wi‑Fi: prueba interna.<br>2. Liga pública: para tiendas y móviles desde cualquier lugar.<br>3. La liga pública se puede mandar por WhatsApp, correo o QR.</div></section>';

    // Los mini botones copian usando el botón principal para conservar la
    // misma fuente de verdad y el mismo handler que renderShareInfo asigna.
    q('#v219CopyPublicMini')?.addEventListener('click',()=>q('#copyPublicUrl')?.click());
    q('#v219CopyLanMini')?.addEventListener('click',()=>q('#copyLanUrl')?.click());
  }

  const palette=['','green','purple','orange','pink','money','purple',''];
  function iconForLabel(label){
    const s=String(label||'').toLowerCase();
    if(s.includes('centro'))return svg.home;
    if(s.includes('día')||s.includes('dia')||s.includes('semanal'))return svg.calendar;
    if(s.includes('mensual')||s.includes('productividad'))return svg.chart;
    if(s.includes('convers'))return svg.trend;
    if(s.includes('recuperación $')||s.includes('recuperacion $'))return svg.money;
    if(s.includes('tienda'))return svg.store;
    if(s.includes('score')||s.includes('índice')||s.includes('indice'))return svg.target;
    return svg.chart;
  }

  function decorateVisibility(){
    const box=q('#tabVisibilityOptions');
    if(!box)return;
    qa(':scope > label.field',box).forEach((row,i)=>{
      if(row.querySelector(':scope > .v219-tab-icon'))return;
      const text=row.querySelector(':scope > span:not(.v219-tab-icon)')?.textContent||row.textContent||'';
      const icon=document.createElement('span');
      icon.className='v219-tab-icon '+(palette[i%palette.length]||'');
      icon.innerHTML=iconForLabel(text);
      row.prepend(icon);
    });
  }

  function buildUsers(){
    const page=q('#page-users');
    if(!page||page.dataset.v219Built==='1')return;
    page.dataset.v219Built='1';
    page.classList.add('v219-users');

    const title=page.querySelector(':scope > .title');
    const passwordPanel=page.querySelector(':scope > .panel.superOnly');
    const tabs=q('#tabVisibilityPanel',page);
    if(title)title.textContent='Usuarios';

    if(passwordPanel && !passwordPanel.querySelector('.v219-password-card')){
      const btn=q('#changeMyPasswordBtn',passwordPanel);
      const msg=q('#myPasswordMsg',passwordPanel);
      const card=document.createElement('div');
      card.className='v219-password-card';
      card.setAttribute('role','button');
      card.setAttribute('tabindex','0');
      card.innerHTML='<span class="v219-password-icon">'+svg.lock+'</span><span class="v219-password-copy"><b>Cambiar mi contraseña</b><small>Actualiza tu contraseña de acceso de forma segura.</small></span><span class="v219-password-chevron">›</span>';
      if(btn)card.appendChild(btn);
      if(msg)card.appendChild(msg);
      card.addEventListener('click',e=>{if(e.target!==btn)btn?.click()});
      card.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();btn?.click()}});
      passwordPanel.innerHTML='';
      passwordPanel.appendChild(card);
      passwordPanel.style.padding='0';
      passwordPanel.style.border='0';
      passwordPanel.style.background='transparent';
      passwordPanel.style.boxShadow='none';
    }

    if(tabs && !tabs.querySelector('.v219-tabs-head')){
      const head=document.createElement('div');
      head.className='v219-tabs-head';
      head.innerHTML='<span class="v219-tabs-head-icon">'+svg.chart+'</span><div><h2>Pestañas visibles en los reportes</h2><p>Desmarca una pestaña para ocultarla a todos los usuarios. La carga de datos y la administración permanecen protegidas por rol.</p></div>';
      tabs.prepend(head);
    }
    decorateVisibility();
  }

  function refresh(){
    buildShare();
    buildUsers();
    decorateVisibility();
  }

  const mo=new MutationObserver(muts=>{
    if(muts.some(x=>x.type==='childList'))setTimeout(decorateVisibility,0);
  });

  function init(){
    refresh();
    const box=q('#tabVisibilityOptions');
    if(box)mo.observe(box,{childList:true,subtree:false});
    [120,450,1200].forEach(ms=>setTimeout(refresh,ms));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
  window.addEventListener('pageshow',()=>setTimeout(refresh,80),{passive:true});
  console.info('[V219] Compartir y Usuarios · Opción 3 aplicada.');
})();
</script>"""

    @m.app.middleware("http")
    async def v219_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v219-share-users-option3-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v219-share-users-option3-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V219-OPTION3",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V219] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V219_SHARE_USERS_OPTION3 = True
    print("[V219] Compartir sistema + Usuarios · Opción 3 aplicada.",flush=True)
