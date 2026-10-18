#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Desensamblador AVM1 por reglas de longitud.

REGLA DE FORMATO DE ACCION (SWF):
    ActionCode (u8)
    si ActionCode >= 0x80:
        ActionLength (u16)
        Data[ActionLength]
    si no (ActionCode < 0x80):
        sin longitud, sin dato (1 solo byte)

Esta regla permite recorrer el stream de acciones
sin conocer la semantica de cada opcode: basta con
leer el code y, si es >= 0x80, saltar u16+length.

ENCABEZADOS DE TAG:
    DoAction(12):     Action[]  (sin cabecera)
    DoInitAction(59): u16 SpriteId, luego Action[]

CONSTANTPOOL (0x88) — formato SWF estandar:
    0x88, u16 Length, u16 Count, String[Count]
    (Length = bytes de Count+strings; Count = N strings)

PUSH (0x9C):
    0x9C, u16 Length, Data[Length]
    Data = secuencia (type, value):
      0 String, 1 Float(4), 2 Null, 3 Undefined,
      4 Register(1), 5 Boolean(1), 6 Double(8),
      7 Integer(4), 8 Lookup(1)

VALIDACION: el recorrido debe llegar a End(0x00)
sin desbordar el script.  Si desborda, la regla o
la estructura es distinta -> se marca INVALID.

PRODUCER: desensamblador estructural.  No interpreta
semantica de opcode; solo recorre fronteras y extrae
Push.  Los valores numericos son HYPOTHESIS hasta
confirmacion contra un desensamblador de referencia.
"""
import json
import struct
import sys

# tipos de Push: type -> tamanos fijo (None = NUL-terminado)
# tipo 6 = (float32 4 + uint32 4), NO Double (RXRE-SWF-022).
# El uint32 es fraccion 0.32 fixed-point, VALOR SEPARADO (RXRE-SWF-047:
# NO es funcion determinista del float32; la formula
# u=((b&0xFFFFF)*0x100001+128)>>8 es exacta solo 27/61).
# tipo 9 = Const16 (2 bytes), no estandar (RXRE-SWF-021)
PUSH_TYPE_SIZE = {
    0: None, 1: 4, 2: 0, 3: 0, 4: 1,
    5: 1, 6: 8, 7: 4, 8: 1, 9: 2,
}


def parse_push_data(data):
    """Parsea Data[Length] de un Push. Devuelve
    lista de (type, value) o None si no cabe."""
    pos = 0
    out = []
    n = len(data)
    while pos < n:
        t = data[pos]
        pos += 1
        if t not in PUSH_TYPE_SIZE:
            return None
        sz = PUSH_TYPE_SIZE[t]
        if t == 0:
            end = data.find(b"\x00", pos)
            if end < 0:
                return None
            out.append((t, data[pos:end]))
            pos = end + 1
        elif sz == 0:
            out.append((t, None))
        elif sz == 1:
            if pos + 1 > n:
                return None
            out.append((t, data[pos]))
            pos += 1
        elif sz == 4:
            if pos + 4 > n:
                return None
            if t == 1:
                out.append((t, struct.unpack("<f",
                                                data[pos:pos + 4])[0]))
            else:
                out.append((t, struct.unpack("<i",
                                                data[pos:pos + 4])[0]))
            pos += 4
        elif sz == 2:
            # tipo 9 = Const16 (indice de pool de 2 bytes)
            if pos + 2 > n:
                return None
            out.append((t, struct.unpack("<H",
                                            data[pos:pos + 2])[0]))
            pos += 2
        elif sz == 8:
            # tipo 6 = (float32_LE, uint32_LE), NO Double (RXRE-SWF-022).
            # uint32 = fraccion 0.32, valor separado (RXRE-SWF-047).
            if pos + 8 > n:
                return None
            f1 = struct.unpack("<f", data[pos:pos + 4])[0]
            u2 = struct.unpack("<I", data[pos + 4:pos + 8])[0]
            out.append((t, (f1, u2)))
            pos += 8
    return out


def walk_actions(body, off, end, stop_at_end=True):
    """Recorre el stream de acciones. Devuelve
    (acciones, offset_final, valido).
    Cada accion: (code, data_offset, data_length)."""
    actions = []
    o = off
    while o < end:
        code = body[o]
        o += 1
        if code == 0x00:      # End
            actions.append((0x00, o, 0))
            if stop_at_end:
                return actions, o, True
            continue
        if code >= 0x80:
            if o + 2 > end:
                return actions, o, False
            ln = struct.unpack("<H", body[o:o + 2])[0]
            o += 2
            actions.append((code, o, ln))
            o += ln
            if o > end:
                return actions, o, False
        else:
            actions.append((code, o, 0))
    return actions, o, True


def read_tags(body, off, end, stop_at_end=False):
    tags = []
    while off + 2 <= end:
        hdr = struct.unpack("<H", body[off:off + 2])[0]
        code, ln = hdr >> 6, hdr & 0x3F
        off += 2
        if ln == 0x3F:
            ln = struct.unpack("<I", body[off:off + 4])[0]
            off += 4
        tags.append((code, ln, off))
        off += ln
        if stop_at_end and code == 0:
            break
    return tags, off


def collect_scripts(body, off, end, depth=0, path="root"):
    scripts = []
    tags, _ = read_tags(body, off, end, stop_at_end=(depth > 0))
    for code, ln, toff in tags:
        if code == 12:      # DoAction (sin cabecera)
            scripts.append({"type": "DoAction",
                              "offset": toff,
                              "length": ln,
                              "path": path,
                              "sprite_id": None})
        elif code == 59:    # DoInitAction (u16 SpriteId)
            sid = (struct.unpack("<H",
                                   body[toff:toff + 2])[0]
                   if ln >= 2 else None)
            scripts.append({"type": "DoInitAction",
                              "offset": toff + 2,
                              "length": ln - 2 if ln >= 2 else 0,
                              "path": path,
                              "sprite_id": sid})
        elif code == 39:    # DefineSprite -> recurse
            if ln >= 4:
                sid = struct.unpack("<H",
                                        body[toff:toff + 2])[0]
                sub = collect_scripts(
                    body, toff + 4, toff + ln,
                    depth=depth + 1,
                    path="%s/sprite(%d)" % (path, sid))
                scripts.extend(sub)
    return scripts


# ---------------------------------------------------------------------------
# SEMANTICA DE OPCODES RECUPERADA ESTA SESION (RXRE-SWF-028/029/030/033)
# ---------------------------------------------------------------------------
# Efectos de pila PROBADOS por balance de pila (pop, push):
#   0x4E = GetMember  (pop 2, push 1)  — LEER  objeto[clave]   (RXRE-SWF-028)
#   0x4F = SetMember  (pop 3, push 0)  — ESCRIBIR objeto[clave]=valor (RXRE-SWF-029)
# Efectos netos DETERMINADOS por el simulador de pila con
# CFG: consenso UNANIME entre scripts consistentes; metodo
# validado (0x4E recuperado como -1 en 24/25 scripts)
# (RXRE-SWF-043/044).  neto = push - pop:
#   0x9D BranchIf = -1 (consume la condicion)   4 scripts
#   0x40          = -1 (pop1)                  16 scripts
#   0x49          = -1 (pop1)                   6 scripts
#   0x3E          = -1 (pop1)                   2 scripts
#   0x9F          = -1 (pop1)                  18 scripts
#   0x42          =  0 (sin efecto)             2 scripts
#   0x81          =  0 (sin efecto)             2 scripts
#   0x8C          =  0 (sin efecto)             2 scripts
# Hipotesis (SUPPORTED, no probadas por balance):
#   0x52 = CallMethod (efecto depende del # de
#          args en la pila: -2/-3/-4, no
#          determinable por profundidad),
#   0x87 = StoreRegister (dominante 0, 6/7;
#          discordancia -1), 0x67 = comparacion
#          unaria, 0x99 = salto incondicional.
# Discordantes (no unanimes): 0x3D,0x43,0x47,
#   0x50,0x53.  Sin datos: 0x48,0x51.
# Decodificacion de salto PROBADA (RXRE-SWF-042):
#   0x99 = salto incondicional (1 sucesor);
#   0x9D = branch condicional (2 sucesores:
#          destino + caida);
#   destino = pos_campo_offset + 2 + int16_signo
#   (7053/7053 saltos caen en limites de
#   instruccion).
STACK_EFFECT_PROVEN = {
    0x4E: (2, 1),   # GetMember
    0x4F: (3, 0),   # SetMember
}
# Netos determinados por CFG (RXRE-SWF-044): code -> neto
CFG_DETERMINED_NET = {
    0x9D: -1, 0x40: -1, 0x49: -1, 0x3E: -1,
    0x9F: -1, 0x42: 0, 0x81: 0, 0x8C: 0,
}
OPCODE_SEMANTICS = {
    0x4E: ("GetMember", "PROVEN", "pop objeto,clave; push objeto[clave]"),
    0x4F: ("SetMember", "PROVEN", "pop objeto,clave,valor; objeto[clave]=valor"),
    0x9D: ("BranchIf", "SUPPORTED", "CFG unanime(4): pop condicion; branch (neto -1)"),
    0x99: ("Jump", "SUPPORTED", "salto incondicional (data=offset int16 signo)"),
    0x40: ("?", "SUPPORTED", "CFG unanime(16): pop1 neto (neto -1)"),
    0x49: ("?", "SUPPORTED", "CFG unanime(6): pop1 neto (neto -1)"),
    0x3E: ("?", "SUPPORTED", "CFG unanime(2): pop1 neto (neto -1)"),
    0x9F: ("?", "SUPPORTED", "CFG unanime(18): pop1 neto (neto -1)"),
    0x42: ("?", "SUPPORTED", "CFG unanime(2): sin efecto de pila (neto 0)"),
    0x81: ("?", "SUPPORTED", "CFG unanime(2): sin efecto de pila (neto 0)"),
    0x8C: ("?", "SUPPORTED", "CFG unanime(2): sin efecto de pila (neto 0)"),
    0x52: ("CallMethod", "NOT_DETERMINED", "efecto depende de #args en pila (-2/-3/-4)"),
    0x87: ("StoreRegister", "NOT_DETERMINED", "dominante 0 (6/7); discordancia -1"),
    0x67: ("UnaryCompare", "SUPPORTED", "hipotesis: pop1 push1"),
    0x8E: ("DefineFunction2", "PROVEN", "nombre NUL, u16 numParams, params con reg"),
    0x9B: ("DefineFunction", "PROVEN", "nombre NUL, u16 numParams, params NUL"),
    0x88: ("ConstantPool", "PROVEN", "data[0:2]=u16 Count, Count cadenas NUL"),
    0x96: ("Push", "PROVEN", "NO ESTANDAR (estandar=0x9C); constantes tipadas"),
}


def parse_constant_pool(data):
    """ConstantPool(0x88): data[0:2]=u16 Count, luego Count cadenas
    NUL-terminadas. El offset de walk_actions YA esta pasado ActionLength,
    por lo que Count es el PRIMER u16 de data (RXRE-SWF-030)."""
    if len(data) < 2:
        return None
    count = struct.unpack("<H", data[0:2])[0]
    pos = 2
    n = len(data)
    strings = []
    for _ in range(count):
        e = data.find(b"\x00", pos)
        if e < 0:
            return None
        strings.append(data[pos:e].decode("latin1"))
        pos = e + 1
    return strings if pos == n else None


def build_script_pools(body, scripts):
    """Construye pool activo por script. Un 0x88 fija el pool del script;
    los scripts sin 0x88 heredan el pool mas reciente (ambito de pool)."""
    pools = {}
    current = None
    for s in scripts:
        if s["length"] <= 0:
            pools[s.get("_idx")] = current
            continue
        actions, _, _ = walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        local = None
        for code, doff, dlen in actions:
            if code == 0x88 and dlen > 0:
                p = parse_constant_pool(body[doff:doff + dlen])
                if p is not None:
                    local = p
        if local is not None:
            pools[s.get("_idx")] = local
            current = local
        else:
            pools[s.get("_idx")] = current
    return pools


def resolve_constant(pool, ptype, value):
    """Resuelve Lookup(8, 1B) / Const16(9, 2B) a cadena del pool."""
    if not pool:
        return None
    if ptype in (8, 9) and isinstance(value, int) and 0 <= value < len(pool):
        return pool[value]
    return None


def decode_define_function(data, opcode):
    """DefineFunction(0x9B) / DefineFunction2(0x8E).
    Devuelve (nombre, [params], regCount, flags, body) o None.
    0x9B: nombre NUL, u16 numParams, params (nombre NUL
          cada una, SIN indice de registro), body.
    0x8E: nombre NUL, u16 numParams, u8 regCount, u16 flags,
          params (u8 regIdx + nombre NUL cada una), body.

    FORMATO PROBADO contra bytes brutos (RXRE-SWF-048):
      createWound(0x8E, dlen=29): nombre"createWound",
        numParams=1, regCount=3, flags=0x0029,
        param0 reg=2 "inNumber", body=2B.
      tick(0x8E, dlen=12): nombre"tick", numParams=0,
        regCount=3, flags=0x0069, body=2B.
    El flags es u16 (no u8): con u8 el cuerpo de la
    funcion dlen=149 seria [End,0x75,End] (malformado);
    con u16 es [0x75,End] (bien formado).  (RXRE-SWF-048)

    CUERPO = TOKEN NATIVO DE 2 BYTES (RXRE-SWF-048):
    TODO DefineFunction/DefineFunction2 de este SWF tiene
    un cuerpo de exactamente 2 bytes [opcode, ...].  311
    cuerpos empiezan con opcode >= 0x80 (0x9C, 0xC0,
    0xD7, 0xC9, 0xC4...), lo que ES IMPOSIBLE para una
    accion larga estandar (necesitaria u16 length + datos,
    >2 bytes).  Ergo el cuerpo NO es una secuencia de
    acciones AVM1 estandar: es un token de llamada a
    rutina nativa.  La formula exacta de combate NO esta
    en los cuerpos; hay que recuperarla del stream
    principal (Push/GetMember/arith/SetMember)."""
    pos = 0
    n = len(data)
    e = data.find(b"\x00", pos)
    if e < 0:
        return None
    name = data[pos:e].decode("latin1")
    pos = e + 1
    if pos + 2 > n:
        return None
    numparams = struct.unpack("<H", data[pos:pos + 2])[0]
    pos += 2
    regcount = None
    flags = None
    if opcode == 0x8E:
        if pos + 3 > n:
            return None
        regcount = data[pos]
        pos += 1
        flags = struct.unpack("<H", data[pos:pos + 2])[0]
        pos += 2
    params = []
    for _ in range(numparams):
        if opcode == 0x8E:
            if pos + 1 > n:
                return None
            pos += 1                # u8 indice de registro (DefineFunction2)
        e = data.find(b"\x00", pos)
        if e < 0:
            return None
        params.append(data[pos:e].decode("latin1"))
        pos = e + 1
    return (name, params, regcount, flags, data[pos:])


def disasm_script(body, s):
    """Desensambla un script. Devuelve
    (valid, actions, pushes, numerics, strings)."""
    actions, oend, valid = walk_actions(
        body, s["offset"], s["offset"] + s["length"])
    pushes = []
    numerics = []
    strings = []
    for code, doff, dlen in actions:
        if code == 0x96:      # Push (NO ESTANDAR; estandar=0x9C)
            data = body[doff:doff + dlen]
            parsed = parse_push_data(data)
            if parsed is not None:
                pushes.append({
                    "offset": doff - 3,
                    "length": dlen,
                    "constants": [
                        {"type": t, "value":
                            (v.decode("latin1")
                             if isinstance(v, bytes) else v)}
                        for t, v in parsed],
                })
                for t, v in parsed:
                    if t == 6 and isinstance(v, tuple):
                        numerics.append(v[0])  # float32 del par
                    elif t in (1, 7):
                        numerics.append(v)
                    elif t == 0:
                        strings.append(v)
    return valid, actions, pushes, numerics, strings


def main(swf_path):
    data = open(swf_path, "rb").read()
    sig = data[:3]
    if sig == b"CWS":
        import zlib
        body = zlib.decompress(data[8:])
    elif sig == b"FWS":
        body = data[8:]
    else:
        raise ValueError("firma %r" % sig)

    nbits = body[0] >> 3
    rect_nbytes = (5 + 4 * nbits + 7) // 8
    off = rect_nbytes + 4

    scripts = collect_scripts(body, off, len(body))

    all_pushes = []
    numeric = []
    strings = []
    valid_count = 0
    invalid_count = 0
    for s in scripts:
        if s["length"] <= 0:
            continue
        valid, actions, pushes, nums, strs = disasm_script(body, s)
        s["n_actions"] = len(actions)
        s["valid"] = valid
        s["push_count"] = len(pushes)
        if valid:
            valid_count += 1
        else:
            invalid_count += 1
        for p in pushes:
            p["script_type"] = s["type"]
            p["path"] = s["path"]
            all_pushes.append(p)
        numeric.extend(nums)
        strings.extend(strs)

    ints = sorted(v for v in numeric if isinstance(v, int))
    floats = sorted(v for v in numeric
                      if isinstance(v, float))

    return {
        "total_scripts": len(scripts),
        "valid_parse": valid_count,
        "invalid_parse": invalid_count,
        "push_count": len(all_pushes),
        "numeric_count": len(numeric),
        "int_count": len(ints),
        "float_count": len(floats),
        "string_count": len(strings),
        "int_histogram": {str(v): ints.count(v)
                            for v in sorted(set(ints))},
        "float_histogram": {str(v): floats.count(v)
                              for v in sorted(set(floats))},
        "scripts": scripts,
        "pushes": all_pushes,
    }


if __name__ == "__main__":
    res = main(sys.argv[1])
    summary = {k: v for k, v in res.items()
                 if k not in ("scripts", "pushes")}
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if out:
        json.dump(summary, open(out, "w",
                                    encoding="utf-8"),
                  indent=1, ensure_ascii=False)
    print("scripts:", res["total_scripts"])
    print("parse valido:", res["valid_parse"])
    print("parse invalido:", res["invalid_parse"])
    print("Push acciones:", res["push_count"])
    print("constantes numericas:", res["numeric_count"])
    print("  enteros:", res["int_count"])
    print("  floats:", res["float_count"])
    print("cadenas Push:", res["string_count"])
    print()
    print("=== top enteros (candidatos a balance) ===")
    top = sorted(res["int_histogram"].items(),
                   key=lambda kv: -kv[1])[:60]
    for val, cnt in top:
        print("  %8s : %d" % (val, cnt))
    print()
    print("=== top floats ===")
    topf = sorted(res["float_histogram"].items(),
                    key=lambda kv: -kv[1])[:30]
    for val, cnt in topf:
        print("  %-16s : %d" % (val, cnt))
