"""Agrega SOLO el mes Apr 2026 al mol_perf de cada linea, preservando TODO
el historico previo.

Fuente del nuevo dato Apr 2026: la version sincronizada de cada archivo
en el commit cb8cdaf (que tenia Apr 2026 pero perdio historia).

Para cada producto en mol_perf inline D / OTC_DASHBOARD:
  - Si el producto existe en cb8cdaf con datos para Apr 2026:
    - monthly_vals['Apr 2026']     = valor del commit cb8cdaf
    - quarterly_vals['Q2 2026']    = sum(Apr+May+Jun) - si solo hay Apr, queda solo Apr
    - ytd['Apr 2026']              = sum(Jan..Apr 2026)
    - mat['Apr 2026']              = sum(ultimos 12 meses)
    - ms_monthly['Apr 2026']       = producto/familia para Apr 2026
    - ms_quarterly['Q2 2026']      = producto/familia para Q2 2026
    - ms_ytd['Apr 2026']           = producto/familia YTD
    - ms_mat['Apr 2026']           = producto/familia MAT
  - Resto de los meses NO se tocan.

Tambien actualiza family-level aggregates (monthly[Apr 2026], ytd[Apr 2026],
mat[Apr 2026], quarterly[Q2 2026]).

Verificacion final:
  - Historia preservada (primer mes = misma que antes)
  - Apr 2026 agregado en mol_perf de los 7 lineas

Uso: py shared/merge-april-2026-only.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE_COMMIT_DEFAULT = 'cb8cdaf'  # commit con mol_perf-Apr 2026 (pero historia perdida)
# Override por archivo si el commit default no tiene Apr 2026 para ese path
SOURCE_COMMIT_OVERRIDE = {
    'mujer/index.html': 'bb9ae88',  # mujer/index.html fue sync'd despues, en bb9ae88
}

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}


def msort(mk):
    p = mk.split()
    if len(p) != 2: return 0
    try:
        return int(p[1]) * 100 + MES_INV.get(p[0], 0)
    except (ValueError, IndexError):
        return 0


def quarter_key(mk):
    parts = mk.split()
    if len(parts) != 2: return ''
    m = MES_INV.get(parts[0])
    if not m: return ''
    q = (m - 1) // 3 + 1
    return f'Q{q} {parts[1]}'


# (path, variable_pattern, encoding_header_strip, is_inline)
LINES = [
    ('cardio/data.js',                      'window.OTC_DASHBOARD', 'utf-8-sig', False),
    ('ATB/data.js',                         'window.OTC_DASHBOARD', 'utf-8-sig', False),
    ('OTC/data.js',                         'window.OTC_DASHBOARD', 'utf-8-sig', False),
    ('respiratorio/data.js',                'window.OTC_DASHBOARD', 'utf-8-sig', False),
    ('mujer/index.html',                    'const D',              'utf-8',      True),
    ('SNC/index.html',                      'const D',              'utf-8',      True),
    ('dermatologia/dermato_dashboard.html', 'const D',              'utf-8',      True),
]


def parse_data(text, var_pattern, is_inline):
    """Locate and parse the JSON object. Returns (D, abs_start, abs_end)."""
    if is_inline:
        m = re.search(r'const D\s*=\s*\{', text)
        if not m: return None
        ob = m.end() - 1
    else:
        m = re.search(re.escape(var_pattern) + r'\s*=\s*', text)
        if not m: return None
        ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    return D, ob, ob + end


def get_source_mol_perf(path):
    """Load mol_perf from SOURCE_COMMIT for this file."""
    commit = SOURCE_COMMIT_OVERRIDE.get(path, SOURCE_COMMIT_DEFAULT)
    r = subprocess.run(['git', 'show', f'{commit}:{path}'],
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        return None
    t = r.stdout
    # Detect which variable to look for
    for var, is_inline in [('const D', True), ('window.OTC_DASHBOARD', False), ('window.MUJER_DASHBOARD', False), ('window.OTC_DATA', False)]:
        try:
            parsed = parse_data(t, var, is_inline)
            if parsed:
                D, _, _ = parsed
                if D.get('mol_perf'):
                    return D.get('mol_perf', {})
        except Exception:
            continue
    return None


def merge_apr_2026(path, var_pattern, encoding, is_inline, dry_run=False):
    """Merge Apr 2026 from SOURCE_COMMIT into current file's mol_perf.
    Preserves all historical data."""
    p = REPO / path
    t = p.read_text(encoding=encoding, errors='replace')
    parsed = parse_data(t, var_pattern, is_inline)
    if not parsed:
        return {'status': 'no-data-found'}
    D, ob, end = parsed

    mol = D.get('mol_perf', {})
    if not mol:
        return {'status': 'no-mol-perf'}

    src_mol = get_source_mol_perf(path)
    if not src_mol:
        return {'status': 'no-source-data-in-commit'}

    APR = 'Apr 2026'
    Q2 = 'Q2 2026'

    n_prods_updated = 0
    n_prods_missing_in_source = 0
    families_updated = []

    # Helper: rebuild ytd/mat for Apr 2026
    def compute_ytd_apr2026(monthly_dict):
        """YTD Apr 2026 = sum Jan-Apr 2026."""
        total = 0
        for mes in ['Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026']:
            v = monthly_dict.get(mes)
            if v is not None:
                try: total += float(v)
                except (TypeError, ValueError): pass
        return int(round(total))

    def compute_mat_apr2026(monthly_dict):
        """MAT Apr 2026 = sum May 2025 - Apr 2026 (12 months ending Apr 2026)."""
        months = ['May 2025','Jun 2025','Jul 2025','Aug 2025','Sep 2025','Oct 2025','Nov 2025','Dec 2025',
                  'Jan 2026','Feb 2026','Mar 2026','Apr 2026']
        total = 0
        for mes in months:
            v = monthly_dict.get(mes)
            if v is not None:
                try: total += float(v)
                except (TypeError, ValueError): pass
        return int(round(total))

    # First pass: process products and compute updated family totals
    for fam_key, fam_obj in mol.items():
        if not isinstance(fam_obj, dict):
            continue
        prods = fam_obj.get('products', [])
        src_fam = src_mol.get(fam_key, {})
        src_prods_by_name = {}
        if isinstance(src_fam, dict):
            for sp in src_fam.get('products', []):
                if isinstance(sp, dict) and sp.get('prod'):
                    src_prods_by_name[sp['prod']] = sp

        fam_updated = False
        for p_ in prods:
            if not isinstance(p_, dict): continue
            name = p_.get('prod')
            if not name: continue
            src_p = src_prods_by_name.get(name)
            if not src_p:
                n_prods_missing_in_source += 1
                continue
            # Get Apr 2026 value from source
            src_mv = src_p.get('monthly_vals', {})
            apr_val = src_mv.get(APR)
            if apr_val is None:
                continue
            # Add Apr 2026 to monthly_vals (if not already)
            mv = p_.setdefault('monthly_vals', {})
            mv[APR] = apr_val
            # Update quarterly_vals Q2 2026: sum Apr+May+Jun (only Apr available for now)
            qv = p_.setdefault('quarterly_vals', {})
            apr_q = (mv.get('Apr 2026') or 0) + (mv.get('May 2026') or 0) + (mv.get('Jun 2026') or 0)
            qv[Q2] = int(round(apr_q))
            # Update ytd[Apr 2026] and mat[Apr 2026]
            p_['ytd'] = p_.get('ytd', {}); p_['ytd'][APR] = compute_ytd_apr2026(mv)
            p_['mat'] = p_.get('mat', {}); p_['mat'][APR] = compute_mat_apr2026(mv)
            # ms_* will be filled after family aggregates
            n_prods_updated += 1
            fam_updated = True

        if fam_updated:
            families_updated.append(fam_key)

    # Second pass: update family-level monthly/quarterly/ytd/mat aggregates + ms_*
    for fam_key in families_updated:
        fam_obj = mol[fam_key]
        prods = fam_obj.get('products', [])
        # Sum across all products for Apr 2026
        fam_apr_total = sum((p_.get('monthly_vals', {}).get(APR) or 0) for p_ in prods)
        # Update family monthly[Apr 2026]
        if 'monthly' in fam_obj and isinstance(fam_obj['monthly'], dict):
            fam_obj['monthly'][APR] = int(round(fam_apr_total))
        # Family quarterly Q2 2026
        if 'quarterly' in fam_obj and isinstance(fam_obj['quarterly'], dict):
            fam_q2 = (fam_obj['monthly'].get('Apr 2026') or 0) + (fam_obj['monthly'].get('May 2026') or 0) + (fam_obj['monthly'].get('Jun 2026') or 0)
            fam_obj['quarterly'][Q2] = int(round(fam_q2))
        # Family ytd[Apr 2026]
        if 'ytd' in fam_obj and isinstance(fam_obj['ytd'], dict):
            fam_obj['ytd'][APR] = sum((fam_obj.get('monthly', {}).get(m) or 0) for m in ['Jan 2026','Feb 2026','Mar 2026','Apr 2026'])
        # Family mat[Apr 2026]
        if 'mat' in fam_obj and isinstance(fam_obj['mat'], dict):
            mat_months = ['May 2025','Jun 2025','Jul 2025','Aug 2025','Sep 2025','Oct 2025','Nov 2025','Dec 2025',
                          'Jan 2026','Feb 2026','Mar 2026','Apr 2026']
            fam_obj['mat'][APR] = sum((fam_obj.get('monthly', {}).get(m) or 0) for m in mat_months)
        # Now compute ms_* for each product for Apr 2026
        fam_apr = fam_obj.get('monthly', {}).get(APR, 0) if isinstance(fam_obj.get('monthly'), dict) else fam_apr_total
        fam_q2_total = fam_obj.get('quarterly', {}).get(Q2, 0) if isinstance(fam_obj.get('quarterly'), dict) else fam_apr_total
        fam_ytd_apr = fam_obj.get('ytd', {}).get(APR, 0) if isinstance(fam_obj.get('ytd'), dict) else 0
        fam_mat_apr = fam_obj.get('mat', {}).get(APR, 0) if isinstance(fam_obj.get('mat'), dict) else 0
        for p_ in prods:
            if not isinstance(p_, dict): continue
            mv = p_.get('monthly_vals', {})
            apr_v = mv.get(APR)
            if apr_v is None: continue
            # ms_monthly Apr 2026
            ms_m = p_.setdefault('ms_monthly', {})
            ms_m[APR] = round(apr_v/fam_apr*100, 2) if fam_apr > 0 else 0
            # ms_quarterly Q2 2026
            ms_q = p_.setdefault('ms_quarterly', {})
            q2 = p_.get('quarterly_vals', {}).get(Q2, 0)
            ms_q[Q2] = round(q2/fam_q2_total*100, 2) if fam_q2_total > 0 else 0
            # ms_ytd Apr 2026
            ms_y = p_.setdefault('ms_ytd', {})
            yv = p_.get('ytd', {}).get(APR, 0)
            ms_y[APR] = round(yv/fam_ytd_apr*100, 2) if fam_ytd_apr > 0 else 0
            # ms_mat Apr 2026
            ms_t = p_.setdefault('ms_mat', {})
            mv_v = p_.get('mat', {}).get(APR, 0)
            ms_t[APR] = round(mv_v/fam_mat_apr*100, 2) if fam_mat_apr > 0 else 0

    # Update meta if present
    meta = D.get('meta', {})
    if meta:
        # Solo si meta tenia campos relevantes (no forzamos crearlos)
        if 'latest_month' in meta:
            meta['latest_month'] = APR
        if 'ytd_keys' in meta:
            yk = meta['ytd_keys']
            if isinstance(yk, list) and APR not in yk:
                yk.append(APR)
        if 'mat_keys' in meta:
            mk = meta['mat_keys']
            if isinstance(mk, list) and APR not in mk:
                mk.append(APR)
        if 'current_ytd_key' in meta:
            meta['current_ytd_key'] = APR
        if 'current_mat_key' in meta:
            meta['current_mat_key'] = APR
        if 'prev_ytd_key' in meta and meta.get('latest_month') == APR:
            meta['prev_ytd_key'] = 'Apr 2025'
        if 'kpi_ytd_label' in meta:
            meta['kpi_ytd_label'] = "YTD Abr'2026"
        if 'kpi_ytd_prev_label' in meta:
            meta['kpi_ytd_prev_label'] = "YTD Abr'2025"
        if 'kpi_mat_label' in meta:
            meta['kpi_mat_label'] = "MAT Abr'2026"
        if 'kpi_mat_prev_label' in meta:
            meta['kpi_mat_prev_label'] = "MAT Mar'2026"
        # latestKey for mujer
        if 'latestKey' in meta:
            meta['latestKey'] = APR

    if dry_run:
        return {'status': 'dry-run',
                'updated': n_prods_updated,
                'missing': n_prods_missing_in_source,
                'families': len(families_updated)}

    new_t = t[:ob] + json.dumps(D, ensure_ascii=False) + t[end:]
    p.write_text(new_t, encoding=encoding.replace('-sig', ''), newline='')
    return {'status': 'OK',
            'updated': n_prods_updated,
            'missing': n_prods_missing_in_source,
            'families': len(families_updated)}


def verify(path, var_pattern, encoding, is_inline):
    """Quick verification: check 'Apr 2026' is now in mol_perf and historical
    months are still present."""
    p = REPO / path
    t = p.read_text(encoding=encoding, errors='replace')
    parsed = parse_data(t, var_pattern, is_inline)
    if not parsed: return None
    D, _, _ = parsed
    mol = D.get('mol_perf', {})
    all_months = set()
    apr_count = 0
    for v in mol.values():
        if not isinstance(v, dict): continue
        for p_ in v.get('products', []):
            mv = p_.get('monthly_vals', {})
            all_months.update(mv.keys())
            if 'Apr 2026' in mv: apr_count += 1
    keys = sorted(all_months, key=msort)
    return {
        'first_month': keys[0] if keys else None,
        'last_month': keys[-1] if keys else None,
        'total_months': len(keys),
        'products_with_apr2026': apr_count,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    print(f'Merging Apr 2026 from {SOURCE_COMMIT_DEFAULT} (default) + per-file overrides into restored mol_perf...')
    print()
    results = []
    for path, var, enc, inline in LINES:
        r = merge_apr_2026(path, var, enc, inline, dry_run=args.dry_run)
        results.append((path, r))
        print(f'  {path}: {r}')
    print()
    print('VERIFICATION:')
    print(f'{"file":50s} | {"range":40s} | {"prod_w/Apr2026":15s}')
    print('-'*110)
    for path, var, enc, inline in LINES:
        v = verify(path, var, enc, inline)
        if v:
            r = f'{v["first_month"]} -> {v["last_month"]} ({v["total_months"]} mo)'
            print(f'{path:50s} | {r:40s} | {v["products_with_apr2026"]:15d}')


if __name__ == '__main__':
    main()
