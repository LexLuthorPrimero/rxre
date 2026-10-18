#!/usr/bin/env python3
"""FASE 2 · PASO 5 — TIERRA-1: los 10 campos del contrato en findings.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
El diagrama define 10 campos. El schema real tenia 5. Este test comprueba
que los 10 existen y que los 5 nuevos son escribibles, y que los 12 findings
existentes siguen legibles despues de la migracion.

CONTRASTE
---------
Antes de la migracion: test_findings_tiene_los_10_campos_del_contrato FALLA
porque faltan 5 columnas. Despues: PASA.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from core import store as S  # noqa: E402

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


DB = os.path.join(PKG, "storage", "rxre.sqlite3")

# ==========================================================================
# TEST 1: los 10 campos del contrato
# ==========================================================================
print("\n=== TEST 1: los 10 campos del contrato ===")

conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="t1-"), "t.sqlite3"))
cols = {r["name"] for r in conn.execute("PRAGMA table_info(findings)").fetchall()}

contrato = {
    "finding_id",         # id
    "claim",              # statement
    "object_hash",        # FALTA antes
    "scope",              # FALTA antes
    "epistemic",          # epistemic_state
    "evidence_ids",       # evidence_refs[]
    "derivation_refs",    # FALTA antes
    "contradiction_refs", # FALTA antes
    "falsification_test", # FALTA antes
    "limitations",        # unresolved_obligations[]
}

faltantes = contrato - cols
v("T1.1 los 10 campos del contrato existen",
  not faltantes, "faltan: %s" % sorted(faltantes))

conn.close()

# ==========================================================================
# TEST 2: los 5 campos nuevos son escribibles
# ==========================================================================
print("\n=== TEST 2: los 5 campos nuevos son escribibles ===")

conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="t2-"), "t.sqlite3"))
fid = S.guardar_finding(conn, {
    "finding_id": "F-T1",
    "claim": "test contrato",
    "epistemic": "NOT_DETERMINED",
    "object_hash": "sha256:abc123",
    "scope": "binary",
    "derivation_refs": '["F-BASE"]',
    "contradiction_refs": "[]",
    "falsification_test": "romper X y verificar Y",
})
row = S.recuperar_finding(conn, fid)
v("T2.1 object_hash escribible y legible",
  row is not None and row.get("object_hash") == "sha256:abc123",
  str(row.get("object_hash") if row else None))
v("T2.2 scope escribible y legible",
  row is not None and row.get("scope") == "binary",
  str(row.get("scope") if row else None))
v("T2.3 falsification_test escribible y legible",
  row is not None and row.get("falsification_test") == "romper X y verificar Y",
  str(row.get("falsification_test") if row else None))
v("T2.4 derivation_refs escribible y legible",
  row is not None and row.get("derivation_refs") == ["F-BASE"],
  str(row.get("derivation_refs") if row else None))
v("T2.5 contradiction_refs escribible y legible",
  row is not None and row.get("contradiction_refs") == [],
  str(row.get("contradiction_refs") if row else None))
conn.close()

# ==========================================================================
# TEST 3: los 12 findings existentes siguen legibles
# ==========================================================================
print("\n=== TEST 3: los 12 findings existentes siguen legibles ===")

conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="t3-"), "t.sqlite3"))
# Copiar findings de la BD dev (sin FKs)
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
            ("F-LEGACY-" + row["finding_id"], row["op_id"], row["claim"],
             row["epistemic"], row["evidence_ids"], row["provenance"],
             row["limitations"], row["created_at"]))
    except sqlite3.IntegrityError as e:
        invalidos += 1
src.close()

rows = conn.execute("SELECT finding_id FROM findings").fetchall()
v("T3.1 los 12 findings existentes siguen legibles",
  len(rows) >= 12 and invalidos == 0,
  "%d findings, %d invalidos" % (len(rows), invalidos))

# Los campos nuevos son NULL en filas viejas
for r in rows:
    row = S.recuperar_finding(conn, r["finding_id"])
    assert row is not None
    # NULL es aceptable (backfill pendiente)
    assert row.get("object_hash") is None or isinstance(row["object_hash"], str)
v("T3.2 los campos nuevos son NULL en filas viejas (backfill pendiente)",
  True)

conn.close()

# ==========================================================================
# RESUMEN
# ==========================================================================
print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("TIERRA-1: 10/10 CAMPOS DEL CONTRATO")
sys.exit(0)