"""Cambiar la redistribución del shortfall: en vez de prorratearlo entre todos
los meses futuros del año, hacerlo SOLO sobre los próximos 3 meses (trimestre)
desde el primer mes sin real.

Tambien agregar al strip de totales:
  - 'Próximo: <mes> +X u.'  unidades redistribuidas al proximo mes
  - 'Nuevo target <mes>: Y u.'  budget + redistribuido en ese mes
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

OLD = """  // ── Redistribución mensual: shortfall acumulado se redistribuye a meses futuros ──
  const __origBudgetArr = budget.slice();
  let __sfShort = 0, __sfRemain = 0, __sfReal = 0, __sfBudget = 0;
  for(let i=0;i<12;i++){
    const b = +budget[i]||0, r = real[i];
    __sfBudget += b;
    if(r!=null){ __sfReal += +r||0; __sfShort += Math.max(0, b - (+r||0)); }
    else if(b>0){ __sfRemain++; }
  }
  let __adjBudget = budget.slice();
  if(__sfRemain>0 && __sfShort>0){
    const __extra = __sfShort / __sfRemain;
    for(let i=0;i<12;i++){
      if(real[i]==null && (+budget[i]||0)>0) __adjBudget[i] = (+budget[i]||0) + __extra;
    }
  }
  const __sfPct = __sfBudget>0 ? Math.round(__sfReal/__sfBudget*100) : null;
  const __sfPend = Math.max(0, __sfBudget - __sfReal);
  const __sfTotalsEl = document.getElementById('bud-totals');
  if(__sfTotalsEl){
    const fmtU = n=>Number(n||0).toLocaleString('es-AR');
    const pctCls = __sfPct==null?'color:#4b5563':__sfPct>=100?'color:#15803d':__sfPct>=85?'color:#ca8a04':'color:#b01e1e';
    __sfTotalsEl.innerHTML =
      '<span><b style="color:#111827">Año ' + bYear + '</b></span>'
      + '<span>Budget <b style="color:#111827">' + fmtU(__sfBudget) + '</b> u.</span>'
      + '<span>Real <b style="color:#111827">' + fmtU(__sfReal) + '</b> u.</span>'
      + '<span style="' + pctCls + '">Cumpl. <b>' + (__sfPct==null?'—':__sfPct+'%') + '</b></span>'
      + (__sfPend>0?'<span>Pendiente <b style="color:#b01e1e">' + fmtU(__sfPend) + '</b> u.</span>':'');
  }
  window.__sfBudgetTotals = {budget:__sfBudget, real:__sfReal, pct:__sfPct, pending:__sfPend, adjusted:__adjBudget};"""

NEW = """  // ── Redistribución trimestral: shortfall se redistribuye en los proximos 3 meses ──
  const __origBudgetArr = budget.slice();
  let __sfReal = 0, __sfBudget = 0, __sfShortPast = 0, __firstPending = -1;
  for(let i=0;i<12;i++){
    const b = +budget[i]||0, r = real[i];
    __sfBudget += b;
    if(r!=null){
      __sfReal += +r||0;
      if(b>0) __sfShortPast += Math.max(0, b - (+r||0));
    } else if(__firstPending<0 && b>0){
      __firstPending = i;
    }
  }
  // Targets de redistribucion: proximos 3 meses con budget desde firstPending
  const __sfTriIdx = [];
  if(__firstPending>=0){
    for(let i=__firstPending;i<12 && __sfTriIdx.length<3;i++){
      if((+budget[i]||0)>0) __sfTriIdx.push(i);
    }
  }
  let __adjBudget = budget.slice();
  let __sfExtra = 0;
  if(__sfTriIdx.length>0 && __sfShortPast>0){
    __sfExtra = __sfShortPast / __sfTriIdx.length;
    for(const i of __sfTriIdx){ __adjBudget[i] = (+budget[i]||0) + __sfExtra; }
  }
  const __sfPct = __sfBudget>0 ? Math.round(__sfReal/__sfBudget*100) : null;
  const __sfPend = Math.max(0, __sfBudget - __sfReal);
  const __sfTotalsEl = document.getElementById('bud-totals');
  const __sfMESES = (typeof MESES!=='undefined' && MESES.length===12) ? MESES : ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  if(__sfTotalsEl){
    const fmtU = n=>Number(n||0).toLocaleString('es-AR');
    const pctCls = __sfPct==null?'color:#4b5563':__sfPct>=100?'color:#15803d':__sfPct>=85?'color:#ca8a04':'color:#b01e1e';
    let __triHtml = '';
    if(__sfTriIdx.length>0 && __sfExtra>0){
      const i0 = __sfTriIdx[0];
      const nxtMes = __sfMESES[i0];
      const nxtNew = +__adjBudget[i0]||0;
      __triHtml = '<span style="color:#92400e">Próximo (' + nxtMes + '): <b>+' + fmtU(Math.round(__sfExtra)) + '</b> u. redistribuidas → target <b>' + fmtU(Math.round(nxtNew)) + '</b> u.</span>';
    }
    __sfTotalsEl.innerHTML =
      '<span><b style="color:#111827">Año ' + bYear + '</b></span>'
      + '<span>Budget <b style="color:#111827">' + fmtU(__sfBudget) + '</b> u.</span>'
      + '<span>Real <b style="color:#111827">' + fmtU(__sfReal) + '</b> u.</span>'
      + '<span style="' + pctCls + '">Cumpl. <b>' + (__sfPct==null?'—':__sfPct+'%') + '</b></span>'
      + (__sfPend>0?'<span>Pendiente <b style="color:#b01e1e">' + fmtU(__sfPend) + '</b> u.</span>':'')
      + __triHtml;
  }
  window.__sfBudgetTotals = {budget:__sfBudget, real:__sfReal, pct:__sfPct, pending:__sfPend, adjusted:__adjBudget, triExtra:__sfExtra, triIdx:__sfTriIdx};"""


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if 'Redistribución trimestral' in t:
        return 'SKIP already (trimestral)'
    if OLD not in t:
        return 'NO anchor (old block missing)'
    t = t.replace(OLD, NEW, 1)
    path.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
