#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Parser recursivo de SWF: entra en DefineSprite(39)
para encontrar los DoAction ANIDADOS (la mayoria de la
logica del juego vive dentro de sprites, no a nivel
superior).

Luego escanea cada script (DoAction + DoInitAction,
superior y anidado) buscando acciones Push(0x9C) y
extrae sus constantes numericas (Float/Integer/Double).

Formato de tag (SWF):
    u16 header:  code = header >> 10 ... no:
    en realidad code = header >> 6, length = header & 0x3F
    si length == 0x3F: u32 length adicional
    (ver swfparse.py, verificado contra el original)

DefineSprite(39) body:
    u16 SpriteId
    u16 FrameCount
    Tag[]  (control tags, terminados por End(0))

PRODUCER: estructural.  No interpreta semantica AVM1;
solo localiza scripts y extrae constantes Push con
validacion de parse exacto.
"""
import json
import struct
import sys

from avm1_push import parse_push  # reutiliza el parser de Push


def read_tags(body, off, end, stop_at_end=False):
    """Lee tags desde off hasta end. Devuelve
    (lista de (code, length, offset), siguiente_off)."""
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
    """Recorre recursivamente los tags.  Devuelve lista de
    scripts DoAction/DoInitAction con su offset en body."""
    scripts = []
    tags, _ = read_tags(body, off, end, stop_at_end=(depth > 0))
    for code, ln, toff in tags:
        if code == 12:      # DoAction
            scripts.append({
                "type": "DoAction",
                "offset": toff,
                "length": ln,
                "path": path,
                "depth": depth,
            })
        elif code == 59:    # DoInitAction
            scripts.append({
                "type": "DoInitAction",
                "offset": toff,
                "length": ln,
                "path": path,
                "depth": depth,
            })
        elif code == 39:    # DefineSprite -> recurse
            # body: u16 SpriteId, u16 FrameCount, tags...
            if ln >= 4:
                sid = struct.unpack("<H",
                                    body[toff:toff + 2])[0]
                fc = struct.unpack("<H",
                                   body[toff + 2:toff + 4])[0]
                sub = collect_scripts(
                    body, toff + 4, toff + ln,
                    depth=depth + 1,
                    path="%s/sprite(%d)" % (path, sid))
                scripts.extend(sub)
    return scripts


def scan_push(buf):
    """Escanea un script buscando Push(0x9C) validos."""
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
                            (v.decode("latin1")
                             if isinstance(v, bytes) else v)}
                        for t, v in parsed],
                })
        i = buf.find(b"\x9c", i + 1)
    return pushes


def main(swf_path):
    data = open(swf_path, "rb").read()
    sig, ver = data[:3], data[3]
    if sig == b"CWS":
        import zlib
        body = zlib.decompress(data[8:])
    elif sig == b"FWS":
        body = data[8:]
    else:
        raise ValueError("firma %r" % sig)

    # header: RECT + framerate + framecount -> saltar al primer tag
    # (replica swfparse.py para hallar el inicio del stream)
    nbits = body[0] >> 3
    rect_nbytes = (5 + 4 * nbits + 7) // 8
    off = rect_nbytes + 4  # + framerate(2) + framecount(2)

    scripts = collect_scripts(body, off, len(body))

    # escanea cada script
    all_pushes = []
    numeric = []
    strings = []
    for s in scripts:
        buf = body[s["offset"]:s["offset"] + s["length"]]
        pushes = scan_push(buf)
        if pushes:
            s["push_count"] = len(pushes)
            for p in pushes:
                p["script_type"] = s["type"]
                p["script_offset"] = s["offset"]
                p["path"] = s["path"]
                all_pushes.append(p)
                for c in p["constants"]:
                    if c["type"] in (1, 6, 7):
                        numeric.append(c["value"])
                    elif c["type"] == 0:
                        strings.append(c["value"])

    ints = sorted(v for v in numeric if isinstance(v, int))
    floats = sorted(v for v in numeric if isinstance(v, float))

    return {
        "total_scripts": len(scripts),
        "doaction": sum(1 for s in scripts
                        if s["type"] == "DoAction"),
        "doinitaction": sum(1 for s in scripts
                            if s["type"] == "DoInitAction"),
        "scripts_with_push": sum(1 for s in scripts
                                 if s.get("push_count")),
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
    out = sys.argv[2] if len(sys.argv) > 2 else None
    # no volcar 'scripts' ni 'pushes' completos (grandes)
    summary = {k: v for k, v in res.items()
               if k not in ("scripts", "pushes")}
    if out:
        json.dump(summary, open(out, "w",
                                encoding="utf-8"),
                  indent=1, ensure_ascii=False)
    print("scripts totales (superior+anidados):",
          res["total_scripts"])
    print("  DoAction:", res["doaction"])
    print("  DoInitAction:", res["doinitaction"])
    print("scripts con Push:", res["scripts_with_push"])
    print("Push validos:", res["push_count"])
    print("constantes numericas:", res["numeric_count"])
    print("  enteros:", res["int_count"])
    print("  floats:", res["float_count"])
    print("cadenas Push:", res["string_count"])
    print()
    print("=== top enteros (candidatos a balance) ===")
    top = sorted(res["int_histogram"].items(),
                 key=lambda kv: -kv[1])[:50]
    for val, cnt in top:
        print("  %8s : %d" % (val, cnt))
    print()
    print("=== top floats ===")
    topf = sorted(res["float_histogram"].items(),
                  key=lambda kv: -kv[1])[:30]
    for val, cnt in topf:
        print("  %-14s : %d" % (val, cnt))
