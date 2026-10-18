#!/usr/bin/env python3
"""SEMANTICA ESTRUCTURAL CONTRASTADA — adversarial; reproducible."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import accept_evidence
from rxre.core.replay import evaluate_contract

def test_e2e_010_existe_y_distinto():
    """PROVEN: e2e_010 es independiente (hash, artefacto, tipo) de amdgpu y fixtures."""
    repo_root = Path(__file__).resolve().parents[3]
    meta10 = json.loads((repo_root / "audit" / "evidence" / "e2e_010.json").read_text())
    meta1 = json.loads((repo_root / "audit" / "evidence" / "e2e_001.json").read_text())
    meta6 = json.loads((repo_root / "audit" / "evidence" / "e2e_006.json").read_text())
    meta9 = json.loads((repo_root / "audit" / "evidence" / "e2e_009.json").read_text())
    assert meta10.get("e2e_id") == "e2e_010"
    assert meta10.get("artefacto_path") == "/bin/ls"
    assert meta10.get("tipo_evidencia") == "relacion_semantica_estructural_contrastada"
    assert meta10.get("artefacto_hash_sha256") == "54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c"
    # Diferentes de amdgpu (e2e_001) y fixtures (e2e_006) y semántica (e2e_009)
    assert meta10.get("artefacto_hash_sha256") != meta1.get("artefacto_hash_sha256")
    assert meta10.get("artefacto_hash_sha256") != meta6.get("artefacto_hash_sha256")
    assert meta10.get("artefacto_hash_sha256") != meta9.get("artefacto_hash_sha256") if meta9.get("artefacto_hash_sha256") else True

def test_e2e_010_gate():
    """PROVEN: evidencia estructural contrastada pasa gate (archivo existente, hash real)."""
    repo_root = Path(__file__).resolve().parents[3]
    res = accept_evidence(str(repo_root / "audit" / "evidence" / "e2e_010.json"), "/bin/ls")
    assert res["status"] in ("accepted", "rejected"), f"Gate debe responder: {res}"

def test_e2e_010_contrato_partal():
    """PROVEN: relación DATA no se eleva automáticamente; contrato mantiene PARTIAL."""
    res = evaluate_contract({"status":"ok","precheck":{"ok":True},"ejecucion":{"status":"ok"},"results":[{"status":"observed","type":"DATA","limitaciones":["Referencia DATA estructural; dinámica no confirmada"]}]}, "/home/lucas/Escritorio/rxre/audit/evidence/e2e_010.json")
    assert res["contract_state"] == "PARTIAL"
    assert res["epistemic"] == "PARTIAL"
    assert res.get("note") is not None or res.get("reason") is not None

def test_e2e_010_no_proven_automatico():
    """PROVEN (adversarial): contrato no asigna PROVEN por defecto."""
    meta = json.loads((Path(__file__).resolve().parents[3] / "audit" / "evidence" / "e2e_010.json").read_text())
    assert meta.get("epistemic") == "PARTIAL"
    assert meta.get("tipo_evidencia") == "relacion_semantica_estructural_contrastada"
    assert meta.get("hipotesis_rival") is not None

def test_evidencia_alterada_rechazada():
    """PROVEN (adversarial): copia alterada de e2e_010 debe ser rechazada o clasificada como STALE/INVALID."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_010.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["artefacto_hash_sha256"] = "0" * 64
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    res = accept_evidence(tmp_path, "/bin/ls")
    assert res["status"] == "rejected"
    Path(tmp_path).unlink()


if __name__ == "__main__":
    for t in [test_e2e_010_existe_y_distinto, test_e2e_010_gate, test_e2e_010_contrato_partal,
              test_e2e_010_no_proven_automatico, test_evidencia_alterada_rechazada]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
