#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extrae pools de constantes y vocabulario de los scripts AVM1
(DoAction + DoInitAction).

Formato de pool verificado empiricamente (F-010):
    0x88, u16 ActionLength, u16 Count, luego count cadenas
    terminadas en NUL.  El count es el SEGUNDO u16; con el
    primero (p.ej. 324) el pool desborda el script, con el
    segundo cabe exactamente.

PRODUCER: no interpreta semantica, solo extrae cadenas.
"""
import json
import re
import struct
import sys


def find_pool(buf):
    """Localiza el primer 0x88 y parsea el pool. Devuelve
    (offset, actionLength, count, strings) o None."""
    idx = buf.find(b"\x88")
    while idx >= 0 and idx + 5 < len(buf):
        actionLength = struct.unpack("<H", buf[idx + 1:idx + 3])[0]
        count = struct.unpack("<H", buf[idx + 3:idx + 5])[0]
        # heuristica: count plausible y las cadenas caben
        if 0 < count < 5000:
            p = idx + 5
            strs = []
            ok = True
            for _ in range(count):
                e = buf.find(b"\x00", p)
                if e < 0 or e >= len(buf):
                    ok = False
                    break
                strs.append(buf[p:e].decode("latin1"))
                p = e + 1
            if ok and p <= len(buf):
                return (idx, actionLength, count, strs)
        idx = buf.find(b"\x88", idx + 1)
    return None


def main(swf_json, body_path):
    d = json.load(open(swf_json))
    body = open(body_path, "rb").read()[8:]
    tags = d["tags"]
    scripts = [t for t in tags if t["name"] in ("DoAction", "DoInitAction")]

    all_pools = []
    all_vocab = set()
    for t in scripts:
        buf = body[t["offset"]:t["offset"] + t["length"]]
        r = find_pool(buf)
        entry = {
            "tag": t["name"],
            "tag_offset": t["offset"],
            "length": t["length"],
            "pool_offset": r[0] if r else None,
            "actionLength": r[1] if r else None,
            "count": r[2] if r else None,  # segundo u16
            "strings": r[3] if r else [],
        }
        all_pools.append(entry)
        if r:
            all_vocab.update(r[3])
        # vocabulario de cadenas imprimibles del script entero
        all_vocab.update(m.decode("latin1")
                         for m in re.findall(rb"[\x20-\x7e]{4,}", buf))

    return {
        "script_count": len(scripts),
        "pools_with_pool": sum(1 for p in all_pools if p["pool_offset"] is not None),
        "pools": all_pools,
        "vocab": sorted(all_vocab),
        "vocab_count": len(all_vocab),
    }


if __name__ == "__main__":
    res = main(sys.argv[1], sys.argv[2])
    json.dump(res, open(sys.argv[3], "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("scripts:", res["script_count"])
    print("con pool:", res["pools_with_pool"])
    print("vocabulario:", res["vocab_count"])
