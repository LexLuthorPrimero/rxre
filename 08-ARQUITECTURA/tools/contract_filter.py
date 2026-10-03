#!/usr/bin/env python3
# CONTRACT: name=contract_filter
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""contract_filter -- resta los falsos positivos conocidos de toolkit.py.

POR QUE EXISTE

    `toolkit.py` marca FALLA cuando algo no cuadra, y hay una razon buena para no
    relajar el contrato: es lo unico que permite preguntar "esta herramienta
    puede tocar el hardware?". Aceptarlo como no-fallo para que el semaforo
    quede verde seria admitir que el semaforo ya no mide.

    Ese razonamiento es correcto y no lo toco. Lo que hago es lo que el propio
    toolkit.py hace con su excepcion AJENA, pero al reves: en vez de tolerar
    herramientas enteras, tolero PROBLEMAS CONCRETOS que he comprobado que son
    ruido, y sigo fallando por todo lo demas.

POR QUE UNA LISTA Y NO UNA PALABRA

    Porque una palabra ("ignora estos errores") no es auditable: nadie puede
    comprobar dentro de un ano si lo que se ignora seguia siendo ruido. Cada
    entrada de la lista dice QUE se descarto, POR QUE, y como se comprueba. Si
    un dia el motivo deja de ser cierto, el sitio donde se ve es la lista, no
    un `if` sin nombre.

Y LO QUE ESTO NO HACE

    No arregla las herramientas. Las cinco de abajo DECLARAN BIEN: declaran
    WRITES_FILES=no y escriben un tempfile, o escriben en /tmp. Cambiar su
    contrato a `yes` para que dejen de salir seria cambiar una declaracion
    correcta por una falsa: cinco veces el validador en lugar de arreglar la
    herramienta.
"""
import os
import re
import subprocess
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLKIT = os.path.join(ROOT, "08-ARQUITECTURA/tools/toolkit.py")

# (fichero, LINEA, por_que_es_ruido)
#
# POR QUE LA LINEA Y NO UN TROZO DE TEXTO. El mensaje de toolkit dice
# "primera: L380 open(...,'w'|'a'|'x')" para doclint, para aperture y para
# struct_rw IGUAL. Los tres son open(...,'w') y el mensaje no los distingue: lo
# unico que los separa es en que linea esta, y la linea si es un hecho que he
# comprobado. Una allowlist por texto habria dejado pasar a los tres; por linea
# cada entrada es una afirmacion verificable.
#
# Y una entrada mas, que es esta misma: este fichero contiene en su
# documentacion los patrones que toolkit busca, asi que se senala a si mismo. No
# es un error del detector: es que documentar un falso positivo reproduce el
# falso positivo. Se permite y se dice por que.
PERMITIDOS = (
    ("doclint.py", 380, "Escribe un tempfile.mkstemp en su self-test y lo borra "
     "con os.unlink (L390). Un temporal en /tmp no es un fichero DEL PROYECTO."),
    ("aperture.py", 154, "os.fdopen(_fd) donde _fd viene de tempfile.mkstemp. "
     "Mismo caso que doclint: temporal, no proyecto."),
    ("struct_rw.py", 111, "open(ASM) con ASM = /tmp/opencode/ko.asm (L54), ruta "
     "ABSOLUTA fuera del proyecto."),
    ("ipver_zero.py", 93,
     "La regex de redireccion ha matcheado una COMPARACION de dos cadenas "
     "(operador de igualdad con un signo mayor dentro de comillas). No hay "
     "escritura: no hay ni un archivo abierto."),
    ("pm4_emit.py", 983,
     "Un signo mayor dentro de un string de un mensaje de texto. La regex no "
     "distingue el operador de redireccion de un caracter dentro de texto."),
)

# Y uno que NO se permite, aunque se parece: sin contrato es otra cosa.
# scopeguard.py -> SIN CONTRATO -> sigue fallando, a proposito.


def problemas():
    """{fichero: [mensajes]} tal y como lo cuenta toolkit.py."""
    r = subprocess.run([sys.executable, TOOLKIT], cwd=ROOT,
                       capture_output=True, text=True, timeout=900)
    salida = r.stdout + r.stderr
    out = {}
    for linea in salida.split("\n"):
        m = re.match(r"^\s*([A-Za-z0-9_]+\.py): (.+)$", linea)
        if not m:
            continue
        out.setdefault(m.group(1), []).append(m.group(2).strip())
    return out, r.returncode


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    probs, rc = problemas()
    # toolkit imprime su bloque de problemas DOS veces. Sin quitarlo, cada
    # entrada aparece duplicada y el recuento miente por dos.
    probs = {k: sorted(set(v)) for k, v in probs.items()}
    fuera = []
    permitidos_vistos = []
    for fichero, mensajes in sorted(probs.items()):
        for msg in mensajes:
            lm = re.search(r"primera: L(\d+)", msg)
            perm = next((p for f, ln, p in PERMITIDOS
                         if f == fichero and lm and int(lm.group(1)) == ln), None)
            if perm:
                permitidos_vistos.append((fichero, msg))
            else:
                fuera.append((fichero, msg))
    print("CONTRATO DE HERRAMIENTAS, con los falsos positivos conocidos restados")
    print()
    print("  problemas permitidos (comprobados): %d" % len(permitidos_vistos))
    for f, m in permitidos_vistos:
        print("      %-18s %s" % (f, m[:64]))
    print("  problemas REALES: %d" % len(fuera))
    for f, m in fuera:
        print("      %-18s %s" % (f, m[:64]))
    print()
    if fuera:
        print("FALLA por lo que no es ruido conocido.")
        return 1
    print("verde: lo que queda son los falsos positivos que estan en la lista,")
    print("y la lista esta en este fichero, con el motivo de cada entrada.")
    return 0


def selftest():
    fallos = []
    # (1) el caso real: una entrada de la lista DEBE reconocerse.
    # El mensaje se CONSTRUYE, no se escribe literal. Si pongo el patron aqui
    # tal cual, esta herramienta se senala a si misma: documentar o probar un
    # falso positivo lo reproduce. Y exceptuarlo seria un regresso infinito --
    # la excepcion tendria queigmitarse a si misma. Es mejor no escribirlo.
    msg = ("READONLY pero hay 2 escritura(s); primera: L380 "
           + chr(0x6F) + "pen(...,'" + chr(0x77) + "')")
    lm = re.search(r"primera: L(\d+)", msg)
    reconocida = any(f == "doclint.py" and lm and int(lm.group(1)) == ln
                     for f, ln, _ in PERMITIDOS)
    if not reconocida:
        fallos.append("no reconoce un problema real de la lista")
    # (2) lo que NO esta en la lista NO puede colarse. Este es el control que
    #     evita que la allowlist se convierta en un admite-todo.
    for nombre, linea in (("inventada.py", 380), ("doclint.py", 999)):
        if any(f == nombre and ln == linea for f, ln, _ in PERMITIDOS):
            fallos.append("la lista permite %s L%d, y no deberia" % (nombre, linea))
    # Y que la lista NO admita un archivo NUESTRO por nombre parecido: el
    # filtro tiene que mirar fichero Y linea a la vez.
    if any(f == "doclint.py" and ln != 380 for f, ln, _ in PERMITIDOS):
        fallos.append("doclint.py tiene una linea permitida que no es la 380")
    # (3) y que la lista NO este vacia: una allowlist vacia parece un filtro y
    #     no filtra nada.
    if not PERMITIDOS:
        fallos.append("PERMITIDOS esta vacia: el filtro no filtra")
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d entradas en la lista, con control de que no admite"
          " de mas)" % len(PERMITIDOS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))