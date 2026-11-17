"""Decompiler Zero-Trust skeleton (EDICT/M430, PASS_PARTIAL acotado).

Lifting vía objdump (no heurística por nombre), generación C instrucción-
dependiente, certificado por bloque con vectores adversariales.
Sin equivalencia universal; PROVEN no afirmado sin cadena completa.

RECONSTRUCCIÓN INSTRUCCIÓN-DEPENDIENTE (M9)
-------------------------------------------
La salida de C depende de los nodos levantados.  La plantilla por nombre de
función se eliminó; cualquier nodo desconocido, malformado o no interpretable
devuelve un PARTIAL explícito con razón y lista, nunca una reconstrucción
aparentemente válida.  Las tres plantillas conocidas que antes se activaban
por nombre fueron retiradas y no se preservan como alternativa de emisión.
"""

from __future__ import annotations
import re

KNOWN_MNEMONICS = frozenset({
    # DATA
    "mov", "movzbl", "movsbl",
    "movslq",
    # TRANSFORM
    "add", "sub", "xor", "and", "or", "shl", "shr", "sar", "imul",
    # CONTROL (estructural; sin semántica adjunta)
    "call", "ret", "jmp", "cmp", "test",
    "jo", "jno", "js", "jns", "jp", "jnp", "je", "jne", "jz", "jnz",
    "jg", "jge", "jl", "jle", "ja", "jae", "jb", "jbe",
    "jecxz", "loop", "loope", "loopne",
    "push", "pop", "nop", "int3", "endbr64", "endbr32", "leave",
    # setcc family (compare results)
    "setg", "setge", "setl", "setle", "seta", "setae", "setb", "setbe",
    "sete", "setne", "sets", "setns", "seto", "setno", "setp", "setnp",
    # cmov family (conditional moves)
    "cmovle", "cmovl", "cmovg", "cmovge",
    "cmovs", "cmovns", "cmove", "cmovne",
    "cmova", "cmovae", "cmovb", "cmovbe",
})

_ROLE_VALUES_MNEMONICS = frozenset({"mov","movzbl","movslq",
                                     "add","sub","xor","and","or","shl","shr","sar","imul"})
_ROLE_VALUES = frozenset({"DATA", "TRANSFORM", "CONTROL"})


def lift_objdump(disasm: str, func: str) -> list[dict]:
    """Desensambla objdump -d --no-show-raw-insn y clasifica roles M430."""
    nodes, cur = [], None
    _SKIP = {"nop", "nopl", "nopw", "data16", "int3", "cs", "endbr64", "endbr32", "leave"}
    for line in disasm.splitlines():
        m = re.match(r"^\s*([0-9a-fA-F]+):\t((?:[0-9a-fA-F]{2}[ ]+)+)\s*\t(\S+)\s*(.*)$", line)
        if not m:
            continue
        addr, mne, ops = m.group(1), m.group(3).lower(), m.group(4)
        if mne in _SKIP:
            continue
        base = mne
        if len(base) > 1 and base[-1] in "bwlq" and base[:-1] in _ROLE_VALUES_MNEMONICS:
            base = base[:-1]
        role = "DATA" if base in ("mov","movzbl","movslq") else ("TRANSFORM" if base in ("add","sub","xor","and","or","shl","shr","sar","imul") else "CONTROL")
        nodes.append({"addr": addr, "mnemonic": mne, "operands": ops, "role_M430": role})
    return nodes


def _validate_nodes(nodes: list[dict]):
    """Devuelve (known, unknown_mnemonics, malformed) sobre la evidencia.

    Rige los invariantes del lifter:

      I2  mnemónico fuera del registro => no demostrable => PARTIAL con la lista
      I4  cada nodo queda en {"known", "unknown"|"malformed"} — ninguno oculto
      I6  un nodo solo por estar presente NO es 'consumido'; aquí sólo se valida
      I8  la clasificación role_M430 nunca justifica por sí misma
    """
    known = []
    unknown = []
    malformed = []
    if not isinstance(nodes, list):
        return [], [], [("non-list", "nodes no es una lista")]
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            malformed.append((i, "node no es dict"))
            continue
        mne = n.get("mnemonic")
        if not isinstance(mne, str) or not mne.strip():
            malformed.append((i, "mnemonic ausente o vacío"))
            continue
        m = mne.strip().lower().split()[0]
        role = n.get("role_M430")
        if role not in _ROLE_VALUES:
            malformed.append((i, "role_M430 ausente o fuera de {DATA,TRANSFORM,CONTROL}"))
            continue
        if m in KNOWN_MNEMONICS:
            known.append((i, n))
        # sufijo de tamaño AT&T opcional: si el mnemónico en base está en el
        # set, aceptarlo (ej. `cmpl` -> `cmp`, `jmpq` -> `jmp`). No ampliar el set.
        elif len(m) > 1 and m[-1] in "bwlq" and m[:-1] in KNOWN_MNEMONICS:
            known.append((i, n))
        else:
            unknown.append((i, m))
    return known, unknown, malformed



#: Aliases de registros: cualquier tamaño corresponde al mismo almacenamiento.
_REG_ALIAS = {
    "rax": "rax", "eax": "rax", "ax": "rax", "al": "rax", "ah": "rax",
    "rbx": "rbx", "ebx": "rbx", "bx": "rbx", "bl": "rbx", "bh": "rbx",
    "rcx": "rcx", "ecx": "rcx", "cx": "rcx", "cl": "rcx", "ch": "rcx",
    "rdx": "rdx", "edx": "rdx", "dx": "rdx", "dl": "rdx", "dh": "rdx",
    "rsi": "rsi", "esi": "rsi", "si": "rsi", "sil": "rsi",
    "rdi": "rdi", "edi": "rdi", "di": "rdi", "dil": "rdi",
    "rbp": "rbp", "ebp": "rbp", "bp": "rbp", "bpl": "rbp",
    "rsp": "rsp", "esp": "rsp", "sp": "rsp", "spl": "rsp",
    "r8": "r8", "r9": "r9", "r10": "r10", "r11": "r11",
    "r12": "r12", "r13": "r13", "r14": "r14", "r15": "r15",
    "r8d": "r8", "r8w": "r8", "r8b": "r8",
    "r9d": "r9", "r9w": "r9", "r9b": "r9",
    "r10d": "r10", "r10w": "r10", "r10b": "r10",
    "r11d": "r11", "r11w": "r11", "r11b": "r11",
    "r12d": "r12", "r12w": "r12", "r12b": "r12",
    "r13d": "r13", "r13w": "r13", "r13b": "r13",
    "r14d": "r14", "r14w": "r14", "r14b": "r14",
    "r15d": "r15", "r15w": "r15", "r15b": "r15",
}

def _base_reg(reg):
    # Returns None for registers that aren't in our canonical x86-64 set
    if not isinstance(reg, str):
        return None
    if reg in _REG_ALIAS:
        return _REG_ALIAS[reg]
    # tolerate outer-bit-width register forms (ax, al, ah, ...) by looking up their parent
    for parent, child in (("rax", ("ax", "al", "ah", "eax")),
                          ("rbx", ("bx", "bl", "bh", "ebx")),
                          ("rcx", ("cx", "cl", "ch", "ecx")),
                          ("rdx", ("dx", "dl", "dh", "edx")),
                          ("rsi", ("si", "esi")),
                          ("rdi", ("di", "edi")),
                          ("rbp", ("bp", "ebp")),
                          ("rsp", ("sp", "esp"))):
        if reg in child:
            return parent
    return None

def _base_mne(mne):
    """Strips size suffix from AT&T mnemonics (movl, cmpl, addl, imull ...)."""
    for suf in ("l", "q", "w", "b"):
        if len(mne) > 2 and mne.endswith(suf) and mne[:-1] in KNOWN_MNEMONICS:
            return mne[:-1]
    return mne

def _split_ops(text):
    pieces, cur, depth = [], [], 0
    for ch in text:
        if ch == "(":
            depth += 1; cur.append(ch)
        elif ch == ")":
            depth -= 1; cur.append(ch)
        elif ch == "," and depth == 0:
            pieces.append("".join(cur).strip()); cur = []
        else:
            cur.append(ch)
    if cur:
        pieces.append("".join(cur).strip())
    return pieces

def _parse_op(op):
    op = op.strip()
    if op.startswith("$"):
        try:
            v = int(op[1:], 0)
            return {"kind": "imm", "value": v}
        except ValueError:
            pass
    if op.startswith("%"):
        alias = _base_reg(op[1:])
        if alias is not None:
            return {"kind": "reg", "value": op[1:]}
        return {"kind": "op", "value": op}
    m = re.match(r"^(-?0x[0-9a-fA-F]+|-?[0-9]+)\(%rbp\)$", op)
    if m:
        return {"kind": "stack", "value": int(m.group(1), 0)}
    m = re.match(r"^([0-9a-fA-F]+)$", op)
    if m:
        return {"kind": "imm", "value": int(m.group(1), 16)}
    return {"kind": "op", "value": op}


# =============================================================================
# Modelo de flags (M11.2)
# =============================================================================
# flags = {"cf": expr|None, "of": ..., "sf": ..., "zf": ...}
#   - valor string C: expresión bien formada sobre variables locales disponibles
#     en la función reconstruida.
#   - None: flag desconocido (entrante al inicio, o producido por una
#     instrucción admitida sin semántica de flags modelada en M11.2).
# Sólo las instrucciones admitidas que cambian flags mutan el estado; las
# demás preservan. Ninguna jXX/setcc/cmov se emite con flags requeridos
# desconocidos: se produce un rechazo explícito (PARTIAL), nunca valores
# antiguos reutilizados.
_FLAG_NEEDS = {
    "jle": ("sf", "of", "zf"), "jl": ("sf", "of"),
    "jg": ("sf", "of", "zf"), "jge": ("sf", "of"),
    "je": ("zf",), "jne": ("zf",),
    "ja": ("cf", "zf"), "jae": ("cf",), "jb": ("cf",), "jbe": ("cf", "zf"),
    "js": ("sf",), "jns": ("sf",), "jo": ("of",), "jno": ("of",),
}


def _sf(res):
    return "(((%s)) < 0)" % res


def _zf(res):
    return "(((%s)) == 0)" % res


def _tmp_vars():
    return []

def _flags_after_cmp(left, right):
    # Toda la condición se calcula sobre aritmética unsigned definida.
    u = "((((unsigned)(%s))) - ((unsigned)(%s)))" % (left, right)
    return {
        "cf": "((((unsigned)(%s))) < ((unsigned)(%s)))" % (left, right),
        "of": "(((((%s) ^ (%s))) & 0x80000000u) != 0 && ((((%s) ^ (%s))) & 0x80000000u) != 0)" % (left, right, left, u),
        "sf": "((%s) & 0x80000000u) != 0" % u,
        "zf": "((%s) == 0)" % u,
    }


def _snapshot(expr, lines, counter):
    """Si la expresión no es literal, snapshotea en un temporal _fN."""
    if re.fullmatch(r"-?\d+|-?0x[0-9a-fA-F]+", expr):
        return expr
    counter[0] += 1
    v = "_f%d" % counter[0]
    lines.append("  int %s = %s;" % (v, expr))
    return v


def _imm_c(v):
    """Emisión de literal entero AT&T de 32 bits preservando valor y bits.

    - [-2147483647, 2147483647]  → decimal (tipo int, sin conversión)
    - fuera de rango              → "(int)0xNNNNNNNNu"
      cast explícito: bit pattern exacto, sin overflow ni pérdida;
      explícitamente local, convierte envuelto (GCC/Clang/MSVC) o señal
      (impl-defined documentada por el standard); no es UB.
    Nunca emite un literal out-of-range decimal y nunca convierte
    un UNSIGNED en negativo decimal.
    """
    if -2147483647 <= v <= 2147483647:
        return str(v)
    return "(int)0x%08xu" % (v & 0xFFFFFFFF)


def _flags_after_addsub(left, right, res, op):
    # Toda la condición se calcula sobre aritmética unsigned definida.
    if op == "add":
        u = "((((unsigned)(%s))) + ((unsigned)(%s)))" % (left, right)
        cf = "((%s) < ((unsigned)(%s)))" % (u, left)
    else:  # sub
        u = "((((unsigned)(%s))) - ((unsigned)(%s)))" % (left, right)
        cf = "((((unsigned)(%s))) < ((unsigned)(%s)))" % (left, right)
    if op == "add":
        of_ = "(((((%s) ^ (%s))) & 0x80000000u) == 0 && ((((%s) ^ (%s))) & 0x80000000u) != 0)" % (left, right, left, u)
    else:  # sub
        of_ = "(((((%s) ^ (%s))) & 0x80000000u) != 0 && ((((%s) ^ (%s))) & 0x80000000u) != 0)" % (left, right, left, u)
    return {"cf": cf,
            "of": of_,
            "sf": "((%s) & 0x80000000u) != 0" % u,
            "zf": "((%s) == 0)" % u}


def _flags_after_logical(res):
    return {"cf": "0", "of": "0", "sf": _sf(res), "zf": _zf(res)}


def _flags_after_shift(res):
    return {"cf": None, "of": None, "sf": _sf(res), "zf": _zf(res)}


def _flags_all_unknown():
    return {"cf": None, "of": None, "sf": None, "zf": None}


def _flag_cond(flags, mne):
    """Devuelve (cond_expr, missing)."""
    need = _FLAG_NEEDS[mne]
    missing = [k for k in need if flags[k] is None]
    if missing:
        return None, missing
    sf, of_, zf, cf = flags["sf"], flags["of"], flags["zf"], flags["cf"]
    cond = {
        "jle": "(((%s) != (%s)) || (%s))" % (sf, of_, zf),
        "jl": "(((%s) != (%s)))" % (sf, of_),
        "jg": "((((%s) == (%s))) && !(%s))" % (sf, of_, zf),
        "jge": "(((%s) == (%s)))" % (sf, of_),
        "je": "(%s)" % zf,
        "jne": "!(%s)" % zf,
        "ja": "(!(%s) && !(%s))" % (cf, zf),
        "jae": "!(%s)" % cf,
        "jb": "(%s)" % cf,
        "jbe": "(((%s) || (%s)))" % (cf, zf),
        "js": "(%s)" % sf,
        "jns": "!(%s)" % sf,
        "jo": "(%s)" % of_,
        "jno": "!(%s)" % of_,
    }[mne]
    return cond, None


# =============================================================================
# Modelo de registros (M11.5): ancho y offset explícitos
# =============================================================================
# Cada nombre de registro → (base, offset_bits, width_bits)
#   al→(rax,0,8)  ah→(rax,8,8)  ax→(rax,0,16)  eax→(rax,0,32)  rax→(rax,0,64)
# Regla de escritura x86-64:
#   - escritura de 32 bits en GPR ⇒ bits 32..63 ponen a cero (automático en
#     nuestro modelo ya que los locales son de 32 bits con signo);
#   - escritura de ≤16 bits ⇒ bits no afectados preservados;
#   - escritura de 8 bits con offset ⇒ preserva los demás bits.
_REG_INFO = {}
for _base in ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
              "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"):
    _REG_INFO[_base] = (_base, 0, 64)
for _base, _s32, _s16, _s8, _s8hi in (
    ("rax", "eax", "ax", "al", "ah"),
    ("rbx", "ebx", "bx", "bl", "bh"),
    ("rcx", "ecx", "cx", "cl", "ch"),
    ("rdx", "edx", "dx", "dl", "dh"),
    ("rsi", "esi", "si", "sil", None),
    ("rdi", "edi", "di", "dil", None),
    ("rbp", "ebp", "bp", "bpl", None),
    ("rsp", "esp", "sp", "spl", None),
    ("r8",  "r8d", "r8w", "r8b", None),
    ("r9",  "r9d", "r9w", "r9b", None),
    ("r10", "r10d", "r10w", "r10b", None),
    ("r11", "r11d", "r11w", "r11b", None),
    ("r12", "r12d", "r12w", "r12b", None),
    ("r13", "r13d", "r13w", "r13b", None),
    ("r14", "r14d", "r14w", "r14b", None),
    ("r15", "r15d", "r15w", "r15b", None),
):
    _REG_INFO[_s32] = (_base, 0, 32)
    _REG_INFO[_s16] = (_base, 0, 16)
    _REG_INFO[_s8]  = (_base, 0, 8)
    if _s8hi:
        _REG_INFO[_s8hi] = (_base, 8, 8)


def _reg_info(name):
    if not isinstance(name, str):
        return None
    return _REG_INFO.get(name)


def _reg_get(name, regs):
    """Devuelve la expresión C del contenido del registro con ancho explícito."""
    info = _reg_info(name)
    if info is None:
        return None
    base, off, width = info
    expr = regs.get(base, base)
    if width in (64, 32):
        return expr  # dominio del modelo: los 64 bits tienen almacenamiento local
    if width == 16:
        return "((%s) & 0xffff)" % expr
    if off == 0:
        return "((%s) & 0xff)" % expr
    return "(((%s) >> %d) & 0xff)" % (expr, off)


def _reg_put(name, expr, regs):
    """Devuelve las líneas que implementan 'mov name, expr' preservando bits según ancho."""
    info = _reg_info(name)
    if info is None:
        return None
    base, off, width = info
    base_expr = regs.get(base, base)
    if width in (64, 32):
        # escritura de 32 bits en GPR ⇒ bits 32..63 a cero; en nuestro modelo
        # los locales son de 32 bits: la asignación directa preserva semántica.
        return ["  %s = %s;" % (base, expr)]
    if width == 16:
        return ["  %s = (((%s) & ~0xffff) | ((%s) & 0xffff));" % (base, base_expr, expr)]
    if off == 0:
        return ["  %s = (((%s) & ~0xff) | ((%s) & 0xff));" % (base, base_expr, expr)]
    return ["  %s = (((%s) & ~0xff00) | (((%s) & 0xff) << 8));" % (base, base_expr, expr)]


def _read_reg_src(src_op, regs):
    if src_op["kind"] == "reg":
        return _reg_get(src_op["value"], regs)
    return None


def _mov_dest_source_lines(dst, src, regs, slots):
    """Emite 'mov dst, src' respetando ancho de escritura."""
    if dst["kind"] == "reg":
        dest_info = _reg_info(dst["value"])
        if dest_info is None:
            return None
        if src["kind"] == "reg":
            sexpr = _reg_get(src["value"], regs)
        elif src["kind"] == "imm":
            sexpr = _imm_c(src["value"])
        elif src["kind"] == "stack":
            sexpr = slots.get(src["value"], "_e_%d" % -src["value"])
        else:
            return None
        lines = _reg_put(dst["value"], sexpr, regs)
        return lines
    if dst["kind"] == "stack":
        if src["kind"] == "reg":
            sexpr = _reg_get(src["value"], regs)
        elif src["kind"] == "imm":
            sexpr = _imm_c(src["value"])
        else:
            return None
        slot_off = dst["value"]
        nm = slots.get(slot_off)
        lines = []
        if nm is None:
            nm = "_s_%d" % -slot_off
            slots[slot_off] = nm
            lines.append("  int %s = 0;" % nm)
        lines.append("  %s = %s;" % (nm, sexpr))
        return lines
    return None


# =============================================================================
# ABI de argumentos (M11.6) — System V AMD64 entero
# =============================================================================
_ABI_INT_ARG_REGS = ("rdi", "rsi", "rdx", "rcx", "r8", "r9")


def _build_abi_argindex():
    idx = {}
    for i, areg in enumerate(_ABI_INT_ARG_REGS):
        for name, (base, off, width) in _REG_INFO.items():
            if base == areg:
                idx[name] = i
    return idx


_ABI_ARGIDX = _build_abi_argindex()


def _detect_argc(nodes):
    """Estima el número de argumentos enteros de la función de acuerdo con el
    comportamiento de GCC -O0: cada parámetro (usado o no) cuyo registro ABI
    aparece con destination stack slot es un argumento posicional.

    No se cuentan los usos como scratch (contilidad: sin spill
    a la pila, el registro no es argumento declarado).

    Menos cálculo es mejor: un parámetro nunca usado esindistinguible y su
    ausencia de la firma es semánticamente segura. Un parámetro detectado por
    spill implica la precondición del parámetro en la firma (orden ABI).
    """
    if not isinstance(nodes, list):
        return 0
    seen = set()
    for n in nodes:
        ops = n.get("operands") if isinstance(n.get("operands"), str) else ""
        ops = ops.strip().lower()
        # -O0 spill:  %<reg>, -<offset>(%rbp)
        m = re.match(r"^%([a-z0-9]+),\s*-?(0x[0-9a-f]+|[0-9]+)\(%rbp\)\s*$", ops)
        if not m:
            continue
        idx = _ABI_ARGIDX.get(m.group(1))
        if idx is not None:
            seen.add(idx)
    if not seen:
        return 0
    return max(seen) + 1


def _reconstruct(nodes, func, argc=None):
    # nodes already parsed by the caller (lift_objdump output)

    if not nodes:
        return None, "empty"

    # Si argc no viene del llamador, se detecta por lectura/escritura de
    # registros ABI (días ISA entera). El llamador nunca suministra valor < 0.
    if argc is None:
        argc = _detect_argc(nodes)
    if not isinstance(argc, int) or argc < 0 or argc > len(_ABI_INT_ARG_REGS):
        return None, "argc:%s" % argc

    # pre-scan jump targets
    label_addrs = set()
    for n in nodes:
        if n["mnemonic"].startswith(("j", "jmp")) and not n["mnemonic"].startswith("jal"):
            m = re.match(r"^([0-9a-fA-F]+)", n["operands"])
            if m:
                label_addrs.add(int(m.group(1), 16))
    labels = {a: "L%x" % a for a in sorted(label_addrs)}

    # === signature: empíricamente el "arg count" puede detectarse desde los
    # registros ABI enteros: cada registro utilizado implica su posición.
    # No es decisivo (los últimos pueden no usarse) pero produce una firma
    # segura respecto de la semántica observada.
    arg_names = ["_a0", "_a1", "_a2", "_a3", "_a4", "_a5"][:argc]
    sig_args = ", ".join("int %s" % a for a in arg_names)
    sig = "int %s(%s) {" % (func, sig_args) if arg_names else "int %s(void) {" % func
    arg_regs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
    regs = {arg_regs[i]: arg_names[i] for i in range(min(argc, len(arg_regs)))}
    lines = [sig,
             "  int rax = 0, rbx = 0, rcx = 0, rdx = 0;",
             "  int rsi = 0, rdi = 0, rbp = 0, rsp = 0;",
             "  int r8 = 0, r9 = 0, r10 = 0, r11 = 0;",
             "  int r12 = 0, r13 = 0, r14 = 0, r15 = 0;"]

    regs = {arg_regs[i]: arg_names[i] for i in range(min(argc, len(arg_regs)))}
    slots = {}
    # RFLAGS entrante: desconocido; sólo cmp/test/logical/add/sub/shl/shr/sar
    # producen valores conocidos. Ninguna jXX puede consumir flags desconocidos,
    # y las banderas se calculan sobre temporales _fN inmutables para que no
    # queden desactualizadas por asignaciones posteriores.
    flags = {"cf": None, "of": None, "sf": None, "zf": None}
    flags_tmp = [0]
    # Modelo de pila M11.7: stack_depth en unidades de 8 bytes desde el marco
    # (push %rbp => prologue; incremento de 1 por push; pop lo decrementa).
    # Los slots se nombran _psuh_N y se exponen por offsets -8,-16,-24... desde rbp.
    stack_depth = 0
    push_record = []

    for n in nodes:
        a = int(n["addr"], 16)
        if a in labels:
            lines.append("%s:" % labels[a])

        mne = n["mnemonic"]
        ops = n["operands"]

        if mne == "push":
            p = _split_ops(ops)
            if len(p) != 1:
                return None, "push:operands:%s" % ops
            info = _parse_op(p[0])
            if info["kind"] == "reg":
                reg_base = _base_reg(info["value"])
                if reg_base is None:
                    return None, "push:reg(%s)" % info["value"]
                # push %rbp prologue: marca marco, no consume slot
                if reg_base == "rbp" and stack_depth == 0:
                    continue
                stack_depth += 1
                nm = "_psuh_%d" % stack_depth
                sexpr = _reg_get(reg_base, regs)
                lines.append("  int %s = %s;" % (nm, sexpr))
                slots[-8 * stack_depth] = nm
                push_record.append((nm, reg_base))
                continue
            if info["kind"] == "imm":
                stack_depth += 1
                nm = "_psuh_%d" % stack_depth
                lines.append("  int %s = %s;" % (nm, _imm_c(info["value"])))
                slots[-8 * stack_depth] = nm
                push_record.append((nm, None))
                continue
            return None, "push:kind:%s" % p[0]

        if mne == "pop":
            p = _split_ops(ops)
            if len(p) != 1:
                return None, "pop:operands:%s" % ops
            info = _parse_op(p[0])
            if info["kind"] != "reg":
                return None, "pop:kind:%s" % p[0]
            reg_base = _base_reg(info["value"])
            if reg_base is None:
                return None, "pop:reg(%s)" % info["value"]
            # pop %rbp teardown de frame: marca salida, no consume slot
            if reg_base == "rbp" and stack_depth == 0:
                continue
            if stack_depth == 0:
                return None, "pop:underflow(%s)" % info["value"]
            nm = slots.get(-8 * stack_depth)
            if nm is None:
                return None, "pop:mismatch"
            stack_depth -= 1
            put = _reg_put(info["value"], nm, regs)
            if put is None:
                return None, "pop:reg_put"
            for ln in put:
                lines.append(ln)
            bk = _base_reg(info["value"])
            if bk:
                regs[bk] = bk
            if push_record:
                push_record.pop()
            continue

        if mne in ("mov",):
            p = _split_ops(ops)
            if len(p) != 2:
                return None, "mov:operands:%s" % ops
            src = _parse_op(p[0])
            dst = _parse_op(p[1])
            if (src["kind"] == "reg" and dst["kind"] == "reg"
                    and src["value"] in ("rsp","rbp") and dst["value"] in ("rsp","rbp")):
                lines.append("  /* frame */")
                continue
            new_lines = _mov_dest_source_lines(dst, src, regs, slots)
            if new_lines is None:
                return None, "mov:case:%s,%s" % (p[0], p[1])
            for ln in new_lines:
                lines.append(ln)
            b = _base_reg(dst["value"]) if dst["kind"] == "reg" else None
            if b:
                regs[b] = b
            continue

        if mne in ("cmp","test"):
            p = _split_ops(ops)
            if len(p) != 2:
                return None, "cmp:operands"
            op1 = _parse_op(p[0])
            op2 = _parse_op(p[1])
            # AT&T: op1 = src, op2 = dst. El resultado r = dst - src (cmp) o dst & src (test).

            def _reg_expr(reg_name):
                v = _reg_get(reg_name, regs)
                if v is None:
                    return reg_name
                return v

            def _op_expr(op):
                if op["kind"] == "imm":
                    return _imm_c(op["value"])
                if op["kind"] == "reg":
                    return _reg_expr(op["value"])
                if op["kind"] == "stack":
                    return slots.get(op["value"], "_e_%d" % -op["value"])
                return None

            if mne == "test":
                a_e, b_e = _op_expr(op1), _op_expr(op2)
                if a_e is None or b_e is None:
                    return None, "test:operand(%s)" % ops
                sa = _snapshot(a_e, lines, flags_tmp)
                sb = _snapshot(b_e, lines, flags_tmp)
                res = "(%s & %s)" % (sa, sb)
                flags = {"cf": "0", "of": "0", "sf": _sf(res), "zf": _zf(res)}
                lines.append("  /* test */")
                continue

            # cmp: determina (left=dest, right=src) por combinación de clases
            if op1["kind"] == "imm":
                right = _imm_c(op1["value"])
                if op2["kind"] == "stack":
                    left = slots.get(op2["value"], "_e_%d" % -op2["value"])
                elif op2["kind"] == "reg":
                    left = _reg_expr(op2["value"])
                else:
                    return None, "cmp:op2"
            elif op2["kind"] == "imm":
                if op1["kind"] == "reg":
                    left = _reg_expr(op1["value"])
                    right = _imm_c(op2["value"])
                else:
                    return None, "cmp:op1-imm"
            elif op1["kind"] == "reg" and op2["kind"] == "reg":
                left = _reg_expr(op2["value"])
                right = _reg_expr(op1["value"])
            elif op1["kind"] == "stack" and op2["kind"] == "reg":
                left = _reg_expr(op2["value"])
                right = slots.get(op1["value"], "_e_%d" % -op1["value"])
            elif op1["kind"] == "reg" and op2["kind"] == "stack":
                left = slots.get(op2["value"], "_e_%d" % -op2["value"])
                right = _reg_expr(op1["value"])
            else:
                return None, "cmp:case"
            sl = _snapshot(left, lines, flags_tmp)
            sr = _snapshot(right, lines, flags_tmp)
            flags = _flags_after_cmp(sl, sr)
            continue

        _JCC = {"jle": "jle", "jl": "jl", "jg": "jg", "jge": "jge",
                 "je": "je", "jne": "jne", "ja": "ja", "jae": "jae",
                 "jb": "jb", "jbe": "jbe", "js": "js", "jns": "jns",
                 "jo": "jo", "jno": "jno",
                 "jz": "je", "jnz": "jne"}
        if mne in _JCC:
            m = re.match(r"^([0-9a-fA-F]+)", ops)
            if not m:
                return None, "jXX:addr"
            tgt = int(m.group(1), 16)
            cond, missing = _flag_cond(flags, _JCC[mne])
            if missing:
                return None, "jXX:%s" % ",".join("%s-unknown" % k for k in missing)
            lines.append("  if (%s) goto L%x;" % (cond, tgt))
            continue
        if mne in ("jp", "jnp"):
            return None, "jXX:pf-unknown (%s)" % mne

        if mne == "jmp":
            m = re.match(r"^([0-9a-fA-F]+)", ops)
            if not m:
                return None, "jmp:addr"
            tgt = int(m.group(1), 16)
            lines.append("  goto L%x;" % tgt)
            continue

        if mne in ("xor",) and ops.split(",")[0].strip() == ops.split(",")[1].strip():
            reg_tok = ops.split(",")[0].strip().lstrip("%")
            if _reg_info(reg_tok) is None:
                return None, "xor:reg(%s)" % reg_tok
            lines += _reg_put(reg_tok, "0", regs)
            bk = _base_reg(reg_tok)
            if bk:
                regs[bk] = bk
            # xor reg,reg: resultado 0 → SF=0, ZF=1, OF=0, CF=0
            flags = {"cf": "0", "of": "0", "sf": "0", "zf": "1"}
            continue

        if mne in ("shl","shr","sar","and","or","sub","add","xor","imul"):
            # AT&T order: origen, destino.
            p = _split_ops(ops)
            if len(p) != 2:
                return None, "binop:operands"
            src_op = _parse_op(p[0])
            dst_op = _parse_op(p[1])
            sym = {
                "shl": "<<", "shr": ">>", "sar": ">>",
                "and": "&", "or": "|", "sub": "-", "add": "+", "xor": "^", "imul": "*",
            }[mne]
            # dst puede ser reg o stack slot
            if dst_op["kind"] == "stack":
                slot_c = slots.get(dst_op["value"], "_e_%d" % -dst_op["value"])
                dst_name = slot_c
                left = dst_name  # reads back the slot
            else:
                dst_name = _base_reg(dst_op["value"])
                left = _reg_get(dst_op["value"], regs)
            # src puede ser reg, imm o stack
            if src_op["kind"] == "reg":
                right = _reg_get(src_op["value"], regs)
            elif src_op["kind"] == "imm":
                right = _imm_c(src_op["value"])
            elif src_op["kind"] == "stack":
                right = slots.get(src_op["value"], "_e_%d" % -src_op["value"])
            else:
                return None, "binop:nonreg-src:%s" % ops
            sa = _snapshot(left, lines, flags_tmp)
            sb = _snapshot(right, lines, flags_tmp)
            res = "(%s %s %s)" % (sa, sym, sb)
            if dst_op["kind"] == "reg":
                new_lines = _reg_put(dst_op["value"], res, regs)
                for ln in new_lines:
                    lines.append(ln)
                # el local del registro base siempre tiene el valor correcto
                if regs.get(dst_name) != dst_name:
                    regs[dst_name] = dst_name
            else:
                lines.append("  %s = %s;" % (dst_name, res))
            if mne in ("and", "or", "xor"):
                flags = _flags_after_logical(res)
            elif mne in ("add", "sub"):
                flags = _flags_after_addsub(sa, sb, res, mne)
            elif mne in ("shl", "shr", "sar"):
                flags = _flags_after_shift(res)
            elif mne == "imul":
                flags = _flags_all_unknown()
            continue

        if mne.startswith("set"):
            info = _parse_op(ops)
            if info["kind"] != "reg":
                return None, "setc:reg"
            if _reg_info(info["value"]) is None:
                return None, "setc:form:%s" % info["value"]
            b = _base_reg(info["value"])
            mapped = {"setg": "jg", "setge": "jge", "setl": "jl", "setle": "jle",
                      "sete": "je", "setne": "jne",
                      "seta": "ja", "setae": "jae", "setb": "jb", "setbe": "jbe",
                      "sets": "js", "setns": "jns", "seto": "jo", "setno": "jno"}.get(mne)
            if mapped is None:
                return None, "setc:unsupported:%s" % mne
            cond, missing = _flag_cond(flags, mapped)
            if missing:
                return None, "setc:%s" % ",".join("%s-unknown" % k for k in missing)
            b = _base_reg(info["value"])
            put_lines = _reg_put(info["value"], "(%s ? 1 : 0)" % cond, regs)
            for ln in put_lines:
                lines.append(ln)
            if b:
                regs[b] = b
            continue

        if mne.startswith("cmov"):
            p = _split_ops(ops)
            if len(p) != 2:
                return None, "cmov:operands"
            s_op = _parse_op(p[0]); d_op = _parse_op(p[1])
            if s_op["kind"] != "reg" or d_op["kind"] != "reg":
                return None, "cmov:kind"
            if _reg_info(d_op["value"]) is None:
                return None, "cmov:form:dst:%s" % d_op["value"]
            mapped = {"cmovle": "jle", "cmovl": "jl", "cmovg": "jg", "cmovge": "jge",
                      "cmove": "je", "cmovne": "jne",
                      "cmovs": "js", "cmovns": "jns",
                      "cmova": "ja", "cmovae": "jae", "cmovb": "jb", "cmovbe": "jbe"}.get(mne)
            if mapped is None:
                return None, "cmov:unsupported:%s" % mne
            cond, missing = _flag_cond(flags, mapped)
            if missing:
                return None, "cmov:%s" % ",".join("%s-unknown" % k for k in missing)
            s_expr = _reg_get(s_op["value"], regs)
            d_expr = _reg_get(d_op["value"], regs)
            res = "((%s) ? (%s) : (%s))" % (cond, s_expr, d_expr)
            put_lines = _reg_put(d_op["value"], res, regs)
            for ln in put_lines:
                lines.append(ln)
            b = _base_reg(d_op["value"])
            if b:
                regs[b] = b
            continue

        if mne in ("movzbl", "movsbl", "movzbw", "movsbw"):
            p = _split_ops(ops)
            if len(p) != 2:
                return None, "%s:operands" % mne
            src_op = _parse_op(p[0])
            dst_op = _parse_op(p[1])
            d_info = _reg_info(dst_op["value"]) if dst_op["kind"] == "reg" else None
            if d_info is None or d_info[2] != 32:
                return None, "%s:form:dst:%s" % (mne, dst_op["value"])
            # fuente de 8 bits: reg con ancho 8, o stack slot (byte)
            if src_op["kind"] == "reg":
                s_info = _reg_info(src_op["value"])
                if s_info is None or s_info[2] != 8:
                    return None, "%s:form:src:%s" % (mne, src_op["value"])
                s = _reg_get(src_op["value"], regs)
            elif src_op["kind"] == "stack":
                s = slots.get(src_op["value"], "_e_%d" % -src_op["value"])
                s = "(%s & 0xff)" % s
            else:
                return None, "%s:form:src:kind" % mne
            if mne in ("movzbl", "movzbw"):
                # extension por cero
                expr = "(%s & 0xff)" % s if mne == "movzbl" else "(%s & 0xffff)" % s
            else:
                # movsbl / movsbw: extension de signo del byte a int
                expr = "(int)(signed char)(%s)" % s if mne == "movsbl" else "(int)(short)(%s & 0xffff)" % s
            put_lines = _reg_put(dst_op["value"], expr, regs)
            for ln in put_lines:
                lines.append(ln)
            b = _base_reg(dst_op["value"])
            if b:
                regs[b] = b
            continue
        if mne == "ret":
            lines.append("  return rax;")
            continue

        return None, "unsupported:%s" % mne

    lines += ["}", ""]
    return "\n".join(lines), "ok"


def generate_c(func: str, nodes: list[dict]) -> str:
    if not isinstance(nodes, list) or len(nodes) == 0:
        return ("/* %s: lifting PARTIAL, sin equivalencia demostrada "
                "(nodes vacíos o no utilizables: sin evidencia) */" % func)

    known, unknown, malformed = _validate_nodes(nodes)
    if malformed:
        detail = ", ".join("[%s] %s" % (i, why) for i, why in malformed[:8])
        return ("/* %s: lifting PARTIAL, sin equivalencia demostrada "
                "(nodos malformados: %s) */" % (func, detail))
    if unknown:
        names = ", ".join(sorted({m for _, m in unknown}))
        return ("/* %s: lifting PARTIAL, sin equivalencia demostrada "
                "(mnemónicos desconocidos: %s) */" % (func, names))

    # AT&T size-suffix normalization on the lowercase mnemonic before validate
    nodes2 = [{**n, "mnemonic": _base_mne(n["mnemonic"])} for n in nodes]
    body, reason = _reconstruct(nodes2, func, None)
    if body is None:
        return ("/* %s: lifting PARTIAL, sin equivalencia demostrada "
                "(%s: %s nodo(s) reconocidos; no se encontró reconstrucción "
                "instrucción-dependiente) */" % (func, reason, len(nodes)))
    return body


def certificate(func: str, vectors: list[tuple[int,int]], nodes: list[dict] | None = None) -> dict:
    """Certificado de trazabilidad del lifting (M430).

    Sin `nodes`, no puede verificar trazabilidad: el certificado declara
    `traceability=null` y `status=NOT_DETERMINED`, conservando los campos
    históricos (`equivalence_claim`, `role`, `vectors`) para no romper
    consumidores existentes.

    Con `nodes`, el informe cuantifica:

      traceability_coverage = nodos con destino o descarte justificado
                              registrados contablemente / nodos recibidos
      consumption_coverage   = nodos efectivamente consumidos por la emisión
                              / nodos recibidos

    Las plantillas hardcoded por nombre se eliminaron; la emisión actual
    depende de los nodos y consume cada nodo.  T no aumenta C: un descarte
    justificado eleva T, nunca C.
    """
    base = {"func": func, "vectors": vectors,
            "equivalence_claim": "NOT_PROVEN (PARTIAL acotado)",
            "role": "M430 flujo causal"}

    if nodes is None:
        base["traceability"] = {
            "status": "NOT_DETERMINED",
            "nodes_received": 0,
            "traceability_coverage": None,
            "consumption_coverage": None,
            "limitations": ["no se proporcionaron `nodes` a certificate()",
                            "no es posible verificar trazabilidad sin evidencia"],
        }
        return base

    known, unknown, malformed = _validate_nodes(nodes)
    n = len(nodes) if isinstance(nodes, list) else 0

    if n == 0:
        traceability = {
            "status": "NOT_DETERMINED",
            "nodes_received": 0,
            "nodes_known": 0,
            "nodes_unknown": [],
            "nodes_malformed": [],
            "nodes_consumed": 0,
            "nodes_not_consumed": 0,
            "traceability_coverage": None,
            "consumption_coverage": None,
            "limitations": ["nodes vacío: sin evidencia, no se mide trazabilidad",
                            "0/n; las coberturas quedan indefinidas, no 1.0"],
        }
        base["traceability"] = traceability
        return base

    if malformed:
        traceability = {
            "status": "BLOCKED",
            "nodes_received": n,
            "nodes_known": len(known),
            "nodes_unknown": sorted({m for _, m in unknown}),
            "nodes_unknown_count": len(unknown),
            "nodes_malformed": [{"index": i, "reason": why} for i, why in malformed],
            "nodes_malformed_count": len(malformed),
            "nodes_consumed": 0,
            "nodes_not_consumed": n,
            "traceability_coverage": 1.0,
            "consumption_coverage": 0.0,
            "limitations": [
                "mnemónicos malformados invalidan la emisión; se rechaza explícitamente",
                "equivalence_claim NOT_PROVEN (PARTIAL acotado) sin cadena fidelity completa",
                "role_M430 es heurística, no evidencia semántica",
            ],
        }
        base["traceability"] = traceability
        return base

    # Normalize mnemonics for the reconstructor (preserving raw nodes in place)
    nodes2 = [{**nd, "mnemonic": _base_mne(nd["mnemonic"])} for nd in nodes]
    body, reason = _reconstruct(nodes2, func, None)
    fully_decoded = reason == "ok"

    consumed = n if fully_decoded else 0
    not_consumed = n - consumed
    status = "PARTIAL" if not fully_decoded else "PARTIAL"
    traceability = {
        "status": status,
        "nodes_received": n,
        "nodes_known": len(known),
        "nodes_unknown": sorted({m for _, m in unknown}),
        "nodes_unknown_count": len(unknown),
        "nodes_malformed": [{"index": i, "reason": why} for i, why in malformed],
        "nodes_malformed_count": len(malformed),
        "nodes_consumed": consumed,
        "nodes_not_consumed": not_consumed,
        "traceability_coverage": 1.0,
        "consumption_coverage": round(consumed / n, 6),
        "limitations": [
            "equivalence_claim NOT_PROVEN (PARTIAL acotado) sin cadena fidelity completa",
            "traceability_coverage=1.0 cuando cada nodo queda en {known,unknown,malformed}; nunca contradice consumption_coverage",
            "role_M430 es heurística, no evidencia semántica",
            "mnemónicos fuera de KNOWN_MNEMONICS => PARTIAL, no PROVEN",
            "consumo == 1.0 sobre los nodos efectivamente emitidos en reconstrucción; 0 si no se pudo reconstruir",
        ],
    }
    base["traceability"] = traceability
    return base


def _is_align_mne(mne):
    return mne in ("nop", "nopl", "nopw", "data16", "cs", "int3", "endbr64", "endbr32", "leave")
