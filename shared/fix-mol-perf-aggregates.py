#!/usr/bin/env python3
"""
shared/fix-mol-perf-aggregates.py

Fix de un bug introducido por sync-mujer-pm.py y sync-snc-pm.py: los
campos `ytd` y `mat` de mol_perf usaban keys 'Dec YYYY' (totales
anuales) en lugar de 'MMM YYYY' donde MMM = mes de cierre. Los
dashboards mujer/SNC buscan ytd['Mar 2026'] y como no existe (solo
hay 'Dec 2026'), no muestran nada en YTD.

Este script recomputa ytd/mat (y ms_ytd/ms_mat) en mujer/index.html
y SNC/index.html con formato consistente con cardio/ATB/OTC/respi:

  ytd[<cierre_month> YYYY] = sum(Jan..<cierre_month>) de YYYY
  mat[<cierre_month> YYYY] = sum rolling 12 meses terminando en
                              <cierre_month> YYYY

NO toca monthly_vals, quarterly_vals, ni rec_*, stock, etc.
NO modifica cardio/ATB/OTC/respi (ya tienen formato correcto).

Uso:
    py shared/fix-mol-perf-aggregates.py [--dry-run]
"""

from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MES_EN = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
          7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
MES_INV = {v:k for k,v in MES_EN.items()}


def parse_mk(mk):
    parts = str(mk).split()
    if len(parts) != 2: return None
    m = MES_INV.get(parts[0])
    if not m: return None
    try: y = int(parts[1])
    except: return None
    return (y, m)


def latest_month_in_dict(d):
    if not d: return None
    parsed = [parse_mk(k) for k in d]
    parsed = [p for p in parsed if p]
    if not parsed: return None
    return max(parsed)


def latest_month_in_mol_perf(mol_perf):
    """Latest month_key across all products' monthly_vals."""
    cands = []
    for fam_obj in mol_perf.values():
        if not isinstance(fam_obj, dict): continue
        for p in fam_obj.get('products', []):
            mv = p.get('monthly_vals', {})
            for k in mv:
                pk = parse_mk(k)
                if pk: cands.append(pk)
    if not cands: return None
    return max(cands)


def recompute_aggregates(mol_perf, cierre):
    """cierre = (year, month_num). Recomputa ytd/mat/ms_ytd/ms_mat."""
    cy, cm = cierre

    def ytd_window(y):
        """Para año y, devuelve list de month_keys Jan..<cierre_month> de y."""
        return [f'{MES_EN[m]} {y}' for m in range(1, cm + 1)]

    def mat_window(y):
        """Para año y, MAT termina en <cierre_month> y. Empieza 11 meses
        antes. Devuelve list de 12 month_keys."""
        out = []
        for back in range(11, -1, -1):
            total_idx = (y * 12 + (cm - 1)) - back
            yy, mm = divmod(total_idx, 12)
            out.append(f'{MES_EN[mm + 1]} {yy}')
        return out

    def sum_window(monthly, window_keys):
        return sum(int(monthly.get(mk, 0) or 0) for mk in window_keys)

    for fam_key, fam_obj in mol_perf.items():
        if not isinstance(fam_obj, dict): continue
        prods = fam_obj.get('products', [])

        # Determinar años con data (de los monthly_vals de cualquier producto)
        years_with_data = set()
        for p in prods:
            for mk in p.get('monthly_vals', {}):
                pk = parse_mk(mk)
                if pk: years_with_data.add(pk[0])
        years_sorted = sorted(years_with_data)

        # Family-level monthly = suma de products
        fam_monthly = defaultdict(int)
        for p in prods:
            for mk, v in p.get('monthly_vals', {}).items():
                fam_monthly[mk] += int(v or 0)
        fam_monthly = dict(fam_monthly)

        # Recompute family ytd y mat con yearly keys
        new_fam_ytd = {}
        new_fam_mat = {}
        for y in years_sorted:
            ytd_v = sum_window(fam_monthly, ytd_window(y))
            mat_v = sum_window(fam_monthly, mat_window(y))
            new_fam_ytd[f'{MES_EN[cm]} {y}'] = ytd_v
            new_fam_mat[f'{MES_EN[cm]} {y}'] = mat_v
        fam_obj['ytd'] = new_fam_ytd
        fam_obj['mat'] = new_fam_mat

        # Recompute per-product ytd/mat/ms_ytd/ms_mat
        for p in prods:
            mv = p.get('monthly_vals', {})
            new_ytd = {}
            new_mat = {}
            new_ms_ytd = {}
            new_ms_mat = {}
            for y in years_sorted:
                key = f'{MES_EN[cm]} {y}'
                pv_ytd = sum_window(mv, ytd_window(y))
                pv_mat = sum_window(mv, mat_window(y))
                fv_ytd = new_fam_ytd[key]
                fv_mat = new_fam_mat[key]
                new_ytd[key] = pv_ytd
                new_mat[key] = pv_mat
                new_ms_ytd[key] = round(pv_ytd / fv_ytd * 100, 2) if fv_ytd > 0 else 0
                new_ms_mat[key] = round(pv_mat / fv_mat * 100, 2) if fv_mat > 0 else 0
            p['ytd'] = new_ytd
            p['mat'] = new_mat
            p['ms_ytd'] = new_ms_ytd
            p['ms_mat'] = new_ms_mat


def fix_inline(html_path):
    text = html_path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D = (\{)', text)
    if not m:
        print(f'  WARN: const D no encontrado en {html_path}'); return False
    abs_start = m.start() + len('const D = ')
    abs_start = text.index('{', abs_start)
    D, end = json.JSONDecoder().raw_decode(text[abs_start:])
    abs_end = abs_start + end

    mol_perf = D.get('mol_perf')
    if not mol_perf:
        print(f'  WARN: no mol_perf en {html_path}'); return False

    cierre = latest_month_in_mol_perf(mol_perf)
    if not cierre:
        print(f'  WARN: no se pudo determinar cierre en {html_path}'); return False

    print(f'  {html_path}: cierre = {MES_EN[cierre[1]]} {cierre[0]}')

    # Sample antes
    sample_fam = list(mol_perf.keys())[0]
    print(f'    antes -> mol[{sample_fam}].ytd keys: {list(mol_perf[sample_fam].get("ytd",{}).keys())}'.encode('ascii','replace').decode())

    recompute_aggregates(mol_perf, cierre)

    # Sample despues
    print(f'    despues -> mol[{sample_fam}].ytd: {mol_perf[sample_fam]["ytd"]}'.encode('ascii','replace').decode())
    print(f'    despues -> mol[{sample_fam}].mat: {mol_perf[sample_fam]["mat"]}'.encode('ascii','replace').decode())

    new_text = text[:abs_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]
    return new_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    targets = [REPO / 'mujer' / 'index.html', REPO / 'SNC' / 'index.html']
    for tp in targets:
        if not tp.is_file():
            print(f'SKIP {tp}: no existe'); continue
        print(f'Procesando: {tp}')
        new_text = fix_inline(tp)
        if new_text is False:
            continue
        if args.dry_run:
            print(f'  DRY: no se escribio.')
        else:
            tp.write_text(new_text, encoding='utf-8', newline='')
            print(f'  -> reescrito ({tp.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
