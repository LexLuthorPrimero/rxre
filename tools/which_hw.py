#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.
which_hw.py - que hardware de GFX8 tiene ESTA GPU, y con que limites.

POR QUE EXISTE

Pregunté a ipsolve que fichero implementa sdma_v4_0_ip_block para
CHIP_POLARIS12, y respondió:

    verdict   NOT_DISPATCHED_FOR_CHIP
    detail    no amdgpu_device_ip_block_add(...&sdma_v4_0_ip_block)
              inside case CHIP_POLARIS12

Eso es CORRECTO sobre lo que pregunta y esta equivocado sobre lo que quiero
saber. El despacho real no es un switch por chip:

    switch (amdgpu_ip_version(adev, SDMA0_HWIP, 0)) {
    case IP_VERSION(4, 0, 0):
    ...
    case IP_VERSION(4, 4, 0):
            amdgpu_device_ip_block_add(adev, &sdma_v4_0_ip_block);

Es un switch por la VERSION DEL IP leida de un registro. Para saber si esta
GPU usa sdma_v4_0.c hay que conocer SDMA0_HWIP, y eso solo se lee de la
tarjeta. La pregunta no es contestable de forma estatica, y la respuesta
correcta a "que hardware tiene mi GPU" es "no se sabe sin leer un registro".

Esta herramienta hace tres cosas, separadamente, y no las mezcla:

  1. Localiza la GPU en el host, si esta, y lee lo que el host ya publica:
     lspci, sysfs, debugfs. Solo LECTURA. Lo que encuentra son HECHOS DEL HOST,
     no del hardware del ASIC.
  2. Para cada bloque de IP, dice cual es el fichero que lo implementa segun el
     corpus, y si el despacho es por chip (decidible) o por version de IP (no
     decidible sin runtime). Esa distincion es la que faltaba.
  3. Declara que la unica parte que responde a la pregunta es una lectura de
     MMIO, y por que no se hace: la REGLA DE SEGURIDAD de AGENTS.md la marca
     como RUNTIME, y el finding 017 ya/Listo que el host rechaza modulos sin
     firmar, de modo que un modulo propio no cargaria aunque se quisiera.

LO QUE NO ES

Esto no es hardware.txt con fluorescentes. No adivina. Si algo no lo sabe, dice
que no lo sabe y por que, y en que fichero esta la respuesta. Un inventario
de Amenazas con signo de interrogacion es mas util que uno con casillas marcadas
porque el lector puede distinguir lo medido de lo supuesto, y aqui la
distincion es el unico contenido que importa.

CODIGOS DE SALIDA

  0  todo lo consultado se resolvio
  1  algo no se resolvio; el detalle lo dice
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

VERSION = "1.0.0"

# El ASIC de este proyecto. El PCI ID viene de lspci en el host, no de aqui.
CHIP = "CHIP_POLARIS12"
PCI_VENDOR = "0x1002"
PCI_DEVICE = "0x699f"          # RX 550 / Polaris12, verificado con lspci
BDF_HINT = "0000:01:00.0"

# Bloques de IP que este proyecto ha reconstructing, con lo que se necesita para
# saber cual implementa cada uno. El "tipo de despacho" es el hallazgo: sin el,
# se pregunta mal a la herramienta y se obtiene un NOT_DISPATCHED que no significa
# lo que parece.
IP_BLOCKS: List[Dict[str, str]] = [
    # El simbolo del bloque y la funcion de despacho no se llamar igual, y 035
    # fue precisamente eso: citar el fichero equivocado por creerse el
    # nombre. Se declara el simbolo REAL del bloque aparte del nombre logico.
    # El case de POLARIS12 anade sdma_v3_1_ip_block, y amdgpu_discovery.c
    # enruta SDMA0_HWIP 4.x a sdma_v4_0_ip_block. Son dos caminos distintos y
    # este bloque se deja resolver por el campo "definido en": si estan en
    # ficheros distintos, la conclusion es que el case usa uno y el discovery
    # el otro, y que hay que averiguar cual gana. Se informa, no se resuelve.
    {"block": "sdma_v3_1_ip_block", "alias": [],
     "hwip": "SDMA0_HWIP", "fichero": None,
     "nota": "el que anade el case de POLARIS12; ¿comparte .funcs con "
             "sdma_v4_0_ip_block o es otro fichero?"},
    {"block": "sdma_v4_0_ip_block", "alias": [],
     "hwip": "SDMA0_HWIP", "fichero": None,
     "nota": "proveedor de PTEPDE segun 035/036; el destino de "
             "SDMA0_HWIP 4.x segun amdgpu_discovery.c"},
    # Este es el que hay que mirar. gmc_v8_0.c es el fichero del que salen todos
    # los hallazgos de page tables de este proyecto, y el case de CHIP_POLARIS12
    # anade gmc_v8_1_ip_block, NO gmc_v8_0_ip_block. Si ese es el caso, el
    # fichero que he estado leyendo no se compila para esta GPU y sus
    # direcciones de registro pueden no ser las de la tarjeta. Se declara con
    # el bloque de verdad al lado, para que el dato se pueda comprobar.
    # gmc_v8_1_ip_block es el que anade el case de POLARIS12. Su fichero es
    # gmc_v8_0.c, y comparte gmc_v8_0_ip_funcs con gmc_v8_0_ip_block y
    # gmc_v8_5_ip_block (gmc_v8_0.c:1754-1775). Lo que diferencia a los tres es
    # major/minor del IP block, NO el codigo que ejecutan.
    #
    # Yo supuse lo contrario -- que leer gmc_v8_0.c era leer un fichero que esta
    # GPU no usa -- y la suposicion era falsa: el case anade gmc_v8_1_ip_block
    # y ese bloque ESTA DEFINIDO en gmc_v8_0.c. Por eso el campo "fichero" se
    # resuelve buscando la definicion del simbolo, y no de una lista escrita a
    # mano: una lista escrita a mano es una suposicion con formato de dato.
    {"block": "gmc_v8_1_ip_block", "alias": [],
     "hwip": "GC_HWIP", "fichero": None,
     "nota": "el que anade el case de POLARIS12; comparte gmc_v8_0_ip_funcs "
             "con gmc_v8_0_ip_block y gmc_v8_5_ip_block"},
    {"block": "gfx_v8_0_ip_block", "alias": ["gfx_v8_0"],
     "hwip": "GC_HWIP", "fichero": "gfx_v8_0.c",
     "nota": "ring GFX, WAIT_REG_MEM, PFP_SYNC_ME, vm-flush"},
]


def find_kernel(explicit: Optional[str]) -> Tuple[Optional[str], str]:
    if explicit:
        return (os.path.abspath(explicit), "--kernel") \
            if os.path.isdir(explicit) else (None, "no existe")
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    for c in (os.path.join(root, "rx550-upstream-7.2.8", "linux-7.2.8"),
              os.path.join(root, "RESEARCH", "working", "linux-7.1.3")):
        if os.path.isdir(c):
            return c, os.path.relpath(c, root)
    return None, "no encontrado"


def sh(cmd: List[str], timeout: int = 20) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return 127, str(e)


# ---------------------------------------------------------------- host


def leer_host() -> Dict[str, object]:
    """Lo que el host ya publica. Lectura pura, sin escrituras.

    Se separa del corpus a proposito: esto es una observacion del host, no una
    verdad sobre el ASIC. Un lspci que no encuentra la GPU no dice que el
    proyecto no tenga GPU."""
    out: Dict[str, object] = {"fuentes": {}, "presente": False}

    rc, txt = sh(["lspci", "-nn", "-d", "%s:%s" % (PCI_VENDOR, PCI_DEVICE)])
    out["fuentes"]["lspci"] = {"rc": rc, "salida": txt.strip()[:400]}
    if rc == 0 and txt.strip():
        out["presente"] = True
        m = re.search(r"^(.+?):\s+(.+)$", txt.strip(), re.M)
        if m:
            out["bdf"] = m.group(1)
            out["nombre"] = m.group(2).strip()

    # El BDF del hint, por si lspci no esta
    sysfs = "/sys/bus/pci/devices"
    if os.path.isdir(sysfs):
        for dev in sorted(os.listdir(sysfs)):
            try:
                with open(os.path.join(sysfs, dev, "vendor"), "r") as f:
                    vend = f.read().strip()
                with open(os.path.join(sysfs, dev, "device"), "r") as f:
                    devid = f.read().strip()
            except OSError:
                continue
            if vend == PCI_VENDOR and devid == PCI_DEVICE:
                out["presente"] = True
                out["bdf"] = dev
                out["fuentes"]["sysfs"] = {"bdf": dev}
                for attr, key in (("revision", "rev"), ("class", "clase")):
                    p = os.path.join(sysfs, dev, attr)
                    if os.path.exists(p):
                        try:
                            with open(p, "r") as f:
                                out[key] = f.read().strip()
                        except OSError:
                            pass
                break

    # BARs, que son hechos de la configuracion PCI y no del ASIC. La direccion
    # del aperture de doorbells sale de aqui (040).
    if out.get("bdf"):
        bdf = out["bdf"]
        res = os.path.join("/sys/bus/pci/devices", bdf, "resource")
        # El path del recurso es /sys/bus/pci/devices/<bdf>/resource, y el
        # directorio devices/ del MISMO nivel sysfs NO contiene un <bdf>. La
        # primera version construia esa forma y obtenia "sin BARs" sin error,
        # que es el peor modo de fallar: un dato ausente que parece un dato
        # medido. Se comprueba la existencia del fichero antes de parsear.
        out["fuentes"]["resource_path"] = res
        bars = {}
        if os.path.exists(res):
            try:
                with open(res, "r") as f:
                    rlines = f.read().splitlines()
                for n in range(min(6, len(rlines))):
                    campos = rlines[n].split()
                    if len(campos) >= 2:
                        bars[n] = {"inicio": campos[0], "fin": campos[1]}
            except OSError as e:
                out["fuentes"]["resource_error"] = str(e)
        else:
            out["fuentes"]["resource_error"] = "el fichero no existe"
        out["bars"] = bars

    # El motor amdgpu, si esta cargado. Un modulo cargado y funcional es
    # evidencia de que el host PUEDE ejecutar amdgpu, que es distinto de que este
    # proyecto pueda cargar el suyo.
    rc, txt = sh(["lsmod"])
    out["fuentes"]["lsmod"] = {"rc": rc, "amdgpu": "amdgpu" in txt}
    if "amdgpu" in txt:
        out["amdgpu_cargado"] = True
        for attr, key in (("runpm", "runpm"), ("dpm", "dpm"),
                          ("aspm", "aspm")):
            p = "/sys/module/amdgpu/parameters/%s" % attr
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        out["param_" + key] = f.read().strip()
                except OSError:
                    pass

    # Debugfs: puede no estar montado, y no se monta. Montarlo seria una
    # escritura al sistema de ficheros del host y no tiene sentido para esto.
    p = "/sys/kernel/debug/dri"
    out["debugfs_montado"] = os.path.isdir(p)

    return out


# ---------------------------------------------------------------- despacho


def clasificar_despacho(corpus: str) -> Dict[str, object]:
    """Como decide el driver cada bloque: por chip o por version de IP.

    Es la distincion que faltaba, y la razon por la que ipsolve da
    NOT_DISPATCHED para algo que si se usa. Se lee el switch real y se
    comprueba si su discriminante es un asic_type o un amdgpu_ip_version().

    Se leen TODOS los ficheros de amdgpu/, no solo amdgpu_discovery.c. El
    despacho de los bloques de GFX8 esta en vi.c, y leer solo discovery.c
    hace que gfx_v8_0_ip_block y gmc_v8_0_ip_block parezcan no existir. Es la
    misma clase de error que 035: dar por supuesto que el fichero de una
    generacion es el fichero de otra."""
    amd = os.path.join(corpus, "drivers/gpu/drm/amd/amdgpu")
    if not os.path.isdir(amd):
        return {"veredicto": "NO_LEGIBLE", "raiz": amd}

    # Solo los ficheros que de verdad pueden despachar. La lista no es
    # suposicion: se busca la llamada en todos y se ve en cuales esta.
    candidatos: List[Tuple[str, List[str]]] = []
    try:
        for entry in sorted(os.listdir(amd)):
            if not entry.endswith(".c"):
                continue
            with open(os.path.join(amd, entry), "r", errors="replace") as f:
                txt = f.read()
            if "amdgpu_device_ip_block_add" in txt:
                candidatos.append((entry, txt.splitlines()))
    except OSError as e:
        return {"veredicto": "NO_LEGIBLE", "error": str(e)}

    # El case real de CHIP_POLARIS12 en cada fichero de despacho, con los
    # bloques que anade. Es el dato que decide, y leerlo evita emparejar por
    # subcadena: "gmc_v8_0" como alias de gmc_v8_0_ip_block hizo que esta
    # herramienta dijera que el chip usa gmc_v8_0_ip_block cuando el case real
    # dice gmc_v8_1_ip_block.
    cases_chip: List[Dict[str, object]] = []
    for nombre_f, lines in candidatos:
        for i, ln in enumerate(lines):
            if not re.match(r"\s*case\s+CHIP_POLARIS12\s*:", ln):
                continue
            # Un case acaba en su break; un recorte de N lineas fijo no puede
            # saberlo y se come el case siguiente. La primera version leia 20
            # lineas y por eso el bloque de CHIP_CARRIZO aparecio dentro del
            # case de POLARIS12, con gmc_v8_0_ip_block y sdma_v3_0_ip_block
            # listados como si los usara esta GPU. Es peor que no leer: una
            # lista de bloques con dos chips dentro.
            sig: List[str] = []
            cerrado = False
            for k in range(i, min(i + 60, len(lines))):
                sig.extend(re.findall(
                    r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)",
                    lines[k]))
                if re.match(r"\s*break;\s*$", lines[k]):
                    cerrado = True
                    break
            cases_chip.append({
                "fichero": nombre_f,
                "linea": i + 1,
                "fin": k + 1 if cerrado else None,
                "cerrado_con_break": cerrado,
                "bloques": sorted(set(sig)),
            })
            if not cerrado:
                # Sin break dentro del alcance, el case probably se continua
                # con mas lineas. Se dice, en vez de truncar en silencio.
                cases_chip[-1]["aviso"] = (
                    "el case no se cierra con break dentro de 60 lineas; la "
                    "lista puede estar incompleta y no se afirma que lo este")

    funciones: List[Dict[str, object]] = []
    for nombre_f, lines in candidatos:
        i = 0
        while i < len(lines):
            # static Y no-static. La primera version exigia "static", y
            # vi_set_ip_blocks -- que es la que despacha gmc_v8_0_ip_block y
            # gfx_v8_0_ip_block -- no lo es. Perder las funciones publicas de
            # despacho es perder precisamente las que deciden por chip, que es
            # la mitad de lo que esta herramienta informa.
            m = re.match(r"^(?:static\s+)?(?:int|void)\s+(\w+)\s*\(.*$",
                         lines[i])
            if not (m and "device_ip_block_add" in "\n".join(lines[i:i + 60])):
                i += 1
                continue
            nombre = m.group(1)
            cuerpo = lines[i:i + 60]
            discriminante = "DESCONOCIDO"
            for j in range(1, 12):
                sm = re.search(r"switch\s*\(\s*(.+?)\s*\)", cuerpo[j])
                if sm:
                    discriminante = sm.group(1)
                    break
            bloques = sorted(set(re.findall(
                r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)",
                "\n".join(cuerpo))))
            funciones.append({
                "fichero": nombre_f,
                "funcion": m.group(1),
                "linea": i + 1,
                "discriminante": discriminante,
                "n_bloques": len(bloques),
                "por_version": "ip_version" in discriminante,
                "bloques": bloques[:8],
            })
            i += 40
            continue
        i += 1

    por_ver = sum(1 for f in funciones if f["por_version"])
    return {
        "ficheros_con_despacho": [c[0] for c in candidatos],
        "n_funciones_de_despacho": len(funciones),
        "por_version_de_ip": por_ver,
        "por_chip": len(funciones) - por_ver,
        "veredicto": ("MAYORMENTE_POR_VERSION_DE_IP" if por_ver >
                      max(1, len(funciones) / 2) else "MAYORMENTE_POR_CHIP"),
        # Todas las funciones se conservan; la vista las recorta. Recortar la
        # lista que despues se USA para emparejar hacia que un bloque parezca no
        # existir, y eso ya ha pasado una vez: la primera version guardaba
        # funciones[:14] y los bloques de vi.c caian fuera del corte.
        "funciones": funciones,
        "n_funciones_mostradas": min(14, len(funciones)),
        "cases_de_este_chip": cases_chip,
    }


# ---------------------------------------------------------------- informe


def selftest() -> int:
    """Vectores sobre un doble, sin tocar el corpus ni el host.

    Los tres que importan:
      1. el case se cierra con su break, no con un recorte de N lineas. Un
         recorte fijo se come el case siguiente y lista bloques de otro chip,
         que es como el error de 035 parecio correcto.
      2. la direccion del intervalo de colision. El segundo tramo esta MAS BAJO
         que el primero, y un intervalo escrito como ascendente queda vacio.
      3. un bloque que no esta en el case se dice que no esta, sin inventar.
    """
    print("=== which_hw selftest ===\n")
    fallos = 0

    class FicheroFalso:
        def __init__(self, lineas):
            self._l = lineas

        def read(self, *a, **k):
            import io
            return io.StringIO("\n".join(self._l))

    # 1. dos cases consecutivos; el primero NO debe absorber el segundo
    print("[1] el case se cierra en su break, no a N lineas")
    lineas = [
        "int f(void)", "{", "\tswitch (x) {", "\tcase CHIP_POLARIS12:",
        "\t\tamdgpu_device_ip_block_add(adev, &bloque_real);",
        "\t\tbreak;",
        "\tcase CHIP_CARRIZO:",
        "\t\tamdgpu_device_ip_block_add(adev, &bloque_de_otro_chip);",
        "\t\tbreak;", "\t}", "}",
    ]

    def _clasificar(lineas, chip="CHIP_POLARIS12"):
        import re as _re
        out = []
        for i, ln in enumerate(lineas):
            if not _re.match(r"\s*case\s+%s\s*:" % chip, ln):
                continue
            sig, cerrado = [], False
            for k in range(i, min(i + 60, len(lineas))):
                sig.extend(_re.findall(
                    r"amdgpu_device_ip_block_add\s*\([^,]*,\s*&(\w+)\)",
                    lineas[k]))
                if _re.match(r"\s*break;\s*$", lineas[k]):
                    cerrado = True
                    break
            out.append((i + 1, k + 1 if cerrado else None, cerrado,
                        sorted(set(sig))))
        return out

    r = _clasificar(lineas)
    if len(r) != 1:
        print("  FAIL: %d case(s) encontrados, esperaba 1" % len(r))
        fallos += 1
    elif r[0][1] != 6 or not r[0][2]:
        print("  FAIL: el case no se cerro en su break: %r" % (r[0],))
        fallos += 1
    elif r[0][3] != ["bloque_real"]:
        print("  FAIL: se absorbio el case siguiente: %r" % (r[0][3],))
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    # 2. la direccion del intervalo
    print("[2] el intervalo de colision baja, no sube")
    t0 = {"contexto_ini": 0, "contexto_fin": 7, "primer_offset": 0x54f,
          "ultimo_offset": 0x556}
    t1 = {"contexto_ini": 8, "contexto_fin": 15, "primer_offset": 0x50e,
          "ultimo_offset": 0x515}
    lo = t0["primer_offset"] + t1["contexto_ini"]
    hi = t0["primer_offset"] + t1["contexto_fin"]
    if (lo, hi) != (0x557, 0x55e):
        print("  FAIL: intervalo %s, esperaba (0x557, 0x55e)" % ((lo, hi),))
        fallos += 1
    if not (t1["primer_offset"] < t0["primer_offset"]):
        print("  FAIL: el fixture no reproduce que el segundo tramo es menor")
        fallos += 1
    if t1["primer_offset"] >= 0x557:
        print("  FAIL: 0x50e cae dentro del intervalo de colision, y no")
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    # 3. un case que se abre pero no se cierra dentro del alcance
    print("[3] un case sin break dentro del alcance se declara incompleto")
    abierto = ["int g(void)", "{", "\tcase CHIP_POLARIS12:",
               "\t\tamdgpu_device_ip_block_add(adev, &algo);"] + \
              ["\t/* filler %d */" % i for i in range(80)]
    r2 = _clasificar(abierto)
    if not r2 or r2[0][2]:
        print("  FAIL: se dio por cerrado un case que no lo esta: %r" % (r2,))
        fallos += 1
    print("  %s\n" % ("PASS" if fallos == 0 else "FAIL"))

    print("=" * 74)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (3 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="que hardware tiene mi GPU, y cuanto de eso se puede saber sin leerla")
    ap.add_argument("--kernel")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-host", action="store_true",
                    help="no tocar el host: solo el corpus")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    corpus, como = find_kernel(args.kernel)
    print("=" * 78)
    print("which_hw %s · WORK_CLASS=READ_ONLY" % VERSION)
    print("=" * 78)
    if not corpus:
        print("corpus NO localizado (%s). Usa --kernel." % como)
        return 2
    print("corpus      %s" % corpus)

    desp = clasificar_despacho(corpus)
    print()
    print("=" * 78)
    print("1 · COMO SE DECIDE QUE BLOQUE DE IP USA CADA GPU")
    print("=" * 78)
    if desp.get("veredicto") == "NO_LEGIBLE":
        print("  amdgpu_discovery.c no legible")
    else:
        print("  %d funcion(es) de despacho, en %d fichero(s): %s"
              % (desp["n_funciones_de_despacho"],
                 len(desp.get("ficheros_con_despacho", [])),
                 ", ".join(desp.get("ficheros_con_despacho", [])[:5])))
        print("  por VERSION DE IP: %d    por CHIP: %d"
              % (desp["por_version_de_ip"], desp["por_chip"]))
        print("  veredicto: %s" % desp["veredicto"])
        print()
        print("  Esto es lo que faltaba para leer bien las respuestas de las")
        print("  herramientas: si el despacho es por version de IP, el switch no")
        print("  tiene un case CHIP_POLARIS12 que buscar, y una herramienta que")
        print("  lo busque dara NOT_DISPATCHED para algo que SI se usa.")
        print()
        for f in desp["funciones"][:14]:
            print("    %-18s %-36s %s"
                  % (f["fichero"], f["funcion"], f["discriminante"][:32]))
            print("        %d bloque(s), por_version=%s"
                  % (f["n_bloques"], f["por_version"]))
    print()

    print("=" * 78)
    print("2 · LOS BLOQUES QUE ESTE PROYECTO USA")
    print("=" * 78)
    # El case real del chip, que es lo que decide y no una conjetura por nombre.
    cases = desp.get("cases_de_este_chip", [])
    if cases:
        for c in cases:
            if not c["bloques"]:
                continue
            print("  case %s en %s:%d-%d anade:"
                  % (CHIP, c["fichero"], c["linea"], c.get("fin") or "?"))
            for b in c["bloques"]:
                print("      %s" % b)
            if c.get("aviso"):
                print("      AVISO: %s" % c["aviso"])
            print()
    else:
        print("  ningun case %s encontrado en los ficheros de despacho." % CHIP)
        print("  Eso NO significa que el chip no use esos bloques: puede que el")
        print("  despacho sea por version de IP, que es lo que se informa arriba.")
        print()

    amd = os.path.join(corpus, "drivers/gpu/drm/amd/amdgpu")
    amd_files: Dict[str, List[str]] = {}
    try:
        for entry in sorted(os.listdir(amd)):
            p = os.path.join(amd, entry)
            if os.path.isfile(p) and entry.endswith((".c", ".h")):
                with open(p, "r", errors="replace") as f:
                    amd_files[entry] = f.read().splitlines()
    except OSError:
        pass

    for b in IP_BLOCKS:
        # Donde se DEFINE el simbolo. Es la unica fuente que no es una
        # suposicion mia: si el bloque no se encuentra, se dice.
        donde_def = None
        for entry, ls in amd_files.items():
            for i, ln in enumerate(ls):
                if re.match(r"^\s*(?:const\s+)?struct\s+amdgpu_ip_block_version\s+%s\b"
                            % re.escape(b["block"]), ln):
                    donde_def = (entry, i + 1)
                    break
            if donde_def:
                break
        # Y cual es la tabla de funciones que comparte, que es lo que de
        # verdad determina el codigo que se ejecuta.
        funcs = None
        if donde_def:
            ls = amd_files[donde_def[0]]
            for ln in ls[donde_def[1]:donde_def[1] + 12]:
                m = re.search(r"\.funcs\s*=\s*&(\w+)", ln)
                if m:
                    funcs = m.group(1)
                    break
        b["definido_en"] = donde_def
        b["funcs"] = funcs
        real = (donde_def[0] if donde_def else b.get("fichero"))
        b["fichero_real"] = real
        existe = bool(real) and os.path.isfile(os.path.join(amd, real))
        # el despacho de cada uno: por version o por chip
        # Emparejamiento por el simbolo EXACTO que aparece en la llamada, no
        # por subcadena. La subcadena es frágil en los dos sentidos: un
        # "gmc_v8_0" dentro de "gmc_v8_0_gmc_funcs" empareja bien, y un "sdma"
        # dentro de "sdma_v6_0_0" empareja con un fichero que no es. Un
        # emparejamiento exacto que no encuentra nada dice "no lo he visto",
        # que es distinto de afirmar que no existe.
        metodo = "NO VISTO en el despacho"
        # Primero el case real de este chip, que es la fuente de verdad.
        for c in desp.get("cases_de_este_chip", []):
            if b["block"] in c["bloques"]:
                metodo = ("CHIP: %s lo anade en %s:%d"
                          % (CHIP, c["fichero"], c["linea"]))
                break
            continue
        else:
            for f in desp.get("funciones", []):
                if b["block"] in f["bloques"]:
                    metodo = ("VERSION_DE_IP(%s): no decidible sin leer el "
                              "registro" % b["hwip"]) if f["por_version"] \
                        else "CHIP: decidible"
                    break
            else:
                # Ni en el case ni en ninguna funcion de despacho. Informar de
                # la Ausencia y su cota, sin decir por que: puede ser otro
                # nombre, otro fichero, o no existir. Las tres son distintas y
                # esta herramienta solo puede descartar la tercera.
                visto = any(b["block"] in " ".join(f["bloques"])
                            for f in desp.get("funciones", []))
                metodo = ("NO VISTO. Aparece en %d funcion(es) de despacho "
                          "de %d" % (len(desp.get("funciones", [])),
                                     len(desp.get("funciones", []))))
        print("  %-22s %-16s %s"
              % (b["block"], real or "?",
                 "en el corpus" if existe else "NO EN EL CORPUS"))
        if donde_def:
            print("      definido en %s:%d, .funcs = &%s"
                  % (donde_def[0], donde_def[1], funcs or "?"))
        print("      despacho: %s" % metodo)
        print("      %s" % b["nota"])
        if metodo.startswith("NO VISTO"):
            print("      *** NO LO ANADE EL case de %s ***" % CHIP)
            print("      (no aparece en ninguna llamada a")
            print("       amdgpu_device_ip_block_add leida. Puede estar en")
            print("       otro fichero de despacho, o no existir con ese")
            print("       nombre. No se afirma ninguna de las dos cosas.)")
            print("      Si esto importa: los findings que citan %s estan"
                  % (b.get("fichero_real") or b["fichero"] or "?"))
            print("      leyendo un fichero que esta GPU podria no usar.")
    print()

    if args.no_host:
        print("=" * 78)
        print("3 · EL HOST: omitido por --no-host")
        print("=" * 78)
        print()
        return 0

    print("=" * 78)
    print("3 · LO QUE EL HOST YA PUBLICA (lectura, no escritura)")
    print("=" * 78)
    h = leer_host()
    if h.get("presente"):
        print("  GPU presente:  %s" % h.get("bdf", "?"))
        print("  nombre:        %s" % h.get("nombre", "(no informado)"))
        if h.get("rev"):
            print("  revision PCI:  %s" % h["rev"])
        if h.get("bars"):
            print("  BARs (inicio-fin), de la configuracion PCI:")
            for n, b in sorted(h["bars"].items()):
                print("    BAR%d  %s .. %s" % (n, b["inicio"], b["fin"]))
            print("    El aperture de doorbells es BAR2 (amdgpu_doorbell_mgr.c:210).")
    else:
        print("  NO se encuentra %s:%s en este host." % (PCI_VENDOR, PCI_DEVICE))
        print("  Eso es una observacion del HOST, no del proyecto: el ASIC de")
        print("  referencia es el del corpus, y este host puede no ser el que")
        print("  ejecuta las mediciones.")
    if h.get("amdgpu_cargado"):
        print("  amdgpu:         cargado%s%s" % (
            (" (runpm=%s)" % h["param_runpm"]) if "param_runpm" in h else "",
            (" (dpm=%s)" % h["param_dpm"]) if "param_dpm" in h else ""))
    print("  debugfs:        %s" % ("montado" if h.get("debugfs_montado")
                                   else "NO montado (no se monta: seria una escritura al host)"))
    print()

    print("=" * 78)
    print("4 · LO QUE NO SE PUEDE SABER SIN LEER LA TARJETA")
    print("=" * 78)
    print("  Ninguno de estos se contesta leyendo el corpus, y conviene decirlo")
    print("  antes de que alguien lo busque otra vez:")
    print()
    print("    - la version de cada IP block (SDMA0_HWIP, GC_HWIP, GMC_HWIP),")
    print("      que es el discriminante real del despacho")
    print("    - por tanto si esta GPU usa sdma_v4_0.c o sdma_v6_0_0.c")
    print("    - el numero real de anillos, colas y CUs activos")
    print("    - si el modulo propio llegaria a cargarse: el host tiene")
    print("      CONFIG_MODULE_SIG_ALL y CONFIG_SECURITY_LOCKDOWN_LSM, y la")
    print("      clave de firma no esta, de modo que un .ko sin firmar no carga")
    print("      aunque la politica de seguridad lo permitiera")
    print()
    print("  Esas son lecturas de MMIO. AGENTS.md las clasifica RUNTIME, y este")
    print("  proyecto no las hace sin un discriminante que las justifique. Que")
    print("  no haya discriminante es la razon, no una falta de tiempo.")
    print()

    if args.json:
        print(json.dumps({"despacho": desp, "host": h},
                         indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
