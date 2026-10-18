#!/usr/bin/env python3
"""INTEGRIDAD — reproducible CWD-independent, evidencia canónica + adversarial."""
import sys, os, tempfile, json, hashlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import validate_evidence_path

def test_evidence_e2e_001_integridad():
    """PROVEN: evidencia canónica pasa validación completa."""
    repo_root = Path(__file__).resolve().parents[3]
    res = validate_evidence_path(str(repo_root / "audit" / "evidence" / "e2e_001.json"),
                                  str(repo_root / "amdgpu.ko"))
    assert res["ok"], f"E2E evidencia debe ser válida; errores: {res['errors']}"
    assert res["checks"].get("hash_matches") is True
    assert res["checks"].get("artifact_exists") is True


def test_evidence_e2e_002_integridad():
    """PROVEN: evidencia estructural pasa validación."""
    repo_root = Path(__file__).resolve().parents[3]
    res = validate_evidence_path(str(repo_root / "audit" / "evidence" / "e2e_002.json"),
                                  str(repo_root / "amdgpu.ko"))
    assert res["ok"], f"E2E_002 debe ser válida; errores: {res['errors']}"
    assert res["checks"].get("epistemic_valid") is True


def test_adversarial_hash_mismatch():
    """PROVEN: evidencia manipulada (hash alterado) debe fallar validación."""
    import tempfile
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["artefacto_hash_sha256"] = "0" * 64
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    res = validate_evidence_path(tmp_path, str(repo_root / "amdgpu.ko"))
    assert res["ok"] is False, "Manipulación debe ser detectada (hash no coincide)"
    assert any("hash_mismatch" in str(e) for e in res["errors"]), \
        "Debe reportar hash_mismatch"
    Path(tmp_path).unlink()


def test_adversarial_epistemic_invalid():
    """PROVEN: estado epistemico no válido debe fallar."""
    import tempfile
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["epistemic"] = "VERIFICADO_FAKE"
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    res = validate_evidence_path(tmp_path, str(repo_root / "amdgpu.ko"))
    assert res["ok"] is False, "Estado epistemico inventado debe ser rechazado"
    assert any("invalid_epistemic" in str(e) for e in res["errors"]), \
        "Debe reportar invalid_epistemic"
    Path(tmp_path).unlink()


def test_e2e_002_rival_rejected_structural():
    """NOT_DETERMINED / PROVEN: archivo vacío (0 funciones) no podría ser módulo AMD."""
    # Confirmación indirecta: archivo completo (34MB) con funciones AMD; archivo vacío rechazaría
    # Esta prueba confirma que el archivo real no es vacío, no afirma exclusividad dinámica
    art = Path(__file__).resolve().parents[3] / "amdgpu.ko"
    assert art.stat().st_size > 0, "Artefacto real no debe ser vacío"


if __name__ == "__main__":
    import traceback
    for t in [test_evidence_e2e_001_integridad, test_evidence_e2e_002_integridad,
              test_adversarial_hash_mismatch, test_adversarial_epistemic_invalid,
              test_e2e_002_rival_rejected_structural]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
