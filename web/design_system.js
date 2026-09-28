(() => {
  'use strict';

  const iconPaths = {
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    operation:'<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v6h-6"/>',
    commercial:'<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
    users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    share:'<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.59 13.51 6.83 3.98M15.41 6.51 8.59 10.49"/>',
    refresh:'<path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/>',
    filter:'<path d="M4 5h16M7 12h10m-7 7h4"/>',
    upload:'<path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 20h14"/>',
    download:'<path d="M12 4v12m0 0 5-5m-5 5-5-5"/><path d="M5 20h14"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.6v-.1A1.7 1.7 0 0 0 8 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 3.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2V9.6h.1A1.7 1.7 0 0 0 3.6 8a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8 3.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V2h4v.1A1.7 1.7 0 0 0 15 3.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 8a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.1.4h.1v4h-.1a1.7 1.7 0 0 0-1.7 1.6Z"/>',
    file:'<path d="M6 2h8l4 4v16H6z"/><path d="M14 2v5h5M9 13h6M9 17h6"/>',
    store:'<path d="M3 9l2-5h14l2 5"/><path d="M5 13v8h14v-8M9 21v-6h6v6"/><path d="M3 9c0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0"/>'
  };

  const icon = (name, cls='or-icon') => {
    const paths = iconPaths[name] || iconPaths.file;
    return `<span class="${cls}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths}</svg></span>`;
  };

  const setNavIcon = (el, name) => {
    if (!el || el.querySelector('.or-icon')) return;
    el.insertAdjacentHTML('afterbegin', icon(name));
  };

  const enhanceNavigation = () => {
    const side = document.querySelector('.side');
    if (!side) return;

    const oldGroup = side.querySelector('.group');
    if (oldGroup) oldGroup.textContent = 'NAVEGACIÓN';

    const navs = [...side.querySelectorAll('.nav[data-main]')];
    const defs = {
      operativo:{label:'OPERACIÓN',icon:'operation'},
      analysis:{label:'COMERCIAL',icon:'commercial'},
      users:{label:'GESTIÓN',icon:'users'},
      share:{label:null,icon:'share'}
    };

    let lastSection = null;
    navs.forEach(nav => {
      const key = nav.dataset.main;
      const def = defs[key] || {icon:'file'};
      setNavIcon(nav, def.icon);
      if (def.label && def.label !== lastSection && !nav.previousElementSibling?.classList?.contains('or-nav-section')) {
        const sec = document.createElement('div');
        sec.className = 'or-nav-section';
        sec.textContent = def.label;
        nav.before(sec);
        lastSection = def.label;
      }
    });

    document.querySelectorAll('.mnav[data-main]').forEach(btn => {
      const def = defs[btn.dataset.main] || {icon:'file'};
      const old = btn.querySelector('.mnav-icon');
      if (old) old.outerHTML = icon(def.icon,'mnav-icon or-icon');
    });
  };

  const addMobileDrawer = () => {
    if (document.getElementById('orMobileMenuBtn')) return;
    const hero = document.querySelector('.hero');
    const side = document.querySelector('.side');
    if (!hero || !side) return;

    const btn = document.createElement('button');
    btn.id = 'orMobileMenuBtn';
    btn.className = 'or-mobile-menu-trigger';
    btn.type = 'button';
    btn.setAttribute('aria-label','Abrir menú');
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round">${iconPaths.menu}</svg>`;

    const backdrop = document.createElement('div');
    backdrop.className = 'or-drawer-backdrop';
    backdrop.setAttribute('aria-hidden','true');

    const close = () => {
      document.body.classList.remove('or-mobile-drawer-open');
      btn.setAttribute('aria-expanded','false');
    };
    const open = () => {
      document.body.classList.add('or-mobile-drawer-open');
      btn.setAttribute('aria-expanded','true');
    };
    btn.addEventListener('click', () => document.body.classList.contains('or-mobile-drawer-open') ? close() : open());
    backdrop.addEventListener('click', close);
    side.addEventListener('click', e => {
      if (e.target.closest('.nav[data-main]') && innerWidth <= 900) close();
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

    hero.prepend(btn);
    document.body.appendChild(backdrop);
  };

  const enhanceFilters = () => {
    const filters = document.getElementById('globalFilters');
    if (!filters || document.getElementById('orActiveFilters')) return;

    const refresh = document.getElementById('refresh');
    if (refresh && !refresh.querySelector('.or-btn-icon')) {
      refresh.insertAdjacentHTML('afterbegin', icon('refresh','or-btn-icon or-icon'));
    }

    const clear = document.createElement('button');
    clear.type = 'button';
    clear.id = 'orClearFilters';
    clear.className = 'or-clear-filters';
    clear.innerHTML = icon('filter','or-btn-icon or-icon') + 'Limpiar';
    filters.appendChild(clear);

    const summary = document.createElement('div');
    summary.id = 'orActiveFilters';
    summary.className = 'or-filter-summary';
    filters.after(summary);

    const controls = [...filters.querySelectorAll('select,input')];

    const render = () => {
      summary.innerHTML = '';
      controls.forEach(control => {
        if (control.closest('.hidden')) return;
        const value = String(control.value || '').trim();
        if (!value || /^(Todas|Todos|Compañía)$/i.test(value)) return;
        const label = control.closest('.filter')?.querySelector('label')?.textContent?.trim() || 'Filtro';
        const chip = document.createElement('span');
        chip.className = 'or-filter-chip';
        chip.innerHTML = `<b>${label}:</b> ${value}`;
        summary.appendChild(chip);
      });
    };

    window.__orRenderFilterSummary = render;
    controls.forEach(c => c.addEventListener('change', render));
    clear.addEventListener('click', () => {
      controls.forEach(control => {
        if (control.tagName === 'SELECT') {
          const preferred = [...control.options].find(o => /^(Todas|Todos|Compañía)$/i.test(o.value || o.textContent));
          control.value = preferred ? preferred.value : (control.options[0]?.value || '');
        } else {
          control.value = '';
        }
        control.dispatchEvent(new Event('change',{bubbles:true}));
      });
      render();
    });
    render();
  };

  const isNumericText = text => {
    const s = String(text || '').trim()
      .replace(/[$,%]/g,'')
      .replace(/\s+pzas?$/i,'')
      .replace(/,/g,'');
    return s !== '' && /^[-+]?\d+(\.\d+)?$/.test(s);
  };

  const enhanceTable = table => {
    if (!table) return;
    const rows = [...table.rows].filter(row => row.dataset.orEnhanced !== '1');
    rows.forEach(row => {
      row.dataset.orEnhanced = '1';
      [...row.cells].forEach(cell => {
        if (isNumericText(cell.textContent)) cell.classList.add('or-num');
        if (/^(total|total general|subtotal)/i.test(cell.textContent.trim())) {
          cell.classList.add('or-total');
          row.classList.add('or-total');
        }
      });
    });
  };

  const enhanceKpis = root => {
    (root || document).querySelectorAll?.('.kpis').forEach(group => {
      const visible = [...group.children].filter(x => x.classList?.contains('kpi'));
      group.classList.toggle('or-kpi-matrix', visible.length >= 7);
    });
  };

  const enhanceStates = root => {
    (root || document).querySelectorAll?.('.panel,.infoempty,.log,.msg').forEach(el => {
      const t = (el.textContent || '').trim();
      el.classList.toggle('or-loading', /^Cargando( información| historial)?[.…]*$/i.test(t));
      el.classList.toggle('or-error-state', /^(Error|No fue posible|Falló)/i.test(t));
      el.classList.toggle('or-success-state', /^(Procesado|Guardado|Publicado|Completado)/i.test(t));
    });
  };

  const buttonIconName = label => {
    const t = label.toLowerCase();
    if (/actualizar|consultar|recargar/.test(t)) return 'refresh';
    if (/cargar|subir|procesar|publicar/.test(t)) return 'upload';
    if (/descargar|exportar/.test(t)) return 'download';
    if (/config|meta|tienda/.test(t)) return 'settings';
    if (/compartir/.test(t)) return 'share';
    return null;
  };

  const enhanceButtons = root => {
    (root || document).querySelectorAll?.('button.primary,button.action-sm,.report-actions button').forEach(btn => {
      if (btn.querySelector('.or-btn-icon')) return;
      const name = buttonIconName(btn.textContent || '');
      if (name) btn.insertAdjacentHTML('afterbegin', icon(name,'or-btn-icon or-icon'));
    });
  };

  let scheduled = false;
  const refreshEnhancements = () => {
    scheduled = false;
    document.querySelectorAll('table.table').forEach(enhanceTable);
    enhanceKpis(document);
    enhanceStates(document);
    enhanceButtons(document);
    if (typeof window.__orRenderFilterSummary === 'function') window.__orRenderFilterSummary();
  };

  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(refreshEnhancements);
  };

  const init = () => {
    document.documentElement.classList.add('or-design-system-v2');
    enhanceNavigation();
    addMobileDrawer();
    enhanceFilters();
    refreshEnhancements();

    const observer = new MutationObserver(schedule);
    observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class']});
    window.addEventListener('resize', () => {
      if (innerWidth > 900) document.body.classList.remove('or-mobile-drawer-open');
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
