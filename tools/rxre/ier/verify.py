#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY
"""RXRE · IER · VERIFY — certificado de verificación independiente.

La diferencia del IER frente a autochequeo: una capacidad certificada solo
existe cuando OTRO oráculo (que no escribió el código) confirma el resultado.
El certificado conserva hashes sellados y evidencia verificable. Nada de esto
ele la capacidad a PROVEN: promocion a PROMOTED es dictado del propietario.
"""
from __future__ import annotations
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

SCHEMA = "IER-CERTIFICATE-1"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _independencia_ok(prod: str, ora: str) -> bool:
    p, o = prod.lower(), ora.lower()
    if p == o:
        return False
    # subcadena en cualquier direccion => mismo sustrato o derivado
    return p not in o and o not in p


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def emitir(mission_id: str, artefacto: str,
           verificaciones: List[Dict[str, Any]],
           oraculo_independiente: Dict[str, Any],
           estado: str = "PARTIAL",
           path: Optional[str] = None) -> Dict[str, Any]:
    """Genera un certificado. Oraculo DEBE ser distinto del productor."""
    if not verificaciones:
        raise ValueError("se exigen verificaciones reales; no se emite vacío")
    art_sha = _sha256_file(artefacto)
    cert_id = "cert_" + _sha256_text(
        "%s|%s|%s|%s" % (mission_id, art_sha,
                          json.dumps(verificaciones, sort_keys=True),
                          json.dumps(oraculo_independiente, sort_keys=True)))[:16]
    cert = {
        "schema": SCHEMA,
        "certificate_id": cert_id,
        "mission_id": mission_id,
        "artifact": {"path": artefacto,
                     "sha256": art_sha},
        "verifications": verificaciones,
        "independent_oracle": oraculo_independiente,
        "state": estado,
        "issued": _now(),
        "license": "PARTIAL honestly capped; PROVEN requiere dictado propietario",
    }
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(_canonical(cert))
    return cert


def verificar(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Revalida un certificado existente: errores explícitos."""
    errores = []
    a = cert.get("artifact", {})
    if not a:
        errores.append("artifact ausente")
    else:
        h = hashlib.sha256()
        with open(a["path"], "rb") as f:
            h.update(f.read())
        if h.hexdigest() != a.get("sha256"):
            errores.append("artifact sha256 no coincide con el sellado")
    indep = cert.get("independent_oracle", {})
    prod = indep.get("producer_of_result")
    ora = indep.get("oracle_tool")
    if not prod or not ora:
        errores.append("oraculo_independiente incompleto (producer/oracle_tool)")
    elif not _independencia_ok(prod, ora):
        errores.append("el productor es su propio oraculo: no hay independencia")
    return {"integridad_ok": not errores, "errores": errores}


def decidir(cert: Dict[str, Any]) -> str:
    """Decisión honesta: solo promoción bajo dictado; tuya."""
    v = verificar(cert)
    if not v["integridad_ok"]:
        return "REJECT"
    fails = [x for x in cert.get("verifications", [])
             if x.get("result") == "FAIL"]
    passes = [x for x in cert.get("verifications", [])
              if x.get("result") == "PASS"]
    if fails:
        return "REJECT"
    if not passes:
        return "NOT_DETERMINED"
    return "PARTIAL"
