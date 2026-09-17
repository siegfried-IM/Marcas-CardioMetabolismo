# -*- coding: utf-8 -*-
"""Gate: que el JS no toque nodos que la pagina no tiene.

POR QUE EXISTE (2026-09-17). Se saco de las 7 paginas el panel "Top competidores
por recetas" pero quedo viva esta linea en renderRec():

    document.getElementById('rec-comp-table').innerHTML = '...';

en la rama que corre cuando la marca activa NO tiene base CloseUp. Esa rama no se
ejecuta con las marcas que uno prueba a mano, asi que el tablero abria bien y el
error solo aparecia al elegir una marca sin recetas: TypeError, y se cortaba el
render de toda la seccion. Lo mismo puede pasar con cualquier rama de "sin datos",
"sin base", "sin match" -las ramas vacias, que son justo las que nadie prueba-.

QUE MIRA. Por cada `getElementById('X')` / `querySelector('#X')` cuyo id X no
aparece en NINGUN lado de la pagina (ni en el markup ni dentro de un template de
JS que lo genere):

  FALLA  si el resultado se desreferencia de una (`.algo` o `[...]`) y nada lo
         protege -> TypeError seguro en cuanto esa rama corra.
  avisa  si esta protegido. Tres formas de proteccion, las tres reales en este
         repo: early-return sobre el mismo id; la variable asignada y chequeada;
         y early-return sobre OTRO id que tambien falta, que deja la funcion
         entera inalcanzable (renderPrec() de SNC guarda por prec-pills y adentro
         usa prec-content: no existe ninguno de los dos, nunca llega). Eso no
         rompe, pero es codigo muerto y se informa al final.

LIMITE DECLARADO: es analisis de texto, no ejecuta la pagina. No ve un id armado
por concatenacion (getElementById('x'+i)); esos se cuentan aparte. Cubre la
familia de fallas que aparecio de verdad, no todas las posibles.

Uso: py shared/check-dom-refs-vivas.py [--verbose]
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUIR = {'worktrees', 'node_modules', '__pycache__', '.git'}

Q = "[\"']"                                   # comilla simple o doble
ID = "[A-Za-z0-9_-]+"

RE_GEBI = re.compile(r"getElementById\(\s*%s(%s)%s\s*\)(\s*[.\[])?" % (Q, ID, Q))
RE_QS = re.compile(r"querySelector\(\s*%s#(%s)%s\s*\)(\s*[.\[])?" % (Q, ID, Q))
RE_DINAMICO = re.compile(r"(?:getElementById|querySelector)\(\s*[^\"')][^)]*\)")
RE_FUN = re.compile(
    r"^\s*(?:function\s+\w+\s*\(|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?function\b"
    r"|(?:const|let|var)\s+\w+\s*=\s*\()", re.M)
RE_ID_DECL = re.compile(r"\bid\s*=\s*%s([^\"']+)%s" % (Q, Q))
RE_ID_TMPL = re.compile(r"\bid\s*=\s*%s(%s)\$\{" % (Q, ID))


def ids_presentes(txt):
    """Todo id declarado, tanto en el markup como dentro de los templates de JS
    que generan HTML (por eso se busca en el texto entero, no solo en el <body>)."""
    out = {m.group(1).strip() for m in RE_ID_DECL.finditer(txt)}
    out |= {m.group(1) for m in RE_ID_TMPL.finditer(txt)}   # id="x${i}" -> prefijo
    return out


def inicio_de_funcion(txt):
    inicios = [m.start() for m in RE_FUN.finditer(txt)]
    def de(pos):
        ant = [i for i in inicios if i < pos]
        return ant[-1] if ant else 0
    return de


def protegido(txt, ini, pos, ident, faltantes):
    tramo = txt[ini:pos]
    pat = r"if\s*\(\s*!\s*document\.getElementById\(\s*%s(%s)%s\s*\)\s*\)\s*return" % (Q, ID, Q)
    for m in re.finditer(pat, tramo):
        g = m.group(1)
        if g == ident or g in faltantes:
            return True
    asig = r"(?:const|let|var)\s+(\w+)\s*=\s*document\.getElementById\(\s*%s%s%s\s*\)" % (
        Q, re.escape(ident), Q)
    for m in re.finditer(asig, tramo):
        v = re.escape(m.group(1))
        resto = tramo[m.end():]
        if re.search(r"if\s*\(\s*!\s*%s\s*\)\s*(?:return|\{)" % v, resto):
            return True
        if re.search(r"if\s*\(\s*%s\s*\)" % v, resto):
            return True
    return False


def analizar(p):
    txt = p.read_text(encoding='utf-8', errors='replace')
    presentes = ids_presentes(txt)
    usos = [m for rx in (RE_GEBI, RE_QS) for m in rx.finditer(txt)
            if m.group(1) not in presentes]
    faltantes = {m.group(1) for m in usos}
    de = inicio_de_funcion(txt)
    crash, muertas = [], []
    for m in usos:
        ident = m.group(1)
        linea = txt.count(chr(10), 0, m.start()) + 1
        if m.group(2) and not protegido(txt, de(m.start()), m.start(), ident, faltantes):
            crash.append((linea, ident))
        else:
            muertas.append((linea, ident))
    return crash, muertas, len(RE_DINAMICO.findall(txt))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    verbose = '--verbose' in sys.argv
    paginas = sorted(q for q in REPO.rglob('*.html')
                     if not (EXCLUIR & set(q.relative_to(REPO).parts)))
    if not paginas:
        print('SKIP  no se encontro ninguna pagina html')
        return 2

    n_fail = n_pass = tot_crash = tot_muertas = tot_din = 0
    con_muertas = []
    for p in paginas:
        rel = p.relative_to(REPO).as_posix()
        crash, muertas, din = analizar(p)
        tot_crash += len(crash); tot_muertas += len(muertas); tot_din += din
        if muertas:
            con_muertas.append((rel, len(muertas)))
        if crash:
            n_fail += 1
            print('FAIL  %-42s %d desreferencia(s) a nodo inexistente' % (rel, len(crash)))
            for ln, i in crash:
                print('        L%-6d getElementById("%s").<algo>  -> TypeError cuando corra esa rama'
                      % (ln, i))
        else:
            n_pass += 1
            if verbose:
                print('PASS  %-42s sin desreferencias rotas' % rel)

    if con_muertas:
        print()
        print('  referencias muertas (no rompen; el id no existe en la pagina):')
        for rel, n in sorted(con_muertas, key=lambda x: -x[1]):
            print('    %-44s %d' % (rel, n))

    print()
    print('=' * 70)
    print('check-dom-refs-vivas: %d PASS  %d FAIL  0 SKIP' % (n_pass, n_fail))
    print('  paginas revisadas ......... %d' % len(paginas))
    print('  desreferencias rotas ...... %d' % tot_crash)
    print('  referencias muertas ....... %d' % tot_muertas)
    print('  selectores dinamicos ...... %d (no verificables por texto)' % tot_din)
    print('=' * 70)
    return 1 if n_fail else 0


if __name__ == '__main__':
    sys.exit(main())
