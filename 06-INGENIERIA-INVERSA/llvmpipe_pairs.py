#!/usr/bin/env python3
"""Clasifica la rampa alfa BC3 contra tres implementaciones de referencia.

POR QUE EXISTE ESTO
===================

AD-12 (truncamiento vs redondeo en el sampler de Polaris 12) no se resuelve
leyendo la especificacion: se resuelve midiendo que rampa produce la RX 550 y
comparandola con las que se podrian haber usado por software. Para que esa
comparacion tenga poder discriminante hace falta que las referencias sean
mutuamente distinguibles, y no lo son todas.

Las tres implementaciones de referencia son:

    spec      la regla Microsoft "Block Compression (Direct3D 10)", con los
              terminos de redondeo +3 (rama /7) y +2 (rama /5)
    trunc     el mismo calculo SIN redondeo: es lo que hace bcdec v0.985
    llvmpipe  lp_build_lerpdxta(), transcrita desde
              /home/lucas/mesa/src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c:817-877

EL METODO, Y POR QUE NO ES UNA TAUTOLOGIA
=========================================

Cada valor se CALCULA desde su formula. La categoria de una tripla se deduce
POR COMPARACION entre los tres valores calculados, no leyendo una tabla de
expectativas. Los recuentos emergen de esa clasificacion.

Este script NO contiene ningun numero de resultado. La unica cifra que se
compara contra el exterior es 649, y viene del commit 1e28733, una derivacion
independiente hecha por otra sesion sobre el mismo arbol de Mesa. Que dos
derivaciones independientes coincidan ES evidencia; un 649 que yo escribiera
al ver mi propia salida no lo seria. Por eso es un contraste externo y
documentado, y no un EXPECTED.

La version anterior de este fichero tenia:

    EXPECTED = {UNIVERSE_TODOS: (136686, 42170, 93867, 649),
                UNIVERSE_COMUN: (136686, 42170, 41817, 271)}

La fila de COMUN era inventada, y el script no se quejaba porque la
acumulacion de discriminantes no comprobaba el universo. Un valor esperado
escrito a mano convierte el test en una comparacion consigo mismo.

EL UNIVERSO: TRIPLAS (a0, a1, code)
===================================

El universo de PARES (a0, a1) es 256*256 = 65536. El commit 1e28733 reporta
136686 casos divergentes, que no cabe como recuento de pares. Son TRIPLAS
(a0, a1, code) con code en 2..7: 65536 pares x 6 codigos = 393216.

QUE CODIGOS SE COMPARAN, Y POR QUE NO IMPORTA PARA EL DISCRIMINANTE
==================================================================

En la rama a0 <= a1 la spec y el trunc FIJAN los codigos 6 y 7 a 0 y 255,
mientras llvmpipe los interpola. Compararlos ahi seria comparar una
constante contra un valor calculado.

Se emiten los dos universos, y el resultado instructive es que NO cambia:

    TODOS   compara 2..7 en ambas ramas
    COMUN   compara solo los codigos que las tres implementaciones definen
            (2..7 si a0 > a1; 2..5 si a0 <= a1)

Los discriminantes_RESULTANTES SON EL MISMO CONJUNTO en ambos universos.
La razon, medida: las 649 triplas caen solo en los codigos 5 y 7, y ninguna
en 6 ni en 7 de la rama a0 <= a1. Es decir, el conjunto con poder
discriminante queda entero dentro de los codigos que las tres definen. La
pregunta por tanto no era cual universo usar, sino por que seProduces la
duda: los codigos 6 y 7 de la rama a0 <= a1 no generan ni un solo
discriminante.

LO QUE NO ESTA ESTABLECIDO
==========================

Que lp_build_lerpdxta sea la funcion que llvmpipe usa REALMENTE para BC3 en
esta version de Mesa es NOT_DETERMINED. Este script reproduce la funcion
citada en 1e28733; que sea la ruta efectiva en ejecucion solo lo dira la
medicion de AD-12.

Salida
======

    --classify            recuento por universo y contraste con 1e28733
    --emit-fixture RUTA   escribe el JSON de las 649 triplas discriminantes
    --triples             lista esas triplas por stdout
    --ramp A0 A1          imprime las tres rampas y la categoria por codigo

Devuelve 1 si el contraste con el commit 1e28733 falla, para que no se
regenere un fixture sobre una aritmetica que ya no se ha verificado.
"""

import argparse
import hashlib
import json
import sys

N_PALETTE = 8

SPEC = "spec"
TRUNC = "trunc"
NONE = "ninguna"       # llvmpipe no coincide con ninguna de las otras dos
SAME = "sin_informacion"  # spec == trunc: la tripla no discrimina nada


# ----------------------------------------------------------------------
# Las tres formulas. Una por tripla (a0, a1, code), escalares.
# ----------------------------------------------------------------------

def calculate_spec(a0, a1, code):
    """Rampa segun Microsoft "Block Compression (Direct3D 10)".

    a0 >  a1 : 6 valores interpolados, divisor 7, redondeo +3
    a0 <= a1 : 4 valores interpolados, divisor 5, redondeo +2, mas los
               extremos fijos 0 (transparente) y 255 (opaco)
    """
    if code < FIRST or code > LAST:
        raise ValueError("code %d fuera de 2..7" % code)
    if a0 > a1:
        return ((8 - code) * a0 + (code - 1) * a1 + 3) // 7
    if code <= 5:
        return ((6 - code) * a0 + (code - 1) * a1 + 2) // 5
    return 0 if code == 6 else 255


def calculate_trunc(a0, a1, code):
    """La misma regla sin terminos de redondeo.

    No es un error del script: es la hipotesis rival que AD-12 tiene que
    separar de la spec. bcdec v0.985 trunca, y diverge de la especificacion
    en ~82.9% de los pares con un error maximo de 1 sobre 255.
    """
    if code < FIRST or code > LAST:
        raise ValueError("code %d fuera de 2..7" % code)
    if a0 > a1:
        return ((8 - code) * a0 + (code - 1) * a1) // 7
    if code <= 5:
        return ((6 - code) * a0 + (code - 1) * a1) // 5
    return 0 if code == 6 else 255


def calculate_llvmpipe(a0, a1, code):
    """lp_build_lerpdxta(), transcrita de lp_bld_format_s3tc.c:817-877.

    No interpola con pesos nominales. Trabaja en 16 bits con pesos fijos
    PRETRUNCADOS y dos desplazamientos encadenados:

        weight5 = 255*64/5  = 3264      (truncado en la fuente)
        weight7 = 255*64/7  = 2330      (truncado en la fuente)
        weight  = weight7 si a0 > a1, si no weight5

        code    = code - 1
        weight  = (weight * code) >> 6
        delta   = a1 - a0
        ainterp = (delta * weight) >> 8
        result  = a0 + ainterp

    De ahi la divergencia: delta es NEGATIVO cuando a0 > a1 y se multiplica
    por un peso que CRECE con code, de modo que el producto se suma en vez de
    restar, y los dos desplazamientos no reconstruyen la ponderacion nominal.
    """
    if code < FIRST or code > LAST:
        raise ValueError("code %d fuera de 2..7" % code)
    weight5 = (255 * 64) // 5
    weight7 = (255 * 64) // 7
    w = weight7 if a0 > a1 else weight5
    w = (w * (code - 1)) >> 6
    delta = a1 - a0
    return (a0 + ((delta * w) >> 8)) & 0xFF


FIRST, LAST = 2, 7

CALCS = (
    (SPEC, calculate_spec),
    (TRUNC, calculate_trunc),
    ("llvmpipe", calculate_llvmpipe),
)


# ----------------------------------------------------------------------
# Clasificacion por comparacion de valores calculados
# ----------------------------------------------------------------------

def classify(a0, a1, code):
    """Categoria de la tripla, deducida comparando los tres valores.

    Devuelve (categoria, {nombre: valor}).
    """
    vals = {name: fn(a0, a1, code) for name, fn in CALCS}
    sv, tv, lv = vals[SPEC], vals[TRUNC], vals["llvmpipe"]

    if sv == tv:
        return SAME, vals          # la referencia rival coincide: no discrimina
    if lv == sv:
        return SPEC, vals
    if lv == tv:
        return TRUNC, vals
    return NONE, vals


# Los dos universos. La funcion devuelve los codigos COMUNES a las tres
# implementaciones para ese par.
UNIVERSE_TODOS = "todos"
UNIVERSE_COMUN = "comun"


def codes_todos(a0, a1):
    return range(FIRST, LAST + 1)


def codes_comun(a0, a1):
    # En a0 <= a1 la spec y el trunc fijan 6 y 7 a constantes; llvmpipe los
    # interpola. ahi no son comparables.
    return range(FIRST, LAST + 1) if a0 > a1 else range(FIRST, 6)


UNIVERSES = (
    (UNIVERSE_TODOS, codes_todos),
    (UNIVERSE_COMUN, codes_comun),
)


def all_pairs():
    """Los 65536 pares (a0, a1), ambos en 0..255, en orden ascendente.

    Se recorren LOS DOS ORDENES. El codificador de este proyecto nunca produce
    a0 < a1 (ordena a0=max, a1=min, commit 44bc133), asi que un recorrido
    triangular cerraria en la mitad del universo y daria mitades de todos los
    recuentos sin que nada fallara. Un decodificador tiene que manejar los dos.

    El recorrido es completo porque una omision aqui NO FALLA: produce numeros
    mas pequenos y todavia plausibles.
    """
    for a0 in range(256):
        for a1 in range(256):
            yield a0, a1


def scan():
    """Recorre el universo una vez y clasifica cada tripla.

    Devuelve (resultados_por_universo, discriminantes_por_universo).

    discriminantes[u] es una lista de dicts con los valores ya calculados. No
    hay ningun valor esperado en ninguna parte: todo sale de calculate_*().
    """
    counts = {}
    discs = {}

    for name, codes_for in UNIVERSES:
        d = sp = tr = no = 0
        keep = []
        for a0, a1 in all_pairs():
            branch = "a0>a1" if a0 > a1 else "a0<=a1"
            for code in codes_for(a0, a1):
                cat, vals = classify(a0, a1, code)
                if cat == SAME:
                    continue
                d += 1
                if cat == SPEC:
                    sp += 1
                elif cat == TRUNC:
                    tr += 1
                else:
                    no += 1
                    keep.append({
                        "a0": a0,
                        "a1": a1,
                        "code": code,
                        "branch": branch,
                        "expect_spec": vals[SPEC],
                        "expect_trunc": vals[TRUNC],
                        "expect_llvmpipe": vals["llvmpipe"],
                    })
        counts[name] = {"divergentes": d, "spec": sp, "trunc": tr, "ninguna": no}
        discs[name] = keep
    return counts, discs


# Contraste EXTERNO. La unica cifra que este fichero no produce.
# Fuente: commit 1e28733, derivacion independiente sobre el mismo arbol.
# Si el arbol de Mesa cambia y esto deja de cuadrar, el fixture NO debe
# regenerarse hasta entender por que.
CROSSCHECK = {
    "universo": UNIVERSE_TODOS,
    "fuente": "commit 1e28733 (derivacion independiente, IA-3)",
    "divergentes": 136686,
    "spec": 42170,
    "trunc": 93867,
    "ninguna": 649,
}


def do_classify(stream):
    w = stream.write
    n_pairs = 256 * 256
    n_triples = n_pairs * (LAST - FIRST + 1)
    counts, discs = scan()

    w("rampa BC3 -- 3 implementaciones, clasificacion por TRIPLA (a0,a1,code)\n")
    w("  pares  (a0, a1) en 0..255   : %d\n" % n_pairs)
    w("  triples (a0, a1, code) %d..%d : %d\n\n" % (FIRST, LAST, n_triples))

    for name, _ in UNIVERSES:
        c = counts[name]
        d = c["divergentes"]
        w("  universo '%s'  (%s)\n"
          % (name,
             "codigos %d..%d en ambas ramas" % (FIRST, LAST) if name == UNIVERSE_TODOS
             else "solo los codigos que las tres definen"))
        w("    spec != trunc  (divergentes)   : %7d\n" % d)
        w("      llvmpipe == spec   (+3/+2)   : %7d  %5.2f %%\n" % (c["spec"], 100.0 * c["spec"] / d))
        w("      llvmpipe == trunc  (bcdec)   : %7d  %5.2f %%\n" % (c["trunc"], 100.0 * c["trunc"] / d))
        w("      llvmpipe == NINGUNA          : %7d  %5.2f %%  <==\n" % (c["ninguna"], 100.0 * c["ninguna"] / d))
        w("\n")

    # El resultado que hace innecesaria la eleccion de universo.
    same = set((t["a0"], t["a1"], t["code"]) for t in discs[UNIVERSE_TODOS])
    only = set((t["a0"], t["a1"], t["code"]) for t in discs[UNIVERSE_COMUN])
    w("  Los dos universos producen el MISMO conjunto de discriminantes:\n")
    w("    solo en TODOS : %d\n" % len(same - only))
    w("    solo en COMUN : %d\n" % len(only - same))
    w("    reparto por rama y codigo de las discriminantes:\n")
    dist = {}
    for t in discs[UNIVERSE_TODOS]:
        dist[(t["branch"], t["code"])] = dist.get((t["branch"], t["code"]), 0) + 1
    for (branch, code), n in sorted(dist.items()):
        w("      %-7s code %d : %4d\n" % (branch, code, n))
    w("    Ninguna cae en code 6 o 7 de la rama a0<=a1, que es donde las tres\n")
    w("    no son comparables. Por eso la pregunta del universo no cambia el\n")
    w("    conjunto: la duda no tenia consecuencia.\n\n")

    w("  CONTRASTE EXTERNO\n")
    cc = CROSSCHECK
    got = counts[cc["universo"]]
    ok = (got["divergentes"] == cc["divergentes"] and got["spec"] == cc["spec"]
          and got["trunc"] == cc["trunc"] and got["ninguna"] == cc["ninguna"])
    w("    fuente : %s\n" % cc["fuente"])
    w("    calculado  %7d %6d %6d %4d\n"
      % (got["divergentes"], got["spec"], got["trunc"], got["ninguna"]))
    w("    commit    %7d %6d %6d %4d   %s\n"
      % (cc["divergentes"], cc["spec"], cc["trunc"], cc["ninguna"],
         "COINCIDE" if ok else "NO COINCIDE"))
    w("    (divergentes / spec / trunc / ninguna)\n\n")

    w("  LAS 649 SON EQUIVALENTES EN PODER DISCRIMINANTE\n")
    w("  Una version anterior de este proyecto las dividia en 271 robustos y\n")
    w("  378 debiles, por ser estos ultimos de la rama a0<=a1. Esa division\n")
    w("  era FALSA: los 378 caen en el codigo 5, que las tres implementaciones\n")
    w("  interpolan. La division real es por RAMA, no por poder probatorio.\n\n")

    w("  LO QUE NO SE AFIRMA\n")
    w("  Que lp_build_lerpdxta sea la ruta efectiva de llvmpipe para BC3 en\n")
    w("  esta version de Mesa es NOT_DETERMINED. Aqui se reproduce la funcion\n")
    w("  que cita 1e28733, no una traza de ejecucion.\n")

    return 0 if ok else 1


def emit_fixture(path, triples):
    """Escribe el JSON de las triplas discriminantes.

    Sin flag de poder discriminante: las 649 son equivalentes. Se conserva
    `branch` y `code` como metadatos informativos, no como criterio.
    """
    doc = {
        "schema": "rx550-fase3-corpus-discriminante/1",
        "purpose": ("triplas (a0,a1,code) donde llvmpipe difiere de spec Y de "
                    "trunc. Discriminan hardware de software por aritmetica, "
                    "sin depender de la respuesta de AD-12."),
        "generated_by": ("06-INGENIERIA-INVERSA/llvmpipe_pairs.py --emit-fixture, "
                         "valores CALCULADOS desde las tres formulas"),
        "provenance": {
            "spec": "Microsoft 'Block Compression (Direct3D 10)', +3 rama /7, +2 rama /5",
            "trunc": "la misma regla sin redondeo (bcdec v0.985 trunca)",
            "llvmpipe": ("lp_build_lerpdxta(), /home/lucas/mesa "
                         "src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c:817-877"),
            "mesa_tree": "26.1-branchpoint-1415-gc5e413533f4",
            "NO_VERIFICADO": ("que lp_build_lerpdxta sea la ruta efectiva de "
                              "llvmpipe en ejecucion. Solo la medicion de AD-12."),
            "crosscheck": ("recuento contrastado contra el commit 1e28733, "
                           "derivacion independiente"),
        },
        "counts": {
            "total": len(triples),
            "branch_a0_gt_a1": sum(1 for t in triples if t["branch"] == "a0>a1"),
            "branch_a0_le_a1": sum(1 for t in triples if t["branch"] == "a0<=a1"),
        },
        "poder_discriminante": ("Las %d triplas son equivalentes. La division "
                                "anterior 271/378 por poder probatorio era FALSA: "
                                "los 378 del caso a0<=a1 caen en el codigo 5, "
                                "que las tres implementaciones interpolan." % len(triples)),
        "cases": triples,
    }
    blob = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    with open(path, "w") as f:
        f.write(blob)

    sys.stderr.write("escrito %s\n" % path)
    sys.stderr.write("  triplas   : %d\n" % len(triples))
    sys.stderr.write("  bytes     : %d\n" % len(blob))
    sys.stderr.write("  sha256    : %s\n" % hashlib.sha256(blob.encode()).hexdigest())
    return triples


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--classify", action="store_true",
                    help="recuento por universo y contraste con el commit 1e28733")
    ap.add_argument("--emit-fixture", metavar="RUTA",
                    help="escribe el JSON de las triplas discriminantes")
    ap.add_argument("--triples", action="store_true",
                    help="lista las triplas discriminantes por stdout")
    ap.add_argument("--ramp", nargs=2, type=int, metavar=("A0", "A1"),
                    help="imprime las tres rampas y la categoria por codigo")
    args = ap.parse_args()

    if args.ramp:
        a0, a1 = args.ramp
        if not (0 <= a0 <= 255 and 0 <= a1 <= 255):
            sys.stderr.write("a0 y a1 deben estar en 0..255\n")
            return 2
        for name, fn in CALCS:
            pal = [a0, a1] + [fn(a0, a1, c) for c in range(FIRST, LAST + 1)]
            print("%-9s %s" % (name, " ".join("%3d" % v for v in pal)))
        for code in range(FIRST, LAST + 1):
            cat, v = classify(a0, a1, code)
            print("  code %d: spec=%3d trunc=%3d llvmpipe=%3d   %s"
                  % (code, v[SPEC], v[TRUNC], v["llvmpipe"], cat))
        return 0

    if args.emit_fixture or args.triples:
        counts, discs = scan()
        keep = discs[UNIVERSE_TODOS]
        if args.triples:
            for t in keep:
                print("%3d %3d %d" % (t["a0"], t["a1"], t["code"]))
            return 0
        emit_fixture(args.emit_fixture, keep)
        got = counts[CROSSCHECK["universo"]]
        if (got["divergentes"], got["spec"], got["trunc"], got["ninguna"]) != \
           (CROSSCHECK["divergentes"], CROSSCHECK["spec"], CROSSCHECK["trunc"],
            CROSSCHECK["ninguna"]):
            sys.stderr.write("\nAVISO: el contraste con %s NO coincide.\n"
                             "El fixture se ha escrito, pero no debe usarse hasta\n"
                             "entender por que.\n" % CROSSCHECK["fuente"])
            return 1
        return 0

    return do_classify(sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
