#!/usr/bin/env python3
# CONTRACT: name=dires
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto de esta herramienta fue `READONLY=yes, WRITES_FILES=no`, y la clase
# de cada escritura se resolvio a TEMPORAL: son las del selftest, que escribe en
# un `tempfile` precisamente para no tocar el arbol.
#
# `revkit` no tenia NINGUN contrato (0 de 30) y es el directorio con mas acceso
# a hardware del proyecto.  Este bloque no anade comportamiento: hace el
# comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
#
# TOUCHES_INTEGRATED=no: lee ficheros y sysfs de la DISCRETA.  No abre DRM, no
# hace ioctl, no escribe en la GPU.  El campo no existe en el vocabulario de
# toolkit.py -- hallazgo 1487 -- y se declara igualmente porque la frontera que
# no se puede declarar es la que no se puede hacer cumplir.
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


def selftest():
    """Vectores sobre un indice SINTETICO, no sobre el corpus real.

    MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2). Antes este fichero NO tenia
    selftest, y esa ausencia es parte del defecto: el unico guardarraon era la
    AUTOCOMPROBACION de mas abajo, que valida el INDICE contra 0x1537/0x1538 en
    BIF 4.1 y no sabe nada de --bloque. El censo lo dice en :350-352: 'valida el
    indice, no el --bloque'.

    Y la propia AUTOCOMPROBACION no se puede usar como selftest: depende del
    corpus de 470 MB y tardaria mas que la mayoria de las herramientas del banco.
    Un selftest que necesita el corpus entero no se ejecuta, y un selftest que no
    se ejecuta no es una red.
    """
    import tempfile
    vectores = []

    with tempfile.TemporaryDirectory() as td:
        # Dos bloques. `bif` define los dos offsets que la AUTOCOMPROBACION
        # espera; `athub` existe pero NO define 0x1537 -- define OTRO offset.
        # Es exactamente el par que separa "bloque que no existe" de "bloque
        # que no define este offset", que es la distincion que el arreglo
        # introduce. Una primera version de este fixture ponia a athub un
        # 0x1537 y el bloque existia pero SI definia el offset, o sea que el
        # caso que se queria probar no estaba: tres vectores fallaron y tenian
        # razon en fallar.
        os.makedirs(os.path.join(td, "bif"))
        os.makedirs(os.path.join(td, "athub"))
        with open(os.path.join(td, "bif", "bif_4_1_d.h"), "w") as f:
            f.write("#define mmGPU_HDP_FLUSH_REQ 0x1537\n"
                    "#define mmGPU_HDP_FLUSH_DONE 0x1538\n")
        with open(os.path.join(td, "athub", "athub_0_0_d.h"), "w") as f:
            f.write("#define mmTHATUB_FLUFLUSH 0x2000\n")
        # Un _sh_mask.h NO debe entrar: es lo que separa el indice bueno del malo.
        with open(os.path.join(td, "bif", "bif_4_1_sh_mask.h"), "w") as f:
            f.write("#define mmGPU_HDP_FLUSH_REQ_MASK 0x1\n")

        res, err = cargar(td)
        idx, n_fich, n_def = res
        vectores.append(("el indice se carga y el sh_mask queda fuera",
                         n_fich == 2 and n_def == 3, "fich=%d def=%d" % (n_fich, n_def)))
        bloques = sorted({b for v in idx.values() for (_n, b, _f, _l) in v})
        vectores.append(("la poblacion de bloques se calcula del indice",
                         bloques == ["athub", "bif"], bloques))

        def vis(bloque):
            if not bloque:
                return list(idx[0x1537])
            return [t for t in idx[0x1537] if t[1] == bloque]

        # Control positivo: el bloque existe y define el offset.
        v = vis("bif")
        vectores.append(("bloque que existe y define: filas presentes",
                         len(v) == 1 and v[0][1] == "bif", "%d filas" % len(v)))
        # Control positivo del filtro: el bloque existe pero no define el offset.
        v = vis("athub")
        vectores.append(("bloque que existe y NO define: 0 filas, y es un caso"
                         " DISTINTO del bloque inexistente",
                         len(v) == 0, "%d filas" % len(v)))
        # Los cuatro vectores del defecto medido, sobre el valor del argumento.
        for malo in ("BIF", "biff", "bloque_que_no_existe", "BIF4", "BIF_4_1"):
            vectores.append(("--bloque %r no pasa la validacion contra la"
                             " poblacion del indice" % malo,
                             malo not in bloques, "poblacion=%s" % bloques))
        # `--bloque ""` es FALSO en Python, y el filtro de toda la vida ha sido
        # `if a.bloque and ...`, o sea que la cadena vacia significa "sin
        # filtro". No es un nombre de bloque, y no debe pasar por la validacion
        # como si lo fuera. Se declara explicitamente para que el cambio sea
        # visible si alguien Tightena la comprobacion.
        vectores.append(("--bloque '' es cadena vacia: significa SIN filtro",
                         bool("") is False and "" not in bloques,
                         "poblacion=%s" % bloques))
        # Un bloque que no esta en la lista debe salir con rc=2: se comprueba
        # la FUNCION de decision, no el rc de main(), que aqui no se invoca para
        # no releer el corpus real.
        def rc_de(bloque):
            if bloque and bloque not in bloques:
                return 2
            return 1 if not vis(bloque) else 0
        vectores.append(("bloque inexistente: rc=2 (no se ha medido nada)",
                         rc_de("BIF") == 2, rc_de("BIF")))
        vectores.append(("bloque real sin entrada en el offset: rc=1 (NOT_FOUND)",
                         rc_de("athub") == 1, rc_de("athub")))
        vectores.append(("bloque real con entrada: rc=0",
                         rc_de("bif") == 0, rc_de("bif")))
        vectores.append(("sin filtro: rc=0 y sale la entrada que si hay en 0x1537",
                         rc_de("") == 0 and len(vis("")) == 1, rc_de("")))
        # La comparacion es exacta y sensible a mayusculas, y ESO se declara:
        # un bloque son minusculas en el arbol.
        vectores.append(("la comparacion de bloques es exacta y en minusculas",
                         all(b == b.lower() for b in bloques), bloques))

    fallos = sum(1 for _, ok, _ in vectores if not ok)
    print("dires.py selftest")
    for nombre, ok, det in vectores:
        print("  %s %s%s" % ("OK  " if ok else "FAIL", nombre,
                             "" if ok else "   -- %r" % (det,)))
    print("RESULT: %s (%d vectores)" % ("PASS" if not fallos else "FAIL",
                                        len(vectores)))
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser(
        description="indice de direcciones de registro por bloque y ASIC")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("offset", nargs="?",
                    help="offset a resolver, decimal o 0xHEX")
    ap.add_argument("--raiz", default=None)
    ap.add_argument("--bloque", default=None, help="filtra por bloque")
    ap.add_argument("--contar", action="store_true",
                    help="solo el resumen del indice")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

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

    # MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2, sobre el censo
    # 08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md:319-352).
    #
    # El filtro de --bloque era `if a.bloque and bloque != a.bloque: continue`, o
    # sea una comparacion que no decia nada cuando no encontraba nada.
    # Consecuencia medida ANTES del arreglo, offset 0x1537:
    #
    #   --bloque bif                  ->  3 filas,  rc=0   (control)
    #   --bloque BIF                  ->  0 filas,  rc=0   (mayusculas)
    #   --bloque bloque_que_no_existe ->  0 filas,  rc=0
    #   --bloque athub                ->  0 filas,  rc=0   (athub EXISTE)
    #
    # Los cuatro imprimen el mismo "0x1537 ->" y las tres filas del control.
    #
    # Y el caso mas incomodo de los cuatro es el ultimo: `athub` es un bloque
    # real, esta en el indice, y --contar lo enumera. Lo que no hace es definir
    # ESTE offset. "No hay entrada de este bloque en este offset" y "este
    # bloque no existe" son dos respuestas distintas, y el filtro las fundia en
    # un vacio mudo igual para las dos. Por eso el arreglo las separa:
    #
    #   bloque que NO esta en el indice   ->  rc=2, no se ha medido nada
    #   bloque que esta pero no en el offset ->  rc=1, declarado NOT_FOUND
    #
    # La poblacion de bloques se CALCULA del propio indice, que es lo que esta
    # herramienta ya hace en --contar. No se valida contra un fichero de texto
    # ni contra un catalogo escrito a mano, que es el modo de fallar del primer
    # intento del hallazgo 1055.
    bloques = sorted({b for v in idx.values() for (_n, b, _f, _l) in v})

    if a.bloque and a.bloque not in bloques:
        print("ERROR  --bloque %s no es ningun bloque de este indice." % a.bloque)
        print("  bloques que SI existen (%d): %s"
              % (len(bloques), ", ".join(bloques)))
        print()
        print("  No se ha medido nada. Este mismo fichero dice arriba, en el")
        print("  comentario de SUFIJOS_DIR, que 'un filtro mal escrito no avisa")
        print("  de que lo este': un --bloque mal escrito devolvia una lista")
        print("  vacia, que es indistinguible de 'aqui no hay nada'.")
        return 2

    if a.contar:
        from collections import Counter
        c = Counter()
        for v in idx.values():
            for _n, bloque, _f, _l in v:
                if a.bloque and bloque != a.bloque:
                    continue
                c[bloque] += 1
        for b, n in c.most_common():
            print("  %-10s %d" % (b, n))
        if a.bloque:
            print()
            print("  filtro --bloque %s aplicado: %d entradas contadas de %d"
                  % (a.bloque, c.get(a.bloque, 0), n_def))
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

    vis = [(nombre, bloque, fichero, linea)
           for (nombre, bloque, fichero, linea) in idx[off]
           if not a.bloque or bloque == a.bloque]

    if not vis:
        # El bloque esta validado como real (arriba), asi que este vacio NO es
        # un nombre mal escrito: es que este offset no lo define. Se declara,
        # y se sale con 1, que es el codigo que ya usa el "no esta en el indice"
        # de mas arriba. Un rc=0 aqui seria una respuesta a una pregunta que
        # nadie ha hecho.
        print("0x%04x: el indice tiene %d entradas para este offset, ninguna"
              % (off, len(idx[off])))
        print("del bloque %s." % a.bloque)
        print()
        n_bloque = sum(1 for v in idx.values() for (_n, b, _f, _l) in v
                       if b == a.bloque)
        print("El bloque %s SI existe en este indice: %d entradas en total."
              % (a.bloque, n_bloque))
        print("Lo que no existe es una entrada SUYA en este offset.")
        print("Esto es NOT_FOUND dentro del indice, no PROVEN_ABSENT: el")
        print("offset si esta, y los bloques que si lo definen son:")
        for nombre, bloque, fichero, linea in idx[off][:8]:
            print("  %-32s %-8s %s:%d" % (nombre, bloque, fichero, linea))
        if len(idx[off]) > 8:
            print("  ... y %d mas" % (len(idx[off]) - 8))
        return 1

    print("0x%04x ->" % off)
    for nombre, bloque, fichero, linea in vis:
        print("  %-32s %-8s %s:%d" % (nombre, bloque, fichero, linea))
    if a.bloque:
        print("  filtro --bloque %s: %d de %d entradas de este offset"
              % (a.bloque, len(vis), len(idx[off])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
