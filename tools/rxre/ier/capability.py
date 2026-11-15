#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY (.rxre/ier/)
"""RXRE · IER · CAPABILITY — registro de capacidades promocionables.

Distingue rigorosamente:
  SOLUCIÓN PUNTUAL  -> arreglar una incidencia
  CAPACIDAD         -> utilidad verificada reutilizable con dominio/límites

Ciclo de vida: DECLARED -> EXECUTED -> VERIFIED -> PROMOTED -> RETIRED.
La promoción a PROMOTED NUNCA es automática: exige el certificado de
verificación interna, la firma del propietario (dictado) y no-regresión
medida (suite mínima verde o failure documentado). Este módulo NO firma nada.
"""
from __future__ import annotations

import json
import os
import hashlib
from typing import Any, Dict, List, Optional

CAPABILITY_VERSION = "IER-CAPABILITY-1"
STATUS = ("DECLARED", "EXECUTED", "VERIFIED", "PROMOTED", "RETIRED")

CRITERIA = ("RESOLVES", "NEGATIVE_CONTROL", "BOUNDARIES", "REPRODUCTION",
            "INDEPENDENCE")


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def store_root() -> str:
    override = os.environ.get("IER_STORE")
    if override:
        return override
    return os.path.join(_repo_root(), ".rxre", "ier")


def _dir_capabilities(path: Optional[str] = None) -> str:
    d = os.path.join(store_root() if not path else path, "capabilities")
    os.makedirs(d, exist_ok=True)
    return d


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def declarar(name: str, purpose: str, domain: str, ruta: str, version: str = "v0.0.0",
             limitations: Optional[List[str]] = None,
             dependencies: Optional[List[Dict[str, Any]]] = None,
             source_mission_id: Optional[str] = None,
             path: Optional[str] = None) -> Dict[str, Any]:
    if not os.path.isfile(ruta):
        raise FileNotFoundError("ruta de capacidad no existe: %s" % ruta)
    fingerprint = _sha256_file(ruta)
    rel = os.path.relpath(ruta, _repo_root()) if os.path.exists(ruta) else ruta
    cap_id = "cap_" + _sha256_text(_canonical({
        "name": name, "purpose": purpose, "domain": domain,
        "artifact_sha256": fingerprint, "version": version,
    }))[:16]

    record = {
        "schema": CAPABILITY_VERSION,
        "capability_id": cap_id,
        "name": name,
        "purpose": purpose,
        "domain": domain,
        "execution": {
            "kind": "module",
            "path": rel,
            "artifact_sha256": fingerprint,
        },
        "version": version,
        "limitations": list(limitations or []),
        "dependencies": list(dependencies or []),
        "status": "DECLARED",
        "source_mission_id": source_mission_id,
        "verifications": {c: {"status": "NOT_EXECUTED"} for c in CRITERIA},
        "created": strftime_now(),
        "updated": strftime_now(),
        "history": [],
    }
    _write(record, path)
    return record


def strftime_now() -> str:
    return __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z", __import__("time").gmtime())


def _write(record: Dict[str, Any], path: Optional[str] = None) -> None:
    d = _dir_capabilities(path)
    dest = os.path.join(d, record["capability_id"] + ".json")
    if os.path.exists(dest):
        raise FileExistsError("ya existe la capacidad: %s" % dest)
    with open(dest, "wb") as f:
        f.write(_canonical(record).encode("utf-8"))
    with open(dest, "rb") as f:
        os.fsync(f.fileno())


def cargar(capability_id: str, path: Optional[str] = None) -> Dict[str, Any]:
    dest = os.path.join(_dir_capabilities(path), capability_id + ".json")
    with open(dest, encoding="utf-8") as f:
        return json.load(f)


def listar(path: Optional[str] = None) -> List[Dict[str, Any]]:
    d = _dir_capabilities(path)
    out = []
    for name in sorted(os.listdir(d)):
        if name.endswith(".json"):
            try:
                out.append(cargar(name[:-5], path=path))
            except Exception:
                pass
    return out


def _write_overwrite(record: Dict[str, Any], path: Optional[str] = None) -> None:
    d = _dir_capabilities(path)
    dest = os.path.join(d, record["capability_id"] + ".json")
    with open(dest, "wb") as f:
        f.write(_canonical(record).encode("utf-8"))
    with open(dest, "rb") as f:
        os.fsync(f.fileno())


def transitar(capability_id: str, nuevo_status: str, motivo: str = "",
              path: Optional[str] = None) -> Dict[str, Any]:
    if nuevo_status not in STATUS:
        raise ValueError("status fuera de STATUS")
    cap = cargar(capability_id, path=path)
    orden = {s: i for i, s in enumerate(STATUS)}
    if orden[nuevo_status] < orden[cap["status"]]:
        raise ValueError("transicion regresiva: %s -> %s" % (cap["status"], nuevo_status))
    if nuevo_status == "PROMOTED":
        raise PermissionError("PROMOTED es dictado del propietario; este módulo no firma")
    cap["history"].append({"when": strftime_now(), "from": cap["status"],
                            "to": nuevo_status, "reason": motivo})
    cap["status"] = nuevo_status
    cap["updated"] = strftime_now()
    _write_overwrite(cap, path)
    return cap


def registrar_verificacion(capability_id: str, criterio: str, status: str,
                           refs: Optional[List[str]] = None,
                           detalle: str = "",
                           path: Optional[str] = None) -> Dict[str, Any]:
    if criterio not in CRITERIA:
        raise ValueError("criterio fuera de CRITERIA")
    if status not in ("PASS", "FAIL", "NOT_EXECUTED", "PENDING_EXTERNAL_REVIEWER"):
        raise ValueError("status de verificación fuera de dominio")
    cap = cargar(capability_id, path=path)
    cap["verifications"][criterio] = {
        "status": status,
        "refs": list(refs or []),
        "detail": detalle,
        "verified_at": strftime_now(),
    }
    cap["updated"] = strftime_now()
    _write_overwrite(cap, path)
    return cap


def resumen_verificacion(capability_id: str,
                         path: Optional[str] = None) -> Dict[str, Any]:
    cap = cargar(capability_id, path=path)
    verifs = cap["verifications"]
    return {
        "capability_id": capability_id,
        "criteria": {c: verifs[c]["status"] for c in CRITERIA},
        "reproducible": verifs["REPRODUCTION"]["status"] == "PASS",
        "independent": verifs["INDEPENDENCE"]["status"],
        "promoted": cap["status"] == "PROMOTED",
    }
