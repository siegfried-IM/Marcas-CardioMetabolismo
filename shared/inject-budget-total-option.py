"""Agrega opcion 'TOTAL LÍNEA' al selector de Venta Interna vs Presupuesto.
Cuando se selecciona, el chart muestra la suma de budget/real de TODAS las
familias SIE para el año activo. Aplica a las 7 lineas. Idempotente."""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

OLD_PILLS = """function renderBudPills(){
  document.getElementById('bud-pills').innerHTML = BUD_PRODS.map(p=>`
    <button class="pill ${p===bProd?'on':''}" onclick="setBP('${p}')"
      style="${p===bProd?`color:${COLORS[p]||'#38bdf8'};border-color:${COLORS[p]||'#38bdf8'}`:''}">
      <span class="dot" style="background:${COLORS[p]||'#555'}"></span>${p}
    </button>`).join('');
}"""

NEW_PILLS = """function renderBudPills(){
  const totalPill = `<button class="pill ${'__TOTAL__'===bProd?'on':''}" onclick="setBP('__TOTAL__')"
      style="${'__TOTAL__'===bProd?'color:#111827;border-color:#111827;font-weight:700;':'font-weight:700;'}">
      <span class="dot" style="background:#111827"></span>TOTAL LÍNEA
    </button>`;
  document.getElementById('bud-pills').innerHTML = totalPill + BUD_PRODS.map(p=>`
    <button class="pill ${p===bProd?'on':''}" onclick="setBP('${p}')"
      style="${p===bProd?`color:${COLORS[p]||'#38bdf8'};border-color:${COLORS[p]||'#38bdf8'}`:''}">
      <span class="dot" style="background:${COLORS[p]||'#555'}"></span>${p}
    </button>`).join('');
}"""

OLD_RB_START = """function renderBudget(){
  const src = D.budget[bProd]?.[bYear]||{};
  const budget = src.budget||[];
  let real   = src.real||[];"""

NEW_RB_START = """function renderBudget(){
  // TOTAL LINEA: aggregate across all families
  let src, budget, real;
  if(bProd==='__TOTAL__'){
    budget = new Array(12).fill(0);
    real = new Array(12).fill(null);
    let hasReal = new Array(12).fill(false);
    Object.keys(D.budget||{}).forEach(fam=>{
      const fy = (D.budget[fam]||{})[bYear];
      if(!fy) return;
      const fb = fy.budget||[];
      const fr = fy.real||[];
      for(let i=0;i<12;i++){
        budget[i] += (+fb[i]||0);
        const v = fr[i];
        if(v!=null){
          if(real[i]==null) real[i] = 0;
          real[i] += (+v||0);
          hasReal[i] = true;
        }
      }
    });
    // Cleanup: if no fam had real for that month, keep null
    for(let i=0;i<12;i++){ if(!hasReal[i]) real[i] = null; }
    src = { budget, real };
  } else {
    src = D.budget[bProd]?.[bYear]||{};
    budget = src.budget||[];
    real   = src.real||[];
  }"""


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    if "'__TOTAL__'" in t or "TOTAL LÍNEA" in t or "TOTAL LINEA" in t:
        return 'SKIP already'
    changes = []
    if OLD_PILLS in t:
        t = t.replace(OLD_PILLS, NEW_PILLS, 1)
        changes.append('pills')
    if OLD_RB_START in t:
        t = t.replace(OLD_RB_START, NEW_RB_START, 1)
        changes.append('renderBudget')
    if not changes:
        return 'NO match'
    path.write_text(t, encoding='utf-8', newline='')
    return f'OK [{", ".join(changes)}]'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file(): print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
