(function(){
  const D = window.OTC_DASHBOARD || window.OTC_DATA;
  if(!D) return;
  window.OTC_DASHBOARD = D;

  function normalizeBudgetShape(data){
    const src = data?.budget;
    if(!src || !Array.isArray(src.months) || !src.families || Array.isArray(src)) return;
    const months = src.months;
    const families = src.families;
    const brands = (Array.isArray(data.families) ? data.families : Object.keys(families)).filter(name => name && name !== 'Totales');
    const converted = {};

    brands.forEach((brand) => {
      const family = families[brand];
      if(!family) return;
      const actual = Array.isArray(family.actual) ? family.actual : [];
      const budget = Array.isArray(family.budget) ? family.budget : [];
      converted[brand] = {
        '2025': { budget: [], real: [] },
        '2026': { budget: [], real: [] }
      };
      months.forEach((label, idx) => {
        const year = String(label || '').split('-')[1];
        if(year !== '2025' && year !== '2026') return;
        converted[brand][year].budget.push(budget[idx] ?? null);
        converted[brand][year].real.push(actual[idx] ?? null);
      });
      ['2025','2026'].forEach((year) => {
        while(converted[brand][year].budget.length < 12) converted[brand][year].budget.push(null);
        while(converted[brand][year].real.length < 12) converted[brand][year].real.push(null);
      });
    });

    data.budget = converted;
  }

  function normalizeChannelShape(data){
    if(data?.canales) return;
    const families = data?.channel?.families;
    if(!families) return;
    const converted = {};
    Object.entries(families).forEach(([brand, entry]) => {
      const prev = entry?.prev || null;
      const current = entry?.current || null;
      const currConv = current?.convenioPct ?? entry?.convenioPct ?? 0;
      const prevConv = prev?.convenioPct ?? entry?.convenioPctPrev ?? null;
      const currMost = current?.mostradorPct ?? entry?.mostradorPct ?? 0;
      const prevMost = prev?.mostradorPct ?? entry?.mostradorPctPrev ?? null;
      converted[brand] = {
        unid: current?.facturedUnits ?? entry?.facturedUnits ?? 0,
        conv: currConv,
        most: currMost,
        conv_units: current?.convenioUnits ?? entry?.convenioUnits ?? 0,
        most_units: current?.mostradorUnits ?? entry?.mostradorUnits ?? 0,
        dto_total: current?.discountTotalPct ?? entry?.discountTotalPct ?? 0,
        dto_conv: current?.discountConvenioPct ?? entry?.discountConvenioPct ?? 0,
        dto_most: current?.discountCommonPct ?? entry?.discountCommonPct ?? 0,
        unid_prev: prev?.facturedUnits ?? entry?.facturedUnitsPrev ?? null,
        conv_prev: prevConv,
        most_prev: prevMost,
        conv_units_prev: prev?.convenioUnits ?? entry?.convenioUnitsPrev ?? null,
        most_units_prev: prev?.mostradorUnits ?? entry?.mostradorUnitsPrev ?? null,
        dto_total_prev: prev?.discountTotalPct ?? entry?.discountTotalPctPrev ?? null,
        dto_conv_prev: prev?.discountConvenioPct ?? entry?.discountConvenioPctPrev ?? null,
        dto_most_prev: prev?.discountCommonPct ?? entry?.discountCommonPctPrev ?? null,
        conv_pp: prevConv == null ? null : currConv - prevConv,
        most_pp: prevMost == null ? null : currMost - prevMost
      };
    });
    data.canales = converted;
  }

  function normalizeConveniosShape(data){
    if(data?.convenios) return;
    const families = data?.osComparison?.families;
    if(!families) return;
    const converted = {};
    Object.entries(families).forEach(([brand, entry]) => {
      converted[brand] = Array.isArray(entry?.rows) ? entry.rows.map((row) => ({
        os: row.os,
        unid24: row.units2024 ?? null,
        unid: row.units2025 ?? 0,
        delta: row.deltaPct ?? null
      })) : [];
    });
    data.convenios = converted;
  }

  function normalizeMeta(data){
    data.meta = data.meta || {};
    if(data.meta.canales_prev_year == null) data.meta.canales_prev_year = '2024';
    if(data.meta.canales_current_year == null) data.meta.canales_current_year = '2025';
    if(data.meta.conv_prev_year == null) data.meta.conv_prev_year = '2024';
    if(data.meta.conv_current_year == null) data.meta.conv_current_year = '2025';
  }

  normalizeBudgetShape(D);
  normalizeChannelShape(D);
  normalizeConveniosShape(D);
  normalizeMeta(D);

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
    const current = Array.isArray(D.budget[family]['2026'].real) ? D.budget[family]['2026'].real : [];
    const hasReal = current.some(value => value != null && Number(value) !== 0);
    if(!hasReal){
      D.budget[family]['2026'].real = values.slice(0, 12);
    }
  });
})();
