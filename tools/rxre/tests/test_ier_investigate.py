#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-103 · discriminación de hipótesis rivales — el motor ejecuta, no inventa.

Nada aquí prueba nada sobre RXRE en su conjunto: demuestra que existe la
maquinaria para obligar a que una hipótesis rival tenga que elegir salida
contra observación registrada. La ausencia de discriminante => NOT_DETERMINED.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_inv_")

from ier import investigate, mission  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-46s" % nombre)
    else:
        print("  FAIL %-46s %s" % (nombre, info))
        _fallos.append(nombre)


# 1) seleccionar un discriminante
disc = investigate.elegir({"H1": [], "H2": []})
v("discriminante seleccionable", disc in ("exit_code_delta",
                                          "output_hash_delta",
                                          "set_identity"))

# 2) contrastar con predicción de H1 cumplida
obs = {"discriminant": "exit_code_delta",
       "h1_result": 42, "h2_result": 0,
       "expected_h1": 42}
r = investigate.contrastar(obs)
v("H1 gana si observa lo que H1 predice", r["decision"] == "H1")

# 3) predicción violada → H2
obs2 = {"discriminant": "exit_code_delta",
        "h1_result": 0, "h2_result": 7,
        "expected_h1": 42}
r = investigate.contrastar(obs2)
v("H2 gana si H1 falla", r["decision"] == "H2")

# 4) sin observaciones → NOT_DETERMINED (no se inventa)
r = investigate.contrastar({"discriminant": "exit_code_delta",
                             "h1_result": None, "h2_result": None,
                             "expected_h1": 42})
v("sin observaciones NOT_DETERMINED", r["decision"] == "NOT_DETERMINED")

# 5) mismo observable H1 == H2 → NOT_DETERMINED (el discriminante es insuficiente)
r = investigate.contrastar({"discriminant": "exit_code_delta",
                             "h1_result": 1, "h2_result": 1,
                             "expected_h1": 42})
v("H1==H2 => NOT_DETERMINED", r["decision"] == "NOT_DETERMINED")

# 6) falsabilidad mínima — ancla medible real (hex/numero/unidad o bytes)
f = investigate.evaluar_falsabilidad("el parser rechaza en offset 0x00")
v("falsabilidad semi-cuantitativa", f["semi_cuantitativa"])

# 7) hipótesis basura rechazada
b = investigate.rechaza_inaceptable("siempre siempre si o no")
v("rechazada por lenguaje absoluto", b)

# 8) misión con hipótesis registrada + experimento real
tmp = tempfile.mkdtemp(prefix="ier_mis_")
art = os.path.join(tmp, "a.bin")
open(art, "wb").close()
m = mission.nuevo(identity={"project": "rxre", "issue": "ier-disc-test",
                            "repository": "rxre", "commit": "x"},
                  target={"type": "ELF", "architecture": "x86_64",
                          "build_flags": [], "path": art},
                  problem={"expected_behavior": "x",
                           "observed_behavior": "y",
                           "reproduction": "z"})
mission.añadir_hipotesis(m["mission_id"], "H1: parser nunca valida largo")
mission.añadir_experimento(m["mission_id"], "repro",
                           {"observable": "exit_code observable",
                            "h1_result": 42,
                            "h2_result": 0,
                            "expected_h1": 42})
m2 = mission.cargar(m["mission_id"])
v("mission con experimento real",
  len(m2["experiments"]) == 1)

print()
if _fallos:
    print("IER investigate FALLA:", _fallos)
    sys.exit(1)
print("IER investigate OK")
sys.exit(0)
