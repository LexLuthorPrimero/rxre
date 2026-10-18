#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra los hallazgos del simulador de pila con CFG
(avm1_cfg.py) via RXRE (registrar_investigacion).

Hallazgos:
  RXRE-SWF-042  decodificacion de salto (PROVEN)
  RXRE-SWF-043  metodo CFG validado (SUPPORTED)
  RXRE-SWF-044  efectos netos determinados (SUPPORTED)
  RXRE-SWF-045  opcodes dependientes del valor (NOT_DETERMINED)
  RXRE-SWF-046  opcodes restantes sin datos (NOT_DETERMINED)
"""
import hashlib
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")
from core import store as S  # noqa: E402

SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main():
    c = S.conectar()
    resp = []

    # --- Evidencia: decodificacion de salto (RXRE-SWF-042) ---
    res_id = "res_jump_decode_7053_" + _sha("jump")
    request = {
        "request_id": "req_jump_decode",
        "contract_version": "1",
        "capability": "avm1_cfg.stack_simulator",
        "question": "Do 0x99/0x9D jump targets land on "
                    "instruction boundaries?",
        "target": TARGET,
        "scope": "all 1749 scripts",
    }
    env = {
        "operation": "measure",
        "status": "COMPLETE",
        "results": [{
            "result_id": res_id,
            "type": "MEASUREMENT",
            "value": "7053/7053 (100%) jump targets on "
                     "instruction boundaries; "
                     "target = data_pos + 2 + int16_signed",
            "source": "tools/avm1_cfg.py",
            "location": {"file": "tools/avm1_cfg.py",
                         "line": "jump_target"},
            "scope": "all scripts",
            "tool": "avm1_cfg.py",
            "tool_version": "1",
            "status": "PROVEN",
        }],
    }
    op_id = S.registrar(c, request, env)
    print("evidence op:", op_id, "result:", res_id)

    def rec(cid, tax, kind, text, status, refs=None,
            gap=None):
        r = S.registrar_investigacion(
            c, kind,
            "[%s/%s] %s" % (cid, tax, text),
            status, refs=refs or [],
            session=SESSION, target=TARGET,
            gap_kind=gap or "")
        resp.append({"claim_id": cid, "taxonomy": tax,
                     "state": status, "kind": kind,
                     "rxre": r})
        print("%-14s %-16s %-14s -> %s" % (
            cid, tax, status, r.get("estado")))
        return r

    # RXRE-SWF-042: decodificacion de salto (PROVEN, con ref)
    rec("RXRE-SWF-042", "FACT", "claim",
        "Decodificacion de salto AVM1 PROBADA: 0x99=salto "
        "incondicional (1 sucesor); 0x9D=branch condicional "
        "(2 sucesores). destino = pos_campo_offset + 2 + "
        "int16_con_signo. 7053/7053 saltos (100%) caen en "
        "limites de instruccion.",
        "PROVEN", refs=[res_id])

    # RXRE-SWF-043: metodo CFG validado (SUPPORTED)
    rec("RXRE-SWF-043", "MEASUREMENT", "hypothesis",
        "Simulador de pila con CFG (consenso por script): "
        "resuelve cada script por separado y agrega el "
        "consenso unanime entre scripts consistentes. "
        "VALIDADO: recupera 0x4E=GetMember como neto -1 en "
        "24/25 scripts (1 determinacion fraccionaria "
        "espuria filtrada). 187 scripts consistentes, 35 "
        "inconsistentes.",
        "SUPPORTED")

    # RXRE-SWF-044: efectos determinados (SUPPORTED)
    rec("RXRE-SWF-044", "DERIVATION", "hypothesis",
        "Efectos netos (push-pop) DETERMINADOS por consenso "
        "unanime: 0x9D BranchIf=-1 (consume la condicion, "
        "4 scripts); 0x40=-1 (16); 0x49=-1 (6); 0x3E=-1 (2); "
        "0x9F=-1 (18); 0x42=0 (2); 0x81=0 (2); 0x8C=0 (2). "
        "SUPPORTED por metodo validado (RXRE-SWF-043), no "
        "PROVEN (sin runtime Flash).",
        "SUPPORTED")

    # RXRE-SWF-045: opcodes dependientes del valor (NOT_DETERMINED)
    rec("RXRE-SWF-045", "NEGATIVE_RESULT", "hypothesis",
        "0x52 CallMethod y 0x87 StoreRegister son "
        "dependientes del valor: su efecto de pila depende "
        "de valores en la pila (# de args de CallMethod: "
        "-2/-3/-4; StoreRegister: dominante 0 en 6/7 con "
        "discordancia -1). NO determinables por analisis de "
        "profundidad (requiere simulacion de valores).",
        "NOT_DETERMINED")

    # RXRE-SWF-046: opcodes restantes (NOT_DETERMINED)
    rec("RXRE-SWF-046", "NEGATIVE_RESULT", "note",
        "Opcodes 0x3D,0x43,0x47,0x50,0x53 con consenso "
        "discordante (no unanime) y 0x48,0x51 sin datos "
        "(nunca en ecuaciones consistentes): efecto "
        "NOT_DETERMINED. 0x67 UnaryCompare sigue como "
        "hipotesis SUPPORTED sin determinar por CFG.",
        "NOT_DETERMINED")

    # guardar respuestas
    import json
    with open("queries/cfg-record-responses.json", "w") as f:
        json.dump(resp, f, indent=1, ensure_ascii=False)
    print("\nregistrados:", len(resp))
    return resp


if __name__ == "__main__":
    main()
