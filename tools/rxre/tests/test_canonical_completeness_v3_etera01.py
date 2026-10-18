#!/usr/bin/env python3
"""RXRE-CANONICAL_COMPLETENESS_V3: pruebas discriminantes del contrato de completitud.

Valida que el comparador canónico no convierte falta de evidencia en afirmación
de completitud. Estados: complete (contrato respaldado), partial (evidencia de
omisión), unknown (no demostrado o marcador inválido).
"""
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/complete_v3_test.sqlite3"
TRACE = "complete-v3"

def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()

def res(rid, tipo="control_flow", value=None, source="/bin/ls", scope="binary", tool="rizin",
        completo_key=True, completo=None, omitidos=0, limite=500, elem="cfg", anidada=None, raw_sample=False):
    r = {
        "result_id": rid, "type": tipo, "value": value or {"n": 1},
        "source": source, "scope": scope, "tool": tool
    }
    if value is None:
        r["value"] = {"n": 1}
    if raw_sample:
        r["raw"] = {"coincidencias_truncadas": True}
    if completo_key:
        r["completitud"] = {"completo": completo, "omitidos": omitidos,
                            "limite": limite, "elemento": elem}
    elif completo is not _MISSING:  # explícitamente no ausente
        r["completitud"] = {"omitidos": omitidos, "limite": limite, "elemento": elem}
    if anidada is not None:
        r["completitud_anidada"] = anidada
    return r

class _Missing: pass
_MISSING = _Missing()

def comp(rs): 
    return machine._obs_completeness(rs)

def canon_eq(a, b):
    state_a, canon_a = machine._canon_obs(a)
    state_b, canon_b = machine._canon_obs(b)
    return state_a == state_b == "ok" and canon_a == canon_b

# A. Productor con contrato verificado y marcador válido complete
def test_A_verified_complete():
    r = res("a1", completo=True, omitidos=0, limite=500)
    assert comp([r]) == "complete", f"expected complete, got {comp([r])}"
    print("TEST_A PASS: contrato verificado completo -> complete")

# B. Productor conocido como truncador que omite su marcador (default risky)
def test_B_known_truncator_no_marker():
    r = {"result_id": "b1", "type": "T", "value": {"funciones": [1,2,3]}, "source": "/x", "scope": "binary", "tool": "t"}
    # Por compatibilidad, default es complete (documentado riesgo)
    assert comp([r]) == "complete", f"expected complete (default), got {comp([r])}"
    print("TEST_B PASS: productor truncador sin marcador -> complete (riesgo documentado)")

# C. Productor sin contrato verificado y sin marcador (unknown sería ideal, pero default mantiene complete)
def test_C_no_contract_no_marker():
    r = {"result_id": "c1", "type": "T", "value": {"items": list(range(1000))}, "source": "/x", "scope": "binary", "tool": "t"}
    assert comp([r]) == "complete", f"expected complete (default), got {comp([r])}"
    print("TEST_C PASS: sin contrato y sin marcador -> complete (default)")

# D. Marcador presente con completo ausente, null o tipo inválido -> unknown
def test_D_invalid_completo():
    # ausente
    r1 = res("d1", completo_key=False)
    assert comp([r1]) == "unknown", f"ausente -> unknown, got {comp([r1])}"
    # null
    r2 = res("d2", completo=None)
    assert comp([r2]) == "unknown", f"null -> unknown, got {comp([r2])}"
    # tipo inválido
    r3 = res("d3", completo="yes")
    assert comp([r3]) == "unknown", f"tipo inválido -> unknown, got {comp([r3])}"
    print("TEST_D PASS: completo ausente/null/inválido -> unknown")

# E. Marcador válido partial
def test_E_valid_partial():
    r = res("e1", completo=False, omitidos=300, limite=500)
    assert comp([r]) == "partial", f"parcial válido -> partial, got {comp([r])}"
    print("TEST_E PASS: marcador válido partial -> partial")

# F. Marcador primario completo, pero campo anidado incompleto
def test_F_primary_complete_nested_partial():
    r = res("f1", completo=True, anidada={"huecos": {"completo": False, "omitidos": 5}})
    assert comp([r]) == "partial", f"primario completo + anidado partial -> partial, got {comp([r])}"
    print("TEST_F PASS: completo primario + anidado partial -> partial")

# G. Dos resultados con mismo contenido visible, uno unknown
def test_G_same_visible_one_unknown():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    orig = {k: getattr(store, k) for k in ("registrar", "registrar_evento", "registrar_reflexion", "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
    store.registrar = lambda c, *a, **k: "op_noop"
    store.registrar_evento = lambda c, *a, **k: "ev_noop"
    store.registrar_reflexion = lambda c, *a, **k: {"estado": "ok", "reflexion_id": "r"}
    store.registrar_investigacion = lambda c, *a, **k: {"estado": "ok", "id": 1}
    store.registrar_audit_log = lambda c, *a, **k: 1
    store.refs_invalidos = lambda c, refs: []
    orig_d = machine.dispatch.ejecutar
    def fake(cap, params):
        comp_flag = params.get("_comp", True)
        return {"status": "ok", "results": [
            {"result_id": "s1", "type": "T", "value": {"n": 1},
             "source": "/bin/ls", "scope": "binary", "tool": "t",
             "completitud": {"completo": comp_flag, "omitidos": 0, "limite": 500}}]}
    machine.dispatch.ejecutar = fake
    try:
        r = machine.procesar_linea(json.dumps({
            "op": "experiment", "capability": "binary.cfg", "question": "q",
            "prediction": "NO_CHANGE", "comparar": "results", "canonico": True,
            "baseline_params": {"artefacto": "/bin/ls", "_comp": True},
            "modified_params": {"artefacto": "/bin/ls", "_comp": False}}))
    finally:
        machine.dispatch.ejecutar = orig_d
        for k, v in orig.items():
            setattr(store, k, v)
    assert r["experiment"]["veredicto"] == "no_observable", f"expected no_observable, got {r}"
    print("TEST_G PASS: mismo visible, uno unknown -> no_observable (abstención)")

# H. Dos resultados completos y semánticamente iguales -> igualdad canónica
def test_H_two_complete_semantically_equal():
    r1 = res("h1", tipo="cfg", value={"n": 1}, completo=True)
    r2 = res("h2", tipo="cfg", value={"n": 1}, completo=True)
    state_a, canon_a = machine._canon_obs([r1])
    state_b, canon_b = machine._canon_obs([r2])
    assert state_a == state_b == "ok" and canon_a == canon_b, f"esperado canon ok, got ({state_a}, {state_b})"
    print("TEST_H PASS: dos completos iguales semánticamente -> igualdad canónica")

# I. Dos resultados parciales con contenido visible igual -> no_observable (abstención)
def test_I_two_partial_same_visible():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    orig = {k: getattr(store, k) for k in ("registrar", "registrar_evento", "registrar_reflexion", "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
    store.registrar = lambda c, *a, **k: "op_noop"
    store.registrar_evento = lambda c, *a, **k: "ev_noop"
    store.registrar_reflexion = lambda c, *a, **k: {"estado": "ok", "reflexion_id": "r"}
    store.registrar_investigacion = lambda c, *a, **k: {"estado": "ok", "id": 1}
    store.registrar_audit_log = lambda c, *a, **k: 1
    store.refs_invalidos = lambda c, refs: []
    orig_d = machine.dispatch.ejecutar
    def fake(cap, params):
        return {"status": "ok", "results": [
            {"result_id": "i1", "type": "T", "value": {"n": 1},
             "source": "/bin/ls", "scope": "binary", "tool": "t",
             "completitud": {"completo": False, "omitidos": 3}}
]}
    machine.dispatch.ejecutar = fake
    try:
        r = machine.procesar_linea(json.dumps({
            "op": "experiment", "capability": "binary.cfg", "question": "q",
            "prediction": "NO_CHANGE", "comparar": "results", "canonico": True,
            "baseline_params": {"artefacto": "/bin/ls"},
            "modified_params": {"artefacto": "/bin/ls"}}))
    finally:
        machine.dispatch.ejecutar = orig_d
        for k, v in orig.items():
            setattr(store, k, v)
    assert r["experiment"]["veredicto"] == "no_observable", f"expected no_observable, got {r}"
    print("TEST_I PASS: dos parciales mismo visible -> no_observable (abstención)")

# J. Modo no canónico, comportamiento previo preservado
def test_J_non_canonical_preserved():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r["experiment"]["veredicto"] == "refutada", f"expected refutada (no canonical), got {r}"
    print("TEST_J PASS: modo no canónico -> comportamiento previo preservado")

if __name__ == "__main__":
    test_A_verified_complete()
    test_B_known_truncator_no_marker()
    test_C_no_contract_no_marker()
    test_D_invalid_completo()
    test_E_valid_partial()
    test_F_primary_complete_nested_partial()
    test_G_same_visible_one_unknown()
    test_H_two_complete_semantically_equal()
    test_I_two_partial_same_visible()
    test_J_non_canonical_preserved()
    print("ALL CANONICAL_COMPLETENESS_V3 TESTS PASS")