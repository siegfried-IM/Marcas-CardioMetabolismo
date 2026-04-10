(function(){
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
})();
