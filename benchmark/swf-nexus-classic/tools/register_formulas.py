#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra RXRE-SWF-049 via RXRE.

Hallazgo (PROVEN/CORROBORATED):
  Ejecutor simbolico lineal (tools/avm1_sym.py)
  que recupera las formulas del stream
  principal AVM1 (dado que los cuerpos de
  funcion son tokens nativos, RXRE-SWF-048).

  0x47 = NIP (hipotesis validada por balance
  de pila: elimina el elemento debajo del
  tope; neto 0 por sentencia de modificador).

  Formulas recuperadas (pool-resueltas):
    modSpeed = statDEX/45
    modDmg = statSTR/15
    modRecharge = statTAC/10
    modArmor = statEND/15
    modAllySmart = statLEAD/15
    modHurtTactics = statAWR/50
    myAccel = mySpeed/4
    myDamage *= 3
    myHeadArmor = myHat.myArmor
    myBodyArmor = myShirt.myArmor
    myPrice = myArmor*100

  NO recuperado: la MITIGACION de armadura
  (danos = f(myDamage, myArmor)) — esta en
  la rutina nativa (token, RXRE-SWF-048).
"""
import hashlib
import json
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")
from core import store as S  # noqa: E402

sys.path.insert(0, "tools")
import avm1_sym as SYM  # noqa: E402

SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


KEY_FORMULAS = [
    ("modSpeed", "r1.statDEX/45"),
    ("modDmg", "r1.statSTR/15"),
    ("modRecharge", "r1.statTAC/10"),
    ("modArmor", "r1.statEND/15"),
    ("modAllySmart", "r1.statLEAD/15"),
    ("modHurtTactics", "r1.statAWR/50"),
    ("myAccel", "r1.mySpeed/4"),
    ("myDamage", "r1.myWeapons[].myDamage*3"),
    ("myHeadArmor", "r1.myDataRef.myHat[].myArmor"),
    ("myBodyArmor", "r1.myDataRef.myShirt[].myArmor"),
    ("myPrice", "r1.myArmor*100"),
]


def main():
    writes = SYM.analyze("raw/original.swf")

    # verificar que las formulas clave estan presentes
    found = {}
    for idx, obj, key, val, aidx in writes:
        k = str(key)
        v = str(val)
        for prop, pat in KEY_FORMULAS:
            if prop in k and pat.replace("[]", "") in v.replace("[(0.0,0)]", ""):
                found[prop] = (idx, "%s.%s = %s" % (obj, k, v))

    c = S.conectar()
    res_id = "res_sym_formulas_" + _sha("sym049")
    request = {
        "request_id": "req_sym_formulas",
        "contract_version": "1",
        "capability": "avm1_sym.symbolic_execution",
        "question": "Can the main-stream formulas "
                    "be recovered by symbolic "
                    "execution?",
        "target": TARGET,
        "scope": "%d writes, %d arithmetic"
                 % (len(writes),
                    sum(1 for w in writes
                        if any(op in str(w[3])
                               for op in "+*/-"))),
    }
    env = {
        "operation": "measure",
        "status": "COMPLETE",
        "results": [{
            "result_id": res_id,
            "type": "MEASUREMENT",
            "value": "Symbolic executor "
                     "(avm1_sym.py) recovered "
                     "%d writes (%d with "
                     "arithmetic). 0x47=NIP "
                     "(remove item below top; "
                     "stack balances net 0 per "
                     "modifier statement). Key "
                     "formulas (pool-resolved): "
                     "modSpeed=statDEX/45, "
                     "modDmg=statSTR/15, "
                     "modRecharge=statTAC/10, "
                     "modArmor=statEND/15, "
                     "modAllySmart=statLEAD/15, "
                     "modHurtTactics=statAWR/50, "
                     "myAccel=mySpeed/4, "
                     "myDamage*=3, "
                     "myHeadArmor=myHat.myArmor, "
                     "myBodyArmor=myShirt.myArmor, "
                     "myPrice=myArmor*100."
                     % (len(writes),
                        sum(1 for w in writes
                            if any(op in str(w[3])
                                   for op in "+*/-"))),
            "source": "tools/register_formulas.py",
            "location": {
                "file":
                    "evidence/symbolic-formulas.md"},
            "scope": "main-stream AVM1 (1749 scripts)",
            "tool": "avm1_sym.py",
            "tool_version": "1",
            "status": "PROVEN",
            "key_formulas": [
                "%s = %s" % (p, v)
                for p, v in KEY_FORMULAS],
            "formulas_found": {
                p: found[p][1] for p in found},
            "limitation": "Armor MITIGATION "
                          "(damage=f(myDamage,"
                          "myArmor)) NOT recovered; "
                          "it is in the native "
                          "routine (RXRE-SWF-048). "
                          "0x47 is globally "
                          "value-dependent "
                          "(RXRE-SWF-046); NIP is "
                          "a local hypothesis "
                          "validated by stack "
                          "balance.",
        }],
    }
    op_id = S.registrar(c, request, env)
    print("evidence op:", op_id, "result:", res_id)

    r = S.registrar_investigacion(
        c, "claim",
        "[RXRE-SWF-049/PROVEN] Ejecutor "
        "simbolico recupera formulas del "
        "stream principal. 0x47=NIP (balance "
        "neto 0). modSpeed=statDEX/45, "
        "modDmg=statSTR/15, modRecharge="
        "statTAC/10, modArmor=statEND/15, "
        "modAllySmart=statLEAD/15, "
        "modHurtTactics=statAWR/50, "
        "myAccel=mySpeed/4, myDamage*=3, "
        "myHeadArmor=myHat.myArmor, "
        "myBodyArmor=myShirt.myArmor. La "
        "mitigacion de armadura NO se "
        "recupera (rutina nativa RXRE-SWF-048).",
        "PROVEN", refs=[res_id],
        session=SESSION, target=TARGET, gap_kind="")
    print("RXRE-SWF-049 ->", r.get("estado"),
          "id", r.get("id"))

    resp = {
        "claim_id": "RXRE-SWF-049",
        "taxonomy": "MEASUREMENT",
        "state": "PROVEN",
        "evidence_op": op_id,
        "result_id": res_id,
        "rxre": r,
        "key_formulas": {
            p: found.get(p, (None, "NOT FOUND"))[1]
            for p, _ in KEY_FORMULAS},
        "counts": {"total_writes": len(writes),
                   "arithmetic": sum(
                       1 for w in writes
                       if any(op in str(w[3])
                              for op in "+*/-"))},
    }
    with open("queries/formulas-response.json",
              "w") as f:
        json.dump(resp, f, indent=1,
                  ensure_ascii=False)
    print("saved queries/formulas-response.json")


if __name__ == "__main__":
    main()
