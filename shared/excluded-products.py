"""Lista canonica de productos a EXCLUIR de TODOS los analisis.

Cuando se agrega un producto aca:
1. Corre `py shared/apply-product-exclusions.py` para limpiar todos los
   archivos data (rec_comp, mol_perf, brand_monthly, etc.).
2. Corre `py shared/build-kpis.py` para regenerar kpis.json.
3. El syntax-and-consistency check va a fallar si estos productos
   reaparecen en cualquier data file -> forza a re-correr el scrub.

Match: case-insensitive, comparacion exacta del nombre 'prod' / brand key.
"""
from __future__ import annotations

# Productos excluidos forever
EXCLUDED_PRODUCTS = [
    'VIXIDONE SIE',
    'VIXIDONE LB SIE',
    'DECADRON AL SIE',
    'CALCITOL D3 (SIE)',
    'CALCITOL D3 SIE',
    'BONVIVA (SIE)',
    'BONVIVA SIE',
]

EXCLUDED_UPPER = set(p.upper() for p in EXCLUDED_PRODUCTS)


def is_excluded(name):
    """Returns True if a product name matches the exclusion list."""
    if not name:
        return False
    return str(name).strip().upper() in EXCLUDED_UPPER
