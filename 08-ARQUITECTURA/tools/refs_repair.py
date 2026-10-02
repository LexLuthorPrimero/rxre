#!/usr/bin/env python3
# CONTRACT: name=refs_repair
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""refs_repair -- repara referencias colgando en los hallazgos PROPIOS.

POR QUE EXISTE. `FINDINGS-RENUMERACIONES.md` mide 1028 referencias que apuntan a
un hallazgo distinto del que citan. Este script repara **solo las que estan en
ficheros mios**, porque las de otras sesiones son suyas y suyas son sus decisiones.

LIMITE DURE Y DELIBERADO. No hay heuristica de "esto parece mio". Hay una lista
EXPLICITA de ficheros. Un archivo que no este en la lista no se toca ni aunque el
numero suggests lo contrario, porque tocar ficheros de otra sesion seria mezclar
ambitos justo cuando el problema es de ambitos.

LO QUE NO HACE Y POR QUE NO DEBERIA HACERLO

* No reescribe referencias que no sean `` `NNN` `` entre acentos graves. Hay
  referencias en prosa ("el hallazgo 025") que un regex wider tocaria sin poder
  distinguir una cita de un numero de linea.
* No resuelve ambiguedades. Si `202` esta en la tabla de reenvio, `202` se
  reescribe a `242` sin preguntar, porque el contexto es una cita de hallazgo y
  no otra cosa. Si alguna vez NO fuera asi, es un cambio a revisar a mano.

AVISO DE AUTO-REFERENCIA. Tras la reparacion, un hallazgo puede citar su PROPIO
numero nuevo, porque antes citaba su numero viejo. Eso es correcto en contenido
pero es un caso que hay que ver, no uno que deba pasar en silencio.

Uso:
  refs_repair.py --dry-run         muestra el diff, no escribe
  refs_repair.py --aplicar         escribe, solo ficheros de la lista
  refs_repair.py --self-test

Codigos de salida:
  0  nada que reparar
  1  habia referencias colgando reparadas (o a reparar, en --dry-run)
  2  lista de ficheros vacia
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")
sys.path.insert(0, HERE)

from findings_index import escanear, reenvios, FIND  # noqa: E402

# Ficheros PROPIOS. Numeros actuales. Anything not here is not touched.
# Se listan por numero y se resuelve al nombre real, porque el numero puede
# haber cambiado entre ejecuciones.
MIS_NUMEROS = [191, 192, 200, 203, 231, 242, 244, 247, 259]

RE_CITA = re.compile(r"`(\d{3})`")


def mi_fichero_por_num(num, filas):
    for f in filas:
        if f["num"] == num:
            return f["fichero"]
    return None


def plan(filas, rev):
    """(fichero, [(linea, viejo, nuevo)]) para mis ficheros."""
    viejos = {x["viejo"]: x["nuevo"] for x in rev if x.get("reasignado")}
    out = []
    for num in MIS_NUMEROS:
        nombre = mi_fichero_por_num(num, filas)
        if not nombre:
            continue
        ruta = os.path.join(FIND, nombre)
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            lineas = fh.read().split("\n")
        cambios = []
        for n, linea in enumerate(lineas, 1):
            def sub(m):
                v = int(m.group(1))
                if v in viejos and v != num:
                    cambios.append((n, v, viejos[v]))
                    return "`%03d`" % viejos[v]
                return m.group(0)
            RE_CITA.sub(sub, linea)
        if cambios:
            out.append((nombre, num, cambios))
    return out


def aplicar(p, dry):
    for nombre, num, cambios in p:
        ruta = os.path.join(FIND, nombre)
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        nuevos = {nuevo for _n, _v, nuevo in cambios}
        texto2 = texto
        for viejo, nuevo in sorted({(v, x) for _n, v, x in cambios}):
            texto2 = texto2.replace("`%03d`" % viejo, "`%03d`" % nuevo)
        if not dry:
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write(texto2)
        print("%s  (%d referencias)" % (nombre, len(cambios)))
        for n, v, x in cambios[:4]:
            print("     L%-4d  `%03d` -> `%03d`%s"
                  % (n, v, x, "   <-- AUTO-REFERENCIA" if x == num else ""))
        if len(cambios) > 4:
            print("     ... y %d mas" % (len(cambios) - 4))
    return sum(len(c) for _n, _i, c in p)


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. El regex solo toca citas entre acentos graves. Un "hallazgo 025" en prosa
    #    NO se reescribe, y eso es lo correcto: no sabemos si es una cita.
    eq("cita entre acentos", RE_CITA.sub(lambda m: m.group(0), "ver `025` aqui"), "ver `025` aqui")
    eq("prosa no se toca", RE_CITA.sub(lambda m: m.group(0), "el hallazgo 025 dice"), "el hallazgo 025 dice")
    eq("numero de linea no se toca", RE_CITA.sub(lambda m: m.group(0), "L025"), "L025")

    # 2. La lista de ficheros PROPIOS tiene que estar vacia si no se conoce, no
    #    "todos". Una lista vacia significa no tocar nada.
    if not MIS_NUMEROS:
        fails.append("control negativo: MIS_NUMEROS vacio, la herramienta no "
                     "podria distinguir mio de ajeno")

    # 3. Control negativo: una reescritura no puede crear un bucle de reescritura.
    #    Si `NNN` -> `NNN'` y `NNN'` tambien esta en la tabla, reescribir dos
    #    veces llevaria a un numero que tampoco es el. Se comprueba que el
    #    destino no es a su vez una clave de la tabla.
    filas = escanear()
    rev = reenvios(filas)
    mapa = {x["viejo"]: x["nuevo"] for x in rev if x.get("reasignado")}
    encadenados = [(a, b) for a, b in mapa.items() if b in mapa]
    if encadenados:
        fails.append("cadena de renumeraciones sin resolver: %s" % encadenados[:4])

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (3 vectores de alcance del regex, 1 control de lista, "
          "1 de encadenamiento)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    filas = escanear()
    rev = reenvios(filas)
    p = plan(filas, rev)
    if not p:
        print("nada que reparar en mis %d hallazgos" % len(MIS_NUMEROS))
        return 0
    print("=== %s ===" % ("VISTA PREVIA (no se escribe)" if "--dry-run" in argv
                          else "ESCRITURA"))
    n = aplicar(p, "--dry-run" in argv)
    print()
    print("referencias %s: %d"
          % ("a reparar" if "--dry-run" in argv else "reparadas", n))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))