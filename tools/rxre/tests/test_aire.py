#!/usr/bin/env python3
"""AIRE adversarial — fallan primero."""
import os, tempfile, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rxre.core.aire import Aire

fails = []
n = 0

def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    db = os.path.join(td, "aire.db")
    a = Aire(db)

    # Ai1 — traza reconstruible
    tid = a.trazar("decidir scan", "rz_functions")
    a.resultado(tid, resultado="3 funciones")
    trace = a.reconstruir(tid)
    v("Ai1.1 traza reconstruible", trace is not None)
    v("Ai1.2 decision preservado", trace.get("decision") == "decidir scan")
    v("Ai1.3 resultado preservado", trace.get("resultado") == "3 funciones")

    # Ai2 — 3 tramos
    tid2 = a.trazar("decidir", "herramienta")
    a.resultado(tid2, resultado="ok")
    trace2 = a.reconstruir(tid2)
    v("Ai2.1 decision", bool(trace2.get("decision")))
    v("Ai2.2 herramienta", bool(trace2.get("herramienta")))
    v("Ai2.3 resultado", bool(trace2.get("resultado")))

    # Ai3 — falla trazada
    tid3 = a.trazar("decidir", "herramienta")
    a.resultado(tid3, error="falló X")
    trace3 = a.reconstruir(tid3)
    v("Ai3.1 error trazado", trace3.get("error") == "falló X")

    # Ai3 — reconstrucción por último
    last = a.reconstruir()
    v("Ai3.2 reconstruir sin args devuelve último", last is not None)

print("PASS: %d / %d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
