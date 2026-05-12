"""Quitar la seccion 'Precios vs Competidores' del body y mover Precios al nav
como pill externo (color bordeaux suave) que linkea a siegfried-precios.pages.dev.

Aplica a las 7 lineas. Idempotente.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# Reemplaza el nav-item Precios por un pill externo (estilo bordeaux/dark)
NAV_OLD = '<a class="nav-item" href="#s-prec">Precios</a>'
NAV_NEW = '<a class="nav-tab hl" href="https://siegfried-precios.pages.dev/" target="_blank" rel="noopener" style="color:#fff;background:#7a1414;border-radius:5px;padding:0 12px;margin:8px 8px 8px 0;height:34px;">Precios ↗</a>'

# Bloque de seccion s-prec a eliminar (busqueda regex permisiva por indent variable)
SEC_PATTERN = re.compile(
    r'\s*<!-- ══ 06 PRECIOS COMPETIDORES[^\n]*\n'
    r'\s*<div class="sec" id="s-prec">.*?</div>\s*\n\s*</div>\s*',
    re.S
)
# Fallback sin comentario header
SEC_PATTERN_FALLBACK = re.compile(
    r'\s*<div class="sec" id="s-prec">.*?siegfried-precios\.pages\.dev.*?</div>\s*\n\s*</div>\s*',
    re.S
)


def patch(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    notes = []
    # 1) Nav
    if 'siegfried-precios.pages.dev' in t and NAV_OLD not in t and 'Precios ↗' in t:
        notes.append('nav already')
    elif NAV_OLD in t:
        t = t.replace(NAV_OLD, NAV_NEW, 1)
        notes.append('nav OK')
    else:
        notes.append('nav NO anchor')
    # 2) Section removal
    t2, n = SEC_PATTERN.subn('\n', t, count=1)
    if n == 0:
        t2, n = SEC_PATTERN_FALLBACK.subn('\n', t, count=1)
    if n > 0:
        t = t2
        notes.append('section removed')
    elif 'id="s-prec"' not in t:
        notes.append('section already removed')
    else:
        notes.append('section NO match')
    path.write_text(t, encoding='utf-8', newline='')
    return ' · '.join(notes)


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  {f}: MISSING'); continue
        print(f'  {f}: {patch(p)}')


if __name__ == '__main__':
    main()
