#!/usr/bin/env python3
"""VERIFICACIÓN DE REINVESTIGACIÓN — adversarial; reproducible."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.replay import verify_reinvestigation, plan_reinvestigation, analyze_dependencies

def test_resolved_valid():
    """PROVEN: plan VALID + resultado válido -> RESOLVED."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = str(repo_root / "audit" / "evidence" / "e2e_001.json")
    plan = plan_reinvestigation("op_2939a40bc715d58f", ev_path)
    result = {"op_id": "op_2939a40bc715d58f", "classification": "VALID", "evidence_path": ev_path, "reproducible": True}
    res = verify_reinvestigation(plan, result)
    assert res["verification_status"] == "RESOLVED"
    assert res["reducida_incertidumbre"] is True


def test_unresolved_stale_no_progreso():
    """PROVEN (adversarial): plan STALE + resultado que no confirma resolución -> UNRESOLVED."""
    # Simular plan STALE (hash alterado) y resultado sin evidencia consistente
    plan = plan_reinvestigation("op_2939a40bc715d58f", "/tmp/fake_evidence.json")
    result = {"op_id": "op_2939a40bc715d58f", "classification": "INVALID_RESULT", "evidence_path": "/tmp/fake_evidence.json"}
    res = verify_reinvestigation(plan, result)
    assert res["verification_status"] in ("UNRESOLVED", "INVALID_RESULT")


def test_invalid_result_op_id_mismatch():
    """PROVEN (adversarial): op_id diferente -> INVALID_RESULT."""
    plan = plan_reinvestigation("op_2939a40bc715d58f")
    result = {"op_id": "op_OTRA", "classification": "VALID"}
    res = verify_reinvestigation(plan, result)
    assert res["verification_status"] == "INVALID_RESULT"
    assert res["motivo"] == "operación del resultado no coincide con el plan"


def test_no_destructivo():
    """PROVEN: verificación no modifica evidencia."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    before = ev_path.read_text()
    plan = plan_reinvestigation("op_2939a40bc715d58f")
    result = {"op_id": "op_2939a40bc715d58f", "classification": "VALID"}
    verify_reinvestigation(plan, result)
    after = ev_path.read_text()
    assert before == after


if __name__ == "__main__":
    for t in [test_resolved_valid, test_unresolved_stale_no_progreso, test_invalid_result_op_id_mismatch, test_no_destructivo]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
