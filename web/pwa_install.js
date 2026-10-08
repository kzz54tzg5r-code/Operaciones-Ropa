(() => {
  const isStandalone = () =>
    window.matchMedia?.('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

  document.documentElement.classList.toggle('pwa-standalone', isStandalone());

  let swRegistration = null;
  let loadedBuild = null;
  let lastVersionCheck = 0;
  let updateVisible = false;
  let pendingVersion = null;
  let refreshing = false;
  let pendingWrites = 0;
  let lastInteraction = Date.now();
  const edits = new Set();
  const originals = new WeakMap();
  const valueOf = el => ['checkbox', 'radio'].includes(el.type) ? el.checked : el.value;
  const eligible = el => el?.matches?.('input,textarea,select') &&
    !el.closest('#loginView,.filters,.v165-subfilters,.or-filter-panel-v3,#viewRoleBox') &&
    !['hidden', 'button', 'submit'].includes(el.type);
  document.addEventListener('focusin', event => {
    if (eligible(event.target) && !originals.has(event.target)) originals.set(event.target, valueOf(event.target));
  });
  const trackEdit = event => {
    lastInteraction = Date.now();
    const el = event.target;
    if (!eligible(el)) return;
    if (originals.has(el) && valueOf(el) === originals.get(el)) edits.delete(el);
    else edits.add(el);
  };
  document.addEventListener('input', trackEdit);
  document.addEventListener('change', trackEdit);
  document.addEventListener('or:capture-saved', event => {
    const root = event.detail?.root;
    if (!root) return;
    for (const el of edits) if (root.contains(el) || (event.detail.draftKey && el.dataset.orDraftKey === event.detail.draftKey)) {
      edits.delete(el);
      originals.set(el, valueOf(el));
    }
  });
  for (const type of ['pointerdown', 'touchstart', 'keydown']) {
    document.addEventListener(type, () => { lastInteraction = Date.now(); }, { passive: true });
  }
  document.addEventListener('scroll', () => { lastInteraction = Date.now(); }, { passive: true, capture: true });
  // Track writes only; never infer that an unrelated successful request saved a form.
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const method = String(args[1]?.method || args[0]?.method || 'GET').toUpperCase();
    const writing = !['GET', 'HEAD', 'OPTIONS'].includes(method);
    if (writing) pendingWrites++;
    try { return await originalFetch(...args); }
    finally { if (writing) pendingWrites--; }
  };
  const safeToRefresh = () => navigator.onLine !== false && pendingWrites === 0 && edits.size === 0;

  const addSystemStyle = () => {
    if (document.getElementById('pwaSystemStyle')) return;
    const style = document.createElement('style');
    style.id = 'pwaSystemStyle';
    style.textContent = `
      .or-version-badge{display:flex;align-items:center;gap:6px;margin-top:7px;padding:6px 8px;border:1px solid #e1e8f0;
        border-radius:8px;background:#f8fafc;color:#62748a;font-size:8px;font-weight:750;line-height:1.2}
      .or-version-dot{width:7px;height:7px;border-radius:50%;background:#0e9f6e;box-shadow:0 0 0 3px rgba(14,159,110,.10)}
      .or-update-banner{position:fixed;left:10px;right:10px;top:calc(10px + env(safe-area-inset-top));z-index:25000;
        max-width:620px;margin:0 auto;display:flex;align-items:center;gap:10px;padding:10px 11px;border:1px solid #b9dafc;
        border-radius:12px;background:#fff;color:#123b73;box-shadow:0 16px 40px rgba(10,49,91,.20);
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
      .or-update-banner strong{display:block;font-size:11px;margin-bottom:2px}.or-update-banner span{display:block;font-size:9px;color:#66758a;line-height:1.3}
      .or-update-banner button{margin-left:auto;flex:0 0 auto;border:0;border-radius:8px;background:#0d7ff4;color:#fff;
        min-height:34px;padding:0 11px;font-size:9px;font-weight:900;cursor:pointer}
      .or-update-banner button:disabled{opacity:.65}
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

  const renderVersion = version => {
    addSystemStyle();
    const profile = document.querySelector('.profile');
    if (!profile) return;
    let badge = profile.querySelector('.or-version-badge');
    if (!badge) {
      badge = document.createElement('div');
      badge.className = 'or-version-badge';
      profile.appendChild(badge);
    }
    const short = String(version || 'local').slice(0, 8);
    badge.innerHTML = '<span class="or-version-dot"></span><span>Versión ' + short + ' · actualización automática</span>';
  };

  const refreshAndReload = async (button, automatic = false) => {
    if (refreshing) return;
    if (!safeToRefresh()) {
      const message = document.querySelector('.or-update-banner span');
      if (message) message.textContent = 'Guarda los cambios pendientes y espera a tener conexión antes de actualizar.';
      return;
    }
    refreshing = true;
    if (button) {
      button.disabled = true;
      button.textContent = 'Actualizando…';
    }
    try {
      await swRegistration?.update?.();
      await fetchVersion(); // Do not reload into an unavailable deployment.
      if (!safeToRefresh() || (automatic && Date.now() - lastInteraction < 30000)) throw new Error('Hay actividad pendiente');
      const waiting = swRegistration?.waiting;
      if (waiting) await new Promise((resolve, reject) => {
        const timer = setTimeout(() => { waiting.removeEventListener('statechange', changed); reject(new Error('La actualización sigue preparándose')); }, 10000);
        function changed() {
          if (waiting.state === 'activated') { clearTimeout(timer); waiting.removeEventListener('statechange', changed); resolve(); }
        }
        waiting.addEventListener('statechange', changed);
        waiting.postMessage({ type: 'SKIP_WAITING' });
        changed();
      });
      if (!safeToRefresh() || (automatic && Date.now() - lastInteraction < 30000)) throw new Error('Hay actividad pendiente');
    } catch (error) {
      console.warn('[PWA] actualización previa a recarga:', error);
      refreshing = false;
      if (button) { button.disabled = false; button.textContent = 'Reintentar'; }
      return;
    }
    location.reload();
  };

  const showUpdateBanner = newVersion => {
    pendingVersion = newVersion;
    if (updateVisible) return;
    updateVisible = true;
    addSystemStyle();
    const banner = document.createElement('div');
    banner.className = 'or-update-banner';
    banner.innerHTML = `
      <div style="flex:1;min-width:0">
        <strong>Nueva versión disponible</strong>
        <span>Operaciones Ropa ya fue actualizada en el servidor. No necesitas reinstalarla.</span>
      </div>
      <button type="button">Actualizar</button>
    `;
    banner.querySelector('button')?.addEventListener('click', event => refreshAndReload(event.currentTarget));
    document.body.appendChild(banner);
    // The badge identifies the loaded build, never the pending server build.
    renderVersion(loadedBuild);
  };

  const fetchVersion = async () => {
    const response = await fetch('/api/app-version?t=' + Date.now(), {
      cache: 'no-store',
      credentials: 'same-origin',
      headers: { 'Cache-Control': 'no-cache' }
    });
    if (!response.ok) throw new Error('version ' + response.status);
    return response.json();
  };

  const checkVersion = async ({ initial = false } = {}) => {
    try {
      const info = await fetchVersion();
      const version = String(info?.version || 'local');
      lastVersionCheck = Date.now();

      if (initial || loadedBuild === null) {
        loadedBuild = version;
        renderVersion(version);
        return;
      }

      if (version !== loadedBuild) {
        showUpdateBanner(version);
      } else {
        renderVersion(version);
      }
    } catch (error) {
      console.warn('[PWA] no se pudo comprobar versión:', error);
    }
  };

  const registerServiceWorker = async () => {
    if (!('serviceWorker' in navigator)) return;
    try {
      swRegistration = await navigator.serviceWorker.register('/service-worker.js', {
        scope: '/',
        updateViaCache: 'none'
      });
      await swRegistration.update();

      swRegistration.addEventListener('updatefound', () => {
        const worker = swRegistration.installing;
        if (!worker) return;
        worker.addEventListener('statechange', () => {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) {
            checkVersion();
          }
        });
      });
    } catch (error) {
      console.warn('[PWA] service worker no registrado:', error);
    }
  };

  window.addEventListener('load', async () => {
    await registerServiceWorker();
    await checkVersion({ initial: true });
  });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    if (Date.now() - lastVersionCheck < 30000) return;
    swRegistration?.update?.().catch(() => {});
    checkVersion();
  });

  window.addEventListener('focus', () => {
    if (Date.now() - lastVersionCheck < 30000) return;
    checkVersion();
  });

  // Revisión periódica mientras la aplicación permanece abierta.
  window.setInterval(() => {
    if (document.visibilityState === 'visible') checkVersion();
  }, 120000);

  window.setInterval(() => {
    if (pendingVersion && document.visibilityState === 'visible' &&
        Date.now() - lastInteraction >= 30000 && safeToRefresh()) {
      refreshAndReload(document.querySelector('.or-update-banner button'), true);
    }
  }, 10000);

  // La actualización anterior funciona tanto instalada como en navegador.
  // Lo siguiente sólo controla la invitación de instalación.
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

  const closeHint = hint => {
    sessionStorage.setItem('pwa-install-hint-dismissed', '1');
    hint?.remove();
  };

  const makeHint = (message, withInstallButton=false) => {
    if (document.querySelector('.pwa-install-hint')) return;
    if (sessionStorage.getItem('pwa-install-hint-dismissed') === '1') return;
    addSystemStyle();
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
