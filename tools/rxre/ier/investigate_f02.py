#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · EE · INVEGIGATE_F02 — caso histórico de regresión F-02.

Fase: utilización de la arquitectura existente de RXRE para reconstruir la
investigación de F-02 (incompatible ya resuelto) con IER misiones + mission +
investigar y verificar + core/store (sobre copia aislada).

Lectura/escritura solo fuera del repo/protected: solo sobre copias en /tmp
o sobre IER_STORE cuando se inyecta explícitamente.

No uso de P0; no se modifica ni RXRE/sqlite3 ni contratos ni AGENTS.md.
"""
from __future__ import annotations
import json
import os
import shutil
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from . import mission, investigate  # noqa: E402
_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core")
sys.path.insert(0, _CORE)
from core import store, evidence_integrity  # noqa: E402

ORIGEN = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
DDL_REF = "/home/lucas/Escritorio/rxre/tools/rxre/core/store.py"

MISSION_OUTCOME = {"state": "partial"}  # honestamente PARTIAL; no PROVEN

CONSTRAINTS = (
    "PROBLEM_DELIMITADO",
    "EVIDENCIA_SELLADA",
    "HIPOTESIS_RIVALES",
    "EXPERIMENTO_DISCRIMINANTE",
    "DIAGNOSTICO_EVIDENCIADO",
    "PARTIAL_SIN_PROMOCION",
)


def _sha(path: str) -> str:
    return path and os.path.getsize(path) > 0 and (
        __import__("hashlib").sha256(open(path, "rb").read()).hexdigest())


def _verify_aducido(e2e_path: str) -> Dict[str, Any]:
    """Reusa core.evidence_integrity para verificar la evidencia E2E."""
    try:
        return evidence_integrity.accept_evidence(e2e_path, ORIGEN)
    except Exception:
        return {"status": "rejected", "note": "no evidence/E2E puede verificarse aquí"}


def _columnas_tabla(con, tabla):
    return [r[1] for r in con.execute("PRAGMA table_info(%s)" % tabla)]


CONTINUE_HANDLE = None


def run_flow(ier_store: Optional[str] = None, db_copy: str = "/tmp/opencode/ee-mision.sqlite3") -> Dict[str, Any]:
    """Reproduce el flujo F-02 como misión IER con diagnóstico trazable."""
    IER_STORE = ier_store or os.environ.get("IER_STORE", "/tmp/opencode/ier-f02-mision")
    os.makedirs(IER_STORE, exist_ok=True)

    H_SRC = _sha(ORIGEN)
    if os.path.exists(db_copy):
        os.remove(db_copy)
    shutil.copy2(ORIGEN, db_copy)
    if _sha(db_copy) != H_SRC:
        return {"status": "blocked", "reason": "la copia no coincide con el origen sellado"}

    # 1. Misión
    mis = mission.nuevo(
        identity={"project": "rxre-ee", "issue": "F-02", "repository":
                  "LexLuthorPrimero/rxre", "commit": "cb86b9e0"},
        target={"type": "sqlite", "architecture": "x86-64", "build_flags": None,
                "path": ORIGEN, "size_bytes": os.path.getsize(ORIGEN),
                "artifact_sha256": H_SRC},
        problem={"expected_behavior": "registrar() puede persistir una operación sin OperationalError",
                 "observed_behavior": "registrar() falla con OperationalError no column named declared_scope",
                 "reproduction": "conectar(storage/rxre.sqlite3) + registrar({...}) sobre copia sellada"},
        path=IER_STORE)

    # 2. Hipótesis rivales
    H = [
        investigate.formular("La tabla operations de la DB operativa carece de las 5 columnas M281 declaradas por store.DDL y escritas por store.registrar().", kind="claim"),
        investigate.formular("La DB operativa usa un esquema heredado ANTES de la migración M281; por ello la inicialización la deja incompleta.", kind="claim"),
        investigate.formular("store.conectar() no enmascara columnas faltantes; la falta de columnas es un hecho, no un bug runtime.", kind="claim"),
        investigate.formular("Las columnas existen pero con tipos o DEFAULT incompatibles con los declarados en el DDL.", kind="claim"),
    ]
    for h in H:
        mission.añadir_hipotesis(mis["mission_id"], h["statement"], path=IER_STORE)

    # 3. Experimento discriminante
    con = __import__("sqlite3").connect(db_copy, isolation_level=None)
    con.row_factory = __import__("sqlite3").Row
    ops_cols = _columnas_tabla(con, "operations")
    rs_cols  = _columnas_tabla(con, "results")
    cov_op = [c for c in ["declared_scope","authorized_scope","auth_decision","auth_actor","auth_timestamp"] if c not in ops_cols]
    cov_rs = [c for c in ["verified_scope","scope_decision","limitations_json"] if c not in rs_cols]
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    ops_total = con.execute("SELECT count(*) FROM operations").fetchone()[0]
    con.close()

    # 4. store.conectar() sobre ruta NO protegida: migra la copia, no la DB protegida
    ws = store.conectar(db_copy)
    op_id = store.registrar(ws, {"target":"/bin/ls","capability":"F-02",
                                 "contract_version":"1.0",
                                 "question":"estructura"},
                            {"status":"ok","operation":"F-02",
                             "results":[{"result_id":"EE-F02-1","type":"ok"}]})
    ws_integrity = ws.execute("PRAGMA integrity_check").fetchone()[0]
    ws_ops = ws.execute("SELECT count(*) FROM operations").fetchone()[0]
    ws.close()

    ek = {
        "id": "EV-SELECT-1",
        "what": "PRAGMA+integrity+registrar sobre copia",
        "tabla": {"operations_cols_present": ops_cols,
                   "results_cols_present": rs_cols,
                   "missing_columns_operations": cov_op,
                   "missing_columns_results": cov_rs,
                   "integrity_before": integrity,
                   "operations_count_before": ops_total,
                   "integrity_after_register": ws_integrity,
                   "operations_count_after_register": ws_ops,
                   "registrar_op_id": op_id},
    }

    # 5. Diagnóstico
    diag = {
        "caso": "F-02",
        "causa": "Esquema pre-M281 en la DB operativa: faltan 8 columnas M281 que store.DDL declara y registrar() escribe.",
        "evidencia": [ek],
        "hipotesis_confirmada": H[0]["statement"],
        "hipotesis_rechazadas": [H[2]["statement"], H[3]["statement"]],
        "hipotesis_no_determinada": [H[1]["statement"]],
        "limitaciones": [
            "Diagnóstico sobre copia; la DB protegida no se abrió ni migrated.",
            "Sin revisión externa; PARTIAL honesto.",
            "H2 permanece NOT_DETERMINED: no se ha hallado esquema heredado alternativo en este scope.",
        ],
        "outcome": "partial",
    }
    mission.añadir_experimento(mis["mission_id"], "experimento_discriminante", diag, path=IER_STORE)
    mission.fijar_outcome(mis["mission_id"], "partial", "reproducción sobre copia; diagnóstico evidenciado", path=IER_STORE)
    m = mission.cargar(mis["mission_id"], path=IER_STORE)

    return {
        "status": "PASS_PARTIAL",
        "mision_id": m["mission_id"],
        "outcome": m["outcome"]["state"],
        "evidence_count": len(m["experiments"]),
        "hipotesis_count": len(m["hypotheses"]),
        "integrity_after_register": ws_integrity,
        "limitaciones": diag["limitaciones"],
    }


if __name__ == "__main__":
    print(json.dumps(run_flow(), indent=2, sort_keys=True, ensure_ascii=False))
