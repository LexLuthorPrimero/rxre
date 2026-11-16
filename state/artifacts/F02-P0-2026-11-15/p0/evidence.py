"""Evidencia recogida: table_info, conteos y sellado de origen."""
import sqlite3, json

TABLES = ("operations","results","relations","edges","findings","research","execution_events")

def collect(path):
    con = sqlite3.connect("file:%s?mode=ro&immutable=1" % path, uri=True)
    info = {
        "columns": {t: [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)] for t in ("operations","results")},
        "counts": {t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0] for t in TABLES},
        "integrity": con.execute("PRAGMA integrity_check").fetchone()[0],
    }
    con.close()
    return info

def missing(pre, required=None):
    if required is None:
        required = {
            "operations": ["declared_scope","authorized_scope","auth_decision","auth_actor","auth_timestamp"],
            "results":     ["verified_scope","scope_decision","limitations_json"],
        }
    out = {}
    for t, cols in required.items():
        present = set(pre["columns"].get(t, []))
        out[t] = [c for c in cols if c not in present]
    return out
