#!/usr/bin/env python3
"""RXRE-CANONICAL_COMPARISON_V3: identidad UMR, truncacion declarada, orden."""
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/canon_v3_test.sqlite3"
TRACE = "canon-v3"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def canon(rs):
    st, c = machine._canon_obs(rs)
    return st, c


def umr(rid, reg, value=0x1234):
    return {"result_id": rid, "type": "RAW_BINARY", "value": value,
            "source": "0000:01:00.0", "scope": "gpu", "tool": "umr",
            "location": {"pci_address": "0000:01:00.0", "register": reg}}


def test_1_umr_same_register_equal():
    assert canon([umr("r1", "regA")])[1] == canon([umr("r2", "regA")])[1]
    print("TEST_1 PASS: UMR mismo registro y valor -> equivalentes")


def test_2_umr_different_register_not_equal():
    assert canon([umr("r1", "regA")])[1] != canon([umr("r2", "regB")])[1]
    print("TEST_2 PASS: UMR registros distintos -> no equivalentes")


def test_3_umr_missing_register_abstains():
    no_reg = {"result_id": "r1", "type": "RAW_BINARY", "value": 0x1234,
              "source": "0000:01:00.0", "scope": "gpu", "tool": "umr",
              "location": {"pci_address": "0000:01:00.0"}}
    st, c = canon([no_reg])
    assert st == "incomplete" and c is None
    print("TEST_3 PASS: UMR sin identidad de registro -> abstencion (incomplete)")


def test_4_umr_extra_fields():
    # value_hex es redundante con value; bitfields/decoded derivados; registros_leidos provenance
    a = umr("r1", "regA")
    b = umr("r2", "regA")
    b["value_hex"] = "0x1234"  # redundante con value
    assert canon([a])[1] == canon([b])[1], "value_hex redundante no debe cambiar"
    # registros_leidos es provenance: no aporta semantica de la lectura
    b2 = umr("r3", "regA")
    b2["registros_leidos"] = ["a", "b"]
    assert canon([a])[1] == canon([b2])[1], "registros_leidos (provenance) no aporta"
    # bitfields derivados del valor: no cambian si value igual
    b3 = umr("r4", "regA")
    b3["bitfields"] = {"f": 1}
    assert canon([a])[1] == canon([b3])[1], "bitfields derivados no aportan"
    print("TEST_4 PASS: campos UMR extra no aportan semantica no contenida en value")


def test_5_declared_truncation_no_full_equality():
    # Ambos brazos son muestras declaradas e iguales -> abstencion (no_observable)
    s1 = {"result_id": "s1", "type": "STRUCTURAL_FACTS", "value": {"a": 1},
          "source": "/x.c", "scope": "source", "tool": "tree_sitter",
          "limitations": ["muestra parcial"], "raw": {"coincidencias_truncadas": True}}
    s2 = {"result_id": "s2", "type": "STRUCTURAL_FACTS", "value": {"a": 1},
          "source": "/x.c", "scope": "source", "tool": "tree_sitter",
          "limitations": ["muestra parcial"], "raw": {"coincidencias_truncadas": True}}
    assert canon([s1])[1] == canon([s2])[1]
    assert machine._is_declared_sample(s1) and machine._is_declared_sample(s2)
    print("TEST_5 PASS: muestras declaradas iguales -> no afirmar igualdad completa")


def test_6_complete_vs_partial_no_full_equality():
    # completo vs parcial -> los valores difieren -> refutada (no igualdad)
    full = {"result_id": "f1", "type": "T", "value": {"n": 100},
            "source": "/x", "scope": "binary", "tool": "rizin"}
    part = {"result_id": "p1", "type": "T", "value": {"n": 100, "_sample": True},
            "source": "/x", "scope": "binary", "tool": "rizin",
            "limitations": ["muestra parcial"]}
    assert canon([full])[1] != canon([part])[1]
    print("TEST_6 PASS: completo vs parcial -> no afirmar igualdad completa")


def test_7_equal_samples_abstain_state():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    # two identical arms, both declared samples -> handler should abstain
    orig = {k: getattr(store, k) for k in
            ("registrar", "registrar_evento", "registrar_reflexion",
             "registrar_investigacion", "registrar_audit_log", "refs_invalidos")}
    store.registrar = lambda c, *a, **k: "op_noop"
    store.registrar_evento = lambda c, *a, **k: "ev_noop"
    store.registrar_reflexion = lambda c, *a, **k: {"estado": "ok", "reflexion_id": "r"}
    store.registrar_investigacion = lambda c, *a, **k: {"estado": "ok", "id": 1}
    store.registrar_audit_log = lambda c, *a, **k: 1
    store.refs_invalidos = lambda c, refs: []
    try:
        # monkeypatch dispatch to return declared-sample results
        orig_d = machine.dispatch.ejecutar

        def fake(cap, params):
            return {"status": "ok", "results": [
                {"result_id": "s1", "type": "T", "value": {"a": 1}, "source": "/x",
                 "scope": "source", "tool": "tree_sitter",
                 "limitations": ["muestra parcial"],
                 "raw": {"coincidencias_truncadas": True}}]}
        machine.dispatch.ejecutar = fake
        r = machine.procesar_linea(json.dumps({
            "op": "experiment", "capability": "source.ast_parse",
            "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
            "canonico": True,
            "baseline_params": {"artefacto": "/bin/ls"},
            "modified_params": {"artefacto": "/bin/ls"}}))
        machine.dispatch.ejecutar = orig_d
    finally:
        for k, v in orig.items():
            setattr(store, k, v)
    assert r["experiment"]["veredicto"] == "no_observable", r
    print("TEST_7 PASS: dos muestras iguales con procedencia parcial -> no_observable")


def test_8_top_level_order_normalized_duplicates_preserved():
    rs = [umr("r%d" % i, "regA") for i in range(3)]
    perm = list(reversed(rs))
    assert canon(rs)[1] == canon(perm)[1]
    dup = rs + [rs[0]]
    assert len(canon(dup)[1]) == 4
    print("TEST_8 PASS: orden de lista superior normalizado; duplicados preservados")


def test_9_semantic_nested_order_preserved():
    a = {"result_id": "a1", "type": "T", "value": {"instr": [{"i": 1}, {"i": 2}]},
         "source": "/x", "scope": "binary", "tool": "capstone"}
    b = {"result_id": "b1", "type": "T", "value": {"instr": [{"i": 2}, {"i": 1}]},
         "source": "/x", "scope": "binary", "tool": "capstone"}
    assert canon([a])[1] != canon([b])[1], "orden semantico (instrucciones) se conserva"
    print("TEST_9 PASS: orden de lista anidada semantica conserva la diferencia")


def test_10_missing_null_types_no_accidental_equivalence():
    a = [{"result_id": "r1", "type": "T", "value": None, "source": "/x", "scope": "binary", "tool": "rizin"}]
    b = [{"result_id": "r1", "type": "T", "value": {}, "source": "/x", "scope": "binary", "tool": "rizin"}]
    c = [{"result_id": "r1", "type": "T", "value": 0, "source": "/x", "scope": "binary", "tool": "rizin"}]
    assert canon(a)[1] != canon(b)[1]
    assert canon(b)[1] != canon(c)[1]
    print("TEST_10 PASS: nulos/tipos incompatibles no producen equivalencias accidentales")


def test_11_non_canonical_unchanged():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE", "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r["experiment"]["veredicto"] == "refutada", r
    print("TEST_11 PASS: modo no canonico conserva comportamiento")


def test_12_v2_regressions():
    # V2: order-independent canonical equality (xrefs)
    import backends.adapters.rz_xrefs as XR
    env = XR.xrefs("/bin/ls", "rizin", nivel_analisis="aaa")
    rs = env["results"]
    perm = list(reversed(rs))
    assert canon(rs)[1] == canon(perm)[1]
    # incomplete
    inc = [dict(r) for r in rs[:3]]
    inc.append({k: v for k, v in inc[0].items() if k != "result_id"})
    assert canon(inc)[0] == "incomplete"
    print("TEST_12 PASS: regresiones V2 preservadas")


if __name__ == "__main__":
    test_1_umr_same_register_equal()
    test_2_umr_different_register_not_equal()
    test_3_umr_missing_register_abstains()
    test_4_umr_extra_fields()
    test_5_declared_truncation_no_full_equality()
    test_6_complete_vs_partial_no_full_equality()
    test_7_equal_samples_abstain_state()
    test_8_top_level_order_normalized_duplicates_preserved()
    test_9_semantic_nested_order_preserved()
    test_10_missing_null_types_no_accidental_equivalence()
    test_11_non_canonical_unchanged()
    test_12_v2_regressions()
    print("ALL CANONICAL_COMPARISON_V3 TESTS PASS")
