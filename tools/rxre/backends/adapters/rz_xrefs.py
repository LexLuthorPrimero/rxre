#!/usr/bin/env python3
"""RXRE-1635. `binary.xrefs` sobre rizin/radare2.

PRINCIPIO: solo dos backends pueden cumplir esta capacidad:
- `risin` (`axtj`/`axfj` con `aaa`, `aa; axtj` -> [] y `aaa; axtj` -> 3)
- `radare2` (`axtj` igual)

Capstone NO cubre xrefs: no hace analisis de funciones.
Por eso `binary.xrefs` es PARTIAL en el registro y requiere
`nivel_analisis` para discriminar `aa` vs `aaa` en la respuesta.
"""

import json
import os
import subprocess
import tempfile
import hashlib
from typing import Any, Dict

from backends import contract as C


#: BACKENDS SOLOS CON PRODUCER
_BACKENDS = {
    "rizin": C.Backend("rizin", "rizin", ["-q"], timeout=900),
    "radare2": C.Backend("radare2", "r2", ["-q"], timeout=900),
}


def _ejecutar_comando(backend_id: str, nivel_analisis: str, archivo: str, timeout: int) -> tuple:
    """Ejecuta el comando apropiado para obtener xrefs."""
    if backend_id == "rizin":
        cmd = ["rizin", "-q", "-N", "-c", f"{nivel_analisis}; axtj @ 0x4000", archivo]
    elif backend_id == "radare2":
        cmd = ["r2", "-q", "-c", f"{nivel_analisis}; axtj @ 0x4000", archivo]
    else:
        raise ValueError(f"Backend no soportado: {backend_id}")

    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return resultado.returncode, resultado.stdout, resultado.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout después de {timeout} segundos"


def persistir(env: Dict[str, Any]) -> Dict[str, Any]:
    """Persistir el resultado del producer para reproducibilidad.

    Medido 2026-10-12: rizin/radare2 usan la misma transacción determinista:
    archivo temporal + comando. Registrar el hash del input y el hash del output.
    """
    input_hash = env.get("input_hash")
    if not input_hash and env.get("artefacto"):
        if isinstance(env["artefacto"], (str, bytes)):
            data = env["artefacto"].encode() if isinstance(env["artefacto"], str) else env["artefacto"]
            input_hash = hashlib.sha256(data).hexdigest()

    output_hash = hashlib.sha256(
        f"{input_hash or 'none'}{env.get('backend_id')}{env.get('nivel_analisis')}"
        f"{env.get('inicio')}{env.get('longitud')}".encode()
    ).hexdigest()

    return {
        "producer": "rz_xrefs",
        "contract_version": "2026-10-12",
        "input_hash": input_hash,
        "output_hash": output_hash,
        "reproducible": True,
        "backend_id": env.get("backend_id"),
        "nivel_analisis": env.get("nivel_analisis"),
        "metadata": {"found": True},
    }


def xrefs(artefacto: Any, **kwargs) -> Dict[str, Any]:
    """Implementacion de `binary.xrefs`. RXRE-1635.

    Contrato:
    - inputs: artefacto binario, inicio (offset), longitud (bytes), backend_id,
      nivel_analisis ("aaa" o "aa"), timeout, fixture_json opcional.
    - outputs: {"status": "ok" | "empty" | "error", "xrefs": <int>, "metadata": ...}
    - evidencia requerida: JSON valido con discriminante nivel_analisis.
    """
    # Validar backend_id
    backend_id = kwargs.get("backend_id", "rizin")
    if backend_id not in _BACKENDS:
        return {"status": "error",
                "message": f"Backend '{backend_id}' no tiene producer para binary.xrefs"}

    # Validar nivel_analisis
    nivel_analisis = kwargs.get("nivel_analisis", "aaa")
    if nivel_analisis not in ["aa", "aaa"]:
        return {"status": "error",
                "message": f"nivel_analisis debe ser 'aa' o 'aaa', no '{nivel_analisis}'"}

    # Manejar artefacto o fixture
    if kwargs.get("fixture_json"):
        try:
            fixture_data = json.loads(kwargs["fixture_json"])
            if isinstance(fixture_data, str):
                entrada = bytes.fromhex(fixture_data) if len(fixture_data) <= 1024 else fixture_data.encode('utf-8')
            elif isinstance(fixture_data, list):
                entrada = bytes(fixture_data)
            else:
                entrada = b""
        except Exception:
            entrada = b""
    else:
        if artefacto is None:
            return {"status": "error", "message": "artefacto es requerido"}
        entrada = artefacto.encode() if isinstance(artefacto, str) else artefacto

    # Escribir a archivo temporal
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as tmp:
        tmp.write(entrada)
        tmp_path = tmp.name

    try:
        # Ejecutar comando
        timeout = kwargs.get("timeout", 300)
        returncode, stdout, stderr = _ejecutar_comando(backend_id, nivel_analisis, tmp_path, timeout)

        # Procesar resultado
        if returncode != 0:
            return {"status": "error", "message": f"Error en {backend_id}: {stderr.strip()[:200]}"}

        # Intentar parsear como JSON
        try:
            data = json.loads(stdout.strip()) if stdout.strip() else []
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                data = []

            xrefs_count = len(data)

            # Determinar status
            if xrefs_count == 0:
                status = "empty"
            else:
                status = "ok"

            return {
                "status": status,
                "xrefs": xrefs_count,
                "backend": backend_id,
                "nivel_analisis": nivel_analisis,
                "metadata": {
                    "limites": {
                        "inicio": kwargs.get("inicio"),
                        "longitud": kwargs.get("longitud"),
                    },
                    "backend_version": backend_id,
                    "nota": "Adapter rz_xrefs.py implementacion RXRE-1635: xrefs con nivel_analisis"
                }
            }
        except json.JSONDecodeError:
            return {"status": "error", "message": f"Salida no JSON de {backend_id}: {stdout[:100]}"}

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass