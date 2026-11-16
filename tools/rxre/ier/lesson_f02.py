#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · EE · LESSON_F02 — lecciones aprendidas de F-02, verificables y revalidables.

Circuito:
    M6/M8 resultado  →  extraer lección  →  registrar con procedencia
        →  recuperar  →  revalidar  →  usar con limitaciones
    Si las precondiciones no coinciden → NO reutilizable como solución.

Reglas:
- Una copia de trabajo es el único artefacto donde se persiste.
- La lección conserva su procedencia (mision_id, diagnosis, hashes).
- OBSERVATION ≠ HYPOTHESIS ≠ VALIDATED_RULE.
- Un éxito en una copia NO autoriza regla universal sobre todas las bases.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from ier import mission, investigate  # noqa: E402
from core import store, hash as core_hash, evidence_integrity  # noqa: E402

ORIGEN = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
DDL_REF = "/home/lucas/Escritorio/rxre/tools/rxre/core/store.py"


def _sha(path: str) -> str:
    return core_hash.hash_file(path)


def _sha_text(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


# ------------------------------------------------------------
# 1. EXTRAER LECCIÓN del resultado de M6/M8
# ------------------------------------------------------------
def extraer_leccion(mision_id: str, dev_store: Optional[str] = None) -> Dict[str, Any]:
    """Construye una leccion estructurada a partir del resultado resperServer guardado."""
    IER_STORE = dev_store or os.environ.get("IER_STORE", "/tmp/opencode/ier-f02-lesson")
    mision = mission.cargar(mision_id, path=IER_STORE)
    if not mision:
        return {"estado": "BLOCKED", "reason": "misión no encontrada"}

    # Tomar el experimento más reciente
    exp = sorted(mision.get("experiments", []),
                 key=lambda e: e.get("created", ""),
                 reverse=True)[0]
    resultado = exp.get("result", {})

    leccion_raw = {
        "dominio": "persistencia SQLite / RXRE almacenamiento",
        "predicado": "El esquema de la base operativa puede divergir del DDL declarado en \n" +
                     "core/store.py. ANTES de depender de ésta, verificar integridad con PRAGMA.",
        "observacion": {
            "sha256_origen": resultado.get("sha256_origen"),
            "sha256_reparada": resultado.get("sha256_reparada"),
            "pre_schema_missing": resultado.get("pre_counts", {}),
            "post_schema_ok": None,  # rellenado más abajo
            "estado_operativo": "PASS" if resultado.get("repair_ok") else "FAIL",
            "epistemic": "PARTIAL",
        },
        "precondicion_necesaria": [
            "operado sobre copia verificada, no sobre la DB protegida;",
            "la copia debe coincidir por SHA-256 con la fuente sellada;",
            "las 8 columnas M281 están declaradas en store.DDL como clases opérations/results;",
            "la inicialización debe ser sobre ruta NO protegida o con dictado mínimo esperado."
        ],
        "procedimiento_ejecutado": [
            "copiar la base origen a scratch (versión _root_ sha=195...);",
            "reparation por ALTER TABLE ADD COLUMN para las 5 ops y 3 res faltantes;",
            "reejecutar conectar() → registrar() para verificar;",
            "checking integrity ok y rollback extrinsic si falla."
        ],
        "resultado_observado": resultado.get("registrar_op_id"),
        "problemas_conocidos": [
            "el diagnóstico solo es válido para esquema pre-M281;",
            "una columna ya existente pero de tipo o DEFAULT distinto produce SCHEMA_INCOMPATIBLE y no debe regenerarse;",
            "recibe rollback ante cualquier error transaccional, no solo el error de prueba."
        ],
        "referencia_origen": {
            "mision_id": mision_id,
            "exp_id": exp.get("experiment_id"),
            "sha256_origen": resultado.get("sha256_origen"),
            "sha256_snapshot": resultado.get("sha256_snapshot"),
        },
    }

    if resultado.get("repair_ok") is True:
        leccion_raw["observacion"]["post_schema_ok"] = True

    return {"estado": "OK", "leccion": leccion_raw, "mision_id": mision_id}


# ------------------------------------------------------------
# 2. REGISTRAR LECCIÓN en copia de trabajo
# ------------------------------------------------------------
def registrar_leccion(c: sqlite3.Connection, leccion: Dict[str, Any],
                       operation_id: Optional[str] = None) -> Dict[str, Any]:
    """Escribe una lección en la copia, usando el esquema reflexiones de RXRE."""
    # preferimos INSERT directo para no depender de _exige_schema_ok que exige conteo de M281
    # primero aprovechamos  store  aseguramos columnas
    store._asegurar_columnas_reflexiones(c)
    leccion_id = "leccion_" + _sha_text(json.dumps(leccion, sort_keys=True, separators=(",", ":",)))[:16]
    c.execute(
        "INSERT OR IGNORE INTO reflexiones (reflexion_id, attempt_id, feedback, reflection, outcome, strategy, target, capability, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
        (leccion_id,
         operation_id or leccion["referencia_origen"]["mision_id"],
         json.dumps(leccion["observacion"], sort_keys=True, ensure_ascii=False)[:4000],
         leccion["predicado"] + "\n\n" +
         ",\n".join([l + "." for l in leccion["precondicion_necesaria"]]),
         "success" if leccion["observacion"]["estado_operativo"] == "PASS" else "failure",
         leccion.get("strategy", ""),
         leccion["dominio"],
         ""))
    return {"reflexion_id": leccion_id, "estado": "registrado"}


# ------------------------------------------------------------
# 3. RECUPERAR y VERIFICAR PROCEDENCIA
# ------------------------------------------------------------
def recuperar_lecciones(c: sqlite3.Connection, capability: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """Recupera lecciones desde la copia."""
    filas = c.execute(
        "SELECT reflexion_id, feedback, reflection, outcome, strategy, target, capability, timestamp "
        "FROM reflexiones "
        "WHERE target LIKE ? OR capability LIKE ? OR strategy LIKE ? "
        "ORDER BY timestamp DESC LIMIT ?",
        ("%" + capability + "%", "%" + capability + "%", "%" + capability + "%", limit),
    ).fetchall()
    return [dict(r) for r in filas]


# ------------------------------------------------------------
# 4. REVALIDAR PROCEDENTE
# ------------------------------------------------------------
def revalidar_leccion(leccion_id: str, copia: str,
                      mode: str = "repair_post") -> Dict[str, Any]:
    """Revalida si una lección sigue siendo aplicable.

    No ejecutar la reparación; solo comprobar que las precondiciones estructurales
    siguen coincidiendo con el perfil que describe la lección.

    Modos:
        diagnostic_pre_repair  -> work copywith missing columns (expected behavior)
        repair_post           -> copia tras reparación (8 cols present)
    """
    if mode not in ("repair_post", "diagnostic_pre_repair"):
        return {"estado": "NOT_DETERMINED",
                "motivo": "modo desconocido: %s" % mode,
                "leccion_id": leccion_id}
    con = sqlite3.connect(copia, isolation_level=None)
    try:
        ops_cols = [r[1] for r in con.execute("PRAGMA table_info(operations)")]
        rs_cols  = [r[1] for r in con.execute("PRAGMA table_info(results)")]
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
                   for t in ("operations","results","relations","edges","research","execution_events")}
    except sqlite3.Error as e:
        con.close()
        return {"estado": "NOT_DETERMINED",
                "motivo": "error al leer la copia: %s" % e,
                "leccion_id": leccion_id}
    con.close()
    miss_op = [c for c in ["declared_scope","authorized_scope","auth_decision",
                            "auth_actor","auth_timestamp"] if c not in ops_cols]
    miss_rs = [c for c in ["verified_scope","scope_decision","limitations_json"] if c not in rs_cols]
    if mode == "diagnostic_pre_repair":
        if len(miss_op) + len(miss_rs) > 0:
            return {"estado": "REVALIDADA", "motivo": "diagnóstico confirmado: %d columnas faltantes como esperaba" % (len(miss_op) + len(miss_rs)),
                    "leccion_id": leccion_id, "integrity": integrity, "counts": counts,
                    "missing_columns": miss_op + miss_rs}
        return {"estado": "RECHAZAR", "motivo": "la copia ya está completa: no es el estado de pre-reparación",
                "leccion_id": leccion_id}
    # mode == "repair_post": expect 8 cols present
    if miss_op or miss_rs:
        return {"estado": "RECHAZAR", "motivo": "faltan columnas tras reparación: %s" % (miss_op + miss_rs),
                "leccion_id": leccion_id, "missing_columns": miss_op + miss_rs,
                "integrity": integrity, "counts": counts}
    if integrity != "ok":
        return {"estado": "RECHAZAR", "motivo": "integridad no ok tras reparación: %s" % integrity,
                "leccion_id": leccion_id, "integrity": integrity}
    return {"estado": "REVALIDADA", "motivo": "condiciones estructurales coincidentes; aplicabilidad confirmada",
            "leccion_id": leccion_id, "integrity": integrity, "counts": counts}


# ------------------------------------------------------------
# Emergencia (estilo-085): marca de fallo
# ------------------------------------------------------------
def registrar_fallo_leccion(c: sqlite3.Connection, ref: str, reason: str,
                              rollback_info: Dict[str, Any]) -> Dict[str, Any]:
    """Registra la lección negativa de un fallo con rollback."""
    store._asegurar_columnas_reflexiones(c)
    neg_id = "leccion_neg_" + _sha_text(ref + "|" + reason + "|" + json.dumps(rollback_info))[:16]
    c.execute(
        "INSERT OR IGNORE INTO reflexiones (reflexion_id, attempt_id, feedback, reflection, outcome, strategy, target) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (neg_id, ref,
         "fallo en reparación: " + reason,
         "rollback ejecutado; sha256 restaurado; NO promover como lección positiva: la reparación falló.",
         "failure", "abortado_rollback", "persistencia RXRE"))
    return {"reflexion_id": neg_id, "estado": "failure_registrado"}
