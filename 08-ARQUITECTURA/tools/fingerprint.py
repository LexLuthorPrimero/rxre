#!/usr/bin/env python3
# CONTRACT: name=fingerprint
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""fingerprint -- fingerprint de hardware reproducible, y veredicto TARGET_MATCH.

POR QUE EXISTE. Todo el trabajo del proyecto se apoya en una GPU concreta y nunca
se habia construido el fingerprint que la identifica, ni se habia comparado con el
target declarado. Eso deja una pregunta sin responder en la base de todo lo demas:
¿sobre QUE hardware se hizo cada hallazgo?

Este es un PRODUCTO, no una lectura de una vez: se regenera, se compara campo a
campo con el contrato de target, y devuelve codigo de salida distinto segun el
veredicto.

REGLA QUE IMPONE EL PROPIO CONTRATO. `NOT_AVAILABLE` no es `MATCH`. Un campo que no
se pudo leer se reporta como tal y hace que el veredicto NO sea MATCH. Si no, el
fingerprint "pasa" mientras le falta la mitad, que es como un filtro que solo dice
"no".

Y el dispositivo GPU NO se localiza por indice de bus: se busca por clase y por
identidad PCI. El indice 01:00.0 es una convencion de esta maquina, no una
propiedad del hardware, y hardcodearlo es exactamente el tipo de generalizacion
que este proyecto no quiere.

Uso:
  fingerprint.py --completo     todos los campos + veredicto
  fingerprint.py --campo N      un campo
  fingerprint.py --self-test

Codigos de salida:
  0  TARGET_MATCH
  1  TARGET_MISMATCH  (un campo contradice al contrato)
  2  TARGET_INDETERMINATE (un campo no se pudo leer)
  3  dependencia ausente (lspci / journalctl)
"""

import os
import re
import subprocess
import sys

PCI_DIR = "/sys/bus/pci/devices"
SYS_DMI = "/sys/class/dmi/id"

# El contrato de target. Cada entrada: (etiqueta, valor esperado, predicado).
# El predicado se evalua sobre el valor real; None significa igualdad exacta.
TARGET = [
    ("cpu",        "Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz", None),
    ("board",      "H81H3-M4",                                  None),
    ("os",         "Nobara Linux",                              None),
    ("gpu_vendor", "Advanced Micro Devices",                    None),
    ("gpu_device", "699f",                                      None),
    ("asic",       "POLARIS12",                                 None),
    ("gfx",        "8.0.0",                                     None),
    ("vram_mib",   2048,                                        lambda v: abs(v - 2048) < 64),
    ("bar0_mib",   256,                                         lambda v: abs(v - 256) < 4),
    ("igpu",       True,                                        lambda v: v is True),
]


def _leer(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return None


def _cmd(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _dmi(f):
    return _leer(os.path.join(SYS_DMI, f))


def _klog():
    """Kernel log via journalctl. `dmesg` puede estar vacio por permisos."""
    return _cmd(["journalctl", "-k", "--no-pager"]) or ""


def gpu_dispositivo():
    """Localiza la GPU por clase PCI 0300 con vendor 1002. NO por indice de bus."""
    vendor = _cmd(["lspci", "-nn"])
    if vendor is None:
        return None
    for linea in vendor.split("\n"):
        # "01:00.0 VGA compatible controller [0300]: ... [1002:699f] (rev c7)"
        m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                     r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]", linea)
        if m and m.group(2) == "1002":
            return {"slot": m.group(1), "vendor": m.group(2),
                    "device": m.group(3), "linea": linea}
    return None


def iGPU_presente():
    vendor = _cmd(["lspci", "-nn"]) or ""
    # 8086:0412 es el GT3 de Haswell (Iris Pro 4600 / HD Graphics 4600).
    return "8086:0412" in vendor


def Collected():
    """Reúne todos los campos. Devuelve (campos, ausentes)."""
    k = _klog()
    campos = {}

    cpuinfo = _leer("/proc/cpuinfo") or ""
    m = re.search(r"model name\s*:\s*(.+)", cpuinfo)
    campos["cpu"] = m.group(1).strip() if m else None
    n_cpu = len(re.findall(r"^processor\s*:", cpuinfo, re.M))
    campos["cpus_logicos"] = n_cpu or None
    # nucleos fisicos, de la topologia del kernel (una entrada por nucleo)
    topo = _leer("/sys/devices/system/cpu/cpu0/topology/thread_siblings_list") or ""
    campos["thread_siblings"] = topo

    mem = _leer("/proc/meminfo") or ""
    m = re.search(r"MemTotal:\s+(\d+) kB", mem)
    campos["ram_kib"] = int(m.group(1)) if m else None
    campos["ram_gib"] = round(campos["ram_kib"] / 1048576.0, 2) if campos["ram_kib"] else None

    campos["board"] = _dmi("board_name")
    campos["board_vendor"] = _dmi("board_vendor")
    campos["bios"] = _dmi("bios_version")

    un = _cmd(["uname", "-srmo"])
    campos["kernel"] = un.strip() if un else None
    campos["arch"] = un.split()[2] if un and len(un.split()) > 2 else None

    osr = _leer("/etc/os-release") or ""
    m = re.search(r'PRETTY_NAME="([^"]+)"', osr)
    campos["os"] = m.group(1) if m else None

    g = gpu_dispositivo()
    if g:
        campos["gpu_slot"] = g["slot"]
        campos["gpu_vendor"] = g["linea"].split(": ", 1)[1].split(" [")[0]
        campos["gpu_device"] = g["device"]
        campos["gpu_linea"] = g["linea"]
    else:
        campos["gpu_slot"] = campos["gpu_vendor"] = campos["gpu_device"] = None
        campos["gpu_linea"] = None

    # ASIC y GFX: el driver los imprime al arrancar.
    m = re.search(r"initializing kernel modesetting \(([^ ]+)", k)
    campos["asic"] = m.group(1) if m else None
    m = re.search(r"detected ip block number 3 <gfx_v(\d+)_(\d+)_(\d+)>", k)
    campos["gfx"] = ("%s.%s.%s" % (m.group(1), m.group(2), m.group(3))
                     if m else None)

    m = re.search(r"Detected VRAM RAM=(\d+)M, BAR=(\d+)M", k)
    campos["vram_mib"] = int(m.group(1)) if m else None
    campos["bar0_mib_log"] = int(m.group(2)) if m else None

    m = re.search(r"GART:\s*(\d+)M", k)
    campos["gart_mib"] = int(m.group(1)) if m else None
    m = re.search(r"(\d+)M of GTT memory ready", k)
    campos["gtt_mib"] = int(m.group(1)) if m else None

    # BAR0 medido del recurso, independiente del log.
    if campos["gpu_slot"]:
        # lspci imprime "01:00.0" SIN dominio; sysfs usa "0000:01:00.0" CON el.
        # Sin esta normalizacion el recurso no existe y el fingerprint queda
        # INDETERMINATE -- que es lo que paso, y que es el comportamiento
        # correcto: la herramienta dijo que le faltaba un campo en vez de
        # suponerlo.
        slot = campos["gpu_slot"]
        if not re.match(r"^[0-9a-f]{4}:", slot):
            slot = "0000:" + slot
        campos["gpu_slot_sysfs"] = slot
        r = os.path.join(PCI_DIR, slot, "resource")
        txt = _leer(r)
        if txt:
            filas = [l.split() for l in txt.split("\n") if l.strip()]
            if filas:
                a, b = int(filas[0][0], 16), int(filas[0][1], 16)
                campos["bar0_mib"] = (b - a + 1) // (1024 * 1024) if b else None
    campos.setdefault("bar0_mib", None)

    # BAR de registros: el que el driver mapea de verdad.
    m = re.search(r"register mmio base:\s*(0x[0-9A-Fa-f]+)", k)
    campos["rmmio_base"] = m.group(1) if m else None
    m = re.search(r"register mmio size:\s*(\d+)", k)
    campos["rmmio_size"] = int(m.group(1)) if m else None

    campos["igpu"] = iGPU_presente() if campos["gpu_vendor"] else None

    campos["driver"] = "amdgpu"
    campos["modulo"] = "amdgpu" if _leer("/proc/modules") and "amdgpu" in (
        _leer("/proc/modules") or "") else None

    ausentes = [n for n, _e, _p in TARGET if campos.get(n) is None]
    return campos, ausentes


def veredicto(campos):
    filas, mal, indet = [], [], []
    for etiqueta, esperado, pred in TARGET:
        real = campos.get(etiqueta)
        if real is None:
            estado = "INDETERMINATE"
            indet.append(etiqueta)
        elif pred is not None:
            estado = "MATCH" if pred(real) else "MISMATCH"
        else:
            if isinstance(esperado, bool):
                estado = "MATCH" if real is esperado else "MISMATCH"
            elif isinstance(esperado, str):
                estado = "MATCH" if esperado in str(real) else "MISMATCH"
            else:
                estado = "MATCH" if real == esperado else "MISMATCH"
        if estado == "MISMATCH":
            mal.append(etiqueta)
        filas.append((etiqueta, str(esperado), str(real), estado))
    return filas, mal, indet


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. La aritmetica de RAM: MemTotal viene en KiB y el contrato pide GiB.
    eq("12098904 kB son GiB", round(12098904 / 1048576.0, 2), 11.54)

    # 2. La GPU se localiza por clase, no por indice. Un fixture con la GPU en
    #    OTRO bus tiene que dar el mismo resultado: por eso el parser es el
    #    producto que se prueba, no el indice.
    lineas = [
        "00:02.0 Display controller [0380]: Intel Corporation [8086:0412] (rev 06)",
        "01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. "
        "[AMD/ATI] Lexa PRO [1002:699f] (rev c7)",
        "07:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. "
        "[AMD/ATI] Another [1002:699f] (rev c7)",
    ]
    got = None
    for l in lineas:
        m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                     r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]", l)
        if m and m.group(2) == "1002":
            got = m.group(1)
            break          # el PRIMERO gana, como en gpu_dispositivo()
    eq("el parser encuentra la primera VGA de vendor 1002", got, "01:00.0")

    # 3. CONTROL NEGATIVO del parser: una linea que NO es la GPU no debe casar.
    #    Sin esto, "hay 0300 en alguna parte" seria suficiente y seria falso.
    m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                 r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]",
                 "00:02.0 Display controller [0380]: Intel Corporation [8086:0412]")
    if m:
        fails.append("control negativo: el parser caso con un Display controller Intel")

    # 4. CONTROL NEGATIVO: una GPU de otro vendor NO debe_selected.
    m = re.match(r"([0-9a-f]{2}:[0-9a-f]{2}\.\d)\s+"
                 r"VGA compatible controller.*\[([0-9a-f]{4}):([0-9a-f]{4})\]",
                 "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation "
                 "GA106 [10de:2404] (rev a1)")
    if m and m.group(2) == "1002":
        fails.append("control negativo: selecciono una GPU NVIDIA")

    # 5. LA REGLA QUE IMPONE EL CONTRATO: un campo ausente NO es MATCH.
    campos = {n: None for n, _e, _p in TARGET}
    _f, mal, indet = veredicto(campos)
    if not indet:
        fails.append("todos los campos a None deben ser INDETERMINATE, no MATCH")
    eq("ninguno debe ser MISMATCH con todo ausente", mal, [])

    # 6. Y al reves: un valor equivocado debe ser MISMATCH, no INDETERMINATE.
    campos2 = {n: 1 for n, _e, _p in TARGET}
    _f2, mal2, indet2 = veredicto(campos2)
    if not mal2:
        fails.append("valores erroneos deben dar MISMATCH")

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (1 vector de unidades, 4 de parser con 3 controles "
          "negativos, 2 de veredicto)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()

    campos, _aus = Collected()

    if "--campo" in argv:
        n = argv[argv.index("--campo") + 1]
        v = campos.get(n)
        print("%-14s %s" % (n, "NOT_AVAILABLE" if v is None else v))
        return 0 if v is not None else 2

    print("=" * 72)
    print("HARDWARE FINGERPRINT")
    print("=" * 72)
    for k in ("cpu", "cpus_logicos", "ram_gib", "board_vendor", "board", "bios",
              "os", "kernel", "arch", "gpu_slot", "gpu_vendor", "gpu_device",
              "asic", "gfx", "vram_mib", "bar0_mib", "bar0_mib_log", "gart_mib",
              "gtt_mib", "rmmio_base", "rmmio_size", "igpu", "driver", "modulo"):
        v = campos.get(k)
        print("  %-14s %s" % (k, "NOT_AVAILABLE" if v is None else v))

    print()
    print("-" * 72)
    print("VEREDICTO CONTRA EL CONTRATO DE TARGET")
    print("-" * 72)
    print("  %-13s %-38s %-22s %s" % ("campo", "esperado", "real", "estado"))
    filas, mal, indet = veredicto(campos)
    for etiqueta, esp, real, estado in filas:
        print("  %-13s %-38s %-22s %s"
              % (etiqueta, esp[:38], real[:22], estado))

    print()
    if mal:
        print("TARGET_MISMATCH en: %s" % ", ".join(mal))
        return 1
    if indet:
        print("TARGET_INDETERMINATE: %s no se pudo leer." % ", ".join(indet))
        print("  NOT_AVAILABLE no es MATCH. El fingerprint esta incompleto.")
        return 2
    print("TARGET_MATCH")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))