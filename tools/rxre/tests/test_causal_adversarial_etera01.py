#!/usr/bin/env python3
"""RXRE-ETAPA01-CAUSAL-ADVERSARIAL: validacion de incertidumbre.

No modifica el sistema. Ejecuta escenarios desfavorables (REFUTED,
NOT_DETERMINED, referencia invalida, evidencia contradictoria) y verifica
que RXRE distingue SUPPORTED/REFUTED/NOT_DETERMINED, no fabrica enlaces y
reconstruye el resultado desde otro proceso.
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import rxre.core.store as store

DB = "/tmp/opencode/causal_adv.sqlite3"
TID = "causal-adv-trace-001"


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
        "SELECT op FROM execution_events WHERE trace_id=?", (tid,))]
    ops = {e["op"] for e in events}
    for req in ("discover", "experiment"):
        if req not in ops:
            errors.append("missing step: %s" % req)
    rows = [dict(r) for r in conn.execute(
        "SELECT id, kind, status, refs_json FROM research WHERE session=?",
        (tid,))]
    claims = [r for r in rows if r["kind"] == "claim"]
    hypotheses = [r for r in rows if r["kind"] == "hypothesis"]
    # estados presentes
    statuses = {c["status"] for c in claims}
    # refs resuelven
    for r in rows:
        for ref in json.loads(r["refs_json"] or "[]"):
            if ref.startswith("res_"):
                tbl, col = "results", "result_id"
            elif ref.startswith("op_"):
                tbl, col = "operations", "operation_id"
            else:
                errors.append("research id=%s ref con prefijo no citable: %s"
                              % (r["id"], ref))
                continue
            if not conn.execute("SELECT 1 FROM %s WHERE %s=?" % (tbl, col),
                                (ref,)).fetchone():
                errors.append("research id=%s ref no resuelve: %s" % (r["id"], ref))
    # invalid ref must not appear anywhere
    allrefs = []
    for r in rows:
        allrefs.extend(json.loads(r["refs_json"] or "[]"))
    if "res_does_not_exist_123" in allrefs:
        errors.append("referencia invalida fabricada como enlace")
    conn.close()
    return {"errors": errors, "statuses": statuses, "n_claims": len(claims),
            "n_hypotheses": len(hypotheses), "claims": claims}


def main():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID

    # 1. discover (observacion)
    r = run_step("discover", artefacto="/bin/ls")
    assert r.get("status") == "ok", r

    # 2. Experimento SUPPORTED (prediccion coincide)
    r1 = run_step("experiment", capability="binary.callgraph",
                  question="status es ok en ambos brazos?",
                  prediction="ok", comparar="status", esperado="ok",
                  baseline_params={"artefacto": "/bin/ls", "backend_id": "radare2"},
                  modified_params={"artefacto": "/bin/ls", "backend_id": "radare2"})
    assert r1.get("status") == "ok", r1
    assert r1["experiment"]["veredicto"] == "sostenida", r1

    # 3. Experimento REFUTED (prediccion no coincide; evidencia contradictoria)
    r2 = run_step("experiment", capability="binary.callgraph",
                  question="status sera NOPE?",
                  prediction="ok", comparar="status", esperado="NOPE",
                  refs=["res_does_not_exist_123"],  # referencia invalida
                  baseline_params={"artefacto": "/bin/ls", "backend_id": "radare2"},
                  modified_params={"artefacto": "/bin/ls", "backend_id": "radare2"})
    assert r2.get("status") == "ok", r2
    assert r2["experiment"]["veredicto"] == "refutada", r2

    # 4. Experimento NOT_DETERMINED (observable inexistente)
    r3 = run_step("experiment", capability="binary.callgraph",
                  question="observable inexistente",
                  prediction="ok", comparar="results.999.value",
                  baseline_params={"artefacto": "/bin/ls", "backend_id": "radare2"},
                  modified_params={"artefacto": "/bin/ls", "backend_id": "radare2"})
    assert r3.get("status") == "ok", r3
    assert r3["experiment"]["veredicto"] in ("no_observable", "no_separable"), r3

    rec = reconstruir(DB, TID)
    print("estados de conclusion observados:", sorted(rec["statuses"]))
    print("n_claims=%d n_hypotheses=%d" % (rec["n_claims"], rec["n_hypotheses"]))
    assert not rec["errors"], rec["errors"]
    # los tres estados deben estar presentes
    assert "SUPPORTED" in rec["statuses"], "falta SUPPORTED"
    assert "REFUTED" in rec["statuses"], "falta REFUTED"
    assert "NOT_DETERMINED" in rec["statuses"], "falta NOT_DETERMINED"
    # evidencia preservada: claims con refs no vacios para supported/refuted
    for c in rec["claims"]:
        refs = json.loads(c["refs_json"])
        if c["status"] in ("SUPPORTED", "REFUTED"):
            assert len(refs) > 0, "claim %s sin evidencia" % c["status"]
    # invalid ref not fabricated
    assert "res_does_not_exist_123" not in json.dumps(rec["claims"])
    print("ADVERSARIAL VALIDATION PASS: SUPPORTED/REFUTED/NOT_DETERMINED "
          "distinguidos, evidencia preservada, sin enlaces fabricados")


if __name__ == "__main__":
    main()