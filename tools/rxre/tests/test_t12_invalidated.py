#!/usr/bin/env python3
"""T12: INVALIDATED requiere reevaluacion documentada.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
Que `actualizar_estado_finding` rechace INVALIDATED sin reevaluacion
documentada, y que la acepte cuando la hay.

CONTRASTE
---------
Antes: acepta INVALIDATED sin reevaluacion.
Despues: rechaza sin reevaluacion, acepta con reevaluacion.
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


# --- Test negativo: sin reevaluacion → rechazado ---
print("\n=== TEST NEGATIVO: INVALIDATED sin reevaluacion ===")

conn = S.conectar(os.path.join(tempfile.mkdtemp(prefix="t12-"), "t.sqlite3"))
fid = S.guardar_finding(conn, {
    "finding_id": "F-T12-A", "claim": "x", "epistemic": "PROVEN",
    "object_hash": "sha256:a", "scope": "binary",
    "falsification_test": "test",
})
try:
    S.actualizar_estado_finding(conn, fid, "INVALIDATED", 0)
    v("T12 negativo: INVALIDATED sin reevaluacion rechazado", False,
      "acepto INVALIDATED sin reevaluacion")
except ValueError as e:
    v("T12 negativo: INVALIDATED sin reevaluacion rechazado",
      "INVALIDATED requiere reevaluacion" in str(e), str(e)[:60])
except Exception as e:
    v("T12 negativo: error inesperado", False, str(e)[:60])

# --- Test positivo: con reevaluacion → aceptado ---
print("\n=== TEST POSITIVO: INVALIDATED con reevaluacion ===")

fid2 = S.guardar_finding(conn, {
    "finding_id": "F-T12-B", "claim": "x2", "epistemic": "PROVEN",
    "object_hash": "sha256:a", "scope": "binary",
    "falsification_test": "test",
})
# Insertar reevaluacion documentada
conn.execute("PRAGMA foreign_keys = OFF")
conn.execute(
    "INSERT INTO finding_reevaluations "
    "(finding_id, contradiction, decision, rationale, reviewer, created_at) "
    "VALUES (?, 'otro producer discrepa', 'INVALIDATED', 'evidencia nueva', 'test', datetime('now'))",
    (fid2,))
conn.commit()

rc = S.actualizar_estado_finding(conn, fid2, "INVALIDATED", 0)
row = S.recuperar_finding(conn, fid2)
v("T12 positivo: INVALIDATED con reevaluacion aceptado", rc == 1)
v("T12 positivo: estado actualizado a INVALIDATED",
  row["epistemic"] == "INVALIDATED")

# --- Test adicional: REVERTED → PROVEN funciona ---
print("\n=== TEST ADICIONAL: REVERTED -> PROVEN ===")

fid3 = S.guardar_finding(conn, {
    "finding_id": "F-T12-C", "claim": "x3", "epistemic": "INVALIDATED",
    "object_hash": "sha256:a", "scope": "binary",
    "falsification_test": "test",
})
# Insertar reevaluacion REVERTED
conn.execute("PRAGMA foreign_keys = OFF")
conn.execute(
    "INSERT INTO finding_reevaluations "
    "(finding_id, contradiction, decision, rationale, reviewer, created_at) "
    "VALUES (?, 'la contradiccion era erronea', 'REVERTED', 'se refuto', 'test', datetime('now'))",
    (fid3,))
conn.commit()

rc = S.actualizar_estado_finding(conn, fid3, "PROVEN", 0)
row = S.recuperar_finding(conn, fid3)
v("T12 adicional: PROVEN sin reevaluacion de INVALIDATED funciona",
  rc == 1 and row["epistemic"] == "PROVEN")

conn.close()

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("T12: INVALIDATED requiere reevaluacion documentada")
sys.exit(0)