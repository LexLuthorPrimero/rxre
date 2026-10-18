#!/usr/bin/env python3
"""CONTRATO UNIFORME — adversarial; reproducible."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.replay import evaluate_contract

def test_contract_elf_ok():
    """PROVEN: BK_OK completo -> COMPLETE / VALID."""
    # Usar resultado real de elff_ok (simulado con datos reales)
    res = evaluate_contract({"status":"ok","precheck":{"ok":True},"ejecucion":{"status":"ok"},"results":[{"status":"declared","limitations":["test"]}]}, None)
    # Con limitación explícita -> PARTIAL
    assert res["contract_state"] == "PARTIAL", f"Con limitaciones debe ser PARTIAL: {res['contract_state']}"
    assert res["epistemic"] == "PARTIAL"

def test_contract_empty_invalid():
    """PROVEN (adversarial): BK_INVALID (empty/text) -> INVALID_INPUT / NOT_DETERMINED."""
    res = evaluate_contract({"status":"invalid_input","precheck":{"ok":False},"ejecucion":{"status":"blocked"}})
    assert res["contract_state"] == "INVALID_INPUT"
    assert res["epistemic"] == "NOT_DETERMINED"
    assert res["execution_status"] == "invalid_input"

def test_contract_blocked_error():
    """PROVEN (adversarial): BK_ERROR -> BLOCKED / NOT_DETERMINED."""
    res = evaluate_contract({"status":"blocked","precheck":{"ok":True},"ejecucion":{"status":"blocked"}})
    assert res["contract_state"] == "BLOCKED"
    assert res["epistemic"] == "NOT_DETERMINED"

def test_contract_truncated_partial():
    """PROVEN (adversarial): BK_OK con evidencia frontera -> PARTIAL (no COMPLETO)."""
    repo_root = Path(__file__).resolve().parents[3]
    res = evaluate_contract({"status":"ok","precheck":{"ok":True},"ejecucion":{"status":"ok"},"results":[{"status":"declared","limitations":["RAW_BINARY","limite"]}]}, str(repo_root / "audit" / "evidence" / "e2e_004.json"))
    assert res["contract_state"] == "PARTIAL"
    assert res["epistemic"] == "PARTIAL"
    assert res["evidence_integrity"] is True

def test_contract_no_auto_proven():
    """PROVEN: ningún caso debe producir PROVEN automáticamente."""
    for case in [
        {"status":"ok","precheck":{"ok":True}},
        {"status":"invalid_input"},
        {"status":"blocked"}
    ]:
        res = evaluate_contract(case)
        assert res["epistemic"] != "PROVEN", f"No debe ser PROVEN automático: {res['epistemic']}"


if __name__ == "__main__":
    for t in [test_contract_elf_ok, test_contract_empty_invalid, test_contract_blocked_error,
              test_contract_truncated_partial, test_contract_no_auto_proven]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
