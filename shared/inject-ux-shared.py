"""Inyecta los assets UX compartidos (microinteractions.css, design-tokens.css,
ux-shared.js) en las 21 paginas del hub + lineas + DDD + competidores.

Idempotente: si ya estan inyectados (marker comment), no duplica.

Uso:
    py shared/inject-ux-shared.py [--dry-run]
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DRY = '--dry-run' in sys.argv

# (path, depth) — depth = niveles desde root para calcular relativo a /shared/
TARGETS = [
    ('index.html',                                  0),
    ('kpis.html',                                   0),
    # Main dashboards (depth 1)
    ('cardio/index.html',                           1),
    ('ATB/index.html',                              1),
    ('OTC/index.html',                              1),
    ('respiratorio/index.html',                     1),
    ('SNC/index.html',                              1),
    ('mujer/index.html',                            1),
    ('dermatologia/dermato_dashboard.html',         1),
    ('dermatologia/competidores.html',              1),
    ('dermatologia/dermato_ddd.html',               1),
    # DDD (depth 2)
    ('cardio/DDD/index.html',                       2),
    ('ATB/DDD/index.html',                          2),
    ('OTC/DDD/index.html',                          2),
    ('respiratorio/DDD/index.html',                 2),
    ('mujer/DDD/index.html',                        2),
    ('SNC/DDD/psq_ddd.html',                        2),
    # Competidores (depth 2)
    ('cardio/DDD/competidores.html',                2),
    ('ATB/DDD/competidores.html',                   2),
    ('OTC/DDD/competidores.html',                   2),
    ('respiratorio/DDD/competidores.html',          2),
    ('mujer/DDD/competidores.html',                 2),
    ('SNC/DDD/competidores.html',                   2),
]

# Assets compartidos a inyectar (relative paths se computan por depth)
SHARED_CSS = [
    'shared/design-tokens.css',
    'shared/microinteractions.css',
    'shared/responsive.css',
]
SHARED_JS = [
    'shared/ux-shared.js',
]

MARKER = '<!-- sie-ux-shared -->'


def rel_path(asset, depth):
    """asset='shared/microinteractions.css', depth=2 -> '../../shared/microinteractions.css'"""
    return '../' * depth + asset if depth > 0 else './' + asset


def build_block(depth):
    """Build the HTML block to inject (CSS links + JS scripts)."""
    parts = [MARKER]
    for asset in SHARED_CSS:
        parts.append(f'<link rel="stylesheet" href="{rel_path(asset, depth)}">')
    for asset in SHARED_JS:
        parts.append(f'<script src="{rel_path(asset, depth)}" defer></script>')
    return '\n'.join(parts)


def patch_file(path, depth):
    p = REPO / path
    if not p.exists():
        return 'NOT EXISTS'
    t = p.read_text(encoding='utf-8', errors='replace')

    # Idempotency: remove old block if present, then re-insert with current paths
    old_block = re.search(
        rf'{re.escape(MARKER)}.*?(?=</head>|<!--|<link|<script|<title|<meta|<style)',
        t, re.DOTALL
    )
    if old_block:
        # Find old block end: stop right before next tag, but keep trailing whitespace tight
        end = old_block.end()
        # Be more precise: end is the position before next non-whitespace
        block_text = old_block.group(0)
        # Re-find with stricter pattern to capture only our block
        precise = re.search(
            rf'{re.escape(MARKER)}\n(?:<link[^>]*?>\n?)*(?:<script[^>]*?></script>\n?)*',
            t, re.DOTALL
        )
        if precise:
            t = t[:precise.start()] + t[precise.end():]

    if '</head>' not in t:
        return 'NO </head>'

    block = build_block(depth) + '\n'
    new_t = t.replace('</head>', f'{block}</head>', 1)

    if new_t == t:
        return 'no-change'

    if not DRY:
        p.write_text(new_t, encoding='utf-8', newline='')
    return 'OK'


def main():
    if DRY:
        print('[DRY RUN]')
    print(f'Inyectando UX shared assets en {len(TARGETS)} paginas...')
    print()
    ok = 0
    for path, depth in TARGETS:
        result = patch_file(path, depth)
        marker = 'OK' if result == 'OK' else result
        print(f'  [d={depth}] {path}: {marker}')
        if result == 'OK':
            ok += 1
    print()
    print(f'TOTAL: {ok}/{len(TARGETS)} files patched')


if __name__ == '__main__':
    main()
