#!/usr/bin/env python3
# CONTRACT: name=pm4_layout_audit
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
AUDITORIA CRUZADA: layout documentado  vs  payload realmente emitido.

Idea: el kernel documenta el layout de algunos paquetes con un comentario
numerado que empieza en "/* 1. header" y sigue "2.", "3.", ... El ultimo
numero es el total de dwords del paquete, y el payload es (total - 1).

Eso da una segunda fuente de verdad DENTRO del corpus: no hace falta medir
el hardware ni fiarse de una implementacion externa. Se puede comprobar si
el kernel esta de acuerdo consigo mismo.

Si la regla es  F = payload - 1, entonces para cada layout documentado:

        F emitido  ==  payload documentado - 1

Salida: tabla opcode / doc / F / real / veredicto, y el recuento.
Todo lo no contable se declara, nunca se estima.
"""
import re, sys, glob, os

BASE = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"


def documented_layouts():
    """{opcode: payload_documentado} leyendo los comentarios '/* 1. header'."""
    docs = {}
    where = {}
    for p in glob.glob(f"{BASE}/*.h"):
        lines = open(p, errors="replace").read().split("\n")
        for i, l in enumerate(lines):
            if l.strip() != "/* 1. header":
                continue
            op = None
            for j in range(i - 1, max(0, i - 8), -1):
                m = re.search(r"define\s+(PACKET3_[A-Z0-9_]+)\s+0x", lines[j])
                if m:
                    op = m.group(1)
                    break
            body, k = [], i
            while k < len(lines) and not re.search(r"\*/", lines[k]):
                body.append(lines[k])
                k += 1
            nums = [int(m.group(1)) for m in
                    re.finditer(r"\*\s*(\d+)\.\s", "\n".join(body))]
            if op and nums:
                docs[op] = max(nums) - 1
                where[op] = (os.path.basename(p), i + 1)
    return docs, where


def funcs(src):
    """[(nombre, ini, fin)] de todas las funciones, ignorando prototipos."""
    out, i = [], 0
    while i < len(src):
        l = src[i]
        if re.match(r"^(static\s+)?\w[\w \*]*\s+\**\w+\s*\(", l) and not l.rstrip().endswith(";"):
            m = re.match(r"^(?:static\s+)?[\w \*]*?\**(\w+)\s*\(", l)
            name = m.group(1) if m else "?"
            j = i
            while "{" not in src[j] and j < len(src) - 1:
                j += 1
            if "{" not in src[j]:
                i += 1
                continue
            d = 0
            for k in range(j, len(src)):
                d += src[k].count("{") - src[k].count("}")
                if d == 0:
                    out.append((name, i, k))
                    i = k
                    break
            else:
                break
        i += 1
    return out


def count_emissions(files):
    rows, unknown = [], []
    for f in sorted(files):
        src = open(f, errors="replace").read().split("\n")
        for name, lo, hi in funcs(src):
            body = src[lo:hi + 1]
            for idx, l in enumerate(body):
                m = re.search(r"PACKET3\(\s*(PACKET3_[A-Z0-9_]+)\s*,\s*(\d+)\s*\)", l)
                if not m:
                    continue
                op, F = m.group(1), int(m.group(2))
                cnt, unk = 0, False
                for nxt in body[idx + 1:]:
                    if re.search(r"PACKET3\(|PACKET0\(", nxt):
                        break
                    if "amdgpu_ring_write" in nxt:
                        cnt += 1
                        continue
                    if re.search(r"\b(if|else|for|while|switch)\b", nxt):
                        unk = True
                        break
                row = dict(file=os.path.basename(f), func=name,
                           line=lo + idx + 1, op=op, F=F, real=cnt,
                           unknown=unk)
                (unknown if unk else rows).append(row)
    return rows, unknown


def main():
    only = None
    for a in sys.argv:
        if a.startswith("--only="):
            only = a.split("=", 1)[1]
    if only:
        files = [f for f in sorted(glob.glob(f"{BASE}/*.c"))
                 if only in os.path.basename(f)]
    else:
        files = sorted(glob.glob(f"{BASE}/*.c"))

    docs, where = documented_layouts()
    if not docs:
        sys.exit("NO_LAYOUTS_FOUND -- el parser del layout esta roto")

    rows, unknown = count_emissions(files)
    checkable = [r for r in rows if r["op"] in docs]

    print("=" * 74)
    print("AUDITORIA CRUZADA: layout documentado vs payload emitido")
    print("=" * 74)
    print(f"layouts documentados en el corpus : {len(docs)}")
    print(f"emisiones con layout documentado  : {len(checkable)}")
    print()
    hdr = f"{'opcode':30} {'doc':>4} {'F':>4} {'real':>5} {'esperado':>9}  veredicto"
    print(hdr)
    print("-" * len(hdr))
    ok = bad = 0
    for r in checkable:
        exp = docs[r["op"]] - 1
        good = r["F"] == exp and r["F"] == r["real"] - 1
        ok, bad = (ok + 1, bad) if good else (ok, bad + 1)
        v = "OK" if good else "*** DISCREPA ***"
        print(f"{r['op']:30} {docs[r['op']]:4} {r['F']:4} "
              f"{r['real']:5} {exp:9}  {v}")

    print("-" * len(hdr))
    print(f"conformes   : {ok}")
    print(f"discrepantes: {bad}")
    print()
    print("Los no contables (rama/loop entre cabecera y fin) se declaran:")
    seen = set()
    for r in unknown:
        if r["op"] in docs and r["op"] not in seen:
            seen.add(r["op"])
    print("  " + (", ".join(sorted(seen)) if seen else "(ninguno)"))
    print()
    if bad == 0:
        print("VEREDICTO: el corpus esta de acuerdo consigo mismo.")
        print("  Para todo paquete con layout documentado:")
        print("      F emitido == payload documentado - 1")
        print("      F emitido == payload realmente escrito - 1")
        print("  Es decir: el kernel DOCUMENTA y USA la misma regla.")
        print("  Esto confirma F = datos - 1 sin apelar a fuentes externas")
        print("  ni a medicion de hardware. Fuentes de verdad independientes: 2")
        print("  (el comentario del layout y el codigo de emision).")
    else:
        print("VEREDICTO: hay discrepancias. No cerrar la convencion; investigarlas.")
        for r in checkable:
            if r["F"] != docs[r["op"]] - 1 or r["F"] != r["real"] - 1:
                print(f"  {r['file']}:{r['line']} {r['func']} {r['op']} "
                      f"F={r['F']} real={r['real']} doc={docs[r['op']]}")


if __name__ == "__main__":
    main()