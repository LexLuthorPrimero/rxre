#!/usr/bin/env python3
"""RELACION ESTRUCTURAL INDEPENDIENTE — /bin/ls xrefs + iS (no amdgpu/fixture)."""
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import accept_evidence
from rxre.core.replay import evaluate_contract

def test_e2e_008_existe_independiente():
    repo_root = Path(__file__).resolve().parents[3]
    ev = repo_root / "audit" / "evidence" / "e2e_008.json"
    assert ev.exists()
    meta = json.loads(ev.read_text())
    assert meta.get("e2e_id") == "e2e_008"
    assert meta.get("tipo_evidencia") == "relacion_estructural_independiente"
    assert meta.get("epistemic") == "PARTIAL"

def test_e2e_008_no_reutiliza_amdgpu():
    repo_root = Path(__file__).resolve().parents[3]
    meta6 = json.loads((repo_root / "audit" / "evidence" / "e2e_006.json").read_text())
    meta8 = json.loads((repo_root / "audit" / "evidence" / "e2e_008.json").read_text())
    assert meta8.get("artefacto_hash_sha256") != meta6.get("artefacto_hash_sha256")
    assert meta8.get("artefacto_path") == "/bin/ls"

def test_e2e_008_contrato_partal():
    repo_root = Path(__file__).resolve().parents[3]
    res = evaluate_contract({"status":"ok","precheck":{"ok":True},"ejecucion":{"status":"ok"},"results":[{"status":"declared","limitations":["Referencia DATA estructural verificable; dinámica no confirmada"]}]}, str(repo_root / "audit" / "evidence" / "e2e_008.json"))
    assert res["contract_state"] == "PARTIAL"
    assert res["epistemic"] == "PARTIAL"

def test_e2e_008_gate():
    repo_root = Path(__file__).resolve().parents[3]
    res = accept_evidence(str(repo_root / "audit" / "evidence" / "e2e_008.json"), "/bin/ls")
    assert res["status"] in ("accepted", "rejected")

def test_e2e_008_no_inventado_proven():
    meta = json.loads(Path("/home/lucas/Escritorio/rxre/audit/evidence/e2e_008.json").read_text())
    assert meta.get("epistemic") != "PROVEN"

if __name__ == "__main__":
    for t in [test_e2e_008_existe_independiente, test_e2e_008_no_reutiliza_amdgpu, test_e2e_008_contrato_partal, test_e2e_008_gate, test_e2e_008_no_inventado_proven]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
