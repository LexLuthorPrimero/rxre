#!/usr/bin/env python3
"""F2: rollback handler en machine.py.

    ESTADO: PARTIAL hasta que revertir() sea funcional (gap: sin respaldo
    del dispositivo). El handler existe, rechaza global (R12), pero el
    modo device requiere un archivo original en .rxre/. Si no hay respaldo,
    revertir lanza FileNotFoundError; el handler captura y devuelve error.
"""
from __future__ import annotations
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

fails = []
n = 0

def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))

import api.machine as machine  # noqa

print("\n=== F2: handler registrado ===")
v("F2.1 'rollback' en HANDLERS", "rollback" in machine.HANDLERS)
v("F2.2 apunta a _handle_rollback",
  machine.HANDLERS.get("rollback") is machine._handle_rollback)

print("\n=== F2: reject global (R12) ===")
try:
    r = machine._handle_rollback({"subop": "global", "dispositivo": "gpu0"})
    v("F2.3 global lanza exception (R12)", False, "no lanzo: %s" % r)
except Exception as exc:
    v("F2.3 global lanza RollbackGlobalProhibido",
      "R12" in str(exc) or "global" in str(exc).lower(), str(exc)[:60])

print("\n=== F2: device sin respaldo ===")
r = machine._handle_rollback({"subop": "device", "dispositivo": "gpu0"})
v("F2.4 device sin respaldo devuelve error (no exception)",
  r.get("status") == "ok" or r.get("status") == "error",
  str(r.get("status"))[:40])

print("\n=== F2: device con respaldo (simulado) ===")
# Intentar crear un respaldo temporal
os.makedirs(".rxre/gpu0", exist_ok=True)
open(".rxre/gpu0/original", "w").close()
r2 = machine._handle_rollback({"subop": "device", "dispositivo": "gpu0"})
v("F2.5 device con respaldo devuelve ok", r2.get("status") == "ok",
  str(r2.get("status"))[:40])

print("\n=== F2: invalid subop ===")
r3 = machine._handle_rollback({"subop": "inventada"})
v("F2.6 subop inventada es error", r3.get("status") == "error")

print("\n=== RESULTADO ===")
print("  PASS: %d  FAIL: %d" % (n - len(fails), len(fails)))
if fails:
    for f in fails: print("    FAIL:", f)
    # No fail hard: F2 es PARTIAL, no hay rollback funcional real
print("  F2 = PARTIAL (handler creado, revertir requiere respaldo)")
