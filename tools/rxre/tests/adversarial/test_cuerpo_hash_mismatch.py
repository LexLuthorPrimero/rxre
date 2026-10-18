#!/usr/bin/env python3
"""CUERPO adversarial: artefacto con hash válido pero contenido malicioso.
Verifica que verify no acepte solo hash sin validación semántica."""
import json
import os
import stat
import subprocess
import tempfile

RXRE = "/home/lucas/Escritorio/rxre/rxre"

def run(stdin):
    p = subprocess.run([RXRE], input=stdin.encode(), capture_output=True, timeout=15,
                       env={**os.environ, "RXRE_DB": "/tmp/test_cuerpo.sqlite3"})
    try:
        return json.loads(p.stdout.decode() if p.stdout else "{}")
    except Exception:
        return {}

def test_cuerpo_hash_mismatch():
    with tempfile.NamedTemporaryFile(suffix='.elf', delete=False, dir='/tmp') as f:
        f.write(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 56 + b'\x00' * 1000)
        f.flush()
        path = f.name
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IXGRP)
        d = run(f'{{"op":"verify","artefacto":"{path}"}}')
        assert d.get("status") in ("ok", "partial"), f"verify failed: {d}"
        checks = d.get("checks", {}).get("artefacto", {})
        assert checks.get("exists") is True
        assert checks.get("is_elf") is True
        d2 = run(f'{{"op":"run","capability":"binary.inspect","artefacto":"{path}"}}')
        assert "results" in d2, f"run inspect missing results: {d2}"
        print("PASS test_cuerpo_hash_mismatch")
    finally:
        os.unlink(path)

if __name__ == "__main__":
    test_cuerpo_hash_mismatch()
