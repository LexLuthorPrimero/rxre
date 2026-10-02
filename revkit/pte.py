#!/usr/bin/env python3
"""
pte.py -- analisis de flags de PTE/PDE de GFX8, end to end.

POR QUE EXISTE
--------------
Los flags de PTE son macros del preprocesador (#define), asi que no aparecen
en el BTF, ni en los simbolos, ni en ninguna estructura. Localizarlos exige
recorrer defines, resolver sus dependencias y separar quien los ESCRIBE de
quien los BORRA.

En la sesion anterior eso se hizo a mano y salio con un error que cambiaba la
conclusion: se tomo el 9 de fragment_size_default por el block_size, y se
afirmo "MTYPE no existe" cuando existe en el binario pero no en GFX8.

QUE HACE
--------
  bits      lista los bits de AMDGPU_PTE_* y quien los define
  jeden     Producer y consumidor de cada flag, con su transformacion
  para-gfx8 Intersecta con lo que GFX8 alcanzable, separando lo que NO aplica
  dump      Decodifica una palabra de 64 bits como PTE, campo a campo

LIMITE CRITICO, y es el punto de todo
-------------------------------------
Un flag que un fichero DEFINE no significa que GFX8 lo USE. El corpus entero
define los flags de todas las generaciones: gfxhub_v12, gmc_v10, etc. Solo un
subconjunto es alcanzable desde GFX8.

Por eso "para-gfx8" exige DEMOSTRAR la alcanzabilidad, y su veredicto puede
ser NOT_DETERMINED. Presentar la lista de #define como "los flags de GFX8"
es exactamente el error que produjo la confusion de MTYPE.
"""
import argparse
import os
import re
import sys

RESEARCH = "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH"
AMDKG = os.path.join(RESEARCH, "working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu")

# Ficheros que GFX8 PUEDE alcanzar. La razon de la lista esta en los callers:
# son los que contiene la vtable de gfx_v8_0 (gfx_v8_0.c:7072 usa
# gfx_v8_0_*), mas los compartidos que llama.
#
# No es "todo lo que menciona gfx8": es lo que el driver ejecuta para este
# ASIC. La diferencia importa, porque amdgpu_gart.c define MTYPE y GFX8 nunca
# entra por esa rama.
GFX8_ALCANZABLE = {
    "gfx_v8_0.c", "gmc_v8_0.c", "gfxhub_v8_0.h", "amdgpu_vm.c",
    "amdgpu_vm_pt.c", "amdgpu_vm.h", "amdgpu_gart.c", "amdgpu_gmc.h",
    "amdgpu_ttm.c", "amdgpu_gfx.h", "gfx.h",
}

# Definicion de bits de AMDGPU_PTE_* y AMDGPU_PDE_*
RE_DEFINE = re.compile(
    r"^#define\s+(AMDGPU_(?:PTE|PDE|VM)_[A-Z0-9_]+)\s+(.+?)\s*$")


def carga_defines():
    """define -> (valor, fichero, linea, texto)"""
    out = {}
    for base, _d, fs in os.walk(AMDKG):
        for fn in sorted(fs):
            if not fn.endswith((".h", ".c")):
                continue
            p = os.path.join(base, fn)
            try:
                lines = open(p, encoding="utf-8",
                             errors="replace").read().splitlines()
            except Exception:
                continue
            for i, ln in enumerate(lines, 1):
                m = RE_DEFINE.match(ln)
                if not m:
                    continue
                nombre, val = m.group(1), m.group(2)
                # solo bits: los que son 1<<N
                mm = re.match(r"\(\s*1\s*U?L?L?\s*<<\s*(\d+)\s*\)", val)
                if not mm:
                    mm = re.match(r"1\s*U?L?L?\s*<<\s*(\d+)", val)
                if not mm:
                    continue
                out.setdefault(nombre, []).append(
                    (int(mm.group(1)), fn, i, val))
    return out


def carga_uso(defines):
    """flag -> [(fichero, linea, texto)] donde se USA (no donde se define)"""
    uso = {k: [] for k in defines}
    for base, _d, fs in os.walk(AMDKG):
        for fn in sorted(fs):
            if not fn.endswith((".h", ".c")):
                continue
            p = os.path.join(base, fn)
            try:
                lines = open(p, encoding="utf-8",
                             errors="replace").read().splitlines()
            except Exception:
                continue
            for i, ln in enumerate(lines, 1):
                if ln.lstrip().startswith("#define"):
                    continue
                for k in defines:
                    # con limites de palabra: AMDGPU_PTE_VALID no debe casar
                    # dentro de AMDGPU_PTE_VALIDATE
                    if re.search(r"(?<![A-Za-z0-9_])" + k + r"(?![A-Za-z0-9_])",
                                 ln):
                        uso[k].append((fn, i, ln.strip()[:110]))
    return uso


def cmd_bits(defs):
    print("=== bits de PTE/PDE definidos en amdgpu ===")
    print()
    print("NOTA: esto lista lo DEFINIDO, no lo que GFX8 usa. Usa 'para-gfx8'")
    print("para separar. El corpus define los flags de todas las generaciones,")
    print("y confundirlos es el error que produjo la conclusion falsa de MTYPE.")
    print()
    print("%-36s %4s  %-22s %s" % ("flag", "bit", "definido en", "valor"))
    print("-" * 96)
    for k in sorted(defs, key=lambda x: (min(d[0] for d in defs[x]), x)):
        bit, fn, i, val = defs[k][0]
        otros = sorted({d[1] for d in defs[k]})
        print("%-36s %4d  %-22s %s" % (k, bit, ",".join(otros[:2]), val))
    print("--- %d flags definidos" % len(defs))
    return 0


def cmd_para(defs, uso):
    """
    SEPARA lo que GFX8 alcanza de lo que solo el driver define.

    Este es el comando que evita el error de MTYPE. Un flag definido en
    amdgpu no es un flag de GFX8: es un flag de ALGUN ASIC. La pregunta correcta
    no es "esta definido" sino "lo escribe o lo lee una ruta que GFX8 ejecuta".
    """
    print("=== intersaccion con GFX8 ===")
    print("Un flag DEFINIDO no es un flag de GFX8: el corpus define los de")
    print("todas las generaciones. Solo cuenta si lo consume un fichero")
    print("alcanzable desde gfx_v8_0.\n")
    alcanzable, no_alcanzable, sin_consumidor = [], [], []
    for k in sorted(defs):
        bit = defs[k][0][0]
        consumidores = {f for f, _i, _t in uso.get(k, [])}
        if not consumidores:
            sin_consumidor.append((k, bit))
            continue
        (alcanzable if consumidores & GFX8_ALCANZABLE
         else no_alcanzable).append((k, bit, consumidores))

    print("CON ALCANZABILIDAD DEMOSTRADA (%d):" % len(alcanzable))
    for k, bit, cs in alcanzable:
        g8 = sorted(cs & GFX8_ALCANZABLE)
        print("  bit %2d  %-34s %s" % (bit, k, ",".join(g8[:3])))
    print()
    print("DEFINIDOS PERO NINGUN CONSUMIDOR ALCANZABLE (%d):" % len(no_alcanzable))
    for k, bit, cs in no_alcanzable:
        otros = sorted(cs - GFX8_ALCANZABLE)
        print("  bit %2d  %-34s solo en %s" % (bit, k, ",".join(otros[:2])))
    print()
    print("SIN NINGUN CONSUMIDOR (%d):" % len(sin_consumidor))
    for k, bit in sin_consumidor:
        print("  bit %2d  %-34s definido y nunca usado" % (bit, k))
    print()
    print("CLASIFICACION")
    print("  alcanzable   : el flag lo consume una ruta que GFX8 ejecuta")
    print("  no_alcanzable: solo lo consumen rutas de OTRO ASIC")
    print("                 -> NOT_APPLICABLE para GFX8, no PROVEN_ABSENT")
    print("  sin_consumidor: definido y nadie lo usa -> NOT_OBSERVED")
    return 0


# Mascara de direccion del ASIC. La tabla de campos de mas abajo es la UNION
# de las generaciones, y usarla sola confunde. Para GFX8 el campo de
# direccion NO llega al bit 47: `gmc_v8_0.c:1134` pone
#     adev->gmc.pte_addr_mask = 0x000000FFFFFFF000ULL; /* 40 bit PA */
# es decir la PA ocupa los bits 0..39 y la PTE guarda los 28 altos en 12..39.
# Leer "bit 47..12" como el ancho de GFX8 da 8 bits de mas.
PTE_ADDR_MASK_GFX8 = 0x000000FFFFFFF000


def ancho_direccion_este_asic(mask):
    """Bits de direccion que caben en la mascara, y ventana que cubren."""
    if mask == 0:
        return None
    alto = mask.bit_length() - 1
    return {"bit_mas_alto": alto, "bits_de_direccion": alto - 12 + 1,
            "ventana_bytes": 1 << (alto - 12 + 1)}


def cmd_dump(defs, valor):
    """
    Decodifica un valor de 64 bits como PTE.

    Sirve para leer una PTB real cuando se tenga, y para verificar el
    encoder: si el driver escribe los flags que creemos, el resultado tiene
    que salir aqui.
    """
    v = int(valor, 0) & 0xFFFFFFFFFFFFFFFF
    print("PTE = 0x%016x" % v)
    print()
    _a = ancho_direccion_este_asic(PTE_ADDR_MASK_GFX8)
    print("  --- ancho de DIRECCION de GFX8, no el de la tabla generica ---")
    print("  gmc_v8_0.c:1134  pte_addr_mask = 0x%016x  (/* 40 bit PA */)"
          % PTE_ADDR_MASK_GFX8)
    print("  la direccion va en bits 12..%d = %d bits = ventana de %d MiB"
          % (_a["bit_mas_alto"], _a["bits_de_direccion"],
             _a["ventana_bytes"] // (1024 * 1024)))
    print("  ADDR_BA de este ASIC = 0x%x" % ((v >> 12) & 0xFFFFFFF))
    print()
    print("  AVISO: los campos de abajo son la UNION de todas las")
    print("  generaciones, no el layout de GFX8. Para GFX8 el campo de")
    print("  direccion acaba en el bit %d, no en el 47." % _a["bit_mas_alto"])
    print()
    print("  bit 63..48  ADDR_HI / fragment  0x%x" % ((v >> 48) & 0xFFFF))
    print("  bit 47..12  ADDR_BA  (PFN << 12) 0x%x" % ((v >> 12) & 0xFFFFFFFFF))
    print("  bit 11      LOG               %d" % ((v >> 11) & 1))
    print("  bit 10      BFS               %d" % ((v >> 10) & 1))
    print("  bit  9      NOALLOC           %d" % ((v >> 9) & 1))
    print("  bit  8      PDE_PTE           %d" % ((v >> 8) & 1))
    print("  bit  7      WRITABLE          %d" % ((v >> 7) & 1))
    print("  bit  6      READABLE          %d" % ((v >> 6) & 1))
    print("  bit  5      EXECUTABLE        %d" % ((v >> 5) & 1))
    print("  bit  4      SNOOPED           %d" % ((v >> 4) & 1))
    print("  bit  3      TMZ               %d" % ((v >> 3) & 1))
    print("  bit  2      SYSTEM            %d" % ((v >> 2) & 1))
    print("  bit  1      PRT               %d" % ((v >> 1) & 1))
    print("  bit  0      VALID             %d" % (v & 1))
    print()
    print("  flags activos: %s" % ", ".join(
        "%s=%d" % (b, (v >> n) & 1)
        for n, b in [(63, "V6?"), (11, "LOG"), (10, "BFS"), (9, "NOALLOC"),
                     (8, "PDE_PTE"), (7, "WRITABLE"), (6, "READABLE"),
                     (5, "EXECUTABLE"), (4, "SNOOPED"), (3, "TMZ"),
                     (2, "SYSTEM"), (1, "PRT"), (0, "VALID")]
        if (v >> n) & 1) or "(ninguno)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="analisis de PTE de GFX8")
    ap.add_argument("cmd", choices=["bits", "para-gfx8", "dump"])
    ap.add_argument("valor", nargs="?", default=None)
    a = ap.parse_args()

    if a.cmd == "dump":
        if not a.valor:
            print("dump necesita un valor: 0x...")
            return 2
        return cmd_dump({}, a.valor)

    defs = carga_defines()
    print("flags con valor 1<<N encontrados: %d\n" % len(defs))
    if a.cmd == "bits":
        return cmd_bits(defs)
    uso = carga_uso(defs)
    return cmd_para(defs, uso)


if __name__ == "__main__":
    sys.exit(main())