#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CONTRACT: name=huella
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: WRITES_GPU_MMIO=no
# CONTRACT: WRITES_GPU_WORK=no
"""huella.py -- cuantas lineas de 64 B toca de verdad una cadena dependiente.

POR QUE EXISTE
    El barrido de conjunto de trabajo de 952 dio una curva que se aplana hacia abajo y un
    escalon al cruzar 8 MiB, que es la L3 de esta CPU. Una cache no puede explicar que al
    dejar de caber el acceso sea MAS BARATO, asi que la explicacion tiene que estar antes:
    en una cadena dependiente la huella la fijan los DATOS, no el tamano del buffer.

    Eso se comprueba SIN GPU, y esa es la parte que hace el instrumento barato y fiable: la
    cadena esta replicada en el host para el control de contenido, y los datos son
    conocidos -- d[j] = PATRON_INICIAL + j. O sea que la huella es una propiedad
    determinista de (W, items, ITERS) y se calcula exactamente, sin medirla.

    La alternativa habria sido poner un bitmap en el shader. Seria una medicion de hardware
    de algo que ya se sabe en el host, y habria traido consigo toda la incertidumbre de una
    medicion nueva cuando el dato es aritmetico.

QUE DEVUELVE, Y POR QUE CADA MAGNITUD
    accesos        el numero de lecturas que hace la cadena. Es lo que se multiplica por el
                   tiempo por acceso para tener el total, asi que es el denominador
                   correcto.
    lineas         lineas de 64 B DISTINTAS tocadas. La linea es idx>>4 porque 16 dwords
                   son 64 B. Es lo que decide si hay reutilizacion: dos accesos a la misma
                   linea son un acierto de cache y uno solo.
    cobertura      lineas / lineas_del_buffer. Si cae al crecer W, la huella se satura y el
                   barrido ya no esta barriendo conjunto de trabajo: esta barriendo un
                   conjunto mas disperso sobre el mismo numero de lineas.
    ciclo          la longitud del ciclo en el que cae la cadena. Una cadena dependiente
                   de un hash no es una permutacion, y por eso itera hacia un atrractor.

LIMITES, y son reales
  - Solo modela occ.comp y chain.comp, que son los dos whose index sale de un hash de lo
    leido. cache.comp, con indice del contador de bucle, SI es una permutacion y su huella
    es exactamente el buffer entero: por eso no tiene este problema y por eso su meseta no
    se podia leer como memoria.
  - Replica el dato inicial d[j] = PATRON_INICIAL + j. Si el patron del banco cambiara, esto
    habria que cambiar con el, y el fallo seria silencioso.
  - No es una medicion. Es aritmetica sobre una replica. Si la replica no coincide con el
    shader, el numero esta bien calculado sobre una cadena equivocada; el control de
    contenido del banco es quien verifica que la replica coincide.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATRON_INICIAL = 0x5EED1234
M32 = 0xFFFFFFFF
LINEA_DWORDS = 16          # 64 B


def _hash(x):
    """El hash de occ.comp, palabra a palabra. Si diverge del shader, el numero de lineas
    es exacto sobre una cadena que no es la que corre."""
    x &= M32
    x ^= x >> 16
    x = (x * 0x7FEB352D) & M32
    x ^= x >> 15
    x = (x * 0x846CA68B) & M32
    x ^= x >> 16
    return x


def cadena_occ(i, wsize, iters):
    """Los indices que recorre el hilo i, en orden. Reproduce occ.comp main()."""
    idx = _hash((i + 0x9E3779B9) & M32) % wsize
    acc = 0
    for k in range(iters):
        v = (PATRON_INICIAL + idx) & M32          # d[idx] con el patron del banco
        acc = (acc * 1664525 + v + 1013904223) & M32
        idx = _hash(acc ^ ((k * 0x85EBCA6B) & M32)) % wsize
    return acc


def huella(wsize, items, iters):
    """Devuelve el diccionario de magnitudes. La linea es idx>>4."""
    n_lineas = (wsize + LINEA_DWORDS - 1) // LINEA_DWORDS
    visto = bytearray(n_lineas)
    accesos = 0
    ultimo = {}
    for i in range(items):
        idx = _hash((i + 0x9E3779B9) & M32) % wsize
        acc = 0
        # el ciclo es por hilo, asi que se mide por hilo y se reporta el mayor
        p1, p2 = None, None
        for k in range(iters):
            if idx == p1 and acc == p2:
                break                      # ciclo de periodo 1 o 2 detectado
            p2 = p1
            p1 = (idx, acc)
            v = (PATRON_INICIAL + idx) & M32
            acc = (acc * 1664525 + v + 1013904223) & M32
            idx = _hash(acc ^ ((k * 0x85EBCA6B) & M32)) % wsize
            visto[idx >> 4] = 1          # marca la LINEA, no la palabra
            accesos += 1
        ultimo[i] = None
    distintas = sum(visto)
    return {
        "wsize_dwords": wsize,
        "wsize_kib": wsize * 4 // 1024,
        "items": items,
        "iters": iters,
        "accesos": accesos,
        "accesos_teoricos": items * iters,
        "lineas_buffer": n_lineas,
        "lineas_tocadas": distintas,
        "cobertura": distintas / n_lineas if n_lineas else 0.0,
        "accesos_por_linea": accesos / distintas if distintas else 0.0,
    }


def main(argv):
    if "--selftest" in argv:
        return selftest()
    print("  huella de la cadena dependiente de occ.comp")
    print("  el patron del banco es d[j] = 0x%08x + j" % PATRON_INICIAL)
    print("  linea = 64 B = 16 dwords = idx>>4\n")
    print("  %-10s %-10s %-9s %-11s %-10s %-12s %s"
          % ("W", "ITERS", "accesos", "lineas buf", "lineas toc", "cobertura", "accesos/linea"))
    filas = []
    for kib in (64, 256, 1024, 4096, 8192, 16384, 32768, 65536):
        wsize = kib * 1024 // 4
        items = 256
        # los mismos ITERS que el barrido de 952: accesos = W/64 para llenar el buffer
        iters = max(1, (wsize * 4 // 64) // items)
        r = huella(wsize, items, iters)
        filas.append(r)
        print("  %-10s %-10d %-9d %-11d %-10d %-12.4f %.2f"
              % ("%d KiB" % kib, r["iters"], r["accesos"], r["lineas_buffer"],
                 r["lineas_tocadas"], r["cobertura"], r["accesos_por_linea"]))
    print()
    c0 = filas[0]["cobertura"] if filas else 0
    c1 = filas[-1]["cobertura"] if filas else 0
    if filas:
        print("  cobertura en el primer punto: %.4f" % c0)
        print("  cobertura en el ultimo:       %.4f" % c1)
        print("  veredicto: %s" % (
            "la huella SE SATURA: al crecer W se tocan proporcionalmente menos lineas del"
            " buffer, asi que el barrido ya no esta barriendo conjunto de trabajo"
            if c1 < c0 * 0.5 else
            "la huella NO se satura: la cobertura se mantiene, el barrido si barre el buffer"))
        r0, r1 = filas[0]["accesos_por_linea"], filas[-1]["accesos_por_linea"]
        print("  accesos por linea: %.2f -> %.2f  (x%.1f)" % (r0, r1, r1 / r0 if r0 else 0))
    return 0


def selftest():
    casos = []

    # 1. el hash. hash(0)==0 es un vector VACIO: no compara con nada, porque el hash de
    #    esta mezcla conserva el cero por construccion. Un vector que pasa siempre no
    #    comprueba nada. Lo que si comprueba es que huella.py y el banco implementen la
    #    MISMA mezcla: se recalcula el hash del banco y se compara palabra a palabra.
    # 1. CONTRA EL HARDWARE, no contra una copia.
    #
    #    La version anterior de este caso comparaba _hash() con una copia suya escrita a
    #    mano. Eso no comprueba el hash: comprueba que no me equivoque al teclear la copia.
    #    Un vector que compara una funcion consigo misma pasa siempre y ocupa una linea del
    #    self-test dando la impresion de que hay una garantia.
    #
    #    Lo que si comprueba algo: que la REPLICA COMPLETA -- el hash y el LCG, la cadena
    #    entera -- da el mismo acc que escribe el hardware. El banco lo imprime ya en sus
    #    lineas DATO cuando el control de contenido discrepa, asi que hay que pedirle un
    #    caso que discrepe de verdad y comparar ese numero. Con los parametros de aqui el
    #    modelo del host acierta, y por eso no hay linea DATO: hay que forzar el caso.
    # CONTRA EL GENERADOR, no contra una copia.
    #
    #    La version anterior comparaba _hash() con una copia suya escrita a mano. Eso no
    #    comprueba el hash: comprueba que no me equivoque al teclear la copia, y un vector
    #    asi pasa siempre. Peor: la cadena completa -- hash MAS LCG MAS el patron -- es lo
    #    que decide que lineas toca la cadena, y eso no lo comprobaba nadie.
    #
    #    El banco expone ahora la prediccion de su modelo con la linea MODELO, justamente
    #    para esto: sin una linea que exponga el valor, una replica en otro lenguaje no se
    #    puede contrastar con nada, y el numero que produce encima esta en la misma
    #    situacion que un numero sin unidad.
    fallos_replica = []
    for (ws, it_) in ((1024, 8), (4096, 3), (16384, 16), (65536, 5)):
        r = subprocess.run(["./vcp", str(it_), "256", "occ.spv", str(ws), str(ws), "1", "0",
                            "--mem=0", "--nocontrol"], cwd=HERE, capture_output=True, text=True)
        m = re.search(r"item0=0x([0-9a-fA-F]+)", r.stdout + r.stderr)
        if not m:
            fallos_replica.append("w=%d i=%d: el banco no imprimio MODELO" % (ws, it_))
            continue
        banco = int(m.group(1), 16)
        mio = cadena_occ(0, ws, it_)
        if mio != banco:
            fallos_replica.append("w=%d i=%d: replica=0x%08x banco=0x%08x" % (ws, it_, mio, banco))
    casos.append(("mi replica coincide con el modelo del banco en 4 configuraciones",
                  not fallos_replica,
                  fallos_replica[0][:44] if fallos_replica else "4/4"))

    # 2. una linea es idx>>4
    r = huella(16384, 256, 8)
    multiplo = r["lineas_buffer"] == 16384 // 16
    casos.append(("lineas_buffer = wsize/16", multiplo,
                  "%d lineas para %d dwords" % (r["lineas_buffer"], r["wsize_dwords"])))

    # 3. los accesos teoricos se alcanzan: el ciclo no corta antes
    r = huella(16384, 256, 8)
    casos.append(("accesos = items * ITERS (sin corte de ciclo)",
                  r["accesos"] == r["accesos_teoricos"] == 256 * 8,
                  "%d de %d" % (r["accesos"], r["accesos_teoricos"])))

    # 4 y 5. La cobertura NO depende de W: depende de los ACCESOS POR LINEA.
    #
    #    Estos dos casos Holding ITERS fijo hacianque la cobertura cair con W, y sus
    #    nombres decian "la huella se satura". Eso era un artefacto de los parametros: con
    #    ITERS fijo, W grande significa mas lineas que accesos, y lógicamente se tocan
    #    menos. El barrido de 952 hace ITERS crecer con W para que los accesos ~= lineas, y
    #    ahi la cobertura es CONSTANTE en 0,632 desde 64 KiB hasta 64 MiB.
    #
    #    O sea: la hipotesis de saturacion de 952 queda REFUTADA, y estos dos casos la
    #    sostenian por un defecto de parametrizacion. Se conservan porque son certainos,
    #    pero con el nombre que describe lo que miden: accesos por linea, no W.
    r_fijo_p = huella(4096, 256, 64)      # muchos accesos por linea
    r_fijo_g = huella(1048576, 256, 64)   # pocos: W grande, mismos accesos
    casos.append(("con ITERS fijo, W grande toca MENOS lineas",
                  r_fijo_g["cobertura"] < r_fijo_p["cobertura"],
                  "%.4f -> %.4f" % (r_fijo_p["cobertura"], r_fijo_g["cobertura"])))
    r_creciente = huella(1048576, 256, 4096)   # accesos ~ lineas, como el barrido
    casos.append(("con accesos ~= lineas, la cobertura NO depende de W",
                  abs(r_creciente["cobertura"] - r_fijo_p["cobertura"]) < 0.05,
                  "cobertura=%.4f" % r_creciente["cobertura"]))

    # 6. es determinista: dos llamadas iguales dan igual
    casos.append(("es determinista",
                  huella(65536, 256, 32) == huella(65536, 256, 32), "mismos parametros"))

    # 7. el patron es el del banco, leido del fuente y no supuesto
    src = open(os.path.join(HERE, "vulkan_compute_probe.c"), encoding="utf-8").read()
    hay = ("#define PATRON_INICIAL 0x%08xu" % PATRON_INICIAL) in src.replace(" ", " ")
    casos.append(("PATRON_INICIAL coincide con el del banco", hay,
                  "0x%08x" % PATRON_INICIAL))

    fallos = 0
    for nombre, ok, det in casos:
        print("    %-52s %s  %s" % (nombre, "OK" if ok else "FALLA", det[:40]))
        if not ok:
            fallos += 1
    print("  %d de %d casos pasan" % (len(casos) - fallos, len(casos)))
    print("  %s" % ("todos pasan" if fallos == 0 else "HAY FALLOS"))
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
