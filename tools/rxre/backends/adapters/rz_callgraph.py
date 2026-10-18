#!/usr/bin/env python3
"""RXRE-1636. `binary.callgraph` sobre radare2.

PRINCIPIO: radare2 `agCj` produce JSON con funciones y sus importaciones
(aristas de llamada). Capstone NO cubre callgraph: no hace analisis de
funciones. Por eso `binary.callgraph` requiere `backend_id='radare2'`.

EL ADAPTER:
- usa `<nivel>; agCj` de radare2. `nivel_analisis` en {"aa","aaa","aaaa"};
  default `aa` (el mas barato). Un nivel insuficiente PUEDE omitir funciones y
  relaciones: la respuesta declara `nivel_analisis` y su limitacion.
- acepta artefacto como PATH (str, desde CLI) o BYTES (backward compat con tests)
- produce precheck/ejecucion/provenance (contrato completo)
- produce JSON con funciones y aristas de llamada

## ETERA01-D1 (2026-10-17)

Antes, el comando era `aa; agCj` FIJO: `nivel_analisis` no existia en el
contrato, y un `aaa` solicitado se descartaba en silencio devolviendo 5 nodos
sobre /bin/ls frente a 84 con `aaa` (120 con `aaaa`). Ahora el nivel se valida,
se ejecuta el nivel SOLICITADO, y el nivel efectivo queda en
`ejecucion.nivel_analisis`. `ok` no implica completitud.

## CORRECCION 2026-10-16 (RXRE-BMS-EXT-002-D)

El adapter original tenia el MISMO defecto que rz_xrefs.py:
  entrada = artefacto.encode() if isinstance(artefacto, str) else artefacto

Trataba el path string como contenido. Via CLI, `artefacto=/bin/ls` codificaba
la CADENA `/bin/ls` a bytes, no el contenido del archivo. radare2 analizaba
el texto del path, no el ELF. `binary.callgraph` nunca funciono por la CLI.

MEDIDO 2026-10-16:
  CLI con path:   status=empty, ejecucion=null, precheck=null  (BROKEN)
  test con bytes: status=ok, nodes=74, edges=1                  (WORKS)

FIX: aceptar path de archivo directamente (como rz_cfg.py), validar isfile,
hash con sha256_de, pasar path a argv. Mantener backward compat con bytes.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple, Union

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_RXRE = os.path.abspath(os.path.join(HERE, "..", ".."))
PKG_TOOLS = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for _p in (PKG_TOOLS, PKG_RXRE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backends import registry                               # noqa: E402
from backends.contract import (                              # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK,
    CALL_GRAPH, Backend, limpiar, sha256_de, estado_firma,
)

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\r|[\x00\x07\x08]")

#: BACKENDS SOLOS CON PRODUCER
_BACKENDS: Dict[str, Backend] = {
    "radare2": Backend(
        "radare2", "r2", ["-q"], timeout=900,
        repo="https://github.com/radareorg/radare2.git",
        commit="008a7a6cd2e5acb8268f65f486760d080f3b107b",
        env_extra={"R2_NOPLUGINS": "1"},
    ),
}

#: Niveles de analisis de radare2 admitidos por `binary.callgraph`.
#: El nivel NO es cosmetico: cambia cuantas funciones descubre cada nivel.
#: MEDIDO 2026-10-17 sobre /bin/ls: aa=5 nodos, aaa=84, aaaa=120.
#: El default es `aa` (el mas barato, comportamiento historico): la respuesta
#: declara el nivel usado y su limitacion y NO impone `aaa`/`aaaa` a todos.
_NIVELES_ANALISIS: Tuple[str, ...] = ("aa", "aaa", "aaaa")
_DEFAULT_NIVEL: str = "aa"


def _ts() -> str:
    return datetime.datetime.now().isoformat()


def _elf_header(artefacto: str) -> str:
    """Lee el tipo ELF (ET_REL, ET_EXEC, etc.) sin invocar readelf."""
    try:
        with open(artefacto, "rb") as fh:
            h = fh.read(20)
    except OSError:
        return ""
    if len(h) < 18 or h[:4] != b"\x7fELF":
        return ""
    import struct as _s
    e_type, = _s.unpack_from("<H" if h[5] == 1 else ">H", h, 16)
    return {1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN",
            4: "ET_CORE"}.get(e_type, "ET_%d" % e_type)


def _argv(exe: str, artefacto: str, cmd: str) -> List[str]:
    """argv para radare2: -q -e scr.color=0 (stdout sin ANSI para JSON)."""
    return [exe, "-q", "-e", "scr.color=0", "-c", cmd, artefacto]


def _cmd_agCj(nivel: str) -> str:
    """Comando r2 para `binary.callgraph`: `<nivel>; agCj`.

    ETERA01-D1: costura UNICA del verbo de analisis. Aislarla permite una
    ablacion por monkeypatch (reintroducir el `aa` fijo) que demuestra que la
    prueba discriminante de nivel lo detecta (test_callgraph_etera01_d1).
    """
    return "%s; agCj" % nivel


def _nivel_efectivo(cmd_str: str, solicitado: str) -> str:
    """Nivel REALMENTE usado, derivado del comando construido.

    No es un eco del nivel pedido: se lee del comando que se ejecuta. Si no
    expone un nivel admitido, cae al solicitado. Asi `ejecucion.nivel_analisis`
    es evidencia del comando, no una afirmacion del solicitante.
    """
    nivel = cmd_str.split(";", 1)[0].strip()
    return nivel if nivel in _NIVELES_ANALISIS else solicitado


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _limpiar_tmp(tmp_path: str, borra: bool) -> None:
    """Borra `tmp_path` SOLO si `borra` es True.

    CONTRATO (RXRE-FUEGO-001):
        borra=True  -> RXRE creo ese fichero con tempfile; se elimina.
        borra=False -> `tmp_path` es un archivo del usuario; NO SE TOCA.

    `borra` NO significa "existe" ni "es temporal": significa "RXRE es el
    dueno del fichero". Pasar aqui un flag con polaridad contraria destruye
    el artefacto del usuario, que es exactamente lo que hacia este modulo
    antes de la reparacion (la bandera era `es_path`, que vale True cuando
    el path ES el original).
    """
    if borra:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _cadena_backend_local(ejec: Dict[str, Any], ident: Dict[str, Any],
                          artefacto: str, input_hash: str) -> Dict[str, Any]:
    """La cadena del backend, extraible del envelope (§9 EPISTEMIC KERNEL)."""
    return {
        "backend_id": ident.get("backend_id", ""),
        "tool_version": ident.get("tool_version", ""),
        "backend_version_status": ident.get("backend_version_status", ""),
        "version_verificada": ident.get("version_verificada"),
        "repository": ident.get("repository", ""),
        "repository_commit": ident.get("repository_commit", ""),
        "command_or_api": ejec.get("command_or_api", ""),
        "argv": ejec.get("argv") or [],
        "exit_status": ejec.get("exit_status"),
        "raw_output_len": ejec.get("raw_output_len"),
        "stderr": (ejec.get("stderr", "") or "")[:400],
        "limpieza": ejec.get("limpieza") or {},
        "input_artifact": artefacto,
        "input_hash": input_hash,
        "transformacion": "r2 -q -e scr.color=0 -c '%s; agCj' <artefacto> -> "
                          "limpieza ANSI -> json.loads -> nodos/aristas"
                          % ejec.get("nivel_analisis", _DEFAULT_NIVEL),
        "normalizador": "backends.adapters.rz_callgraph.callgraph",
        "provenance_estado": "completa",
        "chain": ["result_id", "operation_id", "backend", "tool_version",
                  "repository_commit", "input_artifact", "input_hash",
                  "command_or_api", "argv", "raw_output",
                  "transformacion", "normalizador", "normalized_result"],
    }


def _build_resultados(data: List[Dict], artefacto_ref: str, backend_id: str,
                      identidad: Dict, input_hash: str,
                      inicio=None, longitud=None,
                      nivel_analisis: str = _DEFAULT_NIVEL
                      ) -> Tuple[List[Dict], int, int]:
    """Construye results list + nodos/aristas desde los datos de agCj."""
    results = []
    nodes = 0
    edges = 0
    for i, func in enumerate(data):
        if not isinstance(func, dict):
            continue
        nodes += 1
        func_name = func.get("name", "func_%d" % i)
        func_addr = func.get("offset", 0)
        imports = func.get("imports", [])
        edges += len(imports)
        result_id = "ccg_%s" % hashlib.sha256(
            ("%s|%s|%d|%s" % (artefacto_ref, backend_id, i,
                              json.dumps(func, sort_keys=True, default=str))
             ).encode()).hexdigest()[:16]
        result = {
            "result_id": result_id,
            "type": CALL_GRAPH,
            "value": {
                "name": func_name,
                "offset": func_addr,
                "imports": imports,
                "nodos": nodes,
            },
            "source": artefacto_ref,
            "location": {"file": os.path.basename(artefacto_ref),
                         "offset": inicio},
            "scope": "binary",
            "tool": backend_id,
            "tool_version": identidad.get("tool_version", ""),
            "input": {"path": artefacto_ref, "sha256": input_hash},
            "timestamp": _ts(),
            "artifact": artefacto_ref,
            "artifact_hash": input_hash,
            "status": "observed",
            "raw": {
                "n_coincidencias": nodes,
                "nodos": nodes,
                "edges": edges,
            },
            "limitations": [
                "RAW_BINARY: lo que r2 declara, no semantica verificada del callgraph.",
                "nivel_analisis '%s': un nivel insuficiente (aa) puede no "
                "descubrir todas las funciones ni relaciones." % nivel_analisis,
            ],
        }
        results.append(result)
    return results, nodes, edges


def callgraph(artefacto: Union[str, bytes], **kwargs) -> Dict[str, Any]:
    """Implementacion de `binary.callgraph`. RXRE-1636.

    Contrato:
    - inputs: artefacto (path str o bytes), inicio, longitud, backend_id, timeout,
              nivel_analisis en {"aa","aaa","aaaa"} (default "aa"),
              fixture_json opcional
    - outputs: {"status": ok|empty|error, "nodes": int, "edges": int,
                "results": [...], "precheck": {...}, "ejecucion": {...},
                "provenance": ..., "backend": str, "backend_identity": dict,
                "nivel_analisis": str (el nivel EFECTIVAMENTE usado)}

    SEMANTICA DE ESTADO (ETERA01-D1, determinada por prueba):
    - empty: el producer no declaro ninguna funcion (nodes == 0).
    - ok:    el producer declaro >= 1 funcion AL NIVEL SOLICITADO.
             `ok` NO es prueba de COMPLETITUD: con `aa` el grafo puede ser
             parcial. El nivel efectivo viaja en `ejecucion.nivel_analisis`
             y la limitacion se declara. No se emite `partial` desde una sola
             corrida porque no hay evidencia de parcialidad relativa a un nivel
             mas profundo (mismo patron que rz_cfg/rz_xrefs).

    Diferencia clave con binary.xrefs: callgraph captura relaciones
    interfuncionales; xrefs captura referencias directas.
    """
    backend_id = kwargs.get("backend_id", "radare2")
    nivel_analisis = kwargs.get("nivel_analisis", _DEFAULT_NIVEL)
    if nivel_analisis is None:
        nivel_analisis = _DEFAULT_NIVEL
    timeout = kwargs.get("timeout", 300)
    inicio = kwargs.get("inicio")
    longitud = kwargs.get("longitud")
    fixture_json = kwargs.get("fixture_json")

    # --- VALIDAR backend_id ---
    if backend_id not in _BACKENDS:
        return {
            "status": BK_ERROR,
            "message": "Backend '%s' no tiene producer para binary.callgraph"
                       % backend_id,
            "precheck": {},
            "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: backend invalido",
            "results": [], "limitations": [
                "backend_id requerido: radare2 (rizin no soporta agCj)"],
        }

    # --- VALIDAR nivel_analisis ---
    # No se ignora en silencio: un nivel fuera de `_NIVELES_ANALISIS` es un
    # error de parametro, no un `aa` encubierto.
    if nivel_analisis not in _NIVELES_ANALISIS:
        return {
            "status": BK_ERROR,
            "precheck": {},
            "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: parametro invalido",
            "message": "nivel_analisis debe ser uno de %s, no '%s'" % (
                ", ".join(_NIVELES_ANALISIS), nivel_analisis),
            "results": [],
            "limitations": [
                "nivel_analisis debe ser uno de %s, no '%s'" % (
                    ", ".join(_NIVELES_ANALISIS), nivel_analisis)],
        }

    b: Backend = _BACKENDS[backend_id]

    # --- PRE-EXECUTION CONTRACT CHECK ---
    pre: Dict[str, Any] = {
        "input_existe": False,
        "input_es_elf": False,
        "elf_tipo": "",
        "input_hash": "",
        "backend_existe": b.existe(),
        "backend_path": b.path() or "",
        "verb": nivel_analisis,
        "salida_cmd": "agCj",
        "inicio": inicio,
        "longitud": longitud,
        "usa_fixture": bool(fixture_json),
        "ok": False,
    }

    # RXRE-FUEGO-001: quien es el dueno de `tmp_path`?
    #
    # Es la UNICA bandera que autoriza `_limpiar_tmp` a hacer `os.unlink`.
    #   True  = RXRE creo ese fichero con tempfile -> se puede borrar.
    #   False = `tmp_path` es un archivo del usuario  -> NO se toca JAMAS.
    #
    # Se inicializa a False (conservador): si un camino futuro deja la bandera
    # sin asignar, la limpieza no borra nada en vez de borrar de mas.
    #
    # El defecto anterior pasaba `es_path`, que significa justo lo contrario
    # ("este path ES el original"), por lo que la limpieza destruia el
    # artefacto del usuario y dejaba huerfano su propio temporal.
    rxre_creo_tmp = False

    # --- ARTEFACTO REQUERIDO ---
    if artefacto is None:
        return {
            "status": BK_ERROR,
            "message": "artefacto es requerido",
            "precheck": pre,
            "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: artefacto requerido",
            "results": [], "limitations": ["artefacto es None"],
        }

    # --- MANEJAR FIXTURE ---
    if fixture_json:
        try:
            fixture_data = json.loads(fixture_json)
            if isinstance(fixture_data, str):
                entrada = bytes.fromhex(fixture_data)
            elif isinstance(fixture_data, list):
                entrada = bytes(fixture_data)
            else:
                entrada = b""
        except Exception:
            return {
                "status": BK_INVALID,
                "precheck": pre,
                "ejecucion": None,
                "provenance": "PROVENANCE_INCOMPLETE: fixture invalido",
                "message": "no se pudo parsear fixture_json",
                "results": [], "limitations": ["no se pudo parsear fixture_json"],
            }

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".bin", delete=False
        ) as tmp:
            tmp.write(entrada)
            tmp_path = tmp.name
        rxre_creo_tmp = True          # RXRE creo este temporal: es suyo
        pre["input_existe"] = True
        pre["input_hash"] = _sha256_bytes(entrada)[:16]
        pre["elf_tipo"] = "ET_BYTES"
        pre["input_es_elf"] = entrada[:4] == b"\x7fELF"
        artifact_ref = "fixture:%s" % pre["input_hash"][:8]
        ident = {"backend_id": "fixture", "tool_version": "",
                 "version_verificada": False,
                 "backend_version_status": "UNVERIFIED"}
        rc, so, se, dur, timedout = 0, "", "modo fixture: producer simulado", 0.0, False
        argv = ["<fixture>", tmp_path]
        ident_backend = "fixture"
        salida_cmd = "agCj"
        cmd_str = _cmd_agCj(nivel_analisis)

    else:
        # --- MANEJAR ARTEFACTO: path (str) o bytes ---
        # MEDIDO 2026-10-16: el CLI pasa un PATH STRING. El adapter debe
        # diferenciar: un path que existe se pasa AL FILE DIRECTAMENTE a r2
        # (como rz_cfg.py), no se codifica como contenido.
        es_path = isinstance(artefacto, str) and os.path.isfile(artefacto)

        if es_path:
            pre["input_existe"] = True
            if estado_firma(artefacto) == "no_legible":
                return {
                    "status": BK_INVALID,
                    "precheck": pre,
                    "ejecucion": None,
                    "provenance": "PROVENANCE_INCOMPLETE: no legible",
                    "message": "la entrada EXISTE pero no es legible "
                               "(permiso o E/S): %s" % artefacto,
                    "results": [],
                    "limitations": [
                        "la entrada EXISTE pero no es legible "
                        "(permiso o E/S): %s" % artefacto,
                        "no se pudo leer la firma: NO se sabe si es ELF",
                        "no se invoco al producer: sin ELF no hay callgraph"],
                }
            pre["elf_tipo"] = _elf_header(artefacto)
            if not pre["elf_tipo"]:
                return {
                    "status": BK_INVALID,
                    "precheck": pre,
                    "ejecucion": None,
                    "provenance": "PROVENANCE_INCOMPLETE: not ELF",
                    "message": "la entrada no es un ELF: %s" % artefacto,
                    "results": [],
                    "limitations": [
                        "la entrada no es un ELF (firma distinta de \\x7fELF): %s" % artefacto,
                        "no se invoco al producer: sin ELF no hay callgraph"],
                }
            pre["input_es_elf"] = True
            pre["input_hash"] = sha256_de(artefacto)
            artifact_ref = artefacto
            tmp_path = artefacto          # usar el path directamente
            rxre_creo_tmp = False         # es el ORIGINAL: nunca se borra
        elif isinstance(artefacto, (bytes, bytearray)):
            entrada_bytes = bytes(artefacto)
            pre["input_existe"] = True
            pre["input_hash"] = _sha256_bytes(entrada_bytes)[:16]
            pre["elf_tipo"] = "ET_BYTES"
            pre["input_es_elf"] = entrada_bytes[:4] == b"\x7fELF"
            artifact_ref = "bytes:%s" % pre["input_hash"][:8]
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".bin", delete=False
            ) as tmp:
                tmp.write(entrada_bytes)
                tmp_path = tmp.name
            rxre_creo_tmp = True          # RXRE creo este temporal: es suyo
        else:
            pre["input_existe"] = False
            return {
                "status": BK_INVALID,
                "precheck": pre,
                "ejecucion": None,
                "provenance": "PROVENANCE_INCOMPLETE: artefacto invalido",
                "message": "el artefacto '%s' no es un path de archivo existente ni bytes" % str(artefacto)[:80],
                "results": [],
                "limitations": [
                    "el artefacto no es un path existente ni bytes",
                    "para bytes: pasar como bytes, no como string"],
            }

        # --- VERIFICAR BACKEND ---
        ident = b.identidad()
        ident_backend = backend_id
        if not pre["backend_existe"]:
            _limpiar_tmp(tmp_path, rxre_creo_tmp)
            return {
                "status": BK_BLOCKED,
                "precheck": pre,
                "ejecucion": None,
                "provenance": "PROVENANCE_INCOMPLETE: backend missing",
                "results": [],
                "limitations": ["el backend %s no esta en PATH" % backend_id],
            }

        # --- EJECUCION ---
        # ETERA01-D1: el verbo de analisis es el SOLICITADO, no `aa` fijo.
        cmd_str = _cmd_agCj(nivel_analisis)
        salida_cmd = "agCj"
        argv = _argv(b.path(), tmp_path, cmd_str)
        t0 = time.time()
        try:
            p = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout
            )
            rc = p.returncode
            so = p.stdout or ""
            se = p.stderr or ""
            timedout = False
        except subprocess.TimeoutExpired:
            rc, so, se = None, "", "timeout a los %ds" % timeout
            timedout = True
        except OSError as exc:
            rc, so, se = None, "", str(exc)
            timedout = False
        dur = round(time.time() - t0, 3)

    # --- LIMPIEZA DE OUTPUT ---
    limpio, n_quit = limpiar(so)
    texto = ANSI.sub("", limpio)

    # ETERA01-D1: nivel EFECTIVAMENTE usado = el que aparece en el comando.
    # No se confia en el solicitado: `ejecucion.nivel_analisis` se deriva del
    # comando que realmente se construyo (y por tanto se ejecuto).
    nivel_efectivo = _nivel_efectivo(cmd_str, nivel_analisis)
    pre["verb"] = nivel_efectivo

    ejec = {
        "backend_id": ident_backend,
        "operation": "binary.callgraph",
        "command_or_api": "r2 -q -e scr.color=0 -c '%s' <artefacto>" % cmd_str,
        "argv": argv,
        "exit_status": rc,
        "raw_output_len": len(so),
        "stderr": se.strip()[:400],
        "limpieza": {"aplicada": n_quit > 0, "caracteres_quitados": n_quit},
        "timeout": timedout,
        "duration_s": dur,
        "salida_cmd": salida_cmd,
        "nivel_analisis": nivel_efectivo,   # nivel EFECTIVAMENTE usado
        "inicio": inicio,
        "longitud": longitud,
    }

    if timedout:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_BLOCKED,
            "precheck": pre,
            "ejecucion": ejec,
            "backend": ident_backend,
            "limitations": ["timeout a los %ds" % timeout],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: timeout",
            "message": "timeout a los %ds" % timeout,
        }

    if rc not in (0, None):
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_ERROR,
            "precheck": pre,
            "ejecucion": ejec,
            "backend": ident_backend,
            "message": "Error en radare2: %s" % (se.strip() or so.strip())[:200],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: producer error",
            "limitations": [
                "el producer salio rc=%s: %s" % (rc, (se.strip() or so.strip())[:300])],
        }

    # --- PARSEAR JSON ---
    inicio_json = texto.find("[")
    if inicio_json < 0:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_ERROR,
            "precheck": pre,
            "ejecucion": ejec,
            "backend": ident_backend,
            "message": "Salida no JSON de agCj: %s" % texto[:100],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: no JSON",
            "limitations": [
                "la salida de agCj no contiene JSON. stdout: %s" % texto[:200]],
        }

    try:
        data = json.loads(texto[inicio_json:])
    except ValueError as exc:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_ERROR,
            "precheck": pre,
            "ejecucion": ejec,
            "backend": ident_backend,
            "message": "JSON mal formado de agCj: %s" % exc,
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: JSON invalido",
            "limitations": ["JSON mal formado de agCj: %s" % exc],
        }

    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        data = []

    results, nodes, edges = _build_resultados(
        data, artifact_ref, backend_id, ident,
        pre["input_hash"], inicio, longitud, nivel_efectivo
    )

    # ETERA01-D1: `empty` es "el producer no declaro funciones". `ok` es "hay
    # funciones AL NIVEL SOLICITADO", NO "el grafo esta completo". El nivel
    # efectivo y su limitacion viajan en `ejecucion`/`limitations`.
    empty = (nodes == 0)
    status = BK_EMPTY if empty else BK_OK
    pre["ok"] = True

    _limpiar_tmp(tmp_path, rxre_creo_tmp)

    return {
        "status": status,
        "precheck": pre,
        "ejecucion": ejec,
        "backend": ident_backend,          # string, backward compat
        "backend_identity": ident,        # dict completo
        "callgraph_raw": data,            # backward compat con tests
        "nodes": nodes,                   # backward compat
        "edges": edges,                   # backward compat
        "results": results,
        "nivel_analisis": nivel_efectivo,   # nivel EFECTIVAMENTE usado
        "inicio": inicio,
        "longitud": longitud,
        "metadata": {
            "limites": {"inicio": inicio, "longitud": longitud},
            "backend_version": backend_id,
            "nota": "Adapter rz_callgraph.py (2026-10-17): binary.callgraph via "
                    "radare2 agCj. artefacto acepta path de archivo o bytes; "
                    "nivel_analisis controla la profundidad del analisis.",
        },
        "limitations": [
            "RAW_BINARY: lo que r2 declara, no semantica verificada.",
            "binary.callgraph NO es binary.xrefs: captura relaciones "
            "interfuncionales, no referencias directas.",
            "Solo radare2 soporta agCj; rizin no (produce ASCII).",
            "nivel_analisis '%s': 'aa' es el nivel mas barato y PUEDE omitir "
            "funciones y relaciones; comparar con 'aaa'/'aaaa' sobre el mismo "
            "artefacto cuando la completitud importe. `ok` no implica "
            "completitud." % nivel_efectivo],
        "provenance": {
            "estado": "completa",
            "input_hash": pre["input_hash"],
            "backend": ident_backend,
            "command_or_api": ejec.get("command_or_api", ""),
            "transformacion": "r2 -c '%s; agCj' <artefacto> -> limpieza ANSI "
                              "-> json.loads -> nodos/aristas" % nivel_efectivo,
            "normalizador": "backends.adapters.rz_callgraph.callgraph",
            "tool_version": ident.get("tool_version", ""),
            "repository_commit": ident.get("repository_commit", ""),
            "provenance_estado": "completa",
        },
        "cadena_backend": _cadena_backend_local(
            ejec, ident, artifact_ref, pre["input_hash"]),
    }


def persistir(env: Dict[str, Any], db: Optional[Any] = None,
              question: str = "") -> Optional[str]:
    """Guarda la operacion para que `explain` reconstruya la evidencia.

    Sigue el patron de rz_inspect.persistir / rz_cfg.persistir.
    """
    from core import store as S
    _abierta_por_nosotros = db is None
    c = db or S.conectar()

    ids = [r["result_id"] for r in env.get("results") or []
           if isinstance(r, dict) and r.get("result_id")]
    existentes = []
    for i in ids:
        if c.execute(
            "SELECT 1 FROM results WHERE result_id=?", (i,)
        ).fetchone():
            existentes.append(i)
    if existentes:
        if _abierta_por_nosotros:
            c.close()
        return "COLISION:%s" % ",".join(existentes)

    pre = env.get("precheck") or {}
    res0 = (env.get("results") or [{}])[0] if env.get("results") else {}
    artefacto = res0.get("source", "") or res0.get("artifact", "") or ""
    target = "binary:%s" % (os.path.basename(artefacto) or "callgraph")

    op_id = S.registrar(
        c,
        {"request_id": "",
         "question": question or ("callgraph de %s" % artefacto),
         "capability": "binary.callgraph",
         "scope": "binary",
         "target": target},
        {"operation": "binary.callgraph",
         "status": env.get("status"),
         "backend": env.get("backend_identity") or env.get("backend"),
         "ejecucion": env.get("ejecucion"),
         "provenance": env.get("provenance"),
         "precheck": pre,
         "cadena_backend": env.get("cadena_backend", {}),
         "results": env.get("results") or []},
        duracion=(env.get("ejecucion") or {}).get("duration_s", 0))

    if _abierta_por_nosotros:
        c.close()
    return op_id
