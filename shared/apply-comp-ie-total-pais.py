"""Aplica las modificaciones del template OTC competidores.html a las otras 6
paginas de competidores (cardio/ATB/respiratorio/SNC/dermato/mujer DDD).

Cambios (todos relativos a OTC/DDD/competidores.html como source de verdad):
1. JS: agregar IE en cells de computeGridA + funcion computeCountryRow
2. JS: agregar colorIE + fmtIE
3. JS: variable PROV_FILTER
4. JS: renderTableA con opts (totalRow, clickable, activeProv) + IE sub-col
5. HTML: cambiar 'Por Region CUP (zonas IQVIA detalladas)' -> 'Por Region' +
   boton limpiar filtro
6. JS: render() pasa opts y filtra cupRegs por PROV_FILTER
7. JS: event handler para click en provincia + limpiar filtro
8. JS: cup-meta refleja si hay filtro activo
9. CSS: row-total-pais + row-active + sub-ie

Idempotente: si ya esta aplicado (detecta `PROV_FILTER` variable), skip.

Estrategia: detecta los bloques OLD en cada file y los reemplaza por NEW
extraidos de OTC. Las diferencias entre archivos (titulo + Bonos PAP nav)
no afectan estas modificaciones porque estan en zonas distintas del file.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SOURCE = REPO / 'OTC' / 'DDD' / 'competidores.html'
TARGETS = [
    'cardio/DDD/competidores.html',
    'ATB/DDD/competidores.html',
    'respiratorio/DDD/competidores.html',
    'mujer/DDD/competidores.html',
    'SNC/DDD/competidores.html',
    'dermatologia/competidores.html',
]

# Cada (OLD, NEW) es un reemplazo. OLD debe ser un substring exacto que existe
# en el archivo destino antes del cambio. NEW es el reemplazo.

PATCHES = []

# -- 1. State variable PROV_FILTER --
PATCHES.append((
    "  let HEAT_MARKET = null;\n"
    "  const VIS_BY_MKT = {};  // market -> Set<brand> when in custom mode",
    "  let HEAT_MARKET = null;\n"
    "  let PROV_FILTER = null;  // provincia activa para filtrar la tabla Region (click)\n"
    "  const VIS_BY_MKT = {};  // market -> Set<brand> when in custom mode",
))

# -- 2. IE en cells de computeGridA + computeCountryRow --
PATCHES.append((
    "        cells[b][r] = {u_act:u_a, u_prev:u_p, mkt_act:mkt_a, mkt_prev:mkt_p, ms_act:ms_a, ms_prev:ms_p, dms, du};\n"
    "        if (ms_a!==null && ms_a>max_ms) max_ms = ms_a;\n"
    "        if (dms!==null && Math.abs(dms)>max_abs_dms) max_abs_dms = Math.abs(dms);\n"
    "        if (du!==null && Math.abs(du)>max_abs_du) max_abs_du = Math.abs(du);\n"
    "      }\n"
    "    }\n"
    "    return {rows, cols, cells, max_ms, max_abs_dms, max_abs_du};\n"
    "  }",
    "        // IE vs mercado (base 100): (brand_growth / market_growth) × 100\n"
    "        let ie = null;\n"
    "        if (u_p > 0 && mkt_a > 0 && mkt_p > 0) {\n"
    "          const bg = u_a / u_p;\n"
    "          const mg = mkt_a / mkt_p;\n"
    "          if (mg > 0) ie = (bg / mg) * 100;\n"
    "          if (ie !== null && ie > 999) ie = 999;\n"
    "        }\n"
    "        cells[b][r] = {u_act:u_a, u_prev:u_p, mkt_act:mkt_a, mkt_prev:mkt_p, ms_act:ms_a, ms_prev:ms_p, dms, du, ie};\n"
    "        if (ms_a!==null && ms_a>max_ms) max_ms = ms_a;\n"
    "        if (dms!==null && Math.abs(dms)>max_abs_dms) max_abs_dms = Math.abs(dms);\n"
    "        if (du!==null && Math.abs(du)>max_abs_du) max_abs_du = Math.abs(du);\n"
    "      }\n"
    "    }\n"
    "    return {rows, cols, cells, max_ms, max_abs_dms, max_abs_du};\n"
    "  }\n"
    "\n"
    "  // Compute country (Total País) aggregates from a grid\n"
    "  function computeCountryRow(grid){\n"
    "    const countryCells = {};\n"
    "    for (const row of grid.rows){\n"
    "      const b = row.brand;\n"
    "      let u_a_c=0, u_p_c=0, mkt_a_c=0, mkt_p_c=0;\n"
    "      let havePrev = false;\n"
    "      for (const r of grid.cols){\n"
    "        const c = grid.cells[b][r];\n"
    "        u_a_c += Number(c.u_act||0);\n"
    "        mkt_a_c += Number(c.mkt_act||0);\n"
    "        if (c.u_prev !== null && c.u_prev !== undefined){ u_p_c += Number(c.u_prev||0); havePrev = true; }\n"
    "        if (c.mkt_prev !== null && c.mkt_prev !== undefined) mkt_p_c += Number(c.mkt_prev||0);\n"
    "      }\n"
    "      const ms_a_c = mkt_a_c>0 ? u_a_c/mkt_a_c*100 : null;\n"
    "      const ms_p_c = (havePrev && mkt_p_c>0) ? u_p_c/mkt_p_c*100 : null;\n"
    "      const dms_c = (ms_a_c!==null && ms_p_c!==null) ? ms_a_c-ms_p_c : null;\n"
    "      const du_c = (havePrev && u_p_c>0) ? (u_a_c-u_p_c)/u_p_c*100 : null;\n"
    "      let ie_c = null;\n"
    "      if (havePrev && u_p_c>0 && mkt_a_c>0 && mkt_p_c>0){\n"
    "        const bg = u_a_c/u_p_c, mg = mkt_a_c/mkt_p_c;\n"
    "        if (mg>0) ie_c = (bg/mg)*100;\n"
    "        if (ie_c !== null && ie_c > 999) ie_c = 999;\n"
    "      }\n"
    "      countryCells[b] = {u_act:u_a_c, u_prev:havePrev?u_p_c:null, mkt_act:mkt_a_c, mkt_prev:havePrev?mkt_p_c:null,\n"
    "                        ms_act:ms_a_c, ms_prev:ms_p_c, dms:dms_c, du:du_c, ie:ie_c};\n"
    "    }\n"
    "    return countryCells;\n"
    "  }",
))

# -- 3. colorIE + fmtIE despues de colorDiv --
PATCHES.append((
    "      const r = Math.round(255+(220-255)*tt);\n"
    "      const g = Math.round(255+(38-255)*tt);\n"
    "      const b = Math.round(255+(38-255)*tt);\n"
    "      return {bg:`rgb(${r},${g},${b})`, fg: tt>0.3?'#fff':'#000'};\n"
    "    }\n"
    "  }\n"
    "  function fmtCellMetric(cell, max){",
    "      const r = Math.round(255+(220-255)*tt);\n"
    "      const g = Math.round(255+(38-255)*tt);\n"
    "      const b = Math.round(255+(38-255)*tt);\n"
    "      return {bg:`rgb(${r},${g},${b})`, fg: tt>0.3?'#fff':'#000'};\n"
    "    }\n"
    "  }\n"
    "  // Color para IE: anchored at 100 (base), ±50 saturates\n"
    "  function colorIE(v){\n"
    "    if (v==null) return {bg:'#fff', fg:'#9ca3af'};\n"
    "    const diff = v - 100;\n"
    "    const t = Math.max(-1, Math.min(1, diff/50));\n"
    "    if (t>=0){\n"
    "      const r = Math.round(255+(22-255)*t);\n"
    "      const g = Math.round(255+(163-255)*t);\n"
    "      const b = Math.round(255+(74-255)*t);\n"
    "      return {bg:`rgb(${r},${g},${b})`, fg: t>0.3?'#fff':'#000'};\n"
    "    } else {\n"
    "      const tt = -t;\n"
    "      const r = Math.round(255+(220-255)*tt);\n"
    "      const g = Math.round(255+(38-255)*tt);\n"
    "      const b = Math.round(255+(38-255)*tt);\n"
    "      return {bg:`rgb(${r},${g},${b})`, fg: tt>0.3?'#fff':'#000'};\n"
    "    }\n"
    "  }\n"
    "  function fmtIE(v){ return v==null ? '—' : Math.round(v).toString(); }\n"
    "  function fmtCellMetric(cell, max){",
))

# -- 4. Reemplazo total de renderTableA --
PATCHES.append((
    "  // === Render Shape A table (TRANSPOSED: regions=rows, competitors=cols) ===\n"
    "  function renderTableA(tableId, regions, market, period, visibleSet){\n"
    "    const tbl = document.getElementById(tableId);\n"
    "    const thead = tbl.querySelector('thead'); const tbody = tbl.querySelector('tbody');\n"
    "    if (!regions.length){ thead.innerHTML=''; tbody.innerHTML='<tr><td class=\"empty\">Sin regiones.</td></tr>'; return; }\n"
    "    const grid = computeGridA(market, regions, period, visibleSet);\n"
    "    if (!grid || !grid.rows.length){ thead.innerHTML=''; tbody.innerHTML='<tr><td class=\"empty\">Sin datos visibles. Activá competidores en el filtro.</td></tr>'; return; }\n"
    "    const max = {ms: Math.max(grid.max_ms,1), dms: Math.max(grid.max_abs_dms, 0.1), du: Math.max(grid.max_abs_du, 1)};\n"
    "    const cleanReg = r => r.startsWith('_') ? r.slice(1) : r;\n"
    "    // Header con DOS filas: competidor (colspan=2) y abajo sub-headers metric | Unidades\n"
    "    // Las sub-headers incluyen el periodo activo y, si es Δ, el comparador\n"
    "    const pLab = period.label || '';\n"
    "    const ppLab = period.prevLabel || '';\n"
    "    let metricLabel;\n"
    "    if (HEAT_METRIC==='ms')       metricLabel = 'MS%';\n"
    "    else if (HEAT_METRIC==='dms') metricLabel = 'VAR MS%';\n"
    "    else                          metricLabel = 'VAR UNIDADES%';\n"
    "    const unitsLabel = 'Unidades';\n"
    "    let h = '<tr><th rowspan=\"2\">Región / Provincia</th>';\n"
    "    for (const row of grid.rows){\n"
    "      const cls = row.isSie ? 'sie sie-col' : '';\n"
    "      h += `<th class=\"${cls}\" colspan=\"2\" title=\"${row.brand}\" style=\"border-bottom:1px solid rgba(255,255,255,.15)\">${row.isSie?'★ ':''}${row.brand}</th>`;\n"
    "    }\n"
    "    h += '</tr><tr>';\n"
    "    for (const row of grid.rows){\n"
    "      const cls = row.isSie ? 'sie sie-col sub' : 'sub';\n"
    "      h += `<th class=\"${cls}\" style=\"font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;\" title=\"${metricLabel}\">${metricLabel}</th>`;\n"
    "      h += `<th class=\"${cls}\" style=\"font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;\" title=\"${unitsLabel}\">${unitsLabel}</th>`;\n"
    "    }\n"
    "    h += '</tr>';\n"
    "    thead.innerHTML = h;\n"
    "    // Body: una fila por región, dos celdas por competidor (MS% colored + Units plain)\n"
    "    function fmtUnits(u){\n"
    "      if (u==null) return '—';\n"
    "      if (u >= 1e6) return (u/1e6).toFixed(1)+'M';\n"
    "      if (u >= 1e3) return (u/1e3).toFixed(1)+'k';\n"
    "      return u.toLocaleString('es-AR');\n"
    "    }\n"
    "    let b = '';\n"
    "    for (const r of grid.cols){\n"
    "      b += `<tr><th title=\"${r}\">${cleanReg(r)}</th>`;\n"
    "      for (const row of grid.rows){\n"
    "        const cell = grid.cells[row.brand][r];\n"
    "        const f = fmtCellMetric(cell, max);\n"
    "        const tt = [`${row.brand} · ${r}`];\n"
    "        tt.push(`Período: ${period.label}`);\n"
    "        if (cell.ms_act!=null) tt.push(`MS%: ${cell.ms_act.toFixed(2)}%`);\n"
    "        if (cell.dms!=null) tt.push(`Δ MS%: ${(cell.dms>=0?'+':'')+cell.dms.toFixed(2)} pp (vs ${period.prevLabel||'—'})`);\n"
    "        if (cell.du!=null) tt.push(`Δ U: ${(cell.du>=0?'+':'')+cell.du.toFixed(1)}% (vs ${period.prevLabel||'—'})`);\n"
    "        tt.push(`Unidades: ${cell.u_act.toLocaleString('es-AR')}`);\n"
    "        if (cell.mkt_act > 0){\n"
    "          const perPct = cell.mkt_act / 100;\n"
    "          tt.push(`1% MS% = ${Math.round(perPct).toLocaleString('es-AR')} u. (mercado total: ${cell.mkt_act.toLocaleString('es-AR')})`);\n"
    "        }\n"
    "        const tdCls = row.isSie ? 'sie-col' : '';\n"
    "        const ttStr = tt.join('\\n');\n"
    "        // Sub-col 1: metric (con heat color)\n"
    "        b += `<td class=\"${tdCls} sub-metric\" style=\"background:${f.bg};color:${f.fg}\" title=\"${ttStr}\">${f.txt}</td>`;\n"
    "        // Sub-col 2: unidades (neutro)\n"
    "        const uStr = fmtUnits(cell.u_act);\n"
    "        b += `<td class=\"${tdCls} sub-units\" style=\"color:#525252;background:#fafafa;font-weight:500;\" title=\"${ttStr}\">${uStr}</td>`;\n"
    "      }\n"
    "      b += '</tr>';\n"
    "    }\n"
    "    tbody.innerHTML = b;\n"
    "  }",
    None  # se llena abajo extrayendo del OTC source
))

# -- 5. Titulo Por Region + boton limpiar --
PATCHES.append((
    '    <div class="tbl-title" style="margin-top:18px;"><span>Por Región CUP (zonas IQVIA detalladas) <span id="cup-period" style="font-weight:400;color:#6b7280;font-family:IBM Plex Mono,monospace;font-size:9px;letter-spacing:.04em;text-transform:none;margin-left:6px;"></span></span><span class="meta" id="cup-meta"></span></div>',
    '    <div class="tbl-title" style="margin-top:18px;"><span>Por Región <span id="cup-period" style="font-weight:400;color:#6b7280;font-family:IBM Plex Mono,monospace;font-size:9px;letter-spacing:.04em;text-transform:none;margin-left:6px;"></span> <button id="btn-clear-prov-filter" type="button" style="display:none;margin-left:10px;padding:4px 10px;font-size:10px;font-weight:600;color:#b01e1e;background:#fff;border:1px solid #b01e1e;border-radius:5px;cursor:pointer;font-family:IBM Plex Sans,sans-serif;">✕ Limpiar filtro</button></span><span class="meta" id="cup-meta"></span></div>',
))

# -- 6. render() para SHAPE A con opts y filtro --
PATCHES.append((
    "    if (SHAPE==='A'){\n"
    "      // Pills + ranking use the raw (full) data for accuracy\n"
    "      const allRanked = rankedBrandsA(HEAT_MARKET, allRegs, period);\n"
    "      const visibleSet = getVisibleSet(HEAT_MARKET, allRanked);\n"
    "      renderPills(HEAT_MARKET, allRanked, visibleSet);\n"
    "      // Province table: aggregated view\n"
    "      withProvinceView(HEAT_MARKET, () => {\n"
    "        const provView = MKTS[PROV_MKT_KEY];\n"
    "        const provNames = Object.keys(provView.total_monthly);\n"
    "        renderTableA('hm-prov', provNames, PROV_MKT_KEY, period, visibleSet);\n"
    "      });\n"
    "      // CUP/Region table: raw zones\n"
    "      renderTableA('hm-cup', cupRegs, HEAT_MARKET, period, visibleSet);\n"
    "    } else {",
    "    if (SHAPE==='A'){\n"
    "      // Pills + ranking use the raw (full) data for accuracy\n"
    "      const allRanked = rankedBrandsA(HEAT_MARKET, allRegs, period);\n"
    "      const visibleSet = getVisibleSet(HEAT_MARKET, allRanked);\n"
    "      renderPills(HEAT_MARKET, allRanked, visibleSet);\n"
    "      // Province table: aggregated view + Total País + clickable rows\n"
    "      withProvinceView(HEAT_MARKET, () => {\n"
    "        const provView = MKTS[PROV_MKT_KEY];\n"
    "        const provNames = Object.keys(provView.total_monthly);\n"
    "        renderTableA('hm-prov', provNames, PROV_MKT_KEY, period, visibleSet,\n"
    "                     {totalRow:true, clickable:true, activeProv: PROV_FILTER});\n"
    "      });\n"
    "      // CUP/Region table: raw zones, filtered by selected province if any\n"
    "      const cupRegsFiltered = PROV_FILTER\n"
    "        ? cupRegs.filter(r => regionToProvince(r) === PROV_FILTER)\n"
    "        : cupRegs;\n"
    "      renderTableA('hm-cup', cupRegsFiltered, HEAT_MARKET, period, visibleSet);\n"
    "      // Mostrar/ocultar boton de limpiar filtro\n"
    "      const clrBtn = document.getElementById('btn-clear-prov-filter');\n"
    "      if (clrBtn) clrBtn.style.display = PROV_FILTER ? 'inline-block' : 'none';\n"
    "    } else {",
))

# -- 7. cup-meta refleja filtro activo --
PATCHES.append((
    "    document.getElementById('cup-meta').textContent = `${cupRegs.length} zonas CUP`; document.getElementById('cup-period').textContent = periodInfo;\n"
    "  }",
    "    if (PROV_FILTER){\n"
    "      const filteredCount = (SHAPE==='A')\n"
    "        ? cupRegs.filter(r => regionToProvince(r) === PROV_FILTER).length\n"
    "        : (function(){ const aggC = aggregateB(HEAT_MARKET, period.curr); return Object.keys(aggC).filter(r => regionToProvince(r) === PROV_FILTER && aggC[r].total>0).length; })();\n"
    "      document.getElementById('cup-meta').textContent = `${filteredCount} zonas · filtrado: ${PROV_FILTER}`;\n"
    "    } else {\n"
    "      document.getElementById('cup-meta').textContent = `${cupRegs.length} zonas`;\n"
    "    }\n"
    "    document.getElementById('cup-period').textContent = periodInfo;\n"
    "  }",
))

# -- 8. Event handler para click en provincia + reset filtro --
PATCHES.append((
    "  // === Wire up controls (event delegation for pills) ===\n"
    "  document.addEventListener('click', (e)=>{\n"
    "    const t = e.target;\n"
    "    if (t.matches && t.matches('.mkt-pill')){\n"
    "      HEAT_MARKET = t.dataset.mkt;\n"
    "      document.querySelectorAll('.mkt-pill').forEach(b=>b.classList.toggle('on', b===t));\n"
    "      render();\n"
    "    } else if (t.closest && t.closest('#ctl-period')){",
    "  // === Wire up controls (event delegation for pills) ===\n"
    "  document.addEventListener('click', (e)=>{\n"
    "    const t = e.target;\n"
    "    // Click en boton de limpiar filtro de provincia\n"
    "    if (t && t.id === 'btn-clear-prov-filter'){\n"
    "      PROV_FILTER = null;\n"
    "      render();\n"
    "      return;\n"
    "    }\n"
    "    // Click en fila de la tabla Provincia (no en TOTAL PAÍS)\n"
    "    const provRow = t && t.closest && t.closest('#hm-prov tbody tr[data-prov]');\n"
    "    if (provRow){\n"
    "      const newProv = provRow.dataset.prov;\n"
    "      PROV_FILTER = (PROV_FILTER === newProv) ? null : newProv;\n"
    "      render();\n"
    "      // Scroll suave a la tabla CUP\n"
    "      const cupTitle = document.getElementById('cup-period');\n"
    "      if (cupTitle && PROV_FILTER) cupTitle.closest('.tbl-title').scrollIntoView({behavior:'smooth', block:'start'});\n"
    "      return;\n"
    "    }\n"
    "    if (t.matches && t.matches('.mkt-pill')){\n"
    "      HEAT_MARKET = t.dataset.mkt;\n"
    "      PROV_FILTER = null;  // limpiar filtro al cambiar mercado\n"
    "      document.querySelectorAll('.mkt-pill').forEach(b=>b.classList.toggle('on', b===t));\n"
    "      render();\n"
    "    } else if (t.closest && t.closest('#ctl-period')){",
))

# -- 9. CSS para total-pais + active row + sub-ie --
PATCHES.append((
    ".note{font-size:10px;color:var(--mut);margin-top:8px;font-style:italic;}",
    ".note{font-size:10px;color:var(--mut);margin-top:8px;font-style:italic;}\n"
    "/* Total País row + click-to-filter province feedback */\n"
    "table.hm tbody tr.row-total-pais th,\n"
    "table.hm tbody tr.row-total-pais td{position:sticky;border-top:2px solid #b01e1e;border-bottom:1px solid #1f2937;}\n"
    "table.hm tbody tr.row-total-pais th{background:#1f2937 !important;color:#fff !important;font-weight:700;letter-spacing:.04em;}\n"
    "table.hm tbody tr[data-prov]{cursor:pointer;transition:background .15s;}\n"
    "table.hm tbody tr[data-prov]:hover th{background:rgba(176,30,30,.08) !important;}\n"
    "table.hm tbody tr.row-active th{background:#fef2f2 !important;color:#b01e1e !important;border-left:3px solid #b01e1e !important;font-weight:700;}\n"
    "table.hm tbody tr.row-active td{box-shadow:inset 0 0 0 9999px rgba(176,30,30,.04);}\n"
    "table.hm td.sub-ie{font-family:'IBM Plex Mono',monospace;font-size:9px;text-align:center;}\n"
    "table.hm thead tr:first-child th[colspan=\"3\"]{border-right:2px solid #d4d4d4;}\n"
    "table.hm td.sub-ie:not(:last-child){border-right:2px solid #d4d4d4 !important;}",
))


def extract_new_renderTableA(source_html):
    """Extract the new renderTableA function from the OTC source."""
    m = re.search(
        r'  // === Render Shape A table.*?\n  // === Render Shape B table',
        source_html, re.DOTALL
    )
    if not m:
        raise RuntimeError('No se pudo extraer renderTableA del source OTC')
    # Volvemos todo menos los ultimos 2 lines (que son del Shape B header)
    block = m.group(0)
    # Cortamos en el "// === Render Shape B" exclusivo
    end = block.find('  // === Render Shape B table')
    new_block = block[:end].rstrip() + '\n'
    return new_block


def patch_file(path, new_renderTableA):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')
    orig = t

    # Idempotency
    if 'PROV_FILTER' in t:
        return 'already-applied'

    # Aplicar cada patch
    for i, (old, new) in enumerate(PATCHES):
        if new is None:  # placeholder para renderTableA
            new = new_renderTableA
        if old not in t:
            return f'patch-{i+1}-not-found'
        t = t.replace(old, new, 1)

    if t == orig:
        return 'no-change'
    p.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    src = SOURCE.read_text(encoding='utf-8')
    new_renderTableA = extract_new_renderTableA(src)
    # El patch 4 OLD es la version vieja de renderTableA. NEW debe ser el nuevo.
    # Como new_renderTableA termina con '\n', y el OLD termina con '  }', necesitamos ajustar.
    # Re-leemos el OLD y el NEW para que matchen.
    # Para simplificar: tomamos NEW como new_renderTableA tal cual (con su \n final).
    # El OLD termina con "  }" sin trailing \n.
    # Vamos a ajustar: el OLD termina con "  }" (sin \n) y new_renderTableA termina con "  }\n".
    # Para que el reemplazo sea limpio, ajustamos OLD para incluir el \n posterior.
    # ESTE detalle se maneja porque en el archivo target hay un '\n\n  // === Render Shape B'
    # despues de OLD. Asi que NEW debe terminar con '\n\n' para conservar la separacion.
    new_renderTableA = new_renderTableA.rstrip() + '\n\n'
    # Ajustar el patch 4: OLD termina con "  }" y debe consumir hasta antes de "  // === Render Shape B"
    OLD_4 = PATCHES[3][0]
    OLD_4_full = OLD_4 + "\n\n"
    PATCHES[3] = (OLD_4_full, new_renderTableA)

    for path in TARGETS:
        result = patch_file(path, new_renderTableA)
        print(f'  {path}: {result}')


if __name__ == '__main__':
    main()
