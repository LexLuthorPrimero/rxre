#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-101 · MISSION roundtrip — persistir y recuperar por proceso separado.

Criterio (E1 plan): la MISSION se conserva integra en cada roundtrip;
frases nunca se mutan entre procesos; si falta el artefacto, el proceso falla.
Nada aquí demuestra que RXRE haya promovido una capacidad: hoy es infraestructura.
"""
import os
import sys
import json
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)
os.environ["IER_STORE"] = tempfile.mkdtemp(prefix="ier_roundtrip_")

from ier import mission  # noqa: E402

_fallos = []


def v(nombre, cond, info=""):
    if cond:
        print("  PASS %-40s" % nombre)
    else:
        print("  FAIL %-40s %s" % (nombre, info))
        _fallos.append(nombre)


tmp = tempfile.mkdtemp(prefix="ier_art_")
art = os.path.join(tmp, "fixture.bin")
with open(art, "wb") as f:
    f.write(b"\x7fELF" + b"\x02\x01\x01\x00" + b"fixture-ier-001")

m = mission.nuevo(
    identity={"project": "rxre", "issue": "ier-test",
              "repository": "LexLuthorPrimero/rxre", "commit": "test"},
    target={"type": "ELF", "architecture": "x86_64",
            "build_flags": ["-O0"],
            "path": art},
    problem={"expected_behavior": "exit codes observable por el invocado",
             "observed_behavior": "crash potencial en parseo",
             "reproduction": "./fixture.bin < sample"})
v("mission_id bien formado", m["mission_id"].startswith("mis_"))
v("phase inicial DESCUBRIR", m["phase"] == "DESCUBRIR")
v("outcome inicial pending", m["outcome"]["state"] == "pending")
v("artifact_sha256 relleno", bool(m["target"]["artifact_sha256"]))

m2 = mission.actualizar({**m, "phase": "ANALIZAR"})
v("actualizar fase no rompe", m2["phase"] == "ANALIZAR")

cargado = mission.cargar(m["mission_id"])
v("roundtrip preserva id", cargado["mission_id"] == m["mission_id"])
v("roundtrip preserva hash artefacto",
  cargado["target"]["artifact_sha256"] == m["target"]["artifact_sha256"])
v("roundtrip preserva identidad",
  cargado["identity"]["issue"] == "ier-test")

mission.añadir_hipotesis(m["mission_id"],
                         "H1: parser nunca ve el cuarto byte", rival_de=None)
mission.añadir_hipotesis(m["mission_id"],
                         "H2: parser no valida tamano de entrada",
                         rival_de=None)
mission.añadir_experimento(m["mission_id"], "repro",
                           {"observable": "exit code observable",
                            "outcome": "NOT_DETERMINED"})
m3 = mission.cargar(m["mission_id"])
v("2 hipotesis registradas", len(m3["hypotheses"]) == 2)
v("1 experimento registrado", len(m3["experiments"]) == 1)

mission.fijar_decision(m["mission_id"], "reparar", "bug de parseo confirmado")
mission.fijar_outcome(m["mission_id"], "partial", {"diff": "1 byte"})
m4 = mission.cargar(m["mission_id"])
v("intervention registrada", m4["intervention"]["kind"] == "reparar")
v("outcome registrada", m4["outcome"]["state"] == "partial")

try:
    mission.actualizar({**m4, "phase": "NO_EXISTE"})
    v("fase invalida rechazada", False)
except ValueError:
    v("fase invalida rechazada", True)

try:
    mission.actualizar({**m4, "outcome": {"state": "inventado", "obtained": None}})
    v("outcome fuera de dominio rechazado", False)
except ValueError:
    v("outcome fuera de dominio rechazado", True)


def test_no_artifact_path_falla():
    try:
        mission.nuevo(identity={"project": "x"}, target={"path": "/no/existe.bin"},
                      problem={})
        v("sin artefacto falla", False)
    except FileNotFoundError:
        v("sin artefacto falla", True)


test_no_artifact_path_falla()

print()
if _fallos:
    print("IER mission roundtrip FALLA:", _fallos)
    sys.exit(1)
print("IER mission roundtrip OK")
sys.exit(0)
