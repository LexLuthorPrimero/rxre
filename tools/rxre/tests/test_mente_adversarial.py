#!/usr/bin/env python3
"""MENTE adversarial — M1, M2, M4."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.mente import Mente, PASOS

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    m = Mente(os.path.join(td, "mente.db"))
    hips = m.proponer_hipotesis({"fenomeno": "F_01"})
    v("M1.1 >=2 rivales", len(hips) >= 2)
    v("M1.2 predicciones distintas", hips[0].predicciones != hips[1].predicciones)
    v("M1.3 falsificador presente", bool(hips[0].falsificador) and bool(hips[1].falsificador))
    p = m.disenar_prueba(hips[0].id, hips[1].id)
    v("M2.1 prueba creada", p.id.startswith("pr-"))
    v("M2.2 predicciones distintas", p.prediccion_a != p.prediccion_b)
    r = m.evaluar_prueba(p.id, {"observado": p.prediccion_a})
    v("M4.1 falsificador funciona", r["ok"] and r.get("refutada") == hips[1].id)

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
