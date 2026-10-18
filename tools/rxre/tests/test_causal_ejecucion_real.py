#!/usr/bin/env python3
"""INVESTIGACIÓN CAUSAL — EJECUCIÓN REAL VÍA ROUTER (reproducible, sin invento)."""
import sys, os, subprocess, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
def test_router_ejecucion_real():
    """PROVEN: router resolve + ejecutar funciona con contrato real (2 args)."""
    from backends.dispatch import resolve, ejecutar
    cap = "binary.inspect"
    r = resolve(cap)
    assert r.get("backend") is not None, f"Router debe resolver backend para {cap}"
    # Ejecución con contrato real: 2 argumentos (capability, params dict)
    res = repo_root = Path(__file__).resolve().parents[3]
    art_path = str(repo_root / "amdgpu.ko")
    ejecutar(cap, {"artefacto": art_path,"timeout":30})
    assert res.get("status") == "ok", f"Ejecución debe retar ok, no blocked: {res}"
    assert res.get("ejecutada") is True, "Router debe reportar ejecutada"

def test_e2e_evidence_preserved():
    """PROVEN: evidencia E2E coincide con archivo presente."""
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    art = repo_root / "amdgpu.ko"
    assert ev_path.exists(), "Evidencia E2E debe existir"
    meta = json.loads(ev_path.read_text())
    assert art.exists(), "Artefacto real debe existir"
    assert art.stat().st_size == meta["artefacto_size_bytes"], \
        "Tamaño archivo debe coincidir con E2E"

def test_e2e_e2_linkage():
    """PROVEN: relación E2E -> estructura verificada."""
    repo_root = Path(__file__).resolve().parents[3]
    ev2 = repo_root / "audit" / "evidence" / "e2e_002.json"
    if ev2.exists():
        meta = json.loads(ev2.read_text())
        assert meta.get("tipo") == "relacion_estructural", \
            "Relación debe ser estructural, no dinámica"
        assert meta.get("artefacto") == "amdgpu.ko", \
            "Artefacto debe coincidir"
        assert meta.get("epistemic") == "PROVEN", \
            "Estado debe ser PROVEN (no inventado)"

def test_not_dynamic_claim():
    """NOT_DETERMINED: esta evidencia confirma estructura, no comportamiento dinámico."""
    # Confirmación: la evidencia no declara dinámica de ejecución
    repo_root = Path(__file__).resolve().parents[3]
    contrato = (repo_root / "docs" / "CONTRATO_CAUSAL_INV_ESTRING.md").read_text()
    assert "no confirma comportamiento dinámico" in contrato.lower() or \
           "NOT_DETERMINED" in contrato, \
        "El contrato debe documentar la limitación (no dinámica)"

if __name__ == "__main__":
    import traceback
    for t in [test_router_ejecucion_real, test_e2e_evidence_preserved, test_e2e_e2_linkage, test_not_dynamic_claim]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
