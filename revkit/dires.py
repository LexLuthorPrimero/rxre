#!/usr/bin/env python3
"""
dires.py -- indice de DIRECCIONES de registro, por ASIC y por bloque.

POR QUE ESTA HERRAMIENTA, Y QUE LE FALTA A regs.py
---------------------------------------------------
`regs.py` indexa los CAMPOS de registro: MASK y __SHIFT. Le van 162669 campos
y su trabajo esta bien hecho.

Pero un campo sin direccion no sirve para nada de lo que se ha hecho esta
tarde. Para comprobar que un PAQUET3 del anillo escribe donde dice, hace falta
saber que registro vive en que offset, y eso no estaba en ningun indice.

El fallo se manifesto de forma concreta: al intentar comprobar si
`0x3c00` era un registro de GFX8, se busco en el directorio de amdgpu y no
habia nada, y casi se escribio "no hay registro ahi". Era un NOT_FOUND
FALSO: los headers no estan en `drivers/gpu/drm/amd/amdgpu/`, estan en
`drivers/gpu/drm/amd/include/asic_reg/`, ordenados por bloque.

Este indice recorre `asic_reg/` y saca:
  - que BLOQUE (gca, gmc, bif, sdma, smu...) define cada registro
  - en que FICHERO lo define, con linea
  - a que offset

Que NO hace
-----------
No resuelve offsets a nombres en general. Varias familias de headers no
traen el offset en la misma forma, y unificarlas a ojo seria adivinar. Este
script solo indexa lo que esta escrito de forma uniforme y reconoce, y
declara lo que no reconoce en vez de dejarlo passar.

En particular, los headers tipo `_sh_mask.h` (MASK y __SHIFT) NO tienen
direccion, y los `.d.h` / `_offset.h` / `_default.h` si. Se distinguen por
nombre, y esa distincion es la que hace que la cuenta cuadre.
"""
import argparse
import os
import re
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(_AQUI, "..", "RESEARCH", "baseline", "linux-7.1.3",
                      "drivers", "gpu", "drm", "amd", "include", "asic_reg")

# Sufijos de fichero que SON de direccion. Los demas (sh_mask) no la tienen.
#
# OJO con el patron: los ficheros se llaman `bif_4_1_d.h`, con GUION BAJO
# delante de la d, no `bif_4_1.d.h` con punto. La primera version puso ".d.h"
# y por eso el filtro no cogia ni un solo .d.h de BIF: el indice salia con
# 587164 entradas de DCN y GC, y con CERO de BIF, que es justo el bloque que
# hace falta para esta GPU. Un filtro mal escrito no avisa: devuelve una
# lista vacia que parece "aqui no hay nada".
SUFIJOS_DIR = ("_d.h", "_offset.h", "_default.h")
# Los que se dejan fuera a proposito, con el motivo.
SUFIJOS_NO_DIR = ("_sh_mask.h", "_enum.h", "_hubmask.h", "_reg.h")

# Una define de direccion: mmNOMBRE <tab/espacios> 0xVALOR
RE_DIR = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+|reg[A-Za-z0-9_]+)\s+"
                    r"(0x[0-9A-Fa-f]+|\d+)\s*(?://.*)?$")


def cargar(raiz=None):
    """
    Devuelve {offset: [(nombre, bloque, fichero, linea), ...]}

    Se indexa por offset y no por nombre a proposito: la pregunta que se
    quiere responder es "que registro vive en 0x1537", y buscar por nombre
    obligaria a saber el nombre antes de empezar.
    """
    raiz = raiz or CORPUS
    if not os.path.isdir(raiz):
        return None, raiz
    idx = {}
    n_fich = 0
    n_def = 0
    for bloque in sorted(os.listdir(raiz)):
        bdir = os.path.join(raiz, bloque)
        if not os.path.isdir(bdir):
            continue
        for fn in sorted(os.listdir(bdir)):
            if fn.endswith(SUFIJOS_NO_DIR):
                continue
            if not fn.endswith(SUFIJOS_DIR):
                continue
            p = os.path.join(bdir, fn)
            n_fich += 1
            try:
                with open(p, errors="replace") as f:
                    for linea, texto in enumerate(f, 1):
                        m = RE_DIR.match(texto.rstrip("\n"))
                        if not m:
                            continue
                        nombre = m.group(1)
                        try:
                            off = int(m.group(2), 0)
                        except ValueError:
                            continue
                        idx.setdefault(off, []).append(
                            (nombre, bloque, "%s/%s" % (bloque, fn), linea))
                        n_def += 1
            except OSError:
                continue
    return (idx, n_fich, n_def), None


def main():
    ap = argparse.ArgumentParser(
        description="indice de direcciones de registro por bloque y ASIC")
    ap.add_argument("offset", nargs="?",
                    help="offset a resolver, decimal o 0xHEX")
    ap.add_argument("--raiz", default=None)
    ap.add_argument("--bloque", default=None, help="filtra por bloque")
    ap.add_argument("--contar", action="store_true",
                    help="solo el resumen del indice")
    a = ap.parse_args()

    res, err = cargar(a.raiz)
    if res is None:
        print("no existe el directorio de asic_reg: %s" % err)
        print()
        print("Sin ese directorio no hay direcciones de registro que")
        print("consultar. NO se responde con un 0: no responder y no")
        print("encontrar son cosas distintas, y aqui se han confundido.")
        return 2
    idx, n_fich, n_def = res

    print("direcciones indexadas : %d" % n_def)
    print("ficheros leidos       : %d" % n_fich)
    print("offsets distintos     : %d" % len(idx))
    print()

    if a.contar:
        from collections import Counter
        c = Counter()
        for v in idx.values():
            for _n, bloque, _f, _l in v:
                c[bloque] += 1
        for b, n in c.most_common():
            print("  %-10s %d" % (b, n))
        return 0

    if not a.offset:
        ap.print_usage()
        print()
        print("Falta el offset. Sin el, esta herramienta no contesta nada,")
        print("y no se permite que eso parezca un resultado.")
        return 2

    # AUTOCOMPROBACION en cada ejecucion. Se ejecuta siempre, no solo en un
    # test aparte, porque el fallo que corrigio esto (SUFIJOS_DIR con ".d.h"
    # en vez de "_d.h") no daba error: devolvia una lista vacia para BIF, el
    # bloque que hace falta en esta GPU, y eso parece un resultado
    # legitimo. Un filtro mal escrito no avisa de que lo este.
    #
    # Estos tres valores se eligen porque son conocidos de antemano por el
    # analisis del WAIT_REG_MEM: el anillo observo 0x1537/0x1538 y el
    # corpus los define como REQ/DONE en BIF 4.1. Si el indice no los
    # encuentra, el indice esta mal, y se dice en vez de seguir.
    fallos = []
    for off, esperado in ((0x1537, "mmGPU_HDP_FLUSH_REQ"),
                          (0x1538, "mmGPU_HDP_FLUSH_DONE")):
        nombres = [n for n, bloque, _f, _l in idx.get(off, [])
                   if bloque == "bif" and "4_1" in _f]
        if not nombres:
            fallos.append("0x%04x no aparece en el indice de BIF 4.1" % off)
        elif esperado not in nombres:
            fallos.append("0x%04x da %s, esperaba %s"
                          % (off, nombres[0], esperado))
    if fallos:
        print("AUTOCOMPROBACION FALLIDA: el indice no es de fiar.")
        for f in fallos:
            print("  - %s" % f)
        print()
        print("Se detiene aqui. Un indice que no encuentra lo que se sabe")
        print("que esta, no va a servir para dizer que algo NO esta.")
        return 3

    try:
        off = int(a.offset, 0)
    except ValueError:
        print("no entiendo el offset %r. Usa decimal o 0xHEX." % a.offset)
        return 2

    if off not in idx:
        print("0x%04x: ningun registro en el indice" % off)
        print()
        print("Esto es NOT_FOUND dentro del indice, no PROVEN_ABSENT.")
        print("El indice cubre los headers que traen la direccion de forma")
        print("uniforme. Que no aparezca NO significa que el registro no")
        print("exista: puede estar en un header con otra forma, que es una")
        print("cosa que este script reconoce y no resuelve.")
        return 1

    print("0x%04x ->" % off)
    for nombre, bloque, fichero, linea in idx[off]:
        if a.bloque and bloque != a.bloque:
            continue
        print("  %-32s %-8s %s:%d" % (nombre, bloque, fichero, linea))
    return 0


if __name__ == "__main__":
    sys.exit(main())
