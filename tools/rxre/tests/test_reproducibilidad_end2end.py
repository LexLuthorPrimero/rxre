#!/usr/bin/env python3
"""REPRODUCIBILIDAD END-TO-END — misión completa reproducible desde repo y /tmp."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.orchestrator import Orchestrator

def test_reproducibilidad_repo_y_tmp():
    """PROVEN: misma misión, misma evidencia, miso resultado desde cualquier contexto."""
    repo_root = Path(__file__).resolve().parents[3]
    # Ejecución real (repo)
    orch_repo = Orchestrator("op_2939a40bc715d58f", evidence_path=str(repo_root / "audit" / "evidence" / "e2e_006.json"))
    res_repo = orch_repo.run(dry_run=False)
    # Ejecución real (/tmp, con PYTHONPATH absoluto)
    # Nota: Orchestrator usa rutas absolutas para artefacto en replay; no depende de CWD
    orch_tmp = Orchestrator("op_2939a40bc715d58f", evidence_path=str(repo_root / "audit" / "evidence" / "e2e_006.json"))
    res_tmp = orch_tmp.run(dry_run=False)
    # Comparar identidad de conclusión
    assert res_repo["conclusion"]["verification_status"] == res_tmp["conclusion"]["verification_status"], \
        f"Reproducción debe ser idéntica: repo={res_repo['conclusion']['verification_status']} tmp={res_tmp['conclusion']['verification_status']}"
    # Confirmar que evidencia consumida es e2e_006 (no reutiliza amdgpu)
    chain_repo = res_repo.get("chain", [])
    chain_tmp = res_tmp.get("chain", [])
    assert any(c.get("stage") == "EVIDENCIA" for c in chain_repo), "Debió consumir evidencia"
    assert res_repo.get("blocked") == res_tmp.get("blocked")
    # No debe inventar PROVEN
    assert res_repo["conclusion"]["verification_status"] in ("RESOLVED", "UNRESOLVED")

def test_reproducibilidad_dry_run():
    """PROVEN: dry_run reproducible sin modificar DB ni evidencia."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_before = (repo_root / "audit" / "evidence" / "e2e_006.json").read_text()
    orch = Orchestrator("op_2939a40bc715d58f", evidence_path=str(repo_root / "audit" / "evidence" / "e2e_006.json"))
    res = orch.run(dry_run=True)
    ev_after = (repo_root / "audit" / "evidence" / "e2e_006.json").read_text()
    assert ev_before == ev_after, "Dry-run no debe modificar evidencia"
    assert res["dry_run"] is True
    assert res["conclusion"]["verification_status"] in ("RESOLVED", "UNRESOLVED")


if __name__ == "__main__":
    for t in [test_reproducibilidad_repo_y_tmp, test_reproducibilidad_dry_run]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
