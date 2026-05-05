#!/usr/bin/env python3
"""
shared/fix-mol-perf-mat-monthly.py

Fix de regression: el commit 9b7ecf1 simplifico ytd/mat de mujer y
SNC mol_perf a solo entries yearly ('Mar 2024', 'Mar 2025'...). Esto
rompio el chart de Mercado IQVIA en SNC que esperaba mat keys
MENSUALES (rolling 12 ending cada mes: 'Mar 2022', 'Apr 2022', ...,
'Mar 2026').

Este script recomputa mat y ms_mat con keys MENSUALES (rolling 12)
desde monthly_vals, manteniendo ademas las entries yearly que
queremos preservar (ya estan ahi pero no estorban — el chart filtra
por las que necesita).

NO toca ytd / ms_ytd (ya estan correctos en formato yearly).
NO toca monthly_vals / quarterly_vals / ms_monthly / ms_quarterly.

Aplica a mujer/index.html y SNC/index.html.

Uso:
    py shared/fix-mol-perf-mat-monthly.py [--dry-run]
"""

from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MES_EN = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
          7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
MES_INV = {v:k for k,v in MES_EN.items()}


def msort(mk):
    p = mk.split()
    if len(p) != 2: return 0
    return int(p[1]) * 100 + MES_INV.get(p[0], 0)


def parse_mk(mk):
    parts = str(mk).split()
    if len(parts) != 2: return None
    m = MES_INV.get(parts[0])
    if not m: return None
    try: y = int(parts[1])
    except: return None
    return (y, m)


def fix_mol_perf(D):
    mol_perf = D.get('mol_perf', {})
    if not mol_perf: return False

    n_products = 0
    for fam_key, fam_obj in mol_perf.items():
        if not isinstance(fam_obj, dict): continue
        prods = fam_obj.get('products', [])

        # 1) Recompute family-level monthly + mat rolling
        fam_monthly = defaultdict(int)
        for p in prods:
            for mk, v in p.get('monthly_vals', {}).items():
                fam_monthly[mk] += int(v or 0)
        fam_monthly = dict(fam_monthly)
        sorted_mks = sorted(fam_monthly.keys(), key=msort)

        # Rolling 12-month MAT ending at each month
        def rolling_mat(monthly_dict):
            sorted_keys = sorted(monthly_dict.keys(), key=msort)
            out = {}
            for i, mk in enumerate(sorted_keys):
                if i < 11: continue
                window = sorted_keys[i-11:i+1]
                out[mk] = sum(int(monthly_dict.get(m, 0) or 0) for m in window)
            return out

        fam_mat_monthly = rolling_mat(fam_monthly)

        # Merge monthly mat keys con yearly que ya existen (preserva ambos)
        existing_mat = fam_obj.get('mat', {})
        merged_mat = dict(existing_mat)
        merged_mat.update(fam_mat_monthly)
        fam_obj['mat'] = merged_mat

        # 2) Per-product
        for p in prods:
            mv = p.get('monthly_vals', {})
            p_mat_monthly = rolling_mat(mv)

            existing_p_mat = p.get('mat', {})
            merged_p_mat = dict(existing_p_mat)
            merged_p_mat.update(p_mat_monthly)
            p['mat'] = merged_p_mat

            # ms_mat por mes vs family mat
            existing_ms_mat = p.get('ms_mat', {})
            merged_ms_mat = dict(existing_ms_mat)
            for mk, pv in p_mat_monthly.items():
                fv = fam_mat_monthly.get(mk, 0)
                merged_ms_mat[mk] = round(pv / fv * 100, 2) if fv > 0 else 0
            p['ms_mat'] = merged_ms_mat

            n_products += 1

    return n_products


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    targets = [REPO / 'mujer' / 'index.html', REPO / 'SNC' / 'index.html']
    for tp in targets:
        if not tp.is_file():
            print(f'SKIP {tp}: no existe'); continue
        text = tp.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'const D = (\{)', text)
        if not m:
            print(f'SKIP {tp}: const D no encontrado'); continue
        abs_start = m.start() + len('const D = ')
        abs_start = text.index('{', abs_start)
        D, end = json.JSONDecoder().raw_decode(text[abs_start:])
        abs_end = abs_start + end

        n = fix_mol_perf(D)
        print(f'  {tp}: {n} productos updated')

        # Sample
        fam_key = list(D['mol_perf'].keys())[0]
        fam = D['mol_perf'][fam_key]
        n_mat = len(fam.get('mat', {}))
        sample_prod = fam['products'][0]
        n_pmat = len(sample_prod.get('mat', {}))
        n_pmsmat = len(sample_prod.get('ms_mat', {}))
        sp_name = sample_prod.get('prod', '?')
        print(f'    sample fam[{fam_key}].mat keys: {n_mat}')
        print(f'    sample prod[{sp_name}].mat keys: {n_pmat}')
        print(f'    sample prod[{sp_name}].ms_mat keys: {n_pmsmat}')

        if args.dry_run:
            print(f'    DRY: no se escribio.')
        else:
            new_text = text[:abs_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]
            tp.write_text(new_text, encoding='utf-8', newline='')
            print(f'    -> reescrito ({tp.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
