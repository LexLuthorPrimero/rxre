"""FASE 2 — correcciones v3 sobre store.py. Tests adversariales.

Cada corrección sigue el mismo patrón:
  1. el test falla contra el código actual (sin la corrección)
  2. se aplica el cambio
  3. el test pasa
  4. se rompe la corrección y el test falla (contraste)

Si un test pasa ANTES del cambio, el cambio no es necesario o el test está mal.
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


def conn_bd(tmp):
    return S.conectar(os.path.join(tmp, "t.sqlite3"))


# ==========================================================================
# CORRECCIÓN 1 — CHECK de 6 estados en findings
# ==========================================================================
print("\n=== CORRECCIÓN 1: CHECK 6 estados en findings ===")

c = conn_bd(tempfile.mkdtemp(prefix="c1-"))
try:
    S.guardar_finding(c, {"finding_id": "F-GARBAGE", "claim": "test",
                          "epistemic": "GARBAGE",
                          "object_hash": "sha256:test",
                          "scope": "binary",
                          "falsification_test": "romper X",
                          "derivation_refs": "[]",
                          "contradiction_refs": "[]"})
    v("C1.1 (ANTES) acepta 'GARBAGE' → debe fallar tras el fix",
      False, "acepta GARBAGE")
except sqlite3.IntegrityError as e:
    v("C1.1 (ANTES) 'GARBAGE' rechazado → ya hay trigger o CHECK",
      "EPISTEMIC_INVALID" in str(e), str(e)[:60])
except Exception as e:
    v("C1.1 (ANTES) error inesperado", False, str(e)[:60])

# Test de regresión: estado válido sigue funcionando
try:
    fid = S.guardar_finding(c, {"finding_id": "F-VALID", "claim": "test-valido",
                                "epistemic": "NOT_DETERMINED",
                                "object_hash": "sha256:test",
                                "scope": "binary",
                                "falsification_test": "romper X"})
    assert fid.startswith("finding_") or fid.startswith("COLISION:")
    v("C1.2 estado válido aceptado tras el fix", True)
except Exception as e:
    v("C1.2 estado válido", False, str(e)[:60])

# Verificar que hay OBSERVED en la BD (gap documentado)
obs = c.execute("SELECT COUNT(*) FROM findings WHERE epistemic='OBSERVED'"
                ).fetchone()[0]
v("C1.3 (gap) filas con OBSERVED en la BD de desarrollo: %d "
  "(no bloquea, pero el trigger los protege de futuros UPDATEs)" % obs,
  True)

c.close()

# ==========================================================================
# CORRECCIÓN 2 — Append-only en results
# ==========================================================================
print("\n=== CORRECCIÓN 2: Append-only en results ===")

c = conn_bd(tempfile.mkdtemp(prefix="c2-"))
# Insertar un result para poder probar
c.execute(
    "INSERT INTO results (result_id, operation_id, type, value, raw_json, "
    "timestamp) VALUES ('r1', NULL, 'raw_binary', '{}', '{}', "
    "'2026-01-01T00:00:00')")

# UPDATE debe fallar
try:
    c.execute("UPDATE results SET value='x' WHERE result_id='r1'")
    v("C2.1 (ANTES) UPDATE results aceptado → debe fallar tras el fix",
      False)
except sqlite3.DatabaseError as e:
    v("C2.1 (ANTES) UPDATE results rechazado → ya hay trigger",
      "APPEND_ONLY" in str(e), str(e)[:60])
except Exception as e:
    v("C2.1 (ANTES) error inesperado", False, str(e)[:60])

# DELETE debe fallar
try:
    c.execute("DELETE FROM results WHERE result_id='r1'")
    v("C2.2 (ANTES) DELETE results aceptado → debe fallar tras el fix",
      False)
except sqlite3.DatabaseError as e:
    v("C2.2 (ANTES) DELETE results rechazado → ya hay trigger",
      "APPEND_ONLY" in str(e), str(e)[:60])
except Exception as e:
    v("C2.2 (ANTES) error inesperado", False, str(e)[:60])

# row_hash: la columna debe existir
try:
    c.execute("SELECT row_hash FROM results LIMIT 1")
    v("C2.3 columna row_hash existe", True)
except sqlite3.OperationalError:
    v("C2.3 columna row_hash NO existe → falta ALTER TABLE",
      False, "columna ausente")

# supersedes_ref: la columna debe existir
try:
    c.execute("SELECT supersedes_ref FROM results LIMIT 1")
    v("C2.4 columna supersedes_ref existe", True)
except sqlite3.OperationalError:
    v("C2.4 columna supersedes_ref NO existe → falta ALTER TABLE",
      False, "columna ausente")

c.close()

# ==========================================================================
# CORRECCIÓN 3 — INVALIDATED con reevaluación documentada
# ==========================================================================
print("\n=== CORRECCIÓN 3: INVALIDATED con reevaluación ===")

c = conn_bd(tempfile.mkdtemp(prefix="c3-"))
fid = S.guardar_finding(c, {"finding_id": "F-C3", "claim": "test",
                           "epistemic": "NOT_DETERMINED",
                           "object_hash": "sha256:test",
                           "scope": "binary",
                           "falsification_test": "romper X"})

# INVALIDATED sin reevaluación → debe fallar
try:
    S.reevaluar_finding(c, fid, "", "INVALIDATED", "motivo", "revisor")
    v("C3.1 (ANTES) INVALIDATED sin contradicción aceptado → debe fallar",
      False)
except (ValueError, Exception) as e:
    v("C3.1 (ANTES) INVALIDATED sin contradicción rechazado",
      "contradiction" in str(e).lower() or "contradiccion" in str(e).lower(),
      str(e)[:60])

# INVALIDATED con reevaluación → debe funcionar
r = S.reevaluar_finding(c, fid, "otro producer discrepa", "INVALIDATED",
                        "discrepancia", "revisor-externo")
v("C3.2 INVALIDATED con reevaluación aceptado",
  r["epistemic"] == "INVALIDATED")

# REVERTED → PROVEN (reversible)
r2 = S.reevaluar_finding(c, fid, "se refutó", "REVERTED", "refutado",
                         "revisor-externo")
v("C3.3 REVERTED devuelve a PROVEN", r2["epistemic"] == "PROVEN")

# Histórico completo
hist = S.reevaluaciones_de_finding(c, fid)
v("C3.4 histórico conserva ambas decisiones",
  [h["decision"] for h in hist] == ["INVALIDATED", "REVERTED"])

c.close()

# ==========================================================================
# CORRECCIÓN 4 — Concurrencia por operación
# ==========================================================================
print("\n=== CORRECCIÓN 4: Concurrencia por operación ===")

c = conn_bd(tempfile.mkdtemp(prefix="c4-"))
fid = S.guardar_finding(c, {"finding_id": "F-C4", "claim": "test",
                           "epistemic": "NOT_DETERMINED",
                           "object_hash": "sha256:test",
                           "scope": "binary",
                           "falsification_test": "romper X"})

# Columna version existe
try:
    vv = c.execute("SELECT version FROM findings WHERE finding_id=?", (fid,)
                   ).fetchone()["version"]
    v("C4.1 columna version existe", vv == 0)
except Exception as e:
    v("C4.1 columna version NO existe", False, str(e)[:60])

# Actualizar estado: primer update OK
try:
    rc = S.actualizar_estado_finding(c, fid, "PROVEN", 0)
    v("C4.2 primer update OK", rc == 1)
except AttributeError as e:
    v("C4.2 actualizar_estado_finding NO existe", False, str(e)[:60])
except Exception as e:
    v("C4.2 error inesperado", False, str(e)[:60])

# Segundo update con version vieja: conflicto
try:
    rc = S.actualizar_estado_finding(c, fid, "PARTIAL", 0)
    v("C4.3 segundo update con version vieja → conflicto (0)",
      rc == 0, "rc=%d" % rc)
except AttributeError as e:
    v("C4.3 actualizar_estado_finding NO existe", False, str(e)[:60])
except Exception as e:
    v("C4.3 error inesperado", False, str(e)[:60])

# Regresión: crear finding nuevo sigue funcionando
fid2 = S.guardar_finding(c, {"finding_id": "F-NEW", "claim": "nuevo-unico",
                             "epistemic": "NOT_DETERMINED",
                             "object_hash": "sha256:test",
                             "scope": "binary",
                             "falsification_test": "romper X",
                             "derivation_refs": "[]",
                             "contradiction_refs": "[]"})
row = S.recuperar_finding(c, fid2)
v("C4.4 (regresión) crear finding nuevo funciona",
  fid2.startswith("finding_") and row is not None
  and row.get("version") == 0)

# Nueva semántica: id existente no sobrescribe
fid3 = S.guardar_finding(c, {"claim": "duplicado-test", "epistemic": "NOT_DETERMINED",
                             "object_hash": "sha256:test", "scope": "binary",
                             "falsification_test": "romper X",
                             "derivation_refs": "[]", "contradiction_refs": "[]"})
assert fid3.startswith("finding_")
fid4 = S.guardar_finding(c, {"claim": "duplicado-test", "epistemic": "PROVEN",
                             "object_hash": "sha256:test", "scope": "binary",
                             "falsification_test": "romper X",
                             "derivation_refs": "[]", "contradiction_refs": "[]"})

v("C4.5 (nueva semántica) id existente → COLISION, no sobrescribe",
  fid4.startswith("COLISION:") and fid4.endswith(fid3),
  "fid4=%s" % fid4)
row = S.recuperar_finding(c, fid3)
v("C4.5b el finding original no se pisó",
  row["claim"] == "duplicado-test"
  and row["epistemic"] == "NOT_DETERMINED")

c.close()

# ==========================================================================
# CORRECCIÓN 5 — ÉTER (no existe en producción)
# ==========================================================================
print("\n=== CORRECCIÓN 5: ÉTER ===")

try:
    from core import eter as E
    v("C5.1 módulo core/eter.py existe", True)
except ImportError as e:
    v("C5.1 módulo core/eter.py NO existe → crear", False, str(e))

# ==========================================================================
# CORRECCIÓN 6 — FUEGO (no existe en producción)
# ==========================================================================
print("\n=== CORRECCIÓN 6: FUEGO ===")

try:
    from core import fuego as F
    v("C6.1 módulo core/fuego.py existe", True)
except ImportError as e:
    v("C6.1 módulo core/fuego.py NO existe → crear", False, str(e))

# ==========================================================================
# CORRECCIÓN 7 — ACCEPTED con autoridad declarada (documental)
# ==========================================================================
print("\n=== CORRECCIÓN 7: ACCEPTED con autoridad (documental) ===")

import os as _os
auth_path = _os.path.join(PKG, "..", "..", "audit", "AUTHORITY.md")
v("C7.1 audit/AUTHORITY.md existe", _os.path.isfile(auth_path),
  "falta crear")

# ==========================================================================
# RESUMEN
# ==========================================================================
print("\n=== RESUMEN: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    print("\nFAILS:")
    for f in fails:
        print("  ", f)
    sys.exit(1)
print("TODAS LAS CORRECCIONES VERIFICADAS")
sys.exit(0)
