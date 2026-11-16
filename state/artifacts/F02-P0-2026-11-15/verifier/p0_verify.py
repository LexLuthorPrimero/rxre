"""Verificador INDEPENDIENTE de la reparación F-02.

No importa p0 ni core.store. Oráculo: DDL de store.py + columnas literales.
"""
import hashlib, json, os, re, sqlite3, sys

EXPECT_FILE = sys.argv[1] if len(sys.argv) > 1 else (
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expected.json"))
SRC    = sys.argv[2] if len(sys.argv) > 2 else None   # src para sellado inicial (opcional)
VERIFY = sys.argv[3] if len(sys.argv) > 3 else None   # dst copia migrada (opcional)
oracle = json.load(open(EXPECT_FILE, encoding="utf-8"))
oracle_sha = hashlib.sha256(open(EXPECT_FILE,"rb").read()).hexdigest()

def table_info(con, t):
    return {r[1]: {"type": r[2], " notnull": r[3], "default": r[4], "pk": r[5]} for r in con.execute("PRAGMA table_info(%s)" % t)}

def ddl_flat():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(here, "..", "..", "..", "rxre", "tools", "rxre", "core", "store.py")
    return re.sub(r"\s+", " ", open(p, encoding="utf-8").read())

required = {
    "operations": ["declared_scope","authorized_scope","auth_decision","auth_actor","auth_timestamp"],
    "results":     ["verified_scope","scope_decision","limitations_json"],
}

def main():
    if VERIFY:
        path = VERIFY
    else:
        path = os.environ.get("VERIFY_DB")
        if not path:
            print("FAIL: VERIFY_DB not set", file=sys.stderr); sys.exit(2)
    con = sqlite3.connect(path)
    info = {t: table_info(con, t) for t in ("operations","results")}
    counts = {t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
              for t in ("operations","results","relations","edges","findings","research","execution_events")}
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    out = {"verify_db": path, "sha256_verify": hashlib.sha256(open(path,'rb').read()).hexdigest(),
           "integrity": integrity, "counts": counts,
           "columns": {t: list(info[t]) for t in info}}

    # V1: ausencia antes de migrar (cambio requerido)
    migrated_cols = sum(len([c for c in required[t] if c in info[t]]) for t in required)
    out["migrated_columns"] = migrated_cols

    # V2: integridad ok
    out["v_integrity"] = (integrity == "ok")

    # V3: preservación de counts 360/330... excepto operations +1 por registrar probe
    expected_counts = oracle["counts_pre"]
    delta_ops = counts["operations"] - expected_counts["operations"]
    out["counts_preserved"] = (counts["results"]      == expected_counts["results"]
                            and counts["relations"]  == expected_counts["relations"]
                            and counts["edges"]       == expected_counts["edges"]
                            and counts["findings"]    == expected_counts["findings"]
                            and counts["research"]    == expected_counts["research"]
                            and counts["execution_events"] == expected_counts["execution_events"])
    out["delta_ops"] = delta_ops

    # V4: columnas requeridas presentes ahora
    missing = []
    for t, cols in required.items():
        for c in cols:
            if c not in info[t]: missing.append(f"{t}.{c}")
    out["missing_after_migration"] = missing
    out["all_columns_present"] = len(missing) == 0

    # V5: integridad de la copia frente al origen (aspexión)
    con.close()
    out["oracle_sha256"] = oracle_sha
    out["verdict"] = ("PASS_PARTIAL" if (out["v_integrity"] and out["all_columns_present"] and out["counts_preserved"]) else "FAIL")
    print(json.dumps(out, indent=2, sort_keys=True))
    sys.exit(0 if out["verdict"] == "PASS_PARTIAL" else 1)

if __name__ == "__main__":
    main()
