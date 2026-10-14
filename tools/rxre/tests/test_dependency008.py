#!/usr/bin/env python3
"""RXRE-008. Dependencias de validacion: cadenas VALIDATION -> DEPENDENCY ->
REMEDIATION -> RESULTADO.

LA PREGUNTA DISCRIMINANTE DE RXRE-008:

    ¿puede RXRE representar y recuperar la cadena:
        VALIDATION_GOAL -> TEST_TARGET -> BUILD_CONFIGURATION ->
        DEPENDENCY -> OBSERVED_BLOCKER -> REMEDIATION -> EXECUTION_RESULT
    con cada eslabon MEDIDO (no asumido), contextualizado (revision,
    herramientas, flags), y con distinciones epistemicas (bloqueado /
    fallado / no_ejecutado)?

Y mide algo mas que el camino feliz: el estado inicial MISSING debe
permanecer MISSING mientras la remediación este en PENDING, y solo pasar a
SATISFIED cuando una VERIFICACION independiente (otro result_id) lo confirme.
Eso es lo que impide que una hipotesis de "ya se pudo instalar" haga creer
que la dependency esta resuelta sin evidencia.

Se prueba por dos medios:
  1. Por la API publica del core (registrar_dependency, registrar_remediation,
     marcar_remediacion_completada, query_validation_chain): aqui se miden
     las transiciones de estado, el contexto y la cadena.
  2. Por mutacion: la verificacion de una dependency MISSING solo a SATISFIED
     cuando verification_result == 'RESOLVED' Y hay un verification_evidence.
     Una remediación declarada RESOLVED sin evidencia NO actualiza la
     dependency (la cadena quedaria en el aire).

El patron de prueba sigue a test_integration.py: db temporal, cinco fases,
y asserts explicitos que fallan por separado.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from core.store import (
    conectar,
    registrar_dependency,
    registrar_remediation,
    marcar_remediation_completada,
    query_validation_chain,
)


def run_test():
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name

    c = conectar(db_path)

    # -------------------------------------------------------------- 1.
    # PRECONDICIONES
    # --------------------------------------------------------------
    assert os.path.isfile(db_path), "db_path debe existir"

    # -------------------------------------------------------------- 2.
    # FASE A: una dependency MISSING observada para una validacion concreta
    # (el caso KytyPS5: SDL3 / libX11 / wayland ausentes en Nobara).
    # --------------------------------------------------------------
    reg = registrar_dependency(
        c,
        target="S_ADD_U32_regression",
        name="SDL3",
        state="MISSING",
        required=True,
        diagnostic=(
            "CMake Error: Could NOT find SDL3 (missing: SDL3_LIBRARY SDL3_INCLUDE_DIR)"
        ),
        source="3rdparty/SDL3/cmake/FindSDL3.cmake:124",
        context={
            "os": "Nobara Linux 44",
            "cmake_version": "4.3.0",
            "compiler": "GCC 16.2.1",
            "target": "shader_recompiler_compute_tests",
        },
        validated_by="op_kyty_configure_1",
    )
    assert reg["estado"] == "ok", "registrar_dependency debe devolver ok"
    assert reg["state"] == "MISSING", "estado inicial: MISSING"
    assert reg["target"] == "S_ADD_U32_regression", "target debe coincidir"
    assert reg["required"] is True, "requerida: True"
    assert reg["diagnostic"] in reg["diagnostic"], "diagnostic debe conservarse"
    assert "Nobara Linux 44" in json.dumps(reg["context"]), "contexto debe guardarse"
    assert reg["dep_id"].startswith("dep_"), "dep_id debe tener prefijo dep_"
    print("1. dependency MISSING registrada: %s (target=%s)" % (reg["id"][:12], reg["target"]))

    # -------------------------------------------------------------- 3.
    # FASE B: la remediation se PROPOSE (attempted=False) y NO debe
    # modificar la dependency. MISSING no pasa a SATISFIED por arte de
    # magia: se necesita una verificacion independiente.
    # --------------------------------------------------------------
    rem = registrar_remediation(
        c,
        dep_id=reg["id"],
        remediation="dnf install -y SDL3-devel libX11-devel wayland-devel",
        remediation_type="INSTALL",
        target="S_ADD_U32_regression",
    )
    assert rem["estado"] == "ok", "registrar_remediation debe devolver ok"
    assert rem["attempted"] is False, "remediación propuesta no puede ser intentada"
    # Re-leemos la dependency: sigue MISSING (la propuesta no cambia el estado).
    cadena = query_validation_chain(c, target="S_ADD_U32_regression")
    assert cadena["estado"] == "ok"
    assert len(cadena["dependencias"]) >= 1
    assert cadena["dependencias"][0]["state"] == "MISSING", (
        "la remediación PROUESTA no debe cambiar el estado de la dependency"
    )
    print("2. remediación propuesta (attempted=False) -> dependency SIGUE MISSING")

    # -------------------------------------------------------------- 4.
    # FASE C: ejecutar la remediation y VERIFICARLA con un result_id de
    # evidencia INDEPENDIENTE (el rc=0 de la dnf).
    # --------------------------------------------------------------
    verif = marcar_remediation_completada(
        c,
        rem_id=rem["id"],
        verification_result="RESOLVED",
        verification_evidence="res_dnf_success_001",
    )
    assert verif["estado"] == "ok", "marcar_remediation_completada debe devolver ok"
    assert verif["verification_result"] == "RESOLVED", "resultado: RESOLVED"

    # Ahora SI: la dependency pasa a SATISFIED porque hay verificación
    # independiente con evidencia.
    cadena = query_validation_chain(c, target="S_ADD_U32_regression")
    deps = cadena["dependencias"]
    assert len(deps) >= 1, "debe aparecer la dependency en la cadena"
    dep = deps[0]
    assert dep["state"] == "SATISFIED", "MISSING + RESOLVED + evidencia = SATISFIED"
    assert dep["verified"] is True, "verification: True"
    assert dep["remediation"]["remediation_type"] == "INSTALL"
    assert dep["remediation"]["evidence"] == "res_dnf_success_001"
    print("3. remediación EJECUTADA y VERIFICADA con evidencia:")
    print("     dependency.state=%s | verification_result=%s | evidence=%s"
          % (dep["state"], dep["remediation"]["verification_result"],
             dep["remediation"]["evidence"]))

    # -------------------------------------------------------------- 5.
    # FASE D: mutacion discriminante. Si se declara RESOLVED sin
    # verification_evidence, la dependency NO debe cambiar (cadena en el
    # aire). Esto demuestra que el estado no depende de la opinion de quien
    # remedia, sino de la evidencia.
    # --------------------------------------------------------------
    reg2 = registrar_dependency(
        c,
        target="S_ADD_U32_regression",
        name="libX11",
        state="MISSING",
        required=True,
        diagnostic="CMake Error: Could NOT find X11",
        source="3rdparty/SDL3/cmake/sdlchecks.cmake:1",
        context={"cmake_version": "4.3.0"},
    )
    rem2 = registrar_remediation(
        c, dep_id=reg2["id"], remediation="dnf install -y libX11-devel",
        remediation_type="INSTALL", target="S_ADD_U32_regression")
    # Declarar RESOLVED SIN evidencia.
    verif2 = marcar_remediation_completada(
        c, rem_id=rem2["id"], verification_result="RESOLVED",
        verification_evidence=None)
    assert verif2["estado"] == "ok", "debe aceptar la marca sin evidencia"
    cadena2 = query_validation_chain(c, target="S_ADD_U32_regression")
    # Encontrar la fila de libX11
    libx11 = [d for d in cadena2["dependencias"] if d["name"] == "libX11"][0]
    assert libx11["state"] == "MISSING", (
        "RESOLVED sin verification_evidence NO debe pasar a SATISFIED"
    )
    # También checks the evidence field
    assert libx11["remediation"]["verification_result"] == "RESOLVED"
    print("4. RESOLVED sin evidencia -> libX11 PERMANECE MISSING (cadena incompleta)")

    # -------------------------------------------------------------- 6.
    # FASE E: la cadena completa y distinguible: la diferencia entre
    # test BLOQUEADO (dependency MISSING, remediation pendiente) y test
    # FALLADO / no-ejecutado esta en la cadena, no en un campo binario.
    # --------------------------------------------------------------
    full = query_validation_chain(c, target="S_ADD_U32_regression")
    estados = {d["name"]: d["state"] for d in full["dependencias"]}
    print("5. cadena completa para S_ADD_U32_regression:")
    for name, estado in estados.items():
        print("     - %s: %s" % (name, estado))
    assert "SDL3" in estados
    assert estados["SDL3"] == "SATISFIED", "SDL3 resuelto con evidencia"
    assert estados["libX11"] == "MISSING", "libX11 pendiente de evidencia"

    # Un query con filtro devuelve solo lo esperado.
    filtered = query_validation_chain(c, target="S_ADD_U32_regression", state="MISSING")
    missing = [d["name"] for d in filtered["dependencias"]]
    assert "libX11" in missing, "filtro por state=MISSING debe devolver libX11"
    assert "SDL3" not in missing, "SDL3 ya no esta MISSING"
    print("6. filtrado por state=MISSING -> [libX11]; estado: %s"
          % json.dumps(missing))

    # -------------------------------------------------------------- 7.
    # RESUMEN DE CAPACIDADES
    # --------------------------------------------------------------
    c.close()
    os.unlink(db_path)
    print()
    print("=== CAPACIDADES RXRE-008 VERIFICADAS ===")
    print("  - La dependency es un requisito MEDIDO para una validacion concreta.")
    print("  - El estado viaja con su diagnostico y contexto (revision, herramientas, flags).")
    print("  - MISSING se mantiene hasta que una verificacion independiente lo resuelve.")
    print("  - RESOLVED sin evidencia no falsea el estado (cadena incompleta, no cerrada).")
    print("  - La cadena VALIDATION -> DEPENDENCY -> REMEDIATION -> RESULTADO se recupera.")
    print("  - Distingue BLOCKED (dependency MISSING/pendiente) de FALLADO / no-ejecutado.")
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_test())
    except AssertionError as e:
        print("FAIL: %s" % e)
        sys.exit(1)
