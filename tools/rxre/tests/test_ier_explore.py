#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-108 · EXPLORE — lector público de issues con ranking determinista."""
import os
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from ier import explore  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-50s" % nombre)
    else:
        print("  FAIL %-50s %s" % (nombre, info))
        _fallos.append(nombre)


# 1) ranking determinista con corpus sintético
sample = [
    {"number": 1, "title": "parser segfault on null bytes", "body": "null deref", "labels": [], "state": "open", "htmlUrl": "x", "author": "a"},
    {"number": 2, "title": "feature request: dark mode", "body": "nothing to re", "labels": [], "state": "open", "htmlUrl": "y", "author": "b"},
    {"number": 3, "title": "libc miscompile binary", "body": "reproducer included", "labels": [], "state": "open", "htmlUrl": "z", "author": "c"},
    {"number": 4, "title": "[x]", "body": "x", "labels": [], "state": "open", "htmlUrl": "w", "author": "d"},
]
r = explore.rankear(sample, n=3)
v("ranking por palabras clave", r[0]["puntaje"] >= r[1]["puntaje"] >= r[2]["puntaje"])
v("issues relevantes primero", r[0]["number"] in (1, 3))

# 2) descubrir con gh es opcional y honesto
try:
    rs = explore.descubrir("LexLuthorPrimero/rxre", cantidad=2)
    v("gh discover responde lista", isinstance(rs, list))
except Exception as exc:
    print("  SKIP gh discover (red/gh): %s" % exc)

# 3) corchete_surgimiento con fixture mockeado no existe; validación de campos
#    estructurales invariantes al hacer el ranking
r2 = explore.rankear(sample, n=2)
v("resultado tiene campos obligatorios", all(
    "number" in x and "puntaje" in x and "title" in x for x in r2))

print()
if _fallos:
    print("IER explore FALLA:", _fallos)
    sys.exit(1)
print("IER explore OK")
sys.exit(0)
