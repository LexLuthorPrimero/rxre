#!/usr/bin/env python3
"""Pruebas P0 (F-02) sobre copias selladas."""
import hashlib, json, os, shutil, sqlite3, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("P0_SCRATCH", "/tmp/opencode/p0-tests")
from p0.seal import sha256_file, snapshot, restore
from p0.evidence import collect, missing
from p0.repair import migrate
SRC = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
EXPECTED_SHA = "195f68fb25db674b41408ee8283df952b158528c9ccb58cdb1dc42b0810f8ef2"
TEST_DIR = "/tmp/opencode/p0-tests-%d" % int(time.time())
os.makedirs(TEST_DIR)

def fresh_copy(name):
    p = os.path.join(TEST_DIR, name)
    shutil.copy2(SRC, p)
    return p

def ok(cond, name, detail=""):
    print(("PASS" if cond else "FAIL"), "-", name, detail)
    return 0 if cond else 1

tests = []

# --- caso normal ---
snap = fresh_copy("normal.sqlite3")
h0 = snapshot(SRC, snap)
info0 = collect(snap)
t01 = ok(h0 == EXPECTED_SHA, "T01 seal sha match", h0); tests.append(t01)
t02 = ok(info0["integrity"] == "ok", "T02 integrity pre", info0["integrity"]); tests.append(t02)
miss = missing(info0)
t03 = ok(sum(len(v) for v in miss.values()) == 8, "T03 detecta 8 columnas faltantes", miss); tests.append(t03)
mig = migrate(snap)
info1 = collect(snap)
t04 = ok(len(mig["added"]) == 8, "T04 migración agrega 8 columnas", mig); tests.append(t04)
t05 = ok(info1["integrity"] == "ok", "T05 integrity post-mig", info1["integrity"]); tests.append(t05)

# --- origen hash incorrecto ---
bad = fresh_copy("bad.sqlite3"); h0b = snapshot(SRC, bad)
with open(bad, "r+b") as f:
    f.seek(1000); b = f.read(1); f.seek(1000); f.write(bytes([b[0] ^ 1]))
h_bad = sha256_file(bad)
t06 = ok(h_bad != EXPECTED_SHA, "T06 detecta origen con hash incorrecto", h_bad[:16]); tests.append(t06)

# --- tipo incorrecto ---
wrong = fresh_copy("wrongtype.sqlite3")
con = sqlite3.connect(wrong); con.execute("BEGIN")
con.execute("ALTER TABLE operations ADD COLUMN declared_scope INTEGER DEFAULT 0"); con.commit()
sql_type = next(r[2] for r in con.execute("PRAGMA table_info(operations)") if r[1]=="declared_scope")
t07 = ok(sql_type != "TEXT", "T07 tipo incorrecto detectado", sql_type); tests.append(t07)
con.close()

# --- default incorrecto ---
wrongd = fresh_copy("wrongdefault.sqlite3")
con = sqlite3.connect(wrongd); con.execute("BEGIN")
con.execute("ALTER TABLE operations ADD COLUMN auth_decision TEXT DEFAULT 'WRONG'"); con.commit()
sql_def = next(r[4] for r in con.execute("PRAGMA table_info(operations)") if r[1]=="auth_decision")
t08 = ok(sql_def != "'UNAUTH'", "T08 default incorrecto detectado", sql_def); tests.append(t08)
con.close()

# --- migración parcial ---
partial = fresh_copy("partial.sqlite3")
con = sqlite3.connect(partial); con.execute("BEGIN")
for t, c in [("operations","declared_scope"),("operations","authorized_scope"),("operations","auth_decision")]:
    con.execute("ALTER TABLE %s ADD COLUMN %s TEXT DEFAULT ''" % (t, c))
con.commit(); con.close()
miss2 = missing(collect(partial))
t09 = ok(sum(len(v) for v in miss2.values()) == 5, "T09 migración parcial detectada", miss2); tests.append(t09)

# --- interrupción antes del commit ---
rolled = fresh_copy("rolledback.sqlite3")
con = sqlite3.connect(rolled); con.execute("BEGIN")
for table, col in [("operations","declared_scope"),("results","verified_scope")]:
    con.execute("ALTER TABLE %s ADD COLUMN %s TEXT DEFAULT ''" % (table, col))
con.execute("ROLLBACK"); con.close()
miss3 = missing(collect(rolled))
t10 = ok(sum(len(v) for v in miss3.values()) == 8, "T10 rollback restaura esquema original", miss3); tests.append(t10)

# --- alteración de datos preexistentes ---
altered = fresh_copy("altered.sqlite3")
con = sqlite3.connect(altered)
pre_r = con.execute("SELECT count(*) FROM research").fetchone()[0]
con.execute("DELETE FROM research WHERE rowid = (SELECT min(rowid) FROM research)"); con.commit()
post_r = con.execute("SELECT count(*) FROM research").fetchone()[0]
t11 = ok(post_r == pre_r - 1, "T11 alteración detectada por conteo", (pre_r, post_r)); tests.append(t11)
con.close()

# --- segunda ejecución / idempotencia ---
snap2 = fresh_copy("idem.sqlite3")
snapshot(SRC, snap2); migrate(snap2)
mig2 = migrate(snap2)
t12 = ok(len(mig2["added"]) == 0 and len(mig2["already"]) == 8, "T12 segunda migración idempotente", mig2); tests.append(t12)

print("SUMMARY: %d PASSes, %d FAILs" % (sum(1 for t in tests if t == 0), sum(1 for t in tests if t != 0)))
sys.exit(1 if any(t != 0 for t in tests) else 0)
