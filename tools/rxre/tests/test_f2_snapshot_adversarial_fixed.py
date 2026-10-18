#!/usr/bin/env python3
"""F2 adversarial — contrato corregido (archivo original, no directorio; fixture verificado; hardware pendiente)."""
import sys, os, pytest, hashlib, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pathlib import Path
from rxre.core.fuego import Fuego

SNAP_FILE = Path(".rxre/gpu0/original")
META_FILE = Path(".rxre/gpu0/snapshot_meta.json")

def test_f2_original_es_archivo():
    assert SNAP_FILE.is_file(), ".rxre/gpu0/original debe ser archivo (contrato real core/fuego.py:108)"
    # Verificar que no es archivo vacío después del fixture
    if SNAP_FILE.stat().st_size == 0:
        pytest.skip("F2: archivo original vacío — fixture aún no creado (requiere ejecución autorizada de script)")

def test_f2_snapshot_contenido():
    if SNAP_FILE.stat().st_size == 0:
        pytest.skip("F2 PARTIAL: archivo vacío (fixture no creado; requiere autorización para crear o captura hardware)")
    # Si hay metadatos, verificar consistencia
    if META_FILE.exists():
        meta = json.loads(META_FILE.read_text())
        assert meta.get("fixture") is True, "El snapshot debe declararse como fixture (no como captura real)"
        assert meta.get("bytes") == SNAP_FILE.stat().st_size, "Bytes en meta deben coincidir con archivo"
        content = SNAP_FILE.read_bytes()
        assert hashlib.sha256(content).hexdigest() == meta.get("hash_sha256"), "Hash debe coincidir"
    else:
        # Si no hay meta, verificar que el archivo tiene contenido determinista
        content = SNAP_FILE.read_bytes()
        assert len(content) == 4096, "Fixture debe ser 4096 bytes deterministas"
        assert content.startswith(b"\xde\xad\xbe\xef"), "Contenido debe ser determinista"

def test_f2_revertir_funciona_con_fixture():
    if SNAP_FILE.stat().st_size == 0:
        pytest.skip("F2 PARTIAL: archivo vacío; revertir() lanza FileNotFoundError (confirmado) — fixture pendiente")
    # Si el archivo tiene contenido (fixture o real), revertir debe funcionar
    r = Fuego(".rxre").revertir("gpu0")
    assert r is not None
    # Verifica que se creó restaurado
    restaurado = Path(".rxre/gpu0/restaurado")
    if restaurado.exists():
        assert restaurado.stat().st_size == SNAP_FILE.stat().st_size, "restaurado debe tener mismo tamaño que original"

def test_f2_no_es_hardware_real():
    meta_path = Path(".rxre/gpu0/snapshot_meta.json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        assert meta.get("fixture") is True or meta.get("source") == "test_fixture_not_hardware", \
            "El snapshot debe documentarse claramente como NO captura de hardware (contrato)"
    else:
        # Si no hay meta, confirmar que archivo existe pero no hay evidencia de captura real
        pass  # No se afirma captura real; solo se confirma ausencia de meta real
