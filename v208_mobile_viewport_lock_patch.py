"""V208 · bloqueo de rebote móvil + orientación responsive global.

Corrige:
- texto literal \\n visible sobre el login al hacer overscroll;
- rebote/arrastre de la pantalla raíz en iPhone/iPad/Chrome Android;
- reflow de reportes al rotar entre vertical y horizontal;
- posición del aviso de instalación cerca del borde inferior del navegador.

No modifica datos, endpoints, cálculos, roles ni persistencia.
"""
from __future__ import annotations

from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V208_MOBILE_VIEWPORT_LOCK", False):
        return

    css = r'''<style id="v208-mobile-viewport-lock-css">
:root{
  --or-app-vh:100dvh;
  --or-app-vw:100vw;
}

/* El documento no debe mostrar contenido fuera del viewport al rebotar. */
html.or-mobile-shell,
html.or-mobile-shell body{
  width:100%!important;
  max-width:100%!important;
  overscroll-behavior-x:none!important;
  overscroll-behavior-y:none!important;
}
html.or-mobile-shell body{
  overflow-x:hidden!important;
  background:#f3f6fa!important;
}
html.or-mobile-shell #appView{
  min-height:var(--or-app-vh)!important;
}

/* Login: la pantalla raíz queda fija; si falta altura, sólo se desplaza la tarjeta. */
html.or-login-locked,
html.or-login-locked body{
  width:100%!important;
  height:var(--or-app-vh)!important;
  min-height:var(--or-app-vh)!important;
  max-height:var(--or-app-vh)!important;
  overflow:hidden!important;
  overscroll-behavior:none!important;
}
html.or-login-locked #loginView.login-v15{
  position:fixed!important;
  inset:0!important;
  width:100%!important;
  height:var(--or-app-vh)!important;
  min-height:0!important;
  max-height:var(--or-app-vh)!important;
  overflow:hidden!important;
  overscroll-behavior:none!important;
}
html.or-login-locked #loginView .login-v15-card{
  max-height:calc(var(--or-app-vh) - 12px - env(safe-area-inset-top) - env(safe-area-inset-bottom))!important;
  overflow-y:auto!important;
  overflow-x:hidden!important;
  overscroll-behavior:contain!important;
  -webkit-overflow-scrolling:touch!important;
  scrollbar-width:none!important;
}
html.or-login-locked #loginView .login-v15-card::-webkit-scrollbar{display:none!important}

/* V196 deja overscroll:auto para Android. Aquí sólo quitamos el rebote,
   sin tocar el pan vertical de un dedo. */
html.or-mobile-shell.android-one-finger-scroll,
html.or-mobile-shell.android-one-finger-scroll body,
html.or-mobile-shell.android-one-finger-scroll .shell,
html.or-mobile-shell.android-one-finger-scroll .main,
html.or-mobile-shell.android-one-finger-scroll section.page,
html.or-mobile-shell.android-one-finger-scroll section.page.active{
  overscroll-behavior-y:none!important;
}

/* Aviso PWA: pegado al borde útil inferior, justo sobre la barra del navegador. */
@media(max-width:900px){
  .pwa-install-hint{
    left:8px!important;
    right:8px!important;
    bottom:max(6px,env(safe-area-inset-bottom))!important;
    max-width:560px!important;
    margin:0 auto!important;
    z-index:29000!important;
    padding:9px 10px!important;
    border-radius:14px!important;
    transform:translateZ(0);
  }
  .pwa-install-hint img{
    width:42px!important;
    height:42px!important;
    flex-basis:42px!important;
    border-radius:11px!important;
  }
  .pwa-install-hint strong{font-size:11px!important;margin-bottom:2px!important}
  .pwa-install-hint span{font-size:9px!important;line-height:1.28!important}
  .pwa-install-close{
    width:32px!important;
    height:32px!important;
    flex-basis:32px!important;
  }
  .pwa-install-action{
    min-height:34px!important;
    padding:7px 10px!important;
    font-size:9px!important;
  }
}

/* ===============================================================
   MÓVIL HORIZONTAL · regla global para todos los reportes
   =============================================================== */
@media(max-width:900px) and (orientation:landscape){
  html.or-mobile-landscape .main{
    padding:3px 5px calc(54px + env(safe-area-inset-bottom))!important;
  }
  html.or-mobile-landscape .hero{
    min-height:44px!important;
    padding:6px 44px 6px 10px!important;
    border-radius:11px!important;
  }
  html.or-mobile-landscape .hero h1{
    font-size:14px!important;
    line-height:1.05!important;
  }
  html.or-mobile-landscape .hero p,
  html.or-mobile-landscape .hero-greeting{
    font-size:7px!important;
    line-height:1.15!important;
  }

  /* Navegación interna: más compacta, conserva carrusel y centrado. */
  html.or-mobile-landscape #operativoNav:not(.hidden),
  html.or-mobile-landscape #analysisNav:not(.hidden),
  html.or-mobile-landscape #v200OperationTabs{
    min-height:56px!important;
    gap:4px!important;
    padding:3px max(10px,calc((100vw - 70px)/2)) 7px!important;
    margin:0 -5px 3px!important;
    scroll-padding-inline:calc((100vw - 70px)/2)!important;
  }
  html.or-mobile-landscape #operativoNav>button,
  html.or-mobile-landscape #analysisNav>button,
  html.or-mobile-landscape #v200OperationTabs>button{
    flex:0 0 70px!important;
    width:70px!important;
    min-width:70px!important;
    max-width:70px!important;
    height:51px!important;
    min-height:51px!important;
    max-height:51px!important;
    padding:3px 2px 4px!important;
    font-size:6.2px!important;
    border-radius:11px!important;
  }
  html.or-mobile-landscape #operativoNav .v206-tab-icon,
  html.or-mobile-landscape #analysisNav .v206-tab-icon,
  html.or-mobile-landscape #v200OperationTabs .v203-tab-icon{
    width:27px!important;
    min-width:27px!important;
    max-width:27px!important;
    height:27px!important;
    min-height:27px!important;
    max-height:27px!important;
  }
  html.or-mobile-landscape #operativoNav .v206-tab-icon svg,
  html.or-mobile-landscape #analysisNav .v206-tab-icon svg,
  html.or-mobile-landscape #v200OperationTabs .v203-tab-icon svg{
    width:14px!important;
    height:14px!important;
  }

  html.or-mobile-landscape .v207-context-header{
    margin:2px 0 7px!important;
  }
  html.or-mobile-landscape .v207-context-title,
  html.or-mobile-landscape .title{
    font-size:16px!important;
    line-height:1.08!important;
    margin-top:5px!important;
    margin-bottom:4px!important;
  }
  html.or-mobile-landscape .v207-context-sub,
  html.or-mobile-landscape .subtitle{
    font-size:7.5px!important;
    line-height:1.25!important;
    margin-bottom:5px!important;
  }

  /* KPIs: aprovechar el ancho extra del teléfono horizontal. */
  html.or-mobile-landscape .kpis,
  html.or-mobile-landscape .report-kpis,
  html.or-mobile-landscape .v149-kpis,
  html.or-mobile-landscape .v126-kpis,
  html.or-mobile-landscape .v125-kpis,
  html.or-mobile-landscape .v164-matrix-kpis,
  html.or-mobile-landscape .v165-mini-kpis,
  html.or-mobile-landscape .v168-plan-kpis,
  html.or-mobile-landscape .sales-kpi-grid,
  html.or-mobile-landscape .lingerie-kpis,
  html.or-mobile-landscape .v201-demo-grid{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:5px!important;
  }
  html.or-mobile-landscape .kpi,
  html.or-mobile-landscape .report-kpi,
  html.or-mobile-landscape .v149-kpi,
  html.or-mobile-landscape .v126-kpi,
  html.or-mobile-landscape .v125-kpi,
  html.or-mobile-landscape .v164-matrix-kpi,
  html.or-mobile-landscape .v165-mini-kpi,
  html.or-mobile-landscape .v168-plan-kpi,
  html.or-mobile-landscape .sales-kpi,
  html.or-mobile-landscape .v201-demo-kpi{
    min-height:74px!important;
    padding-top:7px!important;
    padding-bottom:6px!important;
  }
  html.or-mobile-landscape .val,
  html.or-mobile-landscape .report-kpi .rk-value,
  html.or-mobile-landscape .v149-kpi b,
  html.or-mobile-landscape .v126-kpi b,
  html.or-mobile-landscape .v125-kpi b,
  html.or-mobile-landscape .sales-kpi .sv{
    font-size:clamp(16px,3.2vw,22px)!important;
  }

  /* Tarjetas y filtros usan más columnas al rotar. */
  html.or-mobile-landscape .cards{
    grid-template-columns:repeat(3,minmax(0,1fr))!important;
    gap:5px!important;
  }
  html.or-mobile-landscape #globalFilters.filters,
  html.or-mobile-landscape .filters,
  html.or-mobile-landscape .v161-filter-grid{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:4px!important;
  }
  html.or-mobile-landscape #operativoPeriodBar.or-report-filter-card>.or-report-filter-grid{
    grid-template-columns:repeat(6,minmax(0,1fr))!important;
    gap:4px!important;
  }

  /* Tablas y gráficas: ancho completo y scroll táctil propio. */
  html.or-mobile-landscape .tablewrap,
  html.or-mobile-landscape .model-sticky-table,
  html.or-mobile-landscape .model-scroll-30,
  html.or-mobile-landscape .table-scroll-35,
  html.or-mobile-landscape .chart-scroll,
  html.or-mobile-landscape .sales-chart-scroll,
  html.or-mobile-landscape .v168-pivot-wrap,
  html.or-mobile-landscape .v168-plan-matrix{
    max-width:100%!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior:contain!important;
  }
  html.or-mobile-landscape .panel,
  html.or-mobile-landscape .card,
  html.or-mobile-landscape .chart-box{
    padding:7px!important;
  }

  /* Login horizontal: se comprime; si aún falta altura, scroll sólo dentro de la tarjeta. */
  html.or-mobile-landscape #loginView.login-v15{
    padding:4px 8px!important;
    align-items:flex-start!important;
    justify-content:center!important;
  }
  html.or-mobile-landscape .login-v15-card{
    width:min(720px,calc(100vw - 18px))!important;
    max-height:calc(var(--or-app-vh) - 8px)!important;
    padding:8px 16px 10px!important;
  }
  html.or-mobile-landscape .login-logo-v15{
    width:82px!important;
    margin:0 auto 2px!important;
  }
  html.or-mobile-landscape .login-sub-v15{
    margin:0 0 7px!important;
    font-size:9px!important;
  }
  html.or-mobile-landscape .login-sub-v15:after{
    margin-top:2px!important;
    font-size:9px!important;
  }
  html.or-mobile-landscape .login-form-v15{gap:6px!important}
  html.or-mobile-landscape .login-field-v15{
    min-height:38px!important;
  }
  html.or-mobile-landscape .login-field-v15 input{
    min-height:36px!important;
    padding:5px 6px!important;
    font-size:11px!important;
  }
  html.or-mobile-landscape .login-help-v15{
    margin-top:7px!important;
    gap:5px!important;
    font-size:10px!important;
  }
  html.or-mobile-landscape .server-msg-v15,
  html.or-mobile-landscape .login-msg-v15{
    min-height:12px!important;
    margin-top:2px!important;
    font-size:8px!important;
  }

  html.or-mobile-landscape .pwa-install-hint{
    left:6px!important;
    right:6px!important;
    bottom:max(4px,env(safe-area-inset-bottom))!important;
    max-width:620px!important;
    padding:7px 9px!important;
    gap:8px!important;
  }
  html.or-mobile-landscape .pwa-install-hint img{
    width:36px!important;height:36px!important;flex-basis:36px!important;
  }
  html.or-mobile-landscape .pwa-install-hint strong{font-size:10px!important}
  html.or-mobile-landscape .pwa-install-hint span{font-size:8px!important}
}

/* Chrome Android y Safari iOS comparten la misma regla de borde inferior. */
html.or-android-chrome .pwa-install-hint,
html.or-ios-safari .pwa-install-hint{
  bottom:max(6px,env(safe-area-inset-bottom))!important;
}
</style>'''

    js = r'''<script id="v208-mobile-viewport-lock-js">
(function(){
  if(window.__V208_MOBILE_VIEWPORT_LOCK)return;
  window.__V208_MOBILE_VIEWPORT_LOCK=true;

  const root=document.documentElement;
  const ua=navigator.userAgent||'';
  const isIOS=/iPad|iPhone|iPod/i.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  const isAndroid=/Android/i.test(ua);
  const isChrome=/Chrome|CriOS/i.test(ua) && !/EdgA|OPR/i.test(ua);
  const isSafari=isIOS && /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/i.test(ua);

  root.classList.toggle('or-ios-safari',isSafari);
  root.classList.toggle('or-android-chrome',isAndroid&&isChrome);

  function mobile(){
    return window.matchMedia('(max-width:900px)').matches || isIOS || isAndroid;
  }
  function loginVisible(){
    const el=document.getElementById('loginView');
    return !!el && !el.classList.contains('hidden');
  }
  function activeTabCenter(){
    [
      document.querySelector('#operativoNav>button.active:not(.hidden):not([hidden])'),
      document.querySelector('#analysisNav>button.active:not(.hidden):not([hidden])'),
      document.querySelector('#v200OperationTabs>button.active:not(.hidden):not([hidden])')
    ].filter(Boolean).forEach(btn=>{
      try{btn.scrollIntoView({behavior:'auto',block:'nearest',inline:'center'})}catch(_){}
    });
  }

  let raf=0;
  function syncViewport(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      const vv=window.visualViewport;
      const h=Math.max(1,Math.round(vv?.height||window.innerHeight||document.documentElement.clientHeight||1));
      const w=Math.max(1,Math.round(vv?.width||window.innerWidth||document.documentElement.clientWidth||1));
      const isMobile=mobile();
      const landscape=isMobile && window.matchMedia('(orientation:landscape)').matches;

      root.style.setProperty('--or-app-vh',h+'px');
      root.style.setProperty('--or-app-vw',w+'px');
      root.classList.toggle('or-mobile-shell',isMobile);
      root.classList.toggle('or-mobile-landscape',landscape);
      root.classList.toggle('or-mobile-portrait',isMobile&&!landscape);
      root.classList.toggle('or-login-locked',isMobile&&loginVisible());

      if(isMobile&&loginVisible()){
        if(window.scrollY!==0)window.scrollTo(0,0);
      }
      setTimeout(activeTabCenter,40);
    });
  }

  let lastTouchY=0;
  document.addEventListener('touchstart',event=>{
    if(!mobile()||!event.touches?.length)return;
    lastTouchY=event.touches[0].clientY;
  },{passive:true});

  document.addEventListener('touchmove',event=>{
    if(!mobile()||!event.touches?.length)return;
    const y=event.touches[0].clientY;
    const delta=y-lastTouchY;

    if(root.classList.contains('or-login-locked')){
      const card=event.target.closest?.('.login-v15-card');
      if(!card){
        event.preventDefault();
      }else{
        const canScroll=card.scrollHeight>card.clientHeight+1;
        const atTop=card.scrollTop<=0;
        const atBottom=card.scrollTop+card.clientHeight>=card.scrollHeight-1;
        if(!canScroll || (atTop&&delta>0) || (atBottom&&delta<0)){
          event.preventDefault();
        }
      }
      lastTouchY=y;
      return;
    }

    // En Safari iOS bloquea sólo el tirón hacia abajo cuando ya estamos arriba.
    // El scroll normal hacia el contenido permanece intacto.
    if(isIOS && delta>0 && window.scrollY<=0){
      event.preventDefault();
    }
    lastTouchY=y;
  },{passive:false});

  const login=document.getElementById('loginView');
  if(login){
    new MutationObserver(syncViewport).observe(login,{attributes:true,attributeFilter:['class']});
  }

  window.addEventListener('resize',syncViewport,{passive:true});
  window.addEventListener('orientationchange',()=>{
    syncViewport();
    [80,220,500].forEach(ms=>setTimeout(syncViewport,ms));
  },{passive:true});
  window.visualViewport?.addEventListener('resize',syncViewport,{passive:true});
  window.visualViewport?.addEventListener('scroll',syncViewport,{passive:true});
  window.addEventListener('pageshow',syncViewport,{passive:true});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')syncViewport()});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',syncViewport,{once:true});
  else syncViewport();

  console.info('[V208] viewport móvil bloqueado contra rebote y orientación responsive activa.');
})();
</script>'''

    @m.app.middleware("http")
    async def v208_html(request, call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")

            # Corrige el texto literal "\\n" que quedó entre el CSS y </head>.
            html=html.replace(
                '<link rel="stylesheet" href="/static/design_system.css?v=20260928-mobile-v5">\\n</head>',
                '<link rel="stylesheet" href="/static/design_system.css?v=20260928-mobile-v5">\n</head>'
            )

            # Chrome Android usa esto para recalcular el viewport sin desplazar el shell.
            html=html.replace(
                'content="width=device-width,initial-scale=1,viewport-fit=cover"',
                'content="width=device-width,initial-scale=1,viewport-fit=cover,interactive-widget=resizes-content"',
                1
            )

            if "v208-mobile-viewport-lock-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v208-mobile-viewport-lock-js" not in html:
                html=html.replace("</body>",js+"</body>",1)

            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V208",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V208] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V208_MOBILE_VIEWPORT_LOCK=True
    print("[V208] bloqueo móvil + orientación + PWA inferior instalados.",flush=True)
