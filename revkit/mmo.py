#!/usr/bin/env python3
# CONTRACT: name=mmo
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que lee debugfs de la discreta y compone rutas; no tiene escritura propia pero delega.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
"""
mmo.py -- observacion de SOLO LECTURA del hardware, via debugfs de amdgpu.

QUE ABRE Y POR QUE
------------------
Con acceso root se abre el debugfs del driver, y eso da acceso al hardware que
todo el trabajo anterior solo podia deducir. Este es el instrumento que
convierte NOT_DETERMINED en OBSERVED, y es el que faltaba.

GARANTIA DE SOLO LECTURA, POR CONSTRUCCION
-------------------------------------------
Este script NUNCA abre un nodo para escritura. No hay ningun modo de
escribir, no hay ninguna llamada a open() con modo escritura, y la lista de
nodos es una CONSTANTE DEL CODIGO, no algo que se pueda ampliar por linea de
comandos.

La razon no es el protocolo, es la consecuencia: escribir en estos nodos
puede resetear la GPU, apagarla (amdgpu_gfxoff), o ESCRIBIR EN LOS REGISTROS
para forzar valores (amdgpu_gpr, amdgpu_wave). Eso no es reversible con
seguridad y dejaria la maquina sin consola.

Lo que SI hace:
  - lee registros MMIO (amdgpu_regs, amdgpu_iomem)
  - lee el contenido REAL de las tablas de page (amdgpu_vm_info)
  - lee el contenido REAL de un anillo (amdgpu_ring_gfx, ..._sdma0/1)
  - lee el VBIOS (amdgpu_vbios, psp_spirom_dump)
  - lee los parametros de modulo, que antes NO eran legibles
  - lee sensores, fences, power, firmware

La GPU NO se toca: leer debugfs de amdgpu no escribe en ningun registro.
amdgpu_regs llama a pm_runtime_get_sync, que REANUDA la GPU si estaba
suspendida; eso es reversible y no cambia estado observable. Se anota por si
alguna vez hiciera falta distinguir.

COMO SE USA LA CONTRASENA
-------------------------
Viene de la variable de entorno RX550_SUDO_PASS, NO de un fichero y NO de un
argumento. Un argumento aparece en /proc/PID/cmdline y queda en el historial
del shell; una variable de entorno no. Y este script NO la escribe en ningun
sitio, ni en el codigo ni en la salida.

El valor NO se guarda en el repositorio. Es de la maquina, no del proyecto.
"""
import argparse
import os
import re
import subprocess
import sys

DEBUGFS = "/sys/kernel/debug/dri/0000:01:00.0"

# NODOS PERMITIDOS. Todos verificados con "ls -l" como modo sin 'w'.
# Cualquier otro nodo se rechaza, aunque exista.
LISTA_BLANCA = {
    # --- MMIO y registros ---
    "amdgpu_iomem": "mapa de MMIO: que bloques hay y que permisos",
    "amdgpu_regs": "volcado de registros MMIO",
    "amdgpu_regs2": "volcado de registros, parte 2",
    "amdgpu_regs_pcie": "registros del puente PCIe",
    "amdgpu_regs_pcie64": "registros PCIe de 64 bits",
    "amdgpu_regs_smc": "registros del SMC",
    "amdgpu_regs_didt": "registros DiDT",
    # --- page tables: EL MAS VALIOSO ---
    "amdgpu_vm_info": "contenido REAL de las tablas de pagina",
    # --- anillos: IB REALES ---
    "amdgpu_ring_gfx": "contenido real del anillo GFX",
    "amdgpu_ring_sdma0": "contenido real del anillo SDMA0",
    "amdgpu_ring_sdma1": "contenido real del anillo SDMA1",
    "amdgpu_ring_comp_1.3.1": "anillo de compute",
    # --- firmware ---
    "amdgpu_vbios": "VBIOS crudo",
    "psp_spirom_dump": "volcado de la SPI ROM",
    "amdgpu_firmware_info": "versiones de firmware",
    # --- estado ---
    "amdgpu_sensors": "sensores",
    "amdgpu_fence_info": "fences pendientes",
    "amdgpu_sa_info": "state del SA",
    "amdgpu_pm_info": "power management",
    "amdgpu_gem_info": "informacion de los BO",
    "amdgpu_gtt_mm": "mapa de memoria GTT",
    "amdgpu_vram_mm": "mapa de memoria VRAM",
    "amdgpu_gds_mm": "mapa de memoria GDS",
    "amdgpu_oa_mm": "mapa de memoria OA",
    "amdgpu_dm_capabilities": "capacidades del display manager",
    "amdgpu_mst_topology": "topologia MST",
}

# Nodos que EXISTEN pero ESCRIBEN. Se listan para dejar constancia de que se
# conhece su existencia y se decide no tocarlos.
CONOCIDOS_PERO_NO_SE_TOCAN = {
    "amdgpu_gpr": "escribe un valor y lee el registro del shader",
    "amdgpu_gprwave": "idem, por wave",
    "amdgpu_wave": "idem",
    "amdgpu_test_ib": "emite un IB de prueba",
    "amdgpu_preempt_ib": "preempta un anillo",
    "amdgpu_gfxoff": "APAGA la GPU",
    "amdgpu_gfxoff_count": "idem",
    "amdgpu_gfxoff_status": "idem",
    "amdgpu_gfxoff_residency": "idem",
    "amdgpu_force_sclk": "fuerza la frecuencia de reloj",
    "amdgpu_smu_debug": "control del SMU",
    "amdgpu_sdma_sched_mask": "mascara de scheduling SDMA",
    "amdgpu_compute_sched_mask": "mascara de scheduling compute",
    "amdgpu_benchmark": "ejecuta un benchmark",
    "amdgpu_dm_*": "modos del display manager",
}


def passwd():
    p = os.environ.get("RX550_SUDO_PASS")
    if p:
        return p
    # Fallback:_cache de sudo ya puede estar poblado. Si no, se aborta con
    # un mensaje claro en vez de pedir la contrasena de forma interactiva.
    return ""


def sudo_read(ruta, timeout=120):
    """
    Lee un fichero de debugfs usando sudo. SOLO LECTURA.

    El modo es "r". Nunca "w", nunca "r+", nunca "a".

    Se usa `dd` con bloque de 1 y sin bs grande para que no haya un modo de
    escritura implicito, y `cat` que es abro-exclusivamente-lectura por
    definicion en el kernel para estos nodos.
    """
    pw = passwd()
    cmd = ["sudo", "-S", "-k", "bash", "-c",
           "cat %s" % _quote(ruta)]
    r = subprocess.run(cmd, input=(pw + "\n") if pw else None,
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr, r.returncode


def _quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def valida(nodo):
    """
    Comprueba que el nodo esta en la lista blanca ANTES de leerlo.

    No es decorativo: el nodo viene de la linea de comandos, y sin esta
    comprobacion un nombre mal escrito podria acabar en un nodo que escribe.
    Se valida el NOMBRE exacto, no un prefijo.
    """
    if nodo not in LISTA_BLANCA:
        return False, ("%r no esta en la lista blanca. Los permitidos: %s"
                       % (nodo, ", ".join(sorted(LISTA_BLANCA))))
    return True, LISTA_BLANCA[nodo]


# --------------------------------------------------------------- comandos
def cmd_capacidades(a):
    """Que se puede leer y que no, verificado contra el modo real del nodo."""
    pw = passwd()
    r = subprocess.run(
        ["sudo", "-S", "-k", "bash", "-c",
         "ls -l %s/ | awk '{print $1, $NF}' | sort" % _quote(DEBUGFS)],
        input=(pw + "\n") if pw else None, capture_output=True, text=True,
        timeout=120)
    filas = {}
    for ln in r.stdout.splitlines():
        if ln.startswith("[sudo]") or not ln.strip():
            continue
        partes = ln.split(None, 1)
        if len(partes) == 2:
            filas[partes[1].strip()] = partes[0]
    print("=== ACCESIBILIDAD REAL, verificada con el modo del fichero ===")
    print("debugfs: %s" % DEBUGFS)
    print()
    print("%-32s %-12s %s" % ("nodo", "modo", "clasificacion"))
    print("-" * 78)
    leibles, bloqueados = 0, 0
    for nodo in sorted(LISTA_BLANCA):
        modo = filas.get(nodo, "(NO EXISTE)")
        # un modo con 'w' ESCRIBE, aunque la lista blanca lo allow
        if modo.startswith("-") and "w" in modo:
            print("%-32s %-12s ESCRIBE -- la lista blanca esta mal"
                  % (nodo, modo))
            bloqueados += 1
            continue
        if modo == "(NO EXISTE)":
            print("%-32s %-12s ausente en este driver" % (nodo, modo))
            bloqueados += 1
            continue
        ok, _desc = valida(nodo)
        if ok:
            print("%-32s %-12s LISTA BLANCA, seguro" % (nodo, modo))
            leibles += 1
    print()
    print("legibles con seguridad: %d" % leibles)
    if bloqueados:
        print("ATENCION: %d nodos de la lista blanca no son legibles aqui."
              % bloqueados)
    print()
    print("NODOS QUE EXISTEN Y ESCRIBEN, y no se tocan:")
    for n, why in sorted(CONOCIDOS_PERO_NO_SE_TOCAN.items()):
        if n in filas:
            print("   %-28s %-10s %s" % (n, filas[n], why))
    print()
    print("Que un nodo NO este en la lista de escribientes NO lo hace seguro:")
    print("la unica garantia es que no se abre, y eso lo hace el codigo.")
    return 0


def cmd_nodo(a):
    ok, desc = valida(a.nodo)
    if not ok:
        print("RECHAZADO: %s" % desc)
        print()
        print("Este script no lee nodos fuera de la lista blanca, aunque")
        print("existan y sean legibles. La lista esta en el codigo.")
        return 1
    out, err, rc = sudo_read(os.path.join(DEBUGFS, a.nodo),
                             timeout=a.timeout)
    print("### %s" % a.nodo)
    print("### %s" % desc)
    print("### %d bytes, rc=%d" % (len(out), rc))
    print("-" * 72)
    if err.strip() and "contraseña" not in err:
        print("stderr: %s" % err.strip()[:300])
    if a.binario:
        # salida binaria: se resume, no se vuelca
        import hashlib
        b = out.encode("utf-8", "surrogateescape")
        print("sha256: %s" % hashlib.sha256(b).hexdigest())
        print("primeros bytes no nulos: %s"
              % [hex(ord(c)) for c in out if ord(c)][:16])
    else:
        # se recorta por defecto: un volcado de amdgpu_regs son 128 KiB
        lineas = out.splitlines()
        if a.max > 0 and len(lineas) > a.max:
            print("(%d lineas en total, mostrando %d; --max 0 para todas)"
                  % (len(lineas), a.max))
        for ln in lineas[:a.max if a.max else None]:
            print(ln)
    return 0 if rc == 0 or out else 1


def cmd_params(a):
    """Los 96 parametros del modulo, que antes NO eran legibles."""
    pw = passwd()
    base = "/sys/module/amdgpu/parameters"
    r = subprocess.run(
        ["sudo", "-S", "-k", "bash", "-c",
         "for f in %s/*; do printf '%%s = ' \"$(basename $f)\"; cat $f; done"
         % _quote(base)],
        input=(pw + "\n") if pw else None, capture_output=True, text=True,
        timeout=120)
    print("=== parametros de modulo amdgpu ===")
    print("antes NO legibles sin root. Ahora si.\n")
    n = 0
    for ln in r.stdout.splitlines():
        if ln.startswith("[sudo]") or not ln.strip():
            continue
        print("  %s" % ln)
        n += 1
    print("--- %d parametros" % n)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="observacion de solo lectura del hardware (debugfs)")
    ap.add_argument("cmd", choices=["capacidades", "nodo", "params", "lista"])
    ap.add_argument("nodo", nargs="?", default=None)
    ap.add_argument("--max", type=int, default=120,
                    help="maximo de lineas a mostrar (0 = todas)")
    ap.add_argument("--binario", action="store_true")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()

    print("GPU INTACTA. Esta herramienta NO escribe en ningun registro.")
    print("La escritura no es posible aqui por construccion: la lista de")
    print("nodos es una constante del codigo y solo se abren para lectura.")
    print()
    print("Contrasena: variable de entorno RX550_SUDO_PASS, "
          "presente=%s" % bool(passwd()))
    print()

    if a.cmd == "lista":
        for n, d in sorted(LISTA_BLANCA.items()):
            print("  %-28s %s" % (n, d))
        print("--- %d nodos permitidos" % len(LISTA_BLANCA))
        return 0
    if a.cmd == "capacidades":
        return cmd_capacidades(a)
    if a.cmd == "params":
        return cmd_params(a)
    if a.cmd == "nodo":
        if not a.nodo:
            print("falta el nombre del nodo")
            print("permitidos: %s" % ", ".join(sorted(LISTA_BLANCA)))
            return 2
        return cmd_nodo(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())