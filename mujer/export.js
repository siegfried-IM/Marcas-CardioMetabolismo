(function () {
  "use strict";

  var common = window.SfExportCommon || null;

  function dashboardData() {
    return window.MUJER_DASHBOARD || null;
  }

  function regionalData() {
    return window.MUJER_DATA || null;
  }

  function safeRows(rows) {
    return Array.isArray(rows) && rows.length ? rows : [{ info: "Sin datos disponibles" }];
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

  function rowsToSheet(rows) {
    var normalized = safeRows(rows);
    var sheet = XLSX.utils.json_to_sheet(normalized);
    var keys = Object.keys(normalized[0] || {});
    sheet["!cols"] = keys.map(function (key) {
      var maxLen = key.length;
      for (var i = 0; i < normalized.length; i += 1) {
        var value = normalized[i][key];
        var text = value == null ? "" : String(value);
        if (text.length > maxLen) {
          maxLen = text.length;
        }
      }
      return { wch: Math.min(Math.max(maxLen + 2, 12), 40) };
    });
    if (sheet["!ref"]) {
      sheet["!autofilter"] = { ref: sheet["!ref"] };
    }
    return sheet;
  }

  function appendSheet(workbook, seen, name, rows) {
    XLSX.utils.book_append_sheet(workbook, rowsToSheet(rows), uniqueSheetName(name, seen));
  }

  function valueOrNull(value) {
    return value == null ? null : value;
  }

  function buildMetaRows(dash, ddd) {
    var dashMeta = (dash && dash.meta) || {};
    var dataMeta = (ddd && ddd.meta) || {};
    return [
      { area: "dashboard", campo: "latest_month", valor: dashMeta.latest_month || "" },
      { area: "dashboard", campo: "budget_label", valor: dashMeta.budget_label || "" },
      { area: "dashboard", campo: "rec_label", valor: dashMeta.rec_label || "" },
      { area: "dashboard", campo: "kpi_ytd_label", valor: dashMeta.kpi_ytd_label || "" },
      { area: "dashboard", campo: "kpi_mat_label", valor: dashMeta.kpi_mat_label || "" },
      { area: "dashboard", campo: "canales_label", valor: dashMeta.canales_label || "" },
      { area: "dashboard", campo: "price_prev_label", valor: dashMeta.price_prev_label || "" },
      { area: "dashboard", campo: "price_curr_label", valor: dashMeta.price_curr_label || "" },
      { area: "dashboard", campo: "footer_date", valor: dashMeta.footer_date || "" },
      { area: "ddd", campo: "generatedAt", valor: dataMeta.generatedAt || "" },
      { area: "ddd", campo: "sourceDir", valor: dataMeta.sourceDir || "" },
      { area: "ddd", campo: "budgetCut", valor: dataMeta.budgetCut || "" },
      { area: "ddd", campo: "stockCut", valor: dataMeta.stockCut || "" },
      { area: "ddd", campo: "rxCut", valor: dataMeta.rxCut || "" },
      { area: "ddd", campo: "dddCut", valor: dataMeta.dddCut || "" }
    ];
  }

  function buildSummaryRows(ddd) {
    if (!ddd || !ddd.summary) {
      return [];
    }
    return Object.keys(ddd.summary).map(function (family) {
      var row = ddd.summary[family];
      return {
        familia: family,
        ytd_actual_2026: valueOrNull(row.ytdActual2026),
        ytd_budget_2026: valueOrNull(row.ytdBudget2026),
        cumplimiento_2026_pct: valueOrNull(row.compliance2026),
        ultimo_mes: row.latestMonth || "",
        ultimo_real: valueOrNull(row.latestActual),
        ultimo_budget: valueOrNull(row.latestBudget),
        stock_dias: valueOrNull(row.latestStockDays),
        convenio_pct: valueOrNull(row.convenioPct),
        recetas_ultimo_corte: valueOrNull(row.latestRx),
        market_share_ultimo_corte_pct: valueOrNull(row.latestShare),
        tiene_ddd: row.hasDdd ? "Si" : "No"
      };
    });
  }

  function buildGlobalKpiRows(dash) {
    if (!dash || !dash.kpiStrip) {
      return [];
    }
    return [dash.kpiStrip];
  }

  function buildBrandKpiRows(dash) {
    if (!dash || !dash.brandKpis) {
      return [];
    }
    var rows = [];
    Object.keys(dash.brandKpis).forEach(function (brand) {
      var kpi = dash.brandKpis[brand] || {};
      ["ytd", "mat"].forEach(function (period) {
        var row = kpi[period];
        if (!row) {
          return;
        }
        rows.push({
          marca: brand,
          bloque: period.toUpperCase(),
          ie: valueOrNull(row.ie),
          ms_pct: valueOrNull(row.ms),
          unidades: valueOrNull(row.units),
          unidades_previas: valueOrNull(row.units_prev),
          mercado_total: valueOrNull(row.market_total),
          growth_pct: valueOrNull(row.growth)
        });
      });
      if (kpi.budget) {
        rows.push({
          marca: brand,
          bloque: "BUDGET",
          ie: null,
          ms_pct: null,
          unidades: valueOrNull(kpi.budget.real),
          unidades_previas: null,
          mercado_total: valueOrNull(kpi.budget.target),
          growth_pct: valueOrNull(kpi.budget.pct)
        });
      }
      if (kpi.rec) {
        rows.push({
          marca: brand,
          bloque: "RECETAS",
          ie: null,
          ms_pct: valueOrNull(kpi.rec.ms),
          unidades: null,
          unidades_previas: null,
          mercado_total: null,
          growth_pct: null,
          label: kpi.rec.label || ""
        });
      }
    });
    return rows;
  }

  function buildBudgetRows(dash) {
    if (!dash || !dash.budget || !dash.meses) {
      return [];
    }
    var rows = [];
    Object.keys(dash.budget).forEach(function (brand) {
      var yearly = dash.budget[brand] || {};
      Object.keys(yearly).forEach(function (year) {
        var payload = yearly[year] || {};
        dash.meses.forEach(function (monthLabel, idx) {
          rows.push({
            marca: brand,
            anio: year,
            mes: monthLabel,
            periodo: monthLabel + "-" + year,
            budget: valueOrNull(payload.budget && payload.budget[idx]),
            real: valueOrNull(payload.real && payload.real[idx])
          });
        });
      });
    });
    return rows;
  }

  function buildBudgetTopRows(ddd) {
    if (!ddd || !ddd.budget || !ddd.budget.topProducts) {
      return [];
    }
    var rows = [];
    Object.keys(ddd.budget.topProducts).forEach(function (family) {
      (ddd.budget.topProducts[family] || []).forEach(function (item, idx) {
        rows.push({
          familia: family,
          rank: idx + 1,
          producto: item.name || "",
          total_actual: valueOrNull(item.totalActual),
          ytd_2026: valueOrNull(item.ytd2026),
          ultimo_real: valueOrNull(item.latestActual)
        });
      });
    });
    return rows;
  }

  function buildIqviaMonthlyRows(dash) {
    if (!dash || !dash.mol_perf) {
      return [];
    }
    var rows = [];
    Object.keys(dash.mol_perf).forEach(function (family) {
      var perf = dash.mol_perf[family] || {};
      (perf.products || []).forEach(function (product) {
        var unitsByMonth = product.monthly_vals || {};
        var msByMonth = product.ms_monthly || {};
        Object.keys(unitsByMonth).forEach(function (period) {
          rows.push({
            familia: family,
            producto: product.prod || "",
            laboratorio: product.manuf || "",
            es_siegfried: product.is_sie ? "Si" : "No",
            periodo: period,
            unidades: valueOrNull(unitsByMonth[period]),
            market_share_pct: valueOrNull(msByMonth[period])
          });
        });
      });
    });
    return rows;
  }

  function buildIqviaAccumRows(dash) {
    if (!dash || !dash.mol_perf) {
      return [];
    }
    var rows = [];
    Object.keys(dash.mol_perf).forEach(function (family) {
      var perf = dash.mol_perf[family] || {};
      (perf.products || []).forEach(function (product) {
        ["ytd", "mat"].forEach(function (bucket) {
          var units = product[bucket] || {};
          var share = product["ms_" + bucket] || {};
          Object.keys(units).forEach(function (period) {
            rows.push({
              familia: family,
              producto: product.prod || "",
              laboratorio: product.manuf || "",
              es_siegfried: product.is_sie ? "Si" : "No",
              vista: bucket.toUpperCase(),
              periodo: period,
              unidades: valueOrNull(units[period]),
              market_share_pct: valueOrNull(share[period])
            });
          });
        });
      });
    });
    return rows;
  }

  function buildIqviaQuarterRows(dash) {
    if (!dash || !dash.mol_perf) {
      return [];
    }
    var rows = [];
    Object.keys(dash.mol_perf).forEach(function (family) {
      var perf = dash.mol_perf[family] || {};
      (perf.products || []).forEach(function (product) {
        var unitsByQuarter = product.quarterly_vals || {};
        var msByQuarter = product.ms_quarterly || {};
        Object.keys(unitsByQuarter).forEach(function (period) {
          rows.push({
            familia: family,
            producto: product.prod || "",
            laboratorio: product.manuf || "",
            es_siegfried: product.is_sie ? "Si" : "No",
            trimestre: period,
            unidades: valueOrNull(unitsByQuarter[period]),
            market_share_pct: valueOrNull(msByQuarter[period])
          });
        });
      });
    });
    return rows;
  }

  function buildRecetasRows(dash) {
    if (!dash || !dash.recetas) {
      return [];
    }
    var rows = [];
    Object.keys(dash.recetas).forEach(function (brand) {
      var monthly = dash.recetas[brand] || {};
      var recMs = (dash.rec_ms && dash.rec_ms[brand]) || {};
      var sieByMonth = recMs.sie || {};
      var msByMonth = recMs.ms || {};
      Object.keys(monthly).forEach(function (period) {
        var item = monthly[period] || {};
        rows.push({
          marca: brand,
          periodo: period,
          recetas_mercado: valueOrNull(item.recetas),
          medicos: valueOrNull(item.medicos),
          recetas_siegfried: valueOrNull(sieByMonth[period]),
          market_share_pct: valueOrNull(msByMonth[period])
        });
      });
    });
    return rows;
  }

  function buildRecetasQuarterRows(dash) {
    if (!dash || !dash.rec_ms) {
      return [];
    }
    var rows = [];
    Object.keys(dash.rec_ms).forEach(function (brand) {
      var item = dash.rec_ms[brand] || {};
      var quarterly = item.quarterly || {};
      var share = item.ms_quarterly || {};
      Object.keys(quarterly).forEach(function (period) {
        rows.push({
          marca: brand,
          trimestre: period,
          recetas_siegfried: valueOrNull(quarterly[period]),
          market_share_pct: valueOrNull(share[period])
        });
      });
    });
    return rows;
  }

  function buildRecetasCompetidorRows(dash) {
    if (!dash || !dash.rec_comp) {
      return [];
    }
    var rows = [];
    Object.keys(dash.rec_comp).forEach(function (brand) {
      var competitors = dash.rec_comp[brand] || {};
      Object.keys(competitors).forEach(function (competitor) {
        var item = competitors[competitor] || {};
        var monthly = item.monthly || {};
        Object.keys(monthly).forEach(function (period) {
          rows.push({
            marca: brand,
            competidor: competitor,
            periodo: period,
            recetas: valueOrNull(monthly[period])
          });
        });
      });
    });
    return rows;
  }

  function buildCanalesRows(dash) {
    if (!dash || !dash.canales) {
      return [];
    }
    return Object.keys(dash.canales).map(function (brand) {
      var item = dash.canales[brand] || {};
      return {
        marca: brand,
        unidades_facturadas: valueOrNull(item.unid),
        convenio_pct: valueOrNull(item.conv),
        mostrador_pct: valueOrNull(item.most),
        convenio_unidades: valueOrNull(item.conv_units),
        mostrador_unidades: valueOrNull(item.most_units),
        descuento_total_pct: valueOrNull(item.dto_total),
        descuento_convenio_pct: valueOrNull(item.dto_conv),
        descuento_mostrador_pct: valueOrNull(item.dto_most),
        unidades_previas: valueOrNull(item.unid_prev),
        convenio_pct_prev: valueOrNull(item.conv_prev),
        mostrador_pct_prev: valueOrNull(item.most_prev),
        convenio_pp: valueOrNull(item.conv_pp),
        mostrador_pp: valueOrNull(item.most_pp)
      };
    });
  }

  function buildConveniosRows(dash) {
    if (!dash || !dash.convenios) {
      return [];
    }
    var rows = [];
    Object.keys(dash.convenios).forEach(function (brand) {
      (dash.convenios[brand] || []).forEach(function (item, idx) {
        rows.push({
          marca: brand,
          rank: idx + 1,
          obra_social: item.os || "",
          unidades_2024: valueOrNull(item.unid24),
          unidades_2025: valueOrNull(item.unid),
          delta_pct: valueOrNull(item.delta)
        });
      });
    });
    return rows;
  }

  function buildStockRows(dash) {
    if (!dash || !dash.stock) {
      return [];
    }
    var rows = [];
    Object.keys(dash.stock).forEach(function (brand) {
      var periods = dash.stock[brand] || {};
      Object.keys(periods).forEach(function (period) {
        var item = periods[period] || {};
        rows.push({
          marca: brand,
          periodo: period,
          stock_unidades: valueOrNull(item.stock),
          ventas_unidades: valueOrNull(item.ventas),
          facturacion_unidades: valueOrNull(item.facturacion),
          dias_cobertura: valueOrNull(item.dias)
        });
      });
    });
    return rows;
  }

  function buildStockAlertRows(dash) {
    if (!dash || !dash.stock_alerts) {
      return [];
    }
    return Object.keys(dash.stock_alerts).map(function (brand) {
      var item = dash.stock_alerts[brand] || {};
      return {
        marca: brand,
        familia: item.familia || brand,
        peor_estado: item.worst_status || "",
        cantidad_alertas: valueOrNull(item.n_alerts),
        indices_alerta: Array.isArray(item.alert_indices) ? item.alert_indices.join(", ") : ""
      };
    });
  }

  function buildStockPresentRows(dash) {
    if (!dash || !dash.stock_pres) {
      return [];
    }
    var rows = [];
    Object.keys(dash.stock_pres).forEach(function (presentation) {
      var item = dash.stock_pres[presentation] || {};
      var ventas = item.ventas || [];
      var dias = item.dias || [];
      var statuses = item.statuses || [];
      var maxLen = Math.max(ventas.length, dias.length, statuses.length);
      for (var idx = 0; idx < maxLen; idx += 1) {
        rows.push({
          presentacion: presentation,
          familia: item.familia || "",
          posicion: idx + 1,
          ventas_unidades: valueOrNull(ventas[idx]),
          dias_cobertura: valueOrNull(dias[idx]),
          estado: statuses[idx] || ""
        });
      }
    });
    return rows;
  }

  function buildPriceRows(dash) {
    if (!dash || !dash.precios) {
      return [];
    }
    var rows = [];
    Object.keys(dash.precios).forEach(function (brand) {
      var presentations = dash.precios[brand] || {};
      var iqviaMap = (dash.prec_iqvia && dash.prec_iqvia[brand]) || {};
      Object.keys(presentations).forEach(function (dose) {
        (presentations[dose] || []).forEach(function (item) {
          rows.push({
            marca: brand,
            presentacion: dose,
            laboratorio: item.lab || "",
            producto: item.prod || "",
            es_siegfried: item.is_sie ? "Si" : "No",
            pvp_prev: valueOrNull(item.pvp_dic25),
            pvp_actual: valueOrNull(item.pvp_feb26),
            variacion: valueOrNull(item.var),
            iqvia_mat_unidades: valueOrNull(iqviaMap[item.prod])
          });
        });
      });
    });
    return rows;
  }

  function buildDddMonthlyRows(ddd) {
    if (!ddd || !ddd.ddd || !ddd.ddd.markets) {
      return [];
    }
    var rows = [];
    Object.keys(ddd.ddd.markets).forEach(function (market) {
      var payload = ddd.ddd.markets[market] || {};
      (payload.monthly || []).forEach(function (item) {
        rows.push({
          mercado: market,
          familia: payload.family || "",
          ultimo_mes: payload.latestMonth || "",
          periodo: item.month || "",
          unidades_mercado: valueOrNull(item.total),
          unidades_siegfried: valueOrNull(item.sie),
          market_share_pct: valueOrNull(item.share)
        });
      });
    });
    return rows;
  }

  function buildDddRegionRows(ddd) {
    if (!ddd || !ddd.ddd || !ddd.ddd.markets) {
      return [];
    }
    var rows = [];
    Object.keys(ddd.ddd.markets).forEach(function (market) {
      var payload = ddd.ddd.markets[market] || {};
      var byMonth = payload.regionsByMonth || {};
      Object.keys(byMonth).forEach(function (period) {
        (byMonth[period] || []).forEach(function (item, idx) {
          rows.push({
            mercado: market,
            familia: payload.family || "",
            periodo: period,
            rank: idx + 1,
            region: item.name || "",
            unidades_mercado: valueOrNull(item.total),
            unidades_siegfried: valueOrNull(item.sie),
            market_share_pct: valueOrNull(item.share)
          });
        });
      });
    });
    return rows;
  }

  function buildDddProductRows(ddd) {
    if (!ddd || !ddd.ddd || !ddd.ddd.markets) {
      return [];
    }
    var rows = [];
    Object.keys(ddd.ddd.markets).forEach(function (market) {
      var payload = ddd.ddd.markets[market] || {};
      var byMonth = payload.productsByMonth || {};
      Object.keys(byMonth).forEach(function (period) {
        (byMonth[period] || []).forEach(function (item, idx) {
          rows.push({
            mercado: market,
            familia: payload.family || "",
            periodo: period,
            rank: idx + 1,
            producto: item.product || "",
            es_siegfried: item.isSie ? "Si" : "No",
            unidades: valueOrNull(item.units),
            market_share_pct: valueOrNull(item.share)
          });
        });
      });
    });
    return rows;
  }

  function workbookFileName(dash) {
    var footer = dash && dash.meta && dash.meta.footer_date ? dash.meta.footer_date : "";
    var stamp = footer ? footer.replace(/\//g, "-") : new Date().toISOString().slice(0, 10);
    return "OTC_Datos_" + stamp + ".xlsx";
  }

  function setExportState(isBusy) {
    var buttons = document.querySelectorAll("[data-export-otc]");
    buttons.forEach(function (button) {
      if (!button.dataset.defaultLabel) {
        button.dataset.defaultLabel = button.textContent.trim();
      }
      button.disabled = isBusy;
      button.style.opacity = isBusy ? "0.7" : "1";
      button.style.pointerEvents = isBusy ? "none" : "auto";
      button.textContent = isBusy ? "Exportando..." : button.dataset.defaultLabel;
    });
  }

  function createLinkButton(text, className, extraStyles) {
    var link = document.createElement("a");
    link.href = "javascript:void(0)";
    link.className = className;
    link.setAttribute("data-export-otc", "true");
    link.textContent = text;
    link.onclick = function () {
      window.exportOtcWorkbook();
    };
    if (extraStyles) {
      Object.keys(extraStyles).forEach(function (key) {
        link.style[key] = extraStyles[key];
      });
    }
    return link;
  }

  function mountExportButtons() {
    if (document.querySelector("[data-export-otc]")) {
      return;
    }

    var executiveHub = document.querySelector('.nav a.nav-ext[href="../"]');
    if (executiveHub && executiveHub.parentNode) {
      executiveHub.parentNode.insertBefore(
        createLinkButton("Exportar Excel", "nav-ext"),
        executiveHub
      );
    }

    var dddNavRight = document.querySelector(".nav-right");
    if (dddNavRight && !dddNavRight.querySelector("[data-export-otc]")) {
      dddNavRight.insertBefore(
        createLinkButton("Exportar Excel", "nav-hub", {
          padding: "6px 10px",
          border: "1px solid var(--bd)",
          borderRadius: "6px",
          cursor: "pointer"
        }),
        dddNavRight.firstChild
      );
    }
  }

  function buildWorkbook() {
    var dash = dashboardData();
    var ddd = regionalData();
    var workbook = XLSX.utils.book_new();
    var seen = new Set();
    var entries = [];
    var footer = (dash && dash.meta && dash.meta.footer_date) || (ddd && ddd.meta && ddd.meta.dddCut) || "";
    var context = {
      title: "OTC",
      footer: footer
    };

    if (common && common.ensureWorkbookChrome) {
      common.ensureWorkbookChrome(workbook, seen);
    }

    if (common && common.appendTableSheet) {
      [
        ["Meta", "Metadatos", buildMetaRows(dash, ddd), "Resumen Ejecutivo"],
        ["Resumen", "Resumen", buildSummaryRows(ddd), "Resumen Ejecutivo"],
        ["KPI_Global", "KPI Global", buildGlobalKpiRows(dash), "Indicadores"],
        ["KPI_Marca", "KPI por Marca", buildBrandKpiRows(dash), "Indicadores"],
        ["Presupuesto_Mes", "Presupuesto Mensual", buildBudgetRows(dash), "Presupuesto"],
        ["Presupuesto_Top", "Presupuesto Top Productos", buildBudgetTopRows(ddd), "Presupuesto"],
        ["IQVIA_Mes", "IQVIA Mensual", buildIqviaMonthlyRows(dash), "IQVIA"],
        ["IQVIA_Acum", "IQVIA Acumulados", buildIqviaAccumRows(dash), "IQVIA"],
        ["IQVIA_Trim", "IQVIA Trimestral", buildIqviaQuarterRows(dash), "IQVIA"],
        ["Recetas_Mes", "Recetas Mensuales", buildRecetasRows(dash), "Recetas"],
        ["Recetas_Trim", "Recetas Trimestrales", buildRecetasQuarterRows(dash), "Recetas"],
        ["Rec_Comp_Mes", "Competidores Recetas", buildRecetasCompetidorRows(dash), "Recetas"],
        ["Canales", "Canales", buildCanalesRows(dash), "Canales y Convenios"],
        ["Convenios_OS", "Convenios OS", buildConveniosRows(dash), "Canales y Convenios"],
        ["Stock_Mes", "Stock Mensual", buildStockRows(dash), "Stock"],
        ["Stock_Alertas", "Alertas de Stock", buildStockAlertRows(dash), "Stock"],
        ["Stock_Present", "Cobertura por Presentacion", buildStockPresentRows(dash), "Stock"],
        ["Precios_Comp", "Precios Comparados", buildPriceRows(dash), "Precios"],
        ["DDD_Mensual", "DDD Mensual", buildDddMonthlyRows(ddd), "DDD"],
        ["DDD_Regiones", "DDD Regiones", buildDddRegionRows(ddd), "DDD"],
        ["DDD_Productos", "DDD Productos", buildDddProductRows(ddd), "DDD"]
      ].forEach(function (item) {
        entries.push(common.appendTableSheet(
          workbook,
          seen,
          item[0],
          "Siegfried | OTC | " + item[1],
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
        kind: "Dashboard + DDD OTC"
      });
      return workbook;
    }

    appendSheet(workbook, seen, "Meta", buildMetaRows(dash, ddd));
    appendSheet(workbook, seen, "Resumen", buildSummaryRows(ddd));
    appendSheet(workbook, seen, "KPI_Global", buildGlobalKpiRows(dash));
    appendSheet(workbook, seen, "KPI_Marca", buildBrandKpiRows(dash));
    appendSheet(workbook, seen, "Presupuesto_Mes", buildBudgetRows(dash));
    appendSheet(workbook, seen, "Presupuesto_Top", buildBudgetTopRows(ddd));
    appendSheet(workbook, seen, "IQVIA_Mes", buildIqviaMonthlyRows(dash));
    appendSheet(workbook, seen, "IQVIA_Acum", buildIqviaAccumRows(dash));
    appendSheet(workbook, seen, "IQVIA_Trim", buildIqviaQuarterRows(dash));
    appendSheet(workbook, seen, "Recetas_Mes", buildRecetasRows(dash));
    appendSheet(workbook, seen, "Recetas_Trim", buildRecetasQuarterRows(dash));
    appendSheet(workbook, seen, "Rec_Comp_Mes", buildRecetasCompetidorRows(dash));
    appendSheet(workbook, seen, "Canales", buildCanalesRows(dash));
    appendSheet(workbook, seen, "Convenios_OS", buildConveniosRows(dash));
    appendSheet(workbook, seen, "Stock_Mes", buildStockRows(dash));
    appendSheet(workbook, seen, "Stock_Alertas", buildStockAlertRows(dash));
    appendSheet(workbook, seen, "Stock_Present", buildStockPresentRows(dash));
    appendSheet(workbook, seen, "Precios_Comp", buildPriceRows(dash));
    appendSheet(workbook, seen, "DDD_Mensual", buildDddMonthlyRows(ddd));
    appendSheet(workbook, seen, "DDD_Regiones", buildDddRegionRows(ddd));
    appendSheet(workbook, seen, "DDD_Productos", buildDddProductRows(ddd));

    return workbook;
  }

  window.exportOtcWorkbook = function () {
    if (!common || !common.ensureStyledXlsx) {
      window.alert("No se pudo preparar la exportacion de Excel.");
      return;
    }
    if (!dashboardData() || !regionalData()) {
      window.alert("No se encontro la data de OTC para exportar.");
      return;
    }

    setExportState(true);
    common.ensureStyledXlsx()
      .then(function () {
        window.setTimeout(function () {
          try {
            var workbook = buildWorkbook();
            XLSX.writeFile(workbook, workbookFileName(dashboardData()));
          } catch (error) {
            console.error(error);
            window.alert("No se pudo generar el Excel de OTC.");
          } finally {
            setExportState(false);
          }
        }, 0);
      })
      .catch(function (error) {
        console.error(error);
        window.alert("No se pudo cargar la libreria de Excel.");
        setExportState(false);
      });
  };

  document.addEventListener("DOMContentLoaded", mountExportButtons);
})();
