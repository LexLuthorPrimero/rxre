"""Reparación experimental F-02 sobre copia aislada. BEGIN→ALTER→COMMIT, idempotente."""
import os, sqlite3

MIGRATE = [
    ("operations", "declared_scope",   "TEXT", "''"),
    ("operations", "authorized_scope", "TEXT", "''"),
    ("operations", "auth_decision",    "TEXT", "'UNAUTH'"),
    ("operations", "auth_actor",       "TEXT", "''"),
    ("operations", "auth_timestamp",   "TEXT", "''"),
    ("results",     "verified_scope",   "TEXT", "''"),
    ("results",     "scope_decision",   "TEXT", "'UNVERIFIED'"),
    ("results",     "limitations_json", "TEXT", "'{}'"),
]

def migrate(db_path):
    # Conexión escribible sobre la COPIA de trabajo; nunca sobre trabajo protegido.
    con = sqlite3.connect(db_path)
    try:
        con.execute("BEGIN")
        added, already = [], []
        for table, col, typ, default in MIGRATE:
            cols = {r[1] for r in con.execute("PRAGMA table_info(%s)" % table)}
            if col in cols:
                already.append("%s.%s" % (table, col)); continue
            con.execute("ALTER TABLE %s ADD COLUMN %s %s DEFAULT %s" % (table, col, typ, default))
            added.append("%s.%s" % (table, col))
        con.commit()
        return {"added": added, "already": already}
    finally:
        con.close()
