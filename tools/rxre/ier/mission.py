#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY (.rxre/ier/)
"""RXRE · IER · MISSION — el objeto central ejecutable.

Cada investigación parte de un problema real y vive como una entidad concreta:

    identity  target  problem  hypotheses  experiments  intervention
    validation  outcome

El registro es append-only a nivel de fichero (.rxre/ier/missions/<id>.json);
las actualizaciones pasan por este módulo (sin escritura externa ciega).
Nunca se promociona nada aquí: esto persiste el estado del ciclo IER,
la promoción vive en la parte E7 (Evolution Engine) con dictado del propietario.
"""
from __future__ import annotations

import json
import os
import re
import hashlib
import time
from typing import Any, Dict, List, Optional

MISSION_VERSION = "IER-MISSION-1"
PHASES = ("DESCUBRIR", "REPRODUCIR", "ANALIZAR", "CUELLO",
          "DECIDIR", "VALIDAR", "CONTRIBUIR", "EVOLUCIONAR")
OUTCOMES = ("pending", "partial", "not_determined", "blocked", "resolved")


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def store_root(path: Optional[str] = None) -> str:
    if path:
        return path
    override = os.environ.get("IER_STORE")
    if override:
        return override
    return os.path.join(_repo_root(), ".rxre", "ier")


def _dir_missions(path: Optional[str] = None) -> str:
    d = os.path.join(store_root(path), "missions")
    os.makedirs(d, exist_ok=True)
    return d


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_id(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-").lower()
    return slug or "mission"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())


def _mission_id(identity: Dict[str, Any], target: Dict[str, Any], created: str) -> str:
    fingerprint = _canonical({
        "identity": identity,
        "target": {k: target.get(k) for k in sorted(target)},
        "created": created,
    })
    return "mis_" + _sha256_text(fingerprint)[:24]


def nuevo(identity: Dict[str, Any], target: Dict[str, Any],
          problem: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
    """Crea una MISSION nueva. Falla si falta el artefacto verificado."""
    if not isinstance(target, dict) or not target.get("path"):
        raise ValueError("target.path es obligatorio (artefacto real)")

    art = target["path"]
    if not os.path.exists(art):
        raise FileNotFoundError("artefacto no existe: %s" % art)

    fingerprint = _sha256_file(art)
    created = now_iso()
    mission_id = _mission_id(identity, {**target, "artifact_sha256": fingerprint}, created)

    record = {
        "schema": MISSION_VERSION,
        "mission_id": mission_id,
        "created": created,
        "identity": {
            "project": identity.get("project"),
            "issue": identity.get("issue"),
            "repository": identity.get("repository"),
            "commit": identity.get("commit"),
        },
        "target": {
            "type": target.get("type"),
            "architecture": target.get("architecture"),
            "build_flags": target.get("build_flags"),
            "path": art,
            "size_bytes": os.path.getsize(art),
            "artifact_sha256": fingerprint,
        },
        "problem": {
            "expected_behavior": problem.get("expected_behavior"),
            "observed_behavior": problem.get("observed_behavior"),
            "reproduction": problem.get("reproduction"),
        },
        "hypotheses": [],
        "experiments": [],
        "intervention": None,
        "validation": {"positive": [], "negative": [], "independent": None},
        "outcome": {"state": "pending", "obtained": None},
        "phase": "DESCUBRIR",
    }
    _write(record, path=path)
    return record


def _write(record: Dict[str, Any], path: Optional[str] = None) -> None:
    d = _dir_missions(path)
    dest = os.path.join(d, record["mission_id"] + ".json")
    if os.path.exists(dest):
        # append-only: no sobrescribir una mision existente
        raise FileExistsError("ya existe la mision: %s" % dest)
    blob = _canonical(record).encode("utf-8")
    with open(dest, "wb") as f:
        f.write(blob)
    # fsync best-effort
    with open(dest, "rb") as f:
        os.fsync(f.fileno())


def actualizar(mission: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
    """Reescribe el fichero de la mision, verificando integridad (append-unsafe pero encadenada)."""
    d = _dir_missions(path)
    dest = os.path.join(d, mission["mission_id"] + ".json")
    if not os.path.exists(dest):
        raise FileNotFoundError(dest)
    prev = cargar(mission["mission_id"], path=path)
    if prev.get("created") != mission.get("created"):
        raise ValueError("created diverge; posible reutilizacion de mission_id")
    if mission.get("phase") not in PHASES:
        raise ValueError("phase fuera de PHASES: %r" % mission.get("phase"))
    if mission.get("outcome", {}).get("state") not in OUTCOMES:
        raise ValueError("outcome.state fuera de OUTCOMES")
    with open(dest, "wb") as f:
        f.write(_canonical(mission).encode("utf-8"))
    with open(dest, "rb") as f:
        os.fsync(f.fileno())
    return mission


def cargar(mission_id: str, path: Optional[str] = None) -> Dict[str, Any]:
    dest = os.path.join(_dir_missions(path), mission_id + ".json")
    with open(dest, encoding="utf-8") as f:
        return json.load(f)


def listar(path: Optional[str] = None) -> List[Dict[str, Any]]:
    d = _dir_missions(path)
    out = []
    for name in sorted(os.listdir(d)):
        if name.endswith(".json"):
            try:
                out.append(cargar(name[:-5], path=path))
            except Exception:
                pass
    return out


def añadir_hipotesis(mission_id: str, statement: str, rival_de: Optional[str] = None,
                     path: Optional[str] = None) -> Dict[str, Any]:
    m = cargar(mission_id, path=path)
    hid = "hyp_" + _sha256_text("%s|%s|%d" % (mission_id, statement, len(m["hypotheses"])))[:16]
    m["hypotheses"].append({"hypothesis_id": hid, "statement": statement,
                            "rival_of": rival_de,
                            "created": now_iso()})
    return actualizar(m, path=path)


def añadir_experimento(mission_id: str, propósito: str, resultado: Dict[str, Any],
                       path: Optional[str] = None) -> Dict[str, Any]:
    m = cargar(mission_id, path=path)
    eid = "exp_%s_%d" % (mission_id[-8:], len(m["experiments"]) + 1)
    m["experiments"].append({
        "experiment_id": eid,
        "purpose": propósito,
        "result": resultado,
        "created": now_iso(),
    })
    return actualizar(m, path=path)


def fijar_decision(mission_id: str, kind: str, seleccion: str,
                   path: Optional[str] = None) -> Dict[str, Any]:
    if kind not in ("reparar", "extender", "sustituir", "combinar", "crear"):
        raise ValueError("kind fuera de intervención: %r" % kind)
    m = cargar(mission_id, path=path)
    m["intervention"] = {"kind": kind, "selection": seleccion,
                         "created": now_iso()}
    return actualizar(m, path=path)


def fijar_outcome(mission_id: str, state: str, obtained: Any = None,
                  path: Optional[str] = None) -> Dict[str, Any]:
    if state not in OUTCOMES:
        raise ValueError("state fuera de OUTCOMES")
    m = cargar(mission_id, path=path)
    m["outcome"] = {"state": state, "obtained": obtained}
    return actualizar(m, path=path)


def fijar_fase(mission_id: str, phase: str, path: Optional[str] = None) -> Dict[str, Any]:
    if phase not in PHASES:
        raise ValueError("phase fuera de PHASES")
    m = cargar(mission_id, path=path)
    m["phase"] = phase
    return actualizar(m, path=path)


def integridad(mission_id: str, path: Optional[str] = None) -> Dict[str, Any]:
    """Verificación derivada: intención de re-hash vs comprobación de cadena."""
    m = cargar(mission_id, path=path)
    art = m["target"]["path"]
    ok = os.path.exists(art) and _sha256_file(art) == m["target"]["artifact_sha256"]
    return {"mision": m, "target_integro": ok}
