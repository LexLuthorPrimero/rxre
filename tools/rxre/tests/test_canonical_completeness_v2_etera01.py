#!/usr/bin/env python3
"""RXRE-CANONICAL_COMPLETENESS_V2: auditoria de completitud anidada y raw."""
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/complete_v2_test.sqlite3"
TRACE = "complete-v2"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def res(rid, completo=True, omitidos=0, limite=500, elem="cfg",
        completo_key=True, anidada=None):
    r = {"result_id": rid, "type": "control_flow", "value": {"n": 1},
         "source": "/bin/ls", "scope": "binary", "tool": "radare2"}
    c = {"omitidos": omitidos, "limite": limite, "elemento": elem}
    if completo_key:
        c["completo"] = completo
    r["completitud"] = c
    if anidada is not None:
        r["completitud_anidada"] = anidada
    return r


class _Missing:
    pass


_MISSING = _Missing()


def comp(rs):
    return machine._obs_completeness(rs)


# A. Envelope sin marcador de completitud -> complete (default documentado)
def test_A_no_marker():
    r = {"result_id": "a1", "type": "T", "value": {}, "source": "/x", "scope": "binary", "tool": "rizin"}
    assert comp([r]) == "complete"
    print("TEST_A PASS: sin marcador -> complete (default documentado)")


# B. completitud presente pero completo ausente -> unknown
def test_B_completo_missing():
    r = res("b1", completo=_MISSING, completo_key=False)
    assert comp([r]) == "unknown"
    print("TEST_B PASS: completitud sin 'completo' -> unknown")


# C. completo null -> unknown
def test_C_completo_null():
    r = res("c1", completo=None)
    assert comp([r]) == "unknown"
    print("TEST_C PASS: completo null -> unknown")


# D. completo tipo invalido -> unknown
def test_D_completo_invalid_type():
    r = res("d1", completo="yes")
    assert comp([r]) == "unknown"
    print("TEST_D PASS: completo tipo invalido -> unknown")


# E. Truncacion anidada, lista principal completa -> partial
def test_E_nested_partial():
    r = res("e1", completo=True, anidada={"huecos": {"completo": False, "omitidos": 5}})
    assert comp([r]) == "partial"
    print("TEST_E PASS: truncacion anidada -> partial")


# F. huecos truncados, instrucciones completos -> partial
def test_F_huecos_truncated():
    r = res("f1", completo=True, anidada={"huecos": {"completo": False}})
    assert comp([r]) == "partial"
    print("TEST_F PASS: huecos truncados, instrucciones completos -> partial")


# G. raw recortado (campo raw con marcador) -> partial via declared sample
def test_G_raw_truncated():
    r = {"result_id": "g1", "type": "T", "value": {}, "source": "/x", "scope": "binary",
         "tool": "t", "raw": {"coincidencias_truncadas": True}}
    assert machine._is_declared_sample(r)
    assert comp([r]) == "partial"
    print("TEST_G PASS: raw recortado declarado -> partial")


# H. Resultado que excede limite de primer nivel (sintetico) -> partial
def test_H_exceeds_first_level():
    r = res("h1", completo=False, omitidos=300, limite=500)
    assert comp([r]) == "partial"
    print("TEST_H PASS: excede limite primer nivel -> partial")


# I. Excede limite anidado (sintetico) -> partial
def test_I_exceeds_nested():
    r = res("i1", completo=True, anidada={"huecos": {"completo": False, "omitidos": 50}})
    assert comp([r]) == "partial"
    print("TEST_I PASS: excede limite anidado -> partial")


# J. Alcanza limite sin evidencia de omision -> complete
def test_J_at_limit_no_omission():
    r = res("j1", completo=True, omitidos=0, limite=500)
    assert comp([r]) == "complete"
    print("TEST_J PASS: en el limite sin evidencia de omision -> complete")


# K. Misma muestra visible, distinto estado de completitud -> no_observable
def test_K_same_visible_diff_completeness():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    orig = {k: getattr(store, k) for k in
            ("registrar", "registrar_evento", "registrar_reflexion",
             "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
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
            {"result_id": "s1", "type": "control_flow", "value": {"n": 1},
             "source": "/bin/ls", "scope": "binary", "tool": "radare2",
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
    assert r["experiment"]["veredicto"] == "no_observable", r
    print("TEST_K PASS: misma muestra visible, distinta completitud -> no_observable")


# L. Modo no canonico -> comportamiento previo
def test_L_non_canonical():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r["experiment"]["veredicto"] == "refutada", r
    print("TEST_L PASS: modo no canonico conserva comportamiento")


if __name__ == "__main__":
    test_A_no_marker()
    test_B_completo_missing()
    test_C_completo_null()
    test_D_completo_invalid_type()
    test_E_nested_partial()
    test_F_huecos_truncated()
    test_G_raw_truncated()
    test_H_exceeds_first_level()
    test_I_exceeds_nested()
    test_J_at_limit_no_omission()
    test_K_same_visible_diff_completeness()
    test_L_non_canonical()
    print("ALL CANONICAL_COMPLETENESS_V2 TESTS PASS")
