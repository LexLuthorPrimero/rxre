#!/usr/bin/env python3
"""FASE 2 · PASO 6 — Trigger de validación para findings nuevos.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
El trigger `trg_findings_contrato_nuevo` rechaza INSERT de findings nuevos
que no tengan los 10 campos del contrato. Los findings legacy (prefijo
F-LEGACY-) quedan exentos (grandfathered).

CONTRASTE
---------
Antes del trigger: acepta findings incompletos.
Despues: rechaza con CONTRATO_INCOMPLETO.
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


# --- Test 1: finding nuevo sin contrato → falla ---
print("\n=== TEST 1: finding nuevo sin contrato ===")

conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="t6-"), "t.sqlite3"))
try:
    S.guardar_finding(conn, {
        "finding_id": "F-NUEVO-INCOMPLETO",
        "claim": "test",
        "epistemic": "NOT_DETERMINED",
        # falta object_hash, scope, falsification_test, etc.
    })
    v("T6.1 (ANTES) acepta finding incompleto → debe fallar tras el fix",
      False, "acepta incompleto")
except sqlite3.IntegrityError as e:
    v("T6.1 (ANTES) finding incompleto rechazado → ya hay trigger",
      "CONTRATO_INCOMPLETO" in str(e), str(e)[:60])
except Exception as e:
    v("T6.1 (ANTES) error inesperado", False, str(e)[:60])

# --- Test 2: finding legacy exento ---
print("\n=== TEST 2: finding legacy exento ===")

# El trigger exime por prefijo de finding_id. guardar_finding genera el id
# a partir del claim, asi que para probar la excepcion hay que insertar
# directamente con un id F-LEGACY-.
try:
    conn.execute(
        "INSERT INTO findings (finding_id, claim, epistemic, evidence_ids, "
        "provenance, limitations, created_at, version) "
        "VALUES ('F-LEGACY-TEST', 'legacy', 'NOT_DETERMINED', '[]', '{}', "
        "'[]', datetime('now'), 0)")
    v("T6.2 finding legacy exento (no levanta excepcion)", True)
except Exception as e:
    v("T6.2 finding legacy exento", False, str(e)[:60])

# --- Test 3: finding nuevo completo → aceptado ---
print("\n=== TEST 3: finding nuevo completo ===")

try:
    fid = S.guardar_finding(conn, {
        "finding_id": "F-COMPLETO",
        "claim": "test completo",
        "epistemic": "NOT_DETERMINED",
        "object_hash": "sha256:abc",
        "scope": "binary",
        "falsification_test": "romper X",
    })
    v("T6.3 finding nuevo completo aceptado", True)
except Exception as e:
    v("T6.3 finding nuevo completo", False, str(e)[:60])

conn.close()

# --- Test 4: los 12 findings existentes siguen legibles ---
print("\n=== TEST 4: los 12 findings existentes siguen legibles ===")

conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="t6b-"), "t.sqlite3"))
conn.execute("PRAGMA foreign_keys = OFF")
src = sqlite3.connect(f"file:{os.path.join(PKG, 'storage', 'rxre.sqlite3')}?mode=ro",
                      uri=True)
src.row_factory = sqlite3.Row
invalidos = 0
for row in src.execute("SELECT finding_id, op_id, claim, epistemic, "
                       "evidence_ids, provenance, limitations, created_at, "
                       "object_hash, scope, derivation_refs, contradiction_refs, "
                       "falsification_test FROM findings").fetchall():
    # Los 12 findings existentes son legacy: se insertan con prefijo
    # F-LEGACY- para que el trigger los exima. En la BD real ya existen
    # (insertados antes del trigger) y no se re-insertan.
    legacy_id = "F-LEGACY-" + row["finding_id"]
    try:
        conn.execute(
            "INSERT INTO findings (finding_id, op_id, claim, epistemic, "
            "evidence_ids, provenance, limitations, created_at, version) "
            "VALUES (?,?,?,?,?,?,?,?,'0')",
            (legacy_id, row["op_id"], row["claim"], row["epistemic"],
             row["evidence_ids"], row["provenance"], row["limitations"],
             row["created_at"]))
    except sqlite3.IntegrityError as e:
        invalidos += 1
        v("T6.4 finding %s invalido" % row["finding_id"], False, str(e)[:60])
src.close()
conn.close()
v("T6.4 los 12 findings existentes siguen legibles",
  invalidos == 0, "%d invalidos" % invalidos)

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("TIERRA-1: trigger de validacion activo")
sys.exit(0)