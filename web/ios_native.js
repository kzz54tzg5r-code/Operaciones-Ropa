(() => {
  const cap = window.Capacitor;
  const isNative = Boolean(cap && typeof cap.getPlatform === 'function' && cap.getPlatform() === 'ios');
  if (!isNative) return;

  document.documentElement.classList.add('capacitor-ios');

  const style = document.createElement('style');
  style.textContent = `
    html.capacitor-ios body{padding-top:env(safe-area-inset-top)}
    html.capacitor-ios .mobile{padding-bottom:calc(5px + env(safe-area-inset-bottom))!important}
    .ios-network-banner{position:fixed;left:10px;right:10px;top:calc(8px + env(safe-area-inset-top));z-index:20000;
      background:#7f1d1d;color:#fff;padding:9px 12px;border-radius:10px;font:700 12px/1.2 -apple-system,BlinkMacSystemFont,sans-serif;
      text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.18);display:none}
    .ios-network-banner.show{display:block}
  `;
  document.head.appendChild(style);

  const plugins = cap.Plugins || {};
  const Haptics = plugins.Haptics;
  const Network = plugins.Network;
  const Share = plugins.Share;
  const App = plugins.App;

  const banner = document.createElement('div');
  banner.className = 'ios-network-banner';
  banner.textContent = 'Sin conexión. Algunas funciones pueden no actualizarse.';
  document.body.appendChild(banner);

  const setConnected = (connected) => banner.classList.toggle('show', !connected);

  try {
    Network?.getStatus?.().then(s => setConnected(Boolean(s.connected))).catch(() => {});
    Network?.addListener?.('networkStatusChange', s => setConnected(Boolean(s.connected)));
  } catch (_) {}

  document.addEventListener('click', (event) => {
    const target = event.target?.closest?.('.mnav,.nav,.switch,.primary,.action-sm,.report-actions button,.sidebar-toggle');
    if (!target || !Haptics?.impact) return;
    Haptics.impact({ style: 'LIGHT' }).catch(() => {});
  }, { passive: true });

  try {
    App?.addListener?.('appStateChange', ({ isActive }) => {
      if (isActive) document.documentElement.classList.add('ios-app-active');
      else document.documentElement.classList.remove('ios-app-active');
    });
  } catch (_) {}

  window.OperacionesRopaNative = {
    isIOS: true,
    async haptic(style = 'LIGHT') {
      if (!Haptics?.impact) return false;
      await Haptics.impact({ style });
      return true;
    },
    async share({ title = 'Operaciones Ropa', text = '', url = location.href } = {}) {
      if (!Share?.share) return false;
      await Share.share({ title, text, url, dialogTitle: 'Compartir' });
      return true;
    },
    async networkStatus() {
      if (!Network?.getStatus) return { connected: navigator.onLine };
      return Network.getStatus();
    }
  };
})();
