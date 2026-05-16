"""Mejora 2 — Consistencia visual:
- Reemplaza font-family 'Inter' -> 'IBM Plex Sans' en las DDD/competidores
  (las 14 paginas que hoy rompen consistencia con el hub y los dashboards
  principales).
- Corrige .pg-title{color:#ecf4ff} (color casi invisible) -> #111827 en los 7
  main dashboards. Hoy esta salvado por overrides inline; despues de este
  cambio el override inline ya no hace falta pero NO lo removemos por no
  modificar HTML existente.

Idempotente.
"""
from __future__ import annotations
from pathlib import Path
import glob

REPO = Path(__file__).resolve().parent.parent


def collect_files():
    files = set()
    for d in ['cardio', 'ATB', 'OTC', 'respiratorio', 'SNC', 'mujer', 'dermatologia']:
        for p in glob.glob(f'{REPO}/{d}/**/*.html', recursive=True):
            if Path(p).stat().st_size > 1024:
                files.add(p)
    for p in [REPO / 'index.html', REPO / 'kpis.html']:
        if p.exists():
            files.add(str(p))
    return sorted(files)


def patch_file(path):
    p = Path(path)
    t = p.read_text(encoding='utf-8', errors='replace')
    orig = t

    # 1) 'Inter' -> 'IBM Plex Sans' (mantiene fallback system-ui)
    t = t.replace("'Inter',system-ui,sans-serif", "'IBM Plex Sans',system-ui,sans-serif")
    t = t.replace("'Inter',sans-serif", "'IBM Plex Sans',sans-serif")
    t = t.replace("'Inter','IBM Plex Sans'", "'IBM Plex Sans'")
    # Por las dudas, otros casos:
    t = t.replace(",'Inter',", ",'IBM Plex Sans',")
    t = t.replace("font-family:'Inter'", "font-family:'IBM Plex Sans'")

    # 2) Color invisible #ecf4ff (heredado de un dark mode descartado)
    # Reemplazamos por sie-ink dark. Mantiene los overrides inline si existian.
    t = t.replace('color:#ecf4ff;', 'color:#111827;')

    if t == orig:
        return 'no-change'
    p.write_text(t, encoding='utf-8', newline='')
    return 'OK'


def main():
    files = collect_files()
    ok = 0
    for f in files:
        result = patch_file(f)
        if result == 'OK':
            ok += 1
            print(f'  {Path(f).relative_to(REPO)}: OK')
    print()
    print(f'TOTAL: {ok}/{len(files)} files updated')


if __name__ == '__main__':
    main()
