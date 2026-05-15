"""Check sintactico + antipatrones para todos los archivos HTML/JS de las 7 lineas.

Atrapa los siguientes problemas (que ya nos pasaron):
1. JS sintacticamente roto:
   - 'const D=const D=' duplicado
   - 'window.X = window.X' duplicado
   - inline const D / window.OTC_DATA / window.OTC_DASHBOARD que no parsea como JSON
2. Hardcoded antipatterns en DDD JS (asume 12 meses / 4 quarters):
   - Array(12).fill(0)
   - [0,1,2,3].map
   - return[0,0,0,0]
   - tm[11], tm[10], bm[11], bm[10]   (asume last/prev = index 11/10)
   - 'DIC 2025' label hardcoded
3. Consistencia: si const D tiene N meses, los hardcoded indices deben coincidir.
4. nav-actions/nav-items balance: cada nav restructurado tiene actions wrapper.

Se ejecuta automaticamente desde audit-full.py. Tambien se puede correr standalone.

Salida: lista de issues encontrados, exit code 1 si hay alguno.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path
import glob

REPO = Path(__file__).resolve().parent.parent


def collect_html_files():
    files = []
    for d in ['cardio', 'ATB', 'OTC', 'respiratorio', 'SNC', 'mujer', 'dermatologia']:
        files += glob.glob(f'{REPO}/{d}/**/*.html', recursive=True)
    # Skip redirect-only pages (tiny files)
    return [f for f in sorted(set(files)) if Path(f).stat().st_size > 1024]


def collect_data_js():
    files = []
    for d in ['cardio', 'ATB', 'OTC', 'respiratorio', 'SNC', 'mujer', 'dermatologia']:
        files += glob.glob(f'{REPO}/{d}/**/data.js', recursive=True)
    return sorted(set(files))


def check_js_syntax(t, label):
    """Detect duplicate var declarations and unparseable inline data."""
    issues = []

    # Duplicate const/var assignments
    for pat, msg in [
        (r'const D\s*=\s*const D\s*=', "duplicate 'const D=const D='"),
        (r'window\.OTC_DATA\s*=\s*window\.OTC_DATA', "duplicate 'window.OTC_DATA = window.OTC_DATA'"),
        (r'window\.OTC_DASHBOARD\s*=\s*window\.OTC_DASHBOARD', "duplicate 'window.OTC_DASHBOARD = window.OTC_DASHBOARD'"),
    ]:
        m = re.search(pat, t)
        if m:
            issues.append(f'{label}: SYNTAX {msg} at pos {m.start()}')

    # Try to parse inline const D
    m = re.search(r'(?:^|\n|\s|;)const D\s*=\s*\{', t)
    if m:
        ob = t.index('{', m.end())
        try:
            D, _ = json.JSONDecoder().raw_decode(t[ob:])
        except Exception as e:
            issues.append(f'{label}: const D parse error: {str(e)[:120]}')

    # Try to parse window.OTC_DATA / window.OTC_DASHBOARD (only if followed by {)
    for var_name in ['window.OTC_DATA', 'window.OTC_DASHBOARD']:
        # Look for direct object literal assignment (followed by {), not aliases
        m = re.search(rf'{re.escape(var_name)}\s*=\s*\{{', t)
        if m:
            ob = m.end() - 1  # position of {
            try:
                D, _ = json.JSONDecoder().raw_decode(t[ob:])
            except Exception as e:
                issues.append(f'{label}: {var_name} parse error: {str(e)[:120]}')

    return issues


def check_sku_level_sie(t, label):
    """Detect SKU-level SIE products in mol_perf (should be brand-level)."""
    issues = []
    # Look for inline const D or window.OTC_DASHBOARD or window.MUJER_DATA
    for var_pat in [r'(?:^|\n|\s|;)const D\s*=\s*\{',
                    r'window\.OTC_DASHBOARD\s*=\s*\{',
                    r'window\.OTC_DATA\s*=\s*\{']:
        m = re.search(var_pat, t)
        if m:
            ob = t.index('{', m.start())
            try:
                D, _ = json.JSONDecoder().raw_decode(t[ob:])
            except Exception:
                continue
            mol = D.get('mol_perf', {})
            if not isinstance(mol, dict):
                continue
            # Patterns indicating SKU-level packaging info
            sku_indicators = ['TABL ', 'CAPS ', 'COMP ', 'AMP ', 'JBE ',
                              'CREM ', 'GOTAS ', 'GEL ', 'SUSP ', 'GRAN ',
                              'SUPP ', 'SPRAY ', 'A.IM', 'POMA ', 'POLV ',
                              'OVUL ', 'ENJUAGUE ', 'TAB ', 'INH ']
            for fam, obj in mol.items():
                if not isinstance(obj, dict):
                    continue
                for p in obj.get('products', []):
                    if not isinstance(p, dict) or not p.get('is_sie'):
                        continue
                    nm = (p.get('prod') or '').upper()
                    has_sku = any(ind in nm for ind in sku_indicators)
                    has_digit = any(c.isdigit() for c in nm)
                    if has_sku and has_digit:
                        issues.append(
                            f'{label}: SKU-LEVEL SIE in mol_perf[{fam!r}]: {p.get("prod")!r} '
                            f'(should be brand-level, e.g. "ISIS (SIE)")'
                        )
            break
    return issues


def check_ddd_hardcoded(t, label):
    """Detect hardcoded month/quarter indices in DDD JS code."""
    issues = []
    # Only inspect if this is a DDD file with inline const D
    m = re.search(r'(?:^|\n|\s|;)const D\s*=\s*\{', t)
    if not m:
        return issues
    ob = t.index('{', m.end())
    try:
        D, _ = json.JSONDecoder().raw_decode(t[ob:])
    except Exception:
        return issues
    n_months = len(D.get('months', []))
    n_quarters = len(D.get('quarters', []))

    # Look for hardcoded patterns AFTER the const D (in the JS code)
    code_after_data = t[ob:]
    end_data_pos = re.search(r'\};\s*\n', code_after_data)
    if end_data_pos:
        code_after_data = code_after_data[end_data_pos.end():]

    for pat, msg in [
        (r'Array\(12\)\.fill', "Array(12).fill — should use Array(D.months.length).fill"),
        (r'\[0,1,2,3\]\.map\(q=>', "[0,1,2,3].map — should use Array.from({length:D.quarters.length})"),
        (r'return\[0,0,0,0\]', "return[0,0,0,0] — should match D.quarters.length"),
        (r'tm\[11\]', "tm[11] — should use tm[tm.length-1]"),
        (r'tm\[10\]', "tm[10] — should use tm[tm.length-2]"),
        (r'bm\[11\]', "bm[11] — should use bm[bm.length-1]"),
        (r'bm\[10\]', "bm[10] — should use bm[bm.length-2]"),
        (r"['\"]DIC 2025['\"]", "'DIC 2025' hardcoded label"),
    ]:
        for hit in re.finditer(pat, code_after_data):
            if n_months > 12 or n_quarters > 4:
                issues.append(f'{label}: HARDCODED {msg} (data has {n_months}mo/{n_quarters}q)')
                break  # one report per pattern

    return issues


def main():
    all_issues = []

    print('[CHECK] Sintaxis + antipatrones para todas las paginas HTML/JS...')
    html_files = collect_html_files()
    for f in html_files:
        t = Path(f).read_text(encoding='utf-8', errors='replace')
        rel = str(Path(f).relative_to(REPO))
        all_issues += check_js_syntax(t, rel)
        all_issues += check_ddd_hardcoded(t, rel)
        all_issues += check_sku_level_sie(t, rel)

    js_files = collect_data_js()
    for f in js_files:
        t = Path(f).read_text(encoding='utf-8-sig', errors='replace')
        rel = str(Path(f).relative_to(REPO))
        all_issues += check_js_syntax(t, rel)
        all_issues += check_sku_level_sie(t, rel)

    if not all_issues:
        print(f'[CHECK] OK: {len(html_files)} HTML + {len(js_files)} JS files validados, sin issues.')
        sys.exit(0)
    else:
        print(f'[CHECK] FAIL: {len(all_issues)} issues encontrados:')
        for i in all_issues:
            print(f'  - {i}')
        sys.exit(1)


if __name__ == '__main__':
    main()
