#!/usr/bin/env python3
"""RXRE-ETAPA03: mision integral autonoma con continuacion adaptativa."""
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/mission_int_test.sqlite3"
TID = "mission-int-trace-001"


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
    ops = [r[0] for r in conn.execute(
        "SELECT DISTINCT op FROM execution_events WHERE trace_id=?", (tid,))]
    for req in ("discover", "hypothesize", "select", "select_experiment_predictive", "saturate", "continuation"):
        if req not in ops:
            errors.append("missing event op: %s" % req)
    for op in ("hypothesize", "continuation", "experiment", "saturate", "select", "select_experiment_predictive"):
        n = conn.execute("SELECT count(*) FROM execution_events WHERE trace_id=? AND op=?", (tid, op)).fetchone()[0]
        if n < 2:
            errors.append("expected >=2 events for %s, got %d" % (op, n))
    nhyp = conn.execute("SELECT count(*) FROM research WHERE kind='hypothesis' AND session=?", (tid,)).fetchone()[0]
    nclaim = conn.execute("SELECT count(*) FROM research WHERE kind='claim' AND session=?", (tid,)).fetchone()[0]
    if nhyp < 2:
        errors.append("expected >=2 hypotheses, got %d" % nhyp)
    if nclaim < 2:
        errors.append("expected >=2 claims, got %d" % nclaim)
    cont_notes = [dict(r) for r in conn.execute(
        "SELECT id, text FROM research WHERE kind='note' AND session=? AND text LIKE 'continuation:%'", (tid,))]
    if len(cont_notes) < 2:
        errors.append("expected >=2 continuation notes, got %d" % len(cont_notes))
    # causal link: iter1 continuation note has next_frontier; iter2 hypothesize event has caused_by_continuation_id
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
    missions = [dict(r) for r in conn.execute("SELECT mission_id, status FROM missions")]
    if not missions:
        errors.append("no mission created")
    notes = [dict(r) for r in conn.execute("SELECT text FROM research WHERE kind='note' AND session=?", (tid,))]
    trace_notes = [n for n in notes if "investigate:" in (n.get("text") or "")]
    if not trace_notes:
        errors.append("no investigate trace note persisted")
    conn.close()
    return {"errors": errors, "ops": ops, "missions": missions, "trace_notes": trace_notes,
            "cont_notes": cont_notes, "nhyp": nhyp, "nclaim": nclaim}


def test_integral_mission():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("investigate", artefacto="/bin/ls", trace_id=TID)
    assert r.get("status") == "ok", r
    ad = r.get("autonomous_decisions", [])
    assert "continuation_decision (ABSTAIN)" in ad
    trace = r.get("trace", [])
    assert len(trace) == 9, "expected 9 steps, got %d" % len(trace)
    for t in trace:
        assert t.get("status") in ("ok", "abstained", "empty"), t
    rec = reconstruir(DB, TID)
    assert not rec["errors"], rec["errors"]
    c = store.conectar(DB)
    ms = [dict(x) for x in c.execute("SELECT mission_id,status FROM missions")]
    c.close()
    assert ms and ms[0]["status"] != "COMPLETED", ms
    print("TEST_INTEGRAL_MISSION PASS: continuation ABSTAIN, reconstruction 0 errors, "
          "mission not falsely completed, ops=%s, hyps=%d, claims=%d, cont_notes=%d"
          % (rec["ops"], rec["nhyp"], rec["nclaim"], len(rec["cont_notes"])))


def test_no_manual_id_passing():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("investigate", artefacto="/bin/ls", trace_id=TID)
    assert r.get("status") == "ok"
    assert r.get("mission_id")
    assert r.get("hypothesis_id")
    print("TEST_NO_MANUAL_ID_PASSING PASS: IDs extracted internally")


def test_adversarial_invalid_artifact():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    r = run_step("investigate", artefacto="/nonexistent/binary", trace_id=TID)
    assert r.get("status") in ("blocked", "invalid_input", "error"), r.get("status")
    disc = [t for t in r.get("trace", []) if t.get("step") == "discover"][0]
    assert disc.get("status") in ("blocked", "invalid_input", "error"), disc
    print("TEST_ADVERSARIAL_INVALID_ARTIFACT PASS: status=%s" % r.get("status"))


def test_ablation_hypothesize_in_mission():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    orig = store.registrar_investigacion

    def patched(c, kind, text, *a, **kw):
        if kind == "hypothesis":
            return {"estado": "blocked", "id": None, "motivo": "ablated"}
        return orig(c, kind, text, *a, **kw)

    store.registrar_investigacion = patched
    r = run_step("investigate", artefacto="/bin/ls", trace_id=TID)
    store.registrar_investigacion = orig
    hyp_step = [t for t in r.get("trace", []) if t.get("step") == "hypothesize"][0]
    assert hyp_step.get("status") in ("abstained", "blocked", "empty", "error"), hyp_step
    print("TEST_ABLATION_HYPOTHESIZE_IN_MISSION PASS: hypothesize abstained -> %s" % hyp_step.get("status"))


if __name__ == "__main__":
    test_integral_mission()
    test_no_manual_id_passing()
    test_adversarial_invalid_artifact()
    test_ablation_hypothesize_in_mission()
    print("ALL MISSION-INTEGRATION TESTS PASS")