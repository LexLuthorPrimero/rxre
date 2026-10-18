#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Busca donde se computa r3 (la base del
danio) antes de la accion 14259 en
script 1627."""
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
    actions, _, _ = A.walk_actions(
        body, s["offset"], s["offset"] + s["length"])

    # StoreRegister a R3/R18 en el rango del
    # computo de danio [14000, 14259]
    targets = [3, 18]  # r3 (base) y r18 (headshot mult)
    print("=== StoreRegister a R3 / R18 en [14000,14259] ===")
    for j in range(14000, 14259):
        code, doff, dlen = actions[j]
        d = body[doff:doff + dlen] \
            if dlen > 0 else b""
        if code == 0x87 and dlen > 0 \
                and d[0] in targets:
            print("\n  StoreRegister R%d en accion %d:" % (
                d[0], j))
            lo = max(0, j - 22)
            for k in range(lo, j + 1):
                c2, do2, dl2 = actions[k]
                d2 = body[do2:do2 + dl2] \
                    if dl2 > 0 else b""
                tag = ""
                if c2 == 0x96 and dl2 > 0:
                    p = A.parse_push_data(d2)
                    res = [resolve(pool, it)
                           for it in (p or [])]
                    tag = " <Push [%s]>" % (
                        ", ".join(res))
                if c2 == 0x87 and dl2 > 0:
                    tag = " <StoreRegister R%d>" % d2[0]
                mark = " <<<" if k == j else ""
                print("    [%3d] code=0x%02X dlen=%d%s%s"
                      % (k, c2, dl2, tag, mark))


if __name__ == "__main__":
    main()
