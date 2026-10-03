#!/usr/bin/env python3
"""Reconstruye la lista de las 26 funciones (via AST de clang) y da el span
verificable de cada una, con el nombre exacto.

El agrupamiento (26) es el de contract.crossblock(): en los ficheros de la
"ruta VI" (BLOQUES), cada funcion que escribe >1 registro distinto, sin
mutex_lock(&adev->...) dentro, y cuyo nombre NO casa con RE_INITFN.

El SPAN se resuelve por AST, y se exige ademas que:
  - el nombre empiece por el prefijo del fichero (gfx_v8_0_*, gmc_v8_0_*...),
    porque la atribucion de fichero por el "file" del JSON de clang no es
    fiable (ver astext.src);
  - la linea caiga dentro del fichero.
Se imprime la cabecera de cada span para que se pueda leer y verificar.
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, "/var/tmp/rx550/kit")
import contract as C          # noqa: E402  (RE_MUTEX, RE_INITFN, BLOQUES, regctx)
import funcspan as FS         # noqa: E402

AMD = C._AMD
FILES = ["gfx_v8_0.c", "gmc_v8_0.c", "sdma_v3_0.c", "gfxhub_v2_1.c"]
AST = "/var/tmp/rx550/agents/ast"


def prefix(f):
    return f[:-2]


def idx(fname):
    d = json.load(open(os.path.join(AST, prefix(fname) + ".idx.json")))
    src = open(os.path.join(AMD, "amdgpu", fname),
               encoding="utf-8", errors="replace").read().splitlines()
    return d, src


def fn_at(d, src, line):
    """La funcion de d que contiene `line` (la mas pequena)."""
    cand = [f for f in d["functions"] if f["start"] and f["start"] <= line]
    if not cand:
        return None
    f = max(cand, key=lambda x: x["start"])
    if f["end"] and line > f["end"]:
        return None
    if not (f["name"] or "").startswith(prefix(fname_of(d))):
        return None
    return f


def fname_of(d):
    return os.path.basename(d["file"])


def main():
    # 1. reescrituras W de la ruta, tal y como las cuenta contract.py
    todos = C.regctx.scan(C._CORPUS)[1]
    por_fn = collections.defaultdict(set)
    for a in todos:
        if "offset" not in a or not a["via"].startswith("W"):
            continue
        if not C.BLOQUES.get(a["fichero"]):
            continue
        f, ln = a["fichero"], a["linea"]
        try:
            st, en, meth = FS.of_line(os.path.join(AMD, "amdgpu", f), ln)
        except OSError:
            continue
        if st is None:
            continue
        por_fn[(f, st, en, meth)].add(a["reg"])

    rows = []
    for (f, st, en, meth), regs in por_fn.items():
        if len(regs) <= 1:
            continue
        src = open(os.path.join(AMD, "amdgpu", f),
                   encoding="utf-8", errors="replace").read().splitlines()
        cab = src[st - 1].strip()
        mutex = sorted({m.group(1) for i in range(st - 1, min(en, len(src)))
                        for m in C.RE_MUTEX.finditer(src[i])})
        rows.append(dict(f=f, st=st, en=en, meth=meth, nreg=len(regs),
                         mutex=mutex, init=bool(C.RE_INITFN.search(cab)),
                         regs=sorted(regs), cab=cab))
    rows.sort(key=lambda r: (r["f"], r["st"]))

    # 2. Span por AST y nombre exacto
    idxs = {f: idx(f) for f in FILES}
    for r in rows:
        d, src = idxs[r["f"]]
        cand = [x for x in d["functions"]
                if x["start"] and x["start"] <= r["st"]
                and (x["end"] or 10 ** 9) >= r["en"]
                and (x["name"] or "").startswith(prefix(r["f"]) + "_")]
        if cand:
            x = min(cand, key=lambda y: (y["end"] or 0) - (y["start"] or 0))
            r["name"] = x["name"]
            r["ast_start"], r["ast_end"] = x["start"], x["end"]
            r["static"] = x["static"]
            r["type"] = x["type"]
        else:
            r["name"] = None
            r["ast_start"] = r["ast_end"] = None
            r["static"] = None
            r["type"] = None
        r["head"] = src[r["st"] - 1].strip()[:150]

    json.dump(rows, open("/var/tmp/rx550/agents/f26.json", "w"), indent=1)
    n_mul = len(rows)
    n_rt = sum(1 for r in rows if not r["mutex"] and not r["init"])
    print("funciones multi-registro: %d | con mutex: %d | init sin mutex: %d "
          "| RUNTIME sin mutex: %d"
          % (n_mul, sum(1 for r in rows if r["mutex"]),
             sum(1 for r in rows if not r["mutex"] and r["init"]), n_rt))
    print()
    for r in rows:
        if r["mutex"] or r["init"]:
            continue
        print("%-14s %5d-%-5d %-46s nreg=%-2d static=%-5s"
              % (r["f"], r["st"], r["en"], r["name"], r["nreg"], r["static"]))
        print("      %s" % r["type"])
        print("      regs: %s" % ", ".join(r["regs"][:6]))
    sin_nombre = [r for r in rows
                  if not r["mutex"] and not r["init"] and not r["name"]]
    if sin_nombre:
        print("\nSIN NOMBRE RESUELTO POR AST (%d):" % len(sin_nombre))
        for r in sin_nombre:
            print("  %s:%d-%d  metodo=%s  cab=%s"
                  % (r["f"], r["st"], r["en"], r["meth"], r["cab"]))


if __name__ == "__main__":
    main()