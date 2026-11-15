#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-102 · CAPABILITY lifecycle — declarar, verificar, no promocionar sin evidencia.

Criterios por plan E2:
  - DECLARED -> EXECUTED -> VERIFIED: solo mediante verificaciones en disco.
  - PROMOTED exige dictado del propietario: rechazo duro en este paquete.
  - Criterios 5 verificados uno a uno.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_cap_")

from ier import capability  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-44s" % nombre)
    else:
        print("  FAIL %-44s %s" % (nombre, info))
        _fallos.append(nombre)


tmp = tempfile.mkdtemp(prefix="ier_cap_art_")
linea = os.path.join(tmp, "decibelia.c")
with open(linea, "w") as f:
    f.write("int main(){return 0;}\n")

cap = capability.declarar(
    name="cap_test_decision_lookup",
    purpose="lookup determinista para pruebas",
    domain="re/testing",
    ruta=linea,
    version="0.1.0",
    limitations=["sin concurrencia"],
    source_mission_id="mis_test")
v("DECLARED inicial", cap["status"] == "DECLARED")
v("5 criterios NOT_EXECUTED", all(
    cap["verifications"][c]["status"] == "NOT_EXECUTED"
    for c in capability.CRITERIA))
v("identity hash no vacío", bool(cap["execution"]["artifact_sha256"]))

cap2 = capability.transitar(cap["capability_id"], "EXECUTED", "smoke")
v("transicion EXECUTED", cap2["status"] == "EXECUTED")

cap3 = capability.registrar_verificacion(cap["capability_id"], "RESOLVES", "PASS",
                                          ["ev_test_1"], "caso canónico")
v("criterio 1 registrado", cap3["verifications"]["RESOLVES"]["status"] == "PASS")

try:
    capability.transitar(cap["capability_id"], "PROMOTED", "auto")
    v("PROMOTED rechazado sin dictado", False)
except PermissionError:
    v("PROMOTED rechazado sin dictado", True)

cap4 = capability.transitar(cap["capability_id"], "VERIFIED", "tras criterios")
v("VERIFIED alcanzado", cap4["status"] == "VERIFIED")

r = capability.resumen_verificacion(cap["capability_id"])
v("summary expone el estatus Criteria", r["criteria"]["RESOLVES"] == "PASS")

# promote forbidden remains even with all tests green
try:
    capability.transitar(cap["capability_id"], "PROMOTED", "dictado ajeno")
    v("PROMOTED sigue rechazado tras criterios completos", False)
except PermissionError:
    v("PROMOTED sigue rechazado tras criterios completos", True)

print()
if _fallos:
    print("IER capability lifecycle FALLA:", _fallos)
    sys.exit(1)
print("IER capability lifecycle OK")
sys.exit(0)
