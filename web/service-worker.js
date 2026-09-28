const CACHE_NAME = 'operaciones-ropa-runtime-v1';
const STATIC_ASSETS = [
  '/static/offline.html',
  '/static/app-icon-192.svg',
  '/static/app-icon-512.svg',
  '/static/app-icon-maskable.svg',
  '/static/app-logo.svg',
  '/static/app-logo-white.svg',
  '/static/pwa_brand.css',
  '/static/pwa_brand.js',
  '/static/design_system.css',
  '/static/design_system.js',
  '/static/report_tab_carousel.js',
  '/static/report_tab_mundial_v7.js',
  '/static/report_tab_icon_rail_v1.js',
  '/static/pwa_install.js',
  '/static/ios_native.js'
];

const putInCache = async (request, response) => {
  if (!response || response.status !== 200 || response.type !== 'basic') return;
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
};

const networkFirst = async (request, fallbackUrl = null) => {
  try {
    const response = await fetch(request, { cache: 'no-store' });
    await putInCache(request, response);
    return response;
  } catch (error) {
    const cached = await caches.match(request, { ignoreSearch: true });
    if (cached) return cached;
    if (fallbackUrl) {
      const fallback = await caches.match(fallbackUrl, { ignoreSearch: true });
      if (fallback) return fallback;
    }
    throw error;
  }
};

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();

  if (event.data?.type === 'REFRESH_APP_SHELL') {
    event.waitUntil((async () => {
      const cache = await caches.open(CACHE_NAME);
      await Promise.all(STATIC_ASSETS.map(async url => {
        try {
          const response = await fetch(url, { cache: 'no-store' });
          if (response.ok) await cache.put(url, response.clone());
        } catch (_) {}
      }));
    })());
  }
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Datos, sesiones, descargas y reportes nunca se almacenan en caché.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request, { cache: 'no-store' }));
    return;
  }

  // La navegación siempre intenta el servidor primero.
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, '/static/offline.html'));
    return;
  }

  // CSS/JS/íconos: siempre red primero; caché sólo como respaldo sin conexión.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(networkFirst(request));
  }
});
