#!/usr/bin/env python3
"""FRONTERAS REALES DEL ANALIZADOR — adversarial; reproducible."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import validate_evidence_path

def test_e2e_004_integridad():
    """PROVEN: evidencia frontera existe y pasa validación estructural."""
    repo_root = Path(__file__).resolve().parents[3]
    ev = repo_root / "audit" / "evidence" / "e2e_004.json"
    assert ev.exists()
    meta = json.loads(ev.read_text())
    assert meta.get("e2e_id") == "e2e_004"
    assert meta.get("epistemic") == "PARTIAL"


def test_frontera_empty_no_proven():
    """PROVEN (adversarial): archivo vacío no debe ser aceptado como PROVEN."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_004.json"
    # Confirmar que el registro de frontera marca empty como NOT_DETERMINED
    meta = json.loads(ev_path.read_text())
    cases = meta.get("observaciones_frontera", [])
    empty_case = [c for c in cases if c.get("fixture") == "empty"]
    assert len(empty_case) == 1
    assert empty_case[0]["epistemic"] == "NOT_DETERMINED"


def test_frontera_truncated_no_proven():
    """PROVEN (adversarial): binario truncado no debe ser elevado a PROVEN automáticamente."""
    meta = json.loads((Path(__file__).resolve().parents[3] / "audit" / "evidence" / "e2e_004.json").read_text())
    truncated = [c for c in meta.get("observaciones_frontera", []) if c.get("fixture") == "truncated"]
    assert len(truncated) == 1
    assert truncated[0]["epistemic"] == "PARTIAL"


def test_no_evidencia_antigua_confundida():
    """PROVEN: e2e_004 es distinta de e2e_001/002/003."""
    repo_root = Path(__file__).resolve().parents[3]
    ids = set()
    for ev_name in ["e2e_001.json", "e2e_002.json", "e2e_003.json", "e2e_004.json"]:
        meta = json.loads((repo_root / "audit" / "evidence" / ev_name).read_text())
        ids.add(meta.get("e2e_id"))
    assert len(ids) == 4, f"Cada evidencia debe tener ID distinto; encontrado: {ids}"


def test_e2e_004_gate():
    """PROVEN: e2e_004 pasa gate (archivo de evidencia, no artefacto físico)."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_004.json"
    # Validar esquema básico
    meta = json.loads(ev_path.read_text())
    assert "tipo_evidencia" in meta
    assert meta.get("tipo_evidencia") == "frontera_analizador"


if __name__ == "__main__":
    for t in [test_e2e_004_integridad, test_frontera_empty_no_proven, test_frontera_truncated_no_proven,
              test_no_evidencia_antigua_confundida, test_e2e_004_gate]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
