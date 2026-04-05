(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;
  var common = root.SfExportCommon;

  if (!common) {
    return;
  }

  function exportConfig() {
    return root.__SFG_DDD_EXPORT__ || null;
  }

  function exportData(cfg) {
    return cfg && cfg.data ? cfg.data : null;
  }

  function lineTitle(cfg) {
    return cfg && (cfg.title || cfg.line || cfg.filePrefix) ? (cfg.title || cfg.line || cfg.filePrefix) : "Linea";
  }

  function footerLabel(data, cfg) {
    if (cfg && cfg.footer) {
      return cfg.footer;
    }
    if (data && data.meta) {
      return data.meta.comp_month_label || data.meta.ms_title_label || "";
    }
    if (data && Array.isArray(data.months) && data.months.length) {
      return data.months[data.months.length - 1];
    }
    return "";
  }

  function dddContext(cfg, data) {
    return {
      title: lineTitle(cfg),
      footer: footerLabel(data, cfg)
    };
  }

  function marketNames(data) {
    if (!data || !data.markets) {
      return [];
    }
    if (Array.isArray(data.marketOrder) && data.marketOrder.length) {
      return data.marketOrder.filter(function (name) {
        return data.markets[name];
      });
    }
    return Object.keys(data.markets);
  }

  function marketEntry(data, marketName) {
    return data && data.markets ? data.markets[marketName] || null : null;
  }

  function regionNames(data, market) {
    var configured = Array.isArray(data && data.regions) ? data.regions : [];
    if (configured.length) {
      return configured.filter(function (region) {
        return region !== "__NAC__" && (!market || !market.region_data || market.region_data[region]);
      });
    }
    return Object.keys((market && market.region_data) || {}).filter(function (region) {
      return region !== "__NAC__";
    });
  }

  function normalizeRegion(region) {
    if (region === "__NAC__") {
      return "Nacional";
    }
    return String(region || "").replace(/^_/, "");
  }

  function normalizeQuarterName(label, index) {
    if (label) {
      return label;
    }
    return "Q" + String(index + 1);
  }

  function safeSeries(series, fallbackLength) {
    if (Array.isArray(series)) {
      return series.slice();
    }
    return Array(Math.max(0, fallbackLength || 0)).fill(0);
  }

  function sumSeries(seriesList, length) {
    var targetLength = length || common.sumBy(seriesList, function (series) {
      return Array.isArray(series) ? series.length : 0;
    });
    var result = Array(Math.max(0, targetLength)).fill(0);
    (seriesList || []).forEach(function (series) {
      if (!Array.isArray(series)) {
        return;
      }
      for (var idx = 0; idx < targetLength; idx += 1) {
        result[idx] += Number(series[idx]) || 0;
      }
    });
    return result;
  }

  function monthlyToQuarterly(series, labels) {
    var output = [];
    for (var quarterIndex = 0; quarterIndex < labels.length; quarterIndex += 1) {
      var start = quarterIndex * 3;
      var sum = 0;
      for (var offset = 0; offset < 3; offset += 1) {
        sum += Number(series[start + offset]) || 0;
      }
      output.push(sum);
    }
    return output;
  }

  function sieBrands(market) {
    return (market && Array.isArray(market.brands) ? market.brands : []).filter(function (brand) {
      return market.brand_meta && market.brand_meta[brand] && market.brand_meta[brand].sie;
    });
  }

  function brandSeries(market, brand, region, monthCount) {
    var brandData = market && market.brand_monthly ? market.brand_monthly[brand] : null;
    return safeSeries(brandData && brandData[region], monthCount);
  }

  function totalSeries(market, region, monthCount) {
    return safeSeries(market && market.total_monthly ? market.total_monthly[region] : null, monthCount);
  }

  function sieRegionSeries(data, market, region) {
    var monthCount = Array.isArray(data && data.months) ? data.months.length : 0;
    return sumSeries(sieBrands(market).map(function (brand) {
      return brandSeries(market, brand, region, monthCount);
    }), monthCount);
  }

  function percent(part, total) {
    if (!total) {
      return null;
    }
    return +((Number(part) || 0) / total * 100).toFixed(1);
  }

  function buildOverviewRows(data, cfg) {
    var names = marketNames(data);
    var totalSie = common.sumBy(names, function (name) {
      var market = marketEntry(data, name);
      return market ? market.sie_units : 0;
    });
    var totalMarket = common.sumBy(names, function (name) {
      var market = marketEntry(data, name);
      return market ? market.total_units : 0;
    });

    return [
      { Indicador: "Linea", Valor: lineTitle(cfg) },
      { Indicador: "Vista", Valor: "DDD" },
      { Indicador: "Mercados", Valor: names.length },
      { Indicador: "Regiones", Valor: common.countKeys(data && data.regions) || 0 },
      { Indicador: "Meses", Valor: common.countKeys(data && data.months) || 0 },
      { Indicador: "Trimestres", Valor: common.countKeys(data && data.quarters) || 0 },
      { Indicador: "Unidades Siegfried", Valor: common.valueOrNull(totalSie) },
      { Indicador: "Unidades Mercado", Valor: common.valueOrNull(totalMarket) },
      { Indicador: "MS ponderado", Valor: percent(totalSie, totalMarket) },
      { Indicador: "Corte", Valor: footerLabel(data, cfg) || "" }
    ];
  }

  function buildMetaRows(data, cfg) {
    var rows = [
      { Campo: "linea", Valor: lineTitle(cfg) },
      { Campo: "file_prefix", Valor: cfg && cfg.filePrefix ? cfg.filePrefix : "" },
      { Campo: "months", Valor: Array.isArray(data && data.months) ? data.months.join(" | ") : "" },
      { Campo: "quarters", Valor: Array.isArray(data && data.quarters) ? data.quarters.join(" | ") : "" }
    ];
    var meta = (data && data.meta) || {};
    Object.keys(meta).forEach(function (key) {
      rows.push({
        Campo: "meta." + key,
        Valor: typeof meta[key] === "object" ? JSON.stringify(meta[key]) : String(meta[key])
      });
    });
    return rows;
  }

  function buildMarketSummaryRows(data) {
    return marketNames(data).map(function (marketName) {
      var market = marketEntry(data, marketName);
      var sieList = sieBrands(market);
      return {
        Mercado: marketName,
        Clase: market && market.clase ? market.clase : "",
        Marcas_total: market && market.brands ? market.brands.length : 0,
        Marcas_siegfried: sieList.length,
        Unid_siegfried: common.valueOrNull(market && market.sie_units),
        Unid_mercado: common.valueOrNull(market && market.total_units),
        MS_nacional: common.valueOrNull(market && market.global_ms)
      };
    });
  }

  function buildBrandSummaryRows(data) {
    var rows = [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      (market && market.brands ? market.brands : []).forEach(function (brand) {
        var meta = market.brand_meta && market.brand_meta[brand] ? market.brand_meta[brand] : {};
        rows.push({
          Mercado: marketName,
          Marca: brand,
          Es_siegfried: meta.sie ? "Si" : "No",
          Unidades_total: common.valueOrNull(meta.units)
        });
      });
    });
    return rows;
  }

  function buildBrandMonthlyRows(data) {
    var rows = [];
    var months = Array.isArray(data && data.months) ? data.months : [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      var totalNational = totalSeries(market, "__NAC__", months.length);
      (market && market.brands ? market.brands : []).forEach(function (brand) {
        var meta = market.brand_meta && market.brand_meta[brand] ? market.brand_meta[brand] : {};
        var series = brandSeries(market, brand, "__NAC__", months.length);
        months.forEach(function (month, index) {
          rows.push({
            Mercado: marketName,
            Marca: brand,
            Mes: month,
            Es_siegfried: meta.sie ? "Si" : "No",
            Unid_marca: common.valueOrNull(series[index]),
            Unid_mercado: common.valueOrNull(totalNational[index]),
            MS_marca: percent(series[index], totalNational[index])
          });
        });
      });
    });
    return rows;
  }

  function buildMarketMonthlyRows(data) {
    var rows = [];
    var months = Array.isArray(data && data.months) ? data.months : [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      var totalNational = totalSeries(market, "__NAC__", months.length);
      var sieNational = sieRegionSeries(data, market, "__NAC__");
      months.forEach(function (month, index) {
        rows.push({
          Mercado: marketName,
          Mes: month,
          Unid_siegfried: common.valueOrNull(sieNational[index]),
          Unid_mercado: common.valueOrNull(totalNational[index]),
          MS_siegfried: percent(sieNational[index], totalNational[index])
        });
      });
    });
    return rows;
  }

  function buildMarketQuarterRows(data) {
    var rows = [];
    var quarters = Array.isArray(data && data.quarters) ? data.quarters : [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      var totalQuarterly = monthlyToQuarterly(totalSeries(market, "__NAC__", quarters.length * 3), quarters);
      var sieQuarterly = monthlyToQuarterly(sieRegionSeries(data, market, "__NAC__"), quarters);
      quarters.forEach(function (quarter, index) {
        rows.push({
          Mercado: marketName,
          Trimestre: normalizeQuarterName(quarter, index),
          Unid_siegfried: common.valueOrNull(sieQuarterly[index]),
          Unid_mercado: common.valueOrNull(totalQuarterly[index]),
          MS_siegfried: percent(sieQuarterly[index], totalQuarterly[index])
        });
      });
    });
    return rows;
  }

  function buildRegionSummaryRows(data) {
    var rows = [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      regionNames(data, market).forEach(function (region) {
        var regionData = market.region_data && market.region_data[region] ? market.region_data[region] : {};
        rows.push({
          Mercado: marketName,
          Region: normalizeRegion(region),
          Unid_siegfried: common.valueOrNull(regionData.sie),
          Unid_mercado: common.valueOrNull(regionData.total),
          MS_region: common.valueOrNull(regionData.ms),
          MS_vs_nacional_pp: regionData.ms != null && market.global_ms != null ? +((regionData.ms || 0) - (market.global_ms || 0)).toFixed(1) : null
        });
      });
    });
    return rows;
  }

  function buildRegionMonthlyRows(data) {
    var rows = [];
    var months = Array.isArray(data && data.months) ? data.months : [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      regionNames(data, market).forEach(function (region) {
        var totalRegion = totalSeries(market, region, months.length);
        var sieRegion = sieRegionSeries(data, market, region);
        months.forEach(function (month, index) {
          rows.push({
            Mercado: marketName,
            Region: normalizeRegion(region),
            Mes: month,
            Unid_siegfried: common.valueOrNull(sieRegion[index]),
            Unid_mercado: common.valueOrNull(totalRegion[index]),
            MS_region: percent(sieRegion[index], totalRegion[index])
          });
        });
      });
    });
    return rows;
  }

  function buildRegionQuarterRows(data) {
    var rows = [];
    var quarters = Array.isArray(data && data.quarters) ? data.quarters : [];
    marketNames(data).forEach(function (marketName) {
      var market = marketEntry(data, marketName);
      regionNames(data, market).forEach(function (region) {
        var totalQuarterly = monthlyToQuarterly(totalSeries(market, region, quarters.length * 3), quarters);
        var sieQuarterly = monthlyToQuarterly(sieRegionSeries(data, market, region), quarters);
        quarters.forEach(function (quarter, index) {
          rows.push({
            Mercado: marketName,
            Region: normalizeRegion(region),
            Trimestre: normalizeQuarterName(quarter, index),
            Unid_siegfried: common.valueOrNull(sieQuarterly[index]),
            Unid_mercado: common.valueOrNull(totalQuarterly[index]),
            MS_region: percent(sieQuarterly[index], totalQuarterly[index])
          });
        });
      });
    });
    return rows;
  }

  function workbookFileName(cfg, data) {
    var prefix = common.sanitizeFilePart((cfg && cfg.filePrefix) || lineTitle(cfg));
    return prefix + "_DDD_Datos_" + common.inferStamp(footerLabel(data, cfg)) + ".xlsx";
  }

  function buildWorkbookFromConfig(cfg) {
    var data = exportData(cfg);
    if (!data) {
      throw new Error("No se encontro la data regional");
    }

    var workbook = root.XLSX.utils.book_new();
    var seen = new Set();
    var context = dddContext(cfg, data);
    var entries = [];

    common.ensureWorkbookChrome(workbook, seen);

    var sheets = [
      ["Resumen", "Resumen DDD", buildOverviewRows(data, cfg), "Resumen Regional"],
      ["Meta", "Metadatos DDD", buildMetaRows(data, cfg), "Resumen Regional"],
      ["Mercado_Resumen", "Mercados", buildMarketSummaryRows(data), "Mercados"],
      ["Mercado_Mes", "Mercados por Mes", buildMarketMonthlyRows(data), "Mercados"],
      ["Mercado_Trim", "Mercados por Trimestre", buildMarketQuarterRows(data), "Mercados"],
      ["Marca_Resumen", "Marcas", buildBrandSummaryRows(data), "Marcas"],
      ["Marca_Mes", "Marcas por Mes", buildBrandMonthlyRows(data), "Marcas"],
      ["Region_Resumen", "Regiones", buildRegionSummaryRows(data), "Regiones"],
      ["Region_Mes", "Regiones por Mes", buildRegionMonthlyRows(data), "Regiones"],
      ["Region_Trim", "Regiones por Trimestre", buildRegionQuarterRows(data), "Regiones"]
    ];

    sheets.forEach(function (item) {
      entries.push(common.appendTableSheet(
        workbook,
        seen,
        item[0],
        "Siegfried | " + context.title + " | " + item[1],
        common.makeSubtitle(context, item[2].length),
        item[2],
        {
          group: item[3],
          label: item[1],
          description: item[1]
        }
      ));
    });

    common.finalizeWorkbook(workbook, context, entries, {
      kind: "Vista Regional DDD"
    });

    return workbook;
  }

  function exportWorkbook() {
    var cfg = exportConfig();
    var data = exportData(cfg);
    if (!common || !common.ensureStyledXlsx) {
      root.alert("No se pudo preparar la exportacion de Excel.");
      return;
    }
    if (!data) {
      root.alert("No se encontro la data regional para exportar.");
      return;
    }

    common.setButtonState("[data-export-ddd]", true);
    common.ensureStyledXlsx()
      .then(function () {
        root.setTimeout(function () {
          try {
            var workbook = buildWorkbookFromConfig(cfg);
            root.XLSX.writeFile(workbook, workbookFileName(cfg, data));
          } catch (error) {
            console.error(error);
            root.alert("No se pudo generar el Excel regional.");
          } finally {
            common.setButtonState("[data-export-ddd]", false);
          }
        }, 0);
      })
      .catch(function (error) {
        console.error(error);
        root.alert("No se pudo cargar la libreria de Excel.");
        common.setButtonState("[data-export-ddd]", false);
      });
  }

  function mountButton() {
    var cfg = exportConfig();
    var navRight = document.querySelector(".nav-right");
    if (!cfg || !navRight || document.querySelector("[data-export-ddd]")) {
      return;
    }

    var hubLink = navRight.querySelector(".nav-hub");
    navRight.insertBefore(
      common.createActionButton("data-export-ddd", "Exportar Excel", "nav-hub", exportWorkbook, {
        padding: "6px 10px",
        border: "1px solid var(--bd)",
        borderRadius: "8px"
      }),
      hubLink || navRight.firstChild
    );
  }

  root.SfDddExport = {
    buildWorkbook: buildWorkbookFromConfig,
    exportWorkbook: exportWorkbook,
    mountButton: mountButton
  };

  common.mountWhenReady(mountButton);
})();
