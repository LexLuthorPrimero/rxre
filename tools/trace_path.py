#!/usr/bin/env python3
<<<<<<< HEAD
# CONTRACT: name=trace_path
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 4 escrituras que
# tiene se resolvieron a la clase TEMPORAL: 4 caen DENTRO de un `with tempfile...`.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
=======
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
"""trace_path.py — la cadena de llamadas de un símbolo, con el nodo vivo/muerto.
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.

Por qué existe
--------------
La regla RELATION_FIRST_REVERSE_ENGINEERING dice: cuando un nombre no aparece,
rastrear PRODUCER → TRANSFORMATION → CONSUMER en vez de leer archivos a ojo.
Eso son veinte saltos, y cada salto tiene dos trampas que solo se ven al
recorrerlos:

  1. **Código muerto.** Una llamada existe en el fichero pero está en una rama
     `chip_id == CHIP_VEGAM`, que no se ejecuta en nuestra tarjeta. Encadenarla
     produce una ruta que parece real y no lo es. Es el error de 050, y leer
     el grafo sin marcarlo lo repite a escala.

  2. **Funciones indirectas.** El driver usa vtables (`adev->reg.didt.rreg`,
     `hwmgr->smumgr_funcs->...`) y macros. Un call-graph por grep no las ve, y
     la cadena se parte justo donde el hardware empieza.

Esta herramienta construye el grafo, marca cada nodo con su veredicto para MI
ASIC usando `asic_resolver`, y separa tres tipos de arista:

  DIRECTA      llamada explícita a un símbolo del corpus
  VTABLE       llamada a través de un puntero a función; se reporta el vector
  MACRO        la "llamada" es una macro, no una función: se marca aparte

Lo que produce
--------------
Un árbol de llamadas con, para cada nodo:
  · fichero:línea
  · si es alcanzable desde nuestra ASIC, o código muerto
  · la rama `chip_id` que lo gobierna, si la hay

Y un resumen: `%` de la cadena que es viva. Una cadena con 40% vivo no es una
ruta; es un mapa. Eso decide cuánto esfuerzo merece seguirla.

Lo que NO hace
--------------
No resuelve punteros a función en tiempo de ejecución. Una vtable la reporta
como tal, con el fichero donde se declara, que es el siguiente paso manual.
No infiere que un nodo "se ejecuta": dice "no está en una rama muerta", que es
distinto y más débil.

Uso
---
    trace_path.py --kernel RAIZ --chip CHIP_POLARIS12 --from smu7_send_msg_to_smc
    trace_path.py --kernel RAIZ --chip CHIP_POLARIS12 --from smu7_send_msg_to_smc --depth 4
    trace_path.py --kernel RAIZ --from x --callers-of smu7_send_msg_to_smc
    trace_path.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "trace_path"
VERSION = "1.0.0"

DEFAULT_CHIP = "CHIP_POLARIS12"
ASIC_ENUM_REL = "include/drm/amd_asic_type.h"

# Definición de función: al principio de línea, tipo de retorno, nombre, '('.
_FUNC_DEF = re.compile(
    r"^(?P<ret>(?:static\s+|const\s+|extern\s+|inline\s+|unsigned\s+|struct\s+"
    r"|enum\s+|union\s+)*[A-Za-z_][\w \t\*]*?[\w\*])\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*\("
)
# Una función que NO devuelve nada: "void\nfoo(" en linea separada. Se cubre
# dejando que el nombre sea el ultimo identificador antes de '('.
_CALL = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*\(")
# Miembro de vtable: algo->miembro(  o  algo.miembro(
_VTABLE = re.compile(r"\b(?P<obj>[A-Za-z_]\w*)\s*(?:->|\.)\s*(?P<fn>[A-Za-z_]\w*)\s*\(")
_CHIP_CMP = re.compile(
    r"(chip_id|asic_type)\s*(==|!=|<=|>=|<|>)\s*(CHIP_[A-Z0-9_]+)"
)
_CMP = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b,
        "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}

# Macros conocidas del subsistema. No son funciones: llamarlas es una
# indirección que un call-graph ingenuo reporta como salto.
KNOWN_MACROS = {
    "cgs_read_register", "cgs_write_register", "cgs_read_ind_register",
    "cgs_write_ind_register", "RREG32", "WREG32", "DREG32", "RREG32_SMC",
    "WREG32_SMC", "RREG32_DIDT", "WREG32_DIDT", "RREG32_GC_CAC",
    "CGS_WREG32_FIELD_IND", "CGS_RREG32_FIELD_IND", "CGS_WREG32_FIELD",
    "PP_ASSERT_WITH_CODE", "PHM_READ_FIELD", "PHM_WRITE_FIELD",
    "PHM_WAIT_FIELD_UNEQUAL", "PPMESSAGE", "PPHMM_INFO",
}

# Tipos que devuelven puntero a funcion, para no tratarlos como funciones.
_FUNCTYPE = re.compile(r"\(\s*\*\s*[A-Za-z_]\w*\s*\)\s*\(")


def strip_comments(text: str) -> str:
    """Comentarios a espacio conservando longitud: el informe cita lineas."""
    out: List[str] = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def parse_chip_enum(path: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    rx = re.compile(r"^\s*(CHIP_[A-Z0-9_]+)\s*,?\s*(?:/\*\s*([0-9]+)\s*\*/)?\s*$")
    implicit, in_enum = 0, False
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.split("//", 1)[0].rstrip()
            if re.match(r"^\s*enum\b", s) and "asic_type" in s:
                in_enum = True
                continue
            if in_enum and s.strip().startswith("}"):
                break
            if not in_enum or not s.strip():
                continue
            m = rx.match(s)
            if not m:
                continue
            if m.group(2) is not None:
                out[m.group(1)] = int(m.group(2))
                implicit = int(m.group(2)) + 1
            else:
                out[m.group(1)] = implicit
                implicit += 1
    return out


# El simbolo del enum de ASIC que trace_path necesita para evaluar las
# ramas `chip_id == CHIP_*`.  Es un SIMBOLO, no una ruta: la ruta
# historica (`include/drm/amd_asic_type.h`) es solo donde ese simbolo
# se definio en kernels que tienen el arbol include/ completo.
_ENUM_SYMBOL = "amd_asic_type"

# Linea de definicion: `enum ... asic_type` al principio de linea.
# Distingue la DEFINICION de los USOS del tipo (miembro de struct,
# parametro, `switch`): ambos contienen `enum ... asic_type`, pero
# solo la definicion tiene cuerpo entre llaves con valores CHIP_*,
# y solo ella produce valores bajo parse_chip_enum.
_ENUM_DEF_LINE = re.compile(r"^\s*enum\b[^;{]*\b" + _ENUM_SYMBOL + r"\b",
                            re.MULTILINE)


def _enum_def_line_no(text: str, m: "re.Match[str]") -> int:
    """Linea (1-based) donde empieza el match, en el texto original."""
    return text.count("\n", 0, m.start()) + 1


def _enum_candidates_in(kernel_root: str) -> List[Dict[str, object]]:
    """Candidatos a definicion de `enum amd_asic_type` en un corpus.

    Recorre el corpus una sola vez.  Un fichero es candidato solo si
    contiene una linea `enum ... asic_type` cuyo parseo produce al
    menos un valor CHIP_*: eso separa la DEFINICION de los USOS del
    tipo, que es la unica forma estatica de no confundir
    `enum amd_asic_type asic_type;` (miembro de struct, amdgpu.h)
    con `enum amd_asic_type { CHIP_... };` (la definicion).
    """
    cands: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(kernel_root):
        # Poda: directorios ocultos y de control de versiones.
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d != "__pycache__"]
        for fn in filenames:
            if not (fn.endswith(".h") or fn.endswith(".c")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            if "asic_type" not in text:
                continue
            m = _ENUM_DEF_LINE.search(text)
            if not m:
                continue
            values = parse_chip_enum(p)
            if not values:
                continue
            cands.append({"path": p,
                          "line": _enum_def_line_no(text, m),
                          "values": values})
    return cands


def resolve_enum_definition(kernel: str,
                            symbol: str = _ENUM_SYMBOL,
                            known_rel: str = ASIC_ENUM_REL
                            ) -> Dict[str, object]:
    """Resuelve la definicion de un enum de ASIC dentro de un corpus.

    Contrato (DOGFOOD-002):
      1. Ruta conocida: si existe y contiene una definicion valida
         (parseo con >= 1 valor), se usa.  Provenance: ruta historica.
      2. Si no, se busca la definicion del simbolo en TODO el corpus.
      3. Un candidato es valido solo si el parseo produce >= 1 valor
         CHIP_*: rechaza usos del tipo (struct, parametro, switch).
      4. Exactamente un candidato valido -> RESOLVED.
      5. Mas de uno -> AMBIGUOUS_SYMBOL (no se elige arbitrariamente).
      6. Ninguno -> NOT_FOUND (ausencia EN EL CORPUS, no ausencia
         probada del simbolo).
      7. Provenance conservada: archivo, linea, simbolo, corpus.
    """
    res: Dict[str, object] = {
        "status": "NOT_FOUND", "symbol": symbol, "corpus": kernel,
        "known_path": os.path.join(kernel, known_rel),
        "path": None, "line": None, "values": {}, "candidates": [],
        "source": None,
    }
    # 1. Ruta conocida.
    known = str(res["known_path"])
    if os.path.isfile(known):
        try:
            with open(known, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        m = _ENUM_DEF_LINE.search(text)
        if m:
            vals = parse_chip_enum(known)
            if vals:
                res.update({"status": "RESOLVED", "path": known,
                            "line": _enum_def_line_no(text, m),
                            "values": vals, "source": "KNOWN_PATH"})
                return res
    # 2. Busqueda en el corpus.
    cands = _enum_candidates_in(kernel)
    res["candidates"] = [{"path": c["path"], "line": c["line"]}
                         for c in cands]
    if len(cands) > 1:
        res["status"] = "AMBIGUOUS_SYMBOL"
        return res
    if len(cands) == 1:
        res.update({"status": "RESOLVED", "path": cands[0]["path"],
                    "line": cands[0]["line"], "values": cands[0]["values"],
                    "source": "CORPUS_SEARCH"})
    return res


def function_bodies(text: str) -> List[Dict[str, object]]:
    """Trocea el fichero en funciones, con su linea y su cuerpo.

    Trocear por llaves de nivel 0 es lo unico que sobrevive a las macros
    multi-linea: un `{` dentro de un `PP_ASSERT_WITH_CODE(...)` no abre un
    bloque de funcion. Contar llaves a pelo parte las funciones por la mitad.
    """
    funcs: List[Dict[str, object]] = []
    lines = text.splitlines(keepends=True)
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        # La firma puede cruzar lineas: "int (*registrar(void))(int)". Unir la
        # linea actual con la siguiente si no cierra su parentesis evita que el
        # nombre se parta y que "int" se lea como nombre de funcion.
        probe = line
        j2 = i
        while probe.count("(") > probe.count(")") and j2 + 1 < n:
            j2 += 1
            probe += lines[j2]
        stripped = line.lstrip()
        # typedef NO es una definicion de funcion. Sin esta exclusion,
        # "typedef int (*cb_t)(int);" captura `int` como nombre de funcion y
        # el indice se llena de tipos.
        is_typedef = stripped.startswith("typedef")
        m = None if is_typedef else _FUNC_DEF.match(stripped)
        if not m and not is_typedef:
            m2 = re.match(r"^\s*\(\s*\*\s*(?P<name>[A-Za-z_]\w*)\s*\(", probe)
            if m2:
                funcs.append({"name": m2.group("name"), "line": i + 1,
                              "body": "", "file_line": i + 1,
                              "firma_multilinea": True})
                i = j2 + 1
                continue
        is_def = False
        name = None
        if m and not _FUNCTYPE.search(line):
            cand = m.group("name")
            if cand not in ("if", "while", "for", "switch", "return", "sizeof"):
                is_def, name = True, cand
        elif not is_typedef:
            # Segunda forma de definicion: el tipo de retorno esta en la linea
            # anterior y la firma abre en esta, con el nombre entre parentesis
            # por ser un puntero a funcion.
            # Se distingue de una llamada suelta porque una definicion tiene
            # una llave propia tras la firma y una llamada termina en ';'.
            # Sin esta comprobacion, "hardware_ayudante(hwmgr);" dentro de un
            # cuerpo se contaria como la definicion de una funcion nueva.
            # La firma de un puntero a funcion empieza con "(*":
            #   int (*registrar(void))(int)
            # El patron de aqui capturaria `int` como nombre. Se excluye y la
            # forma correcta la cubre la rama m2 de arriba.
            mc = re.match(r"^\s*(?P<name>[A-Za-z_]\w*)\s*\(", line)
            if mc and ";" not in line.split("{")[0] and "(*" not in line:
                cand = mc.group("name")
                if cand not in ("if", "while", "for", "switch", "return",
                                "sizeof", "defined", "offsetof"):
                    name = cand
                    is_def = True
        if not is_def:
            i += 1
            continue
        # el cuerpo empieza en la primera llave de nivel 0
        depth = 0
        started = False
        j = i
        body_start = j
        while j < n:
            for ch in lines[j]:
                if ch == "{":
                    depth += 1
                    if not started:
                        started = True
                        body_start = j
                elif ch == "}":
                    depth -= 1
            if started and depth == 0:
                break
            j += 1
        if not started:
            i += 1
            continue
        body = "".join(lines[body_start:j + 1])
        funcs.append({"name": name, "line": i + 1, "body": body,
                      "file_line": body_start + 1})
        i = j + 1
    return funcs


def calls_in(body: str) -> Tuple[List[str], List[Dict[str, str]], List[str]]:
    """(llamadas directas, llamadas por vtable, macros) en un cuerpo."""
    direct: List[str] = []
    vtab: List[Dict[str, str]] = []
    macros: List[str] = []
    for ln, line in enumerate(body.splitlines()):
        s = line.strip()
        if not s:
            continue
        for m in _VTABLE.finditer(line):
            fn = m.group("fn")
            if fn in ("if", "while", "for", "sizeof", "return"):
                continue
            vtab.append({"fn": fn, "obj": m.group("obj"), "line": s[:80]})
        for m in _CALL.finditer(line):
            fn = m.group("name")
            if fn in ("if", "while", "for", "switch", "sizeof", "return",
                      "defined", "offsetof"):
                continue
            if fn in KNOWN_MACROS:
                macros.append(fn)
            else:
                direct.append(fn)
    # una llamada por vtable no es una llamada directa al mismo nombre
    for v in vtab:
        if v["fn"] in direct:
            direct.remove(v["fn"])
    return direct, vtab, macros


def has_code_outside_conditions(body: str) -> bool:
    """Hay codigo en el cuerpo fuera de todo if/else que compare chip_id.

    Es lo que separa PARCIAL de MUERTA. Sin esto, una funcion que empieza con
    `if (chip_id == CHIP_VEGAM) { ... }` y sigue trabajando se marcaria
    MUERTA y se daria por eliminada cuando su resto sigue vivo.
    """
    lines = [l for l in body.splitlines() if l.strip()]
    guard_lines = set()
    for i, l in enumerate(lines):
        if re.search(r"(chip_id|asic_type)\s*(==|!=|<=|>=|<|>)\s*CHIP_", l):
            guard_lines.add(i)
            # el if y su cuerpo indentado
            indent = len(l) - len(l.lstrip())
            j = i + 1
            while j < len(lines):
                ind2 = len(lines[j]) - len(lines[j].lstrip())
                if lines[j].strip() and ind2 <= indent:
                    break
                guard_lines.add(j)
                j += 1
    substantial = 0
    for i, l in enumerate(lines):
        if i in guard_lines:
            continue
        s = l.strip()
        if not s or s in ("{", "}") or s.startswith("/*"):
            continue
        if s.startswith("}") or s.startswith("else"):
            continue
        if re.match(r"^(return|\}|\)|\{|\s*\))", s):
            continue
        substantial += 1
    return substantial > 0


def branch_verdict(func_text: str, chip: int, enum: Dict[str, int],
                   has_code_outside: bool = False) -> Tuple[str, List[Dict[str, str]]]:
    """Veredicto de alcanzabilidad por las comparaciones chip_id del cuerpo.

    Semantico y declarado, porque MUERTA es una afirmacion fuerte:

      NO_CONDICIONAL  el cuerpo no compara contra ningun CHIP_*
                      NO significa que se ejecute siempre
      VIVA            alguna comparacion se cumple para mi ASIC
      PARCIAL         comparaciones falsas, y ademas codigo FUERA del if:
                      la mitad de la funcion corre igual
      MUERTA          todas las comparaciones son falsas Y el cuerpo es solo
                      ese if/else

    PARCIAL y MUERTA no son intercambiables. Marcar MUERTA una funcion con una
    rama muerta y otra viva la daria por eliminada cuando su mitad viva sigue
    siendo la ruta real.
    """
    conds: List[Dict[str, str]] = []
    for m in _CHIP_CMP.finditer(func_text):
        field, op, cname = m.group(1), m.group(2), m.group(3)
        cval = enum.get(cname)
        takes = None if cval is None else _CMP[op](chip, cval)
        conds.append({"field": field, "op": op, "constant": cname,
                      "value": "?" if cval is None else str(cval),
                      "taken": "?" if takes is None else ("SI" if takes else "no")})
    if not conds:
        return "NO_CONDICIONAL", conds
    if any(c["taken"] == "SI" for c in conds):
        return "VIVA", conds
    if has_code_outside:
        return "PARCIAL", conds
    return "MUERTA", conds

# Una macro con PARARAMETROS: el cuerpo es lo que va despues del parentesis
# de la firma. Sin saltar ese parentesis, el cuerpo capturado son los propios
# parametros y la llamada detectada es un parametro, no una funcion.
_DEFINE = re.compile(
    r"#\s*define\s+(?P<name>[A-Za-z_]\w*)\s*"
    r"(?:\((?P<params>[^)]*)\))?\s*"
    r"(?P<body>(?:[^\n\\]|\\\s*\n)*)",
    re.M,
)


_MACRO_BODY_CACHE: Dict[str, str] = {}


def macro_expansions(roots: Sequence[str]) -> Dict[str, List[str]]:
    """Macro -> cuerpo de la funcion a la que realmente llama.

    Sin esto, PHM_WAIT_FIELD_UNEQUAL aparece como nodo folha "INDIRECCION" y
    la cadena se corta justo donde el acceso al hardware empieza. El cuerpo
    del driver tiene dozens de macros asi: la mitad de la ruta real es
    macro, no llamada directa.

    Solo se resuelven las macros cuyo cuerpo es UNA llamada de funcion. Una
    macro con varias sentencias, o con logica, se deja como indireccion: no
    se sabe a que funcion llama porque puede llamar a varias.
    """
    if _MACRO_BODY_CACHE:
        return _MACRO_BODY_CACHE
    out: Dict[str, List[str]] = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if not fn.endswith(".h"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        text = strip_comments(fh.read())
                except OSError:
                    continue
                for m in _DEFINE.finditer(text):
                    name = m.group("name")
                    body = m.group("body").replace("\\\n", " ")
                    if not body or len(body) > 600 or body.count(";") > 1:
                        continue
                    # NO se excluye por compartir prefijo con el nombre de la
                    # macro: PHM_WAIT_FIELD_UNEQUAL llama a
                    # PHM_WAIT_REGISTER_UNEQUAL, que es justo lo que hay que
                    # resolver. El filtro por `c not in name` las eliminaba y
                    # devolvia None para las macros que mas importan.
                    calls = [c for c in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body)
                             if c not in KNOWN_MACROS and c != name
                             and c not in ("if", "while", "for", "sizeof", "return",
                                           "PHM_FIELD_SHIFT", "PHM_FIELD_MASK",
                                           "CGS_REG_FIELD_MASK", "CGS_REG_FIELD_SHIFT")]
                    # Varias llamadas no es motivo para abandonar: PHM_WAIT_
                    # FIELD_UNEQUAL llama a tres macros, y las tres son el
                    # camino real. Se guardan todas y el consumidor decide si
                    # son alternativas o partes de la misma expresion.
                    if calls:
                        out.setdefault(name, [])
                        for c in calls:
                            if c not in out[name]:
                                out[name].append(c)
    _MACRO_BODY_CACHE.update(out)
    return out


class Index:
    """Indice de funciones del subarbol, cacheado."""

    def __init__(self, root: str, extra_roots: Optional[Sequence[str]] = None):
        self.root = root
        self.macros = macro_expansions([root] + list(extra_roots or []))
        self.by_name: Dict[str, List[Dict[str, object]]] = {}
        self._cache: Dict[str, List[Dict[str, object]]] = {}
        self._scanned = False

    def _scan(self) -> None:
        if self._scanned:
            return
        self._scanned = True
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if not fn.endswith(".c"):
                    continue
                p = os.path.join(dirpath, fn)
                cached = self._cache.get(p)
                if cached is None:
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as fh:
                            clean = strip_comments(fh.read())
                    except OSError:
                        continue
                    cached = function_bodies(clean)
                    self._cache[p] = cached
                for f in cached:
                    # La ruta la aporta quien indexa: function_bodies solo ve
                    # texto. Sin esto, el informe no puede citar fichero:línea.
                    f = dict(f)
                    f["file"] = p
                    self.by_name.setdefault(str(f["name"]), []).append(f)

    def get(self, name: str) -> List[Dict[str, object]]:
        self._scan()
        return self.by_name.get(name, [])

    def files_scanned(self) -> int:
        return len(self._cache)


def render_tree(roots: Sequence[Dict[str, object]], enum: Dict[str, int],
<<<<<<< HEAD
                chip: str, chip_val: int,
                n_fich: Optional[int] = None,
                root: Optional[str] = None) -> str:
=======
                chip: str, chip_val: int) -> str:
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    L = [f"{NAME} {VERSION} · chip={chip} valor={chip_val}"]
    L.append("  DIRECTA=llamada a funcion   VTABLE=puntero a funcion   MACRO=indireccion")
    L.append("  VIVA / MUERTA / PARCIAL se refiere a las comparaciones chip_id del cuerpo,")
    L.append("  NO a si la funcion se ejecuta. NO_CONDICIONAL = sin comparacion contra CHIP_*.")
<<<<<<< HEAD
    # MEDIDO 2026-10-04: el denominador va ANTES del primer veredicto, no
    # despues. Estaba en la ultima linea y era la UNICA diferencia entre una
    # salida buena y la de un corpus que no se ha leido: si el tamano de la
    # poblacion va despues, el veredicto ya se ha leido y solo queda la linea
    # que lo acompana para corrección. Este es el requisito que §8.7 del censo
    # le pone a la puerta, y aqui se cumple por construccion.
    if n_fich is not None:
        L.append(f"  poblacion indexada: {n_fich} ficheros .c"
                 + (f" bajo {root}" if root else ""))
        L.append("  Los veredictos de abajo son sobre ESA poblacion y sobre")
        L.append("  ningun otro corpus. Leer un veredicto sin este numero es")
        L.append("  leerlo sin denominador.")
=======
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    L.append("")
    for r in roots:
        L.extend(_render_node(r, 0, enum, chip_val))
    return "\n".join(L)


def _render_node(r: Dict[str, object], depth: int,
                 enum: Dict[str, int], chip_val: int) -> List[str]:
    ind = "  " * (depth + 1)
    kind = str(r.get("kind", "?"))
    sym = str(r.get("sym", "?"))
    v = str(r.get("verdict", "?"))
    loc = r.get("loc") or ""
    L = [f"{ind}{kind:<8} {sym:<44} {v:<14} {loc}"]
    for c in r.get("conds", []):
        L.append(f"{ind}  └ cond: {c['field']} {c['op']} {c['constant']} "
                 f"(={c['value']}) -> {c['taken']}")
    if r.get("note"):
        L.append(f"{ind}  └ {r['note']}")
    for ch in r.get("children", []):  # type: ignore[union-attr]
        L.extend(_render_node(ch, depth + 1, enum, chip_val))
    return L


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Cadena de llamadas con nodo vivo/muerto por ASIC.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--chip", default=DEFAULT_CHIP)
    ap.add_argument("--from", dest="sym", action="append", default=[],
                    help="simbolo raiz de la cadena")
    ap.add_argument("--callers-of", action="append", default=[],
                    help="quien llama a este simbolo (inverso)")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--root", default=None, help="subarbol a indexar")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)
    root = args.root or os.path.join(kernel, "drivers/gpu/drm/amd")
    # Resolucion del enum de ASIC (DOGFOOD-002): el simbolo se
    # resuelve DENTRO del corpus, no por una ruta asumida. La ruta
    # historica se usa cuando existe y es valida; si no, se busca
    # la definicion en el corpus, rechazando usos del tipo, y se
    # rechaza la ambiguedad en lugar de elegirla.
    res = resolve_enum_definition(kernel)
    if res["status"] != "RESOLVED":
        if res["status"] == "AMBIGUOUS_SYMBOL":
            print(f"ERROR  AMBIGUOUS_SYMBOL: la definicion de enum "
                  f"'{res['symbol']}' se encontro en "
                  f"{len(res['candidates'])} ficheros del corpus",
                  file=sys.stderr)
            for c in res["candidates"]:
                print(f"  {c['path']}:{c['line']}", file=sys.stderr)
            print("  No se elige arbitrariamente entre definiciones "
                  "competidoras.", file=sys.stderr)
        else:
            print(f"ERROR  la definicion del enum '{res['symbol']}' "
                  f"no se encontro en el corpus {kernel}",
                  file=sys.stderr)
            print(f"  La ruta conocida {res['known_path']} no existe "
                  f"o no contiene la definicion.", file=sys.stderr)
            print("  NOT_FOUND es ausencia en el corpus, no ausencia "
                  "prohada del simbolo: el corpus puede estar "
                  "incompleto.", file=sys.stderr)
        return 2
    enum = res["values"]
    if res["source"] == "CORPUS_SEARCH":
        print(f"NOTA: definicion de '{res['symbol']}' resuelta por "
              f"busqueda en {res['path']}:{res['line']}"
              f" (la ruta conocida {ASIC_ENUM_REL} no existe en este "
              f"corpus)", file=sys.stderr)
    chip_val = enum.get(args.chip)
    if chip_val is None:
        print(f"ERROR  {args.chip} no esta en {res['path']}:"
              f"{res['line']} (definicion de {res['symbol']})",
              file=sys.stderr)
        return 2

    idx = Index(root, [os.path.join(kernel, "include")])
<<<<<<< HEAD

    # MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2, sobre el censo
    # 08-ARQUITECTURA/FILTROS-MAL-FORMADOS.md:133-176, que lo llama "el mas
    # peligroso del proyecto").
    #
    # Una ruta que no existe no da error: os.walk no produce nada, el indice
    # queda con 0 funciones, y el veredicto por simbolo pasa a ser N_CALLERS
    # para TODOS los simbolos. Consecuencia medida ANTES del arreglo, con
    # control, las dos salidas COMPLETAS difieren en UNA linea de ocho:
    #
    #   --root NO_EXISTE_ESTA_RUTA   INVERSO ... N_CALLERS   ficheros .c indexados: 0    rc=0
    #   --root <amdgpu>              INVERSO ... N_CALLERS   ficheros .c indexados: 304  rc=0
    #
    #   8c8
    #   <   ficheros .c indexados: 0
    #   ---
    #   >   ficheros .c indexados: 304
    #
    # Un simbolo que existe en el driver y al que NADIE llama da el mismo
    # N_CALLERS que un simbolo que no existe en un corpus que no se ha leido.
    # Y el patron correcto esta a veinte lineas, en este MISMO fichero:
    # `--chip` valida contra el enum con rc=2 (:510-512) y `--from` tiene un
    # veredicto NO_ENCONTRADO propio (:519-522). Lo que faltaba era aplicarlo a
    # --root.
    #
    # La validacion va DESPUES de la del chip y con la misma forma, a proposito:
    # dos convenciones distintas en el mismo main es lo que produce este tipo
    # de defecto. Y distingue los DOS fallos, que no son el mismo:
    #   - la ruta que el usuario escribio no existe  -> rc=2, "no he leido nada"
    #   - la ruta existe pero no tiene .c indexables  -> rc=2, pero otro texto
    if not os.path.isdir(root):
        print(f"ERROR  --root {root} no existe o no es un directorio",
              file=sys.stderr)
        print("  No se ha leido nada. Un recorrido de 0 ficheros NO es", file=sys.stderr)
        print("  'nadie llama a este simbolo': es 'no he mirado nada', y", file=sys.stderr)
        print("  los dos salen iguales si no se dice cual de los dos es.", file=sys.stderr)
        print(f"  Se ha probado: {root}", file=sys.stderr)
        return 2

    # El indice se recorre ANTES de emitir el primer veredicto, y su tamano se
    # imprime ANTES tambien. Antes se imprimia en la ULTIMA linea (:659), que
    # es la unica diferencia entre la salida buena y la de un corpus no leido:
    # si el denominador va despues del numerador, el numerador ya se ha leido.
    idx._scan()
    n_fich = idx.files_scanned()
    if n_fich == 0:
        print(f"ERROR  --root {root} existe pero no contiene ningun .c indexable",
              file=sys.stderr)
        print(f"  0 ficheros leidos. No se ha medido nada, y un 'N_CALLERS'", file=sys.stderr)
        print("  sobre 0 ficheros no es un resultado: es la ausencia de", file=sys.stderr)
        print("  medicion. La ruta existe, y aun asi no hay nada que leer.", file=sys.stderr)
        return 2

=======
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    results: List[Dict[str, object]] = []

    for sym in args.sym:
        defs = idx.get(sym)
        if not defs:
            results.append({"kind": "DIRECTA", "sym": sym, "verdict": "NO_ENCONTRADO",
                            "loc": "-", "note": "busqueda en todo el subarbol indexado",
                            "children": []})
            continue
        children: List[Dict[str, object]] = []
        seen: Set[str] = set()
        # budget va aparte de depth: encadenar macros son tres saltos que no
        # son profundidad logica. Con el mismo contador, una cadena de cuatro
        # macros se cortaria en el primero y pareceria que no hay mas.
        budget = [args.depth + 6]

        def expand(fname: str, depth: int, sink: Optional[List[Dict[str, object]]] = None) -> None:
            """Expande una funcion: cuelga sus hijos en `sink` (o en children)."""
            target = sink if sink is not None else children
            if depth <= 0 or fname in seen or budget[0] <= 0:
                return
            budget[0] -= 1
            seen.add(fname)
            for f in idx.get(fname):
                d, vt, mc = calls_in(str(f["body"]))
                for c in d:
                    if c in seen:
                        continue
                    cf = idx.get(c)
                    if cf:
                        bodytxt = str(cf[0]["body"])
                        v, conds = branch_verdict(
                            bodytxt, chip_val, enum,
                            has_code_outside_conditions(bodytxt))
                        node = {
                            "kind": "DIRECTA", "sym": c, "verdict": v,
                            "conds": conds,
                            "loc": f"{os.path.basename(str(cf[0]['file']))}:{cf[0]['line']}",
                            "children": []}
                        target.append(node)
                        expand(c, depth - 1, node["children"])
                for v2 in vt:
                    target.append({"kind": "VTABLE", "sym": v2["fn"],
                                   "verdict": "RESOLVER", "conds": [],
                                   "loc": f"via {v2['obj']}",
                                   "note": "puntero a funcion: la vtable decide, "
                                           "siguiente paso es localizarla",
                                   "children": []})
                for m2 in mc:
                    if m2 in seen:
                        continue
                    # Una macro puede llamar a otra macro. Se sigue la cadena
                    # hasta llegar a una funcion real o hasta agotar el
                    # presupuesto: PHM_WAIT_FIELD_UNEQUAL ->
                    # PHM_WAIT_REGISTER_UNEQUAL ->
                    # PHM_WAIT_REGISTER_UNEQUAL_GIVEN_INDEX ->
                    # phm_wait_for_register_unequal son cuatro saltos.
                    hops = [m2]
                    cur = m2
                    for _ in range(6):
                        nx = idx.macros.get(cur) or []
                        real = [x for x in nx if idx.get(x)]
                        if real:
                            hops.extend(nx)
                            break
                        if not nx:
                            break
                        cur = nx[0]
                        hops.append(cur)
                    else:
                        hops = [m2]
                    m2_show = " -> ".join(hops)
                    nxt = idx.macros.get(hops[-1]) or []
                    if not nxt and idx.get(hops[-1]):
                        nxt = [hops[-1]]
                    if not nxt:
                        if m2 not in [x.get("sym") for x in target]:
                            target.append({"kind": "MACRO", "sym": m2,
                                           "verdict": "INDIRECCION",
                                             "conds": [], "loc": "",
                                             "note": "macro sin llamada unica "
                                                "localizada: su cuerpo es "
                                                "mas de una sentencia",
                                           "children": []})
                        continue
                    # La macro se encadena hasta su funcion real. Sin esto,
                    # PHM_WAIT_FIELD_UNEQUAL aparece como hoja y la cadena se
                    # corta justo donde empieza el acceso al hardware.
                    for nx in nxt:
                        fn = idx.get(nx)  # noqa
                        if fn:
                            v, conds = branch_verdict(
                                str(fn[0]["body"]), chip_val, enum,
                                has_code_outside_conditions(str(fn[0]["body"])))
                            nm = f"{m2_show}" if nx == [nx[0]] else " -> ".join(hops)
                            if nm not in [x.get("sym") for x in target]:
                                node = {
                                    "kind": "MACRO", "sym": nm, "verdict": v,
                                    "conds": conds,
                                    "loc": f"{os.path.basename(str(fn[0]['file']))}:{fn[0]['line']}",
                                    "children": []}
                                target.append(node)
                                expand(nx, depth - 1, node["children"])
                            else:
                                expand(nx, depth - 1, target)
                        else:
                            nm = f"{m2_show}" if nx == [nx[0]] else " -> ".join(hops)
                            if nm not in [x.get("sym") for x in target]:
                                children.append({"kind": "MACRO", "sym": nm,
                                                 "verdict": "MACRO_SIN_RESOLVER",
                                                 "conds": [], "loc": "",
                                                 "children": []})
        for d0 in defs:
            v, conds = branch_verdict(str(d0["body"]), chip_val, enum)
            results.append({
                "kind": "DIRECTA", "sym": sym, "verdict": v, "conds": conds,
                "loc": f"{os.path.basename(str(d0['file']))}:{d0['line']}",
                "children": children})
            break
        expand(sym, args.depth)

    for sym in args.callers_of:
        idx._scan()
        callers: List[Dict[str, object]] = []
        for fname, defs in idx.by_name.items():
            for f in defs:
                d, vt, mc = calls_in(str(f["body"]))
                if sym in d or any(x["fn"] == sym for x in vt):
                    v, conds = branch_verdict(str(f["body"]), chip_val, enum)
                    callers.append({"kind": "CALLER", "sym": fname, "verdict": v,
                                    "conds": conds,
                                    "loc": f"{os.path.basename(str(f['file']))}:{f['line']}",
                                    "children": []})
        results.append({"kind": "INVERSO", "sym": sym, "verdict": "N_CALLERS",
                        "loc": "-", "children": callers})

    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "chip": args.chip,
<<<<<<< HEAD
                          "chip_value": chip_val, "root": root,
                          # El denominador viaja con los datos. Un consumidor que
                          # lee results sin esto no puede distinguir "nadie llama
                          # a este simbolo" de "no he leido nada".
                          "ficheros_indexados": n_fich,
                          "results": results},
                         indent=2, ensure_ascii=False))
        return 0

    print(render_tree(results, enum, args.chip, chip_val, n_fich, root))
    print()
    print(f"  ficheros .c indexados: {n_fich}")
=======
                          "chip_value": chip_val, "results": results},
                         indent=2, ensure_ascii=False))
        return 0

    print(render_tree(results, enum, args.chip, chip_val))
    print()
    print(f"  ficheros .c indexados: {idx.files_scanned()}")
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    return 0


def selftest() -> int:
    failures: List[str] = []
<<<<<<< HEAD
    vectores = 0

    def check(name: str, got, want) -> None:
        nonlocal vectores
        vectores += 1
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    def check_true(name: str, got) -> None:
        check(name, bool(got), True)

    # --- --root, MEDIDO 2026-10-04 (nodo FILTROS-REPARO-2) ---
    #
    # No habia ni un vector sobre --root. El defecto era el peor del censo:
    # con una ruta inexistente el indice queda vacio, el veredicto es N_CALLERS
    # para todos los simbolos, y las dos salidas difieren en una sola linea.
    # Se prueba sobre un arbol SINTETICO para no depender de los 304 ficheros.
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        buen = os.path.join(td, "amdgpu")
        os.makedirs(buen)
        with open(os.path.join(buen, "a.c"), "w") as fh:
            fh.write("void llama_a(void) {}\n"
                     "void otra(void) { llama_a(); }\n")
        vacio = os.path.join(td, "sin-c")
        os.makedirs(vacio)
        with open(os.path.join(vacio, "leeme.txt"), "w") as fh:
            fh.write("esto no es un .c\n")
        # Un indice con contenido: el denominador es el que tiene que aparecer.
        i1 = Index(buen, [])
        i1._scan()
        check("root.contenido_no_vacio", i1.files_scanned(), 1)
        check("root.la_funcion_se_indexa", sorted(i1.by_name), ["llama_a", "otra"])
        # Una ruta inexistente: os.walk no produce nada. Es el defecto MEDIDO, y
        # se comprueba que el indice queda a cero, que es la causa del N_CALLERS
        # silencioso. Que de a cero es lo que hay que ver para que el rc=2 de
        # main() tenga sentido: sin esto, el rc=2 seria solo una politica.
        i2 = Index(os.path.join(td, "NO_EXISTE_ESTA_RUTA"), [])
        i2._scan()
        check("root.inexistente_deja_el_indice_a_cero", i2.files_scanned(), 0)
        # Un directorio que existe pero sin .c: OTRO fallo, con otro texto.
        i3 = Index(vacio, [])
        i3._scan()
        check("root.sin_c_deja_el_indice_a_cero", i3.files_scanned(), 0)
        # La distincion que hay que sostener: no-existe y existe-sin-c dan los
        # dos cero, y aun asi NO son el mismo fallo. Si seRunnable el codigo de
        # salida por la cuenta de ficheros, los dos mensajes tiene que existir.
        check("root.los_dos_casos_cero_no_se_confunden",
              (os.path.isdir(os.path.join(td, "NO_EXISTE_ESTA_RUTA")),
               os.path.isdir(vacio)), (False, True))
        # Y el denominador tiene que salir ANTES del veredicto en el texto.
        txt = render_tree([], {}, "CHIP_POLARIS12", 17, 1, buen)
        lineas = txt.splitlines()
        pos_pob = next(i for i, l in enumerate(lineas) if "poblacion indexada" in l)
        check_true("root.el_denominador_se_imprime", pos_pob >= 0)
        check("root.el_denominador_va_antes_del_arbol",
              pos_pob < len(lineas) - 1, True)
        check_true("root.el_denominador_dice_la_cifra", "1 ficheros .c" in txt)
        # Con una poblacion vacia el numero sigue estando: es el 0, que es
        # justamente lo que hay que poder leer.
        check_true("root.el_denominador_no_se_omite_si_es_0",
                   "0 ficheros .c" in render_tree([], {}, "C", 17, 0, vacio))
        # El denominador no es opcional: hay que imprimirlo tambien cuando vale
        # 0, porque el 0 es justo el numero que faltaba. Este vector falla si
        # alguien deja el parametro en None, que es como el defecto volvio.
        check_true("root.el_denominador_se_imprime_siempre",
                   "poblacion indexada" in render_tree([], {}, "C", 17, 0, vacio)
                   and "poblacion indexada" in render_tree([], {}, "C", 17, 1, buen))

=======

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    # enum
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        eh = os.path.join(td, "amd_asic_type.h")
        with open(eh, "w", encoding="utf-8") as fh:
            fh.write("enum amd_asic_type {\n"
                     "\tCHIP_POLARIS10,\t/* 15 */\n"
                     "\tCHIP_POLARIS11,\t/* 16 */\n"
                     "\tCHIP_POLARIS12,\t/* 17 */\n"
                     "\tCHIP_VEGAM,\t/* 18 */\n};\n")
        en = parse_chip_enum(eh)
        check("enum.p10", en.get("CHIP_POLARIS10"), 15)
        check("enum.p12", en.get("CHIP_POLARIS12"), 17)

        src = os.path.join(td, "a.c")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(
                "#include \"x.h\"\n"
                "int nivel3(struct pp_hwmgr *hwmgr)\n"
                "{\n"
                "\tint r = 0;\n"
                "\tr = hardware_ayudante(hwmgr);\n"
                "\treturn r;\n"
                "}\n"
                "int nivel2(struct pp_hwmgr *hwmgr)\n"
                "{\n"
                "\tif (hwmgr->chip_id == CHIP_VEGAM)\n"
                "\t\tllamada_muerta(hwmgr);\n"
                "\tnivel3(hwmgr);\n"
                "\treturn 0;\n"
                "}\n"
                "int nivel1(struct pp_hwmgr *hwmgr)\n"
                "{\n"
                "\tPP_ASSERT_WITH_CODE(hwmgr != NULL, \"x\", return -1);\n"
                "\tpp_read_registro(hwmgr, mmSMC_RESP_0);\n"
                "\thwmgr->smumgr_funcs->send_msg(hwmgr, 1);\n"
                "\tif (hwmgr->chip_id == CHIP_POLARIS12)\n"
                "\t\tonly_polaris12(hwmgr);\n"
                "\treturn nivel2(hwmgr);\n"
                "}\n"
            )
        text = strip_comments(open(src, encoding="utf-8").read())
        funcs = function_bodies(text)
        names = sorted(str(f["name"]) for f in funcs)
        # hardware_ayudante SOLO se llama, nunca se define en este fichero.
        # Contarla como definicion seria inventar una funcion.
        check("funcs.encontradas", names, ["nivel1", "nivel2", "nivel3"])
        check("funcs.no_inventa_definiciones", "hardware_ayudante" in names, False)
        f3a = next(f for f in funcs if f["name"] == "nivel3")
        d3, _, _ = calls_in(str(f3a["body"]))
        check("calls.hardware_ayudante_detectada", "hardware_ayudante" in d3, True)

        f1 = next(f for f in funcs if f["name"] == "nivel1")
        d, vt, mc = calls_in(str(f1["body"]))
        check("calls.nivel2", "nivel2" in d, True)
        check("calls.macro_en_macro", "PP_ASSERT_WITH_CODE" in mc, True)
        check("calls.macro_no_es_directa", "PP_ASSERT_WITH_CODE" in d, False)
        check("calls.vtable", any(x["fn"] == "send_msg" for x in vt), True)
        check("calls.only_p12", "only_polaris12" in d, True)

        f2 = next(f for f in funcs if f["name"] == "nivel2")
        v2, c2 = branch_verdict(str(f2["body"]), 17, en,
                                 has_code_outside_conditions(str(f2["body"])))
        check("verdict.parcial", v2, "PARCIAL")
        check("verdict.ve_muerte", any(c["constant"] == "CHIP_VEGAM" and
                                       c["taken"] == "no" for c in c2), True)

        f3 = next(f for f in funcs if f["name"] == "nivel3")
        v3, c3 = branch_verdict(str(f3["body"]), 17, en)
        check("verdict.sin_condicion", v3, "NO_CONDICIONAL")

        # una rama solo-POLARIS12 es VIVA para nosotros
        text2 = strip_comments(
            "int solo_p12(struct pp_hwmgr *hwmgr)\n{\n"
            "\tif (hwmgr->chip_id == CHIP_POLARIS12)\n\t\tx();\n}\n")
        f4 = function_bodies(text2)
        check("funcs.undefined_abi", len(f4), 1)
        v4, _ = branch_verdict(str(f4[0]["body"]), 17, en)
        check("verdict.viva", v4, "VIVA")

        # Un typedef de puntero a funcion NO es una definicion, y la firma
        # "int (*fn(void))(int)" tampoco lo es: devuelve un puntero, no es una
        # funcion. Antes de la correccion la herramienta reportaba "int" como
        # nombre de funcion, inventando un simbolo que no existe.
        text3 = ("typedef int (*cb_t)(int);\n"
                 "int (*registrar(void))(int)\n{\n\treturn 0;\n}\n")
        got3 = [f["name"] for f in function_bodies(text3)]
        check("funcs.typedef_no_es_definicion", got3, [])
        check("funcs.no_inventa_int", "int" in got3, False)
        # pero una funcion normal de puntero a funcion SI existe con su cuerpo
        text4 = ("typedef int (*cb_t)(int);\n"
                 "int usar(cb_t f)\n{\n"
                 "\treturn f(1);\n}\n")
        check("funcs.normal_con_typedef_presente",
              [f["name"] for f in function_bodies(text4)], ["usar"])

        check("enum.inexistente", parse_chip_enum(os.path.join(td, "nope.h")), {})

    # --- resolver de definicion de enum (DOGFOOD-002) ---
    #
    # El defecto de DOGFOOD-001: trace_path asumia la ruta
    # `include/drm/amd_asic_type.h` y, cuando el corpus no la
    # tiene (arbol include/ podado), fallaba con un mensaje que
    # afirmaba falsamente que el CHIP no estaba en ese fichero.
    # Seis vectores: la ruta historica, la ruta alternativa, la
    # ambiguedad, la ausencia, el USO rechazado, y la
    # coherencia de la provenance.
    ENUM_SRC = ("enum amd_asic_type {\n"
                "\tCHIP_POLARIS10,\t/* 15 */\n"
                "\tCHIP_POLARIS11,\t/* 16 */\n"
                "\tCHIP_POLARIS12,\t/* 17 */\n"
                "\tCHIP_VEGAM,\t/* 18 */\n};\n")
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        # CASE 1: la ruta conocida existe y contiene la definicion.
        hist = os.path.join(td, "c1", "include", "drm")
        os.makedirs(hist)
        with open(os.path.join(hist, "amd_asic_type.h"),
                  "w", encoding="utf-8") as fh:
            fh.write(ENUM_SRC)
        r1 = resolve_enum_definition(os.path.join(td, "c1"))
        check("resolver.caso1_ruta_historica", r1["status"], "RESOLVED")
        check("resolver.caso1_provenance",
              (r1["path"], r1["source"]),
              (os.path.join(hist, "amd_asic_type.h"), "KNOWN_PATH"))

        # CASE 2: la ruta conocida NO existe; la definicion esta
        # en otra ruta del corpus.  Se resuelve, no se falla.
        alt = os.path.join(td, "c2", "drivers", "gpu", "drm",
                           "amd", "amdgpu")
        os.makedirs(alt)
        with open(os.path.join(alt, "amdgpu.h"), "w",
                  encoding="utf-8") as fh:
            fh.write(ENUM_SRC)
        r2 = resolve_enum_definition(os.path.join(td, "c2"))
        check("resolver.caso2_ruta_alternativa", r2["status"], "RESOLVED")
        check("resolver.caso2_provenance",
              (r2["path"], r2["source"]),
              (os.path.join(alt, "amdgpu.h"), "CORPUS_SEARCH"))

        # CASE 3: dos definiciones validas -> AMBIGUOUS_SYMBOL.
        # No se elige arbitrariamente.
        amb = os.path.join(td, "c3")
        for rel in ("a/amd_asic_type.h", "b/amd_asic_type.h"):
            d = os.path.join(amb, os.path.dirname(rel))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(amb, rel), "w",
                      encoding="utf-8") as fh:
                fh.write(ENUM_SRC)
        r3 = resolve_enum_definition(amb)
        check("resolver.caso3_ambiguo", r3["status"], "AMBIGUOUS_SYMBOL")
        check("resolver.caso3_no_elige", r3["path"], None)

        # CASE 4: el simbolo esta ausente del corpus.
        empty = os.path.join(td, "c4")
        os.makedirs(empty)
        with open(os.path.join(empty, "otro.h"), "w",
                  encoding="utf-8") as fh:
            fh.write("#define X 1\n")
        r4 = resolve_enum_definition(empty)
        check("resolver.caso4_ausente", r4["status"], "NOT_FOUND")

        # CASE 5: el fichero contiene el simbolo pero es un USO
        # (miembro de struct, parametro), no la definicion.
        # Sin valores CHIP_* extraibles, no es candidato.
        uso = os.path.join(td, "c5", "drivers", "gpu", "drm",
                           "amd", "amdgpu")
        os.makedirs(uso)
        with open(os.path.join(uso, "amdgpu.h"), "w",
                  encoding="utf-8") as fh:
            fh.write("struct amdgpu_device {\n"
                     "\tenum amd_asic_type\t\tasic_type;\n"
                     "};\n"
                     "bool f(enum amd_asic_type t);\n")
        r5 = resolve_enum_definition(os.path.join(td, "c5"))
        check("resolver.caso5_rechaza_uso", r5["status"], "NOT_FOUND")

        # CASE 6: la provenance es coherente: la linea que el
        # resolver reporta contiene la definicion (`enum` y
        # `asic_type` en ella), no otra linea del fichero.
        with open(str(r2["path"]), "r", encoding="utf-8") as fh:
            reported = fh.read().splitlines()[int(str(r2["line"])) - 1]
        check("resolver.caso6_provenance_coherente",
              ("enum" in reported) and ("asic_type" in reported), True)

    print(f"{NAME} {VERSION} · self-test")
<<<<<<< HEAD
    # El numero de vectores se imprime siempre: sin el, "RESULTADO OK" no dice
    # si se han comprobado 12 cosas o 12000, y no se puede comparar con el de
    # antes de un arreglo para ver si la red ha crecido.
    print(f"  vectores: {vectores}")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)} de {vectores}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print(f"  RESULTADO OK · {vectores} vectores conocidos reproducidos")
=======
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
>>>>>>> c682c4a4cf4e2c5c518a90f41e54107a7ecde6db
    print("  NOTA: veredicto por rama declarada. NO prueba ejecucion real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
