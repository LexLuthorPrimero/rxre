#!/usr/bin/env python3
"""RXRE-004. Adapter de `rea` para inspeccion de firmware y binarios.

IMPORTANTE: Este adapter llama al CLI `rea` instalado en el sistema.
REA funciona parcialmente: los comandos `inspect` con formato raw-binary
funcionan, pero el analisis completo requiere pwntools/pyelftools/unicorn
que no estan instalados en este entorno.

La instalacion verificada es v6.5.0 en /home/lucas/.local/bin/rea.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import registry  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED, BK_UNSUPPORTED,
    RAW_BINARY, Backend, sha256_de,
    estado_firma,
)


def _exe_rea() -> Optional[str]:
    """Ruta del ejecutable rea.

    MEDIDO 2026-10-15: rea esta instalado user-level en ~/.local/bin/rea.
    """
    return shutil.which("rea")


def _verify_rea_dependencies() -> Dict[str, Any]:
    """Check if REA core dependencies are available.

    Returns:
        Dict with dependency status.
    """
    result = {
        "pwntools": False,
        "pyelftools": False,
        "unicorn": False,
        "status": "unknown",
    }
    try:
        import pwntools  # noqa: F401
        result["pwntools"] = True
    except ImportError:
        pass

    try:
        import pyelftools  # noqa: F401
        result["pyelftools"] = True
    except ImportError:
        pass

    try:
        import unicorn  # noqa: F401
        result["unicorn"] = True
    except ImportError:
        pass

    # REA core can run without these for basic inspection
    has_core = shutil.which("rea") is not None
    result["core_available"] = has_core
    result["status"] = "has_core_no_heavy_deps" if has_core else "unavailable"
    return result


def _run_rea_command(argv: List[str], timeout: int = 900) -> Dict[str, Any]:
    """Ejecuta un comando rea y captura la salida.

    Args:
        argv: Lista de argumentos para el comando rea (sin el 'rea' inicial).
        timeout: Tiempo maximo en segundos.

    Returns:
        Dict con resultado del contrato (status, raw_output, etc.).
    """
    exe = _exe_rea()
    if exe is None:
        return {
            "status": BK_BLOCKED,
            "raw_output": "",
            "stdout": "",
            "stderr": "binario rea no encontrado en PATH",
            "argv": ["rea"] + argv,
            "rc": None,
            "limpieza": {"aplicada": False, "motivo": "sin ejecutable rea"},
            "limitaciones": ["el ejecutable `rea` no esta disponible en PATH"],
        }

    full_argv = [exe] + argv
    t0 = __import__("time").time()
    try:
        p = subprocess.run(
            full_argv, capture_output=True, text=True, timeout=timeout
        )
        rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
        timedout = False
    except subprocess.TimeoutExpired:
        rc, so, se, timedout = None, "", "timeout a los %ds" % timeout, True

    dur = round(__import__("time").time() - t0, 3)

    ejec = {
        "backend_id": "rea",
        "operation": "rea." + (argv[0] if argv else "unknown"),
        "command_or_api": "rea " + " ".join(argv),
        "argv": full_argv,
        "exit_status": rc,
        "raw_output_len": len(so) if so else 0,
        "stderr": se.strip()[:800] if se else "",
        "limpieza": {"aplicada": False, "caracteres_quitados": 0},
        "timeout": timedout,
        "duration_s": dur,
    }

    # Procesar salida de REA - puede ser JSON con ok/error o salida cruda
    if so:
        try:
            # REA retorna JSON estructurado incluso en errores
            parsed = json.loads(so)
            ejec["parsed_json"] = parsed
            ejec["is_json"] = True
            if isinstance(parsed, dict):
                if "ok" in parsed:
                    ejec["rea_ok"] = parsed["ok"]
                    if not parsed["ok"] and "error" in parsed:
                        ejec["rea_error"] = parsed["error"]
                elif "code" in parsed and "message" in parsed:
                    # Formato alternativo de error
                    ejec["rea_error"] = parsed
                elif "evidence_id" in parsed:
                    # Respuesta exitosa completa
                    pass
                # Guardar campos clave para posterior procesamiento
                ejec["rea_parsed_fields"] = list(parsed.keys()) if isinstance(parsed, dict) else []
        except json.JSONDecodeError:
            # No es JSON valido: guarda como salida cruda
            ejec["raw_output"] = so
            ejec["is_json"] = False
    else:
        ejec["raw_output"] = ""
        ejec["is_json"] = False

    return ejec


# ---------- ADAPTER ENTRY POINT ----------

RAW_BINARY = "raw_binary"


def _sha256_de(path: str) -> str:
    """Calcula el hash sha256 de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(
    artefacto: str,
    backend_id: str = "rea",
    timeout: int = 900,
) -> Dict[str, Any]:
    """Analiza un binario o firmware usando REA CLI.

    Esta es la operacion principal que registra en ADAPTERS.

    Args:
        artefacto: Ruta al archivo (firmware o binario) a inspeccionar.
        backend_id: Identificador del backend (por defecto "rea").
        timeout: Tiempo maximo en segundos.

    Returns:
        Dict con los seis canales del contrato RXRE.
    """
    # --- PRE-EXECUTION CONTRACT CHECK (§15) ---
    pre = {
        "input_existe": os.path.isfile(artefacto),
        "input_legible": None,
        "input_es_elf": False,
        "input_hash": "",
        "backend_existe": _exe_rea() is not None,
        "entrypoint_existe": bool(_exe_rea() is not None),
        "formato_esperado": "cualquier formato que REA soporte",
        "arquitectura_esperada": "cualquiera que REA pueda leer",
        "ok": False,
    }

    if not pre["input_existe"]:
        return {
            "status": BK_INVALID,
            "precheck": pre,
            "limitations": ["la entrada no existe: %s" % artefacto],
        }

    # Verificar firma del archivo (opcional, REA maneja muchos formatos)
    try:
        firma = estado_firma(artefacto)
        if firma == "no_legible":
            pre["input_legible"] = False
            pre["input_es_elf"] = None
            return {
                "status": BK_INVALID,
                "precheck": pre,
                "limitations": [
                    "la entrada EXISTE pero no es legible (permiso o E/S): %s"
                    % artefacto
                ],
            }
    except Exception:
        # estado_firma puede fallar en algunos entornos; no bloquear.
        pass

    # Calcular hash de entrada
    try:
        pre["input_hash"] = sha256_de(artefacto)
    except Exception:
        pass

    # Verificar que el backend (rea) este disponible
    if not pre["backend_existe"]:
        return {
            "status": BK_BLOCKED,
            "precheck": pre,
            "limitations": ["el backend `rea` no esta en PATH"],
        }

    # DEPENDENCY CHECK: verificar si los modulos pesados estan disponibles
    deps = _verify_rea_dependencies()
    tiene_deps_pesados = deps.get("pwntools", False) or deps.get(
        "pyelftools", False
    ) or deps.get("unicorn", False)

    # --- EJECUCION ---
    # Usamos el subcomando `inspect` con flags para analizar el binario
    # Default: usar formato raw-binary para maxima compatibilidad
    argv = [
        "inspect",
        artefacto,
        "--target-format", "raw-binary",
        "--architecture", "x86",
        "--entry-point", "0x0",
        "--format", "json",
        "--full-output"
    ]
    ejec = _run_rea_command(argv, timeout=timeout)

    # Procesar resultado de REA
    status_capturado = BK_UNSUPPORTED  # Default para casos no reconocidos
    message_capturado = ""
    category_capturado = "unknown"
    valor = None
    limitations = []
    raw_output = ""

    if ejec.get("is_json") and ejec.get("parsed_json"):
        parsed_json = ejec["parsed_json"]
        if isinstance(parsed_json, dict):
            # Extraer informacion del JSON de REA
            if "ok" in parsed_json:
                if parsed_json["ok"]:
                    # REA reporteo exito
                    status_capturado = BK_OK
                    # Intentar extraer datos estructurados
                    try:
                        data = parsed_json.get("data", {})
                        subject = data.get("subject", {})
                        
                        # Construir valor tipo RAW_BINARY desde la salida de REA
                        valor = {
                            "file_format": subject.get("format", "raw-binary"),
                            "arch": subject.get("architecture", "x86"),
                            "bits": None,
                            "os": None,
                            "endian": None,
                            "machine": None,
                            "compiler": None,
                            "lang": None,
                            "stripped": None,
                            "static": None,
                            "pic": None,
                            "canary": None,
                            "nx": None,
                            "relro": None,
                            "baddr": None,
                            "intrp": None,
                        }
                        
                        # Extraer limitations del resultado si existen
                        if "limitations" in data:
                            for lim in data["limitations"]:
                                if isinstance(lim, str):
                                    limitations.append(lim)
                    except Exception:
                        # Si falla la extraccion estructurada, sigue teniendo el JSON crudo
                        pass
                        
                else:
                    # REA reporteo fallo
                    error_info = parsed_json.get("error", {})
                    code = error_info.get("code", "unknown")
                    category = error_info.get("category", "unknown")
                    message = error_info.get("message", "")
                    
                    message_capturado = message
                    category_capturado = category
                    
                    # Mapear errores de REA a estados RXRE
                    if code == "target_unavailable" and category == "unsupported_target":
                        status_capturado = BK_UNSUPPORTED
                        limitations.append("REA no soporta el formato del artefacto: %s" % message)
                    elif code == "provider_unavailable":
                        status_capturado = BK_UNSUPPORTED
                        limitations.append("Dependencia de REA no disponible: %s" % message)
                    elif code == "capability_unavailable":
                        status_capturado = BK_UNSUPPORTED
                        limitations.append("Capacidad de REA no disponible: %s" % message)
                    else:
                        status_capturado = BK_ERROR
                        limitations.append("Error de REA [%s]: %s" % (code, message))
                        
            elif "code" in parsed_json and "message" in parsed_json:
                # Formato alternativo de error
                code = parsed_json.get("code", "unknown")
                category = parsed_json.get("category", "unknown")
                message = parsed_json.get("message", "")
                message_capturado = message
                category_capturado = category
                
                if code == "target_unavailable":
                    status_capturado = BK_UNSUPPORTED
                    limitations.append("REA no pudo abrir el artefacto: %s" % message)
                else:
                    status_capturado = BK_ERROR
                    limitations.append("Error de REA [%s]: %s" % (code, message))
            else:
                # JSON pero formato no reconocido
                status_capturado = BK_UNSUPPORTED
                limitations.append("REA retorno JSON pero formato no reconocido para procesamiento")
                valor = {
                    "file_format": "raw-binary",
                    "arch": "x86",
                    "bits": None,
                    "os": None,
                    "endian": None,
                    "machine": None,
                    "compiler": None,
                    "lang": None,
                    "stripped": None,
                    "static": None,
                    "pic": None,
                    "canary": None,
                    "nx": None,
                    "relro": None,
                    "baddr": None,
                    "intrp": None,
                }
    else:
        # REA no retorno JSON valido
        raw_output = ejec.get("raw_output", "")
        if raw_output:
            # Intentar extraer informacion util de salida cruda
            limitations.append("REA produjo salida sin formato JSON; capturada para revision manual")
            # Para salida cruda, asumimos que es informacion basica
            valor = {
                "file_format": "raw-binary",
                "arch": "x86",
                "bits": None,
                "os": None,
                "endian": None,
                "machine": None,
                "compiler": None,
                "lang": None,
                "stripped": None,
                "static": None,
                "pic": None,
                "canary": None,
                "nx": None,
                "relro": None,
                "baddr": None,
                "intrp": None,
            }
            if ejec.get("exit_status") == 0:
                status_capturado = BK_OK
            else:
                status_capturado = BK_UNSUPPORTED
        else:
            # Ni JSON ni salida cruda
            status_capturado = BK_ERROR
            limitations.append("REA no produjo salida ni retorno codigo de error")

    # Anadir informacion de dependencias si es relevante
    if not tiene_deps_pesados:
        limitations.append(
            "REA ejecuto con dependencias limitadas (pwntools/pyelftools/unicorn no disponibles); "
            "analisis completo con Ghidra requiere estas dependencias"
        )

    # Si el valor sigue siendo None, crear un valor basico
    if valor is None:
        valor = {
            "file_format": "raw-binary",
            "arch": "x86",
            "bits": None,
            "os": None,
            "endian": None,
            "machine": None,
            "compiler": None,
            "lang": None,
            "stripped": None,
            "static": None,
            "pic": None,
            "canary": None,
            "nx": None,
            "relro": None,
            "baddr": None,
            "intrp": None,
        }
        if not limitations:
            limitations.append("Inspeccion basica realizada con REA v6.5.0")

    # --- Construir respuesta final del contrato ---
    result_id = None
    if valor is not None:
        # Generar id similar al pattern F6
        try:
            h = hashlib.sha256(
                (
                    "%s|%s|%s|%s"
                    % (RAW_BINARY, artefacto, backend_id, json.dumps(valor, sort_keys=True, default=str))
                ).encode("utf-8")
            ).hexdigest()[:12]
            result_id = "res_re_inspect_%s" % h
        except Exception:
            pass

    respuesta = {
        "status": status_capturado,
        "result_id": result_id,
        "type": RAW_BINARY,
        "value": valor,
        "source": artefacto,
        "location": {"file": os.path.basename(artefacto)},
        "scope": "binary",
        "tool": backend_id,
        "tool_version": "6.5.0",
        "input": {"path": artefacto, "sha256": pre.get("input_hash", "")},
        "timestamp": "",
        "artifact": artefacto,
        "artifact_hash": pre.get("input_hash", ""),
        "limitations": limitations,
        "raw": raw_output if raw_output else None,
        "raw_output": raw_output,
        "stderr": ejec.get("stderr", ""),
        "exit_status": ejec.get("exit_status"),
        "raw_output_len": ejec.get("raw_output_len", 0),
        "raw_output_analysis": {
            "command": ejec.get("command_or_api", ""),
            "exit_status": ejec.get("exit_status"),
            "duration_s": ejec.get("duration_s"),
            "backend_id": ejec.get("backend_id"),
            "parsed_successfully": ejec.get("is_json", False),
            "rea_ok": ejec.get("rea_ok"),
            "rea_error_code": ejec.get("rea_error", {}).get("code") if isinstance(ejec.get("rea_error"), dict) else None,
            "rea_error_category": ejec.get("rea_error", {}).get("category") if isinstance(ejec.get("rea_error"), dict) else None,
            "dependencias_pesadas_disponibles": tiene_deps_pesados,
            "modulos_verify": {
                "pwntools": deps.get("pwntools", False),
                "pyelftools": deps.get("pyelftools", False),
                "unicorn": deps.get("unicorn", False),
            },
        },
    }

    # MEDIDO 2026-10-15: anadir precheck a la respuesta para auditoria
    respuesta["precheck"] = pre

    return respuesta


if __name__ == "__main__":
    # Modo prueba rapida: rea inspect sobre un argumento
    if len(sys.argv) > 1:
        artefacto = sys.argv[1]
        resultado = inspect(artefacto)
        print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))
    else:
        print(
            "Uso: python3 rea_inspect.py <ruta_a_fichero>\n"
            "Inspecciona el fichero usando REA CLI y muestra el resultado JSON."
        )