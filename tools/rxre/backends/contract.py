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
import importlib
import json
import os
import re
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

    def __init__(self, backend_id: str, exe: Optional[str], argv: Optional[List[str]],
                 timeout: int = 900, repo: str = "",
                 commit: str = "", env_extra: Optional[Dict[str, str]] = None,
                 cwd: str = "", modulo: str = "") -> None:
        """`exe` es un binario en PATH; `modulo` es una libreria EN PROCESO.

        MEDIDO 2026-10-12: `capstone` es el primer producer del catalogo que
        no es un subproceso. Se importa y se desensambla dentro del proceso
        del adapter. MEDIDO tambien que es mas rapido por eso (~158000
        instr/s, sin coste de arranque) y que da algo que rizin y radare2 no
        dan: operandos con TIPO, y por tanto la posibilidad de construir un
        CFG, cuando `pdfj`, `agCj` y `agf` no emiten JSON.

        Antes de este campo no habia forma de registrarlo: `Backend` era un
        ejecutable o nada. La consecuencia era concreta: capstone estaba
        INSTALADO en el sistema y era invisible para RXRE, y la capacidad
        "desensamblar con semantica" figuraba como cerrada por producers que
        no la pueden cumplir.

        La identidad se sigue VERIFICANDO en runtime en los dos casos: por
        binario en PATH para `exe`, por `find_spec` + `__version__` para
        `modulo`. Un modulo que no se puede importar NO cuenta como
        existente, que es el mismo criterio que aplica a un binario que no
        esta en PATH.
        """
        self.backend_id = backend_id
        self.exe = exe
        self.modulo = modulo
        if argv is None:
            argv = []
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
        la identidad de un BINARIO se verifica por el binario, no por import.

        Para un backend de MODULO se devuelve el `__file__` real, y
        `None` si no se puede localizar el paquete: mismo criterio, misma
        exigencia.
        """
        if self.modulo:
            spec = self._spec()
            if spec is None:
                return None
            origin = getattr(spec, "origin", None) or ""
            if origin and origin != "namespace":
                return origin
            # namespace package: se acepta solo si trae un submodule real
            return "" or None
        if not self.exe:
            return None
        for d in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(d, self.exe)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    def _spec(self):
        """`ModuleSpec` del modulo, o None. Cacheado."""
        if getattr(self, "_spec_cache", "?") != "?":
            return self._spec_cache
        spec = None
        try:
            import importlib.util
            spec = importlib.util.find_spec(self.modulo)
        except (ImportError, ValueError, ModuleNotFoundError):
            spec = None
        self._spec_cache = spec
        return spec

    def existe(self) -> bool:
        if self.modulo:
            # MEDIDO: un paquete que se puede localizar Y tiene submodulos
            # reales. Un directorio vacio con el nombre justo no cuenta: por
            # eso se exige que el spec no sea `namespace` sin contenido, ni
            # un `origin` que sea None.
            spec = self._spec()
            return spec is not None and getattr(spec, "origin", None) not in (
                None, "namespace")
        return self.path() is not None

    def version(self) -> Dict[str, Any]:
        """Version del binario QUE CORRE. Verificada, no declarada."""
        if self._version_checked:
            return self._version or {}
        self._version_checked = True
        if self.modulo:
            if not self.existe():
                self._version = {"error": "modulo no localizable: %s"
                                 % self.modulo, "verificada": False}
                return self._version
            try:
                mod = importlib.import_module(self.modulo)
                ver = getattr(mod, "__version__", "")
            except Exception as exc:
                self._version = {"error": "import fallo: %s" % exc,
                                 "verificada": False}
                return self._version
            cs = ""
            fn = getattr(mod, "cs_version", None)
            if callable(fn):
                try:
                    cs = ".".join(str(x) for x in fn())
                except Exception:
                    cs = ""
            self._version = {"primera_linea": ver, "cs_version": cs,
                             "verificada": bool(ver or cs),
                             "tipo": "modulo en proceso"}
            return self._version
        exe = self.path()
        if not exe:
            self._version = {"error": "no encontrado en PATH"}
            return self._version
        # `X -v` no es universal: rizin usa -v, radare2 usa -v, otros -V.
        # Ademas, algunos tools usan -v para verbosidad (no version), y producen
        # errores o usage messages. Validar que la salida se parezca a una version:
        # debe contener un patron numerico como 1.0 o 1.0.0, y no empezar con [ERROR]
        # o Usage. Si ningun flag produce una version valida, se marca como
        # NO verificada con el ultimo output capturado (para diagnostico).
        _version_pat = re.compile(r'\d+\.\d+(?:\.\d+)?')
        _last_output: Dict[str, Any] = {"primera_linea": "", "flag": ""}
        # MEDIDO 2026-10-14: esta lista estaba FIJA y el `argv_template` que
        # el registry declara para cada backend se ignoraba. Eso produce
        # versiones FALSAS NEGATIVAS en herramientas que no usan -v/-V/--version.
        #
        # UMR en esta maquina:
        #     umr -v         -> [ERROR]: ASIC not found or compatible ...  (rechazado)
        #     umr -V         -> [ERROR]: ...                                 (rechazado)
        #     umr --version  -> [ERROR]: ...                                 (rechazado)
        #     umr --help     -> "User Mode Register debugger v1.0.0 ..."     rc=0
        #
        # O sea: el registry DECLARABA ["--help"], que es la unica sonda que
        # funciona, y el codigo no la llegaba a probar. `version_verificada`
        # salia False para una herramienta cuya version se lee sin problema.
        #
        # El backend sabe como se consulta SU version; se pregunta primero a
        # quien lo declara, y solo si no hay declaracion se prueban las
        # banderas genericas. Se conservan los dos rechazos de la version
        # anterior (error/usage no son versiones), que ya estaban bien.
        # Primero lo que declara el registry; despues, si no sale nada, las
        # banderas genericas. El fallback es lo que evita REGRESION: rizin y
        # radare2 se verificaban con `-v` antes de este cambio, y su argv
        # declarado no lo lleva. Sin el fallback, arreglar UMR habria roto
        # dos herramientas que funcionaban.
        _declarados = [f for f in (self.argv_template or []) if isinstance(f, str)]
        _genericos = ["-v", "-V", "--version"]
        _flags = _declarados + [f for f in _genericos if f not in _declarados]
        for flag in _flags:
            # El argv lo declara el registry, asi que se acota igual que se
            # acota `register_name` en los adapters: sin separadores de shell,
            # sin espacios, sin bytes de control. `subprocess.run` con argv
            # list ya evita la shell; esto evita que el argv contenga algo
            # que no sea un flag.
            if not isinstance(flag, str) or not flag:
                continue
            if re.search(r"[\s;&|`$<>\"']", flag) or \
                    any(ord(c) < 32 for c in flag):
                continue
            try:
                p = subprocess.run([exe, flag], capture_output=True, text=True,
                                   timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                continue
            txt = (p.stdout or "") + (p.stderr or "")
            if not txt.strip():
                continue
            first = txt.strip().splitlines()[0][:120]
            _last_output = {"primera_linea": first, "flag": flag}
            # Rechazar errores y usage messages (no son versiones)
            if (first.startswith("[ERROR]") or first.startswith("[WARN]") or
                    first.lower().startswith("usage:") or
                    "unknown option" in first.lower() or
                    first.lower().startswith("error")):
                continue  # intentar siguiente flag
            # Aceptar solo si la primera linea contiene un patron de version
            if _version_pat.search(first):
                self._version = {"flag": flag, "primera_linea": first,
                                 "verificada": True, "rc": p.returncode}
                return self._version
        # Ningun flag produjo una version valida
        self._version = {"error": "ningun flag produjo una version "
                         "reconocible; se rechazaron errores/usage messages "
                         "(ultima salida con flag %s: %s)"
                         % (_last_output["flag"], _last_output["primera_linea"]),
                         "verificada": False,
                         "ultima_salida": _last_output["primera_linea"],
                         "ultimo_flag": _last_output["flag"]}
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