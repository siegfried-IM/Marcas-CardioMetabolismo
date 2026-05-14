"""Enriquece D.mol_perf[<market>].products con TODAS las brands disponibles
en competidores-data.js (44 brands en respi/ACEMUK vs 8 que estaban).

Para cada market que matchea entre los 2 archivos:
  - Para cada brand en competidores.markets[m].brand_monthly:
    - Suma units across regions por mes
    - Convierte formato 'Abr-2024' -> 'Apr 2024'
    - Si ya existe en mol_perf como producto, NO sobreescribe (mantiene SIE flags)
    - Si no existe, agrega como nuevo producto (is_sie=False)
  - Recomputa ytd/mat/quarterly_vals/ms_* desde monthly_vals

Idempotente: corre cuantas veces quieras.
"""
from __future__ import annotations
import re, json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('cardio',       'cardio/data.js',                'cardio/DDD/competidores-data.js',     False),
    ('ATB',          'ATB/data.js',                   'ATB/DDD/competidores-data.js',        False),
    ('OTC',          'OTC/data.js',                   'OTC/DDD/competidores-data.js',        False),
    ('respiratorio', 'respiratorio/data.js',          'respiratorio/DDD/competidores-data.js', False),
    ('mujer',        'mujer/index.html',              'mujer/DDD/competidores-data.js',      True),
    ('SNC',          'SNC/index.html',                'SNC/DDD/competidores-data.js',        True),
    ('dermatologia', 'dermatologia/dermato_dashboard.html', 'dermatologia/competidores-data.js', True),
]
MES_EN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
MES_ES_TO_EN = {'Ene':'Jan','Feb':'Feb','Mar':'Mar','Abr':'Apr','May':'May','Jun':'Jun',
                'Jul':'Jul','Ago':'Aug','Sep':'Sep','Oct':'Oct','Nov':'Nov','Dic':'Dec'}


def parse_es_month(mk_es):
    """'Abr-2024' -> 'Apr 2024'"""
    parts = mk_es.split('-')
    if len(parts) != 2: return None
    en = MES_ES_TO_EN.get(parts[0])
    if not en: return None
    return f'{en} {parts[1]}'


def load_competidores(path):
    s = path.read_text(encoding='utf-8').replace('window.SFG_COMP_DATA = ', '').rstrip(';\n')
    return json.loads(s)


def load_D(path_rel, is_inline):
    p = REPO / path_rel
    text = p.read_text(encoding='utf-8-sig' if not is_inline else 'utf-8', errors='replace')
    if is_inline:
        m = re.search(r'const D = (\{)', text)
        ob = text.index('{', m.start() + 8)
    else:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
        ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    return text[:ob], D, text[ob+end:], p, is_inline


def save_D(prefix, D, suffix, p):
    p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                 encoding='utf-8', newline='')


def match_market(comp_mkt_name, mol_keys):
    """Match competidores market name -> mol_perf key (case insensitive, fuzzy)."""
    target = comp_mkt_name.upper().replace('-', ' ').replace(' ', '').replace('.', '').strip()
    for k in mol_keys:
        norm = k.upper().replace('-', ' ').replace(' ', '').replace('.', '').strip()
        if norm == target:
            return k
    # Try contains
    for k in mol_keys:
        norm = k.upper().replace('-', ' ').replace(' ', '').replace('.', '').strip()
        if target.startswith(norm) or norm.startswith(target):
            return k
    return None


def aggregate_brand_monthly(brand_monthly_obj, months_es):
    """brand_monthly_obj = {region: [N month values]}
    Returns {month_en: total_units} summed across regions."""
    out = {}
    for region, arr in brand_monthly_obj.items():
        if not isinstance(arr, list): continue
        for i, val in enumerate(arr):
            if i >= len(months_es): break
            mk_en = parse_es_month(months_es[i])
            if not mk_en: continue
            out[mk_en] = out.get(mk_en, 0) + (val or 0)
    return out


def compute_period_aggregates(monthly):
    """Compute ytd, mat, quarterly_vals from monthly_vals."""
    ytd = {}
    mat = {}
    quarterly = {}
    # Group by year
    by_year = defaultdict(dict)
    for mk, v in monthly.items():
        parts = mk.split()
        if len(parts) != 2: continue
        try:
            year = int(parts[1])
            m_idx = MES_EN.index(parts[0])
            by_year[year][m_idx] = v
        except: continue
    # YTD per year = sum from Jan to last available month
    for yr, mvals in by_year.items():
        if not mvals: continue
        ytd[yr] = sum(mvals.values())
    # Quarterly
    for yr, mvals in by_year.items():
        for q in range(1, 5):
            months_in_q = [(q-1)*3, (q-1)*3+1, (q-1)*3+2]
            q_sum = sum(mvals.get(m, 0) for m in months_in_q if m in mvals)
            if q_sum > 0:
                quarterly[f'Q{q} {yr}'] = q_sum
    # MAT: last 12 months from latest entry
    all_mks_sorted = sorted(monthly.keys(), key=lambda k: (int(k.split()[1]), MES_EN.index(k.split()[0])))
    if len(all_mks_sorted) >= 12:
        last_12 = all_mks_sorted[-12:]
        mat_key = int(last_12[-1].split()[1])
        mat[mat_key] = sum(monthly[mk] for mk in last_12)
    elif all_mks_sorted:
        mat_key = int(all_mks_sorted[-1].split()[1])
        mat[mat_key] = sum(monthly[mk] for mk in all_mks_sorted)
    return ytd, mat, quarterly


def enrich_line(line_key, data_rel, comp_rel, is_inline):
    data_p = REPO / data_rel
    comp_p = REPO / comp_rel
    if not data_p.is_file():
        return f'no data file'
    if not comp_p.is_file():
        return f'no competidores file'
    prefix, D, suffix, file_p, _ = load_D(data_rel, is_inline)
    comp = load_competidores(comp_p)
    months_es = comp['months']
    comp_markets = comp['markets']
    mol = D.get('mol_perf', {})
    mol_keys = list(mol.keys())

    stats = {'markets_matched': 0, 'markets_skipped': 0, 'brands_added': 0, 'brands_updated': 0}

    for comp_mkt_name, mkt_obj in comp_markets.items():
        mol_key = match_market(comp_mkt_name, mol_keys)
        if not mol_key:
            stats['markets_skipped'] += 1
            continue
        stats['markets_matched'] += 1

        mol_obj = mol[mol_key]
        existing_prods = {p.get('prod'): p for p in mol_obj.get('products', [])}
        existing_bases = {re.sub(r'\s*\(.*?\)\s*$', '', name).strip().upper(): p
                          for name, p in existing_prods.items()}

        for brand, brand_monthly_obj in mkt_obj.get('brand_monthly', {}).items():
            # Aggregate units across regions
            monthly = aggregate_brand_monthly(brand_monthly_obj, months_es)
            if not monthly: continue
            ytd, mat, quarterly = compute_period_aggregates(monthly)

            # Match existing product
            brand_upper = brand.upper().strip()
            existing = existing_bases.get(brand_upper)
            if existing:
                # Update monthly_vals + derived aggregates, KEEP is_sie + prod name
                existing['monthly_vals'] = {**(existing.get('monthly_vals') or {}), **monthly}
                # Recompute aggregates from updated monthly
                e_ytd, e_mat, e_q = compute_period_aggregates(existing['monthly_vals'])
                existing['ytd'] = e_ytd
                existing['mat'] = e_mat
                existing['quarterly_vals'] = e_q
                stats['brands_updated'] += 1
            else:
                # Add new product
                new_p = {
                    'prod': brand,
                    'is_sie': False,
                    'monthly_vals': monthly,
                    'ytd': ytd,
                    'mat': mat,
                    'quarterly_vals': quarterly,
                    'ms_monthly': {},
                    'ms_ytd': {},
                    'ms_mat': {},
                    'ms_quarterly': {},
                }
                mol_obj['products'].append(new_p)
                stats['brands_added'] += 1

        # Recompute MS% per period for ALL products in this mol
        all_prods = mol_obj['products']
        # MS monthly: total per month
        total_monthly = defaultdict(int)
        for p in all_prods:
            for mk, v in (p.get('monthly_vals') or {}).items():
                total_monthly[mk] += (v or 0)
        for p in all_prods:
            ms_m = {}
            for mk, v in (p.get('monthly_vals') or {}).items():
                tot = total_monthly[mk]
                if tot > 0:
                    ms_m[mk] = round((v or 0) / tot * 100, 2)
            p['ms_monthly'] = ms_m
        # MS ytd: total per year
        total_ytd = defaultdict(int)
        for p in all_prods:
            for yr, v in (p.get('ytd') or {}).items():
                total_ytd[yr] += (v or 0)
        for p in all_prods:
            ms_y = {}
            for yr, v in (p.get('ytd') or {}).items():
                tot = total_ytd[yr]
                if tot > 0: ms_y[yr] = round((v or 0)/tot*100, 2)
            p['ms_ytd'] = ms_y
        # MS mat
        total_mat = defaultdict(int)
        for p in all_prods:
            for yr, v in (p.get('mat') or {}).items():
                total_mat[yr] += (v or 0)
        for p in all_prods:
            ms_m = {}
            for yr, v in (p.get('mat') or {}).items():
                tot = total_mat[yr]
                if tot > 0: ms_m[yr] = round((v or 0)/tot*100, 2)
            p['ms_mat'] = ms_m
        # MS quarterly
        total_q = defaultdict(int)
        for p in all_prods:
            for qk, v in (p.get('quarterly_vals') or {}).items():
                total_q[qk] += (v or 0)
        for p in all_prods:
            ms_q = {}
            for qk, v in (p.get('quarterly_vals') or {}).items():
                tot = total_q[qk]
                if tot > 0: ms_q[qk] = round((v or 0)/tot*100, 2)
            p['ms_quarterly'] = ms_q

    save_D(prefix, D, suffix, file_p)
    return f"markets matched={stats['markets_matched']}, skipped={stats['markets_skipped']}, brands added={stats['brands_added']}, updated={stats['brands_updated']}"


def main():
    for key, data_rel, comp_rel, inline in LINES:
        try:
            print(f'  {key}: {enrich_line(key, data_rel, comp_rel, inline)}')
        except Exception as e:
            print(f'  {key}: ERROR {e}')


if __name__ == '__main__':
    main()
