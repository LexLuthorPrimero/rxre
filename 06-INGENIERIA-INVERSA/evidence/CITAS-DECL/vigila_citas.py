#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VIGILANTE DE UN FICHERO QUE DESAPARECE Y REAPARECE.

Medido 2026-10-04: `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARATION.md` esta en
`os.listdir()` y `stat()` devuelve ENOENT segundos despues.  El disco es ext4
real (`/dev/sdb3`), sin overlay ni fuse, y no hay symlinks en la ruta, asi que
no es un problema de montaje.  ALGUIEN BORRA Y RECREA EL FICHERO.

Este vigilante NO repara nada y NO escribe el objetivo.  Solo registra, con
timestamp de reloj, cada transicion de estado que ve, y para cada una intenta
identificar al proceso que la produjo.

Salida: una linea por transicion, y un resumen al final.

    ./vigila_citas.py [segundos] [ruta]
"""
import hashlib
import os
import sys
import time

OBJETO_POR_DEFECTO = "08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md"


def estado(ruta):
    """Devuelve (estado, detalle).  Estados: AUSENTE, PRESENTE."""
    try:
        st = os.stat(ruta)
    except FileNotFoundError:
        return "AUSENTE", ""
    except OSError as e:
        return "ERROR:%s" % type(e).__name__, str(e)
    try:
        with open(ruta, "rb") as fh:
            b = fh.read()
    except OSError as e:
        return "ILEGIBLE:%s" % type(e).__name__, str(e)
    h = hashlib.sha256(b).hexdigest()[:16]
    return "PRESENTE", "sz=%d ino=%d sha=%s" % (len(b), st.st_ino, h)


def autor_de_la_transicion(ruta, segundos_atras):
    """Busca procesos que hayan tenido el fichero abierto para escritura.

    No es prueba: solo dice quien PODRIA ser.  Se lee /proc/<pid>/fd y se
    comprueba si el enlace apunta a la ruta (o a su inodo).
    """
    try: ino_objetivo = os.stat(ruta).st_ino
    except OSError:
        ino_objetivo = None
    rb = os.path.realpath(ruta)
    sospechosos = []
    ahora = time.time()
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fddir = "/proc/%s/fd" % pid
        try:
            fds = os.listdir(fddir)
        except OSError:
            continue
        for fd in fds:
            try:
                dest = os.readlink(os.path.join(fddir, fd))
            except OSError:
                continue
            if rb not in dest and (ino_objetivo is None or str(ino_objetivo) not in dest):
                continue
            try:
                st = os.stat("/proc/%s" % pid)
                edad = ahora - st.st_ctime
                if edad > segundos_atras * 4:
                    continue
                cmd = open("/proc/%s/cmdline" % pid, "rb").read().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            sospechosos.append((pid, cmd[:120], dest[:80]))
    return sospechosos


def main():
    segundos = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
    ruta = sys.argv[2] if len(sys.argv) > 2 else OBJETO_POR_DEFECTO
    raiz = os.path.dirname(ruta) or "."

    print("vigila %s durante %.0f s" % (ruta, segundos))
    print("raiz del proyecto: %s" % os.path.realpath(os.path.dirname(raiz) or "."))
    transiciones = 0
    t0 = time.time()
    ultimo_estado, ultimo_detalle = None, ""
    ultimo_cambio = 0.0
    while time.time() - t0 < segundos:
        est, det = estado(ruta)
        ahora = time.time()
        if est != ultimo_estado or det != ultimo_detalle:
            transiciones += 1
            dt = ahora - ultimo_cambio if ultimo_cambio else 0.0
            print("[%8.3f s]  %-8s  dt=%7.3f  %s" % (ahora - t0, est, dt, det))
            if ultimo_estado is not None:
                sos = autor_de_la_transicion(ruta, max(dt, 1.0))
                if sos:
                    for pid, cmd, dest in sos[:4]:
                        print("              posible autor: pid=%s fd->%s" % (pid, dest))
                        print("                           cmd=%s" % cmd)
                else:
                    print("              posible autor: NADIE lo tenia abierto (ventana %.3fs)" % dt)
            ultimo_estado, ultimo_detalle = est, det
            ultimo_cambio = ahora
        time.sleep(0.05)

    print("")
    print("RESUMEN")
    print("  transiciones observadas : %d" % transiciones)
    est, det = estado(ruta)
    print("  estado final            : %s  %s" % (est, det))
    print("  NOTA: el fichero solo cambia si ALGO lo esta cambiando; un fichero")
    print("  que no se toca no alterna entre PRESENTE y AUSENTE.")


if __name__ == "__main__":
    main()