#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-107 · EVOLVE — Triple Condición: corrección, no-regresión, compatibilidad."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from ier import evolve  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-50s" % nombre)
    else:
        print("  FAIL %-50s %s" % (nombre, info))
        _fallos.append(nombre)


cap = {
    "evidencia": [
        {"criterion": "RESOLVES", "name": "determinism", "result": "PASS"},
        {"criterion": "REPRODUCTION", "name": "hermetic",  "result": "PASS"},
    ],
    "regression": {"baseline_verde": True,
                   "fuente": "clon fresco rc=0"},
    "compatibility": {"presente": True, "cli_557": True, "summary": True},
}

# 1) sin dictado => propuesta pendiente
r = evolve.evaluacion_triple_condicion(cap, None)
v("sin dictado -> PENDIENTE_DICTADO", r["veredicto"] == "PENDIENTE_DICTADO")

# 2) dictado del propietario => PROMOTED
r = evolve.evaluacion_triple_condicion(cap, "dictado propietario")
v("dictado -> PROMOTED", r["veredicto"] == "PROMOTED")

# 3) dictado distinto (no propietario) => no promociona
r = evolve.evaluacion_triple_condicion(cap, "dictado asistente")
v("dictado distinto -> PENDIENTE_DICTADO (no PROMOTED)", r["veredicto"] == "PENDIENTE_DICTADO")

# 4) regresion => RECHAZO_POR_INSUFICIENTE
cap_bad = dict(cap)
cap_bad["regression"] = {"baseline_verde": False}
r = evolve.evaluacion_triple_condicion(cap_bad, "dictado propietario")
v("regresión -> RECHAZO", r["veredicto"] == "RECHAZO_POR_INSUFICIENTE")

# 5) sin evidencias => RECHAZO
cap_empty = dict(cap)
cap_empty["evidencia"] = []
r = evolve.evaluacion_triple_condicion(cap_empty, "dictado propietario")
v("sin evidencias -> RECHAZO", r["veredicto"] == "RECHAZO_POR_INSUFICIENTE")

# 6) resumen no silencia nada
txt = evolve.resumen_reporte(cap, "dictado propietario")
v("resumen contiene 'PROMOTED'", "PROMOTED" in txt)

print()
if _fallos:
    print("IER evolve FALLA:", _fallos)
    sys.exit(1)
print("IER evolve OK")
sys.exit(0)
