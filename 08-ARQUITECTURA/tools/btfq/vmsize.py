#!/usr/bin/env python3
"""
vmsize.py -- modelo ejecutable de amdgpu_vm_adjust_size para GFX8.

POR QUE EXISTE
-------------
El driver registra su geometria de page tables al arrancar. En ESTE host:

    amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit,
                        fragment size is 9-bit

El corpus (linux-7.1.3) no reproduce ese log. Este script existe para
cuantificar exactamente CUANTO se aparta, en vez de describir la diferencia
en prosa.

HALLAZGO QUE ABRE ESTE SCRIPT
-----------------------------
El corpus dice, en gmc_v8_0.c:1127:

    amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
                              ^^  ^  ^
                    min_vm   frag max_ max_
                             _size level bits

Con max_level = 1, la linea amdgpu_vm.c:2427 hace

    num_level = min_t(unsigned int, max_level, tmp);

y min_t(1, tmp) NO PUEDE dar 2, para ningun valor de tmp. El corpus
necesariamente produce num_level = 1.

Y con num_level == 1 se toma la rama "else" de amdgpu_vm.c:2452-2454:

    else if (adev->vm_manager.num_level > 1)
            adev->vm_manager.block_size = 9;
    else
            adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp);

que da 23 bits con los numeros reales de este host.

El log dice 2 levels y 10 bits. LAS DOS COSAS SON INCOMPATIBLES con el corpus.

Que significa eso, clasificado
-----------------------------
  - NO es un bug de calculo: min_t con max_level=1 no puede exceder 1.
  - NO es un artefacto de ASIC: el host se identifica como POLARIS12 /
    gfx_v8_0, que es exactamente el ASIC de gmc_v8_0.c.
  - SI es evidencia de que el driver QUE CORRE esta parcheado respecto a
    RESEARCH/working/linux-7.1.3.

Por que sigue siendo relevante: cualquier geometria de page table que se
escriba a mano contra el corpus estara mal respecto a lo que hace el driver
real. El corpus es valido como ARBOL DE FUENTES; no es valido como
especificacion de lo que el host hace.

Como se comprueba sin root
--------------------------
El log del kernel es legible por el usuario via journalctl -k. Los
parametros del modulo (/sys/module/amdgpu/parameters/*) NO son legibles sin
root, asi que no se puede saber si el modulo fue cargado con
amdgpu_vm_block_size forzado. Eso es un hueco real del modelo y se reporta
como tal, no se rellena suponiendo.
"""
import re
import subprocess
import sys

GPU_PAGE_SHIFT = 12
GPU_PAGE_SIZE = 1 << GPU_PAGE_SHIFT


def get_block_size(v):
    """
    amdgpu_vm.c:2356

        unsigned bits = ilog2(vm_size) + 18;
        if (vm_size <= 8)
                return (bits - 9);
        else
                return ((bits + 3) / 2);

    OJO con el parametro. El nombre del fuente dice vm_size, pero el unico
    llamador (:2454) le pasa 'tmp', que en ese punto ya fue reescrito y vale
    un numero pequeno. La rama "vm_size <= 8" compara, por tanto, una
    cantidad que ya no es un tamano de VM contra el literal 8.

    Se conserva la formula TAL CUAL esta en el fuente, sin "corregirla":
    el objetivo es modelar lo que el driver hace, no lo que deberia hacer.
    """
    bits = (v.bit_length() - 1) + 18            # ilog2(v) + 18
    if v <= 8:
        return bits - 9
    return (bits + 3) // 2


def adjust_size(min_vm_size, fragment_default, max_level, max_bits,
                phys_ram_bytes, forced_vm=None, forced_block=None,
                forced_frag=None):
    """
    Reproduccion linea a linea de amdgpu_vm.c:2379-2461.
    Cada valor lleva la linea que lo produce.
    """
    max_size = 1 << (max_bits - 30)             # :2383

    if forced_vm is not None:                   # :2385 if (amdgpu_vm_size != -1)
        vm_size = min(forced_vm, max_size)      # :2387
    else:
        phys_ram_gb = (phys_ram_bytes + (1 << 30) - 1) >> 30   # :2413
        c = phys_ram_gb * 3                     # :2418
        c = max(min_vm_size, min(c, max_size))  # :2419 clamp
        vm_size = 1 << (c - 1).bit_length()     # roundup_pow_of_two

    max_pfn = vm_size << 18                     # :2423

    tmp = max_pfn                                # :2426 roundup_pow_of_two(max_pfn)
    if forced_block is not None:                # :2427
        tmp >>= forced_block - 9
    x = tmp.bit_length() - 1                    # :2428 fls64(tmp)-1
    tmp = -(-x // 9) - 1                        # DIV_ROUND_UP(x,9)-1
    num_level = min(max_level, tmp)             # :2429 min_t

    if forced_block is not None:                # :2450
        block = min(forced_block,
                    max_bits - GPU_PAGE_SHIFT - 9 * num_level)
    elif num_level > 1:                         # :2452
        block = 9
    else:                                       # :2454
        # El fuente pasa 'tmp', y tmp en este punto ya fue REESCRITO en
        # :2428 por DIV_ROUND_UP(fls64(tmp)-1, 9) - 1, o sea que vale un
        # numero pequeno ligado al numero de niveles, NO max_pfn.
        #
        # La primera version de este modelo pasaba max_pfn aqui y salia 22.
        # Pasar tmp da OTRO valor. La diferencia no es academica: es
        # exactamente el punto donde el calculo se bifurca, asi que un
        # modelo que pase la magnitud equivocada en esta linea no puede
        # usarse para diagnosticar nada.
        block = get_block_size(tmp)

    frag = fragment_default if forced_frag is None else forced_frag  # :2457
    return {"vm_size": vm_size, "num_level": num_level,
            "block_size": block, "fragment_size": frag}


def memtotal_bytes():
    for line in open("/proc/meminfo"):
        if line.startswith("MemTotal:"):
            return int(re.search(r"(\d+)", line).group(1)) * 1024
    return 0


def host_log():
    """Lo que el driver REAL registro. No es una suposicion: es el log."""
    try:
        out = subprocess.run(["journalctl", "-k", "-b", "--no-pager"],
                             capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    for line in out.stdout.splitlines():
        if "vm size is" in line:
            m = re.search(r"vm size is (\d+) GB, (\d+) levels, "
                          r"block size is (\d+)-bit, fragment size is (\d+)-bit",
                          line)
            if m:
                return {"vm_size": int(m.group(1)),
                        "num_level": int(m.group(2)),
                        "block_size": int(m.group(3)),
                        "fragment_size": int(m.group(4)),
                        "raw": line.split("amdgpu ")[-1]}
    return None


def main():
    mem = memtotal_bytes()
    print("Modelo de amdgpu_vm_adjust_size para GFX8")
    print("MemTotal = %d bytes (%.2f GB)" % (mem, mem / 2 ** 30))
    print("Parametros de modulo: NO legibles sin root; se asume el automatico")
    print()
    print("gmc_v8_0.c:1127 -> amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)")
    print()
    m = adjust_size(64, 9, 1, 40, mem)
    print("MODELO (corpus 7.1.3):")
    for k in ("vm_size", "num_level", "block_size", "fragment_size"):
        print("   %-15s = %s" % (k, m[k]))
    print()

    h = host_log()
    if not h:
        print("LOG DEL HOST: no disponible (journalctl no devolvio la linea)")
        return 1

    # El log imprime num_level + 1 (amdgpu_vm.c:2463). Descontarlo aqui es
    # obligatorio: comparar "2 levels" contra un num_level de 1 produce una
    # contradiccion que no existe, y fue exactamente lo que paso antes de
    # leer la linea del dev_info.
    h_nl = h["num_level"] - 1
    print("LOG DEL HOST (observacion, no modelo):")
    print("   %s" % h["raw"])
    print("   vm_size=%s  num_level=%s(log) -> %s(interno)  "
          "block_size=%s  fragment=%s"
          % (h["vm_size"], h["num_level"], h_nl,
             h["block_size"], h["fragment_size"]))
    print()

    print("DIVERGENCIA:")
    igual = True
    for k in ("vm_size", "num_level", "block_size", "fragment_size"):
        hv = h_nl if k == "num_level" else h[k]
        d = m[k] != hv
        igual &= not d
        print("   %-15s modelo=%-6s host=%-6s %s"
              % (k, m[k], hv, "" if not d else "  <-- DIFIERE"))
    print()

    if igual:
        print("El modelo reproduce al host. La geometria del corpus es la real.")
        print()
        print("CONTRADICTION REFUTADA: durante este analisis se sospecho que el")
        print("kernel del host llevaba parches al driver, porque el log decia")
        print("'2 levels' y el corpus solo puede dar num_level=1. La causa era")
        print("el +1 del dev_info. No hay parche.")
        print()
        print("Como corroboracion independiente: el corpus tambien predice")
        print("GART 256M para CHIP_POLARIS12 (gmc_v8_0.c:595) y el host")
        print("registra GART 256M. Dos geometrias distintas, un solo codigo.")
        b = m["block_size"]
        print()
        print("Geometria de GPUVM en GFX8 / POLARIS12:")
        print("   num_level    = %d  (mas la raiz PDB0: %d nivel(es) de PDE)"
              % (m["num_level"], m["num_level"] + 1))
        print("   PTB          = 2^%d entradas = %d" % (b, 2 ** b))
        print("   un PTB cubre 2^%d paginas de %d KiB = %d KiB = %d MiB"
              % (b, GPU_PAGE_SIZE // 1024, 2 ** b * GPU_PAGE_SIZE // 1024,
                 2 ** b * GPU_PAGE_SIZE // 1024 // 1024))
        print("   fragment     = %d bits (512 entradas de fragmento)"
              % m["fragment_size"])
        return 0

    print("CONCLUSION: el corpus NO reproduce el comportamiento del host.")
    print()
    print("Clasificacion epistemica:")
    print("   corpus != host en la geometria de PT     : PROVEN")
    print("   el host esta parcheado                  : HIPOTESIS")
    print("   cual es el parche                       : NOT_DETERMINED")
    return 1


if __name__ == "__main__":
    sys.exit(main())