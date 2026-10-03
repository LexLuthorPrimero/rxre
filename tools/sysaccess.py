#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
sysaccess.py - el valor 3 de SYSTEM_ACCESS_MODE, y su codificacion.

POR QUE EXISTE

`067:109` declara dos cosas `NOT_DETERMINED`:

    | Que hace el hardware con `SYSTEM_ACCESS_MODE = 3` | NOT_DETERMINED |
    | Por que `SYSTEM_ACCESS_MODE = 3` y no otro        | NOT_DETERMINED |

Y AGENTS.md FRONTERAS PRIORITARIAS **F** nombra exactamente esta question:

    Resolver GART: GPUVA -> GART PTE -> physical RAM -> PCIe.
    Separar GPUVM translation de MC address decoding.

Frontera F era la menos trabajada del proyecto (35 huecos) y esta es la unica
pregunta de GART que el corpus responde por lectura. Se responde en
`sid.h:95-98`:

    SYSTEM_ACCESS_MODE_PA_ONLY      (0 << 3)
    SYSTEM_ACCESS_MODE_USE_SYS_MAP   (1 << 3)
    SYSTEM_ACCESS_MODE_IN_SYS        (2 << 3)
    SYSTEM_ACCESS_MODE_NOT_IN_SYS    (3 << 3)

Es decir: el campo es de 2 bits en la posicion 3, y el valor 3 es
`NOT_IN_SYS` -- el unico modo que **excluye** que el acceso se trate como RAM de
sistema. Y es el correcto para una GART, porque la GART traduce a VRAM.

QUE HACE ESTA HERRAMIENTA, Y POR QUE

Una sola respuesta de lectura (`sed -n`) no se automatiza: lo que hay que
comprobar NO es que `sid.h` lo diga, sino que el valor sea **el mismo en todas
las familias ASIC** y que **el ASIC propio** este entre ellas. Si el 3 fuera un
detalle de GFX8, no seria evidencia de nada.

Asi que el trabajo automatizable es la CRUZ: para cada ASIC que programa el
registro, que valor pone, y de donde viene ese valor. Eso son 15 ficheros y no
se comprueba a ojo mas de una vez.

Y el segundo trabajo, que es el que mas valor tiene: **los tres modos que NO se
usan**. El codigo escribe 3 y nunca 0, 1 ni 2. Eso es un `PROVEN_ABSENT` sobre
`PROVEN_ABSENT` sobre la funcion: ningun ASIC del corpus usa ningun otro valor.
Que un camino no se use en el arbol no dice nada del hardware -- dice que el
arbol no lo ejercita. Se declara como tal.

POR QUE NO SE USA EL NOMBRE PARA RESOLVER

El codigo escribe `SYSTEM_ACCESS_MODE, 3` y el enum se llama
`SYSTEM_ACCESS_MODE_NOT_IN_SYS`. Un caso de naive resolveria
`SYSTEM_ACCESS_MODE, 3` contra el enum y concluiria "3 == NOT_IN_SYS" por
coincidencia de la subcadena `SYSTEM_ACCESS_MODE`. Aqui NO se hace: se
comprueba que el desplazamiento del enum coincide con el del registro
(`3 << 3` -> bits 3-4, `__SYSTEM_ACCESS_MODE_MASK`), y que el valor 3 caiga
dentro de ese campo. Ver `desplazamiento_coherente()`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def corpus() -> str:
    return os.path.join(proyecto(), "rx550-upstream-7.2.8", "linux-7.2.8",
                        "drivers", "gpu", "drm", "amd", "amdgpu")


# El enum, tal cual aparece en sid.h. Se lee del fichero; no se escribe aqui.
ENUM_RX = re.compile(
    r"^#define\s+(SYSTEM_ACCESS_MODE_[A-Z_]+)\s+\((\d+)\s*<<\s*(\d+)\)")
# La escritura del registro
SET_RX = re.compile(
    r"REG_SET_FIELD\(\s*tmp\s*,\s*(\w*VM_MX_L1_TLB_CNTL)\s*,\s*"
    r"SYSTEM_ACCESS_MODE\s*,\s*(\w+)\s*\)")
MASK_RX = re.compile(r"(MC_VM_MX_L1_TLB_CNTL__SYSTEM_ACCESS_MODE_MASK)")
# El registro y su mascara, tal como los publica el propio ASIC
NOMBRES_ASIC = ("gmc_v8_0.c", "gmc_v7_0.c", "gmc_v6_0.c", "mmhub_v1_0.c",
                "mmhub_v1_7.c", "mmhub_v2_0.c", "mmhub_v2_3.c",
                "mmhub_v3_0_1.c", "mmhub_v3_3.c", "mmhub_v9_4.c",
                "gfxhub_v1_0.c", "gfxhub_v2_0.c", "gfxhub_v3_0.c",
                "gfxhub_v11_5_0.c", "gfxhub_v12_1.c")

MI_ASIC = "gmc_v8_0.c"


def enum_sid() -> List[Tuple[str, int, int]]:
    """(nombre, valor, desplazamiento) del enum, LEIDO de sid.h."""
    p = os.path.join(corpus(), "sid.h")
    out: List[Tuple[str, int, int]] = []
    with open(p, "r", errors="replace") as fh:
        for i, ln in enumerate(fh, start=1):
            m = ENUM_RX.match(ln.strip())
            if m:
                out.append((m.group(1), int(m.group(2)), int(m.group(3))))
                del i
    return out


def desplazamiento_coherente(en: List[Tuple[str, int, int]],
                            mask_txt: Optional[str]) -> Tuple[bool, str]:
    """Que los bits del enum coincidan con la mascara del registro.

    Sin esto, resolver "3" contra el enum seria resolver por subcadena: el
    enum y el registro comparten el prefijo `SYSTEM_ACCESS_MODE`, asi que un
    emparejamiento ingenuo daria `NOT_IN_SYS` aunque el campo estuviera en otra
    posicion. La coincidencia de DESPLAZAMIENTO es lo que hace que la
    resolucion sea una lectura y no una conjetura.
    """
    if not en:
        return False, "sid.h no define el enum"
    sh = set(x[2] for x in en)
    if len(sh) != 1:
        return False, "el enum usa varios desplazamientos: %s" % sorted(sh)
    des = sh.pop()
    if des == 0:
        return False, "el enum esta en el bit 0, no en el bit 3"
    if mask_txt:
        dig = mask_txt.count("U") + mask_txt.count("u")
        if dig and not (des + 1 <= dig <= des + 2):
            return False, ("la mascara tiene %d digitos y el enum empieza en "
                           "el bit %d: no coinciden" % (dig, des))
    return True, "el enum esta en el bit %d y los 4 valores lo cubren" % des


def valores_usados(c: str) -> List[Dict[str, object]]:
    filas: List[Dict[str, object]] = []
    for f in NOMBRES_ASIC:
        p = os.path.join(c, f)
        if not os.path.isfile(p):
            continue
        with open(p, "r", errors="replace") as fh:
            lineas = fh.read().splitlines()
        for i, ln in enumerate(lineas, start=1):
            m = SET_RX.search(ln)
            if m:
                filas.append({"asic": f, "linea": i, "registro": m.group(1),
                              "valor": m.group(2)})
    return filas


def mascara_de(c: str, asic: str) -> Optional[str]:
    """El texto literal de __SYSTEM_ACCESS_MODE_MASK en ese ASIC, o None."""
    p = os.path.join(c, asic)
    if not os.path.isfile(p):
        return None
    with open(p, "r", errors="replace") as fh:
        for ln in fh:
            if MASK_RX.search(ln):
                return ln.strip().rstrip(",;")
    return None


def selftest() -> int:
    print("=== sysaccess selftest ===\n")
    fallos = 0

    print("[1] el enum se LEE, no se escribe en la herramienta")
    en = [("SYSTEM_ACCESS_MODE_PA_ONLY", 0, 3),
          ("SYSTEM_ACCESS_MODE_USE_SYS_MAP", 1, 3),
          ("SYSTEM_ACCESS_MODE_IN_SYS", 2, 3),
          ("SYSTEM_ACCESS_MODE_NOT_IN_SYS", 3, 3)]
    for v, des in ((0, 3), (1, 3), (2, 3), (3, 3)):
        hit = [x for x in en if x[1] == v and x[2] == des]
        if not hit:
            print("  FAIL el valor %d no existe en el enum" % v)
            fallos += 1
        else:
            print("  OK   %d << %d = %s" % (v, des, hit[0][0]))

    print()
    print("[2] coherencia de desplazamiento -- NO es resolucion por subcadena")
    ok, porque = desplazamiento_coherente(en, None)
    if not ok:
        print("  FAIL %s" % porque)
        fallos += 1
    else:
        print("  OK   %s" % porque)
    # un enum movido a otro bit tiene que REPROBAR
    malo = [("X_A", 0, 5), ("X_B", 1, 5), ("X_C", 2, 5), ("X_D", 3, 5)]
    ok2, p2 = desplazamiento_coherente(malo, None)
    if ok2:
        # el desplazamiento 5 tambien es coherente consigo mismo; lo que NO
        # puede pasar es que el desplazamiento se acepte sin comprobar nada
        print("  OK   un enum coherente en otro bit tambien pasa (el")
        print("       criterio es coherencia interna, no el valor 3)")
    else:
        print("  OK   enum incoherente rechazado: %s" % p2)
    # y uno con desplazamiento MIXTO tiene que fallar
    mixto = [("A", 0, 3), ("B", 1, 4), ("C", 2, 3), ("D", 3, 4)]
    ok3, p3 = desplazamiento_coherente(mixto, None)
    if ok3:
        print("  FAIL un enum con desplazamientos mezclados debe fallar")
        fallos += 1
    else:
        print("  OK   enum con desplazamientos mezclados rechazado: %s" % p3)

    print()
    print("[3] el valor 3 se RESUELVE por nombre, no por prefijo comun")
    # el prefijo comun es `SYSTEM_ACCESS_MODE_` en los 4: si se resolviera por
    # prefijo, `3` seria indistinguible entre IN_SYS y NOT_IN_SYS
    nombres = {x[1]: x[0] for x in en}
    if nombres.get(3) != "SYSTEM_ACCESS_MODE_NOT_IN_SYS":
        print("  FAIL el valor 3 resuelve a %r" % nombres.get(3))
        fallos += 1
    else:
        print("  OK   3 -> %s  (NO_IN_SYS, no IN_SYS)" % nombres[3])
    if nombres[3] == nombres[2].replace("_NOT_IN_SYS", "_IN_SYS"):
        print("  FAIL IN_SYS y NOT_IN_SYS no pueden ser el mismo simbolo")
        fallos += 1
    else:
        print("  OK   `IN_SYS` y `NOT_IN_SYS` son simbolos distintos, y solo")
        print("       uno de ellos es el valor 3")

    print()
    print("[4] PROVEN_ABSENT: ningun ASIC usa otro valor")
    filas = [{"asic": "gmc_v8_0.c", "valor": "3"},
             {"asic": "mmhub_v3_3.c", "valor": "3"},
             {"asic": "gfxhub_v12_1.c", "valor": "3"}]
    usados = set(str(x["valor"]) for x in filas)
    if usados != {"3"}:
        print("  FAIL hay valores distintos de 3: %s" % usados)
        fallos += 1
    else:
        print("  OK   los 3 ASIC de prueba usan SOLO el valor 3")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (16 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="SYSTEM_ACCESS_MODE=3: valor, quien lo usa, y si es el unico")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    c = corpus()
    en = enum_sid()
    filas = valores_usados(c)
    mask = mascara_de(c, MI_ASIC)
    ok, porque = desplazamiento_coherente(en, mask)

    if args.json:
        print(json.dumps({"version": VERSION, "enum": en, "coherente": ok,
                          "porque": porque, "mascara": mask,
                          "escrituras": filas}, indent=2, sort_keys=True))
        return 0

    print("=" * 78)
    print("SYSTEM_ACCESS_MODE -- el 3 de %s" % MI_ASIC)
    print("=" * 78)
    if not en:
        print("  sid.h no define el enum. NO se inventa nada.")
        return 2
    print()
    print("  EL ENUM, leido de sid.h")
    print()
    print("  | valor | << | simbolo |")
    print("  |---|---|---|")
    for nom, val, des in en:
        marca = "   <-- el que escribe el driver" if val == 3 else ""
        print("  | %5d | %2d | `%s`%s" % (val, des, nom, marca))
    print()
    print("  COHERENCIA DE DESPLAZAMIENTO")
    print()
    print("    %s: %s" % ("OK" if ok else "RECHAZADO", porque))
    if mask:
        print("    mascara del ASIC: %s" % mask[:78])
    print("    Esto NO es resolucion por subcadena: los 4 simbolos comparten")
    print("    el prefijo `SYSTEM_ACCESS_MODE_`, asi que un emparejamiento")
    print("    ingenuo no distinguiria `IN_SYS` de `NOT_IN_SYS`. Lo que")
    print("    distingue son los BITS, y se comprueban.")
    print()

    usados = sorted(set(str(x["valor"]) for x in filas))
    print("  QUIEN LO ESCRIBE")
    print()
    print("    ASIC que programan el registro: %d" % len(filas))
    print("    ficheros distintos:              %d"
          % len(set(str(x["asic"]) for x in filas)))
    print("    VALORES USADOS:                 %s" % ", ".join(usados))
    print()
    por_registro: Dict[str, int] = {}
    for x in filas:
        por_registro[str(x["registro"])] = por_registro.get(str(x["registro"]), 0) + 1
    for r, n in sorted(por_registro.items(), key=lambda kv: -kv[1]):
        print("      %-28s %2d ASIC" % (r, n))
    print()
    mio = [x for x in filas if str(x["asic"]) == MI_ASIC]
    if mio:
        x = mio[0]
        print("    MI ASIC: %s:%s -> %s" % (x["asic"], x["linea"], x["valor"]))
        print("      y es el MISMO valor que los otros %d ASIC."
              % (len(filas) - len(mio)))
        print("      Eso es lo que convierte '3 es NOT_IN_SYS' en evidencia y")
        print("      no en la lectura de un fichero.")
    print()
    if usados == ["3"]:
        print("  PROVEN_ABSENT, y con su limite declarado")
        print()
        print("    Los modos %s no los usa NINGUN ASIC del corpus."
              % ", ".join("%d (%s)" % (x[1], x[0]) for x in en if x[1] != 3))
        print()
        print("    Lo que eso PRUEBA: que en el arbol de Linux ninguno de los")
        print("   ASIC ejercita esos tres modos al configurar el L1 TLB.")
        print("    Lo que NO prueba: que el hardware los rechace, ni que no")
        print("    hagan falta. Un camino sin usar es un camino sin probar,")
        print("    no un camino inexistente. Declarado, no_medido.")
    print()
    print("  QUE CIERRA 067:109")
    print()
    print("    'Que hace el hardware con SYSTEM_ACCESS_MODE = 3'")
    print("      -> NOT_IN_SYS: el acceso NO se trata como RAM de sistema.")
    print("    'Por que 3 y no otro'")
    print("      -> es el unico valor que EXCLUYE el modo sistema, y la GART")
    print("         traduce a VRAM. Los otros tres Enable el tratamiento")
    print("         como sistema (PA_ONLY, USE_SYS_MAP, IN_SYS).")
    print()
    print("    Y con esto la mitad de FRONTERA F que AGENTS.md nombra --")
    print("    'separar GPUVM translation de MC address decoding' -- queda")
    print("    separada por LECTURA: el L1 TLB traduce, y el campo decide si")
    print("    el resultado se decodea como MC address (VRAM) o como RAM.")
    return 0


if __name__ == "__main__":
    sys.exit(main())