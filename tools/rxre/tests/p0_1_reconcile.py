#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""P0.1 RECONCILIATION — what unit do 0x1AC / 0x1AD represent, and is >>2 correct?

Read-only. No tool is used as semantic authority: every claim cites kernel
source. reg_resolve.py is only asked what it currently DOES, never what the
unit SHOULD be.

The decisive test is alignment. If these were byte offsets, a 32-bit register
at a non-multiple-of-4 address would be impossible, because the accessors do
writel/readl at that address.
"""
import re
import subprocess
import sys
from pathlib import Path

RXRE = Path(__file__).resolve().parents[3]
AMD = RXRE / "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"


def defines(symbol):
    """Every #define of symbol in asic_reg, with file and line."""
    out = []
    for p in (AMD / "include/asic_reg").rglob("*.h"):
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            m = re.match(r"^#define\s+%s\s+(0[xX][0-9a-fA-F]+)\s*$" % re.escape(symbol), line)
            if m:
                out.append((p.relative_to(AMD).as_posix(), n, int(m.group(1), 16)))
    return out


def rxre_now(symbol):
    """What reg_resolve does TODAY. Behaviour, not authority."""
    p = subprocess.run([sys.executable, "-B", str(RXRE / "tools/rxre/rxre"),
                        "register", symbol, "--gfx", "gfx_8_0", "--timeout", "40"],
                       cwd=RXRE, capture_output=True, text=True, timeout=60,
                       env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    import json
    r = json.loads(p.stdout)["results"][0]
    return {k: r.get(k) for k in ("value", "dword_index", "byte_offset", "unit")}


def rule(t=""):
    print("\n" + "=" * 72)
    if t:
        print(t)
        print("=" * 72)


# --- 1. the declared constants ------------------------------------------------
rule("1. LAS CONSTANTES DECLARADAS (header)")
for sym in ("mmSMC_IND_INDEX_11", "mmSMC_IND_DATA_11", "mmSMC_IND_ACCESS_CNTL"):
    print(f"\n{sym}")
    for f, n, v in defines(sym):
        print(f"  {f}:{n:<5} 0x{v:04X}   %4 = {v % 4}")

# --- 2. THE DECISIVE TEST ------------------------------------------------------
rule("2. TEST DECISIVO: ALINEACION")
print("Si el valor fuera un BYTE OFFSET, un registro de 32 bits en una")
print("direccion no multiplo de 4 seria imposible: los accessors hacen")
print("writel/readl EN esa direccion, y el hardware no tendria registro ahi.")
print()
print("  simbolo                 valor   %4   leido como indice*4   alineado?")
for sym in ("mmSMC_IND_INDEX_11", "mmSMC_IND_DATA_11", "mmSMC_IND_ACCESS_CNTL"):
    for f, n, v in defines(sym):
        if "7_1_1" not in f and "7_1_2" not in f and "7_1_3" not in f:
            continue
        b = v * 4
        print(f"  {sym:<24} 0x{v:04X}  {v%4}      0x{b:04X}            {b%4==0}")
print()
print("  RESULTADO: 0x1AC%4==0 pero 0x1AD%4==1 y 0x92%4==2.")
print("  Leidos como byte offsets, DOS de esos registros de 32 bits estan")
print("  desalineados. Leidos como indice dword, los TRES son validos.")
print("  => CASO A: la unidad es indice dword de registro.")

# --- 3. the chain --------------------------------------------------------------
rule("3. LA CADENA, con la fuente de cada eslabon")
chain = [
    ("header", "smu_7_1_1_d.h:179-180",
     "#define mmSMC_IND_INDEX_11 0x1AC / DATA_11 0x1AD"),
    ("", "smu7_smumgr.c:43",
     "cgs_write_register(hwmgr->device, mmSMC_IND_INDEX_11, smc_addr)  -- la MACRO"),
    ("cgs", "amdgpu_cgs.c:50-55",
     "static void amdgpu_cgs_write_register(..., unsigned offset, v) { WREG32(offset, v); }"),
    ("macro", "amdgpu.h:1295",
     "#define WREG32(reg, v) amdgpu_device_wreg(adev, (reg), (v), 0)"),
    ("accessor", "amdgpu_reg_access.c:494,501",
     "if ((reg * 4) < adev->rmmio_size) ... writel(v, adev->rmmio + (reg * 4))"),
    ("", "amdgpu_reg_access.c:482",
     "@reg: dword aligned register offset"),
]
for role, cite, text in chain:
    print(f"  {role:<9} {cite:<32} {text}")
print()
print("  Transformacion documentada: reg -> reg * 4 (byte). Multiplica.")
print("  La frase '@reg: dword aligned register offset' se lee 'offset de")
print("  registro alineado a dword', y la operacion del accessor lo confirma.")

# --- 4. the collision, re-derived ---------------------------------------------
rule("4. LA COLISION DE 1589, RE-DERIVADA")
i, d = 0x1AC, 0x1AD
print(f"  >> 2 sobre el valor INDICE :  0x{i:X}>>2 = 0x{i>>2:X}   0x{d:X}>>2 = 0x{d>>2:X}   iguales = {i>>2 == d>>2}")
print(f"  valor como indice, byte = *4:  0x{i*4:X}              0x{d*4:X}              iguales = {i*4 == d*4}")
print(f"  identidad preservada con >>2 ? NO. Con *4 ? SI.")
print()
print("  1589 trato 0x1AC como byte_offset y luego lo dividio. Esa division")
print("  produce 0x6B, que NO es la direccion de byte de NINGUNO de los dos:")
print(f"    byte real de INDEX_11 = 0x{i*4:X}")
print(f"    byte real de DATA_11  = 0x{d*4:X}")
print("  0x6B=107 no es 0x6B0 ni 0x6B4. Dividir produce un numero sin")

# --- 5. what reg_resolve does now ---------------------------------------------
rule("5. LO QUE reg_resolve HACE HOY (comportamiento, no autoridad)")
for sym in ("mmSMC_IND_INDEX_11", "mmSMC_IND_DATA_11"):
    print(f"  {sym}: {rxre_now(sym)}")

# --- 6. is >>2 ever right anywhere? -------------------------------------------
rule("6. ¿ES >>2 CORRECTA EN ALGUN CASO?")
print("  Solo si la entrada fuera un byte offset. En este corpus las macros")
print("  mm* son indices dword por el contrato de amdgpu_device_wreg/rreg.")
print("  Con byte offsets reales (RREG8 / amdgpu_mm_rreg8) la unidad SI es")
print("  byte, pero esos NO pasan por reg_resolve: son otra API.")
print()
print("  El documento de reg_resolve (1602) lo dice explicitamente:")
print("    byte_offset = valor * 4")

print()
print("=" * 72)
print("VEREDICTO:  P0.1 = REVISED")
print("  La COLISION 0x1AC>>2 == 0x1AD>>2 es aritmeticamente cierta.")
print("  El DEFECTO que la empujaba (byte_offset como unidad canonica) es")
print("  FALSO: la unidad canonica es el indice dword.")
print("  >>2 no era una colision real: era una division sobre la unidad")
print("  equivocada, que produce 0x6B, direccion que no existe.")
print("=" * 72)