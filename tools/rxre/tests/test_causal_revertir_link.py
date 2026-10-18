#!/usr/bin/env python3
"""INVESTIGACIÓN CAUSAL — RELACIÓN ESTRUCTURAL A RESTAURACIÓN
Verifica que revertir() preserva contenido (causalidad: original -> restaurado).
No inventa dinámica de hardware; confirma contrato mecanizado."""
import sys, os, tempfile, shutil, hashlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
from rxre.core.fuego import Fuego

def test_causal_revertir_preserves_content():
    """PROVEN: si original existe con contenido determinista, revertir() produce restaurado idéntico."""
    repo_root = Path(__file__).resolve().parents[3]
    snap = repo_root / ".rxre" / "gpu0" / "original"
    restored = repo_root / ".rxre" / "gpu0" / "restaurado"
    assert snap.exists(), "original debe existir (fixture creado)"
    original_content = snap.read_bytes()
    # Ejecutar revertir con instancia correcta (.rxre como raíz)
    repo_root = Path(__file__).resolve().parents[3]
    f = Fuego(str(repo_root / ".rxre"))
    result = f.revertir("gpu0")
    assert result is not None
    assert restored.exists(), "restaurado debe ser creado por revertir()"
    assert restored.read_bytes() == original_content, \
        "CAUSAL FALSO: restaurado no coincide con original (integridad rota)"

def test_causal_distinguish_mock_empty():
    """NOT_DETERMINED (rival): archivo vacío debe producir restaurado vacío; diferencia clara."""
    with tempfile.TemporaryDirectory() as td:
        mock_dir = Path(td) / ".rxre" / "mockdev"
        mock_dir.mkdir(parents=True)
        # Simular archivo vacío (como original.initial_empty)
        (mock_dir / "original").write_bytes(b"")
        f = Fuego(str(Path(td) / ".rxre"))
        res = f.revertir("mockdev")
        restored_mock = Path(td) / ".rxre" / "mockdev" / "restaurado"
        assert restored_mock.exists(), "restaurado debe crearse incluso desde vacío"
        assert restored_mock.read_bytes() == b"", "restaurado vacío coincide con original vacío (diferencia distinguible de fixture)"

def test_causal_evidence_linkage():
    """PROVEN: evidencia E2E coincide con archivo presente."""
    repo_root = Path(__file__).resolve().parents[3]
    ev_path = repo_root / "audit" / "evidence" / "e2e_001.json"
    art = repo_root / "amdgpu.ko"
    assert ev_path.exists(), "evidencia E2E debe existir"
    import json
    meta = json.loads(ev_path.read_text())
    assert art.exists() and art.stat().st_size == meta["artefacto_size_bytes"], \
        "Artefacto real debe coincidir con evidencia E2E"

if __name__ == "__main__":
    import traceback
    for t in [test_causal_revertir_preserves_content, test_causal_distinguish_mock_empty, test_causal_evidence_linkage]:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:
            print("FAIL", t.__name__, "-", type(exc).__name__, str(exc)[:60])
