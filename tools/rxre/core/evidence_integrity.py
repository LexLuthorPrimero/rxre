#!/usr/bin/env python3
"""VALIDACIÓN DE INTEGRIDAD DE EVIDENCIA RXRE.
Verifica que evidencia E2E/E2 coincide con artefacto real y esquema válido.
No modifica evidencia canónica; solo lee.
"""
import hashlib, json, sys
from pathlib import Path

VALID_EPISTEMIC = {"PROVEN", "PARTIAL", "NOT_DETERMINED", "PROVEN_ABSENT", "DEFERRED", "INVALIDATED", "OBSERVED", "VALID"}
REQUIRED_E2E = {"e2e_id", "artefacto_path", "artefacto_size_bytes", "artefacto_hash_sha256", "epistemic", "procedencia"}
REQUIRED_E2E2 = {"e2e_id", "parent_e2e", "tipo", "artefacto", "hash_sha256", "artefacto_size_bytes", "epistemic", "procedencia"}

def accept_evidence(ev_path: str, art_path: str = None) -> dict:
    """GATE DE EVIDENCIA — rechaza antes de aceptar; no destruye evidencia previa."""
    res = validate_evidence_path(ev_path, art_path)
    if res["ok"]:
        return {"status": "accepted", "evidence_path": ev_path, "checks": res["checks"], "errors": []}
    else:
        return {"status": "rejected", "evidence_path": ev_path, "checks": res["checks"], "errors": res["errors"], "note": "No se persistió; evidencia previa preservada"}


def validate_evidence_path(ev_path: str, art_path: str = None) -> dict:
    result = {"ok": False, "path": ev_path, "checks": {}, "errors": []}
    try:
        ev_path_obj = Path(ev_path)
        if not ev_path_obj.exists():
            result["errors"].append("evidence_path_missing")
            return result
        meta = json.loads(ev_path_obj.read_text())
        result["checks"]["json_valid"] = True

        # Schema check based on known keys
        if "parent_e2e" in meta:
            required = REQUIRED_E2E2
        else:
            required = REQUIRED_E2E
        missing = sorted(required - meta.keys())
        result["checks"]["required_keys"] = len(missing) == 0
        if missing:
            result["errors"].append(f"missing_keys: {missing}")

        # Epistemic validity
        ep = meta.get("epistemic")
        result["checks"]["epistemic_valid"] = ep in VALID_EPISTEMIC
        if ep not in VALID_EPISTEMIC:
            result["errors"].append(f"invalid_epistemic: {ep}")

        # Artifact provenance
        if art_path is None:
            # Derive from meta if present
            art_path = meta.get("artefacto_path") or meta.get("artefacto")
        if art_path:
            art = Path(art_path)
            if not art.exists():
                result["errors"].append(f"artifact_missing: {art_path}")
            else:
                result["checks"]["artifact_exists"] = True
                art_size = art.stat().st_size
                expected_size = meta.get("artefacto_size_bytes")
                result["checks"]["size_matches"] = (expected_size == art_size) if expected_size is not None else True
                if expected_size is not None and expected_size != art_size:
                    result["errors"].append(f"size_mismatch: expected={expected_size}, actual={art_size}")
                # Hash consistency
                expected_hash = meta.get("artefacto_hash_sha256", meta.get("hash_sha256", ""))
                if expected_hash:
                    h = hashlib.sha256(art.read_bytes()).hexdigest()
                    result["checks"]["hash_matches"] = h.startswith(expected_hash[:16])
                    if not result["checks"]["hash_matches"]:
                        result["errors"].append(f"hash_mismatch: expected={expected_hash[:16]}, actual={h[:16]}")
        else:
            result["checks"]["artifact_path_known"] = False

        result["ok"] = len(result["errors"]) == 0
    except Exception as exc:
        result["errors"].append(f"exception: {type(exc).__name__}: {exc}")
    return result
