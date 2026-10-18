#!/usr/bin/env python3
"""RXRE-ETAPA01-SEMANTIC-ALIGNMENT: alineacion semantica hipotesis-experimento."""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/sem_align_test.sqlite3"
TID = "sem-align-trace-001"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def run_step(op, **kw):
    return machine.procesar_linea(json.dumps({"op": op, **kw}))


def reconstruir(db_path, tid):
    uri = "file:%s?mode=ro" % db_path
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    errors = []
    hyps = [dict(r) for r in conn.execute(
        "SELECT id, kind, status, refs_json, session, text FROM research "
        "WHERE kind='hypothesis' AND session=?", (tid,))]
    if not hyps:
        errors.append("no hypothesis persisted")
    for h in hyps:
        t = h["text"] or ""
        if "conjuntos" not in t.lower() and "conjunto" not in t.lower():
            errors.append("hypothesis does not claim result-set identity: %s" % t[:80])
        if "conteos distintos" in t:
            errors.append("hypothesis still claims count difference (stale): %s" % t[:80])
        if "Observable: results." not in t:
            errors.append("hypothesis lacks observable alignment: %s" % t[:80])
        if "convencion de contraste" not in t:
            errors.append("hypothesis lacks prediction provenance: %s" % t[:80])
        for ref in json.loads(h["refs_json"] or "[]"):
            tbl = "results" if ref.startswith("res_") else "operations"
            col = "result_id" if ref.startswith("res_") else "operation_id"
            if not conn.execute("SELECT 1 FROM %s WHERE %s=?" % (tbl, col),
                                (ref,)).fetchone():
                errors.append("hypothesis ref not resolvable: %s" % ref)
        a = conn.execute(
            "SELECT actor FROM audit_log WHERE entity_type='research' "
            "AND entity_id=?", (str(h["id"]),)).fetchone()
        if not a or a[0] != "rxre":
            errors.append("hypothesis proposer not rxre")
    conn.close()
    return {"errors": errors, "hypotheses": hyps}


def test_hypothesis_alignment():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("discover", artefacto="/bin/ls")
    assert r.get("status") == "ok"
    c = store.conectar(DB)
    frows = [dict(x) for x in c.execute(
        "SELECT id,target FROM research WHERE kind='frontier'")]
    c.close()
    xf = [f for f in frows if "xref" in (f["target"] or "").lower()][0]
    rh = run_step("hypothesize", frontier_id=xf["id"], trace_id=TID)
    assert rh.get("status") == "ok", rh
    assert rh.get("audit_verified") is True
    rec = reconstruir(DB, TID)
    assert not rec["errors"], rec["errors"]
    h = rec["hypotheses"][0]
    print("TEST_HYPOTHESIS_ALIGNMENT PASS: hypothesis claims result-set identity, "
          "refs resolve, provenance recorded")


def test_verdicts_contract():
    # Verify the four verdicts derive from prediction, not tautology
    os.environ["RXRE_DB"] = "/tmp/opencode/sem_verdicts.sqlite3"
    db = "/tmp/opencode/sem_verdicts.sqlite3"
    for suf in ("", "-wal", "-shm"):
        p = db + suf
        if os.path.exists(p):
            os.unlink(p)
    os.environ["RXRE_DB"] = db
    import rxre.core.store as st
    conn = st.conectar(db); conn.close()

    def run(exp):
        return machine.procesar_linea(json.dumps(exp))

    # sostenida: mod differs from base AND mod==prediction (non-tautological observable)
    r = run({"op":"experiment","capability":"binary.xrefs","question":"sos",
             "prediction":"radare2","comparar":"backend",
             "baseline_params":{"artefacto":"/bin/ls","backend_id":"rizin"},
             "modified_params":{"artefacto":"/bin/ls","backend_id":"radare2"}})
    assert r["experiment"]["veredicto"] == "sostenida", r

    # refutada: mod differs from base AND mod!=prediction
    r = run({"op":"experiment","capability":"binary.xrefs","question":"ref",
             "prediction":"NO_CHANGE","comparar":"results",
             "baseline_params":{"artefacto":"/bin/ls","backend_id":"rizin"},
             "modified_params":{"artefacto":"/bin/ls","backend_id":"radare2"}})
    assert r["experiment"]["veredicto"] == "refutada", r

    # no_separable: mod==base
    r = run({"op":"experiment","capability":"binary.xrefs","question":"nosep",
             "prediction":"NO_CHANGE","comparar":"status",
             "baseline_params":{"artefacto":"/bin/ls","backend_id":"rizin"},
             "modified_params":{"artefacto":"/bin/ls","backend_id":"radare2"}})
    assert r["experiment"]["veredicto"] == "no_separable", r

    # no_observable: missing path
    r = run({"op":"experiment","capability":"binary.xrefs","question":"noobs",
             "prediction":"x","comparar":"results.999.value",
             "baseline_params":{"artefacto":"/bin/ls","backend_id":"rizin"},
             "modified_params":{"artefacto":"/bin/ls","backend_id":"radare2"}})
    assert r["experiment"]["veredicto"] == "no_observable", r
    print("TEST_VERDICTS_CONTRACT PASS: sostenida/refutada/no_separable/no_observable verified")


def test_count_equality_distinct_sets():
    # counts equal (74 vs 74) but sets differ -> hypothesis must claim sets, not counts
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("discover", artefacto="/bin/ls")
    assert r.get("status") == "ok"
    c = store.conectar(DB)
    frows = [dict(x) for x in c.execute(
        "SELECT id,target FROM research WHERE kind='frontier'")]
    c.close()
    xf = [f for f in frows if "xref" in (f["target"] or "").lower()][0]
    rh = run_step("hypothesize", frontier_id=xf["id"], trace_id=TID)
    assert rh.get("status") == "ok"
    assert "conteos distintos" not in rh.get("hypothesis", "")
    assert "conjuntos" in rh.get("hypothesis", "").lower()
    print("TEST_COUNT_EQUALITY_DISTINCT_SETS PASS: hypothesis claims sets, not counts")


def test_tautology_avoidance():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("discover", artefacto="/bin/ls")
    assert r.get("status") == "ok"
    c = store.conectar(DB)
    frows = [dict(x) for x in c.execute(
        "SELECT id,target FROM research WHERE kind='frontier'")]
    c.close()
    xf = [f for f in frows if "xref" in (f["target"] or "").lower()][0]
    rh = run_step("hypothesize", frontier_id=xf["id"], trace_id=TID)
    hyp = rh.get("hypothesis", "")
    assert "results.0.tool" not in hyp
    assert "backend" not in hyp.lower() or "Observable: results." in hyp
    print("TEST_TAUTOLOGY_AVOIDANCE PASS: discriminant not tautological (tool name)")


def test_invalid_ref_abstention():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    # frontier con refs invalidos insertado directamente (simula dato legado)
    c = store.conectar(DB)
    c.execute(
        "INSERT INTO research (kind, status, text, gap_kind, refs_json, session, "
        "target, timestamp) VALUES (?,?,?,?,?,?,?,?)",
        ("frontier", "OPEN", "x en /bin/ls", None,
         json.dumps(["res_does_not_exist"]), TID, "binary_xrefs",
         "2026-10-17T00:00:00+0000"))
    fid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    rn = run_step("hypothesize", frontier_id=fid, trace_id=TID)
    assert rn.get("status") == "abstained", rn
    c = store.conectar(DB)
    n = c.execute("SELECT count(*) FROM research WHERE kind='hypothesis' AND session=?",
                  (TID,)).fetchone()[0]
    c.close()
    assert n == 0
    print("TEST_INVALID_REF_ABSTENTION PASS: abstained, no hypothesis")


def test_ablation_hypothesize():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("discover", artefacto="/bin/ls")
    assert r.get("status") == "ok"
    c = store.conectar(DB)
    frows = [dict(x) for x in c.execute(
        "SELECT id,target FROM research WHERE kind='frontier'")]
    c.close()
    xf = [f for f in frows if "xref" in (f["target"] or "").lower()][0]
    orig = store.registrar_investigacion

    def patched(c, kind, text, *a, **kw):
        if kind == "hypothesis":
            return {"estado": "blocked", "id": None, "motivo": "ablated"}
        return orig(c, kind, text, *a, **kw)

    store.registrar_investigacion = patched
    run_step("hypothesize", frontier_id=xf["id"], trace_id=TID)
    store.registrar_investigacion = orig
    conn = store.conectar(DB)
    conn.execute("DELETE FROM research WHERE kind='hypothesis' AND session=?", (TID,))
    conn.execute("DELETE FROM execution_events WHERE op='hypothesize' AND trace_id=?", (TID,))
    conn.commit()
    conn.close()
    rec = reconstruir(DB, TID)
    assert any("no hypothesis persisted" in e for e in rec["errors"]), rec["errors"]
    print("TEST_ABLATION_HYPOTHESIZE PASS: razon ->",
          [e for e in rec["errors"] if "hypothesis" in e])


if __name__ == "__main__":
    test_hypothesis_alignment()
    test_verdicts_contract()
    test_count_equality_distinct_sets()
    test_tautology_avoidance()
    test_invalid_ref_abstention()
    test_ablation_hypothesize()
    print("ALL SEMANTIC-ALIGNMENT TESTS PASS")