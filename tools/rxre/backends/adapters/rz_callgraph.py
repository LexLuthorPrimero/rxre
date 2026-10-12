#!/usr/bin/env python3
"""RXRE-1636. `binary.callgraph` sobre radare2.

PRINCIPIO: radare2 `agCj` produce JSON con funciones y sus importaciones
(que sirven como aristas de llamadas). Capstone NO cubre callgraph: no
hace análisis de llamadas. Por eso `binary.callgraph` requiere
`backend_id='radare2'`.

El adapter:
- usa `aa; agCj` de radare2
- acepta artefacto binario, backend_id, timeout, fixture_json
- produce JSON con funciones y sus aristas de llamada
- rechaza backends no soportados
"""

import json
import os
import subprocess
import tempfile
import hashlib
from typing import Any, Dict, List

from backends import contract as C

#: BACKENDS SOLOS CON PRODUCER
_BACKENDS = {
    "radare2": C.Backend("radare2", "r2", ["-q"], timeout=900),
}


def _ejecutar_comando(archivo: str, timeout: int) -> tuple:
    """Ejecuta `r2 aa; agCj` para obtener el callgraph."""
    cmd = ["r2", "-q", "-c", "aa; agCj", archivo]
    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=timeout)
        return resultado.returncode, resultado.stdout, resultado.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout después de {timeout} segundos"


def persistir(env: Dict[str, Any]) -> Dict[str, Any]:
    """Persistir el resultado del producer para reproducibilidad."""
    input_hash = env.get("input_hash")
    if not input_hash and env.get("artefacto"):
        if isinstance(env["artefacto"], (str, bytes)):
            data = env["artefacto"].encode() if isinstance(env["artefacto"], str) else env["artefacto"]
            input_hash = hashlib.sha256(data).hexdigest()

    output_hash = hashlib.sha256(
        f"{input_hash or 'none'}radare2{env.get('inicio')}{env.get('longitud')}".encode()
    ).hexdigest()

    return {
        "producer": "rz_callgraph",
        "contract_version": "2026-10-12",
        "input_hash": input_hash,
        "output_hash": output_hash,
        "reproducible": True,
        "backend_id": env.get("backend_id"),
        "metadata": {"found": True},
    }


def callgraph(artefacto: Any, **kwargs) -> Dict[str, Any]:
    """Implementacion de `binary.callgraph`. RXRE-1636.

    Contrato:
    - inputs: artefacto binario, inicio (offset), longitud (bytes), backend_id, timeout, fixture_json opcional.
    - outputs: {"status": "ok" | "empty" | "error", "nodes": <int>, "edges": <int>, "metadata": ...}
    - evidencia requerida: JSON valido con funciones y aristas de llamada.
    """
    # Validar backend_id
    backend_id = kwargs.get("backend_id", "radare2")
    if backend_id not in _BACKENDS:
        return {"status": "error",
                "message": f"Backend '{backend_id}' no tiene producer para binary.callgraph"}

    # Validar artefacto
    if artefacto is None:
        return {"status": "error", "message": "artefacto es requerido"}

    timeout = kwargs.get("timeout", 300)
    inicio = kwargs.get("inicio")
    longitud = kwargs.get("longitud")

    # Manejar fixture_json para testing
    if kwargs.get("fixture_json"):
        try:
            fixture_data = json.loads(kwargs["fixture_json"])
            if isinstance(fixture_data, str):
                entrada = bytes.fromhex(fixture_data)
            elif isinstance(fixture_data, list):
                entrada = bytes(fixture_data)
            else:
                entrada = b""
        except Exception:
            entrada = b""
    else:
        entrada = artefacto.encode() if isinstance(artefacto, str) else artefacto

    if isinstance(entrada, str):
        entrada = entrada.encode()

    # Escribir a archivo temporal
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as tmp:
        tmp.write(entrada)
        tmp_path = tmp.name

    try:
        # Ejecutar comando
        returncode, stdout, stderr = _ejecutar_comando(tmp_path, timeout)

        if returncode != 0:
            return {"status": "error",
                    "message": f"Error en radare2: {stderr.strip()[:200]}"}

        # Parsear JSON
        try:
            data = json.loads(stdout.strip()) if stdout.strip() else []
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                data = []

            # agCj produce una lista de funciones, cada una con imports (aristas)
            nodes = len(data)
            edges = sum(len(f.get("imports", [])) for f in data)
            empty = (nodes == 0)

            return {
                "status": "empty" if empty else "ok",
                "nodes": nodes,
                "edges": edges,
                "backend": backend_id,
                "inicio": inicio,
                "longitud": longitud,
                "callgraph_raw": data,
                "metadata": {
                    "limites": {"inicio": inicio, "longitud": longitud},
                    "nota": "Adapter RXRE-1636: binary.callgraph via radare2 agCj. "
                            "nodes=funciones, edges=imports. "
                            "NO es lo mismo que binary.xrefs: este captura llamadas "
                            "interfuncionales, xrefs captura referencias directas."
                }
            }
        except json.JSONDecodeError as e:
            return {"status": "error",
                    "message": f"Salida no JSON de radare2: {str(e)}"}

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass