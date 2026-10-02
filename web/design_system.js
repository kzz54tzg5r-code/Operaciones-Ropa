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

  // Las dos capas visuales comparten este catálogo sin exponerlo en window.
  (() => {
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
    observer.observe(document.body,{subtree:true,childList:true});
    window.addEventListener('resize', () => {
      if (innerWidth > 900) document.body.classList.remove('or-mobile-drawer-open');
    });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();


/* =========================================================
   EXPERIENCE V3 · filtros compactos y drawer
   ========================================================= */
(() => {
  'use strict';

  const filterSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16M7 12h10m-7 7h4"/></svg>';

  const isMobile = () => window.matchMedia('(max-width:900px)').matches;

  const panelValues = panel => {
    const values = [];
    panel.querySelectorAll('.filter:not(.hidden)').forEach(box => {
      const control = box.querySelector('select,input');
      if (!control || control.disabled && !control.value) return;
      let value = '';
      if (control.tagName === 'SELECT') {
        value = control.selectedOptions?.[0]?.textContent?.trim() || control.value || '';
      } else {
        value = control.value || '';
      }
      if (!value) return;
      values.push(value);
    });
    return values;
  };

  const updatePanelSummary = panel => {
    const out = panel.querySelector('.or-filter-summary-v3');
    if (!out) return;
    const values = panelValues(panel);
    const next = values.length ? values.join(' · ') : 'Sin filtros adicionales';
    if (out.textContent !== next) out.textContent = next;
    if (out.title !== next) out.title = next;
  };

  const makePanel = (panel, title='Filtros') => {
    if (!panel || panel.dataset.orFilterV3 === '1') return;
    panel.dataset.orFilterV3 = '1';
    panel.classList.add('or-filter-panel-v3');

    let body;
    if (panel.id === 'operativoPeriodBar') {
      body = [...panel.children].find(el => !el.classList.contains('or-filter-head-v3'));
      if (!body) return;
      body.classList.add('or-filter-body-v3');
    } else {
      body = document.createElement('div');
      body.className = 'or-filter-body-v3';
      [...panel.children].forEach(child => body.appendChild(child));
      panel.appendChild(body);
    }

    const head = document.createElement('div');
    head.className = 'or-filter-head-v3';
    head.innerHTML = `
      <div class="or-filter-head-main-v3">
        <span class="or-filter-head-icon-v3" aria-hidden="true">${filterSvg}</span>
        <div class="or-filter-head-copy-v3">
          <b>${title}</b>
          <span class="or-filter-summary-v3"></span>
        </div>
      </div>
      <button type="button" class="or-filter-toggle-v3" aria-expanded="false">Cambiar</button>
    `;
    panel.prepend(head);

    const toggle = head.querySelector('.or-filter-toggle-v3');
    const setOpen = open => {
      const shouldOpen = Boolean(open);
      if (panel.classList.contains('or-filters-open') !== shouldOpen) {
        panel.classList.toggle('or-filters-open', shouldOpen);
      }
      const expanded = shouldOpen ? 'true' : 'false';
      const label = shouldOpen ? 'Cerrar' : 'Cambiar';
      if (toggle && toggle.getAttribute('aria-expanded') !== expanded) toggle.setAttribute('aria-expanded', expanded);
      if (toggle && toggle.textContent !== label) toggle.textContent = label;
    };

    setOpen(!isMobile());

    toggle?.addEventListener('click', () => {
      setOpen(!panel.classList.contains('or-filters-open'));
    });

    panel.addEventListener('change', () => updatePanelSummary(panel));

    const applyButtons = panel.querySelectorAll('#operPeriodApply,#refresh,.primary');
    applyButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        window.setTimeout(() => {
          updatePanelSummary(panel);
          if (isMobile()) setOpen(false);
        }, 120);
      });
    });

    updatePanelSummary(panel);

    panel.__orSetFilterOpen = setOpen;
  };

  const enhanceFilterPanels = () => {
    document.getElementById('orActiveFilters')?.remove();
  };

  const enforceTopOrder = () => {
    const main = document.querySelector('main.main');
    const hero = main?.querySelector(':scope > .hero');
    const opNav = document.getElementById('operativoNav');
    const analysisNav = document.getElementById('analysisNav');
    const globalFilters = document.getElementById('globalFilters');
    if (!main || !hero || !opNav || !analysisNav || !globalFilters) return;

    // Mover el contenedor completo de navegación. V222 envuelve las barras
    // con flechas; extraer sólo el host deja etapas huérfanas y duplica flechas.
    const opNode = opNav.closest('.v226-tab-shell') || opNav.closest('.v222-tab-stage') || opNav.closest('.rt-carousel-shell') || opNav;
    const analysisNode = analysisNav.closest('.v226-tab-shell') || analysisNav.closest('.v222-tab-stage') || analysisNav.closest('.rt-carousel-shell') || analysisNav;

    if (hero.nextElementSibling !== opNode) hero.after(opNode);
    if (opNode.nextElementSibling !== analysisNode) opNode.after(analysisNode);
    if (analysisNode.nextElementSibling !== globalFilters) analysisNode.after(globalFilters);
  };

  const enhanceDrawer = () => {
    const side = document.querySelector('.side');
    if (!side || side.querySelector('.or-drawer-close-v3')) return;
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'or-drawer-close-v3';
    close.setAttribute('aria-label','Cerrar menú');
    close.textContent = '×';
    close.addEventListener('click',() => {
      document.body.classList.remove('or-mobile-drawer-open');
      document.getElementById('orMobileMenuBtn')?.setAttribute('aria-expanded','false');
    });
    side.prepend(close);
  };

  const tabIconPaths = {
    'operations.center':'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    'operations.day':'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    'operations.week':'<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
    'operations.month':'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01"/>',
    'operations.conversion':'<path d="M4 18 9 13l4 3 7-9"/><path d="M15 7h5v5"/>',
    'operations.recovery':'<circle cx="12" cy="12" r="9"/><path d="M15 8.5c-.7-.7-1.7-1-3-1-1.7 0-3 .9-3 2.2 0 3.2 6 1.4 6 4.5 0 1.3-1.3 2.3-3 2.3-1.2 0-2.4-.4-3.2-1.2M12 5.5v13"/>',
    'operations.recovery_store':'<path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/>',
    'operations.productivity':'<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
    'operations.routes':'<path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z"/><circle cx="12" cy="10" r="2"/>',
    'operations.score':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    'operations.alerts':'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    'commercial.macro':'<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
    'commercial.accordion':'<path d="M4 6h16M4 12h16M4 18h16"/>',
    'commercial.stores':'<path d="M3 10h18l-2-5H5l-2 5Z"/><path d="M5 10v9h14v-9M9 19v-5h6v5"/>',
    'commercial.sections':'<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
    'commercial.areas':'<path d="M4 5h16M7 12h10m-7 7h4"/>',
    'commercial.lingerie_checklist':'<path d="m5 12 4 4L19 6"/>',
    'commercial.more':'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'
  };

  const enhanceSubnavIcons = () => {
    document.querySelectorAll('#operativoNav .switch,#analysisNav .switch').forEach(btn => {
      // V221 usa .rt-tab-icon como iconografía autoritativa. Si ya existe,
      // retirar cualquier icono heredado para no mostrar dos iconos por pestaña.
      if (btn.querySelector('.rt-tab-icon,.v203-tab-icon')) {
        btn.querySelectorAll(':scope > .or-tab-icon').forEach(x => x.remove());
        return;
      }
      if (btn.querySelector('.or-tab-icon')) return;
      const key = btn.dataset.tabKey || '';
      let path = tabIconPaths[key];
      if (!path) {
        if ((btn.textContent || '').includes('Carga')) path = iconPaths.upload;
        else if (btn.id === 'openGoalsBtn') path = iconPaths.settings;
        else path = iconPaths.file;
      }
      btn.insertAdjacentHTML('afterbegin',
        '<span class="or-tab-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + path + '</svg></span>'
      );
    });
  };

  const syncResponsiveState = () => {
    document.querySelectorAll('.or-filter-panel-v3').forEach(panel => {
      if (!isMobile()) panel.__orSetFilterOpen?.(true);
      else if (!panel.dataset.orMobileInitialized) {
        panel.dataset.orMobileInitialized='1';
        panel.__orSetFilterOpen?.(false);
      }
    });
    if (!isMobile()) document.body.classList.remove('or-mobile-drawer-open');
  };

  const initV3 = () => {
    document.documentElement.classList.add('or-experience-v3');
    enforceTopOrder();
    enhanceFilterPanels();
    enhanceDrawer();
    enhanceSubnavIcons();
    syncResponsiveState();

    let observerScheduled = false;
    const observer = new MutationObserver(mutations => {
      if (observerScheduled) return;
      const meaningful = mutations.some(m => m.addedNodes.length || m.removedNodes.length);
      if (!meaningful) return;
      observerScheduled = true;
      requestAnimationFrame(() => {
        observerScheduled = false;
        enforceTopOrder();
        enhanceFilterPanels();
        enhanceSubnavIcons();
        document.querySelectorAll('.or-filter-panel-v3').forEach(updatePanelSummary);
      });
    });
    observer.observe(document.body,{subtree:true,childList:true});

    window.addEventListener('resize',syncResponsiveState,{passive:true});
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',initV3,{once:true});
  else initV3();
})();
})();
