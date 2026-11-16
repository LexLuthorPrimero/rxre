#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · EE · REPAIR_FLOW — ciclo reparacion controlada para F-02.

Entrada: mision de investigacion (ier/investigate_f02.py reutiliza).
Salida:  resultado de reparacion controlada sobre copia aislada.

Peligrosamente limitado: no toca la DB protegida, no modifica contratos,
no promueve nada. Toda promocion/autorizacion es dictamen del propietario.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from . import mission  # noqa: E402
_CORE = os.path.join(_HERE, "..", "core")
sys.path.insert(0, _CORE)
from core import store, hash as core_hash  # noqa: E402

ORIGEN = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
DDL_REF = "/home/lucas/Escritorio/rxre/tools/rxre/core/store.py"
EXPECTED_SHA256 = "195f68fb25db674b41408ee8283df952b158528c9ccb58cdb1dc42b0810f8ef2"
EXPECTED_COLS_OPERACIONES = ["declared_scope","authorized_scope","auth_decision","auth_actor","auth_timestamp"]
EXPECTED_COLS_RESULTADOS  = ["verified_scope","scope_decision","limitations_json"]


def _sha(path: str) -> str:
    return core_hash.hash_file(path)


def _sha_text(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def _columnas_tabla(con, tabla):
    return [r[1] for r in con.execute("PRAGMA table_info(%s)" % tabla)]


def _schema_preconditions(db_copy: str) -> Dict[str, Any]:
    con = sqlite3.connect(db_copy, isolation_level=None)
    try:
        cols_ops = _columnas_tabla(con, "operations")
        cols_res = _columnas_tabla(con, "results")
        faltan_op = [c for c in EXPECTED_COLS_OPERACIONES if c not in cols_ops]
        faltan_rs = [c for c in EXPECTED_COLS_RESULTADOS  if c not in cols_res]
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
                   for t in ("operations","results","relations","edges","research","execution_events")}
        return {"pre_columns_missing_operations": faltan_op,
                "pre_columns_missing_results":    faltan_rs,
                "pre_integrity": integrity,
                "pre_counts": counts}
    finally:
        con.close()


def _repair_copy(work: str) -> Dict[str, Any]:
    """Aplica EXCLUSIVAMENTE los ALTER necesarios sobre la copia de trabajo."""
    con = sqlite3.connect(work)
    con.execute("BEGIN")
    try:
        for col in EXPECTED_COLS_OPERACIONES:
            if col not in {r[1] for r in con.execute("PRAGMA table_info(operations)")}:
                if col == "declared_scope":
                    con.execute("ALTER TABLE operations ADD COLUMN declared_scope TEXT DEFAULT ''")
                elif col == "authorized_scope":
                    con.execute("ALTER TABLE operations ADD COLUMN authorized_scope TEXT DEFAULT ''")
                elif col == "auth_decision":
                    con.execute("ALTER TABLE operations ADD COLUMN auth_decision TEXT DEFAULT 'UNAUTH'")
                elif col == "auth_actor":
                    con.execute("ALTER TABLE operations ADD COLUMN auth_actor TEXT DEFAULT ''")
                elif col == "auth_timestamp":
                    con.execute("ALTER TABLE operations ADD COLUMN auth_timestamp TEXT DEFAULT ''")
        for col in EXPECTED_COLS_RESULTADOS:
            if col not in {r[1] for r in con.execute("PRAGMA table_info(results)")}:
                if col == "verified_scope":
                    con.execute("ALTER TABLE results ADD COLUMN verified_scope TEXT DEFAULT ''")
                elif col == "scope_decision":
                    con.execute("ALTER TABLE results ADD COLUMN scope_decision TEXT DEFAULT 'UNVERIFIED'")
                elif col == "limitations_json":
                    con.execute("ALTER TABLE results ADD COLUMN limitations_json TEXT DEFAULT '{}'")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _verify_and_return(work: str, src_sha: str, counts_before: Dict[str, int]) -> Dict[str, Any]:
    con = sqlite3.connect(work)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        cols_ops = _columnas_tabla(con, "operations")
        cols_res = _columnas_tabla(con, "results")
        counts_after = {t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
                         for t in ("operations","results","relations","edges","research","execution_events")}
        return {"integrity_after": integrity,
                "columns_operations": cols_ops,
                "columns_results": cols_res,
                "counts_before": counts_before,
                "counts_after": counts_after,
                "sha256_after": core_hash.hash_file(work),
                "preserved": all(counts_after[t] == counts_before[t] for t in counts_before)}
    finally:
        con.close()


def restore_from_snapshot(dst: str, snapshot: str) -> Dict[str, Any]:
    """Restaura `dst` desde `snapshot` y verifica hash exacto."""
    if not os.path.exists(snapshot):
        return {"status": "BLOCKED", "reason": "snapshot inexistente"}
    sha_snap = _sha(snapshot)
    shutil.copy2(snapshot, dst)
    sha_after = _sha(dst)
    ok = sha_snap == sha_after
    return {"status": "PASS" if ok else "BLOCKED",
            "sha256_snapshot": sha_snap,
            "sha256_after": sha_after,
            "restaurado": ok}


def run_repair(mapped_store: Optional[str] = None, work_copy: Optional[str] = None,
               keep_scratch: bool = False, origen: Optional[str] = None) -> Dict[str, Any]:
    ORIGEN_LOCAL = origen or ORIGEN
    IER_STORE = mapped_store or os.environ.get("IER_STORE", "/tmp/opencode/ier-f02-repair")
    os.makedirs(IER_STORE, exist_ok=True)
    WORK = work_copy or os.path.join(IER_STORE, "work.sqlite3")
    SNAPSHOT = os.path.join(IER_STORE, "snapshot.sqlite3")

    H_SRC = _sha(ORIGEN_LOCAL)
    if H_SRC != EXPECTED_SHA256:
        return {"status": "BLOCKED", "mission_id": None,
                "reasons": ["origen no coincide con esperado; no se opera"],
                "epistemic": "BLOCKED", "operational": "BLOCKED"}

    # copia sellada de trabajo
    if os.path.exists(WORK):
        os.remove(WORK)
    shutil.copy2(ORIGEN_LOCAL, WORK)
    if _sha(WORK) != H_SRC:
        return {"status": "BLOCKED",
                "reasons": ["copia en WORK no coincide con origen"],
                "epistemic": "BLOCKED", "operational": "BLOCKED"}

    # snapshot (backup adicional para rollback)
    shutil.copy2(WORK, SNAPSHOT)

    # precondiciones
    pre = _schema_preconditions(WORK)

    # misión
    mision_id = None
    m = mission.cargar("nonexistent", path=IER_STORE) if False else None
    mis = mission.nuevo(
        identity={"project": "rxre-ee", "issue": "F-02", "commit": "cb86b9e0"},
        target={"path": ORIGEN_LOCAL, "artifact_sha256": H_SRC, "size_bytes": os.path.getsize(ORIGEN_LOCAL),
                "type": "sqlite", "architecture": "x86-64", "build_flags": None},
        problem={"observed_behavior": "pre-M281: faltan 8 columnas M281",
                 "expected_behavior": "operaciones pueden persistirse",
                 "reproduction": "conectar(storage/rxre.sqlite3)+registrar(...)"},
        path=IER_STORE)
    mission.añadir_hipotesis(mis["mission_id"],
        "Esquema pre-M281 en la DB operativa", path=IER_STORE)
    mission.fijar_outcome(mis["mission_id"], "partial",
        "diagnóstico evidenciado; reparación controlada planificada", path=IER_STORE)

    # aplicar reparación
    repair_sha = None
    post = None
    repair_ok = False
    try:
        _repair_copy(WORK)
        repair_sha = _sha(WORK)
        post = _verify_and_return(WORK, H_SRC, pre["pre_counts"])
        repair_ok = post["integrity_after"] == "ok" and len(post["columns_operations"]) == 20 and len(post["columns_results"]) == 18
    except Exception as exc:
        repair_ok = False
        repair_sha = None
        post = None

    # registrar reparación (sobre la COPIA migrada, nunca sobre la protegida)
    op_id = None
    _post_reg = "repair not ok"
    if repair_ok and post:
        ws = store.conectar(WORK)
        try:
            op_id = store.registrar(ws, {"target": "/bin/ls", "capability": "F-02-repair",
                                        "contract_version": "1.0",
                                        "question": "repair F-02 controlado"},
                                {"status": "ok", "operation": "F-02-repair",
                                 "results": [{"result_id": "F02-REPAIR-1", "type": "ok"}]})
        except Exception as exc:
            repair_ok = False
            _post_reg = str(exc)
            op_id = None
        ws.close()
    else:
        _post_reg = "repair failed"

    #rollback si falló la verificación posterior
    # distinguir dos cosas diferentes:
    #   rollback_restored = true si el snapshot devolvió el original (rollback exitoso)
    #   repair_ok        = true solo si la reparación se verificó (integrity==ok + columnas esperadas)
    if repair_ok and post:
        rollback_res = {"status": "NOT_APPLICABLE", "sha256_after": repair_sha, "restaurado": False}
    else:
        rollback_res = restore_from_snapshot(WORK, SNAPSHOT)
        rollback_restored = rollback_res.get("status") == "PASS" and bool(rollback_res.get("restaurado"))
        # si la reparación falló pero el rollback restaura, el resultado operativo es FAIL con restauración verificada
        repair_ok = False

    # cerrar misión
    mis_final = mission.cargar(mis["mission_id"], path=IER_STORE)
    pid = mis_final["mission_id"]
    exp = {
        "repair_id": "repair-%s" % _sha_text(pid)[:16],
        "mission_id": pid,
        "sha256_origen": H_SRC,
        "sha256_snapshot": _sha(SNAPSHOT),
        "sha256_reparada": repair_sha if repair_ok else None,
        "rollback": rollback_res,
        "rollback_restored": rollback_res.get("restaurado", False),
        "pre_integrity": pre["pre_integrity"],
        "pre_counts": pre["pre_counts"],
        "post_integrity": post["integrity_after"] if post else None,
        "post_counts": post["counts_after"] if post else None,
        "registrar_op_id": op_id if repair_ok else None,
        "repair_ok": repair_ok,
        "epistemic": "PARTIAL",
        "operational": "PASS" if repair_ok else "FAIL",
    }
    mission.añadir_experimento(mis["mission_id"], "reparacion_controlada", exp, path=IER_STORE)
    mis_cierre = mission.cargar(mis["mission_id"], path=IER_STORE)

    scratch_keep = keep_scratch
    return {"mission_id": pid, "work_copy": WORK, "snapshot": SNAPSHOT,
            "repair_ok": repair_ok,
            "operational": exp["operational"],
            "epistemic": exp["epistemic"],
            "result": exp,
            "cleanup": "kept" if scratch_keep else "all-in-tmp"}
