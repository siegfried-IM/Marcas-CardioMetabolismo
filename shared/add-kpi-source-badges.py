#!/usr/bin/env python3
"""
shared/add-kpi-source-badges.py

Agrega un badge en la esquina superior-derecha de cada KPI tile
indicando la fuente de la data:
  - IQVIA   (cyan)   para IE, MS%, Unidades, Crecimiento
  - Recetas (violeta) para MS% Recetas
  - Vta Int (verde)  para Presupuesto

Inyecta:
1) CSS para .kpi-source y variantes de color
2) Helper JS function _kpiSrc(lbl) que devuelve el span apropiado
3) Modifica los template strings en renderKpis/renderBrandKpis para
   incluir ${_kpiSrc(x.lbl)} antes del .kpi-accent

Aplica a 7 lineas. Idempotente: si ya existe la helper, skip.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = ['cardio/index.html', 'ATB/index.html', 'OTC/index.html',
         'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
         'dermatologia/dermato_dashboard.html']

CSS_INJECT = """
/* KPI source badge (IQVIA / Recetas / Vta Int) */
.kpi { position: relative; }
.kpi-source {
  position: absolute; top: 8px; right: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 8px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase;
  padding: 2px 6px; border-radius: 3px;
  background: rgba(0,0,0,.06); color: #4b5563;
  white-space: nowrap;
}
.kpi-source.iq  { background: rgba(8,145,178,.12);  color: #0891b2; }
.kpi-source.rec { background: rgba(124,58,237,.12); color: #7c3aed; }
.kpi-source.vi  { background: rgba(22,163,74,.14);  color: #16a34a; }
"""

JS_HELPER = """
function _kpiSrc(lbl){
  if(!lbl) return '';
  if(lbl.indexOf('Recetas')!==-1) return '<span class="kpi-source rec">Recetas</span>';
  if(lbl.indexOf('Presupuesto')!==-1) return '<span class="kpi-source vi">Vta Int</span>';
  return '<span class="kpi-source iq">IQVIA</span>';
}
"""


def transform(text):
    n_changes = 0

    # 1) CSS: inyectar antes del </style> del primer <style> block
    if '.kpi-source' not in text:
        # Buscar primer </style>
        m = re.search(r'</style>', text)
        if m:
            text = text[:m.start()] + CSS_INJECT + text[m.start():]
            n_changes += 1

    # 2) JS helper: inyectar antes del primer renderKpis o renderBrandKpis
    if '_kpiSrc' not in text:
        # Buscar 'function renderKpis' o 'function renderBrandKpis'
        m = re.search(r'\nfunction (?:renderKpis|renderBrandKpis)', text)
        if m:
            text = text[:m.start()] + '\n' + JS_HELPER + text[m.start():]
            n_changes += 1

    # 3) Template: inyectar ${_kpiSrc(x.lbl)} despues del <div class="kpi"> y antes de <div class="kpi-accent"
    # Patron: `<div class="kpi"><div class="kpi-accent"`
    # Reemplazo: `<div class="kpi">${_kpiSrc(x.lbl)}<div class="kpi-accent"`
    pattern = re.compile(r'`<div class="kpi"><div class="kpi-accent"')
    new_text, n = pattern.subn(r'`<div class="kpi">${_kpiSrc(x.lbl)}<div class="kpi-accent"', text)
    if n > 0:
        text = new_text
        n_changes += n

    # 4) Template multilinea (mujer/SNC): el div esta en multiples lineas con
    # whitespace. Patron: `\n      <div class="kpi">\n        <div class="kpi-accent"
    # Inyectar ${_kpiSrc(x.lbl)} antes del kpi-accent inner
    pattern2 = re.compile(r'(<div class="kpi">)(\s*\n\s*<div class="kpi-accent")')
    new_text, n2 = pattern2.subn(r'\1${_kpiSrc(x.lbl)}\2', text)
    if n2 > 0:
        text = new_text
        n_changes += n2

    return text, n_changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for rel in LINES:
        p = REPO / rel
        if not p.is_file():
            print(f'  [{rel}] SKIP: no existe'); continue
        text = p.read_text(encoding='utf-8', errors='replace')
        new_text, n = transform(text)
        if n == 0:
            print(f'  [{rel}] SKIP: sin cambios (ya aplicado?)')
            continue
        if args.dry_run:
            print(f'  [{rel}] DRY: {n} cambios')
        else:
            p.write_text(new_text, encoding='utf-8', newline='')
            print(f'  [{rel}] OK: {n} cambios ({p.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
