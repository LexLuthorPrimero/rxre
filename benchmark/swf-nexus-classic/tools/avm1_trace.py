#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Simulador de pila AVM1: traza asignaciones SetVariable.

Las acciones CORTAS (0x00-0x33) son AVM1 estandar
(RXRE-SWF-024): Pop(0x17), GetVariable(0x1C),
SetVariable(0x1D), Duplicate(0x25), aritmetica
(0x0A-0x12).  Este simulador mantiene una pila y,
al encontrar SetVariable(0x1D), registra la
asignacion (nombre, valor).

LIMITACION (RXRE-SWF-025): las constantes de
combate NO se asignan via SetVariable; fluyen a
llamadas a funcion/metodo (0x4E, 0x4F, 0x52,
0x9D, 0x49) cuyos opcodes NO estan identificados
(dialecto no estandar; sin tabla de referencia).
Por tanto este instrumento recupera las asignaciones
de framework/UI, NO el mapeo de constantes de
combate.

PRODUCER: simulador estructural.  No interpreta
semantica de opcodes no identificados.
"""
import collections
import struct
import sys

from avm1_disasm import collect_scripts, walk_actions

SZ = {0: (None, "String"), 1: (4, "Float"), 2: (0, "Null"),
      3: (0, "Undefined"), 4: (1, "Register"), 5: (1, "Boolean"),
      6: (8, "Type6Pair"), 7: (4, "Integer"), 8: (1, "Lookup"),
      9: (2, "Const16")}

# acciones aritmeticas/comparacion estandar (pop 2, push resultado)
ARITH = {0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11,
         0x13, 0x22, 0x2E}


def parse_push(d):
    pos = 0
    n = len(d)
    out = []
    while pos < n:
        t = d[pos]
        pos += 1
        if t not in SZ:
            return None
        sz, nm = SZ[t]
        if sz is None:
            e = d.find(b"\x00", pos)
            if e < 0:
                return None
            out.append((nm, d[pos:e].decode("latin1")))
            pos = e + 1
        elif sz == 0:
            out.append((nm, None))
        elif sz == 1:
            if pos + 1 > n:
                return None
            out.append((nm, d[pos]))
            pos += 1
        elif sz == 2:
            if pos + 2 > n:
                return None
            out.append((nm, struct.unpack("<H", d[pos:pos + 2])[0]))
            pos += 2
        elif sz == 4:
            if pos + 4 > n:
                return None
            if t == 1:
                out.append((nm, struct.unpack("<f", d[pos:pos + 4])[0]))
            else:
                out.append((nm, struct.unpack("<i", d[pos:pos + 4])[0]))
            pos += 4
        elif sz == 8:
            if pos + 8 > n:
                return None
            f1 = struct.unpack("<f", d[pos:pos + 4])[0]
            out.append((nm, f1))
            pos += 8
    return out if pos == n else None


def parse_pool(d):
    if len(d) < 2:
        return None
    count = struct.unpack("<H", d[:2])[0]
    pos = 2
    strs = []
    for _ in range(count):
        e = d.find(b"\x00", pos)
        if e < 0:
            return None
        strs.append(d[pos:e].decode("latin1"))
        pos = e + 1
    return strs if pos == len(d) else None


def trace_setvariable(body, scripts):
    """Simula la pila y devuelve (assigns, name_assigns, stats).

    assigns: Counter((nombre, valor_repr))
    name_assigns: {nombre: Counter(valor_repr)}
    stats: dict con conteos.
    """
    assigns = collections.Counter()
    name_assigns = collections.defaultdict(collections.Counter)
    total_setvar = 0
    resolved = 0
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        pool = None
        for c, doff, dlen in actions:
            if c == 0x88 and dlen > 0:
                pool = parse_pool(body[doff:doff + dlen])
                break
        stack = []
        for c, doff, dlen in actions:
            if c == 0x96 and dlen > 0:      # Push
                r = parse_push(body[doff:doff + dlen])
                if r is not None:
                    for nm, v in r:
                        if nm in ("Lookup", "Const16") and \
                                pool is not None and \
                                isinstance(v, int) and v < len(pool):
                            stack.append(("str", pool[v]))
                        elif nm == "String":
                            stack.append(("str", v))
                        else:
                            stack.append((nm, v))
            elif c == 0x17:                   # Pop
                if stack:
                    stack.pop()
            elif c == 0x25:                   # Duplicate
                if stack:
                    stack.append(stack[-1])
            elif c in ARITH:                  # aritmetica
                if len(stack) >= 2:
                    stack.pop()
                    stack.pop()
                    stack.append(("int", 0))
            elif c == 0x12:                   # Not
                if stack:
                    stack.pop()
                    stack.append(("int", 0))
            elif c == 0x1C:                   # GetVariable
                if stack:
                    stack.pop()
                stack.append(("var_result", None))
            elif c == 0x1D:                   # SetVariable
                if len(stack) >= 2:
                    vt = stack.pop()
                    nt = stack.pop()
                    total_setvar += 1
                    name = nt[1] if nt[0] == "str" else None
                    val = vt[1]
                    if name is not None:
                        resolved += 1
                        vr = (repr(round(val, 6))
                              if isinstance(val, float) else str(val))
                        assigns[(name, vr)] += 1
                        name_assigns[name][vr] += 1
                elif stack:
                    stack.pop()
    stats = {"total_setvar": total_setvar,
             "resolved": resolved,
             "distinct_pairs": len(assigns)}
    return assigns, name_assigns, stats


def trace_setmember(body, scripts):
    """Simula la pila y, en 0x4E (HYPOTESIS SetMember),
    registra (clave, valor) de los 3 superiores.

    HYPOTESIS: 0x4E = SetMember (object[key]=value).
    Si la hipotesis es correcta, las claves y valores
    tienen sentido (corroborado: wound, item, level...).
    Devuelve (keyval, stats).
    """
    keyval = collections.Counter()
    total_4e = 0
    resolved_4e = 0
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        pool = None
        for c, doff, dlen in actions:
            if c == 0x88 and dlen > 0:
                pool = parse_pool(body[doff:doff + dlen])
                break
        stack = []
        for c, doff, dlen in actions:
            if c == 0x96 and dlen > 0:
                r = parse_push(body[doff:doff + dlen])
                if r is not None:
                    for nm, v in r:
                        if nm in ("Lookup", "Const16") and \
                                pool is not None and \
                                isinstance(v, int) and v < len(pool):
                            stack.append(("str", pool[v]))
                        elif nm == "String":
                            stack.append(("str", v))
                        else:
                            stack.append((nm, v))
            elif c == 0x17:
                if stack:
                    stack.pop()
            elif c == 0x25:
                if stack:
                    stack.append(stack[-1])
            elif c in ARITH:
                if len(stack) >= 2:
                    stack.pop()
                    stack.pop()
                    stack.append(("int", 0))
            elif c == 0x12:
                if stack:
                    stack.pop()
                    stack.append(("int", 0))
            elif c == 0x1C:
                if stack:
                    stack.pop()
                stack.append(("var", None))
            elif c == 0x1D:
                if len(stack) >= 2:
                    stack.pop()
                    stack.pop()
                elif stack:
                    stack.pop()
            elif c == 0x4E:               # HYPOTESIS SetMember
                total_4e += 1
                if len(stack) >= 3:
                    vt = stack[-1]
                    kt = stack[-2]
                    key = kt[1] if kt[0] == "str" else None
                    val = vt[1]
                    if key is not None and \
                            isinstance(val, (int, float)):
                        resolved_4e += 1
                        vr = (repr(round(val, 6))
                              if isinstance(val, float)
                              else str(val))
                        keyval[(key, vr)] += 1
                    stack.pop()
                    stack.pop()
                    stack.pop()
                    stack.append(("obj", None))
                elif stack:
                    stack.pop()
    stats = {"total_4e": total_4e,
             "resolved_4e": resolved_4e,
             "distinct_pairs": len(keyval)}
    return keyval, stats


def main(swf_path):
    import zlib
    data = open(swf_path, "rb").read()
    sig = data[:3]
    if sig == b"CWS":
        body = zlib.decompress(data[8:])
    elif sig == b"FWS":
        body = data[8:]
    else:
        raise ValueError("firma %r" % sig)
    nbits = body[0] >> 3
    off = (5 + 4 * nbits + 7) // 8 + 4
    scripts = collect_scripts(body, off, len(body))
    assigns, name_assigns, stats = trace_setvariable(body, scripts)
    keyval, stats4e = trace_setmember(body, scripts)
    stats["setmember"] = stats4e
    stats["setmember_keyval"] = keyval
    return assigns, name_assigns, stats, keyval, stats4e


if __name__ == "__main__":
    assigns, name_assigns, stats, keyval, stats4e = main(sys.argv[1])
    print("SetVariable total:", stats["total_setvar"])
    print("asignaciones con nombre resuelto:", stats["resolved"])
    print("pares (nombre,valor) distintos:", stats["distinct_pairs"])
    print()
    print("=== Nombres de variables asignadas (top 40) ===")
    nname = collections.Counter()
    for (n, v), c in assigns.items():
        nname[n] += c
    for n, c in nname.most_common(40):
        print("  %-28s : %d" % (n, c))
    print()
    print("=== 0x4E SetMember (HYPOTESIS) ===")
    print("0x4E total:", stats4e["total_4e"])
    print("pares (clave,valor) resueltos:", stats4e["resolved_4e"])
    print("pares distintos:", stats4e["distinct_pairs"])
    print()
    print("=== Pares (clave = valor) de 0x4E ===")
    for (k, v), c in keyval.most_common():
        print("  %-26s = %-10s : %d" % (k, v, c))
