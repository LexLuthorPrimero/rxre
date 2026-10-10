#!/usr/bin/env python3
"""RXRE-004. Contrato de backend. Lo que un backend DEBE poder responder.

POR QUE UN CONTRATO Y NO UNA INTERFAZ COMUN A TODOS.

rizin y radare2 son CLIs con verbos propios: `rz-bin -Ij` y `rabin2 -Ij` no son
lo mismo, y `rizin -qc 'aa; aflj'` no tiene equivalente exacto en r2. Un
contrato comun que los obligue a parecerse los obliga a perder lo que ya saben
hacer.

Por eso el contrato no dice COMO se llama. Dice QUE tiene que poder responder:

    dado un artefacto de entrada y una operacion,
    ¿puede el backend ejecutarla, y puede RXRE saber que hizo?

Y separa cuatro cosas que un solo campo `output` confunde:

    raw_output       lo que el backend escupio, byte a byte
    normalized_output lo que RXRE entendio
    provenance       quien, con que version, con que commit, sobre que hash
    status           si se pudo, si no, y por que no

Y el `status` tiene un valor que los estados de RXRE-001/002/003 no tienen:
`unsupported`. `empty` quiere decir "se ejecuto y no hay nada". Un backend que no
sabe decompilar no esta vacio: no sabe.

    unsupported != empty

## LOS ESTADOS Y POR QUE SON DISTINTOS

    ok           se ejecuto y produjo salida parseable
    empty        se ejecuto y no produjo nada; NO es ausencia del objeto
    unsupported  el backend no tiene esa capacidad, con nombre y version
    blocked      se intento y una precondicion fallo (backend, permisos, build)
    invalid      la entrada no es valida para este backend
    error        fallo del backend

Colapsar `unsupported` a `empty` es el fallo que §13 de RXRE-003 prohibe y que
este contrato vuelve estructural: una IA que pregunte por decompilacion
recibiria "vacio" y concluiria que el binario no tiene.

`unsupported` LLEVA el motivo y el verbo que faltaba, para que la IA pueda
intentar por otro camino en vez de rendirse.

## PROVENANCE Y LA REGLA QUE MAS DUELE

Un backend entra en RXRE solo si su version es VERIFICABLE en runtime. MEDIDO:
`import angr` funciona dentro del arbol del proyecto y `angr.__file__` es
`None` -- es el directorio clonado acting como namespace package. Fuera, no
importa. Un backend cuya identidad no se puede comprobar no puede entrar en
provenance: se registraria un `backend_version` que nadie puede confirmar.

    backend verificable en runtime = requisito, no buena practica

Y `repository_commit` es la IDENTIFICACION DEL CODIGO FUENTE, distinto de
`tool_version` que es la del BINARIO QUE CORRE. Con rizin hay los dos y NO
coinciden:

    repo     d14c3fac4126  (v0.10.0-dev, branch dev)
    runtime  0.7.4         (Fedora 43)

Es la misma clase de confusion que `CHANGELOG` frente a `git describe`. Un
envelope que solo lleve `tool_version` pierde el commit, y un envelope que solo
lleve `commit` no dice que version se ejecuto.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

CONTRACT_VERSION = "1.0"

# --- estados de backend. Distintos de los de RXRE-001 a proposito ---------
BK_OK = "ok"
BK_EMPTY = "empty"
BK_UNSUPPORTED = "unsupported"
BK_BLOCKED = "blocked"
BK_INVALID = "invalid_input"
BK_ERROR = "error"
BACKEND_STATES = (BK_OK, BK_EMPTY, BK_UNSUPPORTED, BK_BLOCKED, BK_INVALID, BK_ERROR)

#: rc de salida por estado. Deliberadamente MAS que cuatro: `unsupported` e
#: `invalid` no existian en RXRE-001 porque alli no habia backends.
BACKEND_RC = {
    BK_OK: 0, BK_EMPTY: 0, BK_UNSUPPORTED: 4,
    BK_BLOCKED: 2, BK_INVALID: 5, BK_ERROR: 1,
}

# --- Representaciones epistemicas. §10 -------------------------------------
# El orden NO es decorativo: `type` de un resultado dice en que peldano esta.
# Y lo que NO se permite es guardar un peldano alto como si fuera bajo.
RAW_BINARY = "raw_binary"
DISASSEMBLY = "disassembly"
FUNCTION_CANDIDATE = "function_candidate"
BASIC_BLOCK = "basic_block"
CONTROL_FLOW = "control_flow"
CALL_GRAPH = "call_graph"
XREF = "xref"
DATA_FLOW = "data_flow"
DECOMPILATION = "decompilation"
SEMANTIC_HYPOTHESIS = "semantic_hypothesis"
VALIDATED_SEMANTICS = "validated_semantics"

#: De menor a mayor confianza. Un resultado NO puede declararse de un nivel
#: superior al que su producer demuestra.
ORDEN_CONFIANZA = [
    RAW_BINARY, DISASSEMBLY, FUNCTION_CANDIDATE, BASIC_BLOCK,
    CONTROL_FLOW, CALL_GRAPH, XREF, DATA_FLOW, DECOMPILATION,
    SEMANTIC_HYPOTHESIS, VALIDATED_SEMANTICS,
]


def nivel(tipo: str) -> int:
    try:
        return ORDEN_CONFIANZA.index(tipo)
    except ValueError:
        return -1


def puede_declarar(producer_tipo: str, consumidor_tipo: str) -> bool:
    """¿El productor demuestra lo que el consumidor afirma?

    Es la regla que impide que una DECOMPILACION se guarde como
    VALIDATED_SEMANTICS. Responde `False` casi siempre, y por eso es util.

        un decompilador no demuestra la semantica del hardware
    """
    return nivel(producer_tipo) >= nivel(consumidor_tipo)


def sha256_de(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def sha256_texto(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Backend:
    """Un backend ejecutable, con su identidad verificada en runtime."""

    def __init__(self, backend_id: str, exe: str, argv: List[str],
                 timeout: int = 900, repo: str = "",
                 commit: str = "", env_extra: Optional[Dict[str, str]] = None,
                 cwd: str = "") -> None:
        self.backend_id = backend_id
        self.exe = exe
        self.argv_template = list(argv)
        self.timeout = timeout
        self.repo = repo
        self.commit = commit
        self.env_extra = dict(env_extra or {})
        self.cwd = cwd
        self._version: Optional[str] = None
        self._version_checked = False

    # --- identidad -------------------------------------------------------
    def path(self) -> Optional[str]:
        """Ruta absoluta del ejecutable, o None si no esta.

        MEDIDO: `angr` esta "importable" dentro del arbol porque el directorio
        clonado se llama `angr` y Python lo toma como namespace package. Por eso
        la identidad se verifica por BINARIO, no por import.
        """
        for d in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(d, self.exe)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    def existe(self) -> bool:
        return self.path() is not None

    def version(self) -> Dict[str, Any]:
        """Version del binario QUE CORRE. Verificada, no declarada."""
        if self._version_checked:
            return self._version or {}
        self._version_checked = True
        exe = self.path()
        if not exe:
            self._version = {"error": "no encontrado en PATH"}
            return self._version
        # `X -v` no es universal: rizin usa -v, radare2 usa -v, otros -V.
        for flag in ("-v", "-V", "--version"):
            try:
                p = subprocess.run([exe, flag], capture_output=True, text=True,
                                   timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                continue
            txt = (p.stdout or "") + (p.stderr or "")
            if txt.strip():
                self._version = {"flag": flag, "primera_linea": txt.strip()
                                 .splitlines()[0][:120], "verificada": True}
                return self._version
        self._version = {"error": "ningun flag de version respondio",
                         "verificada": False}
        return self._version

    def identidad(self) -> Dict[str, Any]:
        """Todo lo que RXRE puede AFIRMAR sobre este backend. Nada mas.

        `backend_version_status` no es decorativo: es el campo que impide
        declarar una version sin comprobar. Si la sonda no respondio, el
        estado es `UNVERIFIED` y `tool_version` va vacio. Un envelope que
        dijera `VERIFIED` con la version del repo seria el mismo defecto que
        F8 (un `exit 0` con una salida que no es la pedida): apariencia de
        exito sin contenido.

            UNVERIFIED con version vacia > VERIFIED con version inventada
        """
        v = self.version()
        verificada = bool(v.get("verificada"))
        return {
            "backend_id": self.backend_id,
            "exe": self.exe,
            "path": self.path(),
            "existe": self.existe(),
            "tool_version": v.get("primera_linea", ""),
            "version_verificada": verificada,
            "backend_version_status": "VERIFIED" if verificada else "UNVERIFIED",
            "version_flag": v.get("flag", ""),
            "version_error": v.get("error", ""),
            "repository": self.repo,
            "repository_commit": self.commit,
        }

    # --- ejecucion -------------------------------------------------------
    def ejecutar(self, args: List[str], timeout: Optional[int] = None) -> Dict[str, Any]:
        """Ejecuta y devuelve SIEMPRE los cuatro canales del contrato.

        MEDIDO: rizin y r2 meten ANSI y `\\r` en stdout. Sin `-e scr.color=0` el
        JSON no parsea. Por eso `limpieza` es un campo declarado: el normalizador
        tiene que saber si limpio, y si no, por que no.

            una salida con secuencias de control NO es una salida invalida;
            es una salida que hay que limpiar, y decirlo
        """
        exe = self.path()
        if not exe:
            return {"status": BK_BLOCKED, "raw_output": "", "stdout": "",
                    "stderr": "backend no encontrado", "argv": [], "rc": None,
                    "limpieza": {"aplicada": False,
                                 "motivo": "sin ejecutable"}}
        argv = [exe] + self.argv_template + list(args)
        env = dict(os.environ)
        env.update(self.env_extra)
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout or self.timeout, env=env,
                               cwd=self.cwd or None)
        except subprocess.TimeoutExpired:
            return {"status": BK_BLOCKED, "raw_output": "", "stdout": "",
                    "stderr": "timeout a los %ds" % (timeout or self.timeout),
                    "argv": argv, "rc": None,
                    "limpieza": {"aplicada": False, "motivo": "timeout"}}
        except OSError as e:
            return {"status": BK_ERROR, "raw_output": "", "stdout": "",
                    "stderr": str(e), "argv": argv, "rc": None,
                    "limpieza": {"aplicada": False, "motivo": str(e)}}
        limpio, n_quitados = limpiar(p.stdout or "")
        return {"status": BK_OK if p.returncode == 0 else BK_ERROR,
                "raw_output": p.stdout or "", "stdout": limpio,
                "stderr": p.stderr or "", "argv": argv, "rc": p.returncode,
                "limpieza": {"aplicada": n_quitados > 0,
                             "caracteres_quitados": n_quitados}}


def limpiar(s: str):
    """Quita secuencias de control. MEDIDO: son la razon de que fallen JSON.

    Devuelve el numero de caracteres quitados, para que la provenance diga si
    la limpieza fue real o no. Una limpieza que no limpia nada debe notarse.
    """
    import re
    # CSI (colores, cursor) + CR + backspace + BEL
    pat = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\r|[\x00\x07\x08]")
    limpio, n = pat.subn("", s)
    return limpio, n


def parsear_json(s: str):
    """JSON o None. Nunca inventa."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except ValueError:
        for i, ch in enumerate(s):
            if ch in "{[":
                try:
                    return json.loads(s[i:])
                except ValueError:
                    continue
    return None


def contrato_de_backend(b: Backend) -> Dict[str, Any]:
    """El contrato como documento, para `rxre backends`."""
    return {
        "contract_version": CONTRACT_VERSION,
        "estados": list(BACKEND_STATES),
        "rc_por_estado": BACKEND_RC,
        "representaciones": list(ORDEN_CONFIANZA),
        "campos": [
            "backend_id", "tool_version", "version_verificada",
            "repository", "repository_commit", "input_artifact",
            "input_hash", "architecture", "format", "operation",
            "command_or_api", "exit_status", "raw_output",
            "normalized_output", "limpieza", "limitations",
        ],
        "regla_de_estados": "unsupported != empty: un backend que no sabe "
                            "una capacidad NO esta vacio",
        "regla_de_confianza": "un resultado no puede declararse de un nivel "
                              "superior al que su producer demuestra",
        "regla_de_identidad": "un backend entra solo si su version es "
                              "verificable en runtime; el commit del repo es "
                              "dato distinto de la version del binario",
    }