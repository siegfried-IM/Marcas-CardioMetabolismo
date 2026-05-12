#!/usr/bin/env python3
"""Quitar entries de stock con stock=0 ventas=0 (placeholders sin data real)
para Mar/Apr 2026 en OTC. Similar al fix de SNC commit 1cfa052."""
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def patch(line_key, months_check):
    p = REPO / line_key / 'data.js'
    t = p.read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    if not m: return
    ob = t.index('{', m.end())
    d2, end = json.JSONDecoder().raw_decode(t[ob:])
    prefix = t[:ob]; suffix = t[ob+end:]
    stock = d2.get('stock', {})
    removed = 0
    for fam, months in stock.items():
        if not isinstance(months, dict): continue
        for mk in months_check:
            if mk in months:
                e = months[mk]
                if not isinstance(e, dict): continue
                stk = e.get('stock', 0) or 0
                vts = e.get('ventas', 0) or 0
                if stk == 0 and vts == 0:
                    del months[mk]
                    removed += 1
                    print(f'  {line_key} {fam} {mk}: removed (placeholder stock=0 ventas=0)')
    print(f'{line_key}: {removed} entries removidas')
    p.write_text(prefix + json.dumps(d2, ensure_ascii=False) + suffix, encoding='utf-8', newline='')

if __name__ == '__main__':
    patch('OTC', ['Mar 2026', 'Apr 2026'])
