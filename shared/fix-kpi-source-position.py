#!/usr/bin/env python3
"""
shared/fix-kpi-source-position.py

El badge de fuente (IQVIA/Recetas/Vta Int) en posicion absolute
top-right hacia overlap feo con labels largos que wrappean.

Fix:
1) Cambiar CSS: chip inline-block (no absolute), pequeño, alineado
   antes del label (no superpuesto).
2) Cambiar template: el span va INMEDIATAMENTE antes del kpi-lbl,
   no entre el accent y el lbl en posicion absoluta.

Visual final: chip pequeñito arriba del label como prefijo,
ej. '[IQVIA]  IE LÍNEA · YTD MAR 2026'.

Aplica a las 7 lineas.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = ['cardio/index.html', 'ATB/index.html', 'OTC/index.html',
         'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
         'dermatologia/dermato_dashboard.html']

OLD_CSS = """
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

NEW_CSS = """
/* KPI source chip (inline, antes del label) */
.kpi-source {
  display: inline-block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 8px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase;
  padding: 2px 6px; border-radius: 3px;
  background: rgba(0,0,0,.06); color: #4b5563;
  white-space: nowrap;
  margin-bottom: 4px;
}
.kpi-source.iq  { background: rgba(8,145,178,.12);  color: #0891b2; }
.kpi-source.rec { background: rgba(124,58,237,.12); color: #7c3aed; }
.kpi-source.vi  { background: rgba(22,163,74,.14);  color: #16a34a; }
"""


def transform(text):
    n = 0

    # 1) Reemplazar el bloque CSS viejo por el nuevo
    if OLD_CSS in text:
        text = text.replace(OLD_CSS, NEW_CSS)
        n += 1

    # 2) Cambiar el orden en el template: ${_kpiSrc(x.lbl)} debe ir
    # ANTES del <p class="kpi-lbl"> y DESPUES del <div class="kpi-accent">
    # Patron actual: `<div class="kpi">${_kpiSrc(x.lbl)}<div class="kpi-accent" ...></div><p class="kpi-lbl">${x.lbl}</p>`
    # Nuevo:        `<div class="kpi"><div class="kpi-accent" ...></div>${_kpiSrc(x.lbl)}<p class="kpi-lbl">${x.lbl}</p>`
    pattern = re.compile(r'<div class="kpi">\$\{_kpiSrc\(x\.lbl\)\}(<div class="kpi-accent"[^<]*</div>)(<p class="kpi-lbl">)')
    new_text, k = pattern.subn(r'<div class="kpi">\1${_kpiSrc(x.lbl)}\2', text)
    if k > 0:
        text = new_text
        n += k

    # 3) Mismo cambio para template multilinea (mujer/SNC)
    pattern2 = re.compile(r'(<div class="kpi">)\$\{_kpiSrc\(x\.lbl\)\}(\s*\n\s*<div class="kpi-accent"[^<]*</div>)')
    new_text, k2 = pattern2.subn(r'\1\2${_kpiSrc(x.lbl)}', text)
    if k2 > 0:
        text = new_text
        n += k2

    return text, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for rel in LINES:
        p = REPO / rel
        if not p.is_file():
            print(f'  [{rel}] SKIP'); continue
        text = p.read_text(encoding='utf-8', errors='replace')
        new_text, n = transform(text)
        if n == 0:
            print(f'  [{rel}] SKIP: sin cambios')
            continue
        if args.dry_run:
            print(f'  [{rel}] DRY: {n} cambios')
        else:
            p.write_text(new_text, encoding='utf-8', newline='')
            print(f'  [{rel}] OK: {n} cambios')
    return 0


if __name__ == '__main__':
    sys.exit(main())
