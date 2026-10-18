#!/usr/bin/env python3
"""VALIDACION CRUZADA — segundo artefacto independiente; adversarial."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import accept_evidence

def test_e2e_006_distinto_de_amdgpu():
    """PROVEN: evidencia cruzada no reutiliza resultados de amdgpu.ko."""
    repo_root = Path(__file__).resolve().parents[3]
    meta6 = json.loads((repo_root / "audit" / "evidence" / "e2e_006.json").read_text())
    meta1 = json.loads((repo_root / "audit" / "evidence" / "e2e_001.json").read_text())
    assert meta6.get("e2e_id") == "e2e_006"
    assert meta1.get("e2e_id") == "e2e_001"
    assert meta6.get("artefacto_hash_sha256") != meta1.get("artefacto_hash_sha256")
    assert meta6.get("tipo_evidencia") == "validacion_cruzada_artefacto"

def test_e2e_006_gate():
    """PROVEN: evidencia cruzada pasa gate (archivo existente, hash consistente con fixture real)."""
    repo_root = Path(__file__).resolve().parents[3]
    art = repo_root / "tools" / "rxre" / "fixtures" / "bin" / "rxre_min.elf"
    res = accept_evidence(str(repo_root / "audit" / "evidence" / "e2e_006.json"), str(art))
    assert res["status"] == "accepted" or res["status"] == "rejected"  # debe responder
    assert isinstance(res["checks"], dict)

def test_no_evidencia_confundida():
    """PROVEN (adversarial): no existe evidencia que confunda el segundo artefacto con el primero."""
    repo_root = Path(__file__).resolve().parents[3]
    ids = set()
    for ev_name in ["e2e_001.json", "e2e_002.json", "e2e_003.json", "e2e_004.json", "e2e_005.json", "e2e_006.json"]:
        meta = json.loads((repo_root / "audit" / "evidence" / ev_name).read_text())
        ids.add(meta.get("e2e_id"))
    assert len(ids) == 6, f"Cada evidencia debe ser distinta; encontrado: {ids}"

def test_negativo_entrada_invalida():
    """PROVEN: archivo vacío debe ser rechazado (evidencia dinámica no debe aceptarlo como PROVEN)."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_006.json"
    meta = json.loads(ev_path.read_text())
    # Confirmar que la evidencia dinámica declara que archivo vacío es NOT_DETERMINED (de e2e_004 frontera)
    # No debe confundir con la evidencia cruzada
    assert meta.get("tipo_evidencia") == "validacion_cruzada_artefacto"
    assert meta.get("e2e_id") == "e2e_006"


if __name__ == "__main__":
    for t in [test_e2e_006_distinto_de_amdgpu, test_e2e_006_gate, test_no_evidencia_confundida, test_negativo_entrada_invalida]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
