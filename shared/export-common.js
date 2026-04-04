(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;

  function valueOrNull(value) {
    return value == null ? null : value;
  }

  function safeRows(rows) {
    return Array.isArray(rows) && rows.length ? rows : [{ Info: "Sin datos disponibles" }];
  }

  function uniqueSheetName(name, seen) {
    var base = String(name || "Hoja").replace(/[\\/?*\[\]:]/g, " ").trim() || "Hoja";
    base = base.slice(0, 31);
    var next = base;
    var idx = 2;
    while (seen.has(next)) {
      var suffix = " " + idx;
      next = base.slice(0, Math.max(0, 31 - suffix.length)) + suffix;
      idx += 1;
    }
    seen.add(next);
    return next;
  }

  function columnLetter(index) {
    var value = index + 1;
    var result = "";
    while (value > 0) {
      var remainder = (value - 1) % 26;
      result = String.fromCharCode(65 + remainder) + result;
      value = Math.floor((value - 1) / 26);
    }
    return result || "A";
  }

  function normalizeRows(rows, columns) {
    var normalized = safeRows(rows);
    var headers = Array.isArray(columns) ? columns.slice() : [];
    normalized.forEach(function (row) {
      Object.keys(row || {}).forEach(function (key) {
        if (headers.indexOf(key) === -1) {
          headers.push(key);
        }
      });
    });
    if (!headers.length) {
      headers = ["Info"];
    }
    return {
      headers: headers,
      rows: normalized.map(function (row) {
        var output = {};
        headers.forEach(function (key) {
          output[key] = row && Object.prototype.hasOwnProperty.call(row, key) ? row[key] : null;
        });
        return output;
      })
    };
  }

  function computeColumnWidths(headers, rows) {
    return headers.map(function (key) {
      var maxLen = String(key).length;
      rows.forEach(function (row) {
        var text = row[key] == null ? "" : String(row[key]);
        if (text.length > maxLen) {
          maxLen = text.length;
        }
      });
      return { wch: Math.min(Math.max(maxLen + 2, 12), 42) };
    });
  }

  function buildTableSheet(title, subtitle, rows, options) {
    if (!root.XLSX || !root.XLSX.utils) {
      throw new Error("XLSX no disponible");
    }

    options = options || {};
    var prepared = normalizeRows(rows, options.columns);
    var headers = prepared.headers;
    var normalizedRows = prepared.rows;
    var sheet = root.XLSX.utils.aoa_to_sheet([
      [title || "Siegfried"],
      [subtitle || ""],
      [],
      headers
    ]);

    root.XLSX.utils.sheet_add_json(sheet, normalizedRows, {
      origin: "A5",
      header: headers,
      skipHeader: true
    });

    var lastCol = columnLetter(headers.length - 1);
    var lastRow = normalizedRows.length + 4;
    sheet["!cols"] = computeColumnWidths(headers, normalizedRows);
    sheet["!rows"] = [{ hpt: 22 }, { hpt: 18 }, { hpt: 8 }, { hpt: 18 }];
    sheet["!merges"] = [
      root.XLSX.utils.decode_range("A1:" + lastCol + "1"),
      root.XLSX.utils.decode_range("A2:" + lastCol + "2")
    ];
    sheet["!autofilter"] = { ref: "A4:" + lastCol + lastRow };

    return sheet;
  }

  function appendTableSheet(workbook, seen, sheetName, title, subtitle, rows, options) {
    root.XLSX.utils.book_append_sheet(
      workbook,
      buildTableSheet(title, subtitle, rows, options),
      uniqueSheetName(sheetName, seen)
    );
  }

  function sanitizeFilePart(text) {
    return String(text || "Datos")
      .replace(/[^A-Za-z0-9_-]+/g, "_")
      .replace(/^_+|_+$/g, "") || "Datos";
  }

  function inferStamp(footer) {
    if (footer) {
      return String(footer).replace(/[^\dA-Za-z]+/g, "-").replace(/^-+|-+$/g, "");
    }
    return new Date().toISOString().slice(0, 10);
  }

  function nowLabel() {
    try {
      return new Date().toLocaleString("es-AR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      });
    } catch (error) {
      return new Date().toISOString().slice(0, 16).replace("T", " ");
    }
  }

  function makeSubtitle(context, rowCount, extra) {
    var pieces = [];
    if (context && context.title) {
      pieces.push("Linea: " + context.title);
    }
    pieces.push("Exportado: " + nowLabel());
    if (context && context.footer) {
      pieces.push("Corte: " + context.footer);
    }
    if (typeof rowCount === "number") {
      pieces.push("Filas: " + rowCount);
    }
    if (extra) {
      pieces.push(extra);
    }
    return pieces.join(" | ");
  }

  function countKeys(obj) {
    return obj ? Object.keys(obj).length : 0;
  }

  function sumBy(items, getter) {
    if (!Array.isArray(items)) {
      return 0;
    }
    return items.reduce(function (acc, item, index) {
      return acc + (Number(getter(item, index)) || 0);
    }, 0);
  }

  function createActionButton(attrName, text, className, handler, extraStyles) {
    var button = document.createElement("a");
    button.href = "javascript:void(0)";
    button.className = className;
    button.setAttribute(attrName, "true");
    button.textContent = text;
    button.onclick = handler;
    Object.keys(extraStyles || {}).forEach(function (key) {
      button.style[key] = extraStyles[key];
    });
    return button;
  }

  function setButtonState(selector, isBusy) {
    var nodes = document.querySelectorAll(selector);
    nodes.forEach(function (node) {
      if (!node.dataset.defaultLabel) {
        node.dataset.defaultLabel = node.textContent.trim();
      }
      node.disabled = isBusy;
      node.style.opacity = isBusy ? "0.7" : "1";
      node.style.pointerEvents = isBusy ? "none" : "auto";
      node.textContent = isBusy ? "Exportando..." : node.dataset.defaultLabel;
    });
  }

  function mountWhenReady(fn) {
    if (typeof document === "undefined") {
      return;
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
      return;
    }
    fn();
  }

  root.SfExportCommon = {
    appendTableSheet: appendTableSheet,
    buildTableSheet: buildTableSheet,
    countKeys: countKeys,
    createActionButton: createActionButton,
    inferStamp: inferStamp,
    makeSubtitle: makeSubtitle,
    mountWhenReady: mountWhenReady,
    nowLabel: nowLabel,
    sanitizeFilePart: sanitizeFilePart,
    setButtonState: setButtonState,
    sumBy: sumBy,
    uniqueSheetName: uniqueSheetName,
    valueOrNull: valueOrNull
  };
})();
