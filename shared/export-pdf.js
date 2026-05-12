/* shared/export-pdf.js
 *
 * Auto-inyecta un botón "Exportar PDF" en cada dashboard / DDD / Competidores.
 * Usa window.print() + un @media print stylesheet que oculta el chrome de
 * navegación y arma una salida A4 landscape limpia.
 *
 * Uso: <script src="<relative>/shared/export-pdf.js"></script>
 *      (idempotente: si ya está inyectado, no duplica botón ni estilos)
 */
(function () {
  "use strict";

  if (window.__sfPdfExportInjected) return;
  window.__sfPdfExportInjected = true;

  // 1) Print stylesheet
  function injectPrintStyles() {
    if (document.getElementById("sf-pdf-print-css")) return;
    var s = document.createElement("style");
    s.id = "sf-pdf-print-css";
    s.textContent = [
      "@media print {",
      "  @page { size: A4 landscape; margin: 10mm; }",
      "  html, body { background: #fff !important; }",
      "  body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }",
      "  *, *::before, *::after { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }",
      "  /* Hide nav/footer chrome */",
      "  nav, .nav, .navbar, .footer, .nav-back, .nav-ext, .nav-tab, .nav-tab-ddd, .nav-tab-comp, .nav-tab-bonos, .nav-hub, .nav-export { display: none !important; }",
      "  /* Hide export buttons themselves */",
      "  [data-export-dashboard], [data-export-ddd], [data-export-pdf], .pdf-export-btn { display: none !important; }",
      "  /* Hide hub toolbar (root index) */",
      "  .hub-toolbar { display: none !important; }",
      "  /* Avoid breaking inside cards / sections */",
      "  .card, section, .cd, .chart-card, .panel, .perf-card { break-inside: avoid; page-break-inside: avoid; }",
      "  canvas, svg, img { max-width: 100% !important; height: auto !important; }",
      "  /* Body padding & margins */",
      "  .wrap, .main, main { padding-top: 0 !important; }",
      "}"
    ].join("\n");
    document.head.appendChild(s);
  }

  // 2) Botón
  function makeButton() {
    var btn = document.createElement("a");
    btn.href = "javascript:void(0)";
    btn.setAttribute("data-export-pdf", "true");
    btn.title = "Exportar a PDF (vista de impresión)";
    btn.textContent = "Exportar PDF";
    btn.onclick = function (e) {
      e && e.preventDefault();
      window.print();
    };
    return btn;
  }

  function styleAsTwin(btn, sibling) {
    // Copiar la apariencia del botón Excel hermano si existe (mismo className)
    if (sibling && sibling.className) {
      btn.className = sibling.className;
    }
    btn.style.marginLeft = "6px";
  }

  function styleAsFallback(btn) {
    btn.style.cssText = [
      "display:inline-flex",
      "align-items:center",
      "gap:6px",
      "font-family:'IBM Plex Sans',sans-serif",
      "font-size:11px",
      "font-weight:600",
      "color:#b01e1e",
      "background:#fff",
      "border:1px solid #e5e7eb",
      "padding:6px 12px",
      "border-radius:5px",
      "cursor:pointer",
      "text-decoration:none",
      "margin:0 6px",
      "letter-spacing:.04em"
    ].join(";");
  }

  function injectButton() {
    if (document.querySelector("[data-export-pdf]")) return;
    var btn = makeButton();
    // Preferencia 1: pegado a "Exportar Excel" si existe
    var excel = document.querySelector("[data-export-dashboard], [data-export-ddd]");
    if (excel && excel.parentNode) {
      styleAsTwin(btn, excel);
      excel.parentNode.insertBefore(btn, excel.nextSibling);
      return;
    }
    // Preferencia 2: insertarlo en el nav (final)
    var nav = document.querySelector("nav.nav, nav.navbar, nav");
    if (nav) {
      styleAsFallback(btn);
      nav.appendChild(btn);
      return;
    }
    // Fallback: floating top-right
    styleAsFallback(btn);
    btn.style.position = "fixed";
    btn.style.top = "10px";
    btn.style.right = "12px";
    btn.style.zIndex = "999";
    document.body.appendChild(btn);
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    injectPrintStyles();
    injectButton();
    // Re-intentar en 250ms por si Excel button se inyecta despues
    setTimeout(function () {
      if (!document.querySelector("[data-export-pdf]")) injectButton();
    }, 250);
    setTimeout(function () {
      if (!document.querySelector("[data-export-pdf]")) injectButton();
    }, 1000);
  });
})();
