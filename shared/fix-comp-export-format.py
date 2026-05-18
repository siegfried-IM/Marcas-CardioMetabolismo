"""Reemplaza tableToAoA + exportExcel en las 6 competidores restantes
(post-POC en OTC commit XXX) con versiones que:
- Parsean texto -> numeros reales con format Excel (%, #,##0, +0.0, etc.).
- Mantienen colspan/rowspan via XLSX !merges.
- Aplican anchos de columna + freeze panes.
- Renombran sheet "Por Region CUP" -> "Por Region".

Idempotente: detecta presencia de tableToStructured y skip.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / 'OTC' / 'DDD' / 'competidores.html'
TARGETS = [
    'cardio/DDD/competidores.html',
    'ATB/DDD/competidores.html',
    'respiratorio/DDD/competidores.html',
    'mujer/DDD/competidores.html',
    'SNC/DDD/competidores.html',
    'dermatologia/competidores.html',
]


def extract_new_export_block(source_html):
    """Extract the new export functions block from OTC source."""
    m = re.search(
        r'  // === Export to Excel ===.*?  document\.getElementById\(\'btn-export\'\)\.addEventListener\(\'click\', exportExcel\);',
        source_html, re.DOTALL
    )
    if not m:
        raise RuntimeError('No se pudo extraer bloque export del source')
    return m.group(0)


# Old block pattern (lo que existe HOY en los 6 archivos, antes del fix)
OLD_BLOCK_PATTERN = re.compile(
    r'  // === Export to Excel ===.*?  document\.getElementById\(\'btn-export\'\)\.addEventListener\(\'click\', exportExcel\);',
    re.DOTALL
)


def patch_file(path, new_block):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')

    # Idempotency
    if 'tableToStructured' in t:
        return 'already-applied'

    m = OLD_BLOCK_PATTERN.search(t)
    if not m:
        return 'old-block-not-found'

    new_t = t[:m.start()] + new_block + t[m.end():]
    if new_t == t:
        return 'no-change'
    p.write_text(new_t, encoding='utf-8', newline='')
    return 'OK'


def main():
    src = SOURCE.read_text(encoding='utf-8')
    new_block = extract_new_export_block(src)
    for path in TARGETS:
        print(f'  {path}: {patch_file(path, new_block)}')


if __name__ == '__main__':
    main()
