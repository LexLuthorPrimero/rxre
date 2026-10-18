#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001. Adapter de `source.ast_parse` sobre tree-sitter.

POR QUE ESTA CAPACIDAD Y NO OTRA.

`source.semantic_search` (Coccinelle) ya existe y MEDIO algo: aplica un patch y
mira el diff. Eso responde "que cambia si modifico esto". NO responde "que
estructura tiene ESTE fichero", porque un patch del que no aplica no dice nada
del arbol.

El hueco real: el driver de amdgpu es C de ~800 kLine, y la pregunta
"cuantas funciones escriben en este registro" NO se responde con patch. Se
responde con un AST, y el AST de un fichero de C lo da tree-sitter sin build
y sin motor de analisis.

MEDIDO 2026-10-15, `amdgpu.h` del clon sparse de linux (commit
0fcb05b72344f40806cbe810de8872f1698bf053):

    amdgpu.h parseado: 42872 bytes, 7066 nodos, root=translation_unit
    nodos ERROR/missing: 10

Es decir: 7066 nodos y 10 de error. El 0.14% de nodos invalidos es la
prueba de que el parser es usable sobre ESTE codigo, y tambien de que no es
perfecto: esos 10 nodos se REPORTAN, no se esconden (§81).

## LO QUE ESTE ADAPTER HACE Y LO QUE NO

HACE:
    entrada -> hash -> precheck -> parseo -> conteo de nodos por tipo
           -> localization de patrones en nodos -> provenance -> persistencia

NO HACE, y por que:

* NO afirma nada del HARDWARE. `source.ast_parse` produce `structural_facts`:
    lo que el CODIGO dice, no lo que el hardware hace. Un `write` a un
    registro en el fuente es una HIPOTESIS sobre el hardware hasta que un
    probe la confirme. El nivel de confianza lo pone el contrato, no el
    adapter.

* NO inventa un lenguaje. Si el fichero no es del lenguaje pedido, se devuelve
    `unsupported`, no `empty`: no saber parsearlo NO es lo mismo que no tener
    nada que mirar. Es la distincion que `rz_inspect` ya aplica con la
    arquitectura (MEDIDO alli: arch=None != sin arquitectura).

* NO usa regex. Si se pide un `patron`, se busca en el ARBOL, no en el texto.
    Un patron que casa en un comentario o en un string NO es un nodo. Esa
    diferencia es la capacidad entera.

* NO cuenta ocurrencias de texto. Cuenta NODOS. `write(` aparece 400 veces
    en un .c, y 12 de esas veces son el nombre de una funcion local.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time as _t
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.contract import (  # noqa: E402
    BK_BLOCKED, BK_EMPTY, BK_ERROR, BK_INVALID, BK_OK, BK_UNSUPPORTED,
    Backend, sha256_de,
)

#: Tipo de resultado. NO esta en ORDEN_CONFIANZA del contrato porque no es una
#: afirmacion sobre un binario ni sobre hardware: es una afirmacion sobre la
#: ESTRUCTURA del texto fuente. Se declara aqui para no contaminar la escalera
#: de confianza, que es para productores de binario/hardware.
STRUCTURAL_FACTS = "structural_facts"

#: El venv aislado donde se instalaron los bindings. NO es el interprete del
#: sistema: §89 dice que las dependencias que no hacen falta globalmente no se
#: instalan globalmente.
#:
#: MEDIDO: `PKG` es `tools/`, NO la raiz del repositorio. Un `os.path.join(PKG,
#: "..", "..")` lleva a la raiz de la SX del HOME, no a la del repo: el primer
#: intento resolvio `/home/lucas/Escritorio/rxre/tools/../../.venv` y produjo
#: `blocked` con un path que no existe. Se sube por dirname hasta encontrar el
#: directorio que contiene a `tools/rxre` Y a `.venv`, en vez de contar niveles.
#: Contar niveles es brittle ante cualquier movimiento; preguntar por la marca
#: no lo es.
def _raiz_del_repo() -> str:
    d = HERE
    for _ in range(6):
        d = os.path.dirname(d)
        if (os.path.isdir(os.path.join(d, "tools", "rxre"))
                and os.path.isdir(os.path.join(d, ".venv"))):
            return d
    # Sin `.venv` todavía: se sube igualmente hasta el repo y se informa.
    d = HERE
    while not os.path.isdir(os.path.join(d, "tools", "rxre")):
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    return d


RAIZ = _raiz_del_repo()
VENV = os.path.join(RAIZ, ".venv", "eco")
VENV_PY = os.path.join(VENV, "bin", "python")

#: Lenguajes con binding medido en ESTE host. La lista es cerrado a proposito:
#: `tree_sitter_language_pack` trae 150 gramaticas y no se ha medido ninguna,
#: asi que declararlas seria生产能力 sin producer.
#: Proporcion de nodos ERROR por encima de la cual el fichero NO es del
#: lenguaje pedido. MEDIDO el 2026-10-15 con el parser de C:
#:
#:     amdgpu.h (C real)   ratio 0.0014
#:     fichero .py         ratio 0.0667
#:     fichero .md         ratio 0.1034
#:
#: El umbral va en medio del hueco, no en un borde. Subirlo a 0.05 dejaria
#: pasar el .py; bajarlo a 0.005 rechazaria C con macros exoticas.
UMBRAL_ERROR = 0.01

LENGUAJES = {
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
}

#: Tipos de nodo que NO son codigo fuente, aunque sean hojas.
#:
#: MEDIDO 2026-10-15. El visitor original filtraba por `child_count == 0`
#: creyendo que "hoja" significa "codigo". Es FALSO en tree-sitter: un
#: comentario y una cadena literales son hojas.
#:
#:     /* MARCA */ const char *s = "MARCA"; int MARCA = 1;
#:     texto = 3 apariciones
#:     filter_por_child_count_0 = 3 nodos   <-MAL: cuenta el comentario y la cadena
#:     filter_por_tipo = 1 nodo            <- lo que dice "donde escribe esto"
#:
#: El filtro por tipo es el correcto para la pregunta que la capacidad
#: responde. Un `grep` cuenta 3; un grep cuenta 3; solo el AST cuenta las que
#: son codigo ejecutable.
TIPOS_NO_CODIGO = frozenset((
    "comment", "line_comment", "block_comment",
    "string_literal", "string_content", "char_literal",
    "system_lib_string", "preproc_include", "preproc_def", "preproc_call",
    "preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif",
    "preproc_params", "preproc_directive",
    "interpreted_string_literal", "raw_string_literal",
))

#: Extracto del script que corre DENTRO del venv. Se pasa por stdin y se
#: responde por stdout como JSON de una linea.
#:
#: POR QUE UN SUBPROCESO Y NO UN IMPORT: los bindings de tree-sitter son
#: binarios nativos compilados para una version de Python concreta (CPython
#: 3.14 aqui). Importarlos en el interprete del motor los ataria a ESTE host
#: y haria que `import backends.adapters.ts_ast` fallara en otro. Aislando en
#: un subproceso, el fallo es un `blocked` con causa, no un ImportError que
#: tumba el dispatch entero.
_CODIGO_VENV = r'''
import json, os, sys
NO_CODIGO = set()          # lo inyecta el adapter
try:
    from tree_sitter import Language, Parser
except Exception as e:
    print(json.dumps({"status": "blocked", "motivo": "tree_sitter ausente: %s" % e}))
    raise SystemExit(0)
import importlib
_params = json.loads(sys.stdin.read())
# MEDIDO 2026-10-15: la primera version hacia
#     idioma, camino, patron, limite = json.loads(sys.stdin.read())
# y fallaba con FileNotFoundError: 'camino'. Desempaquetar un DICT en Python
# yield sus CLAVES, no sus valores: `camino` valia la cadena "camino", y el
# parser buscaba un fichero con ese nombre. Un rc=1 con traceback, que es
# justo el fallo caro: el script habia arrancado y parecia que funcionaba.
_params = _params if isinstance(_params, dict) else {}
idioma = _params.get("idioma", "")
camino = _params.get("camino", "")
patron = _params.get("patron", "")
limite = _params.get("limite", 100)
if not camino or not os.path.isfile(camino):
    print(json.dumps({"status": "error",
                      "motivo": "camino no existe: %r" % camino}))
    raise SystemExit(0)
try:
    mod = importlib.import_module(LENGUAJES.get(idioma, ""))
except Exception as e:
    print(json.dumps({"status": "unsupported",
                      "motivo": "sin binding para %s: %s" % (idioma, e)}))
    raise SystemExit(0)
try:
    lang = Language(mod.language())
except Exception:
    lang = Language(mod.language())          # tree_sitter <0.22 firma
parser = Parser(lang)
with open(camino, "rb") as fh:
    src = fh.read()
tree = parser.parse(src)

conteo = {}
errores = []
coincidencias = []

def tipo_de(nodo):
    t = nodo.type
    return t if isinstance(t, str) else str(t)

def texto_de(nodo):
    try:
        return nodo.text.decode("utf-8", "replace")
    except Exception:
        return ""

def visitar(nodo, padre=""):
    global limite
    t = tipo_de(nodo)
    conteo[t] = conteo.get(t, 0) + 1
    if nodo.type == "ERROR" or nodo.is_missing:
        errores.append({"tipo": t, "linea": nodo.start_point[0] + 1,
                        "columna": nodo.start_point[1] + 1,
                        "falta": bool(nodo.is_missing)})
    if patron and len(coincidencias) < limite:
        # MEDIDO 2026-10-15: el filtro original era `nodo.child_count == 0`
        # ("es una hoja"), y eso mete comentarios y cadenas literales, que en
        # tree-sitter SON hojas. Se filtra por TIPO, que es lo que distingue
        # "donde aparece esta cadena" de "donde esta escrita esta linea".
        if (patron in texto_de(nodo)
                and t not in NO_CODIGO
                and nodo.child_count == 0):
            coincidencias.append({"tipo": t, "linea": nodo.start_point[0] + 1,
                                  "columna": nodo.start_point[1] + 1,
                                  "padre": padre, "texto": texto_de(nodo)[:120]})
    for c in nodo.children:
        visitar(c, t)

visitar(tree.root_node)
print(json.dumps({
    "status": "ok",
    "root": tipo_de(tree.root_node),
    "bytes": len(src),
    "nodos": sum(conteo.values()),
    "por_tipo": dict(sorted(conteo.items(), key=lambda kv: -kv[1])),
    "errores_parseo": errores,
    "n_errores": len(errores),
    "coincidencias": coincidencias,
    "n_coincidencias": len(coincidencias),
}))
'''


def _venv_python() -> Optional[str]:
    if os.path.isfile(VENV_PY) and os.access(VENV_PY, os.X_OK):
        return VENV_PY
    return None


def _id_resultado(artefacto: str, backend: str, valor: Any,
                  donde: Optional[Dict[str, Any]] = None) -> str:
    """Id que NO colisiona. Regla F6.

    MEDIDO (rx_inspect, hallazgo 1627-area): un id derivado solo de
    (tipo, valor, herramienta) colisiona. Aqui el valor es un dict COMPLETO
    con el conteo de nodos, mas la ubicacion: dos ficheros con la misma
    estructura tienen el mismo conteo, y sin `artefacto` + `hash` no se
    distinguirian.
    """
    h = hashlib.sha256(
        ("%s|%s|%s|%s" % (STRUCTURAL_FACTS, artefacto, backend,
                          json.dumps(valor, sort_keys=True, default=str)))
        .encode("utf-8")).hexdigest()[:12]
    return "res_ast_parse_%s" % h


def _normalizar(d: Dict[str, Any], artefacto: str, backend: str,
                sha: str, idioma: str) -> Dict[str, Any]:
    por_tipo = d.get("por_tipo", {})
    valor = {
        "root": d.get("root"),
        "bytes": d.get("bytes"),
        "nodos": d.get("nodos"),
        "n_errores_parseo": d.get("n_errores", 0),
        "ratio_error": round(d.get("n_errores", 0) / max(d.get("nodos", 1), 1), 6),
        "funciones": por_tipo.get("function_definition", 0),
        "declaraciones": por_tipo.get("declaration", 0),
        "llamadas": sum(v for k, v in por_tipo.items()
                        if k.endswith("call_expression")),
        "asignaciones": sum(v for k, v in por_tipo.items()
                            if k.endswith("assignment_expression")),
        "sentencias_if": por_tipo.get("if_statement", 0),
        "sentencias_while": por_tipo.get("while_statement", 0),
        "tipos_distintos": len(por_tipo),
    }
    lim = [
        "source.ast_parse produce afirmacion sobre la ESTRUCTURA del texto "
        "fuente, no sobre el hardware. Que el fuente escriba un registro es "
        "una HIPOTESIS; confirmarla exige un probe.",
        "los nodos ERROR/missing del parseo (%d) se reportan, no se "
        "descartan: un AST con errores es un AST incompleto y asi se declara"
        % d.get("n_errores", 0),
    ]
    if d.get("n_errores", 0):
        lim.append("este fichero NO parseo limpio: las estructuras dentro de "
                   "los nodos ERROR no son fiables")
    if d.get("n_coincidencias", 0) > 50:
        lim.append("el patron casa %d veces; `raw.coincidencias` guarda las "
                   "primeras 50 y `raw.coincidencias_truncadas` vale true. El "
                   "TOTAL esta en `raw.n_coincidencias`: usa ese numero, no el "
                   "longitud de la lista"
                   % d.get("n_coincidencias", 0))
    return {
        "result_id": _id_resultado(artefacto, backend, valor),
        "type": STRUCTURAL_FACTS,
        "value": valor,
        "source": artefacto,
        "location": {"file": os.path.basename(artefacto), "lenguaje": idioma},
        "scope": "source",
        "tool": backend,
        "tool_version": "",
        "input": {"path": artefacto, "sha256": sha},
        "timestamp": _ts(),
        "artifact": artefacto,
        "artifact_hash": sha,
        "status": "derived",
        "limitations": lim,
        # MEDIDO 2026-10-15: la version anterior publicaba SOLO la lista
        # recortada a 50. Sobre `amdgpu.h` con patron `ioctl` el producer
        # encuentra N coincidencias y se persistian las 50 primeras sin decir
        # que habia mas: un consumidor que lea `raw.coincidencias` contaria 50
        # cuando el numero real es otro. Eso es perder informacion en
        # silencio, que es peor que truncarla declarada.
        #
        # Ahora van las tres cifras: `n_coincidencias` (el total real),
        # `coincidencias` (la lista) y `coincidencias_truncadas` (si la lista
        # esta recortada). Un consumidor puede distinguir "no hay" de "hay mas
        # de las que te enseño".
        "raw": {"por_tipo": por_tipo,
                "n_errores_parseo": d.get("n_errores", 0),
                "errores_parseo": d.get("errores_parseo", [])[:20],
                "errores_parseo_truncados":
                    len(d.get("errores_parseo", [])) > 20,
                "n_coincidencias": d.get("n_coincidencias", 0),
                "coincidencias": d.get("coincidencias", [])[:50],
                "coincidencias_truncadas":
                    d.get("n_coincidencias", 0) > len(
                        d.get("coincidencias", [])[:50])},
    }


def _fuente_de_este_modulo() -> str:
    """El fuente de ESTE modulo, para el guard de lecciones.

    Se relee del disco en vez de usar `inspect`: si el fichero se ha editado
    pero el proceso tiene el modulo cacheado, lo que importa es lo que hay
    escrito, no lo que se importo.
    """
    try:
        with open(os.path.abspath(__file__), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def parsear(artefacto: str, lenguaje: str = "c", patron: str = "",
            limite: int = 100, backend_id: str = "tree-sitter",
            timeout: int = 300) -> Dict[str, Any]:
    """La operacion. Devuelve SIEMPRE los seis canales del contrato.

    Las lecciones de `backends.lessons` se EJECUTAN aqui, no se citan: este
    es el punto donde las siete de RXRE-ECO-001 habrian evitado un bug cada
    una. Concretamente `contraviene()` comprueba que este modulo no repite
    los patrones que ya se pagaron, y devuelve `blocked` si lo hace.
    """
    # --- LECCIONES EJECUTADAS, NO CITADAS (AGUA) -------------------------
    # MEDIDO: estas siete lecciones costaron una tarde cada una. Un modulo
    # de lecciones que solo se lee no evita nada; una que se IMPORTA y cuya
    # violacion devuelve `blocked` si.
    try:
        from backends import lessons as _L
        prohibido = _L.contraviene(_fuente_de_este_modulo())
        if prohibido:
            return {"status": BK_BLOCKED,
                    "precheck": {"ok": False, "lecciones_violadas": prohibido},
                    "limitations": [
                        "el propio adapter repite un patron que ya se pago: "
                        "L%d %s" % (prohibido[0], prohibido[1])]}
    except Exception:
        # Si el modulo de lecciones no se puede cargar, NO se bloquea la
        # operacion: el guard es una ayuda, no un permiso. Bloquear aqui
        # dejaria el sistema inservible por un import fallido.
        pass

    ent = None
    try:
        from backends import registry
        ent = registry.get(backend_id)
        b: Backend = ent["backend"]
    except Exception:
        b = Backend(backend_id, None, None)

    # --- PRE-EXECUTION CONTRACT CHECK (§15/§26). Antes de invocar. --------
    py = _venv_python()
    pre = {
        "input_existe": os.path.isfile(artefacto),
        "input_legible": False,
        "input_hash": "",
        "lenguaje_pedido": lenguaje,
        "lenguaje_tiene_binding": lenguaje in LENGUAJES,
        "venv_aislado": bool(py),
        "venv_python": py or "",
        "ok": False,
    }
    if not pre["input_existe"]:
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": ["la entrada no existe: %s" % artefacto]}
    if not pre["lenguaje_tiene_binding"]:
        return {"status": BK_UNSUPPORTED, "precheck": pre,
                "limitations": [
                    "no hay binding medido para el lenguaje %r. Los "
                    "lenguajes con producer MEDIDO en este host son: %s. "
                    "Declarar otros seria capacidad sin producer."
                    % (lenguaje, ", ".join(sorted(LENGUAJES)))]}
    if not py:
        return {"status": BK_BLOCKED, "precheck": pre,
                "limitations": [
                    "no existe el venv aislado %s con los bindings de "
                    "tree-sitter. Se crea con: python3 -m venv .venv/eco && "
                    ".venv/eco/bin/pip install tree_sitter tree_sitter_c"
                    % VENV]}

    try:
        with open(artefacto, "rb") as fh:
            fh.read(1)
        pre["input_legible"] = True
    except OSError as e:
        return {"status": BK_INVALID, "precheck": pre,
                "limitations": ["la entrada no se puede leer: %s" % e]}
    pre["input_hash"] = sha256_de(artefacto)
    pre["ok"] = True

    # --- EJECUCION --------------------------------------------------------
    codigo = _CODIGO_VENV.replace(
        "LENGUAJES.get(idioma, \"\")", repr(LENGUAJES.get(lenguaje, "")))
    codigo = codigo.replace(
        "NO_CODIGO = set()", "NO_CODIGO = %r" % (set(TIPOS_NO_CODIGO),))
    t0 = _t.time()
    try:
        p = subprocess.run([py, "-c", codigo],
                           input=json.dumps({"idioma": lenguaje,
                                             "camino": os.path.abspath(artefacto),
                                             "patron": patron,
                                             "limite": int(limite)}),
                           capture_output=True, text=True, timeout=timeout)
        rc, so, se = p.returncode, p.stdout or "", p.stderr or ""
        timedout = False
    except subprocess.TimeoutExpired:
        rc, so, se, timedout = None, "", "timeout a los %ds" % timeout, True

    dur = round(_t.time() - t0, 3)
    argv_repr = ["<venv>/bin/python", "-c", "<script tree_sitter>"]

    ejec = {
        "backend_id": backend_id,
        "operation": "source.ast_parse",
        "command_or_api": "tree_sitter.Parser(language).parse(bytes)",
        "argv": argv_repr,
        "exit_status": rc,
        "raw_output_len": len(so),
        "stderr": se.strip()[:400],
        "limpieza": {"aplicada": False, "caracteres_quitados": 0},
        "timeout": timedout,
        "duration_s": dur,
    }
    ident = b.identidad() if isinstance(b, Backend) else {}

    if timedout:
        ejec.update({"status": BK_BLOCKED,
                     "limitations": ["timeout a los %ds" % timeout]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: sin salida"}

    if rc != 0:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["el subproceso salio con rc=%s: %s"
                                     % (rc, (se.strip() or so.strip())[:300])]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: fallo"}

    try:
        d = json.loads(so.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError) as e:
        ejec.update({"status": BK_ERROR,
                     "limitations": ["salida no parseable: %s" % e,
                                     "stdout: %s" % so[:200]]})
        return {"status": BK_ERROR, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: no parseable"}

    if d.get("status") == "blocked":
        ejec.update({"status": BK_BLOCKED,
                     "limitations": [d.get("motivo", "sin detalle")]})
        return {"status": BK_BLOCKED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "PROVENANCE_INCOMPLETE: venv"}
    if d.get("status") == "unsupported":
        ejec.update({"status": BK_UNSUPPORTED,
                     "limitations": [d.get("motivo", "sin binding")]})
        return {"status": BK_UNSUPPORTED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "provenance": "completa: el backend=no puede"}

    nodos = d.get("nodos", 0)
    if nodos <= 1:
        ejec.update({"status": BK_EMPTY,
                     "limitations": ["el parser devolvio %d nodos: el fichero "
                                     "no tiene estructura del lenguaje pedido"
                                     % nodos]})
        return {"status": BK_EMPTY, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "raw_output": d, "results": [],
                "provenance": "completa"}

    # --- EL LENGUAJE ES EL QUE SE PIDIO? (umbral MEDIDO, no redondito) ---
    #
    # BUG MEDIDO 2026-10-15. La primera version solo miraba `nodos > 1`, con
    # lo que tree-sitter parseaba un fichero PYTHON con la gramatica de C y
    # devolvia `ok`. MEDIDO, parser C contra tres entradas:
    #
    #     amdgpu.h    nodos=7066  ERROR=10   ratio=0.0014   <- C real
    #     python      nodos=15    ERROR=1    ratio=0.0667   <- no es C
    #     markdown    nodos=29    ERROR=3    ratio=0.1034   <- no es C
    #
    # Un umbral de 1% separa con margen de ~7x a un lado y ~5x al otro. No es
    # un numero redondo por gusto: es el hueco MEDIDO entre las dos clases.
    #
    # Por que importa mas de lo que parece: `ok` significa "el producer sabe
    # esto". Si un `.py` pide `lenguaje=c` y la respuesta es `ok`, una IA lee
    # "hay 15 nodos, 1 declaracion" como una afirmacion sobre el fichero. No
    # hay nada que ver ahi: hay un parser usando el lenguaje equivocado y una
    # confianza que nadie pidio.
    #
    # Y NO se "arregla" reparseando con otro lenguaje para devolver algo: la
    # capacidad pide `c`. Si quieres Python, pide Python.
    n_err = d.get("n_errores", 0)
    ratio = n_err / max(nodos, 1)
    if ratio > UMBRAL_ERROR:
        ejec.update({
            "status": BK_UNSUPPORTED,
            "limitaciones": [
                "el fichero NO parece %s: el parser produjo %d nodos de los "
                "cuales %d son ERROR (ratio %.4f), por encima del umbral "
                "medido de %.2f. MEDIDO: un C real da 0.0014; un fichero de "
                "otro lenguaje da 0.0667 o mas. `unsupported`, no `empty`: el "
                "parser abrio el fichero y no es de este lenguaje."
                % (lenguaje, nodos, n_err, ratio, UMBRAL_ERROR),
                "no se reintenta con otro lenguaje: se pidio %r" % lenguaje,
            ],
        })
        return {"status": BK_UNSUPPORTED, "precheck": pre, "ejecucion": ejec,
                "backend": ident, "raw_output": d, "results": [],
                "lenguaje_evaluado": {"nodos": nodos, "n_errores": n_err,
                                      "ratio": round(ratio, 6)},
                "provenance": "completa: la salida EXISTE y es trazable; lo "
                              "que no se puede es interpretarla como %s"
                              % lenguaje}

    res = _normalizar(d, artefacto, backend_id, pre["input_hash"], lenguaje)
    res["tool_version"] = ident.get("tool_version", "") or (
        "tree_sitter(venv aislado)")

    prov = {
        "estado": "completa",
        "cadena": ["artefacto", "input_hash", "venv_python", "subprocess",
                   "json_stdout", "conteo_nodos", "_normalizar",
                   "result_id"],
        "artefacto": os.path.relpath(artefacto, PKG),
        "input_hash": pre["input_hash"],
        "backend_id": backend_id,
        "tool_version": res["tool_version"],
        "transformacion": "bytes -> tree_sitter.Parser.parse -> visitor "
                          "recursivo -> conteo por tipo + coincidencias",
        "normalizador": "backends.adapters.ts_ast._normalizar",
        "limitaciones": res["limitations"],
    }
    ejec.update({"status": BK_OK, "limitations": []})
    return {"status": BK_OK, "precheck": pre, "ejecucion": ejec,
            "backend": ident, "raw_output": d, "results": [res],
            "provenance": prov}


def _ts() -> str:
    return _t.strftime("%Y-%m-%dT%H:%M:%S%z")


def persistir(env: Dict[str, Any], db: Optional[Any] = None,
              question: str = "") -> Optional[str]:
    """Guarda la operacion para que `explain` pueda reconstruirla.

    B3: el target es `source:<nombre>@<hash>`, NO un PCI. Una lectura de fuente
    NO toca la RX550: firmarlo como target de GPU seria una evidencia que no
    ha ocurrido.
    """
    from core import store as S
    _abierta = db is None
    c = db or S.conectar()
    ids = [r["result_id"] for r in env.get("results") or []
           if isinstance(r, dict) and r.get("result_id")]
    for i in ids:
        if c.execute("SELECT 1 FROM results WHERE result_id=?", (i,)).fetchone():
            if _abierta:
                c.close()
            return "COLISION:%s" % i
    pre = env.get("precheck") or {}
    res0 = (env.get("results") or [{}])[0] if env.get("results") else {}
    artefacto = res0.get("source") or ""
    base = os.path.basename(artefacto)
    target = "source:%s@%s" % (base, pre.get("input_hash", "")[:16])
    op_id = S.registrar(
        c,
        {"request_id": "",
         "question": question or ("parsear AST de %s" % (base or "artefacto")),
         "capability": "source.ast_parse", "scope": "source", "target": target},
        {"operation": "source.ast_parse", "status": env.get("status"),
         "backend": env.get("backend"), "ejecucion": env.get("ejecucion"),
         "provenance": env.get("provenance"), "precheck": pre,
         "results": env.get("results") or []},
        duracion=(env.get("ejecucion") or {}).get("duration_s", 0))
    if _abierta:
        c.close()
    return op_id
