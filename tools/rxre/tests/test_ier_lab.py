#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-105 · LAB — sesión aislada donde la fuente no cambia jamás."""
import os
import sys
import json
import hashlib
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from ier import lab  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-46s" % nombre)
    else:
        print("  FAIL %-46s %s" % (nombre, info))
        _fallos.append(nombre)


tmp_src = tempfile.mkdtemp(prefix="ier_src_")
src_file = os.path.join(tmp_src, "mod.py")
with open(src_file, "w") as f:
    f.write("VALUE = 'OK'\n")

s = lab.RepairSession(tmp_src)
orig_content = open(src_file).read()

# 1) aplicar mutacion en workdir temporal; fuente intacta
work = s.en_tmp("r")
work2 = os.path.join(work, "tree")
os.makedirs(work2)
s.aplicar(work2, {"ruta": "mod.py", "buscar": "OK", "cambio": "MUTADO"})
v("fuente tras aplicar mutacion intacta",
  open(src_file).read() == orig_content)
m = open(os.path.join(work2, "mod.py")).read()
v("workdir contiene la mutacion", "MUTADO" in m)

# 2) ejecutar probe con exito/fracaso
r = s.ejecutar_probe(work2, ["python3", "-c",
                              "import sys;sys.exit(0 if 'MUTADO' in open('mod.py').read() else 1)"])
v("probe ejecutada con rc=0", r.get("rc") == 0)
r2 = s.ejecutar_probe(work2, ["python3-no-existe-xyz", "--help"])
v("probe no ejecutable => error", r2.get("status") == "error")

# 3) verificacion de integridad fuente
rep = s.reporte_integridad(work2)
v("fuente intacta reportada", rep["fuente_intacta"] is True)

# 4) fingerprint determinista
rep2 = s.reporte_integridad(work2)
v("fingerprint estable",
  rep2["fingerprint_workdir"] == rep["fingerprint_workdir"])

# 5) ref escrito a la raiz -> no se toca
rep3 = s.reporte_integridad(tmp_src)
v("mismo fingerprint de fuente", rep3["fingerprint_workdir"] == rep3["fingerprint_fuente"])

print()
if _fallos:
    print("IER lab FALLA:", _fallos)
    sys.exit(1)
print("IER lab OK")
sys.exit(0)
