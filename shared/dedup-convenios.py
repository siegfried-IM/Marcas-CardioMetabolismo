#!/usr/bin/env python3
"""
shared/dedup-convenios.py

Las top OS en convenios traen duplicados por OS aparecida dos veces
con identificadores distintos:
  OSDE (9124) | 1379
  OSDE NACIONAL | FMLK | 1123
  OSEP - O.S. Prov. de Mendoza (9244) | 1020
  OSEP - O.S. Prov. Mendoza | FMLK | 1020
  ...

Dedupe: agrupar por canonical name (extracto del prefijo, ej. OSDE,
OSEP, IOSFA, SWISS MEDICAL, OBSBA) y mantener solo la entry con
MAX unid del grupo. El nombre que se muestra es el del original
(no FMLK preferentemente).

Aplica a las 7 lineas (cardio/ATB/OTC/respi/mujer/SNC/dermato) y a
TODAS las familias dentro de convenios.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('data.js',  'cardio/data.js'),
    ('data.js',  'ATB/data.js'),
    ('data.js',  'OTC/data.js'),
    ('data.js',  'respiratorio/data.js'),
    ('inline',   'mujer/index.html'),
    ('inline',   'SNC/index.html'),
    ('inline',   'dermatologia/dermato_dashboard.html'),
]


def canonical_os(name):
    """Extrae la sigla canonica de la OS para agrupar duplicados.
    'OSDE (9124)' -> 'OSDE'
    'OSDE NACIONAL | FMLK' -> 'OSDE'
    'OSEP - O.S. Prov. de Mendoza (9244)' -> 'OSEP'
    'IOSFA - CF | P . 10410' -> 'IOSFA'
    'SWISS MEDICAL GROUP (9195)' -> 'SWISS MEDICAL'
    'OBSBA - O.S. Ciudad ...' -> 'OBSBA'
    """
    s = str(name).strip().upper()
    # Quitar todo despues de '|' o '(' o '-'
    s = re.split(r'[|(\-]', s)[0].strip()
    # Quitar palabras genericas finales
    s = re.sub(r'\s+(O\.?S\.?|NACIONAL|GROUP|CF|PH|FMLK)\.?$', '', s)
    return s.strip() or str(name)


def is_fmlk(name):
    return 'FMLK' in str(name).upper()


def dedup_list(entries):
    """Dedupe lista de entries de convenios."""
    if not entries: return entries
    # Group por canonical
    groups = defaultdict(list)
    for e in entries:
        groups[canonical_os(e.get('os', ''))].append(e)
    # Para cada group, mantener el entry con max unid; si empate, preferir
    # el que NO tenga FMLK
    out = []
    for canon, items in groups.items():
        if len(items) == 1:
            out.append(items[0])
            continue
        # Sort: por unid desc, luego por is_fmlk asc (no-FMLK primero)
        items.sort(key=lambda e: (-(e.get('unid', 0) or 0), is_fmlk(e.get('os',''))))
        out.append(items[0])
    # Re-sort por unid desc
    out.sort(key=lambda e: -(e.get('unid', 0) or 0))
    # Recomputar % del total si existe campo
    total = sum((e.get('unid', 0) or 0) for e in out)
    if total > 0:
        for e in out:
            if 'pct' in e:
                e['pct'] = round((e.get('unid', 0) or 0) / total * 100, 1)
    return out


def process_data(D):
    """Aplica dedup a D.convenios. Devuelve count de cambios."""
    conv = D.get('convenios', {})
    n_dedup = 0
    n_orig_total = 0
    n_new_total = 0
    for fam, entries in conv.items():
        if not isinstance(entries, list): continue
        before = len(entries)
        new_entries = dedup_list(entries)
        if len(new_entries) < before:
            conv[fam] = new_entries
            n_dedup += (before - len(new_entries))
        n_orig_total += before
        n_new_total += len(conv[fam])
    return n_dedup, n_orig_total, n_new_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for kind, rel in LINES:
        p = REPO / rel
        if not p.is_file():
            print(f'  [{rel}] SKIP'); continue
        text = p.read_text(encoding='utf-8-sig' if kind == 'data.js' else 'utf-8', errors='replace')
        if kind == 'data.js':
            m = re.search(r'window\.OTC_DASHBOARD\s*=\s*\{', text)
            if not m:
                print(f'  [{rel}] SKIP: no OTC_DASHBOARD'); continue
            obj_start = text.index('{', m.end() - 1)
            D, end = json.JSONDecoder().raw_decode(text[obj_start:])
            abs_end = obj_start + end
            n_dedup, n_orig, n_new = process_data(D)
            new_data = json.dumps(D, ensure_ascii=False)
            # Reconstruir texto (preservando OTC_DATA antes y resto despues)
            new_text = text[:obj_start] + new_data + text[abs_end:]
        else:
            m = re.search(r'const D = (\{)', text)
            if not m:
                print(f'  [{rel}] SKIP: no const D'); continue
            obj_start = m.start() + len('const D = ')
            obj_start = text.index('{', obj_start)
            D, end = json.JSONDecoder().raw_decode(text[obj_start:])
            abs_end = obj_start + end
            n_dedup, n_orig, n_new = process_data(D)
            new_text = text[:obj_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]

        if n_dedup == 0:
            print(f'  [{rel}] sin duplicados ({n_orig} entries)')
            continue
        if args.dry_run:
            print(f'  [{rel}] DRY: {n_dedup} duplicados detectados ({n_orig} -> {n_new} entries)')
        else:
            p.write_text(new_text, encoding='utf-8', newline='')
            print(f'  [{rel}] OK: {n_dedup} duplicados removidos ({n_orig} -> {n_new} entries)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
