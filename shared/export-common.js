(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;

  var PALETTE = {
    brand: "B51F24",
    brandDark: "8E171D",
    brandSoft: "FBECEC",
    brandTint: "F7D7D9",
    ink: "1F2937",
    muted: "6B7280",
    border: "E5E7EB",
    borderStrong: "D1D5DB",
    surface: "FFFFFF",
    surfaceAlt: "F9FAFB",
    surfaceMuted: "F3F4F6",
    link: "1D4ED8",
    linkFill: "E8F0FE",
    okFill: "ECFDF5"
  };

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

  function cellAddress(rowIndex, columnIndex) {
    return columnLetter(columnIndex) + String(rowIndex + 1);
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

  function humanizeHeader(key) {
    return String(key || "")
      .replace(/_/g, " ")
      .replace(/\bPct\b/gi, "%")
      .replace(/\bMs\b/g, "MS")
      .replace(/\bIqvia\b/gi, "IQVIA")
      .replace(/\bArs\b/gi, "ARS")
      .replace(/\bPvp\b/gi, "PVP")
      .replace(/\bDdd\b/gi, "DDD")
      .replace(/\bOs\b/gi, "OS")
      .replace(/\s+/g, " ")
      .trim();
  }

  function textLength(value) {
    return value == null ? 0 : String(value).length;
  }

  function computeColumnWidths(headers, rows) {
    return headers.map(function (key) {
      var maxLen = Math.max(textLength(humanizeHeader(key)), 12);
      rows.forEach(function (row) {
        maxLen = Math.max(maxLen, textLength(row[key]));
      });
      return { wch: Math.min(maxLen + 3, 38) };
    });
  }

  function border(color) {
    var line = { style: "thin", color: { rgb: color || PALETTE.border } };
    return { top: line, right: line, bottom: line, left: line };
  }

  function baseFont(size, bold, color) {
    return {
      name: "Calibri",
      sz: size,
      bold: !!bold,
      color: { rgb: color || PALETTE.ink }
    };
  }

  function titleStyle() {
    return {
      font: baseFont(16, true, "FFFFFF"),
      fill: { fgColor: { rgb: PALETTE.brand } },
      alignment: { vertical: "center", horizontal: "left" }
    };
  }

  function subtitleStyle() {
    return {
      font: baseFont(10, false, PALETTE.muted),
      fill: { fgColor: { rgb: PALETTE.brandSoft } },
      alignment: { vertical: "center", horizontal: "left", wrapText: true }
    };
  }

  function navStyle() {
    return {
      font: baseFont(10, true, PALETTE.link),
      fill: { fgColor: { rgb: PALETTE.linkFill } },
      border: border(PALETTE.borderStrong),
      alignment: { vertical: "center", horizontal: "center" }
    };
  }

  function infoStyle() {
    return {
      font: baseFont(9, false, PALETTE.ink),
      fill: { fgColor: { rgb: PALETTE.surfaceMuted } },
      border: border(PALETTE.borderStrong),
      alignment: { vertical: "center", horizontal: "left", wrapText: true }
    };
  }

  function groupStyle() {
    return {
      font: baseFont(10, true, PALETTE.brandDark),
      fill: { fgColor: { rgb: PALETTE.brandTint } },
      border: border(PALETTE.borderStrong),
      alignment: { vertical: "center", horizontal: "left" }
    };
  }

  function headerStyle() {
    return {
      font: baseFont(10, true, "FFFFFF"),
      fill: { fgColor: { rgb: PALETTE.brandDark } },
      border: border(PALETTE.brandDark),
      alignment: { vertical: "center", horizontal: "center", wrapText: true }
    };
  }

  function bodyStyle(isEven, alignment) {
    return {
      font: baseFont(10, false, PALETTE.ink),
      fill: { fgColor: { rgb: isEven ? PALETTE.surfaceAlt : PALETTE.surface } },
      border: border(PALETTE.border),
      alignment: { vertical: "center", horizontal: alignment || "left", wrapText: false }
    };
  }

  function statLabelStyle() {
    return {
      font: baseFont(10, true, PALETTE.muted),
      fill: { fgColor: { rgb: PALETTE.surfaceMuted } },
      border: border(PALETTE.borderStrong),
      alignment: { vertical: "center", horizontal: "left" }
    };
  }

  function statValueStyle() {
    return {
      font: baseFont(11, true, PALETTE.ink),
      fill: { fgColor: { rgb: PALETTE.surface } },
      border: border(PALETTE.borderStrong),
      alignment: { vertical: "center", horizontal: "left" }
    };
  }

  function inferNumberFormat(header, value) {
    if (typeof value !== "number" || !isFinite(value)) {
      return null;
    }
    var key = String(header || "").toLowerCase();
    if (/(^|_)(ms|pct|pp)($|_)|%|delta|variacion|cumplimiento|share/.test(key)) {
      if (/pp/.test(key)) {
        return '0.0" pp";[Red]-0.0" pp"';
      }
      return '0.0"%";[Red]-0.0"%"';
    }
    if (/ars|pvp|precio|neto|valor/.test(key)) {
      return '"AR$" #,##0.00;[Red]-"AR$" #,##0.00';
    }
    if (Math.round(value) !== value) {
      return '#,##0.0;[Red]-#,##0.0';
    }
    return '#,##0;[Red]-#,##0';
  }

  function setCell(sheet, address, value, style, link, format) {
    var cell;
    if (typeof value === "number" && isFinite(value)) {
      cell = { t: "n", v: value };
      if (format) {
        cell.z = format;
      }
    } else if (typeof value === "boolean") {
      cell = { t: "b", v: value };
    } else {
      cell = { t: "s", v: value == null ? "" : String(value) };
    }
    if (style) {
      cell.s = style;
    }
    if (link) {
      cell.l = {
        Target: link.target || link,
        Tooltip: link.tooltip || link.target || link
      };
    }
    sheet[address] = cell;
  }

  function addMerge(merges, startRow, startCol, endRow, endCol) {
    merges.push({
      s: { r: startRow, c: startCol },
      e: { r: endRow, c: endCol }
    });
  }

  function decorateTableSheet(sheet, headers, normalizedRows, options) {
    var displayHeaders = headers.map(humanizeHeader);
    var dataStartRow = 6;
    var lastColumnIndex = Math.max(headers.length - 1, 0);
    var merges = [];
    var title = options.title || "Siegfried";
    var subtitle = options.subtitle || "";
    var groupLabel = options.group ? "Bloque: " + options.group : "Datos exportados";
    var infoText = "Columnas: " + headers.length + " | Filas: " + normalizedRows.length + (options.note ? " | " + options.note : "");

    setCell(sheet, "A1", title, titleStyle());
    setCell(sheet, "A2", subtitle, subtitleStyle());
    setCell(sheet, "A3", "← Ir al indice", navStyle(), { target: "#'Indice'!A1", tooltip: "Volver al indice" });
    setCell(sheet, "B3", "↖ Ir a portada", navStyle(), { target: "#'Portada'!A1", tooltip: "Volver a portada" });
    setCell(sheet, cellAddress(2, 2), infoText, infoStyle());
    setCell(sheet, "A4", groupLabel, groupStyle());

    addMerge(merges, 0, 0, 0, lastColumnIndex);
    addMerge(merges, 1, 0, 1, lastColumnIndex);
    if (lastColumnIndex >= 2) {
      addMerge(merges, 2, 2, 2, lastColumnIndex);
    }
    addMerge(merges, 3, 0, 3, lastColumnIndex);

    displayHeaders.forEach(function (header, index) {
      setCell(sheet, cellAddress(5, index), header, headerStyle());
    });

    normalizedRows.forEach(function (row, rowIndex) {
      var isEven = rowIndex % 2 === 0;
      headers.forEach(function (key, columnIndex) {
        var value = row[key];
        var format = inferNumberFormat(key, value);
        var alignment = typeof value === "number" ? "right" : "left";
        setCell(
          sheet,
          cellAddress(dataStartRow + rowIndex, columnIndex),
          value,
          bodyStyle(isEven, alignment),
          null,
          format
        );
      });
    });

    sheet["!cols"] = computeColumnWidths(headers, normalizedRows);
    sheet["!rows"] = [
      { hpt: 24 },
      { hpt: 32 },
      { hpt: 22 },
      { hpt: 20 },
      { hpt: 8 },
      { hpt: 22 }
    ];
    sheet["!merges"] = merges;
    sheet["!autofilter"] = {
      ref: "A6:" + columnLetter(lastColumnIndex) + String(normalizedRows.length + dataStartRow)
    };
  }

  function buildTableSheet(title, subtitle, rows, options) {
    if (!root.XLSX || !root.XLSX.utils) {
      throw new Error("XLSX no disponible");
    }

    options = options || {};
    var prepared = normalizeRows(rows, options.columns);
    var headers = prepared.headers;
    var normalizedRows = prepared.rows;
    var dataMatrix = normalizedRows.map(function (row) {
      return headers.map(function (key) {
        return row[key];
      });
    });
    var sheet = root.XLSX.utils.aoa_to_sheet([
      [title || "Siegfried"],
      [subtitle || ""],
      ["", "", ""],
      [""],
      [""],
      headers.map(humanizeHeader)
    ].concat(dataMatrix));

    decorateTableSheet(sheet, headers, normalizedRows, {
      title: title,
      subtitle: subtitle,
      group: options.group,
      note: options.note
    });

    return sheet;
  }

  function appendTableSheet(workbook, seen, sheetName, title, subtitle, rows, options) {
    var actualName = uniqueSheetName(sheetName, seen);
    var originalCount = Array.isArray(rows) ? rows.length : 0;
    root.XLSX.utils.book_append_sheet(
      workbook,
      buildTableSheet(title, subtitle, rows, options),
      actualName
    );
    return {
      name: actualName,
      group: options && options.group ? options.group : "General",
      label: options && options.label ? options.label : actualName,
      description: options && options.description ? options.description : title,
      rows: originalCount
    };
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

  function ensureStyledXlsx() {
    if (root.__sfStyledXlsxReady) {
      return root.__sfStyledXlsxReady;
    }

    var existingStyledScript = null;
    if (typeof document !== "undefined") {
      existingStyledScript = Array.prototype.slice.call(document.scripts || []).find(function (script) {
        return /xlsx-js-style/i.test(script.src || "");
      }) || null;
    }

    if (existingStyledScript && root.XLSX) {
      root.__sfStyledXlsxReady = Promise.resolve(root.XLSX);
      return root.__sfStyledXlsxReady;
    }

    root.__sfStyledXlsxReady = new Promise(function (resolve, reject) {
      if (typeof document === "undefined") {
        if (root.XLSX) {
          resolve(root.XLSX);
          return;
        }
        reject(new Error("No se puede cargar xlsx-js-style fuera del navegador."));
        return;
      }

      var script = existingStyledScript || document.createElement("script");
      if (!existingStyledScript) {
        script.src = "https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js";
        script.async = true;
      }

      script.onload = function () {
        if (root.XLSX) {
          resolve(root.XLSX);
          return;
        }
        reject(new Error("La libreria de Excel no quedo disponible."));
      };
      script.onerror = function () {
        reject(new Error("No se pudo cargar xlsx-js-style."));
      };

      if (!existingStyledScript) {
        document.head.appendChild(script);
      }
    });

    return root.__sfStyledXlsxReady;
  }

  function buildCoverSheet(context, entries, options) {
    var kind = options && options.kind ? options.kind : "Exportable";
    var rows = [];
    var totalRows = sumBy(entries, function (entry) { return entry.rows || 0; });
    var firstDataSheet = entries.length ? entries[0].name : "Indice";

    rows.push(["Siegfried | " + (context.title || "Linea") + " | " + kind]);
    rows.push([makeSubtitle(context, totalRows, "Hojas de datos: " + entries.length)]);
    rows.push([]);
    rows.push(["Linea", context.title || ""]);
    rows.push(["Vista", kind]);
    rows.push(["Corte", (context && context.footer) || ""]);
    rows.push(["Exportado", nowLabel()]);
    rows.push(["Hojas de datos", entries.length]);
    rows.push(["Filas totales", totalRows]);
    rows.push([]);
    rows.push(["Abrir indice", "Ir al indice"]);
    rows.push(["Primera hoja", firstDataSheet]);
    rows.push([]);
    rows.push(["Bloque", "Descripcion", "Filas"]);

    entries.forEach(function (entry) {
      rows.push([entry.group, entry.label, entry.rows || 0]);
    });

    var sheet = root.XLSX.utils.aoa_to_sheet(rows);
    var lastCol = 2;
    var merges = [];

    setCell(sheet, "A1", rows[0][0], titleStyle());
    setCell(sheet, "A2", rows[1][0], subtitleStyle());
    addMerge(merges, 0, 0, 0, lastCol);
    addMerge(merges, 1, 0, 1, lastCol);

    for (var infoRow = 3; infoRow <= 8; infoRow += 1) {
      setCell(sheet, cellAddress(infoRow, 0), rows[infoRow][0], statLabelStyle());
      setCell(sheet, cellAddress(infoRow, 1), rows[infoRow][1], statValueStyle(), null, typeof rows[infoRow][1] === "number" ? '#,##0' : null);
      addMerge(merges, infoRow, 1, infoRow, lastCol);
    }

    setCell(sheet, "A11", "Ir al indice", navStyle(), { target: "#'Indice'!A1", tooltip: "Abrir indice" });
    setCell(sheet, "B11", "Ver hojas", navStyle(), { target: "#'Indice'!A4", tooltip: "Abrir indice detallado" });
    setCell(sheet, "A12", "Primera hoja", statLabelStyle());
    setCell(sheet, "B12", firstDataSheet, navStyle(), { target: "#'" + firstDataSheet + "'!A1", tooltip: "Abrir " + firstDataSheet });
    addMerge(merges, 11, 1, 11, lastCol);

    setCell(sheet, "A14", "Bloque", headerStyle());
    setCell(sheet, "B14", "Descripcion", headerStyle());
    setCell(sheet, "C14", "Filas", headerStyle());

    entries.forEach(function (entry, index) {
      var rowIndex = 14 + index;
      var even = index % 2 === 0;
      setCell(sheet, cellAddress(rowIndex, 0), entry.group, bodyStyle(even, "left"));
      setCell(
        sheet,
        cellAddress(rowIndex, 1),
        entry.label,
        bodyStyle(even, "left"),
        { target: "#'" + entry.name + "'!A1", tooltip: "Abrir " + entry.name }
      );
      setCell(sheet, cellAddress(rowIndex, 2), entry.rows || 0, bodyStyle(even, "right"), null, '#,##0');
    });

    sheet["!cols"] = [{ wch: 18 }, { wch: 46 }, { wch: 12 }];
    sheet["!rows"] = [{ hpt: 24 }, { hpt: 26 }];
    sheet["!merges"] = merges;
    return sheet;
  }

  function buildIndexSheet(context, entries, options) {
    var kind = options && options.kind ? options.kind : "Exportable";
    var rows = [
      ["Indice de navegacion | " + (context.title || "Linea")],
      [makeSubtitle(context, sumBy(entries, function (entry) { return entry.rows || 0; }), kind)],
      [],
      ["Grupo", "Hoja", "Descripcion", "Filas", "Ir"]
    ];

    entries.forEach(function (entry) {
      rows.push([entry.group, entry.name, entry.label, entry.rows || 0, "Abrir"]);
    });

    var sheet = root.XLSX.utils.aoa_to_sheet(rows);
    var merges = [];
    addMerge(merges, 0, 0, 0, 4);
    addMerge(merges, 1, 0, 1, 4);

    setCell(sheet, "A1", rows[0][0], titleStyle());
    setCell(sheet, "A2", rows[1][0], subtitleStyle());
    setCell(sheet, "A3", "↖ Volver a portada", navStyle(), { target: "#'Portada'!A1", tooltip: "Volver a portada" });
    addMerge(merges, 2, 1, 2, 4);
    setCell(sheet, "B3", "Usa la columna Ir para navegar entre hojas", infoStyle());

    ["A4", "B4", "C4", "D4", "E4"].forEach(function (address, index) {
      setCell(sheet, address, rows[3][index], headerStyle());
    });

    entries.forEach(function (entry, index) {
      var rowIndex = 4 + index;
      var even = index % 2 === 0;
      setCell(sheet, cellAddress(rowIndex, 0), entry.group, bodyStyle(even, "left"));
      setCell(
        sheet,
        cellAddress(rowIndex, 1),
        entry.name,
        bodyStyle(even, "left"),
        { target: "#'" + entry.name + "'!A1", tooltip: "Abrir " + entry.name }
      );
      setCell(sheet, cellAddress(rowIndex, 2), entry.label, bodyStyle(even, "left"));
      setCell(sheet, cellAddress(rowIndex, 3), entry.rows || 0, bodyStyle(even, "right"), null, '#,##0');
      setCell(
        sheet,
        cellAddress(rowIndex, 4),
        "Abrir",
        navStyle(),
        { target: "#'" + entry.name + "'!A1", tooltip: "Abrir " + entry.name }
      );
    });

    sheet["!cols"] = [
      { wch: 18 },
      { wch: 22 },
      { wch: 40 },
      { wch: 12 },
      { wch: 12 }
    ];
    sheet["!rows"] = [{ hpt: 24 }, { hpt: 24 }, { hpt: 22 }, { hpt: 22 }];
    sheet["!merges"] = merges;
    sheet["!autofilter"] = {
      ref: "A4:E" + String(entries.length + 4)
    };
    return sheet;
  }

  function ensureWorkbookChrome(workbook, seen) {
    if (workbook.SheetNames.indexOf("Portada") === -1) {
      root.XLSX.utils.book_append_sheet(workbook, root.XLSX.utils.aoa_to_sheet([["Preparando portada..."]]), uniqueSheetName("Portada", seen));
    }
    if (workbook.SheetNames.indexOf("Indice") === -1) {
      root.XLSX.utils.book_append_sheet(workbook, root.XLSX.utils.aoa_to_sheet([["Preparando indice..."]]), uniqueSheetName("Indice", seen));
    }
  }

  function setWorkbookProps(workbook, context, options) {
    workbook.Props = {
      Title: "Siegfried | " + (context && context.title ? context.title : "Exportable"),
      Subject: options && options.kind ? options.kind : "Exportable de datos",
      Author: "Codex",
      Company: "Siegfried Argentina",
      CreatedDate: new Date()
    };
  }

  function finalizeWorkbook(workbook, context, entries, options) {
    if (!workbook || !workbook.Sheets) {
      return workbook;
    }
    workbook.Sheets.Portada = buildCoverSheet(context || {}, entries || [], options || {});
    workbook.Sheets.Indice = buildIndexSheet(context || {}, entries || [], options || {});
    setWorkbookProps(workbook, context, options);
    return workbook;
  }

  root.SfExportCommon = {
    appendTableSheet: appendTableSheet,
    buildTableSheet: buildTableSheet,
    countKeys: countKeys,
    createActionButton: createActionButton,
    ensureStyledXlsx: ensureStyledXlsx,
    ensureWorkbookChrome: ensureWorkbookChrome,
    finalizeWorkbook: finalizeWorkbook,
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
