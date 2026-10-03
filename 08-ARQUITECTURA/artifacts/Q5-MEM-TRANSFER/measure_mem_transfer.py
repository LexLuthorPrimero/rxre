#!/usr/bin/env python3
"""
Q5-MEM-TRANSFER — ¿alguna tabla de opcode de memoria del ISA GCN3 es
trasladable a gfx803 por valor?

Q5-MEM-TABLES midio COBERTURA por nombre y halló 45 discrepancias, 35 en FLAT y
10 en MIMG. Q5-VOP-VEC mostro que en VOPC la diferencia no era de valores sueltos
sino de reparto de bloques. Aqui se pregunta lo mismo para las cinco familias de
memoria: ¿el desplazamiento entre header GFX8 e ISA GCN3 es un delta constante
por grupo (trasladable con una correccion) o un reordenamiento (no trasladable)?

Criterio de veredicto por familia:
  TRASLADABLE   todos los deltas constantes por grupo y ninguna permutacion
  REORDENADA    existe permutacion: dos instrucciones intercambian su valor
  MIXTA         ambas cosas a la vez

NIVEL 0/1. Solo lectura. Sin GPU, sin sudo.
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP12 = os.path.join(HERE, "..", "Q5-ISA-CAP12", "cap12.txt")
HEADER = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
          "linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h")

# prefijo_header, prefijo_isa, tabla, (paginas logicas 0-based en cap12.txt)
FAMILIES = [
    ("SQ_DS_",     "DS_",      "12.7",  (160, 161, 162, 163, 164, 165)),
    ("SQ_BUFFER_", "BUFFER_",  "12.8",  (166, 167, 168)),
    ("SQ_TBUFFER_", "TBUFFER_", "12.9",  (169, 170)),
    ("SQ_IMAGE_",  "IMAGE_",   "12.12", (171, 172, 173, 174)),
    ("SQ_FLAT_",   "FLAT_",    "12.13", (176, 177)),
]

# La fila del PDF empieza en la columna 0, NO con sangria, y el valor aparece
   # como "00 (0x0)". Q5-ISA-CAP12 §2 registro ademas que el PDF escribe a veces
   # "(0x 30)" con espacio y "(C)" sin prefijo; por eso el hex se tolera.
   # La familia se filtra por prefijo, no por sangria: exigir sangria excluyo las
   # cinco tablas y produjo isa=0, que es como un fallo de parser se disfraza
   # de "no hay discrepancias". MIN_ROWS lo hace imposible de nuevo.
ROW = re.compile(r"^\s*([A-Z][A-Z0-9_]{3,})\s+\S.*?\(\s*0x\s*([0-9A-Fa-f]+)\s*\)\s*$")
MIN_ROWS = 8   # por familia; por debajo, el parser ha fallado


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_header():
    pref = {}
    for line in open(HEADER, errors="replace"):
        m = re.match(r"#define (SQ_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+)", line)
        if m:
            pref[m.group(1)] = int(m.group(2), 16)
    return pref


def main():
    for p in (CAP12, HEADER):
        if not os.path.isfile(p):
            sys.stderr.write("MISSING_INPUT %s\n" % p)
            return 2
    print("INPUT cap12.txt      sha256 %s" % sha256(CAP12))
    print("INPUT gfx_8_0_enum.h sha256 %s" % sha256(HEADER))

    pages = open(CAP12, errors="replace").read().split("\f")
    pref = load_header()

    out = open(os.path.join(HERE, "mem-transfer.tsv"), "w")
    out.write("familia\ttabla\tinstruccion\theader_gfx8\tisa_gcn3\tdelta\testado\n")

    verdict = {}
    for hp, ip, tabla, rng in FAMILIES:
        isa = {}
        for i in rng:
            if i >= len(pages):
                sys.stderr.write("PAGE_OOB %d\n" % i)
                return 1
            for line in pages[i].split("\n"):
                m = ROW.match(line)
                if m and m.group(1).startswith(ip):
                    isa.setdefault(m.group(1), int(m.group(2), 16))
        if len(isa) < MIN_ROWS:
            sys.stderr.write("SELFTEST_FAIL tabla %s: %d filas < MIN_ROWS %d "
                             "-> parser, NO medicion\n" % (tabla, len(isa), MIN_ROWS))
            return 1
        hdr = {k[len("SQ_"):]: v for k, v in pref.items() if k.startswith(hp)}

        com = sorted(k for k in hdr if k in isa)
        pairs = [(k, hdr[k], isa[k]) for k in com]
        diffs = [(k, h, s, h - s) for k, h, s in pairs if h != s]

        # permutacion: existe instruccion A cuyo valor en el header es el que el
        # ISA asigna a otra instruccion B. Eso invalida una simple correccion.
        isav = {}
        for k, h, s in pairs:
            isav.setdefault(h, []).append(k)
        perm = [(k, h, isav[h][0]) for k, h, s, d in diffs
                if h in isav and isav[h][0] != k]

        deltas = sorted({d for _, _, _, d in diffs})
        if not diffs:
            v = "TRASLADABLE"
        elif perm:
            v = "REORDENADA" if len(deltas) > 1 else "REORDENADA"
        else:
            v = "DESPLAZAMIENTO_UNIFORME"
        verdict[tabla] = (v, len(hdr), len(isa), len(com), len(diffs), len(perm),
                          hdr, isa, com, diffs, perm, deltas)

        for k in sorted(hdr):
            if k in isa:
                d = hdr[k] - isa[k]
                out.write("%s\t%s\t%s\t0x%X\t0x%X\t%+d\t%s\n"
                          % (tabla, tabla, k, hdr[k], isa[k], d,
                             "COINCIDE" if d == 0 else "DIFIERE"))
            else:
                out.write("%s\t%s\t%s\t0x%X\t\t\tSIN_FILA_EN_ISA\n"
                          % (tabla, tabla, k, hdr[k]))
    out.close()

    print("")
    print("%-7s %-24s %6s %5s %5s %6s %6s" %
          ("tabla", "veredicto", "hdr", "isa", "com", "diff", "perm"))
    for tabla, (v, nh, ni, nc, nd, np_, *_) in verdict.items():
        print("%-7s %-24s %6d %5d %5d %6d %6d"
              % (tabla, v, nh, ni, nc, nd, np_))

    for tabla, (v, nh, ni, nc, nd, np_, hdr, isa, com, diffs, perm, deltas) in verdict.items():
        if perm:
            print("\n-- %s: PERMUTACION (header toma el valor que el ISA da a otra) --" % tabla)
            for k, h, other in perm[:8]:
                print("   %-24s header=0x%X  ese valor en el ISA es de %s" % (k, h, other))
            if len(perm) > 8:
                print("   ... (%d mas)" % (len(perm) - 8))
        if len(deltas) > 1:
            print("   deltas distintos en %s: %s" % (tabla, deltas[:12]))
    print("\nOUTPUT mem-transfer.tsv sha256 %s"
          % sha256(os.path.join(HERE, "mem-transfer.tsv")))
    return 0


if __name__ == "__main__":
    sys.exit(main())