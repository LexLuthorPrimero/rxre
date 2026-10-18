#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Traza donde se computa r16 (el danio de
bodyDamage/headDamage) en script 1627."""
import sys
import zlib

sys.path.insert(0, "tools")
import avm1_disasm as A  # noqa: E402
import avm1_sym as S  # noqa: E402


def resolve(pool, item):
    if item[0] == 9:
        return "C16:%d=%s" % (
            item[1], A.resolve_constant(pool, 9, item[1]))
    if item[0] == 8:
        return "LK:%d=%s" % (
            item[1], A.resolve_constant(pool, 8, item[1]))
    if item[0] == 4:
        return "R%d" % item[1]
    if item[0] == 7:
        return "I%d" % item[1]
    return str(item)


def main():
    data = open("raw/original.swf", "rb").read()
    body = zlib.decompress(data[8:])
    nbits = body[0] >> 3
    off = (5 + 4 * nbits + 7) // 8 + 4
    scripts = A.collect_scripts(body, off, len(body))
    for i, s in enumerate(scripts):
        s["_idx"] = i
    pools = A.build_script_pools(body, scripts)

    s = scripts[1627]
    pool = pools.get(1627)
    sym = S.Sym(body, s["offset"], s["length"], pool)
    sym.run()
    actions, _, _ = A.walk_actions(
        body, s["offset"], s["offset"] + s["length"])

    # find bodyDamage = r16 write
    for obj, key, val, aidx in sym.writes:
        if str(key) == "bodyDamage" and str(val) == "r16":
            print("=== bodyDamage = r16 at action %d ==="
                  % aidx)
            lo = max(0, aidx - 90)
            for j in range(lo, aidx + 2):
                code, doff, dlen = actions[j]
                d = body[doff:doff + dlen] if dlen > 0 \
                    else b""
                tag = ""
                if code == 0x96 and dlen > 0:
                    p = A.parse_push_data(d)
                    resolved = [resolve(pool, it)
                                for it in (p or [])]
                    tag = " <Push [%s]>" % (
                        ", ".join(resolved))
                if code == 0x87 and dlen > 0:
                    tag = " <StoreRegister R%d>" % d[0]
                mark = " <<<" if j == aidx else ""
                print("  [%3d] code=0x%02X dlen=%d%s%s"
                      % (j, code, dlen, tag, mark))
            print()
            break


if __name__ == "__main__":
    main()
