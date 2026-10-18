#!/usr/bin/env python3
"""AGUA adversarial — fallan primero, luego pasan."""
import os, sys, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rxre.core.agua import Agua

fails = []
n = 0

def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    db = os.path.join(td, "agua.db")
    a = Agua(db)

    # G1 — guardar con procedencia
    lid = a.guardar("hash", "sha256 es estándar", procedencia="finding:F-42")
    v("G1.1 guardar", lid.startswith("lec-"))

    # G1 — recuperar por topic con procedencia
    lecciones = a.recuperar("hash")
    v("G1.2 recuperar con procedencia", len(lecciones) == 1 and lecciones[0]["procedencia"] == "finding:F-42")

    # G2 — revalidación
    a.revalidar(lid)
    lecciones_rev = a.recuperar("hash", revalidar=True)
    v("G2.1 revalidación marca como reciente", lecciones_rev[0]["revalidada"] is True)

    # G3 — recuperar solo del topic pedido
    a.guardar("hash", "sha256", procedencia="x")
    a.guardar("hash", "md5 obsoleto", procedencia="y")
    a.guardar("otro", "irrelevante", procedencia="z")
    lecciones_hash = a.recuperar("hash")
    v("G3.1 solo topic pedido", len(lecciones_hash) == 3 and all(l["topic"] == "hash" for l in lecciones_hash))

print("PASS: %d / %d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
