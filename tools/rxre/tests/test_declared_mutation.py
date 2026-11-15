#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Self-test de `harness/declared_mutation.py`.

El mundo de prueba es SINTÉTICO a propósito: así el test no codifica en su
propia sombra el estado del árbol real. El uso real del arnés sucede dentro
de cada mutación concreta declarada en RXRE, con su probe real.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location(
    "declared_mutation", os.path.join(PKG, "harness", "declared_mutation.py"))
dm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dm)

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %s" % nombre)
    else:
        print("  FAIL %s: %s" % (nombre, info))
        _fallos.append(nombre)


def fixture_raiz(tmp):
    raiz = os.path.join(tmp, "arbol")
    os.makedirs(os.path.join(raiz, "sub"), exist_ok=True)
    with open(os.path.join(raiz, "mod.py"), "w", encoding="utf-8") as f:
        f.write("STATE = 'OK'\n")
    with open(os.path.join(raiz, "sub", "decoy.py"), "w", encoding="utf-8") as f:
        f.write("STATE = 'OK'\n")  # buscar debe NO tocar este decoy
    return raiz


PROBE_CHECK = ["python3", "-c",
               "import sys;sys.exit(0 if open(sys.argv[1]).read().strip().endswith('OK') else 1)",
               "{workdir}/mod.py"]
PROBE_ALWAYS_PASS = ["python3", "-c", "pass"]
PROBE_BOGUS = ["python3-ruta-inexistente-xyz", "--help"]


def test_caer_detectada(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m1", "ruta": "mod.py", "buscar": "OK", "cambio": "ROTO",
         "esperado": "CAER", "probe": PROBE_CHECK}
    r = dm.ejecutar_entrada(raiz, e, tmp)
    v("CAER detectada", r["resultado"] == "DETECTADA" and r["esperado_cumplido"] is True)


def test_caer_punto_ciego(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m2", "ruta": "mod.py", "buscar": "OK", "cambio": "ROTO",
         "esperado": "CAER", "probe": PROBE_ALWAYS_PASS}
    r = dm.ejecutar_entrada(raiz, e, tmp)
    v("CAER no detectada => SOBREVIVE y esperado_cumplido=False",
      r["resultado"] == "SOBREVIVE" and r["esperado_cumplido"] is False)


def test_vivir_sobrevive(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m3", "ruta": "mod.py", "buscar": "OK", "cambio": "ROTO",
         "esperado": "VIVIR", "probe": PROBE_ALWAYS_PASS}
    r = dm.ejecutar_entrada(raiz, e, tmp)
    v("VIVIR sobrevive y se cumple", r["resultado"] == "SOBREVIVE" and r["esperado_cumplido"] is True)


def test_vivir_sorpresa(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m4", "ruta": "mod.py", "buscar": "OK", "cambio": "ROTO",
         "esperado": "VIVIR", "probe": PROBE_CHECK}
    r = dm.ejecutar_entrada(raiz, e, tmp)
    v("VIVIR detectada es SORPRESA (se reporta)",
      r["resultado"] == "DETECTADA" and r["esperado_cumplido"] is None)


def test_probe_no_ejecutable_es_error(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m5", "ruta": "mod.py", "buscar": "OK", "cambio": "ROTO",
         "esperado": "CAER", "probe": PROBE_BOGUS}
    r = dm.ejecutar_entrada(raiz, e, tmp)
    v("probe imposible de ejecutar => ERROR", r["resultado"] == "ERROR")


def test_buscar_ausente_es_error(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m6", "ruta": "mod.py", "buscar": "NOEXISTE", "cambio": "X",
         "esperado": "CAER", "probe": PROBE_CHECK}
    r = dm.ejecutar_entrada(raiz, e, tmp)
    v("buscar ausente => ERROR", r["resultado"] == "ERROR")


def test_la_mutacion_no_toca_el_decoy(tmp):
    raiz = fixture_raiz(tmp)
    e = {"nombre": "m7", "ruta": "mod.py", "buscar": "OK", "cambio": "ROTO",
         "esperado": "CAER", "probe": PROBE_CHECK}
    dm.ejecutar_entrada(raiz, e, tmp)
    with open(os.path.join(raiz, "sub", "decoy.py"), encoding="utf-8") as f:
        v("el arbol de origen no se modifica", f.read() == "STATE = 'OK'\n")
    with open(os.path.join(raiz, "mod.py"), encoding="utf-8") as f:
        v("la raiz original no se muta", f.read() == "STATE = 'OK'\n")


_tmp = tempfile.mkdtemp(prefix="dm_selftest_")
test_caer_detectada(_tmp)
test_caer_punto_ciego(_tmp)
test_vivir_sobrevive(_tmp)
test_vivir_sorpresa(_tmp)
test_probe_no_ejecutable_es_error(_tmp)
test_buscar_ausente_es_error(_tmp)
test_la_mutacion_no_toca_el_decoy(_tmp)

print()
if _fallos:
    print("declared_mutation self-test FALLA:", _fallos)
    sys.exit(1)
print("declared_mutation self-test OK")
sys.exit(0)
