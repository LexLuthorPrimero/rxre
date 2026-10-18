#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extrae las firmas de funcion (params) y escribe
evidence/function-signatures.md (RXRE-SWF-048)."""
import sys
from collections import OrderedDict

sys.path.insert(0, "tools")
import avm1_disasm


def main():
    data = open("raw/original.swf", "rb").read()
    import zlib
    body = zlib.decompress(data[8:])
    nbits = body[0] >> 3
    rect_nbytes = (5 + 4 * nbits + 7) // 8
    off = rect_nbytes + 4
    scripts = avm1_disasm.collect_scripts(body, off, len(body))

    sigs = OrderedDict()
    for s in scripts:
        if s["length"] <= 0:
            continue
        actions, _o, _v = avm1_disasm.walk_actions(
            body, s["offset"], s["offset"] + s["length"])
        for code, doff, dlen in actions:
            if code in (0x9B, 0x8E) and dlen > 0:
                r = avm1_disasm.decode_define_function(
                    body[doff:doff + dlen], code)
                if r:
                    nm, params, rc, fl, b = r
                    sigs.setdefault(nm, {})
                    key = (tuple(params), rc, fl, b[0])
                    sigs[nm][key] = sigs[nm].get(key, 0) + 1

    L = []
    L.append("# Funciones recuperadas: firmas (RXRE-SWF-048)")
    L.append("")
    L.append("Metodo: decode_define_function(data, opcode) corregido.")
    L.append("Formato PROBADO contra bytes brutos:")
    L.append("  0x9B DefineFunction:  nombre NUL, u16 numParams,")
    L.append("       params (nombre NUL, SIN regIdx), body.")
    L.append("  0x8E DefineFunction2: nombre NUL, u16 numParams,")
    L.append("       u8 regCount, u16 flags, params (u8 regIdx +")
    L.append("       nombre NUL), body.")
    L.append("")
    L.append("## HALLAZGO: cuerpo = token nativo de 2 bytes")
    L.append("")
    L.append("TODO DefineFunction/DefineFunction2 de este SWF tiene")
    L.append("un cuerpo de EXACTAMENTE 2 bytes (1342/1342).")
    L.append("  - 322 cuerpos empiezan con opcode >= 0x80")
    L.append("    (0x9C, 0xC0, 0xD7, 0xC9, 0xC4, 0xDA, 0xE4,")
    L.append("     0xE0, 0xEB, 0xAF, 0xFA, 0xFF...), lo que es")
    L.append("    IMPOSIBLE para una accion larga AVM1 estandar")
    L.append("    (necesitaria code + u16 length + datos = >=3")
    L.append("    bytes, + End = >=4 bytes) en 2 bytes.")
    L.append("  - 306 cuerpos NO terminan en End(0x00).")
    L.append("  - Solo 839/1342 son secuencias de acciones")
    L.append("    estandar de 2 bytes ([accion corta, End]).")
    L.append("")
    L.append("Ergo: el cuerpo NO es una secuencia de acciones")
    L.append("AVM1 estandar. Es un TOKEN DE LLAMADA A RUTINA")
    L.append("NATIVA. La formula exacta de combate NO esta en")
    L.append("los cuerpos; hay que recuperarla del stream")
    L.append("principal (Push/GetMember/arith/SetMember) o")
    L.append("requiere runtime (RXRE-SWF-014).")
    L.append("")
    L.append("Esto REFUTA la premisa de desensamblar tick()")
    L.append("para la formula: tick() es un token nativo")
    L.append("(0x44 la mayoria), no codigo AVM1.")
    L.append("")
    L.append("## Firmas (nombre -> params, regCount, flags, body)")
    L.append("")
    L.append("| Funcion | #params | Params | regCount | flags | body | ocurrences |")
    L.append("|---|---|---|---|---|---|---|")
    for nm in sorted(sigs):
        for (params, rc, fl, bop), cnt in sorted(
                sigs[nm].items(), key=lambda kv: -kv[1]):
            fls = ("0x%04x" % fl) if fl is not None else "-"
            rcs = str(rc) if rc is not None else "-"
            L.append("| %s | %d | %s | %s | %s | 0x%02X | %d |" % (
                nm, len(params),
                ", ".join(params) if params else "-",
                rcs, fls, bop, cnt))
    L.append("")
    L.append("## Modelo de datos revelado por las firmas")
    L.append("")
    L.append("### Combate (danos/arma/impacto)")
    L.append("")
    L.append(" - EXPLOSION/DANOS (13 params, body=0x51):")
    L.append("   inType, inScorch, inSource, inX, inY, inFloor,")
    L.append("   inRange, inDamage, inSound, inKnockback, inDir,")
    L.append("   inAutoHit, inSubDeath")
    L.append(" - GOLPE DE ARMA (6 params, body=0x60):")
    L.append("   inWeapon, inAttacker, inHitX, inHitY,")
    L.append("   inRangeGood, inHeadshot")
    L.append(" - ATAQUE DE ARMA (5 params, body=0x4A):")
    L.append("   inWeapon, inAttacker, inBlock, inKillShot, inRange")
    L.append(" - MELEE (3 params, body=0x53): inMeleeDir, inMeleeType, inWeapon")
    L.append(" - DANOS (1 param, body=0x17): inDamage")
    L.append(" - BLAST (3 params, body=0x5A): inSource, inPower, inReverseBlast")
    L.append("")
    L.append("### Estadisticas de personaje (15 params, body=0xC0)")
    L.append("")
    L.append("  inStr, inDex, inTac, inEnd, inLead, inAwr, SPACER,")
    L.append("  inMelee, inUnarmed, inPistol, inRevolver, inSMG,")
    L.append("  inShotgun, inRifle, inHeavy")
    L.append("  (Str=Strength, Dex=Dexterity, Tac=Tactics,")
    L.append("   End=Endurance, Lead=Leadership, Awr=Awareness;")
    L.append("   + proficiencia por tipo de arma)")
    L.append("")
    L.append("### Fisica de sprite (15 params)")
    L.append("")
    L.append("  inType, inCategory, inX, inY, inXSpeed, inYSpeed,")
    L.append("  inRot, inRotSpeed, inBounce, inFloor, inAlpha,")
    L.append("  inScale, inStanding, inStandRot, inDataRef")
    L.append("  (posicion, velocidad, rotacion, rebote, piso,")
    L.append("   transparencia, escala, enPie)")
    L.append("")
    open("evidence/function-signatures.md", "w").write("\n".join(L))
    print("wrote evidence/function-signatures.md")
    print("unique names:", len(sigs))
    total = sum(cnt for nm in sigs for cnt in sigs[nm].values())
    print("total functions:", total)

    combat = ["inDamage", "inArmor", "inWeapon", "inAttacker",
              "inRange", "inHeadshot", "inKnockback",
              "inBlock", "inKillShot"]
    print()
    print("=== signatures mentioning combat keywords ===")
    for nm in sorted(sigs):
        for (params, rc, fl, bop), cnt in sigs[nm].items():
            ps = " ".join(params)
            if any(k in ps for k in combat):
                print("  %-18s body=0x%02X : %s" % (nm, bop, ", ".join(params)))


if __name__ == "__main__":
    main()
