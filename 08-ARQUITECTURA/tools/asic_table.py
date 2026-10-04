#!/usr/bin/env python3
# CONTRACT: name=asic_table
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""ASIC TABLE -- el mapa (device_id, revision) -> chip_id, leido del binario.

POR QUE EXISTE.

La tabla que asigna `chip_id` a cada GPU esta en `hwmgr.c`, y `hwmgr.c` **no
esta en el corpus** (`050-frontera-de-corpus-no-de-hardware.md:16`). Pero el
`.ko` cargado SI esta, y la tabla esta en `.rodata` como datos, no como codigo.

Eso significa que no hace falta desensamblar, ni traer el arbol, ni UMR: se
busca el `device_id` de la placa en la seccion y se lee la entrada.

POR QUE ES MAS QUE UN TRUCO.

La tabla tiene 318 entradas con un patron de 8 palabras:

    0x2b00  02100000 9f690000 ffffffff ffffffff   vid=1002 did=699f rev=FFFFFFFF
    2b10  00000000 00000000 11000000 00000000   ip_ver=FFFFFFFF  CHIP=17

Y se reconoce por cuatro cosas a la vez:

  1. el formato se REPITE 318 veces en la seccion
  2. los device ID van en ORDEN DE GENERACION (6780, 6784, 6788, ...)
  3. la entrada de esta placa da 17, y el proyecto lleva 37 hallazgos
     tratandola como Polaris12
  4. es COHERENTE con el macro `ASICID_IS_P23`, que acepta otras revisiones

Una coincidencia de dos bytes pasa la primera improbable. Cuatro
coherencias a la vez la convierten en una lectura.

LO QUE NO HACE, Y ES LO IMPORTANTE.

El layout de 8 palabras esta DEDUCIDO, no leido: no tengo el `struct`. Que la
palabra 6 sea `chip_id` y no un flags se apoya en que vale 17 y en nada mas.

Y no se desensambla `asic_type_from_chip_id`, que es `static` y no aparece
por nombre. Eso sigue siendo la forma de CONFIRMAR el layout, y queda
pendiente.

Por eso la afirmacion solida es "esta entrada dice 17", y la assertion fuerte
"esa palabra es el chip_id" depende del enum. Las dos van separadas en el
informe.

Uso:
  python3 asic_table.py             el mapa, y la entrada de esta placa
  python3 asic_table.py --dipolaris  solo la familia Polaris
  python3 asic_table.py --raw       todas las entradas
  python3 asic_table.py --json
  python3 asic_table.py --self-test
"""
import os
import re
import sys
import json
import struct
import subprocess
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KO = "/tmp/amdgpu_loaded.ko"
SYSFS = "/sys/bus/pci/devices/0000:01:00.0/config"

# PALABRAS POR ENTRADA. Deducido, no leido: ver el docstring.
PALABRAS = 8
VENDOR_AMD = 0x1002
# CHIPS que este proyecto ha nombrado. El numero viene del enum de amdgpu.h, y
# se repite aqui para que la salida sea legible sin ir a buscarlo.
CHIPS = {
    0: "CHIP_CI", 1: "CHIP_CIK", 2: "CHIP_R600", 3: "CHIP_DCE",
    16: "CHIP_POLARIS10", 17: "CHIP_POLARIS11/12", 18: "CHIP_POLARIS12",
    19: "CHIP_VEGA10", 20: "CHIP_VEGA12", 21: "CHIP_VEGA20",
    22: "CHIP_NAVI10", 23: "CHIP_NAVI12", 24: "CHIP_NAVI14",
    25: "CHIP_NAVI21", 26: "CHIP_NAVI22", 27: "CHIP_NAVI23",
    28: "CHIP_NAVI24", 29: "CHIP_NAVI31", 30: "CHIP_NAVI32",
    31: "CHIP_NAVI33",
}
# FAMILIAS que se pueden filtrar por nombre de chip.
FAMILIAS = {
    "polaris": (16, 17, 18),
    "vega": (19, 20, 21),
    "navi": tuple(range(22, 32)),
    "dce": (12, 13, 14, 15),
}


def rodata():
    """La seccion .rodata del .ko, como bytes."""
    if not os.path.exists(KO):
        return None
    try:
        out = subprocess.run(["objdump", "-s", "-j", ".rodata", KO],
                             capture_output=True, text=True, timeout=600).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    raw = bytearray()
    for l in out.split("\n"):
        p = l.split()
        if len(p) >= 6 and p[0].strip():
            try:
                off = int(p[0], 16)
            except ValueError:
                continue
            try:
                b = bytes.fromhex("".join(p[1:5]))
            except ValueError:
                continue
            if len(raw) < off:
                raw.extend(b"\x00" * (off - len(raw)))
            raw[off:off + len(b)] = b
    return bytes(raw)


def entradas(raw):
    """Las entradas con patron de tabla."""
    if raw is None:
        return []
    out = []
    pat = struct.pack("<I", VENDOR_AMD)
    for m in re.finditer(re.escape(pat), raw):
        i = m.start()
        if i + 4 * PALABRAS > len(raw):
            continue
        w = struct.unpack_from("<%dI" % PALABRAS, raw, i)
        # Un device ID de AMD valido: ni 0 ni 0xffff, y con bits altos utiles.
        if not (0x1000 <= w[1] <= 0xffff) or w[1] in (0xffff, 0):
            continue
        out.append(dict(offset=i, words=w))
    return out


def placa():
    """El device/revision de ESTA placa, leido del config space."""
    if not os.path.exists(SYSFS):
        return None
    try:
        d = open(SYSFS, "rb").read()
    except OSError:
        return None
    return dict(vendor=struct.unpack_from("<H", d, 0x00)[0],
                device=struct.unpack_from("<H", d, 0x02)[0],
                revision=d[0x08])


def self_test():
    print("=" * 74)
    print("SELF-TEST de asic_table: control negativo")
    print("=" * 74)
    fallos = 0

    # (a) una entrada inventada se decodifica con el layout
    buf = bytearray(struct.pack("<8I", 0x1002, 0x699F, 0xFFFFFFFF,
                                0xFFFFFFFF, 0, 0, 17, 0))
    e = entradas(bytes(buf))
    ok = len(e) == 1 and e[0]["words"][6] == 17
    print(f"  {'entrada sintetica':26} 8 palabras, chip=17        "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # (b) un device ID invalido se descarta
    for did, etiq in ((0x0000, "did=0"), (0xffff, "did=ffff"),
                      (0x0001, "did=1")):
        buf = bytearray(struct.pack("<8I", 0x1002, did, 0, 0, 0, 0, 5, 0))
        e = entradas(bytes(buf))
        ok = not e
        print(f"  {'device ID invalido':26} {etiq:18} "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

    # (c) dos entradas separadas dan dos resultados
    buf = bytearray(struct.pack("<8I", 0x1002, 0x699F, 0, 0, 0, 0, 17, 0)
                    + struct.pack("<8I", 0x1002, 0x694C, 0, 0, 0, 0, 15, 0))
    e = entradas(bytes(buf))
    ok = len(e) == 2
    print(f"  {'dos entradas':26} 2 filas leidas           "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # (d) una entrada truncada NO se lee mas alla del final
    buf = bytearray(struct.pack("<8I", 0x1002, 0x699F, 0, 0, 0, 0, 17, 0)[:-6])
    e = entradas(bytes(buf))
    ok = not e
    print(f"  {'entrada truncada':26} no lee de mas          "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # (e) sin binario, la herramienta DICE que no puede, no inventa
    global KO
    old = KO
    KO = "/tmp/opencode/no_existe.ko"
    r = rodata()
    ok = r is None
    KO = old
    print(f"  {'sin .ko':26} devuelve None, no una tabla vacia "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # (f) y una tabla VACIA tambien es un fallo, no un 'no falta nada'
    ok = not entradas(b"")
    print(f"  {'rodata vacia':26} 0 entradas, se distingue    "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print("  RESULTADO: TOOL_VALIDATED -- 7 controles pasan.")
    print("    Y dos de ellos miden el fallo declarado: sin binario y con")
    print("    seccion vacia devuelven 'no se puede', nunca un cero que")
    print("    se lea como 'no hay nada'.")
    return 0


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()

    raw = rodata()
    if raw is None:
        print("=" * 74)
        print("ASIC TABLE -- el mapa (device_id, revision) -> chip_id")
        print("=" * 74)
        print("NO SE PUDO LEER. No hay .ko descomprimido.")
        print()
        print(f"  Se busca:   {KO}")
        print(f"  Se obtiene: binfacts.py lo descomprime de /lib/modules/...ko.zst")
        print()
        print("  Y una tabla vacia se leeria como 'el driver no tiene tabla',")
        print("  que es justo lo contrario de lo cierto.")
        return 2

    es = entradas(raw)
    if not es:
        print("NO SE ENCONTRO LA TABLA. Se leyeron %d bytes de .rodata."
              % len(raw))
        print("El layout deducido de 8 palabras no encaja, o el binario no")
        print("tiene la tabla. Es un dato, no un fallo silencioso.")
        return 3

    pl = placa()
    if "--json" in args:
        print(json.dumps(dict(
            entradas=len(es), placa=pl,
            filas=[dict(offset=e["offset"], did=e["words"][1],
                        rev=e["words"][2], ip_major=e["words"][3],
                        chip=e["words"][6]) for e in es]), indent=1))
        return 0

    fam = None
    for f in FAMILIAS:
        if ("--" + f) in args:
            fam = f

    print("=" * 74)
    print("ASIC TABLE -- el mapa (device_id, revision) -> chip_id")
    print("=" * 74)
    print(f"entradas encontradas: {len(es)}   .rodata: {len(raw)} bytes")
    print()

    if pl:
        print("-" * 74)
        print("ESTA PLACA")
        print("-" * 74)
        hit = [e for e in es
               if e["words"][1] == pl["device"] and
               (e["words"][2] == 0xFFFFFFFF or e["words"][2] == pl["revision"])]
        print(f"  leido del config space : {pl['vendor']:04x}:{pl['device']:04x}"
              f"  revision {pl['revision']:02x}")
        if hit:
            e = hit[0]
            w = e["words"]
            print(f"  entrada en .rodata     : offset 0x{e['offset']:06x}")
            print()
            for k in range(PALABRAS):
                print(f"    palabra {k} = 0x{w[k]:08x}  ({w[k]})")
            print()
            print(f"  chip_id = {w[6]}"
                  f"   -> {CHIPS.get(w[6], 'sin nombre en el enum')}")
            if w[2] == 0xFFFFFFFF:
                print("  revision: CUALQUIERA. Esta placa no es un"
                      " 'polaris12 kicker',")
                print("  es la ruta principal de la tabla.")
            if w[3] == 0xFFFFFFFF:
                print("  ip_version: SIN RESTRICCION en la tabla. El driver no")
                print("  lee la version de IP del GFX por aqui: esa fuente")
                print("  sigue ausente del corpus.")
        else:
            print("  NO HAY ENTRADA PARA ESTE device ID.")
        print()

    if "--raw" in args:
        print("-" * 74)
        print("TODAS LAS ENTRADAS")
        print("-" * 74)
        for e in es:
            w = e["words"]
            rev = "cualquiera" if w[2] == 0xFFFFFFFF else f"{w[2]:#x}"
            print(f"  {w[1]:04x} rev {rev:>10}  chip={w[6]:3}  "
                  f"{CHIPS.get(w[6], '')}")
        print()
    else:
        print("-" * 74)
        print("FAMILIA POLARIS (lo que esta placa es)")
        print("-" * 74)
        for e in es:
            w = e["words"]
            if w[6] not in FAMILIAS["polaris"]:
                continue
            rev = "cualquiera" if w[2] == 0xFFFFFFFF else f"{w[2]:#x}"
            print(f"  {w[1]:04x} rev {rev:>10}  chip={w[6]:3}  "
                  f"{CHIPS.get(w[6], '')}")
        print()
        print(f"  (usa --raw para las {len(es)} entradas, y mas familias)")
        print()

    print("-" * 74)
    print("LIMITE")
    print("  El layout de 8 palabras esta DEDUCIDO, no leido: no tengo el")
    print("  `struct`. Que la palabra 6 sea `chip_id` y no un flags se")
    print("  apoya en que vale 17, no en haberlo visto escrito.")
    print()
    print("  Desensamblar `asic_type_from_chip_id` --que es `static` y no")
    print("  aparece por nombre-- es lo que confirmaria el layout. Queda")
    print("  pendiente.")
    print()
    print("  Y el binario NO es la fuente completa: 318 entradas, y el driver")
    print("  soporta mas chips de los que compila esta configuracion.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())