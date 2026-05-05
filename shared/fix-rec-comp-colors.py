#!/usr/bin/env python3
"""
shared/fix-rec-comp-colors.py

Los competidores en el chart de Recetas usan COMP_COLORS = paleta de
grises (['#374151','#6b7280','#9ca3af','#d1d5db','#4b5563','#1f2937'])
que es casi invisible cuando se renderean como lineas dashed thin
encima de la linea SIE.

Fix: dentro de renderRec(), reemplazar `COMP_COLORS[i%...]` por una
paleta distinta y vibrante REC_COMP_COLORS (azul, verde, naranja,
violeta, cyan, rojo). Asi los competidores se distinguen entre si
y de la linea SIE (rojo/marca color).

Tambien:
- borderWidth 1.5 -> 2.2 (mas grueso, visible)
- pointRadius 2 -> 3

Aplica a 7 lineas. Tres puntos de cambio por archivo:
  1) view 'ms' competitor loop
  2) view 'quarterly' competitor loop
  3) view 'rec'/'med' competitor loop (si aplica)
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = ['cardio/index.html', 'ATB/index.html', 'OTC/index.html',
         'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
         'dermatologia/dermato_dashboard.html']

# Paleta distinta para competidores en chart de Recetas
NEW_PALETTE = "['#2563eb','#16a34a','#d97706','#7c3aed','#0891b2','#dc2626']"


def transform(text):
    n = 0

    # Inyectar la constante REC_COMP_COLORS antes de la primera ocurrencia de
    # COMP_COLORS en renderRec, si no esta ya definida.
    if 'REC_COMP_COLORS' not in text:
        # Buscar una ubicacion en script donde inyectar la constante. Antes
        # de function renderRec.
        m = re.search(r'\nfunction renderRec\(\)\{', text)
        if m:
            inject = "\nconst REC_COMP_COLORS = " + NEW_PALETTE + ";  // distintos para chart de recetas\n"
            text = text[:m.start()] + inject + text[m.start():]
            n += 1

    # Reemplazar `COMP_COLORS[i%COMP_COLORS.length]` por
    # `REC_COMP_COLORS[i%REC_COMP_COLORS.length]` SOLO dentro de renderRec().
    # Usar regex con ventana entre `function renderRec()` y la siguiente `function`.
    rr_match = re.search(r'(function renderRec\(\)\{.*?)(\nfunction \w+\(\))', text, re.DOTALL)
    if rr_match:
        body = rr_match.group(1)
        new_body = body.replace(
            'COMP_COLORS[i%COMP_COLORS.length]',
            'REC_COMP_COLORS[i%REC_COMP_COLORS.length]'
        )
        if new_body != body:
            n += body.count('COMP_COLORS[i%COMP_COLORS.length]') - new_body.count('COMP_COLORS[i%COMP_COLORS.length]')
            text = text.replace(body, new_body, 1)

    # Aumentar borderWidth de 1.5 a 2.2 SOLO en datasets de renderRec (lineas
    # de competidores). Pattern: borderColor:clr,backgroundColor:'transparent',
    # fill:false,tension:.3,pointRadius:2,borderWidth:1.5,borderDash:[4,3]
    pattern_bw = re.compile(
        r"(borderColor:clr,backgroundColor:'transparent',fill:false,tension:\.3,pointRadius:)2(,borderWidth:)1\.5"
    )
    new_text, k = pattern_bw.subn(r'\g<1>3\g<2>2.2', text)
    if k > 0:
        text = new_text
        n += k

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
            print(f'  [{rel}] SKIP (sin cambios)')
            continue
        if args.dry_run:
            print(f'  [{rel}] DRY: {n} cambios')
        else:
            p.write_text(new_text, encoding='utf-8', newline='')
            print(f'  [{rel}] OK: {n} cambios')
    return 0


if __name__ == '__main__':
    sys.exit(main())
