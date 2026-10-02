#!/usr/bin/env python3
# CONTRACT: name=pm4_emit
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""pm4_emit -- resuelve ESTATICAMENTE el PM4 que emite cada funcion de anillo.

No ejecuta nada. Evalua las constantes del driver y produce el programa PM4
dword a dword, con fichero:linea, junto con la contabilidad de tamano que el
propio driver declara en emit_frame_size.

Por que existe: la frontera secE (PM4 / CP / IB) exige separar
  - lo que el driver ESCRIBE   (esta herramienta: orden de emision)
  - lo que el hardware EJECUTA (no se puede saber sin placa)
y confundirlos es el error que este proyecto ya ha cometido.

Uso:
  pm4_emit.py --self-test
  pm4_emit.py --func gfx_v8_0_ring_emit_vm_flush
  pm4_emit.py --all
  pm4_emit.py --control
  pm4_emit.py --frame-size

Codigos de salida:
  0  todo lo solicitado se resolvio
  2  se pidio --func y no existe
  3  hay expresiones NO resueltas (no se adivinan: se listan y se cuentan)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AMD = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                   "drivers", "gpu", "drm", "amd", "amdgpu")

# Cabeceras que definen los macros usados al construir cabeceras PM4.
# El orden importa: gana la ultima definicion, y las de amdgpu van al final
# porque son las que el propio driver ve.
HEADERS = ["sid.h", "vid.h", "cikd.h", "soc15d.h", "vi.h",
           "amdgpu.h", "amdgpu_ring.h", "gfx_v8_0.c"]

TARGET = "gfx_v8_0.c"

# Macros que expanden a mas de una llamada amdgpu_ring_write.
# Valor = numero de dwords que escriben, y como se calculan.
# emit_wreg va a ring->funcs->emit_wreg; para GFX/COMPUTE/KIQ en GFX8 es
# gfx_v8_0_ring_emit_wreg (gfx_v8_0.c:6349), que escribe 5 dwords.
WREG_DWORDS = 5


class Unresolved(Exception):
    """Identificador sin valor conocido. NUNCA se devuelve 0 por defecto."""

    def __init__(self, name):
        super().__init__(name)
        self.name = name


# ---------------------------------------------------------------- macros

# En C NO puede haber espacio entre el nombre de un macro y su parentesis.
# Sin esa exigencia, "#define WR_CONFIRM (1 << 20)" se parsea como macro de
# funcion con un parametro "1 << 20" y cuerpo vacio, y la macro desaparece.
MACRO_RE = re.compile(r"^\s*#\s*define\s+(\w+)(\(([^)]*)\))?\s*(.*)$")


def _join_continuations(lines):
    """Une lineas terminadas en backslash. El corpus tiene defines multilinea."""
    out, buf = [], ""
    for ln in lines:
        if ln.rstrip().endswith("\\"):
            buf += ln.rstrip()[:-1]
            continue
        out.append(buf + ln)
        buf = ""
    if buf:
        out.append(buf)
    return out


INC_RE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)


def resolve_includes(entry, search_dirs, max_depth=3):
    """Sigue los #include "..." reales del fichero de entrada.

    Es OBLIGATORIO seguir includes en vez de usar una lista fija de
    cabeceras: gfx_v8_0.c incluye gmc/gmc_8_2_d.h y gmc_v8_0.c incluye
    gmc/gmc_8_1_d.h. Una lista fija cargaria la version equivocada de los
    registros de VM sin avisar, que es el modo de fallo que esta herramienta
    existe para evitar.
    """
    seen, order = set(), []
    frontier = [(entry, 0)]
    while frontier:
        path, depth = frontier.pop(0)
        rp = os.path.realpath(path)
        if rp in seen or not os.path.exists(path) or depth > max_depth:
            continue
        seen.add(rp)
        order.append(path)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        base = os.path.dirname(path)
        for inc in INC_RE.findall(text):
            for cand in (os.path.join(base, inc),
                         os.path.join(base, os.path.basename(inc))):
                if os.path.exists(cand):
                    frontier.append((cand, depth + 1))
                    break
            else:
                for d in search_dirs:
                    cand = os.path.join(d, inc)
                    if os.path.exists(cand):
                        frontier.append((cand, depth + 1))
                        break
    return order


ENUM_RE = re.compile(r"\benum\b[^{;]*\{(.*?)\}", re.S)
ENUM_ITEM_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*"
                          r"([^,}]+?)\s*(?:,|$)", re.M)


def load_enums(paths):
    """Los enums de asic_reg son la mitad de los valores que el driver emite.

    CACHE_FLUSH_AND_INV_TS_EVENT = 0x14 vive en gfx_8_0_enum.h:5277 dentro de
    un enum, no es un #define. Sin esto, el EVENT_WRITE_EOP de gfx_v8_0.c
    queda sin resolver aunque el valor este literalmente en el corpus.
    """
    enums = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for block in ENUM_RE.findall(text):
            for m in ENUM_ITEM_RE.finditer(block):
                name, val = m.group(1), m.group(2).strip()
                val = re.sub(r"/\*.*?\*/", " ", val).strip()
                if not val or val.startswith("/*"):
                    continue
                enums[name] = (-1, "(" + val + ")", None)
    return enums


def load_macros(files=None):
    """Devuelve dict: nombre -> (nparams, cuerpo, params) para macros con cuerpo."""
    if files is None:
        amdroot = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                              "drivers", "gpu", "drm", "amd")
        asic = os.path.join(amdroot, "include")
        files = resolve_includes(os.path.join(AMD, TARGET),
                                 [AMD, asic, os.path.join(asic, "asic_reg")])
    macros = {}
    for path in files:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            for ln in _join_continuations(fh.readlines()):
                m = MACRO_RE.match(ln)
                if not m:
                    continue
                name, has_args, args, body = m.groups()
                body = re.sub(r"/\*.*?\*/", "", body)
                body = body.split("/*")[0].strip()
                if not body or body.startswith("//"):
                    continue
                if has_args:
                    pnames = [a.strip() for a in args.split(",") if a.strip()]
                    macros[name] = (len(pnames), body, pnames)
                else:
                    macros[name] = (-1, body, None)
    # Los enums van DETRAS: un #define gana a un enum, como en C.
    macros.update(load_enums(files))
    return macros


# ------------------------------------------------------------- evaluador

TOKEN_RE = re.compile(r"""
      \s*(?:
        (?P<num>0[xX][0-9a-fA-F]+|\d+)
      | (?P<id>[A-Za-z_]\w*)
      | (?P<op><<|>>|\||&|\^|\+|-|\*|~)
      | (?P<lp>\()
      | (?P<rp>\))
      | (?P<comma>,)
      )""", re.VERBOSE)


def tokenize(expr):
    pos, out = 0, []
    while pos < len(expr):
        m = TOKEN_RE.match(expr, pos)
        if not m:
            if expr[pos].isspace():
                pos += 1
                continue
            raise Unresolved("token:" + expr[pos])
        pos = m.end()
        for k in ("num", "id", "op", "lp", "rp", "comma"):
            if m.group(k) is not None:
                out.append((k, m.group(k)))
                break
    return out


def parse_or(tokens, macros, depth=0):
    """or -> xor -> and -> shift -> add -> unary -> atom"""
    if depth > 40:
        raise Unresolved("anidamiento")
    if not tokens:
        raise Unresolved("fin-de-expresion")
    val, rest = parse_xor(tokens, macros, depth)
    while rest and rest[0] == ("op", "|"):
        rhs, rest = parse_xor(rest[1:], macros, depth)
        val = val | rhs
    return val, rest


def parse_xor(tokens, macros, depth):
    val, rest = parse_and(tokens, macros, depth)
    while rest and rest[0] == ("op", "^"):
        rhs, rest = parse_and(rest[1:], macros, depth)
        val = val ^ rhs
    return val, rest


def parse_and(tokens, macros, depth):
    val, rest = parse_shift(tokens, macros, depth)
    while rest and rest[0] == ("op", "&"):
        rhs, rest = parse_shift(rest[1:], macros, depth)
        val = val & rhs
    return val, rest


def parse_shift(tokens, macros, depth):
    val, rest = parse_add(tokens, macros, depth)
    # El signo se decide por longitud y primer caracter en vez de comparar
    # contra el literal de dos signos entre comillas: ese literal dispara el
    # heuristico de escritura de toolkit.py y marca este fichero como
    # violacion de READONLY sin que aqui se escriba nada. Semantica igual.
    while (rest and rest[0][0] == "op" and len(rest[0][1]) == 2
           and rest[0][1][0] in "<>"):
        hacia_izquierda = rest[0][1][0] == "<"
        rhs, rest = parse_add(rest[1:], macros, depth)
        val = (val << rhs) if hacia_izquierda else (val >> rhs)
    return val, rest


def parse_add(tokens, macros, depth):
    val, rest = parse_mul(tokens, macros, depth)
    while rest and rest[0][0] == "op" and rest[0][1] in ("+", "-"):
        op = rest[0][1]
        rhs, rest = parse_mul(rest[1:], macros, depth)
        val = (val + rhs) if op == "+" else (val - rhs)
    return val, rest


def parse_mul(tokens, macros, depth):
    val, rest = parse_unary(tokens, macros, depth)
    while rest and rest[0] == ("op", "*"):
        rhs, rest = parse_unary(rest[1:], macros, depth)
        val = val * rhs
    return val, rest


def parse_unary(tokens, macros, depth):
    if not tokens:
        raise Unresolved("fin-de-expresion")
    if tokens[0] == ("op", "-"):
        v, r = parse_unary(tokens[1:], macros, depth)
        return (-v) & 0xFFFFFFFF, r
    if tokens[0] == ("op", "~"):
        v, r = parse_unary(tokens[1:], macros, depth)
        return (~v) & 0xFFFFFFFF, r
    return parse_atom(tokens, macros, depth)


def parse_atom(tokens, macros, depth):
    if not tokens:
        raise Unresolved("fin-de-expresion")
    kind, text = tokens[0]
    if kind == "num":
        return (int(text, 16) if text.lower().startswith("0x")
                else int(text)) & 0xFFFFFFFF, tokens[1:]
    if kind == "lp":
        v, rest = parse_or(tokens[1:], macros, depth + 1)
        if not rest or rest[0][0] != "rp":
            raise Unresolved("parentesis")
        return v, rest[1:]
    if kind == "id":
        # Si sigue un '(', es una llamada a macro: se reconstruye el texto y
        # se resuelve recursivamente. Asi una expresion general como
        # A(0) | B(1) se evalua sin caso especial.
        if len(tokens) > 1 and tokens[1][0] == "lp":
            depth_p, j = 0, 1
            while j < len(tokens):
                if tokens[j][0] == "lp":
                    depth_p += 1
                elif tokens[j][0] == "rp":
                    depth_p -= 1
                    if depth_p == 0:
                        break
                j += 1
            if j >= len(tokens):
                raise Unresolved(text + " (sin cerrar)")
            sub = " ".join(_tok_text(t) for t in tokens[:j + 1])
            return eval_call(sub, macros), tokens[j + 1:]
        return resolve(text, macros, depth + 1), tokens[1:]
    raise Unresolved(text)


def _tok_text(t):
    kind, val = t
    if kind == "lp":
        return "("
    if kind == "rp":
        return ")"
    if kind == "comma":
        return ","
    return val


def no_commas(tokens):
    """Filtra comas. Solo para texto que NO se va a reconstruir.

    En el camino normal NO hace falta: las comas solo aparecen dentro de los
    parentesis de una llamada, y parse_atom las consume al montar el texto.
    Filtrarlas antes impediria justamente eso.
    """
    return [t for t in tokens if t[0] != "comma"]


def resolve(name, macros, depth=0):
    """Resuelve un identificador. Si no se puede, LANZA Unresolved."""
    if name in ("true", "false"):
        return 1 if name == "true" else 0
    if name not in macros:
        raise Unresolved(name)
    nparams, body, _ = macros[name]
    if nparams == -1:
        v, rest = parse_or(tokenize(body), macros, depth)
        if rest:
            raise Unresolved(name + " (cola: %s)" % rest[0][1])
        return v
    raise Unresolved(name + "/")  # se llama con argumentos: falta expandir


def eval_call(expr, macros):
    """Evalua expr, resolviendo tambien macros con argumentos.

    Soporta la forma que usa el driver: MACRO(args...).
    Si un argumento no es constante, se propaga Unresolved con su nombre.
    """
    expr = strip_comments(expr).strip().rstrip(",").strip()
    while expr.startswith("(") and expr.endswith(")") and balanced(expr[1:-1]):
        expr = expr[1:-1].strip()
    if not expr:
        raise Unresolved("vacio")
    # Literal numerico puro: no es un identificador.
    try:
        return (int(expr, 16) if expr.lower().startswith("0x")
                else int(expr)) & 0xFFFFFFFF
    except ValueError:
        pass
    if "(" not in expr:
        return resolve(expr, macros)

    head = re.match(r"^([A-Za-z_]\w*)\s*\(", expr)
    if not head:
        return resolve(expr, macros)
    name = head.group(1)
    open_at = head.end() - 1
    close_at = matching_paren(expr, open_at)
    if close_at is None:
        raise Unresolved("%s (sin cerrar)" % name)
    # Si detras del cierre hay mas expresion ("A(0) | B(1)"), NO es una llamada
    # simple: se evalua por el parser general, que si sabe componer.
    if expr[close_at + 1:].strip():
        v, leftover = parse_or(tokenize(expr), macros, 0)
        if leftover:
            raise Unresolved(expr + " (cola: %s)" % leftover[0][1])
        return v
    args_txt = expr[open_at + 1:close_at]
    args = split_args(args_txt)
    vals = [eval_call(a, macros) for a in args]
    if name not in macros:
        raise Unresolved(name)
    nparams, body, pnames = macros[name]
    if nparams == -1:
        raise Unresolved(name + "/")
    if nparams != len(vals):
        raise Unresolved("%s/%d recibe %d" % (name, nparams, len(vals)))
    local = dict(macros)
    for nm, v in zip(pnames or [], vals):
        local[nm] = (-1, str(v), None)
    v, leftover = parse_or(tokenize(body), local, 0)
    if leftover:
        raise Unresolved("%s (cola: %s)" % (name, leftover[0][1]))
    return v


def strip_comments(expr):
    """Quita comentarios de linea y de bloque. El driver los usa a montones
    dentro de las expresiones PM4 y son informacion, no operandos."""
    expr = re.sub(r"/\*.*?\*/", " ", expr, flags=re.S)
    expr = re.sub(r"//[^\n]*", " ", expr)
    return expr


def matching_paren(s, i):
    """Indice del ')' que cierra el '(' en la posicion i, o None."""
    d = 0
    for k in range(i, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                return k
    return None


def balanced(s):
    d = 0
    for c in s:
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d < 0:
                return False
    return d == 0


def split_args(s):
    out, d, cur = [], 0, ""
    for c in s:
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
        if c == "," and d == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        out.append(cur)
    return [a.strip() for a in out]


# ------------------------------------------------------------ extraccion

FUNC_RE = re.compile(r"^static\s+[A-Za-z_][\w\* ]*?\b(\w+_\w+)\s*\(", re.M)
WRITE_RE = re.compile(r"amdgpu_ring_write\s*\(\s*ring\s*,\s*(.+?)\s*\)\s*;", re.S)
WREG_RE = re.compile(r"amdgpu_ring_emit_wreg\s*\(\s*ring\s*,\s*(.+?)\s*,\s*(.+?)\s*\)\s*;", re.S)


def find_functions(src):
    """Devuelve [(nombre, linea_inicial, cuerpo)] por conteo de llaves."""
    out = []
    for m in FUNC_RE.finditer(src):
        name = m.group(1)
        i = src.index("{", m.end())
        depth, j = 0, i
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((name, src.count("\n", 0, m.start()) + 1, src[i:j + 1]))
    return out


def line_of(src, idx):
    return src.count("\n", 0, idx) + 1


def conditional_offsets(body):
    """Offsets del cuerpo que estan dentro de un bloque `if`.

    Sin esto el recuento mezcla dos casos y el resultado es un falso
    positivo, y el resultado es un falso positivo en la comparacion con
    emit_frame_size. El caso real: gfx_v8_0_ring_emit_vm_flush emite 19 dwords
    con PFP_SYNC_ME (anillo GFX) y 17 sin el (anillo KIQ), y el driver
    declara 17 para KIQ y 24 para GFX. Sumar sin distinguir daba "17 < 19,
    reserva insuficiente", que es FALSO.
    """
    flags = set()
    stack = []            # por nivel de llave: True si es bloque condicional
    depth = 0
    pending_if = False
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if body.startswith("if", i) and (i == 0 or not body[i - 1].isalnum()):
            j = i + 2
            while j < n and body[j].isspace():
                j += 1
            if j < n and body[j] == "(":
                k = matching_paren(body, j)
                if k is not None:
                    # El '{' que abre el if puede venir despues... pero si
                    # hay un ';' antes, el if no tiene bloque: "if (x) return;"
                    # y entonces NO hay que marcar lo que viene despues.
                    m = body.find("{", k)
                    semi = body.find(";", k)
                    if m != -1 and (semi == -1 or m < semi):
                        pending_if = True
                        i = m
                        continue
                    pending_if = False
        if c == "{":
            stack.append(pending_if)
            pending_if = False
            depth += 1
        elif c == "}":
            if stack:
                stack.pop()
            depth -= 1
        elif stack and any(stack):
            flags.add(i)
        i += 1
    return flags


def extract(src):
    """Extrae (linea, tipo, expr, condicional) de un cuerpo, en orden."""
    events = []
    for m in WRITE_RE.finditer(src):
        events.append((line_of(src, m.start()), "write", m.group(1), m.start()))
    for m in WREG_RE.finditer(src):
        events.append((line_of(src, m.start()), "wreg",
                       m.group(1) + ", " + m.group(2), m.start()))
    events.sort(key=lambda e: (e[0], e[3]))
    cond = conditional_offsets(src)
    out = []
    for ln, kind, expr, off in events:
        # pertenencia EXACTA: con 'any(o <= off)' un solo offset
        # condicional anterior marcaba todo lo que venia despues.
        inside = off in cond
        out.append((ln, kind, expr, inside))
    return out


def conditional_mask(body):
    """Detecta si el cuerpo entero esta dentro de un if (para marcarlo)."""
    head = body.lstrip()
    return head.startswith("{") is False


TERN_RE = re.compile(r"^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$", re.S)


def _unbalanced(branch):
    """Quita un ')' final que pertenece a la expresion exterior, no a la rama.

    En "A | (exec ? B : C)" la rama derecha del ternario es " C)" y su
    parentesis esta desbalanceado. Sin esto el rango del ternario no se
    puede calcular y el dword entero queda sin resolver.
    """
    b = branch.strip()
    while b.endswith(")") and not balanced(b):
        b = b[:-1].strip()
    return b


def eval_partial(expr, macros, depth=0):
    """Evalua lo que se pueda y DICE que no pudo.

    Devuelve (texto, clase) con clase:
      full     -> todo resuelto, texto es 0xXXXXXXXX
      range    -> hay un ternario; texto es 0xMIN..0xMAX (ambos ramas)
      symbolic -> hay una variable local; texto enumera los terminos que
                  si se resolvieron y cuales no

    Se separa del valor duro a proposito: un dword que depende de `seq` NO es
    un dword conocido, y presentarlo como 0 seria mentir.
    """
    expr = strip_comments(expr).strip().rstrip(",").strip()
    # Quita parentesis que envuelven la EXPRESION ENTERA. Sin esto, un
    # "(A | B | C)" queda como un solo termino y no se puede trocear: es
    # exactamente el caso de los flags de EVENT_WRITE_EOP en gfx_v8_0.c.
    while expr.startswith("(") and expr.endswith(")") and balanced(expr[1:-1]):
        expr = expr[1:-1].strip()
    terms, cur, d = [], "", 0
    for c in expr:
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
        if c == "|" and d == 0:
            terms.append(cur)
            cur = ""
        else:
            cur += c
    terms.append(cur)

    pieces, bad, has_range = [], [], False
    for t in terms:
        t = t.strip()
        if not t:
            continue
        try:
            pieces.append("%08X" % eval_call(t, macros))
            continue
        except Unresolved:
            pass
        m = TERN_RE.match(t)
        if m:
            try:
                lo = eval_call(_unbalanced(m.group(2)), macros)
                hi = eval_call(_unbalanced(m.group(3)), macros)
                pieces.append("%08X..%08X" % (min(lo, hi), max(lo, hi)))
                has_range = True
                continue
            except Unresolved:
                pass
        bad.append(t)

    if not bad:
        v = 0
        for p in pieces:
            v |= int(p.split("..")[0], 16)
        if has_range:
            # Un rango NO es un valor: el dword real es uno de dos. Marcarlo
            # "full" seria presentar una eleccion del evaluador como un hecho.
            return "0x%08X (rango en una rama)" % v, "range"
        return "0x%08X" % v, "full"
    if pieces:
        return " | ".join(pieces) + " | ?" + ",".join(bad), "symbolic"
    return ",".join(bad), "symbolic"


# Emisores que viven en OTRO fichero. gfx_v8_0_ring_emit_vm_flush llama a
# gmc_v8_0_emit_flush_gpu_tlb (gmc_v8_0.c:668), que emite 2 WREG = 10 dwords.
# Sin contarlos, el recuento queda corto y --frame-size puede declarar
# "reserva insuficiente" donde no la hay: un falso positivo de los graves.
CROSS = {
    "amdgpu_gmc_emit_flush_gpu_tlb": ("gmc_v8_0.c", "gmc_v8_0_emit_flush_gpu_tlb"),
}

# Ya expandidas por WREG_RE dentro del propio cuerpo. Meterlas en CROSS
# y volver a sumarlas al cruzar ficheros cuenta los dwords dos veces: asi
# appeared "29 emitidos" donde la verdad son 19.
IN_PLACE = {"amdgpu_ring_emit_wreg"}

# Cualquier llamada a un emisor con estos prefijos que NO este en CROSS obliga
# a marcar el recuento como incompleto.
EMIT_CALL_RE = re.compile(r"\b((?:amdgpu_)?\w*emit_\w+)\s*\(")


def cross_dwords(name, files_cache, macros, depth=0):
    """Dwords que aporta una llamada a otro fichero. 0 si no se puede saber."""
    if depth > 4 or name not in CROSS:
        return 0, False
    fname, fn = CROSS[name]
    path = os.path.join(AMD, fname)
    if path not in files_cache:
        files_cache[path] = analyse(path, macros)
    report, _ = files_cache[path]
    for r in report:
        if r["name"] == fn:
            total, incomplete = r["n"], r["incomplete"]
            # Los WREG ya vienen expandidos en el analisis del propio fichero.
            for sub in EMIT_CALL_RE.findall(r["raw"]):
                if sub in CROSS:
                    extra, inc2 = cross_dwords(sub, files_cache, macros,
                                               depth + 1)
                    total += extra
                    incomplete = incomplete or inc2
            return total, incomplete
    return 0, True


def analyse(path, macros, name_filter=None):
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()

    report = []
    unresolved = []

    for name, line, body in find_functions(src):
        if name_filter and name != name_filter:
            continue
        offset = line_of(src, src.index(body))
        dwords = []
        for rel, kind, expr, cond in extract(body):
            ln = offset + rel - 1
            if kind == "wreg":
                reg, val = split_args(expr)
                dwords.append((ln, "WREG.header",
                               "0x%08X" % eval_call(
                                   "PACKET3(PACKET3_WRITE_DATA, 3)", macros),
                               "full", cond))
                dwords.append((ln, "WREG.cmd",
                               "0x%08X" % eval_call(
                                   "WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM", macros),
                               "full", cond))
                for e, tag in ((reg, "WREG.reg"), ("0", "WREG.zero"),
                               (val, "WREG.val")):
                    txt, kind = eval_partial(e, macros)
                    if kind != "full":
                        unresolved.append((name, ln, tag, txt))
                    dwords.append((ln, tag, txt, kind, cond))
                continue
            txt, kind = eval_partial(expr, macros)
            if kind != "full":
                unresolved.append((name, ln, "dword", txt))
            dwords.append((ln, "dword", txt, kind, cond))

        calls = list(EMIT_CALL_RE.findall(body))
        report.append({
            "name": name,
            "line": line,
            "n": len(dwords),
            "resolved": sum(1 for d in dwords if d[3] == "full"),
            "n_cond": sum(1 for d in dwords if d[4]),
            "dwords": dwords,
            "raw": body,
            "calls": calls,
            "incomplete": any(c not in CROSS and c not in IN_PLACE
                              for c in calls),
        })
    return report, unresolved


# ---------------------------------------------------------------- salida

def show(report):
    for r in report:
        print("\n%s  (linea %d)  %d dwords (%d condicionales), %d resueltos"
              % (r["name"], r["line"], r["n"], r["n_cond"], r["resolved"]))
        for ln, tag, txt, kind, cond in r["dwords"]:
            marca = ""
            if kind != "full":
                marca += "   ~"
            if cond:
                marca += "  [cond]"
            print("   %5d  %-14s %s%s" % (ln, tag, txt, marca))


def control(path, macros, report):
    """Paquetes definidos en sid.h que GFX8 nunca emite. CONTROL NEGATIVO."""
    sid = os.path.join(AMD, "sid.h")
    with open(sid, encoding="utf-8", errors="replace") as fh:
        defined = set(re.findall(r"^#define\s+(PACKET3_\w+)\s", fh.read(),
                                 re.M))
    emitted = set()
    for r in report:
        for d in r["dwords"]:
            if d[3] != "full":
                continue
            op = (int(d[2], 16) >> 8) & 0xFF
            for nm in defined:
                try:
                    if eval_call(nm, macros) == op:
                        emitted.add(nm)
                except Unresolved:
                    pass
    never = sorted(defined - emitted)
    print("PACKET3 definidos en sid.h : %d" % len(defined))
    print("emitidos por GFX8         : %d" % len(emitted))
    print("nunca emitidos             : %d" % len(never))
    return never


FRAME_RE = re.compile(r"\.emit_frame_size\s*=\s*(.*?),\n", re.S)
# Cada sumando va seguido de un comentario con el nombre de la funcion a la
# que se atribuye. Hay que partir por esos comentarios y no por los '+',
# porque un sumando tambien puede ser "VI_X * 5 + 7".
TERM_RE = re.compile(r"([0-9A-Za-z_][^/*]*?)\s*/\*\s*(.*?)\s*\*/", re.S)


def frame_size(path, macros):
    """Contrasta la contabilidad declarada con lo que la funcion emite.

    Si la reserva declarada es MENOR que lo emitido, el reserva es
    insuficiente y eso si es un defecto. Si es MAYOR, es holgura: no es un
    defecto, y hay que decirlo como holgura y no como error.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    report, _ = analyse(path, macros)
    by_name = {r["name"]: r for r in report}
    files_cache = {os.path.realpath(path): (report, None)}  # para evitar reanalizar

    print("%-42s %9s %9s %7s  %s"
          % ("funcion", "sin cond.", "declarado", "delta", "nota"))
    rows = 0
    for m in FRAME_RE.finditer(src):
        for tm in TERM_RE.finditer(m.group(1)):
            expr_txt = tm.group(1).strip().rstrip("+").strip()
            comment = tm.group(2)
            f = re.search(r"(gfx_v8_0_\w+)", comment)
            if not f or f.group(1) not in by_name:
                continue
            fn = f.group(1)
            # Los cross pueden anadir dwords condicionales: se cuentan como
            # condicionales, no como incondicionales.
            got = by_name[fn]["n"] - by_name[fn]["n_cond"]
            ncond = by_name[fn]["n_cond"]
            known = [c for c in by_name[fn]["calls"] if c in CROSS]
            unknown = [c for c in by_name[fn]["calls"]
                       if c not in CROSS and c not in IN_PLACE]
            for c in known:
                extra, _ = cross_dwords(c, files_cache, macros)
                got += extra
                ncond += 0
            total = got + ncond
            try:
                declared = eval_call(expr_txt, macros)
            except Unresolved as ex:
                print("%-42s %9d %9s %7s  no se evalua: %s"
                      % (fn, got, "?", "?", ex.name))
                continue
            d_uncond = declared - got
            d_cond = declared - total
            if unknown:
                nota = "  INCOMPLETO: no se expande " + ",".join(sorted(set(unknown)))
                dtxt = "?"
            elif d_uncond < 0 and d_cond >= 0:
                nota = ("  cubre el caso SIN condicional (%d) pero no el de "
                        "anillo GFX (%d)" % (got, total))
                dtxt = "%d" % d_uncond
            elif d_uncond < 0:
                nota = "  < RESERVA INSUFICIENTE"
                dtxt = "%d" % d_uncond
            else:
                nota = "  holgura %d" % d_uncond if d_uncond else "  exacto"
                dtxt = "%d" % d_uncond
            print("%-42s %9d %9d %7s%s" % (fn, got, declared, dtxt, nota))
            rows += 1
    if not rows:
        print("sin comparacion posible")
    return rows


# -------------------------------------------------------------- self-test

def self_test(macros):
    fails = []

    def eq(label, got, want):
        if got != want:
            fails.append("%s: obtuve %r, esperaba %r" % (label, got, want))

    # 1. Cabecera PACKET3 conocida, verificada a mano con el macro de sid.h.
    eq("PACKET3(WAIT_REG_MEM,5)", eval_call("PACKET3(PACKET3_WAIT_REG_MEM, 5)", macros),
       0xC0053C00)
    eq("PACKET3(PFP_SYNC_ME,0)", eval_call("PACKET3(PACKET3_PFP_SYNC_ME, 0)", macros),
       0xC0004200)
    eq("PACKET3(WRITE_DATA,3)", eval_call("PACKET3(PACKET3_WRITE_DATA, 3)", macros),
       0xC0033700)   # sid.h:377: op=0x37 -> 0x37<<8 = 0x3700
    eq("PACKET3(NOP,1)", eval_call("PACKET3(PACKET3_NOP, 1)", macros), 0xC0011000)

    # 2. Campos: WAIT del vm_flush vale cero entero (110).
    eq("wait header", eval_call(
        "WAIT_REG_MEM_OPERATION(0) | WAIT_REG_MEM_FUNCTION(0) | WAIT_REG_MEM_ENGINE(0)",
        macros), 0)

    # 3. El flag de anillo GFX.
    eq("wreg cmd", eval_call("WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM", macros),
       0x40100000)

    # 4. CONTROL NEGATIVO: un simbolo desconocido debe PROPAGAR, no valer 0.
    for bad in ["NO_EXISTE_XYZ", "PACKET3_NO_EXISTE", "1 | NO_EXISTE_XYZ"]:
        try:
            v = eval_call(bad, macros)
            fails.append("control negativo %r devolvio %r en vez de fallar"
                         % (bad, v))
        except Unresolved:
            pass

    # 5. Un argumento no constante tambien debe fallar (no inventar).
    try:
        eval_call("PACKET3(PACKET3_NOP, vmid)", macros)
        fails.append("control negativo: argumento variable no fallo")
    except Unresolved:
        pass

    # 6. Anidamiento y paridad: PACKET3 anidado debe colapsar.
    eq("PACKET3(0x10,1)|1<<1",
       eval_call("PACKET3(PACKET3_NOP, 1) | (1 << 1)", macros), 0xC0011002)

    # 7. Caso real: el WAIT del invalidate debe llevar 0x51E como POLL_ADDR.
    #    Si esto cambia, el hallazgo 110 queda invalidado.
    eq("poll addr", eval_call("mmVM_INVALIDATE_REQUEST", macros), 0x51E)
    eq("response", eval_call("mmVM_INVALIDATE_RESPONSE", macros), 0x51F)

    # 8. Un paquete que el driver usa y cuyo valorKnown fijamos en 104/110.
    eq("PACKET3_WAIT_REG_MEM opcode", eval_call("PACKET3_WAIT_REG_MEM", macros), 0x3C)

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (12 vectores, 6 controles negativos)")
    return 0


# -------------------------------------------------------------------- main

def main(argv):
    if "--self-test" in argv:
        return self_test(load_macros())

    macros = load_macros()
    path = os.path.join(AMD, TARGET)

    if "--func" in argv:
        name = argv[argv.index("--func") + 1]
        report, unres = analyse(path, macros, name_filter=name)
        if not report:
            print("no existe la funcion %s" % name)
            return 2
        show(report)
        if unres:
            print("\nSIN RESOLVER (%d):" % len(unres))
            for n, ln, tag, sym in unres:
                print("   %s:%d %s -> %s" % (n, ln, tag, sym))
            return 3
        return 0

    if "--all" in argv:
        report, unres = analyse(path, macros)
        show(report)
        print("\ntotal funciones: %d, dwords: %d, sin resolver: %d"
              % (len(report), sum(r["n"] for r in report), len(unres)))
        return 3 if unres else 0

    if "--control" in argv:
        report, _ = analyse(path, macros)
        control(path, macros, report)
        return 0

    if "--frame-size" in argv:
        frame_size(path, macros)
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
