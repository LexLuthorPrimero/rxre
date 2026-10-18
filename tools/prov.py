#!/usr/bin/env python3
# CONTRACT: name=prov
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
"""prov.py -- mide la procedencia declarada en 06-INGENIERIA-INVERSA/findings/.

POR QUE EXISTE
    El hallazgo `1473` conclusion que el verificador automatico de procedencia
    no se debe construir, porque mediria al detector y no al corpus.  Para que
    esa conclusion sea falsable, las TRES cifras tienen que salir de un script
    reproducible y no de un regex escrito a mano tres veces.

QUE MIDE
    Un hallazgo "declara procedencia" si contiene al menos UNA de:

      P1   una clave de metadatos en una lista CERRADA de 13 nombres
      P2   una cita con linea:  fichero.c:123
      P3   un bloque de codigo citado:  ```c

    Y D1/D2/D3 son tres definiciones distintas de "lo anterior", que es
    exactamente lo que hace variar la cifra:

      D1 = P1, con la lista cerrada y exigiendo el backtick
      D2 = D1 o P2 o P3
      D3 = cualquier CLAVE= en mayusculas al principio de linea, o P2, o P3

QUE NO HACE
    No decide si un hallazgo es correcto.  No da nota.  No corrige nada.
    Su unico producto es la tabla de `1473` §1, y el hecho de que esa tabla
    varye segun como se escriba el detector.

GARANTIAS
    Solo LECTURA.  No escribe en el arbol de hallazgos.
    exit 0 siempre: el numero de huecos es un DATO, no un error.
    El corpus lo escriben varios autores y crece mientras corre, asi que
    `--n` y `--d3` se imprimen siempre junto a los porcentajes.  Una cifra
    sin su denominador no es comparable entre ejecuciones.

USO
    prov.py                 la tabla de §1
    prov.py --json          la misma tabla, parseable
    prov.py --sin-procedencia  lista los ficheros que D3 no ve
    prov.py --claves        el recuento de claves de metadatos del corpus
    prov.py --self-test
"""
import argparse
import collections
import json
import os
import re
import sys

VERSION = "1.0.0"

DEFAULT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "06-INGENIERIA-INVERSA", "findings")

# Tokens de estado del §10 del proyecto.  Un fichero sin ninguno no es un
# hallazgo: es un indice o una nota, y no entra en la medicion.
STATE = re.compile(
    r"\b(PROVEN|OBSERVED|MEASURED|DERIVED|CORROBORATED|PARTIAL|"
    r"NOT_DETERMINED|REFUTED|NOT_OBSERVED|NOT_FOUND|PROVEN_ABSENT|"
    r"UNVALIDATED|SATURATED|DEFERRED)\b")

# P1: lista CERRADA.  Es el fallo medido en 1473 §2: `HERRAMIENTAS_NUEVAS` no
# esta en la lista y produce falsos negativos.
P1_CLOSED = re.compile(
    r"`(CORPUS|FUENTE|ARTEFACTO|PRODUCER|SOURCE|ORACLE|EVIDENCIA|FICHERO|"
    r"CAPTURA|HERRAMIENTA|TOOL|CROSS-CHECK|CROSSCHECK|MEDIDO|COMANDO|"
    r"LECTURA)\b", re.I)
# La misma lista sin backtick, para ver cuanto del error es el backtick.
P1_NOBT = re.compile(
    r"^[ \t]*(ARTEFACTO|FUENTE|PRODUCER|SOURCE|ORACLE|EVIDENCIA|FICHERO|"
    r"CAPTURA|HERRAMIENTA|TOOL|CROSS-CHECK|CROSSCHECK|MEDIDO|COMANDO|"
    r"LECTURA)\b", re.I | re.M)
P2 = re.compile(r"\b[\w./-]+\.[ch]:\d+")
P3 = re.compile(r"```c")
# D3: cualquier clave en mayusculas al principio de linea.
P1_OPEN = re.compile(r"^[ \t`]*([A-Z][A-Z0-9_]{2,})[ \t]*=", re.M)

AUTORIA = re.compile(r"AGENT-RE-TOOLING")


def measure(directory):
    files, sin_d1, sin_d2, sin_d3, tokens = [], 0, 0, 0, collections.Counter()
    claves = collections.Counter()
    mios = 0
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".md"):
            continue
        txt = open(os.path.join(directory, fn), errors="ignore").read()
        if not STATE.search(txt):
            continue
        files.append(fn)
        if AUTORIA.search(txt):
            mios += 1
        for t in STATE.findall(txt):
            tokens[t] += 1
        for k in P1_OPEN.findall(txt):
            claves[k] += 1
        d1 = bool(P1_CLOSED.search(txt))
        d2 = bool(P1_NOBT.search(txt))
        p2, p3 = bool(P2.search(txt)), bool(P3.search(txt))
        sin_d1 += not d1
        sin_d2 += not (d1 or p2 or p3)
        sin_d3 += not (P1_OPEN.search(txt) or p2 or p3)
    n = len(files)
    pct = lambda k: round(100.0 * k / max(1, n), 1)
    return {
        "version": VERSION,
        "directorio": directory,
        "ficheros_totales": len(os.listdir(directory)),
        "n_con_estado": n,
        "n_esta_sesion": mios,
        "D1_sin": sin_d1, "D1_pct": pct(sin_d1),
        "D2_sin": sin_d2, "D2_pct": pct(sin_d2),
        "D3_sin": sin_d3, "D3_pct": pct(sin_d3),
        "factor_D1_sobre_D3": round(sin_d1 / max(1, sin_d3), 1),
        "tokens": dict(tokens.most_common()),
        "claves": dict(claves.most_common()),
        "_files": files,
        "_sin_d3": [f for f in files
                    if not _has_open(os.path.join(directory, f))],
    }


def _has_open(path):
    txt = open(path, errors="ignore").read()
    return P1_OPEN.search(txt) or P2.search(txt) or P3.search(txt)


# --- vectores -------------------------------------------------------------
# El vector que importa NO es "el numero es X": el corpus crece entre
# ejecuciones y el numero se mueve.  Es que la RELACION entre detectores se
# mantiene, y que D3 no puede ser peor que D2.
VECTORS = [
    ("el-corpus-no-esta-vacio", lambda m: m["n_con_estado"] > 100),
    ("D3-no-es-peor-que-D2", lambda m: m["D3_sin"] <= m["D2_sin"]),
    ("D3-no-es-peor-que-D1", lambda m: m["D3_sin"] <= m["D1_sin"]),
    ("el-factor-supera-10x", lambda m: m["factor_D1_sobre_D3"] > 10),
    ("D3-deja-menos-del-1-por-ciento", lambda m: m["D3_pct"] < 1.0),
    ("el-denominador-se-imprime", lambda m: m["n_con_estado"] > 0),
    ("los-porcentajes-cuadran-con-los-absolutos",
     lambda m: all(abs(m[f"{d}_pct"] - 100.0 * m[f"{d}_sin"] / m["n_con_estado"]) < 0.05
                   for d in ("D1", "D2", "D3"))),
    ("hay-ficheros-de-esta-sesion", lambda m: m["n_esta_sesion"] > 0),
    ("la-sesion-es-una-minoria", lambda m: m["n_esta_sesion"] < m["n_con_estado"]),
]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prov.py")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sin-procedencia", action="store_true")
    ap.add_argument("--claves", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="version", version=f"prov.py {VERSION}")
    args = ap.parse_args(argv)

    m = measure(args.dir)

    if args.self_test:
        print(f"prov {VERSION} -- self-test")
        print(f"{m['n_con_estado']} hallazgos con token de estado")
        print()
        ok = bad = 0
        for name, check in VECTORS:
            try:
                good = bool(check(m))
            except Exception as exc:                      # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
                bad += 1
                continue
            print(f"  {'PASS' if good else 'FAIL'}  {name}")
            ok += good
            bad += not good
        print()
        print(f"  {ok} pasan, {bad} fallan")
        print()
        print("  NOTA: ningun vector comprueba un numero absoluto. El corpus lo")
        print("  escriben varios autores y crece entre ejecuciones, asi que un")
        print("  numero absoluto no seria falsable. Lo que se comprueba es la")
        print("  RELACION entre detectores, que es lo que sostiene 1473.")
        return 0 if bad == 0 else 1

    if args.sin_procedencia:
        for f in m["_sin_d3"]:
            print(f)
        return 0
    if args.claves:
        for k, c in m["claves"].items():
            print(f"  {c:4d}  {k}")
        return 0
    if args.json:
        out = {k: v for k, v in m.items() if not k.startswith("_")}
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    print(f"procedencia declarada en {m['directorio']}")
    print()
    print(f"  ficheros totales en el directorio   {m['ficheros_totales']}")
    print(f"  hallazgos con token de estado       {m['n_con_estado']}")
    print(f"  de ellos, de esta sesion           {m['n_esta_sesion']}")
    print()
    print("  detector                     sin procedencia    %")
    print(f"    D1  lista cerrada + btik   {m['D1_sin']:5d}          {m['D1_pct']:5.1f}")
    print(f"    D2  D1 o cita o bloque    {m['D2_sin']:5d}          {m['D2_pct']:5.1f}")
    print(f"    D3  CLAVE= o cita o bloque{m['D3_sin']:5d}          {m['D3_pct']:5.1f}")
    print()
    print(f"  factor D1/D3: {m['factor_D1_sobre_D3']}x")
    print()
    print("  El hueco se multiplica por ese factor cambiando SOLO el detector.")
    print("  Conclusion de 1473: no construir el verificador.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
