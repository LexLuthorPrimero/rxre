#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Self-test de `verifier/dry_drift.py`.

Lo que se comprueba: las cuatro clases de espera actúan como declaran.
Nada aquí mide RXRE de verdad (podría codificar un cambio intencional como
fallo mañana); el mundo real se prueba en el paso de integración al final.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)  # tools/rxre
spec = importlib.util.spec_from_file_location(
    "dry_drift", os.path.join(PKG, "verifier", "dry_drift.py"))
dd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dd)

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %s" % nombre)
    else:
        print("  FAIL %s: %s" % (nombre, info))
        _fallos.append(nombre)


BASE = {
    "est": {"clase": "ESTABLE", "valores": ["a", "b"]},
    "dri": {"clase": "DRIFTABLE", "valores": ["x"]},
    "vac": {"clase": "VACIA", "valores": []},
    "con": {"clase": "CONOCIDA", "valores": ["angr"]},
}


def fake_actual(**over):
    return {
        "est": ("ESTABLE", over.get("est", ["a", "b"])),
        "dri": ("DRIFTABLE", over.get("dri", ["x"])),
        "vac": ("VACIA", over.get("vac", [])),
        "con": ("CONOCIDA", over.get("con", ["angr"])),
    }


def test_estable_cambia_es_error():
    err, _, _ = dd.evaluar(fake_actual(est=["a", "b", "c"]), BASE)
    v("ESTABLE que cambia produce error", any("ESTABLE cambió" in e for e in err))


def test_drifable_cambia_es_solo_diff():
    err, _, diffs = dd.evaluar(fake_actual(dri=["x", "y"]), BASE)
    v("DRIFTABLE que cambia no falla", not err)
    v("DRIFTABLE que cambia se informa", len(diffs) == 1 and diffs[0][0] == "dri")


def test_vacia_llenarse_es_error():
    err, _, _ = dd.evaluar(fake_actual(vac=["algo"]), BASE)
    v("VACIA que se llena es hallazgo nuevo", any("VACIA se llenó" in e for e in err))


def test_conocida_crece_es_error():
    err, _, _ = dd.evaluar(fake_actual(con=["angr", "nuevo"]), BASE)
    v("CONOCIDA que crece falla", any("CONOCIDA creció" in e for e in err))


def test_conocida_encoger_no_es_error():
    err, _, diffs = dd.evaluar(fake_actual(con=[]), BASE)
    v("CONOCIDA que encoge es corrección (se informa, no falla)", not err)
    v("CONOCIDA que encoge se reporta", diffs and diffs[0][0] == "con")


def test_sin_base_avisa():
    err, avisos, _ = dd.evaluar(fake_actual(), {})
    v("sin línea base no falla", not err)
    v("sin línea base avisa", avisos)


def test_congelar_y_verificar_roundtrip(tmp):
    lb = os.path.join(tmp, "linea_base.json")
    # congelar midiendo el mundo real, pero escribiendo en tmp via monkeypatch
    real_base = dd.LINEA_BASE
    dd.LINEA_BASE = lb
    try:
        rc = dd.cmd_congelar(None)
        v("congelar devuelve 0", rc == 0)
        v("congelar escribió base", os.path.isfile(lb))
        rc = dd.cmd_verificar(None, False)
        v("verificar inmediatamente después da 0 o 4 (por 'sin cambio' no puede ser 1/2/3)",
          rc in (0, 4), "rc=%s" % rc)
        base = json.load(open(lb, encoding="utf-8"))
        v("la base tiene medidas", len(base.get("medidas", {})) >= 6)
    finally:
        dd.LINEA_BASE = real_base


test_estable_cambia_es_error()
test_drifable_cambia_es_solo_diff()
test_vacia_llenarse_es_error()
test_conocida_crece_es_error()
test_conocida_encoger_no_es_error()
test_sin_base_avisa()
_tmp = tempfile.mkdtemp(prefix="dd_roundtrip_")
test_congelar_y_verificar_roundtrip(_tmp)

print()
if _fallos:
    print("dry_drift self-test FALLA:", _fallos)
    sys.exit(1)
print("dry_drift self-test OK")
sys.exit(0)
