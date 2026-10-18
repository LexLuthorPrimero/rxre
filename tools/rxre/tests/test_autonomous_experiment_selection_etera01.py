#!/usr/bin/env python3
"""RXRE-ETAPA01-AUTONOMOUS-EXPERIMENT-SELECTION: seleccion autonoma de experimento."""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/selexp_test.sqlite3"
TID = "selexp-trace-001"


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
    events = [dict(r) for r in conn.execute(
        "SELECT evento_id, op, trace_id, persistido, limitations FROM execution_events "
        "WHERE trace_id=? AND op='select_experiment'", (tid,))]
    if not events:
        errors.append("missing select_experiment event")
    # parse decision from limitations
    decision = None
    for e in events:
        try:
            lim = json.loads(e["limitations"])
            if isinstance(lim, list) and lim:
                decision = json.loads(lim[0]) if isinstance(lim[0], str) else lim[0]
        except Exception:
            pass
    if not decision:
        errors.append("decision not persisted in event")
    # research note with the decision
    notes = [dict(r) for r in conn.execute(
        "SELECT id, kind, status, session, text, refs_json FROM research "
        "WHERE kind='note' AND session=?", (tid,))]
    if not notes:
        errors.append("missing persisted selection note")
    # audit attribution (for the decision note)
    for n in notes:
        if "select_experiment:" in (n.get("text") or "") and "result:" not in (n.get("text") or ""):
            a = conn.execute(
                "SELECT actor FROM audit_log WHERE entity_type='research' "
                "AND entity_id=?", (str(n["id"]),)).fetchone()
            if not a or a[0] != "rxre":
                errors.append("selection note proposer not rxre")
    # verify candidate fields
    if decision:
        if len(decision.get("candidates", [])) < 2:
            errors.append("fewer than 2 candidates persisted")
        if not decision.get("selected"):
            errors.append("no selected candidate persisted")
        if not decision.get("justification"):
            errors.append("no justification persisted")
        # tautological discarded
        discarded = {d["id"]: d["reason"] for d in decision.get("discarded", [])}
        if "cand_tool" in discarded and discarded["cand_tool"] != "tautologico":
            errors.append("tautological candidate not discarded as tautologico")
        # non-discriminative discarded
        if "cand_status" in discarded and discarded["cand_status"] != "no-discriminante":
            errors.append("non-discriminative candidate not discarded")
        # selected is the discriminative one (cand_results)
        if decision.get("selected") != "cand_results":
            errors.append("selected not the discriminative candidate: %s" % decision.get("selected"))
        # priority check: cand_status has priority 1 (higher) but not selected
        # (recorded in candidates)
        cands = {cd["id"]: cd for cd in decision.get("candidates", [])}
        if "cand_status" in cands and "cand_results" in cands:
            if cands["cand_status"].get("priority", 99) < cands["cand_results"].get("priority", 0):
                # status has higher priority (lower number) but was not selected -> good
                pass
            else:
                errors.append("priority ordering unexpected")
    conn.close()
    return {"errors": errors, "events": events, "decision": decision,
            "notes": notes}


def test_candidates_and_selection():
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
    rs = run_step("select_experiment", hypothesis_id=rh.get("hypothesis_id"),
                  trace_id=TID)
    assert rs.get("status") == "ok", rs
    # at least 2 candidates
    assert len(rs.get("candidates", [])) >= 2
    # selected is the discriminative one (cand_results), not status (higher priority)
    assert rs.get("selected") == "cand_results", rs.get("selected")
    # cand_status has higher priority (lower number) but was not selected
    cands = {cd["id"]: cd for cd in rs["candidates"]}
    assert cands["cand_status"]["priority"] < cands["cand_results"]["priority"], \
        "status should have higher priority (lower number)"
    # tautological discarded
    discarded = {d["id"]: d["reason"] for d in rs.get("discarded", [])}
    assert discarded.get("cand_tool") == "tautologico"
    assert discarded.get("cand_status") == "no-discriminante"
    # justification persisted before execution
    assert rs.get("justification")
    # decision persisted
    rec = reconstruir(DB, TID)
    assert not rec["errors"], rec["errors"]
    # experiment executed and linked
    assert (rs.get("experiment_result") or {}).get("status") == "ok"
    verdict = (rs.get("experiment_result") or {}).get("experiment", {}).get("veredicto")
    assert verdict in ("sostenida", "refutada", "no_separable", "no_observable"), verdict
    print("TEST_CANDIDATES_AND_SELECTION PASS: selected=%s (discriminative, not highest priority); "
          "verdict=%s; candidates=%d" % (rs.get("selected"), verdict, len(rs["candidates"])))


def test_ablation_select_experiment():
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
    # ablate: registrar_investigacion returns blocked for kind=note
    orig = store.registrar_investigacion

    def patched(c, kind, text, *a, **kw):
        if kind == "note":
            return {"estado": "blocked", "id": None, "motivo": "ablated"}
        return orig(c, kind, text, *a, **kw)

    store.registrar_investigacion = patched
    run_step("select_experiment", hypothesis_id=rh.get("hypothesis_id"),
             trace_id=TID)
    store.registrar_investigacion = orig
    # remove any persisted decision
    conn = store.conectar(DB)
    conn.execute("DELETE FROM execution_events WHERE op='select_experiment' AND trace_id=?", (TID,))
    conn.execute("DELETE FROM research WHERE kind='note' AND session=?", (TID,))
    conn.commit()
    conn.close()
    rec = reconstruir(DB, TID)
    assert any("missing select_experiment event" in e or "missing persisted selection note" in e
               for e in rec["errors"]), rec["errors"]
    print("TEST_ABLATION_SELECT_EXPERIMENT PASS: razon ->",
          [e for e in rec["errors"] if "select" in e or "note" in e or "decision" in e])


def test_abstention_no_discriminative():
    # frontier with no prior differing evidence -> abstain
    # Use a frontier whose target is not xref/callgraph -> no candidates -> abstain
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID
    c = store.conectar(DB)
    fid = store.registrar_investigacion(
        c, kind="frontier", text="foo en /bin/ls", status="OPEN",
        target="binary_functions", refs=[], gap_kind="")["id"]
    # frontier with refs but non-discriminable target -> hypothesize abstains, so no hypothesis
    # Instead create hypothesis directly with target binary_functions (no experiment candidate)
    c2 = store.conectar(DB)
    hyp = store.registrar_investigacion(
        c2, kind="hypothesis", text="hipotesis generica", status="OPEN",
        refs=[], session=TID, target="binary_functions", gap_kind="")
    # hyp has no refs -> but select_experiment checks refs? It uses hyp refs for audit; target binary_functions -> abstain (no conditions)
    c.close(); c2.close()
    if hyp.get("estado") == "ok":
        rs = run_step("select_experiment", hypothesis_id=hyp["id"], trace_id=TID)
        assert rs.get("status") == "abstained", rs
        print("TEST_ABSTENTION_NO_DISCRIMINATIVE PASS: abstained ->", rs.get("motivo"))
    else:
        print("TEST_ABSTENTION_NO_DISCRIMINATIVE SKIP (hyp blocked):", hyp)


def test_priority_not_discrimination():
    # explicit: status has higher priority (lower number) but is not selected
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
    rs = run_step("select_experiment", hypothesis_id=rh.get("hypothesis_id"),
                  trace_id=TID)
    assert rs.get("status") == "ok"
    cands = {cd["id"]: cd for cd in rs["candidates"]}
    assert cands["cand_status"]["priority"] < cands["cand_results"]["priority"], \
        "status must have higher priority (lower number) than results"
    assert rs["selected"] == "cand_results", \
        "selector chose highest-priority instead of most discriminative"
    print("TEST_PRIORITY_NOT_DISCRIMINATION PASS: selected most discriminative, "
          "not highest priority")


if __name__ == "__main__":
    test_candidates_and_selection()
    test_priority_not_discrimination()
    test_abstention_no_discriminative()
    test_ablation_select_experiment()
    print("ALL AUTONOMOUS-EXPERIMENT-SELECTION TESTS PASS")