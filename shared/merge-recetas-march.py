#!/usr/bin/env python3
"""
shared/merge-recetas-march.py

Merge ad-hoc para agregar UN mes de recetas (sin re-correr build-data.ps1)
a partir del pivot de CloseUp.

Input: el pivot Excel "Sin titulo - Tabla dinamica - <fecha>.xlsx"
       con columnas [Mercado, Droga, Marca, <fecha>] y valores de recetas.

Output: cada <linea>/data.js modificado in-place agregando el mes nuevo en:
  - OTC_DATA.prescriptions.months -> append "<MMM-YYYY>"
  - OTC_DATA.prescriptions.families[F].prescriptions -> append family total
  - OTC_DATA.prescriptions.families[F].doctors -> append 0 (no en pivot)
  - OTC_DATA.prescriptions.families[F].latestMonth -> "<MMM-YYYY>"
  - OTC_DATA.meta.rxCut -> "<MMM-YYYY>"
  - OTC_DASHBOARD.recetas[F]["<MMM YYYY>"] = {recetas, medicos:0}
  - OTC_DASHBOARD.rec_ms[F].sie/ms["<MMM YYYY>"] = ...
  - OTC_DASHBOARD.rec_comp[F][P].monthly["<MMM YYYY>"] = product_count
  - OTC_DASHBOARD.meta.rec_label = "<MMM>'YY"

Lineas soportadas: cardio, ATB, OTC, respiratorio (estructura OTC_DATA + OTC_DASHBOARD).
NO toca mujer/SNC (estructura distinta, requiere su propio extractor).

Uso:
    py shared/merge-recetas-march.py \\
        --pivot "C:\\Users\\.../Sin titulo - Tabla dinamica - 30 de abril de 2026.xlsx" \\
        --month "2026-03" \\
        [--lines cardio ATB OTC respiratorio]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl

LINES_DEFAULT = ['cardio', 'ATB', 'OTC', 'respiratorio']

MES_EN = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
MES_ES = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}


def normalize_brand(name: str | None) -> str:
    if not name: return ''
    s = str(name).upper().strip()
    # Quitar puntos y espacios extras pero mantener forma
    s = re.sub(r'\s+', ' ', s)
    return s


# Mercados que son roll-ups de SIE u otros agregados; sus productos aparecen
# tambien en el mercado especifico, asi que incluirlos genera double-counting.
EXCLUDED_MARKETS = {
    'MIX SIEGFRIED',
}


def load_pivot(pivot_path: Path):
    """Devuelve:
       - brand_count: dict[normalized_brand] -> max count seen across mercados
         (no sumamos: un mismo brand puede aparecer en multiples mercados que son
          aggregations distintas; tomamos el MAX porque las recetas reales son
          el cut mas grande). Ver tambien EXCLUDED_MARKETS para roll-ups que
          se filtran enteros.
       - market_total: dict[market_name] -> count_for_target_month
       - market_brands: dict[market_name] -> list[(brand_normalized, count, is_sie)]
    """
    wb = openpyxl.load_workbook(pivot_path, read_only=True, data_only=True)
    ws = wb.active

    brand_count = {}
    market_total = {}
    market_brands = defaultdict(list)

    for row in ws.iter_rows(min_row=3, values_only=True):
        if not row or len(row) < 4: continue
        merc, droga, marca, val = row[0], row[1], row[2], row[3]
        if not merc: continue
        try:
            count = int(val) if val is not None else 0
        except (TypeError, ValueError):
            count = 0
        cur_market = str(merc).strip()

        if cur_market.upper() in EXCLUDED_MARKETS:
            continue

        if (droga or '').strip().lower() == 'totales' and not marca:
            market_total[cur_market] = count
            continue
        if (marca or '').strip().lower() == 'totales' or not marca:
            continue
        b = normalize_brand(marca)
        is_sie = b.endswith(' SIE') or b.endswith('(SIE)')
        market_brands[cur_market].append((b, count, is_sie))
        # Si el mismo brand aparece en mas de un mercado, tomamos el MAX:
        # CloseUp suele exponer cuts solapados (ej. CARVEDILOL c/ DILATREND
        # y BETABLOQUEANTES c/ DILATREND); el cut mas amplio es el correcto
        # para usar como "recetas totales del producto en el periodo".
        prev = brand_count.get(b, 0)
        if count > prev:
            brand_count[b] = count

    wb.close()
    return brand_count, market_total, market_brands


def parse_data_js(text: str):
    """Extrae los dos objetos window.OTC_DATA = {...}; window.OTC_DASHBOARD = {...};
    Devuelve (otc_data, otc_dashboard, prefix1, suffix1, prefix2, suffix2) para
    poder reconstruir el archivo despues."""
    # Find first window.X = {...};
    m1 = re.search(r'window\.OTC_DATA\s*=\s*', text)
    if not m1:
        raise ValueError('OTC_DATA not found')
    obj_start1 = text.index('{', m1.end())
    d1, end1 = json.JSONDecoder().raw_decode(text[obj_start1:])
    abs_end1 = obj_start1 + end1
    # The semicolon and newlines after
    m2 = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text[abs_end1:])
    if not m2:
        return d1, None, text[:obj_start1], text[abs_end1:], None, None
    obj_start2 = abs_end1 + text[abs_end1:].index('{', m2.end())
    d2, end2 = json.JSONDecoder().raw_decode(text[obj_start2:])
    abs_end2 = obj_start2 + end2

    prefix1 = text[:obj_start1]
    middle = text[abs_end1:obj_start2]
    suffix2 = text[abs_end2:]
    return d1, d2, prefix1, middle, obj_start2, suffix2


def serialize_data_js(text_orig: str, d1: dict, d2: dict | None) -> str:
    """Reconstruye data.js preservando prefijos y sufijos textuales."""
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
    return (prefix1
            + json.dumps(d1, ensure_ascii=False)
            + middle
            + json.dumps(d2, ensure_ascii=False)
            + suffix)


def merge_line(data_js_path: Path, brand_count: dict, month_label_es: str, month_key_en: str, month_key_short: str, dry_run: bool = False):
    """Patcha data.js de UNA linea con la data del nuevo mes."""
    text = data_js_path.read_text(encoding='utf-8-sig', errors='replace')
    d1, d2, *_ = parse_data_js(text)
    if d2 is None:
        return {'skipped': 'no OTC_DASHBOARD'}

    rec_comp = d2.get('rec_comp') or {}
    if not rec_comp:
        return {'skipped': 'no rec_comp'}

    families = list(rec_comp.keys())
    fam_summary = {}

    for fam in families:
        comp = rec_comp[fam]
        sie_total = 0
        market_total = 0
        unmatched = []
        for prod_name, prod_data in comp.items():
            if not isinstance(prod_data, dict): continue
            monthly = prod_data.setdefault('monthly', {})
            b = normalize_brand(prod_name)
            count = brand_count.get(b, 0)
            if count == 0 and b not in brand_count:
                unmatched.append(prod_name)
            monthly[month_key_en] = count
            # Update total
            if isinstance(prod_data.get('total'), (int, float)):
                prod_data['total'] = (prod_data['total'] or 0) + count
            market_total += count
            if 'SIE' in b.upper().split() or b.upper().endswith(' SIE') or b.upper().endswith('(SIE)'):
                sie_total += count

        # rec_ms
        rms = d2.setdefault('rec_ms', {}).setdefault(fam, {})
        sie_dict = rms.setdefault('sie', {})
        ms_dict = rms.setdefault('ms', {})
        sie_dict[month_key_en] = sie_total
        ms_pct = round((sie_total / market_total) * 100, 1) if market_total else 0
        ms_dict[month_key_en] = ms_pct

        # recetas (per family monthly aggregate)
        rec_fam = d2.setdefault('recetas', {}).setdefault(fam, {})
        rec_fam[month_key_en] = {'recetas': market_total, 'medicos': 0}

        # OTC_DATA.prescriptions
        pres = d1.setdefault('prescriptions', {}).setdefault('families', {}).setdefault(fam, {
            'prescriptions': [], 'doctors': [], 'latestMonth': '', 'topBrands': []
        })
        if isinstance(pres.get('prescriptions'), list):
            pres['prescriptions'].append(market_total)
        if isinstance(pres.get('doctors'), list):
            pres['doctors'].append(0)
        pres['latestMonth'] = month_label_es

        fam_summary[fam] = {
            'sie': sie_total, 'mkt': market_total, 'ms': ms_pct,
            'unmatched': unmatched[:5], 'unmatched_count': len(unmatched)
        }

    # OTC_DATA.prescriptions.months
    months = d1.setdefault('prescriptions', {}).setdefault('months', [])
    if month_label_es not in months:
        months.append(month_label_es)

    # Meta updates
    d1.setdefault('meta', {})['rxCut'] = month_label_es
    d2.setdefault('meta', {})['rec_label'] = month_key_short

    if not dry_run:
        new_text = serialize_data_js(text, d1, d2)
        data_js_path.write_text(new_text, encoding='utf-8', newline='')

    return {'families': fam_summary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pivot', required=True, help='Ruta al pivot Excel.')
    ap.add_argument('--month', required=True, help='Mes target: YYYY-MM (ej. 2026-03)')
    ap.add_argument('--repo', default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument('--lines', nargs='+', default=LINES_DEFAULT)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    m = re.match(r'^(\d{4})-(\d{2})$', args.month)
    if not m:
        print(f'ERROR: --month debe ser YYYY-MM, recibido: {args.month}', file=sys.stderr)
        return 2
    yr = int(m.group(1)); mo = int(m.group(2))
    month_label_es = f"{MES_ES[mo]}-{yr}"        # ej. "Mar-2026" para OTC_DATA.prescriptions.months
    month_key_en = f"{MES_EN[mo]} {yr}"          # ej. "Mar 2026" para rec_comp/recetas/rec_ms keys
    month_key_short = f"{MES_EN[mo]}'{str(yr)[-2:]}"  # ej. "Mar'26" para meta.rec_label

    pivot_path = Path(args.pivot)
    if not pivot_path.is_file():
        print(f'ERROR: pivot no existe: {pivot_path}', file=sys.stderr)
        return 2

    print(f'Loading pivot: {pivot_path}')
    brand_count, _, _ = load_pivot(pivot_path)
    print(f'  Brands distintos: {len(brand_count)}')

    repo = Path(args.repo)
    print(f'\nMerging mes "{month_label_es}" en {len(args.lines)} lineas...')
    for line in args.lines:
        data_js = repo / line / 'data.js'
        if not data_js.is_file():
            print(f'  [{line}] SKIP: no data.js')
            continue
        try:
            res = merge_line(data_js, brand_count, month_label_es, month_key_en, month_key_short, dry_run=args.dry_run)
        except Exception as e:
            print(f'  [{line}] ERROR: {e}')
            continue
        if 'skipped' in res:
            print(f'  [{line}] SKIP: {res["skipped"]}')
            continue
        fams = res['families']
        total_unmatched = sum(f['unmatched_count'] for f in fams.values())
        print(f'  [{line}] OK: {len(fams)} familias, {total_unmatched} productos sin match en pivot')
        for fam, s in list(fams.items())[:3]:
            print(f'    - {fam}: SIE={s["sie"]} mkt={s["mkt"]} ms={s["ms"]}%')

    if args.dry_run:
        print('\nDRY RUN: nada se escribio.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
