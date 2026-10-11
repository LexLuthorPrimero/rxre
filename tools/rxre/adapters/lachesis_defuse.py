#!/usr/bin/env python3
"""Adaptador de flujo de datos interprocedural: Lachesis, por CLI.

POR QUE UN ADAPTADOR Y NO UN MOTOR PROPIO.

RXRE no tiene motor de flujo de datos (def-use interprocedural): es el
hueco declarado en la auditoria RXRE-1629 (§4, fila 6). Lachesis 0.5.3
si lo tiene (kernel nativo `reaching_def`, `value-history` con cadena de
propietario). Este modulo NO implementa un segundo motor: ejecuta
Lachesis como PROCESO EXTERNO por su CLI, valida su salida contra el
esquema medido de la version instalada, y traduce lo que dice al
contrato de RXRE. Lo que Lachesis no sabe, este modulo no lo inventa.

LAS TRES CAPAS, Y POR QUE NO SE PUEDEN FUNDIR.

    identity   reg_resolve.py (NATIVO de RXRE). Sabe que un #define
               mm* es un registro, en que BLOQUE de IP esta, a que
               DIRECCION (indice dword) apunta, y con que arista de
               include lo consume el codigo.
    provider   lachesis (EXTERNO). Sabe donde estan las entidades y
               como fluyen los valores entre ellas. No sabe que un
               registro es un registro: para el, `#define mmATC_L2_CNTL
               0x0640` es una macro opaca.
    dataflow   lachesis `value-history` sobre el nodo ya localizado.

La identidad de un registro NO se resuelve por nombre: se resuelve por
(bloque de IP, direccion), con la procedencia de cada definicion. El
proveedor reporta 9 macros homonimas de `mmATC_L2_CNTL` SIN agrupar;
este adaptador las agrupa POR LA IDENTIDAD NATIVA (una tabla de tres
identidades con tres direcciones distintas), nunca al reves.

EL MODELO DE ERRORES, Y LA REGLA QUE NO SE NEGOCIA.

    un fallo del proveedor NUNCA se convierte en "no hay flujo"

    rc != 0 del proveedor          -> error (salida 1), con su stderr
    JSON ilegible o esquema roto  -> error (salida 1), sin inventar
    precondicion no cumplida      -> blocked (salida 2)
    el proveedor corrio y no encontro -> empty, CON la causa
    el proveedor no puede contestar -> NOT_DETERMINED, CON la causa

`empty` y `NOT_DETERMINED` no son ausencia. Lachesis no tiene nocion
de universo exhaustivo: su `not-found` significa "no esta en el indice
que yo construi", y eso se dice, no se traduce a `PROVEN_ABSENT`. La
unica ausencia que este adaptador emite es la NATIVA
(`PROVEN_ABSENT_EN_ASIC_REG` de reg_resolve, con su busqueda
exhaustiva sobre asic_reg como evidencia), y se emite con su
productor identificado.

SALIDA. El contrato de este script es su propio JSON (capas, resultados,
limites, herramientas usadas). El envelope de RXRE lo construye el
handler (`commands/handlers.py::defuse`), como con todas las
capacidades: el adaptador habla su formato, el handler lo envuelve.

CODIGOS DE SALIDA (los del VEREDICTO, no los del proveedor):

    0   ok o empty (se ejecuto; empty lleva la causa en limitations)
    1   error (el proveedor o la capa nativa fallo, o el esquema
          cambió; nada se interpreta)
    2   blocked (precondicion no cumplida: no hay grafo, no hay
          corpus, no hay lachesis, falta el kernel)

LICENCIA. Lachesis es AGPL-3.0. Este adaptador lo invoca como proceso
independiente por su CLI: no vendoriza, no enlaza, no copia codigo.
La interpretacion de AGPL-3.0 sobre esta integracion queda pendiente de
revision legal antes de cualquier redistribucion del conjunto (§7 de
RXRE-1629).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

# --- contrato de este adaptador ----------------------------------------

TOOL = "lachesis_defuse.py"
VERSION = "1.0.0"
OPERATION = "defuse"

#: Estados epistemicos de un RESULTADO (el vocabulario de RXRE). El
#: envelope tiene los estados OPERATIVOS (ok/empty/blocked/error); el
#: estado epistemico viaja dentro de cada resultado, como el
#: `verdict` de reg_resolve.
ESTADOS = ("PROVEN", "PARTIAL", "NOT_DETERMINED",
           "PROVEN_ABSENT_EN_ASIC_REG")

INTENTOS = ("symbol", "def-use", "value-history", "bit-semantics")

#: Preguntas del proveedor que este adaptador usa, con el esquema que
#: se MIDIO de lachesis 0.5.3 (no el que dice la documentacion).
PREGUNTAS_PROVEEDOR = ("find-entity", "function", "value-history")

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
REG_RESOLVE = os.path.join(TOOLS, "reg_resolve.py")

#: Raiz de fuentes por defecto para la capa nativa. MEDIDO: `working`
#: y `kernelbuild` tienen los 476 headers de asic_reg; `kernelbuild`
#: es la raiz verificada para identidad de registro en RXRE-1629.
KERNEL_DEFECTO = os.path.join(ROOT, "RESEARCH", "kernelbuild", "linux-7.1.3")

GFX_DEFECTO = "gfx_8_0"

#: Presupuesto del pool de buffers de Kuzu. MEDIDO (RXRE-1629 §5): las
#: consultas sobre el grafo acotado necesitan un pool explicito; 512 MiB
#: bastan para el grafo de corpus-small; el grafo completo (128 k nodos)
#: no materializa NI con 2 GiB en este host.
KUZU_BPS_DEFECTO = "536870912"


# --- excepciones: una clase por forma de fallar -----------------------

class ErrorDeContrato(Exception):
    """Precondicion no cumplida. Es un `blocked`, no un fallo."""


class ErrorDeEsquema(Exception):
    """El proveedor cambio su esquema. Lachesis es pre-1.0 y autodeclara
    que el esquema puede cambiar entre versiones menores: un cambio de
    esquema es un ERROR ruidoso, nunca una degradacion silenciosa."""


class ErrorDeProveedor(Exception):
    """El proveedor fallo (rc != 0). Su stderr es la evidencia.

    `rc` es `Optional`: el timeout no tiene codigo de salida,
    y ese caso viaja por la misma clase para que el consumidor
    no necesite dos ramas de error de transporte.
    """

    def __init__(self, herramienta: str, rc: Optional[int],
                 detalle: str) -> None:
        super().__init__("%s rc=%s: %s"
                         % (herramienta,
                            rc if rc is not None else "?",
                            detalle))
        self.herramienta = herramienta
        self.rc = rc
        self.detalle = detalle


class ErrorDeProveedorTimeout(ErrorDeProveedor):
    """El proveedor no termino en el presupuesto."""

    def __init__(self, herramienta: str, timeout: int) -> None:
        super().__init__(herramienta, None,
                         "timeout a los %ds" % timeout)
        self.timeout = timeout


class ErrorNativo(Exception):
    """La capa nativa (reg_resolve) fallo. Un fallo nativo NO se
    convierte en "no es un registro": eso inventaria una ausencia con
    evidencia insuficiente."""

    def __init__(self, herramienta: str, detalle: str) -> None:
        super().__init__("%s: %s" % (herramienta, detalle))
        self.herramienta = herramienta
        self.detalle = detalle


# --- validadores de esquema (contra la salida MEDIDA de 0.5.3) --------
#
# Cada validador devuelve una lista de errores; vacia = conforme. Se
# validan TIPO y PRESENCIA de las claves que este adaptador traduce.
# No se valida el significado: interpretar es trabajo de la traduccion,
# no del validador.

def _es(d: Any, t: type, camino: str, errs: List[str]) -> bool:
    if not isinstance(d, t):
        errs.append("%s: se esperaba %s, se recibio %s"
                    % (camino, t.__name__, type(d).__name__))
        return False
    return True


def _validar_ubicacion(loc: Any, camino: str, errs: List[str]) -> None:
    if not _es(loc, dict, camino, errs):
        return
    for k, t in (("file", str), ("start_line", int),
                 ("start_column", int), ("end_line", int),
                 ("end_column", int)):
        if k not in loc:
            errs.append("%s.location: falta %s" % (camino, k))
        elif not isinstance(loc[k], t):
            errs.append("%s.location.%s: se esperaba %s, se recibio %s"
                        % (camino, k, t.__name__, type(loc[k]).__name__))


def _validar_match(m: Any, camino: str, errs: List[str]) -> None:
    if not _es(m, dict, camino, errs):
        return
    for k in ("id", "kind", "label"):
        if k not in m:
            errs.append("%s: falta %s" % (camino, k))
        elif not isinstance(m[k], str):
            errs.append("%s.%s: se esperaba str, se recibio %s"
                        % (camino, k, type(m[k]).__name__))
    if "location" not in m:
        errs.append("%s: falta location" % camino)
    else:
        _validar_ubicacion(m["location"], camino, errs)
    # Campos de procedencia. lachesis 0.5.3 los emite SIEMPRE
    # (`origin: compiler`, `confidence: exact|low|...`). El frontend
    # autodeclara que su esquema puede cambiar entre menores: si estos
    # campos desaparecen, el adaptador DEBE fallar ruidoso, porque la
    # procedencia es lo que el consumidor lee para no alucinar.
    for k in ("origin", "confidence"):
        if k not in m:
            errs.append("%s: falta %s (campo de procedencia)" % (camino, k))
        elif not isinstance(m[k], str):
            errs.append("%s.%s: se esperaba str, se recibio %s"
                        % (camino, k, type(m[k]).__name__))
    loc = m.get("locator")
    if not _es(loc, dict, "%s.locator" % camino, errs):
        return
    for k in ("tier", "artifact", "kind", "label"):
        if k not in loc:
            errs.append("%s.locator: falta %s" % (camino, k))
    oc = loc.get("owner_chain")
    if not _es(oc, list, "%s.locator.owner_chain" % camino, errs):
        return
    for i, eslabon in enumerate(oc):
        if not isinstance(eslabon, dict) or "kind" not in eslabon:
            errs.append("%s.locator.owner_chain[%d]: eslabon sin 'kind'"
                        % (camino, i))


def _validar_find_entity(doc: Any) -> List[str]:
    errs: List[str] = []
    if not _es(doc, dict, "raiz", errs):
        return errs
    if "schema_version" not in doc:
        errs.append("raiz: falta schema_version")
    if doc.get("query") != "find-entity":
        errs.append("raiz.query: se esperaba 'find-entity', se recibio %r"
                    % doc.get("query"))
    if "status" not in doc:
        errs.append("raiz: falta status")
    elif doc["status"] not in ("exact", "ambiguous", "not-found"):
        errs.append("raiz.status: valor %r fuera de "
                    "{exact, ambiguous, not-found}" % doc["status"])
    ms = doc.get("matches")
    if not _es(ms, list, "raiz.matches", errs):
        return errs
    for i, m in enumerate(ms):
        _validar_match(m, "matches[%d]" % i, errs)
    return errs


def _validar_function(doc: Any) -> List[str]:
    errs: List[str] = []
    if not _es(doc, dict, "raiz", errs):
        return errs
    if doc.get("query") != "function":
        errs.append("raiz.query: se esperaba 'function', se recibio %r"
                    % doc.get("query"))
    _validar_match(doc.get("focus"), "focus", errs)
    sm = doc.get("summary")
    if not _es(sm, dict, "summary", errs):
        return errs
    for k in ("parameter_count", "call_count", "body_node_count",
              "effect_count"):
        if k not in sm:
            errs.append("summary: falta %s" % k)
        elif not isinstance(sm[k], int):
            errs.append("summary.%s: se esperaba int, se recibio %s"
                        % (k, type(sm[k]).__name__))
    sec = doc.get("sections")
    if not _es(sec, dict, "sections", errs):
        return errs
    for k in ("parameters", "calls", "call_targets", "unresolved",
              "effects", "evidence", "control_and_body"):
        if k not in sec:
            errs.append("sections: falta %s" % k)
        elif not isinstance(sec[k], list):
            errs.append("sections.%s: se esperaba list, se recibio %s"
                        % (k, type(sec[k]).__name__))
    for i, ct in enumerate(sec.get("call_targets") or []):
        if not isinstance(ct, dict):
            errs.append("sections.call_targets[%d]: no es objeto" % i)
            continue
        if ct.get("kind") not in ("INVOKES", "MAY_INVOKE"):
            errs.append("sections.call_targets[%d].kind: %r fuera de "
                        "{INVOKES, MAY_INVOKE}" % (i, ct.get("kind")))
        for k in ("source", "target", "confidence"):
            if k not in ct:
                errs.append("sections.call_targets[%d]: falta %s" % (i, k))
    return errs


def _validar_value_history(doc: Any) -> List[str]:
    errs: List[str] = []
    if not _es(doc, dict, "raiz", errs):
        return errs
    if doc.get("query") != "value-history":
        errs.append("raiz.query: se esperaba 'value-history', se recibio %r"
                    % doc.get("query"))
    _validar_match(doc.get("focus"), "focus", errs)
    sm = doc.get("summary")
    if not _es(sm, dict, "summary", errs):
        return errs
    for k in ("related_value_count", "transition_count"):
        if k not in sm:
            errs.append("summary: falta %s" % k)
        elif not isinstance(sm[k], int):
            errs.append("summary.%s: se esperaba int, se recibio %s"
                        % (k, type(sm[k]).__name__))
    h = (doc.get("sections") or {}).get("history")
    if not _es(h, list, "sections.history", errs):
        return errs
    for i, e in enumerate(h):
        _validar_match(e, "sections.history[%d]" % i, errs)
    return errs


# --- capa de proveedor: Lachesis por subproceso ------------------------

class LachesisCLI:
    """Transporte hacia el CLI de Lachesis. NO interpreta: transporta.

    La interpretacion (validacion de esquema, traduccion) es del
    adaptador, y es inyectable: los tests sustituyen esta clase por un
    doble que devuelve salidas REALES capturadas, sin ejecutar
    Lachesis, sin red y sin tocar la GPU.
    """

    def __init__(self, binario: str = "lachesis",
                 timeout: int = 300,
                 budget_tokens: Optional[int] = None,
                 kuzu_bps: Optional[str] = None) -> None:
        self.binario = binario
        self.timeout = timeout
        self.budget_tokens = budget_tokens
        self.kuzu_bps = kuzu_bps or os.environ.get("LACHESIS_KUZU_BPS") \
            or KUZU_BPS_DEFECTO

    # -- entorno ------------------------------------------------------
    def _raiz_runtime(self) -> Optional[str]:
        """Si el binario pertenece a un runtime `--target`, su raiz es
        lo que hace importable el paquete `lachesis` (PYTHONPATH).

        MEDIDO: `bin/lachesis` es un script Python con
        `from lachesis.cli.main import main`; sin el runtime en
        `PYTHONPATH` no arranca. Un lachesis instalado en el sistema no
        tiene esa estructura y no necesita el ajuste.
        """
        padre = os.path.dirname(os.path.dirname(os.path.abspath(self.binario)))
        if os.path.isfile(os.path.join(padre, "lachesis", "__init__.py")):
            return padre
        return None

    def _entorno(self) -> Dict[str, str]:
        env = os.environ.copy()
        rt = self._raiz_runtime()
        if rt:
            prev = env.get("PYTHONPATH")
            env["PYTHONPATH"] = rt + (os.pathsep + prev if prev else "")
        env["LACHESIS_KUZU_BPS"] = self.kuzu_bps or KUZU_BPS_DEFECTO
        return env

    # -- transporte ----------------------------------------------------
    def _ejecutar(self, args: List[str], timeout: int) -> Dict[str, Any]:
        argv = [sys.executable, self.binario] + list(args)
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout, env=self._entorno())
        except subprocess.TimeoutExpired:
            raise ErrorDeProveedorTimeout(self.binario, timeout)
        except OSError as e:
            raise ErrorDeProveedor(self.binario, None, str(e))
        if p.returncode != 0:
            raise ErrorDeProveedor(self.binario, p.returncode,
                                   (p.stderr or p.stdout or "").strip()[:400])
        try:
            return json.loads(p.stdout)
        except ValueError:
            raise ErrorDeEsquema(
                "salida de %s no es JSON (rc=0): %r"
                % (self.binario, (p.stdout or "")[:160]))

    def _ejecutar_texto(self, operacion: str, args: List[str],
                        timeout: int) -> Dict[str, Any]:
        """Comandos cuya salida es texto de progreso, no JSON.

        MEDIDO (integracion RXRE-1630): `lachesis build` y
        `lachesis enrich` escriben su progreso en stdout
        ('Streamed 1 frontends into ...\\nTier: core-only
        ...'). Ese texto NO es una respuesta consultable: es
        el registro del EFECTO del comando. Interpretarlo
        como dato (json.loads) convierte un build exitoso
        en ErrorDeEsquema y aborta antes de `enrich` y del
        manifiesto: un fallo de transporte disfrazado de
        fallo de esquema. Aqui el rc sigue siendo la unica
        senal de vida, y la salida viaja como evidencia de
        que el comando corrio, no como resultado."""
        argv = [sys.executable, self.binario] + list(args)
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout, env=self._entorno())
        except subprocess.TimeoutExpired:
            raise ErrorDeProveedorTimeout(self.binario, timeout)
        except OSError as e:
            raise ErrorDeProveedor(self.binario, None, str(e))
        if p.returncode != 0:
            raise ErrorDeProveedor(self.binario, p.returncode,
                                   (p.stderr or p.stdout or "").strip()[:400])
        return {"herramienta": self.binario,
                "operacion": operacion,
                "rc": p.returncode,
                "salida": (p.stdout or "").strip()[-400:],
                "stderr": (p.stderr or "").strip()[-200:]}

    # -- sonda de vida -------------------------------------------------
    def version(self) -> str:
        """`lachesis --version`. Es la sonda de vida del adaptador: si
        esto no responde, la capacidad NO esta disponible (blocked)."""
        argv = [sys.executable, self.binario, "--version"]
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               timeout=30, env=self._entorno())
        except (subprocess.TimeoutExpired, OSError) as e:
            raise ErrorDeContrato("lachesis no responde: %s" % e)
        if p.returncode != 0:
            raise ErrorDeContrato("lachesis --version rc=%d: %s"
                                  % (p.returncode, (p.stderr or "").strip()[:200]))
        return (p.stdout or "").strip()

    # -- preguntas -----------------------------------------------------
    def _query(self, graph: str, pregunta: str,
               args: Tuple[str, ...]) -> Dict[str, Any]:
        argv = ["query", "--format", "json", graph, pregunta] + list(args)
        if self.budget_tokens:
            argv = ["query", "--format", "json", "--budget-tokens",
                    str(self.budget_tokens), graph, pregunta] + list(args)
        return self._ejecutar(argv, self.timeout)

    def find_entity(self, graph: str, nombre: str,
                    kind: Optional[str] = None,
                    archivo: Optional[str] = None) -> Dict[str, Any]:
        args: List[str] = []
        if kind:
            args += ["--kind", kind]
        if archivo:
            args += ["--file", archivo]
        args.append(nombre)
        return self._query(graph, "find-entity", tuple(args))

    def function(self, graph: str, foco: str,
                 archivo: Optional[str] = None) -> Dict[str, Any]:
        args = ["--file", archivo] if archivo else []
        return self._query(graph, "function", tuple(args + [foco]))

    def value_history(self, graph: str, node_id: str) -> Dict[str, Any]:
        return self._query(graph, "value-history", (node_id,))

    # -- ciclo de vida del grafo ---------------------------------------
    def build(self, corpus: str, salida: str,
              timeout: int = 1800) -> Dict[str, Any]:
        """`lachesis build`. MEDIDO (RXRE-1629 §5): el timeout por
        defecto del frontend (300 s) mata el build de un corpus real;
        el build de corpus-small tarda 5:52. El presupuesto se pasa
        explicito y se declara. Su stdout es progreso, no JSON:
        el registro del efecto viaja en `salida`."""
        return self._ejecutar_texto(
            "build",
            ["build", "--timeout", str(timeout), corpus, salida],
            timeout)

    def enrich(self, graph: str, timeout: int = 600) -> Dict[str, Any]:
        """`lachesis enrich`. MEDIDO: 281 MB RSS, exito sobre
        corpus-small. Sin enrich, los tiers de efectos y semantica no
        existen y `function` reporta effect_count 0."""
        return self._ejecutar_texto("enrich", ["enrich", graph],
                                    timeout)

    def resolver_grafo(self, grafo: Optional[str],
                       corpus: Optional[str],
                       build_timeout: int = 1800) -> str:
        """Resuelve la precondicion del proveedor: un grafo .kuzu
        construido y enriquecido.

        Es PRECONDICION DEL PROVEEDOR, no del adaptador: quien
        sabe si un grafo sirve es el que lo va a consultar. El
        adaptador delega, y el doble de test devuelve un grafo
        simbolico: la validacion de existencia es del transporte
        real, no de la logica.
        """
        if grafo:
            if not os.path.isdir(grafo):
                raise ErrorDeContrato(
                    "el grafo no existe: %s (construyelo con --corpus, "
                    "o con `lachesis build` + `lachesis enrich`)" % grafo)
            return grafo
        if corpus:
            info = garantizar_grafico(
                corpus, self._grafo_por_defecto(corpus), self,
                build_timeout)
            return info["graph"]
        raise ErrorDeContrato(
            "falta grafo o corpus: pasa --graph <grafo.kuzu> ya "
            "construido y enriquecido, o --corpus <dir> para "
            "construirlo (lachesis build + enrich; el build de "
            "corpus-small mide 5:52 wall, 1.37 GB RSS)")

    @staticmethod
    def _grafo_por_defecto(corpus: str) -> str:
        return os.path.join(
            os.path.dirname(os.path.abspath(corpus)),
            "lachesis-defuse.kuzu")


# --- capa nativa: reg_resolve por subproceso ---------------------------

def _nativo_reg_resolve(kernel: str, simbolo: str, gfx: str,
                        timeout: int) -> Dict[str, Any]:
    """Ejecuta reg_resolve.py y devuelve su JSON.

    reg_resolve es la UNICA fuente de identidad de registro de RXRE:
    su busqueda sobre asic_reg es exhaustiva y su veredicto
    `PROVEN_ABSENT_EN_ASIC_REG` es la unica ausencia que este adaptador
    puede emitir. Un fallo de reg_resolve se propaga como error: no se
    interpreta como "no es un registro".
    """
    argv = [sys.executable, REG_RESOLVE, "--kernel", kernel,
            "--reg", simbolo, "--gfx", gfx, "--json"]
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ErrorNativo("reg_resolve.py", "timeout a los %ds" % timeout)
    except OSError as e:
        raise ErrorNativo("reg_resolve.py", str(e))
    if p.returncode != 0:
        raise ErrorNativo("reg_resolve.py",
                          "rc=%d: %s" % (p.returncode,
                                         (p.stderr or "").strip()[:300]))
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise ErrorNativo("reg_resolve.py", "salida no JSON")


# --- modelo de identidad de registro -----------------------------------

#: El bloque de IP es el DIRECTORIO bajo asic_reg/. Es una proyeccion
#: determinista de la ruta de procedencia, no una interpretacion:
#: `include/asic_reg/mmhub/mmhub_1_0_offset.h` dice que el bloque es
#: mmhub. Lo que no se deriva de la ruta no se inventa.
_ALIASES_BLOQUE = {
    "gc": "GC", "gmc": "GMC", "mmhub": "MMHUB", "gfxhub": "GFXHUB",
    "gca": "GCA", "vi": "VI", "cik": "CIK", "sdma": "SDMA",
    "nbio": "NBIO", "mp": "MP", "smu": "SMU", "psp": "PSP",
}


def _bloque_de(rel: str) -> str:
    """Bloque de IP a partir de la ruta relativa de la definicion."""
    partes = rel.replace("\\", "/").split("/")
    if "asic_reg" in partes:
        i = partes.index("asic_reg")
        if i + 1 < len(partes):
            crudo = partes[i + 1]
            return _ALIASES_BLOQUE.get(crudo.lower(), crudo.upper())
    return "DESCONOCIDO"


def _clave_de_definicion(rel: str, linea: int) -> Tuple[str, int, bool]:
    """Clave de union entre una definicion nativa y un nodo del
    proveedor: el sufijo de ruta tras `asic_reg/` mas la linea.

    El sufijo (y no la ruta absoluta) es la clave porque el proveedor
    y reg_resolve pueden hablar del mismo header desde raices de corpus
    distintas. Si la ruta no contiene `asic_reg/`, la clave cae a
    basename+linea y se marca como DEBIL: una clave debil puede unir
    dos definiciones distintas que compartan nombre, y eso se dice.
    """
    norm = rel.replace("\\", "/")
    if "asic_reg/" in norm:
        return (norm.split("asic_reg/", 1)[1], linea, True)
    return (os.path.basename(norm), linea, False)


def _clave_de_nodo(archivo: str, linea: int) -> Tuple[str, int, bool]:
    """La misma clave, para un nodo del proveedor (ruta absoluta)."""
    norm = archivo.replace("\\", "/")
    if "asic_reg/" in norm:
        return (norm.split("asic_reg/", 1)[1], linea, True)
    return (os.path.basename(norm), linea, False)


def _identidades_de_registro(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Agrupa las definiciones de reg_resolve por (bloque de IP,
    direccion). Cada grupo ES una identidad: una direccion en un
    bloque. Nunca se agrupa por nombre, y nunca se elige una sola.

    La unidad se conserva: el valor de asic_reg es un INDICE DWORD
    (declarado por reg_resolve con su cita de
    amdgpu_reg_access.c); el byte offset es indice*4.
    """
    res = (doc.get("results") or [{}])[0]
    defs = res.get("definitions") or []
    grupos: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    orden: List[Tuple[str, int]] = []
    for d in defs:
        bloque = _bloque_de(d.get("rel") or d.get("file") or "")
        valor = int(d.get("value") or 0)
        clave = (bloque, valor)
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        grupos[clave].append(d)
    identidades: List[Dict[str, Any]] = []
    for bloque, valor in orden:
        ds = grupos[(bloque, valor)]
        identidades.append({
            "ip_block": bloque,
            "symbol": res.get("symbol"),
            "address": "0x%x" % valor,
            "byte_offset": "0x%x" % (valor * 4),
            "unidad": "indice dword (byte offset = indice * 4)",
            "definition_count": len(ds),
            "definitions": ds,
        })
    # La eleccion de reg_resolve (si la hay) se REPORTA, no se reelige.
    elegida = res.get("chosen") or {}
    seleccion: Optional[Dict[str, Any]] = None
    if elegida:
        clave_el = _clave_de_definicion(
            elegida.get("rel") or elegida.get("file") or "",
            int(elegida.get("line") or 0))
        for idx, iden in enumerate(identidades):
            for d in iden["definitions"]:
                if _clave_de_definicion(d.get("rel") or d.get("file") or "",
                                        int(d.get("line") or 0)) == clave_el:
                    seleccion = {
                        "identity_index": idx,
                        "selected_by": "reg_resolve.py",
                        "rule": res.get("selection_rule"),
                        "evidence": res.get("selection_evidence"),
                    }
                    break
            if seleccion:
                break
    return {
        "verdict": res.get("verdict"),
        "note": res.get("note"),
        "identities": identidades,
        "identity_count": len(identidades),
        "conflict": bool(res.get("conflict")),
        "candidates": res.get("candidates") or [],
        "selection": seleccion,
        "unit_declaration": doc.get("unit_declaration"),
    }


# --- ciclo de vida del grafo (build cacheado por huella) --------------

def _huella_corpus(corpus: str) -> str:
    """SHA-256 canonico del corpus: rutas relativas ordenadas + hash de
    contenido. Determinista: el mismo corpus produce la misma huella, y
    un corpus distinto produce otra (el grafo cacheado no se reusa)."""
    h = hashlib.sha256()
    rutas: List[str] = []
    for base, _, ficheros in os.walk(corpus):
        for f in ficheros:
            rutas.append(os.path.relpath(os.path.join(base, f), corpus))
    for r in sorted(rutas):
        h.update(r.encode("utf-8"))
        with open(os.path.join(corpus, r), "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def garantizar_grafico(corpus: str, grafo: str, cli: LachesisCLI,
                       build_timeout: int = 1800) -> Dict[str, Any]:
    """Construye y enriquece el grafo, o reusa el existente.

    El manifisto junto al grafo registra la huella del corpus, la
    version de lachesis y el argv de build. Si todo casa, el grafo se
    reusa (el build de corpus-small mide 5:52; reusarlo es lo que hace
    repetible la prueba de integracion sin repetir el coste). Si no
    casa, se reconstruye: un grafo de otro corpus es una mentira con
    grafos bonitos.
    """
    manifiesto = grafo + ".manifest.json"
    version = cli.version()
    if os.path.isdir(grafo) and os.path.isfile(manifiesto):
        try:
            with open(manifiesto) as fh:
                m = json.load(fh)
            if (m.get("corpus_sha256") == _huella_corpus(corpus)
                    and m.get("lachesis_version") == version
                    and m.get("build_timeout") == build_timeout):
                return {"reused": True, "graph": grafo,
                        "manifest": m, "lachesis_version": version}
        except (ValueError, OSError):
            pass  # manifiesto ilegible: reconstruir, no confiar
    if not os.path.isdir(corpus):
        raise ErrorDeContrato("el corpus no existe: %s" % corpus)
    os.makedirs(os.path.dirname(os.path.abspath(grafo)) or ".",
                exist_ok=True)
    cli.build(corpus, grafo, build_timeout)
    cli.enrich(grafo)
    m = {"corpus": os.path.abspath(corpus),
         "corpus_sha256": _huella_corpus(corpus),
         "lachesis_version": version,
         "build_timeout": build_timeout,
         "build_argv": ["lachesis", "build", "--timeout",
                        str(build_timeout), corpus, grafo],
         "enriched": True}
    with open(manifiesto, "w") as fh:
        json.dump(m, fh, indent=2)
    return {"reused": False, "graph": grafo, "manifest": m,
            "lachesis_version": version}


def _limites_declarados_del_frontend(raiz_runtime: Optional[str]
                                     ) -> Dict[str, Any]:
    """Lee los limites que el propio frontend C se autodeclara.

    MEDIDO (RXRE-1629 §6): `lachesis/frontends/c/capabilities.json`
    autodeclara `direct_data_flow: partial`, `context_sensitivity:
    none`, `branch_histories: none`, entre otros. Esos limites viajan
    en cada resultado de flujo de datos: un consumidor que no los lee
    sobrestima lo que el proveedor demuestra.
    """
    if not raiz_runtime:
        return {"leidos": False,
                "razon": "runtime de lachesis no localizado (binario de "
                         "sistema): los limites autodeclarados del "
                         "frontend no se adjuntan"}
    ruta = os.path.join(raiz_runtime, "lachesis", "frontends", "c",
                        "capabilities.json")
    if not os.path.isfile(ruta):
        return {"leidos": False, "razon": "no encontrado: %s" % ruta}
    try:
        with open(ruta) as fh:
            doc = json.load(fh)
    except (ValueError, OSError) as e:
        return {"leidos": False, "razon": "ilegible (%s): %s" % (e, ruta)}
    return {"leidos": True, "fuente": ruta,
            "capabilities": doc.get("capabilities") or doc}


# --- el adaptador ------------------------------------------------------

class Defuse:
    """El adaptador. Traduce, valida y expone; no decide por la IA.

    Las dos capas externas son inyectables (`native`, `provider`) para
    que los tests corran contra salidas REALES capturadas sin ejecutar
    nada: sin Lachesis, sin reg_resolve, sin red, sin GPU.
    """

    def __init__(
        self,
        *,
        kernel: str = KERNEL_DEFECTO,
        gfx: str = GFX_DEFECTO,
        grafo: Optional[str] = None,
        corpus: Optional[str] = None,
        ip_block: Optional[str] = None,
        address: Optional[str] = None,
        timeout: int = 300,
        build_timeout: int = 1800,
        budget_tokens: Optional[int] = None,
        native: Optional[Callable[..., Dict[str, Any]]] = None,
        provider: Optional[LachesisCLI] = None,
        lachesis_bin: str = "lachesis",
    ) -> None:
        self.kernel = kernel
        self.gfx = gfx
        self.grafo = grafo
        self.corpus = corpus
        self.ip_block = ip_block
        self.address = address
        self.timeout = timeout
        self.build_timeout = build_timeout
        self.budget_tokens = budget_tokens
        self._native = native or _nativo_reg_resolve
        self._provider = provider or LachesisCLI(
            binario=lachesis_bin, timeout=timeout,
            budget_tokens=budget_tokens)

    # -- utilidades de contrato ---------------------------------------
    def _capa_no_aplicable(self, motivo: str) -> Dict[str, Any]:
        return {"producer": None, "status": "not-applicable",
                "reason": motivo}

    def _filtro_bloque(self, identidad: Dict[str, Any]) -> bool:
        if self.ip_block and identidad["ip_block"].lower() \
                != self.ip_block.lower():
            return False
        if self.address:
            try:
                pedida = int(str(self.address), 16)
            except ValueError:
                raise ErrorDeContrato(
                    "--address no es hexadecimal: %r" % self.address)
            if int(identidad["address"], 16) != pedida:
                return False
        return True

    # -- entrada principal ---------------------------------------------
    def consultar(self, intento: str, sujeto: str) -> Dict[str, Any]:
        if intento not in INTENTOS:
            raise ErrorDeContrato(
                "intento desconocido: %r (validos: %s)"
                % (intento, ", ".join(INTENTOS)))
        if not sujeto or not str(sujeto).strip():
            raise ErrorDeContrato("el sujeto no puede ser vacio")
        metodo = {
            "symbol": self._i_symbol,
            "def-use": self._i_def_use,
            "value-history": self._i_value_history,
            "bit-semantics": self._i_bit_semantics,
        }[intento]
        return metodo(sujeto)

    # -- caso 1: localizacion de simbolo ------------------------------
    def _i_symbol(self, sujeto: str) -> Dict[str, Any]:
        """¿Donde esta este simbolo? La capa nativa se consulta SIEMPRE
        primero (es barata y acota: un simbolo que es registro tiene
        identidad de registro); el proveedor localiza."""
        identidad = self._consultar_capa_nativa(sujeto)
        doc = self._provider_find_entity(sujeto)
        coincidencias = doc.get("matches") or []
        resultados: List[Dict[str, Any]] = []
        vistas: Dict[Tuple[str, int], int] = {}
        for m in coincidencias:
            loc = m.get("location") or {}
            clave = (loc.get("file"), int(loc.get("start_line") or 0))
            vistas[clave] = vistas.get(clave, 0) + 1
        for m in coincidencias:
            loc = m.get("location") or {}
            clave = (loc.get("file"), int(loc.get("start_line") or 0))
            rol = "definition" if m.get("kind") == "function" \
                else "reference"
            resultados.append({
                "state": "PROVEN",
                "kind": m.get("kind"),
                "label": m.get("label"),
                "role": rol,
                "node_id": m.get("id"),
                "location": {
                    "file": loc.get("file"),
                    "start_line": loc.get("start_line"),
                    "end_line": loc.get("end_line"),
                    "start_column": loc.get("start_column"),
                    "end_column": loc.get("end_column"),
                },
                "origin": m.get("origin"),
                "confidence": m.get("confidence"),
                "owner_chain": [
                    {"kind": e.get("kind"), "label": e.get("label")}
                    for e in ((m.get("locator") or {}).get("owner_chain")
                              or [])],
                "provenance": {
                    "producer": "lachesis",
                    "question": "find-entity",
                    "locator_tier": (m.get("locator") or {}).get("tier"),
                },
            })
        limitaciones = self._limitaciones_de_conteo(coincidencias, vistas)
        return self._contrato(
            intento="symbol", sujeto=sujeto,
            capas={"identity": identidad["capa"],
                   "provider": self._capa_proveedor(doc,
                                                     "find-entity")},
            resultados=resultados,
            limitaciones=limitaciones,
            herramientas=[{"tool": "reg_resolve.py",
                           "rc": identidad["rc"]},
                          {"tool": "lachesis",
                           "question": "find-entity",
                           "rc": 0}])

    def _limitaciones_de_conteo(
            self, coincidencias: List[Dict[str, Any]],
            vistas: Dict[Tuple[str, int], int]) -> List[str]:
        lim: List[str] = []
        for (archivo, linea), n in sorted(vistas.items()):
            if n > 1:
                lim.append(
                    "%d coincidencias comparten la misma localizacion "
                    "%s:%s: son nodos de la MISMA sentencia, no %d sitios "
                    "distintos. Falso positivo de conteo medido en "
                    "lachesis 0.5.3 (los dos operandos de una llamada se "
                    "reportan como dos entidades)." % (n, archivo, linea, n))
        return lim

    # -- caso 2/3/6: definicion y consumo -----------------------------
    def _i_def_use(self, sujeto: str) -> Dict[str, Any]:
        """¿Que define y que consume este simbolo?

        Dos caminos, y el que se toma NO se elige en silencio:

            reg_resolve resuelve el simbolo como REGISTRO
                -> identidades por (bloque, direccion); por cada
                   identidad, los nodos del proveedor que coinciden
                   POR CLAVE DE DEFINICION (no por nombre), y el
                   flujo de datos sobre el nodo representativo.
            reg_resolve responde PROVEN_ABSENT_EN_ASIC_REG
                -> no es un registro: el proveedor hace el slice de
                   funcion (definicion, parametros, llamadas, aristas
                   de destino).
        """
        identidad = self._consultar_capa_nativa(sujeto)
        if identidad["ausente"]:
            return self._def_use_de_funcion(sujeto, identidad)
        return self._def_use_de_registro(sujeto, identidad)

    def _def_use_de_funcion(
            self, sujeto: str,
            identidad: Dict[str, Any]) -> Dict[str, Any]:
        doc = self._provider_find_entity(sujeto)
        funciones = [m for m in (doc.get("matches") or [])
                     if m.get("kind") == "function"]
        if doc.get("status") == "not-found" or not funciones:
            return self._contrato(
                intento="def-use", sujeto=sujeto,
                capas={"identity": identidad["capa"],
                       "provider": self._capa_proveedor(doc,
                                                         "find-entity")},
                resultados=[],
                limitaciones=[
                    "el proveedor reporta not-found para %r en el indice "
                    "que construyo sobre SU corpus. Lachesis no tiene "
                    "nocion de universo exhaustivo: esto NO es ausencia "
                    "demostrada, es ausencia en el corpus parseado." % sujeto,
                    "la capa nativa (reg_resolve) ya acoto la ausencia de "
                    "definicion de registro sobre asic_reg con busqueda "
                    "exhaustiva; ver la capa identity."],
                herramientas=[{"tool": "reg_resolve.py",
                               "rc": identidad["rc"]},
                              {"tool": "lachesis",
                               "question": "find-entity", "rc": 0}])
        if len(funciones) > 1:
            lista = "; ".join("%s (%s:%s)" % (
                m.get("label"),
                (m.get("location") or {}).get("file"),
                (m.get("location") or {}).get("start_line"))
                for m in funciones)
            return self._contrato(
                intento="def-use", sujeto=sujeto,
                capas={"identity": identidad["capa"],
                       "provider": self._capa_proveedor(doc,
                                                         "find-entity")},
                resultados=[],
                limitaciones=[
                    "el sujeto es AMBIGUO para el proveedor: %d funciones "
                    "homonymas (%s). No se elige una en silencio: pasa "
                    "--file para desambiguar." % (len(funciones), lista)],
                herramientas=[{"tool": "reg_resolve.py",
                               "rc": identidad["rc"]},
                              {"tool": "lachesis",
                               "question": "find-entity", "rc": 0}])
        foco = funciones[0]
        slice_doc = self._provider_function(sujeto, foco)
        sec = slice_doc.get("sections") or {}
        llamadas = sec.get("calls") or []
        objetivos = sec.get("call_targets") or []
        con_arista = {ct.get("source") for ct in objetivos}
        sin_arista = [c for c in llamadas if c.get("id") not in con_arista]
        res: List[Dict[str, Any]] = [{
            "state": "PROVEN",
            "kind": "function",
            "label": foco.get("label"),
            "node_id": foco.get("id"),
            "role": "definition",
            "location": self._ubicacion_de(foco),
            "origin": foco.get("origin"),
            "confidence": foco.get("confidence"),
            "summary": slice_doc.get("summary"),
            "provenance": {"producer": "lachesis",
                           "question": "function",
                           "locator_tier":
                               (foco.get("locator") or {}).get("tier")},
        }]
        for p in sec.get("parameters") or []:
            res.append({
                "state": "PROVEN", "kind": p.get("kind"),
                "label": p.get("label"), "node_id": p.get("id"),
                "role": "parameter", "location": self._ubicacion_de(p),
                "origin": p.get("origin"), "confidence": p.get("confidence"),
                "provenance": {"producer": "lachesis",
                               "question": "function",
                               "locator_tier":
                                   (p.get("locator") or {}).get("tier")},
            })
        for c in llamadas:
            res.append({
                "state": "PROVEN", "kind": c.get("kind"),
                "label": c.get("label"), "node_id": c.get("id"),
                "role": "outgoing_call", "location": self._ubicacion_de(c),
                "origin": c.get("origin"), "confidence": c.get("confidence"),
                "provenance": {"producer": "lachesis",
                               "question": "function",
                               "locator_tier":
                                   (c.get("locator") or {}).get("tier")},
            })
        for ct in objetivos:
            res.append({
                "state": ("PROVEN" if ct.get("kind") == "INVOKES"
                          else "PARTIAL"),
                "kind": "call_target",
                "edge_kind": ct.get("kind"),
                "significado": ("direct_call" if ct.get("kind") == "INVOKES"
                                else "dispatch_indirect_candidate"),
                "source_node": ct.get("source"),
                "target_node": ct.get("target"),
                "confidence": ct.get("confidence"),
                "reason": ct.get("reason"),
                "provenance": {"producer": "lachesis",
                               "question": "function"},
                "limitations": ([] if ct.get("kind") == "INVOKES" else
                                ["arista %s con confianza %s y razon %r: "
                                 "el destino NO esta demostrado, es un "
                                 "candidato por nombre"
                                 % (ct.get("kind"), ct.get("confidence"),
                                    ct.get("reason"))]),
            })
        limitaciones = [
            "efectos: effect_count=%s (el tier de efectos exige "
            "enrich+analyze; este adaptador no ejecuta `analyze`, que es "
            "un analisis de seguridad, no un flujo de datos)"
            % ((slice_doc.get("summary") or {}).get("effect_count")),
            "vocabulario unificado: INVOKES (RXRE: arista DIRECTA) = "
            "llamada directa resuelta; MAY_INVOKE (RXRE: arista VTABLE) = "
            "candidato a dispatch indirecto. Un agente no necesita saber "
            "que herramienta lo modelo.",
        ]
        if sin_arista:
            limitaciones.append(
                "%d de %d llamadas salientes no tienen arista de destino "
                "en el grafo (sections.unresolved esta vacio): su objetivo "
                "es EXTERNO al corpus acotado del proveedor. No es una "
                "llamada no resuelta por el proveedor; es una frontera de "
                "corpus." % (len(sin_arista), len(llamadas)))
        if (sec.get("unresolved") or []):
            limitaciones.append(
                "el proveedor reporta %d llamadas no resueltas "
                "(sections.unresolved)." % len(sec["unresolved"]))
        return self._contrato(
            intento="def-use", sujeto=sujeto,
            capas={"identity": identidad["capa"],
                   "provider": self._capa_proveedor(doc, "find-entity"),
                   "dataflow": self._capa_proveedor(slice_doc, "function")},
            resultados=res, limitaciones=limitaciones,
            herramientas=[{"tool": "reg_resolve.py",
                           "rc": identidad["rc"]},
                          {"tool": "lachesis", "question": "find-entity",
                           "rc": 0},
                          {"tool": "lachesis", "question": "function",
                           "rc": 0}])

    def _def_use_de_registro(
            self, sujeto: str,
            identidad: Dict[str, Any]) -> Dict[str, Any]:
        """Caso 2: identidad de registro por bloque de IP.

        Por cada identidad (bloque, direccion): se localizan los nodos
        del proveedor que coinciden con SUS definiciones por clave de
        definicion (sufijo asic_reg + linea), y se pregunta al proveedor
        por el flujo de datos del nodo representativo. La eleccion de
        un nodo representativo por identidad se DECLARA: los nodos de
        una misma identidad son macros homonymas con el mismo valor, y
        el historial vacio medido de uno es el historial vacio de todos.
        """
        doc = self._provider_find_entity(sujeto)
        nodos: Dict[Tuple[str, int, bool], Dict[str, Any]] = {}
        clave_debil: List[str] = []
        for m in (doc.get("matches") or []):
            loc = m.get("location") or {}
            clave = _clave_de_nodo(str(loc.get("file") or ""),
                                   int(loc.get("start_line") or 0))
            nodos[clave] = m
            if not clave[2]:
                clave_debil.append("%s:%s" % (loc.get("file"),
                                              loc.get("start_line")))
        identidades = identidad["modelo"]["identities"]
        if self.ip_block or self.address:
            identidades = [i for i in identidades if self._filtro_bloque(i)]
        resultados: List[Dict[str, Any]] = []
        limite_defs_sin_nodo: List[str] = []
        for iden in identidades:
            provistos: List[Dict[str, Any]] = []
            sin_nodo: List[Dict[str, Any]] = []
            for d in iden["definitions"]:
                clave = _clave_de_definicion(
                    d.get("rel") or d.get("file") or "",
                    int(d.get("line") or 0))
                nodo = nodos.get(clave)
                if nodo is None:
                    sin_nodo.append({
                        "file": d.get("rel") or d.get("file"),
                        "line": d.get("line"),
                        "value": "0x%x" % int(d.get("value") or 0),
                        "causa": "definicion fuera del corpus que el "
                                 "proveedor parseo: no tiene nodo en SU "
                                 "indice. No es una definicion inexistente.",
                    })
                else:
                    provistos.append({
                        "node_id": nodo.get("id"),
                        "kind": nodo.get("kind"),
                        "label": nodo.get("label"),
                        "location": self._ubicacion_de(nodo),
                        "origin": nodo.get("origin"),
                        "confidence": nodo.get("confidence"),
                        "locator_tier": (nodo.get("locator") or {}).get(
                            "tier"),
                        "union": "clave de definicion (sufijo asic_reg + "
                                 "linea)" if clave[2] else
                                 "CLAVE DEBIL (basename + linea)",
                    })
            if sin_nodo:
                limite_defs_sin_nodo.append(
                    "%s/%s: %d de %d definiciones no tienen nodo en el "
                    "proveedor (%s)" % (
                        iden["ip_block"], iden["address"], len(sin_nodo),
                        len(iden["definitions"]),
                        ", ".join("%s:%s" % (s["file"], s["line"])
                                  for s in sin_nodo)))
            flujo = self._flujo_de_identidad(iden, provistos)
            resultado = {
                "state": "PROVEN",
                "kind": "register_identity",
                "symbol": iden["symbol"],
                "ip_block": iden["ip_block"],
                "address": iden["address"],
                "byte_offset": iden["byte_offset"],
                "unidad": iden["unidad"],
                "definition_count": iden["definition_count"],
                "definitions": [
                    {"file": d.get("rel") or d.get("file"),
                     "line": d.get("line"),
                     "value": "0x%x" % int(d.get("value") or 0),
                     "text": d.get("text")}
                    for d in iden["definitions"]],
                "provider_nodes": provistos,
                "provider_nodes_without_definition": sin_nodo,
                "dataflow": flujo,
                "provenance": {
                    "identity": {"producer": "reg_resolve.py",
                                 "kernel": self.kernel, "gfx": self.gfx},
                    "provider": {"producer": "lachesis",
                                 "question": "find-entity"},
                },
            }
            if identidad["modelo"].get("selection") \
                    and identidad["modelo"]["selection"]["identity_index"] \
                    == identidad["modelo"]["identities"].index(iden):
                resultado["native_selection"] = \
                    identidad["modelo"]["selection"]
            resultados.append(resultado)
        limitaciones = [
            "el proveedor NO modela bloques de IP ni direcciones: reporta "
            "%d macros homonymas sin agrupar. La agrupacion por (bloque, "
            "direccion) la hace la capa NATIVA (reg_resolve); este "
            "adaptador solo une las dos capas por clave de definicion."
            % len(doc.get("matches") or []),
            "la identidad de registro es (bloque de IP, direccion, "
            "procedencia), nunca el nombre: el nombre solo no identifica "
            "un registro en este driver.",
        ]
        if clave_debil:
            limitaciones.append(
                "%d nodo(s) del proveedor se unieron por CLAVE DEBIL "
                "(basename+linea, sin asic_reg/ en la ruta): la union "
                "puede ser ambigua." % len(clave_debil))
        if limite_defs_sin_nodo:
            limitaciones.extend(
                "union parcial: " + s for s in limite_defs_sin_nodo)
        if identidad["modelo"].get("conflict"):
            limitaciones.append(
                "reg_resolve detecta CONFLICTO: %d definiciones con %d "
                "direcciones distintas %s. La eleccion nativa (%s) solo "
                "es valida con la arista de include que la sustenta, y se "
                "reporta con su evidencia; las demas identidades siguen "
                "siendo respuestas validas para su bloque."
                % (sum(i["definition_count"] for i in identidades),
                   len(identidades),
                   identidad["modelo"].get("candidates") or [],
                   (identidad["modelo"].get("selection") or {}).get(
                       "rule") or "sin eleccion"))
        return self._contrato(
            intento="def-use", sujeto=sujeto,
            capas={"identity": identidad["capa"],
                   "provider": self._capa_proveedor(doc, "find-entity"),
                   "dataflow": {"producer": "lachesis",
                                "query": "value-history",
                                "status": "per-identity",
                                "detail": "un nodo representativo por "
                                          "identidad; declarado, no "
                                          "silencioso"}},
            resultados=resultados, limitaciones=limitaciones,
            herramientas=[{"tool": "reg_resolve.py",
                           "rc": identidad["rc"]},
                          {"tool": "lachesis", "question": "find-entity",
                           "rc": 0}])

    def _flujo_de_identidad(
            self, iden: Dict[str, Any],
            provistos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Flujo de datos de UNA identidad de registro.

        MEDIDO (RXRE-1630, contra lachesis 0.5.3): `value-history`
        sobre un nodo macro devuelve `related_value_count: 0`. Una
        #define es un valor opaco en el modelo del proveedor. Eso es
        NOT_DETERMINED con la causa medida, y NO es "no hay flujo".
        """
        if not provistos:
            return {
                "state": "NOT_DETERMINED",
                "causa": "ningun nodo del proveedor coincide con las "
                         "definiciones de esta identidad: no hay nodo "
                         "sobre el que preguntar por el flujo. La "
                         "identidad sigue siendo PROVEN por la capa "
                         "nativa.",
            }
        rep = provistos[0]
        try:
            doc = self._provider_value_history(rep["node_id"])
        except (ErrorDeProveedor, ErrorDeEsquema) as e:
            return {
                "state": "NOT_DETERMINED",
                "causa": "el proveedor fallo sobre el nodo "
                         "representativo %s: %s. La identidad sigue siendo "
                         "PROVEN por la capa nativa." % (rep["node_id"], e),
                "error_del_proveedor": str(e),
            }
        sm = doc.get("summary") or {}
        if not (doc.get("sections") or {}).get("history"):
            return {
                "state": "NOT_DETERMINED",
                "causa": "el proveedor reporta historial vacio "
                         "(related_value_count=%s) para el nodo macro %s: "
                         "una #define es un valor opaco en su modelo, sin "
                         "def-use. Esto NO es ausencia de flujo de datos: "
                         "es un limite del modelo del proveedor. Los usos "
                         "del registro (RREG32/WREG32) son macros y son "
                         "invisibles para el proveedor (medido en "
                         "RXRE-1629 caso 3)."
                         % (sm.get("related_value_count"), rep["node_id"]),
                "summary": sm,
                "representative_node": rep["node_id"],
                "sampling": "un nodo representativo por identidad",
            }
        return {
            "state": "PARTIAL",
            "causa": "historial de valores presente sobre el nodo "
                     "representativo; ver budget por truncamiento",
            "summary": sm,
            "representative_node": rep["node_id"],
            "sampling": "un nodo representativo por identidad",
        }

    # -- caso 4: historial de valores -----------------------------------
    def _i_value_history(self, sujeto: str) -> Dict[str, Any]:
        """¿Que valores definen y consumen este valor? El sujeto es un
        node_id del proveedor, o un nombre (con desambiguacion
        explicita: nunca se elige un nodo en silencio)."""
        nodo_id = sujeto.strip()
        if not nodo_id.startswith("v2:"):
            doc = self._provider_find_entity(nodo_id)
            ms = doc.get("matches") or []
            if doc.get("status") == "not-found" or not ms:
                return self._contrato(
                    intento="value-history", sujeto=sujeto,
                    capas={"identity": self._capa_no_aplicable(
                               "el sujeto es un nodo, no un nombre de "
                               "registro: la capa nativa no aplica"),
                           "provider": self._capa_proveedor(doc,
                                                             "find-entity")},
                    resultados=[],
                    limitaciones=[
                        "el proveedor reporta not-found para %r en SU "
                        "indice. Sin nocion de universo exhaustivo: esto "
                        "NO es ausencia demostrada." % sujeto],
                    herramientas=[{"tool": "lachesis",
                                   "question": "find-entity", "rc": 0}])
            if len(ms) > 1:
                lista = "; ".join("%s %s (%s:%s)" % (
                    m.get("kind"), m.get("label"),
                    (m.get("location") or {}).get("file"),
                    (m.get("location") or {}).get("start_line"))
                    for m in ms[:10])
                return self._contrato(
                    intento="value-history", sujeto=sujeto,
                    capas={"identity": self._capa_no_aplicable(
                               "el sujeto es un nodo, no un nombre de "
                               "registro: la capa nativa no aplica"),
                           "provider": self._capa_proveedor(doc,
                                                             "find-entity")},
                    resultados=[],
                    limitaciones=[
                        "el sujeto %r es AMBIGUO: %d entidades (%s...). "
                        "No se elige un nodo en silencio: pasa el node_id "
                        "(empieza por 'v2:') que reporta find-entity."
                        % (sujeto, len(ms), lista)],
                    herramientas=[{"tool": "lachesis",
                                   "question": "find-entity", "rc": 0}])
            nodo_id = ms[0].get("id")
        doc = self._provider_value_history(nodo_id)
        sm = doc.get("summary") or {}
        budget = doc.get("budget") or {}
        historial = (doc.get("sections") or {}).get("history") or []
        resultados = [{
            "state": "PARTIAL",
            "kind": e.get("kind"),
            "label": e.get("label"),
            "node_id": e.get("id"),
            "location": self._ubicacion_de(e),
            "origin": e.get("origin"),
            "confidence": e.get("confidence"),
            "owner_chain": [
                {"kind": s.get("kind"), "id": s.get("id"),
                 "label": s.get("label")}
                for s in ((e.get("locator") or {}).get("owner_chain") or [])],
            "provenance": {
                "producer": "lachesis",
                "question": "value-history",
                "focus_node": nodo_id,
                "locator_tier": (e.get("locator") or {}).get("tier"),
                "owner_chain_es_la_cadena_de_procedencia": True,
            },
        } for e in historial]
        limitaciones = self._limites_de_dataflow(budget, sm, len(historial))
        return self._contrato(
            intento="value-history", sujeto=sujeto,
            capas={"identity": self._capa_no_aplicable(
                       "el sujeto es un nodo, no un nombre de registro: "
                       "la capa nativa no aplica"),
                   "provider": self._capa_proveedor(doc, "value-history"),
                   "dataflow": self._capa_proveedor(doc, "value-history")},
            resultados=resultados, limitaciones=limitaciones,
            herramientas=[{"tool": "lachesis",
                           "question": "value-history", "rc": 0}])

    def _limites_de_dataflow(self, budget: Dict[str, Any],
                             sm: Dict[str, Any],
                             mostrados: int) -> List[str]:
        lim: List[str] = []
        relacionados = int(sm.get("related_value_count") or 0)
        if budget.get("truncated"):
            omit = budget.get("omitted") or {}
            lim.append(
                "el proveedor TRUNCA el historial por presupuesto de "
                "respuesta: %d de %d valores relacionados (%d omitidos); "
                "%s transiciones y %s evidencias omitidas "
                "(presupuesto %s tokens, estimador %s). El truncamiento "
                "se declara con numeros: un historial truncado no es un "
                "historial completo."
                % (mostrados, relacionados, omit.get("history"),
                   omit.get("transitions"), omit.get("evidence"),
                   budget.get("requested_tokens"), budget.get("estimator")))
        lim.append(
            "limites autodeclarados por el frontend C de lachesis: "
            "direct_data_flow: partial, context_sensitivity: none, "
            "branch_histories: none. El historial es una cadena de "
            "def-use SIN sensibilidad de contexto: una rama no tomada no "
            "se distingue de una tomada.")
        return lim

    # -- caso 5: semantica de bits (rechazo por contrato) --------------
    def _i_bit_semantics(self, sujeto: str) -> Dict[str, Any]:
        """¿Que bit invalida el ATC L2? RECHAZO POR CONTRATO.

        El proveedor modela estructura de codigo (AST de clang), no
        semantica de registro: no hay modelo de bits, de mascara ni de
        efecto de hardware. MEDIDO (RXRE-1629 caso 5): la respuesta
        correcta es una MASCARA DE MODO (CACHE_INVALIDATE_MODE, shift
        0x8), no un flag — y esa respuesta vive en
        rxre_register_fields.py, nativo de RXRE, no aqui.

        El adaptador no invoca al proveedor (no hay pregunta que
        hacerle) y no invoca a rxre_register_fields (componer otra
        capacidad es trabajo del pipeline, no del adaptador): declara
        quien puede responder.
        """
        return self._contrato(
            intento="bit-semantics", sujeto=sujeto,
            capas={
                "identity": self._capa_no_aplicable(
                    "el rechazo es por contrato, antes de consultar"),
                "provider": self._capa_no_aplicable(
                    "no hay pregunta de flujo de datos que hacerle al "
                    "proveedor sobre semantica de bits"),
                "dataflow": self._capa_no_aplicable(
                    "el proveedor no modela semantica de bits de registro"),
            },
            resultados=[{
                "state": "NOT_DETERMINED",
                "kind": "bit_semantics",
                "subject": sujeto,
                "causa": "lachesis modela estructura de codigo (AST de "
                         "clang expandido), no semantica de registro: no "
                         "hay modelo de bits, de mascara ni de efecto de "
                         "hardware. Una #define mm* es una macro opaca en "
                         "su modelo.",
                "resolvable_by": {
                    "tool": "rxre_register_fields.py",
                    "capability": "register-fields",
                    "por_que": "lee los *_sh_mask.h: shift, mascara y "
                               "campo por campo, por bloque de IP y "
                               "generacion. La invalidez de ATC L2 la "
                               "gobierna CACHE_INVALIDATE_MODE (shift 0x8) "
                               "con NUMBER_OF_TRANSLATION_{READS,WRITES}_"
                               "DEPENDS_ON_ADDR_MOD (shift 0x6/0x7): una "
                               "mascara de modo, no un flag simple.",
                    "argv": ["rxre_register_fields.py", "--reg", sujeto,
                             "--gfx", self.gfx, "--json"],
                },
            }],
            limitaciones=[
                "este adaptador NO responde preguntas de semantica de "
                "bits: no es una falta de ejecucion, es una frontera de "
                "modelo del proveedor. La respuesta nativa existe y se "
                "puede pedir por la capacidad register-fields.",
            ],
            herramientas=[])

    # -- helpers de capa ------------------------------------------------
    def _consultar_capa_nativa(self, sujeto: str) -> Dict[str, Any]:
        """Ejecuta reg_resolve y prepara la capa identity.

        Un fallo de reg_resolve ES un error del adaptador: no se
        interpreta como ausencia de registro.
        """
        try:
            doc = self._native(self.kernel, sujeto, self.gfx, self.timeout)
        except ErrorNativo as e:
            raise ErrorNativo("reg_resolve.py",
                              "fallo la capa nativa: %s" % e.detalle)
        res = (doc.get("results") or [{}])[0]
        ausente = str(res.get("verdict") or "").startswith("PROVEN_ABSENT")
        modelo = _identidades_de_registro(doc) if not ausente else None
        capa = {
            "producer": "reg_resolve.py",
            "status": "absent" if ausente else "resolved",
            "verdict": res.get("verdict"),
            "note": res.get("note"),
            "kernel": self.kernel,
            "gfx": self.gfx,
            "unit_declaration": doc.get("unit_declaration"),
        }
        if modelo:
            capa.update({
                "identity_count": modelo["identity_count"],
                "conflict": modelo["conflict"],
                "candidates": modelo["candidates"],
                "selection": modelo["selection"],
            })
        return {"capa": capa, "modelo": modelo, "ausente": ausente,
                "rc": 0, "doc": doc}

    def _capa_proveedor(self, doc: Dict[str, Any],
                        pregunta: str) -> Dict[str, Any]:
        return {"producer": "lachesis", "status": doc.get("status")
                or doc.get("query") or "responded",
                "question": pregunta,
                "criteria": doc.get("criteria") or doc.get("focus")
                or None,
                "summary": doc.get("summary") or None,
                "budget": doc.get("budget") or None,
                "match_count": len(doc.get("matches") or [])}

    @staticmethod
    def _ubicacion_de(m: Dict[str, Any]) -> Dict[str, Any]:
        loc = m.get("location") or {}
        return {"file": loc.get("file"),
                "start_line": loc.get("start_line"),
                "start_column": loc.get("start_column"),
                "end_line": loc.get("end_line"),
                "end_column": loc.get("end_column")}

    # -- proveedor con validacion de esquema ----------------------------
    def _provider_find_entity(self, nombre: str) -> Dict[str, Any]:
        doc = self._provider.find_entity(self._grafo_o_error(), nombre)
        errs = _validar_find_entity(doc)
        if errs:
            raise ErrorDeEsquema(
                "find-entity no cumple el esquema medido de lachesis "
                "0.5.3 (%d problema(s)): %s"
                % (len(errs), "; ".join(errs[:6])))
        return doc

    def _provider_function(self, foco: str,
                           nodo: Dict[str, Any]) -> Dict[str, Any]:
        archivo = (nodo.get("location") or {}).get("file")
        doc = self._provider.function(self._grafo_o_error(), foco,
                                      archivo=archivo)
        errs = _validar_function(doc)
        if errs:
            raise ErrorDeEsquema(
                "function no cumple el esquema medido de lachesis 0.5.3 "
                "(%d problema(s)): %s" % (len(errs), "; ".join(errs[:6])))
        return doc

    def _provider_value_history(self, node_id: str) -> Dict[str, Any]:
        doc = self._provider.value_history(self._grafo_o_error(), node_id)
        errs = _validar_value_history(doc)
        if errs:
            raise ErrorDeEsquema(
                "value-history no cumple el esquema medido de lachesis "
                "0.5.3 (%d problema(s)): %s"
                % (len(errs), "; ".join(errs[:6])))
        return doc

    def _grafo_o_error(self) -> str:
        """La precondicion del grafo la resuelve el PROVEEDOR:
        el transporte real valida que el grafo exista (o lo
        construye desde --corpus, cacheado por huella); el
        doble de test devuelve un grafo simbolico. El adaptador
        no decide si un grafo sirve: no es su capa."""
        if getattr(self, "_grafo_resuelto", None):
            return self._grafo_resuelto
        self._grafo_resuelto = self._provider.resolver_grafo(
            self.grafo, self.corpus, self.build_timeout)
        self.grafo = self._grafo_resuelto
        return self._grafo_resuelto

    # -- el contrato de salida ------------------------------------------
    def _contrato(self, *, intento: str, sujeto: str,
                  capas: Dict[str, Any], resultados: List[Dict[str, Any]],
                  limitaciones: List[str],
                  herramientas: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "tool": TOOL,
            "version": VERSION,
            "operation": OPERATION,
            "intent": intento,
            "subject": sujeto,
            "layers": capas,
            "results": resultados,
            "limitations": limitaciones or [],
            "tools_used": herramientas,
        }


# --- selftest: la sonda de vida (sin Lachesis, sin reg_resolve) -------

def _fixture(nombre: str) -> Dict[str, Any]:
    ruta = os.path.join(RXRE_PKG, "tests", "fixtures", "lachesis", nombre)
    with open(ruta) as fh:
        return json.load(fh)


class _ProveedorFijo:
    """Doble del proveedor que devuelve salidas REALES capturadas de
    lachesis 0.5.3. No ejecuta nada: es el proveedor medido, congelado
    como vector de regression."""

    def __init__(self, respuestas: Dict[str, Dict[str, Any]],
                 fallos: Optional[Dict[str, Exception]] = None) -> None:
        self.respuestas = respuestas
        self.fallos = fallos or {}
        self.llamadas: List[Tuple[str, tuple]] = []

    def _respuesta(self, pregunta: str, args: Tuple[str, ...]) \
            -> Dict[str, Any]:
        self.llamadas.append((pregunta, args))
        fallo = self.fallos.get(pregunta)
        if fallo:
            raise fallo
        return self.respuestas[pregunta]

    def find_entity(self, graph: str, nombre: str,
                    kind: Optional[str] = None,
                    archivo: Optional[str] = None) -> Dict[str, Any]:
        return self._respuesta("find-entity", (nombre,))

    def function(self, graph: str, foco: str,
                 archivo: Optional[str] = None) -> Dict[str, Any]:
        return self._respuesta("function", (foco,))

    def value_history(self, graph: str, node_id: str) -> Dict[str, Any]:
        return self._respuesta("value-history", (node_id,))

    def build(self, corpus: str, salida: str,
              timeout: int = 1800) -> Dict[str, Any]:
        return self._respuesta("build", (corpus, salida))

    def enrich(self, graph: str, timeout: int = 600) -> Dict[str, Any]:
        return self._respuesta("enrich", (graph,))

    def resolver_grafo(self, grafo: Optional[str],
                       corpus: Optional[str],
                       build_timeout: int = 1800) -> str:
        # El doble no valida: el grafo es simbolico porque la
        # logica bajo test no depende del sistema de archivos.
        return "fixture://lachesis"

    @property
    def binario(self) -> str:
        return "lachesis-ficticio"

    def version(self) -> str:
        return "lachesis 0.5.3 (fixture)"

    def _raiz_runtime(self) -> Optional[str]:
        return None


class _NativoFijo:
    """Doble de reg_resolve: devuelve la salida REAL capturada."""

    def __init__(self, docs: Dict[str, Dict[str, Any]]) -> None:
        self.docs = docs
        self.llamadas: List[Tuple[str, str, str]] = []

    def __call__(self, kernel: str, simbolo: str, gfx: str,
                 timeout: int) -> Dict[str, Any]:
        self.llamadas.append((kernel, simbolo, gfx))
        return self.docs[simbolo]


def selftest() -> int:
    """La sonda que `dispatch.probe_all` ejecuta: demuestra que el
    adaptador traduce, contra salidas reales, sin ejecutar nada.

    No es un test de la maquina: es la prueba de vida de la capacidad.
    Los tests completos viven en tests/test_lachesis_defuse_adapter.py.
    """
    try:
        _ejecutar_selftest()
    except Exception as e:  # la sonda debe decirlo, no tronar
        print("selftest FAIL: %s: %s" % (type(e).__name__, e),
              file=sys.stderr)
        return 1
    print("selftest OK: 6 vectores traducidos (casos 1-6 de RXRE-1629)")
    return 0


def _ejecutar_selftest() -> None:
    gart = _fixture("find-entity_gmc_v8_0_gart_enable.json")
    mmatc = _fixture("find-entity_mmATC_L2_CNTL.json")
    zzz = _fixture("find-entity_mmZZZ_NO_EXISTE.json")
    func = _fixture("function_gmc_v8_0_gart_enable.json")
    vh = _fixture("value-history_parameter_adev.json")
    nat_mmatc = _fixture("reg-resolve_mmATC_L2_CNTL.json")
    nat_zzz = _fixture("reg-resolve_mmZZZ_NO_EXISTE_ESTE_REG.json")
    nat_gart = _fixture("reg-resolve_gmc_v8_0_gart_enable.json")

    prov = _ProveedorFijo({"find-entity": gart, "function": func})
    nat = _NativoFijo({"gmc_v8_0_gart_enable": nat_gart})
    a = Defuse(native=nat, provider=prov)
    r = a.consultar("symbol", "gmc_v8_0_gart_enable")
    assert r["layers"]["identity"]["status"] == "absent", r["layers"]
    assert len(r["results"]) == 3, len(r["results"])
    assert r["results"][0]["state"] == "PROVEN"

    prov2 = _ProveedorFijo({"find-entity": mmatc,
                            "value-history": _fixture(
                                "value-history_macro_mmATC_L2_CNTL.json")})
    nat2 = _NativoFijo({"mmATC_L2_CNTL": nat_mmatc})
    a2 = Defuse(native=nat2, provider=prov2)
    r2 = a2.consultar("def-use", "mmATC_L2_CNTL")
    ids = r2["results"]
    assert len(ids) == 3, "esperadas 3 identidades, hay %d" % len(ids)
    bloques = sorted(i["ip_block"] for i in ids)
    assert bloques == ["GC", "GMC", "MMHUB"], bloques
    dirs = sorted(i["address"] for i in ids)
    assert dirs == ["0x640", "0x800", "0xcd5"], dirs
    assert all(i["dataflow"]["state"] == "NOT_DETERMINED" for i in ids)
    assert any("native_selection" in i for i in ids)

    prov3 = _ProveedorFijo({"find-entity": gart, "function": func})
    nat3 = _NativoFijo({"gmc_v8_0_gart_enable": nat_gart})
    a3 = Defuse(native=nat3, provider=prov3)
    r3 = a3.consultar("def-use", "gmc_v8_0_gart_enable")
    assert r3["results"][0]["role"] == "definition"
    assert any(x.get("role") == "outgoing_call" for x in r3["results"])

    prov4 = _ProveedorFijo({"value-history": vh})
    a4 = Defuse(native=_NativoFijo({}), provider=prov4)
    r4 = a4.consultar("value-history", "v2:frontend:clang-c:"
                      "parameter:4afbcc267c1671efd7dc")
    assert r4["results"] and r4["results"][0]["state"] == "PARTIAL"
    assert any("TRUNC" in x or "trunc" in x.lower()
               for x in r4["limitations"])

    a5 = Defuse(native=_NativoFijo({}), provider=_ProveedorFijo({}))
    r5 = a5.consultar("bit-semantics", "ATC_L2_CNTL")
    assert r5["results"][0]["state"] == "NOT_DETERMINED"
    assert r5["results"][0]["resolvable_by"]["tool"] == \
        "rxre_register_fields.py"

    prov6 = _ProveedorFijo({"find-entity": zzz})
    nat6 = _NativoFijo({"mmZZZ_NO_EXISTE_ESTE_REG": nat_zzz})
    a6 = Defuse(native=nat6, provider=prov6)
    r6 = a6.consultar("def-use", "mmZZZ_NO_EXISTE_ESTE_REG")
    assert r6["layers"]["identity"]["verdict"] == "PROVEN_ABSENT_EN_ASIC_REG"
    assert r6["layers"]["provider"]["status"] == "not-found"


# --- CLI ---------------------------------------------------------------

def _argumentos() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL,
        description="Flujo de datos interprocedural (def-use) sobre "
                    "Lachesis, con identidad de registro nativa de RXRE.")
    p.add_argument("--intent", default="def-use", choices=INTENTOS,
                   help="intento a responder (defecto: def-use)")
    p.add_argument("--subject", required=False,
                   help="sujeto: registro, funcion, simbolo o node_id")
    p.add_argument("--kernel", default=KERNEL_DEFECTO,
                   help="raiz de fuentes para la capa nativa (reg_resolve)")
    p.add_argument("--gfx", default=GFX_DEFECTO)
    p.add_argument("--graph", dest="grafo",
                   help="grafo .kuzu ya construido y enriquecido")
    p.add_argument("--corpus",
                   help="raiz de fuentes para construir el grafo "
                        "(build+enrich, cacheado por huella)")
    p.add_argument("--ip-block",
                   help="desambigua por bloque de IP (GC, GMC, MMHUB...)")
    p.add_argument("--address",
                   help="desambigua por direccion dword (hex, p.ej. 0x640)")
    p.add_argument("--lachesis-bin", default="lachesis")
    p.add_argument("--timeout", type=int, default=300,
                   help="presupuesto por consulta al proveedor")
    p.add_argument("--build-timeout", type=int, default=1800,
                   help="presupuesto del build del frontend (MEDIDO: el "
                        "defecto de 300 s mata el build de un corpus real)")
    p.add_argument("--budget-tokens", type=int,
                   help="presupuesto de respuesta del proveedor")
    p.add_argument("--selftest", action="store_true",
                   help="sonda de vida sobre fixtures (no ejecuta nada)")
    p.add_argument("--json", action="store_true",
                   help="el contrato ES JSON; la bandera existe por el "
                        "contrato de dispatch")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = _argumentos()
    args = p.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.subject:
        p.error("--subject es obligatorio sin --selftest")
    try:
        cli = LachesisCLI(binario=args.lachesis_bin,
                          timeout=args.timeout,
                          budget_tokens=args.budget_tokens)
        try:
            cli.version()
        except ErrorDeContrato as e:
            raise ErrorDeContrato(
                "lachesis no esta disponible (%s). Pasa --lachesis-bin con "
                "la ruta al binario, o instalalo del wheel (sin tocar el "
                "sistema): pip3 install --target <runtime> "
                "lachesis_cpg-0.5.3*.whl" % e)
        a = Defuse(kernel=args.kernel, gfx=args.gfx, grafo=args.grafo,
                   corpus=args.corpus, ip_block=args.ip_block,
                   address=args.address, timeout=args.timeout,
                   build_timeout=args.build_timeout,
                   budget_tokens=args.budget_tokens,
                   lachesis_bin=args.lachesis_bin)
        contrato = a.consultar(args.intent, args.subject)
        json.dump(contrato, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        # ok y empty salen 0 a proposito (el envelope lo decide):
        # empty es una ejecucion correcta sin resultados, no un fallo.
        return 0
    except ErrorDeContrato as e:
        # Precondicion no cumplida: blocked (2). No es un fallo: es una
        # limitacion declarada, y el envelope la eleva a ST_BLOCKED.
        salida = {"tool": TOOL, "version": VERSION, "operation": OPERATION,
                  "intent": args.intent, "subject": args.subject,
                  "error": {"kind": "blocked", "detail": str(e)},
                  "layers": {}, "results": [],
                  "limitations": [str(e)], "tools_used": []}
        json.dump(salida, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        print("blocked: %s" % e, file=sys.stderr)
        return 2
    except (ErrorDeEsquema, ErrorDeProveedor, ErrorDeProveedorTimeout,
            ErrorNativo) as e:
        # El proveedor o la capa nativa fallo: error (1). Nunca empty.
        salida = {"tool": TOOL, "version": VERSION, "operation": OPERATION,
                  "intent": args.intent, "subject": args.subject,
                  "error": {"kind": "error",
                            "class": type(e).__name__,
                            "detail": str(e)},
                  "layers": {}, "results": [],
                  "limitations": ["%s: %s" % (type(e).__name__, e)],
                  "tools_used": []}
        json.dump(salida, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        print("error: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
