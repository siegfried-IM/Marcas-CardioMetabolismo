#!/usr/bin/env python3
"""
shared/fix-kpi-order.py

Reordena los KPIs de cada linea para que tanto LINEA como MARCA
queden en el mismo orden:
  1) IE
  2) MS% IQVIA
  3) Unidades
  4) Crecimiento
  5) Presupuesto
  6) MS% Recetas

Antes: LINEA tenia MS% Recetas en posicion 4 y Crecimiento/Presup
en 5/6, mientras que MARCA tenia MS% Recetas al final. Confuso al
comparar.

Aplica a las 7 lineas via regex. Solo toca el orden de los 3
ultimos items en el array `items` de renderKpis (line-level).
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = ['cardio/index.html', 'ATB/index.html', 'OTC/index.html',
         'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
         'dermatologia/dermato_dashboard.html']


def reorder_in_text(text):
    """Busca 3 lines consecutivas: MS% Recetas, Crecimiento, Presupuesto.
    Las reordena a: Crecimiento, Presupuesto, MS% Recetas."""

    # Patron para los 3 items del array (cada uno empieza con `    {lbl:`)
    # MS% Recetas item suele tener `MS% Recetas` en lbl
    # Crecimiento item tiene `Crecimiento Línea` (cardio/ATB/OTC/respi/dermato/mujer/SNC)
    # Presupuesto tiene `Presupuesto · `

    # Capturar 3 items consecutivos (pueden ser multilinea para mujer/SNC)
    # Cada item es {lbl:...,...} terminando en `},`

    # Estrategia simple: para cardio/ATB/OTC/respi/dermato (items en 1 linea c/u):
    # encontrar 3 lineas consecutivas y reordenar
    pattern_oneline = re.compile(
        r'(\s+\{lbl:`MS% Recetas[^\n]+\},)\n'
        r'(\s+\{lbl:`Crecimiento[^\n]+\},)\n'
        r'(\s+\{lbl:`Presupuesto[^\n]+\},)',
        re.MULTILINE
    )
    new_text, n = pattern_oneline.subn(r'\2\n\3\n\1', text)
    if n > 0:
        return new_text, 'oneline', n

    # Estrategia para mujer/SNC: items multilinea
    # Cada item es un bloque {  ... },\n
    # Cada bloque empieza con `    {\n      lbl:...` y termina con `    },\n`
    pattern_multi = re.compile(
        r'(    \{\n      lbl:.MS% Recetas.*?\n    \},)\n'
        r'(    \{\n      lbl:`Crecimiento.*?\n    \},)\n'
        r'(    \{\n      lbl:`Presupuesto.*?\n    \},)',
        re.DOTALL
    )
    new_text, n = pattern_multi.subn(r'\2\n\3\n\1', text)
    if n > 0:
        return new_text, 'multi', n

    return text, 'no-match', 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for rel in LINES:
        p = REPO / rel
        if not p.is_file():
            print(f'  [{rel}] SKIP: no existe'); continue
        text = p.read_text(encoding='utf-8', errors='replace')
        new_text, kind, n = reorder_in_text(text)
        if n == 0:
            print(f'  [{rel}] WARN: no match (kind={kind})')
            continue
        if args.dry_run:
            print(f'  [{rel}] DRY: matched {kind} (n={n})')
        else:
            p.write_text(new_text, encoding='utf-8', newline='')
            print(f'  [{rel}] OK ({kind}, n={n})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
