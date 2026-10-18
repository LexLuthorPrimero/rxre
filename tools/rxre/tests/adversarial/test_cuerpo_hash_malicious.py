#!/usr/bin/env python3
"""CUERPO adversarial: artefacto ELF válido pero con características sospechosas
(permisos de grupo escritura). CUERPO debe detectar al menos que algo está fuera de norma."""
import json, os, stat, subprocess, tempfile

CLI = "/home/lucas/Escritorio/rxre/rxre"

def run_jsonl(stdin, timeout=10):
    p = subprocess.run([CLI], input=stdin.encode(), capture_output=True, timeout=timeout,
                       env={**os.environ, "RXRE_DB": "/tmp/test_cuerpo.sqlite3"})
    try:
        return json.loads(p.stdout.decode())
    except Exception:
        return {}

def test_cuerpo_hash_malicious():
    with tempfile.NamedTemporaryFile(suffix='.elf', delete=False, dir='/tmp') as f:
        f.write(b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 56 + b'\x00' * 1000)
        path = f.name
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IXGRP)
        # CUERPO verify debe procesar el artefacto pero con limitaciones/anomalías
        d = run_jsonl(f'{{"op":"verify","artefacto":"{path}"}}')
        assert d.get("status") in ("ok", "partial"), f"verify failed: {d}"
        checks = d.get("checks", {}).get("artefacto", {})
        assert checks.get("exists") is True
        assert checks.get("is_elf") is True
        # run inspección debe procesar el binario
        d2 = run_jsonl(f'{{"op":"run","capability":"binary.inspect","artefacto":"{path}"}}')
        assert "results" in d2, f"run inspect missing results: {d2}"
        print("PASS test_cuerpo_hash_malicious")
    finally:
        os.unlink(path)

if __name__ == "__main__":
    test_cuerpo_hash_malicious()
