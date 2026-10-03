#!/usr/bin/env python3
"""asic_resolver.py — decide si un fichero se compila para MI ASIC y qué rama ejecuta.

Por qué existe
--------------
Dos fallos míos, ambos por no hacer una pregunta mecánica antes de leer código:

1. Invertí seis documentos y unas 1250 líneas en ``si_dpm.c`` sin comprobar que
   su objeto depende de ``CONFIG_DRM_AMDGPU_SI``. Era **una línea** de
   ``legacy-dpm/Makefile``. La regla ``COMPILE_GATE_BEFORE_TRACE_GATE`` nació de
   ese error, pero una regla escrita sigue siendo un recordatorio: se olvida.

2. Afirmé que la rama ``hwmgr->chip_id == CHIP_POLARIS10`` era la nuestra porque
   el fichero se llama ``polaris10_smumgr.c``. Nuestro chip es ``CHIP_POLARIS12``
   (17), luego la condición es falsa y se ejecuta la rama ``else``, con
   constantes distintas. ``NAME_MATCH ≠ SEMANTIC_MATCH`` aplicado al **nombre del
   fichero**: el peor sitio posible, porque el nombre parece evidencia.

Las dos preguntas son mecánicas,yen las dos veces las respondí leyendo. Esta
herramienta las vuelve inseparables de la lectura.

Lo que NO hace
--------------
No dice que un fichero no se compila porque no encuentre su ``.o`` en un
Makefile. Esa es una ausencia, y las ausencias necesitan universos. Sin
``--expect`` que confirme que los Makefiles relevantes están dentro del árbol
declarado, el resultado es ``NOT_REFERENCED`` + ``[NO ABSENCE CLAIM]``.

Un parser correcto NO demuestra que la semántica del hardware sea correcta. Esta
herramienta razona sobre Makefiles y sobre el enum de ASIC. Nada más.

Uso
---
    # ¿Se compila este fichero, y bajo qué puerta?
    asic_resolver.py --kernel ROOT --chip CHIP_POLARIS12 \\
        --makefile drivers/gpu/drm/amd/pm/legacy-dpm/si_dpm.c

    # ¿Qué ramas de chip_id hay en este fichero y cuál ejecuta mi chip?
    asic_resolver.py --kernel ROOT --chip CHIP_POLARIS12 \\
        --branches drivers/gpu/drm/amd/pm/powerplay/smumgr/polaris10_smumgr.c

    asic_resolver.py --selftest

Salida: texto legible, o ``--json`` para consumo de agente.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "asic_resolver"
VERSION = "1.0.0"

# El enum de ASIC vive en la UAPI compartida, no dentro de amdgpu. Es el único
# lugar donde un valor CHIP_* tiene un número, y ese número decide ramas.
ASIC_ENUM_REL = "include/drm/amd_asic_type.h"

# Nombre generico del ASIC cuando el usuario no da uno. El valor por defecto
# NO es una suposicion silenciosa: se imprime siempre en la cabecera.
DEFAULT_CHIP = "CHIP_POLARIS12"


# --------------------------------------------------------------------------
# resolucion del enum de ASIC
# --------------------------------------------------------------------------

# El fichero real usa comentarios de bloque `/* n */` detras de cada entrada, y
# en algunos sitios `, /* n */` con el numero en decimal. Mi primer regex
# aceptaba solo comentarios `#`, y devolvia un enum vacio: cero findings sobre
# un fichero que si define 40 constantes. Un parser que no parsea no avisa.
_ENUM_ENTRY = re.compile(
    r"^\s*(CHIP_[A-Z0-9_]+)\s*,?\s*(?:/\*\s*([0-9]+)\s*\*/)?\s*$"
)


def parse_asic_enum(path: str) -> Dict[str, int]:
    """Devuelve {NOMBRE: valor} del enum de ASIC.

    Se admiten las dos convenciones que aparecen en el fichero real: comentario
    ``/* n */`` tras la entrada, y enumeracion implicita por posicion.
    """
    out: Dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    implicit = 0
    in_enum = False
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
            m = _ENUM_ENTRY.match(s)
            if not m:
                # Linea que no parsea dentro del enum: no la fuerzo, y no la
                # cuento como entrada. Contarla seria inventar un valor.
                continue
            name = m.group(1)
            if m.group(2) is not None:
                out[name] = int(m.group(2))
                implicit = int(m.group(2)) + 1
            else:
                out[name] = implicit
                implicit += 1
    return out


# --------------------------------------------------------------------------
# Makefiles: alcanzabilidad y puertas
# --------------------------------------------------------------------------

_OBJ_RE = re.compile(r"([A-Za-z0-9_./-]+?)\.o\b")
_INCLUDE_RE = re.compile(r"^\s*include\s+(?:\$\(|\s*)?(.*)$")
_VAR_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*([:+?]?=)\s*(.*)$")
_MAKE_INCLUDE_EXT = re.compile(r"(?:.*[/])?([A-Za-z0-9_.-]*Makefile)\s*$")


def _strip_line(line: str) -> str:
    """Quita el comentario final respetando los \\ de continuacion."""
    out, i = [], 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            out.append(line[i : i + 2])
            i += 2
            continue
        if ch == "#":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def _logical_lines(path: str) -> List[Tuple[int, str]]:
    """Devuelve [(numero_de_linea, texto_logico_unido)].

    Las continuaciones con \\ se unen: una lista de objetos partida en tres
    lineas es una sola regla, y leerla linea a linea produce ausencias falsas.
    Esa es exactamente la trampa de si_dpm.c.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.readlines()
    except OSError:
        return []
    out: List[Tuple[int, str]] = []
    buf, start = "", 0
    for n, line in enumerate(raw, 1):
        piece = _strip_line(line)
        if not buf and not piece.strip():
            continue
        if not buf:
            start = n
        if piece.rstrip().endswith("\\"):
            buf += piece.rstrip()[:-1]
            continue
        buf += piece
        out.append((start, buf))
        buf = ""
    if buf:
        out.append((start, buf))
    return out


def _expand_vars(text: str, table: Dict[str, str]) -> str:
    """Sustitucion de variables, dos pasadas, sin evaluar funciones de make."""
    for _ in range(3):
        def repl(m: "re.Match[str]") -> str:
            return table.get(m.group(1) or m.group(2), m.group(0))
        text = re.sub(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)|\$\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, text)
    return text


def enumerate_makefiles(root: str, max_files: int = 400) -> List[str]:
    """Todos los Makefiles/Kbuild bajo `root`, por recorrido del arbol.

    Es la forma de universo que si se puede verificar: un directorio se enumera
    entero o el universo esta incompleto, y ningun fichero puede esconderse.
    Seguir `include` es mas fiel al Make real pero no es exhaustivo, porque
    `$(addprefix $(FULL_AMD_PATH)/...)` usa variables que solo existen dentro
    del build y que aqui no se pueden resolver.
    """
    out: List[str] = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            if fn in ("Makefile", "Kbuild") or fn.endswith(".mk"):
                out.append(os.path.join(dirpath, fn))
    out.sort()
    return out[:max_files]


def collect_makefiles(start: str, kernel_root: str, max_files: int = 400) -> Tuple[List[str], List[str]]:
    """Recorre `include` desde `start` y devuelve (alcanzados, no_alcanzados)."""
    seen: List[str] = []
    unreachable: List[str] = []
    queue = [os.path.abspath(start)]
    depth_guard = 0
    while queue and len(seen) < max_files and depth_guard < 4000:
        path = queue.pop(0)
        depth_guard += 1
        ap = os.path.abspath(path)
        if ap in seen:
            continue
        if not os.path.isfile(ap):
            unreachable.append(ap)
            continue
        seen.append(ap)
        table: Dict[str, str] = {}
        logical = _logical_lines(ap)
        # primera pasada: variables escalares, para resolver includes posteriores
        for _, text in logical:
            m = _VAR_ASSIGN.match(text)
            if m and m.group(2) in (":=", "=") and "+" not in text.split("=")[0]:
                table[m.group(1)] = m.group(3).strip()
        for _, text in logical:
            m = _INCLUDE_RE.match(text)
            if not m:
                continue
            target = _expand_vars(m.group(1), table).strip()
            mt = _MAKE_INCLUDE_EXT.search(target)
            if not mt:
                continue
            cand = mt.group(1)
            for base in (os.path.dirname(ap), kernel_root,
                         os.path.join(kernel_root, "drivers/gpu/drm/amd")):
                p = os.path.join(base, cand)
                if os.path.isfile(p):
                    queue.append(p)
                    break
            else:
                unreachable.append(target)
    return seen, unreachable


def object_reference(obj: str, makefiles: Sequence[str]) -> List[Dict[str, object]]:
    """Busca las asignaciones que mencionan `obj` (p. ej. `si_dpm.o`)."""
    hits: List[Dict[str, object]] = []
    for mk in makefiles:
        for lineno, text in _logical_lines(mk):
            if obj not in text:
                continue
            lhs = text.split("=", 1)[0].strip() if "=" in text else text
            gates = re.findall(r"CONFIG_[A-Z0-9_]+", text)
            # Una puerta cuenta solo si esta en el lado izquierdo: en el derecho
            # puede ser un #define citado como argumento, no una condicion.
            lhs_gates = re.findall(r"CONFIG_[A-Z0-9_]+", lhs)
            hits.append({
                "makefile": mk,
                "line": lineno,
                "lhs": lhs,
                "gates_lhs": lhs_gates,
                "gates_any": gates,
                "gated": bool(lhs_gates),
                "text": text.strip()[:400],
            })
    return hits


def classify_target(target: str, makefiles: Sequence[str],
                    expected: Sequence[str],
                    config: Optional[Dict[str, bool]] = None,
                    universe_verified: Optional[bool] = None) -> Dict[str, object]:
    """Clasifica un .c como compilado, gateado, o no referenciado.

    `config` traduce valores declarados de CONFIG_* a booleanos. Sin el, una
    puerta se reporta pero NO se evalua: quien lee no puede afirmar que el
    fichero falta del binario, solo que falta SI la puerta esta apagada.

    `universe_verified` lo decide quien llamante. Un subdirectorio enumerado
    entero es exhaustivo por construccion; un recorrido de `include` no lo es,
    porque las variables de make que expanden las rutas viven fuera del arbol.
    """
    config = config or {}
    obj = os.path.basename(target)
    if not obj.endswith(".c"):
        obj += ".c"
    obj_name = obj[:-2] + ".o"

    if universe_verified is None:
        universe_ok = bool(expected) and all(os.path.exists(p) for p in expected)
    else:
        universe_ok = bool(universe_verified)
    hits = object_reference(obj_name, makefiles)
    gated = [h for h in hits if h["gated"]]
    ungated = [h for h in hits if not h["gated"]]
    gates = sorted({g for h in hits for g in h["gates_lhs"]})

    if ungated:
        verdict = "COMPILED_UNGATED"
        reason = f"'{obj_name}' aparece en una asignacion sin CONFIG en el lado izquierdo"
        conditional = False
    elif gated:
        undeclared = [g for g in gates if g not in config]
        if undeclared:
            verdict = "GATED_UNDECLARED"
            reason = (f"'{obj_name}' solo se compila si "
                      f"{', '.join(gates)} estan activas; valores no declarados")
            conditional = True
        elif all(config[g] for g in gates):
            verdict = "COMPILED_GATED_ON"
            reason = f"'{obj_name}' esta tras {', '.join(gates)}, declaradas activas"
            conditional = True
        else:
            off = [g for g in gates if not config[g]]
            verdict = "NOT_COMPILED_GATED_OFF"
            reason = f"'{obj_name}' esta tras {', '.join(off)}, declaradas inactivas"
            conditional = True
    else:
        verdict = "NOT_REFERENCED"
        reason = f"'{obj_name}' no aparece en los {len(makefiles)} Makefiles alcanzados"
        conditional = False

    # Solo hay claim de "no se compila" si (a) el universo esta verificado,
    # (b) existe una puerta que lo excluya, y (c) el valor de esa puerta esta
    # declarado. Un objeto no referenciado NO tiene puerta que lo excluya: no
    # hay evidencia de exclusion, solo de no-busqueda.
    absence_claim = (
        universe_ok
        and verdict in ("NOT_COMPILED_GATED_OFF", "COMPILED_GATED_ON",
                        "GATED_UNDECLARED")
        and all(g in config for g in gates)
    )
    if verdict == "NOT_REFERENCED":
        note = ("[NO ABSENCE CLAIM] el objeto no esta referenciado en ningun "
                "Makefile alcanzado. Eso no es evidencia de que no se compile: "
                "puede estarlo por una regla que este Makefile no expresa. "
                "Hay que ampliar el universo, no concluir.")
    elif verdict == "GATED_UNDECLARED":
        note = ("[CLAIM CONDICIONAL] hace falta el valor de "
                f"{', '.join(g for g in gates if g not in config)} para "
                "afirmar compilacion o no.")
    else:
        note = None

    return {
        "target": target,
        "object": obj_name,
        "verdict": verdict,
        "reason": reason,
        "conditional": conditional,
        "universe_verified": universe_ok,
        "absence_claimable": absence_claim,
        "note": note,
        "makefiles_scanned": len(makefiles),
        "hits": hits,
        "gates": gates,
        "config_used": {g: config[g] for g in gates if g in config},
    }


# --------------------------------------------------------------------------
# ramas de chip_id
# --------------------------------------------------------------------------

_COND_RE = re.compile(
    r"(chip_id|asic_type)\s*(==|!=|<=|>=|<|>)\s*(CHIP_[A-Z0-9_]+)"
)
_CMP = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def find_branches(target: str, chip: str, chip_value: int) -> Dict[str, object]:
    """Enumera las comparaciones contra CHIP_* y dice cual cumple MI chip.

    El punto de esta funcion no es buscar: es la columna `takes`. Un fichero
    llamado polaris10_smumgr.c contiene ramas para tres generaciones, y sin
    saber cual se cumple el resto de la lectura es sobre codigo muerto.
    """
    if not os.path.isfile(target):
        return {"target": target, "error": "FICHERO_NO_LEGIBLE", "branches": []}
    branches = []
    with open(target, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            for m in _COND_RE.finditer(line):
                field, op, name = m.group(1), m.group(2), m.group(3)
                branches.append({
                    "line": lineno,
                    "field": field,
                    "op": op,
                    "constant": name,
                    "text": line.strip()[:300],
                    "_taken": (field, op, name),
                })
    # Resuelvo el valor de cada constante con el enum; el evaluo aparte porque
    # el enum puede no contenerla.
    return {
        "target": target,
        "chip": chip,
        "chip_value": chip_value,
        "branches": branches,
    }


def evaluate_branches(target: str, chip: str, chip_value: int,
                      enum: Dict[str, int]) -> Dict[str, object]:
    res = find_branches(target, chip, chip_value)
    if res.get("error"):
        return res
    out = []
    for b in res["branches"]:
        const = b.pop("_taken")[2]
        cval = enum.get(const)
        op = b["op"]
        if cval is None:
            b.update({"constant_value": None, "takes": None,
                      "note": "CONSTANTE_FUERA_DEL_ENUM"})
            out.append(b)
            continue
        b["constant_value"] = cval
        b["takes"] = bool(_CMP[op](chip_value, cval))
        b["note"] = None
        out.append(b)
    res["branches"] = out
    res["taken_count"] = sum(1 for b in out if b["takes"] is True)
    res["false_count"] = sum(1 for b in out if b["takes"] is False)
    res["unknown_count"] = sum(1 for b in out if b["takes"] is None)
    return res


def enclosing_if(target: str, lineno: int, window: int = 60) -> Optional[str]:
    """Busca hacia arriba el `if (` o `} else {` mas cercano que abre la rama."""
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return None
    for i in range(min(lineno, len(lines)) - 1, max(-1, lineno - 1 - window), -1):
        s = lines[i].strip()
        if s.startswith("if (") or s.startswith("} else") or s.startswith("else"):
            return f"{i + 1}: {s[:200]}"
    return None


# --------------------------------------------------------------------------
# resolucion de #define en todo el corpus
# --------------------------------------------------------------------------

_DEFINE_RE_CACHE: Dict[str, List[Dict[str, object]]] = {}


def find_define(name: str, roots: Sequence[str], universe: Sequence[str]) -> Dict[str, object]:
    """Busca un #define por nombre EXACTO en todos los roots declarados.

    Devuelve todos los ficheros que lo definen, no el primero. Cuatro ficheros
    con el mismo #define no es un problema del corpus: es una pista de que el
    simbolo se duplica por generacion, y el generico se elige en otro sitio.
    """
    if name in _DEFINE_RE_CACHE:
        hits = _DEFINE_RE_CACHE[name]
    else:
        pat = re.compile(r"^\s*#\s*define\s+" + re.escape(name) + r"\b")
        hits = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
                for fn in filenames:
                    if not fn.endswith((".h", ".c")):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as fh:
                            for n, line in enumerate(fh, 1):
                                if pat.match(line):
                                    hits.append({
                                        "file": p,
                                        "line": n,
                                        "text": line.strip()[:300],
                                    })
                                    break  # una definicion por fichero basta
                    except OSError:
                        continue
        hits.sort(key=lambda h: (h["file"], h["line"]))
        _DEFINE_RE_CACHE[name] = hits

    universe_ok = bool(universe) and all(os.path.exists(p) for p in universe)
    claimable = universe_ok
    return {
        "name": name,
        "hits": hits,
        "file_count": len({h["file"] for h in hits}),
        "universe_verified": universe_ok,
        "absence_claimable": claimable,
        "note": None if claimable else
                "[NO ABSENCE CLAIM] faltan roots del universo; "
                "un 0 aqui no es ausencia",
    }


# --------------------------------------------------------------------------
# presentacion
# --------------------------------------------------------------------------

def _hdr(chip: str, value: Optional[int]) -> str:
    v = "?" if value is None else str(value)
    return (f"{NAME} {VERSION} · chip={chip} valor={v} · "
            f"WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE")


def render_makefile(res: Dict[str, object]) -> str:
    L = [_hdr(str(res.get("chip", DEFAULT_CHIP)), res.get("chip_value"))]
    L.append("")
    L.append(f"OBJETIVO  {res['target']}")
    L.append(f"OBJETO    {res['object']}")
    L.append(f"VEREDICTO {res['verdict']}")
    L.append(f"MOTIVO    {res['reason']}")
    if res["gates"]:
        L.append(f"PUERTAS   {', '.join(res['gates'])}")
    if res.get("config_used"):
        L.append(f"VALORES   " + ", ".join(
            f"{k}={'y' if v else 'n'}" for k, v in res["config_used"].items()))
    L.append(f"UNIVERSO  {'verificado' if res['universe_verified'] else 'NO VERIFICADO'}")
    L.append(f"ABSENCIA  {'reclamable' if res['absence_claimable'] else 'NO reclamable'}")
    if res["note"]:
        L.append(f"AVISO     {res['note']}")
    L.append("")
    L.append("EVIDENCIA (asignaciones que mencionan el objeto):")
    if not res["hits"]:
        L.append("  (ninguna)")
    for h in res["hits"]:
        gate = ",".join(h["gates_lhs"]) or "-"
        L.append(f"  {h['makefile']}:{h['line']}  [gate:{gate}]")
        L.append(f"    LHS  {h['lhs'][:160]}")
        L.append(f"    TEXTO {h['text'][:300]}")
    L.append("")
    L.append(f"Makefiles alcanzados por include: {res['makefiles_scanned']}")
    return "\n".join(L)


def render_branches(res: Dict[str, object]) -> str:
    if res.get("error"):
        return f"{_hdr(DEFAULT_CHIP, None)}\n\nERROR {res['error']}: {res['target']}"
    L = [_hdr(str(res["chip"]), int(res["chip_value"]))]
    L.append("")
    L.append(f"FICHERO   {res['target']}")
    L.append(f"compara nuestro chip contra {res['chip']} = {res['chip_value']}")
    L.append("")
    L.append(f"{'linea':>6}  {'toma':<5}  {'campo':<9} {'op':<2} {'constante':<22} valor")
    L.append("-" * 72)
    for b in res["branches"]:
        mark = {True: "SI", False: "no", None: "?"}[b["takes"]]
        val = "?" if b["constant_value"] is None else str(b["constant_value"])
        L.append(f"{b['line']:>6}  {mark:<5}  {b['field']:<9} {b['op']:<2} "
                 f"{b['constant']:<22} {val}")
        L.append(f"        {b['text'][:150]}")
        if b["takes"] is True:
            env = enclosing_if(res["target"], b["line"])
            if env:
                L.append(f"        rama abierta en {env}")
    L.append("")
    L.append(f"RESUMEN    se cumple: {res['taken_count']}   "
             f"no se cumple: {res['false_count']}   "
             f"constante no resoluble: {res['unknown_count']}")
    if res["false_count"]:
        L.append("")
        L.append("AVISO  Las ramas marcadas 'no' son CODIGO MUERTO para mi ASIC.")
        L.append("       No trazar su interior como si se ejecutara. Ese fue el")
        L.append("       error en polaris10_smumgr.c:1674, al tomar CHIP_POLARIS10")
        L.append("       por nuestra generacion solo porque el fichero se llama asi.")
    return "\n".join(L)


def render_define(res: Dict[str, object]) -> str:
    L = [_hdr(DEFAULT_CHIP, None)]
    L.append("")
    L.append(f"SIMBOLO   {res['name']}")
    L.append(f"DEFINIDO EN {res['file_count']} fichero(s)")
    if not res["hits"]:
        L.append("")
        L.append("SIN DEFINICIONES")
        L.append(f"AVISO     {res['note']}")
        return "\n".join(L)
    L.append("")
    for h in res["hits"]:
        L.append(f"  {h['file']}:{h['line']}")
        L.append(f"    {h['text'][:250]}")
    if res["file_count"] > 1:
        L.append("")
        L.append("AVISO  Multiples definiciones: el simbolo se duplica por")
        L.append("       generacion. Elegir la vigente es otro paso, no automatico.")
    return "\n".join(L)


# --------------------------------------------------------------------------
# self-test: vectores conocidos, tomados de hallazgos ya verificados a mano
# --------------------------------------------------------------------------

def selftest() -> int:
    """Vectores conocidos extraidos de hallazgos verificados manualmente.

    Cada caso afirma algo que ya se comprobo leyendo el fichero a mano. Si el
    self-test pasa, la herramienta reproduce esas lecturas; no dice nada sobre
    si las lecturas eran correctas.
    """
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    def contains(name: str, haystack: str, needle: str) -> None:
        if needle not in haystack:
            failures.append(f"{name}: no encontre {needle!r} en la salida")

    # --- vectores de enum: valores verificados a mano en amd_asic_type.h ---
    enum_src = (
        "#include <linux/types.h>\n"
        "enum amd_asic_type {\n"
        "\tCHIP_UNKNOWN,\t/* 0 */\n"
        "\tCHIP_SI,\t/* 1 */\n"
        "\tCHIP_POLARIS10,\t/* 15 */\n"
        "\tCHIP_POLARIS11,\t/* 16 */\n"
        "\tCHIP_POLARIS12,\t/* 17 */\n"
        "\tCHIP_VEGA10,\t/* 19 */\n"
        "};\n"
    )
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "amd_asic_type.h")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(enum_src)
        enum = parse_asic_enum(p)
        check("enum.POLARIS10", enum.get("CHIP_POLARIS10"), 15)
        check("enum.POLARIS12", enum.get("CHIP_POLARIS12"), 17)
        check("enum.UNKNOWN", enum.get("CHIP_UNKNOWN"), 0)
        check("enum.VEGA10", enum.get("CHIP_VEGA10"), 19)

        # --- vector de gate: el caso que costo seis documentos ---
        legacy = os.path.join(td, "Makefile")
        with open(legacy, "w", encoding="utf-8") as fh:
            fh.write(
                "LEGACYDPM_MGR-y = legacy_dpm.o\n"
                "LEGACYDPM_MGR-$(CONFIG_DRM_AMDGPU_CIK)+= kv_dpm.o kv_smc.o\n"
                "LEGACYDPM_MGR-$(CONFIG_DRM_AMDGPU_SI)+= si_dpm.o si_smc.o\n"
            )
        si_off = {"CONFIG_DRM_AMDGPU_SI": False}
        si_on = {"CONFIG_DRM_AMDGPU_SI": True}

        check("gate.si_dpm.sin_valor",
              classify_target("si_dpm.c", [legacy], [legacy])["verdict"],
              "GATED_UNDECLARED")
        check("gate.si_dpm.sin_valor.no_claim",
              classify_target("si_dpm.c", [legacy], [legacy])["absence_claimable"],
              False)
        # Este es el cierre mecanico del error de seis documentos:
        # CONFIG_DRM_AMDGPU_SI=n  =>  si_dpm.c NO entra en el binario.
        off = classify_target("si_dpm.c", [legacy], [legacy], si_off)
        check("gate.si_dpm.apagada", off["verdict"], "NOT_COMPILED_GATED_OFF")
        check("gate.si_dpm.apagada.claim", off["absence_claimable"], True)
        check("gate.si_dpm.apagada.gates", off["gates"], ["CONFIG_DRM_AMDGPU_SI"])
        on = classify_target("si_dpm.c", [legacy], [legacy], si_on)
        check("gate.si_dpm.encendida", on["verdict"], "COMPILED_GATED_ON")

        check("gate.legacy_dpm.o",
              classify_target("legacy_dpm.c", [legacy], [legacy])["verdict"],
              "COMPILED_UNGATED")
        # Objeto no referenciado: no es ausencia, con o sin universo verificado,
        # porque no hay ninguna puerta que lo excluya.
        nr = classify_target("no_existe.c", [legacy], [legacy])
        check("gate.ausente.verdict", nr["verdict"], "NOT_REFERENCED")
        check("gate.ausente.no_claim", nr["absence_claimable"], False)
        nr2 = classify_target("no_existe.c", [legacy], [td])
        check("gate.ausente.universo_ok", nr2["universe_verified"], True)
        check("gate.ausente.claim_sigue_falso", nr2["absence_claimable"], False)
        contains("gate.ausente.aviso", nr2["note"] or "", "NO ABSENCE CLAIM")

        # Un CONFIG citado en el lado DERECHO no es una puerta: es un argumento.
        rhs = os.path.join(td, "rhs.Makefile")
        with open(rhs, "w", encoding="utf-8") as fh:
            fh.write("EXTRA = mi_objeto.o $(CONFIG_DRM_AMDGPU_SI)\n")
        check("gate.config_en_derecho_no_es_puerta",
              classify_target("mi_objeto.c", [rhs], [rhs])["verdict"],
              "COMPILED_UNGATED")

        # --- vector de continuacion de linea: la lista partida en varias lineas ---
        cont = os.path.join(td, "cont.Makefile")
        with open(cont, "w", encoding="utf-8") as fh:
            fh.write("SMU_MGR = smumgr.o smu8_smumgr.o tonga_smumgr.o \\\n"
                     "\t  polaris10_smumgr.o \\\n"
                     "\t  smu7_smumgr.o vega10_smumgr.o\n")
        check("continuacion.polaris10",
              classify_target("polaris10_smumgr.c", [cont], [cont])["verdict"],
              "COMPILED_UNGATED")
        # smu7_hwmgr.c vive en hwmgr/Makefile, no en este. Pedirlo aqui debe dar
        # NOT_REFERENCED, no COMPILED: el nombre parecido no es el objeto.
        check("continuacion.pariente_no_es_el_mismo",
              classify_target("smu7_hwmgr.c", [cont], [cont])["verdict"],
              "NOT_REFERENCED")

        # --- vectores de rama: el error de chip_id ---
        src = os.path.join(td, "smumgr.c")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(
                "static int f(struct pp_hwmgr *hwmgr)\n{\n"
                "\tif (hwmgr->chip_id == CHIP_POLARIS10) {\n"
                "\t\ta = 1;\n"
                "\t} else {\n"
                "\t\tb = 2;\n"
                "\t}\n"
                "\tif ((hwmgr->chip_id == CHIP_POLARIS12) ||\n"
                "\t    x)\n"
                "\t\tc = 3;\n"
                "\treturn hwmgr->chip_id < CHIP_VEGA10;\n"
                "}\n"
            )
        r = evaluate_branches(src, "CHIP_POLARIS12", 17, enum)
        lines = {b["line"]: b for b in r["branches"]}
        # Numeros de linea contados sobre el literal de arriba:
        #   1 static int f(...)   2 {   3 if (chip_id == CHIP_POLARIS10)
        #   8 if ((chip_id == CHIP_POLARIS12) ||   11 return chip_id < CHIP_VEGA10
        check("rama.POLARIS10.linea3", lines[3]["line"], 3)
        check("rama.POLARIS10.no_toma", lines[3]["takes"], False)
        check("rama.POLARIS12.linea8", lines[8]["takes"], True)
        # 17 < 19 (CHIP_VEGA10): la comparacion por rango SI se cumple para
        # nosotros. Es el caso donde el nombre del fichero no dice nada y el
        # orden del enum si: Polaris queda antes que Vega.
        check("rama.VEGA10.linea11", lines[11]["takes"], True)
        check("rama.resumen.taken", r["taken_count"], 2)
        check("rama.resumen.false", r["false_count"], 1)
        env = enclosing_if(src, 3)
        contains("rama.enclosing_if", env or "", "chip_id == CHIP_POLARIS10")
        rendered = render_branches(r)
        contains("render.aviso_codigo_muerto", rendered, "CODIGO MUERTO")

        # --- una constante fuera del enum no puede evaluarse: se declara ---
        src2 = os.path.join(td, "otro.c")
        with open(src2, "w", encoding="utf-8") as fh:
            fh.write("\tif (hwmgr->chip_id == CHIP_FUTURO)\n\t\tx = 1;\n")
        r2 = evaluate_branches(src2, "CHIP_POLARIS12", 17, enum)
        check("rama.constante_desconocida", r2["unknown_count"], 1)
        check("rama.constante_desconocida.takes",
              r2["branches"][0]["takes"], None)

        # --- entrada vacia y entrada malformada no rompen nada ---
        empty = os.path.join(td, "empty.c")
        open(empty, "w").close()
        check("vacio.sin_branches", evaluate_branches(empty, "CHIP_POLARIS12", 17, enum)["branches"], [])
        check("inexistente.error",
              evaluate_branches(os.path.join(td, "nope.c"), "CHIP_POLARIS12", 17, enum).get("error"),
              "FICHERO_NO_LEGIBLE")
        check("enum_inexistente", parse_asic_enum(os.path.join(td, "nope.h")), {})

        # --- define: 0 hits no es ausencia si el universo no esta verificado ---
        d = find_define("NO_EXISTE_JA", [td], [])
        check("define.sin_hits", d["file_count"], 0)
        check("define.sin_hits.no_claim", d["absence_claimable"], False)
        with open(os.path.join(td, "a.h"), "w", encoding="utf-8") as fh:
            fh.write("#define VOLTAGE_SCALE 4\n")
        with open(os.path.join(td, "b.h"), "w", encoding="utf-8") as fh:
            fh.write("#define VOLTAGE_SCALE 4\n")
        d2 = find_define("VOLTAGE_SCALE", [td], [td])
        check("define.multiples_ficheros", d2["file_count"], 2)
        contains("define.aviso_multiples", render_define(d2), "Multiples definiciones")
        # Un prefijo no debe hacer match: se busca por nombre EXACTO.
        with open(os.path.join(td, "c.h"), "w", encoding="utf-8") as fh:
            fh.write("#define VOLTAGE_SCALE_EXTRA 9\n")
        check("define.nombre_exacto",
              find_define("VOLTAGE_SCALE", [td], [td])["file_count"], 2)

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: pasar esto NO valida la semantica del hardware.")
    return 0


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog=NAME,
        description="Compile-gate y evaluacion de ramas por ASIC. Solo lectura.")
    ap.add_argument("--selftest", action="store_true",
                    help="ejecuta los vectores conocidos y sale")
    ap.add_argument("--kernel", help="raiz del arbol del kernel (linux-N.N.N)")
    ap.add_argument("--chip", default=DEFAULT_CHIP,
                    help=f"nombre del ASIC (por defecto {DEFAULT_CHIP})")
    ap.add_argument("--makefile", action="append", default=[],
                    help="fichero .c cuya compilacion hay que decidir (repetible)")
    ap.add_argument("--branches", action="append", default=[],
                    help="fichero .c del que extraer ramas por chip_id (repetible)")
    ap.add_argument("--define", action="append", default=[], dest="defines",
                    help="simbolo #define a resolver en todo el corpus (repetible)")
    ap.add_argument("--amd-root", default=None,
                    help="raiz de drivers/gpu/drm/amd (por defecto bajo --kernel)")
    ap.add_argument("--from-makefile", default=None,
                    help="Makefile raiz desde el que seguir los include "
                         "(por defecto el Makefile de --amd-root/pm)")
    ap.add_argument("--expect", action="append", default=[],
                    help="ruta que debe existir para habilitar claims de ausencia")
    ap.add_argument("--config", action="append", default=[], metavar="K=V",
                    help="valor de CONFIG_* (K=y o K=n) para evaluar puertas. "
                         "Sin esto, una puerta se reporta pero no se resuelve")
    ap.add_argument("--universe", default="pm-subtree",
                    choices=["pm-subtree", "includes", "both", "explicit"],
                    help="como se declara el universo de Makefiles. "
                         "pm-subtree enumera todos los Makefiles bajo "
                         "drivers/gpu/drm/amd/pm (exhaustivo); "
                         "includes sigue solo las directivas include (fiel pero "
                         "no exhaustivo); explicit usa solo --expect")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.kernel and (args.makefile or args.branches or args.defines):
        ap.error("--kernel es obligatorio salvo con --selftest")
    if not (args.makefile or args.branches or args.defines):
        ap.error("indica al menos --makefile, --branches o --define")

    kernel = os.path.abspath(args.kernel) if args.kernel else None
    amd_root = os.path.abspath(args.amd_root) if args.amd_root else os.path.join(
        kernel, "drivers/gpu/drm/amd")
    enum = parse_asic_enum(os.path.join(kernel, ASIC_ENUM_REL))
    chip_value = enum.get(args.chip)
    expect = [os.path.abspath(p) for p in args.expect]

    if chip_value is None:
        print(f"AVISO  '{args.chip}' no esta en {ASIC_ENUM_REL}. "
              f"Constantes conocidas: {', '.join(sorted(enum)[:8])}...")
        if args.json:
            print(json.dumps({"error": "CHIP_NO_RESOLUBLE", "chip": args.chip}))
        return 2

    start_mk = os.path.abspath(args.from_makefile) if args.from_makefile else os.path.join(
        amd_root, "pm", "Makefile")
    followed, unreachable = collect_makefiles(start_mk, kernel)

    # El universo. Enumerar un subdirectorio entero es exhaustivo por
    # construccion. Seguir includes es fiel al Make real pero NO es exhaustivo:
    # las rutas se expanden con $(FULL_AMD_PATH) y funciones addprefix/addsuffix
    # que solo existen dentro del build. Mezclarlos sin decir cual es cual
    # fabricaria ausencias.
    subtree = os.path.join(amd_root, "pm")
    enumerated: List[str] = []
    if args.universe in ("pm-subtree", "both"):
        enumerated = enumerate_makefiles(subtree)
    if args.universe == "explicit":
        makefiles = sorted(p for p in expect if os.path.isfile(p))
    else:
        makefiles = sorted(set(followed) | set(enumerated))
    universe_verified = (args.universe in ("pm-subtree", "both")
                         and bool(enumerated))
    universe_note = {
        "pm-subtree": "enumeracion exhaustiva de todos los Makefiles bajo "
                      "drivers/gpu/drm/amd/pm",
        "includes": "solo directivas include: NO exhaustivo; las rutas "
                    "expandidas con $(FULL_AMD_PATH) no se resuelven aqui",
        "both": "enumeracion del subdirectorio mas include: exhaustivo por "
                "la enumeracion del subdirectorio",
        "explicit": "solo los ficheros declarados en --expect",
    }[args.universe]

    config: Dict[str, bool] = {}
    for item in args.config:
        if "=" not in item:
            ap.error(f"--config espera K=V, recibí {item!r}")
        k, v = item.split("=", 1)
        v = v.strip().lower()
        if v in ("y", "1", "m", "true"):
            config[k.strip()] = True
        elif v in ("n", "0", "false"):
            config[k.strip()] = False
        else:
            ap.error(f"--config {item!r}: valor no booleano")

    out: Dict[str, object] = {
        "tool": NAME, "version": VERSION,
        "chip": args.chip, "chip_value": chip_value,
        "chip_enum_file": os.path.join(kernel, ASIC_ENUM_REL),
        "amd_root": amd_root,
        "universe_mode": args.universe,
        "universe_note": universe_note,
        "universe_verified": universe_verified,
        "makefiles_enumerated": len(enumerated),
        "makefiles_followed": len(followed),
        "makefiles_total": len(makefiles),
        "makefiles_unreachable": unreachable,
        "expect": expect,
        "config": config,
        "work_class": "READ_ONLY",
        "write_execution": "NONE",
    }

    blocks = []
    for t in args.makefile:
        ap_ = t if os.path.isabs(t) else os.path.join(kernel, t)
        blocks.append({"mode": "makefile",
                       **classify_target(ap_, makefiles, expect, config,
                                         universe_verified)})
    for t in args.branches:
        ap_ = t if os.path.isabs(t) else os.path.join(kernel, t)
        blocks.append({"mode": "branches",
                       **evaluate_branches(ap_, args.chip, chip_value, enum)})
    for name in args.defines:
        roots = [amd_root]
        blocks.append({"mode": "define",
                       **find_define(name, roots, expect)})
    out["results"] = blocks

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    head = _hdr(args.chip, chip_value)
    print(head)
    print(f"Makefiles alcanzados: {len(makefiles)}  "
          f"no alcanzados: {len(unreachable)}")
    if unreachable:
        print("  (includes no resueltos, pueden ser rutas de compilacion condicional)")
    for b in blocks:
        print()
        print("=" * 72)
        if b["mode"] == "makefile":
            print(render_makefile(b))
        elif b["mode"] == "branches":
            print(render_branches(b))
        else:
            print(render_define(b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
