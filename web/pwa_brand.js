(() => {
  'use strict';
  // V395: imagen original de Price Shoes; no usar el icono viejo de Operaciones.
  // Una sola fuente, con cache busting, para pantalla de acceso y reportes.
  const brandLogo = '/static/price_shoes_logo.png?v=395';
  const iconFallback = '/static/app-icon-192.svg?v=395';
  const selector = '.login-logo-v15, #sidebar .sidebrand img, .main>.hero .or-report-brand img';
  const applyBrand = () => {
    document.querySelectorAll(selector).forEach(img => {
      if (img.dataset.priceFallback !== '1' && img.getAttribute('src') !== brandLogo) {
        img.src = brandLogo;
      }
      img.alt = 'Price Shoes';
      img.setAttribute('aria-label', 'Price Shoes');
      img.decoding = 'async';
    });
    const loginSub = document.querySelector('.login-sub-v15');
    if (loginSub && loginSub.textContent.trim() !== 'Operaciones Ropa')
      loginSub.textContent = 'Operaciones Ropa';
  };

  // Guardar dimensiones antes de que cargue la imagen evita el salto del login.
  const stabilizeImage = img => {
    if (img.dataset.priceBound === '1') return;
    img.dataset.priceBound = '1';
    img.addEventListener('error', () => {
      if (img.dataset.priceFallback === '1') return;
      img.dataset.priceFallback = '1';
      img.src = iconFallback; // también contiene el logo de Price Shoes
    });
    if (img.classList.contains('login-logo-v15')) {
      img.width = 211;
      img.height = 121;
    }
  };
  const ensure = () => {
    document.querySelectorAll(selector).forEach(stabilizeImage);
    applyBrand();
  };

  const begin = () => {
    ensure();
    // Los paneles pueden re-renderizarse al cambiar de pestaña/rol.
    // Observar SOLO los nodos de marca evita afectar los reportes y sus tablas.
    for (const selectorRoot of ['#loginView', '#sidebar', '#appView .main>.hero']) {
      const root = document.querySelector(selectorRoot);
      if (!root) continue;
      const observer = new MutationObserver(mutations => {
        if (mutations.some(m => m.type === 'childList' ||
            (m.type === 'attributes' && m.target.matches?.(selector)))) {
          ensure();
        }
      });
      observer.observe(root, {subtree: true, childList: true,
        attributes: true, attributeFilter: ['src']});
    }
    window.addEventListener('pageshow', ensure);
  };
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', begin, {once: true});
  else begin();

  // Splash acotado: nunca tapa indefinidamente el login si falla alguna petición.
  const splash = document.createElement('div');
  splash.id = 'orSplash';
  splash.setAttribute('aria-hidden', 'true');
  splash.innerHTML = `
    <div class="or-splash-inner">
      <div class="or-splash-logo-wrap"><img class="or-splash-logo" src="${brandLogo}" alt="Price Shoes" width="211" height="121"></div>
      <div class="or-splash-name">OPERACIONES <span>ROPA</span></div>
      <div class="or-splash-loading"><i></i></div>
      <div class="or-splash-caption">Conectando con el sistema...</div>
    </div>`;
  document.body.prepend(splash);
  let closed = false;
  const hideSplash = () => {
    if (closed) return;
    closed = true;
    splash.classList.add('or-splash-hide');
    window.setTimeout(() => splash.remove(), 290);
  };
  // Esperar al DOM (no a todos los scripts, imágenes y reportes).
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', () => window.setTimeout(hideSplash, 250), {once: true});
  else window.setTimeout(hideSplash, 250);
  window.setTimeout(hideSplash, 2200); // respaldo contra fallos de carga
})();
