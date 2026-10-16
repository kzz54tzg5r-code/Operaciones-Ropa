/* Solo para la rama de prueba en Vercel. No recopila credenciales ni llama a APIs. */
(() => {
  const render = () => {
    if (document.getElementById('vercel-preview-indicator')) return;
    const badge = document.createElement('div');
    badge.id = 'vercel-preview-indicator';
    badge.setAttribute('role', 'status');
    badge.textContent = 'PRUEBA VERCEL · SIN CONEXIÓN A DATOS REALES';
    Object.assign(badge.style, {
      position: 'fixed', bottom: 'calc(7px + env(safe-area-inset-bottom, 0px))',
      left: '8px', zIndex: '2147483000', pointerEvents: 'none',
      font: '600 10px/1.3 system-ui, sans-serif', letterSpacing: '.02em',
      color: '#ffffff', background: 'rgba(10, 37, 65, .84)',
      border: '1px solid rgba(255,255,255,.22)', borderRadius: '7px',
      padding: '5px 8px', maxWidth: 'calc(100vw - 20px)',
      boxShadow: '0 2px 7px rgba(0,0,0,.16)'
    });
    document.body.appendChild(badge);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render, { once: true });
  } else { render(); }
})();
