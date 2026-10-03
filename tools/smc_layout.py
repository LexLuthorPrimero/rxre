#!/usr/bin/env python3
"""smc_layout.py — el contrato de memoria host↔firmware, derivado del offsetof.

Por qué existe
--------------
`FW_SMU_INTERPRETATION` está marcado `NOT_IN_CORPUS`: no sabemos qué hace el
firmware con las tablas que el host le entrega. Es la pregunta abierta más
importante del scope, porque de ella depende si el voltaje, el reloj o el
estado los pone el driver o el firmware.

Hay un ángulo estático que acota la respuesta sinneed de la semántica del
firmware. El driver **no copia la tabla a ciegas**: calcula la dirección de
cada sub-estructura con

    base + offsetof(TIPO, CAMPO)

sobre un bloque que vive en la SRAM del SMC. Eso significa que **el layout del
struct que usa el host es observable en el código**, y el firmware tiene que
interpretar exactamente ese layout o leerá basura.

Lo que esto responde y lo que no:

    RESUELVE   qué offset en bytes ocupa cada campo dentro del bloque que el
              firmware lee, y por tanto qué bytes son significativos
    RESUELVE   que el host y el firmware comparten un layout, o no funcionan
    NO RESUELVE qué hace el firmware con cada byte

Y por eso el hallazgo central no es el offset: es que **el bloque se direcciona
campo a campo**. Un campo que el host no rellena es un byte que el firmware lee
sin que nadie lo haya escrito.

Lo que produce
--------------
Para cada `offsetof(TIPO, CAMPO)` del subarbol:
  · el offset en bytes, resuelto con `struct_layout`
  · el tamaño del campo y del tipo contenedor
  · si el host ESCRIBE ese campo antes de enviarlo, o solo lo lee
  · el hueco que queda entre campos: memoria que nadie inicializa

Ese último es el hallazgo accionable para un driver propio: **un campo no
inicializado enviado a un firmware es una fuente de comportamiento no
determinista**, y se localiza mecánicamente.

Lo que NO hace
--------------
No dice qué significa el contenido. No simula el firmware. Solo mide el
contrato de memoria, que es la parte que el host controla.

Uso
---
    smc_layout.py --kernel RAIZ --type SMU74_Discrete_DpmTable
    smc_layout.py --kernel RAIZ --list
    smc_layout.py --kernel RAIZ --type SMU74_Discrete_DpmTable --unwritten
    smc_layout.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

NAME = "smc_layout"
VERSION = "1.0.0"

WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

# offsetof(TIPO, CAMPO) — la forma que usa el driver para direccionar campos
# dentro del bloque que lee el firmware.
OFFSETOF = re.compile(
    r"offsetof\s*\(\s*(?:struct\s+)?(?P<type>[A-Za-z_]\w*)\s*,\s*"
    r"(?P<field>\w+)\s*\)")
# La asignacion que calcula la direccion: algo = base + offsetof(...)
BASE_PLUS = re.compile(
    r"(?P<var>\w+)\s*=\s*(?P<base>[\w>.\-]+)\s*\+\s*"
    r"offsetof\s*\(\s*(?:struct\s+)?(?P<type>[A-Za-z_]\w*)\s*,\s*"
    r"(?P<field>\w+)\s*\)")
# Y la forma con offsetof dentro de una llamada, que direcciona subestructuras
OFFSETOF_CALL = re.compile(
    r"(?P<fn>\w+)\s*\([^)]*?offsetof\s*\(\s*(?P<type>SMU\d+_\w+|[A-Z]\w+)\s*,"
    r"\s*(?P<field>\w+)\s*\)[^)]*\)")

# Asignaciones que escriben en la memoria del host antes de enviarla.
# Una asignacion en C puede declarar TIPO delante: "uint32_t array = base+...".
# Exigir un LHS desnudo perdia esas, que son justamente las que calculan la
# direccion del bloque que el firmware lee.
WRITE_ASSIGN = re.compile(
    r"^\s*(?:[A-Za-z_]\w*(?:\s+|\s*\*\s*)+)?"
    r"(?P<lhs>[A-Za-z_]\w*(?:[>\-]\w*)*(?:\[[^\]]*\])*)"
    r"\s*=(?!=)\s*(?P<rhs>.+)$")


def normalize(text: str) -> Tuple[str, List[int], List[int]]:
    """Colapsa espacios y devuelve el mapa posicion_normalizada -> original.

    En C una sentencia continua en la linea siguiente cuando esta acaba en un
    operador, NO solo cuando lleva backslash. El driver escribe:

        uint32_t array = smu_data->smu7_data.dpm_table_start +
                            offsetof(SMU74_Discrete_DpmTable, GraphicsLevel);

    Unir solo por backslash no lo jointea, y el BASE_PLUS se degrada a un
    OFFSETOF suelto: se pierde la base, que es justamente el hallazgo central.
    """
    out: List[str] = []
    back: List[int] = []
    lines: List[int] = []
    line = 1
    prev_space = False
    for i, ch in enumerate(text):
        if ch == "\n":
            line += 1
        if ch.isspace():
            if prev_space:
                continue
            out.append(" ")
            back.append(i)
            lines.append(line)
            prev_space = True
        else:
            out.append(ch)
            back.append(i)
            lines.append(line)
            prev_space = False
    return "".join(out), back, lines


def lineno_at(lines: List[int], pos: int) -> int:
    return lines[pos] if pos < len(lines) else 1


def strip_comments(text: str) -> str:
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


def scan_offsets(files: Sequence[str]) -> List[Dict[str, object]]:
    """Todos los offsetof del subarbol, con su fichero y linea real."""
    out: List[Dict[str, object]] = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                clean = strip_comments(fh.read())
        except OSError:
            continue
        base = os.path.basename(f)
        norm, back, lines = normalize(clean)
        for m in BASE_PLUS.finditer(norm):
            out.append({"file": base, "line": lineno_at(lines, m.start()),
                        "type": m.group("type"), "field": m.group("field"),
                        "var": m.group("var"), "base": m.group("base"),
                        "forma": "BASE_PLUS",
                        "text": norm[m.start():m.end() + 80].strip()[:200]})
        seen = {(o["type"], o["field"]) for o in out}
        for m in OFFSETOF.finditer(norm):
            # Un OFFSETOF contenido dentro de un BASE_PLUS ya se/accountó con
            # su base. Si no se filtra aqui, el mismo campo sale dos veces: una
            # con base y otra sin ella. Y al estar la sentencia partida en dos
            # lineas, los numeros de linea DIFIEREN y el dedup por linea no
            # los detecta.
            if (m.group("type"), m.group("field")) in seen:
                continue
            lineno = lineno_at(lines, m.start())
            out.append({"file": base, "line": lineno,
                        "type": m.group("type"), "field": m.group("field"),
                        "var": None, "base": None, "forma": "OFFSETOF",
                        "text": norm[max(0, m.start() - 60):m.end() + 60]
                        .strip()[:200]})
    return out


def collect_writes(files: Sequence[str]) -> Dict[str, Set[int]]:
    """variable -> lineas donde se le asigna, para saber si se escribe."""
    writes: Dict[str, Set[int]] = {}
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                clean = strip_comments(fh.read())
        except OSError:
            continue
        for n, raw in enumerate(clean.splitlines(), 1):
            m = WRITE_ASSIGN.match(raw)
            if not m:
                continue
            lhs = m.group("lhs").strip()
            root = re.split(r"[.\[]", lhs)[0]
            writes.setdefault(root, set()).add(n)
            writes.setdefault(lhs, set()).add(n)
    return writes


def resolve_type(type_name: str, amd_root: str,
                 struct_tool) -> Optional[Dict[str, object]]:
    """Layout del struct contenedor, via struct_layout."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import struct_layout as SL
    except ImportError:
        return None
    # ANTES de parse_fields, no despues: es parse_fields quien resuelve el
    # limite del array. Con la cache vacia, [SMU74_MAX_LEVELS_GRAPHICS] no se
    # resuelve, el array mide 0 bytes y todos los campos posteriores se
    # desplazan. Layout plausible y falso.
    if not SL._MACRO_CONST_CACHE:
        SL.macro_constants([os.path.join(amd_root, "include"),
                            os.path.join(amd_root, "pm")])
    hits = SL.find_struct_cached(amd_root, type_name)
    if not hits:
        return None
    h = hits[0]
    flds, unk = SL.parse_fields(str(h["body"]))
    # Los structs amdgpu son casi todo anidamiento. Sin resolver los tipos
    # anidados, un solo campo sin medir invalida el total y la tabla entera
    # sale NULA: inútil para calcular una dirección en la SRAM del SMC.
    known, unresolved = SL.resolve_nested(flds, amd_root)
    lay = SL.layout(flds,
                    packed="__packed" in str(h["decl_full"]).lower(),
                    known=known, enum_root=str(h["file"]))
    return {"file": h["file"], "line": h["line"], "layout": lay,
            "unresolved_types": unresolved,
            "other_definitions": len(hits) - 1}


def field_row(type_name: str, field: str, lay: Dict[str, object],
              occ: Sequence[Dict[str, object]]) -> Dict[str, object]:
    rows = lay.get("rows", [])  # type: ignore[assignment]
    target = None
    for r in rows:
        if r.get("name") == field:
            target = r
            break
    return {
        "type": type_name,
        "field": field,
        "offset": target.get("offset") if target else None,
        "size": target.get("size") if target else None,
        "found": target is not None,
        "occurrences": len(occ),
        "sites": [f"{o['file']}:{o['line']}" for o in occ[:4]],
        "verdict": target.get("verdict") if target else "CAMPO_NO_ENCONTRADO",
    }


def gaps_between(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Bytes entre campos que el host no direcciona. Nobody los escribe."""
    known = [r for r in rows if r.get("offset") is not None]
    known.sort(key=lambda r: int(r["offset"]))
    out: List[Dict[str, object]] = []
    for a, b in zip(known, known[1:]):
        off_a = int(a["offset"])
        size_a = int(a["size"] or 0)
        off_b = int(b["offset"])
        end_a = off_a + size_a
        if off_b > end_a:
            out.append({"from": a["field"], "to": b["field"],
                        "start": end_a, "size": off_b - end_a})
    return out


# Llamadas de copia a la RAM del SMC. El destino suele ser
# smu_data->..._start + offsetof(TIPO, CAMPO) y la longitud una expresion de
# sizeof. Auditar esa aritmetica es la unica forma de detectar una copia
# truncada, y hay mas de cien llamadas: leerlas una a una no escala.
COPY_CALL = re.compile(
    r"\b(?P<fn>[a-z0-9_]*copy_bytes_to_smc[a-z0-9_]*)\s*\(")
# Expresion de longitud: sizeof(TIPO) con signo, factor y multiplicaciones.
SIZE_TERM = re.compile(r"(?P<sign>[+-]?)\s*"
                       r"(?:(?P<k>\d+)\s*\*\s*)?"
                       r"sizeof\s*\(\s*(?:struct\s+)?(?P<type>[A-Za-z_]\w*)\s*\)")
_LONGFN = re.compile(r"\b[A-Za-z_]\w*\s*\(")


def split_args_depth(text: str) -> List[str]:
    """Parte por comas de profundidad 0.

    Aplanar las llamadas anidadas con una sustitucion de texto destrozaba la
    expresion: "sizeof(A) - 3*sizeof(B)" se convertia en "_F_A) - 3*_F_B)", con
    el parentesis descolgado, y la longitud ya no se podia evaluar. Contar
    llaves y comas es lo unico que conserva el texto intacto, que es
    justamente lo que hace falta para analizarlo.
    """
    out: List[str] = []
    depth = 0
    cur = ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


# Las constantes de compilacion multiplican los sizeof: el driver escribe
# sizeof(SMU7_Fusion_GraphicsLevel) * SMU7_MAX_LEVELS_GRAPHICS. Sin sustituirlas
# por su valor la expresion queda con residuo no aritmetico y la copia se
# declara no resuelta aunque el tamano se sepa con exactitud.
_MACRO_IDENT = re.compile(r"\b[A-Za-z_]\w*\b")


def expand_macros(expr: str, macros: Dict[str, int]) -> str:
    """Sustituye identificadores que son macros enteras por su valor.

    Solo dentro de la aritmetica: los operandos de sizeof son TIPOS, no
    constantes, y sustituir ahi cambiaria el tipo que se pide medir.
    """
    if not macros:
        return expr
    keep: Dict[str, str] = {}

    def _stash(m: "re.Match[str]") -> str:
        key = f"__SZ_{len(keep)}__"
        keep[key] = m.group(0)
        return key

    protected = re.sub(r"sizeof\s*\(\s*(?:struct\s+)?[A-Za-z_]\w*\s*\)",
                       _stash, expr)
    expanded = _MACRO_IDENT.sub(
        lambda m: str(macros[m.group(0)]) if m.group(0) in macros
        else m.group(0), protected)
    for key, val in keep.items():
        expanded = expanded.replace(key, val)
    return expanded


_TOK_NUM = re.compile(r"\d+")
_TOK_CAST = re.compile(r"\(\s*(?:(?:struct|union|const|unsigned|signed|short|long)"
                       r"\s+)*[A-Za-z_]\w*\s*\**\s*\)")
_TOK_SIZEOF = re.compile(r"sizeof\s*\(\s*(?:struct\s+)?(?P<type>[A-Za-z_]\w*)\s*\)")
_TOK_IDENT = re.compile(r"[A-Za-z_]\w*")


class _SizeEval:
    """Evaluador de una longitud en bytes a partir de sizeof y literales.

    La version anterior acumulaba los sizeof con una expresion regular y solo
    sabia restar y sumar residuos. No sabia multiplicar, y multiplicar es la
    forma normal de una longitud en este driver:
    sizeof(SMU7_Fusion_GraphicsLevel) * SMU7_MAX_LEVELS_GRAPHICS.
    Escribir sizeof(A) * 8 devolvia None, y None se declara igual que un tipo
    que no se encuentra: dos causas distintas parecen la misma.

    La division NO se audita: sizeof(A) / sizeof(B) es un numero de elementos,
    no un numero de bytes, y aceptarla como longitud daria por buena una copia
    que copia ocho veces menos de lo que dice. Se declara y se nombra.
    """

    def __init__(self, sizes: Dict[str, int]):
        self.sizes = sizes
        self.missing: List[str] = []
        self.pos = 0
        self.text = ""

    def _bad(self, why: str) -> None:
        if why not in self.missing:
            self.missing.append(why)

    def _skip(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def expr(self) -> Optional[int]:
        left = self.term()
        if left is None:
            # Un fallo ya ha nombrado su causa. Mirar el operador que sigue
            # anade una segunda razon falsa: "sizeof(A)/sizeof(B)" reportaba
            # tambien "EXPRESION:/ sizeof", que no es el problema.
            return None
        while True:
            self._skip()
            if self.pos >= len(self.text):
                return left
            op = self.text[self.pos]
            if op in "+-":
                pass
            elif op == ")":
                # El cierre de parentesis lo consume factor(): aqui es el fin
                # natural de la expresion, no un error. Sin esta salida,
                # cualquier parentesis se declaraba sintaxis rota.
                return left
            else:
                self._bad("EXPRESION:" + self.text[self.pos:self.pos + 8].strip())
                return None
            self.pos += 1
            right = self.term()
            if left is None or right is None:
                return None
            left = left + right if op == "+" else left - right

    def term(self) -> Optional[int]:
        left = self.factor()
        while True:
            self._skip()
            if self.pos >= len(self.text):
                return left
            op = self.text[self.pos]
            if op == "*":
                self.pos += 1
                right = self.factor()
                if left is None or right is None:
                    return None
                left = left * right
            elif op == "/":
                self._bad("DIVISION_NO_AUDITABLE")
                return None
            else:
                return left

    def factor(self) -> Optional[int]:
        self._skip()
        if self.pos >= len(self.text):
            return None
        if self.text[self.pos] == "(":
            # CAST: "(uint32_t)sizeof(x)", "(u8)y". El driver castea la
            # longitud casi siempre. Sin esto el "uint32_t" se leia como un
            # identificador sin resolver y la copia se declaraba no medida
            # cuando el tamaño se sabe con exactitud. Se distingue un cast de
            # un grupo porque dentro hay un IDENTIFICADOR de tipo, no un numero.
            mc = _TOK_CAST.match(self.text, self.pos)
            if mc:
                self.pos = mc.end()
                return self.factor()
            self.pos += 1
            v = self.expr()
            self._skip()
            if self.pos < len(self.text) and self.text[self.pos] == ")":
                self.pos += 1
            else:
                # parentesis sin cerrar: se acepta en silencio y el resultado
                # parece bueno. Se declara. Pero si la expresion interior ya
                # fallo, el cierre no se puede juzgar: se informa solo del
                # fallo real, que es el que hay que arreglar.
                if v is None:
                    return None
                self._bad("PARENTESIS_NO_CERRADO")
                return None
            return v
        if self.text[self.pos] == "-":
            self.pos += 1
            v = self.factor()
            return None if v is None else -v
        m = _TOK_SIZEOF.match(self.text, self.pos)
        if m:
            self.pos = m.end()
            name = m.group("type")
            if name not in self.sizes:
                self._bad(name)
                return None
            return self.sizes[name]
        m = _TOK_NUM.match(self.text, self.pos)
        if m:
            self.pos = m.end()
            return int(m.group(0))
        m = _TOK_IDENT.match(self.text, self.pos)
        if m:
            self._bad("EXPRESION:" + m.group(0)[:24])
            self.pos = m.end()
            return None
        self._bad("EXPRESION:" + self.text[self.pos:self.pos + 8].strip())
        return None


def parse_size_expr(expr: str, sizes: Dict[str, int]) -> Tuple[Optional[int], List[str]]:
    """Resuelve una expresion de sizeof a bytes. (valor, simbolos_faltantes)

    Evalua la aritmetica completa de +, -, * y parentesis sobre sizeof y
    literales, que es lo que usa el driver:
        sizeof(A) - 3 * sizeof(B)
        sizeof(struct C) - sizeof(D) - sizeof(E)
        sizeof(T) * SMU7_MAX_LEVELS_GRAPHICS

    Lo que no resuelve devuelve None con la lista de lo que no pudo, en vez de
    inventar un numero. Un tamano inventado aqui daria por buena una copia que
    en realidad esta truncada, y una copia truncada no da error: da voltaje o
    reloj erratico.
    """
    ev = _SizeEval(sizes)
    ev.text = expr or ""
    if not ev.text.strip():
        return None, []
    total = ev.expr()
    ev._skip()
    if total is not None and ev.pos < len(ev.text):
        ev._bad("EXPRESION:" + ev.text[ev.pos:ev.pos + 8].strip())
        total = None
    if ev.missing:
        return None, ev.missing
    return total, []


def check_against_destination(row: Dict[str, object], size_of,
                              SL) -> Dict[str, object]:
    """Compara la longitud de la copia con el tamano del campo de destino."""
    # La referencia correcta NO es el tamano del campo destino sino los bytes
    # que quedan del struct DESDE ese campo. Una copia que empieza en
    # SystemFlags esta pensada para llenar de ahi hasta el final de la tabla:
    # sizeof(T) - offsetof(T, SystemFlags). Comparar contra los 4 bytes del
    # campo daba EXCEDE en las copias mas correctas del fichero.
    out: Dict[str, object] = {"field_size": None, "struct_size": None,
                              "dest_offset": None, "tail_size": None,
                              "truncada": None, "excede": None,
                              "patron": None}
    tname = row.get("dest_type")
    fname = row.get("dest_field")
    if not tname or not fname:
        # Copia a una base DESNUDA: "pi->soft_regs_start + reg_offset",
        # "si_pi->dte_table_start". No hay offsetof, luego no hay campo contra
        # el que medir, y la extension del destino la define el contrato con
        # el firmware, no un struct. Se declara como tal en vez de contarla
        # como auditada o como fallo.
        out["patron"] = "DESTINO_SIN_TIPO"
        return out
    # Si el destino lleva un offset ADEMAS del offsetof, la copia es parcial
    # por construccion y no puede estar truncada: se esta escribiendo dentro
    # del campo, no rellenandolo. El driver lo hace en bucle, entrada a
    # entrada: si_dpm.c copia sizeof(MCArbDramTimingRegisterSet) = 12 bytes
    # sobre un array de 16 entradas de 192, y las 12 son correctas.
    dest = str(row.get("dest") or "")
    m_off = OFFSETOF.search(dest)
    if m_off:
        # Solo lo que va DESPUES del offsetof. El "+" de delante
        # ("dpm_table_start + offsetof(...)") es parte de la direccion base y
        # aparece en todas las llamadas: mirarlo hacia que las 110 se
        # clasificaran como subcampo y el discriminante no discriminara nada.
        if "+" in dest[m_off.end():]:
            out["patron"] = "SUBCAMPO_CON_OFFSET"
            return out
    hits = SL.find_struct_cached(_AMD_ROOT[0], str(tname)) if _AMD_ROOT else []
    if not hits:
        return out
    h = hits[0]
    flds, _ = SL.parse_fields(str(h["body"]), ctx_file=str(h["file"]))
    known, _ = SL.resolve_nested(flds, _AMD_ROOT[0], ctx_file=str(h["file"]))
    lay = SL.layout(flds, known=known, enum_root=str(h["file"]),
                    pack=h.get("pack"))
    rows_ = lay["rows"]
    for i, rr in enumerate(rows_):
        if rr.get("name") != fname:
            continue
        # offset y tamano del campo; si es el ultimo, hasta el final del struct
        off = rr.get("offset")
        total = lay["total_size"]
        if not isinstance(off, int) or not isinstance(total, int):
            return out
        out["dest_offset"] = off
        out["field_size"] = rr.get("size")
        out["struct_size"] = total
        tail = total - off
        out["tail_size"] = tail
        ln = row.get("length_bytes")
        if not isinstance(ln, int):
            return out
        fsz = rr.get("size")
        fsz = fsz if isinstance(fsz, int) else None
        # TRES patrones legitimos, y medirlos todos en vez de suponer uno:
        #   1. el campo entero:    1 byte a un uint8_t es una copia COMPLETA
        #   2. el array del campo: 224 bytes a GraphicsLevel[7] es completa
        #   3. la cola del struct: sizeof(T) - offsetof(T, campo), que es como
        #      el driver sube la tabla entera al SMC
        # Comparar solo con la cola daba 36 "truncadas" que son 36 copias
        # correctas de un solo campo.
        if fsz is not None and ln == fsz:
            out["patron"] = "CAMPO_COMPLETO"
        elif fsz is not None and ln < fsz:
            out["patron"] = "PREFIXO_DE_ARRAY"
            out["truncada"] = True
        elif ln == tail:
            out["patron"] = "COLA_DEL_STRUCT"
        else:
            out["patron"] = "FUERA_DE_CATALOGO"
            out["excede"] = ln > tail
        return out
    return out


def build_size_resolver(amd_root: str, SL):
    """Devuelve una funcion tipo -> bytes, cacheada, para todo el subarbol.

    Se factoriza fuera de audit_copies porque coverage necesita lo mismo y dos
    copias de la logica de medicion divergen: una corrige un fallo y la otra no.
    """
    size_cache: Dict[str, Optional[int]] = {}

    def size_of(t: str) -> Optional[int]:
        # Los PRIMITIVOS tienen tamano conocido por el ABI y no aparecen en
        # ningun header. Sin esta linea, sizeof(u8) y sizeof(u32) salian como
        # "tipo no medido" y 77 de 110 copias quedaban sin auditar: la mitad del
        # corpus de copias descartado por no saber que un u32 ocupa 4 bytes.
        prim = SL.ABI64.get(t)
        if prim is not None:
            size_cache[t] = prim[0]
            return prim[0]
        if t in size_cache:
            return size_cache[t]
        hits = SL.find_struct_cached(amd_root, t)
        if not hits:
            size_cache[t] = None
            return None
        h = hits[0]
        body = str(h["body"])
        # ctx_file y pack son OBLIGATORIOS para medir bien: sin ellos se toma
        # la definicion del struct equivocada cuando el kernel lo redefine por
        # ASIC, y se ignoran los #pragma pack(push, 1) del subarbol.
        flds, _ = SL.parse_fields(body, ctx_file=str(h["file"]))
        # Un cuerpo con contenido que produce CERO campos no es un struct de
        # cero bytes: es un cuerpo que no se ha parseado. Una union en linea,
        # una declaracion con sintaxis no contemplada, todo eso. Devolver 0
        # hace que la copia de 384 bytes se audite como copia de 0 y se de por
        # buena. Lo que no se midio se declara que no se midio.
        if not flds and body.strip():
            size_cache[t] = None
            return None
        known, _ = SL.resolve_nested(flds, amd_root, ctx_file=str(h["file"]))
        lay = SL.layout(flds, known=known, enum_root=str(h["file"]),
                        pack=h.get("pack"))
        size_cache[t] = (lay["total_size"]
                         if isinstance(lay["total_size"], int) and lay["total_size"] > 0
                         else None)
        return size_cache[t]

    return size_of


def audit_copies(files: Sequence[str], amd_root: str,
                 struct_tool) -> Dict[str, object]:
    """Audita cada llamada de copia a la SMC: destino y longitud.

    El destino es base + offsetof(TIPO,CAMPO) y la longitud una expresion de
    sizeof. Si la longitud no cubre lo que el destino promete, la copia esta
    truncada y el firmware lee basura. Con mas de cien llamadas, revisarlas a
    mano no escala, y una copia truncada es un fallo silencioso: no da error,
    solo voltaje o reloj erratico.
    """
    SL = struct_tool
    _AMD_ROOT[:] = [amd_root]
    if not SL._MACRO_CONST_CACHE:
        SL.macro_constants([os.path.join(amd_root, "include"),
                            os.path.join(amd_root, "pm")])
    size_of = build_size_resolver(amd_root, SL)
    locals_map = local_types(files)

    rows: List[Dict[str, object]] = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                clean = strip_comments(fh.read())
        except OSError:
            continue
        base = os.path.basename(f)
        norm, back, lines = normalize(clean)
        for m in COPY_CALL.finditer(norm):
            # isolating the argument list, honouring nesting
            i = m.end() - 1
            depth = 0
            j = i
            while j < len(norm):
                if norm[j] in "([{":
                    depth += 1
                elif norm[j] in ")]}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            args_raw = norm[i + 1:j]
            # offsetof(TIPO, CAMPO) contiene una coma PROPIA, y al dividir
            # por comas parte el argumento en dos: el destino se partia por la
            # mitad y el offsetof se leia como un argumento nuevo. Se
            # sustituye por un marcador opaco ANTES de dividir, y se restauran
            # los offsetof despues para poder analizarlos.
            # Partir por profundidad: conserva el texto de cada argumento, con
            # sus offsetof y sizeof intactos, que es lo que hay que analizar.
            args = split_args_depth(args_raw)
            # Firma real, verificada en smumgr/smu7_smumgr.h:56 y
            # smumgr/smu7_smumgr.c:49
            #   (hwmgr, smc_start_address, src, byte_count, limit)
            # El quinto NO es un flag: es el limite superior de la RAM del SMC,
            # y el driver comprueba en :59 que
            #   limit > smc_start_address + byte_count
            # Llama a un flag lo que es el limite fue una suposicion mia que
            # hacia el parametro parecer intercambiable, y no lo es: define
            # hasta donde se puede escribir.
            dest = args[1] if len(args) > 1 else ""
            length = args[3] if len(args) > 3 else ""
            d_off = OFFSETOF.search(dest)
            ln, missing = parse_size_expr(length, {})
            rows.append({
                "file": base,
                "line": lineno_at(lines, m.start()),
                "fn": m.group("fn"),
                "dest": " ".join(dest.split())[:120],
                "dest_type": d_off.group("type") if d_off else None,
                "dest_field": d_off.group("field") if d_off else None,
                "length_expr": " ".join(length.split())[:120],
                "_len": ln, "_missing": missing,
                "_args": args,
            })
    # second pass: resolve sizes now that every type is known
    for r in rows:
        types = set()
        for m in SIZE_TERM.finditer(str(r["length_expr"])):
            types.add(m.group("type"))
        sizes = {}
        for t in sorted(types):
            # Un sizeof de un NOMBRE LOCAL se resuelve a su tipo declarado.
            # El tipo solo se busca cuando el nombre aparece de verdad en una
            # expresion: recorrer el arbol por los miles de nombres locales
            # del subarbol para la mayoria no usados es lo que hacia que la
            # herramienta no terminara.
            real = locals_map.get(t, "")
            real = real.replace("*", "").strip() if real else t
            sizes[t] = size_of(real)
        missing = [t for t, v in sizes.items() if v is None]
        expr = str(r["length_expr"])
        # Las macros constantes se sustituyen antes de medir. Es lo que
        # convierte sizeof(T) * SMU7_MAX_LEVELS_GRAPHICS en un numero, y sin
        # esto 42 de 110 copias se declaraban no resueltas sin motivo real.
        expr_num = expand_macros(expr, SL._MACRO_CONST_CACHE)
        total, resid = parse_size_expr(expr_num, sizes)  # type: ignore[arg-type]
        r["length_resolved_expr"] = " ".join(expr_num.split())[:120]
        r["missing"] = missing + [x for x in resid if x not in missing]
        if total is None:
            r["length_bytes"] = None
            # Dos causas MUY distintas, mezcladas en un mismo veredicto:
            #   RUNTIME_MISSING   la longitud depende de un valor que se
            #                     calcula al ejecutar. No hay nada que medir
            #                     en el codigo, y no es un fallo de la
            #                     herramienta: es una limitacion real del
            #                     analisis estatico.
            #   EVIDENCE_MISSING  falta el tipo o la macro para medirla.
            # El corpus tiene las dos y confundirlas hace que 32 sitios
            # parecieran un problema de la herramienta cuando 30 son
            # longitudes que dependen del runtime.
            runtime = [x for x in r["missing"] if x.startswith("EXPRESION:")]
            r["verdict"] = ("LARGO_EN_VARIABLE" if runtime
                            else "LARGO_NO_RESUELTO")
            r["causa"] = "RUNTIME_MISSING" if runtime else "EVIDENCE_MISSING"
        else:
            r["length_bytes"] = total
            r["verdict"] = "OK"
            r["causa"] = None

        # LA COMPARACION QUE IMPORTA: la longitud contra el tamano del campo
        # destino. Una copia mas corta que su destino no da error: el
        # firmware lee lo que dejo la copia anterior, y el sintoma es voltaje
        # o reloj erratico, no un fallo de copia. Una copia mas larga que su
        # destino escribe en el campo de al lado, que es peor.
        r.update(check_against_destination(r, size_of, SL))
        r.pop("_len", None)
        r.pop("_args", None)
        r.pop("_missing", None)
    return {"rows": rows,
            "total": len(rows),
            "ok": len([r for r in rows if r["verdict"] == "OK"]),
            "unresolved": len([r for r in rows
                               if r["verdict"] == "LARGO_NO_RESUELTO"]),
            "runtime": len([r for r in rows
                            if r["verdict"] == "LARGO_EN_VARIABLE"])}


def run_probe(tmpdir: str, type_name: str) -> Dict[str, object]:
    """Ejecuta audit_copies sobre un arbol temporal con un struct conocido."""
    import struct_layout as SL
    inc = os.path.join(tmpdir, "include")
    os.makedirs(inc, exist_ok=True)
    with open(os.path.join(inc, "probe.h"), "w", encoding="utf-8") as fh:
        fh.write("struct A { int x[100]; };\nstruct B { int y[9]; };\n")
    return audit_copies([os.path.join(tmpdir, "c.c")], tmpdir, SL)


# Declaracion de una variable o static, para resolver sizeof(NOMBRE) a su
# TIPO. El driver escribe sizeof(u16_boot_mvdd) y sizeof(avfs_memory_level_...),
# que son nombres locales, no tipos. Sin esto, la expresion parece un tipo no
# medido y la copia queda sin auditar.
_LOCAL_DECL = re.compile(
    r"^\s*(?:static\s+)?(?:const\s+)?"
    r"(?P<type>[A-Za-z_]\w*(?:\s*\*\s*\w*)?(?:\s+[A-Za-z_]\w*)?)\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*(?:=|;)")


_LOCAL_CACHE: Dict[str, Dict[str, str]] = {}

# Raiz del subarbol amdgpu en uso, para los ayudantes que lo necesitan.
_AMD_ROOT: List[str] = []


def local_types(files: Sequence[str]) -> Dict[str, str]:
    """nombre local -> tipo declarado, para resolver sizeof(NOMBRE).

    Cacheado por fichero: la version sin cache releia los ~400 ficheros del
    subarbol en cada llamada de copia, y con 110 llamadas eso son 44000
    lecturas de un arbol que no cambia. La herramienta se pasaba de dos minutos.
    """
    out: Dict[str, str] = {}
    for f in files:
        cached = _LOCAL_CACHE.get(f)
        if cached is not None:
            out.update(cached)
            continue
        per = _local_types_file(f)
        _LOCAL_CACHE[f] = per
        out.update(per)
    return out


def _local_types_file(f: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for f in [f]:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                clean = strip_comments(fh.read())
        except OSError:
            continue
        for raw in clean.splitlines():
            m = _LOCAL_DECL.match(raw)
            if not m:
                continue
            t = m.group("type").strip()
            n = m.group("name")
            if t in ("return", "if", "while", "for", "switch"):
                continue
            out.setdefault(n, t)
    return out



def resolve_base_aliases(text: str) -> Dict[str, int]:
    """Nombre local -> offset dentro de una struct, para las direcciones precalculadas.

    El driver hace esto:
        vr_config_address = dpm_table_start + offsetof(SMU74_Discrete_DpmTable, VRConfig);
        ...
        smu7_copy_bytes_to_smc(hwmgr, vr_config_address, ...);

    En la llamada de copia no aparece ningun offsetof: la direccion ya esta
    calculada. Sin resolver el alias, la union de escrituras se queda sin la mayor
    parte de las escrituras y la cobertura que sale es falsa por omision. Una
    cobertura incompleta no es cobertura.
    """
    out: Dict[str, int] = {}
    pat = re.compile(
        r"(?P<var>[A-Za-z_]\w*)\s*=\s*(?P<base>[A-Za-z_]\w*)\s*\+\s*"
        r"offsetof\s*\(\s*(?P<type>[A-Za-z_]\w*)\s*,\s*(?P<field>[A-Za-z_]\w*)\s*\)")
    for m in pat.finditer(text):
        var = m.group("var")
        base = m.group("base")
        if base in out:
            continue
        try:
            v = _field_offset(m.group("type"), m.group("field"))
        except Exception:
            continue
        if v is not None:
            out[var] = v
    return out


def _field_offset(type_name: str, field: str) -> Optional[int]:
    """offsetof de un campo, o None si no se puede medir."""
    if not _AMD_ROOT:
        return None
    root = _AMD_ROOT[0]
    hits = SL.find_struct_scoped(type_name, "", root)
    if not hits:
        return None
    h = hits[0]
    flds, _ = SL.parse_fields(str(h["body"]), ctx_file=str(h["file"]))
    known, _ = SL.resolve_nested(flds, root, ctx_file=str(h["file"]))
    lay = SL.layout(flds, known=known, enum_root=str(h["file"]), pack=h.get("pack"))
    for rr in lay["rows"]:
        if rr.get("name") == field and isinstance(rr.get("offset"), int):
            return int(rr["offset"])
    return None


def coverage(files: Sequence[str], amd_root: str, SL,
             base: str, struct: str) -> Dict[str, object]:
    """Intervalos que el host escribe dentro de una struct compartida con el firmware.

    Responde a una pregunta que un conteo no responde: no solo que escribe el host,
    sino QUE PARTE NO ESCRIBE. Un hueco en la union es memoria que el host deja como
    estaba, y a un driver propio le importa exactamente eso.
    """
    _AMD_ROOT[:] = [amd_root]
    if not SL._MACRO_CONST_CACHE:
        SL.macro_constants([os.path.join(amd_root, "include"), amd_root,
                            os.path.join(amd_root, "pm")])
    files = [f for f in files if os.path.isfile(f)]
    try:
        hits = SL.find_struct_scoped(struct, files[0], amd_root)
    except Exception:
        hits = SL.find_struct_cached(amd_root, struct)
    if not hits:
        return {"estado": "STRUCT_NO_ENCONTRADA", "base": base, "struct": struct}
    h = hits[0]
    flds, _ = SL.parse_fields(str(h["body"]), ctx_file=str(h["file"]))
    known, _ = SL.resolve_nested(flds, amd_root, ctx_file=str(h["file"]))
    lay = SL.layout(flds, known=known, enum_root=str(h["file"]), pack=h.get("pack"))
    total = lay["total_size"]
    if not isinstance(total, int):
        return {"estado": "STRUCT_NO_MEDIBLE", "base": base, "struct": struct}

    offsets: Dict[str, int] = {}
    for rr in lay["rows"]:
        if rr.get("name") and isinstance(rr.get("offset"), int):
            offsets[str(rr["name"])] = int(rr["offset"])

    size_of = build_size_resolver(amd_root, SL)
    locals_map = local_types(files)

    intervals: List[Tuple[int, int, str, int]] = []
    sin_medir = 0
    otra = 0
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError:
            continue
        clean = strip_comments(raw)
        norm, back, lines = normalize(clean)
        aliases = resolve_base_aliases(norm)
        for m in COPY_CALL.finditer(norm):
            i = m.end() - 1
            depth = 0
            j = i
            while j < len(norm):
                if norm[j] in "([{":
                    depth += 1
                elif norm[j] in ")]}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            args = split_args_depth(norm[i + 1:j])
            if len(args) < 4:
                continue
            dest = args[1]
            if base not in dest:
                continue
            # longitud: mismos tipos, mismas macros y mismos nombres locales
            # que la auditoria, para que las dos cifras no puedan divergir
            expr = expand_macros(args[3], SL._MACRO_CONST_CACHE)
            types = sorted({m.group("type") for m in SIZE_TERM.finditer(expr)})
            sizes = {}
            for t in types:
                real = locals_map.get(t, "") or t
                sizes[t] = size_of(real.replace("*", "").strip()
                                   if real else t)
            if all(v is not None for v in sizes.values()):
                ln, _ = parse_size_expr(expr, sizes)
            else:
                ln = None
            base_off = None
            mo = OFFSETOF.search(dest)
            otra_struct = False
            if mo and mo.group("type") == struct:
                base_off = offsets.get(mo.group("field"))
            else:
                for var, voff in aliases.items():
                    if var in dest:
                        base_off = voff
                        break
            if mo is not None and mo.group("type") != struct:
                # Destino de una struct DISTINTA. No es una limitacion: es otro
                # tipo, de otra generacion. Contarlo como "sin medir" mezcla
                # dos cosas que no tienen nada que ver y hace que el recuento
                # de cobertura parezca incompleto cuando es correcto.
                otra_struct = True
            if not isinstance(ln, int) or base_off is None:
                if otra_struct:
                    otra += 1
                else:
                    sin_medir += 1
                continue
            intervals.append((base_off, base_off + ln,
                              os.path.basename(f),
                              lineno_at(lines, m.start())))
    intervals.sort()
    union: List[List[int]] = []
    for a, b, _, _ in intervals:
        if union and a <= union[-1][1]:
            union[-1][1] = max(union[-1][1], b)
        else:
            union.append([a, b])
    covered = sum(b - a for a, b in union)
    gaps: List[List[int]] = []
    cursor = 0
    for a, b in union:
        if a > cursor:
            gaps.append([cursor, a])
        cursor = max(cursor, b)
    if cursor < total:
        gaps.append([cursor, total])
    return {
        "estado": "OK", "base": base, "struct": struct,
        "struct_file": h["file"], "struct_line": h["line"],
        "struct_size": total, "pack": h.get("pack"),
        "escrituras": [{"ini": a, "fin": b, "fichero": fn, "linea": ln}
                       for a, b, fn, ln in intervals],
        "intervalos_union": union,
        "bytes_cubiertos": covered,
        "huecos": gaps,
        "escrituras_sin_medir": sin_medir,
        "escrituras_de_otra_struct": otra,
        "escrituras_solo_con_offsetof": True,
    }


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    check("work_class", WORK_CLASS, "READ_ONLY")
    check("patron_base_plus", bool(BASE_PLUS.search(
        "uint32_t array = base + offsetof(SMU74_Discrete_DpmTable, GraphicsLevel);")), True)
    check("patron_offsetof", bool(OFFSETOF.search(
        "offsetof(struct foo, bar)")), True)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "a.c")
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("int f(struct pp_hwmgr *h)\n{\n"
                     "\tuint32_t array = smu_data->dpm_table_start +\n"
                     "\t\t\toffsetof(SMU74_Discrete_DpmTable, GraphicsLevel);\n"
                     "\tuint32_t sz = sizeof(struct SMU74_Discrete_GraphicsLevel) * N;\n"
                     "\t/* offsetof(Falso, NoExiste) */\n"
                     "\tmemcpy(d.drambuf, &table, 4);\n"
                     "\treturn 0;\n}\n")
        offs = scan_offsets([a])
        check("scan.uno", len(offs), 1)
        check("scan.tipo", offs[0]["type"], "SMU74_Discrete_DpmTable")
        check("scan.campo", offs[0]["field"], "GraphicsLevel")
        check("scan.forma", offs[0]["forma"], "BASE_PLUS")
        check("scan.comentario_excluido",
              any(o["field"] == "NoExiste" for o in offs), False)

        w = collect_writes([a])
        check("writes.detecta", "array" in w, True)
        # La asignacion abre en la linea 3; la 4 es la continuacion del
        # offsetof. Lo que se registra es donde ABRE la sentencia.
        check("writes.linea", 3 in w.get("array", set()), True)

        # huecos: campos a 0(4), 8(4) dejan 4 bytes entre medias
        gaps = gaps_between([
            {"field": "a", "offset": 0, "size": 4},
            {"field": "b", "offset": 8, "size": 4},
        ])
        check("gaps.detecta", len(gaps), 1)
        check("gaps.tam", gaps[0]["size"], 4)
        # adyacentes: sin hueco
        check("gaps.adyacentes", gaps_between([
            {"field": "a", "offset": 0, "size": 4},
            {"field": "b", "offset": 4, "size": 4}]), [])

        # aritmetica de sizeof: lo que decide si una copia esta truncada
        sz = {"A": 1120, "B": 36, "C": 24}
        v, miss = parse_size_expr("sizeof(A) - 3 * sizeof(B)", sz)
        check("size.resta", v, 1012)
        check("size.resta_sin_faltantes", miss, [])
        v2, m2 = parse_size_expr("sizeof(A) - sizeof(B) - sizeof(C)", sz)
        check("size.dos_restas", v2, 1120 - 36 - 24)
        v3, m3 = parse_size_expr("sizeof(A) + 8", sz)
        check("size.suma", v3, 1128)
        v4, m4 = parse_size_expr("sizeof(A)", sz)
        check("size.simple", v4, 1120)
        # un tipo que no se mide devuelve None y lo DICE, no inventa
        v5, m5 = parse_size_expr("sizeof(NO_EXISTE) - sizeof(B)", sz)
        check("size.no_resuelto", v5, None)
        check("size.no_resuelto_nombra", m5, ["NO_EXISTE"])
        # una expresion no aritmetica tampoco se resuelve
        v6, m6 = parse_size_expr("sizeof(A) / sizeof(B)", sz)
        check("size.no_aritmetica", v6, None)
        check("size.expresion_vacia", parse_size_expr("", sz)[0], None)

        # el modo de copias: una llamada real del driver
        c = os.path.join(td, "c.c")
        with open(c, "w", encoding="utf-8") as fh:
            fh.write("int f(struct pp_hwmgr *hwmgr, struct T *table)\n{\n"
                     "\treturn smu7_copy_bytes_to_smc(hwmgr,\n"
                     "\t\t\tsmu_data->dpm_table_start +\n"
                     "\t\t\toffsetof(A, SystemFlags),\n"
                     "\t\t\t(uint8_t *)&(table->SystemFlags),\n"
                     "\t\t\tsizeof(A) - 3 * sizeof(B),\n"
                     "\t\t\tSMC_RAM_END);\n}\n")
        rc = run_probe(td, "A")
        check("copies.una_llamada", rc["total"], 1)
        check("copies.destino_tipo", rc["rows"][0]["dest_type"], "A")
        check("copies.destino_campo", rc["rows"][0]["dest_field"], "SystemFlags")
        # El struct de prueba es int x[100] = 400 bytes, no 1120. Lo que se
        # comprueba es la aritmetica: 400 - 3*(int y[9]=36) = 292.
        check("copies.longitud", rc["rows"][0]["length_bytes"], 400 - 3 * 36)
        check("copies.veredicto", rc["rows"][0]["verdict"], "OK")

        # COBERTURA: la pregunta es que parte NO escribe el host, no cuanto
        # escribe. Se ejercita con un hueco a proposito en medio.
        import struct_layout as SL
        with open(os.path.join(td, "c3.c"), "w", encoding="utf-8") as fh:
            fh.write("int h(struct pp_hwmgr *hwmgr)\n{\n"
                     "\tsmu7_copy_bytes_to_smc(hwmgr, base +"
                     " offsetof(Cob, x),\n"
                     "\t\tsrc, sizeof(uint32_t), SMC_RAM_END);\n"
                     "\tsmu7_copy_bytes_to_smc(hwmgr, base +"
                     " offsetof(Cob, z),\n"
                     "\t\tsrc, sizeof(uint32_t), SMC_RAM_END);\n}\n")
        with open(os.path.join(td, "include", "probe3.h"), "w",
                  encoding="utf-8") as fh:
            # Nombre propio: en este mismo temporal ya existe un struct A, y
            # un fixture que reutiliza un nombre mide el struct equivocado.
            # Multilinea, como los escribe el corpus. En una sola linea
            # parse_fields pierde declaraciones, y eso ya esta declarado como
            # limitacion: el fixture no debe apoyarse en ella.
            fh.write("struct Cob {\n uint32_t x;\n uint32_t hueco;\n"
                     " uint32_t z;\n uint32_t t;\n};\n")
        cov = coverage([os.path.join(td, "c3.c")], td, SL, "base", "Cob")
        check("cobertura.estado", cov.get("estado"), "OK")
        check("cobertura.intervalos",
              cov.get("intervalos_union"), [[0, 4], [8, 12]])
        check("cobertura.cubierto", cov.get("bytes_cubiertos"), 8)
        # Dos huecos, no uno: se escriben x [0,4) y z [8,12), asi que quedan
        # hueco [4,8) y t [12,16) sin tocar. Pensar en un solo hueco era un
        # error de cuenta mio, no de la herramienta.
        check("cobertura.hueco_1", cov.get("huecos"), [[4, 8], [12, 16]])
        # si el host escribiese la struct entera no habria hueco
        with open(os.path.join(td, "c4.c"), "w", encoding="utf-8") as fh:
            fh.write("int i(struct pp_hwmgr *hwmgr)\n{\n"
                     "\tsmu7_copy_bytes_to_smc(hwmgr, base +"
                     " offsetof(Cob, x),\n"
                     "\t\tsrc, sizeof(Cob), SMC_RAM_END);\n}\n")
        cov2 = coverage([os.path.join(td, "c4.c")], td, SL, "base", "Cob")
        check("cobertura.sin_hueco", cov2.get("huecos"), [])
        check("cobertura.total", cov2.get("bytes_cubiertos"), 16)
        # una struct que no existe se declara, no se inventa
        cov3 = coverage([os.path.join(td, "c4.c")], td, SL, "base", "NoExiste")
        check("cobertura.ausente_declarado",
              cov3.get("estado"), "STRUCT_NO_ENCONTRADA")

        # Dos casos que el barrido del corpus Gentile y que antes pasaban por
        # buenos. Se ejercitan por el camino REAL (una llamada de copia), no
        # por una copia de la logica: un test que reimplementa lo que prueba
        # no prueba nada.
        inc2 = os.path.join(td, "include")
        os.makedirs(inc2, exist_ok=True)
        with open(os.path.join(inc2, "probe2.h"), "w", encoding="utf-8") as fh:
            fh.write("struct Opaco { union { int a; int b; } u; };\n"
                     "struct DosD { int e[8][4]; };\n")
        with open(os.path.join(td, "c2.c"), "w", encoding="utf-8") as fh:
            fh.write("int g(struct pp_hwmgr *hwmgr)\n{\n"
                     "\tsmu7_copy_bytes_to_smc(hwmgr, smu_data->a,\n"
                     "\t\tsrc, sizeof(DosD), SMC_RAM_END);\n"
                     "\tsmu7_copy_bytes_to_smc(hwmgr, smu_data->b,\n"
                     "\t\tsrc, sizeof(Opaco), SMC_RAM_END);\n}\n")
        import struct_layout as SL
        r2 = audit_copies([os.path.join(td, "c2.c")], td, SL)
        check("struct.dos_dimensiones", r2["rows"][0]["length_bytes"], 8 * 4 * 4)
        check("struct.dos_dimensiones_ok", r2["rows"][0]["verdict"], "OK")
        # un cuerpo que no se parsea NO es un struct de cero bytes: con 0 la
        # copia se declararia correcta, y no lo es
        check("struct.opaco_no_es_cero", r2["rows"][1]["length_bytes"], None)
        check("struct.opaco_declarado",
              r2["rows"][1]["verdict"], "LARGO_NO_RESUELTO")

        # expansion de macros: la multiplicacion por una constante de
        # compilacion es la forma normal de una longitud en este driver
        mac = {"SMU7_MAX_LEVELS_GRAPHICS": 8, "MAX": 4}
        ex = expand_macros("sizeof(A) * SMU7_MAX_LEVELS_GRAPHICS", mac)
        check("macro.expand", ex, "sizeof(A) * 8")
        ex2 = expand_macros("sizeof(SMU7_T) * MAX + sizeof(B)", mac)
        check("macro.no_toca_sizeof", ex2, "sizeof(SMU7_T) * 4 + sizeof(B)")
        # una macro que se parece a un tipo NO se sustituye dentro de sizeof
        ex3 = expand_macros("sizeof(MAX)", mac)
        check("macro.tipo_dentro_sizeof", ex3, "sizeof(MAX)")
        check("macro.sin_tabla", expand_macros("sizeof(A) * 8", {}), "sizeof(A) * 8")
        v7, m7 = parse_size_expr(expand_macros("sizeof(A) * SMU7_MAX_LEVELS_GRAPHICS", mac), sz)
        check("macro.longitud_final", v7, 1120 * 8)
        check("macro.sin_razon", m7, [])
        # una macro que no existe deja residuo y se dice cual es
        v8, m8 = parse_size_expr(expand_macros("sizeof(A) * NO_EXISTE", mac), sz)
        check("macro.ausente_detectado", v8, None)
        check("macro.ausente_nombre", m8, ["EXPRESION:NO_EXISTE"])
        # la division NO es auditable: sizeof(A)/sizeof(B) es un numero de
        # elementos, no de bytes, y aceptarla daria por buena una copia corta
        v9, m9 = parse_size_expr("sizeof(A) / sizeof(B)", sz)
        check("size.division_rechazada", v9, None)
        check("size.division_motivo", m9, ["DIVISION_NO_AUDITABLE"])
        # parentesis y signo menos unario
        check("size.parentesis",
              parse_size_expr("(sizeof(A) - sizeof(B)) * 2", sz)[0],
              (1120 - 36) * 2)
        check("size.unario", parse_size_expr("-sizeof(A)", sz)[0], -1120)
        # texto sobrante tras una expresion completa: no se acepta en silencio
        v10, m10 = parse_size_expr("sizeof(A) + 8 garbage", sz)
        check("size.cola_sin_leer", v10, None)
        check("size.cola_motivo", m10, ["EXPRESION:garbage"])
        # texto no balanceado: tampoco
        check("size.desbalanceado", parse_size_expr("sizeof(A) + (8", sz)[0], None)
        # expresion solo
        check("size.mas_que_nada", parse_size_expr("* 4", sz)[0], None)
        # CAST: "(uint32_t)sizeof(A)" es un entero del mismo tamaño que
        # sizeof(A). El cast no cambia el valor, solo el tipo.
        check("size.cast_simple", parse_size_expr("(uint32_t)sizeof(A)", sz)[0], 1120)
        check("size.cast_anidado",
              parse_size_expr("(uint32_t)(sizeof(A) - 4)", sz)[0], 1116)
        check("size.cast_operando",
              parse_size_expr("(uint32_t)sizeof(A) * 2", sz)[0], 2240)
        check("size.cast_desconocido",
              parse_size_expr("(mi_tipo)sizeof(A)", sz)[0], 1120)
        # un grupo con identificador DENTRO sigue siendo un grupo: si el
        # identificador no se puede medir, no se inventa
        v11, m11 = parse_size_expr("(NO_EXISTE + 4)", sz)
        check("size.grupo_con_id", v11, None)
        check("size.grupo_con_id_motivo", m11, ["EXPRESION:NO_EXISTE"])

        check("scan.sin_fichero", scan_offsets([os.path.join(td, "nope.c")]), [])
        check("writes.sin_fichero", collect_writes([os.path.join(td, "nope.c")]), {})

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: mide el contrato de memoria. NO dice que hace el firmware.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Deriva el contrato host-firmware de la tabla SMC.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--type", action="append", default=[], dest="types")
    ap.add_argument("--coverage", action="store_true",
                    help="que parte de una struct escribe el host y cual deja como estaba")
    ap.add_argument("--base", default="dpm_table_start",
                    help="variable base con la que se direcciona")
    ap.add_argument("--copies", action="store_true",
                    help="auditar todas las llamadas de copia a la SMC")
    ap.add_argument("--list", action="store_true",
                    help="listar los tipos de tabla que el driver direcciona")
    ap.add_argument("--unwritten", action="store_true",
                    help="solo campos sin escribir y huecos entre campos")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)
    amd_root = os.path.join(kernel, "drivers/gpu/drm/amd")
    pm = os.path.join(amd_root, "pm")
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(pm):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        files += [os.path.join(dirpath, f) for f in filenames
                  if f.endswith((".c", ".h"))]

    offs = scan_offsets(files)
    by_type: Dict[str, List[Dict[str, object]]] = {}
    for o in offs:
        by_type.setdefault(str(o["type"]), []).append(o)

    if args.coverage:
        import struct_layout as SL
        _st = (args.types or [""])[0]
        cov = coverage(files, amd_root, SL, args.base, _st)
        if args.json:
            print(json.dumps({"tool": NAME, "version": VERSION, **cov},
                             indent=2, ensure_ascii=False, default=str))
            return 0
        if cov.get("estado") != "OK":
            print(f"  {cov.get('estado')}: {args.base} / {_st}")
            return 2
        print(f"{NAME} {VERSION} · cobertura de escritura del host")
        print(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}")
        print()
        print(f"  struct  {_st}  ({os.path.basename(str(cov['struct_file']))}"
              f":{cov['struct_line']})  {cov['struct_size']} bytes"
              f"{'   pack=' + str(cov['pack']) if cov.get('pack') else ''}")
        print(f"  base    {args.base}")
        print()
        print(f"  {'intervalo':>18}  {'tam':>6}  sitio")
        print("  " + "-" * 74)
        for iv in cov["intervalos_union"]:
            print(f"  [{iv[0]:>6}, {iv[1]:>6})  {iv[1]-iv[0]:>6}")
        print()
        print(f"  escrituras medidas {len(cov['escrituras'])}"
              f"   de otra struct {cov.get('escrituras_de_otra_struct', 0)}"
              f"   sin medir {cov['escrituras_sin_medir']}")
        print(f"  cubierto {cov['bytes_cubiertos']} de {cov['struct_size']} bytes")
        print()
        if cov["huecos"]:
            print("  HUECOS: el host NO escribe aqui, lo deja como estaba.")
            for a, b in cov["huecos"]:
                print(f"    [{a:>6}, {b:>6})   {b-a} bytes")
            print()
            print("  Un hueco no es un error: es memoria del firmware. Un driver")
            print("  propio tiene que respetarla como espacio, no rellenarla.")
        else:
            print("  sin huecos: el host escribe la struct entera")
        return 0

    if args.copies:
        import struct_layout as SL
        res = audit_copies(files, amd_root, SL)
        if args.json:
            print(json.dumps({"tool": NAME, "version": VERSION, **res},
                             indent=2, ensure_ascii=False, default=str))
            return 0
        print(f"{NAME} {VERSION} · auditoria de copias a la RAM del SMC")
        print(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}")
        print("  Una copia truncada no da error: da voltaje o reloj erratico.")
        print()
        print(f"  llamadas {res['total']}   longitudes resueltas {res['ok']}   "
              f"no resueltas {res['unresolved']}   en variable de runtime "
              f"{res['runtime']}")
        pat: Dict[str, int] = {}
        for r in res["rows"]:  # type: ignore[index]
            k = r.get("patron") or r.get("verdict")
            pat[str(k)] = pat.get(str(k), 0) + 1
        print()
        print(" Accounting de las copias, por patron de destino:")
        for k, v in sorted(pat.items(), key=lambda x: -x[1]):
            print(f"    {k:<24} {v}")
        print()
        print(f"  TRUNCADAS {sum(1 for r in res['rows'] if r.get('truncada'))}"
              f"   EXCEDEN {sum(1 for r in res['rows'] if r.get('excede'))}")
        print()
        print(f"  {'sitio':<40} {'long':>6}  destino")
        print("  " + "-" * 104)
        for r in res["rows"]:  # type: ignore[index]
            ln = "?" if r["length_bytes"] is None else str(r["length_bytes"])
            d = f"{r['dest_type']}.{r['dest_field']}" if r["dest_type"] else \
                str(r["dest"])[:46]
            L2 = f"{r['file'][:20]}:{r['line']}"
            print(f"  {L2:<40} {ln:>6}  {d[:52]}")
            if r["verdict"] != "OK":
                print(f"      expresion: {r['length_expr'][:88]}")
                if r.get("missing"):
                    print(f"      tipos no medidos: {', '.join(r['missing'])}")
        return 0

    if args.list:
        print(f"{NAME} {VERSION} · tipos direccionados con offsetof")
        print(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}")
        print()
        for t, occ in sorted(by_type.items(),
                             key=lambda x: -len(x[1])):
            files_ = sorted({str(o["file"]) for o in occ})
            print(f"  {t:<44} {len(occ):>3} usos   {len(files_)} fichero(s)")
        return 0

    if not args.types:
        ap.error("indica --type o --list")
    import struct_layout as SL
    out_rows: List[Dict[str, object]] = []
    for t in args.types:
        occ = by_type.get(t, [])
        res = resolve_type(t, amd_root, SL)
        if not res:
            out_rows.append({"type": t, "error": "PROVEN_ABSENT_EN_CORPUS",
                             "usages": len(occ),
                             "note": "el driver lo direcciona pero su layout "
                                     "no esta en los headers del subarbol"})
            continue
        lay = res["layout"]
        rows = [field_row(t, str(o["field"]), lay,
                          [x for x in occ if x["field"] == o["field"]])
                for o in occ]
        uniq = {r["field"]: r for r in rows}
        out_rows.append({
            "type": t, "file": res["file"], "line": res["line"],
            "total_size": lay["total_size"], "confidence": lay["confidence"],
            "other_definitions": res["other_definitions"],
            "fields": list(uniq.values()),
            "gaps": gaps_between(list(uniq.values())),
            "usages": len(occ),
        })

    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "rows": out_rows},
                         indent=2, ensure_ascii=False, default=str))
        return 0

    print(f"{NAME} {VERSION} · contrato host<->firmware")
    print(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}")
    print("  El host direcciona la tabla campo a campo con offsetof. El")
    print("  firmware tiene que interpretar ESE layout o lee basura.")
    print()
    for r in out_rows:
        if r.get("error"):
            print(f"  {r['type']}: {r['error']}  ({r['usages']} usos)")
            print(f"    {r['note']}")
            continue
        print(f"  {r['type']}   TAMANO={r['total_size']}  "
              f"CONFIANZA={r['confidence']}  usos={r['usages']}")
        print(f"  {os.path.basename(str(r['file']))}:{r['line']}")
        print(f"  {'offset':>7} {'tam':>5}  campo            donde")
        print("  " + "-" * 74)
        for fl in r["fields"]:  # type: ignore[union-attr]
            off = "?" if fl["offset"] is None else str(fl["offset"])
            sz = "?" if fl["size"] is None else str(fl["size"])
            sites = ", ".join(str(s) for s in fl["sites"][:2])  # type: ignore[index]
            mark = "" if fl["found"] else "   << NO ENCONTRADO"
            print(f"  {off:>7} {sz:>5}  {str(fl['field'])[:18]:<18} {sites}{mark}")
        gaps = r["gaps"]  # type: ignore[index]
        if gaps:
            print()
            print("  HUECOS: memoria entre campos que el host direcciona")
            print("  pero no escribe. El firmware la lee sin inicializar.")
            for g in gaps:
                print(f"    offset {g['start']}  {g['size']} bytes  "
                      f"entre {g['from']} y {g['to']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
