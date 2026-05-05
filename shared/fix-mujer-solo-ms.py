#!/usr/bin/env python3
"""
shared/fix-mujer-solo-ms.py

Fix puntual: la familia SOLO de mujer no tiene tracking en CloseUp
(productos SIDERBLUT/FER-IN-SOL son OTC, no aparecen en pivots de
recetas). Como resultado:
  - rec_ms[SOLO].sie estaba todo en 0
  - rec_ms[SOLO].ms estaba todo en 0
  - rec_comp[SOLO] tenia competidores mal asignados (de HIERROS ASOC.
    COMPLEX que no son SOLO realmente)
  - Grafico de MS% Recetas para SOLO aparece vacio.

Workaround: deriva los valores desde IQVIA Units (mol_perf[SOLO])
para que el grafico tenga data. Es un proxy: el grafico mostrara
share de UNIDADES IQVIA en lugar de share de recetas, pero al menos
el usuario ve resultados en lugar de 0% plano.

Pasos:
  1) Para cada SIE product en mol_perf[SOLO].products:
       sie_monthly[mk] += monthly_vals[mk]
  2) Para cada producto del family:
       fam_monthly[mk] += monthly_vals[mk]
  3) rec_ms[SOLO].sie[mk]  = sie_monthly[mk]
  4) rec_ms[SOLO].ms[mk]   = sie_monthly[mk] / fam_monthly[mk] * 100
  5) rec_ms[SOLO].ms_quarterly recomputado por trimestre
  6) rec_comp[SOLO] reconstruido desde mol_perf[SOLO].products
     (todos los products como entries con monthly = monthly_vals,
     is_sie matcheando, total=sum)

NO modifica nada mas.

Uso:
    py shared/fix-mujer-solo-ms.py [--dry-run]
"""

from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'mujer' / 'index.html'
FAMILY = 'SOLO'

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}


def quarter_key(mk):
    parts = mk.split()
    if len(parts) != 2: return ''
    m = MES_INV.get(parts[0])
    if not m: return ''
    return f'Q{(m-1)//3+1} {parts[1]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    text = HTML.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D = (\{)', text)
    if not m:
        print('ERROR: const D no encontrado', file=sys.stderr); return 2
    abs_start = m.start() + len('const D = ')
    abs_start = text.index('{', abs_start)
    D, end = json.JSONDecoder().raw_decode(text[abs_start:])
    abs_end = abs_start + end

    mol = D.get('mol_perf', {}).get(FAMILY)
    if not mol:
        print(f'ERROR: mol_perf[{FAMILY}] no existe'); return 3
    prods = mol.get('products', [])
    print(f'mol_perf[{FAMILY}]: {len(prods)} productos')

    # Build family monthly + sie monthly
    fam_monthly = defaultdict(int)
    sie_monthly = defaultdict(int)
    sie_count = 0
    for p in prods:
        mv = p.get('monthly_vals', {})
        is_sie = bool(p.get('is_sie'))
        if is_sie: sie_count += 1
        for mk, v in mv.items():
            try: vv = int(v or 0)
            except: vv = 0
            fam_monthly[mk] += vv
            if is_sie:
                sie_monthly[mk] += vv

    print(f'  SIE products: {sie_count}')
    print(f'  Months range: {len(fam_monthly)}')

    # Recomputar rec_ms[SOLO]
    sie_dict = {mk: int(v) for mk, v in sie_monthly.items()}
    ms_dict = {}
    for mk, fv in fam_monthly.items():
        sv = sie_monthly.get(mk, 0)
        ms_dict[mk] = round(sv / fv * 100, 2) if fv > 0 else 0

    # Quarterly
    sie_q = defaultdict(int)
    fam_q = defaultdict(int)
    for mk, sv in sie_monthly.items():
        qk = quarter_key(mk)
        if qk:
            sie_q[qk] += sv
            fam_q[qk] += fam_monthly.get(mk, 0)
    ms_q = {}
    for qk, fv in fam_q.items():
        sv = sie_q.get(qk, 0)
        ms_q[qk] = round(sv / fv * 100, 2) if fv > 0 else 0

    rec_ms = D.setdefault('rec_ms', {})
    rec_ms[FAMILY] = {
        'sie': sie_dict,
        'ms':  ms_dict,
        'ms_quarterly': dict(ms_q),
    }

    # Reconstruir rec_comp[SOLO] desde products
    rec_comp = D.setdefault('rec_comp', {})
    new_rc = {}
    for p in prods:
        prod_name = p.get('prod', '').strip()
        if not prod_name: continue
        mv = p.get('monthly_vals', {})
        monthly = {mk: int(v or 0) for mk, v in mv.items() if v}
        if not monthly: continue
        # Quarterly per brand
        b_q = defaultdict(int)
        for mk, v in monthly.items():
            qk = quarter_key(mk)
            if qk: b_q[qk] += v
        new_rc[prod_name] = {
            'is_sie': bool(p.get('is_sie')),
            'monthly':           monthly,
            'quarterly':         dict(b_q),
            'total':             sum(monthly.values()),
            'monthly_medicos':   {},
            'quarterly_medicos': {},
            'total_medicos':     0,
        }
    # Sort: SIE primero, luego por total desc
    new_rc = dict(sorted(new_rc.items(),
                         key=lambda kv: (not kv[1]['is_sie'], -kv[1]['total'])))
    rec_comp[FAMILY] = new_rc

    # Sample
    last_3 = sorted(sie_dict.items(), key=lambda x: (int(x[0].split()[1]),
                                                       MES_INV.get(x[0].split()[0],0)))[-3:]
    print(f'\nrec_ms[{FAMILY}].sie last 3: {last_3}')
    last_3_ms = sorted(ms_dict.items(), key=lambda x: (int(x[0].split()[1]),
                                                         MES_INV.get(x[0].split()[0],0)))[-3:]
    print(f'rec_ms[{FAMILY}].ms last 3:  {last_3_ms}')
    print(f'rec_comp[{FAMILY}] brands ({len(new_rc)}): {list(new_rc.keys())[:5]}'.encode('ascii','replace').decode())

    if args.dry_run:
        print('\nDRY RUN: no se escribio.')
        return 0

    new_text = text[:abs_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]
    HTML.write_text(new_text, encoding='utf-8', newline='')
    print(f'\n-> {HTML} reescrito ({HTML.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
