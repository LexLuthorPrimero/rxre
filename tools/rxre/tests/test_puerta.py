#!/usr/bin/env python3
"""PUERTA adversarial — P2-P7."""
import sys, os, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from rxre.core.puerta import Puerta

fails = []
n = 0
def v(nombre, cond, det=""):
    global n, fails
    n += 1
    if not cond: fails.append(nombre + (" <- %s" % det if det else ""))
    print("  %s %s" % ("PASS" if cond else "FAIL", nombre))

with tempfile.TemporaryDirectory() as td:
    p = Puerta(os.path.join(td, "puerta.db"))

    # P2: CONTESTED → CHALLENGED requiere evidencia nueva
    p.transicionar("CONTESTED", "audit rechazado")
    try:
        p.transicionar("CHALLENGED", "revisión")
        v("P2.1 sin evidencia debe fallar", False, "no falló")
    except ValueError:
        v("P2.1 sin evidencia debe fallar", True)
    # Con evidencia pasa
    r = p.transicionar("CHALLENGED", "revisión", evidencia_nueva="test-42")
    v("P2.2 con evidencia pasa", r.get("ok") is True)

    # P3-P6: ACCEPTED requiere 4 condiciones
    with tempfile.TemporaryDirectory() as td2:
        pp = Puerta(os.path.join(td2, "puerta.db"))
        try:
            pp.transicionar("ACCEPTED", "aceptar")
            v("P3.1 sin condiciones debe fallar", False, "no falló")
        except ValueError:
            v("P3.1 sin condiciones debe fallar", True)
        pp.marcar("artefactos_integros", True)
        pp.marcar("revisor_independiente", True)
        pp.marcar("autoridad_nombrada", True)
        pp.marcar("refutaciones_pendientes", False)
        pp.transicionar("CHALLENGED", "revisión")
        rr = pp.transicionar("ACCEPTED", "aceptar")
        v("P3-P6.2 con 4 condiciones pasa", rr.get("ok") is True)

    # P4: refutaciones_cero (refutaciones_pendientes=False)
    with tempfile.TemporaryDirectory() as td3:
        pp = Puerta(os.path.join(td3, "puerta.db"))
        pp.marcar("artefactos_integros", True)
        pp.marcar("revisor_independiente", True)
        pp.marcar("autoridad_nombrada", True)
        pp.transicionar("CHALLENGED", "revisión")
        # Dejar refutaciones en 1 (True) → debe fallar ACCEPTED
        pp.marcar("refutaciones_pendientes", True)
        try:
            pp.transicionar("ACCEPTED", "aceptar")
            v("P4.1 con refutaciones debe fallar", False, "no falló")
        except ValueError:
            v("P4.1 con refutaciones debe fallar", True)

    # P5: revisor independiente
    with tempfile.TemporaryDirectory() as td4:
        pp = Puerta(os.path.join(td4, "puerta.db"))
        pp.marcar("artefactos_integros", True)
        pp.marcar("autoridad_nombrada", True)
        pp.marcar("refutaciones_pendientes", False)
        pp.transicionar("CHALLENGED", "revisión")
        try:
            pp.transicionar("ACCEPTED", "aceptar")
            v("P5.1 sin revisor debe fallar", False, "no falló")
        except ValueError:
            v("P5.1 sin revisor debe fallar", True)

    # P6: autoridad nombrada
    with tempfile.TemporaryDirectory() as td5:
        pp = Puerta(os.path.join(td5, "puerta.db"))
        pp.marcar("artefactos_integros", True)
        pp.marcar("revisor_independiente", True)
        pp.marcar("refutaciones_pendientes", False)
        # sin autoridad
        pp.transicionar("CHALLENGED", "revisión")
        try:
            pp.transicionar("ACCEPTED", "aceptar")
            v("P6.1 sin autoridad debe fallar", False, "no falló")
        except ValueError:
            v("P6.1 sin autoridad debe fallar", True)

    # P7: Etapa 1 bloqueada hasta ACCEPTED
    with tempfile.TemporaryDirectory() as td6:
        pp = Puerta(os.path.join(td6, "puerta.db"))
        v("P7.1 bloqueada inicial", pp.etapa1_bloqueada() is True)
        # Marcar todo y aceptar
        pp.marcar("artefactos_integros", True)
        pp.marcar("revisor_independiente", True)
        pp.marcar("autoridad_nombrada", True)
        pp.marcar("refutaciones_pendientes", False)
        pp.transicionar("CHALLENGED", "revisión")
        pp.transicionar("ACCEPTED", "aceptar")
        v("P7.2 no bloqueada tras ACCEPTED", pp.etapa1_bloqueada() is False)

print("PASS: %d/%d" % (n - len(fails), n))
if fails: print("FAILS:", fails)
