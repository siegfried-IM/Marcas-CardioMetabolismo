(function(){
  const D = window.OTC_DASHBOARD || window.OTC_DATA;
  if(!D) return;
  window.OTC_DASHBOARD = D;

  D.defaults = {
    brand: 'DAURAN',
    market: 'Dapagliflozina',
    rec: 'DAURAN'
  };

  const real2026 = {
    'DAURAN': [1574,1753,2119,null,null,null,null,null,null,null,null,null],
    'DILATREND': [62302,50032,54233,null,null,null,null,null,null,null,null,null],
    'DILATREND AP': [5061,3713,4437,null,null,null,null,null,null,null,null,null],
    'DILATREND D': [1192,1012,1006,null,null,null,null,null,null,null,null,null],
    'DIOVAN': [46185,36348,45676,null,null,null,null,null,null,null,null,null],
    'DIOVAN D': [26877,22477,32731,null,null,null,null,null,null,null,null,null],
    'EMPAX': [2239,2233,2000,null,null,null,null,null,null,null,null,null],
    'EMPAX MET': [360,230,330,null,null,null,null,null,null,null,null,null],
    'ENTRESTO': [15136,21017,21323,null,null,null,null,null,null,null,null,null],
    'EXFORGE': [20053,13610,18249,null,null,null,null,null,null,null,null,null],
    'EXFORGE D': [9037,1976,12251,null,null,null,null,null,null,null,null,null],
    'METGLUCON AP': [29537,29352,31341,null,null,null,null,null,null,null,null,null],
    'METGLUCON DUO': [275,202,201,null,null,null,null,null,null,null,null,null],
    'PIXABAN': [2163,3329,2678,null,null,null,null,null,null,null,null,null],
    'ROXOLAN': [21570,18856,20197,null,null,null,null,null,null,null,null,null],
    'SILTRAN': [2610,2594,2956,null,null,null,null,null,null,null,null,null],
    'SILTRAN MET': [3174,2797,3548,null,null,null,null,null,null,null,null,null],
    'SINTROM': [64655,61017,65570,null,null,null,null,null,null,null,null,null],
    'TELPRES': [4465,3935,3756,null,null,null,null,null,null,null,null,null],
    'TERLOC': [39599,30796,29528,null,null,null,null,null,null,null,null,null]
  };

  Object.entries(real2026).forEach(([family, values]) => {
    D.budget = D.budget || {};
    D.budget[family] = D.budget[family] || {};
    D.budget[family]['2026'] = D.budget[family]['2026'] || { budget:Array(12).fill(null), real:Array(12).fill(null) };
    D.budget[family]['2026'].real = values.slice(0, 12);
  });
})();
