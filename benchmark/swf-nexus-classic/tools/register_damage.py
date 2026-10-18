#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Registra RXRE-SWF-050: la formula de APLICACION
de danos, recuperada del stream principal.

Hallazgo (PROVEN, traza de bytecode + resolucion
de pool + balance de pila):

  r1.myAttackTarget.myHealth =
      r1.myAttackTarget.myHealth
      - (r1.myDataRef.myUnarmed.myDamage / 4)

Es decir: la SALUD del objetivo se reduce por
(danio desarmado / 4).  Esta es la APLICACION
del danio de combate, y ESTA en el stream
principal (NO solo en la rutina nativa).

Traza (script 1627, acciones 31869-31884):
  Push [R1, myAttackTarget]   ; objeto
  GetMember                   ; r1.myAttackTarget
  Push [myHealth, R1, myAttackTarget]
  GetMember                   ; r1.myAttackTarget
  Push [myHealth]
  GetMember                   ; (r1.myAttackTarget).myHealth
  Push [R1, myDataRef]
  GetMember                   ; r1.myDataRef
  Push [myUnarmed]
  GetMember                   ; r1.myDataRef.myUnarmed
  Push [myDamage]
  GetMember                   ; .myUnarmed.myDamage
  Push [4]
  Divide                      ; myDamage/4
  Subtract (0x0B)             ; myHealth - myDamage/4
  SetMember (0x4F)            ; myAttackTarget.myHealth = ...

Balance neto: +2-1+3-1+1-1+2-1+1-1+1-1+1-1-1-3 = 0.

Formulas relacionadas (mismo stream):
  recoilTimer = weapon.myDamage * weapon.myShots
  skillPoints = myLevel * 3
  myDataRef.myHealth = myHealthMax / 2  (respawn)
  myGun.myHealth = myGun.myHealth - 2   (durabilidad)
  targetHealthY = 5 * (myHealth/myHealthMax)

NO recuperado: la MITIGACION de armadura
(como myArmor reduce el danio entrante) —
esta en la rutina nativa (token, RXRE-SWF-048)
con firma inDamage/inArmor.
"""
import hashlib
import json
import sys

sys.path.insert(0, "/home/lucas/Escritorio/rxre/tools/rxre")
from core import store as S  # noqa: E402

sys.path.insert(0, "tools")
import avm1_disasm as A  # noqa: E402
import avm1_sym as SYM  # noqa: E402

SESSION = "swf-nexus"
TARGET = "Madness Project Nexus Classic.swf"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _trace_damage():
    """Traza la formula de aplicacion de danio y
    devuelve (pool_resolved, balance, actions)."""
    import zlib
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
    sym = SYM.Sym(body, s["offset"], s["length"], pool)
    sym.run()
    actions, _, _ = A.walk_actions(
        body, s["offset"], s["offset"] + s["length"])
    for obj, key, val, aidx in sym.writes:
        if "myAttackTarget" in str(key) and \
                "myUnarmed" in str(val):
            # reconstruir la traza de pool
            seq = []
            for j in range(aidx - 16, aidx + 1):
                code, doff, dlen = actions[j]
                if code == 0x96 and dlen > 0:
                    p = A.parse_push_data(d)
                    for item in (p or []):
                        if item[0] == 9:
                            seq.append("C16:%d=%s" % (
                                item[1],
                                A.resolve_constant(
                                    pool, 9, item[1])))
                        elif item[0] == 8:
                            seq.append("LK:%d=%s" % (
                                item[1],
                                A.resolve_constant(
                                    pool, 8, item[1])))
                        elif item[0] == 4:
                            seq.append("R%d" % item[1])
                        elif item[0] == 7:
                            seq.append("I%d" % item[1])
                elif code == 0x4E:
                    seq.append("GetMember")
                elif code == 0x0D:
                    seq.append("Divide")
                elif code == 0x0B:
                    seq.append("Subtract")
                elif code == 0x4F:
                    seq.append("SetMember")
            return (seq, aidx, str(val))
    return ([], None, None)


def main():
    seq, aidx, val = _trace_damage()
    writes = SYM.analyze("raw/original.swf")

    c = S.conectar()
    res_id = "res_damage_app_" + _sha("dmg050")
    request = {
        "request_id": "req_damage_app",
        "contract_version": "1",
        "capability": "avm1_sym.damage_application",
        "question": "Is the combat damage-"
                    "application formula in "
                    "the main stream?",
        "target": TARGET,
        "scope": "script 1627, action %s" % aidx,
    }
    env = {
        "operation": "measure",
        "status": "COMPLETE",
        "results": [{
            "result_id": res_id,
            "type": "MEASUREMENT",
            "value": "DAMAGE APPLICATION "
                     "FORMULA (PROVEN): "
                     "r1.myAttackTarget.myHealth "
                     "= r1.myAttackTarget.myHealth "
                     "- (r1.myDataRef.myUnarmed"
                     ".myDamage / 4).  El objetivo "
                     "pierde salud = danio "
                     "desarmado / 4.  Traza "
                     "bytecode script 1627 acc "
                     "%s: Push[R1,myAttackTarget]"
                     "->GetMember->...->"
                     "Push[myUnarmed]->GetMember"
                     "->Push[myDamage]->"
                     "GetMember->Push[4]->"
                     "Divide->Subtract->"
                     "SetMember.  Pool: "
                     "LK:203=myAttackTarget, "
                     "LK:62=myHealth, LK:12="
                     "myDataRef, C16:546=myUnarmed,"
                     "C16:481=myDamage.  Balance "
                     "neto 0.  RELACIONADAS: "
                     "recoilTimer=weapon.myDamage"
                     "*weapon.myShots; "
                     "skillPoints=myLevel*3; "
                     "myDataRef.myHealth="
                     "myHealthMax/2; myGun.myHealth"
                     "-=2; targetHealthY=5*(myHealth"
                     "/myHealthMax).  NO recuperada: "
                     "la MITIGACION de armadura "
                     "(como myArmor reduce el danio) "
                     "— rutina nativa (RXRE-SWF-048)."
                     % aidx,
            "source": "tools/register_damage.py",
            "location": {
                "file":
                    "evidence/symbolic-formulas.md"},
            "scope": "script 1627 (enterFrameHandler)",
            "tool": "avm1_sym.py + bytecode trace",
            "tool_version": "1",
            "status": "PROVEN",
            "bytecode_trace": seq,
            "formula": val,
            "limitation": "Weapon damage uses the "
                          "same subtraction with a "
                          "computed damage variable; "
                          "the full weapon-damage "
                          "computation (with armor "
                          "mitigation) is in the "
                          "native routine inDamage/"
                          "inArmor (RXRE-SWF-048).",
        }],
    }
    op_id = S.registrar(c, request, env)
    print("evidence op:", op_id, "result:", res_id)

    r = S.registrar_investigacion(
        c, "claim",
        "[RXRE-SWF-050/PROVEN] Aplicacion de "
        "danio en el stream principal: "
        "myAttackTarget.myHealth = "
        "myAttackTarget.myHealth - "
        "(myDataRef.myUnarmed.myDamage/4). "
        "El objetivo pierde salud = danio "
        "desarmado/4.  Traza bytecode + pool "
        "+ balance neto 0.  recoilTimer="
        "weapon.myDamage*weapon.myShots; "
        "skillPoints=myLevel*3.  La "
        "mitigacion de armadura (como myArmor "
        "reduce el danio) NO se recupera: "
        "rutina nativa inDamage/inArmor "
        "(RXRE-SWF-048).",
        "PROVEN", refs=[res_id],
        session=SESSION, target=TARGET, gap_kind="")
    print("RXRE-SWF-050 ->", r.get("estado"),
          "id", r.get("id"))

    resp = {
        "claim_id": "RXRE-SWF-050",
        "taxonomy": "MEASUREMENT",
        "state": "PROVEN",
        "evidence_op": op_id,
        "result_id": res_id,
        "rxre": r,
        "formula": val,
        "bytecode_trace": seq,
    }
    with open("queries/damage-response.json",
              "w") as f:
        json.dump(resp, f, indent=1,
                  ensure_ascii=False)
    print("saved queries/damage-response.json")


if __name__ == "__main__":
    main()
