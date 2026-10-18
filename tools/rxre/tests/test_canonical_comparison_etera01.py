#!/usr/bin/env python3
"""RXRE-CANONICAL-EXPERIMENT: comparacion canonica de conjuntos de resultados."""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import backends.dispatch as dispatch

DB = "/tmp/opencode/canon_test.sqlite3"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    import rxre.core.store as store
    conn = store.conectar(DB)
    conn.close()


def run_step(op, **kw):
    return machine.procesar_linea(json.dumps({"op": op, **kw}))


def test_canonical_equal_volatile_metadata():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = "canon-t1"
    # rizin vs radare2 (sets differ) -> refutada in canonico
    exp = {"capability": "binary.xrefs",
           "question": "conjuntos identicos?", "prediction": "NO_CHANGE",
           "comparar": "results", "canonico": True,
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}
    r = run_step("experiment", **exp)
    assert r["experiment"]["veredicto"] == "refutada", r
    print("TEST_CANONICAL_DIFFERENT_SETS PASS: refutada (conjuntos difieren)")


def test_canonical_identical_sets():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = "canon-t2"
    # rizin vs rizin (sets identical) -> no_separable (not sostenida)
    exp = {"capability": "binary.xrefs",
           "question": "conjuntos identicos?", "prediction": "NO_CHANGE",
           "comparar": "results", "canonico": True,
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "rizin"}}
    r = run_step("experiment", **exp)
    assert r["experiment"]["veredicto"] == "no_separable", r
    print("TEST_CANONICAL_IDENTICAL_SETS PASS: no_separable (conjuntos identicos)")


def test_canonical_identical_not_sostenida():
    # Identical arms with esperado=NO_CHANGE -> no_separable, NOT sostenida
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = "canon-t3"
    exp = {"capability": "binary.xrefs",
           "question": "conjuntos identicos?", "prediction": "NO_CHANGE",
           "comparar": "results", "canonico": True, "esperado": "NO_CHANGE",
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "rizin"}}
    r = run_step("experiment", **exp)
    assert r["experiment"]["veredicto"] == "no_separable", r
    print("TEST_CANONICAL_IDENTICAL_NOT_SOSTENIDA PASS: no_separable (no sostenida)")


def test_canonical_missing_identity():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = "canon-t4"
    # missing path -> no_observable
    exp = {"capability": "binary.xrefs",
           "question": "missing", "prediction": "x",
           "comparar": "results.999.value", "canonico": True,
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}
    r = run_step("experiment", **exp)
    assert r["experiment"]["veredicto"] == "no_observable", r
    print("TEST_CANONICAL_MISSING_IDENTITY PASS: no_observable")


def test_canonical_sostenida_tautological():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = "canon-t5"
    # tautological observable (backend name) with different arms -> sostenida
    exp = {"capability": "binary.xrefs",
           "question": "backend name", "prediction": "radare2",
           "comparar": "results.0.tool", "canonico": True, "esperado": "radare2",
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}
    r = run_step("experiment", **exp)
    assert r["experiment"]["veredicto"] == "sostenida", r
    print("TEST_CANONICAL_SOSTENIDA_TAUTOLOGICAL PASS: sostenida")


def test_non_canonical_unchanged():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = "canon-t6"
    # non-canonico: same as before (refutada due to timestamps)
    exp = {"capability": "binary.xrefs",
           "question": "q", "prediction": "NO_CHANGE",
           "comparar": "results",
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"}}
    r = run_step("experiment", **exp)
    assert r["experiment"]["veredicto"] == "refutada", r
    print("TEST_NON_CANONICAL_UNCHANGED PASS: refutada (sin cambios)")


def test_canonical_oracle_independent():
    # Oracle: compare canonical result_ids independently
    base_env = dispatch.ejecutar("binary.xrefs", {"artefacto": "/bin/ls", "backend_id": "rizin"})
    mod_env = dispatch.ejecutar("binary.xrefs", {"artefacto": "/bin/ls", "backend_id": "radare2"})
    base_ids = sorted(r.get("result_id") for r in (base_env.get("results") or []) if isinstance(r, dict) and r.get("result_id"))
    mod_ids = sorted(r.get("result_id") for r in (mod_env.get("results") or []) if isinstance(r, dict) and r.get("result_id"))
    assert base_ids != mod_ids, "oracle: sets should differ"
    print("TEST_CANONICAL_ORACLE_INDEPENDENT PASS: oracle confirms sets differ (base_n=%d mod_n=%d)" % (len(base_ids), len(mod_ids)))


if __name__ == "__main__":
    test_canonical_equal_volatile_metadata()
    test_canonical_identical_sets()
    test_canonical_identical_not_sostenida()
    test_canonical_missing_identity()
    test_canonical_sostenida_tautological()
    test_non_canonical_unchanged()
    test_canonical_oracle_independent()
    print("ALL CANONICAL-COMPARISON TESTS PASS")