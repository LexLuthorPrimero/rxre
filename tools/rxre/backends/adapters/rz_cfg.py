#!/usr/bin/env python3
"""RXRE-ARCH-EXEC-002. Adapters para `binary.cfg` y `binary.dataflow`.

## QUE CIERRA ESTE FICHERO

`binary.cfg` y `binary.dataflow` estaban declaradas como AVAILABLE en el
registry (radare2 `agfj` y `afvxj` producen JSON), pero NO estaban en
ADAPTERS → `esta_permitida` devolvia `blocked` con motivo "sin adapter
no hay producer". La capability era declarada pero no ejecutable.

Este adapter cierra la brecha: registra `cfg` y `dataflow` en ADAPTERS, y
el producer real es `r2 -q -c "aaa; agfj" <artefacto>` (CFG) o
`r2 -q -c "aaa; afvxj" <artefacto>` (data flow).

## MEDIDO, NO SUPUESTO

MEDIDO 2026-10-14, `/bin/ls` (ELF ET_DYN x86-64), radare2 5.9.8:

    r2 -q -e scr.color=0 -c "aaa; agfj" /bin/ls → JSON valido (array de CFGs)
    r2 -q -e scr.color=0 -c "aaa; afvxj" /bin/ls → JSON valido (dict reads/writes)

rizin 0.7.4:

    rizin -q -N -e scr.color=0 -c "aaa; agfj" /bin/ls → JSON valido
    rizin -q -N -e scr.color=0 -c "aaa; afvxj" /bin/ls → JSON MAL FORMADO

Por eso el registry declara rizin=PARTIAL y radare2=AVAILABLE. El adapter
ejecuta el backend solicitado y deja la diferencia en `limitations`:
NINGUN backend es autoridad.

## POR QUE UN FICHERO NUEVO Y NO AGREGAR A rz_functions.py

`rz_functions.py` cierra `binary.functions` y `binary.basic_blocks`. Agregar
cfg y dataflow al mismo modulo cambiaria su identidad (el docstring dice
"Adaptador de `binary.functions`"). El separar: `rz_cfg` tiene su propio
scope (CFG y dataflow), su propio MEDIDO, y no crea dependencia accidental
entre capabilities.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_RXRE = os.path.abspath(os.path.join(HERE, "..", ".."))
PKG_TOOLS = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
import sys
for _p in (PKG_TOOLS, PKG_RXRE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backends import registry                               # noqa: E402
from backends.contract import (                              # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK,
    BACKEND_RC, Backend, limpiar, sha256_de, sha256_texto, estado_firma,
)
from . import provenance as _prov

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\r|[\x00\x07\x08]")


def _elf_tipo(artefacto: str) -> str:
    """Lee el tipo ELF (ET_REL, ET_EXEC, etc.) sin invocar readelf."""
    try:
        with open(artefacto, "rb") as fh:
            h = fh.read(20)
    except OSError:
        return ""
    if len(h) < 18 or h[:4] != b"\x7fELF":
        return ""
    e_type, = struct.unpack_from("<H" if h[5] == 1 else ">H", h, 16)
    return {1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN",
            4: "ET_CORE"}.get(e_type, "ET_%d" % e_type)


def _argv(backend_id: str, exe: str, artefacto: str, cmd: str) -> List[str]:
    """El argv correcto para cada producer.

    rizin necesita -N (no init) para evitar que cargue plugins; r2 no.
    -e scr.color=0 deshabilita ANSI (MEDIDO: sin esto el JSON no parsea).
    """
    if backend_id == "rizin":
        return [exe, "-q", "-N", "-e", "scr.color=0",
                "-c", cmd, "-A", artefacto]
    return [exe, "-q", "-e", "scr.color=0", "-c", cmd, "-A", artefacto]


def _backends_de(capacidad: str) -> List[str]:
    """Que producers declara ESTA capacidad."""
    try:
        from backends import dispatch as _d
        return sorted(_d.esta_permitida(capacidad).get("backends") or [])
    except Exception:
        return []


def _ejecutar(backend_id: str, artefacto: str, salida_cmd: str,
              verb: str = "aa", timeout: int = 900,
              fixture_json: str = "") -> Dict[str, Any]:
    """Ejecución compartida por cfg() y dataflow().

    Devuelve el envelope base con precheck/ejecucion/backend, y el texto
    JSON limpio para parsear. No parsea: deja eso al caller.
    """
    # --- PRE-EXECUTION CONTRACT CHECK ---
    pre = {"input_existe": os.path.isfile(artefacto),
           "input_es_elf": False, "elf_tipo": "",
           "input_hash": "",
           "backend_existe": False, "backend_path": "",
           "verb": verb, "salida_cmd": salida_cmd,
           "usa_fixture": bool(fixture_json), "ok": False}

    if fixture_json:
        if not os.path.isfile(fixture_json):
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["no existe el fixture: %s"
                                     % fixture_json]}
        bruto = open(fixture_json, encoding="utf-8").read()
        argv = ["<fixture>", fixture_json]
        ident_backend = "fixture"
        ident = {"backend_id": "fixture", "tool_version": "",
                 "version_verificada": False,
                 "backend_version_status": "UNVERIFIED"}
        rc, so, se, dur, timedout = 0, bruto, "modo fixture: producer simulado", 0.0, False
    else:
        if not pre["input_existe"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["la entrada no existe: %s" % artefacto]}
        if os.path.isfile(artefacto) and estado_firma(artefacto) == "no_legible":
            pre["elf_tipo"] = ""
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada EXISTE pero no es legible (permiso o E/S): %s"
                        % artefacto,
                        "no se pudo leer la firma: NO se sabe si es ELF",
                        "no se invoco al producer: %s sobre artefacto ilegible "
                        "no produce CFG" % salida_cmd]}
        pre["elf_tipo"] = _elf_tipo(artefacto)
        if not pre["elf_tipo"]:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": [
                        "la entrada no es un ELF: %s" % artefacto,
                        "no se invoco al producer: %s sobre no-ELF no produce CFG"
                        % salida_cmd]}
        pre["input_es_elf"] = True
        pre["input_hash"] = sha256_de(artefacto)
        try:
            ent = registry.get(backend_id)
        except KeyError:
            return {"status": BK_INVALID, "precheck": pre,
                    "limitations": ["backend desconocido: %r" % backend_id]}
        b: Backend = ent["backend"]
        pre["backend_existe"] = b.existe()
        pre["backend_path"] = b.path() or ""
        if not pre["backend_existe"]:
            return {"status": BK_BLOCKED, "precheck": pre,
                    "limitations": ["el backend %s no esta en PATH"
                                     % backend_id]}
        ident = b.identidad()
        ident_backend = backend_id
        argv = _argv(backend_id, b.path(), artefacto, "%s; %s" % (verb, salida_cmd))
        t0 = time.time()
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout)
            rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
            timedout = False
        except subprocess.TimeoutExpired:
            rc, so, se = None, "", "timeout a los %ds" % timeout
            timedout = True
        except OSError as exc:
            rc, so, se = None, "", str(exc)
            timedout = False
        dur = round(time.time() - t0, 3)

    ejec = {"backend_id": ident_backend or backend_id,
            "operation": "binary.cfg" if salida_cmd == "agfj" else "binary.dataflow",
            "command_or_api": "%s; %s" % (verb, salida_cmd),
            "argv": argv, "exit_status": rc,
            "stderr": se.strip()[:400], "timeout": timedout,
            "duration_s": dur, "verb": verb, "salida_cmd": salida_cmd}

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": ["timeout a los %ds: %s es costoso"
                                     % (timeout, salida_cmd)]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident or {}, "limitations": ejec.get("limitations", []),
                "provenance": _prov.construir(estado=_prov.ESTADO_INCOMPLETA, motivo_incompleta='timeout', transformacion="rizin -c 'af; agj' -> json.loads -> grafo de bloques con nodos y aristas", normalizador='backends.adapters.rz_cfg._ejecutar')}

    if rc not in (0, None):
        ejec.update({"status": BK_ERROR,
                     "limitations": ["el producer salio rc=%s: %s"
                                     % (rc, (se.strip() or so.strip())[:300])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident or {}, "limitations": ejec.get("limitations", []),
                "provenance": _prov.construir(estado=_prov.ESTADO_INCOMPLETA, motivo_incompleta='producer error', transformacion="rizin -c 'af; agj' -> json.loads -> grafo de bloques con nodos y aristas", normalizador='backends.adapters.rz_cfg._ejecutar')}

    # Parsear JSON (limpiar ANSI primero)
    texto = ANSI.sub("", so)
    inicio = texto.find("[") if salida_cmd == "agfj" else texto.find("{")
    if inicio < 0:
        texto_stripped = texto[:200]
        ejec.update({"status": BK_ERROR,
                     "limitations": [
                         "la salida de %s no contiene JSON. stdout: %s"
                         % (salida_cmd, texto_stripped)]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident or {},
                "provenance": _prov.construir(estado=_prov.ESTADO_INCOMPLETA, motivo_incompleta='no JSON', transformacion="rizin -c 'af; agj' -> json.loads -> grafo de bloques con nodos y aristas", normalizador='backends.adapters.rz_cfg._ejecutar')}

    try:
        parsed = json.loads(texto[inicio:])
    except ValueError as exc:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["JSON mal formado de %s: %s"
                                     % (salida_cmd, exc)]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident or {},
                "provenance": _prov.construir(estado=_prov.ESTADO_INCOMPLETA, motivo_incompleta='JSON invalido', transformacion="rizin -c 'af; agj' -> json.loads -> grafo de bloques con nodos y aristas", normalizador='backends.adapters.rz_cfg._ejecutar')}

    pre["ok"] = True
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident or {}, "parsed": parsed,
            "provenance": _prov.desde_precheck(pre, transformacion="rizin -c 'af; agj' -> json.loads -> grafo de bloques con nodos y aristas", normalizador='backends.adapters.rz_cfg._ejecutar')}


def _backends_disponibles() -> str:
    return ", ".join(_backends_de("binary.cfg")) or "ninguno"


def cfg(artefacto: str, backend_id: str = "radare2",
        timeout: int = 900, verb: str = "aa",
        fixture_json: str = "") -> Dict[str, Any]:
    """`binary.cfg`: Control Flow Graph como JSON.

    Producer: r2 `agfj` / rizin `agfj` (despues de análisis `aa`).
    SALIDA: array de objetos con blocks/ops por función.
    """
    r = _ejecutar(backend_id, artefacto, "agfj", verb, timeout, fixture_json)
    if r["status"] != BK_OK:
        r.pop("parsed", None)
        return r
    parsed = r.pop("parsed")
    n_funciones = len(parsed) if isinstance(parsed, list) else 0
    n_bloques = sum(len(f.get("blocks", [])) for f in parsed if isinstance(f, dict))

    ident = r["backend"]
    artifact_ref = artefacto if not fixture_json else fixture_json
    version = ident.get("tool_version", "")
    rid = "res_cfg_" + sha256_texto(
        "%s|%s|%s|%d" % (artifact_ref, backend_id, verb, n_funciones))[:12]

    limitations = [
        "RAW_BINARY: lo que r2 declara, no semantica verificada del CFG.",
        "r2 5.9.8 y rizin 0.7.4 pueden diferir en coverage: NINGUN backend "
        "es autoridad. Usado: %s." % backend_id,
        "el verbo de análisis es '%s': 'aa' puede no descubrir todas las "
        "funciones. Comparar con 'aaa' para binarios complejos." % verb,
    ]
    if backend_id == "rizin":
        limitations.append(
            "rizin 0.7.4 es PARCIAL para binary.cfg: el registry documenta "
            "que emite salida con limitaciones de coverage.")

    result = {
        "result_id": rid,
        "type": "control_flow",
        "value": {"n_funciones": n_funciones, "n_bloques": n_bloques,
                  "cfg": parsed[:500]},  # sample de los primeros grafos
        "completitud": {"completo": len(parsed) <= 500,
                        "omitidos": max(0, len(parsed) - 500),
                        "limite": 500,
                        "elemento": "cfg"},
        "source": artifact_ref,
        "location": {"file": os.path.basename(artifact_ref)},
        "scope": "binary",
        "tool": backend_id,
        "tool_version": version,
        "input": {"path": artifact_ref,
                  "sha256": r["precheck"].get("input_hash", "")},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": artifact_ref,
        "artifact_hash": r["precheck"].get("input_hash", ""),
        "status": "observed",
        "limitations": limitations,
        "raw": "",
    }
    r["results"] = [result]
    r["n_funciones"] = n_funciones
    r["n_bloques"] = n_bloques
    r["limitations"] = limitations
    return r


def dataflow(artefacto: str, backend_id: str = "radare2",
             timeout: int = 900, verb: str = "aa",
              fixture_json: str = "") -> Dict[str, Any]:
    """`binary.dataflow`: Data flow (reads/writes) como JSON.

    Producer: r2 `afvxj` / rizin `afvxj` (despues de análisis `aa`).
    SALIDA: dict con 'reads' y 'writes'.
    """
    r = _ejecutar(backend_id, artefacto, "afvxj", verb, timeout, fixture_json)
    if r["status"] != BK_OK:
        r.pop("parsed", None)
        return r
    parsed = r.pop("parsed")
    n_reads = len(parsed.get("reads", [])) if isinstance(parsed, dict) else 0
    n_writes = len(parsed.get("writes", [])) if isinstance(parsed, dict) else 0

    ident = r["backend"]
    artifact_ref = artefacto if not fixture_json else fixture_json
    version = ident.get("tool_version", "")
    rid = "res_dataflow_" + sha256_texto(
        "%s|%s|%s|%d|%d" % (artifact_ref, backend_id, verb, n_reads, n_writes))[:12]

    limitations = [
        "RAW_BINARY: lo que r2 declara, no semantica verificada de data flow.",
        "r2 5.9.8 y rizin 0.7.4 pueden diferir: rizin 0.7.4 produce "
        "afvxj MAL FORMADO (registry: PARTIAL). Usado: %s." % backend_id,
        "el scope es global (no por función): afvxj da reads/writes globales.",
    ]

    result = {
        "result_id": rid,
        "type": "data_flow",
        "value": {"n_reads": n_reads, "n_writes": n_writes,
                  "dataflow": parsed},
        "source": artifact_ref,
        "location": {"file": os.path.basename(artifact_ref)},
        "scope": "binary",
        "tool": backend_id,
        "tool_version": version,
        "input": {"path": artifact_ref,
                  "sha256": r["precheck"].get("input_hash", "")},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact": artifact_ref,
        "artifact_hash": r["precheck"].get("input_hash", ""),
        "status": "observed",
        "limitations": limitations,
        "raw": "",
    }
    r["results"] = [result]
    r["n_reads"] = n_reads
    r["n_writes"] = n_writes
    r["limitations"] = limitations
    return r


def persistir(env: Dict[str, Any], db=None, question: str = "") -> Optional[str]:
    """Guarda la operacion para que `explain` pueda reconstruirla.

    Sigue el patron de rz_inspect.persistir / rz_functions.persistir.
    """
    from core import store as S
    _abierta_por_nosotros = db is None
    c = db or S.conectar()

    ids = [r["result_id"] for r in env.get("results") or []
           if isinstance(r, dict) and r.get("result_id")]
    existentes = []
    for i in ids:
        if c.execute("SELECT 1 FROM results WHERE result_id=?", (i,)).fetchone():
            existentes.append(i)
    if existentes:
        if _abierta_por_nosotros:
            c.close()
        return "COLISION:%s" % ",".join(existentes)

    pre = env.get("precheck") or {}
    artefacto = pre.get("input_path", "") or pre.get("source", "") or ""
    if not artefacto:
        # Inferir de los results
        res0 = (env.get("results") or [{}])[0] if env.get("results") else {}
        artefacto = res0.get("artifact", "") or res0.get("source", "")
    target = "binary:%s" % os.path.basename(artefacto)

    op_id = S.registrar(
        c,
        {"request_id": "",
         "question": question or ("cfg/dataflow de %s" % artefacto),
         "capability": env.get("capability", ""),
         "scope": "binary",
         "target": target},
        {"operation": env.get("ejecucion", {}).get("operation", ""),
         "status": env.get("status"),
         "backend": env.get("backend", {}),
         "ejecucion": env.get("ejecucion"),
         "provenance": env.get("provenance"),
         "precheck": pre,
         "results": env.get("results") or []},
        duracion=(env.get("ejecucion") or {}).get("duration_s", 0))

    if _abierta_por_nosotros:
        c.close()
    return op_id
