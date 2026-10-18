#!/usr/bin/env python3
"""F2 — Productor SEGURO de snapshot (fixture de prueba, NO captura hardware).
Contratos verificados: core/fuego.py trata original como archivo (line 108).
No usa /dev/mem ni interactúa con GPU. Escrito para .rxre/ (proyecto, no hardware).
Limitación: este fixture NO es evidencia de registros MMIO reales.
"""
from pathlib import Path
import hashlib, json, datetime

DEVICE_ID = "gpu0"
SNAP_DIR = Path(".rxre") / DEVICE_ID
SNAP_FILE = SNAP_DIR / "original"
META_FILE = SNAP_DIR / "snapshot_meta.json"

def create_safe_fixture():
    """Crea snapshot de prueba. Requiere que SNAP_DIR exista."""
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    # Contenido de prueba: 4096 bytes fijos (fixture determinista, no hardware)
    content = b"\xde\xad\xbe\xef" * 1024  # 4096 bytes deterministas
    SNAP_FILE.write_bytes(content)
    meta = {
        "device_id": DEVICE_ID,
        "fixture": True,
        "source": "test_fixture_not_hardware",
        "bytes": len(content),
        "hash_sha256": hashlib.sha256(content).hexdigest(),
        "created": datetime.datetime.utcnow().isoformat(),
        "note": "Fixture de prueba — NO captura MMIO real. Requiere autorización root + /dev/mem para snapshot físico."
    }
    META_FILE.write_text(json.dumps(meta, indent=2))
    return meta

if __name__ == "__main__":
    meta = create_safe_fixture()
    print("Fixture creado:", meta["hash_sha256"][:16] + "...", meta["bytes"], "bytes")
    print("Nota: NO es captura de GPU. Es contrato de archivo verificado.")
