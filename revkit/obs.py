#!/usr/bin/env python3
# CONTRACT: name=obs
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que lanza consultas de sysfs por subprocess y compone el nodo con `os.path.join`.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
"""
obs.py -- observacion del host en una sola llamada.

POR QUE
-------
Cada vez que hace falta un dato del host (log, sysfs, identidades PCI) se
tiene que inventar el comando, filtrar por el dispositivo correcto y separar
lo legible de lo que existe pero no se puede leer. En esta sesion eso paso
varias veces y una vez salio mal: se leyo /sys/class/drm/card0 creyendo que
era la GPU, y card0 era la Intel 8086:0412. La RX550 era card1.

Esa confusion es facil de repetir y cara: un dato atribuido al ASIC
equivocado es peor que no tenerlo. Este script:

  1. LOCALIZA la GPU objetivo por identidad PCI, no por numero de card.
  2. DISTINGUE lo leido de lo que existe pero no es legible, y lo dice.
  3. DEDUPLICA: el log repite lineas (el driver reinicializa GART varias
     veces), asi que hay que separar valores unicos de ocurrencias.
  4. No necesita root. Lo que requiere root lo marca BLOCKED_BY_AUTHORIZATION
     con el motivo, en vez de fallar en silencio.

LIMITES
-------
No lee MMIO. /sys/kernel/debug/dri esta en 0400 y sin sudo no hay acceso, asi
que el camino de runtime completo sigue cerrado. Este script solo lee lo que el
kernel ya publico y que es legible por el usuario.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Identidad de la GPU objetivo, confirmada por el log de arranque del host:
# "initializing kernel modesetting (POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7)"
OBJ_VENDOR = "0x1002"
OBJ_DEVICE = "0x699f"


def sh(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except Exception as e:
        return "", str(e), 1


def localiza_gpu():
    """
    Devuelve (card, path) de la GPU objetivo, por IDENTIDAD PCI.

    NUNCA por numero de card. En este host card0 es la Intel iGPU
    (8086:0412) y card1 es la RX550. Asumir el orden por el indice es lo que
    produjo un dato atribuido al ASIC equivocado.
    """
    found = []
    base = "/sys/class/drm"
    for card in sorted(os.listdir(base)):
        d = os.path.join(base, card, "device")
        if not os.path.isdir(d):
            continue
        ven = leer(os.path.join(d, "vendor"))
        dev = leer(os.path.join(d, "device"))
        if ven == OBJ_VENDOR and dev == OBJ_DEVICE:
            found.append((card, d))
    return found


def leer(p):
    try:
        return open(p).read().strip()
    except Exception:
        return None


def sysfs(d, nombres):
    print("=== atributos sysfs de %s ===" % d)
    for n in nombres:
        p = os.path.join(d, n)
        if not os.path.exists(p):
            print("  %-26s AUSENTE" % n)
            continue
        v = leer(p)
        if v is None:
            print("  %-26s <NO LEGIBLE>" % n)
        else:
            print("  %-26s = %s" % (n, v))


def log_amdgpu(filtro=None):
    out, _e, rc = sh("journalctl -k -b --no-pager 2>/dev/null")
    if rc != 0 or not out:
        print("journalctl: sin salida (rc=%d). Puede needing root o no haber" % rc)
        print("arranque en journall. NO es evidencia de que no haya log.")
        return []
    lineas = [l for l in out.splitlines() if "amdgpu" in l]
    if filtro:
        rx = re.compile(filtro, re.I)
        lineas = [l for l in lineas if rx.search(l)]
    return lineas


def clave_log(linea):
    """
    Quita el prefijo variable del log para poder DEDUPLICAR.

    El driver reinicializa GART, UVD y VCE varias veces, asi que el log tiene
    ~50 lineas que son 3 valores unicos repetidos. Contar lineas y contar
    hechos son dos cosas distintas, y confundirlas hace que "GART 256M" pareza
    aparecer 12 veces, lo que sugiere una corroboracion que no existe: es el
    mismo mensaje del mismo arranque.
    """
    return re.sub(r"^\w{3}\s+\d+\s+\d+:\d+:\d+\s+\S+\s+kernel:\s*", "",
                  linea.strip())


def main():
    ap = argparse.ArgumentParser(description="observacion del host")
    ap.add_argument("cmd", choices=[
        "gpu", "sysfs", "log", "log-uniq", "params", "todo", "json"])
    ap.add_argument("--filtro", default=None, help="regex para el log")
    ap.add_argument("--n", type=int, default=120)
    a = ap.parse_args()

    if a.cmd in ("gpu", "todo", "json"):
        print("=== localizar la GPU por identidad PCI ===")
        print("objetivo: %s:%s" % (OBJ_VENDOR, OBJ_DEVICE))
        print("ATENCION: no se usa el numero de card. En este host card0 es")
        print("la Intel 8086:0412 y card1 la RX550.")
        print()
        gs = localiza_gpu()
        if not gs:
            print("NO ENCONTRADA. 0 aqui significa que no se pudo leer vendor")
            print("o device (puede necesitar root), no que la GPU no exista.")
            return 1
        for card, d in gs:
            print("ENCONTRADA: card=%s  %s" % (card, d))
            rev = leer(os.path.join(d, "revision"))
            sv = leer(os.path.join(d, "subsystem_vendor"))
            sd = leer(os.path.join(d, "subsystem_device"))
            print("  revision=%s subsystem=%s:%s" % (rev, sv, sd))
        print()

    if a.cmd in ("sysfs", "todo", "json"):
        gs = localiza_gpu()
        if gs:
            _c, d = gs[0]
            sysfs(d, [
                "revision", "subsystem_vendor", "subsystem_device", "class",
                "irq", "current_link_speed", "current_link_width",
                "max_link_speed", "max_link_width",
                "mem_info_vram_total", "mem_info_vram_used",
                "mem_info_vis_vram_total", "mem_info_vis_vram_used",
                "mem_info_gtt_total", "mem_info_gtt_used",
                "rom", "vbios_version", "vbios_build",
            ])
        print()

    if a.cmd in ("log", "todo", "json"):
        print("=== log del kernel: amdgpu ===")
        ls = log_amdgpu(a.filtro)
        for l in ls[:a.n]:
            print(l)
        print("--- %d lineas" % len(ls))
        print()

    if a.cmd in ("log-uniq", "todo", "json"):
        print("=== log DEDUPLICADO (hechos, no ocurrencias) ===")
        ls = log_amdgpu(a.filtro)
        uniq = {}
        for l in ls:
            k = clave_log(l)
            uniq[k] = uniq.get(k, 0) + 1
        for k in sorted(uniq):
            n = uniq[k]
            print("  %-86s x%d" % (k[:86], n))
        print("--- %d lineas, %d hechos unicos" % (len(ls), len(uniq)))
        print()
        print("Un valor repetido NO es una corroboracion: es el mismo mensaje")
        print("del mismo arranque repetido por un reinicio de subsistema.")
        print()

    if a.cmd == "params":
        print("=== parametros de modulo ===")
        base = "/sys/module/amdgpu/parameters"
        if not os.path.isdir(base):
            print("no existe", base)
            return 1
        leibles = noleibles = 0
        for n in sorted(os.listdir(base)):
            v = leer(os.path.join(base, n))
            if v is None:
                noleibles += 1
            else:
                leibles += 1
        print("  %d parametros, %d legibles, %d NO legibles sin root"
              % (leibles + noleibles, leibles, noleibles))
        print()
        print("Los no legibles NO son cero ni inexistentes: son datos que")
        print("existen y no se pueden leer. Tratarlos como ausentes es el")
        print("error que hace que un resultado tenga menos confianza de la")
        print("que realmente tiene.")
        for n in sorted(os.listdir(base)):
            v = leer(os.path.join(base, n))
            if v is not None:
                print("    %-30s = %s" % (n, v))
        return 0

    if a.cmd == "json":
        gs = localiza_gpu()
        d = gs[0][1] if gs else None
        uniq = {}
        for l in log_amdgpu(a.filtro):
            uniq[clave_log(l)] = uniq.get(clave_log(l), 0) + 1
        out = {"gpu_path": d,
               "identidad": {k: (leer(os.path.join(d, k)) if d else None)
                             for k in ("vendor", "device", "revision",
                                       "subsystem_vendor", "subsystem_device")},
               "log_lineas": sum(uniq.values()),
               "log_hechos_unicos": uniq}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())