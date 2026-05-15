"""Aplica el mismo rediseno compacto del navbar a las paginas DDD y Competidores
para mantener consistencia con los dashboards principales.

Estrategia:
1. Restructura el HTML <nav>: deja section nav-items a la izquierda, agrupa los
   pill tabs (DDD/Comp/Bonos) en <div class="nav-actions"> a la derecha
   (margin-left:auto).
2. Inyecta un <style id="nav-compact-overrides"> antes de </head> con CSS
   override compacto (.nav-item, .nav-tab-*, .nav-actions) que aplica tanto
   a <nav class="nav"> como a <nav class="nav-unified">.

Idempotente. No toca otras secciones ni datos.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGETS = [
    # DDD pages (<nav class="nav-unified">)
    ('cardio/DDD/index.html',                 'nav-unified'),
    ('ATB/DDD/index.html',                    'nav-unified'),
    ('OTC/DDD/index.html',                    'nav-unified'),
    ('respiratorio/DDD/index.html',           'nav-unified'),
    ('mujer/DDD/index.html',                  'nav-unified'),
    ('SNC/DDD/psq_ddd.html',                  'nav-unified'),
    ('dermatologia/dermato_ddd.html',         'nav-unified'),
    # Competidores pages (<nav class="nav">)
    ('ATB/DDD/competidores.html',             'nav'),
    ('cardio/DDD/competidores.html',          'nav'),
    ('mujer/DDD/competidores.html',           'nav'),
    ('OTC/DDD/competidores.html',             'nav'),
    ('respiratorio/DDD/competidores.html',    'nav'),
    ('SNC/DDD/competidores.html',             'nav'),
    ('dermatologia/competidores.html',        'nav'),
]


OVERRIDES_CSS = """<style id="nav-compact-overrides">
/* Override compacto para que el navbar entre en una sola fila */
.nav, .nav-unified { padding:0 16px !important; }
.nav-items, .nav-unified .nav-items {
  display:flex !important; flex:1 1 auto !important; min-width:0 !important;
  overflow-x:auto !important; scrollbar-width:none !important;
}
.nav-items::-webkit-scrollbar, .nav-unified .nav-items::-webkit-scrollbar { display:none !important; }
.nav .nav-item, .nav-unified .nav-item {
  height:48px !important; padding:0 9px !important; font-size:10.5px !important;
}
.nav-back, .nav-unified .nav-back { padding:5px 10px !important; margin-right:10px !important; font-size:10px !important; }
.nav-logo, .nav-unified .nav-logo {
  width:auto !important; height:auto !important; background:transparent !important;
  border-radius:6px !important; overflow:visible !important;
  margin-right:12px !important; padding:4px 6px !important;
  display:inline-flex !important; align-items:center !important;
}
.nav-actions {
  display:flex !important; align-items:center !important; gap:5px !important;
  margin-left:auto !important; flex-shrink:0 !important; padding-left:8px !important;
}
.nav-actions .nav-tab-ddd, .nav-actions .nav-tab-comp, .nav-actions .nav-tab-bonos,
.nav .nav-tab-ddd, .nav .nav-tab-comp, .nav .nav-tab-bonos,
.nav-unified .nav-tab-ddd, .nav-unified .nav-tab-comp, .nav-unified .nav-tab-bonos {
  height:28px !important; padding:0 10px !important; font-size:10.5px !important;
  margin:0 !important; align-self:center !important;
}
</style>"""


def restructure_nav(t, nav_class):
    """Restructure nav: move tab pills into <div class="nav-actions">."""
    pat = re.compile(rf'<nav class="{re.escape(nav_class)}">(.*?)</nav>', re.DOTALL)
    m = pat.search(t)
    if not m:
        return t, 'no-nav'
    nav_inner = m.group(1)

    # Idempotency
    if 'class="nav-actions"' in nav_inner:
        return t, 'already-restructured'

    # Extract: nav-back, nav-logo, nav-items (sections + tabs)
    m_back = re.search(r'<a class="nav-back"[^>]*>.*?</a>', nav_inner, re.DOTALL)
    m_logo = re.search(r'<a class="nav-logo"[^>]*>.*?</a>', nav_inner, re.DOTALL)
    m_items = re.search(r'<div class="nav-items">(.*?)</div>', nav_inner, re.DOTALL)
    if not (m_back and m_logo and m_items):
        return t, 'missing-parts'

    items_inner = m_items.group(1)
    # Section items (any href; distinguished from tabs by class)
    section_items = re.findall(
        r'<a class="nav-item(?:\s+on)?" href="[^"]*"[^>]*>.*?</a>',
        items_inner, re.DOTALL
    )
    # Tab pills: nav-tab-ddd, nav-tab-comp, nav-tab-bonos
    tab_pills = re.findall(
        r'<a class="nav-tab-(?:ddd|comp|bonos)"[^>]*>.*?</a>',
        items_inner, re.DOTALL
    )
    if not section_items:
        return t, 'no-section-items'

    sections_html = '\n    '.join(section_items)
    tabs_html = '\n    '.join(tab_pills)

    new_inner = f"""
  {m_back.group(0)}
  {m_logo.group(0)}
  <div class="nav-items">
    {sections_html}
  </div>
  <div class="nav-actions">
    {tabs_html}
  </div>
"""
    new_nav = f'<nav class="{nav_class}">{new_inner}</nav>'
    return t[:m.start()] + new_nav + t[m.end():], 'restructured'


def inject_overrides(t):
    """Inject (or replace) <style id="nav-compact-overrides"> before </head>."""
    # Idempotent replace: if block already exists, swap with current OVERRIDES_CSS
    existing = re.search(r'<style id="nav-compact-overrides">.*?</style>', t, re.DOTALL)
    if existing:
        if existing.group(0).strip() == OVERRIDES_CSS.strip():
            return t, 'already-injected'
        return t[:existing.start()] + OVERRIDES_CSS + t[existing.end():], 'updated'
    if '</head>' not in t:
        return t, 'no-head'
    return t.replace('</head>', f'{OVERRIDES_CSS}\n</head>', 1), 'injected'


def patch_file(path, nav_class):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')
    t1, nav_status = restructure_nav(t, nav_class)
    t2, css_status = inject_overrides(t1)
    if t2 == t:
        return f'no-op ({nav_status}, {css_status})'
    p.write_text(t2, encoding='utf-8', newline='')
    return f'OK ({nav_status}, {css_status})'


def main():
    for path, nav_class in TARGETS:
        print(f'  {path}: {patch_file(path, nav_class)}')


if __name__ == '__main__':
    main()
