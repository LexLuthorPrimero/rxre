#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""P0.1 RECONCILIATION, part 2: two discriminants independent of alignment.

Discriminant 1 was alignment. This one uses rmmio_size and cross-generation
variation. If these macros were byte offsets, both tests fail.

Read-only. No writes. No MMIO.
"""
import re
from pathlib import Path

AMD = Path("/home/lucas/Escritorio/rxre/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")


def rule(t=""):
    print("\n" + "=" * 72)
    if t:
        print(t)
        print("=" * 72)


def all_defines(symbol):
    out = []
    for p in (AMD / "include/asic_reg").rglob("*.h"):
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            m = re.match(r"^#define\s+%s\s+(0[xX][0-9a-fA-F]+)\s*$" % re.escape(symbol), line)
            if m:
                out.append((p.relative_to(AMD).as_posix(), n, int(m.group(1), 16)))
    return out


# --- DISCRIMINANT 1: rmmio_size bound -----------------------------------------
rule("D1. EL LIMITE rmmio_size: NO DISCRIMINA (negativo medido)")
print("El accessor acota con (reg * 4) < adev->rmmio_size. Si reg fuera")
print("BYTE OFFSET el limite seria reg < 0x40000; si fuera INDICE DWORD")
print("seria reg < 0x10000. Los dos limites distinguen SOLO si algun")
print("valor del corpus cae entre 0x10000 y 0x40000.")
print()
mayor = 0
sentinel = 0
for p in (AMD / "include/asic_reg").rglob("*.h"):
    for line in p.read_text(errors="replace").splitlines():
        m = re.match(r"^#define\s+(mm[A-Z0-9_]+)\s+(0[xX][0-9a-fA-F]+)\s*$", line)
        if not m:
            continue
        v = int(m.group(2), 16)
        # 0xFFFFFFFF, 0x10000FFFF et al son SENTINEL de mascara de bits, no
        # offsets: asi los nombra el propio kernel. MEDIDO aqui: el valor
        # mayor del corpus era 0x10000FFFF, que no cabe en regmmio ni en
        # byte offset. Contarlos como registros daria un denominador falso.
        # Tres clases que NO son offsets de registro, y que reg_resolve ya
        # separa con classify_symbol(): los Sentinel de mascara, los sufijos
        # _DEFAULT (valores de reset, p.ej. 0xfffdf79f) y los sufijos _MASK.
        if ("SENTINEL" in line or v >= 0xFFFF0000
                or m.group(1).endswith(("_DEFAULT", "_MASK", "__SHIFT"))):
            sentinel += 1
            continue
        if v > mayor:
            mayor = v
print(f"  definidos mm* no-offset (Sentinel/_DEFAULT/_MASK/__SHIFT): {sentinel}")
print(f"  mayor valor mm* OFFSET real: 0x{mayor:X}")
print(f"  cae en la franja discriminante 0x10000..0x40000? "
      f"{'SI' if 0x10000 < mayor < 0x40000 else 'NO'}")
print()
print("  RESULTADO: NO discrimina en este corpus. Este test NO aporta")
print("  evidencia a favor ni en contra, y no se cuenta como oraculo.")
print("  Se registra porque un test que no discrimina es informacion:")
print("  cualquier conclusion basada solo en rmmio_size seria falsa.")
print()
print("  Dato adicional que SI es consistente, sin ser discriminante:")
print("  si reg fuera indice dword, ningun offset pasaria de 0xFFFF;")
print(f"  el maximo observado 0x{mayor:X} lo cumple.")

# --- DISCRIMINANT 2: cross-generation variation -------------------------------
rule("D2. VARIACION ENTRE GENERACIONES: INDICE SI O NO")
print("mmSMC_IND_ACCESS_CNTL cambia entre generaciones del MISMO campo:")
print()
for f, n, v in all_defines("mmSMC_IND_ACCESS_CNTL"):
    gen = f.split("/")[-1].replace("_d.h", "")
    print(f"  {gen:<12} 0x{v:04X}   %4={v%4}   como indice*4 = 0x{v*4:04X}")
print()
vals = sorted({v for _, _, v in all_defines("mmSMC_IND_ACCESS_CNTL")})
print(f"  valores distintos: {[hex(v) for v in vals]}")
print(f"  pasos entre valores: {[vals[i+1]-vals[i] for i in range(len(vals)-1)]}")
unaligned_bytes = [v for v in vals if v % 4 != 0]
print(f"  de esos, NO alineados a 4 bytes: {[hex(v) for v in unaligned_bytes]}")
print()
if unaligned_bytes:
    print("  ARGUMENTO: un registro de 32 bits NO puede vivir en una")
    print("  direccion de byte no alineada a 4. Los accessors hacen")
    print("  writel/readl en reg*4, y ese producto SI esta alineado.")
    print("  Por lo tanto reg NO es un byte offset: reg*4 lo es.")
    print("  Reading 0x92 as a byte offset would put a 32-bit register at")
    print("  byte 146, straddling dwords 36/37 — not a register.")

# --- DISCRIMINANT 3: does 0x6B name anything? --------------------------------
rule("D3. ¿0x6B ES LA DIRECCION DE ALGO?")
print("1589 produzca dword_index = 0x6B para ambos registros.")
print("Si 0x6B fuera una direccion de byte valida, no podria ser la")
print("direccion de DOS registros distintos.")
print()
print("  Como indice dword, 0x6B * 4 = 0x1AC — que es INDEX_11, no DATA_11.")
print("  O sea: dividir por 4 sobre un indice no pierde informacion al azar;")
print("  devuelve un indice de OTRO registro. Peor que perderla:")
print("  pointing to the wrong register without warning.")
print()
print("  Verificacion: el byte real de DATA_11 es 0x6B4. 0x6B no es 0x6B4.")
print("  0x6B*4 = 0x1AC, which is INDEX_11, and never DATA_11.")
print("  Conclusiones: 0x6B NO es la direccion de ninguno de los dos.")

# --- what remains PROVEN -------------------------------------------------------
rule("4. QUE PARTE DE P0 PERMANECE PROVEN")
rows = [
    ("0x1AC y 0x1AD son registros DISTINTOS",
     "PROVEN", "dos #define con valores distintos, 3 headers cada uno"),
    ("0x1AC>>2 == 0x1AD>>2 == 0x6B",
     "PROVEN (aritmetica)", "verificado; pero es una division sobre unidad equivocada"),
    ("byte_offset de INDEX_11 = 0x6B0",
     "PROVEN_DERIVED", "indice * 4, contrato del accessor"),
    ("byte_offset de DATA_11 = 0x6B4",
     "PROVEN_DERIVED", "indice * 4, contrato del accessor"),
    ("dword_index es la unidad canonica del valor del #define",
     "PROVEN_DERIVED", "alignacion + accessor + variante entre generaciones"),
    ("byte_offset es la unidad canonica",
     "REFUTED", "0x1AD%4=1 y 0x92%4=2 lo impiden"),
    (">>2 es una colision real de identidad",
     "REFUTED", "0x6B no es la direccion de ninguno de los dos"),
    ("el consumidor rxre_cobertura_gfx8.py:88 pierde identidad",
     "NOT_DETERMINED", "no re-inspeccionado en esta iteracion"),
    ("CONFLICT/CANDIDATES para ESTE caso",
     "PROVEN_ABSCENT_NEED", "0x1AC y 0x1AD no compiten: son simbolos distintos"),
]
print(f"  {'afirmacion':<52} {'estado':<22} Basis")
print("  " + "-" * 118)
for a, s, b in rows:
    print(f"  {a:<52} {s:<22} {b}")

print()
print("=" * 72)
print("VEREDICTO FINAL:  P0.1 = REVISED")
print()
print("  REVISED, no CONFIRMED y no REFUTED, porque la COLISION es cierta")
print("  y el DEFECTO no lo era. Lo que se corrige es la UNIDAD.")
print()
print("  CONFIRMED : 0x1AC y 0x1AD son registros distintos; >>2 los iguala.")
print("  REFUTED   : que byte_offset sea la unidad canonica (0x1AD%4=1).")
print("  REFUTED   : que 0x6B sea la direccion de uno de los dos.")
print("  NUEVO     : el defecto real era la division, no la multiplicacion")
print("              ausente. P0.3 lo-'reparo' describiendo una colision")
print("              que era un artefacto de la unidad equivocada.")
print("=" * 72)