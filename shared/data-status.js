/* shared/data-status.js
 * Mejoras de UX universales que se inyectan en cada dashboard:
 *  1) Badge "Datos al DD/MM/YYYY" en el navbar (verde si <45 dias,
 *     naranja si 45-90, rojo si >90). Tooltip con todos los cortes.
 *  2) Chips de molecula/familia sin productos SIE -> grayed out con
 *     leyenda "(sin SIE)" para que el usuario sepa antes de clickear
 *     que no hay datos comparativos en esa familia.
 *
 * Usage: add `<script src="../shared/data-status.js"></script>` antes
 * de `</body>` en cada dashboard. No requiere ningun otro cambio.
 */
(function () {
  'use strict';

  function getDataObj() {
    return window.D || window.OTC_DASHBOARD || window.OTC_DATA || null;
  }

  function getMeta() {
    // OTC_DATA.meta tiene generatedAt + cuts; OTC_DASHBOARD.meta tiene
    // footer_date + labels. Mergeamos ambos para que el badge tenga toda
    // la info posible.
    var meta = {};
    if (window.OTC_DATA && window.OTC_DATA.meta) {
      Object.assign(meta, window.OTC_DATA.meta);
    }
    if (window.OTC_DASHBOARD && window.OTC_DASHBOARD.meta) {
      Object.assign(meta, window.OTC_DASHBOARD.meta);
    }
    var D = window.D;
    if (D && D.meta && D !== window.OTC_DASHBOARD && D !== window.OTC_DATA) {
      Object.assign(meta, D.meta);
    }
    return meta;
  }

  function injectStyles() {
    if (document.getElementById('data-status-styles')) return;
    var style = document.createElement('style');
    style.id = 'data-status-styles';
    style.textContent = [
      '.data-status-badge {',
      '  margin-left:auto;display:inline-flex;align-items:center;gap:6px;',
      '  padding:4px 10px;font-size:10px;color:#4b5563;',
      '  border:1px solid rgba(0,0,0,.12);border-radius:5px;',
      '  background:#f9fafb;cursor:help;flex-shrink:0;white-space:nowrap;',
      '  font-family:system-ui,-apple-system,sans-serif;',
      '}',
      '.data-status-dot {',
      '  width:6px;height:6px;border-radius:50%;display:inline-block;',
      '}',
      '.mol-chip.no-sie-chip {',
      '  opacity:0.45 !important;',
      '  cursor:not-allowed !important;',
      '  pointer-events:none !important;',
      '}',
      '.mol-chip.no-sie-chip::after {',
      '  content:" \\00b7 sin SIE";',
      '  font-size:9px;color:#94a3b8;font-weight:400;margin-left:3px;',
      '}',
      ''
    ].join('\n');
    document.head.appendChild(style);
  }

  function parseDate(s) {
    if (!s) return null;
    var s2 = String(s);
    // ISO: 2026-04-29 09:26 or 2026-04-29
    var m = s2.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return { date: new Date(+m[1], +m[2] - 1, +m[3]), label: m[3] + '/' + m[2] + '/' + m[1] };
    // dd/mm/yyyy (footer_date format)
    m = s2.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
    if (m) {
      var d = m[1].length === 1 ? '0' + m[1] : m[1];
      var mm = m[2].length === 1 ? '0' + m[2] : m[2];
      return { date: new Date(+m[3], +m[2] - 1, +m[1]), label: d + '/' + mm + '/' + m[3] };
    }
    return null;
  }

  function getFooterDateFromDom() {
    // Fallback para dashboards self-contained (mujer, SNC) que no exponen
    // OTC_DATA/OTC_DASHBOARD en window: leemos #footer-date o cualquier
    // texto con patron "Datos al DD/MM/YYYY".
    var el = document.getElementById('footer-date');
    if (el && el.textContent) return el.textContent.trim();
    var foot = document.querySelector('.footer, footer');
    if (foot) {
      var match = (foot.textContent || '').match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
      if (match) return match[1];
    }
    return null;
  }

  function injectBanner() {
    var meta = getMeta();
    // Preferir footer_date (fecha del corte) sobre generatedAt (cuando se corrio el build)
    var pd = parseDate(meta.footer_date) || parseDate(meta.generatedAt) || parseDate(getFooterDateFromDom());
    if (!pd) return;

    var ageDays = Math.round((Date.now() - pd.date.getTime()) / 86400000);
    var color;
    if (ageDays <= 45) color = '#16a34a';
    else if (ageDays <= 90) color = '#d97706';
    else color = '#dc2626';
    var label = 'Datos al ' + pd.label;

    var tipLines = [];
    if (meta.footer_date) tipLines.push('Corte: ' + meta.footer_date);
    if (meta.generatedAt) tipLines.push('Generado: ' + meta.generatedAt);
    if (meta.budgetCut) tipLines.push('Budget: ' + meta.budgetCut);
    if (meta.budget_label) tipLines.push('Budget: ' + meta.budget_label);
    if (meta.stockCut) tipLines.push('Stock: ' + meta.stockCut);
    if (meta.rxCut) tipLines.push('Recetas: ' + meta.rxCut);
    if (meta.rec_label) tipLines.push('Recetas: ' + meta.rec_label);
    if (meta.dddCut) tipLines.push('DDD: ' + meta.dddCut);
    if (meta.canales_label) tipLines.push('Canales: ' + meta.canales_label);

    var nav = document.querySelector('.nav, .navbar');
    if (!nav) return;
    if (nav.querySelector('.data-status-badge')) return;

    var badge = document.createElement('span');
    badge.className = 'data-status-badge';
    badge.title = tipLines.join('\n');
    badge.innerHTML =
      '<span class="data-status-dot" style="background:' + color + ';"></span>' +
      '<span>' + label + '</span>';
    nav.appendChild(badge);
  }

  function decorateChips() {
    var D = getDataObj();
    if (!D || !D.mol_perf) return;
    var chips = document.querySelectorAll('.mol-chip');
    chips.forEach(function (chip) {
      var onclick = chip.getAttribute('onclick') || '';
      var m = onclick.match(/setPMol\(\s*['"]([^'"]+)['"]\s*\)/);
      if (!m) return;
      var mol = m[1];
      var data = D.mol_perf[mol];
      var hasSie = !!(data && data.products && data.products.some(function (p) { return p && p.is_sie; }));
      if (hasSie) {
        chip.classList.remove('no-sie-chip');
      } else {
        chip.classList.add('no-sie-chip');
      }
    });
  }

  function init() {
    injectStyles();
    injectBanner();
    decorateChips();
    var grid = document.getElementById('perf-mol-grid');
    if (grid && typeof MutationObserver !== 'undefined') {
      var mo = new MutationObserver(function () { decorateChips(); });
      mo.observe(grid, { childList: true, subtree: false });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 250); });
  } else {
    setTimeout(init, 250);
  }
})();
