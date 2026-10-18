#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extrae heuristicamente las constantes numericas de las
acciones Push(0x9C) del bytecode AVM1.

Formato Push (SWF 5+):
    0x9C, u16 Length, Data[Length]
    Data = secuencia de (type, value):
      0 String   (NUL-terminado, longitud variable)
      1 Float    (4 bytes, IEEE-754)
      2 Null     (0 bytes)
      3 Undefined(0 bytes)
      4 Register (1 byte)
      5 Boolean  (1 byte)
      6 Double   (8 bytes, IEEE-754)
      7 Integer  (4 bytes, signed)
      8 Lookup   (1 byte, indice de ConstantPool)  [SWF 6+]

VALIDACION (para filtrar falsos positivos de 0x9C en datos):
    - todo byte de tipo esta en 0..8
    - cada valor cabe dentro de Length
    - el parse consume EXACTAMENTe Length bytes (pos == Length)

PRODUCER: heuristica. NO es un desensamblador completo (no
rastrea fronteras de accion). Un 0x9C en datos de otra accion
que por casualidad parsee exacto es un falso positivo; la
validacion exacta lo hace improbable pero no imposible.
Los valores son HYPOTHESIS hasta confirmacion con un
desensamblador completo (RXRE-SWF-015).
"""
import json
import struct
import sys

# tamanos fijos por tipo (None = variable, 0 = sin dato)
TYPE_SIZE = {
    0: None,   # String: variable (NUL-terminado)
    1: 4,      # Float
    2: 0,      # Null
    3: 0,      # Undefined
    4: 1,      # Register
    5: 1,      # Boolean
    6: 8,      # Double
    7: 4,      # Integer
    8: 1,      # Lookup
}


def parse_push(data):
    """Parsea Data[Length] de un Push. Devuelve lista de
    (type, value) o None si no parsea exactamente."""
    pos = 0
    out = []
    n = len(data)
    while pos < n:
        t = data[pos]
        pos += 1
        if t not in TYPE_SIZE:
            return None
        sz = TYPE_SIZE[t]
        if t == 0:  # String: hasta NUL
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
            if t == 1:      # Float
                out.append((t, struct.unpack("<f", data[pos:pos + 4])[0]))
            else:            # Integer (t == 7)
                out.append((t, struct.unpack("<i", data[pos:pos + 4])[0]))
            pos += 4
        elif sz == 8:      # Double
            if pos + 8 > n:
                return None
            out.append((t, struct.unpack("<d", data[pos:pos + 8])[0]))
            pos += 8
    if pos != n:
        return None
    return out


def scan_script(buf):
    """Escanea un script buscando Push validos."""
    pushes = []
    i = buf.find(b"\x9c")
    while i >= 0 and i + 3 <= len(buf):
        length = struct.unpack("<H", buf[i + 1:i + 3])[0]
        end = i + 3 + length
        if end <= len(buf) and length > 0:
            parsed = parse_push(buf[i + 3:end])
            if parsed is not None:
                pushes.append({
                    "offset": i,
                    "length": length,
                    "constants": [
                        {"type": t, "value":
                            (v.decode("latin1") if isinstance(v, bytes)
                             else v)}
                        for t, v in parsed
                    ],
                })
        i = buf.find(b"\x9c", i + 1)
    return pushes


def main(swf_json, body_path):
    d = json.load(open(swf_json))
    body = open(body_path, "rb").read()[8:]
    tags = d["tags"]
    scripts = [t for t in tags if t["name"] in ("DoAction", "DoInitAction")]

    all_pushes = []
    numeric = []          # valores numericos (Float/Integer/Double)
    strings = []
    for t in scripts:
        buf = body[t["offset"]:t["offset"] + t["length"]]
        pushes = scan_script(buf)
        for p in pushes:
            p["tag"] = t["name"]
            p["tag_offset"] = t["offset"]
            all_pushes.append(p)
            for c in p["constants"]:
                if c["type"] in (1, 6, 7):       # Float/Double/Integer
                    numeric.append(c["value"])
                elif c["type"] == 0:               # String
                    strings.append(c["value"])

    # distribucion de valores numericos enteros (candidatos a balance)
    ints = sorted(v for v in numeric if isinstance(v, int))
    floats = sorted(v for v in numeric if isinstance(v, float))

    return {
        "script_count": len(scripts),
        "push_count": len(all_pushes),
        "numeric_constant_count": len(numeric),
        "int_constant_count": len(ints),
        "float_constant_count": len(floats),
        "string_constant_count": len(strings),
        "int_histogram": {str(v): ints.count(v) for v in
                          sorted(set(ints))},
        "pushes": all_pushes,
    }


if __name__ == "__main__":
    res = main(sys.argv[1], sys.argv[2])
    json.dump(res, open(sys.argv[3], "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("scripts:", res["script_count"])
    print("Push validos:", res["push_count"])
    print("constantes numericas:", res["numeric_constant_count"])
    print("  enteros:", res["int_constant_count"])
    print("  floats:", res["float_constant_count"])
    print("cadenas Push:", res["string_constant_count"])
    print()
    print("=== histograma de enteros (candidatos a balance) ===")
    hist = res["int_histogram"]
    top = sorted(hist.items(), key=lambda kv: -kv[1])[:40]
    for val, cnt in top:
        print("  %6s : %d" % (val, cnt))
