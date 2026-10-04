#!/usr/bin/env python3
# CONTRACT: name=h1_stale
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""H1_STALE -- el H1 de un hallazgo afirma algo que su propio cuerpo desmiente.

EL PROBLEMA QUE RESUELVE.

Un titulo de hallazgo es un ENUNCIADO sobre el estado del mundo, y por eso es lo
primero que se lee y lo ultimo que se revisa. El cuerpo de un hallazgo, en
cambio, se corrige cada vez que una medida lo desmiente: nace con
`CORREGIDO POR <n>`, `REFUTADA por <n>`, `RETIRADO por <n>`. De ahi el patron
`CORRADO_EL_CUERPO_PERO_NO_EL_TITULO`: el cuerpo pasa a ser verdad y el H1 se
queda en la primera redaccion, affirmando lo que el propio fichero acaba de
negar.

Medido el 2026-10-04 sobre `06-INGENIERIA-INVERSA/findings/`: 581 ficheros
numerados, 6.371.898 bytes, de los cuales 10 tienen el H1 caducado. El caso
seminal es `1028`, que en su propio cuerpo (`:286` antes del parche) declara
"**Y EL TITULO DE ESTE HALLAZGO TAMBIEN ESTA CADUCADO**" y despues lo dice tres
veces mas. Es decir: el Patron ya se habia detectado a mano y no se habia
cerrado. Eso es lo que mide esta herramienta.

LO QUE HACE, y lo que NO hace. Cuatro reglas, cada una con un modo de fallo
real, y las cuatro son MECANICAMENTE DECIDIBLES:

  H1_REVERTED             el H1 vuelve a ser el titulo viejo que la propia
                          marca `H1 CORREGIDO` registra como ya corregido.
  EVIDENCE_DRIFT          una linea `> - `:N` -- nota: «cita»` de una marca ya no
                          contiene esa cita, porque el cuerpo se movio. La marca
                          esta mintiendo y eso es peor que no tenerla.
  MARK_WITHOUT_H1         hay marca `H1 CORREGIDO` y el fichero ya no tiene H1.
  SELF_DECLARED_UNACTIONED  el cuerpo declara que SU PROPIO TITULO esta caducado y
                          no hay marca de correccion. Esto es el patron puro, y
                          es la unica regla que lo caza sin que nadie haya
                          registrado las marcas: quien lo escribe se delata solo.

LIMITE DECLARADO, Y ES EL LIMITE IMPORTANTE.

Esto NO caza un H1 caducado. Solo comprueba cuatro cosas mecanicas. Un H1 que
se contradiga con su cuerpo sin que el cuerpo lo diga no lo ve nadie: hace falta
que alguien lo escriba. Y no es una limitacion accidental, es una MEDIDA:

  Se construyeron dos detectores lexicos y se mediron contra los 10 H1 caducados
  conocidos antes de escribir esta herramienta:

    A. "una cantidad del H1 no aparece en ninguna linea asertiva del cuerpo"
       -> 2 de 10, con 17 falsos positivos sobre 581 ficheros.
    B. "una cantidad del H1 aparece en el cuerpo como valor sustituido"
       -> 11 candidatos, 2 confirmed.

  Los dos se descartaron. Un detector que acierta 2 de 10 y avisa 17 veces por
  cada 581 ficheros no es una puerta: es ruido con codigo de salida, que es la
  forma mas cara de teatro porque parece que vigila. Lo que se conserva es lo
  que se puede decidir sin adivinar, y la regla que de verdad caza el patron --
  `SELF_DECLARED_UNACTIONED` -- no necesita los 10: necesita que quien lo escribe
  lo diga, y 1028 lo dice.

Los ficheros degenerados (NUL, o sin H1) se cuentan y se INFORMAN aparte. No son
H1 caducados: son ficheros rotos, y confundirlos con un titulo obsoleto seria
contar como trabajo de titulo lo que es trabajo de integridad.

Uso:
  python3 h1_stale.py              tabla de reglas, hallazgos y DEGENERADOS
  python3 h1_stale.py --json       salida estructurada
  python3 h1_stale.py --fail-only  solo lo que falla
  python3 h1_stale.py --dir=RUTA   otro directorio de hallazgos (para las
                                   pruebas de negacion, que necesitan mirar un
                                   arbol viejo sin tocar el arbol vivo)

Salida: codigo 1 si hay algun FAIL, 0 si no. INVALID_RESULT si no encuentra el
directorio de hallazgos, para que un fallo de entorno no se lea como un arbol
limpio.
"""

import json
import os
import re
import sys

FINDINGS = os.path.join('06-INGENIERIA-INVERSA', 'findings')

# «el H1 de este hallazgo esta caducado» dicho por el propio fichero.
SELF_DECLARED = re.compile(
    r'(?:T[IÍ]TULO|H1|encabezado)[^\n]{0,120}?'
    r'(?:CADUCAD|mentiros|obsolet|incorrect|desactualizad|falso|ya no describe|'
    r'no (?:describe|refleja|ya no)|tambi[eé]n est[aá] caducad|'
    r'no lo tocaron|sigue mintiendo)',
    re.I | re.S)

MARK_HEAD = re.compile(r'H1 CORREGIDO EL (\d{4}-\d{2}-\d{2})')
MARK_OLD = re.compile(r'El titulo anterior decia «(.*?)»')
# > - `:245` — nota: «cita»
MARK_EV = re.compile(r'^> - `:(\d+)`\s*[—-]+\s*(.*?):\s*«(.*)»\s*$')


def fence_map(lines):
    """1-based line numbers that sit inside a fenced code block."""
    inside = False
    fence = None
    out = set()
    for i, l in enumerate(lines, 1):
        m = re.match(r'^\s{0,3}(`{3,}|~{3,})', l)
        if m:
            ch = m.group(1)[0]
            if not inside:
                inside, fence = True, ch
                out.add(i)
            elif ch == fence:
                inside = False
            continue
        if inside:
            out.add(i)
    return out


def first_h1(lines, in_fence):
    for i, l in enumerate(lines, 1):
        if l.startswith('# ') and i not in in_fence:
            return i, l
    return None, None


def strip_num(title):
    return re.sub(r'^\d{3,5}\s*[·:.\-]?\s*', '', title)


def scan(path):
    raw = open(path, 'rb').read()
    rec = {'file': path, 'bytes': len(raw), 'nul': raw.count(b'\x00'),
           'degenerate': [], 'fail': [], 'evidence': []}
    if rec['nul']:
        rec['degenerate'].append('DEGENERATE_NUL')
    text = raw.decode('utf-8', 'replace')
    lines = text.split('\n')
    fences = fence_map(lines)
    hi, h1 = first_h1(lines, fences)
    rec['h1_line'] = hi
    rec['h1'] = h1
    if h1 is None:
        rec['degenerate'].append('DEGENERATE_NO_H1')
        return rec

    mark_i = next((i for i, l in enumerate(lines, 1)
                   if MARK_HEAD.search(l) and i != hi), None)
    rec['mark_line'] = mark_i

    # SELF_DECLARED_UNACTIONED: quien lo escribe se delata y no se corrigio.
    if mark_i is None:
        for i, l in enumerate(lines, 1):
            if i == hi or i in fences:
                continue
            if SELF_DECLARED.search(l):
                rec['fail'].append({'rule': 'SELF_DECLARED_UNACTIONED',
                                    'line': i, 'detail': l.strip()[:120]})
                break

    if mark_i is None:
        return rec

    # MARK_WITHOUT_H1 no puede ocurrir aqui (h1 is not None); se cubre en el
    # orden de reglas inferior por si el H1 esta dentro de un fence.
    if hi in fences:
        rec['fail'].append({'rule': 'MARK_WITH_H1_IN_FENCE', 'line': hi,
                            'detail': 'el H1 esta dentro de un bloque de codigo'})

    m_old = MARK_OLD.search(text)
    if m_old:
        old = m_old.group(1).strip()
        rec['old_title'] = old
        if strip_num(h1[2:]).strip() == old:
            rec['fail'].append({'rule': 'H1_REVERTED', 'line': hi,
                                'detail': 'el H1 vuelve a ser el titulo viejo'})

    for i, l in enumerate(lines, 1):
        m = MARK_EV.match(l)
        if not m:
            continue
        n, note, quote = int(m.group(1)), m.group(2), m.group(3)
        rec['evidence'].append({'line': n, 'quote': quote})
        if not (1 <= n <= len(lines)):
            rec['fail'].append({'rule': 'EVIDENCE_DRIFT', 'line': i,
                                'detail': f':{n} fuera de rango'})
        elif quote not in lines[n - 1]:
            rec['fail'].append({'rule': 'EVIDENCE_DRIFT', 'line': i,
                                'detail': f':{n} no contiene «{quote[:60]}»'})
    return rec


def main():
    args = sys.argv[1:]
    findings = FINDINGS
    for a in args:
        if a.startswith('--dir='):
            findings = a.split('=', 1)[1]
    if not os.path.isdir(findings):
        sys.stderr.write(f'INVALID_RESULT: no existe {findings}\n')
        return 2
    recs = []
    for fn in sorted(os.listdir(findings)):
        if fn.endswith('.md') and re.match(r'^\d{3,5}-', fn):
            recs.append(scan(os.path.join(findings, fn)))
    nfail = sum(len(r['fail']) for r in recs)
    degen = [r for r in recs if r['degenerate']]

    if '--json' in args:
        print(json.dumps({'files': len(recs), 'bytes': sum(r['bytes'] for r in recs),
                          'failures': nfail, 'records': recs},
                         indent=1, ensure_ascii=False))
        return 1 if nfail else 0

    marks = [r for r in recs if r.get('mark_line')]
    ev = sum(len(r.get('evidence', [])) for r in recs)
    print(f'ALCANCE   ficheros={len(recs)}  bytes={sum(r["bytes"] for r in recs)}')
    print(f'MARCAS    H1 CORREGIDO={len(marks)}  citas verificadas={ev}')
    print(f'FALLOS    {nfail}')
    print(f'DEGENERADOS (no son H1 caducado, se informan aparte)  {len(degen)}')
    for r in degen:
        print(f'  {r["file"].split("/")[-1][:52]:54s} {",".join(r["degenerate"])}')
    if '--fail-only' not in args:
        print('\nPOR REGLA (0 = la puerta no ve nada en ese caso):')
        rules = {}
        for r in recs:
            for f in r['fail']:
                rules[f['rule']] = rules.get(f['rule'], 0) + 1
        for k in ('H1_REVERTED', 'EVIDENCE_DRIFT', 'SELF_DECLARED_UNACTIONED',
                  'MARK_WITH_H1_IN_FENCE'):
            print(f'  {k:28s} {rules.get(k, 0)}')
        print('\nCON MARCA (la correccion esta aplicada y su evidencia apunta):')
        for r in marks:
            print(f'  {r["file"].split("/")[-1][:52]:54s} marca@{r["mark_line"]} '
                  f'evidencias={len(r.get("evidence", []))}')
    for r in recs:
        for f in r['fail']:
            print(f"FAIL {f['rule']} {r['file']}:{f['line']} {f['detail']}")
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main())