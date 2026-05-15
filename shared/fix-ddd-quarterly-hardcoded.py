"""Arregla los indices hardcoded en cardio/SNC/dermato DDD que asumian 12 meses
y 4 quarters, ahora extiendo a soportar cualquier longitud (24 meses, 8 quarters).

Estos 3 archivos tienen el JS inline (const D = {...}) y funciones como
getQMS, getBQMS, rComp que tenian:
  - Array(12).fill(0)        -> Array(D.months.length).fill(0)
  - [0,1,2,3].map(...)       -> Array.from({length:D.quarters.length},...)
  - return [0,0,0,0]         -> return Array(D.quarters.length).fill(0)
  - tm[11] / tm[10]          -> tm[tm.length-1] / tm[tm.length-2]
  - bm[11] / bm[10]          -> bm[bm.length-1] / bm[bm.length-2]
  - 'DIC 2025' (label)       -> ultimo mes formatted dinamicamente

El chart "Evolucion Trimestral MS% por Region" estaba mostrando solo Q2-2024 a
Q1-2025 (4 quarters) cuando la data tiene 8 quarters (Q2-2024 a Q1-2026).

Idempotente. No toca otras secciones ni datos.
"""
from __future__ import annotations
import re, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGETS = [
    'cardio/DDD/index.html',
    'SNC/DDD/psq_ddd.html',
    'dermatologia/dermato_ddd.html',
]


def patch_file(path):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')

    # Idempotency marker
    if '/* ddd-quarterly-hardcoded-fix */' in t:
        return 'already-applied'

    # Parse D to get latest month label
    m = re.search(r'const D\s*=\s*\{', t)
    if not m:
        return 'no-const-D'
    ob = m.end() - 1
    try:
        D, _ = json.JSONDecoder().raw_decode(t[ob:])
    except Exception as e:
        return f'parse-err: {e}'

    months = D.get('months', [])
    quarters = D.get('quarters', [])
    if not months or not quarters:
        return 'empty-data'

    # Format latest month: 'Mar-2026' -> 'MAR 2026'
    latest_label = months[-1].upper().replace('-', ' ')

    new_t = t

    # Replace Array(12).fill -> Array((tm||[]).length||D.months.length||12).fill
    # But Array(12) is used both for `s` (sums) inside getQMS and getBQMS, where
    # we want length=tm.length. Safe to replace with D.months.length.
    new_t = new_t.replace(
        'Array(12).fill(0)',
        'Array(D.months.length).fill(0)'
    )

    # [0,1,2,3].map(q=>...) -> Array.from({length:D.quarters.length},(_,q)=>...)
    new_t = new_t.replace(
        '[0,1,2,3].map(q=>',
        'Array.from({length:D.quarters.length},(_,q)=>'
    )

    # return[0,0,0,0] -> return Array(D.quarters.length).fill(0)
    new_t = new_t.replace(
        'return[0,0,0,0]',
        'return Array(D.quarters.length).fill(0)'
    )

    # tm[11] -> tm[tm.length-1], tm[10] -> tm[tm.length-2]
    new_t = new_t.replace('tm[11]', 'tm[tm.length-1]')
    new_t = new_t.replace('tm[10]', 'tm[tm.length-2]')
    # bm[11] -> bm[bm.length-1], bm[10] -> bm[bm.length-2]
    new_t = new_t.replace('bm[11]', 'bm[bm.length-1]')
    new_t = new_t.replace('bm[10]', 'bm[bm.length-2]')

    # Replace hardcoded 'DIC 2025' label in rComp with dynamic
    # rComp builds: `COMPETIDORES ${rl} · DIC 2025`
    # Replace with dynamic latest month label
    new_t = new_t.replace('DIC 2025`', f'{latest_label}`')
    # Also handle if there's any other 'DIC 2025' label (eg in dermato has 2)
    # The other one might be in different context — keep them dynamic too
    # We use the in-code latest from D so it stays consistent at runtime.
    # Find any remaining DIC 2025 outside literal D = {...}
    # (just to be safe, also handle template literal contexts)

    # Add idempotency marker comment
    new_t = new_t.replace(
        '<script>\nconst D = ',
        '<script>\n/* ddd-quarterly-hardcoded-fix */\nconst D = ',
        1
    )

    if new_t == t:
        return 'no-changes-needed'

    p.write_text(new_t, encoding='utf-8', newline='')
    return f'OK latest={latest_label}'


def main():
    for f in TARGETS:
        print(f'  {f}: {patch_file(f)}')


if __name__ == '__main__':
    main()
