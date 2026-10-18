#!/usr/bin/env python3
"""RXRE-ETAPA04-ALTERNATIVE-CONTINUATION: continuacion con alternativa real."""
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/alt_cont_test.sqlite3"
TID = "alt-cont-trace-001"


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
    ncont = conn.execute("SELECT count(*) FROM execution_events WHERE trace_id=? AND op='continuation'", (tid,)).fetchone()[0]
    if ncont < 2:
        errors.append("expected >=2 continuation events, got %d" % ncont)
    nhyp = conn.execute("SELECT count(*) FROM research WHERE kind='hypothesis' AND session=?", (tid,)).fetchone()[0]
    if nhyp < 2:
        errors.append("expected >=2 hypotheses, got %d" % nhyp)
    nclaim = conn.execute("SELECT count(*) FROM research WHERE kind='claim' AND session=?", (tid,)).fetchone()[0]
    if nclaim < 2:
        errors.append("expected >=2 claims, got %d" % nclaim)
    cont_notes = [dict(r) for r in conn.execute(
        "SELECT id, text FROM research WHERE kind='note' AND session=? AND text LIKE 'continuation:%'", (tid,))]
    if len(cont_notes) < 2:
        errors.append("expected >=2 continuation notes, got %d" % len(cont_notes))
    causal_ok = False
    for n in cont_notes:
        if "iter=1" in (n.get("text") or "") and "CONTINUE" in (n.get("text") or ""):
            m = re.search(r"next_frontier=(\d+)", n.get("text") or "")
            if m:
                for he in conn.execute("SELECT limitations FROM execution_events WHERE trace_id=? AND op='hypothesize'", (tid,)):
                    if "caused_by_continuation_id=%s" % n["id"] in (he["limitations"] or ""):
                        causal_ok = True
    if not causal_ok:
        errors.append("causal link CONTINUE(iter1)->iter2 not verifiable")
    ops = [r[0] for r in conn.execute("SELECT DISTINCT op FROM execution_events WHERE trace_id=?", (tid,))]
    for req in ("discover", "hypothesize", "select", "select_experiment_predictive", "saturate", "continuation"):
        if req not in ops:
            errors.append("missing event op: %s" % req)
    conn.close()
    return {"errors": errors, "ops": ops, "cont_notes": cont_notes, "nhyp": nhyp, "nclaim": nclaim}


def test_alternative_continuation():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("investigate", artefacto="/bin/ls", trace_id=TID)
    assert r.get("status") == "ok", r
    ad = r.get("autonomous_decisions", [])
    assert "continuation_decision (ABSTAIN)" in ad
    trace = r.get("trace", [])
    assert len(trace) == 9, "expected 9 steps, got %d" % len(trace)
    rec = reconstruir(DB, TID)
    assert not rec["errors"], rec["errors"]
    # verify alternative is genuine: second hypothesis has real refs
    c = store.conectar(DB); c.row_factory = sqlite3.Row
    hyps = [dict(x) for x in c.execute(
        "SELECT id, target, refs_json FROM research WHERE kind='hypothesis' AND session=?", (TID,))]
    assert all(len(json.loads(h["refs_json"] or "[]")) > 0 for h in hyps), "hypothesis without real refs"
    # second hypothesis (callgraph) refs must be subset of callgraph frontier refs
    cg_frontier = c.execute(
        "SELECT refs_json FROM research WHERE kind='frontier' AND session=? AND target='binary_callgraph'", (TID,)).fetchone()
    assert cg_frontier is not None
    cg_refs = set(json.loads(cg_frontier["refs_json"] or "[]"))
    # find iter2 hypothesis via caused_by link
    hyp2_id = None
    for he in c.execute("SELECT limitations FROM execution_events WHERE trace_id=? AND op='hypothesize'", (TID,)):
        if "caused_by_continuation_id" in (he["limitations"] or ""):
            # the hypothesis created in this event's handler; find by max id
            pass
    # simpler: the second hypothesis has target binary_callgraph
    hyp2 = [h for h in hyps if h["target"] == "binary_callgraph"]
    assert hyp2, "no second hypothesis from callgraph frontier"
    hyp2_refs = set(json.loads(hyp2[0]["refs_json"] or "[]"))
    assert hyp2_refs.issubset(cg_refs), "alternative hypothesis refs not from real evidence"
    c.close()
    # causal link verified by reconstruir
    assert len(rec["cont_notes"]) >= 2
    iter1 = [n for n in rec["cont_notes"] if "iter=1" in (n.get("text") or "")]
    iter2 = [n for n in rec["cont_notes"] if "iter=2" in (n.get("text") or "")]
    assert iter1 and "CONTINUE" in iter1[0]["text"]
    assert iter2 and "ABSTAIN" in iter2[0]["text"]
    print("TEST_ALTERNATIVE_CONTINUATION PASS: 2 iterations, causal link verified, "
          "alternative genuine (refs subset of frontier), abstention present")


def test_abstention_no_alternative():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    orig_discover = machine._handle_discover

    def patched_discover(params):
        resp = orig_discover(params)
        try:
            conn = store.conectar(DB)
            conn.execute("DELETE FROM research WHERE kind='frontier' AND target='binary_callgraph'")
            conn.commit()
            conn.close()
        except Exception:
            pass
        return resp

    machine._handle_discover = patched_discover
    machine.HANDLERS["discover"] = patched_discover
    r = run_step("investigate", artefacto="/bin/ls", trace_id=TID)
    machine._handle_discover = orig_discover
    machine.HANDLERS["discover"] = orig_discover
    assert r.get("status") == "ok", r
    c = store.conectar(DB)
    nhyp = c.execute("SELECT count(*) FROM research WHERE kind='hypothesis' AND session=?", (TID,)).fetchone()[0]
    c.close()
    assert nhyp == 1, "expected 1 hypothesis (no alternative), got %d" % nhyp
    assert r.get("continuation_decision") == "ABSTAIN", r.get("continuation_decision")
    print("TEST_ABSTENTION_NO_ALTERNATIVE PASS: 1 hypothesis, abstained (no alternative)")


def test_causal_link_ablation():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("investigate", artefacto="/bin/ls", trace_id=TID)
    assert r.get("status") == "ok"
    conn = store.conectar(DB)
    conn.execute("UPDATE execution_events SET limitations='[]' WHERE op='hypothesize' AND limitations LIKE '%caused_by_continuation_id%'")
    conn.commit()
    conn.close()
    rec = reconstruir(DB, TID)
    assert any("causal link" in e for e in rec["errors"]), rec["errors"]
    print("TEST_CAUSAL_LINK_ABLATION PASS: razon ->", [e for e in rec["errors"] if "causal" in e])


if __name__ == "__main__":
    test_alternative_continuation()
    test_abstention_no_alternative()
    test_causal_link_ablation()
    print("ALL ALTERNATIVE-CONTINUATION TESTS PASS")