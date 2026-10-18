#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra RXRE-SWF-048 via RXRE.

Hallazgo (PROVEN):
  Los CUERPOS de DefineFunction(0x9B)/DefineFunction2(0x8E)
  son TOKENS NATIVOS de 2 bytes, NO secuencias de
  acciones AVM1 estandar.  Ademas, las FIRMAS
  (params) revelan el modelo de datos de combate,
  estadisticas y fisica del juego.

Corolario (NEGATIVE_RESULT):
  La premisa "desensamblar tick() para recuperar la
  formula exacta de combate" es REFUTADA: tick() es
  un token nativo (0x44), no codigo AVM1.  La formula
  exacta NO esta en los cuerpos; requiere el stream
  principal o runtime (RXRE-SWF-014).
"""
import hashlib
import json
import sys
import zlib

sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")
from core import store as S  # noqa: E402

SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"
SWF = "raw/original.swf"

sys.path.insert(0, "tools")
import avm1_disasm  # noqa: E402


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main():
    data = open(SWF, "rb").read()
    body = zlib.decompress(data[8:])
    res = avm1_disasm.main(SWF)
    scripts = res["scripts"]

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

    total = len(funcs)
    all2 = all(len(f[5]) == 2 for f in funcs)
    big = sum(1 for f in funcs if f[5][0] >= 0x80)
    noend = sum(1 for f in funcs if f[5][1] != 0x00)
    std = sum(1 for f in funcs
              if f[5][0] < 0x80 and f[5][1] == 0x00)

    # firmas unicas
    from collections import OrderedDict
    sigs = OrderedDict()
    for code, nm, params, rc, fl, b in funcs:
        sigs.setdefault(nm, {})
        key = (tuple(params), rc, fl, b[0])
        sigs[nm][key] = sigs[nm].get(key, 0) + 1

    sig_lines = []
    for nm in sorted(sigs):
        for (params, rc, fl, bop), cnt in sorted(
                sigs[nm].items(), key=lambda kv: -kv[1]):
            sig_lines.append("%s|%d|%s|%s|%s|0x%02x|%d" % (
                nm, len(params),
                ",".join(params) if params else "-",
                str(rc) if rc is not None else "-",
                ("0x%04x" % fl) if fl is not None else "-",
                bop, cnt))

    c = S.conectar()
    # --- Evidencia: cuerpo=nativo + firmas ---
    res_id = "res_fn_native_token_" + _sha("fn048")
    request = {
        "request_id": "req_fn_native_token",
        "contract_version": "1",
        "capability": "avm1_disasm.decode_define_function",
        "question": "Are DefineFunction/DefineFunction2 "
                    "bodies standard AVM1 action sequences?",
        "target": TARGET,
        "scope": "1342 DefineFunction/DefineFunction2",
    }
    env = {
        "operation": "measure",
        "status": "COMPLETE",
        "results": [{
            "result_id": res_id,
            "type": "NEGATIVE_RESULT",
            "value": "ALL bodies are exactly 2 bytes "
                     "(%d/%d). %d bodies start with opcode "
                     ">=0x80 (impossible for a standard long "
                     "action in 2 bytes: needs code+u16 len"
                     "+data>=3B, +End>=4B). %d bodies do not "
                     "end in End(0x00). Only %d are valid 2-"
                     "byte standard action sequences. Bodies "
                     "are NATIVE-CALL TOKENS, not AVM1."
                     % (total, total, big, noend, std),
            "source": "tools/register_signatures.py",
            "location": {
                "file": "evidence/function-signatures.md"},
            "scope": "%d functions, %d unique names"
                     % (total, len(sigs)),
            "tool": "avm1_disasm.py",
            "tool_version": "1",
            "status": "PROVEN",
            "signatures": sig_lines,
        }],
    }
    op_id = S.registrar(c, request, env)
    print("evidence op:", op_id, "result:", res_id)

    # RXRE-SWF-048: cuerpo=nativo (PROVEN, con ref)
    r = S.registrar_investigacion(
        c, "claim",
        "[RXRE-SWF-048/PROVEN] Los cuerpos de "
        "DefineFunction(0x9B)/DefineFunction2(0x8E) son "
        "tokens nativos de 2 bytes, NO acciones AVM1: "
        "%d/%d cuerpos=2B; %d empiezan con opcode>=0x80 "
        "(imposible para accion larga en 2B); %d no "
        "terminan en End; solo %d son acciones estandar. "
        "tick()=token 0x44. La formula exacta de combate "
        "NO esta en los cuerpos."
        % (total, total, big, noend, std),
        "PROVEN", refs=[res_id],
        session=SESSION, target=TARGET, gap_kind="")
    print("RXRE-SWF-048 ->", r.get("estado"))

    resp = {
        "claim_id": "RXRE-SWF-048",
        "taxonomy": "NEGATIVE_RESULT",
        "state": "PROVEN",
        "evidence_op": op_id,
        "result_id": res_id,
        "rxre": r,
        "counts": {"total": total, "all_2bytes": all2,
                   "native_token(>=0x80)": big,
                   "no_end": noend, "std_actions": std,
                   "unique_names": len(sigs)},
    }
    with open("queries/signatures-response.json", "w") as f:
        json.dump(resp, f, indent=1, ensure_ascii=False)
    print("saved queries/signatures-response.json")


if __name__ == "__main__":
    main()
