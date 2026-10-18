#!/usr/bin/env python3
"""Gap OBSERVED cerrado: 9 findings migrados, rz_findings con 6 estados."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


# --- Test 1: rz_findings tiene 6 estados ---
import importlib.util
spec = importlib.util.spec_from_file_location(
    "rzf", os.path.join(PKG, "backends", "adapters", "rz_findings.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
v("OBSERVED gap: rz_findings tiene 6 estados (INVALIDATED incluido)",
  set(mod.EPISTEMIC_STATUS) == {"PROVEN", "PARTIAL", "NOT_DETERMINED",
                                "PROVEN_ABSENT", "DEFERRED", "INVALIDATED"},
  str(mod.EPISTEMIC_STATUS))
v("OBSERVED gap: OBSERVED ya no esta en EPISTEMIC_STATUS",
  "OBSERVED" not in mod.EPISTEMIC_STATUS)

# --- Test 2: 0 findings con OBSERVED en la BD de desarrollo ---
DB = os.path.join(PKG, "storage", "rxre.sqlite3")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
obs = c.execute("SELECT COUNT(*) FROM findings WHERE epistemic='OBSERVED'"
                ).fetchone()[0]
v("OBSERVED gap: 0 findings con OBSERVED en la BD de desarrollo",
  obs == 0, "quedan %d" % obs)
c.close()

# --- Test 3: trigger bloquea OBSERVED en INSERT (en BD temporal) ---
from core import store as S
tmp_db = os.path.join(tempfile.mkdtemp(prefix="obs-"), "t.sqlite3")
conn = S.conectar(tmp_db)
try:
    S.guardar_finding(conn, {"finding_id": "F-OBS", "claim": "test",
                             "epistemic": "OBSERVED"})
    v("OBSERVED gap: trigger bloquea INSERT con OBSERVED", False,
      "acepta OBSERVED")
except sqlite3.IntegrityError as e:
    v("OBSERVED gap: trigger bloquea INSERT con OBSERVED",
      "EPISTEMIC_INVALID" in str(e), str(e)[:60])
conn.close()

# --- Test 4: los 12 findings son validos bajo el trigger ---
conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="obs2-"), "t.sqlite3"))
# Las FKs no son el punto de este test: el punto es el CHECK de epistemic.
# Se desactivan para poder copiar findings sin copiar toda la cadena de
# operations/results, que no es lo que se esta verificando.
conn.execute("PRAGMA foreign_keys = OFF")
src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
src.row_factory = sqlite3.Row
invalidos = 0
for row in src.execute("SELECT finding_id, op_id, claim, epistemic, "
                       "evidence_ids, provenance, limitations, created_at "
                       "FROM findings").fetchall():
    try:
        conn.execute(
            "INSERT INTO findings (finding_id, op_id, claim, epistemic, "
            "evidence_ids, provenance, limitations, created_at, version) "
            "VALUES (?,?,?,?,?,?,?,?,'0')",
            (row["finding_id"], row["op_id"], row["claim"], row["epistemic"],
             row["evidence_ids"], row["provenance"], row["limitations"],
             row["created_at"]))
    except sqlite3.IntegrityError as e:
        invalidos += 1
        v("OBSERVED gap: finding %s invalido bajo trigger" % row["finding_id"],
          False, str(e)[:60])
src.close()
conn.close()
v("OBSERVED gap: los 12 findings migrados son validos bajo el trigger",
  invalidos == 0, "%d invalidos" % invalidos)

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("OBSERVED GAP CERRADO")
sys.exit(0)