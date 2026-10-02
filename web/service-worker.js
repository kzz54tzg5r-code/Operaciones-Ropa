const CACHE_NAME = 'operaciones-ropa-runtime-v42-v237';
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
  '/static/report_tab_mundial_v7.js',
  '/static/pwa_install.js',
  '/static/ios_native.js'
];

const putInCache = async (request, response) => {
  if (!response || response.status !== 200 || response.type !== 'basic') return;
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
};

const cachedFallback = async (request, fallbackUrl = null) => {
  const cached = await caches.match(request, { ignoreSearch: true });
  if (cached) return cached;
  if (fallbackUrl) {
    const fallback = await caches.match(fallbackUrl, { ignoreSearch: true });
    if (fallback) return fallback;
  }
  return null;
};

const networkFirst = async (request, fallbackUrl = null) => {
  try {
    const response = await fetch(request, { cache: 'no-store' });

    // Render puede devolver 502/503/504 durante el relevo entre deploys.
    // No mostramos esa pantalla al usuario: conservamos el shell que ya tenía
    // funcionando y la app vuelve a consultar el backend cuando éste regresa.
    if ([502, 503, 504].includes(response.status)) {
      const fallback = await cachedFallback(request, fallbackUrl);
      if (fallback) return fallback;
    }

    await putInCache(request, response);
    return response;
  } catch (error) {
    const fallback = await cachedFallback(request, fallbackUrl);
    if (fallback) return fallback;
    throw error;
  }
};

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(STATIC_ASSETS);

    // Guardar un shell de la aplicación sin hacer fallar la instalación si
    // justo coincide con un despliegue de Render.
    try {
      const shellRequest = new Request('/', { cache: 'no-store', credentials: 'same-origin' });
      const shellResponse = await fetch(shellRequest);
      if (shellResponse.ok) await cache.put('/', shellResponse.clone());
    } catch (_) {}

    await self.skipWaiting();
  })());
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
    event.respondWith((async () => {
      try {
        const response = await networkFirst(request, '/');
        if ([502,503,504].includes(response.status)) {
          const offline = await caches.match('/static/offline.html');
          if (offline) return offline;
        }
        return response;
      } catch (_) {
        const shell = await caches.match('/');
        if (shell) return shell;
        const offline = await caches.match('/static/offline.html');
        if (offline) return offline;
        return new Response('Operaciones Ropa está reconectando…', {
          status: 503,
          headers: {'Content-Type':'text/plain; charset=utf-8','Retry-After':'5'}
        });
      }
    })());
    return;
  }

  // CSS/JS/íconos: siempre red primero; caché sólo como respaldo sin conexión.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(networkFirst(request));
  }
});
