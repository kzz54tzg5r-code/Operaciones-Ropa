(() => {
  const isStandalone = () =>
    window.matchMedia?.('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

  document.documentElement.classList.toggle('pwa-standalone', isStandalone());

  let swRegistration = null;
  const loadedVersionKey = "operaciones-ropa:loaded-version";
  let loadedBuild = null;
  let lastVersionCheck = 0;
  let updateVisible = false;
  let pendingVersion = null;
  let pendingVersionAt = 0;
  let refreshing = false;
  let pendingWrites = 0;
  let lastInteraction = Date.now();
  const edits = new Set();
  const originals = new WeakMap();
  const valueOf = el => ['checkbox', 'radio'].includes(el.type) ? el.checked : el.value;
  const eligible = el => el?.matches?.('input,textarea,select') &&
    !el.closest('#loginView,.filters,.v165-subfilters,.or-filter-panel-v3,#viewRoleBox,.v313-filters,.v293-filters,.v302-filters,.v330-layout,.v330-source') &&
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
  // Los filtros cambian consultas, no son capturas sin guardar.
  // Los campos desconectados del DOM no deben bloquear actualizaciones.
  const pendingDrafts = () => {
    try {
      return Array.from({ length: sessionStorage.length }, (_, i) => sessionStorage.key(i))
        .some(key => /^or\.capture\.v1:/.test(key || ''));
    } catch (_) { return false; }
  };
  const liveUnsavedEdits = () => {
    for (const el of edits) if (!el.isConnected) edits.delete(el);
    return edits.size > 0 || pendingDrafts();
  };
  const safeToRefresh = () => navigator.onLine !== false && pendingWrites === 0 && !liveUnsavedEdits();

  const addSystemStyle = () => {
    if (document.getElementById('pwaSystemStyle')) return;
    const style = document.createElement('style');
    style.id = 'pwaSystemStyle';
    style.textContent = `
      .or-version-badge{display:flex;align-items:center;gap:6px;margin-top:7px;padding:6px 8px;border:1px solid #e1e8f0;
        border-radius:8px;background:#f8fafc;color:#62748a;font-size:8px;font-weight:750;line-height:1.2}
      .or-version-dot{width:7px;height:7px;border-radius:50%;background:#0e9f6e;box-shadow:0 0 0 3px rgba(14,159,110,.10)}
      .or-update-banner{position:fixed;left:10px;right:10px;top:calc(10px + env(safe-area-inset-top));z-index:2147483000!important;pointer-events:auto!important;isolation:isolate;
        max-width:620px;margin:0 auto;display:flex;align-items:center;gap:10px;padding:10px 11px;border:1px solid #b9dafc;
        border-radius:12px;background:#fff;color:#123b73;box-shadow:0 16px 40px rgba(10,49,91,.20);
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
      .or-update-banner strong{display:block;font-size:11px;margin-bottom:2px}.or-update-banner span{display:block;font-size:9px;color:#66758a;line-height:1.3}
      .or-update-banner button{margin-left:auto;flex:0 0 auto;border:0;border-radius:8px;background:#0d7ff4;color:#fff;
        min-height:40px;padding:0 14px;font-size:11px;font-weight:900;cursor:pointer;pointer-events:auto!important;touch-action:manipulation;position:relative;z-index:2}
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
      const message = document.querySelector('.or-update-banner:not(.or-update-current) span');
      if (message) message.textContent = pendingWrites > 0
        ? 'Hay un guardado en proceso; actualiza cuando termine.'
        : liveUnsavedEdits()
          ? 'Tienes una captura sin guardar. Guárdala primero y después presiona Actualizar.'
          : 'Comprueba tu conexión y vuelve a intentarlo.';
      if (button) { button.disabled = false; button.textContent = 'Actualizar'; }
      return;
    }
    refreshing = true;
    if (button) { button.disabled = true; button.textContent = 'Actualizando…'; }
    try {
      const verified = await fetchVersion();
      if (!verified?.version || verified.version === 'local') throw new Error('Versión no verificable');
      if (!safeToRefresh() || (automatic && Date.now() - lastInteraction < 30000)) {
        throw new Error('Hay una captura o petición pendiente');
      }
      // El SW puede permanecer esperando si otra pestaña sigue abierta:
      // el shell es network-first, no esperamos su activación para recargar.
      try {
        if (swRegistration?.update) {
          await Promise.race([
            swRegistration.update(),
            new Promise(resolve => setTimeout(resolve, 2500))
          ]);
        }
        swRegistration?.waiting?.postMessage({type:'SKIP_WAITING'});
      } catch (swError) {
        console.warn('[PWA] SW se actualizará durante la navegación:', swError);
      }
      if (!safeToRefresh()) throw new Error('Captura pendiente');
      localStorage.setItem(loadedVersionKey, String(verified.version));
      loadedBuild = String(verified.version);
      location.reload();
    } catch (error) {
      console.warn('[PWA] no se pudo aplicar actualización:', error);
      refreshing = false;
      if (button) { button.disabled = false; button.textContent = 'Reintentar'; }
      const message = document.querySelector('.or-update-banner:not(.or-update-current) span');
      if (message) message.textContent = 'No se pudo confirmar la nueva versión. Reintenta cuando haya conexión.';
    }
  };

  const showUpdateBanner = newVersion => {
    if (pendingVersion !== newVersion) pendingVersionAt = Date.now();
    pendingVersion = newVersion;
    if (updateVisible) { const el=document.querySelector('.or-update-banner:not(.or-update-current)'); if(el){const span=el.querySelector('span'); if(span)span.textContent='Versión nueva lista para instalar sin reinstalar la aplicación.';} return; }
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
    banner.querySelector('button')?.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); refreshAndReload(event.currentTarget); });
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
        let previous = "";
        try { previous = localStorage.getItem(loadedVersionKey) || ""; } catch (_) {}
        loadedBuild = previous && previous !== "local" ? previous : version;
        if (!previous || previous === "local") {
          try { localStorage.setItem(loadedVersionKey, version); } catch (_) {}
        }
        renderVersion(loadedBuild);
      }
      if (version !== loadedBuild) {
        showUpdateBanner(version);
        return { available: true, version };
      }
      renderVersion(version);
      return { available: false, version };
    } catch (error) {
      console.warn('[PWA] no se pudo comprobar versión:', error);
    }
  };

  // Se utiliza desde el botón Actualizar de Bonos y cualquier otro reporte.
  // El mensaje emergente aparece también al abrir una PWA instalada desactualizada.
  window.OperacionesPWA = {
    checkForUpdates: async function(opts = {}) {
      try { await swRegistration?.update?.(); } catch (_) {}
      const result = await checkVersion();
      if (opts.manual && result && !result.available) {
        const notice = document.createElement("div");
        notice.className = "or-update-banner";
        notice.style.zIndex = "25001";
        notice.innerHTML = '<div style="flex:1"><strong>Aplicación actualizada</strong><span>Ya tienes la versión más reciente de Operaciones Ropa.</span></div><button type="button">Cerrar</button>';
        addSystemStyle();
        document.querySelector(".or-update-current")?.remove();
        notice.classList.add("or-update-current");
        notice.querySelector("button").onclick = () => notice.remove();
        document.body.appendChild(notice);
      }
      return result;
    },
    applyUpdate: () => refreshAndReload(document.querySelector(".or-update-banner:not(.or-update-current) button"))
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
  }, 60000);

  // La nueva versión se mantiene visible hasta pulsar Actualizar.
  // No recargar por sorpresa mientras el usuario revisa un reporte.

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
