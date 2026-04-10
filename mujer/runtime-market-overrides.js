(function(){
  function ordered(obj){
    var out = {};
    Object.keys(obj || {}).forEach(function(key){ out[key] = obj[key]; });
    return out;
  }
  function merge(target, source){
    Object.entries(source || {}).forEach(function(entry){
      var key = entry[0];
      var value = entry[1];
      if(value && typeof value === 'object' && !Array.isArray(value) && target[key] && typeof target[key] === 'object' && !Array.isArray(target[key])){
        merge(target[key], value);
      } else {
        target[key] = value;
      }
    });
    return target;
  }

  var D = window.MUJER_DASHBOARD || window.MUJER_DATA;
  var O = window.MUJER_MARKET_OVERRIDE;
  if(!D || !O) return;

  D.mol_perf = O.mol_perf || D.mol_perf;
  D.molLabels = O.molLabels || D.molLabels;
  D.sieMolMap = O.sieMolMap || D.sieMolMap;
  D.kpiStrip = merge(D.kpiStrip || {}, O.kpiStrip || {});

  Object.entries(O.brandKpis || {}).forEach(function(entry){
    var brand = entry[0];
    var value = entry[1];
    D.brandKpis = D.brandKpis || {};
    D.brandKpis[brand] = merge(D.brandKpis[brand] || {}, value);
  });

  var firstFamilyWithMarket = Object.keys(D.mol_perf || {})[0];
  var marketMonthly = firstFamilyWithMarket ? (D.mol_perf[firstFamilyWithMarket].monthly || {}) : {};
  var latestMarketMonth = Object.keys(marketMonthly).filter(function(key){
    return Number(marketMonthly[key] || 0) > 0;
  }).sort(function(a,b){
    return new Date(a.replace(/^([A-Za-z]{3}) /,'$1 1, ')) - new Date(b.replace(/^([A-Za-z]{3}) /,'$1 1, '));
  }).slice(-1)[0] || null;

  if (latestMarketMonth && D.meta) {
    D.meta.current_ytd_key = latestMarketMonth;
    D.meta.current_mat_key = latestMarketMonth;
    var prevYearMonth = latestMarketMonth.replace(/ (\d{4})$/, function(_, y){ return ' ' + (Number(y) - 1); });
    D.meta.prev_ytd_key = prevYearMonth;
    D.meta.prev_mat_key = prevYearMonth;
    var parts = latestMarketMonth.split(' ');
    if (parts.length === 2) {
      D.meta.kpi_ytd_label = 'YTD ' + parts[0] + "'" + parts[1].slice(-2);
      D.meta.kpi_ytd_prev_label = 'YTD ' + parts[0] + "'" + String(Number(parts[1]) - 1).slice(-2);
      D.meta.kpi_mat_label = 'MAT ' + parts[0] + "'" + parts[1].slice(-2);
      D.meta.kpi_mat_prev_label = 'MAT ' + parts[0] + "'" + String(Number(parts[1]) - 1).slice(-2);
    }
  }

  var families = Object.keys(D.mol_perf || {});
  if ((!D.familyToMarkets || !Object.keys(D.familyToMarkets).length) && families.length) {
    D.familyToMarkets = {};
    families.forEach(function(f){ D.familyToMarkets[f] = [f]; });
    D.familyToMarkets.Totales = families.slice();
  }

  if ((!D.ddd || !Object.keys(D.ddd).length) && families.length) {
    var firstFamily = families[0];
    var months = Object.keys((D.mol_perf[firstFamily] && D.mol_perf[firstFamily].monthly) || {}).sort(function(a,b){
      return new Date(a.replace(/^([A-Za-z]{3}) /,'$1 1, ')) - new Date(b.replace(/^([A-Za-z]{3}) /,'$1 1, '));
    });
    var markets = {};
    families.forEach(function(family){
      var mk = D.mol_perf[family];
      var productsByMonth = {};
      var regionsByMonth = {};
      months.forEach(function(month){
        var total = Number((mk.monthly || {})[month] || 0);
        var rows = (mk.products || []).map(function(p){
          var units = Number((p.monthly_vals || {})[month] || 0);
          var share = total > 0 ? +(units / total * 100).toFixed(1) : 0;
          return {
            product: p.prod,
            units: units,
            share: share,
            isSie: !!p.is_sie
          };
        }).filter(function(row){ return row.units > 0; }).sort(function(a,b){ return b.units - a.units; });
        var sie = rows.filter(function(r){ return r.isSie; }).reduce(function(s,r){ return s + r.units; }, 0);
        productsByMonth[month.replace(' ','-').replace('Jan','Ene').replace('Apr','Abr').replace('Aug','Ago').replace('Dec','Dic')] = rows;
        regionsByMonth[month.replace(' ','-').replace('Jan','Ene').replace('Apr','Abr').replace('Aug','Ago').replace('Dec','Dic')] = [{
          name: 'Nacional',
          rr: '__NAC__',
          total: total,
          sie: sie,
          share: total > 0 ? +(sie / total * 100).toFixed(1) : 0
        }];
      });
      var lastKey = Object.keys(productsByMonth).filter(function(k){
        return (productsByMonth[k] || []).length > 0;
      }).slice(-1)[0] || Object.keys(regionsByMonth).slice(-1)[0] || null;
      markets[family] = {
        family: family,
        latestMonth: lastKey,
        productsByMonth: productsByMonth,
        regionsByMonth: regionsByMonth
      };
    });
    D.ddd = { months: Object.keys(markets[firstFamily].regionsByMonth || {}), markets: markets };
    D.marketShare = { months: D.ddd.months, markets: markets };
  }

  window.MUJER_DATA = D;
  window.MUJER_DASHBOARD = D;
})();
