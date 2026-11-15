#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-109 · UPSTREAM — paquete listo para revisión, jamás autoenviado."""
import os
import sys
import json
import hashlib
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from ier import upstream  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-50s" % nombre)
    else:
        print("  FAIL %-50s %s" % (nombre, info))
        _fallos.append(nombre)


tmp = tempfile.mkdtemp(prefix="ier_up_")
patch = os.path.join(tmp, "p.patch")
with open(patch, "w") as f:
    f.write("--- a/x\n+++ b/x\n@@\n-a\n+b\n")

# 1) construir paquete con evidencia
pkg = upstream.construir(
    mission_id="mis_test",
    target_repo="target/lib",
    probable_upstream="lib/upstream#123",
    patch_file=patch,
    evidencia=[{"name": "fix_verificado", "result": "PASS"}],
    alcance="El fix afecta solo a la función X, no al ABI ni al ABI",
    limitaciones=["dominio X86_64 únicamente"],
    path=os.path.join(tmp, "pkg.json"))
v("paquete generado", bool(pkg))

# 2) verificar el paquete generado
r = upstream.verificar_pkg(os.path.join(tmp, "pkg.json"))
v("paquete integro", r["integridad_ok"])

# 3) reporte no anuncia envio: LISTO para el propietario, nunca autoenviado
txt = upstream.reporte_revision(os.path.join(tmp, "pkg.json"))
v("reporte anterior al cambio de patch: LISTO", txt.startswith("LISTO"))

# 3) paquete sin evidencia rechazado
pkg2 = upstream.construir(
    mission_id="mis_test", target_repo="target/lib", probable_upstream="lib#124",
    patch_file=patch, evidencia=[], alcance="x", limitaciones=[],
    path=os.path.join(tmp, "pkg2.json"))
r2 = upstream.verificar_pkg(os.path.join(tmp, "pkg2.json"))
v("paquete sin evidencia rechazado", not r2["integridad_ok"])

# 4) patch contenido cambiado => sha no coincide
with open(patch, "w") as f:
    f.write("changed")
r3 = upstream.verificar_pkg(os.path.join(tmp, "pkg.json"))
v("patch alterado rechazado", not r3["integridad_ok"])



print()
if _fallos:
    print("IER upstream FALLA:", _fallos)
    sys.exit(1)
print("IER upstream OK")
sys.exit(0)
