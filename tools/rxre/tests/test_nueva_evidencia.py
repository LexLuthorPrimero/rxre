#!/usr/bin/env python3
"""NUEVA EVIDENCIA — descubrimiento adversarial; reproducible CWD-independent."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import accept_evidence

def test_nueva_evidencia_e2e_003_integridad():
    """PROVEN: e2e_003 es archivo real con hash verificado."""
    repo_root = Path(__file__).resolve().parents[3]
    ev = repo_root / "audit" / "evidence" / "e2e_003.json"
    art = repo_root / "amdgpu.ko"
    assert ev.exists(), "Nueva evidencia debe existir"
    meta = json.loads(ev.read_text())
    assert meta.get("e2e_id") == "e2e_003"
    assert meta.get("objetivo") == "investigar símbolo gfx_enable_kcq y referencias polaris en amdgpu.ko"
    assert meta.get("epistemic") == "PARTIAL"
    # Gate debe aceptar (hash coincide con artefacto real)
    res = accept_evidence(str(ev), str(art))
    assert res["status"] == "accepted", f"Nueva evidencia debe pasar gate: {res}"

def test_nueva_evidencia_no_reutiliza_e2e_001():
    """PROVEN (adversarial): e2e_003 no debe ser confundida con e2e_001/002."""
    repo_root = Path(__file__).resolve().parents[3]
    ev3 = repo_root / "audit" / "evidence" / "e2e_003.json"
    ev1 = repo_root / "audit" / "evidence" / "e2e_001.json"
    meta3 = json.loads(ev3.read_text())
    meta1 = json.loads(ev1.read_text())
    assert meta3.get("e2e_id") != meta1.get("e2e_id")
    assert meta3.get("artefacto_path") == meta1.get("artefacto_path")  # mismo artefacto, pregunta distinta
    assert "simbolo" in str(meta3.get("observaciones", {}))

def test_nueva_evidencia_no_inventado_proven():
    """PROVEN: evidencia no declara PROVEN dinámico; mantiene PARTIAL + limitación."""
    repo_root = Path(__file__).resolve().parents[3]
    meta = json.loads((repo_root / "audit" / "evidence" / "e2e_003.json").read_text())
    assert meta.get("epistemic") == "PARTIAL"
    assert any("F2 PARTIAL" in str(l) for l in meta.get("limitaciones", []))

def test_evidencia_alterada_rechazada():
    """PROVEN (adversarial): copia alterada de e2e_003 debe ser rechazada."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_003.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["artefacto_hash_sha256"] = "0" * 64
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    res = accept_evidence(tmp_path, str(repo_root / "amdgpu.ko"))
    assert res["status"] == "rejected"
    Path(tmp_path).unlink()


if __name__ == "__main__":
    for t in [test_nueva_evidencia_e2e_003_integridad, test_nueva_evidencia_no_reutiliza_e2e_001,
              test_nueva_evidencia_no_inventado_proven, test_evidencia_alterada_rechazada]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
