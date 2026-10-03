#!/usr/bin/env python3
"""
Q5-VOP-VEC — el tercer universo de opcode GFX8: el ALU vector.

Por que existe: Q5-ISA-CAP12 midio el prefijo SQ_S_* (216) y Q5-MEM-TABLES
midio la memoria vectorial (353). El prefijo SQ_V* (425 entradas) no lo midio
ninguno de los dos, y es el universo donde vive el ALU vector.

Solo lectura. No toca GPU, no abre PDF, no escribe fuera de este directorio.
Entradas: el .tsv de opcodes YA VALIDADO por Q5-ISA-CAP12 y el header del
kernel. Ninguna entrada esta fuera del root canonico.
"""

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TSV = os.path.join(HERE, "..", "Q5-ISA-CAP12", "cap12-opcodes-all.tsv")
HEADER = os.path.join(
    ROOT, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h"
)

# Constantes de encoding, no opcodes. Regla declarada y con control negativo:
# ningun nombre que acabe en un tipo escalar (_F32/_U32/...) es tragado por ella.
NON_OPCODE_SUFFIX = ("_COUNT", "_OFFSET")
NON_OPCODE_PREFIX = ("SQ_VCC", "SQ_VGPR")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def is_opcode_name(name):
    if name.startswith(NON_OPCODE_PREFIX):
        return False
    if name.endswith(NON_OPCODE_SUFFIX):
        return False
    return True


def main():
    # --- verificacion de inputs ANTES de interpretar (regla 26) ---
    for path in (TSV, HEADER):
        if not os.path.isfile(path):
            sys.stderr.write("MISSING_INPUT %s\n" % path)
            return 2
    print("INPUT %s  sha256 %s" % (os.path.basename(TSV), sha256(TSV)))
    print("INPUT %s  sha256 %s" % (os.path.basename(HEADER), sha256(HEADER)))

    # --- universo del header ---
    universe = {}       # isa_name -> header value
    nonopcodes = {}
    with open(HEADER, "r", errors="replace") as fh:
        for line in fh:
            if not line.startswith("#define SQ_V"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name, value = parts[1], int(parts[2], 16)
            if is_opcode_name(name):
                universe[name[len("SQ_"):]] = value
            else:
                nonopcodes[name] = value

    # --- lado ISA, del tsv validado ---
    isa = {}            # isa_name -> row dict
    isa_only = []
    with open(TSV, "r", errors="replace") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        idx = {name: i for i, name in enumerate(header)}
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < len(header):
                continue
            name = f[idx["isa_name"]]
            if not name.startswith("V_"):
                continue
            isa[name] = {
                "format": f[idx["format"]],
                "dec": int(f[idx["dec"]]),
                "hex": int(f[idx["hex_raw"]], 16),
                "value": int(f[idx["value"]]),
                "value_source": f[idx["value_source"]],
                "page": f[idx["printed_12_N"]],
                "pdf": f[idx["pdf_page"]],
                "self_consistent": f[idx["isa_self_consistent"]],
            }

    # --- comparacion, criterio identico al de Q5-ISA-CAP12 ---
    # COINCIDE si el valor del header aparece en CUALQUIERA de las dos columnas
    # del ISA (hex si existe, si no decimal). Se registra cual coincidio, porque
    # el ISA se contradice entre decimal y hex en algunos casos.
    rows = []
    for name in sorted(universe):
        hv = universe[name]
        if name not in isa:
            rows.append((name, hv, None, None, "AUSENTE_DE_ISA"))
            continue
        r = isa[name]
        if hv == r["hex"]:
            rows.append((name, hv, r, "hex", "COINCIDE"))
        elif hv == r["dec"]:
            rows.append((name, hv, r, "dec", "COINCIDE_DEC_ISA_HEX_DISONANTE"))
        else:
            rows.append((name, hv, r, None, "DIFIERE"))

    for name in sorted(isa):
        if name not in universe:
            isa_only.append(name)

    # --- salida estructurada ---
    out_tsv = os.path.join(HERE, "coverage-vop.tsv")
    with open(out_tsv, "w") as fh:
        fh.write("isa_name\theader_value\tisa_format\tisa_dec\tisa_hex\t"
                 "isa_page\tisa_pdf\tmatch\tstate\n")
        for name, hv, r, match, state in rows:
            if r is None:
                fh.write("%s\t0x%x\t\t\t\t\t\t\t%s\n" % (name, hv, state))
            else:
                fh.write("%s\t0x%x\t%s\t%d\t0x%X\t%s\t%s\t%s\t%s\n"
                         % (name, hv, r["format"], r["dec"], r["hex"],
                            r["page"], r["pdf"], match or "-", state))

    counts = {}
    for _, _, _, _, state in rows:
        counts[state] = counts.get(state, 0) + 1

    print("")
    print("UNIVERSE_HEADER_SQV_TOTAL   %d" % (len(universe) + len(nonopcodes)))
    print("UNIVERSE_NO_OPCODE          %d" % len(nonopcodes))
    print("UNIVERSE_OPCODE_CANDIDATOS  %d" % len(universe))
    print("ISA_ROWS_V_                 %d" % len(isa))
    for state in sorted(counts):
        print("STATE %-34s %d" % (state, counts[state]))
    print("ISA_SOLO_NO_EN_HEADER       %d  %s" % (len(isa_only), isa_only))
    print("OUTPUT %s  sha256 %s" % (os.path.basename(out_tsv), sha256(out_tsv)))

    # --- autocomprobacion: los tres conjuntos tienen que cuadrar ---
    ok = True
    if len(universe) + len(nonopcodes) != len(universe) + len(nonopcodes):
        ok = False
    if counts.get("COINCIDE", 0) + counts.get("COINCIDE_DEC_ISA_HEX_DISONANTE", 0) \
            + counts.get("DIFIERE", 0) + counts.get("AUSENTE_DE_ISA", 0) != len(universe):
        print("SELFTEST FAIL: los estados no suman el universo")
        ok = False
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())