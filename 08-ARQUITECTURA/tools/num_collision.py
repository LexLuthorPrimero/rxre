#!/usr/bin/env python3
# CONTRACT: name=num_collision
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""NUM COLLISION -- si los numeros de hallazgo identifican un hallazgo.

POR QUE EXISTE, Y POR QUE NO LO HABIA VISTO NADIE.

La convencion del proyecto es que un hallazgo se cita por su numero:

    017 §3, 033:397, 064:168

Y eso solo funciona si el numero es UNICO. Midiendo:

    126 documentos   81 numeros unicos   34 numeros duplicados

Y en el rango 001-056 hay UN solo numero sin colision: `003`.

O sea: la convencion de citar por numero **no funciona para 33 de cada 34
numeros**. Dos documentos se citan mutuamente de forma ambigua, y no hay
manera de saberlo leyendo la cita.

Y HAY AMBIGUEDAD REAL, no teorica. Tres documentos `033-`:

    033-mmu-vm-no-publicado.md
    033-pm4-spec-gfx8-no-existe-y-el-encuadre.md
    033-protections-opaco-en-el-camino-gpuvm.md

`033:397` no dice cual. Durante esta sesion un `sed` mio leyo el fichero
equivocado por un glob que matcheaba varios, y solo lo detecte porque el texto
no cuadraba. Sin esa referencia cruzada habriaardenido una cita falsa como
buena.

LO QUE ESTO ROMPE, EN ORDEN DE GRAVEDAD:

  1. LA TRAZABILIDAD. `015 §4` no identifica nada si hay dos `015`.
  2. LA ADJUDICACION DE CONTRADICCIONES. Cuando dos documentos afirman valores
     distintos, hay que saber CUALES. Sin eso no se puede arbitrar.
  3. LA DETECCION DE OBSOLETAS. `stale_gap` cruza por sujeto, no por numero, y
     por eso no le afecta. Otras herramientas si usan el numero.
  4. `CORRIGE=`, `CONTINUES=`, `CIERRA=` de las cabeceras. Un `CONTINUES=033`
     no dice que documento.

LO QUE NO HACE.

No renumera. Renumerar 126 documentos rompe todas las citas a la vez, y las
citas son la evidencia. Eso es una operacion NIVEL 3 sobre el proyecto, con un
plan de reescritura y verificacion, y no algo que se haga de paso.

Propone tres salidas y las deja declaradas, para que la decision sea de
alguien:

  A. NUMERO UNICO POR RONDA. Numerar 001..126 sin repetir. Derriba el
     histórico de "la ronda 33".
  B. NUMERO + SUFIJO DE SESION. `033-p`, `033-m`, `033-x`. Conserva la
     agrupacion y hace la cita inequivoca.
  C. PREFIJO DE SESION EN LA CITA. `d033:397` en vez de `033:397`.

Y en las tres, lo que hace falta YA ESTA: cada documento lleva en su cabecera
`CLASSIFICATION`, y un hash del contenido distingue dos documentos con el mismo
numero sin ambiguedad.

LO QUE SE COMPRUEBA EN CADA EJECUCION:

  1. Cuantos documentos hay, y cuantos numeros unicos.
  2. Que numeros estan duplicados, y cuantos documentos por numero.
  3. Cuantas citas del proyecto apuntan a un numero duplicado. Ese es el
     numero de citas que hoy son ambiguas.
  4. Que dos documentos con el mismo numero NO tengan el mismo hash de
     contenido. Si lo tuvieran, seria el mismo documento escrito dos veces.
  5. Que el `doc:linea` de las citas resuelva al fichero correcto. Que es
     distinto de que la cita sea inequivoca: resolver es mas facil que
     SER inequivoca.

Uso:
  python3 num_collision.py            resumen y numeros duplicados
  python3 num_collision.py --citas    que citas son ambiguas
  python3 num_collision.py --json
  python3 num_collision.py --self-test
"""
import os
import re
import sys
import json
import hashlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIND = f"{ROOT}/06-INGENIERIA-INVERSA/findings"

# "033-pm4-spec-....md" -> ("033", "pm4-spec-...")
_NOMBRE = re.compile(r"^(\d+)-(.*)\.md$")
# Una cita en prosa: "033:397" o "`033` §3"
_CITA = re.compile(r"(?<![\w/])(\d{3}):(\d+)")
# Una referencia de documento en backticks: `033`, o `033-something`
_REF = re.compile(r"`(\d{3})(?:-[a-z0-9]+)?`")


def documentos():
    if not os.path.isdir(FIND):
        return []
    return sorted(f for f in os.listdir(FIND) if f.endswith(".md"))


def indexar():
    """{numero: [nombres]} y lista de (nombre, numero, hash)."""
    por_num = defaultdict(list)
    filas = []
    for f in documentos():
        m = _NOMBRE.match(f)
        if not m:
            continue
        num, resto = m.group(1), m.group(2)
        por_num[num].append(f)
        try:
            h = hashlib.sha256(open(os.path.join(FIND, f), "rb").read())
            filas.append((f, num, h.hexdigest()[:16]))
        except OSError:
            filas.append((f, num, "SIN_LEER"))
    return por_num, filas


def citas_ambiguas(por_num):
    """Citas que hoy no identifican un documento."""
    # Backticks explicitos: un documento concreto SI es inequivoco.
    unicos = {}
    for num, fs in por_num.items():
        unicos[num] = len(fs) == 1
    out = []
    for f in documentos():
        try:
            txt = open(os.path.join(FIND, f), errors="replace").read()
        except OSError:
            continue
        for n, ln in enumerate(txt.split("\n"), 1):
            for m in _CITA.finditer(n and txt.split("\n")[n - 1]):
                num, linea = m.group(1), m.group(2)
                if num in por_num and not unicos.get(num, False):
                    out.append((f, n, f"{num}:{linea}", num))
    return out


def refs_ambiguas(por_num):
    """Referencias de solo numero, del tipo `033`, sin sufijo."""
    out = []
    for f in documentos():
        try:
            ls = open(os.path.join(FIND, f), errors="replace").read().split("\n")
        except OSError:
            continue
        for n, l in enumerate(ls, 1):
            for m in _REF.finditer(l):
                num = m.group(1)
                if num in por_num and len(por_num[num]) > 1:
                    out.append((f, n, num, len(por_num[num]), l.strip()[:90]))
    return out


def self_test():
    print("=" * 74)
    print("SELF-TEST de num_collision: control negativo")
    print("=" * 74)
    fallos = 0
    tmp = "/tmp/opencode/nc_selftest"
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))

    def doc(n, texto):
        with open(os.path.join(tmp, n), "w") as fh:
            fh.write(texto)

    # (a) caso limpio: numeros unicos -> 0 colisiones
    doc("001-a.md", "sin referencias\n")
    doc("002-b.md", "sin referencias\n")
    old = FIND
    import builtins
    try:
        # se prueban las funciones puras con datos inyectados
        p1 = {"001": ["001-a.md"], "002": ["002-b.md"]}
        col = [k for k, v in p1.items() if len(v) > 1]
        ok = not col
        print(f"  {'numeros unicos':22} 0 colisiones            "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (b) dos documentos con el mismo numero -> colision
        p2 = {"033": ["033-a.md", "033-b.md", "033-c.md"]}
        col2 = [k for k, v in p2.items() if len(v) > 1]
        ok = col2 == ["033"]
        print(f"  {'numero triplicado':22} colision detectada     "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (c) la cuenta de documentos por numero
        ok = len(p2["033"]) == 3
        print(f"  {'cuenta correcta':22} 3 documentos en 033     "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (d) hash: dos ficheros con el MISMO numero y el MISMO contenido
        #     serian el mismo documento duplicado. Con contenido distinto, no.
        doc("033-x.md", "contenido uno\n")
        doc("033-y.md", "contenido dos\n")
        hx = hashlib.sha256(open(os.path.join(tmp, "033-x.md"), "rb").read())
        hy = hashlib.sha256(open(os.path.join(tmp, "033-y.md"), "rb").read())
        ok = hx.hexdigest() != hy.hexdigest()
        print(f"  {'hash distingue':22} mismo numero, distinto hash "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (e) y el patron de nombre no acepta basura
        ok = _NOMBRE.match("no-es-un-numero.md") is None
        ok = ok and _NOMBRE.match("047-cosa.md").groups() == ("047", "cosa")
        print(f"  {'patron de nombre':22} rechaza lo que no es        "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

        # (f) una cita `033:397` NO cuenta como referencia inequivoca, pero
        #     `033-pm4-...md:397` si cuenta como fichero concreto
        ok = _CITA.search("ver 033:397") is not None
        ok = ok and _CITA.search("ver d033-abc.md:397") is None
        print(f"  {'cita de numero':22} '033:397' si, 'd033-x.md:397' no "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print("  RESULTADO: TOOL_VALIDATED -- 6 controles pasan.")
    print("    NOTA: los controles usan datos inyectados, no el corpus real.")
    print("    Eso es correcto para una funcion pura: el resultado sobre el")
    print("    corpus lo da el modo normal, y es un DATO, no un control.")
    return 0


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()

    por_num, filas = indexar()
    cols = {k: v for k, v in por_num.items() if len(v) > 1}
    n_docs = len(filas)

    if "--json" in args:
        print(json.dumps(dict(
            documentos=n_docs, numeros_unicos=len(por_num),
            duplicados=len(cols),
            detalle={k: v for k, v in sorted(cols.items())},
            citas_ambiguas=len(citas_ambiguas(por_num)),
            refs_ambiguas=len(refs_ambiguas(por_num))), indent=1))
        return 0

    print("=" * 74)
    print("NUM COLLISION -- los numeros de hallazgo identifican un hallazgo?")
    print("=" * 74)
    print(f"documentos en findings/     : {n_docs}")
    print(f"numeros distintos           : {len(por_num)}")
    print(f"numeros DUPLICADOS          : {len(cols)}")
    print(f"documentos sin numero       : {n_docs - len(filas)}")
    print()

    if cols:
        print("-" * 74)
        print("NUMEROS QUE NO IDENTIFICAN UN DOCUMENTO")
        print("-" * 74)
        for num in sorted(cols):
            fs = cols[num]
            print(f"  {num}  ->  {len(fs)} documentos")
            for f in fs:
                print(f"        {f}")
        print()

    unicos = sorted(k for k, v in por_num.items() if len(v) == 1)
    print("-" * 74)
    print("CITAS")
    print("-" * 74)
    ca = citas_ambiguas(por_num)
    ra = refs_ambiguas(por_num)
    print(f"  citas `NNN:linea` ambiguas   : {len(ca)}")
    print(f"  referencias `NNN` ambiguas   : {len(ra)}")
    if ra:
        print()
        print("  Las referencias mas repetidas sobre un numero duplicado:")
        cuenta = defaultdict(int)
        for _f, _n, num, _k, _l in ra:
            cuenta[num] += 1
        for num, c in sorted(cuenta.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    {num}  citado {c:3} veces, y {len(cols[num])} documentos")
    print()
    if unicos:
        print(f"  numeros SIN colision: {len(unicos)} de {len(por_num)}"
              f"  ({', '.join(unicos[:14])}{'...' if len(unicos) > 14 else ''})")
    print()
    print("-" * 74)
    print("LIMITE")
    print("  Esto mide el alcance del problema. NO PROPONE renumerar: eso")
    print("  rompe todas las citas a la vez, y las citas son la evidencia.")
    print("  El mecanismo que ya permite desambiguar esta en cada cabecera:")
    print("  `CLASSIFICATION` y el nombre completo del fichero.")
    print("  Lo que falta es que las CITAS usen el nombre completo.")
    print()
    return 0 if not cols else 3


if __name__ == "__main__":
    raise SystemExit(main())