#!/usr/bin/env python3
"""struct_layout.py — tamaño y offset de cada campo de un struct del kernel.
    WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.

Por qué existe
--------------
Para escribir un driver propio hay que conocer el layout exacto de
`pp_hwmgr`, `smu7_hwmgr`, `gpu_pt_config_reg`, `adev->reg.didt`. Eso son
decenas de campos y el kernel no publica nada: hay que contar bytes.

El cálculo es mecánico y por eso mismo es donde más fácil se cuela un error.
Los struct del kernel usan de hecho:

  * `u32/u64/s32` con alineacion natural
  * punteros = 8 bytes en x86-64
  * arrays `[]` de tamaño flexible
  * `__packed` o `packed` en algunos, que quitan el relleno
  * unions con `union { }`
  * `bitfield` no ocupa bytes calculables a ojo

Y el error clásico: contar el relleno como si no existiera, o suponer que
todos los campos van en orden. El resultado es un offset equivocado, que en
un driver propio significa escribir en el campo de al lado.

Esta herramienta calcula el layout aplicando las reglas del compilador de C
para el ABI de x86-64, y **declara qué reglas ha supuesto**. Lo que no sabe
no lo adivina: lo dice.

Lo que produce
--------------
  * offset de cada campo, en bytes, desde el inicio del struct
  * tamaño total, y tamaño si no alineara
  * el relleno, marcado como `padding`, porque ahí NO se puede escribir
  * los arrays y unions, con su tamaño
  * la lista de supuestos, para saber qué parte del resultado es solida

Lo que NO hace
--------------
No compila nada. No valida el layout contra el compilador. Si una regla del ABI
no está implementada, aparece en `supuestos_no_aplicados` y el resultado lleva
`CONFIANZA=PARCIAL`. Es preferible decir "esto no lo sé" a dar un offset
falso: un offset falso en un driver es una escritura en el campo vecino.

Uso
---
    struct_layout.py --kernel RAIZ --struct gpu_pt_config_reg
    struct_layout.py --kernel RAIZ --struct pp_hwmgr --fields
    struct_layout.py --kernel RAIZ --struct smu7_hwmgr --offset smc_state_table
    struct_layout.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "struct_layout"
VERSION = "1.0.0"

# ABI x86-64 System V, que es el que compila el kernel de este host.
# El kernel impone ademas su propia regla: __aligned_u64 exige 8. Se declara
# aparte porque no es una regla del compilador de usuario.
ABI64 = {
    "char": (1, 1), "s8": (1, 1), "u8": (1, 1), "int8_t": (1, 1), "uint8_t": (1, 1),
    "bool": (1, 1), "_Bool": (1, 1),
    "short": (2, 2), "s16": (2, 2), "u16": (2, 2),
    "int16_t": (2, 2), "uint16_t": (2, 2),
    "int": (4, 4), "unsigned": (4, 4), "unsigned int": (4, 4),
    "s32": (4, 4), "u32": (4, 4), "int32_t": (4, 4), "uint32_t": (4, 4),
    "long": (8, 8), "unsigned long": (8, 8),
    "s64": (8, 8), "u64": (8, 8), "int64_t": (8, 8), "uint64_t": (8, 8),
    "long long": (8, 8), "unsigned long long": (8, 8),
    "long long int": (8, 8), "long long unsigned int": (8, 8),
    "float": (4, 4), "double": (8, 8),
    "void *": (8, 8), "char *": (8, 8),
    "size_t": (8, 8), "ssize_t": (8, 8), "phys_addr_t": (8, 8),
    "__le16": (2, 2), "__le32": (4, 4), "__le64": (8, 8),
    "__u16": (2, 2), "__u32": (4, 4), "__u64": (8, 8),
    "__s16": (2, 2), "__s32": (4, 4), "__s64": (8, 8),
    "reg32_t": (4, 4), "int64": (8, 8), "uint64": (8, 8),
    "__aligned_u64": (8, 8),
}

PRIM = tuple(sorted(ABI64.keys(), key=len, reverse=True))


def strip_comments(text: str) -> str:
    """Comentarios a espacio, conservando longitud: si no, los numeros de
    linea del informe dejan de corresponder al fichero."""
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


def align_up(x: int, a: int) -> int:
    if a <= 1:
        return x
    return (x + a - 1) // a * a


# La clave incluye el NEEDLE COMPLETO, no su longitud.
#
# Con la longitud, SMU73_Discrete_DpmTable y SMU74_Discrete_DpmTable colisionan:
# miden los dos 23. Buscando el primero, smu74_discrete.h se cacheaba como ""
# (el needle no estaba en el), y buscando el segundo la longitud coincidia y la
# cache devolvia "" como respuesta correcta. Resultado: SMU74_Discrete_DpmTable
# no se encontraba y su tamano salia sin medir, unicamente por el orden en que
# os.walk visitaba los ficheros.
#
# La longitud como clave es el mismo fallo que un hash de tamano: dos entradas
# distintas que ocupan lo mismo se confirman mutuamente.
_TEXT_CACHE: Dict[Tuple[str, str], Tuple[float, str]] = {}


def _clean_text(path: str, needle: str) -> str:
    """Texto sin comentarios, cacheado por (ruta, needle) y validado por mtime.

    Sin esta cache, pedir dos structs relee el arbol entero dos veces y el
    segundo rastreo tarda minutos: el filtro barato es `needle in texto`, pero
    ese filtro solo funciona si el texto ya esta en memoria.
    """
    try:
        st = os.stat(path)
    except OSError:
        return ""
    key = (path, needle)
    cached = _TEXT_CACHE.get(key)
    if cached and cached[0] == st.st_mtime:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError:
        return ""
    if needle not in raw:
        _TEXT_CACHE[key] = (st.st_mtime, "")
        return ""
    clean = strip_comments(raw)
    _TEXT_CACHE[key] = (st.st_mtime, clean)
    return clean


_FIND_STRUCT_CACHE: Dict[str, List[Dict[str, object]]] = {}


def find_struct_cached(root: str, name: str) -> List[Dict[str, object]]:
    """find_struct con cache por (raiz, simbolo).

    find_struct re-recorre el arbol entero en cada llamada. Cuando un barrido
    resuelve miles de sizeof, eso pasa de dos minutos y la herramienta se
    abandona. Un fallo de rendimiento en una herramienta de barrido es un fallo
    de usabilidad: vuelve el grep manual, con todos sus fallos.
    """
    key = root + "|" + name
    if key not in _FIND_STRUCT_CACHE:
        _FIND_STRUCT_CACHE[key] = find_struct(root, name)
    return _FIND_STRUCT_CACHE[key]


# #pragma pack es una DIRECTIVA CON ESTADO: afecta a todo lo que viene
# despues, hasta el pop. El corpus la usa de forma masiva:
#     smu74.h:28   #pragma pack(push, 1)
#     smu74.h:637  #pragma pack(pop)
# Sin seguirla, el layout se calcula como si no hubiera empaquetado y
# SMU7_MclkDpmScoreboard sale de 112 bytes con los punteros a funcion
# alineados, cuando gcc dice 106 con alignof 1. Un struct con un puntero a
# funcion desalineado no es un struct: escribirlo a mano revienta.
_PRAGMA_PACK = re.compile(
    r"^\s*#\s*pragma\s+pack\s*\(\s*(?P<act>push|pop)?\s*"
    r"(?:,\s*(?P<val>\d+))?\s*\)")
_PACK_CACHE: Dict[str, Dict[int, Optional[int]]] = {}


def pack_states(path: str) -> Dict[int, Optional[int]]:
    """Linea -> valor de pack vigente (1, 2, 4, 8) o None si es el natural.

    None significa "sin pragma activo", no "pack de 0".
    """
    if path in _PACK_CACHE:
        return _PACK_CACHE[path]
    out: Dict[int, Optional[int]] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        _PACK_CACHE[path] = out
        return out
    stack: List[int] = []
    cur: Optional[int] = None
    for i, line in enumerate(lines, 1):
        m = _PRAGMA_PACK.match(line)
        if m:
            act = m.group("act")
            val = m.group("val")
            if act == "push":
                stack.append(cur if val is None else int(val))
                cur = int(val) if val is not None else cur
            elif act == "pop":
                cur = stack.pop() if stack else None
            else:
                cur = int(val) if val is not None else None
        out[i] = cur
    _PACK_CACHE[path] = out
    return out


def pack_at(path: str, line: int) -> Optional[int]:
    st = pack_states(path)
    if not st:
        return None
    keys = [k for k in st if k <= line]
    if not keys:
        return None
    return st[max(keys)]


def _scan_one_file(p: str, name: str) -> List[Dict[str, object]]:
    """Definiciones de `name` en UN fichero. Es la unidad de busqueda."""
    out: List[Dict[str, object]] = []
    try:
        clean = _clean_text(p, name)
    except OSError:
        return out
    if not clean:
        return out
    # typedef struct NOMBRE { ... } NOMBRE;   y   struct NOMBRE { ... };
    pat_td = re.compile(r"typedef\s+struct\s+" + re.escape(name) + r"\s*\{")
    pat_st = re.compile(r"(?<!typedef\s)\bstruct\s+" + re.escape(name) + r"\s*\{")
    for pat, kind in ((pat_td, "typedef"), (pat_st, "struct")):
        m = pat.search(clean)
        if not m:
            continue
        i = m.end() - 1
        depth, j = 0, i
        while j < len(clean):
            if clean[j] == "{":
                depth += 1
            elif clean[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append({
            "file": p,
            "kind": kind,
            "line": clean[:m.start()].count("\n") + 1,
            "body": clean[m.end():j],
            "after": clean[j:j + 200],
            "decl_full": clean[m.start():j + 1],
            "pack": pack_at(p, clean[:m.start()].count("\n") + 1),
        })
        break
    return out


def find_struct_in_file(p: str, name: str) -> List[Dict[str, object]]:
    """Definiciones de un tipo en un fichero concreto."""
    return _scan_one_file(p, name)


def find_struct(root: str, name: str) -> List[Dict[str, object]]:
    """Localiza la definicion del struct, con todos sus ficheros.

    Varios ficheros pueden definirlo: en el kernel eso significa o una
    reexportacion o dos definiciones distintas segun ASIC. Se devuelven todas y
    quien elige sabe cual esta en vigor: usar la primera por orden de recorrido
    es arbitrario. Ver find_struct_scoped, que si sigue el grafo de includes.
    """
    hits: List[Dict[str, object]] = []
    if not os.path.isdir(root):
        return hits
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            if not fn.endswith(".h"):
                continue
            hits.extend(_scan_one_file(os.path.join(dirpath, fn), name))
    if not hits:
        # Ultimo recurso: un typedef ANONIMO con el nombre en la cola.
        #   typedef struct { int a; } sclkFcwRange_t;
        # El patron se construcia aqui. Al extraer el escaneo por fichero para
        # poder seguir el grafo de includes, el patron se llevo consigo y esta
        # rama se quedaron sin patron: NameError en cuanto un tipo solo existe
        # como typedef anonimo. No lo cazo el self-test porque ningun vector
        # usaba esa forma.
        pat_alias = re.compile(
            r"typedef\s+struct\s*\{(?P<body>[^{}]*?)\}\s*"
            + re.escape(name) + r"\s*;")
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if not fn.endswith(".h"):
                    continue
                p = os.path.join(dirpath, fn)
                clean = _clean_text(p, name)
                if not clean:
                    continue
                m = pat_alias.search(clean)
                if not m:
                    continue
                hits.append({
                    "file": p, "kind": "typedef_anonimo",
                    "line": clean[:m.start()].count("\n") + 1,
                    "body": m.group("body"),
                    "after": m.group(0)[-120:],
                    "decl_full": m.group(0),
                })
                break
            if hits:
                break
    hits.sort(key=lambda h: (h["kind"] != "struct", str(h["file"])))
    return hits


_ENUM_CACHE: Dict[str, Optional[Tuple[int, int]]] = {}


def enum_size(root: str, ename: str) -> Optional[Tuple[int, int]]:
    """Tamaño de un enum, leido del corpus.

    En C un enum tiene tamaño de int, pero el kernel usa enums cuyo valor
    maximo no cabe en 32 bits, y entonces el compilador elige 8. Suponer 4 sin
    mirar el enum da un offset equivocado a partir del campo siguiente, asi
    que se lee el corpus y se declaran los dos casos.
    """
    if ename in _ENUM_CACHE:
        return _ENUM_CACHE[ename]
    clean = _clean_text_direct(root, ename)
    res: Optional[Tuple[int, int]] = None
    if clean:
        body = _extract_brace_body(clean, re.compile(
            r"\benum\s+" + re.escape(ename) + r"\s*\{"), 0)
        if body is not None:
            vals = re.findall(r"([A-Za-z_]\w*)\s*(?:=\s*(0[xX][0-9a-fA-F]+|\d+))?", body)
            maxv, neg = 0, False
            for name, lit in vals:
                if lit:
                    v = int(lit, 16) if lit.lower().startswith("0x") else int(lit)
                else:
                    v = maxv + 1
                if v > maxv:
                    maxv = v
                if name.isupper() and "NEG" in name:
                    neg = True
            if "MAX" in ename and maxv > 0x7FFFFFFF:
                res = (8, 8)
            elif maxv > 0xFFFFFFFF or neg:
                res = (8, 8)
            else:
                res = (4, 4)
    _ENUM_CACHE[ename] = res
    return res


def _clean_text_direct(path: str, needle: str) -> str:
    try:
        st = os.stat(path)
    except OSError:
        return ""
    cached = _TEXT_CACHE.get(path)
    if cached and cached[0] == st.st_mtime:
        return cached[2]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError:
        return ""
    clean = strip_comments(raw)
    _TEXT_CACHE[path] = (st.st_mtime, len(needle), clean)
    return clean


def _extract_brace_body(text: str, pat: "re.Pattern[str]", offset: int) -> Optional[str]:
    m = pat.search(text)
    if not m:
        return None
    j = m.end() - 1 + offset
    depth = 0
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]
        j += 1
    return None


def type_size(t: str, known: Optional[Dict[str, Tuple[int, int]]] = None) -> Optional[object]:
    """(tamaño, alineacion) de un tipo, o None si no se sabe."""
    known = known or {}
    tt = t.strip()
    if not tt:
        return None
    if tt.endswith("*"):
        return (8, 8)
    # puntero a struct
    mptr = re.match(r"(?:struct|union)\s+\w+\s*\*$", tt)
    if mptr:
        return (8, 8)
    m = re.match(r"(?:struct|union)\s+([A-Za-z_]\w*)$", tt)
    if m:
        return ("STRUCT", m.group(1))
    menum = re.match(r"enum\s+([A-Za-z_]\w*)$", tt)
    if menum:
        en = menum.group(1)
        if en in known:
            return known[en]
        return ("ENUM", en)
    # Puntero a funcion: en ABI x86-64 ocupa lo mismo que un puntero a datos.
    if re.match(r"^[A-Za-z_][\w \t]*\s*\(\*", tt) or tt.endswith("(*)()"):
        return ABI64["void *"]
    for p in PRIM:
        if tt == p:
            return ABI64[p]
    # "unsigned long int", "long long unsigned int", etc.
    norm = " ".join(tt.replace("unsigned int", "unsigned").split())
    for p in PRIM:
        if norm == p:
            return ABI64[p]
    if tt in known:
        return known[tt]
    return None


# Sigue el grafo de #include para saber que definicion de un tipo esta EN
# VIGOR. El kernel redefine el mismo struct por ASIC y todos los ficheros viven
# en el mismo directorio, asi que el orden del recorrido no dice nada:
#     smu71.h:444  struct SMU7_HystController_Data { u8 x4; }        -> 4 bytes
#     smu74.h:223  struct SMU7_HystController_Data { u8 x4; u16 x2; } -> 8 bytes
# smu74_discrete.h incluye smu74.h, luego en ese contexto vale la de smu74.h.
# Tomar la primera hacia que SMU7_TdcLimitScoreboard midiese 20 en vez de 24,
# con CONFIANZA COMPLETA: un error con total y sin aviso.
_INCLUDE_LOCAL = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
_INCLUDE_CACHE: Dict[str, List[str]] = {}


def include_closure(path: str, max_depth: int = 4) -> List[str]:
    """Ficheros alcanzables desde path siguiendo #include "locales"."""
    key = path
    if key in _INCLUDE_CACHE:
        return _INCLUDE_CACHE[key]
    out: List[str] = []
    seen: Set[str] = set()
    frontier = [path]
    depth = 0
    while frontier and depth < max_depth:
        nxt: List[str] = []
        for f in frontier:
            if f in seen or not os.path.isfile(f):
                continue
            seen.add(f)
            out.append(f)
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            d = os.path.dirname(f)
            for inc in _INCLUDE_LOCAL.findall(txt):
                cand = os.path.normpath(os.path.join(d, inc))
                if os.path.isfile(cand):
                    nxt.append(cand)
        frontier = nxt
        depth += 1
    _INCLUDE_CACHE[key] = out
    return out


def find_struct_scoped(name: str, ctx_file: str,
                      fallback_root: str = "") -> List[Dict[str, object]]:
    """Definiciones de un tipo VIGENTES en el contexto de ctx_file.

    Primero se busca en los ficheros que ctx_file incluye, en orden de
    inclusion. Solo si no aparece ahi se recurre a la busqueda global, y si esa
    devuelve varias se declara la ambiguedad en vez de elegir una.

    fallback_root es EXPLICITO a proposito. Antes se derivaba subiendo cuatro
    directorios desde ctx_file, lo que desde un arbol temporal acababa
    recorriendo /tmp entero y colgaba la herramienta. Ademas, un sitio que pide
    una busqueda global sabe cual es la raiz; adivinarla es lo que la hacia
    colgarla.
    """
    if ctx_file:
        for f in include_closure(ctx_file):
            hits = find_struct_in_file(f, name)
            if hits:
                return hits
    if fallback_root:
        return find_struct_cached(fallback_root, name)
    return []


def parse_fields(body: str, ctx_file: str = "") -> Tuple[List[Dict[str, object]], List[str]]:
    """Separa los campos de nivel superior. Declara lo que no sabe medir."""
    fields: List[Dict[str, object]] = []
    unknown: List[str] = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        i += 1
        if not s:
            continue
        # union {...} en linea: se marca como opaco
        m = re.match(r"union\s*\{", s)
        if m:
            unknown.append(f"union en linea: {s[:60]}")
            continue
        # ARRAY antes que nada, y antes que la rama de "struct en linea".
        # "struct Entry entries[8][4]" cumple el patron de struct seguido de
        # array, entraba por ahi y con el patron de una sola dimension no
        # casaba: el campo se perdia y el struct contenedor se media con un
        # campo menos, desplazando todos los offsets siguientes.
        #
        # MULTIDIMENSIONAL: "T entries[A][B];". Con una sola dimension el
        # patron no casa cuando hay una segunda y el campo cae al final de la
        # cadena. SMU74_Discrete_MCArbDramTimingTable tiene
        # entries[SMU__NUM_SCLK_DPM_STATE][SMU__NUM_MCLK_DPM_LEVELS], y sus
        # seis copias a la RAM del SMC se declaraban de longitud 0.
        ma = re.match(r"^(?P<type>[A-Za-z_][\w \t*]*?)\s*"
                      r"(?P<name>\w+)(?P<dims>(?:\s*\[[^\]]*\])+)\s*;?$", s)
        if ma:
            raw_dims = re.findall(r"\[([^\]]*)\]", ma.group("dims"))
            counts: List[Optional[int]] = []
            flex = False
            for d in raw_dims:
                if d.strip() == "":
                    flex = True
                    counts.append(1)
                    continue
                c, _ = resolve_bound(d, ctx_file=ctx_file)
                counts.append(c)
            if all(c is not None for c in counts):
                cnt: Optional[int] = 1
                for c in counts:
                    cnt = int(c) * cnt  # type: ignore[arg-type]
            else:
                # NO cero. Cero es una medida; aqui no hay medida, y confundirlas
                # hace que un array sin medir parezca un array vacio.
                cnt = None
            ftype = ma.group("type").strip()
            fields.append({"decl": s, "type": ftype,
                           "name": ma.group("name"),
                           "count": cnt,
                           "dims": raw_dims,
                           "bound_expr": ",".join(raw_dims),
                           "flexible": flex,
                           "bound_unresolved": cnt is None and not flex})
            continue
        # struct {...} / union {...} sin nombre, en linea: opaco
        if re.match(r"^(?:struct|union)\s*\{", s):
            unknown.append(f"struct/union anonimo en linea: {s[:60]}")
            continue
        # PUNTERO A FUNCION: "void (*TargetStateCalculator)(uint8_t);"
        # No estaba contemplado y el campo se perdia entero. Dos punteros a
        # funcion son 16 bytes, asi que SMU7_MclkDpmScoreboard salia de 92 en
        # vez de 106 con CONFIANZA COMPLETA: el total era plausible y falso, y
        # todos los offsets posteriores desplazados.
        mfn = re.match(r"^(?P<ret>[A-Za-z_][\w \t]*?)\s*\(\s*\*+\s*"
                       r"(?P<name>\w+)\s*\)\s*\(", s)
        if mfn:
            fields.append({"decl": s,
                           "type": mfn.group("ret").strip() + " (*)()",
                           "name": mfn.group("name"), "count": 1,
                           "flexible": False})
            continue
        # PUNTERO: "uint32_t *p;", "struct foo *bar;", "char **argv;".
        # No estaba contemplado y el campo caia al final de la cadena. Los
        # punteros estan por todas partes en el kernel: un struct con un solo
        # puntero sin parsear invalida el TOTAL del layout contenedor, y todos
        # los offsets siguientes se declaran no medidos. El self-test solo
        # ejercitaba punteros llamando a layout() directamente, saltandose el
        # parser entero, asi que el hueco pasaba inadvertido.
        mptr = re.match(r"^(?P<type>[A-Za-z_][\w \t]*?)\s*(?P<stars>\*+)\s*"
                        r"(?P<name>\w+)\s*;?$", s)
        if mptr:
            # Los asteriscos SE CONSERVAN. Sustituirlos por espacios hacia que
            # type_size midiera el TIPO BASE: un uint32_t* salia de 4 bytes en
            # vez de 8, que es un numero plausible y falso, y desplaza todos
            # los offsets siguientes sin avisar.
            fields.append({"decl": s,
                           "type": mptr.group("type").strip() + mptr.group("stars"),
                           "name": mptr.group("name"), "count": 1,
                           "flexible": False})
            continue
        # puntero a tipo nombrado sin la palabra struct: ya cubierto arriba
        #quita  ';'
        if s.endswith(";"):
            s = s[:-1].strip()
        if not s:
            continue
        # bitfield: "u32 a : 3;"
        if re.search(r"\w+\s*:\s*\d+\s*$", s):
            fields.append({"decl": s, "bitfield": True,
                           "name": s.split(":")[0].split()[-1]})
            continue
        # array: "u32 foo[16];" o "u32 foo[];"
        # MULTIDIMENSIONAL: "T entries[A][B];". El patron de una sola dimension
        # no casa cuando hay una segunda, el campo cae al final de la cadena y
        # se pierde: el struct entero se media como CERO BYTES y un cero medido
        # se confunde con un struct vacio. SMU74_Discrete_MCArbDramTimingTable
        # tiene entries[SMU__NUM_SCLK_DPM_STATE][SMU__NUM_MCLK_DPM_LEVELS], y
        # sus seis copias a la RAM del SMC se declaraban de longitud 0.
        ma = re.match(r"^(?P<type>.+?)\s+(?P<name>\w+)"
                      r"(?P<dims>(?:\s*\[[^\]]*\])+)\s*$", s)
        if ma:
            raw_dims = re.findall(r"\[([^\]]*)\]", ma.group("dims"))
            counts: List[Optional[int]] = []
            flex = False
            for d in raw_dims:
                if d.strip() == "":
                    flex = True
                    counts.append(1)
                    continue
                c, _ = resolve_bound(d, ctx_file=ctx_file)
                counts.append(c)
            if all(c is not None for c in counts):
                cnt: Optional[int] = 1
                for c in counts:
                    cnt = int(c) * cnt  # type: ignore[arg-type]
            else:
                cnt = None
            fields.append({"decl": s, "type": ma.group("type").strip(),
                           "name": ma.group("name"),
                           "count": cnt,
                           "dims": raw_dims,
                           "bound_expr": ",".join(raw_dims),
                           "flexible": flex,
                           "bound_unresolved": cnt is None and not flex})
            continue
        # multi-declaracion: "u32 foo, bar, baz;"
        # ESTE CASO VA ANTES del match simple. Con el orden contrario,
        # "uint32_t b, c" casa con ^(type)\s+(name)$ de forma codiciosa y
        # devuelve type="uint32_t b," name="c": el primer declarador se pierde
        # y el segundo hereda un tipo que no existe. El self-test lo caza.
        if "," in s and re.match(r"^[A-Za-z_][\w \t*]*?,\s*\w", s):
            mfirst = re.match(r"^(?P<type>.+?)\s+(?P<n1>\w+)\s*,", s)
            if mfirst:
                btype = mfirst.group("type").strip()
                # El primer segmento lleva el tipo delante: "uint32_t b". Si no
                # se le quita, su "nombre" sale siendo uint32_t y el primer
                # declarador se pierde con el tipo pegado.
                for idx, part in enumerate(s.split(",")):
                    seg = part.strip()
                    if not seg:
                        continue
                    if idx == 0:
                        seg = re.sub(r"^" + re.escape(btype) + r"\s+", "", seg)
                    marr = re.match(r"^(\w+)\s*\[\s*(\d*)\s*\]$", seg)
                    if marr:
                        fields.append({"decl": seg, "type": btype,
                                       "name": marr.group(1),
                                       "count": int(marr.group(2)) if marr.group(2) else 0,
                                       "flexible": not marr.group(2)})
                    else:
                        mm = re.match(r"^(\w+)$", seg)
                        if mm:
                            fields.append({"decl": seg, "type": btype,
                                           "name": mm.group(1), "count": 1,
                                           "flexible": False})
                        else:
                            unknown.append(f"multi-decl no partida: {seg[:40]}")
                continue

        # simple: "u32 foo;"
        ms = re.match(r"^(?P<type>.+?)\s+(?P<name>\w+)$", s)
        if ms:
            fields.append({"decl": s, "type": ms.group("type").strip(),
                           "name": ms.group("name"), "count": 1,
                           "flexible": False})
            continue
        unknown.append(s[:80])
    return fields, unknown


def layout(fields: Sequence[Dict[str, object]],
           packed: bool = False,
           known: Optional[Dict[str, Tuple[int, int]]] = None,
           enum_root: Optional[str] = None,
           pack: Optional[int] = None) -> Dict[str, object]:
    """pack=N limita la alineacion de cada campo a N bytes (#pragma pack)."""
    """Calcula offsets aplicando ABI x86-64. Marca lo que no sabe."""
    known = dict(known) if known else {}
    off = 0
    align = 1
    rows: List[Dict[str, object]] = []
    unknown: List[str] = []
    for f in fields:
        if f.get("bitfield"):
            rows.append({"offset": None, "name": f.get("name"),
                         "size": None, "align": None, "kind": "bitfield",
                         "decl": f.get("decl"),
                         "note": "bitfield: ocupa bits, no se puede contar a mano"})
            continue
        t = str(f.get("type", ""))
        info = type_size(t, known)
        if isinstance(info, tuple) and info and info[0] in ("STRUCT", "ENUM"):
            sname = str(info[1])
            if info[0] == "ENUM":
                if sname in known:
                    sz, al = known[sname]
                else:
                    es = enum_size(enum_root or "", sname)
                    if es:
                        sz, al = es
                        known[sname] = es
                    else:
                        unknown.append(f"enum {sname} sin medir")
                        rows.append({"offset": None, "name": f.get("name"),
                                     "size": None, "align": None,
                                     "kind": "enum_desconocido",
                                     "decl": f.get("decl"),
                                     "note": f"sizeof(enum {sname}) no medido"})
                        continue
            elif sname in known:
                sz, al = known[sname]
            else:
                unknown.append(f"struct {sname} sin medir")
                rows.append({"offset": None, "name": f.get("name"),
                             "size": None, "align": None,
                             "kind": "struct_desconocido",
                             "decl": f.get("decl"),
                             "note": f"sizeof(struct {sname}) no medido"})
                continue
        elif info is None:
            # puede ser un typedef propio
            if t in known:
                sz, al = known[t]
            else:
                unknown.append(t or "?")
                rows.append({"offset": None, "name": f.get("name"),
                             "size": None, "align": None,
                             "kind": "tipo_desconocido",
                             "decl": f.get("decl"),
                             "note": f"tipo '{t}' no resuelto"})
                continue
        else:
            sz, al = info  # type: ignore[misc]

        if pack is not None and pack > 0:
            al = min(al, pack)
        if not packed:
            aligned = align_up(off, al)
            if aligned > off:
                rows.append({"offset": off, "name": None, "size": aligned - off,
                             "align": None, "kind": "padding",
                             "note": f"relleno a {al}"})
                off = aligned
        align = max(align, al)

        cnt = f.get("count", 1)
        if not isinstance(cnt, int):
            # El limite del array NO se resolvio. Contarlo como 1 elemento da
            # un layout plausible y FALSO: el struct sale mas pequeno, todos los
            # offsets siguientes se desplazan, y nada lo avisa. Se declara que
            # no se ha medido y el total se invalida.
            unknown.append(f"{t or '?'}[{f.get('bound_expr', '?')}] sin medir")
            rows.append({"offset": None, "name": f.get("name"), "size": None,
                         "align": al, "kind": "limite_no_resuelto",
                         "decl": f.get("decl"),
                         "note": f"limite [{f.get('bound_expr', '?')}] no resuelto"})
            continue
        count = cnt
        total = sz * count
        # Miembro de array flexible: ocupa cero bytes y, ademas, el struct
        # termina ahi. sizeof(struct { uint32_t n; uint8_t d[]; }) es 4, no 8:
        # el relleno final no se aplica cuando el ultimo miembro es flexible
        # (C99 6.7.2.1p16). Contarlo como 1 byte y rellenar daba 8, que es un
        # tamano plausible y equivocado para cualquier struct que termine en
        # array flexible, y esos structs son la forma normal de una tabla.
        if f.get("flexible"):
            total = 0
        rows.append({"offset": off, "name": f.get("name"), "size": total,
                     "align": al, "kind": "campo", "decl": f.get("decl"),
                     "flexible": bool(f.get("flexible")),
                     "opaque": bool(f.get("opaque"))})
        off += total

    # El relleno final no existe si el ultimo campo es un array flexible
    cap = pack if (pack is not None and pack > 0) else None
    if cap:
        align = min(align, cap)
    if not packed and not any(f.get("flexible") for f in fields):
        final = align_up(off, align)
        if final > off:
            rows.append({"offset": off, "name": None, "size": final - off,
                         "align": None, "kind": "padding",
                         "note": f"relleno final a {align}"})
            off = final

    measured = all(r["offset"] is not None for r in rows)
    # Si parse_fields no entendio alguna declaracion, el total NO es de fiar:
    # falta un campo y todo lo que hay detras va desplazado. Declararlo
    # medido era el modo de fallo mas peligroso, porque el numero que sale es
    # plausible y no hay nada en el resultado que avise.
    if not measured or unknown:
        total: Optional[int] = None
        conf = "NULA"
    else:
        total = off
        conf = "COMPLETA"
    return {
        "rows": rows,
        "total_size": total,
        "measured": measured and not unknown,
        "unknown": unknown,
        "confidence": conf,
        "packed": packed,
    }


def resolve_nested(fields: Sequence[Dict[str, object]],
                   amd_root: str,
                   known: Optional[Dict[str, Tuple[int, int]]] = None,
                   depth: int = 0,
                   max_depth: int = 6,
                   ctx_file: str = "") -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
    """Mide los tipos anidados que aparezcan como campo.

    El corpus amdgpu es casi todo structs anidados: SMU74_Discrete_DpmTable
    contiene SMU74_PIDController y SMIO_Table, y sus arrays son de otro tipo
    todavia. Sin resolverlos, el layout entero sale NULA porque un solo campo
    sin medir invalida el total, y una tabla con 40 campos medidos y 1 sin
    medir no sirve para calcular una direccion.

    Se mide en cascada con presupuesto de profundidad: un anidamiento
    infinito en un corpus con punteros opacos se cortaria solo.
    """
    known = dict(known) if known else {}
    pending: Dict[str, Tuple[int, int]] = {}
    unresolved: List[str] = []
    if depth >= max_depth:
        return known, ["PROFUNDIDAD_MAXIMA"]

    # Primera pasada: identificar los tipos que faltan
    wanted: Dict[str, str] = {}
    for f in fields:
        t = str(f.get("type", "")).strip()
        m = re.match(r"(?:struct|union)\s+([A-Za-z_]\w*)$", t)
        if m:
            if m.group(1) not in known:
                wanted[m.group(1)] = m.group(1)
            continue
        # Un tipo propio puede empezar en minuscula: sclkFcwRange_t es real en
        # smu74_discrete.h. Exigir mayuscula inicial lo dejaba sin medir, y un
        # solo campo sin medir invalida el TOTAL del layout contenedor.
        if (re.match(r"^[A-Za-z_]\w*$", t) and t not in ABI64
                and t not in known and t not in _SCALARISH):
            wanted[t] = t

    for tname in sorted(wanted):
        if tname in known:
            continue
        # Con contexto de fichero se busca la definicion VIGENTE. El kernel
        # redefine el mismo struct por ASIC, y los cinco ficheros estan en el
        # mismo directorio, asi que el orden del recorrido no dice nada:
        # SMU7_HystController_Data mide 4 bytes en smu71.h y 8 en smu74.h.
        # Elegir la primera hacia que SMU7_TdcLimitScoreboard saliera de 20 en
        # vez de 24, con CONFIANZA COMPLETA y sin ningun aviso.
        if ctx_file:
            hits = find_struct_scoped(tname, ctx_file, amd_root)
        else:
            hits = find_struct_cached(amd_root, tname)
        if not hits:
            unresolved.append(tname)
            continue
        if len(hits) > 1:
            unresolved.append(tname + "(varias definiciones)")
        h = hits[0]
        sub, unk = parse_fields(str(h["body"]), ctx_file=str(h["file"]))
        more, deep_unres = resolve_nested(sub, amd_root, known,
                                          depth + 1, max_depth,
                                          ctx_file=str(h["file"]))
        known.update(more)
        unresolved.extend(deep_unres)
        lay = layout(sub, packed="__packed" in str(h["decl_full"]).lower(),
                     known=known, enum_root=str(h["file"]),
                     pack=h.get("pack"))
        if lay["total_size"] is not None:
            known[tname] = (int(lay["total_size"]), _max_align(lay["rows"]))
        else:
            unresolved.append(tname + "(layout incompleto)")
        pending[tname] = (int(lay["total_size"] or 0),
                          _max_align(lay["rows"]))
    return known, sorted(set(unresolved))


def _max_align(rows: Sequence[Dict[str, object]]) -> int:
    a = 1
    for r in rows:
        v = r.get("align")
        if isinstance(v, int) and v > a:
            a = v
    return a


# Tipos que parecen identificador propio pero son escalares o punteros. Sin
# esta lista, resolve_nested intenta "medir" int64_t como si fuera un struct,
# no lo encuentra y lo reporta como no resuelto: ruido que esconde los
# casos reales como sclkFcwRange_t.
_SCALARISH = {
    "int", "char", "long", "short", "unsigned", "signed", "void", "bool",
    "float", "double", "size_t", "ssize_t", "u8", "u16", "u32", "u64",
    "s8", "s16", "s32", "s64", "le16", "le32", "le64", "be16", "be32",
    "be64", "reg32_t", "phys_addr_t", "dma_addr_t", "gfp_t", "pid_t",
    "ktime_t", "u32ptr", "uintptr_t", "intptr_t", "atomic_t",
}


_MACRO_RAW: Dict[str, str] = {}
_MACRO_CONST_CACHE: Dict[str, int] = {}

_DEFINE_ANY = re.compile(r"#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$")
_NUM_TOK = re.compile(r"^\(?\s*(0[xX][0-9a-fA-F]+|\d+)[uUlL]*\s*\)?$")


# El valor de un #define NO es lo que hay hasta el fin de linea: lo que hay
# hasta el comentario. El kernel escribe asi:
#     #define SMU7_MAX_LEVELS_UVD   8   // VCLK/DCLK levels for UVD.
#     #define RV770_DEFAULT_VCLK_FREQ 53300 /* 10 khz */
# Sin quitar el comentario, el valor no es un numero, la macro no se indexa y
# desaparece en silencio. Medido: 132 macros del subarbol de pm, entre ellas
# SMU__NUM_PCIE_DPM_LEVELS, que vale CERO. Una macro ausente y una macro que
# vale cero se confunden: un array de 0 elementos se reporta como no medible.
_DEF_TRAILING = re.compile(r"\s*(?://.*|/\*.*)$", re.S)


def _define_value(raw: str) -> str:
    """Quita el comentario FINAL de un valor de #define.

    Solo el final. Un comentario de bloque en mitad de la expresion
    ("A /* x */ + 2") NO se quita: truncar a "A" haria que la macro
    resolviera al valor de A, que es un numero plausible y equivocado. En ese
    caso se deja el valor entero, que no es un numero, y la macro queda sin
    indexar: ausente y declarada, nunca inventada.
    """
    v = raw.strip()
    out: List[str] = []
    in_str: Optional[str] = None
    i = 0
    while i < len(v):
        ch = v[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < len(v):
                out.append(v[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in "\"'":
            in_str = ch
            out.append(ch)
            i += 1
            continue
        rest = v[i:]
        if re.match(r"\s*(?://|/\*)", rest):
            if rest.rstrip().endswith("*/") or "//" in rest:
                # comentario que llega al final de la linea
                tail = v[i:].rstrip()
                closed = tail.count("/*") == tail.count("*/")
                if "/*" not in tail or closed:
                    break
        out.append(ch)
        i += 1
    return "".join(out).strip()


# Las macros se indexan POR DIRECTORIO, no en un solo diccionario global.
# 157783 macros del subarbol pm tienen definiciones CONFLICTANTES, porque el
# kernel redefine el mismo simbolo por ASIC y por generacion:
#     pm/legacy-dpm/kv_dpm.h:29      #define SMU__NUM_PCIE_DPM_LEVELS 0 /* ??? */
#     pm/powerplay/inc/smu74.h:35    #define SMU__NUM_PCIE_DPM_LEVELS 8
# Un indice con "la primera gana segun el orden del recorrido" es arbitrario:
# si kv_dpm.h se recorre antes, SMU74_MAX_LEVELS_LINK vale 0, el array
# LinkLevel[8] mide 0 bytes, y SMU74_Discrete_DpmTable sale 1756 en vez de
# 1884. Un cero medido no se distingue de un array vacio.
#
# Aqui la nearest-definition gana, como en el preprocesador: se busca en el
# directorio del fichero que usa la macro, luego hacia arriba, y solo si no
# aparece se usa el valor global, y solo si es UNICO. Si hay conflicto sin
# poder decidir, no se usa: la macro queda sin medir y se declara.
_MACRO_BY_DIR: Dict[str, Dict[str, str]] = {}
_MACRO_ALL_SITES: Dict[str, List[str]] = {}
_MACRO_AMBIGUOUS: Dict[str, List[str]] = {}


def _register_macro(name: str, value: str, path: str) -> None:
    d = os.path.dirname(path)
    _MACRO_BY_DIR.setdefault(d, {}).setdefault(name, value)
    _MACRO_ALL_SITES.setdefault(name, []).append(d)


def macro_value(name: str, from_file: str = "",
                macro_dir: Dict[str, Dict[str, str]] = None,
                consts: Optional[Dict[str, int]] = None,
                _depth: int = 0) -> Optional[int]:
    """Resuelve una macro como lo haria el preprocesador: la mas cercana gana.

    Devuelve None si no se puede decidir. Preferir un valor arbitrario entre
    definiciones incompatibles produce numeros plausibles y falsos, que es el
    peor resultado posible: un array de 0 elementos no se distingue de uno que
    no se ha medido.
    """
    if consts is None:
        consts = _MACRO_CONST_CACHE
    if name in consts and not from_file:
        return consts[name]
    by_dir = _MACRO_BY_DIR if macro_dir is None else macro_dir
    if from_file and _depth < 12:
        d = os.path.dirname(os.path.abspath(from_file))
        for _ in range(12):
            table = by_dir.get(d)
            if table and name in table:
                v = _chain_to_int(table[name], by_dir, d, consts, 0)
                if v is not None:
                    return v
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    # sin contexto de fichero: solo si el valor global es unico
    if name in consts:
        return consts[name]
    return None


def _chain_to_int(raw: str, by_dir: Dict[str, Dict[str, str]],
                  d: str, consts: Dict[str, int], depth: int) -> Optional[int]:
    """Sigue una cadena de alias en el contexto de un directorio."""
    seen: Set[str] = set()
    cur = raw
    for _ in range(8):
        if depth > 12 or cur in seen:
            return None
        seen.add(cur)
        mnum = _NUM_TOK.match(cur)
        if mnum:
            tok = mnum.group(1)
            return int(tok, 16) if tok.lower().startswith("0x") else int(tok)
        parts = cur.split()
        if not parts:
            return None
        nxt = parts[0]
        if nxt in consts:
            return consts[nxt]
        table = by_dir.get(d) or {}
        if nxt in table:
            cur = table[nxt]
            continue
        return None
    return None


def macro_constants(roots: Sequence[str]) -> Dict[str, int]:
    """#define del corpus, resueltos TRANSITIVAMENTE.

    El corpus encadena alias: en smu74.h
        #define SMU74_MAX_LEVELS_GRAPHICS   SMU__NUM_SCLK_DPM_STATE
        #define SMU__NUM_SCLK_DPM_STATE      8
    Un indice que solo guarda numeros no encuentra el primero, o si lo
    encuentra lo toma por el segundo y mide 0. El resultado es un array de 0
    bytes que desplaza todos los campos posteriores: un layout plausible y
    FALSO, que es el peor fallo posible porque un offset equivocado escrito
    por un driver cae en el campo de al lado sin avisar.

    Solo se indexan los directorios del subarbol de interest: barrer las
    1.5 millones de macros del arbol completo cuesta minutos y no aporta nada
    que estos headers no tengan.
    """
    if _MACRO_CONST_CACHE or _MACRO_BY_DIR:
        return _MACRO_CONST_CACHE
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
                        for line in fh:
                            m = _DEFINE_ANY.match(line.rstrip())
                            if m:
                                _register_macro(m.group(1),
                                                _define_value(m.group(2)), p)
                except OSError:
                    continue

    # Que valores distintos tiene cada simbolo en todo el subarbol. Una macro
    # con mas de un valor NO entra en el indice global: se resuelve por
    # directorio cuando hay contexto de fichero, y sin contexto se declara que
    # no se puede decidir, en vez de elegir uno al azar.
    sites: Dict[str, Set[str]] = {}
    for table in _MACRO_BY_DIR.values():
        for name, val in table.items():
            sites.setdefault(name, set()).add(val)
    for name, vals in sites.items():
        if len(vals) > 1:
            _MACRO_AMBIGUOUS[name] = sorted(vals)

    # Resolucion en cadena, con presupuesto: los alias del kernel no son
    # ciclicos, pero una herramienta mal construida si lo fuera, y un bucle
    # infinito aqui cuelga la sesion entera.
    for table in _MACRO_BY_DIR.values():
        for name, raw in table.items():
            if name in _MACRO_CONST_CACHE or name in _MACRO_AMBIGUOUS:
                continue
            seen: Set[str] = set()
            cur = raw
            val: Optional[int] = None
            for _ in range(8):
                if cur in seen:
                    break
                seen.add(cur)
                mnum = _NUM_TOK.match(cur)
                if mnum:
                    tok = mnum.group(1)
                    val = (int(tok, 16) if tok.lower().startswith("0x")
                           else int(tok))
                    break
                parts = cur.split()
                if not parts:
                    break
                cur = table.get(parts[0], parts[0])
                if cur in _MACRO_CONST_CACHE:
                    val = _MACRO_CONST_CACHE[cur]
                    break
            if val is not None:
                _MACRO_CONST_CACHE[name] = val
    return _MACRO_CONST_CACHE


# Los limites de array tambien se escriben con CONSTANTES DE ENUM, no solo con
# macros. En smu73.h:
#     enum { SCLK1, SCLK2, ..., SCLK7, NUM_VFT_COLUMNS };
# y luego
#     uint8_t Static_Voltage_Offset[NUM_VFT_COLUMNS];
# Sin resolver enums, AVFS_meanNsigma_t queda sin medir, y eso lo usa
# polaris10_smumgr.c:1872, que es la ruta de Polaris12 y no un caso de borde.
_ENUM_BLOCK = re.compile(r"\benum\s*(?P<tag>[A-Za-z_]\w*)?\s*\{(?P<body>[^{}]*)\}?")
_ENUM_CACHE: Dict[str, Dict[str, int]] = {}


def enum_constants(path: str) -> Dict[str, int]:
    """Constantes de enumeracion de un fichero, con su valor."""
    if path in _ENUM_CACHE:
        return _ENUM_CACHE[path]
    out: Dict[str, int] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        _ENUM_CACHE[path] = out
        return out
    for m in _ENUM_BLOCK.finditer(txt):
        val = 0
        for part in m.group("body").split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                name, expr = part.split("=", 1)
                name = name.strip()
                expr = expr.strip()
                mm = re.match(r"^-?(?:0[xX][0-9a-fA-F]+|\d+)", expr)
                if mm:
                    tok = mm.group(0)
                    val = int(tok, 16) if tok.lower().lstrip("-").startswith("0x") \
                        else int(tok)
                else:
                    # no se sabe: se salta la asignacion y sigue contando
                    out.setdefault(name, val)
                    val += 1
                    continue
            else:
                name = part
            if re.match(r"^[A-Za-z_]\w*$", name):
                out.setdefault(name, val)
            val += 1
    _ENUM_CACHE[path] = out
    return out


_ENUM_ALL_CACHE: Dict[str, Dict[str, int]] = {}


def enum_constant(name: str, ctx_file: str = "") -> Optional[int]:
    """Valor de una constante de enum, buscando primero el contexto."""
    if ctx_file:
        for f in include_closure(ctx_file):
            t = enum_constants(f)
            if name in t:
                return t[name]
    if not ctx_file:
        return None
    if not _ENUM_ALL_CACHE:
        amd_guess = _AMD_GUESS[0] if _AMD_GUESS else ""
        root = amd_guess
        if root and os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames
                               if d not in (".git", "__pycache__")]
                for fn in filenames:
                    if fn.endswith(".h"):
                        for k, v in enum_constants(
                                os.path.join(dirpath, fn)).items():
                            _ENUM_ALL_CACHE.setdefault(k, v)
    return _ENUM_ALL_CACHE.get(name)


_AMD_GUESS: List[str] = []


def resolve_bound(expr: str, macros: Optional[Dict[str, int]] = None,
                  ctx_file: str = "") -> Tuple[Optional[int], bool]:
    """Resuelve el contenido de un [ ... ] de array.

    Devuelve (valor, es_flexible). Acepta:
      16                 literal
      MACRO              constante de #define
      (16)               parentizada
      ARRAYDIM*2         producto si todos los factores se resuelven
      lo que no se resuelva -> (None, False): NO se inventa
    """
    e = expr.strip()
    flexible = not e
    e = e.strip("()").strip()
    if not e:
        return None, True
    macros = macros if macros is not None else _MACRO_CONST_CACHE
    # producto: separar por * conservando parentesis simples
    if "*" in e and not e.startswith("*"):
        parts = [x for x in e.split("*") if x.strip()]
        total = 1
        for pp in parts:
            v, _f = resolve_bound(pp, macros, ctx_file)
            if v is None:
                return None, False
            total *= v
        return total, False
    if re.match(r"^0[xX][0-9a-fA-F]+$", e):
        return int(e, 16), False
    if re.match(r"^\d+$", e):
        return int(e), False
    if e in macros:
        return macros[e], False
    # Contexto de fichero: la definicion mas cercana gana, como en el
    # preprocesador. Sin el, una macro redefinida por ASIC se resuelve con el
    # valor de otro ASIC y el array sale de tamano equivocado.
    if ctx_file:
        v = macro_value(e, ctx_file, macro_dir=_MACRO_BY_DIR, consts=macros)
        if v is not None:
            return v, False
    v = enum_constant(e, ctx_file)
    if v is not None:
        return v, False
    if e in _MACRO_AMBIGUOUS:
        return None, False
    return None, False


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    # 0. Valor de un #define: el corpus los escribe con comentario detras y sin
    #    quitarlos la macro desaparece del indice en silencio
    for raw, exp in (("8   // VCLK/DCLK levels", "8"),
                     ("53300 /* 10 khz */", "53300"),
                     ("0 /* ??? */", "0"),
                     ('"a//b"', '"a//b"'),
                     ("A /* x */ + 2", "A /* x */ + 2")):
        check(f"define_value({raw[:14]!r})", _define_value(raw), exp)

    # 0-bis. Array MULTIDIMENSIONAL: antes se perdia el campo entero y el struct
    #       se media como cero bytes, que es indistinguible de un struct vacio
    md, _ = parse_fields("\tSMU74_MCArbDramTimingTableEntry entries[A][B];")
    check("multidim.un_campo", len(md), 1)
    check("multidim.nombre", md[0]["name"] if md else None, "entries")
    check("multidim.dimensiones", md[0].get("dims") if md else None, ["A", "B"])
    md2, _ = parse_fields("\tuint8_t m[2][3];")
    check("multidim.producto", md2[0]["count"] if md2 else None, 6)
    md3, _ = parse_fields("\tuint8_t m[8][4];")
    check("multidim.una_dimension", md3[0]["count"] if md3 else None, 32)
    # una dimension sin resolver NO es cero: es no medido
    md4, _ = parse_fields("\tuint8_t m[8][NO_EXISTE];")
    check("multidim.sin_resolver", md4[0]["count"] if md4 else "NO", None)

    # 0-ter. Vectores cruzados con gcc 19 asserts estaticos. Estos No son
    # inventados: cada tamano y cada offset de esta tabla lo fijo el
    # compilador. Los punteros, los arrays multidimensionales y el array
    # flexible se median mal y el self-test anterior no lo cazaba porque
    # ejercitaba layout() directamente, saltandose parse_fields entero.
    _GCC = (
        # (nombre, cuerpo, sizeof, {campo: offset})
        ("Entry", "uint32_t a;\nuint32_t b;\nuint8_t c;\nuint8_t pad[3];\n",
         12, {"a": 0, "b": 4, "c": 8, "pad": 9}),
        ("Arb", "struct Entry entries[8][4];\n", 384, {"entries": 0}),
        ("DosD", "uint8_t m[2][3];\n", 6, {"m": 0}),
        ("TresD", "uint16_t m[2][3][4];\n", 48, {"m": 0}),
        ("Mix", "uint8_t a[5];\nuint32_t b[3];\n", 20, {"a": 0, "b": 8}),
        ("Ptrs", "uint32_t *p;\nstruct Entry *q[2];\nchar **argv;\n", 32,
         {"p": 0, "q": 8, "argv": 24}),
        ("Mix2", "uint8_t a;\nuint32_t *p;\nuint8_t b;\n", 24,
         {"a": 0, "p": 8, "b": 16}),
        ("Flex", "uint32_t n;\nuint8_t d[];\n", 4, {"n": 0, "d": 4}),
        ("Tbl", "uint32_t count;\nstruct Entry e[];\n", 4, {"count": 0, "e": 4}),
        ("Align", "uint8_t a[3];\nuint64_t q;\nuint16_t b;\n", 24,
         {"a": 0, "q": 8, "b": 16}),
        ("Deep", "uint8_t a;\nstruct Entry e;\nuint8_t b;\n", 20,
         {"a": 0, "e": 4, "b": 16}),
    )
    for _n, _body, _sz, _offs in _GCC:
        _f, _u = parse_fields(_body)
        check(f"gcc[{_n}].campos_no_perdidos", len(_f), len(_offs))
        _k, _ = resolve_nested(_f, "", depth=0)
        _k["Entry"] = (12, 4)
        _l = layout(_f, known=_k)
        check(f"gcc[{_n}].sizeof", _l["total_size"], _sz)
        _got = {r["name"]: r["offset"] for r in _l["rows"] if r.get("name")}
        for _fn, _fo in _offs.items():
            check(f"gcc[{_n}].{_fn}", _got.get(_fn), _fo)
    # un limite de array SIN resolver NO se cuenta como 1 elemento: seria un
    # tamano plausible y falso. Se declara y el total se invalida.
    _nr = [{"decl": "uint32_t e[NO_EXISTE]", "type": "uint32_t", "name": "e",
            "count": None, "bound_expr": "NO_EXISTE", "flexible": False,
            "bound_unresolved": True}]
    _l = layout(_nr)
    check("limite.sin_resolver_no_es_1", _l["total_size"], None)
    check("limite.declarado", _l["confidence"], "NULA")
    check("limite.marca_el_campo",
          any(r["kind"] == "limite_no_resuelto" for r in _l["rows"]), True)
    # y el struct que lo contiene tampoco puede darse por medido
    _cont = layout([{"type": "uint32_t", "name": "a", "count": 1}] + _nr)
    check("limite.contenedor_no_medido", _cont["total_size"], None)

    # Constante de ENUM como limite de array. smu73.h la usa asi:
    #     enum { SCLK1, ..., SCLK7, NUM_VFT_COLUMNS };
    #     uint8_t Static_Voltage_Offset[NUM_VFT_COLUMNS];
    # y AVFS_meanNsigma_t, que la usa, esta en la ruta de Polaris12.
    import tempfile as _tf
    _tmp = _tf.mkdtemp(prefix="sl_enum_")
    _p = os.path.join(_tmp, "e.h")
    with open(_p, "w", encoding="utf-8") as _fh:
        _fh.write("enum Sclk1 { SCLK1, SCLK2, SCLK3, NUM_VFT_COLUMNS };\n"
                  "enum Anon { A, B, C = 10, D };\n")
    check("enum.limite_basico",
          resolve_bound("NUM_VFT_COLUMNS", ctx_file=_p)[0], 3)
    check("enum.valor_explicito",
          resolve_bound("C", ctx_file=_p)[0], 10)
    check("enum.continua_despues_de_explicito",
          resolve_bound("D", ctx_file=_p)[0], 11)
    check("enum.ausente",
          resolve_bound("NO_EXISTE_ENUM", ctx_file=_p)[0], None)
    try:
        os.unlink(_p)
        os.rmdir(_tmp)
    except OSError:
        pass

    # #pragma pack(1): todo alineado a 1 byte, sin relleno. El corpus lo usa de
    # forma masiva (smu74.h:28) y sin esta regla los punteros a funcion se
    # alinean a 8 y el total sale 6 bytes mayor que el de gcc.
    _pk = [{"type": "uint32_t", "name": "a", "count": 1},
           {"type": "void (*)()", "name": "f", "count": 1},
           {"type": "uint16_t", "name": "b", "count": 1}]
    check("pack1.sin_relleno", layout(_pk, pack=1)["total_size"], 4 + 8 + 2)
    check("pack1.offsets", [r["offset"] for r in layout(_pk, pack=1)["rows"]],
          [0, 4, 12])
    # sin pack: a en 0, relleno a 8 para el puntero, relleno final a 8
    check("sin_pack.rellena",
          [r["offset"] for r in layout(_pk)["rows"]], [0, 4, 8, 16, 18])
    check("pack1.total_redondeado",
          layout(_pk, pack=1)["total_size"], 14)
    # pack(2): el puntero se alinea a 2, asi que va en 4 y b en 12
    check("pack2.limita_a_2",
          [r["offset"] for r in layout(_pk, pack=2)["rows"]], [0, 4, 12])
    check("pack2.sin_relleno_final",
          layout(_pk, pack=2)["total_size"], 14)

    # COLISION DE CACHE por longitud de needle. Dos nombres de la MISMA longitud
    # no pueden confirmar el resultado del otro. Este bug hacia que
    # SMU74_Discrete_DpmTable saliera sin medir solo por el orden de os.walk:
    # fiji_smumgr.c se recorre antes que polaris10_smumgr.c, y
    # SMU73_Discrete_DpmTable mide 23 igual que SMU74_Discrete_DpmTable.
    import tempfile as _tf3
    _t3 = _tf3.mkdtemp(prefix="sl_cache_")
    _f3 = os.path.join(_t3, "h.h")
    with open(_f3, "w", encoding="utf-8") as _fh:
        _fh.write("struct SMU74_Discrete_DpmTable { uint32_t a; };\n")
    _A = "SMU73_Discrete_DpmTable"
    _B = "SMU74_Discrete_DpmTable"
    check("cache.misma_longitud", len(_A), len(_B))
    _clean_text(_f3, _A)
    check("cache.no_colisiona",
          _B in _clean_text(_f3, _B), True)
    check("cache.ausente_sigue_ausente", _clean_text(_f3, _A) == "", True)
    try:
        os.unlink(_f3)
        os.rmdir(_t3)
    except OSError:
        pass

    # el puntero se mide como PUNTERO, no como su tipo base
    check("puntero.no_es_el_base",
          type_size("uint32_t *", {})[0], 8)
    check("puntero.doble", type_size("char **", {})[0], 8)

    # 1. gpu_pt_config_reg real del kernel: 20 bytes, sin relleno
    lay = layout([
        {"decl": "uint32_t offset", "type": "uint32_t", "name": "offset", "count": 1},
        {"decl": "uint32_t mask", "type": "uint32_t", "name": "mask", "count": 1},
        {"decl": "uint32_t shift", "type": "uint32_t", "name": "shift", "count": 1},
        {"decl": "uint32_t value", "type": "uint32_t", "name": "value", "count": 1},
        {"decl": "enum gpu_pt_config_reg_type type",
         "type": "enum gpu_pt_config_reg_type", "name": "type", "count": 1,
         "opaque": False},
    ], known={"gpu_pt_config_reg_type": (4, 4)})
    check("gpcr.sz", lay["total_size"], 20)
    check("gpcr.type_off",
          next(r["offset"] for r in lay["rows"] if r.get("name") == "type"), 16)
    # Un enum con valores > 32 bits se mide como 8 bytes, no 4.
    check("enum.no_resuelto_no_inventa",
          layout([{"type": "enum no_existe", "name": "e", "count": 1}])["confidence"],
          "NULA")

    # 2. Relleno: u8 seguido de u32 debe dejar 3 bytes
    lay2 = layout([
        {"type": "u8", "name": "a", "count": 1},
        {"type": "u32", "name": "b", "count": 1},
    ])
    check("relleno.offset_b",
          next(r["offset"] for r in lay2["rows"] if r.get("name") == "b"), 4)
    check("relleno.hay_padding",
          any(r["kind"] == "padding" for r in lay2["rows"]), True)
    check("relleno.sz", lay2["total_size"], 8)

    # 3. Array
    lay3 = layout([{"type": "u32", "name": "e", "count": 16}])
    check("array.sz", lay3["total_size"], 64)

    # 4. Puntero = 8 en x86-64
    lay4 = layout([{"type": "uint32_t *", "name": "p", "count": 1}])
    check("puntero.sz", lay4["total_size"], 8)

    # 5. __packed quita el relleno
    lay5 = layout([
        {"type": "u8", "name": "a", "count": 1},
        {"type": "u32", "name": "b", "count": 1},
    ], packed=True)
    check("packed.offset_b",
          next(r["offset"] for r in lay5["rows"] if r.get("name") == "b"), 1)
    check("packed.sz", lay5["total_size"], 5)

    # 6. Tipo desconocido: NO se inventa offset
    lay6 = layout([{"type": "mi_tipo_raro", "name": "x", "count": 1}])
    check("desconocido.medido", lay6["measured"], False)
    check("desconocino.sz_none", lay6["total_size"], None)
    check("desconocido.confianza", lay6["confidence"], "NULA")
    check("desconocido.anotado", "mi_tipo_raro" in lay6["unknown"], True)

    # 7. parse_fields: array, puntero, bitfield, multi-declaracion
    body = ("\tuint32_t count;\n"
            "\tphm_rec entries[];\n"
            "\tuint64_t *ptr;\n"
            "\tuint32_t a : 3;\n"
            "\tuint32_t b, c;\n"
            "\t/* comentario uint32_t fantasma; */\n"
            "\tuint32_t d;\n")
    flds, unk = parse_fields(body)
    names = [f.get("name") for f in flds]
    check("parse.array_flexible",
          any(f.get("name") == "entries" and f.get("flexible") for f in flds), True)
    check("parse.bitfield", any(f.get("bitfield") for f in flds), True)
    check("parse.multi_b", any(f.get("name") == "b" for f in flds), True)
    check("parse.multi_c", any(f.get("name") == "c" for f in flds), True)
    check("parse.comentario_excluido",
          any(f.get("name") == "fantasma" for f in flds), False)
    check("parse.d_visible", any(f.get("name") == "d" for f in flds), True)

    # 7-bis. typedef ANONIMO: "typedef struct { ... } NOMBRE;". El patron de
    #       esta rama se perdio al extraer el escaneo por fichero, y ningun
    #       vector lo cubria: un NameError esperando a que apareciera el primer
    #       tipo que solo existe en esa forma.
    import tempfile as _tf2
    _t2 = _tf2.mkdtemp(prefix="sl_anon_")
    # Multilinea, como los escribe el corpus: smu73.h:80 data_64_t y
    # smu73.h:85 data_128_t. Comprobado que en el corpus no hay ninguno de una
    # sola linea, asi que el caso de abajo no muerde aqui.
    with open(os.path.join(_t2, "anon.h"), "w", encoding="utf-8") as _fh:
        _fh.write("typedef struct {\n uint32_t f1;\n uint16_t f2;\n}"
                  " sclkFcwRange_t;\n")
    _hits = find_struct(_t2, "sclkFcwRange_t")
    check("anon.encontrado", len(_hits), 1)
    check("anon.tipo", _hits[0]["kind"] if _hits else None, "typedef_anonimo")
    _fa, _ua = parse_fields(_hits[0]["body"]) if _hits else ([], [])
    check("anon.campos", len(_fa), 2)
    check("anon.size",
          layout(_fa, known={})["total_size"] if _fa else None, 8)
    # LIMITACION CONOCIDA, declarada y no maquillada: parse_fields trabaja linea
    # a linea, asi que un cuerpo de UNA SOLA linea con dos declaraciones pierde
    # la primera. No hay ninguno en el corpus; se deja el vector para que la
    # limitacion este escrita y no se descubra por sorpresa.
    _f1, _ = parse_fields("uint32_t f1; uint16_t f2;")
    check("anon.una_linea_limitacion",
          len(_f1), 1)
    try:
        os.unlink(os.path.join(_t2, "anon.h"))
        os.rmdir(_t2)
    except OSError:
        pass

    # 8. find_struct sobre un arbol temporal: un solo struct con el nombre
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        h = os.path.join(td, "smu7_hwmgr.h")
        with open(h, "w", encoding="utf-8") as fh:
            fh.write("#ifndef X\n#define X\n"
                     "struct gpu_pt_config_reg {\n"
                     "\tuint32_t offset;\n"
                     "\tuint32_t mask;\n"
                     "\tuint32_t shift;\n"
                     "\tuint32_t value;\n"
                     "\tenum gpu_pt_config_reg_type type;\n"
                     "};\n"
                     "typedef struct otro { int x; } otro;\n"
                     "#endif\n")
        hits = find_struct(td, "gpu_pt_config_reg")
        check("find.uno", len(hits), 1)
        check("find.line", hits[0]["line"] if hits else None, 3)
        f2, u2 = parse_fields(hits[0]["body"]) if hits else ([], [])
        check("find.campos", len([f for f in f2 if not f.get("bitfield")]), 5)
        # el struct equivocado no debe aparecer
        check("find.no_contamina",
              any(f.get("name") == "x" for f in f2), False)

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: calculo de layout por reglas de ABI. NO compila ni verifica.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Layout de struct del kernel: offset y tamano.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--amd-root", default=None)
    ap.add_argument("--struct", action="append", default=[], dest="structs")
    ap.add_argument("--offset", action="append", default=[],
                    help="campo cuyo offset se pide")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)
    amd_root = os.path.abspath(args.amd_root) if args.amd_root else \
        os.path.join(kernel, "drivers/gpu/drm/amd")
    roots = [amd_root, os.path.join(kernel, "include")]

    # Las constantes de macro se cargan UNA vez: sin ellas los limites de
    # array no se resuelven y todo el layout posterior se desplaza.
    SL_MACROS = macro_constants([os.path.join(amd_root, "include"),
                                 os.path.join(kernel, "include"),
                                 os.path.join(amd_root, "pm")])
    # El banner va a stderr cuando se pide --json. En stdout mezclaba texto con
    # el JSON y cualquier consumidor automatico fallaba al parsear: una
    # herramienta cuyo modo legible por maquina no lo es, no lo es.
    _banner = (f"{NAME} {VERSION} · ABI x86-64 · WORK_CLASS=READ_ONLY\n"
               f"  constantes de macro indexadas: {len(SL_MACROS)}\n"
               f"  macros con definicion CONFLICTANTE: {len(_MACRO_AMBIGUOUS)}"
               f"  (se resuelven por directorio; sin contexto no se eligen)\n")
    print(_banner, end="", file=sys.stderr if args.json else sys.stdout)

    blocks = []
    for s in args.structs:
        hits = find_struct(amd_root, s)
        if not hits:
            blocks.append({"struct": s, "error": "PROVEN_ABSENT_EN_CORPUS",
                           "note": "busqueda exhaustiva; puede estar fuera de "
                                   "drivers/gpu/drm/amd"})
            continue
        h = hits[0]
        flds, unk = parse_fields(str(h["body"]), ctx_file=str(h["file"]))
        # Los tipos anidados se resuelven ANTES de calcular el layout. Sin esta
        # linea, SMU74_Discrete_DpmTable sale con TAMANO None porque sus tres
        # SMU74_PIDController y su SMIO_Table no estan medidos, y un solo campo
        # sin medir invalida el total entero. El corpus amdgpu es casi todo
        # structs anidados, asi que sin esto la herramienta no mide el caso
        # para el que existe.
        known, nested_unres = resolve_nested(flds, amd_root,
                                             ctx_file=str(h["file"]))
        lay = layout(flds, packed="__packed" in str(h["decl_full"]).lower()
                     or "__attribute__((packed))" in str(h["decl_full"]),
                     known=known, enum_root=str(h["file"]),
                     pack=h.get("pack"))
        blocks.append({"struct": s, "file": h["file"], "line": h["line"],
                       "kind": h["kind"], "layout": lay,
                       "parse_unknown": unk,
                       "nested_unresolved": nested_unres,
                       "other_definitions": len(hits) - 1})

    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "results": blocks},
                         indent=2, ensure_ascii=False))
        return 0
    if not blocks:
        ap.error("indica --struct")

    for b in blocks:
        print()
        print("=" * 76)
        if b.get("error"):
            print(f"  {b['struct']}: {b['error']}")
            print(f"  {b['note']}")
            continue
        print(f"  {b['struct']}  ({os.path.basename(str(b['file']))}:{b['line']})")
        if b["other_definitions"]:
            print(f"  ATENCION: {b['other_definitions']} definicion(es) mas en el corpus")
        if b["parse_unknown"]:
            print(f"  no analizado: {b['parse_unknown'][:3]}")
        lay = b["layout"]
        print(f"  TAMANO {lay['total_size']}   CONFIANZA {lay['confidence']}"
              f"{'   (packed)' if lay['packed'] else ''}")
        if lay["unknown"]:
            print(f"  tipos no resueltos: {lay['unknown'][:6]}")
        print()
        print(f"  {'offset':>8} {'tam':>6} {'al':>3}  campo")
        print("  " + "-" * 66)
        for r in lay["rows"]:
            if r["kind"] == "padding":
                print(f"  {r['offset']:>8} {r['size']:>6} {'':>3}  "
                      f"<< {r['note']} >>")
            else:
                off = "?" if r["offset"] is None else str(r["offset"])
                sz = "?" if r["size"] is None else str(r["size"])
                al = "" if r["align"] is None else str(r["align"])
                nm = r.get("name") or ""
                extra = ""
                if r.get("flexible"):
                    extra = "  (flexible: ocupa lo que quede)"
                if r.get("bitfield"):
                    extra = "  (bitfield)"
                if r.get("note"):
                    extra = f"  {r['note']}"
                print(f"  {off:>8} {sz:>6} {al:>3}  {nm}{extra}")
        if lay["confidence"] != "COMPLETA":
            print()
            print("  CONFIANZA PARCIAL: los offsets marcados '?' no se han medido.")
            print("  Un offset inventado en un driver escribe en el campo vecino.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
