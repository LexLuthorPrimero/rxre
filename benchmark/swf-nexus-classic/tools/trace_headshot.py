#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Busca el multiplicador de headshot (R18)
y la computacion de headDamage en
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


def show(actions, body, pool, lo, hi, mark_j):
    for k in range(lo, hi):
        c2, do2, dl2 = actions[k]
        d2 = body[do2:do2 + dl2] if dl2 > 0 else b""
        tag = ""
        if c2 == 0x96 and dl2 > 0:
            p = A.parse_push_data(d2)
            res = [resolve(pool, it) for it in (p or [])]
            tag = " <Push [%s]>" % (", ".join(res))
        if c2 == 0x87 and dl2 > 0:
            tag = " <StoreRegister R%d>" % d2[0]
        mark = " <<<" if k == mark_j else ""
        print("    [%3d] code=0x%02X dlen=%d%s%s"
              % (k, c2, dl2, tag, mark))


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

    # 1) StoreRegister R18 (headshot crit multiplier)
    print("=== StoreRegister R18 (headshot mult) ===")
    for j in range(0, 14259):
        code, doff, dlen = actions[j]
        d = body[doff:doff + dlen] if dlen > 0 else b""
        if code == 0x87 and dlen > 0 and d[0] == 18:
            print("  StoreRegister R18 en accion %d:" % j)
            show(actions, body, pool,
                 max(0, j - 16), j + 1, j)
            print()

    # 2) headDamage = r16 write (headshot path)
    print("=== headDamage = r16 (headshot path) ===")
    for obj, key, val, aidx in sym.writes:
        if str(key) == "headDamage" \
                and str(val) == "r16":
            print("  headDamage = r16 en accion %d:" % aidx)
            show(actions, body, pool,
                 max(0, aidx - 40), aidx + 1, aidx)
            print()
            break


if __name__ == "__main__":
    main()
