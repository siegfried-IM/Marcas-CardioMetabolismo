/* shared/ux-shared.js
 * Helpers UX compartidos para todas las paginas (toast, empty states,
 * filter feedback). Idempotente — chequea window flags antes de actuar.
 *
 * NO modifica datos ni logica existente. Solo agrega capa visual.
 */
(function () {
  'use strict';
  if (window.__sieUxShared) return;
  window.__sieUxShared = true;

  /* ─────────────────────────────────────────────────────────
   *  Toast notifications
   * ─────────────────────────────────────────────────────────*/
  function ensureToastContainer() {
    var c = document.getElementById('sie-toast-container');
    if (c) return c;
    c = document.createElement('div');
    c.id = 'sie-toast-container';
    document.body.appendChild(c);
    return c;
  }

  function toast(msg, opts) {
    opts = opts || {};
    var dur = opts.duration || 2000;
    var container = ensureToastContainer();
    var el = document.createElement('div');
    el.className = 'sie-toast';
    if (opts.kind) el.setAttribute('data-kind', opts.kind);
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(function () {
      el.classList.add('out');
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 200);
    }, dur);
  }
  window.sieToast = toast;

  /* ─────────────────────────────────────────────────────────
   *  Empty state renderer
   * ─────────────────────────────────────────────────────────*/
  var EMPTY_TEMPLATES = {
    'no-data': {
      icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-5"/></svg>',
      title: 'Sin datos para este filtro',
      sub: 'Probá con otra marca o limpiá los filtros'
    },
    'no-recetas': {
      icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 10h8M8 14h5"/></svg>',
      title: 'Esta marca no tiene recetas',
      sub: 'No hay datos de CloseUp para el período actual'
    },
    'loading': {
      icon: '<div class="sie-spinner"></div>',
      title: 'Cargando datos…',
      sub: ''
    },
    'error': {
      icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
      title: 'Hubo un problema al cargar',
      sub: 'Recargá la página para reintentar'
    }
  };

  function renderEmptyState(container, type) {
    if (!container) return;
    var el = typeof container === 'string'
      ? document.getElementById(container) || document.querySelector(container)
      : container;
    if (!el) return;
    var tpl = EMPTY_TEMPLATES[type] || EMPTY_TEMPLATES['no-data'];
    el.innerHTML =
      '<div class="sie-empty">' +
        '<div class="sie-empty-icon">' + tpl.icon + '</div>' +
        '<div class="sie-empty-title">' + tpl.title + '</div>' +
        (tpl.sub ? '<div class="sie-empty-sub">' + tpl.sub + '</div>' : '') +
      '</div>';
  }
  window.sieEmptyState = renderEmptyState;

  /* ─────────────────────────────────────────────────────────
   *  Inject minimal CSS for empty/loading (if not already)
   * ─────────────────────────────────────────────────────────*/
  function injectStyles() {
    if (document.getElementById('sie-ux-shared-styles')) return;
    var s = document.createElement('style');
    s.id = 'sie-ux-shared-styles';
    s.textContent = [
      '.sie-empty { display:flex; flex-direction:column; align-items:center; justify-content:center;',
      '  padding:32px 20px; text-align:center; color:#6b7280; min-height:200px; }',
      '.sie-empty-icon { color:#9ca3af; margin-bottom:12px; opacity:.6; }',
      '.sie-empty-title { font-size:13px; font-weight:600; color:#374151; margin-bottom:4px;',
      '  font-family:"IBM Plex Sans",system-ui,sans-serif; }',
      '.sie-empty-sub { font-size:11px; color:#9ca3af; max-width:280px; line-height:1.5; }',
      '.sie-spinner { width:24px; height:24px; border:2.5px solid #e5e7eb;',
      '  border-top-color:#b01e1e; border-radius:50%; animation:sie-spin .8s linear infinite; }',
      '@keyframes sie-spin { to { transform:rotate(360deg); } }',
      /* Skeleton */
      '.sie-skeleton { background:linear-gradient(90deg,#f3f4f6 0%,#e5e7eb 50%,#f3f4f6 100%);',
      '  background-size:200% 100%; animation:sie-shimmer 1.4s ease-in-out infinite;',
      '  border-radius:6px; }',
      '@keyframes sie-shimmer { 0% { background-position:200% 0; } 100% { background-position:-200% 0; } }'
    ].join('\n');
    document.head.appendChild(s);
  }

  /* ─────────────────────────────────────────────────────────
   *  Init
   * ─────────────────────────────────────────────────────────*/
  function init() {
    injectStyles();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
