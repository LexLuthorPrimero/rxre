#!/usr/bin/env python3
"""DISCIPLINA adversarial — D1, D2, D3."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.disciplina import Disciplina, PASOS

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    d = Disciplina(os.path.join(td, "disc.db"))

    # D1 — orden completo
    iid = d.iniciar("test causalidad")
    for paso in PASOS[1:]:
        d.avanzar(iid, paso)
    v("D1.1 orden completo", d.estado(iid)["paso_actual"] == "VALIDATION")

    # D2 — salto detectado
    iid2 = d.iniciar("test salto")
    try:
        d.avanzar(iid2, "IMPLEMENTATION")
        v("D2.1 salto detectado", False, "no abortó")
    except ValueError as e:
        v("D2.1 salto detectado", "SALTO" in str(e))
    estado = d.estado(iid2)
    v("D2.2 abortado", estado["aborted_at"] is not None)
    v("D2.3 razón incluye 'saltó'", "saltó" in (estado["abort_reason"] or ""))

    # D3 — reconstrucción
    h = d.historial(iid)
    v("D3.1 historial reconstruible", len(h) == 5)
    v("D3.2 primer paso EVIDENCE", h[0]["desde"] == "EVIDENCE")
    v("D3.3 último paso VALIDATION", h[-1]["hacia"] == "VALIDATION")

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
