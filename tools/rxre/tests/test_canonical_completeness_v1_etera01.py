#!/usr/bin/env python3
"""RXRE-CANONICAL_COMPLETENESS_V1: completitud de resultados canonicos."""
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/complete_test.sqlite3"
TRACE = "complete-trace"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def res(rid, value=None, completo=True, omitidos=0, limite=500, elem="cfg"):
    return {"result_id": rid, "type": "control_flow", "value": value or {"n": 1},
            "source": "/bin/ls", "scope": "binary", "tool": "radare2",
            "completitud": {"completo": completo, "omitidos": omitidos,
                            "limite": limite, "elemento": elem}}


def comp(rs):
    return machine._obs_completeness(rs)


# A. Dos completos iguales -> no_separable
def test_A_complete_equal():
    a = [res("a1")]; b = [res("b1")]
    assert comp(a) == "complete" and comp(b) == "complete"
    ca = machine._canon_obs(a)[1]; cb = machine._canon_obs(b)[1]
    assert ca == cb
    print("TEST_A PASS: dos completos iguales -> no_separable (no abstencion)")


# B. Dos parciales iguales -> abstencion
def test_B_partial_equal_abstain():
    a = [res("a1", completo=False, omitidos=5)]
    b = [res("b1", completo=False, omitidos=5)]
    assert comp(a) == "partial" and comp(b) == "partial"
    assert machine._canon_obs(a)[1] == machine._canon_obs(b)[1]
    print("TEST_B PASS: dos parciales iguales -> no_observable (abstencion)")


# C. Completo vs parcial iguales -> abstencion
def test_C_complete_vs_partial_abstain():
    a = [res("a1", completo=True)]
    b = [res("b1", completo=False, omitidos=5)]
    assert comp(a) == "complete" and comp(b) == "partial"
    print("TEST_C PASS: completo vs parcial -> no_observable (abstencion)")


# D. Parcial vs completo con contenido visible distinto -> refutada
def test_D_partial_vs_complete_different():
    a = [res("a1", value={"n": 1}, completo=False, omitidos=5)]
    b = [res("b1", value={"n": 2}, completo=True)]
    assert comp(a) == "partial" and comp(b) == "complete"
    assert machine._canon_obs(a)[1] != machine._canon_obs(b)[1]
    print("TEST_D PASS: parcial vs completo distinto -> refutada")


# E. Completitud desconocida vs completo -> abstencion
def test_E_unknown_vs_complete():
    unk = {"result_id": "u1", "type": "control_flow", "value": {"n": 1},
           "source": "/bin/ls", "scope": "binary", "tool": "radare2",
           "completitud": {"completo": None}}
    c = [res("c1", completo=True)]
    assert comp([unk]) == "unknown" and comp(c) == "complete"
    print("TEST_E PASS: completitud desconocida vs completo -> no_observable")


# F. Dos parciales con distinto limite -> no_observable (si visibles iguales)
def test_F_partial_different_limits():
    a = [res("a1", completo=False, omitidos=5, limite=500)]
    b = [res("b1", completo=False, omitidos=9000, limite=10000)]
    assert comp(a) == "partial" and comp(b) == "partial"
    assert machine._canon_obs(a)[1] == machine._canon_obs(b)[1]
    print("TEST_F PASS: dos parciales distinto limite -> no_observable")


# G. Marcador perdido -> el comparador no abstiene (limitacion declarada)
def test_G_marker_lost():
    a = [res("a1", completo=False, omitidos=5)]
    b = [{"result_id": "b1", "type": "control_flow", "value": {"n": 1},
          "source": "/bin/ls", "scope": "binary", "tool": "radare2"}]  # sin completitud
    assert comp(a) == "partial" and comp(b) == "complete"
    print("TEST_G PASS: marcador perdido -> completitud por defecto complete (limitacion)")


# H. Alcanza el limite sin evidencia de omision -> completo (si len<=limite)
def test_H_at_limit_no_omission_evidence():
    a = [res("a1", completo=True, omitidos=0, limite=500)]
    assert comp(a) == "complete"
    print("TEST_H PASS: en el limite sin evidencia de omision -> complete")


# I. Completo mas largo que el limite de otro producer -> no parcial falso
def test_I_long_complete_not_false_partial():
    a = [res("a1", completo=True, omitidos=0, limite=500)]
    # aunque la lista sea larga, completo=True -> complete
    assert comp(a) == "complete"
    print("TEST_I PASS: completo largo no se declara parcial por longitud")


# J. Modo no canonico con los mismos envelopes -> comportamiento previo
def test_J_non_canonical():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r["experiment"]["veredicto"] == "refutada", r
    print("TEST_J PASS: modo no canonico conserva comportamiento")


# Handler-level verdicts (non-destructive)
def _handler_verdict(base_comp, mod_comp, base_val=None, mod_val=None):
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
        comp = params.get("_comp", True)
        val = params.get("_val", {"n": 1})
        return {"status": "ok", "results": [
            {"result_id": "s1", "type": "control_flow", "value": val,
             "source": "/bin/ls", "scope": "binary", "tool": "radare2",
             "completitud": {"completo": comp, "omitidos": 0, "limite": 500}}]}
    machine.dispatch.ejecutar = fake
    try:
        r = machine.procesar_linea(json.dumps({
            "op": "experiment", "capability": "binary.cfg", "question": "q",
            "prediction": "NO_CHANGE", "comparar": "results", "canonico": True,
            "baseline_params": {"artefacto": "/bin/ls", "_comp": base_comp, "_val": base_val or {"n": 1}},
            "modified_params": {"artefacto": "/bin/ls", "_comp": mod_comp, "_val": mod_val or {"n": 1}}}))
    finally:
        machine.dispatch.ejecutar = orig_d
        for k, v in orig.items():
            setattr(store, k, v)
    return r["experiment"]["veredicto"]


def test_handler_verdicts():
    assert _handler_verdict(True, True) == "no_separable"
    assert _handler_verdict(False, False) == "no_observable"
    assert _handler_verdict(True, False) == "no_observable"
    assert _handler_verdict(True, True, {"n": 1}, {"n": 2}) == "refutada"
    assert _handler_verdict(False, True, {"n": 1}, {"n": 2}) == "refutada"
    print("HANDLER VERDICTS PASS: A/B/C/D mapped correctly")


if __name__ == "__main__":
    test_A_complete_equal()
    test_B_partial_equal_abstain()
    test_C_complete_vs_partial_abstain()
    test_D_partial_vs_complete_different()
    test_E_unknown_vs_complete()
    test_F_partial_different_limits()
    test_G_marker_lost()
    test_H_at_limit_no_omission_evidence()
    test_I_long_complete_not_false_partial()
    test_J_non_canonical()
    test_handler_verdicts()
    print("ALL CANONICAL_COMPLETENESS_V1 TESTS PASS")
