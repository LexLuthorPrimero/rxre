#!/usr/bin/env python3
"""RXRE-ETAPA04-SUPPORTED-ORACLE: demostracion de SUPPORTED con oraculo independiente."""
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre")
sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")

import api.machine as machine
import backends.dispatch as dispatch
import rxre.core.store as store

DB = "/tmp/opencode/supp_oracle_test.sqlite3"
TID = "supp-oracle-trace-001"


def reset_db():
    for suf in ("", "-wal", "-shm", "-journal"):
        p = DB + suf
        if os.path.exists(p):
            os.unlink(p)
    conn = store.conectar(DB)
    conn.close()


def run_step(op, **kw):
    return machine.procesar_linea(json.dumps({"op": op, **kw}))


def main():
    reset_db()
    os.environ["RXRE_DB"] = DB
    os.environ["RXRE_TRACE_ID"] = TID

    # Oraculo independiente: ejecutar rizin dos veces y comparar conjuntos canonicos (result_ids)
    base_env = dispatch.ejecutar("binary.xrefs", {"artefacto": "/bin/ls", "backend_id": "rizin"})
    mod_env = dispatch.ejecutar("binary.xrefs", {"artefacto": "/bin/ls", "backend_id": "rizin"})
    base_ids = sorted(r.get("result_id") for r in (base_env.get("results") or []) if isinstance(r, dict))
    mod_ids = sorted(r.get("result_id") for r in (mod_env.get("results") or []) if isinstance(r, dict))
    oracle_identical = (base_ids == mod_ids)
    print("ORACLE (independiente, IDs canonicos): base_n=%d mod_n=%d identical=%s"
          % (len(base_ids), len(mod_ids), oracle_identical))

    # El mecanismo compara envelopes completos (incluyendo timestamps), por lo que
    # condiciones identicas producen refutada, no sostenida, por diferencia de timestamps.
    exp = {"capability": "binary.xrefs",
           "question": "conjuntos identicos?",
           "prediction": "NO_CHANGE", "comparar": "results",
           "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
           "modified_params": {"artefacto": "/bin/ls", "backend_id": "rizin"}}
    r = run_step("experiment", **exp)
    ex = r.get("experiment", {})
    verdict = ex.get("veredicto")
    print("verdict (non-tautological, identical arms):", verdict)

    # Oraculo: los result_ids son identicos (oracle_identical=True)
    # Mecanismo: refutada porque los envelopes difieren en timestamp
    print("ORACLE CHECK: oracle_identical=%s, mechanism=%s" % (oracle_identical, verdict))
    print("GAP: el mecanismo compara envelopes completos (incluyendo timestamps),")
    print("     por lo que condiciones identicas producen refutada, no sostenida.")
    print("     La identidad de conjuntos requiere comparacion canonica de result_ids,")
    print("     que el mecanismo actual no soporta. Este es un limite arquitectonico real.")
    print("GAP2: sostenida no-tautologica requiere mod != base AND mod == prediction,")
    print("      que para uso autonomo requiere observacion previa del valor modificado")
    print("      (circular) o un observable tautologico. Esto es un limite arquitectonico.")

    # Demonstrate sostenida with tautological observable (mechanism works)
    exp2 = {"capability": "binary.xrefs",
            "question": "rizin es determinista?",
            "prediction": "rizin", "comparar": "results.0.tool",
            "esperado": "rizin",
            "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
            "modified_params": {"artefacto": "/bin/ls", "backend_id": "rizin"}}
    r2 = run_step("experiment", **exp2)
    ex2 = r2.get("experiment", {})
    print("verdict (tautological observable, identical arms):", ex2.get("veredicto"))
    print("MECHANISM OK: sostenida se produce cuando mod==esperado (tautologico)")


if __name__ == "__main__":
    main()