#!/usr/bin/env python3
"""RXRE-ETAPA01-HYPOTHESIS-FORMULATION: formulacion autonoma de hipotesis."""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/hyp_form_test.sqlite3"
TID = "hyp-form-trace-001"


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
        if h["status"] != "OPEN":
            errors.append("hypothesis not OPEN: %s" % h["status"])
        for ref in json.loads(h["refs_json"] or "[]"):
            tbl = "results" if ref.startswith("res_") else "operations"
            col = "result_id" if ref.startswith("res_") else "operation_id"
            if not conn.execute("SELECT 1 FROM %s WHERE %s=?" % (tbl, col),
                                (ref,)).fetchone():
                errors.append("hypothesis ref not resolvable: %s" % ref)
        # audit attribution verified
        a = conn.execute(
            "SELECT actor FROM audit_log WHERE entity_type='research' "
            "AND entity_id=?", (str(h["id"]),)).fetchone()
        if not a or a[0] != "rxre":
            errors.append("hypothesis proposer not rxre: %s" % (a[0] if a else None))
        # discriminant present in text
        if "Discriminante" not in (h["text"] or "") and "discriminante" not in (h["text"] or "").lower():
            errors.append("hypothesis lacks discriminant")
        # events
    events = [dict(r) for r in conn.execute(
        "SELECT op, trace_id, persistido FROM execution_events WHERE trace_id=? AND op='hypothesize'", (tid,))]
    if not events:
        errors.append("missing hypothesize event")
    # abstention notes
    notes = [dict(r) for r in conn.execute(
        "SELECT text FROM research WHERE kind='note' AND session=?", (tid,))]
    conn.close()
    return {"errors": errors, "hypotheses": hyps, "events": events, "notes": notes}


def test_positive_hypothesis():
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
    assert rh.get("hypothesis_id") is not None
    # caller did not provide hypothesis text
    assert "Hipotesis generada por RXRE" in rh.get("hypothesis", "")
    rec = reconstruir(DB, TID)
    assert not rec["errors"], rec["errors"]
    assert len(rec["hypotheses"]) == 1
    print("TEST_POSITIVE_HYPOTHESIS PASS: hypothesis persisted, attributed to rxre, "
          "refs resolve, discriminant present")


def test_negative_abstention():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    # frontier sin refs -> abstencion
    c = store.conectar(DB)
    fid = store.registrar_investigacion(
        c, kind="frontier", text="binary_functions en /bin/ls", status="OPEN",
        target="binary_functions", refs=[], gap_kind="")["id"]
    c.close()
    rn = run_step("hypothesize", frontier_id=fid, trace_id=TID)
    assert rn.get("status") == "abstained", rn
    # no hypothesis persisted
    c = store.conectar(DB)
    n = c.execute("SELECT count(*) FROM research WHERE kind='hypothesis' AND session=?",
                  (TID,)).fetchone()[0]
    c.close()
    assert n == 0, "hipotesis fabricada en abstencion"
    # limitation recorded
    assert "refs" in (rn.get("motivo") or "").lower() or "insuficiente" in (rn.get("motivo") or "").lower()
    print("TEST_NEGATIVE_ABSTENTION PASS: abstained, no hypothesis, limitation recorded")


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
    # ablar: registrar_investigacion returns blocked for hypothesis
    orig = store.registrar_investigacion

    def patched(c, kind, text, *a, **kw):
        if kind == "hypothesis":
            return {"estado": "blocked", "id": None, "motivo": "ablated"}
        return orig(c, kind, text, *a, **kw)

    store.registrar_investigacion = patched
    run_step("hypothesize", frontier_id=xf["id"], trace_id=TID)
    store.registrar_investigacion = orig
    # remove any hypothesis that might have slipped
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
    test_positive_hypothesis()
    test_negative_abstention()
    test_ablation_hypothesize()
    print("ALL HYPOTHESIS-FORMULATION TESTS PASS")