#!/usr/bin/env python3
"""GATE DE EVIDENCIA — flujo completo con adversarial; reproducible CWD-independent."""
import sys, os, tempfile, json, hashlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.evidence_integrity import accept_evidence

def test_gate_acepta_evidencia_canica():
    """PROVEN: evidencia válida pasa el gate."""
    repo_root = Path(__file__).resolve().parents[3]
    ev = repo_root / "audit" / "evidence" / "e2e_001.json"
    art = repo_root / "amdgpu.ko"
    res = accept_evidence(str(ev), str(art))
    assert res["status"] == "accepted", f"Evidencia válida debe ser aceptada: {res}"
    assert res["checks"]["hash_matches"] is True


def test_gate_rechaza_hash_alterado():
    """PROVEN (adversarial): evidencia con hash alterado debe ser rechazada antes de aceptarse."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["artefacto_hash_sha256"] = "0" * 64
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    art = repo_root / "amdgpu.ko"
    res = accept_evidence(tmp_path, str(art))
    assert res["status"] == "rejected", f"Hash alterado debe ser rechazado: {res}"
    assert any("hash_mismatch" in str(e) for e in res["errors"]), \
        "Debe reportar hash_mismatch"
    Path(tmp_path).unlink()


def test_gate_rechaza_esquema_invalido():
    """PROVEN (adversarial): esquema sin clave obligatoria debe ser rechazado."""
    import tempfile
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta.pop("epistemic", None)
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    art = repo_root / "amdgpu.ko"
    res = accept_evidence(tmp_path, str(art))
    assert res["status"] == "rejected", f"Esquema incompleto debe ser rechazado: {res}"
    assert any("missing_keys" in str(e) for e in res["errors"]), \
        "Debe reportar missing_keys"
    Path(tmp_path).unlink()


def test_gate_rechaza_procedencia_inconsistente():
    """PROVEN (adversarial): evidencia que referencia archivo que no existe debe ser rechazada."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["artefacto_path"] = "/no/existe/archivo.ko"
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    res = accept_evidence(tmp_path, None)  # Deriva del meta falso -> debe fallar
    assert res["status"] == "rejected", f"Procedencia inconsistente debe ser rechazada: {res}"
    assert any("artifact_missing" in str(e) for e in res["errors"]), \
        "Debe reportar artifact_missing"
    Path(tmp_path).unlink()


def test_evidencia_previa_no_modificada():
    """NOT_DETERMINED / PROVEN: evidencia canónica debe mantenerse intacta tras rechazos."""
    import hashlib
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    art_path = str(repo_root / "amdgpu.ko")
    # Leer evidencia antes
    before = ev_path.read_text()
    # Intentar rechazar con archivo temporal (no modifica canónica)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        meta = json.loads(ev_path.read_text())
        meta["artefacto_hash_sha256"] = "0" * 64
        tmp.write(json.dumps(meta))
        tmp_path = tmp.name
    res = accept_evidence(tmp_path, art_path)
    assert res["status"] == "rejected"
    Path(tmp_path).unlink()
    # Confirmar que canónica no fue tocada
    after = ev_path.read_text()
    assert before == after, "Evidencia canónica no debe ser modificada por rechazos"


if __name__ == "__main__":
    import traceback
    for t in [test_gate_acepta_evidencia_canica, test_gate_rechaza_hash_alterado,
              test_gate_rechaza_esquema_invalido, test_gate_rechaza_procedencia_inconsistente,
              test_evidencia_previa_no_modificada]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
