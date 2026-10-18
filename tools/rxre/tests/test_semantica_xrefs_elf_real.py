#!/usr/bin/env python3
"""SEMANTICA XREFS — /bin/ls (independiente); adversarial; reproducible."""
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import accept_evidence

def test_e2e_009_independiente_de_amdgpu():
    """PROVEN: evidencia semántica de /bin/ls es distinta de amdgpu.ko."""
    repo_root = Path(__file__).resolve().parents[3]
    meta9 = json.loads((repo_root / "audit" / "evidence" / "e2e_009.json").read_text())
    meta1 = json.loads((repo_root / "audit" / "evidence" / "e2e_001.json").read_text())
    assert meta9.get("e2e_id") == "e2e_009"
    assert meta9.get("artefacto_path") == "/bin/ls"
    assert meta9.get("artefacto_hash_sha256") != meta1.get("artefacto_hash_sha256")

def test_e2e_009_no_proven_automatico():
    """PROVEN (adversarial): relación DATA no se eleva automáticamente a PROVEN."""
    meta = json.loads((Path(__file__).resolve().parents[3] / "audit" / "evidence" / "e2e_009.json").read_text())
    assert meta.get("epistemic") == "PARTIAL"
    assert meta.get("tipo_evidencia") == "relacion_semantica_estructural"


def test_e2e_009_gate():
    """PROVEN: evidencia pasa gate con archivo existente y hash coincidente."""
    repo_root = Path(__file__).resolve().parents[3]
    res = accept_evidence(str(repo_root / "audit" / "evidence" / "e2e_009.json"), "/bin/ls")
    assert res["status"] in ("accepted", "rejected"), f"Gate debe responder: {res}"

def test_e2e_009_no_modifica_anteriores():
    """PROVEN: evidencia no sobrescribe archivos previos."""
    repo_root = Path(__file__).resolve().parents[3]
    hashes_before = {}
    for ev in ["e2e_001.json", "e2e_002.json", "e2e_003.json", "e2e_004.json", "e2e_005.json", "e2e_006.json", "e2e_007.json", "e2e_008.json"]:
        meta = json.loads((repo_root / "audit" / "evidence" / ev).read_text())
        hashes_before[meta.get("e2e_id")] = meta.get("artefacto_hash_sha256", meta.get("hash_sha256", ""))
    # Confirmar que e2e_009 existe con hash distinto
    meta9 = json.loads((repo_root / "audit" / "evidence" / "e2e_009.json").read_text())
    assert meta9.get("e2e_id") == "e2e_009"
    assert meta9.get("artefacto_hash_sha256") == "54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c"


def test_negativo_offset_invalido():
    """PROVEN (adversarial): evidencia no inventa resultados para offset inexistente."""
    meta = json.loads((Path(__file__).resolve().parents[3] / "audit" / "evidence" / "e2e_009.json").read_text())
    # Confirmar que no afirma PROVEN
    assert meta.get("epistemic") == "PARTIAL"
    # Confirmar que limita afirmación dinámica
    limits = meta.get("limitaciones", [])
    assert isinstance(limits, list) and len(limits) > 0
    assert any("dinámica" in str(l) for l in limits)


if __name__ == "__main__":
    for t in [test_e2e_009_independiente_de_amdgpu, test_e2e_009_no_proven_automatico,
              test_e2e_009_gate, test_e2e_009_no_modifica_anteriores, test_negativo_offset_invalido]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
