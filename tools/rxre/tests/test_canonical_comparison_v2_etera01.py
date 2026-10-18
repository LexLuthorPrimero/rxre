#!/usr/bin/env python3
"""RXRE-CANONICAL_COMPARISON_V2: igualdad canonica independiente del orden."""
import hashlib
import json
import os
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import backends.adapters.rz_xrefs as XR
import rxre.core.store as store

DB = "/tmp/opencode/canon_v2_test.sqlite3"
TRACE = "canon-v2"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def real_results():
    """Resultados reales del productor (no destructivo: el adapter no escribe DB)."""
    env = XR.xrefs("/bin/ls", "rizin", nivel_analisis="aaa")
    assert env.get("status") == "ok"
    return env["results"]


def producer_ids(data):
    """IDs que asignaria el productor real (index-dependent)."""
    out = []
    for i, xref in enumerate(data):
        raw = {k: v for k, v in xref["value"].items() if k != "nodos"}
        out.append("res_xref_" + hashlib.sha256(
            ("%s|%s|%d|%s" % (xref["source"], "rizin", i,
                              json.dumps(raw, sort_keys=True, default=str))).encode()
        ).hexdigest()[:16])
    return out


def canon(rs):
    st, c = machine._canon_obs(rs)
    assert st == "ok", st
    return c


def test_1_permutation_before_ids_equal():
    rs = real_results()
    perm = list(reversed(rs))
    perm_with_ids = []
    for i, xref in enumerate(perm):
        raw = {k: v for k, v in xref["value"].items() if k != "nodos"}
        rid = "res_xref_" + hashlib.sha256(
            ("%s|%s|%d|%s" % (xref["source"], "rizin", i,
                              json.dumps(raw, sort_keys=True, default=str))).encode()
        ).hexdigest()[:16]
        perm_with_ids.append({**xref, "result_id": rid})
    assert producer_ids(rs) != producer_ids(perm), "los IDs SI dependen del orden"
    assert canon(rs) == canon(perm_with_ids), "canonical debe ser igual"
    print("TEST_1 PASS: permutacion ANTES de IDs -> canonical igual (IDs difieren)")


def test_2_permutation_after_ids_equal():
    rs = real_results()
    perm = list(reversed(rs))
    assert canon(rs) == canon(perm)
    print("TEST_2 PASS: permutacion DESPUES de IDs -> canonical igual")


def test_3_same_multiplicity_equal():
    rs = real_results()[:5]
    assert canon(rs) == canon(list(rs))
    assert canon(rs) == canon(list(reversed(rs)))
    print("TEST_3 PASS: misma multiplicidad -> igual independientemente del orden")


def test_4_multiplicity_changes():
    rs = real_results()[:5]
    dup = rs + [rs[0]]
    assert canon(rs) != canon(dup)
    print("TEST_4 PASS: distinta multiplicidad -> desigual")


def test_5_semantic_field_changes():
    rs = real_results()[:5]
    changed = [dict(r) for r in rs]
    changed[0] = {**changed[0], "value": {**changed[0]["value"], "from": 999999}}
    assert canon(rs) != canon(changed)
    print("TEST_5 PASS: campo semantico (value) distinto -> desigual")


def test_6_volatile_metadata_ignored():
    rs = real_results()[:5]
    # timestamps y limitations difieren, contenido igual
    vol = []
    for k, r in enumerate(rs):
        r2 = {**r, "timestamp": "2020-01-01", "limitations": ["volatil-%d" % k]}
        vol.append(r2)
    assert canon(rs) == canon(vol)
    print("TEST_6 PASS: metadatos volatiles no cambian la comparacion")


def test_7_missing_identity_abstains():
    incomplete = [dict(r) for r in real_results()[:3]]
    incomplete.append({k: v for k, v in incomplete[0].items() if k != "result_id"})
    st, c = machine._canon_obs(incomplete)
    assert st == "incomplete" and c is None
    print("TEST_7 PASS: resultado sin result_id -> abstencion (incomplete)")


def test_8_missing_null_types_no_accidental_equality():
    a = [{"result_id": "r1", "type": "xref", "value": None, "source": "/bin/ls",
          "scope": "binary", "tool": "rizin"}]
    b = [{"result_id": "r1", "type": "xref", "value": {}, "source": "/bin/ls",
          "scope": "binary", "tool": "rizin"}]
    c = [{"result_id": "r1", "type": "xref", "value": 0, "source": "/bin/ls",
          "scope": "binary", "tool": "rizin"}]
    assert canon(a) != canon(b), "None != {}"
    assert canon(b) != canon(c), "{} != 0"
    print("TEST_8 PASS: nulos/tipos incompatibles no producen equivalencias accidentales")


def test_9_prediction_canonical():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    # identical arms, esperado=NO_CHANGE -> no_separable (no sostenida)
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE",
        "comparar": "results", "canonico": True, "esperado": "NO_CHANGE",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "rizin"}}))
    assert r["experiment"]["veredicto"] == "no_separable", r
    # different arms, esperado=NO_CHANGE -> refutada
    r2 = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE",
        "comparar": "results", "canonico": True, "esperado": "NO_CHANGE",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r2["experiment"]["veredicto"] == "refutada", r2
    print("TEST_9 PASS: prediccion comparada en representacion canonica")


def test_10_non_canonical_unchanged():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TRACE
    r = machine.procesar_linea(json.dumps({
        "op": "experiment", "capability": "binary.xrefs",
        "question": "q", "prediction": "NO_CHANGE",
        "comparar": "results",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}))
    assert r["experiment"]["veredicto"] == "refutada", r
    print("TEST_10 PASS: modo no canonico conserva comportamiento (refutada)")


if __name__ == "__main__":
    test_1_permutation_before_ids_equal()
    test_2_permutation_after_ids_equal()
    test_3_same_multiplicity_equal()
    test_4_multiplicity_changes()
    test_5_semantic_field_changes()
    test_6_volatile_metadata_ignored()
    test_7_missing_identity_abstains()
    test_8_missing_null_types_no_accidental_equality()
    test_9_prediction_canonical()
    test_10_non_canonical_unchanged()
    print("ALL CANONICAL_COMPARISON_V2 TESTS PASS")
