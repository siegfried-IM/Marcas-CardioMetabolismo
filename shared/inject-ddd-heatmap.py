#!/usr/bin/env python3
"""
shared/inject-ddd-heatmap.py

Inyecta una nueva seccion 'Competidores · Heatmap geografico' en todos
los DDD del repo. La seccion muestra crecimiento por competidor x
provincia y region CUP con selectores de periodo (M/Q/S/YTD/MAT) y
metrica (MS% / dMS% pp / dUnits %).

Detecta shape:
  - Shape A (cardio, SNC, dermato): D.markets[m].brand_monthly[brand][region][12]
    -> render heatmap completo competidor x region
  - Shape B (ATB, OTC, respi, mujer): OTC_DATA.ddd|dddGineco con regionsByMonth
    -> render simplificado SIE x region (sin granularidad por competidor)

Idempotente: si ya esta inyectado (busca id="s5-heat"), skip.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (file, shape) — shape determined by what variable they reference
FILES_SHAPE_A = [
    'cardio/DDD/index.html',
    'SNC/DDD/psq_ddd.html',
    'dermatologia/dermato_ddd.html',
]
FILES_SHAPE_B = [
    'ATB/DDD/index.html',
    'OTC/DDD/index.html',
    'respiratorio/DDD/index.html',
    'mujer/DDD/index.html',
]

# ── CSS (shared) ─────────────────────────────────────────────────────
CSS = """
/* Heatmap section */
.heat-section{margin-top:24px;padding:18px 20px;background:#fff;border:1px solid #e5e5e5;border-radius:8px;}
.heat-hd{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;}
.heat-hd .cn{font-family:'IBM Plex Mono',monospace;color:#737373;font-size:12px;font-weight:600;}
.heat-hd .ctt{font-size:16px;font-weight:700;color:#1a1a1a;}
.heat-sub{color:#737373;font-size:12px;margin-bottom:14px;}
.heat-ctrl{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:14px;padding:10px 12px;background:#fafafa;border-radius:6px;}
.heat-ctrl .seg{display:inline-flex;border:1px solid #d4d4d4;border-radius:4px;overflow:hidden;background:#fff;}
.heat-ctrl .seg button{padding:5px 11px;border:0;background:transparent;cursor:pointer;font-size:11px;font-weight:600;color:#525252;border-right:1px solid #e5e5e5;}
.heat-ctrl .seg button:last-child{border-right:0;}
.heat-ctrl .seg button.on{background:#7A1518;color:#fff;}
.heat-ctrl .seg button:hover:not(.on){background:#f5f5f5;}
.heat-ctrl .lbl{font-size:10px;color:#737373;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-right:-6px;}
.heat-ctrl .meta{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#737373;margin-left:auto;}
.heat-filter{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:14px;padding:10px 12px;background:#fafafa;border-radius:6px;}
.heat-filter .lbl{font-size:10px;color:#737373;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-right:6px;}
.heat-filter .seg{display:inline-flex;border:1px solid #d4d4d4;border-radius:4px;overflow:hidden;background:#fff;margin-right:8px;}
.heat-filter .seg button{padding:4px 10px;border:0;background:transparent;cursor:pointer;font-size:10px;font-weight:600;color:#525252;border-right:1px solid #e5e5e5;}
.heat-filter .seg button:last-child{border-right:0;}
.heat-filter .seg button:hover{background:#f5f5f5;}
.heat-comp-pills{display:flex;flex-wrap:wrap;gap:4px;flex:1;min-width:300px;}
.heat-comp-pill{padding:3px 9px;border:1px solid #d4d4d4;border-radius:11px;font-size:10px;font-weight:600;cursor:pointer;background:#fff;color:#525252;white-space:nowrap;transition:all .15s;}
.heat-comp-pill.on{background:#1f2937;color:#fff;border-color:#1f2937;}
.heat-comp-pill.on.sie{background:#7A1518;border-color:#7A1518;}
.heat-comp-pill:not(.on){opacity:.55;}
.heat-comp-pill:not(.on):hover{opacity:1;border-color:#737373;}
.heat-comp-pill .dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:5px;vertical-align:middle;}
.heat-search{padding:4px 10px;border:1px solid #d4d4d4;border-radius:4px;font-size:11px;background:#fff;color:#1a1a1a;width:160px;}
.heat-search:focus{outline:none;border-color:#7A1518;}
.heat-comp-meta{font-family:'IBM Plex Mono',monospace;font-size:9px;color:#737373;margin-left:auto;}
.heat-table-title{font-size:12px;font-weight:700;color:#1a1a1a;text-transform:uppercase;letter-spacing:.08em;margin:14px 0 6px;}
.heat-wrap{overflow-x:auto;border:1px solid #e5e5e5;border-radius:6px;max-height:560px;overflow-y:auto;}
table.heat{border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:10px;width:max-content;}
table.heat th,table.heat td{border:1px solid #f0f0f0;padding:4px 6px;text-align:center;min-width:42px;}
table.heat thead th{position:sticky;top:0;background:#1f2937;color:#fff;font-weight:700;font-size:9px;letter-spacing:.04em;z-index:2;white-space:nowrap;}
table.heat thead th:first-child{position:sticky;left:0;z-index:3;}
table.heat tbody th{position:sticky;left:0;background:#fafafa;color:#1a1a1a;font-weight:600;text-align:left;font-size:10px;white-space:nowrap;z-index:1;border-right:1px solid #d4d4d4;max-width:180px;overflow:hidden;text-overflow:ellipsis;}
table.heat tbody th.sie{color:#7A1518;font-weight:700;}
table.heat tbody th.sie::before{content:'★ ';color:#7A1518;}
table.heat tbody tr:hover th,table.heat tbody tr:hover td{filter:brightness(0.95);}
.heat-empty{padding:14px;color:#737373;font-size:12px;text-align:center;}
.heat-cell{font-size:10px;}
.heat-note{font-size:10px;color:#737373;margin-top:8px;font-style:italic;}
"""

# ── HTML (shared) ────────────────────────────────────────────────────
HTML = """
<section class="heat-section" id="s5-heat">
  <div class="heat-hd">
    <div class="cn">06</div>
    <div class="ctt">Competidores · Heatmap geográfico</div>
  </div>
  <p class="heat-sub">Crecimiento y MS% por <strong>competidor × provincia / región CUP</strong> en distintos períodos. Color verde = crecimiento; rojo = caída; azul = MS% absoluto. Mercado activo se sincroniza con el selector superior.</p>

  <div class="heat-ctrl">
    <span class="lbl">Período</span>
    <div class="seg" id="heat-period">
      <button data-p="m">Mensual</button>
      <button data-p="q" class="on">Trimestral</button>
      <button data-p="s">Semestral</button>
      <button data-p="ytd">YTD</button>
      <button data-p="mat">MAT</button>
    </div>
    <span class="lbl">Métrica</span>
    <div class="seg" id="heat-metric">
      <button data-m="ms" class="on">MS%</button>
      <button data-m="dms">Δ MS% (pp)</button>
      <button data-m="du">Δ Unidades %</button>
    </div>
    <span class="meta" id="heat-period-label"></span>
  </div>

  <div class="heat-filter" id="heat-filter">
    <span class="lbl">Competidores</span>
    <div class="seg" id="heat-preset">
      <button data-preset="all">Todos</button>
      <button data-preset="sie">Solo SIE</button>
      <button data-preset="top5">Top 5</button>
      <button data-preset="top10" class="on">Top 10</button>
    </div>
    <input type="text" class="heat-search" id="heat-search" placeholder="Buscar competidor..." />
    <div class="heat-comp-pills" id="heat-comp-pills"></div>
    <span class="heat-comp-meta" id="heat-comp-meta"></span>
  </div>

  <div class="heat-table-title">Por Provincia</div>
  <div class="heat-wrap"><table class="heat" id="heat-prov"><thead></thead><tbody></tbody></table></div>

  <div class="heat-table-title">Por Región CUP (BAIRES)</div>
  <div class="heat-wrap"><table class="heat" id="heat-cup"><thead></thead><tbody></tbody></table></div>

  <p class="heat-note" id="heat-note"></p>
</section>
"""

# ── JS for Shape A (full brand × region heatmap) ─────────────────────
JS_SHAPE_A = r"""
/* === DDD Heatmap (Shape A: brand_monthly por region) ============== */
(function(){
  if (typeof D === 'undefined' || !D || !D.markets) return;
  let HEAT_PERIOD = 'q';   // m | q | s | ytd | mat
  let HEAT_METRIC = 'ms';  // ms | dms | du
  let HEAT_PRESET = 'top10';  // all | sie | top5 | top10 | custom
  let HEAT_SEARCH = '';
  // visibleBrands keyed by market: market -> Set<brand>
  const VIS_BY_MKT = {};

  // Determine periods (current + comparator) returning {curr:[idx], prev:[idx]|null, label, prevLabel}
  function periodIdxs(){
    const N = (D.months||[]).length;
    if (N === 0) return null;
    const lastIdx = N - 1;
    const lastMonth = D.months[lastIdx];
    function mkLabel(start, end){ return D.months[start] + (end>start ? '..'+D.months[end] : ''); }
    if (HEAT_PERIOD === 'm'){
      const prev = lastIdx>=1 ? [lastIdx-1] : null;
      return {curr:[lastIdx], prev, label: lastMonth, prevLabel: prev ? D.months[prev[0]] : null};
    }
    if (HEAT_PERIOD === 'q'){
      const curr = [lastIdx-2, lastIdx-1, lastIdx].filter(i=>i>=0);
      const prev = lastIdx-5>=0 ? [lastIdx-5, lastIdx-4, lastIdx-3] : null;
      return {curr, prev, label: mkLabel(curr[0], curr[curr.length-1]), prevLabel: prev ? mkLabel(prev[0], prev[2]) : null};
    }
    if (HEAT_PERIOD === 's'){
      const curr = Array.from({length:6}, (_,k)=>lastIdx-5+k).filter(i=>i>=0);
      const prev = lastIdx-11>=0 ? Array.from({length:6}, (_,k)=>lastIdx-11+k) : null;
      return {curr, prev, label: mkLabel(curr[0], curr[curr.length-1]), prevLabel: prev ? mkLabel(prev[0], prev[5]) : null};
    }
    if (HEAT_PERIOD === 'ytd'){
      // YTD = months in current year up to lastIdx
      const yr = lastMonth.split('-')[1];
      const curr = D.months.map((m,i)=>m.endsWith('-'+yr) ? i : -1).filter(i=>i>=0 && i<=lastIdx);
      // prev YTD: same N months in prior year
      const prevYr = String(parseInt(yr,10)-1);
      const prevAll = D.months.map((m,i)=>m.endsWith('-'+prevYr) ? i : -1).filter(i=>i>=0);
      const prev = prevAll.length >= curr.length ? prevAll.slice(0, curr.length) : null;
      return {curr, prev, label:'YTD '+yr, prevLabel: prev ? 'YTD '+prevYr : null};
    }
    if (HEAT_PERIOD === 'mat'){
      const curr = Array.from({length:12}, (_,k)=>lastIdx-11+k).filter(i=>i>=0);
      const prev = lastIdx-23>=0 ? Array.from({length:12}, (_,k)=>lastIdx-23+k) : null;
      return {curr, prev, label: 'MAT '+D.months[lastIdx], prevLabel: prev ? 'MAT '+D.months[lastIdx-12] : null};
    }
    return null;
  }

  function sumMonths(arr, idxs){
    if (!arr || !idxs) return 0;
    let s = 0;
    for (const i of idxs){ if (i>=0 && i<arr.length){ const v = arr[i]; if (typeof v === 'number') s += v; }}
    return s;
  }

  // Compute the full ranked list of brands for a market & period (used for preset filters + pills)
  function rankedBrands(market, regions, period){
    const mk = D.markets[market]; if (!mk) return [];
    const bm = mk.brand_monthly || {};
    const brands = Object.keys(bm);
    const sieList = (mk.brands || []).map(s=>String(s).toUpperCase());
    const brandTotal = {};
    for (const b of brands){
      let t = 0;
      for (const r of regions){
        const arr = (bm[b]||{})[r]; if (!arr) continue;
        t += sumMonths(arr, period.curr);
      }
      brandTotal[b] = t;
    }
    return brands.filter(b=>brandTotal[b]>0)
                 .sort((a,b)=>brandTotal[b]-brandTotal[a])
                 .map(b=>({brand:b, units:brandTotal[b], isSie: sieList.includes(String(b).toUpperCase())}));
  }

  function getVisibleSet(market, allRanked){
    if (!VIS_BY_MKT[market]) VIS_BY_MKT[market] = new Set();
    const cache = VIS_BY_MKT[market];
    if (HEAT_PRESET === 'all'){
      return new Set(allRanked.map(r=>r.brand));
    }
    if (HEAT_PRESET === 'sie'){
      return new Set(allRanked.filter(r=>r.isSie).map(r=>r.brand));
    }
    if (HEAT_PRESET === 'top5'){
      return new Set(allRanked.slice(0,5).map(r=>r.brand));
    }
    if (HEAT_PRESET === 'top10'){
      return new Set(allRanked.slice(0,10).map(r=>r.brand));
    }
    // custom: use cached set (or initialize to top10 first time)
    if (cache.size === 0){
      allRanked.slice(0,10).forEach(r=>cache.add(r.brand));
    }
    return cache;
  }

  // Returns: { rows:[{brand, isSie}], cols:[region], cells:{brand:{region:{ms,dms,du,units,units_prev}}}, max:{ms,abs_dms,abs_du} }
  function computeGrid(market, regions, period, visibleSet){
    const mk = D.markets[market]; if (!mk) return null;
    const bm = mk.brand_monthly || {};
    const tm = mk.total_monthly || {};
    const brands = Object.keys(bm);
    if (!brands.length) return null;

    // For each brand, compute total units in current period (national, across selected regions)
    const brandTotal = {};
    for (const b of brands){
      let t = 0;
      for (const r of regions){
        const arr = (bm[b]||{})[r]; if (!arr) continue;
        t += sumMonths(arr, period.curr);
      }
      brandTotal[b] = t;
    }

    // Sort brands by total units desc; mark SIE; filter by visibleSet
    const sieList = (mk.brands || []).map(s=>String(s).toUpperCase());
    const rows = brands.filter(b=>brandTotal[b]>0 && (!visibleSet || visibleSet.has(b)))
                       .sort((a,b)=>brandTotal[b]-brandTotal[a])
                       .map(b=>({
                         brand: b,
                         isSie: sieList.includes(String(b).toUpperCase())
                       }));

    // Sort regions by total market units in period desc
    const regTotal = {};
    for (const r of regions){
      regTotal[r] = sumMonths(tm[r] || (function(){
        // Fallback: sum brand_monthly across all brands
        let s=0; for (const b of brands){ s += sumMonths((bm[b]||{})[r], period.curr); } return [s];
      })(), period.curr);
    }
    const cols = regions.filter(r=>regTotal[r]>0).sort((a,b)=>regTotal[b]-regTotal[a]);

    // Build cells
    const cells = {};
    let max_ms = 0, max_abs_dms = 0, max_abs_du = 0;
    for (const row of rows){
      const b = row.brand;
      cells[b] = {};
      for (const r of cols){
        const arr = (bm[b]||{})[r] || null;
        const tot_arr = tm[r] || null;
        const u_act = sumMonths(arr, period.curr);
        const mkt_act = sumMonths(tot_arr, period.curr) || (function(){
          let s=0; for (const bb of brands){ s += sumMonths((bm[bb]||{})[r], period.curr); } return s;
        })();
        const ms_act = mkt_act > 0 ? (u_act/mkt_act*100) : null;
        let u_prev = null, mkt_prev = null, ms_prev = null, dms = null, du = null;
        if (period.prev){
          u_prev = sumMonths(arr, period.prev);
          mkt_prev = sumMonths(tot_arr, period.prev) || (function(){
            let s=0; for (const bb of brands){ s += sumMonths((bm[bb]||{})[r], period.prev); } return s;
          })();
          ms_prev = mkt_prev > 0 ? (u_prev/mkt_prev*100) : null;
          if (ms_act !== null && ms_prev !== null) dms = ms_act - ms_prev;
          if (u_prev > 0) du = (u_act - u_prev)/u_prev*100;
        }
        cells[b][r] = {u_act, u_prev, mkt_act, mkt_prev, ms_act, ms_prev, dms, du};
        if (ms_act !== null && ms_act > max_ms) max_ms = ms_act;
        if (dms !== null && Math.abs(dms) > max_abs_dms) max_abs_dms = Math.abs(dms);
        if (du !== null && Math.abs(du) > max_abs_du) max_abs_du = Math.abs(du);
      }
    }
    return {rows, cols, cells, max_ms, max_abs_dms, max_abs_du};
  }

  function colorMS(v, max){
    if (v === null || v === undefined || max <= 0) return {bg:'#fff', fg:'#9ca3af'};
    const t = Math.min(v/max, 1);
    // gradient #f3f4f6 → #1e40af
    const r = Math.round(243 + (30-243)*t);
    const g = Math.round(244 + (64-244)*t);
    const b = Math.round(246 + (175-246)*t);
    const fg = t > 0.55 ? '#fff' : '#1f2937';
    return {bg:`rgb(${r},${g},${b})`, fg};
  }
  function colorDiv(v, max){
    if (v === null || v === undefined || max <= 0) return {bg:'#fff', fg:'#9ca3af'};
    const t = Math.max(-1, Math.min(1, v/max));
    if (t >= 0){
      // white → green
      const r = Math.round(255 + (22-255)*t);
      const g = Math.round(255 + (163-255)*t);
      const b = Math.round(255 + (74-255)*t);
      return {bg:`rgb(${r},${g},${b})`, fg: t>0.55?'#fff':'#0f5132'};
    } else {
      const tt = -t;
      const r = Math.round(255 + (220-255)*tt);
      const g = Math.round(255 + (38-255)*tt);
      const b = Math.round(255 + (38-255)*tt);
      return {bg:`rgb(${r},${g},${b})`, fg: tt>0.55?'#fff':'#7f1d1d'};
    }
  }

  function fmtCell(cell, max){
    if (HEAT_METRIC === 'ms'){
      if (cell.ms_act === null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
      const col = colorMS(cell.ms_act, max.ms);
      return {txt: cell.ms_act.toFixed(1)+'%', bg: col.bg, fg: col.fg};
    }
    if (HEAT_METRIC === 'dms'){
      if (cell.dms === null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
      const col = colorDiv(cell.dms, max.dms);
      return {txt: (cell.dms>=0?'+':'')+cell.dms.toFixed(1), bg: col.bg, fg: col.fg};
    }
    if (HEAT_METRIC === 'du'){
      if (cell.du === null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
      const col = colorDiv(cell.du, max.du);
      return {txt: (cell.du>=0?'+':'')+cell.du.toFixed(0)+'%', bg: col.bg, fg: col.fg};
    }
    return {txt:'—', bg:'#fff', fg:'#9ca3af'};
  }

  function renderTable(tableId, regions, market, period, visibleSet){
    const tbl = document.getElementById(tableId); if (!tbl) return;
    const thead = tbl.querySelector('thead');
    const tbody = tbl.querySelector('tbody');
    if (!regions.length){
      thead.innerHTML = '';
      tbody.innerHTML = `<tr><td class="heat-empty">Sin regiones disponibles para esta vista.</td></tr>`;
      return;
    }
    const grid = computeGrid(market, regions, period, visibleSet);
    if (!grid || !grid.rows.length){
      thead.innerHTML = '';
      tbody.innerHTML = `<tr><td class="heat-empty">Sin datos para este mercado.</td></tr>`;
      return;
    }
    const max = {ms: Math.max(grid.max_ms, 1), dms: Math.max(grid.max_abs_dms, 0.1), du: Math.max(grid.max_abs_du, 1)};
    const cleanReg = r => r.startsWith('_') ? r.slice(1) : r;
    // Header
    let h = '<tr><th>Competidor</th>';
    for (const r of grid.cols){ h += `<th title="${r}">${cleanReg(r)}</th>`; }
    h += '</tr>';
    thead.innerHTML = h;
    // Body
    let b = '';
    for (const row of grid.rows){
      b += `<tr><th class="${row.isSie?'sie':''}" title="${row.brand}">${row.brand}</th>`;
      for (const r of grid.cols){
        const cell = grid.cells[row.brand][r];
        const f = fmtCell(cell, max);
        const titleParts = [`${row.brand} · ${r}`];
        if (cell.ms_act !== null) titleParts.push(`MS%: ${cell.ms_act.toFixed(2)}%`);
        if (cell.dms !== null) titleParts.push(`Δ MS%: ${(cell.dms>=0?'+':'')+cell.dms.toFixed(2)} pp`);
        if (cell.du !== null) titleParts.push(`Δ Units: ${(cell.du>=0?'+':'')+cell.du.toFixed(1)}%`);
        titleParts.push(`Units: ${cell.u_act.toLocaleString('es-AR')}`);
        b += `<td class="heat-cell" style="background:${f.bg};color:${f.fg}" title="${titleParts.join(' · ')}">${f.txt}</td>`;
      }
      b += '</tr>';
    }
    tbody.innerHTML = b;
  }

  function renderCompPills(market, allRanked, visibleSet){
    const el = document.getElementById('heat-comp-pills'); if (!el) return;
    const search = (HEAT_SEARCH||'').toUpperCase();
    const filtered = search ? allRanked.filter(r => r.brand.toUpperCase().includes(search)) : allRanked;
    el.innerHTML = filtered.map(r => {
      const on = visibleSet.has(r.brand);
      const cls = 'heat-comp-pill' + (on?' on':'') + (r.isSie?' sie':'');
      const safe = r.brand.replace(/'/g, "\\'").replace(/"/g, '&quot;');
      return `<button class="${cls}" data-brand="${safe}" title="${safe} · ${r.units.toLocaleString('es-AR')} u.">${r.isSie?'★ ':''}${r.brand}</button>`;
    }).join('');
    document.getElementById('heat-comp-meta').textContent =
      `${visibleSet.size}/${allRanked.length} visibles` + (search?` · filtro: "${HEAT_SEARCH}"`:'');
    // Re-bind clicks (delegation would be cleaner but this is short list)
    el.querySelectorAll('.heat-comp-pill').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const b = btn.dataset.brand;
        // Switch to custom preset
        if (HEAT_PRESET !== 'custom'){
          HEAT_PRESET = 'custom';
          document.querySelectorAll('#heat-preset button').forEach(x=>x.classList.remove('on'));
          // seed VIS_BY_MKT from current visibleSet
          VIS_BY_MKT[market] = new Set(visibleSet);
        }
        const cache = VIS_BY_MKT[market];
        if (cache.has(b)) cache.delete(b); else cache.add(b);
        window.renderHeat();
      });
    });
  }

  window.renderHeat = function renderHeat(){
    const market = (typeof cur !== 'undefined' && cur) ? cur : Object.keys(D.markets)[0];
    if (!market || !D.markets[market]){
      document.getElementById('heat-period-label').textContent = '';
      return;
    }
    const period = periodIdxs();
    if (!period) return;
    const allRegs = (D.regions || []).filter(r => r && r !== '-');
    const provRegs = allRegs.filter(r => !r.startsWith('_'));
    const cupRegs = allRegs.filter(r => r.startsWith('_'));
    // Rank brands using ALL regions (combined provinces + CUP)
    const allRanked = rankedBrands(market, allRegs, period);
    const visibleSet = getVisibleSet(market, allRanked);
    renderCompPills(market, allRanked, visibleSet);
    renderTable('heat-prov', provRegs, market, period, visibleSet);
    renderTable('heat-cup', cupRegs, market, period, visibleSet);
    // Period label
    const labelEl = document.getElementById('heat-period-label');
    if (labelEl){
      const prev = period.prevLabel ? ` (vs ${period.prevLabel})` : ' · sin comparador';
      labelEl.textContent = `${market} · ${period.label}${HEAT_METRIC==='ms'?'':prev}`;
    }
    const noteEl = document.getElementById('heat-note');
    if (noteEl){
      if (HEAT_METRIC !== 'ms' && !period.prev){
        noteEl.textContent = 'No hay período comparador disponible: la serie no es lo suficientemente larga para esta agregación.';
      } else {
        noteEl.textContent = 'Hover sobre cada celda para detalle. Filas = competidores por unidades; columnas = regiones por volumen del mercado.';
      }
    }
  };

  function bindControls(){
    document.querySelectorAll('#heat-period button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        HEAT_PERIOD = btn.dataset.p;
        document.querySelectorAll('#heat-period button').forEach(b=>b.classList.toggle('on', b===btn));
        window.renderHeat();
      });
    });
    document.querySelectorAll('#heat-metric button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        HEAT_METRIC = btn.dataset.m;
        document.querySelectorAll('#heat-metric button').forEach(b=>b.classList.toggle('on', b===btn));
        window.renderHeat();
      });
    });
    document.querySelectorAll('#heat-preset button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        HEAT_PRESET = btn.dataset.preset;
        document.querySelectorAll('#heat-preset button').forEach(b=>b.classList.toggle('on', b===btn));
        // Clear cached custom selection so preset takes effect cleanly
        const market = (typeof cur !== 'undefined' && cur) ? cur : Object.keys(D.markets)[0];
        if (market) VIS_BY_MKT[market] = new Set();
        window.renderHeat();
      });
    });
    const searchInput = document.getElementById('heat-search');
    if (searchInput){
      searchInput.addEventListener('input', ()=>{
        HEAT_SEARCH = searchInput.value || '';
        window.renderHeat();
      });
    }
  }

  // Wait for DOM + main app to set up `cur` variable
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', ()=>{ bindControls(); setTimeout(window.renderHeat, 100); });
  } else {
    bindControls();
    setTimeout(window.renderHeat, 100);
  }
  // Hook into market selector if exists — intercept clicks on .ml elements
  document.addEventListener('click', (e)=>{
    if (e.target.closest && e.target.closest('.ml')) setTimeout(window.renderHeat, 50);
  });
})();
"""

# ── JS for Shape B (SIE-only heatmap, simplified) ────────────────────
JS_SHAPE_B = r"""
/* === DDD Heatmap (Shape B: SIE x region only, no per-competitor) ==== */
(function(){
  const ROOT = window.OTC_DATA || {};
  const DD = ROOT.ddd || ROOT.dddGineco || ROOT.respDdd || null;
  if (!DD || !DD.markets && !DD.families) {
    const notEl = document.getElementById('heat-note');
    if (notEl) notEl.textContent = 'Data DDD no encontrada para esta linea.';
    return;
  }
  const MKTS = DD.markets || DD.families || {};
  const MONTHS = DD.months || [];
  let HEAT_PERIOD = 'q';
  let HEAT_METRIC = 'ms'; // ms (SIE share) | dms | du

  function periodIdxs(){
    const N = MONTHS.length;
    if (N === 0) return null;
    const lastIdx = N - 1;
    const lastMonth = MONTHS[lastIdx];
    function mkLabel(start, end){ return MONTHS[start] + (end>start ? '..'+MONTHS[end] : ''); }
    if (HEAT_PERIOD === 'm'){
      const prev = lastIdx>=1 ? [lastIdx-1] : null;
      return {curr:[lastIdx], prev, label: lastMonth, prevLabel: prev ? MONTHS[prev[0]] : null};
    }
    if (HEAT_PERIOD === 'q'){
      const curr = [lastIdx-2, lastIdx-1, lastIdx].filter(i=>i>=0);
      const prev = lastIdx-5>=0 ? [lastIdx-5, lastIdx-4, lastIdx-3] : null;
      return {curr, prev, label: mkLabel(curr[0], curr[curr.length-1]), prevLabel: prev ? mkLabel(prev[0], prev[2]) : null};
    }
    if (HEAT_PERIOD === 's'){
      const curr = Array.from({length:6}, (_,k)=>lastIdx-5+k).filter(i=>i>=0);
      const prev = lastIdx-11>=0 ? Array.from({length:6}, (_,k)=>lastIdx-11+k) : null;
      return {curr, prev, label: mkLabel(curr[0], curr[curr.length-1]), prevLabel: prev ? mkLabel(prev[0], prev[5]) : null};
    }
    if (HEAT_PERIOD === 'ytd'){
      const yr = lastMonth.split('-').pop();
      const curr = MONTHS.map((m,i)=>m.endsWith('-'+yr) ? i : -1).filter(i=>i>=0 && i<=lastIdx);
      const prevYr = String(parseInt(yr,10)-1);
      const prevAll = MONTHS.map((m,i)=>m.endsWith('-'+prevYr) ? i : -1).filter(i=>i>=0);
      const prev = prevAll.length >= curr.length ? prevAll.slice(0, curr.length) : null;
      return {curr, prev, label:'YTD '+yr, prevLabel: prev ? 'YTD '+prevYr : null};
    }
    if (HEAT_PERIOD === 'mat'){
      const curr = Array.from({length:12}, (_,k)=>lastIdx-11+k).filter(i=>i>=0);
      const prev = lastIdx-23>=0 ? Array.from({length:12}, (_,k)=>lastIdx-23+k) : null;
      return {curr, prev, label: 'MAT '+MONTHS[lastIdx], prevLabel: prev ? 'MAT '+MONTHS[lastIdx-12] : null};
    }
    return null;
  }

  // Returns map: region -> {sie, total, ms} for given idxs
  function aggregate(market, idxs){
    const mk = MKTS[market]; if (!mk) return {};
    // Shape: mk.molecule.all.regionsByMonth[month] = list of {name,total,sie,share}
    // OR mk.regionsByMonth[month] = same
    const rbm = (mk.regionsByMonth) || (mk.molecule && mk.molecule.all && mk.molecule.all.regionsByMonth) || {};
    const agg = {}; // region -> {sie:0, total:0}
    for (const i of idxs){
      const mn = MONTHS[i]; if (!mn) continue;
      const list = rbm[mn] || [];
      for (const r of list){
        const name = r.name;
        if (!agg[name]) agg[name] = {sie:0, total:0};
        agg[name].sie += Number(r.sie||0);
        agg[name].total += Number(r.total||0);
      }
    }
    for (const k of Object.keys(agg)){
      const a = agg[k];
      a.ms = a.total > 0 ? a.sie/a.total*100 : null;
    }
    return agg;
  }

  function colorMS(v, max){
    if (v === null || v === undefined || max <= 0) return {bg:'#fff', fg:'#9ca3af'};
    const t = Math.min(v/max, 1);
    const r = Math.round(243 + (30-243)*t);
    const g = Math.round(244 + (64-244)*t);
    const b = Math.round(246 + (175-246)*t);
    return {bg:`rgb(${r},${g},${b})`, fg: t > 0.55 ? '#fff' : '#1f2937'};
  }
  function colorDiv(v, max){
    if (v === null || v === undefined || max <= 0) return {bg:'#fff', fg:'#9ca3af'};
    const t = Math.max(-1, Math.min(1, v/max));
    if (t >= 0){
      const r = Math.round(255 + (22-255)*t);
      const g = Math.round(255 + (163-255)*t);
      const b = Math.round(255 + (74-255)*t);
      return {bg:`rgb(${r},${g},${b})`, fg: t>0.55?'#fff':'#0f5132'};
    } else {
      const tt = -t;
      const r = Math.round(255 + (220-255)*tt);
      const g = Math.round(255 + (38-255)*tt);
      const b = Math.round(255 + (38-255)*tt);
      return {bg:`rgb(${r},${g},${b})`, fg: tt>0.55?'#fff':'#7f1d1d'};
    }
  }

  function renderTable(tableId, regionFilter, market, period){
    const tbl = document.getElementById(tableId); if (!tbl) return;
    const thead = tbl.querySelector('thead');
    const tbody = tbl.querySelector('tbody');
    const aggCurr = aggregate(market, period.curr);
    const aggPrev = period.prev ? aggregate(market, period.prev) : null;
    const regs = Object.keys(aggCurr).filter(regionFilter).filter(r=>aggCurr[r].total>0)
                       .sort((a,b)=>aggCurr[b].total - aggCurr[a].total);
    if (!regs.length){
      thead.innerHTML = '';
      tbody.innerHTML = `<tr><td class="heat-empty">Sin datos para esta vista.</td></tr>`;
      return;
    }
    // Compute max
    let max_ms=0, max_abs_dms=0, max_abs_du=0;
    const rows = ['SIE','Mercado total'];
    for (const r of regs){
      const a = aggCurr[r];
      if (a.ms !== null && a.ms > max_ms) max_ms = a.ms;
      if (aggPrev && aggPrev[r]){
        const p = aggPrev[r];
        if (p.ms !== null && a.ms !== null){
          const dms = a.ms - p.ms;
          if (Math.abs(dms) > max_abs_dms) max_abs_dms = Math.abs(dms);
        }
        if (p.sie > 0){
          const du = (a.sie - p.sie)/p.sie*100;
          if (Math.abs(du) > max_abs_du) max_abs_du = Math.abs(du);
        }
        if (p.total > 0){
          const du2 = (a.total - p.total)/p.total*100;
          if (Math.abs(du2) > max_abs_du) max_abs_du = Math.abs(du2);
        }
      }
    }
    const max = {ms: Math.max(max_ms,1), dms: Math.max(max_abs_dms, 0.1), du: Math.max(max_abs_du, 1)};
    const cleanReg = r => r.startsWith('_') ? r.slice(1) : r;
    let h = '<tr><th>Serie</th>';
    for (const r of regs){ h += `<th title="${r}">${cleanReg(r)}</th>`; }
    h += '</tr>';
    thead.innerHTML = h;

    function cellFor(serie, region){
      const a = aggCurr[region]; const p = aggPrev ? aggPrev[region] : null;
      const v_act = serie==='SIE' ? a.sie : a.total;
      const v_prev = p ? (serie==='SIE' ? p.sie : p.total) : null;
      const ms_act = serie==='SIE' ? a.ms : 100;
      const ms_prev = (p && serie==='SIE') ? p.ms : null;
      let dms = null, du = null;
      if (ms_act !== null && ms_prev !== null) dms = ms_act - ms_prev;
      if (v_prev !== null && v_prev > 0) du = (v_act - v_prev)/v_prev*100;
      if (HEAT_METRIC === 'ms'){
        if (serie === 'Mercado total'){
          return {txt: v_act.toLocaleString('es-AR'), bg:'#fafafa', fg:'#525252'};
        }
        if (ms_act === null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorMS(ms_act, max.ms);
        return {txt: ms_act.toFixed(1)+'%', bg: c.bg, fg: c.fg};
      }
      if (HEAT_METRIC === 'dms'){
        if (serie === 'Mercado total') return {txt:'—', bg:'#fafafa', fg:'#9ca3af'};
        if (dms === null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorDiv(dms, max.dms);
        return {txt:(dms>=0?'+':'')+dms.toFixed(1), bg: c.bg, fg: c.fg};
      }
      if (HEAT_METRIC === 'du'){
        if (du === null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorDiv(du, max.du);
        return {txt:(du>=0?'+':'')+du.toFixed(0)+'%', bg: c.bg, fg: c.fg};
      }
      return {txt:'—', bg:'#fff', fg:'#9ca3af'};
    }

    let b = '';
    for (const serie of rows){
      b += `<tr><th class="${serie==='SIE'?'sie':''}">${serie}</th>`;
      for (const r of regs){
        const f = cellFor(serie, r);
        b += `<td class="heat-cell" style="background:${f.bg};color:${f.fg}" title="${serie} · ${r}">${f.txt}</td>`;
      }
      b += '</tr>';
    }
    tbody.innerHTML = b;
  }

  function getCurrentMarket(){
    // App-specific: try common variable names
    if (typeof cur !== 'undefined' && cur && MKTS[cur]) return cur;
    return Object.keys(MKTS)[0];
  }

  window.renderHeat = function renderHeat(){
    const market = getCurrentMarket();
    if (!market) return;
    const period = periodIdxs(); if (!period) return;
    const provFilter = r => r && r !== '-' && !r.startsWith('_');
    const cupFilter  = r => r && r.startsWith('_');
    renderTable('heat-prov', provFilter, market, period);
    renderTable('heat-cup', cupFilter, market, period);
    const labelEl = document.getElementById('heat-period-label');
    if (labelEl){
      const prev = period.prevLabel ? ` (vs ${period.prevLabel})` : ' · sin comparador';
      labelEl.textContent = `${market} · ${period.label}${HEAT_METRIC==='ms'?'':prev}`;
    }
    const noteEl = document.getElementById('heat-note');
    if (noteEl){
      let txt = 'Esta linea no expone unidades por competidor individual en la data DDD. Mostrando SIE vs Mercado Total agregado por region.';
      if (HEAT_METRIC !== 'ms' && !period.prev) txt += ' Sin periodo comparador disponible.';
      noteEl.textContent = txt;
    }
  };

  function bindControls(){
    document.querySelectorAll('#heat-period button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        HEAT_PERIOD = btn.dataset.p;
        document.querySelectorAll('#heat-period button').forEach(b=>b.classList.toggle('on', b===btn));
        window.renderHeat();
      });
    });
    document.querySelectorAll('#heat-metric button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        HEAT_METRIC = btn.dataset.m;
        document.querySelectorAll('#heat-metric button').forEach(b=>b.classList.toggle('on', b===btn));
        window.renderHeat();
      });
    });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', ()=>{ bindControls(); setTimeout(window.renderHeat, 300); });
  } else {
    bindControls();
    setTimeout(window.renderHeat, 300);
  }
  document.addEventListener('click', (e)=>{
    if (e.target.closest && e.target.closest('.ml,.mkt-list,[data-market]')) setTimeout(window.renderHeat, 100);
  });
})();
"""


HEAT_VERSION = 'v2-with-pills'


def strip_old(text: str) -> str:
    """Remove previously-injected heatmap CSS + section + script blocks."""
    # Strip CSS block (between '/* Heatmap section */' and the comment terminator we don't have — use sentinel)
    # Easier: remove the whole CSS region from '/* Heatmap section */' through '.heat-note{...}'
    text = re.sub(r'\n/\* Heatmap section \*/.*?\.heat-note\{[^}]*\}', '', text, count=1, flags=re.DOTALL)
    # Strip section (between '<section class="heat-section" id="s5-heat">' and '</section>')
    text = re.sub(r'<section class="heat-section" id="s5-heat">.*?</section>\n?', '', text, count=1, flags=re.DOTALL)
    # Strip the IIFE script: it's a <script> that contains 'DDD Heatmap (Shape A' or 'DDD Heatmap (Shape B'
    text = re.sub(r'<script>\s*\n?/\* === DDD Heatmap \(Shape [AB]\).*?</script>\n?', '', text, count=1, flags=re.DOTALL)
    return text


def inject(path: Path, shape: str) -> str:
    text = path.read_text(encoding='utf-8', errors='replace')
    if f'HEAT_VERSION="{HEAT_VERSION}"' in text:
        return f'  [{path.relative_to(REPO)}] SKIP (ya en {HEAT_VERSION})'
    # Strip old injection if present
    if 'id="s5-heat"' in text:
        text = strip_old(text)

    # 1) Inject CSS before first </style>
    m_style = re.search(r'</style>', text)
    if m_style:
        text = text[:m_style.start()] + CSS + text[m_style.start():]
    else:
        # Wrap in a style tag at head
        m_head = re.search(r'</head>', text)
        if m_head:
            text = text[:m_head.start()] + '<style>' + CSS + '</style>\n' + text[m_head.start():]

    # 2) Inject HTML — try to insert right before </body> or the first <script> after main content
    # Prefer: insert just before </body>
    m_body = re.search(r'</body>', text)
    if m_body:
        text = text[:m_body.start()] + HTML + '\n' + text[m_body.start():]
    else:
        # Fallback: append at end
        text = text + HTML

    # 3) Inject JS before </body> (after HTML). Use shape-specific bundle wrapped in <script>
    version_marker = f'\n/* HEAT_VERSION="{HEAT_VERSION}" */\n'
    js_bundle = '<script>' + version_marker + (JS_SHAPE_A if shape == 'A' else JS_SHAPE_B) + '\n</script>\n'
    m_body2 = re.search(r'</body>', text)
    if m_body2:
        text = text[:m_body2.start()] + js_bundle + text[m_body2.start():]
    else:
        text = text + js_bundle

    path.write_text(text, encoding='utf-8', newline='')
    return f'  [{path.relative_to(REPO)}] OK (shape={shape}, {path.stat().st_size:,} bytes)'


def main():
    print('Inyectando heatmap DDD...\n')
    for rel in FILES_SHAPE_A:
        print(inject(REPO/rel, 'A'))
    for rel in FILES_SHAPE_B:
        print(inject(REPO/rel, 'B'))
    print('\nListo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
