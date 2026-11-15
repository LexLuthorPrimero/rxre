#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY
"""RXRE · IER · UPSTREAM — paquete de contribución verificado, listo para revisión.

Empaqueta un parche + evidencia + alcance para su envío upstream. NO publica
nada: el envío real (PR/push/email) es siempre dictado del propietario.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def construir(mission_id: str, target_repo: str, probable_upstream: str,
              patch_file: str, evidencia: List[Dict[str, Any]],
              alcance: str, limitaciones: List[str],
              path: Optional[str] = None) -> Dict[str, Any]:
    if not os.path.isfile(patch_file):
        raise FileNotFoundError(patch_file)
    pkg_id = "pkg_" + hashlib.sha256(
        ("%s|%s|%s|%s" % (mission_id, target_repo, patch_file,
                           json.dumps(evidencia, sort_keys=True))).encode()
    ).hexdigest()[:16]
    patch_sha = _sha256_file(patch_file)
    pkg = {
        "schema": "IER-UPSTREAM-1",
        "package_id": pkg_id,
        "mission_id": mission_id,
        "target_repo": target_repo,
        "probable_upstream": probable_upstream,
        "patch": {"file": patch_file, "sha256": patch_sha},
        "evidencia": list(evidencia),
        "alcance": alcance,
        "limitaciones": list(limitaciones),
        "ready_for_review": bool(evidencia and alcance),
        "created": _now(),
    }
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, indent=2, ensure_ascii=False)
    return pkg


def verificar_pkg(pkg_file: str) -> Dict[str, Any]:
    pkg = json.load(open(pkg_file, encoding="utf-8"))
    errores = []
    if not pkg.get("evidencia"):
        errores.append("paquete sin evidencia: no se envia")
    if not pkg.get("alcance"):
        errores.append("paquete sin alcance declarado: no se envia")
    if not os.path.isfile(pkg["patch"]["file"]):
        errores.append("patch_file no existe")
    else:
        if _sha256_file(pkg["patch"]["file"]) != pkg["patch"]["sha256"]:
            errores.append("patch sha256 no coincide con el sellado")
    if not pkg.get("ready_for_review"):
        errores.append("ready_for_review=false: paquete no listo")
    return {"integridad_ok": not errores, "errores": errores,
            "package_id": pkg.get("package_id")}


def reporte_revision(pkg_file: str) -> str:
    v = verificar_pkg(pkg_file)
    if not v["integridad_ok"]:
        return "RECHAZO: %s (%s)" % (v["package_id"], "; ".join(v["errores"]))
    return ("LISTO para revisión por el propietario; "
            "package_id=%s; nada se envia sin dictado" % v["package_id"])
