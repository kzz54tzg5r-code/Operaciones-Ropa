(() => {
  const isStandalone = () =>
    window.matchMedia?.('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

  document.documentElement.classList.toggle('pwa-standalone', isStandalone());

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js', { scope: '/' }).catch(err => {
        console.warn('[PWA] service worker no registrado:', err);
      });
    });
  }

  if (isStandalone()) return;

  const ua = navigator.userAgent || '';
  const isiOS = /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isAndroid = /Android/i.test(ua);

  let installEvent = null;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installEvent = event;
    if (isAndroid) showAndroidHint();
  });

  const addStyle = () => {
    if (document.getElementById('pwaInstallStyle')) return;
    const style = document.createElement('style');
    style.id = 'pwaInstallStyle';
    style.textContent = `
      .pwa-install-hint{position:fixed;left:10px;right:10px;bottom:calc(76px + env(safe-area-inset-bottom));z-index:19000;
        max-width:520px;margin:0 auto;background:#fff;border:1px solid #dce4ee;border-radius:16px;padding:11px 12px;
        box-shadow:0 14px 40px rgba(18,59,115,.22);display:flex;gap:10px;align-items:center;color:#123b73;
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
      .pwa-install-hint img{width:46px;height:46px;flex:0 0 46px;border-radius:12px}
      .pwa-install-hint strong{display:block;font-size:12px;margin:1px 0 3px}.pwa-install-hint span{display:block;font-size:10px;line-height:1.35;color:#667085}
      .pwa-install-close{border:0;background:#f2f5f9;color:#123b73;border-radius:8px;width:28px;height:28px;font-weight:900;flex:0 0 28px}
      .pwa-install-action{border:0;background:#0d7ff4;color:#fff;border-radius:9px;padding:8px 11px;font-size:10px;font-weight:900;white-space:nowrap}
      @media(min-width:901px){.pwa-install-hint{display:none!important}}
    `;
    document.head.appendChild(style);
  };

  const closeHint = hint => {
    sessionStorage.setItem('pwa-install-hint-dismissed', '1');
    hint?.remove();
  };

  const makeHint = (message, withInstallButton=false) => {
    if (document.querySelector('.pwa-install-hint')) return;
    if (sessionStorage.getItem('pwa-install-hint-dismissed') === '1') return;
    addStyle();
    const hint = document.createElement('div');
    hint.className = 'pwa-install-hint';
    hint.innerHTML = `
      <img src="/static/app-icon-192.svg" alt="Operaciones Ropa">
      <div style="flex:1;min-width:0">
        <strong>Instala Operaciones Ropa</strong>
        <span>${message}</span>
      </div>
      ${withInstallButton ? '<button type="button" class="pwa-install-action">Instalar</button>' : ''}
      <button type="button" class="pwa-install-close" aria-label="Cerrar">×</button>
    `;
    hint.querySelector('.pwa-install-close')?.addEventListener('click', () => closeHint(hint));
    hint.querySelector('.pwa-install-action')?.addEventListener('click', async () => {
      if (!installEvent) return;
      installEvent.prompt();
      try { await installEvent.userChoice; } catch (_) {}
      installEvent = null;
      closeHint(hint);
    });
    document.body.appendChild(hint);
  };

  const showAndroidHint = () =>
    makeHint('En Android toca Instalar para agregarla como aplicación.', true);

  if (isiOS) {
    window.setTimeout(() => makeHint(
      'En iPhone: Compartir → Añadir a pantalla de inicio → deja activado “Abrir como app web”.'
    ), 1500);
  } else if (isAndroid) {
    window.setTimeout(() => {
      if (installEvent) showAndroidHint();
      else makeHint('En Chrome abre el menú ⋮ y elige “Instalar app” o “Agregar a pantalla principal”.');
    }, 1800);
  }

  window.addEventListener('appinstalled', () => {
    document.querySelector('.pwa-install-hint')?.remove();
  });
})();
