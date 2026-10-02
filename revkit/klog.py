#!/usr/bin/env python3
"""
klog.py -- el log de arranque del kernel, como fuente de evidencia.

POR QUE EXISTE
-------------
Porque se passo una sesion entera markando F12 (el contenido de la page table)
como `NOT_AVAILABLE` sin mirar `journalctl -k -b`. Ese log tiene 80 lineas de
`amdgpu` con direcciones FISICAS que no estaban en ninguna otra fuente, y entre
ellas la de la tabla del GART, que resulta estar dentro de la ventana del BAR.

O sea: el observador que se buscaba existia, estava en un fichero de texto que
nadie abrio, y la frontera se cerro como-imposible. Esta herramienta existe para
que no vuelva a pasar: las direcciones de arranque son evidencia de primer
orden y son gratis de leer.

LO QUE HACE
------------
  lineas   las lineas de amdgpu (o de lo que se pida) del arranque
  dirs     las direcciones que aparecen, clasificadas por ESPACIO
  gart     donde esta la tabla del GART y si cabe en la ventana del BAR
  todo     las tres cosas, y el veredicto de si el observador existe

LA DISTINCION QUE MAS IMPORTA
----------------------------
Un espacio de direccion no es otro. La misma pagina de VRAM aparece con tres
nombres distintos en tres sitios del log y en tres sitios de la evidencia:

    PA de VRAM      0xF400000000 .. 0xF47FFFFFFF   la que ve la MC
    VA de VRAM      0x000100258000 .. 0x000100278600  la que usan los IB
    VA del GART     0xFF00000000  .. 0xFF0FFFFFFF

Confundirlas produce numeros que cuadran y preguntas equivocadas. `dirs` las
separa y dice de que espacio es cada una.

LO QUE NO HACE
--------------
No lee el hardware. No abre `resource0`. Esto solo lee texto del log, y su unico
efecto es decir SI el observador existe y DONDE. La lectura de la tabla es de
NIVEL 2 y esta en otro sitio, con su credencial.
"""
import argparse
import re
import subprocess
import sys

# Rangos que identifican a que espacio pertenece una direccion. El orden
# importa: se comprueban del mas especifico al mas general.
ESPACIOS = [
    ("PA de VRAM", 0xF400000000, 0xF400000000 + 2048 * 1024 * 1024 - 1),
    ("VA del GART", 0xFF00000000, 0xFF00000000 + 256 * 1024 * 1024 - 1),
    ("BAR de VRAM", 0x00000000, 0x00000000 + 256 * 1024 * 1024 - 1),
]


def log_amdgpu(patron="amdgpu", boot=True):
    """Devuelve las lineas del kernel que casan con el patron."""
    cmd = ["journalctl", "-k"]
    if boot:
        cmd.append("-b")
    cmd += ["--no-pager"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        print("no se pudo leer el log: %s" % e, file=sys.stderr)
        return []
    if r.returncode != 0:
        return []
    out = []
    for ln in r.stdout.split("\n"):
        if patron.lower() in ln.lower():
            out.append(ln.split("kernel: ", 1)[-1].strip())
    return out


def clasifica(direccion):
    """De que espacio de direcciones es. None si no se reconoce."""
    for nombre, lo, hi in ESPACIOS:
        if lo <= direccion <= hi:
            return nombre
    return None


def cmd_lineas(a):
    ls = log_amdgpu(a.patron)
    print("lineas de '%s' en el log del arranque: %d" % (a.patron, len(ls)))
    print()
    for ln in ls:
        print("  %s" % ln)
    return 0 if ls else 4


def cmd_dirs(a):
    ls = log_amdgpu(a.patron)
    # Los numeros en notacion de dmesg, con 0x o sin él.
    found = {}
    for ln in ls:
        for m in re.finditer(r"0x([0-9a-fA-F]{8,16})", ln):
            v = int(m.group(1), 16)
            found.setdefault(v, ln[:78])
    print("DIRECCIONES EN EL LOG, CLASIFICADAS POR ESPACIO")
    print("=" * 72)
    print()
    por = {}
    for v, ctx in sorted(found.items()):
        por.setdefault(clasifica(v) or "sin clasificar", []).append((v, ctx))
    for esp in ("PA de VRAM", "VA del GART", "sin clasificar", "BAR de VRAM"):
        if esp not in por:
            continue
        print("  %s" % esp)
        for v, ctx in por[esp]:
            print("    0x%012X   %s" % (v, ctx))
        print()
    return 0 if por else 4


def cmd_gart(a):
    ls = log_amdgpu(a.patron)
    tabla = vram = bar = None
    for ln in ls:
        m = re.search(r"GART of \d+M enabled \(table at 0x([0-9a-fA-F]+)\)", ln)
        if m:
            tabla = int(m.group(1), 16)
        m = re.search(r"VRAM: \d+M (0x[0-9a-fA-F]+) - (0x[0-9a-fA-F]+)", ln)
        if m:
            vram = (int(m.group(1), 16), int(m.group(2), 16))
        m = re.search(r"RAM=(\d+)M,\s*BAR=(\d+)M", ln)
        if m:
            # MiB -> bytes es multiplicar. int(str, base) NO es una
            # conversion de unidades: base debe estar entre 2 y 36.
            bar = int(m.group(2)) * 1024 * 1024

    print("TABLA DEL GART: ¿ES LEGIBLE POR CPU?")
    print("=" * 72)
    print()
    if tabla is None or vram is None or bar is None:
        print("  NO SE ENCONTRARON las tres piezas en el log.")
        print("  Sin tabla, sin rango de VRAM o sin tamaño de BAR no se puede")
        print("  decidir nada. Se sale con codigo 4, no con un 'no'.")
        return 4
    off = tabla - vram[0]
    print("  tabla GART (PA)     0x%012X" % tabla)
    print("  VRAM (PA)          0x%012X .. 0x%012X" % vram)
    print("  ventana del BAR    %d bytes = 0x%X" % (bar, bar))
    print()
    print("  offset dentro de VRAM : 0x%X = %d MiB" % (off, off // 1024 // 1024))
    cabe = 0 <= off < bar
    print("  cabe en el BAR       : %s" % ("SI" if cabe else "NO"))
    print()
    if cabe:
        print("  VEREDICTO: la tabla de page table del GART ES LEGIBLE por CPU")
        print("  a traves de resource0, en el offset 0x%X." % off)
        print()
        print("  Eso convierte F12 de 'no hay observador' a 'falta la lectura'.")
        print("  Leer el BAR es NIVEL 2 en la jerarquia del AGENTS.md.")
        print("  resource0 es root-only, asi que hace falta sudo.")
    else:
        print("  VEREDICTO: la tabla esta FUERA de la ventana del BAR.")
        print("  Habria que mirar otro observador, no este.")
    print()
    return 0 if cabe else 1


def main():
    ap = argparse.ArgumentParser(description="el log de arranque, como evidencia")
    ap.add_argument("cmd", choices=["lineas", "dirs", "gart", "todo"])
    ap.add_argument("--patron", default="amdgpu")
    a = ap.parse_args()
    if a.cmd in ("lineas", "todo"):
        rc = cmd_lineas(a)
        if a.cmd == "todo" and rc:
            return rc
    if a.cmd in ("dirs", "todo"):
        rc = cmd_dirs(a)
        if a.cmd == "todo" and rc:
            return rc
    if a.cmd in ("gart", "todo"):
        rc = cmd_gart(a)
        if a.cmd == "todo" and rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())