(() => {
  // Precio Shoes: mantener el mismo logotipo en acceso, carga y reportes.
  const brandLogo = '/static/price_shoes_logo.png?v=380';
  const splash = document.createElement('div');
  splash.id = 'orSplash';
  splash.innerHTML = `
    <div class="or-splash-inner">
      <div class="or-splash-logo-wrap"><img class="or-splash-logo" src="${brandLogo}" alt="Price Shoes"></div>
      <div class="or-splash-name">OPERACIONES <span>ROPA</span></div>
      <div class="or-splash-loading"><i></i></div>
      <div class="or-splash-caption">Cargando tu información...</div>
    </div>`;
  document.body.prepend(splash);

  const hideSplash = () => {
    window.setTimeout(() => {
      splash.classList.add('or-splash-hide');
      window.setTimeout(() => splash.remove(), 320);
    }, 700);
  };
  if (document.readyState === 'complete') hideSplash();
  else window.addEventListener('load', hideSplash, { once:true });

  const applyBrand = () => {
    const loginLogo = document.querySelector('.login-logo-v15');
    if (loginLogo) {
      loginLogo.src = brandLogo;
      loginLogo.alt = 'Price Shoes';
    }
    const loginSub = document.querySelector('.login-sub-v15');
    if (loginSub) loginSub.textContent = 'Operaciones Ropa';
    document.querySelectorAll('.sidebrand img').forEach(img => {
      img.src = brandLogo;
      img.alt = 'Price Shoes';
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBrand, { once:true });
  } else {
    applyBrand();
  }
})();
