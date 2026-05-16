"""Scrub products listed in shared/excluded-products.py from all data sources.

Searches and removes excluded products from:
  - data.js  -> mol_perf[*].products[], rec_comp[*][brand], brand_monthly[brand]
  - index.html (inline const D) -> idem
  - DDD competidores-data.js -> markets[*].brand_monthly[brand]

Idempotente. Re-run after every data refresh, or after adding to the list.
"""
from __future__ import annotations
import re, json, importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Load the exclusion list dynamically (filename has hyphen)
spec = importlib.util.spec_from_file_location('excluded', REPO / 'shared' / 'excluded-products.py')
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)
is_excluded = _mod.is_excluded
EXCLUDED_PRODUCTS = _mod.EXCLUDED_PRODUCTS


def scrub_mol_perf(D, log_prefix):
    """Remove products from D.mol_perf[*].products[]."""
    removed = 0
    mol = D.get('mol_perf', {})
    if not isinstance(mol, dict):
        return removed
    for fam, obj in mol.items():
        if not isinstance(obj, dict):
            continue
        prods = obj.get('products', [])
        new_prods = []
        for p in prods:
            if isinstance(p, dict) and is_excluded(p.get('prod')):
                removed += 1
                print(f'    {log_prefix} mol_perf[{fam!r}] removed: {p.get("prod")!r}')
                continue
            new_prods.append(p)
        obj['products'] = new_prods
    return removed


def scrub_rec_comp(D, log_prefix):
    """Remove products from D.rec_comp[fam][brand]."""
    removed = 0
    rec_comp = D.get('rec_comp', {})
    if not isinstance(rec_comp, dict):
        return removed
    for fam, brands in rec_comp.items():
        if not isinstance(brands, dict):
            continue
        keys_to_drop = [b for b in brands if is_excluded(b)]
        for b in keys_to_drop:
            del brands[b]
            removed += 1
            print(f'    {log_prefix} rec_comp[{fam!r}] removed: {b!r}')
    return removed


def scrub_ddd_markets(D, log_prefix):
    """Remove products from D.markets[*].brand_monthly[brand] (DDD shape)."""
    removed = 0
    markets = D.get('markets', {})
    if not isinstance(markets, dict):
        return removed
    for mk, obj in markets.items():
        if not isinstance(obj, dict):
            continue
        bm = obj.get('brand_monthly', {})
        if isinstance(bm, dict):
            keys = [b for b in bm if is_excluded(b)]
            for b in keys:
                del bm[b]
                removed += 1
                print(f'    {log_prefix} markets[{mk!r}].brand_monthly removed: {b!r}')
        # Also brands SIE list
        brands_list = obj.get('brands', [])
        if isinstance(brands_list, list):
            new = [b for b in brands_list if not is_excluded(b)]
            if len(new) != len(brands_list):
                removed += (len(brands_list) - len(new))
                obj['brands'] = new
    return removed


def scrub_inline_const_D(path):
    """Scrub inline const D in HTML files."""
    t = path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D\s*=\s*\{', t)
    if not m:
        return 0
    ob = m.end() - 1
    try:
        D, end = json.JSONDecoder().raw_decode(t[ob:])
    except Exception:
        return 0
    prefix = t[:ob]
    suffix = t[ob + end:]
    n = scrub_mol_perf(D, str(path.relative_to(REPO)))
    n += scrub_rec_comp(D, str(path.relative_to(REPO)))
    n += scrub_ddd_markets(D, str(path.relative_to(REPO)))
    n += scrub_precios(D, str(path.relative_to(REPO)))
    if n > 0:
        path.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                        encoding='utf-8', newline='')
    return n


def scrub_precios(D, log_prefix):
    """Remove products from D.precios / D.prec_iqvia (nested structures)."""
    removed = 0

    # D.precios: dict by family, then nested list of {prod, ...}
    # Also handles list-style: D.precios = [{prod, ...}, ...]
    for key in ['precios', 'prec_iqvia']:
        node = D.get(key)
        if node is None:
            continue
        removed += _scrub_recursive(node, key, log_prefix)
    return removed


def _scrub_recursive(obj, label, log_prefix):
    """Recursively remove excluded items from any nested structure:
       - dict keys matching excluded -> deleted
       - list items with 'prod' field matching excluded -> filtered out
    """
    removed = 0
    if isinstance(obj, dict):
        keys_to_drop = [k for k in obj if is_excluded(k)]
        for k in keys_to_drop:
            del obj[k]
            removed += 1
            print(f'    {log_prefix} {label} dict-key removed: {k!r}')
        # Recurse into remaining values
        for k, v in list(obj.items()):
            removed += _scrub_recursive(v, f'{label}.{k}', log_prefix)
    elif isinstance(obj, list):
        # Filter out dicts whose 'prod' is excluded
        to_drop = [i for i, it in enumerate(obj)
                   if isinstance(it, dict) and is_excluded(it.get('prod'))]
        for i in reversed(to_drop):
            print(f'    {log_prefix} {label}[{i}] removed: {obj[i].get("prod")!r}')
            obj.pop(i)
            removed += 1
        # Recurse remaining
        for it in obj:
            removed += _scrub_recursive(it, label, log_prefix)
    return removed


def scrub_data_js(path):
    """Scrub all known data variables (may have multiple per file)."""
    t = path.read_text(encoding='utf-8-sig', errors='replace')
    total = 0
    for var_name in ['window.OTC_DASHBOARD', 'window.OTC_DATA',
                     'window.MUJER_DATA', 'window.MUJER_DASHBOARD',
                     'window.SFG_COMP_DATA']:
        # Allow multiple occurrences
        offset = 0
        while True:
            m = re.search(rf'{re.escape(var_name)}\s*=\s*\{{', t[offset:])
            if not m:
                break
            ob = offset + m.end() - 1
            try:
                D, end = json.JSONDecoder().raw_decode(t[ob:])
            except Exception:
                offset = ob + 1
                continue
            prefix = t[:ob]
            suffix = t[ob + end:]
            n = scrub_mol_perf(D, str(path.relative_to(REPO)))
            n += scrub_rec_comp(D, str(path.relative_to(REPO)))
            n += scrub_ddd_markets(D, str(path.relative_to(REPO)))
            n += scrub_precios(D, str(path.relative_to(REPO)))
            if n > 0:
                t = prefix + json.dumps(D, ensure_ascii=False) + suffix
                total += n
                # Recompute offset since text changed
                offset = ob + len(json.dumps(D, ensure_ascii=False))
            else:
                offset = ob + end
    if total > 0:
        path.write_text(t, encoding='utf-8', newline='')
    return total


def main():
    print(f'Excluded products: {EXCLUDED_PRODUCTS}')
    print()
    grand_total = 0

    # Process all data.js
    for p in REPO.glob('**/data.js'):
        if '/.git/' in str(p) or '\\.git\\' in str(p):
            continue
        n = scrub_data_js(p)
        if n > 0:
            print(f'  [{p.relative_to(REPO)}] scrubbed {n} entries')
            grand_total += n

    # Process all competidores-data.js
    for p in REPO.glob('**/competidores-data.js'):
        n = scrub_data_js(p)
        if n > 0:
            print(f'  [{p.relative_to(REPO)}] scrubbed {n} entries')
            grand_total += n

    # Process inline const D in HTMLs
    for line_dir in ['cardio', 'ATB', 'OTC', 'respiratorio', 'SNC', 'mujer', 'dermatologia']:
        for html in (REPO / line_dir).rglob('*.html'):
            if html.stat().st_size < 5000:
                continue
            n = scrub_inline_const_D(html)
            if n > 0:
                print(f'  [{html.relative_to(REPO)}] scrubbed {n} entries')
                grand_total += n

    print()
    print(f'TOTAL: {grand_total} entries scrubbed')
    if grand_total > 0:
        print('IMPORTANT: re-run `py shared/build-kpis.py` to refresh kpis.json')


if __name__ == '__main__':
    main()
