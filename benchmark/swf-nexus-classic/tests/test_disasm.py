#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Test de regresion del desensamblador AVM1 (avm1_disasm.py).

Valida que las correcciones no-estandar permanezcan:
  - Push = opcode 0x96 (no 0x9C)          (RXRE-SWF-020)
  - tipo 6 = (float32, uint32), no Double  (RXRE-SWF-022)
  - tipo 9 = Const16 (2 bytes)             (RXRE-SWF-021)
  - ConstantPool 0x88 = accion autonoma    (RXRE-SWF-012)

Si alguna de estas se rompe (p.ej. alguien revierte
0x96 a 0x9C), push_count volvera a 0 y este test
falla.  Verifica contra los conteos OBSERVED.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import avm1_disasm  # noqa: E402
import avm1_cfg    # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
SWF = os.path.join(ROOT, "raw", "original.swf")

# Conteos OBSERVED (extraccion verificada; ver raw/avm1-constants.json)
EXPECTED = {
    "total_scripts": 1749,
    "valid_parse": 1749,
    "invalid_parse": 0,
    "push_count": 54187,
    "int_count": 17033,
    "float_count": 5435,
    "string_count": 2918,
}

# Conteos OBSERVED de semantica recuperada esta sesion
# (inmutables: el SWF original no se modifica)
SEMANTIC = {
    "getmember_0x4e": 24316,     # RXRE-SWF-028
    "setmember_0x4f": 8359,      # RXRE-SWF-029
    "constant_pool_0x88": 456,   # RXRE-SWF-030
    "define_function_0x9b": 289, # RXRE-SWF-033
    "define_function2_0x8e": 1053,
    "callmethod_0x52": 7699,     # RXRE-SWF-035 (SUPPORTED)
    "jump_0x99": 1610,           # RXRE-SWF-036 (SUPPORTED)
    "branch_0x9d": 5443,
    "store_register_0x87": 2731, # RXRE-SWF-037 (SUPPORTED)
    "unary_compare_0x67": 657,   # RXRE-SWF-038 (SUPPORTED)
}
FUNCTION_NAMES = {"tick": 196, "createWound": 8}
BIGGEST_POOL = 908               # RXRE-SWF-031
STORE_RESOLVED_PROPS = 121       # RXRE-SWF-034
RMW_RESOLVED_PROPS = 15


def check(name, got, want):
    ok = got == want
    print("test: %-28s got=%-8s want=%-8s %s"
          % (name, got, want, "OK" if ok else "FAIL"))
    return ok


def main():
    res = avm1_disasm.main(SWF)
    ok = True
    for k, want in EXPECTED.items():
        ok &= check(k, res[k], want)

    body = _body()
    scripts = res["scripts"]
    for i, s in enumerate(scripts):
        s["_idx"] = i

    # El tipo 6 NO es Double: el primer valor de un par
    # debe ser un float32 pequeno (multiplicador), no un
    # double astronomico.  Recolectar pares tipo 6.
    pairs = _collect_type6(body, scripts)
    check("type6_pairs_present", len(pairs) > 0, True)
    # todos los float32 del rango de combate son |v| < 1e4
    small = all(abs(f) < 1e4 for f, _u in pairs)
    check("type6_float32_not_double", small, True)
    # si fuera Double, habria valores ~1e170
    huge = any(abs(f) > 1e10 for f, _u in pairs)
    check("type6_no_astronomical", huge, False)

    # --- REFUTACION: uint32 NO es funcion del float32 (RXRE-SWF-047) ---
    for name, got, want in _type6_refutation(body, scripts):
        ok &= check(name, got, want)

    # --- semantica recuperada (RXRE-SWF-028/029/030/033) ---
    opcount = _collect_opcodes(body, scripts)
    for k, want in SEMANTIC.items():
        ok &= check(k, opcount.get(_OPCODE_OF[k], 0), want)

    # --- ConstantPool: formato + pool mas grande ---
    pools = avm1_disasm.build_script_pools(body, scripts)
    biggest = max((p for p in pools.values() if p), key=len, default=[])
    check("biggest_pool", len(biggest), BIGGEST_POOL)
    check("pool_has_game_vocab",
          all(t in biggest for t in
              ("_global", "MadnessCharacter", "targetsHit", "ASSetPropFlags")),
          True)

    # --- DefineFunction: nombres recuperados ---
    fn = _collect_function_names(body, scripts)
    for name, want in FUNCTION_NAMES.items():
        ok &= check("fn_%s" % name, fn.get(name, 0), want)

    # --- correccion de decodificacion de funcion (RXRE-SWF-048) ---
    sig_tests = _function_signature_tests(body, scripts)
    for name, got, want in sig_tests:
        ok &= check(name, got, want)

    # --- resolucion de propiedades (RXRE-SWF-031/034) ---
    store_props, rmw_props = _resolve_properties(body, scripts, pools)
    check("store_resolved_props", len(store_props), STORE_RESOLVED_PROPS)
    check("rmw_resolved_props", len(rmw_props), RMW_RESOLVED_PROPS)
    check("myDamage_resolved", "myDamage" in store_props, True)
    check("myArmor_resolved", "myArmor" in store_props, True)
    check("myDash_resolved", "myDash" in store_props, True)

    # --- simulador de pila con CFG (RXRE-SWF-042/043/044) ---
    n_cfg = _cfg_tests(body, scripts)
    for name, got, want in n_cfg:
        ok &= check(name, got, want)

    # --- SwainMath.randomNumber (RXRE-SWF-052) ---
    n_swm = _swainmath_tests(body, scripts, pools)
    for name, got, want in n_swm:
        ok &= check(name, got, want)

    print()
    fails = 0
    n_t6 = _type6_refutation(body, scripts)
    print("%d checks" % (len(EXPECTED) + 4 + len(SEMANTIC)
                         + 2 + len(FUNCTION_NAMES) + 6
                         + len(sig_tests)
                         + len(n_cfg) + len(n_swm)
                         + len(n_t6)))
    return 0 if ok else 1


_OPCODE_OF = {
    "getmember_0x4e": 0x4E, "setmember_0x4f": 0x4F,
    "constant_pool_0x88": 0x88, "define_function_0x9b": 0x9B,
    "define_function2_0x8e": 0x8E, "callmethod_0x52": 0x52,
    "jump_0x99": 0x99, "branch_0x9d": 0x9D,
    "store_register_0x87": 0x87, "unary_compare_0x67": 0x67,
}


def _collect_opcodes(body, scripts):
    """Cuenta cada opcode AVM1 en todos los scripts."""
    counts = {}
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        for code, _doff, _dlen in actions:
            counts[code] = counts.get(code, 0) + 1
    return counts


def _function_signature_tests(body, scripts):
    """RXRE-SWF-048: decodificacion correcta de
    DefineFunction/DefineFunction2 (pasando el opcode)
    y el hallazgo de que los CUERPOS son tokens
    nativos de 2 bytes (no acciones AVM1 estandar)."""
    tests = []
    funcs = []
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        for code, doff, dlen in actions:
            if code in (0x9B, 0x8E) and dlen > 0:
                r = avm1_disasm.decode_define_function(
                    body[doff:doff + dlen], code)
                if r:
                    funcs.append((code,) + r)
    # createWound(0x8E) debe tener el param "inNumber",
    # regCount y flags leidos (antes estaba desalineado)
    cw = [f for f in funcs
          if f[1] == "createWound" and f[0] == 0x8E]
    tests.append(("fn2_createWound_has_inNumber",
                  len(cw) > 0
                  and "inNumber" in cw[0][2], True))
    tests.append(("fn2_createWound_regcount_set",
                  cw[0][3] is not None, True))
    tests.append(("fn2_createWound_flags_set",
                  cw[0][4] is not None, True))
    # tick(0x8E) numParams=0, regCount=3, flags=0x0069
    tk = [f for f in funcs
          if f[1] == "tick" and f[0] == 0x8E]
    tests.append(("fn2_tick_numparams0",
                  tk[0][2] == [], True))
    tests.append(("fn2_tick_regcount3",
                  tk[0][3] == 3, True))
    tests.append(("fn2_tick_flags0069",
                  tk[0][4] == 0x0069, True))
    # TODO DefineFunction(0x9B) createWound: params SIN
    # regCount/flags (regCount=None, flags=None)
    cw9b = [f for f in funcs
            if f[1] == "createWound" and f[0] == 0x9B]
    tests.append(("fn9b_createWound_noregcount",
                  cw9b[0][3] is None, True))
    tests.append(("fn9b_createWound_noflags",
                  cw9b[0][4] is None, True))
    # CUERPO = token nativo de 2 bytes: todo cuerpo
    # mide exactamente 2 bytes
    bodylens = [len(f[5]) for f in funcs]
    tests.append(("fn_bodies_all_2bytes",
                  all(bl == 2 for bl in bodylens), True))
    # 322 cuerpos empiezan con opcode >= 0x80: IMPOSIBLE
    # para accion larga estandar (necesitaria code+u16
    # length+datos = >=3 bytes, +End = >=4) en 2 bytes.
    # Ergo NO son acciones AVM1 estandar (token nativo).
    big = sum(1 for f in funcs if f[5][0] >= 0x80)
    tests.append(("fn_bodies_native_token_count", big, 322))
    # 306 cuerpos NO terminan en End(0x00): tampoco
    # estandar (un cuerpo de acciones termina en End)
    noend = sum(1 for f in funcs if f[5][1] != 0x00)
    tests.append(("fn_bodies_no_end_count", noend, 306))
    # solo 839/1342 son secuencias de acciones estandar
    # de 2 bytes ([accion corta, End])
    valid = sum(1 for f in funcs
                if f[5][0] < 0x80 and f[5][1] == 0x00)
    tests.append(("fn_bodies_std_action_count", valid, 839))
    # tick cuerpo = opcode 0x44 (mayoria)
    tests.append(("fn_tick_body_0x44",
                  tk[0][5][0] == 0x44, True))
    return tests


def _collect_function_names(body, scripts):
    """Decodifica DefineFunction(0x9B)/DefineFunction2(0x8E)
    y cuenta los nombres de funcion recuperados."""
    names = {}
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        for code, doff, dlen in actions:
            if code in (0x9B, 0x8E) and dlen > 0:
                r = avm1_disasm.decode_define_function(
                    body[doff:doff + dlen], code)
                if r:
                    names[r[0]] = names.get(r[0], 0) + 1
    return names


def _resolve_properties(body, scripts, pools):
    """Detecta propiedades resueltas via SetMember(0x4F):
    patron STORE Push[...,clave,mult]->0x4F y patron RMW
    Push[o,k,o,k]->0x4E->Push[mult]->Multiply->0x4F."""
    def resolve(idx, ptype, value):
        return avm1_disasm.resolve_constant(pools.get(idx), ptype, value)

    store_props = set()
    rmw_props = set()
    for idx, s in enumerate(scripts):
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        # STORE: Push[..., clave, mult] -> SetMember
        for i in range(len(actions) - 1):
            c0, doff0, dlen0 = actions[i]
            if c0 == 0x96 and actions[i + 1][0] == 0x4F and dlen0 > 0:
                p0 = avm1_disasm.parse_push_data(body[doff0:doff0 + dlen0])
                if p0 and len(p0) >= 2:
                    last, second = p0[-1], p0[-2]
                    if (last[0] == 6 and isinstance(last[1], tuple)
                            and second[0] in (8, 9)):
                        r = resolve(idx, second[0], second[1])
                        if r:
                            store_props.add(r)
        # RMW: Push[o,k,o,k] -> GetMember -> Push[mult] -> Multiply -> SetMember
        for i in range(len(actions) - 4):
            c0, doff0, dlen0 = actions[i]
            if (c0 == 0x96 and actions[i + 1][0] == 0x4E
                    and actions[i + 2][0] == 0x96
                    and actions[i + 3][0] == 0x0C
                    and actions[i + 4][0] == 0x4F):
                p0 = avm1_disasm.parse_push_data(
                    body[doff0:doff0 + dlen0]) if dlen0 > 0 else None
                if p0:
                    kc = [(t, v) for t, v in p0 if t in (8, 9)]
                    rep = [kv for kv in kc if p0.count(kv) >= 2]
                    if rep:
                        nm, val = rep[-1]
                        r = resolve(idx, nm, val)
                        if r:
                            rmw_props.add(r)
    return store_props, rmw_props


def _cfg_tests(body, scripts):
    """Tests del simulador de pila con CFG
    (avm1_cfg.py).  RXRE-SWF-042 (decodificacion
    de salto), RXRE-SWF-043 (metodo validado) y
    RXRE-SWF-044 (efectos determinados)."""
    tests = []

    # RXRE-SWF-042: decodificacion de salto.
    # 100% de los saltos 0x99/0x9D caen en limites
    # de instruccion con destino = drel + 2 + int16.
    total_jumps = 0
    on_boundary = 0
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        starts = {0}
        for c, doff, dlen in actions:
            drel = doff - s["offset"]
            starts.add(drel if c < 0x80 else drel + dlen)
        for c, doff, dlen in actions:
            if c in (0x99, 0x9D) and dlen == 2:
                total_jumps += 1
                tgt = avm1_cfg.jump_target(
                    s["offset"], doff, body)
                if tgt in starts:
                    on_boundary += 1
    tests.append(("cfg_jump_decode_pct",
                  100 * on_boundary // total_jumps if total_jumps else 0,
                  100))

    # RXRE-SWF-043: auto-test 0x4E = -1 (>=90%).
    hits, tries, _vd = avm1_cfg._validation_0x4e(body, scripts)
    pct = 100 * hits // tries if tries else 0
    tests.append(("cfg_validation_0x4e_pct", pct >= 90, True))

    # RXRE-SWF-044: efectos determinados (unanimes).
    (determined, debil, no_det,
     _nc, _ni, _dist) = avm1_cfg.per_script_consensus(
        body, scripts)
    for code, want in avm1_disasm.CFG_DETERMINED_NET.items():
        got = determined.get(code, "NOT_DETERMINED")
        tests.append(("cfg_0x%02x_net" % code, got, want))

    # 0x52 CallMethod y 0x87 StoreRegister son
    # dependientes del valor: NO determinados.
    tests.append(("cfg_0x52_valuedep",
                  0x52 in no_det, True))
    tests.append(("cfg_0x87_valuedep",
                  0x87 in no_det, True))
    return tests


def _swainmath_tests(body, scripts, pools):
    """RXRE-SWF-052: convencion de argumentos de
    SwainMath.randomNumber(precision, lo, hi).

    AVM1 empuja los argumentos en orden INVERSO,
    de modo que el ULTIMO antes del objeto es arg1.
    La hipotesis es lo<=hi.  Se verifican las
    llamadas con los 3 args enteros comparables."""
    n_calls = 0
    n_sig = set()
    n_ordered = 0
    n_viol = 0
    for s in scripts:
        if s["length"] <= 0:
            continue
        pool = pools.get(s["_idx"])
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        for j, (code, doff, dlen) in enumerate(actions):
            if code != 0x96 or dlen <= 0:
                continue
            p = avm1_disasm.parse_push_data(
                body[doff:doff + dlen])
            if not p:
                continue
            names = [avm1_disasm.resolve_constant(
                pool, it[0], it[1]) for it in p]
            if "SwainMath" not in names:
                continue
            if (j + 3 >= len(actions)
                    or actions[j + 1][0] != 0x1C):
                continue
            c2, do2, dl2 = actions[j + 2]
            if c2 != 0x96 or dl2 <= 0:
                continue
            n2 = [avm1_disasm.resolve_constant(
                pool, it[0], it[1])
                for it in (avm1_disasm.parse_push_data(
                    body[do2:do2 + dl2]) or [])]
            if "randomNumber" not in n2:
                continue
            if actions[j + 3][0] != 0x52:
                continue
            idx = names.index("SwainMath")
            decl = list(reversed(p[:idx]))
            n_calls += 1
            # firma distinta por VALOR (no por tipo)
            n_sig.add(tuple(
                (it[0], it[1] if it[0] in (1, 4, 5, 7)
                 else repr(it[1]))
                for it in decl))
            if (len(decl) == 3
                    and decl[0][0] == 7
                    and decl[1][0] == 7
                    and decl[2][0] == 7):
                n_ordered += 1
                if decl[1][1] > decl[2][1]:
                    n_viol += 1

    tests = [
        ("swm_calls_found", n_calls >= 400, True),
        ("swm_signatures", len(n_sig) >= 100, True),
        ("swm_comparable", n_ordered >= 100, True),
        # 0 violaciones de lo<=hi -> convencion PROVEN
        ("swm_lo_le_hi_violations", n_viol, 0),
    ]
    return tests


def _body():
    data = open(SWF, "rb").read()
    import zlib
    return zlib.decompress(data[8:])


def _collect_type6(body, scripts):
    """Recolecta los pares (float32, uint32) de tipo 6."""
    out = []
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _oend, _valid = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        for code, doff, dlen in actions:
            if code == 0x96 and dlen > 0:
                parsed = avm1_disasm.parse_push_data(
                    body[doff:doff + dlen])
                if parsed is None:
                    continue
                for t, v in parsed:
                    if t == 6 and isinstance(v, tuple):
                        out.append(v)
    return out


def _type6_refutation(body, scripts):
    """RXRE-SWF-047: el uint32 tipo-6 NO es funcion determinista del float32.

    Invierte u=(M*0x100001+128)>>8 (biyeccion para M de 20 bits) para
    recuperar el M' efectivo de cada u, y clasifica M' vs lo20.
    Devuelve lista de (nombre, valor, esperado)."""
    import struct
    pairs = _collect_type6(body, scripts)
    # pares distintos (f, u)
    seen = {}
    for f, u in pairs:
        seen[(f, u)] = seen.get((f, u), 0) + 1
    distinct = list(seen.keys())

    def formula(M):
        return ((M * 0x100001 + 128) >> 8) & 0xFFFFFFFF

    def inv_M(u):
        approx = (u * 256) // 0x100001
        for M in range(max(0, approx - 4), min(0x100000, approx + 5)):
            if formula(M) == u:
                return M
        return None

    n_lo20 = n_b19 = n_c19 = n_16 = n_other = n_noinv = 0
    for f, u in distinct:
        b = struct.unpack("<I", struct.pack("<f", f))[0]
        lo20 = b & 0xFFFFF
        Mp = inv_M(u)
        if Mp is None:
            n_noinv += 1
        elif Mp == lo20:
            n_lo20 += 1
        elif Mp == (lo20 ^ 0x80000):
            n_b19 += 1
        elif Mp == (lo20 & 0x1FFFF):
            n_c19 += 1
        elif Mp == (lo20 & 0xFFFF):
            n_16 += 1
        else:
            n_other += 1
    return [
        ("type6_distinct_pairs", len(distinct), 61),
        ("type6_formula_exact_lo20", n_lo20, 27),
        ("type6_M_eq_lo20_flip19", n_b19, 9),
        ("type6_M_eq_lo20_clear19", n_c19, 8),
        ("type6_M_eq_lo20_clear16", n_16, 2),
        ("type6_M_other", n_other, 6),
        ("type6_no_inverse", n_noinv, 9),
    ]


if __name__ == "__main__":
    sys.exit(main())
