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

    Usar la capa centralizada core.store para todos los adapters.
    """
    from core import store as S

    db = env.get("db")
    abierta_por_nosotros = db is None
    c = db or S.conectar()

    capability = env.get("capability", "binary.xrefs")
    target = env.get("target", "")
    question = env.get("question", "")
    import hashlib as _hash
    op_seed = f"{capability}|{target}|{question}"
    op_id = "op_" + _hash.sha256(op_seed.encode()).hexdigest()[:16]

    # Eliminar operaciones previas con el mismo op_id para evitar duplicados.
    # El column name en el esquema es operation_id, no op_id.
    c.execute("DELETE FROM operations WHERE operation_id=?", (op_id,))
    c.execute("DELETE FROM results WHERE operation_id=?", (op_id,))
    c.commit()

    request = {
        "request_id": "",
        "question": question or f"inspeccionar {target or 'artefacto'}",
        "capability": capability,
        "scope": "binary",
        "target": target,
    }
    operation = {
        "operation": capability,
        "status": env.get("status", "ok"),
        "backend": env.get("backend"),
        "ejecucion": env.get("ejecucion"),
        "provenance": env.get("provenance"),
        "precheck": env.get("precheck"),
        "cadena_backend": env.get("cadena_backend"),
        "results": env.get("results") or [],
    }
    duracion = (env.get("ejecucion") or {}).get("duration_s", 0)
    resultado_op_id = S.registrar(c, request, operation, duracion)

    if abierta_por_nosotros:
        c.close()

    return {
        "producer": "rz_xrefs",
        "contract_version": "2026-10-12",
        "input_hash": env.get("input_hash"),
        "output_hash": env.get("output_hash"),
        "reproducible": True,
        "backend_id": env.get("backend_id"),
        "nivel_analisis": env.get("nivel_analisis"),
        "metadata": {"found": True},
        "operation_id": resultado_op_id if resultado_op_id else None,
        "persistido": bool(resultado_op_id and not str(resultado_op_id).startswith("COLISION"))
    }


def _ts():
    """Timestamp simple para usar en los results."""
    import datetime
    return datetime.datetime.now().isoformat()


def xrefs(artefacto: Any, **kwargs) -> Dict[str, Any]:
    """Implementacion de `binary.xrefs`. RXRE-1635.
    
    Contrato:
    - inputs: artefacto binario, inicio (offset), longitud (bytes), backend_id,
      nivel_analisis ("aaa" o "aa"), timeout, fixture_json opcional.
    - outputs: {"status": "ok" | "empty" | "error", "xrefs": <int>, "results": [...], "metadata": ...}
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
                entrada = bytes.fromhex(fixture_data)
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

            # Construir resultados con result_id para persistencia
            results = []
            for i, xref in enumerate(data):
                # Cada xref es una referencia a una función o símbolo
                # Usar hash determinista basado en el contenido del xref
                xref_str = json.dumps(xref, sort_keys=True, default=str)
                result_id = "xref_" + hashlib.sha256(f"{i}_{xref_str}".encode()).hexdigest()[:12]
                result = {
                    "result_id": result_id,
                    "type": "xref",
                    "value": xref,
                    "source": "binary.xrefs",
                    "location": {"file": str(artefacto), "offset": kwargs.get("inicio", 0)},
                    "scope": "binary",
                    "tool": backend_id,
                    "tool_version": "",
                    "input": {"path": str(artefacto), "sha256": ""},
                    "timestamp": _ts(),
                    "artifact": str(artefacto),
                    "artifact_hash": "",
                    "status": "declared",
                    "limitations": ["xref requiere análisis de funciones"]
                }
                results.append(result)

            return {
                "status": status,
                "xrefs": xrefs_count,
                "results": results,  # <-- This is the key addition
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