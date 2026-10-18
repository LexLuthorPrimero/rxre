#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra RXRE-SWF-051: aleatorizacion
del danio y critico de headshot,
recuperados del stream principal.

Hallazgos (PROVEN, traza de bytecode +
resolucion de pool):

1. ALEATORIZACION del danio:
   bodyDamage = Math.floor(
     SwainMath.randomNumber(totalFrameDamage,
                            -2, 2) / 4)
   headDamage = Math.floor(
     SwainMath.randomNumber(totalFrameDamage,
                            -2, 2) / 4)
   El danio varia aleatoriamente en
   [totalFrameDamage-2, totalFrameDamage+2],
   piso, dividido por 4.

2. CRITICO DE HEADSHOT:
   si perkHeadshotCrits:
     damage = bodyDamage * r18
   donde r18 = SwainMath.randomNumber(
                  200, 120, 2) / 100
   = un valor aleatorio en [1.2, 2.0]
   (120% a 200% del danio).
   Para melee-especial (amSpecial &&
   myCat==melee): r18 = 1 (sin critico).

3. PERK bulletEater: afecta el danio
   (ramificacion en el computo).

4. totalFrameDamage = r3 (el danio total
   del frame).  El danio total se computa
   en ramas previas (flujo de control);
   la MITIGACION de armadura esta en ese
   computo (requiere seguimiento de valores
   con CFG, no lineal).

Trazas:
  headshot mult (acc 13653):
    Push[I200,I120,I2,SwainMath] -> 0x1C ->
    Push[randomNumber] -> CallMethod ->
    Push[I100] -> Divide -> StoreRegister R18
  headDamage (acc 14018):
    Push[R3,R1,totalFrameDamage] -> GetMember
    -> 0x47(NIP) -> Push[I-2,I2,SwainMath] ->
    0x1C -> Push[randomNumber] -> CallMethod ->
    Push[I4] -> Divide -> Push[I1,Math] -> 0x1C
    -> Push[floor] -> CallMethod ->
    StoreRegister R16
  bodyDamage (acc 14279): similar, base r3.
  crit (acc 13896):
    r3 = r1.bodyDamage; si perkHeadshotCrits:
    r3 = r3 * r18; r4.myDamage = r3;
    r1.myHealth = r1.myHealth - r3.
"""
import hashlib
import json
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")
from core import store as S  # noqa: E402

SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main():
    c = S.conectar()
    res_id = "res_dmg_rand_" + _sha("dmg051")
    request = {
        "request_id": "req_dmg_rand",
        "contract_version": "1",
        "capability": "avm1_sym.damage_randomization",
        "question": "How is weapon damage "
                    "randomized and how "
                    "does the headshot "
                    "crit work?",
        "target": TARGET,
        "scope": "script 1627 (enterFrameHandler)",
    }
    env = {
        "operation": "measure",
        "status": "COMPLETE",
        "results": [{
            "result_id": res_id,
            "type": "MEASUREMENT",
            "value": "DAMAGE RANDOMIZATION "
                     "(PROVEN): bodyDamage = "
                     "Math.floor(SwainMath"
                     ".randomNumber("
                     "totalFrameDamage, -2, 2)"
                     " / 4); headDamage = same. "
                     "Damage varies randomly in "
                     "[totalFrameDamage-2, "
                     "totalFrameDamage+2], "
                     "floored, /4. HEADSHOT "
                     "CRIT (PROVEN): if "
                     "perkHeadshotCrits: damage "
                     "= bodyDamage * r18 where "
                     "r18 = SwainMath.random"
                     "Number(200, 120, 2)/100 "
                     "= random in [1.2, 2.0] "
                     "(120%-200% damage). For "
                     "amSpecial && myCat==melee: "
                     "r18 = 1 (no crit). "
                     "PERK bulletEater affects "
                     "damage. totalFrameDamage "
                     "= r3 (total frame damage, "
                     "computed across branches; "
                     "the ARMOR MITIGATION is "
                     "in that computation and "
                     "requires CFG-aware value "
                     "tracking, not the linear "
                     "executor).",
            "source": "tools/register_damage2.py",
            "location": {
                "file":
                    "evidence/symbolic-formulas.md"},
            "scope": "script 1627",
            "tool": "avm1_sym.py + bytecode trace",
            "tool_version": "1",
            "status": "PROVEN",
            "formulas": {
                "bodyDamage": "Math.floor("
                              "SwainMath.random"
                              "Number(totalFrame"
                              "Damage, -2, 2)/4)",
                "headDamage": "Math.floor("
                              "SwainMath.random"
                              "Number(totalFrame"
                              "Damage, -2, 2)/4)",
                "headshot_crit_mult": "SwainMath"
                                     ".random"
                                     "Number(200,"
                                     "120,2)/100 "
                                     "in [1.2,2.0]",
                "headshot_gate": "perkHeadshotCrits",
                "apply": "target.myHealth -= damage",
            },
            "limitation": "Armor mitigation (how "
                          "myArmor reduces the "
                          "totalFrameDamage) is in "
                          "the totalFrameDamage "
                          "computation, which is "
                          "across branches "
                          "(requires CFG-aware "
                          "value tracking). "
                          "NOT recovered by the "
                          "linear executor.",
        }],
    }
    op_id = S.registrar(c, request, env)
    print("evidence op:", op_id, "result:", res_id)

    r = S.registrar_investigacion(
        c, "claim",
        "[RXRE-SWF-051/PROVEN] Aleatorizacion "
        "del danio: bodyDamage=headDamage="
        "Math.floor(SwainMath.randomNumber("
        "totalFrameDamage,-2,2)/4). Critico "
        "de headshot: si perkHeadshotCrits, "
        "damage=bodyDamage*r18 con "
        "r18=SwainMath.randomNumber(200,120,"
        "2)/100 (aleatorio [1.2,2.0]=120-200%). "
        "Para amSpecial&&melee: r18=1. Perk "
        "bulletEater afecta el danio. "
        "totalFrameDamage=r3 (danio total del "
        "frame). La MITIGACION de armadura "
        "esta en el computo de totalFrameDamage "
        "(en ramas; requiere seguimiento con "
        "CFG, no lineal).",
        "PROVEN", refs=[res_id],
        session=SESSION, target=TARGET, gap_kind="")
    print("RXRE-SWF-051 ->", r.get("estado"),
          "id", r.get("id"))

    resp = {
        "claim_id": "RXRE-SWF-051",
        "taxonomy": "MEASUREMENT",
        "state": "PROVEN",
        "evidence_op": op_id,
        "result_id": res_id,
        "rxre": r,
        "formulas": {
            "bodyDamage": "Math.floor(SwainMath"
                          ".randomNumber("
                          "totalFrameDamage,"
                          "-2,2)/4)",
            "headDamage": "Math.floor(SwainMath"
                          ".randomNumber("
                          "totalFrameDamage,"
                          "-2,2)/4)",
            "headshot_crit": "if perkHeadshotCrits:"
                             " damage=bodyDamage*"
                             "SwainMath.random"
                             "Number(200,120,2)"
                             "/100 in [1.2,2.0]",
            "bulletEater": "perk affects damage",
            "totalFrameDamage": "= r3 (total "
                                "damage, across "
                                "branches)",
        },
    }
    with open("queries/damage-rand-response.json",
              "w") as f:
        json.dump(resp, f, indent=1,
                  ensure_ascii=False)
    print("saved queries/damage-rand-response.json")


if __name__ == "__main__":
    main()
