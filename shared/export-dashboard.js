(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;
  var common = root.SfExportCommon;

  if (!common) {
    return;
  }

  function exportConfig() {
    return root.__SFG_DASHBOARD_EXPORT__ || null;
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
      return data.meta.footer_date || data.meta.latest_month || "";
    }
    return "";
  }

  function dashboardContext(cfg, data) {
    return {
      title: lineTitle(cfg),
      footer: footerLabel(data, cfg)
    };
  }

  function countPriceRows(data) {
    var total = 0;
    Object.keys(data.precios || {}).forEach(function (brand) {
      Object.keys(data.precios[brand] || {}).forEach(function (presentation) {
        total += (data.precios[brand][presentation] || []).length;
      });
    });
    return total;
  }

  function countIqviaProducts(data) {
    var total = 0;
    Object.keys(data.mol_perf || {}).forEach(function (family) {
      total += (data.mol_perf[family] && data.mol_perf[family].products ? data.mol_perf[family].products.length : 0);
    });
    return total;
  }

  function countRecCompetitors(data) {
    var total = 0;
    Object.keys(data.rec_comp || {}).forEach(function (brand) {
      total += Object.keys(data.rec_comp[brand] || {}).length;
    });
    return total;
  }

  function buildOverviewRows(data, cfg) {
    var kpi = data.kpiStrip || {};
    return [{
      Linea: lineTitle(cfg),
      Exportado: common.nowLabel(),
      Corte_tablero: footerLabel(data, cfg),
      Meses_tablero: (data.meses || []).length,
      Marcas_presupuesto: common.countKeys(data.budget),
      Familias_iqvia: common.countKeys(data.mol_perf),
      Productos_iqvia: countIqviaProducts(data),
      Marcas_recetas: common.countKeys(data.recetas),
      Competidores_recetas: countRecCompetitors(data),
      Presentaciones_stock: common.countKeys(data.stock_pres),
      Presentaciones_precios: countPriceRows(data),
      IE_YTD: common.valueOrNull(kpi.ie_ytd),
      IE_MAT: common.valueOrNull(kpi.ie_mat),
      MS_YTD_pct: common.valueOrNull(kpi.ms_ytd),
      MS_MAT_pct: common.valueOrNull(kpi.ms_mat),
      Unidades_YTD: common.valueOrNull(kpi.units_ytd),
      Unidades_MAT: common.valueOrNull(kpi.units_mat),
      Budget_pct: common.valueOrNull(kpi.bud_pct),
      Real_total: common.valueOrNull(kpi.real_total),
      Budget_total: common.valueOrNull(kpi.bud_total)
    }];
  }

  function buildMetaRows(data, cfg) {
    var rows = [
      { Area: "Exportacion", Campo: "linea", Valor: lineTitle(cfg) },
      { Area: "Exportacion", Campo: "exportado", Valor: common.nowLabel() },
      { Area: "Exportacion", Campo: "corte_tablero", Valor: footerLabel(data, cfg) },
      { Area: "Modelo", Campo: "meses", Valor: (data.meses || []).join(", ") },
      { Area: "Modelo", Campo: "stock_periodos", Valor: (data.stock_pres_months || data.coverage_labels || []).join(", ") }
    ];
    Object.keys(data.meta || {}).forEach(function (key) {
      rows.push({ Area: "Meta", Campo: key, Valor: data.meta[key] });
    });
    return rows;
  }

  function buildGlobalKpiRows(data) {
    return data.kpiStrip ? [data.kpiStrip] : [];
  }

  function buildBrandKpiRows(data) {
    var rows = [];
    if (data.brandKpis) {
      Object.keys(data.brandKpis).forEach(function (brand) {
        var item = data.brandKpis[brand] || {};
        var ytd = item.ytd || {};
        var mat = item.mat || {};
        var budget = item.budget || {};
        var rec = item.rec || {};
        rows.push({
          Marca: brand,
          Familia: data.familyMap && data.familyMap[brand] ? data.familyMap[brand] : "",
          IE_YTD: common.valueOrNull(ytd.ie),
          MS_YTD_pct: common.valueOrNull(ytd.ms),
          Unidades_YTD: common.valueOrNull(ytd.units),
          Unidades_YTD_prev: common.valueOrNull(ytd.units_prev),
          Mercado_YTD: common.valueOrNull(ytd.market_total),
          Growth_YTD_pct: common.valueOrNull(ytd.growth),
          IE_MAT: common.valueOrNull(mat.ie),
          MS_MAT_pct: common.valueOrNull(mat.ms),
          Unidades_MAT: common.valueOrNull(mat.units),
          Unidades_MAT_prev: common.valueOrNull(mat.units_prev),
          Mercado_MAT: common.valueOrNull(mat.market_total),
          Growth_MAT_pct: common.valueOrNull(mat.growth),
          Budget_pct: common.valueOrNull(budget.pct),
          Budget_real: common.valueOrNull(budget.real),
          Budget_target: common.valueOrNull(budget.target),
          Recetas_MS_pct: common.valueOrNull(rec.ms),
          Recetas_label: rec.label || ""
        });
      });
      return rows;
    }

    Object.keys(data.kpiByBrand || {}).forEach(function (brand) {
      var item = data.kpiByBrand[brand] || {};
      rows.push({
        Marca: brand,
        Molecula: item.mol || "",
        IE_YTD: common.valueOrNull(item.ie_ytd),
        IE_MAT: common.valueOrNull(item.ie_mat),
        MS_YTD_pct: common.valueOrNull(item.ms_ytd),
        MS_MAT_pct: common.valueOrNull(item.ms_mat),
        Unidades_YTD: common.valueOrNull(item.units_ytd),
        Unidades_YTD_prev: common.valueOrNull(item.units_ytd25),
        Mercado_YTD: common.valueOrNull(item.mkt_ytd26),
        Unidades_MAT: common.valueOrNull(item.units_mat),
        Unidades_MAT_prev: common.valueOrNull(item.units_mat25),
        Mercado_MAT: common.valueOrNull(item.mkt_mat26),
        Recetas_MS_pct: common.valueOrNull(item.ms_rec),
        Budget_pct: common.valueOrNull(item.bud_pct),
        Budget_total: common.valueOrNull(item.bud_total),
        Real_total: common.valueOrNull(item.real_total)
      });
    });
    return rows;
  }

  function buildBudgetRows(data) {
    var rows = [];
    Object.keys(data.budget || {}).forEach(function (brand) {
      Object.keys(data.budget[brand] || {}).forEach(function (year) {
        var payload = data.budget[brand][year] || {};
        (data.meses || []).forEach(function (month, index) {
          rows.push({
            Marca: brand,
            Anio: year,
            Mes: month,
            Periodo: month + " " + year,
            Budget: common.valueOrNull(payload.budget && payload.budget[index]),
            Real: common.valueOrNull(payload.real && payload.real[index])
          });
        });
      });
    });
    return rows;
  }

  function buildIqviaMonthlyRows(data) {
    var rows = [];
    Object.keys(data.mol_perf || {}).forEach(function (family) {
      var products = data.mol_perf[family] && data.mol_perf[family].products ? data.mol_perf[family].products : [];
      products.forEach(function (product) {
        Object.keys(product.monthly_vals || {}).forEach(function (period) {
          rows.push({
            Familia: family,
            Producto: product.prod || "",
            Laboratorio: product.manuf || "",
            Es_Siegfried: product.is_sie ? "Si" : "No",
            Periodo: period,
            Unidades: common.valueOrNull(product.monthly_vals[period]),
            MS_pct: common.valueOrNull(product.ms_monthly && product.ms_monthly[period])
          });
        });
      });
    });
    return rows;
  }

  function buildIqviaAccumRows(data) {
    var rows = [];
    Object.keys(data.mol_perf || {}).forEach(function (family) {
      var products = data.mol_perf[family] && data.mol_perf[family].products ? data.mol_perf[family].products : [];
      products.forEach(function (product) {
        ["ytd", "mat"].forEach(function (bucket) {
          Object.keys(product[bucket] || {}).forEach(function (period) {
            rows.push({
              Familia: family,
              Producto: product.prod || "",
              Laboratorio: product.manuf || "",
              Es_Siegfried: product.is_sie ? "Si" : "No",
              Vista: bucket.toUpperCase(),
              Periodo: period,
              Unidades: common.valueOrNull(product[bucket][period]),
              MS_pct: common.valueOrNull(product["ms_" + bucket] && product["ms_" + bucket][period])
            });
          });
        });
      });
    });
    return rows;
  }

  function buildIqviaQuarterRows(data) {
    var rows = [];
    Object.keys(data.mol_perf || {}).forEach(function (family) {
      var products = data.mol_perf[family] && data.mol_perf[family].products ? data.mol_perf[family].products : [];
      products.forEach(function (product) {
        Object.keys(product.quarterly_vals || {}).forEach(function (period) {
          rows.push({
            Familia: family,
            Producto: product.prod || "",
            Laboratorio: product.manuf || "",
            Es_Siegfried: product.is_sie ? "Si" : "No",
            Trimestre: period,
            Unidades: common.valueOrNull(product.quarterly_vals[period]),
            MS_pct: common.valueOrNull(product.ms_quarterly && product.ms_quarterly[period])
          });
        });
      });
    });
    return rows;
  }

  function buildRecetasRows(data) {
    var rows = [];
    Object.keys(data.recetas || {}).forEach(function (brand) {
      var item = data.recetas[brand] || {};
      var recMs = data.rec_ms && data.rec_ms[brand] ? data.rec_ms[brand] : {};
      Object.keys(item).forEach(function (period) {
        rows.push({
          Marca: brand,
          Periodo: period,
          Recetas_mercado: common.valueOrNull(item[period] && item[period].recetas),
          Medicos: common.valueOrNull(item[period] && item[period].medicos),
          Recetas_Siegfried: common.valueOrNull(recMs.sie && recMs.sie[period]),
          MS_pct: common.valueOrNull(recMs.ms && recMs.ms[period]),
          Mercado_total_recetas: common.valueOrNull(recMs.mkt && recMs.mkt[period])
        });
      });
    });
    return rows;
  }

  function buildRecetasQuarterRows(data) {
    var rows = [];
    Object.keys(data.rec_ms || {}).forEach(function (brand) {
      var item = data.rec_ms[brand] || {};
      var periods = {};
      Object.keys(item.quarterly || {}).forEach(function (period) { periods[period] = true; });
      Object.keys(item.ms_quarterly || {}).forEach(function (period) { periods[period] = true; });
      Object.keys(periods).forEach(function (period) {
        rows.push({
          Marca: brand,
          Trimestre: period,
          Recetas_Siegfried: common.valueOrNull(item.quarterly && item.quarterly[period]),
          MS_pct: common.valueOrNull(item.ms_quarterly && item.ms_quarterly[period])
        });
      });
    });
    return rows;
  }

  function buildRecCompetitorMonthlyRows(data) {
    var rows = [];
    Object.keys(data.rec_comp || {}).forEach(function (brand) {
      Object.keys(data.rec_comp[brand] || {}).forEach(function (competitor) {
        var item = data.rec_comp[brand][competitor] || {};
        Object.keys(item.monthly || {}).forEach(function (period) {
          rows.push({
            Marca: brand,
            Competidor: competitor,
            Periodo: period,
            Recetas: common.valueOrNull(item.monthly[period])
          });
        });
      });
    });
    return rows;
  }

  function buildRecCompetitorQuarterRows(data) {
    var rows = [];
    Object.keys(data.rec_comp || {}).forEach(function (brand) {
      Object.keys(data.rec_comp[brand] || {}).forEach(function (competitor) {
        var item = data.rec_comp[brand][competitor] || {};
        Object.keys(item.quarterly || {}).forEach(function (period) {
          rows.push({
            Marca: brand,
            Competidor: competitor,
            Trimestre: period,
            Recetas: common.valueOrNull(item.quarterly[period]),
            Total: common.valueOrNull(item.total)
          });
        });
      });
    });
    return rows;
  }

  function buildCanalesRows(data) {
    return Object.keys(data.canales || {}).map(function (brand) {
      var item = data.canales[brand] || {};
      return {
        Marca: brand,
        Unidades_facturadas: common.valueOrNull(item.unid),
        Convenio_pct: common.valueOrNull(item.conv),
        Mostrador_pct: common.valueOrNull(item.most),
        Convenio_unidades: common.valueOrNull(item.conv_units),
        Mostrador_unidades: common.valueOrNull(item.most_units),
        Descuento_total_pct: common.valueOrNull(item.dto_total),
        Descuento_convenio_pct: common.valueOrNull(item.dto_conv),
        Descuento_mostrador_pct: common.valueOrNull(item.dto_most),
        Neto_ARS: common.valueOrNull(item.neto_ars),
        Unidades_previas: common.valueOrNull(item.unid_prev),
        Convenio_pct_prev: common.valueOrNull(item.conv_prev),
        Mostrador_pct_prev: common.valueOrNull(item.most_prev),
        Convenio_pp: common.valueOrNull(item.conv_pp),
        Mostrador_pp: common.valueOrNull(item.most_pp)
      };
    });
  }

  function buildConveniosRows(data) {
    var rows = [];
    Object.keys(data.convenios || {}).forEach(function (brand) {
      (data.convenios[brand] || []).forEach(function (item, index) {
        rows.push({
          Marca: brand,
          Rank: index + 1,
          Obra_social: item.os || "",
          Unidades_2024: common.valueOrNull(item.unid24),
          Unidades_2025: common.valueOrNull(item.unid),
          Delta_pct: common.valueOrNull(item.delta)
        });
      });
    });
    return rows;
  }

  function buildStockRows(data) {
    var rows = [];
    Object.keys(data.stock || {}).forEach(function (brand) {
      Object.keys(data.stock[brand] || {}).forEach(function (period) {
        var item = data.stock[brand][period] || {};
        rows.push({
          Marca: brand,
          Periodo: period,
          Stock_unidades: common.valueOrNull(item.stock),
          Ventas_unidades: common.valueOrNull(item.ventas),
          Facturacion_unidades: common.valueOrNull(item.facturacion),
          Dias_cobertura: common.valueOrNull(item.dias)
        });
      });
    });
    return rows;
  }

  function alertLabels(data, indices) {
    var labels = data.stock_pres_months || data.coverage_labels || [];
    return (indices || []).map(function (index) {
      return labels[index] || ("P" + (index + 1));
    }).join(", ");
  }

  function buildStockAlertRows(data) {
    return Object.keys(data.stock_alerts || {}).map(function (brand) {
      var item = data.stock_alerts[brand] || {};
      return {
        Marca: brand,
        Familia: item.familia || brand,
        Peor_estado: item.worst_status || "",
        Cantidad_alertas: common.valueOrNull(item.n_alerts),
        Periodos_alerta: alertLabels(data, item.alert_indices),
        Indices_alerta: Array.isArray(item.alert_indices) ? item.alert_indices.join(", ") : ""
      };
    });
  }

  function buildStockPresentationRows(data) {
    var rows = [];
    var labels = data.stock_pres_months || data.coverage_labels || [];
    Object.keys(data.stock_pres || {}).forEach(function (presentation) {
      var item = data.stock_pres[presentation] || {};
      var maxLen = Math.max(
        (item.ventas || []).length,
        (item.dias || []).length,
        (item.statuses || []).length
      );
      for (var index = 0; index < maxLen; index += 1) {
        rows.push({
          Presentacion: presentation,
          Familia: item.familia || "",
          Periodo: labels[index] || ("P" + (index + 1)),
          Orden: index + 1,
          Ventas_unidades: common.valueOrNull(item.ventas && item.ventas[index]),
          Dias_cobertura: common.valueOrNull(item.dias && item.dias[index]),
          Estado: item.statuses && item.statuses[index] ? item.statuses[index] : ""
        });
      }
    });
    return rows;
  }

  function buildPriceRows(data) {
    var rows = [];
    Object.keys(data.precios || {}).forEach(function (brand) {
      var iqviaMap = data.prec_iqvia && data.prec_iqvia[brand] ? data.prec_iqvia[brand] : {};
      Object.keys(data.precios[brand] || {}).forEach(function (presentation) {
        (data.precios[brand][presentation] || []).forEach(function (item) {
          rows.push({
            Marca: brand,
            Presentacion_tablero: presentation,
            Presentacion_iqvia: item.pres || "",
            Laboratorio: item.lab || "",
            Producto: item.prod || "",
            Es_Siegfried: item.is_sie ? "Si" : "No",
            PVP_prev: common.valueOrNull(item.pvp_dic25),
            PVP_actual: common.valueOrNull(item.pvp_feb26),
            Variacion_pct: common.valueOrNull(item.var),
            IQVIA_MAT_unidades: common.valueOrNull(iqviaMap[item.prod])
          });
        });
      });
    });
    return rows;
  }

  function workbookFileName(cfg, data) {
    var prefix = common.sanitizeFilePart((cfg && cfg.filePrefix) || lineTitle(cfg));
    return prefix + "_Datos_" + common.inferStamp(footerLabel(data, cfg)) + ".xlsx";
  }

  function buildWorkbookFromConfig(cfg) {
    var data = exportData(cfg);
    if (!data) {
      throw new Error("No se encontro la data del dashboard");
    }

    var workbook = root.XLSX.utils.book_new();
    var seen = new Set();
    var context = dashboardContext(cfg, data);

    var sheets = [
      ["Resumen", "Resumen", buildOverviewRows(data, cfg)],
      ["Meta", "Metadatos", buildMetaRows(data, cfg)],
      ["KPI_Global", "KPI Global", buildGlobalKpiRows(data)],
      ["KPI_Marca", "KPI por Marca", buildBrandKpiRows(data)],
      ["Presupuesto_Mes", "Presupuesto Mensual", buildBudgetRows(data)],
      ["IQVIA_Mes", "IQVIA Mensual", buildIqviaMonthlyRows(data)],
      ["IQVIA_Acum", "IQVIA Acumulados", buildIqviaAccumRows(data)],
      ["IQVIA_Trim", "IQVIA Trimestral", buildIqviaQuarterRows(data)],
      ["Recetas_Mes", "Recetas Mensuales", buildRecetasRows(data)],
      ["Recetas_Trim", "Recetas Trimestrales", buildRecetasQuarterRows(data)],
      ["Rec_Comp_Mes", "Competidores Recetas", buildRecCompetitorMonthlyRows(data)],
      ["Rec_Comp_Trim", "Competidores Recetas Trim", buildRecCompetitorQuarterRows(data)],
      ["Canales", "Canales", buildCanalesRows(data)],
      ["Convenios_OS", "Convenios OS", buildConveniosRows(data)],
      ["Stock_Mes", "Stock Mensual", buildStockRows(data)],
      ["Stock_Alertas", "Alertas de Stock", buildStockAlertRows(data)],
      ["Stock_Present", "Cobertura por Presentacion", buildStockPresentationRows(data)],
      ["Precios_Comp", "Precios Comparados", buildPriceRows(data)]
    ];

    sheets.forEach(function (item) {
      common.appendTableSheet(
        workbook,
        seen,
        item[0],
        "Siegfried | " + context.title + " | " + item[1],
        common.makeSubtitle(context, item[2].length),
        item[2]
      );
    });

    return workbook;
  }

  function exportWorkbook() {
    var cfg = exportConfig();
    var data = exportData(cfg);
    if (!root.XLSX || !root.XLSX.utils) {
      root.alert("No se pudo cargar la libreria de Excel. Recarga la pagina e intenta otra vez.");
      return;
    }
    if (!data) {
      root.alert("No se encontro la data del dashboard para exportar.");
      return;
    }

    common.setButtonState("[data-export-dashboard]", true);
    root.setTimeout(function () {
      try {
        var workbook = buildWorkbookFromConfig(cfg);
        root.XLSX.writeFile(workbook, workbookFileName(cfg, data));
      } catch (error) {
        console.error(error);
        root.alert("No se pudo generar el Excel del dashboard.");
      } finally {
        common.setButtonState("[data-export-dashboard]", false);
      }
    }, 0);
  }

  function mountButton() {
    var cfg = exportConfig();
    if (!cfg || document.querySelector("[data-export-dashboard]")) {
      return;
    }
    var hubLink = document.querySelector(".nav a.nav-ext[href='../'], .nav-ext[href='../'], .nav-ext[href='./']");
    if (!hubLink || !hubLink.parentNode) {
      return;
    }
    hubLink.parentNode.insertBefore(
      common.createActionButton("data-export-dashboard", "Exportar Excel", "nav-ext", exportWorkbook),
      hubLink
    );
  }

  root.SfDashboardExport = {
    buildWorkbook: buildWorkbookFromConfig,
    exportWorkbook: exportWorkbook,
    mountButton: mountButton
  };

  common.mountWhenReady(mountButton);
})();
