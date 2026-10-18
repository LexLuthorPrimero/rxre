#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extrae las formulas recuperadas por el ejecutor
simbolico (avm1_sym.py, RXRE-SWF-049) y escribe
evidence/symbolic-formulas.md."""
import sys
from collections import OrderedDict

sys.path.insert(0, "tools")
import avm1_sym as S


CATEGORIES = [
    ("Combate (dano y aplicacion)",
     ["myHealth", "myAttackTarget", "myGun",
      "meleeHealth", "recoilTimer",
      "skillPoints", "myPrice", "myDamage",
      "myShots", "myROF", "myUnarmed",
      "myLevel", "myHealthMax", "bodyDamage",
      "headDamage", "damageDifficultyMod",
      "arenaKills", "autoHit", "inRange",
      "myRange", "myKnockback", "myHeadshot",
      "myBlock", "myKillShot", "bulletEater",
      "blocking", "hitStopAttack", "findRange",
      "brokeRange", "myKills", "myWeapon",
      "inHeadshot", "inDamage", "inArmor",
      "inWeapon", "inAttacker", "inKillShot",
      "inBlock", "inAutoHit", "inKnockback",
      "inDir", "inSubDeath", "inType",
      "inScorch", "inSource", "inFloor",
      "inSound", "inMelee", "inMeleeDir",
      "inMeleeType", "inHitX", "inHitY",
      "inRangeGood", "inPower", "inReverseBlast",
      "inEnemy", "inTarget", "inChar",
      "inRoom", "inLocker", "inWeapons",
      "inTrack", "inTrackObj", "inOn",
      "inSound", "inPan", "inName",
      "inUnits", "inDifficulty", "inCategory",
      "inLeader", "inRef", "inRosterRef",
      "inFaction", "inPlayer", "inRoster",
      "myDoor", "myStartX", "myStartY",
      "inX", "inY", "inXSpeed", "inYSpeed",
      "inRot", "inRotSpeed", "inBounce",
      "inAlpha", "inScale", "inStanding",
      "inStandRot", "inDataRef", "inStr",
      "inDex", "inTac", "inEnd", "inLead",
      "inAwr", "SPACER", "inPistol",
      "inRevolver", "inSMG", "inShotgun",
      "inRifle", "inHeavy"]),
    ("Estadisticas -> modificadores",
     ["statSTR", "statDEX", "statTAC", "statEND",
      "statLEAD", "statAWR", "modDmg", "modSpeed",
      "modRecharge", "modAllySmart", "modHurtTactics",
      "modArmor"]),
    ("Armadura (fuente y valores)",
     ["myArmor", "myBodyArmor", "myHeadArmor",
      "amArmor", "armor", "myPrice", "myShirt",
      "myHat", "myMask", "myMouth"]),
    ("Danos",
     ["myDamage", "damage", "myUnarmed",
      "assignWeaponDamage", "bodyDamage",
      "headDamage", "bodydamage", "damageDifficultyMod"]),
    ("Movimiento",
     ["myAccel", "mySpeed", "mySpeedRight",
      "mySpeedDown", "myAimX", "myAimY",
      "intendedX", "intendedY", "modSpeed",
      "slowmoSpeedMod", "stairsAdjustMove",
      "doorLockBoost", "myDash"]),
    ("Salud / heridas",
     ["health", "Health", "wound", "Wound",
      "meleeHealth", "bodyWounds", "headWounds"]),
    ("Temporizadores",
     ["Timer", "timer"]),
]


def categorize(key):
    k = str(key)
    for cat, kws in CATEGORIES:
        for kw in kws:
            if kw in k:
                return cat
    return "Otras"


def main():
    writes = S.analyze("raw/original.swf")

    # deduplicar por (obj, clave, patron-valor)
    cats = OrderedDict()
    for cat, _ in CATEGORIES:
        cats[cat] = OrderedDict()
    cats["Otras"] = OrderedDict()

    for idx, obj, key, val, aidx in writes:
        cat = categorize(key)
        vpat = str(val)
        sig = (str(obj), str(key), vpat)
        d = cats[cat]
        if sig not in d:
            d[sig] = (idx, aidx)

    L = []
    L.append("# Formulas recuperadas por el ejecutor")
    L.append(" simbolico (RXRE-SWF-049)")
    L.append("")
    L.append("## Metodo")
    L.append("")
    L.append("Ejecutor simbolico lineal (`tools/avm1_sym.py`)")
    L.append("sobre el stream principal AVM1. Seguimiento")
    L.append("de pila de expresiones simbolicas con")
    L.append("profundidad de expresion (`expr_depth`) para")
    L.append("calcular el marco de `CallMethod` (0x52):")
    L.append("marco = profundidad_actual - expr_depth =")
    L.append("args + objeto + metodo, donde expr_depth =")
    L.append("profundidad tras la ultima accion")
    L.append("terminadora (SetMember/SetVariable/Pop/")
    L.append("StoreRegister/CallMethod/BranchIf/Jump).")
    L.append("Esto recupera el # de args aunque los args")
    L.append("sean computados via GetMember (que reinicia")
    L.append("el contador de pushes consecutivos).")
    L.append("")
    L.append("## Limitaciones (instrumento de investigacion)")
    L.append("")
    L.append("- Ejecucion LINEAL: los merges del CFG no")
    L.append("  se unen (una variable puede tener el valor")
    L.append("  de una sola rama).")
    L.append("- Las llamadas a rutinas nativas (0x52)")
    L.append("  producen un resultado opaco `call()`; el")
    L.append("  argumento de retorno es desconocido.")
    L.append("- El marco de CallMethod es un heuristico")
    L.append("  (puede fallar en llamadas encadenadas).")
    L.append("- La MITIGACION de armadura (danos =")
    L.append("  f(myDamage, myArmor)) NO aparece: esta")
    L.append("  en la rutina nativa (token, RXRE-SWF-048)")
    L.append("  con firma inDamage/inArmor.")
    L.append("")
    L.append("Escrituras recuperadas: %d" % len(writes))
    arith = [w for w in writes
             if any(op in str(w[3])
                    for op in ("+", "*", "-", "/"))]
    L.append("con expresion aritmetica: %d" % len(arith))
    L.append("")

    total = 0
    for cat, d in cats.items():
        L.append("## %s (%d)" % (cat, len(d)))
        L.append("")
        L.append("| script | objeto | propiedad | valor |")
        L.append("|---|---|---|---|")
        for (obj, key, vpat), (idx, aidx) in d.items():
            L.append("| %d | %s | %s | `%s` |" % (
                idx, obj, key, vpat))
            total += 1
        L.append("")
    L.append("Total formulas distintas: %d" % total)
    L.append("")

    with open("evidence/symbolic-formulas.md", "w") as f:
        f.write("\n".join(L))
    print("wrote evidence/symbolic-formulas.md")
    print("total distinct formulas:", total)
    for cat, d in cats.items():
        print("  %-32s : %d" % (cat, len(d)))

    # resumen de las formulas clave
    print()
    print("=== FORMULAS CLAVE ===")
    key_formulas = [
        ("modDmg", "statSTR/15"),
        ("modArmor", "statEND/15"),
        ("modSpeed", "statDEX/45"),
        ("modRecharge", "statTAC/10"),
        ("modAllySmart", "statLEAD/15"),
        ("modHurtTactics", "statAWR/50"),
        ("myAccel", "mySpeed/4"),
        ("myDamage", "myDamage*3"),
        ("myHeadArmor", "myHat"),
        ("myBodyArmor", "myShirt"),
        ("myPrice", "myArmor*100"),
        ("myHealth", "myUnarmed.myDamage/4"),
        ("recoilTimer", "myShots"),
        ("skillPoints", "myLevel*3"),
    ]
    for prop, pat in key_formulas:
        found = []
        for cat, d in cats.items():
            for (obj, key, vpat), (idx, aidx) in d.items():
                if prop in str(key) and pat in vpat:
                    found.append((idx, obj, key, vpat))
        if found:
            idx, obj, key, vpat = found[0]
            print("  [%s].%s = %s  (script %d)" % (
                obj, key, vpat, idx))
        else:
            print("  [NO ENCONTRADO] %s = %s" % (prop, pat))


if __name__ == "__main__":
    main()
