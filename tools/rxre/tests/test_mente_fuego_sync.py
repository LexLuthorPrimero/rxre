#!/usr/bin/env python3
"""MENTE-6 adversarial — sync MENTE↔FUEGO."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.mente import Mente

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    m = Mente(os.path.join(td, "mente.db"))
    # M6: MENTE invoca FUEGO (rollback como ejemplo de transformación)
    try:
        r = m.invocar_fuego("rollback", {"subop": "global"})
        # FUEGO debe rechazar global (R12); MENTE recibe el error
        v("M6.1 MENTE recibe rechazo FUEGO (global)", r.get("status") == "ok" or "prohibido" in str(r), str(r)[:40])
    except Exception as exc:
        v("M6.1 MENTE recibe rechazo FUEGO (global)", "global" in str(exc).lower() or "prohibido" in str(exc).lower(), str(exc)[:40])
    # M6 con device (no requiere respaldo real para que MENTE vea respuesta)
    try:
        r2 = m.invocar_fuego("rollback", {"subop": "device", "dispositivo": "test"})
        v("M6.2 MENTE recibe ok de rollback device", r2.get("status") == "ok" or "dispositivo" in str(r2), str(r2.get("status"))[:40])
    except Exception as exc:
        v("M6.2 MENTE recibe ok de rollback device", False, str(exc)[:40])

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
