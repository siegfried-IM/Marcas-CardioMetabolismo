"""shared/inject-budget-redistribute.py

Inyecta en cada dashboard (cardio/ATB/OTC/respi/mujer/SNC/dermato) dos cosas
dentro de la sección 'Venta Interna vs Presupuesto':

1) Un strip con Totales del año: Budget · Real · Cumpl% · Pendiente
2) Redistribución: el shortfall acumulado de meses con real < budget se reparte
   en los meses futuros sin real, respetando el total anual.

Idempotente: si detecta __sfBudgetTotals, no re-aplica.
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

ANCHOR_HTML = '<div class="pill-group" id="bud-pills"></div>'
HTML_INJECT = ('<div class="pill-group" id="bud-pills"></div>'
               '<div id="bud-totals" style="margin-left:16px;display:flex;gap:14px;'
               'flex-wrap:wrap;font-family:IBM Plex Mono,monospace;font-size:11px;'
               'color:#4b5563;align-items:center;"></div>')

JS_INJECT = r"""// ── Redistribución mensual: shortfall acumulado se redistribuye a meses futuros ──
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
  window.__sfBudgetTotals = {budget:__sfBudget, real:__sfReal, pct:__sfPct, pending:__sfPend, adjusted:__adjBudget};
  """

ANCHOR_JS = 'const isIQVIADerived'

CHART_PATTERN = re.compile(r"(\{label:'Budget',data:)budget(,)")


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if '__sfBudgetTotals' in t:
        return 'SKIP already'
    if ANCHOR_HTML not in t:
        return 'NO anchor pill-group'
    if ANCHOR_JS not in t:
        return 'NO anchor isIQVIADerived'
    t = t.replace(ANCHOR_HTML, HTML_INJECT, 1)
    t = t.replace(ANCHOR_JS, JS_INJECT + ANCHOR_JS, 1)
    t2, n = CHART_PATTERN.subn(r"\1__adjBudget\2", t, count=1)
    if n == 0:
        return 'NO chart data:budget pattern'
    path.write_text(t2, encoding='utf-8', newline='')
    return 'OK'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
