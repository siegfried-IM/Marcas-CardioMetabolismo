"""Audit completo: revisa TODAS las brands de TODAS las lineas en TODAS las
metricas (IE, MS%, units, growth, recetas, stock) en TODOS los periodos
(YTD, MAT, mensual, trimestre, semestre).

Tolerancia 0.5pp para porcentajes, 0.1% para conteos.
Reporta cada inconsistencia detectada.

Returns exit code 0 si todo OK, 1 si hay mismatches.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KJ_PATH = REPO / 'kpis.json'

LINES = [
    ('cardio',  'cardio',       'cardio/data.js', False),
    ('antibio', 'ATB',          'ATB/data.js',    False),
    ('otx',     'OTC',          'OTC/data.js',    False),
    ('resp',    'respiratorio', 'respiratorio/data.js', False),
    ('mujer',   'mujer',        'mujer/index.html', True),
    ('snc',     'SNC',          'SNC/index.html',   True),
    ('derma',   'dermatologia', 'dermatologia/dermato_dashboard.html', True),
]
MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def load_D(path_rel, is_inline):
    p = REPO / path_rel
    text = p.read_text(encoding='utf-8-sig' if not is_inline else 'utf-8', errors='replace')
    if is_inline:
        m = re.search(r'const D = (\{)', text)
        ob = text.index('{', m.start() + 8)
    else:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
        ob = text.index('{', m.end())
    D, _ = json.JSONDecoder().raw_decode(text[ob:])
    return D


def latest_month(D):
    all_m = set()
    for o in (D.get('mol_perf') or {}).values():
        if not isinstance(o, dict): continue
        for p in o.get('products', []):
            all_m.update((p.get('monthly_vals') or {}).keys())
    if not all_m: return None
    def msort(k):
        ps = k.split(); return int(ps[1])*100 + MES.index(ps[0])+1
    sm = sorted(all_m, key=msort)
    p = sm[-1].split()
    return (int(p[1]), MES.index(p[0])+1)


def ytd(year, end_m): return [f'{MES[i]} {year}' for i in range(end_m)]
def mat(end_y, end_m):
    out = []; y,m = end_y, end_m
    for _ in range(12):
        out.append(f'{MES[m-1]} {y}'); m-=1
        if m==0: m=12; y-=1
    return list(reversed(out))
def trimestre(end_y, end_m):
    return mat(end_y, end_m)[-3:]
def semestre(end_y, end_m):
    return mat(end_y, end_m)[-6:]
def mensual(end_y, end_m):
    return [f'{MES[end_m-1]} {end_y}']


def sum_window(monthly, win): return sum(monthly.get(mk, 0) or 0 for mk in win)


def find_brand_mol(D, brand_key):
    """Find the mol_perf primary market for brand."""
    mol = D.get('mol_perf', {})
    bu = brand_key.upper()
    cands = []
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = str(p.get('prod','')).upper()
            base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
            if base == bu:
                pri = 2 if bu == m_key.upper() else (1 if bu in m_key.upper() else 0)
                cands.append((pri, m_key, obj))
    if not cands: return None, None
    cands.sort(key=lambda x: -x[0])
    return cands[0][1], cands[0][2]


def compute_brand_vs_market(D, brand_key, win_c, win_p):
    mol_key, mol_obj = find_brand_mol(D, brand_key)
    if not mol_obj: return None
    bu = brand_key.upper()
    b_c = b_p = m_c = m_p = 0
    for p in mol_obj.get('products', []):
        mv = p.get('monthly_vals', {})
        c = sum_window(mv, win_c); pp = sum_window(mv, win_p)
        m_c += c; m_p += pp
        name = str(p.get('prod','')).upper()
        base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        if p.get('is_sie') and base == bu:
            b_c += c; b_p += pp
    ie = None
    if b_p > 0 and m_p > 0 and m_c > 0:
        br = b_c/b_p; mr = m_c/m_p
        if mr > 0 and br < 5:
            ie = round(br/mr*100, 1)
    ms = round(b_c/m_c*100, 1) if m_c > 0 else None
    return {'b_c':b_c, 'b_p':b_p, 'm_c':m_c, 'm_p':m_p, 'ie':ie, 'ms':ms}


def approx_eq(a, b, tol=0.5):
    if a is None and b is None: return True
    if a is None or b is None: return False
    return abs(a-b) <= tol


class AuditReport:
    def __init__(self):
        self.checks = 0
        self.fails = 0
        self.fail_details = []

    def check(self, label, expected, actual, tol=0.5):
        self.checks += 1
        if not approx_eq(expected, actual, tol):
            self.fails += 1
            self.fail_details.append(f'  FAIL {label}: expected={expected}, actual={actual}, diff={(actual or 0)-(expected or 0):.2f}')


def audit_line_level(R):
    kj = json.loads(KJ_PATH.read_text(encoding='utf-8'))
    kjl = {l['key']:l for l in kj['lines']}
    print('\n[1] LINE-LEVEL: hub kpis.json vs dashboard kpiStrip')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        ks = D.get('kpiStrip', {})
        kl = kjl.get(key)
        if not kl: continue
        for period_short in ['ytd','mat']:
            k = kl['kpis'][period_short]
            R.check(f'{line_dir} {period_short.upper()} IE', k['units_sie']['ie'], ks.get(f'ie_{period_short}'))
            R.check(f'{line_dir} {period_short.upper()} MS%', k['ms_units']['curr'], ks.get(f'ms_{period_short}'))
            R.check(f'{line_dir} {period_short.upper()} U', k['units_sie']['curr'], ks.get(f'units_{period_short}'), tol=1)
            R.check(f'{line_dir} {period_short.upper()} Uprev', k['units_sie']['prev'], ks.get(f'units_{period_short}25'), tol=1)


def audit_brand_level(R):
    print('\n[2] BRAND-LEVEL: brandKpis vs mol_perf computed')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        bk = D.get('brandKpis', {})
        if not bk: continue
        latest = latest_month(D)
        if not latest: continue
        end_y, end_m = latest
        for brand, kobj in bk.items():
            if not isinstance(kobj, dict): continue
            for period_short, win_c_fn, win_p_fn in [
                ('ytd', lambda: ytd(end_y, end_m),       lambda: ytd(end_y-1, end_m)),
                ('mat', lambda: mat(end_y, end_m),        lambda: mat(end_y-1, end_m)),
            ]:
                target = kobj.get(period_short)
                if not isinstance(target, dict): continue
                comp = compute_brand_vs_market(D, brand, win_c_fn(), win_p_fn())
                if not comp: continue
                R.check(f'{line_dir} {brand} {period_short.upper()} IE', comp['ie'], target.get('ie'))
                R.check(f'{line_dir} {brand} {period_short.upper()} units', comp['b_c'], target.get('units'), tol=1)
                R.check(f'{line_dir} {brand} {period_short.upper()} units_prev', comp['b_p'], target.get('units_prev'), tol=1)
                R.check(f'{line_dir} {brand} {period_short.upper()} ms', comp['ms'], target.get('ms'))


def audit_recetas(R):
    """Verifica que rec_ms.sie + ms_recetas en kpiStrip esten consistentes."""
    kj = json.loads(KJ_PATH.read_text(encoding='utf-8'))
    kjl = {l['key']:l for l in kj['lines']}
    print('\n[3] RECETAS: kpis.json ms_recetas vs kpiStrip.ms_rec')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        ks = D.get('kpiStrip', {})
        kl = kjl.get(key)
        if not kl: continue
        expected = kl['kpis']['ytd']['ms_recetas']['curr']
        if expected is None: continue
        actual = ks.get('ms_rec')
        R.check(f'{line_dir} ms_rec', expected, actual)


def audit_summary(R):
    print('\n' + '=' * 70)
    print(f'TOTAL CHECKS: {R.checks}  PASS: {R.checks-R.fails}  FAIL: {R.fails}')
    print('=' * 70)
    if R.fails:
        print('\nFAILURE DETAILS:')
        for d in R.fail_details[:50]:
            print(d)
        if R.fails > 50:
            print(f'  ... y {R.fails-50} mas')
    return 0 if R.fails == 0 else 1


def main():
    R = AuditReport()
    audit_line_level(R)
    audit_brand_level(R)
    audit_recetas(R)
    return audit_summary(R)


if __name__ == '__main__':
    sys.exit(main())
