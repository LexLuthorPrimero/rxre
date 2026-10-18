#!/usr/bin/env python3
"""RXRE-1635. `binary.xrefs` sobre rizin/radare2.

PRINCIPIO: solo dos backends pueden cumplir esta capacidad:
- `rizin` (`axtj` con `aaa`)
- `radare2` (`axtj` con `aaa`)

Capstone NO cubre xrefs: no hace analisis de funciones.
Por eso `binary.xrefs` requiere `nivel_analisis` para discriminar `aa` vs `aaa`.

## CORRECCIONES 2026-10-15 (RXRE-BMS-EXT-002-C)

El adapter original tenia TRES defectos medidos sobre el CLI:

1. ARTEFACTO COMO CONTENIDO, NO COMO PATH: hacia
       entrada = artefacto.encode() if isinstance(artefacto, str) else artefacto
   El CLI pasa un path string ('amdgui.ko'). `.encode()` convertia la CADENA
   DEL PATH a bytes, no el contenido del archivo. rizin analizaba `b'amdgui.ko'`
   (7 bytes de texto), no el ELF de 37MB. `binary.xrefs` nunca funciono por la
   CLI: devolvia `empty` con `ejecucion=null`, `precheck=null`.
   El test solo pasaba porque llamaba `X.xrefs(elf_bytes)` directamente.

2. SIN CONTRATO: no tenia `precheck` (os.path.isfile, sha256_de), no tenia
   `ejecucion` (argv, exit_status, duration_s), no tenia `provenance`.
   `nivel_analisis` viajaba como top-level, no en `ejecucion`, asi que
   `explain` no podia reconstruir el nivel usado.

3. OFFSET HARDCODEADO: `axtj @ 0x4000` y `inicio`/`longitud` eran parametros
   declarados en dispatch pero IGNORADOS.

EL ADAPTER AHORA:
- Acepta artefacto como PATH (str) o BYTES (backward compat con tests).
  Un path valido se pasa DIRECTAMENTE a rizin/r2 (como rz_cfg.py), con
  validacion isfile + hash sha256_de + ELF signature check.
- Produce el envelope completo: precheck/ejecucion/provenance/cadena_backend.
- `nivel_analisis` vive en `ejecucion` para trazabilidad.
- `inicio` controla el offset de `axtj`; default 0x4000 (preserva 74 xrefs
  en /bin/ls, verificado 2026-10-15).
"""
from __future__ import annotations

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
    XREF, Backend, limpiar, sha256_de, estado_firma,
)

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\r|[\x00\x07\x08]")

#: RX 550 hard boundary — never touch Intel iGPU 0000:00:02.0
ALLOWED_PCI = ("0000:01:00.0",)

#: BACKENDS SOLOS CON PRODUCER
_BACKENDS: Dict[str, Backend] = {
    "rizin": Backend(
        "rizin", "rizin", ["-q"], timeout=900,
        repo="https://github.com/rizinorg/rizin.git",
        commit="d14c3fac4126bc5fbe66e7f3d1660aeab22b01d8",
        env_extra={"RZ_NOPLUGINS": "1"},
    ),
    "radare2": Backend(
        "radare2", "r2", ["-q"], timeout=900,
        repo="https://github.com/radareorg/radare2.git",
        commit="008a7a6cd2e5acb8268f65f486760d080f3b107b",
        env_extra={"R2_NOPLUGINS": "1"},
    ),
}

#: Default address for `axtj @ <addr>`.
#: MEDIDO 2026-10-15: en rizin 0.7.4, `axtj` sin `@ addr` devuelve 0 (solo en
#: el seek actual). `axtj @ 0x4000` devuelve la lista COMPLETA (74 en /bin/ls).
#: Este es un quirk de rizin: cualquier `@ <addr>` lista todos los xrefs.
#: El 0x4000 se mantiene como default para preservar el comportamiento medido;
#: `inicio` lo reemplaza si se provee.
_DEFAULT_XREF_ADDR = "0x4000"


def _elf_header(artefacto: str) -> str:
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


def _sha256_bytes(data: bytes) -> str:
    """Hash de bytes (para backward compat con tests que pasan bytes)."""
    return hashlib.sha256(data).hexdigest()


def _argv(backend_id: str, exe: str, artefacto: str,
          cmd: str) -> List[str]:
    """El argv correcto para cada producer.

    rizin necesita -N (no init) y -e scr.color=0 para stdout parseable.
    r2 no usa -N pero si necesita -e scr.color=0.
    """
    if backend_id == "rizin":
        return [exe, "-q", "-N", "-e", "scr.color=0", "-c", cmd, artefacto]
    return [exe, "-q", "-e", "scr.color=0", "-c", cmd, artefacto]


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _xrefs_cmd(nivel_analisis: str, inicio: Optional[int]) -> Tuple[str, str]:
    """Construye el comando de rizin/r2 para xrefs.

    `inicio` controla el offset de `axtj`. Si es None, usa el default 0x4000
    (quirk de rizin: lista todos los xrefs con cualquier @ addr).

    Devuelve (cmd_str, salida_cmd).
    """
    addr = "0x%x" % inicio if inicio is not None else _DEFAULT_XREF_ADDR
    salida_cmd = "axtj"
    cmd = "%s; axtj @ %s" % (nivel_analisis, addr)
    return cmd, salida_cmd


def _resolve_artefacto(artefacto: Union[str, bytes], fixture_json: Optional[str],
                       pre: Dict[str, Any]) -> Tuple[str, str, str, bool, bool, Dict]:
    """Resuelve artefacto a un path de archivo ejecutable.

    Devuelve (tmp_path, artifact_ref, input_hash, es_path, input_es_elf, ident).
    Levanta BK_INVALID/BK_ERROR si el artefacto es invalido.

    Tres modos:
    1. File path string  -> usa directamente (como rz_cfg.py), valida ELF
    2. Bytes             -> temp file (backward compat con tests)
    3. fixture_json      -> parse hex, temp file, ejecuta rizin de verdad
    """
    b: Backend = _BACKENDS[pre.get("_backend_id", "rizin")]

    # --- MODO 1: File path string ---
    es_path = isinstance(artefacto, str) and os.path.isfile(artefacto)
    if es_path:
        pre["input_existe"] = True
        if estado_firma(artefacto) == "no_legible":
            raise _InvalidArtefacto(
                "la entrada EXISTE pero no es legible (permiso o E/S): %s" % artefacto,
                "no se pudo leer la firma: NO se sabe si es ELF; sin lectura "
                "no hay analisis de xrefs",
            )
        pre["input_hash"] = sha256_de(artefacto)
        elf_t = _elf_header(artefacto)
        pre["elf_tipo"] = elf_t
        if not elf_t:
            raise _InvalidArtefacto(
                "la entrada no es un ELF (firma distinta de \\x7fELF): %s" % artefacto,
                "no se invoco al producer: sin ELF no hay analisis de xrefs",
            )
        pre["input_es_elf"] = True
        return artefacto, artefacto, pre["input_hash"], True, True, b.identidad()

    # --- MODO 2/3: Bytes o fixture_json -> temp file ---
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
            raise _InvalidArtefacto(
                "no se pudo parsear fixture_json",
                "el fixture debe ser un JSON con hex del binario",
            )
    elif isinstance(artefacto, (bytes, bytearray)):
        entrada = bytes(artefacto)
    else:
        # String que no es un path existente
        raise _InvalidArtefacto(
            "el artefacto '%s' no es un path de archivo existente ni bytes"
            % str(artefacto)[:80],
            "para bytes: pasar como bytes, no como string",
        )

    pre["input_existe"] = True
    pre["input_hash"] = _sha256_bytes(entrada)[:16]
    pre["elf_tipo"] = "ET_BYTES"
    pre["input_es_elf"] = entrada[:4] == b"\x7fELF"

    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".bin", delete=False
    ) as tmp:
        tmp.write( entrada )
        tmp_path = tmp.name

    artifact_ref = "bytes:%s" % pre["input_hash"][:8]
    return tmp_path, artifact_ref, pre["input_hash"], False, pre["input_es_elf"], b.identidad()


class _InvalidArtefacto(Exception):
    """Raised when artefacto validation fails before execution."""
    def __init__(self, msg: str, limitation: str):
        self.msg = msg
        self.limitation = limitation
        super().__init__(msg)


def _ejecutar_rizin(artefacto_path: str, cmd_str: str,
                    backend_id: str, b: Backend,
                    timeout: int, pre: Dict) -> Tuple[int, str, str, float, bool, List]:
    """Ejecuta el comando de rizin/r2 sobre un path de archivo.

    Devuelve (rc, stdout, stderr, duration_s, timedout, argv).
    """
    argv = _argv(backend_id, b.path(), artefacto_path, cmd_str)
    pre["argv"] = argv
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
    return rc, so, se, dur, timedout, argv


def xrefs(artefacto: Union[str, bytes], backend_id: str = "rizin",
          nivel_analisis: str = "aaa", timeout: int = 900,
          inicio: Optional[int] = None, longitud: Optional[int] = None,
          fixture_json: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """`binary.xrefs`: referencias cruzadas (DATA, CALL, JUMP).

    PRE-EXECUTION CONTRACT CHECK (§26):
    - artefacto: path de archivo (str) o bytes (backward compat con tests)
    - backend_id en {_BACKENDS}
    - nivel_analisis en {"aa", "aaa"}
    - fixture_json: string JSON con hex del binario (para testing CI)

    Devuelve SIEMPRE: status, precheck, ejecucion, backend, results, provenance.
    Estados: ok/empty/error (siguiendo el contrato de backends.contract).
    """
    # --- VALIDAR backend_id ---
    if backend_id not in _BACKENDS:
        return {
            "status": BK_ERROR, "precheck": {},
            "limitations": [
                "el backend %s no tiene producer para binary.xrefs. "
                "Backends: %s" % (backend_id, ", ".join(sorted(_BACKENDS)))],
            "results": [], "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: backend invalido",
            "message": "Backend '%s' no tiene producer para binary.xrefs" % backend_id,
        }

    # --- VALIDAR nivel_analisis ---
    if nivel_analisis not in ("aa", "aaa"):
        return {
            "status": BK_ERROR, "precheck": {},
            "limitations": [
                "nivel_analisis debe ser 'aa' o 'aaa', no '%s'" % nivel_analisis],
            "results": [], "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: parametro invalido",
            "message": "nivel_analisis debe ser 'aa' o 'aaa', no '%s'" % nivel_analisis,
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
        "salida_cmd": "axtj",
        "inicio": inicio,
        "longitud": longitud,
        "usa_fixture": bool(fixture_json),
        "_backend_id": backend_id,
        "ok": False,
    }

    # --- RESOLVER ARTEFACTO ---
    try:
        tmp_path, artifact_ref, input_hash_str, es_path, input_es_elf, ident = \
            _resolve_artefacto(artefacto, fixture_json, pre)
        # RXRE-FUEGO-001: `_resolve_artefacto` devuelve `es_path=True` cuando
        # `tmp_path` es el archivo ORIGINAL del usuario, y `False` cuando es un
        # temporal creado aqui. Para `_limpiar_tmp` la polaridad es la OPUESTA:
        # se borra cuando RXRE es el dueno. Antes se pasaba `es_path` tal cual,
        # con lo que `binary.xrefs` destruia el artefacto original y dejaba
        # huerfano su propio temporal.
        rxre_creo_tmp = not es_path
    except _InvalidArtefacto as exc:
        pre.pop("_backend_id", None)
        return {
            "status": BK_INVALID, "precheck": pre,
            "limitations": [exc.msg, exc.limitation],
            "results": [], "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: artefacto invalido",
            "message": exc.msg,
        }

    pre.pop("_backend_id", None)
    ident_backend = ident.get("backend_id", backend_id)
    if fixture_json:
        ident_backend = "fixture"
        ident = {"backend_id": "fixture", "tool_version": "",
                 "version_verificada": False,
                 "backend_version_status": "UNVERIFIED"}

    # --- VERIFICAR BACKEND EXISTE ---
    if not pre["backend_existe"]:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_BLOCKED, "precheck": pre,
            "limitations": ["el backend %s no esta en PATH" % backend_id],
            "results": [], "ejecucion": None,
            "provenance": "PROVENANCE_INCOMPLETE: backend missing",
        }

    # --- EJECUCION ---
    cmd_str, salida_cmd = _xrefs_cmd(nivel_analisis, inicio)
    rc, so, se, dur, timedout, argv = _ejecutar_rizin(
        tmp_path, cmd_str, backend_id, b, timeout, pre
    )

    # --- LIMPIEZA DE OUTPUT ---
    limpio, n_quit = limpiar(so)
    texto = ANSI.sub("", limpio)

    ejec = {
        "backend_id": ident_backend,
        "operation": "binary.xrefs",
        "command_or_api": "rizin/r2 -q -N -e scr.color=0 -c \"%s\" <artefacto>" % cmd_str,
        "argv": argv,
        "exit_status": rc,
        "raw_output_len": len(so),
        "stderr": se.strip()[:400],
        "limpieza": {"aplicada": n_quit > 0, "caracteres_quitados": n_quit},
        "timeout": timedout,
        "duration_s": dur,
        "nivel_analisis": nivel_analisis,         # ← NOW in ejecucion for traceability
        "inicio": inicio,
        "longitud": longitud,
        "salida_cmd": salida_cmd,
    }

    if timedout:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
            "backend": ident_backend,
            "limitations": ["timeout a los %ds" % timeout],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: timeout",
        }

    if rc not in (0, None):
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
            "backend": ident_backend,
            "limitations": [
                "el producer salio rc=%s: %s"
                % (rc, (se.strip() or so.strip())[:300])],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: producer error",
            "message": "Error en %s: %s" % (backend_id, (se.strip() or so.strip())[:200]),
        }

    # --- PARSEAR JSON ---
    inicio_json = texto.find("[")
    if inicio_json < 0:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
            "backend": ident_backend,
            "limitations": ["la salida de axtj no contiene JSON. stdout: %s" % texto[:200]],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: no JSON",
            "message": "Salida no JSON de axtj: %s" % texto[:100],
        }

    try:
        data = json.loads(texto[inicio_json:])
    except ValueError as exc:
        _limpiar_tmp(tmp_path, rxre_creo_tmp)
        return {
            "status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
            "backend": ident_backend,
            "limitations": ["JSON mal formado de axtj: %s" % exc],
            "results": [],
            "provenance": "PROVENANCE_INCOMPLETE: JSON invalido",
            "message": "JSON mal formado de axtj: %s" % exc,
        }

    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        data = []

    xrefs_count = len(data)
    status = BK_EMPTY if xrefs_count == 0 else BK_OK
    pre["ok"] = True

    # --- CONSTRUIR RESULTADOS ---
    results = []
    for i, xref in enumerate(data):
        xref_str = json.dumps(xref, sort_keys=True, default=str)
        result_id = "res_xref_" + \
            hashlib.sha256(
                ("%s|%s|%d|%s" % (artifact_ref, backend_id, i, xref_str)).encode()
            ).hexdigest()[:16]
        result = {
            "result_id": result_id,
            "type": XREF,
            "value": {**xref, "nodos": xrefs_count},  # nodos para ALMA/ETER
            "source": artifact_ref,
            "location": {
                "file": os.path.basename(tmp_path),
                "offset": inicio,
            },
            "scope": "binary",
            "tool": backend_id,
            "tool_version": ident.get("tool_version", ""),
            "input": {"path": artifact_ref, "sha256": input_hash_str},
            "timestamp": _ts(),
            "artifact": artifact_ref,
            "artifact_hash": input_hash_str,
            "status": "observed",
            "raw": {
                "n_coincidencias": xrefs_count,  # para ALMA/ETER linkage
                "nodos": xrefs_count,
            },
            "limitations": [
                "RAW_BINARY: lo que rizin/r2 declara, no semantica verificada.",
                "nivel_analisis '%s': un nivel insuficiente (aa) puede no "
                "descubrir todas las referencias." % nivel_analisis,
            ],
        }
        results.append(result)

    _limpiar_tmp(tmp_path, rxre_creo_tmp)

    limitations = [
        "RAW_BINARY: lo que rizin/r2 declara, no semantica verificada de los xref.",
        "nivel_analisis '%s': 'aa' puede no descubrir todas las referencias; "
        "comparar con 'aaa' para binarios complejos." % nivel_analisis,
        "binary.xrefs NO es callgraph: captura referencias directas (DATA/CALL/"
        "JUMP), no relaciones interfuncionales.",
        "EL OFFSET DE QUERY: en rizin 0.7.4, `axtj @ <addr>` lista todos los "
        "xrefs (quirk). El offset default es 0x4000; `inicio` lo reemplaza.",
    ]

    return {
        "status": status,
        "precheck": pre,
        "ejecucion": ejec,
        "backend": ident_backend,           # string, para backward compat
        "backend_identity": ident,          # dict completo
        "results": results,
        "xrefs": xrefs_count,
        "nivel_analisis": nivel_analisis,   # backward compat con tests
        "metadata": {
            "limites": {"inicio": inicio, "longitud": longitud},
            "backend_version": backend_id,
            "nota": "Adapter rz_xrefs.py (2026-10-15): binary.xrefs via "
                    "axtj, con precheck/ejecucion/provenance. artefacto "
                    "acepta path de archivo o bytes; inicio controla el offset.",
        },
        "limitations": limitations,
        "provenance": {
            "estado": "completa",
            "input_hash": input_hash_str,
            "backend": ident_backend,
            "command_or_api": ejec.get("command_or_api", ""),
            "transformacion": "rizin/r2 -c 'aaa; axtj @ <addr>' -> limpieza ANSI "
                              "-> json.loads -> extraccion de resultados",
            "normalizador": "backends.adapters.rz_xrefs.xrefs",
            "tool_version": ident.get("tool_version", ""),
            "repository_commit": ident.get("repository_commit", ""),
            "provenance_estado": "completa",
        },
        "cadena_backend": _cadena_backend_local(
            ejec, ident, tmp_path, input_hash_str),
    }


def _limpiar_tmp(tmp_path: str, borra: bool) -> None:
    """Borra `tmp_path` SOLO si `borra` es True.

    CONTRATO (RXRE-FUEGO-001):
        borra=True  -> RXRE creo ese fichero con tempfile; se elimina.
        borra=False -> `tmp_path` es un archivo del usuario; NO SE TOCA.

    `borra` NO significa "existe" ni "es temporal": significa "RXRE es el
    dueno del fichero". Pasarla con la polaridad contraria destruye el
    artefacto del usuario.
    """
    if borra:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _cadena_backend_local(ejec: Dict[str, Any], ident: Dict[str, Any],
                          artefacto: str, input_hash: str) -> Dict[str, Any]:
    """La cadena del backend, extraible del envelope.

    B3 / §9: result_id -> operation_id -> backend -> version -> commit
    -> input -> input_hash -> argv -> raw -> transformacion -> normalized
    """
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
        "transformacion": "rizin/r2 -c 'aaa; axtj @ <addr>' -> limpieza ANSI "
                          "-> json.loads -> extraccion de resultados",
        "normalizador": "backends.adapters.rz_xrefs.xrefs",
        "limitaciones": ejec.get("limitations", []),
        "provenance_estado": "completa",
        "chain": ["result_id", "operation_id", "backend", "tool_version",
                  "repository_commit", "input_artifact", "input_hash",
                  "command_or_api", "argv", "raw_output",
                  "transformacion", "normalizador", "normalized_result"],
    }


def target_binario(artefacto: str, input_hash: str = "") -> str:
    """El `target` de una operacion binaria. B3: target es el ARTEFACTO."""
    base = os.path.basename(artefacto or "")
    if input_hash:
        return "binary:%s@%s" % (base, input_hash[:16])
    return "binary:%s" % base


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
    target = "binary:%s" % (os.path.basename(artefacto) or "xrefs")

    op_id = S.registrar(
        c,
        {"request_id": "",
         "question": question or ("xrefs de %s" % artefacto),
         "capability": "binary.xrefs",
         "scope": "binary",
         "target": target},
        {"operation": "binary.xrefs",
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
