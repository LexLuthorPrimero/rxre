#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra la refutacion del uint32 tipo-6 (RXRE-SWF-047)
via RXRE (registrar_investigacion).

Hallazgo:
  RXRE-SWF-047  el uint32 tipo-6 NO es funcion determinista
                del float32 (PROVEN, NEGATIVE_RESULT)
"""
import hashlib
import json
import struct
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")
from core import store as S  # noqa: E402

SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"
SWF = "raw/original.swf"

sys.path.insert(0, "tools")
import avm1_disasm  # noqa: E402


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _collect_type6(body, scripts):
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


def main():
    sys.path.insert(0, "tools")
    import zlib

    data = open(SWF, "rb").read()
    body = zlib.decompress(data[8:])
    res = avm1_disasm.main(SWF)
    scripts = res["scripts"]

    pairs = _collect_type6(body, scripts)
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

    c = S.conectar()
    # --- Evidencia: analisis de inversion de formula ---
    res_id = "res_type6_refute_61_" + _sha("type6")
    request = {
        "request_id": "req_type6_refute",
        "contract_version": "1",
        "capability": "avm1_disasm.type6_formula_inversion",
        "question": "Is the type-6 uint32 a deterministic "
                    "function of the float32?",
        "target": TARGET,
        "scope": "61 distinct type-6 (float32,uint32) pairs",
    }
    env = {
        "operation": "measure",
        "status": "COMPLETE",
        "results": [{
            "result_id": res_id,
            "type": "NEGATIVE_RESULT",
            "value": "formula u=((b&0xFFFFF)*0x100001+128)>>8 "
                     "exact for 27/61; M'==lo20^0x80000 in 9; "
                     "M'==lo20&0x1FFFF in 8; M'==lo20&0xFFFF in 2; "
                     "OTHER in 6; NO_INVERSE in 9. NOT a "
                     "deterministic function.",
            "source": "tools/register_type6_refutation.py",
            "location": {"file":
                         "evidence/type6-uint32-analysis.md"},
            "scope": "61 distinct pairs",
            "tool": "avm1_disasm.py",
            "tool_version": "1",
            "status": "PROVEN",
        }],
    }
    op_id = S.registrar(c, request, env)
    print("evidence op:", op_id, "result:", res_id)

    # RXRE-SWF-047: refutacion (PROVEN, NEGATIVE_RESULT, con ref)
    r = S.registrar_investigacion(
        c, "claim",
        "[RXRE-SWF-047/NEGATIVE_RESULT] REFUTACION: el "
        "uint32 tipo-6 NO es funcion determinista del "
        "float32. Invirtiendo u=(M*0x100001+128)>>8 se "
        "recupera el M' efectivo: M'==lo20 en 27/61; "
        "M'==lo20^0x80000 en 9; M'==lo20&0x1FFFF en 8; "
        "M'==lo20&0xFFFF en 2; OTHER en 6; 9 pares sin "
        "inversa. El mismo u aparece con lo20 distinto "
        "(u=0.4 para f=1.8,1.8625,1.89375,1.925,2.0375,"
        "2.1,3.77822). La formula es coincidencia (vale "
        "cuando lo20==round(u*2^20)). El uint32 es un "
        "valor separado (peso/probabilidad).",
        "PROVEN", refs=[res_id],
        session=SESSION, target=TARGET, gap_kind="")
    print("RXRE-SWF-047 ->", r.get("estado"))

    resp = {"claim_id": "RXRE-SWF-047",
            "taxonomy": "NEGATIVE_RESULT", "state": "PROVEN",
            "evidence_op": op_id, "result_id": res_id,
            "rxre": r,
            "counts": {"distinct": len(distinct),
                       "lo20": n_lo20, "flip19": n_b19,
                       "clear19": n_c19, "clear16": n_16,
                       "other": n_other, "no_inverse": n_noinv}}
    with open("queries/type6-refute-response.json", "w") as f:
        json.dump(resp, f, indent=1, ensure_ascii=False)
    print("saved queries/type6-refute-response.json")


if __name__ == "__main__":
    main()
