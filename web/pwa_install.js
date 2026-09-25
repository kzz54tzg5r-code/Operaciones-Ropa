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

  const isiOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  if (!isiOS || isStandalone()) return;
  if (sessionStorage.getItem('pwa-install-hint-dismissed') === '1') return;

  const style = document.createElement('style');
  style.textContent = `
    .pwa-install-hint{position:fixed;left:10px;right:10px;bottom:calc(76px + env(safe-area-inset-bottom));z-index:19000;
      max-width:520px;margin:0 auto;background:#fff;border:1px solid #dce4ee;border-radius:16px;padding:12px 13px;
      box-shadow:0 14px 40px rgba(18,59,115,.22);display:flex;gap:10px;align-items:flex-start;color:#123b73;
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .pwa-install-hint .pwa-logo{width:42px;height:42px;flex:0 0 42px;border-radius:11px;background:#123b73;color:#fff;
      display:grid;place-items:center;font-weight:900;font-size:21px;box-shadow:inset -9px 0 #e4007f}
    .pwa-install-hint strong{display:block;font-size:12px;margin:1px 0 3px}.pwa-install-hint span{display:block;font-size:10px;line-height:1.35;color:#667085}
    .pwa-install-hint button{border:0;background:#f2f5f9;color:#123b73;border-radius:8px;width:28px;height:28px;font-weight:900;flex:0 0 28px}
    @media(min-width:901px){.pwa-install-hint{display:none!important}}
  `;
  document.head.appendChild(style);

  const hint = document.createElement('div');
  hint.className = 'pwa-install-hint';
  hint.innerHTML = `
    <div class="pwa-logo">R</div>
    <div style="flex:1">
      <strong>Instala Operaciones Ropa</strong>
      <span>En iPhone: Compartir → Añadir a pantalla de inicio → deja activado “Abrir como app web”.</span>
    </div>
    <button type="button" aria-label="Cerrar">×</button>
  `;

  hint.querySelector('button').addEventListener('click', () => {
    sessionStorage.setItem('pwa-install-hint-dismissed', '1');
    hint.remove();
  });

  window.setTimeout(() => document.body.appendChild(hint), 1200);
})();
