#!/usr/bin/env python3
"""
Q5-VOP-VEC — prediccion de VOPC: ¿el header GFX8 se deriva de la
descripcion parametrica del ISA GCN3, o trae operaciones que el ISA no nombra?

Este es el tercer universo de opcode GFX8. Q5-ISA-CAP12 midio SQ_S_*
(216, escalares) y Q5-MEM-TABLES midio la memoria vectorial (353). El
universo vector SQ_V* no lo midio ninguno de los dos, y VOPC no puede
medirse por nombre porque el ISA lo documenta parametrico (Tablas
12.1/12.2/12.3), no enumerativo. Por eso aqui no se une por nombre: se
extrae la REGLA del ISA y se predice cada entrada del header. Lo que sobra
tras predecir todo es lo que el header tiene y el ISA no nombra.

Solo lectura. Sin GPU, sin sudo, sin PDF nuevo: las dos entradas estan
dentro del root canonico.
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CAP12 = os.path.join(HERE, "..", "Q5-ISA-CAP12", "cap12.txt")
HEADER = os.path.join(
    ROOT, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h"
)

# --- Tabla OP16, Table 12.1, impresa 12-121, extraida literalmente ---
OP16 = {"F": 0, "LT": 1, "EQ": 2, "LE": 3, "GT": 4, "LG": 5, "GE": 6,
        "O": 7, "U": 8, "NGE": 9, "NLG": 10, "NGT": 11, "NLE": 12,
        "NEQ": 13, "NLT": 14, "TRU": 15}
# --- Tabla OP8, Table 12.2, impresa 12-122, extraida literalmente ---
OP8 = {"F": 0, "LT": 1, "EQ": 2, "LE": 3, "GT": 4, "LG": 5, "GE": 6, "TRU": 7}
# --- Familias y su base, Table 12.1 / 12.2 ---
FLOAT_FAMILIES = [("CMP", 0x00), ("CMPX", 0x10), ("CMP", 0x20), ("CMPX", 0x30),
                  ("CMPS", 0x40), ("CMPSX", 0x50), ("CMPS", 0x60), ("CMPSX", 0x70)]
INT_FAMILIES = [("CMP", 0x80), ("CMPX", 0x90), ("CMP", 0xA0), ("CMPX", 0xB0),
                ("CMP", 0xC0), ("CMPX", 0xD0), ("CMP", 0xE0), ("CMPX", 0xF0)]
# --- Table 12.3, impresa 12-123 ---
CLASS = [("CMP", "CLASS", "F32", 0x10), ("CMPX", "CLASS", "F32", 0x11),
         ("CMP", "CLASS", "F64", 0x12), ("CMPX", "CLASS", "F64", 0x13),
         ("CMP", "CLASS", "F16", 0x14), ("CMPX", "CLASS", "F16", 0x15)]

FLOAT_TYPES = {"F32": 0, "F64": 1}
INT_TYPES = {"I32": 2, "I64": 3, "U32": 4, "U64": 5}


def build_rules():
    """Regla del ISA -> nombre canonico V_CMP.. -> opcode."""
    rules = {}
    for fam, base in FLOAT_FAMILIES:
        for op, off in OP16.items():
            t = "F32" if base in (0x00, 0x10, 0x40, 0x50) else "F64"
            rules["V_%s%s_%s" % (fam, op, t)] = (base + off, "12.1", "OP16")
    for fam, base in INT_FAMILIES:
        for op, off in OP8.items():
            t = {0x80: "I32", 0x90: "I32", 0xA0: "I64", 0xB0: "I64",
                 0xC0: "U32", 0xD0: "U32", 0xE0: "U64", 0xF0: "U64"}[base]
            rules["V_%s%s_%s" % (fam, op, t)] = (base + off, "12.2", "OP8")
    for fam, mid, t, val in CLASS:
        rules["V_%s_%s_%s" % (fam, mid, t)] = (val, "12.3", "CLASS")
    return rules


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    for p in (CAP12, HEADER):
        if not os.path.isfile(p):
            sys.stderr.write("MISSING_INPUT %s\n" % p)
            return 2
    print("INPUT cap12.txt     sha256 %s" % sha256(CAP12))
    print("INPUT gfx_8_0_enum.h sha256 %s" % sha256(HEADER))

    # El ISA tiene que DECIR lo que la regla afirma. Se comprueba sobre el
    # texto, no sobre mi memoria: si el PDF no contiene la familia, la regla
    # no se sostiene y el nodo para aqui.
    txt = open(CAP12, errors="replace").read()
    anchors = ["V_CMP_{OP16}_F32", "V_CMPX_{OP16}_F32", "V_CMP_{OP8}_I32",
               "V_CMPX_{OP8}_U64", "V_CMP_CLASS_F32", "V_CMPX_CLASS_F16"]
    missing = [a for a in anchors if a not in txt]
    print("SELFTEST_ANCHORS_ISA %s" % ("PASS" if not missing else "FAIL %s" % missing))
    if missing:
        return 1

    rules = build_rules()
    print("RULES_FROM_ISA %d" % len(rules))

    header = {}
    for line in open(HEADER, errors="replace"):
        if not line.startswith("#define SQ_V_CMP"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        header[parts[1][3:]] = int(parts[2], 16)   # quita "SQ_" -> V_CMP...
    print("UNIVERSE_HEADER_SQ_V_CMP %d" % len(header))

    matched, mismatched, unexplained = [], [], []
    for name in sorted(header):
        hv = header[name]
        if name in rules:
            rv, table, kind = rules[name]
            (matched if rv == hv else mismatched).append((name, hv, rv, table, kind))
        else:
            unexplained.append((name, hv))

    # Reglas del ISA que el header no materializa
    orphan_rules = sorted(n for n in rules if n not in header)

    print("")
    print("PREDICTED_AND_MATCHED     %d" % len(matched))
    print("PREDICTED_BUT_MISMATCH    %d" % len(mismatched))
    print("HEADER_NOT_IN_ISA_RULE    %d" % len(unexplained))
    print("ISA_RULE_NOT_IN_HEADER    %d" % len(orphan_rules))
    total = len(matched) + len(mismatched) + len(unexplained)
    print("CHECK %d + %d + %d = %d  (universo %d)  %s"
          % (len(matched), len(mismatched), len(unexplained), total, len(header),
             "OK" if total == len(header) else "FAIL"))

    print("\n-- VOPC que el header trae y la regla del ISA no explica --")
    bysuffix = {}
    for name, hv in unexplained:
        t = name.rsplit("_", 1)[-1]
        bysuffix.setdefault(t, []).append((name, hv))
    for t in sorted(bysuffix):
        print("  tipo %-4s n=%-4d  ej: %s" % (t, len(bysuffix[t]),
              ", ".join("%s=0x%x" % (n, v) for n, v in bysuffix[t][:3])))

    out = os.path.join(HERE, "vopc-prediction.tsv")
    with open(out, "w") as fh:
        fh.write("isa_name\theader_value\tisa_predicted\tisa_table\tisa_kind\tstate\n")
        for name, hv, rv, table, kind in matched:
            fh.write("%s\t0x%x\t0x%x\t%s\t%s\tCOINCIDE\n" % (name, hv, rv, table, kind))
        for name, hv, rv, table, kind in mismatched:
            fh.write("%s\t0x%x\t0x%x\t%s\t%s\tDIFIERE\n" % (name, hv, rv, table, kind))
        for name, hv in unexplained:
            fh.write("%s\t0x%x\t\t\t\tSIN_REGLA_EN_ISA\n" % (name, hv))
    print("\nOUTPUT %s sha256 %s" % (os.path.basename(out), sha256(out)))

    if mismatched:
        print("\n-- DIFIERE, ambos valores --")
        for name, hv, rv, table, kind in mismatched:
            print("  %-28s header=0x%03X isa=0x%03X (%s %s)" % (name, hv, rv, table, kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())