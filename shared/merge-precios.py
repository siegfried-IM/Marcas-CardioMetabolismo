#!/usr/bin/env python3
"""
shared/merge-precios.py

Mergea actualizacion de precios desde el dump del Manual Farmaceutico
(formato Excel con columnas: Producto, Presentacion, Droga, Laboratorio,
PVP al <fecha_prev>, PVP al <fecha_curr>, % Var, Fecha Vigencia).

Para cada linea (cardio/ATB/OTC/respi) actualiza in-place:
  - precios[F][molecule|atc][pres][i].pvp_dic25  (slot "previo")
  - precios[F][molecule|atc][pres][i].pvp_feb26  (slot "actual")
  - precios[F][molecule|atc][pres][i].var
  - meta.price_prev_label = "PVP al <fecha_prev>"
  - meta.price_curr_label = "PVP al <fecha_curr>"

Match por (producto, presentacion). Lab solo informativo si hace falta
desempatar. Productos no encontrados en el archivo conservan los precios
viejos sin tocar.

NO toca recetas, mol_perf, budget, stock, convenios, canales, etc.
NO toca SNC ni mujer (estructuras distintas).

Uso:
    py shared/merge-precios.py --pricefile "<archivo.xlsx>"
"""

from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import openpyxl

LINES_DEFAULT = ['cardio', 'ATB', 'OTC', 'respiratorio']


def normalize_text(s):
    if s is None: return ''
    return re.sub(r'\s+', ' ', str(s).upper().strip())


def normalize_pres(s):
    """Normaliza presentacion: minuscula, espacios colapsados, sin acentos comunes."""
    if s is None: return ''
    s = str(s).strip().lower()
    # Colapsa whitespace
    s = re.sub(r'\s+', ' ', s)
    # Quita acentos comunes (caps. cáps. cps. → mismo)
    s = s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    return s


def parse_pricefile(path):
    """Devuelve:
       (lookup, prev_label, curr_label)
       lookup = { (prod_norm, pres_norm) : (pvp_prev, pvp_curr, var) }
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    headers = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
    # Find the two PVP columns and var
    col_prev = col_curr = col_var = None
    label_prev = label_curr = None
    for i, h in enumerate(headers):
        s = str(h or '').strip()
        if not s.startswith('PVP'): continue
        if col_prev is None:
            col_prev = i; label_prev = s
        else:
            col_curr = i; label_curr = s
    if col_prev is None or col_curr is None:
        raise ValueError(f'No encontre 2 columnas PVP en headers: {headers}')
    for i, h in enumerate(headers):
        if str(h or '').lower().startswith('% var') or str(h or '').lower() == 'var':
            col_var = i; break

    # Find col indexes for Producto / Presentacion / Laboratorio
    col_prod = col_pres = col_lab = None
    for i, h in enumerate(headers):
        s = str(h or '').strip().lower()
        if s == 'producto': col_prod = i
        elif s == 'presentacion' or s == 'presentación': col_pres = i
        elif s == 'laboratorio': col_lab = i

    if col_prod is None or col_pres is None:
        raise ValueError(f'Faltan cols Producto/Presentacion. Headers: {headers}')

    lookup = {}
    n_total = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) <= max(col_prev, col_curr): continue
        prod = row[col_prod]
        pres = row[col_pres]
        if not prod or not pres: continue
        try: pvp_prev = float(row[col_prev]) if row[col_prev] is not None else None
        except: pvp_prev = None
        try: pvp_curr = float(row[col_curr]) if row[col_curr] is not None else None
        except: pvp_curr = None
        if pvp_curr is None: continue
        try: var = float(row[col_var]) if col_var is not None and row[col_var] is not None else None
        except: var = None
        if var is None and pvp_prev:
            var = (pvp_curr - pvp_prev) / pvp_prev
        key = (normalize_text(prod), normalize_pres(pres))
        lookup[key] = (pvp_prev, pvp_curr, var)
        n_total += 1

    wb.close()
    return lookup, label_prev, label_curr, n_total


def parse_data_js(text):
    m1 = re.search(r'window\.OTC_DATA\s*=\s*', text)
    if not m1: raise ValueError('OTC_DATA not found')
    obj_start1 = text.index('{', m1.end())
    d1, end1 = json.JSONDecoder().raw_decode(text[obj_start1:])
    abs_end1 = obj_start1 + end1
    m2 = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text[abs_end1:])
    if not m2:
        return d1, None
    obj_start2 = abs_end1 + text[abs_end1:].index('{', m2.end())
    d2, _ = json.JSONDecoder().raw_decode(text[obj_start2:])
    return d1, d2


def serialize_data_js(text_orig, d1, d2):
    m1 = re.search(r'window\.OTC_DATA\s*=\s*', text_orig)
    obj_start1 = text_orig.index('{', m1.end())
    _, end1 = json.JSONDecoder().raw_decode(text_orig[obj_start1:])
    abs_end1 = obj_start1 + end1
    prefix1 = text_orig[:obj_start1]
    if d2 is None:
        return prefix1 + json.dumps(d1, ensure_ascii=False) + text_orig[abs_end1:]
    m2 = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text_orig[abs_end1:])
    obj_start2 = abs_end1 + text_orig[abs_end1:].index('{', m2.end())
    _, end2 = json.JSONDecoder().raw_decode(text_orig[obj_start2:])
    abs_end2 = obj_start2 + end2
    middle = text_orig[abs_end1:obj_start2]
    suffix = text_orig[abs_end2:]
    return prefix1 + json.dumps(d1, ensure_ascii=False) + middle + json.dumps(d2, ensure_ascii=False) + suffix


def update_entry(entry, lookup, pres_key):
    """Actualiza un entry de producto si lo encuentra en el lookup. Devuelve True si matched."""
    prod = entry.get('prod', '')
    if not prod: return False
    key = (normalize_text(prod), normalize_pres(pres_key))
    if key not in lookup:
        return False
    pvp_prev, pvp_curr, var = lookup[key]
    if pvp_prev is not None:
        entry['pvp_dic25'] = pvp_prev
    entry['pvp_feb26'] = pvp_curr
    if var is not None:
        entry['var'] = var
    return True


def merge_line(data_js_path, lookup, label_prev, label_curr, dry_run=False):
    text = data_js_path.read_text(encoding='utf-8-sig', errors='replace')
    d1, d2 = parse_data_js(text)
    if d2 is None:
        return {'skipped': 'no OTC_DASHBOARD'}
    precios = d2.get('precios')
    if not isinstance(precios, dict):
        return {'skipped': 'no precios'}

    matched = 0
    not_matched = 0
    samples_unmatched = []

    for fam, fam_obj in precios.items():
        if not isinstance(fam_obj, dict): continue
        # Two patterns: (a) precios[F][molecule|atc][pres][i] (cardio/ATB/respi)
        #               (b) precios[F][pres][i]              (OTC)
        # Detect: if any subkey value is dict -> pattern (a); if list -> pattern (b)
        keys = list(fam_obj.keys())
        if not keys: continue
        first_val = fam_obj[keys[0]]

        if isinstance(first_val, dict):
            # pattern (a): two views (molecule, atc) — actualizamos AMBAS porque suelen
            # tener referencias al MISMO objeto entry; json.dumps deduplica? No,
            # son objetos separados pero el frontend los lee en paralelo.
            for view_key in keys:  # ['molecule', 'atc']
                view = fam_obj[view_key]
                if not isinstance(view, dict): continue
                for pres_key, items in view.items():
                    if not isinstance(items, list): continue
                    for entry in items:
                        if not isinstance(entry, dict): continue
                        if update_entry(entry, lookup, pres_key):
                            matched += 1
                        else:
                            not_matched += 1
                            if len(samples_unmatched) < 3:
                                samples_unmatched.append(f"{entry.get('prod')} | {pres_key}")
        elif isinstance(first_val, list):
            # pattern (b)
            for pres_key, items in fam_obj.items():
                if not isinstance(items, list): continue
                for entry in items:
                    if not isinstance(entry, dict): continue
                    if update_entry(entry, lookup, pres_key):
                        matched += 1
                    else:
                        not_matched += 1
                        if len(samples_unmatched) < 3:
                            samples_unmatched.append(f"{entry.get('prod')} | {pres_key}")

    # Update meta labels
    d2.setdefault('meta', {})['price_prev_label'] = label_prev
    d2.setdefault('meta', {})['price_curr_label'] = label_curr

    if not dry_run:
        new_text = serialize_data_js(text, d1, d2)
        data_js_path.write_text(new_text, encoding='utf-8', newline='')

    return {'matched': matched, 'not_matched': not_matched, 'samples_unmatched': samples_unmatched}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pricefile', required=True)
    ap.add_argument('--repo', default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument('--lines', nargs='+', default=LINES_DEFAULT)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    pf = Path(args.pricefile)
    if not pf.is_file():
        print(f'ERROR: archivo no existe: {pf}', file=sys.stderr); return 2

    print(f'Leyendo: {pf}')
    lookup, label_prev, label_curr, n_total = parse_pricefile(pf)
    print(f'  Filas con precio: {n_total}')
    print(f'  Productos unicos (prod, presentacion): {len(lookup)}')
    print(f'  Label previo:  {label_prev}')
    print(f'  Label actual:  {label_curr}')

    repo = Path(args.repo)
    print(f'\nMergeando precios en {len(args.lines)} lineas...')
    for line in args.lines:
        data_js = repo / line / 'data.js'
        if not data_js.is_file():
            print(f'  [{line}] SKIP: no data.js')
            continue
        try:
            res = merge_line(data_js, lookup, label_prev, label_curr, dry_run=args.dry_run)
        except Exception as e:
            print(f'  [{line}] ERROR: {e}'); continue
        if 'skipped' in res:
            print(f'  [{line}] SKIP: {res["skipped"]}'); continue
        m, nm = res['matched'], res['not_matched']
        total = m + nm
        pct = round(m * 100 / total, 1) if total else 0
        print(f'  [{line}] OK: {m}/{total} entries actualizados ({pct}%), {nm} sin match')
        for s in res['samples_unmatched']:
            print(f'    sample no-match: {s}')

    if args.dry_run:
        print('\nDRY RUN: nada se escribio.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
