#!/usr/bin/env python3
# CONTRACT: name=commitmsg_lint
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""commitmsg_lint -- residuos de codificacion en mensajes de commit.

POR QUE EXISTE, y no es COSMETICO

    Un mensaje de commit corrupto NO es un detalle de forma. El mensaje es parte
    del REGISTRO: es lo que se lee cuando alguien quiere saber por que se hizo
    algo, y un `FALSA:五次 el validador` no dice por que se hizo nada.

    Tres veces en una sola sesion un texto generado a maquina salio con ideogramas
    o sustitutos de CJK incrustados en mitad de una palabra espanola, y las tres
    veces el arreglo llego TARDE: el commit ya estaba hecho y hubo que enmendar.

POR QUE NO BASTA CON MIRARLO ANTES DE COMMITEAR

    Porque es un paso que se olvida, y porque el que lo hace es el mismo que
    acaba de escribir el texto y ya lo tiene en la cabeza. Un control que depende
    de que te acuerdes es un control que se salta.

    Asi que hay dos usos y los dos importan:
      --commits N   audita los ultimos N mensajes. Se integra en run_all, de modo
                    que un residuo no puede QUEDARSE: sale en el runner.
      --file F      audita un mensaje antes de existir, para no tener que
                    enmendar despues.

LO QUE DETECTA, y lo que NO

    Detecta: ideogramas CJK, Hangul y las zonas de puntuacion CJK.
    NO detecta: un mensaje en chino entero escrito a proposito, que es una
    decision distinta y legitima. Esto no es "los commits tienen que estar en
    espanol": es "no hay texto de otro idioma pegado dentro de una palabra".
"""
import os
import re
import subprocess
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"

# Las zonas. Y hay una que FALTA, y el self-test la encontro.
#
# Primero puse (0x2E80-0x2FFF) creyendo que cubria los ideogramas. No: ese bloque
# son Radicales Suplement. Los ideogramas unificados viven en U+4E00-U+9FFF, y
# `chr(0x4e94)` -- 五, uno de los dos caracteres que se me colaron HOY dos veces --
# cae al otro lado del hueco. Es decir: la herramienta no habria detectado
# precisamente los residuos que fue escrita para detectar, y habria pasado
# --self-test con los vectoresbien escritos.
#
# Un self-test cuyo vector NO falla cuando deberia no es un self-test: es una
# decoracion. Este fallo se ve porque el vector de control usa chr() en vez de
# una cadena literal, y chr() no se puede "arreglar" por accidente.
ZONAS = (
    (0x2E80, 0x2FFF),      # Radicales Suplement y variantes
    (0x3000, 0x303F),      # puntuacion CJK, incluye el espacio U+3000
    (0x4E00, 0x9FFF),      # ideogramas unificados  <- LA QUE FALTABA
    (0xAC00, 0xD7AF),      # silabas Hangul
    (0xFF01, 0xFF60),      # formas de anchura completa
)


def residuos(texto):
    """[(offset, caracter, U+XXXX)] de todo lo que no deberia estar ahi."""
    out = []
    for i, c in enumerate(texto):
        o = ord(c)
        if any(a <= o <= b for a, b in ZONAS):
            out.append((i, c, "U+%04X" % o))
    return out


def contexto(texto, pos, ancho=26):
    ini = max(0, pos - ancho)
    return texto[ini:pos + ancho].replace("\n", "\\n")


def commits(n):
    """Los ultimos n mensajes, en orden cronologico inverso."""
    try:
        r = subprocess.run(["git", "log", "-n", str(n), "--format=%H%x00%B%x00%x00"],
                           cwd=ROOT, capture_output=True, text=True,
                           timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    partes = r.stdout.split("\x00")
    # %H, %B, separador -> de tres en tres
    return [(partes[i].strip(), partes[i + 1])
            for i in range(0, len(partes) - 2, 3) if partes[i].strip()]


def auditar_texto(nombre, texto):
    rs = residuos(texto)
    if not rs:
        return True, []
    problemas = []
    for pos, c, cp in rs:
        problemas.append("%s: %s (%s) -> ...%s..."
                         % (nombre, c, cp, contexto(texto, pos)))
    return False, problemas


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()

    if any(a.startswith("--commits") for a in argv):
        n = 20
        for a in argv:
            if a.startswith("--commits="):
                n = int(a.split("=", 1)[1])
        lista = commits(n)
        if not lista:
            print("no se pudieron leer los commits: rc!=0 o no hay historial")
            return 2
        malos = 0
        for sha, cuerpo in lista:
            ok, probs = auditar_texto(sha[:10], cuerpo)
            if not ok:
                malos += 1
                for p in probs:
                    print("  %s" % p)
        print()
        print("auditados %d mensajes | con residuos: %d" % (len(lista), malos))
        if malos:
            print()
            print("Un mensaje corrupto NO es cosmetico: el mensaje es el registro.")
            print("Enmendar con:  git commit --amend -F <fichero>")
            return 1
        print("sin residuos")
        return 0

    if "--file" in argv:
        ruta = argv[argv.index("--file") + 1]
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        ok, probs = auditar_texto(os.path.basename(ruta), texto)
        for p in probs:
            print("  %s" % p)
        print("residuos: %d" % len(probs))
        return 0 if ok else 1

    print("usa --commits[=N] o --file FICHERO")
    return 0


# Los vectores. El segundo es el que importa: sin el, un linter que solo sabe
# decir "si" se pasa con un archivo entero en cualquier idioma.
VECTORES = (
    ("texto limpio en espanol", "FALSA: cinco veces el validador", 0),
    ("el que se colaba de verdad", "FALSA:" + chr(0x4e94) + chr(0x6b21) + " el validador", 2),
    ("otro con espacio CJK", "\u3000al principio de la frase", 1),
    ("coreano pegado", "la palabra \uc548\ub155 en medio", 2),
    ("acentos y enye son legales", "ma\u0303s, a\u0308nimo, r\u0303pido", 0),
    ("mensaje vacio", "", 0),
)


def selftest():
    fallos = []
    # (1) casos reales: tienen que Contar
    for nombre, texto, esperados in VECTORES:
        if len(residuos(texto)) != esperados:
            fallos.append("%s: esperaba %d residuos y hay %d"
                          % (nombre, esperados, len(residuos(texto))))
    # (2) el CONTROL NEGATIVO: texto espanol legitimo con acentos, enye y
    #     tildes compuestas NO puede salir como sucio. Un linter que accuse a la
    #     "~" o a la "n" con virgulilla seria inservible en un idioma con
    #     ortografia.
    if residuos("mas " + chr(0x0303) + " ano " + chr(0x0303) + "nimia"):
        fallos.append("las tildes combinantes salen como residuo: un linter que "
                      "acusara a la ortografia espanola no serviria aqui")
    # (3) y el control de que el self-test no este VACIO: sin vectores con
    #     residuos esperados, un linter que devuelve siempre [] pasaria.
    if not any(n > 0 for _, _, n in VECTORES):
        fallos.append("ningun vector tiene residuos esperados: el test es vacio")
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d vectores, %d con residuos, y control de tildes)"
          % (len(VECTORES), sum(1 for _, _, n in VECTORES if n > 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))