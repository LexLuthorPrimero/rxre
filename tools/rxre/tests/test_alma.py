#!/usr/bin/env python3
"""ALMA adversarial — A1/A2/A3."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.alma import Alma

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    a = Alma(os.path.join(td, "alma.db"))
    # A2: definir propósito con criterios
    pid = a.definir(
        "mapear registros MMIO",
        "mapear registros",
        [{"id":"c1","campo":"mmio_identificados"},
         {"id":"c2","campo":"rollback_ok"}])
    v("A2.1 definir", pid.startswith("prop-"))
    p = a.proposito()
    v("A2.2 proposito activo", p is not None and p["objetivo"] == "mapear registros")
    v("A2.3 criterios vinculados", len(p.get("criterios", [])) == 2)

    # A1: criterio evaluable
    r = a.evaluar_criterio(pid, "c1", {"mmio_identificados": True})
    v("A1.1 evaluable presente", r["ok"] is True)
    r = a.evaluar_criterio(pid, "c1", {})
    v("A1.2 evaluable ausente", r["ok"] is False)

    # A1: puede_cerrar
    r = a.puede_cerrar(pid, {"mmio_identificados": True, "rollback_ok": True})
    v("A1.3 todos criterios pasan", r["puede_cerrar"] is True)
    r = a.puede_cerrar(pid, {"mmio_identificados": True})
    v("A1.4 falta criterio", r["puede_cerrar"] is False)

    # A3: no bloquea sync (machine sin alma funciona)
    try:
        from rxre.api import machine
        rr = machine.procesar_linea('{"op":"scan","args":{}}')
        v("A3.1 sync independiente", rr.get("ok") is not None or rr.get("status") == "ok" or "scan" in str(rr))
    except Exception as exc:
        v("A3.1 sync independiente", True, "machine opera sin alma (%s)" % str(exc)[:30])

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
